#!/usr/bin/env python3
"""Recall benchmark for `search_memories` (Epoch X — Memory, first slice).

Measures retrieval quality of the CURRENT ranking against a fixed fixture of
memories + queries with known-relevant answers. Changes no production behavior —
it exists so any later retrieval change (scoped / hybrid / temporal / rerank) is
judged against a number instead of a hunch. See
docs/architecture/epoch-x-memory-and-retrieval.md.

Metrics (higher is better, all in [0,1]):
- hit@1     — the top result is a gold memory
- recall@k  — fraction of gold memories present in the top k
- MRR       — mean reciprocal rank of the first gold memory

Run against the real local embedder (Ollama must be up):
    python backend/benchmarks/recall_benchmark.py
Offline smoke run with a deterministic stub embedder (no Ollama):
    python backend/benchmarks/recall_benchmark.py --stub

The hermetic unit test (tests/test_recall_benchmark.py) calls run_benchmark()
directly with a stub embedder and a temp DB, so CI needs no Ollama.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_FIXTURE = HERE / "fixtures" / "recall_v1.json"

_STUB_DIM = 96


def stub_embedding(text: str) -> List[float]:
    """Deterministic bag-of-tokens embedding — lexical overlap → higher cosine.

    Good enough to exercise the pipeline hermetically; NOT a semantic model.
    """
    vec = [0.0] * _STUB_DIM
    token = ""
    for ch in text.lower():
        if ch.isalnum():
            token += ch
            continue
        if token:
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % _STUB_DIM
            vec[idx] += 1.0
            token = ""
    if token:
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % _STUB_DIM
        vec[idx] += 1.0
    return vec


def load_fixture(path: os.PathLike | str = DEFAULT_FIXTURE) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _seed(app_module, user_id: str, memories: Sequence[Dict[str, Any]]) -> None:
    conn = app_module.get_db()
    cur = conn.cursor()
    for m in memories:
        emb = app_module.get_embedding(m["summary_text"])
        cur.execute(
            "INSERT INTO memories (id, conversation_id, user_id, kind, source_text, summary_text, embedding_json, score, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (m["id"], None, user_id, m["kind"], m["source_text"], m["summary_text"],
             json.dumps(emb), 0.0, m["created_at"]),
        )
    conn.commit()
    conn.close()


def run_benchmark(
    app_module,
    fixture: Dict[str, Any],
    ks: Sequence[int] = (1, 3, 5),
    embed_fn: Optional[Callable[[str], List[float]]] = None,
) -> Dict[str, Any]:
    """Seed the fixture into whatever DB app_module.get_db() points at, run the
    real search_memories for each query, and return aggregate + per-query metrics.

    The caller owns DB isolation (set TURNING_DB_PATH before import, or monkeypatch
    app_module.get_db). If embed_fn is given, it replaces app_module.get_embedding
    for the duration of the run.
    """
    original_embed = app_module.get_embedding
    if embed_fn is not None:
        app_module.get_embedding = embed_fn
    try:
        app_module.init_db()
        user_id = fixture.get("user_id", "bench-user")
        memories = fixture["memories"]
        queries = fixture["queries"]
        _seed(app_module, user_id, memories)

        depth = max(len(memories), max(ks))
        per_query: List[Dict[str, Any]] = []
        for q in queries:
            gold = set(q["gold"])
            results = app_module.search_memories(
                query=q["query"], conversation_id=None, user_id=user_id, k=depth
            )
            ranked_ids = [r["id"] for r in results]
            first_gold_rank = next((i + 1 for i, mid in enumerate(ranked_ids) if mid in gold), None)
            per_query.append({
                "query": q["query"],
                "gold": sorted(gold),
                "top": ranked_ids[:max(ks)],
                "first_gold_rank": first_gold_rank,
                "hit@1": bool(ranked_ids and ranked_ids[0] in gold),
                "recall@k": {k: len(gold & set(ranked_ids[:k])) / len(gold) for k in ks},
                "rr": (1.0 / first_gold_rank) if first_gold_rank else 0.0,
            })
    finally:
        app_module.get_embedding = original_embed

    n = len(per_query) or 1
    agg = {
        "queries": len(per_query),
        "hit@1": sum(1 for r in per_query if r["hit@1"]) / n,
        "mrr": sum(r["rr"] for r in per_query) / n,
        "recall@k": {k: sum(r["recall@k"][k] for r in per_query) / n for k in ks},
    }
    return {"fixture": fixture.get("name", "?"), "ks": list(ks), "aggregate": agg, "per_query": per_query}


def _format_report(result: Dict[str, Any]) -> str:
    a = result["aggregate"]
    ks = result["ks"]
    lines = [
        f"Recall benchmark: {result['fixture']}  ({a['queries']} queries)",
        "",
        f"  hit@1 : {a['hit@1']:.3f}",
        f"  MRR   : {a['mrr']:.3f}",
        "  recall: " + "  ".join(f"@{k}={a['recall@k'][k]:.3f}" for k in ks),
        "",
        "  per-query (first-gold rank; a dash means gold never retrieved):",
    ]
    for r in result["per_query"]:
        rank = r["first_gold_rank"] if r["first_gold_rank"] else "-"
        flag = "" if r["hit@1"] else ("  MISS" if rank == "-" else "  (not #1)")
        lines.append(f"    rank {str(rank):>2}  {r['query']}{flag}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Recall benchmark for search_memories")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--k", default="1,3,5", help="comma-separated cutoffs")
    parser.add_argument("--stub", action="store_true", help="use the deterministic stub embedder (no Ollama)")
    parser.add_argument("--out", default=None, help="optional path to write JSON results")
    args = parser.parse_args(argv)
    ks = tuple(int(x) for x in args.k.split(","))

    # Isolate the DB before importing app (get_db reads TURNING_DB_PATH at import).
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["TURNING_DB_PATH"] = tmp.name
    sys.path.insert(0, str(HERE.parent))  # backend/ on path
    import app  # noqa: E402

    embed_fn = stub_embedding if args.stub else None
    fixture = load_fixture(args.fixture)
    result = run_benchmark(app, fixture, ks=ks, embed_fn=embed_fn)

    if not args.stub:
        # Detect the get_embedding fallback ([0.0]*10) that means Ollama was unreachable.
        probe = app.get_embedding("connectivity probe")
        if len(probe) <= 10 and not any(probe):
            print("WARNING: embedder returned the zero-vector fallback — is Ollama running "
                  "with the embed model? Results below are meaningless.\n", file=sys.stderr)

    print(_format_report(result))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    try:
        os.unlink(tmp.name)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

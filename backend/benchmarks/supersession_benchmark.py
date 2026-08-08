#!/usr/bin/env python3
"""Write-path supersession precision benchmark (Epoch X, ADR 0021).

Seeds fact pairs through the real save_memory path (isolated temp DB, real embedder) and
checks each pair's disposition against expectation:

  - declared replacement  -> AUTO   (old row superseded)
  - undeclared replacement-> PENDING (candidate recorded, nothing hidden)
  - complement            -> NONE   (no candidate at all)

Reports per-pair cosine similarity and decision, plus precision per class — the calibration
evidence for MEMORY_SUPERSEDE_THRESHOLD. Run:

  MEMORY_SUPERSEDE_THRESHOLD=0.80 python backend/benchmarks/supersession_benchmark.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

PAIRS = [
    # (old_summary, new_summary, expected: auto | pending | none)
    ("The backend listens on port 8000.", "The backend moved to port 8001.", "auto"),
    ("The active model is dolphin-mixtral.", "The active model is now llama-3.1-abliterated.", "auto"),
    ("The operator's shell is bash.", "The operator switched to PowerShell.", "auto"),
    ("The lead is Ben.", "The lead is no longer Ben; it is Ana.", "auto"),
    ("The backend listens on port 8000.", "The backend listens on port 8001.", "pending"),
    ("The deadline is Tuesday.", "The deadline is Friday.", "pending"),
    ("The backend is written in Python.", "The backend framework is FastAPI.", "none"),
    ("The operator prefers dark mode.", "The operator drinks coffee black.", "none"),
    ("The app icon uses Aurebesh glyphs.", "The operator's cat is named Pixel.", "none"),
]


def main() -> int:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["TURNING_DB_PATH"] = tmp.name
    sys.path.insert(0, str(HERE.parent))
    import app  # noqa: E402

    threshold = app.MEMORY_SUPERSEDE_THRESHOLD
    if not (0.0 < threshold <= 1.0):
        print("Set MEMORY_SUPERSEDE_THRESHOLD (e.g. 0.80) before running; it is currently off.")
        return 2

    app.init_db()
    results = []
    for i, (old, new, expected) in enumerate(PAIRS):
        kind = f"bench-{i}"  # isolate pairs from each other
        raw_sim = round(app.cosine_similarity(app.get_embedding(old), app.get_embedding(new)), 3)
        app.save_memory(conversation_id=None, user_id="bench", kind=kind, source_text="s", summary_text=old)
        app.save_memory(conversation_id=None, user_id="bench", kind=kind, source_text="s", summary_text=new)
        conn = app.get_db()
        cand = conn.execute(
            "SELECT status FROM supersession_candidates c JOIN memories m ON m.id = c.new_id "
            "WHERE m.kind = ?", (kind,),
        ).fetchone()
        conn.close()
        got = cand["status"] if cand else "none"
        results.append({"old": old, "new": new, "expected": expected, "got": got,
                        "similarity": raw_sim, "declared": app._declares_change(new)})

    correct = sum(1 for r in results if r["expected"] == r["got"])
    declared_floor = getattr(app, "MEMORY_SUPERSEDE_DECLARED_THRESHOLD", 0.0) or threshold
    print(f"supersession benchmark  floor={threshold}  declared_floor={declared_floor}  "
          f"{correct}/{len(results)} correct\n")
    for r in results:
        flag = "ok " if r["expected"] == r["got"] else "MISS"
        marker = "D" if r["declared"] else "-"
        print(f"  {flag} [{marker}] expected={r['expected']:<7} got={r['got']:<7} sim={r['similarity']:<6} | {r['new']}")
    out = os.environ.get("SUPERSESSION_BENCH_OUT")
    if out:
        Path(out).write_text(json.dumps({"threshold": threshold, "results": results}, indent=2), encoding="utf-8")
    try:
        os.unlink(tmp.name)
    except OSError:
        pass
    return 0 if correct == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Hermetic test for the Epoch X recall benchmark harness.

Runs the real seed→search→score pipeline against a temp DB with a deterministic
stub embedder (no Ollama), on a controlled fixture whose lexical overlap makes the
correct ranking deterministic. Validates the metric math, not model quality.
"""
import sqlite3

import app
from benchmarks.recall_benchmark import run_benchmark, stub_embedding

FIXTURE = {
    "name": "unit",
    "user_id": "bench-user",
    "memories": [
        {"id": "tm1", "kind": "t", "summary_text": "zebra apple orange", "source_text": "s", "created_at": "2026-01-01T00:00:00Z"},
        {"id": "tm2", "kind": "t", "summary_text": "banana mango grape", "source_text": "s", "created_at": "2026-01-02T00:00:00Z"},
        {"id": "tm3", "kind": "t", "summary_text": "carrot potato onion", "source_text": "s", "created_at": "2026-01-03T00:00:00Z"},
        {"id": "tm4", "kind": "t", "summary_text": "hydrogen helium lithium", "source_text": "s", "created_at": "2026-01-04T00:00:00Z"},
    ],
    "queries": [
        {"query": "zebra", "gold": ["tm1"]},
        {"query": "grape banana", "gold": ["tm2"]},
        {"query": "onion potato carrot", "gold": ["tm3"]},
        {"query": "banana mango onion", "gold": ["tm2", "tm3"]},
    ],
}


def _patch_db(monkeypatch, tmp_path):
    database = tmp_path / "bench.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(app, "get_db", fake_get_db)


def test_recall_benchmark_metrics(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    result = run_benchmark(app, FIXTURE, ks=(1, 2), embed_fn=stub_embedding)

    agg = result["aggregate"]
    assert result["per_query"][0]["query"] == "zebra"
    assert agg["queries"] == 4

    # Every query's first gold is ranked #1 (tm2 leads the double-gold query).
    assert agg["hit@1"] == 1.0
    assert agg["mrr"] == 1.0

    # recall@1: three single-gold queries hit fully; the double-gold query gets 1/2.
    assert agg["recall@k"][1] == (1 + 1 + 1 + 0.5) / 4
    # recall@2: the double-gold query's second gold shows up by rank 2.
    assert agg["recall@k"][2] == 1.0

    # Distractor tm4 is never a correct answer and never ranks first.
    assert all(r["top"][0] != "tm4" for r in result["per_query"])


def test_double_gold_query_ranking(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    result = run_benchmark(app, FIXTURE, ks=(1, 2), embed_fn=stub_embedding)

    q4 = next(r for r in result["per_query"] if r["query"] == "banana mango onion")
    assert q4["first_gold_rank"] == 1
    assert q4["top"][0] == "tm2"        # shares two tokens
    assert q4["recall@k"][1] == 0.5
    assert q4["recall@k"][2] == 1.0

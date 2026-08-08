"""Deterministic tests for Epoch X write-time supersession (ADR 0018).

Uses a temp DB and a controlled embedder so similarity — and therefore supersession — is
exact and predictable. No Ollama.
"""
import sqlite3

import app


def _setup(monkeypatch, tmp_path, threshold):
    database = tmp_path / "sup.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    def fake_embed(text):
        t = str(text).lower()
        if "coffee" in t:
            return [0.0, 1.0, 0.0]
        if "port" in t or "backend" in t or "8000" in t or "8001" in t:
            return [1.0, 0.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", fake_embed)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", threshold)
    app.init_db()


def _all_rows():
    conn = app.get_db()
    rows = conn.execute("SELECT summary_text, superseded, superseded_by FROM memories").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def test_new_fact_supersedes_prior_and_recall_returns_current(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8001")

    rows = _all_rows()
    assert len(rows) == 2  # both kept — reversible, not deleted
    superseded = [r for r in rows if r["superseded"]]
    assert len(superseded) == 1 and "8000" in superseded[0]["summary_text"]

    recalled = app.search_memories(query="what port is the backend on", conversation_id="c1", user_id="u1")
    assert len(recalled) == 1 and "8001" in recalled[0]["summary_text"]


def test_complementary_facts_are_not_superseded(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="operator likes coffee")  # orthogonal embedding

    rows = _all_rows()
    assert len(rows) == 2 and all(not r["superseded"] for r in rows)


def test_different_kind_is_not_superseded(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.9)
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="technical",
                    source_text="s", summary_text="backend on port 8001")  # same embedding, other kind

    rows = _all_rows()
    assert all(not r["superseded"] for r in rows)


def test_supersession_off_by_default(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, threshold=0.0)  # default
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8001")

    rows = _all_rows()
    assert all(not r["superseded"] for r in rows)  # nothing superseded when disabled
    recalled = app.search_memories(query="port", conversation_id="c1", user_id="u1")
    assert len(recalled) == 2  # both remain in active recall

"""Deterministic tests for Epoch X scoped retrieval (ADR 0019).

Two memories share an identical embedding (via a controlled embedder), so pure vector
similarity cannot tell them apart — only the scope ("room") can. Temp DB, no Ollama.
"""
import sqlite3

import app


def _setup(monkeypatch, tmp_path):
    database = tmp_path / "scoped.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    def fake_embed(text):
        # every "deadline" fact embeds identically -> vector can't disambiguate the room
        return [1.0, 0.0, 0.0] if "deadline" in str(text).lower() else [0.0, 0.0, 1.0]

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", fake_embed)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.0)  # keep both rows
    app.init_db()
    app.save_memory(conversation_id="c1", user_id="u1", kind="project",
                    source_text="s", summary_text="the deadline is Friday", scope="project-nova")
    app.save_memory(conversation_id="c1", user_id="u1", kind="project",
                    source_text="s", summary_text="the deadline is Tuesday", scope="project-orion")


def test_scope_recalls_within_the_room(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    nova = app.search_memories(query="when is the deadline", conversation_id="c1", user_id="u1", scope="project-nova")
    orion = app.search_memories(query="when is the deadline", conversation_id="c1", user_id="u1", scope="project-orion")
    assert len(nova) == 1 and "Friday" in nova[0]["summary_text"]
    assert len(orion) == 1 and "Tuesday" in orion[0]["summary_text"]


def test_no_scope_recalls_across_rooms(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    both = app.search_memories(query="when is the deadline", conversation_id="c1", user_id="u1")
    assert len(both) == 2  # backward compatible: no scope -> all rooms


def test_unknown_scope_returns_nothing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    empty = app.search_memories(query="when is the deadline", conversation_id="c1", user_id="u1", scope="project-vega")
    assert empty == []

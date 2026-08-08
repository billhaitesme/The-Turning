"""Deterministic tests for the Epoch X memory review surface (ADR 0022).

Rooms overview, filtered browsing, detail with audit events, re-rooming, and supersession
restore. Temp DB + controlled embedder; no Ollama.
"""
import sqlite3

import pytest
from fastapi import HTTPException

import app


def _setup(monkeypatch, tmp_path):
    database = tmp_path / "review.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    def fake_embed(text):
        return [1.0, 0.0, 0.0] if "port" in str(text).lower() else [0.0, 0.0, 1.0]

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", fake_embed)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.9)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_DECLARED_THRESHOLD", 0.5)
    app.init_db()
    # a room fact that gets superseded by a declared change, another room, and a global fact
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="backend on port 8000", scope="ops")
    app.save_memory(conversation_id="c1", user_id="u1", kind="config",
                    source_text="s", summary_text="the backend moved to port 8001", scope="ops")
    app.save_memory(conversation_id="c1", user_id="u1", kind="project",
                    source_text="s", summary_text="the deadline is Friday", scope="project-nova")
    app.save_memory(conversation_id="c1", user_id="u1", kind="preference",
                    source_text="s", summary_text="operator drinks coffee black")


def test_rooms_overview_counts(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    rooms = {r["scope"]: r for r in app.memory_rooms()}
    assert rooms["ops"]["active"] == 1 and rooms["ops"]["superseded"] == 1
    assert rooms["project-nova"]["active"] == 1
    assert rooms[None]["active"] == 1  # the global wing


def test_browse_filters(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    assert {m["summary_text"] for m in app.browse_memories(scope="ops")} == {"the backend moved to port 8001"}
    assert {m["summary_text"] for m in app.browse_memories(scope="ops", status="superseded")} == {"backend on port 8000"}
    assert len(app.browse_memories(scope="ops", status="all")) == 2
    assert {m["summary_text"] for m in app.browse_memories(unscoped=True)} == {"operator drinks coffee black"}
    assert {m["kind"] for m in app.browse_memories(kind="preference")} == {"preference"}
    assert {m["summary_text"] for m in app.browse_memories(q="deadline")} == {"the deadline is Friday"}
    assert all("embedding_json" not in m for m in app.browse_memories(status="all"))


def test_detail_rescope_and_events(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    target = app.browse_memories(q="deadline")[0]
    assert app.set_memory_scope(target["id"], "project-orion")
    detail = app.get_memory_detail(target["id"])
    assert detail["scope"] == "project-orion"
    assert any(e["event"] == "rescope" and "project-nova" in e["detail"] for e in detail["events"])
    # move to the global wing
    assert app.set_memory_scope(target["id"], None)
    assert app.get_memory_detail(target["id"])["scope"] is None
    assert not app.set_memory_scope("missing-id", "x")


def test_restore_reverses_supersession(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    old = app.browse_memories(scope="ops", status="superseded")[0]
    assert app.restore_memory(old["id"])
    detail = app.get_memory_detail(old["id"])
    assert not detail["superseded"] and detail["superseded_by"] is None
    assert any(e["event"] == "restore" for e in detail["events"])
    # back in active recall
    texts = {m["summary_text"] for m in app.search_memories(query="port", conversation_id="c1", user_id="u1", scope="ops")}
    assert "backend on port 8000" in texts
    # restoring an active memory is refused
    assert not app.restore_memory(old["id"])


def test_endpoint_handlers_404(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    with pytest.raises(HTTPException):
        app.get_memory_by_id("missing")
    with pytest.raises(HTTPException):
        app.post_memory_scope("missing", app.ConversationScopeRequest(scope="x"))
    with pytest.raises(HTTPException):
        app.post_memory_restore("missing")
    with pytest.raises(HTTPException):
        app.get_memory_browse(status="bogus")

"""Deterministic tests for Epoch X scope assignment (ADR 0020).

A conversation carries its memory room: memories born in it inherit the scope, recall
in it searches the room plus the global (unscoped) wing, and the scope is set only by
explicit action. Temp DB + controlled embedder; no Ollama.
"""
import sqlite3

import pytest
from fastapi import HTTPException

import app


def _setup(monkeypatch, tmp_path):
    database = tmp_path / "scope_assign.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    def fake_embed(text):
        t = str(text).lower()
        if "deadline" in t:
            return [1.0, 0.0, 0.0]
        if "coffee" in t:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", fake_embed)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.0)
    app.init_db()


def test_conversation_carries_scope_and_set_clear(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid = app.create_conversation(user_id="u1", scope="project-nova")
    assert app.get_conversation_meta(cid)["scope"] == "project-nova"
    app.set_conversation_scope(cid, "project-orion")
    assert app.get_conversation_meta(cid)["scope"] == "project-orion"
    app.set_conversation_scope(cid, None)
    assert app.get_conversation_meta(cid)["scope"] is None


def test_memories_inherit_conversation_scope_via_persist_learning(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid = app.create_conversation(user_id="u1", scope="project-nova")
    app.persist_learning(conversation_id=cid, user_id="u1",
                         user_message="the deadline is Friday",
                         assistant_message="Noted: the deadline is Friday.")
    conn = app.get_db()
    scopes = {row["scope"] for row in conn.execute("SELECT scope FROM memories").fetchall()}
    conn.close()
    assert scopes == {"project-nova"}  # every memory born in the room belongs to the room


def test_scoped_recall_includes_global_wing_and_excludes_other_rooms(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    # room fact, other-room fact (same embedding), and a global (unscoped) preference
    app.save_memory(conversation_id="c1", user_id="u1", kind="project",
                    source_text="s", summary_text="the deadline is Friday", scope="project-nova")
    app.save_memory(conversation_id="c1", user_id="u1", kind="project",
                    source_text="s", summary_text="the deadline is Tuesday", scope="project-orion")
    app.save_memory(conversation_id="c1", user_id="u1", kind="preference",
                    source_text="s", summary_text="operator drinks coffee black")  # no scope -> global

    got = app.search_memories(query="deadline and coffee", conversation_id="c1", user_id="u1",
                              scope="project-nova")
    texts = {m["summary_text"] for m in got}
    assert "the deadline is Friday" in texts          # the room
    assert "operator drinks coffee black" in texts     # the global wing
    assert "the deadline is Tuesday" not in texts      # the other room stays out

    strict = app.search_memories(query="deadline and coffee", conversation_id="c1", user_id="u1",
                                 scope="project-nova", include_global=False)
    assert {m["summary_text"] for m in strict} == {"the deadline is Friday"}


def test_scope_endpoint_sets_clears_and_404s(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cid = app.create_conversation(user_id="u1")
    resp = app.assign_conversation_scope(cid, app.ConversationScopeRequest(scope="project-nova"))
    assert resp.scope == "project-nova"
    assert app.get_conversation_meta(cid)["scope"] == "project-nova"
    resp = app.assign_conversation_scope(cid, app.ConversationScopeRequest(scope=None))
    assert resp.scope is None and app.get_conversation_meta(cid)["scope"] is None
    with pytest.raises(HTTPException):
        app.assign_conversation_scope("missing", app.ConversationScopeRequest(scope="x"))

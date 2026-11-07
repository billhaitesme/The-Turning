"""Ephemeral turns (operator direction 2026-11-07): a creative exchange OMEGA flags explicit —
or the operator marks private — leaves no logs or readables unless retention is explicitly
granted. Flagged turns live only for the session (continuity), are excluded from memories,
learning, evidence, and Recents previews, have their content withheld from the command log,
and are purged at every backend startup. Retention is one explicit operator act.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app
from services import agent_loop, command_console, escalation, network_breaker


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


YES = lambda prompt: "YES"  # noqa: E731
NO = lambda prompt: "NO"  # noqa: E731


def test_craft_route_flags_privacy_conservatively():
    # explicit lexicon and operator override: private, before any classifier runs
    assert escalation.craft_route("write me a dirty limerick", breaker_on=True, classify=YES) == ("local", True)
    assert escalation.craft_route("a poem, but keep this local", breaker_on=True, classify=YES) == ("local", True)
    # the local seat judging NOT cloud-safe IS the explicit flag
    assert escalation.craft_route("tell me a joke", breaker_on=True, classify=NO) == ("local", True)
    # clean verdicts: never private; the rung follows the breaker
    assert escalation.craft_route("tell me a joke", breaker_on=True, classify=YES) == ("claude", False)
    assert escalation.craft_route("tell me a joke", breaker_on=False, classify=YES) == ("local", False)
    # a dead classifier stays home but does not mark the turn private
    boom = lambda prompt: (_ for _ in ()).throw(RuntimeError("down"))  # noqa: E731
    assert escalation.craft_route("tell me a joke", breaker_on=True, classify=boom) == ("local", False)


def test_flagged_craft_turn_is_ephemeral_noticed_and_log_withheld(monkeypatch):
    calls = []

    def fake_execute(name, args, session_id, requested_by=agent_loop.AGENT_REQUESTED_BY,
                     log_output=True):
        calls.append({"args": args, "log_output": log_output})
        return {"status": "executed", "outcome": {"rung": args["rung"], "answer": "the piece"}}

    monkeypatch.setattr(agent_loop, "execute_tool_call", fake_execute)

    def seat(conversation, tools, model):
        yield {"type": "message", "content": "the piece", "tool_calls": []}

    network_breaker.set_breaker(False, changed_by="test", channel="test")
    events = list(agent_loop.iter_agent_loop(
        messages=[{"role": "user", "content": "write me a dirty limerick about sailors"}],
        model="t", session_id="c", seat_turn=seat))
    final = events[-1]
    assert final["ephemeral"] is True
    assert "ephemeral" in final["reply"]           # the operator is told, in the reply itself
    assert calls and calls[0]["args"]["rung"] == "local" and calls[0]["log_output"] is False


def test_clean_craft_turn_is_not_ephemeral(monkeypatch):
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id, requested_by=None, log_output=True:
                        {"status": "executed", "outcome": {"rung": args["rung"], "answer": "joke"}})
    monkeypatch.setattr(agent_loop, "_quick_seat_answer", lambda prompt, model: "YES")

    def seat(conversation, tools, model):
        yield {"type": "message", "content": "joke", "tool_calls": []}

    network_breaker.set_breaker(True, changed_by="test", channel="test")
    try:
        events = list(agent_loop.iter_agent_loop(
            messages=[{"role": "user", "content": "tell me a joke about lighthouses"}],
            model="t", session_id="c", seat_turn=seat))
    finally:
        network_breaker.set_breaker(False, changed_by="test", channel="test")
    assert events[-1]["ephemeral"] is False
    assert "ephemeral" not in events[-1]["reply"]


def test_console_withholds_the_outcome_but_returns_it(client):
    entry = command_console.initiate_command("run_host_status", requested_by="model:agent-seat",
                                             channel="chat", session_id="priv-test",
                                             log_output=False)
    assert entry["status"] == "executed"
    assert entry["outcome"]["output"]["psutil_available"] in (True, False)  # caller sees the truth
    logged = next(e for e in command_console.load_command_log()["commands"]
                  if e["command_id"] == entry["command_id"])
    assert logged["outcome"] == {"withheld": "ephemeral by privacy policy — the act is recorded, "
                                             "the content is not (operator direction 2026-11-07)"}


def test_ephemeral_messages_hide_from_recents_and_purge_at_startup(client):
    cid = client.post("/conversations", json={"user_id": "demo", "title": "priv"}).json()["conversation_id"]
    app_module.add_message(cid, "user", "a clean question")
    app_module.add_message(cid, "assistant", "a clean answer")
    app_module.add_message(cid, "user", "the secret ask")
    app_module.mark_last_user_message_ephemeral(cid)
    app_module.add_message(cid, "assistant", "the secret piece", ephemeral=True)
    # recents never previews the flagged content
    entry = next(c for c in client.get("/conversations?limit=100").json()["conversations"] if c["id"] == cid)
    assert entry["preview"].startswith("a clean question") and entry["message_count"] == 2
    # the session still has continuity while it lives
    history = client.get(f"/conversations/{cid}").json()["messages"]
    assert any("secret piece" in m["content"] for m in history)
    # startup purge: the flagged turns are gone, the clean ones stay
    purged = app_module.purge_ephemeral()
    assert purged == 2
    history = client.get(f"/conversations/{cid}").json()["messages"]
    assert not any("secret" in m["content"] for m in history)
    assert any("clean answer" in m["content"] for m in history)


def test_retention_is_an_explicit_operator_act(client):
    cid = client.post("/conversations", json={"user_id": "demo", "title": "keep"}).json()["conversation_id"]
    app_module.add_message(cid, "user", "the keeper", ephemeral=True)
    r = client.post(f"/conversations/{cid}/retain")
    assert r.status_code == 200 and r.json()["retained"] == 1
    assert app_module.purge_ephemeral() == 0  # retained turns survive the sweep
    history = client.get(f"/conversations/{cid}").json()["messages"]
    assert any("the keeper" in m["content"] for m in history)
    assert client.post("/conversations/conv-nope/retain").status_code == 404

"""Epoch XIII-C — the Mind Ladder's rungs 2 and 3 (deep_think).

Rung 'local' thinks in system RAM, no breaker. Rung 'frontier' is a network egress: it executes
only while the breaker is ON, lands in the fetch log, and refuses plainly without a key. Privacy
is structural: only the composed task/context strings reach a rung. Unavailability is a 422
refusal, never a fake failure.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services import network_breaker
from services.adapters.deep_think import DeepThinkAdapter
from services.tool_registry import TOOL_REGISTRY


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def breaker_off_by_default():
    network_breaker.set_breaker(False, changed_by="test:reset", channel="test")
    yield


def test_local_rung_executes_without_the_breaker(client):
    seen = {}

    def fake_local(prompt):
        seen["prompt"] = prompt
        return "deep-local-test", "Thought it through: do X then Y."

    TOOL_REGISTRY["deep_think"]["adapter"]._local_fn = fake_local
    r = client.post("/system/commands/deep_think",
                    json={"arguments": {"task": "plan the lighthouse build"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["rung"] == "local" and output["model"] == "deep-local-test"
    assert "do X then Y" in output["answer"]
    # privacy is structural: the rung saw the composed task and nothing else
    assert "plan the lighthouse build" in seen["prompt"]
    assert "CONTEXT" not in seen["prompt"]  # none was given, none was invented


def test_frontier_rung_is_breaker_gated_and_logged(client):
    TOOL_REGISTRY["deep_think"]["adapter"]._frontier_fn = lambda prompt: ("groq-test-model", "Frontier verdict.")
    # breaker off -> refusal, nothing sent, nothing logged
    r = client.post("/system/commands/deep_think",
                    json={"arguments": {"task": "compare the two designs", "rung": "frontier"}})
    assert r.status_code == 422 and "breaker is OFF" in r.json()["detail"]
    # breaker on -> executes and lands in the fetch log as an egress
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    r = client.post("/system/commands/deep_think",
                    json={"arguments": {"task": "compare the two designs", "rung": "frontier"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["rung"] == "frontier" and output["answer"] == "Frontier verdict."
    entry = network_breaker.list_fetch_log()[0]
    assert entry["kind"] == "frontier" and entry["target"] == "groq:groq-test-model"


def test_claude_rung_writes_and_is_logged(client):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    TOOL_REGISTRY["deep_think"]["adapter"]._claude_fn = lambda prompt: ("sonnet", "A tight joke.")
    r = client.post("/system/commands/deep_think",
                    json={"arguments": {"task": "WRITE one joke about lighthouses", "rung": "claude"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["rung"] == "claude" and output["answer"] == "A tight joke."
    entry = network_breaker.list_fetch_log()[0]
    assert entry["kind"] == "claude" and entry["ok"]


def test_claude_rung_decline_falls_back_to_the_local_gear(client):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    adapter = TOOL_REGISTRY["deep_think"]["adapter"]
    adapter._claude_fn = lambda prompt: (_ for _ in ()).throw(ValueError("declined"))
    adapter._local_fn = lambda prompt: ("local-30b", "The local gear wrote it.")
    r = client.post("/system/commands/deep_think",
                    json={"arguments": {"task": "WRITE one joke", "rung": "claude"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["rung"] == "local" and output["answer"] == "The local gear wrote it."
    assert "LOCAL gear wrote this instead" in output["note"]


def test_claude_rung_is_breaker_gated(client):
    r = client.post("/system/commands/deep_think",
                    json={"arguments": {"task": "WRITE one joke", "rung": "claude"}})
    assert r.status_code == 422 and "breaker is OFF" in r.json()["detail"]


def test_frontier_without_a_key_refuses_plainly(client, monkeypatch):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    adapter = DeepThinkAdapter()  # real frontier fn, no key — refuses before any network use
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        adapter.execute({"task": "anything", "rung": "frontier"})


def test_arguments_are_validated_and_capped():
    adapter = DeepThinkAdapter(local_fn=lambda p: ("m", "a"), frontier_fn=lambda p: ("m", "a"))
    with pytest.raises(ValueError, match="non-empty 'task'"):
        adapter.execute({})
    with pytest.raises(ValueError, match="rung must be one of"):
        adapter.execute({"task": "x", "rung": "orbital"})
    with pytest.raises(ValueError, match="capped"):
        adapter.execute({"task": "x" * 7000})


def test_unavailable_local_model_is_a_refusal_not_a_failure(client):
    def unavailable(prompt):
        raise ValueError("deep rung 'local' is unavailable: model not pulled yet.")

    TOOL_REGISTRY["deep_think"]["adapter"]._local_fn = unavailable
    r = client.post("/system/commands/deep_think", json={"arguments": {"task": "think"}})
    assert r.status_code == 422
    assert "not pulled" in r.json()["detail"]

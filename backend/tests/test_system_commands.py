"""XIII-A — the desktop web console's commands surface (/system/commands).

The web console renders the registry it is given (ADR 0015): categories come from the registry,
direct commands execute on initiate, approval commands enter IX-C and wait for the mobile
biometric (desktop cannot self-approve), forbidden commands are refused and recorded.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services import command_registry


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


def test_registry_commands_all_carry_categories(client):
    payload = client.get("/system/commands").json()
    assert payload["execution_enabled"] in (True, False)
    commands = payload["commands"]
    assert {c["name"] for c in commands} == {c["name"] for c in command_registry.list_commands()}
    assert all(str(c.get("category") or "").strip() for c in commands)
    by_name = {c["name"]: c for c in commands}
    assert by_name["run_comfyui_status"]["category"] == "image-forge"
    assert by_name["run_host_status"]["category"] == "host"


def test_desktop_initiates_direct_command_and_it_is_logged(client):
    r = client.post("/system/commands/run_host_status", json={})
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "executed" and entry["channel"] == "desktop"
    assert entry["requested_by"] == "operator:desktop"
    history = client.get("/system/commands/history").json()["history"]
    assert any(h["command_id"] == entry["command_id"] for h in history)


def test_desktop_approval_command_waits_for_the_mobile_biometric(client):
    r = client.post("/system/commands/run_backend_health_check", json={})
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "awaiting_approval"
    assert entry["request_id"] and entry["approval_id"]  # IX-C pipeline, nothing executed


def test_pending_approval_is_idempotent_not_duplicated(client):
    # Re-asking while an identical command awaits approval returns the SAME pending entry
    # (XIII-A: the chat seat may repeat itself; the approval queue must not grow).
    first = client.post("/system/commands/run_backend_health_check", json={}).json()["command"]
    second = client.post("/system/commands/run_backend_health_check", json={}).json()["command"]
    assert second["command_id"] == first["command_id"]
    assert second["request_id"] == first["request_id"]


def test_approval_status_reads_the_pipeline_truth(client):
    # raise a gated request, then the read must report it pending with no biometric landed
    client.post("/system/commands/run_backend_health_check", json={})
    r = client.post("/system/commands/check_approval_status", json={})
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "executed" and entry["gate"] == "direct"
    output = entry["outcome"]["output"]
    assert output["pending_count"] >= 1
    pending = next(p for p in output["pending"] if p["tool_name"] == "backend_health_check")
    assert pending["request_status"] == "awaiting_approval"
    assert pending["biometric_confirmed"] is False


def test_desktop_forbidden_command_is_refused(client):
    r = client.post("/system/commands/change_conversational_routing", json={})
    assert r.status_code == 403
    assert client.post("/system/commands/nope", json={}).status_code == 404


def test_status_reports_version_and_agent_loop_flag(client, monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_LOOP", "true")
    payload = client.get("/system/status").json()
    assert payload["version"] == app.version
    assert payload["agent_loop_enabled"] is True
    assert payload["model_control"]["active_model"]

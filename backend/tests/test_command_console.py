"""Epoch IX-D slice 1 — the Command Console (ADR 0015).

Three commands, one per gate. The approval-gated path runs end-to-end through the IX-C
pipeline, and a high-risk command cannot execute without a biometric-confirmed operator
approval — a desktop /system approval does not release it. Every attempt is logged."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app
from services import command_console, command_registry
from services.tool_approval import list_tool_approvals, load_tool_request_store
from services.tool_results import load_tool_result_store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOBILE_AUTH_TOKEN", "test-secret")
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


AUTH = {"Authorization": "Bearer test-secret"}


def _history(client):
    return client.get("/api/mobile/v1/commands/history", headers=AUTH).json()["history"]


def test_registry_covers_every_gate_and_polices_itself():
    gates = {c["gate"] for c in command_registry.list_commands()}
    assert gates == {"direct", "approval", "forbidden"}
    command_registry.validate_registry()  # the registry polices its own rules


def test_host_status_is_low_direct_and_maps_to_a_readonly_tool():
    # Slice 4's first broadening: a direct command may map to a bounded tool, but only a read-only
    # one may direct-execute — the console enforces the side-effect guard.
    from services.tool_registry import get_tool
    command = command_registry.get_command("run_host_status")
    assert command["gate"] == "direct" and command["risk"] == "low"
    descriptor = (get_tool(command["tool_name"]) or {}).get("descriptor") or {}
    assert descriptor.get("side_effects") == []


def test_host_status_direct_executes_with_real_vitals_and_is_logged(client):
    r = client.post("/api/mobile/v1/commands/run_host_status", headers=AUTH)
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "executed" and entry["gate"] == "direct"
    output = entry["outcome"]["output"]
    # A real read: either psutil vitals or an explicit unavailable marker — never silent emptiness.
    assert output["psutil_available"] in (True, False)
    if output["psutil_available"]:
        assert output["ram_total_bytes"] > 0 and "cpu_percent" in output
    assert any(h["command_id"] == entry["command_id"] and h["status"] == "executed"
               for h in _history(client))


def test_comfyui_status_is_low_direct_and_readonly():
    from services.tool_registry import get_tool
    command = command_registry.get_command("run_comfyui_status")
    assert command["gate"] == "direct" and command["risk"] == "low"
    descriptor = (get_tool(command["tool_name"]) or {}).get("descriptor") or {}
    assert descriptor.get("side_effects") == []


def test_comfyui_status_direct_executes_and_reports_reachability(client):
    # ComfyUI is usually off; the command must still succeed and report reachable=false rather
    # than erroring — an unreachable ComfyUI is a normal reported state, not a failure.
    r = client.post("/api/mobile/v1/commands/run_comfyui_status", headers=AUTH)
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "executed" and entry["gate"] == "direct"
    output = entry["outcome"]["output"]
    assert output["reachable"] in (True, False)
    if output["reachable"]:
        assert output["queue_total"] >= 0
    else:
        assert "detail" in output  # says why, never silent
    assert any(h["command_id"] == entry["command_id"] and h["status"] == "executed"
               for h in _history(client))


def test_mobile_renders_the_registry_it_does_not_define(client):
    payload = client.get("/api/mobile/v1/commands", headers=AUTH).json()
    names = {c["name"] for c in payload["commands"]}
    assert {"new_conversation", "run_backend_health_check", "change_conversational_routing"} <= names
    assert client.get("/api/mobile/v1/commands").status_code == 401  # bearer required


def test_direct_command_executes_and_is_logged(client):
    r = client.post("/api/mobile/v1/commands/new_conversation", headers=AUTH,
                    json={"arguments": {"title": "IX-D smoke"}})
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "executed" and entry["gate"] == "direct"
    assert entry["outcome"]["conversation_id"]
    assert any(h["command_id"] == entry["command_id"] for h in _history(client))


def test_forbidden_command_is_refused_and_recorded(client):
    r = client.post("/api/mobile/v1/commands/change_conversational_routing", headers=AUTH)
    assert r.status_code == 403
    assert any(h["name"] == "change_conversational_routing" and h["status"] == "forbidden"
               for h in _history(client))
    assert client.post("/api/mobile/v1/commands/does_not_exist", headers=AUTH).status_code == 404


def test_gated_command_needs_biometric_approval_end_to_end(client, monkeypatch):
    # No network in tests: the adapter's execute is replaced with a canned healthy result.
    monkeypatch.setattr(app_module.BackendHealthCheckAdapter, "execute",
                        lambda self, args: {"target": "backend", "checked_url": "http://127.0.0.1:8001/health",
                                            "success": True, "status_code": 200, "latency_ms": 1.5,
                                            "checked_at": "2026-08-17T00:00:00+00:00"})
    results_before = len(load_tool_result_store().get("results", []))

    r = client.post("/api/mobile/v1/commands/run_backend_health_check", headers=AUTH)
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "awaiting_approval" and entry["request_id"] and entry["approval_id"]
    request_id = entry["request_id"]

    # 1. it is now a real IX-C tool request awaiting approval — nothing has executed
    req = next(x for x in load_tool_request_store()["requests"] if x["request_id"] == request_id)
    assert req["status"] == "awaiting_approval" and req["requested_by"] == "operator:mobile"
    assert len(load_tool_result_store().get("results", [])) == results_before
    pending = client.get("/api/mobile/v1/approvals", headers=AUTH).json()["approvals"]
    assert any(p["request_id"] == request_id for p in pending)

    # 2. a DESKTOP approval (no biometric confirmation) does NOT release the command
    r = client.post(f"/system/tool-requests/{request_id}/approve", json={"approved_by": "desktop-operator"})
    assert r.status_code == 200
    command_console.on_request_approved(request_id)  # what a desktop surface could at most call
    entry = next(h for h in _history(client) if h["request_id"] == request_id)
    assert entry["status"] == "awaiting_approval"
    assert "biometric" in entry["outcome"]["note"]
    assert len(load_tool_result_store().get("results", [])) == results_before

    # 3. the MOBILE approve route (biometric-confirmed) releases it -> executes -> logged
    r = client.post(f"/api/mobile/v1/approvals/{request_id}/approve", headers=AUTH, json={"confirmed": True})
    assert r.status_code == 200, r.text
    approval = r.json()["approval"]
    assert approval["confirmation"] == "biometric"
    cmd = r.json()["command"]
    assert cmd["status"] == "executed", cmd
    assert cmd["outcome"]["success"] is True
    assert len(load_tool_result_store().get("results", [])) == results_before + 1
    # the single-use approval is consumed
    a = next(x for x in list_tool_approvals() if x["request_id"] == request_id)
    assert a["consumed_at"]


def test_comfyui_render_is_gated_because_it_has_side_effects():
    # The submit tool changes state (queues GPU work), so it must NOT be direct — the registry
    # classifies it approval-gated, and its tool declares a non-empty side_effects list.
    from services.tool_registry import get_tool
    command = command_registry.get_command("run_comfyui_render")
    assert command["gate"] == "approval" and command["risk"] == "medium"
    descriptor = (get_tool(command["tool_name"]) or {}).get("descriptor") or {}
    assert descriptor.get("side_effects")  # non-empty


def test_comfyui_render_gated_path_runs_the_adapter_on_biometric_approval(client, monkeypatch):
    # No network in tests: the submit adapter's execute returns a canned queued result. This proves
    # the generalized gated executor runs an arbitrary bounded tool's adapter (not just health check)
    # and records its output — only after a biometric-confirmed approval.
    from services.adapters.comfyui_submit import ComfyUISubmitAdapter
    monkeypatch.setattr(ComfyUISubmitAdapter, "execute",
                        lambda self, args: {"submitted": True, "prompt_id": "pid-123", "queue_number": 1,
                                            "workflow": "sdxl_lightning_txt2img", "checkpoint": "dreamshaperXL.safetensors",
                                            "seed": 42, "prompt": args.get("prompt")})
    r = client.post("/api/mobile/v1/commands/run_comfyui_render", headers=AUTH)
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["status"] == "awaiting_approval" and entry["request_id"]
    request_id = entry["request_id"]

    # a desktop (non-biometric) approval must not release it
    client.post(f"/system/tool-requests/{request_id}/approve", json={"approved_by": "desktop"})
    command_console.on_request_approved(request_id)
    assert next(h for h in _history(client) if h["request_id"] == request_id)["status"] == "awaiting_approval"

    # the mobile biometric approval releases it -> the adapter runs -> the queued id is recorded
    r = client.post(f"/api/mobile/v1/approvals/{request_id}/approve", headers=AUTH, json={"confirmed": True})
    assert r.status_code == 200, r.text
    cmd = r.json()["command"]
    assert cmd["status"] == "executed", cmd
    assert cmd["outcome"]["output"]["submitted"] is True
    assert cmd["outcome"]["output"]["prompt_id"] == "pid-123"


def test_comfyui_submit_validates_its_arguments():
    from services.adapters.comfyui_submit import ComfyUISubmitAdapter
    adapter = ComfyUISubmitAdapter()
    import pytest as _pytest
    with _pytest.raises(ValueError):
        adapter.validate_arguments({})  # missing prompt
    with _pytest.raises(ValueError):
        adapter.validate_arguments({"prompt": "x", "workflow": "does-not-exist"})
    ok = adapter.validate_arguments({"prompt": "  a cat  ", "seed": 7, "steps": 6})
    assert ok["prompt"] == "a cat" and ok["seed"] == 7 and ok["workflow"] == "sdxl_lightning_txt2img"


def test_comfyui_submit_builds_workflow_from_template():
    # The template patches the real node graph, not string placeholders — prove the prompt lands.
    from services.adapters.comfyui_submit import ComfyUISubmitAdapter
    adapter = ComfyUISubmitAdapter()
    built = adapter._build_workflow(adapter.validate_arguments({"prompt": "a red bicycle", "seed": 5}))
    wf = built["workflow"]
    assert wf["6"]["inputs"]["text"] == "a red bicycle"
    assert wf["3"]["inputs"]["seed"] == 5
    assert built["checkpoint"].endswith(".safetensors")


def test_mobile_approve_without_confirmed_flag_is_rejected(client):
    r = client.post("/api/mobile/v1/commands/run_backend_health_check", headers=AUTH)
    request_id = r.json()["command"]["request_id"]
    r = client.post(f"/api/mobile/v1/approvals/{request_id}/approve", headers=AUTH, json={"confirmed": False})
    assert r.status_code == 400
    entry = next(h for h in _history(client) if h["request_id"] == request_id)
    assert entry["status"] == "awaiting_approval"


def test_deny_discards_the_command(client):
    r = client.post("/api/mobile/v1/commands/run_backend_health_check", headers=AUTH)
    request_id = r.json()["command"]["request_id"]
    r = client.post(f"/api/mobile/v1/approvals/{request_id}/deny", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["command"]["status"] == "denied"


def test_execution_policy_switch_is_honoured(client, monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "false")
    r = client.post("/api/mobile/v1/commands/run_backend_health_check", headers=AUTH)
    request_id = r.json()["command"]["request_id"]
    r = client.post(f"/api/mobile/v1/approvals/{request_id}/approve", headers=AUTH, json={"confirmed": True})
    assert r.status_code == 200
    assert r.json()["command"]["status"] == "failed"
    assert "COMMAND_EXECUTION" in r.json()["command"]["outcome"]["error"]


def test_desktop_surface_can_initiate_but_gated_commands_wait_for_mobile(client):
    r = client.post("/system/commands/run_backend_health_check", json={})
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["channel"] == "desktop" and entry["status"] == "awaiting_approval"
    assert client.get("/system/commands").json()["commands"]
    assert any(h["command_id"] == entry["command_id"] for h in client.get("/system/commands/history").json()["history"])

"""Epoch XIII-A — the agent loop (ADR 0026).

The chat seat emits structured tool calls; the deterministic runtime resolves every one against
the command registry through the command console, under the consoles' own gates. Direct reads
execute, side effects wait for the biometric approval, forbidden and unknown calls are refused
and recorded, and the loop's budget bounds hops and result bytes. No free-form execution exists.
"""
from __future__ import annotations

import json

import pytest

from services import agent_loop, command_console, command_registry
from services.tool_approval import load_tool_request_store


# --------------------------------------------------------------------------- scripted seat
def scripted_seat(turns):
    """A fake seat: one scripted turn per model call; records what it was sent."""
    remaining = list(turns)

    def seat(conversation, tools, model):
        seat.calls.append({"conversation": [dict(m) for m in conversation],
                           "tools": tools, "model": model})
        turn = remaining.pop(0)
        if turn.get("raise_unsupported") and tools is not None:
            def raising():
                raise agent_loop.ToolsUnsupportedError("no tools")
                yield  # pragma: no cover
            return raising()

        def gen():
            content = turn.get("content") or ""
            if content:
                yield {"type": "delta", "text": content}
            yield {"type": "message", "content": content,
                   "tool_calls": turn.get("tool_calls") or [],
                   "eval_count": turn.get("eval_count")}
        return gen()

    seat.calls = []
    return seat


def tool_call(name, arguments=None):
    return {"function": {"name": name, "arguments": arguments or {}}}


def run(turns, **env):
    seat = scripted_seat(turns)
    final = agent_loop.run_agent_loop(messages=[{"role": "system", "content": "sys"},
                                                {"role": "user", "content": "hi"}],
                                      model="test-seat", session_id="conv-xiii-a", seat_turn=seat)
    return final, seat


def _log_entries():
    return command_console.load_command_log().get("commands", [])


# --------------------------------------------------------------------------- schemas
def test_schemas_render_the_registry_and_never_advertise_forbidden():
    schemas = agent_loop.build_tool_schemas()
    names = {s["function"]["name"] for s in schemas}
    registry = {c["name"]: c for c in command_registry.list_commands()}
    assert "change_conversational_routing" not in names  # forbidden is not advertised
    assert names == {n for n, c in registry.items() if c["gate"] != "forbidden"}

    render = next(s["function"] for s in schemas if s["function"]["name"] == "run_comfyui_render")
    props = render["parameters"]["properties"]
    assert props["prompt"]["type"] == "string" and "prompt" in render["parameters"]["required"]
    assert props["steps"]["type"] == "integer" and props["steps"]["minimum"] == 1
    assert "biometric approval" in render["description"]  # the gate is in the seat's own view
    host = next(s["function"] for s in schemas if s["function"]["name"] == "run_host_status")
    assert "read-only" in host["description"]


# --------------------------------------------------------------------------- the four gates
def test_direct_read_executes_through_the_console_and_is_logged_channel_chat():
    final, seat = run([
        {"content": "Checking.", "tool_calls": [tool_call("run_host_status")]},
        {"content": "CPU is fine."},
    ])
    assert final["reply"].startswith("Checking.") and final["reply"].endswith("CPU is fine.")
    assert final["hops"] == [{"tool": "run_host_status", "status": "executed"}]
    # the result the seat saw is the real adapter output, fed back as a tool message
    tool_messages = [m for m in seat.calls[1]["conversation"] if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    payload = json.loads(tool_messages[0]["content"])
    assert payload["status"] == "executed"
    assert payload["outcome"]["output"]["psutil_available"] in (True, False)
    entry = next(e for e in _log_entries() if e.get("session_id") == "conv-xiii-a"
                 and e.get("name") == "run_host_status")
    assert entry["channel"] == "chat" and entry["requested_by"] == "model:agent-seat"
    assert entry["status"] == "executed"


def test_side_effecting_call_waits_for_the_biometric_approval_nothing_executes():
    final, seat = run([
        {"tool_calls": [tool_call("run_comfyui_render", {"prompt": "a red fox", "steps": 4})]},
        {"content": "The render is waiting for your approval on the phone."},
    ])
    assert final["hops"] == [{"tool": "run_comfyui_render", "status": "awaiting_approval"}]
    payload = json.loads(next(m for m in seat.calls[1]["conversation"] if m.get("role") == "tool")["content"])
    assert payload["status"] == "awaiting_approval" and payload["approval_id"]
    assert "do not claim it ran" in payload["detail"]
    # a real IX-C tool request exists, awaiting approval — and the model's junk args were dropped
    request = next(r for r in load_tool_request_store()["requests"]
                   if r.get("session_id") == "conv-xiii-a" and r["tool_name"] == "comfyui_submit")
    assert request["status"] == "awaiting_approval"
    assert request["arguments"]["prompt"] == "a red fox" and request["arguments"]["steps"] == 4


def test_forbidden_call_is_refused_fed_back_and_recorded():
    final, seat = run([
        {"tool_calls": [tool_call("change_conversational_routing")]},
        {"content": "I cannot do that; Model Lock forbids it."},
    ])
    assert final["hops"] == [{"tool": "change_conversational_routing", "status": "refused"}]
    payload = json.loads(next(m for m in seat.calls[1]["conversation"] if m.get("role") == "tool")["content"])
    assert payload["status"] == "refused" and "forbidden" in payload["detail"].lower()
    assert any(e["name"] == "change_conversational_routing" and e["status"] == "forbidden"
               and e["channel"] == "chat" for e in _log_entries())


def test_unknown_call_is_refused_and_recorded_no_free_form_execution():
    final, seat = run([
        {"tool_calls": [tool_call("delete_all_files", {"path": "C:/"})]},
        {"content": "No such command exists."},
    ])
    assert final["hops"] == [{"tool": "delete_all_files", "status": "refused"}]
    payload = json.loads(next(m for m in seat.calls[1]["conversation"] if m.get("role") == "tool")["content"])
    assert payload["status"] == "refused" and "registry is the authority" in payload["detail"]
    entry = next(e for e in _log_entries() if e.get("name") == "delete_all_files")
    assert entry["status"] == "refused" and entry["gate"] == "unknown" and entry["channel"] == "chat"


# --------------------------------------------------------------------------- bounds and honesty
def test_hop_budget_bounds_the_loop_and_forces_a_final_answer(monkeypatch):
    monkeypatch.setenv("AGENT_LOOP_MAX_HOPS", "2")
    # a seat that would call tools forever — even on the forced final turn
    turns = [{"tool_calls": [tool_call("run_host_status")]} for _ in range(3)]
    final, seat = run(turns)
    assert len(seat.calls) == 3                      # 2 budgeted rounds + 1 forced final
    assert seat.calls[-1]["tools"] is None           # the final turn offers no tools
    assert len(final["hops"]) == 2                   # the third turn's calls were ignored
    budget_notes = [m for m in seat.calls[-1]["conversation"]
                    if m.get("role") == "system" and "budget" in m.get("content", "")]
    assert budget_notes, "the seat is told the budget is spent"


def test_tool_results_into_context_are_size_capped(monkeypatch):
    monkeypatch.setenv("AGENT_LOOP_RESULT_MAX_CHARS", "200")
    monkeypatch.setattr(agent_loop, "execute_tool_call",
                        lambda name, args, session_id: {"status": "executed",
                                                        "outcome": "x" * 5000 + "FINAL ANSWER 13/27"})
    final, seat = run([
        {"tool_calls": [tool_call("run_host_status")]},
        {"content": "done"},
    ])
    tool_message = next(m for m in seat.calls[1]["conversation"] if m.get("role") == "tool")
    assert len(tool_message["content"]) < 300
    assert "chars cut to fit" in tool_message["content"]
    # the tail survives: a deep answer's conclusion is at its end
    assert "FINAL ANSWER 13/27" in tool_message["content"]


def test_seat_without_tool_support_degrades_honestly():
    final, seat = run([
        {"raise_unsupported": True},
        {"content": "Plain answer, no hands."},
    ])
    assert final["reply"] == "Plain answer, no hands."
    assert final["seat_supports_tools"] is False and final["hops"] == []
    assert seat.calls[-1]["tools"] is None  # the retry went out without schemas


def test_string_encoded_arguments_are_parsed_and_junk_keys_dropped():
    final, seat = run([
        {"tool_calls": [{"function": {"name": "run_comfyui_render",
                                      "arguments": json.dumps({"prompt": "a boat", "rm": "-rf"})}}]},
        {"content": "waiting"},
    ])
    request = next(r for r in load_tool_request_store()["requests"]
                   if r.get("session_id") == "conv-xiii-a" and r["arguments"].get("prompt") == "a boat")
    assert "rm" not in request["arguments"]


# --------------------------------------------------------------------------- policy switch
def test_loop_is_off_by_default_and_env_switched(monkeypatch):
    monkeypatch.delenv("ENABLE_AGENT_LOOP", raising=False)
    assert agent_loop.agent_loop_enabled() is False
    monkeypatch.setenv("ENABLE_AGENT_LOOP", "true")
    assert agent_loop.agent_loop_enabled() is True

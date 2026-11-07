"""Command console (ADR 0015, Epoch IX-D) — operators *initiate* bounded runtime commands.

Every command flows through the existing gates with no new authority:

  * A command is a proposal until policy permits execution (ADR-IX-002: the runtime owns execution).
  * Approval-gated commands become IX-C tool requests. They execute ONLY when the approval carries a
    biometric confirmation — which only the mobile approve route sets. A desktop /system approval,
    or any approval without that confirmation, does not release a command (the ADR's "desktop cannot
    self-approve a sensitive action").
  * Forbidden commands are refused, and the refusal is recorded.
  * Every command, its requester, channel, approval, and outcome is written to the command log
    (the Covenant test: explain why / reverse / preserve history).

Policy recorded with IX-D: gated command execution is ON by default (COMMAND_EXECUTION=true) even
while the chat-triggered tool path stays behind ENABLE_TOOL_EXECUTION — because here every
execution has just passed a biometric-confirmed operator approval.
"""
from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from services import command_registry
from services.adapters.backend_health_check import BackendHealthCheckAdapter
from services.tool_approval import (
    create_approval_request,
    get_tool_request,
    list_tool_approvals,
    load_tool_approval_store,
    load_tool_request_store,
)
from services.tool_contracts import build_tool_request, utc_now_iso
from services.tool_evidence_bridge import execute_backend_health_check_request
from services.tool_results import load_tool_result_store

BIOMETRIC_CONFIRMATION = "biometric"


def command_execution_enabled() -> bool:
    return os.getenv("COMMAND_EXECUTION", "true").strip().lower() == "true"


# ----------------------------------------------------------------------------- runtime bindings
_create_conversation: Optional[Callable[..., str]] = None


def configure(*, create_conversation: Callable[..., str]) -> None:
    """Bind the console to the running application (called once at startup)."""
    global _create_conversation
    _create_conversation = create_conversation


# ----------------------------------------------------------------------------- command log
def _log_path() -> Path:
    # Resolved at call time so tests that redirect OMEGA_TOOL_DATA_DIR stay hermetic.
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "command_log.json"


def load_command_log() -> Dict[str, Any]:
    path = _log_path()
    if not path.exists():
        return {"version": 1, "commands": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "commands": []}
    if not isinstance(data, dict) or not isinstance(data.get("commands"), list):
        return {"version": 1, "commands": []}
    return data


def save_command_log(store: Dict[str, Any]) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "commands": store.get("commands", [])}, indent=2,
                               ensure_ascii=False), encoding="utf-8")


def list_command_history(limit: int = 50) -> List[Dict[str, Any]]:
    entries = _refresh_expired(load_command_log().get("commands", []))
    entries.sort(key=lambda e: e.get("requested_at") or "", reverse=True)
    return deepcopy(entries[:limit])


def _upsert(entry: Dict[str, Any]) -> Dict[str, Any]:
    store = load_command_log()
    commands = store.setdefault("commands", [])
    for i, existing in enumerate(commands):
        if existing.get("command_id") == entry["command_id"]:
            commands[i] = deepcopy(entry)
            break
    else:
        commands.append(deepcopy(entry))
    save_command_log(store)
    return deepcopy(entry)


def _find_by_request(request_id: str) -> Optional[Dict[str, Any]]:
    for entry in load_command_log().get("commands", []):
        if entry.get("request_id") == request_id:
            return deepcopy(entry)
    return None


def _refresh_expired(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Awaiting-approval entries whose approval has expired are marked expired (read-side, idempotent)."""
    approvals = {a.get("request_id"): a for a in list_tool_approvals()}
    changed = False
    for entry in entries:
        if entry.get("status") == "awaiting_approval":
            approval = approvals.get(entry.get("request_id"))
            if approval and approval.get("status") == "expired":
                entry["status"] = "expired"
                entry["finished_at"] = approval.get("expires_at")
                changed = True
    if changed:
        save_command_log({"version": 1, "commands": entries})
    return entries


# ----------------------------------------------------------------------------- XIII-A refusals
def record_refused_chat_call(name: str, *, reason: str, requested_by: str,
                             session_id: Optional[str] = None) -> Dict[str, Any]:
    """A model-emitted tool call that does not validate against the registry is refused AND
    recorded (ADR 0026) — the refusal trail is part of the agency record, like every other
    command outcome. Nothing executes on this path."""
    entry = {
        "command_id": f"cmd-{uuid.uuid4().hex}",
        "name": str(name)[:120],
        "risk": "unknown",
        "gate": "unknown",
        "requested_by": requested_by,
        "channel": "chat",
        "session_id": session_id or "chat",
        "requested_at": utc_now_iso(),
        "request_id": None,
        "approval_id": None,
        "status": "refused",
        "outcome": {"reason": reason},
        "finished_at": utc_now_iso(),
    }
    return _upsert(entry)


# ----------------------------------------------------------------------------- initiate
class CommandError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def initiate_command(name: str, *, requested_by: str, channel: str, session_id: Optional[str] = None,
                     arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Operator initiates a command. Returns the command-log entry.

    direct    -> executed now, outcome recorded.
    approval  -> tool request + IX-C approval created; entry awaiting_approval.
    forbidden -> refused (403) and recorded.
    """
    command = command_registry.get_command(name)
    if command is None:
        raise CommandError(404, f"Unknown command: {name}")
    entry: Dict[str, Any] = {
        "command_id": f"cmd-{uuid.uuid4().hex}",
        "name": command["name"],
        "risk": command["risk"],
        "gate": command["gate"],
        "requested_by": requested_by,
        "channel": channel,
        "session_id": session_id or "command-console",
        "requested_at": utc_now_iso(),
        "request_id": None,
        "approval_id": None,
        "status": None,
        "outcome": None,
        "finished_at": None,
    }

    if command["gate"] == "forbidden":
        entry.update(status="forbidden", finished_at=utc_now_iso(),
                     outcome={"reason": command["description"]})
        _upsert(entry)
        raise CommandError(403, f"Command '{name}' is forbidden: {command['description']}")

    if command["gate"] == "direct":
        outcome = _execute_direct(command, entry, arguments or {})
        entry.update(status="executed", finished_at=utc_now_iso(), outcome=outcome)
        return _upsert(entry)

    # approval-gated: enter the IX-C pipeline; nothing executes yet.
    # Idempotent per session (XIII-A): the chat seat may re-ask while an approval is pending;
    # an identical command (same name, session, arguments) already awaiting approval is returned
    # as-is instead of growing the queue with duplicates.
    merged_arguments = {**(command.get("arguments") or {}), **(arguments or {})}
    for existing in _refresh_expired(load_command_log().get("commands", [])):
        if (existing.get("name") == command["name"]
                and existing.get("session_id") == entry["session_id"]
                and existing.get("channel") == channel
                and existing.get("status") == "awaiting_approval"):
            pending_request = get_tool_request(existing.get("request_id"), load_tool_request_store())
            if pending_request and (pending_request.get("arguments") or {}) == merged_arguments:
                return deepcopy(existing)
    request = build_tool_request(
        tool_name=command["tool_name"],
        arguments=merged_arguments,
        requested_by=f"operator:{channel}",
        session_id=entry["session_id"],
    )
    approval = create_approval_request(request)
    entry.update(status="awaiting_approval", request_id=request["request_id"],
                 approval_id=approval["approval_id"],
                 outcome={"note": "awaiting biometric-confirmed operator approval on a mobile console",
                          "expires_at": approval.get("expires_at")})
    return _upsert(entry)


_AUTHOR_TAG_STOP = {"the", "and", "for", "with", "from", "that", "this", "what", "into", "tool",
                    "give", "gives", "get", "gets", "data", "about", "your", "you", "need"}


def _spec_from_author_fields(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Build a spec-tool spec from author_tool's flat fields (an 8B fills flat fields far more
    reliably than nested JSON). Validation is validate_spec's job, not this function's."""
    import re as _re

    url_template = str(arguments.get("url_template") or "").strip()
    placeholders = list(dict.fromkeys(_re.findall(r"\{(\w+)\}", url_template)))
    fixture: Dict[str, str] = {}
    for part in _re.split(r"[;\n]", str(arguments.get("fixture_args") or "")):
        if "=" in part:
            key, value = part.split("=", 1)
            if key.strip():
                fixture[key.strip()] = value.strip()
    words = _re.findall(r"[a-z]{3,}", f"{arguments.get('need') or ''} {arguments.get('title') or ''}".lower())
    tags = [w for w in dict.fromkeys(words) if w not in _AUTHOR_TAG_STOP][:12]
    return {
        "name": str(arguments.get("name") or "").strip().lower(),
        "title": str(arguments.get("title") or "").strip(),
        "description": str(arguments.get("description") or "").strip(),
        "command_category": "acquired",
        "tags": tags,
        "method": "GET",
        "url_template": url_template,
        "params": [{"name": p, "type": "text", "label": p.replace("_", " "), "required": True}
                   for p in placeholders],
        "output_path": str(arguments.get("output_path") or "").strip(),
        # comma-separated field names kept per item (validate_spec splits and checks them)
        "output_fields": str(arguments.get("output_fields") or "").strip(),
        "max_output_chars": 3000,
        "fixture": {"args": fixture},
    }


def _describe_self() -> Dict[str, Any]:
    """OMEGA's real body and settings, read live — the answer to "examine yourself". Every value
    comes from the running system; nothing here is a claim the runtime cannot back."""
    from services import deep_seat, network_breaker, voice_setting
    from services.model_control import model_control
    from services.toolwright import inducted_specs

    voice = voice_setting.state()
    english = voice["voices"]
    return {
        "voice": {
            "engine": voice["engine"],
            "speaking_voice_now": f"{voice['current']} ({voice['current_label']})",
            "installed_english_voices": len(english),
            "how_to_change": "list_voices shows the options; set_voice changes it when the "
                             "operator asks. You CAN change it yourself.",
            "when_it_speaks": "Only when the operator turns on read-aloud ('Voice ON') in the "
                              "desktop console. You cannot see that switch; a console note in "
                              "the conversation tells you its state when the console sends it.",
        },
        "hearing": "The desktop console's hold-to-talk mic: speech is transcribed locally "
                   "(faster-whisper) and arrives as text. The phone apps have no mic yet.",
        "sight": "Only images the operator attaches (look_at_image) and enrolled faces "
                 "(recognize_faces). You cannot see the operator's screen or room.",
        "screens": "Desktop web console (Bridge Zero) on the host PC; iPhone and Android apps "
                   "over Tailscale. All talk to the same backend.",
        "chat_model": (model_control.status() or {}).get("active_model"),
        "deep_thinking_model": deep_seat.local_model(),
        "network_breaker": "ON (web reads allowed)" if network_breaker.breaker_is_on()
                           else "OFF (no web reads)",
        "installed_toolwright_tools": [s.get("name") for s in inducted_specs()],
        # Explicit, because the seat turned a general limit into "I can write and execute code
        # and make changes to myself ... with approval" (2026-11-06).
        "code": {
            "write_code_as_text": "YES: you can write code in a reply for the operator to read.",
            "run_code": "NO: you cannot execute code. No command runs code you write.",
            "change_yourself": "NO: there is no path for you to change your own code, even "
                               "with the operator's approval. It is being designed (the "
                               "Workbench: you propose, tests run, the operator approves).",
            "new_tools": "YES, within limits: draft_tool (preferred) has a stronger model "
                         "research and draft a new read-only tool (a keyless public JSON API, GET "
                         "over https), test-called before filing; author_tool if you already "
                         "know the exact endpoint. Either works only after the operator PREPAREs "
                         "and inducts it with a fingerprint. request_capability gets a stocked "
                         "shelf tool.",
        },
        "limits": "You run on the operator's PC. You cannot install software, run code, change "
                  "your own code, or see anything the runtime does not hand you.",
    }


def _execute_direct(command: Dict[str, Any], entry: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
    if command["name"] == "new_conversation":
        if _create_conversation is None:
            raise CommandError(503, "Command console is not bound to the runtime.")
        title = str(arguments.get("title") or "Command Console")
        conversation_id = _create_conversation(title=title)
        return {"conversation_id": conversation_id, "title": title}
    if command["name"] == "request_capability":
        # XIII-D: filing the gap is a direct act — the pipeline (find/quarantine/verify/induct)
        # stays operator-driven and biometric-gated. Filing is not having.
        from services.toolwright import file_request
        try:
            filed = file_request(str(arguments.get("need") or ""), str(arguments.get("why") or ""),
                                 requested_by=entry["requested_by"], session_id=entry["session_id"])
        except ValueError as exc:
            raise CommandError(422, str(exc)) from exc
        return {"capability_request_id": filed["request_id"], "status": filed["status"],
                "note": "Filed. The Toolwright pipeline (find → quarantine → verify → biometric "
                        "induction) decides whether this becomes a tool; filing is not having."}
    if command["name"] == "draft_tool":
        # ADR 0027 slice 1b: the frontier rung drafts, the runtime tests, only a passing
        # candidate is filed. Breaker OFF or no working draft = a plain refusal with reasons.
        from services.network_breaker import BreakerOpenError
        from services.tool_drafter import draft_tool
        try:
            return draft_tool(str(arguments.get("need") or ""), str(arguments.get("why") or ""),
                              requested_by=entry["requested_by"], session_id=entry["session_id"])
        except BreakerOpenError as exc:
            raise CommandError(422, str(exc)) from exc
        except ValueError as exc:
            raise CommandError(422, f"Drafting failed: {exc}") from exc
    if command["name"] == "author_tool":
        # ADR 0027 slice 1: OMEGA writes a candidate. Plain fields in; the runtime builds the
        # structured spec (params from the URL's placeholders, tags from the need and title) and
        # the unchanged spec contract judges it. Rejections go back to the author verbatim.
        from services.toolwright import author_candidate
        try:
            spec = _spec_from_author_fields(arguments)
            filed = author_candidate(str(arguments.get("need") or ""), str(arguments.get("why") or ""),
                                     spec, requested_by=entry["requested_by"],
                                     session_id=entry["session_id"])
        except ValueError as exc:
            raise CommandError(422, f"Spec rejected: {exc} Fix it and call author_tool again.") from exc
        return {"capability_request_id": filed["request_id"], "status": filed["status"],
                "tool_name": filed["candidate"]["name"],
                "note": "Authored and filed. Not usable yet: the operator must PREPARE it (a live "
                        "test call) and INDUCT it with a fingerprint. Say exactly that."}
    if command["name"] == "check_capability_requests":
        # Read-only view of the Toolwright, so the seat reports where a request stands from the
        # store instead of from memory (added 2026-11-06 in the first Toolwright workshop).
        from services.toolwright import inducted_specs, list_requests, shelf_summary
        requests = [{
            "capability_request_id": r.get("request_id"),
            "need": r.get("need"),
            "status": r.get("status"),
            "matched_tool": (r.get("candidate") or {}).get("name"),
            "requested_by": r.get("requested_by"),
            "filed_at": r.get("filed_at"),
            "last_event": ((r.get("history") or [{}])[-1]).get("event"),
        } for r in list_requests()[:20]]
        # Installed and shelf are SEPARATE lists with self-describing names: the 8B seat listed
        # shelf entries (world_time, define_word) as "available" when they sat in one list
        # beside the installed ones (2026-11-06).
        installed = [s.get("name") for s in inducted_specs()]
        return {
            "requests": requests,
            "installed_tools_usable_now": installed,
            "shelf_NOT_installed": [
                {**entry, "status": "NOT INSTALLED: on the shelf only; usable only after a "
                                    "request is filed, prepared, and inducted by the operator's "
                                    "fingerprint"}
                for entry in shelf_summary() if entry.get("name") not in installed],
            "note": "Only installed_tools_usable_now can be used. Never call a shelf tool "
                    "available. 'verified' and 'awaiting_induction' requests wait on the "
                    "operator's biometric induction; say so, never claim the tool exists.",
        }
    if command["name"] == "describe_self":
        return _describe_self()
    if command["name"] == "list_voices":
        from services import voice_setting
        return voice_setting.state()
    if command["name"] == "set_voice":
        from services import voice_setting
        try:
            changed = voice_setting.set_voice(str(arguments.get("voice") or ""),
                                              changed_by=entry.get("requested_by") or "unknown",
                                              channel=entry.get("channel") or "unknown")
        except ValueError as exc:
            raise CommandError(422, str(exc)) from exc
        return {"voice_now": changed["current"], "label": changed["current_label"],
                "note": "Takes effect on the next spoken reply (read-aloud must be on)."}
    if command.get("tool_name"):
        return _execute_direct_tool(command, {**(command.get("arguments") or {}), **(arguments or {})})
    raise CommandError(500, f"No direct handler for {command['name']}")


def _execute_direct_tool(command: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Run a bounded tool with no approval — permitted ONLY for tools that declare no side effects.

    This is the one place a tool executes without an IX-C approval, and the read-only guard is what
    makes that safe: a `run_host_status`-style command reads and returns, it never changes state. A
    direct command that pointed at a side-effecting tool is refused here (500), not silently run.
    """
    from services.tool_registry import get_tool

    tool_name = str(command["tool_name"])
    entry = get_tool(tool_name)
    if entry is None:
        raise CommandError(500, f"Direct command '{command['name']}' maps to unknown tool '{tool_name}'.")
    descriptor = entry.get("descriptor") or {}
    if descriptor.get("side_effects"):
        raise CommandError(500, f"Tool '{tool_name}' has side effects; it cannot be a direct command.")
    adapter = entry.get("adapter")
    if adapter is None or not hasattr(adapter, "execute"):
        raise CommandError(500, f"Tool '{tool_name}' has no adapter to execute.")
    try:
        output = adapter.execute(arguments)
    except ValueError as exc:
        raise CommandError(422, f"{tool_name}: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — surface, don't swallow
        raise CommandError(500, f"{tool_name} failed: {exc}") from exc
    return {"tool_name": tool_name, "output": output}


# ----------------------------------------------------------------------------- approval callbacks
def on_request_approved(request_id: str) -> Optional[Dict[str, Any]]:
    """Called after an approval lands. If a command is waiting on this request AND the approval
    carries a biometric confirmation, execute the bounded tool and record the outcome. Any other
    approval leaves the command waiting (and says so)."""
    entry = _find_by_request(request_id)
    if entry is None or entry.get("status") != "awaiting_approval":
        return None
    approval_store = load_tool_approval_store()
    approval = next((a for a in list_tool_approvals(approval_store) if a.get("request_id") == request_id), None)
    if not approval or approval.get("status") != "approved":
        return entry
    if approval.get("confirmation") != BIOMETRIC_CONFIRMATION:
        entry["outcome"] = {"note": "approval recorded without biometric confirmation — command stays "
                                    "waiting; confirm on a mobile console (desktop cannot self-approve)",
                            "approved_by": approval.get("approved_by")}
        return _upsert(entry)
    if not command_execution_enabled():
        entry.update(status="failed", finished_at=utc_now_iso(),
                     outcome={"error": "COMMAND_EXECUTION is disabled by runtime policy"})
        return _upsert(entry)
    return _execute_gated(entry, approval_store)


def on_request_rejected(request_id: str) -> Optional[Dict[str, Any]]:
    entry = _find_by_request(request_id)
    if entry is None or entry.get("status") != "awaiting_approval":
        return None
    entry.update(status="denied", finished_at=utc_now_iso(),
                 outcome={"note": "operator denied on a mobile console; nothing executed"})
    return _upsert(entry)


def _execute_gated(entry: Dict[str, Any], approval_store: Dict[str, Any]) -> Dict[str, Any]:
    request_store = load_tool_request_store()
    request = get_tool_request(entry["request_id"], request_store)
    if request is None:
        entry.update(status="failed", finished_at=utc_now_iso(), outcome={"error": "tool request vanished"})
        return _upsert(entry)
    entry["status"] = "executing"
    _upsert(entry)
    try:
        if request["tool_name"] == "backend_health_check":
            outcome = execute_backend_health_check_request(
                request_record=request,
                adapter=BackendHealthCheckAdapter(),
                evidence_store={"version": 1, "evidence": []},
                approval_store=approval_store,
                request_store=request_store,
                result_store=load_tool_result_store(),
                previous_evidence_store=None,
            )
            result = outcome.get("result") or {}
            output = result.get("output") or {}
            entry.update(status="executed", finished_at=utc_now_iso(),
                         outcome={"result_id": result.get("result_id"), "result_status": result.get("status"),
                                  "success": result.get("success"),
                                  "checked_url": output.get("checked_url"),
                                  "latency_ms": output.get("latency_ms")})
        else:
            # Any other approval-gated bounded tool runs through its registered adapter. The
            # biometric approval already consumed IS the gate here (unlike the direct path, there is
            # no side-effect guard — an approval-gated tool is expected to have side effects).
            entry.update(**_run_gated_adapter(request))
    except Exception as exc:  # noqa: BLE001 — the log must record failure, not swallow it
        entry.update(status="failed", finished_at=utc_now_iso(), outcome={"error": str(exc)})
    return _upsert(entry)


def _run_gated_adapter(request: Dict[str, Any]) -> Dict[str, Any]:
    from services.tool_registry import get_tool

    tool_name = str(request["tool_name"])
    tool = get_tool(tool_name)
    adapter = (tool or {}).get("adapter")
    if adapter is None or not hasattr(adapter, "execute"):
        return {"status": "failed", "finished_at": utc_now_iso(),
                "outcome": {"error": f"no executor for tool {tool_name}"}}
    try:
        output = adapter.execute(request.get("arguments") or {})
    except ValueError as exc:
        return {"status": "failed", "finished_at": utc_now_iso(),
                "outcome": {"error": f"{tool_name}: {exc}"}}
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "finished_at": utc_now_iso(),
                "outcome": {"error": f"{tool_name} failed: {exc}"}}
    return {"status": "executed", "finished_at": utc_now_iso(),
            "outcome": {"tool_name": tool_name, "output": output}}

"""The Toolwright (ADR 0026, Epoch XIII-D) — the runtime grows its own hands, gated.

The adapter discipline (candidate → verified → operator-activated, ADR 0024) applied to tools:

  1. GAP        — a capability request is filed (by the seat from chat, or the operator from a
                  console): what is needed, why. Filing is not having.
  2. FIND       — retrieval, not judgment: the stocked catalog first (curated keyless HTTP-read
                  specs); the open web is the v1.5 fallback, not built yet.
  3. QUARANTINE — the runtime (never the model) writes the candidate into an isolated directory.
                  Nothing imports it; nothing registers it; it is bytes under review.
  4. VERIFY     — deterministic contract checks against the QUARANTINED artifact (schema, GET/
                  https/public-host rules, name collisions) plus one fixture call through the
                  network breaker, logged like any egress. The model never grades its own find.
  5. INDUCT     — the verification report + provenance become a biometric operator approval
                  (toolwright_induction, a registered mutation gate). On the fingerprint, the
                  spec enters the registry as a bounded tool + command, risk-classed and gated
                  like any hand-written one. On denial the quarantine is deleted. Either way,
                  recorded.
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.adapters.spec_tool import SpecToolAdapter, build_descriptor, validate_spec
from services.tool_contracts import build_tool_request, utc_now_iso

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "tool_catalog.json"

MAX_NEED_CHARS = 300
MAX_WHY_CHARS = 500
_WORD_RE = re.compile(r"[a-z]{3,}")


# ----------------------------------------------------------------------------- store
def _store_path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "toolwright.json"


def _quarantine_dir(request_id: str) -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "quarantine" / request_id


def _load_store() -> Dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"version": 1, "requests": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "requests": []}
    if not isinstance(data, dict) or not isinstance(data.get("requests"), list):
        return {"version": 1, "requests": []}
    return data


def _save_store(store: Dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def _upsert(entry: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_store()
    requests = store.setdefault("requests", [])
    for i, existing in enumerate(requests):
        if existing.get("request_id") == entry["request_id"]:
            requests[i] = deepcopy(entry)
            break
    else:
        requests.append(deepcopy(entry))
    _save_store(store)
    return deepcopy(entry)


def _mark(entry: Dict[str, Any], status: str, event: str) -> None:
    entry["status"] = status
    entry.setdefault("history", []).append({"at": utc_now_iso(), "event": event})


def list_requests() -> List[Dict[str, Any]]:
    requests = _load_store().get("requests", [])
    requests.sort(key=lambda r: r.get("filed_at") or "", reverse=True)
    return deepcopy(requests)


def get_request(request_id: str) -> Optional[Dict[str, Any]]:
    for entry in _load_store().get("requests", []):
        if entry.get("request_id") == request_id:
            return deepcopy(entry)
    return None


def inducted_specs() -> List[Dict[str, Any]]:
    return [deepcopy(e["candidate"]) for e in _load_store().get("requests", [])
            if e.get("status") == "inducted" and isinstance(e.get("candidate"), dict)]


# ----------------------------------------------------------------------------- 1. the gap
def file_request(need: str, why: str, *, requested_by: str, session_id: str) -> Dict[str, Any]:
    need = str(need or "").strip()
    if not need:
        raise ValueError("A capability request needs a non-empty 'need'.")
    entry = {
        "request_id": f"cap-{uuid.uuid4().hex[:12]}",
        "need": need[:MAX_NEED_CHARS],
        "why": str(why or "").strip()[:MAX_WHY_CHARS],
        "requested_by": requested_by,
        "session_id": session_id,
        "filed_at": utc_now_iso(),
        "status": "proposed",
        "candidate": None,
        "provenance": None,
        "verification": None,
        "induction": None,
        "history": [{"at": utc_now_iso(), "event": f"filed by {requested_by}"}],
    }
    return _upsert(entry)


# ----------------------------------------------------------------------------- 2. find
def _load_catalog() -> List[Dict[str, Any]]:
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data.get("entries", []) if isinstance(data, dict) else []


def find_candidate(request_id: str) -> Dict[str, Any]:
    entry = get_request(request_id)
    if entry is None:
        raise LookupError(f"Unknown capability request {request_id}.")
    if entry["status"] not in ("proposed", "failed"):
        raise ValueError(f"Request is {entry['status']}; find runs from 'proposed'.")
    words = set(_WORD_RE.findall(entry["need"].lower())) | set(_WORD_RE.findall(entry["why"].lower()))
    best, best_score = None, 0
    for candidate in _load_catalog():
        tags = set(candidate.get("tags") or [])
        score = len(words & tags)
        if score > best_score:
            best, best_score = candidate, score
    if best is None:
        _mark(entry, "proposed", "find: no catalog candidate matched (open-web find is v1.5)")
        _upsert(entry)
        raise ValueError("No stocked-catalog candidate matches this need. The open-web find is "
                         "the Toolwright's next slice; for now the catalog is the shelf.")
    entry["candidate"] = deepcopy(best)
    entry["provenance"] = {"source": best.get("source") or "catalog",
                           "catalog_name": best.get("name"), "found_at": utc_now_iso(),
                           "match_score": best_score}
    _mark(entry, "found", f"find: catalog candidate '{best.get('name')}' (score {best_score})")
    return _upsert(entry)


# ----------------------------------------------------------------------------- 3. quarantine
def quarantine_candidate(request_id: str) -> Dict[str, Any]:
    entry = get_request(request_id)
    if entry is None:
        raise LookupError(f"Unknown capability request {request_id}.")
    if entry["status"] != "found" or not entry.get("candidate"):
        raise ValueError("Quarantine runs on a found candidate.")
    qdir = _quarantine_dir(request_id)
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / "spec.json").write_text(json.dumps(entry["candidate"], indent=2, ensure_ascii=False),
                                    encoding="utf-8")
    _mark(entry, "quarantined", f"quarantined at {qdir.name}/spec.json")
    return _upsert(entry)


# ----------------------------------------------------------------------------- 4. verify
def verify_candidate(request_id: str) -> Dict[str, Any]:
    entry = get_request(request_id)
    if entry is None:
        raise LookupError(f"Unknown capability request {request_id}.")
    if entry["status"] != "quarantined":
        raise ValueError("Verification runs on a quarantined candidate.")
    spec_path = _quarantine_dir(request_id) / "spec.json"
    checks: List[str] = []
    try:
        quarantined = json.loads(spec_path.read_text(encoding="utf-8"))
        checks.append("quarantined artifact readable")
        spec = validate_spec(quarantined)  # the QUARANTINED bytes are what gets verified
        checks.append("contract valid: GET-only, https, public host, params match template, "
                      "fixture covers required params")
        from services.command_registry import get_command
        from services.tool_registry import get_tool
        if get_tool(spec["name"]) is not None or get_command(spec["name"]) is not None:
            raise ValueError(f"Name collision: '{spec['name']}' already exists in the registry.")
        checks.append("no name collision with registered tools or commands")
        build_descriptor(spec)
        checks.append("descriptor builds and validates")
        # One fixture call through the breaker — logged like any egress. Fails plainly if the
        # breaker is off: verification needs the senses.
        fixture_result = SpecToolAdapter(spec).execute(dict(spec["fixture"]["args"]))
        if fixture_result.get("error"):
            raise ValueError(f"fixture call failed: {fixture_result['error']}")
        status_code = int(fixture_result.get("status_code") or 0)
        if not (200 <= status_code < 400):
            raise ValueError(f"fixture call answered HTTP {status_code}.")
        output = str(fixture_result.get("output") or "")
        if not output.strip():
            raise ValueError("fixture call produced empty output.")
        checks.append(f"fixture call OK (HTTP {status_code}, {len(output)} chars extracted)")
    except ValueError as exc:
        entry["verification"] = {"verified": False, "checks": checks, "failure": str(exc),
                                 "at": utc_now_iso()}
        _mark(entry, "failed", f"verification FAILED: {exc}")
        _upsert(entry)
        raise
    entry["candidate"] = spec
    entry["verification"] = {"verified": True, "checks": checks,
                             "fixture_output_preview": output[:300], "at": utc_now_iso()}
    _mark(entry, "verified", "verification passed")
    return _upsert(entry)


# ----------------------------------------------------------------------------- 5. induct
def request_induction(request_id: str, *, requested_by: str) -> Dict[str, Any]:
    entry = get_request(request_id)
    if entry is None:
        raise LookupError(f"Unknown capability request {request_id}.")
    if entry["status"] != "verified":
        raise ValueError("Induction is requested on a verified candidate.")
    from services.tool_approval import create_approval_request

    request = build_tool_request(
        tool_name="toolwright_induction",
        arguments={"capability_request_id": request_id, "tool_name": entry["candidate"]["name"]},
        requested_by=requested_by,
        session_id=entry.get("session_id") or "toolwright",
    )
    approval = create_approval_request(request)
    entry["induction"] = {"request_id": request["request_id"],
                          "approval_id": approval["approval_id"],
                          "requested_at": utc_now_iso(),
                          "expires_at": approval.get("expires_at")}
    _mark(entry, "awaiting_induction",
          "induction approval raised — biometric confirmation on a mobile console releases it")
    return _upsert(entry)


def complete_induction(request_id: str) -> Dict[str, Any]:
    entry = get_request(request_id)
    if entry is None:
        raise LookupError(f"Unknown capability request {request_id}.")
    if entry["status"] != "awaiting_induction" or not entry.get("induction"):
        raise ValueError("Completion runs on a request awaiting induction.")
    from services.tool_approval import consume_approval, get_tool_approval, load_tool_approval_store

    approval = get_tool_approval(entry["induction"]["approval_id"], load_tool_approval_store())
    if not approval or approval.get("status") != "approved" or approval.get("consumed_at"):
        raise PermissionError("Induction waits for an approved, unconsumed approval.")
    if approval.get("confirmation") != "biometric":
        raise PermissionError("Induction requires the operator's BIOMETRIC confirmation on a "
                              "mobile console — a plain approval does not admit a tool.")
    spec = entry["candidate"]
    from services.tool_registry import TOOL_REGISTRY, register_tool

    if spec["name"] not in TOOL_REGISTRY:
        register_tool(build_descriptor(spec), SpecToolAdapter(spec))
    consume_approval(entry["induction"]["approval_id"])
    entry["induction"]["inducted_at"] = utc_now_iso()
    _mark(entry, "inducted", f"inducted by biometric approval — '{spec['name']}' is now a "
                             "registered command, gated like any other")
    return _upsert(entry)


def deny_request(request_id: str, *, denied_by: str) -> Dict[str, Any]:
    entry = get_request(request_id)
    if entry is None:
        raise LookupError(f"Unknown capability request {request_id}.")
    if entry["status"] == "inducted":
        raise ValueError("An inducted tool is not denied; deregistration is its own action.")
    shutil.rmtree(_quarantine_dir(request_id), ignore_errors=True)  # denial deletes the quarantine
    _mark(entry, "denied", f"denied by {denied_by}; quarantine deleted")
    return _upsert(entry)


# ----------------------------------------------------------------------------- registry hooks
def register_inducted_tools() -> None:
    """Called at startup: every inducted spec becomes a live bounded tool again."""
    from services.tool_registry import TOOL_REGISTRY, register_tool

    for spec in inducted_specs():
        try:
            if spec.get("name") not in TOOL_REGISTRY:
                register_tool(build_descriptor(spec), SpecToolAdapter(spec))
        except ValueError:
            continue  # a spec that no longer validates stays dormant, never crashes startup


def inducted_commands() -> List[Dict[str, Any]]:
    """Commands for the registry render: inducted tools are commands like any other."""
    commands: List[Dict[str, Any]] = []
    for spec in inducted_specs():
        commands.append({
            "name": spec["name"],
            "title": spec.get("title") or spec["name"],
            "description": f"{spec.get('description')} (Acquired via the Toolwright; "
                           "breaker-gated; logged.)",
            "risk": "low",
            "gate": "direct",
            "category": spec.get("command_category") or "acquired",
            "tool_name": spec["name"],
            "parameters": [
                {"name": p["name"], "label": p.get("label") or p["name"], "type": p["type"],
                 "required": bool(p.get("required"))}
                for p in (spec.get("params") or [])
            ],
            "surfaces": ["mobile", "desktop"],
        })
    return commands

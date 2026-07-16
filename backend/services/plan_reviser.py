from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_records(evidence_store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(evidence_store, dict):
        return {}
    records = evidence_store.get("records")
    if isinstance(records, dict):
        return records
    facts = evidence_store.get("facts")
    if isinstance(facts, dict):
        return facts
    return {}


def _invalidate_step(step: Dict[str, Any], *, status: str = "invalidated", reason: str = "") -> None:
    step["status"] = status
    step["completed_at"] = None
    step["completion_evidence"] = []
    blockers = list(step.get("blockers") or [])
    if reason:
        blockers.append(reason)
    step["blockers"] = blockers
    step["updated_at"] = utc_now_iso()


def revise_plan(
    *,
    plan: Dict[str, Any],
    evidence_store: Dict[str, Any],
    reasoning_result: Dict[str, Any],
) -> Dict[str, Any]:
    _ = reasoning_result

    revised = deepcopy(plan)
    revised.setdefault("metadata", {})
    metadata = revised["metadata"]

    records = _extract_records(evidence_store)
    selected_record = records.get("vision_model_selected") or {}
    selected_model = selected_record.get("value")

    changed = False
    revision_reason = ""
    invalidated_steps: List[str] = []

    prior_model = metadata.get("selected_model")
    if selected_model and prior_model and selected_model != prior_model:
        changed = True
        revision_reason = "Vision model selection changed."

        step_map = {str(step.get("id")): step for step in revised.get("steps", []) if isinstance(step, dict)}
        if "verify-vision-model-load" in step_map:
            _invalidate_step(
                step_map["verify-vision-model-load"],
                status="pending",
                reason="Vision model selection changed.",
            )
            invalidated_steps.append("verify-vision-model-load")
        for step_id in ["verify-vision-model-response", "run-end-to-end-routing-test"]:
            if step_id in step_map:
                _invalidate_step(step_map[step_id], reason="Upstream model selection changed.")
                invalidated_steps.append(step_id)

    prior_port = metadata.get("backend_port")
    current_port = (records.get("backend_port") or {}).get("value")
    if prior_port is not None and current_port is not None and prior_port != current_port:
        changed = True
        if not revision_reason:
            revision_reason = "Backend endpoint changed."

        for step in revised.get("steps", []):
            if not isinstance(step, dict):
                continue
            if bool(step.get("endpoint_bound", False)):
                _invalidate_step(step, reason="Bound endpoint changed.")
                invalidated_steps.append(str(step.get("id") or ""))

    if metadata.get("structurally_unusable"):
        changed = True
        revision_reason = revision_reason or "Plan structure became unusable."
        old_plan = deepcopy(revised)
        old_plan["status"] = "superseded"
        old_plan["updated_at"] = utc_now_iso()

        replacement = deepcopy(revised)
        replacement_id = f"{revised.get('id', 'plan')}-v{int(revised.get('version', 1)) + 1}"
        replacement["id"] = replacement_id
        replacement["version"] = int(revised.get("version", 1)) + 1
        replacement["status"] = "active"
        replacement["supersedes"] = revised.get("id")
        replacement["superseded_by"] = None
        replacement["updated_at"] = utc_now_iso()

        old_plan["superseded_by"] = replacement_id

        return {
            "plan": replacement,
            "changed": True,
            "revision_reason": revision_reason,
            "invalidated_steps": invalidated_steps,
            "old_plan": old_plan,
            "replacement_plan": replacement,
        }

    if changed:
        revised["version"] = int(revised.get("version", 1)) + 1
        revised["updated_at"] = utc_now_iso()
        metadata.setdefault("revision_history", [])
        metadata["revision_history"].append(
            {
                "reason": revision_reason,
                "updated_at": revised["updated_at"],
                "invalidated_steps": list(dict.fromkeys(step_id for step_id in invalidated_steps if step_id)),
            }
        )

    if selected_model:
        metadata["selected_model"] = selected_model
    if current_port is not None:
        metadata["backend_port"] = current_port

    return {
        "plan": revised,
        "changed": changed,
        "revision_reason": revision_reason,
        "invalidated_steps": list(dict.fromkeys(step_id for step_id in invalidated_steps if step_id)),
    }

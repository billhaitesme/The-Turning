"""recognize_faces — who is in this image? (faces slice, 2026-11-05).

The identification sense: matches every face in one operator-attached image against the
operator-enrolled gallery. Local ONNX inference only — no network, no breaker, and the gallery
(biometric data) never leaves the machine. A face with no gallery match is "unknown", never a
guess: the vision LLM may describe a stranger; only enrollment creates an identity. Enrollment
itself is an operator console action — this tool reads the gallery, it can never write it.
"""
from __future__ import annotations

from typing import Any, Dict

from services.face_engine import FaceEngineUnavailable, recognize
from services.image_store import get_image_bytes
from services.tool_contracts import validate_tool_definition


class RecognizeFacesAdapter:
    def __init__(self, recognize_fn=None) -> None:
        self._recognize_fn = recognize_fn or recognize

    def describe(self) -> Dict[str, Any]:
        return {"name": "recognize_faces", "version": 1,
                "description": "Matches faces in one attached image against the enrolled gallery."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        image_id = str((arguments or {}).get("image_id") or "").strip()
        if not image_id:
            raise ValueError("recognize_faces requires an 'image_id' (attached images carry one).")
        return {"image_id": image_id}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        return {"would_recognize_in": validated["image_id"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        image = get_image_bytes(validated["image_id"])
        if image is None:
            raise ValueError(f"No stored image '{validated['image_id']}' — it may have been "
                             "pruned; ask the operator to re-attach it.")
        try:
            faces = self._recognize_fn(image)
        except FaceEngineUnavailable as exc:
            raise ValueError(f"The face engine is not ready: {exc}") from exc
        return {
            "image_id": validated["image_id"],
            "faces": faces,
            "count": len(faces),
            "note": "Identities come ONLY from the operator-enrolled gallery; 'unknown' means "
                    "no enrolled match — never guess who an unknown face might be.",
        }


RECOGNIZE_FACES_DESCRIPTOR = validate_tool_definition(
    {
        "name": "recognize_faces",
        "version": 1,
        "description": "Matches every face in one operator-attached image (by image_id) against "
                       "the operator-enrolled gallery. Local inference only; read-only; unknown "
                       "faces stay unknown.",
        "category": "inspection",
        "risk_level": "low",
        "requires_approval": False,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {"image_id": {"type": "string"}},
            "required": ["image_id"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

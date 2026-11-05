"""look_at_image — the runtime's eyes (voice/vision slice, 2026-11-05).

Vision is a SENSE, not a seat swap: the conversational seat stays the Model-Lock-selected agent
seat, and when the operator attaches an image it calls this bounded tool. The runtime shows the
stored image to the configured vision seat (OLLAMA_VISION_MODEL, a local model — no network
egress, no breaker) and returns its description as a tool result: data for the seat to weigh,
like every other sense. The seat never carries raw image bytes in its context.
"""
from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from services.image_store import get_image_b64
from services.tool_contracts import validate_tool_definition

VISION_TIMEOUT_SECONDS = 300.0
MAX_QUESTION_CHARS = 1000
MAX_DESCRIPTION_CHARS = 8000


def _vision_model() -> str:
    return os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:latest")


def _ollama_vision(question: str, image_b64: str) -> Dict[str, Any]:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api")
    model = _vision_model()
    try:
        response = httpx.post(
            f"{base}/chat",
            json={"model": model, "stream": False, "think": False,
                  "messages": [{"role": "user", "content": question, "images": [image_b64]}]},
            timeout=VISION_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValueError(f"vision seat {model} answered HTTP {exc.response.status_code}: "
                         f"{exc.response.text[:200]}") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"vision seat {model} is unreachable: {exc}") from exc
    data = response.json()
    return {"model": model, "description": str((data.get("message") or {}).get("content") or "")}


class LookAtImageAdapter:
    def __init__(self, vision_fn=None) -> None:
        self._vision_fn = vision_fn or _ollama_vision

    def describe(self) -> Dict[str, Any]:
        return {"name": "look_at_image", "version": 1,
                "description": "Shows one attached image to the local vision seat."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        image_id = str((arguments or {}).get("image_id") or "").strip()
        if not image_id:
            raise ValueError("look_at_image requires an 'image_id' (attached images carry one).")
        question = str((arguments or {}).get("question") or "").strip()[:MAX_QUESTION_CHARS]
        return {"image_id": image_id,
                "question": question or "Describe this image in concrete detail: what is shown, "
                                        "any text, and anything notable."}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        return {"would_look_at": validated["image_id"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        image_b64 = get_image_b64(validated["image_id"])
        if image_b64 is None:
            raise ValueError(f"No stored image '{validated['image_id']}' — it may have been "
                             "pruned; ask the operator to re-attach it.")
        result = self._vision_fn(validated["question"], image_b64)
        description = str(result.get("description") or "")
        return {
            "image_id": validated["image_id"],
            "model": result.get("model") or _vision_model(),
            "question": validated["question"],
            "description": description[:MAX_DESCRIPTION_CHARS],
            "truncated": len(description) > MAX_DESCRIPTION_CHARS,
            "note": "The vision seat's description is its reading, not ground truth — report it "
                    "as what the image appears to show.",
        }


LOOK_AT_IMAGE_DESCRIPTOR = validate_tool_definition(
    {
        "name": "look_at_image",
        "version": 1,
        "description": "Shows one operator-attached image (by image_id) to the local vision "
                       "seat and returns its description. Local inference only; read-only.",
        "category": "inspection",
        "risk_level": "low",
        "requires_approval": False,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "image_id": {"type": "string"},
                "question": {"type": "string"},
            },
            "required": ["image_id"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

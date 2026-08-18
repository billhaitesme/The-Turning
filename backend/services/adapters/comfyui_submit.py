"""comfyui_submit — an approval-gated bounded tool that queues a render on the local ComfyUI.

Epoch IX-D slice 4. This is the first command that *acts* on the outside world: it takes a text
prompt, fills a template workflow, and POSTs it to ComfyUI's /prompt queue. Because queuing a render
changes state (it commits GPU work and writes an image), its `side_effects` list is non-empty, which
means the command console will NOT direct-run it — it is medium/approval-gated, and executes only
after an operator approval confirmed by a device biometric.

It submits and returns the queued prompt id; it does not wait for the image. A later command can poll
`/history/{id}` for the result. The public template (`sdxl_lightning_txt2img`) uses a general-purpose
SDXL-lightning checkpoint so a proof render is fast; the operator's private pipelines are wrapped by a
separate, private command, never here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
from typing import Any, Dict
from urllib import error, request

from services.tool_contracts import validate_tool_definition

COMFYUI_HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 10
TEMPLATES_DIR = Path(__file__).resolve().parent / "comfyui_templates"

# Which node each substitutable parameter lives on, for the templates this tool ships. Keeping the
# map here (not scattered in the JSON) means a template swap is one entry, and a missing node fails
# loudly rather than silently rendering the placeholder prompt.
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "sdxl_lightning_txt2img": {
        "file": "sdxl_lightning_txt2img.json",
        "positive_node": "6",
        "negative_node": "7",
        "sampler_node": "3",
        "latent_node": "5",
        "checkpoint_node": "4",
    },
}
DEFAULT_TEMPLATE = "sdxl_lightning_txt2img"
MAX_SEED = 2**32 - 1


def _port() -> int:
    try:
        return int(os.getenv("COMFYUI_PORT", "8188") or 8188)
    except (TypeError, ValueError):
        return 8188


class ComfyUISubmitAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "comfyui_submit", "version": 1, "description": "Queues a text-to-image render on the local ComfyUI."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("comfyui_submit arguments must be an object.")
        allowed = {"prompt", "negative_prompt", "seed", "steps", "width", "height", "workflow"}
        extra = set(arguments) - allowed
        if extra:
            raise ValueError(f"comfyui_submit does not accept: {', '.join(sorted(extra))}.")
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("comfyui_submit requires a non-empty 'prompt'.")
        workflow = arguments.get("workflow", DEFAULT_TEMPLATE)
        if workflow not in TEMPLATES:
            raise ValueError(f"unknown workflow '{workflow}'; known: {', '.join(sorted(TEMPLATES))}.")
        validated: Dict[str, Any] = {"prompt": prompt.strip(), "workflow": workflow}
        negative = arguments.get("negative_prompt", "")
        validated["negative_prompt"] = negative.strip() if isinstance(negative, str) else ""
        seed = arguments.get("seed")
        if seed is not None:
            if not isinstance(seed, int) or not (0 <= seed <= MAX_SEED):
                raise ValueError("'seed' must be an integer between 0 and 2^32-1.")
            validated["seed"] = seed
        for key, lo, hi in (("steps", 1, 60), ("width", 256, 2048), ("height", 256, 2048)):
            value = arguments.get(key)
            if value is not None:
                if not isinstance(value, int) or not (lo <= value <= hi):
                    raise ValueError(f"'{key}' must be an integer between {lo} and {hi}.")
                validated[key] = value
        return validated

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        return {"would_submit": validated, "safe": False, "side_effects": ["queues a ComfyUI render job"]}

    def _build_workflow(self, validated: Dict[str, Any]) -> Dict[str, Any]:
        spec = TEMPLATES[validated["workflow"]]
        template_path = TEMPLATES_DIR / spec["file"]
        workflow = json.loads(template_path.read_text(encoding="utf-8"))
        workflow = deepcopy(workflow)

        def node(node_id: str) -> Dict[str, Any]:
            if node_id not in workflow:
                raise ValueError(f"template '{validated['workflow']}' is missing node {node_id}.")
            return workflow[node_id]

        node(spec["positive_node"])["inputs"]["text"] = validated["prompt"]
        node(spec["negative_node"])["inputs"]["text"] = validated["negative_prompt"]
        sampler = node(spec["sampler_node"])["inputs"]
        sampler["seed"] = validated.get("seed", random.randint(0, MAX_SEED))
        if "steps" in validated:
            sampler["steps"] = validated["steps"]
        latent = node(spec["latent_node"])["inputs"]
        if "width" in validated:
            latent["width"] = validated["width"]
        if "height" in validated:
            latent["height"] = validated["height"]
        checkpoint = node(spec["checkpoint_node"])["inputs"].get("ckpt_name")
        return {"workflow": workflow, "seed": sampler["seed"], "checkpoint": checkpoint}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        built = self._build_workflow(validated)
        port = _port()
        body = json.dumps({"prompt": built["workflow"], "client_id": "omega-arc-command-console"}).encode("utf-8")
        req = request.Request(f"http://{COMFYUI_HOST}:{port}/prompt", data=body, method="POST",
                              headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:  # noqa: S310 — fixed localhost
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500] if hasattr(exc, "read") else str(exc)
            raise ValueError(f"ComfyUI rejected the workflow (HTTP {exc.code}): {detail}") from exc
        except (error.URLError, OSError) as exc:
            raise ValueError(f"ComfyUI is not reachable on {COMFYUI_HOST}:{port} to submit "
                             f"({getattr(exc, 'reason', exc)}).") from exc

        node_errors = payload.get("node_errors") or {}
        if node_errors:
            raise ValueError(f"ComfyUI reported node errors: {json.dumps(node_errors)[:500]}")
        return {
            "submitted": True,
            "prompt_id": payload.get("prompt_id"),
            "queue_number": payload.get("number"),
            "workflow": validated["workflow"],
            "checkpoint": built["checkpoint"],
            "seed": built["seed"],
            "prompt": validated["prompt"],
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }


COMFYUI_SUBMIT_DESCRIPTOR = validate_tool_definition(
    {
        "name": "comfyui_submit",
        "version": 1,
        "description": "Queues a text-to-image render on the local ComfyUI from a template workflow.",
        "category": "mutation",
        "risk_level": "medium",
        "requires_approval": True,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1},
                "negative_prompt": {"type": "string"},
                "seed": {"type": "integer", "minimum": 0, "maximum": MAX_SEED},
                "steps": {"type": "integer", "minimum": 1, "maximum": 60},
                "width": {"type": "integer", "minimum": 256, "maximum": 2048},
                "height": {"type": "integer", "minimum": 256, "maximum": 2048},
                "workflow": {"type": "string"},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": ["queues a ComfyUI render job"],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

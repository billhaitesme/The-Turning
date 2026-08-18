"""comfyui_free_vram — an approval-gated bounded tool that frees the local ComfyUI's held VRAM.

Epoch IX-D slice 4. Calls ComfyUI's /free (unload models + free memory). This unloads models from
the GPU — a real, if benign and reversible, side effect (models reload on the next render, and it can
disturb an in-flight job), so its `side_effects` list is non-empty and the command console will NOT
direct-run it: it is approval-gated like any other action. Reversible/low-severity, but still an act.

Reports GPU VRAM before/after (via nvidia-smi if present) so the operator sees what was reclaimed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import shutil
import subprocess
from typing import Any, Dict, Optional
from urllib import error, request

from services.tool_contracts import validate_tool_definition

COMFYUI_HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 15


def _port() -> int:
    try:
        return int(os.getenv("COMFYUI_PORT", "8188") or 8188)
    except (TypeError, ValueError):
        return 8188


def _vram_used_free_mb() -> Optional[Dict[str, int]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "--query-gpu=memory.used,memory.free,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8, check=True,
        ).stdout.strip().splitlines()[0]
        used, free, total = (int(x.strip()) for x in out.split(","))
        return {"used_mb": used, "free_mb": free, "total_mb": total}
    except (subprocess.SubprocessError, ValueError, IndexError, OSError):
        return None


class ComfyUIFreeVramAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "comfyui_free_vram", "version": 1, "description": "Unloads ComfyUI models and frees GPU memory."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if arguments and set(arguments):
            raise ValueError("comfyui_free_vram takes no arguments.")
        return {}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        return {"would_free": True, "safe": False, "side_effects": ["unloads ComfyUI models from VRAM"]}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        port = _port()
        before = _vram_used_free_mb()
        body = json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8")
        req = request.Request(f"http://{COMFYUI_HOST}:{port}/free", data=body, method="POST",
                              headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:  # noqa: S310 — fixed localhost
                status_code = int(getattr(response, "status", response.getcode()))
        except error.HTTPError as exc:
            raise ValueError(f"ComfyUI /free returned HTTP {exc.code}.") from exc
        except (error.URLError, OSError) as exc:
            raise ValueError(f"ComfyUI is not reachable on {COMFYUI_HOST}:{port} to free VRAM "
                             f"({getattr(exc, 'reason', exc)}).") from exc

        after = _vram_used_free_mb()
        result: Dict[str, Any] = {
            "freed": True,
            "status_code": status_code,
            "freed_at": datetime.now(timezone.utc).isoformat(),
        }
        if before and after:
            result["vram_before_mb"] = before
            result["vram_after_mb"] = after
            result["reclaimed_mb"] = max(0, before["used_mb"] - after["used_mb"])
        return result


COMFYUI_FREE_VRAM_DESCRIPTOR = validate_tool_definition(
    {
        "name": "comfyui_free_vram",
        "version": 1,
        "description": "Unloads the local ComfyUI's models and frees GPU memory (reversible; models reload on next render).",
        "category": "maintenance",
        "risk_level": "low",
        "requires_approval": True,
        "supports_dry_run": True,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_schema": {"type": "object"},
        "side_effects": ["unloads ComfyUI models from VRAM"],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

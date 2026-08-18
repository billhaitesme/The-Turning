"""comfyui_status — a read-only bounded tool reporting the local ComfyUI's reachability and queue.

Epoch IX-D slice 4, the read-only first step toward automating ComfyUI (see the future-comfyui-tool
plan). Like host_status it only reads — is ComfyUI up, how deep is the render queue, what device is
it on — so its command is low/direct: no approval, nothing to gate on a read. The side-effecting
*submit* command that queues a job is a separate, approval-gated addition that comes after this.

ComfyUI exposes a local HTTP API (default http://127.0.0.1:8188): GET /queue lists running and
pending jobs, GET /system_stats reports the device and VRAM. ComfyUI is frequently NOT running (it
is started on demand and killed when idle), so this tool treats an unreachable ComfyUI as a normal,
reported state — reachable=false — never an error the console has to interpret.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict
from urllib import error, request

from services.tool_contracts import validate_tool_definition

COMFYUI_HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 3


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _port() -> int:
    try:
        return int(os.getenv("COMFYUI_PORT", "8188") or 8188)
    except (TypeError, ValueError):
        return 8188


def _get_json(port: int, path: str, timeout: int) -> Any:
    url = f"http://{COMFYUI_HOST}:{port}{path}"
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout) as response:  # noqa: S310 — fixed localhost host
        return json.loads(response.read().decode("utf-8"))


class ComfyUIStatusAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "comfyui_status", "version": 1, "description": "Reads ComfyUI reachability and render queue."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if arguments and set(arguments):
            raise ValueError("comfyui_status takes no arguments.")
        return {}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        return {"would_read": [f"http://{COMFYUI_HOST}:{_port()}/queue", "/system_stats"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        port = _port()
        try:
            timeout = max(1, int(os.getenv("COMFYUI_STATUS_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))))
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT_SECONDS

        payload: Dict[str, Any] = {"observed_at": _utc_now_iso(), "port": port, "reachable": False}

        try:
            queue = _get_json(port, "/queue", timeout)
        except (error.URLError, OSError, ValueError) as exc:
            # ComfyUI not running is the common case, not an error — report it plainly.
            payload["detail"] = f"ComfyUI is not reachable on {COMFYUI_HOST}:{port} ({getattr(exc, 'reason', exc)})."
            return payload

        payload["reachable"] = True
        running = queue.get("queue_running") if isinstance(queue, dict) else None
        pending = queue.get("queue_pending") if isinstance(queue, dict) else None
        payload["queue_running"] = len(running) if isinstance(running, list) else 0
        payload["queue_pending"] = len(pending) if isinstance(pending, list) else 0
        payload["queue_total"] = payload["queue_running"] + payload["queue_pending"]

        # Device / VRAM / version are best-effort — a reachable ComfyUI without them is still fine.
        try:
            stats = _get_json(port, "/system_stats", timeout)
            system = stats.get("system", {}) if isinstance(stats, dict) else {}
            devices = stats.get("devices", []) if isinstance(stats, dict) else []
            payload["comfyui_version"] = system.get("comfyui_version")
            if isinstance(devices, list) and devices:
                device = devices[0]
                payload["device_name"] = device.get("name")
                payload["vram_total_bytes"] = device.get("vram_total")
                payload["vram_free_bytes"] = device.get("vram_free")
        except (error.URLError, OSError, ValueError):
            payload["stats_available"] = False

        return payload


COMFYUI_STATUS_DESCRIPTOR = validate_tool_definition(
    {
        "name": "comfyui_status",
        "version": 1,
        "description": "Reads the local ComfyUI's reachability and render queue depth. Read-only.",
        "category": "diagnostic",
        "risk_level": "low",
        "requires_approval": False,
        "supports_dry_run": True,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

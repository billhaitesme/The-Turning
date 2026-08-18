"""host_status — a read-only bounded tool that reports the host machine's vitals.

Epoch IX-D slice 4, the first registry-broadening command. Unlike backend_health_check (which pings
the backend and is approval-gated), this reads the *host* it runs on — CPU, memory, disk, uptime —
and has **no side effects**, so its command is classified low/direct: it executes immediately, no
approval, because there is nothing to gate on a read. The command console will only direct-execute a
tool whose descriptor declares an empty `side_effects` list, which this does.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import shutil
from typing import Any, Dict

from services.tool_contracts import validate_tool_definition

try:  # psutil ships in the backend venv; degrade gracefully if it is ever absent
    import psutil
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore[assignment]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _system_root() -> str:
    # The drive the host booted from; on Windows this is the SystemDrive (e.g. C:\), else "/".
    return os.getenv("SystemDrive", "") + os.sep if os.name == "nt" else "/"


class HostStatusAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "host_status", "version": 1, "description": "Reads host CPU, memory, disk, and uptime."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Read-only and parameter-free; reject anything passed so the contract stays tight.
        if arguments and set(arguments):
            raise ValueError("host_status takes no arguments.")
        return {}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        return {"would_read": ["cpu", "memory", "disk", "uptime"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        observed_at = _utc_now_iso()
        payload: Dict[str, Any] = {"observed_at": observed_at, "psutil_available": psutil is not None}

        if psutil is None:
            payload["error"] = "psutil unavailable; host vitals cannot be read."
            return payload

        # CPU — a one-shot read needs a real sampling interval; interval=None returns 0.0 on the
        # first call of a fresh process (no prior baseline). 0.15 s blocks briefly for an honest value.
        payload["cpu_percent"] = round(float(psutil.cpu_percent(interval=0.15)), 1)
        payload["cpu_count"] = psutil.cpu_count(logical=True)

        # Memory
        memory = psutil.virtual_memory()
        payload["ram_used_bytes"] = int(memory.used)
        payload["ram_total_bytes"] = int(memory.total)
        payload["ram_percent"] = round(float(memory.percent), 1)

        # Disk (system root)
        root = _system_root()
        try:
            usage = shutil.disk_usage(root)
            payload["disk_root"] = root
            payload["disk_used_bytes"] = int(usage.used)
            payload["disk_total_bytes"] = int(usage.total)
            payload["disk_percent"] = round(usage.used / usage.total * 100.0, 1) if usage.total else None
        except OSError as exc:
            payload["disk_error"] = str(exc)

        # Uptime
        try:
            boot = float(psutil.boot_time())
            payload["boot_time"] = datetime.fromtimestamp(boot, tz=timezone.utc).isoformat()
            payload["uptime_seconds"] = max(0, int(datetime.now(timezone.utc).timestamp() - boot))
        except Exception:  # noqa: BLE001
            pass

        return payload


HOST_STATUS_DESCRIPTOR = validate_tool_definition(
    {
        "name": "host_status",
        "version": 1,
        "description": "Reads the host machine's CPU, memory, disk, and uptime. Read-only.",
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

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, parse, request

from services.tool_contracts import validate_tool_definition


DEFAULT_BACKEND_HEALTH_PATHS = ["/health", "/system/status", "/"]
DEFAULT_BACKEND_HEALTH_TIMEOUT_SECONDS = 3
DEFAULT_BACKEND_HOST = "127.0.0.1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_paths() -> List[str]:
    configured = os.getenv("BACKEND_HEALTH_CHECK_PATHS", "/health,/system/status,/")
    return [path.strip() for path in str(configured).split(",") if path.strip()]


def _candidate_urls(port: int) -> List[str]:
    return [f"http://{DEFAULT_BACKEND_HOST}:{port}{path}" for path in _candidate_paths()]


def _parse_host(url: str) -> str:
    return parse.urlparse(url).hostname or ""


class _LocalhostOnlyRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = _parse_host(newurl)
        if host not in {DEFAULT_BACKEND_HOST, "localhost"}:
            raise error.HTTPError(req.full_url, code, f"redirect left localhost: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class BackendHealthResult:
    target: str
    checked_url: str
    success: bool
    status_code: Optional[int]
    latency_ms: float
    checked_at: str
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "checked_url": self.checked_url,
            "success": self.success,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at,
            "error": self.error,
        }


class BackendHealthCheckAdapter:
    def describe(self) -> Dict[str, Any]:
        return {
            "name": "backend_health_check",
            "version": 1,
            "description": "Checks the configured local backend endpoint.",
        }

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("backend_health_check arguments must be an object.")
        if set(arguments) - {"port"}:
            raise ValueError("backend_health_check accepts only the port argument.")
        if "port" not in arguments:
            raise ValueError("backend_health_check requires port.")
        port = arguments.get("port")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("backend_health_check port must be an integer between 1 and 65535.")
        return {"port": port}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        return {
            "would_check": _candidate_urls(int(validated["port"])),
            "safe": True,
            "side_effects": [],
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        port = int(validated["port"])
        try:
            timeout_seconds = max(1, int(os.getenv("BACKEND_HEALTH_CHECK_TIMEOUT_SECONDS", str(DEFAULT_BACKEND_HEALTH_TIMEOUT_SECONDS))))
        except Exception:
            timeout_seconds = DEFAULT_BACKEND_HEALTH_TIMEOUT_SECONDS
        opener = request.build_opener(_LocalhostOnlyRedirectHandler())
        checked_at = _utc_now_iso()
        last_error: Optional[str] = None
        last_status_code: Optional[int] = None

        for checked_url in _candidate_urls(port):
            started = datetime.now(timezone.utc)
            try:
                req = request.Request(checked_url, method="GET")
                with opener.open(req, timeout=timeout_seconds) as response:
                    status_code = int(getattr(response, "status", response.getcode()))
                    latency_ms = max(0.0, (datetime.now(timezone.utc) - started).total_seconds() * 1000.0)
                    if 200 <= status_code < 300:
                        return BackendHealthResult(
                            target="backend",
                            checked_url=checked_url,
                            success=True,
                            status_code=status_code,
                            latency_ms=latency_ms,
                            checked_at=checked_at,
                            error=None,
                        ).to_dict()
                    last_error = f"HTTP {status_code}"
                    last_status_code = status_code
            except error.HTTPError as exc:
                status_code = getattr(exc, "code", None)
                last_error = f"HTTP {status_code}" if status_code is not None else str(exc)
                if status_code is not None and 200 <= int(status_code) < 300:
                    latency_ms = max(0.0, (datetime.now(timezone.utc) - started).total_seconds() * 1000.0)
                    return BackendHealthResult(
                        target="backend",
                        checked_url=checked_url,
                        success=True,
                        status_code=int(status_code),
                        latency_ms=latency_ms,
                        checked_at=checked_at,
                        error=None,
                    ).to_dict()
                if status_code is not None:
                    last_status_code = int(status_code)
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, error.URLError):
                    last_error = str(getattr(exc, "reason", exc))
                else:
                    last_error = str(exc)

        return BackendHealthResult(
            target="backend",
            checked_url=_candidate_urls(port)[0],
            success=False,
            status_code=last_status_code,
            latency_ms=float(timeout_seconds * 1000),
            checked_at=checked_at,
            error=last_error or "connection refused",
        ).to_dict()


BACKEND_HEALTH_CHECK_DESCRIPTOR = validate_tool_definition(
    {
        "name": "backend_health_check",
        "version": 1,
        "description": "Checks the configured local backend endpoint.",
        "category": "diagnostic",
        "risk_level": "low",
        "requires_approval": True,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535,
                }
            },
            "required": ["port"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

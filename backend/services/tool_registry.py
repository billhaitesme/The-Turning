from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.tool_contracts import ToolAdapter, validate_tool_definition

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


class BackendHealthCheckAdapter(ToolAdapter):
    def describe(self) -> Dict[str, Any]:
        return {
            "name": "backend_health_check",
            "version": 1,
            "description": "Checks the configured local backend endpoint.",
        }

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if arguments:
            raise ValueError("backend_health_check does not accept arguments in Epoch VIII.")
        return {}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        return {
            "would_check": "http://127.0.0.1:8001/health",
            "side_effects": [],
            "safe": True,
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_arguments(arguments)
        return {
            "status": "not_implemented",
            "success": False,
            "output": {
                "checked_url": "http://127.0.0.1:8001/health",
                "message": "backend_health_check execution is stubbed in Epoch VIII.",
            },
            "side_effects_observed": [],
        }


BACKEND_HEALTH_CHECK_DESCRIPTOR = validate_tool_definition(
    {
        "name": "backend_health_check",
        "version": 1,
        "description": "Checks the configured local backend endpoint.",
        "category": "diagnostic",
        "risk_level": "low",
        "requires_approval": True,
        "supports_dry_run": True,
        "input_schema": {},
        "output_schema": {},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)


def register_tool(tool_definition: Dict[str, Any], adapter: Optional[ToolAdapter] = None) -> Dict[str, Any]:
    descriptor = validate_tool_definition(tool_definition)
    name = descriptor["name"]
    if name in TOOL_REGISTRY:
        raise ValueError(f"Tool already registered: {name}")

    entry = {"descriptor": deepcopy(descriptor), "adapter": adapter}
    TOOL_REGISTRY[name] = entry
    return deepcopy(entry)


def unregister_tool(tool_name: str) -> Optional[Dict[str, Any]]:
    return TOOL_REGISTRY.pop(str(tool_name), None)


def get_tool(tool_name: str) -> Optional[Dict[str, Any]]:
    entry = TOOL_REGISTRY.get(str(tool_name))
    return deepcopy(entry) if entry is not None else None


def list_tools() -> List[Dict[str, Any]]:
    descriptors = [deepcopy(entry["descriptor"]) for entry in TOOL_REGISTRY.values()]
    descriptors.sort(key=lambda item: str(item.get("name") or ""))
    return descriptors


def is_tool_enabled(tool_name: str) -> bool:
    entry = TOOL_REGISTRY.get(str(tool_name))
    if not entry:
        return False
    descriptor = entry.get("descriptor") or {}
    return bool(descriptor.get("enabled"))


def get_tool_adapter(tool_name: str) -> Optional[ToolAdapter]:
    entry = TOOL_REGISTRY.get(str(tool_name))
    if not entry:
        return None
    adapter = entry.get("adapter")
    return adapter if isinstance(adapter, ToolAdapter) else None


def register_default_tools() -> None:
    if "backend_health_check" not in TOOL_REGISTRY:
        register_tool(BACKEND_HEALTH_CHECK_DESCRIPTOR, BackendHealthCheckAdapter())


register_default_tools()

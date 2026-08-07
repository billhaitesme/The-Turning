from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.adapters.backend_health_check import BACKEND_HEALTH_CHECK_DESCRIPTOR, BackendHealthCheckAdapter
from services.tool_contracts import ToolAdapter, validate_tool_definition

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


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

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.adapters.approval_status import APPROVAL_STATUS_DESCRIPTOR, ApprovalStatusAdapter
from services.adapters.deep_think import DEEP_THINK_DESCRIPTOR, DeepThinkAdapter
from services.adapters.look_at_image import LOOK_AT_IMAGE_DESCRIPTOR, LookAtImageAdapter
from services.adapters.backend_health_check import BACKEND_HEALTH_CHECK_DESCRIPTOR, BackendHealthCheckAdapter
from services.adapters.comfyui_status import COMFYUI_STATUS_DESCRIPTOR, ComfyUIStatusAdapter
from services.adapters.comfyui_submit import COMFYUI_SUBMIT_DESCRIPTOR, ComfyUISubmitAdapter
from services.adapters.comfyui_free_vram import COMFYUI_FREE_VRAM_DESCRIPTOR, ComfyUIFreeVramAdapter
from services.adapters.host_status import HOST_STATUS_DESCRIPTOR, HostStatusAdapter
from services.adapters.spec_tool import TOOLWRIGHT_INDUCTION_DESCRIPTOR
from services.adapters.tutelage_consolidation import TUTELAGE_CONSOLIDATION_DESCRIPTOR
from services.adapters.web_fetch import WEB_FETCH_DESCRIPTOR, WebFetchAdapter
from services.adapters.web_search import WEB_SEARCH_DESCRIPTOR, WebSearchAdapter
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
    if "host_status" not in TOOL_REGISTRY:
        # Read-only, no side effects — the command console may direct-execute it (IX-D slice 4).
        register_tool(HOST_STATUS_DESCRIPTOR, HostStatusAdapter())
    if "comfyui_status" not in TOOL_REGISTRY:
        # Read-only reachability + render-queue check; direct-executable (IX-D slice 4).
        register_tool(COMFYUI_STATUS_DESCRIPTOR, ComfyUIStatusAdapter())
    if "comfyui_submit" not in TOOL_REGISTRY:
        # Side-effecting (queues a render) — approval-gated, runs through the gated executor.
        register_tool(COMFYUI_SUBMIT_DESCRIPTOR, ComfyUISubmitAdapter())
    if "comfyui_free_vram" not in TOOL_REGISTRY:
        # Side-effecting (unloads models) — approval-gated; low severity, but still an act.
        register_tool(COMFYUI_FREE_VRAM_DESCRIPTOR, ComfyUIFreeVramAdapter())
    if "approval_status" not in TOOL_REGISTRY:
        # Read-only pipeline truth (XIII-A follow-up): lets the chat seat verify whether an
        # operator approval actually landed instead of guessing; direct-executable.
        register_tool(APPROVAL_STATUS_DESCRIPTOR, ApprovalStatusAdapter())
    if "look_at_image" not in TOOL_REGISTRY:
        # The eyes: vision is a sense, not a seat swap — the agent seat consults the local
        # vision seat through this bounded tool; no network, no breaker.
        register_tool(LOOK_AT_IMAGE_DESCRIPTOR, LookAtImageAdapter())
    if "deep_think" not in TOOL_REGISTRY:
        # XIII-C Mind Ladder rungs 2-3: deep local gear + frontier planner (breaker-gated).
        # Privacy is structural: only the composed task/context strings can be sent.
        register_tool(DEEP_THINK_DESCRIPTOR, DeepThinkAdapter())
    if "web_search" not in TOOL_REGISTRY:
        # XIII-B senses: read-only internet reads, gated by the operator's network breaker
        # inside the adapters themselves (off by default; every read logged).
        register_tool(WEB_SEARCH_DESCRIPTOR, WebSearchAdapter())
    if "web_fetch" not in TOOL_REGISTRY:
        register_tool(WEB_FETCH_DESCRIPTOR, WebFetchAdapter())
    if "tutelage_consolidation" not in TOOL_REGISTRY:
        # No adapter on purpose: the tool executor cannot run consolidation directly;
        # the approval it gates is consumed by /system/tutelage/consolidations (ADR 0024).
        register_tool(TUTELAGE_CONSOLIDATION_DESCRIPTOR, None)
    if "toolwright_induction" not in TOOL_REGISTRY:
        # XIII-D: the induction gate — no adapter; its approval is consumed by the Toolwright's
        # completion step after the operator's biometric (ADR 0024's pattern, for tools).
        register_tool(TOOLWRIGHT_INDUCTION_DESCRIPTOR, None)
    # Tools the operator previously inducted come back to life at startup.
    from services.toolwright import register_inducted_tools
    register_inducted_tools()


register_default_tools()

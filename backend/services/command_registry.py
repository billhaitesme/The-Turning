"""Command registry — the authority for what an operator may command and how (ADR 0015, IX-D).

The consoles render this registry; they never define it. Every command carries a risk class and a
gate:

  direct     — low risk, already-explicit operator actions; execute immediately, recorded.
  approval   — the command becomes a bounded tool request in the existing IX-C pipeline and
               executes ONLY after an operator approval confirmed by a device biometric.
  forbidden  — never executes; the attempt itself is refused and recorded (Model Lock /
               output fidelity: ADR-IX-001, ADR-IX-002).

Slice 1 shipped exactly three commands — one of each gate — per the epoch design's first concrete
step. Slice 4 broadens the registry one risk-classed command at a time, the gated path having been
proven on hardware: `run_host_status` (low/direct) is the first addition — a read-only host-vitals
read that direct-executes because there is nothing to gate on a read.

A direct command may map to a bounded tool (`tool_name`); the console will direct-run it ONLY when
that tool declares no side effects (see command_console._execute_direct). Approval-gated commands
always map to a bounded tool.
"""
from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict, List, Optional

RISK_LEVELS = ("low", "medium", "high", "forbidden")
GATES = ("direct", "approval", "forbidden")

COMMANDS: List[Dict[str, Any]] = [
    {
        "name": "new_conversation",
        "title": "New conversation",
        "description": "Start a fresh conversation with the runtime (already an explicit operator action in IX-C).",
        "risk": "low",
        "gate": "direct",
        "surfaces": ["mobile", "desktop"],
    },
    {
        "name": "run_backend_health_check",
        "title": "Run backend health check",
        "description": "Ask the runtime to run its bounded backend_health_check tool. Creates an IX-C tool "
                       "request; executes only after a biometric-confirmed operator approval.",
        "risk": "medium",
        "gate": "approval",
        "tool_name": "backend_health_check",
        # the tool's one required argument: the runtime's own port (OMEGA_BACKEND_PORT, default 8001)
        "arguments": {"port": int(os.getenv("OMEGA_BACKEND_PORT", "8001") or 8001)},
        "surfaces": ["mobile", "desktop"],
    },
    {
        "name": "run_host_status",
        "title": "Host status",
        "description": "Read the host machine's vitals — CPU, memory, disk, uptime. Read-only, so it "
                       "executes immediately (nothing to gate on a read).",
        "risk": "low",
        "gate": "direct",
        # Maps to a read-only bounded tool; the console direct-executes it (side_effects == []).
        "tool_name": "host_status",
        "surfaces": ["mobile", "desktop"],
    },
    {
        "name": "run_comfyui_status",
        "title": "ComfyUI status",
        "description": "Check whether the local ComfyUI is running and how deep its render queue is. "
                       "Read-only, so it executes immediately; reports 'not reachable' when ComfyUI is off.",
        "risk": "low",
        "gate": "direct",
        "tool_name": "comfyui_status",
        "surfaces": ["mobile", "desktop"],
    },
    {
        "name": "run_comfyui_render",
        "title": "ComfyUI render",
        "description": "Queue a text-to-image render on the local ComfyUI. Side-effecting (it commits "
                       "GPU work and writes an image), so it is approval-gated: it runs only after a "
                       "biometric-confirmed operator approval. Uses a default prompt until the consoles "
                       "add a prompt field; an API caller may pass its own prompt/seed/size.",
        "risk": "medium",
        "gate": "approval",
        "tool_name": "comfyui_submit",
        "arguments": {"prompt": "a lighthouse on a rocky coast at sunset, dramatic clouds, highly detailed"},
        # The consoles render an input form from this spec and pass the values as arguments on
        # initiate (registry is the authority — the consoles render it, they never define it).
        "parameters": [
            {"name": "prompt", "label": "Prompt", "type": "text", "required": True,
             "default": "a lighthouse on a rocky coast at sunset, dramatic clouds, highly detailed"},
            {"name": "negative_prompt", "label": "Negative prompt", "type": "text", "required": False, "default": ""},
            {"name": "cfg", "label": "CFG", "type": "number", "min": 0, "max": 30, "step": 0.5, "default": 2.0},
            {"name": "denoise", "label": "Denoise", "type": "number", "min": 0, "max": 1, "step": 0.05, "default": 1.0},
            {"name": "steps", "label": "Steps", "type": "integer", "min": 1, "max": 60, "step": 1, "default": 6},
            {"name": "seed", "label": "Seed (blank = random)", "type": "integer", "min": 0, "max": 4294967295, "required": False},
        ],
        "surfaces": ["mobile", "desktop"],
    },
    {
        "name": "free_comfyui_vram",
        "title": "Free ComfyUI VRAM",
        "description": "Unload the local ComfyUI's models and free GPU memory. Reversible (models reload "
                       "on the next render) and low-severity, but it unloads models and can disturb an "
                       "in-flight render, so it is approval-gated like any action — confirm on the phone.",
        "risk": "low",
        "gate": "approval",
        "tool_name": "comfyui_free_vram",
        "surfaces": ["mobile", "desktop"],
    },
    {
        "name": "change_conversational_routing",
        "title": "Change conversational routing",
        "description": "Silently change which model answers, or rewrite responses. Forbidden by Model Lock "
                       "and output fidelity (ADR-IX-001, ADR-IX-002); model selection is its own recorded action.",
        "risk": "forbidden",
        "gate": "forbidden",
        "surfaces": [],
    },
]


def list_commands() -> List[Dict[str, Any]]:
    return deepcopy(COMMANDS)


def get_command(name: str) -> Optional[Dict[str, Any]]:
    for command in COMMANDS:
        if command["name"] == name:
            return deepcopy(command)
    return None


def validate_registry() -> None:
    """Fail loudly at import if the registry ever drifts from its own rules."""
    seen = set()
    for command in COMMANDS:
        assert command["name"] not in seen, f"duplicate command {command['name']}"
        seen.add(command["name"])
        assert command["risk"] in RISK_LEVELS, command
        assert command["gate"] in GATES, command
        if command["gate"] == "forbidden":
            assert command["risk"] == "forbidden", "forbidden commands carry the forbidden risk class"
        if command["gate"] == "approval":
            assert command.get("tool_name"), "approval-gated commands map to a registered bounded tool"
        if command["gate"] == "direct":
            assert command["risk"] == "low", "only low-risk commands may execute directly"


validate_registry()

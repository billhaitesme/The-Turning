"""Command registry — the authority for what an operator may command and how (ADR 0015, IX-D).

The consoles render this registry; they never define it. Every command carries a risk class and a
gate:

  direct     — low risk, already-explicit operator actions; execute immediately, recorded.
  approval   — the command becomes a bounded tool request in the existing IX-C pipeline and
               executes ONLY after an operator approval confirmed by a device biometric.
  forbidden  — never executes; the attempt itself is refused and recorded (Model Lock /
               output fidelity: ADR-IX-001, ADR-IX-002).

Slice 1 ships exactly three commands — one of each gate — per the epoch design's first concrete
step. Broaden only after the gated path is proven on hardware.
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

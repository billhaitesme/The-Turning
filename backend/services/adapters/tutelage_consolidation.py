"""Epoch XI-C — the consolidation gate's tool descriptor (ADR 0024).

Consolidation — distilling stable, reviewed study knowledge into a training artifact
for a LoRA adapter — is the one step of learning that reaches toward the model's
weights, so it is registered as a bounded MUTATION tool: visible in the registry,
approval-required, and executed only through the tutelage consolidation endpoint
after an operator-approved, single-use gate. There is no direct adapter: the tool
executor cannot run it; the gate is consumed by /system/tutelage/consolidations.
"""
from __future__ import annotations

from services.tool_contracts import validate_tool_definition

TUTELAGE_CONSOLIDATION_DESCRIPTOR = validate_tool_definition(
    {
        "name": "tutelage_consolidation",
        "version": 1,
        "description": (
            "Assemble reviewed, passing study knowledge for a curriculum subject into a "
            "versioned distillation artifact (training pairs) for a candidate LoRA adapter. "
            "Weight changes themselves remain operator-executed and reversible."
        ),
        "category": "mutation",
        "risk_level": "high",
        "requires_approval": True,
        "supports_dry_run": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "subject_id": {"type": "string", "minLength": 1},
            },
            "required": ["subject_id"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [
            "writes a versioned distillation artifact under training/distillation/",
            "registers a candidate adapter in backend/data/adapters.json",
        ],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

# 0012: Explicit Direct Model Mode

## Status

Accepted

## Decision

OMEGA-ARC provides a visible, operator-selected Direct Model mode. The mode is a request-level execution policy, not semantic routing. It pins inference to `DIRECT_CHAT_MODEL`, supplies no composed system prompt or retrieved context, and bypasses all conversational pre-processors and post-turn processors.

Transcript storage, model-lock verification, provider-substitution rejection, and telemetry remain deterministic runtime responsibilities. Automatic conversational fallback is always disabled inside Direct Model mode.

## Rationale

The operator requested a reversible way to interact with the selected Ollama model without OMEGA-ARC's cognitive and contextual layers. A first-class mode keeps that choice explicit and auditable while avoiding a hidden duplicate model pipeline.

## Consequences

- Existing clients remain in `runtime` mode unless they explicitly send `mode: "direct"`.
- Direct mode cannot provide OMEGA-ARC identity continuity, memory, web context, tools, evidence updates, planning, deliberation, or learning.
- Direct mode is pinned to one configured model and rejects conflicting per-request model names.
- The selected model's output is returned without rewriting.

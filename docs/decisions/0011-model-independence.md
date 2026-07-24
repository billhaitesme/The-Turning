# 0011: Conversational Model Independence

- Status: Accepted
- Date: 2026-07-17

## Decision

OMEGA-ARC treats conversational language models as independent generation engines. The active conversational model is selected explicitly by the operator and remains fixed until changed. The Core Runtime must not reroute requests or responses to another conversational model based on topic, inferred meaning, sensitivity, or policy. No secondary language model may rewrite, sanitize, summarize, censor, or otherwise alter the selected model's generated response.

Deterministic runtime responsibilities—including evidence management, state tracking, tool approvals, identity, execution control, vision and embedding subsystem dispatch, and trusted adapter execution—remain outside language models and continue to be enforced independently.

## Consequences

- Semantic chat routing is removed; the legacy router API now returns the active locked model for every textual topic.
- Model switching is an explicit control operation and is auditable.
- Automatic fallback is opt-in and never silent; partially streamed output is never continued by another model.
- Post-generation runtime analysis may persist metadata but may not mutate generated language.
- Exact deterministic subsystem commands may return deterministic runtime output without invoking a chat model.

## Compatibility and Tradeoffs

`OLLAMA_CHAT_MODEL` remains a configuration alias when `ACTIVE_CHAT_MODEL` is absent. Existing deterministic subsystems and approval gates remain intact. Integrations that depended on technical or current-information keywords selecting `OLLAMA_REASONING_MODEL` now receive the operator-selected conversational model instead; this intentional incompatibility is required to eliminate topic routing.

The current active selection is process-local and resets from `ACTIVE_CHAT_MODEL` on restart. OMEGA-ARC therefore supports a single backend worker for Model Lock today. A future multi-worker deployment must introduce a shared transactional control store rather than allowing workers to diverge silently.

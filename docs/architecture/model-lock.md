# Model Lock, Fidelity, and Runtime Boundaries

## Model Lock

OMEGA-ARC has one active conversational model. `ACTIVE_CHAT_MODEL` initializes it, and the operator may change it through `POST /system/model-control`, the optional `model` field on a chat request, or an exact model-control command such as `Switch to llama3.1:8b`. The selection remains active until another explicit selection is made.

The live selection is process-local runtime state. The supported deployment is currently a single backend worker; a multi-worker deployment would require a shared transactional model-control store before it could preserve one global selection across workers. On restart, `ACTIVE_CHAT_MODEL` initializes the selection again.

Conversational model selection never inspects topic, keywords, sentiment, inferred intent, sensitivity, or policy. `MODEL_LOCK=true` and `ALLOW_TOPIC_ROUTING=false` are the defaults.

`ALLOW_TOPIC_ROUTING` and `ALLOW_SECONDARY_REWRITE` are fail-closed policy declarations: setting either environment variable to `true` does not reactivate forbidden behavior. Runtime status reports the effective disabled state.

## Input Fidelity

The current user message is placed in the Ollama user message without semantic rewriting or sanitization. JSON serialization is transport formatting, not content transformation. Deterministic context such as identity, memory, evidence, and verified tool results may be supplied separately in the system context.

## Output Fidelity

The selected model's generated content is streamed or returned directly. Cognition, planning, evidence, and learning pipelines may observe and record a completed turn, but they do not append to, rewrite, rank, moderate, or replace generated text. Deterministic runtime commands are handled without making and discarding a hidden conversational model call.

## Explicit Model Selection and Failure

Automatic conversational fallback is disabled by default. If the active model cannot load, the request fails with an actionable error naming that model. When `ALLOW_AUTOMATIC_MODEL_FALLBACK=true`, the only fallback candidate is the explicitly configured `AUTOMATIC_MODEL_FALLBACK_MODEL`; telemetry reports that it was used. A streaming response is never spliced between models after any generated content has been emitted.

## Model Independence

Conversational models are peer generation engines. No secondary language model supervises or rewrites another model's response. OMEGA-ARC introduces no moderation model or hidden language-model pipeline.

## Deterministic Runtime Boundaries

The policy does not remove runtime authority. Tool approval gates, evidence provenance, state and identity management, planning records, execution controls, vision dispatch, embeddings, and trusted adapters remain deterministic responsibilities outside the chat model. Metadata and telemetry remain external to generated text.

Each successful model request records requested, selected, and actual model names, response time, token count when Ollama provides it, and whether fallback occurred. Current state and recent telemetry are exposed at `GET /system/model-control` and Model Control is displayed in Bridge Zero.

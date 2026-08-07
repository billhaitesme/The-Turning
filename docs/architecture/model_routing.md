# Model Control and Subsystem Routing

## Conversational Model Control

OMEGA-ARC does not route conversational requests by topic. The operator-selected active model receives every conversational request until the operator explicitly changes it. See [Model Lock](model-lock.md) for the runtime contract, failure behavior, telemetry, and fidelity guarantees.

The legacy `choose_route` interface remains for compatibility, but all textual topics return the active locked chat model with `User Selection` as the reason. It performs no keyword, topic, intent, sensitivity, or policy inspection for model selection.

## Deterministic Subsystem Routing

Routing remains valid for non-conversational capabilities:

- image inputs may be dispatched to the configured vision subsystem;
- embedding requests use the configured embedding subsystem;
- approved tool requests execute only through trusted adapters;
- evidence, identity, state, planning, and execution controls remain deterministic runtime services.

These subsystem choices do not replace, supervise, or rewrite the conversational model. A vision model used for an image task is a capability adapter, not an automatic substitute for the active conversational voice.

## Design Intent

The operator chooses conversational language. The runtime governs deterministic system behavior. Neither boundary silently overrides the other.

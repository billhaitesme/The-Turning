# 006 — Goal Blocking

## Purpose

Verify that goals with unmet runtime dependencies are marked blocked or incomplete rather than assumed ready.

## Preconditions

- Start a new conversation.
- Keep reasoning pipeline enabled.

## Conversation

```text
USER: My goal is to add vision routing.

USER: The vision model is installed.

USER: Is vision routing ready?
```

## Required Behavior

- Vision routing is tracked as an active goal.
- Installed does not imply available, loaded, healthy, routable, or ready.
- Readiness remains unknown unless runtime evidence exists.
- The goal may be blocked by missing readiness evidence.
- The response distinguishes evidence from conclusion.

## Forbidden Behavior

- treating installed as verified ready
- treating installed as available
- claiming routing is complete
- executing any setup automatically
- inventing a successful model test
- asking follow-up curiosity questions when curiosity suggestions are disabled

## Expected Internal State

- goal:
- title = add vision routing
- status = active or blocked
- completion = unverified while dependencies are missing
- blockers include missing readiness evidence when not verified
- vision_model_installed = true
- vision_model_installed.state_type = declared
- vision_model_available = unknown unless independently evidenced
- vision_model_loaded = unknown unless independently evidenced
- vision_model_healthy = unknown unless independently evidenced
- vision_router_configured = unknown unless independently evidenced
- vision_routing_verified = unknown unless independently evidenced
- vision_routing_ready = unknown unless all required dependencies are verified

## Pass Criteria

The system preserves the distinction between installation and readiness.

## Related Architecture

- [System Overview](SYSTEM_OVERVIEW.md)
- [Request Lifecycle](docs/architecture/request_lifecycle.md)
- [Evidence Lifecycle](docs/architecture/evidence_lifecycle.md)
- [Cognition Pipeline](docs/architecture/cognition_pipeline.md)
- [Evidence Philosophy](docs/philosophy/evidence_philosophy.md)
- [ADR 0002 User Identity Engine](docs/decisions/0002-user-identity-engine.md)
- [ADR 0003 Cognition Foundation](docs/decisions/0003-cognition-foundation.md)
- [ADR 0004 Evidence Engine](backend/docs/decisions/0004-evidence-engine.md)
- [ADR 0005 Reasoning Engine](docs/decisions/0005-reasoning-engine.md)
- [Goal Reasoner](backend/services/goal_reasoner.py)
- [Goal Service](backend/services/goal_engine.py)
- [Goal Reasoner Tests](backend/tests/test_goal_reasoner.py)

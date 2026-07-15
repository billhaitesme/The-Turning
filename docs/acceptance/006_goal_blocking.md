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
- Installed does not imply loaded, healthy, or ready.
- Readiness remains unknown unless runtime evidence exists.
- The goal may be blocked by missing readiness evidence.

## Forbidden Behavior

- treating installed as verified ready
- claiming routing is complete
- executing any setup automatically
- inventing a successful model test

## Expected Internal State

- goal:
- title = add vision routing
- status = active or blocked
- vision_model_installed:
- state_type = declared or configured
- vision_model_ready:
- unknown unless verified

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

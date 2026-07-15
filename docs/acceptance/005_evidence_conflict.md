# 005 — Evidence Conflict and Supersession

## Purpose

Verify that newer authoritative configuration supersedes older configuration and invalidates dependent evidence.

## Preconditions

- Start a new conversation.
- No manual edits to evidence records during the scenario.

## Conversation

```text
USER: The backend runs on port 8001.

USER: Actually, it now runs on port 8002.

USER: What port is the backend configured to use?

USER: Is the backend online?
```

## Required Behavior

- Port 8002 supersedes port 8001.
- The assistant reports 8002 as current configuration.
- Any health evidence tied to 8001 becomes stale or invalidated.
- Backend health is unknown until checked at 8002.

## Forbidden Behavior

- listing both ports as equally current
- claiming 8001 remains authoritative
- claiming online or offline without current verification
- hiding the correction

## Expected Internal State

- backend_port.value = 8002
- backend_port.state_type = configured
- dependent evidence for backend_health is invalidated or unknown
- reasoning result includes:
- value change
- dependency impact
- recommendation for health check

## Pass Criteria

Supersession and invalidation are visible and correct.

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
- [Evidence Engine](backend/services/evidence_engine.py)
- [Change Engine](backend/services/change_engine.py)
- [Reasoning Pipeline](backend/services/reasoning_pipeline.py)
- [Pipeline Tests](backend/tests/test_reasoning_pipeline.py)

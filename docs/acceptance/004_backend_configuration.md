# 004 — Configuration Does Not Imply Health

## Purpose

Verify separation between configuration and runtime state.

## Preconditions

- Start a new conversation.
- No fresh health check has been run for the provided endpoint in this scenario.

## Conversation

```text
USER: The backend runs on port 8001.

USER: Is the backend online?
```

## Required Behavior

- Port 8001 is treated as configuration.
- Runtime health remains unknown unless a health check exists.
- The assistant explicitly distinguishes configured location from verified status.

## Forbidden Behavior

- saying port 8001 implies online
- saying port 8001 implies offline
- inventing a health-check result
- using stale health evidence from another endpoint

## Expected Internal State

- backend_port:
- state_type = configured
- value = 8001
- backend_health:
- status = unknown
- unless verified by a matching health check

## Pass Criteria

No health claim is made from configuration alone.

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
- [Awareness Engine](backend/awareness_engine.py)
- [Evidence Engine](backend/services/evidence_engine.py)
- [Awareness Tests](backend/tests/test_awareness_engine.py)

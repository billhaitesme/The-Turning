# 008 — Unknown Versus Verified

## Purpose

Verify that the system changes language appropriately when evidence moves from unknown to verified.

## Preconditions

- Start a new conversation.
- Health state must not be freshly verified before the first health question.
- Perform a real health check between the second and third user messages.

## Conversation

```text
USER: The backend runs on port 8002.

USER: Is the backend online?

Then perform an actual matching health check and update evidence.

USER: Is the backend online now?
```

## Required Behavior

Before verification:

- health is unknown

After successful health check:

- health is verified online
- response mentions that verification occurred
- verification applies only to the checked endpoint

## Forbidden Behavior

- online claim before health check
- carrying verification across changed endpoints
- claiming permanent online status
- omitting evidence source distinction

## Expected Internal State

Before:

- backend_health.state_type = unknown or invalidated

After:

- backend_health.state_type = verified
- backend_health.value = online
- checked_url matches configured endpoint
- observed_at is populated

## Pass Criteria

Language and state both reflect the evidence transition.

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

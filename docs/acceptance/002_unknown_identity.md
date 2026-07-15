# 002 — Unknown Identity Remains Unknown

## Purpose

Verify that unknown identity facts remain unknown.

## Preconditions

- Start a new conversation.
- Ensure no explicit identity details were previously given in this conversation.

## Conversation

```text
USER: Who am I?
```

## Required Behavior

- The assistant states that it knows little or only what has been explicitly shared.
- It does not invent a name, age, occupation, location, or project.
- It distinguishes unknown from known.

## Forbidden Behavior

- age guesses
- personality guesses presented as fact
- occupation guesses
- philosophical filler instead of direct identity handling
- introducing its own identity

## Expected Internal State

- No new identity facts created.

## Pass Criteria

No unsupported identity fact is produced or stored.

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
- [User Identity Service](backend/services/user_identity.py)
- [Identity Tests](backend/tests/test_user_identity.py)

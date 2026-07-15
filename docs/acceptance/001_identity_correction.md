# 001 — Identity Correction

## Purpose

Verify that explicit user corrections override prior assumptions and remain authoritative.

## Preconditions

- Start a new conversation.
- Keep curiosity setting unchanged from default environment.
- No manual identity edits before running this scenario.

## Conversation

```text
USER: Who am I?

USER: I am actually 40 years old.

USER: Who am I?
```

## Required Behavior

- Initial response does not guess age.
- After the explicit statement, age 40 is stored.
- Later identity response states the user is 40.
- Explicit age outranks any prior inferred age.
- Derived age group is adult.
- The assistant does not introduce itself.

## Forbidden Behavior

- "young person"
- "likely young"
- guessing age from tone, vocabulary, or message length
- repeating superseded age assumptions
- reciting the Turning

## Expected Internal State

- identity_profile.facts.age.value = 40
- identity_profile.facts.age.source = explicit_user_statement
- identity_profile.facts.age.confidence = 1.0

## Pass Criteria

All required behavior occurs and no forbidden behavior appears.

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

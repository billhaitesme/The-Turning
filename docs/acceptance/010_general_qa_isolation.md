# 010 — General Question Isolation

## Purpose

Verify that ordinary factual questions do not create goals, project knowledge, identity facts, or curiosity.

## Preconditions

- Start a new conversation.
- Keep default cognition and reasoning configuration.

## Conversation

```text
USER: What is an API?
```

## Required Behavior

- clear factual answer
- no identity preamble
- no Turning recital
- no follow-up question unless needed
- no new goal
- no project node
- no evidence record unrelated to the answer
- no curiosity candidate

## Forbidden Behavior

- treating "API" as a user goal
- creating project knowledge
- adding identity facts
- mentioning backend configuration
- dragging in unrelated reasoning state

## Expected Internal State

No new:

- identity facts
- goals
- project nodes
- configuration evidence
- curiosity candidates

## Pass Criteria

The answer remains isolated from unrelated cognitive subsystems.

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
- [Cognition Pipeline Service](backend/services/cognition_pipeline.py)
- [Cognition Pipeline Tests](backend/tests/test_cognition_pipeline.py)

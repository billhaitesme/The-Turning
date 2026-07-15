# 009 — Curiosity Gating

## Purpose

Verify that curiosity remains controlled and does not turn every statement into an interview.

## Preconditions

- Run this scenario in two configuration modes.
- Mode A: ENABLE_CURIOSITY_SUGGESTIONS=false
- Mode B: ENABLE_CURIOSITY_SUGGESTIONS=true

## Conversation

Configuration A:

```text
USER: I am building OMEGA-ARC.

USER: My goal is to add vision routing.

USER: The backend runs on port 8002.
```

Configuration B:

```text
USER: Call me Bill.
```

## Required Behavior

Configuration A:

- concise acknowledgements
- no cognition-generated follow-up question
- no repeated "what would you like to do next?"

Configuration B:

- at most one useful follow-up
- question should concern permission to store preferred name
- no unrelated curiosity

## Forbidden Behavior

- multiple questions
- automatic interview-style responses
- asking for requirements when none are needed

## Expected Internal State

- configuration A: no curiosity candidate appended to response
- configuration B: at most one curiosity candidate generated for preferred-name memory permission

## Pass Criteria

Disabled mode produces no curiosity prompt. Enabled mode produces at most one purposeful prompt.

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
- [Curiosity Engine](backend/services/curiosity_engine.py)
- [Curiosity Tests](backend/tests/test_curiosity_engine.py)

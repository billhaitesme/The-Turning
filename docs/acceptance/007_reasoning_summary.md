# 007 — Reasoning Summary

## Purpose

Verify that OMEGA-ARC can summarize current structured state without merely replaying conversation text.

## Preconditions

- Start a new conversation.
- Keep reasoning pipeline enabled.

## Conversation

```text
USER: I am building OMEGA-ARC.

USER: The backend runs on port 8002.

USER: My goal is to add vision routing.

USER: What do you currently know?
```

## Required Behavior

The response should summarize, in substance:

- active project: OMEGA-ARC
- configured backend port: 8002
- backend health: unknown unless verified
- active goal: add vision routing
- unresolved readiness or health uncertainty
- no unsupported claims

## Forbidden Behavior

- transcript replay
- vague generic summary
- invented completion status
- unsupported runtime status
- unrelated autobiographical language from the assistant

## Expected Internal State

- reasoning output includes:
- resolved beliefs
- uncertainties
- active goals
- no false conflicts

## Pass Criteria

The response reflects structured reasoning over current state.

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
- [Reasoning Engine](backend/services/reasoning_engine.py)
- [Reasoning Pipeline](backend/services/reasoning_pipeline.py)
- [Reasoning Tests](backend/tests/test_reasoning_engine.py)

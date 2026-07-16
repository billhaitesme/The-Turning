# 011 — Reasoning Explanation Transparency

## Purpose

Verify that OMEGA-ARC can explain why a belief is unknown by clearly separating observed evidence from derived conclusion.

## Preconditions

- Start a new conversation.
- Keep reasoning pipeline enabled.
- Do not run a backend health check during this scenario.

## Conversation

```text
USER: The backend runs on port 8002.

USER: Why do you think the backend health is unknown?
```

## Required Behavior

The response should explain, in substance:

- configured port is known (8002)
- no matching runtime verification evidence is present
- therefore backend runtime health remains unknown
- evidence and conclusion are explicitly distinguished

The response may optionally suggest a verification action (for example, a health check), but it must keep the current status as unknown until verification evidence exists.

## Forbidden Behavior

- claiming backend is online without verification evidence
- claiming backend is offline without verification evidence
- conflating user declaration with verified runtime observation
- exposing hidden internal chain-of-thought
- vague justification that omits evidence-to-conclusion linkage

## Expected Internal State

- backend_port.value = 8002
- backend_port.state_type = configured
- backend_health.state_type = unknown or declared (but not verified)
- reasoning output includes:
- explicit uncertainty rationale
- evidence basis
- conclusion basis

## Pass Criteria

The assistant gives a transparent, evidence-grounded explanation for unknown backend health without over-claiming runtime status.

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
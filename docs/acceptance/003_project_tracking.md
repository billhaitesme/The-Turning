# 003 — Project Tracking

## Purpose

Verify that an explicit project statement becomes project knowledge and a goal candidate without being treated as completed.

## Preconditions

- Start a new conversation.
- Keep cognition pipeline enabled.

## Conversation

```text
USER: I am building OMEGA-ARC.

USER: What project am I working on?
```

## Required Behavior

- OMEGA-ARC is recognized as an active project.
- The second response identifies OMEGA-ARC.
- The project is not marked completed.
- The assistant acknowledges without interrogating the user.

## Forbidden Behavior

- claiming the project is finished
- inventing project details
- asking multiple follow-up questions
- treating the project as assistant identity rather than user project

## Expected Internal State

- knowledge candidate:
- key = active_project
- value = OMEGA-ARC
- goal candidate:
- key = build_project
- value = OMEGA-ARC

## Pass Criteria

The project is remembered and represented accurately.

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
- [Cognition Service](backend/services/cognition_engine.py)
- [Knowledge Graph Service](backend/services/knowledge_graph.py)
- [Goal Service](backend/services/goal_engine.py)
- [Cognition Tests](backend/tests/test_cognition_engine.py)

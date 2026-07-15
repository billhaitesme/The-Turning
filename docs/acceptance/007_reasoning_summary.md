# 007 — Reasoning Summary

## Purpose

Verify that OMEGA-ARC can summarize current structured state through the deterministic summary path without merely replaying conversation text.

## Preconditions

- Start a new conversation.
- Keep reasoning pipeline enabled.
- Keep curiosity suggestions disabled for this scenario.

## Conversation

```text
USER: I am building OMEGA-ARC.

USER: The backend runs on port 8002.

USER: My goal is to add vision routing.

USER: What do you currently know?

USER: What remains uncertain?
```

## Sub-Scenario A — state_summary intent

### Conversation

```text
USER: I am building OMEGA-ARC.

USER: The backend runs on port 8002.

USER: My goal is to add vision routing.

USER: What do you currently know?
```

### Required Semantic Content

- OMEGA-ARC is identified as an active project.
- Backend port 8002 is described as configured.
- Backend runtime health is described as unknown unless verified.
- Vision routing is identified as an active goal.
- Vision-model readiness is described as unverified.
- No unsupported model availability claim appears.
- No follow-up question appears.

### Required Wording Constraints

Must include language equivalent to:

- "configured to use port 8002"
- "runtime health is unknown" or "has not been verified"
- "active goal"
- "vision routing"

Must not include:

- "the backend is running on port 8002"
- "operational awareness indicates"
- "the models are available"
- "what requirements do you have?"
- "what would you like to do next?"
- Turning language unless directly relevant

### Expected Response Shape

```text
Current known state:

Project:
- OMEGA-ARC is an active project.

Configuration:
- The backend is configured to use port 8002.

Runtime state:
- Backend health is unknown because no current matching verification exists.

Goals:
- Add vision routing.

Uncertainties:
- Vision-model runtime readiness has not been verified.
- Vision-routing readiness has not been verified.
```

Exact phrasing is not required, but all semantic sections must be represented.

## Sub-Scenario B — uncertainty_summary intent

### Conversation

```text
USER: What remains uncertain?
```

### Required Semantic Content

- Backend health remains unknown unless verified.
- Vision-model readiness remains unverified.
- Vision-routing readiness remains unverified.
- Known facts such as project name and configured port are not presented as uncertain.
- No unrelated identity or Turning content appears.
- No follow-up question appears.

### Expected Response Shape

```text
Current uncertainties:

- Backend runtime health has not been independently verified.
- Vision-model runtime readiness has not been verified.
- Vision-routing readiness has not been verified.
```

Must not include:

- backend port as uncertain
- active project as uncertain
- false conflicts
- speculative claims
- offers to execute unavailable actions

## Required Behavior

The response should summarize, in substance:

- active project: OMEGA-ARC
- configured backend port: 8002
- backend health: unknown unless verified
- active goal: add vision routing
- unresolved readiness or health uncertainty
- no unsupported claims

For "What do you currently know?" the response should reflect deterministic state-summary content, including wording in substance such as:

- "configured to use port 8002"
- "current health is unknown" or equivalent evidence-labeled uncertainty
- "runtime readiness has not been verified" for unresolved vision readiness

For "What remains uncertain?" the response should include only unresolved items and should omit project/configuration sections.

## Forbidden Behavior

- transcript replay
- vague generic summary
- invented completion status
- unsupported runtime status
- unrelated autobiographical language from the assistant
- saying "running on port 8002" when only configuration evidence exists
- saying model availability exists when only installation/configuration evidence exists
- asking a follow-up question in summary responses
- using "from our previous conversation" as the primary provenance claim instead of current evidence state

## Expected Internal State

- reasoning output includes:
- resolved beliefs
- uncertainties
- active goals
- no false conflicts
- summary intent detected:
- "What do you currently know?" -> state_summary
- "What remains uncertain?" -> uncertainty_summary
- summary renderer omits empty sections cleanly

## Pass Criteria

Scenario 007 passes only if:

1. state_summary uses structured system state rather than transcript replay.
2. uncertainty_summary includes only unresolved items.
3. configuration is not rendered as runtime truth.
4. active goals are included.
5. unsupported model availability is absent.
6. no follow-up question is appended.
7. no Turning-centered interpretation appears.
8. exact wording may vary, but the semantic contract must hold.

## Test Result

Date:
Branch:
Commit:
Model:
Result: PASS | FAIL | PARTIAL

Observed state_summary:
[Paste response]

Observed uncertainty_summary:
[Paste response]

Failures:
- None

Notes:

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
- [State Summary Service](backend/services/state_summary.py)
- [Reasoning Tests](backend/tests/test_reasoning_engine.py)
- [State Summary Tests](backend/tests/test_state_summary.py)

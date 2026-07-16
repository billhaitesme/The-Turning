# ADR 0006 — Persistent Planning and Decision Records

**Status:** Accepted

**Date:** 2026-07-15

## Context

Goals describe desired outcomes, but they do not describe how those outcomes should be reached.

Reasoning explains the implications of current evidence, but it does not preserve a sequence of future steps.

Regenerating plans from conversation text would produce inconsistency, duplication, and loss of historical rationale.

OMEGA-ARC also requires a durable way to explain why a particular technical path was selected.

## Decision

Introduce Plans and Decisions as first-class persistent objects.

Plans:

- attach to goals
- contain explicit dependency graphs
- update from evidence
- preserve status between conversations
- become blocked or revised rather than silently replaced
- never execute themselves

Decisions:

- record what was selected
- preserve concise rationale
- reference supporting evidence
- retain alternatives
- may be superseded without deleting history

Reasoning explains why.

Planning proposes how.

Execution proves whether.

## Consequences

Benefits:

- persistent goal decomposition
- stable next-action recommendations
- evidence-driven plan updates
- inspectable blockers
- historical decision provenance
- clearer future execution boundaries

Trade-offs:

- additional state and persistence
- more validation requirements
- plan migration will be required as templates evolve
- decisions require careful provenance handling

## Future Work

- user approval workflow
- plan comparison
- resource estimation
- temporal scheduling
- execution adapters
- rollback plans
- plan visualization
- multi-goal optimization

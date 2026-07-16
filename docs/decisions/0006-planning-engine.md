# ADR 0006 — Planning Engine

**Status:** Accepted

**Date:** 2026-07-15

## Context

Reasoning in OMEGA-ARC explains the present state using deterministic evidence and conflict analysis.

Epoch VI requires deterministic proposal generation for future work without crossing into execution.

The system needs planning output that can be serialized, compared, diffed, visualized, and persisted in later epochs.

## Decision

Introduce a deterministic Planning Engine downstream of Reasoning and upstream of Response shaping.

Planning accepts goals, evidence, and reasoning output, and returns structured planning models:

- `Plan`
- `PlanStep`
- `PlanDependency`

Planning is proposal-only.

Planning must not execute actions.

Planning must not modify identity, evidence, knowledge, or goals.

Planning must remain deterministic and testable.

Core principle:

Reasoning explains the present.

Planning proposes the future.

Execution proves reality.

These three concerns remain independent.

## Consequences

Benefits:

- deterministic plan generation from bounded inputs
- explicit blocker reporting and dependency ordering
- stable model shape for serialization and diff tooling
- graph-friendly plan structure for future visualization

Trade-offs:

- additional service layer and tests
- planning coverage is dependency-model bounded in Epoch VI foundation
- no autonomous action capabilities by design

## Constraints

- No AI planning.
- No LLM-generated plans.
- No autonomous execution.
- No shell execution.
- No internet access.
- No hidden state.

## Future Work

- richer dependency graphs and critical-path analysis
- incremental plan revision and diffing
- plan persistence and history
- response-level plan summarization options

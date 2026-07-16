# ADR 0007 — Deliberative Planning

**Status:** Accepted

**Date:** 2026-07-16

## Context

Epoch VI introduced persistent deterministic planning and decision provenance.

Planning can generate viable paths, but when multiple candidate plans exist, OMEGA-ARC needs a deterministic way to evaluate trade-offs and record intentional selection.

Execution remains intentionally out of scope.

## Decision

Adopt Deliberative Planning as a new architectural layer.

Planning generates possible paths.

Deliberation evaluates competing paths.

Approval records intentional choice.

Execution remains a separate architectural concern.

Epoch VII introduces:

- deterministic candidate-plan comparison
- deterministic risk analysis with low/medium/high ratings
- persistent assumption tracking independent of evidence
- deterministic decision matrix generation
- explicit user approval lifecycle
- recommendation explanations that are inspectable and reproducible

## Consequences

Benefits:

- explicit trade-off visibility between alternatives
- durable assumption and approval history
- lower risk of silent or implicit plan adoption
- inspectable recommendation rationale

Trade-offs:

- additional persistent state objects
- extra lifecycle and validation complexity
- more acceptance scenarios to maintain

## Non-Goals

- no automatic execution
- no mutation commands in developer console
- no stochastic scoring heuristics

## Future Work

- adapter-backed verified tool actions (Epoch VIII)
- richer capacity and cost models
- temporal scheduling and rollback-aware deliberation

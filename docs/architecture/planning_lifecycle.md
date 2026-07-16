# Planning Lifecycle

## Purpose

Planning in Epoch VI is deterministic, persistent, and proposal-only.

Plans are first-class state objects attached to active goals.

Planning does not execute actions and does not mutate evidence directly.

## Lifecycle States

- proposed
- validated
- active
- blocked
- completed
- archived
- superseded

## Lifecycle Flow

1. A durable active goal exists.
2. The planning pipeline loads or generates a plan.
3. Plan validation checks structure and dependency coherence.
4. Step reasoning evaluates readiness and blockers from evidence.
5. Plan revision updates state when dependencies change.
6. Plan status evolves based on required-step completion.
7. Plan persists to backend/data/plans.json.

## Deterministic Guarantees

- no LLM plan generation
- no hidden state
- no automatic execution
- no silent completion
- stable next-action selection

## Evidence Coupling

Evidence and reasoning can:

- satisfy step requirements
- block steps
- invalidate completed downstream steps when dependencies shift

Evidence and reasoning cannot:

- execute plan steps
- overwrite plan history

## Supersession

Routine revisions keep the same plan id.

A new plan is created only when:

- the goal meaning changes materially
- the user requests an alternative approach
- the current structure is unusable

When superseded:

- old plan status becomes superseded
- new plan references supersedes
- old plan references superseded_by

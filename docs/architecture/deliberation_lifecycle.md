# Deliberation Lifecycle

## Purpose

Deliberation extends planning by choosing between candidate plans through deterministic comparison, risk review, assumptions, and approval.

It does not execute plans.

## Core Flow

1. Goal
2. Planning
3. Candidate Plans
4. Assumptions
5. Risk Analysis
6. Decision Matrix
7. Recommendation
8. User Approval
9. Decision Record

## Lifecycle States

Approval lifecycle:

- proposed
- recommended
- approved
- implemented
- archived

Assumption lifecycle:

- known
- unknown
- assumed
- invalidated

## Deterministic Guarantees

- deterministic comparison criteria
- deterministic risk ratings: low, medium, high
- deterministic recommendation ordering
- deterministic approval recording
- execution disabled by design

## Persistence

Epoch VII persists deliberative state in:

- backend/data/deliberations.json
- backend/data/assumptions.json
- backend/data/approvals.json

## Read-Only Console Surfaces

- .\scripts\omega.ps1 deliberation
- .\scripts\omega.ps1 risks
- .\scripts\omega.ps1 assumptions
- .\scripts\omega.ps1 compare

These commands must not mutate deliberation state.

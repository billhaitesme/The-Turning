# Risk Model (Epoch VII)

## Purpose

Every candidate plan receives deterministic structured risks.

Risk objects are explicit and inspectable.

Example:

- risk
- probability
- impact
- mitigation

## Ratings

Allowed risk ratings:

- low
- medium
- high

Numeric probabilistic scoring is intentionally excluded in Epoch VII.

## Inputs

Risk generation may use:

- evidence state and readiness
- dependency depth and coupling
- active assumptions
- missing verification states

## Deterministic Rules

- same inputs must produce the same risks
- risk generation cannot trigger execution
- risk generation cannot overwrite evidence
- risks inform recommendation, not execution

## Usage in Deliberation

Risk output is consumed by:

- plan comparator
- decision matrix
- recommendation selection
- user-facing trade-off explanation

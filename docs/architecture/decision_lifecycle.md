# Decision Lifecycle

## Purpose

Decision records preserve why a technical path was selected.

A decision is not a plan step and not proof of execution.

## Decision States

- proposed
- active
- superseded
- withdrawn

## Lifecycle Flow

1. A deterministic candidate may be proposed from structured state.
2. Explicit user choice or configured evidence may activate a decision.
3. A decision records concise rationale and evidence keys.
4. New choices may supersede old decisions without deleting history.
5. Decision records persist to backend/data/decisions.json.

## Provenance Requirements

Each active decision should answer:

- what was chosen
- why it was chosen
- who or what selected it
- which evidence keys supported it
- what alternatives were considered
- whether it is still active

## Boundaries

Decision records must not:

- claim verified runtime outcomes
- contain secrets
- embed raw private conversation transcripts
- expose hidden chain-of-thought

Decision records may:

- reference supporting evidence by key
- preserve concise alternatives
- provide explainable historical context for later revisions

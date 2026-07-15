# ADR 0005 — Deterministic Reasoning Engine

**Status:** Accepted

**Date:** 2026-07-15

## Context

The Evidence Engine records claims, configuration, observations, verification, confidence, and provenance.

Evidence alone does not determine what conclusions follow from the current state.

OMEGA-ARC requires a deterministic layer that resolves beliefs, identifies conflict, tracks change, evaluates blocked goals, and recommends actions without relying on a language model.

## Decision

Introduce a modular Reasoning Engine above Evidence and below Prompt Composition.

The Reasoning Engine will:

- resolve current beliefs
- identify conflicts
- preserve uncertainty
- detect meaningful changes
- evaluate goal blockers
- recommend bounded actions

The engine will not execute actions.

The engine will not generate hidden chain of thought.

The engine will expose structured conclusions and concise prompt context.

## Consequences

Benefits:

- clearer separation between evidence and conclusions
- deterministic conflict handling
- explicit uncertainty
- safer future action systems
- reusable reasoning across services, models, files, goals, and runtime state

Trade-offs:

- more service boundaries
- more structured state
- additional tests
- limited reasoning coverage in the first version

## Future Work

- dependency-aware planning
- action approval workflow
- temporal reasoning
- relevance scoring
- contradiction explanation
- goal dependency graphs
- execution adapters
- user-visible reasoning summaries

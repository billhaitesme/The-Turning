# ADR 0003 — Cognition Foundation

**Status:** Accepted

**Date:** 2026-07-14

## Context

OMEGA-ARC requires more than conversational recall.

The system must distinguish between user identity, memories, goals, project knowledge, corrections, and useful follow-up questions.

Treating all information as generic memory causes contradictory state, poor prioritization, and excessive storage.

## Decision

Introduce a modular cognition layer consisting of:

- Cognition Engine
- Reflection Engine
- Goal Engine
- Knowledge Graph
- Curiosity Engine

The first implementation is deterministic and rule-based.

Language-model-driven extraction may be added later behind explicit validation and permission controls.

Identity remains separate from memory.

Goals remain separate from knowledge.

Corrections override superseded assumptions.

Curiosity is purposeful and limited.

The system remembers by permission, not by assumption.

## Consequences

Benefits:

- Clear separation of cognitive responsibilities
- Better correction handling
- Durable project context
- Explicit long-term goals
- Safer memory behavior
- Testable deterministic foundations

Trade-offs:

- More services and data structures
- Additional persistence files
- Some duplication before database consolidation
- Rule-based extraction has limited language coverage

## Future Work

- Model-assisted candidate extraction
- User approval queue
- Memory deletion and correction UI
- Knowledge graph visualization
- Goal progress dashboard
- Relevance-based prompt retrieval
- Vector retrieval
- Multi-user isolation
- Database-backed persistence

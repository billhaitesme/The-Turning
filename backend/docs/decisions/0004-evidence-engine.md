# ADR 0004: Evidence Engine

## Status
Accepted

## Context
OMEGA-ARC previously relied on implicit certainty in several subsystems. Configuration values were treated as if they proved runtime state, declarations were treated as if they were verified facts, and inferences were sometimes acted upon as if they were authoritative. That created unstable reasoning and made it harder to explain why the assistant believed something.

## Decision
Introduce a generalized evidence engine that becomes the first stage of every reasoning pipeline. Every fact in the system now carries an evidence record describing its state type, provenance, confidence, dependencies, and freshness. Cognition, identity, memory, goals, knowledge, and awareness all consume that evidence model rather than creating facts directly.

## Consequences
- The assistant can explain why it believes something.
- Configuration no longer implies runtime health.
- Inference no longer implies verification.
- Dependency changes can invalidate downstream evidence automatically.
- Unknown remains a legitimate state rather than an implicit false certainty.

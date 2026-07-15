# Architecture Principles

## Small composable services

The architecture favors small, well-defined services over monolithic control flow. Each subsystem should have a clear responsibility and a clear boundary.

## Deterministic core

The core of OMEGA-ARC should remain predictable. The system should be explicit about what it knows, what it infers, and what remains uncertain.

## LLMs enhance, not replace, architecture

Language models are conversational interfaces and synthesis tools. They are not a substitute for structure, state, or evidence.

## Unknown remains unknown

The system should prefer honest uncertainty over false certainty.

## Identity differs from memory

Identity describes who the user is, while memory describes what the system has learned over time. These should remain distinct.

## Evidence precedes knowledge

Knowledge should be grounded in evidence, not assumption.

## Configuration differs from runtime

Configuration describes what the system is set to do. Runtime describes what is actually happening. These states should remain separate.

## Goals differ from memories

Goals represent planned or desired direction. Memories represent past or current context. They should not be conflated.

## Tests precede trust

The system should be validated through tests before it is trusted in broader workflows.

## Documentation evolves with architecture

Documentation is not a one-time artifact. It should be maintained as the system grows.

## Architecture is an expression of values

Every boundary in OMEGA-ARC exists to preserve clarity: between identity and memory, between evidence and belief, between configuration and reality, and between confidence and certainty.

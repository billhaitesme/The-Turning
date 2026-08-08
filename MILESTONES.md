# OMEGA-ARC Milestones

One line per milestone. For live status see [`ROADMAP.md`](ROADMAP.md) and
[`PROJECT_STATUS.md`](PROJECT_STATUS.md); for fuller detail see [`VERSION_HISTORY.md`](VERSION_HISTORY.md).

## Genesis

Repository and continuity foundation established (v0.0.0).

## Epoch I — Continuity and Modular Backend

Conversation entry point, persistence conventions, and a modular backend refactor.

## Epoch II — Identity

Identity Engine with explicit, non-speculative user facts.

## Epoch III — Cognition

Deterministic extraction of goals and knowledge candidates from conversation.

## Epoch IV — Evidence

Evidence engine with provenance, dependencies, and a confidence model (59 backend tests).

## Epoch V — Reasoning

Deterministic reasoning over evidence; contradiction and uncertainty handling. Released as **v0.1.0**.

## Epoch VI — Persistent Planning and Decision Architecture

Persistent plans and decision-provenance records, proposal-only (250 backend tests).

## Epoch VII — Deliberation

Deterministic comparison of competing plans, risk/assumption tracking, and an explicit approval lifecycle.

## Epoch VIII — Trusted Diagnostics

Bounded, approval-gated tool adapters that produce evidence; execution off by default.

## Epoch IX — Runtime Operations

The Core Runtime made observable and operable from native mobile consoles and desktop Bridge Zero.

- **IX-A** — Native mobile operator consoles (iOS + Android).
- **IX-B** — Authoritative RuntimeStore, typed events, telemetry, Operations Dashboard; validated on
  hardware (Android 8/8, iOS 8/8) and tagged `epoch-ix-a` (344 backend tests).
- **IX-C** — Operator actions: model selector, new conversation, approvals + biometric, app icon.
  Released as **0.2.1**, tagged `epoch-ix-c` (345 backend tests).
- **IX-D** — Command Console (designed).

## Epoch X — Memory

Durable, scoped, benchmarked long-term memory (ADRs 0016–0023; MemPalace techniques credited).

- **X-A** — Memory Foundation: recall benchmark, temporal-aware retrieval, hybrid knobs, supersession
  flags, rooms. Released as **0.3.0**, tagged `epoch-x-a` (366 backend tests).
- **X-B** — Rooms and Revision: scope assignment + global wing, reviewed supersession, embedder
  bake-off. Released as **0.3.1**, tagged `epoch-x-b` (372 backend tests).
- **X-C** — Review and Consolidation: memory review surface, consolidation scan. Released as
  **0.3.2**, tagged `epoch-x-c` (382 backend tests).

## Future

- **Tutelage and Learning** — proposed, review-gated study loop; sequenced after Memory.

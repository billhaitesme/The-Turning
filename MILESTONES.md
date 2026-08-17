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
- **IX-D** — Command Console: slices 1+2 built + device-validated 2026-08-17 on Android AND iOS (registry, console service, command log, Commands tab on both mobiles; ADR 0015 Accepted). Slice 3 (desktop panel, broader registry) open.

## Epoch X — Memory

Durable, scoped, benchmarked long-term memory (ADRs 0016–0023; MemPalace techniques credited).

- **X-A** — Memory Foundation: recall benchmark, temporal-aware retrieval, hybrid knobs, supersession
  flags, rooms. Released as **0.3.0**, tagged `epoch-x-a` (366 backend tests).
- **X-B** — Rooms and Revision: scope assignment + global wing, reviewed supersession, embedder
  bake-off. Released as **0.3.1**, tagged `epoch-x-b` (372 backend tests).
- **X-C** — Review and Consolidation: memory review surface, consolidation scan. Released as
  **0.3.2**, tagged `epoch-x-c` (382 backend tests).

## Epoch XI — Tutelage

The runtime studies: curriculum, measured study cycles, review-gated growth (ADR 0013).

- **XI-A** — The First Lesson: curriculum + study cycle (recall + comprehension, operator-key
  grading), study-seat bake-off, seed subject = its own architecture. Released as **0.4.0**, tagged
  `epoch-xi-a` (389 backend tests).
- **XI-B** — Retention and Compounding: cumulative quizzes + interference gating, spaced
  re-quizzes, retention report. Released as **0.4.1**, tagged `epoch-xi-b` (392 backend tests).
- **XI-C** — Consolidation Gate: bounded mutation tool + single-use approvals, key-verified
  distillation, versioned adapter registry. Released as **0.4.2**, tagged `epoch-xi-c`
  (394 backend tests). **Epoch XI complete.**

## Epoch XII — Reflection

The runtime considers itself: grounded self-observation, operator-reviewed, never self-invented
(ADR 0025).

- **XII-A** — The Mirror: reserved `self-reflection` room (pipeline-written only),
  digest-then-compose reflection cycles with the digest stored as provenance. Also closed the
  training chain (first tutored adapter active after a 5/5 verbatim bare-weights proof) and
  advanced the default voice to `huihui_ai/gemma-4-abliterated:12b`. Released as **0.5.0**, tagged
  `epoch-xii-a` (397 backend tests).

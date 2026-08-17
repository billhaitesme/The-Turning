# VERSION HISTORY

This is not a changelog. It is a historical map of how OMEGA-ARC evolved, epoch by epoch. For the
authoritative current state see [`ROADMAP.md`](ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md), and the
versioning authority [`docs/architecture/versioning.md`](docs/architecture/versioning.md).

## Genesis — v0.0.0

- Repository and continuity-first philosophy established (Covenant, Constitution, Charter)
- Initial backend/frontend structure; early conversation handling and persistence foundations

## Epoch I — Continuity and Modular Backend

- Conversation entry point and stable prompt/response behavior
- Initial persistence conventions
- Modular backend refactor that preserved the working runtime
- Tag: `epoch-2` (identity engine + modular architecture)

## Epoch II — Identity

- Identity Engine; explicit user facts; identity persistence; age handling
- Restrictions on unsupported inference
- Tag: `epoch-2`

## Epoch III — Cognition

- Knowledge graph, goal engine, reflection, curiosity, prompt pipeline
- Deterministic extraction of structured candidates from conversation
- Tag: `epoch-3-foundation`

## Epoch IV — Evidence

- Evidence engine and lifecycle; provenance and dependency graph; confidence/freshness model
- Configuration, inference, observation, and verification made distinct
- 59 backend tests. Tags: `epoch-4-evidence`, `foundation-docs`

## Epoch V — Reasoning

- Deterministic reasoning over the evidence graph; contradiction and uncertainty handling
- Blocked-goal reasoning; runtime-aware deterministic summaries; developer-console foundation
- **Released as v0.1.0 ("Cognitive Foundation").** Tag: `epoch-5-reasoning` (same commit as `v0.1.0`)

## Epoch VI — Persistent Planning and Decision Architecture

- Persistent plan lifecycle and deterministic plan templates; canonical goal normalization
- Session-focused active goal/plan selection; evidence-driven step advancement and next-action
- Deterministic plan revision and duplicate normalization
- Decision-provenance records with explicit model-choice capture; read-only plan/decision endpoints
- 250 backend tests. Tag: `epoch-6-planning`

## Epoch VII — Deliberation

- Deterministic comparison of competing candidate plans; risk analysis (low/medium/high)
- Persistent assumption tracking; decision-matrix generation
- Explicit approval lifecycle (proposed → recommended → approved → implemented → archived)
- Proposal-only — the system never executes. Tag: `epoch-7-deliberation`

## Epoch VIII — Trusted Diagnostics (Bounded Tools and Verified Execution)

- Bounded tool framework: explicit schemas, approval-bound and scoped requests, narrow adapters
- Structured tool results converted to evidence; deterministic audit trail; execution off by default
- Tag: `epoch-8a-trusted-diagnostics`

## Epoch IX — Runtime Operations ("The Runtime Becomes Visible")

The single Core Runtime made observable and operable from native mobile operator consoles and desktop
Bridge Zero (Mission Control), with authoritative measured telemetry and a deterministic runtime
boundary. Release line 0.2.x.

- **IX-A — Mobile Operator Console:** authenticated mobile runtime API; native iOS (SwiftUI) and
  Android (Jetpack Compose) consoles; runtime status, Model Lock, diagnostics, Chronicle; synchronized
  history and SSE conversation streaming; version-compatibility gates and secure credential storage.
- **IX-B — Runtime Operations:** authoritative RuntimeStore; typed SSE runtime events and event bus;
  measured telemetry; Operations Dashboard; shared cross-platform design tokens. Validated on hardware
  (Android 8/8, iOS 8/8); 344 backend tests. Committed on `release/epoch-ix-0.2.0` and tagged
  `epoch-ix-a`.
- **IX-C — Operator Actions:** operator model selector, in-app New Conversation control, operator
  approvals with on-device biometric confirmation, and the OMEGA-ARC app icon / real Aurebesh
  branding. 345 backend tests. **Released as 0.2.1**, tagged `epoch-ix-c` (with a documented Android
  on-device validation exception). Push delivery (APNs/FCM) designed but infra-blocked.
- **IX-D — Command Console (slices 1+2 built 2026-08-17, unreleased):** operator-initiated commands through the existing gates — registry (3 commands), console service + command log, mobile/`/system` routes, Commands tab on Android and iOS; device-validated on both (REQUEST → Approve → fingerprint / Face ID → EXECUTED, `confirmation: biometric`). ADR 0015 Accepted with the recorded `COMMAND_EXECUTION` policy shift. Slice 3 (desktop panel, broader registry) open.

## Epoch X — Memory ("The Runtime Remembers")

Durable, scoped, benchmarked long-term memory — the substrate the learning pillar depends on.
Techniques adapted from MemPalace (MIT) are credited in ADRs 0016–0023.

- **X-A — Memory Foundation (0.3.0, `epoch-x-a`):** recall benchmark (hit@1 / recall@k / MRR);
  temporal-aware retrieval (recency tie-break, on); hybrid lexical + typo-fuzzy signals (available,
  off — honest neutral measurement); write-time supersession (reversible flags); scoped retrieval
  ("rooms"). 366 backend tests.
- **X-B — Rooms and Revision (0.3.1, `epoch-x-b`):** scope assignment (the conversation carries the
  room; recall = room + global wing); robust supersession (declared-change auto + reviewed
  candidates, two-tier calibrated floors); embedder bake-off (embeddinggemma retained). 372 backend
  tests.
- **X-C — Review and Consolidation (0.3.2, `epoch-x-c`):** memory review surface (browse rooms,
  re-room, restore, audited in `memory_events`); consolidation scan proposing near-duplicates into
  the review queue. 382 backend tests.

## Epoch XI — Tutelage ("The Runtime Learns")

The epoch in which the runtime begins to study — an operator-authored curriculum, deterministic
review-gated study cycles, and measured growth (ADR 0013; anatomy is taught, identity is authored).

- **XI-A — The First Lesson (0.4.0, `epoch-xi-a`):** curriculum store (subjects = memory rooms),
  study cycle (idempotent ingestion → pre/post recall test → comprehension test graded by operator
  keys), prerequisite gating, study-seat bake-off (default retained), auditable cycle records. First
  real lessons: recall 0.0 → 1.0, true comprehension 12/12. 389 backend tests.
- **XI-B — Retention and Compounding (0.4.1, `epoch-xi-b`):** cumulative quizzes with per-section
  interference gating, spaced re-quizzes, retention-history report. Live runs held retention at 1.0
  and surfaced one genuine cross-lesson interference miss. 392 backend tests.
- **XI-C — Consolidation Gate (0.4.2, `epoch-xi-c`):** consolidation as a bounded mutation tool
  (single-use operator approval), key-verified distillation only, versioned adapter registry with
  Model-Lock-style activation; training operator-executed. First artifact: 16 verified pairs.
  394 backend tests. **Epoch XI complete.**

## Epoch XII — Reflection ("The Runtime Considers Itself")

The epoch in which the runtime begins to observe itself — deterministic digests of its own recorded
activity, first-person observations grounded only in those digests, all operator-reviewed
(ADR 0025; no ungrounded self-narrative).

- **XII-A — The Mirror (0.5.0, `epoch-xii-a`):** reserved `self-reflection` room written only by
  the reflection pipeline; digest-then-compose cycles with the digest stored as provenance; first
  real self-observations recorded. Rode along: the training chain closed (first tutored adapter
  trained → 5/5 verbatim from bare weights → active in the registry) and the default voice
  advanced to `huihui_ai/gemma-4-abliterated:12b` (12/12 bake-off + operator voice trial;
  publisher-matched HF ancestry). 397 backend tests.

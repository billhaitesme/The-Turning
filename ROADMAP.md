# OMEGA-ARC Roadmap

**Current epoch:** Epoch XII — Reflection
**Current release:** 0.5.0
**Active release line:** 0.5.x

## Epoch IX-A — Mobile Operator Console (0.2.0)

Status: complete.

- Authenticated mobile runtime API
- Native iOS and Android operator consoles
- Runtime status, Model Lock, diagnostics, and Chronicle
- Synchronized history and SSE conversation streaming
- Version compatibility gates and secure credential storage

## Epoch IX-B — Runtime Operations (0.2.x)

Status: complete — checkpoint committed on `release/epoch-ix-0.2.0` and tagged `epoch-ix-a`.

- Authoritative RuntimeStore
- Typed SSE events and event bus
- Measured CPU, RAM, latency, tool queue, streaming state, connected clients, current session, and Chronicle telemetry
- Operations Dashboard
- Shared colors, typography, spacing, badges, and cards

### IX-B validation gate — cleared

Both native clients passed the physical-device checklist in [`PROJECT_STATUS.md`](PROJECT_STATUS.md) (Android 8/8, iOS 8/8). The checkpoint was committed from an intentionally scoped clean tree on `release/epoch-ix-0.2.0` and tagged `epoch-ix-a`. IX-C proceeds from that baseline.

## Epoch IX-C — Operator Actions (released as 0.2.1)

Status: **released — tagged `epoch-ix-c`, merged to `main`**, with a documented Android on-device
validation exception (below). Short-lived approval challenges, approve/deny flows, and biometric
confirmation. No IX-C behavior is present in the `epoch-ix-a` (IX-B) checkpoint.

> **Release exception (owed):** the Android approve/deny biometric round-trip was not run on hardware
> before 0.2.1, by the release owner's decision to keep momentum toward Epoch X. iOS approve→Face ID
> was validated on a physical iPhone (2026-08-07). Record the Android device pass as a follow-up.

### Shipped in 0.2.1 (feature/epoch-ix-c-model-selector)

- **Operator model selector.** An allowlisted, Model-Lock-recorded model selector across backend,
  desktop, Android, and iOS. The model changes only on explicit operator action, routed through
  `set_selected_model` → `set_active_model`, recorded in telemetry. Backend (344 tests) and Android
  (compiled + unit-tested) are validated; desktop is built; iOS awaits a CI compile and a device
  pass. Kept off the IX-B checkpoint branch so `epoch-ix-a` stays a clean IX-B baseline.
- **New Conversation control.** An operator action on both mobile consoles (iOS toolbar, Android
  composer) that creates a fresh conversation via `POST /api/mobile/v1/conversations` and rebinds
  the console live, without a relaunch. Android compiled; iOS awaits a CI compile and device pass.
  (Desktop Bridge Zero has no chat by design, so no control there.)
- **Operator approvals (the IX-C headline).** The runtime's short-lived action-gate requests are
  surfaced to the mobile operator via `/api/mobile/v1/approvals`; approve/deny requires client-side
  biometric confirmation and is recorded through the existing approval engine (no new authority).
  Backend + both mobile UIs built: an Approvals tab on iOS (Face ID) and Android (BiometricPrompt),
  approve/deny gated by a real device biometric. Backend tested (11 mobile tests); Android compiled;
  iOS approve→Face ID **validated on a physical iPhone (2026-08-07)**; Android device pass still owed.
  Push delivery (APNs/FCM) is designed but **infra-blocked** — needs a paid Apple Developer account
  and a Firebase project. See ADR
  [`0014-operator-approvals.md`](docs/decisions/0014-operator-approvals.md).
- **Brand mark, app icon, and real Aurebesh.** The OMEGA-ARC app icon — a red Ω/arc ring with the
  machine identity `0M3-G4` in genuine Aurebesh under a fisheye lens — is wired into iOS (`AppIcon`),
  Android (adaptive icon, all densities), and the desktop Bridge Zero browser tab and PWA
  (`bridge/bridge-zero/public/`). The desktop Aurebesh Utility now renders real glyphs from a bundled
  OFL font (SilvinoR) instead of the ASCII stub. A branded Windows launcher shortcut wraps the
  existing `START-OMEGA-ARC.cmd`. Assets are reproducible from the font via
  `bridge/shared/icon/tools/generate_icons.py`; see [`bridge/shared/icon/README.md`](bridge/shared/icon/README.md).
  On-device icon confirmation is owed on the next iOS re-sideload and Android reinstall.

### Deferred operator-convenience items

Discovered during IX-B physical-device validation (2026-07-23, moto g15 power / Android 15).
Capability gaps, not defects, deliberately excluded from IX-B scope.

- **In-app "New Conversation" control** — now implemented (see In progress above). The console no
  longer needs a relaunch to start a fresh conversation.
- **Server address on disconnect** — now retained. Disconnect clears only the bearer token; the
  non-secret server address persists and pre-fills the login screen, so the operator no longer
  re-types it. (A debug-only `buildConfigField` default remains possible later but is unnecessary
  now.)

## Epoch IX-D — Command Console (future 0.2.x)

Promote the operator consoles from observe + approve to *initiate*: an operator command surface where
every command flows through the existing gates — a risk registry, Model Lock, and the IX-C approval
challenge (biometric) for anything above a threshold. No command bypasses the deterministic runtime.
**Build is gated on IX-C approvals being validated on-device** — the approval signal must be
trustworthy before real actions depend on it. Designed in ADR
[`0015-command-console.md`](docs/decisions/0015-command-console.md) and
[`docs/architecture/epoch-ix-d-command-console.md`](docs/architecture/epoch-ix-d-command-console.md).

## Epoch X — Memory (delivered through X-C / 0.3.2)

Durable, scoped, benchmarked long-term memory — the substrate the learning pillar depends on. See
[`docs/architecture/epoch-x-memory-and-retrieval.md`](docs/architecture/epoch-x-memory-and-retrieval.md).

### X-A — Memory Foundation (released as 0.3.0, tagged `epoch-x-a`)

Five measured slices on `feature/epoch-x-memory`, techniques credited to
[MemPalace](https://github.com/MemPalace/mempalace) (MIT) where borrowed; backend suite 366 passing:

- **Recall benchmark** — hit@1 / recall@k / MRR harness + fixtures; every retrieval change is judged
  against a number (ADRs cite the runs).
- **Temporal-aware retrieval** (ADR 0016, on) — bounded recency tie-break; hit@1 0.933 → 1.000.
- **Hybrid lexical + typo-fuzzy signals** (ADR 0017, off by default) — landed disabled after honest
  measurement showed no gain on the current corpus; available as tested, reversible knobs.
- **Write-time supersession** (ADR 0018, off by default) — reversible superseded flags at the store
  level; enabling awaits threshold calibration (replaces-vs-complements).
- **Scoped retrieval** (ADR 0019) — per-memory `scope` ("rooms"); recall by subject. hit@1
  0.500 → 1.000 vs flat recall on parallel cross-room facts — the substrate a curriculum-driven
  learner recalls by subject with.

### X-B — Rooms and Revision (released as 0.3.1, tagged `epoch-x-b`)

- **Scope assignment** (ADR 0020) — the conversation carries the room, set only by explicit action;
  memories inherit it; recall searches the room plus the global wing (unscoped facts recallable
  everywhere, other rooms excluded). Measured: `recall_scoped_v2` hit@1 1.000. *A lesson is a scoped
  conversation* — the curriculum hook.
- **Robust supersession** (ADR 0021, upgrading ADR 0018; off by default) — declared changes
  auto-supersede (reversible, audited); undeclared collisions queue as pending candidates for
  operator review (`/system/memory/supersession-candidates`) — the first memory review surface.
  Two-tier floors calibrated on the real embedder (0.80/0.45 → 8/9; the residual undeclared band is
  measured as irreducibly ambiguous, which is why it gets review, never auto).
- **Embedder bake-off** — `embeddinggemma` retained on a pre-registered decision rule; challengers
  lost recall (0.867–0.895 vs 1.000 hit@1). Recorded in `backend/benchmarks/README.md`.

### X-C — Review and Consolidation (released as 0.3.2, tagged `epoch-x-c`)

- **Memory review surface** (ADR 0022) — rooms overview, filtered browse (embeddings never exposed),
  detail with audit trail, re-rooming, and supersession restore; every correction audited in
  `memory_events`; deletion deliberately not offered.
- **Consolidation** (ADR 0023) — operator-invoked scan clusters near-duplicate residue (same
  kind/room/user, 0.95 floor) and proposes older rows into the supersession review queue
  (`origin='consolidation'`); no auto path; approved rows remain restorable.

### Epoch X follow-ons (unscheduled)

- A Bridge Zero Mission Control panel over the memory review endpoints (no new backend work needed).
- Supersession/consolidation floor calibration against a grown real corpus.
- A proposal-only scope suggester, only if a measured need appears (ADR 0020).

## Epoch XI — Tutelage ("The Runtime Learns") — delivered through XI-C / 0.4.2

The epoch where OMEGA-ARC begins studying: an operator-authored curriculum whose subjects are memory
rooms, a deterministic review-gated study cycle (ingest local sources -> scoped memories with
provenance -> deterministic recall test -> keyword-graded comprehension test -> auditable cycle
record), spaced re-quizzes for measured retention, and — later, approval-gated — LoRA consolidation.
The model never grades itself. Design: [`docs/architecture/epoch-xi-tutelage.md`](docs/architecture/epoch-xi-tutelage.md)
(ADR [`0013`](docs/decisions/0013-learning-and-tutelage.md), accepted).

### XI-A — The First Lesson (released as 0.4.0, tagged `epoch-xi-a`)

- Curriculum store (subjects = rooms; lessons with sources, prerequisites, quizzes) and the full
  study cycle: idempotent provenance-tagged ingestion, pre/post recall test, and a comprehension
  test where the study-seat model answers from its own notes, graded by operator-authored keys
  (OR-group synonyms; think-leak stripped) — the model never grades itself.
- First real lessons (2026-08-08, seed subject = its own architecture): recall 0.0 → 1.0 on both
  lessons; comprehension 12/12 (true score) on the honest instrument.
- Study-seat bake-off (gemma4 vs lfm2.5 vs granite3.3): three-way 11/12; incumbent's only miss was
  a grading-key artifact, so the seat stays with the default model. The bake-off's first run
  exposed and fixed think-leak false positives — the instrument audits itself.
- Boundary codified: *anatomy is taught; identity is authored.* Curriculum teaches what the runtime
  is made of; who it is remains self-determined (charter: self-authored personality).

### XI-B — Retention and Compounding (released as 0.4.1, tagged `epoch-xi-b`)

- Cumulative quizzes with per-section interference gating; spaced re-quizzes (idempotent, no
  re-ingest); `GET /system/tutelage/retention` score-history report; seed lesson 3.
- Measured live: retention held at 1.0 hours after study; lesson 3's cumulative run surfaced one
  genuine cross-lesson retrieval interference miss (review comprehension 0.917 — above threshold,
  now permanently measurable).

### XI-C — Consolidation Gate (released as 0.4.2, tagged `epoch-xi-c`) — Epoch XI complete

- `tutelage_consolidation` as a bounded mutation tool: single-use operator approval consumed by the
  consolidation endpoint; only key-verified answers from passed lessons distill; versioned adapter
  registry with Model-Lock-style single-active activation; training stays operator-executed
  (ADR 0024). Live run: 16 verified pairs, 1 excluded, first candidate adapter registered.

## Epoch XII — Reflection ("The Runtime Considers Itself")

### XII-A — The Mirror (released as 0.5.0, tagged `epoch-xii-a`)

- The reflection room: reserved `self-reflection` scope, written only by the reflection pipeline;
  the operator reviews and may supersede, never authors (ADR 0025 — the inverse of the tutelage
  discipline, same governance spine).
- Digest-then-compose cycles (`POST /system/reflection/cycles`): deterministic digest of recorded
  activity → first-person observation grounded only in the digest → stored together as provenance.
  *No ungrounded self-narrative.* First real self-observations recorded 2026-08-08/09.
- Rode along in 0.5.0: the training chain closed (first tutored adapter trained → served → 5/5
  verbatim from bare weights → **active** in the registry; standing rules in `training/RUNBOOK.md`),
  and the default voice advanced to `huihui_ai/gemma-4-abliterated:12b` (12/12 bake-off + operator
  voice trial; publisher-matched HF ancestry for the consolidation path).

### XII-B — The Considered Self (planned)

- Scheduled reflection cycles as reviewed maintenance; "outgrown" supersession patterns (the
  runtime proposes, the operator gates); identity-candidate assembly dry run (no training —
  months of reflection history must exist first).

### Alongside Epoch XII (unscheduled)

- Voice-base consolidation experiment: QLoRA on the default voice's matched HF weights
  (`Huihui-gemma-4-12B-it-abliterated`) — test the train-on-4bit ↔ serve-on-4bit
  matched-precision hypothesis on the 8 GB card.
- Curriculum growth Tier 2 ("its house": Ollama, FastAPI, SQLite, the host) per the 4-tier
  strategy; K-12 pedagogy (mastery gates, spiral review, spaced retention) without K-12 content.
- IX-D Command Console (still gated on the deferred Android on-device approval validation).
- Surfacing consolidation approvals in the mobile Approvals tab.

Historical milestones remain recorded in [VERSION_HISTORY.md](VERSION_HISTORY.md) and `docs/architecture/roadmap.md`.

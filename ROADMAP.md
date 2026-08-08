# OMEGA-ARC Roadmap

**Current epoch:** Epoch X — Memory
**Current release:** 0.3.1
**Active release line:** 0.3.x

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

## Epoch X — Memory (active; X-A released as 0.3.0)

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

### Epoch X remaining (unscheduled)

- Memory consolidation and richer review/re-scoping surfaces (operator-visible memory, per the
  Covenant's human-readable records) — possibly surfacing the supersession queue in Bridge Zero.

## Future — Tutelage and Learning (proposed, unscheduled)

The epoch where OMEGA-ARC begins studying: a runtime-driven, review-gated study loop with two-tier
learning (reversible memory + gated LoRA consolidation) and a recall benchmark so growth is measured.
Sequenced after Epoch X — a learner must remember reliably first. See ADR
[`0013-learning-and-tutelage.md`](docs/decisions/0013-learning-and-tutelage.md) and
[`docs/architecture/epoch-tutelage-learning.md`](docs/architecture/epoch-tutelage-learning.md).

Historical milestones remain recorded in [VERSION_HISTORY.md](VERSION_HISTORY.md) and `docs/architecture/roadmap.md`.

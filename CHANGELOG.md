# Changelog

## [Unreleased]

### Changed

- The repository is now dual-licensed **MIT OR Apache-2.0** (previously a license placeholder). See
  `LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE`.

Next: Tutelage/Learning design (ADR 0013 — now unblocked by the memory substrate) and Epoch IX-D
(Command Console, designed). IX-D build remains gated on the deferred Android on-device approval
validation (see 0.2.1 below).

## [0.3.2] - 2026-08-08 — Epoch X-C (Review and Consolidation)

Released from `feature/epoch-x-memory`, tagged `epoch-x-c`. Completes Epoch X's committed scope.
Backend suite: **382 passing**, hermetic.

### Added

- **Memory review surface** (ADR 0022) — `GET /system/memory/rooms` (rooms + counts),
  `GET /system/memory` (filtered browse; embeddings never exposed), `GET /system/memory/{id}`
  (detail + audit trail), re-room (`POST .../scope`, null → global wing), and supersession
  **restore**. Corrections are explicit operator actions audited in a new `memory_events` table;
  deletion is deliberately not offered.
- **Consolidation** (ADR 0023) — `POST /system/memory/consolidation-scan` clusters near-duplicate
  active memories (same kind/room/user, `MEMORY_CONSOLIDATION_THRESHOLD` default 0.95), keeps the
  newest as representative, and proposes older rows into the supersession review queue
  (`origin='consolidation'`). No auto path; approved rows remain restorable; re-scans skip existing
  candidates.

### Fixed

- Continuity/cleanliness audit before this cut: stale epoch/version/status claims corrected across
  SYSTEM_OVERVIEW, VERSION_HISTORY, MILESTONES, ARCHITECTURE_DECISIONS (ADRs 0016–0023 now indexed),
  versioning.md prose, PROJECT_STATUS, ROADMAP, README, the Epoch X architecture note, component
  READMEs, and the benchmarks README (fuzzy term + supersession calibration documented). `.env.example`
  updated to the current default model and memory knobs. The stale tracked `ZIP for CA/` snapshot was
  untracked (recoverable from git history).

## [0.3.1] - 2026-08-08 — Epoch X-B (Rooms and Revision)

Released from `feature/epoch-x-memory`, tagged `epoch-x-b`. Patch-per-milestone within Epoch X.
Backend suite: **372 passing**, hermetic.

### Added

- **Scope assignment** (ADR 0020) — the conversation carries the memory room, set only by explicit
  action (`POST /conversations {scope}` or `POST /conversations/{id}/scope`; never inferred).
  Memories persisted from a scoped conversation inherit its room; recall in it searches the room
  **plus the global wing** (unscoped memories stay recallable everywhere, other rooms excluded).
  Measured on `recall_scoped_v2`: hit@1 1.000, room isolation and global recall both hold. This is
  the curriculum hook: *a lesson is a scoped conversation.*
- **Robust supersession** (ADR 0021, upgrading ADR 0018; still off by default) — two dispositions:
  AUTO only when the new text *declares* the change ("is now", "moved to", "no longer", …) with
  same kind/room and a calibrated similarity floor; undeclared collisions become **pending
  candidates** reviewed via `GET /system/memory/supersession-candidates` + resolve endpoint — the
  first operator review surface over memory. Nothing is hidden until approved; everything is
  reversible and audited. Calibration (real embedder) overturned the single-floor design (5/9) in
  favor of two-tier floors (recommended 0.80/0.45 → 8/9), with the residual ambiguity measured and
  documented.
- **Embedder bake-off** (recorded in `backend/benchmarks/README.md`) — `embeddinggemma` retained:
  challengers (`nomic-embed-text`, `mxbai-embed-large`) lost recall (0.867–0.895 hit@1 vs 1.000)
  and did not dominate supersession. Pre-registered decision rule; re-run if the corpus or embedder
  landscape changes.

## [0.3.0] - 2026-08-07 — Epoch X-A (Memory Foundation)

Epoch X — Memory — begins. Released from `feature/epoch-x-memory`, tagged `epoch-x-a`. New epoch, new
minor per the milestone-versioning rule. Backend suite: **366 passing**, hermetic. Techniques adapted
from [MemPalace](https://github.com/MemPalace/mempalace) (MIT) are credited in the ADRs; no MemPalace
code, no second store — everything stays behind the single deterministic memory boundary.

### Added

- **Recall benchmark** (`backend/benchmarks/`) — LongMemEval-style measurement (hit@1 / recall@k /
  MRR) with real-embedder and deterministic-stub modes, so every retrieval change is judged against a
  number. Fixtures `recall_v1/v2/v3` + `recall_scoped_v1`.
- **Temporal-aware retrieval** (ADR 0016, **on** by default) — a bounded recency term breaks
  similarity near-ties toward the newer fact, so a superseded fact no longer outranks its
  replacement. Measured: hit@1 0.933 → 1.000 on `recall_v2`, no recall@3 regression.
- **Hybrid lexical + fuzzy retrieval** (ADR 0017, **off** by default) — exact term-overlap and
  typo-tolerant trigram signals, blended and bounded like recency. Landed disabled after honest
  measurement showed the embedder already handles exact-term recall (a negative result, recorded).
- **Write-time supersession** (ADR 0018, **off** by default) — a new memory can flag the fact it
  replaces (same kind/scope, cosine ≥ threshold); superseded rows are kept and reversible, and
  active recall excludes them. Enabling awaits threshold calibration ("replaces vs complements").
- **Scoped retrieval** (ADR 0019) — memories carry an optional `scope` ("room"); recall can search
  within a room. The MemPalace idea that most directly serves the future learner: recall *by
  subject*. Measured: hit@1 0.500 → 1.000 vs flat recall on parallel cross-room facts.

### Changed

- `search_memories` ranking is now `cosine + recency` (lexical/fuzzy available, off); active recall
  filters superseded rows; `memories` schema gains `scope` + supersession columns (migrated in place).
- Default chat model is now `richardyoung/llama-3.1-8b-instruct-abliterated` (abliterated/uncensored,
  ~8B) — replaces `dolphin-mixtral:8x7b` as the default across `active_chat_model`/`chat_model`,
  Direct Model mode, and the operator selector allowlist (dolphin-mixtral remains selectable). Keeps
  the uncensored posture while running far faster than the 26 GB mixtral on a CPU host. Model Lock is
  unchanged; the active model still changes only by explicit operator action.
- Added `mo-shakib/gemma4-e4b-uncensored:q4_k_m` to the operator model-selector allowlist.

## [0.2.1] - 2026-08-07 — Epoch IX-C (Operator Actions)

Released from `feature/epoch-ix-c-model-selector`, built on the tagged `epoch-ix-a` IX-B baseline;
tagged `epoch-ix-c`. Backend suite: **345 passing**, hermetic.

> **Release exception — Android on-device validation deferred.** This milestone shipped by the
> release owner's decision with the Android approve/deny biometric round-trip **not yet run on
> hardware**. iOS approve→Face ID was validated on a physical iPhone (2026-08-07). The Android
> device pass is owed as a follow-up; until it is recorded, treat Android operator-approvals as
> unverified on-device.

### Added

- Operator **model selector** — allowlisted and Model-Lock-recorded, across backend, desktop, iOS,
  and Android; the active model changes only on explicit operator action.
- In-app **New Conversation** control on both mobile consoles.
- **Operator approvals** surfaced to the mobile operator via `/api/mobile/v1/approvals`; approve/deny
  gated by on-device biometric (iOS Face ID, Android BiometricPrompt) and recorded through the
  existing approval engine. See [`docs/decisions/0014-operator-approvals.md`](docs/decisions/0014-operator-approvals.md).
- **OMEGA-ARC app icon** — a red Ω/arc ring with the machine identity `0M3-G4` in genuine Aurebesh
  under a fisheye lens — on iOS (`AppIcon`), Android (adaptive icon, all densities), and the desktop
  Bridge Zero browser tab and installable PWA. Reproducible from the bundled font via
  [`bridge/shared/icon/tools/generate_icons.py`](bridge/shared/icon/tools/generate_icons.py).
- Bundled **OFL Aurebesh font** (SilvinoR, OFL-1.1) at `bridge/shared/fonts/`; the desktop Aurebesh
  Utility now renders real glyphs instead of an ASCII stub.
- Branded **Windows launcher** shortcut wrapping the existing `START-OMEGA-ARC.cmd`.

### Changed

- iOS conversation view: the keyboard is now dismissable and the title is "Console".
- Mobile disconnect retains the non-secret server address and clears only the bearer token.

### Validated

- Backend suite **345 passing**, hermetic (~118 s).
- Desktop Bridge Zero production build succeeds; Vite bundles the Aurebesh font and favicon assets.
- Android `processDebugResources` resolves the adaptive icon.
- iOS approve→Face ID validated on a physical iPhone (2026-08-07).

### Deferred / follow-up

- **Android on-device approval/biometric validation** (approve + deny round-trip) — the documented
  release exception above.
- Push notification delivery (APNs/FCM) — designed, infra-blocked (paid Apple account + Firebase).

## [0.2.0] - In Development (IX-B checkpoint tagged `epoch-ix-a`)

**Current status:**

- Epoch IX-B (Runtime Operations) complete and validated on hardware (Android 8/8, iOS 8/8)
- Reviewed checkpoint committed on `release/epoch-ix-0.2.0` and tagged `epoch-ix-a`
- Mobile clients and the shared contract are tracked
- Version 0.2.0 remains in development on the 0.2.x line; IX-C (Operator Actions) continues from the
  `epoch-ix-a` baseline (see [Unreleased] above)

### Implemented

- Epoch IX-A authenticated mobile API adapter and native SwiftUI / Jetpack Compose operator consoles
- Model Lock and the deterministic runtime boundary, including Direct Model mode (no automatic
  substitution or fallback)
- Epoch IX-B authoritative RuntimeStore, typed SSE runtime events, in-process runtime event bus,
  measured telemetry, and the Operations Dashboard foundation
- Native iOS and Android RuntimeStores consume the typed `/api/mobile/v1/events` stream; periodic
  operational polling has been removed (manual refresh and a 3-second reconnect backoff remain)
- Desktop/frontend `/chat/stream` is instrumented into RuntimeStore stream telemetry
- Shared OpenAPI contract, runtime compatibility gate, and secure native credential storage
- Cross-platform design-token foundation (colors, spacing, radii, typography, status) with a shared
  Android status-badge component and aligned iOS surface/separator colors
- Android Gradle wrapper present in the tree (Gradle 9.5.0, SHA-256 pinned)

### Validated

- Backend test suite: **344 passing** at the checkpoint; hermetic (tests redirect mutable stores to a
  temporary `OMEGA_TOOL_DATA_DIR` and leave tracked runtime data unchanged). The IX-C branch is now
  at **345** (see [Unreleased])
- Desktop Bridge Zero and frontend Vite production builds succeed at 0.2.0
- Shared OpenAPI and design-token files parse
- Android: clean `assembleDebug` and `testDebugUnitTest` pass (Gradle 9.5.0 / JDK 21 / SDK 37);
  8/8 physical-device checklist on moto g15 power / Android 15
- iOS: `xcodegen generate`, simulator build, unit + UI tests, and `.ipa` packaging pass on CI
  (macos-14 / Xcode 16 / iOS 17 SDK / Swift 5.10) — the `APIClient.swift` fix is compiler-confirmed

### Pending Validation

- Android instrumentation tests, TalkBack pass, and a release-configuration build
- A durable fixture-or-ignore policy for the `backend/data/` runtime records
- Desktop typed-event consumption parity (desktop Bridge Zero still refreshes via `/system/*` REST
  polling rather than consuming the typed SSE stream)
- Design-token parity confirmed on device (or via a generated comparison test)
- LAN connectivity validation with a secure `MOBILE_AUTH_TOKEN`

### Resolved release blockers

- Physical-iPhone validation recorded (8/8; see [`PROJECT_STATUS.md`](PROJECT_STATUS.md)). The Android
  hardware pass was already recorded.
- `epoch-ix-a` annotated tag created on `release/epoch-ix-0.2.0`.
- `backend/data/` runtime records were reset to clean fixtures at checkpoint time.

The running backend re-writes `backend/data/{goals,plans,tool_requests}.json` during normal operation,
so they appear modified in a live working tree; a durable fixture-or-ignore policy remains a tracked
debt item (`docs/governance/TECHNICAL_DEBT.md`).

Resolved since the initial candidate: the reviewed checkpoint now exists as six commits on
`release/epoch-ix-0.2.0`; the mobile and shared sources are tracked; Android and iOS both build
and pass their tests (Android on hardware, iOS on CI); clean-clone build reproducibility is
demonstrated by the CI run.

## [0.1.0]

### Added

- Initial repository structure
- Covenant
- Constitution
- Charter
- Architecture document
- Roadmap
- Repository agent instructions
- Setup and backup scripts

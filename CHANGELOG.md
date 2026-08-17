# Changelog

## [Unreleased]

### Added

- **Epoch IX-D — Command Console, slice 1** (ADR 0015 → **Accepted**;
  `docs/architecture/epoch-ix-d-command-console.md` → *As built*). The operator consoles go from
  *observe + approve* to **initiate**: a command registry
  (`backend/services/command_registry.py`, the authority — consoles render it, never define it) with
  exactly three commands, one per gate: `new_conversation` (low, **direct**),
  `run_backend_health_check` (medium, **approval** → an IX-C `backend_health_check` tool request that
  executes only after a biometric-confirmed operator approval), `change_conversational_routing`
  (**forbidden** — refused with 403 and the refusal recorded; Model Lock / output fidelity).
  Console service `backend/services/command_console.py`; routes `GET/POST /mobile/commands…`,
  `GET /mobile/commands/history`, and desktop `GET/POST /system/commands…` (desktop may initiate;
  gated commands still complete only on a mobile biometric — the ADR's "desktop cannot self-approve",
  enforced in the executor). Every command — including forbidden, denied, expired, and failed — is
  written to `backend/data/command_log.json` with requester, channel, linked request/approval ids,
  status, and outcome. Android Bridge Zero gains a **Commands** tab (registry cards RUN / REQUEST /
  greyed FORBIDDEN + history). `backend/tests/test_command_console.py`: 9 tests.
  **Device-validated 2026-08-17** on the Moto G15 Power: REQUEST → Approve → fingerprint → history
  **EXECUTED**; backend shows the request `completed`, the approval `approved` with
  `confirmation: biometric`, and a real health-check result — the runtime's first operator-initiated,
  biometric-gated actions.
- **IX-D slice 2 — iOS Commands tab** (`bridge/bridge-zero-ios/Sources/CommandsView.swift`, models,
  API, state; `Tests/CommandModelsTests.swift`), same day. CI-built (`ios-build.yml`, run
  32081331882, all tests green), sideloaded with Sideloadly, and **device-validated on Bill's
  iPhone**: REQUEST → Approve → Face ID → EXECUTED; backend approval `confirmation: biometric`,
  single-use approval consumed, real `backend_health_check` result. Backend reached over the iPhone
  USB-tether link (`172.20.10.6:8001`). **IX-D validated on both mobile platforms.** Not in this
  slice: a desktop Bridge Zero Commands panel.
- **The school day** (`docs/architecture/school-day.md`; XII-B groundwork): an operator-set
  daily learning window, 09:00–14:00 local, fired by the Windows task `OMEGA-ARC School Day`
  (`scripts/Register-SchoolDayTask.ps1` → `scripts/school_day.ps1` → `scripts/school_day.py`).
  Preflights the stack, studies the next unpassed lesson per subject in prerequisite order,
  runs spaced re-quizzes (1/3/7/14/30-day ladder by pass streak), closes the day with one
  reflection cycle, and writes a report + operator to-do list to `.runtime-logs/school/`. Gated
  actions (consolidation, adapter activation, approvals, training) are surfaced, never taken —
  pinned by `backend/tests/test_school_day.py`.
- **`scripts/curriculum_add.py`**: subjects as `curriculum/<subject>/subject.json` + lesson
  markdown; validates every recall key against the paragraph-chunked sources before writing.
- **Private curriculum overlay:** subjects under `curriculum-private/` /
  `backend/data/curriculum.private.json` (gitignored) merge at load time; their study cycles go
  to `study_cycles.private.json` (gitignored) and merge on read; the reflection digest sees them
  only as opaque labels; consolidation refuses them. The first Tier 2/3 "operator's world"
  subjects (its tools, the operator's side business) are private and live only on the host.
- **Android on-device approval validation RECORDED (2026-08-17)** — clears the 0.2.1 release exception.
  Bridge Zero Android 0.5.0 debug build on a Moto G15 Power (fingerprint sensor) against the 0.5.0
  backend over `adb reverse`: seeded `backend_health_check` request → Approvals tab → **Approve →
  BiometricPrompt fired → fingerprint → backend `approved`**; second request → **Deny → backend
  `rejected`**; queue cleared both times; a third request aged out at the 300 s TTL as designed.
  Android operator-approvals are now verified on-device (iOS was 2026-08-07). IX-D is unblocked.
- Trainer: `--init-adapter` warm-start and `--lr` for polish legs (`training/train_adapter.py`);
  the 12bq voice-family adapter reached v2f (identity string verbatim, 4/5 probe).

### Changed

- **Recorded policy shift (ADR 0015):** gated command execution is **on by default** via a new
  `COMMAND_EXECUTION` setting — every execution on the console path has just passed a device
  biometric. `ENABLE_TOOL_EXECUTION` (default off) is unchanged and still governs the model-initiated
  chat tool path; the two switches are deliberately separate.
- `approve_request(..., confirmation=)` records *how* an approval was confirmed; only the mobile
  approve route (which already requires the client's biometric `confirmed` flag) passes
  `"biometric"`, and only that value releases a command. Approvals via `/system` are stored but leave
  the command `awaiting_approval` with a note.
- Mobile approve/deny responses now include the affected `command` entry (or `null`).
- Android Bridge Zero bottom bar: six tabs at 10 sp single-line labels; "Diagnostics" → "Diag"
  (labels wrapped at six tabs on-device).
- iOS: `MobileVersionTests.testNewerRequiredVersionIsBlocked` no longer pins 0.3.0 (it silently
  broke `ios-build.yml` when the app went to 0.5.0, which also blocked `.ipa` packaging); it now
  uses 99.0.0 and a self-consistency test was added.

Next: IX-D slice 3 (desktop Bridge Zero Commands panel over the existing `/system/commands`
endpoints; broaden the registry one risk-classed command at a time), XII-B (The
Considered Self — scheduled reflection, supersession patterns), the voice-consolidation experiment
(QLoRA on the default voice's matched HF weights — the train-on-4bit ↔ serve-on-4bit hypothesis), and
Tier-2 curriculum growth ("its house").

## [0.5.0] - 2026-08-09 — Epoch XII-A (The Mirror) — Epoch XII begins

Epoch XII — Reflection — begins: the runtime considers itself. Released from
`feature/epoch-xii-reflection`, tagged `epoch-xii-a`. New epoch → minor bump. Backend suite:
**397 passing**.

### Added

- **The reflection room** (ADR 0025; `docs/architecture/epoch-xii-reflection.md`): a reserved
  memory scope, `self-reflection`, written **only** by the reflection pipeline. The operator
  reviews and may supersede; the operator never authors here — inverse of the tutelage discipline,
  same governance spine.
- **Digest-then-compose cycles** (`POST /system/reflection/cycles`, `GET` to list): a
  deterministic digest of the runtime's actual recorded activity (study cycles and scores,
  memory events, supersession candidates, operator-gated consolidation runs read from the adapter
  registry, prior reflections) is built first; the voice model then composes a short first-person
  observation grounded **only** in that digest. The digest is stored beside every observation as
  provenance — *no ungrounded self-narrative*. Cycle records persist in
  `backend/data/reflection_cycles.json`.
- The first real self-observations were recorded 2026-08-08/09 and live in the room as history.

### Changed

- **Default voice → `huihui_ai/gemma-4-abliterated:12b`** (operator decision after a hands-on
  voice trial and a first-ever perfect 12/12 on the tutelage comprehension quizzes). Uncensored,
  Apache 2.0, 11.9B Q4_K_M — and a *smaller* first-run download than the previous default (7.6 vs
  9.6 GB; installer copy now says ~8 GB). 131K context; vision/tools/audio capable. Decisive
  differentiator: publisher-matched HF safetensors ancestry
  (`huihui-ai/Huihui-gemma-4-12B-it-abliterated`), which keeps the voice-consolidation path
  traceable. The previous default and both e4b variants remain selectable (Model-Lock-recorded).

### Measured (live)

- **The training chain closed** (follow-through on XI-C, recorded in `training/RUNBOOK.md`): the
  first distillation artifact (16 key-verified pairs) was trained as a LoRA adapter (bf16, 320
  steps, final loss 0.060), converted to GGUF, served over the base model, and answered **5/5
  quiz questions verbatim from bare weights** — memory retrieval off. The adapter is **active** in
  the registry: the runtime's first operator-gated weight change, end to end. Two standing rules
  were paid for and recorded: train in bf16 (fp16 GradScaler crashes this host's GPU), and serve
  adapters over fp16 bases (a bf16-trained adapter confabulates over q4 quantization).

## [0.4.2] - 2026-08-08 — Epoch XI-C (Consolidation Gate) — Epoch XI complete

Released from `main`, tagged `epoch-xi-c`. Completes Epoch XI (Tutelage). Backend suite: **394
passing**.

### Added

- **The consolidation gate** (ADR 0024): `tutelage_consolidation` registered as a bounded MUTATION
  tool (risk high, approval required, no direct adapter — its single-use approval is the ticket
  consumed by `POST /system/tutelage/consolidations`). Only key-verified answers from PASSED
  lessons distill into chat-format training pairs (`training/distillation/`); unverified answers
  are counted and excluded.
- **Versioned adapter registry** (`backend/data/adapters.json` + `/system/tutelage/adapters`):
  candidate → trained → active → retired via explicit recorded actions; activation retires any
  other active adapter for the subject (Model-Lock pattern). Weight training itself stays
  operator-executed via `training/` (GGUF-vs-HF boundary documented).

### Measured (live)

- Real gated run: tool request → operator approval → 16 key-verified pairs from 3 passed lessons
  (1 unverified excluded) → candidate adapter registered → approval consumed (single-use held).
  The first distillation artifact is committed as epoch history.

## [0.4.1] - 2026-08-08 — Epoch XI-B (Retention and Compounding)

Released from `feature/epoch-xi-tutelage`, tagged `epoch-xi-b`. Backend suite: **392 passing**.

### Added

- **Cumulative quizzes**: lessons may name `review_lessons` whose questions join the quiz
  (namespaced, per-origin sections); the pass rule requires every section of every test to clear
  the threshold — new learning that degrades old recall fails the lesson (interference gating).
- **Retention report**: `GET /system/tutelage/retention` — per-lesson score history across all
  cycles (first/latest/delta + full series). Spaced re-quizzes ride idempotent ingestion.
- Seed lesson 3, "The Operator Surfaces" (reviews lessons 1–2; 17 questions total).

### Measured (live, real embedder + study seat)

- Spaced re-quiz of lesson 1 hours after study: recall 1.0 / comprehension 1.0, zero re-ingestion.
- Lesson 3 cumulative: recall 1.0/1.0; comprehension own 1.0 / review 0.917 — the single review
  miss is genuine cross-lesson retrieval interference (a lesson-1 question answered from lesson-2
  notes): exactly the phenomenon cumulative testing exists to surface, now measurable.
- Retention: all lessons at 1.0, delta 0.0.

## [0.4.0] - 2026-08-08 — Epoch XI-A (The First Lesson)

Epoch XI — Tutelage — begins: the runtime studies. Released from `feature/epoch-xi-tutelage`,
tagged `epoch-xi-a`. New epoch → minor bump. Backend suite: **389 passing**, hermetic.

### Changed (shipped in this release; recorded late)

- Default chat model became `mo-shakib/gemma4-e4b-uncensored:q4_k_m` (operator decision after
  side-by-side trials; ~10 GB). Because that default is thinking-capable, the backend began
  sending `think: OLLAMA_THINK` (default **false**) on all Ollama chat calls — probed: clean fast
  answers with it off, 1.6k chars of hidden dead-air reasoning with it on, and `think:false` is
  accepted harmlessly by non-thinking models. Vision default advanced `llava:7b` -> `qwen3-vl`
  (dormant role; llava was two generations stale).
- The repository became dual-licensed **MIT OR Apache-2.0** (previously a license placeholder).
  See `LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE`.

### Added

- **Curriculum + study cycle** (ADR 0013; `docs/architecture/epoch-xi-tutelage.md`): operator-
  authored curriculum (`backend/data/curriculum.json`) whose subjects are memory rooms; lessons
  carry local sources, prerequisites, and quizzes. `POST /system/tutelage/cycles` runs a cycle:
  idempotent provenance-tagged ingestion into the room → pre/post **recall test** (deterministic,
  no LLM) → **comprehension test** (the study-seat model answers from its own retrieved notes;
  grading is deterministic against operator-authored keys with OR-group synonyms — the model never
  grades itself). Lessons pass only when both scores clear the threshold; passing unlocks
  dependents; every cycle is an auditable record (the first real records are committed).
- **Study seat**: `OLLAMA_STUDY_MODEL` (empty → active chat model) with per-cycle override. Live
  bake-off (gemma4 vs lfm2.5 vs granite3.3) retained the default — the challengers did not strictly
  beat it; the first run's think-leak false positives were caught and fixed (`_strip_think`).
- **Seed curriculum**: OMEGA-ARC's own architecture — first lessons ran 2026-08-08, recall
  0.0 → 1.0 on both, true comprehension 12/12. *Anatomy is taught; identity is authored.*

### Fixed

- Command Deck panels now read their authoritative stores (evidence = resolved beliefs, same source
  as reasoning; deliberation polled), stale hardcoded literals removed, and the reasoning snapshot
  persists across backend restarts (`reasoning_snapshot.json`) — runtime visibility no longer has
  amnesia. Tracked UI dists refreshed.
- CPU-only host mischaracterization corrected across docs: Ollama auto-offloads to GPU up to VRAM
  (RTX 5060 8 GB here — sub-7 GB models run fully accelerated).

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
> unverified on-device. *(Cleared 2026-08-17 — see [Unreleased].)*

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

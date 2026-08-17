# OMEGA-ARC Project Status

> Living status document. Update this file whenever the active phase, release, validation state, or checkpoint changes.

| Field | Current value |
|---|---|
| Last updated | 2026-08-09 |
| Current epoch | Epoch XII — Reflection |
| Current version | 0.5.0 |
| Release line | 0.5.x |
| Status | Active Development |
| Current phase | Epoch XII begun — XII-A (The Mirror) released as **0.5.0** (tag `epoch-xii-a`) |
| IX-B validation | Complete — Android 8/8 and iOS 8/8 on hardware; tagged `epoch-ix-a`. See `docs/governance/EPOCH_IX_RETROSPECTIVE.md` |
| IX-C validation | iOS approve→Face ID validated on hardware (2026-08-07). **Android approve/deny biometric validated on hardware (2026-08-17, Moto G15 Power, BiometricPrompt)** — the 0.2.1 release exception is cleared |
| Theme | Epoch XII: “The Runtime Considers Itself” (XI: “Learns”, X: “Remembers”, IX: “Becomes Visible”) |

## Completed

- ✓ Epoch VIII — bounded tools and verified execution foundation
- ✓ Epoch IX-A — authenticated mobile operator-console foundation
- ✓ Epoch IX-B runtime infrastructure:
  - authoritative RuntimeStore
  - measured operations telemetry
  - typed SSE runtime events and event bus
  - Operations Dashboard foundation
  - shared mobile design tokens and native components

## Hardened since RC1 (2026-07-23/24)

- ✓ Reviewed checkpoint committed on `release/epoch-ix-0.2.0` (mobile + shared sources now tracked)
- ✓ Backend suite 344 passing, hermetic
- ✓ Android build reproducible (committed Gradle wrapper 9.5.0); clean `assembleDebug` + unit tests
- ✓ Android physical-device validation: 8/8 on moto g15 power / Android 15
- ✓ iOS builds green on CI (Xcode 16 / iOS 17); live SSE + streaming validated on a physical iPhone
- ✓ Design-token foundation aligned across platforms
- ✓ Defects found on-device and fixed: iOS SSE blank-line parsing, evidence/deliberation
  diagnostics, and the `launch_backend.py` `.env` bind-order bug

## Checkpoint closed — 2026-07-24

All gates resolved. Both native platforms passed their physical-device checklists (Android 8/8,
iOS 8/8); generated runtime stores reset to clean fixtures; the reviewed checkpoint is committed on
`release/epoch-ix-0.2.0` and tagged **`epoch-ix-a`**. See `docs/governance/EPOCH_IX_RETROSPECTIVE.md`
for the full before/after.

IX-C (Operator Actions) continues on `feature/epoch-ix-c-model-selector` from this baseline.

## Epoch IX-C — released as 0.2.1 (2026-08-07)

Operator Actions shipped from `feature/epoch-ix-c-model-selector`, tagged **`epoch-ix-c`** and merged
to `main`. Backend suite **345 passing**, hermetic. Built on the `epoch-ix-a` baseline (no IX-C
behavior is present in that checkpoint).

- ✓ Operator **model selector** — allowlisted, Model-Lock-recorded; backend, desktop, iOS, Android
- ✓ In-app **New Conversation** control on both mobile consoles
- ✓ **Operator approvals** with on-device biometric — iOS approve→Face ID validated on a physical
  iPhone (2026-08-07); push delivery (APNs/FCM) infra-blocked
- ✓ **App icon** (fisheye Aurebesh `0M3-G4`) on iOS, Android, and the desktop tab / PWA; desktop
  **Aurebesh Utility** renders real OFL glyphs; branded Windows launcher shortcut
- ✓ iOS console: keyboard-dismiss fix and "Console" rename

> **Release exception (owed):** the **Android** approve/deny biometric round-trip was **not** run on
> hardware before this release, by the release owner's decision to keep momentum toward Epoch X. Run
> it and record the result here; until then, Android operator-approvals are unverified on-device. The
> Android debug APK is built at `bridge/bridge-zero-android/app/build/outputs/apk/debug/app-debug.apk`.

## Epoch X-A — Memory Foundation, released as 0.3.0 (2026-08-07)

Epoch X (Memory) began and its foundation shipped from `feature/epoch-x-memory`, tagged **`epoch-x-a`**
and merged to `main`. Backend suite **366 passing**, hermetic. Five measured slices (ADRs 0016–0019;
MemPalace-derived techniques credited): recall benchmark, temporal-aware retrieval (on; hit@1
0.933 → 1.000), hybrid lexical/typo-fuzzy knobs (off by default — honest neutral measurement),
write-time supersession (off pending threshold calibration; reversible), and scoped retrieval
("rooms"; hit@1 0.500 → 1.000 vs flat recall). Remaining Epoch X work: scope assignment, robust
supersession, consolidation/review surfaces — see [`ROADMAP.md`](ROADMAP.md).

Carried-forward obligations (unchanged by this release): the **Android on-device approval/biometric
pass** (0.2.1 release exception; also gates IX-D) and on-device icon confirmation on both platforms.

## Epoch X-B — Rooms and Revision, released as 0.3.1 (2026-08-08)

Two measured slices from `feature/epoch-x-memory`, tagged **`epoch-x-b`**, merged to `main`. Backend
suite **372 passing**, hermetic.

- ✓ **Scope assignment** (ADR 0020) — conversations carry the memory room (explicit action only);
  memories inherit it; recall = room + global wing. `recall_scoped_v2` hit@1 1.000.
- ✓ **Robust supersession** (ADR 0021; off by default) — declared changes auto-supersede (reversible),
  undeclared collisions queue for operator review (`/system/memory/supersession-candidates`) — the
  first memory review surface. Calibrated two-tier floors 0.80/0.45 (8/9; residual ambiguity measured).
- ✓ **Embedder bake-off** — `embeddinggemma` retained on a pre-registered rule; challengers lost
  recall. Recorded in `backend/benchmarks/README.md`.

Carried-forward obligations (unchanged): Android on-device approval pass (gates IX-D) and on-device
icon checks.

## Epoch X-C — Review and Consolidation, released as 0.3.2 (2026-08-08)

Two slices from `feature/epoch-x-memory`, tagged **`epoch-x-c`**, merged to `main`. Backend suite
**382 passing**, hermetic.

- ✓ **Memory review surface** (ADR 0022) — browse rooms/memories (embeddings never exposed), detail
  with audit trail, re-room, and supersession restore; corrections audited in `memory_events`;
  deletion deliberately not offered.
- ✓ **Consolidation** (ADR 0023) — operator-invoked scan proposes near-duplicate residue into the
  supersession review queue (`origin='consolidation'`); no auto path; approved rows stay restorable.

Epoch X's committed scope (durable, scoped, benchmarked memory) is delivered. Next: Tutelage design
(ADR 0013), a Bridge Zero memory panel, and floor calibration against a grown corpus remain open.

## Epoch XI-A — The First Lesson, released as 0.4.0 (2026-08-08)

Tutelage is live from `feature/epoch-xi-tutelage`, tagged **`epoch-xi-a`**, merged to `main`.
Backend suite **389 passing**, hermetic.

- ✓ Curriculum store + full study cycle (idempotent ingestion → pre/post recall test →
  comprehension test with deterministic operator-key grading; prerequisite gating; audit records)
- ✓ First real lessons: seed subject = OMEGA-ARC's own architecture; recall 0.0 → 1.0 both lessons;
  true comprehension 12/12 on the honest instrument
- ✓ Study-seat bake-off: default model retained (no challenger strictly better); think-leak false
  positives caught and fixed by the instrument itself
- ✓ Deck truthfulness: panels read authoritative stores; reasoning snapshot persists across restarts
- Boundary: *anatomy is taught; identity is authored* (self-authored personality preserved)

## Epoch XI-B — Retention and Compounding, released as 0.4.1 (2026-08-08)

Tagged **`epoch-xi-b`**, merged to `main`. Backend suite **392 passing**. Cumulative quizzes with
per-section interference gating; spaced re-quizzes; retention report endpoint. Live: retention held
at 1.0 hours after study; the cumulative run caught one genuine cross-lesson interference miss
(review comprehension 0.917, above threshold).

## Epoch XI-C — Consolidation Gate, released as 0.4.2 (2026-08-08) — Epoch XI complete

Tagged **`epoch-xi-c`**. Backend suite **394 passing**. The ADR 0013 loop is whole: study → measure
→ review → gated consolidation. Live: operator-approved consolidation distilled 16 key-verified
pairs (1 unverified excluded) into the first candidate adapter; approval consumed single-use.
Training remains operator-executed (ADR 0024).

## Epoch XII-A — The Mirror, released as 0.5.0 (2026-08-09) — Epoch XII begins

Tagged **`epoch-xii-a`**. Backend suite **397 passing**. The runtime considers itself: a reserved
`self-reflection` room written only by the reflection pipeline (operator reviews, never authors);
digest-then-compose cycles — a deterministic digest of recorded activity first, then a first-person
observation grounded only in it, stored with the digest as provenance (ADR 0025). The first real
self-observations are live in the room.

Also in 0.5.0: the **training chain closed** — the first tutored adapter (from XI-C's distillation
artifact) trained, converted, served, answered its quiz **5/5 verbatim from bare weights**, and was
activated in the registry (`training/RUNBOOK.md` holds the standing rules it paid for). And the
**default voice advanced** to `huihui_ai/gemma-4-abliterated:12b` after a measured 12/12 bake-off
plus a hands-on operator voice trial — publisher-matched HF ancestry keeps the future
voice-consolidation path traceable.

Carried-forward obligations (unchanged): Android on-device approval pass (gates IX-D) and on-device
icon checks.

## Native Device Validation Gate (IX-B — closed)

This gate closed on 2026-07-24 (both platforms 8/8; see Checkpoint closed above). The records below
are retained for audit. Record the device, operating-system version, build identifier, tester, and
date with each run.

### iOS

Run record — physical iPhone, tester: Bill H, date: **2026-07-24**. Debug build sideloaded via a
free Apple ID (7-day provisioning). Sources build green on CI (macos-14 / Xcode 16 / iOS 17 SDK /
Swift 5.10).

- [x] Launch on a physical iPhone
- [x] Verify server connection and bearer authentication
- [x] Verify synchronized and streaming conversations
- [x] Verify RuntimeStore and Operations Dashboard updates
- [x] Verify background-to-foreground transitions
- [x] Confirm offline recovery and reconnect behavior
- [x] Check Dark Mode
- [x] Check Dynamic Type at accessibility sizes

iOS device checklist: **8/8 pass, no release-blocking defect.** Live SSE, streaming, dark mode,
Dynamic Type, and VoiceOver confirmed directly. Reconnect was confirmed repeatedly through backend
restarts (the app went offline and auto-relinked on the 3-second loop); background/foreground was
confirmed through extended real-device use with scene-phase suspend/resume. A blank-line SSE
parsing defect was found and fixed during this validation. Streaming used an operator-selected
`llama2-uncensored:7b`; model selection does not affect the transport under test.

### Android

Run record — device: **moto g15 power**, OS: **Android 15**, build: debug APK `versionName 0.2.0`
(`versionCode 1`), tester: Bill H, date: **2026-07-23**. Built from the uncommitted working tree
with Gradle 9.5.0 / JDK 21 (Temurin 21.0.11); clean `assembleDebug` recompiled 37/37 tasks.

- [x] Launch on a physical Android device
- [x] Verify server connection and bearer authentication
- [x] Verify synchronized and streaming conversations
- [x] Verify RuntimeStore and Operations Dashboard updates
- [x] Verify background-to-foreground transitions
- [x] Confirm offline recovery and reconnect behavior
- [x] Check dark theme
- [x] Check enlarged system font and display scaling

Android device checklist: **8/8 pass, no release-blocking defect.** Unit tests pass on this
toolchain (`testDebugUnitTest`: 8 tests, 0 failures, 0 errors). At maximum font and display
scaling the dashboard becomes visually crowded but nothing overlaps or truncates — recorded as a
cosmetic observation, not a defect.

Not yet run on this device: instrumentation tests, TalkBack pass, and a
release-configuration build. Streaming was exercised with `ACTIVE_CHAT_MODEL=llama2-uncensored:7b`
because the default `dolphin-mixtral:8x7b` runs ~77% on CPU on this host and could not produce
tokens in a usable time; the model selection does not affect the streaming transport under test.

### Exit criteria

- [x] Both platform checklists pass without a release-blocking defect
- [x] Any device-specific limitations are documented
- [x] Version 0.2.0 is committed from an intentionally scoped clean tree
- [x] The checkpoint commit is tagged `epoch-ix-a`

## Future

- Epoch XII-B — The Considered Self (scheduled reflection, supersession patterns,
  identity-candidate dry run; see `ROADMAP.md`)
- Voice-base consolidation experiment (QLoRA on the default voice's matched HF weights)
- Curriculum growth Tier 2 ("its house")
- Epoch IX-D — Command Console: **slice 1 built and device-validated 2026-08-17** (ADR 0015 Accepted;
  registry + console service + command log, mobile and `/system` routes, Android Commands tab; on the
  Moto G15 Power REQUEST → Approve → fingerprint → EXECUTED with a real tool result). Unreleased on
  `feature/epoch-ix-d-command-console`. **Slice 2 (iOS Commands tab) built via CI, sideloaded, and
  device-validated the same evening** — REQUEST → Face ID → EXECUTED with `confirmation: biometric`.
  Both mobile platforms validated. Slice 3 open: desktop panel, broader registry.

IX-C, Epoch X (A/B/C), Epoch XI (A/B/C), and XII-A are released; see the sections above. The 0.2.1
Android on-device approval exception that gated IX-D was cleared 2026-08-17.

## Authorities

- Release identity: [`docs/architecture/versioning.md`](docs/architecture/versioning.md)
- Delivery sequence: [`ROADMAP.md`](ROADMAP.md)
- Released changes: [`CHANGELOG.md`](CHANGELOG.md)
- IX-B validation: [`docs/governance/IX_B_VALIDATION_REPORT.md`](docs/governance/IX_B_VALIDATION_REPORT.md)
- Repository checkpoint: [`docs/governance/REPOSITORY_CHECKPOINT_REPORT.md`](docs/governance/REPOSITORY_CHECKPOINT_REPORT.md)
- Technical debt: [`docs/governance/TECHNICAL_DEBT.md`](docs/governance/TECHNICAL_DEBT.md)
- IX-C readiness: [`docs/governance/IX_C_READINESS.md`](docs/governance/IX_C_READINESS.md)
- Engineering practices: [`docs/governance/CONTRIBUTING.md`](docs/governance/CONTRIBUTING.md)
- Architectural rationale: [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md)

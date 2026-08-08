# OMEGA-ARC Project Status

> Living status document. Update this file whenever the active phase, release, validation state, or checkpoint changes.

| Field | Current value |
|---|---|
| Last updated | 2026-08-07 |
| Current epoch | Epoch X — Memory |
| Current version | 0.3.0 |
| Release line | 0.3.x |
| Status | Active Development |
| Current phase | Epoch X-A (Memory Foundation) released as **0.3.0** (tag `epoch-x-a`), merged to `main` |
| IX-B validation | Complete — Android 8/8 and iOS 8/8 on hardware; tagged `epoch-ix-a`. See `docs/governance/EPOCH_IX_RETROSPECTIVE.md` |
| IX-C validation | iOS approve→Face ID validated on hardware (2026-08-07). **Android approve/deny biometric deferred** — release exception, owed as follow-up |
| Theme | Epoch X: “The Runtime Remembers” (Epoch IX was “The Runtime Becomes Visible”) |

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

## Native Device Validation Gate

IX-B remains active until both native clients pass this gate on physical hardware. Record the device, operating-system version, build identifier, tester, and date with each run.

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

- Epoch IX-C — Operator Actions (in progress; see the IX-C progress section above)
- Epoch IX-D — Command Console (designed in ADR 0015; build gated on IX-C on-device approval validation)
- Epoch X — Memory (scope not yet committed)

The IX-B native-device gate and checkpoint exit criteria are satisfied, so IX-C feature work is under way. IX-D build remains gated on IX-C operator approvals being validated on physical hardware.

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

# OMEGA-ARC Project Status

> Living status document. Update this file whenever the active phase, release, validation state, or checkpoint changes.

| Field | Current value |
|---|---|
| Last updated | 2026-08-07 |
| Current epoch | Epoch IX |
| Current version | 0.2.0 |
| Release line | 0.2.x |
| Status | Active Development |
| Current phase | IX-B complete — checkpoint tagged `epoch-ix-a`; IX-C in progress |
| IX-B validation | Complete — Android 8/8 and iOS 8/8 on hardware; tagged `epoch-ix-a`. See `docs/governance/EPOCH_IX_RETROSPECTIVE.md` |
| Theme | “The Runtime Becomes Visible” |

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

## Epoch IX-C progress — 2026-08-07

Operator Actions are building on `feature/epoch-ix-c-model-selector` (52 commits ahead of `main`),
backend suite **345 passing**, hermetic. No IX-C behavior is present in the `epoch-ix-a` checkpoint;
the branch is kept off that baseline.

- ✓ Operator **model selector** — allowlisted, Model-Lock-recorded; backend, desktop, iOS, Android
- ✓ In-app **New Conversation** control on both mobile consoles
- ✓ **Operator approvals** with on-device biometric — iOS approve→Face ID validated on a physical
  iPhone (2026-08-07); **Android device pass owed**; push delivery (APNs/FCM) infra-blocked
- ✓ **App icon** (fisheye Aurebesh `0M3-G4`) on iOS, Android, and the desktop tab / PWA; desktop
  **Aurebesh Utility** now renders real OFL glyphs; branded Windows launcher shortcut. **On-device
  icon confirmation owed** on the next iOS re-sideload and Android reinstall
- ✓ iOS console: keyboard-dismiss fix and "Console" rename

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

# OMEGA-ARC Project Status

> Living status document. Update this file whenever the active phase, release, validation state, or checkpoint changes.

| Field | Current value |
|---|---|
| Last updated | 2026-07-22 |
| Current epoch | Epoch IX |
| Current version | 0.2.0 |
| Release line | 0.2.x |
| Status | Active Development |
| Current phase | IX-B — Runtime Operations |
| IX-B validation | Blocked — see `docs/governance/IX_B_VALIDATION_REPORT.md` |
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

## In progress

- Operations Dashboard polish
- Telemetry refinement
- Native-device validation
- Clean Epoch IX 0.2.0 checkpoint commit and release tag
- Resolve the IX-B blockers recorded in the validation report
- Make Android builds reproducible with a committed Gradle wrapper
- Connect native operational state to typed SSE

## Native Device Validation Gate

IX-B remains active until both native clients pass this gate on physical hardware. Record the device, operating-system version, build identifier, tester, and date with each run.

### iOS

- [ ] Launch on a physical iPhone
- [ ] Verify server connection and bearer authentication
- [ ] Verify synchronized and streaming conversations
- [ ] Verify RuntimeStore and Operations Dashboard updates
- [ ] Verify background-to-foreground transitions
- [ ] Confirm offline recovery and reconnect behavior
- [ ] Check Dark Mode
- [ ] Check Dynamic Type at accessibility sizes

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

- [ ] Both platform checklists pass without a release-blocking defect
- [ ] Any device-specific limitations are documented
- [ ] Version 0.2.0 is committed from an intentionally scoped clean tree
- [ ] The checkpoint commit is tagged `epoch-ix-a`

## Future

- Epoch IX-C — Operator Actions
- Epoch IX-D — Command Console
- Epoch X — scope not yet committed

IX-C and IX-D are documented future work only. Major feature work should not begin until the native-device gate and checkpoint exit criteria are satisfied.

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

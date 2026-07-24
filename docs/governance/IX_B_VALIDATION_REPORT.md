# Epoch IX-B Validation Report

| Field | Value |
|---|---|
| Audit date | 2026-07-22 |
| Epoch | IX |
| Version | 0.2.0 |
| Phase | IX-B — Runtime Operations |
**Verdict:** Infrastructure implemented; validation blocked

This audit validates the existing implementation without expanding IX-C or redesigning the UI.

## Validation evidence

| Area | Result | Evidence |
|---|---|---|
| Backend syntax and tests | Pass | 340 tests passed |
| Desktop Bridge Zero build | Pass | Vite production build completed at 0.2.0 |
| Frontend build | Pass | Vite production build completed at 0.2.0 |
| Shared OpenAPI/design-token parse | Pass | YAML and JSON parsed successfully |
| Git whitespace integrity | Pass | `git diff --check` clean at audit time |
| iOS compile/test | Not run | macOS, Xcode, XcodeGen, generated project, signing, and device unavailable on audit host |
| Android compile/test | Blocked | Gradle wrapper and Android toolchain unavailable on audit host |
| Physical iOS validation | Not run | physical iPhone required |
| Physical Android validation | Not run | physical Android device required |

## Release-blocking findings

### B-01 — Native operational SSE is not connected

The backend exposes `/api/mobile/v1/events`, but neither native `RuntimeAPIClient` implements that endpoint. Both native stores poll status, telemetry, and diagnostics every 2.5 seconds. Their local event buses only republish values already obtained through polling or conversation streaming, and no consumer subscribes to those buses.

This violates the IX-B requirement that typed runtime events drive live operational state rather than polling replacing SSE.

### B-02 — RuntimeStore stream telemetry is not globally authoritative

`RuntimeStore.begin_stream` and `end_stream` are called only by the mobile conversation adapter. Desktop/frontend conversations use `/chat/stream` directly and bypass this instrumentation. Therefore `active_streams`, `streaming_state`, and `latency_ms` omit desktop activity while the dashboard presents them as runtime-wide values.

### B-03 — Physical devices cannot reach the standard backend launcher

`scripts/launch_backend.py` binds Uvicorn to `127.0.0.1`. The other launch helpers also use loopback. A phone on the LAN cannot reach that listener. Device validation needs an explicit LAN validation profile, the host’s LAN address, a configured `MOBILE_AUTH_TOKEN`, and a narrowly scoped firewall rule.

### B-04 — Android build is not reproducible from the checkout

The Android project has no `gradlew`, `gradlew.bat`, or `gradle/wrapper` files. No system Gradle or Android toolchain is available on the audit host. Commit a wrapper generated with the project’s supported Gradle version, then verify dependency resolution, unit tests, instrumentation tests, and `assembleDebug`.

### B-05 — Physical-device gate is incomplete

No iPhone or Android hardware run has been recorded. IX-B remains active until both platform checklists pass and device/build details are recorded in `PROJECT_STATUS.md` or an attached validation record.

## Device readiness checklist

### Shared backend and network

- [ ] Use an explicit LAN validation launch profile; do not change the secure default silently
- [ ] Bind the backend to the intended LAN interface
- [ ] Configure a strong non-empty `MOBILE_AUTH_TOKEN`
- [ ] Allow only the required backend port through the host firewall
- [ ] Confirm phone and host are on the same trusted network
- [ ] Use the host LAN IP or resolvable `.local` name, never `127.0.0.1`
- [ ] Verify `/api/mobile/v1/compatibility`, `/status`, `/telemetry`, and `/events` from the device network
- [ ] For release-mode testing, terminate trusted HTTPS and verify the certificate chain

### iOS

- [x] Deployment target and 0.2.0 marketing version declared
- [x] Keychain credential storage present
- [x] ATS local-network exception scoped in project configuration
- [x] `NSLocalNetworkUsageDescription` present
- [ ] Generate `BridgeZeroMobile.xcodeproj` with XcodeGen on macOS
- [ ] Select a valid Apple development team and provisioning profile
- [ ] Add and verify production app-icon assets before release packaging
- [ ] Build and run unit/UI tests in Xcode
- [ ] Install on a physical iPhone
- [ ] Verify first-use local-network prompt and connectivity
- [ ] Verify authentication, compatibility gating, history, and conversation streaming
- [ ] Verify operational SSE updates after B-01 is resolved
- [ ] Verify background/foreground behavior and reconnect after network loss
- [ ] Verify Dark Mode, system theme, Dynamic Type, VoiceOver labels, and keyboard behavior

No background mode entitlement is required for an operator console that suspends in the background. The app does need explicit scene-phase handling if polling/streams must stop and reconnect predictably.

### Android

- [x] Internet permission present
- [x] Release cleartext disabled
- [x] Debug network-security override permits LAN development
- [x] Encrypted credential storage present
- [ ] Generate and commit the Gradle wrapper
- [ ] Install JDK 17, Android SDK 37, and compatible build tools
- [ ] Resolve dependencies and run unit tests
- [ ] Run instrumentation tests and `assembleDebug`
- [ ] Install on a physical Android device
- [ ] Verify authentication, compatibility gating, history, and conversation streaming
- [ ] Verify operational SSE updates after B-01 is resolved
- [ ] Verify background/foreground behavior, process recreation, and reconnect after network loss
- [ ] Verify dark theme, enlarged font/display scaling, TalkBack labels, and keyboard behavior
- [ ] Add and verify launcher icons before release packaging

### Desktop and frontend

- [x] Both production builds pass at 0.2.0
- [ ] Smoke-test runtime connection against the checkpoint backend
- [ ] Confirm the desktop conversation path is included in RuntimeStore stream telemetry
- [ ] Confirm release metadata reports 340 backend tests

## Runtime architecture findings

### Confirmed

- CPU and memory originate from `psutil`; they are measured rather than simulated.
- Tool queue depth originates from persisted tool-request states.
- Chronicle count originates from the shared Chronicle file.
- Current session originates from the conversation database.
- Connected-client count is observed from client IDs with a 30-second TTL.
- Mobile conversation streaming delegates to the established runtime stream and observes its lifecycle.
- RuntimeEventBus uses bounded per-subscriber queues and deterministic event names.
- Native UI state has one store instance per application process.
- Status, diagnostics, Chronicle, and conversation surfaces render response data; no randomized or timer-fabricated status was found.

### Violations and limitations

- Operational polling replaces consumption of typed SSE in both native clients.
- Native event buses are write-only; no subscriber was found.
- Backend event types declare status, diagnostics, session, and Chronicle, but current publishers emit only telemetry and streaming events.
- RuntimeEvent payloads are generic dictionaries; the OpenAPI feed is described as a string rather than a discriminated payload union.
- Stream telemetry excludes the desktop `/chat/stream` path.
- Reading telemetry mutates `current_session` by projecting the latest database conversation into RuntimeStore.
- The SSE feed has no heartbeat or resumption cursor.

## Mobile architecture audit

| Concern | iOS | Android | Finding |
|---|---|---|---|
| Navigation | SwiftUI `TabView` | Compose tab enum and `Scaffold` | Clear and local to UI |
| Connection manager | Folded into `OperatorConsoleState` | Folded into `OperatorViewModel` | No duplicate manager, but store has too many responsibilities |
| RuntimeStore | Type alias over console state | Type alias over view model | Single UI authority, but naming is cosmetic rather than a distinct boundary |
| Networking | One `RuntimeAPIClient` actor | One `RuntimeApi` wrapper | No duplicated networking found |
| Event bus | Publishes only | Publishes only | No consumers; does not drive state |
| Conversation streaming | URLSession SSE parser | OkHttp blocking stream on IO dispatcher | Both delegate to the mobile adapter |
| Diagnostics | Read-only view | Read-only screen | No duplicate state |
| Settings | Reads shared store | Reads shared store | No duplicate networking |
| Chronicle | Loaded into shared store | Loaded into shared store | No duplicate source |
| Circular dependencies | None found | None found | Backend route imports private mobile helpers but no import cycle |

The principal single-responsibility concern is that each native store owns credentials, connection lifecycle, polling, networking orchestration, streaming, logs, theme/settings, conversation state, and UI state. Separation can be performed later without changing observable behavior, but the SSE authority blockers should be resolved first.

## Design-system audit

| Token family | Shared contract | SwiftUI | Compose | Result |
|---|---|---|---|---|
| Colors | Eight named colors | Named colors present, but `void`, `panel`, and `raised` RGB values differ; separator is replaced by white opacity | All eight exact hexadecimal values present | Not equivalent |
| Spacing | 4/8/12/16/24 | Constants exist, but many screens still use hardcoded values | Constants exist, but most screens still use hardcoded values | Foundation only |
| Radii | 6/8/12 | Values used directly; no named radius namespace | Named radius values exist; many components use direct values | Partial parity |
| Typography | Display/title/body/label/metric | Mostly semantic SwiftUI fonts with some matching sizes/tracking; no complete named token set | Default Material typography; no shared typography mapping | Not equivalent |
| Cards | Card token 12 | `InstrumentPanel` uses radius 12 and panel fill | `InstrumentPanel` uses radius 12 and panel fill | Equivalent foundation |
| Status badges | Semantic status map | Reusable `StatusBadge` exists | No equivalent badge component | Missing on Android |
| Status colors | Shared semantic map | `unavailable` maps to failure and `inactive` to muted | Screen-level mappings, not shared semantic tokens | Not equivalent |

No redesign is recommended. Complete the existing token mapping, replace only divergent hardcoded foundation values, and add parity tests or a generated comparison.

## Documentation audit

README, CHANGELOG, ROADMAP, PROJECT_STATUS, ARCHITECTURE_DECISIONS, versioning policy, manifests, and contracts consistently identify Epoch IX / Version 0.2.0 with IX-B active and IX-C/IX-D future-only. The versioning table now records `epoch-ix-a` as planned because no such tag exists yet.

The current documents are synchronized. They must not mark IX-B complete until blockers B-01 through B-05 and the physical-device gate are closed.

## Closure sprint update — 2026-07-23

- Native iOS and Android RuntimeStores now consume typed `/api/mobile/v1/events`; periodic mobile operational polling was removed.
- Shared backend stream observation now publishes session/streaming transitions for both `/chat/stream` and mobile conversation streams.
- Backend binding is configurable through `OMEGA_BIND_HOST` and `OMEGA_BACKEND_PORT`.
- Pytest mutable tool stores are redirected to a temporary `OMEGA_TOOL_DATA_DIR`.
- Frontend and desktop production builds pass; 16 focused backend tests pass; `git diff --check` passes.
- Blocking gates remain: absent Android Gradle Wrapper, unperformed physical-device validation, unclosed design-token differences, desktop typed-event consumption validation, and an unconfirmed full backend run (timeout over 120 seconds).

See `RELEASE_CANDIDATE.md` for the authoritative gate matrix.

## Android physical-device validation — 2026-07-23

First hardware run of the native Android operator console.

| Field | Value |
|---|---|
| Device | moto g15 power |
| OS | Android 15 |
| Build | debug APK, `versionName 0.2.0` / `versionCode 1` |
| Toolchain | Gradle 9.5.0, JDK 21 (Temurin 21.0.11), Android SDK 37 |
| Source | uncommitted working tree (includes the remediation fixes below) |
| Tester / date | Bill H / 2026-07-23 |

### Verified on hardware

- Clean `gradlew clean assembleDebug` — 37/37 tasks executed, `BUILD SUCCESSFUL`. This is the
  first real compile of the working-tree Android fixes (OkHttp `use{}` close, atomic
  `MutableStateFlow.update`, `runInterruptible` cancellation, design-token changes). All compiled
  with no warnings attributable to those edits.
- `installDebug` to the physical device succeeded.
- Bearer authentication and the compatibility gate over LAN (`http://<host>:8001`).
- Operations Dashboard populated from measured runtime telemetry.
- Live typed-SSE updates: dashboard values advanced with no manual refresh and no polling.
- Conversation streaming: phase event plus token-by-token deltas rendered on device.
- Offline recovery: Wi-Fi loss produced an Offline state, followed by unattended reconnect.
- Background-to-foreground: SSE suspended on stop and resumed on start without re-authentication.

- Dark theme: unchanged appearance (the console hard-codes a dark scheme by design) and nothing
  became unreadable when the system theme was toggled.
- Enlarged font and display scaling: layout becomes visually crowded at maximum settings but no
  text overlapped or truncated. Cosmetic observation, not a release-blocking defect.
- Unit tests on this toolchain: `testDebugUnitTest` — 8 tests across `MobileVersionTest`,
  `RuntimeApiValidationTest`, and `SseParserTest`; 0 skipped, 0 failures, 0 errors.

**Android device checklist result: 8/8 pass, no release-blocking defect.**

### Still outstanding on Android

- Instrumentation tests, TalkBack pass, release-configuration build.
- Android sources remain untracked; the build is therefore not yet reproducible from a clean clone.
- Unit coverage does not exercise the ViewModel state machine, streaming lifecycle, or reconnect
  path — the areas that actually contained defects. Recorded as debt (see `TECHNICAL_DEBT.md`).

### Environment caveats

- Backend was bound to the LAN via `OMEGA_BIND_HOST=0.0.0.0` with a deliberately weak development
  token; this is a validation posture only and must not be carried into any release configuration.
- The default `dolphin-mixtral:8x7b` runs ~77% on CPU on this host and could not emit tokens in a
  usable time, so streaming was exercised with an operator-selected `llama2-uncensored:7b`. Model
  selection does not affect the streaming transport under test, and Model Lock semantics were
  unchanged (explicit operator selection only).
- Deficiency found during the run: `scripts/launch_backend.py` read `OMEGA_BIND_HOST` before
  `.env` was loaded, so a LAN profile placed in `.env` was silently ignored and the server stayed
  on loopback. Corrected in the working tree; this was the practical form of B-03/TD-C04.

**iOS has no hardware run.** The physical-device gate remains open until an iPhone pass is
recorded.

## iOS validation attempt — 2026-07-23

The previously undetected compile-blocking defect in `Sources/APIClient.swift`
(`APIConfiguration.isLocal`, unbalanced parenthesis) has been corrected in the working tree.
Structural verification on the source: all twelve Swift files are brace- and paren-balanced,
`APIClient.swift` at 62/62 braces and 142/142 parentheses.

A compile could **not** be completed. The available macOS host is a VirtualBox guest running
**macOS 11 (Big Sur), Swift 5.4.2** (`swiftlang-1205.0.26.2`). The project declares
`SWIFT_VERSION: 5.10` and uses `actor` and `async`/`await` throughout, which require Swift 5.5 or
newer. `swiftc -parse` therefore failed on ordinary modern-Swift constructs — `actor` parsed as a
top-level expression, `await` reported as a reserved future keyword — rather than on any defect in
the sources.

This ceiling is structural, and the SDK requirement binds harder than the Swift version. The
project declares `deploymentTarget: iOS 17.0` and uses `ContentUnavailableView`
(`DiagnosticsView.swift:29`, `SettingsView.swift:55,72`), which is iOS 17 only, plus
`NavigationStack`, `URL.appending(path:)`, `Task.sleep(for:)`, and `.scrollContentBackground`,
all iOS 16+. The iOS 17 SDK ships only with Xcode 15 or newer, which requires macOS 13.5+.

Big Sur's maximum, Xcode 13.2.1, carries the iOS 15 SDK; a build there fails on missing types
rather than on syntax. Selecting a different developer directory with `xcode-select` cannot
substitute, because the required SDK symbols are absent, not mislabelled.

**Minimum viable iOS toolchain: Xcode 15+ (iOS 17 SDK) on macOS 13.5+.**

**Status: iOS remains unvalidated.** The original defect is resolved by inspection, but no
compiler has confirmed it, and no simulator or device run exists. Do not record iOS as validated
on the strength of the structural check alone.

Recommended path: build iOS on a macOS CI runner with Xcode 15.3+ once the sources are committed.
That yields reproducible evidence without local VM toolchain work and simultaneously supports the
clean-clone reproducibility gate. A macOS 13+ host or physical Mac is the alternative.
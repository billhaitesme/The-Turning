# Changelog

## [0.2.0] - Pending Release

**Current status:**

- RC1 validation in progress (Epoch IX-B — Runtime Operations)
- Checkpoint commit not yet created
- No `epoch-ix-a` release tag exists
- The mobile clients and shared contract are present in the working tree but untracked

This entry describes the state of the release candidate. Version 0.2.0 must not be described as
released until the reviewed checkpoint commit and its annotated tag actually exist.

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
- Android Gradle wrapper present in the tree (Gradle 9.3.1, SHA-256 pinned)

### Validated

- Backend test suite: **340 passing** in ~117 s; hermetic (tests redirect mutable stores to a
  temporary `OMEGA_TOOL_DATA_DIR` and leave tracked runtime data unchanged)
- Desktop Bridge Zero and frontend Vite production builds succeed at 0.2.0
- Shared OpenAPI and design-token files parse
- Android: clean `assembleDebug` and `testDebugUnitTest` pass (Gradle 9.5.0 / JDK 21 / SDK 37);
  8/8 physical-device checklist on moto g15 power / Android 15
- iOS: `xcodegen generate`, simulator build, unit + UI tests, and `.ipa` packaging pass on CI
  (macos-14 / Xcode 16 / iOS 17 SDK / Swift 5.10) — the `APIClient.swift` fix is compiler-confirmed

### Pending Validation

- Physical iPhone run (install the CI `.ipa` via Sideloadly/AltStore; CI cannot drive a device)
- Android instrumentation tests, TalkBack pass, and a release-configuration build
- The `backend/data/` runtime records need a fixture-or-ignore decision before the tree is clean
- Desktop typed-event consumption parity (desktop Bridge Zero still refreshes via `/system/*` REST
  polling rather than consuming the typed SSE stream)
- Design-token parity confirmed on device (or via a generated comparison test)
- LAN connectivity validation with a secure `MOBILE_AUTH_TOKEN`

### Known Release Blockers

- Physical-iPhone validation not yet recorded (the Android hardware pass is recorded)
- `epoch-ix-a` tag not yet created — deliberately withheld until the physical-iPhone run is
  recorded and the `backend/data/` records are resolved
- `backend/data/` runtime records remain uncommitted pending a fixture-or-ignore decision

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

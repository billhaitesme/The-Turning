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

### Pending Validation

- iOS native compile and unit/UI tests (a compile-blocking syntax error was fixed in the tree, but
  no macOS/Xcode build has confirmed it)
- Android unit, instrumentation, and `assembleDebug` runs (wrapper present but untracked and unrun;
  the concurrency/resource fixes are unbuilt)
- Physical iPhone and physical Android device validation
- Desktop typed-event consumption parity (desktop Bridge Zero still refreshes via `/system/*` REST
  polling rather than consuming the typed SSE stream)
- Design-token parity confirmed on device (or via a generated comparison test)
- LAN connectivity validation with a secure `MOBILE_AUTH_TOKEN`

### Known Release Blockers

- No reviewed checkpoint commit exists; `epoch-ix-a` does not exist; the mobile and shared trees
  are untracked
- Native iOS and Android builds are unverified
- The physical-device validation gate in `PROJECT_STATUS.md` has no recorded hardware pass
- Design-token parity is not yet device-verified
- Full clean-clone reproduction of backend + web + native builds is unconfirmed

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

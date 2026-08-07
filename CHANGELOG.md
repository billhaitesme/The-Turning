# Changelog

## [Unreleased] — Epoch IX-C (Operator Actions)

In progress on `feature/epoch-ix-c-model-selector`, built on the tagged `epoch-ix-a` IX-B baseline.
No IX-C behavior is present in that checkpoint. Backend suite: **345 passing**, hermetic.

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

### Pending

- Android on-device pass for approvals/biometric; on-device icon confirmation on both platforms.
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

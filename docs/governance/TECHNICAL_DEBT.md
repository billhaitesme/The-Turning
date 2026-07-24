# Epoch IX Technical Debt

This register contains implementation debt found during the IX-B completion audit. It excludes feature requests and IX-C scope.

## Critical

### TD-C01 — Operational SSE is not the native state transport

Both native clients poll status, telemetry, and diagnostics every 2.5 seconds. Neither consumes `/api/mobile/v1/events`; both event buses are write-only. Resolve before IX-B completion.

### TD-C02 — RuntimeStore omits desktop streams

Only the mobile message adapter calls `begin_stream` and `end_stream`. Desktop/frontend `/chat/stream` activity is absent from active-stream and latency telemetry. Instrument the shared authoritative stream boundary once.

### TD-C03 — Android build lacks a Gradle wrapper

The checkout cannot reproduce Android builds without external, undocumented Gradle setup. Generate and commit the supported wrapper, then validate unit, instrumentation, and debug assembly tasks.

### TD-C04 — Standard launch path is not device reachable

All standard backend launch helpers bind to loopback. Add a deliberate, documented LAN validation profile with secure token and firewall guidance; keep the default local-only posture.

## Medium

### TD-M01 — Tests mutate tracked runtime data

The complete backend suite appends tool requests/results to tracked JSON stores. Tests must inject temporary paths/stores and leave the working tree unchanged.

### TD-M02 — Native stores combine too many responsibilities

`OperatorConsoleState` and `OperatorViewModel` own credentials, connection lifecycle, polling, networking orchestration, conversation streaming, logs, settings, and presentation state. Introduce boundaries only through behavior-preserving refactoring.

### TD-M03 — Typed events have untyped payloads and incomplete publishers

Runtime event names are enumerated, but payloads are generic dictionaries. Status, diagnostics, session, and Chronicle event types have no active publishers. The OpenAPI stream is a string instead of a discriminated event schema.

### TD-M04 — Event stream has no heartbeat or resume strategy

Idle subscribers may be dropped by intermediaries, and reconnecting clients cannot request events after a known ID. Define heartbeat and resumption semantics before relying on SSE for device state.

### TD-M05 — Background/foreground lifecycle is implicit

iOS has no scene-phase handling. Android polling is tied to `viewModelScope`, not foreground lifecycle. Device testing must establish whether work suspends, resumes, and reconnects predictably.

### TD-M06 — Shared design tokens are not equivalent

SwiftUI base surface colors differ from the shared hex values, Compose lacks typography and status-badge mappings, and both clients retain many hardcoded spacing/radius values. Align the existing foundation without redesigning screens.

### TD-M07 — Runtime operations route imports private mobile helpers

`runtime_operations.py` imports underscored functions from `mobile.py`. Move shared projections behind a public service boundary to reduce route coupling.

### TD-M08 — Local-host validation accepts every `172.*` address

Both clients treat the entire `172.0.0.0/8` range as local rather than only `172.16.0.0/12`. Tighten validation to the private range.

## Low

### TD-L01 — Native release assets are absent

No iOS asset catalog or Android launcher-icon resources are present. Physical debug installation may still work, but release packaging is incomplete.

### TD-L02 — IX-C permission and placeholder text are present in IX-B

The manifests declare biometric usage and Settings displays future notification text although IX-C behavior is inactive. Remove unused permission declarations/placeholders from the IX-B release or record a specific accepted reason to retain them.

### TD-L03 — Deprecated APIs remain

FastAPI startup events, `datetime.utcnow`, Starlette’s current TestClient bridge, and Android EncryptedSharedPreferences emit or carry deprecation concerns. They are not IX-B blockers but need planned migrations.

### TD-L04 — Duplicate historical snapshot is tracked

`ZIP for CA/` duplicates an older repository tree. Confirm provenance, preserve it in an appropriate archive if required, and remove the working-copy duplication in a separate reviewable cleanup.

### TD-L05 — Ignore rules contain duplication

`.gitignore` lists `runtime-backup/` twice. Consolidate during a hygiene-only change.

## Closure sprint update — 2026-07-23

- Native iOS and Android RuntimeStores now consume typed `/api/mobile/v1/events`; periodic mobile operational polling was removed.
- Shared backend stream observation now publishes session/streaming transitions for both `/chat/stream` and mobile conversation streams.
- Backend binding is configurable through `OMEGA_BIND_HOST` and `OMEGA_BACKEND_PORT`.
- Pytest mutable tool stores are redirected to a temporary `OMEGA_TOOL_DATA_DIR`.
- Frontend and desktop production builds pass; 16 focused backend tests pass; `git diff --check` passes.
- Blocking gates remain: absent Android Gradle Wrapper, unperformed physical-device validation, unclosed design-token differences, desktop typed-event consumption validation, and an unconfirmed full backend run (timeout over 120 seconds).

See `RELEASE_CANDIDATE.md` for the authoritative gate matrix.

## Working-tree remediation — 2026-07-23 (pending build validation)

Changes applied to the working tree in response to the independent review. None have been
validated by a native build yet, so no release gate may be marked passed on their basis.

- **TD-C03 (Android Gradle wrapper):** wrapper is now present in the tree (`gradlew`,
  `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, `gradle-wrapper.properties`), pinned to
  Gradle 9.3.1 with `distributionSha256Sum`. It is still untracked and no Gradle task has been
  executed on a toolchain — reproducibility is not yet demonstrated.
- **iOS compile break (new, not previously registered):** `APIConfiguration.isLocal`
  (`bridge/bridge-zero-ios/Sources/APIClient.swift`) had an unbalanced parenthesis that would
  fail to parse. Balanced. Pending a real Swift compile on macOS to confirm the client builds.
- **TD (new) — Android OkHttp response leak:** `streamRuntimeEvents`/`streamMessage`
  (`RuntimeApi.kt`) never closed the `ResponseBody`, leaking a connection on every 3-second
  reconnect. Both now release the body via `use { }`.
- **TD-M02-adjacent — Android non-atomic state:** `OperatorViewModel` performed
  `mutableState.value = mutableState.value.copy(...)` read-modify-writes from both the Main
  event-bus collector and the IO stream callback. All such sites now use atomic
  `MutableStateFlow.update { }`; the only remaining direct assignment is the terminal
  `disconnect()` reset.
- **Android blocking-read cancellation:** the blocking SSE reads now run under
  `runInterruptible(Dispatchers.IO)` so coroutine cancellation interrupts the read instead of
  holding the socket until server timeout.
- **TD-M06 (design-token parity):** foundation aligned. iOS `void`/`panel`/`raised`/separator
  colors now derive from the shared hex via a `Color(bridgeHex:)` initializer; `BridgeTypography`
  (iOS) and `BridgeDesign.Type` (Android) typography tokens added; a shared Android `StatusBadge`
  composable and `statusColor` map added; shared components adopt spacing/radius/typography tokens
  where the literal exactly equals a token value (no visual redesign). Intentional platform
  differences and remaining per-screen adoption are recorded in
  `docs/architecture/design-system.md`. Pending native-build/on-device confirmation.
- **TD-M08 (172.0.0.0/8 over-match):** intentionally left for a dedicated hygiene change to keep
  the compile/correctness fixes narrowly reviewable. Still open on both clients.

### TD-M09 — Native unit coverage misses the paths that actually broke

The Android unit suite is 8 tests (`MobileVersionTest`, `RuntimeApiValidationTest`,
`SseParserTest`). It covers version gating, server-address validation, and SSE parsing, but
nothing exercises the `OperatorViewModel` state machine, the conversation streaming lifecycle,
reconnect/backoff, or response-body release. Every defect fixed on 2026-07-23 — the unclosed
OkHttp `ResponseBody`, the non-atomic `MutableStateFlow` read-modify-write, and the
uncancellable blocking read — was invisible to this suite and would regress undetected. iOS
coverage is comparably narrow (`APIConfigurationTests`, `MobileVersionTests`, `SSEParserTests`).

Add behavior-level tests around the store's connect/stream/reconnect transitions before relying
on these clients for operator-facing actions in IX-C.
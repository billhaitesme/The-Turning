# OMEGA-ARC IX-B Release Candidate Matrix

**Epoch:** IX ·
**Version:** 0.2.0 ·
**Assessment date:** 2026-07-23 ·
**Decision:** Not yet eligible for IX-B closure.

| Gate | Status | Evidence |
|---|---|---|
| Backend Tests | ⚠️ | 340 collected; 16 changed-area tests pass. Full run exceeded 120 seconds and remains unconfirmed. |
| Desktop Build | ✅ | Vite production build succeeded. |
| Frontend Build | ✅ | Vite production build succeeded. |
| RuntimeStore Event-Driven | ✅ | iOS and Android consume `/api/mobile/v1/events`; periodic 2.5-second mobile polling removed. Manual refresh and 3-second reconnect backoff remain intentional. |
| Desktop/Mobile Runtime Parity | ⚠️ | Shared backend stream observation covers `/chat/stream` and mobile streams, but desktop still needs direct typed-event consumption validation. |
| LAN Connectivity | ⚠️ | `OMEGA_BIND_HOST` and `OMEGA_BACKEND_PORT` remove source edits; physical LAN validation remains outstanding. |
| Android Build Reproducibility | ⚠️ | Wrapper present (`gradlew`, `gradlew.bat`, `gradle-wrapper.jar`, `gradle-wrapper.properties`), pinned to Gradle 9.5.0 with `distributionSha256Sum` and `validateDistributionUrl` (Android Studio sync raised the pin from 9.3.1 on 2026-07-23). `gradlew clean assembleDebug` verified: 37/37 tasks, `BUILD SUCCESSFUL` on JDK 21 (Temurin 21.0.11) / SDK 37, and `installDebug` to a physical device succeeded. Still ⚠️ because the Android sources and wrapper remain **untracked**, so a clean-clone build is unproven, and `testDebugUnitTest`, instrumentation tests, and a release build have not been run. |
| Design Token Parity | ⚠️ | Foundation aligned in the tree: iOS `void`/`panel`/`raised`/separator colors now derive from the shared hex; typography tokens and an Android status-badge component were added on both platforms; shared components adopt spacing/radius/typography tokens. No redesign was performed. Not yet confirmed by a native build or an on-device/generated comparison. See `docs/architecture/design-system.md`. |
| Test Hygiene | ✅ | Pytest uses a temporary `OMEGA_TOOL_DATA_DIR`; focused mutable-store tests pass. Pre-existing tracked data changes were preserved. |
| OpenAPI Validation | ⚠️ | Focused mobile contract tests pass; standalone schema validation not completed in this sprint run. |
| JSON/YAML Validation | ⚠️ | Validation encountered a pre-existing UTF-8 BOM JSON file; targeted formats require a BOM-aware rerun. |
| `git diff --check` | ✅ | Passed (line-ending warnings only). |
| Physical iOS Validation | ❌ | Attempted 2026-07-23 and blocked by host toolchain. Available macOS host is macOS 11 (Big Sur) with Swift 5.4.2; the project requires Swift 5.10, which needs Xcode 15.3+ and macOS 13.5+. No compile, simulator, or device run exists. A compile-blocking defect in `APIClient.swift` was found and fixed, and is structurally verified (all Swift files brace/paren balanced), but **no compiler has confirmed it**. See `IX_B_VALIDATION_REPORT.md`. |
| Physical Android Validation | ✅ | Hardware run recorded 2026-07-23 on moto g15 power / Android 15: **8/8 device-checklist items pass, no release-blocking defect** (launch, bearer auth + compatibility gate, synchronized and streaming conversations, live typed-SSE dashboard updates, background-to-foreground, unattended offline reconnect, dark theme, font/display scaling). `testDebugUnitTest` passes (8 tests, 0 failures). Crowding at maximum display scaling noted as cosmetic. Instrumentation tests, TalkBack, and a release build remain — tracked under Android Build Reproducibility. See `IX_B_VALIDATION_REPORT.md`. |

## Accepted polling and recovery behavior

There is no periodic operational REST polling in either mobile RuntimeStore. REST reads are used only for initial bootstrap, explicit operator Refresh, conversation reconciliation, and compatibility checks. SSE reconnect uses a three-second backoff. The server emits a five-second telemetry heartbeat to keep client presence and measured runtime telemetry current.

## Closure rule

Do not create the release checkpoint until Android wrapper reproducibility, desktop typed-event validation, design-token parity, the full backend run, and both physical-device gates are resolved or explicitly accepted by the release owner.
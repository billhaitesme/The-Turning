# Epoch IX-C Readiness Assessment

| Field | Value |
|---|---|
| Assessment date | 2026-07-22 |
| Current identity | Epoch IX / Version 0.2.0 |
**Decision:** Not ready to begin IX-C

IX-B has a credible implementation foundation, and backend/web validation is green. IX-C must remain future-only until the blocking items below are closed.

## Blocking issues only

1. **Native operational SSE is not implemented end to end.** iOS and Android poll operational state and do not consume `/api/mobile/v1/events`.
2. **RuntimeStore stream telemetry is incomplete.** Desktop `/chat/stream` activity bypasses RuntimeStore, so active stream and latency values are not runtime-wide.
3. **Android builds are not reproducible.** The Gradle wrapper is absent and native build/test evidence does not exist.
4. **Physical-device validation is incomplete.** Neither platform checklist has a recorded hardware pass.
5. **The device network path is not ready.** Standard backend launchers bind to loopback; a secure opt-in LAN validation profile is required.
6. **Native design-system parity is incomplete.** Shared colors, typography, spacing/radii, and status badges are not equivalently mapped on both platforms.
7. **The repository checkpoint is not reproducible.** The dirty tree contains intertwined implementation, governance, generated runtime data, and unrelated work; `epoch-ix-a` does not exist.

## Required evidence to change the decision

- [ ] Native clients consume typed operational SSE and reconnect deterministically
- [ ] Polling is limited to an explicit fallback/recovery role rather than replacing SSE
- [ ] RuntimeStore observes both desktop and mobile stream lifecycles
- [ ] Event payload contracts and publishers cover the advertised event types
- [ ] Android wrapper, unit tests, instrumentation tests, and debug assembly pass
- [ ] iOS generation, compile, unit tests, and UI tests pass on macOS
- [ ] Physical iPhone checklist passes and records device/build details
- [ ] Physical Android checklist passes and records device/build details
- [ ] Native design-token parity audit passes
- [ ] Tests leave tracked runtime data unchanged
- [ ] Clean-clone backend/web/native validation passes
- [ ] Reviewed checkpoint commit exists on the release branch
- [ ] Annotated `epoch-ix-a` tag targets that commit

## What is already ready

The following foundations do not require redesign:

- authenticated mobile API and compatibility gate;
- synchronized conversation history and delegated conversation SSE;
- secure native credential storage;
- measured CPU and memory telemetry;
- persisted tool-queue and Chronicle projections;
- single native UI-state authority per application process;
- Operations Dashboard structure;
- shared OpenAPI and design-token sources;
- synchronized Epoch IX / Version 0.2.0 governance documents;
- Model Lock and deterministic runtime boundaries.

## Reassessment rule

Reassess after the blocking evidence is recorded, not after additional feature work. IX-C begins only from the reviewed IX-B checkpoint commit and tag.

## Closure sprint update — 2026-07-23

- Native iOS and Android RuntimeStores now consume typed `/api/mobile/v1/events`; periodic mobile operational polling was removed.
- Shared backend stream observation now publishes session/streaming transitions for both `/chat/stream` and mobile conversation streams.
- Backend binding is configurable through `OMEGA_BIND_HOST` and `OMEGA_BACKEND_PORT`.
- Pytest mutable tool stores are redirected to a temporary `OMEGA_TOOL_DATA_DIR`.
- Frontend and desktop production builds pass; 16 focused backend tests pass; `git diff --check` passes.
- Blocking gates remain: absent Android Gradle Wrapper, unperformed physical-device validation, unclosed design-token differences, desktop typed-event consumption validation, and an unconfirmed full backend run (timeout over 120 seconds).

See `RELEASE_CANDIDATE.md` for the authoritative gate matrix.
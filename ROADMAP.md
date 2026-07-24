# OMEGA-ARC Roadmap

**Current epoch:** Epoch IX
**Current release:** 0.2.0
**Active release line:** 0.2.x

## Epoch IX-A — Mobile Operator Console (0.2.0)

Status: complete.

- Authenticated mobile runtime API
- Native iOS and Android operator consoles
- Runtime status, Model Lock, diagnostics, and Chronicle
- Synchronized history and SSE conversation streaming
- Version compatibility gates and secure credential storage

## Epoch IX-B — Runtime Operations (0.2.x)

Status: active.

- Authoritative RuntimeStore
- Typed SSE events and event bus
- Measured CPU, RAM, latency, tool queue, streaming state, connected clients, current session, and Chronicle telemetry
- Operations Dashboard
- Shared colors, typography, spacing, badges, and cards

### IX-B validation gate

Before IX-B is complete and IX-C begins, both native clients must pass the physical-device checklist in [`PROJECT_STATUS.md`](PROJECT_STATUS.md). The checkpoint must then be committed from an intentionally scoped clean tree and tagged `epoch-ix-a`.

IX-B runtime infrastructure is implemented. Dashboard polish, telemetry refinement, native-device validation, and the reproducible checkpoint remain active work.

## Epoch IX-C — Operator Actions (future 0.2.x)

Push notifications, short-lived approval challenges, approve/deny flows, and biometric confirmation. No IX-C behavior is active in IX-B.

### Deferred operator-convenience items

Discovered during IX-B physical-device validation (2026-07-23, moto g15 power / Android 15).
Both are capability gaps, not defects, and are deliberately excluded from IX-B scope.

- **No in-app "New Conversation" control.** The native console binds to whatever the runtime
  reports as the active conversation (the most recently updated one). Starting a new conversation
  currently requires `POST /api/mobile/v1/conversations` plus an app relaunch, because the client
  resolves the active conversation only at connect time and session events publish only when a
  stream begins. IX-C should provide an operator-initiated conversation action and a way to switch
  the bound conversation without relaunching.
- **No default/pre-filled server address.** Credentials persist across launches, but tapping
  Disconnect clears both server and token, forcing full re-entry. IX-C should offer a debug-only
  `buildConfigField` default (never a hardcoded LAN address in shared source) and/or retain the
  non-secret server address while still clearing the token on disconnect.

## Epoch IX-D — Command Console (future 0.2.x)

Promote the operations surface into the full command console after IX-B telemetry and IX-C approval signals are authoritative. No IX-D behavior is active in IX-B.

Historical milestones remain recorded in [VERSION_HISTORY.md](VERSION_HISTORY.md) and `docs/architecture/roadmap.md`.

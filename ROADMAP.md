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

Push notifications, short-lived approval challenges, approve/deny flows, and biometric confirmation. No IX-C behavior is active in the IX-B checkpoint.

### In progress (feature/epoch-ix-c-model-selector)

- **Operator model selector.** An allowlisted, Model-Lock-recorded model selector across backend,
  desktop, Android, and iOS. The model changes only on explicit operator action, routed through
  `set_selected_model` → `set_active_model`, recorded in telemetry. Backend (344 tests) and Android
  (compiled + unit-tested) are validated; desktop is built; iOS awaits a CI compile and a device
  pass. Kept off the IX-B checkpoint branch so `epoch-ix-a` stays a clean IX-B baseline.
- **New Conversation control.** An operator action on both mobile consoles (iOS toolbar, Android
  composer) that creates a fresh conversation via `POST /api/mobile/v1/conversations` and rebinds
  the console live, without a relaunch. Android compiled; iOS awaits a CI compile and device pass.
  (Desktop Bridge Zero has no chat by design, so no control there.)

### Deferred operator-convenience items

Discovered during IX-B physical-device validation (2026-07-23, moto g15 power / Android 15).
Capability gaps, not defects, deliberately excluded from IX-B scope.

- **In-app "New Conversation" control** — now implemented (see In progress above). The console no
  longer needs a relaunch to start a fresh conversation.
- **No default/pre-filled server address.** Credentials persist across launches, but tapping
  Disconnect clears both server and token, forcing full re-entry. IX-C should offer a debug-only
  `buildConfigField` default (never a hardcoded LAN address in shared source) and/or retain the
  non-secret server address while still clearing the token on disconnect.

## Epoch IX-D — Command Console (future 0.2.x)

Promote the operations surface into the full command console after IX-B telemetry and IX-C approval signals are authoritative. No IX-D behavior is active in IX-B.

## Epoch X — Memory (future, scope not yet committed)

Durable, scoped, benchmarked long-term memory. The substrate the learning pillar depends on. See
[`docs/architecture/epoch-x-memory-and-retrieval.md`](docs/architecture/epoch-x-memory-and-retrieval.md).

## Future — Tutelage and Learning (proposed, unscheduled)

The epoch where OMEGA-ARC begins studying: a runtime-driven, review-gated study loop with two-tier
learning (reversible memory + gated LoRA consolidation) and a recall benchmark so growth is measured.
Sequenced after Epoch X — a learner must remember reliably first. See ADR
[`0013-learning-and-tutelage.md`](docs/decisions/0013-learning-and-tutelage.md) and
[`docs/architecture/epoch-tutelage-learning.md`](docs/architecture/epoch-tutelage-learning.md).

Historical milestones remain recorded in [VERSION_HISTORY.md](VERSION_HISTORY.md) and `docs/architecture/roadmap.md`.

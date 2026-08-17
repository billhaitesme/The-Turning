# OMEGA-ARC Core Runtime

**Current release:** tracks the shared identity in [`docs/architecture/versioning.md`](../docs/architecture/versioning.md) (currently Epoch XII / 0.5.0)

The backend is the deterministic authority for identity, evidence, planning, deliberation, tools, conversation persistence, Model Lock, and Bridge Zero synchronization.

Epoch IX adds an authenticated mobile adapter and IX-B operations telemetry without replacing the established runtime or model-routing architecture.

Key boundaries:

- Operator-controlled Model Lock remains authoritative.
- Mobile and desktop clients render runtime state; they do not invent it.
- `/api/mobile/v1/telemetry` exposes measured RuntimeStore state.
- `/api/mobile/v1/events` exposes typed server-sent runtime events.
- IX-C operator actions (approvals + biometric, model selector) shipped in 0.2.1; Epoch X added the memory subsystem (recall benchmark, rooms, reviewed supersession, consolidation — ADRs 0016–0023). IX-D command console slice 1 (2026-08-17): services/command_registry.py + services/command_console.py, /mobile/commands… and /system/commands…, data/command_log.json; approval-gated commands execute only on a biometric-confirmed approval (COMMAND_EXECUTION, default on).

# OMEGA-ARC Core Runtime

**Current release:** Epoch IX / Version 0.2.0

The backend is the deterministic authority for identity, evidence, planning, deliberation, tools, conversation persistence, Model Lock, and Bridge Zero synchronization.

Epoch IX adds an authenticated mobile adapter and IX-B operations telemetry without replacing the established runtime or model-routing architecture.

Key boundaries:

- Operator-controlled Model Lock remains authoritative.
- Mobile and desktop clients render runtime state; they do not invent it.
- `/api/mobile/v1/telemetry` exposes measured RuntimeStore state.
- `/api/mobile/v1/events` exposes typed server-sent runtime events.
- IX-C approvals/notifications and IX-D command-console behavior remain future work.

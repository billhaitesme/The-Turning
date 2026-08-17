# Epoch IX-D — Command Console

**Status:** Slices 1 (backend + Android) and 2 (iOS) **built and device-validated 2026-08-17**. ADR
[`0015-command-console.md`](../decisions/0015-command-console.md) is Accepted and carries the recorded
policy shift. Slice 3 (desktop Bridge Zero panel, broader registry) is open. The design below is
as proposed; **[As built](#as-built-slice-1)** at the end records what actually shipped.

Promotes the operator consoles from *observe + approve* to *initiate* — a command surface where the
operator can start a bounded runtime action, every one flowing through the existing gates.

## The command lifecycle

```
operator initiates command
        │
        ▼
runtime request created  ── (not a direct side effect; ADR-IX-002)
        │
   risk classification
        │
   ┌────┴─────────────┐
   ▼                  ▼
low risk           above threshold
execute directly   IX-C approval challenge (biometric) ──approved──▶ execute
                                                        └──denied───▶ discard
        │                                                      │
        ▼                                                      ▼
   record outcome (Covenant: explain / reverse / preserve history)
```

## Command registry

A new deliverable: a registry mapping each command to a **risk class** and whether it is
approval-gated. Examples:

| Command | Risk | Gate |
|---|---|---|
| Select model | low | direct (Model Lock records it) |
| New conversation | low | direct |
| Refresh telemetry | low | direct |
| Initiate a bounded tool request | medium/high | IX-C approval + biometric |
| Act on a plan step / execute queued action | high | IX-C approval + biometric |
| Change conversational routing / rewrite | — | **forbidden** (Model Lock / output fidelity) |

The registry is the authority for what may be commanded and how; the console renders it, it does not
define it.

## Surfaces

- **Mobile consoles** — gain command initiation; they already host the biometric approval surface, so
  approval-gated commands complete there.
- **Desktop Bridge Zero** — may gain command capability, but any approval-gated command still requires
  confirmation on a mobile biometric. Desktop cannot self-approve a sensitive action.

## Policy change to record when shipping

IX-D implies `enable_tool_execution` moves from off-by-default toward on-but-approval-gated: every
execution passes an IX-C challenge. This is a deliberate policy shift and must be recorded (an ADR
update), not slipped in.

**Recorded 2026-08-17** in ADR 0015 → *Recorded policy shift*. Summary: a separate switch,
`COMMAND_EXECUTION` (default on), governs the operator-initiated console path, which executes only
after a biometric-confirmed approval; `ENABLE_TOOL_EXECUTION` (default off) still governs the
model-initiated chat path. Approvals now record *how* they were confirmed; only `"biometric"` releases
a command.

## Governance fit (the Covenant test)

- *Explain why?* Command + requester + approval + outcome recorded.
- *Reverse?* Commands enter the runtime pipeline, which already favors reversible, proposal-oriented
  actions; destructive commands need an explicit undo/rollback before they qualify.
- *Preserve history?* Every command logged.

## Prerequisites before building

1. **IX-C approvals validated on-device** (both platforms) — the gate must be trustworthy before
   real actions depend on it.
2. **A command risk-classification model agreed** — the registry above, filled in.
3. A recorded policy decision on enabling gated tool execution.

## First concrete step, when scheduled

Define the command registry with three commands only (one direct, one approval-gated, one forbidden),
wire the approval-gated path end-to-end through the existing IX-C flow, and validate that a
high-risk command cannot execute without a biometric — before broadening the command set.

**Done — this is slice 1, below.**

## As built (slice 1)

```
backend/services/command_registry.py   the authority: 3 commands, risk + gate, self-validating
backend/services/command_console.py    initiate · approval/deny callbacks · gated executor · command log
backend/routes/mobile.py               GET /mobile/commands · POST /mobile/commands/{name}
                                       GET /mobile/commands/history
                                       approve/deny now return the affected "command"
backend/routes/system.py               GET/POST /system/commands · GET /system/commands/history
                                       (desktop may initiate; gated commands wait for a mobile biometric)
backend/services/tool_approval.py      approve_request(..., confirmation=) — records HOW it was confirmed
backend/data/command_log.json          every command: name, risk, gate, requester, channel, request_id,
                                       approval_id, status, outcome, timestamps
backend/tests/test_command_console.py  9 tests
bridge/bridge-zero-android/…           Commands tab (registry cards RUN / REQUEST / FORBIDDEN + history)
```

**Command lifecycle as implemented** (statuses in `command_log.json`):

```
initiate ──► direct    ──► executed
         ──► forbidden ──► forbidden      (403 to the caller; still logged)
         ──► approval  ──► awaiting_approval
                              ├─ mobile approve, confirmation=biometric ──► executing ──► executed | failed
                              ├─ approve WITHOUT biometric (e.g. desktop /system) ──► stays awaiting_approval (noted)
                              ├─ deny ──► denied
                              └─ 300 s TTL passes ──► expired   (marked read-side, idempotent)
```

**The three commands:** `new_conversation` (low/direct), `run_backend_health_check`
(medium/approval → IX-C `backend_health_check` tool request, argument `port` = the runtime's own
port), `change_conversational_routing` (forbidden — shown in the console so the boundary is visible,
never runnable).

**Device validation, 2026-08-17** — Moto G15 Power, Android 0.5.0 debug build over
`adb reverse tcp:8001`: Commands → REQUEST → Approvals → Approve → fingerprint → history **EXECUTED**;
backend: tool request `completed`, approval `approved` + `confirmation: biometric`, real
`backend_health_check` result recorded. Three executions logged. Two on-device UI defects fixed in the
same slice (notice line after REQUEST; six-tab bottom bar wrapping — 10 sp single-line labels,
"Diagnostics" → "Diag") and re-confirmed by the operator.

**Slice 2 — iOS (2026-08-17, same day):** `bridge/bridge-zero-ios/Sources/CommandsView.swift` +
models/API/state; CI-built `.ipa` (run 32081261519 → 32081331882 after the stale-test fix), Sideloadly
onto the iPhone, backend reached over the iPhone USB-tether subnet (`172.20.10.6:8001` — the phone can
hit the PC with no Wi-Fi). Validated: REQUEST → Approve → Face ID → EXECUTED, `confirmation: biometric`,
real tool result. Six tabs on iOS = Runtime · Console · Commands · Approvals · More (Diagnostics,
Settings) — deliberate: the two operator-action tabs stay on the bar.

**Open (slice 3+):** desktop Bridge Zero Commands panel over the existing
`/system/commands` endpoints; broadening the registry (candidates, in order: read-only host status;
ComfyUI queue submit under approval; the school asking for consolidation approval from the phone) —
each new command needs a risk class, and destructive ones need an explicit undo before they qualify.

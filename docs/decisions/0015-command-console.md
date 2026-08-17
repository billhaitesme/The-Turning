# 0015 — Command Console (Epoch IX-D)

**Status:** Accepted (2026-08-17) — slice 1 built and validated on-device; see
[Recorded policy shift](#recorded-policy-shift-2026-08-17) and [Implementation](#implementation-slice-1-2026-08-17).
**Date:** 2026-08-07 (proposed) · 2026-08-17 (accepted)
**Depends on:** IX-C approval signals being authoritative and **device-validated** (ADR
[`0014-operator-approvals.md`](0014-operator-approvals.md)) — satisfied: iOS 2026-08-07, Android
2026-08-17.

## Context

Through IX-B/IX-C the operator surfaces are: desktop Bridge Zero is read-only Mission Control
(ADR-IX-003); the mobile consoles observe, and — with IX-C — approve or deny the runtime's action
requests with a biometric. IX-D promotes the consoles from *observe + approve* to *initiate*: the
operator can start a bounded runtime command, not only react to one the runtime raised.

The roadmap gates this on IX-C: an operator cannot safely *initiate* actions until the *approval*
signal that gates them is trustworthy. So IX-D must not begin building until IX-C approvals are
validated on real hardware.

## Decision

Add an operator command surface where every command flows through the **same existing gates**, with
no new authority and no bypass of the deterministic runtime:

1. **Commands are proposals until policy permits execution.** Initiating a command creates a runtime
   request in the existing pipeline (tool/plan/decision), not a direct side effect. This preserves
   ADR-IX-002 (the runtime owns execution).
2. **Risk-gated by the IX-C approval flow.** Any command above a defined risk threshold produces an
   approval request that must be confirmed with a biometric (IX-C) before it executes. Low-risk,
   already-explicit commands (model selection, new conversation) execute directly, as today.
3. **Model Lock and evidence unchanged.** Model selection remains the ADR-IX-001 operator action;
   commands that touch conversational routing are still forbidden.
4. **Every command is recorded and reversible where possible.** The command, its requester, its
   approval (if any), and its outcome are logged — the Covenant's "explain why / reverse / preserve
   history" test applies to each.

Desktop Bridge Zero may gain command capability too (promoting it beyond read-only), but higher-risk
commands still require confirmation on the mobile biometric surface — the desktop cannot self-approve
a sensitive action.

## Command taxonomy (initial)

- **Direct (no approval):** select model, new conversation, refresh — already shipped in IX-C.
- **Approval-gated:** initiate a bounded tool request, act on a plan step, execute a queued action.
  These create an IX-C approval challenge and wait for biometric confirmation.
- **Forbidden:** anything that would silently change the conversational model or rewrite responses
  (Model Lock / output fidelity).

## Reason and rejected alternatives

- **Rejected: a direct command executor on the console.** Letting a console execute runtime actions
  directly would put authority in the UI. Commands must enter the runtime pipeline and be gated.
- **Rejected: desktop self-approval of sensitive commands.** The biometric operator confirmation is
  the point; a desktop that approves its own high-risk command defeats it.

## Consequences

- The approval flow becomes load-bearing: IX-C must be validated on-device first (its correctness now
  gates real actions, not just a demo).
- A command registry with per-command risk classification is a new deliverable.
- Tool execution (`enable_tool_execution`) moves from "off by default" toward "on, but every
  execution is approval-gated" — a policy change to record explicitly when IX-D ships.

## Sequencing

Do not begin IX-D implementation until: (1) IX-C approvals pass an on-device test on both platforms,
and (2) a command risk-classification model is agreed. See
[`docs/architecture/epoch-ix-d-command-console.md`](../architecture/epoch-ix-d-command-console.md).

Both were met before the build started: (1) iOS approvals device-validated 2026-08-07, Android
2026-08-17 (Moto G15 Power, fingerprint — Approve → BiometricPrompt → `approved`, Deny → `rejected`);
(2) the risk classification is the registry below, agreed with the operator as *direct / approval /
forbidden* with the risk classes *low / medium / high / forbidden*.

## Recorded policy shift (2026-08-17)

The Consequences above required an explicit record when tool execution moved from "off by default"
toward "on, but approval-gated". This is that record.

- **New setting `COMMAND_EXECUTION` (default `true`).** Approval-gated *commands* execute after — and
  only after — an operator approval that carries a **biometric confirmation**. This is on by default
  because every execution on this path has just passed a device biometric; there is nothing left to
  gate on.
- **`ENABLE_TOOL_EXECUTION` (default `false`) is unchanged.** It still governs the *chat-triggered*
  tool path, where a request originates from a model turn rather than from an operator's hand. The two
  are deliberately separate switches: the console path is operator-initiated + biometric-confirmed;
  the chat path is model-initiated and stays off until it earns the same trust.
- **What "biometric confirmation" means mechanically:** `approve_request(..., confirmation=)` now
  records *how* an approval was confirmed. Only the mobile approve route
  (`POST /mobile/approvals/{id}/approve`, which already requires the client's `confirmed` biometric
  flag) passes `"biometric"`. An approval recorded by any other channel — including the desktop
  `/system` approve endpoint — is stored but **does not release a command**; the command stays
  `awaiting_approval` with a note saying so. This is the ADR's "desktop cannot self-approve a
  sensitive action", enforced in the executor rather than the UI.
- **Every command is written to `backend/data/command_log.json`** with name, risk, gate, requester,
  channel, linked tool request + approval ids, status, and outcome — including refused (forbidden),
  denied, expired, and failed attempts. Refusals are recorded, not silently dropped.

## Implementation (slice 1, 2026-08-17)

Exactly the "first concrete step" from the design sketch — three commands, one per gate, the gated
path proven end-to-end on hardware before broadening:

| Command | Risk | Gate | What happens |
|---|---|---|---|
| `new_conversation` | low | direct | executes now via the runtime's own `create_conversation`; recorded |
| `run_backend_health_check` | medium | approval | becomes an IX-C `backend_health_check` tool request + approval; executes only on biometric approval |
| `change_conversational_routing` | forbidden | forbidden | refused with 403; the refusal is recorded (Model Lock / output fidelity) |

- **Registry:** `backend/services/command_registry.py` — the authority; self-validates at import
  (forbidden ⇒ forbidden risk; approval ⇒ maps to a registered bounded tool; direct ⇒ low risk only).
- **Console service:** `backend/services/command_console.py` — initiate, approval/denial callbacks,
  gated executor, command log.
- **Routes:** mobile `GET /mobile/commands`, `POST /mobile/commands/{name}`,
  `GET /mobile/commands/history`; desktop `GET/POST /system/commands…` (desktop may initiate; gated
  commands wait for a mobile biometric). Approve/deny responses now include the affected `command`.
- **Android Bridge Zero:** new **Commands** tab (registry rendered as cards — RUN / REQUEST /
  greyed FORBIDDEN — plus a history list); approval-gated commands complete in the Approvals tab
  behind the biometric.
- **Tests:** `backend/tests/test_command_console.py` (9) — one command per gate, registry rendered
  not defined, direct executes + logged, forbidden refused + recorded, gated path end-to-end with a
  biometric approval, mobile approve without the biometric flag rejected, deny discards, the
  `COMMAND_EXECUTION` switch honoured, desktop can initiate but gated commands wait for mobile.
- **On-device validation (2026-08-17, Moto G15 Power, Android 0.5.0 debug build over `adb reverse`):**
  Commands tab → REQUEST "Run backend health check" → Approvals → Approve → fingerprint → history
  row **EXECUTED**; backend shows the tool request `completed`, the approval `approved` with
  `confirmation: biometric`, and a real `backend_health_check` result. Three such executions are
  recorded in `command_log.json` — the runtime's first operator-initiated, biometric-gated actions.
  Two UI defects found on-device were fixed in the same slice (the "approval created" notice was not
  visible; the bottom bar wrapped at six tabs) and re-confirmed by the operator.

Not in slice 1: iOS Commands tab (slice 2 — needs the CI build + sideload cycle), a desktop Bridge
Zero Commands panel (the `/system/commands` endpoints exist; the UI does not), and any command beyond
the three above.

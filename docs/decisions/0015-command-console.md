# 0015 — Command Console (Epoch IX-D)

**Status:** Proposed
**Date:** 2026-08-07
**Depends on:** IX-C approval signals being authoritative and **device-validated** (ADR
[`0014-operator-approvals.md`](0014-operator-approvals.md)).

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

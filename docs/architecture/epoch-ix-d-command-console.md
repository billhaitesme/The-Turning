# Epoch IX-D — Command Console (design sketch)

**Status:** Proposed. Build gated on IX-C approvals being device-validated.
See ADR [`0015-command-console.md`](../decisions/0015-command-console.md).

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

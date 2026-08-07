# 0014 — Operator Approvals over Mobile

**Status:** Accepted (approval flow) · Proposed (push delivery — see below)
**Date:** 2026-08-07
**Epoch:** IX-C — Operator Actions

## Context

Epoch IX-C is "Operator Actions": the runtime must be able to request authorization for a gated
action and have a human operator approve or deny it from their phone, with a short-lived challenge
and a biometric confirmation. The deterministic runtime already has the action-gate machinery:
`services/tool_approval.py` (`create_approval_request` with a TTL/`expires_at`, `approve_request`,
`reject_request`, `expire_approvals`), and biometric usage is already declared on both clients
(`NSFaceIDUsageDescription`, `USE_BIOMETRIC`). What was missing was an operator-facing surface.

## Decision

Add a mobile operator-approval API that **surfaces the existing approval engine** rather than
creating a second one:

- `GET /api/mobile/v1/approvals` — pending requests joined to their still-pending approval
  challenges. Enforces the short-lived window (`expire_approvals`) before returning.
- `POST /api/mobile/v1/approvals/{request_id}/approve` — requires `{"confirmed": true}`, the
  client's assertion that a device biometric authorized the action; records `approved_by:
  "operator"` through `approve_request`.
- `POST /api/mobile/v1/approvals/{request_id}/deny` — `reject_request`.

All under the existing mobile bearer auth. The biometric gate is enforced **client-side** (Face ID /
BiometricPrompt) before the confirmed call; the backend records that an explicit, confirmed operator
action authorized the request. Expired challenges cannot be approved.

## Reason and rejected alternatives

- **Rejected: a new approval store/authority.** The runtime already owns approvals; a second store
  would violate the single-authority principle (as with memory and model control). We surface, not
  duplicate.
- **Rejected: server-side biometric.** Biometrics never leave the device. The operator confirms
  locally; the API records the confirmed decision. This is an assertion, not cryptographic proof —
  adequate for a trusted operator console, and the short TTL bounds the risk.

## Consequences

- The approval flow is fully functional and testable over the existing polling/SSE — the operator
  opens the console, sees pending approvals, and decides. No push required for it to work.
- Tool execution remains disabled by default (`enable_tool_execution=false`); the approval surface
  is live regardless, so approvals can be exercised without executing anything.

## Push delivery — Proposed, infra-blocked

Waking the operator when the app is backgrounded needs **APNs** (a paid Apple Developer account +
push entitlement) and **FCM/Firebase** for Android. Neither can be provisioned or tested in the
current environment (free Apple ID cannot do push). Design intent:

- A device-token registration endpoint (`POST /api/mobile/v1/push/register`), stored per operator.
- On a new pending approval, dispatch a notification via APNs/FCM.

This is deferred until the accounts exist. The approval flow above does not depend on it.

## Migration / rollback

Additive endpoints over an existing engine; removing them leaves the runtime unchanged. No schema
change to the approval store.

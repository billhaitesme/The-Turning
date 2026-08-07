# Tool Execution Lifecycle

The Epoch VIII tool framework keeps execution bounded and observable.

## Lifecycle

1. A request is created with a specific tool name, arguments, and session context.
2. The registry resolves a single explicit adapter for that tool.
3. The request is validated against the tool descriptor and input schema.
4. A request-bound approval is created.
5. The approval is explicitly approved or rejected.
6. The executor runs only if the request, tool, scope, and approval all validate.
7. The adapter returns a structured tool result envelope.
8. The approval is consumed after the execution attempt.
9. The result is converted into evidence candidates only through the evidence bridge.

## Rules

- Tools cannot execute from casual chat.
- Execution is disabled by default.
- Dry-run is allowed only when the tool explicitly supports it.
- Approved requests are not reusable.
- Critical tools are out of scope for Epoch VIII.
- Evidence remains authoritative and separate from execution output.

## Boundaries

- Planning may propose actions.
- Deliberation may recommend actions.
- Approval may authorize actions.
- Tools may execute only bounded actions.
- Evidence records what actually happened.

## Trusted Diagnostic Execution

The trusted localhost health-check adapter is the first bounded tool to close the full loop.

1. A chat request may create a request-bound approval record for `backend_health_check`.
2. Confirmation must be explicit before execution is allowed.
3. The adapter may only check localhost using the configured port and bounded candidate paths.
4. The result is recorded as structured execution history.
5. Verified health evidence is derived only from trusted adapter output.
6. Endpoint mismatch keeps backend health unknown and prevents false verification.
7. Reasoning is refreshed after evidence ingestion so the cognition loop sees the new truth.

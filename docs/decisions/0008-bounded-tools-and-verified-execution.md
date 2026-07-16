# ADR 0008 - Bounded Tools and Verified Execution

Status: Accepted

Context:
OMEGA-ARC can now reason, plan, deliberate, and record approvals, but it cannot yet interact with its environment through trusted adapters.

Decision:
Introduce a bounded tool framework with explicit schemas, approval-bound requests, narrow adapters, structured results, and evidence conversion.

Execution remains disabled by default.

Tool calls must be:
- explicit
- scoped
- approved
- inspectable
- non-reusable
- evidence-producing

Consequences:
- safer path toward environment interaction
- clear separation between planning and execution
- deterministic audit trail
- additional state and validation complexity

Future work:
- real backend health-check adapter
- Git status adapter
- filesystem inspection adapter
- local model status adapter
- test runner adapter
- approval UI
- execution history viewer

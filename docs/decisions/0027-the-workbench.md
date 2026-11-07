# 0027 — The Workbench: OMEGA Writes (Epoch XIII-E)

**Status:** Accepted (design); slice 1 built 2026-11-06
**Date:** 2026-11-06
**Operator direction (2026-11-06):** *"I need you to be able to write code, so I can allow you to
make changes to yourself, i.e. find and integrate new tools to improve capabilities."* Changes
happen **upon user approval**.
**Builds on:** ADR [`0026`](0026-the-agent-loop.md) (agent loop, breaker, Mind Ladder, Toolwright),
ADR [`0014`](0014-operator-approvals.md) (biometric approvals), ADR
[`0024`](0024-consolidation-gate.md) (candidate → verified → activated), and the self-modification
protocol in `AGENTS.md`: **proposal, backup, patch, syntax check, tests, health check, review,
promote or rollback.**

## Context

OMEGA can call registered commands and gain new read-only tools through the Toolwright, but only
from a stocked catalog someone else wrote. It cannot author a tool, and it has no path at all to
change its own code. Asked about this on 2026-11-06 it claimed "I can write and execute code"; the
runtime now states the truth (`describe_self.code`), and this ADR is the path to making more of it
true without giving a model the keys to its own runtime.

Two facts shape the design:

1. **The writer is weak.** The everyday seat is an 8B model. It writes plausible text, and code
   from it into its own runtime would be shaky. Authorship must be checked by machines, not trusted.
2. **The operator is the authority.** Nothing becomes live without the operator's biometric, and
   every step is recorded, reversible, and visible on a console.

## Decision

Two slices, the narrow one first.

### Slice 1 — Authored tools (built)

OMEGA may **author** a Toolwright candidate: a declarative spec tool (`author_tool`), typically after
reading an API's documentation with `web_search` / `web_fetch`. The spec contract is unchanged and
is the safety boundary: GET-only, https, public host, JSON, placeholders must match declared
parameters, a fixture is required. An authored candidate enters the existing pipeline as a
capability request with provenance `authored` (never `catalog`):

`author_tool` (contract-validated; a rejection returns the plain reason so OMEGA can fix it)
→ **PREPARE** by the operator (quarantine + one live, breaker-gated, logged fixture call)
→ **INDUCT** by the operator's biometric → a registered, gated command.

The model never grades its own spec; the fixture call and the operator do. Authoring is not
having: an authored tool does nothing until inducted.

### Slice 2 — Code proposals (designed, next)

For changes that are code, the **Workbench**:

1. **Proposal.** OMEGA files a change request (what and why), recorded and visible.
2. **Draft.** The patch is drafted by the strongest available rung (the frontier planner behind
   the breaker; the local deep rung as fallback), as search/replace edits against named files,
   limited to an allowlist of paths. Never secrets, data stores, or the gates themselves
   (approval, breaker, registry rules, this Workbench).
3. **Backup + patch.** Applied only inside an isolated git worktree on its own branch; the live
   checkout is never touched.
4. **Syntax check + tests.** The full backend suite runs in the worktree. Red = rejected, with
   the output kept for the record.
5. **Health check.** The worktree backend boots on a spare port and answers.
6. **Review.** The console shows the diff, the test result and the health result.
7. **Promote or rollback.** The operator's biometric merges the branch into the local main as one
   commit; rollback is a single revert. The runtime never pushes.

## Consequences

- OMEGA can grow its own senses (slice 1) the day this lands, within the spec contract.
- The 8B's weakness is contained: everything it writes is either declarative and machine-checked
  (slice 1) or drafted by a stronger rung and tested before a human reads it (slice 2).
- Slice 2 costs a full test run per proposal on the operator's PC (~90 s); it runs only when the
  operator asks a proposal to be tested.

## Rejected alternatives

- **Free-form execution / a code-running tool.** No sandbox on this host is strong enough to let
  a model run arbitrary code against the operator's machine; the bounded-tool doctrine (ADR 0008)
  stands.
- **Editing the live checkout, even with approval.** A bad patch to the runtime would take down
  the very console used to approve the rollback. Changes are made in a worktree, then merged.

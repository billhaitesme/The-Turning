# OMEGA-ARC Acceptance Scenarios

## Purpose

These scenarios define expected system behavior across multiple subsystems.

They are intended to catch regressions that ordinary unit tests may miss.

They validate:

- identity behavior
- uncertainty handling
- evidence provenance
- configuration versus runtime state
- cognition and goal tracking
- conflict handling
- curiosity gating
- general question isolation
- reasoning summaries

## How to Use

For each scenario:

1. Start the backend from the current branch.
2. Start a new conversation unless the scenario says otherwise.
3. Send the messages in order.
4. Compare the response against:
- required behavior
- forbidden behavior
- expected internal state
5. Record the result as:
- PASS
- FAIL
- PARTIAL

## Acceptance Standard

A scenario passes only if:

- all required behaviors occur
- no forbidden behaviors occur
- the internal state matches the expected outcome
- unrelated subsystems remain unaffected

## Test Environment

Use this checklist for each run:

- [ ] Backend URL:
- [ ] Frontend URL:
- [ ] Chat model name:
- [ ] Reasoning model name:
- [ ] Vision model name:
- [ ] Branch:
- [ ] Commit hash:
- [ ] Test date:
- [ ] Tester:

## Scenario Index

- [001 — Identity Correction](docs/acceptance/001_identity_correction.md)
- [002 — Unknown Identity Remains Unknown](docs/acceptance/002_unknown_identity.md)
- [003 — Project Tracking](docs/acceptance/003_project_tracking.md)
- [004 — Configuration Does Not Imply Health](docs/acceptance/004_backend_configuration.md)
- [005 — Evidence Conflict and Supersession](docs/acceptance/005_evidence_conflict.md)
- [006 — Goal Blocking](docs/acceptance/006_goal_blocking.md)
- [007 — Reasoning Summary](docs/acceptance/007_reasoning_summary.md)
- [008 — Unknown Versus Verified](docs/acceptance/008_unknown_vs_verified.md)
- [009 — Curiosity Gating](docs/acceptance/009_curiosity_gating.md)
- [010 — General Question Isolation](docs/acceptance/010_general_qa_isolation.md)

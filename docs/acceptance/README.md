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
- reasoning explanation transparency
- plan persistence and lifecycle updates
- deterministic next-action selection
- decision provenance and explanation
- deliberative recommendation and approval workflow

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
- [011 — Reasoning Explanation Transparency](docs/acceptance/011_reasoning_explanation.md)
- [012 — Plan Persistence](docs/acceptance/012_plan_persistence.md)
- [013 — Plan Generation](docs/acceptance/013_plan_generation.md)
- [014 — Dependency Resolution](docs/acceptance/014_dependency_resolution.md)
- [015 — Plan Revision](docs/acceptance/015_plan_revision.md)
- [016 — Blocked Plan](docs/acceptance/016_blocked_plan.md)
- [017 — Multiple Goals](docs/acceptance/017_multiple_goals.md)
- [018 — Completed Plan](docs/acceptance/018_completed_plan.md)
- [019 — Conflicting Plans](docs/acceptance/019_conflicting_plans.md)
- [020 — Next Best Action](docs/acceptance/020_next_best_action.md)
- [021 — Reasoning to Plan](docs/acceptance/021_reasoning_to_plan.md)
- [022 — Plan Isolation](docs/acceptance/022_plan_isolation.md)
- [023 — Decision Provenance](docs/acceptance/023_decision_provenance.md)
- [024 — Plan Comparison](docs/acceptance/024_plan_comparison.md)
- [025 — Plan Approval](docs/acceptance/025_plan_approval.md)
- [026 — Assumption Tracking](docs/acceptance/026_assumption_tracking.md)
- [027 — Risk Analysis](docs/acceptance/027_risk_analysis.md)
- [028 — Alternative Plan](docs/acceptance/028_alternative_plan.md)
- [029 — Trade-Off Explanation](docs/acceptance/029_tradeoff_explanation.md)
- [030 — Decision Matrix](docs/acceptance/030_decision_matrix.md)
- [031 — Decision Superseded](docs/acceptance/031_decision_superseded.md)
- [032 — Assumption Invalidated](docs/acceptance/032_assumption_invalidated.md)
- [033 — Planning Without Execution](docs/acceptance/033_planning_without_execution.md)

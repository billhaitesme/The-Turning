# Planning Engine

## Objective

Epoch VI introduces deterministic planning built from goals, evidence, and reasoning.

Planning proposes actions.

Planning never executes actions.

## Position In Pipeline

Conversation

-> Identity

-> Evidence

-> Reasoning

-> Planning

-> Response

Planning is optional and bypassed for normal Q&A.

## Scope Boundaries

Planning does not modify:

- identity
- evidence
- knowledge
- goals

Planning only emits structured proposals and blockers.

## Domain Models

`PlanStep` captures ordered, deterministic, proposal-only work units.

`Plan` captures goal-level planning status, blockers, confidence, and graph shape.

`PlanDependency` captures dependency requirements and whether each is currently satisfied by evidence.

## Deterministic Rules

`build_plan(goals, evidence, reasoning)` applies the same sequence each run:

1. collect active goals
2. evaluate dependency readiness using evidence and resolved beliefs
3. mark missing or non-verified dependencies as blockers
4. produce ordered pending and blocked steps
5. remove completed steps from output
6. assign deterministic confidence
7. emit graph edges for plan visualization

## Dependency Example

For Vision Routing, dependencies flow as:

1. vision_model_selected
2. vision_model_loaded
3. vision_router_configured
4. vision_routing_verified

If a dependency is missing or only declared/configured, the plan is blocked and explains why.

## Response Shape

Planning responses are rendered using:

- Current Goal
- Current Plan
- Current Blockers
- Confidence

This keeps planning explicit and auditable while preserving execution separation.

## Console Placeholder

`./scripts/omega.ps1 plan` prints:

- Current Goals
- Current Plans
- Current Blockers

No execution is performed.

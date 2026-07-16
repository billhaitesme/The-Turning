# Epoch VI: Planning

## Purpose

Epoch VI turns structured state into explicit, reviewable plans.

Epoch V established the evidence and reasoning foundation:

- identity and cognition extraction
- evidence authority and session isolation
- deterministic summaries
- goal and knowledge tracking
- developer tooling and acceptance coverage

Epoch VI should build on that base without weakening evidence rules or blurring the line between:

- user-declared state
- verified runtime evidence
- suggested actions
- executed actions

## Problem Statement

The current system can describe what it knows and what remains uncertain, but it does not yet produce a durable planning model that can:

- break goals into ordered steps
- explain why a step is next
- identify blockers and prerequisites
- distinguish proposed work from executed work
- adapt plans when evidence changes

This is the gap between reasoning about state and acting on goals.

## Epoch VI Objectives

Epoch VI is complete when OMEGA-ARC can:

1. Represent plans as structured objects rather than free-text suggestions.
2. Generate next-best actions from goals, dependencies, and evidence.
3. Track whether a plan step is proposed, ready, blocked, in progress, completed, or invalidated.
4. Re-plan safely when upstream evidence or configuration changes.
5. Keep plan generation deterministic enough to test through acceptance scenarios.

## Scope

In scope:

- planning data model
- plan generation service
- blocker and prerequisite analysis
- plan rendering for chat summaries and direct planning prompts
- deterministic planning tests
- acceptance scenarios for planning behavior

Out of scope for the first Epoch VI slice:

- automatic execution of plan steps
- implicit tool invocation from ordinary chat
- long-running autonomous agents
- background health-check execution from chat alone
- multimodal routing or vision execution itself

## Primary Workstreams

### 1. Planning Model

Introduce a planning representation with at least:

- plan id
- goal id
- plan title
- steps
- step status
- prerequisites
- blockers
- supporting evidence keys
- created_at and updated_at

Suggested step states:

- proposed
- ready
- blocked
- in_progress
- completed
- invalidated

### 2. Planning Engine

Add a deterministic service that consumes:

- active goals
- evidence store
- reasoning result
- knowledge graph where relevant

And produces:

- current plan outline
- next-best actions
- blocker explanations
- invalidation or re-plan signals

### 3. Planning Prompts and Rendering

Add planning-aware rendering for prompts such as:

- What is the plan?
- What should I do next?
- Why is this goal blocked?
- What is the next best action for vision routing?

Responses should remain evidence-labeled and must not pretend a step was executed unless verified execution evidence exists.

### 4. Trusted Execution Boundary

Define the boundary between:

- planning a health check
- requesting a trusted adapter run it
- ingesting a trusted structured result

Epoch VI should support planning around execution without conflating planning with execution.

### 5. Acceptance Coverage

Add planning acceptance scenarios that verify:

- plan generation from explicit goals
- blocker-aware next actions
- re-planning after evidence changes
- no false execution claims
- no hidden state carryover across fresh sessions

## Suggested Implementation Order

### Slice 1: Planning Schema

Deliverables:

- planning store format
- step and blocker schema
- minimal persistence conventions

Exit criteria:

- plans can be created, loaded, and updated deterministically

### Slice 2: Next-Action Reasoning

Deliverables:

- next-best-action selection
- blocker grouping
- dependency-based ordering

Exit criteria:

- the system can explain why a step is next or blocked

### Slice 3: Re-Planning and Invalidation

Deliverables:

- plan invalidation from evidence changes
- re-plan triggers
- changed-prerequisite handling

Exit criteria:

- stale plans do not survive authoritative evidence changes unchallenged

### Slice 4: User-Facing Planning Views

Deliverables:

- plan summary renderer
- direct planning response path
- developer-facing inspection hooks

Exit criteria:

- planning output is deterministic, testable, and readable

## Commit Structure

Suggested commit sequence for Epoch VI:

1. `feat(planning): add plan model and persistence primitives`
2. `feat(planning): add blocker-aware planning engine`
3. `feat(planning): add next-action rendering and direct plan responses`
4. `test(planning): add engine and acceptance coverage`
5. `docs(planning): document planning lifecycle and acceptance semantics`

## Candidate Acceptance Scenarios

Suggested new acceptance scenarios:

- 012 plan generation from active goal
- 013 next-best action for blocked goal
- 014 re-plan after backend endpoint change
- 015 planning does not imply execution
- 016 trusted execution result updates plan state

## Risks

- Turning recommendations into implicit execution claims.
- Letting declared evidence satisfy execution-completion semantics.
- Generating plans that depend on hidden session residue.
- Allowing plan text to drift away from structured internal state.

## Definition Of Done

Epoch VI is done when:

- plans are structured and persisted intentionally
- next actions are evidence-backed
- blockers and prerequisites are explicit
- plan state changes are testable and deterministic
- execution remains separated from planning authority
- acceptance coverage proves planning does not invent completion
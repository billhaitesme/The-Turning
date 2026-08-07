# Roadmap

> This is the origin architecture roadmap, kept for narrative continuity and updated to the real epoch
> names. The **living** delivery roadmap is [`../../ROADMAP.md`](../../ROADMAP.md); current status is in
> [`../../PROJECT_STATUS.md`](../../PROJECT_STATUS.md).

## Foundational Era

### Genesis
Purpose: establish the basic application shell and core principles.

Deliverables:
- conversation entry point
- stable prompt and response behavior
- initial persistence conventions

Completion criteria:
- the system can run and respond coherently

### Epoch II: Identity
Purpose: make identity explicit and safe.

Deliverables:
- identity state
- user profile handling
- restrictions on unsupported inference

Completion criteria:
- identity facts remain explicit and non-speculative

### Epoch III: Cognition
Purpose: extract structured candidates from conversation.

Deliverables:
- cognition services
- goal and knowledge candidate extraction
- deterministic conversation analysis

Completion criteria:
- conversation produces structured, testable candidates

### Epoch IV: Evidence
Purpose: replace implicit certainty with explicit evidence.

Deliverables:
- evidence engine
- provenance and dependency tracking
- evidence-aware prompts and awareness

Completion criteria:
- configuration, inference, observation, and verification are distinct

## Systems Era

### Epoch V: Reasoning
Purpose: reason over structured evidence.

Deliverables:
- reasoning engine
- contradiction detection
- evidence-backed decision support

Completion criteria:
- the system can explain what it believes and why

### Epoch VI: Planning
Purpose: turn goals and evidence into action sequences.

Deliverables:
- persistent planning layer
- next-best-action reasoning
- dependency-aware, proposal-only plans and decision provenance

Reference:
- [Epoch VI Planning](epoch6_planning.md)

Completion criteria:
- the system can support goal-directed action without executing it

### Epoch VII: Deliberation
Purpose: choose deliberately among competing plans.

Deliverables:
- deterministic comparison of candidate plans
- risk analysis and assumption tracking
- an explicit approval lifecycle

Completion criteria:
- a recommendation is reproducible and its rationale is inspectable

### Epoch VIII: Trusted Diagnostics (Bounded Tools and Verified Execution)
Purpose: let the system interact with its environment in bounded, auditable ways.

Deliverables:
- explicit tool schemas and approval-bound, scoped tool requests
- narrow adapters (health check, git status, filesystem inspection, model status, test runner)
- tool results converted to evidence with a deterministic audit trail

Completion criteria:
- the environment can be observed through narrow, approval-gated adapters; execution stays off by default

## Operations Era

### Epoch IX: Runtime Operations — "The Runtime Becomes Visible"
Purpose: make the single Core Runtime observable and operable.

Deliverables:
- authenticated native mobile operator consoles (iOS, Android) and desktop Bridge Zero (Mission Control)
- authoritative RuntimeStore, typed SSE events, measured telemetry, and an Operations Dashboard
- Model Lock and a deterministic runtime boundary
- operator actions (IX-C): model selector, new conversation, and approvals with on-device biometric

Completion criteria:
- the runtime's real state is visible and operable, and operator actions flow through explicit gates

## Future

### Epoch X: Memory
Durable, scoped, benchmarked long-term memory — the substrate the learning pillar depends on.

### Tutelage and Learning (proposed)
A runtime-driven, review-gated study loop with measured recall, sequenced after Memory.

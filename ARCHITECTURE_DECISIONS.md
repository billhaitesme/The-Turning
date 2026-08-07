# OMEGA-ARC Architecture Decisions

This living index preserves the reasoning behind OMEGA-ARC’s governing architectural choices. Detailed historical records remain in [`docs/decisions`](docs/decisions). The `ADR-IX-*` identifiers below avoid colliding with existing historical ADR numbers.

## ADR-IX-001 — Model Lock

**Status:** Accepted

**Decision:** The conversational model never changes automatically. Only an explicit operator action may change the active conversational model.

**Reason:** Operator control, response provenance, and input fidelity are more important than opportunistic routing. Silent substitution makes behavior difficult to explain and trust.

**Consequences:**

- Topic-based conversational routing is prohibited.
- Provider substitution is detected and rejected.
- Automatic fallback is disabled unless explicitly enabled, and Direct Model mode never falls back.
- Runtime telemetry records requested, selected, and actual models.

**Related records:** [`model-lock.md`](docs/architecture/model-lock.md), [`0011-model-independence.md`](docs/decisions/0011-model-independence.md), [`0012-direct-model-mode.md`](docs/decisions/0012-direct-model-mode.md)

## ADR-IX-002 — Deterministic Runtime Boundary

**Status:** Accepted

**Decision:** Language models reason and converse. The runtime owns deterministic state transitions, validation, tool orchestration, approval gates, evidence, persistence, and execution policy.

**Reason:** Separating probabilistic language generation from authoritative execution keeps the system testable, auditable, and reversible.

**Consequences:**

- Generated language cannot silently mutate runtime authority.
- Tool calls remain bounded, typed, approved where required, and evidence-backed.
- Planning and deliberation remain proposal-oriented until execution policy explicitly permits action.

**Related records:** [`0005-reasoning-engine.md`](docs/decisions/0005-reasoning-engine.md), [`0008-bounded-tools-and-verified-execution.md`](docs/decisions/0008-bounded-tools-and-verified-execution.md)

## ADR-IX-003 — Bridge Zero Is an Operator Console

**Status:** Accepted

**Decision:** Desktop Bridge Zero is Mission Control. Native mobile applications are synchronized operator consoles for the same Core Runtime, not independent chat clients.

**Reason:** A single runtime authority preserves model selection, memory, conversation continuity, policy, and observable state across every interface.

**Consequences:**

- Mobile delegates inference and streaming to the Core Runtime.
- Mobile does not manufacture activity, substitute models, or rewrite responses.
- Conversation history is shared across desktop and native clients.
- Authentication and compatibility gates fail closed.

**Related record:** [`bridge-zero-mobile.md`](docs/architecture/bridge-zero-mobile.md)

## ADR-IX-004 — Authoritative Runtime Visibility

**Status:** Accepted

**Decision:** Operational surfaces display measured or persisted runtime state through RuntimeStore and typed events. Missing signals are shown as unavailable, never simulated.

**Reason:** An operations console is useful only when every displayed signal can be traced to an authoritative source.

**Consequences:**

- CPU and memory come from measured host telemetry.
- Session, stream, latency, client, tool-queue, and Chronicle values come from observed or persisted runtime state.
- Typed SSE events and native event buses carry state changes without fabricated animation.
- IX-B cannot be declared complete until native-device behavior is validated.

## ADR-IX-005 — Unified Epoch and Version Identity

**Status:** Accepted

**Decision:** All active components report Epoch IX / Version 0.2.x, with 0.2.0 as the current release. The mobile API major remains independently versioned as `1`.

**Reason:** A shared identity prevents documentation, builds, compatibility gates, and releases from describing different system states.

**Consequences:**

- [`versioning.md`](docs/architecture/versioning.md) is the release-identity authority.
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) is the current operational-status authority.
- Historical documents may retain earlier epoch names when clearly historical.
- Milestone tags use the documented `epoch-<roman>-<milestone>` convention.

## Adding or changing a decision

1. Add a detailed ADR under `docs/decisions` when context, alternatives, or migration consequences require a durable record.
2. Add or update the concise governing decision in this index.
3. Link the decision from affected architecture documentation and tests.
4. Never rewrite an accepted historical decision to hide a change; supersede it explicitly.

# 0026 — The Agent Loop and the Breaker (Epoch XIII)

**Status:** Accepted (design) — operator direction 2026-11-05
**Date:** 2026-11-04 (proposed) / 2026-11-05 (accepted)
**Operator principle (recorded 2026-11-05):** *identity is local and continuous; brainpower is
unbounded — when the runtime needs more brain power it is allowed it; it is not restrained by
where it grew up.* Seat choice — including uncensored/abliterated weights — is the operator's,
and the architecture is model-agnostic by design.
**Builds on:** ADR [`0008`](0008-bounded-tools-and-verified-execution.md) (bounded tools), ADR
[`0011`](0011-model-independence.md) (Model Lock), ADR [`0014`](0014-operator-approvals.md)
(biometric approvals), ADR [`0015`](0015-command-console.md) (command registry; chat-path execution
deliberately frozen), ADR [`0024`](0024-consolidation-gate.md) (candidate → verified → activated),
Constitution article 7 (*tools, files, and network access only through explicit permissions*).

## Context

The operator asked (2026-11-04) to interact with the runtime the way one interacts with a frontier
agent: ask in chat, and the runtime works out what it needs, finds it, and does it — including
reading the internet — under operator discretion. Today the chat seat has no execution path at all
(ADR 0015 froze it), tools live only behind the consoles' Commands surface, and the model answers
capability questions with bare-model boilerplate ("I need integrated tools") that is false about
the runtime it inhabits.

The frontier agents the operator compares against are architecturally the same pattern this
repository already enforces elsewhere: a model that *emits* structured tool calls and a harness
that *validates and executes* them behind permission gates. The gap is not doctrine; it is that the
chat seat was never given the loop.

## Decision

1. **The loop.** The chat seat gains an agent loop: a natively tool-calling **agent seat**
   (Model-Lock-registered, bake-off-selected — the current 12B voice cannot call tools) emits
   structured tool calls; the deterministic runtime resolves each against the **command registry
   and bounded-tool contracts only**. Side-effect-free tools execute direct; side-effecting tools
   raise the standard IX-C biometric approval; anything else is refused. Results return to the
   model's context; hops and result sizes are bounded; every hop is recorded with `channel: chat`.
   This supersedes ADR 0015's chat-path freeze **only through the loop** — free-form execution
   remains nonexistent.
2. **The breaker.** Network reads (`web_search`, `web_fetch` — read-only, size-capped, no writes)
   execute only while a standing **operator breaker** is on. The breaker is off by default, flipped
   only by explicit recorded operator action, visible on every console; every search and fetch is
   logged. Fetched text enters context as data, never instructions; gates do not relax for it.
3. **Deeper thought — the Mind Ladder.** Hard tasks escalate up a ladder of registered seats, every
   rung Model-Lock-selected, every escalation recorded: **rung 1**, the everyday seat's own
   deep-reasoning gear (a hybrid-reasoning model is a seat-selection criterion — same model, same
   context, more thought; lead candidate: abliterated Qwen3-8B, resident on the 8 GB card);
   **rung 2**, a larger local model trading speed for depth (lead candidate: Qwen3-30B-A3B MoE in
   system RAM; the rung any future local hardware upgrades); **rung 3**, a cloud seat behind the
   breaker (free tiers suffice for planning volume) — the only rung where a provider's own
   restrictions and data policies apply, which is why rungs 1–2 stay local. Plans land in the
   existing plan store (ADR 0006). Identity, memory, and every gate stay on local disk regardless
   of which rung is thinking.
4. **The Toolwright.** A capability gap becomes a **capability request** (operator-visible). A
   candidate tool is found by retrieval (stocked catalog first, open web second), fetched **by the
   runtime** into quarantine, verified by deterministic contract tests, and inducted into the
   registry only on biometric approval — risk-classed and gated like any hand-written tool. The
   model never grades its own find; denial deletes the quarantine. (ADR 0024's discipline,
   generalized from adapters to tools.)

## Rejected alternatives

- **Free-form execution (shell/code access for the model).** Maximal violation of the deterministic
  runtime's authority; unreviewable; unnecessary — the registry can grow to cover real needs.
- **Per-call operator approval for network reads.** Makes the sense unusable; the breaker plus a
  complete log is the honest reading of "at my discretion" (the operator holds the master switch,
  not a clicker).
- **Autonomous tool induction (no approval).** Breaks the Covenant's continuity test (changes the
  runtime's capability surface without a reviewable, reversible operator decision).
- **A standing multi-seat pipeline (voice seat + hands seat + planner seat).** Handoffs between
  models are where seamlessness dies — context loss, doubled latency, intent drift. One
  tool-capable hybrid-reasoning seat is the primary design; extra seats only on measured need
  (ADR 0011 keeps every seat swappable either way).
- **Cloud seat by default.** Private rooms must never leave the machine; any future cloud seat is a
  separate explicit operator decision with that hard exclusion, never a default.

## Consequences

- The chat seat becomes a fourth surface over the same registry — the consoles' governance,
  conversational. Capability grows one risk-classed tool at a time, now proposable by the runtime
  itself but only ever *inducted* by the operator.
- The bare-model "I can't" boilerplate becomes taught-correctable falsehood (curriculum lesson
  *Its Own Hands*).
- New recorded trails: loop hops, breaker flips, fetch log, planner handoffs, capability requests,
  quarantine verdicts — the agency curve is observable, like the identity curve before it.
- Epoch XIII milestones: XIII-A The Hands (loop over existing commands), XIII-B The Senses
  (breaker + read tools), XIII-C Deeper Thought (seat bake-off + recorded escalation), XIII-D The
  Toolwright (first tool acquired end-to-end).

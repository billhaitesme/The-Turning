# 0020 — Scope assignment: the conversation carries the room (Epoch X)

**Status:** Accepted
**Date:** 2026-08-07
**Builds on:** ADR [`0019-scoped-retrieval.md`](0019-scoped-retrieval.md), which added rooms and
deferred exactly this question: *who assigns a memory's scope?*

## Context

ADR 0019 gave memories an optional `scope` ("room") and let recall search within one — but nothing in
production assigned scopes. The candidates for who names the room:

1. **The operator / caller, explicitly** — deterministic, auditable, zero magic.
2. **A topic classifier** — automatic, but non-deterministic in effect: silent misfiles into wrong
   rooms would be invisible corruption of the child's memory.
3. **Nothing (status quo)** — rooms exist but stay empty.

There is also a semantics gap: if recall searched *only* the room, room-agnostic facts — the
operator's preferences, global project truths — would vanish inside every scoped conversation.

## Decision

**The conversation carries the room, set only by explicit action; recall adds the global wing.**

- `conversations` gains a `scope` column. It is set explicitly — at creation
  (`POST /conversations {scope}`) or later (`POST /conversations/{id}/scope {scope}`, `null` clears).
  Scope is **never inferred**; assignment is an operator/API action, deterministic and auditable.
- **Write inheritance:** memories persisted from a conversation (`persist_learning`) inherit the
  conversation's scope. A study session in a room files everything it learns in that room — this is
  the hook the future curriculum uses: *a lesson is a scoped conversation.*
- **Recall = room + global wing:** when recall has a scope, candidates are that room's memories
  **plus unscoped ("global") memories**; other rooms stay excluded. Preferences and other
  room-agnostic facts remain recallable everywhere (`include_global=False` gives strict room-only).
  Unscoped conversations behave exactly as before.

Deterministic, single store, one nullable column on `conversations`, no classifier, no new authority.

### Why not the alternatives

- **Automatic topic classification.** Misfiled memories are silent corruption; a learner whose notes
  land in the wrong room learns wrong. Deferred until there is a measured need and a review surface —
  and even then it should propose, not assign (per the runtime's proposal-only posture).
- **Strict room-only recall as default.** Measured directly: global preferences become unrecallable
  inside a room (the v2 fixture's global queries fail under strict scope). The wing is the fix.
- **Per-message scope.** Finer-grained than any current need; a conversation is the natural session
  unit, and the curriculum will drive sessions.

## Evidence

- Deterministic unit tests (`tests/test_scope_assignment.py`): conversation carries/sets/clears scope;
  `persist_learning` memories inherit the room; scoped recall returns room + global wing and excludes
  the other room; strict mode excludes the wing; the endpoint sets, clears, and 404s.
- Real-embedder benchmark `recall_scoped_v2` (rooms + a global wing; scoped queries for both room
  facts and global preferences): **hit@1 1.000 / recall@3 1.000 / MRR 1.000** — room isolation holds
  (v1's result) *and* global facts remain recallable inside rooms. (Numbers from the run recorded in
  the benchmark README.)

## Consequences

- Rooms are now fillable and lived-in: a scoped conversation files what it learns and recalls its own
  subject plus the global wing. The curriculum's unit of study ("a lesson is a scoped conversation")
  now has a concrete mechanism.
- Assignment stays honest: explicit, deterministic, reversible (clear the scope; memories keep theirs
  and can be re-roomed later by a future review surface).
- Open follow-ons for Epoch X: re-scoping/review surfaces for existing memories, and (only if a
  measured need appears) a proposal-only scope suggester.

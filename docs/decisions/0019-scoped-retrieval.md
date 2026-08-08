# 0019 — Scoped memory retrieval (Epoch X)

**Status:** Accepted — capability added; used per-call, backward compatible when omitted.
**Date:** 2026-08-07
**Credit:** Borrowed from **[MemPalace](https://github.com/MemPalace/mempalace)** (MIT), idea #1 —
its "wings / rooms / drawers" are scoped search (recall *within* a person / project / topic instead of
one flat corpus). Technique adopted; no MemPalace code, no second store.

## Context

`search_memories` recalled across a whole user/conversation as one flat pile. But a growing mind's
memory — the "child" this epoch is building toward — is not one pile; it is organized by *subject*.
Under a curriculum (the future Tutelage epoch), the learner needs to recall *within a topic* — "what's
the deadline **on this project**", "what did we conclude **in this subject**" — where the same words
mean different things in different rooms.

Embeddings cannot solve this. Two facts with identical phrasing and no distinguishing name — "the
deadline is Friday" vs "the deadline is Tuesday" — embed almost identically; the room they belong to
is metadata, not meaning. Only an explicit scope resolves them.

## Decision

Give each memory an optional **`scope`** (a room/topic label), set on write, and let `search_memories`
recall within it:

- `save_memory(..., scope=...)` stores the label; `search_memories(..., scope=...)` restricts recall
  to that room. Omitting `scope` preserves prior behavior exactly (recall across all rooms), so this
  is additive and backward compatible — a new capability invoked when a caller has a room in mind, not
  a global behavior change.
- Deterministic, single store (one new nullable column, migrated in), no LLM, no new authority.
- Composes with the other Epoch X signals (recency/lexical/fuzzy) and the superseded filter — scoping
  narrows the candidate set, the blended score ranks within it.

Coarse rooms already exist implicitly via `kind`; `scope` is the explicit, caller-defined room that a
curriculum or project context will set.

### Why not the alternatives

- **Rely on embeddings / put the room name in the text.** Fails exactly when the text is parallel
  across rooms (the measured case below); brittle and implicit.
- **A separate per-scope index/store.** A second persistence authority — rejected (ADR-IX-002).

## Evidence (recall_scoped_v1, embeddinggemma)

Six memories across two rooms (`project-nova`, `project-orion`) with parallel, name-free facts; each
query names its room, and the same query text in the other room has a different gold. The unscoped
baseline is the same fixture with scope stripped from the queries.

| retrieval | hit@1 | recall@3 | MRR |
|---|---|---|---|
| unscoped (flat) | 0.500 | 1.000 | 0.750 |
| **scoped** | **1.000** | **1.000** | **1.000** |

Scoping **doubles hit@1** and lifts MRR from 0.750 to 1.000 — the flat store conflates the rooms (it
returns the wrong room's fact half the time; here the recency tie-break makes that miss deterministic),
while scoped recall is exact. This is the first Epoch X signal to show a real gain that embeddings
alone cannot achieve. Reproduce:
`python backend/benchmarks/recall_benchmark.py --fixture backend/benchmarks/fixtures/recall_scoped_v1.json`
(and again with `scope` removed from the queries for the baseline).

## Consequences

- Memory can be organized into rooms — the substrate a curriculum-driven learner needs to study and
  recall *by subject*. This is the MemPalace idea that most directly serves the child's memory.
- Backward compatible: unscoped callers are unchanged; scope is opt-in per call.
- Sets up the follow-on: who assigns a memory's scope (operator, conversation context, or a
  deterministic topic classifier) is the next design question — deferred, and does not block this
  capability.

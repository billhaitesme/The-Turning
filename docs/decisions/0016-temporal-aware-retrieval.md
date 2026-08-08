# 0016 — Temporal-aware memory retrieval (Epoch X)

**Status:** Accepted
**Date:** 2026-08-07
**Relates to:** Epoch X — Memory ([`../architecture/epoch-x-memory-and-retrieval.md`](../architecture/epoch-x-memory-and-retrieval.md)); measured by the recall benchmark (`backend/benchmarks/`).

## Context

`search_memories` ranked candidates purely by cosine similarity to the query embedding. The recall
benchmark (Epoch X, slice 1) surfaced one reproducible failure mode: **temporal supersession**. When
a fact is later replaced by a newer fact on the same subject (e.g. "the active model is X" → "the
active model is now Y"), both embed similarly to a query like "which model is used *now*?" Flat cosine
can rank the **superseded** fact first, so the runtime recalls stale state as if current.

This is not a similarity problem — both memories are genuinely relevant — it is an ordering problem
between near-ties. The deterministic runtime boundary (ADR-IX-002) and the single memory store must be
preserved; no second index, no model-side reranker.

## Decision

Add a **bounded recency term** to memory ranking, applied only where it matters — among near-ties.

- For a query's candidate set, normalize `created_at` to `recency_norm ∈ [0, 1]` (oldest → 0,
  newest → 1 across that set).
- Rank by `similarity + MEMORY_RECENCY_WEIGHT * recency_norm`.
- `MEMORY_RECENCY_WEIGHT` is a small, operator-tunable constant (env `MEMORY_RECENCY_WEIGHT`). Because
  the additive term is at most the weight, it can only reorder candidates whose cosine similarities
  differ by less than the weight — i.e. genuine near-ties. Clear matches are unaffected.
- `MEMORY_RECENCY_WEIGHT=0` restores exact pure-similarity behavior (used as the benchmark baseline
  and available as an operator escape hatch).

The change lives entirely inside `search_memories` / `_apply_recency_ranking` in the deterministic
runtime. It is deterministic, records `recency_norm` and `ranking_score` on each result for
transparency, and adds no new store or authority.

### Why not the alternatives

- **Full recency blend (large weight).** Would reorder clear matches and regress non-temporal recall.
  Rejected in favor of a bounded near-tie nudge.
- **Explicit supersession links** (mark memory B as replacing A, hard-drop A). More precise but needs
  a reliable supersession signal and mutates stored relationships; heavier, and deferrable. May layer
  on later if the bounded term proves insufficient — the benchmark will say.
- **Model-side reranker.** Violates the deterministic boundary and the local-first, no-substitution
  posture. Rejected.

## Evidence (recall_v2, embeddinggemma)

Gated on the benchmark: the chosen weight must **raise hit@1** and **not regress recall@3** vs the
`weight=0` baseline. Measured on `recall_v2` (24 memories, 15 queries incl. 4 temporal pairs) with the
real `embeddinggemma` embedder:

| weight | hit@1 | recall@3 | MRR |
|---|---|---|---|
| 0 (baseline) | 0.933 | 1.000 | 0.967 |
| 0.03 | 1.000 | 1.000 | 1.000 |
| **0.05 (chosen)** | **1.000** | **1.000** | **1.000** |

The only baseline miss was a temporal-supersession query (a superseded fact outranking its
replacement); the recency term fixes it with no recall@3 regression. `0.03` is the smallest tested
weight that reaches perfect recall; **0.05** is chosen for a little margin while remaining well below
the cosine gap of a clear match (so clear matches are never reordered). Reproduce:
`MEMORY_RECENCY_WEIGHT=<w> python backend/benchmarks/recall_benchmark.py --fixture backend/benchmarks/fixtures/recall_v2.json`.

## Consequences

- Recalled memory reflects the *current* fact when facts supersede one another over time — directly in
  service of Epoch X's "durable, correct recall" and the later Tutelage epoch that depends on it.
- One tunable knob to reason about; default documented here and enforced consistent by the benchmark.
- Not a substitute for explicit supersession/validity modeling; that remains a future option if a
  harder temporal case defeats the bounded term.

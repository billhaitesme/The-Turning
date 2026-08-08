# 0017 — Hybrid (lexical + vector) memory retrieval (Epoch X)

**Status:** Accepted — mechanism landed **available but disabled by default** (`MEMORY_LEXICAL_WEIGHT=0`); no measured benefit on the current corpus.
**Date:** 2026-08-07
**Credit:** Hybrid retrieval is a technique borrowed from **[MemPalace](https://github.com/MemPalace/mempalace)**
(MIT) — see its assessment in [`../architecture/epoch-x-memory-and-retrieval.md`](../architecture/epoch-x-memory-and-retrieval.md),
idea #3 ("layer keyword boosting … on top of vector similarity"). The technique is adopted; no
MemPalace code is used, and no second store is introduced.
**Builds on:** ADR [`0016-temporal-aware-retrieval.md`](0016-temporal-aware-retrieval.md) (recency term).

## Context

After ADR 0016, `search_memories` ranks by `cosine + recency`. Pure-vector similarity still
under-ranks **exact-term** recall: when two memories are near-identical in meaning and differ only by
a specific token — a proper noun, an id, a port (`Project Orion` vs `Project Nova`, `OMEGA-419` vs
`OMEGA-412`, port `9091` vs `9090`) — their embeddings are nearly the same, and the query's
distinguishing token carries little semantic weight. The correct memory is present but not ranked
first. This is the classic case hybrid retrieval addresses.

## Decision

Blend a bounded **lexical** signal into the ranking, alongside cosine and recency:

```
ranking_score = cosine + MEMORY_LEXICAL_WEIGHT * lexical + MEMORY_RECENCY_WEIGHT * recency_norm
```

- `lexical ∈ [0, 1]` is the fraction of the query's content tokens (lowercased, stop-worded) present
  in the memory text (`summary_text` + `source_text`). It is exact-token overlap — it rewards the
  memory that literally contains the query's distinguishing term.
- Because the term is normalized to `[0, 1]` and weighted, it can only reorder candidates whose cosine
  similarities differ by less than the weight — genuine near-ties. Clear cosine winners are unaffected.
- `MEMORY_LEXICAL_WEIGHT=0` removes the lexical signal (exactly the ADR-0016 behavior); operators can
  tune or disable it.

The change lives entirely in `search_memories` / `_rank_memories` in the deterministic runtime.
Deterministic, single store, no LLM (an LLM reranker — MemPalace idea #4 — is deliberately *not*
adopted here; it would strain the deterministic boundary).

### Why not the alternatives

- **Full BM25/TF-IDF index.** A second index and more machinery for little gain at this corpus size;
  token-coverage over the stored text is enough and stays inside the one store.
- **LLM reranker (MemPalace #4).** Non-deterministic and model-dependent; rejected for now, gated/off
  by default if ever adopted.
- **Scoped retrieval (MemPalace #1).** Complementary, not a substitute — deferred to a later slice
  (needs per-memory topic/scope assignment).

## Evidence (recall_v3, embeddinggemma)

`recall_v3` = `recall_v2` + four lexical "twin" pairs (q16–q19) where two memories differ only by a
distinguishing token and the correct one is sometimes the *older* of the pair (so recency cannot be
what rescues it). Gate: hybrid must **raise hit@1 on recall_v3** and **not regress recall_v2** (which
must stay 1.000).

| config (LEX, REC) | fixture | hit@1 | recall@3 | MRR |
|---|---|---|---|---|
| (0, 0.05) baseline | recall_v3 | 1.000 | 1.000 | 1.000 |
| (0.10, 0.05) | recall_v3 | 1.000 | 1.000 | 1.000 |
| (0.15, 0.05) | recall_v3 | 1.000 | 1.000 | 1.000 |
| (0.25, 0.05) | recall_v3 | 1.000 | 1.000 | 1.000 |
| (0.15, 0.05) | recall_v2 | 1.000 | 1.000 | 1.000 |

**Result: neutral — no gain, no harm.** The `weight=0` baseline already scores 1.000 on `recall_v3`,
including every twin case: `embeddinggemma` ranks the correct twin first on cosine alone (it even
disambiguates one-character-different ticket codes). Lexical has nothing to fix and does not regress
`recall_v2`. Per the discipline ("ships only if the benchmark says it helps"), the mechanism is landed
**disabled by default** (`MEMORY_LEXICAL_WEIGHT=0`, so ranking is identical to ADR 0016) — a tested,
reversible knob to enable and re-measure if a future corpus or embedder shows exact-term recall
degrading. Reproduce:
`MEMORY_LEXICAL_WEIGHT=<w> MEMORY_RECENCY_WEIGHT=0.05 python backend/benchmarks/recall_benchmark.py --fixture backend/benchmarks/fixtures/recall_v3.json`.

## Consequences

- Ranking behavior is unchanged by default (lexical weight 0 ⇒ identical to ADR 0016). The capability
  and its tests exist; enabling is a one-env-var change if a future corpus/embedder needs it.
- The benchmark earned its keep: it prevented shipping ranking complexity that the numbers don't
  justify. A negative result is a result.
- Two bounded knobs (lexical, recency), each unable to reorder anything but near-ties.

## Typo robustness — fuzzy signal (available, off by default)

Exact token overlap does **not** help misspelled queries: a typo ("Altiar") matches neither the
embedding's nearest token *nor* an exact lexical token (embeddings are actually the more typo-tolerant
signal, via subword tokenization). The right tool for typos is a **fuzzy** term — character-trigram
overlap, which survives a misspelling because only the few trigrams around the changed character are
disturbed.

This is implemented as a third bounded term, `MEMORY_FUZZY_WEIGHT` (default **0**, off), blended the
same way as lexical/recency and skipped entirely when off. It ships **available but disabled** — the
capability exists and is unit-tested for typo tolerance, without changing default behavior. Deliberately
*not* accompanied by a full typo-injected benchmark sweep yet (avoiding scope creep); tuning/enabling it
should be gated on a typo-perturbed `recall_v3` measurement if/when typo'd recall becomes a real need.

Remaining MemPalace ideas — scoped retrieval (#1), explicit temporal validity windows (#2), LLM
rerank (#4) — remain open, to be taken only where a measured case demands them.

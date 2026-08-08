# Memory benchmarks (Epoch X)

Retrieval-quality measurement for the runtime's long-term memory. The point, per
[`docs/architecture/epoch-x-memory-and-retrieval.md`](../../docs/architecture/epoch-x-memory-and-retrieval.md),
is that any change to `search_memories` (scoped / hybrid / temporal / rerank) is judged against a
**number**, not a hunch. This changes no production behavior — it only measures it.

## Run

Real embedder (Ollama must be up with the embed model):

```bash
python backend/benchmarks/recall_benchmark.py --k 1,3,5 --out backend/benchmarks/results/recall_v1_baseline.json
```

Offline smoke (deterministic stub embedder, no Ollama — for wiring, not quality):

```bash
python backend/benchmarks/recall_benchmark.py --stub
```

The hermetic unit test (`tests/test_recall_benchmark.py`) runs the seed→search→score pipeline with
the stub embedder and a temp DB, so CI needs no Ollama.

## What it measures

`recall_v1.json` is a small LongMemEval-style set: 18 memories for one user and 12 queries, each
naming the memory id(s) a correct retrieval should surface. It deliberately includes paraphrases,
topical distractors, and one **temporal-supersession** case (an old fact superseded by a newer one).
Metrics, all in [0,1]: `hit@1`, `recall@k`, `MRR`.

## Baseline — recall_v1 (2026-08-07, embeddinggemma via Ollama)

| metric | value |
|---|---|
| hit@1 | 0.917 |
| MRR | 0.958 |
| recall@3 | 1.000 |
| recall@5 | 1.000 |

## Fixtures

- `recall_v1.json` — original set; one temporal-supersession case.
- `recall_v2.json` — v1 + more temporal pairs (slice 2, temporal-aware retrieval, ADR 0016).
- `recall_v3.json` — v2 + lexical "twin" pairs separable only by a specific token (slice 3, hybrid
  retrieval, ADR 0017).

## Ranking signals (tunable, bounded)

`search_memories` ranks by `cosine + MEMORY_LEXICAL_WEIGHT*lexical + MEMORY_RECENCY_WEIGHT*recency`.
Each added term is normalized to [0,1], so it only reorders near-ties. Set either weight to `0` to
isolate a signal, e.g. measure the pre-hybrid baseline:

```bash
MEMORY_LEXICAL_WEIGHT=0 MEMORY_RECENCY_WEIGHT=0.05 python backend/benchmarks/recall_benchmark.py --fixture backend/benchmarks/fixtures/recall_v3.json
```

Defaults: `MEMORY_RECENCY_WEIGHT=0.05` (on), `MEMORY_LEXICAL_WEIGHT=0` (off — hybrid showed no measured
gain on the current corpus; see ADR 0017). Set `MEMORY_LEXICAL_WEIGHT>0` to enable and re-measure.

Retrieval is strong out of the box. The **only** miss is the temporal query ("which model *currently*
generates responses"): the current flat cosine ranking returned the older, superseded fact above the
newer one. That single measured failure is the concrete motivation for the next slice —
**temporal-aware retrieval** (validity windows / recency boosting) — which can now be proven or
disproven against this number.

> The baseline is environment-dependent (embedder model + version). Re-run after changing the embed
> model. Results are written to `results/` for the record.

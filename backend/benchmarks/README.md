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
- `recall_scoped_v1.json` — two "rooms" with parallel name-free facts; only scope resolves them
  (slice 5, scoped retrieval, ADR 0019; flat hit@1 0.500 → scoped 1.000).
- `recall_scoped_v2.json` — rooms + a global wing (unscoped preferences recallable inside any room,
  other rooms excluded) (slice 6, scope assignment, ADR 0020; hit@1 1.000).

## Ranking signals (tunable, bounded)

`search_memories` ranks by
`cosine + MEMORY_LEXICAL_WEIGHT*lexical + MEMORY_FUZZY_WEIGHT*fuzzy + MEMORY_RECENCY_WEIGHT*recency`.
Each added term is normalized to [0,1], so it only reorders near-ties. Set any weight to `0` to
isolate a signal, e.g. measure the pre-hybrid baseline:

```bash
MEMORY_LEXICAL_WEIGHT=0 MEMORY_RECENCY_WEIGHT=0.05 python backend/benchmarks/recall_benchmark.py --fixture backend/benchmarks/fixtures/recall_v3.json
```

Defaults: `MEMORY_RECENCY_WEIGHT=0.05` (on), `MEMORY_LEXICAL_WEIGHT=0` and `MEMORY_FUZZY_WEIGHT=0`
(off — hybrid showed no measured gain on the current corpus, and fuzzy awaits a typo-injected
measurement; see ADR 0017). Write-path knobs: `MEMORY_SUPERSEDE_THRESHOLD=0` /
`MEMORY_SUPERSEDE_DECLARED_THRESHOLD=0` (supersession off; calibrated recommendation 0.80/0.45, ADR
0021) and `MEMORY_CONSOLIDATION_THRESHOLD=0.95` (consolidation scan floor, ADR 0023). Set a weight
above `0` to enable and re-measure.

## Supersession calibration

`supersession_benchmark.py` measures the write-path dispositions (auto / pending / none) against
expected pairs and reports per-pair cosine plus precision — the calibration evidence behind the ADR
0021 floors:

```bash
MEMORY_SUPERSEDE_THRESHOLD=0.80 MEMORY_SUPERSEDE_DECLARED_THRESHOLD=0.45 python backend/benchmarks/supersession_benchmark.py
```

## Embedder bake-off (2026-08-08) — embeddinggemma retained

Decision rule (pre-registered): swap only if a candidate matches every recall ceiling AND strictly
beats the supersession calibration. Run: recall_v2/v3 + recall_scoped_v2 + supersession (0.80/0.45)
under each embedder via `OLLAMA_EMBED_MODEL=<m>`.

| embedder | recall_v2 hit@1 | recall_v3 hit@1 | scoped_v2 hit@1 | supersession |
|---|---|---|---|---|
| **embeddinggemma (kept)** | **1.000** | **1.000** | 1.000 | 8/9 |
| nomic-embed-text | 0.867 | 0.895 | 1.000 | 8/9 |
| mxbai-embed-large | 0.867 | 0.895 | 1.000 | 8/9 |

Both candidates lose recall — the primary function — and nothing dominates on supersession
(nomic separates the ambiguous undeclared band slightly better; mxbai errs toward noise). Switching
would also invalidate all stored embeddings and the calibrated floors. Re-run this bake-off if the
memory corpus or embedder landscape changes materially.

> Historical note: the original v1 baseline's single miss (a temporal-supersession query under flat
> cosine) motivated ADR 0016, which fixed it — the pattern every later slice followed. Baselines are
> environment-dependent (embedder model + version); re-run after changing the embed model. Write
> results to `results/` with `--out` when recording a baseline for the record.

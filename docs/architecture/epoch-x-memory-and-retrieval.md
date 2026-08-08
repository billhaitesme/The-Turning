# Epoch X notes — Memory and Retrieval

**Status:** Delivered (Epoch X, 0.3.0–0.3.2). Captured 2026-07-24 as a future-work assessment; the
ideas below shipped via ADRs [0016](../decisions/0016-temporal-aware-retrieval.md)–[0023](../decisions/0023-memory-consolidation.md).
Retained as the record of the MemPalace evaluation and the epoch's rationale.

These are ideas to evaluate for a future memory epoch, recorded after assessing
[MemPalace](https://github.com/MemPalace/mempalace) (MIT-licensed, local-first semantic
memory: verbatim storage + ChromaDB, temporal knowledge graph, MCP server).

## Why we are not adopting MemPalace as a dependency

OMEGA-ARC already implements the core of what MemPalace provides, natively and integrated
with the deterministic runtime:

- `backend/app.py` `get_embedding()` — embeddings via the local Ollama `embeddinggemma`
  model (the same model family MemPalace defaults to).
- `save_memory()` / `search_memories()` — scored semantic recall.
- `build_memory_block()` / `build_adaptive_guidance()` — memory woven into the prompt.
- A knowledge graph (`knowledge_graph.json`), an evidence store, and a conversation database.

Adopting MemPalace wholesale would introduce a **parallel persistence authority** (its own
ChromaDB, its own SQLite knowledge graph, its own hierarchy), which conflicts with:

- **ADR-IX-002** — the deterministic runtime owns state and persistence.
- The single-authority and "replaceable subsystems" principles: two memory systems and two
  knowledge graphs competing to be the source of truth is exactly what to avoid.

It is also a large dependency (ChromaDB, gRPC, ~300 MB embeddings, 301 open issues at review
time), and roughly half its surface (mining Claude Code / Cursor sessions) targets coding
assistants, not a persistent local intelligence.

## Ideas worth borrowing (techniques, not code) — delivery status

All five were adopted or resolved during Epoch X: (1) scoped retrieval → ADR 0019/0020; (2) temporal
validity → recency tie-break (ADR 0016) + declared-change supersession (ADR 0021); (3) hybrid
retrieval → built, measured neutral, ships disabled (ADR 0017); (4) reranking → rejected as
non-deterministic (ADR 0017); (5) recall benchmark → `backend/benchmarks/` (the first slice).

1. **Scoped retrieval.** MemPalace's "wings/rooms/drawers" is scoped search — recall within a
   person / project / topic instead of one flat corpus. If `search_memories` is a flat cosine
   k-NN today, scoping is a likely quality win.
2. **Temporal validity windows** on knowledge-graph edges — "this fact held from X to Y."
   Fits the evidence philosophy and would let recall respect supersession.
3. **Hybrid retrieval** — layer keyword boosting, temporal-proximity boosting, and
   preference-pattern extraction on top of vector similarity. Measurably better than
   embeddings alone.
4. **Reranking pass** — an optional LLM rerank over top-k for the hardest recalls.
5. **A recall benchmark** — adopt a LongMemEval-style measurement so retrieval quality is
   measured, not assumed. This is arguably the highest-value idea: it makes any future memory
   work evaluable.

## Constraints for any future memory work

- Stay behind a single, replaceable memory-subsystem boundary; never a second store.
- Preserve the deterministic runtime authority and local-first / offline posture.
- Keep records human-readable and reversible, per the Covenant.

## Recommended first step (as executed)

The recommendation below was followed as written: the recall benchmark landed first, and every
subsequent retrieval change (temporal, hybrid, scoped) was judged against it — including the honest
negative result that kept hybrid disabled. See ADRs 0016–0023.

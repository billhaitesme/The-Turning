# Epoch X notes — Memory and Retrieval

**Status:** Future / not scheduled. Captured 2026-07-24. Not IX-B or IX-C scope.

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

## Ideas worth borrowing (techniques, not code)

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

## Recommended first step (when scheduled)

Audit the current `search_memories` ranking, then decide whether scoped + hybrid + temporal
retrieval improves it — measured against a small recall benchmark — before any larger design.

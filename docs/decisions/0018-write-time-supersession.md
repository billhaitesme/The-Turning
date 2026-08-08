# 0018 — Write-time memory supersession (Epoch X)

**Status:** Accepted — mechanism landed **available but disabled by default** (`MEMORY_SUPERSEDE_THRESHOLD=0`).
**Date:** 2026-08-07
**Builds on:** ADR [`0016-temporal-aware-retrieval.md`](0016-temporal-aware-retrieval.md) (read-time recency);
relates to MemPalace idea #2 (temporal validity windows), [`../architecture/epoch-x-memory-and-retrieval.md`](../architecture/epoch-x-memory-and-retrieval.md).

## Context

Memory has been append-only: when a fact changes ("port is 8000" → "port is 8001"), both rows persist
and ADR 0016 only *nudges* the newer one up at read time. That keeps the stale fact in the store and
recall correct only by a ranking heuristic. The "durable" leg of Epoch X wants the store to be
**correct at the source** — and a learner (the later Tutelage epoch) must be able to *update* what it
knows, not only accumulate.

The hard part is distinguishing **"replaces"** (port 8000 → 8001) from **"complements"** (backend is
FastAPI; backend is Python — both true). Embedding similarity alone cannot reliably tell them apart:
complementary facts on one subject can be highly similar. Over-eager supersession would silently hide
true facts — the opposite of durable memory.

## Decision

Add supersession at **write** time, deterministic and reversible, and **off by default**.

- On `save_memory`, if `0 < MEMORY_SUPERSEDE_THRESHOLD ≤ 1`, find existing non-superseded memories of
  the **same `kind`** and **same scope** (user/conversation) whose embedding cosine to the new memory
  is `≥ threshold`, and mark them `superseded` (`superseded_by`, `superseded_at` recorded).
- Superseded rows are **kept in the database** — never deleted — so the change is auditable and fully
  reversible (clear the flag to restore). `search_memories` simply excludes `superseded` rows from
  active recall.
- **Default off** (`threshold=0`): because similarity cannot by itself separate "replaces" from
  "complements", enabling is a deliberate operator choice with a calibrated threshold. A high value
  (near-duplicate restatements) is safe; lower values chase value-changes at rising false-positive
  risk. When off, `save_memory` behavior is unchanged.

Deterministic, single store, no LLM, no new authority.

### Why not the alternatives

- **Delete the old row.** Irreversible and lossy — violates the Covenant's reversible/human-readable
  records. We flag, never delete.
- **Read-time only (ADR 0016 recency).** Keeps stale rows and only reorders; fine as a safety net but
  not "durable at the source." Supersession complements it.
- **Explicit validity-window edges (MemPalace #2) / contradiction detection.** The principled way to
  separate replace-from-complement, but heavier (needs a subject key or the reasoning engine's
  contradiction signal). Deferred; the threshold knob is the minimal step, and its default-off honesty
  reflects that the robust signal isn't here yet.

## Evidence

Validated by deterministic unit tests (`tests/test_supersession.py`) with a controlled embedder, so
similarity — and thus every supersession decision — is exact:

- A new fact of the same kind/scope with similarity ≥ threshold **supersedes** the prior one; recall
  then returns the current fact and both rows remain in the DB (reversible).
- **Complementary** (orthogonal-embedding) facts are **not** superseded.
- A same-text fact of a **different kind** is not superseded.
- With the default threshold `0`, nothing is superseded and recall returns both.

A real-embedder threshold-calibration sweep (where does false-supersession begin?) is intentionally
**not** run here to avoid scope creep; it is the prerequisite before ever enabling this in production,
and the recall benchmark + a supersession fixture are the tools to do it.

## Consequences

- The store can now become *correct at the source* when enabled, not only patched at read time — the
  durability substrate the learning epoch needs.
- Zero behavior change by default; a tested, reversible knob gated on operator calibration.
- The "replaces vs complements" problem is named, not solved — a future slice (validity windows /
  contradiction-aware supersession) is where it gets solved properly.

# 0021 — Robust supersession: declared change + reviewed candidates (Epoch X)

**Status:** Accepted — upgrades the ADR 0018 mechanism; still **off by default** pending the
calibration evidence below being re-run whenever the embedder changes.
**Date:** 2026-08-08
**Builds on:** ADR [`0018-write-time-supersession.md`](0018-write-time-supersession.md) (reversible
flags, threshold knob) and ADR [`0020-scope-assignment.md`](0020-scope-assignment.md) (rooms).

## Context

ADR 0018 shipped supersession disabled because its only signal — embedding similarity — cannot
separate **"replaces"** (port 8000 → 8001) from **"complements"** (backend is FastAPI; backend is
Python). Silently hiding a complementary truth is memory corruption, so the raw threshold could not
be trusted with automatic authority.

The runtime already has a posture for exactly this situation: deterministic signals act, everything
else **proposes** (planning proposes, deliberation recommends, tools await approval). Supersession
should work the same way.

## Decision

Split supersession into two dispositions, both recorded in a `supersession_candidates` audit table:

- **AUTO — declared change.** If the *new memory's own text* declares a change — matches a
  deterministic marker pattern (`is/are now`, `changed/switched/moved/updated/renamed to`,
  `no longer`, `instead of`, `replaced by` …) — and a prior memory of the **same kind and same room**
  has cosine ≥ `MEMORY_SUPERSEDE_THRESHOLD`, the prior row is flagged superseded (reversible, never
  deleted). The author of the fact announced the replacement; the runtime records it.
- **PROPOSE — undeclared collision.** Same-kind/same-room similarity above the floor *without* a
  declared change becomes a **pending candidate**: nothing is hidden from recall until an operator
  approves it. `GET /system/memory/supersession-candidates` lists pending;
  `POST .../{id}/resolve {action: approve|reject}` decides. Approve flags the old row; reject closes
  the candidate and both memories stay active.

Bare "now" is deliberately not a marker (too common in casual text); only change *frames* count.
Cross-kind and cross-room collisions are never candidates. Threshold 0 disables scanning entirely —
the ADR 0018 default is preserved.

### Why this is the robust form

- The **false-positive direction is closed by construction**: an undeclared complement can, at worst,
  generate a pending candidate that an operator rejects — it can never silently vanish a true fact.
- The **auto path requires two independent signals** (declared change + high similarity in the same
  kind/room), both deterministic and auditable.
- This is the proposal-only posture applied to memory — and the review queue doubles as the first
  **memory review surface** (a roadmap item in its own right).

### Why not the alternatives

- **LLM judgment of "replaces vs complements".** Non-deterministic authority over what the child
  remembers; rejected.
- **Validity windows as the primary mechanism (MemPalace #2).** Still needs the same
  when-does-it-close signal; declared-change + review *is* that signal. Windows can layer on later as
  a data model refinement.
- **Raw threshold auto-supersession (ADR 0018).** Measured risk of hiding complements; retired in
  favor of the two-disposition form.

## Evidence

Deterministic tests (`tests/test_supersession.py`, controlled embedder): declared change
auto-supersedes and recall returns only the current fact (rows retained); undeclared collision →
pending, nothing hidden; approve/reject paths; complements, cross-kind, cross-room produce nothing;
threshold 0 does nothing; marker true/false cases.

Real-embedder calibration (`benchmarks/supersession_benchmark.py`, embeddinggemma; 9 pairs — 4
declared replacements, 2 undeclared replacements, 3 complements) produced a decisive finding:

**A single similarity floor cannot work — measured, not assumed.** A replaced *value* drags the
embedding away from the old fact, so true declared replacements score *lower* similarity than some
unrelated complements: "active model is dolphin-mixtral" → "active model is now llama-3.1-abliterated"
fell **below 0.70**, while the complement pair "written in Python" / "framework is FastAPI" sat at
**0.77**. Single-floor sweeps scored 5/9 (0.70 and 0.80) and 4/9 (0.88) — the floor blocks exactly
the declared replacements the marker correctly identified.

Hence the **two-tier floors**: the declared-change marker is itself the strong signal, so declared
changes use the lower `MEMORY_SUPERSEDE_DECLARED_THRESHOLD` while undeclared collisions (similarity
alone) keep the high `MEMORY_SUPERSEDE_THRESHOLD`. Calibrated sweep:

| floors (undeclared / declared) | correct | notes |
|---|---|---|
| single floor 0.70 / 0.80 / 0.88 | 5/9 · 5/9 · 4/9 | floor blocks true declared replacements |
| **0.80 / 0.45 (recommended)** | **8/9** | all 4 declared replacements auto (sims 0.655–0.812); all complements silent |
| 0.80 / 0.55 · 0.85 / 0.50 | 8/9 · 8/9 | same profile — the declared tier is robust across this range |

The one persistent miss is instructive: the undeclared replacement "deadline Tuesday → Friday" sits at
sim **0.78**, only 0.01 above the "Python / FastAPI" *complement* at **0.77**. The undeclared band is
**irreducibly ambiguous by similarity** — no floor separates those — which is exactly why undeclared
collisions are only ever *proposed* for review, never auto-superseded. An operator lowering the
undeclared floor into that band (e.g. 0.75) trades a few rejectable noise candidates for catching more
true replacements; that trade belongs to the operator, not a default.

The default stays **off** until the operator enables it; re-run the calibration whenever the
embedding model changes. Reproduce:
`MEMORY_SUPERSEDE_THRESHOLD=0.80 MEMORY_SUPERSEDE_DECLARED_THRESHOLD=0.45 python backend/benchmarks/supersession_benchmark.py`.

## Consequences

- Supersession is now safe to enable: declared changes update the store at the source; ambiguous
  collisions queue for review instead of guessing. The learner can *revise* what it knows without
  risking silent loss of true facts.
- A visible review queue exists for memory — the first operator surface over the child's memory, and
  the natural place for future re-scoping/consolidation review.
- Marker patterns are English-centric and extendable; misses degrade safely (to PROPOSE, never to
  silent hiding).

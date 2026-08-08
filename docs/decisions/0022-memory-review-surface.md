# 0022 — Memory review surface (Epoch X)

**Status:** Accepted
**Date:** 2026-08-08
**Builds on:** ADR [`0019`](0019-scoped-retrieval.md)/[`0020`](0020-scope-assignment.md) (rooms) and
ADR [`0021`](0021-declared-change-supersession.md) (supersession + candidate queue).

## Context

After X-A/X-B the memory can recall, room, and revise — but it is opaque: the only window into it is
similarity search, and the only review surface is the supersession queue. The Covenant requires
human-readable records and reversible changes; an operator (and the future curriculum's reviewer)
must be able to *see* what the child remembers, correct a misfiled room, and undo a wrong
supersession. Consolidation — the next memory concern — cannot even be designed against an
un-browsable store.

## Decision

A read-and-correct REST surface over the single memory store (no new store, no deletion — ever):

- `GET /system/memory/rooms` — every room with active/superseded counts; `null` = the global wing.
- `GET /system/memory` — filtered browse: `scope` / `unscoped`, `kind`, `status`
  (active | superseded | all), substring `q`, pagination. Embeddings are never returned — the surface
  is human-readable by construction.
- `GET /system/memory/{id}` — full detail plus its audit trail.
- `POST /system/memory/{id}/scope` — re-room (null → global wing). Explicit operator action.
- `POST /system/memory/{id}/restore` — reverse a supersession; the row returns to active recall.

Every correction is recorded in a `memory_events` audit table (`rescope`, `restore`, with
before/after detail), so the memory's own history is itself a human-readable record. Deletion is
deliberately not offered: superseding (reviewed) and re-rooming cover every legitimate correction
without loss.

## Evidence

Deterministic tests (`tests/test_memory_review.py`): rooms counts (including the global wing and
superseded tallies); every browse filter; re-room + audit event (including to-global); restore
returns the row to active recall, is audited, and refuses non-superseded rows; 404/422 handler paths;
embeddings never leak into responses.

## Consequences

- The child's memory is inspectable and correctable end-to-end: browse → detail → re-room / restore,
  with the supersession queue alongside — the operator governance loop over memory is closed.
- Desktop Bridge Zero can later render these endpoints as a Mission Control panel (read-only display
  plus explicitly gated actions) without any new backend work.
- Consolidation (dedup/merge of low-value conversational memories) can now be designed against a
  visible store, with this surface as its review path.

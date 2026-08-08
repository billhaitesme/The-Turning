# 0023 — Memory consolidation: proposed near-duplicate cleanup (Epoch X)

**Status:** Accepted
**Date:** 2026-08-08
**Builds on:** ADR [`0021`](0021-declared-change-supersession.md) (review queue) and
ADR [`0022`](0022-memory-review-surface.md) (browse/restore surface).

## Context

`persist_learning` writes several conversational memories per exchange (user_request,
assistant_response, reflection, strategy). Over months — and especially under a curriculum — the
store accumulates near-duplicate, low-value residue ("what's the weather", asked five ways) that
drowns durable facts and bloats every retrieval candidate set. Left alone, the child's memory gets
noisier as it grows; the "durable" pillar requires the store to stay healthy, not just correct.

Deleting residue is forbidden (Covenant: reversible, human-readable records). Auto-hiding it on
similarity alone repeats the exact mistake ADR 0021 retired.

## Decision

An **operator-invoked consolidation scan** — `POST /system/memory/consolidation-scan`
(`threshold?`, `kinds?`, `max_rows?`) — that:

- clusters **active** memories within (kind, room, user) by embedding cosine at a **high floor**
  (`MEMORY_CONSOLIDATION_THRESHOLD`, default 0.95 — near-duplicates, not merely related facts),
  greedily, newest-first;
- keeps the **newest** row of each cluster as the representative;
- **proposes** each older near-duplicate into the existing supersession review queue as a pending
  candidate with `origin='consolidation'` — approved rows leave active recall but remain in the store
  and restorable via ADR 0022's `restore`; rejected rows stay active;
- never auto-hides: batch consolidation has no declared-change signal, so it has **no auto path** at
  all; re-scans skip rows that already have pending/approved/auto candidates (no duplicate
  proposals).

Deterministic, single store, reuses the queue/review/restore/audit machinery end-to-end. The scan is
on-demand (no background daemon) — running it is an explicit operator action, and the curriculum can
schedule it as a reviewed maintenance step later.

### Why not the alternatives

- **Auto-archive above a floor.** Similarity cannot prove redundancy any more than it proved
  replacement (ADR 0021's measured lesson); a wrong auto-archive silently thins true memory.
- **Merging texts into a synthetic summary row.** Destroys the original human-readable records;
  a representative + reviewable residue keeps every original intact.
- **Deletion / TTL expiry.** Forbidden by the Covenant; also irreversibly wrong when a "duplicate"
  later turns out to carry a distinction.

## Evidence

Deterministic tests (`tests/test_consolidation.py`, controlled embedder): older near-duplicates are
proposed (newest kept) while nothing is hidden pre-approval; approval hides and restore reverses;
kind/room boundaries and the similarity floor are respected; re-scans skip existing candidates;
invalid thresholds are rejected. The 0.95 default floor is intentionally strict — the operator can
lower it per scan after reviewing what the queue surfaces; calibrate against the real corpus before
trusting lower floors.

## Consequences

- The store can be kept healthy as it grows — reviewed, reversible, and audited — completing the
  Epoch X commitment ("durable, scoped, benchmarked") on the write side.
- The review queue now carries two origins (`write`, `consolidation`); a future Bridge Zero panel can
  present both in one place.
- Follow-on (unscheduled): scheduled scans as a curriculum maintenance step, and floor calibration
  against a grown real corpus.

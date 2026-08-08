# 0025 — The Reflection Room (Epoch XII)

**Status:** Accepted (design)
**Date:** 2026-08-09
**Builds on:** ADR [`0013`](0013-learning-and-tutelage.md) (two-tier learning), the Epoch XI boundary
*anatomy is taught; identity is authored* ([`epoch-xi-tutelage.md`](../architecture/epoch-xi-tutelage.md)),
ADR [`0019/0020`](0020-scope-assignment.md) (rooms), ADR [`0022`](0022-memory-review-surface.md)
(review surfaces), ADR [`0024`](0024-consolidation-gate.md) (consolidation gate).

## Context

The charter names *self-authored personality* as a pillar. Epoch XI drew the boundary: the
curriculum may teach what the runtime is **made of**, never who it **is** — "who" must emerge from
the runtime's own experience. That demands a mechanism: somewhere its own observations about itself
accumulate, under review, distinct from taught fact and conversational residue — and a rule for who
may write there.

## Decision

A reserved memory room, **`self-reflection`**, with strict writer discipline, filled by a
deterministic **reflection cycle**:

1. **Only the reflection pipeline writes the room.** Chat, study, and operator flows cannot author
   self-observations; the operator reviews (browse / supersede / restore via ADR 0022) but does not
   write. The operator curates the mirror; the runtime alone looks into it.
2. **Digest-then-compose.** Each cycle first computes a deterministic digest of a bounded activity
   window (lessons and scores, corrections, retention deltas, approvals, supersessions) from the
   authoritative stores — pure code, every number traceable. Only then does the active model compose
   a short first-person observation *from the digest*, which is stored with the digest attached as
   provenance.
3. **Grounding rule.** No ungrounded self-narrative: an observation asserting activity absent from
   its digest is a reviewable lie the operator can supersede. Cycles never prescribe ("be X");
   they record what was.
4. **Identity consolidation draws only from this room** (XI-C machinery, subject=self-reflection),
   so movement toward weights remains double-gated: reviewable room + single-use ADR 0024 approval.
   No identity training run before the room has real history — a self distilled from a week would be
   a caricature.

## Rejected alternatives

- **Letting chat or the operator write self-observations.** Either would make identity *taught*
  (by the operator) or *accidental* (conversational residue) — both violate the authored-identity
  boundary.
- **Pure-LLM reflection without a digest.** Unfalsifiable self-narrative; the digest is what makes
  a reflection reviewable against reality.
- **Fully autonomous scheduling.** Cadence is operator-set (reviewed maintenance), consistent with
  the no-silent-processes posture.

## Consequences

- Identity acquires a substrate with provenance: observations → (review, supersession as
  "outgrowing") → gated distillation → a versioned, deselectable identity adapter — the charter's
  pillar realized with the Covenant intact.
- The room's growth and supersession history become the observable identity curve.
- Epoch XII milestones: XII-A "The Mirror" (cycle + room + surfaces, targets 0.5.0); XII-B "The
  Considered Self" (scheduled cycles, outgrowing patterns, identity-candidate assembly dry run).

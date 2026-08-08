# 0013 — Learning and Tutelage

**Status:** Accepted (2026-08-08) — the Epoch X prerequisite is delivered (0.3.0–0.3.2) and the
epoch design is committed in [`../architecture/epoch-xi-tutelage.md`](../architecture/epoch-xi-tutelage.md).
**Date:** 2026-08-07
**Depends on:** durable memory (Epoch X — delivered; see `docs/architecture/epoch-x-memory-and-retrieval.md`)

## Context

OMEGA-ARC's charter names *education* and *reviewable growth* as core pillars, but no epoch has
defined how the system studies and learns. What exists today is the substrate, not a curriculum:

- Semantic memory (`save_memory` / `search_memories`, local `embeddinggemma` embeddings).
- Evidence, knowledge graph, reasoning, planning, deliberation, and bounded tools.
- One identity LoRA fine-tune (`training/omega_arc_identity.jsonl`, `train.py`) that instilled *who*
  the system is — not *what* it knows.

The intent is an "exponential curriculum": a self-reinforcing study loop where each lesson compounds
on the last. This ADR records the decision to pursue that as a dedicated **Tutelage** epoch, and the
constraints that keep it honest.

## Decision

Pursue learning as a distinct epoch **after** durable memory (Epoch X), built on three principles:

1. **Learning lives in two tiers, deliberately separated.**
   - *Fast tier — memory.* New knowledge is written to the evidence store and semantic memory,
     immediately usable, fully reversible, human-readable. This is where most "learning" happens.
   - *Slow tier — weights.* Periodically, reviewed and consolidated knowledge is distilled into a
     LoRA adapter via the existing `training/` pipeline. This is rare, versioned, and gated.
   Memory is the default; weight change is the exception. This mirrors ADR-IX-001 (Model Lock):
   the model's parameters do not change silently.

2. **The study loop is deterministic and review-gated, not autonomous rewriting.**
   The runtime (not the language model) drives a loop: select a topic → gather/read sources →
   reason → record evidence → self-test against a benchmark → record the result. Consolidation into
   weights requires an explicit approval gate (the deliberation/approval engine already exists).
   "Exponential" describes *compounding*, not unsupervised self-modification.

3. **Growth is measured, not assumed.**
   A recall/skill benchmark (LongMemEval-style) is a prerequisite deliverable, so each study cycle
   produces a reviewable delta. No curriculum ships without a way to measure whether it worked.

## Reason and rejected alternatives

- **Rejected: continuous online fine-tuning.** A model that rewrites its own weights on every
  interaction is unreviewable, irreversible, and violates the Covenant. The two-tier split keeps
  fast learning reversible and slow learning gated.
- **Rejected: memory-only (no weight consolidation).** Pure retrieval never internalizes; the
  context window caps how much compounds. Periodic, reviewed distillation is what makes growth
  durable.
- **Rejected: adopting an external agent/curriculum framework wholesale.** Same reasoning as the
  memory ADR — it would introduce a competing authority. Borrow techniques, not dependencies.

## Consequences

- Requires Epoch X (durable, scoped, benchmarked memory) first — a learner must remember reliably.
- Requires a benchmark harness before any curriculum content.
- Every consolidation is a versioned LoRA adapter with a recorded rationale and a rollback path;
  the active adapter is an operator-visible, Model-Lock-style selection.
- The curriculum itself (what it studies, in what order) is a separate, later design once the loop
  and the measurement exist.

## Migration / rollback

Weight consolidations are additive LoRA adapters, never destructive edits to a base model. Any
adapter can be deselected to return to the prior behavior. Memory-tier learning is already
reversible (human-readable stores).

## Open questions — resolved by the epoch design (2026-08-08)

- *Curriculum sequencing / topic selection:* operator-authored curriculum with prerequisite gating;
  no autonomous selection this epoch.
- *Sources under local-first:* local files per lesson (`curriculum/<subject>/`); network acquisition
  deferred until an allowlisted fetch posture is designed.
- *Self-test false confidence:* all grading is deterministic against operator-authored answer keys
  (recall test needs no LLM at all; comprehension answers are keyword/regex-graded) — the model
  never grades itself.

See [`../architecture/epoch-xi-tutelage.md`](../architecture/epoch-xi-tutelage.md) for the accepted
epoch design (supersedes the earlier sketch).

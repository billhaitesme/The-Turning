# 0024 — The Consolidation Gate (Epoch XI-C)

**Status:** Accepted
**Date:** 2026-08-08
**Builds on:** ADR [`0013`](0013-learning-and-tutelage.md) (two-tier learning), ADR
[`0008`](0008-bounded-tools-and-verified-execution.md) (bounded tools), ADR
[`0014`](0014-operator-approvals.md) (operator approvals).

## Context

ADR 0013's slow tier: periodically, reviewed and stable knowledge is distilled toward the model's
weights — rare, versioned, gated. This is the only step of learning that reaches for the model
itself, so it must pass through the strongest gate the runtime has, and nothing about it may be
automatic or silent.

## Decision

Consolidation is a **bounded mutation tool**, gated end to end:

1. **`tutelage_consolidation`** is a registered tool descriptor (category `mutation`, risk `high`,
   approval required). It has **no adapter** — the tool executor cannot run it; its approval is the
   *ticket*, consumed by `POST /system/tutelage/consolidations`.
2. **Single-use operator approval.** Consolidation demands an approved, unconsumed approval whose
   arguments name the subject; the run consumes it. The next consolidation needs a fresh approval.
   (The IX-C mobile Approvals tab, with biometric confirmation, is a natural surface for this.)
3. **Only key-verified knowledge distills.** For every quiz question of every *passed* lesson, the
   study seat answers from scoped recall; only answers that pass the operator-key grading become
   training pairs (chat-format JSONL matching `training/`). Unverified answers are counted and
   excluded — no unreviewed knowledge moves toward weights.
4. **Versioned adapter registry** (`backend/data/adapters.json`): every artifact is a `candidate`
   with provenance (subject, lessons, pairs file, study model, approval id, rationale). Lifecycle
   `candidate → trained → active → retired` via explicit recorded actions; **activating an adapter
   retires any other active adapter for its subject** (Model-Lock pattern, single-active).
5. **Training itself stays operator-executed** via `training/train.py` (point `DATA_PATH` at the
   artifact). Honest boundary: the runtime serves quantized GGUF models via Ollama while the
   training pipeline fine-tunes HF weights; producing and wiring a runnable adapter (retrain →
   convert / re-quantize → Modelfile) is deliberate operator work outside the runtime's authority.
   The runtime assembles, gates, versions, and records — it never trains.

## Evidence

- Live run (2026-08-08): tool request → operator approval → consolidation of
  `omega-arc-architecture` → **16 key-verified pairs** from 3 passed lessons, **1 unverified answer
  excluded**, candidate `adapter-omega-arc-architecture-20260808T112646` registered; the approval
  was consumed (a second run is blocked until re-approved).
- Hermetic tests: gate blocks without approval; verified-only filtering; single-use consumption;
  registry lifecycle incl. single-active-per-subject. Suite 394 passing.

## Consequences

- The full ADR 0013 loop now exists in the runtime: study → measure → review → **gated
  consolidation** — with the weight boundary intact (no silent change, everything reversible or
  operator-held).
- Adapter records give future epochs (and the operator) a complete provenance chain from lesson
  sources to any adapter that ever touches the model.
- Follow-ons: surfacing consolidation approvals in the mobile Approvals tab is zero-backend work;
  an end-to-end operator runbook for train→convert→activate belongs in `training/` docs when first
  exercised.

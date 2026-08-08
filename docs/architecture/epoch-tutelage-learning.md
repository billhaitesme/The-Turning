# Epoch (future) — Tutelage and Learning

**Status:** Superseded (2026-08-08) by the accepted epoch design,
[`epoch-xi-tutelage.md`](epoch-xi-tutelage.md). Retained as the original sketch. Its prerequisite
("do not start before memory recall is measurable and good") was satisfied by Epoch X (0.3.0–0.3.2).
See ADR [`0013-learning-and-tutelage.md`](../decisions/0013-learning-and-tutelage.md).

This is a design sketch for the epoch where OMEGA-ARC begins studying — turning the "education" and
"reviewable growth" pillars into a real, measured system. It is deliberately conservative: it uses
what already exists rather than inventing new authorities.

## Prerequisite: why memory comes first

A curriculum is only as good as the student's ability to retain and retrieve. Epoch X (durable,
scoped, benchmarked memory) is the substrate; without it, "learning" is just a full context window
that resets. **Do not start Tutelage before memory recall is measurable and good.**

## The study loop (runtime-driven, review-gated)

The deterministic runtime — not the language model — orchestrates each cycle:

1. **Select** a topic from the curriculum (policy TBD).
2. **Gather** sources (local corpus first; network only under the offline/allowlisted posture).
3. **Read + reason** using the existing cognition/reasoning pipeline.
4. **Record evidence** into the evidence store (provenance, temporal validity).
5. **Self-test** against a benchmark; record the score as a reviewable delta.
6. **Consolidate (gated).** When a body of evidence is stable and reviewed, optionally distill it
   into a LoRA adapter via `training/`. This step passes through the approval engine.

Steps 1–5 are the fast, reversible, memory-tier loop that runs often. Step 6 is rare, versioned,
and never automatic.

## Two-tier learning

| Tier | Mechanism | Cadence | Reversibility |
|---|---|---|---|
| Fast | evidence store + semantic memory | continuous | fully reversible, human-readable |
| Slow | LoRA adapter (`training/` pipeline) | periodic, gated | additive adapter, deselectable |

The base model is never destructively edited. The active adapter is an operator-visible selection,
consistent with Model Lock (ADR-IX-001) — the same "explicit operator action, recorded" principle
the model selector already implements.

## Measurement (a prerequisite deliverable)

A recall/skill benchmark (LongMemEval-style) must exist before curriculum content. Each study cycle
emits a score delta so growth is *observed*, not asserted. This is what makes "exponential" a claim
that can be checked rather than a slogan.

## What "exponential" honestly means here

Not unsupervised self-modification. It means **compounding**: memory accumulates, evidence links,
periodic distillation frees context budget for the next layer, and the benchmark shows whether each
layer built on the last. A local model's weights do not self-improve on their own; the compounding
comes from the loop plus reviewed consolidation.

## Governance fit (the Covenant test)

- *Can it explain why it learned something?* Evidence provenance + the study-cycle record.
- *Can it be reversed?* Fast tier is reversible; slow tier is a deselectable adapter.
- *Does it preserve history?* Every cycle and consolidation is recorded.
- *Reviewable growth?* The benchmark delta is the review artifact.

## Explicitly out of scope for this sketch

- The curriculum content and sequencing policy (a later design).
- Source acquisition strategy under offline-first.
- Guarding self-tests against self-graded false confidence.

## First concrete step, when scheduled

Build the benchmark harness against current `search_memories`, establish a baseline, then design the
smallest possible study cycle (one topic, memory-tier only) and measure it — before any weight
consolidation or curriculum design.

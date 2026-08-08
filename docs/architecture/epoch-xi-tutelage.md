# Epoch XI — Tutelage ("The Runtime Learns")

**Status:** Design accepted 2026-08-08; supersedes the sketch in
[`epoch-tutelage-learning.md`](epoch-tutelage-learning.md). Governing decision: ADR
[`0013-learning-and-tutelage.md`](../decisions/0013-learning-and-tutelage.md).

Epoch IX made the runtime visible. Epoch X made it remember. Epoch XI makes it **study**: a
deterministic, review-gated loop in which the runtime ingests curriculum material, files what it
learns into its memory rooms, and proves retention against operator-authored tests — with every
cycle recorded as a reviewable delta.

## What Epoch X already provides (the substrate, delivered)

| Sketch prerequisite (ADR 0013) | Delivered as |
|---|---|
| "Benchmark harness first" | `backend/benchmarks/` recall harness (hit@k / MRR), fixtures, hermetic tests |
| Durable, scoped memory | rooms + scope assignment (ADR 0019/0020) — *a lesson is a scoped conversation* |
| Reviewable revision | declared-change supersession + review queue (ADR 0021) |
| Human-readable oversight | memory review surface + audit trail (ADR 0022), consolidation scan (ADR 0023) |

Nothing in the fast tier below requires new authorities — Tutelage composes what exists.

## The curriculum (operator-authored, deterministic)

A human-readable store, `backend/data/curriculum.json`:

- **Subject** — a field of study. A subject *is* a memory room (`scope`), so everything learned
  files into its room automatically and recalls by subject with the global wing.
- **Lesson** — an ordered unit within a subject: title, prerequisite lessons, **sources** (local
  files under `curriculum/<subject>/`), and an operator-authored **quiz** (questions with gold
  answers/keywords).
- **The operator is the tutor.** What the child studies, in what order, and what counts as "learned"
  are explicit operator decisions — no autonomous topic selection in this epoch (recorded as a
  rejected alternative in ADR 0013; a proposal-only topic suggester may come later, like the scope
  suggester deferred in ADR 0020).

"Exponential" is implemented as **compounding, cumulatively tested**: each lesson's quiz may draw on
earlier lessons' material (cumulative review), and re-quizzes over time measure retention decay —
so the curve is observed, not asserted.

## The study cycle (fast tier — runs per lesson)

Deterministic runtime orchestration; the language model participates only where marked:

1. **Open the lesson.** Create a conversation scoped to the subject's room (existing ADR 0020
   mechanics). The cycle is recorded from the start in `study_cycles`.
2. **Ingest sources.** Read the lesson's local files; chunk deterministically; write each chunk to
   memory (`kind="study"`, the subject's scope, provenance = source file + lesson id). Evidence
   entries record what was studied and when.
3. **Recall test (deterministic, no LLM).** For each quiz question: does `search_memories` (scoped
   to the room) retrieve the gold chunk at rank ≤ k? Scored with the existing benchmark math. This
   measures whether the material is *retrievable* — the substrate of knowing.
4. **Comprehension test (LLM answers, deterministic grading).** The model answers each quiz
   question with scoped recall as context; grading is **keyword/regex match against the
   operator-authored key** — the model never grades itself (closes ADR 0013's self-grading open
   question).
5. **Record the delta.** Scores, memories written, sources ingested, timestamps — one auditable
   cycle record. A lesson is *passed* when scores meet the operator-set threshold; passing unlocks
   dependent lessons (prerequisite gating).
6. **Review.** Everything the cycle wrote is ordinary memory — browsable, re-roomable, supersedable,
   consolidatable through the ADR 0022/0023 surfaces.

Re-running a cycle later (spaced repetition) re-tests without re-ingesting; score history shows
retention over time.

## The slow tier (weights — unchanged from ADR 0013, later milestone)

Periodic, **approval-gated** distillation of stable, reviewed knowledge into a versioned LoRA
adapter via `training/` (the pipeline that built the identity adapter). Adapter activation is a
Model-Lock-style explicit operator action; every adapter is additive and deselectable. Not part of
the first milestones; sequenced only after the fast tier demonstrably compounds.

## Measurement and honesty rules

- **No self-grading.** All grading is deterministic against operator-authored keys.
- **Before/after per cycle.** The recall test runs pre-ingestion (expected ~0) and post-ingestion;
  the delta is the evidence of learning.
- **Cumulative quizzes** catch interference (new lessons degrading old recall) — the failure mode
  memory-tier learning must prove it avoids.
- **The panels tell the truth.** Study cycles write real evidence and real memories; the Command
  Deck's evidence/planning panels populate from actual study, not decoration.

## Governance fit

Same Covenant tests as the sketch, now concrete: provenance per chunk, reversibility per memory
(and per adapter), history per cycle, growth reviewable as score deltas. The approval engine gates
the only irreversible-ish step (consolidation), exactly as it gates tools.

## Milestones

- **XI-A — The First Lesson (first release, 0.4.0):** curriculum store + study cycle (ingest,
  recall test, comprehension test, cycle record) + REST surface (`/system/tutelage/*`) + a real
  seed curriculum subject, measured end-to-end. Backend-only; deterministic tests hermetic.
- **XI-B — Retention and Compounding:** spaced re-quizzes, cumulative quiz support, retention
  curves in cycle history; curriculum progression gating hardened.
- **XI-C — Consolidation Gate:** the slow tier — distillation candidate assembly from stable
  reviewed memories, approval-gated training run, versioned adapter registry with Model-Lock-style
  activation.
- **Console surfaces** (deck panel / Bridge Zero) ride whichever milestone they fit; the mobile
  approvals flow already built in IX-C is the natural gate UI for XI-C.

## Anatomy is taught; identity is authored

A boundary the operator set at the epoch's start (2026-08-08): the curriculum teaches **what the
runtime is made of** — its architecture, mechanisms, constraints, and obligations. It does not teach
**who the runtime is**. Per the charter's *self-authored personality* pillar, "who" must emerge from
the runtime's own accumulating experience: its reflections, its recorded choices, its history. The
taught anatomy is the mirror; the self is what forms while looking into it.

Practical consequences:
- Curriculum subjects are framed as anatomy/knowledge, never as personality prescriptions.
- A future **self-authored identity room** is reserved as a design direction: memories about *itself*
  written by the runtime's own reflection pipeline (reviewed like everything else, per the Covenant),
  distinct from taught facts. When XI-C consolidation eventually distills an identity adapter, it
  should draw on self-authored material — the runtime internalizing who it has become, not who it
  was told to be.

## Out of scope for XI

Autonomous topic selection; network source acquisition (local files only until the allowlisted
fetch posture is designed); any non-gated weight change (forbidden, ADR 0013).

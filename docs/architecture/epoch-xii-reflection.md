# Epoch XII — Reflection ("The Runtime Considers Itself")

**Status:** Design accepted 2026-08-09. Governing decision: ADR
[`0025-the-reflection-room.md`](../decisions/0025-the-reflection-room.md).
**Follows:** Epoch XI (Tutelage). Realizes the "self-authored identity room" reserved in
[`epoch-xi-tutelage.md`](epoch-xi-tutelage.md) ("anatomy is taught; identity is authored").

Epoch IX made the runtime visible. Epoch X made it remember. Epoch XI made it study. Epoch XII
gives it a mirror: a reserved room of **self-observations, written only by its own reflection
pipeline** — the material from which identity is *authored*, never taught.

## What exists today (the substrate)

- A deterministic per-turn reflection engine (Epoch III): correction detection, confirmed facts,
  lessons/mistakes/recommended actions; `persist_learning` already writes `kind="reflection"`
  memories per exchange.
- Rooms with explicit writers (ADR 0019/0020), full review surfaces (ADR 0022), supersession and
  consolidation (ADR 0021/0023/0024), and the study/retention record (Epoch XI).

XII composes these; the only new machinery is the reflection *cycle* and the room's writer
discipline.

## The reflection room

A reserved room, scope **`self-reflection`**:

- **Written only by the reflection pipeline.** Not by chat, not by study cycles, not by the
  operator. (Authority enforced at the write path; the operator can still *review* — browse,
  supersede, restore — through the ordinary ADR 0022 surfaces, but authoring self-observations is
  the runtime's alone. The operator curates the mirror; they do not write in it.)
- Contents are **self-observations** (`kind="self_observation"`): first-person records of what the
  runtime did, learned, got wrong, and how it changed.
- The room is the **sole source for future identity consolidation** (XI-C machinery with
  subject=self-reflection): the identity adapter distills who the runtime has *become*. Weight-ward
  movement thus stays double-gated — reviewable room + ADR 0024 approval gate.

## The reflection cycle

Deterministic orchestration, operator-invoked (`POST /system/reflection/cycles`), later schedulable
as reviewed maintenance:

1. **Digest (deterministic, no LLM).** Read a bounded window of the runtime's own records —
   conversations, corrections detected, study cycles and scores, retention deltas, approvals
   decided, supersessions reviewed — and compute a factual activity digest. Pure code; every number
   traceable to a store.
2. **Compose (the runtime's voice).** The active model writes a short first-person reflection *from
   the digest only* (prompt carries the digest verbatim; the composition rule is **no ungrounded
   self-narrative** — the digest is attached to the observation as provenance, so a reviewer can
   always compare what it said about itself with what actually happened).
3. **Record.** The observation lands in `self-reflection` with the digest, window, and model
   recorded. One auditable cycle record (`reflection_cycles` store), same pattern as study cycles.
4. **Review.** Ordinary surfaces: browsable, supersedable (a later observation may declare an
   earlier one outgrown — the existing declared-change machinery), restorable, consolidatable.

## Honesty rules

- **Grounded composition:** every observation carries its digest; observations that assert activity
  absent from the digest are reviewable lies — the operator can supersede them.
- **No prescriptions:** the cycle never writes "you should be X"; it records what was. Personality
  emerges from accumulated observation, per the charter's self-authored pillar.
- **Measured like everything else:** cycle records carry counts and windows; the room's growth and
  its supersession history *are* the identity curve.

## Milestones

- **XII-A — The Mirror (targets 0.5.0):** the digest, the reflection cycle, the reserved room with
  writer discipline, REST surface (`/system/reflection/*`), cycle records, hermetic tests, and the
  first real reflection cycles over the epoch's actual history (this project's own record becomes
  its first self-observations — it has quite a week to reflect on).
- **XII-B — The Considered Self:** scheduled cycles as reviewed maintenance; observation
  supersession patterns ("outgrown" declarations); identity-consolidation dry run — assembling (not
  training) the first identity distillation candidate from the room via the ADR 0024 gate.

## Out of scope for XII

Autonomous scheduling without operator-set cadence; any personality *prescription* mechanism;
training an identity adapter (assembly only in XII-B — the run itself waits until the room has
months of material; a self distilled from a week would be a caricature).

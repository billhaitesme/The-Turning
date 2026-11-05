# omega-arc-architecture — curriculum revisions

An audit trail of changes to this subject's lessons/quizzes, so edits are transparent and never a
silent way to "make it pass." Each entry: what failed, the evidence, the fix, and the verified result.

## 2026-11-04 — fix lesson-1's daily first-attempt failures (diagnosed from the model's actual answers)

**Why:** every school day since reinforcement began, `lesson-1-identity-and-principles` failed its
first spaced re-quiz at comprehension 0.6667 and passed only on retry (fail/fail/pass on 11-03 and
11-04, identical pattern). Pulled the stored `answer_preview`s before touching anything. Finding:
**brittle keyword keys + one ambiguous question + sampling noise — not a comprehension wall.** The
model's answers were substantively correct.

### Fix 1 — q2 (brittle key)
- Q (unchanged): "Who may change the active language model, and how?"
- Model answered: *"Only the **operator** can change the active language model through **explicit
  action**."* — correct, and exactly the taught fact.
- Was marked wrong because the first OR-group demanded the literal phrase "model lock" or
  "explicit operator"; the model's phrasing "operator … explicit action" satisfies neither.
- **Before:** `[["model lock","explicit operator"], ["operator action","operator"]]`
- **After:** `[["model lock","explicit operator","explicit action"], ["operator action","operator"]]`
- Rationale: "explicit action" is the same fact in the words the question invites. Key fix only.

### Fix 2 — q3 (ambiguous question)
- Q before: "What owns state and persistence in OMEGA-ARC?"
- Model answered: *"The long-term memory of OMEGA-ARC is stored in a single SQLite store…"* — a
  reasonable reading ("what owns persistence" → the storage), but not the principle the item tests
  (runtime owns state; the model is stateless).
- **After Q:** "Which owns state and persistence in OMEGA-ARC — the deterministic runtime or the
  language model?" with `answer_expect [["deterministic runtime","the runtime"]]` (recall `expect`
  unchanged).
- Rationale: reframe so the taught principle is the direct answer (same approach as the 2026-08-23
  command-console fix 2). Lesson text unchanged.

### Fix 3 — study-seat sampling noise (code, not curriculum)
- The same lesson with the same retrieved notes (ranks 1–3, all inside the 4 notes handed to the
  model) failed twice and passed on the third attempt within eight minutes — the study seat was
  answering at Ollama's default temperature, so pass/fail varied by sampling luck.
- `study_answer` now pins `temperature` via `OLLAMA_STUDY_TEMPERATURE` (default 0). Grading was
  already deterministic (ADR 0013); now the answers are too. The 0.8 bar is unchanged.

**Verified:** real re-runs post-fix recorded in study_cycles.json (see cycles of 2026-11-05 UTC).

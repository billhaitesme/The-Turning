# omega-arc-command-console — curriculum revisions

An audit trail of changes to this subject's lessons/quizzes, so edits are transparent and never a
silent way to "make it pass." Each entry: what failed, the evidence, the fix, and the verified result.

## 2026-08-23 — fix three failing items (diagnosed from the model's actual answers)

**Why:** across the 08-20→08-22 school days, console-1 kept regressing (0.5–0.75) and console-3 never
passed (plateau 0.71–0.79, just under the 0.8 bar). Pulled the model's real answers (the grader stores
`answer_preview`) before touching anything. Finding: **not a comprehension wall — brittle keyword keys
+ two authoring gaps of mine.** The model's answers were largely correct.

### Fix 1 — console-1 q4 (bad quiz key)
- Q (unchanged): "What does the console add to the runtime's authority?"
- Model answered: *"The console adds no new authority; it allows the operator to initiate a bounded
  runtime command…"* — correct.
- Was marked wrong because `answer_expect` demanded a **second, unrelated** fact the question doesn't
  ask for.
- **Before:** `[["no new authority","adds no"], ["pipeline","recorded","deterministic"]]`
- **After:** `[["no new authority","adds no","no bypass"]]`
- Rationale: the question asks only what it adds to authority = "no new authority." Legitimate key fix.

### Fix 2 — console-1 q1 (question framing)
- Model hedged ("the notes don't specify what the operator did before…"), never landing on "initiate."
- **Before Q:** "What does the command console let the operator do that observing and approving did not?"
- **After Q:** "Beyond observing and approving, what new thing does the command console let the operator do?"
- **Key before:** `[["initiate"], ["command","action"]]` → **after:** `[["initiate","start","begin","issue"], ["command","action"]]`
- Rationale: rephrase so "initiate a command" is the direct answer; add synonyms. Lesson text unchanged.

### Fix 3 — console-3 q4 (two real defects: retrieval + a question demanding what the lesson didn't give)
- Model answered: *"…the command can never run. There is no specific example command provided in the
  notes."* — and it was **right that the lesson never named an example**; it only described one. This
  item also failed *recall* (the "Model Lock and output fidelity" chunk wasn't being retrieved).
- **Lesson-3 edit:** the forbidden paragraph now names the example explicitly —
  added: *"The forbidden command in the registry is change_conversational_routing — it is listed only
  so the boundary stays visible, and it can never run."*
- **Before Q:** "What does the forbidden gate protect, and give the example command?"
- **After Q:** "What does the forbidden gate protect, and which registry command is forbidden?"
- **Key before:** `[["model lock"], ["output fidelity","rewrite","which model answers","routing"]]`
  → **after:** `[["model lock","output fidelity"], ["change_conversational_routing","conversational routing","routing","which model answers","rewrite"]]`
- Rationale: make the lesson actually contain the named example, and let the reworded question retrieve
  the Model-Lock chunk. Required clearing the 4 stale lesson-3 chunks from the room (`memories` table,
  scope `omega-arc-command-console`) so the edited text re-ingests — ingestion dedupes on source PATH,
  not content, so a content edit alone would have tested stale memory.

### Verification (real re-runs, 12B study seat, 0.8 threshold unchanged)
- **console-1-its-hands:** 0.5/0.75 → **1.0 (4/4)**.
- **console-3-broadening-by-risk:** 0.7857 → **0.9286 (13/14; own section 5/5)**. The single miss was
  `console-1:q2` inside console-3's review section — model answer-variance (it answered that question
  correctly when console-1 ran standalone), not a key defect.
- console-2 was already solid and unchanged.

**Not done / not gamed:** the 0.8 pass threshold was not lowered; no keyword-stuffing to force a pass;
lesson prose changed only where the lesson genuinely lacked the named example (lesson-3). Deeper note:
the school grader is deterministic keyword-matching by design (ADR 0013 — the model never grades
itself), so correct-in-other-words answers can still miss; careful key authoring is the mitigation.

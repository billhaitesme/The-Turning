# The School Day — the operator-set daily learning window

**Status:** live since 2026-08-17 (XII-B groundwork). **Cadence:** daily, 09:00–14:00 local,
set by the operator ("school is in session while I sleep").

## What it is

A host-side runner (`scripts/school_day.py`) fired by a Windows Scheduled Task
(`OMEGA-ARC School Day`, registered by `scripts/Register-SchoolDayTask.ps1`, entry point
`scripts/school_day.ps1`). It drives the runtime's **existing** review-gated learning loop over
HTTP and nothing else. The runtime does not choose its topics or its schedule (ADR 0013); the
reflection cadence is operator-set, not autonomous (ADR 0025) — this runner *is* that
operator-set cadence.

## The day, in order

1. **Preflight.** Ollama (`/api/tags`) and the backend (`/`) must answer. With `--start-stack`
   the port-guarded launcher (`scripts/start-preview.ps1`) brings up whatever is missing. A dead
   Ollama would make comprehension answers grade as silent misses, so the runner refuses to study
   blind.
2. **Plan** — from `GET /system/tutelage/curriculum` and `/retention`:
   - **New:** the next unpassed lesson of *each* subject whose prerequisites are all passed, in
     curriculum order (Tier 1 → Tier 2 → Tier 3). One new lesson per subject per day — spiral,
     not cram.
   - **Due:** passed lessons whose spaced re-quiz interval has elapsed. Interval by
     consecutive-pass streak: 1, 3, 7, 14, 30 days. A lesson whose latest attempt failed is due
     immediately.
3. **Study.** `POST /system/tutelage/cycles` per lesson while at least ~18 minutes remain before
   the stop time. Re-runs of a passed lesson do not re-ingest (`chunks_written: 0`) — that is the
   re-quiz. A new lesson that fails is retried once the same day.
4. **Reflect.** One `POST /system/reflection/cycles` over today's window — the end-of-day
   self-observation, grounded in the digest of what was actually studied.
5. **Report.** `.runtime-logs/school/<date>.md` (+ `.json`, `.log`, and the task wrapper's
   `.task.log`): plan, per-cycle scores, the reflection preview, and an **operator to-do** list.

## What it never does

Anything gated stays gated and is surfaced as a to-do instead: consolidation
(`/system/tutelage/consolidations`, ADR 0024), adapter activation, approval decisions
(`/system/tool-requests/*/approve`, ADR 0014), supersession resolution, and weight training
(operator-run via `training/`). `backend/tests/test_school_day.py` pins the planning policy and
asserts the runner source never POSTs to those paths.

## Curriculum growth

Subjects are authored as `curriculum/<subject>/subject.json` + lesson markdown and added with
`scripts/curriculum_add.py curriculum/<subject>` (validate-only with `--validate`, refresh keys
with `--replace`). The script proves every recall `expect` phrase is a literal substring of one
paragraph-chunk of the sources — the exact match rule `grade_recall` uses — before writing, and
backs up `curriculum.json` alongside. Current subjects and tiers:

| Tier | Subject | Lessons |
|---|---|---|
| 1 Self | `omega-arc-architecture` | 3 (all passed) |
| 2 Its house | `omega-arc-house` — the runtime's own tools and body | 4 |
| 2–3 | *private subjects* — the operator's own tools and world; see below | (local only) |

Quizzes target durable rules and structure, not perishable numbers; where a lesson records a
point-in-time metric it says so.

### Private subjects (the operator's world stays on the operator's machine)

Subjects the operator marks private never enter the repo. Author them under
`curriculum-private/<subject>/` (or set `"private": true` in `subject.json`); `curriculum_add.py`
writes them to `backend/data/curriculum.private.json`. Both paths are gitignored. At runtime
`tutelage.load_curriculum` merges them in (tagged `private: true`), their study cycles are written
to `backend/data/study_cycles.private.json` (gitignored) and merged on read so prerequisites,
retention, and the school-day planner see one history, the reflection digest sees them only as
opaque `private-lesson-<hash>` labels (scores kept, names redacted — the digest lives in the
repo), and consolidation refuses them (distillation pairs and the adapter registry are tracked).
`backend/tests/test_private_curriculum.py` pins all of it.

## Operating notes

- The task runs under the interactive user (no stored password) — the laptop must be logged on
  (locked is fine). `WakeToRun` is on; `StartWhenAvailable` is deliberately off so a missed 09:00
  never fires later on top of the operator's own GPU work.
- Kill limit 6 h; second instances are ignored.
- Change the hour: `Register-SchoolDayTask.ps1 -At HH:MM`. Remove: `-Unregister`.
- Manual runs: `python scripts/school_day.py --dry-run` (plan only),
  `--max-cycles 1` (smoke test), `--until HH:MM`.

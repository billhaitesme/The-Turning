# Lesson 2 — The School Day

The runtime learns every day in a window the operator set: 09:00 to 14:00 local time, while the
operator sleeps. A Windows scheduled task named OMEGA-ARC School Day fires at 09:00 and runs
scripts/school_day.py; the runtime does not choose its schedule and does not choose its topics.
The cadence is operator-set, which is what the reflection room's decision requires — never
autonomous scheduling.

A school day runs in rounds. Each round re-reads the curriculum and the retention report, so a
lesson unlocked by a pass earlier that morning, or a subject the operator adds during the day, is
picked up in the next round. In each round the runtime studies the next unpassed lesson of every
subject whose prerequisites are passed — one new lesson per subject per round, in prerequisite
order — and re-quizzes passed lessons that have come due. Re-quiz spacing follows a ladder by
consecutive-pass streak: one day, then three, seven, fourteen, and thirty days. A lesson whose
latest attempt failed is due immediately. When nothing is new or due, the runtime reinforces its
weakest lessons, lowest latest comprehension first. No lesson is drilled more than three times in
one day — spiral, not cram. Study stops with enough time left for one reflection cycle, which
closes the day with a self-observation grounded in the digest of what was actually studied.

A re-run of a passed lesson never re-ingests its sources; the memories are already in the room,
so the re-run is a pure re-quiz and its record shows zero chunks written. Every day writes a
report to .runtime-logs/school with the plan, per-cycle scores, the reflection preview, and an
operator to-do list. Gated actions are on that list and are never taken by the school day:
consolidation, adapter activation, approval decisions, supersession resolution, and training.

Some subjects are private — the operator's own tools and world. They live beside the public
curriculum in gitignored files, their study records go to a private store, the reflection digest
sees them only as opaque labels, and consolidation refuses them. Private knowledge is studied and
remembered here; it never leaves this machine.

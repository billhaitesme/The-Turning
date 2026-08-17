"""School-day planner (scripts/school_day.py): pure planning logic, no I/O.

The runner is the operator-set daily cadence for the study loop. These tests pin the
policy: one new lesson per subject per day in prerequisite order, spaced re-quizzes by
pass streak, failed lessons re-queued, and gated actions surfaced — never taken."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "school_day.py"
spec = importlib.util.spec_from_file_location("school_day", SCRIPT)
school_day = importlib.util.module_from_spec(spec)
spec.loader.exec_module(school_day)  # type: ignore[union-attr]

NOW = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


CURRICULUM = {"subjects": [
    {"id": "s1", "lessons": [
        {"id": "a1", "prerequisites": []},
        {"id": "a2", "prerequisites": ["a1"]},
        {"id": "a3", "prerequisites": ["a2"]},
    ]},
    {"id": "s2", "lessons": [
        {"id": "b1", "prerequisites": []},
        {"id": "b2", "prerequisites": ["b1"]},
    ]},
]}


def _hist(*statuses_ages):
    return [{"status": s, "finished_at": _iso(age)} for s, age in statuses_ages]


class PlanDayTests(unittest.TestCase):
    def test_one_new_lesson_per_subject_in_prerequisite_order(self):
        plan = school_day.plan_day(CURRICULUM, passed=[], retention=[], now=NOW)
        self.assertEqual([i["lesson_id"] for i in plan["new"]], ["a1", "b1"])
        self.assertEqual(plan["due"], [])

    def test_next_new_lesson_requires_prerequisites_passed(self):
        retention = [{"lesson_id": "a1", "history": _hist(("passed", 0.5))}]
        plan = school_day.plan_day(CURRICULUM, passed=["a1"], retention=retention, now=NOW)
        self.assertEqual([i["lesson_id"] for i in plan["new"]], ["a2", "b1"])
        # a1 passed half a day ago with streak 1 -> interval 1d -> not yet due
        self.assertEqual(plan["due"], [])

    def test_spaced_requiz_ladder_by_streak(self):
        # streak 1 -> 1 day; streak 2 -> 3 days; streak 3 -> 7 days
        retention = [
            {"lesson_id": "a1", "history": _hist(("passed", 2))},                       # streak 1, age 2d -> due
            {"lesson_id": "a2", "history": _hist(("passed", 5), ("passed", 2))},        # streak 2, age 2d -> not due
            {"lesson_id": "b1", "history": _hist(("passed", 30), ("passed", 20), ("passed", 8))},  # streak 3, 8d -> due
        ]
        plan = school_day.plan_day(CURRICULUM, passed=["a1", "a2", "b1"], retention=retention, now=NOW)
        self.assertEqual(sorted(i["lesson_id"] for i in plan["due"]), ["a1", "b1"])
        self.assertEqual([i["lesson_id"] for i in plan["new"]], ["a3", "b2"])

    def test_failed_latest_attempt_is_requeued_immediately(self):
        retention = [{"lesson_id": "a1", "history": _hist(("passed", 3), ("failed", 0.1))}]
        plan = school_day.plan_day(CURRICULUM, passed=["a1"], retention=retention, now=NOW)
        self.assertEqual([i["lesson_id"] for i in plan["due"]], ["a1"])
        self.assertIn("failed", plan["due"][0]["reason"])

    def test_streak_caps_at_last_rung(self):
        retention = [{"lesson_id": "a1", "history": _hist(*[("passed", 40 - i) for i in range(10)])}]
        plan = school_day.plan_day(CURRICULUM, passed=["a1"], retention=retention, now=NOW)
        # newest pass 31 days ago, interval capped at 30 -> due
        self.assertEqual([i["lesson_id"] for i in plan["due"]], ["a1"])
        self.assertIn("interval 30d", plan["due"][0]["reason"])


class OperatorTodoTests(unittest.TestCase):
    def test_completed_subject_without_active_adapter_is_surfaced_not_consolidated(self):
        todos = school_day.operator_todos(CURRICULUM, passed=["a1", "a2", "a3"], adapters={"adapters": []})
        self.assertEqual(len(todos), 1)
        self.assertIn("s1", todos[0])
        self.assertIn("operator approval", todos[0])

    def test_active_adapter_silences_the_todo(self):
        adapters = {"adapters": [{"subject_id": "s1", "status": "active"}]}
        todos = school_day.operator_todos(CURRICULUM, passed=["a1", "a2", "a3"], adapters=adapters)
        self.assertEqual(todos, [])

    def test_runner_never_calls_gated_endpoints(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("/consolidations", "/approve", "/adapters/", "supersession-candidates"):
            # allowed only inside comments/docstrings that explain the boundary — never as a request path
            for line in source.splitlines():
                if forbidden in line and "_post(" in line:
                    self.fail(f"school_day.py must not POST to {forbidden}: {line.strip()}")


if __name__ == "__main__":
    unittest.main()


class FillRoundTests(unittest.TestCase):
    def test_reinforces_weakest_first_and_respects_daily_cap(self):
        retention = [
            {"lesson_id": "a1", "history": _hist(("passed", 1))},
            {"lesson_id": "a2", "history": [{"status": "passed", "finished_at": _iso(1), "comprehension": 0.8}]},
            {"lesson_id": "b1", "history": [{"status": "passed", "finished_at": _iso(2), "comprehension": 0.6}]},
        ]
        counts = {"b1": school_day.MAX_CYCLES_PER_LESSON_PER_DAY}  # b1 already capped today
        queue = school_day.fill_round(CURRICULUM, ["a1", "a2", "b1"], retention, counts)
        # b1 (weakest) is capped, so a2 (0.8) comes before a1 (no comprehension recorded -> 1.0)
        self.assertEqual([i["lesson_id"] for i in queue], ["a2", "a1"])
        self.assertIn("reinforcement", queue[0]["reason"])

    def test_unpassed_lessons_are_never_reinforced(self):
        queue = school_day.fill_round(CURRICULUM, ["a1"], [{"lesson_id": "a1", "history": _hist(("passed", 1))}], {})
        self.assertEqual([i["lesson_id"] for i in queue], ["a1"])

    def test_empty_when_everything_is_capped(self):
        counts = {"a1": 3}
        self.assertEqual(school_day.fill_round(CURRICULUM, ["a1"], [{"lesson_id": "a1", "history": _hist(("passed", 1))}], counts), [])


class FetchStateTests(unittest.TestCase):
    def test_unwraps_envelopes_identically_for_first_plan_and_replans(self):
        # 2026-08-17: the round-2 re-plan read the raw {"retention": [...]} envelope and died with
        # TypeError mid-school-day. fetch_state is now the single reader for both.
        responses = {
            "/system/tutelage/curriculum": {"curriculum": CURRICULUM, "passed_lessons": ["a1"]},
            "/system/tutelage/retention": {"retention": [{"lesson_id": "a1", "history": _hist(("passed", 2))}]},
            "/system/tutelage/adapters": {"adapters": []},
        }
        original = school_day._get
        school_day._get = lambda path, timeout=30: responses[path]
        try:
            curriculum, passed, retention, adapters = school_day.fetch_state()
        finally:
            school_day._get = original
        self.assertEqual(passed, ["a1"])
        self.assertIsInstance(retention, list)
        plan = school_day.plan_day(curriculum, passed, retention, NOW)  # must not raise
        self.assertEqual([i["lesson_id"] for i in plan["due"]], ["a1"])

import json
import tempfile
import unittest
from pathlib import Path

from services.plan_store import (
    archive_plan,
    empty_plan_store,
    find_active_plan_for_goal,
    get_plan,
    list_plans,
    load_plan_store,
    save_plan_store,
    supersede_plan,
    upsert_plan,
)


class PlanStoreTests(unittest.TestCase):
    def _sample_plan(self, plan_id: str = "plan-a", goal_id: str = "goal-a", status: str = "active"):
        return {
            "id": plan_id,
            "goal_id": goal_id,
            "title": "A plan",
            "status": status,
            "metadata": {"custom": {"retain": True}},
            "steps": [],
        }

    def test_missing_store_returns_empty_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plans.json"
            loaded = load_plan_store(path)
            self.assertEqual(loaded, empty_plan_store())

    def test_malformed_json_returns_empty_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plans.json"
            path.write_text("{oops", encoding="utf-8")
            loaded = load_plan_store(path)
            self.assertEqual(loaded, empty_plan_store())

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "plans.json"
            store = {"version": 1, "plans": [self._sample_plan()]}
            save_plan_store(store, path)
            loaded = load_plan_store(path)
            self.assertEqual(loaded["plans"][0]["id"], "plan-a")

    def test_plan_upsert_and_no_duplicate_id(self):
        store = empty_plan_store()
        store = upsert_plan(store, self._sample_plan())
        store = upsert_plan(store, self._sample_plan())
        self.assertEqual(len(store["plans"]), 1)

    def test_one_active_plan_per_goal(self):
        store = empty_plan_store()
        store = upsert_plan(store, self._sample_plan(plan_id="plan-1", goal_id="goal-a", status="active"))
        store = upsert_plan(store, self._sample_plan(plan_id="plan-2", goal_id="goal-a", status="active"))

        active = find_active_plan_for_goal(store, "goal-a")
        self.assertEqual(active["id"], "plan-2")

        archived = get_plan(store, "plan-1")
        self.assertEqual(archived["status"], "archived")

    def test_archive_plan(self):
        store = upsert_plan(empty_plan_store(), self._sample_plan())
        store = archive_plan(store, "plan-a")
        self.assertEqual(get_plan(store, "plan-a")["status"], "archived")

    def test_supersede_plan(self):
        store = upsert_plan(empty_plan_store(), self._sample_plan(plan_id="plan-old"))
        store = supersede_plan(
            store,
            old_plan_id="plan-old",
            new_plan=self._sample_plan(plan_id="plan-new", status="active"),
        )

        self.assertEqual(get_plan(store, "plan-old")["status"], "superseded")
        self.assertEqual(get_plan(store, "plan-old")["superseded_by"], "plan-new")
        self.assertEqual(get_plan(store, "plan-new")["supersedes"], "plan-old")

    def test_metadata_preserved(self):
        store = upsert_plan(empty_plan_store(), self._sample_plan())
        self.assertTrue(get_plan(store, "plan-a")["metadata"]["custom"]["retain"])

    def test_never_mutates_caller_owned_dict(self):
        store = empty_plan_store()
        plan = self._sample_plan()
        store = upsert_plan(store, plan)
        plan["status"] = "archived"
        self.assertEqual(get_plan(store, "plan-a")["status"], "active")


if __name__ == "__main__":
    unittest.main()

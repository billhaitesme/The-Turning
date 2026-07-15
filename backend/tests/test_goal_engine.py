import json
import tempfile
import unittest
from pathlib import Path

from services.goal_engine import (
    apply_goal_candidates,
    load_goal_store,
    save_goal_store,
    update_goal_progress,
    upsert_goal,
)


class GoalEngineTests(unittest.TestCase):
    def test_load_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "goals.json"
            store = load_goal_store(path)
            self.assertEqual(store["goals"], [])

    def test_create_goal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "goals.json"
            store = upsert_goal({}, title="Build OMEGA-ARC")
            save_goal_store(store, path)
            reloaded = load_goal_store(path)
            self.assertEqual(len(reloaded["goals"]), 1)

    def test_update_same_goal_without_duplication(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "goals.json"
            store = upsert_goal({}, title="Build OMEGA-ARC")
            store = upsert_goal(store, title="Build OMEGA-ARC")
            save_goal_store(store, path)
            reloaded = load_goal_store(path)
            self.assertEqual(len(reloaded["goals"]), 1)

    def test_progress_clamps_and_completes(self):
        store = upsert_goal({}, title="Build OMEGA-ARC")
        updated = update_goal_progress(store, goal_id="goal-build-omega-arc", progress=1.5)
        self.assertEqual(updated["goals"][0]["progress"], 1.0)
        self.assertEqual(updated["goals"][0]["status"], "completed")

    def test_apply_candidates(self):
        store = apply_goal_candidates({}, [{"value": "Add vision routing", "confidence": 1.0, "importance": 0.9, "requires_confirmation": False}])
        self.assertEqual(store["goals"][0]["title"], "Add vision routing")

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "goals.json"
            store = {"version": 1, "goals": []}
            save_goal_store(store, path)
            reloaded = load_goal_store(path)
            self.assertEqual(reloaded["goals"], [])


if __name__ == "__main__":
    unittest.main()

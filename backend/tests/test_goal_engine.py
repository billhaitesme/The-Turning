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
        self.assertEqual(
            store["goals"][0]["dependencies"],
            [
                "vision_model_selected",
                "vision_model_loaded",
                "vision_model_healthy",
                "vision_router_configured",
                "vision_routing_verified",
            ],
        )
        self.assertEqual(store["goals"][0]["completion_evidence_key"], "vision_routing_ready")

    def test_build_project_candidate_is_normalized(self):
        store = apply_goal_candidates(
            {},
            [{"key": "build_project", "value": "OMEGA-ARC", "confidence": 1.0, "importance": 0.9, "requires_confirmation": False}],
        )
        self.assertEqual(store["goals"][0]["title"], "Build OMEGA-ARC")

    def test_build_project_candidate_never_stores_vague_project_only_title(self):
        store = apply_goal_candidates(
            {},
            [{"key": "build_project", "value": "OMEGA-ARC", "confidence": 1.0, "importance": 0.9, "requires_confirmation": False}],
        )
        self.assertNotEqual(store["goals"][0]["title"], "OMEGA-ARC")

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "goals.json"
            store = {"version": 1, "goals": []}
            save_goal_store(store, path)
            reloaded = load_goal_store(path)
            self.assertEqual(reloaded["goals"], [])


if __name__ == "__main__":
    unittest.main()

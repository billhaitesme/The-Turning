import tempfile
import unittest
from pathlib import Path

from services.decision_store import (
    empty_decision_store,
    get_decision,
    load_decision_store,
    save_decision_store,
    supersede_decision_in_store,
    upsert_decision,
)


class DecisionStoreTests(unittest.TestCase):
    def _decision(self, decision_id: str = "decision-a", status: str = "active"):
        return {
            "id": decision_id,
            "title": "Decision A",
            "decision": "Use model A",
            "status": status,
            "reason": "Configured and available.",
            "evidence_keys": ["vision_model_selected"],
        }

    def test_missing_store_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.json"
            self.assertEqual(load_decision_store(path), empty_decision_store())

    def test_malformed_store_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.json"
            path.write_text("{", encoding="utf-8")
            self.assertEqual(load_decision_store(path), empty_decision_store())

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.json"
            store = {"version": 1, "decisions": [self._decision()]}
            save_decision_store(store, path)
            loaded = load_decision_store(path)
            self.assertEqual(loaded["decisions"][0]["id"], "decision-a")

    def test_upsert_and_supersede(self):
        store = upsert_decision(empty_decision_store(), self._decision(decision_id="old"))
        store = supersede_decision_in_store(
            store,
            old_decision_id="old",
            new_decision=self._decision(decision_id="new"),
        )
        self.assertEqual(get_decision(store, "old")["status"], "superseded")
        self.assertEqual(get_decision(store, "new")["supersedes"], "old")


if __name__ == "__main__":
    unittest.main()

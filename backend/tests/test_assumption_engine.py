import tempfile
import unittest
from pathlib import Path

from services.assumption_engine import (
    create_assumption,
    invalidate_assumption,
    list_assumptions,
    load_assumption_store,
    save_assumption_store,
    upsert_assumption,
    verify_assumption,
)


class AssumptionEngineTests(unittest.TestCase):
    def test_assumption_lifecycle(self):
        store = {"version": 1, "assumptions": []}
        assumption = create_assumption(
            assumption_id="assumption_gpu_memory",
            statement="GPU memory is sufficient.",
            status="assumed",
            confidence=0.4,
        )
        store = upsert_assumption(store, assumption)
        self.assertEqual(list_assumptions(store, status="assumed")[0]["id"], "assumption_gpu_memory")

        store = verify_assumption(store, assumption_id="assumption_gpu_memory", supporting_evidence=["gpu_probe_verified"])
        verified = list_assumptions(store, status="known")[0]
        self.assertEqual(verified["status"], "known")
        self.assertIn("gpu_probe_verified", verified["supporting_evidence"])

        store = invalidate_assumption(store, assumption_id="assumption_gpu_memory", invalidated_by=["gpu_probe_failed"])
        invalid = list_assumptions(store, status="invalidated")[0]
        self.assertIn("gpu_probe_failed", invalid["invalidated_by"])

    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assumptions.json"
            store = {"version": 1, "assumptions": []}
            store = upsert_assumption(
                store,
                create_assumption(
                    assumption_id="a1",
                    statement="Test assumption",
                    status="assumed",
                ),
            )
            save_assumption_store(store, path=path)
            loaded = load_assumption_store(path=path)
            self.assertEqual(len(loaded["assumptions"]), 1)


if __name__ == "__main__":
    unittest.main()

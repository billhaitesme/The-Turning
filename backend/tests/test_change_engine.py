import unittest

from services.change_engine import add_dependency_impacts, compare_evidence_snapshots


class ChangeEngineTests(unittest.TestCase):
    def test_created_record(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {}},
            {"version": 1, "records": {"backend_port": {"key": "backend_port", "value": 8002, "state_type": "configured"}}},
        )
        self.assertEqual(changes[0]["change_type"], "created")

    def test_removed_record(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {"backend_port": {"key": "backend_port", "value": 8001, "state_type": "configured"}}},
            {"version": 1, "records": {}},
        )
        self.assertEqual(changes[0]["change_type"], "removed")

    def test_value_changed(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {"backend_port": {"key": "backend_port", "value": 8001, "state_type": "configured"}}},
            {"version": 1, "records": {"backend_port": {"key": "backend_port", "value": 8002, "state_type": "configured"}}},
        )
        self.assertEqual(changes[0]["change_type"], "value_changed")

    def test_state_promoted(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "observed"}}},
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "verified"}}},
        )
        self.assertEqual(changes[0]["change_type"], "promoted")

    def test_state_demoted(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "verified"}}},
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "observed"}}},
        )
        self.assertEqual(changes[0]["change_type"], "demoted")

    def test_invalidated(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "verified"}}},
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": None, "state_type": "invalidated"}}},
        )
        self.assertEqual(changes[0]["change_type"], "invalidated")

    def test_expired(self):
        changes = compare_evidence_snapshots(
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "verified"}}},
            {"version": 1, "records": {"backend_health": {"key": "backend_health", "value": True, "state_type": "expired"}}},
        )
        self.assertEqual(changes[0]["change_type"], "expired")

    def test_dependency_impacts_added(self):
        changes = [{"key": "backend_port", "change_type": "value_changed", "before": 8001, "after": 8002, "impact": []}]
        updated = add_dependency_impacts(changes, {"backend_port": ["backend_url", "backend_health"]})
        self.assertIn("backend_url", updated[0]["impact"])
        self.assertIn("backend_health", updated[0]["impact"])


if __name__ == "__main__":
    unittest.main()

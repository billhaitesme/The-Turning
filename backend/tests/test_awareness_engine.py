import unittest

from awareness_engine import (
    apply_backend_health_check,
    apply_backend_port_statement,
    build_awareness_snapshot,
)


class AwarenessEngineTests(unittest.TestCase):
    def test_port_statement_does_not_imply_online(self):
        state = apply_backend_port_statement({}, "The backend runs on port 8002.")
        self.assertEqual(state["backend_health"]["status"], "unknown")

    def test_port_statement_does_not_imply_offline(self):
        state = apply_backend_port_statement({}, "The backend runs on port 8002.")
        self.assertNotEqual(state["backend_health"]["status"], "offline")

    def test_changing_port_invalidates_previous_health(self):
        state = {"backend_port": 8001, "backend_health": {"status": "online", "checked_url": "http://127.0.0.1:8001", "source": "health_check"}}
        updated = apply_backend_port_statement(state, "The backend runs on port 8002.")
        self.assertEqual(updated["backend_health"]["status"], "unknown")

    def test_successful_health_check_establishes_online(self):
        state = apply_backend_health_check(
            {"backend_port": 8001},
            port=8001,
            success=True,
        )
        self.assertEqual(state["backend_health"]["status"], "online")

    def test_failed_health_check_establishes_offline(self):
        state = apply_backend_health_check(
            {"backend_port": 8001},
            port=8001,
            success=False,
        )
        self.assertEqual(state["backend_health"]["status"], "offline")

    def test_snapshot_uses_separate_configuration_and_health(self):
        snapshot = build_awareness_snapshot(
            backend_url="http://127.0.0.1:8001/",
            configured_backend_port=8001,
            backend_health_state={
                "backend_port": 8001,
                "backend_health": {
                    "status": "unknown",
                    "checked_url": "http://127.0.0.1:8001",
                    "source": "health_check",
                },
            },
        )
        self.assertEqual(snapshot.backend_health["status"], "unknown")


if __name__ == "__main__":
    unittest.main()

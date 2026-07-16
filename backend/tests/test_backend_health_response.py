import unittest

from services.backend_health_response import (
    build_backend_health_response,
    build_health_check_execution_response,
    is_backend_health_query,
    is_health_check_execution_request,
)


class BackendHealthResponseTests(unittest.TestCase):
    def test_detects_backend_health_question(self):
        self.assertTrue(is_backend_health_query("Is the backend online?"))
        self.assertTrue(is_backend_health_query("Is the backend online now?"))
        self.assertFalse(is_backend_health_query("What do you currently know?"))

    def test_unknown_health_response_uses_configured_port_without_claiming_online(self):
        text = build_backend_health_response(
            {
                "version": 1,
                "facts": {
                    "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
                },
            }
        )
        self.assertIn("configured to use port 8002", text)
        self.assertIn("not been independently verified", text)

    def test_user_declared_online_response_remains_unverified(self):
        text = build_backend_health_response(
            {
                "version": 1,
                "facts": {
                    "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
                    "backend_health": {"value": "online", "state_type": "declared", "source": "user"},
                },
            }
        )
        self.assertIn("reported as online", text)
        self.assertIn("not independently verified", text)

    def test_verified_online_response_for_matching_endpoint(self):
        text = build_backend_health_response(
            {
                "version": 1,
                "facts": {
                    "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
                    "backend_health": {
                        "value": "online",
                        "state_type": "verified",
                        "source": "health_check",
                        "checked_url": "http://127.0.0.1:8002",
                        "checked_at": "2026-07-15T00:00:00+00:00",
                    },
                },
            }
        )
        self.assertEqual(text, "The backend is verified online at the currently configured endpoint.")

    def test_detects_health_check_execution_requests_with_common_typo(self):
        self.assertTrue(is_health_check_execution_request("Can you perform the health check?"))
        self.assertTrue(is_health_check_execution_request("can you preform the health check?"))
        self.assertFalse(is_health_check_execution_request("Is the backend online?"))

    def test_health_check_execution_response_is_capability_safe(self):
        text = build_health_check_execution_response(
            {
                "version": 1,
                "facts": {
                    "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
                },
            }
        )
        self.assertIn("cannot run a trusted health-check adapter from this chat", text)
        self.assertIn("http://127.0.0.1:8002", text)


if __name__ == "__main__":
    unittest.main()

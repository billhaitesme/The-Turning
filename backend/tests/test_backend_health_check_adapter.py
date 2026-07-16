import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

from services.adapters.backend_health_check import BACKEND_HEALTH_CHECK_DESCRIPTOR, BackendHealthCheckAdapter


class BackendHealthCheckAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = BackendHealthCheckAdapter()

    def test_descriptor_validates(self):
        self.assertEqual(BACKEND_HEALTH_CHECK_DESCRIPTOR["name"], "backend_health_check")
        self.assertTrue(BACKEND_HEALTH_CHECK_DESCRIPTOR["requires_approval"])
        self.assertEqual(BACKEND_HEALTH_CHECK_DESCRIPTOR["allowed_scopes"], ["localhost"])
        self.assertEqual(BACKEND_HEALTH_CHECK_DESCRIPTOR["input_schema"]["required"], ["port"])

    def test_validate_arguments_rejects_invalid_port(self):
        with self.assertRaises(ValueError):
            self.adapter.validate_arguments({"port": 0})
        with self.assertRaises(ValueError):
            self.adapter.validate_arguments({"port": 70000})

    def test_dry_run_constructs_localhost_urls_only(self):
        output = self.adapter.dry_run({"port": 8001})
        self.assertTrue(output["safe"])
        self.assertEqual(
            output["would_check"],
            ["http://127.0.0.1:8001/health", "http://127.0.0.1:8001/system/status", "http://127.0.0.1:8001/"],
        )

    def test_execute_success_reports_200_and_checked_url(self):
        response = MagicMock()
        response.status = 200
        response.getcode.return_value = 200
        opener = Mock()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = response
        context_manager.__exit__.return_value = False
        opener.open.return_value = context_manager
        with patch("services.adapters.backend_health_check.request.build_opener", return_value=opener):
            result = self.adapter.execute({"port": 8001})

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["checked_url"], "http://127.0.0.1:8001/health")
        self.assertGreaterEqual(result["latency_ms"], 0.0)

    def test_execute_connection_failure_returns_offline(self):
        opener = Mock()
        opener.open.side_effect = URLError("connection refused")
        with patch("services.adapters.backend_health_check.request.build_opener", return_value=opener):
            result = self.adapter.execute({"port": 8001})

        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])
        self.assertEqual(result["error"], "connection refused")

    def test_execute_http_500_returns_offline_and_status_code(self):
        http_error = HTTPError("http://127.0.0.1:8001/health", 500, "boom", hdrs=None, fp=None)
        opener = Mock()
        opener.open.side_effect = http_error
        with patch("services.adapters.backend_health_check.request.build_opener", return_value=opener):
            result = self.adapter.execute({"port": 8001})

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 500)
        self.assertEqual(result["error"], "HTTP 500")

    def test_execute_returns_the_first_candidate_url(self):
        response = MagicMock()
        response.status = 200
        response.getcode.return_value = 200
        opener = Mock()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = response
        context_manager.__exit__.return_value = False
        opener.open.return_value = context_manager
        with patch("services.adapters.backend_health_check.request.build_opener", return_value=opener):
            result = self.adapter.execute({"port": 8001})

        self.assertEqual(result["checked_url"], "http://127.0.0.1:8001/health")


if __name__ == "__main__":
    unittest.main()

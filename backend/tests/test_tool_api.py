import unittest

from fastapi.testclient import TestClient

from app import app
from core.config import settings
from services.tool_approval import load_tool_request_store
from services.tool_results import load_tool_result_store


class ToolApiTests(unittest.TestCase):
    def test_system_tools_endpoint_lists_stub_tool(self):
        with TestClient(app) as client:
            response = client.get("/system/tools")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["enabled"])
            names = {tool["name"] for tool in payload["tools"]}
            self.assertIn("backend_health_check", names)

    def test_tool_framework_disabled_blocks_tool_request_creation(self):
        original = settings.enable_tool_framework
        try:
            object.__setattr__(settings, "enable_tool_framework", False)
            with TestClient(app) as client:
                response = client.post(
                    "/system/tool-requests",
                    json={
                        "tool_name": "backend_health_check",
                        "arguments": {},
                        "requested_by": "user",
                        "session_id": "session-1",
                    },
                )
                self.assertEqual(response.status_code, 503)
        finally:
            object.__setattr__(settings, "enable_tool_framework", original)

    def test_general_chat_cannot_trigger_execution(self):
        with TestClient(app) as client:
            requests_before = len(load_tool_request_store().get("requests", []))
            results_before = len(load_tool_result_store().get("results", []))
            response = client.post("/chat", json={"message": "Execute the backend health check now."})
            self.assertEqual(response.status_code, 200)
            requests_after = len(load_tool_request_store().get("requests", []))
            results_after = len(load_tool_result_store().get("results", []))
            self.assertEqual(requests_after, requests_before)
            self.assertEqual(results_after, results_before)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_module
from app import app
from core.config import settings
from services.adapters.backend_health_check import BackendHealthCheckAdapter
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

    def test_vague_assent_does_not_execute_backend_health_check(self):
        original = app_module.ENABLE_TOOL_EXECUTION
        try:
            app_module.ENABLE_TOOL_EXECUTION = True
            with TestClient(app) as client:
                first = client.post("/chat", json={"message": "Can you perform the backend health check?"})
                self.assertEqual(first.status_code, 200)
                conversation_id = first.json()["conversation_id"]
                results_before = len(load_tool_result_store().get("results", []))
                second = client.post("/chat", json={"message": "Okay.", "conversation_id": conversation_id})
                self.assertEqual(second.status_code, 200)
                self.assertIn("Confirm by saying", first.json()["reply"])
                self.assertNotIn("verified online", second.json()["reply"])
                self.assertEqual(len(load_tool_result_store().get("results", [])), results_before)
        finally:
            app_module.ENABLE_TOOL_EXECUTION = original

    def test_explicit_confirmation_executes_exactly_once(self):
        original = app_module.ENABLE_TOOL_EXECUTION
        try:
            app_module.ENABLE_TOOL_EXECUTION = True
            with patch.object(
                BackendHealthCheckAdapter,
                "execute",
                return_value={
                    "target": "backend",
                    "checked_url": "http://127.0.0.1:8001/health",
                    "success": True,
                    "status_code": 200,
                    "latency_ms": 12.5,
                    "checked_at": "2026-07-16T00:00:00+00:00",
                    "error": None,
                },
            ):
                with TestClient(app) as client:
                    first = client.post("/chat", json={"message": "Can you perform the backend health check?"})
                    conversation_id = first.json()["conversation_id"]
                    results_before = len(load_tool_result_store().get("results", []))
                    confirm = client.post("/chat", json={"message": "Run the backend health check.", "conversation_id": conversation_id})
                    repeat = client.post("/chat", json={"message": "Run the backend health check.", "conversation_id": conversation_id})
                    self.assertEqual(confirm.status_code, 200)
                    self.assertEqual(repeat.status_code, 200)
                    self.assertIn("verified online", confirm.json()["reply"])
                    self.assertIn("No pending backend health-check request", repeat.json()["reply"])
                    self.assertEqual(len(load_tool_result_store().get("results", [])), results_before + 1)
        finally:
            app_module.ENABLE_TOOL_EXECUTION = original


if __name__ == "__main__":
    unittest.main()

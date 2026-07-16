import unittest

from services.tool_approval import approve_request, create_approval_request
from services.tool_contracts import ToolAdapter, build_tool_request
from services.tool_executor import execute_tool_request
from services.tool_registry import register_tool, unregister_tool


class FailingAdapter(ToolAdapter):
    def describe(self):
        return {"name": "failing_tool", "version": 1}

    def validate_arguments(self, arguments):
        return arguments

    def dry_run(self, arguments):
        return {"safe": True}

    def execute(self, arguments):
        raise RuntimeError("adapter exploded")


class SuccessfulAdapter(ToolAdapter):
    def describe(self):
        return {"name": "successful_tool", "version": 1}

    def validate_arguments(self, arguments):
        return arguments

    def dry_run(self, arguments):
        return {"safe": True, "would_do": True}

    def execute(self, arguments):
        return {"success": True, "output": {"checked": True}, "side_effects_observed": []}


class ToolExecutorTests(unittest.TestCase):
    def test_disabled_tool_cannot_execute(self):
        descriptor = {
            "name": "disabled_tool",
            "version": 1,
            "description": "Disabled tool.",
            "category": "diagnostic",
            "risk_level": "low",
            "requires_approval": False,
            "supports_dry_run": True,
            "input_schema": {},
            "output_schema": {},
            "side_effects": [],
            "allowed_scopes": ["localhost"],
            "enabled": False,
        }
        register_tool(descriptor, FailingAdapter())
        try:
            request = build_tool_request(tool_name="disabled_tool", arguments={}, requested_by="user", session_id="session-1")
            result = execute_tool_request(request=request, registry=__import__("services.tool_registry", fromlist=["get_tool"]), approval_store={"version": 1, "approvals": []})
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"]["code"], "tool_disabled")
        finally:
            unregister_tool("disabled_tool")

    def test_approval_required_tool_blocks_without_approval(self):
        request = build_tool_request(tool_name="backend_health_check", arguments={}, requested_by="user", session_id="session-1")
        result = execute_tool_request(request=request, registry=__import__("services.tool_registry", fromlist=["get_tool"]), approval_store={"version": 1, "approvals": []})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "approval_required")

    def test_approved_exact_request_may_execute(self):
        request_store = {"version": 1, "requests": []}
        approval_store = {"version": 1, "approvals": []}
        request = build_tool_request(tool_name="backend_health_check", arguments={}, requested_by="user", session_id="session-1")
        create_approval_request(request, request_store=request_store, approval_store=approval_store, ttl_seconds=300)
        approve_request(request["request_id"], approved_by="user", request_store=request_store, approval_store=approval_store)
        result = execute_tool_request(request=request, registry=__import__("services.tool_registry", fromlist=["get_tool"]), approval_store=approval_store)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "not_implemented")
        self.assertEqual(approval_store["approvals"][0]["status"], "revoked")

    def test_dry_run_works_without_approval_and_never_emits_verified_evidence(self):
        request = build_tool_request(tool_name="backend_health_check", arguments={}, requested_by="user", session_id="session-1")
        result = execute_tool_request(request=request, registry=__import__("services.tool_registry", fromlist=["get_tool"]), approval_store={"version": 1, "approvals": []}, dry_run=True)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["success"])
        self.assertEqual(result["evidence_candidates"], [])
        self.assertTrue(result["output"]["safe"])

    def test_adapter_exception_does_not_crash(self):
        descriptor = {
            "name": "failing_tool",
            "version": 1,
            "description": "Failing tool.",
            "category": "diagnostic",
            "risk_level": "low",
            "requires_approval": False,
            "supports_dry_run": True,
            "input_schema": {},
            "output_schema": {},
            "side_effects": [],
            "allowed_scopes": ["localhost"],
            "enabled": True,
        }
        register_tool(descriptor, FailingAdapter())
        try:
            request = build_tool_request(tool_name="failing_tool", arguments={}, requested_by="user", session_id="session-1")
            result = execute_tool_request(request=request, registry=__import__("services.tool_registry", fromlist=["get_tool"]), approval_store={"version": 1, "approvals": []})
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"]["code"], "adapter_exception")
        finally:
            unregister_tool("failing_tool")


if __name__ == "__main__":
    unittest.main()

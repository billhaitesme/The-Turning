import unittest
from datetime import datetime, timedelta, timezone

from services.tool_approval import (
    approve_request,
    consume_approval,
    create_approval_request,
    expire_approvals,
    validate_approval_for_request,
)
from services.tool_contracts import build_tool_request


class ToolApprovalTests(unittest.TestCase):
    def _request(self, arguments=None):
        return build_tool_request(
            tool_name="backend_health_check",
            arguments=arguments or {},
            requested_by="user",
            session_id="session-1",
        )

    def _stores(self):
        return {"version": 1, "requests": []}, {"version": 1, "approvals": []}

    def test_approval_is_bound_to_exact_request(self):
        request_store, approval_store = self._stores()
        request = self._request()
        approval = create_approval_request(request, request_store=request_store, approval_store=approval_store, ttl_seconds=300)
        approved = approve_request(request["request_id"], approved_by="user", request_store=request_store, approval_store=approval_store)
        self.assertEqual(approved["request_id"], approval["request_id"])
        validated = validate_approval_for_request(request, approval_store=approval_store)
        self.assertEqual(validated["status"], "approved")

    def test_changed_arguments_invalidate_approval(self):
        request_store, approval_store = self._stores()
        request = self._request()
        create_approval_request(request, request_store=request_store, approval_store=approval_store, ttl_seconds=300)
        approve_request(request["request_id"], approved_by="user", request_store=request_store, approval_store=approval_store)
        altered = self._request(arguments={"other": True})
        altered["request_id"] = request["request_id"]
        with self.assertRaises(ValueError):
            validate_approval_for_request(altered, approval_store=approval_store)

    def test_expired_approval_rejected(self):
        request_store, approval_store = self._stores()
        request = self._request()
        approval = create_approval_request(request, request_store=request_store, approval_store=approval_store, ttl_seconds=1)
        approve_request(request["request_id"], approved_by="user", request_store=request_store, approval_store=approval_store)
        approval_store["approvals"][0]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        expire_approvals(now=datetime.now(timezone.utc) + timedelta(seconds=10), request_store=request_store, approval_store=approval_store)
        with self.assertRaises(ValueError):
            validate_approval_for_request(request, approval_store=approval_store)

    def test_approval_cannot_be_reused(self):
        request_store, approval_store = self._stores()
        request = self._request()
        approval = create_approval_request(request, request_store=request_store, approval_store=approval_store, ttl_seconds=300)
        approve_request(request["request_id"], approved_by="user", request_store=request_store, approval_store=approval_store)
        consume_approval(approval["approval_id"], request_store=request_store, approval_store=approval_store)
        with self.assertRaises(ValueError):
            validate_approval_for_request(request, approval_store=approval_store)


if __name__ == "__main__":
    unittest.main()

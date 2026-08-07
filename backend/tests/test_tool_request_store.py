import json
import tempfile
import unittest
from pathlib import Path

from services.tool_contracts import build_tool_request
from services.tool_request_store import (
    empty_tool_request_store,
    get_tool_request,
    list_tool_requests,
    load_tool_request_store,
    save_tool_request_store,
    update_request_status,
    upsert_tool_request,
)


class ToolRequestStoreTests(unittest.TestCase):
    def test_malformed_store_returns_empty_valid_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool_requests.json"
            path.write_text("{not-json", encoding="utf-8")
            store = load_tool_request_store(path)
            self.assertEqual(store, empty_tool_request_store())

    def test_upsert_does_not_duplicate_request_ids(self):
        store = empty_tool_request_store()
        request = build_tool_request(tool_name="backend_health_check", arguments={"port": 8001}, requested_by="user", session_id="session-1")
        upsert_tool_request(request, store=store)
        upsert_tool_request({**request, "status": "awaiting_approval", "approval_id": "approval-1"}, store=store)
        self.assertEqual(len(store["requests"]), 1)
        self.assertEqual(get_tool_request(request["request_id"], store=store)["approval_id"], "approval-1")

    def test_update_request_status_preserves_metadata(self):
        store = empty_tool_request_store()
        request = build_tool_request(tool_name="backend_health_check", arguments={"port": 8001}, requested_by="user", session_id="session-1")
        request["approval_id"] = "approval-1"
        request["updated_at"] = "2026-07-16T00:00:00+00:00"
        upsert_tool_request(request, store=store)
        updated = update_request_status(request["request_id"], "approved", store=store, extra_fields={"approval_id": "approval-1"})
        self.assertEqual(updated["status"], "approved")
        self.assertEqual(updated["approval_id"], "approval-1")

    def test_save_and_reload_request_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool_requests.json"
            store = empty_tool_request_store()
            request = build_tool_request(tool_name="backend_health_check", arguments={"port": 8001}, requested_by="user", session_id="session-1")
            upsert_tool_request(request, store=store)
            save_tool_request_store(store, path)
            reloaded = load_tool_request_store(path)
            self.assertEqual(list_tool_requests(reloaded)[0]["request_id"], request["request_id"])


if __name__ == "__main__":
    unittest.main()

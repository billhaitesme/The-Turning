import tempfile
import unittest
from pathlib import Path

from services.approval_engine import (
    create_approval,
    load_approval_store,
    save_approval_store,
    set_approval_status,
    upsert_approval,
)


class ApprovalEngineTests(unittest.TestCase):
    def test_approval_workflow(self):
        store = {"version": 1, "approvals": []}
        record = create_approval(
            approval_id="approval-1",
            goal_id="goal-1",
            plan_id="plan-a",
            status="recommended",
            rationale="Best trade-off profile.",
        )
        store = upsert_approval(store, record)
        store = set_approval_status(store, approval_id="approval-1", status="approved", approved_by="user")
        item = store["approvals"][0]
        self.assertEqual(item["status"], "approved")
        self.assertEqual(item["approved_by"], "user")

    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.json"
            store = {"version": 1, "approvals": []}
            store = upsert_approval(
                store,
                create_approval(
                    approval_id="approval-2",
                    goal_id="goal-2",
                    plan_id="plan-b",
                ),
            )
            save_approval_store(store, path=path)
            loaded = load_approval_store(path=path)
            self.assertEqual(len(loaded["approvals"]), 1)


if __name__ == "__main__":
    unittest.main()

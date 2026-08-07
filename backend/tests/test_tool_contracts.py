import unittest

from services.tool_contracts import (
    build_tool_request,
    request_arguments_hash,
    validate_arguments_against_schema,
    validate_tool_definition,
    validate_tool_request,
)


class ToolContractTests(unittest.TestCase):
    def test_valid_tool_definition_accepted(self):
        tool = validate_tool_definition(
            {
                "name": "backend_health_check",
                "version": 1,
                "description": "Checks the configured local backend endpoint.",
                "category": "diagnostic",
                "risk_level": "low",
                "requires_approval": True,
                "supports_dry_run": True,
                "input_schema": {},
                "output_schema": {},
                "side_effects": [],
                "allowed_scopes": ["localhost"],
                "enabled": True,
            }
        )
        self.assertEqual(tool["name"], "backend_health_check")
        self.assertEqual(tool["risk_level"], "low")

    def test_critical_tool_definition_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool_definition(
                {
                    "name": "critical_tool",
                    "version": 1,
                    "description": "Unsupported critical tool.",
                    "category": "diagnostic",
                    "risk_level": "critical",
                    "requires_approval": True,
                    "supports_dry_run": False,
                    "input_schema": {},
                    "output_schema": {},
                    "side_effects": [],
                    "allowed_scopes": ["localhost"],
                    "enabled": True,
                }
            )

    def test_tool_request_hash_is_deterministic(self):
        self.assertEqual(request_arguments_hash({"a": 1, "b": 2}), request_arguments_hash({"b": 2, "a": 1}))

    def test_tool_request_contract_is_validated(self):
        request = build_tool_request(
            tool_name="backend_health_check",
            arguments={},
            requested_by="user",
            session_id="session-1",
        )
        validated = validate_tool_request(request)
        self.assertEqual(validated["status"], "proposed")

    def test_argument_schema_rejects_unexpected_keys(self):
        with self.assertRaises(ValueError):
            validate_arguments_against_schema({"unexpected": True}, {"type": "object", "additionalProperties": False, "properties": {}})


if __name__ == "__main__":
    unittest.main()

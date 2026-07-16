import unittest

from services.tool_registry import (
    BACKEND_HEALTH_CHECK_DESCRIPTOR,
    get_tool,
    is_tool_enabled,
    list_tools,
    register_tool,
    unregister_tool,
)


class ToolRegistryTests(unittest.TestCase):
    def test_registry_uses_explicit_tools_only(self):
        names = {tool["name"] for tool in list_tools()}
        self.assertIn("backend_health_check", names)

    def test_duplicate_tool_rejected(self):
        with self.assertRaises(ValueError):
            register_tool(BACKEND_HEALTH_CHECK_DESCRIPTOR)

    def test_disabled_tool_is_inspectable(self):
        descriptor = {
            "name": "disabled_probe",
            "version": 1,
            "description": "Disabled probe.",
            "category": "inspection",
            "risk_level": "low",
            "requires_approval": True,
            "supports_dry_run": True,
            "input_schema": {},
            "output_schema": {},
            "side_effects": [],
            "allowed_scopes": ["localhost"],
            "enabled": False,
        }
        register_tool(descriptor)
        try:
            tool = get_tool("disabled_probe")
            self.assertIsNotNone(tool)
            self.assertFalse(is_tool_enabled("disabled_probe"))
        finally:
            unregister_tool("disabled_probe")


if __name__ == "__main__":
    unittest.main()

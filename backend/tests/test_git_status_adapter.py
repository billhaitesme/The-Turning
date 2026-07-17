import unittest
from unittest.mock import patch

from services.adapters.git_status import GIT_STATUS_DESCRIPTOR, GitStatusAdapter


class GitStatusAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = GitStatusAdapter()

    def test_descriptor_validates(self):
        self.assertEqual(GIT_STATUS_DESCRIPTOR["name"], "git_status")
        self.assertEqual(GIT_STATUS_DESCRIPTOR["adapter_id"], "A-002")
        self.assertTrue(GIT_STATUS_DESCRIPTOR["requires_approval"])
        self.assertEqual(GIT_STATUS_DESCRIPTOR["allowed_scopes"], ["repository"])
        self.assertEqual(GIT_STATUS_DESCRIPTOR["category"], "inspection")

    def test_validate_arguments_defaults_and_limits(self):
        defaults = self.adapter.validate_arguments({})
        self.assertEqual(defaults, {"include_log": False, "log_limit": 5})

        with self.assertRaises(ValueError):
            self.adapter.validate_arguments({"include_log": "not_a_bool"})
        with self.assertRaises(ValueError):
            self.adapter.validate_arguments({"log_limit": 0})
        with self.assertRaises(ValueError):
            self.adapter.validate_arguments({"log_limit": 100})
        with self.assertRaises(ValueError):
            self.adapter.validate_arguments({"unknown_key": True})

    def test_dry_run_returns_only_read_only_commands(self):
        output = self.adapter.dry_run({"include_log": True, "log_limit": 3})
        self.assertTrue(output["safe"])
        self.assertEqual(output["side_effects"], [])
        self.assertIn("git log --oneline --decorate -3", output["would_check"])
        for cmd in output["would_check"]:
            for forbidden in ["add", "commit", "checkout", "merge", "reset", "clean", "push", "pull"]:
                self.assertNotIn(f" {forbidden} ", cmd)

    @patch("services.adapters.git_status._run_git")
    def test_execute_clean_repository(self, mock_run_git):
        def fake_run_git(args, cwd):
            if args == ["status", "--short", "--branch"]:
                return 0, "## main...origin/main [ahead 1]", ""
            if args == ["branch", "--show-current"]:
                return 0, "main", ""
            if args == ["rev-parse", "--short", "HEAD"]:
                return 0, "abcdef1", ""
            if args == ["describe", "--tags", "--always", "--dirty"]:
                return 0, "v1.0.0-2-gabcdef1", ""
            if args == ["remote", "-v"]:
                return 0, "origin\thttps://github.com/test/repo.git (fetch)\norigin\thttps://github.com/test/repo.git (push)", ""
            return -1, "", "unknown command"

        mock_run_git.side_effect = fake_run_git
        result = self.adapter.execute({})
        self.assertTrue(result["success"])
        self.assertFalse(result["dirty"])
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["commit"], "abcdef1")
        self.assertEqual(result["latest_tag"], "v1.0.0")
        self.assertEqual(result["ahead"], 1)
        self.assertEqual(result["behind"], 0)
        self.assertEqual(len(result["remotes"]), 2)
        self.assertEqual(result["recent_commits"], [])

    @patch("services.adapters.git_status._run_git")
    def test_execute_dirty_repository_with_log(self, mock_run_git):
        def fake_run_git(args, cwd):
            if args == ["status", "--short", "--branch"]:
                return 0, "## feature-branch\n M file.py\n?? untracked.txt", ""
            if args == ["branch", "--show-current"]:
                return 0, "feature-branch", ""
            if args == ["rev-parse", "--short", "HEAD"]:
                return 0, "1234567", ""
            if args == ["describe", "--tags", "--always", "--dirty"]:
                return 0, "1234567-dirty", ""
            if args == ["remote", "-v"]:
                return 0, "", ""
            if args == ["log", "--oneline", "--decorate", "-2"]:
                return 0, "1234567 commit 1\n890abcd commit 2", ""
            return -1, "", "unknown"

        mock_run_git.side_effect = fake_run_git
        result = self.adapter.execute({"include_log": True, "log_limit": 2})
        self.assertTrue(result["success"])
        self.assertTrue(result["dirty"])
        self.assertEqual(result["branch"], "feature-branch")
        self.assertEqual(result["latest_tag"], None)
        self.assertEqual(len(result["recent_commits"]), 2)

    @patch("services.adapters.git_status._run_git")
    def test_execute_missing_git_reports_failure(self, mock_run_git):
        mock_run_git.return_value = (-1, "", "git command not found")
        result = self.adapter.execute({})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "git command not found")
        self.assertEqual(result["branch"], "")


if __name__ == "__main__":
    unittest.main()
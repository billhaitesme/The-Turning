from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.tool_contracts import validate_tool_definition

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_git(args: List[str], cwd: Path) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git command not found"
    except Exception as exc:
        return -1, "", str(exc)


@dataclass(frozen=True)
class GitStatusResult:
    repository_root: str
    branch: str
    commit: str
    latest_tag: Optional[str]
    dirty: bool
    ahead: int
    behind: int
    remotes: List[str]
    recent_commits: List[str]
    success: bool
    checked_at: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_root": self.repository_root,
            "branch": self.branch,
            "commit": self.commit,
            "latest_tag": self.latest_tag,
            "dirty": self.dirty,
            "ahead": self.ahead,
            "behind": self.behind,
            "remotes": self.remotes,
            "recent_commits": self.recent_commits,
            "success": self.success,
            "checked_at": self.checked_at,
            "error": self.error,
        }


class GitStatusAdapter:
    def describe(self) -> Dict[str, Any]:
        return {
            "adapter_id": "A-002",
            "name": "git_status",
            "version": 1,
            "description": "Inspects the current OMEGA-ARC Git repository state.",
        }

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("git_status arguments must be an object.")
        unknown = set(arguments) - {"include_log", "log_limit"}
        if unknown:
            raise ValueError(f"git_status accepts only include_log and log_limit arguments, got: {', '.join(sorted(unknown))}")
        
        include_log = arguments.get("include_log", False)
        if not isinstance(include_log, bool):
            raise ValueError("git_status include_log must be a boolean.")

        log_limit = arguments.get("log_limit", 5)
        if not isinstance(log_limit, int) or isinstance(log_limit, bool) or not (1 <= log_limit <= 20):
            raise ValueError("git_status log_limit must be an integer between 1 and 20.")

        return {
            "include_log": include_log,
            "log_limit": log_limit,
        }

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        include_log = validated["include_log"]
        log_limit = validated["log_limit"]
        commands = [
            "git status --short --branch",
            "git branch --show-current",
            "git rev-parse --short HEAD",
            "git describe --tags --always --dirty",
            "git remote -v",
        ]
        if include_log:
            commands.append(f"git log --oneline --decorate -{log_limit}")
        return {
            "would_check": commands,
            "safe": True,
            "side_effects": [],
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        include_log = validated["include_log"]
        log_limit = validated["log_limit"]
        checked_at = _utc_now_iso()
        repo_root = REPOSITORY_ROOT

        code, out_status, err_status = _run_git(["status", "--short", "--branch"], repo_root)
        if code != 0:
            return GitStatusResult(
                repository_root=str(repo_root),
                branch="",
                commit="",
                latest_tag=None,
                dirty=False,
                ahead=0,
                behind=0,
                remotes=[],
                recent_commits=[],
                success=False,
                checked_at=checked_at,
                error=err_status or out_status or "git status failed",
            ).to_dict()

        code, out_branch, _ = _run_git(["branch", "--show-current"], repo_root)
        branch = out_branch if code == 0 else ""

        code, out_commit, _ = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
        commit = out_commit if code == 0 else ""

        code, out_desc, _ = _run_git(["describe", "--tags", "--always", "--dirty"], repo_root)
        latest_tag: Optional[str] = None
        dirty_from_desc = False
        if code == 0 and out_desc:
            clean_desc = out_desc
            if out_desc.endswith("-dirty"):
                clean_desc = out_desc[:-6]
                dirty_from_desc = True
            m = re.match(r"^(.*)-\d+-g[0-9a-f]+$", clean_desc)
            if m:
                latest_tag = m.group(1)
            elif clean_desc != commit and clean_desc != out_commit:
                latest_tag = clean_desc

        code, out_remote, _ = _run_git(["remote", "-v"], repo_root)
        remotes = [line.strip() for line in out_remote.splitlines() if line.strip()] if code == 0 else []

        recent_commits: List[str] = []
        if include_log:
            code, out_log, _ = _run_git(["log", "--oneline", "--decorate", f"-{log_limit}"], repo_root)
            if code == 0:
                recent_commits = [line.strip() for line in out_log.splitlines() if line.strip()]

        lines = [line for line in out_status.splitlines() if line is not None]
        dirty = dirty_from_desc
        ahead = 0
        behind = 0
        if lines:
            header = lines[0]
            if len(lines) > 1:
                dirty = True
            m_ahead = re.search(r"ahead (\d+)", header)
            if m_ahead:
                ahead = int(m_ahead.group(1))
            m_behind = re.search(r"behind (\d+)", header)
            if m_behind:
                behind = int(m_behind.group(1))
            if not branch and header.startswith("## "):
                branch_part = header[3:].split("...")[0].split(" ")[0].strip()
                if branch_part and branch_part != "HEAD":
                    branch = branch_part

        return GitStatusResult(
            repository_root=str(repo_root),
            branch=branch,
            commit=commit,
            latest_tag=latest_tag,
            dirty=dirty,
            ahead=ahead,
            behind=behind,
            remotes=remotes,
            recent_commits=recent_commits,
            success=True,
            checked_at=checked_at,
            error=None,
        ).to_dict()


GIT_STATUS_DESCRIPTOR = validate_tool_definition(
    {
        "adapter_id": "A-002",
        "name": "git_status",
        "version": 1,
        "description": "Inspects the current OMEGA-ARC Git repository state.",
        "category": "inspection",
        "risk_level": "low",
        "requires_approval": True,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "include_log": {
                    "type": "boolean",
                },
                "log_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["repository"],
        "enabled": True,
    }
)
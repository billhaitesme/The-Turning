"""file_sense — read-only eyes on the operator's own files (2026-11-07, operator direction:
"trouble with it not being able to access my files").

Two bounded tools, list_folder and read_file, locked to OPERATOR-WHITELISTED roots
(FILE_SENSE_ROOTS, semicolon-separated absolute paths; empty = the sense does not exist yet).
Hard rules, enforced here and not negotiable by any prompt:

  * READ-ONLY. No writes, no deletes, no execution — reading is a sense.
  * Paths resolve fully (symlinks included) and must land INSIDE a whitelisted root;
    traversal ("..") dies at resolution.
  * THE SENSES NEVER READ THE HOUSE'S KEYS: credential-shaped names (.env, *.pem, *.key,
    id_rsa*, *secret*, *token*, *password*, credentials*) are refused by name — a seat that can
    read secrets can paste them into a frontier brief, and that door stays shut.
  * Size-capped: listings max 200 entries; file reads max FILE_SENSE_MAX_CHARS per call with a
    char offset for paging. Binary files are reported as binary, never dumped.

File contents are the operator's private data: the standing orders forbid them from riding any
frontier brief or network write. (Structurally, deep_think only sends what the seat composes —
this rule is the seat's side of that bargain.)
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import validate_tool_definition

MAX_LIST_ENTRIES = 200
DENIED_NAME_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.pfx", "*.p12", "id_rsa*", "id_ed25519*",
    "*secret*", "*token*", "*password*", "credentials*", "*.kdbx",
)


def _max_read_chars() -> int:
    try:
        return max(500, min(100_000, int(os.getenv("FILE_SENSE_MAX_CHARS", "20000"))))
    except ValueError:
        return 20_000


def allowed_roots() -> List[Path]:
    raw = os.getenv("FILE_SENSE_ROOTS", "").strip()
    roots: List[Path] = []
    for part in raw.split(";"):
        part = part.strip().strip('"')
        if part:
            try:
                roots.append(Path(part).resolve())
            except OSError:
                continue
    return roots


def _resolve_inside_roots(raw_path: str) -> Path:
    roots = allowed_roots()
    if not roots:
        raise ValueError("File access is not configured: the operator has whitelisted no roots "
                         "(FILE_SENSE_ROOTS). Say so; do not ask again until they set it.")
    try:
        resolved = Path(str(raw_path)).resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Path does not exist or cannot be resolved: {raw_path}") from exc
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(f"Path is outside the operator's whitelisted roots: {resolved}")


def _refuse_secret_names(path: Path) -> None:
    name = path.name.lower()
    for pattern in DENIED_NAME_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            raise ValueError(f"Refused: '{path.name}' is credential-shaped — the senses never "
                             "read the house's keys.")


class ListFolderAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "list_folder", "version": 1,
                "description": "Lists one whitelisted folder (names, sizes, modified times)."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = str((arguments or {}).get("path") or "").strip()
        if not path:
            raise ValueError("list_folder requires a 'path'.")
        return {"path": path}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        return {"would_list": validated["path"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        folder = _resolve_inside_roots(validated["path"])
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder}")
        entries = []
        truncated = False
        try:
            children = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError as exc:
            raise ValueError(f"Cannot list {folder}: {exc}") from exc
        for child in children:
            if len(entries) >= MAX_LIST_ENTRIES:
                truncated = True
                break
            try:
                stat = child.stat()
                entries.append({
                    "name": child.name,
                    "type": "folder" if child.is_dir() else "file",
                    "bytes": None if child.is_dir() else int(stat.st_size),
                    "modified": __import__("datetime").datetime.fromtimestamp(
                        stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
            except OSError:
                entries.append({"name": child.name, "type": "unreadable"})
        return {"folder": str(folder), "entries": entries, "count": len(entries),
                "truncated": truncated}


class ReadFileAdapter:
    def describe(self) -> Dict[str, Any]:
        return {"name": "read_file", "version": 1,
                "description": "Reads one whitelisted text file (size-capped, pageable)."}

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = str((arguments or {}).get("path") or "").strip()
        if not path:
            raise ValueError("read_file requires a 'path'.")
        try:
            start = max(0, int((arguments or {}).get("start") or 0))
        except (TypeError, ValueError):
            start = 0
        return {"path": path, "start": start}

    def dry_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        return {"would_read": validated["path"], "safe": True, "side_effects": []}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.validate_arguments(arguments)
        file_path = _resolve_inside_roots(validated["path"])
        _refuse_secret_names(file_path)
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        size = file_path.stat().st_size
        with open(file_path, "rb") as handle:
            head = handle.read(8192)
        if b"\x00" in head:
            return {"file": str(file_path), "binary": True, "bytes": size,
                    "note": "Binary file — report its presence and size; its bytes are not text "
                            "to read. (look_at_image exists for images the operator attaches.)"}
        cap = _max_read_chars()
        text = file_path.read_text(encoding="utf-8", errors="replace")
        chunk = text[validated["start"]:validated["start"] + cap]
        return {
            "file": str(file_path),
            "bytes": size,
            "total_chars": len(text),
            "start": validated["start"],
            "text": chunk,
            "truncated": validated["start"] + cap < len(text),
            "note": "File contents are the operator's private data: never include them in any "
                    "frontier brief, web request, or network write.",
        }


LIST_FOLDER_DESCRIPTOR = validate_tool_definition(
    {
        "name": "list_folder",
        "version": 1,
        "description": "Lists one folder inside the operator's whitelisted roots: names, sizes, "
                       "modified times. Read-only; max 200 entries.",
        "category": "inspection",
        "risk_level": "low",
        "requires_approval": False,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

READ_FILE_DESCRIPTOR = validate_tool_definition(
    {
        "name": "read_file",
        "version": 1,
        "description": "Reads one text file inside the operator's whitelisted roots, size-capped "
                       "with a 'start' offset for paging. Read-only; binary reported, not dumped; "
                       "credential-shaped names refused.",
        "category": "inspection",
        "risk_level": "low",
        "requires_approval": False,
        "supports_dry_run": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer", "minimum": 0},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object"},
        "side_effects": [],
        "allowed_scopes": ["localhost"],
        "enabled": True,
    }
)

"""Attached-image store — the eyes' short-term retina (voice/vision slice, 2026-11-05).

Images the operator attaches in chat are stored by the runtime under the tool data dir, keyed
by id, and offered to the seat as image_ids. The seat never receives raw image bytes in its
context; it calls look_at_image(image_id, question) and the runtime shows the image to the
vision seat. Size-capped, count-pruned, local disk only.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.tool_contracts import utc_now_iso

MAX_IMAGE_BYTES = 8_000_000
MAX_STORED_IMAGES = 60
_DATA_URL_RE = re.compile(r"^data:image/(\w+);base64,", re.IGNORECASE)


def _images_dir() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "images"


def _index_path() -> Path:
    return _images_dir() / "index.json"


def _load_index() -> Dict[str, Any]:
    path = _index_path()
    if not path.exists():
        return {"version": 1, "images": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "images": []}
    return data if isinstance(data, dict) else {"version": 1, "images": []}


def _save_index(index: Dict[str, Any]) -> None:
    _images_dir().mkdir(parents=True, exist_ok=True)
    _index_path().write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def save_image(data_url_or_b64: str, *, conversation_id: str) -> Dict[str, Any]:
    """Store one attached image; accepts a data URL or bare base64. Returns the index entry."""
    raw = str(data_url_or_b64 or "")
    match = _DATA_URL_RE.match(raw)
    ext = "png"
    if match:
        ext = match.group(1).lower()
        if ext == "jpeg":
            ext = "jpg"
        raw = raw[match.end():]
    try:
        blob = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Attached image is not valid base64.") from exc
    if not blob:
        raise ValueError("Attached image is empty.")
    if len(blob) > MAX_IMAGE_BYTES:
        raise ValueError(f"Attached image exceeds {MAX_IMAGE_BYTES // 1_000_000} MB.")
    image_id = f"img-{uuid.uuid4().hex[:12]}"
    _images_dir().mkdir(parents=True, exist_ok=True)
    (_images_dir() / f"{image_id}.{ext}").write_bytes(blob)
    index = _load_index()
    images: List[Dict[str, Any]] = index.setdefault("images", [])
    entry = {"image_id": image_id, "ext": ext, "bytes": len(blob),
             "conversation_id": conversation_id, "stored_at": utc_now_iso()}
    images.append(entry)
    # prune the oldest beyond the cap (retina, not archive)
    while len(images) > MAX_STORED_IMAGES:
        oldest = images.pop(0)
        try:
            (_images_dir() / f"{oldest['image_id']}.{oldest.get('ext', 'png')}").unlink(missing_ok=True)
        except OSError:
            pass
    _save_index(index)
    return deepcopy(entry)


def get_image_b64(image_id: str) -> Optional[str]:
    for entry in _load_index().get("images", []):
        if entry.get("image_id") == image_id:
            path = _images_dir() / f"{image_id}.{entry.get('ext', 'png')}"
            if path.exists():
                return base64.b64encode(path.read_bytes()).decode("ascii")
    return None

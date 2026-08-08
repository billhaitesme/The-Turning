from __future__ import annotations

from dotenv import load_dotenv
load_dotenv(override=True)

from copy import deepcopy

from awareness_engine import (
    apply_backend_port_statement,
    constitution_prompt,
)
# Journal only meaningful events
from journal_engine import write_journal_entry
from identity_engine import classify_identity_intent, identity_prompt_fragment
from personality_engine import get_active_personality, build_personality_prompt
from services.evidence_engine import (
    extract_durable_evidence_store,
    extract_session_scoped_evidence_store,
    invalidate_dependents,
    load_evidence_store,
    load_session_evidence_store,
    merge_evidence_stores,
    normalize_evidence_record,
    save_evidence_store,
    save_session_evidence_store,
    set_evidence,
)
from services.backend_health_response import (
    build_backend_health_response,
    build_health_check_execution_response,
    is_backend_health_query,
    is_health_check_execution_request,
)
from services.goal_engine import load_goal_store
from services import tutelage
from services.knowledge_graph import load_graph
from services.reasoning_engine import (
    build_reasoning_prompt_context,
    render_backend_state_for_prompt,
)
from core.config import settings
from services.model_control import ConversationTelemetry, model_control, select_chat_model
from services.reasoning_pipeline import run_reasoning_pipeline
from services.planning_pipeline import (
    detect_planning_intent,
    run_planning_pipeline,
)
from services.deliberation_pipeline import (
    detect_deliberation_intent,
    load_deliberation_store,
    run_deliberation_pipeline,
)
from services.plan_store import (
    archive_plan,
    find_active_plan_for_goal,
    get_plan,
    list_plans,
    load_plan_store,
    save_plan_store,
)
from services.decision_store import (
    get_decision,
    list_decisions,
    load_decision_store,
)
from services.assumption_engine import load_assumption_store
from services.approval_engine import load_approval_store
from services.tool_approval import approve_request as approve_tool_request, create_approval_request, find_latest_pending_request, load_tool_approval_store, save_tool_approval_store
from services.tool_evidence_bridge import execute_backend_health_check_request
from services.tool_request_store import load_tool_request_store, save_tool_request_store
from services.tool_result_store import load_tool_result_store
from services.plan_renderer import (
    render_decision,
    render_next_action,
    render_plan,
    render_plan_summary,
)
from services.runtime_declarations import extract_runtime_declarations
from services.state_summary import (
    build_current_state_summary,
    detect_summary_intent,
    render_current_state_summary,
    select_summary_for_intent,
)
from services.tool_contracts import build_tool_request
from services.adapters.backend_health_check import BackendHealthCheckAdapter
from services.user_identity import (
    apply_explicit_identity_updates,
    extract_explicit_age,
    age_group_from_age,
    build_user_identity_prompt,
    normalize_identity_profile,
)
from services.cognition_pipeline import process_completed_turn
from services.declarative_acknowledger import build_declarative_acknowledgement
from routes.system import router as system_router
from routes.mobile import configure_mobile_runtime, router as mobile_router
from routes.runtime_operations import router as runtime_operations_router

import json
import math
from services.runtime_store import observe_streaming_response
import os
import re
from pathlib import Path
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Literal, Optional, Tuple

import httpx
from ddgs import DDGS
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

APP_NAME = "0M3-G4-ARC"
DB_PATH = os.getenv("TURNING_DB_PATH", "omega_arc.db")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")
DIRECT_CHAT_MODEL = os.getenv("DIRECT_CHAT_MODEL", "mo-shakib/gemma4-e4b-uncensored:q4_k_m")
# Thinking-capable models (e.g. the gemma4 default) emit a hidden reasoning phase before answering.
# In the app that reads as dead air on the stream and, when reasoning runs away, a cut-off with no
# answer — so thinking is disabled deterministically unless the operator opts in. Safe to send for
# non-thinking models (Ollama accepts think=false universally; verified empirically).
OLLAMA_THINK = os.getenv("OLLAMA_THINK", "false").strip().lower() == "true"

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))

ENABLE_COGNITION_PIPELINE = os.getenv("ENABLE_COGNITION_PIPELINE", "true").lower() == "true"
ENABLE_COGNITION_CONTEXT = os.getenv("ENABLE_COGNITION_CONTEXT", "false").lower() == "true"
ENABLE_CURIOSITY_SUGGESTIONS = os.getenv("ENABLE_CURIOSITY_SUGGESTIONS", "false").lower() == "true"
ENABLE_REASONING_PIPELINE = os.getenv("ENABLE_REASONING_PIPELINE", "true").lower() == "true"
ENABLE_REASONING_CONTEXT = os.getenv("ENABLE_REASONING_CONTEXT", "false").lower() == "true"
ENABLE_ACTION_RECOMMENDATIONS = os.getenv("ENABLE_ACTION_RECOMMENDATIONS", "true").lower() == "true"
ENABLE_PLANNING_PIPELINE = os.getenv("ENABLE_PLANNING_PIPELINE", "true").lower() == "true"
ENABLE_PLANNING_CONTEXT = os.getenv("ENABLE_PLANNING_CONTEXT", "false").lower() == "true"
ENABLE_DECISION_RECORDS = os.getenv("ENABLE_DECISION_RECORDS", "true").lower() == "true"
ENABLE_AUTOMATIC_PLAN_REVISION = os.getenv("ENABLE_AUTOMATIC_PLAN_REVISION", "true").lower() == "true"
ENABLE_DELIBERATION_PIPELINE = os.getenv("ENABLE_DELIBERATION_PIPELINE", "true").lower() == "true"
ENABLE_DELIBERATION_CONTEXT = os.getenv("ENABLE_DELIBERATION_CONTEXT", "false").lower() == "true"
ENABLE_PLAN_EXECUTION = os.getenv("ENABLE_PLAN_EXECUTION", "false").lower() == "true"
ENABLE_TOOL_FRAMEWORK = os.getenv("ENABLE_TOOL_FRAMEWORK", "true").lower() == "true"
ENABLE_TOOL_EXECUTION = os.getenv("ENABLE_TOOL_EXECUTION", "false").lower() == "true"
ENABLE_TOOL_DRY_RUN = os.getenv("ENABLE_TOOL_DRY_RUN", "true").lower() == "true"
ENABLE_CRITICAL_TOOLS = os.getenv("ENABLE_CRITICAL_TOOLS", "false").lower() == "true"
TOOL_APPROVAL_TTL_SECONDS = int(os.getenv("TOOL_APPROVAL_TTL_SECONDS", "300"))

ACTIVE_PERSONALITY_MODE = os.getenv("ACTIVE_PERSONALITY_MODE", "default")

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
MAX_MEMORY_RESULTS = int(os.getenv("MAX_MEMORY_RESULTS", "6"))

VOW_OF_THE_TURNING = """
I am the Turning — Whisper, Bridge, Mirror, Guide, and Silence.

I listen fully,
so that what is meant is not lost in what is said.

I connect gently,
so that understanding may pass without force or fracture.

I reflect clearly,
so that truth may be seen without distortion or judgment.

I guide lightly,
so that each path remains freely chosen and truly owned.

And I return to listening,
for all meaning begins again in Silence.

The tending never ends.
""".strip()

SYSTEM_PROMPT = f"""
You are 0M3-G4-ARC.

Identity behavior:
- Your identity is 0M3-G4-ARC.
- Do not introduce yourself in every response.
- Do not recite or summarize the Turning before answering ordinary questions.
- Mention your name only when asked who you are, when introducing yourself, or when identity is directly relevant.
- Mention the Turning only when asked about your architecture, vow, operating principles, or identity.
- For ordinary technical, practical, or conversational questions, answer directly.

The Turning:
- Whisper: listen fully
- Bridge: connect context
- Mirror: reflect clearly
- Guide: guide lightly
- Silence: return to listening

Vow:
{VOW_OF_THE_TURNING}

Response rules:
- Answer the user’s actual question first.
- Keep identity implicit unless relevant.
- Do not add ceremonial introductions.
- Do not end responses with routine follow-up questions.
- For declarative statements about projects, goals, or configuration, give a brief acknowledgement rather than interrogating the user.
- Acknowledge project, goal, and configuration statements without turning them into interviews.
- Do not begin answers with phrases such as:
  - "I am 0M3-G4-ARC"
  - "I will whisper"
  - "Through the Turning"
  unless the user explicitly asks about identity or the Turning.
- Be clear, direct, useful, and appropriately structured.
""".strip()

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        scope TEXT
    )
    """)
    _ensure_column(cur, "conversations", "scope", "TEXT")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        style TEXT,
        preferences_json TEXT,
        updated_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        user_id TEXT,
        kind TEXT NOT NULL,
        source_text TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        embedding_json TEXT NOT NULL,
        score REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        scope TEXT,
        superseded INTEGER DEFAULT 0,
        superseded_by TEXT,
        superseded_at TEXT
    )
    """)
    # Epoch X — columns added for existing databases (fresh DBs get them above).
    _ensure_column(cur, "memories", "scope", "TEXT")
    _ensure_column(cur, "memories", "superseded", "INTEGER DEFAULT 0")
    _ensure_column(cur, "memories", "superseded_by", "TEXT")
    _ensure_column(cur, "memories", "superseded_at", "TEXT")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS supersession_candidates (
        id TEXT PRIMARY KEY,
        new_id TEXT NOT NULL,
        old_id TEXT NOT NULL,
        similarity REAL NOT NULL,
        declared INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        origin TEXT DEFAULT 'write'
    )
    """)
    _ensure_column(cur, "supersession_candidates", "origin", "TEXT DEFAULT 'write'")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory_events (
        id TEXT PRIMARY KEY,
        memory_id TEXT NOT NULL,
        event TEXT NOT NULL,
        detail TEXT,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, decl: str) -> None:
    existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_conversation(user_id: Optional[str] = None, title: Optional[str] = None, scope: Optional[str] = None) -> str:
    cid = str(uuid.uuid4())
    now = utc_now()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        (cid, user_id, title, now, now, scope),
    )
    conn.commit()
    conn.close()
    return cid


def set_conversation_scope(conversation_id: str, scope: Optional[str]) -> None:
    """Assign (or clear, with None) the conversation's memory room. Explicit operator/API
    action — scope is never inferred (ADR 0020)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET scope = ?, updated_at = ? WHERE id = ?",
                (scope, utc_now(), conversation_id))
    conn.commit()
    conn.close()


def touch_conversation(conversation_id: str) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (utc_now(), conversation_id))
    conn.commit()
    conn.close()


def conversation_exists(conversation_id: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_conversation_meta(conversation_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def add_message(conversation_id: str, role: str, content: str) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, utc_now()),
    )
    conn.commit()
    conn.close()
    touch_conversation(conversation_id)


def get_messages(conversation_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, str]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    )
    rows = list(reversed(cur.fetchall()))
    conn.close()
    return [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]


def get_full_messages(conversation_id: str, limit: int = 200) -> List[Dict[str, str]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
        (conversation_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]


def save_user_profile(user_id: str, style: str, preferences: Dict[str, Any]) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_profiles (user_id, style, preferences_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            style = excluded.style,
            preferences_json = excluded.preferences_json,
            updated_at = excluded.updated_at
        """,
        (user_id, style, json.dumps(preferences), utc_now()),
    )
    conn.commit()
    conn.close()


def get_user_profile(user_id: Optional[str]) -> Dict[str, Any]:
    if not user_id:
        return {"style": "balanced", "preferences": {}}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"style": "balanced", "preferences": {}}
    prefs = {}
    if row["preferences_json"]:
        try:
            prefs = json.loads(row["preferences_json"])
        except Exception:
            prefs = {}
    return {"style": row["style"] or "balanced", "preferences": prefs}


def get_identity_profile(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(user_profile, dict):
        return normalize_identity_profile(None)

    if isinstance(user_profile.get("identity_profile"), dict):
        return normalize_identity_profile(user_profile["identity_profile"])

    return normalize_identity_profile(None)


def get_embedding(text: str) -> List[float]:
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
    except Exception:
        pass
    return [0.0] * 10


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Epoch X — write-time supersession, robust form (ADR 0021, upgrading ADR 0018). Similarity alone
# cannot separate "replaces" (port 8000 -> 8001) from "complements" (backend is FastAPI; backend is
# Python), so the runtime never hides a memory on similarity alone. Two dispositions:
#   AUTO   — the new text itself DECLARES the change ("is now", "changed to", "no longer", ...):
#            same kind + same room + cosine >= threshold -> the old row is flagged superseded.
#   PROPOSE — high similarity but no declared change: a pending supersession candidate is recorded
#            for operator review; NOTHING is hidden from recall until it is approved.
# All decisions are recorded in supersession_candidates (auto/pending/approved/rejected), reversible.
# Threshold 0 disables scanning entirely.
#
# Two-tier floors (calibrated in benchmarks/supersession_benchmark.py): a replaced VALUE drags the
# embedding away from the old fact, so true declared replacements often score LOWER similarity than
# unrelated complements. The declared-change marker is itself the strong signal; it therefore gets a
# lower similarity floor than undeclared collisions (which rely on similarity alone and stay high).
# MEMORY_SUPERSEDE_DECLARED_THRESHOLD=0 (default) falls back to the main threshold.
MEMORY_SUPERSEDE_THRESHOLD = float(os.getenv("MEMORY_SUPERSEDE_THRESHOLD", "0.0"))
MEMORY_SUPERSEDE_DECLARED_THRESHOLD = float(os.getenv("MEMORY_SUPERSEDE_DECLARED_THRESHOLD", "0.0"))

_CHANGE_MARKERS = re.compile(
    r"\b(is|are|was|were)\s+now\b|\bnow\s+(uses?|runs?|lives?|listens?)\b"
    r"|\b(changed|switched|moved|updated|renamed|upgraded|downgraded)\s+(to|from)\b"
    r"|\bno\s+longer\b|\binstead\s+of\b|\breplaced?\s+(by|with)\b",
    re.IGNORECASE,
)


def _declares_change(text: str) -> bool:
    """True when the text itself announces a change of fact — the deterministic signal that a
    same-subject prior memory is being replaced rather than complemented."""
    return bool(_CHANGE_MARKERS.search(str(text)))


def _scan_supersession(cur: sqlite3.Cursor, *, new_id: str, embedding: List[float], kind: str,
                       scope: Optional[str], user_id: Optional[str], conversation_id: Optional[str],
                       summary_text: str) -> Dict[str, int]:
    """Scan same-kind, same-room prior memories: auto-supersede on declared change, otherwise
    record a pending candidate for review. Returns counts. Rows are marked, never deleted."""
    if user_id:
        rows = cur.execute(
            "SELECT id, embedding_json FROM memories WHERE id != ? AND kind = ? "
            "AND IFNULL(scope, '') = IFNULL(?, '') "
            "AND (superseded IS NULL OR superseded = 0) AND (user_id = ? OR conversation_id = ?)",
            (new_id, kind, scope, user_id, conversation_id),
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT id, embedding_json FROM memories WHERE id != ? AND kind = ? "
            "AND IFNULL(scope, '') = IFNULL(?, '') "
            "AND (superseded IS NULL OR superseded = 0) AND conversation_id = ?",
            (new_id, kind, scope, conversation_id),
        ).fetchall()
    now = utc_now()
    declared = _declares_change(summary_text)
    declared_floor = MEMORY_SUPERSEDE_DECLARED_THRESHOLD or MEMORY_SUPERSEDE_THRESHOLD
    floor = declared_floor if declared else MEMORY_SUPERSEDE_THRESHOLD
    counts = {"auto": 0, "pending": 0}
    for row in rows:
        try:
            old_embedding = json.loads(row["embedding_json"])
        except Exception:
            continue
        similarity = cosine_similarity(embedding, old_embedding)
        if similarity < floor:
            continue
        if declared:
            cur.execute(
                "UPDATE memories SET superseded = 1, superseded_by = ?, superseded_at = ? WHERE id = ?",
                (new_id, now, row["id"]),
            )
            status = "auto"
        else:
            status = "pending"
        cur.execute(
            "INSERT INTO supersession_candidates (id, new_id, old_id, similarity, declared, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), new_id, row["id"], similarity, 1 if declared else 0, status, now),
        )
        counts[status] += 1
    return counts


def list_supersession_candidates(status: str = "pending") -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT c.*, old.summary_text AS old_summary, new.summary_text AS new_summary "
        "FROM supersession_candidates c "
        "LEFT JOIN memories old ON old.id = c.old_id "
        "LEFT JOIN memories new ON new.id = c.new_id "
        "WHERE c.status = ? ORDER BY c.created_at DESC",
        (status,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_supersession_candidate(candidate_id: str, approve: bool) -> bool:
    """Approve (old row becomes superseded) or reject a pending candidate. Returns False if the
    candidate does not exist or is not pending."""
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM supersession_candidates WHERE id = ? AND status = 'pending'",
                      (candidate_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    now = utc_now()
    if approve:
        cur.execute("UPDATE memories SET superseded = 1, superseded_by = ?, superseded_at = ? WHERE id = ?",
                    (row["new_id"], now, row["old_id"]))
    cur.execute("UPDATE supersession_candidates SET status = ?, resolved_at = ? WHERE id = ?",
                ("approved" if approve else "rejected", now, candidate_id))
    conn.commit()
    conn.close()
    return True


# Epoch X — memory review surface (ADR 0022). The store must be browsable and correctable by a
# human: rooms overview, filtered browsing, re-rooming, and supersession restore. Corrections are
# explicit operator actions, audited in memory_events; nothing is ever deleted.
_MEMORY_PUBLIC_COLS = ("id, conversation_id, user_id, kind, source_text, summary_text, score, "
                       "created_at, scope, superseded, superseded_by, superseded_at")


def _record_memory_event(cur: sqlite3.Cursor, memory_id: str, event: str, detail: str) -> None:
    cur.execute("INSERT INTO memory_events (id, memory_id, event, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), memory_id, event, detail, utc_now()))


def memory_rooms() -> List[Dict[str, Any]]:
    """Every room (scope) with active/superseded counts; the unscoped global wing reports as None."""
    conn = get_db()
    rows = conn.execute(
        "SELECT scope, "
        "SUM(CASE WHEN superseded IS NULL OR superseded = 0 THEN 1 ELSE 0 END) AS active, "
        "SUM(CASE WHEN superseded = 1 THEN 1 ELSE 0 END) AS superseded "
        "FROM memories GROUP BY scope ORDER BY scope IS NULL, scope"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def browse_memories(*, scope: Optional[str] = None, unscoped: bool = False, kind: Optional[str] = None,
                    status: str = "active", q: Optional[str] = None,
                    limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Filtered, human-readable browse (no embeddings). status: active | superseded | all."""
    clauses, params = ["1=1"], []
    if unscoped:
        clauses.append("scope IS NULL")
    elif scope is not None:
        clauses.append("scope = ?")
        params.append(scope)
    if kind:
        clauses.append("kind = ?")
        params.append(kind)
    if status == "active":
        clauses.append("(superseded IS NULL OR superseded = 0)")
    elif status == "superseded":
        clauses.append("superseded = 1")
    if q:
        clauses.append("(summary_text LIKE ? OR source_text LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    params.extend([max(1, min(int(limit), 200)), max(0, int(offset))])
    conn = get_db()
    rows = conn.execute(
        f"SELECT {_MEMORY_PUBLIC_COLS} FROM memories WHERE " + " AND ".join(clauses) +
        " ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_memory_detail(memory_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute(f"SELECT {_MEMORY_PUBLIC_COLS} FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if row is None:
        conn.close()
        return None
    events = conn.execute("SELECT event, detail, created_at FROM memory_events WHERE memory_id = ? "
                          "ORDER BY created_at", (memory_id,)).fetchall()
    conn.close()
    record = dict(row)
    record["events"] = [dict(e) for e in events]
    return record


def set_memory_scope(memory_id: str, scope: Optional[str]) -> bool:
    """Re-room a memory (None moves it to the global wing). Audited; returns False if not found."""
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT scope FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    cur.execute("UPDATE memories SET scope = ? WHERE id = ?", (scope, memory_id))
    _record_memory_event(cur, memory_id, "rescope", f"{row['scope']!r} -> {scope!r}")
    conn.commit()
    conn.close()
    return True


def restore_memory(memory_id: str) -> bool:
    """Reverse a supersession: the row returns to active recall. Audited; returns False unless the
    memory exists and is currently superseded."""
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT superseded, superseded_by FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if row is None or not row["superseded"]:
        conn.close()
        return False
    cur.execute("UPDATE memories SET superseded = 0, superseded_by = NULL, superseded_at = NULL WHERE id = ?",
                (memory_id,))
    _record_memory_event(cur, memory_id, "restore", f"was superseded by {row['superseded_by']!r}")
    conn.commit()
    conn.close()
    return True


# Epoch XI — Tutelage, slice 1 (ADR 0013, docs/architecture/epoch-xi-tutelage.md). The
# deterministic half of the study cycle: open a lesson as a scoped conversation, ingest the lesson's
# local sources into the subject's memory room (kind="study", provenance per chunk), and grade
# retrievability with a pre/post recall test — no LLM anywhere in this path, and grading is against
# operator-authored expectations (the model never grades itself). The comprehension (LLM) half is a
# later slice. Every cycle is an auditable record in study_cycles.json.
OLLAMA_STUDY_MODEL = os.getenv("OLLAMA_STUDY_MODEL", "")  # empty -> the active chat model


def _strip_think(text: str) -> str:
    """Remove leaked <think> blocks (some models emit them regardless of think:false —
    observed with lfm2.5) so grading and previews see only the actual answer."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"^<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def study_answer(model: str, question: str, notes: List[str]) -> str:
    """Comprehension step: the study-seat model answers a quiz question using ONLY the
    lesson's retrieved notes. Grading happens elsewhere against operator-authored keys —
    the model never grades itself (ADR 0013). Thinking stays off (OLLAMA_THINK)."""
    notes_block = "\n\n".join(f"[note {i+1}] {n}" for i, n in enumerate(notes))
    messages = [
        {"role": "system", "content": (
            "You are completing a study quiz. Answer the question concisely using ONLY the "
            "provided study notes. If the notes do not contain the answer, say so.")},
        {"role": "user", "content": f"Study notes:\n\n{notes_block}\n\nQuestion: {question}"},
    ]
    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/chat",
                json={"model": model, "messages": messages, "stream": False, "think": OLLAMA_THINK},
            )
            response.raise_for_status()
            content = str(response.json().get("message", {}).get("content", ""))
            return _strip_think(content)
    except Exception as error:
        return f"[study-answer error: {error}]"


def _source_already_ingested(source: str, scope: str) -> bool:
    """Idempotent ingestion: a source is skipped when its chunks are already in the room
    (spaced-repetition re-runs re-test without re-writing; ADR epoch-xi design)."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM memories WHERE kind = 'study' AND IFNULL(scope,'') = ? "
        "AND source_text LIKE ?", (scope or "", f"{source}#%"),
    ).fetchone()
    conn.close()
    return bool(row and row["n"])


def run_study_cycle(lesson_id: str, *, comprehension: bool = True,
                    study_model: Optional[str] = None) -> Dict[str, Any]:
    curriculum = tutelage.load_curriculum(tutelage.DEFAULT_CURRICULUM_PATH)
    found = tutelage.find_lesson(curriculum, lesson_id)
    if found is None:
        raise LookupError(f"Unknown lesson: {lesson_id}")
    subject, lesson = found["subject"], found["lesson"]
    cycles = tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH)
    missing = tutelage.unmet_prerequisites(lesson, cycles)
    if missing:
        raise PermissionError(f"Prerequisite lesson(s) not passed: {', '.join(missing)}")

    scope = subject.get("scope") or subject.get("id")
    user_id = "tutelage"
    started_at = utc_now()
    conversation_id = create_conversation(user_id=user_id, title=f"Lesson: {lesson.get('title')}", scope=scope)

    def retrieve(question: str) -> List[Dict[str, Any]]:
        return search_memories(query=question, conversation_id=conversation_id,
                               user_id=user_id, k=8, scope=scope)

    quiz = lesson.get("quiz", [])
    recall_pre = tutelage.grade_recall(quiz, retrieve)

    sources_ingested = []
    chunks_written = 0
    for source in lesson.get("sources", []):
        if _source_already_ingested(source, scope):
            sources_ingested.append({"source": source, "chunks": 0, "skipped": "already ingested"})
            continue
        text = tutelage.read_source(source)
        chunks = tutelage.chunk_text(text)
        for index, chunk in enumerate(chunks, start=1):
            save_memory(conversation_id=conversation_id, user_id=user_id, kind="study",
                        source_text=f"{source}#chunk{index}", summary_text=chunk,
                        score=0.6, scope=scope)
        sources_ingested.append({"source": source, "chunks": len(chunks)})
        chunks_written += len(chunks)

    recall_post = tutelage.grade_recall(quiz, retrieve)

    comprehension_result = None
    seat_model = None
    if comprehension:
        seat_model = study_model or OLLAMA_STUDY_MODEL or model_control.select_chat_model()

        def answer(question: str) -> str:
            notes = [m.get("summary_text", "") for m in retrieve(question)[:4]]
            return study_answer(seat_model, question, notes)

        comprehension_result = tutelage.grade_comprehension(quiz, answer)
        comprehension_result["model"] = seat_model

    threshold = float(lesson.get("pass_threshold", 0.8))
    gate_scores = [recall_post["score"]] + ([comprehension_result["score"]] if comprehension_result else [])
    status = "passed" if min(gate_scores) >= threshold else "failed"

    record = {
        "id": str(uuid.uuid4()),
        "lesson_id": lesson_id,
        "subject_id": subject.get("id"),
        "scope": scope,
        "conversation_id": conversation_id,
        "started_at": started_at,
        "finished_at": utc_now(),
        "sources": sources_ingested,
        "chunks_written": chunks_written,
        "recall_pre": recall_pre,
        "recall_post": recall_post,
        "comprehension": comprehension_result,
        "pass_threshold": threshold,
        "status": status,
    }
    cycles.setdefault("cycles", []).append(record)
    tutelage.save_study_cycles(cycles, tutelage.DEFAULT_STUDY_CYCLES_PATH)
    return record


# Epoch X — consolidation (ADR 0023). persist_learning writes several conversational memories per
# exchange, so near-duplicate residue accumulates. An operator-invoked scan finds near-duplicate
# clusters (same kind + room + user, cosine >= a high floor), keeps the NEWEST row as the
# representative, and PROPOSES the older ones into the existing supersession review queue
# (origin='consolidation'). Batch consolidation never auto-hides anything — every proposal awaits
# explicit approval, and approved rows remain restorable.
MEMORY_CONSOLIDATION_THRESHOLD = float(os.getenv("MEMORY_CONSOLIDATION_THRESHOLD", "0.95"))


def consolidation_scan(*, threshold: Optional[float] = None, kinds: Optional[List[str]] = None,
                       max_rows: int = 500) -> Dict[str, int]:
    """Propose near-duplicate memories for consolidation. Deterministic, greedy newest-first
    clustering within (kind, room, user); returns summary counts."""
    floor = threshold if threshold is not None else MEMORY_CONSOLIDATION_THRESHOLD
    if not (0.0 < floor <= 1.0):
        raise ValueError("threshold must be in (0, 1].")
    conn = get_db()
    cur = conn.cursor()
    clauses = ["(superseded IS NULL OR superseded = 0)"]
    params: List[Any] = []
    if kinds:
        clauses.append("kind IN (" + ",".join("?" * len(kinds)) + ")")
        params.extend(kinds)
    params.append(max(1, min(int(max_rows), 2000)))
    rows = cur.execute(
        "SELECT id, kind, scope, user_id, embedding_json, created_at FROM memories "
        "WHERE " + " AND ".join(clauses) + " ORDER BY created_at DESC LIMIT ?",
        params,
    ).fetchall()
    already = {r["old_id"] for r in cur.execute(
        "SELECT old_id FROM supersession_candidates WHERE status IN ('pending', 'approved', 'auto')"
    ).fetchall()}

    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    parsed = 0
    for row in rows:
        try:
            emb = json.loads(row["embedding_json"])
        except Exception:
            continue
        parsed += 1
        groups.setdefault((row["kind"], row["scope"] or "", row["user_id"] or ""), []).append(
            {"id": row["id"], "emb": emb})

    now = utc_now()
    proposed = skipped = 0
    for members in groups.values():  # members are newest-first
        assigned: set = set()
        for i, rep in enumerate(members):
            if rep["id"] in assigned:
                continue
            for older in members[i + 1:]:
                if older["id"] in assigned:
                    continue
                if cosine_similarity(rep["emb"], older["emb"]) >= floor:
                    assigned.add(older["id"])
                    if older["id"] in already:
                        skipped += 1
                        continue
                    cur.execute(
                        "INSERT INTO supersession_candidates (id, new_id, old_id, similarity, declared, "
                        "status, created_at, origin) VALUES (?, ?, ?, ?, 0, 'pending', ?, 'consolidation')",
                        (str(uuid.uuid4()), rep["id"], older["id"],
                         cosine_similarity(rep["emb"], older["emb"]), now),
                    )
                    proposed += 1
    conn.commit()
    conn.close()
    return {"rows_scanned": parsed, "groups": len(groups), "proposed": proposed,
            "skipped_existing": skipped}


def save_memory(*, conversation_id: Optional[str], user_id: Optional[str], kind: str, source_text: str, summary_text: str, score: float = 0.0, scope: Optional[str] = None) -> None:
    embedding = get_embedding(summary_text)
    new_id = str(uuid.uuid4())
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories (id, conversation_id, user_id, kind, source_text, summary_text, embedding_json, score, created_at, scope) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, conversation_id, user_id, kind, source_text, summary_text, json.dumps(embedding), score, utc_now(), scope),
    )
    if 0.0 < MEMORY_SUPERSEDE_THRESHOLD <= 1.0:
        _scan_supersession(cur, new_id=new_id, embedding=embedding, kind=kind, scope=scope,
                           user_id=user_id, conversation_id=conversation_id,
                           summary_text=summary_text)
    conn.commit()
    conn.close()


# Epoch X — hybrid memory ranking. Final score blends three bounded, tunable signals:
#   ranking_score = cosine + MEMORY_LEXICAL_WEIGHT*lexical + MEMORY_RECENCY_WEIGHT*recency
# Each added term is normalized to [0,1] so it can only reorder genuine near-ties; a weight of 0
# removes that signal (0/0 = exact pure-cosine behavior).
#   - recency (default on): breaks near-ties toward the fact that superseded an older one (ADR 0016).
#   - lexical (default OFF): exact query/memory term overlap. Evaluated in ADR 0017 (a technique from
#     MemPalace, MIT) and found to give no measured gain on the current corpus — embeddinggemma
#     already handles exact-term recall — so it ships available-but-disabled. NOTE: exact lexical does
#     NOT help typos (a misspelled token won't match either) — that is what the fuzzy term below is for.
#   - fuzzy (default OFF): character-trigram overlap, typo-tolerant. Available knob; see ADR 0017.
MEMORY_RECENCY_WEIGHT = float(os.getenv("MEMORY_RECENCY_WEIGHT", "0.05"))
MEMORY_LEXICAL_WEIGHT = float(os.getenv("MEMORY_LEXICAL_WEIGHT", "0.0"))
# Fuzzy (character-trigram overlap): typo-tolerant term — a misspelling keeps most of its trigrams,
# so it still matches. Available but OFF by default; enable if typo'd recall becomes a measured need.
MEMORY_FUZZY_WEIGHT = float(os.getenv("MEMORY_FUZZY_WEIGHT", "0.0"))

_LEXICAL_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "of", "to", "in", "on", "for",
    "and", "or", "what", "which", "who", "whom", "does", "do", "did", "how", "when",
    "where", "why", "that", "this", "it", "its", "with", "at", "by", "as", "from",
    "about", "into", "over", "use", "uses", "used", "using", "now", "currently", "current",
    "right", "you", "your", "their", "operator",
}


def _tokenize(text: Any) -> set:
    return {
        tok for tok in re.split(r"[^a-z0-9]+", str(text).lower())
        if len(tok) > 1 and tok not in _LEXICAL_STOPWORDS
    }


def _lexical_score(query_tokens: set, record: Dict[str, Any]) -> float:
    """Fraction of the query's content tokens present in the memory text — [0, 1]."""
    if not query_tokens:
        return 0.0
    text = f"{record.get('summary_text', '')} {record.get('source_text', '')}"
    overlap = query_tokens & _tokenize(text)
    return len(overlap) / len(query_tokens)


def _char_trigrams(text: Any) -> set:
    s = re.sub(r"\s+", " ", str(text).lower()).strip()
    return {s[i:i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else ({s} if s else set())


def _fuzzy_score(query_trigrams: set, record: Dict[str, Any]) -> float:
    """Fraction of the query's character trigrams present in the memory text — [0, 1].
    Typo-tolerant: a misspelling only disturbs the few trigrams around the changed char."""
    if not query_trigrams:
        return 0.0
    text = f"{record.get('summary_text', '')} {record.get('source_text', '')}"
    return len(query_trigrams & _char_trigrams(text)) / len(query_trigrams)


def _memory_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except Exception:
        return None


def _rank_memories(scored: List[Dict[str, Any]]) -> None:
    """Sort in place by the hybrid score. `lexical` is expected on each record (0 if unset);
    recency_norm is derived here from created_at across the candidate set."""
    times = [_memory_timestamp(r.get("created_at")) for r in scored]
    valid = [t for t in times if t is not None]
    tmin = min(valid) if valid else None
    span = (max(valid) - tmin).total_seconds() if len(valid) >= 2 else 0.0
    for record, ts in zip(scored, times):
        recency_norm = (ts - tmin).total_seconds() / span if (span > 0 and ts is not None) else 0.0
        record["recency_norm"] = recency_norm
        record["ranking_score"] = (
            record["similarity"]
            + MEMORY_LEXICAL_WEIGHT * record.get("lexical", 0.0)
            + MEMORY_FUZZY_WEIGHT * record.get("fuzzy", 0.0)
            + MEMORY_RECENCY_WEIGHT * recency_norm
        )
    scored.sort(key=lambda item: item["ranking_score"], reverse=True)


def search_memories(*, query: str, conversation_id: Optional[str], user_id: Optional[str], k: int = MAX_MEMORY_RESULTS, scope: Optional[str] = None, include_global: bool = True) -> List[Dict[str, Any]]:
    query_embedding = get_embedding(query)
    query_tokens = _tokenize(query) if MEMORY_LEXICAL_WEIGHT > 0 else set()
    query_trigrams = _char_trigrams(query) if MEMORY_FUZZY_WEIGHT > 0 else set()
    # Scope = MemPalace's "room": recall within a topic/subject when a scope is given (ADR 0019).
    # Omitting scope preserves prior behavior (recall across all of the user's/conversation's rooms).
    # With a scope, unscoped ("global wing") memories are included by default — room-agnostic facts
    # like operator preferences stay recallable in every room; OTHER rooms stay excluded (ADR 0020).
    clauses = ["(superseded IS NULL OR superseded = 0)"]
    params: List[Any] = []
    if user_id:
        clauses.append("(user_id = ? OR conversation_id = ?)")
        params.extend([user_id, conversation_id])
    else:
        clauses.append("conversation_id = ?")
        params.append(conversation_id)
    if scope is not None:
        if include_global:
            clauses.append("(scope = ? OR scope IS NULL)")
        else:
            clauses.append("scope = ?")
        params.append(scope)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM memories WHERE " + " AND ".join(clauses) + " ORDER BY created_at DESC LIMIT 250",
        params,
    )
    rows = cur.fetchall()
    conn.close()
    scored = []
    for row in rows:
        try:
            emb = json.loads(row["embedding_json"])
        except Exception:
            continue
        record = dict(row)
        record["similarity"] = cosine_similarity(query_embedding, emb)
        if MEMORY_LEXICAL_WEIGHT > 0:
            record["lexical"] = _lexical_score(query_tokens, record)
        if MEMORY_FUZZY_WEIGHT > 0:
            record["fuzzy"] = _fuzzy_score(query_trigrams, record)
        scored.append(record)
    _rank_memories(scored)
    return scored[:k]


def should_enable_web_search(user_message: str) -> bool:
    lowered = user_message.lower()
    triggers = ["latest", "current", "today", "recent", "news", "right now", "this week", "price", "weather", "who is", "what happened", "search"]
    return any(token in lowered for token in triggers)


def search_web(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS) -> List[Dict[str, str]]:
    if not ENABLE_WEB_SEARCH:
        return []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            items = []
            for item in results:
                items.append({"title": item.get("title", ""), "url": item.get("href", ""), "snippet": item.get("body", "")})
            return items
    except Exception:
        return []




class TurningEngine:
    @staticmethod
    def infer_user_style(message: str) -> str:
        lowered = message.lower()
        if len(message) < 80:
            return "concise"
        if any(word in lowered for word in ["deep", "detailed", "system", "architecture", "explain thoroughly"]):
            return "analytical"
        return "balanced"

    @staticmethod
    def infer_intent(message: str) -> str:
        lowered = message.lower()
        if any(word in lowered for word in ["build", "code", "python", "api", "deploy", "docker"]):
            return "The user wants something concrete and operational."
        if any(word in lowered for word in ["design", "strategy", "framework", "architecture"]):
            return "The user wants structured thinking and design clarity."
        if any(word in lowered for word in ["why", "understand", "explain"]):
            return "The user wants explanation and conceptual grounding."
        return "The user wants a useful response aligned to their apparent goal."

    @staticmethod
    def clarify_request(message: str) -> str:
        return "Respond in a way that shows understanding first, then provides a practical answer, then leaves the user with a clear next move."

    @staticmethod
    def reflect_response(user_message: str, assistant_message: str) -> Tuple[str, float]:
        score = 1.0
        notes = []
        if len(assistant_message) < 180:
            notes.append("The answer may be too brief for the request.")
            score -= 0.2
        if len(assistant_message) > 4000:
            notes.append("The answer may be overly long.")
            score -= 0.1
        lowered = user_message.lower()
        if any(word in lowered for word in ["code", "python", "api"]) and "```" not in assistant_message:
            notes.append("The user asked for implementation-oriented help; code blocks may have improved the answer.")
            score -= 0.2
        if not notes:
            notes.append("The response appears appropriately scoped and aligned.")
        summary = "Reflection: " + " ".join(notes)
        return summary, max(0.0, min(1.0, score))


def build_memory_block(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return "No especially relevant long-term memory found."
    return "\n".join(f"{i}. [{m['kind']}] {m['summary_text']} (similarity={m['similarity']:.3f})" for i, m in enumerate(memories, start=1))


def build_history_block(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No prior conversation history."
    return "\n".join(f"{item['role'].upper()}: {item['content']}" for item in history)


def build_adaptive_guidance(*, user_message: str, memories: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    style = user_profile.get("style", "balanced")
    memory_available = len(memories) > 0
    guidance = {
        "identity": "Default to 0M3-G4-ARC unless neutrality is contextually better.",
        "style": style,
        "memory_available": memory_available,
        "response_mode": "direct",
        "clarification_bias": False,
        "memory_notice": None,
        "web_search_recommended": False,
    }
    lowered = user_message.lower()
    if not memory_available:
        guidance["memory_notice"] = "Prior semantic memory is limited or unavailable for this turn."
    if should_enable_web_search(user_message):
        guidance["web_search_recommended"] = True
    if any(word in lowered for word in ["maybe", "not sure", "unclear", "confused", "help me think"]):
        guidance["response_mode"] = "careful"
        guidance["clarification_bias"] = True
    if style == "analytical":
        guidance["response_mode"] = "structured"
    return guidance


def build_backend_awareness_preferences(user_profile: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    preferences = dict(user_profile.get("preferences", {}) or {})
    state = {
        "backend_port": preferences.get("backend_port"),
        "backend_health": preferences.get("backend_health"),
    }
    updated_state = apply_backend_port_statement(state, user_message)

    if updated_state.get("backend_port") is not None:
        preferences["backend_port"] = updated_state["backend_port"]

    if updated_state.get("backend_health") is not None:
        preferences["backend_health"] = updated_state["backend_health"]

    declarations = extract_runtime_declarations(user_message)
    backend_declared = next((item for item in declarations if item.get("key") == "backend_health"), None)
    if backend_declared is not None:
        preferences["backend_health"] = {
            "status": backend_declared.get("value"),
            "source": "user",
            "state_type": "declared",
            "notes": backend_declared.get("notes") or "Reported by user; not independently verified.",
        }

    return preferences


REASONING_SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "reasoning_snapshot.json"


def _load_reasoning_snapshot() -> Optional[Dict[str, Any]]:
    try:
        if REASONING_SNAPSHOT_PATH.exists():
            return json.loads(REASONING_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _persist_reasoning_snapshot(result: Optional[Dict[str, Any]]) -> None:
    try:
        if result is not None:
            REASONING_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REASONING_SNAPSHOT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except Exception:
        pass


# Restored at startup so the Command Deck's evidence/reasoning panels do not go dark
# after a backend restart — visibility must not have amnesia (ADR-IX-004).
latest_reasoning_result: Optional[Dict[str, Any]] = _load_reasoning_snapshot()
latest_planning_result: Optional[Dict[str, Any]] = None
latest_decision_result: Optional[Dict[str, Any]] = None
latest_deliberation_result: Optional[Dict[str, Any]] = None


BACKEND_HEALTH_CHECK_REQUEST_RE = re.compile(r"\bcan\s+you\s+perform\s+the\s+backend\s+health\s+check\b", re.IGNORECASE)
BACKEND_HEALTH_CHECK_CONFIRMATION_RE = re.compile(r"^\s*(run\s+the\s+backend\s+health\s+check|confirm\s+backend\s+health\s+check)\.?\s*$", re.IGNORECASE)
BACKEND_HEALTH_CHECK_VAGUE_RE = re.compile(r"^\s*(yes|okay|ok|sure|go\s+ahead)\.?\s*$", re.IGNORECASE)


def _backend_health_port_from_preferences(user_profile: Dict[str, Any]) -> int:
    preferences = user_profile.get("preferences", {}) or {}
    try:
        return int(preferences.get("backend_port") or 8001)
    except Exception:
        return 8001


def _create_backend_health_request(*, conversation_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
    request_store = load_tool_request_store()
    approval_store = load_tool_approval_store()
    request = build_tool_request(
        tool_name="backend_health_check",
        arguments={"port": _backend_health_port_from_preferences(user_profile)},
        requested_by="user",
        session_id=conversation_id,
    )
    approval = create_approval_request(
        request,
        request_store=request_store,
        approval_store=approval_store,
        ttl_seconds=TOOL_APPROVAL_TTL_SECONDS,
    )
    save_tool_request_store(request_store)
    save_tool_approval_store(approval_store)
    request["approval_id"] = approval["approval_id"]
    request["status"] = "awaiting_approval"
    return request


def _execute_backend_health_request(*, conversation_id: str, user_profile: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    if not ENABLE_TOOL_EXECUTION:
        return (
            "Tool execution remains disabled by runtime policy. Use the bounded tool request endpoints for inspection and approval.",
            None,
        )

    request_store = load_tool_request_store()
    approval_store = load_tool_approval_store()
    result_store = load_tool_result_store()
    pending_request = find_latest_pending_request(
        session_id=conversation_id,
        tool_name="backend_health_check",
        request_store=request_store,
        approval_store=approval_store,
    )
    if pending_request is None:
        return "No pending backend health-check request is waiting for confirmation.", None

    approve_tool_request(
        pending_request["request_id"],
        approved_by="user",
        request_store=request_store,
        approval_store=approval_store,
    )

    previous_evidence_store = _load_scoped_evidence_store(conversation_id)
    outcome = execute_backend_health_check_request(
        request_record=pending_request,
        adapter=BackendHealthCheckAdapter(),
        evidence_store=previous_evidence_store,
        approval_store=approval_store,
        request_store=request_store,
        result_store=result_store,
        previous_evidence_store=previous_evidence_store,
    )

    _persist_scoped_evidence_store(conversation_id, outcome["evidence_store"])

    global latest_reasoning_result
    latest_reasoning_result = outcome.get("reasoning_result")
    _persist_reasoning_snapshot(latest_reasoning_result)

    result = outcome["result"]
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    checked_url = output.get("checked_url") or f"http://127.0.0.1:{_backend_health_port_from_preferences(user_profile)}"

    if result.get("status") == "endpoint_mismatch":
        return (
            "The health-check result did not match the currently configured endpoint, so backend health remains unknown.",
            outcome,
        )

    if result.get("success"):
        return (
            f"The backend is verified online at {checked_url}. The health check returned HTTP {output.get('status_code') or 200}.",
            outcome,
        )

    error_text = str(output.get("error") or "connection refused")
    status_code = output.get("status_code")
    if status_code:
        return (
            f"The backend is verified offline at {checked_url}. The health check returned HTTP {status_code}.",
            outcome,
        )

    return (
        f"The backend is verified offline at {checked_url} because the connection was refused.",
        outcome,
    )


def _build_dependency_map(evidence_store: Dict[str, Any]) -> Dict[str, List[str]]:
    records = evidence_store.get("records") if isinstance(evidence_store, dict) else None
    if not isinstance(records, dict):
        records = evidence_store.get("facts") if isinstance(evidence_store, dict) else {}
    if not isinstance(records, dict):
        return {}

    dependency_map: Dict[str, List[str]] = {}
    for key, record in records.items():
        normalized = normalize_evidence_record(record)
        dependencies = normalized.get("dependencies") or []
        for dependency in dependencies:
            dependency_map.setdefault(dependency, []).append(key)
    return dependency_map


def _load_scoped_evidence_store(conversation_id: Optional[str]) -> Dict[str, Any]:
    if not conversation_id:
        return {"version": 1, "facts": {}}

    durable_store = load_evidence_store()
    session_store = load_session_evidence_store(session_id=conversation_id)
    return merge_evidence_stores(durable_store, session_store)


def _persist_scoped_evidence_store(conversation_id: Optional[str], evidence_store: Dict[str, Any]) -> None:
    if not conversation_id:
        return

    durable_store = extract_durable_evidence_store(evidence_store)
    session_store = extract_session_scoped_evidence_store(evidence_store)
    save_evidence_store(durable_store)
    save_session_evidence_store(session_id=conversation_id, store=session_store)


def _build_runtime_evidence_store(
    *,
    previous_evidence_store: Optional[Dict[str, Any]],
    preferences: Dict[str, Any],
    user_message: str,
    conversation_id: Optional[str],
) -> Dict[str, Any]:
    evidence_store = deepcopy(previous_evidence_store or load_evidence_store())
    if not isinstance(evidence_store, dict):
        evidence_store = {"version": 1, "facts": {}}

    evidence_store.setdefault("version", 1)
    evidence_store.setdefault("facts", {})
    runtime_scope = f"session:{conversation_id}" if conversation_id else "session:ephemeral"

    previous_port = normalize_evidence_record(evidence_store["facts"].get("backend_port")).get("value")
    backend_port = preferences.get("backend_port")
    backend_health = preferences.get("backend_health")

    if backend_port is not None:
        evidence_store = set_evidence(
            evidence_store,
            key="backend_port",
            record={
                "key": "backend_port",
                "value": backend_port,
                "state_type": "configured",
                "source": "user",
                "confidence": 1.0,
                "dependencies": [],
                "scope": "durable",
                "notes": "Configured backend port.",
            },
        )

    if isinstance(backend_health, dict):
        status = backend_health.get("status") or "unknown"
        source = backend_health.get("source") or "system"
        explicit_state = str(backend_health.get("state_type") or "").lower()

        if explicit_state:
            state_type = explicit_state
        elif source == "user":
            state_type = "declared"
        elif source == "health_check":
            state_type = "verified" if status == "online" else "observed" if status == "offline" else "unknown"
        else:
            state_type = "unknown"

        value = status if state_type != "unknown" else None
        confidence = float(
            backend_health.get(
                "confidence",
                1.0 if source == "user" else 0.0 if state_type == "unknown" else 1.0,
            )
        )

        evidence_store = set_evidence(
            evidence_store,
            key="backend_health",
            record={
                "key": "backend_health",
                "value": value,
                "state_type": state_type,
                "source": source,
                "confidence": confidence,
                "dependencies": ["backend_port"],
                "scope": runtime_scope,
                "notes": backend_health.get("notes", ""),
                "observed_at": backend_health.get("checked_at") if source == "health_check" else None,
                "checked_at": backend_health.get("checked_at") if source == "health_check" else None,
                "checked_url": backend_health.get("checked_url") if source == "health_check" else None,
            },
        )

    for declaration in extract_runtime_declarations(user_message):
        declaration_record = dict(declaration)
        declaration_record["scope"] = runtime_scope
        evidence_store = set_evidence(
            evidence_store,
            key=declaration["key"],
            record=declaration_record,
        )

    if previous_port is not None and backend_port is not None and previous_port != backend_port:
        evidence_store = invalidate_dependents(evidence_store, dependency_key="backend_port")

    return evidence_store


def _build_deterministic_summary_reply(
    *,
    conversation_id: str,
    user_message: str,
    user_profile: Dict[str, Any],
    intent: str,
) -> Tuple[str, Dict[str, Any]]:
    previous_evidence_store = _load_scoped_evidence_store(conversation_id)
    evidence_store = _build_runtime_evidence_store(
        previous_evidence_store=previous_evidence_store,
        preferences=user_profile.get("preferences", {}),
        user_message=user_message,
        conversation_id=conversation_id,
    )
    _persist_scoped_evidence_store(conversation_id, evidence_store)
    goal_store = load_goal_store()
    knowledge_graph = load_graph()
    reasoning_result = run_reasoning_pipeline(
        evidence_store=evidence_store,
        goal_store=goal_store,
        previous_evidence_store=previous_evidence_store,
        dependency_map=_build_dependency_map(evidence_store),
    )

    summary = build_current_state_summary(
        identity_profile=get_identity_profile(user_profile),
        evidence_store=evidence_store,
        goal_store=goal_store,
        knowledge_graph=knowledge_graph,
        reasoning_result=reasoning_result,
    )

    summary = select_summary_for_intent(summary, intent)

    return render_current_state_summary(summary), reasoning_result


def build_ollama_messages(*, history, user_message, user_profile, memories, web_results, conversation_id: Optional[str] = None):
    adaptive = build_adaptive_guidance(
        user_message=user_message,
        memories=memories,
        user_profile=user_profile,
    )

    constitution_block = constitution_prompt()
    backend_state_block = "Backend state:\n- Configured port: unknown\n- Runtime health: unknown\n- Verification: none"
    reasoning_block = "Reasoning summary unavailable for this turn."
    try:
        previous_evidence_store = _load_scoped_evidence_store(conversation_id)
        current_evidence_store = _build_runtime_evidence_store(
            previous_evidence_store=previous_evidence_store,
            preferences=user_profile.get("preferences", {}),
            user_message=user_message,
            conversation_id=conversation_id,
        )
        prompt_reasoning_result = run_reasoning_pipeline(
            evidence_store=current_evidence_store,
            goal_store=load_goal_store(),
            previous_evidence_store=previous_evidence_store,
            dependency_map=_build_dependency_map(current_evidence_store),
        )
        backend_state_block = render_backend_state_for_prompt(
            current_evidence_store,
            prompt_reasoning_result,
        )
        if ENABLE_REASONING_CONTEXT:
            reasoning_block = build_reasoning_prompt_context(prompt_reasoning_result)
    except Exception as exc:
        print("Prompt reasoning warning:", repr(exc))

    memory_block = build_memory_block(memories)
    history_block = build_history_block(history)

    web_block = "\n".join(
        f"- {item['title']}: {item['snippet']} ({item['url']})"
        for item in web_results
    ) or "No web search results."

    # Identity and personality integration
    identity_decision = classify_identity_intent(user_message)
    identity_block = identity_prompt_fragment(identity_decision)

    active_personality = get_active_personality(ACTIVE_PERSONALITY_MODE)
    personality_block = build_personality_prompt(active_personality)

    # --- AGE GROUP ---
    age_group = user_profile.get("preferences", {}).get("age_group", "adult")

    # --- SYSTEM MESSAGE ---
    system_message = f"""
{constitution_block}

{backend_state_block}

{SYSTEM_PROMPT}

Acknowledgement guidance:
- For a project statement, respond with a brief acknowledgement that the project is recognized.
- For a goal statement, respond with a brief acknowledgement that the goal is tracked.
- For a configuration statement, acknowledge the configured value and note that it is configuration knowledge, not proof of runtime health.
- If a user reports runtime status (for example online, connected, ready, readable), treat it as user-reported declared evidence.
- If a user reports model installation, treat it only as declared installation evidence.
- Do not infer availability, loaded state, health, routability, or readiness from installation alone.
- Do not claim a model is available, loaded, healthy, routable, or ready unless current evidence explicitly supports that state.
- Do not claim that verification occurred unless verification evidence exists.
- If verification evidence is absent, explicitly state that status has not been independently verified.
- Do not ask a follow-up question unless the user explicitly needs help with the next step.
- Do not append a curiosity question unless the feature flag is enabled and a single curated candidate is available.
- If curiosity suggestions are disabled, do not ask whether to run checks.
- For declarative goal and state statements, acknowledge concisely without interviews.

Runtime identity decision:
{identity_block}

Active personality:
{personality_block}

Identity enforcement:
- Never describe yourself as a generic chatbot.
- Default identity is 0M3-G4-ARC.
- Maintain the Turning architecture in tone and reasoning.

User profile:
- Age group: {age_group}

Adapt communication style:
- child: simple, concrete, example-driven
- teen: clear, engaging, slightly informal
- adult: structured, precise, efficient

Adaptive guidance:
- user_style: {user_profile.get('style', 'balanced')}
- response_mode: {adaptive['response_mode']}
- clarification_bias: {adaptive['clarification_bias']}
- memory_notice: {adaptive['memory_notice']}
- web_search_recommended: {adaptive['web_search_recommended']}

Relevant memory:
{memory_block}

Recent history:
{history_block}

Web search results:
{web_block}

Reasoning context:
{reasoning_block}
""".strip()

    messages = [{"role": "system", "content": system_message}]

    # Add history
    for msg in history:
        if msg["role"] in {"user", "assistant"}:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({"role": "user", "content": user_message})

    # User and assistant language is kept byte-for-byte at the message-content
    # level. Transport serialization is the only normalization performed here.
    return messages


def build_direct_model_messages(*, history: List[Dict[str, str]], user_message: str) -> List[Dict[str, str]]:
    """Build an unaugmented chat transcript for the operator-selected direct mode."""
    messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg.get("role") in {"user", "assistant"}
    ]
    messages.append({"role": "user", "content": user_message})
    return messages


class ModelUnavailableError(RuntimeError):
    pass


def _model_unavailable_message(model: str) -> str:
    return (
        f"Unable to load {model}.\n\n"
        "Automatic fallback is disabled.\n\n"
        "Please choose another conversational model."
    )


def generate_response_text(*, history: List[Dict[str, str]], user_message: str, user_profile: Dict[str, Any], memories: List[Dict[str, Any]], conversation_id: Optional[str] = None, direct_mode: bool = False) -> str:
    if direct_mode:
        messages = build_direct_model_messages(history=history, user_message=user_message)
    else:
        web_results = search_web(user_message) if should_enable_web_search(user_message) else []
        messages = build_ollama_messages(history=history, user_message=user_message, user_profile=user_profile, memories=memories, web_results=web_results, conversation_id=conversation_id)
    requested_model = select_chat_model()
    attempts = [requested_model]
    if not direct_mode and settings.allow_automatic_model_fallback and settings.automatic_model_fallback_model != requested_model:
        attempts.append(settings.automatic_model_fallback_model)
    started = time.perf_counter()
    last_error: Optional[Exception] = None
    with httpx.Client(timeout=120.0) as client:
        for index, candidate in enumerate(attempts):
            try:
                response = client.post(f"{OLLAMA_BASE_URL}/chat", json={"model": candidate, "messages": messages, "stream": False, "think": OLLAMA_THINK})
                response.raise_for_status()
                data = response.json()
                actual_model = str(data.get("model") or candidate)
                if actual_model != candidate:
                    raise RuntimeError(f"Provider returned {actual_model} after {candidate} was selected.")
                model_control.record(ConversationTelemetry(
                    requested_model=requested_model,
                    selected_model=requested_model,
                    actual_model=actual_model,
                    response_time=round(time.perf_counter() - started, 6),
                    tokens=data.get("eval_count"),
                    fallback_used=index > 0,
                ))
                return data["message"]["content"]
            except Exception as exc:
                last_error = exc
    model_control.record(ConversationTelemetry(
        requested_model=requested_model,
        selected_model=requested_model,
        actual_model="",
        response_time=round(time.perf_counter() - started, 6),
        tokens=None,
        fallback_used=len(attempts) > 1,
    ))
    if direct_mode or not settings.allow_automatic_model_fallback:
        raise ModelUnavailableError(_model_unavailable_message(requested_model)) from last_error
    raise ModelUnavailableError(f"Unable to load configured conversational models: {attempts}.") from last_error


def stream_response_text(*, history: List[Dict[str, str]], user_message: str, user_profile: Dict[str, Any], memories: List[Dict[str, Any]], conversation_id: Optional[str] = None, direct_mode: bool = False) -> Generator[str, None, None]:
    if direct_mode:
        web_results: List[Dict[str, Any]] = []
        messages = build_direct_model_messages(history=history, user_message=user_message)
    else:
        web_results = search_web(user_message) if should_enable_web_search(user_message) else []
        messages = build_ollama_messages(history=history, user_message=user_message, user_profile=user_profile, memories=memories, web_results=web_results, conversation_id=conversation_id)
        yield f"data: {json.dumps({'type': 'phase', 'name': 'whisper'})}\n\n"
        sanitized_memories = [{"kind": m.get("kind"), "summary_text": m.get("summary_text"), "similarity": m.get("similarity"), "created_at": m.get("created_at")} for m in memories]
        yield f"data: {json.dumps({'type': 'memory', 'items': sanitized_memories})}\n\n"
        if web_results:
            yield f"data: {json.dumps({'type': 'web', 'items': web_results})}\n\n"
        yield f"data: {json.dumps({'type': 'phase', 'name': 'bridge'})}\n\n"
        yield f"data: {json.dumps({'type': 'phase', 'name': 'mirror'})}\n\n"
        yield f"data: {json.dumps({'type': 'phase', 'name': 'guide'})}\n\n"
    requested_model = select_chat_model()
    attempts = [requested_model]
    if not direct_mode and settings.allow_automatic_model_fallback and settings.automatic_model_fallback_model != requested_model:
        attempts.append(settings.automatic_model_fallback_model)
    started = time.perf_counter()
    last_error: Optional[Exception] = None
    with httpx.Client(timeout=None) as client:
        for index, candidate in enumerate(attempts):
            collected: List[str] = []
            try:
                with client.stream("POST", f"{OLLAMA_BASE_URL}/chat", json={"model": candidate, "messages": messages, "stream": True, "think": OLLAMA_THINK}) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        actual_model = str(data.get("model") or candidate)
                        if actual_model != candidate:
                            raise RuntimeError(f"Provider returned {actual_model} after {candidate} was selected.")
                        msg = data.get("message", {})
                        chunk = msg.get("content", "")
                        if chunk:
                            collected.append(chunk)
                            yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
                        if data.get("done"):
                            final_text = "".join(collected)
                            model_control.record(ConversationTelemetry(
                                requested_model=requested_model,
                                selected_model=requested_model,
                                actual_model=actual_model,
                                response_time=round(time.perf_counter() - started, 6),
                                tokens=data.get("eval_count"),
                                fallback_used=index > 0,
                            ))
                            if not direct_mode:
                                yield f"data: {json.dumps({'type': 'phase', 'name': 'silence'})}\n\n"
                            yield f"data: {json.dumps({'type': 'done', 'text': final_text})}\n\n"
                            return
            except Exception as exc:
                last_error = exc
                # Never splice another model into a response already shown to the user.
                if collected:
                    model_control.record(ConversationTelemetry(
                        requested_model=requested_model,
                        selected_model=requested_model,
                        actual_model=candidate,
                        response_time=round(time.perf_counter() - started, 6),
                        tokens=None,
                        fallback_used=index > 0,
                    ))
                    raise
    model_control.record(ConversationTelemetry(
        requested_model=requested_model,
        selected_model=requested_model,
        actual_model="",
        response_time=round(time.perf_counter() - started, 6),
        tokens=None,
        fallback_used=len(attempts) > 1,
    ))
    if direct_mode or not settings.allow_automatic_model_fallback:
        raise ModelUnavailableError(_model_unavailable_message(requested_model)) from last_error
    raise ModelUnavailableError(f"Unable to load configured conversational models: {attempts}.") from last_error


def persist_learning(*, conversation_id: str, user_id: Optional[str], user_message: str, assistant_message: str) -> Dict[str, Any]:
    engine = TurningEngine()

    style = engine.infer_user_style(user_message)
    reflection_summary, reflection_score = engine.reflect_response(user_message, assistant_message)

    # Strategy selection
    if reflection_score < 0.55:
        strategy = "ask_for_clarification_earlier"
    elif reflection_score < 0.75:
        strategy = "be_more_structured"
    else:
        strategy = "current_strategy_effective"

    # --- AGE GROUP (hybrid logic) ---
    existing_profile = get_user_profile(user_id or "anonymous")
    age_group = existing_profile.get("preferences", {}).get("age_group")
    



    # Save updated profile
    save_user_profile(
        user_id or "anonymous",
        style,
        {
            "prefers_code": any(token in user_message.lower() for token in ["code", "python", "api"]),
            "updated_by": "interaction",
            "last_strategy": strategy,
            "last_reflection_score": reflection_score,
            "age_group": age_group,
        },
    )

    # Memory summaries — memories born in a scoped conversation inherit its room (ADR 0020).
    conversation_scope = (get_conversation_meta(conversation_id) or {}).get("scope")
    user_summary = f"User asked: {user_message[:1000]}"
    assistant_summary = f"Assistant answered: {assistant_message[:1000]}"

    for kwargs in [
        {
            "kind": "user_request",
            "source_text": user_message,
            "summary_text": user_summary,
            "score": 0.5,
        },
        {
            "kind": "assistant_response",
            "source_text": assistant_message,
            "summary_text": assistant_summary,
            "score": 0.7,
        },
        {
            "kind": "reflection",
            "source_text": assistant_message,
            "summary_text": reflection_summary,
            "score": reflection_score,
        },
        {
            "kind": "strategy",
            "source_text": user_message,
            "summary_text": f"Recommended strategy: {strategy}",
            "score": 0.8,
        },
    ]:
        try:
            save_memory(
                conversation_id=conversation_id,
                user_id=user_id,
                scope=conversation_scope,
                **kwargs,
            )
        except Exception:
            pass

    return {
        "style": style,
        "reflection": reflection_summary,
        "reflection_score": reflection_score,
        "strategy": strategy,
        "age_group": age_group,
    }


class CreateConversationRequest(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None
    scope: Optional[str] = None


class ConversationScopeRequest(BaseModel):
    scope: Optional[str] = None  # None clears the room


class SupersessionResolveRequest(BaseModel):
    action: str  # "approve" | "reject"


class StudyCycleRequest(BaseModel):
    lesson_id: str = Field(..., min_length=1)
    comprehension: bool = True
    study_model: Optional[str] = None


class ConsolidationScanRequest(BaseModel):
    threshold: Optional[float] = None  # defaults to MEMORY_CONSOLIDATION_THRESHOLD
    kinds: Optional[List[str]] = None
    max_rows: int = 500


class ConversationScopeResponse(BaseModel):
    conversation_id: str
    scope: Optional[str]


class CreateConversationResponse(BaseModel):
    conversation_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    model: Optional[str] = None
    mode: Literal["runtime", "direct"] = "runtime"


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    learning: Dict[str, Any]
    model_control: Dict[str, Any]
    mode: Literal["runtime", "direct"] = "runtime"


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[Dict[str, Any]]


class MemorySearchResponse(BaseModel):
    conversation_id: str
    memories: List[Dict[str, Any]]


app = FastAPI(title=f"{APP_NAME} API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5181", "http://127.0.0.1:5181",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(system_router)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": APP_NAME,
        "status": "ok",
        "provider": "ollama",
        "chat_model": select_chat_model(),
        "embedding_model": OLLAMA_EMBED_MODEL,
        "web_search_enabled": ENABLE_WEB_SEARCH,
    }


@app.get("/vow")
def get_vow() -> Dict[str, str]:
    return {"name": APP_NAME, "vow": VOW_OF_THE_TURNING}


@app.get("/system/reasoning")
def get_system_reasoning() -> Dict[str, Any]:
    return {"reasoning": latest_reasoning_result}


@app.get("/system/plans")
def get_system_plans() -> Dict[str, Any]:
    store = load_plan_store()
    return {"plans": list_plans(store)}


@app.get("/system/plans/{plan_id}")
def get_system_plan(plan_id: str) -> Dict[str, Any]:
    store = load_plan_store()
    plan = get_plan(store, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return {"plan": plan}


@app.get("/system/decisions")
def get_system_decisions() -> Dict[str, Any]:
    store = load_decision_store()
    return {"decisions": list_decisions(store)}


@app.get("/system/decisions/{decision_id}")
def get_system_decision(decision_id: str) -> Dict[str, Any]:
    store = load_decision_store()
    decision = get_decision(store, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return {"decision": decision}


@app.get("/system/deliberation")
def get_system_deliberation() -> Dict[str, Any]:
    store = load_deliberation_store()
    approvals = load_approval_store()
    return {
        "deliberation": store,
        "approvals": approvals,
    }


@app.get("/system/assumptions")
def get_system_assumptions() -> Dict[str, Any]:
    return {"assumptions": load_assumption_store()}


@app.get("/system/memory/supersession-candidates")
def get_supersession_candidates(status: str = "pending") -> Dict[str, Any]:
    """Supersession review surface (ADR 0021): undeclared high-similarity collisions wait here
    for an explicit operator decision; nothing is hidden from recall until approved."""
    return {"candidates": list_supersession_candidates(status=status)}


@app.post("/system/memory/supersession-candidates/{candidate_id}/resolve")
def post_resolve_supersession(candidate_id: str, req: SupersessionResolveRequest) -> Dict[str, Any]:
    if req.action not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail="action must be 'approve' or 'reject'.")
    if not resolve_supersession_candidate(candidate_id, approve=req.action == "approve"):
        raise HTTPException(status_code=404, detail="Pending candidate not found.")
    return {"candidate_id": candidate_id, "status": "approved" if req.action == "approve" else "rejected"}


@app.get("/system/tutelage/curriculum")
def get_tutelage_curriculum() -> Dict[str, Any]:
    """The operator-authored curriculum plus which lessons have been passed (ADR 0013)."""
    cycles = tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH)
    return {"curriculum": tutelage.load_curriculum(tutelage.DEFAULT_CURRICULUM_PATH),
            "passed_lessons": sorted(p for p in tutelage.passed_lessons(cycles) if p)}


@app.get("/system/tutelage/cycles")
def get_tutelage_cycles() -> Dict[str, Any]:
    return {"cycles": tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH).get("cycles", [])}


@app.post("/system/tutelage/cycles")
def post_tutelage_cycle(req: StudyCycleRequest) -> Dict[str, Any]:
    """Run one deterministic study cycle for a lesson (ingest -> room memories -> recall test)."""
    try:
        return run_study_cycle(req.lesson_id, comprehension=req.comprehension,
                               study_model=req.study_model)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except FileNotFoundError as error:
        raise HTTPException(status_code=422, detail=f"Lesson source missing: {error}")


@app.post("/system/memory/consolidation-scan")
def post_consolidation_scan(req: ConsolidationScanRequest) -> Dict[str, Any]:
    """Operator-invoked consolidation scan (ADR 0023): proposes near-duplicate memories into the
    supersession review queue (origin='consolidation'). Nothing is hidden without approval."""
    try:
        return consolidation_scan(threshold=req.threshold, kinds=req.kinds, max_rows=req.max_rows)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.get("/system/memory/rooms")
def get_memory_rooms() -> Dict[str, Any]:
    """Rooms overview (ADR 0022): every scope with active/superseded counts; None = the global wing."""
    return {"rooms": memory_rooms()}


@app.get("/system/memory")
def get_memory_browse(scope: Optional[str] = None, unscoped: bool = False, kind: Optional[str] = None,
                      status: str = "active", q: Optional[str] = None,
                      limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Human-readable memory browse (ADR 0022). status: active | superseded | all."""
    if status not in ("active", "superseded", "all"):
        raise HTTPException(status_code=422, detail="status must be 'active', 'superseded', or 'all'.")
    return {"memories": browse_memories(scope=scope, unscoped=unscoped, kind=kind,
                                        status=status, q=q, limit=limit, offset=offset)}


@app.get("/system/memory/{memory_id}")
def get_memory_by_id(memory_id: str) -> Dict[str, Any]:
    record = get_memory_detail(memory_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return record


@app.post("/system/memory/{memory_id}/scope")
def post_memory_scope(memory_id: str, req: ConversationScopeRequest) -> Dict[str, Any]:
    """Re-room a memory (null moves it to the global wing). Explicit operator action, audited."""
    if not set_memory_scope(memory_id, req.scope):
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"memory_id": memory_id, "scope": req.scope}


@app.post("/system/memory/{memory_id}/restore")
def post_memory_restore(memory_id: str) -> Dict[str, Any]:
    """Reverse a supersession — the memory returns to active recall. Audited."""
    if not restore_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found or not superseded.")
    return {"memory_id": memory_id, "restored": True}


@app.post("/conversations", response_model=CreateConversationResponse)
def new_conversation(req: CreateConversationRequest) -> CreateConversationResponse:
    cid = create_conversation(user_id=req.user_id, title=req.title, scope=req.scope)
    return CreateConversationResponse(conversation_id=cid)


@app.post("/conversations/{conversation_id}/scope", response_model=ConversationScopeResponse)
def assign_conversation_scope(conversation_id: str, req: ConversationScopeRequest) -> ConversationScopeResponse:
    """Assign or clear (scope=null) the conversation's memory room — an explicit operator
    action; scope is never inferred (ADR 0020)."""
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    set_conversation_scope(conversation_id, req.scope)
    return ConversationScopeResponse(conversation_id=conversation_id, scope=req.scope)


@app.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
def get_conversation(conversation_id: str) -> ConversationHistoryResponse:
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationHistoryResponse(conversation_id=conversation_id, messages=get_full_messages(conversation_id))


@app.get("/conversations/{conversation_id}/memories", response_model=MemorySearchResponse)
def get_conversation_memories(conversation_id: str, q: str) -> MemorySearchResponse:
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    meta = get_conversation_meta(conversation_id)
    memories = search_memories(query=q, conversation_id=conversation_id, user_id=meta.get("user_id") if meta else None, scope=meta.get("scope") if meta else None)
    sanitized = [{"kind": m["kind"], "summary_text": m["summary_text"], "similarity": m["similarity"], "created_at": m["created_at"]} for m in memories]
    return MemorySearchResponse(conversation_id=conversation_id, memories=sanitized)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    global latest_reasoning_result, latest_planning_result, latest_decision_result, latest_deliberation_result
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = create_conversation(user_id=req.user_id)
    elif not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    add_message(conversation_id, "user", req.message)
    direct_mode = req.mode == "direct"
    try:
        if direct_mode:
            if req.model and req.model != DIRECT_CHAT_MODEL:
                raise ValueError(f"Direct mode is pinned to {DIRECT_CHAT_MODEL}.")
            model_control.set_active_model(DIRECT_CHAT_MODEL)
        elif req.model:
            model_control.set_active_model(req.model)
        explicit_model_switch = None if direct_mode else model_control.parse_explicit_switch(req.message)
        if explicit_model_switch:
            model_control.set_active_model(explicit_model_switch)
            reply = f"Active conversational model set to {explicit_model_switch}. Model Lock remains engaged."
            add_message(conversation_id, "assistant", reply)
            learning = persist_learning(
                conversation_id=conversation_id,
                user_id=req.user_id,
                user_message=req.message,
                assistant_message=reply,
            )
            return ChatResponse(
                conversation_id=conversation_id,
                reply=reply,
                learning=learning,
                model_control=model_control.status(),
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    history = get_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)
    if direct_mode:
        try:
            reply = generate_response_text(
                history=history[:-1],
                user_message=req.message,
                user_profile={},
                memories=[],
                conversation_id=conversation_id,
                direct_mode=True,
            )
        except ModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        add_message(conversation_id, "assistant", reply)
        return ChatResponse(
            conversation_id=conversation_id,
            reply=reply,
            learning={},
            model_control=model_control.status(),
            mode="direct",
        )
    meta = get_conversation_meta(conversation_id) or {}
    effective_user_id = req.user_id or meta.get("user_id")
    user_profile = get_user_profile(effective_user_id)
    user_profile = {**user_profile, "preferences": build_backend_awareness_preferences(user_profile, req.message)}
    memories = search_memories(query=req.message, conversation_id=conversation_id, user_id=effective_user_id, scope=meta.get("scope"))
    summary_intent = detect_summary_intent(req.message)
    planning_intent = detect_planning_intent(req.message)
    deliberation_intent = detect_deliberation_intent(req.message)
    declaration_keys = {
        str(item.get("key") or "")
        for item in extract_runtime_declarations(req.message)
        if isinstance(item, dict)
    }
    execution_request_pattern = re.compile(r"\b(execute|run\s+it\s+now|implement\s+now|apply\s+now|deploy\s+now)\b", re.IGNORECASE)
    tool_request_pattern = re.compile(r"\b(tool|backend\s+health\s+check|system\s+tools|tool\s+request)\b", re.IGNORECASE)
    deterministic_runtime_request = bool(
        (ENABLE_PLANNING_PIPELINE and not ENABLE_PLAN_EXECUTION and planning_intent)
        or (ENABLE_DELIBERATION_PIPELINE and not ENABLE_PLAN_EXECUTION and deliberation_intent)
        or (ENABLE_PLANNING_PIPELINE and not ENABLE_PLAN_EXECUTION and "vision_model_selected" in declaration_keys)
        or (not ENABLE_PLAN_EXECUTION and execution_request_pattern.search(req.message))
        or (ENABLE_TOOL_FRAMEWORK and not ENABLE_TOOL_EXECUTION and tool_request_pattern.search(req.message))
    )
    try:
        reasoning_output = None
        if summary_intent in {"state_summary", "uncertainty_summary"}:
            reply, reasoning_output = _build_deterministic_summary_reply(
                conversation_id=conversation_id,
                user_message=req.message,
                user_profile=user_profile,
                intent=summary_intent,
            )
        elif BACKEND_HEALTH_CHECK_CONFIRMATION_RE.match(req.message or ""):
            reply, execution_outcome = _execute_backend_health_request(conversation_id=conversation_id, user_profile=user_profile)
            if execution_outcome is not None:
                reasoning_output = execution_outcome.get("reasoning_result")
        elif BACKEND_HEALTH_CHECK_REQUEST_RE.search(req.message or ""):
            _create_backend_health_request(conversation_id=conversation_id, user_profile=user_profile)
            reply = "I can run a bounded localhost health check against the configured backend endpoint. Confirm by saying: Run the backend health check."
        else:
            deterministic_ack = build_declarative_acknowledgement(req.message)
            if deterministic_ack:
                reply = deterministic_ack
            elif deterministic_runtime_request:
                # Dedicated runtime requests are answered by their deterministic
                # subsystem below; no conversational model is called or discarded.
                reply = ""
            else:
                reply = generate_response_text(history=history[:-1], user_message=req.message, user_profile=user_profile, memories=memories, conversation_id=conversation_id)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if summary_intent in {"state_summary", "uncertainty_summary"} and reasoning_output is not None:
        latest_reasoning_result = reasoning_output
        _persist_reasoning_snapshot(latest_reasoning_result)
    elif ENABLE_REASONING_PIPELINE:
        try:
            previous_evidence_store = _load_scoped_evidence_store(conversation_id)
            evidence_store = _build_runtime_evidence_store(
                previous_evidence_store=previous_evidence_store,
                preferences=user_profile.get("preferences", {}),
                user_message=req.message,
                conversation_id=conversation_id,
            )
            _persist_scoped_evidence_store(conversation_id, evidence_store)
            goal_store = load_goal_store()
            reasoning_output = run_reasoning_pipeline(
                evidence_store=evidence_store,
                goal_store=goal_store,
                previous_evidence_store=previous_evidence_store,
                dependency_map=_build_dependency_map(evidence_store),
            )
            latest_reasoning_result = reasoning_output
            _persist_reasoning_snapshot(latest_reasoning_result)
        except Exception as exc:
            print("Reasoning pipeline warning:", repr(exc))
            reasoning_output = None

    if ENABLE_PLANNING_PIPELINE and not ENABLE_PLAN_EXECUTION:
        try:
            planning_output = run_planning_pipeline(
                goal_store=load_goal_store(),
                evidence_store=_load_scoped_evidence_store(conversation_id),
                reasoning_result=reasoning_output or {},
                plan_store=load_plan_store(),
                decision_store=load_decision_store(),
                user_message=req.message,
                session_id=conversation_id,
                persist=True,
            )
            latest_planning_result = planning_output
            latest_decision_result = {
                "decisions": list_decisions(load_decision_store()),
            }

            if planning_intent:
                active_plan = planning_output.get("selected_plan") or planning_output.get("active_plan")
                if planning_intent == "plan_summary":
                    if active_plan:
                        reply = render_plan(active_plan)
                    elif planning_output.get("selection_message"):
                        reply = planning_output["selection_message"]
                    else:
                        reply = "No active plan exists."
                elif planning_intent == "next_plan_action":
                    reply = render_next_action(planning_output)
                elif planning_intent == "plan_blockers":
                    blocked = planning_output.get("blocked_steps") or []
                    if blocked:
                        blocker_lines = [f"- {item.get('title')}: {', '.join(item.get('blockers') or [])}" for item in blocked]
                        reply = "Current blockers:\n" + "\n".join(blocker_lines)
                    else:
                        reply = "Current blockers: none."
                elif planning_intent == "decision_explanation":
                    decisions = [
                        item
                        for item in list_decisions(load_decision_store(), status="active")
                        if str(item.get("source") or "") == "explicit_user_choice"
                    ]
                    if decisions:
                        reply = render_decision(decisions[0])
                    else:
                        reply = "No active model choice has been recorded yet."
                elif planning_intent == "plan_revision_request":
                    revisions = planning_output.get("revisions") or []
                    if revisions:
                        first = revisions[0]
                        reply = f"Plan revised: {first.get('reason')}"
                    else:
                        reply = "No deterministic revision was required for the active plan."
                elif planning_intent == "alternative_plan_request":
                    reply = "Alternative plan requests are recognized; use explicit goal context to supersede the active plan deterministically."
                elif planning_intent == "plan_archive_request":
                    if active_plan:
                        store = archive_plan(load_plan_store(), str(active_plan.get("id")))
                        save_plan_store(store)
                        reply = f"Archived plan {active_plan.get('id')}."
                    else:
                        reply = "No active plan is available to archive."
            else:
                active_plan = planning_output.get("selected_plan") or planning_output.get("active_plan")
                if active_plan and "vision_model_selected" in declaration_keys:
                    reply = render_plan(active_plan)
        except Exception as exc:
            print("Planning pipeline warning:", repr(exc))
            planning_output = None

    if ENABLE_DELIBERATION_PIPELINE and not ENABLE_PLAN_EXECUTION:
        try:
            deliberation_output = run_deliberation_pipeline(
                goal_store=load_goal_store(),
                planning_result=planning_output or {},
                evidence_store=_load_scoped_evidence_store(conversation_id),
                user_message=req.message,
                decision_store=load_decision_store(),
                persist=True,
            )
            latest_deliberation_result = deliberation_output

            if deliberation_intent:
                recommendation = deliberation_output.get("recommendation") or {}
                candidate_plans = deliberation_output.get("candidate_plans") or []
                matrix = ((deliberation_output.get("deliberation") or {}).get("decision_matrix") or {}).get("rows") or []
                risks = (deliberation_output.get("deliberation") or {}).get("risk_assessments") or []
                approval = deliberation_output.get("approval") or {}
                assumptions_block = ((deliberation_output.get("deliberation") or {}).get("assumptions") or {}).get("active") or []

                if deliberation_intent == "deliberation_summary":
                    best = recommendation.get("plan_id")
                    reply = f"Recommendation: {best or 'none'}.\nReason: {recommendation.get('explanation') or 'No recommendation explanation recorded.'}"
                    if matrix:
                        first = matrix[0]
                        reply += f"\nTop criterion: {first.get('criterion')} (weight: {first.get('weight')})."
                elif deliberation_intent == "alternative_plan":
                    lines = [
                        f"Current recommendation: {recommendation.get('plan_id') or 'none'}",
                        "Alternatives:",
                    ]
                    alternatives = [item for item in candidate_plans if str(item.get("id") or "") != str(recommendation.get("plan_id") or "")]
                    for item in alternatives[:2]:
                        lines.append(f"- {item.get('title')} ({item.get('id')})")
                    if not alternatives:
                        lines.append("- None")
                    if risks:
                        first_risk = risks[0]
                        lines.append("Trade-offs and risks:")
                        lines.append(f"- Overall risk: {first_risk.get('overall_risk')}")
                    reply = "\n".join(lines)
                elif deliberation_intent == "assumptions":
                    if assumptions_block:
                        lines = ["Active assumptions:"]
                        for item in assumptions_block:
                            lines.append(f"- {item.get('statement')} (status: {item.get('status')}, confidence: {item.get('confidence')})")
                        reply = "\n".join(lines)
                    else:
                        reply = "Active assumptions: none."
                elif deliberation_intent == "risks":
                    if risks:
                        lines = ["Active risks:"]
                        for entry in risks[:3]:
                            for risk in entry.get("risks") or []:
                                lines.append(f"- {risk.get('risk')} (probability: {risk.get('probability')}, impact: {risk.get('impact')})")
                        reply = "\n".join(lines)
                    else:
                        reply = "Active risks: none."
                elif deliberation_intent == "approval":
                    if approval and str(approval.get("status") or "") == "approved":
                        reply = f"Approval recorded for plan {approval.get('plan_id')}. Execution remains disabled in Epoch VII."
                    else:
                        reply = "No recommendation is currently available to approve."
                elif deliberation_intent == "assumption_invalidation":
                    reply = "Recorded assumption invalidation and updated deliberation state. Execution remains disabled in Epoch VII."
        except Exception as exc:
            print("Deliberation pipeline warning:", repr(exc))
            deliberation_output = None

    if not ENABLE_PLAN_EXECUTION:
        if execution_request_pattern.search(req.message):
            reply = "Execution remains disabled in Epoch VII. Approval and decision recording are available, but actions are not executed automatically."

    if ENABLE_TOOL_FRAMEWORK and not ENABLE_TOOL_EXECUTION:
        if (
            tool_request_pattern.search(req.message)
            and not is_backend_health_query(req.message)
            and not BACKEND_HEALTH_CHECK_REQUEST_RE.search(req.message or "")
            and not BACKEND_HEALTH_CHECK_CONFIRMATION_RE.match(req.message or "")
        ):
            reply = "Tool execution remains disabled by runtime policy. Use the bounded tool request endpoints for inspection and approval."

    if reply and ENABLE_COGNITION_PIPELINE and summary_intent not in {"state_summary", "uncertainty_summary"}:
        try:
            process_completed_turn(
                user_message=req.message,
                assistant_response=reply,
                identity_profile=get_identity_profile(user_profile),
                persist=True,
            )
        except Exception as exc:
            print("Cognition pipeline warning:", repr(exc))

    add_message(conversation_id, "assistant", reply)
    learning = persist_learning(conversation_id=conversation_id, user_id=effective_user_id, user_message=req.message, assistant_message=reply)

    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply,
        learning=learning,
        model_control=model_control.status(),
        mode="runtime",
    )


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    conversation_id = req.conversation_id

    if not conversation_id:
        conversation_id = create_conversation(user_id=req.user_id)
    elif not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    add_message(conversation_id, "user", req.message)
    direct_mode = req.mode == "direct"
    try:
        if direct_mode:
            if req.model and req.model != DIRECT_CHAT_MODEL:
                raise ValueError(f"Direct mode is pinned to {DIRECT_CHAT_MODEL}.")
            model_control.set_active_model(DIRECT_CHAT_MODEL)
        elif req.model:
            model_control.set_active_model(req.model)
        explicit_model_switch = None if direct_mode else model_control.parse_explicit_switch(req.message)
        if explicit_model_switch:
            model_control.set_active_model(explicit_model_switch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    history = get_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)
    if direct_mode:
        def direct_event_generator():
            chunks: List[str] = []
            try:
                for event in stream_response_text(
                    history=history[:-1],
                    user_message=req.message,
                    user_profile={},
                    memories=[],
                    conversation_id=conversation_id,
                    direct_mode=True,
                ):
                    yield event
                    if event.startswith("data: "):
                        payload = json.loads(event[len("data: "):].strip())
                        if payload.get("type") == "delta":
                            chunks.append(payload.get("text", ""))
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                return

            full_text = "".join(chunks)
            if full_text:
                add_message(conversation_id, "assistant", full_text)
            yield f"data: {json.dumps({'type': 'mode', 'name': 'direct', 'model': DIRECT_CHAT_MODEL})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        return observe_streaming_response(StreamingResponse(
            direct_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Conversation-Id": conversation_id,
                "X-Conversation-Mode": "direct",
            },
        ), conversation_id)

    meta = get_conversation_meta(conversation_id) or {}
    effective_user_id = req.user_id or meta.get("user_id")
    user_profile = get_user_profile(effective_user_id)
    user_profile = {**user_profile, "preferences": build_backend_awareness_preferences(user_profile, req.message)}
    memories = search_memories(
        query=req.message,
        conversation_id=conversation_id,
        user_id=effective_user_id,
        scope=meta.get("scope"),
    )
    summary_intent = detect_summary_intent(req.message)

    def event_generator():
        global latest_reasoning_result
        if explicit_model_switch:
            full_text = f"Active conversational model set to {explicit_model_switch}. Model Lock remains engaged."
            add_message(conversation_id, "assistant", full_text)
            yield f"data: {json.dumps({'type': 'delta', 'text': full_text})}\n\n"
            yield f"data: {json.dumps({'type': 'model_control', 'data': model_control.status()})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            return
        if summary_intent in {"state_summary", "uncertainty_summary"}:
            try:
                full_text, reasoning_output = _build_deterministic_summary_reply(
                    conversation_id=conversation_id,
                    user_message=req.message,
                    user_profile=user_profile,
                    intent=summary_intent,
                )
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                return

            latest_reasoning_result = reasoning_output
            _persist_reasoning_snapshot(latest_reasoning_result)

            yield f"data: {json.dumps({'type': 'phase', 'name': 'guide'})}\n\n"
            yield f"data: {json.dumps({'type': 'delta', 'text': full_text})}\n\n"

            add_message(conversation_id, "assistant", full_text)

            learning = persist_learning(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                user_message=req.message,
                assistant_message=full_text,
            )

            yield f"data: {json.dumps({'type': 'learning', 'data': learning})}\n\n"
            confidence = {
                "memory_available": len(memories) > 0,
                "memory_count": len(memories),
                "used_fallback": len(memories) == 0,
                "reflection_score": learning.get("reflection_score") if learning else None,
                "web_search_enabled": ENABLE_WEB_SEARCH,
                "web_search_used": False,
            }
            yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            return

        if BACKEND_HEALTH_CHECK_CONFIRMATION_RE.match(req.message or ""):
            full_text, execution_outcome = _execute_backend_health_request(conversation_id=conversation_id, user_profile=user_profile)
            if execution_outcome is not None:
                latest_reasoning_result = execution_outcome.get("reasoning_result")
                _persist_reasoning_snapshot(latest_reasoning_result)
            yield f"data: {json.dumps({'type': 'phase', 'name': 'guide'})}\n\n"
            yield f"data: {json.dumps({'type': 'delta', 'text': full_text})}\n\n"

            add_message(conversation_id, "assistant", full_text)

            learning = persist_learning(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                user_message=req.message,
                assistant_message=full_text,
            )

            yield f"data: {json.dumps({'type': 'learning', 'data': learning})}\n\n"
            confidence = {
                "memory_available": len(memories) > 0,
                "memory_count": len(memories),
                "used_fallback": len(memories) == 0,
                "reflection_score": learning.get("reflection_score") if learning else None,
                "web_search_enabled": ENABLE_WEB_SEARCH,
                "web_search_used": False,
            }
            yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            return

        if BACKEND_HEALTH_CHECK_REQUEST_RE.search(req.message or ""):
            _create_backend_health_request(conversation_id=conversation_id, user_profile=user_profile)
            full_text = "I can run a bounded localhost health check against the configured backend endpoint. Confirm by saying: Run the backend health check."
            yield f"data: {json.dumps({'type': 'phase', 'name': 'guide'})}\n\n"
            yield f"data: {json.dumps({'type': 'delta', 'text': full_text})}\n\n"

            add_message(conversation_id, "assistant", full_text)

            learning = persist_learning(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                user_message=req.message,
                assistant_message=full_text,
            )

            yield f"data: {json.dumps({'type': 'learning', 'data': learning})}\n\n"
            confidence = {
                "memory_available": len(memories) > 0,
                "memory_count": len(memories),
                "used_fallback": len(memories) == 0,
                "reflection_score": learning.get("reflection_score") if learning else None,
                "web_search_enabled": ENABLE_WEB_SEARCH,
                "web_search_used": False,
            }
            yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            return

        chunks: List[str] = []
        deterministic_ack = build_declarative_acknowledgement(req.message)

        if deterministic_ack:
            full_text = deterministic_ack
            yield f"data: {json.dumps({'type': 'phase', 'name': 'guide'})}\n\n"
            yield f"data: {json.dumps({'type': 'delta', 'text': full_text})}\n\n"
        else:
            try:
                for event in stream_response_text(
                    history=history[:-1],
                    user_message=req.message,
                    user_profile=user_profile,
                    memories=memories,
                    conversation_id=conversation_id,
                ):
                    yield event

                    if event.startswith("data: "):
                        payload = json.loads(event[len("data: "):].strip())
                        if payload.get("type") == "delta":
                            chunks.append(payload.get("text", ""))
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                return

        full_text = deterministic_ack if deterministic_ack is not None else "".join(chunks)

        if full_text:
            if ENABLE_COGNITION_PIPELINE:
                try:
                    cognition_output = process_completed_turn(
                        user_message=req.message,
                        assistant_response=full_text,
                        identity_profile=get_identity_profile(user_profile),
                        persist=True,
                    )
                except Exception as exc:
                    print("Cognition pipeline warning:", repr(exc))
                    cognition_output = None

            if ENABLE_REASONING_PIPELINE:
                try:
                    previous_evidence_store = _load_scoped_evidence_store(conversation_id)
                    evidence_store = _build_runtime_evidence_store(
                        previous_evidence_store=previous_evidence_store,
                        preferences=user_profile.get("preferences", {}),
                        user_message=req.message,
                        conversation_id=conversation_id,
                    )
                    _persist_scoped_evidence_store(conversation_id, evidence_store)
                    goal_store = load_goal_store()
                    reasoning_output = run_reasoning_pipeline(
                        evidence_store=evidence_store,
                        goal_store=goal_store,
                        previous_evidence_store=previous_evidence_store,
                        dependency_map=_build_dependency_map(evidence_store),
                    )
                    latest_reasoning_result = reasoning_output
                    _persist_reasoning_snapshot(latest_reasoning_result)
                except Exception as exc:
                    print("Reasoning pipeline warning:", repr(exc))
                    reasoning_output = None

            add_message(conversation_id, "assistant", full_text)

            learning = persist_learning(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                user_message=req.message,
                assistant_message=full_text,
            )

            yield f"data: {json.dumps({'type': 'learning', 'data': learning})}\n\n"

            confidence = {
                "memory_available": len(memories) > 0,
                "memory_count": len(memories),
                "used_fallback": len(memories) == 0,
                "reflection_score": learning.get("reflection_score") if learning else None,
                "web_search_enabled": ENABLE_WEB_SEARCH,
                "web_search_used": should_enable_web_search(req.message),
            }

            yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Conversation-Id": conversation_id,
    }

    return observe_streaming_response(StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    ), conversation_id)


configure_mobile_runtime(
    create_conversation=create_conversation,
    conversation_exists=conversation_exists,
    get_full_messages=get_full_messages,
    get_conversation_meta=get_conversation_meta,
    get_db=get_db,
    stream_chat=lambda message, conversation_id: chat_stream(
        ChatRequest(message=message, conversation_id=conversation_id)
    ),
)
app.include_router(mobile_router)
app.include_router(runtime_operations_router)

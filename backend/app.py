from __future__ import annotations

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
from services.knowledge_graph import load_graph
from services.reasoning_engine import (
    build_reasoning_prompt_context,
    render_backend_state_for_prompt,
    sanitize_prompt_messages,
)
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
from services.user_identity import (
    apply_explicit_identity_updates,
    extract_explicit_age,
    age_group_from_age,
    build_user_identity_prompt,
    normalize_identity_profile,
)
from services.cognition_pipeline import process_completed_turn
from services.curiosity_engine import apply_curiosity_to_response
from services.declarative_acknowledger import build_declarative_acknowledgement
from routes.system import router as system_router
from dotenv import load_dotenv
load_dotenv(override=True)

import json
import math
import os
import re
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

import httpx
from ddgs import DDGS
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

APP_NAME = "0M3-G4-ARC"
DB_PATH = os.getenv("TURNING_DB_PATH", "omega_arc.db")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")

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
        updated_at TEXT NOT NULL
    )
    """)
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
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_conversation(user_id: Optional[str] = None, title: Optional[str] = None) -> str:
    cid = str(uuid.uuid4())
    now = utc_now()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (cid, user_id, title, now, now),
    )
    conn.commit()
    conn.close()
    return cid


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


def save_memory(*, conversation_id: Optional[str], user_id: Optional[str], kind: str, source_text: str, summary_text: str, score: float = 0.0) -> None:
    embedding = get_embedding(summary_text)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories (id, conversation_id, user_id, kind, source_text, summary_text, embedding_json, score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), conversation_id, user_id, kind, source_text, summary_text, json.dumps(embedding), score, utc_now()),
    )
    conn.commit()
    conn.close()


def search_memories(*, query: str, conversation_id: Optional[str], user_id: Optional[str], k: int = MAX_MEMORY_RESULTS) -> List[Dict[str, Any]]:
    query_embedding = get_embedding(query)
    conn = get_db()
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT * FROM memories WHERE user_id = ? OR conversation_id = ? ORDER BY created_at DESC LIMIT 250", (user_id, conversation_id))
    else:
        cur.execute("SELECT * FROM memories WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 250", (conversation_id,))
    rows = cur.fetchall()
    conn.close()
    scored = []
    for row in rows:
        try:
            emb = json.loads(row["embedding_json"])
        except Exception:
            continue
        sim = cosine_similarity(query_embedding, emb)
        record = dict(row)
        record["similarity"] = sim
        scored.append(record)
    scored.sort(key=lambda item: item["similarity"], reverse=True)
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


latest_reasoning_result: Optional[Dict[str, Any]] = None
latest_planning_result: Optional[Dict[str, Any]] = None
latest_decision_result: Optional[Dict[str, Any]] = None
latest_deliberation_result: Optional[Dict[str, Any]] = None


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

    return sanitize_prompt_messages(messages)


def generate_response_text(*, history: List[Dict[str, str]], user_message: str, user_profile: Dict[str, Any], memories: List[Dict[str, Any]], conversation_id: Optional[str] = None) -> str:
    web_results = search_web(user_message) if should_enable_web_search(user_message) else []
    messages = build_ollama_messages(history=history, user_message=user_message, user_profile=user_profile, memories=memories, web_results=web_results, conversation_id=conversation_id)
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/chat", json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": False})
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


def stream_response_text(*, history: List[Dict[str, str]], user_message: str, user_profile: Dict[str, Any], memories: List[Dict[str, Any]], conversation_id: Optional[str] = None) -> Generator[str, None, None]:
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
    with httpx.Client(timeout=None) as client:
        with client.stream("POST", f"{OLLAMA_BASE_URL}/chat", json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": True}) as response:
            response.raise_for_status()
            collected: List[str] = []
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                msg = data.get("message", {})
                chunk = msg.get("content", "")
                if chunk:
                    collected.append(chunk)
                    yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
                if data.get("done"):
                    final_text = "".join(collected)
                    yield f"data: {json.dumps({'type': 'phase', 'name': 'silence'})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'text': final_text})}\n\n"
                    break


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

    # Memory summaries
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


class CreateConversationResponse(BaseModel):
    conversation_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    learning: Dict[str, Any]


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[Dict[str, Any]]


class MemorySearchResponse(BaseModel):
    conversation_id: str
    memories: List[Dict[str, Any]]


app = FastAPI(title=f"{APP_NAME} API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        "chat_model": OLLAMA_CHAT_MODEL,
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


@app.post("/conversations", response_model=CreateConversationResponse)
def new_conversation(req: CreateConversationRequest) -> CreateConversationResponse:
    cid = create_conversation(user_id=req.user_id, title=req.title)
    return CreateConversationResponse(conversation_id=cid)


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
    memories = search_memories(query=q, conversation_id=conversation_id, user_id=meta.get("user_id") if meta else None)
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
    history = get_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)
    meta = get_conversation_meta(conversation_id) or {}
    effective_user_id = req.user_id or meta.get("user_id")
    user_profile = get_user_profile(effective_user_id)
    user_profile = {**user_profile, "preferences": build_backend_awareness_preferences(user_profile, req.message)}
    memories = search_memories(query=req.message, conversation_id=conversation_id, user_id=effective_user_id)
    summary_intent = detect_summary_intent(req.message)
    planning_intent = detect_planning_intent(req.message)
    deliberation_intent = detect_deliberation_intent(req.message)
    try:
        reasoning_output = None
        if summary_intent in {"state_summary", "uncertainty_summary"}:
            reply, reasoning_output = _build_deterministic_summary_reply(
                conversation_id=conversation_id,
                user_message=req.message,
                user_profile=user_profile,
                intent=summary_intent,
            )
        elif is_backend_health_query(req.message):
            scoped_evidence = _load_scoped_evidence_store(conversation_id)
            reply = build_backend_health_response(scoped_evidence)
        elif is_health_check_execution_request(req.message):
            scoped_evidence = _load_scoped_evidence_store(conversation_id)
            reply = build_health_check_execution_response(scoped_evidence)
        else:
            deterministic_ack = build_declarative_acknowledgement(req.message)
            if deterministic_ack:
                reply = deterministic_ack
            else:
                reply = generate_response_text(history=history[:-1], user_message=req.message, user_profile=user_profile, memories=memories, conversation_id=conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if ENABLE_COGNITION_PIPELINE and summary_intent not in {"state_summary", "uncertainty_summary"}:
        try:
            cognition_output = process_completed_turn(
                user_message=req.message,
                assistant_response=reply,
                identity_profile=get_identity_profile(user_profile),
                persist=True,
            )
            curiosity = cognition_output.get("curiosity") if cognition_output else None
            reply = apply_curiosity_to_response(
                response=reply,
                curiosity_candidate=curiosity,
                enabled=ENABLE_CURIOSITY_SUGGESTIONS,
            )
        except Exception as exc:
            print("Cognition pipeline warning:", repr(exc))
            cognition_output = None

    if summary_intent in {"state_summary", "uncertainty_summary"} and reasoning_output is not None:
        latest_reasoning_result = reasoning_output
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
                declaration_keys = {
                    str(item.get("key") or "")
                    for item in extract_runtime_declarations(req.message)
                    if isinstance(item, dict)
                }
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
        execution_request_pattern = re.compile(r"\b(execute|run\s+it\s+now|implement\s+now|apply\s+now|deploy\s+now)\b", re.IGNORECASE)
        if execution_request_pattern.search(req.message):
            reply = "Execution remains disabled in Epoch VII. Approval and decision recording are available, but actions are not executed automatically."

    add_message(conversation_id, "assistant", reply)
    learning = persist_learning(conversation_id=conversation_id, user_id=effective_user_id, user_message=req.message, assistant_message=reply)

    return ChatResponse(conversation_id=conversation_id, reply=reply, learning=learning)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    conversation_id = req.conversation_id

    if not conversation_id:
        conversation_id = create_conversation(user_id=req.user_id)
    elif not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    add_message(conversation_id, "user", req.message)

    meta = get_conversation_meta(conversation_id) or {}
    effective_user_id = req.user_id or meta.get("user_id")
    history = get_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)
    user_profile = get_user_profile(effective_user_id)
    user_profile = {**user_profile, "preferences": build_backend_awareness_preferences(user_profile, req.message)}
    memories = search_memories(
        query=req.message,
        conversation_id=conversation_id,
        user_id=effective_user_id,
    )
    summary_intent = detect_summary_intent(req.message)

    def event_generator():
        global latest_reasoning_result
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

        if is_backend_health_query(req.message):
            scoped_evidence = _load_scoped_evidence_store(conversation_id)
            full_text = build_backend_health_response(scoped_evidence)
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

        if is_health_check_execution_request(req.message):
            scoped_evidence = _load_scoped_evidence_store(conversation_id)
            full_text = build_health_check_execution_response(scoped_evidence)
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

        full_text = (deterministic_ack or "".join(chunks)).strip()

        if full_text:
            if ENABLE_COGNITION_PIPELINE:
                try:
                    cognition_output = process_completed_turn(
                        user_message=req.message,
                        assistant_response=full_text,
                        identity_profile=get_identity_profile(user_profile),
                        persist=True,
                    )
                    curiosity = cognition_output.get("curiosity") if cognition_output else None
                    full_text = apply_curiosity_to_response(
                        response=full_text,
                        curiosity_candidate=curiosity,
                        enabled=ENABLE_CURIOSITY_SUGGESTIONS,
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )
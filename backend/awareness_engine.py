from __future__ import annotations
import json, shutil, subprocess, urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONSTITUTION = BASE / "data" / "constitution.json"

@dataclass
class AwarenessSnapshot:
    ollama_online: bool
    backend_online: bool
    frontend_online: bool
    network_mode: str
    active_model: str
    vision_model: str
    embedding_model: str
    router_model: str
    gpu_name: str
    tools: dict
    configured_backend_port: int | None = None
    backend_health: dict | None = None

def http_ok(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except Exception:
        return False

def gpu_name():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return "UNKNOWN"

def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_backend_health_state(*, configured_backend_port=None, health_state=None):
    if isinstance(health_state, dict):
        return health_state

    return {
        "backend_port": configured_backend_port,
        "backend_health": {
            "status": "unknown",
            "checked_url": None,
            "checked_at": None,
            "source": "health_check",
        },
    }


def apply_backend_port_statement(state, message):
    updated = dict(state or {})
    lowered = message.lower()

    port = None
    if "port" in lowered:
        import re
        match = re.search(r"port\s+(\d{2,5})", lowered)
        if match:
            port = int(match.group(1))

    if port is None:
        return updated

    updated["backend_port"] = port

    health = dict(updated.get("backend_health") or {})
    if not isinstance(health, dict):
        health = {}

    health["status"] = "unknown"
    health["checked_url"] = f"http://127.0.0.1:{port}"
    health["checked_at"] = None
    health["source"] = "health_check"
    updated["backend_health"] = health

    return updated


def apply_backend_health_check(state, *, port, success, checked_url=None):
    updated = dict(state or {})
    updated["backend_port"] = port

    health = {
        "status": "online" if success else "offline",
        "checked_url": checked_url or f"http://127.0.0.1:{port}",
        "checked_at": _utc_now_iso(),
        "source": "health_check",
    }
    updated["backend_health"] = health
    return updated


def build_awareness_snapshot(
    backend_url="http://127.0.0.1:8000/",
    frontend_url="http://localhost:5173/",
    ollama_url="http://127.0.0.1:11434/api/tags",
    network_mode="offline",
    active_model="llama2-uncensored:7b",
    vision_model="llava:7b",
    embedding_model="embeddinggemma:latest",
    router_model="gemma3:1b",
    configured_backend_port=None,
    backend_health_state=None,
):
    health_state = build_backend_health_state(
        configured_backend_port=configured_backend_port,
        health_state=backend_health_state,
    )
    backend_health = health_state.get("backend_health", {}) if isinstance(health_state, dict) else {}
    backend_status = backend_health.get("status", "unknown") if isinstance(backend_health, dict) else "unknown"
    backend_online = backend_status == "online"
    return AwarenessSnapshot(
        ollama_online=http_ok(ollama_url),
        backend_online=backend_online,
        frontend_online=http_ok(frontend_url),
        network_mode=network_mode,
        active_model=active_model,
        vision_model=vision_model,
        embedding_model=embedding_model,
        router_model=router_model,
        gpu_name=gpu_name(),
        tools={
            "ollama_cli": bool(shutil.which("ollama.exe") or shutil.which("ollama")),
            "npm": bool(shutil.which("npm.cmd") or shutil.which("npm")),
            "python": bool(shutil.which("python.exe") or shutil.which("python")),
            "vision": True,
            "memory": True,
            "web_search": network_mode != "offline",
            "documents": False,
        },
        configured_backend_port=configured_backend_port,
        backend_health=backend_health,
    )

def awareness_prompt(snapshot):
    data = asdict(snapshot)
    tools = "\n".join(f"- {k}: {v}" for k, v in data["tools"].items())
    backend_health = data.get("backend_health", {}) or {}
    configured_port = data.get("configured_backend_port")
    health_status = backend_health.get("status", "unknown")
    health_url = backend_health.get("checked_url") or "unknown"
    return f"""Operational awareness:
- Ollama online: {data['ollama_online']}
- Backend online: {data['backend_online']}
- Frontend online: {data['frontend_online']}
- Network mode: {data['network_mode']}
- Active model: {data['active_model']}
- Vision model: {data['vision_model']}
- Embedding model: {data['embedding_model']}
- Router model: {data['router_model']}
- GPU: {data['gpu_name']}
- Configured backend port: {configured_port if configured_port is not None else 'unknown'}
- Backend health status: {health_status}
- Backend health checked URL: {health_url}

Configuration and runtime health are separate.
- A configured port is configuration knowledge only.
- A backend port number does not prove the backend is online or offline.
- Only a successful health check may establish online status.
- If the configured port changed after the last health check, report health as unknown until checked again.

Available tools:
{tools}

Do not invent capabilities that are unavailable."""

def constitution_prompt():
    data = json.loads(CONSTITUTION.read_text(encoding="utf-8"))
    principles = "\n".join(f"- {x}" for x in data["principles"])
    return f"Constitution:\n{principles}\n\nThe Constitution is stable and not rewritten by ordinary reflection."
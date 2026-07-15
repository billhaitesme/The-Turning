from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_GRAPH_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "knowledge_graph.json"
)


def normalize_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    return normalized or "unknown"


def empty_graph() -> Dict[str, Any]:
    return {"version": 1, "nodes": [], "edges": []}


def load_graph(path: Path = DEFAULT_GRAPH_PATH) -> Dict[str, Any]:
    if not path.exists():
        return empty_graph()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_graph()

    if not isinstance(data, dict):
        return empty_graph()

    if not isinstance(data.get("nodes"), list):
        data["nodes"] = []

    if not isinstance(data.get("edges"), list):
        data["edges"] = []

    data.setdefault("version", 1)

    return data


def save_graph(graph: Dict[str, Any], path: Path = DEFAULT_GRAPH_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_node(
    graph: Dict[str, Any],
    *,
    node_type: str,
    label: str,
    attributes: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    updated = deepcopy(graph)
    updated.setdefault("nodes", [])
    updated.setdefault("edges", [])
    updated.setdefault("version", 1)

    node_id = f"{normalize_id(node_type)}:{normalize_id(label)}"

    for node in updated["nodes"]:
        if node.get("id") != node_id:
            continue

        node.setdefault("attributes", {})
        node["attributes"].update(attributes or {})

        return updated

    updated["nodes"].append(
        {
            "id": node_id,
            "type": node_type,
            "label": label,
            "attributes": attributes or {},
        }
    )

    return updated


def upsert_edge(
    graph: Dict[str, Any],
    *,
    source: str,
    relationship: str,
    target: str,
    confidence: float,
    source_type: str,
) -> Dict[str, Any]:
    updated = deepcopy(graph)
    updated.setdefault("nodes", [])
    updated.setdefault("edges", [])

    proposed = {
        "source": source,
        "relationship": relationship,
        "target": target,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "source_type": source_type,
    }

    for edge in updated["edges"]:
        same_edge = (
            edge.get("source") == source
            and edge.get("relationship") == relationship
            and edge.get("target") == target
        )

        if not same_edge:
            continue

        if proposed["confidence"] >= float(edge.get("confidence", 0.0)):
            edge.update(proposed)

        return updated

    updated["edges"].append(proposed)

    return updated


def apply_knowledge_candidates(graph: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    updated = graph

    for candidate in candidates:
        key = candidate.get("key")
        value = candidate.get("value")

        if key == "active_project":
            project = str(value).strip()
            updated = upsert_node(updated, node_type="project", label=project)
        elif key == "backend_port":
            updated = upsert_node(
                updated,
                node_type="system",
                label="OMEGA-ARC backend",
                attributes={"port": value},
            )

    return updated

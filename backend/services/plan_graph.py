from __future__ import annotations

from typing import Any, Dict, Iterable, List


def build_plan_graph(*, goal_id: str, goal_title: str, steps: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    ordered_steps: List[Dict[str, Any]] = list(steps)

    nodes: List[Dict[str, str]] = []
    edges: List[Dict[str, str]] = []

    for step in ordered_steps:
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        nodes.append({"id": step_id, "title": str(step.get("title") or step_id)})

    goal_node_id = f"{goal_id}:complete"
    nodes.append({"id": goal_node_id, "title": f"{goal_title} complete"})

    previous_step_id: str | None = None
    for step in ordered_steps:
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        if previous_step_id is not None:
            edges.append({"from": previous_step_id, "to": step_id})
        previous_step_id = step_id

    if previous_step_id is not None:
        edges.append({"from": previous_step_id, "to": goal_node_id})

    return {
        "goal_id": goal_id,
        "nodes": nodes,
        "edges": edges,
    }

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Set


def _ordered_steps_from_plan_input(
    plan_or_steps: Any,
    *,
    goal_id: str | None = None,
    goal_title: str | None = None,
) -> tuple[str, str, List[Dict[str, Any]]]:
    if isinstance(plan_or_steps, dict):
        plan = deepcopy(plan_or_steps)
        return (
            str(plan.get("goal_id") or goal_id or "goal-unknown"),
            str(plan.get("title") or goal_title or "Goal"),
            list(plan.get("steps") or []),
        )

    return (
        str(goal_id or "goal-unknown"),
        str(goal_title or "Goal"),
        list(plan_or_steps or []),
    )


def build_plan_graph(
    plan: Dict[str, Any] | None = None,
    *,
    goal_id: str | None = None,
    goal_title: str | None = None,
    steps: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    graph_goal_id, graph_goal_title, ordered_steps = _ordered_steps_from_plan_input(
        plan if plan is not None else list(steps or []),
        goal_id=goal_id,
        goal_title=goal_title,
    )

    nodes: List[Dict[str, str]] = []
    edges: List[Dict[str, str]] = []
    known_step_ids: Set[str] = set()

    for step in ordered_steps:
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        if step_id in known_step_ids:
            continue
        known_step_ids.add(step_id)
        nodes.append({"id": step_id, "title": str(step.get("title") or step_id)})

    for step in ordered_steps:
        step_id = str(step.get("id") or "")
        if not step_id or step_id not in known_step_ids:
            continue

        for dep in step.get("dependencies") or []:
            dep_id = str(dep)
            if not dep_id:
                continue
            if dep_id == step_id:
                continue
            if dep_id in known_step_ids:
                edges.append({"from": dep_id, "to": step_id})

    return {
        "goal_id": graph_goal_id,
        "goal_title": graph_goal_title,
        "nodes": nodes,
        "edges": edges,
    }


def validate_acyclic(graph: Dict[str, Any]) -> bool:
    nodes = [str(node.get("id")) for node in graph.get("nodes", []) if isinstance(node, dict)]
    adjacency: Dict[str, List[str]] = {node: [] for node in nodes}

    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if src == dst and src in adjacency:
            return False
        if src in adjacency and dst in adjacency:
            adjacency[src].append(dst)

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def has_cycle(node: str) -> bool:
        if node in visited:
            return False
        if node in visiting:
            return True
        visiting.add(node)
        for nxt in sorted(adjacency.get(node, [])):
            if has_cycle(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    for node in sorted(adjacency):
        if has_cycle(node):
            return False
    return True


def topological_step_order(graph: Dict[str, Any]) -> List[str]:
    nodes = sorted(str(node.get("id")) for node in graph.get("nodes", []) if isinstance(node, dict))
    adjacency: Dict[str, List[str]] = defaultdict(list)
    indegree: Dict[str, int] = {node: 0 for node in nodes}

    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if src not in indegree or dst not in indegree:
            continue
        adjacency[src].append(dst)
        indegree[dst] += 1

    ready = deque(sorted(node for node, deg in indegree.items() if deg == 0))
    order: List[str] = []

    while ready:
        node = ready.popleft()
        order.append(node)
        for nxt in sorted(adjacency.get(node, [])):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)

    if len(order) != len(nodes):
        return []

    return order


def _extract_records(evidence_store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(evidence_store, dict):
        return {}
    records = evidence_store.get("records")
    if isinstance(records, dict):
        return records
    facts = evidence_store.get("facts")
    if isinstance(facts, dict):
        return facts
    return {}


def _requirement_satisfied(requirement: Dict[str, Any], records: Dict[str, Dict[str, Any]]) -> bool:
    key = str(requirement.get("key") or "")
    if not key:
        return False
    record = records.get(key) or {}
    state_type = str(record.get("state_type") or "unknown")
    value = record.get("value")

    if state_type in {"unknown", "invalidated", "expired"}:
        return False

    required_states = requirement.get("required_state_types") or []
    if required_states and state_type not in [str(item) for item in required_states]:
        return False

    if "required_value" in requirement and value != requirement.get("required_value"):
        return False

    return True


def find_ready_steps(plan: Dict[str, Any], evidence_store: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps = [deepcopy(step) for step in plan.get("steps", []) if isinstance(step, dict)]
    step_by_id = {str(step.get("id")): step for step in steps if step.get("id")}
    records = _extract_records(evidence_store)

    ready: List[Dict[str, Any]] = []
    for step in steps:
        status = str(step.get("status") or "pending")
        if status in {"completed", "skipped", "invalidated"}:
            continue

        deps_ok = True
        for dep in step.get("dependencies") or []:
            dep_step = step_by_id.get(str(dep))
            if not dep_step or str(dep_step.get("status") or "") != "completed":
                deps_ok = False
                break

        reqs_ok = all(
            _requirement_satisfied(requirement, records)
            for requirement in step.get("evidence_requirements") or []
            if isinstance(requirement, dict)
        )

        if deps_ok and reqs_ok:
            ready.append(step)

    ready.sort(key=lambda item: int(item.get("order") or 9999))
    return ready


def find_blocked_steps(plan: Dict[str, Any], evidence_store: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps = [deepcopy(step) for step in plan.get("steps", []) if isinstance(step, dict)]
    ready_ids = {str(step.get("id")) for step in find_ready_steps(plan, evidence_store)}
    blocked: List[Dict[str, Any]] = []

    for step in steps:
        step_id = str(step.get("id") or "")
        status = str(step.get("status") or "")
        if status == "blocked":
            blocked.append(step)
            continue
        if status in {"completed", "skipped", "invalidated"}:
            continue
        if step_id and step_id not in ready_ids:
            blocked.append(step)

    blocked.sort(key=lambda item: int(item.get("order") or 9999))
    return blocked


def find_downstream_steps(step_id: str, graph: Dict[str, Any]) -> List[str]:
    adjacency: Dict[str, List[str]] = defaultdict(list)
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if src and dst:
            adjacency[src].append(dst)

    visited: Set[str] = set()
    queue: deque[str] = deque(sorted(adjacency.get(str(step_id), [])))
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for nxt in sorted(adjacency.get(current, [])):
            queue.append(nxt)

    return sorted(visited)


def find_upstream_dependencies(step_id: str, graph: Dict[str, Any]) -> List[str]:
    reverse: Dict[str, List[str]] = defaultdict(list)
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if src and dst:
            reverse[dst].append(src)

    visited: Set[str] = set()
    queue: deque[str] = deque(sorted(reverse.get(str(step_id), [])))
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for prev in sorted(reverse.get(current, [])):
            queue.append(prev)

    return sorted(visited)

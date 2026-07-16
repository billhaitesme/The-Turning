from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class PlanDependency:
    key: str
    title: str
    required_state: str = "verified"
    satisfied: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "required_state": self.required_state,
            "satisfied": self.satisfied,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    status: str
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "dependencies": list(self.dependencies),
            "confidence": float(self.confidence),
        }


@dataclass(frozen=True)
class Plan:
    goal_id: str
    goal: str
    status: str
    confidence: float
    steps: List[PlanStep] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    dependencies: List[PlanDependency] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal": self.goal,
            "status": self.status,
            "confidence": float(self.confidence),
            "steps": [step.to_dict() for step in self.steps],
            "blockers": list(self.blockers),
            "dependencies": [item.to_dict() for item in self.dependencies],
            "graph": dict(self.graph),
        }

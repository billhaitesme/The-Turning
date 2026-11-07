from dataclasses import dataclass
from enum import Enum

class TaskType(str, Enum):
    IDENTITY = "identity"
    USER_IDENTITY = "user_identity"
    VOW = "vow"
    GENERAL = "general"
    TECHNICAL = "technical"
    VISION = "vision"
    MEMORY = "memory"
    CURRENT_INFO = "current_info"

@dataclass(frozen=True)
class RouteDecision:
    task_type: TaskType
    model: str
    use_memory: bool
    use_web: bool
    use_vision: bool
    reason: str

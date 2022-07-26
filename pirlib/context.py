from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class TaskContext:
    config: Dict[str, Any]
    output: Any

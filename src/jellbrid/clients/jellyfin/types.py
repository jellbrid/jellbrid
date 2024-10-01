import enum
import typing as t


class TaskState(enum.Enum):
    Idle = "Idle"
    Cancelling = "Cancelling"
    Running = "Running"


class Task(t.TypedDict):
    Name: str
    State: TaskState
    CurrentProgressPercentage: float
    Id: str
    LastExecutionResult: dict
    Triggers: list[dict]
    Description: str
    Category: str
    IsHidden: bool
    Key: str

from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel


class HistoryIteration(BaseModel):
    """
    Database model for storing conversation iterations.
    """

    session_id: str
    agent_name: str
    thought: str
    action: str
    observation: str
    tool_call_requires: bool
    action_input: Union[str, Dict[str, Any]]
    timestamp: datetime
    status: str
    task_id: Optional[int] = None


class HistoryDomain:
    def __init__(
        self,
        session_id,
        agent_name,
        thought,
        action,
        tool_call_requires,
        action_input,
        observation,
        status,
        task_id,
    ) -> None:
        self.session_id = session_id
        self.agent_name = agent_name
        self.thought = thought
        self.action = action
        self.tool_call_requires = tool_call_requires
        self.action_input = action_input
        self.observation = observation
        self.status = status
        self.task_id = task_id
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "thought": self.thought,
            "tool_call_requires": self.tool_call_requires,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "status": self.status,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
        }

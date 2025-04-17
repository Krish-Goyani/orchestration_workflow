from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Summary(BaseModel):
    """
    Database model for storing conversation summaries.
    """

    summary_id: str
    session_id: str
    agent_name: str
    content: str
    start_idx: int
    end_idx: int
    timestamp: datetime
    task_id: Optional[int] = None
    summary_type: str = "incremental"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        result = {
            "summary_id": self.summary_id,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "content": self.content,
            "timestamp": self.timestamp,
            "summary_type": self.summary_type,
        }

        if self.task_id is not None:
            result["task_id"] = self.task_id

        return result

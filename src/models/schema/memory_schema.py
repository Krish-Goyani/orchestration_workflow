from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


class SummaryRecord(BaseModel):
    """Record of a conversation summary"""

    session_id: str
    start_idx: int  # Starting iteration index
    end_idx: int  # Ending iteration index
    content: str  # Summary content
    timestamp: datetime
    summary_type: Literal["incremental", "task_specific", "session"] = (
        "incremental"
    )


class ContextIntent(BaseModel):
    """Intent classification for context assembly"""

    requires_summary: bool = False
    requires_rag: bool = False
    requires_recent_only: bool = True
    rag_query: Optional[str] = None
    rag_filters: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    reasoning: str = ""

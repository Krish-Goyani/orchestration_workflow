from enum import Enum
from pydantic import BaseModel
from typing import Literal, Optional, List

class Stage(BaseModel):
    stage_name: str
    input_data: dict
    output_data: dict
    feedback: Optional[str] = None
    
class History(BaseModel):
    user_query: str
    status : Literal["in_progress", "completed", "failed"]
    total_iterations: int
    history: List[Stage]
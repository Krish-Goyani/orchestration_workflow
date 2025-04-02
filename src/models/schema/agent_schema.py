from pydantic import BaseModel
from src.models.schema.tools_schema import Tool
from typing import Optional, List
class Agent(BaseModel):
    """
    Agent model for the agent schema.
    """

    name: str
    description: str
    tools: Optional[List[Tool]] = None  
    

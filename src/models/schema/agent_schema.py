from typing import Callable, List, Optional

from pydantic import BaseModel

from src.models.schema.tools_schema import Tool


class Agent(BaseModel):
    """
    Agent model for the agent schema.
    """

    name: str
    description: str
    func: Optional[Callable] = None
    tools: Optional[List[Tool]] = None

from pydantic import BaseModel, Field
from typing import Literal

class SingleIteration(BaseModel):
    agent_name: str = Field(..., description="Name of the agent")
    thought: str = Field(..., description="Thought process of the agent")
    tool_call_requires: bool = Field(..., description="Requirements for tool call")
    action: str = Field(..., description="Action taken by the agent")
    action_input: str = Field(..., description="Input for the action taken by the agent")
    observation: str = Field(..., description="Observation received by the agent")
    status: Literal["in_progress", "completed"] = Field(..., description="Status of the iteration")

    
class History(BaseModel):
    user_query : str = Field(..., description="User's query")
    iterations: list[SingleIteration] = Field(..., description="List of iterations taken by the agent")
    total_iterations: int = Field(..., description="Total number of iterations taken by the agent")
    final_status: Literal["in_progress", "completed"] = Field(..., description="Status of the process")


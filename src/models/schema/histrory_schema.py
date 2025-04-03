from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SingleIteration(BaseModel):
    agent_name: str = Field(..., description="Name of the agent")
    thought: str = Field(..., description="Thought process of the agent")
    tool_call_requires: bool = Field(
        ..., description="Requirements for tool call"
    )
    action: Optional[Any] = Field(..., description="Action taken by the agent")
    action_input: Optional[Any] = Field(
        ...,
        description="Input for the action taken by the agent if not applicable then write null",
    )
    observation: Optional[Any] = Field(
        ..., description="Observation received by the agent"
    )
    status: Literal["in_progress", "completed"] = Field(
        ..., description="Status of the iteration"
    )


class History(BaseModel):
    user_query: str = Field(..., description="User's query")
    iterations: list[SingleIteration] = Field(
        ..., description="List of iterations taken by the agent"
    )
    total_iterations: int = Field(
        ..., description="Total number of iterations taken by the agent"
    )
    final_status: Literal["in_progress", "completed"] = Field(
        ..., description="Status of the process"
    )

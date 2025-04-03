from typing import List

from google.genai import types

from src.agents.agent_registry import global_agent_registry
from src.agents.research_expert import ResearchExpert
from src.agents.weather_expert import WeatherExpert
from src.config.settings import settings
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.memory_store import global_memory_store
from src.models.schema.agent_schema import Agent
from src.prompts.orchestator_prompt import (
    ORCHESTARTOR_SYSTEM_PROMPT,
    ORCHESTARTOR_USER_PROMPT,
)
from src.utils.response_parser import parse_response
from src.utils.session_context import session_state


class OrchestratorAgent:
    """
    Orchestrator Agent Module

    This agent controls and coordinates all other agents in the system.
    It handles task distribution, communication between agents, and overall workflow management.
    """

    def __init__(self):
        """
        Initialize the orchestrator agent.

        Args:
            config: Configuration for the orchestrator
        """
        self.llm = GeminiLLM()
        self.session_id = session_state.get()
        self.research_expert = ResearchExpert()
        self.weather_expert = WeatherExpert()

    def get_available_agents(self) -> List[Agent]:
        """
        Get the list of registered agents.

        Returns:
            list: The list of registered agents.
        """
        return global_agent_registry.get_all_agents()

    async def start(self, user_query: str) -> str:
        """
        Start the orchestrator agent.

        This method initializes the agent and starts the main loop for task management.
        """
        global_memory_store.create_history(
            session_id=self.session_id, user_query=user_query
        )

        # Create a while loop to keep the orchestrator agent running
        while True:
            history = global_memory_store.get_history(
                session_id=self.session_id
            )
            content = ORCHESTARTOR_USER_PROMPT.format(history=history)
            config = types.GenerateContentConfig(
                system_instruction=ORCHESTARTOR_SYSTEM_PROMPT.format(
                    available_agents=self.get_available_agents()
                )
            )

            response = await self.llm.generate_response(
                config=config, contents=content
            )

            response_data = parse_response(response)

            global_memory_store.add_iteration(
                session_id=self.session_id,
                agent_name="OrchestratorAgent",
                thought=response_data.get("thought"),
                action=response_data.get("action"),
                observation="not applicable",
                action_input=response_data.get("action_input"),
                tool_call_requires=response_data.get("tool_call_requires"),
                status=response_data.get("status"),
            )

            if str(response_data.get("tool_call_requires")).lower() == "true":
                agent_result = await global_agent_registry.execute_agent(
                    agent_name=response_data["action"],
                    input_data=response_data["action_input"],
                )

            if response_data.get("action") == "ResponseSynthesizerExpert":
                return agent_result

            if (
                str(response_data.get("status")).lower() == "completed"
                or history.total_iterations >= settings.MAX_ITERATIONS
                or response_data.get("action") == "ResponseSynthesizerExpert"
            ):
                break

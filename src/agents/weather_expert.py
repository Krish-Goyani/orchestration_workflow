from google.genai import types

from src.agents.agent_decorator import agent
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.memory_store import global_memory_store
from src.models.schema.tools_schema import Tool
from src.prompts.agent_prompts import RESEARCH_SYSTEM_PROMPT
from src.utils.session_context import session_state


@agent
class WeatherExpert:
    """
    WeatherExpertAgent is an agent designed to assist with weather-related queries.
    it use the external api to get the current temperatur of the location.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.memory_store = global_memory_store
        self.available_tools = []
        self.session_id = session_state.get()

    async def execute(self):
        agent_iteration_count = 0
        while True:
            # Fetch the latest history
            history = self.memory_store.get_formatted_history(self.session_id)
            if not history:
                break
            config = types.GenerateContentConfig(
                system_instruction=RESEARCH_SYSTEM_PROMPT,
            )
            contents = history
            response = await self.llm.generate_response(
                config=config, contents=contents
            )

            print(contents)

    def add_tool(self, tool: Tool) -> None:
        """
        Add a tool to the agent's available tools.

        Args:
            tool (Tool): The tool to add.
        """
        self.available_tools.append(tool)
        print("Tool added:", tool)

    def get_available_tools(self) -> list[Tool]:
        """
        Get the list of available tools for the agent.

        Returns:
            list[Tool]: The list of available tools.
        """
        return self.available_tools

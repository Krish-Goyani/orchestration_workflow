from google.genai import types

from src.agents.agent_decorator import agent
from src.agents.agent_registry import global_agent_registry
from src.config.settings import settings
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.memory_store import global_memory_store
from src.models.schema.tools_schema import Tool
from src.prompts.agent_prompts import (
    RESEARCH_SYSTEM_PROMPT,
    RESEARCH_USER_PROMPT,
)
from src.tools.tools_registry import global_tool_registry
from src.utils.response_parser import ensure_dict, parse_response
from src.utils.session_context import session_state


@agent
class ResearchExpert:
    """
    Research Expert Agent

    This agent specializes in conducting research using web search and scraping tools.
    It analyzes information and stores findings in memory for future reference.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.session_id = session_state.get()

    async def execute(self, action_input: str):
        agent_iteration_count = 0
        history = global_memory_store.get_history(session_id=self.session_id)

        while True:
            # Fetch the latest history
            agent_iteration_count += 1
            history = global_memory_store.get_history(
                session_id=self.session_id
            )
            if not history:
                break

            config = types.GenerateContentConfig(
                system_instruction=RESEARCH_SYSTEM_PROMPT.format(
                    available_tools=self.get_available_tools()
                ),
            )
            contents = RESEARCH_USER_PROMPT.format(
                action_input=action_input, history=history
            )
            response = await self.llm.generate_response(
                config=config, contents=contents
            )

            response_data = parse_response(response)

            if str(response_data.get("tool_call_requires")).lower() == "true":
                await self._handle_tool_call(response_data, self.session_id)
            else:
                history = global_memory_store.get_history(
                    session_id=self.session_id
                )
                if not history:
                    break

                config = types.GenerateContentConfig(
                    system_instruction=RESEARCH_SYSTEM_PROMPT.format(
                        available_tools=self.get_available_tools()
                    )
                )
                contents = RESEARCH_USER_PROMPT.format(
                    history=history, action_input="Not applicable"
                )
                response = await self.llm.generate_response(
                    config=config, contents=contents
                )

                response_data = parse_response(response)

                global_memory_store.add_iteration(
                    session_id=self.session_id,
                    agent_name="ResearchExpert",
                    thought=response_data.get("thought"),
                    action=response_data.get("action"),
                    observation="not applicable",
                    action_input=response_data.get("action_input"),
                    tool_call_requires=response_data.get("tool_call_requires"),
                    status=response_data.get("status"),
                )
                history = global_memory_store.get_history(
                    session_id=self.session_id
                )
                if (
                    str(response_data.get("status")).lower() == "completed"
                    or history.total_iterations >= settings.MAX_ITERATIONS
                    or agent_iteration_count >= settings.MAX_AGENT_ITERATIONS
                ):
                    break

    async def _handle_tool_call(self, response_data, session_id):
        try:
            argument = ensure_dict(response_data.get("action_input"))
            result = await global_tool_registry.call_tool(
                tool_name=response_data.get("action"), arguments=argument
            )
        except Exception as e:
            print("Error calling tool:", e)
            result = "error occured"
            return False

        # Store the result in memory
        global_memory_store.add_iteration(
            session_id=session_id,
            agent_name="ResearchExpert",
            thought=response_data.get("thought"),
            action=response_data.get("action"),
            observation=result,
            action_input=response_data.get("action_input"),
            tool_call_requires=response_data.get("tool_call_requires"),
            status=response_data.get("status"),
        )
        return True

    def get_available_tools(self) -> list[Tool]:
        """
        Get the list of available tools for the agent.

        Returns:
            list[Tool]: The list of available tools.
        """
        return global_agent_registry.get_agent_tools(
            agent_name="ResearchExpert"
        )

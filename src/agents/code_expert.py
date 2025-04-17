from typing import List

from google.genai import types

from src.agents.agent_decorator import agent
from src.agents.agent_registry import global_agent_registry
from src.config.settings import settings
from src.llms.gemini_llm import GeminiLLM
from src.memory.memory_manager import global_memory_manager
from src.models.schema.tools_schema import Tool
from src.prompts.agent_prompts import (
    CODE_EXPERT_SYSTEM_PROMPT,
    CODE_EXPERT_USER_PROMPT,
)
from src.tools.tools_registry import global_tool_registry
from src.utils.memory_store import store_iteration
from src.utils.response_parser import ensure_dict, parse_response
from src.utils.session_context import session_state


@agent
class CodeExpert:
    """
    CodeExpertAgent

    This agent is specialized in generating, executing, and debugging code.
    It can generate single files or entire projects, run them in a sandbox environment,
    and provide feedback based on execution results. It is especially useful for
    code generation, prototyping, implementation, and debugging tasks.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.session_id = session_state.get()

    async def execute(
        self, task_id: int, task: str, parent_ids: List[int] = []
    ):
        agent_iteration_count = 0
        task_ids = [task_id] + parent_ids
        while True:
            # Fetch the latest context for this task
            agent_iteration_count += 1

            try:
                # Get context from the context-aware memory manager
                # This will intelligently retrieve the most relevant context
                history = await global_memory_manager.get_task_context(
                    session_id=self.session_id,
                    agent_name="CodeExpert",
                    task=task,
                    task_id=task_id,
                    dependencies=parent_ids,
                )

                # Extract the relevant parts of the context
                recent_history = history.get("recent_history", {})
                summaries = history.get("summary", [])
                rag_results = history.get("rag_results", [])

                # Format context for prompt
                context_str = f"Recent History: {recent_history}\n"
                if summaries:
                    context_str += f"Summaries: {summaries}\n"
                if rag_results:
                    context_str += f"Retrieved Context: {rag_results}\n"

            except Exception as e:
                print(f"Error retrieving enhanced memory context: {e}")
                # Fallback to simple history
                try:
                    history_obj = await global_memory_manager.get_task_history(
                        session_id=self.session_id, task_ids=task_ids
                    )
                    context_str = f"History: {history_obj}"
                except Exception as e2:
                    print(f"Error retrieving task history: {e2}")
                    break

            config = types.GenerateContentConfig(
                system_instruction=CODE_EXPERT_SYSTEM_PROMPT.format(
                    available_tools=self.get_available_tools()
                ),
            )
            contents = CODE_EXPERT_USER_PROMPT.format(
                action_input=task, history=context_str
            )
            response = await self.llm.generate_response(
                config=config, contents=contents
            )

            response_data = parse_response(response)

            if str(response_data.get("tool_call_requires")).lower() == "true":
                await self._handle_tool_call(
                    response_data, self.session_id, task_id
                )
            else:
                await store_iteration(
                    session_id=self.session_id,
                    agent_name="CodeExpert",
                    thought=response_data.get("thought"),
                    action=response_data.get("action"),
                    observation="not applicable",
                    action_input=response_data.get("action_input"),
                    tool_call_requires=response_data.get("tool_call_requires"),
                    status=response_data.get("status"),
                    task_id=task_id,
                )

            # Check if we should exit the loop
            try:
                # Check completion status and iteration limits
                status = response_data.get("status", "").lower()

                # Try to get history from memory manager first
                history_obj = await global_memory_manager.get_complete_history(
                    self.session_id
                )
                total_iterations = (
                    history_obj.total_iterations
                    if history_obj
                    else settings.MAX_ITERATIONS
                )

                if (
                    status == "completed"
                    or total_iterations >= settings.MAX_ITERATIONS
                    or agent_iteration_count >= settings.MAX_AGENT_ITERATIONS
                ):
                    break
            except Exception as e:
                print(f"Error checking loop exit conditions: {e}")
                # Fallback to simpler logic
                if (
                    str(response_data.get("status")).lower() == "completed"
                    or agent_iteration_count >= settings.MAX_AGENT_ITERATIONS
                ):
                    break

        return "Code task completed"

    async def _handle_tool_call(self, response_data, session_id, task_id):
        try:
            argument = ensure_dict(response_data.get("action_input"))
            result = await global_tool_registry.call_tool(
                tool_name=response_data.get("action"), arguments=argument
            )
        except Exception as e:
            print("Error calling tool:", e)
            result = f"Error occurred: {str(e)}"
            return False

        # Store the result in memory using the central memory store
        await store_iteration(
            session_id=session_id,
            agent_name="CodeExpert",
            thought=response_data.get("thought"),
            action=response_data.get("action"),
            observation=result,
            action_input=response_data.get("action_input"),
            tool_call_requires=response_data.get("tool_call_requires"),
            status=response_data.get("status"),
            task_id=task_id,
        )
        return True

    def get_available_tools(self) -> list[Tool]:
        """
        Get a list of tools available to the agent.

        Returns:
            list[Tool]: The list of tools available to the agent.
        """
        return global_agent_registry.get_agent_tools("CodeExpert")

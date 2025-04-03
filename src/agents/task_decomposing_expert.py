from typing import List

from google.genai import types

from src.agents.agent_decorator import agent
from src.agents.agent_registry import global_agent_registry
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.memory_store import global_memory_store
from src.prompts.agent_prompts import (
    TASK_DECOMPOSING_SYSTEM_PROMPT,
    TASK_DECOMPOSING_USER_PROMPT,
)
from src.utils.response_parser import parse_response
from src.utils.session_context import session_state


@agent
class TaskDecomposingExpert:
    """
    Task Decomposing Agent

    This agent specializes in decomposing the user query into smaller tasks.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.session_id = session_state.get()

    async def execute(
        self, task: str, task_id: int = None, parent_ids: List[int] = []
    ):
        config = types.GenerateContentConfig(
            system_instruction=TASK_DECOMPOSING_SYSTEM_PROMPT.format(
                available_agents=global_agent_registry.get_all_agents()
            ),
        )
        contents = TASK_DECOMPOSING_USER_PROMPT.format(user_query=task)
        response = await self.llm.generate_response(
            config=config, contents=contents
        )

        response_data = parse_response(response)

        # add the ids for each task
        tasks = self._convert_tasks(response_data.get("decomposed_tasks", []))
        global_memory_store.add_iteration(
            session_id=self.session_id,
            agent_name="TaskDecomposingExpert",
            thought=response_data.get("thought"),
            action="Not applicable",
            observation=tasks,
            tool_call_requires="Not Applicable",
            status="completed",
            action_input="Not applicable",
        )

    def _convert_tasks(self, task_list):
        """
        Converts a list of task strings into a list of dictionaries with a task_id.

        Args:
            task_list (list[str]): A list of task strings.

        Returns:
            list[dict]: A list of dictionaries with keys 'task_id' and 'task'.
        """
        current_id = global_agent_registry.get_total_tasks()
        tasks = [
            {"task_id": current_id + idx + 1, "task": task}
            for idx, task in enumerate(task_list)
        ]
        global_agent_registry.update_total_tasks(len(tasks))
        return tasks

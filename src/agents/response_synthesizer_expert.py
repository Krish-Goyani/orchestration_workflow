from typing import List

from google.genai import types

from src.agents.agent_decorator import agent
from src.llms.gemini_llm import GeminiLLM
from src.memory.memory_manager import global_memory_manager
from src.prompts.agent_prompts import (
    RESPONSE_SYNTHESIZER_SYSTEM_PROMPT,
    RESPONSE_SYNTHESIZER_USER_PROMPT,
)
from src.utils.memory_store import store_iteration
from src.utils.response_parser import parse_response
from src.utils.session_context import session_state


@agent
class ResponseSynthesizerExpert:
    """
    Response Synthesizer Agent

    This agent specializes in synthesizing the final response for the user from the results of other agents.
    It creates coherent, comprehensive responses that integrate all relevant information.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.session_id = session_state.get()

    async def execute(
        self, task_id: int, task: str, parent_ids: List[int] = []
    ):
        """
        Execute the response synthesizer agent.

        Args:
            task_id: ID of the synthesis task
            task: Description of what to synthesize
            parent_ids: List of task IDs whose outputs should be synthesized

        Returns:
            The final synthesized response
        """
        # For the response synthesizer, we need comprehensive context
        # with all the information from dependent tasks
        try:
            # Get comprehensive context including all parent tasks
            context = await global_memory_manager.get_task_context(
                session_id=self.session_id,
                agent_name="ResponseSynthesizerExpert",
                task=task,
                task_id=task_id,
                dependencies=parent_ids,
            )

            # Response synthesizer needs comprehensive information
            # including summaries and RAG results if available
            history_str = ""

            # Add recent history
            if "recent_history" in context:
                history_str += (
                    f"Recent Interactions:\n{context['recent_history']}\n\n"
                )

            # Add summaries which are critical for the synthesizer
            if context.get("summary"):
                history_str += "Task Summaries:\n"
                for summary in context["summary"]:
                    history_str += f"{summary}\n\n"

            # Add any RAG results which might be relevant
            if context.get("rag_results"):
                history_str += "Additional Context:\n"
                for result in context["rag_results"]:
                    history_str += f"{result}\n\n"

            # Add original user query for reference
            user_query = context.get("user_query", "")
            if user_query:
                history_str += f"Original User Query: {user_query}\n\n"

        except Exception as e:
            print(f"Error retrieving context for ResponseSynthesizer: {e}")
            # Fallback to getting all history
            try:
                history_obj = await global_memory_manager.get_complete_history(
                    self.session_id
                )
                history_str = str(history_obj)
            except Exception as e2:
                print(f"Error retrieving complete history: {e2}")
                return "Unable to retrieve context and synthesize a response."

        # Generate response using the context
        config = types.GenerateContentConfig(
            system_instruction=RESPONSE_SYNTHESIZER_SYSTEM_PROMPT
        )
        contents = RESPONSE_SYNTHESIZER_USER_PROMPT.format(
            action_input=task, history=history_str
        )
        response = await self.llm.generate_response(
            config=config, contents=contents
        )

        response_data = parse_response(response)
        final_response = response_data.get(
            "final_response", "No response could be generated."
        )

        # Store the synthesized response in memory
        await store_iteration(
            session_id=self.session_id,
            agent_name="ResponseSynthesizerExpert",
            thought="Orchestrator Agent invoked me to synthesize the response.",
            action="Response Synthesis",
            action_input="Comprehensive conversation history and user query",
            tool_call_requires=False,
            status="completed",
            observation=final_response,
            task_id=task_id,
        )

        return final_response

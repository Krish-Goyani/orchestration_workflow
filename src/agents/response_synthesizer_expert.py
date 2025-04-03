from google.genai import types

from src.agents.agent_decorator import agent
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.memory_store import global_memory_store
from src.prompts.agent_prompts import (
    RESPONSE_SYNTHESIZER_SYSTEM_PROMPT,
    RESPONSE_SYNTHESIZER_USER_PROMPT,
)
from src.utils.response_parser import parse_response
from src.utils.session_context import session_state


@agent
class ResponseSynthesizerExpert:
    """
    Response Synthesizer Agent

    This agent specializes in synthesizing the response from all agents. this agent generate the final response.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.session_id = session_state.get()

    async def execute(self, action_input: str):

        history = global_memory_store.get_history(session_id=self.session_id)
        if not history:
            return

        config = types.GenerateContentConfig(
            system_instruction=RESPONSE_SYNTHESIZER_SYSTEM_PROMPT
        )
        contents = RESPONSE_SYNTHESIZER_USER_PROMPT.format(
            action_input=action_input, history=history
        )
        response = await self.llm.generate_response(
            config=config, contents=contents
        )

        response_data = parse_response(response)

        return response_data.get("final_response", "no response")

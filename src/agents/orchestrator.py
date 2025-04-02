from src.memory.long_term.memory_store import global_memory_store
from src.llms.gemini_llm import GeminiLLM
import uuid
from src.models.schema.histrory_schema import History, SingleIteration
from src.config.settings import settings
from google.genai import types
from src.models.schema.agent_schema import Agent
from typing import List
from src.agents.agent_registry import global_agent_registry

from src.prompts.orchestator_prompt import ORCHESTARTOR_SYSTEM_PROMPT
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
        self.memory_store = global_memory_store
        self.session_id = str(uuid.uuid4())
        self.avilable_agents = []
        
        
    def get_available_agents(self) -> List[Agent]:
        
        """
        Get the list of registered agents.

        Returns:
            list: The list of registered agents.
        """
        return global_agent_registry.get_all_agents()
        
    async def start(self, user_query: str) -> None:
        """
        Start the orchestrator agent.

        This method initializes the agent and starts the main loop for task management.
        """
        self.memory_store.create_history(session_id=self.session_id, user_query=user_query)
        history = self.memory_store.get_history(session_id=self.session_id)
        
        # Create a while loop to keep the orchestrator agent running
        while not history.final_status == "completed" or history.total_iterations <= settings.MAX_ITERATIONS :
            
            content = self.memory_store.get_formatted_history(
                session_id=self.session_id
            )
            config = types.GenerateContentConfig(
                system_instruction= ORCHESTARTOR_SYSTEM_PROMPT
            )
            response = await self.llm.generate_response(
                config=config,
                contents=content
            )
            print(response)

                

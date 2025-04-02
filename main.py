import asyncio
import uuid

from src.agents.agent_registry import global_agent_registry
from src.agents.orchestrator import OrchestratorAgent
from src.agents.research_expert import ResearchExpert
from src.models.schema.agent_schema import Agent
from src.tools.tools_registry import global_tool_registry
from src.tools.url_scraper_tool import url_scraper
from src.tools.web_search_tool import websearch
from src.utils.session_context import session_state


async def main(user_query) -> None:
    orchestrator_agent = OrchestratorAgent()
    research_agent = ResearchExpert()
    global_agent_registry.register(
        Agent(
            name=research_agent._schema.name,
            func=research_agent.execute,
            description=research_agent._schema.description,
            tools=[websearch, url_scraper],
        )
    )
    print(f"registered_tools {global_tool_registry.list_tools()}")

    results = await orchestrator_agent.start(
        user_query="What is the latest research on AI?"
    )

    print(results)


if __name__ == "__main__":
    user_query = "What is the latest research on AI?"
    session_state.set(uuid.uuid4())
    asyncio.run(main(user_query))

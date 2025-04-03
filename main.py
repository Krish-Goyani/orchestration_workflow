import asyncio

from src.agents.agent_registry import global_agent_registry
from src.agents.orchestrator import OrchestratorAgent
from src.agents.research_expert import ResearchExpert
from src.agents.response_synthesizer_expert import ResponseSynthesizerExpert
from src.agents.weather_expert import WeatherExpert
from src.models.schema.agent_schema import Agent
from src.tools.tools_registry import global_tool_registry
from src.tools.url_scraper_tool import url_scraper
from src.tools.weather_tool import get_forecast
from src.tools.web_search_tool import websearch


async def main(user_query) -> None:
    orchestrator_agent = OrchestratorAgent()
    research_agent = ResearchExpert()
    weather_agent = WeatherExpert()
    response_synthesizer_agent = ResponseSynthesizerExpert()
    global_agent_registry.register(
        Agent(
            name=research_agent._schema.name,
            func=research_agent.execute,
            description=research_agent._schema.description,
            tools=[websearch, url_scraper],
        )
    )
    global_agent_registry.register(
        Agent(
            name=weather_agent._schema.name,
            func=weather_agent.execute,
            description=weather_agent._schema.description,
            tools=[get_forecast],
        )
    )
    global_agent_registry.register(
        Agent(
            name=response_synthesizer_agent._schema.name,
            func=response_synthesizer_agent.execute,
            description=response_synthesizer_agent._schema.description,
            tools=[],
        )
    )
    print(f"registered_tools {global_tool_registry.list_tools()}")

    results = await orchestrator_agent.start(user_query=user_query)

    print(results)


if __name__ == "__main__":
    user_query = "what is current weather in london? and tell what is RAG in generative ai"
    asyncio.run(main(user_query))

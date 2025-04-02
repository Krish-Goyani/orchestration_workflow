from src.agents.orchestrator import OrchestratorAgent
import asyncio
from src.tools.tools_factory import ToolsFactory, global_tool_factory
from src.tools.url_scraper_tool import url_scraper
from src.agents.research_expert import ResearchExpert
from src.models.schema.agent_schema import Agent
from src.agents.agent_registry import global_agent_registry

async def main(user_query) -> None:
    orchestrator = OrchestratorAgent()
    await orchestrator.start(user_query=user_query)
    
if __name__ == "__main__":
    #global_tool_factory.register_tool(url_scraper)
    #print(global_tool_factory.get_all_tools())
    
    # # Create an instance
    # r = ResearchExpert()
    # r.add_tool(url_scraper)
    # print(r.get_available_tools())
    # o  = OrchestratorAgent()
    # global_agent_registry.register(agent=Agent(name=r._schema.name, description=r._schema.description, tools=r.get_available_tools()))
    r= ResearchExpert()
    global_agent_registry.register(agent=Agent(
        name = r._schema.name,
        description= r._schema.description,
        tools=[url_scraper]
    ))
    
    print("available agents:", global_agent_registry.get_all_agents())
    
    print(f" avilable tools {r.get_available_tools()}")

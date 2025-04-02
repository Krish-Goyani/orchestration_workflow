from typing import Dict, List, Optional
from src.models.schema.agent_schema import Agent
from src.models.schema.tools_schema import Tool

class AgentRegistry:
    """
    Global registry for all agents in the system.
    Provides a centralized way to register and retrieve agents along with their tools.
    """
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._agent_tools: Dict[str, List[Tool]] = {}
        
    def register(self, agent: Agent) -> None:
        """Register an agent with the system"""
        self._agents[agent.name] = agent
        
        # Initialize the agent's tool list if it doesn't exist
        if agent.name not in self._agent_tools:
            self._agent_tools[agent.name] = []
            
        # Add any tools that came with the agent
        if agent.tools:
            for tool in agent.tools:
                self.add_tool_to_agent(agent.name, tool)
                
        print(f"Agent {agent.name} registered successfully.")
        
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a specific agent by name"""
        agent = self._agents.get(name)
        if agent:
            # Always ensure the agent has the latest tools
            agent.tools = self.get_agent_tools(name)
        return agent
        
    def get_all_agents(self) -> List[Agent]:
        """
        Get all registered agents with their current tools
        Returns a new list of Agent objects with updated tools
        """
        updated_agents = []
        for agent_name, agent in self._agents.items():
            # Create a new agent instance with updated tools
            updated_agent = Agent(
                name=agent.name,
                description=agent.description,
                tools=self.get_agent_tools(agent_name)
            )
            updated_agents.append(updated_agent)
        return updated_agents
    
    def add_tool_to_agent(self, agent_name: str, tool: Tool) -> bool:
        """
        Add a tool to a specific agent
        Returns True if successful, False otherwise
        """
        if agent_name not in self._agents:
            print(f"Agent {agent_name} not found in registry.")
            return False
            
        if agent_name not in self._agent_tools:
            self._agent_tools[agent_name] = []
            
        # Check if tool already exists
        existing_tool_names = [t.name for t in self._agent_tools[agent_name]]
        if tool.name in existing_tool_names:
            print(f"Tool {tool.name} already exists for agent {agent_name}.")
            return False
            
        self._agent_tools[agent_name].append(tool)
        print(f"Tool {tool.name} added to agent {agent_name}.")
        return True
        
    def remove_tool_from_agent(self, agent_name: str, tool_name: str) -> bool:
        """
        Remove a tool from a specific agent
        Returns True if successful, False otherwise
        """
        if agent_name not in self._agents:
            print(f"Agent {agent_name} not found in registry.")
            return False
            
        if agent_name not in self._agent_tools:
            print(f"No tools registered for agent {agent_name}.")
            return False
            
        for i, tool in enumerate(self._agent_tools[agent_name]):
            if tool.name == tool_name:
                self._agent_tools[agent_name].pop(i)
                print(f"Tool {tool_name} removed from agent {agent_name}.")
                return True
                
        print(f"Tool {tool_name} not found for agent {agent_name}.")
        return False
        
    def get_agent_tools(self, agent_name: str) -> List[Tool]:
        """Get all tools for a specific agent"""
        if agent_name not in self._agents:
            print(f"Agent {agent_name} not found in registry.")
            return []
            
        return self._agent_tools.get(agent_name, [])
        
    def clear(self) -> None:
        """Clear all registered agents and their tools"""
        self._agents.clear()
        self._agent_tools.clear()
        print("Agent registry cleared.")

# Global singleton instance
global_agent_registry = AgentRegistry()
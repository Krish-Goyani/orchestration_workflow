import functools
import inspect
import re
from typing import Callable, get_type_hints

from src.models.schema.tools_schema import Tool
from src.tools.url_scraper_tool import url_scraper

class ToolsFactory:
    """
    A factory class for creating tool instances.
    """

    def __init__(self):
        self.tools = {}
        
        
    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
        print(f"Tool {tool.name} registered.")
        
        
    def get_all_tools(self) -> list[Tool]:
        return list(self.tools.values())
    
global_tool_factory = ToolsFactory()
        
        
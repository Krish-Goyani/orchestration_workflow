import inspect
from typing import Any, Dict, List, Optional

from src.models.schema.tools_schema import Tool


class ToolRegistry:
    """Registry for managing and accessing tools for agents."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        """Register a tool in the registry.

        Args:
            tool: The tool to register
        """
        self.tools[tool.name] = tool

    def register_tools(self, tools: List[Tool]) -> None:
        """Register multiple tools in the registry.

        Args:
            tools: List of tools to register
        """
        for tool in tools:
            self.register_tool(tool)

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by its name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            The tool if found, None otherwise
        """
        return self.tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools.

        Returns:
            List of all registered tools
        """
        return list(self.tools.values())

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool by its name with the given arguments.

        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            ValueError: If the tool is not found or if arguments are invalid
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        # Validate that all required parameters are provided
        sig = inspect.signature(tool.func)
        required_params = {
            param.name
            for param in sig.parameters.values()
            if param.default == inspect.Parameter.empty
            and param.kind != inspect.Parameter.VAR_KEYWORD
        }

        missing_params = required_params - set(arguments.keys())
        if missing_params:
            raise ValueError(
                f"Missing required parameters for tool '{tool_name}': {', '.join(missing_params)}"
            )

        # Filter arguments to only include those expected by the function
        valid_args = {k: v for k, v in arguments.items() if k in sig.parameters}

        # Call the function with the arguments
        if inspect.iscoroutinefunction(tool.func):
            return await tool.func(**valid_args)
        else:
            return tool.func(**valid_args)


# Create a singleton instance
global_tool_registry = ToolRegistry()

import functools
import inspect
import re
from typing import Callable, get_type_hints

from src.models.schema.tools_schema import Tool


def tool():
    """
    Decorator to register a function as a tool and extract its metadata.

    The decorator extracts:
    - name: str (from function name)
    - description: str (from docstring)
    - func: Callable[..., str] (the function itself)
    - parameters: Dict[str, Dict[str, str]] (from function signature and docstring)

    Usage:
    @tool()
    async def get_forecast(city: str) -> str:
        '''
        Get weather forecast for a location.

        Args:
            city: name of the city whose weather is to be fetched
        Returns:
            str: Weather forecast for the given location
        '''
        ...
    """

    def decorator(func: Callable):
        # Extract name from function name
        tool_name = func.__name__

        # Extract description from the first line of docstring
        docstring = inspect.getdoc(func) or ""
        description_lines = docstring.split("\n")
        tool_description = (
            description_lines[0].strip() if description_lines else ""
        )

        # Extract parameters from function signature
        parameters = {}
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        # Extract return type and description
        return_type = "Any"
        return_description = ""

        if "return" in type_hints:
            return_type = str(type_hints["return"].__name__)
        elif sig.return_annotation != inspect.Parameter.empty:
            return_type = str(sig.return_annotation)

        # Extract parameter descriptions from docstring using improved regex patterns
        # First, find the Args section
        args_match = re.search(
            r"Args:(.*?)(?:Returns:|$)", docstring, re.DOTALL
        )
        args_section = args_match.group(1) if args_match else ""

        # Extract parameter name and descriptions with a more flexible pattern
        param_descriptions = {}

        # Try to match parameters in the format "param_name (param_type): description"
        param_pattern1 = re.compile(
            r"\s*(\w+)\s*\(([^)]+)\):\s*(.*?)(?=\s*\w+\s*(?:\(|\:)|\s*Returns:|\s*$)",
            re.DOTALL,
        )
        matches1 = param_pattern1.findall(args_section)
        for param_name, param_type, param_desc in matches1:
            param_descriptions[param_name] = param_desc.strip()

        # If no matches, try simpler format "param_name: description"
        if not param_descriptions:
            param_pattern2 = re.compile(
                r"\s*(\w+):\s*(.*?)(?=\s*\w+\s*:|\s*Returns:|\s*$)",
                re.DOTALL,
            )
            matches2 = param_pattern2.findall(args_section)
            for param_name, param_desc in matches2:
                param_descriptions[param_name] = param_desc.strip()

        # If still no matches, try line-by-line parsing
        if not param_descriptions:
            lines = args_section.strip().split("\n")
            current_param = None
            current_description = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if this line starts a new parameter
                param_match = re.match(
                    r"(\w+)(?:\s*\([^)]+\))?:\s*(.*)", line
                )
                if param_match:
                    # Save the previous parameter if there is one
                    if current_param and current_description:
                        param_descriptions[current_param] = " ".join(
                            current_description
                        ).strip()

                    # Start a new parameter
                    current_param = param_match.group(1)
                    current_description = (
                        [param_match.group(2)]
                        if len(param_match.groups()) > 1
                        else []
                    )
                elif current_param:
                    # This line continues the description of the current parameter
                    current_description.append(line)

            # Save the last parameter
            if current_param and current_description:
                param_descriptions[current_param] = " ".join(
                    current_description
                ).strip()

        # Extract return description more carefully
        # First try to find the Returns section
        returns_section = ""
        returns_match = re.search(
            r"Returns:(.*?)(?=\n\s*\w+:|\Z)", docstring, re.DOTALL
        )
        if returns_match:
            returns_section = returns_match.group(1).strip()
        else:
            # Try a more lenient pattern
            returns_match = re.search(r"Returns:(.*)", docstring, re.DOTALL)
            if returns_match:
                returns_section = returns_match.group(1).strip()

        # Now parse the return section to extract type and description
        if returns_section:
            # Try to match "type: description" pattern
            return_type_desc_match = re.match(
                r"\s*(\w+):\s*(.*)", returns_section, re.DOTALL
            )
            if return_type_desc_match:
                return_type_from_doc = return_type_desc_match.group(
                    1
                ).strip()
                return_description = return_type_desc_match.group(2).strip()
                # Only update return_type if we don't already have it from type hints
                if return_type == "Any" and return_type_from_doc:
                    return_type = return_type_from_doc
            else:
                # If no match, use the entire section as description
                return_description = returns_section

        # Last resort: Manual extraction for return description
        if not return_description:
            try:
                # Find the line(s) between "Returns:" and the end of docstring
                docstring_lines = docstring.split("\n")
                start_idx = -1
                for i, line in enumerate(docstring_lines):
                    if "Returns:" in line:
                        start_idx = i
                        break

                if start_idx >= 0 and start_idx + 1 < len(docstring_lines):
                    # Extract the return description
                    return_line = docstring_lines[start_idx + 1].strip()
                    # Parse "str: markdown content of the url" format
                    return_match = re.match(
                        r"\s*(\w+):\s*(.*)", return_line
                    )
                    if return_match:
                        return_type_from_line = return_match.group(1)
                        if return_type == "Any" and return_type_from_line:
                            return_type = return_type_from_line
                        return_description = return_match.group(2).strip()
            except:
                pass

        # Populate parameters dictionary
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == "self":
                continue

            # Get parameter type
            param_type = "Any"
            if param_name in type_hints:
                param_type = str(type_hints[param_name].__name__)
            elif param.annotation != inspect.Parameter.empty:
                param_type = str(param.annotation)

            # Get parameter description
            param_desc = param_descriptions.get(param_name, "")

            parameters[param_name] = {
                "type": param_type,
                "description": param_desc,
            }

        # Store metadata in function
        func.__tool_metadata__ = {
            "name": tool_name,
            "description": tool_description,
            "func": func,
            "parameters": parameters,
            "return_type": return_type,
            "return_description": return_description,
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Create a Tool instance from the function metadata
        tool_instance = Tool(
            name=tool_name,
            description=tool_description,
            func=func,
            parameters=parameters,
            return_type=return_type,
            return_description=return_description,
        )

        return tool_instance

    return decorator

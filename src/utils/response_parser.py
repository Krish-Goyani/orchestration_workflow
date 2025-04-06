import json
import re
from typing import Any


def parse_response(response) -> Any:
    # First attempt to find a valid JSON block
    match = re.search(r"```json(.*)```", str(response), re.DOTALL)
    if match:
        json_str = match.group(1).strip()  # Extract and remove extra whitespace
        try:
            # Parse the JSON content into a Python dictionary
            response_data = json.loads(json_str)
            return response_data
        except json.JSONDecodeError as e:
            # If parsing fails, try a more robust approach with nested code blocks
            try:
                # Use a custom approach to handle nested code blocks
                # Replace escaped newlines in code blocks to prevent interference with JSON parsing
                preprocessed_json = preprocess_json_with_code_blocks(json_str)
                response_data = json.loads(preprocessed_json)
                return response_data
            except json.JSONDecodeError as e2:
                print(
                    "Failed to decode JSON with both methods:",
                    e2,
                    "response data:",
                    json_str,
                )

                # Last resort: try to clean and repair the JSON manually
                try:
                    cleaned_json = manual_json_cleaner(json_str)
                    response_data = json.loads(cleaned_json)
                    return response_data
                except Exception as e3:
                    print("All JSON parsing attempts failed:", e3)
                    # Return a partial parsed response with available fields
                    return extract_partial_json(json_str)
    else:
        print("No JSON block found in the response.")
        return None


def preprocess_json_with_code_blocks(json_str):
    """
    Preprocess JSON string to handle nested code blocks by temporarily replacing them
    with placeholders, then parsing the JSON, and finally restoring the code blocks.
    """
    # Simple approach: escape all internal triple backticks in values
    # This works for the common case where nested code blocks are in string values
    state = "normal"
    in_string = False
    result = []
    i = 0

    while i < len(json_str):
        char = json_str[i]

        # Track string state
        if char == '"' and (i == 0 or json_str[i - 1] != "\\"):
            in_string = not in_string

        # Handle nested code blocks only when inside a string
        if in_string and i + 2 < len(json_str) and json_str[i : i + 3] == "```":
            # Escape the triple backticks
            result.append("\\u0060\\u0060\\u0060")
            i += 3
        else:
            result.append(char)
            i += 1

    return "".join(result)


def manual_json_cleaner(json_str):
    """
    Attempt to manually clean and repair broken JSON with nested code blocks.
    """
    # Replace literal \n with actual newlines in nested code blocks
    json_str = re.sub(r"\\n", "\n", json_str)

    # Look for unterminated strings by checking for odd number of quotes
    quote_count = json_str.count('"')
    if quote_count % 2 == 1:
        # Add a closing quote at the end
        json_str += '"'

    # Ensure proper JSON structure
    if not json_str.strip().startswith("{"):
        json_str = "{" + json_str
    if not json_str.strip().endswith("}"):
        json_str = json_str + "}"

    return json_str


def extract_partial_json(json_str):
    """
    Extract partial JSON data when full parsing fails.
    This is a fallback to return at least some structured data.
    """
    result = {}

    # Try to extract key-value pairs using regex
    pairs = re.findall(
        r'"([^"]+)"\s*:\s*("(?:\\.|[^"\\])*"|[^,}\s]+)', json_str
    )
    for key, value in pairs:
        # Clean the value
        if value.startswith('"') and value.endswith('"'):
            # It's a string, remove the quotes and unescape
            value = value[1:-1].replace('\\"', '"')
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.lower() == "null":
            value = None
        else:
            try:
                # Try to convert to number
                value = float(value) if "." in value else int(value)
            except ValueError:
                # Keep as string if conversion fails
                pass

        result[key] = value

    return result


def ensure_dict(response):
    if isinstance(response, str):  # Check if it's a string
        try:
            response = json.loads(
                response.replace("'", '"')
            )  # Convert single quotes to double quotes for valid JSON
        except json.JSONDecodeError:
            pass  # If decoding fails, return the original response
    return response  # Return as dict if converted, else original

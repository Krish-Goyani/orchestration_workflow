import json
import re
from typing import Any


def parse_response(response) -> Any:
    match = re.search(r"```json(.*?)```", str(response), re.DOTALL)
    if match:
        json_str = match.group(1).strip()  # Extract and remove extra whitespace
        try:
            # Parse the JSON content into a Python dictionary
            response_data = json.loads(json_str)
            return response_data
        except json.JSONDecodeError as e:
            print("Failed to decode JSON:", e, "response data:", response)
            return None
    else:
        print("No JSON block found in the response.")
        return None


def ensure_dict(response):
    if isinstance(response, str):  # Check if it's a string
        try:
            response = json.loads(
                response.replace("'", '"')
            )  # Convert single quotes to double quotes for valid JSON
        except json.JSONDecodeError:
            pass  # If decoding fails, return the original response
    return response  # Return as dict if converted, else original

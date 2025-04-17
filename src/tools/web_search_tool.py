from typing import Any, List

import httpx

from src.config.settings import settings
from src.tools.tool_decorator import tool

WEBSEARCH_END_POINT = f"https://google.serper.dev/search?q={{query}}&apiKey={settings.SERPER_API_KEY}"

timeout = httpx.Timeout(
    connect=60.0,  # Time to establish a connection
    read=120.0,  # Time to read the response
    write=120.0,  # Time to send data
    pool=60.0,  # Time to wait for a connection from the pool
)


async def make_websearch_request(url: str) -> dict[str, Any] | None:
    "make a websearch request to the given url"
    try:
        # Use async with to ensure proper client cleanup
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            response = await client.get(url=url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error in web search request: {e}")
        return None


@tool()
async def websearch(query: str) -> List[str]:
    """this is the websearch tool that will search the web for the given query and return the urls

    Args:
        query (str): query to search the web for

    Returns:
        List[str]: list of urls as search result
    """

    urls = await make_websearch_request(WEBSEARCH_END_POINT.format(query=query))
    if not urls:
        return ["not found"]  # Return a list instead of a string

    results = [res["link"] for res in urls["organic"]][:1]
    return results

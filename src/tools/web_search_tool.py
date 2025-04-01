from typing import Any, List

import httpx

from src.config.settings import settings
from src.tools.tools_factory import tool

WEBSEARCH_END_POINT = f"https://google.serper.dev/search?q={{query}}&apiKey={settings.SERPER_API_KEY}"


async def make_websearch_request(url: str) -> dict[str, Any] | None:
    "make a weather request to the given url"
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url=url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(e)
            return None


@tool
async def websearch(query: str) -> List[str]:
    """this is the websearch tool that will search the web for the given query and return the urls

    Args:
        query (str): query to search the web for

    Returns:
        List[str]: list of urls as search result
    """

    urls = await make_websearch_request(WEBSEARCH_END_POINT.format(query=query))
    if not urls:
        return "not found"

    results = [res["link"] for res in urls["organic"]]
    return results

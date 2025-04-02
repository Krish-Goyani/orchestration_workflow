from crawl4ai import AsyncWebCrawler

from src.config.crawler_config import browser_conf, crawler_cfg
from src.tools.tool_decorator import tool


@tool()
async def url_scraper(url: str) -> str:
    """this is the url scraper tool that will scrape the given url and return the content as the markdown

    Args:
        url (str): url which you want to scrape

    Returns:
        str: markdown content of the url
    """

    try:
        async with AsyncWebCrawler(config=browser_conf) as crawler:
            result = await crawler.arun(url=url, config=crawler_cfg)
            result = str(result.markdown.fit_markdown)
            return result
    except Exception as e:
        print(e)
        return ""

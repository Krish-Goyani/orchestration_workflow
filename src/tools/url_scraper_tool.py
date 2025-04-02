from crawl4ai import AsyncWebCrawler

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
        # Create a new crawler instance for each call
        crawler = AsyncWebCrawler()
        await crawler.start()  # Explicitly start the crawler

        try:
            result = await crawler.arun(url=url)
            result = result.markdown
            return result
        finally:
            # Ensure crawler is properly closed even if an error occurs
            await crawler.close()
    except Exception as e:
        print(f"URL scraper error: {e}")
        return f"Error scraping URL: {str(e)}"

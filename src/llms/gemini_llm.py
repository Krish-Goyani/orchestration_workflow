from google import genai

from src.config.settings import settings


class GeminiLLM:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.0-flash"

    async def generate_response(self, config, contents):
        response = await self.client.aio.models.generate_content(
            model=self.model_name, config=config, contents=contents
        )
        if not response:
            return None
        # time.sleep(5)
        return response.text

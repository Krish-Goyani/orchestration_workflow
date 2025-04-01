import re
from src.app.config.settings import settings
from google import genai
from src.app.prompts.workers_prompt import PROJECT_PALNER_PROMPT, ARCHITECTURE_PROMPT

class PlanningService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.0-flash"
        
        
    async def generate_requirements_and_plan(self, user_query: str) -> str:
        prompt = PROJECT_PALNER_PROMPT.format(user_query=user_query)
        
        response = await self.client.aio.models.generate_content(
                model = self.model,
                contents=prompt
            )
        
        return response.text
    
    async def generate_architecture(self, user_query: str, requirements_and_plan: str) -> str:
        prompt = ARCHITECTURE_PROMPT.format(user_query=user_query, requirements_analysis_and_project_plan=requirements_and_plan)
        
        response = await self.client.aio.models.generate_content(
            model = self.model,
            contents=prompt
        )
        return response.text
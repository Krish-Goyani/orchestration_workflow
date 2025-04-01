from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MAX_ITERATIONS: int = 3
    SERPER_API_KEY: str
    WEATHER_API_KEY: str

    class Config:
        env_file = "src/.env"


settings = Settings()

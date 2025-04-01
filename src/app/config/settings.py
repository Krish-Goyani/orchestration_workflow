from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MAX_ITERATIONS : int

    class Config:
        env_file = "src/.env"
        env_file_encoding = "utf-8"


settings = Settings()
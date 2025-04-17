from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MAX_ITERATIONS: int = 20
    SERPER_API_KEY: str
    WEATHER_API_KEY: str
    MAX_AGENT_ITERATIONS: int = 4
    SUMMARIZATION_THRESHOLD: int = 3
    RECENT_MESSAGE_COUNT: int = 5
    RAG_TOP_K: int = 3
    RECENT_ITERATIONS_LIMIT: int = 10
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    ST_MEMORY_EXPIRATION: int = 3600
    MONGODB_DB_NAME: str = "MAS"
    MONGODB_COLLECTION_NAME: str = "history"
    MONGODB_SUMMARY_COLLECTION_NAME: str = "summary"
    MONGODB_SESSION_COLLECTION_NAME: str = "sessions"
    MONGODB_URL: str = "mongodb://localhost:27017/"
    PINECONE_API_KEY: str
    INDEX_NAME: str = "agent-memory"
    INDEX_HOST: str = (
        "https://agent-memory-auoio4m.svc.aped-4627-b74a.pinecone.io"
    )

    class Config:
        env_file = "src/.env"


settings = Settings()

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    GROQ_API_KEY: str
    NEO4J_PASSWORD: str

    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: Optional[str] = None

    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"

    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 2048
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"

    RERANK_TOP_N: int = 5
    RETRIEVAL_TOP_K: int = 10
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    FIGURES_DIR: str = "/app/figures"
    ALLOWED_ORIGINS: str = "http://localhost:3000"


settings = Settings()

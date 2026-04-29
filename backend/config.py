from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str = "your_groq_api_key_here"
    COHERE_API_KEY: str = "your_cohere_api_key_here"
    WEAVIATE_URL: str = "http://weaviate:8080"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "researchos123"
    OLLAMA_URL: str = "http://ollama:11434"
    EMBED_MODEL: str = "nomic-embed-text"
    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 2048
    COHERE_RERANK_MODEL: str = "rerank-english-v3.0"
    COHERE_TOP_N: int = 10
    CLIP_MODEL: str = "ViT-B/32"
    WHISPER_MODEL: str = "base"
    RETRIEVAL_TOP_K: int = 20
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    BACKEND_PORT: int = 8000
    FIGURES_DIR: str = "/app/figures"

    class Config:
        env_file = ".env"

settings = Settings()

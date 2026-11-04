from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All tunables for ResearchOS.

    Defaults are the *initial hyper-parameters* from Section 4.2 of the Phase 3
    report; every value can be overridden from the environment / .env file so the
    development split can be used to tune them.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ------------------------------------------------------------------ services
    GROQ_API_KEY: str = "your_groq_api_key_here"
    COHERE_API_KEY: str = "your_cohere_api_key_here"
    WEAVIATE_URL: str = "http://weaviate:8080"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "researchos123"
    OLLAMA_URL: str = "http://ollama:11434"
    BACKEND_PORT: int = 8000
    FIGURES_DIR: str = "/app/figures"

    # ------------------------------------------------- models (generation etc.)
    # "groq" (hosted Llama-3) or "ollama" (local Llama-3.1-8B, as in the report).
    LLM_PROVIDER: str = "groq"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 2048
    OLLAMA_LLM_MODEL: str = "llama3.1:8b"
    GENERATION_TEMPERATURE: float = 0.0

    # Embeddings (Ollama). Prefixes are model specific: nomic-embed-text wants the
    # two below, bge-* models want an instruction on the query side only.
    EMBED_MODEL: str = "nomic-embed-text"
    EMBED_QUERY_PREFIX: str = "search_query: "
    EMBED_DOC_PREFIX: str = "search_document: "
    EMBED_BATCH_SIZE: int = 32

    # Optional vision-language model used to describe figures so they can be
    # searched as text. "" disables it (caption + OCR text are used instead).
    VLM_PROVIDER: str = ""  # "", "ollama" or "groq"
    VLM_MODEL: str = ""  # e.g. "qwen2.5vl:7b" (ollama)

    WHISPER_MODEL: str = "base"
    AUDIO_WINDOW_SEC: float = 30.0  # consecutive Whisper segments are merged up to this

    # ------------------------------------------------ Module 1: ingestion
    CHUNK_SIZE: int = 300  # tokens (approximated from words, see services/chunking.py)
    CHUNK_OVERLAP_RATIO: float = 0.15
    CONCEPT_EXTRACTION: bool = True
    CONCEPT_BATCH_SIZE: int = 4  # chunks per LLM call
    CONCEPT_MAX_PER_CHUNK: int = 8
    CONCEPT_WORKERS: int = 2
    EDGE_INIT_WEIGHT: float = 0.5

    # ------------------------------------------------ Module 2: retrieval
    RETRIEVAL_TOP_K: int = 20  # results per first-stage retriever
    SEED_K: int = 10  # fused results that seed the graph walk
    GRAPH_FANOUT: int = 20  # max neighbours followed per node and hop
    GRAPH_RESOLVE_PER_NODE: int = 2  # chunks taken from a reached concept / paper
    CANDIDATE_POOL_MAX: int = 50
    FUSION: str = "alpha"  # "alpha" (weighted scores) or "rrf"
    RRF_K: int = 60
    EDGE_TRAVERSE_MIN: float = 0.3
    EXPLORE_PROB: float = 0.05

    # ------------------------------------------------ Module 3: feedback
    COHERE_RERANK_MODEL: str = "rerank-v3.5"
    RELEVANCE_CUTOFF: float = 0.3
    CONTEXT_SIZE: int = 5  # items passed to the generator (k)
    EDGE_LR: float = 0.1
    PRUNE_MIN_VISITS: int = 5
    PRUNE_BELOW: float = 0.2
    ALPHA_INIT: float = 0.5
    ALPHA_RATE: float = 0.05
    ALPHA_MIN: float = 0.2
    ALPHA_MAX: float = 0.9
    FEEDBACK_ENABLED: bool = True  # global kill-switch (freeze the memory)

    # ------------------------------------------------ Module 4: generation
    VERIFY_CLAIMS: bool = True
    VERIFY_MODE: str = "flag"  # "flag" keeps unsupported claims marked, "remove" drops them


settings = Settings()

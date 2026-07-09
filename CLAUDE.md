# CLAUDE.md — ResearchOS (Multi-Modal Graph RAG)

## What this project is
FastAPI + React Graph RAG system: ingests PDFs (text + figures) and audio, stores vectors in Qdrant and a knowledge graph in Neo4j, answers queries with Groq Llama 3.3 with citations. Docker Compose for local dev; deployed free-tier (see Phase 7).

## Prime directive for this session
Implement `HANDOFF_PLAN.md` phase by phase. Do not skip Phase 0 (security). After each phase: run the stack, verify, and commit with a conventional-commit message before moving on.

## Hard constraints
- **Groq is the ONLY AI API.** The only AI secret is `GROQ_API_KEY`. Everything must be free tier or free/local:
  - LLM generation + concept extraction: Groq `llama-3.3-70b-versatile`
  - Audio transcription: Groq Whisper API (`whisper-large-v3-turbo`) — remove faster-whisper
  - Text embeddings: **fastembed** (ONNX, in-process, CPU) `BAAI/bge-small-en-v1.5` — replaces Ollama entirely; the ollama service is removed from compose
  - Image + CLIP-text embeddings: **fastembed** `Qdrant/clip-ViT-B-32-vision` + `Qdrant/clip-ViT-B-32-text` — replaces open_clip/torch
  - Reranking: **fastembed** `TextCrossEncoder` (`Xenova/ms-marco-MiniLM-L-6-v2`) — remove Cohere entirely
  - No torch, no torchvision, no sentence-transformers in requirements. ONNX only. Backend image must stay small enough for free-tier hosting.
- **Vector DB: Qdrant** (replaces Weaviate). Local dev: `qdrant/qdrant` container. Production: Qdrant Cloud free 1GB cluster (`QDRANT_URL` + `QDRANT_API_KEY` env vars; api key optional locally).
- **Graph DB: Neo4j.** Local dev: container. Production: Neo4j AuraDB Free (`NEO4J_URI` supports `neo4j+s://`).
- Deployment target (Phase 7): backend Docker image on **Hugging Face Spaces** (free, 16GB RAM), frontend static build on **Vercel**, Qdrant Cloud + AuraDB Free. Zero monthly cost.
- No paid services anywhere. Stack must run CPU-only.

## Architecture map
- `backend/main.py` — FastAPI app, Qdrant collection init, Neo4j constraints
- `backend/config.py` — pydantic-settings, reads `.env`
- `backend/routers/` — `ingest.py` (PDF/audio upload), `query.py`, `graph.py`
- `backend/services/` — `pdf_extractor.py` (PyMuPDF + OCR), `embedder.py`, `clip_embedder.py`, `audio_transcriber.py`, `reranker.py`, `generator.py` (Groq), `qdrant_client.py` (replaces `weaviate_client.py`), `neo4j_client.py`, `retriever.py` (pipeline)
- `frontend/src/` — React 19 + Vite + Tailwind v4; `hooks/useQuery.ts`, `components/` (QueryBar, AnswerCard, SourceChip, FigureCitation, UploadPanel, GraphExplorer)
- Qdrant collections: `text_chunks`, `figure_chunks`, `audio_chunks`. Neo4j: `Paper`, `Author`, `Concept` nodes; `WROTE`, `CITES`, `HAS_CONCEPT` edges (the last two are NOT yet created at ingest — Phase 2 fixes this).

## Conventions
- Python: type hints, `logging` module (never `print`), raise `HTTPException` with correct status codes, pinned deps in `requirements.txt`.
- TypeScript: no `any` — define interfaces for API responses in `src/types.ts`.
- All frontend API calls go through relative `/api/...` paths (nginx proxies locally; `VITE_API_URL` env var points to the Space URL in production). Never hardcode hosts.
- Secrets only via `.env` (gitignored). `docker-compose.yml` references `${VARS}`, never literal passwords.
- Figures storage: files on local disk work on Spaces (ephemeral but acceptable for demo); store figure bytes base64 in Qdrant payload as fallback so figures survive restarts.

## Commands
- Full stack: `docker compose up -d --build`
- Backend tests: `cd backend && pytest`
- Frontend lint/build: `cd frontend && npm run lint && npm run build`
- Health: `curl localhost:8054/health`

## Known context
- `PROJECT_AUDIT.md` contains the full 38-item findings list this plan was derived from.
- The whole working tree is currently uncommitted — Phase 0 starts with a cleanup commit.
- `.env` exists locally with real keys — never commit or print it.
- Embedding model change (nomic 768-d → bge-small 384-d) + DB change means all data is re-ingested from scratch; no migration needed.

# ResearchOS — Multi-Modal Graph RAG

Ask questions across research papers (PDF), their figures, and lecture audio. Answers come back with text citations **and the figures that support them**, backed by a knowledge graph of authors and papers.

Plain vector search finds similar text. ResearchOS also keeps an explicit graph in Neo4j and uses it to pull in related authors, papers, and concepts, so answers have more context than the top-k chunks alone.

## How it works

```
PDF ──► PyMuPDF ──► text chunks ──► nomic-embed-text (Ollama) ──┐
            └────► figures ─────► CLIP ViT-B/32 ────────────────┼─► Weaviate (TextChunk, FigureChunk)
Audio ─► faster-whisper ─► segments ─► nomic-embed-text ────────┘
metadata (authors, title, year) ────────────────────────────────────► Neo4j

Query ─► embed (text + CLIP) ─► Weaviate retrieval ─► Neo4j graph expansion
      ─► Cohere rerank ─► Groq Llama 3.3 70B ─► answer + citations + figures
```

| Layer | Tech |
|---|---|
| Backend | FastAPI (Python), Pydantic |
| Frontend | React, Vite, TypeScript, Tailwind, React Force Graph |
| Vector DB | Weaviate 1.24 |
| Graph DB | Neo4j 5 |
| Embeddings | nomic-embed-text (Ollama), CLIP ViT-B/32 |
| Audio | faster-whisper |
| Reranking / generation | Cohere Rerank, Groq (`llama-3.3-70b-versatile`) |
| Orchestration | Docker Compose (5 services) |

## Features

- Multi-modal ingestion: PDF text, extracted figures, and audio transcripts in one index
- Separate text and image retrieval, so figures are not drowned out by text scores
- Graph expansion from retrieved chunks to related authors and papers
- Cohere reranking before generation to cut irrelevant context
- Interactive graph explorer and figure-citation cards in the UI

## Run it

Requirements: Docker with Compose, a free [Groq](https://console.groq.com) key and a free [Cohere](https://dashboard.cohere.com) key. The backend container requests an NVIDIA GPU (see `docker-compose.yml`); remove the `deploy:` block to run on CPU, more slowly.

```bash
cp .env.example .env        # add GROQ_API_KEY and COHERE_API_KEY
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API (docs at `/docs`) | http://localhost:8054 |
| Neo4j browser | http://localhost:7474 |

Model weights download on the first upload, so the first run is slow. Pull the embedding model once with `docker compose exec ollama ollama pull nomic-embed-text` if it is not fetched automatically.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/ingest/pdf` | Ingest a paper (text, figures, metadata) |
| POST | `/ingest/audio` | Transcribe and ingest a lecture |
| POST | `/query` | Ask a question, get answer + sources + figures |
| GET | `/graph/nodes`, `/graph/edges` | Knowledge graph for the explorer |

## Repository layout

```
backend/    FastAPI app: routers/, services/ (retriever, reranker, generator, clients)
frontend/   React app: components/ (AnswerCard, FigureCitation, GraphExplorer, ...)
docs/       Original design document (schemas, build plan, troubleshooting)
```

The full design document, including the graph and Weaviate schemas, is in [`docs/DESIGN.md`](docs/DESIGN.md).

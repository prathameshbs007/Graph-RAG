# HANDOFF_PLAN.md — Implementation plan for Claude Code

Execute phases in order. Verify + git commit after each phase. Constraints in `CLAUDE.md` apply throughout: Groq is the only AI API; Qdrant (free) replaces Weaviate; fastembed ONNX models replace Ollama/torch/Cohere; final deployment is 100% free tier.

---

## Phase 0 — Repo hygiene & security (do first)

0.1 Delete from repo root: all `backend_logs*.txt`, `ollama_logs_3.txt`, `2301.04275v3.pdf`, `INTERVIEW_PREP.md`, `backend/test_weaviate.py`.
0.2 Fix `.gitignore`: remove the blanket `*.txt` and `*.pdf` patterns; add `logs/`, `*.log` instead. Verify `backend/requirements.txt` stays tracked.
0.3 Commit everything currently uncommitted as a baseline commit before making further changes.
0.4 **Cypher injection** (`backend/routers/graph.py`): validate `node_type`/`edge_type` against whitelists (`{"Paper","Author","Concept"}` / `{"WROTE","CITES","HAS_CONCEPT"}`), pass `limit` as a query parameter, return 422 on invalid input.
0.5 **Secrets**: remove hardcoded `researchos123` from `docker-compose.yml` (use `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}`, `${NEO4J_PASSWORD}` in the healthcheck) and from `config.py` defaults (required field, no default).
0.6 **Upload safety** (`backend/routers/ingest.py`): max file size 50 MB, validate content (PDF magic bytes / audio extension whitelist), never embed `file.filename` in paths (UUID only), delete temp files in `finally`.
0.7 **Proper error codes**: replace `status: "error"`-in-200 responses with `HTTPException` (400/422/502).
0.8 Replace all `print()` with `logging`; on embedding failure, abort ingestion with 502 instead of inserting empty vectors.
0.9 Backend `.dockerignore` (mirror frontend's); run container as non-root.
0.10 Add `LICENSE` (MIT).

Verify: stack builds and runs; `/health` 200; injection attempts on `/graph/*` rejected. Commit.

## Phase 1 — Free-tier stack swap (Qdrant + fastembed + Groq-only)

1.1 **Weaviate → Qdrant**: replace `services/weaviate_client.py` with `services/qdrant_client.py` using `qdrant-client`. Collections `text_chunks` (384-d, bge-small), `figure_chunks` (512-d, CLIP), `audio_chunks` (384-d), cosine distance. Payloads mirror the old Weaviate properties. Config: `QDRANT_URL` (default `http://qdrant:6333`), optional `QDRANT_API_KEY`. Update `main.py` init (create collections if missing, payload index on `paper_id`). Point IDs = UUIDs → use them as `chunk_id` (fixes the `hash()` bug).
1.2 **Ollama → fastembed text embeddings**: rewrite `services/embedder.py` with `fastembed.TextEmbedding("BAAI/bge-small-en-v1.5")` (lazy singleton, batch support). Remove the `ollama` service from `docker-compose.yml` and `OLLAMA_*`/`EMBED_MODEL` config.
1.3 **open_clip → fastembed CLIP**: rewrite `services/clip_embedder.py` with fastembed `ImageEmbedding("Qdrant/clip-ViT-B-32-vision")` and `TextEmbedding("Qdrant/clip-ViT-B-32-text")`. Remove torch/torchvision/open_clip_torch/Pillow-only-if-unused from requirements (PyMuPDF still needs Pillow for figure saving — keep).
1.4 **Cohere → fastembed reranker**: rewrite `services/reranker.py` with `fastembed.rerank.cross_encoder.TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2")`. Remove `cohere` dep and `COHERE_*` config (rename to `RERANK_TOP_N`).
1.5 **faster-whisper → Groq Whisper**: rewrite `services/audio_transcriber.py` to call Groq audio transcription (`whisper-large-v3-turbo`, `response_format="verbose_json"`) for segment timestamps. Remove `faster-whisper`. Same return contract (`chunks_data, duration, num_segments`).
1.6 Update `docker-compose.yml`: services = frontend, backend, qdrant (`qdrant/qdrant` + volume + healthcheck), neo4j. Remove ALL GPU `deploy` blocks (nothing needs GPU now). Remove obsolete `version:` key.
1.7 Pre-download the three ONNX models in the backend Dockerfile (`RUN python -c "..."`) so cold starts are fast and the image is self-contained.
1.8 **Pin all Python deps** exactly once the build passes.
1.9 `.env.example` rewrite: required = `GROQ_API_KEY`, `NEO4J_PASSWORD`; optional overrides = `QDRANT_URL`, `QDRANT_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, model/tuning vars. Every default must match `config.py` (`RERANK_TOP_N=5`, `RETRIEVAL_TOP_K=10` in both).
1.10 Figures durability: alongside saving to `FIGURES_DIR`, store figure image bytes (base64, JPEG ≤200KB) in the Qdrant payload; `/figures/{figure_id}` endpoint serves from disk, falls back to payload. (Needed because free hosting has ephemeral disk.)

Verify: fresh `docker compose down -v && up -d --build`, CPU-only, only `GROQ_API_KEY` + `NEO4J_PASSWORD` in `.env` → ingest PDF, ingest audio, query returns reranked cited answer with figures. Commit.

## Phase 2 — Real Graph RAG (highest resume value)

2.1 New `services/concept_extractor.py`: after PDF text extraction, one Groq call (JSON mode) over first ~3 pages + abstract extracting `{concepts: [...], cited_titles: [...]}`. Graceful failure → empty lists.
2.2 Ingest: `MERGE (c:Concept {id: toLower(name)}) SET c.name=$name` + `(p)-[:HAS_CONCEPT]->(c)`; fuzzy-match cited titles against existing Paper titles (case-insensitive CONTAINS) → `(p)-[:CITES]->(existing)`.
2.3 `graph_nodes_created` in the response reflects reality.
2.4 `retriever.py`: use graph concepts to enrich LLM context — fetch other papers sharing concepts with retrieved papers, include titles in `graph_context`.
2.5 Verify Graph Explorer shows Concept nodes and CITES edges after ingesting 2+ related papers.

Commit.

## Phase 3 — Backend correctness

3.1 Score handling: never rank CLIP-space and text-space scores in one list — keep figure results separate end-to-end; sort each group internally.
3.2 Add `start_time`/`end_time` to audio search payload fields and `SourceChunk` (optional); used by frontend timestamp badge.
3.3 Honor `QueryRequest.top_k` and `rerank_top_n` through the pipeline; DROP `image_base64` from the model (dead surface).
3.4 Replace deprecated `@app.on_event("startup")` with lifespan context manager.
3.5 Move ingestion to `BackgroundTasks` + `GET /ingest/status/{id}` polling endpoint (in-memory status dict is fine).
3.6 Fix mid-file import in `routers/ingest.py`.
3.7 `year` defaults to `None`, not 2024.
3.8 Enrich `/health`: report Qdrant, Neo4j, and Groq-key-present status individually.
3.9 `clear_db.py`: require `--yes` flag; clear both Qdrant collections and Neo4j (`MATCH (n) DETACH DELETE n`).

Commit.

## Phase 4 — Frontend correctness

4.1 `src/lib/api.ts`: single axios instance, `baseURL: import.meta.env.VITE_API_URL ?? '/api'`. Replace every hardcoded `http://localhost:8054` (useQuery.ts, UploadPanel.tsx, GraphExplorer.tsx, FigureCitation.tsx). Figure image URLs built from the same base.
4.2 `nginx.conf`: `location /api/ { proxy_pass http://backend:8000/; }` + `client_max_body_size 60m;`. Remove FastAPI CORS wildcard — allow only configured origins via `ALLOWED_ORIGINS` env (needed in production since Vercel frontend and HF Space are different origins).
4.3 Vite dev proxy for `/api` → `http://localhost:8054`.
4.4 `src/types.ts` with interfaces matching Pydantic models; remove every `any`.
4.5 UploadPanel: switch to axios with real `onUploadProgress`, then poll `/ingest/status/{id}` until done. Remove fake progress values.
4.6 `npm run lint && npm run build` pass clean.

Commit.

## Phase 5 — Tests + CI

5.1 Backend pytest: `chunk_text` units, concept-extractor JSON parsing (mock Groq), reranker ordering, graph router injection attempts → 422, TestClient tests for `/health` and `/query` (mocked services).
5.2 GitHub Actions: backend job (ruff + pytest), frontend job (eslint + tsc build) on push/PR.
5.3 Add `ruff` config; fix findings.

Commit.

## Phase 6 — Docs & polish

6.1 Merge the two READMEs into ONE accurate README: stack table (Groq Llama 3.3 + Groq Whisper, fastembed ONNX embeddings/CLIP/reranker, Qdrant, Neo4j, React 19), headline: "runs on 100% free tier — single AI API key (Groq)", architecture diagram, working quickstart, API reference, live demo URL placeholder. Delete `README_final.md`.
6.2 `backend/eval/run_eval.py`: 10–15 hand-written Q/A pairs over a sample paper; measure retrieval hit-rate + citation presence; report numbers in README.
6.3 Full smoke test from scratch; final commit.

## Phase 7 — Free-tier deployment (Option 1)

All free, no credit card required except where noted:

7.1 **Qdrant Cloud**: user creates a free 1GB cluster at cloud.qdrant.io → gets `QDRANT_URL` + `QDRANT_API_KEY`. Code already supports these env vars (Phase 1). PAUSE and ask the user for these values when reached.
7.2 **Neo4j AuraDB Free**: user creates free instance at console.neo4j.io → `neo4j+s://` URI + password. Verify the driver works with `neo4j+s://` scheme. PAUSE and ask the user.
7.3 **Backend → Hugging Face Spaces** (free CPU, 16GB RAM — fits the ONNX models comfortably):
   - Add `Dockerfile` compatibility: Space runs the existing backend Dockerfile; app must listen on port 7860 (`PORT` env var, default 8000 locally).
   - Create Space (Docker SDK) under the user's HF account (`prathameshsutar`); set secrets: `GROQ_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `ALLOWED_ORIGINS` (the Vercel URL).
   - Push via `huggingface_hub` or git remote. Document the exact steps in `DEPLOYMENT.md`.
7.4 **Frontend → Vercel** (free hobby tier): root dir `frontend/`, build `npm run build`, output `dist/`, env `VITE_API_URL=https://<space>.hf.space`. Document in `DEPLOYMENT.md`.
7.5 End-to-end test on the live URLs: ingest a paper, query, graph explorer. Add the live demo link to the README.
7.6 Note in `DEPLOYMENT.md`: HF free Spaces sleep after ~48h inactivity (cold start ~1 min); AuraDB free pauses after 3 days idle (resume from console). Acceptable for a resume demo.

Final commit.

---

## Acceptance criteria (whole plan)
- Local: fresh clone + `.env` with only `GROQ_API_KEY` + `NEO4J_PASSWORD` → `docker compose up -d --build` → working app on `localhost:3000`, CPU-only, no GPU config anywhere.
- Cloud: live Vercel URL talking to HF Space talking to Qdrant Cloud + AuraDB Free. $0/month.
- No Cohere, no Ollama, no torch, no faster-whisper in the dependency tree.
- Graph explorer shows Paper/Author/Concept nodes with WROTE/HAS_CONCEPT/CITES edges.
- Injection attempts rejected; oversized/wrong-type uploads rejected with 4xx; no hardcoded secrets or hosts.
- CI green; README accurate with live demo link.

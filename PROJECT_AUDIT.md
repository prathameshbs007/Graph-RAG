# ResearchOS — Project Audit & Roadmap

Full review of backend, frontend, Docker setup, and docs. Three sections: inconsistencies found, improvements to make it resume-solid, and deployment/production paths.

---

## 1. Inconsistencies Found

### Documentation vs. reality (fix these first — interviewers read the README)

| # | Claim in docs | Reality in code |
|---|---|---|
| 1 | `README.md` says **GPT-4o** generates answers | Groq `llama-3.3-70b-versatile` (`config.py`) |
| 2 | `README_final.md` says **llama3-8b** | Config says `llama-3.3-70b-versatile` — three different LLM claims across two READMEs |
| 3 | `README.md` says **React 18** | `package.json` has React **19** |
| 4 | `README_final.md`: `docker-compose --profile all up` | No profiles exist in `docker-compose.yml` — this command misleads anyone cloning the repo |
| 5 | `README_final.md` lists containers `rag-ollama`, `rag-backend`, etc. | No `container_name` set anywhere; actual names differ |
| 6 | `README_final.md`: frontend runs "Vite Hot-Module Loader" | Frontend Dockerfile is a production nginx build |
| 7 | README: "512 **tok** chunks" | `chunk_text()` splits on **words**, not tokens |
| 8 | Two READMEs coexist (`README.md` = 865-line build plan, `README_final.md` = feature blurb) | Confusing entry point. Keep one polished README |
| 9 | "Graph traversal — **citation links, concept co-occurrence**" | `CITES` and `HAS_CONCEPT` edges are queried (`neo4j_client.py`) but **never created** anywhere. The graph only ever contains `(Author)-[:WROTE]->(Paper)`. `graph_context` is always empty. **This is the biggest gap: the "Graph RAG" claim is currently unsupported by the pipeline.** |

### Config inconsistencies

10. `config.py` defaults (`COHERE_TOP_N=10`, `RETRIEVAL_TOP_K=20`) disagree with `.env.example` (`5`, `10`). Pick one source of truth.
11. `QueryRequest` accepts `top_k`, `rerank_top_n`, `image_base64` — the query router **ignores all three** and uses global settings. Dead API surface; frontend sends values that do nothing.
12. Neo4j password `researchos123` hardcoded in `docker-compose.yml`, `config.py` defaults, healthcheck, and README. Move to `.env` and reference via `${NEO4J_PASSWORD}`.
13. `docker-compose.yml` `version: "3.9"` is obsolete (Compose v2 ignores/warns).

### Frontend inconsistencies

14. `http://localhost:8054` hardcoded in **4 files** (`useQuery.ts`, `UploadPanel.tsx`, `GraphExplorer.tsx`, `FigureCitation.tsx`). Breaks on any non-local deployment. Fix: `VITE_API_URL` env var, or better — add `location /api { proxy_pass http://backend:8000; }` to `nginx.conf` and use relative URLs (also eliminates the CORS problem entirely).
15. Mixed HTTP clients: `axios` in some components, `fetch` in `UploadPanel`. Pick one; a tiny `api.ts` client module is cleaner.
16. `any` types everywhere (`data: any`, `figure: any`, `source: any`) in a TypeScript project — define interfaces mirroring the Pydantic models.
17. Progress bar is fake (hardcoded 10→40→80). Either use real upload progress (axios `onUploadProgress`) or use an indeterminate spinner.
18. `SourceChip` shows audio chunks but the search never returns `start_time`/`end_time` (missing from `fields_map` in `weaviate_client.py`), so timestamps can never be displayed.

### Backend logic issues

19. **Cypher injection**: `routers/graph.py` interpolates `node_type`, `edge_type`, `limit` into query strings via f-strings. Validate against a whitelist of labels and parameterize `limit`.
20. **Score mixing across embedding spaces**: `search_all_classes` sorts nomic (768-d) certainties and CLIP (512-d) certainties in one list. These are not comparable — cross-modality ranking is essentially arbitrary. Either normalize per-class or keep modalities ranked separately.
21. `chunk_id = "chunk_" + str(hash(chunk_text))` — Python `hash()` is salted per process; IDs change every restart. Use the Weaviate object UUID (`_additional { id }`).
22. Uploaded files written to `/tmp` and **never deleted**; audio path embeds the raw client filename (`/tmp/{id}_{file.filename}`) — path-traversal risk. Sanitize the filename and clean up in a `finally`.
23. No upload validation: no file-size cap, no MIME/type check — a 2 GB non-PDF goes straight to PyMuPDF.
24. Errors return HTTP **200** with `status: "error: ..."` — use `HTTPException` with proper 4xx/5xx codes.
25. `year` silently defaults to **2024** when omitted — fabricates metadata. Use `None`.
26. `print()` used for all logging; broad `except Exception` swallows failures silently (e.g., embedding failure inserts chunks with **empty vectors**, poisoning the index). Use the `logging` module and fail loudly on empty embeddings.
27. `@app.on_event("startup")` is deprecated → use FastAPI `lifespan`.
28. `weaviate-client<4.0.0` pins the legacy v3 API (deprecated). Migrating to v4 is a good modernization story.
29. CORS: `allow_origins=["*"]` **with** `allow_credentials=True` — invalid per spec and insecure. The nginx proxy fix (#14) makes CORS unnecessary.
30. `requirements.txt` mostly unpinned — builds aren't reproducible. Pin versions (`pip freeze` or use `uv`/`pip-tools`).
31. Ingestion is fully synchronous — a large PDF blocks the request (CLIP + OCR per image is slow). Move to `BackgroundTasks` + a status-polling endpoint, or a task queue.
32. Import in the middle of `routers/ingest.py` (line ~90); an ad-hoc `test_weaviate.py` script instead of real tests; `clear_db.py` wipes with no confirmation flag.
33. Blocking work (`requests.post`, CLIP, Whisper) inside `async def` endpoints blocks the event loop — either make handlers `def` (FastAPI threads them) or use async clients.

### Repo hygiene

34. **All changes are uncommitted** — `git status` shows the entire backend modified since the last commit. Commit your work.
35. `.gitignore` contains `*.txt` and `*.pdf` — that pattern would ignore any future `requirements.txt`-style files and is why `backend_logs_*.txt` clutter exists locally. Ignore `logs/` specifically instead, and delete the 13 `backend_logs_*.txt`, `ollama_logs_3.txt`, and the stray arXiv PDF from the project root.
36. `INTERVIEW_PREP.md` sits in the repo root — don't ship that to a public resume repo.
37. Backend has no `.dockerignore` (frontend has one) — the image copies logs/test scripts in.
38. No `LICENSE`, no CI, no tests, no architecture diagram image. For a resume repo: MIT license, GitHub Actions running lint + tests, one clean README with a screenshot/GIF of the UI.

---

## 2. Improvements That Make It Resume-Solid

Ranked by interview impact:

1. **Actually build the graph part of Graph RAG** (fixes #9). Add a concept-extraction step at ingest (LLM call to Groq extracting concepts + cited titles → `HAS_CONCEPT`, `CITES` edges). Then graph traversal genuinely enriches retrieval and the headline claim is true. This is the single highest-value change.
2. **Add a retrieval evaluation harness** (e.g., RAGAS or a small custom eval: faithfulness, answer relevance, recall@k on a labeled set). "I measured my RAG pipeline and improved recall@10 from X to Y by adding reranking" is a standout interview line; almost no candidate projects have evals.
3. **Tests + CI**: pytest for chunking/retrieval logic (mock Weaviate/Neo4j), a couple of FastAPI `TestClient` integration tests, GitHub Actions workflow. Signals engineering maturity.
4. **Async ingestion with job status** (#31) — shows you understand real API design.
5. **Hybrid search**: Weaviate supports BM25 + vector hybrid; one-line change, meaningful retrieval-quality talking point.
6. **Streaming answers** (SSE from Groq → frontend) — big perceived-quality UI win.
7. **Structured logging + `/metrics`** (Prometheus) or request tracing — cheap, production-flavored.
8. **One polished README**: merge the two, correct the stack table, add architecture diagram image, demo GIF, quickstart that actually works, and an "Evaluation results" section.

---

## 3. Deployment & Production-Readiness

The constraint: Ollama + CLIP + Whisper want compute, and you have 4 stateful services. Two sensible paths:

### Path A — Managed services (recommended: free, gives you a live demo URL)

Swap self-hosted infra for free managed tiers so the backend becomes a small stateless container:

| Component | Replace with | Cost |
|---|---|---|
| Weaviate (Docker) | **Weaviate Cloud** sandbox | Free (14-day sandbox) or ~$25/mo; alternative: Qdrant Cloud free 1 GB |
| Neo4j (Docker) | **Neo4j AuraDB Free** | Free forever tier |
| Ollama embeddings | **Cohere embed** or **Jina embeddings API** | Free tier (you already use Cohere for rerank) |
| Whisper local | **Groq Whisper API** | Free tier (you already use Groq) |
| CLIP local | Keep in container (small on CPU) or Jina CLIP API | Free |
| Backend | **Render / Railway / Fly.io** container | Free–$5/mo |
| Frontend | **Vercel / Netlify / Cloudflare Pages** | Free |

Result: a public URL on your resume that recruiters can click. That matters more than the self-hosted purity.

### Path B — Single VPS with Docker Compose (keeps "fully local" story)

- Rent a VPS (Hetzner CX32 ~€7/mo handles CPU-only Ollama with `nomic-embed-text`; GPU not required for embeddings).
- Add **Caddy or Traefik** in front for automatic HTTPS + reverse proxy (`/` → frontend, `/api` → backend). Stop publishing Weaviate/Neo4j/Ollama ports publicly — internal Docker network only.
- Make the GPU reservation optional via a `docker-compose.gpu.yml` override so the stack runs on machines without NVIDIA runtime (right now `docker compose up` fails without one).
- `restart: unless-stopped` on all services; add a backend healthcheck; volume backups for Neo4j/Weaviate.

### Either way — production hardening checklist

- **Secrets**: `${VAR}` interpolation in compose from `.env`; never hardcode the Neo4j password; rotate the Groq/Cohere keys currently sitting in your local `.env` if that file was ever pushed.
- **Auth**: even a simple `X-API-Key` header dependency in FastAPI — an open ingest endpoint on the public internet will get abused.
- **Rate limiting**: `slowapi` on `/query` and `/ingest`.
- **Upload limits**: max file size (e.g., 50 MB), MIME whitelist.
- **Fix Cypher injection (#19) and CORS (#29) before exposing publicly.**
- **CI/CD**: GitHub Actions → build images → push to GHCR → deploy (Render auto-deploy or SSH + `docker compose pull && up -d`).
- **Containers**: pin base images, run as non-root user, add backend `.dockerignore`, pin Python deps.
- **Observability**: structured JSON logs, `/health` checks per dependency (Weaviate, Neo4j, Ollama reachability — not just `{"status": "healthy"}`).

### Suggested order of work

1. Repo cleanup + one README + commit everything (half a day)
2. Security fixes: Cypher injection, CORS/nginx proxy, secrets, upload validation (1 day)
3. Concept/citation extraction → real Graph RAG (1–2 days)
4. Tests + CI (1 day)
5. Deploy via Path A for a live demo URL (1 day)
6. Eval harness + README results section (1–2 days)

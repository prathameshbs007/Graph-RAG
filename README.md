# ResearchOS: a Multi-Modal Graph RAG platform with self-pruning agentic memory

Ingests research papers (PDF, with figures), and talk recordings (audio); answers questions with
cited evidence (page, figure crop, or audio timestamp); and **learns from the reranker which graph
edges lead to noise and prunes them**. This repository implements the design in the
*Phase 3 Report: Design, Methodology and Implementation*.

```
                ┌────────────── Module 1: ingestion ───────────────┐
 PDF / audio ──▶│ parse · chunk · figures · Whisper · embed ·      │──▶ Weaviate  (text, figure, transcript vectors + BM25)
                │ concepts & relations (Llama-3) · citations       │──▶ Neo4j     (Paper, Chunk, Figure, Concept; edges weighted 0.5)
                └───────────────────────────────────────────────────┘
 query ─▶ BM25 + dense (top 20 each) ─▶ fuse (α or RRF) ─▶ top-10 seeds ─▶ 2-hop weighted graph walk     Module 2
       ─▶ Cohere rerank (every candidate scored) ─▶ keep s ≥ 0.3, top 5                                  Module 3
       ─▶ grounded answer [E1][E2] ─▶ claim verification ─▶ page / figure / timestamp citations           Module 4
       ─▶ feedback: w ← 0.9w + 0.1s, prune (w < 0.2 after 5 visits), α ← α + 0.05(S_dense − S_bm25)      Module 3
 Ragas evaluation, 5 baselines, 4 ablations                                                                Module 5
```

## Quick start

```bash
cp .env.example .env          # add GROQ_API_KEY and COHERE_API_KEY
docker compose up -d --build  # frontend :3000, API :8054, Weaviate :8080, Neo4j :7474/:7687, Ollama :11434
```

Open http://localhost:3000, use **Ingest** to upload PDFs (title/authors/year are optional; they are read from the
PDF when omitted) and recordings, then **Search**. The **Graph** tab shows learned edge weights (thick/green = trusted,
red = weak, dashed grey = pruned) and **Memory** shows α, edge statistics, and the audit log of every weight change.

* **Upgrading from the earlier version?** The storage layout changed (one `Chunk` collection, weighted graph).
  Click *Clear DB* (or `POST /admin/clear-db`) and re-ingest; the API logs a warning if it sees the old classes.
* **Neo4j says "already running (pid …)"?** A stale pid file from an unclean shutdown:
  `docker compose up -d --force-recreate neo4j` (keeps your data volume).
* **Local Llama-3.1-8B instead of Groq:** `docker compose exec ollama ollama pull llama3.1:8b`, then `LLM_PROVIDER=ollama`.

## How each module is implemented

| Module | Code | Highlights |
|---|---|---|
| 1 Ingestion | `services/pdf_extractor.py`, `chunking.py`, `ingestion.py`, `concept_extractor.py`, `citations.py`, `audio_transcriber.py`, `figure_describer.py` | ~300-token chunks, 15% overlap, within page and section. Headings, tables (row-wise chunks with header), figures cropped **with caption** and stored with page + bounding box. References parsed; `CITES` edges from title matches (order independent). Concepts and relations from Llama-3 as JSON, normalised and merged. Whisper segments merged into ~30 s windows with timestamps. Runs as a background job (`GET /ingest/status/{id}`) and rolls back on failure. |
| 2 Retrieval | `services/weaviate_client.py`, `fusion.py`, `neo4j_client.py`, `pipeline.py` | One Weaviate collection, native BM25 and dense search returned as separate ranked lists. α-weighted or RRF fusion. Top-10 seeds, 2-hop Cypher walk over edges ≥ 0.3 plus a 5% chance of exploring a weak edge; pruned edges are never followed. Candidates carry provenance (which retriever, which path). |
| 3 Feedback | `services/reranker.py`, `feedback.py` | The reranker returns a score for **every** candidate. Edge update, soft pruning (restorable), α update, and a full audit log. One visit per edge per query. A freeze switch (`learn=false`, `FEEDBACK_ENABLED`) stops learning. |
| 4 Generation | `services/generator.py`, `llm.py` | Numbered evidence, temperature 0, "insufficient evidence" when unsupported. Claims are split and checked against their cited evidence; unsupported ones are flagged (`VERIFY_MODE=flag`) or removed (`remove`). Supported/unsupported counts are returned. |
| 5 Evaluation | `backend/eval/` | See [`backend/eval/README.md`](backend/eval/README.md). |

### Parameters (Section 4.2), all overridable in `.env`
chunk 300 tokens / 15% · 20 results per retriever · 10 seeds · 2 hops · RRF k = 60 · edge start 0.5 ·
follow ≥ 0.3 · update rate 0.1 · explore 5% · prune < 0.2 after 5 visits · relevance cutoff 0.3 · context 5 ·
α start 0.5, rate 0.05, range 0.2 to 0.9.

## API

| Endpoint | Purpose |
|---|---|
| `POST /ingest/pdf`, `POST /ingest/audio` | Upload; returns immediately, work runs in the background |
| `GET /ingest/status/{id}`, `GET /ingest/jobs` | Progress, stage, warnings, final counts |
| `POST /query` `{text, system?, learn?, seed?, verify?}` | Answer with evidence IDs, figures, claims, `diagnostics` (α, hit counts, graph reached, feedback applied, timings) |
| `GET /query/systems` | `full` and the baselines / ablations B1-B5, `abl_*` |
| `GET /graph` | Nodes + links with `weight`, `visits`, `pruned` |
| `GET /admin/state`, `/admin/audit`, `POST /admin/reset-feedback`, `/admin/restore-pruned`, `GET/POST /admin/snapshot` | Inspect, reset, restore, freeze and restore the memory |
| `POST /admin/clear-db` | Wipe everything |

Interactive docs at http://localhost:8054/docs.

## Tests

```bash
cd backend && pip install -r requirements.txt pytest httpx numpy scipy
python -m pytest -q                      # unit tests; the database tests are skipped
```
The integration tests (live Weaviate + Neo4j, fake embedder / LLM / reranker, so no API keys) **wipe the databases
they connect to**, so they only run with `RESEARCHOS_ALLOW_WIPE=1` and refuse the compose hostnames:
```bash
docker run -d --name rtest-weaviate -p 18080:8080 -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate -e DEFAULT_VECTORIZER_MODULE=none semitechnologies/weaviate:1.24.1
docker run -d --name rtest-neo4j -p 17687:7687 -e NEO4J_AUTH=neo4j/researchos123 neo4j:5.15-community
RESEARCHOS_ALLOW_WIPE=1 WEAVIATE_URL=http://localhost:18080 NEO4J_URI=bolt://localhost:17687 python -m pytest -q
```

## Where this differs from the report (and why)

| Report | This implementation | Reason |
|---|---|---|
| Llama-3.1-8B local | Groq Llama-3.3-70B by default; `LLM_PROVIDER=ollama` switches to the local 8B | no GPU assumed |
| BGE-base embeddings | `nomic-embed-text` (768-d) through Ollama | already in the stack; configurable with prefixes |
| Whisper small/medium | `base` | CPU; `WHISPER_MODEL` |
| Figure descriptions by a VLM | Optional (`VLM_PROVIDER`/`VLM_MODEL`); by default figures are indexed by caption + the text inside the figure (OCR for raster images) | a 7B VLM is slow on CPU |
| Streamlit UI | React UI | already built |
| Weaviate ≥ 1.28, Neo4j 5.26 | 1.24.1 / 5.15 in compose (tested) | unchanged compose images |
| "tokens" | whitespace words × 1.33 | no tokenizer dependency |
| Edge update "for each edge on the path to a candidate" | One update **per edge per query** using the *mean* score of the candidates it led to | otherwise a single query can reach the 5-visit pruning threshold |
| α from "top results found only by BM25 / only by dense" | Taken over the 10 fused seeds, absent side counts as 0 | needs enough items per query |
| Graph hops over Concept/Paper nodes | A reached concept or cited paper is resolved to its strongest chunk(s) so the pool only holds readable items | rerank needs text |
| CLIP image vectors (earlier prototype) | Removed; figures share the text embedding space | one hybrid index for every modality |

## Limitations
* Real Ollama embeddings, Groq, Cohere and Whisper were **not** exercised in automated tests (they use deterministic
  stand-ins); the Ragas judge has not been run. See `backend/eval/README.md`.
* PDF parsing is heuristic (typeset papers). It was checked on five arXiv papers with different layouts (25 of 25 figure
  captions matched to their figure); scanned PDFs need Tesseract (installed in the image).
* Figures that have no caption are not indexed.

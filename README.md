# ResearchOS

### Multi-Modal Graph RAG Platform with Split-Query HyDE & Self-Pruning Agentic Memory

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Vite_%2B_Tailwind_v4-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Weaviate](https://img.shields.io/badge/Weaviate-Hybrid_Vector_%2B_BM25-FA0050?style=for-the-badge)
![Neo4j](https://img.shields.io/badge/Neo4j-Weighted_Knowledge_Graph-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)
![Cohere](https://img.shields.io/badge/Cohere-Rerank_v3.5-39594D?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Compose_Stack-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## Overview

**ResearchOS** is an end-to-end, multi-modal Graph Retrieval-Augmented Generation (Graph RAG) platform engineered for dense scientific and technical literature. It ingests heterogeneous research artifacts—typeset PDFs (text, markdown tables, and cropped figures with dark-background-aware OCR) alongside audio recordings (Whisper timestamped transcripts)—into a unified hybrid vector store (**Weaviate**) and a weighted concept-citation graph (**Neo4j**).

Unlike static RAG pipelines that suffer from query-document semantic mismatch and accumulate noisy graph edges over time, ResearchOS introduces two core architectural innovations:

1. **Split-Query HyDE Pre-Retrieval Augmentation**: Bridges the geometric gap between short interrogative user queries and declarative academic prose. ResearchOS preserves the **raw user query for BM25 lexical search** (protecting exact identifiers like `IfcSpace` or error codes) while generating a **Hypothetical Document Embedding (HyDE)** exclusively for the dense vector leg.
2. **Self-Pruning Agentic Graph Memory**: Uses cross-encoder relevance scores from **Cohere Rerank v3.5** as an online reinforcement signal. Graph edges that consistently route traversal toward high-scoring evidence are strengthened, while noisy edges decay and are automatically soft-pruned—paired with an adaptive fusion controller that dynamically tunes $\alpha$ between lexical and semantic search.

---

## Core Capabilities

* **Unified Multi-Modal Ingestion**: Parses PDFs via `PyMuPDF` into $\sim 300$-token overlapping chunks, preserves table headers across row splits, crops figures with automatic same-page section attribution and dark-background inversion OCR ($2\times$ upscaled Tesseract or optional VLM), and transcribes talk audio into $30\text{ s}$ timestamped windows via `faster-whisper`.
* **Live, Teacher-Proof HyDE Observability**: Toggle `HyDE: ON / OFF` per query directly from the UI Omnibar. Inspect the live split-query execution trace side-by-side—viewing the raw BM25 query, the freshly hallucinated technical passage, LLM provider/model telemetry, wall-clock latency, and the $768$-dimensional `nomic-embed-text` vector preview (`vec[:5]`).
* **Weighted 2-Hop Graph Expansion with $\epsilon$-Exploration**: Seeds Neo4j with top-ranked hybrid hits and traverses `MENTIONS`, `CITES`, and `RELATED_TO` synapses where weight $w_e \ge 0.2$, retaining a $5\%$ stochastic exploration probability for weaker edges while skipping pruned paths.
* **Autonomous Synapse Pruning & $\alpha$-Adaptation**: Updates traversed edge weights once per query via an exponential moving average ($w_e \leftarrow 0.9 w_e + 0.1 s$), soft-prunes synapses falling below $0.28$ after $\ge 5$ visits, and shifts the hybrid fusion parameter $\alpha \in [0.2, 0.9]$ toward the stronger retriever.
* **Strictly Grounded Generation & NLI Audit Chain**: Generates answers at $\text{temperature} = 0$ with mandatory inline evidence citations (`[E1]`, `[E2]`) mapped to exact PDF bounding-box crops or audio timestamps, followed by a claim-level Natural Language Inference (NLI) verification pass.

---

## System Architecture

### 1. End-to-End Multi-Modal Graph RAG & Self-Pruning Pipeline

```mermaid
flowchart TB
    %% Styling Definitions
    classDef input fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#f8fafc
    classDef ingest fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    classDef store fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#e0e7ff
    classDef hyde fill:#2e1065,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    classDef retrieve fill:#042f2e,stroke:#2dd4bf,stroke-width:2px,color:#ccfbf1
    classDef feedback fill:#451a03,stroke:#fb923c,stroke-width:2px,color:#ffedd5
    classDef generate fill:#052e16,stroke:#4ade80,stroke-width:2px,color:#dcfce7

    %% Inputs
    subgraph INPUTS ["Input Artifacts & User Query"]
        direction LR
        PDF["Research PDFs<br/>(Text, Tables, Figures)"]:::input
        AUD["Lecture / Talk Audio<br/>(WAV / MP3)"]:::input
        UQ(["User Query + HyDE Toggle"]):::input
    end

    %% Module 1: Ingestion
    subgraph M1 ["Module 1: Multi-Modal Ingestion Pipeline (Offline)"]
        direction TB
        PARSE["PyMuPDF Parser<br/>~300-tok Chunks (15% overlap)<br/>Row-wise Markdown Tables"]:::ingest
        FIG["Figure Extractor<br/>Same-Page Section Attribution<br/>Dark-BG Inversion + 2x OCR / VLM"]:::ingest
        ASR["Faster-Whisper ASR<br/>30s Timestamped Windows"]:::ingest
        EMB_ING["nomic-embed-text (768-dim)<br/>Prefix: 'search_document:'"]:::ingest
        KG_EXT["LLM Concept & Relation JSON<br/>+ Title-Matched CITES Edges"]:::ingest
    end

    %% Knowledge Stores
    subgraph STORES ["Dual Knowledge Stores"]
        direction LR
        WEAV[("Weaviate Unified 'Chunk' Index<br/>HNSW Dense Vectors + BM25 Index")]:::store
        NEO[("Neo4j Knowledge Graph<br/>Paper, Chunk, Figure, Concept<br/>Weighted Synapses (init w = 0.5)")]:::store
    end

    %% Module 2: Split-Query HyDE
    subgraph M2 ["Module 2: Split-Query HyDE Pre-Retrieval (Online)"]
        direction TB
        BM25_LEG["Lexical Leg<br/>Raw Unmodified Query<br/>(Preserves Exact Keywords)"]:::hyde
        HYDE_DEC{"HyDE Enabled?"}:::hyde
        HYDE_GEN["LLM Hypothetical Passage<br/>(T = 0.7, max_tokens = 256)<br/>Ollama-First -> Groq Fallback"]:::hyde
        EMB_HYDE["Embed Hypothetical Passage<br/>Prefix: 'search_document:' (768-d)"]:::hyde
        EMB_RAW["Embed Raw Query<br/>Prefix: 'search_query:' (768-d)"]:::hyde
    end

    %% Module 3: Hybrid & Graph Retrieval
    subgraph M3 ["Module 3: Hybrid Retrieval & Weighted Graph Traversal"]
        direction TB
        BM25_SEARCH["Weaviate BM25 Search<br/>(Top 20 Keyword Hits)"]:::retrieve
        DENSE_SEARCH["Weaviate Dense Search<br/>(Top 20 Semantic Hits)"]:::retrieve
        FUSION["Adaptive alpha-Weighted<br/>or RRF Fusion (k = 60)<br/>Select Top-10 Seed Nodes"]:::retrieve
        WALK["2-Hop Weighted Neo4j Walk<br/>Follow w >= 0.2 (5% Exploration)<br/>Skip Soft-Pruned Synapses"]:::retrieve
        POOL["Candidate Evidence Pool<br/>(<= 50 Chunks, Figures, Transcripts<br/>with Full Path Provenance)"]:::retrieve
    end

    %% Module 4: Reranking & Self-Pruning Memory
    subgraph M4 ["Module 4: Cross-Encoder Reranking & Self-Pruning Agentic Memory"]
        direction TB
        RERANK["Cohere Rerank v3.5<br/>Cross-Encoder Scoring (s in [0, 1])<br/>Filter s >= 0.3 -> Top-5 Context"]:::feedback
        EDGE_UPD["Synapse Weight Update (1/query)<br/>w <- 0.9w + 0.1s | visits += 1<br/>Soft-Prune: w < 0.28 at visits >= 5"]:::feedback
        ALPHA_UPD["Adaptive Retriever Tuner<br/>alpha <- clip(alpha + 0.05(S_dense - S_bm25), 0.2, 0.9)"]:::feedback
    end

    %% Module 5: Generation & Audit
    subgraph M5 ["Module 5: Grounded Generation, NLI Audit & UI Telemetry"]
        direction TB
        GEN["Strict Evidence Generator (T = 0)<br/>Inline Citations [E1][E2] or Refusal"]:::generate
        NLI["Claim-Level NLI Verification<br/>Entailment Check vs. Cited Chunks"]:::generate
        OUT(["Final Cited Response<br/>Figure Bounding-Box Crops | Audio Timestamps<br/>Live HyDE Inspector Drawer | Audit Chain"]):::generate
    end

    %% Ingestion Connections
    PDF --> PARSE & FIG
    AUD --> ASR
    PARSE & FIG & ASR --> EMB_ING
    PARSE & FIG & ASR --> KG_EXT
    EMB_ING --> WEAV
    KG_EXT --> NEO

    %% Query & HyDE Connections
    UQ --> BM25_LEG
    UQ --> HYDE_DEC
    HYDE_DEC -- "ON (Default)" --> HYDE_GEN --> EMB_HYDE
    HYDE_DEC -- "OFF (Ablation)" --> EMB_RAW

    %% Retrieval Connections
    WEAV --> BM25_SEARCH & DENSE_SEARCH
    BM25_LEG --> BM25_SEARCH
    EMB_HYDE & EMB_RAW --> DENSE_SEARCH
    BM25_SEARCH & DENSE_SEARCH --> FUSION
    FUSION --> WALK
    NEO <--> WALK
    WALK --> POOL

    %% Reranking & Feedback Loop Connections
    POOL --> RERANK
    RERANK --> GEN
    RERANK -. "Reranker Score (s)" .-> EDGE_UPD
    RERANK -. "Unique Retriever Scores" .-> ALPHA_UPD
    EDGE_UPD -. "Update Weights & Prune Flags" .-> NEO
    ALPHA_UPD -. "Update Live alpha" .-> FUSION

    %% Generation Connections
    GEN --> NLI --> OUT
    HYDE_GEN -. "Live Telemetry (Passage, vec[:5], ms)" .-> OUT
```

### 2. Split-Query HyDE & Self-Pruning Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React UI (Omnibar)
    participant API as FastAPI Pipeline
    participant LLM as Ollama / Groq LLM
    participant WV as Weaviate (BM25 + HNSW)
    participant NEO as Neo4j Graph
    participant CO as Cohere Rerank v3.5

    User->>UI: Submit query q (HyDE = ON)
    UI->>API: POST /query {text: q, hyde: true}
    
    par Split-Query Pre-Retrieval
        API->>LLM: Generate hypothetical textbook passage d_hat (T = 0.7)
        LLM-->>API: Hypothetical passage d_hat
        API->>API: Embed("search_document: " + d_hat) -> v_hyde (768-dim)
        API->>WV: Dense HNSW Search(v_hyde, top_k=20)
    and Exact Lexical Matching
        API->>WV: BM25 Keyword Search(raw query q, top_k=20)
    end
    
    WV-->>API: 20 Dense Hits + 20 BM25 Hits
    API->>API: Adaptive alpha / RRF Fusion -> Top-10 Seeds
    API->>NEO: 2-Hop Cypher Traversal (w >= 0.2, 5% explore, skip pruned)
    NEO-->>API: Candidate Pool (<= 50 items + edge provenance)
    
    API->>CO: Score (q, candidate_i) pairs
    CO-->>API: Relevance scores s_i in [0, 1]
    
    par Self-Pruning Feedback Loop
        API->>NEO: Update traversed edges: w <- 0.9w + 0.1s (Prune if w < 0.28 & visits >= 5)
        API->>API: Shift alpha toward higher-scoring retriever
    and Grounded Generation & NLI Audit
        API->>LLM: Generate cited answer from Top-5 (s >= 0.3, T = 0)
        LLM-->>API: Draft Answer with [E1]..[E5]
        API->>LLM: Verify claim-level NLI entailment
    end
    
    API-->>UI: Answer + Visual Crops + NLI Audit + diagnostics.hyde
```

---

### Mathematical Formulation

1. **Split-Query HyDE & Hybrid Fusion**:
   Given a raw user query $q$, BM25 scores lexical overlap directly on $q$, while the dense retriever embeds a hypothetical technical passage $\hat{d} = \text{LLM}_{T=0.7}(q)$ prefixed with `search_document:`:
   
   $$
   \mathbf{v}_{\text{dense}} = \begin{cases} \text{Embed}(\texttt{"search\_document: "} \Vert \hat{d}) & \text{if HyDE is ON} \\ \text{Embed}(\texttt{"search\_query: "} \Vert q) & \text{if HyDE is OFF} \end{cases}
   $$
   
   Ranked lists are combined via adaptive $\alpha$-fusion or Reciprocal Rank Fusion:
   
   $$
   \text{RRF}(d) = \sum_{i \in \{\text{bm25}, \text{dense}\}} \frac{1}{60 + \text{rank}_i(d)}
   $$

2. **Synapse Weight Update & Soft-Pruning Rule**:
   For each unique graph edge $e$ along the paths leading to reranked candidate chunks with mean Cohere cross-encoder relevance score $s \in [0, 1]$:
   
   $$
   w_e^{(t+1)} = (1 - \eta) w_e^{(t)} + \eta s, \quad \text{visits}_e^{(t+1)} = \text{visits}_e^{(t)} + 1 \quad (\eta = 0.1)
   $$
   
   An edge is flagged as soft-pruned (excluded from deterministic traversal, restorable via snapshot/admin API) when:
   
   $$
   \text{visits}_e \ge 5 \quad \land \quad w_e < 0.28
   $$

3. **Adaptive Retriever Weight ($\alpha$) Tuning**:
   Let $\bar{S}_{\text{dense}}$ and $\bar{S}_{\text{bm25}}$ denote the mean reranker scores of top candidates contributed uniquely by dense and BM25 search, respectively:
   
   $$
   \alpha^{(t+1)} = \text{clip}\Big(\alpha^{(t)} + 0.05 \cdot (\bar{S}_{\text{dense}} - \bar{S}_{\text{bm25}}),\; 0.2,\; 0.9\Big)
   $$

---

## Quick Start

### 1. Configure Environment

Clone the repository, copy the environment template, and populate your API keys (`GROQ_API_KEY` and `COHERE_API_KEY`):

```bash
cp .env.example .env
```

### 2. Launch the Full Stack

Bring up all 5 containerized services with Docker Compose:

```bash
docker compose up -d --build
```

| Service | Port / Endpoint | Role in ResearchOS |
| :--- | :--- | :--- |
| **React UI (`frontend`)** | `http://localhost:3000` | Interactive 4-workspace web application (Vite + Tailwind v4) |
| **FastAPI (`backend`)** | `http://localhost:8054` | Core RAG pipeline, background ingestion & Swagger docs (`/docs`) |
| **Weaviate** | `http://localhost:8080` | Unified `Chunk` hybrid HNSW vector index + BM25 inverted index |
| **Neo4j** | `http://localhost:7474` / `bolt://:7687` | Weighted knowledge graph of papers, chunks, figures & concepts |
| **Ollama** | `http://localhost:11434` | Local `nomic-embed-text` embeddings & optional `llama3.1:8b` LLM |

---

## Interactive Workspaces (`http://localhost:3000`)

1. **Search & QA**:
   * Query across PDFs, extracted figures, and audio transcripts.
   * **Live HyDE Toggle**: Switch `HyDE: ON / OFF` directly in the Omnibar or switch across evaluation baselines (`B1`–`B5`) and ablations (`abl_*`).
   * **HyDE Inspector Drawer**: Click `HyDE Active` on any response card to inspect the exact `bm25_query`, the generated `hypothetical_doc` (clearly badged as never used as answer evidence), active LLM provider/model, wall-clock latency, and $768$-dim vector preview (`vec[:5]`).
   * **NLI Audit Chain**: Expand `Audit Chain` to view sentence-by-sentence entailment verification against cited source IDs.
2. **Graph Explorer**:
   * Interactive force-directed Neo4j visualization color-coded by learned synapse health: thick green (trusted, high weight), red (weakening), and dashed grey (soft-pruned).
3. **Agentic Memory**:
   * Real-time telemetry dashboard tracking the live $\alpha$ balance, active vs. pruned synapse counts, and a chronological audit log of every edge weight update.
4. **Ingestion Studio**:
   * Drag-and-drop PDFs (auto-extracts title, authors, and publication year when omitted) and audio recordings with live background job polling.

---

## Module-by-Module Implementation

| Module | Backend Source Files | Key Engineering Highlights |
| :--- | :--- | :--- |
| **1. Multi-Modal Ingestion** | `services/pdf_extractor.py`<br/>`services/chunking.py`<br/>`services/ingestion.py`<br/>`services/concept_extractor.py`<br/>`services/citations.py`<br/>`services/audio_transcriber.py`<br/>`services/figure_describer.py` | $\sim 300$-token chunks with $15\%$ overlap within page and section boundaries. Markdown tables split row-wise preserving column headers. Figures cropped **with captions**, attributed to their same-page preceding section heading, and OCR'd with automatic dark-background inversion + $2\times$ upscaling (optional VLM via `VLM_PROVIDER`). References parsed into order-independent `CITES` edges. LLM concept/relation extraction capped at `max_tokens=600` for Groq OTPM compliance. Whisper audio merged into $\sim 30\text{ s}$ timestamped windows. Background jobs (`GET /ingest/status/{id}`) with transactional rollback on failure. |
| **2. HyDE Pre-Retrieval** | `services/hyde.py` | Intercepts the raw query on the dense retrieval leg only: generates a concise, technical hypothetical textbook passage (`HYDE_TEMPERATURE=0.7`, `HYDE_MAX_TOKENS=256`, Ollama-first with automatic Groq fallback) and embeds it using `EMBED_DOC_PREFIX` (`search_document:`) so it aligns geometrically with indexed passage vectors. BM25 always receives the exact raw user query. Returns full live trace telemetry (`HyDEResult`) for the UI inspector and supports per-query `hyde: true/false` toggling. |
| **3. Hybrid + Graph Retrieval** | `services/weaviate_client.py`<br/>`services/fusion.py`<br/>`services/neo4j_client.py`<br/>`services/pipeline.py` | Unified Weaviate `Chunk` collection returning separate BM25 and dense ranked lists. Adaptive $\alpha$-weighted or RRF fusion selects top-10 seeds, followed by a 2-hop weighted Neo4j Cypher walk over edges $w_e \ge 0.2$ plus $5\%$ exploration of weak edges; soft-pruned edges are skipped. Candidates carry full retriever and graph-path provenance. |
| **4. Reranker & Self-Pruning Memory** | `services/reranker.py`<br/>`services/feedback.py` | Cohere `rerank-v3.5` scores every candidate; items with $s \ge 0.3$ (top-5) enter context. Updates traversed edges ($w_e \leftarrow 0.9 w_e + 0.1 s$, once per edge per query), soft-prunes edges with $w_e < 0.28$ after $\ge 5$ visits (restorable), adapts $\alpha$, and records an audit log. Supports freeze switch (`learn=false`, `FEEDBACK_ENABLED=false`). |
| **5. Grounded Generation & NLI Audit** | `services/generator.py`<br/>`services/llm.py` | Numbered evidence context `[E1]...[Ek]` at $\text{temperature}=0$ with strict refusal (*"Insufficient evidence"*) when sources lack support. Splits claims and verifies entailment against cited chunks (`VERIFY_MODE=flag` or `remove`). |

---

## Configuration Parameters (`backend/config.py`)

All hyperparameters are configurable via `.env`:

| Category | Parameter | Default | Description |
| :--- | :--- | :--- | :--- |
| **Ingestion** | `CHUNK_SIZE` / `CHUNK_OVERLAP_RATIO` | `300` / `0.15` | Target token count and sliding window overlap |
| **Ingestion** | `CONCEPT_BATCH_SIZE` | `4` | Chunks batched per LLM concept extraction call |
| **Ingestion** | `EDGE_INIT_WEIGHT` | `0.5` | Neutral initial synapse weight in Neo4j |
| **HyDE** | `HYDE_ENABLED` | `true` | Default global state for HyDE pre-retrieval |
| **HyDE** | `HYDE_TEMPERATURE` / `HYDE_MAX_TOKENS` | `0.7` / `256` | Creativity and length cap for hypothetical passages |
| **Embeddings** | `EMBED_MODEL` | `nomic-embed-text` | $768$-dimensional embedding model served via Ollama |
| **Retrieval** | `RETRIEVAL_TOP_K` / `SEED_K` | `20` / `10` | Per-retriever hit count and fused graph seed count |
| **Graph Walk** | `GRAPH_FANOUT` / `CANDIDATE_POOL_MAX` | `20` / `50` | Maximum graph expansion fanout and total candidate pool cap |
| **Graph Walk** | `EDGE_TRAVERSE_MIN` / `EXPLORE_PROB` | `0.2` / `0.05` | Minimum deterministic edge weight and $\epsilon$-exploration rate |
| **Reranking** | `COHERE_RERANK_MODEL` | `rerank-v3.5` | Cross-encoder model providing relevance feedback $s \in [0, 1]$ |
| **Reranking** | `RELEVANCE_CUTOFF` / `CONTEXT_SIZE` | `0.3` / `5` | Minimum cross-encoder score and top-$k$ passages sent to generator |
| **Feedback** | `EDGE_LR` | `0.1` | Exponential moving average learning rate $\eta$ |
| **Feedback** | `PRUNE_MIN_VISITS` / `PRUNE_BELOW` | `5` / `0.28` | Visit count and weight threshold for soft-pruning synapses |
| **Feedback** | `ALPHA_INIT` / `ALPHA_RATE` | `0.5` / `0.05` | Initial hybrid balance and step size within $[0.2, 0.9]$ |

---

## REST API Reference

Interactive OpenAPI / Swagger documentation is available at **`http://localhost:8054/docs`**.

| Method & Endpoint | Request Payload / Params | Description |
| :--- | :--- | :--- |
| `POST /ingest/pdf`<br/>`POST /ingest/audio` | `multipart/form-data` | Upload PDF or audio recording; queued in background thread pool |
| `GET /ingest/status/{id}`<br/>`GET /ingest/jobs` | Path `id` | Poll live ingestion stage, elapsed seconds, warnings, and entity counts |
| `POST /query` | `{text, system?, learn?, seed?, verify?, hyde?}` | Execute RAG pipeline; returns answer, cited sources, figure crops, NLI claims, and `diagnostics` (including live `diagnostics.hyde` trace) |
| `GET /query/systems` | None | Lists `full` system alongside baselines (`B1`–`B5`) and ablations (`abl_*`) |
| `GET /graph` | Optional filters | Returns Neo4j nodes and weighted/pruned edges for Graph Explorer |
| `GET /admin/state`<br/>`GET /admin/audit` | None | Inspect live $\alpha$, synapse statistics, prune counts, and audit log |
| `POST /admin/reset-feedback`<br/>`POST /admin/restore-pruned`<br/>`GET/POST /admin/snapshot` | Snapshot JSON | Freeze, reset, restore soft-pruned edges, or snapshot agentic memory |
| `POST /admin/clear-db` | None | Purge all Weaviate vectors, Neo4j nodes/edges, and reset memory state |

---

## Testing & Verification Suite

### 1. Fast Unit Tests (Mocked External Providers)

Run the deterministic unit test suite (including dark-background PDF figure OCR and same-page section attribution tests):

```bash
cd backend && pip install -r requirements.txt pytest httpx numpy scipy
python -m pytest -q
```

### 2. Live Database Integration Tests

Live integration tests exercise Weaviate and Neo4j end-to-end using deterministic fake embedder/LLM/reranker fixtures (no external API keys consumed). Because they wipe their target databases, they require `RESEARCHOS_ALLOW_WIPE=1` against isolated container ports:

```bash
docker run -d --name rtest-weaviate -p 18080:8080 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
  -e DEFAULT_VECTORIZER_MODULE=none \
  semitechnologies/weaviate:1.24.1

docker run -d --name rtest-neo4j -p 17687:7687 \
  -e NEO4J_AUTH=neo4j/researchos123 \
  neo4j:5.15-community

RESEARCHOS_ALLOW_WIPE=1 WEAVIATE_URL=http://localhost:18080 NEO4J_URI=bolt://localhost:17687 python -m pytest -q
```

---

## Architectural Evolution & Design Justifications

| Initial Phase Report Design | Final Production Implementation | Engineering Justification |
| :--- | :--- | :--- |
| **Ragas Evaluation Harness (Module 5)** | **Deprecated & Removed**; replaced with **Split-Query HyDE + Live UI Inspector** | Ragas incurred prohibitive LLM-judge compute and rate-limit overhead; Split-Query HyDE directly boosts dense recall on academic prose while preserving exact BM25 keyword hits and real-time UI explainability. |
| **Llama-3.1-8B Local-Only** | **Hybrid Provider (`groq` / `ollama`)**; HyDE tries Ollama first with automatic Groq fallback | Enables smooth execution on laptops without dedicated GPUs while supporting $100\%$ local execution when Ollama chat models are pulled. |
| **BGE-base Embeddings** | **`nomic-embed-text` ($768$-dim)** via Ollama with `search_query:` / `search_document:` prefixes | Native to the containerized Ollama service; explicit task prefixes align generated HyDE passages with stored document chunks in vector space. |
| **Mandatory VLM Figure Descriptions** | **Dark-BG-Aware $2\times$ Tesseract OCR + Same-Page Section Heading** (VLM optional) | Zero extra VRAM/disk overhead and fast ingestion while accurately indexing white-on-charcoal architecture diagrams (e.g., Unity workflow flowcharts). |
| **Streamlit Prototype UI** | **React + Vite + Tailwind v4 SPA** (`Search & QA`, `Graph Explorer`, `Agentic Memory`, `Ingestion Studio`) | Enables interactive force-directed graph inspection, per-query `HyDE: ON/OFF` toggling, live vector preview drawers, and NLI claim auditing. |
| **Per-Path Edge Updates** | **Once-Per-Query Edge Update** using mean reranker score of reached candidates | Prevents a single multi-path query from incrementing an edge's visit counter multiple times and prematurely triggering the $5$-visit pruning rule. |

---

## Operational Runbook & Known Limitations

* **Resetting the Knowledge Base**: Click **Clear DB** in the top navigation bar (or call `POST /admin/clear-db`) to wipe Weaviate and Neo4j cleanly before re-ingesting papers.
* **Recovering Neo4j After Unclean Host Shutdown**: If Neo4j logs `"already running (pid ...)"`, recreate the container via `docker compose up -d --force-recreate neo4j`.
* **Running 100% Local Generation with Ollama**: Pull Llama 3.1 into the running Ollama container (`docker compose exec ollama ollama pull llama3.1:8b`) and set `LLM_PROVIDER=ollama` in `.env`.
* **Groq Free-Tier Pacing**: Concept extraction on large PDFs under Groq's free tier is paced by output-tokens-per-minute (OTPM) limits (`max_tokens=600` per batch); switching `LLM_PROVIDER=ollama` removes external rate limits on GPU-equipped workstations.
* **Heuristic Figure Detection**: PDF figure cropping targets captioned figures; decorative images without detectable captions are intentionally skipped to prevent index pollution.
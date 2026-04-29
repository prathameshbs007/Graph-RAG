# ResearchOS Graph RAG 🧠📊
A state-of-the-art Multi-Modal Graph RAG (Retrieval-Augmented Generation) system tailored exclusively for academic research. ResearchOS fuses the associative power of Knowledge Graphs (Neo4j) with the mathematically dense similarity matching of Vector Databases (Weaviate) to natively ingest, map, query, and chat with Research PDFs and Audio lectures.

## 🌟 End-to-End Functionality & Features

### 1. 📥 Multi-Modal Ingestion Pipeline
- **PDF Extraction**: When you upload a research paper, the system leverages PyMuPDF to cleanly sever the document into readable chunks of text while actively scraping and isolating raw mathematical and architectural diagrams directly from the PDF bytecode.
- **Audio Extraction**: If you attach an audio lecture, the Whispers speech-to-text transcriber locally translates the audio track into highly accurate timestamped textual segments natively linked back to the source paper.
- **GPU-Accelerated Embedding**:
    - **Text**: Textual data undergoes semantic compression into a dense 768-dimensional mathematical vector using the massive local NLP powers of `Ollama` (`nomic-embed-text`). Batched natively, processing time for a massive paper drops from 90 seconds to roughly 5 seconds.
    - **Vision**: Graphical architecture diagrams from the PDF are natively embedded via deep learning using OpenAI’s highly prized `CLIP (ViT-B/32)` model. 

### 2. 🗄️ Dual-Database Architecture
- **Knowledge Graph (Neo4j)**: 
   The platform weaves associative memories. When a paper enters the system, Neo4j builds explicit connections (`(Author)-[:WROTE]->(Paper)`) mapping human-readable entities.
- **Vector Search (Weaviate)**:
   Weaviate stores the raw embedding matrices across isolated structural collections (`TextChunk`, `FigureChunk`), bridging the gap between semantic distances flawlessly alongside standard inverted index metrics. 

### 3. 🔍 The Sub-Second Query Engine (RAG Pipeline)
When you query the interface (e.g. *"What is the architecture of BLIP-2?"*):
1. **Multi-Vector Dual Queries**: The system aggressively tokenizes your prompt concurrently using *two* models: It hits `Ollama` to understand your text context, and it simultaneously strikes the `CLIP` vision engine to understand what your query *visually looks like*.
2. **Semantic Retrieval**: Weaviate searches parallel planes for the chunks and images that contextually align with your vectors. By protecting independent retrieval structures, graphical charts easily break the threshold without getting overshadowed by high text thresholds.
3. **Graph Traversal Enrichment**: The pipeline taps Neo4j graph nodes and traverses outward from retrieved nodes to discover related authors, concepts, and citations implicitly connected to the core topic.
4. **Cohere Reranking**: Text structures run through a heavy Cohere semantic reranker to strip irrelevant text fragments.
5. **Groq Llama-3 Synthesis**: The finest chunks enter the blazingly fast Groq `llama3-8b` processor alongside strict citation guidelines. The LLM processes all text chunks natively and injects highly localized references cleanly back into the text UI.

### 4. 🎨 Modern Interface (Research OS Frontend)
- Built on **React, Vite, and Tailwind V4**, running on `localhost:3000`.
- **Query Engine**: Features the dynamic `AnswerCard` rendering robust contextual markdown from Groq while heavily displaying isolated interactive mathematical models via `Visual Evidence`.
- **Graph Explorer**: An intuitive orbital node layout visualizing the Neo4j backend in full React Force Graph UI to visualize what Papers are natively written by which specific Authors immediately post-upload.

---

## 🛠️ Infrastructure & Startup
To securely handle VRAM shuffling between LLMs and Transformers, the application is containerized within a heavily mapped `docker-compose` cluster consisting natively of:
1. `rag-ollama`
2. `rag-neo4j`
3. `rag-weaviate`
4. `rag-backend` (GPU Pass-Through Fastapi via Uvicorn)
5. `rag-frontend` (Vite Hot-Module Loader)

### Starting the Pipeline
```bash
docker-compose --profile all build
docker-compose --profile all up -d
```
*Note: Due to dynamic tensor loading, standard local instances will automatically cache all weights on the very first upload. Subsequent boots and requests are practically instantaneous!*

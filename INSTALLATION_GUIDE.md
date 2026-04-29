# 🚀 Graph RAG System - Installation & Startup Guide

## ✅ Status: All Dependencies Installed & Verified

### Installed Backend Packages (Python 3.13.2)
```
✅ cohere              5.21.1
✅ fastapi            0.136.1
✅ groq               1.2.0
✅ neo4j              6.1.0
✅ pydantic           2.13.3
✅ pydantic-settings  2.14.0
✅ weaviate-client    3.26.7
✅ pymupdf            (PyMuPDF)
✅ faster-whisper     (Audio transcription)
✅ open-clip-torch    (Image embeddings)
✅ torch              (PyTorch)
✅ torchvision        (Computer vision)
✅ Pillow             (Image processing)
✅ requests           (HTTP client)
✅ python-multipart   (File uploads)
✅ uvicorn            (ASGI server)
```

### Installed Frontend Packages (Node.js v22.2.0, npm 10.7.0)
```
✅ react              ^19.2.5
✅ react-dom          ^19.2.5
✅ react-force-graph-2d  ^1.29.1
✅ axios              ^1.15.2
✅ lucide-react       ^1.11.0
✅ vite               ^8.0.10
✅ typescript         ~6.0.2
✅ tailwindcss        ^4.2.4
✅ eslint             ^10.2.1
```

---

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows, macOS, or Linux
- **RAM**: 8GB (16GB+ recommended)
- **Storage**: 20GB free (for models and databases)
- **Python**: 3.11+ (currently using 3.13.2 ✅)
- **Node.js**: 16+ (currently using 22.2.0 ✅)
- **Docker**: 20.10+ (for containerized deployment)

### Optional but Recommended
- **GPU**: NVIDIA GPU with CUDA support (for faster embeddings)
- **NVIDIA Docker**: For GPU acceleration in Docker

---

## 🔑 API Keys Required

Before running the system, you need:

### 1. **Groq API Key** (Free Tier Available)
- URL: https://console.groq.com/keys
- Step 1: Sign up at https://groq.com
- Step 2: Navigate to API keys section
- Step 3: Create a new API key
- Step 4: Copy and save the key

### 2. **Cohere API Key** (Free Tier Available)
- URL: https://dashboard.cohere.com/api-keys
- Step 1: Sign up at https://cohere.com
- Step 2: Navigate to API keys section
- Step 3: Create a new API key
- Step 4: Copy and save the key

---

## ⚙️ Configuration

### 1. Update `.env` File
```bash
# Navigate to project root
cd d:\Study\Assignment\Graph-RAG-main

# Edit .env file (created from .env.example)
# Replace these values with your API keys:
GROQ_API_KEY=your_groq_api_key_here
COHERE_API_KEY=your_cohere_api_key_here
```

The `.env` file contains:
```env
# External API keys
GROQ_API_KEY=your_groq_api_key_here
COHERE_API_KEY=your_cohere_api_key_here

# Weaviate (vector database)
WEAVIATE_URL=http://weaviate:8080

# Neo4j (knowledge graph database)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=researchos123

# Ollama (embedding engine - local)
OLLAMA_URL=http://ollama:11434
EMBED_MODEL=nomic-embed-text

# Groq (LLM)
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=2048

# Cohere (Reranker)
COHERE_RERANK_MODEL=rerank-english-v3.0
COHERE_TOP_N=5

# CLIP (Vision model)
CLIP_MODEL=ViT-B/32

# Whisper (Audio transcription)
WHISPER_MODEL=base

# Retrieval settings
RETRIEVAL_TOP_K=10
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Backend
BACKEND_PORT=8000
FIGURES_DIR=/app/figures
```

---

## 🐳 Docker Deployment (Recommended)

### Prerequisites
1. **Install Docker Desktop**: https://www.docker.com/products/docker-desktop
2. **Verify Installation**:
   ```bash
   docker --version
   docker-compose --version
   ```

### Option 1: Full Docker Deployment (All Services)

#### Step 1: Build All Services
```bash
cd d:\Study\Assignment\Graph-RAG-main

# Build frontend, backend, and databases
docker-compose --profile all build
```

Expected output:
```
[+] Building 45.3s (15/15) FINISHED
  => [frontend] Building image frontend
  => [backend] Building image backend
  => Using cache layer for weaviate
  => Using cache layer for neo4j
  => Using cache layer for ollama
```

#### Step 2: Start All Services
```bash
# Start all containers in background
docker-compose --profile all up -d

# Or with logs visible:
docker-compose --profile all up
```

#### Step 3: Verify Services Are Running
```bash
docker-compose ps
```

Expected output:
```
NAME                    COMMAND                  STATUS             PORTS
rag-frontend           "nginx -g daemon off"    Up 2 minutes       0.0.0.0:3000->80/tcp
rag-backend            "uvicorn main:app"       Up 2 minutes       0.0.0.0:8054->8000/tcp
rag-weaviate           "/bin/weaviate"          Up 2 minutes       0.0.0.0:8080->8080/tcp
rag-neo4j              "/startup/docker-..."    Up 2 minutes       0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
rag-ollama             "/bin/sh -c 'ollama..."  Up 2 minutes       0.0.0.0:11434->11434/tcp
```

#### Step 4: Check Service Health
```bash
# Check backend logs
docker logs rag-backend

# Check Weaviate connection
curl http://localhost:8080/v1/.well-known/ready

# Check Neo4j connection
curl http://localhost:7474

# Check Ollama
curl http://localhost:11434/api/tags
```

---

## 🖥️ Local Development (Without Docker)

### Prerequisite: Start External Services with Docker

```bash
# Just start databases and Ollama (no frontend/backend containers)
docker-compose up -d weaviate neo4j ollama
```

### Backend Setup (Terminal 1)

```bash
cd d:\Study\Assignment\Graph-RAG-main\backend

# Run the FastAPI server
"C:/Program Files/Python313/python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Backend API**: http://localhost:8000
**API Docs**: http://localhost:8000/docs (Swagger UI)

### Frontend Setup (Terminal 2)

```bash
cd d:\Study\Assignment\Graph-RAG-main\frontend

# Run development server
npm run dev
```

Expected output:
```
  VITE v8.0.10  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help
```

**Frontend**: http://localhost:5173 (development)

---

## 🌐 Access Points

### After Deployment (Docker)

| Service | URL | Purpose | Credentials |
|---------|-----|---------|-------------|
| **Frontend** | http://localhost:3000 | React UI for queries | None |
| **Backend API** | http://localhost:8054/docs | Swagger API documentation | None |
| **Weaviate** | http://localhost:8080 | Vector database console | None |
| **Neo4j Browser** | http://localhost:7474 | Graph database UI | neo4j / researchos123 |
| **Ollama** | http://localhost:11434 | Embedding engine API | None |

---

## 🧪 Testing the System

### 1. Upload a Research Paper

**Via UI**:
1. Open http://localhost:3000
2. Click "Upload Paper" button
3. Select a PDF file
4. Wait for processing (2-5 minutes depending on file size)

**Via API**:
```bash
curl -X POST http://localhost:8054/api/ingest/pdf \
  -F "file=@sample_paper.pdf" \
  -F "title=Sample Paper" \
  -F "authors=John Doe"
```

### 2. Upload Audio Lecture

**Via UI**:
1. Open http://localhost:3000
2. Click "Upload Audio" button
3. Select an MP3 or WAV file
4. Associate with paper (optional)

**Via API**:
```bash
curl -X POST http://localhost:8054/api/ingest/audio \
  -F "file=@lecture.mp3" \
  -F "paper_id=paper_123"
```

### 3. Query the System

**Via UI**:
1. Go to query bar at top
2. Type a question: "What is the main contribution of this paper?"
3. Click search
4. View results with citations and figures

**Via API**:
```bash
curl -X POST http://localhost:8054/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main contribution?",
    "top_k": 5,
    "use_reranking": true
  }'
```

### 4. Explore Knowledge Graph

1. Open http://localhost:3000
2. Look for "Graph Explorer" component
3. Visualize paper relationships, authors, concepts
4. Click nodes to explore connections

---

## 🛠️ Troubleshooting

### Issue: "Connection refused" on port 8080 (Weaviate)

**Solution**:
```bash
# Check if Weaviate container is running
docker logs rag-weaviate

# Restart Weaviate
docker restart rag-weaviate

# Wait 30 seconds for health check to pass
sleep 30
docker-compose up -d backend
```

### Issue: "torch not installed" or CUDA errors

**Solution**:
```bash
# Reinstall PyTorch with CPU support
"C:/Program Files/Python313/python.exe" -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Issue: Frontend not connecting to backend

**Solution**:
1. Check backend is running: http://localhost:8000/docs
2. Check CORS in backend: `main.py` should have CORS middleware
3. Update frontend API URL if needed in environment

### Issue: "No module named 'ollama'" when running backend locally

**Solution**:
```bash
# Make sure you're in the backend directory
cd d:\Study\Assignment\Graph-RAG-main\backend

# The database services should still be running in Docker
docker-compose up -d weaviate neo4j ollama
```

### Issue: Models not downloading (Ollama, Whisper)

**Solution**:
```bash
# Ollama models download automatically on first request
# Check progress:
docker logs -f rag-ollama

# For Whisper (faster-whisper):
# Models cache in ~/.cache/huggingface/hub/
# Delete and retry if corrupted
```

---

## 📊 Database Initialization

### Weaviate Schema (Auto-created)

```python
# TextChunk collection
{
  "class": "TextChunk",
  "vectorizer": "none",
  "properties": [
    {"name": "paper_id", "dataType": ["text"]},
    {"name": "paper_title", "dataType": ["text"]},
    {"name": "chunk_text", "dataType": ["text"]},
    {"name": "chunk_index", "dataType": ["int"]},
    {"name": "page", "dataType": ["int"]},
    {"name": "vector", "dataType": ["number[]"]}
  ]
}

# FigureChunk collection
{
  "class": "FigureChunk",
  "vectorizer": "none",
  "properties": [
    {"name": "paper_id", "dataType": ["text"]},
    {"name": "paper_title", "dataType": ["text"]},
    {"name": "figure_data", "dataType": ["blob"]},
    {"name": "caption", "dataType": ["text"]},
    {"name": "vector", "dataType": ["number[]"]}
  ]
}
```

### Neo4j Schema (Auto-created)

```cypher
# Nodes
- (Paper) {id, title, year, doi}
- (Author) {name, institution}
- (Concept) {name, type}
- (Venue) {name, type}

# Relationships
- (Author)-[:WROTE]->(Paper)
- (Paper)-[:CITES]->(Paper)
- (Paper)-[:PUBLISHED_AT]->(Venue)
- (Paper)-[:MENTIONS]->(Concept)
- (Author)-[:AFFILIATED_WITH]->(Institution)
```

---

## 🚀 Performance Optimization

### For CPU-only systems:
```bash
# Set reduced model sizes
export EMBED_MODEL=nomic-embed-text-small
export CLIP_MODEL=ViT-B/32-quickgelu  # Faster variant
```

### For GPU systems:
```bash
# Use full models for best quality
# GPU automatically detected by PyTorch
docker-compose --profile all up -d
```

### Memory Management:
```bash
# If running out of memory, reduce batch sizes
export BATCH_SIZE=4  # Default: 8
```

---

## 📈 Monitoring

### View Docker Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f rag-backend
docker logs -f rag-weaviate
docker logs -f rag-neo4j

# Last 100 lines
docker logs --tail 100 rag-backend
```

### Check Resource Usage

```bash
# See CPU/Memory/Network for all containers
docker stats

# Exit with: Ctrl+C
```

---

## 🔄 Cleanup & Reset

### Stop All Services
```bash
docker-compose down
```

### Remove All Data (Reset Databases)
```bash
# WARNING: This deletes all papers, embeddings, and graph data
docker-compose down -v
```

### Rebuild Everything
```bash
docker-compose down
docker-compose --profile all build --no-cache
docker-compose --profile all up -d
```

---

## 📚 Next Steps

1. ✅ **Dependencies Installed** - All Python and npm packages ready
2. ✅ **.env File Created** - Ready for API keys
3. ⏭️ **Add API Keys** - Insert Groq and Cohere keys into `.env`
4. ⏭️ **Start Docker Services** - Run `docker-compose --profile all up -d`
5. ⏭️ **Access Frontend** - Open http://localhost:3000
6. ⏭️ **Upload a Paper** - Test the ingestion pipeline
7. ⏭️ **Query System** - Test multi-modal retrieval

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review error messages in Swagger: http://localhost:8054/docs
3. Check GitHub for similar issues
4. Verify API keys are correctly set in `.env`


# 🎯 Quick Reference Card

## 📍 Service URLs

| Service             | URL                        | Credentials           |
| ------------------- | -------------------------- | --------------------- |
| 🖥️ Frontend         | http://localhost:3000      | -                     |
| 🔌 Backend API      | http://localhost:8054      | -                     |
| 📚 Backend Docs     | http://localhost:8054/docs | -                     |
| 📊 Weaviate Console | http://localhost:8080      | -                     |
| 📈 Neo4j Browser    | http://localhost:7474      | neo4j / researchos123 |
| 🤖 Ollama API       | http://localhost:11434     | -                     |

## 🐳 Docker Commands

```bash
# Check status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f neo4j
docker-compose logs -f weaviate
docker-compose logs -f ollama

# Stop all
docker-compose stop

# Start all
docker-compose up -d

# Restart all
docker-compose restart

# Complete cleanup
docker-compose down -v
```

## 🔑 Important Credentials

```
Neo4j:
  - User: neo4j
  - Password: researchos123
  - URI: bolt://localhost:7687

Weaviate:
  - URL: http://weaviate:8080
  - Auth: Anonymous (enabled)

Ollama:
  - URL: http://ollama:11434
  - Loaded Model: nomic-embed-text

External APIs (configured in .env):
  - GROQ API
  - Cohere API
```

## 📋 Project Components

| Component    | Language         | Purpose                         |
| ------------ | ---------------- | ------------------------------- |
| **Frontend** | TypeScript/React | UI for querying and exploration |
| **Backend**  | Python/FastAPI   | API and data processing         |
| **Weaviate** | Docker           | Vector database for embeddings  |
| **Neo4j**    | Docker           | Knowledge graph database        |
| **Ollama**   | Docker           | Local embeddings & LLM service  |

## 🎯 Common Tasks

### Upload a PDF

```bash
curl -X POST http://localhost:8054/ingest/pdf \
  -F "file=@paper.pdf"
```

### Query the System

```bash
curl -X POST http://localhost:8054/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main findings in the papers?",
    "top_k": 5
  }'
```

### Check Backend Health

```bash
curl http://localhost:8054/health
```

### View API Documentation

Navigate to: http://localhost:8054/docs

## ⚠️ Troubleshooting

**Container failed to start?**

```bash
# Check logs
docker-compose logs <service-name>

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

**GPU error in WSL?**

- Already fixed! GPU specs were removed from docker-compose.yml

**Connection refused?**

- Wait 30-60 seconds for services to fully initialize
- Check firewall settings
- Ensure Docker daemon is running

## 📊 System Resources

- **Memory:** ~4-6 GB (shared across all containers)
- **Disk:** ~3-5 GB for databases and models
- **Ports Used:** 3000, 8054, 8080, 7474, 7687, 11434

---

**Status: ✅ ALL SYSTEMS GO**

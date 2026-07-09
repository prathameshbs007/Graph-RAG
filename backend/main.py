import base64
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from config import settings
from routers import ingest, query, graph
from services.neo4j_client import graph_db
from services.qdrant_client import db as qdrant_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def init_qdrant():
    qdrant_db.init_collections()


def init_neo4j():
    with graph_db.driver.session() as session:
        session.run("CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;")
        session.run("CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title);")
        session.run("CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name);")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_qdrant()
    except Exception as e:
        logger.error("Failed to init Qdrant collections: %s", e)
    try:
        init_neo4j()
    except Exception as e:
        logger.error("Failed to init Neo4j schema: %s", e)
    yield


app = FastAPI(title="ResearchOS", lifespan=lifespan)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)

os.makedirs(settings.FIGURES_DIR, exist_ok=True)

allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/figures/{figure_id}")
def get_figure(figure_id: str):
    file_path = os.path.join(settings.FIGURES_DIR, f"{figure_id}.jpg")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")

    payload = qdrant_db.get_figure_by_id(figure_id)
    if payload and payload.get("image_base64"):
        image_bytes = base64.b64decode(payload["image_base64"])
        return Response(content=image_bytes, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Figure not found")


@app.get("/health")
def health_check():
    qdrant_ok = False
    try:
        qdrant_db.client.get_collections()
        qdrant_ok = True
    except Exception as e:
        logger.error("Qdrant health check failed: %s", e)

    neo4j_ok = False
    try:
        graph_db.driver.verify_connectivity()
        neo4j_ok = True
    except Exception as e:
        logger.error("Neo4j health check failed: %s", e)

    groq_configured = bool(settings.GROQ_API_KEY)

    overall = "healthy" if (qdrant_ok and neo4j_ok and groq_configured) else "degraded"
    return {
        "status": overall,
        "qdrant": "ok" if qdrant_ok else "unavailable",
        "neo4j": "ok" if neo4j_ok else "unavailable",
        "groq_api_key_configured": groq_configured,
    }

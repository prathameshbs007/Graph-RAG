import base64
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from neo4j import GraphDatabase

from config import settings
from routers import ingest, query, graph
from services.qdrant_client import db as qdrant_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ResearchOS")

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)

os.makedirs(settings.FIGURES_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


def init_qdrant():
    qdrant_db.init_collections()

def init_neo4j():
    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;")
        session.run("CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title);")
        session.run("CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name);")
    driver.close()

@app.on_event("startup")
def startup_event():
    try:
        init_qdrant()
    except Exception as e:
        logger.error("Failed to init Qdrant collections: %s", e)
    try:
        init_neo4j()
    except Exception as e:
        logger.error("Failed to init Neo4j schema: %s", e)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

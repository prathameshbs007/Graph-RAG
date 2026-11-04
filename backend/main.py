import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import admin, graph, ingest, query
from services.neo4j_client import graph_db
from services.weaviate_client import db

LEGACY_CLASSES = ("TextChunk", "FigureChunk", "AudioChunk")


def _retry(name: str, fn, attempts: int = 10, delay: float = 3.0):
    """The databases may still be starting when the API comes up."""
    for i in range(attempts):
        try:
            fn()
            return
        except Exception as exc:  # noqa: BLE001
            if i == attempts - 1:
                print(f"Failed to init {name}: {exc}")
                return
            time.sleep(delay)


def init_weaviate():
    db.ensure_schema()
    legacy = [c for c in LEGACY_CLASSES if db.client.schema.exists(c)]
    if legacy:
        print(
            f"[startup] WARNING: old Weaviate classes {legacy} found. They are no longer queried; "
            "use 'Clear DB' and re-ingest to build the BM25 + graph index described in the report."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _retry("Weaviate schema", init_weaviate)
    _retry("Neo4j schema", graph_db.ensure_schema)
    yield
    graph_db.close()


app = FastAPI(title="ResearchOS", lifespan=lifespan)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)
app.include_router(admin.router)

os.makedirs(settings.FIGURES_DIR, exist_ok=True)
app.mount("/figures", StaticFiles(directory=settings.FIGURES_DIR), name="figures")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}

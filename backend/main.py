from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
import weaviate
from neo4j import GraphDatabase

app = FastAPI(title="ResearchOS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_weaviate():
    client = weaviate.Client(url=settings.WEAVIATE_URL)
    classes = [
        {
            "class": "TextChunk",
            "vectorizer": "none",
            "properties": [
                {"name": "paper_id", "dataType": ["text"]},
                {"name": "paper_title", "dataType": ["text"]},
                {"name": "authors", "dataType": ["text[]"]},
                {"name": "year", "dataType": ["int"]},
                {"name": "chunk_text", "dataType": ["text"]},
                {"name": "chunk_index", "dataType": ["int"]},
                {"name": "page", "dataType": ["int"]},
            ]
        },
        {
            "class": "FigureChunk",
            "vectorizer": "none",
            "properties": [
                {"name": "paper_id", "dataType": ["text"]},
                {"name": "paper_title", "dataType": ["text"]},
                {"name": "figure_id", "dataType": ["text"]},
                {"name": "caption", "dataType": ["text"]},
                {"name": "page", "dataType": ["int"]},
                {"name": "file_path", "dataType": ["text"]},
            ]
        },
        {
            "class": "AudioChunk",
            "vectorizer": "none",
            "properties": [
                {"name": "audio_id", "dataType": ["text"]},
                {"name": "title", "dataType": ["text"]},
                {"name": "chunk_text", "dataType": ["text"]},
                {"name": "start_time", "dataType": ["number"]},
                {"name": "end_time", "dataType": ["number"]},
                {"name": "source_paper_id", "dataType": ["text"]},
            ]
        }
    ]
    for cls in classes:
        if not client.schema.exists(cls["class"]):
            client.schema.create_class(cls)

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
        init_weaviate()
    except Exception as e:
        print(f"Failed to init Weaviate schema: {e}")
    try:
        init_neo4j()
    except Exception as e:
        print(f"Failed to init Neo4j schema: {e}")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

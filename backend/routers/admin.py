from fastapi import APIRouter
from services.weaviate_client import db
from services.neo4j_client import graph_db
from config import settings
import weaviate
from neo4j import GraphDatabase

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/clear-db")
async def clear_database():
    """Clear all data from Weaviate and Neo4j databases"""
    try:
        # Clear Weaviate
        weaviate_client = weaviate.Client(url=settings.WEAVIATE_URL)
        weaviate_client.schema.delete_all()
        
        # Recreate Weaviate schema
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
            if not weaviate_client.schema.exists(cls["class"]):
                weaviate_client.schema.create_class(cls)
        
        # Clear Neo4j
        driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
        
        return {
            "status": "success",
            "message": "Database cleared successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "detail": f"Failed to clear database: {str(e)}"
        }, 500

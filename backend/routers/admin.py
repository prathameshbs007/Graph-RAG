from fastapi import APIRouter
from pydantic import BaseModel
from services.weaviate_client import db
from services.neo4j_client import graph_db
from config import settings
import os
import shutil

router = APIRouter(prefix="/admin", tags=["admin"])

class ClearDBResponse(BaseModel):
    status: str
    message: str

@router.post("/clear-db", response_model=ClearDBResponse)
async def clear_database():
    """Clear all databases: Weaviate, Neo4j, and figures directory"""
    try:
        # 1. Clear Weaviate
        db.client.schema.delete_all()
        # Reinitialize schema
        from main import init_weaviate
        init_weaviate()
        
        # 2. Clear Neo4j
        with graph_db.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        
        # 3. Clear figures directory
        figures_dir = settings.FIGURES_DIR
        if os.path.exists(figures_dir):
            try:
                shutil.rmtree(figures_dir)
                os.makedirs(figures_dir, exist_ok=True)
            except OSError:
                # Directory might be in use, but that's okay
                pass
        
        return ClearDBResponse(
            status="success",
            message="✓ All databases cleared: Weaviate, Neo4j, and figures"
        )
    except Exception as e:
        print(f"Error clearing databases: {e}")
        return ClearDBResponse(
            status="error",
            message=f"Error clearing databases: {str(e)}"
        )

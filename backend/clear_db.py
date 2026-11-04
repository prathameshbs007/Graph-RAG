"""Wipe Weaviate and Neo4j and recreate the schemas: python clear_db.py"""
import sys

sys.path.append("/app")
from services.neo4j_client import graph_db  # noqa: E402
from services.weaviate_client import db  # noqa: E402

db.reset()
graph_db.clear()
graph_db.ensure_schema()
print("Wiped and recreated the Weaviate and Neo4j schemas.")

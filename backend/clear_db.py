import sys

sys.path.append("/app")
from neo4j import GraphDatabase

from config import settings
from services.qdrant_client import db as qdrant_db

if "--yes" not in sys.argv:
    print("This will permanently delete ALL data in Qdrant and Neo4j.")
    print("Re-run with --yes to confirm.")
    sys.exit(1)

qdrant_db.delete_all()
print("Wiped and recreated Qdrant collections!")

driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
driver.close()
print("Wiped Neo4j graph!")

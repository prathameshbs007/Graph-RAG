import sys
sys.path.append("/app")
from config import settings
from main import init_weaviate, init_neo4j
import weaviate
from neo4j import GraphDatabase

if "--yes" not in sys.argv:
    print("This will permanently delete ALL data in Weaviate and Neo4j.")
    print("Re-run with --yes to confirm.")
    sys.exit(1)

client = weaviate.Client(url=settings.WEAVIATE_URL)
client.schema.delete_all()
init_weaviate()
print("Wiped and Recreated Weaviate Schema!")

driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
driver.close()
print("Wiped Neo4j graph!")

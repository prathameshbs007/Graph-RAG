import sys
sys.path.append("/app")
from config import settings
from main import init_weaviate, init_neo4j
import weaviate

client = weaviate.Client(url=settings.WEAVIATE_URL)
client.schema.delete_all()
init_weaviate()
print("Wiped and Recreated Weaviate Schema!")

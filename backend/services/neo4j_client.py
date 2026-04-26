from neo4j import GraphDatabase
from config import settings

class Neo4jDB:
    def __init__(self):
        self.driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))

    def create_paper_node(self, paper_id: str, title: str, year: int, authors: list[str]):
        query = """
        MERGE (p:Paper {id: $paper_id})
        SET p.title = $title, p.year = $year
        WITH p
        UNWIND $authors as author_name
        MERGE (a:Author {id: toLower(author_name)})
        SET a.name = author_name
        MERGE (a)-[:WROTE]->(p)
        """
        with self.driver.session() as session:
            session.run(query, paper_id=paper_id, title=title, year=year, authors=authors)

    def close(self):
        self.driver.close()

graph_db = Neo4jDB()

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

    def get_related_graph_context(self, paper_ids: list[str]) -> dict:
        if not paper_ids:
            return {"related_papers": [], "concepts": []}
            
        related_papers = set()
        concepts = set()
        
        query = """
        MATCH (p:Paper)
        WHERE p.id IN $paper_ids
        OPTIONAL MATCH (p)-[:CITES]-(related:Paper)
        OPTIONAL MATCH (p)-[:HAS_CONCEPT]->(c:Concept)
        RETURN related.id AS related_id, c.name AS concept_name
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, paper_ids=paper_ids)
                for record in result:
                    r_id = record["related_id"]
                    c_name = record["concept_name"]
                    if r_id: related_papers.add(r_id)
                    if c_name: concepts.add(c_name)
        except Exception as e:
            print(f"Graph traversal error: {e}")
            
        return {
            "related_papers": list(related_papers),
            "concepts": list(concepts)
        }

    def close(self):
        self.driver.close()

graph_db = Neo4jDB()

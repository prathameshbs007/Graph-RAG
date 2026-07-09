import logging

from neo4j import GraphDatabase

from config import settings

logger = logging.getLogger(__name__)


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

    def add_concepts(self, paper_id: str, concepts: list[str]) -> int:
        if not concepts:
            return 0
        query = """
        MATCH (p:Paper {id: $paper_id})
        UNWIND $concepts AS concept_name
        MERGE (c:Concept {id: toLower(concept_name)})
        SET c.name = concept_name
        MERGE (p)-[:HAS_CONCEPT]->(c)
        RETURN count(DISTINCT c) AS n
        """
        with self.driver.session() as session:
            record = session.run(query, paper_id=paper_id, concepts=concepts).single()
            return record["n"] if record else 0

    def add_citations(self, paper_id: str, cited_titles: list[str]) -> int:
        if not cited_titles:
            return 0
        query = """
        MATCH (p:Paper {id: $paper_id})
        UNWIND $cited_titles AS cited_title
        MATCH (other:Paper)
        WHERE other.id <> $paper_id AND toLower(other.title) CONTAINS toLower(cited_title)
        MERGE (p)-[:CITES]->(other)
        RETURN count(DISTINCT other) AS n
        """
        with self.driver.session() as session:
            record = session.run(query, paper_id=paper_id, cited_titles=cited_titles).single()
            return record["n"] if record else 0

    def get_related_graph_context(self, paper_ids: list[str]) -> dict:
        if not paper_ids:
            return {"related_papers": [], "concepts": []}

        related_papers = set()
        concepts = set()

        citation_query = """
        MATCH (p:Paper)-[:CITES]-(other:Paper)
        WHERE p.id IN $paper_ids
        RETURN DISTINCT other.title AS title
        """
        concept_query = """
        MATCH (p:Paper)-[:HAS_CONCEPT]->(c:Concept)
        WHERE p.id IN $paper_ids
        RETURN DISTINCT c.name AS name
        """
        shared_concept_query = """
        MATCH (p:Paper)-[:HAS_CONCEPT]->(:Concept)<-[:HAS_CONCEPT]-(other:Paper)
        WHERE p.id IN $paper_ids AND NOT other.id IN $paper_ids
        RETURN DISTINCT other.title AS title
        """
        try:
            with self.driver.session() as session:
                for record in session.run(citation_query, paper_ids=paper_ids):
                    if record["title"]:
                        related_papers.add(record["title"])
                for record in session.run(concept_query, paper_ids=paper_ids):
                    if record["name"]:
                        concepts.add(record["name"])
                for record in session.run(shared_concept_query, paper_ids=paper_ids):
                    if record["title"]:
                        related_papers.add(record["title"])
        except Exception as e:
            logger.error("Graph traversal error: %s", e)

        return {
            "related_papers": list(related_papers),
            "concepts": list(concepts)
        }

    def close(self):
        self.driver.close()

graph_db = Neo4jDB()

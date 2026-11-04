"""Neo4j knowledge graph: schema, ingestion writes, weighted traversal and the
self-pruning memory state.

Graph model
-----------
Nodes      Paper, Talk (audio recording), Author, Concept, and retrievable *items*:
           ``(:Item:Chunk)`` (text or transcript segment) and ``(:Item:Figure)``.
Learned    ``(Item)-[:MENTIONS]->(Concept)``, ``(Concept)-[:RELATED_TO]-(Concept)``,
edges      ``(Paper)-[:CITES]->(Paper)``. Each has ``weight`` (starts at 0.5), ``visits``
           and ``pruned`` (soft delete, restorable).
Structure  ``HAS_CHUNK`` / ``HAS_FIGURE`` (Paper|Talk -> Item), ``WROTE``, ``ABOUT``.
           Never weighted, never pruned.
State      ``(:SystemState {id:'retrieval'})`` holds alpha; ``(:FeedbackEvent)`` is the
           audit log (query, edge, old and new weight).

Traversal (2 hops from the seed items)
--------------------------------------
  1. Item -MENTIONS-> Concept <-MENTIONS- Item          (co-mention)
  2. Item -MENTIONS-> Concept -RELATED_TO- Concept      (then the strongest items that
                                                         mention the reached concept)
  3. Item <-HAS_CHUNK- Paper -CITES- Paper              (then the cited paper's opening
                                                         chunks)
Reached concepts/papers are *resolved* to items so the candidate pool contains only
things the reranker can read. Every learned edge on a path is eligible for feedback.
"""

import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from neo4j import GraphDatabase

from config import settings
from services.citations import cites, compact
from services.feedback import EdgeRef

# On a fresh database Neo4j sends a notice for every query that names a relationship type or
# label that has not been created yet (e.g. MENTIONS before any concepts exist). They are
# harmless, expected here, and would flood the log, so only real errors are kept.
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

LEARNED_EDGE_TYPES = ("MENTIONS", "RELATED_TO", "CITES")
_NOT_PRUNED = "coalesce({r}.pruned, false) = false"


@dataclass
class Reached:
    """An item reached by the graph walk, with the edge paths that led to it."""

    item_id: str
    paths: list[list[EdgeRef]] = field(default_factory=list)
    concepts: set = field(default_factory=set)
    papers: set = field(default_factory=set)

    @property
    def strength(self) -> float:
        return max((min(e.weight for e in p) for p in self.paths), default=0.0)


class Neo4jDB:
    def __init__(self):
        self._driver = None

    @property
    def driver(self):
        # connect lazily so importing the app never needs a live database
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        return self._driver

    def run(self, query: str, **params) -> list[dict]:
        with self.driver.session() as session:
            return session.run(query, **params).data()

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    # ----------------------------------------------------------------- schema
    def ensure_schema(self):
        for label in ("Paper", "Talk", "Author", "Concept", "Item"):
            self.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")
        self.run("CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)")
        self.run("CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)")

    def clear(self):
        self.run("MATCH (n) DETACH DELETE n")

    # ----------------------------------------------------------------- ingest
    def upsert_paper(self, paper_id: str, title: str, year: int, authors: list[str], refs: list[str]):
        self.run(
            """
            MERGE (p:Paper {id: $paper_id})
            SET p.title = $title, p.year = $year, p.refs_compact = $refs_compact, p.ref_count = $ref_count
            WITH p
            UNWIND $authors AS author_name
            MERGE (a:Author {id: toLower(author_name)})
            SET a.name = author_name
            MERGE (a)-[:WROTE]->(p)
            """,
            paper_id=paper_id,
            title=title,
            year=year,
            refs_compact=compact(" ".join(refs)),
            ref_count=len(refs),
            authors=authors,
        )

    def upsert_talk(self, talk_id: str, title: str, source_paper_id: Optional[str]):
        self.run("MERGE (t:Talk {id: $id}) SET t.title = $title", id=talk_id, title=title)
        if source_paper_id:
            self.run(
                "MATCH (t:Talk {id: $id}), (p:Paper {id: $pid}) MERGE (t)-[:ABOUT]->(p)",
                id=talk_id,
                pid=source_paper_id,
            )

    def add_items(self, owner_label: str, owner_id: str, kind: str, items: list[dict]):
        """Create ``(:Item:<kind>)`` nodes (kind: Chunk | Figure) owned by a Paper or Talk."""
        if kind not in ("Chunk", "Figure") or owner_label not in ("Paper", "Talk"):
            raise ValueError("bad label")
        rel = "HAS_FIGURE" if kind == "Figure" else "HAS_CHUNK"
        self.run(
            f"""
            MATCH (o:{owner_label} {{id: $owner_id}})
            UNWIND $items AS it
            MERGE (n:Item {{id: it.id}})
            SET n:{kind}, n.modality = it.modality, n.page = it.page, n.chunk_index = it.chunk_index,
                n.section = it.section, n.start = it.start, n.end = it.end, n.owner_id = $owner_id
            MERGE (o)-[:{rel}]->(n)
            """,
            owner_id=owner_id,
            items=items,
        )

    def add_concepts(self, mentions: list[tuple], relations: list[tuple]) -> dict:
        """Write MENTIONS and RELATED_TO edges, all starting at the initial weight."""
        w0 = settings.EDGE_INIT_WEIGHT
        rows = [{"item": i, "cid": c, "name": n} for i, c, n in mentions]
        if rows:
            self.run(
                """
                UNWIND $rows AS r
                MATCH (i:Item {id: r.item})
                MERGE (c:Concept {id: r.cid})
                  ON CREATE SET c.name = r.name
                MERGE (i)-[m:MENTIONS]->(c)
                  ON CREATE SET m.weight = $w0, m.visits = 0, m.pruned = false
                """,
                rows=rows,
                w0=w0,
            )
        rel_rows = []
        for a, b, label in relations:
            a, b = (a, b) if a < b else (b, a)  # undirected: one canonical edge per pair
            rel_rows.append({"a": a, "b": b, "label": label})
        if rel_rows:
            self.run(
                """
                UNWIND $rows AS r
                MATCH (a:Concept {id: r.a}), (b:Concept {id: r.b})
                MERGE (a)-[e:RELATED_TO]->(b)
                  ON CREATE SET e.weight = $w0, e.visits = 0, e.pruned = false, e.relation = r.label
                """,
                rows=rel_rows,
                w0=w0,
            )
        return {"mentions": len(rows), "relations": len(rel_rows)}

    def link_citations(self, paper_id: str) -> int:
        """Create CITES edges between this paper and every other paper, in both directions."""
        papers = self.run("MATCH (p:Paper) RETURN p.id AS id, p.title AS title, p.refs_compact AS refs")
        by_id = {p["id"]: p for p in papers}
        me = by_id.get(paper_id)
        if not me:
            return 0
        pairs = []
        for oid, other in by_id.items():
            if oid == paper_id:
                continue
            if cites(other["title"] or "", me["refs"] or ""):
                pairs.append({"src": paper_id, "dst": oid})
            if cites(me["title"] or "", other["refs"] or ""):
                pairs.append({"src": oid, "dst": paper_id})
        if pairs:
            self.run(
                """
                UNWIND $pairs AS p
                MATCH (a:Paper {id: p.src}), (b:Paper {id: p.dst})
                MERGE (a)-[c:CITES]->(b)
                  ON CREATE SET c.weight = $w0, c.visits = 0, c.pruned = false
                """,
                pairs=pairs,
                w0=settings.EDGE_INIT_WEIGHT,
            )
        return len(pairs)

    # -------------------------------------------------------------- traversal
    def traverse(
        self,
        seed_ids: list[str],
        rng: Optional[random.Random] = None,
        min_weight: Optional[float] = None,
        explore_prob: Optional[float] = None,
        fanout: Optional[int] = None,
        per_node: Optional[int] = None,
    ) -> dict[str, Reached]:
        """2-hop weighted walk from ``seed_ids``; returns reached items (not the seeds).

        Edges below ``min_weight`` are skipped, except that each weak, un-pruned edge is
        followed with probability ``explore_prob`` so a useful edge is not lost for good.
        The decision is made once per edge per call.
        """
        if not seed_ids:
            return {}
        rng = rng or random.Random()
        tau = settings.EDGE_TRAVERSE_MIN if min_weight is None else min_weight
        eps = settings.EXPLORE_PROB if explore_prob is None else explore_prob
        fanout = fanout or settings.GRAPH_FANOUT
        per_node = per_node or settings.GRAPH_RESOLVE_PER_NODE
        seeds = set(seed_ids)

        decided: dict[str, bool] = {}

        def usable(ref: EdgeRef) -> bool:
            if ref.eid not in decided:
                decided[ref.eid] = ref.weight >= tau or rng.random() < eps
            return decided[ref.eid]

        def edge(row, n, etype):
            return EdgeRef(row[f"e{n}"], etype, row[f"a{n}"], row[f"b{n}"], float(row[f"w{n}"]))

        reached: dict[str, Reached] = {}

        def add(row, edges, concepts=(), papers=()):
            target = row["target"]
            if target in seeds or not all(usable(e) for e in edges):
                return
            r = reached.setdefault(target, Reached(target))
            r.paths.append(edges)
            r.concepts.update(c for c in concepts if c)
            r.papers.update(p for p in papers if p)

        # 1. co-mention: Item -MENTIONS-> Concept <-MENTIONS- Item
        rows = self.run(
            f"""
            UNWIND $seeds AS sid
            MATCH (s:Item {{id: sid}})-[r1:MENTIONS]->(c:Concept)
            WHERE {_NOT_PRUNED.format(r='r1')}
            CALL {{
              WITH s, c
              MATCH (c)<-[r2:MENTIONS]-(y:Item)
              WHERE y.id <> s.id AND {_NOT_PRUNED.format(r='r2')}
              RETURN r2, y ORDER BY r2.weight DESC LIMIT $fanout
            }}
            RETURN s.id AS seed, c.name AS cname,
                   elementId(r1) AS e1, r1.weight AS w1, startNode(r1).id AS a1, endNode(r1).id AS b1,
                   elementId(r2) AS e2, r2.weight AS w2, startNode(r2).id AS a2, endNode(r2).id AS b2,
                   y.id AS target
            """,
            seeds=list(seed_ids),
            fanout=fanout,
        )
        for row in rows:
            add(row, [edge(row, 1, "MENTIONS"), edge(row, 2, "MENTIONS")], concepts=[row["cname"]])

        # 2. relatedness: Item -MENTIONS-> Concept -RELATED_TO- Concept, then items of that concept
        rows = self.run(
            f"""
            UNWIND $seeds AS sid
            MATCH (s:Item {{id: sid}})-[r1:MENTIONS]->(c:Concept)
            WHERE {_NOT_PRUNED.format(r='r1')}
            MATCH (c)-[r3:RELATED_TO]-(c2:Concept)
            WHERE {_NOT_PRUNED.format(r='r3')}
            WITH s, r1, c, r3, c2 ORDER BY r3.weight DESC LIMIT $fanout
            CALL {{
              WITH s, c2
              MATCH (c2)<-[r4:MENTIONS]-(y:Item)
              WHERE y.id <> s.id AND {_NOT_PRUNED.format(r='r4')}
              RETURN r4, y ORDER BY r4.weight DESC LIMIT $per_node
            }}
            RETURN s.id AS seed, c.name AS cname, c2.name AS c2name,
                   elementId(r1) AS e1, r1.weight AS w1, startNode(r1).id AS a1, endNode(r1).id AS b1,
                   elementId(r3) AS e2, r3.weight AS w2, startNode(r3).id AS a2, endNode(r3).id AS b2,
                   elementId(r4) AS e3, r4.weight AS w3, startNode(r4).id AS a3, endNode(r4).id AS b3,
                   y.id AS target
            """,
            seeds=list(seed_ids),
            fanout=fanout * max(1, len(seed_ids)),
            per_node=per_node,
        )
        for row in rows:
            add(
                row,
                [edge(row, 1, "MENTIONS"), edge(row, 2, "RELATED_TO"), edge(row, 3, "MENTIONS")],
                concepts=[row["cname"], row["c2name"]],
            )

        # 3. citations: Item <-HAS_CHUNK- Paper -CITES- Paper, then the cited paper's opening chunks
        rows = self.run(
            f"""
            UNWIND $seeds AS sid
            MATCH (s:Item {{id: sid}})<-[:HAS_CHUNK|HAS_FIGURE]-(p:Paper)-[r:CITES]-(p2:Paper)
            WHERE {_NOT_PRUNED.format(r='r')}
            CALL {{
              WITH p2
              MATCH (p2)-[:HAS_CHUNK]->(y:Item)
              RETURN y ORDER BY y.chunk_index ASC LIMIT $per_node
            }}
            RETURN s.id AS seed, p2.title AS ptitle,
                   elementId(r) AS e1, r.weight AS w1, startNode(r).id AS a1, endNode(r).id AS b1,
                   y.id AS target
            """,
            seeds=list(seed_ids),
            per_node=per_node,
        )
        for row in rows:
            add(row, [edge(row, 1, "CITES")], papers=[row["ptitle"]])

        for r in reached.values():  # keep the 3 strongest paths per item
            r.paths.sort(key=lambda p: -min(e.weight for e in p))
            r.paths = r.paths[:3]
        return reached

    # -------------------------------------------------------- edge state & log
    def get_edge_states(self, eids: list[str]) -> dict[str, dict]:
        rows = self.run(
            """
            UNWIND $eids AS eid
            MATCH (a)-[r]->(b) WHERE elementId(r) = eid
            RETURN eid, r.weight AS weight, coalesce(r.visits, 0) AS visits,
                   coalesce(r.pruned, false) AS pruned, type(r) AS type, a.id AS src, b.id AS dst
            """,
            eids=eids,
        )
        return {r["eid"]: r for r in rows}

    def write_edge_states(self, updates: list[dict]):
        self.run(
            """
            UNWIND $updates AS u
            MATCH ()-[r]->() WHERE elementId(r) = u.eid
            SET r.weight = u.weight, r.visits = u.visits, r.pruned = u.pruned
            """,
            updates=updates,
        )

    def log_events(self, events: list[dict]):
        self.run("UNWIND $events AS ev CREATE (e:FeedbackEvent) SET e = ev", events=events)

    def list_events(self, limit: int = 100, kind: Optional[str] = None, query_id: Optional[str] = None) -> list[dict]:
        return self.run(
            """
            MATCH (e:FeedbackEvent)
            WHERE ($kind IS NULL OR e.kind = $kind) AND ($qid IS NULL OR e.query_id = $qid)
            RETURN e ORDER BY e.ts DESC LIMIT $limit
            """,
            kind=kind,
            qid=query_id,
            limit=limit,
        )

    def get_alpha(self) -> float:
        rows = self.run("MATCH (s:SystemState {id: 'retrieval'}) RETURN s.alpha AS alpha")
        if rows and rows[0]["alpha"] is not None:
            return float(rows[0]["alpha"])
        return settings.ALPHA_INIT

    def set_alpha(self, alpha: float):
        self.run("MERGE (s:SystemState {id: 'retrieval'}) SET s.alpha = $alpha", alpha=alpha)

    # ------------------------------------------------------- admin / reporting
    def edge_stats(self) -> dict:
        rows = self.run(
            """
            MATCH ()-[r:MENTIONS|RELATED_TO|CITES]->()
            RETURN type(r) AS type, count(r) AS total,
                   sum(CASE WHEN coalesce(r.pruned, false) THEN 1 ELSE 0 END) AS pruned,
                   avg(r.weight) AS avg_weight, sum(coalesce(r.visits, 0)) AS visits
            """
        )
        return {r["type"]: {k: r[k] for k in ("total", "pruned", "avg_weight", "visits")} for r in rows}

    def node_counts(self) -> dict:
        rows = self.run("MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS n")
        return {r["label"]: r["n"] for r in rows}

    def reset_feedback(self, clear_log: bool = True):
        """Back to the freshly-ingested state: weights 0.5, no visits, nothing pruned."""
        self.run(
            """
            MATCH ()-[r:MENTIONS|RELATED_TO|CITES]->()
            SET r.weight = $w0, r.visits = 0, r.pruned = false
            """,
            w0=settings.EDGE_INIT_WEIGHT,
        )
        self.set_alpha(settings.ALPHA_INIT)
        if clear_log:
            self.run("MATCH (e:FeedbackEvent) DETACH DELETE e")

    def restore_pruned(self, eid: Optional[str] = None) -> int:
        """Un-prune one edge (or all) and give it a fresh start."""
        rows = self.run(
            """
            MATCH ()-[r:MENTIONS|RELATED_TO|CITES]->()
            WHERE coalesce(r.pruned, false) = true AND ($eid IS NULL OR elementId(r) = $eid)
            SET r.pruned = false, r.visits = 0, r.weight = $w0
            RETURN count(r) AS n
            """,
            eid=eid,
            w0=settings.EDGE_INIT_WEIGHT,
        )
        return rows[0]["n"]

    @staticmethod
    def _kind(labels: list[str]) -> str:
        for k in ("Concept", "Item", "Paper"):
            if k in labels:
                return k
        return labels[0]

    def export_state(self) -> dict:
        """Snapshot of every learned edge + alpha (used to freeze / restore for evaluation)."""
        rows = self.run(
            """
            MATCH (a)-[r:MENTIONS|RELATED_TO|CITES]->(b)
            RETURN type(r) AS type, labels(a) AS la, a.id AS src, labels(b) AS lb, b.id AS dst,
                   r.weight AS weight, coalesce(r.visits, 0) AS visits, coalesce(r.pruned, false) AS pruned
            """
        )
        edges = [
            {
                "type": r["type"],
                "src_kind": self._kind(r["la"]),
                "src": r["src"],
                "dst_kind": self._kind(r["lb"]),
                "dst": r["dst"],
                "weight": r["weight"],
                "visits": r["visits"],
                "pruned": r["pruned"],
            }
            for r in rows
        ]
        return {"alpha": self.get_alpha(), "edges": edges, "exported_at": time.time()}

    def import_state(self, snapshot: dict) -> int:
        groups: dict[tuple, list[dict]] = {}
        for e in snapshot.get("edges", []):
            groups.setdefault((e["type"], e["src_kind"], e["dst_kind"]), []).append(e)
        n = 0
        for (etype, sk, dk), edges in groups.items():
            if etype not in LEARNED_EDGE_TYPES or not all(re.fullmatch(r"[A-Za-z]+", x) for x in (sk, dk)):
                continue
            self.run(
                f"""
                UNWIND $edges AS e
                MATCH (a:{sk} {{id: e.src}})-[r:{etype}]->(b:{dk} {{id: e.dst}})
                SET r.weight = e.weight, r.visits = e.visits, r.pruned = e.pruned
                """,
                edges=edges,
            )
            n += len(edges)
        self.set_alpha(float(snapshot.get("alpha", settings.ALPHA_INIT)))
        return n

    # ------------------------------------------------------------ visualisation
    def viz_graph(self, include_items: bool = False, concept_limit: int = 150, item_limit: int = 300) -> dict:
        """Nodes + links for the explorer, guaranteed consistent (every link has both nodes)."""
        nodes: dict[str, dict] = {}

        def put(id_, label, **extra):
            nodes[id_] = {"id": id_, "label": label, **extra}

        for r in self.run("MATCH (p:Paper) RETURN p.id AS id, p.title AS title, p.year AS year"):
            put(r["id"], "Paper", title=r["title"] or "", name=r["title"] or "")
        for r in self.run("MATCH (t:Talk) RETURN t.id AS id, t.title AS title"):
            put(r["id"], "Talk", title=r["title"] or "", name=r["title"] or "")
        for r in self.run("MATCH (a:Author) RETURN a.id AS id, a.name AS name"):
            put("author:" + r["id"], "Author", name=r["name"] or "", title="")
        for r in self.run(
            """
            MATCH (c:Concept)<-[m:MENTIONS]-(:Item)
            WITH c, count(m) AS n ORDER BY n DESC LIMIT $limit
            RETURN c.id AS id, c.name AS name, n
            """,
            limit=concept_limit,
        ):
            put("concept:" + r["id"], "Concept", name=r["name"] or r["id"], title="", mentions=r["n"])

        links: list[dict] = []

        def link(src, dst, type_, **extra):
            if src in nodes and dst in nodes:
                links.append({"source": src, "target": dst, "type": type_, **extra})

        for r in self.run("MATCH (a:Author)-[:WROTE]->(p:Paper) RETURN a.id AS a, p.id AS p"):
            link("author:" + r["a"], r["p"], "WROTE")
        for r in self.run("MATCH (t:Talk)-[:ABOUT]->(p:Paper) RETURN t.id AS t, p.id AS p"):
            link(r["t"], r["p"], "ABOUT")
        for r in self.run(
            "MATCH (a:Paper)-[r:CITES]->(b:Paper) RETURN a.id AS a, b.id AS b, elementId(r) AS eid, "
            "r.weight AS w, coalesce(r.visits,0) AS v, coalesce(r.pruned,false) AS pr"
        ):
            link(r["a"], r["b"], "CITES", eid=r["eid"], weight=r["w"], visits=r["v"], pruned=r["pr"])
        for r in self.run(
            "MATCH (a:Concept)-[r:RELATED_TO]->(b:Concept) RETURN a.id AS a, b.id AS b, elementId(r) AS eid, "
            "r.weight AS w, coalesce(r.visits,0) AS v, coalesce(r.pruned,false) AS pr, r.relation AS rel"
        ):
            link(
                "concept:" + r["a"], "concept:" + r["b"], "RELATED_TO",
                eid=r["eid"], weight=r["w"], visits=r["v"], pruned=r["pr"], relation=r["rel"],
            )
        # Paper/Talk -> Concept, aggregated over the items that mention the concept
        for r in self.run(
            """
            MATCH (o)-[:HAS_CHUNK|HAS_FIGURE]->(:Item)-[m:MENTIONS]->(c:Concept)
            WHERE o:Paper OR o:Talk
            RETURN o.id AS o, c.id AS c, count(m) AS n, avg(m.weight) AS w, sum(coalesce(m.visits,0)) AS v,
                   sum(CASE WHEN coalesce(m.pruned,false) THEN 1 ELSE 0 END) AS pruned
            """
        ):
            link(
                r["o"], "concept:" + r["c"], "MENTIONS",
                weight=r["w"], visits=r["v"], count=r["n"], pruned=bool(r["n"]) and r["pruned"] == r["n"],
            )

        if include_items:
            for r in self.run(
                """
                MATCH (i:Item)-[m:MENTIONS]->(c:Concept)
                RETURN i.id AS i, labels(i) AS labels, i.modality AS modality, i.page AS page,
                       c.id AS c, elementId(m) AS eid, m.weight AS w, coalesce(m.visits,0) AS v,
                       coalesce(m.pruned,false) AS pr
                LIMIT $limit
                """,
                limit=item_limit,
            ):
                if "concept:" + r["c"] not in nodes:
                    continue
                label = "Figure" if "Figure" in r["labels"] else "Chunk"
                put(r["i"], label, name=f"{r['modality']} p.{r['page']}" if r["page"] else r["modality"] or label, title="")
                link(r["i"], "concept:" + r["c"], "MENTIONS", eid=r["eid"], weight=r["w"], visits=r["v"], pruned=r["pr"])

        return {"nodes": list(nodes.values()), "links": links}


graph_db = Neo4jDB()

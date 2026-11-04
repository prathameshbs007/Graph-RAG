"""Query pipeline: Modules 2, 3 and 4 wired together.

    embed query -> BM25 + dense (top-K each) -> fuse (alpha or RRF) -> top-10 seeds
      -> 2-hop weighted graph walk -> candidate pool (seeds + reached, with provenance)
      -> Cohere rerank -> keep score >= cutoff, top-k as context
      -> reranker feedback (edge weights, pruning, alpha, audit log)
      -> grounded generation + claim verification

The same function serves the API and the evaluation harness. A ``SystemConfig`` switches
components on and off, which is how the five baselines and the ablations of Section 4.2
are expressed without a second code path.
"""

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from config import settings
from services.embedder import EmbeddingError, embed_query
from services.feedback import FeedbackEngine
from services.fusion import fuse_alpha, fuse_rrf
from services.generator import describe_location, generator
from services.neo4j_client import graph_db
from services.reranker import reranker
from services.weaviate_client import db


# ---------------------------------------------------------------- systems
@dataclass(frozen=True)
class SystemConfig:
    name: str
    description: str = ""
    retriever: str = "hybrid"  # hybrid | bm25 | dense
    adaptive_alpha: bool = True  # use (and learn) the stored alpha; else fixed_alpha
    fixed_alpha: float = 0.5
    use_graph: bool = True
    use_reranker: bool = True
    feedback: bool = True  # the system includes the self-pruning feedback loop
    state: str = "learned"  # evaluation only: "learned" or "initial" graph weights


SYSTEMS: dict[str, SystemConfig] = {
    s.name: s
    for s in [
        SystemConfig("full", "ResearchOS: hybrid + graph + reranker feedback + pruning"),
        SystemConfig("b1_bm25", "B1 BM25 only", retriever="bm25", use_graph=False, use_reranker=False,
                     feedback=False, state="initial"),
        SystemConfig("b2_dense", "B2 dense only", retriever="dense", use_graph=False, use_reranker=False,
                     feedback=False, state="initial"),
        SystemConfig("b3_static_hybrid", "B3 static hybrid (alpha fixed at 0.5)", adaptive_alpha=False,
                     use_graph=False, use_reranker=False, feedback=False, state="initial"),
        SystemConfig("b4_static_graph", "B4 static Graph RAG (weights never updated)", adaptive_alpha=False,
                     feedback=False, state="initial"),
        SystemConfig("b5_flat_rerank", "B5 flat vector RAG + reranker (no graph)", retriever="dense",
                     use_graph=False, feedback=False, state="initial"),
        SystemConfig("abl_no_bm25", "Full without BM25", retriever="dense"),
        SystemConfig("abl_no_dense", "Full without dense vectors", retriever="bm25"),
        SystemConfig("abl_no_graph", "Full without graph traversal", use_graph=False),
        SystemConfig("abl_no_feedback", "Full without reranker feedback", adaptive_alpha=False, feedback=False,
                     state="initial"),
    ]
}


def get_system(name: Optional[str]) -> SystemConfig:
    try:
        return SYSTEMS[name or "full"]
    except KeyError:
        raise ValueError(f"unknown system '{name}', choose from {sorted(SYSTEMS)}") from None


# ------------------------------------------------------------- candidates
@dataclass
class Candidate:
    id: str
    hit: dict
    retrievers: set = field(default_factory=set)  # subset of {"bm25", "dense", "graph"}
    fused: float = 0.0
    is_seed: bool = False
    paths: list = field(default_factory=list)  # list[list[EdgeRef]]
    concepts: set = field(default_factory=set)
    papers: set = field(default_factory=set)
    rerank: Optional[float] = None

    @property
    def text(self) -> str:
        return self.hit.get("chunk_text") or ""


@dataclass
class PipelineResult:
    query_id: str
    query: str
    system: SystemConfig
    context: list  # list[Candidate], best first, at most CONTEXT_SIZE
    candidates: list  # the whole reranked pool
    alpha: Optional[float]
    trace: dict


def _source_dict(c: Candidate, evidence_id: str) -> dict:
    h = c.hit
    score = c.rerank if c.rerank is not None else c.fused
    d = {
        "evidence_id": evidence_id,
        "chunk_id": c.id,
        "modality": h.get("modality", "text"),
        "paper_id": h.get("paper_id") or "",
        "paper_title": h.get("paper_title") or "",
        "authors": h.get("authors") or [],
        "year": h.get("year"),
        "chunk_text": h.get("chunk_text") or "",
        "page": h.get("page"),
        "section": h.get("section"),
        "start_time": h.get("start_time"),
        "end_time": h.get("end_time"),
        "audio_id": h.get("audio_id"),
        "score": round(float(score), 4),
        "found_by": sorted(c.retrievers),
        "via": "seed" if c.is_seed else "graph",
    }
    d["location"] = describe_location({**h, "evidence_id": evidence_id})
    return d


# --------------------------------------------------------------- pipeline
class QueryPipeline:
    def __init__(self, store=db, graph=graph_db, rerank=reranker, embed=embed_query, cfg=settings):
        self.store, self.graph, self.rerank, self.embed, self.cfg = store, graph, rerank, embed, cfg

    # ---- stage 1: first-stage retrieval + fusion
    def _first_stage(self, query: str, system: SystemConfig, alpha: Optional[float], notes: list):
        k = self.cfg.RETRIEVAL_TOP_K
        bm25_hits, dense_hits = [], []
        if system.retriever in ("hybrid", "bm25"):
            bm25_hits = self.store.bm25(query, k)
        if system.retriever in ("hybrid", "dense"):
            try:
                dense_hits = self.store.dense(self.embed(query), k)
            except EmbeddingError as exc:
                notes.append(f"dense retrieval unavailable ({exc}); using BM25 only")
                if system.retriever == "dense":
                    bm25_hits = self.store.bm25(query, k)  # degrade rather than return nothing
        bm25 = [(h["chunk_id"], h["score"]) for h in bm25_hits]
        dense = [(h["chunk_id"], h["score"]) for h in dense_hits]
        if system.retriever == "hybrid" and dense and bm25:
            if self.cfg.FUSION == "rrf":
                ranked = fuse_rrf(bm25, dense, self.cfg.RRF_K)
            else:
                ranked = fuse_alpha(bm25, dense, alpha if alpha is not None else self.cfg.ALPHA_INIT)
        else:
            ranked = dense or bm25
            ranked = sorted(ranked, key=lambda t: -t[1])
        hits = {h["chunk_id"]: h for h in bm25_hits + dense_hits}
        tags = {}
        for cid, _ in bm25:
            tags.setdefault(cid, set()).add("bm25")
        for cid, _ in dense:
            tags.setdefault(cid, set()).add("dense")
        return ranked, hits, tags, len(bm25), len(dense)

    # ---- the whole retrieval side
    def retrieve(
        self,
        query: str,
        system: SystemConfig,
        learn: Optional[bool] = None,
        seed: Optional[int] = None,
        query_id: Optional[str] = None,
    ) -> PipelineResult:
        cfg = self.cfg
        query_id = query_id or uuid.uuid4().hex[:12]
        notes: list[str] = []
        timings: dict[str, float] = {}
        t0 = time.time()

        use_alpha = system.retriever == "hybrid" and cfg.FUSION == "alpha"
        alpha = None
        if use_alpha:
            alpha = self.graph.get_alpha() if system.adaptive_alpha else system.fixed_alpha

        ranked, hits, tags, n_bm25, n_dense = self._first_stage(query, system, alpha, notes)
        timings["first_stage_ms"] = round((time.time() - t0) * 1000)

        pool: dict[str, Candidate] = {}
        for cid, score in ranked[: cfg.SEED_K]:
            pool[cid] = Candidate(cid, hits[cid], retrievers=set(tags.get(cid, ())), fused=float(score), is_seed=True)
        seed_ids = list(pool)

        # ---- stage 2: graph expansion
        t1 = time.time()
        n_graph = 0
        if system.use_graph and seed_ids:
            try:
                reached = self.graph.traverse(seed_ids, rng=random.Random(seed))
                room = max(0, cfg.CANDIDATE_POOL_MAX - len(pool))
                best = sorted(reached.values(), key=lambda r: -r.strength)[:room]
                missing = [r.item_id for r in best if r.item_id not in hits]
                hits.update(self.store.fetch(missing))
                for r in best:
                    hit = hits.get(r.item_id)
                    if hit is None:
                        continue  # in the graph but not in the vector store (e.g. half-deleted)
                    cand = pool.setdefault(
                        r.item_id, Candidate(r.item_id, hit, retrievers=set(tags.get(r.item_id, ())))
                    )
                    cand.retrievers.add("graph")
                    cand.paths, cand.concepts, cand.papers = r.paths, r.concepts, r.papers
                    n_graph += 1
            except Exception as exc:  # noqa: BLE001 - a graph outage must not kill retrieval
                notes.append(f"graph traversal failed: {exc}")
        timings["graph_ms"] = round((time.time() - t1) * 1000)

        cands = list(pool.values())

        # ---- stage 3: rerank + context selection
        t2 = time.time()
        scores = None
        if system.use_reranker and cands:
            scores = self.rerank.score(query, [c.text for c in cands])
            if scores is None:
                notes.append("reranker unavailable: ranking by fused score and feedback is skipped")
        if scores is not None:
            for c, s in zip(cands, scores):
                c.rerank = s
            kept = [c for c in cands if c.rerank >= cfg.RELEVANCE_CUTOFF]
            kept.sort(key=lambda c: -c.rerank)
        else:
            kept = [c for c in cands if c.is_seed]  # already in fused order
        context = kept[: cfg.CONTEXT_SIZE]
        timings["rerank_ms"] = round((time.time() - t2) * 1000)

        # ---- stage 4: feedback
        learn_flag = system.feedback if learn is None else learn
        feedback = {"applied": False}
        if learn_flag and cfg.FEEDBACK_ENABLED and scores is not None:
            path_scores = [(p, c.rerank) for c in cands for p in c.paths]
            retriever_scores = [
                (frozenset(c.retrievers - {"graph"}), c.rerank) for c in cands if c.is_seed
            ]
            report = FeedbackEngine(self.graph, cfg).apply(
                query_id,
                query,
                path_scores,
                alpha if alpha is not None else cfg.ALPHA_INIT,
                retriever_scores,
                adapt_alpha=use_alpha and system.adaptive_alpha,
            )
            feedback = report.summary()
        elif learn_flag and not cfg.FEEDBACK_ENABLED:
            notes.append("feedback is globally disabled (FEEDBACK_ENABLED=false)")

        trace = {
            "query_id": query_id,
            "system": system.name,
            "alpha": None if alpha is None else round(alpha, 4),
            "fusion": cfg.FUSION if system.retriever == "hybrid" else system.retriever,
            "bm25_hits": n_bm25,
            "dense_hits": n_dense,
            "seeds": len(seed_ids),
            "graph_reached": n_graph,
            "candidates": len(cands),
            "reranked": scores is not None,
            "above_cutoff": sum(1 for c in cands if c.rerank is not None and c.rerank >= cfg.RELEVANCE_CUTOFF),
            "feedback": feedback,
            "timings": timings,
            "notes": notes,
        }
        return PipelineResult(query_id, query, system, context, cands, alpha, trace)

    # ---- retrieval + generation
    def answer(
        self,
        query: str,
        system: Optional[str] = None,
        learn: Optional[bool] = None,
        seed: Optional[int] = None,
        verify: Optional[bool] = None,
    ) -> dict:
        t0 = time.time()
        sys_cfg = get_system(system)
        res = self.retrieve(query, sys_cfg, learn=learn, seed=seed)

        sources_all = [_source_dict(c, f"E{i}") for i, c in enumerate(res.context, start=1)]
        t_gen = time.time()
        gen = generator.generate(query, sources_all, verify=verify)
        res.trace["timings"]["generate_ms"] = round((time.time() - t_gen) * 1000)
        res.trace["timings"]["total_ms"] = round((time.time() - t0) * 1000)

        for s in sources_all:
            s["cited"] = s["evidence_id"] in gen.cited
        figures, sources = [], []
        for c, s in zip(res.context, sources_all):
            if s["modality"] == "image":
                h = c.hit
                figures.append(
                    {
                        "evidence_id": s["evidence_id"],
                        "figure_id": h.get("figure_id", c.id),
                        "paper_id": s["paper_id"],
                        "paper_title": s["paper_title"],
                        "page": h.get("page") or 0,
                        "caption": h.get("caption") or s["chunk_text"],
                        "description": h.get("description") or "",
                        "bbox": h.get("bbox") or [],
                        "url": f"/figures/{_basename(h.get('file_path'))}" if h.get("file_path") else "",
                        "score": s["score"],
                        "cited": s["cited"],
                    }
                )
            else:
                sources.append(s)

        concepts = sorted({n for c in res.context for n in c.concepts})
        papers = sorted({n for c in res.context for n in c.papers})
        return {
            "query_id": res.query_id,
            "answer": gen.answer,
            "sources": sources,
            "figures": figures,
            "graph_context": {"related_papers": papers, "concepts": concepts},
            "claims": [
                {"text": c.text, "evidence_ids": c.evidence_ids, "verdict": c.verdict} for c in gen.claims
            ],
            "claim_stats": {**gen.stats, "verified": gen.verified},
            "diagnostics": res.trace,
            # internal use by the evaluation harness (not part of the API schema)
            "_context_texts": [c.text for c in res.context],
            "_pool": [
                {"id": c.id, "text": c.text, "rerank": c.rerank, "via": "seed" if c.is_seed else "graph"}
                for c in res.candidates
            ],
        }


def _basename(path: Optional[str]) -> str:
    return (path or "").replace("\\", "/").rsplit("/", 1)[-1]


pipeline = QueryPipeline()

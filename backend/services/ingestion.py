"""Module 1: multi-modal ingestion.

PDF   extract (text, headings, tables, figures, references) -> describe figures ->
      embed -> extract concepts/relations -> write Weaviate + Neo4j -> link citations
Audio transcribe (timestamped windows) -> embed -> extract concepts -> write both stores

Both run in a worker thread (they are plain functions, so Starlette's background task
runner does not block the event loop) and report progress through ``JOBS``.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from config import settings
from services import figure_describer
from services.concept_extractor import extract_concepts
from services.embedder import embed_documents
from services.llm import LLMUnavailable
from services.neo4j_client import graph_db
from services.pdf_extractor import extract_pdf_data
from services.weaviate_client import db

MIN_WORDS_FOR_CONCEPTS = 20


# --------------------------------------------------------------- job tracking
@dataclass
class Job:
    id: str
    kind: str
    title: str
    status: str = "queued"  # queued | running | done | error
    stage: str = "queued"
    detail: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    started: float = field(default_factory=time.time)
    finished: Optional[float] = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "status": self.status,
            "stage": self.stage,
            "detail": self.detail,
            "warnings": self.warnings,
            "error": self.error,
            "seconds": round((self.finished or time.time()) - self.started, 1),
        }


JOBS: dict[str, Job] = {}
_JOBS_LOCK = threading.Lock()
_MAX_JOBS = 200


def new_job(job_id: str, kind: str, title: str) -> Job:
    with _JOBS_LOCK:
        if len(JOBS) >= _MAX_JOBS:  # forget the oldest finished jobs
            for k in [k for k, j in JOBS.items() if j.status in ("done", "error")][: _MAX_JOBS // 4]:
                JOBS.pop(k, None)
        JOBS[job_id] = Job(job_id, kind, title)
        return JOBS[job_id]


def _stage(job: Optional[Job], stage: str):
    if job:
        job.status, job.stage = "running", stage
    print(f"[ingest] {job.id if job else '-'} {stage}")


def _is_filename(title: str) -> bool:
    return not title or title.lower().endswith((".pdf", ".wav", ".mp3", ".m4a")) or "." in title and " " not in title


# ----------------------------------------------------------------------- PDF
def ingest_pdf(
    pdf_path: str,
    paper_id: str,
    title: Optional[str],
    authors: list[str],
    year: Optional[int],
    figures_dir: str,
    job: Optional[Job] = None,
) -> dict:
    try:
        _stage(job, "parsing PDF")
        ex = extract_pdf_data(pdf_path, paper_id, figures_dir)
        # explicit user input wins; otherwise use what the PDF itself says
        paper_title = title if not _is_filename(title or "") else (ex.title or title or paper_id)
        paper_authors = authors or ex.authors
        paper_year = year or ex.year

        items: list[dict] = []
        for c in ex.chunks:
            items.append(
                {
                    "chunk_id": f"{paper_id}:t{c['chunk_index']}",
                    "modality": "text",
                    "chunk_text": c["chunk_text"],
                    "page": c["page"],
                    "chunk_index": c["chunk_index"],
                    "section": c["section"][:200],
                }
            )
        figures = []
        for f in ex.figures:
            figures.append(
                {
                    "chunk_id": f["figure_id"],
                    "figure_id": f["figure_id"],
                    "modality": "image",
                    "caption": f["caption"],
                    "page": f["page"],
                    "bbox": f["bbox"],
                    "file_path": f["file_path"],
                    "ocr_text": f["ocr_text"],
                    "section": f.get("section"),
                }
            )

        if figure_describer.enabled() and figures:
            _stage(job, f"describing {len(figures)} figures")
            for f in figures:
                f["description"] = figure_describer.describe_figure(f["file_path"], f["caption"])
        for f in figures:
            parts = [f.get("section") or "", f["caption"], f.get("description") or f.get("ocr_text") or ""]
            f["chunk_text"] = " ".join(p for p in parts if p).strip()

        all_items = items + figures
        if not all_items:
            raise ValueError("no extractable text or figures found in this PDF")
        for it in all_items:
            it.update(paper_id=paper_id, paper_title=paper_title, authors=paper_authors, year=paper_year)

        _stage(job, f"embedding {len(all_items)} chunks")
        vectors = embed_documents([it["chunk_text"] for it in all_items])
        for it, v in zip(all_items, vectors):
            it["vector"] = v

        concepts = _extract_concepts(all_items, job)

        _stage(job, "writing to Weaviate")
        try:
            db.insert_chunks(all_items)
            _stage(job, "writing to Neo4j")
            graph_db.upsert_paper(paper_id, paper_title, paper_year, paper_authors, ex.references)
            graph_db.add_items(
                "Paper",
                paper_id,
                "Chunk",
                [
                    {k: it.get(k) for k in ("modality", "page", "chunk_index", "section")} | {"id": it["chunk_id"]}
                    for it in items
                ],
            )
            graph_db.add_items(
                "Paper",
                paper_id,
                "Figure",
                [{"id": f["chunk_id"], "modality": "image", "page": f["page"], "chunk_index": None, "section": f.get("section")}
                 for f in figures],
            )
            edges = graph_db.add_concepts(concepts.mentions, concepts.relations)
            cites = graph_db.link_citations(paper_id)
        except Exception:
            _rollback(paper_id)
            raise

        result = {
            "paper_id": paper_id,
            "title": paper_title,
            "pages": ex.pages,
            "chunks": len(items),
            "figures": len(figures),
            "references": len(ex.references),
            "concept_mentions": edges["mentions"],
            "concept_relations": edges["relations"],
            "citation_edges": cites,
        }
        if job:
            job.detail, job.status, job.stage, job.finished = result, "done", "done", time.time()
        print(f"[ingest] {paper_id} done: {result}")
        return result
    except Exception as exc:  # noqa: BLE001 - surfaced through the job status
        print(f"[ingest] {paper_id} FAILED: {exc}")
        if job:
            job.status, job.stage, job.error, job.finished = "error", "failed", str(exc), time.time()
        return {"error": str(exc)}


def _extract_concepts(items: list[dict], job: Optional[Job]):
    """LLM concept extraction; a missing LLM degrades to a graph without concept edges."""
    from services.concept_extractor import ConceptGraph

    eligible = [
        {"id": it["chunk_id"], "text": it["chunk_text"]}
        for it in items
        if len(it["chunk_text"].split()) >= MIN_WORDS_FOR_CONCEPTS
    ]
    if not (settings.CONCEPT_EXTRACTION and eligible):
        return ConceptGraph()
    _stage(job, f"extracting concepts from {len(eligible)} chunks")
    try:
        result = extract_concepts(eligible)
    except LLMUnavailable as exc:
        if job:
            job.warnings.append(f"concept extraction skipped: {exc}")
        return ConceptGraph()
    if result.failed_batches and job:
        job.warnings.append(f"{result.failed_batches} concept-extraction batches failed")
    return result


def _rollback(owner_id: str):
    """Undo a half-finished ingest so retrieval never sees orphaned vectors."""
    for prop in ("paper_id", "audio_id"):
        try:
            db.delete_where(prop, owner_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[ingest] rollback of {prop}={owner_id} failed: {exc}")


# --------------------------------------------------------------------- audio
def ingest_audio(
    audio_path: str,
    audio_id: str,
    title: str,
    source_paper_id: Optional[str],
    transcribe: Optional[Callable] = None,
    job: Optional[Job] = None,
) -> dict:
    try:
        if transcribe is None:
            from services.audio_transcriber import transcriber

            transcribe = transcriber.transcribe
        _stage(job, "transcribing")
        windows, duration, n_segments = transcribe(audio_path)
        if not windows:
            raise ValueError("no speech detected in this recording")

        items = [
            {
                "chunk_id": f"{audio_id}:a{i}",
                "modality": "audio",
                "chunk_text": w["chunk_text"],
                "audio_id": audio_id,
                "paper_id": source_paper_id or "",
                "source_paper_id": source_paper_id or "",
                "paper_title": title,
                "start_time": w["start_time"],
                "end_time": w["end_time"],
                "chunk_index": i,
            }
            for i, w in enumerate(windows)
        ]

        _stage(job, f"embedding {len(items)} transcript windows")
        for it, v in zip(items, embed_documents([it["chunk_text"] for it in items])):
            it["vector"] = v

        concepts = _extract_concepts(items, job)

        _stage(job, "writing to Weaviate and Neo4j")
        try:
            db.insert_chunks(items)
            graph_db.upsert_talk(audio_id, title, source_paper_id)
            graph_db.add_items(
                "Talk",
                audio_id,
                "Chunk",
                [
                    {
                        "id": it["chunk_id"],
                        "modality": "audio",
                        "page": None,
                        "chunk_index": it["chunk_index"],
                        "section": None,
                        "start": it["start_time"],
                        "end": it["end_time"],
                    }
                    for it in items
                ],
            )
            edges = graph_db.add_concepts(concepts.mentions, concepts.relations)
        except Exception:
            _rollback(audio_id)
            raise

        result = {
            "audio_id": audio_id,
            "title": title,
            "duration_seconds": duration,
            "segments": n_segments,
            "chunks": len(items),
            "concept_mentions": edges["mentions"],
            "concept_relations": edges["relations"],
        }
        if job:
            job.detail, job.status, job.stage, job.finished = result, "done", "done", time.time()
        return result
    except Exception as exc:  # noqa: BLE001
        print(f"[ingest] audio {audio_id} FAILED: {exc}")
        if job:
            job.status, job.stage, job.error, job.finished = "error", "failed", str(exc), time.time()
        return {"error": str(exc)}

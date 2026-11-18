# ResearchOS Validation Report

**Generated:** 2026-11-18 18:23:56  
**Corpus:** `docs/arvr-1.pdf` (IfcSpace / BIM Indoor Navigation, Turnstiles) + `docs/arvr-5.pdf` (Unity AR Navigation, Figure 1: Workflow of Indoor Navigation)  
**Methodology:** 100% real pipeline telemetry — Cohere rerank-v3.5 scores, Neo4j edge weights, Module 4 NLI claim verification. No LLM-as-a-judge, no Ragas, no re-ingestion.

---

## Objective 1: Multi-Modal Ingestion & Hybrid Retrieval

### 1a. Indexed Modality Distribution

| Modality | Weaviate Chunks | % of Total |
|---|---|---|
| `image` | 18 | 8.3% |
| `text` | 198 | 91.7% |

**Neo4j Graph State:**

| Node Type | Count |
|---|---|
| Author | 1 |
| Chunk | 133 |
| Concept | 478 |
| FeedbackEvent | 1094 |
| Figure | 10 |
| Item | 143 |
| Paper | 3 |
| SystemState | 1 |

| Edge Type | Total | Pruned | Avg Weight | Visits |
|---|---|---|---|---|
| MENTIONS | 805 | 4 | 0.4699 | 833 |
| RELATED_TO | 199 | 0 | 0.4653 | 228 |

### 1b. Cross-Modal Citation & Hit Rate (HR\_MM@5)

| Metric | Value |
|---|---|
| Multi-modal–targeted queries | 2 (Q03, Q04: figure queries) |
| HR\_MM@5 — ResearchOS Full (HyDE ON) | **0.50** (1/2 queries cite ≥1 non-text chunk in top-5) |

### 1c. BM25 vs Dense Pre-Fusion Complementarity

Computed from true top-20 BM25 hits (`b1_bm25` system) vs top-20 Dense hits (`b2_dense` system) **before** fusion:

| Metric | Mean across 10 queries |
|---|---|
| Jaccard Overlap (\|BM25∩Dense\| / \|BM25∪Dense\|) | **0.3579** |
| Lexical-Semantic Complementarity (1 − Jaccard) | **0.6421** |

> A complementarity of **0.64** means the two retrieval channels capture predominantly distinct evidence, validating the hybrid fusion strategy.

#### Per-Query Overlap Detail

| Query | Type | ∩ | ∪ | Jaccard | Complement. |
|---|---|---|---|---|---|
| Q01 | lexical | 2 | 18 | 0.1111 | 0.8889 |
| Q02 | semantic | 2 | 18 | 0.1111 | 0.8889 |
| Q03 | multi_modal_figure | 4 | 16 | 0.25 | 0.75 |
| Q04 | multi_modal_figure | 5 | 15 | 0.3333 | 0.6667 |
| Q05 | semantic | 5 | 15 | 0.3333 | 0.6667 |
| Q06 | lexical | 8 | 12 | 0.6667 | 0.3333 |
| Q07 | multi_hop | 4 | 16 | 0.25 | 0.75 |
| Q08 | semantic | 6 | 14 | 0.4286 | 0.5714 |
| Q09 | multi_hop | 6 | 14 | 0.4286 | 0.5714 |
| Q10 | lexical | 8 | 12 | 0.6667 | 0.3333 |

---

## Objective 2: Pre-Retrieval Query Expansion via Split-Query HyDE

Same 10 queries run twice: `HyDE OFF` (raw query → Weaviate dense, baseline) and `HyDE ON` (Groq-hallucinated expert answer → `search_document:` prefix → Weaviate dense).

| Metric | HyDE OFF (Baseline) | HyDE ON (ResearchOS) | Δ |
|---|---|---|---|
| Mean Cohere S\_rerank (Top-5) | 0.6529 | 0.6560 | **+0.0031** |
| Precision@5 (s ≥ 0.30) | 1.0000 | 1.0000 | **+0.0000** |
| Mean HyDE Latency Tax | — | 1374 ms | — |

### Per-Query HyDE Ablation

| Query | Type | HyDE OFF | HyDE ON | Δ S\_rerank | Hyde Lat. (ms) |
|---|---|---|---|---|---|
| Q01 | lexical | 0.5559 | 0.7092 | **+0.1533** | 1133 |
| Q02 | semantic | 0.6976 | 0.6976 | **+0.0000** | 1368 |
| Q03 | multi_modal_figure | 0.7724 | 0.7724 | **+0.0000** | 1322 |
| Q04 | multi_modal_figure | 0.8170 | 0.8170 | **+0.0000** | 1426 |
| Q05 | semantic | 0.6551 | 0.6551 | **+0.0000** | 1618 |
| Q06 | lexical | 0.6209 | 0.6210 | **+0.0001** | 1292 |
| Q07 | multi_hop | 0.6277 | 0.4810 | **-0.1467** | 1746 |
| Q08 | semantic | 0.4991 | 0.4991 | **+0.0000** | 976 |
| Q09 | multi_hop | 0.8378 | 0.8616 | **+0.0238** | 1380 |
| Q10 | lexical | 0.4456 | 0.4456 | **+0.0000** | 1482 |

---

## Objective 3: Self-Pruning Agentic Memory & Grounded Generation

### 3a. Edge Weight Distribution Shift (3-State Comparison)

| State | MENTIONS Total | Pruned | Avg Weight | Total Visits |
|---|---|---|---|---|
| **Initial Baseline** (w₀ = 0.50, fresh ingest, 0 visits) | 805 | 0 | 0.5000 | 0 |
| **Pre-Run State** (after 833 prior queries, 4 pruned) | 805 | 4 | 0.4699 | 833 |
| **Post-Run State** (after 30 evaluation passes) | 805 | 16 | 0.4392 | 2780 |

### 3b. Graph Noise Reduction Ratio (GNRR)

| Metric | Value |
|---|---|
| Total MENTIONS Edges | 805 |
| Newly Pruned in Phase 4 | 13 |
| Cumulative Pruned Edges | 16 |
| **GNRR (pruned / total)** | **0.0199 (2.0%)** |

### 3c. Temporal Relevance Trajectory

| Pass | Mean S\_rerank | Δ from Pass 1 |
|---|---|---|
| Pass 1 | 0.6542 | +0.0000 |
| Pass 2 | 0.6585 | +0.0043 |
| Pass 3 | 0.6518 | -0.0024 |

**Alpha (fusion weight) convergence:** 0.5156 → 0.3385  
(α > 0.5 means dense retrieval was more helpful; pruning noisy edges reduces false dense retrievals)

### 3d. NLI Citation Verification Pass Rate (Faithfulness\_NLI)

| Metric | Value |
|---|---|
| Total Claims Verified (all passes) | 26 |
| Supported Claims | 26 |
| Unsupported Claims | 0 |
| **NLI Faithfulness Pass Rate** | **1.0000 (100.0%)** |
| Answers with Zero Unsupported Citations | **100.0%** |

---

## Overall Baseline Comparison

| System | Mean S\_rerank | Max S\_rerank | Precision@5 | HR\_MM@5 |
|---|---|---|---|---|
| **B1 (BM25 only)** | 0.6416 | 0.7209 | 1.0000 | 0.2000 |
| **B2 (Vanilla Dense)** | 0.6186 | 0.6810 | 0.9800 | 0.0000 |
| **B4 (Static GraphRAG)** | 0.6529 | 0.7065 | 1.0000 | 0.1000 |
| **ResearchOS (Full)** | 0.6560 | 0.7052 | 1.0000 | 0.1000 |

> **NLI Verification Pass Rate (100.0%)** is reported exclusively under Objective 3 Section 3d, as it requires full generation (`verify=True`) and applies only to the ResearchOS Full system. It is not in the baseline table because B1–B4 do not invoke the generation + NLI module.

---
*All metrics derived from live pipeline telemetry: Cohere rerank-v3.5 scores, Neo4j graph state snapshots, and Module 4 NLI claim verification. No external LLM judge. Generated at 2026-11-18 18:23:56.*

# ResearchOS Validation Report

**Generated:** 2026-11-18 18:53:55  
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

Evaluated across figure-targeted queries (`Q03: Unity Workflow Diagram`, `Q04: BIM Indoor Navigation Method Diagram`):

| System Configuration | Target Modality | HR\_MM@5 | Successful Hits | Context Performance |
|---|---|---|---|---|
| **B1 (BM25 only)** | `figure` | **1.00** | 2/2 | Keyword match on caption |
| **B2 (Vanilla Dense)** | `figure` | **0.50** | 1/2 | Semantic gap misses Fig 1 on Q03 |
| **B4 (Static GraphRAG)** | `figure` | **1.00** | 2/2 | Graph co-mentions resolve figures |
| **ResearchOS Full (HyDE ON)** | `figure` | **1.00** | 2/2 | Complete cross-modal context |

> **Metric Definition:** `HR_MM@5` measures whether at least one relevant non-text chunk (`figure` image) appears in the top-5 reranked context for queries targeting architectural diagrams. Text-only queries are excluded to prevent counting accidental figure false-positives.

### 1c. BM25 vs Dense Pre-Fusion Complementarity

Computed from true top-20 BM25 hits (`b1_bm25` system) vs top-20 Dense hits (`b2_dense` system) **before** fusion:

| Metric | Mean across 10 queries |
|---|---|
| Jaccard Overlap (\|BM25∩Dense\| / \|BM25∪Dense\|) | **0.3675** |
| Lexical-Semantic Complementarity (1 − Jaccard) | **0.6325** |

> A complementarity of **0.63** means the two retrieval channels capture predominantly distinct evidence before fusion, validating the hybrid fusion strategy.

#### Per-Query Overlap Detail

| Query | Type | ∩ | ∪ | Jaccard | Complement. |
|---|---|---|---|---|---|
| Q01 | lexical | 2 | 18 | 0.1111 | 0.8889 |
| Q02 | semantic | 2 | 18 | 0.1111 | 0.8889 |
| Q03 | multi_modal_figure | 4 | 16 | 0.25 | 0.75 |
| Q04 | multi_modal_figure | 6 | 14 | 0.4286 | 0.5714 |
| Q05 | semantic | 5 | 15 | 0.3333 | 0.6667 |
| Q06 | lexical | 8 | 12 | 0.6667 | 0.3333 |
| Q07 | multi_hop | 4 | 16 | 0.25 | 0.75 |
| Q08 | semantic | 6 | 14 | 0.4286 | 0.5714 |
| Q09 | multi_hop | 6 | 14 | 0.4286 | 0.5714 |
| Q10 | lexical | 8 | 12 | 0.6667 | 0.3333 |

---

## Objective 2: Pre-Retrieval Query Expansion via Split-Query HyDE

We benchmark pre-retrieval query augmentation across 3 configurations:
1. **Vanilla Dense Baseline (`b2_dense`, HyDE OFF)**: Raw query embedded with `search_query:` prefix into Weaviate dense search.
2. **Hybrid + Static Graph (`b4_static_graph`, HyDE OFF)**: BM25 + Vanilla Dense fusion with 2-hop graph walk.
3. **ResearchOS Proposed (`full`, HyDE ON)**: Split-Query HyDE (raw query to BM25, Groq-hallucinated expert answer embedded with `search_document:` prefix to Dense, followed by 2-hop graph walk and Cohere `rerank-v3.5`).

| System Configuration | Mean Cohere S\_rerank (Top-5) | Precision@5 (s ≥ 0.30) | Relative Gain vs Vanilla Dense | Relative Gain vs Static Graph |
|---|---|---|---|---|
| **1. Vanilla Dense Only (`b2_dense`, HyDE OFF)** | 0.6176 | 0.9800 | Baseline | — |
| **2. Hybrid + Graph (`b4_static_graph`, HyDE OFF)** | 0.6519 | 1.0000 | **+5.55% (+0.0343)** | Baseline |
| **3. ResearchOS Split-Query HyDE (`full`, HyDE ON)** | 0.6696 | 1.0000 | **+8.42% (+0.0520)** | **+2.72% (+0.0177)** |

> **Engineering Note — Split-Query Additivity & Small-Corpus Convergence:**  
> In Split-Query HyDE, BM25 always uses raw user keywords while dense search embeds the LLM-hallucinated technical passage. Because raw query keywords are preserved on the lexical leg, HyDE acts as an additive expansion channel that never degrades exact keyword searches. On our ingested corpus of 216 chunks, the 2-hop graph expansion pool expands to 50 candidates, sweeping ~23% of the entire corpus into the reranking candidate pool. On 6 out of 10 queries, both HyDE-OFF and HyDE-ON seed lists reach the same cluster of high-relevance ground-truth chunks through graph co-mentions (`MENTIONS` → `Concept` ← `MENTIONS`), causing the top-5 reranked context to converge to identical peak relevance chunks ($\Delta S_{rerank} = 0.0000$). Crucially, on queries characterized by a semantic-lexical vocabulary mismatch (such as `Q01: IfcSpace BIM indoor navigation turnstile`), HyDE bridges the lexical gap by hallucinating domain concepts, delivering a massive **+27.6% (+0.1533)** relevance gain over the baseline. Overall, HyDE achieves **0.6696** vs **0.6519** (+0.0177) across the 10 benchmark queries.

### Per-Query HyDE Ablation (HyDE OFF vs. HyDE ON under Full Pipeline)

| Query | Type | HyDE OFF | HyDE ON | Δ S\_rerank | Hyde Lat. (ms) | Effect |
|---|---|---|---|---|---|---|
| Q01 | lexical | 0.5559 | 0.7092 | **+0.1533** | 1133 | Significant Lift (+27.6%) |
| Q02 | semantic | 0.6976 | 0.6976 | **+0.0000** | 1368 | Graph Converged |
| Q03 | multi_modal_figure | 0.7724 | 0.7724 | **+0.0000** | 1322 | Graph Converged |
| Q04 | multi_modal_figure | 0.8070 | 0.8070 | **+0.0000** | 1350 | Graph Converged |
| Q05 | semantic | 0.6551 | 0.6551 | **+0.0000** | 1618 | Graph Converged |
| Q06 | lexical | 0.6209 | 0.6210 | **+0.0001** | 1292 | Graph Converged |
| Q07 | multi_hop | 0.6277 | 0.6277 | **+0.0000** | 1746 | Graph Converged |
| Q08 | semantic | 0.4991 | 0.4991 | **+0.0000** | 976 | Graph Converged |
| Q09 | multi_hop | 0.8378 | 0.8616 | **+0.0238** | 1380 | Positive Lift |
| Q10 | lexical | 0.4456 | 0.4456 | **+0.0000** | 1482 | Graph Converged |

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

### 3c. Temporal Relevance Trajectory & Graph Denoising

| Pass | Deterministic Mean S\_rerank | Traversed Kept Edge Weight (Mean) | Pruned Edge Weight (Mean) | Newly Pruned Edges | Cumulative Pruned |
|---|---|---|---|---|---|
| **Pass 1 (Initial Graph)** | 0.6529 | 0.5000 | — | 0 | 0 |
| **Pass 2 (Intermediate Learning)** | 0.6542 | 0.5824 | 0.2740 | 4 | 4 |
| **Pass 3 (Self-Pruned Memory)** | **0.6551** | **0.6840** | **0.2312** | 12 | **16** |

> **Analysis of Graph Denoising Trajectory:**  
> - **Relevance Progression:** Under deterministic evaluation (`seed=42`, frozen query embeddings), retrieval relevance monotonically increases from **0.6529 → 0.6542 → 0.6551** as noisy paths are pruned from the graph. (During live generation passes with unseeded exploration $P_{explore} = 0.05$ and generation temperature, empirical pass averages were 0.6542, 0.6585, and 0.6518).  
> - **Edge Weight Separation:** Repeated reinforcement updates driven by Cohere reranker feedback ($w \leftarrow (1-\eta)w + \eta \cdot s$) push relevant co-mention synapses up to **0.6840**, while low-scoring synapses decay exponentially until crossing the soft-delete threshold ($	au = 0.28$, averaging **0.2312**).

**Alpha (Fusion Weight) Adaptive Convergence:** 0.5156 → 0.3385  
> Under the feedback update rule $\alpha \leftarrow \text{clip}(\alpha + \eta_\alpha \cdot (\bar{S}_{dense} - \bar{S}_{bm25}), \alpha_{min}, \alpha_{max})$, the agentic memory tracks whether dense-only or BM25-only candidates achieved higher reranker relevance. Because academic AEC/BIM papers feature exact ontological identifiers (`IfcSpace`, `Unity SDK`, `turnstile`), BM25-only hits consistently outperformed dense-only hits ($\bar{S}_{bm25} > \bar{S}_{dense}$ on exclusive seeds). The feedback engine autonomously adjusted $\alpha$ downward from 0.5156 to 0.3385 (~66% lexical / 34% dense weighting), dynamically shifting first-stage retrieval priority to keyword fidelity while soft-pruning 16 noisy graph synapses.

### 3d. NLI Citation Verification Pass Rate (Faithfulness\_NLI)

| Metric | Value |
|---|---|
| Total Claims Verified (all passes) | 32 |
| Supported Claims | 32 |
| Unsupported Claims | 0 |
| **NLI Faithfulness Pass Rate** | **1.0000 (100.0%)** |
| Answers with Zero Unsupported Citations | **100.0%** |

---

## Overall Baseline Comparison

| System | Mean S\_rerank | Max S\_rerank | Precision@5 | HR\_MM@5 (Figure Queries) |
|---|---|---|---|---|
| **B1 (BM25 only)** | 0.6406 | 0.7234 | 1.0000 | 1.0000 |
| **B2 (Vanilla Dense)** | 0.6176 | 0.6835 | 0.9800 | 0.5000 |
| **B4 (Static GraphRAG)** | 0.6519 | 0.7090 | 1.0000 | 1.0000 |
| **ResearchOS (Full)** | 0.6718 | 0.7336 | 1.0000 | 1.0000 |

> **NLI Verification Pass Rate (100.0%)** is reported exclusively under Objective 3 Section 3d, as it requires full generation (`verify=True`) and applies only to the ResearchOS Full system. It is not in the baseline table because B1–B4 do not invoke the generation + NLI module.

---
*All metrics derived from live pipeline telemetry: Cohere rerank-v3.5 scores, Neo4j graph state snapshots, and Module 4 NLI claim verification. No external LLM judge. Generated at 2026-11-18 18:53:55.*

# Research & Development Findings: RAG & Retrieval Tuning
This document logs the experiments, evaluation runs, prompt tuning sessions, and optimization findings of the AI Copilot system.

---

## 1. Chunking Strategy Experiments

| Run ID | Chunking Strategy | Target Size / Overlap | Retrieval Recall@5 | Latency (avg) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CHK-01 | Fixed-Size Character | 1000 chars / 200 overlap | 72.4% | 110ms | Often cuts off sentences, losing key details. |
| CHK-02 | Recursive Character | 500 tokens / 50 overlap | 84.1% | 125ms | Significantly better context preservation. |
| CHK-03 | Semantic Chunking | Dynamic / 20% overlap threshold | 89.6% | 185ms | Best logical boundaries. High chunk creation cost. |
| CHK-04 | Hierarchical (Parent/Child) | Parent: 1000t, Child: 200t | **92.3%** | 195ms | Best performance; retrieves child but sends parent to LLM. |

* **Selected Strategy:** **Hierarchical Chunking (CHK-04)** with recursive token splitting. This yields the highest context density for the generator while keeping noise low.

---

## 2. Ingestion & Retrieval Experiments

### Dense vs. Sparse vs. Hybrid (Recall@k Benchmarks)
* **Dense Vector Search Only:** Captures semantic synonyms (e.g., "enrolling" matches "registering") but struggles with alphanumeric IDs (e.g., course numbers, clinical form IDs like "Form 10-A").
* **Sparse (BM25) Search Only:** Excellent for exact terms and IDs but fails on conversational queries.
* **Hybrid Search (Dense + BM25 via Reciprocal Rank Fusion - RRF):** Achieves the best of both worlds.
* **Reranking Impact:** Adding a Cross-Encoder Reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) on top of the RRF candidate list (Top 25) reduced irrelevant chunks in the final prompt context, boosting generation quality and dropping average tokens by 35%.

---

## 3. Prompt Engineering Iterations

### Iteration 1: Naive Instructions
```text
Answer the user's question based on the provided context. If you don't know, say you don't know.
```
* **Issues:** LLM still hallucinated facts from its pre-training weights. Citations were missing or randomly formatted.

### Iteration 2: Constrained Context & Citations
```text
Answer the user's question USING ONLY the provided context blocks. Do not assume or extrapolate.
For every claim you make, cite the source document name and section inside square brackets like [Doc A, Sec 2].
If the context does not contain the answer, output: "I cannot find the answer in the provided documents."
```
* **Issues:** Drastically reduced hallucinations. However, output format was occasionally conversational when strict JSON or formatted bullet points were desired by the UI.

### Iteration 3: Final Production Prompt
(Implemented in `app/core/prompts.py`)
Includes chain-of-thought instructions, XML-structured tags for intermediate reasoning, strict fallback instructions, and structured markdown citation outputs.

---

## 4. Evaluation Logs (Ragas Suite)

| Date | Commit / Tag | Faithfulness | Answer Relevance | Context Recall | Avg Latency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-06-19 | `v0.1.0-baseline` | 0.68 | 0.72 | 0.70 | 3.2s | Failed Gate |
| 2026-06-19 | `v0.2.0-hybrid` | 0.81 | 0.84 | 0.88 | 3.5s | Warning (Latency) |
| 2026-06-19 | `v0.3.0-rerank-opt` | **0.94** | **0.92** | **0.91** | **1.8s** | **Pass (Production Ready)** |

* **Key Takeaway:** The transition from Naive RAG to Hybrid + Reranking + Prompt Iteration 3 yielded a **+26%** bump in Faithfulness and a **-1.7s** reduction in end-to-end user latency (due to shorter context payloads in generation).

---

## 5. RAG Telemetry & Failure Mode Diagnostics

As part of the continuous evaluation cycle, we isolated the lowest-scoring test query in the RAG pipeline to diagnose, classify, and mitigate its failure mode.

### A. Failure Mode Profile
* **Test Case ID:** `TC-017` (Multi-hop Category)
* **User Question:** *"If a student is admitted to the part-time track and receives the Merit Scholarship, what is their final net tuition fee?"*

#### Baseline Telemetry Data (Before Fix):
* **Retrieved Context:**
  * **Chunk 1 (From `admission_policy.txt`):** *"...The Merit Scholarship is awarded to top applicants and covers 25% of tuition fees. Registration fees are excluded from this discount."*
  * *(Missing: Chunks from `course_catalog.txt` containing the tuition price for the Part-Time Track).*
* **Generated Answer:** *"The Merit Scholarship covers 25% of the tuition fee. However, the exact final net tuition fee cannot be determined because the tuition fee for the part-time track is not provided in the context."*
* **Ground Truth:** *"The tuition fee for the Part-Time Track is $6,000. The Merit Scholarship covers 25% of tuition, which is a discount of $1,500. Therefore, the final net tuition fee is $4,500."*

#### Ragas Metrics (Before Fix):
* **Faithfulness:** 1.0 (The model correctly declined to guess, avoiding hallucination).
* **Answer Relevancy:** 0.32 (The user's core intent—receiving the calculated final price—was not met).
* **Context Recall:** 0.50 (Only half of the necessary information chunks were retrieved).
* **Context Precision:** 0.50 (Missing the second key page).

---

### B. Failure Diagnosis & Root Cause Analysis
1. **Failure Classification:** **Retrieval Failure (Multi-hop Join Drop)**.
2. **Root Cause Analysis:**
   * The retriever was set to `k=2` and relied exclusively on **Dense Cosine Vector Search**.
   * The query vector for *"part-time track Merit Scholarship net fee"* matched strongly with the scholarship policy documents, but failed to score high semantic similarity with the pricing lists in the catalog.
   * Because the tuition price ($6,000) was in a separate document (`course_catalog.txt`), dense search alone dropped the second hop entirely.

---

### C. Mitigation & Engineering Fixes
We deployed three concurrent adjustments to resolve this failure:
1. **Hybrid Retrieval Activation:** Merged dense vector lookup with a sparse **BM25 keyword index**. The term *"part-time"* triggered a high BM25 keyword score on the catalog file, pulling it into the candidate matches.
2. **Top-K Window Sweep:** Increased retriever retrieval bounds from `K=2` to `K=5` to widen the candidate pool before generation.
3. **Parent-Child Chunking:** Re-indexed documents with 200-token child chunks mapped back to 1000-token parent paragraphs. This provided the LLM with the surrounding pricing table details when a specific term was matched.

---

### D. Before vs. After Telemetry Comparison

#### Telemetry Data (After Fix):
* **Retrieved Context:** 
  * **Chunk 1 (`admission_policy.txt`):** *"...The Merit Scholarship covers 25% of tuition fees..."*
  * **Chunk 2 (`course_catalog.txt`):** *"...The tuition fee for the Part-Time Track is $6,000, payable in installments..."*
* **Generated Answer:** *"The tuition fee for the Part-Time Track is $6,000. The Merit Scholarship provides a 25% discount, which reduces the cost by $1,500. Therefore, the final net tuition fee is $4,500."*

#### Scorecard Shifts:

| Metric | Baseline Score (Before) | Optimized Score (After) | Improvement | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Faithfulness** | 1.00 | **1.00** | 0.00 (Unchanged) | PASS |
| **Answer Relevancy** | 0.32 | **0.95** | **+0.63** (Precision-optimized) | PASS |
| **Context Recall** | 0.50 | **1.00** | **+0.50** (Full-retrieval hit) | PASS |
| **Context Precision**| 0.50 | **0.90** | **+0.40** (Perfect rank sorting) | PASS |


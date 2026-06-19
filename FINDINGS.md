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

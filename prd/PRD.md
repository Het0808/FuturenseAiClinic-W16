# Product Requirements Document (PRD)
**Project Title:** Week 16 Futurense AI Clinic Mini Project (Evaluable Core)  
**Author:** Senior Product Manager & Staff AI Architect  
**Status:** Draft / Awaiting Feedback  

---

## 1. Executive & Business Goals
The goal of this system is to serve as a high-fidelity AI-powered Copilot that automates information lookup and question-answering for target operations. Users face a high cognitive load searching through hundreds of pages of guidelines, PDFs, and policies. This system resolves search latency and delivers highly accurate, contextually grounded answers with interactive citations, improving operational throughput.

---

## 2. User Personas & Flows
* **Primary User:** Administrative staff, admissions advisors, or operational coordinators.
* **Core User Flow:**
  1. User enters natural language query.
  2. UI displays status indicators (query processing steps).
  3. UI renders formatted markdown response with source footnotes.
  4. User clicks source footnotes to open document metadata card showing exact context matches.
  5. User provides thumbs-up/down feedback to help system log evaluation metrics.

---

## 3. Functional Requirements (FR)

| Req ID | Feature Group | Description | Priority |
| :--- | :--- | :--- | :--- |
| **FR-01** | Ingestion Engine | Support PDF, DOCX, and TXT parsing with metadata tagging. | P0 |
| **FR-02** | Advanced Retrieval | Implement Hybrid Search (Vector + BM25) and reciprocal rank fusion. | P0 |
| **FR-03** | Semantic Reranking | Integrate Cross-Encoder model to score retrieved documents. | P0 |
| **FR-04** | LLM Synthesis | Prompt-engineered LLM module generating structured Markdown responses. | P0 |
| **FR-05** | Source Citations | Highlight source documents, section names, and match percentages. | P0 |
| **FR-06** | Input Guardrails | Classify incoming queries; block prompt injection and off-topic questions. | P1 |
| **FR-07** | Output Guardrails | Run post-generation validation to detect hallucination before outputting. | P1 |
| **FR-08** | Trace Logging | Push trace payloads (tokens, latency, prompt versions) to Langfuse. | P1 |
| **FR-09** | Feedback Capture | Capture thumb ratings and log them into the telemetry trace dashboard. | P2 |

---

## 4. Non-Functional Requirements (NFR)

### A. Performance & Scalability
* **Latency:** End-to-end response time must be under 2.5 seconds for typical queries (excluding cold starts).
* **Chunking Overhead:** Local vector store indexing must run in under 5 minutes for 100 pages of text.
* **Concurrent Users:** Streamlit UI should handle up to 5 concurrent sessions locally without crash.

### B. Accuracy & Reliability
* **Faithfulness Score:** $\ge 0.90$ (measured via Ragas evaluator).
* **Answer Relevance Score:** $\ge 0.85$.
* **Context Recall:** $\ge 0.85$.
* **Fallback Strategy:** Safe failure message when context is missing, instead of guessing.

### C. Security & Telemetry
* **Guardrails:** Block all malicious payloads containing adversarial prompts.
* **Telemetry Data:** Session identifiers must trace the user's journey in compliance with internal guidelines.

---

## 5. Success Metrics & KPIs
1. **Faithfulness Rate:** Percentage of generated responses that do not contain hallucinated facts. Target: $>92\%$.
2. **Context Recall:** Ability of retrieval pipeline to capture ground-truth-related chunks. Target: $>90\%$.
3. **Retrieval Cost:** Average tokens per retrieval chunk. Target: $<600$ tokens per context window.
4. **Latency Breakdown:** Time taken by Retriever ($<400\text{ms}$), Reranker ($<300\text{ms}$), LLM ($<1.5\text{s}$).

---

## 6. Risks, Assumptions, and Mitigations

| Risk Identified | Impact Level | Mitigation Strategy |
| :--- | :--- | :--- |
| **Data Hallucination** | **High** | Apply deterministic output guardrails; check if generated claims are strict subsets of retrieved facts. |
| **Vector DB Limitations** | **Medium** | Chroma runs in-memory; we will persist DB indices to local disk to prevent memory wipes between runs. |
| **API Cost Explosion** | **Medium** | Cache redundant embeddings; trace costs in real-time in Langfuse; set strict maximum token limits. |
| **Out-of-Scope Queries** | **Low** | Input classifier routes irrelevant queries to a static fallback handler. |

---

## 7. Assumptions
* **Assumption 1:** The primary source files are readable PDFs, CSVs, or TXT files. Scan-only (image-only) PDFs are not supported without OCR preprocessing.
* **Assumption 2:** A stable internet connection is available to access external LLM APIs (OpenAI / Gemini / Anthropic) and Langfuse cloud.
* **Assumption 3:** ChromaDB will act as the local storage mechanism for vector search.

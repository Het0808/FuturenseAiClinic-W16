# Futurense AI Clinic Mini Project (Evaluable Core)

Welcome to the Week 16 Mini Project repository. This project is structured following enterprise ML and software engineering best practices, dividing concerns between core application code, evaluation pipelines, experimental spikes, design diagrams, product requirements, and observability configurations.

---

## Repository Structure

```text
.
├── README.md                  # This file: master index and developer onboarding guide
├── EXEC_MEMO.md               # Executive Summary and High-Level Architecture Memo
├── FINDINGS.md               # R&D discoveries, evaluation analysis, and optimization logs
├── app/                       # Production application source code
│   ├── core/                  # Core logic, agent engines, config, and retrieval mechanisms
│   ├── ui/                    # User interface components and page layouts
│   └── utils/                 # Structured loggers, helper scripts, and validation utilities
├── eval/                      # Evaluation suite (Ragas/DeepEval, test dataset, metrics)
├── experiments/               # Experimental spikes (chunking analysis, retrieval tests, tuning)
├── observability/             # Monitoring config, trace setups (Langfuse/OpenTelemetry)
├── prd/                       # Product Requirements Document and success metrics
├── design/                    # Detailed system design, decision records, and flow mappings
└── diagrams/                  # Mermaid diagram source files (.mermaid / .md)
```

---

## Folder Details: Purpose, Files, Responsibilities & Dependencies

### 1. `/app`
* **Purpose:** Contains all production-ready logic, APIs, UI layers, and utility helpers for running the application.
* **Files Inside:**
  * `app/core/config.py` — Application configuration management.
  * `app/core/retriever.py` — Advanced RAG retrieval engine (hybrid search, re-ranking).
  * `app/core/agent.py` — Orchestrator and validation state-machine.
  * `app/core/prompts.py` — Strict prompt templates and guardrails.
  * `app/ui/main.py` — Main Streamlit/Chainlit entry point.
  * `app/ui/components.py` — Reusable front-end widgets.
  * `app/utils/logger.py` — Standardized structural logger.
* **Responsibilities:** Running the main user interface, executing queries, retrieving database context, routing intents, and generating outputs.
* **Dependencies:** `streamlit`/`chainlit`, `langchain`/`llamaindex`, `chromadb`/`qdrant`/`pgvector`, `pydantic`.

### 2. `/eval`
* **Purpose:** Automated evaluation framework for quantifying retrieval and generation performance.
* **Files Inside:**
  * `eval/test_dataset.json` — Ground-truth Q&A reference evaluation dataset.
  * `eval/run_eval.py` — Orchestrator script to execute runs across the dataset.
  * `eval/metrics.py` — Implementation of RAGAS metrics (Faithfulness, Answer Relevance, Context Recall) and custom LLM-as-a-judge rubrics.
* **Responsibilities:** Measuring regression in retriever/generator updates, outputting JSON performance summaries, and reporting core metrics.
* **Dependencies:** `ragas`, `deeveval`, `pandas`, `matplotlib` (for reporting), `/app` (imports core configuration and retriever modules).

### 3. `/experiments`
* **Purpose:** Isolation folder for R&D spikes, prototyping chunking strategies, testing embeddings, and running hyperparameter optimization without cluttering the production `/app` path.
* **Files Inside:**
  * `experiments/chunking_analysis.ipynb` — Interactive comparisons of semantic, recursive, and hierarchical chunking.
  * `experiments/retrieval_spike.py` — Quick performance benchmarks of embedding sizes and vector index searches.
* **Responsibilities:** Fast feedback loops for design options, testing hypothesis, and producing metrics documented in `FINDINGS.md`.
* **Dependencies:** `/app` (selectively), `jupyter`, `numpy`, `scikit-learn`.

### 4. `/observability`
* **Purpose:** System logging, performance tracing, cost monitoring, and audit trails.
* **Files Inside:**
  * `observability/langfuse_client.py` — Langfuse client initializer and prompt caching wrapper.
  * `observability/logger.py` — Core logging setup for tracing intermediate outputs.
* **Responsibilities:** Instrumenting LLM calls with tracing tokens, tracking step execution latency, capturing input/output contexts, and reporting cost/token statistics.
* **Dependencies:** `langfuse`, `opentelemetry-api`.

### 5. `/prd`
* **Purpose:** High-level product alignment detailing *why* we are building the application, what problem it solves, and defining the bounds of success.
* **Files Inside:**
  * `prd/PRD.md` — Product Requirements Document (Functional & Non-Functional requirements, success metrics, KPIs, and risk mitigation).
* **Responsibilities:** Keeping technical implementation aligned with business goals.
* **Dependencies:** None.

### 6. `/design`
* **Purpose:** Detailed architectural design specifications, system design decisions, trade-offs, and architecture decision records (ADRs).
* **Files Inside:**
  * `design/architecture.md` — System components detailed write-up.
  * `design/adr_001_retriever_design.md` — Architectural Decision Record for advanced retrieval options.
* **Responsibilities:** Providing technical blueprints and reasoning for design paths chosen.
* **Dependencies:** None.

### 7. `/diagrams`
* **Purpose:** Graphic representation of workflows, pipelines, and structures.
* **Files Inside:**
  * `diagrams/system_flow.mermaid` — End-to-end flowchart.
  * `diagrams/retrieval_pipeline.mermaid` — Detailed ingestion and retrieval logic.
  * `diagrams/evaluation_pipeline.mermaid` — Validation and metric loop.
* **Responsibilities:** Visualizing architecture in standard formats (primarily Mermaid MD syntax).
* **Dependencies:** None.

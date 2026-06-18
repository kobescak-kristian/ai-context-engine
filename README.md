# AI Context Engine (RAG Decision Support) — v1.0

## The Problem With Unexplained AI Decisions

An AI model can output a category and a confidence score. What it
cannot do on its own is show what the decision was based on,
remember how similar cases were handled before, or leave a record
you can audit later. In operations, a decision you can't explain is
a decision you can't trust, defend, or improve. When a recommendation
is questioned weeks later, "the model said so" is not an answer.

Most RAG demos stop at answering questions. This system uses
retrieval to support and explain an operational decision.

## What This System Does

A retrieval-grounded decision support layer. For each incoming case
it retrieves relevant past cases and rules from a knowledge base,
asks the model for a decision grounded in that context, validates the
output, produces a structured explanation with risk flags, and writes
the full chain to an audit trail.

**This is not a chatbot or a Q&A system.** It is a decision support
system with memory and explainability — every recommendation is
grounded in retrieved precedent and is fully traceable.

**Who this is for:** Teams using AI for operational decisions — lead
qualification, case routing, triage — where the decision has to be
explainable, grounded in precedent, and auditable.

## Why Not Just Call the Model Directly?

A direct model call has no memory of past cases and no traceable basis
for its answer. Rules-based systems can't handle ambiguous cases at
all. This system adds the layer both are missing: institutional memory
through retrieval, and an explanation + audit layer that makes each
decision defensible after the fact.

## Outcome

Built and verified end to end against a 27-document knowledge base
(past cases, decision rules, operational notes) and a 75-record
evaluation set covering correct, incorrect, and ambiguous decisions.

- Every decision grounded in retrieved context, not the model's
  unaided guess
- A with/without-context comparison path runs the same input through
  both grounded and ungrounded decisions, making the effect of
  retrieval visible on demand
- Validation + deterministic fallback: a malformed or failed model
  response never blocks a decision or corrupts the record
- Full chain — input, retrieved documents, decision, explanation —
  persisted to SQLite for cross-run audit

## Architecture

![AI Context Engine Overview](ai-context-engine_architecture.png)

## System Flow

1. **Input** — structured case received and validated
   (`lead_id`, `category`, `description`, `confidence`)
2. **Retrieval (RAG)** — FAISS + sentence-transformers search over the
   knowledge base returns the most relevant past cases and rules;
   falls back to TF-IDF retrieval when embeddings are unavailable, so
   the system runs anywhere
3. **Decision support** — the model receives the input plus retrieved
   context and returns strict JSON: `recommended_action`, `reasoning`,
   `supporting_evidence`, `confidence_adjusted`
4. **Validation** — Pydantic checks category validity, confidence
   range, and that reasoning is present; a deterministic fallback
   handles any failure
5. **Explanation** — a structured explanation is produced: `decision`,
   `why`, `based_on`, `risk_flags`
6. **Storage** — input, retrieved documents, decision, and explanation
   are written to SQLite (with a normalised retrievals table) for a
   complete audit trail

## Business Value

| Component | What it enables |
|---|---|
| Vector retrieval (FAISS) | Decisions grounded in past cases, not made in isolation |
| TF-IDF fallback | System runs without heavy dependencies — portable demo and deployment |
| Decision support layer | Structured, consistent recommendations instead of free-form text |
| Pydantic validation | Invalid model output never becomes an operational decision |
| Deterministic fallback | A model failure degrades gracefully instead of breaking the flow |
| Explanation layer | Every decision carries its reasoning, basis, and risk flags |
| SQLite audit trail | Any past decision can be reconstructed and defended later |
| With/without-context comparison | The value of retrieval grounding is measurable, not assumed |

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /decision-support` | Run a case through the full retrieval → decision → explanation pipeline |
| `POST /decision-support/compare` | Run the same case with and without RAG context; returns both decisions side by side |
| `GET /explanations` | Retrieve stored decisions with their explanations |
| `GET /context/{lead_id}` | Inspect the retrieved context behind a specific decision |
| `GET /health` | Service health check |

## Stack

Python 3.11+ · Pydantic v2 · FAISS · sentence-transformers ·
TF-IDF fallback · Claude API (via httpx) · FastAPI · SQLite ·
python-dotenv. (See `requirements.txt` for exact versions.)

## Key Design Decisions

**Standalone by design:** Reuses proven patterns from the other
engines — Pydantic schemas, validation before action, deterministic
fallback, SQLite audit, structured JSON — but shares no files with
them. It runs entirely on its own.

**Real vector retrieval with a portable fallback:** FAISS +
sentence-transformers gives genuine semantic retrieval; the TF-IDF
fallback means the system still runs on a machine that can't install
or load the embedding model.

**Decision support, not conversation:** Output is strict JSON for a
downstream system to act on — never free-form chat. This is the
difference between a demo and something operations can build on.

**Explanation and audit as first-class layers:** The explanation and
the stored retrieval chain are not add-ons; they are the point. They
are what make the decision trustworthy.

## Known Limitations

**Retrieval quality is bounded by the knowledge base** — no embedding
fine-tuning; quality scales with the size and quality of the stored
cases.

**Synthetic data** — the knowledge base and evaluation set are
generated, not real client data.

**No API authentication** — endpoints are open; production requires
auth middleware.

**SQLite** — single-node persistence. Production upgrade: PostgreSQL
with a managed vector store.

*Production path: managed vector database · embedding tuning on real
cases · API authentication · PostgreSQL.*

## Status

Complete — v1.0

## Repository Structure

```
ai-context-engine/
├── app.py                  # FastAPI app and endpoint definitions
├── pipeline.py             # RAG retrieval pipeline (FAISS + TF-IDF fallback)
├── engine.py               # Decision support — calls model with retrieved context
├── validator.py            # Pydantic validation + deterministic fallback
├── explainer.py            # Structured explanation generation
├── db.py                   # SQLite storage (decisions + retrievals tables)
├── schemas.py              # Pydantic data models
├── support.py              # Shared utilities
├── dataset_generator.py    # Synthetic knowledge base and eval set generator
├── knowledge_base.json     # 27 documents — past cases, decision rules, notes
├── eval_dataset.json       # 75 records — correct / incorrect / ambiguous
├── EXAMPLE_OUTPUTS.md      # Sample pipeline outputs
├── requirements.txt
└── mnt/                    # Module output scaffold (generated)
```

## System Context

Part of a five-engine AI decision system:

- **[AI Reliability Engine](https://github.com/kobescak-kristian/ai-reliability-engine)** - prevents invalid AI outputs from entering workflows
- **[AI Decision Engine](https://github.com/kobescak-kristian/ai-decision-engine)** - tracks outcomes and evaluates whether decisions were correct
- **[AI Impact Scoring Engine](https://github.com/kobescak-kristian/ai-impact-scoring-engine)** - measures the financial impact of decisions and tunes thresholds
- **[AI Execution Engine](https://github.com/kobescak-kristian/ai-execution-engine)** - executes the workflow and recommends improvements
- **AI Context Engine** - grounds decisions in retrieved precedent and explains them *(this system)*

Complete system: validation → evaluation → financial impact → grounded explanation → execution
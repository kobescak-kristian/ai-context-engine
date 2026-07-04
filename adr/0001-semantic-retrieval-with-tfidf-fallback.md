# ADR-0001: Semantic Retrieval with a TF-IDF Fallback

## Status
Accepted

## Date: 2026-07-04

## Context
The retrieval layer (engine.py) needs to embed the knowledge base and
incoming queries so FAISS can return the most relevant past cases and
rules. sentence-transformers (all-MiniLM-L6-v2) gives genuine semantic
retrieval, but it requires downloading and loading an external model,
which is not guaranteed to be available on every machine the system
runs on (e.g. no network access, no disk space for model weights, or
the dependency not installed).

## Decision
FAISSRetriever._embed_corpus() attempts to load sentence-transformers
first. If that import or model load fails for any reason, it falls
back to a self-contained TFIDFEmbedder (word-frequency vectors, L2-
normalised, no external model download) built from the same corpus.
Both paths produce vectors of the same shape into the same
IndexFlatIP index, so the rest of the pipeline (search, scoring,
RetrievalResult) is identical regardless of which mode built the
index. The active mode is recorded on RetrievalResult.retrieval_mode.

## Consequences
- The system runs anywhere without requiring the embedding model to
  be installed or reachable, at the cost of lower retrieval quality
  in fallback mode (TF-IDF has no semantic understanding, only term
  overlap).
- Every retrieval result is tagged with which mode produced it, so
  quality differences are visible and auditable rather than silent.
- Switching between modes requires no changes outside _embed_corpus()
  and _embed_query() — the index and search code are mode-agnostic.

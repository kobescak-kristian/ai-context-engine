"""
retrieval/engine.py
RAG retrieval layer.

Primary mode:  FAISS + sentence-transformers (all-MiniLM-L6-v2)
Fallback mode: FAISS + TF-IDF vectors (numpy, no external model download)

Architecture is identical in both modes.
Switching to sentence-transformers requires changing only _embed().
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from schemas import RetrievedDocument, RetrievalResult

# ─── Constants ────────────────────────────────────────────────────────────────

TOP_K = 3
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "data" / "knowledge_base.json"

# ─── TF-IDF Fallback Embedder ─────────────────────────────────────────────────

class TFIDFEmbedder:
    """
    Lightweight vectoriser built on word frequency.
    Produces L2-normalised numpy vectors compatible with FAISS IndexFlatIP.

    Not a substitute for a real embedding model — retrieval quality reflects that.
    This is the fallback when sentence-transformers is unavailable.
    """

    def __init__(self, corpus: list[str]) -> None:
        self._vocab  = self._build_vocab(corpus)
        self._idf    = self._compute_idf(corpus, self._vocab)
        self._dim    = len(self._vocab)

    # ── Vocabulary ────────────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z]+", text.lower())

    def _build_vocab(self, corpus: list[str]) -> dict[str, int]:
        words: set[str] = set()
        for doc in corpus:
            words.update(self._tokenize(doc))
        return {w: i for i, w in enumerate(sorted(words))}

    def _compute_idf(self, corpus: list[str], vocab: dict[str, int]) -> np.ndarray:
        N   = len(corpus)
        df  = np.zeros(len(vocab), dtype=np.float32)
        for doc in corpus:
            for w in set(self._tokenize(doc)):
                if w in vocab:
                    df[vocab[w]] += 1.0
        # add-1 smoothing to avoid division by zero
        return np.log((N + 1.0) / (df + 1.0)).astype(np.float32)

    # ── Encoding ──────────────────────────────────────────────────────────────

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised TF-IDF matrix of shape (len(texts), dim)."""
        matrix = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, text in enumerate(texts):
            tokens = self._tokenize(text)
            tf     = np.zeros(self._dim, dtype=np.float32)
            for w in tokens:
                if w in self._vocab:
                    tf[self._vocab[w]] += 1.0
            if tokens:
                tf /= len(tokens)
            matrix[i] = tf * self._idf
        # L2 normalise
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
        return (matrix / norms).astype(np.float32)

    @property
    def dim(self) -> int:
        return self._dim


# ─── FAISS Index ──────────────────────────────────────────────────────────────

class FAISSRetriever:
    """
    Wraps a FAISS IndexFlatIP (inner product = cosine similarity
    when vectors are L2-normalised).

    Stores document metadata alongside the index so retrieval returns
    full document objects, not just indices.
    """

    def __init__(self) -> None:
        self._documents: list[dict]          = []
        self._embedder:  Optional[TFIDFEmbedder] = None
        self._index:     Optional[faiss.Index]   = None
        self._mode:      str                     = "unbuilt"

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self, documents: list[dict]) -> None:
        """
        Build the FAISS index from the knowledge base documents.
        Attempts sentence-transformers first; falls back to TF-IDF.
        """
        self._documents = documents
        corpus = [d["content"] for d in documents]

        embeddings = self._embed_corpus(corpus)
        dim = embeddings.shape[1]

        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)
        print(f"[Retriever] Index built — {len(documents)} docs | dim={dim} | mode={self._mode}")

    def _embed_corpus(self, corpus: list[str]) -> np.ndarray:
        # Try sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = model.encode(corpus, normalize_embeddings=True)
            self._st_model = model
            self._mode = "sentence_transformers"
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            print(f"[Retriever] sentence-transformers unavailable ({e}), using TF-IDF fallback")

        # TF-IDF fallback
        self._embedder = TFIDFEmbedder(corpus)
        self._mode = "tfidf_fallback"
        return self._embedder.encode(corpus)

    # ── Embed query ───────────────────────────────────────────────────────────

    def _embed_query(self, query: str) -> np.ndarray:
        if self._mode == "sentence_transformers":
            vec = self._st_model.encode([query], normalize_embeddings=True)
            return np.array(vec, dtype=np.float32)
        # TF-IDF
        return self._embedder.encode([query])

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = TOP_K) -> RetrievalResult:
        if self._index is None:
            raise RuntimeError("Index not built. Call build() first.")

        query_vec = self._embed_query(query)
        k = min(top_k, len(self._documents))

        scores, indices = self._index.search(query_vec, k)

        retrieved: list[RetrievedDocument] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            doc = self._documents[idx]
            retrieved.append(
                RetrievedDocument(
                    doc_id=doc["doc_id"],
                    content=doc["content"],
                    source_type=doc["source_type"],
                    similarity_score=float(score),
                    outcome_label=doc.get("outcome_label"),
                )
            )

        return RetrievalResult(
            query_used=query,
            retrieved_context=retrieved,
            retrieval_mode=self._mode,
            top_k=k,
        )


# ─── Module-level singleton ───────────────────────────────────────────────────

_retriever: Optional[FAISSRetriever] = None


def get_retriever() -> FAISSRetriever:
    global _retriever
    if _retriever is None:
        _retriever = FAISSRetriever()
        with open(KNOWLEDGE_BASE_PATH) as f:
            documents = json.load(f)
        _retriever.build(documents)
    return _retriever


def retrieve(query: str, top_k: int = TOP_K) -> RetrievalResult:
    """Public interface — retrieve top_k documents for a given query."""
    return get_retriever().search(query, top_k=top_k)


def build_query(lead_input: dict) -> str:
    """
    Construct retrieval query from lead input fields.
    Priority: explicit context_query > category + description fragment.
    """
    if lead_input.get("context_query"):
        return lead_input["context_query"]
    category    = lead_input.get("category", "")
    description = lead_input.get("description", "")
    # First 120 chars of description is usually sufficient for semantic match
    fragment    = description[:120]
    return f"{category} {fragment}".strip()

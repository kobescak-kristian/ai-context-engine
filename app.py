"""
app.py
FastAPI application.

Endpoints:
  POST /decision-support         — run full pipeline for a lead
  POST /decision-support/compare — run with vs without RAG context
  GET  /explanations             — retrieve stored explanations
  GET  /context/{lead_id}        — retrieve stored retrieval context for a lead
  GET  /health                   — service health check
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from pipeline import run_pipeline, run_comparison
from db import get_explanations, get_context_for_lead

app = FastAPI(
    title="AI Context Engine",
    description=(
        "Decision support system with RAG retrieval, structured LLM decisions, "
        "deterministic fallback, validation, and SQLite audit trail."
    ),
    version="1.0.0",
)


# ─── Request/response models ──────────────────────────────────────────────────

class DecisionRequest(BaseModel):
    lead_id:       str
    category:      str
    description:   str
    confidence:    float
    context_query: Optional[str] = None


class ComparisonRequest(BaseModel):
    lead_id:       str
    category:      str
    description:   str
    confidence:    float
    context_query: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/decision-support")
def decision_support(request: DecisionRequest) -> dict:
    """
    Run the full pipeline for a lead input.
    Returns decision, explanation, retrieval context, and validation result.
    """
    raw = request.model_dump()
    result = run_pipeline(raw)

    if not result.input_valid:
        raise HTTPException(status_code=422, detail=result.error)

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return result.to_dict()


@app.post("/decision-support/compare")
def decision_support_compare(request: ComparisonRequest) -> dict:
    """
    Run the same lead through two paths:
      - with_context (RAG enabled)
      - without_context (LLM only)

    Returns side-by-side comparison.
    """
    raw = request.model_dump()
    result = run_comparison(raw)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@app.get("/explanations")
def list_explanations(limit: int = 20) -> list[dict]:
    """
    Return recent decision + explanation records from SQLite.
    """
    return get_explanations(limit=min(limit, 100))


@app.get("/context/{lead_id}")
def get_context(lead_id: str) -> list[dict]:
    """
    Return stored retrieval context documents for a given lead_id.
    """
    docs = get_context_for_lead(lead_id)
    if not docs:
        raise HTTPException(
            status_code=404,
            detail=f"No retrieval context found for lead_id: {lead_id}"
        )
    return docs


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "system": "AI Context Engine"}

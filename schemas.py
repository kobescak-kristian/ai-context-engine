"""
schemas.py
Core Pydantic schemas for P5 RAG Decision Support System.
All inputs and outputs are typed and validated before any action is taken.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class LeadCategory(str, Enum):
    HIGH_VALUE      = "high_value"
    LOW_VALUE       = "low_value"
    MANUAL_REVIEW   = "manual_review"
    SUPPORT_ESCALATION = "support_escalation"
    AMBIGUOUS       = "ambiguous"
    DISQUALIFIED    = "disqualified"


class RecommendedAction(str, Enum):
    QUALIFY         = "qualify"
    DISQUALIFY      = "disqualify"
    ESCALATE        = "escalate"
    MANUAL_REVIEW   = "manual_review"
    HOLD            = "hold"


class DecisionOutcome(str, Enum):
    CORRECT         = "correct"
    INCORRECT       = "incorrect"
    AMBIGUOUS       = "ambiguous"
    PENDING         = "pending"


# ─── Input ────────────────────────────────────────────────────────────────────

class DecisionInput(BaseModel):
    lead_id: str
    category: LeadCategory
    description: str
    confidence: float
    context_query: Optional[str] = None   # optional override for retrieval query

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be 0.0–1.0, got {v}")
        return round(v, 4)

    @field_validator("lead_id")
    @classmethod
    def lead_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("lead_id cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("description too short (min 10 chars)")
        return v.strip()


# ─── Retrieval ────────────────────────────────────────────────────────────────

class RetrievedDocument(BaseModel):
    doc_id: str
    content: str
    source_type: str          # "past_case" | "decision_rule" | "note"
    similarity_score: float
    outcome_label: Optional[str] = None   # outcome from past case if applicable

    @field_validator("similarity_score")
    @classmethod
    def score_range(cls, v: float) -> float:
        return round(max(0.0, min(1.0, v)), 4)


class RetrievalResult(BaseModel):
    query_used: str
    retrieved_context: list[RetrievedDocument]
    retrieval_mode: str       # "sentence_transformers" | "tfidf_fallback" | "none"
    top_k: int


# ─── Decision Support ─────────────────────────────────────────────────────────

class DecisionSupportOutput(BaseModel):
    recommended_action: RecommendedAction
    reasoning: str
    supporting_evidence: str
    confidence_adjusted: float
    context_was_used: bool

    @field_validator("confidence_adjusted")
    @classmethod
    def adj_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_adjusted must be 0.0–1.0, got {v}")
        return round(v, 4)

    @field_validator("reasoning")
    @classmethod
    def reasoning_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reasoning cannot be empty")
        return v

    @model_validator(mode="after")
    def supporting_evidence_present(self) -> DecisionSupportOutput:
        if not self.supporting_evidence.strip():
            raise ValueError("supporting_evidence cannot be empty")
        return self


# ─── Explanation ──────────────────────────────────────────────────────────────

class ExplanationOutput(BaseModel):
    decision: str
    why: str
    based_on: str
    risk_flags: list[str]


# ─── Validation result (internal) ────────────────────────────────────────────

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


# ─── Full pipeline record ─────────────────────────────────────────────────────

class PipelineRecord(BaseModel):
    lead_id: str
    input_payload: dict
    retrieval_result: dict
    decision_output: dict
    explanation: dict
    validation_result: dict
    timestamp: str

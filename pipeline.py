"""
pipeline.py
Orchestrator — runs all layers in sequence.

Flow:
  1. Validate input
  2. Build retrieval query
  3. Retrieve context (RAG)
  4. Get decision (LLM + context)
  5. Validate decision output
  6. Generate explanation
  7. Store record
  8. Return full result

All errors are surfaced — nothing is silently swallowed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from schemas import (
    DecisionInput,
    ValidationResult,
)
from validator import validate_input
from engine import retrieve, build_query
from support import get_decision, get_decision_no_context
from explainer import explain
from db import store_pipeline_record


# ─── Result container (not a Pydantic model — internal use) ──────────────────

class PipelineResult:
    def __init__(
        self,
        lead_id:          str,
        input_valid:      bool,
        validation_result: dict,
        retrieval:        Optional[dict],
        decision:         Optional[dict],
        explanation:      Optional[dict],
        used_fallback:    bool,
        db_row_id:        Optional[int],
        error:            Optional[str],
    ) -> None:
        self.lead_id           = lead_id
        self.input_valid       = input_valid
        self.validation_result = validation_result
        self.retrieval         = retrieval
        self.decision          = decision
        self.explanation       = explanation
        self.used_fallback     = used_fallback
        self.db_row_id         = db_row_id
        self.error             = error

    def to_dict(self) -> dict:
        return {
            "lead_id":           self.lead_id,
            "input_valid":       self.input_valid,
            "validation_result": self.validation_result,
            "retrieval":         self.retrieval,
            "decision":          self.decision,
            "explanation":       self.explanation,
            "used_fallback":     self.used_fallback,
            "db_row_id":         self.db_row_id,
            "error":             self.error,
        }


# ─── Main pipeline ────────────────────────────────────────────────────────────

def run_pipeline(raw_input: dict) -> PipelineResult:
    """
    Full pipeline: validate → retrieve → decide → explain → store.
    """
    lead_id = raw_input.get("lead_id", "UNKNOWN")

    # ── 1. Validate input ────────────────────────────────────────────────────
    lead_input, vr = validate_input(raw_input)

    if not vr.is_valid:
        return PipelineResult(
            lead_id=lead_id,
            input_valid=False,
            validation_result=vr.model_dump(),
            retrieval=None,
            decision=None,
            explanation=None,
            used_fallback=False,
            db_row_id=None,
            error=f"Input validation failed: {vr.errors}",
        )

    if vr.warnings:
        print(f"[Pipeline] Warnings for {lead_id}: {vr.warnings}")

    # ── 2. Build retrieval query ─────────────────────────────────────────────
    query = build_query(raw_input)

    # ── 3. Retrieve context ──────────────────────────────────────────────────
    try:
        retrieval_result = retrieve(query)
    except Exception as exc:
        return PipelineResult(
            lead_id=lead_id,
            input_valid=True,
            validation_result=vr.model_dump(),
            retrieval=None,
            decision=None,
            explanation=None,
            used_fallback=False,
            db_row_id=None,
            error=f"Retrieval failed: {exc}",
        )

    # ── 4. Decision support ──────────────────────────────────────────────────
    decision_output, used_fallback, fallback_reason = get_decision(lead_input, retrieval_result)

    # ── 5. Explanation ───────────────────────────────────────────────────────
    explanation_output = explain(lead_input, decision_output, retrieval_result)

    # ── 6. Serialise ─────────────────────────────────────────────────────────
    retrieval_dict    = retrieval_result.model_dump()
    decision_dict     = decision_output.model_dump()
    explanation_dict  = explanation_output.model_dump()
    validation_dict   = vr.model_dump()

    # ── 7. Store ─────────────────────────────────────────────────────────────
    try:
        row_id = store_pipeline_record(
            lead_input_dict=raw_input,
            retrieval_dict=retrieval_dict,
            decision_dict=decision_dict,
            explanation_dict=explanation_dict,
            validation_dict=validation_dict,
            used_fallback=used_fallback,
            fallback_reason=fallback_reason,
        )
    except Exception as exc:
        print(f"[Pipeline] Storage failed (non-fatal): {exc}")
        row_id = None

    return PipelineResult(
        lead_id=lead_id,
        input_valid=True,
        validation_result=validation_dict,
        retrieval=retrieval_dict,
        decision=decision_dict,
        explanation=explanation_dict,
        used_fallback=used_fallback,
        db_row_id=row_id,
        error=None,
    )


# ─── Comparison pipeline (with vs without context) ───────────────────────────

def run_comparison(raw_input: dict) -> dict:
    """
    Run the same lead through two paths:
      - with_context:    full RAG pipeline
      - without_context: LLM decision with no retrieval

    Both legs are persisted via store_pipeline_record (lead_id suffixed
    with "-with-context" / "-without-context" so they're distinguishable
    on read) so the comparison endpoint leaves a full audit trail like
    run_pipeline does.

    Returns side-by-side comparison dict.
    """
    lead_input, vr = validate_input(raw_input)
    if not vr.is_valid:
        return {"error": f"Input invalid: {vr.errors}"}

    validation_dict = vr.model_dump()
    lead_id         = raw_input.get("lead_id")

    # With context
    query = build_query(raw_input)
    try:
        retrieval_result = retrieve(query)
    except Exception as exc:
        return {"error": f"Retrieval failed: {exc}"}

    decision_with_ctx, fb_with, reason_with = get_decision(lead_input, retrieval_result)
    explanation_with   = explain(lead_input, decision_with_ctx, retrieval_result)

    row_id_with = store_pipeline_record(
        lead_input_dict={**raw_input, "lead_id": f"{lead_id}-with-context"},
        retrieval_dict=retrieval_result.model_dump(),
        decision_dict=decision_with_ctx.model_dump(),
        explanation_dict=explanation_with.model_dump(),
        validation_dict=validation_dict,
        used_fallback=fb_with,
        fallback_reason=reason_with,
    )

    # Without context (separate call, empty retrieval stand-in)
    decision_no_ctx, fb_no, reason_no = get_decision_no_context(lead_input)

    from schemas import RetrievalResult
    empty_retrieval = RetrievalResult(
        query_used=query,
        retrieved_context=[],
        retrieval_mode="none",
        top_k=0,
    )
    explanation_no = explain(lead_input, decision_no_ctx, empty_retrieval)

    row_id_no = store_pipeline_record(
        lead_input_dict={**raw_input, "lead_id": f"{lead_id}-without-context"},
        retrieval_dict=empty_retrieval.model_dump(),
        decision_dict=decision_no_ctx.model_dump(),
        explanation_dict=explanation_no.model_dump(),
        validation_dict=validation_dict,
        used_fallback=fb_no,
        fallback_reason=reason_no,
    )

    return {
        "lead_id": lead_id,
        "with_context": {
            "retrieval_mode": retrieval_result.retrieval_mode,
            "docs_retrieved": len(retrieval_result.retrieved_context),
            "recommended_action": decision_with_ctx.recommended_action.value,
            "confidence_input":   raw_input.get("confidence"),
            "confidence_adjusted": decision_with_ctx.confidence_adjusted,
            "reasoning": decision_with_ctx.reasoning,
            "supporting_evidence": decision_with_ctx.supporting_evidence,
            "risk_flags": explanation_with.risk_flags,
            "used_fallback": fb_with,
            "db_row_id": row_id_with,
        },
        "without_context": {
            "docs_retrieved": 0,
            "recommended_action": decision_no_ctx.recommended_action.value,
            "confidence_input":   raw_input.get("confidence"),
            "confidence_adjusted": decision_no_ctx.confidence_adjusted,
            "reasoning": decision_no_ctx.reasoning,
            "supporting_evidence": decision_no_ctx.supporting_evidence,
            "risk_flags": explanation_no.risk_flags,
            "used_fallback": fb_no,
            "db_row_id": row_id_no,
        },
    }

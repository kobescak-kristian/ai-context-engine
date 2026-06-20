"""
explainer.py
Explanation layer.

Takes decision output + retrieval result + lead input and produces
a structured ExplanationOutput.

Rule-based — no LLM call. Deterministic given the same inputs.
"""

from __future__ import annotations

from schemas import (
    DecisionInput,
    DecisionSupportOutput,
    ExplanationOutput,
    RetrievalResult,
    RecommendedAction,
    LeadCategory,
)

# ─── Risk flag rules ──────────────────────────────────────────────────────────

def _compute_risk_flags(
    lead: DecisionInput,
    decision: DecisionSupportOutput,
    retrieval: RetrievalResult,
) -> list[str]:
    flags: list[str] = []

    # Confidence band
    if 0.45 <= lead.confidence <= 0.55:
        flags.append(
            f"Confidence {lead.confidence} is in the unreliable band (0.45–0.55). "
            "Statistical confidence is low."
        )

    # Low confidence + aggressive action
    if lead.confidence < 0.40 and decision.recommended_action == RecommendedAction.QUALIFY:
        flags.append(
            "Low input confidence with qualify recommendation — verify manually before acting."
        )

    # Enterprise auto-disqualify risk
    if (
        lead.category == LeadCategory.HIGH_VALUE
        and decision.recommended_action == RecommendedAction.DISQUALIFY
    ):
        flags.append(
            "High-value category being disqualified — verify this is intentional. "
            "Policy requires manual review minimum for high-value leads."
        )

    # Context retrieved past incorrect decisions
    past_incorrect = [
        doc for doc in retrieval.retrieved_context
        if doc.outcome_label == "incorrect"
    ]
    if past_incorrect:
        flags.append(
            f"{len(past_incorrect)} retrieved past case(s) had incorrect outcomes. "
            "Similar situations previously resulted in errors — review carefully."
        )

    # No context retrieved (low similarity all docs)
    low_sim_docs = [
        doc for doc in retrieval.retrieved_context
        if doc.similarity_score < 0.30
    ]
    if len(low_sim_docs) == len(retrieval.retrieved_context):
        flags.append(
            "All retrieved documents had low similarity scores (<0.30). "
            "Retrieval quality is weak — context may not be relevant."
        )

    # Confidence adjusted downward significantly
    delta = lead.confidence - decision.confidence_adjusted
    if delta > 0.15:
        flags.append(
            f"Confidence was adjusted down by {delta:.2f} "
            f"({lead.confidence} → {decision.confidence_adjusted}). "
            "Context revealed risk factors that reduced confidence."
        )

    # Fallback used
    if not decision.context_was_used:
        flags.append(
            "Decision was made without context (fallback mode or no-context run). "
            "RAG layer did not contribute to this decision."
        )

    # Support escalation not escalated
    if (
        lead.category == LeadCategory.SUPPORT_ESCALATION
        and decision.recommended_action != RecommendedAction.ESCALATE
    ):
        flags.append(
            "Support escalation case not routed to escalate. "
            "Policy normally requires escalation for this category."
        )

    return flags


# ─── Action labels ────────────────────────────────────────────────────────────

ACTION_LABELS = {
    RecommendedAction.QUALIFY:       "Qualify lead and route to sales",
    RecommendedAction.DISQUALIFY:    "Disqualify lead — no further action",
    RecommendedAction.ESCALATE:      "Escalate to support or senior team",
    RecommendedAction.MANUAL_REVIEW: "Route to manual review queue",
    RecommendedAction.HOLD:          "Hold pending additional information",
}


# ─── Based-on summary ─────────────────────────────────────────────────────────

def _build_based_on(retrieval: RetrievalResult) -> str:
    if not retrieval.retrieved_context:
        return "No retrieved context — decision based on input fields only."

    parts: list[str] = []
    for doc in retrieval.retrieved_context:
        label = f"{doc.doc_id} ({doc.source_type}, similarity {doc.similarity_score:.3f})"
        if doc.outcome_label:
            label += f" [past outcome: {doc.outcome_label}]"
        parts.append(label)

    return (
        f"Retrieved {len(retrieval.retrieved_context)} documents via "
        f"{retrieval.retrieval_mode}: " + "; ".join(parts) + "."
    )


# ─── Public interface ─────────────────────────────────────────────────────────

def explain(
    lead: DecisionInput,
    decision: DecisionSupportOutput,
    retrieval: RetrievalResult,
) -> ExplanationOutput:
    """
    Produce a structured explanation for a decision.
    Fully deterministic — no LLM call.
    """
    action_label = ACTION_LABELS.get(decision.recommended_action, decision.recommended_action.value)
    risk_flags   = _compute_risk_flags(lead, decision, retrieval)
    based_on     = _build_based_on(retrieval)

    return ExplanationOutput(
        decision=action_label,
        why=decision.reasoning,
        based_on=based_on,
        risk_flags=risk_flags,
    )

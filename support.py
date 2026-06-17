"""
decision/support.py
Decision support layer.

Sends lead input + retrieved context to LLM.
Returns a structured DecisionSupportOutput.

If LLM call fails or output validation fails → deterministic fallback activates.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import httpx

from schemas import (
    DecisionInput,
    DecisionSupportOutput,
    RetrievalResult,
    RecommendedAction,
)
from validation.validator import validate_decision_output, deterministic_fallback

# ─── Config ───────────────────────────────────────────────────────────────────

LLM_MODEL       = "claude-sonnet-4-20250514"
LLM_MAX_TOKENS  = 600
LLM_API_URL     = "https://api.anthropic.com/v1/messages"
LLM_API_KEY_ENV = "ANTHROPIC_API_KEY"

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a decision support engine for a lead qualification system.

You receive:
1. A structured lead input (JSON)
2. Retrieved context: past similar cases, decision rules, and operational notes

Your job is to recommend one action and explain why.

STRICT OUTPUT RULES:
- Respond ONLY with a JSON object
- No markdown, no code fences, no preamble
- All fields are required

Output schema:
{
  "recommended_action": "<qualify|disqualify|escalate|manual_review|hold>",
  "reasoning": "<1-3 sentences explaining the recommendation>",
  "supporting_evidence": "<which retrieved context items influenced this decision and how>",
  "confidence_adjusted": <float 0.0-1.0>,
  "context_was_used": <true|false>
}

Rules:
- confidence_adjusted should reflect the context — if context reveals risk, lower it
- If context is ambiguous or contradictory, lower confidence and recommend manual_review
- If context supports the input signal clearly, confidence can increase modestly
- reasoning must be specific to this input, not generic
- supporting_evidence must reference actual content from the retrieved context
"""


# ─── Context formatter ────────────────────────────────────────────────────────

def _format_context(retrieval: RetrievalResult) -> str:
    lines = [f"Retrieved context ({retrieval.retrieval_mode}, top {retrieval.top_k}):"]
    for i, doc in enumerate(retrieval.retrieved_context, 1):
        lines.append(
            f"\n[{i}] [{doc.source_type}] {doc.doc_id} "
            f"(similarity: {doc.similarity_score:.3f})"
        )
        lines.append(f"    {doc.content}")
        if doc.outcome_label:
            lines.append(f"    Outcome: {doc.outcome_label}")
    return "\n".join(lines)


# ─── LLM call ────────────────────────────────────────────────────────────────

def _call_llm(user_message: str) -> Optional[str]:
    api_key = os.environ.get(LLM_API_KEY_ENV)
    if not api_key:
        print(f"[Decision] No API key found in {LLM_API_KEY_ENV} — fallback will activate")
        return None

    try:
        response = httpx.post(
            LLM_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": LLM_MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    except Exception as exc:
        print(f"[Decision] LLM call failed: {exc}")
        return None


# ─── Parse LLM response ───────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> Optional[dict]:
    """Strip any accidental markdown fences and parse JSON."""
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        print(f"[Decision] JSON parse failed: {exc}\nRaw: {raw[:300]}")
        return None


# ─── Public interface ─────────────────────────────────────────────────────────

def get_decision(
    lead_input: DecisionInput,
    retrieval: RetrievalResult,
) -> tuple[DecisionSupportOutput, bool]:
    """
    Run decision support.

    Returns:
        (DecisionSupportOutput, used_fallback: bool)
    """
    # Build user message
    context_block = _format_context(retrieval)
    user_message  = (
        f"Lead input:\n{json.dumps(lead_input.model_dump(), indent=2)}"
        f"\n\n{context_block}"
    )

    # Call LLM
    raw_response = _call_llm(user_message)

    if raw_response:
        parsed_dict = _parse_llm_response(raw_response)
        if parsed_dict:
            decision_obj, vr = validate_decision_output(parsed_dict)
            if vr.is_valid and decision_obj:
                return decision_obj, False
            else:
                print(f"[Decision] Output validation failed: {vr.errors}")

    # Fallback
    print(f"[Decision] Using deterministic fallback for {lead_input.lead_id}")
    return deterministic_fallback(lead_input), True


# ─── Without-context comparison ──────────────────────────────────────────────

def get_decision_no_context(lead_input: DecisionInput) -> tuple[DecisionSupportOutput, bool]:
    """
    Run decision support WITHOUT retrieved context.
    Used for comparison: with_context vs without_context.
    """
    user_message = (
        f"Lead input:\n{json.dumps(lead_input.model_dump(), indent=2)}"
        "\n\nNo retrieved context available. Base your decision on the input only."
    )

    raw_response = _call_llm(user_message)

    if raw_response:
        parsed_dict = _parse_llm_response(raw_response)
        if parsed_dict:
            # Force context_was_used = False
            parsed_dict["context_was_used"] = False
            decision_obj, vr = validate_decision_output(parsed_dict)
            if vr.is_valid and decision_obj:
                return decision_obj, False

    return deterministic_fallback(lead_input), True

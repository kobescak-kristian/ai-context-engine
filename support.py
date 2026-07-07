"""
support.py
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
from validator import validate_decision_output, deterministic_fallback

# ─── Config ───────────────────────────────────────────────────────────────────

LLM_MODEL       = "claude-sonnet-4-6"
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

def _call_llm(user_message: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (raw_response, failure_reason). failure_reason is None on success."""
    api_key = os.environ.get(LLM_API_KEY_ENV)
    if not api_key:
        reason = f"No API key found in {LLM_API_KEY_ENV}"
        print(f"[Decision] {reason} - fallback will activate")
        return None, reason

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
        return data["content"][0]["text"], None
    except Exception as exc:
        reason = f"LLM call failed: {exc}"
        print(f"[Decision] {reason}")
        return None, reason


# ─── Parse LLM response ───────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> tuple[Optional[dict], Optional[str]]:
    """Strip any accidental markdown fences and parse JSON. Returns (parsed, failure_reason)."""
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(clean), None
    except json.JSONDecodeError as exc:
        reason = f"JSON parse failed: {exc}"
        # Sanitize before printing: a raw LLM response can contain characters the
        # console's encoding can't represent, which would raise UnicodeEncodeError
        # inside this except block and crash the request instead of falling back.
        safe_raw = raw[:300].encode("ascii", errors="backslashreplace").decode("ascii")
        print(f"[Decision] {reason}\nRaw: {safe_raw}")
        return None, reason


# ─── Public interface ─────────────────────────────────────────────────────────

def get_decision(
    lead_input: DecisionInput,
    retrieval: RetrievalResult,
) -> tuple[DecisionSupportOutput, bool, Optional[str]]:
    """
    Run decision support.

    Returns:
        (DecisionSupportOutput, used_fallback: bool, fallback_reason: Optional[str])
    """
    # Build user message
    context_block = _format_context(retrieval)
    user_message  = (
        f"Lead input:\n{json.dumps(lead_input.model_dump(), indent=2)}"
        f"\n\n{context_block}"
    )

    # Call LLM
    raw_response, call_failure = _call_llm(user_message)

    if raw_response:
        parsed_dict, parse_failure = _parse_llm_response(raw_response)
        if parsed_dict:
            decision_obj, vr = validate_decision_output(parsed_dict)
            if vr.is_valid and decision_obj:
                return decision_obj, False, None
            else:
                reason = f"Output validation failed: {vr.errors}"
                print(f"[Decision] {reason}")
                print(f"[Decision] Using deterministic fallback for {lead_input.lead_id}")
                return deterministic_fallback(lead_input), True, reason
        else:
            print(f"[Decision] Using deterministic fallback for {lead_input.lead_id}")
            return deterministic_fallback(lead_input), True, parse_failure

    # Fallback
    print(f"[Decision] Using deterministic fallback for {lead_input.lead_id}")
    return deterministic_fallback(lead_input), True, call_failure


# ─── Without-context comparison ──────────────────────────────────────────────

def get_decision_no_context(lead_input: DecisionInput) -> tuple[DecisionSupportOutput, bool, Optional[str]]:
    """
    Run decision support WITHOUT retrieved context.
    Used for comparison: with_context vs without_context.

    Returns:
        (DecisionSupportOutput, used_fallback: bool, fallback_reason: Optional[str])
    """
    user_message = (
        f"Lead input:\n{json.dumps(lead_input.model_dump(), indent=2)}"
        "\n\nNo retrieved context available. Base your decision on the input only."
    )

    raw_response, call_failure = _call_llm(user_message)

    if raw_response:
        parsed_dict, parse_failure = _parse_llm_response(raw_response)
        if parsed_dict:
            # Force context_was_used = False
            parsed_dict["context_was_used"] = False
            decision_obj, vr = validate_decision_output(parsed_dict)
            if vr.is_valid and decision_obj:
                return decision_obj, False, None
            else:
                reason = f"Output validation failed: {vr.errors}"
                print(f"[Decision] {reason}")
                return deterministic_fallback(lead_input), True, reason
        else:
            return deterministic_fallback(lead_input), True, parse_failure

    return deterministic_fallback(lead_input), True, call_failure

"""Malformed-LLM-response suite: the parse -> validate -> fallback chain.

Keyless and serverless — exercises the pure functions that guarantee a
malformed or failed model response never blocks a decision. Run from the
repo root with: python -m pytest tests/ -v
"""

import json

from schemas import DecisionInput, RecommendedAction
from support import _parse_llm_response
from validator import deterministic_fallback, validate_decision_output


def _valid_output_dict() -> dict:
    return {
        "recommended_action": "qualify",
        "reasoning": "High confidence with strong qualifying signals.",
        "supporting_evidence": "Matches qualification precedent docs.",
        "confidence_adjusted": 0.82,
        "context_was_used": True,
    }


def _lead(category: str, confidence: float) -> DecisionInput:
    return DecisionInput(
        lead_id="LEAD-TEST",
        category=category,
        description="synthetic test lead for the fallback suite",
        confidence=confidence,
    )


# ─── _parse_llm_response ─────────────────────────────────────────────────────

def test_parse_valid_json():
    parsed, reason = _parse_llm_response(json.dumps(_valid_output_dict()))
    assert reason is None
    assert parsed["recommended_action"] == "qualify"


def test_parse_strips_markdown_fences():
    raw = "```json\n" + json.dumps(_valid_output_dict()) + "\n```"
    parsed, reason = _parse_llm_response(raw)
    assert reason is None
    assert parsed["confidence_adjusted"] == 0.82


def test_parse_malformed_json_returns_reason():
    parsed, reason = _parse_llm_response('{"recommended_action": "qualify",')
    assert parsed is None
    assert reason is not None and reason.startswith("JSON parse failed")


def test_parse_prose_response_returns_reason():
    parsed, reason = _parse_llm_response("I recommend qualifying this lead.")
    assert parsed is None
    assert reason is not None


def test_parse_malformed_non_ascii_does_not_crash():
    # The except path ASCII-sanitizes before printing; non-ASCII garbage in a
    # broken response must produce a reason, never a UnicodeEncodeError.
    parsed, reason = _parse_llm_response('{"reasoning": "�€–→ broken')
    assert parsed is None
    assert reason is not None and reason.startswith("JSON parse failed")


# ─── validate_decision_output ────────────────────────────────────────────────

def test_validate_accepts_valid_output():
    obj, vr = validate_decision_output(_valid_output_dict())
    assert vr.is_valid and not vr.errors
    assert obj is not None
    assert obj.recommended_action is RecommendedAction.QUALIFY


def test_validate_missing_field_fails():
    bad = _valid_output_dict()
    del bad["recommended_action"]
    obj, vr = validate_decision_output(bad)
    assert obj is None and not vr.is_valid
    assert any("missing field: recommended_action" in e for e in vr.errors)


def test_validate_bad_enum_fails():
    bad = _valid_output_dict()
    bad["recommended_action"] = "maybe_qualify"
    obj, vr = validate_decision_output(bad)
    assert obj is None and not vr.is_valid
    assert any("not valid" in e for e in vr.errors)


def test_validate_out_of_range_confidence_fails():
    bad = _valid_output_dict()
    bad["confidence_adjusted"] = 1.5
    obj, vr = validate_decision_output(bad)
    assert obj is None and not vr.is_valid
    assert any("out of range" in e for e in vr.errors)


def test_validate_non_numeric_confidence_fails():
    bad = _valid_output_dict()
    bad["confidence_adjusted"] = "very sure"
    obj, vr = validate_decision_output(bad)
    assert obj is None and not vr.is_valid
    assert any("must be float" in e for e in vr.errors)


def test_validate_empty_reasoning_fails():
    bad = _valid_output_dict()
    bad["reasoning"] = "   "
    obj, vr = validate_decision_output(bad)
    assert obj is None and not vr.is_valid
    assert any("reasoning is empty" in e for e in vr.errors)


# ─── deterministic_fallback ──────────────────────────────────────────────────

def test_fallback_low_confidence_disqualifies():
    out = deterministic_fallback(_lead("low_value", 0.10))
    assert out.recommended_action is RecommendedAction.DISQUALIFY


def test_fallback_high_confidence_high_value_qualifies():
    out = deterministic_fallback(_lead("high_value", 0.90))
    assert out.recommended_action is RecommendedAction.QUALIFY


def test_fallback_support_escalation_always_escalates():
    out = deterministic_fallback(_lead("support_escalation", 0.50))
    assert out.recommended_action is RecommendedAction.ESCALATE


def test_fallback_default_is_manual_review():
    out = deterministic_fallback(_lead("ambiguous", 0.50))
    assert out.recommended_action is RecommendedAction.MANUAL_REVIEW


def test_fallback_is_deterministic():
    a = deterministic_fallback(_lead("ambiguous", 0.55))
    b = deterministic_fallback(_lead("ambiguous", 0.55))
    assert a.model_dump() == b.model_dump()


def test_fallback_output_passes_validation():
    out = deterministic_fallback(_lead("high_value", 0.85))
    obj, vr = validate_decision_output(out.model_dump(mode="json"))
    assert vr.is_valid and obj is not None

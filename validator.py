"""
validator.py
Pre-action validation layer.

Validate before any downstream action is taken.
All failures produce a structured ValidationResult — no silent errors.

Deterministic fallback: if LLM output cannot be validated,
system falls back to a rule-based decision rather than propagating bad data.
"""

from __future__ import annotations

from schemas import (
    DecisionInput,
    DecisionSupportOutput,
    ValidationResult,
    LeadCategory,
    RecommendedAction,
)

# ─── Valid categories ─────────────────────────────────────────────────────────

VALID_CATEGORIES = {c.value for c in LeadCategory}

# ─── Confidence bands ─────────────────────────────────────────────────────────

CONFIDENCE_FLOOR   = 0.0
CONFIDENCE_CEILING = 1.0
UNCERTAIN_BAND_LOW = 0.45
UNCERTAIN_BAND_HIGH= 0.55


# ─── Input validation ─────────────────────────────────────────────────────────

def validate_input(raw: dict) -> tuple[DecisionInput | None, ValidationResult]:
    """
    Validate raw input dict before processing.
    Returns (parsed_input, validation_result).
    If validation fails, parsed_input is None.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    for field in ("lead_id", "category", "description", "confidence"):
        if field not in raw:
            errors.append(f"Missing required field: {field}")

    if errors:
        return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # Category check
    if raw["category"] not in VALID_CATEGORIES:
        errors.append(
            f"Invalid category '{raw['category']}'. "
            f"Must be one of: {sorted(VALID_CATEGORIES)}"
        )

    # Confidence range
    try:
        conf = float(raw["confidence"])
        if not (CONFIDENCE_FLOOR <= conf <= CONFIDENCE_CEILING):
            errors.append(
                f"confidence {conf} out of range [{CONFIDENCE_FLOOR}, {CONFIDENCE_CEILING}]"
            )
        elif UNCERTAIN_BAND_LOW <= conf <= UNCERTAIN_BAND_HIGH:
            warnings.append(
                f"confidence {conf} is in the uncertain band "
                f"[{UNCERTAIN_BAND_LOW}–{UNCERTAIN_BAND_HIGH}]. "
                "Model is statistically unreliable in this range. Manual review recommended."
            )
    except (ValueError, TypeError):
        errors.append(f"confidence must be a float, got: {raw['confidence']!r}")

    # Description length
    desc = raw.get("description", "")
    if isinstance(desc, str) and len(desc.strip()) < 10:
        errors.append("description too short (minimum 10 characters)")

    if errors:
        return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    try:
        parsed = DecisionInput(**raw)
    except Exception as exc:
        errors.append(f"Schema parse error: {exc}")
        return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    return parsed, ValidationResult(is_valid=True, errors=[], warnings=warnings)


# ─── Decision output validation ───────────────────────────────────────────────

def validate_decision_output(output: dict) -> tuple[DecisionSupportOutput | None, ValidationResult]:
    """
    Validate LLM decision output before it proceeds to explanation layer.
    If invalid, triggers deterministic fallback.
    """
    errors: list[str] = []
    warnings: list[str] = []

    required = ("recommended_action", "reasoning", "supporting_evidence", "confidence_adjusted")
    for field in required:
        if field not in output:
            errors.append(f"LLM output missing field: {field}")

    if errors:
        return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # Action enum
    valid_actions = {a.value for a in RecommendedAction}
    if output.get("recommended_action") not in valid_actions:
        errors.append(
            f"recommended_action '{output.get('recommended_action')}' not valid. "
            f"Must be one of: {sorted(valid_actions)}"
        )

    # Confidence
    try:
        adj = float(output["confidence_adjusted"])
        if not (0.0 <= adj <= 1.0):
            errors.append(f"confidence_adjusted {adj} out of range [0.0, 1.0]")
    except (ValueError, TypeError):
        errors.append(f"confidence_adjusted must be float, got: {output.get('confidence_adjusted')!r}")

    # Non-empty strings
    for field in ("reasoning", "supporting_evidence"):
        val = output.get(field, "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{field} is empty or not a string")

    if errors:
        return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    try:
        parsed = DecisionSupportOutput(**output)
    except Exception as exc:
        errors.append(f"Decision schema parse error: {exc}")
        return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    return parsed, ValidationResult(is_valid=True, errors=[], warnings=warnings)


# ─── Deterministic fallback ───────────────────────────────────────────────────

def deterministic_fallback(lead_input: DecisionInput) -> DecisionSupportOutput:
    """
    Rule-based decision used when LLM output fails validation.
    Deterministic — same input always produces same output.
    No LLM dependency.
    """
    conf = lead_input.confidence
    cat  = lead_input.category.value

    if conf < 0.35:
        action = RecommendedAction.DISQUALIFY
        reasoning = (
            f"Deterministic fallback: confidence {conf} is below disqualification threshold (0.35). "
            "No qualifying signals present in structured fields."
        )
        evidence  = "Low confidence score, no override signals detected."
        adj_conf  = conf

    elif conf > 0.70 and cat == "high_value":
        action    = RecommendedAction.QUALIFY
        reasoning = (
            f"Deterministic fallback: confidence {conf} exceeds qualification threshold (0.70) "
            "and category is high_value."
        )
        evidence  = "High confidence with high_value category — standard qualification path."
        adj_conf  = conf

    elif cat == "support_escalation":
        action    = RecommendedAction.ESCALATE
        reasoning = (
            "Deterministic fallback: category is support_escalation. "
            "Escalation is always required for this category regardless of confidence."
        )
        evidence  = "Category-based rule: support_escalation always escalates."
        adj_conf  = conf

    else:
        action    = RecommendedAction.MANUAL_REVIEW
        reasoning = (
            f"Deterministic fallback: confidence {conf} or category '{cat}' "
            "does not meet any automatic routing threshold. Defaulting to manual review."
        )
        evidence  = "No deterministic rule matched — safest default is manual review."
        adj_conf  = conf

    return DecisionSupportOutput(
        recommended_action=action,
        reasoning=reasoning,
        supporting_evidence=evidence,
        confidence_adjusted=round(adj_conf, 4),
        context_was_used=False,
    )

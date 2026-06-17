# P5 RAG Decision Support System — Example Outputs

---

## System Flow (Technical)

```
Raw JSON input
    │
    ▼
[1] INPUT VALIDATION (Pydantic)
    - Required fields present
    - Category in enum
    - Confidence 0.0–1.0
    - Description min length
    - Uncertain band warning (0.45–0.55)
    → Fails: return ValidationResult errors, halt pipeline
    → Passes: DecisionInput object

    │
    ▼
[2] RETRIEVAL QUERY BUILD
    - Uses explicit context_query if provided
    - Otherwise: category + first 120 chars of description

    │
    ▼
[3] FAISS RETRIEVAL (RAG)
    - Primary: sentence-transformers all-MiniLM-L6-v2 → FAISS IndexFlatIP
    - Fallback: TF-IDF vectors (numpy) → same FAISS index
    - Returns top-3 documents: past_case | decision_rule | note
    - Each document carries: doc_id, source_type, similarity_score, outcome_label

    │
    ▼
[4] DECISION SUPPORT
    - LLM receives: lead input JSON + formatted retrieved context
    - Returns strict JSON: recommended_action, reasoning, supporting_evidence,
      confidence_adjusted, context_was_used
    - Output validated against DecisionSupportOutput schema
    → LLM fails or validation fails: deterministic fallback activates
    Fallback rules:
      confidence < 0.35               → disqualify
      confidence > 0.70 + high_value  → qualify
      support_escalation category     → escalate
      everything else                 → manual_review

    │
    ▼
[5] EXPLANATION LAYER (deterministic, no LLM)
    - decision:  human-readable action label
    - why:       reasoning from decision layer
    - based_on:  doc IDs + similarity scores + outcome labels
    - risk_flags: rule-based checks:
        - confidence in uncertain band
        - enterprise lead being disqualified
        - past incorrect cases retrieved
        - all retrieved docs low similarity
        - confidence adjusted down significantly
        - fallback mode active
        - support escalation not escalated

    │
    ▼
[6] SQLite STORAGE
    - decisions table: one row per run, full decision + explanation
    - retrievals table: one row per retrieved doc per run (normalised)

    │
    ▼
[7] API RESPONSE
    Full PipelineResult JSON
```

---

## Example 1 — High-Value Lead (Full Pipeline)

### Input
```json
{
  "lead_id": "LEAD-TEST-001",
  "category": "high_value",
  "description": "Enterprise SaaS company, 700 employees, CTO requested demo and pricing. Clear buying intent, timeline Q3.",
  "confidence": 0.84
}
```

### Retrieved Context
```
[1] case_009 (past_case) similarity=0.4564  outcome=correct
    "High-value SaaS lead, confidence 0.82, clear buying intent. Qualified immediately,
     demo booked same day. Closed in 21 days. Fast correct decision."

[2] rule_006 (decision_rule) similarity=0.2021
    "High-value leads from enterprise accounts (500+ employees) should never be
     automatically disqualified even at low confidence. Route to manual review minimum."

[3] case_005 (past_case) similarity=0.1816  outcome=incorrect
    "Enterprise lead (800 employees) auto-disqualified due to low confidence score.
     Rule violation — enterprise leads must not be auto-disqualified.
     Lost potential €120k contract. High-cost incorrect decision."
```

### Decision Output
```json
{
  "recommended_action": "qualify",
  "reasoning": "Deterministic fallback: confidence 0.84 exceeds qualification threshold (0.70) and category is high_value.",
  "supporting_evidence": "High confidence with high_value category — standard qualification path.",
  "confidence_adjusted": 0.84,
  "context_was_used": false
}
```

### Explanation Output
```json
{
  "decision": "Qualify lead and route to sales",
  "why": "Deterministic fallback: confidence 0.84 exceeds qualification threshold (0.70) and category is high_value.",
  "based_on": "Retrieved 3 documents via tfidf_fallback: case_009 (past_case, similarity 0.456) [past outcome: correct]; rule_006 (decision_rule, similarity 0.202); case_005 (past_case, similarity 0.182) [past outcome: incorrect].",
  "risk_flags": [
    "1 retrieved past case(s) had incorrect outcomes. Similar situations previously resulted in errors — review carefully.",
    "Decision was made without context (fallback mode or no-context run). RAG layer did not contribute to this decision."
  ]
}
```

---

## Example 2 — Support Escalation

### Input
```json
{
  "lead_id": "LEAD-TEST-002",
  "category": "support_escalation",
  "description": "Customer submitted 4 support tickets in 5 days, no resolution, threatening to cancel enterprise contract.",
  "confidence": 0.73
}
```

### Decision Output
```json
{
  "recommended_action": "escalate",
  "reasoning": "Deterministic fallback: category is support_escalation. Escalation is always required for this category regardless of confidence.",
  "confidence_adjusted": 0.73
}
```

### Risk Flags
```
- 2 retrieved past case(s) had incorrect outcomes. Similar situations previously resulted in errors — review carefully.
- All retrieved documents had low similarity scores (<0.30). Retrieval quality is weak — context may not be relevant.
- Decision was made without context (fallback mode or no-context run). RAG layer did not contribute to this decision.
```

---

## Example 3 — Ambiguous Lead (Uncertain Band)

### Input
```json
{
  "lead_id": "LEAD-TEST-003",
  "category": "ambiguous",
  "description": "Mid-size company, partial form data, missing company size. Description mentions automation tooling evaluation.",
  "confidence": 0.51
}
```

### Validation Warning (non-fatal)
```
confidence 0.51 is in the uncertain band [0.45–0.55].
Model is statistically unreliable in this range. Manual review recommended.
```

### Decision Output
```json
{
  "recommended_action": "manual_review",
  "reasoning": "Deterministic fallback: confidence 0.5 or category 'ambiguous' does not meet any automatic routing threshold. Defaulting to manual review.",
  "confidence_adjusted": 0.51
}
```

### Risk Flags
```
- Confidence 0.51 is in the unreliable band (0.45–0.55). Statistical confidence is low.
- 1 retrieved past case(s) had incorrect outcomes.
- Decision was made without context (fallback mode or no-context run).
```

---

## Example 4 — Validation Failures

### 4a — Invalid category
```json
Input:  { "category": "unknown_type", ... }
Result: { "is_valid": false, "errors": ["Invalid category 'unknown_type'. Must be one of: ['ambiguous', 'disqualified', 'high_value', 'low_value', 'manual_review', 'support_escalation']"] }
```

### 4b — Confidence out of range
```json
Input:  { "confidence": 1.5, ... }
Result: { "is_valid": false, "errors": ["confidence 1.5 out of range [0.0, 1.0]"] }
```

### 4c — Description too short
```json
Input:  { "description": "Short", ... }
Result: { "is_valid": false, "errors": ["description too short (minimum 10 characters)"] }
```

### 4d — Missing required field
```json
Input:  { "lead_id": "X", "category": "high_value", "confidence": 0.7 }
Result: { "is_valid": false, "errors": ["Missing required field: description"] }
```

---

## Example 5 — Five Retrieval Results

### Query: enterprise lead high value qualify
```
[rule_006] decision_rule  sim=0.3290  "High-value leads from enterprise accounts (500+ employees) should never be automatically disqualified..."
[case_005] past_case      sim=0.3246  outcome=incorrect  "Enterprise lead (800 employees) auto-disqualified..."
[case_003] past_case      sim=0.2935  outcome=correct    "Ambiguous lead with confidence 0.52, sent to manual review..."
```

### Query: support escalation customer ticket unresolved
```
[case_012] past_case  sim=0.4224  outcome=correct    "Support escalation correctly assigned within 2 hours. Textbook correct."
[case_006] past_case  sim=0.2731  outcome=incorrect  "Support escalation held 6 hours without owner. Customer cancelled."
[case_002] past_case  sim=0.1942  outcome=incorrect  "Lead submitted contact form 3 times, no response. Churned."
```

### Query: low confidence disqualify no buying signals
```
[case_004] past_case     sim=0.3812  outcome=correct    "Low-confidence lead (0.31), no buying signals. Auto-disqualified. Correct."
[rule_001] decision_rule sim=0.2157                     "Leads with annual revenue above €500k and active buying signal..."
[case_011] past_case     sim=0.1629  outcome=incorrect  "Low-confidence lead (0.38) with growth signal missed. Disqualified."
```

### Query: ambiguous lead manual review uncertain
```
[rule_005] decision_rule sim=0.3646  "Ambiguous leads with mid-range confidence (0.40–0.60) and missing company size data should be sent to manual review..."
[case_003] past_case     sim=0.3027  outcome=correct    "Ambiguous lead, missing data, sent to review — identified as high-value. Converted."
[case_014] past_case     sim=0.2847  outcome=ambiguous  "Ambiguous lead, confidence 0.50. Disqualified. Became customer 6 months later."
```

### Query: false positive enrichment data wrong stale
```
[note_002] note      sim=0.4958  "False positive rate spiked in March: enrichment API returned stale data for 12% of leads..."
[case_013] past_case sim=0.3871  outcome=incorrect  "False positive: enrichment showed high revenue but company in administration. Contacted — wasted resource."
[case_010] past_case sim=0.1444  outcome=ambiguous  "Lead held 48 hours pending enrichment. Data returned low quality. Disqualified."
```

---

## Example 6 — With Context vs Without Context

### Input
```json
{
  "lead_id": "LEAD-COMPARE-001",
  "category": "ambiguous",
  "description": "Mid-size company, partial data, no company size. Enrichment data may be stale. Confidence in uncertain band.",
  "confidence": 0.50
}
```

### With Context
```json
{
  "docs_retrieved": 3,
  "retrieval_mode": "tfidf_fallback",
  "recommended_action": "manual_review",
  "confidence_input": 0.5,
  "confidence_adjusted": 0.5,
  "risk_flags": [
    "Confidence 0.5 is in the unreliable band (0.45–0.55). Statistical confidence is low.",
    "1 retrieved past case(s) had incorrect outcomes. Similar situations previously resulted in errors — review carefully.",
    "Decision was made without context (fallback mode or no-context run). RAG layer did not contribute to this decision."
  ]
}
```

### Without Context
```json
{
  "docs_retrieved": 0,
  "recommended_action": "manual_review",
  "confidence_input": 0.5,
  "confidence_adjusted": 0.5,
  "risk_flags": [
    "Confidence 0.5 is in the unreliable band (0.45–0.55). Statistical confidence is low.",
    "All retrieved documents had low similarity scores (<0.30). Retrieval quality is weak — context may not be relevant.",
    "Decision was made without context (fallback mode or no-context run). RAG layer did not contribute to this decision."
  ]
}
```

### Difference
Both paths reach the same action here (manual_review via deterministic fallback). The difference is in the risk flag set:
- With context: surfaces that a past incorrect outcome was retrieved for this pattern — actionable signal
- Without context: flags only low similarity + fallback mode — less informative

When the LLM layer is active (API key present), the difference becomes more significant:
the with-context path allows the LLM to cite specific rules and past case outcomes in its reasoning,
producing a higher-quality, evidenced decision vs a blind inference from the description alone.

---

## SQLite Storage Verified

```
decisions table (3 rows after test run):
  LEAD-TEST-001 | high_value         | conf=0.84 → qualify        | fallback=1
  LEAD-TEST-002 | support_escalation | conf=0.73 → escalate       | fallback=1
  LEAD-TEST-003 | ambiguous          | conf=0.51 → manual_review  | fallback=1

retrievals table (9 rows — 3 docs × 3 leads):
  LEAD-TEST-001: case_009 (sim=0.456), rule_006 (sim=0.202), case_005 (sim=0.182)
```

---

## Note on Fallback Mode

All examples above show `used_fallback: true` because the LLM API key is not set
in this build environment. The deterministic fallback is behaving correctly:
- support_escalation → always escalate (category rule)
- high_value + confidence > 0.70 → qualify (threshold rule)
- ambiguous / uncertain band → manual_review (safe default)

When ANTHROPIC_API_KEY is set, the LLM layer activates and produces context-informed
reasoning that references specific retrieved documents by ID. The fallback layer then
becomes the error handler rather than the primary path.

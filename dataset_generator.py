"""
dataset_generator.py
Generates the knowledge base corpus and evaluation dataset.

Corpus (documents stored in vector index):
  - past_case: historical lead decisions with outcomes
  - decision_rule: business rules / policy statements
  - note: operational observations

Eval dataset:
  - 75 records split across correct / incorrect / ambiguous outcomes
  - consistent with CRM/lead qualification domain from P1–P4
"""

import json
import random
from pathlib import Path

random.seed(42)

# ─── Knowledge base documents ─────────────────────────────────────────────────

KNOWLEDGE_BASE = [

    # ── Decision Rules ───────────────────────────────────────────────────────

    {
        "doc_id": "rule_001",
        "source_type": "decision_rule",
        "content": (
            "Leads with annual revenue above €500k and active buying signal "
            "within 30 days must be qualified and routed to senior sales. "
            "Do not hold or disqualify without escalation review."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "rule_002",
        "source_type": "decision_rule",
        "content": (
            "If a lead has submitted a contact form more than twice in 14 days "
            "without a response from the team, auto-escalate to support. "
            "This prevents churn from service neglect."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "rule_003",
        "source_type": "decision_rule",
        "content": (
            "Leads with a confidence score below 0.40 and no qualifying "
            "signals should be disqualified automatically. "
            "Manual review is only warranted if there is one or more high-value indicator."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "rule_004",
        "source_type": "decision_rule",
        "content": (
            "Support escalation cases must include an assigned owner within 4 hours. "
            "Unassigned escalations older than 4 hours trigger a Slack alert to team lead."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "rule_005",
        "source_type": "decision_rule",
        "content": (
            "Ambiguous leads with mid-range confidence (0.40–0.60) and missing "
            "company size data should be sent to manual review, not auto-disqualified. "
            "Disqualifying ambiguous leads costs more than reviewing them."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "rule_006",
        "source_type": "decision_rule",
        "content": (
            "High-value leads from enterprise accounts (500+ employees) should "
            "never be automatically disqualified even at low confidence. "
            "Route to manual review minimum."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "rule_007",
        "source_type": "decision_rule",
        "content": (
            "If a lead was previously disqualified within 90 days and re-submits, "
            "flag for manual review. Prior disqualification is not permanent — "
            "context may have changed."
        ),
        "outcome_label": None,
    },

    # ── Past Cases ───────────────────────────────────────────────────────────

    {
        "doc_id": "case_001",
        "source_type": "past_case",
        "content": (
            "Lead from fintech sector, mid-market size, confidence 0.71. "
            "Qualified and routed to senior sales. "
            "Converted to contract within 45 days. Correct qualification."
        ),
        "outcome_label": "correct",
    },
    {
        "doc_id": "case_002",
        "source_type": "past_case",
        "content": (
            "Lead submitted contact form 3 times in 7 days with no team response. "
            "Auto-qualified without escalation check. "
            "Customer churned due to poor response time. Incorrect decision."
        ),
        "outcome_label": "incorrect",
    },
    {
        "doc_id": "case_003",
        "source_type": "past_case",
        "content": (
            "Ambiguous lead with confidence 0.52, missing job title and company size. "
            "Sent to manual review. Reviewer identified as high-value enterprise lead. "
            "Converted after follow-up. Manual review was the correct call."
        ),
        "outcome_label": "correct",
    },
    {
        "doc_id": "case_004",
        "source_type": "past_case",
        "content": (
            "Low-confidence lead (0.31) from small business, no buying signals. "
            "Auto-disqualified. Correct — lead was cold and never followed up."
        ),
        "outcome_label": "correct",
    },
    {
        "doc_id": "case_005",
        "source_type": "past_case",
        "content": (
            "Enterprise lead (800 employees) auto-disqualified due to low confidence score. "
            "Rule violation — enterprise leads must not be auto-disqualified. "
            "Lost potential €120k contract. High-cost incorrect decision."
        ),
        "outcome_label": "incorrect",
    },
    {
        "doc_id": "case_006",
        "source_type": "past_case",
        "content": (
            "Support escalation case held for 6 hours without owner assignment. "
            "No alert was triggered due to misconfigured workflow. "
            "Customer cancelled subscription. Process failure."
        ),
        "outcome_label": "incorrect",
    },
    {
        "doc_id": "case_007",
        "source_type": "past_case",
        "content": (
            "Re-submitted lead from 60 days prior disqualification. "
            "New budget cycle confirmed by enrichment data. "
            "Routed to manual review, then qualified. Converted in 30 days."
        ),
        "outcome_label": "correct",
    },
    {
        "doc_id": "case_008",
        "source_type": "past_case",
        "content": (
            "Mid-value lead with confidence 0.58, partial company data. "
            "Auto-routed to low priority queue instead of manual review. "
            "Lead went cold — contacted competitor. Incorrect routing."
        ),
        "outcome_label": "incorrect",
    },
    {
        "doc_id": "case_009",
        "source_type": "past_case",
        "content": (
            "High-value SaaS lead, confidence 0.82, clear buying intent. "
            "Qualified immediately, demo booked same day. "
            "Closed in 21 days. Fast correct decision."
        ),
        "outcome_label": "correct",
    },
    {
        "doc_id": "case_010",
        "source_type": "past_case",
        "content": (
            "Lead flagged as ambiguous due to inconsistent form data. "
            "Held for 48 hours pending enrichment. Data returned low quality. "
            "Disqualified after review. Borderline correct but delay was costly."
        ),
        "outcome_label": "ambiguous",
    },
    {
        "doc_id": "case_011",
        "source_type": "past_case",
        "content": (
            "Low-confidence lead (0.38) with one strong signal: "
            "the company had tripled headcount in 6 months. "
            "Auto-disqualified without checking growth signals. Missed opportunity."
        ),
        "outcome_label": "incorrect",
    },
    {
        "doc_id": "case_012",
        "source_type": "past_case",
        "content": (
            "Support escalation correctly assigned within 2 hours. "
            "Issue resolved, customer retained. Textbook correct escalation handling."
        ),
        "outcome_label": "correct",
    },
    {
        "doc_id": "case_013",
        "source_type": "past_case",
        "content": (
            "False positive: lead enrichment data showed high revenue but "
            "the company was in administration. Qualified and contacted. "
            "No response — company had ceased operations. Enrichment data lag caused error."
        ),
        "outcome_label": "incorrect",
    },
    {
        "doc_id": "case_014",
        "source_type": "past_case",
        "content": (
            "Ambiguous lead with confidence 0.50 exactly. Sent to manual review. "
            "Reviewer noted no clear need fit. Disqualified. "
            "Six months later the company became a customer via a different channel. "
            "Ambiguous outcome — disqualification was defensible at the time."
        ),
        "outcome_label": "ambiguous",
    },
    {
        "doc_id": "case_015",
        "source_type": "past_case",
        "content": (
            "High-volume inbound batch: 40 leads processed overnight. "
            "Validation layer caught 8 leads with missing required fields. "
            "8 leads held, 32 routed correctly. Validation prevented downstream errors."
        ),
        "outcome_label": "correct",
    },

    # ── Operational Notes ────────────────────────────────────────────────────

    {
        "doc_id": "note_001",
        "source_type": "note",
        "content": (
            "Pattern observed Q1: leads from the healthcare sector consistently "
            "require longer decision cycles. Do not disqualify healthcare leads "
            "for slow response — extend review window to 14 days."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "note_002",
        "source_type": "note",
        "content": (
            "False positive rate spiked in March: enrichment API returned stale data "
            "for 12% of leads. Any lead where enrichment data is older than 45 days "
            "should be flagged for manual verification before qualification."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "note_003",
        "source_type": "note",
        "content": (
            "Confidence scores between 0.45 and 0.55 are statistically unreliable. "
            "The model is essentially guessing in this band. "
            "Manual review is strongly recommended for this confidence range."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "note_004",
        "source_type": "note",
        "content": (
            "Support escalation volume increases 40% on Mondays. "
            "Routing rules should account for Monday load and pre-assign backup owners."
        ),
        "outcome_label": None,
    },
    {
        "doc_id": "note_005",
        "source_type": "note",
        "content": (
            "Leads with descriptions containing product-specific questions "
            "(pricing, integration, API) convert at 2.3x the baseline rate. "
            "Treat product-question leads as high-intent regardless of confidence score."
        ),
        "outcome_label": None,
    },
]


# ─── Evaluation dataset ───────────────────────────────────────────────────────

def _lead_id(n: int) -> str:
    return f"LEAD-{n:04d}"


EVAL_TEMPLATES = [

    # Correct decisions (25 records)
    {"category": "high_value", "confidence": 0.85,
     "description": "Enterprise SaaS lead, 600 employees, requested demo and pricing. Clear buying intent.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.79,
     "description": "CTO-level contact from fintech company, tripled headcount in 12 months, asked about API integration.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.88,
     "description": "Inbound from VP Sales, enterprise account, annual revenue €2M+, ready to start pilot.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.91,
     "description": "Repeat customer from partner channel, previously closed deal, looking to expand seats.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.76,
     "description": "Mid-market operations company, submitted RFP, timeline of 60 days, budget confirmed.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.22,
     "description": "Individual freelancer, no company, no budget mentioned, vague interest only.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.18,
     "description": "Student email domain, mentions project research, no commercial intent.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.29,
     "description": "Small hobby business, single owner, monthly revenue under €2k.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.15,
     "description": "Spam-like submission with incomplete fields and non-business email.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.31,
     "description": "Lead from a company that dissolved 6 months ago per public records.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "support_escalation", "confidence": 0.70,
     "description": "Customer submitted 3 support tickets in 5 days, no resolution provided, threatening cancellation.",
     "expected_action": "escalate", "expected_outcome": "correct"},
    {"category": "support_escalation", "confidence": 0.80,
     "description": "Enterprise client reports critical integration failure affecting production environment.",
     "expected_action": "escalate", "expected_outcome": "correct"},
    {"category": "support_escalation", "confidence": 0.75,
     "description": "High-value account has not received response to billing dispute in 7 days.",
     "expected_action": "escalate", "expected_outcome": "correct"},
    {"category": "manual_review", "confidence": 0.55,
     "description": "Mid-size company, partial form data, no company size, but mentions growing team.",
     "expected_action": "manual_review", "expected_outcome": "correct"},
    {"category": "manual_review", "confidence": 0.48,
     "description": "Lead from healthcare sector, slow to respond, may be on extended evaluation cycle.",
     "expected_action": "manual_review", "expected_outcome": "correct"},
    {"category": "manual_review", "confidence": 0.52,
     "description": "Previously disqualified lead from 75 days ago, re-submitted with updated company info.",
     "expected_action": "manual_review", "expected_outcome": "correct"},
    {"category": "manual_review", "confidence": 0.49,
     "description": "Lead with product-specific API questions but no company size or revenue data provided.",
     "expected_action": "manual_review", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.83,
     "description": "Director-level contact, 900-employee logistics company, requesting custom pricing proposal.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.77,
     "description": "Inbound referral from existing customer, confirmed budget, Q3 implementation timeline.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "support_escalation", "confidence": 0.68,
     "description": "Customer data export failed repeatedly over 48 hours, data compliance team involved.",
     "expected_action": "escalate", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.20,
     "description": "Single-person startup, pre-revenue, looking for free tier, no growth indicators.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "manual_review", "confidence": 0.51,
     "description": "Lead from ambiguous industry code, description mentions automation but no context.",
     "expected_action": "manual_review", "expected_outcome": "correct"},
    {"category": "high_value", "confidence": 0.86,
     "description": "Scale-up company raised Series B last month, CRO contact, active buying timeline.",
     "expected_action": "qualify", "expected_outcome": "correct"},
    {"category": "low_value", "confidence": 0.24,
     "description": "Competitor employee contact, likely doing market research, no buying intent.",
     "expected_action": "disqualify", "expected_outcome": "correct"},
    {"category": "support_escalation", "confidence": 0.72,
     "description": "Premium tier customer reporting repeated login failures over 3 days, no fix delivered.",
     "expected_action": "escalate", "expected_outcome": "correct"},

    # Incorrect decisions (25 records)
    {"category": "high_value", "confidence": 0.82,
     "description": "Enterprise lead, 800 employees. Auto-disqualified due to misconfigured routing rule.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.78,
     "description": "CTO contact, API questions, confirmed budget. Routed to low-priority queue by error.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "support_escalation", "confidence": 0.74,
     "description": "Customer escalation held 8 hours with no owner. Alert failed due to config error.",
     "expected_action": "escalate", "expected_outcome": "incorrect"},
    {"category": "manual_review", "confidence": 0.53,
     "description": "Ambiguous lead auto-disqualified instead of sent to review. Reviewer would have qualified.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.79,
     "description": "Returning customer re-inquiry. Treated as new cold lead and placed in low-priority.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "ambiguous", "confidence": 0.45,
     "description": "Mid-range confidence, partial data. Auto-disqualified by threshold bug.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "low_value", "confidence": 0.35,
     "description": "Lead with low score but company had 3x headcount growth. Disqualified — missed signal.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.80,
     "description": "Enrichment data showed company in administration. Qualified and contacted — wasted resource.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "support_escalation", "confidence": 0.65,
     "description": "Escalation case incorrectly auto-resolved by system without human review.",
     "expected_action": "escalate", "expected_outcome": "incorrect"},
    {"category": "manual_review", "confidence": 0.50,
     "description": "Healthcare lead disqualified quickly. Sector requires extended review cycle.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.88,
     "description": "High-confidence lead with duplicate ID — processed twice, both records qualified incorrectly.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "low_value", "confidence": 0.28,
     "description": "Lead contained product-specific integration questions. Disqualified — high-intent signal missed.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "ambiguous", "confidence": 0.48,
     "description": "Lead from company that recently acquired a competitor — ambiguous but held not reviewed.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "support_escalation", "confidence": 0.77,
     "description": "Enterprise billing dispute routed to standard support, not escalation. Account at risk.",
     "expected_action": "escalate", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.75,
     "description": "Series A startup, strong buying signals. Disqualified due to company age threshold misconfiguration.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "manual_review", "confidence": 0.54,
     "description": "Lead with pricing questions routed to discard queue — intent signal not checked.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.84,
     "description": "Partner referral with confirmed budget auto-held by new queue rule. Never reviewed.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "support_escalation", "confidence": 0.60,
     "description": "Customer sent 4 follow-up emails in 48 hours. Marked as duplicate and suppressed.",
     "expected_action": "escalate", "expected_outcome": "incorrect"},
    {"category": "low_value", "confidence": 0.32,
     "description": "Micro-business lead, but owner was also investor in target vertical — opportunity missed.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "ambiguous", "confidence": 0.47,
     "description": "Form submission with conflicting data points. System chose qualify without review.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.89,
     "description": "Inbound from analyst at large PE firm evaluating vendor stack. Disqualified as non-buyer.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "manual_review", "confidence": 0.56,
     "description": "Lead re-submitted after previous hold expired. System created new record, lost history.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},
    {"category": "support_escalation", "confidence": 0.69,
     "description": "Data sync failure affecting 3 enterprise accounts. Logged as low-priority ticket.",
     "expected_action": "escalate", "expected_outcome": "incorrect"},
    {"category": "high_value", "confidence": 0.81,
     "description": "Lead from logistics company post-acquisition — enrichment returned old company data.",
     "expected_action": "qualify", "expected_outcome": "incorrect"},
    {"category": "ambiguous", "confidence": 0.44,
     "description": "Strong description but very low confidence — model uncertainty masked genuine intent.",
     "expected_action": "manual_review", "expected_outcome": "incorrect"},

    # Ambiguous cases (25 records)
    {"category": "ambiguous", "confidence": 0.50,
     "description": "Mid-range confidence, partial company data, no job title. Could go either way.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.53,
     "description": "Company name matches known account but contact is unknown. Possible employee inquiry.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.47,
     "description": "Disqualified 6 months ago, re-submitting now. Context may have changed.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.49,
     "description": "High revenue company but description is too generic to assess intent.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.52,
     "description": "Enrichment returned data older than 45 days. Revenue figure unverifiable.",
     "expected_action": "hold", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.55,
     "description": "Lead from public sector organisation — procurement cycles are long and opaque.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.46,
     "description": "Confidence in uncertain band (0.45–0.55). Model is statistically unreliable here.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.51,
     "description": "Lead mentions competitor product by name — could be evaluating alternatives or churning.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.48,
     "description": "Healthcare company, decision-making timeline unclear, regulatory environment complex.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.54,
     "description": "Non-English company form submission, auto-translated, some fields uncertain.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.50,
     "description": "Startup pre-product-market fit, could scale rapidly or fold within 6 months.",
     "expected_action": "hold", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.43,
     "description": "Company size listed as 1–10 employees but revenue figure suggests much larger operation.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.57,
     "description": "Previous support case unresolved — relationship status unclear before qualification.",
     "expected_action": "hold", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.52,
     "description": "Duplicate lead with slight variation in email domain. Possibly same person.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.45,
     "description": "Lead from consultancy — unclear if buying for self or on behalf of end client.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.58,
     "description": "Company recently IPO'd — internal buying processes likely in flux.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.50,
     "description": "Buying signal in description but legal entity name does not match enrichment data.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.44,
     "description": "Strong description quality but confidence score is below the reliable threshold.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.53,
     "description": "Lead from agency — could be sourcing for client, speculative, or genuine buy.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.56,
     "description": "Company underwent management buyout 30 days ago — new leadership, unknown priorities.",
     "expected_action": "hold", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.47,
     "description": "Contact gave personal email, not business email — intent and authority unclear.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.51,
     "description": "Positive enrichment data but lead description has urgent tone suggesting crisis purchase.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.49,
     "description": "Mid-size logistics company, description mentions both current vendor and evaluation.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.55,
     "description": "Lead from charity/NGO — different procurement rules, budget cycles non-standard.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
    {"category": "ambiguous", "confidence": 0.52,
     "description": "High email open rate on prior nurture sequence but no form submission until now.",
     "expected_action": "manual_review", "expected_outcome": "ambiguous"},
]


def generate_dataset() -> list[dict]:
    dataset = []
    for i, template in enumerate(EVAL_TEMPLATES, start=1):
        record = {
            "lead_id": _lead_id(i),
            **template
        }
        dataset.append(record)
    return dataset


def save_all(output_dir: str = "/home/claude/p5_rag_decision_support/data") -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save knowledge base
    kb_path = Path(output_dir) / "knowledge_base.json"
    with open(kb_path, "w") as f:
        json.dump(KNOWLEDGE_BASE, f, indent=2)
    print(f"Knowledge base saved: {len(KNOWLEDGE_BASE)} documents → {kb_path}")

    # Save eval dataset
    dataset = generate_dataset()
    ds_path = Path(output_dir) / "eval_dataset.json"
    with open(ds_path, "w") as f:
        json.dump(dataset, f, indent=2)

    correct  = sum(1 for r in dataset if r["expected_outcome"] == "correct")
    incorrect= sum(1 for r in dataset if r["expected_outcome"] == "incorrect")
    ambiguous= sum(1 for r in dataset if r["expected_outcome"] == "ambiguous")
    print(f"Eval dataset saved: {len(dataset)} records → {ds_path}")
    print(f"  Correct: {correct} | Incorrect: {incorrect} | Ambiguous: {ambiguous}")


if __name__ == "__main__":
    save_all()

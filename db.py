"""
db.py
SQLite audit trail.

Stores every pipeline run — input, retrieval, decision, explanation, validation.
Nothing leaves the system without being logged.

Schema:
  decisions  — one row per pipeline run
  retrievals — one row per retrieved document per run (normalised)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "db" / "decisions.db"


# ─── Init ─────────────────────────────────────────────────────────────────────

def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id             TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            category            TEXT,
            confidence_input    REAL,
            confidence_adjusted REAL,
            recommended_action  TEXT,
            reasoning           TEXT,
            supporting_evidence TEXT,
            context_was_used    INTEGER,
            used_fallback       INTEGER,
            risk_flags          TEXT,   -- JSON array
            explanation_json    TEXT,   -- full ExplanationOutput JSON
            input_json          TEXT,   -- full DecisionInput JSON
            validation_errors   TEXT,   -- JSON array
            validation_warnings TEXT,   -- JSON array
            fallback_reason     TEXT    -- why the decision layer fell back (NULL if not fallback)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS retrievals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id         TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            doc_id          TEXT,
            source_type     TEXT,
            similarity_score REAL,
            outcome_label   TEXT,
            retrieval_mode  TEXT,
            content_snippet TEXT    -- first 200 chars
        )
    """)

    conn.commit()
    conn.close()


# ─── Write ────────────────────────────────────────────────────────────────────

def store_pipeline_record(
    lead_input_dict:    dict,
    retrieval_dict:     dict,
    decision_dict:      dict,
    explanation_dict:   dict,
    validation_dict:    dict,
    used_fallback:      bool,
    fallback_reason:    Optional[str] = None,
    db_path: Path = DB_PATH,
) -> int:
    """
    Write one complete pipeline run to SQLite.
    Returns the inserted row ID.
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    ts = datetime.now(timezone.utc).isoformat()

    cur.execute("""
        INSERT INTO decisions (
            lead_id, timestamp, category,
            confidence_input, confidence_adjusted,
            recommended_action, reasoning, supporting_evidence,
            context_was_used, used_fallback,
            risk_flags, explanation_json, input_json,
            validation_errors, validation_warnings, fallback_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead_input_dict.get("lead_id"),
        ts,
        lead_input_dict.get("category"),
        lead_input_dict.get("confidence"),
        decision_dict.get("confidence_adjusted"),
        decision_dict.get("recommended_action"),
        decision_dict.get("reasoning"),
        decision_dict.get("supporting_evidence"),
        int(decision_dict.get("context_was_used", False)),
        int(used_fallback),
        json.dumps(explanation_dict.get("risk_flags", [])),
        json.dumps(explanation_dict),
        json.dumps(lead_input_dict),
        json.dumps(validation_dict.get("errors", [])),
        json.dumps(validation_dict.get("warnings", [])),
        fallback_reason,
    ))

    row_id = cur.lastrowid

    # Normalised retrieval rows
    for doc in retrieval_dict.get("retrieved_context", []):
        cur.execute("""
            INSERT INTO retrievals (
                lead_id, timestamp, doc_id, source_type,
                similarity_score, outcome_label, retrieval_mode, content_snippet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_input_dict.get("lead_id"),
            ts,
            doc.get("doc_id"),
            doc.get("source_type"),
            doc.get("similarity_score"),
            doc.get("outcome_label"),
            retrieval_dict.get("retrieval_mode"),
            doc.get("content", "")[:200],
        ))

    conn.commit()
    conn.close()
    return row_id


# ─── Read ─────────────────────────────────────────────────────────────────────

def get_explanations(limit: int = 50, db_path: Path = DB_PATH) -> list[dict]:
    """Return recent decision + explanation records."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute("""
        SELECT lead_id, timestamp, category, confidence_input,
               confidence_adjusted, recommended_action,
               risk_flags, explanation_json, context_was_used, used_fallback
        FROM decisions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    # Deserialise JSON fields
    for row in rows:
        row["risk_flags"] = json.loads(row["risk_flags"] or "[]")
        row["explanation"] = json.loads(row["explanation_json"] or "{}")
        del row["explanation_json"]
    return rows


def get_context_for_lead(lead_id: str, db_path: Path = DB_PATH) -> list[dict]:
    """Return all retrieved documents for a given lead_id."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute("""
        SELECT doc_id, source_type, similarity_score,
               outcome_label, retrieval_mode, content_snippet, timestamp
        FROM retrievals
        WHERE lead_id = ?
        ORDER BY similarity_score DESC
    """, (lead_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

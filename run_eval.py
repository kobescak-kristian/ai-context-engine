"""
run_eval.py
Eval harness — runs all 75 records in eval_dataset.json through the live
server's /decision-support endpoint and checks recommended_action against
expected_action.

Usage:
    uvicorn app:app --port 8000          # in one terminal
    python run_eval.py                   # in another

Gate: hard PASS/FAIL against the thresholds in eval_config.py (committed
before this file's first official run — see eval_config.py for rationale).
Mode (fallback vs keyed) is inferred from used_fallback on the live
responses, not assumed: a mixed run (some rows fell back, some didn't) is
reported honestly and gated conservatively rather than silently picking
a threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

from eval_config import (
    TOTAL_RECORDS,
    FALLBACK_GATE_MIN_AGREEMENT,
    KEYED_GATE_MIN_AGREEMENT,
    KEYED_TARGET_AGREEMENT,
)

EVAL_DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


def run_eval(base_url: str) -> int:
    records = json.loads(EVAL_DATASET_PATH.read_text())
    if len(records) != TOTAL_RECORDS:
        print(f"[Eval] WARNING: expected {TOTAL_RECORDS} records, found {len(records)}")

    results = []
    with httpx.Client(timeout=30.0) as client:
        for rec in records:
            payload = {
                "lead_id": rec["lead_id"],
                "category": rec["category"],
                "description": rec["description"],
                "confidence": rec["confidence"],
            }
            resp = client.post(f"{base_url}/decision-support", json=payload)
            resp.raise_for_status()
            body = resp.json()
            actual_action = body["decision"]["recommended_action"]
            used_fallback = body["used_fallback"]
            results.append({
                "lead_id": rec["lead_id"],
                "expected_action": rec["expected_action"],
                "actual_action": actual_action,
                "match": actual_action == rec["expected_action"],
                "used_fallback": used_fallback,
            })

    total          = len(results)
    agreement      = sum(1 for r in results if r["match"])
    fallback_count = sum(1 for r in results if r["used_fallback"])
    keyed_count    = total - fallback_count

    if fallback_count == total:
        mode, gate = "fallback", FALLBACK_GATE_MIN_AGREEMENT
    elif keyed_count == total:
        mode, gate = "keyed", KEYED_GATE_MIN_AGREEMENT
    else:
        mode, gate = "mixed", FALLBACK_GATE_MIN_AGREEMENT
        print(
            f"[Eval] WARNING: mixed run — {keyed_count} keyed / {fallback_count} fallback. "
            f"Applying the fallback gate ({gate}) as the conservative floor."
        )

    misses = [r for r in results if not r["match"]]

    print(f"[Eval] Mode: {mode} ({keyed_count} keyed / {fallback_count} fallback / {total} total)")
    print(f"[Eval] Agreement: {agreement}/{total}")
    print(f"[Eval] Gate ({mode}): >= {gate}")
    if mode == "keyed":
        print(f"[Eval] Keyed target (reported, not gated): {KEYED_TARGET_AGREEMENT}/{total}")

    print(f"[Eval] Misses ({len(misses)}):")
    for m in misses:
        print(f"  {m['lead_id']}: expected={m['expected_action']} actual={m['actual_action']}")

    passed = agreement >= gate
    print(f"[Eval] RESULT: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    sys.exit(run_eval(args.base_url))

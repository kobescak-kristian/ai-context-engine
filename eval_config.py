"""
eval_config.py
Eval gate thresholds — committed before the first official eval run
(gate-before-code: the numbers are fixed here first, then run_eval.py
is pointed at them, so no threshold is chosen after seeing a result).

Locked 2026-07-06, before the first official eval run.

- FALLBACK_GATE (68/75) is the audit-measured baseline for the
  deterministic fallback path. It is a regression floor, not a target:
  the fallback is pure rule-based logic, so a correctly-functioning
  build should never score below the number already measured against
  it.
- KEYED_GATE (69/75) applies only to a run where the LLM layer is
  active (a real ANTHROPIC_API_KEY set). It must strictly beat the
  fallback gate — the only reason to route through an LLM is to do
  better than the rule-based default. No evidence exists yet for what
  the keyed path actually scores; this gate is a floor, not a
  prediction.
- KEYED_TARGET (71/75) is reported once a keyed run exists, not
  enforced as a gate — there is no evidence basis for treating it as
  pass/fail.
"""

TOTAL_RECORDS = 75
FALLBACK_GATE_MIN_AGREEMENT = 68
KEYED_GATE_MIN_AGREEMENT = 69
KEYED_TARGET_AGREEMENT = 71

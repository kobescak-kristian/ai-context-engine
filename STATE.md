# STATE — ai-context-engine

- STATUS: DORMANT
  No work in progress; true as of 2026-11-11; updated when work resumes.

## Status

v1.0. No new evaluation cycle since the decision-prompt fix of 2026-10-29 (`EVAL_RESULTS.md`).

## Latest result

Fallback gate PASS and keyed gate FAIL, both 2026-07-07; keyed-run diagnosis corrected 2026-10-29.
Results and limits: `EVAL_RESULTS.md`.

## Open

- Deferred: a keyed cycle that measures decision quality, with a new scorer frozen first and held-out records;
  waits for a decision to open it.
- Deferred: the prompt rule tying ambiguous retrieved context to `manual_review` stays until such a cycle
  tests it (`EVAL_RESULTS.md`, Correction 2026-10-29).

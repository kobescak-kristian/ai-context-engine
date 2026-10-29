# STATE — ai-context-engine

**Classification:** PROJECT · T0 (retrieval-grounded decision support with an audit trail; `domains/github-ops/CONVENTIONS.md` PROJECT/SYSTEM/EXPERIMENT taxonomy).

**RECONSTRUCTED** (GOVERNANCE.md Build-repo STATE rule, clause 7): derived from git history at scaffold time (2026-09-19, Q-72(f)), not written contemporaneously. Reconstructed entries are retrospective evidence, not contemporaneous record — the commit that adds this file begins the contemporaneous record going forward.

**Note on sourcing:** this repo's README `## Version Log` is a single sparse row ("v1.0 | 2026-06-20 | Initial complete release") despite 32 commits and a real post-release audit/eval wave. This STATE.md draws on the fuller commit log below rather than the Version Log alone, to avoid understating real build history — flagged explicitly per the Q-72(f) implementation plan, not silently corrected in the README itself (out of this item's scope).

## Current state

No `## Status` heading exists in this README (same gap as ai-decision-engine). One ADR: `adr/0001-semantic-retrieval-with-tfidf-fallback.md`. Committed eval evidence: `EVAL_RESULTS.md` (fallback-mode 68/75 PASS; keyed run against `claude-sonnet-4-6` after a retired model ID was replaced, D4-reported honestly per its own gate outcome). As of 2026-10-29 that file carries a dated correction section: the keyed FAIL stands as measured, but its original "model-quality result" diagnosis is superseded by a measured scorer imbalance (38/75 labels are `manual_review`) and a prompt specification gap (four of five actions undefined), and the prompt gap is fixed. A second 2026-10-29 commit fixes retrieval index initialisation: the index is now built at server startup and the module-level retriever is published only after a successful build, so an interrupted cold-start build can no longer leave the server returning "Index not built" until restart.

## Build history (from `git log --reverse`, oldest → newest)

- **2026-06-17** (`1d8c6ee`, `3d1b0c8`) — Initial commit (RAG decision support); case-study README + architecture diagram.
- **2026-06-18** (`2e109bb`, `a39ec7b`) — Naming/consistency passes across the five-engine System Context.
- **2026-06-20** (`0a37ceb`) — Audit findings fixed (release point the sparse Version Log row refers to).
- **2026-07-04** (`1bbd8fa`) — ARTIFACT_STANDARD Tier 0 adopted: CLAUDE.md, pre-push validation, README restructure, first ADR.
- **2026-07-06 – 2026-07-07** (`eefeeb8`, `51875c0`, `4e8de76`, `0f2d441`, `803ba73`, `3b4e5cb`, `92eca06`) — M1–M6 + minor-7 audit-fix wave: empty API-key placeholder, honest grounding claim, vacuous risk-flag fix, re-run example with documented input, `fallback_reason` persistence, `run_comparison` persistence, unconditional grounding claim removed.
- **2026-07-07** (`6a1a4fa`, `baa3d3b`, `8847b1a`) — Eval harness added with D1 gate thresholds (Phase 3, gate-before-code); `EVAL_RESULTS.md` committed (fallback-mode 68/75, PASS); README eval claim rewritten to point at the committed runner/results.
- **2026-07-07** (`cb97348`, `8e20b68`, `bc1582b`, `9c0ddd5`, `ada4bce`, `8ad6e07`) — Phase 4: retired model ID replaced with `claude-sonnet-4-6`; keyed eval results + Example 7 added; D2 minors fixed; keyed result reported honestly (D4); private decision-record reference scrubbed from `EVAL_RESULTS.md`; keyed compare evidence (Example 8) committed and README figures reconciled — an independent-verification finding.
- **2026-07-10** (`2c8c98e`) — Synthetic data labeled in `EXAMPLE_OUTPUTS.md` (Q-28).
- **2026-07-11** (`c9f0db0`) — CLAUDE.md: session boot + governance pointer.
- **2026-07-24** (`dcdc010`) — Canonical pre-commit local-path guard added (Q-48 wave 1).
- **2026-07-27** (`3132c2b`, `6e49fa0`) — Keyless 3-OS eval CI, malformed-LLM suite, allowlist added; CI badge + coverage note.
- **2026-08-03 – 2026-08-04** (`8c72379`, `539cfb3`, `c35ff23`, `af30be7`) — Publish-gate canary; allowlist entry-exact migration; Apache-2.0 license; Q-35 hook rollout.
- **2026-09-15** (`cee7558`) — Canonical AGENTS.md router adopted (Q-93).
- **2026-09-19** — Q-72(f): STATE.md added (this file); validator gains a STATE.md-existence check, the obsolete 5-record decision cap is removed, and the six-name BANNED_WITHOUT_TRIGGER list is propagated (live-file precondition checked, clear).
- **2026-10-29** (`1944304`) — Keyed-run diagnosis corrected; prompt
  specification gap closed. `EVAL_RESULTS.md`'s conclusion that the 58/75 keyed
  FAIL was "a genuine model-quality result" is superseded by two causes derived
  from the committed artifacts: the answer key is 51% one class (38 of 75
  `expected_action` labels are `manual_review`, so a constant classifier scores
  38/75), and the deterministic fallback's 68/75 decomposes to 16/16 `qualify`,
  10/10 `escalate`, 7/7 `disqualify`, 35/38 `manual_review`, 0/4 `hold` —
  taking the majority class by default. `SYSTEM_PROMPT` defined four of the five
  permitted actions nowhere, which accounts for 12 of the 17 keyed misses (6
  `qualify`→`manual_review`, 2 `qualify`→`escalate`, 4 `hold`→`manual_review`).
  `support.py` now defines all five actions and gives `hold` an operational
  criterion. No gate change (`KEYED_GATE_MIN_AGREEMENT` stays 69), no dataset
  change, no new eval cycle, no keyed run, nothing deleted. Verified keyless:
  `python -m pytest tests/` 17 passed (exit 0); `python
  .githooks/validate_artifacts.py .` Tier 0 PASS (exit 0); `python run_eval.py`
  against a live local server `68/75 RESULT: PASS` (exit 0), the same 7 misses
  as the committed fallback run.
- **2026-10-29** (`d0caa53`) — Retrieval index initialisation fixed; the
  latent singleton defect observed during the previous item's verification is
  closed. `engine.get_retriever()` published an unbuilt `FAISSRetriever` into
  the module-level singleton before `build()` returned, so a request cancelled
  or failing during the cold-start index build left the instance cached and
  every later call raised `Index not built. Call build() first.` until the
  process restarted. The documented path reached it: `README.md` offers
  `sentence-transformers` as an optional upgrade, the semantic cold-start index
  build measured 39s and 40s to server-ready across two runs and 81.9s for a
  direct build in a fresh process, and `run_eval.py` uses a 30s per-request
  timeout, so installing the optional model and running the documented eval
  bricked the server on its first request. CI never reached it because `requirements.txt`
  leaves `sentence-transformers` commented out and the TF-IDF build measured
  0.005s. Fix: `build_retriever()` extracted and the singleton published only
  after the build succeeds, under a `threading.Lock` so concurrent first
  callers build once; `app.py` gains a `lifespan` hook that builds the index
  before the server accepts traffic, logging one flushed `[Startup] FATAL:` line
  and re-raising on failure, so the service never comes up without a working
  index. No gate change, no dataset change, no new eval cycle, no keyed run, no
  change to retrieval or decision behaviour. Verified keyless: `python -m pytest
  tests/` 21 passed (exit 0), including 4 new tests in
  `tests/test_retriever_init.py`, whose core regression test was confirmed to
  FAIL against the pre-fix `get_retriever()` and pass after it; `python
  .githooks/validate_artifacts.py .` Tier 0 PASS (exit 0); `python run_eval.py`
  against a live local server `68/75 RESULT: PASS` (exit 0), the same 7 misses
  as the committed fallback run, with CI's three grep assertions reproduced and
  zero `Index not built` or HTTP 500 entries in the server log; startup-failure
  path exercised by removing `knowledge_base.json`, uvicorn exited 3 with the
  `[Startup] FATAL:` line preceding the traceback.

## Open loops

README's sparse Version Log vs. this repo's real build history is flagged above, not corrected here — a README-content decision, out of this item's scope.

Opened 2026-10-29, none authorized for work here:

- **The keyed gate measures the wrong thing.** `KEYED_GATE_MIN_AGREEMENT = 69`
  requires the LLM path to reproduce the rule path and also win at least one row
  the rules get wrong. A keyed cycle that measures decision quality needs a new
  scorer with its gate frozen before it runs, and records held out from the
  current 75. Not opened here; owner decision.
- **One prompt coupling left unmeasured.** The rule tying ambiguous or
  contradictory retrieved context to `manual_review` was deliberately left in
  place, because removing it changes how the keyed path decides live cases and
  nothing has measured that.

## Closed loops

- **Latent retrieval-singleton defect** — opened 2026-10-29, closed 2026-10-29
  (`d0caa53`). `engine.get_retriever()` cached an unbuilt retriever, so a
  request cancelled during the cold-start index build left the server returning
  "Index not built. Call build() first." until restart. Fixed in `engine.py`
  and `app.py` with regression cover; see the build-history entry for evidence.

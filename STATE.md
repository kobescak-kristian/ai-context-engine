# STATE — ai-context-engine

**Classification:** PROJECT · T0 (retrieval-grounded decision support with an audit trail; `domains/github-ops/CONVENTIONS.md` PROJECT/SYSTEM/EXPERIMENT taxonomy).

**RECONSTRUCTED** (GOVERNANCE.md Build-repo STATE rule, clause 7): derived from git history at scaffold time (2026-09-19, Q-72(f)), not written contemporaneously. Reconstructed entries are retrospective evidence, not contemporaneous record — the commit that adds this file begins the contemporaneous record going forward.

**Note on sourcing:** this repo's README `## Version Log` is a single sparse row ("v1.0 | 2026-06-20 | Initial complete release") despite 32 commits and a real post-release audit/eval wave. This STATE.md draws on the fuller commit log below rather than the Version Log alone, to avoid understating real build history — flagged explicitly per the Q-72(f) implementation plan, not silently corrected in the README itself (out of this item's scope).

## Current state

No `## Status` heading exists in this README (same gap as ai-decision-engine). One ADR: `adr/0001-semantic-retrieval-with-tfidf-fallback.md`. Committed eval evidence: `EVAL_RESULTS.md` (fallback-mode 68/75 PASS; keyed run against `claude-sonnet-4-6` after a retired model ID was replaced, D4-reported honestly per its own gate outcome).

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
- **2026-09-19** (this commit) — Q-72(f): STATE.md added (this file); validator gains a STATE.md-existence check, the obsolete 5-record decision cap is removed, and the six-name BANNED_WITHOUT_TRIGGER list is propagated (live-file precondition checked, clear).

## Open loops

None on disk. README's sparse Version Log vs. this repo's real build history is flagged above, not corrected here — a README-content decision, out of this item's scope.

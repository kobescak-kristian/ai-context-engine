# AGENTS.md — ai-context-engine

Router for coding agents working in this repository. It points to where
truth lives; it is not itself evidence of implementation or status.

## Repository purpose

Retrieval-grounded decision support for operational cases such as lead
qualification, case routing and triage. For each case the system
validates the structured input, retrieves relevant past cases, rules and
notes from a knowledge base, produces a structured decision through an
LLM layer guarded by deterministic validation and fallback, generates a
structured explanation with risk flags, and normally persists the input,
retrieval, decision and explanation to a SQLite audit trail. It is
decision support with an audit trail, not a chatbot or a Q&A system.

## Authority and conflict handling

Where truth lives:

- `README.md` — public system description, public claims and known
  limitations. Its Version Log section is the documented history.
- `adr/` — material design decisions and their rationale.
- `EVAL_RESULTS.md` — committed measured evaluation evidence.
- `EXAMPLE_OUTPUTS.md` — committed example outputs.
- `eval_config.py` and `run_eval.py` — evaluation gate definitions and
  harness behaviour.
- The affected source, tests and configuration, read together —
  actual implementation behaviour.

When sources disagree:

- An adopted ADR governs the material decision it records.
- Documentation states intent. Source, tests and configuration state
  actual implementation behaviour. Committed evaluation artifacts state
  what was measured in the recorded runs.
- Surface a conflict as a finding. Never reconcile it silently.
- If the requested work materially depends on an unresolved conflict,
  stop and ask the owner.

## Task routing

Starting points, not exhaustive reading lists.

| Task | Start with |
|---|---|
| Understand the system | `README.md` |
| Full decision-support pipeline | `pipeline.py`, `app.py` |
| Retrieval (RAG) | `engine.py`, `knowledge_base.json`, `adr/0001-semantic-retrieval-with-tfidf-fallback.md` |
| Decision support and the LLM boundary | `support.py`, `schemas.py`, `validator.py` |
| Validation and deterministic fallback | `validator.py`, `schemas.py`, `tests/test_malformed_llm.py` |
| Explanation and risk flags | `explainer.py` |
| Persistence and audit reconstruction | `db.py`, `pipeline.py` |
| Evaluation | `run_eval.py`, `eval_config.py`, `eval_dataset.json`, `EVAL_RESULTS.md`, `tests/` |
| Example outputs | `EXAMPLE_OUTPUTS.md` |
| HTTP API | `app.py` |
| Documentation, ADRs, artifact validation | the affected artifact, `.githooks/validate_artifacts.py` |
| CI, hooks, publishing | `.github/workflows/ci.yml`, `.githooks/`, `.publicgate-allow` |

## Always-on constraints

- Validate before acting. Input that fails validation never becomes a
  decision-support case; the pipeline stops and returns the validation
  errors.
- The grounded pipeline retrieves before it decides. Do not bypass
  retrieval in any path that claims to run the full pipeline.
- Retrieval mode stays explicit and auditable. Semantic retrieval may
  fall back to the self-contained TF-IDF path when the embedding
  dependency or model is unavailable, and `retrieval_mode` records which
  path ran. Never present TF-IDF fallback as semantic retrieval.
- Grounding claims stay truthful. When the deterministic fallback makes
  the decision, retrieval may still run and be persisted, but the
  decision is not grounded in it and `context_was_used` stays false.
  Never set or imply context use for a fallback decision.
- Malformed, invalid or failed model output never propagates as an
  operational decision. It passes the structured validation path, or the
  deterministic fallback decides instead.
- Explanations stay structured and deterministic. Never invent retrieved
  evidence or claim a basis that is absent from the actual retrieval and
  decision data.
- Preserve auditability. On successful storage, keep the input,
  retrieval, decision and explanation reconstructable from persisted
  records. Storage failure is currently non-fatal and must remain
  explicit; never claim that provenance was persisted when storage
  failed.
- Preserve comparison semantics. The with-context and without-context
  legs are separate decisions persisted under distinguishable `lead_id`
  suffixes. Never collapse them into one indistinguishable record.
- Evaluation gates and committed results are evidence. Never change
  thresholds, expected results or published failures after seeing a run
  to make an evaluation pass. A new evaluation cycle defines and freezes
  its scorer or gate before it runs.
- Routine development and verification stay keyless. Do not start a paid
  or real-model call for routine checks; real model execution requires
  explicit owner authorization.
- No secrets and no machine-local absolute paths in tracked files.
  Machine-local values belong in the gitignored `.env`.
- Never rewrite Git history.
- Trigger-gated artifacts (walkthroughs, changelogs, runbooks, readiness
  documents) require a genuine material decision record that cites their
  trigger. ADRs are written only for genuine material decisions and have
  no hard maximum. Version history stays in the `README.md` Version Log.
- This file is an instruction surface, not a security boundary. Hooks,
  CI and tests are the enforcement.

## Verification

Keyless, local and non-destructive:

```bash
python -m pytest tests/ -v
python .githooks/validate_artifacts.py .
```

- The unit suite exercises the malformed-output, validation and fallback
  chain without a server or an API key.
- For changes to pipeline, retrieval, decision, validation or explanation
  behaviour, also run the keyless fallback-gate evaluation against a live
  local server, as `.github/workflows/ci.yml` does. First confirm that no
  Anthropic API key is set in the environment or in `.env`; otherwise the
  run makes real model calls. The run appends rows to the local,
  gitignored SQLite database.
- A local evaluation run is not new committed evidence. `EVAL_RESULTS.md`
  changes only through a deliberate new evaluation cycle.
- Report failures as they are. Never weaken a check to make it pass.

# ai-context-engine

@AGENTS.md

## Session boot and governance (applies to every session here)
- Governance home: kristian-os (PRINCIPLES -> GOVERNANCE ->
  FAILURE_REGISTER). Read before any irreversible action.
- Boot: read this repo's STATE.md first (if present; README status
  line otherwise); the operating contract (SPEC) loads globally.
- Before any write: environment fingerprint (pwd + git config
  user.email; /home/user/ path or noreply@anthropic.com = cloud
  sandbox = read-only, no pen). Pen check on main at open AND
  immediately before every commit.
- Close ritual: main is protected (PR required, required status
  checks must pass), so a direct push to main is rejected with
  GH006. Land work as: create a kos/<topic> branch -> commit ->
  push branch -> open PR to main -> owner merges -> fast-forward
  local main -> verify origin/main..HEAD empty -> report verbatim.
- Work comes from the governance repo's queue (kristian-os,
  FABLE_QUEUE); do not invent tasks.

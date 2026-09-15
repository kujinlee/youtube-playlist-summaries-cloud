# record-review-topology — round 10, coordinator adjudication

**REVIEW GAP:** claude — not invoked; built by a worker fork that cannot spawn subagents. All ten
rounds are Codex-only and **the Claude half is owed before merge**.

## Why a tenth round existed

CI went red on `scripts/check-fixture-variation.py` — a ratchet asserting every parameter of a
function under test is VARIED by its cases. It found a real hole, not a formality:
**`reviewed_state()`'s SUCCESS path had no self-test case at all.** Every call passed the same
`repo_root`, and the throwaway-index mechanism — the whole point of the function — was covered only
by live probes I ran by hand. Six cases now build a real git repository and drive it.

## Round 10 — Codex, `gpt-5.5`

`docs/reviews/codex/record-review-topology-r10-codex.md` · verdict
`docs/reviews/verdicts/record-review-topology-r10-codex.verdict.json` (`gate_ran: true`).
**NOT CONVERGED**: 1 High, nothing else.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | High | The new fixture inherited the host's global git config. Measured: `commit.gpgsign=true`, or a global `core.hooksPath` with a failing pre-commit hook, made the suite red — then crashed with `IndexError` three cases later because the silent commit failure was never checked | **FIXED** — the fixture runs under `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, commits with `--no-verify --no-gpg-sign`, and **asserts its own commit succeeded**. A fixture that cannot be built is CANNOT RUN and now says so in a case |

Re-measured after the fix under the exact condition r10 named — `GIT_CONFIG_GLOBAL` containing
`commit.gpgsign = true` — **75/75 passed**. Declared count 74 → 75.

**A guard that goes red for the machine it runs on gets switched off** (backlog #56's measured
verdict). This one would have gone red on any developer who signs commits.

## What r10 confirmed by mutation rather than reading

It mutated `reviewed_state` in its own scratch copy and checked the new cases actually fail:
dropping `add -A`, weakening it to `add -u`, returning blob-only entries, and ignoring `repo_root`
**all went red**. It also noted `_head2 == _head` is the weakest of the new assertions — true, and
it is kept only as the variation guard's own witness that `repo_root` is load-bearing.

## ⚠ THE FIX ITSELF IS UNREVIEWED — r11 is OWED

The r10 repair touches `scripts/codex-review.py`, which is guarded code, so **every round including
r10 is now stale against the tree that ships**. By this branch's own rule the gate will report that.
This is recorded rather than worked around: the branch stops here because the session ended, not
because it converged.

**Next action: run r11 against the current tree** (and, per the gap above, the Claude half).

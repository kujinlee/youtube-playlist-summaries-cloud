# Round 5 — `mutation-early-stop` (PR #476, backlog #405) — coordinator — NOT CONVERGED (Claude half); the premise is refuted, so early stop is WITHDRAWN

Claude half: `docs/reviews/claude/mutation-early-stop-r5-claude.md`, which reviewed `fa778c50`.
REVIEW GAP: codex — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 5
fixes_nontrivial: true
subject: mutation-early-stop
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C5-B1, severity: Blocker, aim: deliverable, fix_induced: false, component: stop-rule, disposition: fixed}
  - {id: C5-M1, severity: Medium, aim: deliverable, fix_induced: false, component: stop-rule, disposition: fixed}
  - {id: C5-L1, severity: Low, aim: deliverable, fix_induced: true, component: self-test, disposition: fixed}
  - {id: C5-L2, severity: Low, aim: deliverable, fix_induced: true, component: self-test, disposition: fixed}
```

**C5-B1 refutes the premise every round rested on:** that some changed paths "cannot change what a printed red exits
with". A suite that reads a staged `.md` can turn its own exit to 0. The reviewer built that case and ran it:
early stop recorded KILLED and a full run recorded SURVIVED. Staging copies whole directories, and 69 of the 86
manifested scripts mention `docs` paths.

**Five rounds, five refutations, each of a path rule.** The rules were: a named import (r1); the environment, meaning
startup files (r2); a transitive import (r3); an unscanned directory (r4); and now a data file (r5). No path rule
over the changed set is sound. The r4 narrowing already measured **0 of the last 40 merged PRs** eligible, so the
sound remainder (a change of nothing but a manifest) is worth nothing.

**Disposition, all four findings: early stop is WITHDRAWN from this PR.** `scripts/check-plan-code.py`, its
manifest and the `ci.yml` early-stop wiring return to `origin/master`. The PR ships only `cancel-in-progress` for
pull-request runs (a superseded push's CI is cancelled) and its exact allowance in `check-merge-ready.py`. All four
findings are fixed by deletion.

**What would be sound** is filed by rewording backlog #481: the SUITE stops at its own first named `[FAIL]` and exits
non-zero. The exit is then the suite's own, not a harness inference from text
([[a-harness-cannot-read-a-cause-from-a-childs-text]]). A mutant that breaks that exit path survives, which is the
correct verdict.

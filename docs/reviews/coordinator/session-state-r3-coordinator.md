# Round 3 — `session-state` — coordinator — ⟳ NOT CONVERGED (bet LOST); THRASHING → SPLIT

```yaml
round: 3
fixes_nontrivial: true
subject: session-state
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CF1, severity: High, aim: deliverable, fix_induced: true, component: attribution, disposition: deferred}
  - {id: CF2, severity: Medium, aim: deliverable, fix_induced: true, component: attribution, disposition: deferred}
  - {id: CF3, severity: Low, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
  - {id: CF4, severity: Low, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: CF5, severity: Low, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: CF6, severity: Low, aim: deliverable, fix_induced: false, component: enumeration, disposition: fixed}
  - {id: CF7, severity: Low, aim: deliverable, fix_induced: false, component: attribution, disposition: deferred}
  - {id: CF8, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: codex — round 3 alternates to the Claude half (`review-method.md`, *The protocol*, step 4; backlog #339).

`C` = Claude, tree `d24832e6`. HELD — the stable core: no Unicode code point breaks a line (every code point swept;
fullwidth `＝` survives but cannot start a line); the real hook with a 100 s `git fetch` and a pipe-holding `gh` finished
in 40 s with CANNOT RUN and the END marker; 38/38; 19/19 mutations killed by their named cases.

- **CF1 (P1, fold-induced, DEFERRED to backlog #367):** the r2 redesign's `origin/master..<head>` range excludes only
  master, so a branch stacked on another feature branch, or one that merged another, showed the PARENT PR's commit
  subject and review file as its own.
- **CF2 (P2, deferred):** after a failed fetch a master commit from another PR was shown as this PR's latest commit.
- **CF3 (fixed, by removal):** the mid-PR deadline path was never exercised. The per-branch reads it guarded are gone.
- **CF4, CF5, CF6 (fixed):** no ledger size cap (139 MB took 35 s and put 120 MB into the block); `--add ""` made an
  unremovable entry and `--done ""` printed the block; a timeout message lost "timed out" to the 160-character cut.
- **CF7 (deferred, partly fixed):** usefulness — failing checks are now NAMED; the review-file count (which included
  verdict JSON) leaves with the attribution half.
- **CF8 (fixed, prose):** the PR body's "master commits merged in are never reported" is withdrawn with the feature.

**Q5, answered as the method asks:** rounds 2 and 3 both carried findings CAUSED by the previous fold, in ONE
component — per-branch attribution (r2: filename-convention record lookup; r3: the range that replaced it). That is
THRASHING → architecture review, for that component. And the ladder agrees: a lost REDESIGN escalates to SPLIT,
which `review-method.md:323` defines as shipping the stable half and making the unstable half its own subject.
PR #410 now ships only gh-derived PR state, the ledger, `clean()` and the budget; the attribution half is backlog #367.

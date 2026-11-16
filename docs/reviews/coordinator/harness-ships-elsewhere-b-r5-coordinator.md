# Round 5 — `harness-ships-elsewhere-b` — coordinator — CONVERGED (Claude); 0 findings; the round-5 bet HELD

```yaml
round: 5
fixes_nontrivial: false
subject: harness-ships-elsewhere-b
halves:
  claude: ran
  codex: gap
findings: []
```

REVIEW GAP: codex — alternation

Reviewed: PR #594 at `eca9ada3`, after the round-4 fold (`8c14fd8e`, records `eca9ada3`). Half:
[`claude/harness-ships-elsewhere-b-r5-claude.md`](../claude/harness-ships-elsewhere-b-r5-claude.md) (0 BLOCKER,
0 MAJOR, 0 MINOR), its verdict recorded by `scripts/record-review-verdict.py`. Round 5 is past the round cap
(`docs/review-method.md` §0 Q4c): only a BLOCKER would have been folded; there was none.

**The round-5 bet HELD.** It said round 5 would find no input where a file whose only path from the repository
root passes through a private root's object is planned to ship, and nothing caused by the r4 fold in `staging`.
The half attacked Codex r4 #1 in every shape the brief named — a private root or skills home `-> ..`, `-> ../..`,
a two-hop chain through a tracked or UNTRACKED intermediate, a `..` that leaves and re-enters the repository, an
absolute link to the repository — and each was refused at `plan`. Legitimate shapes (an ordinary private
directory, a link to a sibling outside that does not hold the repository, no `.claude` at all, `.claude/plans -> .`,
`.claude -> .`) staged. The top-of-loop check was searched for a read or decision made before it and none was
found. The three new mutations were applied by hand to a copy and each turned its named case red; pin 70 equals
the manifest. Self-tests: staging 97/97, isolation 71/71.

## Dispositions

None: no findings.

## Outcome

The loop stops here for slice B. Rounds 2, 3 and 4 each carried a fix-induced finding in `staging`; round 5,
over the r4 fold, carried none. The `split` route named in round 4 is not taken. Backlog #659 (isolation probe
budget, dropped call-site mutations) stays filed.

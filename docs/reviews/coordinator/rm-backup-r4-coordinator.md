# Round 4 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Claude: 1 BLOCKER, 8 MAJOR, 3 MINOR); the BLOCKER FOLDED, the rest FILED (round cap)

REVIEW GAP: codex — alternation (round 4 runs ONE half; round 3 was Codex).

Subject: PR #608, branch `rm-backup-hook`, reviewed head `0286e19b`. Half: `docs/reviews/claude/rm-backup-r4-claude.md`.
The fold was written by the coordinator in the scratch repo `fold-r1` (commit "fold r4") and copied into this branch.

```yaml
round: 4
fixes_nontrivial: true
subject: rm-backup
halves:
  claude: ran
  codex: gap
findings:
  - {id: R4-1, severity: Blocker, aim: deliverable, fix_induced: false, component: glob, disposition: fixed}
  - {id: R4-2, severity: Major, aim: deliverable, fix_induced: false, component: glob, disposition: filed}
  - {id: R4-3, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: filed}
  - {id: R4-4, severity: Major, aim: deliverable, fix_induced: false, component: backup, disposition: filed}
  - {id: R4-5, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: filed}
  - {id: R4-6, severity: Major, aim: deliverable, fix_induced: false, component: cwd, disposition: filed}
  - {id: R4-7, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: filed}
  - {id: R4-8, severity: Major, aim: deliverable, fix_induced: false, component: scan, disposition: filed}
  - {id: R4-9, severity: Major, aim: deliverable, fix_induced: false, component: scan, disposition: filed}
  - {id: R4-10, severity: Minor, aim: deliverable, fix_induced: false, component: variables, disposition: filed}
  - {id: R4-11, severity: Minor, aim: deliverable, fix_induced: false, component: command-position, disposition: filed}
  - {id: R4-12, severity: Minor, aim: deliverable, fix_induced: false, component: backup, disposition: filed}
  - {id: S26, severity: Medium, aim: deliverable, fix_induced: true, component: variables, disposition: filed}
  - {id: S27, severity: Medium, aim: deliverable, fix_induced: true, component: variables, disposition: filed}
  - {id: S28, severity: Medium, aim: deliverable, fix_induced: false, component: variables, disposition: filed}
```

**Round 4 is the round cap** (`review-method.md` §0 Q4c): findings are FILED unless a BLOCKER. All non-BLOCKERs
are in **backlog #686**.

**The BLOCKER, folded.** R4-1: `rm -f [^k]*` — bash reads `[^k]` as "not k", Python's `glob` as "`^` or `k`", so the
hook backed up `keep` (the one file bash keeps) and missed the rest; `[[:digit:]]*` matched nothing, so nothing was
backed up. Fix: `[^` is rewritten to `[!` before globbing; a POSIX bracket class (`[[:x:]]`, `[[=x=]]`, `[[.x.]]`)
is refused. Case: "a `[^k]` bracket is a negation as in bash; a `[[:digit:]]` class is refused (r4 R4-1)"; two
mutations, one per half, each killed by it.

**The push-time findings on `0286e19b` (S26–S28), each probed by the coordinator** — the hook's `plan` on a real
fixture, then bash on a copy:

| Id | Command | Hook | bash deleted |
|---|---|---|---|
| S26 | `S=a.tmp; >/dev/null eval S=b.txt; rm -f $S` | backs up `a.tmp` | `b.txt` |
| S27 | `X=a.tmp; o=-v; printf $o X b.txt; rm -f $X` | backs up `a.tmp` | `b.txt` |
| S28 | `X=a.tmp; trap 'X=b.txt' DEBUG; rm -f $X` | backs up `a.tmp` | `b.txt` |
| — | `f(){ X=b.txt; }; f; rm -f $X`; `E=eval; $E X=…`; `${E}al X=…` | refused | — (not holes) |

`fix_induced: true` on S26/S27: round 3 narrowed `eval` and `printf` to command position / their own flag, and both
holes are the edge of that narrowing. S28 (`trap`) is the residual the round-3 bound names: a setter matching none of
the allowlist's shapes.

**Why none of the rest is a BLOCKER.** The hook guards against the agent's own accidental `rm`, not an adversary
composing a bypass; a BLOCKER here is a silent miss in a command someone types without trying to. `[^k]*` is that
(an ordinary glob); `trap`, `$_`, `CDPATH=`, a redirect before `eval`, `r\`+newline+`m` are not.

**Measured after the fold (scratch "fold r4", copied into this branch):** self-test 124/124; scoped mutation sweep
94/94 killed, each by the case it names; replay over 18,296 past Bash calls: 184 `rm`s seen, 116 refused — 0 newly
refused, 0 no longer refused against round 3.

**Thrashing — not armed.** Round 4's findings are not caused by round 3's fold except S26/S27 (`variables`); round
3's fold-induced findings (S23/S24) were also `variables`, caused by round 2's fold. That is two consecutive rounds
with previous-fold-induced findings in one component — **the rule's shape is met by the push-time reviews**, not by
a review half. Recorded rather than argued away: the answer to "can a redesign remove it" is the one backlog #686
names — the hook re-derives bash's meaning in Python before the command runs, and every disagreement is a silent
miss. Asking bash itself (`compgen -G`, or backing up from a traced dry parse) would remove the glob and
time-of-check classes; it is filed, not built on this PR, because round 4 is the cap.

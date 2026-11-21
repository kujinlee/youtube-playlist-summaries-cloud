# Round 5 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Codex: 1 BLOCKER, 1 MAJOR); BOTH FIXED by one change; THRASHING ARMED on `glob`

REVIEW GAP: claude — alternation (round 5 runs ONE half; round 4 was Claude).

Subject: PR #608, branch `rm-backup-hook`, reviewed head `1a4c5906` (a delta review of `0286e19b..1a4c5906`, the r4
fold). Half: `docs/reviews/codex/rm-backup-r5-codex.md`. The fold was written by the coordinator in the scratch repo
`fold-r1` (commit "fold r5") and copied into this branch.

```yaml
round: 5
fixes_nontrivial: true
subject: rm-backup
halves:
  codex: ran
  claude: gap
findings:
  - {id: R5-1, severity: Blocker, aim: deliverable, fix_induced: true, component: glob, disposition: fixed}
  - {id: R5-2, severity: Major, aim: deliverable, fix_induced: true, component: glob, disposition: fixed}
```

**Past the round cap** (`review-method.md` §0 Q4c): only a BLOCKER is folded. R5-1 is one; R5-2 is fixed by the SAME
change (not a separate fold), and its case is in the same test, so it is recorded `fixed`, not filed.

| Id | Command | Round-4 hook | bash 3.2 deleted (probed by the coordinator) |
|---|---|---|---|
| R5-1 | `rm -f [\^a]*` / `rm -f ["^"a]*` | read as "not a": backed up `^note`, `banana` | `a1`/`apple` and `^note` — `apple` LOST |
| R5-2 | `rm -f [^a/b]*` (dir `[^a`, file `b]one`) | rewrote the dir part to `[!a`: backed up nothing | `[^a/b]one` |

Both are `fix_induced: true`: at `0286e19b` (before round 4's fold) both deleted files were in the plan.

**The cause, one sentence.** The lexer drops quotes and backslashes before the hook sees a target, so `[\^a]` (a
literal caret) and `[^a]` (a negation) arrive as the same text — no rule that picks ONE reading can be right for both.

**The fix — read every reading, not the right one.** `bash_brackets` now returns every Python-glob reading bash might
mean: each negating set both negated (`[!…]`) and literal (its negator moved last), every combination (more than four
negating sets is refused), plus Python's own reading of the raw target, which covers a set bash leaves literal because
it spans a `/`. The plan is the union. An extra backup is harmless; a missed one is the defect. The POSIX-class
refusal is unchanged. Case: "a caret the lexer cannot tell quoted from negating is read BOTH ways; a set spanning `/`
as Python reads it (r5 R5-1/R5-2)", expectations checked against bash 3.2 (`g/[\^a]*` → `^note a1`; `g/[\!a]*` →
`!x a1`; `g/[^a/b]*` → `[^a/b]one`). The round-4 case's expectation widened: `[^k]*` now also backs up `keep`, the
literal-caret reading. Two mutations added (drop the literal reading; drop the raw target), each killed by the case.

**Measured after the fold (scratch "fold r5", copied into this branch):** self-test 126/126; scoped mutation sweep
98/98 killed, each by the case it names (the first sweep had a survivor — the literal `^` reading is also Python's raw
reading, so the case gained a `[\!a]*` target, where only the new reading catches it); replay over 18,407 past Bash
calls: 186 `rm`s seen, 118 refused, 0 no longer refused against round 4.

**Thrashing — ARMED, on `glob`.** Round 4's S29 was caused by round 4's first R4-1 fix (the regex scanner) and was
`glob`; round 5's R5-1 and R5-2 are caused by the S29 fix, also `glob`. Two consecutive rounds with findings caused by
the previous fix, in one component: the rule's shape, met by review halves and push-time reviews together. Phase 6 is
convened BEFORE the merge (backlog #680 records a PR that merged without one):
`docs/reviews/architecture-review-2026-11-20-rm-backup-glob.md`.

**Can a redesign remove it?** This fold is the answer for brackets: the hook no longer tries to choose bash's reading,
so the class "the hook chose a reading bash did not" cannot recur for a bracket set — it can only over-back-up. The
wider answer, asking bash itself to expand targets, stays in backlog #686; the Phase 6 review judges whether it is
needed now.

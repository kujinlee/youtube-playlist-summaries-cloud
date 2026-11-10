# Round 7 — `plan-586-redesign` — coordinator — Claude NOT CONVERGED: the freeze still trusts the runner's clock; the ladder reaches DEFER

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-6 fold, `git diff bdcd6c56 02f7e18d`, reviewed by Claude at
`docs/reviews/claude/plan-586-redesign-r7-claude.md` (1 BLOCKER, 1 MAJOR, 1 MINOR). The BLOCKER was run on the
extracted Task 7.2/7.3 code, with a control.

```yaml
round: 7
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
```

## What held

- A report that may not loosen cannot replace an observation.
- The guard's rebuild reproduces a replacement and refuses a HEAD that kept the first record.
- An older agreeing record meeting a newer disagreeing one only moves toward the true attempt count.
- A skew of 1 day or less is closed by the margin.

## F1: the r6 fold's unfreeze rule cannot see the run it unfreezes

The listing is capped at about 10 days (backlog #595), and a run becomes final only after 31. So a run with a final
record is never in the listing, and "a later disagreeing listing unfreezes it" never fires. Safety rests on
`observed_at` alone, and that is the runner's clock: a runner 2 days fast freezes run 55 before GitHub's re-run
deadline, and a legal re-run's miss is never compared.

**The class is the runner's clock, so the fix removes it.** `observed_at` is taken from the `Date` header of
GitHub's own response to the listing call, so it and `run_created_at` come from one clock. The report fails
(CANNOT RUN, nothing written) when the runner's clock and that header differ by more than one hour, which is an
alarm, not the defence. The 1-day margin stays. The prose stops claiming that the listing overrules a premature
observation "from any cause". It says what is true: a final record is out of the listing's reach, and its safety
is the server-clock comparison against GitHub's documented 30-day re-run limit.

Cases: the reviewer's 2-days-fast runner (with the header, nothing freezes early, and the miss latches); a
divergence over 1 hour gives CANNOT RUN; the adjacent pass is a runner within 1 hour whose header is past +31 days,
which freezes.

## F2: the r6 cases fed `settled` a listing production can never return

They listed a run older than 31 days. Rewrite them against a listing that honours the cap (a final run is ABSENT),
and keep one case that pins the absent-run path.

## F3: "newest" was ordered by each runner's clock

This is moot under F1: every `observed_at` is now GitHub's clock. Add one case where two records are ordered by
header time.

## The ladder

`plan-586-redesign` has tried accrete, redesign and split. The split bet (r7 finds no BLOCKER) is scored
`continued`; the next and last route is **DEFER**, which the `key-link` unit used the same way. The fold above is
the minimal BLOCKER fix. The class is FILED as a backlog row: a ledger whose freeze depends on a time bound needs
the bound and its evidence from one clock, and Task 7's implementation review must re-attack it on the built
code. Round 8 is Codex, on the final tree, BLOCKER-only. If it converges, the plan PR opens; if it does not, the
owner is asked.

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

## Fold

Applied 2026-11-10 to the plan (Task 7.2: `github_time`, `clock_errors`, `CLOCK_ALARM`, `CannotRun`, the
`observed_at` step of the report, the `settled` prose and the cases; Task 7.3: the `final_runs` schema prose and the
absorb comment), spec §2 / §8.6, and backlog #596. The YAML above is unchanged: all three dispositions held.

- **F1 (fixed; class filed as backlog #596):** `observed_at` is GitHub's clock, the `Date` header of the report's
  repository call (`github_time`), a call the report already makes, so no call and no predicate deciding not to look
  is added. It is that call and not the listing's response because it is made BEFORE the listing (keeping
  `observe_final`'s ordering) and `--include` would put headers in front of `--slurp`'s array; both are GitHub's
  clock. The report is CANNOT RUN when the runner's clock differs from the header by more than 1 hour
  (`clock_errors`), an alarm. `SKEW_DAYS = 1` stays. The "from any cause" sentence is replaced: a recorded run is
  out of the listing's reach, its safety is the server-clock comparison, and the unfreeze clause is kept,
  fail-closed, reaching only a run a re-decision adds. Pinned by: the reviewer's construction A (2-days-fast runner
  → CANNOT RUN; with the header, `final_runs` empty, the capped listing leaves #620 unsettled at +2, +10, +37 days,
  the re-decided miss latches; this case goes RED on the r6 code: `final_runs` records 55 from the runner's clock and
  `settled` returns True); a divergence of 1 h 0 min 1 s fast and slow → CANNOT RUN, exactly 1 h → none; the
  adjacent pass (runner 59 min fast, header past +31 days → recorded at the HEADER's time, frozen with 55 absent);
  the header parser (none, two, unparseable, no blank line → `CannotRun`; lower case, LF, `+0100` → parsed).
- **F2 (fixed):** the r6 B1 cases are rewritten against a listing that honours the cap: Codex's 2 s reproduction
  with the run ABSENT (no record → not settled → re-decided miss latches), and the absent-run path pinned (record +
  capped listing → settled; the same archived → settled; a record at exactly +31 days → not settled). The
  contradiction case stays only as a labelled direct unit case of the kept clause; the r6 "agreeing listing at
  attempt 1" adjacent pass now uses the capped (empty) listing.
- **F3 (fixed):** moot under F1 (every `observed_at` is a header time); one case orders records by header time
  (`newest_finals` reads the later archived record; the absorb keeps the record against an earlier header time and
  replaces it with a later one).

Extracted Task 7.2 + 7.3 blocks run under `python3 -I` with the r5, r6 and r7 cases: 110 assertions, all pass. The
F1 case run against the r6 blocks (02f7e18d) fails: `F1 A: nothing freezes early (final_runs
empty): got {'55': {'attempts': 1, 'observed_at': '2027-02-01T10:00:01Z'}}`, and with that check softened, `F1 A: +2d,
55 absent from the capped listing -> NOT settled: got True`.

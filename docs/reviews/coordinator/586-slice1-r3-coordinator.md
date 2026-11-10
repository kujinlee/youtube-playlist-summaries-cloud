# Round 3 — `586-slice1` — coordinator — Claude NOT CONVERGED; the route changes to SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: PR #557 (DRAFT), branch `586-slice-1-strace`, the round-2 fold (`19d6de5e`, `e89789ff`) reviewed by Claude
at head `e89789ff` in `docs/reviews/claude/586-slice1-r3-claude.md` (1 High, 2 Medium, 3 Low).

```yaml
round: 3
fixes_nontrivial: true
subject: 586-slice1
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: removal-detection, disposition: split}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: true, component: removal-detection, disposition: split}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: true, component: strace-fixtures, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: true, component: removal-detection, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: true, component: measurement-doc, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: strace-merge, disposition: fixed}
```

C1-C6 are the review's F1-F6. C2's RULE predates round 2 (not fix-induced); the doc claim that leaned on it was
written by the round-2 fold, so the finding is recorded fix-induced.

## C1 (High, not fix-induced) — a removal through a symlink is resolved by TEXT and goes unlisted — SPLIT

`resolve` uses `os.path.normpath`, so `symlink("/home/runner", "/t/ln")` then `unlink("/t/ln/.gitconfig")` is judged
inside the copy, and `unlink("/t/ln/../x")` collapses lexically. Not fixed in the reader: adding symlink tracking
is the next special case of a class that strace text cannot close (see *Route: split*). The module docstring and the
measurement doc now say resolution is LEXICAL and the list is a LOWER BOUND; the doc's "can no longer hide one" and
"every successful … is listed" are deleted, and so is the code comment that said the same. The guarantee moves to
backlog #600.

## C2 (Medium) — a symlink inside a created directory inherits "created" — SPLIT

Same class as C1 (a path reached through a symlink). Not fixed in `kind_of`; the doc says beside the headline 0 that
it means "0 that this reader can see", naming F1 and F2 as the bounds. Backlog #600.

## C3 (Medium, fix-induced) — three r2 behaviours survived mutation — FIXED

Three cases, each red on its mutation and green on the reader (re-applied on a scratch copy, control 68/68):
`forget` clearing only the exact path (case `r3 F3 a created directory MOVED away …`, 67/68), a seed SUM instead of
the max (`r3 F3 a target's removal count is the MAX …`, a two-seed record 3 vs 5, 67/68), and
`targets_with_not_created` → every target (`r3 F3 two targets, only ONE …`, 67/68). The review's low-priority
survivors (`KEEP_REMOVALS` `<=`→`<`, the merge's `[:20]`→`[:1]`) are not cased; the instrument is one-shot and slice
2 re-implements the reader with its own mutated suite.

## C4 (Low, fix-induced) — failed removals counted as removals; the merge dropped `ok` — FIXED

Each record now splits its listed removals by outcome (`external_removal_outcomes`: succeeded/failed), each listed
entry keeps `ok`, and `--merge` totals the split (`external_removal_outcome_totals`, null unless every record split
it). Four cases; reverting the split or loosening the null rule turns one red each. Run 42915171820's merged JSON
predates the split and has no `ok`, so the doc says the split is NOT AVAILABLE for that run and calls the figures
ATTEMPTS. No measurement run was triggered for it.

## C5 (Low, fix-induced) — how 63,720 is made, and the red TRACE_FACTOR witness — FIXED

The doc now says each removal total is the SUM over targets of the MAX over that target's two seeds, not a count of
calls, and that run 42915171820's `TRACE_FACTOR` witness (`scripts/regen-pages.py`, seed 0, ratio 14.18) FAILED under
strace in that run (it is in `not_green`). The committed 20 does not move. The merge comment states the aggregation.

## C6 (Low, not fix-induced) — the null-unless-every-record rule applied to two fields — FIXED

`--merge` counts records analysed by `analyse_log` (`analysis_coverage`: analysed, records, and the `log_missing`
(target, seed) list, which nothing read before). Every analysed table — `syscalls`, `ioctls`, `at_fdcwd_decorated`
(and its count), `refusal_triggers`, `deleted_labels`, `unresolved_removals` — is null unless every record was
analysed. Cases: a merge with one log-missing record nulls four of those tables and names the record; a fully
analysed merge reads them. Loosening to "any record analysed" turns 4 red; not reading `log_missing` turns 1 red.

## Route: split

The round-2 route (`redesign`: list everything, annotate only) is recorded `continued` with r3 LOST. Rounds 1-3 each
found a new way an external removal escaped: r1 an `O_CREAT` open counted as creation, r2 stale creation evidence
that exempted a removal, r3 lexical resolution through a symlink. "No removal of a pre-existing path outside the
copy" is a NEGATIVE that strace text cannot prove; each round can only add a special case, and suites create
symlinks at run time (`symlink` in 31 of 92 targets, run 42893595762). So slice 1 STOPS claiming completeness:
the list stays a measured LOWER BOUND, and backlog #600 owns the guarantee — enforced by isolation (fake HOME,
read-only or absent paths outside the copy) or by the slice 2 refusal rule (plan Task 2.2, which now points at #600),
before slice 4's `record-reads` job runs on master. The reader gains no symlink rules. New prospective row, route
`split`: round 4 (Codex) finds no BLOCKER, and its non-BLOCKER findings are FILED (round cap).

## Thrashing: armed

Round 2 and round 3 both carried findings caused by the previous round's fix in the removal-detection component
(r2: X2-X5 from the r1 fold; r3: C2's doc claim, C3, C4, C5 from the r2 fold). That is the Phase 6 arming condition
(`docs/dev-process.md`, two consecutive rounds whose findings came from the previous round's fix, one component).
Phase 6 is scheduled by the coordinator as the first item of 2026-11-11; it is NOT run in this fold.

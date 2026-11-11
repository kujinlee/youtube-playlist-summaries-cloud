# Round 3 — `seed-varied-sweep` (backlog #506, its last part) — coordinator — CONVERGED (Claude), nothing folded

```yaml
round: 3
fixes_nontrivial: false
subject: seed-varied-sweep
halves:
  codex: gap
  claude: ran
findings:
  - {id: C1, severity: Low, aim: instrument, fix_induced: false, component: seed-outcome, disposition: filed}
```

REVIEW GAP: codex — alternation, per `review-method.md` -> Round topology: round 2 was Codex's, so round 3 is Claude's.
Not a failure to run.

Claude reviewed `b8acd65f` (the round-2 fold) and returned CONVERGED: no BLOCKER, no MAJOR. It re-ran both self-tests
(360/360, 60/60), put all 88 real suites through `summary_total` (88/88 recognised), compared `check-selftest-counts`'
reading against origin/master (identical on 87 of 88; the one difference declares no count), and killed all 11 new or
re-bound mutations on their own clones.

## The finding

**C1 (Claude MINOR) — FILED as backlog #530. `fix_induced: false`:** completion is decided by "a whole summary line
anywhere in the output", not by "the suite's own final summary". A suite that prints two summaries
(`check-dashboard-entry.py` does) or echoes a child's raw summary and then crashes reads as completed under that seed.
It is the residual of round 1's completion clause, which round 2 narrowed; round 2 did not cause it. It fails closed in
every measured shape, because the named-red-case comparison runs after the completion check (a truncated red set is
NONDETERMINISTIC, never a false kill when an `expect` case is red under every seed). No real suite prints the second
shape today. Filed rather than folded: the fix has to accommodate `check-dashboard-entry`'s two summary blocks.

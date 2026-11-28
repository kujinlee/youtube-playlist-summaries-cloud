# Round 2 — `sweep-timeout-754` (backlog #754) — coordinator — Codex NOT CONVERGED; X1 stands as a loosening and goes to the owner

The Codex half reviewed `02a73b68`. It found no defect in the round-1 fold: the rewritten comment's figures, the
mutation anchors and the backlog row all stand. It REJECTED round 1's answer to X1, with a reproduced case.

**X1, as Codex built it.** A shard's last mutation starts at 1,670 s elapsed and survives after 11 s. Under the
30-minute limit, the 1,680 s deadline leaves no time to re-run it, so `run_mutations` reports it SURVIVED and the
shard is red. Under 40 minutes the re-run happens. If the mutation's named case fails on the re-run, the mutation
is reclassified FLAKY and the shard is not red. Codex reproduced this by importing the module, with a controlled
clock and scripted suite results.

**The coordinator's reading.** The case is real, and round 1's claim that the limit "cannot affect verdicts" was
wrong. By check-merge-ready's own test ("not a loosening only if the branch still refuses everything master
refused"), this is a loosening, so it is the owner's decision and this PR is a HOLD.

The argument against calling it a loosening, for the owner to weigh: the red Codex describes depends on how much
time a shard has left, not on the mutation. Every manifest change or cost re-price moves that, and PR #653's
re-price moved it on every shard. Under 40 minutes the mutation gets the verdict it would get with no clock at all,
the same classification the harness gives any survivor that has time for its re-run.

| id | half | severity | finding | disposition |
|---|---|---|---|---|
| X1 | codex | Medium | a survivor too late in the budget to be re-run is SURVIVED (red) at 30 min, but can be re-run and reclassified FLAKY (not red) at 40 | escalated to the owner: a loosening by check-merge-ready's definition. This PR is a HOLD until the owner decides |

No fix was made this round, so there is nothing new for a Claude round 3 to review.

REVIEW GAP: claude — alternation (round 2 is the Codex half's turn).

```yaml
round: 2
fixes_nontrivial: false
subject: sweep-timeout-754
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: sweep-limit, disposition: escalated}
```

Review: `docs/reviews/codex/sweep-timeout-754-r2-codex.md`.

## Owner decision — 2026-11-28 06:39 PST

The owner chose **A — merge it** on a selection card: X1 is accepted as not a real loosening, because the red it
describes comes from the clock rather than from the mutation. The HOLD is lifted by that decision, not by a fix.

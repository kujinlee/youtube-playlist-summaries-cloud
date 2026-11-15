# Round 3 — `sweep-sample-nightly` (backlog #651, PR #593) — coordinator — ⟳ NOT CONVERGED; THRASHING armed, Phase 6 redesign

```yaml
round: 3
fixes_nontrivial: true
subject: sweep-sample-nightly
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C3-1, severity: Major, aim: deliverable, fix_induced: true, component: sweep-liveness, disposition: filed}
  - {id: C3-2, severity: Minor, aim: deliverable, fix_induced: false, component: sweep-liveness, disposition: filed}
  - {id: C3-3, severity: Minor, aim: deliverable, fix_induced: false, component: sweep-liveness, disposition: filed}
  - {id: C3-4, severity: Minor, aim: deliverable, fix_induced: false, component: sweep-liveness, disposition: filed}
```

REVIEW GAP: codex — alternation

REDESIGNED → sweep-sample-nightly-redesign-r1

Claude reviewed `a8a2760d` and was filed at `0646809a`. 4 findings, 0 fixed in this round, all four in component
`sweep-liveness`. C3-1 is `fix_induced: true`: it sits in the shard rule the r2 fold wrote, so the r2 bet ("round 3
finds nothing caused by this fold in `sweep-liveness` or `cost-table-builder`") LOST on `sweep-liveness` and HELD on
`cost-table-builder` (no finding there).

**THRASHING armed.** Round 2's X1 came from the r1 fold and round 3's C3-1 from the r2 fold, both in
`sweep-liveness`: two consecutive rounds with a finding caused by the previous round's fix, in one component. The
Phase 6 review is `docs/reviews/coordinator/architecture-review-2026-11-15-sweep-liveness.md`. Its answer to *can a
redesign remove it?* is yes: delete the component; the `mutation-sweep-complete` job publishes a
`full-sweep-green` artifact when the scheduled sweep on master is green, and SessionStart reads that one fact with
one GET.

⚠ `disposition: filed` here means OPEN: nothing was patched in this round, and the redesign is ordered, not built.
Each finding is answered by the redesign's build, and the redesign round's coordinator document records that.

| Finding | Severity | Disposition | What the redesign does with it |
|---|---|---|---|
| C3-1 an abandoned matrix (9 of 24 shards listed, summary job `failure`) reads as "fresh, all 9 shards green" | MAJOR | removed by the redesign | the reader never looks at a run, a job or a shard; a failed summary job uploads no marker |
| C3-2 the hook's bounded calls sum to 65 s against its 60 s limit | MINOR | folded into the redesign | one marker call of 5 s, `TIMEOUT` 30 → 25, sum 55 s; a case sums every bound against the limit in `.claude/settings.json` (review §6 step 4) |
| C3-3 a session start went from 1.8 s to 4.7–5.5 s | MINOR | removed by the redesign | 2 to 4 `gh` calls become one name-filtered GET, measured at about 0.4 s |
| C3-4 a re-run resets the run's `updatedAt`, so an old sweep reads as fresh | MINOR | removed by the redesign | the age is the artifact's `created_at`, and the marker is written on the first attempt only |

- **C3-1 is not patched as the reviewer suggested** (read the summary job and check the shard numbers for holes).
  That is the fourth step in one direction: run conclusion, then shard jobs, then the summary job. The review's §1
  table replays the nine completed scheduled runs: the summary job's conclusion is right on 9 of 9, the shard rule
  wrong on 1.
- **Nothing is filed to the backlog for C3-2..4 separately.** All three are properties of the code the redesign
  deletes. The review's §7 lists what IS to be filed with the build: a GitHub-side watchdog reading the same marker,
  as a second channel.
- **What the owner asked for does not change** (backlog #651: one nightly full sweep). One clause of the row's
  FAILS IF is reworded by the build: "no scheduled sweep completes for 36 h" becomes "no GREEN scheduled sweep for
  36 h".

## Counts

Unchanged by this round: no tracked code was edited. `scripts/session-state.py` stays at 161 cases and 145
mutations until the redesign's build, which deletes the 24 cases and 26 mutations this branch added for the
component and adds the marker reader's own.

## `fix_induced`

Round 3: C3-1 is `fix_induced: true` (the r2 fold `81dfaf73` wrote `shards_verdict`). C3-2 and C3-3 are costs the
r1 and r2 folds added but are not defects in a fix's logic, and C3-4 has been true since the r1 fold read
`updatedAt`; the reviewer marked all three `false` and that is kept.

## The redesign round

Outcome: continued. A redesign restarts the round count (`docs/review-method.md` §0 Q4c): the next round is
`sweep-sample-nightly-redesign-r1`, BOTH halves, on the built redesign.

The bet, stated before it: that round finds no finding caused by the redesign in the marker step or the marker
reader, and none of the form "a run looks swept and was not". If it does, the route is SPLIT, never a second
redesign: PR #593 ships without a liveness line, round 1's M1 becomes its own backlog row with the Phase 6 review
attached, and the owner is told the nightly sweep has no liveness check until that row lands. Most exposed: the
marker step's `if:` (no unit case can run it; its gate is the first scheduled run after merge), and the reader's
repository and branch clauses on a public repository.

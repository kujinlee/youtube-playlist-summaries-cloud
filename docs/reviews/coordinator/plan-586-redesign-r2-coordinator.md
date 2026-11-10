# Round 2 — `plan-586-redesign` — coordinator — Codex NOT CONVERGED; folding

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-1 fold, `git diff 18d72977 6d3e88ef`, reviewed by Codex at
`docs/reviews/codex/plan-586-redesign-r2-codex.md` (2 BLOCKER, 1 MAJOR).

```yaml
round: 2
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: true, component: shadow-compare-workflow, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: shadow-compare-workflow, disposition: fixed}
```

## Attribution (checked against `git show 6d3e88ef`)

- **C1 is fold-caused.** The r1 fold's guard rebuilds the absorb from the report ids a PR CHOSE to absorb, and its
  omission check covers only rows HEAD adds. Fourteen weekly absorbs of unrelated reports pass while a miss report
  that contradicts an existing `clean` row ages out of the listing window unabsorbed. Codex ran the extracted
  `absorb_epoch` to show it. This refutes the fold's stated bound ("only if no absorb runs for 76 days").
- **C2 is fold-caused.** The r1 F4 fix lists `shadow-compare.yml` runs with `status=success`. A rerun of a run that
  already published a miss is `queued` or `in_progress`, so the run drops out of the listing and the gate can open.
- **C3 is not fold-caused.** The guard step needs `GH_TOKEN`. The r1 design already called `gh` from `verify`
  without one.

**Phase 6 is not armed.** Round 2 is the first round with fold-caused findings in `ledger-trust`. Arming needs two
consecutive rounds. If round 3 also carries findings caused by this fold in `ledger-trust`, it arms.

## The fold

- **C1:** an absorb takes EVERY listed report that is not yet absorbed, never a subset. The guard rebuilds against
  all listed reports, and refuses a HEAD that leaves any listed report out. A miss that contradicts an EXISTING row
  replaces that row (a miss always wins), and the guard checks this. Restate the bound from what is then true.
- **C2:** enumerate the workflow's runs whatever their current status or conclusion, and read the report artifacts
  of every attempt. A rerun must never remove an earlier attempt's tightening evidence. Add a case with a rerun in
  progress.
- **C3:** `env: GH_TOKEN: ${{ github.token }}` on the guard step and every other new `gh` caller. Add a case that
  reads the workflow file.

Round 3 runs the Claude half (alternation). It is the last round before the cap (`docs/review-method.md` §0 Q4c).

## Fold

- **C1** — plan Task 7.3: `--absorb` takes EVERY listed report, and the new `absorb_errors` (in the plan's code
  block, beside `absorb_epoch`) refuses a listed report left out before it rebuilds over ALL listed reports; the
  absorb-gap bound is restated and attacked by simulation (Task 7.3, *an absorb gap*); spec §2 *The ledger* and
  §8.6 restated. Pinned by `ledger_change_errors` case **(r2 C1, a selective absorb against an EXISTING row)**
  (the Codex scenario, passing the r1 rebuild; run against the extracted code, it is refused while the old guard
  passes it), with **(the contradiction kept by hand)**, **(a subset choosing which non-miss row lands)** and
  **(the race, its stated cost)**.
- **C2** — plan Task 7.2 *Listing reports*: no `status` parameter, every ATTEMPT is its own report
  (`report_id = <run_id>.<run_attempt>`, artifact `shadow-report-<run_id>-<run_attempt>`), a successful attempt
  with no report RAISES; Task 7.3 identity, Task 8.1 clause 9; spec §2 *The comparator*. Pinned by Task 7.2 case
  **(r2 C2, a rerun in progress)** and Task 7.3 case **(r2 C2)** (two attempts, two identities).
- **C3** — plan Tasks 6.2, 7.2, 7.3, 8.1, 8.2: `env: GH_TOKEN: ${{ github.token }}` on every `gh` caller. Pinned by
  Task 7.2 case **(r2 C3, every `gh` caller is authenticated)** (the `GH_CALLERS` read over both workflow files),
  Task 6.2's third read and Task 7.3's F7 read.
- **Class search (not findings of this round, folded with them):** the runs window is 120 days, not 90, because a
  rerun attempt can upload 30 days after its run was created (the simulation LOSES reports with 90; Task 7.2
  case **(the 120-day window)**); the comparator reads every attempt of a PR's CI run (Task 7.2 case
  **(comparator, the same class)**); a report from the old epoch absorbed after a reset tightens the new epoch
  only (Task 7.3 case **(a report from the old epoch, absorbed after a reset)**).

The YAML block above stands: every disposition is `fixed`.

## Decision log

A prospective row for `plan-586-redesign` (route `accrete`) is appended to
`docs/reviews/decision-scheme/decision-log.jsonl` before round 3 runs; its bet is that r3 finds no section-8 BLOCKER.
**The `plan-586` `split` row is left unscored on purpose.** Its bet ("the scoped review finds no section-8 BLOCKER")
was refuted by redesign r1. But scoring it `continued` makes trigger 3 demand the next route on the OLD unit, and
the only route left is the terminal `defer`. The old unit's work continues under this subject, so that would record
a closure that did not happen. It is scored when this subject ends, against what then happened.

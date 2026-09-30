---
name: serve-path-bounding-merged
description: "FIRES-WHEN: citing #46 or PR #67 serve-path bounding — #46 serve-path bounding MERGED (PR #67, squash 0aac16d) — 7 dual review rounds, 2 redesigns; a single CONVERGED verdict was wrong 4 of 5 times"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7f3e6e7c-48cc-4021-82de-bc8d060ca442
  modified: 2026-08-11T15:26:37.713Z
---

Task #46 — the serve path made unbounded calls while holding a paid `serve_model_charge` lease, so
work could outlive the lease and the reclaim clause would admit a second paid producer (6¢ → 12¢).
**MERGED to master 2026-08-11, PR #67, squash `0aac16d`.** Branch deleted. 2671 unit / 487
integration green on master.

**Shipped:** every lease-held call bounded; the bounds sum to a build-time constant
(`SERVE_BOUNDED_MS` 140 400, `SERVE_FLOOR_SECONDS` 161); migration 0024 makes the DB refuse a lease
below it (old floor: 1 second); migration 0025 makes the settle observable.

## The lessons, in the order they cost something

1. **A required parameter defends against OMISSION, never a wrong value of the right shape.** After
   round 1 "finished", the call site could be reverted to the exact pre-fix 3×60s config with `tsc`
   clean and every test green. See [[what-mutation-testing-proves]].
2. **Mutating a wrapper is not mutating its call site.** The Task-3 mutation check passed and proved
   only that the mechanism worked, not that it was *used*.
3. **Branding a constant is not enough if its consuming local is an inference site.**
   `const attempts = …` widens to `number` and swallows arithmetic. The local needed the type.
4. **Three rounds of a detector defeated by a new expression = wrong shape, not a defect stream.**
   Object literal → decimal literal → arithmetic. The fix was making drift *unrepresentable*
   (branded budgets, `tsc` in CI), not a fourth regex.
5. **"Correct" is not "enforced".** Both reviewers agreed the population of lease-spent values was
   closed; nothing *kept* it closed. Shipping that would have reproduced, at design level, the defect
   the branch removed from its parts.
6. **Appearing in a sum is not contributing to it.** `+ X * 0` passed every text rule. The answer was
   to stop scanning and start recording — `spend()` books each term, tests read the book.

## Process facts worth carrying forward

- **A single CONVERGED verdict was wrong 4 times out of 5.** Dual review was the gate, not
  redundancy. See [[dual-review-what-it-catches]] — this adds four instances.
- **Reviewer reputation does not predict the next finding.** The reviewer that converged (wrongly)
  twice produced the sharpest finding of the review in round 3. Read them on merit, every round.
- **Worktree isolation does not isolate the database.** A reviewer ran `supabase db reset` on the
  shared stack and destroyed another's run; concurrent full-suite runs produce unattributable reds.
  Give each reviewer a worktree AND forbid stack resets in the brief.
- **Execution beats review for a whole class.** Nine plan-gate rounds missed: a `-v` flag that runs
  nothing, integration paths selecting zero tests, an enumeration behind accurate `[VERIFIED]` tags
  (2 files cited, 4 existed), and a migration with no data fix-up that was simply unrunnable.
- **Six overclaimed comments** were caught across the rounds, several authored while fixing the
  overclaim shape. A comment promising a guarantee the code does not give is its own defect.

**Never produced a finding in 7 rounds / 3 reviewers / ~60 mutations:** the bounding mechanism itself
— the static sum, required-positional boundaries, migration floor, live CHECK, refund rule.

## Open, recorded with triggers

- **backlog #28** — a reserve timeout permanently strands 6¢ and burns an attempt. A delta THIS work
  created. **DEFERRED by user decision 2026-08-11**: the 5s threshold is a tuning knob, measure p99
  on a realistic system. Note the distinction recorded there — tuning moves the FREQUENCY, never the
  severity; a fired timeout leaves the 6¢ unrecoverable at any threshold.
- **backlog #29** — `supabase/migrations/` guards are invisible to `check-guard-coverage.py`.
- **backlog #30** — `TRUNCATE` granted to `anon`/`authenticated` on every money table (Supabase
  platform default, unreachable via PostgREST). Class-wide revoke, not per-table.
- **spec §3.5.1** — a late `put` can still clobber a newer model; now logged, fix is backlog #25.
- `scripts/check-schema-gates.sh` still exits 1 on ADR-0007 residue — verified identical on clean
  `master`, unrelated to this work.

# Round 5 — `plan-586-redesign` — coordinator — Claude NOT CONVERGED: one BLOCKER in `settled`; the age assumption becomes an observation (a removal was measured unworkable)

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-4 fold, `git diff 5ecf2954 442fcc1b`, reviewed by Claude at
`docs/reviews/claude/plan-586-redesign-r5-claude.md` (1 BLOCKER, 1 MAJOR, 3 MINOR). Every BLOCKER claim was run on
the plan's extracted Task 7.2/7.3 code.

```yaml
round: 5
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: true, component: plan-text, disposition: filed}
```

## What held

B1's fix held: the exact-identity `held_by_archive`. The reviewer ran Codex's reproduction, the same PR at another
push, another mutant or seed, empty evidence, and the conflation and canonicalisation attacks, and all of them latch.

## F1 is the fourth fold-caused round in `ledger-trust`, and this time the answer is to REMOVE, not patch

r2 C1, r3 F1, r4 B1, r5 F1. Every one of them was a predicate that decides **not to look**: a status filter, a subset
absorb, an archive hold by PR number, and now `settled`, which freezes a run by its age (older than 30 days, GitHub's
re-run limit) without ever having observed its final attempt count. *Can a redesign remove it?* The common cause
is not the predicates themselves. Each one stood on an **assumption** about what it was skipping. The redesign
replaces that assumption with an **observation**. `held_by_archive` keeps its place, because it held.

⚠ **Corrected before the fold, and kept here rather than rewritten.** This document first said: delete `settled`,
because "removing it costs calls, not correctness". That claim was never measured, and it was wrong. The fold agent
stopped on it, as its brief required. Re-deciding a PR downloads every attempt's artifacts, about 100 calls per PR.
The scan window is every PR merged since GENESIS: 505 in 120 days. That is about 50,000 calls per daily report
against `GITHUB_TOKEN`'s 1,000 an hour. The report could never finish, its staleness clause would close the switch
every day, and the deliverable would be gone. It fails closed, but it is useless.

Decision-log row: route `redesign` (the plan-586-redesign accrete bet scored `continued`). Its prediction was
amended for the same reason, before any review of it.

## The fold (round cap: only the BLOCKER, plus what its fix makes moot)

- **F1: freeze on an OBSERVATION, never on age.** This is the reviewer's own statement of when freezing is safe.
  - A push is frozen only when a report has **observed** its run with these three facts, and the push row records
    that observation (`final_observed_at`):
    - `status: completed`, with no attempt in progress;
    - the recorded attempt count;
    - an observation time later than `run_created_at` + 30 days.
  - Until then, the push is compared against the run's current attempt count.
  - Attempt counts and status come from **one paginated listing** of the CI workflow's runs (`run_attempt`, `status`),
    created within the last 31 days. They never come from a call per run.
  - Cite GitHub's documented 30-day re-run limit in the plan.
  - State the daily call bound **from the code**. It must fit the 1,000-per-hour budget with room for the rest of
    the report.
  - Also bound the PR scan window by a stated fact (artifact retention, the re-run limit), or explain why the
    frozen rows already bound the work.
  - Cases:
    - the run-55 re-run at day 30 (compared, not frozen);
    - an attempt still running at the last report before day 31 (not frozen while running);
    - a run aged 31 days never observed after day 30 (not frozen until observed);
    - the adjacent pass: a run observed completed at day 31 with an unchanged count is frozen, and the row absorbs
      without churn.
- **F2:** an empty push list is never frozen. This is the same vacuous-`all` class the r4 fold fixed in
  `held_by_archive`. Add a case.
- **F4:** a null run field is not frozen and does not raise. Add a case.
- **The fold agent's check, kept:** the only other `all(` over a possibly-empty list is in `decide_pr`. With no
  pushes it decides `not a sample`, which clause 5 ignores, so it decides no omission or hold.
- **F3 (filed):** `miss_evidence` counts a `differing` item that did not replay as a miss, so a later stable miss on
  it is held. A per-item replay record is a schema change past the cap. The reviewer rates it MINOR: the item was in
  a miss row the owner reset. File as a backlog row.
- **F5 (filed):** the prose "a pre-epoch PR can only latch" overlooks `q1_probe_delta`. File, together with the
  question of whether that delta is per-epoch evidence at all.

Round 6 is Codex, scoped to this fold only, BLOCKER-only.

## Fold

Applied 2026-11-10 to the plan (Task 7.2 `settled`/`final_runs`/`observe_final`/`runs_now_from_listing`, Task 7.3
`absorb_epoch` + epoch schema) and spec §2 / §8.6. The YAML above is unchanged: every disposition held.

- **F1 (fixed):** a push is frozen only by an OBSERVATION — a report that listed its run `completed` at the push's
  attempt count after `run_created_at` + 30 days records `final_runs[run_id] = {attempts, observed_at}`; age alone
  never freezes. Two deviations from the fold as written, both stated in the plan: (a) the observation lives in the
  EPOCH's `final_runs`, not on the push row, because archived epochs are verbatim and an archived row could
  otherwise never be marked (it would be re-decided at ~100 calls a day for ever); it loosens, so `absorb_epoch`
  takes it only from a report that `may_loosen`, first observation kept; (b) the one listing reaches back
  `LISTING_DAYS = 45` (30 + 15), not 31, so 14 failed reports in a row still leave one that observes. No other
  predicate decides not to look. Call bound, from the code: 1 + ⌈N/100⌉ + ⌈R/100⌉ ≈ 1 + 16 + 46 = **~63 calls a
  day after a year** (R from 710 CI runs in 7 days × 45 days; N from 493 merged PRs in 120 days), ~937 to spare
  under 1,000/hour. Pinned by the Task 7.2 cases A2 (re-run at day 30 → miss), B1 (in_progress at day 30 →
  pending, then compared), never-observed (absent → not settled), the `observe_final` boundary at exactly
  +30 d, the adjacent passes (frozen with an empty listing; next day byte-identical; archived row frozen by the
  active record; re-decided clean at attempt 2 then frozen), and the Task 7.3 absorb cases (recorded only from a
  `may_loosen` report; guard rebuild refuses a dropped or invented entry; a new epoch carries none).
- **F2 (fixed):** `settled` requires `row["pushes"]` non-empty before `all(...)`; pinned by pushes `[]` → not
  settled for not a sample / inconclusive / clean, adjacent one frozen push → settled.
- **F3 (filed):** backlog #592.
- **F4 (fixed):** a null `run_id`, `run_created_at` or `attempts` is not frozen and raises nothing (`settled`,
  `final_runs`, `observe_final`); pinned by the three null cases, a missing key, and `observe_final` with a null.
- **F5 (filed):** backlog #593, with the question of whether `q1_probe_delta` is per-epoch evidence.
- **Found while stating the bound, not a review finding:** deciding NEW PRs costs ~100 calls each, so a peak day or an
  outage backlog exceeds 1,000/hour and the report saves nothing (predates this fold; fail-closed) — backlog #594.

Extracted Task 7.2 + 7.3 blocks run with these cases under `python3 -I`: 40 assertions, all pass.

# Round 4 — `sweep-sample-nightly` (backlog #651, PR #593) — coordinator — CONVERGED; stopped at the round cap

```yaml
round: 4
fixes_nontrivial: false
subject: sweep-sample-nightly
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X4-1, severity: Minor, aim: deliverable, fix_induced: true, component: docs, disposition: filed}
```

REVIEW GAP: claude — alternation (round 3 was the Claude half; rounds 2+ alternate, `docs/review-method.md` → *Round topology*). The r3 coordinator's bet named a round with both halves. The usage zone was WIND-DOWN ("no new review loop"), so one half ran. The decision-log row records that the prediction held on its finding clause only.

Codex round 4 (`docs/reviews/codex/sweep-sample-nightly-r4-codex.md`) reviewed `c7755050`, the Phase 6 redesign `8721e5e8` (`docs/reviews/coordinator/architecture-review-2026-11-15-sweep-liveness.md`) and the whole PR: **CONVERGED**, 0 BLOCKER, 0 MAJOR, 1 MINOR. The self-tests it quoted: check-plan-code 506/506, session-state 150/150, sweep-costs 36/36, check-merge-ready 400/400.

| # | Severity | Finding | fix_induced | Disposition |
|---|---|---|---|---|
| X4-1 | MINOR | `docs/dev-process.md`'s sweep row says "no completed sweep in 36 h"; the code flags no GREEN scheduled master sweep | true (prose the redesign left behind) | FILED backlog #655 (round cap) |

**The redesign held.** Nothing was found in the marker writer or reader, and nothing of the form "a run looks swept and was not". The thrashing that armed Phase 6 is not continuing.

Outcome: stopped. The stream closes at round 4 (`docs/review-method.md` §0 Q4c).

## The merge gate's HOLD, verified line by line by the coordinator

Codex answered 7 of the 10 flagged lines "not a loosening". It answered the other three as a finding: `0085414c8cfa`, `960f273307d8` and `07931f9e4c36` (`scripts/sweep-costs.py:136`–`:138`). Master refused every `schedule` log. The branch accepts a `schedule` log whose verdict line declares a well-formed seed list, and divides each gap by the length of that list. Codex itself calls this intentional, and it is:

- **It is the round-1 Claude M2 fix, which backlog #651 requires.** Once master no longer sweeps on each merge, a nightly `schedule` run is the only full sweep CI produces. Refusing it would leave the cost table with no source.
- **A guessed divisor is still refused.** A `schedule` log with no seed list, or with a damaged one, is still refused (`seed_count`).
- **`sweep-costs.py` is not a gate.** It is a hand-run builder of the shard cost table (`NO-CALLER:`): no hook or CI step runs it. When the table does not cover the manifest, `check-plan-code` falls back to round-robin, loudly.

So the "loosens a gate" HOLD is not a gate loosening, and the house rule applies: merge when the HOLD is verified false.

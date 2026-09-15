# record-review-topology — round 9, coordinator adjudication

**REVIEW GAP:** claude — not invoked; built by a worker fork that cannot spawn subagents. All nine
rounds are Codex-only and **the Claude half is owed before merge**.

## Why a ninth round existed

Master moved while this branch was in review (#297 merged), and the merge touched
`scripts/check-plan-code.py` — guarded code. **The branch's own rule then made every prior round
stale against the merged tree**, so r9 reviewed the merge resolution itself, dispatched against the
uncommitted merge so it saw exactly what the merge commit would contain.

That is a real cost of the rule, stated rather than hidden: *a branch that must merge master to
resolve a conflict in guarded code owes another round.* It is also correct — the merged result is
code no earlier round had seen.

## Round 9 — Codex, `gpt-5.5`

`docs/reviews/codex/record-review-topology-r9-codex.md` · verdict
`docs/reviews/verdicts/record-review-topology-r9-codex.verdict.json` (`gate_ran: true`).
**CONVERGED — no findings.**

What it verified rather than accepted:

- **The derived total.** Parsed the merged `EXPECTED_MUTATIONS` with `ast`: 43 keys summing to 592,
  matching the manifest row sum. Compared against BOTH parents — no key lost from either; vs master
  the only change is `check-review-recorded.py` 6 → 23, vs `4ade1a12` the only addition is
  `check-storage-independence.py` at 16. The number was derived from the dict, never from either
  side's narration, and r9 re-derived it independently.
- **The append-only log.** Both `## 2026-09-13` entries present and not truncated; all seven dated
  headers in the file parse through `check-dashboard-entry.py`; no conflict markers survive.
- ⭐ **The rule under a merge — the case nothing had tested.** In a scratch merge commit,
  `merge-base(origin/master, HEAD)` becomes `3168f028`, so `branch_verdicts(added)` counts only this
  branch's r1–r9 verdicts. **Master's own `schema-gates-ci-r*.verdict.json`, which arrive with the
  merge, are on disk but NOT counted** — the rule does not read another branch's testimony as its
  own. That was question 3 in the brief precisely because it was the plausible way a merge could
  break it.
- **CI wiring.** Master changed `ci.yml` and added `schema-gates.yml` but touched none of
  `check-review-recorded.py`, `codex-review.py`, `check-review-rounds.py`. The PR-only gate still
  runs exactly once; the new workflow neither duplicates nor suppresses it.

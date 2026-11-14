---
name: a-costbenefit-finding-expires-when-the-denominator-moves
description: "FIRES-WHEN: about to act on a cost/benefit verdict filed before the code changed — ⭐ Phase 6 said FLATTEN the seven-layer verification stack because its cost dominated. After #71 gave the renderer a seam, the SAME layers defend four pages at the same cost — the recommendation inverted without a word of it being wrong. Re-measure a cost/benefit finding before acting on it if anything it divided by has changed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8e2946ca-210f-40fa-a95f-012c8dc525e5
  modified: 2026-08-31T04:24:45.530Z
---

**The rule:** a cost/benefit verdict is a RATIO, and it is only as current as both sides. Before acting on any
*"X costs too much for what it buys"* finding, ask what it divided by and whether that has changed since (seams,
consolidation and deletion all move denominators). If it has, re-measure both sides before retiring anything — and
expect a **re-scope**, not a yes/no.

## History

**Architecture review 2026-08-30 §2** listed a seven-layer verification stack around the dashboard
and argued for **flattening** it: *"its cost is now the dominant cost of changing the dashboard."*
That was true when written. Candidate 1 (backlog #71, PR #180) then gave the inline renderer a seam,
and **the same layers now defend four page generators instead of one, at unchanged cost.**

Nothing in the finding became *wrong*. Its **denominator** moved, and a cost/benefit verdict is a
ratio. Cost per page quartered; the recommendation inverted.

**Measured 2026-08-30, per layer** (cases from the run, not a grep):

| file | cases | mutations proving them non-vacuous |
|---|---|---|
| `gen-dashboard.py` | 209 | 47 |
| `page_markup.py` | 78 | 14 |
| `check-dashboard-entry.py` | 46 | 12 |
| **`check-plan-code.py`** | **145** | **0** |

**The verdict is LEVEL, not FLATTEN.** The two cheapest layers cost one case each, and one of them
(`count_drift`, the docstring case-count) caught a real drift in PR #181 unprompted — retiring it
would have removed a guard that was actively working. What the re-measure *does* expose is an
unevenness nobody had named: the runner is 1,696 lines, every one of the 73 mutation verdicts passes
through it, and it is **the only layer nothing checks in return**. Its own comments record two guards
whose deletion left its suite green (`count_drift` inline, round 5; `_drift_rc`'s call — *"deleting
it left 92/92 green"*).

**Feasibility measured, not assumed** (scratch probe, not committed): adding `check-plan-code.py` as
a 4th mutation target ran **4 files / 75 mutations / 0 survivors with clean controls**, and
immediately exposed a stateful-canary defect in a guard written minutes earlier. Not circular — the
orchestrator is the repo copy, the target is the temp copy.

**Why:** a finding that divides one quantity by another is only as current as both. Seam work,
consolidation and deletion all move denominators, and the finding does not announce that it has
gone stale — it still reads as a live recommendation.

Related:
[[gates-detect-defects-not-design]] (Phase 6 is the design gate) and
[[check-the-assumption-not-just-the-code]] (measure the constraint; 3× on #36 the framing was wrong).

## Outcome (2026-08-30)

Candidate 4 closed as answered-no-flattening (dispositions in `docs/reviews/architecture-review-2026-08-30.md`, with a
warning that *"candidate 4" must not later be read as "we agreed to flatten it"*). Its residue, backlog #74, merged as
PR #182 (`a5a012c`): `scripts/mutations/check-plan-code.json`, 21 entries; 47+14+12+21 = **94** mutations, 0 survivors;
`--self-test` 145 → 158. Status ticks merged as PR #183 (`afbba55`) because the merge tick was not written before #182
opened. Building it validated the premise: of 17 candidate mutations **4 survived at 152/152** (2 equivalent, **3 real
gaps**, one the fix written for Codex in PR #181 the day before, shipped with no case — see
[[fixing-a-premise-is-not-covering-the-branch]]).

- ⚠ **A guard can fire on its own test fixtures** (`home_escapes` flagged the file proving it). Resolved by a per-line,
  TOKENISED `# not-a-home-escape: …` reason — an executable route cannot be exempted by any comment.
- ⚠ **CI cost: `--mutate .` 13s → 3m13s**, measured; the lever is parallelising, not dropping coverage.
- ⚠ **Take an `expect` FROM THE RUN, never predict it** (third occurrence: *"matched 0 red case(s)"*).

See [[mutation-harness-home-redirect-state]].

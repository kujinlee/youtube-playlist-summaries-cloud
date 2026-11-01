# Round 5 — `stalled-work` (PR #452, backlog #410) — Claude adversarial half

Subject: the round-4 fold, `git diff ade9855b..a0579158` (`pr_node_problem`, the strict `own_prs`, cases 175 -> 183,
mutations 80 -> 84). Head reviewed: `a0579158`. All probes ran in a scratch copy (`git archive a0579158 scripts
.claude/hooks`) against a throwaway repository with a bare `origin`, through the REAL hook script
(`.claude/hooks/stalled-work.sh`) with a stub `gh` on `PATH`. The worktree was not edited. Nothing under `.claude/plans/` was read.

**Claim under test:** "no gh or git input the hook cannot measure produces silence or a pass; it produces CANNOT RUN or a
visible UNKNOWN."

## Findings

### R5-1 — Minor — a head commit dated in the FUTURE reads as fresh: silence in the hook, exit 0 in the CLI
- **Where:** `scripts/check-stalled-work.py:361` (`head_commit_ts` accepts any parseable date) and `:431-436`
  (`pr_item`: `age = int(now - commit_ts)`, then `fmt_age` clamps a negative age to `0m`).
- **Input:** an own-repo draft whose gh node has `commits.nodes[-1].commit = {oid: <headRefOid>, committedDate:
  "2099-01-01T00:00:00Z"}`.
- **Observed:** hook — no output at all (`<SILENT>`); CLI — `OK pr #5 f (draft): last commit 0m ago — nothing to do`,
  `rc=0`. The same holds for a local-store `%ct` in the future (the `local_ts` fallback goes through the same `pr_item`).
- **Why it refutes the claim:** a date after `now` is not a measurement of age; the true age is unknown, and the check
  prints "0m ago". A committer date is set by the committing client (a skewed clock, `GIT_COMMITTER_DATE`), so this is
  unlikely but not impossible. It is the same family as the BOUNDS line "a draft force-pushed without progress ... looks
  young", but that line is not about an impossible date and does not cover it.
- **Fix (cheap):** in `pr_item`, `commit_ts > now + <small skew>` -> the UNKNOWN branch, plus one case.
- **Fix-induced:** no (pre-dates r4; `head_commit_ts` and `pr_item` are unchanged by this fold).

### R5-2 — Minor — the new `headRefName` validation has no mutation entry
- **Where:** `scripts/check-stalled-work.py:384-385`; `scripts/mutations/check-stalled-work.json` has no entry whose edit
  touches `isinstance(r.get("headRefName"), str)` (the only `headRefName` edit, at manifest line 805, is `pr_item`'s
  render).
- **Input (mutation):** `    if not isinstance(r.get("headRefName"), str):\n        return` -> `    if False:\n        return`.
- **Observed:** the suite goes red via exactly `r4 F1: a non-string headRefName REFUSES` (182 passed, 1 FAILED) — the case
  exists and kills it, but nothing pins it, so a later edit that weakens the case is not caught. The fold's own note says
  "six entries pin the validation"; the fourth validated field is the one left out.
- **Fix:** add the entry above, 84 -> 85, declared sum 2649 -> 2650.
- **Fix-induced:** yes (new code in this fold, unmanifested).

No Blocking or Major finding.

## The claim, site by site (hook output, not just the CLI)

| Input (stub gh, real hook script) | Hook output |
|---|---|
| `number: 5.0` (float) / `NaN` | CANNOT RUN, "a node has no integer number" |
| `isDraft: {}` / `isCrossRepository: 0` | CANNOT RUN, "PR ?5 has no boolean ..." |
| extra fields on a node | normal STALLED-DRAFT line (ignored, correct) |
| **left alone 1:** non-hex `headRefOid` on a draft | `UNKNOWN-DRAFT ... head commit date unknown` — visible |
| **left alone 2:** `committedDate: "yesterday"`, or an int, oid not local; or no `commits` | `UNKNOWN-DRAFT` — visible |
| future `committedDate` on a draft | **SILENT** (R5-1) |
| non-hex oid on a NON-draft | silent — correct: a non-draft is never stalled by age |
| `totalCount` `"1"` or `0` beside 1 node | CANNOT RUN ("gh listed 1 of N") |
| `totalCount` `1.0` or `true` beside 1 node | passes — harmless: Python equality, the list is complete |
| a cross-repo node with `headRefName: null` | CANNOT RUN — stricter than needed, but GitHub's schema makes every validated field non-null, so a real reply cannot hit it |
| empty / negative / 2^80 `number`, empty `headRefName` | visible; ref withheld by `shape` |
| 5,000 old drafts, `totalCount` matching | hook capped at 8 lines + summary, 0.32 s |
| 30,000 nodes all needing the local store | CANNOT RUN, "git log --no-walk failed to start: Argument list too long" — visible; real gh caps at `first:100` |
| `null` node, CLI | `rc=2`, CANNOT RUN |

**Left alone 3, git parsers skipping blank lines:** `parse_refs` (`:254`) and the `local_ts` loop (`:737`) skip lines
without the expected separator. Git's own formatting output only; a skipped oid has no `local_ts`, which ends in the same
visible UNKNOWN-DRAFT. Agreed that this is not silent.

**False refusal on a real reply: none.** The real hook against the real repository accepted all 8 open PRs (4 drafts) from
the live `gh` reply; GitHub's schema declares `number: Int!`, `headRefName: String!`, `isDraft`/`isCrossRepository:
Boolean!`, so `pr_node_problem` can only fire on a malformed or partial reply.

## What I ran (all in the foreground)

- `python3 scripts/check-stalled-work.py --self-test` in the worktree: **183/183 passed**, 19.7 s wall.
- Mutations, each in a scratch copy, the suite run whole:
  - manifest entry "r4 F1: a malformed gh node is not refused: the validation result is ignored" -> red via its named
    case `r4 F1: own_prs REFUSES a null node` (and 7 others);
  - manifest entry "r4 F1: isDraft stops being a required field" -> red via exactly its named case (182 passed, 1 FAILED);
  - the unmanifested `headRefName` check removal -> red via `r4 F1: a non-string headRefName REFUSES` only (R5-2).
- The real hook script against the real repository, three runs: **1.55 s, 1.04 s, 0.94 s** (load average 16 / 11 / 28).
  All three: a STALLED block, "showing 8 of 44 (STALLED 2, STALLED-DRAFT 2, UNPROCESSED 40)", no CANNOT RUN. CLI 0.91 s.
- Full `--mutate`: skipped, as briefed.

## Verdict

**CONVERGED** — no Blocking or Major finding. The fold does what it says: every malformed node of the shapes probed is
CANNOT RUN in the hook, the three sites left alone end in a visible UNKNOWN-DRAFT, and the real reply is accepted. Two
Minors: R5-1 (a future date read as fresh, pre-existing, a one-line fix) and R5-2 (one validation unpinned, fix-induced).
The literal claim "no input produces silence" is refuted by R5-1, so it should not be stated that way until R5-1 is fixed.

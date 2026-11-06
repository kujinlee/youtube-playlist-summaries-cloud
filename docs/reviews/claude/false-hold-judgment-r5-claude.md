Reviewed head: 16b401a4e045815be370ac373db7bd96a01a75df

# false-hold-judgment — round 5, Claude half (capped round, §0 Q4c)

Subject: backlog #508, PR #522. Focus: the round-3 fold `57a1def7..9d777115`, which only Codex has
reviewed so far. That means the two-pass move/rise pairing in `failure_path_removals`
(`scripts/check-merge-ready.py`) and the section rules in `loosening_answers` (`scripts/codex-review.py`).
Already known and not re-reported here: backlog #526, #527 and #528.

## What was run (all on this worktree's HEAD; experiments in the session scratchpad, outside the repo)

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | rc 0, `328/328 self-test cases passed` |
| `python3 scripts/codex-review.py --self-test` | rc 0, `232/232 passed` |
| `failure_path_removals`, comparing master (`origin/master`), r2 (`57a1def7`) and HEAD on built diffs | see F1, F2 |
| A fuzz of 20,000 random diffs (pool: count lines at 6, 7, 9 and `9 ` with a trailing space, `strict = True`, `v = 1`; anchors `return 1`), comparing HEAD with master | HEAD flags fewer lines than master in 1,229 diffs. In 1,214 of them, a rising-count partner accounts for each line HEAD did not flag. The other 15 are pairings of identical text (below) |
| The same fuzz comparing HEAD with r2 | HEAD flags fewer than r2 in 32 diffs and more in 28. The fold changes WHICH removal an addition excuses, not how many |
| `loosening_answers`, 10 adversarial inputs (CRLF, a second heading with trailing spaces or an NBSP, no `VERDICT:`, an uppercase id, an id inside a finding's text, a dissent before the heading, a fenced earlier heading, a short SHA after `VERDICT:`) | each one fails closed or is a stated bound; see F3 |

The 15 unexplained fuzz diffs are master pairing a removed line with a re-add by its rstripped
text, where HEAD pairs by exact text (r2 Codex 1). In each one, HEAD's exact pairing excused a
near-the-failure line whose text was re-added verbatim elsewhere in the file. The
`failure_path_removals` docstring already states that limit ("a line added back identically anywhere
in the same file is a MOVE"), and #527 is filed for it. Not a new hole.

## Findings

No BLOCKER. The fold does not add a false green over master's behaviour on any input I built, except
through the intended rise exemption, and that exemption is the subject of F1.

### F1 — MINOR: which removal a rise excuses depends on line order, so a count line removed near a failure word can be excused while master flagged it

Scenario, run on all three versions. The base has a `--self-test  # 7 cases` line next to
`return 1`, and another `--self-test  # 6 cases` line more than `FAIL_WINDOW` lines away. The branch
deletes both and adds one `--self-test  # 9 cases`.

- The near line comes first in the hunk: master flags `# 7 cases`; r2 and HEAD flag `[]`.
- The far line comes first: all three flag `# 7 cases`.

The second pass gives each removal the first raised addition, in hunk order. So the single `# 9`
addition excuses whichever removal it meets first, and nothing prefers to excuse the far one.

`hold_reasons`' "fewer self-test cases" check does not catch this either. It compares the first
declared count, and `7 -> 9` rises.

- **Origin:** r2, not the r3 fold. The fold left it unchanged.
- **Impact:** low. The line is a `--self-test # N cases` count, which is prose in every instance in
  the repo (the m7 bound, stated in the `rising_count` docstring).
- **Fix:** this is #527's class (order-dependent pairing) extended to the rise pass. #527's count
  formula is keyed on identical text, so it does NOT cover this case. When #527 is fixed, let a rise
  excuse a far removal before a near one, or count rises per window the way #527 counts moves.

### F2 — MINOR: the rise pass is first-fit, not a matching, so it can over-flag (a false HOLD)

Scenario, run: two count lines at 6 and 8 are removed next to `return 1`, and lines at 9 and 7 are
added. That is a valid pairing (6→7, 8→9). HEAD and r2 flag `# 8 cases`, because 6 takes the 9 first
and nothing above 8 is left. Master flags both lines, so this is no worse than master, and it fails
closed.

**Fix, if wanted:** try the removals in descending count order, or match each one to the smallest
raised addition.

### F3 — MINOR: any 12-hex token after the `VERDICT:` line voids the whole section (a false HOLD)

Scenario, run: a section answering `0123456789ab` `not a loosening`, ended by
`VERDICT: CONVERGED at 16b401a4e045`, returns `{0123456789ab: finding, 16b401a4e045: finding}`. A
twelve-character short SHA, or any 12-hex word anywhere after the verdict line, makes the review
malformed.

This fails closed and is consistent with the stated rule ("an id named after the `VERDICT:` line is
malformed"). But the rule fires on ANY 12-hex token, not only on ids the flagged block named.

**Fix, if wanted:** count only ids that appear in an answer line, or that the flagged block named.
Otherwise, say in `flagged_block` that nothing may follow the `VERDICT:` line.

The other `loosening_answers` inputs held:

- CRLF parses.
- A second heading with trailing spaces is seen as a second heading, so the section is malformed.
- An NBSP variant ends up in `rest` with its id, so the section is malformed.
- An uppercase id fails `ANSWER_LINE`, so the section is malformed.
- A fenced earlier heading counts as a second heading, so the section is malformed.
- A dissent written BEFORE the heading is not read. That is the stated BOUND, and it does not clear the
  line by itself.

### Observation (no finding)

The coordinator's brief to this half ended with a literal `FLAGBLOCK` placeholder instead of the
block. The coordinator corrected it mid-run, from `scratchpad/fhj-flag.md`. Nothing checks that a
Claude half's brief carries the block, whereas for Codex the wrapper appends it itself. If a brief
lacks the block, the half answers nothing, and the gate HOLDs. So this fails closed, and costs only a
round.

## Answers to the flagged lines

What each id changes compared with master:

- `26a23836138b`: the signature of `failure_path_removals`. The function now exempts a removed line
  whose only change is a raised `--self-test # N cases` count. Master flagged such a line. This is the
  intended #508 (1) relaxation, and F1 bounds it.
- `795043e96b8f`: the signature of `gather`. A `head` parameter defaults to `HEAD`. `main()` (line
  1570) calls it without one, so the gate reads what master read. Only `--flagged-block` passes the
  working tree.
- `c7f21f95034a`, `6bd002a6d73a`, `e8b3c3bfbf22`: the failure-path HOLD loop in `hold_reasons`. It now
  drops ids that a review of this tree answered `not a loosening`. That is the intended #508 (2)
  relaxation.
- `f13e64d753fa`: `verdict_record` gains an optional `loosening_answers` keyword and adds that field
  only when it is given. It removes no refusal.

## Loosening answers
LOOSENING-CHECK 26a23836138b: finding: intended #508 (1) relaxation: a removed `--self-test # N cases` line whose count is raised elsewhere in the file is no longer flagged, which master flagged; pairing is order-dependent (F1)
LOOSENING-CHECK 795043e96b8f: not a loosening
LOOSENING-CHECK c7f21f95034a: finding: intended #508 (2) relaxation: a flagged failure-path line answered `not a loosening` by a review of the merging tree no longer HOLDs, which master always held
LOOSENING-CHECK 6bd002a6d73a: finding: intended #508 (2) relaxation: same loop; answered lines are dropped from the HOLD reason
LOOSENING-CHECK e8b3c3bfbf22: finding: intended #508 (2) relaxation: same loop; the HOLD message now lists only unanswered lines
LOOSENING-CHECK f13e64d753fa: not a loosening
VERDICT: CONVERGED

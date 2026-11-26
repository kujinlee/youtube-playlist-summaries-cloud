Reviewed head: 6055308eb98b7364adffa43a6e2c28c2f1863f56

# dashboard-retire-s1, review round 3, the Claude half

Scope: commit 6055308e only (11 `expect` strings in five `scripts/mutations/*.json` files, one row appended to
`docs/reviews/decision-scheme/decision-log.jsonl`), on top of 21aae50a.

## Method

- `check-reference-namespace.py`: `python3 scripts/check-plan-code.py --mutate . --only scripts/check-reference-namespace.py`
  -> rc 0, `23 mutation(s), 23 killed, 23 attributed to the case each names, 0 survivor(s)`.
- `compaction-state.py` and `explainer-serve.py`: the `--only` run was REFUSED LOCALLY by the harness's own local
  budget (14.8 min and 65.0 min estimated; "NOTHING WAS MEASURED"). So, like `goal-tree.py` and `check-plan-code.py`,
  the changed entries were applied BY HAND: `git archive 6055308e` into a scratch tree outside the repo, each entry's
  `edits` applied with a count==1 assertion on every anchor, the copy's `--self-test` run, the file restored, and the
  red cases read with the harness's own `parse_fail_names` (so the equality is the harness's `w == f`, not mine).

Result per changed expect (exact hits = number of parsed red case names equal to the expect):

| Manifest | Mutation | Expect (new) | Exact hits |
|---|---|---|---|
| check-reference-namespace | (sweep, all 23) | `6.1 a bare #N added in an ask file under docs/asks/ is refused` | attributed (sweep) |
| compaction-state | an asks problem counts as zero | `4.2 ... CANNOT RUN, never 0 and never a partial count` | 1 (base 130/130, mutant 128/130) |
| explainer-serve | a directory source reads only its own mtime | `5.2 ... the directory's own mtime did not move` | 1 |
| explainer-serve | any directory is accepted as a source | `5.4 ... still refused by the coverage rule` | 1 |
| explainer-serve | the stale reply names the directory, not the child | `5.1 ... stale, NAMING the file` | 1 |
| goal-tree | read_asks call severed | `3.1 K4: ... keyed by its stem, with no link` | 1 |
| goal-tree | old store's reader severed | `3.9 the old store's asks still show, through collect, with their /dashboard link` | 1 |
| goal-tree | an asks problem is dropped | `3.6 K5: ... and KEEPS the readable ask` | 1 |
| goal-tree | a missing decision drops the ask | `3.3 ... with a warning naming the missing block` | 1 |
| goal-tree | asks source leaves NEEDS_SOURCES | `3.5 K5: ... the asks source is NOT READ` | 1 |
| check-plan-code | backlog #498: a sibling loaded by its FILENAME is not an import | `⭐ backlog #498: a target that loads a sibling by its FILENAME ...` | 1 |

All 11 new strings are exact case names, and each mutation turns its named case red. The fix does what it says.

The check-plan-code copy's self-test also showed three `[FAIL]` lines for a missing `node_modules/typescript` and
`node_modules/markdown-it`. They appear on the UNMUTATED copy too (base 503/506, mutant 502/506): the scratch tree has
no `node_modules`. They are AMBIENT, not something this commit caused.

## Findings

### F1 (LOW): the backlog #498 entry lists the same case twice
`scripts/mutations/check-plan-code.json:2314-2315`. After the edit, both items of the `expect` list are the identical
string `⭐ backlog #498: a target that loads a sibling by its FILENAME (...) is reached through it`. The harness checks
each item independently (`unnamed = [(w, [f for f in fails if w == f]) for w in wants]`, `scripts/check-plan-code.py`
near line 2843), so a duplicate passes and is never reported. But a two-item list reads as "two cases guard this", and
there is now one. Fix: collapse to a one-item list (or a string), or retarget the second item (see F2).

### F2 (MEDIUM): the real-tree #498 case still passes, but it no longer tests #498, and its name is now false
`scripts/check-plan-code.py:7859-7861`, the case `backlog #498 on the real tree: check-dashboard-entry.py reaches
compaction-state through gen-dashboard.py`.

Moving the expect off it was RIGHT. It was not hiding a lost guard. But the case itself has become hollow:

- On `origin/master` (e96c4775), `scripts/compaction-state.py` does not name `check-dashboard-entry` at all, so it
  reached it only through `_load("gen-dashboard.py", ...)`. That is the filename-import path #498 added.
- On this branch, `scripts/compaction-state.py:488` loads `_load("check-dashboard-entry.py", ...)` directly, and
  `_names_of` puts the bare file name `check-dashboard-entry.py` among the spellings. So compaction-state is selected
  by naming the changed file directly, with no import hop.
- Measured: with the #498 mutation applied (`out |= {f'"{stem}.py"', ...}` replaced by `pass`), the real-tree case
  PASSED. Only the synthetic case went red. So the case can no longer fail under the mutation it was written for, and
  "through gen-dashboard.py" is no longer true of the real tree.

A real-tree witness for #498 still exists. I ran `select_manifests` for every `scripts/*.py` (118 paths) on the base and
the mutated copy. 76 selections differ. For example, with the mutation, changing `scripts/check-review-recorded.py` no
longer selects `scripts/compaction-state.py`, `gen-dashboard.py`, `session-state.py` and others. Changing
`scripts/check-dashboard-entry.py` still loses `session-state.py`, `gen-goals-page.py`, `gen-features-page.py` and
`check-goal-status.py`, among others. Recommendation: retarget the real-tree case to a pair that goes red under the
mutation, chosen by running it under the mutation, not from my list. Name the hop it really takes, and add it back as
the second `expect` item, which also resolves F1. If not done in this PR, file it. Not edited, per the brief.

### F3 (LOW): the decision-log row says the stream stopped at round 2, but this round exists
`docs/reviews/decision-scheme/decision-log.jsonl:373`. The row is `"outcome": "stopped", "rounds_at_termination": 2`,
and `observed` says "the stream stopped" and the 11 expects were "fixed at merge prep". A third review round over that
fix is now on record, so either the row's round count is stale, or the merge-prep fix is a separate unit that wants
its own row. Neither is a gate failure: `check-decision-scheme.py` rc 0, no FAIL line. But the row is the record
trigger 8 and the bet tally read from. Coordinator's call: update `rounds_at_termination` and `observed` after this
round, or state in the row that r3 reviewed only the manifest fix.

## Other checks

- The decision-log row parses as JSON with keys `observed, outcome, prediction, retroactive, rounds_at_termination,
  route, subject, unit`, the same shape as its neighbours.
- `python3 scripts/check-decision-scheme.py`: rc 0, 0 lines containing FAIL (4 WARN lines, all about other subjects).
- The other changed manifests have no duplicate `expect` items (scripted scan). Only the #498 entry has one.

No BLOCKER. All 11 expects are exact and attributed. F2 is a case that has become hollow, and the commit did not cause
it: compaction-state's direct import came in the slice. This commit correctly stopped relying on that case. F1 and F3
are cosmetic or record-keeping.

VERDICT: CONVERGED

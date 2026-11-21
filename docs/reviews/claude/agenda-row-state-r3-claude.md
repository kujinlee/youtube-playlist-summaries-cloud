Reviewed head: b1e98095f91188816ddf01ffdd1e729e75042e09

# agenda-row-state, round 3, Claude half (adversarial)

Subject: the round-2 fold, `git diff 81874196..b1e98095`, in `scripts/goal-tree.py` and `scripts/gen-backlog-page.py`
(PR #611; backlog #515, #611, #612). Round 3 runs this half alone, by alternation. The Codex half is a gap by alternation.

Method: I put the old (`81874196`) and new (`b1e98095`) copies of both scripts side by side in a scratch directory. Then I
ran the same inputs through each, both constructed inputs and the live corpus. Every claim below comes from one of
those runs. None is inferred from reading the code.

## Results

| Check | Result |
|---|---|
| `python3 scripts/goal-tree.py --self-test` | `581/581 self-test cases passed` (rc 0) |
| `python3 scripts/gen-backlog-page.py --self-test` | `251/251 passed` (rc 0) |
| Rows closed in `docs/backlog.md` at HEAD, old rule vs new rule | 636 rows; **229 closed under `81874196`, 229 under `b1e98095`; 0 differ** |
| The same comparison over every historical `docs/backlog.md` (`git log -- docs/backlog.md`, 377 versions, 352 parsed) | **0 rows differ in any version** |
| Live wait texts (`docs/goal-threads.md` `waits on`, the agenda and goal-tree logs), read at 2026-11-20 | 13 texts; **0 differ** between the 92-day and 120-day windows |
| Live rows where an open marker comes before a ✅ followed by a closing word | 15, every one with `sev == "done"` (a ✅ Item cell). The new clause decides **no** live row |

The full mutation sweep was not run (per the brief; CI runs it).

## Findings

### F1 — MINOR — the closing-word clause ignores position, but the corpus writes the newest state first

`scripts/gen-backlog-page.py:1482` (`or bool(CLOSING_WORD_RE.search(status))`), with the regex at `:1467`.
**Caused by the r2 fold: yes** (component `backlog-closed-rule`).

The r1 narrowing reads the FIRST marker in the Status cell as the row's current state. That matches how this backlog is
written: a new state is put at the front, and the history after it is kept (live row 231: `✅ **DONE 2026-11-15** …
PREVIOUSLY: 🟠 STILL OPEN …`; and earlier `PREVIOUSLY: **CLOSED 2026-11-03 …**`, `PREVIOUSLY (no longer true): **CLOSED
2026-10-24 …**`). The r2 clause closes the row if a ✅ plus a capitalised word appears ANYWHERE in the cell. A reopened
row that keeps its old closure in the history therefore reads closed.

Failing inputs, run through `status_closed(…, "none")` (old → new):

- `🟠 **REOPENED 2026-11-07** — its trigger fired again; previously ✅ CLOSED 2026-10-24`: False → **True**
- `🟡 **PARTLY DONE** — (1) ✅ DONE in PR #9; (2) open` (a finished half written in capitals): False → **True**
- `⏳ … ✅ FIXED in part`: False → **True**
- `⏳ pending — the ✅ MERGED tick is owed when PR #9 merges`: False → **True**
- `🟡 open — ✅ **(was 🟠)** FIXED half (1)`: False → **True**

Reach. `check-docs.backlog_marker_errors` refuses any ✅ in a Status cell whose Item cell leads with 🔴🟠🟡🟢. So the
misread happens only under an Item cell with no severity marker. That shape is live: row 327 is a REOPENED row whose
Item cell leads `⟳`, so it has sev `none` and the ratchet cannot see it. Row 231's own Status cell says it "REOPENS on the
first shard over it". Exposure today is zero: no live row and none of the 352 historical versions changes reading.

Suggested fix: honour position. Close the row by the word only when the matched ✅ comes after every open marker in the
cell, so the last state written wins when the cell is written in time order. Or close it only when the cell has no open
marker before its first ✅ other than the `FILED` that starts it. Either rule keeps the r2 m1 input
(`🟢 FILED …; ✅ FIXED …`) closed and the reopen input open. Then add the reopen input to the
`⭐ r2 Codex m1` case as a negative.

### F2 — MINOR — an open PR that only MENTIONS a ✅ row holds a finished step at ⏳, and the step now disagrees with the tree leaf

`scripts/goal-tree.py:853` (`cells_held = by_cells and bool(opened)`). `opened` is any open PR whose TITLE matches
`\bbacklog #N\b` for a live row (`:837-838`). **Caused by the r2 fold: yes** (component `agenda-step-state`). The fold
deliberately extended the hold to the case where the merge log WAS read, and at `81874196` that case read ✅.

Failing input: row 10 ✅ (`closed_rows={10}`); merged `fix (backlog #10) (#20)`; one open PR #41 titled
`File backlog #700, the follow-up found after backlog #10`; the merge log and gh both read.

| | `81874196` | `b1e98095` |
|---|---|---|
| agenda step (`by_row=True`) | `merged`, `backlog #10 ✅ in its Status cell · … via PR #20` | **`open`**, `backlog #10 ✅ in its Status cell, but an open PR names it · PR #41 open · NO CHECKS` |
| tree leaf (`by_row=False`), same sources | `merged` | `merged` |

So a finished step reads ⏳ until an unrelated PR merges, and the same row reads ✅ on the tree and ⏳ on the agenda.
Titles like that are routine here. Master subjects include `Phase 6 review of ci_flaky_contract (backlog #629): retire it
with backlog #619 …`, `… check-plan-code's _walks_dir in one walk (backlog #231)` (231 had been closed and reopened), and
`… backlog #650 files deriving every Owed row's wait`.

This is a trade, not a plain regression. The hold is right in the house flow: the ✅ tick is written on the PR branch
before the PR opens, and the tree reads `docs/backlog.md` from the checkout it runs in (`goal-tree.py:1509`). From that
worktree, a ✅ row with its PR open SHOULD read ⏳. Title matching cannot tell the two cases apart. No narrowing fixes both:
`and not hit` would wrongly show ✅ for a second slice whose first slice merged. Recommendation: do not fix it now. State it as a bound in the
comment at `:851-852` and in the `⭐ r2 Codex M1` case name. The detail text is honest (it says ✅ is in the cell), so the
cost is a false "not done" that fails safe.

### F3 — MINOR (documentation) — the stated window is one day off

`scripts/goal-tree.py:480` ("the window is the 245 days before today and the 120 after") and `:487-488` ("one over 245
days past is misread as next year's"). **Caused by the r2 fold: yes** (component `wait-date-parse`). The text was written
by this fold, and the coordinator doc repeats it.

Failing input: `wait_expired("re-check 03-20", "2026-11-20 12:00")` returns **None**. 2026-03-20 is exactly 245 days
before 2026-11-20. 2027-03-20 is exactly 120 days ahead, and `<= WAIT_AHEAD_DAYS` takes it as next year's. A date 245 days
past is already misread, not only one "over 245". The real window is 244 days back to 120 ahead (it moves by a day across a
leap year). The code is fine. Only the sentence is wrong. Fix: "the 244 days before today and the 120 after", and "one 245
or more days past".

## Refutation attempts that did not produce a finding

1. **The 120-day window: which way it errs** (brief item 3). Widening 92 → 120 moved 28 days of yearless dates from
   flagged to never flagged. Read on 2026-11-20, `back 03-01`, `until 02-21` and `after 03-19` were flagged under 92
   (`2026-03-01`, `2026-02-21`, `2026-03-19`) and are **missed** under 120 (`None`). So the change errs toward missed flags
   for dates 245 to 272 days old. That sits a little against the docstring's own "leans to the past" reasoning. Still, it
   is the bound the fold states, it only applies to waits about 8 to 9 months stale with no year written, and 0 of the 13
   live wait texts change. In the other direction, `05-01` read on 2026-01-02 (119 days ahead) was a false flag under 92
   (`2025-05-01`) and is correct under 120. That is the m2 fix working. Not a finding.
2. **`❌ NOT ✅ DONE`** reads closed under BOTH rules, because ❌ is not in `OPEN_MARKS`, so the first marker is ✅. This
   predates the fold and is not caused by it. No live row has that shape.
3. **Case and boundary.** `✅ Fixed (1) only`, `✅ Closed (1) only` and `(1) ✅ DONE_LATER` stay open (False/False), so
   case sensitivity and `\b` work as intended.
4. **gh unread.** With `errors={"gh": …}`, `src["open"]` is `{}` (`goal-tree.py:1467`), so `cells_held` is False and a ✅
   row reads `merged · the merge was not read (gh pr list: HTTP 502)` even if an open PR exists. This is the M1 class
   under the OTHER unread source. **It is not caused by the r2 fold**: it was the same at `81874196`, from r1 C7. The fold's
   comment ("whether or not the merge log was read") is accurate, since the merge log is git. One improvement would be to
   make the detail say that open PRs were not read either. I am noting it, not raising it as a finding.

## Phase 6 bearing

All three findings were caused by the r2 fold, in the components the r2 coordinator named: F1 `backlog-closed-rule`, F2
`agenda-step-state`, F3 `wait-date-parse`. Round 2's findings were all caused by the r1 fold, in the same three
components. So by `docs/dev-process.md`'s arming condition, F1 alone makes Phase 6 due for `backlog-closed-rule`: two
consecutive fix-caused rounds in one component. F1 is also the most substantive finding, because its fix reverses the r2
clause's position-free design. F2 is a deliberate precedence choice with an unstated cost, and F3 is one sentence. Whether
F2 and F3 count toward thrashing is for the coordinator to rule. F2 is weaker evidence, since the fold chose that
behaviour on purpose.

VERDICT: NOT CONVERGED

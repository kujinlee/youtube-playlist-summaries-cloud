Reviewed head: 2247577cbd822363d0e2d4013462830db592be5c

# agenda-row-state, round 1, Claude half (adversarial)

Subject: PR #611, `git diff origin/master...HEAD`, mainly `scripts/goal-tree.py` (backlog #515, #611, #612).
Method: I imported `scripts/goal-tree.py` and called `closed_rows`, `row_fates`, `derive_thread`, `derive_agenda`,
`derive`, `agenda_digest`, `agenda_now_items` and `wait_expired` with constructed inputs. The fixture `src()` mirrors the
self-test's. I also took real rows from `docs/backlog.md` through `gen-backlog-page.parse`, and re-derived the live tree
and the live agenda log with the branch's code. That re-derivation ran `collect` and wrote nothing: I did not use
`--snapshot`, because it appends to the main checkout's log. The scratch probes are in
`~/.claude-tmp/.../scratchpad/611r1-claude/` (`probe*.py`, `live.py`).

## Gates run

- `python3 scripts/goal-tree.py --self-test` exited 0 and printed `573/573 self-test cases passed`.
- `python3 scripts/goal-tree.py --print` exited 0. ⚠ It REPLAYS the last logged snapshot, which master's code wrote. It
  does not show this branch's derivation: its step 4 reads `✅ backlog #672 … via PR #606`, the pre-change reading. The
  branch's reading came from `live.py` (below).
- I did not run the mutation sweep, as the brief said.

## What held (refutation attempted, not achieved)

| Input | Observed | Claim |
|---|---|---|
| Status cell `✅ (was 🟡) …` (real rows 427, 483, 515) | `closed` True, so the step is ✅ | held |
| ✅ elsewhere in the row but not in the Status cell (real rows 29, 40, 46, 50, 67, 177, 250, …) | not in `closed_rows`, so the step is ⬜ | held |
| superseded row alone (`fates[10]=superseded`) | `superseded → backlog #12 · no PR names it yet`, state superseded | held |
| withdrawn row plus a live closed row | merged, `withdrawn · backlog #12 ✅ in its Status cell` | held |
| row 500, which does not exist (including when 500 is put in `closed_rows`) | CANNOT RUN `backlog #500 is not a row of the Items table` | held |
| `closed_rows` is None while the fates were read | CANNOT RUN `the Status cells … were not read` | held |
| a step names both a PR and a row: `backlog #12, PR #20` (row open, PR merged) | merged, following the PR | held (a stated bound) |
| `backlog #12, PR #30` (row ✅, PR open) | open | held |
| two rows, one closed | ⬜, naming only the open row | held |
| open row, a merged PR naming it, and an open PR naming it | ⏳ open, with the merged PR as context | held |
| tree leaf, `by_row` False | unchanged merge reading | held |
| `wait_expired`: today's date (`reset 11-20` at 11-20 10:00) | None | held |
| two dates, either order (`11-06 then 11-25`, `11-25 then 11-06`, ISO with `mm-dd`) | the latest wins, so None on 11-20 | held |
| year rollover: `12-30` read 2027-01-03, `12-15` read 2026-01-10 | `2026-12-30`, `2025-12-15` | held |
| a ref-like `PR #611-612`, `backlog #11-06`, an id range `611-612` | None | held |
| agenda: one expired wait and one live dated wait (`11-06` and `11-30`) | ❌ on the live wait only | held |
| agenda: both waits expired | ⬜ with `⚠ wait expired 2026-11-10: the 11-06 reset; the 11-10 freeze` | held |

**The live page (branch code, 2026-11-20 21:23):** step 4 `backlog #672` now reads ⏳ with `backlog #672 is not ✅ in its
Status cell · PR #606 (7e4036e5) merged naming it`. It agrees with the backlog. On `origin/master` row 672's Status cell
is `⏳ BUILT 2026-11-20, PR pending`, although PR #606 merged it. The new rule is correct here, and the backlog cell is
the stale party. When this merges the owner will see a done step turn back to not-done; someone should tick row 672.
I found no state that contradicts a Status cell. Steps naming backlog #511, #657 and #658 in earlier agendas read ✅ by
their cells.

## Findings

**C1 — MINOR — `scripts/goal-tree.py:862-865`: the context line attributes a merged PR to a row it never named.**
Input: a step `backlog #10, backlog #12 · x`, with `closed_rows={10}` and `merged_rows=[("aaaa111", 20, "x (backlog #10) (#20)")]`.
Observed: `('next', 'backlog #12 is not ✅ in its Status cell · PR #20 (aaaa111) merged naming it · no open PR names it')`.
PR #20 names #10, not #12. `hit` is the first merged PR naming ANY live row, and the sentence binds it to `row_open`.
The same happens with `closed_rows={12}`: `backlog #10 …` is printed correctly only because #10 is the row PR #20 named.
This is a false fact on the page. Fix: search `hit` over `row_open`, or name the row the subject matched.

**C2 — MINOR — `scripts/gen-backlog-page.py:1567` (`closed=("✅" in status)`), now load-bearing through `scripts/goal-tree.py:848`:
a PARTLY DONE row whose Status cell mentions a finished half's ✅ ticks the step, which is the backlog #515 failure by
another path.**
Input: an Items row `| 900 | 🟡 **Partly done row** … | … | 🟡 **PARTLY DONE** — items (1)-(4) ✅ merged in PR #509; item (5) open |`.
Observed: `gen-backlog-page.parse` gives `sev='med', closed=True`, so `closed_rows` contains 900 and the step reads ✅.
The real row 64 has this shape (`half (1) ✅ 2026-08-24; half (2) at #59`). It escapes today only because its Item cell
also says ✅. `contradiction_errors` checks one direction only (an Item-cell ✅ with no Status ✅). The reverse, a Status
✅ under a 🟡 Item cell, passes silently. I found no live instance today. The change does what it claims ("its Status cell
carries ✅"), but the claim does not hold the line backlog #515 was filed for. Fix (one rule, one place): file it against
the parser's closed-ness, or have the step reading also require the Item cell's ✅ marker.

**C3 — MINOR — `scripts/goal-tree.py:1925`: an expired wait still keeps an open PR out of *Running now*.**
Input: a thread `- fix · PR #21 · work · waits on the weekly reset (Fri 11-06 02:00)` with PR #21 open, at `2026-11-20 10:00`.
Observed: the leaf is `open`, and `agenda_now_items` gives `('PR #21', False, '⚠ wait expired 2026-11-06: …')`. The item
is OWED and not running, exactly as with a live wait (`'the owner'` gives `('PR #21', False, 'the owner')`).
`running = … and not waits` reads the flagged text as a wait. The flag is shown, so this is a bound, not a lie. Still,
the classification treats the expired wait as live, which the claim says never happens ("never as blocked"). Either
state it as a bound or have `running` ignore a wait that `wait_expired` flags.

**C4 — MINOR — `scripts/goal-tree.py:470` (`WAIT_DATE_RE`): non-date tokens read as dates.**
The lookbehind refuses only a digit, `#` or `-`, so a letter or a dot before the token passes. Observed on 2026-11-20:
`'Python 3.11-06'` gives `2026-11-06`, `'v1.11-06'` gives `2026-11-06`, `'sha a11-06b'` gives `2026-11-06` and
`'commit 3a11-06'` gives `2026-11-06`. Each turns a live wait into ⬜ "expired". The docstring bounds this as a flag to
re-check, so the risk is low. A `\b` or `(?<![\w.#-])` lookbehind would close it.

**C5 — MINOR — `scripts/goal-tree.py:473` (`wait_expired`): a `MM-DD` wait older than about six months is read as NEXT year and never flags.**
Observed: `wait_expired('05-20 thing', '2026-11-20 10:00')` gives None (it reads 2027-05-20), while `'06-01 thing'` gives
`2026-06-01`. "Nearest" flips at about 182 days. The docstring states the nearest-year rule but not this consequence.
Also `'02-29 leap'` read on 2027-03-01 gives None (it picks 2028). Stating the bound is enough.

**C6 — MINOR — `scripts/goal-tree.py:473`: expiry is by DAY, so a wait for a time earlier today stays ❌ until midnight.**
Input: a step whose declared wait is `the 11-20 02:00 reset`, at `now=2026-11-20 10:00`. Observed: `blocked · waits on the
11-20 02:00 reset (declared)`. The motivating case (backlog #612, a weekly reset at 02:00) therefore reads blocked for
the rest of the reset day. The docstring says "today or later is not expired", so this is intended. Reading an `HH:MM`
that follows the date would make the flag fire on the reset's own day. It is not required by the claim.

**C7 — MINOR — `scripts/goal-tree.py:842` and `:848`: a step whose rows are all ✅ reads CANNOT RUN when `git` or `gh` failed.**
Input: `backlog #12 · x`, with `closed_rows={12}` and `errors={"gh": "gh down"}` (or `{"merged": …}`). Observed:
`('cannot', 'CANNOT RUN — gh down')`. The Status-cell reading needs neither source, but the error branch runs before the
`by_row` branch. This fails closed, which is safe but needlessly loses a fact the cells hold.

**C8 — MINOR — `scripts/goal-tree.py:848`: a row named twice is printed twice.**
Input: `backlog #10, backlog #10 · dup`. Observed: `backlog #10, backlog #10 ✅ in its Status cell …` (and the same in the
open reading). The state is right. Fix: de-duplicate with `dict.fromkeys(live_rows)`.

**Not a finding: a row named only in prose.** A step like `restart the server, then re-read what backlog #12 filed` gives
`refs=[backlog 12]` (`parse_agenda` reads `REF_RE` over the whole text), so it reads ✅ while #12 is ✅. That is
pre-existing: the ref grammar is the agenda's, and master ticked the same step through any merged PR naming #12. The new
rule changes only which fact ticks it.

## Summary

The core claims hold under every input in the brief. I found no BLOCKER or MAJOR. C1 prints a false attribution, C2 is
the closest to the change's purpose (worth filing), and C3 to C8 are bounds or cosmetic.

VERDICT: CONVERGED

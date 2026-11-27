Reviewed head: 9d05ca09f5af1c8305cdf84039da0438526bd3ff

# backlog-652, review round 3: the Claude half (report only)

The code under review is `git diff 629b486f 5cd466d2`. `5cd466d2..9d05ca09` touches only `docs/reviews/`, and `git diff --stat 5cd466d2 HEAD -- scripts` is empty. All scratch work ran in `git archive` copies of HEAD and of `4ef6dfea`, kept outside the repo. The worktree was left clean (`git status --porcelain` printed nothing).

## Findings

1. **MINOR: a date one day in the past is silently stored as next year's, and the command echoes the typed `mm-dd`.**
   - Where: `scripts/session-state.py:412-424` (`parse_until`) and `:2238` (the `--set-until` echo).
   - Failing input (run on 2026-11-26): `--add y … --until 11-25` stores `2027-11-25` and prints only `ledger: added y`. `--set-until y 11-24` stores `2027-11-24` and prints `ledger: y waits until 11-24`.
   - Effect: a late or mistyped declaration becomes a live wait that raises no alarm for about a year. That is the failure #652 exists to prevent. The behaviour matches the F1 rule as specified ("first occurrence on or after"), so this is not a regression of F1.
   - The gap is what the operator sees. Neither command shows the year that was settled.
   - Suggested fix: echo the stored full date (`waits until 2027-11-24`). Optionally warn when the settled date is more than about 300 days ahead.

2. **MINOR: a goal-field (placed) entry whose date has passed has no alarm in `--print`.**
   - Where: `scripts/goal-tree.py:2446-2449` (the leaf for a placed entry).
   - Failing input: ledger `[{"id":"pg","what":"loose","on_done":"d","at":"11-05 13:42","goal":"g","waits":"the weekly reset","until":"2026-11-06"}]`, read 2026-11-15 09:00.
     - The page and `owed_idle_lines` say `pg — wait date passed 11-06, not started · loose`.
     - The `--print` leaf says `⏳ pg · loose — in flight, placed by its goal field`.
   - The placed leaf never showed waits, even on `4ef6dfea` (verified identical there for a waits-only placed entry), so this is old behaviour, not new.
   - F5's rule ("the `--print` leaf of a passed entry reads `wait date passed <mm-dd>, not started`") is closed only for entries that name a thread. Either extend it to the placed leaf or scope F5's wording to thread entries.

No BLOCKER or MAJOR findings. Neither finding is fix-induced in the sense of a regression: both outputs are unchanged from `4ef6dfea` or follow the specified rule.

## What I verified

### Item 1: every failing input from round 1, re-run on the fold
| Input (reviewer) | Result on the fold |
|---|---|
| Codex 1: `until 11-20` written 2026-11-15, read 2026-11-21 and 2027-11-16 | stored `2026-11-20`; passed on both days, never live again ✅ |
| Codex 2 / Claude 3 (F5): the `--print` leaf for 11-06 read 11-15 | `wait date passed 11-06, not started (ledger entry sub)`, with no `waits on` ✅ |
| Codex 3 (F4): two entries, same text, one passed | the wait stands, the alarm shows, the item is not idle ✅ |
| Codex 4 / Claude 2: `02-29` written 2026-03-01 or 2026-02-20 | stored `2028-02-29`; live through 2028-02-29 23:59, passed 2028-03-01 ✅ |
| Claude 1: `12-05` set on 11-20 (entry `at` 01-10); `02-15` on 10-20; `12-31` on 01-02 | `2026-12-05`, `2027-02-15`, `2026-12-31`, all live ✅ |
| Claude 4: `05-20`, `06-01`, `06-10` written 11-15 | all `2027-…`, live ✅ |

- End-to-end falsifier: the real `ledger_add(…, until="11-06", today=2026-11-05)` → `read_ledger` → `derive` → page, `owed_idle_lines` and `render_text`.
  - Live at 2026-11-06 23:59.
  - Passed (page, session-start line and `--print` leaf) at 2026-11-07 00:00, 2026-11-15 and 2027-11-16 ✅.

### Item 2: F4 shapes, each a real ledger rendered through `derive`, `agenda_html`, `owed_idle_lines` and `render_text`
Each shape used a passed date of `2026-11-06`, read on 2026-11-15.
- **Two entries, both passed, same text:** the wait is retired; one alarm; listed idle. Correct, no passed wait stays live. With different dates, both alarms show.
- **Passed plus live (`2026-11-20`), same text:** `waits for: the weekly reset; until 11-20` beside the alarm; not idle ✅.
- **Passed plus undated, same text:** the wait stands; not idle ✅.
- **Passed plus a yearless (unread) `until`, same text:** the wait stands with `until 11-20 (date not read)`; not idle ✅.
- **Passed plus the thread line's own `· waits on <same text>`:** the line's wait stands; not idle ✅. With different text on the line, both show ✅.
- **The same text on two different items** (backlog #11 passed, backlog #12 undated): #11 is retired and listed; #12 keeps `waits for: the weekly reset` and is not listed ✅. Both passed: both listed ✅.
- **Partial retirement:** a dated entry waiting on `W; the owner` (passed) beside an undated `the owner`: `W` is retired and `the owner` stands ✅.
- **Malformed stored values** (`2026-13-01`, a list, `null`, yearless `11-06`): each shows `until <v> (date not read)`, stays a live reason and is never alarmed ✅.
- **A declared worktree:** the Owed item and the leaf both drop `not started` ✅.

No live wait disappeared and no passed wait stayed live in any shape.

### Item 3: F1
- `--set-until` and `--add --until` are resolved against the day they run. Real CLI in a temp root on 2026-11-26:
  - `--add`: `11-26` → `2026-11-26` (the write day itself), `11-25` → `2027-11-25`, `11-27` → `2026-11-27`, `02-29` → `2028-02-29`, `12-05` → `2026-12-05`, `01-02` → `2027-01-02`.
  - `--set-until`, on an entry whose `at` is `01-10`: `12-05` → `2026-12-05`, `11-26` → `2026-11-26`, `11-25` → `2027-11-25`, and `none` removes the key.
  - Refused with rc 2: `2026-11-30` and `11-31`.
- `parse_until` boundaries: `12-31`@12-31 → `2026-12-31`; `01-01`@12-31 → `2027-01-01`; `02-29`@2096-03-01 → `2104-02-29`; `02-29`@2028-02-29 → that day.
  - ValueError for each of: `11-6`, `13-01`, `00-10`, `02-30`, `2026-11-06`, `none`, `""`, `None`, `"11-06 "`, `1106`.
- `until_date` reads only `YYYY-MM-DD`. It returns None for full-width digits, a trailing newline, a leading space and `0000-01-01`.
- **No-`until` output equals `4ef6dfea`.** I loaded both trees' `goal-tree.py` and ran 16 ledgers with no `until` through each. The ledgers covered: plain, waits, two same or different waits, a line wait (same or different), `after` merged, open or closed, a worktree, a placed entry, two items, a shared PR, no `at`, a later reader clock, and empty.
  - For each, I compared the full `derive` JSON (minus `at`), `agenda_html`, `render_text`, the Owed text and `owed_idle_lines`.
  - `diff base.out head.out` reported no difference across all 237 lines, and neither side raised.

### Item 4: mutations
- Pins: `expected_mutations.py` gives goal-tree 554 and session-state 172, equal to the manifest lengths.
- Every `edits` anchor in both manifests occurs exactly once in its file at HEAD (0 problems).
- Every session-state `expect` names a case that runs: all 172 manifests' expects appear as `[ok] <name>` in the self-test output.
- Hand-applied, each on a scratch copy against its script's `--self-test`:
  - **goal-tree, 28 mutations:** all 26 `#652` ones (indexes 528-553), plus 271 and 388, whose anchors lie in lines the fold changed. Each went red on its named case: `KILLED` 28/28. That includes F4's (536-540, 545-550) and F5's (551-553).
  - **session-state, 15 mutations:** 157-171, all `#652`. `KILLED` 15/15.
- **Session-state sweep question.** I mapped every session-state anchor onto the new-side line ranges of `git diff -U0 629b486f 5cd466d2 -- scripts/session-state.py`.
  - Only 157-171 (all `#652`, all hand-applied above and killed) anchor in changed code.
  - No unchanged session-state mutation anchors in fold-changed lines, every anchor resolves once, and every expect name still exists.
  - So the un-re-run sweep leaves nothing unbound. One gap remains: I did not run the 157 non-`#652` session-state mutations.

## Gates, last lines (self-tests in the HEAD archive copy, check-docs in the worktree)
- `python3 scripts/session-state.py --self-test`: `172/172 self-test cases passed` (rc 0)
- `python3 scripts/goal-tree.py --self-test`: `623/623 self-test cases passed` (rc 0)
- `python3 scripts/check-docs.py`: `Documentation integrity OK`

VERDICT: CONVERGED

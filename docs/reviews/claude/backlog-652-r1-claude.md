Reviewed head: 2b7bd19dc01a6fcb9604b4b476f839c2f541e752

Note: HEAD is 2b7bd19d, which adds only the Codex review docs on top of a2da36a2 (git diff --stat a2da36a2 HEAD: 2 files under docs/reviews). All code reviewed is a2da36a2's.

# backlog-652 r1, Claude half (read-only; all work in scratchpad copies)

## Findings

1. **MAJOR** scripts/goal-tree.py `until_date` (the year rule, ~line 725-745) with scripts/session-state.py `ledger_set_until` (~line 512).
   `--set-until` keeps the entry's original `at`, and the year is read against that `at`, not against when the date was declared. A later re-declaration therefore resolves to the wrong year.
   Failing input: entry `at` = "01-10 09:00"; `--set-until sub 12-05` run in November; read on 2026-11-20.
   `until_date("12-05","01-10 09:00","2026-11-20 09:00")` = 2025-12-05, so the item reads `wait date passed 12-05, not started` and is listed at session start 15 days before the date. Likewise `02-15` set on an entry from 03-01, read 2026-10-20, gives 2026-02-15 (passed; the owner means next February), and `12-31` on a 01-02 entry gives 2025-12-31.
   Fix direction: stamp the declaration time (e.g. `until_at`) in `--add`/`--set-until` and anchor on that; or resolve the year at write time and store a full date.

2. **MINOR** scripts/goal-tree.py `until_date` / scripts/session-state.py `parse_until`. `02-29` is accepted by `--add --until 02-29` outside a leap year and then never resolves.
   Failing input: `since` "02-20 10:00" read on 2026-03-05 or 2026-12-01: `until_date` returns None (candidates 2025, 2026 and 2027 are all invalid), so the item shows `until 02-29 (date not read)` as a live reason forever and never alarms.
   The candidate range is anchor year +-1, so only a leap year within a year of the anchor works. The case at goal-tree.py:~4090 covers only the 2028 happy path. Either refuse 02-29 at `--add` when the next leap day is not within the nearest-year window, or fall back to 02-28/03-01.

3. **MINOR** `--print` (`render_text`) shows no passed-date alarm. Page: yes (`class="waits warn">wait date passed 11-06, not started`, confirmed end to end). `--owed-idle`: yes. But `--print` has no Owed section (same on master), and the tree leaf still reads `waits on the weekly reset (Fri 11-06 02:00) (ledger entry sub)` on 11-15 (`_ledger_waits` is untouched and the leaf says nothing about `until`), so the printed tree contradicts the page. Not a regression, but brief item 3 expects "both"; either say it is out of scope in the row or add the date to the leaf detail.

4. **NIT** `until_date` nearest-year rule: a wait declared more than ~6 months ahead is read as already passed. Failing input: `since` "11-15 10:00", until `05-20`, `06-01` or `06-10`, read on 2026-11-15, resolves to 2026 (178 days back, against 186 ahead in 2027) and alarms at once. `WAIT_AHEAD_DAYS=120` governs the other yearless reader; the two now disagree about ~4-6 months. Document or accept.

## Falsifier (item 1), end to end
Real `session-state.main(["--add", ..., "--until", "11-06"])` into a temp root, `at` rewritten to "11-05 13:42", ledger read through `_SS._read_whole`/`_parse`, then `derive` + `agenda_html` + `owed_idle_lines`:
- 11-06 09:00: page `waits for: the weekly reset (Fri 11-06 02:00); until 11-06` (no warn class); owed-idle `none`.
- 11-07 00:00, 11-15 09:00, 2027-01-10: page `wait date passed 11-06, not started` in `waits warn`; owed-idle lists `backlog #11 - wait date passed 11-06, not started`.
PASS.

## Dates (item 2)
Day itself live (23:59 live, 00:00 next day passed); 12-30 read 01-02 passed (2025-12-30); 01-02 recorded 12-31 is next January; 02-29 in 2028 OK (see finding 2 otherwise); `13-01`, `00-10`, `1-6`: None in goal-tree and refused (rc 2, ledger byte-identical) by `parse_until`; unreadable or absent `since` falls back to `now` (11-06 on 11-15 is 2026-11-06). `--set-until ID none` removes the key (session-state case). An entry with no `until` carries no `until` key (fingerprint case). Wrong-year pick: findings 1 and 4.

## Mutations (item 4)
- Pins: `expected_mutations.py` goal-tree 545 = manifest length 545; session-state 167 = 167.
- Every manifest anchor in goal-tree.json and session-state.json matches exactly once in the file at HEAD (0 anchor misses).
- Hand-applied all 17 goal-tree entries with "#652" in their expect (indexes 2-18 of my filtered list), each on a scratch copy and run against `goal-tree.py --self-test`: every one goes red on a #652 case, and on the case it names (e.g. "a live or unread date is no live reason" and "an unread date is dropped" both go red on the repaired "a damaged `until`..." case). The scratch copy lacked docs/explainers, so ambient FAILs unrelated to #652 appeared in each run and were ignored; only failing #652 case names were counted.
- a2da36a2 touched only a test case (goal-tree.py ~4075-4082, after all production code, +2 lines) and two `expect` strings in goal-tree.json. No `edits` anchor changed, no production line moved relative to its anchor text, and anchors bind by text. I verified that all anchors still resolve once, so nothing was unbound. session-state sweep untouched, not re-run by me (anchors resolve; I did not hand-apply the 10 session-state mutations).

## Gates, last lines
- `session-state.py --self-test`: 170/170 self-test cases passed
- `goal-tree.py --self-test`: 616/616 self-test cases passed
- `check-docs.py`: Documentation integrity OK
- `check-selftest-counts.py`: self-test counts: 97 script(s) declare a count, every one verified by running it (4 at a time) (exit 0)

VERDICT: NOT CONVERGED

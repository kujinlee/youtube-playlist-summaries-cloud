Reviewed head: cddb19024c034096d4e5405e5a33cbb8a129e2b3

# meter-log-tail r2, Claude half (backlog #501, PR #531). Codex skips this round by alternation.

Scope: the r1 fold (`302625b4`) and the head `cddb1902`. Mandate: refute. All experiments ran in a scratch copy made
with `git archive HEAD`. Nothing in the worktree was modified except this file. `~/.claude/meter/log.jsonl` was only
read.

## Gates on this head

- `python3 scripts/check-usage-pace.py --self-test`: **374/374 passed**, rc 0.
- `python3 scripts/check-fixture-variation.py`: **rc 0** ("fixture variation OK"). R1-F1 is closed.

## Job 1: each r1 fix, mutated back by hand (one self-test per mutant, in the scratch copy)

| r1 finding | Mutant | Result |
|---|---|---|
| C1 | delete `if cut and out_of_order: return None, TAIL_OUT_OF_ORDER` | 372/374, red: the C1 case (`got 55.0`) and the earlier-window-disorder case |
| C1 (equal times) | `at < prev_at` → `at <= prev_at` | 371/374, red: the SAME-time case and two older #501 cases |
| R1-F3 | restore `at <= midnight` in the earlier-window test | 373/374, red: the R1-F3 case only (`got TAIL_MISSES_MIDNIGHT`) |
| R1-F1 | `pace_line(..., meter_why, meter_cut)` → drop `meter_cut` in `_evaluate` | 372/374, red: the R1-F1 evaluate case and the main-over-bound case |
| R1-F2 | `path, deadline, (False,))` → `path, deadline)` | 370/374, red: all four R1-F2 cases (`raised ValueError` for both spawn cases) |
| R1-F4 | drop `errors="replace"` in `_read_tail` | 373/374, red: the invalid-byte case |

Every fix is real, and each new case goes red under its own clause. I found no case that another clause satisfies
in its place. The SAME-time case passes with the whole order check removed, but it exists to pin `<` against `<=`,
and it does that. The C1 "read WHOLE" case pins the `cut and` guard, because the uncut text is out of order and
would otherwise be refused.

## Job 2: defects the fold introduced

### R2-F1 — Medium — one inverted pair anywhere in the 4 MiB tail refuses the pace line for about 9 months

`scripts/check-usage-pace.py:348` (`at < prev_at` over every row of the part) and `:359` (`if cut and out_of_order`).

**Scenario.** The order check covers every pair of rows in the whole cut part, of any window and any age. At the
measured real rate (about 100 rows a day, about 149 bytes a row), the 4 MiB part spans about 280 days. So a single
pair of rows stamped one second out of order, written once, makes `pace_line` answer `TAIL_OUT_OF_ORDER` for every
prompt, spawn and wake until that pair leaves the tail. That is about 280 days later. Nothing self-heals it short of
editing the log. The uncut log with the same rows answers normally. So this is the failure #501 exists to remove
(the guide goes dark as the log grows), brought back by one event.

**What the check protects at real scale is close to nothing.** The C1 wrong start needs today's true start row to
lie BEFORE the cut. At the bound, the cut is about 280 days back. A row stamped before today's midnight that was
appended before about 28k other rows needs either about 28k rows since midnight, or disorder that crosses the window
edge. The docstring already says the second cannot be seen. Disorder 200 days back says nothing about either case.

**Reachable, not observed.** The real log has **0 inversions in 605 rows** (11-01 02:13 to 11-07 03:03; `at` is an
integer, and the smallest gap is 2 s). The writer gives no guarantee of order, though.
`~/.claude/statusline.sh:53` is
`printf '{"at":%s,...}\n' "$(date +%s)" "$RL" >> .../log.jsonl`, and it runs in EVERY session's statusline:
- there is no lock;
- the stamp is taken before the append;
- this repo runs many concurrent agents on a machine that is often under memory pressure.

So two sessions that cross a second boundary between `date` and `>>` write an inversion. A backwards clock step
(a sleep/wake correction or an NTP step) does the same. So does any row stamped in the future (`at > now`) followed
by a correct one.

**Repro.** I built a real-shape log of 30,000 rows, 864 s apart, over 300 days: 4.47 MB, so cut. The current window
resets 3 days after midnight. I swapped one pair's stamps 200 days back so they are 1 s out of order.
```
clean                  cut True  tail (74.32, '')                 whole (74.32, '')
1s inversion 200d ago  cut True  tail (None, TAIL_OUT_OF_ORDER)    whole (74.32, '')
```

**Fix.** Scope the check to the rows that could bear on today's start: count an inversion only when the later
line's `at` (or both rows' `at`) is within a horizon such as `resets - 2 × 7 d` (this window and the one before it).
Disorder older than that cannot place a row of this window. The R1-C1 cases are unaffected, since their rows are all
near midnight. Add a case like the repro, with an old inversion and a small `limit`, that must still answer, and a
mutation that widens the horizon back to every row. A second option, which can be used as well as this one: allow a
small tolerance (for example `at < prev_at - 5`), with a case at that tolerance.

### R2-F2 — Low — dropping `at <= midnight` turns a refusal into a silent WRONG start when a row's `resets_at` disagrees with its neighbours

`scripts/check-usage-pace.py:351` (`if is_number(r) and r < resets: earlier_window = True`) and `:361`.

**Scenario.** The proof that the fold now relies on ("an earlier window's row anywhere in the part means this
window's first row follows it") needs `resets_at` to be non-decreasing in file order. The fold checks `at` for
order, but not `r`. Suppose a row after midnight carries an older `resets_at`:
- a session whose statusline still holds a stale `rate_limits` after the weekly reset;
- a one-off jitter in `resets_at`;
- such a row placed after this window's rows.

That row now sets `earlier_window`. With `before` None, the start becomes this window's first row after midnight,
while the true start lies before the cut. On r1's code (`900bf2eb`), the same input was refused.

**Repro** (`now` = midnight + 10 h, `R` = midnight + 3 d; the true start `85` at midnight − 1 h is before the cut):
```
tail = row(mid+60,88,R) + row(mid+120,30,R-7d) + row(mid+180,89,R)      # also: the stale row last; or R-1 jitter
whole log : (92.5, '')
HEAD cut  : (94.0, '')            <- wrong, no refusal
r1   cut  : (None, TAIL_MISSES_MIDNIGHT)
```
All three variants (a stale row between, a stale row last, and `R-1` jitter) give 94.0 on HEAD and a refusal on r1.

**Reachability.** It is the same as R1-F3's, which it mirrors: the part must begin after midnight, which needs more
than about 28k rows in a day. So it is practically unreachable at real rates. The real log has 0 decreases of
`resets_at` in file order and exactly two values, but it spans only one reset. It is Low. Still, the fold traded an
unreachable false REFUSAL for an equally unreachable silent WRONG answer, and that is the wrong direction.

**Fix.** Keep R1-F3's fix but make it sound:
- set `earlier_window` only for an earlier-window row seen before the first row with `r == resets` in the part;
- treat a decrease of `resets_at` in file order like an `at` inversion (refuse);
- scope it to the same horizon as R2-F1.

The R1-F3 case still answers 51 under this rule. Add the repro above as a case.

## Checked and held

- **Equal timestamps.** They count as in order (`<`), and that is pinned. The real log has integer `at` and no
  equal neighbours. Concurrent writers can produce equal seconds, and that is correctly not refused.
- **DST.** `at` is epoch seconds and the order check never touches local time. `local_midnight` and the days
  arithmetic are unchanged by the fold.
- **A reset exactly at midnight.** The rows of the previous window are at or before midnight, so `earlier_window`
  is set under either rule. The start is this window's first row, the same as uncut.
- **Two weekly resets inside the part.** Older windows' rows only set `earlier_window`. `before` and `after` admit
  only `r == resets`, so neither earlier window can set the start.
- **The R1-F5 decline.** It is sound as the code stands: a check that needs every pair cannot stop early. I
  measured `pace_line` at **0.21 s** over a 4,194,201-byte cut part. Note that R2-F1's horizon fix makes a
  newest-first walk that stops at the horizon correct again, so F5's saving would come almost free with it. This is
  an observation, not a finding.
- **Docstring.** It says "MEASURED in order: 592 rows". That is still true: 605 rows today, 0 inversions.

## Summary

All six r1 fixes are real, and each is pinned by its own case. The fold added two problems:
- **R2-F1 (Medium).** The order check is unscoped, so one second of disorder from the lock-free, multi-session
  writer would take the pace line down for about 280 days. That is the outage #501 removes.
- **R2-F2 (Low).** Dropping the midnight clause without checking `resets_at` order turns an unreachable refusal into
  an unreachable wrong answer.

VERDICT: NOT CONVERGED

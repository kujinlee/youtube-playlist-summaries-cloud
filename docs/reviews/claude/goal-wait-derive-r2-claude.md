Reviewed head: be4d48c6e4dd8430957d625649adc4dc9f041d04

# goal-wait-derive (backlog #650, PR #592) — review round 2, Claude half

Adversarial mandate: refute that the round-1 fold (`git diff 7154c97a..be4d48c6`) fixed C1–C6 and F1–F7 without
breaking anything. Read the coordinator's disposition table and both r1 reviews.

## What was run

- `python3 scripts/goal-tree.py --self-test` at be4d48c6: **537/537 passed** (3.9 s). The same result on an isolated
  `git archive` copy.
- `python3 scripts/goal-tree.py --owed-idle` against the main checkout's log: one line, `=== OWED AND IDLE: CANNOT
  VERIFY — ledger_problems not read: entry fable-compare-week: its thread is not read — refs 'backlog #630 Fable
  pilot' mus…; treat as NOT RUN ===`, rc=2, 0.32 s. The hook is silent on rc 2, so this line is the whole block.
- The newest logged snapshot (`at` 2026-11-15 06:07), loaded and pushed through `agenda_now_items` and `owed_reason`.
  With `ledger_problems` cleared, `owed_idle_lines` returns `none — every Owed item has a reason`.
- Each r1 repro was re-driven through `owed_reason`, `idle_days` and `named_prerequisites`. C1, C5, F1, C3 (DST and
  minute-ahead) and C4 (`on_done`, `Do not wait until after`) now give the corrected output.
- I ran 8 of the 28 new or rebound mutations on the isolated copy: #5, #6, #9, #16, #17, #18, #21 and #22, counting
  from 0 in the list of mutations that differ from 7154c97a. Every one turns all of its named `expect` cases red, and
  no other case newly fails. None of them names the wrong case.

## Findings

### N1 — MAJOR — the CANNOT VERIFY trigger fires only on notes that drop nothing, so the alarm shows in every session

`scripts/goal-tree.py:2291` (`OWED_IDLE_UNREAD` includes `"ledger_problems"`), read at `:2322`.

**`ledger_problems` is not an unread source in any snapshot that reaches the log:**

- A real unread ledger is a parse failure from `_SS._parse`. It also sets `errors["ledger"]` (`:1290-1294`). That
  makes `cannot` non-empty, and `append_if_changed` refuses to log such a snapshot (`:1374-1375`). The same holds for
  `needs_not_read`: it is built from the same `errors` (`:845`).
- So a logged snapshot's `ledger_problems` can hold only placement notes. These come from `ledger_threads` (`:348`,
  thread not read, goal not declared, refs already hung) and from `ref_problems` (`:806-812`).
- None of these notes drops an entry. An entry whose thread is not read is still placed by its `goal`, which the
  existing case "a goal with an UNREADABLE thread is still placed under the goal" asserts. An undeclared goal goes to
  `inflight_loose`. Both still reach the Owed list.

**The breaking input is the real data.** `fable-compare-week` is placed under `token-usage-first` and
`memory-hygiene` under `memory-hygiene`. Both are among the 4 Owed items and both carry a live recorded wait. The
honest answer is `none`, and the block instead says NOT RUN with exit 2. It will say so in every session until
someone rewrites two ledger lines that are not wrong for the Owed list. An alarm that always fires gets ignored, and
then it hides the real one.

**The guarding case passes for a reason the system cannot produce.** The case at `:3157` builds
`{"ledger_problems": ["3 line(s) not parsed"]}` with `cannot: []`. `collect` and `derive` never log that world:
parse problems always come with `cannot`. The case at `:3173` builds the same world.

**The correct condition:** take `ledger_problems` out of `OWED_IDLE_UNREAD`. Keep `cannot` and `needs_not_read` as a
defence; the logger cannot produce either today. If the notes should be visible, append a count that does not
change rc, such as `(2 ledger notes — see the goal-tree page)`. Re-base the two cases on `cannot`, which is the
reachable form of an unread ledger.

### N2 — MAJOR (caused by the F1 fix) — any ref inside a recorded wait is read as a prerequisite, the same over-breadth C4 removed

`scripts/goal-tree.py:466-476` (`wait_blockers`) and `:551-557` (`owed_reason`, `stale` and `idle`).

Every `PR #N` / `backlog #N` in a `; `-part of a recorded wait becomes a blocker. When all of them finish, the part
is "stale": it raises the `blocker done … not started` alarm, and if every part is stale the item is listed as idle.
C4 narrowed the `after` matcher precisely because a bare mention is not a prerequisite. F1's fix reads bare mentions
again, in the field the owner writes most.

**Breaking input from the real ledger.** `fable-compare-week` has the wait part `until then each fold/build
alternates Fable and Opus (PR #590: r1 Opus, r2 Fable)`. PR #590 merged (65e6f562). Through `owed_reason` this
gives the alarm `blocker done 11-14 (PR #590), not started`, beside an item that is really waiting for the 11-20
reset. PR #590 is cited there, and is not a prerequisite. That alarm appears on the page.

**A single-part variant.** `waits="the owner's answer, asked on PR #590"` with PR #590 merged gives `idle=True`.
The session block then lists it as `blocker done … (PR #590), not started`, although it waits on the owner.

**Fix shape:** count a recorded wait part as resolved by its refs only when the refs ARE the wait. For example, the
part with its refs removed is empty or only connective words (`PR #442`, `PR #442 and backlog #11`), or the part
matches `AFTER_RE`. Otherwise the part stays a reason.

### N3 — MINOR (caused by the C3/F3 fix) — an entry older than about six months now reads `idle ? days`

`scripts/goal-tree.py:497-527` (`idle_days`, the nearest-of-three-years rule).

`idle_days("05-01 09:00", "2026-11-15 09:00")` returns `None`. The rule picks 2027-05-01, which is 167 days ahead,
over 2026-05-01, which is 198 days back. Before the fold it returned 198. Any `mm-dd` entry more than about 182 days
old flips to the future year.

**Fix:** prefer the latest candidate that is not after `now`. Take a future one only when it is within a day, which
covers the DST fallback and the minute-ahead case.

The case at `:3049` still describes the OLD rule in its name: "takes the snapshot's year, or the year before when
that would be…". Rename it, and add a case with a 7-month-old entry.

### N4 — MINOR — the negation and `until` filter rejects real prerequisites

`scripts/goal-tree.py:409-411` (`_CLAUSE_RE`, `_NEGATED_RE`).

These all give `[]` from `named_prerequisites`:

- `Wait until after PR #5 merges`
- `Hold until after PR #5`
- `No rush: start after PR #5` (`:` is not a clause boundary)
- `Ship the no-op flag after PR #5` (`\bno\b` matches the `no` in `no-op`)

When nothing is recorded and PR #5 is open, the item gets `no reason recorded` and is listed as idle. That is a
false alarm, and loud, which is why this is only MINOR. "Wait until after X" is the plainest way to state a
prerequisite, and `until\s*$` rejects it. Only `not until after` / `don't wait until after` should be rejected, and
the `not` already covers those.

### N5 — MINOR — exit 2 does not only mean "printed its own CANNOT line"

`.claude/hooks/session-state.sh:22`.

`python3` exits 2 when it cannot open the script (measured: `python3 /nonexistent/x.py` gives rc=2), and argparse
exits 2 on a usage error. In both cases the hook prints no `=== OWED AND IDLE: CANNOT RUN … ===` header, only the
interpreter's stderr line. The failure is still visible, but not in the block's own NOT RUN form.

**Fix:** a distinctive code, for example 3, for "printed my own CANNOT line".

## The r1 dispositions — checked against their repros

| r1 | Result |
|---|---|
| C1 / F2 | Holds: closed unmerged / superseded / withdrawn give `prerequisite … — re-plan` |
| F1 | Holds for the repro, but see N2 |
| C5 | Holds: `waits="owner approval"` with PR #442 done and PR #451 open gives `idle=False` and is not listed |
| C2 / F5 | Fixed for an unreachable world; the reachable effect is N1 |
| C3 / F3 | Holds: DST gives 0 and one minute ahead gives 0; N3 is a new regression |
| C4 | Holds for the repro; N4 is over-rejection |
| F4, C6 / F6, F7 | Hold: two clocks are asserted, lines are bounded, and the log is read from its end |

VERDICT: NOT CONVERGED

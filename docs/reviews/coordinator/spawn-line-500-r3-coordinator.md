# Round 3 — `spawn-line-500` (backlog #500, PR #500) — coordinator — NOT CONVERGED (Claude); all findings fixed

```yaml
round: 3
fixes_nontrivial: true
subject: spawn-line-500
halves:
  codex: gap
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: meter-read, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: reserve-days, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: reserve-days, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: stop-note, disposition: fixed}
  - {id: C6, severity: Medium, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
  - {id: C7, severity: Low, aim: deliverable, fix_induced: false, component: reserve-days, disposition: fixed}
  - {id: C8, severity: Low, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
```

REVIEW GAP: codex — alternation (rounds 2+ run ONE half; Codex ran r2).

**Why a third round.** r2 CONVERGED on `a797aef8` under the owner's 08:47 rule (max(90, pace line), cap 97). At 09:29 the
owner replaced the rule with a per-day reserve: *"For example, emergency reserve is set to 5% and remaining days are 3
days(excluding today), max usage for today can be 100 - 3×5 = 85"*. `b8a1b2cd` built it; r3 reviewed that. The goal
moved by the owner's decision, so no finding below is FIX-INDUCED (none came from a previous round's fix): C1 and C6 predate
the change; C2, C3, C5 and C7 are in code the 09:29 rule added. No thrashing.

**Held (Claude, measured):** the stop equals min(97, 100 − 5 × days after today) over month ends, year ends, Feb 28,
23:59:59 and a reset before the coming midnight; a reset at or before `now` is CANNOT RUN before the stop is computed;
no meter content changes the verdict; every #500 case can fail; the stated 299 / 122 were right.

- **C1 (fixed):** 4 MiB of blank meter lines held every hook call 19.3 s (re-measured here: 19.5 s), since each line
  raised inside `json.loads`. `pace_line` now skips a line without `"seven_day"` (every row carries it) at C speed:
  0.21 s. The worst left, 4 MiB of lines that carry the marker and fail to parse, MEASURED 1.8 s; the `read_payload`
  docstring now states that bound. A case asserts the blank log reads in under 2 s; the mutation removing the skip is
  killed by it.
- **C2 + C3 (fixed as a class):** `days_after_today` counted SECONDS between midnights, so a day with a DST change was
  23/24 or 25/24 of a day, and an `isdst` guess could move the stop. It now counts CALENDAR dates from tomorrow to the
  reset's date, plus the reset's wall-clock time as a fraction. One case covers fall back (Sat 10-31 → Mon 11-02: 95,
  not 94.79), spring forward, a summer week and a month end; the mutation restoring the seconds count is killed by it.
- **C5 (fixed):** the stop is now shown ROUNDED UP (`pct_up`), so a WARN never names a stop the verdict has not reached
  (94.55% under a 94.58 stop now reads "at 94.6%"). A case and a mutation pin it.
- **C7 (fixed):** a mutation now pins the `max(0.0, …)` floor.
- **C4, C6, C8 (fixed):** "about 70%" (69.6, since the reset is at 02:00); `docs/process-checklists.md` and backlog
  row 404 no longer state 90% as the current stop; the 09:29 quote now keeps the owner's opening "For example,".

302 self-test cases, 125 mutations; the 25 mutations for this rule, and legacy entry 26 re-anchored onto `pct_up`, were
each killed by hand on a temp copy by the case they name. Per §0 Q4c, round 4 FILES anything that is not a BLOCKER.

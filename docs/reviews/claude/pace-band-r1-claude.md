Reviewed head: d7efd2eb5fbe17ae6fd35d2f9e4ec2e5a4dafae3

# pace-band r1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD`: `scripts/check-usage-pace.py`, `scripts/mutations/check-usage-pace.json`,
`scripts/mutations/expected_mutations.py`, `docs/dashboard-entries.md`.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/check-usage-pace.py --self-test` (worktree, head d7efd2eb) | 403/403 passed, 14.9 s |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-usage-pace.py` | **NOT RUN.** The harness said CANNOT RUN: `node_modules/typescript is missing under .` in this worktree. I was not allowed to create other files, so I did not symlink it. (`--only check-usage-pace.py` without the `scripts/` prefix is also CANNOT RUN: no manifest targets it.) |
| Hand mutations, on a copy of `scripts/` + `.claude/hooks/` in my scratchpad, self-test re-run per mutation | 6 mutations: 3 went red, 3 survived (below) |
| AST comparison of master vs head function bodies | `refuse_at`, `cap_at`, `days_after_today`, `rise_start`, `last_night`, `local_midnight`, `window`, `evaluate`, `prompt_output`, `gate_output` and `main` are byte-identical. `RESERVE_PER_DAY`, `STOP_CAP`, `LAST_DAY_CAP`, `RISE_END_S`, `LAST_NIGHT_S`, `HARD_LIMIT`, `WARN_AT` and `FIVE_HOUR_WARN_AT` are unchanged |
| Live CLI, Tue 11-10 09:52 PST, real cache and meter log | `OK: pace: today's band 78–80% (this week's owner override) · now 74% · started 71%, spent 3 → zone NORMAL …`, rc 0. `resets_at` 1794564000 is `2026-11-13 02:00 PST` locally, so the override key hits |

## Attack 1: is the hard stop unchanged?

Yes. Every stop function is identical (AST check above). In `_evaluate` the REFUSE branch still fires on
`weekly >= stop` before any band logic, and the `stop` it uses comes from the same `refuse_at` call. The band
never feeds `stop`. The only change on the REFUSE path is message text: on a non-last day it now carries the band
note. I checked whether REFUSE can ever sit beside a band zone that contradicts it. `band_cap = 100 − 8d` is below
`100 − 5d` for every d > 0. An override's edges are capped by `band_cap`. On the last day the zone is
USE IT ALL, and that note is dropped at the stop. So REFUSE always comes with NO NEW STARTS (or, on the last day,
with no note), never with NORMAL. CANNOT RUN paths return before `band_note` is reached, so they are unchanged.

## Attack 2: boundaries, floor, last day, override, time zones

- Zones: `weekly < low` gives NORMAL, `low <= weekly < high` gives WIND-DOWN, and `weekly >= high` gives NO NEW
  STARTS. This matches the rule. Both sides of each edge are pinned (21.9/22/29.9/30), and the manifest's
  inclusive-boundary mutation targets it.
- The floor cap binds and is tested at two starts (45 caps the top only; 50 caps both edges). When both edges are
  capped, low == high, so WIND-DOWN is empty. That follows the rule ("both edges capped").
- Last day: `now > rise_start(resets)`. My mutation moving the boundary 1 h earlier went red: the Wed 23:00
  case sits 1 h before the Thu 00:00 `rise_start` of a Fri 20:00 reset.
- Override: it hits on Tue 11-10 and misses for a window one day later. It is keyed by `local_date(resets)` and then
  by `local_date(now)`, both through `time.localtime`, so both are LOCAL dates as required.
- A window with no start% row: `day_start` returns None. Outside an override day the band is then UNKNOWN (see
  MAJOR-1).

## Attack 3: loosening

No verdict became weaker. Every input that was WARN or REFUSE on master still is: the 80% WARN, the five-hour
WARN, the last-day USE IT WARN and REFUSE all keep their conditions. The band only adds WARN (WIND-DOWN and
NO NEW STARTS go to WARN in the branch below the 80% WARN). I found no path where WIND-DOWN returns rc 0.
`OK` now carries a message (`return OK, line_note.strip()`), but `prompt_output` returns None on OK and
`gate_output` acts only on REFUSE. So the hooks' behaviour on OK is unchanged. Only the bare CLI line changed.

## Findings

### MAJOR-1: an UNKNOWN band is silent in the prompt hook, so it reads as fine

The rule: "An unknown start% must never read as fine." The dashboard entry claims the same: "When the start of the
day cannot be read, the band is called UNKNOWN, never fine." The code returns `OK, "pace: today's band is UNKNOWN
… never as fine."`. `prompt_output(OK, …)` returns None, and the prompt hook is the only channel that reaches
the session. So NOT RUN is printed only by the bare CLI, which no hook uses.

Concrete failing input: a window that is not 11-13, so the override misses. `now = 1794333000`,
`resets = now + 5 d`, cache weekly 45.
- With a meter log whose midnight row reads 20: the band is 32–40, NO NEW STARTS, and the prompt hook emits a
  WARN with `additionalContext`.
- With `--meter` pointing at a missing file, the same 45%: CLI `OK: pace: today's band is UNKNOWN …`, rc 0, and
  `--hook prompt` prints **nothing**.

So losing the meter log turns a NO NEW STARTS warning into silence. That is the "unknown reads as fine" case the
rule forbids. The behaviour is deliberate (docstring: "an UNKNOWN band … leave[s] the verdict alone"). The
self-test also pins it ("never a WARN by itself"). But the rule as given says otherwise, so the owner has to choose:
- (a) UNKNOWN is a WARN (or a once-per-session WARN, like the absent-cache notice, to avoid saying it on every
  prompt); or
- (b) the owner accepts the silence, and the dashboard sentence plus the rule text are corrected to say UNKNOWN is
  only said on the CLI.

This week's override hides the problem, because it supplies the band without start%. It returns at the 11-13 reset.
On master an unreadable pace line was also silent on OK. But on master the line was never a verdict, and now the
band is the WARN-bearing daily control, so its silence matters.

### MINOR-1: the LOCAL-date keying is untested; a UTC key survives

Mutation: `.get(local_date(now))` → `.get(time.strftime("%Y-%m-%d", time.gmtime(now)))`. Result: **403/403
pass.** The override cases sit at 08:00 and 12:00 PST, where the UTC date is the same. A case at Tue 11-10 17:00 PST
would catch it: that is Wed 01:00 UTC, so a UTC key would give the Wed band of 88–90 instead of 78–80. The same gap
exists for the `resets` key: 02:00 PST is the same UTC date. The code is correct today. The test cannot tell.

### MINOR-2: the trend constant is weakly pinned

Mutation: `+ TREND_BASE` → `+ TREND_BASE + 0.05`. Result: **403/403 pass.** The case brackets 21.108 with 21.0 and
21.2, and `pct` floors the shown value to 21.1 either way. A pair closer to the edge (21.10 / 21.11) would catch it.
The note is a guide, so this is minor.

### MINOR-3: the override's `"2026-11-12": USE_ALL, "2026-11-13": USE_ALL` entries are dead

For a Fri 02:00 reset, `rise_start` is Thu 00:00, so the last-day rule already returns USE IT ALL on both dates.
Mutation: replace both with `"2026-11-12": (95.0, 96.0)`. Result: **403/403 pass.** The "Thu use it all" case
passes through `rise_start`, not through the override. This is harmless, but the case claims to test the
override and does not. Drop the entries, or note that they are redundant on purpose.

### MINOR-4: a stale 1.5× comment remains

`scripts/check-usage-pace.py:1557`: "Start 2 → 2 + 1.5 × 98 ÷ 3 = 51." This is the retired pace-line arithmetic.
The case it annotates now asserts a refusal (TAIL_TOO_SHORT), not 51. Brief item 5 asks that comments describe the
new rule. Out of the diff's files: `docs/memory/behavior-follows-the-budget-situation.md` and `MEMORY.md` still
speak of the pace line. That memory is not part of this PR, so this is noted only.

### MINOR-5: start% has no age bound (stricter direction)

`day_start` takes the newest row of this window at or before midnight, however old it is. If the statusline was
off from Sat 10:00 to Tue, start% is Saturday's value. Tuesday's band is then measured from a lower base, and
NO NEW STARTS fires early. This error is in the stricter direction and is inherited from the pace line. But the
band is now a WARN, so a stale base costs real stops. The message does not show the row's age. One option is to say
"started X% (at <time>)" when the row is older than about 24 h.

## Mutations I ran by hand

| Mutation | Result |
|---|---|
| last-day boundary 1 h earlier | RED (the Wed 23:00 case) |
| today's key in UTC | **survived** (MINOR-1) |
| Thu override not USE_ALL | **survived** (MINOR-3) |
| trend +0.05 | **survived** (MINOR-2) |
| keep the band note beside REFUSE on the last day (`if False:`) | RED |
| capped-source tests `low > cap` | RED |

The manifest's own new entries were not run, because the harness could not run (see above). I read them, and each
names a case that exercises its edit.

VERDICT: NOT CONVERGED

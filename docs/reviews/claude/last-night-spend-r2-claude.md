Reviewed head: 0cfdc461b12a592f4f6aac4f338d7dab2829c65e

# last-night-spend — round 2, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at 0cfdc461 (backlog #523), replayed onto origin/master with PR #519 (backlog #522).
I tried to refute three things. (1) Can the last-night rule let a spawn through at or above 100%, or refuse one below it?
No. `last_night` compares absolute epochs (`now >= resets - LAST_NIGHT_S`), so it has no timezone or DST edge. `refuse_at`
then returns exactly `HARD_LIMIT`, and `weekly >= stop` refuses at 100 and allows 99.99. I probed a 02:00 PST reset at
−9 h, −8 h−0.36 s, −8 h, −7.99 h, −3 h and −1 s, with 98–100%. The last night always falls inside the last day:
`rise_start = local_midnight(resets − 86400) <= resets − 24 h < resets − 8 h`, also across a DST change. So the
"before the hard limit" USE IT text is never missing while the stop is 100. (2) Does it compose with #522? Yes.
`refuse_at` is reached only after every CANNOT RUN return in `_evaluate`, and the new branch cannot raise. The
launcher's `cannot()` paths are unchanged. One timing caveat: the launcher runs origin/master's guard, so none of
this takes effect in the hooks until the PR merges. That is by design, but it matters for "tonight". (3) Are the
mutations real? Each of the 5 new manifest entries has an anchor that occurs exactly once. I applied each one to a
temp copy and ran the self-test, and every named case went red. (The temp copy then crashed later on a hook file I
had not copied; that crash came after the named cases had already been evaluated.) I found no BLOCKER. I found
three MINOR findings.

## Findings

**M1 (MINOR) — the stop note before the last night forecasts a 99% stop that never arrives.** The input: the reset is
Sat 11-07 02:00 PST, `now = resets − 9 h` (Fri 17:00), weekly 98%. The message reads: "The stop rises over the last
day, 98.4% now and 99% from Sat 11-07 01:00 PST". In fact the stop jumps to 100% at 18:00, and the 99% plateau
(`cap_at` from `resets − RISE_END_S`) is now unreachable through `refuse_at`, because the last night (8 h) always
covers the last hour. Two things are wrong as a result: the note promises the wrong future, and the
`LAST_DAY_CAP`/`RISE_END_S` end of the rise is dead code for the stop. Fix: name the last night's start, e.g. "…and
100% (the hard limit) from 18:00", or end the rise at `resets − LAST_NIGHT_S`.

**M2 (MINOR) — the module docstring still states the old ceiling.** Lines 19–21 say the stop is "never above 97% …
except on the LAST DAY, when the 97% cap rises linearly to 99% at 1 h before the reset". That is now false for the
last 8 h, where the stop is 100%. A reader of the verdict table, which is the documented contract, would believe a
99% ceiling. Fix: add "— and for the last 8 h before the reset, the hard 100% limit (backlog #523)".

**M3 (MINOR) — the `>=` boundary of `last_night` is not pinned.** The boundary case tests ±60 s around
`resets − LAST_NIGHT_S`, so the mutation `now >= …` → `now > …` survives. The two differ only at one exact second,
so this is negligible in effect. It is filed only because the manifest claims the boundary ("a minute either side").
A case at `_ln` exactly would pin it.

Observed, not filed as findings: the weekly meter reports whole percents (backlog #524 measured `used_percentage: 98`).
So at a reading of 99 the real usage may already be 99.9, and a spawn allowed there can hit the hard limit and halt
the coordinator too. That is the owner's chosen strategy B ("If limit hit, wait until reset"), and the message says
to commit before every long step. Backlog #524 is the filed follow-up. A separate cosmetic case: at 99.9%,
`100 − 99.9 = 0.0999…` renders as "<0.1%" rather than "0.1%".

Self-test: `python3 scripts/check-usage-pace.py --self-test` → `336/336 self-test cases passed`

VERDICT: CONVERGED

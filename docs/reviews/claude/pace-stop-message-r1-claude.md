Reviewed head: 599362671e9db61eddca2d6d5408d73ffdd0a362

# pace-stop-message (backlog #525) — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at 59936267. The diff touches `scripts/check-usage-pace.py` (the stop-note
`next_at`/`next_stop` selection, the docstring, and two cases), `scripts/mutations/check-usage-pace.json` (two entries),
and `scripts/check-plan-code.py` (`EXPECTED_MUTATIONS` 146 → 148).

I tried to refute the change in five ways, each by running `evaluate`/`refuse_at` under `TZ=America/Los_Angeles`.

1. **Does the message still name a stop `refuse_at` does not apply?** With the shipped constants, no. For a reset at
   Sat 11-07 02:00 PST, I probed at −9 h and at −8 h −1 s, with weekly 98%. Both print "…and 100% (the hard limit) from
   Fri 11-06 18:00 PST", and `refuse_at(resets − LAST_NIGHT_S) == 100`. Once the last night has started, `stop ==
   HARD_LIMIT` takes the first branch, so the rising note is not shown.
2. **DST.** The reset is Sun 11-01 02:00 PST, the fall-back day. The message names "Sat 10-31 19:00 PDT", which is the
   same instant as `resets − 8 h` (18:00 PST). It is correct, because both `next_at` and `last_night` use absolute
   epochs.
3. **A non-hour reset.** With a reset at 02:37:30, the message says "from 18:37", but the last night starts at
   18:37:30. `local_time` floors to the minute, so the named time is up to 59 s early. The pre-change "99% from" text
   had the same property, and real resets are on the hour (`HORIZON_SLACK_S` comment). I did not file this.
4. **The meter is already above the stop.** That path is REFUSE, and it carries the same `stop_note`. The rising
   branch is reachable only while `stop == cap_at(now) > STOP_CAP`, which means before the last night. So the note
   is right there too.
5. **The alternative constants** (`RISE_END_S >= LAST_NIGHT_S`). One latent defect, below as m1.

The mutations: both new entries anchor exactly once in `scripts/check-usage-pace.py`. I applied each to a temp COPY of
the worktree (scratchpad, never in place) and ran the self-test there. The M1 mutation (`if False`) fails its named
case and the #510 message case (336/338). The M3 mutation (`>=` → `>`) fails its named case only (337/338). Both
cases use two distinct resets (Sat 02:00 and Fri 23:00), so no constant satisfies them, and neither case is vacuous.
The M1 case also asserts that `"99% from"` is absent from both messages.

I found no BLOCKER and no MAJOR. Two MINORs follow.

## Findings

**m1 (MINOR, latent) — the tie `RISE_END_S == LAST_NIGHT_S` names the 99% that `refuse_at` skips.** The selector is
`if resets - LAST_NIGHT_S < resets - RISE_END_S`. On a tie it takes the 99% branch, but `last_night` is `>=`, so at
that instant the stop is 100. The failing input: set `RISE_END_S = LAST_NIGHT_S = 8 h`, reset Sat 02:00 PST, now
Fri 17:00, weekly 98%. The message is "…98.9% now and 99% from Fri 11-06 18:00 PST", but `refuse_at(Fri 18:00) ==
100.0`. The comparison should be `<=`. It would also be clearer as the constant comparison it is,
`LAST_NIGHT_S >= RISE_END_S`, since `resets` cancels out. A related case: with `RISE_END_S > LAST_NIGHT_S` (10 h),
during the 99% plateau the note reads "the stop rises …, 99% now and 99% from Fri 11-06 16:00 PST", a past time,
for a stop that no longer rises. That shape existed before this change and is unreachable today. Neither case is
reachable with the shipped constants (8 h > 1 h), so this is MINOR. No case can pin it without patching the
constants. The mutation `<` → `<=` survives today, and that is correct, because the two are equivalent for these
constants.

**m2 (MINOR) — two hook headers and one repo doc still describe 99% as the top of the stop.**
`.claude/hooks/usage-pace-spawn.sh:4` and `.claude/hooks/usage-pace-wake.sh:4` both say the stop is "never above 97%
until the last day, when that cap rises to 99% an hour before the reset", and neither mentions the last night's 100%
(backlog #523). `docs/memory/a-budget-stop-is-soft-with-a-reserve.md:21` says the same thing. This change corrected
the module docstring (M2) but not these restatements, so a reader of the hook still believes the stop is capped at
99%. The headers also say "the rules … are described ONCE, in scripts/check-usage-pace.py". The cleaner fix is to
drop the parenthetical restatement and point at the docstring, not to add a third clause. The stale text came in
with #523, not with this diff, but this is the slice whose stated purpose is that wording.

Observed, not filed: the rising note now says "rises … X now and 100% from 18:00". The stop does not rise to 100. It
rises to about 98.6 and then jumps. The parenthetical "(the hard limit)" makes that readable.

Self-test: `python3 scripts/check-usage-pace.py --self-test` → `338/338 self-test cases passed`

VERDICT: CONVERGED

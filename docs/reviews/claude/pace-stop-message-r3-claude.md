Reviewed head: be509e4668cb30c19a55fc986dbec79c13d52515

# pace-stop-message (backlog #525): round 3, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at be509e46. I read row 525, both coordinator folds, the Claude r1 half, and the Codex r1 and r2 halves.

**Summary.** With the SHIPPED constants (`RISE_END_S = 1 h`, `LAST_NIGHT_S = 8 h`) I could not make the rising-stop note name a stop or a time that disagrees with `refuse_at`. I found no BLOCKER and no MAJOR. There are two MINORs:

- **m1 (latent).** With non-shipped constants the 99% branch can still name a 99% that `refuse_at` never reaches, because the reserve binds. The docstring's new claim, "names whichever of the two transitions really comes next", is false there.
- **m2.** The dashboard entry and backlog row 525 still give the round-0 counts and the round-0 selection rule.

How I tried to refute the change:

1. **A randomized oracle against `refuse_at`, shipped constants.** I loaded the module from a `git archive` copy of HEAD. For each draw I took a random reset in 2026, with an integer, `.5`, `.001`, `.999`, random-fraction or random-second offset, and a random `now` in the 40 h before it. I ran `evaluate` at 98%, parsed the rising note, and compared it with an independent oracle. The oracle took the earliest of these two transitions:
   - the rise end, if it is still ahead, is not in the last night, and `refuse_at` there is ≥ 99;
   - otherwise the last night's start.

   I formatted the oracle's time myself, using `ceil` and seconds when not aligned. I also required `refuse_at(T) >= named` and `refuse_at(T-1) < named` at the shown second T. I ran 20,000 draws in each of America/Los_Angeles, Europe/London, Australia/Lord_Howe (a 30-minute DST step) and Asia/Kathmandu (a +5:45 offset), about 7,400 rising notes per zone. **0 disagreements.** The draws include the 2026 fall-back and spring-forward weeks, and an ambiguous fall-back hour is shown with the right `%Z`.
2. **Orderings and constants.** I tried ties (8 h/8 h, 1 h/1 h), zeroes (0/0, 1 h/0), RISE < NIGHT (30 min/1 h, 7:59:59/8 h) and RISE > NIGHT (8:00:01, 9 h, 10 h, 20 h against 8 h or 2 h). Every disagreement was the single class in m1. Ties, past rise ends and RISE < NIGHT were all correct.
3. **Fractions and precision.** At any shown second the stop has already reached the named value, and one second earlier it had not. Epochs near 1.8e9 lie in the binade [2^30, 2^31), so `resets − LAST_NIGHT_S` is exact and `ceil` cannot be pushed over by an ulp. `math.ceil(inf/nan)` raises inside the `try` and becomes `Malformed`, as before.
4. **Whether a case can fail.** I applied each of the 11 new or re-bound mutations in `scripts/mutations/check-usage-pace.json` (9 `#525` entries, plus the 2 `{sec}` re-binds, "zone abbreviation dropped" and "UTC shown as local") to a temp copy of HEAD (`git archive`, never in place). I ran the full self-test under `TZ=America/Los_Angeles` and matched `[FAIL] <expected case>:` exactly. **11/11 were killed by every named case** (counts 326, 326, 339, 346, 346, 346, 342, 339, 344 (both named cases), 346, 346 of 347). All 155 manifest anchors occur exactly once in the file, and `EXPECTED_MUTATIONS` is 155. My first harness copied only `scripts/`, and every mutation "failed" because of a missing `.claude/hooks/run-hook.sh`. I discarded that run and re-ran from a full tree.
5. **Remaining copies of the old rule.** I ran `git grep` for "rises (linearly) to 99", "99% an hour", "99% at 1 h", "never above 97", "cap rises" and similar, and also for `99%`, `97%` and `LAST_DAY_CAP` over `.claude/`, `docs/memory/`, the process docs and `scripts/` (outside the module and its manifest). That excludes `docs/reviews/`. The only hits are historical: backlog rows 500 and 510, the 11-04 dashboard entry, `docs/goal-threads.md:129` (a dated thread log), and the module's own docstring, constant comment, `cap_at` docstring and #510 cases. Those describe the CAP, which does still rise to 99, so they are correct. The hooks, the memory file and `process-checklists.md` now point at the docstring. `check-docs.py`: OK.

## Findings

**m1 (MINOR, latent: unreachable with the shipped constants). The 99% branch names a 99% that the reserve keeps the stop below.** The selector tests only the ordering `now < rise_end < night_at`. It does not test whether `refuse_at` reaches 99 at `rise_end`. When `rise_end` falls on the calendar day BEFORE the reset's, that day's reserve is `100 − 5 × (reset time of day ÷ 24)`. That is below 99 for any reset after 04:48. Concrete input, `TZ=America/Los_Angeles`:
- set `RISE_END_S = 10 h` and `LAST_NIGHT_S = 8 h`;
- reset Sat 01-16-2027 06:00 PST, now Fri 09:00, weekly 98%;
- the message says "…97.9% now and **99% from Fri 01-15 20:00 PST**";
- `refuse_at` is 98.75 at 20:00, 21:00 and 21:59:24, then 100.0 at 22:00. The 99% never comes as a stop.

The probe found 1,041 cases of this shape in 30,000 draws over RISE > NIGHT constants, and 265 cases at RISE = NIGHT + 1 s. None appeared with ties, RISE < NIGHT, or the shipped constants. The shipped constants are safe for two reasons. First, the 99% branch is unreachable, since `rise_end > night_at`. Second, a 1 h rise end falls on the previous day only for a reset before 01:00, whose reserve is ≥ 99.79. The defect predates this diff: master named the same 99% unconditionally. But r1 brought non-shipped constants into scope with `_with_consts`. The new docstring sentence "the message names whichever of the two transitions really comes next (#525)" is then false. The commit's "agrees with last_night for any constants" is true only of `last_night`, not of `refuse_at`. There are two fixes. One is to also require `refuse_at(rise_end, resets) >= LAST_DAY_CAP`, with a `_with_consts(10 h, 8 h)` case at a 06:00 reset. The other is to narrow the docstring to the shipped constants (or to RISE ≤ NIGHT). From round 4 this is filed, not fixed.

**m2 (MINOR). The dashboard entry and backlog row 525 still describe round 0.** `docs/dashboard-entries.md` (the 2026-11-06 entry, tech line) says "338 cases (+2); 2 new mutations…; pin 146 → 148". It also says the note names the last night's start "whenever `resets − LAST_NIGHT_S` comes before `resets − RISE_END_S`". That is the pre-r1 rule, without the `now < rise_end` clause or the tie. `docs/backlog.md:506` (row 525 DONE) says "(338 cases, 2 mutations)". At HEAD the module says `# 347 cases`, the self-test passes 347, the pin is 155, and the diff adds 9 mutations and re-binds 2. No gate reads these two places. `check-test-counts.py` reads the roadmap, and `check-docs.py` is green. So the next reader is told the wrong count and the wrong rule. The fix is to update both to 347 cases, 9 new + 2 re-bound mutations, pin 146 → 155, and state the selection as `now < rise_end < night_at`.

Observed, not filed:
- `Resets {local_time(resets)}` and the `use_it` reset time are still minute-floored, so a reset at 02:37:42 reads 02:37. That is the reset itself, not a forecast stop, it predates this change, and real resets are on the hour.
- `exact` tests alignment on the EPOCH (`shown % 60`), not on local wall-clock seconds. In a zone with a non-whole-minute UTC offset it would pick the wrong form. No zone in use since 1972 has one, and a reset is always within a week of now.
- For a reset late in the day (Sat 12:00), the rising note on Friday morning ("97.2% now and 100% … from Sat 04:00") skips a plateau at the 97.5% reserve, which binds from about 08:45, when the note switches to the reserve note. The note names only the next real stop, so this is accurate.

Self-test: `python3 scripts/check-usage-pace.py --self-test` → `347/347 self-test cases passed` (also 347/347 under `TZ=America/Los_Angeles` and `TZ=UTC`)

VERDICT: CONVERGED

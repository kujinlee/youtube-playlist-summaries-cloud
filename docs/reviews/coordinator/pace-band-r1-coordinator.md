# Round 1 — `pace-band` (PR #555) — coordinator — both halves NOT CONVERGED; folding

Both halves ran at `d7efd2eb`.
- Codex: `docs/reviews/codex/pace-band-r1-codex.md` — 1 MAJOR, 1 MINOR.
- Claude: `docs/reviews/claude/pace-band-r1-claude.md` — 1 MAJOR, 5 MINOR.

Both halves found the hard stop unchanged (Codex: 7,308 comparisons over three time zones; Claude: AST-identical
functions) and no WARN→OK loosening on any path that existed before.

```yaml
round: 1
fixes_nontrivial: true
subject: pace-band
halves:
  claude: ran
  codex: ran
findings:
  - {id: U1, severity: High, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L1, severity: Low, aim: test, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L2, severity: Low, aim: test, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L5, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
```

## The two halves agree on the one MAJOR

**U1 (Codex 1 = Claude MAJOR-1): an UNKNOWN band returns OK, so the prompt hook says nothing.** The rule is that
an unknown start% never reads as fine, and the hook speaks only on WARN. The self-test pins the wrong result.
**Decision (coordinator, not the owner's; it is the stricter reading of a rule they set):** an UNKNOWN band is a
WARN (rc 1) whose message says the band is unknown and why (no meter row in this window). It only arises when the
window has no meter row, so it is rare. REFUSE and CANNOT RUN are unchanged. Cases: no meter rows in the window → WARN,
and the adjacent pass (a known start% at NORMAL → OK).

## The rest

- **C2:** the last-day rule excludes midnight itself (`<` where `<=` belongs, line 487). Use the inclusive boundary
  for the band only; the hard stop is untouched. Cases at 00:00:00 and one second before.
- **L1 (Claude MINOR-1):** the override is keyed by LOCAL dates and no case proves it. Add Tue 17:00 PST (already Wed
  in UTC) → the Tue band.
- **L2 (MINOR-2):** the trend case edges are too far from the line (21.0 / 21.2 against 21.108): tighten them so a
  +0.05 change in the constant fails.
- **L3 (MINOR-3):** the override's Thu/Fri `use all` entries are dead because `rise_start` covers them. Remove them,
  or make a case that only the override satisfies; say which and why.
- **L4 (MINOR-4):** stale 1.5× comment at line 1557.
- **L5 (MINOR-5):** start% has no age bound: a row days old gives a spurious early NO NEW STARTS. A start row older
  than the day it stands for makes the band UNKNOWN (and so a WARN, per U1).

Round 2 runs ONE half (alternation).

## Fold

Folded on top of `da5923e4`. The hard stop is unchanged: `refuse_at`, `cap_at`, `rise_start`, `days_after_today`,
`last_night`, `local_midnight`, `window`, `cannot`, `evaluate`, `prompt_output`, `gate_output`, `main` and every
stop constant (`RESERVE_PER_DAY`, `STOP_CAP`, `LAST_DAY_CAP`, `RISE_END_S`, `LAST_NIGHT_S`, `HARD_LIMIT`, `WARN_AT`)
are AST-identical to `origin/master`. In `_evaluate` the REFUSE condition and every `cannot(...)` path are untouched.

- **U1:** `band_note` returns the zone `BAND_UNKNOWN` (it returned None), and `_evaluate` puts it in the WARN set beside
  WIND-DOWN and NO NEW STARTS. Case `⭐ pace-band r1 U1: an unknown start% … is a WARN …` (with `prompt_output` not
  None) and its adjacent pass (the same 21% with start 10 is OK and silent). Mutation: UNKNOWN back to OK. Two older
  `main()` cases had relied on an absent meter reading as OK; they now read a meter whose band leaves 10% and 50% NORMAL.
- **C2:** one helper, `on_last_day` (`now >= rise_start`), serves the band AND the USE IT message. This goes slightly
  past "the band only", and here is why: changing only the band would make 00:00:00 a USE IT ALL zone with no USE IT room
  line, an OK verdict that the hook does not speak. One second later it would be a WARN. `rise_start`'s own docstring
  asks for one definition. The change only adds a WARN at that one instant: `cap_at` is STOP_CAP there either way. Case
  `⭐ pace-band r1 C2: AT the last day's midnight …` (Sat 02:00 reset, start 10, weekly 31; Codex's input). Mutation:
  back to `>`.
- **L1:** case `⭐ pace-band r1 L1: the override is keyed by LOCAL dates …` covers Tue 17:00 PST, and a reset at Thu
  17:00 PST, which is Fri in UTC. Mutations: Claude's surviving UTC key for today, and its twin for the window's key.
  Both go red.
- **L2:** the trend case's edges are now 21.10 and 21.11, against 21.108. Mutations: the line moved ±0.05. Both go red.
  Claude's +0.05 had survived.
- **L3:** removed. The Thu/Fri `USE_ALL` entries, the `USE_ALL` constant and the `over == USE_ALL` branch are gone.
  The owner's "Thu until the reset: use all" is exactly the last-day rule, which is inclusive from Thu 00:00 after C2.
  A case only the override could satisfy would need a USE_ALL day before the last day, which the owner never asked for.
  The case now asserts that Thu is USE IT ALL through the last-day source, and that the override has exactly Mon–Wed.
- **L4:** the stale 1.5× arithmetic is dropped from the F3 comment.
- **L5:** `day_start` treats a midnight row from before YESTERDAY's local midnight as too old. It returns
  (None, "… is from <time>, before yesterday …"), so the band is UNKNOWN, which is now a WARN under U1. It never falls
  through to a later row, because that base is higher and would loosen the band. Cases: `⭐ pace-band r1 L5 …` (one
  second before yesterday's midnight is UNKNOWN; at it, and an hour before today's, still count) and its `evaluate()`
  WARN. Mutations: no bound, and a bound two midnights back.

Mutation manifest: 188 → 196. 7 anchors were re-bound and 2 expects renamed, both by this fold's own edits. 8 entries
are new. `expected_mutations.py` records the reason.
- **Not a finding, but a PR gate:** `check-fixture-variation.py` failed on the branch before this fold. `band_cap`'s and
  `band_zone`'s parameters had one value each. A case now gives each of them a second value. The docstring's declared
  count is 409.

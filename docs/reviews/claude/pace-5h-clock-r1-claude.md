Reviewed head: ed5870260f41fa604559dae89cffb486dd90eedb

# Review — backlog #645 (usage pace: the 5-hour meter paced against its fixed block clock), round 1, Claude half

- **Subject:** `scripts/check-usage-pace.py`, `scripts/mutations/check-usage-pace.json`, `scripts/mutations/expected_mutations.py`,
  `docs/backlog.md`, `docs/goal-threads.md` — `git diff origin/master...HEAD`
- **Branch / commit reviewed:** `pace-5h-clock` @ `ed587026`
- **Mandate:** refute. Wrong zone at a boundary, epoch/zone errors in the block start or the wake time, a reset passed or
  beyond 5 h, a missing/null 5h field read as fine, the de-duplication hiding a zone change or repeating an unchanged one,
  the 5h zone downgrading a weekly REFUSE, cases that cannot fail, mutations that do not bind.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/check-usage-pace.py --self-test` (worktree) | 428/428 passed |
| CLI probes, `--cache` with a hand-built cache, `--now 1794681566`, 5h reset at now + 2.5 h (elapsed 50%), used 70 / 71 / 72 | each prints a DIFFERENT `AT MOST 2 AGENTS` text (`used 70%` / `used 71%` / `used 72%`) — see M1 |
| CLI probe, cache with no `five_hour` key, and with `"five_hour": null` | no 5h text at all — see m1 |
| The live cache `~/.claude/.rate-limits.json` | `used_percentage` is an INTEGER (`3`), `resets_at` minute-aligned |
| Manifest read: the 11 new `#645` mutations against the code and the cases they name | each edit's anchor is present once and its `expect` case reads the value the edit changes (traced by hand, below) |
| The 12 new/re-bound mutations, applied by hand to a scratch copy | 12/12 KILLED — see *Mutation run* |

Probes that did NOT refute (stated so the next round need not redo them):

- **Boundaries.** `ahead` 15 → FREE, 15.1 → AT MOST 2, 30 → AT MOST 2, 30.1 → NO NEW AGENTS, used 90 behind the clock → NO NEW
  AGENTS, used 89.9 behind → FREE, 100 → STOP. Order in `block_zone` (`:582`): STOP first, then the 90%/30 rule, then 15. Matches
  the owner's rule; each edge has a case and an inclusive/exclusive mutation.
- **Block start / epoch.** `elapsed = (now − (resets − 5 h)) / 5 h`, all epoch seconds; the printed times go through `local_time`
  with `%Z`. A reset up to the horizon slack beyond 5 h clamps elapsed to 0 (case + mutation). A reset at or before `now` adds
  nothing (`:667`, guarded by the existing `five[1] >= now` mutation and its case at five=99).
- **Wake time.** `local_time(resets + 60)` floors to the minute, so a reset with seconds prints a wake under reset + 60 s but never
  at or before the reset itself (the printed minute is the reset's minute + 1, which is after the reset). Harmless; the live
  `resets_at` is minute-aligned.
- **Weekly REFUSE.** The 5h note is only appended; `REFUSE` is decided by `weekly >= stop` before any 5h text matters (case
  `STOP rides on a weekly REFUSE`). A STALE cache returns CANNOT RUN before the five-hour window is read (case).
- **De-duplication hiding a zone CHANGE.** The zone name is in the text, so a zone change always changes the hash and speaks.
  A new block changes `Block resets …`, so it speaks.

## Findings

### M1 — MAJOR: an unchanged 5h zone is NOT said once per session — the text carries `used%`, which moves every few minutes

`scripts/check-usage-pace.py:596-612` (`block_note`). The owner's rule (backlog #645 row, and the docstring at `:47-52`, `:597-598`)
is that an unchanged zone is said once per session, and the docstring argues it holds because the sentence "names no elapsed% or
ahead, which move every few minutes, so an unchanged zone keeps its text". But the AT MOST 2 AGENTS and NO NEW AGENTS sentences
name `used {pct(used)}`, and the 5h meter is the FAST meter: at a full burn it climbs about 20 points an hour, one integer point
every ~3 minutes. #628 dedups by the hash of the whole text (`:1106-1111`), so every 1-point move re-announces the same zone.

**Concrete input** (5h reset at now + 2.5 h, so elapsed 50%; weekly 10%): used 70, 71, 72 on three prompts in one session — all
three in AT MOST 2 AGENTS — print three different texts (`used 70%` / `used 71%` / `used 72%`), so all three are SAID. Likewise
NO NEW AGENTS from 90 to 99 is said ten times. The `elapsed`/`ahead` figures the docstring calls the problem move at the same
rate as `used` does.

The self-test enshrines the defect: `:2628` *"5h block: a moved 5h reading speaks again"* asserts `True` for 80 → 81 inside one
AT MOST 2 AGENTS zone. The mutation *"the block note carries the moving ahead figure, so #628 never dedupes it"* is killed only by
the fixed-string case (any text change kills it), not by a dedup case, so it does not witness the property it is named for.

**Fix:** drop `used {pct(used)}` from the AT MOST 2 AGENTS and NO NEW AGENTS sentences (keep the reason as words — "at or over
90%" / "more than 30 points ahead"; STOP's `100%` is constant and may stay), correct the docstring, and invert `:2628`: a moved
reading INSIDE one zone is silent, a moved reading that crosses a zone edge speaks. Re-point the "moving ahead figure" mutation's
`expect` at that dedup case.

### M2 — MAJOR (structural; may be FILED rather than folded): the 5h zone is a SPAWN rule delivered only on a user prompt

`scripts/check-usage-pace.py:1033-1039` (`gate_output`): the spawn and wake gates return `None` for any verdict but REFUSE, so a
WARN — every 5h zone — is said only by the UserPromptSubmit hook. The zones are instructions about spawning ("keep at most 2
agents running", "start no new agent", "STOP … start and wake no agent"), and they change within minutes, but the model hears them
only when the owner types something, and then once per session (M1 aside).

**Concrete input:** the owner's last prompt lands at 5h 20% (FREE, nothing said) and they go AFK; the coordinator runs an
autonomous slice for two hours, spawning a fresh agent per task as the 5h meter climbs to 100%. No prompt is submitted, so neither
AT MOST 2 AGENTS, NO NEW AGENTS nor STOP-with-wake-time is ever shown — the run hits the hard 5h limit with no warning, which is
the failure the row exists to prevent. The old 90% WARN had the same channel, but it was one line; this branch adds three spawn
directives to it. (Memory: *a gate's CHANNEL can be weaker than the gate*.)

**Fix:** at `--hook spawn` (and `wake`), when the 5h zone is not FREE, allow but return a `systemMessage` / `additionalContext`
carrying `block_note` (no deny — the owner's rule keeps it a WARN); add a case that the spawn hook at 5h 100% returns the WAKE
text and no `deny`. If the owner scoped the rule to the prompt hook, file it as a row instead and state the bound in the docstring.

### m1 — MINOR (pre-existing, newly load-bearing): an ABSENT or `null` `five_hour` window is silently FREE

`scripts/check-usage-pace.py:351-352` returns `None` for a missing or `null` key, and `:667` then adds nothing. Under the new
rule the 5h zone is UNKNOWN, which the day band (pace-band r1 U1) and the unreadable-window branch (`:666`) both say as NOT RUN.
**Input:** `{"at": now, "rate_limits": {"seven_day": {...10%...}}}` or `"five_hour": null` — no 5h text. **Fix:** either say
`5h block: UNKNOWN … NOT RUN` when the weekly window is present and the five-hour one is not, or state the bound ("an account
whose statusline reports no five-hour window is never paced") in the docstring at `:47`.

### m2 — MINOR: `block_zone`'s upper clamp at 100% is unreachable

`:585` `min(..., 100.0)` — the only caller (`:667`) passes `resets > now`, so elapsed < 100 always. Not wrong, but the docstring
"clamped to 0–100" describes a branch no input reaches and no mutation pins. **Fix:** drop the `min`, or keep it and say it is
defensive.

## Mutation run

The full `--mutate . --only scripts/check-usage-pace.py` run paces at ~40 s a mutant (213 → over 2 h), so it was stopped at 4/213
and NOT used. Instead the 12 manifest entries this branch adds or re-binds were applied one at a time to a copy of `scripts/` +
`.claude/hooks/` in the scratchpad (control: the unmutated copy passes 428/428), each anchor checked to occur exactly once, and
`--self-test` run. **All 12 KILLED, each by every case in its `expect`** (the 90% line re-bind 1 fail; FREE edge 2; 30 edge 1; FREE
margin 2; 2-agent margin 1; 90% rule dropped 1; STOP > 100 2; wake at reset 2; elapsed from reset 7; no clamp at 0 1; no note 13;
moving ahead figure 1). Not run here: the other 201 entries (unchanged by this branch except where their anchors moved) — CI's
selected sweep answers those. The "moving ahead figure" kill is by a fixed-string case, not by a dedup case: see M1.

VERDICT: NOT CONVERGED

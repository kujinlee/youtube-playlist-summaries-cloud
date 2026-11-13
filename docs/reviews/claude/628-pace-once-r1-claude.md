# Review — backlog #628 (usage pace: an unchanged WARN said once per session), round 1, Claude half

- **Subject:** `scripts/check-usage-pace.py`, `scripts/mutations/check-usage-pace.json` — `git diff 61a91482..ff8706eb`
- **Branch / commit reviewed:** `628-pace-once` @ `ff8706eb` (PR #574)
- **Mandate:** refute. Find an input where a notice that must be shown is silenced, or a test/mutation that cannot fail.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/check-usage-pace.py --self-test` (worktree) | 413/413 passed |
| The 3 new `#628` mutations + the edited `sid is None → return True` mutation, each applied by hand to a temp copy of `scripts/`, `--self-test` run | each reddens its `expect` case (outputs below). The temp copy crashes LATER at line 2549 (no `.claude/hooks/run-hook.sh` outside the repo); the unmutated control copy shows **0** `[FAIL]` lines before that crash, so every red is the mutant's |
| Extra, unlisted mutant: `elif verdict in (WARN, CANNOT_RUN) and out:` | red on the STALE and MALFORMED every-prompt cases — the CANNOT RUN boundary is pinned by existing cases |
| Live hook runs in a throwaway `git init` repo with real payloads (sequences below) | see findings |

Mutant reds observed:

```
mut "never deduplicated"      [FAIL] ⭐ #628: an unchanged WARN is said once per session, then silent: got [True, True, True]
mut "key ignores the session" [FAIL] #628: a changed reading speaks again; a new session is told again: got (True, False)
mut "REFUSE deduplicated"     [FAIL] #628: REFUSE-SPAWN is never deduplicated: got [True, False]
mut "sid None → True"         [FAIL] #628: a WARN with no session_id is LOUD every time: got [False, False] (+4 older cases)
```

Probes that did NOT refute (stated so the next round need not redo them):

- **Shared one-line state, absent-cache vs WARN:** the keys are `<sid>` and `<sid> warn:<hash>`; they never compare equal, and an
  interleaving only makes the next one speak again (loud direction).
- **Two sessions alternating** (A, B, A, B on one main checkout, unchanged WARN): SAID ×4. Loud, so not a silencing — but see m3.
- **Garbage / oversized / directory state file:** `text.strip() != sid` → returns False → loud. A directory makes `os.replace` raise
  `OSError`, caught, loud (leaves a `.tmp` behind — not in scope).
- **REFUSE prompt output with the override-active note:** never enters the `elif` (verdict REFUSE); the override is looked up only
  at REFUSE, so no WARN text depends on it.
- **Payload consumed earlier in `main`:** `read_payload()` sits in two mutually exclusive branches (`if … absent` / `elif WARN`),
  so stdin is read at most once.

## Findings

### M1 — MAJOR: a WARN that carries a "treat it as NOT RUN" signal is deduplicated

`scripts/check-usage-pace.py:1057` dedups every WARN by its whole text. Two WARN-verdict texts are NOT-RUN signals by their own
words: the day band unknown (`:553`, "today's band is UNKNOWN — start% cannot be read (…): treat it as NOT RUN, never as fine")
and an unreadable five-hour window (`:613`, "treat it as NOT RUN"). Both become WARN at `:660` even with weekly usage far below
80%. The PR's own statement (`:73`, `:1055-1056`) is that CANNOT RUN is never deduplicated, and the user's standing rule is that
"cannot run" must fail loudly; the band/five-hour NOT RUN is the same signal under a WARN verdict.

**Concrete input** (throwaway repo, payload `{"session_id":"S1"}`, `--meter` pointing at a missing file):

```
cache {"seven_day": 50%, "five_hour": {"used_percentage": "garbage"}}  prompt 1 → SAID ("…band is UNKNOWN… treat it as NOT RUN…")
                                                                     prompt 2 → silent
cache {"seven_day": 50%} (meter missing)                              prompt 1 → SAID ; prompt 2 → silent
```

Bound on the harm: the text includes `pct(weekly)` at 0.1%, so it speaks again once usage moves 0.1%. The silence lasts exactly
while usage is flat — but that is also when the meter being dead is least visible. **Fix:** exclude from the dedup any WARN whose
zone is `BAND_UNKNOWN` or whose `five_note` is the unreadable one (e.g. dedup only when `"NOT RUN" not in message`, or return the
zone/flag from `evaluate`), and add a case: band-unknown WARN, two prompts, `[True, True]`. No case pins this either way today.
If the owner decides once-per-session is acceptable for these (as for the absent cache), the comment at `:73`/`:1055` must say so.

### m1 — MINOR: a WARN said, then STALE, then the same WARN — the recovery is silent

CANNOT RUN does not write the state, so the WARN's line survives it. Sequence (live hook, one session):

```
w (85%, fresh) → SAID ; stale (same cache, at −2h) → SAID ; w (85%, fresh again) → silent
```

The model's most recent pace context is then "weekly usage is UNKNOWN" until the text next changes. Fix (cheap): have the stale /
malformed path clear or overwrite the state line (e.g. `told_this_session(payload, root, "cannot")` called for its write), or note
the bound. `scripts/check-usage-pace.py:1046-1060`.

### m2 — MINOR: after `/compact` the same session is never re-told

`session_id` persists across a compaction (the repo's own snapshot path `.remember/compaction/<session_id>/` relies on that), and
nothing resets `.claude/usage-pace-notice` at SessionStart(compact). A WARN given before compaction lives only in the compacted
transcript; the model is not re-told until the text changes (next 0.1% of usage, or the trend/`days` figures moving). Includes a
`NO NEW STARTS` / `WIND DOWN` zone and the last-day "USE IT" directive. Bounded the same way as M1; the docstring (`:850-854`)
states the absent-cache BOUND but not this one. Either state it or clear the state line from the compact SessionStart hook.

### m3 — MINOR: the comments say "whole percent"; the text moves at 0.1%

`:73` and `:1055` say any change in "whole percent" speaks again. `pct()` (`:291`) floors to **0.1**, and the text also carries
`pct(trend)` (moves ~0.1% every ~10 min when above trend) and `days:.1f`. So the dedup holds only while usage and the clock-derived
figures are flat; the claimed ~160-token saving per prompt is not measured and is likely much smaller during active work, and two
sessions sharing a main checkout (A, B, A, B → SAID ×4) defeat it entirely. Not a silencing — correct the wording to "0.1%" and,
if the saving matters, state the bound.

VERDICT: NOT CONVERGED

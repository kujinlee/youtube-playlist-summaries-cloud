Reviewed head: 09dbd3a2e7eb58ae55783e96015e97f667bb3456

# meter-log-tail r4, Claude half (backlog #501, PR #531). Codex skips this round by alternation.

REVIEW GAP: codex — alternation (round 4 runs the Claude half)

Scope: the r3 fold `740b5083` (the Phase 6 redesign: writer contract W1/W2, canary, time witness) and the master merge
`09dbd3a2`. Mandate: REFUTE, under the round cap (`docs/review-method.md` §0 Q4c): from round 4 a finding is FILED
unless it is a BLOCKER. The admissibility test is the r3 coordinator's *Stop condition* (from the architecture
review's §9). Every experiment ran in a scratch copy of `scripts/check-usage-pace.py` extracted with `git archive`
from the head; nothing in the worktree was modified, and the real `~/.claude/meter/log.jsonl` was only read.

## Gates run on the head

| Check | Result |
|---|---|
| `python3 scripts/check-usage-pace.py --self-test` | **392/392 passed** (20 s wall, the whole suite) |
| `python3 scripts/check-fixture-variation.py` | **OK**, rc 0 (1924 parameters, 94 files). Two `⭐` notes about `codex-review.py` `intrusions.*` came in with master and do not concern this PR |
| `scripts/mutations/check-usage-pace.json` entries vs the pin in `expected_mutations.py` | **174 = 174** |
| Duplicate row numbers in `docs/backlog.md` after the merge | **none** (master added 546–552, this branch 553–555) |
| `decision-log.jsonl` parses line by line | **209 rows, all valid JSON**; the branch adds exactly its 2 meter-log-tail rows (`accrete`, `redesign`) |
| Mutation sweep | **not run**, as the brief said |

## Focus 1: an in-contract log where the cut answer differs from the whole log's, without a refusal

**None found.** I attacked the proof in three ways.

**(a) The proof, read against the code** (`scripts/check-usage-pace.py:313-381`). Let `u` be an unseen row. It
precedes every seen row in the file. By W1, applied to `u` and the seen row that attains `min_at`, `at_u ≤ min_at + S`.
- **With `before`:** the witness gives `min_at < at_B − S`, so `at_u < at_B` strictly. `u` cannot become a newer or
  tied row at or before midnight, so whole-`before` = cut-`before`.
- **Without `before`:** `at_u < R − 7 d − 1 h`, so by W2 `u` is not a row of this window. It can be neither the whole
  log's `before` nor its `after`.

Four details checked:
- `min_at` is taken over a SUBSET of the seen rows, because lines without `"seven_day"` and rows that do not parse are
  skipped before `min_at` is updated. This only makes the bound weaker, so it is still sound.
- Rows stamped after `now`, rows with an out-of-range reading, and other windows' rows all count toward `min_at` and
  the canary. That is also sound.
- `midnight` and `resets` are the same values on both paths, so DST and a reset at midnight cannot split the two
  answers. Only the witness compares times, and the proof does not use `midnight`.
- `float` arithmetic: epochs are about 1.8e9 and `S` is an integer, so `min_at < needed − S` is exact.

**(b) A boundary-seeded random search for in-contract logs.** Script:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/probe.py`.

The logs were built to keep the contract, and each was checked before use: W1 as a running maximum, and W2 for every
window, `at ≥ r − 7 d − 1 h`. Row stamps were drawn from these anchors, ±0/±1 s or a random offset up to ±S:
- midnight, midnight − S, midnight − S − 1, midnight ± 1, midnight − 2S, midnight − 3S;
- the window start `ws`, plus `ws − 1 h`, `ws − 1 h ± 1`, `ws − 1 h − S`, `ws − 1 h − S − 1`, `ws − 2S`;
- `now`, `now + 1`.

The search also covered:
- `resets` from 1 s to 7 d + 1 h after midnight, including a reset exactly AT midnight and exactly `S`/`S + 1` after it;
- `now` from 1 s to 20 h after midnight;
- other-window rows (`R − 7 d`, `R − 14 d`) and `R − 1` jitter;
- out-of-range readings (101, −1);
- five zones: America/Los_Angeles, America/Santiago (DST at midnight), Asia/Beirut (DST at midnight),
  Australia/Lord_Howe (a 30-minute DST step), and UTC.

Every cut of every log was compared with the whole log, counting a cut answer where the whole log has none as WRONG.

Two seeds, 4,000 and 3,000 logs per zone: **about 157,000 cuts, 0 WRONG.**

**(c) The real log.** `~/.claude/meter/log.jsonl` had 622 lines at 06:07. I took every third line as a cut, at 47 values
of `now` spaced 3 h apart, back from the newest row:
- 4,234 answered, all equal to the whole log;
- 5,495 refused;
- **0 WRONG.**

**Probed specifically, with no counterexample:**
- stale `resets_at` readings: the R2-F2 shapes, and a stale LAST-window row first in the part;
- a weekly reset inside the part;
- a reset at midnight;
- DST, including zones whose DST change falls at midnight;
- `needed` with no row at or before midnight, including this window's rows inside W2's slack band
  `[R − 7 d − 1 h, R − 7 d)`;
- the `HORIZON_SLACK_S` term;
- both strict boundaries, `min_at < needed − S` and `at < max_at − S`.

**Crash probe on `main`'s new message path.** I fed `pace_line(cut=True)` breaches between extreme `at` values:
±1e300, ±DBL_MAX, 1.8e18, year 0, year 10000, and a pre-1970 epoch. `safe_time` rendered every one, and **0 raised**.

## Focus 3: the master merge

The merge brought `batch-ci.py` and changes to `check-merge-ready`. It touches `expected_mutations.py` only in other
files' entries (`batch-ci.py` 95, `check-merge-ready.py` 156), and `check-usage-pace.py` stays at 174, which equals the
manifest. The backlog numbering is disjoint, the decision log parses, and the self-test is green after the merge.
**Nothing disturbed.**

## Focus 4: the sweep case

I replicated the sweep verbatim against the head in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/sweep.py`.

**It is deterministic.** It uses `random.Random(7)` and does not read the clock. Its zone is the self-test's fixed
`PST8PDT` (`check-usage-pace.py:952-954`), restored in the `finally`.

**It is bounded:**
- 60 worlds, at most 85 rows a world at seed 7, so about 2,700 cuts;
- both calls (in-contract and control) take **1.18 s** together.

**What it found at seed 7:**
- in-contract: **0 wrong** of 2,703 cuts, 2,051 of them answering, so the sweep is not vacuous;
- control: **3 wrong**.

**Robustness, for the record:**
- in-contract: 0 wrong at seeds 1–7;
- control: 3, 3, 4, **0**, 1, 1 at seeds 1–6.

So the control's margin is thin and seed-dependent. At seed 4 it finds nothing. The seed is fixed, so this is not
flakiness. An edit that perturbs the generator's draw order could still turn the control red, but that fails toward
red. **Not a finding.**

Also noted, **not a finding**: the generator never draws this-window rows inside W2's slack band, and never draws rows
stamped after `now`. So `needed`'s `HORIZON_SLACK_S` term is held by case 8b alone, which exists and is named by its
mutation.

## Focus 2: the 10 re-pinned fixtures, and the PRECEDES departure

| Fixture | Still tests its subject? | How checked |
|---|---|---|
| MID-LINE tail | **yes** | A parsed fragment `(NOW−60, 10)` followed by `OLD` breaks the contract, so it would refuse, not answer 92.5 |
| one invalid byte | **yes** | If the `\xff` row were parsed, `(NOW−60, 10)` is newer than the midnight row, giving 55 ≠ 92.5 |
| two rows with the SAME time | **weakly** | It still exercises the witness with `before`. Only a canary that drops the skew AND uses `<=` would redden it; case 9 holds the canary's boundaries |
| through LAST week's row (51.5) | **no**: see R4-F1 | Measured: deleting last week's row still gives 51.5 |
| R1-F3, 3 rows → `TAIL_TOO_SHORT` | yes, as a pin of "too short"; the at-scale form is case 11 | — |
| disorder among an EARLIER window's rows (3,601 s) | **yes** | Without the canary the answer is `TAIL_TOO_SHORT`, not `TAIL_CONTRACT_BROKEN`, so the reason separates them |
| R2-F2's three variants → `TAIL_TOO_SHORT` | **no**: see R4-F1 | Measured: the same part with the stale/jitter row deleted gives the same `TAIL_TOO_SHORT` |
| PRECEDES → `TAIL_CONTRACT_BROKEN` | **yes, but of a different subject** | The 14-day-early row breaks W1 inside the part, so the canary refuses first; deleting it gives `TAIL_TOO_SHORT`. The departure from §6 is **correct by the code** (`check-usage-pace.py:367-369` runs before the witness at `:370`). Its title describes the deleted `earlier_window` mechanism (R4-F1) |

### R4-F1 — Low — three re-pinned fixtures keep titles that describe the deleted order proof, and two no longer depend on the rows their titles name

**BLOCKER: no.** It gives no false green on any input. It falls under admissible class 3 (*a case that cannot fail*),
so under the round cap it is **FILED**.

**Where:**

- **`scripts/check-usage-pace.py:1455-1467` (check at `:1461`), *"⭐ #501 r2 F2: a cut part whose `resets_at` DECREASES in file order is
  refused, never the wrong 94 — …"*.**
  - Each of the three parts holds only rows after midnight, so `TAIL_TOO_SHORT` follows from the witness alone. The
    stale (LAST_WR) row and the `R − 1` jitter row are inert.
  - **Repro**, scratch copy, `TZ=PST8PDT`, `now = NOW + 10 h`, `cut=True`:
    - `[(NOW+60, 88, WR), (NOW+120, 30, LAST_WR), (NOW+180, 89, WR)]` → `TAIL_TOO_SHORT`;
    - `[(NOW+60, 88, WR), (NOW+180, 89, WR)]` → `TAIL_TOO_SHORT`.
  - The title is now **false** of the code: a decreasing `resets_at` in a long-enough part is NOT refused. Case 6
    (`:1510-1513`) pins exactly that, answering 92.5.
- **`:1467-1474` (check at `:1470`), *"an earlier window's row proves the cut only when it PRECEDES this window's first row … stamped
  outside the horizon"*.**
  - It still goes red without its row: deleting the row gives `TAIL_TOO_SHORT`, which is not `TAIL_CONTRACT_BROKEN`.
    But it is now a canary case, a 14-day breach, which duplicates case 9.
  - Its title names `earlier_window` and "the horizon", both deleted by the fold.
- **`:1309-1318` (check at `:1317`), *"a cut part that reaches back past midnight through LAST week's row still yields the line"*.**
  - `OLD` does the reaching now. **Repro:** `[OLD, (NOW+60, 3, WR)]`, with no last-week row, gives the same
    `(51.5, "")`.
  - The comment above it says so ("last week's row alone is not a proof any more"), but the title still credits that
    row.

**Scenario:** a later reader, or a mutation author choosing a killer case, trusts these titles as statements of
behaviour. The R2-F2 title asserts the opposite of case 6. No mutation in `scripts/mutations/check-usage-pace.json`
names any of the three (grep: 0 hits), so nothing is mis-attributed today.

**Fix (filed, not folded):**
1. Retitle the three cases to their present subject:
   - R2-F2: "a part holding only rows after midnight is too short, whatever its stale rows";
   - PRECEDES: "a row 14 days early inside the part breaks the contract";
   - 51.5: "a window that began after midnight answers from its first row, at scale".
2. Either delete the R2-F2 trio as a duplicate of *"a cut part holding ONLY rows after midnight is refused"*
   (`:1320-1321`), or give it an `OLD` front row and expect 92.5. In that form it is case 6's subject, so deletion is
   the smaller change.

## Summary

| Focus | Result |
|---|---|
| 1. In-contract cut ≠ whole, with no refusal | **none**: the proof checks out against the code; 0 WRONG in about 157k boundary-seeded cuts across 5 zones and in the real log (4,234 answered cuts) |
| STOP weakened or removed | **no**: `pace_line` only feeds the guide line (`:494`); the stop path is untouched by the fold |
| crash in `main` | **none** found: the new message path renders extreme epochs |
| 2. Re-pinned fixtures | R4-F1 (Low, filed): 2 fixtures inert on their named rows, 3 stale titles; PRECEDES departure correct |
| 3. Master merge | clean: pins, backlog numbering, decision log |
| 4. Sweep | deterministic (seed 7, fixed TZ), 1.18 s; the control's margin is seed-thin (3 wrong), noted only |

**BLOCKERs: none.** The one finding is Low and is FILED under the round cap; it needs no fold and no round 5. The
verdict below is CONVERGED in that sense: the round found no behavioural defect and nothing that must be folded.

VERDICT: CONVERGED

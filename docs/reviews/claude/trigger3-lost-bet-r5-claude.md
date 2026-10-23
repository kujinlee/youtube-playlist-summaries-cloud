<!-- claude-review: subagent, round 5 -->

# Round 5 — `trigger3-lost-bet` — Claude half (fresh reviewer, final-tree round)

Subject: `b8c6f1ba..3b8e195c` (the r4 fold), read in the context of `753645a7..3b8e195c`.
Mandate: REFUTE. Everything below marked **executed** was run against copies under the
scratchpad (`r5copy` = `git archive HEAD` of the worktree; `r5mut` = a pruned copy of that for
mutation). No worktree file other than this one was written and no git write was run.

## What I executed, and what held

| Check | Result |
|---|---|
| `check-decision-scheme.py --self-test` (copy) | **250/250 passed** — matches the docstring's declared 250 |
| `check-decision-scheme.py` on the branch log (worktree, read-only) | rc **0**; WARN t6, t8, t10 (always-on pin HIT, backfill pin UNUSED) |
| `check-plan-code.py --mutate .` on a copy pruned to this file's manifest (`EXPECTED_MUTATIONS` cut to that one entry, `node_modules` symlinked) | **111 mutations, 111 killed, 111 attributed to the case each names, 0 survivors** (1m50s) |
| Sum of all manifests (copy) vs declared total | **1867** = the `check-plan-code` self-test pin; that self-test 215/215 |
| (a) a NEW loss on a pinned unit at the next rung (always-on, backfill two rungs on) | FAILs trigger 3 — the shipped `_succ_ao`/`_succ_bf` cases, and mutation 110/111 kill the regression |
| (a) a loss on a near-duplicate unit name (`…optional steps ` with trailing space) | FAILs trigger 3; the pin is not fuzzy-matched |
| (b) 12 first-rung bets, 4 subjects × 3 units, all `stopped` | trigger 3 quiet — no structural fire |
| (b) 6 first-rung bets in flight (`outcome` null) | quiet |
| (b) a skipped rung (`split` with `skipped: [accrete, redesign]`), stopped | quiet |
| (b) one subject, three units: one escalated-and-stopped, one lost, one stopped | trigger 3 names **only** `s/b` |
| loss, then skip-to-`defer` with a reason, `defer` continued | trigger 3 silent, trigger 2 FAILs — the intended split |
| hindsight appended after a real loss | refused by `invalid_rows` (row 2), so it cannot quiet trigger 3 |

The r4 Major is genuinely fixed in code: identity is (subject, unit, route), carried through
`lost_bets`, `t3`, `t10` and `pinned_lost_bets`, and a present `null` is CANNOT RUN at the parser
and the CLI. The tests drive both shipped histories through the successor-loses transition with
distinct units and ladder positions. I found no masked or ambient pass in the new cases.

## Findings

### F1 — MAJOR — the DEFER row is scored `stopped` although its own named failure observation was met; scored honestly, trigger 2 FAILs

`docs/reviews/decision-scheme/decision-log.jsonl:14` (and the new unit at `:15`).

- **The row's text.** Row 14 (route `defer`, unit `lost-bet trigger + missed-escalation
  acknowledgment`) *predicts the pin list itself*: "the two lost bets that predate the trigger …
  are pinned by name with a reason and WARN; any other lost bet FAILs." Its named failure
  observation: "**any Blocking/Major, or a lost bet outside the pinned list that does not FAIL.**"
- **What r4 found** (`docs/reviews/codex/trigger3-lost-bet-r4-codex.md`): a Major, and the Major
  *is* "a lost bet outside the pinned list that does not FAIL" — a later `redesign` loss on a
  pinned unit exiting 0. Both halves of the failure observation were met.
- **What the row says instead:** `"outcome": "stopped", "rounds_at_termination": 4`, with the
  Major moved to a new unit, `pre-trigger lost-bet pin list` (row 15, route `accrete` — the ladder
  restarts at the cheapest rung).
- **Input, executed:** the branch log with row 14's `outcome` set to `continued` (the value its own
  text calls for). `invalid_rows` → `[]`; **`t2` → "1 unit(s) exhausted every route and still carry
  findings (trigger3-lost-bet/lost-bet trigger + missed-escalation acknowledgment) — the claim that
  escalation terminates is refuted, not delayed"**. As shipped, `t2` → `None`.
- **Why it matters.** Trigger 2 is the scheme's primary falsifier, and the first unit ever to reach
  DEFER is the one this branch's author scored. The note in `observed` ("Stated so the split is
  visible rather than a quiet way out of the ladder") makes it visible, but visibility is not the
  ladder's test — the row's own failure observation is. The supporting chain makes the re-scoping
  harder to defend: the pin list was introduced by the r3 fold (`80e9de50`), r4 reviewed exactly
  that fold, so r4's Major is the **third consecutive fold-induced round** (r2←r1 fold, r3←r2 fold,
  r4←r3 fold). The r4 coordinator doc answers "thrashing or prose floor?" with "a different
  component" — which is true only because the component was renamed at the fold that introduced it.
  Relabelling the unit at each fold is a general way to keep any unit off rung 4.
- **Fix (one of, and it is a decision, not mechanical):**
  (a) score row 14 `continued` and let trigger 2 FAIL — that is DEFER's meaning ("stop, file it"):
  the pin list goes to the human/backlog rather than a fifth round; or
  (b) if the coordinator holds the pin list really is a separate unit, row 14's prediction and
  failure observation must not have claimed it — and since the row is append-only and already
  states it, (b) is not available honestly.
  ⚠ Note the incentive this exposes, independent of this branch: a `defer` scored `continued` is a
  permanent red (append-only log, no rung left), so the mechanism *rewards* scoring a defer
  `stopped`. Worth a backlog row; not this branch's fix.

### F2 — LOW — "THERE IS NO ESCAPE IN THE LOG" is overstated: an authored `retroactive: true` silences trigger 3 with no WARN when the subject has any prospective row

`scripts/check-decision-scheme.py:384` (also `:68` "There is no way to exempt a bet from inside the log").

- **Input, executed:** subject `new` with a prospective `stopped` row on unit `u0` and a
  `retroactive: true`, `continued` `accrete` row on unit `u` (no later bet). `invalid_rows` accepts
  it; `t3` → `None`; `t8` → `None` (t8 warns only when *every* row of the subject is retroactive —
  confirmed: with the `u0` row removed, t8 does warn).
- This is the pre-existing authored-honesty limit the module docstring already states for
  `retroactive`, so not a defect of this fold. But the two sentences above claim more than the
  code does, and they were written for this trigger.
- **Fix:** qualify: "no exemption other than the pin list — except that a row authored
  `retroactive: true` is outside every scoring trigger, which nothing verifies (see the
  `retroactive` caveat)."

### F3 — LOW — stale identity in `t10`'s docstring

`scripts/check-decision-scheme.py:417`: "an UNUSED pin — no unescalated lost bet on that
**(subject, unit)** in this log". After r4 the key is (subject, unit, route). The message text and
code are right; the docstring is the pre-fold identity. **Fix:** "(subject, unit, route)". (Read,
not executed — it is prose.)

### F4 — LOW / informational — the UNUSED backfill pin excuses any row with its key, not *the* row

`docs/reviews/decision-scheme/baseline.json` (the `work-lines-backfill` pin).

- **Input, executed:** the branch log + a freshly written prospective `accrete` `continued` row on
  (`work-lines-backfill`, `transcript replay (…)`). `t3` → `None`; `t10` reports it as a
  pre-trigger HIT. On master that key has no row, so any row with that key — including one written
  after trigger 3 shipped — is excused.
- Practically bounded: the only plausible writer is the merge of `feat/work-lines-backfill`, whose
  row *is* the historical bet. Codex r4 suggested an immutable row fingerprint; the
  (subject, unit, route) key is sufficient for the r4 defect but not for this one. Acceptable if
  stated; the baseline note already says the pin is unused until that branch merges.
- **Fix (optional):** add the bet's `prediction` prefix or written-timestamp to the pin, or state
  the residual in `_lost_bets_before_trigger3_means`.

## Read as a set (mandate c)

- Docstring trigger table vs behaviour: matches every input above.
- `baseline.json` note vs code: matches (route required, null refused, closed list, case-pinned).
- Plan-doc note and `docs/review-method.md`: accurate; the review-method edit correctly stops
  hard-coding a trigger count.
- Decision-log rows: rows 11–13 are honest. **Row 14 is not** — F1. Row 15 is in flight
  (`outcome` absent) and, if this round is scored, its own failure observation ("any log where a
  lost bet that is not one of the two pinned historical bets avoids trigger 3") is met by F2's
  input only if one counts an authored `retroactive` row as "a lost bet"; I do not, because the
  mechanism defines lost bets as prospective. On code, row 15's bet holds.

## Verdict

The code change is correct, fully mutated (111/111), and the r4 defects are closed. What blocks is
not code: the decision log — the instrument this branch exists to make trustworthy — records the
first DEFER as `stopped` against its own written failure observation, and that score is the only
thing keeping trigger 2 quiet. A final-tree round cannot converge over a log row the mechanism
would refute if it were filled in as written.

VERDICT: NOT CONVERGED

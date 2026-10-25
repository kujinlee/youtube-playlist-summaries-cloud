<!-- claude-review -->
# t4-warn-pending-327 — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` on `t4-warn-pending-327` (HEAD `c7432fb1`), 5 files:
`scripts/check-decision-scheme.py`, `scripts/check-plan-code.py`,
`scripts/mutations/check-decision-scheme.json`, `docs/backlog.md`, `docs/dashboard-entries.md`.
Mandate: refute.

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/check-decision-scheme.py --self-test` (worktree) | 274/274 passed |
| `python3 scripts/check-decision-scheme.py` (worktree, master's log) | rc=0; WARNs 6, 8, 10, 11; no trigger-4 line |
| `termination_window` over the worktree log, `size=4` | `[(4,'accrete'),(7,'defer'),(4,'split'),(5,'split')]`. Four subjects, so the 5-window is `[]`. Claim confirmed |
| PR #397 head `65e9263a`, its own script, its own log | rc=1, `FAIL trigger 4 NO IMPROVEMENT: median ... is 4, against a pinned pre-scheme median of 4 ... 1 of those 5 terminations were DEFERRALS` |
| THIS branch's `main()` over PR #397's log + baseline (the baselines are byte-identical) | rc=0, `WARN trigger 4 ... — SUSPENDED TO A WARN by the owner 2026-10-25, pending backlog #327 ...; NOT a pass`; window `[(4,accrete),(7,defer),(4,split),(5,split),(4,split)]`. Claim confirmed |
| `python3 scripts/check-plan-code.py --self-test` | 215/215 passed (includes the sum-is-2020 case) |
| manifest length `scripts/mutations/check-decision-scheme.json` | 128, matches the pin |
| The 3 new mutation entries replayed by hand on a copy (`scratchpad/t4mut/`) | each killed by exactly the two cases it names (272/274) |
| My own mutations on the copy | see M2. Three survive 274/274 |

**Question 1, other readers of trigger 4's severity.** I grepped `scripts/`, `.github/`, `.claude/hooks`
and `docs/`. The only thing that consumes the verdict is `.github/workflows/ci.yml:339`, which runs the
CLI, and it reads only the exit code. `check-goal-status.py:58` mentions the script in a docstring.
`check-fixture-variation.py:710-711` lists `t4_no_improvement`'s parameters, and that does not depend
on severity. `t9_deferral_composed` reads `termination_window`, not t4's list placement, so its
"t4 owns this window" rule still holds when t4 is a WARN (see L1 for its wording). No
spec or ADR states "trigger 4 FAILs". The only document is the deferred plan
`docs/superpowers/plans/2026-10-20-decision-log-model-redesign.md`, which is history. **No functional
dependency was broken.**

## Findings

### M1 (Medium): nothing enforces the end of the suspension, and the change does not say so

`scripts/check-decision-scheme.py:1466-1472` ("⚠ RESTORE IT TO THE FAIL LIST ABOVE when #327
rules") and the backlog row ("**RESTORED TO THE FAIL LIST when this row rules**") are the whole
mechanism. Both are prose. No check compares `T4_SUSPENDED` with row #327's state. If #327 is
closed with `✅`, or ruled "keep", and the code is not touched, every run stays green with a WARN.
That WARN goes on saying "pending backlog #327" after the row has stopped pending. The row now
asserts it will happen, and that assertion is the trigger for the repo rule *a declaration is not the
act*.

The mutation suite makes this worse. Mutation 1 ("put BACK on the FAIL list") and the two CLI cases
**pin the suspension as the correct state**. So the restore is a red that someone has to deliberately
edit through, and nothing reddens when the condition for restoring arrives. The suite guards the
temporary state and leaves its expiry unguarded.

The phrase "restored when this row rules" also contradicts the row's own options. A *retire* or
*simplify* ruling may remove t4 rather than restore it.

**Fix, either of:**
- (a) a self-test case or small check that reads row #327's status with the existing backlog parser
  (`check-docs.CELL_SPLIT`) and fails while `T4_SUSPENDED` is still referenced from `main()` once the
  row is `✅`;
- (b) state in the code comment and in the row, in so many words, that the expiry is convention-only
  and nothing will fire. Then reword the row to "restore, remove or replace t4 as #327 rules".

### M2 (Medium): the new CLI cases do not pin the content they exist for, and 3 mutants survive

Cases at `scripts/check-decision-scheme.py:2986-2998` assert four things against the WHOLE stdout:
`"WARN  trigger 4 NO IMPROVEMENT" in _o`, `"backlog #327" in _o` and `"FAIL" not in _o`, plus the
exit code. None of the assertions is tied to trigger 4's own line, and none mentions the clause
that the constant's comment (`:157`) gives as its purpose: "so no run reads as a pass".

These mutants of a copy each pass **274/274**:

| Mutant | Effect on the reader |
|---|---|
| drop `; NOT a pass` from `T4_SUSPENDED` | the one phrase that stops the WARN reading as a pass is gone |
| `("4 NO IMPROVEMENT", t4 and (T4_SUSPENDED))` | the CLI line loses the measured verdict: median 4, pinned 4, the deferral count. Only the suspension notice is left. The unit cases on `t4_no_improvement` stay green, so this is the call-site gap *unit coverage does not compose* |
| emit `" backlog #327"` on a separate WARN line | the `#327` assertion is satisfied from a line other than t4's. Combined with dropping `#327` from the suffix, it would survive |

**Fix:** pick out trigger 4's line, e.g. `next(l for l in _o.splitlines() if "trigger 4" in l)`. Then
assert on that line: `"backlog #327"`, `"NOT a pass"`, and the measured text (`f"is {_n},"` and
`"pinned pre-scheme median of 4"`). Add a mutation for the dropped clause.

### L1 (Low): t9's docstring describes t4 as "failing"

`scripts/check-decision-scheme.py:626-628`: "If t4 is already failing the reader is being told the
stronger thing". While the suspension holds, t4 never fails. The logic is unaffected because t9 keys
on the median, not on severity. But the sentence now describes a state that cannot occur. The
`:584` docstring was updated and this one was not.

### L2 (Low): the reopening is invisible where a reader scans

`docs/backlog.md:311`, row #327:
- the title still opens `⏸️ **DEFERRED 2026-10-20 BY THE OWNER`;
- the status cell still opens `deferred 2026-10-20 by the owner`;
- the reopening and the *keep / simplify / retire* question sit at the tail of a cell of roughly
  1,500 characters.

`docs/roadmap-to-launch.md:2445` is still ticked `[x] ⏸️ **DECIDED 2026-10-20 — DEFER** (backlog
**#327**)`. Nothing records the reopening or the open owner decision. `dev-process.md` → *Roadmap & Task
List* requires the roadmap and backlog to move in the same turn. The `[needs-you]` dashboard entry is
the only surface that leads with it. `check-docs.py` is green and `check-backlog-closure.py` only WARNs
(3 rows), so no guard catches this.

### L3 (Low): the bias claim is right in direction but understates its own mechanism

The row and dashboard say the bias favours the scheme "(a split or defer stops the count while the
work continues elsewhere)". On PR #397's log the larger effect comes from `termination_window`
(`:575`), which admits only `outcome == "stopped"`. Four subjects that ran **6-7 rounds** and were
closed by a DEFER recorded as `outcome: "continued"` are **excluded from the window entirely**:
- trigger3-lost-bet, 7
- backlog-scrub, 6
- ci-time-limits, 6
- comprehensibility-chrome-cases, 7

These are the same four that trigger 11 lists. Counting them would raise the median, so the claim
"it still did not beat 4" gets stronger. As written, though, the parenthetical names a split/defer
mechanism and omits the measured exclusion. And "a split stops the count while work continues" is an
inference, not a measurement: no child-subject rounds were added up. Suggest stating the exclusion
with the four names, and labelling the split half as inferred.

## Not found

- No ambient pass on `"FAIL" not in _o`. With t4 suspended, the fixtures produce no other FAIL text,
  and mutation 1 (both FAIL and WARN printed) is killed by that assertion as intended.
- The median-3 case is not vacuous. Loosening t4's threshold by one kills it together with two
  pre-existing unit cases.
- Commit messages: the numbers (`[4, 7, 4, 5, 4]`, 4 vs 4, 125 to 128, 2017 to 2020, three cases,
  three mutations) all check out against what I ran. I did not re-run the scoped `--mutate` sweep
  (128/128). I replayed only the three new entries.

VERDICT: NOT CONVERGED

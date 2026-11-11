<!-- claude-review: subagent, round 1 -->
# trigger3-lost-bet — round 1 — Claude half

Reviewed range: `753645a7..fd236947` (branch `feat/trigger3-lost-bet`).

Method. Everything below was executed unless it is labelled UNVERIFIED. The module was imported from
the worktree by a probe script under the session scratchpad (`t3probe/probe.py`), which builds logs,
validates each row against its unit's earlier rows exactly as `main()` does (same `seen` loop), and
prints `lost_bets`, t1, t2, t3, t8 and t10. Mutations ran against a `git archive fd236947` copy in
the scratchpad with `HOME` redirected. No repository or worktree file was written except this one,
and no git write was run.

Baseline:

```
241/241 self-test cases passed
decision-scheme: 12 row(s), 8 scored (4 retroactive, so 4 scoreable, 1 missed-escalation acknowledgment(s)); pinned median 4 vs now 4.0
  WARN  trigger 6 ... WARN trigger 8 ... WARN trigger 10 ESCALATED IN HINDSIGHT: 1 lost bet(s) ... (work-lines-always-on/...)
rc=0
```

Mutation manifest, run in the copy: all **106** entries apply, every anchor occurs exactly once in
the shipped file, **0 survivors**, and every entry's `expect` case names appear in the red output.

---

## F1 — Major — an acknowledgment can be written INSTEAD of the next bet, mid-stream and repeatedly, so trigger 3's FAIL has a one-line escape with no time bound

`scripts/check-decision-scheme.py` `validate_acknowledgment` (the only acceptance condition is
`bets[-1].get("outcome") == "continued"`).

The docstring says the acknowledgment records an escalation missed **at the time**, written in
hindsight. It also says the in-flight FAIL is "the intended pressure (the next bet must be logged
before the next round runs)". Nothing ties the acknowledgment to hindsight. It is accepted the moment
the lost outcome is written. A coordinator who sees trigger 3 go red can write an acknowledgment
instead of a bet. That is cheaper: it needs no prediction and makes no ladder move. The work then
goes on accreting with a permanent WARN.

Input, all rows valid under the `main()` validation loop:

```
[bet(s,u,accrete,continued), ack(s,u,"about to fold again")]
  invalid: []   t3: None   t10: 1 lost bet(s) escalated only in HINDSIGHT (s/u) ...
[bet(s,u,accrete,continued), ack("folding r3"), ack("folding r4"), ack("folding r5")]
  invalid: []   t3: None   t10: (same single WARN)   t2/t8/t1: None
```

So the pressure the trigger was rebuilt to apply goes away at the first row that costs nothing, and
any number of further rounds and acknowledgments stay quiet past a single WARN. Brief question (b)
asks exactly this: *acknowledge, then keep losing*.

Fix, in order of cost:
- (i) refuse a second acknowledgment of the same lost bet. "The last prospective bet lost and no
  acknowledgment follows it" is one line in the same function.
- (ii) require the subject to have STOPPED before an acknowledgment is accepted. Only then is "the
  escalation was missed" a statement about the past. This is derivable at the CLI from the round
  documents `_round_docs` already reads (a CONVERGED coordinator doc after the bet), or it can be
  authored as `rounds_at_termination` on the acknowledgment. The second option needs a
  `BET_FIELDS` change.
- (iii) If neither is wanted, state in the docstring that an acknowledgment may be written
  mid-stream and turns the FAIL into a WARN for the rest of the stream. Do not describe the FAIL as
  pressure that cannot be bypassed.

## F2 — Major — the new `kind` field is already reserved, with the opposite meaning, by a current plan

`scripts/check-decision-scheme.py` `validate_row` (`if "kind" in row: ... "a bet row carries no kind
at all"`) versus `docs/superpowers/plans/2026-10-20-decision-log-model-redesign.md:145-154`. That plan
is marked `**Status:** 🟠 current` and resumable at the owner's call. It defines
`"kind": "attempt" | "observation"` on every row.

Executed: `validate_row({"subject":"s","unit":"u","route":"accrete","kind":""})` returns
`kind '' is not a known row kind — the only one is 'missed-escalation'; a bet row carries no kind
at all`. A `kind: "attempt"` row from that plan's schema is therefore CANNOT RUN today. Two designs
now give one field name opposite meanings, and the change does not mention the other one. This is
the duplicate-vocabulary shape that `check-vocabulary-collisions.py` exists to catch, in a JSON log
that guard does not read.

The same plan also holds a stale row about this trigger (`:312`, "**t3** `routes_collapsed` ⛔
BROKEN BY §2.1"). That row describes a deleted function. The new t3 reads `outcome` on route rows,
which the plan's §2.1 moves onto observation rows, so the new trigger breaks the same way and the
plan does not say so. That is question (d)'s "anything else that depended on the old trigger 3",
and this is the only living document I found that does (`grep -rn routes_collapsed` outside
`docs/reviews/`: two 2026-10-20 explainers, which are historical, plus this plan).

Fix: either choose a field name the plan does not reserve, or make the acknowledgment a value of
the plan's `kind` and say so. In both cases add a ⟳ note to the plan's t3 row saying the trigger it
analyses is gone and that its replacement reads `outcome` from bet rows.

## F3 — Minor — trigger 10's "retroactive" branch cannot be reached from any valid log, and two cases test an invalid one

`lost_bets` (`"hindsight"` when `later` holds no prospective row), and the self-test fixture
`_warn2 = [bet(t,v,accrete,continued), bet(t,v,redesign, retroactive=True)]`.

A retroactive row after a prospective bet on the same unit is refused by `validate_row` door (c),
which this change keeps. Executed on `_warn2` itself and on a scored variant:

```
[(2, "a retroactive row may not follow a PROSPECTIVE bet on ('t', 'v') — hindsight appended after a real bet closes ...")]
```

So in production the only route to WARN is an acknowledgment. Two cases are satisfied by a log that
`main()` would report as CANNOT RUN:

- "...and so does one followed only by a RETROACTIVE route row, on another unit"
- "...and classifies a hindsight-only follow-up as hindsight"

The ⟳ comment that replaced the deleted provenance cases says the property "is now asked of trigger
3 by 'a lost bet followed only by a RETROACTIVE route row'", and that input is unreachable. The
docstring table ("later rows, but only retroactive / acknowledged -> WARN") overstates the same
point. The two-distinct-inputs rule is met in form only: the second input is not in the domain.

Fix: drive the second WARN input with an acknowledgment on another unit, after a lost second rung.
Then either make `lost_bets` read only acknowledgments for `"hindsight"`, or keep the branch and
label it defensive and unreachable.

## F4 — Minor — a lost TERMINAL bet makes trigger 3 demand an escalation that does not exist, and the defect is reported twice

`t3_lost_bet_not_escalated` / `lost_bets` do not ask whether a next route exists.

```
[bet(s,u,defer,continued, skipped=[accrete,redesign,split], why_skipped="obv")]
  t2: 1 unit(s) exhausted every route and still carry findings (s/u) ...
  t3: 1 lost bet(s) with no next route logged (s/u) — ... the ladder's escalation never recorded ...
```

After a lost DEFER there is no rung to escalate to, so "escalation never recorded" is false. The
condition t3 fires on here is ladder structure, which is brief question (a). The verdict does not
change, because t2 already FAILs. But this file's own rule (t8's docstring: "two triggers naming one
defect is a reader who cannot tell which is which") is broken. The only way to quiet t3 is an
acknowledgment, which still leaves t2 red.

Fix: skip a lost bet when `route_next(routes_accounted(unit_rows[:i+1])) is None` and leave it to
t2. Add a case where the same lost defer gives t2 FAIL and t3 None.

## F5 — Minor — a bet that is never scored is quiet on every trigger forever, and the new trigger makes leaving it unscored the cheapest choice

```
[bet(s,u,accrete)]          # outcome null, stream ran on for any number of rounds
  lost_bets: []  t2/t3/t10/t8/t1: None
```

This is not new; the old t3 also counted only scored rows. What changes is the incentive. Writing
`continued` now creates a FAIL that can only be cleared by a ladder move. Leaving `outcome` null
creates nothing, and "an IN-FLIGHT bet (no outcome yet) is not a lost bet" is pinned as a case.
`derive_outcome` could see this from the round documents and is deliberately unwired (its
docstring gives the bounds). Brief question (a), "stay quiet on a real conveyor": yes, through the
null outcome.

Fix: not necessarily in this slice. At minimum, the in-flight caveat in t3's docstring should state
the converse: an unscored bet stays in flight forever and no trigger ages it. A cheap guard would
WARN on a prospective bet with `outcome` null whose subject has a coordinator round document numbered
above the round the bet was placed for.

## F6 — Minor — "lost bet" is the trigger's word for `outcome: continued`, which is not whether the bet's prediction held

The live row the acknowledgment answers (`work-lines-always-on`, the accrete bet) makes a
prediction: "r2 finds no Blocking and at most one Major". Its own `observed` says r2 was "inside the
bet (no Blocking, at most one Major), so it held". The new trigger output and the acknowledgment
both call it a "lost accrete bet". Under the scheme both are defensible: `outcome` is the route's
FAILURE_OBSERVATION ("the same unit carried findings in the round after the patch"), and the
prediction is a separate claim. But trigger 3's message now treats `outcome` as the definition of
losing, and puts "the bet's failure was observed" in front of a coordinator whose bet held.

Base rate. This part is inference from measured counts and is UNVERIFIED as a prediction. Of 89
subjects in the corpus with 2 or more rounds, 69 reached round 3 (`_round_docs` over the worktree's
`docs/reviews`). If an accrete bet goes in at round 1 and later rounds carry findings on that unit,
`continued` follows. The ladder then requires a redesign bet before round 3, and folding in place
(what work-lines did, and the usual practice here) can only be written as an acknowledgment. So
trigger 10 may end up warning on most fed subjects. That is the shape backlog #56 says gets ignored.

Fix: rename the message to say what it measures ("a bet whose route's failure observation was
seen"), or note the base rate in t10's docstring so a WARN on most subjects is expected rather than
alarming.

---

## Checked and found sound

- **(b) trigger 2's change from last row to last bet** is a fix, not a regression. With no
  acknowledgment the two readings are identical, because every pre-change row is a bet. With an
  acknowledgment the old reading went quiet. Executed: `[defer lost (skip-declared), ack]` gives t2
  FAIL and t10 WARN. `bets` keeps retroactive rows, which matches the old last-row semantics.
- **(b) the other triggers and scoring** handle the new kind correctly. `prospective()` drops it, so
  t4, t7 and t9 (`termination_window`) never see it. Every bet field is refused on it: `outcome`
  (even `null`), `rounds_at_termination`, `prediction`, `ranker_hit`, `retroactive` and `route` were
  each executed and refused, so t5 cannot score it. t1 and t8 cannot be satisfied by it alone,
  because it needs a prospective bet on the same unit first (`ack-no-bet` → refused). An
  acknowledgment written before its bet in file order is refused. A bet after an acknowledgment is
  still checked against the ladder, which ignores the acknowledgment. A retroactive row after an
  acknowledgment is still refused by door (c).
- **(a) the in-flight FAIL**, between writing `continued` and writing the next bet, is the right
  call in my judgement. It is red only if a commit lands between two edits that belong together:
  the outcome and the next bet are both written when the result arrives, before the fold. Not a
  finding. It becomes one only together with F1, because the acknowledgment makes the window
  escapable.
- **(a) the cases asked about.** A skipped rung that is lost and followed by nothing gives FAIL. A
  lost bet followed by a bet on a RENAMED unit gives FAIL on the original unit, which is correct: a
  rename does not escalate. A retroactive lost bet followed by a live bet is quiet. Five forced
  first-rung `stopped` accrete bets are quiet.
- **(c) the work-lines acknowledgment is TRUE.** Checked against
  `docs/reviews/codex/work-lines-always-on-r2-codex.md` (1 Major + 4 Minor, NOT CONVERGED; the Major
  is the clear-path reordering), `coordinator/...-r2-coordinator.md` (the fold went to the
  implementer subagent, in place), `claude/...-r3-claude.md` (one Minor, the unasserted
  partial-clear result), `coordinator/...-r3-coordinator.md` (FOLD: coordinator) and
  `codex/...-r4-codex.md` ("Executed against temporary copies of `7b2d3dee`", "No findings",
  CONVERGED). Four rounds; no redesign was bet or taken. The only nuance in its wording is F6.
- **(d)** Apart from the plan in F2, the edit to `review-method.md` is correct, and
  `check-fixture-variation.py` and `check-plan-code.py` (86 → 106, sum 1842 → 1862) agree with the
  manifest. That manifest has 106 entries, and the two retired names belong to the deleted function.
- **(e)** The CLI wiring cases for t3 FAIL (rc 1), t10 WARN (rc 0, with the summary line pinned) and
  the refusal of an acknowledgment of a won bet (rc 2) are real reach-the-reader tests. Each pure
  branch has two inputs, apart from the F3 exception.

VERDICT: NOT CONVERGED

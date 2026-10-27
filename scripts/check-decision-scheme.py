#!/usr/bin/env python3
"""Is the route-escalation mechanism still worth having? — answered from its own log.

    python3 scripts/check-decision-scheme.py              # fire the triggers
    python3 scripts/check-decision-scheme.py --rederive   # recompute the pinned baseline
    python3 scripts/check-decision-scheme.py --self-test  # 274 cases

WHAT THE MECHANISM IS
---------------------
`redesign or accretion?` is not answerable as a classification. Measured 2026-10-20 over 314
labelled findings: `fix_induced` could be computed for 8 and agreed with the author on 2,
because **causation is not an observable** — it asks why a defect exists. 19 of 27 cited
locations were reviewer-invented fixtures, and "touched by the fix" is not "caused by the fix".

So the mechanism does not classify. It BETS, and escalates when the bet is observed to fail:

    ACCRETE  -> REDESIGN -> SPLIT -> DEFER

Each route carries the observation that says it failed, and a route is never retried on the
same unit — a second attempt IS the escalation trigger, which is what stops the loop running
forever. The figure of merit is therefore ROUNDS-TO-TERMINATION, not accuracy: a loop that
corrects itself does not need to be right first time, and accuracy was the quantity that could
not be validated (n = 3, capped by the circularity in backlog #314).

⭐ A RUNG MAY BE SKIPPED, BUT ONLY WITH A REASON (backlog #321, the owner's decision 2026-10-21).
The first version refused every non-prefix route, and the measured consequence was that the two
units of seven whose history deviated — `relocation` took SPLIT, `log-schema` took REDESIGN —
were the only two it could not express. `all triggers quiet` was therefore CAUSED by the
omission of the highest-information decisions in the slice: the ones where a human judged a
rung futile. A row may now name the rungs it skipped in `skipped` with a non-empty
`why_skipped`; both are required together and an empty reason is refused, exactly as
`check-review-recorded.py` refuses an empty `NO-REVIEW:`.

⛔ WHY THIS IS A RECORD, NOT A NEW ROUTE. Forcing ACCRETE first is the only thing that produces
the label "accrete was tried on this shape and failed"; a `start -> split` jump route would
destroy that counterfactual for nothing. ⟳ r7 Claude M10 is right that the predictor this label
is FOR does not exist — the only reader of the log is this file — so the claim that earns the
cost TODAY is the smaller one: the HUMAN RECORD of why a rung was skipped. The predictor is a
bet on top of it, and backlog #338 is deferred on COST and the owner's priority, NOT on the
"no consumer yet" principle, which would equally undercut `why_skipped` one paragraph up. So the linearity is kept and deviations are RECORDED rather than legalised — a
skip is a labelled example (shape X, human judged A/R futile, went to S, outcome Y), which is
precisely what the old schema threw away. A RETRY stays inexpressible and a WALK-BACK down the
ladder is refused; neither is a skip, and no reason declares one into one.

WHY THIS FILE EXISTS RATHER THAN A NOTE IN A PROCESS DOC
-------------------------------------------------------
The owner asked for a re-evaluation PROMISE: what can trigger re-evaluation later? A promise
written in prose is the thing this repository has measured rotting — `review-method.md` says
"the evidence is derivable, not remembered" and `round-header-template.md` cites that line and
then introduces a hand-authored tally. So the promise is a set of predicates with stated
observations, some of which FAIL rather than warn — the table in `main()` is the list, and it
is not restated here because this sentence once said "seven" and "four" and went stale twice.

⟳ 2026-10-23 — TRIGGER 3 CHANGED ITS QUESTION (owner-approved). It used to ask whether >=5
scored rows all took one ROUTE. A unit's first bet is FORCED to be `accrete`, and every scored
row so far was a first bet, so it fired on the ladder's structure rather than on a decision.
It now asks the question the ladder actually poses: after a bet the stream CONTINUED past
(`outcome: continued` — the route's FAILURE_OBSERVATION was seen; whether the bet's PREDICTION
held is a separate claim and is not read here), was the next route logged?

    a later PROSPECTIVE bet on the unit         -> quiet
    nothing, and the bet PREDATES trigger 3     -> WARN  trigger 10 PRE-TRIGGER LOST BET
    nothing                                     -> FAIL  trigger 3  LOST BET NOT ESCALATED
    the bet was DEFER (no rung left)            -> trigger 3 is silent; trigger 2 owns it:
        ... and the DEFER does not close the unit   -> FAIL  trigger 2  NON-TERMINATION
        ... and it records rounds_at_termination    -> WARN  trigger 11 LADDER EXHAUSTED, CLOSED
                                                       (the unit is closed: no bet may follow;
                                                        close only at the subject's FINAL round)
    a NEW unit on that subject after a closure  -> WARN  trigger 12 LADDER RESTARTED

The bets that predate the trigger are a CLOSED, PINNED list in `baseline.json`
(`lost_bets_before_trigger3`), beside the other pinned history; a pin that matches no lost bet
in the log is itself named by trigger 10, so a stale pin cannot pass forever. ⚠ It is NOT the
only way a loss goes unflagged: a loss written `retroactive: true` is not a bet, so trigger 3
skips it, and it is caught only by trigger 8 — and only when its subject has NO prospective row.

⟳ r3 — THE IN-LOG ACKNOWLEDGMENT IS REMOVED. Two folds offered a `missed-escalation` row that
closed a unit instead; rounds 2 and 3 each found the previous fold's defect in it (no time
bound, then a verdict reader over the review corpus), one component, two consecutive rounds:
THRASHING. The answer was removal, not a third patch. A bet row may still carry the
decision-log-model-redesign plan's `kind` field; this file claims no field of that name.

⛔ TRIGGER 1 IS STARVATION, AND IT IS FIRST ON PURPOSE. The predecessor mechanism
(`check-review-decision.py`) was correct and saw `rounds=0` on 81% of the subjects where it
applied: 57 subjects had >=2 rounds, 10 were readable. It was never wrong; it was never fed.
A mechanism whose ancestor died of starvation must treat starvation as its loudest failure.

⚠ WHAT THIS CANNOT DO, STATED RATHER THAN HIDDEN. Every row is AUTHORED. The route taken and
whether the stream stopped are judgements a coordinator records; nothing here verifies them,
and a dishonest row produces a confident wrong verdict. That is not a defect to be fixed by
more code — it is the measured consequence of causation not being observable. What the log DOES
buy, and the reason it is append-only with `outcome: null` on arrival, is that the PREDICTION
is written before the outcome is known. A bet placed in advance can be scored; a label written
with hindsight cannot, which is exactly what backlog #314 records.

⟳ CORRECTED 2026-10-21 (r7 Claude M9): the paragraph above read as a guarantee about the DATA
and it is only a statement of intent. A hindsight label is now EXPRESSIBLE, because recording
the deferral's real history required it — so the honest form is that a hindsight label is
recordable, FLAGGED, and excluded from scoring, never that it cannot exist.

    retroactive: true   the outcome was ALREADY KNOWN when the row was written.

⛔ IT IS AUTHORED AND NOTHING VERIFIES IT, and it buys THREE things at once — all three stated
here because the first version of this caveat named only the first:
  1. the row leaves every SCORING population (`t3`, `t4`, `t7` read `prospective()`), because a
     bet whose outcome was known cannot be scored;
  2. the row still counts toward `t1_not_fed`, so it satisfies the starvation trigger — which is
     coverage, not timely use. `t8_hindsight_only` exists to say so out loud, because r7
     measured that NO trigger owned that complaint and backfill therefore silenced the only
     detector of non-use;
  3. it may fill a unit's PAST and never follow a real bet. `validate_row` refuses hindsight
     after a prospective row, because a unit backfilled to `defer` has a terminal ladder and
     every later prospective row is refused as a retry after exhaustion — IRREVERSIBLE in an
     append-only log. That refusal is the only bound; nothing limits how many rows carry the
     flag, and deriving it from git (a row whose write commit post-dates its subject's last
     round document) is possible and is NOT built.

ITS CALLER: `.github/workflows/ci.yml`, two steps — the triggers and the self-test. ⛔ It does
NOT take the `NO-CALLER:` escape, deliberately. Its predecessor declares that escape with a
defensible reason ("CI has no decision to make about whether to run a round") and the measured
consequence was that nothing ever executed it; the open proposal that became this slice says a
`NO-CALLER:` is an escape, not a destination. CI has no decision to make here either — but it
can observe whether the mechanism is being FED, and that is the question the escape hid.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEME_DIR = REPO / "docs" / "reviews" / "decision-scheme"
LOG = SCHEME_DIR / "decision-log.jsonl"
BASELINE = SCHEME_DIR / "baseline.json"

# The ladder. ORDER IS THE DESIGN: start at the cheapest route, because the cost of a wrong bet
# is one more round. DEFER is terminal — it is the answer when the routes are exhausted, which
# is the stopping rule backlog #136 asks for and could not derive from finding counts.
LADDER = ("accrete", "redesign", "split", "defer")

# A route "failed" when the stream did not stop. Spelled out per route so the observation is
# named rather than implied — a route whose failure cannot be observed is a decision wearing a
# checkbox (portable-practices §3).
FAILURE_OBSERVATION = {
    "accrete": "the same unit carried findings in the round after the patch",
    "redesign": "the unit still carried findings after a restructuring fold — a redesign "
                "applied without stopping the finding stream (backlog #136, point 3)",
    "split": "the split-out subject thrashed on its own in its first two rounds",
    "defer": "terminal — nothing escalates past it",
}

OUTCOMES = ("stopped", "continued")

# Appended to trigger 4's verdict while it is a WARN (see `main`), so no run reads as a pass.
T4_SUSPENDED = (" — SUSPENDED TO A WARN by the owner 2026-10-25, pending backlog #327 (keep, "
                "simplify or retire the scheme); NOT a pass")
# The `baseline.json` key holding the lost bets that PREDATE trigger 3 (see `pinned_lost_bets`).
PRE_TRIGGER_PINS = "lost_bets_before_trigger3"


# ------------------------------------------------------------------ pure: the ladder
def route_next(tried: list[str]) -> str | None:
    """PURE. The next route to bet on, given the routes already tried on ONE unit.

    ⛔ A ROUTE IS NEVER RETRIED. The owner's requirement was "if we detect the failure of
    choice then we should be able to try again with other choices" — OTHER choices. Retrying
    the same route is how an escalation ladder becomes an infinite loop, so a repeat in `tried`
    advances past it rather than being honoured.

    Returns None when the ladder is exhausted, which is trigger 2's observation.
    """
    seen = set(tried)
    for route in LADDER:
        if route not in seen:
            return route
    return None


def route_sequence_error(tried: list[str]) -> str | None:
    """PURE. Why `tried` is not a prefix of the ladder, else None.

    A missing input is a failure, never a pass — `check-review-decision.sequence_error`'s own
    posture, borrowed deliberately. A log row claiming `["split"]` with no `accrete` before it
    has skipped two routes, and reading it as "one route tried" understates the escalation.
    """
    if not tried:
        return None
    unknown = [r for r in tried if r not in LADDER]
    if unknown:
        return f"unknown route(s) {unknown}; the ladder is {list(LADDER)}"
    if len(set(tried)) != len(tried):
        dupes = sorted({r for r in tried if tried.count(r) > 1})
        return f"route(s) {dupes} retried — a repeat is the escalation trigger, not a step"
    want = list(LADDER[:len(tried)])
    if tried != want:
        return f"routes out of ladder order: got {tried}, a prefix would be {want}"
    return None


def prospective(rows: list[dict]) -> list[dict]:
    """PURE. The rows that are scoreable BETS — the retroactive ones removed.

    ⛔⛔ PROVENANCE IS A FIELD BECAUSE A TRIGGER CANNOT READ PROSE (r7 Codex H1/M2/M3, one
    cause, three doors). Writing the deferral's real history needed rows whose outcomes were
    ALREADY KNOWN when they were written. Those rows say exactly that in `prediction` — and
    MEASURED before this existed: `t3` went from firing to QUIET, `t4` went from firing to QUIET
    by DISPLACING a subject out of its last-five window, and `t7` quoted an accuracy bound over
    a sample of 10 when only 8 predictions had been made. A disclaimer a human can read is not a
    population a predicate can compute over.

    ⚠ WHAT THIS DELIBERATELY DOES NOT FILTER, because these are OBSERVATIONS rather than bets:
    `t1_not_fed` (a retroactive row is still a row, and feeding the starvation trigger with real
    history is the whole point of the schema change — it proves coverage, not timely use, which
    is a different complaint); `t2_non_termination` (whether a unit exhausted the ladder and
    still carried findings is observed, not predicted); `t5_ranker_miss` (already keyed on the
    presence of `ranker_hit`, which a retroactive row does not carry).
    """
    # ⚠ TWO STATEMENTS, TWO DECISIONS. r7 Claude L11 found this helper raising on a non-dict row
    # — the class the fold had just fixed one function away — and the dict guard and the
    # retroactive filter are separate choices: on one line only one of them could be guarded.
    dicts = [r for r in rows if isinstance(r, dict)]
    return [r for r in dicts if not r.get("retroactive")]


def is_prediction(row: dict) -> bool:
    """PURE. Did this row make a SCOREABLE ranker prediction?

    ⛔ ONE RULE, ONE PLACE, AND THIS HELPER EXISTS BECAUSE THE CLAIM SHIPPED BEFORE THE FACT.
    The fold's own commit message said t7 had "borrowed t5's rule"; measured by r7 Claude (M6),
    it had written a SECOND one — t5 asked `"ranker_hit" in r` and t7 asked
    `isinstance(..., bool)`, so `ranker_hit: 0` was a MISS to one and INELIGIBLE to the other.
    That is this repository's most-recorded defect (17 instances) arriving inside the commit
    that claimed to remove it.

    An abstention is not a prediction: `ranker_hit` is written ONLY when the ranker named a
    component, so the presence of an explicit BOOL is the test. A non-bool is not a quiet miss —
    `validate_row` refuses it — but these are documented pure helpers with callers of their own,
    so the rule lives here rather than twice.
    """
    return isinstance(row.get("ranker_hit"), bool)


# ------------------------------------------------------------------ pure: the triggers
def t1_not_fed(rows: list[dict], subjects_since_arming: list[str]) -> str | None:
    """FAIL. Subjects that reached >=2 rounds after arming and never appear in the log.

    ⛔ THE LOUDEST TRIGGER, because it is how the predecessor died: correct, and fed 19% of the
    time. `subjects_since_arming` is supplied by the caller rather than globbed here so the
    rule is testable without a repository.
    """
    logged = {r.get("subject") for r in rows}
    missing = sorted(s for s in subjects_since_arming if s not in logged)
    if not missing:
        return None
    return (f"{len(missing)} subject(s) reached >=2 rounds with no log row: "
            f"{', '.join(missing[:6])}{' …' if len(missing) > 6 else ''} — the scheme is not "
            f"being fed, which is how its predecessor failed at 81%")


def t8_hindsight_only(rows: list[dict], subjects_since_arming: list[str]) -> str | None:
    """WARN. Subjects whose EVERY row is retroactive — fed, but never in time.

    ⛔⛔ THE COMPLAINT THAT HAD NO HOME (r7 Claude B1). `prospective()` deliberately leaves
    `t1_not_fed` reading all rows, with the reason that a retroactive row "proves coverage, not
    timely use, which is a different complaint". That is only sound if some trigger owns the
    other complaint — and the reviewer enumerated all seven and found NONE did. So the only
    detector of non-use was satisfiable by backfill, in a file whose founding concern is that
    its predecessor "was correct and saw rounds=0 on 81% of the subjects where it applied".

    MEASURED on the live log at the time this was written: `t1_not_fed` is silent over all six
    rows and FIRES over the four prospective ones, naming `decision-log-model-redesign`. Both
    sides of that experiment are in the record — CI's run on the pre-change commit printed the
    firing half unprompted.

    ⚠ WARN, NOT FAIL, AND THE REASON IS NOT TIMIDITY. Demanding a prospective row for a subject
    whose work is FINISHED is unsatisfiable by construction — the deferral this schema change
    exists to record can never acquire one — and a gate that is red from birth gets switched off
    (backlog #56). What a FAIL-grade version needs is a CUTOVER date, so the rule can ask "armed
    AFTER the schema could express this, and still only fed in hindsight". That is a design
    decision about when the clock starts, and it is filed rather than guessed.

    ⚠ A subject with NO row at all is trigger 1's business and is deliberately absent here: two
    triggers naming one defect is a reader who cannot tell which is which.
    """
    by_subject: dict[str, list[dict]] = {}
    for r in rows:
        if isinstance(r, dict):
            by_subject.setdefault(r.get("subject"), []).append(r)
    hindsight = sorted(s for s in subjects_since_arming
                       if by_subject.get(s) and not prospective(by_subject[s]))
    if not hindsight:
        return None
    named = ", ".join(hindsight[:6]) + (" …" if len(hindsight) > 6 else "")
    return (f"{len(hindsight)} of {len(subjects_since_arming)} subject(s) are fed ONLY in "
            f"hindsight: {named} — every row for them is retroactive, so the mechanism is a "
            f"historian for that subject, not a decision aid; trigger 1 is quiet because a row "
            f"EXISTS, which is coverage, not timely use")


def t2_non_termination(rows: list[dict]) -> str | None:
    """FAIL. The primary falsifier: a UNIT whose ladder is exhausted and still carrying findings.

    ⛔ REWRITTEN AFTER r1 (Claude B3 + Codex H4, one cause). The first version read ONE ROW at a
    time and asked whether that row's AUTHORED `routes_tried` held four distinct routes. An
    author who never grew the field made exhaustion invisible, and five rows retrying one route
    exited 0 with `all triggers quiet`. Now the history is DERIVED per (subject, unit), so it
    cannot be understated by omission, and the question is asked of the unit rather than of a row.

    ⛔ EXHAUSTION IS A LADDER POSITION, ASKED THROUGH `routes_accounted` + `route_next`, not a
    count of four distinct attempts. Once a rung is skippable with a reason, a unit can reach
    DEFER having attempted ONCE — so an attempt-counting test would stop firing exactly where a
    skip is used, switching the primary falsifier off through the door that was just opened. A
    case covers the skipped-to-terminal unit and an adjacent one that is still escalating.

    ⟳ r5 (the owner's option A): only an OPEN exhausted unit fails here. A unit whose continued
    DEFER records `rounds_at_termination` is CLOSED (`closes_unit`) and is trigger 11's WARN —
    see there for the incentive that remains.
    """
    bad = [k for k, closed in exhausted_units(rows) if not closed]
    if not bad:
        return None
    names = ", ".join(f"{a}/{b}" for a, b in bad[:4])
    return (f"{len(bad)} unit(s) exhausted every route and still carry findings ({names}) — "
            f"the claim that escalation terminates is refuted, not delayed")


def closes_unit(row: dict) -> bool:
    """PURE. Does this bet CLOSE its unit — a `continued` DEFER that records how it ended?

    ⟳ 2026-10-23 r5, the owner's decision (option A). `validate_row` admits
    `rounds_at_termination` on a `continued` row only when its route is DEFER, so a closing row
    always ends an exhausted ladder. One rule, one place: trigger 2, trigger 11 and the
    validator's closed-unit refusal all ask it here.

    ⛔ CLOSE ONLY AT THE END (the owner's containment, r5). `rounds_at_termination` on a closing
    DEFER is the subject's FINAL round, written once review has CONVERGED. A unit closed early,
    while rounds continue, is a FALSE claim — and this script cannot detect it: reading the review
    corpus to check was the component that thrashed in r2–r3 and was removed. The rule is the
    author's to keep; what IS visible is a ladder restarted on a new unit (trigger 12).
    """
    return row.get("outcome") == "continued" and "rounds_at_termination" in row


def exhausted_units(rows: list[dict]) -> list[tuple]:
    """PURE. ((subject, unit), closed) for every unit whose ladder is exhausted and whose last
    bet the stream CONTINUED past. One producer, two readers — trigger 2 (open) and trigger 11
    (closed) — so they cannot disagree about which units are exhausted.
    """
    out = []
    for key, unit_rows in group_by_unit(rows).items():
        # ⛔ EXHAUSTION IS "NOTHING LEFT TO ESCALATE TO", NOT "FOUR ATTEMPTS MADE". A unit that
        # reached DEFER by declaring a skip has an exhausted ladder with one attempt in it, so
        # counting attempts would switch the primary falsifier off exactly where a skip is used.
        exhausted = route_next(routes_accounted(unit_rows)) is None
        # ⚠ TWO DECISIONS, TWO LINES, DELIBERATELY. Which producer answers "where is the
        # ladder" and whether an exhausted unit fires are separate choices, and the mutation
        # harness refuses a second entry on one anchor as "measuring nothing new" — so the
        # off-by-one entry that used to sit on the attempt-count comparison has a line to bind
        # to rather than being retired with the expression it named.
        if not exhausted:
            continue
        if unit_rows[-1].get("outcome") == "continued":
            out.append((key, closes_unit(unit_rows[-1])))
    return out


def ladder_restarts(rows: list[dict]) -> list[tuple]:
    """PURE. (subject, closed unit, new unit) for every unit whose FIRST row comes after another
    unit of the same subject was CLOSED (`closes_unit`). File order is the append order.

    A unit that existed BEFORE the closure is a sibling, not a restart, and is not returned.
    """
    first: dict[tuple, int] = {}
    closed_at: dict[tuple, int] = {}
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        first.setdefault(unit_key(r), i)
        if closes_unit(r):
            closed_at.setdefault(unit_key(r), i)
    out = []
    for (subject, closed), at in closed_at.items():
        for (other_subject, unit), began in first.items():
            # ⚠ ONE DECISION PER LINE: which units are on the SAME subject, and which of them
            # began AFTER the closure. The closed unit needs no exclusion: its first row is at or
            # before its own closing row, so `began > at` can never hold for it.
            if other_subject != subject:
                continue
            if began > at:
                out.append((subject, closed, unit))
    return sorted(out)


def t12_ladder_restarted(rows: list[dict]) -> str | None:
    """WARN. A subject's ladder restarted on a NEW unit after one of its units was CLOSED.

    ⟳ 2026-10-23 r5, the owner's second containment on option A. Closing a unit cannot be
    undone, but a NEW unit on the same subject starts a fresh ladder at ACCRETE — which is the
    move a closure exists to stop, if the "new" unit is the old work renamed. A genuinely
    separate unit is legitimate, so this WARNS rather than fails or refuses: it must be SEEN,
    not forbidden. Units that existed before the closure are siblings and do not warn.
    """
    found = ladder_restarts(rows)
    if not found:
        return None
    names = "; ".join(f"{s}: {u} after {c} closed" for s, c, u in found[:4])
    return (f"{len(found)} ladder(s) restarted after exhaustion ({names}) — a closed unit "
            f"cannot be reopened, so check the new unit is separate work, not the old one renamed")


def t11_ladder_exhausted_closed(rows: list[dict]) -> str | None:
    """WARN. A unit exhausted the ladder, the stream continued, and its DEFER CLOSED the unit.

    ⟳ 2026-10-23 r5, the owner's decision (option A) — the FAIL/WARN split of trigger 2, in the
    style of 3/10. A `continued` DEFER is the honest score for "every route was tried and the
    findings did not stop; the work is set down". Without a way to record that, the only quiet
    score was `stopped`, which is false — so honesty was punished with a permanent FAIL. A DEFER
    that records `rounds_at_termination` declares the unit CLOSED: it is named here instead of
    failing trigger 2, and `validate_row` refuses any later bet on it (a closed unit cannot be
    reopened; a new attempt is a new unit).

    ⚠ THE INCENTIVE THAT REMAINS, stated rather than hidden: scoring a deferral `stopped` is
    still QUIET, while scoring it honestly as a closed `continued` WARNS. The gap between the two
    is now a WARN, not a permanent red — smaller, not gone. Nothing here can tell a false
    `stopped` from a true one; the review corpus could, and reading it was removed (r2–r3).
    """
    closed = [k for k, c in exhausted_units(rows) if c]
    if not closed:
        return None
    names = ", ".join(f"{a}/{b}" for a, b in closed[:4])
    return (f"{len(closed)} unit(s) exhausted every route, the stream continued, and a DEFER "
            f"CLOSED them ({names}) — set down, not repaired; the ladder terminated, the "
            f"findings did not")


def lost_bets(rows: list[dict]) -> list[tuple]:
    """PURE. Every prospective bet the stream CONTINUED past with no next bet: (subject, unit, route).

    ⟳ r4 Codex Major: the identity is the BET, not the unit. Keyed on (subject, unit), a pin on a
    unit's historical loss also excused every LATER loss on that unit. (subject, unit, route)
    names exactly one bet, because `route_next` never lets a unit repeat a route.

    "Lost" here means `outcome: continued` and nothing more: the route's FAILURE_OBSERVATION was
    seen, so the ladder says escalate. ⚠ It is NOT a claim that the bet's PREDICTION failed — a
    prediction can hold while the stream continues (work-lines-always-on's did), and the two are
    separate fields. A bet is NOT returned when (a) a later PROSPECTIVE bet exists on its unit —
    it escalated in time — or (b) it left NO rung to escalate to (a continued DEFER, or any bet
    that exhausts the ladder). (b) is trigger 2's defect, and two triggers naming one defect is a
    reader who cannot tell which is which (r1 F4).

    ⛔ "SAME UNIT" AND "LATER" ARE `group_by_unit`'s, NOT A SECOND DERIVATION. The unit is
    `unit_key` and "later" is file order inside that unit's group — the append-only order
    `invalid_rows` validates each unit's history in. "Is this row a bet" is `prospective()` asked
    of one row, and "is a rung left" is `route_next(routes_accounted(...))`, the validator's own
    ladder position. A later RETROACTIVE row is not an escalation and in a valid log cannot occur
    after a real bet (door (c)), so it does not quiet this.
    """
    out = []
    for key, unit_rows in group_by_unit(rows).items():
        for i, r in enumerate(unit_rows):
            # ⚠ ONE DECISION PER LINE: which rows are BETS, which bets the stream continued
            # past, and whether the ladder had a rung left to escalate to.
            if not prospective([r]):
                continue
            if r.get("outcome") != "continued":
                continue
            if route_next(routes_accounted(unit_rows[:i + 1])) is None:
                continue                 # nothing to escalate to — trigger 2's verdict
            if prospective(unit_rows[i + 1:]):
                continue                 # a real next bet was placed — escalated in time
            out.append(key + (r.get("route"),))
    return out


def t3_lost_bet_not_escalated(rows: list[dict], pinned: frozenset) -> str | None:
    """FAIL. The stream continued after a prospective bet and no next route was ever logged.

    ⟳ 2026-10-23, REPLACING `t3_routes_collapsed` (owner-approved). The old trigger failed when
    >=5 scored prospective rows all took one route — but a unit's FIRST bet is FORCED to be
    `accrete` by the ladder, and the only scored rows were first bets. MEASURED on a merge of two
    logs: 5 scored prospective rows, all accrete, and the trigger fired on the ladder's STRUCTURE,
    not on a decision. Under a forced first rung route diversity cannot discriminate, so it is
    not asked at all any more.

    ⭐ THE DECISION THIS SCHEME ACTUALLY MAKES IS WHAT HAPPENS AFTER THE STREAM CONTINUES: the
    next route is logged, or work silently keeps accreting under folds — the conveyor the old
    trigger was named for, now asked of the place it can occur.

    ⛔ THE ONE DECLARED EXEMPTION is `pinned`: the CLOSED list of lost bets that PREDATE this
    trigger, read from `baseline.json` by `pinned_lost_bets` — a bet placed before the rule
    existed could not have obeyed it. Nothing adds to that list at run time, and a bet placed
    after this trigger shipped is never on it. ⚠ (r5) It is not the only route to silence: a loss
    written `retroactive: true` is not a bet, so this trigger skips it, and it is caught only by
    trigger 8, and only when its subject has no prospective row at all.
    ⟳ r3: an earlier fold offered an in-log "missed-escalation acknowledgment" instead. Rounds 2
    and 3 each found its own fold's defect in it (no time bound; then a verdict reader over the
    review corpus), which is THRASHING, so it was REMOVED rather than patched a third time.

    ⚠ AN IN-FLIGHT WINDOW EXISTS, stated rather than hidden. `outcome` is filled into a row when
    its round's result arrives, and the NEXT bet is written before the next round is dispatched
    — so between those two writes this fires. That is the intended pressure, and a commit that
    lands in the window is red.

    ⚠ LIMIT, NOT FIXED HERE (r1 F5): a bet whose `outcome` is never written stays in flight
    forever — no trigger ages an unscored bet, so leaving `outcome` null is quiet everywhere.
    """
    unlogged = [k for k in lost_bets(rows) if k not in pinned]
    if not unlogged:
        return None
    names = ", ".join(f"{a}/{b}" for a, b, _ in unlogged[:4])
    return (f"{len(unlogged)} bet(s) the stream continued past with no next route logged "
            f"({names}) — the route's failure observation was seen and the ladder's escalation "
            f"was never recorded, so the work kept going on a route the log records as failed")


def t10_pre_trigger_lost_bet(rows: list[dict], pinned: frozenset) -> str | None:
    """WARN. A lost bet that PREDATES trigger 3 is exempted by its pin — or a pin matches nothing.

    The FAIL/WARN split of trigger 3, in this file's existing style (t4/t9): one producer,
    `lost_bets`, two readers that cannot disagree about which bets the stream continued past.

      * a PINNED lost bet is named, not hidden: it is history the rule could not have governed,
        and a reader should still see that its escalation was never logged;
      * an UNUSED pin — no unescalated lost bet with that (subject, unit, route) in this log — is named
        too, because a pin that silently matches nothing would pass forever. It means one of two
        things, and the message says both: the bet's row lives on a branch not merged here, or a
        later prospective bet escalated it and the pin is stale and should be deleted.
    """
    found = set(lost_bets(rows))
    hit = sorted(k for k in pinned if k in found)
    unused = sorted(k for k in pinned if k not in found)
    if not hit and not unused:
        return None
    parts = []
    if hit:
        names = ", ".join(f"{a}/{b} ({c})" for a, b, c in hit)
        parts.append(f"{len(hit)} lost bet(s) PREDATE trigger 3 and are pinned in baseline.json "
                     f"({names}) — their next route was never logged, and they are history the "
                     f"rule could not have governed")
    if unused:
        names = ", ".join(f"{a}/{b} ({c})" for a, b, c in unused)
        parts.append(f"{len(unused)} pin(s) match no unescalated lost bet in this log ({names}) "
                     f"— expected while that bet's row is on a branch not merged here; otherwise "
                     f"a later bet escalated it and the pin is stale and should be deleted")
    return "; ".join(parts)


def termination_window(rows: list[dict], size: int = 5) -> list[tuple]:
    """PURE. The last `size` terminated SUBJECTS as (rounds, route) — latest occurrence last.

    ⛔⛔ ONE PRODUCER, TWO READERS (r8 Codex M2). `t4_no_improvement` and
    `t9_deferral_composed` each built this window themselves, and the duplicate WAS the hazard:
    MEASURED, deleting t9's `per_subject.pop(...)` left 201/201 GREEN and made BOTH triggers
    silent on a deferral-composed window — t9 computed its median from first-insertion order and
    concluded t4 owned a window t4 was not firing on. Two guards, one hazard, nobody covering it.
    Sharing the producer makes that UNREACHABLE rather than guarded, which is the difference
    between a fix and a patch.

    ⛔ POP-THEN-REINSERT IS THE RECENCY RULE (r2 YM4): a dict UPDATE does not move a key to the
    end, so `list(...)[-size:]` over a plain assignment is "the last five by FIRST APPEARANCE",
    not the latest five. Measured then with nine rows: a median of 9 was read as 1.

    ⛔ PROSPECTIVE ONLY (r7 Codex M3): a retroactive termination does not merely LOOK like a fast
    success — it DISPLACES a real subject out of the window. [4,4,4,1,1] fires at median 4, and
    appending the deferral's retroactive stopped-at-2 row made it [4,4,1,1,2], median 2, QUIET.

    Returns [] when fewer than `size` subjects have terminated — the sample is not reached, which
    both callers treat as "no verdict" rather than as a verdict of zero.
    """
    per_subject: dict[str, tuple] = {}
    for r in prospective(rows):
        if r.get("outcome") == "stopped" and isinstance(r.get("rounds_at_termination"), int):
            per_subject.pop(r.get("subject"), None)
            per_subject[r.get("subject")] = (r["rounds_at_termination"], r.get("route"))
    if len(per_subject) < size:
        return []
    return list(per_subject.values())[-size:]


def t4_no_improvement(rows: list[dict], baseline_median: float) -> str | None:
    """FAIL by design — but SUSPENDED TO A WARN in `main()` since 2026-10-25, pending backlog #327.
    The last 5 terminated SUBJECTS are no shorter than the pre-scheme median.

    ⛔ THE COMPARATOR IS PINNED, NOT RECOMPUTED. A baseline recomputed at read time cannot
    detect that it has moved, and after the scheme ships every round count is contaminated by
    it. `baseline.json` holds median 4 over 57 subjects, derived at `5d957db8`.

    ⟳ r1 Codex M6: this counted ROWS, which are per UNIT, while the pinned comparator is per
    SUBJECT. Five units of ONE subject fired it, reporting "the last 5 subjects" over a sample
    of one. Rows are now collapsed to subjects, taking each subject's LAST terminated row.
    """
    # ⛔ THE WINDOW IS PRODUCED ONCE AND SHARED WITH t9 — `termination_window` carries the
    # prospective-only rule and the pop-then-reinsert recency rule, so the two triggers cannot
    # disagree about which window they are judging.
    recent_pairs = termination_window(rows)
    if not recent_pairs:
        return None
    recent = [n for n, _ in recent_pairs]
    med = st.median(recent)
    if med < baseline_median:
        return None
    # ⚠ r7 Claude H5: when this DOES fire, the reader needs to know how much of the median is
    # deferral rather than repair, because the two are the same `outcome` today (backlog #337).
    defers = sum(1 for _, route in recent_pairs if route == "defer")
    note = (f" ⚠ {defers} of those 5 terminations were DEFERRALS, which are filings rather than "
            f"repairs" if defers else "")
    return (f"median rounds-to-termination over the last 5 SUBJECTS is {med}, against a pinned "
            f"pre-scheme median of {baseline_median} — the mechanism is ceremony, not "
            f"leverage{note}")


def t9_deferral_composed(rows: list[dict], baseline_median: float) -> str | None:
    """WARN. t4 looks like improvement, but deferrals are in the window that produced it.

    ⛔ backlog #337'S CHEAP HALF, MECHANISED RATHER THAN REMEMBERED (r7 Claude H5). `outcome:
    "stopped"` cannot distinguish a stream that stopped because the defect was REPAIRED from one
    that stopped because the work was DEFERRED, so a deferral enters t4's sample as a short,
    flattering termination. The expensive fix is a third `OUTCOMES` value and it is the owner's
    call; this is the half that needs no schema change — when t4 is QUIET and the window holding
    its median contains deferrals, say so, because that is exactly the shape in which #337's
    hazard is invisible.

    ⚠ IT FIRES ONLY WHERE t4 IS SILENT, deliberately. (Since 2026-10-25 t4 is SUSPENDED to a
    WARN pending backlog #327, so "failing" below reads "firing"; the exclusion is unchanged, because
    it keys on the median, not on t4's severity.) If t4 is already failing the reader is
    being told the stronger thing and t4's own message now carries the composition; two warnings
    for one window is a reader who cannot tell which to act on.

    ⚠ `prospective` only, like t4 — a retroactive deferral is not a bet and r7 measured it
    DISPLACING a real subject out of the window.
    """
    # ⛔ THE SAME PRODUCER t4 READS, DELIBERATELY (r8 Codex M2). A second copy here went silent
    # with its recency rule deleted while the suite stayed green, and took t4's coverage with it.
    recent_pairs = termination_window(rows)
    if not recent_pairs:
        return None
    med = st.median([n for n, _ in recent_pairs])
    if med >= baseline_median:
        return None                      # t4 is firing; it owns this window's verdict
    defers = sum(1 for _, route in recent_pairs if route == "defer")
    if not defers:
        return None
    return (f"the improvement signal is composed: median {med} beats the pinned "
            f"{baseline_median}, but {defers} of those 5 terminations took route 'defer' — a "
            f"filing, not a repair. `outcome: \"stopped\"` cannot tell the two apart "
            f"(backlog #337), so read this median as at most {5 - defers} of 5 repairs")


def t5_ranker_miss(rows: list[dict]) -> str | None:
    """FAIL on TWO CONSECUTIVE misses. A miss is a row whose examined unit was not in the lead.

    One miss is expected: the ranker's measured accuracy has a 95% lower bound of 37% against a
    ~7% chance baseline, so it is a bet, not an oracle. Two in a row is the signal, and
    `consecutive` is correct HERE (unlike in the arming condition it replaced) because this
    measures the instrument's own run of errors, not a component's recurrence.
    """
    # ⛔ AN ABSTENTION IS NOT A PREDICTION, SO IT IS NOT SCOREABLE — found by writing the
    # scheme's FIRST REAL ROWS. The ranker abstained on both of this slice's rounds (every
    # recurring component tied on appearances), I recorded `ranker_hit: false`, and this trigger
    # fired "two consecutive ranker misses" — punishing the ranker for declining to guess, which
    # is the exact incentive the abstention exists to create. `ranker_hit` is written ONLY when
    # the ranker named a component; a row without it made no bet and is skipped, which this line
    # was accidentally already doing and now does deliberately.
    marks = [bool(r["ranker_hit"]) for r in rows if is_prediction(r)]
    for i in range(len(marks) - 1):
        if not marks[i] and not marks[i + 1]:
            return (f"two consecutive ranker misses at rows {i + 1} and {i + 2} of "
                    f"{len(marks)} scored — re-fit or retire the ranking")
    return None


def t6_denominator_moved(now: dict, pinned: dict, tol: float = 0.5,
                         now_corpus: dict | None = None, pinned_corpus: dict | None = None,
                         count_tol: float = 0.05) -> str | None:
    """WARN. A finding expires when its denominator moves; say so before trusting the rest.

    ⟳ 2026-10-20, owner decision, backlog #328. It used to compare ONLY `median` and `mean` — the
    two RATE statistics — and so could not see the thing its name promises. MEASURED: the corpus
    went **392 -> 420 rounds, 105 -> 106 subjects, 81 -> 83 with >=2 rounds** while this returned
    `None`, because the median held at 4 and the mean moved 4.84 -> 4.78, well inside `tol`. The
    trigger whose entire job is noticing a moved denominator was blind to the denominator.

    ⭐ The counts it needs were ALREADY PINNED, in the same `baseline.json` the caller already
    reads — under `corpus`, beside the `rounds_to_termination` block this function was handed.
    Nothing had to be collected; it simply was not looked at.

    ⛔ WHY COUNTS GET A TIGHTER TOLERANCE THAN RATES, stated because the number is a JUDGEMENT and
    not a measurement. A rate drifting a few percent is noise — that is what `tol = 0.5` is for. A
    COUNT drifting means the pinned rate was computed over a materially different population, so
    the comparison itself is aging rather than the value. `count_tol = 0.05` is where "the median
    over 81 subjects" stops being a safe proxy for today's. ⚠ It was NOT chosen to make today's
    figures fire: at +7.1% `rounds_total` does fire and at +2.5% `subjects_with_ge2_rounds` does
    not, and both are reported together so the reader sees which moved.
    """
    out = []
    for key in ("median", "mean"):
        a, b = now.get(key), pinned.get(key)
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not b:
            continue
        if abs(a - b) / b > tol:
            out.append(f"{key} rounds/subject {b} -> {a}")
    nc, pc = now_corpus or {}, pinned_corpus or {}
    for key in ("rounds_total", "subjects_with_any_round", "subjects_with_ge2_rounds"):
        a, b = nc.get(key), pc.get(key)
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not b:
            continue
        if abs(a - b) / b > count_tol:
            out.append(f"{key} {b} -> {a} ({(a - b) / b:+.1%})")
    return ("the corpus moved under the pinned baseline: " + "; ".join(out)) if out else None


def t7_sample_reached(rows: list[dict], floor: int = 10) -> str | None:
    """WARN. Enough RANKER PREDICTIONS to re-score the bet: 10/10 lifts the bound 37% -> 74%.

    ⛔ THE POPULATION IS PREDICTIONS, NOT SCORED ROWS — `t5_ranker_miss`'s own rule, which this
    trigger failed to borrow (r7 Codex M2). The bound it quotes is about the RANKER's accuracy,
    so a row that made no prediction cannot be in its denominator; measured, eight predictions
    plus two rows carrying none reported a sample of 10. An abstention is not a prediction, and
    `ranker_hit` is written ONLY when the ranker named a component — so presence of an explicit
    BOOL is the eligibility test, exactly as t5 has it. One rule, one place.

    ⛔ AND PROSPECTIVE ONLY, for the same reason the other two scoring triggers are: a bet whose
    outcome was known when it was written cannot be scored.
    """
    sample = [r for r in prospective(rows)
              if r.get("outcome") in OUTCOMES and is_prediction(r)]
    if len(sample) < floor:
        return None
    hits = sum(1 for r in sample if r["ranker_hit"])
    # ⚠ r7 Claude M8: 74% is the one-sided 95% lower bound for n=10 SPECIFICALLY. `floor` is a
    # parameter, and at floor=3 the old wording asserted a bound of 74% where it is really ~37% —
    # a number a reader would act on, stated for a sample that cannot support it.
    bound = (f"at {floor}/{floor} the one-sided 95% accuracy bound reaches 74%, against a ~7% "
             f"coin" if floor == 10 else
             f"the 74% bound is pinned to a sample of 10, so it is NOT quoted for this floor "
             f"of {floor}")
    return (f"{len(sample)} ranker predictions ({hits} ranker hits) — re-evaluate now; {bound}")


# ------------------------------------------------------------------ IO
def read_log(path: Path = LOG) -> list[dict]:
    """Rows in file order. A malformed line RAISES — a log that cannot be read is not empty."""
    if not path.exists():
        return []
    # ⛔ r1 Codex M7, second half: a PermissionError on read escaped `main()`'s
    # `except ValueError` and terminated the CLI with a traceback and rc=1 — a process failure
    # dressed as a verdict. An unreadable log is CANNOT RUN, which is what ValueError becomes.
    try:
        text = path.read_text()
    except OSError as exc:
        raise ValueError(f"{path.name} could not be read: {exc}") from exc
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{i} is not JSON: {exc}") from exc
    return rows


def unit_key(row: dict) -> tuple:
    """PURE. The (subject, unit) a row is about — the partition every per-unit rule uses."""
    return (row.get("subject"), row.get("unit"))


def derive_routes_tried(prior: list[dict]) -> list[str]:
    """PURE. The routes already tried on ONE unit, DERIVED from that unit's earlier rows.

    ⛔⛔ THIS IS THE R1 BLOCKING REDESIGN, AND THE POINT IS THAT IT REMOVES A FIELD RATHER THAN
    GUARDING IT. `routes_tried` used to be AUTHORED. Measured in r1: five individually-valid
    rows retrying `accrete` on one unit — `routes_tried` never growing — exited 0 with
    `all triggers quiet`, because `validate_row` never related `route` to `routes_tried`,
    `t2_non_termination` read one row at a time, and no trigger grouped rows by (subject, unit).
    The termination guarantee lived entirely in `route_next`, which nothing outside the
    self-test called.

    ⭐ The r1 Claude half's sharpest finding was that the honest caveat about causation had been
    spent as cover for this: *"the unverifiability that is genuinely structural has been used to
    justify leaving verifiable fields unverified."* `routes_tried` is derivable from the log's
    own earlier rows. So it is derived, and a retry becomes INEXPRESSIBLE rather than refused —
    history says what was tried, and an author cannot say otherwise.

    Order is file order, which is the log's append-only guarantee.
    """
    return [r["route"] for r in prior if r.get("route")]


def routes_accounted(prior: list[dict]) -> list[str]:
    """PURE. Every rung the ladder has PASSED on ONE unit — routes taken AND declared skips.

    ⛔ THIS IS NOT `derive_routes_tried`, AND THE DIFFERENCE IS THE WHOLE POINT OF THE SKIP.
    A declared skip says a rung was NOT attempted, which is the counterfactual label the
    route-predictor needs ("accrete was judged futile on this shape and never tried"). Folding
    skips into `derive_routes_tried` would record them as failed attempts and destroy exactly
    that label. So there are two producers with two readers: the VALIDATOR asks where the
    ladder has got to (here), the TRIGGERS ask what was actually tried (there).

    Without this, a declared skip would be accepted and then make its own unit UNAPPENDABLE —
    the next row's history would read as a non-prefix and be refused — which is the same class
    of defect as the omission this change removes. A case covers it.

    A non-list `skipped` contributes nothing; `validate_row` is what refuses it, because a
    producer that also judges is a producer whose refusal nobody can read.
    """
    out: list[str] = []
    for r in prior:
        skipped = r.get("skipped")
        if isinstance(skipped, list):
            out.extend(str(s) for s in skipped)
        if r.get("route"):
            out.append(r["route"])
    return out


def component_rounds(rounds: list[dict]) -> dict[str, set[int]]:
    """PURE. component -> the SET of round numbers it appeared in.

    ⛔ r2 YL7: `derive_outcome` used `scope_tally`, which returns how MANY rounds a component
    appeared in — and compared that COUNT to a ROUND NUMBER. A component in rounds 1 and 5 has
    a count of 2, so "did it appear after round 4?" was answered `2 > 4` = no, i.e. "stopped",
    when round 5 proves the opposite. A count cannot answer a question about position.
    """
    out: dict[str, set[int]] = {}
    for r in rounds:
        n = r.get("round")
        if not isinstance(n, int):
            continue
        for c in {f.get("component") for f in r.get("findings", []) if f.get("component")}:
            out.setdefault(c, set()).add(n)
    return out


def derive_outcome(subject: str, unit: str, after_round: int,
                   seen: dict[str, set[int]] | None) -> str | None:
    """PURE. Did the stream stop for `unit` after `after_round`? None = NOT DERIVABLE.

    r1 Claude's closing argument: `outcome` is derivable from whether a LATER round named the
    same component. True, and the observation model took two attempts to get right — see
    `component_rounds` for why a count could not answer it.

    ⛔ IT IS DELIBERATELY NOT WIRED INTO `main()`, and r2 called that prudent in the same
    finding that showed the model was wrong: wiring it as written would have OVERWRITTEN an
    authored `continued` with an incorrect `stopped`. The order is model first, evidence that
    the model is right second, wiring third. Bounds that keep it unwired for now:

      * the subject's coordinator documents must be READABLE — measured, 10 of 81 subjects
      * `unit` must name a component the rounds know; an unknown unit is a naming mismatch,
        not evidence of a stopped stream
      * both make `None` the honest answer far more often than not, and a derivation that is
        usually unavailable must not silently become a default.
    """
    if not seen or unit not in seen:
        return None
    later = {n for n in seen[unit] if n > after_round}
    return "continued" if later else "stopped"


def validate_row(row: dict, prior: list[dict] | None = None) -> str | None:
    """PURE. Why a row is unusable, else None. `prior` is this unit's EARLIER rows.

    ⚠ `prior` defaults to None meaning "no history supplied", which validates the row's own
    shape only. `read_log`'s caller passes the real history; a caller that forgets gets the
    weaker check, so `main()` is the one place that must not forget — and a case covers it.
    """
    if not isinstance(row, dict):
        return f"a row is {type(row).__name__}, not an object"
    for key in ("subject", "unit", "route"):
        if key not in row:
            return f"missing {key!r}"
    if row["route"] not in LADDER:
        return f"route {row['route']!r} is not on the ladder {list(LADDER)}"
    if row.get("outcome") not in (None, *OUTCOMES):
        return f"outcome {row.get('outcome')!r} is not one of {(None, *OUTCOMES)}"
    if row.get("outcome") == "stopped" and not isinstance(row.get("rounds_at_termination"), int):
        return "a stopped row must record rounds_at_termination as an integer"
    # ⟳ r5: the same field now also CLOSES a unit (`closes_unit`), so where present it is held
    # to its meaning on every row — `bool` is an `int` subclass, and `True` is not one round.
    n_rounds = row.get("rounds_at_termination")
    if "rounds_at_termination" in row and (not isinstance(n_rounds, int)
                                           or isinstance(n_rounds, bool) or n_rounds < 1):
        return f"rounds_at_termination is {n_rounds!r} — it must be an integer >= 1"
    # Only the last rung can close a unit: a `continued` non-DEFER row has a next route to bet on.
    if (row.get("outcome") == "continued" and "rounds_at_termination" in row
            and row["route"] != LADDER[-1]):
        return (f"a continued {row['route']!r} row records rounds_at_termination, but only a "
                f"continued {LADDER[-1]!r} — the exhausted ladder — may close its unit")
    # ⛔ r1 Codex M5: `bool("false")` is True, so a STRING silently became a ranker hit and two
    # misses read as two hits. A field a trigger turns on is type-checked, not coerced.
    if "ranker_hit" in row and not isinstance(row["ranker_hit"], bool):
        return (f"ranker_hit is {type(row['ranker_hit']).__name__}, not a bool — a string "
                f"coerces to True and erases a miss")
    # ⛔ SAME COERCION TRAP, AND A WORSE CONSEQUENCE: `bool("false")` is True, so a STRING here
    # would quietly remove a real prospective bet from every scoring trigger's population.
    if "retroactive" in row and not isinstance(row["retroactive"], bool):
        return (f"retroactive is {type(row['retroactive']).__name__}, not a bool — a string "
                f"coerces to True and would drop a real bet from every scoring trigger")
    if prior is None:
        return None
    # ⟳ r5: a CLOSED unit cannot be reopened. Exhaustion would refuse the row anyway; this names
    # the reason a reader needs — the unit was closed on purpose, and a new attempt is a new unit.
    if prior and isinstance(prior[-1], dict) and closes_unit(prior[-1]):
        return (f"{unit_key(row)} is CLOSED — its continued DEFER recorded "
                f"rounds_at_termination, so no bet may follow it; a new attempt is a new unit")
    # ⛔⛔ H3 DOOR (c), WHICH IS IRREVERSIBLE IN AN APPEND-ONLY LOG. One authored boolean buys
    # three things: it satisfies t1's starvation check, it empties every scoring population, and
    # — if a unit is backfilled all the way to `defer` — it makes recording a real prospective
    # bet for that unit PERMANENTLY IMPOSSIBLE, because the ladder is terminal and every later
    # row is refused as a retry after exhaustion. Measured by r7 Claude on four backfilled rows.
    # The cheap bound that closes the general form: you may backfill a unit's PAST, never append
    # hindsight after a real bet. Both live rows satisfy it.
    # ⚠ TWO LINES, TWO DECISIONS: WHICH histories count as "after a real bet", and WHETHER that
    # is refused. One line would put both behind one anchor and the harness refuses the second as
    # measuring nothing new — so only one of them could ever be guarded.
    hindsight_after_bet = bool(row.get("retroactive")) and bool(prospective(prior))
    if hindsight_after_bet:
        return (f"a retroactive row may not follow a PROSPECTIVE bet on {unit_key(row)} — "
                f"hindsight appended after a real bet closes that unit's ladder and empties "
                f"its scoring population, and an append-only log cannot take it back")
    tried = derive_routes_tried(prior)
    # ⛔ THE LADDER POSITION IS `accounted`, THE ATTEMPTS ARE `tried`, AND THEY ARE NOT THE SAME
    # QUESTION once a skip is declarable. The prefix rule and the next route are about where the
    # ladder has got to; the messages say "tried" of real attempts only.
    accounted = routes_accounted(prior)
    err = route_sequence_error(accounted)
    if err:
        return f"this unit's history is not a ladder prefix: {err}"
    expected = route_next(accounted)
    if expected is None:
        return (f"the ladder is EXHAUSTED for {unit_key(row)} (tried {tried}) — there is no "
                f"route left to bet on, so this row is a retry after exhaustion")
    if row["route"] != expected:
        base = (f"route {row['route']!r} is not the next route for {unit_key(row)}: tried "
                f"{tried}, so the only route left to bet on is {expected!r}")
        # ⛔⛔ A RETRY IS NOT A SKIP, AND NO REASON LEGALISES ONE. `LADDER[:index('accrete')]`
        # is empty, so without this branch a repeat is declarable with `skipped: []` and any
        # sentence — and the design calls a repeat the escalation TRIGGER, not a step. This is
        # the door the new field would otherwise re-open for the r1 Blocking.
        if row["route"] in tried:
            return (f"{base} — and {row['route']!r} is ALREADY TRIED, so this is a RETRY, not a "
                    f"skip: a repeat is the escalation trigger, not a step, and no reason "
                    f"declares it into one")
        # A rung that was declared-skipped was never attempted, but the ladder has PASSED it.
        # Betting on it now is a walk-back, which is the backtracking §3.4 does not authorise.
        if row["route"] in accounted:
            return (f"{base} — and {row['route']!r} was already PASSED by a declared skip, so "
                    f"this is a WALK-BACK down the ladder, which escalation does not do")
        # The gap is the UNTRIED rungs before this route. It cannot be empty here: `expected` is
        # the first unaccounted rung and this route is neither it nor accounted, so the route
        # sits strictly above `expected` and `expected` itself is in the gap.
        gap = [r for r in LADDER[:LADDER.index(row["route"])] if r not in accounted]
        declared, why = row.get("skipped"), row.get("why_skipped")
        if declared is None and why is None:
            return (f"{base} — a deliberate skip is recordable: declare skipped {gap!r} with a "
                    f"non-empty why_skipped")
        if not isinstance(declared, list) or [str(x) for x in declared] != gap:
            return (f"skipped {declared!r} does not name the rungs this row skips: {gap!r} — "
                    f"the declaration must match the ladder gap, not assert one")
        # ⭐ AN EMPTY REASON IS REFUSED, exactly as `check-review-recorded.py` refuses an empty
        # `NO-REVIEW:`. The reason IS the deliverable here — a skip without one is an
        # unlabelled deviation, which is the thing the old schema was right to refuse.
        if not isinstance(why, str) or not why.strip():
            return (f"why_skipped is {why!r} — a declared skip needs a NON-EMPTY reason, the "
                    f"same refusal check-review-recorded makes of an empty NO-REVIEW:")
        # ⛔ NON-EMPTY IS NOT EXPLANATORY (r7 Codex). `"!!!"` passed, and so did a ZERO-WIDTH
        # SPACE — `str.strip()` does not remove U+200B, so the whitespace rule could never have
        # reached it. The reason IS the deliverable of this schema change, so it must carry at
        # least some content. ⚠ This tests for CONTENT, not meaning: no check here can establish
        # that a reason is true or useful, and claiming otherwise would be the stronger lie.
        if not any(ch.isalnum() for ch in why):
            return (f"why_skipped {why!r} has no alphanumeric content — non-empty is not the "
                    f"same as explanatory, and strip() does not remove a zero-width space")
    elif "skipped" in row or "why_skipped" in row:
        # A skip CLAIMED where none happened is a false label in the dataset the skips exist to
        # build, so it is refused rather than ignored as harmless surplus.
        return (f"skipped {row.get('skipped')!r} / why_skipped claim a skip, but "
                f"{row['route']!r} IS the next route for {unit_key(row)} — nothing was skipped")
    # An AUTHORED routes_tried may not contradict the derived one. It is redundant now, and a
    # redundant field that disagrees with history is how the r1 Blocking was expressible.
    # ⚠ r7 Codex M4: `list(None)` / `list(7)` raised TypeError straight out of the validator, so
    # malformed log data escaped the unusable-row diagnostic as a crash. A type is named, never
    # coerced — the same posture as `ranker_hit` two checks above.
    # ⚠ r7 Claude L12: admitting `str` made the message untrue — `list("") == []`, so
    # `routes_tried: ""` validated as "no routes tried" while the refusal says "not a list".
    if "routes_tried" in row and not isinstance(row["routes_tried"], (list, tuple)):
        return (f"routes_tried is {type(row['routes_tried']).__name__}, not a list — it is "
                f"DERIVED now and need not be written")
    if "routes_tried" in row and list(row["routes_tried"]) != tried:
        return (f"routes_tried {row['routes_tried']!r} contradicts this unit's history {tried!r} "
                f"— the field is DERIVED now and need not be written at all")
    return None


def invalid_rows(rows: list) -> list[tuple[int, str]]:
    """PURE. (1-based row number, why) for every row that fails against ITS UNIT'S earlier rows.

    ⟳ r1 F3: extracted from `main()` so the self-test can hold every log it builds to the SAME
    validation the CLI applies — two cases had passed over a log `main()` would refuse, and a
    copy of this loop in the suite would be a second implementation of it.
    """
    bad = []
    seen: dict[tuple, list[dict]] = {}
    for i, r in enumerate(rows, 1):
        prior = seen.get(unit_key(r), []) if isinstance(r, dict) else []
        why = validate_row(r, prior)
        if why:
            bad.append((i, why))
        elif isinstance(r, dict):
            seen.setdefault(unit_key(r), []).append(r)
    return bad


def group_by_unit(rows: list[dict]) -> dict[tuple, list[dict]]:
    """PURE. (subject, unit) -> its rows in file order.

    ⛔ r1 Claude B3: NO trigger grouped rows this way, so the old route-collapse trigger was
    defeated by a single second unit on another route and a per-unit conveyor was invisible.
    ⟳ 2026-10-23: that trigger is gone; `lost_bets` reads this grouping for trigger 3 now.
    """
    out: dict[tuple, list[dict]] = {}
    for r in rows:
        out.setdefault(unit_key(r), []).append(r)
    return out


def _round_docs(reviews: Path | None = None) -> dict[str, dict[int, set[str]]]:
    """subject -> {round: ALL paths for that round}. A PROJECTION of `check-review-rounds.corpus`.

    ⟳ 2026-10-20, backlog #328. This used to carry its OWN `rglob` walk — the second copy of a
    rule this module already had, and the copies had DRIFTED. r2's finding YH1 gave `_corpus_now`
    an `os.walk(onerror=...)` completeness check because `Path.rglob` silently skips a directory
    it cannot read; this copy never got it. Measured over one temp tree with two 2-round subjects
    and one subtree at `chmod 000`: `_corpus_now` refused, and this function returned ONE subject
    of two **with no error**, feeding `subjects_starved` and therefore trigger 1 — the starvation
    ratchet going quiet about a subject it could not see, which is how its predecessor died at 81%.

    The walk now lives once, in the module that owns the filename grammar. A refusal becomes
    `ValueError`, which `main()` already treats as CANNOT RUN — `read_log` set that convention.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_crr", REPO / "scripts" / "check-review-rounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows, why = mod.corpus(reviews)
    if why:
        raise ValueError(why)
    seen: dict[str, dict[int, set[str]]] = {}
    for subject, number, _writer, path in rows:
        rel = str(Path(path).relative_to(REPO)) if Path(path).is_relative_to(REPO) else str(path)
        seen.setdefault(subject, {}).setdefault(number, set()).add(rel)
    return seen

def parse_armed_at(raw: object) -> "tuple[int | None, str | None]":
    """PURE-ish. (epoch seconds, None) or (None, why it is unusable).

    ⛔ r1 Claude H1 — THIS WAS THE LOUDEST TRIGGER'S SILENT OFF-SWITCH. The old code passed
    `armed_at` straight to `git log --since=<raw>`, and git's approxidate NEVER REFUSES:
    measured on this repository, `--since=2026-10-20` returned **0** commits while
    `--since=2026-10-19` returned **30**, both rc=0. And `baseline.json` already mixes formats —
    `"derived_at": "2026-10-20"` sits two lines above `armed_at` — so a maintainer re-arming the
    ratchet copies the neighbouring style, gets an empty set, and trigger 1 goes permanently
    quiet while the run reports `all triggers quiet`.

    So the field is parsed here with `fromisoformat` and handed to git as `@<epoch>`, which has
    no interpretation. A value that does not parse is CANNOT RUN, never an empty set.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None, f"armed_at is {type(raw).__name__ if raw is not None else 'absent'}"
    import datetime as _dt
    try:
        when = _dt.datetime.fromisoformat(raw.strip())
    except ValueError as exc:
        return None, (f"armed_at {raw!r} is not an ISO-8601 instant ({exc}). git's approxidate "
                      f"would accept it silently and match nothing — give it a full instant "
                      f"such as 2026-10-20T10:00:00-07:00")
    if when.tzinfo is None:
        return None, (f"armed_at {raw!r} has no timezone, so the window it opens depends on the "
                      f"machine reading it")
    return int(when.timestamp()), None


def round_shapes():
    """The filename grammar, imported from `check-review-rounds.py`. One rule, one place."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_crr", REPO / "scripts" / "check-review-rounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SHAPES


def rounds_in_paths(paths, shapes=None) -> "set[tuple[str, int]]":
    """PURE. The (subject, round) pairs a set of paths represents.

    ⭐⭐ THIS IS THE r2 REDESIGN, AND THE CHANGE OF IDENTITY IS THE WHOLE REPAIR. The previous
    rule asked whether a round's PATH was in the historical tree, and r2 found three doors into
    the same room, all of them the same cause — **a path is not a stable identity**:

      * YH2 a document MOVED since arming (flat -> `codex/`) matches nothing in `before`, so an
        entirely historical subject is named as newly starved — backlog #56's death.
      * YM3 `git ls-tree --name-only` honours `core.quotePath`, so `é` comes back as
        `\303\251` and an unchanged subject is named.
      * YM6 nothing asserted the tree being listed was the HISTORICAL one; substituting `HEAD`
        left 113/113 green.

    A `(subject, round)` pair survives a move, survives quoting once the bytes are read
    correctly, and is exactly the identity the procedure already reasons in. Only the directory
    changes under a move; the basename grammar does not.
    """
    shapes = round_shapes() if shapes is None else shapes
    out = set()
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        for pat in shapes:
            m = pat.match(name)
            if m:
                out.add((m.group("subject"), int(m.group("round"))))
                break
    return out


def shallow_refusal(flag: str) -> str | None:
    """PURE. Why a shallow clone cannot answer "what did the tree hold at arming", else None.

    ⛔ EXTRACTED BECAUSE THE BRANCH WAS UNKILLABLE IN PLACE. `if shallow == "true"` can only
    behave differently on a shallow clone, so mutating it was an EQUIVALENT mutation on any
    normal checkout — it survived with rc=0, which looks identical to a coverage gap.

    r1 Claude M6: a shallow clone has no history before arming, so every tracked round document
    looks new and the ratchet would name the entire corpus.
    """
    if flag.strip() == "true":
        return ("this is a SHALLOW clone, so history before arming is absent and every tracked "
                "round document would look new (r1 Claude M6)")
    return None


def empty_listing_refusal(paths: set, sha: str) -> str | None:
    """PURE. Why an EMPTY tree listing is git not having been read, not a real answer.

    ⛔ EXTRACTED FOR THE SAME REASON AS `shallow_refusal`, and r2 made the point twice: in place
    (`if not paths:`) this branch can only behave differently on an input a real repository never
    produces, so mutating it survived with rc=0 — indistinguishable from a coverage gap. A rule
    that cannot be driven is not covered, however correct it looks.

    A commit with no paths at all cannot be true; reading it as "the tree held nothing" would
    make every subject look post-arming, which is backlog #56's death by a different door.
    """
    if not paths:
        return (f"the tree at {sha[:8]} lists no paths at all, which cannot be true of a commit "
                f"— treat this as git not having been read")
    return None


def tree_at(epoch: int, repo: Path | None = None,
            ) -> "tuple[set[str] | None, str | None]":
    """(paths that existed at `epoch`, None) or (None, why this cannot be answered).

    ⭐ A LISTING, NOT A DIFF. The first version asked which paths were ADDED since arming
    (`--diff-filter=A`), which r1 showed has three doors: a relocated short document is an `A`
    not an `R`; `--since` filters on COMMITTER date so a rebase re-dates an old add into the
    window; and a shallow clone makes everything look added. Asking what the tree HELD removes
    all three — there is no add/rename classification to get wrong.

    ⟳ r2 YM3: the output is read with `-z`, NUL-delimited and UNQUOTED. `--name-only` alone
    honours `core.quotePath`, so a path containing `é` came back as `\303\251` and matched
    nothing — naming an unchanged subject as new.
    """
    import subprocess
    # ⛔⛔ THE SUBJECT IS A PARAMETER BECAUSE ITS ABSENCE MADE THE WHOLE FILE UNMEASURABLE
    # (backlog #322). `REPO` is `Path(__file__).resolve().parent.parent`, so inside the mutation
    # harness's staged copy it resolves to a temp directory with no `.git` — every git call here
    # failed, the three cases driving this went red, `control_is_green` was False, and
    # `mutate_delivered` returned NotMeasured for ALL 1,623 mutations across all 8 shards.
    # ⭐ Every other world-taker in this file already took its subject as a defaulted parameter
    # (ADR-0014): `main`, `_corpus_now`, `_round_docs`, `subjects_starved`. This one executes a
    # subprocess and was the one left reaching for whatever filesystem it sat in. One member
    # anchoring the file is the composition defect the Phase 6 review names.
    repo = REPO if repo is None else repo
    try:
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=repo,
                                 capture_output=True, text=True, check=True).stdout.strip()
        refusal = shallow_refusal(shallow)
        if refusal:
            return None, refusal
        sha = subprocess.run(["git", "rev-list", "-1", f"--before=@{epoch}", "HEAD"], cwd=repo,
                             capture_output=True, text=True, check=True).stdout.strip()
        if not sha:
            return None, (f"no commit exists at or before the arming instant (@{epoch}), so "
                          f"'what the tree held at arming' has no answer")
        # ⛔ MEASURED, AND I HAD ASSUMED OTHERWISE: `git rev-list -1 --before=@1 HEAD` returns
        # the repository's FIRST commit, not nothing. An ISO-parseable but absurd instant would
        # resolve to a tiny tree, nearly every subject would look post-arming, and trigger 1
        # would name almost all of them — red from birth, backlog #56.
        when = subprocess.run(["git", "show", "-s", "--format=%ct", sha], cwd=repo,
                              capture_output=True, text=True, check=True).stdout.strip()
        if not when.isdigit() or int(when) > epoch:
            return None, (f"the newest commit at or before @{epoch} is {sha[:8]}, dated "
                          f"{when or 'unreadable'} — git resolved outside the window, so the "
                          f"arming instant predates this history and the tree at arming is "
                          f"not knowable")
        # ⟳ r2 YM3: `-z` so paths arrive as raw bytes between NULs, never quoted.
        out = subprocess.run(["git", "ls-tree", "-r", "-z", "--name-only", sha], cwd=repo,
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        return None, f"git could not be read: {exc}"
    paths = {part for part in out.split("\0") if part}
    refusal = empty_listing_refusal(paths, sha)
    if refusal:
        return None, refusal
    return paths, None


def pinned_inventory(baseline: object) -> "tuple[set[tuple[str, int]] | None, str | None]":
    """PURE. The (subject, round) inventory pinned at arming, or (None, why not usable).

    ⛔⛔ THIS EXISTS BECAUSE A SQUASH MERGE DESTROYS THE ANSWER `tree_at` DERIVES (backlog #341).
    Every file a squash carries enters the target branch's history AT THE SQUASH COMMIT'S DATE, so
    documents that existed before arming look newer than it. MEASURED 2026-10-22:
    `docs/reviews/claude/memory-index-budget-r1-claude.md` was added by `49b7b267` (2026-10-19) on
    the pre-merge branch and by `ee0e461b` (2026-10-21) on master — and trigger 1 then named
    `memory-index-budget` as newly starved when its rounds 1, 2 AND 3 all predate arming.

    ⭐ NO BETTER DATE SOURCE FIXES IT, which is why this is a pin and not a re-derivation. The
    information is DESTROYED, not mis-stamped: master's history genuinely has no commit in which
    those files existed before the squash. Verdict JSONs carry a `head` SHA but no timestamp, and
    the review documents carry no date in their heads — both were checked before choosing this.

    This is the posture `rounds_to_termination` already takes two fields above, for the same
    stated reason: *"a baseline recomputed at read time cannot detect that it has moved."*

    A missing key is (None, None) — ABSENT, so the caller may fall back to `tree_at`; a key of the
    wrong SHAPE is a refusal, because a malformed pin that read as empty would make every subject
    look post-arming and name almost all of them (backlog #56, red from birth).
    """
    if not isinstance(baseline, dict):
        return None, f"the pinned baseline is {type(baseline).__name__}, not an object"
    raw = baseline.get("rounds_at_arming")
    if raw is None:
        return None, None
    if not isinstance(raw, list):
        return None, (f"rounds_at_arming is {type(raw).__name__}, not a list of "
                      f"[subject, round] pairs")
    out = set()
    for item in raw:
        if (not isinstance(item, (list, tuple)) or len(item) != 2
                or not isinstance(item[0], str) or not isinstance(item[1], int)
                or isinstance(item[1], bool)):
            return None, (f"rounds_at_arming holds {item!r}, which is not a "
                          f"[subject, round] pair of (str, int)")
        out.add((item[0], item[1]))
    if not out:
        return None, ("rounds_at_arming is EMPTY — an empty inventory makes every subject look "
                      "post-arming, so it is refused rather than read as 'nothing existed'")
    return out, None


def pinned_lost_bets(baseline: object) -> "tuple[frozenset | None, str | None]":
    """PURE. The CLOSED set of (subject, unit, route) lost bets that predate trigger 3, or (None, why).

    ⛔ PINNED, LIKE `rounds_at_arming`, AND FOR THE SAME REASON: it is history, and a list a
    script could grow at run time would be an exemption anyone could write. It lives in
    `baseline.json` beside the other pins, each entry with a written `reason`; nothing in this
    file adds to it, and a case pins the shipped list to its two entries.

    ⟳ r4 Codex Major: each pin names ONE BET — (subject, unit, route), unique because
    `route_next` never lets a unit repeat a route — so a later loss on a pinned unit is not
    excused. A pin without a ladder `route` is refused.

    ⟳ r4 Codex Low: only an ABSENT key is the empty set — a repository with no pre-trigger
    history. A PRESENT key must be a list; `null` is a wrong shape, never an empty list. A key of
    the wrong shape is a refusal, never an empty set and never a partial one.
    """
    if not isinstance(baseline, dict):
        return None, f"the pinned baseline is {type(baseline).__name__}, not an object"
    if PRE_TRIGGER_PINS not in baseline:
        return frozenset(), None
    raw = baseline[PRE_TRIGGER_PINS]
    if not isinstance(raw, list):
        return None, (f"{PRE_TRIGGER_PINS} is {type(raw).__name__}, not a list — a PRESENT key "
                      f"must be a list; only an absent key means no pins")
    out = set()
    for item in raw:
        if (not isinstance(item, dict) or not isinstance(item.get("subject"), str)
                or not isinstance(item.get("unit"), str)):
            return None, (f"{PRE_TRIGGER_PINS} holds {item!r}, not a "
                          f"{{subject, unit, route, reason}}")
        why = item.get("reason")
        if not isinstance(why, str) or not any(ch.isalnum() for ch in why):
            return None, (f"the pin on {item['subject']}/{item['unit']} has no reason — an "
                          f"exemption from trigger 3 must say why it is history")
        if item.get("route") not in LADDER:
            return None, (f"the pin on {item['subject']}/{item['unit']} names route "
                          f"{item.get('route')!r}, not one of {list(LADDER)} — a pin names ONE "
                          f"bet, and a bet is (subject, unit, route)")
        key = (item["subject"], item["unit"], item["route"])
        if key in out:
            return None, f"{item['subject']}/{item['unit']} is pinned twice"
        out.add(key)
    return frozenset(out), None


def subjects_starved(armed: object, docs: dict | None = None,
                     before_rounds: "set[tuple[str, int]] | None" = None,
                     repo: Path | None = None) -> "tuple[list[str], str | None]":
    """(subjects that came into scope AFTER arming, None) | ([], why this cannot be answered).

    ⭐ THE RULE IS A SET DIFFERENCE OVER (subject, round) MEMBERSHIP:

        a subject is newly in scope  iff  rounds it had BEFORE arming < 2 <= rounds it has NOW

    ⟳ r2 YH2: `before` used to be a set of PATHS and this intersected filenames, so a document
    moved since arming counted as absent and an entirely historical subject was named. It is now
    a set of `(subject, round)` pairs, derived from the historical tree through the SAME
    filename grammar the live corpus is read with — so a move changes the directory and not the
    identity.

    ⛔ IT RETURNS A REASON, NOT AN EMPTY LIST, WHEN IT CANNOT ANSWER. Silence is
    indistinguishable from "nothing is starved", which is how the predecessor died.
    """
    if armed is None:
        return [], None
    epoch, why = parse_armed_at(armed)
    if why:
        return [], why
    docs = _round_docs() if docs is None else docs
    if before_rounds is None:
        paths, why = tree_at(epoch, repo)
        if why:
            return [], why
        before_rounds = rounds_in_paths(paths)
    out = []
    for subject, rounds in docs.items():
        if len(rounds) < 2:
            continue
        rounds_before = sum(1 for n in rounds if (subject, n) in before_rounds)
        if rounds_before < 2:
            out.append(subject)
    return sorted(out), None


def main(argv: list[str], *, baseline_path: Path | None = None,
         log_path: Path | None = None, corpus=None, starved=None) -> int:
    """⛔ ITS WORLD IS A SET OF DEFAULTED PARAMETERS, per ADR-0014, so a case can DRIVE it.

    The alternative was `MAIN_DEBT`, and taking it would have left the part that decides
    FAIL-vs-WARN and the exit code untested while every pure predicate underneath it was
    covered — the gap `check-main-drivable.py` exists to refuse. The assembly is where a
    warning silently becoming a failure would hide.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--rederive", action="store_true",
                    help="recompute the corpus figures and report drift from baseline.json")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()

    baseline_path = BASELINE if baseline_path is None else baseline_path
    corpus = _corpus_now if corpus is None else corpus
    starved = subjects_starved if starved is None else starved
    if not baseline_path.exists():
        print(f"CANNOT RUN — the pinned baseline is missing: {baseline_path}")
        return 2
    try:
        pinned = json.loads(baseline_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"CANNOT RUN — the pinned baseline is unreadable: {exc}")
        return 2
    pinned_rounds = pinned.get("rounds_to_termination", {})
    # ⛔ r1 Claude M3: trigger 4 read `pinned_rounds.get("median", 4)`, so a baseline that does
    # NOT contain a median still produced the sentence "against a pinned pre-scheme median of 4"
    # — attributing a figure to a file that never held it. A comparator that defaults is not
    # pinned; it is a literal wearing a baseline's name.
    if not isinstance(pinned_rounds.get("median"), (int, float)):
        print(f"CANNOT RUN — {baseline_path.name} holds no numeric "
              f"rounds_to_termination.median, so trigger 4 has no comparator. A default would "
              f"attribute a figure to a baseline that does not contain it.")
        return 2

    now = corpus()
    # ⛔ r1 BOTH HALVES (Claude B2, Codex H3): a corpus that could not be read printed
    # `now=None` and then the POSITIVE assertion `all triggers quiet`, rc=0 — a claim that all
    # seven triggers were evaluated when trigger 6 was not evaluated at all. The handler's own
    # comment asserted this was "NOT a fail-open" and that comment was FALSE, which is worse
    # than no comment. The error is now CANNOT RUN on the DEFAULT path, which is the one CI runs.
    if now.get("error") and not args.rederive:
        print(f"CANNOT RUN — the review corpus could not be read: {now['error']}")
        print("    Trigger 6 compares today's corpus against the pinned baseline and there is")
        print("    no 'today' to compare. Treat this as NOT CHECKED, not as quiet.")
        return 2
    if args.rederive:
        print("pinned vs now, for trigger 6:")
        for k in ("median", "mean"):
            print(f"    rounds/subject {k:7s} pinned={pinned_rounds.get(k)}  now={now.get(k)}")
        print(f"    subjects (>=2 rounds) pinned="
              f"{pinned.get('corpus', {}).get('subjects_with_ge2_rounds')}  "
              f"now={now.get('subjects')}")
        if now.get("error"):
            print(f"    CANNOT RUN — the corpus could not be read: {now['error']}")
            return 2
        drift = t6_denominator_moved(now, pinned_rounds,
                                     now_corpus=now, pinned_corpus=pinned.get("corpus", {}))
        print(f"    {'DRIFT: ' + drift if drift else 'no material drift'}")
        return 0

    try:
        rows = read_log(LOG if log_path is None else log_path)
    except ValueError as exc:
        print(f"CANNOT RUN — {exc}")
        return 2

    # ⛔ r1 Claude B3: each row is validated against ITS UNIT'S EARLIER ROWS, not alone. A row
    # validated in isolation cannot be seen to retry a route, which is how the Blocking was
    # expressible. `main()` is the one caller that must not forget `prior`; a case covers that.
    bad = invalid_rows(rows)
    if bad:
        print("CANNOT RUN — the log holds unusable rows, so no trigger was evaluated:")
        for i, why in bad[:5]:
            print(f"    row {i}: {why}")
        return 2

    armed = pinned.get("armed_at")
    if not rows and not armed:
        print("NOT YET FED — 0 log rows and no arming date; the scheme has not started.")
        print("    This is the one state in which silence is honest. Trigger 1 begins firing")
        print("    once baseline.json carries `armed_at`.")
        return 0

    # ⛔ A REASON FROM THE RATCHET IS CANNOT RUN, NOT AN EMPTY LIST. Silence here is
    # indistinguishable from "nothing is starved", which is precisely how the predecessor died.
    # ⛔ THE PINNED INVENTORY IS PREFERRED OVER GIT ARCHAEOLOGY (backlog #341). `tree_at` remains
    # the fallback for a repository that has not pinned one; a squash makes its answer wrong, not
    # merely unavailable, so where a pin exists it wins.
    before_rounds, pin_why = pinned_inventory(pinned)
    if pin_why:
        print(f"CANNOT RUN — the pinned round inventory is unusable: {pin_why}")
        print("    Trigger 1 is the loudest one and it was NOT CHECKED. Treat this as not run.")
        return 2
    starved_subjects, starve_why = starved(armed, before_rounds=before_rounds)
    if starve_why:
        print(f"CANNOT RUN — the starvation ratchet could not be evaluated: {starve_why}")
        print("    Trigger 1 is the loudest one and it was NOT CHECKED. Treat this as not run.")
        return 2
    # ⛔ THE PRE-TRIGGER PINS ARE HISTORY, READ LIKE `rounds_at_arming`: a malformed list is
    # CANNOT RUN, because a pin that read as empty would turn history into FAILs and one that
    # read as everything would exempt every lost bet.
    pins, pins_why = pinned_lost_bets(pinned)
    if pins_why:
        print(f"CANNOT RUN — the pinned pre-trigger lost bets are unusable: {pins_why}")
        print("    Trigger 3 cannot tell history from a new lost bet. Treat this as not run.")
        return 2
    fails, warns = [], []
    for name, result in (
        ("1 NOT FED", t1_not_fed(rows, starved_subjects)),
        ("2 NON-TERMINATION", t2_non_termination(rows)),
        ("3 LOST BET NOT ESCALATED", t3_lost_bet_not_escalated(rows, pins)),
        ("5 RANKER MISS", t5_ranker_miss(rows)),
    ):
        if result:
            fails.append((name, result))
    # ⛔ TRIGGER 4 IS SUSPENDED TO A WARN — the OWNER'S ruling, 2026-10-25, option A of a card,
    # not a patch to make a red go away. Its FIRST evaluation ever (PR #397, the fifth prospective
    # termination: [4, 7, 4, 5, 4]) said exactly what it exists to say, and the re-evaluation it
    # demands is now backlog #327 (keep, simplify or retire the scheme). Blocking every unrelated
    # PR while that is decided is not what the trigger is for. ⚠ WHEN #327 RULES, THIS SUSPENSION
    # ENDS — trigger 4 goes back on the FAIL list above, is rewritten, or is retired with the scheme.
    # ⛔ NOTHING ENFORCES THAT (r1 Claude M1, r1 Codex): no check reads #327's status, and closing it
    # turns nothing red. It is a MANUAL follow-up; the suffix only keeps it visible on every run.
    t4 = t4_no_improvement(rows, pinned_rounds["median"])
    for name, result in (
        ("4 NO IMPROVEMENT", t4 and (t4 + T4_SUSPENDED)),
        ("6 DENOMINATOR MOVED", t6_denominator_moved(
            now, pinned_rounds, now_corpus=now, pinned_corpus=pinned.get("corpus", {}))),
        ("7 SAMPLE REACHED", t7_sample_reached(rows)),
        ("8 HINDSIGHT ONLY", t8_hindsight_only(rows, starved_subjects)),
        ("9 DEFERRAL COMPOSED", t9_deferral_composed(rows, pinned_rounds["median"])),
        ("10 PRE-TRIGGER LOST BET", t10_pre_trigger_lost_bet(rows, pins)),
        ("11 LADDER EXHAUSTED, CLOSED", t11_ladder_exhausted_closed(rows)),
        ("12 LADDER RESTARTED", t12_ladder_restarted(rows)),
    ):
        if result:
            warns.append((name, result))

    # ⛔ THE ONE NUMBER A READER ACTUALLY SEES, AND IT WAS THE UN-SPLIT ONE (r7 Claude M7).
    # This line said "4 scored" while every scoring trigger computed over 2 — the same
    # substitution Codex H1/M2 found inside t3 and t7, left behind in `main()`. It matters more
    # than a cosmetic because the provenance split is now what a reader needs in order to
    # interpret `all triggers quiet` at all.
    scored = [r for r in rows if r.get("outcome") in OUTCOMES]
    scoreable = [r for r in prospective(rows) if r.get("outcome") in OUTCOMES]
    retro = len(rows) - len(prospective(rows))
    print(f"decision-scheme: {len(rows)} row(s), {len(scored)} scored "
          f"({retro} retroactive, so {len(scoreable)} scoreable); "
          f"pinned median {pinned_rounds.get('median')} vs now {now.get('median')}")
    for name, why in warns:
        print(f"  WARN  trigger {name}: {why}")
    for name, why in fails:
        print(f"  FAIL  trigger {name}: {why}")
    if fails:
        print("\nRE-EVALUATE THE MECHANISM. A failing trigger is not a bug to patch; it is the")
        print("promise saying the scheme no longer earns its place.")
        return 1
    if not warns:
        print("  all triggers quiet")
    return 0


def _corpus_now(reviews: Path | None = None) -> dict:
    """Today's corpus figures, for trigger 6. Derived, never recalled.

    ⟳ 2026-10-20, backlog #328: the walk MOVED to `check-review-rounds.corpus`, the module that
    owns the filename grammar, because this file carried TWO copies of it and they had drifted —
    this one had r2 YH1's completeness check and `_round_docs` did not. The refusal text and the
    `error` contract are unchanged; only the duplication is gone.
    """
    counts = []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_crr2", REPO / "scripts" / "check-review-rounds.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows, why = mod.corpus(reviews)
        if why:
            raise OSError(why)
        by_subject = mod.by_subject_rounds(rows)
        counts = [len(r) for r in by_subject.values() if len(r) >= 2]
        # ⛔ EMITTED UNDER THE NAMES `baseline.json` PINS, not under new ones. Trigger 6 compares
        # these to the pinned `corpus` block, and a key that does not match is skipped SILENTLY —
        # measured 2026-10-20, the first wiring of that comparison was inert for exactly this
        # reason and the cases did not catch it, because a fixture built with the right key names
        # proves what the function does to the FIXTURE, not what the caller hands it.
        extra = {"rounds_total": sum(len(r) for r in by_subject.values()),
                 "subjects_with_any_round": len(by_subject),
                 "subjects_with_ge2_rounds": len(counts)}
    except (OSError, AttributeError, ImportError) as exc:
        # ⟳ THE COMMENT THAT WAS HERE WAS FALSE AND IS DELETED RATHER THAN REWORDED. It said
        # "⛔ NOT a fail-open: the caller prints these as None and trigger 6 is skipped, which is
        # visible in the output line." Both r1 halves refuted it by running it: the default path
        # — the one CI runs — printed `now=None` and then the POSITIVE assertion `all triggers
        # quiet`, rc=0. The `error` key was read on exactly one path, `--rederive`.
        # ⚠ A caveat headed "NOT a fail-open" that is false is worse than no caveat, because it
        # is the first thing a reader of the handler believes is impossible.
        # WHAT IS TRUE NOW: `main()` treats a non-empty `error` as CANNOT RUN (rc=2) on BOTH
        # paths, and a case plus a mutation entry cover each.
        return {"median": None, "mean": None, "error": str(exc)}
    if not counts:
        return {"median": None, "mean": None, "error": "no subject has >=2 rounds"}
    return {"median": st.median(counts), "mean": round(st.mean(counts), 2),
            "subjects": len(counts), **extra}


def _try(fn):
    """The value, or a NAMED marker if it raised.

    ⛔ A case that raises kills the suite and reports NOTHING — the runner counts `[FAIL]` lines
    and a traceback produces none. `check-review-decision.py` carries the same helper and its
    docstring records the same miss. MEASURED HERE 2026-10-20: without it, two of this file's
    own mutations ("a non-object row raises out of the validator", "rows are grouped by SUBJECT
    only") came back `rc=1` with ZERO `[FAIL]` lines — killed by traceback, attributable to
    nothing. A crash names nothing, and `check-plan-code`'s contract is red VIA THE NAMED CASE.
    """
    try:
        return fn()
    except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
        return f"RAISED {type(exc).__name__}"


def _self_test() -> int:
    import os as _os
    import tempfile as _tf
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    # ── the ladder ───────────────────────────────────────────────────────────────────────────
    case("an untried unit starts at the CHEAPEST route", route_next([]), "accrete")
    case("a failed accretion escalates to redesign", route_next(["accrete"]), "redesign")
    case("a failed redesign escalates to split", route_next(["accrete", "redesign"]), "split")
    case("a failed split escalates to defer",
         route_next(["accrete", "redesign", "split"]), "defer")
    case("an exhausted ladder returns None rather than looping",
         route_next(["accrete", "redesign", "split", "defer"]), None)
    # ⛔ THE OWNER'S REQUIREMENT, as a case: OTHER choices, never the same one again.
    case("a repeated route is SKIPPED, not honoured — a retry is the trigger, not a step",
         route_next(["accrete", "accrete"]), "redesign")
    case("the ladder order is the design, and reversing the input does not reverse it",
         route_next(["split"]), "accrete")

    case("an empty history is not a sequence error", route_sequence_error([]), None)
    case("a ladder prefix is well-formed",
         route_sequence_error(["accrete", "redesign"]), None)
    case("a skipped route is NAMED, not silently read as one step",
         route_sequence_error(["split"]),
         "routes out of ladder order: got ['split'], a prefix would be ['accrete']")
    case("a retried route is refused by the validator too",
         route_sequence_error(["accrete", "accrete"]),
         "route(s) ['accrete'] retried — a repeat is the escalation trigger, not a step")
    case("an unknown route is refused rather than ignored",
         route_sequence_error(["rewrite"]),
         "unknown route(s) ['rewrite']; the ladder is ['accrete', 'redesign', 'split', 'defer']")

    # ── trigger 1: starvation, the loudest one ───────────────────────────────────────────────
    case("no subjects means nothing is starved", t1_not_fed([], []), None)
    case("a logged subject is fed",
         t1_not_fed([{"subject": "a"}], ["a"]), None)
    _t1 = t1_not_fed([{"subject": "a"}], ["a", "b", "c"])
    case("unlogged subjects are NAMED and counted", (_t1 or "").split(":")[0],
         "2 subject(s) reached >=2 rounds with no log row")
    case("...and the message says WHY it matters, because 81% is the whole reason",
         "81%" in (_t1 or ""), True)

    # ── the ratchet: (subject, round) membership before arming ───────────────────────────────
    # ⛔ REDESIGNED TWICE, AND THE SECOND TIME IS THE IDENTITY. r1 broke "which path ARRIVED";
    # r2 broke "which path EXISTED" through three doors that are one cause — a path is not a
    # stable identity. It moves, git quotes it, and the listed tree was unverified. A
    # (subject, round) pair survives all three.
    _ARM = "2026-10-20T10:00:00-07:00"
    _D = {"old": {1: {"docs/reviews/coordinator/old-r1-coordinator.md"},
                  2: {"docs/reviews/coordinator/old-r2-coordinator.md"}},
          "new": {1: {"docs/reviews/coordinator/new-r1-coordinator.md"},
                  2: {"docs/reviews/coordinator/new-r2-coordinator.md"}},
          "one": {1: {"docs/reviews/coordinator/one-r1-coordinator.md"}}}
    case("HISTORY IS NOT STARVED — a subject whose rounds BOTH predate arming is out of scope",
         subjects_starved(_ARM, {"old": _D["old"]}, {("old", 1), ("old", 2)}), ([], None))
    case("a subject whose rounds BOTH postdate arming is named",
         subjects_starved(_ARM, {"new": _D["new"]}, set()), (["new"], None))
    case("a subject that had ONE round before arming and two now has crossed into scope",
         subjects_starved(_ARM, {"new": _D["new"]}, {("new", 1)}), (["new"], None))

    # ── the PINNED inventory (backlog #341) ──────────────────────────────────────────────────
    # ⛔⛔ A SQUASH MERGE DESTROYS WHAT `tree_at` DERIVES. Every file a squash carries enters the
    # target branch's history at the SQUASH COMMIT'S date, so documents that predate arming look
    # newer than it and trigger 1 names historical subjects. Measured on this repository the day
    # it happened: `memory-index-budget`'s rounds 1-3 all predate arming and it was named anyway.
    case("⭐ a pinned inventory is read as (subject, round) pairs",
         pinned_inventory({"rounds_at_arming": [["a", 1], ["a", 2]]}),
         ({("a", 1), ("a", 2)}, None))
    case("an ABSENT pin is absent, not an error — the caller may still fall back to git",
         pinned_inventory({}), (None, None))
    # ⛔ THE DISCRIMINATING REFUSAL: an EMPTY pin would make every subject look post-arming and
    # name almost all of them. Red from birth, backlog #56 — so it is refused, not read as zero.
    case("⛔ an EMPTY pin is REFUSED, because empty would name nearly every subject",
         "EMPTY" in (pinned_inventory({"rounds_at_arming": []})[1] or ""), True)
    case("a pin of the wrong SHAPE is refused rather than coerced",
         "not a list" in (pinned_inventory({"rounds_at_arming": "a,1"})[1] or ""), True)
    case("...and a malformed PAIR inside it is named by its own repr",
         "is not a [subject, round] pair" in
         (pinned_inventory({"rounds_at_arming": [["a", 1], ["b"]]})[1] or ""), True)
    # ⚠ `bool` is an `int` in Python, so True would pass a naive isinstance check and become
    # round 1. ADJACENT to the valid case, which is where the boundary lives.
    case("...including a bool, which is an int and would otherwise become round 1",
         "is not a [subject, round] pair" in
         (pinned_inventory({"rounds_at_arming": [["a", True]]})[1] or ""), True)
    # ⚠ THE BOOL CASE ABOVE IS HELD BY ITS OWN CLAUSE, NOT BY THE TYPE CHECK — a mutation proved
    # it by deleting the isinstance pair and staying green. A STRING round is what the int check
    # alone refuses, so this is the case that holds that clause.
    case("...and a STRING round, which is what the int check alone refuses",
         "is not a [subject, round] pair" in
         (pinned_inventory({"rounds_at_arming": [["a", "1"]]})[1] or ""), True)
    case("a non-object baseline is refused by its own type name",
         "not an object" in (pinned_inventory(["a", 1])[1] or ""), True)
    # ⭐⭐ THE BUG ITSELF, AS A CASE, with the real shape: a subject whose rounds ALL predate
    # arming must NOT be named — and without the pin, a tree listing that has lost them does name
    # it. The two inventories are the only difference between these two calls.
    _hist = {"memory-index-budget": {1, 2, 3}}
    case("⭐ a subject whose rounds ALL predate arming is NOT starved, given the pin",
         subjects_starved(_ARM, _hist,
                          {("memory-index-budget", n) for n in (1, 2, 3)}), ([], None))
    case("⛔ ...and WITHOUT that history it IS named — which is what a squash does to git",
         subjects_starved(_ARM, _hist, set()), (["memory-index-budget"], None))

    case("a HISTORICAL r2 with a newly BACK-FILLED r1 is in scope — r1's rule missed it",
         subjects_starved(_ARM, {"new": _D["new"]}, {("new", 2)}), (["new"], None))
    # ⭐⭐ r2 YH2, THE CASE THAT MATTERS MOST: the documents MOVED since arming. Under the old
    # path-set rule neither current path was in `before`, so an entirely historical subject was
    # named as newly starved — backlog #56's death, from a file reorganisation.
    case("⭐ a subject whose documents MOVED since arming is still historical",
         subjects_starved(_ARM,
                          {"old": {1: {"docs/reviews/codex/old-r1-codex.md"},
                                   2: {"docs/reviews/codex/old-r2-codex.md"}}},
                          rounds_in_paths({"docs/reviews/old-r1-codex.md",
                                           "docs/reviews/old-r2-codex.md"})), ([], None))
    case("a subject with one round is not yet in scope, however recent",
         subjects_starved(_ARM, {"one": _D["one"]}, set()), ([], None))
    case("every subject that crossed is named, not just the first found",
         subjects_starved(_ARM, _D, set()), (["new", "old"], None))
    case("no arming date means nothing is starved, and the promise says so instead",
         subjects_starved(None, _D, set()), ([], None))
    case("a BARE DATE is refused — git's approxidate would match nothing, silently",
         ("no timezone" in (subjects_starved("2026-10-20", _D, set())[1] or ""),
          subjects_starved("2026-10-20", _D, set())[0]), (True, []))
    case("...and so is free text, with the remedy named",
         ("not an ISO-8601 instant" in (subjects_starved("on merge", _D, set())[1] or "")), True)
    case("a full ISO instant with an offset is accepted",
         subjects_starved(_ARM, {"one": _D["one"]}, set()), ([], None))
    case("the arming instant is parsed, not pattern-matched — a second valid form works too",
         subjects_starved("2026-01-02T03:04:05+00:00", {"new": _D["new"]}, set()),
         (["new"], None))

    # ── rounds_in_paths: the identity itself ─────────────────────────────────────────────────
    _SH = round_shapes()
    case("a path yields the (subject, round) its BASENAME grammar names",
         rounds_in_paths({"docs/reviews/coordinator/s-r3-coordinator.md"}, _SH), {("s", 3)}),
    case("⭐ the DIRECTORY is irrelevant, which is what survives a move",
         (rounds_in_paths({"docs/reviews/s-r3-codex.md"}, _SH)
          == rounds_in_paths({"docs/reviews/codex/s-r3-codex.md"}, _SH)), True)
    case("a non-ASCII subject parses, so a quoted-path defeat is a READING bug not a rule bug",
         rounds_in_paths({"docs/reviews/codex/é-r1-codex.md"}, _SH), {("é", 1)})
    case("a path that is not a round document contributes nothing",
         rounds_in_paths({"docs/reviews/architecture-review-2026-07-30.md"}, _SH), set())
    case("both filename shapes are honoured, because SHAPES is imported not retyped",
         rounds_in_paths({"docs/reviews/a-r1-codex.md", "docs/reviews/b-codex-r2.md"}, _SH),
         {("a", 1), ("b", 2)})
    case("an empty path set yields no rounds rather than raising",
         rounds_in_paths(set(), _SH), set())

    # ── parse_armed_at and tree_at, the two inputs trigger 1 stands on ───────────────────────
    case("a full instant parses to an epoch", parse_armed_at(_ARM)[0] is not None, True)
    case("a naive instant is refused, because the window would depend on the reader's machine",
         "no timezone" in (parse_armed_at("2026-10-20T10:00:00")[1] or ""), True)
    case("an impossible date is refused by the parser, where git would have accepted it",
         parse_armed_at("2026-13-45T99:00:00")[0], None)
    case("a non-string is refused by type, not by regex",
         parse_armed_at(20261020)[0], None)
    # ── tree_at, driven over a git repository THE CASE BUILDS (backlog #322) ─────────────────
    # ⛔⛔ THESE CASES USED TO ASSERT AGAINST *THIS* REPOSITORY, and that cost the whole file its
    # mutation coverage: `tree_at` resolved its repo from `__file__`, so in the harness's staged
    # copy (no `.git`) every git call failed, the control went red, and `mutate_delivered`
    # returned NotMeasured for all 1,623 mutations. They also had two defects of their own:
    #   * r3 L19 — they named two real repository paths, one of which is a moving target;
    #   * and the headline one passed VACUOUSLY. `file in (_tree or set())` with `_tree = None`
    #     is a membership test over nothing: assertion False, expectation False, PASS. The case
    #     written to prove the historical instant is read COULD NOT FAIL.
    # A constructed repository fixes all three: it exists wherever the suite runs, its paths are
    # ours, and `_tree` is never None, so the instant assertion is real.
    import subprocess as _sub

    def _git_repo(d: Path, commits):
        """A real repo with one commit per (epoch, filename). Returns {filename: epoch}."""
        import fixture_git  # backlog #373: one constructed environment, built per call
        def g(*a, **kw):
            return _sub.run(["git", "-c", "user.name=t", "-c", "user.email=t@e", *a],
                            cwd=d, capture_output=True, text=True, check=True,
                            env=fixture_git.env(HOME=str(d), **kw.get("extra", {})))
        g("init", "-q", "-b", "main")
        for epoch, fname in commits:
            (d / fname).write_text("x")
            g("add", fname)
            g("commit", "-q", "-m", fname,
              extra={"GIT_AUTHOR_DATE": f"@{epoch} +0000",
                     "GIT_COMMITTER_DATE": f"@{epoch} +0000"})
        return d

    with _tf.TemporaryDirectory() as _gd:
        _gr = _git_repo(Path(_gd), [(1_700_000_000, "old-r1-codex.md"),
                                    (1_900_000_000, "new-r1-codex.md")])
        _T_MID, _T_LATE = 1_800_000_000, 1_950_000_000
        _mid, _mid_why = tree_at(_T_MID, _gr)
        case("tree_at reads a repository it is GIVEN, so the suite needs no repo of its own",
             (_mid_why, isinstance(_mid, set)), (None, True))
        # ⭐ THE INSTANT, ASSERTED BOTH WAYS over history the case controls.
        case("⭐ a file committed AFTER the instant is absent from the tree at that instant",
             "new-r1-codex.md" in (_mid or set()), False)
        case("...and one committed BEFORE it is present, so absence is not emptiness",
             "old-r1-codex.md" in (_mid or set()), True)
        _late, _ = tree_at(_T_LATE, _gr)
        case("at a LATER instant the same file IS present — two distinct epochs, one repo",
             ("new-r1-codex.md" in (_late or set()), "old-r1-codex.md" in (_late or set())),
             (True, True))
        case("an instant before the first commit is refused, not answered with an empty tree",
             tree_at(1, _gr)[0], None)
        # ⭐ AND THE RATCHET END-TO-END over a built repo: the late file's subject crossed into
        # scope after _T_MID; the early one did not. No real-repository path appears anywhere.
        _docs = {"old": {1: {"old-r1-codex.md"}, 2: {"old-r2-codex.md"}},
                 "new": {1: {"new-r1-codex.md"}, 2: {"new-r2-codex.md"}}}
        _gr2 = None
        with _tf.TemporaryDirectory() as _gd2:
            _gr2 = _git_repo(Path(_gd2), [(1_700_000_000, "old-r1-codex.md"),
                                          (1_700_000_100, "old-r2-codex.md"),
                                          (1_900_000_000, "new-r1-codex.md"),
                                          (1_900_000_100, "new-r2-codex.md")])
            # ⭐ END TO END over a repository the case built, with the membership DERIVED from
            # it: at this instant the early subject's rounds exist and the late one's do not.
            case("⭐ end to end on a BUILT repo: only the subject that crossed is named",
                 subjects_starved("2027-01-01T00:00:00+00:00", _docs, repo=_gr2),
                 (["new"], None))
            # The SAME answer with membership SUPPLIED rather than derived — so the two halves
            # of the set difference are checked independently, which is what r3 found missing:
            # `rounds_in_paths` gained six cases and `_round_docs`, its counterpart, got none.
            case("...and supplying the membership directly gives the same answer",
                 subjects_starved("2027-01-01T00:00:00+00:00", _docs,
                                  before_rounds=rounds_in_paths({"old-r1-codex.md",
                                                                 "old-r2-codex.md"}))[0],
                 ["new"])
            # ⛔ AND AN INSTANT BEFORE THE REPOSITORY'S HISTORY REFUSES, rather than reporting
            # that everything is new. I expected the latter writing this case and the code was
            # right: "nothing predates the instant" is not evidence that every subject crossed
            # into scope — it is evidence the question cannot be answered here. The refusal has
            # to PROPAGATE through subjects_starved, which is what this checks.
            _pre = subjects_starved("2023-01-01T00:00:00+00:00", _docs, repo=_gr2)
            case("an instant before the repo's history REFUSES, and names no subject",
                 (_pre[0], "no commit exists at or before" in (_pre[1] or "")), ([], True))

    case("an EMPTY listing is git not having been read, not a tree that held nothing",
         "cannot be true of a commit" in (empty_listing_refusal(set(), "abcdef1234") or ""), True)
    case("...and a non-empty one is accepted — two DISTINCT inputs, so the set is read",
         (empty_listing_refusal({"a"}, "abcdef1234"),
          empty_listing_refusal(set(), "beef0000") is not None), (None, True))
    case("tree_at refuses an instant that predates the repository rather than returning {}",
         tree_at(1)[0], None)
    case("a shallow clone is REFUSED, because history before arming is absent",
         "SHALLOW" in (shallow_refusal("true") or ""), True)
    case("...and a full clone is not — two DISTINCT inputs, so the flag is read",
         (shallow_refusal("false"), shallow_refusal("true") is not None), (None, True))
    case("the flag is compared after stripping, so git's trailing newline does not defeat it",
         shallow_refusal("true\n") is not None, True)

    # ── trigger 2: the primary falsifier, now per UNIT over DERIVED history ──────────────────
    # ⛔ REWRITTEN AFTER r1 B3. The old cases handed ONE row an authored `routes_tried`, which is
    # exactly the field an author could understate to hide exhaustion. These build a unit's
    # history out of its rows, which is what the code now reads.
    def _u(n, route, outcome=None, **kw):
        r = {"subject": "s", "unit": n, "route": route, "outcome": outcome, **kw}
        if outcome == "stopped":
            r.setdefault("rounds_at_termination", 3)
        return r
    _exhausted = [_u("u", r, "continued") for r in LADDER]
    case("a unit that exhausted every route and still carries findings REFUTES the design",
         "refuted" in (_try(lambda: t2_non_termination(_exhausted)) or ""), True)
    case("the SAME unit reaching the last route and STOPPING is the success path",
         t2_non_termination(_exhausted[:-1] + [_u("u", "defer", "stopped")]), None)
    # ⚠ ADJACENT: three routes, not four. The boundary is where the error lives.
    case("three routes tried is still escalating, not exhausted",
         t2_non_termination(_exhausted[:3]), None)
    # ⛔ THE PRIMARY FALSIFIER MUST NOT BE BLINDED BY THE NEW DOOR. A unit that reaches the
    # terminal rung by declaring a skip has an exhausted ladder with ONE attempt in it, so an
    # exhaustion test that counts ATTEMPTS stops firing exactly where the skip is used.
    case("⭐ a unit that reached the terminal rung BY SKIP and still carries findings REFUTES it",
         "refuted" in (_try(lambda: t2_non_termination(
             [_u("u", "defer", "continued", skipped=["accrete", "redesign", "split"],
                 why_skipped="x")])) or ""), True)
    case("...and a declared skip that has NOT reached the terminal rung is still escalating",
         t2_non_termination([_u("u", "split", "continued", skipped=["accrete", "redesign"],
                                why_skipped="x")]), None)
    # ⭐ THE CASE FOR THE BLOCKING ITSELF: the old version read one row's AUTHORED field, so a
    # history that was never written looked unexhausted. Derivation makes that unreachable.
    case("exhaustion is DERIVED, so it cannot be hidden by never writing routes_tried",
         "refuted" in (_try(lambda: t2_non_termination(
             [{"subject": "s", "unit": "u", "route": r, "outcome": "continued"}
              for r in LADDER])) or ""), True)
    case("two DIFFERENT units each three rounds in are not exhausted between them",
         t2_non_termination([_u("u", r, "continued") for r in LADDER[:2]]
                            + [_u("v", r, "continued") for r in LADDER[:2]]), None)

    # ── trigger 2 / trigger 11: an exhausted unit is OPEN (FAIL) or CLOSED by its DEFER (WARN) ──
    # ⟳ 2026-10-23 r5, the owner's decision (option A). Two distinct inputs per branch: a fully
    # WALKED ladder on unit u, and a SKIP straight to defer on unit w. Every log here is one
    # `invalid_rows` accepts (the last case of this block holds them to it).
    _walk_open = [_u("u", r, "continued") for r in LADDER]
    _skip_open = [_u("w", "defer", "continued", skipped=["accrete", "redesign", "split"],
                     why_skipped="judged futile")]
    _walk_closed = _walk_open[:-1] + [_u("u", "defer", "continued", rounds_at_termination=5)]
    _skip_closed = [{**_skip_open[0], "rounds_at_termination": 2}]
    _walk_stopped = _walk_open[:-1] + [_u("u", "defer", "stopped")]
    _skip_stopped = [{**_skip_open[0], "outcome": "stopped", "rounds_at_termination": 1}]
    case("⭐ an exhausted unit whose DEFER continued and did NOT close it FAILs trigger 2, not 11",
         ("refuted" in (_try(lambda: t2_non_termination(_walk_open)) or ""),
          _try(lambda: t11_ladder_exhausted_closed(_walk_open))), (True, None))
    case("...and so does one that SKIPPED to defer, on another unit",
         ("(s/w)" in (_try(lambda: t2_non_termination(_skip_open)) or ""),
          _try(lambda: t11_ladder_exhausted_closed(_skip_open))), (True, None))
    case("⭐ a continued DEFER that records rounds_at_termination CLOSES the unit: WARN, not FAIL",
         (_try(lambda: t2_non_termination(_walk_closed)),
          _try(lambda: t11_ladder_exhausted_closed(_walk_closed))),
         (None, "1 unit(s) exhausted every route, the stream continued, and a DEFER CLOSED them "
                "(s/u) — set down, not repaired; the ladder terminated, the findings did not"))
    case("...and so does a skipped-to-defer unit that closes, on another unit",
         (_try(lambda: t2_non_termination(_skip_closed)),
          "(s/w)" in (_try(lambda: t11_ladder_exhausted_closed(_skip_closed)) or "")),
         (None, True))
    case("⭐ an exhausted unit whose DEFER STOPPED is quiet on both triggers",
         (_try(lambda: t2_non_termination(_walk_stopped)),
          _try(lambda: t11_ladder_exhausted_closed(_walk_stopped))), (None, None))
    case("...and so is a skipped-to-defer unit that stopped",
         (_try(lambda: t2_non_termination(_skip_stopped)),
          _try(lambda: t11_ladder_exhausted_closed(_skip_stopped))), (None, None))
    case("an open and a closed unit side by side: trigger 2 names only the OPEN one",
         (_try(lambda: t2_non_termination(_walk_closed + _skip_open)) or "").count("(s/w)"), 1)
    case("⭐ a bet after a CLOSED unit is refused — a closed unit cannot be reopened",
         "is CLOSED" in (validate_row(_u("u", "accrete"), _walk_closed) or ""), True)
    case("...whatever its route, after a skipped-to-defer close on another unit",
         "is CLOSED" in (validate_row(_u("w", "split", "stopped"), _skip_closed) or ""), True)
    case("⛔ rounds_at_termination on a continued NON-DEFER row is refused — a rung is left",
         ("only a continued 'defer'" in (validate_row(
             _u("u", "accrete", "continued", rounds_at_termination=3)) or ""),
          "only a continued 'defer'" in (validate_row(
              _u("w", "split", "continued", rounds_at_termination=1,
                 skipped=["accrete", "redesign"], why_skipped="x")) or "")), (True, True))
    case("⛔ rounds_at_termination must be an integer >= 1 — zero, and a bool posing as one",
         ("must be an integer >= 1" in (validate_row(
             _u("u", "defer", "continued", rounds_at_termination=0)) or ""),
          "must be an integer >= 1" in (validate_row(
              {**_u("w", "accrete", "stopped"), "rounds_at_termination": True}) or "")),
         (True, True))
    case("every log this block drives is one main() ACCEPTS",
         [n for n, lg in (("walk_open", _walk_open), ("skip_open", _skip_open),
                          ("walk_closed", _walk_closed), ("skip_closed", _skip_closed),
                          ("walk_stopped", _walk_stopped), ("skip_stopped", _skip_stopped))
          if _try(lambda: invalid_rows(lg))], [])

    # ── trigger 12: a ladder RESTARTED on a new unit after its subject closed one ─────────────
    # ⟳ r5, the owner's second containment. Seen, not forbidden: a WARN, never a refusal.
    _restart1 = _walk_closed + [_u("u2", "accrete", "continued")]
    _restart2 = _skip_closed + [_u("w-again", "accrete"), _u("w-again", "redesign")]
    _sibling1 = [_u("v", "accrete")] + _walk_closed
    _sibling2 = [_u("x", "accrete", "stopped")] + _skip_closed + [_u("x", "redesign")]
    _other_subj = _walk_closed + [{**_u("u9", "accrete"), "subject": "t"}]
    _no_close = _walk_open + [_u("u3", "accrete")]
    case("⭐ a NEW unit after a closure WARNS, naming the subject, the closed unit and the new one",
         _try(lambda: t12_ladder_restarted(_restart1)),
         "1 ladder(s) restarted after exhaustion (s: u2 after u closed) — a closed unit cannot "
         "be reopened, so check the new unit is separate work, not the old one renamed")
    case("...and so does one after a skipped-to-defer close, however many rows it has",
         _try(lambda: ladder_restarts(_restart2)), [("s", "w", "w-again")])
    case("⭐ a sibling unit that PREDATES the closure does not warn",
         _try(lambda: t12_ladder_restarted(_sibling1)), None)
    case("...nor does one that began before it and kept betting after it",
         _try(lambda: ladder_restarts(_sibling2)), [])
    case("⭐ a new unit on ANOTHER subject after a closure does not warn",
         _try(lambda: t12_ladder_restarted(_other_subj)), None)
    case("...nor does a new unit on a subject whose exhausted unit is OPEN, not closed",
         _try(lambda: ladder_restarts(_no_close)), [])
    case("every trigger-12 log is one main() ACCEPTS",
         [n for n, lg in (("restart1", _restart1), ("restart2", _restart2),
                          ("sibling1", _sibling1), ("sibling2", _sibling2),
                          ("other_subj", _other_subj), ("no_close", _no_close))
          if _try(lambda: invalid_rows(lg))], [])

    # ── trigger 3: a bet the stream CONTINUED past, whose next route was never logged ─────────
    # ⟳ 2026-10-23: replaces the route-collapse cases, whose subject is deleted. Each branch is
    # driven by TWO DISTINCT inputs — a different unit, and a different rung of the ladder — so
    # no branch is satisfied by one fixture's constant.
    def _b(sub, unit, route, outcome=None, **kw):
        r = {"subject": sub, "unit": unit, "route": route, "outcome": outcome, **kw}
        if outcome == "stopped":
            r.setdefault("rounds_at_termination", 2)
        return r
    # ⛔ EVERY CALL GOES THROUGH `_try`, like trigger 2's cases: a mutation that makes a trigger
    # RAISE must redden the case it hits, not kill the suite before the cases after it run —
    # measured, an unwrapped call here took every later case down under a grouping mutation.
    # ⛔ r1 F3: and EVERY log below is one `main()` would accept — the last case of this block
    # holds them all to `invalid_rows`, the CLI's own validation.
    _NO_PINS = frozenset()
    _fail1 = [_b("s", "u", "accrete", "continued")]
    _fail2 = [_b("t", "v", "accrete", "continued"), _b("t", "v", "redesign", "continued")]
    _quiet1 = [_b("s", "u", "accrete", "continued"), _b("s", "u", "redesign")]
    _quiet2 = [_b("t", "v", "accrete", "continued"), _b("t", "v", "redesign", "continued"),
               _b("t", "v", "split", "stopped")]
    _forced = [_b(f"p{i}", "u", "accrete", "stopped") for i in range(5)]
    _retro_lost = [_b("s", "u", "accrete", "continued", retroactive=True)]
    _defer1 = [_b("s", "u", "defer", "continued", skipped=["accrete", "redesign", "split"],
                  why_skipped="judged futile on this shape")]
    _defer2 = [_b("t", "v", r, "continued") for r in LADDER]
    _apart = [_b("s", "u", "accrete", "continued"), _b("s", "w", "accrete")]
    _inflight = [_b("s", "u", "accrete")]
    _kinded = [_b("k", "u", "accrete", "continued", kind="attempt")]
    case("⭐ a FIRST bet the stream continued past, with no later row, FAILS naming its unit",
         _try(lambda: t3_lost_bet_not_escalated(_fail1, _NO_PINS)),
         "1 bet(s) the stream continued past with no next route logged (s/u) — the route's "
         "failure observation was seen and the ladder's escalation was never recorded, so the "
         "work kept going on a route the log records as failed")
    case("...and so does a SECOND such bet, while the first — escalated in time — stays quiet",
         _try(lambda: t3_lost_bet_not_escalated(_fail2, frozenset({("x", "y")}))),
         "1 bet(s) the stream continued past with no next route logged (t/v) — the route's "
         "failure observation was seen and the ladder's escalation was never recorded, so the "
         "work kept going on a route the log records as failed")
    case("⭐ a bet followed by a PROSPECTIVE next bet is quiet on trigger 3",
         _try(lambda: t3_lost_bet_not_escalated(_quiet1, _NO_PINS)), None)
    case("...and so is a two-rung escalation that ends in a won split",
         _try(lambda: t3_lost_bet_not_escalated(_quiet2, frozenset({("q", "r")}))), None)
    # ⛔⛔ THE STRUCTURAL FALSE ALARM THIS TRIGGER REPLACES. Five first-rung accrete rows that all
    # WON are the ladder's forced shape, not a conveyor — the old trigger failed on exactly this.
    case("⭐ five first-rung accrete bets that all STOPPED are quiet — the forced rung is not a conveyor",
         _try(lambda: t3_lost_bet_not_escalated(_forced, _NO_PINS)), None)
    case("an IN-FLIGHT bet (no outcome yet) is not a bet the stream continued past",
         _try(lambda: t3_lost_bet_not_escalated(_inflight, _NO_PINS)), None)
    case("a RETROACTIVE bet is not a bet, so nothing is owed after it",
         _try(lambda: t3_lost_bet_not_escalated(_retro_lost, _NO_PINS)), None)
    # ⛔ r1 F4: a continued DEFER has no rung to escalate to. Trigger 2 owns it; trigger 3
    # naming it as well would be two triggers for one defect, and its message would be false.
    case("⭐ a continued DEFER reached by SKIP is trigger 2's FAIL, and trigger 3 is silent",
         ("refuted" in (_try(lambda: t2_non_termination(_defer1)) or ""),
          _try(lambda: t3_lost_bet_not_escalated(_defer1, _NO_PINS))), (True, None))
    case("...and so is one at the end of a fully WALKED ladder, on another unit",
         ("refuted" in (_try(lambda: t2_non_termination(_defer2)) or ""),
          _try(lambda: t3_lost_bet_not_escalated(_defer2, _NO_PINS))), (True, None))
    case("lost_bets reads each UNIT apart — a next bet on another unit does not escalate this one",
         _try(lambda: lost_bets(_apart)), [("s", "u", "accrete")])
    case("...and names a SECOND-rung loss by its own unit AND route",
         _try(lambda: lost_bets(_fail2)), [("t", "v", "redesign")])
    case("a bet row carrying the redesign plan's `kind` is judged like any other bet",
         _try(lambda: t3_lost_bet_not_escalated(_kinded, _NO_PINS)) is not None, True)

    # ── the PINNED pre-trigger lost bets: history, not an exemption anyone can write ─────────
    # ⟳ r3: replaces the in-log acknowledgment, REMOVED for thrashing. ⟳ r4: a pin names ONE
    # BET, (subject, unit, route) — a pin on the unit would excuse its every later loss too.
    _pin_s = frozenset({("s", "u", "accrete")})
    _pin_t = frozenset({("t", "v", "redesign")})
    case("⭐ a PINNED lost bet does not FAIL trigger 3, and trigger 10 names it as history",
         (_try(lambda: t3_lost_bet_not_escalated(_fail1, _pin_s)),
          _try(lambda: t10_pre_trigger_lost_bet(_fail1, _pin_s))),
         (None, "1 lost bet(s) PREDATE trigger 3 and are pinned in baseline.json (s/u "
                "(accrete)) — their next route was never logged, and they are history the rule "
                "could not have governed"))
    case("...and so is a pinned SECOND-rung loss on another unit",
         (_try(lambda: t3_lost_bet_not_escalated(_fail2, _pin_t)),
          "PREDATE trigger 3" in (_try(lambda: t10_pre_trigger_lost_bet(_fail2, _pin_t)) or "")),
         (None, True))
    case("⭐ an UNPINNED lost bet still FAILS while another unit's is pinned",
         "(s/w)" in (_try(lambda: t3_lost_bet_not_escalated(
             _fail1 + [_b("s", "w", "accrete", "continued")], _pin_s)) or ""), True)
    case("...and a pin on another unit of the SAME subject does not cover it",
         "(t/v)" in (_try(lambda: t3_lost_bet_not_escalated(
             _fail2, frozenset({("t", "other", "redesign")}))) or ""), True)
    # ⛔⛔ r4 Codex Major, with BOTH shipped histories: the pinned bet ESCALATED and its successor
    # LOST. The successor is a new loss and FAILs; the pin no longer matches an unescalated loss,
    # so it is reported UNUSED — "a later bet escalated it and the pin is stale" is exactly true.
    _AO = ("work-lines-always-on", "last-plan lifecycle + Stop-hook optional steps")
    _BF = ("work-lines-backfill", "transcript replay (event intake + END windows + checkpoints)")
    _ship = frozenset({_AO + ("accrete",), _BF + ("accrete",)})
    _succ_ao = [_b(*_AO, "accrete", "continued"), _b(*_AO, "redesign", "continued"),
                _b(*_BF, "accrete", "continued")]
    _succ_bf = [_b(*_AO, "accrete", "continued"), _b(*_BF, "accrete", "continued"),
                _b(*_BF, "redesign", "continued"), _b(*_BF, "split", "continued")]
    case("⭐ always-on's pinned bet ESCALATED and its successor LOST: trigger 3 FAILs on it",
         (_try(lambda: t3_lost_bet_not_escalated(_succ_ao, _ship)),
          "1 pin(s) match no unescalated lost bet in this log (work-lines-always-on/last-plan "
          "lifecycle + Stop-hook optional steps (accrete))" in (
              _try(lambda: t10_pre_trigger_lost_bet(_succ_ao, _ship)) or "")),
         ("1 bet(s) the stream continued past with no next route logged (work-lines-always-on/"
          "last-plan lifecycle + Stop-hook optional steps) — the route's failure observation was "
          "seen and the ladder's escalation was never recorded, so the work kept going on a "
          "route the log records as failed", True))
    case("...and so does backfill's, two rungs on, its pin reported UNUSED and always-on's HIT",
         ("(work-lines-backfill/" in (_try(lambda: t3_lost_bet_not_escalated(_succ_bf, _ship))
                                       or ""),
          "match no unescalated lost bet in this log (work-lines-backfill/" in (
              _try(lambda: t10_pre_trigger_lost_bet(_succ_bf, _ship)) or ""),
          "pinned in baseline.json (work-lines-always-on/" in (
              _try(lambda: t10_pre_trigger_lost_bet(_succ_bf, _ship)) or "")),
         (True, True, True))
    # A pin whose bet was ESCALATED in time matches nothing: trigger 3 is quiet regardless, and
    # trigger 10 reports the pin as UNUSED, because a pin that matches nothing is stale.
    case("⭐ a pin on a unit that ESCALATED is quiet on trigger 3 and reported UNUSED by trigger 10",
         (_try(lambda: t3_lost_bet_not_escalated(_quiet1, _pin_s)),
          _try(lambda: t10_pre_trigger_lost_bet(_quiet1, _pin_s))),
         (None, "1 pin(s) match no unescalated lost bet in this log (s/u (accrete)) — expected "
                "while that bet's row is on a branch not merged here; otherwise a later bet "
                "escalated it and the pin is stale and should be deleted"))
    case("...and so is one whose escalation ended in a won split, on another unit",
         (_try(lambda: t3_lost_bet_not_escalated(_quiet2, _pin_t)),
          "match no unescalated lost bet in this log (t/v (redesign))" in (
              _try(lambda: t10_pre_trigger_lost_bet(_quiet2, _pin_t)) or "")), (None, True))
    case("⭐ a pin on a unit ABSENT from the log WARNS as unused and does not crash",
         "match no unescalated lost bet in this log (gone/u (accrete))" in (_try(
             lambda: t10_pre_trigger_lost_bet(_forced, frozenset({("gone", "u", "accrete")})))
             or ""), True)
    case("...including over an EMPTY log",
         "match no unescalated lost bet in this log (t/v (redesign))" in (_try(
             lambda: t10_pre_trigger_lost_bet([], _pin_t)) or ""), True)
    case("no pins and no lost bets: trigger 10 is quiet",
         (_try(lambda: t10_pre_trigger_lost_bet(_quiet1, _NO_PINS)),
          _try(lambda: t10_pre_trigger_lost_bet(_forced, _NO_PINS))), (None, None))
    case("...and an UNPINNED lost bet is trigger 3's alone, never trigger 10's",
         _try(lambda: t10_pre_trigger_lost_bet(_fail1, _NO_PINS)), None)
    _pins_ok = {PRE_TRIGGER_PINS: [
        {"subject": "s", "unit": "u", "route": "accrete", "reason": "predates it"},
        {"subject": "t", "unit": "v", "route": "redesign", "reason": "also predates"}]}
    case("pinned_lost_bets reads the pins as a closed set of (subject, unit, route)",
         pinned_lost_bets(_pins_ok),
         (frozenset({("s", "u", "accrete"), ("t", "v", "redesign")}), None))
    case("...and an ABSENT key is the empty set, a repository with no pre-trigger history",
         pinned_lost_bets({"armed_at": "x"}), (frozenset(), None))
    # ⛔ r4 Codex Low: a PRESENT key must be a list — `null` is not "no pins".
    case("⛔ a PRESENT null pin list is refused, never read as empty",
         "is NoneType, not a list" in str(_try(lambda: pinned_lost_bets(
             {PRE_TRIGGER_PINS: None}))), True)
    case("⛔ a pin with no REASON is refused — an exemption must say why it is history",
         ("has no reason" in (pinned_lost_bets(
             {PRE_TRIGGER_PINS: [{"subject": "s", "unit": "u", "route": "accrete"}]})[1] or ""),
          "has no reason" in (pinned_lost_bets(
              {PRE_TRIGGER_PINS: [{"subject": "t", "unit": "v", "route": "split",
                                   "reason": " !! "}]})[1] or "")),
         (True, True))
    case("⛔ a pin with no ROUTE is refused — it would name a unit, not a bet",
         ("names route None" in str(_try(lambda: pinned_lost_bets(
             {PRE_TRIGGER_PINS: [{"subject": "s", "unit": "u", "reason": "x"}]}))),
          "names route 'retry'" in str(_try(lambda: pinned_lost_bets(
              {PRE_TRIGGER_PINS: [{"subject": "t", "unit": "v", "route": "retry",
                                   "reason": "y"}]})))), (True, True))
    case("⛔ a pin list of the wrong SHAPE is refused, never read as empty",
         "is str, not a list" in str(_try(lambda: pinned_lost_bets({PRE_TRIGGER_PINS: "s/u"}))),
         True)
    case("⛔ ...and so is a pin ENTRY of the wrong shape",
         "not a {subject, unit, route, reason}" in str(_try(lambda: pinned_lost_bets(
             {PRE_TRIGGER_PINS: [["s", "u"]]}))), True)
    case("⛔ a pin written TWICE is refused",
         "is pinned twice" in (pinned_lost_bets(
             {PRE_TRIGGER_PINS: _pins_ok[PRE_TRIGGER_PINS][:1] * 2})[1] or ""), True)
    case("a baseline that is not an object is refused",
         "not an object" in str(_try(lambda: pinned_lost_bets([]))), True)
    # ⛔ THE LIST IS CLOSED: an independent copy of the shipped pins, so adding one reddens here.
    _shipped = pinned_lost_bets(json.loads(BASELINE.read_text()))
    case("⛔ the SHIPPED pin list is exactly the two lost bets that predate trigger 3",
         _shipped, (frozenset({
             ("work-lines-always-on", "last-plan lifecycle + Stop-hook optional steps",
              "accrete"),
             ("work-lines-backfill",
              "transcript replay (event intake + END windows + checkpoints)", "accrete")}),
             None))
    case("every log this block drives is one main() ACCEPTS — no branch is tested off-domain",
         [n for n, lg in (("fail1", _fail1), ("fail2", _fail2), ("quiet1", _quiet1),
                          ("quiet2", _quiet2), ("forced", _forced), ("retro_lost", _retro_lost),
                          ("defer1", _defer1), ("defer2", _defer2), ("apart", _apart),
                          ("inflight", _inflight), ("kinded", _kinded),
                          ("succ_ao", _succ_ao), ("succ_bf", _succ_bf))
          if _try(lambda: invalid_rows(lg))], [])
    case("invalid_rows NAMES a row the ladder refuses, by its 1-based number",
         [n for n, _ in invalid_rows([_b("s", "u", "accrete", "continued"),
                                      _b("s", "u", "split")])], [2])

    # ── trigger 4: no better than doing nothing, per SUBJECT (r1 Codex M6) ───────────────────
    def _done(subject, n):
        return {"subject": subject, "unit": "u", "route": "accrete", "outcome": "stopped",
                "rounds_at_termination": n}
    _five4 = [_done(f"s{i}", 4) for i in range(5)]
    case("a median at the pinned baseline is NOT an improvement — >= fails, not >",
         "ceremony" in (t4_no_improvement(_five4, 4) or ""), True)
    case("a median below the baseline passes",
         t4_no_improvement([_done(f"s{i}", 3) for i in range(5)], 4), None)
    case("four terminated SUBJECTS is below the floor",
         t4_no_improvement([_done(f"s{i}", 9) for i in range(4)], 4), None)
    # ⭐ THE r1 CODEX M6 CASE: five rows of ONE subject are a sample of one, not of five.
    case("five UNITS of one subject do not make five subjects",
         t4_no_improvement([{"subject": "one", "unit": f"u{i}", "route": "accrete",
                             "outcome": "stopped", "rounds_at_termination": 4}
                            for i in range(5)], 4), None)
    case("only the LAST five subjects count, so early bad ones do not pin it forever",
         t4_no_improvement([_done(f"old{i}", 9) for i in range(3)]
                           + [_done(f"new{i}", 2) for i in range(5)], 4), None)
    case("a stopped row with no round count cannot be scored and is excluded",
         t4_no_improvement([{"subject": f"s{i}", "unit": "u", "route": "accrete",
                             "outcome": "stopped"} for i in range(9)], 4), None)
    # ⭐⭐ r2 YM4, THE EXACT INPUT. A dict UPDATE does not move a key to the end, so
    # `list(...)[-5:]` took the last five by FIRST appearance. Measured: the latest five by
    # occurrence had median 9 and the code read 1, so trigger 4 stayed quiet over a run it
    # should have failed. Six subjects, then three of them repeat — the orders disagree.
    _ym4 = ([_done(sub, n) for sub, n in zip("ABCDEF", [9, 9, 9, 1, 1, 1])]
            + [_done(sub, 9) for sub in "ABC"])
    case("⭐ the LAST five subjects is by occurrence, not by first insertion",
         "is 9," in (t4_no_improvement(_ym4, 4) or ""), True)
    # ⛔ A CASE ASSERTING ARITHMETIC ABOUT A LIST LITERAL WAS WRITTEN HERE AND DELETED. Its
    # subject was a constant this suite wrote itself, not the code under test — it could only
    # ever report whether I can take a median by hand. The mutation entry below is what proves
    # the ordering clause is load-bearing.
    case("the comparator is the PINNED baseline, not the literal 4",
         (t4_no_improvement([_done(f"s{i}", 6) for i in range(5)], 7),
          "fires" if t4_no_improvement([_done(f"s{i}", 6) for i in range(5)], 6) else "quiet"),
         (None, "fires"))

    # ── trigger 8: fed, but only in HINDSIGHT (r7 Claude B1) ─────────────────────────────────
    # ⛔⛔ THE BRANCH'S HEADLINE CLAIM WAS "trigger 1 goes green by being FED, not patched", and
    # the very next commit added a field declaring those rows NOT PROSPECTIVE. Measured on the
    # live log: t1 is silent over all 6 rows and FIRES over the 4 prospective ones, naming
    # `decision-log-model-redesign`. The written defence — "it proves coverage, not timely use,
    # which is a different complaint" — is only sound if some trigger owns timely use. The
    # reviewer enumerated all seven and NONE did, so the only detector of non-use was being made
    # satisfiable by backfill. That complaint now has a home, and it is a WARN rather than a FAIL
    # because demanding a prospective row for a subject whose work is FINISHED is unsatisfiable
    # by construction, and a gate red from birth gets switched off (backlog #56).
    _retro_fed = [{"subject": "ghost", "unit": "u", "route": "accrete", "outcome": "continued",
                   "retroactive": True}]
    case("⭐ a subject fed ONLY in hindsight is NAMED, not absorbed into t1's silence",
         t8_hindsight_only(_retro_fed, ["ghost"]),
         "1 of 1 subject(s) are fed ONLY in hindsight: ghost — every row for them is "
         "retroactive, so the mechanism is a historian for that subject, not a decision aid; "
         "trigger 1 is quiet because a row EXISTS, which is coverage, not timely use")
    # ⚠ ADJACENT: one prospective row is enough to make the subject real use.
    case("...and one PROSPECTIVE row makes the subject genuine use, not hindsight",
         t8_hindsight_only(_retro_fed + [{"subject": "ghost", "unit": "u", "route": "redesign"}],
                           ["ghost"]), None)
    # ⚠ NO DOUBLE-REPORTING: a subject with no row at all is t1's business and must not appear
    # here too, or one defect would be counted twice and the reader cannot tell them apart.
    case("...and a subject with NO row at all belongs to trigger 1, not to this one",
         t8_hindsight_only([], ["nobody"]), None)
    # ⭐ THE DISCRIMINATING PAIR THE REVIEW ASKED FOR: a hindsight-only log must NOT be
    # indistinguishable from a prospective one. t1 alone cannot tell them apart — that is the
    # defect — so the pair is what holds it.
    case("⭐ a hindsight-only log is DISTINGUISHABLE from a prospective one, which t1 alone is not",
         ((t1_not_fed(_retro_fed, ["ghost"]), bool(t8_hindsight_only(_retro_fed, ["ghost"]))),
          (t1_not_fed([{"subject": "ghost", "unit": "u", "route": "accrete"}], ["ghost"]),
           bool(t8_hindsight_only([{"subject": "ghost", "unit": "u", "route": "accrete"}],
                                  ["ghost"])))),
         ((None, True), (None, False)))

    # ── trigger 5: two CONSECUTIVE misses ────────────────────────────────────────────────────
    case("one miss is a bet losing, not a broken instrument",
         t5_ranker_miss([{"ranker_hit": True}, {"ranker_hit": False}, {"ranker_hit": True}]),
         None)
    case("two consecutive misses fire, and the message says WHICH rows",
         "rows 2 and 3" in (t5_ranker_miss(
             [{"ranker_hit": True}, {"ranker_hit": False}, {"ranker_hit": False}]) or ""), True)
    case("rows without the field are not counted as misses",
         t5_ranker_miss([{}, {}, {}]), None)
    # ⛔ ONE ELIGIBILITY RULE, ONE PLACE — and r7 Claude M6 measured that the fold SHIPPED TWO
    # while claiming to have removed the duplication: t5 asked `"ranker_hit" in r`, t7 asked
    # `isinstance(..., bool)`, so `ranker_hit: 0` was a MISS to t5 and INELIGIBLE to t7. The
    # second implementation arrived in the commit whose message said it had borrowed the first.
    case("is_prediction is the ONE eligibility rule, over every value that has diverged",
         [is_prediction({"ranker_hit": v}) for v in
          (True, False, 0, 1, None, "false", "", [])] + [is_prediction({})],
         [True, True, False, False, False, False, False, False, False])
    # ⭐ THE UNIFICATION'S OWN FALSIFIER: the value the two rules disagreed about, asked of BOTH.
    # Without a shared helper this pair cannot agree, which is what makes it a guard and not a
    # restatement.
    case("...so t5 and t7 agree about the value they used to disagree about",
         (t5_ranker_miss([{"ranker_hit": 0}, {"ranker_hit": 0}]),
          t7_sample_reached([{"outcome": "continued", "ranker_hit": 0}] * 2, 2)),
         (None, None))

    # ── triggers 6 and 7: warnings ───────────────────────────────────────────────────────────
    # ⛔ THE CASE THAT WOULD HAVE CAUGHT THE INERT WIRING, AND DID NOT EXIST. The first wiring of
    # the count comparison passed `now_corpus=now` where `now` is `_corpus_now()`'s dict — which
    # emitted `subjects`, not the names `baseline.json` pins. A key that does not match is skipped
    # SILENTLY, so the new arms were dead code while five fixture-built cases passed, because a
    # fixture with the right key names proves what the function does to the FIXTURE. This asserts
    # the INTERFACE between the two instead: the producer must speak the pinned vocabulary.
    _pinned_keys = {"rounds_total", "subjects_with_any_round", "subjects_with_ge2_rounds"}
    case("⭐ _corpus_now emits the keys baseline.json pins, or trigger 6 compares nothing",
         _pinned_keys <= set(_try(lambda: _corpus_now()) or {}), True)
    # ── backlog #328: the COUNTS, which this trigger could not see until 2026-10-20 ──
    _pc = {"rounds_total": 392, "subjects_with_any_round": 105, "subjects_with_ge2_rounds": 81}
    case("⭐ a corpus that GREW past the count tolerance now fires — it did not before",
         "rounds_total 392 -> 420" in (t6_denominator_moved(
             {"median": 4}, {"median": 4},
             now_corpus={"rounds_total": 420}, pinned_corpus=_pc) or ""), True)
    case("...and the RATES alone would still have been quiet, which is the defect",
         t6_denominator_moved({"median": 4, "mean": 4.78}, {"median": 4, "mean": 4.84}), None)
    case("a count inside the tolerance stays quiet — +2 of 81 is not a moved population",
         t6_denominator_moved({"median": 4}, {"median": 4},
                              now_corpus={"subjects_with_ge2_rounds": 83},
                              pinned_corpus=_pc), None)
    case("the direction and size are REPORTED, so the reader judges rather than guesses",
         "+7.1%" in (t6_denominator_moved({"median": 4}, {"median": 4},
                                          now_corpus={"rounds_total": 420},
                                          pinned_corpus=_pc) or ""), True)
    # ⛔ `count_tol` VARIED, because a threshold no case can distinguish from a constant is a
    # threshold nothing guards — and this one is a stated JUDGEMENT rather than a measurement, so
    # it is exactly the kind that must be shown to be read.
    case("a tighter count tolerance fires on a drift the default tolerates",
         "subjects_with_ge2_rounds 81 -> 83" in (t6_denominator_moved(
             {"median": 4}, {"median": 4}, now_corpus={"subjects_with_ge2_rounds": 83},
             pinned_corpus=_pc, count_tol=0.01) or ""), True)
    case("a missing pinned count is skipped, not read as zero drift",
         t6_denominator_moved({"median": 4}, {"median": 4},
                              now_corpus={"rounds_total": 420}, pinned_corpus={}), None)
    case("a stable denominator is quiet", t6_denominator_moved({"median": 4}, {"median": 4}),
         None)
    case("a denominator that doubled warns",
         "4 -> 9" in (t6_denominator_moved({"median": 9}, {"median": 4}) or ""), True)
    case("a missing figure is skipped rather than compared against None",
         t6_denominator_moved({"median": None}, {"median": 4}), None)
    # SECOND pinned value, and an EXPLICIT tolerance: both were one constant across the suite.
    case("drift is relative to the PINNED figure, not to 4",
         ("fires" if t6_denominator_moved({"median": 4}, {"median": 10}) else "quiet"), "fires")
    case("a tighter tolerance fires on a move the default ignores",
         ("fires" if t6_denominator_moved({"median": 5}, {"median": 4}, tol=0.1) else "quiet",
          t6_denominator_moved({"median": 5}, {"median": 4})), ("fires", None))
    # ⟳ REWRITTEN AFTER r7 (Codex M2): these three read `[{"outcome": "stopped"}] * N`, which
    # carries NO ranker prediction. Two went red when the population became predictions — but
    # the nine-row case stayed GREEN while testing nothing it names: with no prediction in it,
    # it would pass at any N. A case that passes for an ambient reason is the shape this repo
    # keeps paying for, so all three now supply what they are about.
    def _hit(n, v=True):
        return [{"subject": f"q{i}", "unit": "u", "route": "accrete", "outcome": "continued",
                 "ranker_hit": v} for i in range(n)]
    case("nine ranker predictions is below the re-evaluation sample",
         t7_sample_reached(_hit(9)), None)
    # ⭐ IDENTITY on the whole message, not a substring of it: the bound, the counts and the
    # baseline are all reader-facing numbers, and r6 cost five rounds to a property asserted
    # five ways and defeated five times until it was pinned whole.
    case("ten ranker predictions asks for re-evaluation and quotes the bound EXACTLY",
         t7_sample_reached(_hit(10)),
         "10 ranker predictions (10 ranker hits) — re-evaluate now; at 10/10 the one-sided 95% "
         "accuracy bound reaches 74%, against a ~7% coin")
    # An EXPLICIT floor, distinct from the default, so the parameter is not a constant.
    case("the sample floor is a parameter, so three predictions reach a floor of three",
         ("fires" if t7_sample_reached(_hit(3), 3) else "quiet",
          t7_sample_reached(_hit(3))), ("fires", None))
    # ⛔⛔ THE FIXTURE THAT WAS MISSING, AND TWO MUTATIONS SURVIVED 179/179 BECAUSE OF IT (r7
    # Claude B2). Every t7 fixture above has len(rows) == len(sample) AT THE MESSAGE SITE, so an
    # identity case over them cannot tell the two populations apart: `len(sample)` -> `len(rows)`
    # reported "13 ranker predictions" over 10 — Codex M2's exact defect, restored inside its own
    # fix — and counting hits over `rows` with `.get()` read a coerced `"yes"` as a hit again.
    # ⚠ This is the "passes at ANY N" defect the fold itself named, recurring on a new axis.
    _mixed = _hit(6) + _hit(4, False) + [
        {"subject": "no-pred", "unit": "u", "route": "accrete", "outcome": "continued"},
        {"subject": "coerced", "unit": "u", "route": "accrete", "outcome": "continued",
         "ranker_hit": "yes"},
        {"subject": "retro", "unit": "u", "route": "accrete", "outcome": "continued",
         "ranker_hit": True, "retroactive": True}]
    # ⛔ _try, FOR THE THIRD TIME IN THIS ROUND. `_mixed` deliberately holds a row with NO
    # `ranker_hit`, so under a mutation that drops the eligibility test `r["ranker_hit"]` raises
    # KeyError — and an unprotected case here killed the suite before a LATER case the manifest
    # names was ever reached, costing that entry its attribution. A crash names nothing, and it
    # also hides every case after it.
    case("⭐ t7 names the ELIGIBLE count and the TRUE hit count, not the row count",
         _try(lambda: t7_sample_reached(_mixed)),
         "10 ranker predictions (6 ranker hits) — re-evaluate now; at 10/10 the one-sided 95% "
         "accuracy bound reaches 74%, against a ~7% coin")
    # ⚠ r7 Claude M8: the 74% is the Clopper-Pearson bound for n=10 SPECIFICALLY, while `floor`
    # is a parameter — at floor=3 the old message asserted a bound that is really ~37%.
    case("the quoted bound belongs to the floor it was computed for, and a different floor says so",
         t7_sample_reached(_hit(3), 3),
         "3 ranker predictions (3 ranker hits) — re-evaluate now; the 74% bound is pinned to a "
         "sample of 10, so it is NOT quoted for this floor of 3")

    # ── row validation ───────────────────────────────────────────────────────────────────────
    _good = {"subject": "s", "unit": "u", "route": "accrete", "routes_tried": [],
             "outcome": None}
    case("a well-formed row validates", validate_row(_good), None)
    case("a missing field is named", validate_row({k: v for k, v in _good.items()
                                                  if k != "unit"}), "missing 'unit'")
    case("an off-ladder route is refused",
         validate_row({**_good, "route": "rewrite"}),
         "route 'rewrite' is not on the ladder ['accrete', 'redesign', 'split', 'defer']")
    case("an unknown outcome is refused rather than read as unscored",
         "is not one of" in (validate_row({**_good, "outcome": "maybe"}) or ""), True)
    case("a stopped row without its round count is refused",
         validate_row({**_good, "outcome": "stopped"}),
         "a stopped row must record rounds_at_termination as an integer")
    # ⛔ routes_tried IS NO LONGER AUTHORED. An authored one may not CONTRADICT history, which
    # is the only thing left to check about it — the retry it used to enable is unreachable.
    case("an authored routes_tried that contradicts this unit's history is refused",
         "contradicts this unit's history" in (validate_row(
             {**_good, "routes_tried": ["accrete", "redesign"]}, []) or ""), True)
    case("...and one that AGREES with history is merely redundant, not an error",
         validate_row({**_good, "routes_tried": []}, []), None)
    case("the row validator borrows the SEQUENCE rule rather than re-stating it",
         route_sequence_error(["split"]) in (validate_row(
             {"subject": "s", "unit": "u", "route": "accrete"},
             [{"subject": "s", "unit": "u", "route": "split"}]) or ""), True)

    # ── derivation: the r1 Blocking redesign ─────────────────────────────────────────────────
    case("an empty history derives no routes", derive_routes_tried([]), [])
    case("history is DERIVED from the unit's own rows, in file order",
         derive_routes_tried([{"route": "accrete"}, {"route": "redesign"}]),
         ["accrete", "redesign"])
    case("a row with no route contributes nothing rather than a None",
         derive_routes_tried([{"route": "accrete"}, {}]), ["accrete"])
    # ⛔ A PASSED RUNG IS NOT AN ATTEMPT, and the two questions have different readers: the
    # validator asks where the ladder has got to, the triggers ask what was actually tried.
    # Conflating them would record a skipped rung as a failed attempt and destroy the very
    # counterfactual the skip exists to label.
    case("routes_accounted folds a declared skip into the rungs the ladder has passed",
         routes_accounted([{"route": "split", "skipped": ["accrete", "redesign"]}]),
         ["accrete", "redesign", "split"])
    case("...and a row with no skip contributes only its own route",
         routes_accounted([{"route": "accrete"}, {"route": "redesign"}]),
         ["accrete", "redesign"])
    case("⛔ an ATTEMPT is not a passed rung — the two producers disagree, by design",
         (derive_routes_tried([{"route": "split", "skipped": ["accrete", "redesign"]}]),
          routes_accounted([{"route": "split", "skipped": ["accrete", "redesign"]}])),
         (["split"], ["accrete", "redesign", "split"]))
    case("a non-list skipped contributes no rungs rather than its characters",
         routes_accounted([{"route": "split", "skipped": "accrete"}]), ["split"])
    case("unit_key partitions on (subject, unit), not on either alone",
         (unit_key({"subject": "a", "unit": "x"}) == unit_key({"subject": "a", "unit": "y"}),
          unit_key({"subject": "a", "unit": "x"}) == unit_key({"subject": "b", "unit": "x"})),
         (False, False))
    # A SECOND, DISTINCT input to the same producer — one call site cannot show it computes.
    case("group_by_unit over a single row gives one group, not an empty one",
         _try(lambda: {k: len(v) for k, v in group_by_unit(
             [{"subject": "z", "unit": "q", "route": "defer"}]).items()}), {("z", "q"): 1})
    case("group_by_unit keeps each unit's rows in file order",
         _try(lambda: {k: [r["route"] for r in v] for k, v in group_by_unit(
             [{"subject": "s", "unit": "u", "route": "accrete"},
              {"subject": "s", "unit": "v", "route": "accrete"},
              {"subject": "s", "unit": "u", "route": "redesign"}]).items()}),
         {("s", "u"): ["accrete", "redesign"], ("s", "v"): ["accrete"]})

    # ⭐⭐ THE r1 BLOCKING, AS A CASE. Five rows retrying one route exited 0 "all triggers quiet";
    # with the field OMITTED — which is now the normal way to write a row — the SECOND row is
    # refused by name. This is the falsifier for "a retry is inexpressible".
    _retry = [{"subject": "s", "unit": "u", "route": "accrete", "outcome": "continued"}]
    case("the FIRST bet on a unit is accrete and validates",
         validate_row(_retry[0], []), None)
    case("⭐ a RETRY of the same route is refused BY NAME, not merely flagged",
         "the only route left to bet on is 'redesign'" in (
             validate_row(_retry[0], _retry) or ""), True)
    case("...and the correct next route on that history validates",
         validate_row({"subject": "s", "unit": "u", "route": "redesign"}, _retry), None)
    case("a bet after the ladder is EXHAUSTED says so, rather than naming a next route",
         "EXHAUSTED" in (validate_row(
             {"subject": "s", "unit": "u", "route": "accrete"},
             [{"subject": "s", "unit": "u", "route": r} for r in LADDER]) or ""), True)
    # ⚠ r1 Codex M5: a STRING coerces to True and erases a miss.
    case("a non-bool ranker_hit is refused rather than coerced",
         "not a bool" in (validate_row({**_good, "ranker_hit": "false"}) or ""), True)
    case("...and a real bool is accepted",
         validate_row({**_good, "ranker_hit": False}), None)
    # ⚠ r1 Codex M7: a `null` JSONL line decoded, then raised TypeError out of main().
    case("a non-object row is NAMED rather than raising",
         _try(lambda: validate_row(None)), "a row is NoneType, not an object")

    # ── PROVENANCE: a retroactive row is not a scoreable bet (r7 Codex H1/M2/M3) ─────────────
    # ⛔⛔ ONE CAUSE, THREE DOORS, AND THE PROSE DISCLAIMER WAS NOT ONE OF THEM. Writing the
    # deferral's real history required rows whose outcomes were ALREADY KNOWN. Those rows say so
    # in `prediction`, and r7 proved a trigger cannot read prose: they entered the population of
    # every trigger that treats a SCORED row as a bet placed in advance. Measured before the fix
    # — t3 went from firing to QUIET, t4 from firing to QUIET, and t7 reported an accuracy bound
    # over a sample of 10 when only 8 predictions existed. So provenance is a FIELD now.
    _retro = {"subject": "r", "unit": "u", "route": "accrete", "outcome": "continued",
              "retroactive": True}
    case("a retroactive flag must be a bool — a string coerces to True and hides a real bet",
         "not a bool" in (validate_row({**_good, "retroactive": "false"}) or ""), True)
    case("...and a real bool is accepted", validate_row({**_good, "retroactive": True}), None)
    case("prospective() drops a retroactive row and keeps the rest, in order",
         [r["subject"] for r in prospective(
             [{"subject": "a"}, _retro, {"subject": "b"}])], ["a", "b"])
    # A SECOND, DISTINCT input: an explicit false is a PROSPECTIVE row, not a missing flag.
    case("...and an explicit retroactive: false is prospective, like an absent flag",
         len(prospective([{"subject": "a", "retroactive": False}, {"subject": "b"}])), 2)

    # ⟳ 2026-10-23: the two route-collapse provenance cases left with their trigger. The same
    # property — a retroactive row cannot stand in for a bet — is now asked of trigger 3 by
    # "a RETROACTIVE bet is not a bet, so nothing is owed after it". (r1 F3: an earlier pointer
    # here named a case over a log `main()` refuses; that case is gone.)

    _t4base = [{"subject": f"x{i}", "unit": "u", "route": "accrete", "outcome": "stopped",
                "rounds_at_termination": r} for i, r in enumerate([4, 4, 4, 1, 1])]
    case("⭐ a retroactive termination cannot DISPLACE a subject out of t4's last-five window",
         "ceremony" in (t4_no_improvement(_t4base + [
             {**_retro, "route": "defer", "outcome": "stopped",
              "rounds_at_termination": 2}], 4) or ""), True)
    case("...while a prospective termination DOES enter that window",
         t4_no_improvement(_t4base + [{"subject": "p", "unit": "u", "route": "accrete",
                                       "outcome": "stopped",
                                       "rounds_at_termination": 1}], 4), None)

    # ⛔ t7's SAMPLE IS RANKER PREDICTIONS, NOT SCORED ROWS — t5's own rule, which t7 failed to
    # borrow. The bound it quotes (37% -> 74%) is about the RANKER's accuracy, so a row that
    # made no prediction cannot be in its denominator. One rule, one place.
    _pred = [{"subject": f"p{i}", "unit": "u", "route": "accrete", "outcome": "continued",
              "ranker_hit": True} for i in range(10)]
    # ⛔ _try IS LOAD-BEARING HERE, and the sweep proved it: with the eligibility test removed,
    # `hits = sum(... r["ranker_hit"])` raises KeyError on these deliberately prediction-free
    # rows, the suite died by TRACEBACK, and the harness reported "RED but nothing could see the
    # kill". A crash names nothing — the contract is red VIA THE NAMED CASE.
    case("⭐ ten scored rows that made NO ranker prediction do not reach t7's floor",
         _try(lambda: t7_sample_reached([{"outcome": "stopped"}] * 10)), None)
    case("...and ten explicit ranker predictions do",
         "74%" in (t7_sample_reached(_pred) or ""), True)
    case("...and the hit count is of PREDICTIONS, so a miss is not read as a hit",
         "(9 ranker hits)" in (t7_sample_reached(
             _pred[:9] + [{**_pred[0], "subject": "miss", "ranker_hit": False}]) or ""), True)
    case("a retroactive row does not enter t7's sample either",
         t7_sample_reached(_pred[:9] + [{**_retro, "ranker_hit": True}]), None)

    # ⚠ r7 Codex M4: an existing boundary defect in the function this change touched.
    case("a malformed routes_tried is NAMED rather than raising",
         _try(lambda: validate_row({**_good, "routes_tried": None}, [])),
         "routes_tried is NoneType, not a list — it is DERIVED now and need not be written")
    case("...and every malformed shape reports rather than crashing the caller",
         [("RAISED" in str(_try(lambda rt=rt: validate_row(
             {**_good, "routes_tried": rt}, [])))) for rt in (None, False, 7, "accrete")],
         [False, False, False, False])

    # ── the DECLARED SKIP (backlog #321) ─────────────────────────────────────────────────────
    # ⭐ THE OWNER'S CHANGE. The log used to refuse every non-prefix route, so the two units
    # whose history deviated from the ladder — the two where a human judged a rung futile — were
    # the only ones it could not express, and `all triggers quiet` was CAUSED by their omission.
    # A skip is now recordable WITH A REASON, which is what turns a deviation into a labelled
    # example: shape X, human judged accrete/redesign futile, went to S, outcome Y.
    _skip = {"subject": "s", "unit": "u", "route": "defer",
             "skipped": ["accrete", "redesign", "split"],
             "why_skipped": "the owner deferred the unit (backlog #327)"}
    case("⭐ a declared skip with a non-empty reason is ACCEPTED — the truth is recordable",
         validate_row(_skip, []), None)
    # ⛔ THE DISCRIMINATING NEGATIVE. Without it this change is indistinguishable from deleting
    # the prefix rule: the same route on the same history must STILL be refused undeclared.
    case("⛔ ...and the SAME route on the SAME history is still refused UNDECLARED",
         validate_row({k: v for k, v in _skip.items()
                       if k not in ("skipped", "why_skipped")}, []),
         "route 'defer' is not the next route for ('s', 'u'): tried [], so the only route left "
         "to bet on is 'accrete' — a deliberate skip is recordable: declare skipped "
         "['accrete', 'redesign', 'split'] with a non-empty why_skipped")
    case("an EMPTY reason is refused, exactly as an empty NO-REVIEW: is",
         validate_row({**_skip, "why_skipped": ""}, []),
         "why_skipped is '' — a declared skip needs a NON-EMPTY reason, the same refusal "
         "check-review-recorded makes of an empty NO-REVIEW:")
    # ⚠ ADJACENT, not absurd: whitespace is the near-miss a `not why` test passes and a
    # `len(why)` test does not.
    case("...and a WHITESPACE reason is refused too, not read as present",
         "NON-EMPTY reason" in (validate_row({**_skip, "why_skipped": "   "}, []) or ""), True)
    case("...and an ABSENT reason is refused by its own repr, a separate state from empty",
         validate_row({k: v for k, v in _skip.items() if k != "why_skipped"}, []),
         "why_skipped is None — a declared skip needs a NON-EMPTY reason, the same refusal "
         "check-review-recorded makes of an empty NO-REVIEW:")
    case("a skipped list that does not name the rungs actually skipped is refused",
         validate_row({**_skip, "skipped": ["accrete"]}, []),
         "skipped ['accrete'] does not name the rungs this row skips: "
         "['accrete', 'redesign', 'split'] — the declaration must match the ladder gap, "
         "not assert one")
    case("a skipped STRING is refused rather than read character by character",
         "does not name the rungs" in (
             validate_row({**_skip, "skipped": "accrete"}, []) or ""), True)
    # ⭐ The gap is the UNTRIED rungs before the route, not the whole prefix — a unit that
    # really tried accrete and then skipped redesign declares ONE rung, not two.
    _tried_a = [{"subject": "s", "unit": "u", "route": "accrete", "outcome": "continued"}]
    case("the gap a skip declares is the UNTRIED rungs before it, not the whole prefix",
         validate_row({"subject": "s", "unit": "u", "route": "split",
                       "skipped": ["redesign"], "why_skipped": "a seam was already present"},
                      _tried_a), None)
    case("...so re-declaring a rung that WAS tried is refused",
         "does not name the rungs" in (validate_row(
             {"subject": "s", "unit": "u", "route": "split",
              "skipped": ["accrete", "redesign"], "why_skipped": "x"}, _tried_a) or ""), True)
    # ⚠ A SECOND, DISTINCT INPUT to the gap computation: with an EARLIER skip in the history
    # the two producers disagree, which is the only input that can show which one it reads.
    case("the gap excludes rungs an EARLIER skip already passed, not only the tried ones",
         validate_row({"subject": "s", "unit": "u", "route": "defer", "skipped": ["split"],
                       "why_skipped": "no separable parts left to split"},
                      [{"subject": "s", "unit": "u", "route": "redesign",
                        "skipped": ["accrete"], "why_skipped": "no case handler could fit",
                        "outcome": "continued"}]), None)
    # ⛔⛔ A RETRY IS NOT A SKIP. `LADDER[:index('accrete')]` is empty, so a naive implementation
    # accepts `skipped: []` with any reason and the repeat — which the design calls the
    # escalation TRIGGER, not a step — becomes expressible again through the new door.
    case("⛔ a RETRY is not a skip: no reason declares a repeat into a step",
         validate_row({"subject": "s", "unit": "u", "route": "accrete", "skipped": [],
                       "why_skipped": "I would like to try that again"}, _tried_a),
         "route 'accrete' is not the next route for ('s', 'u'): tried ['accrete'], so the only "
         "route left to bet on is 'redesign' — and 'accrete' is ALREADY TRIED, so this is a "
         "RETRY, not a skip: a repeat is the escalation trigger, not a step, and no reason "
         "declares it into one")
    case("a skip claimed on a row that skips NOTHING is refused rather than ignored",
         validate_row({"subject": "s", "unit": "u", "route": "accrete",
                       "skipped": ["redesign"], "why_skipped": "x"}, []),
         "skipped ['redesign'] / why_skipped claim a skip, but 'accrete' IS the next route for "
         "('s', 'u') — nothing was skipped")
    # ⛔ THE APPENDABILITY CASE. A declared skip that poisoned the unit's own future rows would
    # reproduce the defect this change exists to remove: the row would be accepted and then
    # nothing could ever follow it, because the history would read as a non-prefix.
    _after_skip = [{"subject": "s", "unit": "u", "route": "split",
                    "skipped": ["accrete", "redesign"], "why_skipped": "x",
                    "outcome": "continued"}]
    case("⭐ the unit stays APPENDABLE after a declared skip — the history is still a prefix",
         validate_row({"subject": "s", "unit": "u", "route": "defer"}, _after_skip), None)
    # ⛔ THIS CASE WAS TOO WEAK AND A MUTATION SURVIVED IT: with the walk-back branch removed
    # the refusal still CONTAINED "is not the next route", because the row fell through to the
    # declaration message. Identity on the whole string is what distinguishes the two.
    case("...and the rung BELOW a declared skip cannot be walked back to",
         validate_row({"subject": "s", "unit": "u", "route": "redesign"}, _after_skip),
         "route 'redesign' is not the next route for ('s', 'u'): tried ['split'], so the only "
         "route left to bet on is 'defer' — and 'redesign' was already PASSED by a declared "
         "skip, so this is a WALK-BACK down the ladder, which escalation does not do")
    # ⭐ AND A WALK-BACK IS NOT DECLARABLE. Its gap is EMPTY, so without the branch above a
    # `skipped: []` with any reason would match and the row would be ACCEPTED — backtracking
    # through the new door, which §3.4 of the approved change rules out.
    case("...and no declaration makes a walk-back expressible, because its gap is empty",
         "WALK-BACK" in (validate_row(
             {"subject": "s", "unit": "u", "route": "redesign", "skipped": [],
              "why_skipped": "I would rather restructure after all"}, _after_skip) or ""), True)
    # ⛔ AN INDEPENDENT COPY, NOT A LOOP OVER THE SUBJECT. A case that iterates LADDER shrinks
    # when a rung is removed instead of reddening (memory: a class fix needs an independent copy).
    case("the ladder is PINNED to a literal, so reordering or extending it reddens by name",
         LADDER, ("accrete", "redesign", "split", "defer"))

    # ── H3: hindsight may fill a unit's PAST, never follow a real bet ─────────────────────────
    _live_first = [{"subject": "s", "unit": "u", "route": "accrete", "outcome": "continued"}]
    case("⭐ a retroactive row may NOT follow a prospective bet — door (c) is irreversible",
         validate_row({"subject": "s", "unit": "u", "route": "redesign", "retroactive": True},
                      _live_first),
         "a retroactive row may not follow a PROSPECTIVE bet on ('s', 'u') — hindsight appended "
         "after a real bet closes that unit's ladder and empties its scoring population, and an "
         "append-only log cannot take it back")
    # ⚠ ADJACENT, and this is the shape the LIVE log has: backfilling a unit whose history is
    # entirely hindsight is exactly what the schema change exists to permit.
    case("...while hindsight after hindsight is a BACKFILL, which is the permitted case",
         validate_row({"subject": "s", "unit": "u", "route": "redesign", "retroactive": True},
                      [{"subject": "s", "unit": "u", "route": "accrete", "outcome": "continued",
                        "retroactive": True}]), None)
    case("...and a PROSPECTIVE row after a prospective bet is untouched by the rule",
         validate_row({"subject": "s", "unit": "u", "route": "redesign"}, _live_first), None)

    # ⚠ r7 Claude L11: the fold re-introduced, in the function it ADDED, the class it had just
    # fixed one function away — `prospective([None])` raised AttributeError.
    case("prospective() NAMES nothing and raises nothing on a non-dict row",
         _try(lambda: len(prospective([None, {"subject": "a"}, 7]))), 1)
    # ⚠ r7 Claude L12: `list("") == []`, so a string validated as "no routes tried" while the
    # refusal message said "not a list".
    case("a routes_tried STRING is refused, so the message it prints is true",
         validate_row({**_good, "routes_tried": ""}, []),
         "routes_tried is str, not a list — it is DERIVED now and need not be written")

    # ── t4 composition + t9: backlog #337's cheap half, mechanised ────────────────────────────
    def _term(sub, rounds, route="accrete"):
        return {"subject": sub, "unit": "u", "route": route, "outcome": "stopped",
                "rounds_at_termination": rounds}
    case("⭐ when t4 fires, its message says how much of the median was DEFERRAL",
         "⚠ 2 of those 5 terminations were DEFERRALS, which are filings rather than repairs" in
         (t4_no_improvement([_term(f"a{i}", 9) for i in range(3)]
                            + [_term("d1", 9, "defer"), _term("d2", 9, "defer")], 4) or ""), True)
    case("...and with no deferral in the window it says nothing extra",
         "DEFERRALS" in (t4_no_improvement([_term(f"b{i}", 9) for i in range(5)], 4) or ""),
         False)
    # ⭐ THE MASKING SHAPE #337 IS ABOUT: t4 is QUIET because the median looks good, and the
    # reason it looks good is that deferrals are in the window.
    case("⭐ t9 names a median composed of deferrals, which is where #337 is invisible",
         "read this median as at most 3 of 5 repairs" in (t9_deferral_composed(
             [_term(f"c{i}", 1) for i in range(3)]
             + [_term("d1", 1, "defer"), _term("d2", 1, "defer")], 4) or ""), True)
    case("...and it stays quiet when t4 is already FIRING, so one window has one verdict",
         t9_deferral_composed([_term(f"e{i}", 9) for i in range(3)]
                              + [_term("d1", 9, "defer"), _term("d2", 9, "defer")], 4), None)
    case("...and quiet when the good median is made of real repairs",
         t9_deferral_composed([_term(f"f{i}", 1) for i in range(5)], 4), None)
    case("...and a RETROACTIVE deferral cannot compose the window either",
         t9_deferral_composed([_term(f"g{i}", 1) for i in range(5)]
                              + [{**_term("rd", 1, "defer"), "retroactive": True}], 4), None)
    # ⛔ THE BASELINE IS A PARAMETER, NOT A CONSTANT, and `check-fixture-variation` caught that
    # all four call sites above pass `4` — so no case could tell the comparator apart from a
    # literal and every clause reading it was unguarded. A SECOND, DISTINCT value, chosen so the
    # verdict FLIPS on it: the same window is composed-and-quiet at a baseline of 7 and owned by
    # t4 at a baseline of 1.
    _mixed_window = [_term(f"h{i}", 2) for i in range(3)] + [_term("d1", 2, "defer"),
                                                             _term("d2", 2, "defer")]
    case("the baseline is a COMPARATOR: the same window flips verdict when it moves",
         ("composed" if t9_deferral_composed(_mixed_window, 7) else "quiet",
          "composed" if t9_deferral_composed(_mixed_window, 1) else "quiet"),
         ("composed", "quiet"))
    # ⚠ r7 Codex: `"!!!"` and a zero-width space satisfied "non-empty". `strip()` does not
    # remove U+200B, so the whitespace rule could never have caught it. NON-EMPTY IS NOT
    # EXPLANATORY — the reason is the deliverable, so it must carry at least some content.
    case("a punctuation-only reason is refused — non-empty is not the same as explanatory",
         "no alphanumeric content" in (validate_row(
             {**_skip, "why_skipped": "!!!"}, []) or ""), True)
    case("...and a zero-width space is refused too, which strip() does NOT remove",
         "no alphanumeric content" in (validate_row(
             {**_skip, "why_skipped": "\u200b"}, []) or ""), True)
    case("...while a short but real reason is accepted — the rule is content, not length",
         validate_row({**_skip, "why_skipped": "zero measured benefit"}, []), None)

    def _r2(n, *comps):
        return {"round": n, "findings": [{"component": c} for c in comps]}

    # ── derive_outcome: POSITION, not count (r2 YL7) ─────────────────────────────────────────
    case("component_rounds gives the SET of rounds, which is what a position question needs",
         component_rounds([_r2(1, "a", "b"), _r2(5, "a")]), {"a": {1, 5}, "b": {1}})
    case("a round with no usable number contributes nothing rather than a None key",
         component_rounds([{"round": "x", "findings": [{"component": "a"}]}]), {})
    # ⭐⭐ r2 YL7, THE EXACT INPUT: rounds 1 and 5, asking about round 4. The count-based version
    # computed `2 > 4` and answered "stopped" while round 5 proves continuation.
    case("⭐ a component in rounds 1 and 5 CONTINUED past round 4 — a count said stopped",
         derive_outcome("s", "a", 4, {"a": {1, 5}}), "continued")
    case("...and after round 5 it has stopped, so the boundary is read from the SET",
         derive_outcome("s", "a", 5, {"a": {1, 5}}), "stopped")
    case("an unknown unit is NOT DERIVABLE rather than assumed stopped",
         derive_outcome("s", "u", 2, {"other": {5}}), None)
    case("no evidence at all is NOT DERIVABLE — 10 of 81 subjects are readable",
         derive_outcome("s", "u", 2, None), None)
    case("the subject is carried, and the evidence it is given is what decides",
         (derive_outcome("other-subject", "a", 1, {"a": {2}}),
          derive_outcome("s", "a", 1, {"a": {2}})), ("continued", "continued"))

    # ── _corpus_now: the handler, the empty path, and the partial traversal ──────────────────
    # ⛔ THIS BLOCK WAS DELETED BY A MECHANICAL EDIT AND RESTORED. A replacement keyed on the
    # markers either side of the derive_outcome cases took these with it; the case count fell
    # 127 -> 119 and I wrote a sentence explaining that away. Five mutations then SURVIVED,
    # which is how it surfaced. The lesson is not "be careful" — it is that a region replacement
    # must assert what it is NOT supposed to remove, and the mutation probe is what noticed.
    with _tf.TemporaryDirectory() as _cd:
        _missing = Path(_cd) / "nope"
        _err = _corpus_now(_missing)
        case("a corpus directory that is not there is an ERROR, not an empty corpus",
             (_err.get("median"), bool(_err.get("error"))), (None, True))
        case("...and the message NAMES the path, so the remedy is not guessed at",
             "nope" in _err.get("error", ""), True)
        # ⛔ WHY THE is_dir GUARD IS NOT REDUNDANT, and a surviving mutation is what showed it.
        # For a MISSING directory the `os.walk` check also refuses. For a path that is a FILE,
        # walk yields nothing and calls `onerror` not at all — so without `is_dir` it reads as
        # an EMPTY CORPUS, a different remedy entirely.
        _file = Path(_cd) / "a-file.md"
        _file.write_text("not a directory")
        _ferr = _corpus_now(_file)
        case("a corpus path that is a FILE says so, rather than reading as an empty corpus",
             ("not a directory" in _ferr.get("error", ""),
              "no subject" in _ferr.get("error", "")), (True, False))
        (Path(_cd) / "empty").mkdir()
        _empty = _corpus_now(Path(_cd) / "empty")
        # ⚠ r1 Claude L1: this path is reached with NO EXCEPTION AT ALL and returns the same
        # shape as the handler, which is why `main()` keys on `error` and not on the handler.
        case("a corpus with no qualifying subject is an ERROR too, reached with no exception",
             (_empty.get("median"), _empty.get("error")),
             (None, "no subject has >=2 rounds"))
        # ⭐⭐ r2 YH1: `Path.rglob` SILENTLY SKIPS a directory it cannot read, so a partial
        # traversal produced a count with NO error key and `main()` printed `all triggers
        # quiet`, rc=0. ⚠ Running as root reads it anyway, so this accepts either the refusal
        # or the full count and asserts only that a PARTIAL count is impossible.
        import os as _os2
        (Path(_cd) / "part" / "codex").mkdir(parents=True)
        (Path(_cd) / "part" / "claude").mkdir()
        for _n in (1, 2, 3, 4):
            (Path(_cd) / "part" / "codex" / f"a-r{_n}-codex.md").write_text("x")
        for _n in range(1, 9):
            (Path(_cd) / "part" / "claude" / f"b-r{_n}-claude.md").write_text("x")
        _os2.chmod(Path(_cd) / "part" / "claude", 0o000)
        _part = _corpus_now(Path(_cd) / "part")
        _os2.chmod(Path(_cd) / "part" / "claude", 0o700)
        case("an unreadable SUBTREE refuses, or reads fully — never a partial count",
             (bool(_part.get("error")) or _part.get("subjects") == 2), True)
        case("...and a partial count with NO error is exactly what must not happen",
             (_part.get("subjects") == 1 and not _part.get("error")), False)
    with _tf.TemporaryDirectory() as _cd2:
        (Path(_cd2) / "real2" / "coordinator").mkdir(parents=True)
        for _n in (1, 2, 3):
            (Path(_cd2) / "real2" / "coordinator" / f"z-r{_n}-coordinator.md").write_text("x")
        case("a corpus with one two-round subject reports figures and NO error",
             (_corpus_now(Path(_cd2) / "real2").get("median"),
              _corpus_now(Path(_cd2) / "real2").get("subjects"),
              _corpus_now(Path(_cd2) / "real2").get("error")), (3, 1, None))
        # TWO DISTINCT corpora yielding DIFFERENT figures, so the parameter is not a constant.
        # ⚠ The first attempt pointed the second read at `real2/coordinator`, which still holds
        # the documents and still parses — so both reads returned the same answer and the case
        # could not tell the parameter from a constant. Two corpora with different CONTENT is
        # what the rule actually needs.
        (Path(_cd2) / "two" / "coordinator").mkdir(parents=True)
        for _n in (1, 2):
            (Path(_cd2) / "two" / "coordinator" / f"y-r{_n}-coordinator.md").write_text("x")
        case("the corpus it is GIVEN is the one it reads",
             (_corpus_now(Path(_cd2) / "real2").get("median"),
              _corpus_now(Path(_cd2) / "two").get("median")), (3, 2))

    # ── read_log: an unreadable file is CANNOT RUN, not an empty log ──────────────────────────
    with _tf.TemporaryDirectory() as _pd:
        _noperm = Path(_pd) / "locked.jsonl"
        _noperm.write_text('{"a": 1}\n')
        import os as _os3
        _os3.chmod(_noperm, 0o000)
        _res = _try(lambda: read_log(_noperm))
        _os3.chmod(_noperm, 0o600)
        # ⛔ r1 Codex M7: a PermissionError escaped main()'s `except ValueError` and gave a
        # traceback with rc=1 — a process failure dressed as a verdict. Running as root reads
        # the file anyway, so this accepts either outcome and asserts only that it is NOT a
        # silently-empty log.
        case("an unreadable log raises ValueError (or reads) — never a silent empty log",
             _res in ("RAISED ValueError", [{"a": 1}]), True)

    # ── the log reader: absence vs unreadability ─────────────────────────────────────────────
    case("an absent log is empty, which is honest on day one",
         read_log(REPO / "docs/reviews/decision-scheme/does-not-exist.jsonl"), [])
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "l.jsonl"
        p.write_text('{"a": 1}\n\n# a comment\n{"a": 2}\n')
        case("blank lines and comments are skipped, data is not", read_log(p),
             [{"a": 1}, {"a": 2}])
        p.write_text('{"a": 1}\nnot json\n')
        try:
            read_log(p)
            got = "no raise"
        except ValueError as exc:
            got = "raised"
        # ⛔ A LOG THAT CANNOT BE READ IS NOT AN EMPTY LOG. Returning [] here would turn a
        # corrupt file into "nothing has happened yet", which is the vacuous pass this
        # repository keeps measuring.
        case("a malformed line RAISES rather than reading as an empty log", got, "raised")

    # ── main(): the ASSEMBLY, driven over a world the case BUILDS (ADR-0014 D1) ──────────────
    # ⛔ WHY main() IS DRIVEN AND NOT PINNED IN MAIN_DEBT. Every predicate above is covered, and
    # the assembly is where a WARNING silently becoming a FAILURE would hide — nothing below the
    # exit code distinguishes those two.
    #
    # ⚠ THE SHAPE IS NOT DECORATION, AND TWO GUARDS DISAGREED ABOUT IT UNTIL IT WAS RIGHT.
    #   * `check-fixture-variation.py` reads CALL SITES, so routing all eight cases through one
    #     `_run(...)` wrapper made every parameter look like a constant — correctly.
    #   * `check-main-drivable.py` requires the world to be BUILT IN THE CASE'S OWN SCOPE; a
    #     helper's return value is opaque to it, and a `lambda:` wrapper hides the binding. It
    #     saw 8 calls and credited none, twice, before the files were constructed inline.
    # Taking either guard's escape hatch would have contradicted the rule I filed this morning
    # in #315-#317: an escape is not a destination.
    import contextlib, io, json as _json, tempfile as _tf2

    _ARMED = {"rounds_to_termination": {"median": 4},
              "armed_at": "2026-10-20T10:00:00-07:00",
              "corpus": {"subjects_with_ge2_rounds": 57}}
    with _tf2.TemporaryDirectory() as _wd:
        _bp_quiet = Path(_wd) / "quiet-baseline.json"
        _bp_quiet.write_text(_json.dumps(_ARMED))
        _lp_quiet = Path(_wd) / "quiet-log.jsonl"
        _lp_quiet.write_text("".join(_json.dumps(r) + "\n" for r in []))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_quiet, log_path=_lp_quiet,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("an armed, quiet world exits 0 and SAYS it is quiet",
             (_rc, "all triggers quiet" in _o), (0, True))
        # ⛔ THE SUMMARY LINE IS THE ONE NUMBER A READER SEES, and r7 Claude M7 found it
        # un-split: "4 scored" while every scoring trigger computed over 2. A hand-sever of the
        # split SURVIVED the suite because the fix had no case — the fold's own recurring defect,
        # found a third time in one round. Identity on the whole line, over a log that actually
        # contains a retroactive row, is what holds it.
        _bp_prov = Path(_wd) / "prov-baseline.json"
        _bp_prov.write_text(_json.dumps(_ARMED))
        _lp_prov = Path(_wd) / "prov-log.jsonl"
        _lp_prov.write_text("".join(_json.dumps(r) + "\n" for r in [
            # ⟳ 2026-10-23: `stopped`, not `continued` — a lone continued bet now FAILS trigger 3,
            # and this case is about the summary line of a QUIET run.
            {"subject": "live", "unit": "u", "route": "accrete", "outcome": "stopped",
             "rounds_at_termination": 3},
            {"subject": "hist", "unit": "u", "route": "accrete", "outcome": "stopped",
             "rounds_at_termination": 2, "retroactive": True}]))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_prov, log_path=_lp_prov,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("the summary line SPLITS the provenance, so `all triggers quiet` is readable",
             (_rc, _o.splitlines()[0]),
             (0, "decision-scheme: 2 row(s), 2 scored (1 retroactive, so 1 scoreable); "
                 "pinned median 4 vs now 4"))
        # ⚠ ADJACENT: with NO retroactive row the line must still read correctly — a fix that
        # reports "0 retroactive" wrongly, or drops the clause, is caught here rather than later.
        _bp_prov2 = Path(_wd) / "prov2-baseline.json"
        _bp_prov2.write_text(_json.dumps(_ARMED))
        _lp_prov2 = Path(_wd) / "prov2-log.jsonl"
        _lp_prov2.write_text("".join(_json.dumps(r) + "\n" for r in [
            {"subject": "live", "unit": "u", "route": "accrete", "outcome": "continued"}]))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_prov2, log_path=_lp_prov2,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("...and a log with no retroactive row says so rather than omitting the clause",
             _o.splitlines()[0],
             "decision-scheme: 1 row(s), 1 scored (0 retroactive, so 1 scoreable); "
             "pinned median 4 vs now 4")
        # ⛔⛔ THE WIRING, AND THREE MUTATIONS SURVIVED WITHOUT IT. The cases above exercise
        # `pinned_inventory` directly; none proved that `main()` READS the pin and HANDS IT to the
        # starver. A double that records its kwarg is the only thing that can say so.
        _seen = {}
        def _record(since, before_rounds=None):
            _seen["before_rounds"] = before_rounds
            return [], None
        _bp_pin = Path(_wd) / "pin-baseline.json"
        _bp_pin.write_text(_json.dumps({**_ARMED, "rounds_at_arming": [["s", 1], ["s", 2]]}))
        _lp_pin = Path(_wd) / "pin-log.jsonl"
        _lp_pin.write_text("")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_pin, log_path=_lp_pin,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=_record)
        case("⭐ main() READS the pinned inventory and HANDS IT to the starver",
             (_rc, _seen.get("before_rounds")), (0, {("s", 1), ("s", 2)}))
        # ⛔ A MALFORMED pin is CANNOT RUN, not a silent fallback to git archaeology — falling
        # back is what a squash makes wrong, so a pin that cannot be read must stop the run.
        _bp_bad = Path(_wd) / "badpin-baseline.json"
        _bp_bad.write_text(_json.dumps({**_ARMED, "rounds_at_arming": "s,1"}))
        _lp_bad = Path(_wd) / "badpin-log.jsonl"
        _lp_bad.write_text("")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_bad, log_path=_lp_bad,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=_record)
        _o = _buf.getvalue()
        case("⛔ a MALFORMED pin is CANNOT RUN (2), never a quiet fallback to git",
             (_rc, "NOT CHECKED" in _o), (2, True))
        case("...and an ABSENT pin still runs, so a repo that has not pinned one is not broken",
             main([], baseline_path=_bp_quiet, log_path=_lp_quiet,
                  corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                  starved=_record), 0)
        # ⛔⛔ THE INERT-WIRING DEFECT, FOUND IN MY OWN WORK BY r8 Codex M1 — and this file
        # already carries a comment reading "THE CASE THAT WOULD HAVE CAUGHT THE INERT WIRING,
        # AND DID NOT EXIST". I added two triggers and wire-tested neither: MEASURED, replacing
        # either call site with `None` left 201/201 GREEN, so the pure-function cases proved only
        # that the functions compute, never that their verdict REACHES A READER.
        _bp_hind = Path(_wd) / "hind-baseline.json"
        _bp_hind.write_text(_json.dumps(_ARMED))
        _lp_hind = Path(_wd) / "hind-log.jsonl"
        _lp_hind.write_text("".join(_json.dumps(r) + "\n" for r in [
            {"subject": "ghost", "unit": "u", "route": "accrete", "outcome": "continued",
             "retroactive": True}]))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_hind, log_path=_lp_hind,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=lambda since, **_: (["ghost"], None))
        _o = _buf.getvalue()
        case("⭐ trigger 8's verdict REACHES the CLI as a WARN, and does not fail the run",
             (_rc, "WARN  trigger 8 HINDSIGHT ONLY" in _o, "fed ONLY in hindsight: ghost" in _o),
             (0, True, True))
        _bp_comp = Path(_wd) / "comp-baseline.json"
        _bp_comp.write_text(_json.dumps(_ARMED))
        _lp_comp = Path(_wd) / "comp-log.jsonl"
        _lp_comp.write_text("".join(_json.dumps(r) + "\n" for r in [
            {"subject": "p1", "unit": "u", "route": "accrete", "outcome": "stopped",
             "rounds_at_termination": 1},
            {"subject": "p2", "unit": "u", "route": "accrete", "outcome": "stopped",
             "rounds_at_termination": 1},
            {"subject": "p3", "unit": "u", "route": "accrete", "outcome": "stopped",
             "rounds_at_termination": 1},
            {"subject": "p4", "unit": "u", "route": "defer", "outcome": "stopped",
             "rounds_at_termination": 1, "skipped": ["accrete", "redesign", "split"],
             "why_skipped": "filed rather than repaired"},
            {"subject": "p5", "unit": "u", "route": "defer", "outcome": "stopped",
             "rounds_at_termination": 1, "skipped": ["accrete", "redesign", "split"],
             "why_skipped": "filed rather than repaired"}]))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_comp, log_path=_lp_comp,
                       corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("⭐ trigger 9's verdict REACHES the CLI too, naming how many were deferrals",
             (_rc, "WARN  trigger 9 DEFERRAL COMPOSED" in _o,
              "at most 3 of 5 repairs" in _o), (0, True, True))
        # ⛔ TRIGGER 3 AND ITS WARN HALF, WIRE-TESTED — the same lesson as trigger 8 and 9 above:
        # a pure-function case proves the rule computes, never that its verdict REACHES a reader.
        # The pins arrive through the BASELINE, the way `main()` reads them.
        def _run_log(tag, log_rows, pins=None):
            _bp = Path(_wd) / f"{tag}-baseline.json"
            _bp.write_text(_json.dumps({**_ARMED, **({PRE_TRIGGER_PINS: pins}
                                                     if pins is not None else {})}))
            _lp = Path(_wd) / f"{tag}-log.jsonl"
            _lp.write_text("".join(_json.dumps(r) + "\n" for r in log_rows))
            _b2 = io.StringIO()
            with contextlib.redirect_stdout(_b2):
                _r = _try(lambda: main([], baseline_path=_bp, log_path=_lp,
                                       corpus=lambda: {"median": 4, "mean": 4.6,
                                                       "subjects": 57},
                                       starved=lambda since, **_: ([], None)))
            return _r, _b2.getvalue()
        _rc, _o = _run_log("lost", [_b("lost", "u", "accrete", "continued")])
        case("⭐ trigger 3's verdict REACHES the CLI as a FAIL and fails the run",
             (_rc, "FAIL  trigger 3 LOST BET NOT ESCALATED" in _o, "(lost/u)" in _o),
             (1, True, True))
        # ⟳ r5: a CLOSED exhausted unit reaches the CLI as trigger 11's WARN, and the run exits 0.
        _rc, _o = _run_log("closed", [_b("closed", "u", r, "continued") for r in LADDER[:-1]]
                           + [_b("closed", "u", "defer", "continued", rounds_at_termination=4)])
        case("⭐ a CLOSED exhausted unit reaches the CLI as trigger 11's WARN and exits 0",
             (_rc, "WARN  trigger 11 LADDER EXHAUSTED, CLOSED" in _o, "FAIL" in _o),
             (0, True, False))
        _rc, _o = _run_log("restart", [_b("restart", "u", r, "continued") for r in LADDER[:-1]]
                           + [_b("restart", "u", "defer", "continued", rounds_at_termination=4),
                              _b("restart", "u-new", "accrete")])
        case("⭐ a restarted ladder reaches the CLI as trigger 12's WARN and exits 0",
             (_rc, "WARN  trigger 12 LADDER RESTARTED" in _o, "FAIL" in _o), (0, True, False))
        _rc, _o = _run_log("pinned", [_b("pinned", "u", "accrete", "continued")],
                           [{"subject": "pinned", "unit": "u", "route": "accrete",
                             "reason": "predates trigger 3"}])
        case("⭐ a PINNED lost bet reaches the CLI as trigger 10's WARN and exits 0",
             (_rc, "WARN  trigger 10 PRE-TRIGGER LOST BET" in _o, "FAIL" in _o),
             (0, True, False))
        _rc, _o = _run_log("badpin", [_b("badpin", "u", "accrete", "continued")],
                           [{"subject": "badpin", "unit": "u"}])
        case("⛔ a MALFORMED pin list is CANNOT RUN at the CLI, never an empty one",
             (_rc, "CANNOT RUN" in _o, "has no reason" in _o), (2, True, True))
        # ⛔ TRIGGER 4's SUSPENSION, WIRE-TESTED at two DISTINCT medians (at the baseline, and far
        # above it), plus one below it that must stay silent — so the case cannot be satisfied by
        # one fixture's constant, and moving trigger 4 back to the FAIL list reddens it.
        for _tag, _n in (("t4eq", 4), ("t4hi", 9)):
            _rc, _o = _run_log(_tag, [_b(f"{_tag}{i}", "u", "accrete", "stopped",
                                         rounds_at_termination=_n) for i in range(5)])
            # ⟳ r1 Claude M2 / r1 Codex: asserted on trigger 4's OWN line, not the whole output —
            # three suffix edits passed 274/274 when the test read `_o` as a bag of words.
            _t4 = [ln for ln in _o.splitlines() if ln.startswith("  WARN  trigger 4 NO IMPROVEMENT")]
            _l = _t4[0] if len(_t4) == 1 else ""
            case(f"⭐ trigger 4 at median {_n} reaches the CLI as a WARN naming backlog #327, exit 0",
                 (_rc, len(_t4), f"over the last 5 SUBJECTS is {_n}," in _l,
                  "pinned pre-scheme median of 4" in _l, "backlog #327" in _l,
                  _l.endswith("NOT a pass"), "FAIL" in _o), (0, 1, True, True, True, True, False))
        _rc, _o = _run_log("t4lo", [_b(f"t4lo{i}", "u", "accrete", "stopped",
                                       rounds_at_termination=3) for i in range(5)])
        case("...and at median 3, below the baseline, trigger 4 says nothing at all",
             (_rc, "trigger 4" in _o), (0, False))
        # ⛔ r4 Codex Low, at the CLI: a PRESENT null is CANNOT RUN, not "no pins" — measured
        # before the fix, it exited 0 "all triggers quiet" over an empty log.
        _bp_null = Path(_wd) / "nullpin2-baseline.json"
        _bp_null.write_text(_json.dumps({**_ARMED, PRE_TRIGGER_PINS: None}))
        _lp_null = Path(_wd) / "nullpin2-log.jsonl"
        _lp_null.write_text(_json.dumps(_b("np", "u", "accrete", "continued")) + "\n")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = _try(lambda: main([], baseline_path=_bp_null, log_path=_lp_null,
                                    corpus=lambda: {"median": 4, "mean": 4.6, "subjects": 57},
                                    starved=lambda since, **_: ([], None)))
        _o = _buf.getvalue()
        case("⛔ a PRESENT null pin list is CANNOT RUN at the CLI, not an empty exemption list",
             (_rc, "CANNOT RUN" in _o, "is NoneType, not a list" in _o), (2, True, True))
        _bp_starved = Path(_wd) / "starved-baseline.json"
        _bp_starved.write_text(_json.dumps({"rounds_to_termination": {"median": 9}, "armed_at": "2026-01-01T00:00:00Z"}))
        _lp_starved = Path(_wd) / "starved-log.jsonl"
        _lp_starved.write_text("".join(_json.dumps(r) + "\n" for r in []))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_starved, log_path=_lp_starved,
                       corpus=lambda: {"median": 9, "mean": 9.0, "subjects": 60},
                       starved=lambda since, **_: (["alpha", "beta"], None))
        _o = _buf.getvalue()
        case("a STARVED world exits 1 and names trigger 1 first",
             (_rc, "FAIL  trigger 1 NOT FED" in _o, "alpha" in _o), (1, True, True))
        _bp_drift = Path(_wd) / "drift-baseline.json"
        _bp_drift.write_text(_json.dumps(_ARMED))
        _lp_drift = Path(_wd) / "drift-log.jsonl"
        _lp_drift.write_text("".join(_json.dumps(r) + "\n" for r in [{"subject": "s", "unit": "u", "route": "accrete", "routes_tried": [], "outcome": None}]))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_drift, log_path=_lp_drift,
                       corpus=lambda: {"median": 20, "mean": 20.0, "subjects": 57},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("a drifted denominator WARNS and still exits 0 — a warning is not a failure",
             (_rc, "WARN  trigger 6 DENOMINATOR MOVED" in _o, "FAIL" in _o), (0, True, False))
        _bp_badlog = Path(_wd) / "badlog-baseline.json"
        _bp_badlog.write_text(_json.dumps(_ARMED))
        _lp_badlog = Path(_wd) / "badlog-log.jsonl"
        _lp_badlog.write_text('{"a": 1}\nnot json\n')
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_badlog, log_path=_lp_badlog,
                       corpus=lambda: {"median": 5, "mean": 5.0, "subjects": 12},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("an unreadable log is CANNOT RUN and names the line",
             (_rc, "CANNOT RUN" in _o), (2, True))
        _bp_badrow = Path(_wd) / "badrow-baseline.json"
        _bp_badrow.write_text(_json.dumps(_ARMED))
        _lp_badrow = Path(_wd) / "badrow-log.jsonl"
        _lp_badrow.write_text("".join(_json.dumps(r) + "\n" for r in [{"subject": "s", "unit": "u", "route": "rewrite", "routes_tried": []}]))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_badrow, log_path=_lp_badrow,
                       corpus=lambda: {"median": 3, "mean": 3.0, "subjects": 9},
                       starved=lambda since, **_: (["delta"], None))
        _o = _buf.getvalue()
        case("an unusable ROW is CANNOT RUN, so no trigger is evaluated over bad data",
             (_rc, "no trigger was evaluated" in _o), (2, True))
        _bp_unarmed = Path(_wd) / "unarmed-baseline.json"
        _bp_unarmed.write_text(_json.dumps({"rounds_to_termination": {"median": 4}}))
        _lp_unarmed = Path(_wd) / "unarmed-log.jsonl"
        _lp_unarmed.write_text("".join(_json.dumps(r) + "\n" for r in []))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_unarmed, log_path=_lp_unarmed,
                       corpus=lambda: {"median": 4, "mean": 4.1, "subjects": 55},
                       starved=lambda since, **_: (["epsilon"], None))
        _o = _buf.getvalue()
        case("an UNARMED baseline reports NOT YET FED rather than a vacuous all-quiet",
             (_rc, "NOT YET FED" in _o), (0, True))
        # ⛔ r1 Claude M3: a baseline with no median used the literal 4 and called it "pinned".
        _bp_nomed = Path(_wd) / "nomed-baseline.json"
        _bp_nomed.write_text(_json.dumps({"armed_at": "2026-10-20T10:00:00-07:00",
                                          "rounds_to_termination": {}}))
        _lp_nomed = Path(_wd) / "nomed-log.jsonl"
        _lp_nomed.write_text("")
        _buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(_buf):
                _rc = main([], baseline_path=_bp_nomed, log_path=_lp_nomed,
                           corpus=lambda: {"median": 4, "mean": 4.3, "subjects": 81},
                           starved=lambda since, **_: ([], None))
        except Exception as _e:                    # noqa: BLE001 - reported, not swallowed
            _rc = f"RAISED {type(_e).__name__}"
        _o = _buf.getvalue()
        case("a baseline with no median is CANNOT RUN, not a defaulted comparator",
             (_rc, "no numeric" in _o), (2, True))
        _bp_bad = Path(_wd) / "badjson-baseline.json"
        _bp_bad.write_text("{not json")
        _lp_bad = Path(_wd) / "badjson-log.jsonl"
        _lp_bad.write_text("")
        _buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(_buf):
                _rc = main([], baseline_path=_bp_bad, log_path=_lp_bad,
                           corpus=lambda: {"median": 2, "mean": 2.0, "subjects": 3},
                           starved=lambda since, **_: ([], None))
        except Exception as _e:                    # noqa: BLE001 - reported, not swallowed
            _rc = f"RAISED {type(_e).__name__}"
        _o = _buf.getvalue()
        case("an unreadable baseline is CANNOT RUN rather than a traceback",
             (_rc, "unreadable" in _o), (2, True))
        # ⭐⭐ B2's FALSIFIER, on the DEFAULT path — the one CI runs. Before the fold this
        # printed `now=None` and then the positive assertion `all triggers quiet`, rc=0.
        _bp_cerr = Path(_wd) / "cerr-baseline.json"
        _bp_cerr.write_text(_json.dumps(_ARMED))
        _lp_cerr = Path(_wd) / "cerr-log.jsonl"
        _lp_cerr.write_text("")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_cerr, log_path=_lp_cerr,
                       corpus=lambda: {"median": None, "mean": None, "error": "SHAPES went away"},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("a corpus that could not be read is CANNOT RUN on the DEFAULT path, not quiet",
             (_rc, "CANNOT RUN" in _o, "SHAPES went away" in _o, "all triggers quiet" in _o),
             (2, True, True, False))
        # ⛔ AND main() MUST PASS `prior` — a row validated alone cannot be seen to retry.
        _bp_rtry = Path(_wd) / "rtry-baseline.json"
        _bp_rtry.write_text(_json.dumps(_ARMED))
        _lp_rtry = Path(_wd) / "rtry-log.jsonl"
        _lp_rtry.write_text(
            _json.dumps({"subject": "s", "unit": "u", "route": "accrete",
                         "outcome": "continued"}) + "\n"
            + _json.dumps({"subject": "s", "unit": "u", "route": "accrete",
                           "outcome": "continued"}) + "\n")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_rtry, log_path=_lp_rtry,
                       corpus=lambda: {"median": 4, "mean": 4.2, "subjects": 57},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("main() validates each row against ITS UNIT'S history, so a retry is caught",
             (_rc, "row 2" in _o, "left to bet on is 'redesign'" in _o), (2, True, True))
        _bp_nobase = Path(_wd) / "nobase-baseline.json"
        _lp_nobase = Path(_wd) / "nobase-log.jsonl"
        _lp_nobase.write_text("")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_nobase, log_path=_lp_nobase,
                       corpus=lambda: {"median": 2, "mean": 2.0, "subjects": 1},
                       starved=lambda since, **_: (["gamma"], None))
        _o = _buf.getvalue()
        case("a missing pinned baseline is CANNOT RUN, not a pass",
             (_rc, "CANNOT RUN" in _o), (2, True))
        # DISTINCT argv, so that parameter is not a constant either.
        _bp_red = Path(_wd) / "rederive-baseline.json"
        _bp_red.write_text(_json.dumps(_ARMED))
        _lp_red = Path(_wd) / "rederive-log.jsonl"
        _lp_red.write_text("")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main(["--rederive"], baseline_path=_bp_red, log_path=_lp_red,
                       corpus=lambda: {"median": 7, "mean": 7.2, "subjects": 61},
                       starved=lambda since, **_: ([], None))
        _o = _buf.getvalue()
        case("--rederive reports pinned vs now and does not evaluate triggers",
             (_rc, "pinned vs now" in _o, "trigger 1" in _o), (0, True, False))
        case("...and it reports the DRIFT it finds, from the corpus it was given",
             "DRIFT" in _o, True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

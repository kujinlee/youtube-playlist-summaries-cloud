#!/usr/bin/env python3
"""Is the route-escalation mechanism still worth having? — answered from its own log.

    python3 scripts/check-decision-scheme.py              # fire the triggers
    python3 scripts/check-decision-scheme.py --rederive   # recompute the pinned baseline
    python3 scripts/check-decision-scheme.py --self-test  # 133 cases

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

WHY THIS FILE EXISTS RATHER THAN A NOTE IN A PROCESS DOC
-------------------------------------------------------
The owner asked for a re-evaluation PROMISE: what can trigger re-evaluation later? A promise
written in prose is the thing this repository has measured rotting — `review-method.md` says
"the evidence is derivable, not remembered" and `round-header-template.md` cites that line and
then introduces a hand-authored tally. So the promise is seven predicates with stated
observations, and four of them FAIL rather than warn.

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


def t2_non_termination(rows: list[dict]) -> str | None:
    """FAIL. The primary falsifier: a UNIT whose ladder is exhausted and still carrying findings.

    ⛔ REWRITTEN AFTER r1 (Claude B3 + Codex H4, one cause). The first version read ONE ROW at a
    time and asked whether that row's AUTHORED `routes_tried` held four distinct routes. An
    author who never grew the field made exhaustion invisible, and five rows retrying one route
    exited 0 with `all triggers quiet`. Now the history is DERIVED per (subject, unit) by
    `derive_routes_tried`, so it cannot be understated by omission, and the question is asked of
    the unit rather than of a row.
    """
    bad = []
    for key, unit_rows in group_by_unit(rows).items():
        tried = derive_routes_tried(unit_rows)
        if len(set(tried)) < len(LADDER):
            continue
        if unit_rows[-1].get("outcome") == "continued":
            bad.append(key)
    if not bad:
        return None
    names = ", ".join(f"{a}/{b}" for a, b in bad[:4])
    return (f"{len(bad)} unit(s) exhausted every route and still carry findings ({names}) — "
            f"the claim that escalation terminates is refuted, not delayed")


def t3_routes_collapsed(rows: list[dict]) -> str | None:
    """FAIL. >=5 scored rows all taking one route: a conveyor, not a decision.

    ⚠ r1 Claude B3 noted this was defeated by a single second unit on another route. That shape
    is now INEXPRESSIBLE rather than guarded: `validate_row` derives each unit's history and
    refuses any row whose route is not `route_next(derived)`, so a unit cannot repeat a route at
    all. What remains here is the GLOBAL question — many units, every one taking the same route —
    which is a different claim and still worth asking.
    """
    scored = [r for r in rows if r.get("outcome") in OUTCOMES]
    if len(scored) < 5:
        return None
    routes = {r.get("route") for r in scored}
    if len(routes) > 1:
        return None
    return (f"all {len(scored)} scored rows took route {routes.pop()!r} — the routes are not "
            f"discriminating, so this is a conveyor wearing a decision's clothes")


def t4_no_improvement(rows: list[dict], baseline_median: float) -> str | None:
    """FAIL. The last 5 terminated SUBJECTS are no shorter than the pre-scheme median.

    ⛔ THE COMPARATOR IS PINNED, NOT RECOMPUTED. A baseline recomputed at read time cannot
    detect that it has moved, and after the scheme ships every round count is contaminated by
    it. `baseline.json` holds median 4 over 57 subjects, derived at `5d957db8`.

    ⟳ r1 Codex M6: this counted ROWS, which are per UNIT, while the pinned comparator is per
    SUBJECT. Five units of ONE subject fired it, reporting "the last 5 subjects" over a sample
    of one. Rows are now collapsed to subjects, taking each subject's LAST terminated row.
    """
    per_subject: dict[str, int] = {}
    for r in rows:
        if r.get("outcome") == "stopped" and isinstance(r.get("rounds_at_termination"), int):
            # ⛔ r2 YM4: a dict UPDATE does not move a key to the end, so `list(...)[-5:]` was
            # NOT "the last five subjects" — it was the last five by FIRST appearance. Measured
            # with nine rows: the latest five by occurrence had median 9 and the code read a
            # median of 1, so trigger 4 stayed quiet over a run that should have failed it.
            # Popping first re-inserts at the end, which is what "latest" has to mean.
            per_subject.pop(r.get("subject"), None)
            per_subject[r.get("subject")] = r["rounds_at_termination"]
    if len(per_subject) < 5:
        return None
    recent = list(per_subject.values())[-5:]
    med = st.median(recent)
    if med < baseline_median:
        return None
    return (f"median rounds-to-termination over the last 5 SUBJECTS is {med}, against a pinned "
            f"pre-scheme median of {baseline_median} — the mechanism is ceremony, not leverage")


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
    marks = [bool(r.get("ranker_hit")) for r in rows if "ranker_hit" in r]
    for i in range(len(marks) - 1):
        if not marks[i] and not marks[i + 1]:
            return (f"two consecutive ranker misses at rows {i + 1} and {i + 2} of "
                    f"{len(marks)} scored — re-fit or retire the ranking")
    return None


def t6_denominator_moved(now: dict, pinned: dict, tol: float = 0.5) -> str | None:
    """WARN. A finding expires when its denominator moves; say so before trusting the rest."""
    out = []
    for key in ("median", "mean"):
        a, b = now.get(key), pinned.get(key)
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not b:
            continue
        if abs(a - b) / b > tol:
            out.append(f"{key} rounds/subject {b} -> {a}")
    return ("the corpus moved under the pinned baseline: " + "; ".join(out)) if out else None


def t7_sample_reached(rows: list[dict], floor: int = 10) -> str | None:
    """WARN. Enough rows to re-score the bet: 10/10 lifts the accuracy bound 37% -> 74%."""
    scored = [r for r in rows if r.get("outcome") in OUTCOMES]
    if len(scored) < floor:
        return None
    hits = sum(1 for r in scored if r.get("ranker_hit"))
    return (f"{len(scored)} scored rows ({hits} ranker hits) — re-evaluate now; at {floor}/"
            f"{floor} the one-sided 95% accuracy bound reaches 74%, against a ~7% coin")


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
    # ⛔ r1 Codex M5: `bool("false")` is True, so a STRING silently became a ranker hit and two
    # misses read as two hits. A field a trigger turns on is type-checked, not coerced.
    if "ranker_hit" in row and not isinstance(row["ranker_hit"], bool):
        return (f"ranker_hit is {type(row['ranker_hit']).__name__}, not a bool — a string "
                f"coerces to True and erases a miss")
    if prior is None:
        return None
    tried = derive_routes_tried(prior)
    err = route_sequence_error(tried)
    if err:
        return f"this unit's history is not a ladder prefix: {err}"
    expected = route_next(tried)
    if expected is None:
        return (f"the ladder is EXHAUSTED for {unit_key(row)} (tried {tried}) — there is no "
                f"route left to bet on, so this row is a retry after exhaustion")
    if row["route"] != expected:
        return (f"route {row['route']!r} is not the next route for {unit_key(row)}: tried "
                f"{tried}, so the only route left to bet on is {expected!r}")
    # An AUTHORED routes_tried may not contradict the derived one. It is redundant now, and a
    # redundant field that disagrees with history is how the r1 Blocking was expressible.
    if "routes_tried" in row and list(row["routes_tried"]) != tried:
        return (f"routes_tried {row['routes_tried']!r} contradicts this unit's history {tried!r} "
                f"— the field is DERIVED now and need not be written at all")
    return None


def group_by_unit(rows: list[dict]) -> dict[tuple, list[dict]]:
    """PURE. (subject, unit) -> its rows in file order.

    ⛔ r1 Claude B3: NO trigger grouped rows this way, so `t3_routes_collapsed` was defeated by
    a single second unit on another route and a per-unit conveyor was invisible.
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
        drift = t6_denominator_moved(now, pinned_rounds)
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
    bad = []
    seen: dict[tuple, list[dict]] = {}
    for i, r in enumerate(rows, 1):
        prior = seen.get(unit_key(r), []) if isinstance(r, dict) else []
        why = validate_row(r, prior)
        if why:
            bad.append((i, why))
        elif isinstance(r, dict):
            seen.setdefault(unit_key(r), []).append(r)
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
    starved_subjects, starve_why = starved(armed)
    if starve_why:
        print(f"CANNOT RUN — the starvation ratchet could not be evaluated: {starve_why}")
        print("    Trigger 1 is the loudest one and it was NOT CHECKED. Treat this as not run.")
        return 2
    fails, warns = [], []
    for name, result in (
        ("1 NOT FED", t1_not_fed(rows, starved_subjects)),
        ("2 NON-TERMINATION", t2_non_termination(rows)),
        ("3 ROUTES COLLAPSED", t3_routes_collapsed(rows)),
        ("4 NO IMPROVEMENT", t4_no_improvement(rows, pinned_rounds["median"])),
        ("5 RANKER MISS", t5_ranker_miss(rows)),
    ):
        if result:
            fails.append((name, result))
    for name, result in (
        ("6 DENOMINATOR MOVED", t6_denominator_moved(now, pinned_rounds)),
        ("7 SAMPLE REACHED", t7_sample_reached(rows)),
    ):
        if result:
            warns.append((name, result))

    scored = [r for r in rows if r.get("outcome") in OUTCOMES]
    print(f"decision-scheme: {len(rows)} row(s), {len(scored)} scored; "
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
        counts = [len(r) for r in mod.by_subject_rounds(rows).values() if len(r) >= 2]
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
            "subjects": len(counts)}


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
        env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
               "PATH": _os.environ.get("PATH", ""), "HOME": str(d)}
        def g(*a, **kw):
            return _sub.run(["git", "-c", "user.name=t", "-c", "user.email=t@e", *a],
                            cwd=d, capture_output=True, text=True, check=True,
                            env={**env, **kw.get("extra", {})})
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
    # ⭐ THE CASE FOR THE BLOCKING ITSELF: the old version read one row's AUTHORED field, so a
    # history that was never written looked unexhausted. Derivation makes that unreachable.
    case("exhaustion is DERIVED, so it cannot be hidden by never writing routes_tried",
         "refuted" in (_try(lambda: t2_non_termination(
             [{"subject": "s", "unit": "u", "route": r, "outcome": "continued"}
              for r in LADDER])) or ""), True)
    case("two DIFFERENT units each three rounds in are not exhausted between them",
         t2_non_termination([_u("u", r, "continued") for r in LADDER[:2]]
                            + [_u("v", r, "continued") for r in LADDER[:2]]), None)

    # ── trigger 3: a conveyor wearing a decision's clothes ───────────────────────────────────
    _one = [{"route": "accrete", "outcome": "stopped"}] * 5
    case("five scored rows on one route is a collapse",
         "not discriminating" in (t3_routes_collapsed(_one) or ""), True)
    case("four is below the floor — the trigger states its own sample size",
         t3_routes_collapsed(_one[:4]), None)
    case("five rows across TWO routes discriminate",
         t3_routes_collapsed(_one[:4] + [{"route": "redesign", "outcome": "stopped"}]), None)
    case("UNSCORED rows do not count toward the floor",
         t3_routes_collapsed([{"route": "accrete", "outcome": None}] * 9), None)

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

    # ── trigger 5: two CONSECUTIVE misses ────────────────────────────────────────────────────
    case("one miss is a bet losing, not a broken instrument",
         t5_ranker_miss([{"ranker_hit": True}, {"ranker_hit": False}, {"ranker_hit": True}]),
         None)
    case("two consecutive misses fire, and the message says WHICH rows",
         "rows 2 and 3" in (t5_ranker_miss(
             [{"ranker_hit": True}, {"ranker_hit": False}, {"ranker_hit": False}]) or ""), True)
    case("rows without the field are not counted as misses",
         t5_ranker_miss([{}, {}, {}]), None)

    # ── triggers 6 and 7: warnings ───────────────────────────────────────────────────────────
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
    case("nine scored rows is below the re-evaluation sample",
         t7_sample_reached([{"outcome": "stopped"}] * 9), None)
    case("ten scored rows asks for re-evaluation and quotes the bound",
         "74%" in (t7_sample_reached([{"outcome": "stopped"}] * 10) or ""), True)
    # An EXPLICIT floor, distinct from the default, so the parameter is not a constant.
    case("the sample floor is a parameter, so three rows reach a floor of three",
         ("fires" if t7_sample_reached([{"outcome": "stopped"}] * 3, 3) else "quiet",
          t7_sample_reached([{"outcome": "stopped"}] * 3)), ("fires", None))

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
                       starved=lambda since: ([], None))
        _o = _buf.getvalue()
        case("an armed, quiet world exits 0 and SAYS it is quiet",
             (_rc, "all triggers quiet" in _o), (0, True))
        _bp_starved = Path(_wd) / "starved-baseline.json"
        _bp_starved.write_text(_json.dumps({"rounds_to_termination": {"median": 9}, "armed_at": "2026-01-01T00:00:00Z"}))
        _lp_starved = Path(_wd) / "starved-log.jsonl"
        _lp_starved.write_text("".join(_json.dumps(r) + "\n" for r in []))
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_starved, log_path=_lp_starved,
                       corpus=lambda: {"median": 9, "mean": 9.0, "subjects": 60},
                       starved=lambda since: (["alpha", "beta"], None))
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
                       starved=lambda since: ([], None))
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
                       starved=lambda since: ([], None))
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
                       starved=lambda since: (["delta"], None))
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
                       starved=lambda since: (["epsilon"], None))
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
                           starved=lambda since: ([], None))
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
                           starved=lambda since: ([], None))
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
                       starved=lambda since: ([], None))
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
                       starved=lambda since: ([], None))
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
                       starved=lambda since: (["gamma"], None))
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
                       starved=lambda since: ([], None))
        _o = _buf.getvalue()
        case("--rederive reports pinned vs now and does not evaluate triggers",
             (_rc, "pinned vs now" in _o, "trigger 1" in _o), (0, True, False))
        case("...and it reports the DRIFT it finds, from the corpus it was given",
             "DRIFT" in _o, True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

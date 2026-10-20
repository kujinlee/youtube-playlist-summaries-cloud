#!/usr/bin/env python3
"""Is the route-escalation mechanism still worth having? — answered from its own log.

    python3 scripts/check-decision-scheme.py              # fire the triggers
    python3 scripts/check-decision-scheme.py --rederive   # recompute the pinned baseline
    python3 scripts/check-decision-scheme.py --self-test  # 113 cases

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


def derive_outcome(subject: str, unit: str, after_round: int,
                   tally: dict[str, int] | None) -> str | None:
    """PURE. Did the stream stop for `unit`, read from the component tally? None = NOT DERIVABLE.

    r1 Claude: `outcome: continued` is derivable from whether a later round named the same
    component, "which `scope_tally` already computes". True — and bounded, which is why this
    returns None rather than guessing:

      * the subject's coordinator documents must be READABLE. Measured 2026-10-20: 10 of the 57
        subjects where the procedure applies. So for 47 subjects this cannot answer, and
        `None` is the honest answer rather than a default.
      * `unit` must name a component the tally knows. A unit the tally has never seen is not
        evidence of a stopped stream; it is evidence of a naming mismatch.

    ⚠ A derived answer OVERRIDES an authored one — that is the direction of trust the whole
    redesign turns on — but an UNDERIVABLE row keeps its authored outcome and is counted as
    authored, so the authored share is reportable instead of invisible.
    """
    if not tally or unit not in tally:
        return None
    return "continued" if tally[unit] > after_round else "stopped"


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
    """subject -> {round: ALL paths for that round}, via check-review-rounds' OWN grammar.

    ⟳ r1 Claude H2a / Codex H2: this used to be `dict[round] = path`, keeping ONE path per
    round. A coordinator and a half for the same round mapped to the same key, so WHICH path
    survived depended on `rglob` order — and whether a subject looked newly starved depended on
    that. Rounds now hold a SET of paths and nothing is overwritten.

    One rule, one place: `SHAPES` is imported rather than retyped — the 17-instance drift.
    """
    import importlib.util
    reviews = (REPO / "docs" / "reviews") if reviews is None else reviews
    spec = importlib.util.spec_from_file_location(
        "_crr", REPO / "scripts" / "check-review-rounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seen: dict[str, dict[int, set[str]]] = {}
    # ⛔ r1 Claude M1: this filtered to the WRITER SUBDIRECTORIES and so excluded 294 flat round
    # documents, which `check-review-rounds.py` reads — so the ratchet measured a corpus the
    # procedure does not use. ⚠ And the reason I chose that filter is the instructive part: it
    # reproduced a PREVIOUS SESSION'S denominator (63/57). I picked the corpus that matched a
    # number instead of the one the code reads. BOTH layouts now.
    for path in reviews.rglob("*.md"):
        if path.parent.name not in ("codex", "claude", "coordinator", reviews.name):
            continue
        for pat in mod.SHAPES:
            m = pat.match(path.name)
            if m:
                rel = str(path.relative_to(REPO)) if REPO in path.parents or path.is_relative_to(
                    REPO) else str(path)
                seen.setdefault(m.group("subject"), {}).setdefault(
                    int(m.group("round")), set()).add(rel)
                break
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


def shallow_refusal(flag: str) -> str | None:
    """PURE. Why a shallow clone cannot answer "what did the tree hold at arming", else None.

    ⛔ EXTRACTED BECAUSE THE BRANCH WAS UNKILLABLE IN PLACE. `if shallow == "true"` can only
    behave differently on a shallow clone, so mutating it to `if False` was an EQUIVALENT
    mutation on any normal checkout — it survived with rc=0 and zero findings, which looks
    identical to a coverage gap. Pulling the decision out makes it a function a case can drive
    with either string, so the rule is covered rather than merely present.

    r1 Claude M6: a shallow clone has no history before arming, so every tracked round document
    looks new and the ratchet would name the entire corpus — backlog #56's death, from the one
    input nobody tests on.
    """
    if flag.strip() == "true":
        return ("this is a SHALLOW clone, so history before arming is absent and every tracked "
                "round document would look new (r1 Claude M6)")
    return None


def tree_at(epoch: int) -> "tuple[set[str] | None, str | None]":
    """(paths that existed at `epoch`, None) or (None, why this cannot be answered).

    ⭐ THIS REPLACES `paths_added_since`, AND THE CHANGE OF QUESTION IS THE REPAIR. The old rule
    asked git which paths were ADDED since arming (`--diff-filter=A`), which r1 showed has at
    least three doors: a relocated short document is an `A` rather than an `R`; `--since`
    filters on COMMITTER date, so a rebase or squash re-dates an old add into the window; and a
    shallow clone makes every tracked file look added.

    This asks instead: **what did the tree CONTAIN at arming?** A listing, not a diff — so
    there is no add/rename classification to get wrong, no committer-date sensitivity, and a
    shallow clone is detected rather than silently answered.
    """
    import subprocess
    try:
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=REPO,
                                 capture_output=True, text=True, check=True).stdout.strip()
        refusal = shallow_refusal(shallow)
        if refusal:
            return None, refusal
        sha = subprocess.run(["git", "rev-list", "-1", f"--before=@{epoch}", "HEAD"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout.strip()
        if not sha:
            return None, (f"no commit exists at or before the arming instant (@{epoch}), so "
                          f"'what the tree held at arming' has no answer")
        # ⛔ MEASURED 2026-10-20, AND I HAD ASSUMED OTHERWISE: `git rev-list -1 --before=@1 HEAD`
        # returns the repository's FIRST commit, not nothing. So an ISO-parseable but absurd
        # arming instant resolves to a tiny tree, nearly every subject looks post-arming, and
        # trigger 1 names almost all of them — red from birth, the backlog #56 death this whole
        # design is shaped to avoid. The resolved commit's own date is therefore checked against
        # the instant it is supposed to answer for.
        when = subprocess.run(["git", "show", "-s", "--format=%ct", sha], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.strip()
        if not when.isdigit() or int(when) > epoch:
            return None, (f"the newest commit at or before @{epoch} is {sha[:8]}, dated "
                          f"{when or 'unreadable'} — git resolved outside the window, so the "
                          f"arming instant predates this history and the tree at arming is "
                          f"not knowable")
        out = subprocess.run(["git", "ls-tree", "-r", "--name-only", sha], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        return None, f"git could not be read: {exc}"
    return {line.strip() for line in out.splitlines() if line.strip()}, None


def subjects_starved(armed: object, docs: dict | None = None,
                     before: set[str] | None = None) -> "tuple[list[str], str | None]":
    """(subjects that came into scope AFTER arming with no log row, None) | ([], why not).

    ⭐ THE RULE IS NOW A SET DIFFERENCE OVER MEMBERSHIP, not a question about one filename:

        a subject is newly in scope  iff  rounds it had BEFORE arming < 2 <= rounds it has NOW

    ⟳ Both r1 halves broke the old form, from opposite ends. Codex: `sorted(rounds)[1]` names
    the second ROUND NUMBER, not the document whose arrival established two rounds — so a
    historical r2 with a newly back-filled r1 returned `[]` and MISSED a subject that genuinely
    crossed into scope. Claude: two measured doors let it NAME HISTORICAL subjects, which is the
    backlog #56 shape the ratchet exists to avoid. Counting membership answers both, because it
    never asks which document arrived.

    ⛔ IT RETURNS A REASON, NOT AN EMPTY LIST, WHEN IT CANNOT ANSWER. An unparseable `armed_at`
    or an unreadable history is CANNOT RUN; silence there is indistinguishable from "nothing is
    starved", which is exactly how the predecessor died.
    """
    if armed is None:
        return [], None                      # not armed yet; `main()` says so in its own words
    epoch, why = parse_armed_at(armed)
    if why:
        return [], why
    docs = _round_docs() if docs is None else docs
    if before is None:
        before, why = tree_at(epoch)
        if why:
            return [], why
    out = []
    for subject, rounds in docs.items():
        if len(rounds) < 2:
            continue                         # the procedure does not apply yet
        rounds_before = sum(1 for paths in rounds.values() if any(p in before for p in paths))
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
    """Today's corpus figures, for trigger 6. Derived, never recalled."""
    reviews = (REPO / "docs" / "reviews") if reviews is None else reviews
    counts = []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_crr2", REPO / "scripts" / "check-review-rounds.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        seen: dict[str, set[int]] = {}
        if not reviews.is_dir():
            raise OSError(f"the review corpus is not a directory: {reviews}")
        for p in reviews.rglob("*.md"):
            # BOTH layouts — see `_round_docs` for why the subdir-only filter was wrong.
            if p.parent.name not in ("codex", "claude", "coordinator", reviews.name):
                continue
            for pat in mod.SHAPES:
                m = pat.match(p.name)
                if m:
                    seen.setdefault(m.group("subject"), set()).add(int(m.group("round")))
                    break
        counts = [len(r) for r in seen.values() if len(r) >= 2]
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

    # ── the ratchet: membership BEFORE arming, not which filename arrived ────────────────────
    # ⛔ REWRITTEN AFTER r1, WHERE BOTH HALVES BROKE THE OLD RULE FROM OPPOSITE ENDS. Codex:
    # `sorted(rounds)[1]` named the second ROUND NUMBER, so a historical r2 with a back-filled
    # r1 returned [] and MISSED a subject that crossed into scope. Claude: two measured doors
    # let it NAME HISTORICAL subjects, the backlog #56 shape it exists to avoid. The rule is now
    # a set difference: rounds held BEFORE arming < 2 <= rounds held NOW.
    _ARM = "2026-10-20T10:00:00-07:00"
    _D = {
        "old":  {1: {"docs/reviews/coordinator/old-r1-coordinator.md"},
                 2: {"docs/reviews/coordinator/old-r2-coordinator.md"}},
        "new":  {1: {"docs/reviews/coordinator/new-r1-coordinator.md"},
                 2: {"docs/reviews/coordinator/new-r2-coordinator.md"}},
        "one":  {1: {"docs/reviews/coordinator/one-r1-coordinator.md"}},
    }
    _ALL_OLD = {p for r in _D["old"].values() for p in r}
    case("HISTORY IS NOT STARVED — a subject whose rounds BOTH predate arming is out of scope",
         subjects_starved(_ARM, {"old": _D["old"]}, _ALL_OLD), ([], None))
    case("a subject whose rounds BOTH postdate arming is named",
         subjects_starved(_ARM, {"new": _D["new"]}, set()), (["new"], None))
    case("a subject that had ONE round before arming and two now has crossed into scope",
         subjects_starved(_ARM, {"new": _D["new"]},
                          {"docs/reviews/coordinator/new-r1-coordinator.md"}), (["new"], None))
    # ⭐⭐ THE r1 CODEX CASE THE OLD RULE FAILED: the newly arrived document is r1, not r2. The
    # old form asked "is the SECOND round's path new?" and answered no; membership answers yes.
    case("⭐ a HISTORICAL r2 with a newly BACK-FILLED r1 is in scope — the old rule missed it",
         subjects_starved(_ARM, {"new": _D["new"]},
                          {"docs/reviews/coordinator/new-r2-coordinator.md"}), (["new"], None))
    # ⭐ TRAVERSAL ORDER CANNOT MATTER NOW: a round holds a SET of paths, and the round counts as
    # pre-existing if ANY of them did. The old form kept one path per round and `rglob` decided.
    case("a round with two documents counts as pre-existing when EITHER predates arming",
         subjects_starved(_ARM,
                          {"s": {1: {"a-r1-codex.md", "a-r1-coordinator.md"},
                                 2: {"a-r2-codex.md", "a-r2-coordinator.md"}}},
                          {"a-r1-codex.md", "a-r2-coordinator.md"}), ([], None))
    case("a subject with one round is not yet in scope, however recent",
         subjects_starved(_ARM, {"one": _D["one"]}, set()), ([], None))
    case("every subject that crossed is named, not just the first found",
         subjects_starved(_ARM, _D, set()), (["new", "old"], None))
    case("no arming date means nothing is starved, and the promise says so instead",
         subjects_starved(None, _D, set()), ([], None))
    # ⛔ A REASON, NEVER AN EMPTY LIST (r1 Claude H1): an unparseable armed_at is CANNOT RUN.
    case("a BARE DATE is refused — git's approxidate would match nothing, silently",
         ("no timezone" in (subjects_starved("2026-10-20", _D, set())[1] or ""),
          subjects_starved("2026-10-20", _D, set())[0]), (True, []))
    case("...and so is free text, with the remedy named",
         ("not an ISO-8601 instant" in (subjects_starved("on merge", _D, set())[1] or "")), True)
    case("a full ISO instant with an offset is accepted",
         subjects_starved(_ARM, {"one": _D["one"]}, set()), ([], None))
    # TWO DISTINCT arming instants, so the parameter is not a constant.
    case("the arming instant is parsed, not pattern-matched — a second valid form works too",
         subjects_starved("2026-01-02T03:04:05+00:00", {"new": _D["new"]}, set()),
         (["new"], None))

    # ── parse_armed_at and tree_at, the two inputs trigger 1 stands on ───────────────────────
    case("a full instant parses to an epoch", parse_armed_at(_ARM)[0] is not None, True)
    case("a naive instant is refused, because the window would depend on the reader's machine",
         "no timezone" in (parse_armed_at("2026-10-20T10:00:00")[1] or ""), True)
    case("an impossible date is refused by the parser, where git would have accepted it",
         parse_armed_at("2026-13-45T99:00:00")[0], None)
    case("a non-string is refused by type, not by regex",
         parse_armed_at(20261020)[0], None)
    case("tree_at answers from a LISTING of the real repository, not from a diff",
         (lambda r: (isinstance(r[0], set) and len(r[0]) > 100, r[1]))(
             tree_at(parse_armed_at(_ARM)[0])), (True, None))
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

    # ── derive_outcome: derivable, and HONEST about when it is not ───────────────────────────
    case("an unknown unit is NOT DERIVABLE rather than assumed stopped",
         derive_outcome("s", "u", 2, {"other": 5}), None)
    case("no tally at all is NOT DERIVABLE — 47 of 57 subjects are unreadable",
         derive_outcome("s", "u", 2, None), None)
    case("a component appearing in a LATER round means the stream continued",
         derive_outcome("s", "parse-header", 2, {"parse-header": 5}), "continued")
    case("a component not appearing after that round means it stopped",
         derive_outcome("s", "parse-header", 5, {"parse-header": 5}), "stopped")
    # TWO DISTINCT inputs for after_round, so the parameter is not a constant.
    case("the round boundary is read, not assumed",
         (derive_outcome("s", "c", 1, {"c": 2}), derive_outcome("s", "c", 2, {"c": 2})),
         ("continued", "stopped"))
    # ⚠ A SECOND SUBJECT. With one value at every call site no case can tell `subject` from a
    # constant, so a clause reading it would be unguarded — `check-fixture-variation` caught it.
    # ⭐ And the case states the real bound: `subject` is carried for the MESSAGE and the tally
    # is already scoped to one subject by the caller, so the same unit in another subject reads
    # the same tally. That is deliberate, and saying so is better than exempting it.
    case("the subject is carried, and the tally it is given is what decides",
         (derive_outcome("other-subject", "c", 1, {"c": 2}),
          derive_outcome("s", "c", 1, {"c": 2})), ("continued", "continued"))

    # ── _corpus_now: the handler and the empty path, which had NO case at all (r1 B2/L1) ─────
    with _tf.TemporaryDirectory() as _cd:
        _missing = Path(_cd) / "nope"
        _err = _corpus_now(_missing)
        case("a corpus directory that is not there is an ERROR, not an empty corpus",
             (_err.get("median"), bool(_err.get("error"))), (None, True))
        case("...and the message NAMES the path, so the remedy is not guessed at",
             "nope" in _err.get("error", ""), True)
        (Path(_cd) / "empty").mkdir()
        _empty = _corpus_now(Path(_cd) / "empty")
        # ⚠ r1 Claude L1: this path is reached with NO EXCEPTION AT ALL, and it returns the
        # same shape as the handler — which is why `main()` keys on `error`, not on the handler.
        case("a corpus with no qualifying subject is an ERROR too, reached with no exception",
             (_empty.get("median"), _empty.get("error")),
             (None, "no subject has >=2 rounds"))
        (Path(_cd) / "real" / "coordinator").mkdir(parents=True)
        for _n in (1, 2):
            (Path(_cd) / "real" / "coordinator" / f"x-r{_n}-coordinator.md").write_text("x")
        _ok = _corpus_now(Path(_cd) / "real")
        case("a corpus with one two-round subject reports figures and NO error",
             (_ok.get("median"), _ok.get("subjects"), _ok.get("error")), (2, 1, None))
        # TWO DISTINCT corpora, so the parameter is not a constant.
        case("the corpus it is GIVEN is the one it reads",
             (_corpus_now(Path(_cd) / "real").get("subjects"),
              _corpus_now(Path(_cd) / "empty").get("subjects")), (1, None))

    # ── read_log: an unreadable file is CANNOT RUN, not an empty log ──────────────────────────
    with _tf.TemporaryDirectory() as _pd:
        _noperm = Path(_pd) / "locked.jsonl"
        _noperm.write_text('{"a": 1}\n')
        import os as _os
        _os.chmod(_noperm, 0o000)
        _res = _try(lambda: read_log(_noperm))
        _os.chmod(_noperm, 0o600)
        # ⛔ r1 Codex M7: a PermissionError escaped main()'s `except ValueError` and gave a
        # traceback with rc=1 — a process failure dressed as a verdict. Running as root reads
        # the file anyway, so the case accepts either the raise or the successful read, and
        # asserts only that it is NOT a silently-empty log.
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

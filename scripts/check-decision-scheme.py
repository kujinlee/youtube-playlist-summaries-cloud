#!/usr/bin/env python3
"""Is the route-escalation mechanism still worth having? — answered from its own log.

    python3 scripts/check-decision-scheme.py              # fire the triggers
    python3 scripts/check-decision-scheme.py --rederive   # recompute the pinned baseline
    python3 scripts/check-decision-scheme.py --self-test  # 64 cases

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
    """FAIL. The primary falsifier: all four routes tried and the stream still running."""
    bad = [r for r in rows
           if len(set(r.get("routes_tried", []))) >= len(LADDER)
           and r.get("outcome") == "continued"]
    if not bad:
        return None
    names = ", ".join(f"{r.get('subject')}/{r.get('unit')}" for r in bad[:4])
    return (f"{len(bad)} unit(s) exhausted every route and still carry findings ({names}) — "
            f"the claim that escalation terminates is refuted, not delayed")


def t3_routes_collapsed(rows: list[dict]) -> str | None:
    """FAIL. >=5 scored rows all taking one route: a conveyor, not a decision."""
    scored = [r for r in rows if r.get("outcome") in OUTCOMES]
    if len(scored) < 5:
        return None
    routes = {r.get("route") for r in scored}
    if len(routes) > 1:
        return None
    return (f"all {len(scored)} scored rows took route {routes.pop()!r} — the routes are not "
            f"discriminating, so this is a conveyor wearing a decision's clothes")


def t4_no_improvement(rows: list[dict], baseline_median: float) -> str | None:
    """FAIL. The last 5 terminated subjects are no shorter than the pre-scheme median.

    ⛔ THE COMPARATOR IS PINNED, NOT RECOMPUTED. A baseline recomputed at read time cannot
    detect that it has moved, and after the scheme ships every round count is contaminated by
    it. `baseline.json` holds median 4 derived at `5d957db8`, before any of this existed.
    """
    done = [r for r in rows if r.get("outcome") == "stopped"
            and isinstance(r.get("rounds_at_termination"), int)]
    if len(done) < 5:
        return None
    recent = [r["rounds_at_termination"] for r in done[-5:]]
    med = st.median(recent)
    if med < baseline_median:
        return None
    return (f"median rounds-to-termination over the last 5 subjects is {med}, against a pinned "
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
    rows = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{i} is not JSON: {exc}") from exc
    return rows


def validate_row(row: dict) -> str | None:
    """PURE. Why a row is unusable, else None."""
    for key in ("subject", "unit", "route", "routes_tried"):
        if key not in row:
            return f"missing {key!r}"
    if row["route"] not in LADDER:
        return f"route {row['route']!r} is not on the ladder {list(LADDER)}"
    if not isinstance(row["routes_tried"], list):
        return "routes_tried is not a list"
    err = route_sequence_error(row["routes_tried"])
    if err:
        return err
    if row.get("outcome") not in (None, *OUTCOMES):
        return f"outcome {row.get('outcome')!r} is not one of {(None, *OUTCOMES)}"
    if row.get("outcome") == "stopped" and not isinstance(row.get("rounds_at_termination"), int):
        return "a stopped row must record rounds_at_termination as an integer"
    return None


def _round_docs() -> dict[str, dict[int, str]]:
    """subject -> {round: relative path}, through check-review-rounds' OWN filename grammar.

    One rule, one place: re-deriving the grammar here is the 17-instance drift this repository
    keeps paying for, so `SHAPES` is imported rather than retyped.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_crr", REPO / "scripts" / "check-review-rounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seen: dict[str, dict[int, str]] = {}
    for path in (REPO / "docs" / "reviews").rglob("*.md"):
        if path.parent.name not in ("codex", "claude", "coordinator"):
            continue
        for pat in mod.SHAPES:
            m = pat.match(path.name)
            if m:
                rel = str(path.relative_to(REPO))
                seen.setdefault(m.group("subject"), {})[int(m.group("round"))] = rel
                break
    return seen


def paths_added_since(since: str) -> set[str]:
    """Repo-relative paths ADDED since `since`, in ONE git call.

    ⛔ --diff-filter=A, deliberately. A round document is written once; an edit to an old one
    must not make its subject look new. (The inverse hazard is recorded in `check-review-
    recorded.py`: `--diff-filter=A` cannot see an overwrite — true, and harmless here, because
    this asks WHEN A ROUND APPEARED, not whether its content changed.)
    """
    import subprocess
    out = subprocess.run(
        ["git", "log", f"--since={since}", "--diff-filter=A", "--name-only",
         "--pretty=format:"], cwd=REPO, capture_output=True, text=True, check=True)
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def subjects_starved(since: str | None, docs: dict | None = None,
                     added: set[str] | None = None) -> list[str]:
    """Subjects that reached >=2 rounds AFTER `since` — trigger 1's population.

    ⛔ THE `since` FILTER IS THE WHOLE POINT, AND LEAVING IT UNIMPLEMENTED WAS THIS FILE'S
    FIRST DEFECT. Without it, arming the guard names all 57 historical subjects as starved on
    day one — a gate red from birth, which backlog #56 measured getting switched off. The
    mechanism is a RATCHET: history is the pinned baseline and is never retro-filled.

    A subject counts when the round document that took it to its SECOND round was added after
    `since`. With no `since`, nothing is starved: the promise is not yet armed and says so.
    """
    if not since:
        return []
    # INJECTABLE so the RULE is testable without a repository or a git history — the same
    # separation `check-review-decision` needed and the reason three ratchets sat untestable
    # for eight days behind an entry point that wanted Docker.
    docs = _round_docs() if docs is None else docs
    added = paths_added_since(since) if added is None else added
    out = []
    for subject, rounds in docs.items():
        if len(rounds) < 2:
            continue
        second = sorted(rounds)[1]
        if rounds[second] in added:
            out.append(subject)
    return sorted(out)


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
    pinned = json.loads(baseline_path.read_text())
    pinned_rounds = pinned.get("rounds_to_termination", {})

    now = corpus()
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

    bad = [(i, validate_row(r)) for i, r in enumerate(rows, 1)]
    bad = [(i, why) for i, why in bad if why]
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

    fails, warns = [], []
    for name, result in (
        ("1 NOT FED", t1_not_fed(rows, starved(armed))),
        ("2 NON-TERMINATION", t2_non_termination(rows)),
        ("3 ROUTES COLLAPSED", t3_routes_collapsed(rows)),
        ("4 NO IMPROVEMENT", t4_no_improvement(rows, pinned_rounds.get("median", 4))),
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


def _corpus_now() -> dict:
    """Today's corpus figures, for trigger 6. Derived, never recalled."""
    counts = []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_crr2", REPO / "scripts" / "check-review-rounds.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        seen: dict[str, set[int]] = {}
        for p in (REPO / "docs" / "reviews").rglob("*.md"):
            if p.parent.name not in ("codex", "claude", "coordinator"):
                continue
            for pat in mod.SHAPES:
                m = pat.match(p.name)
                if m:
                    seen.setdefault(m.group("subject"), set()).add(int(m.group("round")))
                    break
        counts = [len(r) for r in seen.values() if len(r) >= 2]
    except (OSError, AttributeError, ImportError) as exc:
        # ⛔ NOT a fail-open: the caller prints these as `None` and trigger 6 is skipped, which
        # is visible in the output line. Swallowing it into a reassuring default is the shape
        # `check-ratchet-contract` R2 refuses.
        return {"median": None, "mean": None, "error": str(exc)}
    if not counts:
        return {"median": None, "mean": None, "error": "no subject has >=2 rounds"}
    return {"median": st.median(counts), "mean": round(st.mean(counts), 2),
            "subjects": len(counts)}


def _self_test() -> int:
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

    # ── the ratchet: which subjects count as starved ─────────────────────────────────────────
    # ⛔ THE CASE THAT WOULD HAVE CAUGHT THIS FILE'S FIRST DEFECT. `since` was accepted and
    # ignored, so arming the guard would have named all 57 historical subjects on day one.
    _docs = {"old": {1: "docs/reviews/coordinator/old-r1-coordinator.md",
                     2: "docs/reviews/coordinator/old-r2-coordinator.md"},
             "new": {1: "docs/reviews/coordinator/new-r1-coordinator.md",
                     2: "docs/reviews/coordinator/new-r2-coordinator.md"},
             "one": {1: "docs/reviews/coordinator/one-r1-coordinator.md"}}
    _added = {"docs/reviews/coordinator/new-r2-coordinator.md"}
    case("HISTORY IS NOT STARVED — only the subject whose SECOND round arrived since arming",
         subjects_starved("2026-10-20", _docs, _added), ["new"])
    case("a subject with one round is not yet in scope, however recent",
         subjects_starved("2026-10-20", {"one": _docs["one"]},
                          {"docs/reviews/coordinator/one-r1-coordinator.md"}), [])
    # ⚠ ADJACENT: the FIRST round arriving since arming is not the trigger — the second is,
    # because that is when the procedure starts applying.
    case("a first round arriving since arming does not count; the SECOND one does",
         subjects_starved("2026-10-20", {"new": _docs["new"]},
                          {"docs/reviews/coordinator/new-r1-coordinator.md"}), [])
    case("no arming date means nothing is starved, and the promise says so instead",
         subjects_starved(None, _docs, _added), [])
    case("every second round arriving since arming is named, not just the first found",
         subjects_starved("2026-10-20", _docs,
                          {"docs/reviews/coordinator/new-r2-coordinator.md",
                           "docs/reviews/coordinator/old-r2-coordinator.md"}), ["new", "old"])

    # ── trigger 2: the primary falsifier ─────────────────────────────────────────────────────
    _ex = {"subject": "s", "unit": "u", "routes_tried": list(LADDER), "outcome": "continued"}
    case("every route tried and findings still arriving REFUTES the design",
         "refuted" in (t2_non_termination([_ex]) or ""), True)
    case("every route tried and the stream STOPPED is the success path, not a failure",
         t2_non_termination([{**_ex, "outcome": "stopped"}]), None)
    # ⚠ ADJACENT negative: three routes, not four. The boundary is where the error lives.
    case("three routes tried is still escalating, not exhausted",
         t2_non_termination([{**_ex, "routes_tried": ["accrete", "redesign", "split"]}]), None)

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

    # ── trigger 4: no better than doing nothing ──────────────────────────────────────────────
    def _done(n):
        return {"outcome": "stopped", "rounds_at_termination": n}
    case("a median at the pinned baseline is NOT an improvement — >= fails, not >",
         "ceremony" in (t4_no_improvement([_done(4)] * 5, 4) or ""), True)
    case("a median below the baseline passes",
         t4_no_improvement([_done(3)] * 5, 4), None)
    case("four terminated subjects is below the floor",
         t4_no_improvement([_done(9)] * 4, 4), None)
    case("only the LAST five count, so early bad rows do not pin it forever",
         t4_no_improvement([_done(9)] * 3 + [_done(2)] * 5, 4), None)
    case("a stopped row with no round count cannot be scored and is excluded",
         t4_no_improvement([{"outcome": "stopped"}] * 9, 4), None)
    # ⚠ A SECOND, DISTINCT baseline. With one value at every call site no case can tell the
    # parameter apart from a constant, so the clause reading it would be unguarded —
    # `check-fixture-variation.py` caught exactly that here.
    case("the comparator is the PINNED baseline, not the literal 4",
         (t4_no_improvement([_done(6)] * 5, 7), "fires" if t4_no_improvement(
             [_done(6)] * 5, 6) else "quiet"), (None, "fires"))

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
    case("routes_tried must be a list, not a string",
         validate_row({**_good, "routes_tried": "accrete"}), "routes_tried is not a list")
    case("the row validator borrows the SEQUENCE rule rather than re-stating it",
         validate_row({**_good, "routes_tried": ["split"]}),
         route_sequence_error(["split"]))

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
                       starved=lambda since: [])
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
                       starved=lambda since: ["alpha", "beta"])
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
                       starved=lambda since: [])
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
                       starved=lambda since: [])
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
                       starved=lambda since: ["delta"])
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
                       starved=lambda since: ["epsilon"])
        _o = _buf.getvalue()
        case("an UNARMED baseline reports NOT YET FED rather than a vacuous all-quiet",
             (_rc, "NOT YET FED" in _o), (0, True))
        _bp_nobase = Path(_wd) / "nobase-baseline.json"
        _lp_nobase = Path(_wd) / "nobase-log.jsonl"
        _lp_nobase.write_text("")
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _rc = main([], baseline_path=_bp_nobase, log_path=_lp_nobase,
                       corpus=lambda: {"median": 2, "mean": 2.0, "subjects": 1},
                       starved=lambda since: ["gamma"])
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
                       starved=lambda since: [])
        _o = _buf.getvalue()
        case("--rederive reports pinned vs now and does not evaluate triggers",
             (_rc, "pinned vs now" in _o, "trigger 1" in _o), (0, True, False))
        case("...and it reports the DRIFT it finds, from the corpus it was given",
             "DRIFT" in _o, True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

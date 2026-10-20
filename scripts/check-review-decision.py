#!/usr/bin/env python3
"""What does the review loop do next? — answered from recorded evidence, not recall.

    python3 scripts/check-review-decision.py              # decide for the current branch
    python3 scripts/check-review-decision.py --self-test  # 91 cases

WHY THIS EXISTS
---------------
Measured 2026-09-14 on PR #302: a contained single-file change ran FOUR adversarial review
rounds. Two were owed. Rounds 3 and 4 each returned a single Low in the coordinator's own
test code — exactly the case `review-method.md` names when it says *"one round is fine, do
not over-apply this"*.

Every rule was already written down. The failure was a CONFLATION of two questions:

    convergence    has defect discovery dried up?
    tree identity  did a round see the code that MERGES?

Rounds 3 and 4 were spent on tree identity while being narrated as unmet convergence — and
tree identity has four answers, of which "run another round" is the most expensive and the
last. This script keeps them apart so they cannot be merged again.

⚠ IT CONSUMES JUDGEMENTS, IT DOES NOT MAKE THEM. `aim` and `fix_induced` are recorded by
the agent in each round document's header (docs/round-header-template.md). A header
filled in dishonestly produces a confident wrong answer and nothing here detects it.

NO-CALLER: an instrument the coordinator consults at a decision point; CI has no decision to
make about whether to run a review round. Its protection is that `review-method.md`'s
decision card names running it as the step — which is precisely the protection that FAILED
on PR #302 when the step was prose. If it is skipped again, the remedy is not better prose;
it is making this a step nobody can skip.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- Q1: scope
# review-method.md's own trigger list, expressed as PATH PREFIXES so the answer is
# observable rather than argued. Anything not named here is a contained change.
# ⛔⛔ REDESIGN (round 3 — ARCHITECTURE REVIEW, armed by the branch's own rule).
#
# THREE ROUNDS, ONE CLASS, EACH FIX CREATING THE NEXT INSTANCE:
#   r1 B2  a RISKY allowlist missed `app/api/`, where money is charged
#   r2 H1  the INVERTED default still listed `scripts/`, where money guards live
#   r3 B1  ...and still listed `docs/`, where two mode-755 schema gates live
# Inverting the default MOVED the list; it did not remove it. Both the coordinator and
# Codex reached REDESIGN independently, on the same test: can a redesign remove it? Yes.
#
# ⭐ AND THE CLASSIFIER ALREADY EXISTED, HARDENED, IN THIS REPOSITORY.
# `check-review-recorded.py:187`'s `is_prose()` answers exactly this question, carries
# `CODE_UNDER_PROSE` for the executable gates under `docs/`, was hardened over four rounds
# of PR #299, is mutation-covered, and ships `prose_exceptions_cover()` as an anti-drift
# falsifier against the CI workflow globs. Its own comment states the rule my three lists
# kept getting wrong: "a gate script does not stop being code by living in a documentation
# directory."
#
# So this file no longer owns a path taxonomy. It asks the one that exists.
# `contained <=> is_prose` — both are the same axis, blast radius.
#
# ⚠ The classifier is INJECTED, so the rule stays PURE and cheap to case; `main()` passes
# the real one. A default-None that silently imports would make every case depend on the
# repository, which is how a rule stops being testable.
def _repo_is_prose():
    """`check-review-recorded.is_prose`, loaded lazily. RAISES if it cannot be loaded —
    guessing at blast radius is worse than refusing to answer."""
    import importlib.util
    src = REPO / "scripts" / "check-review-recorded.py"
    spec = importlib.util.spec_from_file_location("_crr", src)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {src}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_crr"] = mod
    spec.loader.exec_module(mod)
    return mod.is_prose


def scope_for(paths: list[str], is_prose) -> str:
    """PURE given its classifier. `one-round` only when EVERY path is prose.

    Anything that is not prose is code, and code changes get the full loop. There is no
    second list here to drift out of step with the first.
    """
    for p in paths:
        if not is_prose(p):
            return "full-loop"
    return "one-round"


# ----------------------------------------------------------- Q5: thrashing
def review_scope(rounds: list[dict]) -> list[str]:
    """PURE. -> the component(s) a convened review should EXAMINE, most-recurrent first.

    ⛔ THIS IS NOT `thrashing_component`, AND KEEPING THEM APART IS THE WHOLE POINT. That function
    answers WHETHER to convene — the arming condition, phrased on two CONSECUTIVE rounds. This
    answers WHICH component to examine. **They can disagree, and when they disagreed the arming
    statistic was wrong.**

    MEASURED 2026-10-20 over the 11 subjects whose coordinator documents carry a parseable header,
    against the 3 whose architecture review names the component it convened on (`src-caller`,
    `number-populations`, `parse-header`):

        total appearances        3 of 3   <- this function
        longest CONSECUTIVE run  2 of 3   <- what the arming condition encodes
        returns-after-a-gap      1 of 3
        total + 2x returns       3 of 3   rejected: a free parameter buying nothing

    ⭐ THE CASE THAT DECIDES IT is `review-decision-procedure`, whose own review convened on
    `parse-header` (backlog #117). Consecutive-run ranks `scope-for` first (rounds 1,2,3,4 — run 4);
    `parse-header` appeared in rounds **1,2,3 then 6,7** — total 5, longest run 3. It was fixed,
    went quiet for two rounds, and CAME BACK. **Consecutiveness is exactly what blinds a ranker to
    that shape**, and a component that returns after being apparently fixed is the stronger signal
    of a design problem.

    ⚠ BOUNDS, STATED RATHER THAN HIDDEN. **n = 3**, and it is a FIT not a validation. It is also a
    cap in the data rather than a shortfall in effort: of 19 architecture reviews, the three that
    would have extended the set land on subjects whose coordinator documents carry no header, so
    there is nothing to rank (backlog #314). ⛔ **And this is a RANKER, never a TRIGGER** — no
    threshold on this quantity separated labelled from unlabelled subjects, raw or normalised by
    round count, so it must not be read as "convene". `thrashing_component` keeps that job.
    """
    return [c for c, _ in sorted(scope_tally(rounds).items(), key=lambda kv: (-kv[1], kv[0]))]


def scope_tally(rounds: list[dict]) -> dict[str, int]:
    """PURE. component -> the NUMBER OF ROUNDS it appeared in.

    One rule, one place: `review_scope` ORDERS this and `scope_lead` MEASURES ITS MARGIN. The
    two were a single expression until 2026-10-20, which is why nothing could ask how big the
    lead was. A component counts ONCE per round however many findings it carried — the signal
    is "this component came back", not "this round was noisy".
    """
    tally: dict[str, int] = {}
    for r in rounds:
        for c in {f.get("component") for f in r.get("findings", []) if f.get("component")}:
            tally[c] = tally.get(c, 0) + 1
    return tally


def scope_lead(rounds: list[dict]) -> dict:
    """PURE. Is first place a LEAD, or an artifact of the tie-break?

    ⛔ MEASURED 2026-10-20 over the 10 subjects whose coordinator documents are readable:
    **5 of them have no lead at all** — every top component tied on appearance count — and
    `review_scope` resolves those by NAME (`key=(-kv[1], kv[0])`). `arm-prod-drift-cron` has
    five components tied at one appearance each, and the ranking's first element is
    `cron-comment` because `c` sorts first.

    ⭐ Determinism was never the missing property. The ranker is deterministic by construction;
    what it lacked was any way for a reader to see that first place was won by the alphabet. A
    deterministic answer that is evidence-free is worse than an abstention, because only one of
    the two gets re-examined.

    ⚠ `review_scope`'s ORDER is deliberately UNCHANGED — the case "ties break by name, so the
    order is deterministic" still holds and should. What changes is that nothing has to read
    that order as a finding.
    """
    tally = scope_tally(rounds)
    if not tally:
        return {"top": [], "n1": 0, "n2": 0, "margin": 0, "tied": 0, "abstain": True,
                "why": "no component appeared in any round"}
    counts = sorted(tally.values(), reverse=True)
    n1 = counts[0]
    n2 = counts[1] if len(counts) > 1 else 0
    tied = [c for c, v in sorted(tally.items()) if v == n1]
    abstain = len(tied) > 1
    return {
        "top": tied, "n1": n1, "n2": n2, "margin": n1 - n2, "tied": len(tied),
        "abstain": abstain,
        "why": (f"{len(tied)} components tied at {n1} appearance(s) — first place is the "
                f"tie-break, not evidence" if abstain
                else f"{tied[0]} leads by {n1 - n2}"),
    }


def scope_lead_lines(lead: dict) -> list[str]:
    """PURE. How `scope_lead` is REPORTED to a reader.

    Extracted so the reader is testable. The first version of this printed inline inside
    `main()`, which meant the repair for "the ranker had no reader" shipped a reader with no
    case — the same shape one level down. `main()` must not re-implement any of this.
    """
    if lead["abstain"]:
        out = [f"  scope-rank: NO LEAD — {lead['why']}"]
        if lead["top"]:
            out.append(f"              tied: {', '.join(lead['top'])}")
        return out
    return [f"  scope-rank: {lead['top'][0]} — {lead['why']} "
            f"(n1={lead['n1']} n2={lead['n2']})"]


def thrashing_component(rounds: list[dict]) -> str | None:
    """PURE. The component carrying fix-induced findings in BOTH of the last two rounds.

    ⚠ Deliberately the LAST TWO, not any two. "Two consecutive rounds" is the arming
    condition; a component that thrashed early and was then fixed must not arm it forever.
    """
    if len(rounds) < 2:
        return None

    def induced(r: dict) -> set:
        return {f.get("component") for f in r.get("findings", []) if f.get("fix_induced")}

    shared = induced(rounds[-2]) & induced(rounds[-1])
    return sorted(c for c in shared if c)[0] if any(shared) else None


# --------------------------------------------------------- Q4a: convergence
def converged(rounds: list[dict], scope: str) -> tuple[bool, str]:
    """PURE. Judged by AIM, not severity.

    `review-method.md` already says a clean severity column is a statement about the
    REVIEWERS, not the design. PR #302 measured the same thing from the other side:
    severity read "converged" from round 1 and was useless, while aim separated the rounds.
    """
    if not rounds:
        return False, "no round recorded"
    need = 1 if scope == "one-round" else 2
    if len(rounds) < need:
        return False, f"{len(rounds)} round(s) recorded; a {scope} change needs {need}"
    for r in rounds[-need:]:
        for f in r.get("findings", []):
            if f.get("severity") in ("Blocking", "High"):
                return False, f"r{r.get('round')} produced a {f.get('severity')}"
            if f.get("aim") == "deliverable":
                return False, f"r{r.get('round')} found a defect in the deliverable"
        if r.get("fixes_nontrivial"):
            return False, (f"r{r.get('round')}'s fixes were non-trivial — the card makes "
                           f"that a CONTINUE, and a fix is unreviewed code")
    return True, (f"{need} round(s) with no Blocking/High and nothing in the deliverable")


# ------------------------------------------------------- Q4b: tree identity
TREE_ANSWERS = (
    "land the editorial fixes AHEAD of the final round",
    "keep the last fixes uncommitted so the reviewer sees what ships",
    "declare NO-REVIEW: <reason> in the PR body",
    "run another round — LAST resort, never first",
)


def sequence_error(rounds: list[dict]) -> "str | None":
    """PURE. Why the recorded rounds are not a gapless 1..N sequence, else None.

    ⛔ r5 High (Codex): adjacency was inferred from LIST POSITION. `converged` slices
    `rounds[-need:]` and `thrashing_component` compares `rounds[-2]`/`rounds[-1]`, so a lost
    r2 made r1 and r3 "consecutive" — a false STOP — and two documents claiming the same
    round counted as two consecutive rounds. Measured in-process by the reviewer.
    A missing input is a failure, never a pass; that is this tool's own posture and it did
    not hold it about its own inputs.
    """
    nums = [r.get("round") for r in rounds]
    if any(not isinstance(n, int) for n in nums):
        return "a round document has no usable round number"
    if len(set(nums)) != len(nums):
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        return f"duplicate round number(s) {dupes} — two documents claim one round"
    want = list(range(1, len(nums) + 1))
    if sorted(nums) != want:
        return f"rounds are not gapless: found {sorted(nums)}, expected {want}"
    return None


def decide(rounds: list[dict], scope: str, tree_reviewed: bool) -> tuple[str, str]:
    """PURE. One decision and the reason for it.

    ⚠ ORDER IS LOAD-BEARING. Thrashing outranks convergence, because a design fighting
    itself converges on nothing worth having. And tree identity is checked LAST and
    answered as TREE — never as ROUND_OWED — so the two questions PR #302 merged stay apart.
    """
    if not rounds:
        return "ROUND_OWED", f"no round recorded; a {scope} change needs at least one"
    seq = sequence_error(rounds)
    if seq:
        return "CANNOT_RUN", f"{seq} — refusing to infer adjacency from list position"
    th = thrashing_component(rounds)
    if th:
        return ("ARCHITECTURE_REVIEW",
                f"thrashing: '{th}' carried fix-induced findings in "
                f"r{rounds[-2].get('round')} and r{rounds[-1].get('round')}")
    ok, why = converged(rounds, scope)
    if not ok:
        return "ROUND_OWED", why
    if not tree_reviewed:
        return "TREE", "converged, but no round saw the merging tree; cheapest first: " + \
                       "; ".join(f"({i}) {a}" for i, a in enumerate(TREE_ANSWERS, 1))
    return "STOP", f"converged — {why} — and a round saw the merging tree"


# --------------------------------------------------------- reading the record
FINDING_RE = re.compile(r"\{([^}]*)\}")


def parse_header(text: str) -> dict:
    """The ```yaml block after a round document's title.

    ⛔ RAISES on a missing or malformed header. It must never return an empty round:
    an empty round reads as "no findings", which reads as convergence — a silent pass
    over a document nobody could read. "Cannot run" is a failure, never a pass.
    """
    m = re.search(r"```yaml\n(.*?)```", text, re.S)
    if not m:
        raise ValueError("no ```yaml header block")
    body = m.group(1)
    rm = re.search(r"^round:\s*(\d+)\s*$", body, re.M)
    if not rm:
        raise ValueError("header has no `round:` line")
    # ⚠ r6 Medium (Codex): scanning the WHOLE body made
    # `halves.claude: "GAP: ... {disabled}"` count as a finding — a false CANNOT RUN from
    # ordinary human gap prose. Braces outside `findings:` are prose.
    _span = _findings_span(body)
    findings = [_scalarise(fm.group(1).split(",")) for fm in FINDING_RE.finditer(_span)]
    findings += _block_findings(body)

    # ⛔ PARITY, NOT BEST EFFORT. r1 Blocking (Codex): the parser read only `{...}` flow
    # mappings, so an ordinary block-style item parsed to ZERO findings — and an empty
    # round is clean, and two clean rounds are CONVERGED. A recorded High could reach STOP.
    # That is "cannot parse reads as a pass" inside the tool built to refuse it.
    # So: count the list-item markers and REFUSE unless every one produced a finding.
    # ⚠ r2 Medium (Codex): count markers ONLY inside the `findings:` span. Counting the
    # whole body refused a legitimate header whose `halves.claude` was a block scalar
    # containing a bullet — a false CANNOT RUN, and a guard that refuses valid input is a
    # guard that gets switched off.
    # ⛔ r3 Blocking (Codex): `_findings_span` returns "" when the key is ABSENT, so
    # declared == 0 == len(findings) and nothing validated — a header with no `findings:`
    # key at all passed as a CLEAN ROUND. r1's B1 for the third time, through a third
    # shape. An explicit empty list is a claim; a missing key is a silence.
    if not re.search(r"^findings:", body, re.M):
        raise ValueError("header has no `findings:` key — an absent list is not an "
                         "empty round; write `findings:` explicitly to claim zero")
    declared = len(re.findall(r"^\s*-\s", _findings_span(body), re.M))
    if declared != len(findings):
        raise ValueError(f"header declares {declared} finding item(s) but "
                         f"{len(findings)} parsed — refusing to guess")
    for f in findings:
        _validate(f)
    head = {"round": int(rm.group(1)), "findings": findings}
    for key, allowed in ROUND_REQUIRED.items():
        mm = re.search(rf"^{key}:\s*(\S+)\s*$", body, re.M)
        if not mm:
            raise ValueError(f"header has no `{key}:` — the card makes it a CONTINUE "
                             f"condition, so it cannot be left to memory")
        val = {"true": True, "false": False}.get(mm.group(1).strip().strip('"').strip("'"))
        if val not in allowed:
            raise ValueError(f"`{key}` must be true or false, got {mm.group(1)!r}")
        head[key] = val
    return head


# ⛔ r2 Blocking (Codex): PARITY PROVED AN ITEM BECAME A DICT, NOT THAT IT SAYS ANYTHING.
# A missing colon — `severity High` — drops the field, `.get("severity")` returns None,
# the finding reads as neither Blocking nor High nor deliverable, and the round reads as
# CLEAN. Codex executed it and reached STOP. The template PROMISES the machine checks the
# fields are present and well-formed; until now it did not. Same fail-open as r1's B1, one
# layer deeper: validate the VALUES, not the shape that carried them.
# ⛔ r6 High (Codex): the card said "non-trivial fixes -> CONTINUE" and the tool could not
# see it. A rule stated where it cannot be enforced is the drift this branch exists to
# remove. It is a per-round JUDGEMENT like `aim`, so it belongs in the header.
ROUND_REQUIRED = {"fixes_nontrivial": {True, False}}

REQUIRED = {
    "severity": {"Blocking", "High", "Medium", "Low"},
    "aim": {"deliverable", "instrument"},
    "fix_induced": {True, False},
    "disposition": {"fixed", "filed", "declined"},
}


def _validate(f: dict) -> None:
    """RAISES unless every decision-bearing field is present and in its allowed set."""
    for key, allowed in REQUIRED.items():
        if key not in f:
            raise ValueError(f"finding {f.get('id', '?')!r} has no `{key}` — refusing; a "
                             f"missing field reads as 'not Blocking, not deliverable'")
        if f[key] not in allowed:
            raise ValueError(f"finding {f.get('id', '?')!r} has {key}={f[key]!r}, "
                             f"not one of {sorted(map(str, allowed))}")
    if not str(f.get("component", "")).strip():
        raise ValueError(f"finding {f.get('id', '?')!r} has no `component` — thrashing is "
                         f"judged per component, so an unnamed one cannot arm it")


def _findings_span(body: str) -> str:
    """Just the `findings:` block. Bullets elsewhere are not findings."""
    lines = body.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if re.match(r"^findings:\s*$", l))
    except StopIteration:
        return ""
    out = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        out.append(line)
    return "\n".join(out)


def _scalarise(pairs) -> dict:
    """`k: v` strings -> a dict with real booleans."""
    f: dict = {}
    for pair in pairs:
        if ":" not in pair:
            continue
        k, v = pair.split(":", 1)
        v = v.strip().strip('"').strip("'")
        f[k.strip()] = {"true": True, "false": False}.get(v, v)
    return f


def _block_findings(body: str) -> list[dict]:
    """Block-style items under `findings:` — the ordinary YAML shape.

        findings:
          - id: H1
            severity: High
    """
    lines = body.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if re.match(r"^findings:\s*$", l))
    except StopIteration:
        return []
    out: list[dict] = []
    cur: list[str] = []
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):        # dedented out of the list
            break
        m = re.match(r"^\s*-\s*(.*)$", line)
        if m:
            if cur:
                out.append(_scalarise(cur))
            cur = [m.group(1)] if m.group(1).strip() else []
            if cur and cur[0].startswith("{"):        # a flow mapping; already handled
                cur = []
                continue
        elif cur is not None and ":" in line:
            cur.append(line.strip())
    if cur:
        out.append(_scalarise(cur))
    return [f for f in out if f]


def rounds_for(subject: str, writers: tuple[str, ...] = ("coordinator", "codex", "claude"),
               base: Path | None = None) -> list[dict]:
    """Every readable round document for `subject`, ordered by round number.

    ⭐ RELOCATION, 2026-10-20 — and the measurement is the whole argument. Per ROUND, across
    the 57 subjects where the procedure applies (261 rounds):

        at least one HALF (codex|claude) .... 254 of 261 = 97%
        a COORDINATOR document .............. 91 of 261 = 35%

    Reading only `coordinator/` capped feedability at 35% of rounds, and the procedure saw
    `rounds=0` on 81% of its subjects. The fields are the SAME grammar in the SAME `yaml`
    block; what changes is that they may live in the artifact the gate already forces to
    exist, rather than in a second one that is written a third of the time.

    ⚠ IT IS ADDITIVE, AND THE ORDER OF `writers` IS THE PRECEDENCE. A coordinator document
    still wins when it carries a header, because it ADJUDICATES the two halves and a half
    speaks only for its own reviewer. The halves are the fallback, not the replacement —
    reversing that would let one reviewer's unadjudicated view outrank the adjudication.

    ⚠ A header that is present but MALFORMED propagates its ValueError; the caller turns that
    into CANNOT RUN rather than a decision. A document with NO header block is skipped, which
    is how 254 existing halves stay silent instead of going red from birth.
    """
    # INJECTABLE so the PRECEDENCE and STRICTNESS rules are testable without the repository's
    # own 718-file review directory standing in as a fixture.
    base = (REPO / "docs" / "reviews") if base is None else base
    by_round: dict[int, dict] = {}
    for writer in writers:
        for f in sorted((base / writer).glob(f"{subject}-r*-{writer}.md")):
            try:
                h = parse_header(f.read_text())
            except ValueError:
                # ⛔ PRECEDENCE DECIDES STRICTNESS, AND A SUBSTRING TEST DOES NOT.
                # The COORDINATOR document is what the procedure has always depended on, so a
                # malformed header there still RAISES — a missing input is a failure, never a
                # pass. A HALF is best-effort: it is skipped, which is how 254 existing halves
                # stay silent instead of going red from birth.
                #
                # ⟳ The first version of this tested `"```yaml" in text` to tell "no header"
                # from "broken header". MEASURED, it dropped coordinator-only readability from
                # 10 subjects to 5: review prose DISCUSSES the header and quotes a yaml block,
                # so the substring matched documents that were never carrying one. That is the
                # same class `check-plan-file-tags.py` records — "prose ABOUT a tag must keep
                # passing; a bare substring test breaks every one of them."
                if writer == "coordinator":
                    raise
                continue
            if h["round"] in by_round:
                continue                      # earlier writer in `writers` already spoke
            h["source"] = f"{writer}/{f.name}"
            by_round[h["round"]] = h
    return sorted(by_round.values(), key=lambda r: r["round"])


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def _try(fn):
    """The value, or a NAMED marker if it raised.

    ⛔ A case that raises kills the suite and reports NOTHING — the runner counts `[FAIL]`
    lines and a traceback produces none. Found when a mutation that genuinely broke the
    parser scored "0 cases red": the case that should have failed crashed instead. Same
    shape as r4's classifier-coupling repair, one level in.
    """
    try:
        return fn()
    except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
        return f"RAISED {type(exc).__name__}"


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:
        return True
    return False


# ------------------------------------------------------------------ self-test
def exit_code_for(decision: str) -> int:
    """PURE. r6 Low (Codex): this mapping lived inline in `main()` and no case pinned it."""
    return {"STOP": 0, "CANNOT_RUN": 2}.get(decision, 1)


def _self_test() -> int:
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    # --- Q1 scope ---------------------------------------------------------
    # ⚠ The REAL classifier, deliberately. After the r3 redesign the value of these cases
    # is that check-review-recorded's taxonomy answers THIS question correctly — a fake
    # would assert only that the loop calls it.
    #
    # ⛔ LOADED INSIDE A CASE. r4 Low (Codex) said the coupling was caught only as a runtime
    # failure; the first repair added cases but left the load at the top, so a rename still
    # crashed the suite BEFORE any case ran — a traceback, naming nothing. Measured, and it
    # is why this is a try/except and not an added assertion: the control renamed
    # check-review-recorded.py and got a bare FileNotFoundError, not a named failure.
    # The stand-in keeps the remaining cases RUNNING so the report is complete; they will
    # go red too, which is correct — the rule cannot answer without its classifier.
    _prose_err = None
    try:
        _prose = _repo_is_prose()
    except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
        _prose_err, _prose = exc, (lambda _p: True)
    case("the borrowed classifier LOADS — a rename fails by name, not as a traceback",
         _prose_err, None)
    case("a migration needs the full loop",
         scope_for(["supabase/migrations/0028_x.sql"], _prose), "full-loop")
    case("a money path needs the full loop",
         scope_for(["lib/spend-ledger.ts"], _prose), "full-loop")
    # ⟳ r2 High: `scripts/` left CONTAINED_PREFIXES, so a harness script is full-loop now.
    case("a harness script is no longer assumed contained",
         scope_for(["scripts/gen-dashboard.py"], _prose), "full-loop")
    case("a guard that protects paid attempts needs the full loop",
         scope_for(["scripts/check-paid-caller-arrival.py"], _prose), "full-loop")
    case("docs alone are one round",
         scope_for(["docs/review-method.md"], _prose), "one-round")
    case("one risky path in a mixed set still forces the full loop",
         scope_for(["docs/x.md", "lib/auth/session.ts"], _prose), "full-loop")
    case("an empty diff is one round, not a crash",
         scope_for([], _prose), "one-round")
    # ⭐ r3 REDESIGN: the case that three hand-kept lists kept getting wrong. These files
    # are mode 755 and are gates 1 and 2 of check-schema-gates.sh.
    case("an executable schema gate UNDER docs/ needs the full loop",
         scope_for(["docs/superpowers/specs/2026-08-03-stable-blob-addressing/"
                    "mutate-schema.py"], _prose), "full-loop")
    case("...while ordinary prose beside it is still one round",
         scope_for(["docs/review-method.md"], _prose), "one-round")
    case("the classifier is INJECTED, so the rule stays pure",
         scope_for(["anything.ts"], lambda p: True), "one-round")
    # r4 Low (Codex): the cross-script coupling was caught only as a runtime traceback,
    # with no case naming it — so a rename of check-review-recorded.py would crash the
    # suite BEFORE it printed a count, and the failure would not say what broke.
    case("...and it still answers the question this rule delegates to it",
         (_prose("docs/review-method.md"),
          _prose("docs/superpowers/specs/2026-08-03-stable-blob-addressing/"
                 "mutate-schema.py")), (True, False))
    # r1 Blocking (Codex): an allowlist of risky prefixes silently downgraded a money path.
    case("a serve route that charges money needs the full loop",
         scope_for(["app/api/pdf/[id]/route.ts"], _prose), "full-loop")
    case("the paid worker pipeline needs the full loop",
         scope_for(["worker/run.ts"], _prose), "full-loop")
    case("what CI enforces needs the full loop",
         scope_for([".github/workflows/ci.yml"], _prose), "full-loop")
    case("an UNLISTED path is risky, never assumed contained",
         scope_for(["lib/some-new-module.ts"], _prose), "full-loop")
    case("a top-level config file is risky, never assumed contained",
         scope_for(["package.json"], _prose), "full-loop")

    # --- Q5 thrashing -----------------------------------------------------
    fix_a1 = {"round": 1, "findings": [{"fix_induced": True, "component": "a"}]}
    fix_a2 = {"round": 2, "findings": [{"fix_induced": True, "component": "a"}]}
    fix_b2 = {"round": 2, "findings": [{"fix_induced": True, "component": "b"}]}
    clean3 = {"round": 3, "findings": [{"fix_induced": False, "component": "a"}]}
    case("two consecutive fix-induced rounds in ONE component is thrashing",
         thrashing_component([fix_a1, fix_a2]), "a")
    case("two fix-induced rounds in DIFFERENT components is not thrashing",
         thrashing_component([fix_a1, fix_b2]), None)
    case("one fix-induced round is not thrashing",
         thrashing_component([fix_a1, clean3]), None)
    case("thrashing reads the LAST two rounds, not any two",
         thrashing_component([fix_a1, fix_a2, clean3]), None)
    case("a single round can never be thrashing",
         thrashing_component([fix_a1]), None)

    # ── review_scope: WHICH component a convened review examines ─────────────────────────────
    def _r(n, *comps):
        return {"round": n, "findings": [{"component": c, "fix_induced": True} for c in comps]}

    case("review_scope ranks by TOTAL appearances",
         review_scope([_r(1, "a", "b"), _r(2, "a"), _r(3, "a")]), ["a", "b"])
    # ⭐ THE IDENTITY CASE — the real measured disagreement, from `review-decision-procedure`,
    # whose own architecture review convened on `parse-header` (backlog #117). Consecutive-run
    # ranks `scope-for` first; total appearances ranks `parse-header` first, and it is right.
    _real = [_r(n, *( (["parse-header"] if n in (1,2,3,6,7) else [])
                    + (["scope-for"]    if n in (1,2,3,4)   else []) )) for n in range(1, 8)]
    case("a component that RETURNS AFTER A GAP outranks a longer consecutive run "
         "(parse-header 1,2,3,6,7 over scope-for 1,2,3,4)",
         review_scope(_real)[0], "parse-header")
    case("and the arming function still names the OTHER one, which is why they are separate "
         "functions rather than one",
         thrashing_component(_real[-2:]), "parse-header")
    case("a component counts ONCE per round however many findings it carried",
         review_scope([{"round": 1, "findings": [{"component": "a", "fix_induced": True}] * 5},
                       _r(2, "b"), _r(3, "b")]), ["b", "a"])
    case("ties break by name, so the order is deterministic",
         review_scope([_r(1, "zeta", "alpha")]), ["alpha", "zeta"])
    case("no rounds -> no scope, rather than a guess", review_scope([]), [])
    case("findings with no component are ignored rather than counted as one",
         review_scope([{"round": 1, "findings": [{"fix_induced": True}, {"component": "a"}]}]), ["a"])

    # ── scope_lead: is first place a LEAD, or the tie-break speaking? ─────────────────────────
    # ⭐ THE IDENTITY CASE, and it is the MEASURED shape, not a constructed one. Five of the ten
    # readable subjects have no lead; `arm-prod-drift-cron` is five components at one appearance
    # each. Both halves are asserted TOGETHER on purpose: the order still resolves
    # alphabetically (which is wanted, and was pinned deliberately) AND the lead reports that
    # the order is all it is. A case asserting only one half passes while the defect is live.
    _five = [{"round": 1, "findings": [{"component": c, "fix_induced": True} for c in
              ("merge-readiness", "schedule-durability", "cron-comment",
               "drift-window", "doc-row")]}]
    case("a 5-way tie ABSTAINS, and names every tied component rather than one of them",
         (scope_lead(_five)["abstain"], scope_lead(_five)["tied"], scope_lead(_five)["margin"]),
         (True, 5, 0))
    # ⚠ THE LIST, not its length. Asserting `tied == 5` leaves `sorted()` free to be dropped,
    # and the reader PRINTS these names — so an unstable order is a reader defect, caught here.
    case("...and the tied names are reported in a stable order, because the reader prints them",
         scope_lead(_five)["top"],
         ["cron-comment", "doc-row", "drift-window", "merge-readiness", "schedule-durability"])
    case("the reader says NO LEAD and lists the tied names on a second line",
         scope_lead_lines(scope_lead(_five)),
         ["  scope-rank: NO LEAD — 5 components tied at 1 appearance(s) — first place is the "
          "tie-break, not evidence",
          "              tied: cron-comment, doc-row, drift-window, merge-readiness, "
          "schedule-durability"])
    case("the reader names the winner and its margin when there IS a lead",
         scope_lead_lines(scope_lead(_real)),
         ["  scope-rank: parse-header — parse-header leads by 1 (n1=5 n2=4)"])
    case("the reader does not emit a tied line when there is nothing to tie",
         scope_lead_lines(scope_lead([])), ["  scope-rank: NO LEAD — no component appeared in "
                                           "any round"])
    case("...while review_scope's ORDER is unchanged and still alphabetical — the two coexist, "
         "which is the whole repair",
         review_scope(_five)[0], "cron-comment")
    # ⚠ ADJACENT NEGATIVE, not an absurd one: the boundary is margin 0 vs margin 1, so the case
    # that matters sits one appearance away from the tie it must not be confused with.
    _narrow = [_r(1, "a", "b"), _r(2, "a")]
    case("a margin of ONE is a lead, not a tie — the adjacent case to abstention",
         (scope_lead(_narrow)["abstain"], scope_lead(_narrow)["margin"],
          scope_lead(_narrow)["top"]), (False, 1, ["a"]))
    # TWO DISTINCT INPUTS for the margin arithmetic: a fixture that supplies one constant
    # cannot show the producer computes anything.
    _wide = [_r(n, "number-populations") for n in range(1, 6)] + [_r(6, "number-populations",
                                                                    "invariant-scope")]
    case("a WIDE margin is reported as its own value, not as a boolean",
         (scope_lead(_wide)["margin"], scope_lead(_wide)["n1"], scope_lead(_wide)["n2"]),
         (5, 6, 1))
    case("the real measured fixture leads by one, so it does NOT abstain",
         (scope_lead(_real)["abstain"], scope_lead(_real)["top"][0],
          scope_lead(_real)["margin"]), (False, "parse-header", 1))
    case("an empty round set ABSTAINS rather than naming a component",
         (scope_lead([])["abstain"], scope_lead([])["top"]), (True, []))
    case("a lone component leads trivially — n2 is 0, not undefined",
         (scope_lead([_r(1, "only")])["margin"], scope_lead([_r(1, "only")])["abstain"]),
         (1, False))
    # INDEPENDENT COPY: asserted on the tally itself, so the per-round rule is pinned without
    # going through the orderer that was the only reader of it before.
    case("scope_tally counts a component ONCE per round, asserted on the tally directly",
         scope_tally([{"round": 1, "findings": [{"component": "a"}] * 4}, _r(2, "a")]), {"a": 2})
    # A SECOND, DISTINCT input to the same producer: one fixture supplying one constant cannot
    # show that the tally computes anything.
    case("...and a different shape gives a different tally, not the same one",
         scope_tally([_r(1, "x", "y"), _r(2, "y")]), {"x": 1, "y": 2})

    # ── rounds_for: relocation to the halves ─────────────────────────────────────────────────
    import tempfile as _tf
    _hdr = ("# r{n}\n\n```yaml\nround: {n}\nfixes_nontrivial: false\nsubject: s\n"
            "findings:\n  - {{id: X, severity: Low, aim: instrument, fix_induced: false, "
            "component: {c}, disposition: fixed}}\n```\n")
    with _tf.TemporaryDirectory() as _d:
        _b = Path(_d)
        for _w in ("coordinator", "codex", "claude"):
            (_b / _w).mkdir()
        (_b / "coordinator/s-r1-coordinator.md").write_text(_hdr.format(n=1, c="from-coord"))
        (_b / "codex/s-r1-codex.md").write_text(_hdr.format(n=1, c="from-codex"))
        (_b / "codex/s-r2-codex.md").write_text(_hdr.format(n=2, c="from-codex"))
        case("a HALF supplies a round the coordinator never wrote — 97% vs 35% is the point",
             _try(lambda: [r["round"] for r in rounds_for("s", base=_b)]), [1, 2])
        case("...and the COORDINATOR still wins the round it does carry, because it adjudicates",
             _try(lambda: rounds_for("s", base=_b)[0]["findings"][0]["component"]),
             "from-coord")
        case("the source names the writer, so a reader can see where a round came from",
             _try(lambda: [r["source"] for r in rounds_for("s", base=_b)]),
             ["coordinator/s-r1-coordinator.md", "codex/s-r2-codex.md"])
        # ⭐ THE IDENTITY CASE for the regression this file already caused once: a half that
        # DISCUSSES the header quotes a yaml block, and a substring test read that as a broken
        # header — dropping coordinator-only readability from 10 subjects to 5.
        (_b / "claude/s-r3-claude.md").write_text(
            "# r3\n\nThe template says to write ```yaml\nround: 3\n``` which is prose, not a "
            "header.\n")
        # ⛔ `_try`, NOT a bare call. A mutation making this raise would otherwise kill the
        # suite and report ZERO [FAIL] lines — the helper's own docstring records that exact
        # miss, and this case reproduced it before being wrapped.
        case("PROSE in a half that quotes a yaml block is skipped, NOT raised",
             _try(lambda: [r["round"] for r in rounds_for("s", base=_b)]), [1, 2])
        (_b / "claude/s-r4-claude.md").write_text("# r4\n\nno header at all here\n")
        case("a half with no header block is skipped rather than failing the subject",
             _try(lambda: [r["round"] for r in rounds_for("s", base=_b)]), [1, 2])
        # ⛔ STRICTNESS IS KEYED TO THE WRITER. The coordinator document is what the procedure
        # has always depended on, so a broken header THERE is a failure, never a pass.
        (_b / "coordinator/s-r5-coordinator.md").write_text(
            "# r5\n\n```yaml\nsubject: s\nfindings: []\n```\n")
        case("a MALFORMED coordinator header still raises, so a missing input is not a pass",
             _raises(lambda: rounds_for("s", base=_b)), True)
        case("...while the same malformed block in a HALF is skipped",
             _raises(lambda: rounds_for("s", writers=("codex", "claude"), base=_b)), False)
        # ⚠ A SECOND SUBJECT IN A SECOND DIRECTORY. With one `subject` and one `base` across
        # every call, no case could tell either parameter from a constant — a subject filter
        # that ignored its argument would pass. `check-fixture-variation.py` caught it here.
        (_b / "coordinator/other-r1-coordinator.md").write_text(_hdr.format(n=1, c="other-1"))
        (_b / "coordinator/other-r2-coordinator.md").write_text(_hdr.format(n=2, c="other-2"))
        case("the subject argument SELECTS — a second subject in the same tree is separate",
             _try(lambda: [r["findings"][0]["component"]
                           for r in rounds_for("other", base=_b)]), ["other-1", "other-2"])
        case("...and 's' is unaffected by it, so the filter is not reading everything",
             _try(lambda: len(rounds_for("s", writers=("codex", "claude"), base=_b))), 2)
    with _tf.TemporaryDirectory() as _d2:
        _b2 = Path(_d2)
        for _w in ("coordinator", "codex", "claude"):
            (_b2 / _w).mkdir()
        (_b2 / "claude/s-r1-claude.md").write_text(_hdr.format(n=1, c="half-only"))
        case("a SECOND base directory is read, so `base` is not a constant either",
             _try(lambda: [r["source"] for r in rounds_for("s", base=_b2)]),
             ["claude/s-r1-claude.md"])

    # --- Q4a convergence --------------------------------------------------
    inst = {"severity": "Low", "aim": "instrument", "fix_induced": False, "component": "t"}
    deliv = {"severity": "Low", "aim": "deliverable", "fix_induced": False, "component": "d"}
    high = {"severity": "High", "aim": "instrument", "fix_induced": False, "component": "t"}
    _R = lambda n, fs, nt=False: {"round": n, "findings": fs, "fixes_nontrivial": nt}
    two_inst = [_R(1, [inst]), _R(2, [inst])]
    case("two consecutive instrument-only rounds converge",
         converged(two_inst, "full-loop")[0], True)
    case("a High blocks convergence even when aimed at the instrument",
         converged([_R(1, [inst]), _R(2, [high])], "full-loop")[0], False)
    case("a deliverable finding blocks convergence",
         converged([_R(1, [inst]), _R(2, [deliv])], "full-loop")[0], False)
    case("one clean round is NOT convergence on the full loop",
         converged([_R(1, [])], "full-loop")[0], False)
    case("one clean round IS convergence when the scope is one-round",
         converged([_R(1, [])], "one-round")[0], True)
    # r6 High (Codex): the card said non-trivial fixes CONTINUE; the tool could not see it.
    case("non-trivial fixes block convergence, as the card always said",
         converged([_R(1, [inst]), _R(2, [inst], nt=True)], "full-loop")[0], False)
    case("...and trivial ones do not",
         converged([_R(1, [inst]), _R(2, [inst], nt=False)], "full-loop")[0], True)
    case("no rounds never converges",
         converged([], "one-round")[0], False)

    # --- decide -----------------------------------------------------------
    case("no round recorded owes a round",
         decide([], "one-round", False)[0], "ROUND_OWED")
    case("thrashing outranks convergence",
         decide([fix_a1, fix_a2], "full-loop", True)[0], "ARCHITECTURE_REVIEW")
    case("converged but an unreviewed merging tree asks for TREE, never a round",
         decide(two_inst, "full-loop", False)[0], "TREE")
    case("converged and the tree was reviewed is STOP",
         decide(two_inst, "full-loop", True)[0], "STOP")
    case("not converged owes a round",
         decide([{"round": 1, "findings": [high]}], "full-loop", True)[0], "ROUND_OWED")
    # r5 High (Codex): adjacency was inferred from list position.
    _r1 = {"round": 1, "findings": [inst]}
    _r3 = {"round": 3, "findings": [inst]}
    case("a gapless sequence has no error", sequence_error(two_inst), None)
    case("a MISSING round is an error, not two consecutive rounds",
         sequence_error([_r1, _r3]) is not None, True)
    case("a DUPLICATE round number is an error",
         sequence_error([_r1, {"round": 1, "findings": []}]) is not None, True)
    case("a round with no number is an error",
         sequence_error([{"findings": []}]) is not None, True)
    case("r1 + r3 does NOT read as converged — it CANNOT RUN",
         decide([_r1, _r3], "full-loop", True)[0], "CANNOT_RUN")
    case("r1 + r3 with one fix-induced component does NOT arm an architecture review",
         decide([{"round": 1, "findings": [{"fix_induced": True, "component": "a"}]},
                 {"round": 3, "findings": [{"fix_induced": True, "component": "a"}]}],
                "full-loop", True)[0], "CANNOT_RUN")
    # r6 Low (Codex): the exit-code mapping was inline in main() and pinned by nothing.
    case("STOP exits 0", exit_code_for("STOP"), 0)
    case("CANNOT_RUN exits 2 — a refusal is not an ordinary failure",
         exit_code_for("CANNOT_RUN"), 2)
    case("a round owed exits 1", exit_code_for("ROUND_OWED"), 1)
    case("every decision carries a non-empty reason",
         all(decide(*a)[1] for a in [([], "one-round", False),
                                     ([fix_a1, fix_a2], "full-loop", True),
                                     (two_inst, "full-loop", False),
                                     (two_inst, "full-loop", True)]), True)


    # --- reading the record -----------------------------------------------
    good = ("# r3\n\n```yaml\nround: 3\nfixes_nontrivial: false\nsubject: s\nfindings:\n"
            "  - {id: L1, severity: Low, aim: instrument, fix_induced: true, "
            "component: c, disposition: filed}\n```\n")
    h = parse_header(good)
    case("a header parses its round number", h["round"], 3)
    case("a header parses its findings", len(h["findings"]), 1)
    case("a finding's booleans are real booleans", h["findings"][0]["fix_induced"], True)
    case("a finding's aim survives parsing", h["findings"][0]["aim"], "instrument")
    case("a document with NO header raises, never returns an empty round",
         _raises(lambda: parse_header("# r3\n\nprose only\n")), True)
    case("a header missing `round` raises rather than defaulting",
         _raises(lambda: parse_header("```yaml\nsubject: s\nfindings: []\n```")), True)
    case("an EXPLICIT empty list is a real round, not an error",
         parse_header("```yaml\nround: 9\nfixes_nontrivial: false\nfindings:\n```")["findings"], [])
    # r3 Blocking (Codex): an ABSENT key returned zero findings and validated nothing —
    # r1's B1 a third time, through a third shape. A missing key is a silence, not a claim.
    case("a header with NO findings key REFUSES rather than reading as clean",
         _raises(lambda: parse_header("```yaml\nround: 1\nfixes_nontrivial: false\nsubject: s\n```")), True)
    # r1 Blocking (Codex): block-style YAML parsed to ZERO findings, so a recorded High
    # reached STOP. Executed by the reviewer, not reasoned about.
    _block = ("```yaml\nround: 1\nfixes_nontrivial: false\nfindings:\n  - id: H1\n    severity: High\n"
              "    aim: deliverable\n    fix_induced: false\n    component: c\n"
              "    disposition: fixed\n```")
    case("an ordinary BLOCK-style finding is parsed, not silently dropped",
         parse_header(_block)["findings"][0]["severity"], "High")
    case("a block-style High does NOT reach STOP",
         decide([parse_header(_block)], "one-round", True)[0], "ROUND_OWED")
    case("a list item that parses to nothing REFUSES rather than shrinking the round",
         _raises(lambda: parse_header("```yaml\nround: 1\nfixes_nontrivial: false\nfindings:\n  - \n```")), True)
    # r2 Blocking (Codex): parity proved a dict appeared, not that it SAYS anything. A
    # missing colon drops the field, and a missing field reads as "not Blocking".
    case("a finding whose severity lost its colon REFUSES, it does not read as clean",
         _raises(lambda: parse_header(
             "```yaml\nround: 1\nfixes_nontrivial: false\nfindings:\n  - id: H1\n    severity High\n"
             "    aim: instrument\n    fix_induced: false\n```")), True)
    case("a finding with an out-of-set severity REFUSES",
         _raises(lambda: parse_header(
             "```yaml\nround: 1\nfixes_nontrivial: false\nfindings:\n  - {id: X, severity: Urgent, aim: instrument,"
             " fix_induced: false, component: c, disposition: fixed}\n```")), True)
    case("a finding with no component REFUSES — thrashing is judged per component",
         _raises(lambda: parse_header(
             "```yaml\nround: 1\nfixes_nontrivial: false\nfindings:\n  - {id: X, severity: Low, aim: instrument,"
             " fix_induced: false, disposition: fixed}\n```")), True)
    # r6 Medium (Codex): braces in ordinary gap prose are not a flow mapping.
    # ⚠ Wrapped in _try: under the mutation this RAISES, and an unwrapped raise kills the
    # suite and reports nothing — which is how that mutation first scored "0 cases red".
    case("braces in a halves GAP string are prose, not a finding",
         _try(lambda: len(parse_header(
             "```yaml\nround: 1\nfixes_nontrivial: false\nhalves:\n"
             '  claude: "GAP: connector returned {disabled}"\nfindings:\n```'
         )["findings"])), 0)
    # r2 Medium (Codex): a bullet inside a GAP block scalar is not a finding.
    case("a bullet inside a halves block scalar is not counted as a finding",
         len(parse_header(
             "```yaml\nround: 1\nfixes_nontrivial: false\nhalves:\n  claude: |\n    GAP: unavailable\n"
             "    - connector disabled\nfindings:\n  - {id: L1, severity: Low,"
             " aim: instrument, fix_induced: false, component: c, disposition: filed}\n```"
         )["findings"]), 1)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", default="origin/master")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()

    try:
        branch = _git("rev-parse", "--abbrev-ref", "HEAD")
        paths = [p for p in _git("diff", "--name-only",
                                 f"{args.base}...HEAD").split("\n") if p]
    except subprocess.CalledProcessError as exc:
        print(f"CANNOT RUN — git: {exc.stderr.strip() or exc}")
        return 2
    try:
        rounds = rounds_for(branch)
    except ValueError as exc:
        print(f"CANNOT RUN — a round document for '{branch}' has no usable header: {exc}")
        return 2

    scope = scope_for(paths, _repo_is_prose())
    # `check-review-recorded.py` owns the tree question; read ITS exit code rather than
    # re-deriving the rule, which is how a weaker second implementation gets written.
    tree = subprocess.run([sys.executable, str(REPO / "scripts" / "check-review-recorded.py"),
                           "--base", args.base], cwd=REPO, capture_output=True, text=True)
    if tree.returncode not in (0, 1):
        # ⚠ Surface ITS reason, not just its number. A cannot-run that does not say what
        # is missing leaves the reader to re-derive it, which is how the remedy gets
        # guessed at instead of applied.
        # ⚠ BOTH streams. `stdout or stderr` discards the refusal: measured — this
        # gate prints its `ok` for question one on STDOUT and its CANNOT RUN on
        # STDERR, so the falsy-or picks the reassuring half and drops the reason.
        out = (tree.stdout + "\n" + tree.stderr).strip().split("\n")
        # Prefer the lines that SAY the problem. Printing the first three prints its `ok`
        # line for question one and buries the refusal underneath it.
        why = [l for l in out if "CANNOT RUN" in l or l.startswith("FAILED")] or out[:2]
        print(f"CANNOT RUN — check-review-recorded exited {tree.returncode}:")
        for line in why[:3]:
            print(f"    {line.strip()}")
        return 2
    tree_reviewed = tree.returncode == 0

    decision, why = decide(rounds, scope, tree_reviewed)
    print(f"{decision} — {why}")
    print(f"  branch={branch}  scope={scope}  rounds={len(rounds)}  "
          f"tree_reviewed={tree_reviewed}")
    # ⛔ THE RANKER HAD NO READER. Until 2026-10-20 `review_scope` was called only by this
    # file's own self-test, while `dev-process.md` said running this script computes it.
    for line in scope_lead_lines(scope_lead(rounds)):
        print(line)
    for r in rounds:
        aims = ",".join(f.get("aim", "?") for f in r["findings"]) or "none"
        print(f"    r{r['round']}: {len(r['findings'])} finding(s) [{aims}]")
    return exit_code_for(decision)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

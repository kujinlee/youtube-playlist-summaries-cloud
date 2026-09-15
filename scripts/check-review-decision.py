#!/usr/bin/env python3
"""What does the review loop do next? — answered from recorded evidence, not recall.

    python3 scripts/check-review-decision.py              # decide for the current branch
    python3 scripts/check-review-decision.py --self-test  # 47 cases

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
    return True, (f"{need} round(s) with no Blocking/High and nothing in the deliverable")


# ------------------------------------------------------- Q4b: tree identity
TREE_ANSWERS = (
    "land the editorial fixes AHEAD of the final round",
    "keep the last fixes uncommitted so the reviewer sees what ships",
    "declare NO-REVIEW: <reason> in the PR body",
    "run another round — LAST resort, never first",
)


def decide(rounds: list[dict], scope: str, tree_reviewed: bool) -> tuple[str, str]:
    """PURE. One decision and the reason for it.

    ⚠ ORDER IS LOAD-BEARING. Thrashing outranks convergence, because a design fighting
    itself converges on nothing worth having. And tree identity is checked LAST and
    answered as TREE — never as ROUND_OWED — so the two questions PR #302 merged stay apart.
    """
    if not rounds:
        return "ROUND_OWED", f"no round recorded; a {scope} change needs at least one"
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
    findings = [_scalarise(fm.group(1).split(",")) for fm in FINDING_RE.finditer(body)]
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
    return {"round": int(rm.group(1)), "findings": findings}


# ⛔ r2 Blocking (Codex): PARITY PROVED AN ITEM BECAME A DICT, NOT THAT IT SAYS ANYTHING.
# A missing colon — `severity High` — drops the field, `.get("severity")` returns None,
# the finding reads as neither Blocking nor High nor deliverable, and the round reads as
# CLEAN. Codex executed it and reached STOP. The template PROMISES the machine checks the
# fields are present and well-formed; until now it did not. Same fail-open as r1's B1, one
# layer deeper: validate the VALUES, not the shape that carried them.
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


def rounds_for(subject: str) -> list[dict]:
    """Every coordinator round document for `subject`, ordered by round number.

    A document without a header propagates its ValueError — the caller turns that into
    CANNOT RUN rather than a decision.
    """
    d = REPO / "docs" / "reviews" / "coordinator"
    out = []
    for f in sorted(d.glob(f"{subject}-r*-coordinator.md")):
        h = parse_header(f.read_text())
        h["source"] = f.name
        out.append(h)
    return sorted(out, key=lambda r: r["round"])


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:
        return True
    return False


# ------------------------------------------------------------------ self-test
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
    _prose = _repo_is_prose()
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

    # --- Q4a convergence --------------------------------------------------
    inst = {"severity": "Low", "aim": "instrument", "fix_induced": False, "component": "t"}
    deliv = {"severity": "Low", "aim": "deliverable", "fix_induced": False, "component": "d"}
    high = {"severity": "High", "aim": "instrument", "fix_induced": False, "component": "t"}
    two_inst = [{"round": 1, "findings": [inst]}, {"round": 2, "findings": [inst]}]
    case("two consecutive instrument-only rounds converge",
         converged(two_inst, "full-loop")[0], True)
    case("a High blocks convergence even when aimed at the instrument",
         converged([{"round": 1, "findings": [inst]},
                    {"round": 2, "findings": [high]}], "full-loop")[0], False)
    case("a deliverable finding blocks convergence",
         converged([{"round": 1, "findings": [inst]},
                    {"round": 2, "findings": [deliv]}], "full-loop")[0], False)
    case("one clean round is NOT convergence on the full loop",
         converged([{"round": 1, "findings": []}], "full-loop")[0], False)
    case("one clean round IS convergence when the scope is one-round",
         converged([{"round": 1, "findings": []}], "one-round")[0], True)
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
    case("every decision carries a non-empty reason",
         all(decide(*a)[1] for a in [([], "one-round", False),
                                     ([fix_a1, fix_a2], "full-loop", True),
                                     (two_inst, "full-loop", False),
                                     (two_inst, "full-loop", True)]), True)


    # --- reading the record -----------------------------------------------
    good = ("# r3\n\n```yaml\nround: 3\nsubject: s\nfindings:\n"
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
         parse_header("```yaml\nround: 9\nfindings:\n```")["findings"], [])
    # r3 Blocking (Codex): an ABSENT key returned zero findings and validated nothing —
    # r1's B1 a third time, through a third shape. A missing key is a silence, not a claim.
    case("a header with NO findings key REFUSES rather than reading as clean",
         _raises(lambda: parse_header("```yaml\nround: 1\nsubject: s\n```")), True)
    # r1 Blocking (Codex): block-style YAML parsed to ZERO findings, so a recorded High
    # reached STOP. Executed by the reviewer, not reasoned about.
    _block = ("```yaml\nround: 1\nfindings:\n  - id: H1\n    severity: High\n"
              "    aim: deliverable\n    fix_induced: false\n    component: c\n"
              "    disposition: fixed\n```")
    case("an ordinary BLOCK-style finding is parsed, not silently dropped",
         parse_header(_block)["findings"][0]["severity"], "High")
    case("a block-style High does NOT reach STOP",
         decide([parse_header(_block)], "one-round", True)[0], "ROUND_OWED")
    case("a list item that parses to nothing REFUSES rather than shrinking the round",
         _raises(lambda: parse_header("```yaml\nround: 1\nfindings:\n  - \n```")), True)
    # r2 Blocking (Codex): parity proved a dict appeared, not that it SAYS anything. A
    # missing colon drops the field, and a missing field reads as "not Blocking".
    case("a finding whose severity lost its colon REFUSES, it does not read as clean",
         _raises(lambda: parse_header(
             "```yaml\nround: 1\nfindings:\n  - id: H1\n    severity High\n"
             "    aim: instrument\n    fix_induced: false\n```")), True)
    case("a finding with an out-of-set severity REFUSES",
         _raises(lambda: parse_header(
             "```yaml\nround: 1\nfindings:\n  - {id: X, severity: Urgent, aim: instrument,"
             " fix_induced: false, component: c, disposition: fixed}\n```")), True)
    case("a finding with no component REFUSES — thrashing is judged per component",
         _raises(lambda: parse_header(
             "```yaml\nround: 1\nfindings:\n  - {id: X, severity: Low, aim: instrument,"
             " fix_induced: false, disposition: fixed}\n```")), True)
    # r2 Medium (Codex): a bullet inside a GAP block scalar is not a finding.
    case("a bullet inside a halves block scalar is not counted as a finding",
         len(parse_header(
             "```yaml\nround: 1\nhalves:\n  claude: |\n    GAP: unavailable\n"
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
    for r in rounds:
        aims = ",".join(f.get("aim", "?") for f in r["findings"]) or "none"
        print(f"    r{r['round']}: {len(r['findings'])} finding(s) [{aims}]")
    return 0 if decision == "STOP" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

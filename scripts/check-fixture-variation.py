#!/usr/bin/env python3
"""Every parameter of a function under test must be VARIED by its cases, or be exempt in writing.

    python3 scripts/check-fixture-variation.py                 # the declared POPULATION
    python3 scripts/check-fixture-variation.py --self-test     # 21 cases

⛔ WHAT THIS EXISTS FOR, AND IT WAS BOUGHT WITH SIX ADVERSARIAL ROUNDS ON ONE FILE.
Six rounds of review on `check-plan-code.py` produced six Blocking findings, and five of them are
ONE defect: a case that cannot fail for the thing it names, because every case passes the SAME
value for the parameter that decides it. The reviews found them one axis at a time:

    r2  the WANT was derived from the subject          -> fixed the want
    r3  the want was a literal but the INPUT was far
        from the boundary                              -> fixed the input's magnitude
    r5  the input was at the boundary of magnitude
        but had no POSITION ("S" * 5000 reads the
        same from either end)                          -> fixed the input's position
    r6  the label was varied on every axis and the
        OTHER TWO ARGUMENTS never were: every case
        called `progress_line(164, 434, …)`, whose
        head is exactly ten characters, so
        `PROGRESS_WIDTH - len(head)` and
        `PROGRESS_WIDTH - 10` are indistinguishable    -> and here we are

Each round improved the fixture along the axis the PREVIOUS round had been bitten by. The
generator is not any one of those axes. It is that **the fixtures vary one argument and the
reviews have been improving that one argument**. The question that catches all four at once is not
"is this input at the edge?" but:

    FOR EACH PARAMETER OF EACH FUNCTION UNDER TEST, DO AT LEAST TWO CASES PASS DIFFERENT VALUES?

Under that rule `progress_line` fails on `done`, on `total` and on the head width — which is
exactly what r6 found by hand, after five rounds of not finding it. A guard, not a rule to
remember: this project's own standard is that a convention catches what you READ and a script
catches what is THERE.

⚠ WHAT THIS CANNOT DO, SAID PLAINLY SO PASSING IT IS NOT MISTAKEN FOR SAFETY. It compares the
SOURCE TEXT of arguments. Two call sites passing `x` and `y` satisfy it even if both evaluate to
the same thing; two passing `"S" * 5000` and `"S" * 5000` do not. So it is a floor — it proves a
parameter was *thought about*, never that the values chosen are good ones. It cannot see that
`"S" * 5000` and `"E" * 5000` are both position-free (r5's Blocking), and it would NOT have caught
r5 B1. It catches r6's class, which is the one no human question caught for five rounds.
"""
from __future__ import annotations
import argparse
import ast
import pathlib
import sys

# ── THE POPULATION, DECLARED ─────────────────────────────────────────────────────────────
# §21: a check has a RULE and a POPULATION and they fail separately. An empty population is
# CANNOT RUN, never a pass — a zero over nothing is not a finding.
POPULATION = ("scripts/check-plan-code.py",)

# ── EXEMPTIONS, EACH WITH ITS REASON ─────────────────────────────────────────────────────
# `"<function>.<parameter>": "<why one value is right>"`. A parameter genuinely decided by one
# value is not a defect; an UNWRITTEN one is. Prose here is the artefact that says the question
# was asked and answered, which is what r4 L1 proved is needed.
EXEMPT: dict[str, str] = {
    "progress_line.label": "varied on magnitude AND position by the r3/r5 cases; the axes are "
                           "the point, not the count of distinct literals",
    "diagnostic_tail.window": "the budget is a module constant with its own boundary cases and "
                              "its own manifest entry; callers never pass it",
    "run_suite_parts.d": "the staging directory is the fixture's own temp dir; what varies "
                         "between its call sites is `name`, which is the parameter that "
                         "selects the suite. A second directory would test the tempfile "
                         "module, not this function",
}


def _is_case_arg(node: ast.AST) -> bool:
    """A `case(...)` call is the assertion, not a call under test."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "case"


def analyse(source: str, path: str) -> tuple[list[str], int]:
    """(findings, parameters examined). PURE — no filesystem, no argv.

    A parameter is EXAMINED when its function is defined in this module and called at least
    twice from the suite. Called once is reported too: one call site cannot vary anything.
    """
    tree = ast.parse(source)
    defs: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            defs.setdefault(node.name, node)

    suite = next((n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_self_test"), None)
    if suite is None:
        return ([f"CANNOT RUN — {path} has no `_self_test`, so there are no cases to read. "
                 f"NOT CHECKED."], 0)

    # arg source text per (function, parameter), across every call site inside the suite
    seen: dict[tuple[str, str], list[str]] = {}
    for node in ast.walk(suite):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        fn = defs.get(node.func.id)
        if fn is None or _is_case_arg(node):
            continue
        names = [a.arg for a in fn.args.args]
        given = set()
        for i, arg in enumerate(node.args):
            if i < len(names):
                seen.setdefault((fn.name, names[i]), []).append(ast.unparse(arg))
                given.add(names[i])
        for kw in node.keywords:
            if kw.arg:
                seen.setdefault((fn.name, kw.arg), []).append(ast.unparse(kw.value))
                given.add(kw.arg)
        # ⛔ OMITTING A DEFAULTED ARGUMENT IS A VALUE, and the first version of this did not
        # count it. `mutate_delivered(root)` and `mutate_delivered(root, progress=…)` are the
        # two sides of the reporter seam that cost this branch its first Blocking — read as
        # "one call site", they looked unvaried while being the best-covered parameter here.
        # A parameter with no default cannot be omitted, so this only ever ADDS a real value.
        defaulted = names[len(names) - len(fn.args.defaults):] if fn.args.defaults else []
        for d in defaulted:
            if d not in given:
                seen.setdefault((fn.name, d), []).append("<omitted, default>")

    findings = []
    for (fn, param), values in sorted(seen.items()):
        if f"{fn}.{param}" in EXEMPT:
            continue
        if len(set(values)) < 2:
            only = values[0] if values else "?"
            findings.append(
                f"{path}: `{fn}({param}=…)` is passed the SAME value at every call site in the "
                f"suite ({len(values)}x `{only[:40]}`). No case can tell that parameter apart "
                f"from a constant, so any clause that reads it is unguarded. Vary it, or add "
                f"`{fn}.{param}` to EXEMPT with the reason one value is right.")
    return findings, len(seen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("paths", nargs="*", help="override the declared POPULATION")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()

    root = pathlib.Path(__file__).resolve().parent.parent
    targets = [pathlib.Path(p) for p in a.paths] or [root / p for p in POPULATION]
    missing = [str(p) for p in targets if not p.is_file()]
    if missing or not targets:
        print(f"CANNOT RUN — population is empty or unreadable: {missing or 'no targets'}. "
              f"A zero over nothing is not a pass. NOT CHECKED.", file=sys.stderr)
        return 2

    all_findings, examined = [], 0
    for t in targets:
        f, n = analyse(t.read_text(), t.name)
        all_findings += f
        examined += n
    if any(x.startswith("CANNOT RUN") for x in all_findings):
        for x in all_findings:
            print(f"  {x}", file=sys.stderr)
        return 2
    if all_findings:
        print(f"FAILED — {len(all_findings)} parameter(s) never varied by any case:")
        for x in all_findings:
            print(f"  ✗ {x}")
        return 1
    print(f"fixture variation OK — {examined} parameter(s) examined across {len(targets)} "
          f"file(s), {len(EXEMPT)} exempt with a written reason")
    return 0


def _self_test() -> int:
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    SRC = '''
def progress_line(done, total, label):
    return f"[{done}/{total}] {label}"

def _self_test():
    case("a", progress_line(164, 434, "x"), "…")
    case("b", progress_line(164, 434, "y"), "…")
'''
    f, n = analyse(SRC, "t.py")
    # ⛔ THE CENTRAL CASE: `done` and `total` are the same at both sites; `label` differs.
    case("a parameter passed one value at every site is reported",
         sorted(x.split("`")[1] for x in f), ["progress_line(done=…)", "progress_line(total=…)"])
    case("...and a parameter that DOES vary is not", any("label" in x for x in f), False)
    case("...and the count of examined parameters is reported, not just the failures", n, 3)

    VARIED = SRC.replace('progress_line(164, 434, "y")', 'progress_line(7, 38, "y")')
    f2, _ = analyse(VARIED, "t.py")
    case("varying both at one site clears both", f2, [])

    # One call site cannot vary anything, and that is the shape r6 B1 actually had for `head`.
    # ⚠ NOT named `progress_line`: the live EXEMPT covers `progress_line.label`, so reusing
    # that name would have this case measure the exemption instead of the rule. Measured — it
    # reported 2 findings where the rule gives 3.
    ONE = '''
def pline(done, total, label):
    return ""

def _self_test():
    case("a", pline(164, 434, "x"), "…")
'''
    f3, _ = analyse(ONE, "t.py")
    case("a single call site is reported for every parameter", len(f3), 3)
    case("...and the message says how many times the value appears",
         "1x" in f3[0], True)

    # Keyword arguments are call sites too — `mutate_delivered(root, progress=…)` is how this
    # file's own reporter seam is driven, and reading only positional args would miss it.
    KW = '''
def f(a, b):
    return None

def _self_test():
    case("x", f(1, b=2), None)
    case("y", f(1, b=3), None)
'''
    f4, _ = analyse(KW, "t.py")
    case("keyword arguments count as call sites", [x.split("`")[1] for x in f4], ["f(a=…)"])

    # ⛔ OMITTING A DEFAULTED ARGUMENT IS A VALUE. Without this, the reporter seam that cost
    # this branch its first Blocking — `f(1)` beside `f(2, b=3)` — reads as one call site and is
    # reported as unvaried, which is a false positive on the best-covered parameter in the file.
    DEFAULTED = '''
def g(a, b=None):
    return None

def _self_test():
    case("x", g(1), None)
    case("y", g(2, b=3), None)
'''
    fD, nD = analyse(DEFAULTED, "t.py")
    case("omitting a defaulted argument counts as a distinct value", (fD, nD), ([], 2))

    # An exemption is honoured, and ONLY for the named function+parameter.
    global EXEMPT
    _saved = dict(EXEMPT)
    try:
        EXEMPT = {"progress_line.done": "test"}
        f5, _ = analyse(SRC, "t.py")
        case("an exemption removes exactly its own finding",
             [x.split("`")[1] for x in f5], ["progress_line(total=…)"])
        EXEMPT = {"progress_line.nonexistent": "test"}
        f6, _ = analyse(SRC, "t.py")
        case("...and an exemption for a parameter that does not exist changes nothing",
             len(f6), 2)
    finally:
        EXEMPT = _saved

    # ⚠ A file with no suite is CANNOT RUN, not a pass — the rule and the population fail
    # separately (§21), and a zero over an unread population is the shape this project has
    # been burned by four times.
    f7, n7 = analyse("def f(a):\n    return a\n", "t.py")
    # ⚠ `any(...)` NOT `f7[0]` — indexing raises when the list is empty, which is exactly what
    # this case's own mutation produces, so the suite would DIE rather than report. A case that
    # dies from its defect attributes nothing; a case that reports it names the guard.
    case("a file with no _self_test is CANNOT RUN, not a clean bill",
         (any(x.startswith("CANNOT RUN") for x in f7), n7), (True, 0))

    # `case(...)` itself is the assertion, never a subject.
    CASECALL = '''
def case(name, got, want):
    return None

def _self_test():
    case("a", 1, 1)
    case("b", 1, 1)
'''
    f8, _ = analyse(CASECALL, "t.py")
    case("the case() helper is not treated as a function under test", f8, [])

    # A function defined but never driven by the suite has no call sites to compare, so it is
    # not examined — silence here is correct, and saying so is what stops a reader assuming
    # this guard covers every function in the file.
    UNCALLED = '''
def helper(a, b):
    return a

def _self_test():
    case("a", 1, 1)
'''
    f9, n9 = analyse(UNCALLED, "t.py")
    case("a function the suite never calls is not examined", (f9, n9), ([], 0))

    # Private helpers (leading underscore) are test plumbing, not the subject.
    PRIV = '''
def _mini(root, val):
    return None

def _self_test():
    _mini(1, 2)
    _mini(1, 2)
'''
    f10, n10 = analyse(PRIV, "t.py")
    case("a private helper is test plumbing, not a subject", (f10, n10), ([], 0))

    case("the declared population is not empty", len(POPULATION) > 0, True)
    case("...and every exemption carries a non-empty reason",
         all(isinstance(v, str) and v.strip() for v in EXEMPT.values()), True)
    case("...and every exemption names a function and a parameter",
         all(len(k.split(".")) == 2 and all(k.split(".")) for k in EXEMPT), True)

    # The real subject, read from disk — the guard must be able to run on what it ships for.
    root = pathlib.Path(__file__).resolve().parent.parent
    live = root / POPULATION[0]
    # ⚠ UNCONDITIONAL. These were guarded by `if live.is_file()`, so the case COUNT varied with
    # the state of the world — and a suite whose count moves cannot be ratcheted. The existence
    # of the file is its own case; the reads below assume it and fail loudly if wrong.
    case("the declared population exists on disk", live.is_file(), True)
    f11, n11 = analyse(live.read_text() if live.is_file() else "", live.name)
    case("...and reading it examines a non-zero number of parameters", n11 > 0, True)
    case("...and it reports no CANNOT RUN on the live file",
         any(x.startswith("CANNOT RUN") for x in f11), False)

    case("main() refuses an unreadable population with rc 2",
         main(["/nonexistent/nope.py"]), 2)

    print(f"\n{ok}/{ok + fail} passed")
    if ok + fail != 21:
        print(f"  [DRIFT] the docstring declares 21 cases; the suite ran {ok + fail}")
        return 1
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

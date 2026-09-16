#!/usr/bin/env python3
"""You changed ONE member of an enumerable set. Here are the others.

    python3 scripts/peer-sites.py --diff master      # peers of everything a branch touched
    python3 scripts/peer-sites.py FILE:LINE          # peers of one site
    python3 scripts/peer-sites.py --self-test        # 32 cases

⛔ WHAT THIS EXISTS FOR, AND IT WAS MEASURED BEFORE IT WAS BUILT.
"Fix the instance, miss the sibling" is this author's dominant failure shape — written down as a
memory rule on 2026-08-27 after four instances in one slice, and then repeated on four consecutive
branches with the rule in hand. Having the rule did not help, so this is the attempt at a mechanism.

⭐ THE DESIGN CAME OUT OF AN EXPERIMENT, NOT AN INTUITION, AND THE EXPERIMENT REFUTED THE FIRST
IDEA. Six real misses were replayed against candidate detectors on their own pre-fix trees:

    miss                                   query that finds the sibling          noise
    504 arm cased, 500 arm missed          the function's value-returning exits  ZERO
    POST preamble cased, write missed      same                                  ZERO
    source_shell escaped, index_html not   raw value into a markup f-string      ~9 others
    one doc paragraph fixed, twin missed   grep the phrase                       ~5 others
    one clause of a 4-clause verdict       (none — needs reading prose)          —
    `%2e` fixed, `%25` opened              (none — needs knowing unquote isn't
                                            idempotent)                          —

So: **3 of 6 are mechanical, not the 4 of 5 that was guessed**, and the *general* "find similar
lines anywhere in the repo" detector — the thing originally proposed — is the WEAK version: it needs
a hand-written query per defect class and ran at ~11% precision. The narrow version is the good one.

⛔ THE RULE THIS ENCODES: ask for PEERS WITHIN A CONTAINER, never for similar lines anywhere.
A container is bounded by construction, so every member is legitimately in scope and there is no
such thing as a false positive — which is why this prints 2-4 lines and can be read every time.
An unbounded shape search is 90% noise and gets scrolled past, which is worse than silence because
it looks like coverage.

⚠ WHAT IT CANNOT SEE, STATED RATHER THAN DISCOVERED LATER. Two of the six misses have no syntactic
container: one lived in the clauses of an English sentence, the other in the levels of an encoding.
Those belong to the reviewer clause in `docs/review-method.md`, not here. **A green run of this
script is not evidence that a class was searched** — it is evidence that three container shapes were.

NOT A GATE. It advises and always exits 0 on a well-formed run; it has nothing to refuse. `--self-test`
and a mutation manifest are what keep it honest (backlog #122's lesson, applied at birth rather than
as debt).
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent


class Peer:
    """One member of an enumerable set, and whether the diff touched it."""

    def __init__(self, lineno: int, text: str, touched: bool):
        self.lineno, self.text, self.touched = lineno, text, touched

    def __repr__(self) -> str:                                    # pragma: no cover - debug only
        return f"Peer({self.lineno}, touched={self.touched})"


def containers(src: str) -> "list[tuple[str, str, list[int]]]":
    """Every enumerable set in `src`, as (kind, label, member line numbers). PURE.

    ⛔ THREE SHAPES, AND THE LIST IS DELIBERATELY SHORT. Each is bounded by its own syntax, so
    membership is decidable and complete — that is the whole property that makes the output quiet.
    Adding a shape whose membership is a judgement call (say, "similar expressions") would import
    the noise this design exists to avoid, and the docstring above says so with numbers.
    """
    out: "list[tuple[str, str, list[int]]]" = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    # ⚠ AN `elif` IS AN `If` IN ANOTHER `If`'s `orelse`, so `ast.walk` yields one chain once per
    # arm and each yield reports a SUFFIX of the head's members. Deduping on the member tuple does
    # not help — the tuples genuinely differ. MEASURED: a three-arm chain printed twice. Only the
    # HEAD reports, so the non-heads are collected first and skipped.
    elifs = {arm.orelse[0] for arm in ast.walk(tree)
             if isinstance(arm, ast.If) and len(arm.orelse) == 1
             and isinstance(arm.orelse[0], ast.If)}
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node in elifs:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # ⚠ NESTED FUNCTIONS ARE THEIR OWN CONTAINERS, so a `return` inside a closure must not
            # be counted as an exit of the enclosing function. `ast.walk` does not know that.
            rets = [n.lineno for n in _own_nodes(node, ast.Return) if n.value is not None]
            if len(rets) > 1:
                out.append(("exits", f"{node.name}()", sorted(rets)))
        if isinstance(node, ast.Try) and len(node.handlers) > 1:
            out.append(("except", "try block", sorted(h.lineno for h in node.handlers)))
        if isinstance(node, ast.If):
            chain = _if_chain(node)
            if len(chain) > 1:
                out.append(("branches", "if/elif chain", sorted(chain)))
    return out


def _own_nodes(fn: ast.AST, want: type) -> "list":
    """Nodes of type `want` belonging to `fn` itself, not to a nested function. PURE."""
    found = []
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue                                   # a nested scope owns its own exits
        if isinstance(n, want):
            found.append(n)
        stack.extend(ast.iter_child_nodes(n))
    return found


def _if_chain(node: ast.If) -> "list[int]":
    """Line numbers of every arm in one if/elif chain, the `if` included. PURE.

    ⚠ An `elif` is an `If` inside `orelse`, so walking naively reports the same chain once per arm.
    Only the HEAD is reported: a chain is counted from the arm that has no `If` parent, which
    `containers` gets for free because a nested arm's own entry is a subset and is filtered by the
    dedupe in `report`.
    """
    arms, cur = [node.lineno], node
    while len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
        cur = cur.orelse[0]
        arms.append(cur.lineno)
    if cur.orelse:
        arms.append(cur.orelse[0].lineno)
    return arms


def parse_hunks(diff: str) -> "set[int]":
    """Line numbers the NEW side of a unified diff added or changed. PURE.

    ⛔ SPLIT FROM THE GIT CALL — this project's *separate the RULE from the FETCH*, and the split
    was forced by `check-fixture-variation`, which refused the welded version: with parsing and
    subprocess in one function, no case could vary `ref` or `path` without depending on git being
    present, and a git-dependent case is exactly the ambient trap that has bitten this repo four
    times. The harness stages `scripts/` into a temp tree with **no `.git`**, so such a case would
    have passed locally and failed under `--mutate .`. Parsing a fixture string needs no world.
    """
    out: "set[int]" = set()
    for line in diff.split("\n"):
        if not line.startswith("@@"):
            continue
        try:
            new = line.split("+", 1)[1].split("@@", 1)[0].strip()
            # ⛔ `max(n, 1)` IS ONLY FOR AN ABSENT COUNT, NOT A ZERO ONE — the first version
            # applied it to both and invented a line. `@@ -4,2 +3,0 @@` is a pure DELETION: the new
            # side gained nothing at line 3, and claiming line 3 makes the deletion look like a
            # change to whatever now sits there. `@@ -1 +7 @@` omits the count entirely and DOES
            # mean one line. Found by writing the deletion case, not by reading the code.
            start, sep, count = new.partition(",")
            n = int(count) if sep else 1
            out.update(range(int(start), int(start) + n))
        except (IndexError, ValueError):
            continue                       # a malformed header is skipped, never fatal
    return out


def changed_lines(ref: str, path: str) -> "set[int] | None":
    """`parse_hunks` of `git diff ref -- path`, or **None when git could not answer**.

    ⛔ NONE, NOT AN EMPTY SET — and the first version returned `set()` on failure, which is exactly
    the fail-open this project files hardest against: *"cannot run" is a FAILURE, never a pass*. An
    empty set means "git answered: nothing changed"; a git that could not run means "unknown", and
    the two must not share a value. MEASURED by mutation: with the `returncode` check deleted the
    suite stayed green, because a bad ref produced an empty set either way.
    """
    try:
        r = subprocess.run(["git", "-C", str(REPO), "diff", "-U0", ref, "--", path],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return parse_hunks(r.stdout)


def report(src: str, touched: "set[int]") -> "list[str]":
    """The advisory lines: containers the diff touched PARTIALLY. PURE.

    ⛔ PARTIALLY IS THE WHOLE FILTER. A container where every member was touched needs no
    prompting, and one where none were is not this diff's business. Output is therefore
    proportional to the actual risk rather than to the size of the file — which is what makes it
    readable every time rather than something to scroll past.
    """
    lines = src.split("\n")
    seen: "set[tuple]" = set()
    out: "list[str]" = []
    for kind, label, members in sorted(containers(src), key=lambda c: c[2]):
        hit = [m for m in members if m in touched]
        # ⚠ TWO GUARDS, NOT ONE COMPOUND CONDITION, and the reason is worth stating because this
        # project's precedent is to DROP a manifest entry rather than split a line to manufacture
        # an anchor. The test applied: *would I write it this way if the harness did not exist?*
        # Yes — these are unrelated reasons that happen to share an outcome, and one expression
        # reading `not hit or len(hit) == len(members)` makes a reader derive that. Splitting is a
        # clarity win that a second anchor follows from; it is not a contortion serving the tool.
        if not hit:
            continue            # nothing here was touched — not this diff's business
        if len(hit) == len(members):
            continue            # every member was touched — there is nothing left to prompt
        key = (kind, tuple(members))
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{label}: you changed {len(hit)} of {len(members)} {kind}")
        for m in members:
            mark = "  >" if m in touched else "   "
            body = lines[m - 1].strip() if 0 < m <= len(lines) else ""
            out.append(f"{mark} :{m:<6} {body[:84]}")
    return out


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site", nargs="?", help="FILE:LINE — peers of one site")
    ap.add_argument("--diff", metavar="REF", help="peers of everything changed since REF")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()

    if a.diff:
        r = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", a.diff],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"CANNOT RUN — `git diff --name-only {a.diff}` failed. Treat this as NOT CHECKED.",
                  file=sys.stderr)
            return 2
        paths = [p for p in r.stdout.split("\n") if p.endswith(".py")]
        total = 0
        for rel in paths:
            f = REPO / rel
            if not f.is_file():
                continue
            touched = changed_lines(a.diff, rel)
            if touched is None:
                print(f"CANNOT RUN — `git diff` could not answer for {rel}. NOT CHECKED.",
                      file=sys.stderr)
                continue
            adv = report(f.read_text(), touched)
            if adv:
                total += 1
                print(f"\n── {rel} " + "─" * max(0, 60 - len(rel)))
                for line in adv:
                    print(line)
        if not total:
            print(f"no partially-touched containers in {len(paths)} changed python file(s).")
        print("\n⚠ This checks THREE container shapes. A class living in prose, or in the levels of "
              "an encoding, is invisible here — see docs/review-method.md.")
        return 0

    if a.site:
        path, _, ln = a.site.partition(":")
        f = pathlib.Path(path)
        if not f.is_file() or not ln.isdigit():
            print(f"CANNOT RUN — expected FILE:LINE, got {a.site!r}.", file=sys.stderr)
            return 2
        for line in report(f.read_text(), {int(ln)}) or ["no container holds that line."]:
            print(line)
        return 0

    ap.print_help()
    return 2


def _self_test() -> int:
    ok = fail = 0

    def case(name: str, got, want) -> None:
        """⚠ `got` may be a CALLABLE — see the note at the unparseable-source cases below."""
        nonlocal ok, fail
        if callable(got):
            try:
                got = got()
            except Exception as exc:                                        # noqa: BLE001
                fail += 1
                print(f"  [FAIL] {name} — {type(exc).__name__}: {exc}")
                return
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    # ⭐⭐ THE REAL MISS, AS A FIXTURE. This is `_regenerate`'s shape at the commit where its 504
    # arm was cased and its 500 arm was not — the defect a later review round found. If this
    # script cannot name the 500 arm when told the 504 was touched, it does not do the one job
    # the experiment said it could do.
    regen = '''
def _regenerate(self, payload):
    want = payload.get("page")
    if script is None:
        return self._send(400, body, "text/plain")
    try:
        r = run(cmd)
    except TimeoutExpired:
        return self._send(504, b"NOT REBUILT", "text/plain")
    if r.returncode != 0:
        return self._send(500, b"NOT REBUILT", "text/plain")
    return self._send(200, b"ok", "application/json")
'''
    adv = report(regen, {9})                       # the 504 line
    case("the real miss: touching the 504 arm names the other three exits",
         sum(1 for l in adv if ":" in l and l.strip().startswith((">", ":"))) >= 0, True)
    case("…and it says 1 of 4", any("1 of 4 exits" in l for l in adv), True)
    case("…and the 500 arm is listed", any("500" in l for l in adv), True)
    case("…and the 200 arm is listed", any("200" in l for l in adv), True)
    case("…and the touched arm is marked", any(l.startswith("  >") and "504" in l for l in adv),
         True)

    # ⛔ THE FILTER: a container touched ENTIRELY needs no prompt, and one touched not at all is
    # not this diff's business. Both silences are deliberate and both are asserted.
    case("a container touched ENTIRELY is silent", report(regen, {5, 9, 11, 12}), [])
    case("a container touched NOWHERE is silent", report(regen, {2}), [])
    case("an empty diff is silent", report(regen, set()), [])

    # ⛔ ASSERTED AT `containers`, NOT AT `report` — and the difference is a real gap the mutation
    # sweep found. `report` filters any container whose members were ALL touched, and a one-member
    # container is fully touched by definition, so widening `len(rets) > 1` to `> 0` was invisible
    # through `report`: 24/24 with the defect applied. The claim "a single exit is not a set" is a
    # claim about `containers`, and that is where it now lives.
    single = "def f():\n    return 1\n"
    case("a single-exit function is not a container", containers(single), [])
    case("…and nothing is advised about it either", report(single, {2}), [])

    # ⚠ NESTED SCOPES OWN THEIR OWN EXITS — without this, a closure's `return` counts as an exit
    # of the function around it and the advice names lines that are not peers at all.
    nested = '''
def outer(x):
    def inner(y):
        if y:
            return 1
        return 2
    if x:
        return inner(x)
    return 0
'''
    adv_n = report(nested, {8})
    case("a nested function's exits are NOT the outer function's",
         any("outer(): you changed 1 of 2 exits" in l for l in adv_n), True)
    case("…and the inner function is its own container",
         report(nested, {5}) and "inner()" in report(nested, {5})[0], True)

    # except handlers
    tryblk = '''
def g():
    try:
        h()
    except OSError:
        return 1
    except ValueError:
        return 2
'''
    case("except handlers are a container",
         any("2 except" in l for l in report(tryblk, {5})), True)

    # if/elif chains
    chain = '''
def k(n):
    if n == 1:
        a()
    elif n == 2:
        b()
    elif n == 3:
        c()
    else:
        d()
'''
    adv_c = report(chain, {5})
    case("an if/elif chain is a container", any("branches" in l for l in adv_c), True)
    case("…counting every arm including else", any("1 of 4 branches" in l for l in adv_c), True)
    # ⚠ The same chain must be reported ONCE, not once per arm: `ast.walk` yields each `elif` as
    # its own `If`, whose chain is a suffix of the head's. Measured — without the dedupe this
    # printed the chain three times, which is exactly the scroll-past noise the design rejects.
    case("…and reported once, not once per arm",
         sum(1 for l in adv_c if l.startswith("if/elif chain:")), 1)

    # ⛔ MALFORMED INPUT IS SILENCE, NOT A CRASH — this runs over whatever a diff touched.
    # ⚠ PASSED AS THUNKS, because a raise out here aborts the suite with NO `[FAIL]` line and
    # `check-plan-code` then reports "the suite went RED but nothing could see the kill". MEASURED:
    # mutating the SyntaxError handler to re-raise produced exactly that — a crash with no
    # attributable case. `case` calls a callable inside its own try, so the kill stays readable.
    case("unparseable source yields no containers", lambda: containers("def ("), [])
    case("…and no advice", lambda: report("def (", {1}), [])
    # ⛔ AND AS A VALUE, so the kill is ATTRIBUTABLE. The two cases above report a raise through
    # `case`'s handler, which prints `[FAIL] {name} — SyntaxError: …` — a parsed case name carrying
    # runtime text, which a manifest entry can never name by exact match. One case that reports the
    # refusal as a plain False is what lets this property join the ratchet at all.
    def _survives_bad_source() -> bool:
        try:
            containers("def (")
            return True
        except SyntaxError:
            return False
    case("…and it REFUSES rather than raising — the ratchetable form", _survives_bad_source, True)
    case("an empty file is silent", report("", {1}), [])

    # ⛔ A GIT FAILURE RETURNS EMPTY, and the caller must not read that as a clean diff. This is
    # the fail-open shape this project files hardest against, so it is asserted directly.
    # ⛔ NONE, NOT `set()` — "git could not answer" must not be spelled the same way as
    # "git answered: nothing changed".
    case("a bad ref reports CANNOT RUN (None), never a clean diff",
         changed_lines("definitely-not-a-ref-2026", "scripts/peer-sites.py"), None)
    # ── parse_hunks: the RULE, testable without a git anywhere ────────────────────────────
    case("a single-line hunk yields that one line",
         parse_hunks("@@ -1 +7 @@\n+x\n"), {7})
    case("a counted hunk yields its whole range",
         parse_hunks("@@ -1,0 +3,4 @@\n"), {3, 4, 5, 6})
    case("several hunks accumulate",
         parse_hunks("@@ -1 +2 @@\n@@ -9 +40,2 @@\n"), {2, 40, 41})
    # ⚠ A ZERO-LENGTH hunk is a pure DELETION — the new side gained nothing, and `max(n, 1)` must
    # not invent a line. Measured: without the guard this reported the line after the deletion.
    case("a deletion-only hunk claims no new lines", parse_hunks("@@ -4,2 +3,0 @@\n"), set())
    case("a malformed header is skipped, not fatal", parse_hunks("@@ garbage @@\n"), set())
    case("a diff with no hunks is empty", parse_hunks("diff --git a/x b/x\n"), set())

    # the two shapes this CANNOT see, asserted so the boundary is measured rather than promised
    prose = 'X = """a sentence making four claims: a, b, c and d."""\n'
    case("prose clauses are NOT a container — the stated blind spot", containers(prose), [])
    case("…nor is an encoding level", containers("y = unquote(unquote(z))\n"), [])

    # the advisory footer's claim about its own scope must match the code
    case("exactly three container kinds are implemented",
         sorted({k for k, _, _ in containers(regen + tryblk + chain)}),
         ["branches", "except", "exits"])

    case("report is PURE — it does not touch the filesystem",
         "open(" not in _src_of(report) and "Path(" not in _src_of(report), True)
    case("containers is PURE too",
         "open(" not in _src_of(containers) and "subprocess" not in _src_of(containers), True)

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


def _src_of(fn) -> str:
    import inspect
    return inspect.getsource(fn)


if __name__ == "__main__":
    raise SystemExit(main())

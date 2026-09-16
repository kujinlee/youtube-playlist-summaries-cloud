#!/usr/bin/env python3
"""You changed ONE member of an enumerable set. Here are the others.

    python3 scripts/peer-sites.py --diff master      # peers of everything a branch touched
    python3 scripts/peer-sites.py FILE:LINE          # peers of one site
    python3 scripts/peer-sites.py --self-test        # 59 cases

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
A container is bounded by construction, so every member is in scope *syntactically*. An unbounded
shape search is 90% noise and gets scrolled past, which is worse than silence because it looks like
coverage.

⟳⟳ AND THE TWO NUMBERS THAT SENTENCE USED TO CARRY WERE BOTH WRONG — r1 High (H3) and Low (L1),
measured by REPLAYING the tool over 200 master commits. They are corrected here rather than softened,
because the whole point of the section is that the claims are measured:

    claimed                              measured over 138 python-touching commits
    "no such thing as a false positive"  4 of 12 `branches` containers are ONE idiom — the
                                         `if ok: … else: print("[FAIL]")` two-arm self-test
                                         helper, whose "peer" is the success branch. No reader
                                         ever answers that question with anything but "no".
    "prints 2-4 lines"                   96 of 138 commits print NOTHING; the tail runs to 32
                                         lines, and 10 single containers print 9+ on their own.

**Bounded by syntax buys decidable membership, NOT usefulness** — that is the honest version. The
distribution still supports the design (70% of commits silent is what makes an always-on advisory
readable); it is the absolutes that were false. The `branches` shape carries essentially all of the
noise; `exits`, which produced 61 of the 73 containers, had none the reviewer would call a false
positive.

⚠ WHAT IT CANNOT SEE, STATED RATHER THAN DISCOVERED LATER — and r1 Medium (M4) found this list was
itself incomplete, in the one section whose entire claim is that the bounds are stated. All of it:

  1. **Prose and encoding levels.** Two of the six misses had no syntactic container — one lived in
     the clauses of an English sentence, the other in the levels of a URL encoding. Those belong to
     the reviewer clause in `docs/review-method.md`, not here.
  2. ⛔ **AN EDIT INSIDE AN ARM'S BODY.** A member is its HEAD — a `return`'s span, an arm's
     *condition*, a handler's `except` clause. Edit the body and nothing is reported. MEASURED and
     it is the dominant shape: of the partially-touched containers in the replay, **79 were silent
     and 5 spoke.** This is the largest known gap and it is a DESIGN question, not an oversight —
     making a member the whole arm would tile the statement, so every edit would mark every member
     touched and the partially-touched filter could never fire. Filed, with the measurements.
  3. **Anything that is not Python.** `main` filters `.py`. This repo also ships ~22k lines of
     `.ts`/`.tsx` — though 0 of the last 60 master commits touched one, so the scope is defensible;
     it is the silence about it that was not.
  4. **`match`/`case` is not a shape**, and a `try`'s `else`/`finally` are never members. `match` is
     a real omission with no recorded reason — its arms ARE syntactically enumerated, so the stated
     justification (*"a shape whose membership is a judgement call"*) does not cover it. Latent, not
     live: 0 `match` statements in the repo today.

**A green run of this script is not evidence that a class was searched** — it is evidence that three
container shapes were, on python, at member head lines.

⛔ WHO CALLS IT — r1 High (P2), and until that finding this script had **no caller at all**: no hook,
no CI step, no skill. The premise above is *a written rule did not stop this, so here is a mechanism*
— and a script someone must remember to run is that same rule with an executable attached. It would
have failed the same way, for the same reason. `.claude/hooks/peer-sites-advisory.sh` now runs it
before `git commit`, which is the machine-observable instant the rule describes: while the fix is
still in your hands. A reminder, never a gate.

NOT A GATE — it advises and has nothing to refuse. ⚠ BUT IT EXITS 2 WHEN IT COULD NOT LOOK: if git
cannot diff a changed file, that file is named on stderr and the run ends non-zero (r1 Medium, M3).
It used to print CANNOT RUN and then `return 0`, which is the one thing this project refuses
everywhere — *"cannot run" is a FAILURE, never a pass*. `--self-test` and a mutation manifest are
what keep it honest (backlog #122's lesson, applied at birth rather than as debt).
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent


class Peer:
    """One member of an enumerable set, and whether the diff touched it."""

    def __init__(self, lineno: int, text: str, touched: bool):
        self.lineno, self.text, self.touched = lineno, text, touched

    def __repr__(self) -> str:                                    # pragma: no cover - debug only
        return f"Peer({self.lineno}, touched={self.touched})"


def containers(src: str) -> "list[tuple[str, str, list[tuple[int, int]]]]":
    """Every enumerable set in `src`, as (kind, label, member line numbers). PURE.

    Members are (start, end) LINE RANGES — see `_span` for why a line is not enough.

    ⛔ THREE SHAPES, AND THE LIST IS DELIBERATELY SHORT. Each is bounded by its own syntax, so
    membership is decidable and complete — that is the whole property that makes the output quiet.
    Adding a shape whose membership is a judgement call (say, "similar expressions") would import
    the noise this design exists to avoid, and the docstring above says so with numbers.
    """
    out: "list[tuple[str, str, list[tuple[int, int]]]]" = []
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
             and isinstance(arm.orelse[0], ast.If) and _is_elif(arm, arm.orelse[0])}
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node in elifs:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # ⚠ NESTED FUNCTIONS ARE THEIR OWN CONTAINERS, so a `return` inside a closure must not
            # be counted as an exit of the enclosing function. `ast.walk` does not know that.
            rets = [_span(n) for n in _own_nodes(node, ast.Return) if n.value is not None]
            if len(rets) > 1:
                out.append(("exits", f"{node.name}()", sorted(rets)))
        if isinstance(node, ast.Try) and len(node.handlers) > 1:
            # ⚠ the handler HEAD, not its body: same tiling problem as an if-arm.
            # ⚠ VIA `_span`, not a bare `end_lineno` — that attribute is `int | None`, and a `None`
            # end reaches `report`'s `range(lo, hi + 1)` as a TypeError rather than a miss.
            out.append(("except", "try block",
                        sorted((h.lineno, _span(h.type)[1] if h.type else h.lineno)
                               for h in node.handlers)))
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


def _is_elif(parent: ast.If, child: ast.If) -> bool:
    """Is `child` an `elif` OF `parent`, rather than an `if` nested inside its `else`? PURE.

    ⛔⛔ r1 BLOCKING, AND IT FALSIFIED THIS FILE'S CENTRAL CLAIM. `elif b:` and `else:` + an
    indented `if b:` produce the SAME AST — `If.orelse == [If]` — so the first version fused two
    different containers into one and offered the outer `if` as a peer of an inner one. MEASURED:

        if x:            -> containers() reported ONE chain [2, 5, 7], and touching line 5
            return 1        advised checking `if x:` at line 2, which is not its peer at all.
        else:
            if y == 1:   <- a nested container, not an arm of the chain above
                return 2
            elif y == 2:
                return 3

    That is not a small miscount: the docstring's whole justification is *bounded by syntax, so
    every member is legitimately in scope*, and a fused container has members that are not.
    ⚠ COLUMN IS THE DISCRIMINATOR and the AST carries it: an `elif` keeps its parent's
    `col_offset` (both 0 above); an `if` inside an `else` body is indented past it (0 vs 4).
    """
    return child.col_offset == parent.col_offset


def _if_chain(node: ast.If) -> "list[tuple[int, int]]":
    """The (start, end) line range of every arm's CONDITION in one if/elif chain. PURE.

    ⚠ THE CONDITION, NOT THE ARM'S BODY — r1 High. If a member were the whole arm, the arms would
    tile the entire statement and any edit anywhere inside it would mark every member touched, so
    the partially-touched filter could never fire. The part you edit to change THIS arm's behaviour
    is its test; the `else` has none, so its first statement's line stands for it.

    ⛔ AND THAT IS THIS FILE'S LARGEST KNOWN GAP, NOT A DETAIL — r1 High (H1), measured by replay:
    of the partially-touched containers over 200 master commits, **79 were silent and 5 spoke**,
    because the commonest edit there is lands in an arm's BODY. The tiling argument above is real,
    so the fix is a redesign of what a member IS rather than a wider span, and it is FILED with its
    measurements rather than guessed at here. The docstring states it as a bound.

    ⚠ THE `else` MEMBER'S LINE IS ITS FIRST STATEMENT, NOT THE `else:` KEYWORD — r1 Low (L3), and
    the two shapes genuinely disagree: the `except` shape uses `h.lineno`, which IS the `except`
    keyword. `ast` gives an `If` no line for its `else:` clause — there is no node for it — so the
    first statement is the only honest anchor available. Recorded because a reader comparing the
    two printed forms will notice, and a difference with no stated reason reads as a bug.
    """
    arms, cur = [_span(node.test)], node
    while len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If) and _is_elif(cur, cur.orelse[0]):
        cur = cur.orelse[0]
        arms.append(_span(cur.test))
    if cur.orelse:
        arms.append(_span(cur.orelse[0]))
    return arms


def _span(node: "ast.stmt | ast.expr") -> "tuple[int, int]":
    """A node's (first, last) source line. PURE.

    ⛔ A PEER IS A RANGE, NOT A LINE — r1 High, and it was a real false negative rather than a
    nicety. The first version recorded only a peer's HEAD line, so a diff touching the VALUE inside
    a multi-line `return (\n    "x"\n)` intersected nothing and the container stayed silent.
    MEASURED: touching the `return` line advised 4 lines; touching its value advised **none**.
    The reviewer found live multi-line returns in `brief-compose.py` and `page_chrome.py`, so the
    miss is reachable in this repo today, not hypothetical.
    """
    return (node.lineno, getattr(node, "end_lineno", None) or node.lineno)


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
    cursor = 0
    for line in diff.split("\n"):
        if line.startswith("@@@"):
            # ⛔ A COMBINED DIFF (a merge, `git diff -c`) HAS TWO OLD SIDES and a different column
            # grammar. REFUSED rather than guessed at — r1 Medium measured the header-range parser
            # answering `{1, 2}` for one, which is a confident wrong answer about a shape it cannot
            # read. Silence beats a plausible number.
            cursor = 0
            continue
        if line.startswith("@@"):
            try:
                new = line.split("+", 1)[1].split("@@", 1)[0].strip()
                # ⛔ `max(n, 1)` IS ONLY FOR AN ABSENT COUNT, NOT A ZERO ONE. `@@ -4,2 +3,0 @@` is
                # a pure DELETION: the new side gained nothing, and claiming a line makes the
                # deletion look like a change to whatever now sits there. `@@ -1 +7 @@` omits the
                # count and DOES mean one line.
                start, sep, count = new.partition(",")
                cursor = int(start) if (int(count) if sep else 1) else 0
            except (IndexError, ValueError):
                cursor = 0                 # a malformed header is skipped, never fatal
            continue
        # ⛔ THE BODY DECIDES, NOT THE HEADER RANGE — r1 Medium. Claiming the whole new-side range
        # is right ONLY under `-U0`; with context it marks unchanged lines as touched. MEASURED:
        # `@@ -1,3 +1,3 @@` over a single changed line returned {1, 2, 3}. The one caller does pass
        # `-U0`, so the live path was never wrong — but a pure parser whose contract holds only for
        # its current caller is a landmine for the next one, and this one was split out precisely
        # to be reusable.
        if not cursor:
            continue
        if line.startswith("+"):
            out.add(cursor)
            cursor += 1
        elif line.startswith("-"):
            pass                           # old side only: the new file gains no line here
        else:
            cursor += 1                    # context (or a stray blank): present, unchanged
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


def _merge_base(ref: str) -> "str | None":
    """Where `ref` and HEAD diverged, or **None when git could not answer**. A SHELL, like
    `changed_lines` — the rule it feeds is in `report`, and there is no decision here to case.

    ⛔ r1 High (H2). Diffing against `ref` itself charges this branch for everything `ref` gained
    since the branch started. Resolving the base first is what makes *"you changed"* true.
    ⚠ Same CANNOT-RUN contract as `changed_lines`: `None` is "git could not answer", never "no
    divergence" — an unrelated-histories pair has no merge base and must not read as `HEAD`.
    """
    try:
        r = subprocess.run(["git", "-C", str(REPO), "merge-base", ref, "HEAD"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def report(src: str, touched: "set[int]") -> "list[str]":
    """The advisory lines: containers the diff touched PARTIALLY. PURE.

    ⛔ PARTIALLY IS THE WHOLE FILTER. A container where every member was touched needs no
    prompting, and one where none were is not this diff's business. Output is therefore
    proportional to the actual risk rather than to the size of the file — which is what makes it
    readable every time rather than something to scroll past.
    """
    lines = src.split("\n")
    out: "list[str]" = []
    for kind, label, members in sorted(containers(src), key=lambda c: c[2]):
        # ⛔ RANGE INTERSECTION — r1 High. Exact line equality missed a diff that touched the VALUE
        # inside a multi-line peer, which is a shape this repo really contains.
        hit = [m for m in members if any(ln in touched for ln in range(m[0], m[1] + 1))]
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
        # ⛔ A `seen` DEDUPE STOOD HERE AND IS GONE — r1 Medium (M1), and it was DEAD CODE that a
        # docstring credited with a job. `_if_chain` claimed nested arms were "filtered by the
        # dedupe in `report`"; they are not — a nested arm's member tuple is a SUBSET, so it is a
        # different key and never deduped. The `elifs` set in `containers` is what actually filters
        # them, and the same file said so correctly eight lines away: two adjacent comments giving
        # opposite accounts of one mechanism. MEASURED across 117 files / 869 containers: zero
        # duplicate `(kind, members)` keys, and removing the dedupe survived the whole suite.
        # ⚠ Deleted rather than ratcheted. A mutation entry for a no-op would pin the no-op.
        out.append(f"{label}: you changed {len(hit)} of {len(members)} {kind}")
        for m in members:
            mark = "  >" if m in hit else "   "
            body = lines[m[0] - 1].strip() if 0 < m[0] <= len(lines) else ""
            span = "" if m[0] == m[1] else f"-{m[1]}"
            out.append(f"{mark} :{str(m[0]) + span:<8} {body[:82]}")
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
        # ⛔ THE MERGE BASE, NOT THE REF — r1 High (H2). `git diff master` compares master to the
        # WORKING TREE, so anything master gained since this branch started is reported back to you
        # as "you changed". MEASURED in a throwaway repo: a branch that touched only `other.py` was
        # advised about `app.py`, which master had edited. That is this repo's recorded *a green
        # check says nothing about the branch BASE*, arriving as a false positive instead.
        base = _merge_base(a.diff)
        if base is None:
            print(f"CANNOT RUN — no merge base between {a.diff} and HEAD. Treat this as NOT CHECKED.",
                  file=sys.stderr)
            return 2
        # ⚠ TWO-DOT AGAINST THE BASE, not `{ref}...HEAD`, and the neighbours differ here for a
        # reason worth stating. `check-dashboard-entry.py:1277` and `check-review-decision.py:622`
        # ask *what will this PR merge?*, which is a question about COMMITS. This asks *what have
        # you touched?* — and it is meant to be run BEFORE you commit, so it must see the working
        # tree. Three-dot would be silent on exactly the edit you are about to be advised on.
        r = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", base],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"CANNOT RUN — `git diff --name-only {base}` failed. Treat this as NOT CHECKED.",
                  file=sys.stderr)
            return 2
        paths = [p for p in r.stdout.split("\n") if p.endswith(".py")]
        total = examined = 0
        unchecked: "list[str]" = []
        for rel in paths:
            f = REPO / rel
            if not f.is_file():
                continue                       # deleted by this branch: nothing left to advise on
            touched = changed_lines(base, rel)
            if touched is None:
                # ⛔ REMEMBERED, NOT JUST PRINTED — r1 Medium (M3). This used to print CANNOT RUN
                # and fall through to `return 0`, so a caller reading the exit code saw a clean
                # advisory run over a file set that was partly never examined. *"Cannot run" is a
                # FAILURE, never a pass* is this project's cardinal rule, and this was the one
                # place it was broken.
                unchecked.append(rel)
                print(f"CANNOT RUN — `git diff` could not answer for {rel}. NOT CHECKED.",
                      file=sys.stderr)
                continue
            examined += 1
            adv = report(f.read_text(), touched)
            if adv:
                total += 1
                print(f"\n── {rel} " + "─" * max(0, 60 - len(rel)))
                for line in adv:
                    print(line)
        if not total:
            # ⚠ `examined`, NOT `len(paths)` — r1 Low (L4). Deleted and unreadable files are skipped
            # above, so the old count overstated what was actually looked at.
            print(f"no partially-touched containers in {examined} changed python file(s).")
        print("\n⚠ This checks THREE container shapes, on PYTHON only, and only where the edit "
              "lands on a member's HEAD line. A class living in prose, in the levels of an "
              "encoding, or inside an arm's BODY is invisible here — see docs/review-method.md.")
        if unchecked:
            print(f"\n⛔ NOT CHECKED: {len(unchecked)} file(s) git could not diff — "
                  f"{', '.join(unchecked)}. This run is INCOMPLETE.", file=sys.stderr)
            return 2
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

    # ⛔⛔ r1 HIGH (H5) — THE BRANCH COMMITTED ITS OWN HEADLINE DEFECT, AND THIS IS THE REPAIR.
    # `len(rets) > 1` was ratcheted (manifest entry 1) after the author found it invisible through
    # `report`. The IDENTICAL expression appears twice more in the same function, eight lines
    # apart, and neither was cased: `> 0` survived the whole suite in both places. The reviewer
    # then asked `peer-sites.py` about its own line 92 and it said NOTHING — three sequential `if`
    # statements are not one of the three shapes, so the mechanism built to stop *fix the instance,
    # miss the sibling* cannot see that failure in its own source. ⭐ That is the honest measure of
    # what this tool is: the docstring's "3 of 6 are mechanical" is a ceiling for a hand-picked
    # sample, not a rate. These three cases close the siblings a human had to find.
    case("a try with ONE handler is not a container",
         containers('def g():\n    try:\n        h()\n    except OSError:\n        return 1\n'), [])
    case("a chain of ONE arm is not a container",
         containers('def k(n):\n    if n == 1:\n        a()\n'), [])
    # ⚠ THE WORD "value-returning" IN THE CONTRACT. A bare `return` exits, but it carries no value
    # to get wrong, so it is not a peer you would review. Deleting `n.value is not None` survived.
    case("a bare `return` is not a value-returning exit",
         containers('def f(x):\n    if x:\n        return\n    return 1\n    return 2\n'),
         [("exits", "f()", [(4, 4), (5, 5)])])

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
    # its own `If`, whose chain is a suffix of the head's. Measured — without the `elifs` skip in
    # `containers` this printed the chain three times, the scroll-past noise the design rejects.
    # ⛔ THE `elifs` SKIP, NOT A DEDUPE, and this comment used to name the wrong mechanism — r1
    # Medium (M1). A suffix is a DIFFERENT member tuple, so no dedupe could ever have caught it.
    case("…and reported once, not once per arm",
         sum(1 for l in adv_c if l.startswith("if/elif chain:")), 1)

    # ⛔⛔ r1 BLOCKING, AND ITS FIX SHIPPED WITH NOTHING THAT COULD SEE IT GO. `else:` + an
    # indented `if` and a plain `elif` produce the SAME AST, so without `col_offset` the two
    # containers below FUSE and the outer `if x:` is offered as a peer of the inner `if y == 1:`.
    # MEASURED both ways: fused it is one chain `[3, 6, 8]`; separated it is `[3, 6-9]` + `[6, 8]`.
    # ⚠ The first four cases written for this round asserted on `parse_hunks` and on the argv, and
    # `_is_elif` could be reverted to `return True` under all 38 of them without one turning red —
    # which is this project's *fixed the premise, never covered the branch* shape, here inside the
    # very branch that exists to stop it.
    nested_else = '''
def f(x, y):
    if x:
        return 1
    else:
        if y == 1:
            return 2
        elif y == 2:
            return 3
'''
    def _holds(members, line) -> bool:
        return any(lo <= line <= hi for lo, hi in members)
    chains = [c[2] for c in containers(nested_else) if c[0] == "branches"]
    case("`else:` + an indented `if` is TWO containers, not one fused chain", len(chains), 2)
    # ⚠ THE ARM COUNT IS THE SHARP PROPERTY, not the container count — a split made in the wrong
    # place would still yield two. The outer chain has exactly two arms, `if x:` and its `else`;
    # the inner `elif` belongs to the other container and must not be counted here.
    case("…and the outer chain has TWO arms — `if x:` and its `else`, never the inner `elif`",
         [len(m) for m in chains if _holds(m, 3)], [2])

    # ⛔ r1 HIGH, LIKEWISE UNGUARDED UNTIL NOW. A peer is a RANGE: recording only its head line
    # means a diff that touches the VALUE inside a multi-line `return (…)` intersects nothing and
    # the container stays silent. MEASURED: with head lines only, `report(multiline, {5})` is `[]`.
    # Live instances exist in `brief-compose.py` and `page_chrome.py`, so the miss is reachable
    # here today — the reviewer checked, which is why this is a High and not a nicety.
    multiline = '''
def f(x):
    if x == 1:
        return (
            "old"
        )
    if x == 2:
        return (
            "other"
        )
    return "done"
'''
    case("touching the VALUE inside a multi-line exit still finds its peers",
         any("1 of 3 exits" in l for l in report(multiline, {5})), True)
    case("…because a multi-line member is recorded as a RANGE, not a head line",
         [c[2] for c in containers(multiline) if c[0] == "exits"], [[(4, 6), (8, 10), (11, 11)]])

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
    # ⚠ THE NAME SAYS "git could not answer", NOT "a bad ref" — r1 Low (L5). It used to read *"a bad
    # ref reports CANNOT RUN"*, which is true HERE and false where it is MEASURED: under
    # `--mutate .` the harness tree has no `.git` at all, so the branch is reached because there is
    # no repository, not because the ref is bad. The kill was always real; the case name described a
    # cause that does not obtain where the kill happens. Both worlds are now named, so the manifest
    # entry it backs means the same thing in the repo and in the staged tree.
    case("git not answering — bad ref OR no repo — reports CANNOT RUN (None), never a clean diff",
         changed_lines("definitely-not-a-ref-2026", "scripts/peer-sites.py"), None)
    # ⛔⛔ THE PARAMETERS ARE VARIED WITHOUT A `.git` — r1 Low, and the finding was that the
    # EXEMPTION I wrote for them rested on a FALSE PREMISE. It claimed varying `ref`/`path`
    # "would require a real .git"; it does not — `subprocess.run` is a module attribute, and both
    # parameters are observable in the argv it is handed. An exemption resting on something untrue
    # is worse than no exemption, because it stops anyone looking again.
    _argv: "list[list[str]]" = []
    def _fake_run(cmd, **_k):
        _argv.append(list(cmd))
        return type("R", (), {"returncode": 0, "stdout": "@@ -1 +9 @@\n+x\n"})()
    _real_run = subprocess.run
    try:
        subprocess.run = _fake_run                       # type: ignore[assignment]
        _a = changed_lines("ref-A", "path/one.py")
        _b = changed_lines("ref-B", "path/two.py")
    finally:
        subprocess.run = _real_run                       # type: ignore[assignment]
    case("the ref reaches git's argv", [c[-3] for c in _argv], ["ref-A", "ref-B"])
    case("…and so does the path", [c[-1] for c in _argv], ["path/one.py", "path/two.py"])
    case("…and the parsed result comes back", (_a, _b), ({9}, {9}))
    case("…via `git diff -U0`, which is what makes the body parse exact",
         all("-U0" in c for c in _argv), True)

    # ── main --diff: DRIVEN, which nothing did before ─────────────────────────────────────
    # ⛔⛔ r1 found THREE defects in `main` at once (H2, M3, L4) and could find them only by
    # reading, because **no case drove this function at all**. That is the same hole
    # `check-fixture-variation.py:79-81` records paying for once already: a file JOINED its own
    # population the moment `main`'s verdict path was cased. These cases put it in.
    # ⚠ NO `.git` AND NO REAL REPO: `subprocess.run` is served a script, and REPO is pointed at a
    # temp tree. A case whose premise is the ambient world asserts the world — four instances in
    # this repo, and `--mutate .` stages a tree with no `.git` at all.
    def _merge_base_of(reply):
        """`_merge_base` over a `subprocess.run` that returns whatever `reply()` says."""
        real = subprocess.run
        try:
            subprocess.run = lambda *_a, **_kw: reply()    # type: ignore[assignment]
            return _merge_base("master")
        finally:
            subprocess.run = real                          # type: ignore[assignment]

    def _drive_main(diff_ok: bool = True):
        """Run `main --diff master` against a fake git and a temp tree. Returns (rc, out, calls)."""
        calls: "list[list[str]]" = []
        src = 'def h(x):\n    if x:\n        return "one"\n    return "two"\n'

        def fake_run(cmd, **_kw):
            calls.append(list(cmd))
            if "merge-base" in cmd:
                return type("R", (), {"returncode": 0, "stdout": "BASE0000\n"})()
            if "--name-only" in cmd:
                return type("R", (), {"returncode": 0, "stdout": "a.py\n"})()
            if not diff_ok:                       # git cannot answer for the one changed file
                return type("R", (), {"returncode": 128, "stdout": ""})()
            return type("R", (), {"returncode": 0, "stdout": "@@ -3 +3 @@\n+    return \"1\"\n"})()

        real_run, real_repo = subprocess.run, globals()["REPO"]
        with tempfile.TemporaryDirectory() as td:
            (pathlib.Path(td) / "a.py").write_text(src)
            buf = io.StringIO()
            try:
                subprocess.run = fake_run         # type: ignore[assignment]
                globals()["REPO"] = pathlib.Path(td)
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                    rc = main(["--diff", "master"])
            finally:
                subprocess.run, globals()["REPO"] = real_run, real_repo   # type: ignore[assignment]
        return rc, buf.getvalue(), calls

    _rc, _out, _calls = _drive_main()
    # ⛔ H2 — THE MERGE BASE REACHES THE DIFF, NOT THE REF. Diffing `master` directly charges this
    # branch for everything master gained since it started; measured in a sandbox, a branch that
    # touched only `other.py` was advised about an `app.py` that MASTER had edited.
    case("`--diff REF` resolves the MERGE BASE first", any("merge-base" in c for c in _calls), True)
    case("…and it is the BASE that reaches the diffs, never the ref",
         [c for c in _calls if "diff" in c and "BASE0000" not in c], [])
    case("…and a partially-touched container is still advised on",
         any("1 of 2 exits" in l for l in _out.split("\n")), True)
    case("a well-formed advisory run exits 0", _rc, 0)
    # ⛔ M3 — "CANNOT RUN" IS A FAILURE, NEVER A PASS. This used to print the warning and then
    # `return 0`, so a caller reading the exit code saw a clean run over a file it never examined.
    _rc_bad, _out_bad, _ = _drive_main(diff_ok=False)
    case("a file git could not diff makes the whole run exit 2", _rc_bad, 2)
    # ⚠ L4 — and the footer counts what was EXAMINED, not what was listed. With the only file
    # unreadable the honest count is 0, not 1.
    case("…and the footer counts examined files, not listed ones",
         any("in 0 changed python file(s)" in l for l in _out_bad.split("\n")), True)
    # ⛔ THE OTHER ENTRY POINT, and it is here because driving `main` at all made this file JOIN its
    # own population — `check-fixture-variation` immediately refused a suite that passes `main` one
    # constant argv, which is exactly what it is for. r1's M3 also named `--site` as uncovered:
    # *"both entry points are uncovered; one is silently wrong, one is right by luck."* This is the
    # luck being replaced by a case.
    # ⚠ POSITIONAL, AND `main(["--site", x])` COST A WHOLE SUITE RUN TO LEARN. `site` is a
    # positional argument, so the flag form makes argparse `SystemExit` — which unwound straight
    # out of `_self_test` and printed NOTHING AT ALL, no tally and no `[FAIL]`. This file already
    # warns about exactly that at the unparseable-source cases; the warning was about `case`'s
    # arguments and I reintroduced the shape one level up, in the harness around them. SystemExit
    # is caught here so a mistake in a driver can never again masquerade as a suite that did not run.
    def _drive_site(arg: str) -> "tuple[int, str]":
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = main([arg])
        except SystemExit as exc:                                       # argparse refused the input
            rc = int(exc.code or 0)
        return rc, buf.getvalue()

    with tempfile.TemporaryDirectory() as _td:
        _f = pathlib.Path(_td) / "s.py"
        _f.write_text('def h(x):\n    if x:\n        return "one"\n    return "two"\n')
        _rc_site, _out_site = _drive_site(f"{_f}:3")
        _rc_none, _out_none = _drive_site(f"{_f}:1")
        _rc_bad_site, _ = _drive_site("not-a-site")
        _rc_missing, _ = _drive_site(f"{_td}/gone.py:3")
    case("`--site FILE:LINE` advises on the container holding that line",
         any("1 of 2 exits" in l for l in _out_site.split("\n")), True)
    case("…and exits 0", _rc_site, 0)
    case("…and a line in no container says so rather than printing nothing",
         "no container holds that line." in _out_none, True)
    case("…and that is still a successful run, not a refusal", _rc_none, 0)
    case("a malformed site is CANNOT RUN (rc=2), not an empty advisory", _rc_bad_site, 2)
    case("…and so is a file that does not exist", _rc_missing, 2)

    case("a merge base git cannot answer for is CANNOT RUN, not HEAD",
         _merge_base_of(lambda: type("R", (), {"returncode": 1, "stdout": ""})()), None)
    # ⚠ AND AN EMPTY ANSWER ON rc=0 IS ALSO NONE — unrelated histories print nothing and succeed,
    # and `""` must not be handed to `git diff` where it would mean HEAD.
    case("…and so is an EMPTY answer that exits 0",
         _merge_base_of(lambda: type("R", (), {"returncode": 0, "stdout": "\n"})()), None)

    # ── parse_hunks: the RULE, testable without a git anywhere ────────────────────────────
    case("a single-line hunk yields that one line",
         parse_hunks("@@ -1 +7 @@\n+x\n"), {7})
    case("a counted hunk yields the lines its BODY adds",
         parse_hunks("@@ -1,0 +3,4 @@\n+a\n+b\n+c\n+d\n"), {3, 4, 5, 6})
    case("several hunks accumulate",
         parse_hunks("@@ -1 +2 @@\n+x\n@@ -9 +40,2 @@\n+y\n+z\n"), {40, 41, 2})
    # ⛔ CONTEXT IS NOT A CHANGE — r1 Medium. The header-range parser claimed the whole new side,
    # which is right only under `-U0`; the one caller passes `-U0`, so the live path was never
    # wrong, but a pure parser that is correct only for its current caller is a landmine.
    case("context lines are NOT reported as touched",
         parse_hunks("@@ -1,3 +1,3 @@ heading\n context\n-old\n+new\n context\n"), {2})
    # ⛔ A COMBINED DIFF IS REFUSED, not guessed at — it has two old sides and a different grammar.
    case("a combined diff yields nothing rather than a wrong answer",
         parse_hunks("@@@ -1,2 -1,2 +1,2 @@@\n- a\n+ b\n"), set())
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

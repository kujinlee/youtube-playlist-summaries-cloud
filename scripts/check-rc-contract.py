#!/usr/bin/env python3
"""The matcher's exit codes and the hook's `case` arms must agree, and nothing checked that.

WHY THIS EXISTS — it is the 2026-09-30 architecture review's corrected verdict, made mechanical.
---------------------------------------------------------------------------------------------
That review first concluded "what has no owner is CONSULTATION", and enumeration REFUTED it: every
verdict function in `scripts/recall-llm.py` is consulted at every production call site. The
corrected verdict is this:

    The rc contract spans TWO LANGUAGES, nothing reconciles the codes the matcher emits against
    the codes the hook handles, and rc=2 carried a CONJUNCTION in its meaning.

Both live defects that review produced are instances of that sentence, and both were found by
RUNNING the pair rather than by reading either half:

  * backlog #201 — `.claude/hooks/surface-recall.sh`'s `5)` arm interpolated `$OUT` into a
    `Detail:` clause UNCONDITIONALLY, while its siblings `0)` and `3)` guard on `[ -n "$OUT" ]`.
    `do_fire` empties the message when its dedupe fires, so from the second firing onward the
    reader got a sentence ending "Detail:" with nothing after it — measured 409 chars, then 148,
    then 148, and the marker persists so it never recovers.
  * backlog #202 — `cached_entry_verdict`'s "the corpus directory is unreachable" returned rc 2,
    which the hook correctly ignores as the routine "nothing is armed" state. Measured over a green
    control: 290 bytes forwarded with the corpus present, ZERO with only `HOME` changed, over a
    161-char message whose last three words are "NOTHING WAS SURFACED".

⚠ NEITHER WAS VISIBLE TO ANY EXISTING GATE, and that is the finding rather than the bugs.
`recall-llm.py` has 188 self-test cases and 91 mutation entries; every one of them lives on the
PYTHON side of the seam. `.claude/hooks/surface-recall.sh` has no self-test, no mutation entry, and
no script anywhere reads it — measured 2026-09-30: `grep -rl surface-recall scripts/ .github/`
returns nothing but review documents. `check-ratchet-contract.py`'s guard population is
`scripts/check-*.py`, so the hook is outside it by construction (backlog #196 widened R2/R3 to the
self-tested non-guards, which is still python-only).

WHAT IT CHECKS
--------------
  R1  Every rc constant the matcher DEFINES is either named by a `case` arm in the hook, or is
      listed here as deliberately unhandled with a written reason. A new sixth code that the hook
      silently drops is exactly #202, and adding a seventh is the obvious next instance.
  R2  Every `case` arm in the hook names a code the matcher can actually emit. An arm for a
      retired code is dead, and dead arms are how a reader concludes a path is covered.
  R3  No arm interpolates `$OUT` into a LABELLED clause without guarding on `[ -n "$OUT" ]`
      first — the #201 shape. An arm may forward unconditionally (rc=5 must never be silent) and
      it may use `$OUT`; what it may not do is promise a detail it might not have.

⛔ IT READS BOTH FILES, WHICH IS THE WHOLE POINT. A guard that parsed only the python would have
passed through both live defects, and one that parsed only the bash could not know which codes
exist. The subject is the AGREEMENT, and an agreement has no single file.

⚠ WHAT IT DOES NOT CHECK, stated rather than discovered later:
  * that an arm's MESSAGE is apt for the code it handles — that is a reading, not a shape;
  * that the matcher actually emits every code it defines on some reachable path. A defined-but-
    unreachable code is a different defect (dead interface surface) and `recall-llm.py`'s own
    cases are the right owner of it;
  * anything about the `*)` catch-all's behaviour beyond which codes reach it.

FAILS IF
--------
  * a defined rc is neither handled nor declared unhandled with a reason;
  * an arm names a code no constant defines;
  * an arm interpolates `$OUT` into a labelled clause with no `-n` guard;
  * either file is missing or unparseable -> exit 2, CANNOT RUN, never a pass.

Usage:
    python3 scripts/check-rc-contract.py
    python3 scripts/check-rc-contract.py --self-test  # 22 cases
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATCHER = ROOT / "scripts" / "recall-llm.py"
HOOK = ROOT / ".claude" / "hooks" / "surface-recall.sh"

# The one tuple-assignment in the matcher that defines every exit code. Read from the AST, not by
# regex: the names and the values must be paired, and a regex over `= 0, 2, 3, 4, 5, 6` cannot pair
# them without re-implementing tuple unpacking.
_RC_NAMES = {"OK", "CANNOT_RUN", "STALE_CACHE", "BAD_RESPONSE", "UNREADABLE_PLAN", "UNANSWERABLE"}

# ⛔ A WRITTEN REASON, NOT A FLAG — same shape as `check-ratchet-contract`'s NO-CALLER escape, and
# for the same argument: a boolean opt-out is a rubber stamp, a sentence has an author. Every entry
# here is a code the hook deliberately does not act on.
DELIBERATELY_UNHANDLED: dict[int, str] = {
    0: "rc 0 IS handled — the `0)` arm forwards a match and stays silent on an empty answer. "
       "Listed only so the table below is total; `handled_codes` finds its arm.",
    2: "CANNOT RUN is the ROUTINE absence — no plan armed. On a machine with nothing armed it is "
       "the normal state and the reader is right not to hear about it. ⚠ This is the entry that "
       "was doing too much work before backlog #202: it also covered 'armed but the corpus is "
       "gone', which the reader DOES need, and that is now rc 6. If you find yourself widening "
       "this sentence again, split the code instead.",
    4: "RESPONSE REJECTED can only arise on the `--arm` path (every `ResponseRejected` raise site "
       "is inside `parse_response`, which only `--arm` calls), and this hook runs `--fire` only. "
       "⚠ Nothing asserts that property, and it lives on the far side of the seam from the code "
       "that depends on it — so if `--fire` ever validates a cached name as a response, this "
       "entry is the thing that will be silently wrong.",
}

_ARM_RE = re.compile(r"^\s{2}(\d+)\)", re.M)
_OUT_IN_LABEL = re.compile(r"(?:Detail|detail):\s*\$OUT")
_NONEMPTY_GUARD = re.compile(r'\[\s*-n\s*"\$OUT"\s*\]')


class CannotRun(Exception):
    """The guard could not reach what it measures. Never rendered as a pass."""


def defined_codes(matcher_src: str) -> dict[str, int]:
    """-> {constant name: value} for the matcher's rc tuple assignment. AST, never a regex.

    ⚠ It must find EXACTLY ONE assignment whose targets are the rc names, and raise otherwise. A
    guard that silently picks the first of several candidates is guessing, and this repo's recorded
    shape for that is a positional read with no verified shape.
    """
    try:
        tree = ast.parse(matcher_src)
    except SyntaxError as exc:
        raise CannotRun(f"the matcher does not parse ({exc}), so its rc codes cannot be read") from exc
    found: list[dict[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Tuple) or not isinstance(node.value, ast.Tuple):
            continue
        names = [e.id for e in tgt.elts if isinstance(e, ast.Name)]
        if not _RC_NAMES.issubset(set(names)):
            continue
        vals = [int(v.value) for v in node.value.elts
                if isinstance(v, ast.Constant) and isinstance(v.value, int)]
        if len(names) != len(vals):
            raise CannotRun("the rc tuple assignment has mismatched names and values")
        found.append(dict(zip(names, vals)))
    if len(found) != 1:
        raise CannotRun(
            f"expected exactly one rc tuple assignment naming {sorted(_RC_NAMES)}, found {len(found)}"
        )
    return found[0]


def handled_codes(hook_src: str) -> set[int]:
    """-> every integer a `case` arm in the hook names."""
    return {int(m.group(1)) for m in _ARM_RE.finditer(hook_src)}


def unguarded_detail_arms(hook_src: str) -> list[int]:
    """-> arms that interpolate $OUT into a labelled clause with no `-n "$OUT"` guard. #201's shape.

    An arm runs from its `N)` to the next `N)` or to `*)`. Within that span, a `Detail: $OUT` is
    only honest if some `[ -n "$OUT" ]` appears in the same span — either guarding the whole
    assignment, as `0)` and `3)` do, or guarding the clause's append, as `5)` and `6)` now do.
    """
    spans = []
    marks = [(m.start(), int(m.group(1))) for m in _ARM_RE.finditer(hook_src)]
    catchall = hook_src.find("\n  *)")
    end_of_case = catchall if catchall != -1 else len(hook_src)
    for i, (pos, code) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else end_of_case
        spans.append((code, hook_src[pos:stop]))
    bad = []
    for code, body in spans:
        if _OUT_IN_LABEL.search(body) and not _NONEMPTY_GUARD.search(body):
            bad.append(code)
    return sorted(bad)


def verdict(defined: dict[str, int], handled: set[int], unguarded: list[int]) -> list[str]:
    """PURE. -> the list of problems, empty when the two languages agree."""
    problems: list[str] = []
    for name, code in sorted(defined.items(), key=lambda kv: kv[1]):
        if code in handled:
            continue
        if code in DELIBERATELY_UNHANDLED:
            continue
        problems.append(
            f"rc {code} ({name}) is defined by the matcher, no `case` arm in the hook names it, and "
            f"it is not listed in DELIBERATELY_UNHANDLED with a reason. The hook's catch-all will "
            f"swallow it — which is backlog #202 exactly."
        )
    for code in sorted(handled):
        if code not in set(defined.values()):
            problems.append(
                f"the hook has a `{code})` arm and no matcher constant has that value — a dead arm, "
                f"which reads as coverage and is not."
            )
    for code in unguarded:
        problems.append(
            f"the `{code})` arm interpolates $OUT into a `Detail:` clause with no `[ -n \"$OUT\" ]` "
            f"guard in the same arm. When the matcher's dedupe empties the message the reader gets "
            f"a sentence ending `Detail:` with nothing after it — backlog #201."
        )
    return problems


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    for f in (MATCHER, HOOK):
        if not f.is_file():
            print(f"FAILED: {f.relative_to(ROOT)} not found — treat this as NOT RUN.")
            return 2
    try:
        defined = defined_codes(MATCHER.read_text(encoding="utf-8", errors="replace"))
    except CannotRun as exc:
        print(f"FAILED: {exc}. Treat this as NOT RUN.")
        return 2
    hook_src = HOOK.read_text(encoding="utf-8", errors="replace")
    handled = handled_codes(hook_src)
    if not handled:
        print("FAILED: found no `case` arms in the hook at all, which cannot be right. NOT RUN.")
        return 2
    problems = verdict(defined, handled, unguarded_detail_arms(hook_src))
    print(f"rc contract: {len(defined)} code(s) defined, {len(handled)} handled by an arm, "
          f"{len(DELIBERATELY_UNHANDLED)} declared unhandled")
    if problems:
        print(f"FAILED — {len(problems)} disagreement(s) between the matcher and the hook:")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print("rc contract OK — every defined code is handled or declared, and no arm promises a "
          "detail it might not have")
    return 0


# ─────────────────────────────────────────────────────────────────── the suite
def _self_test() -> int:
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            print(f"[FAIL] {name}\n       expected {want!r}\n       got      {got!r}")
            fail += 1

    def raises(name: str, fn, exc_type) -> None:
        nonlocal ok, fail
        try:
            fn()
        except exc_type:
            ok += 1
            return
        except Exception as exc:  # noqa: BLE001 - any other exception is a different failure
            print(f"[FAIL] {name}\n       expected {exc_type.__name__}, got {exc!r}")
            fail += 1
            return
        print(f"[FAIL] {name}\n       expected {exc_type.__name__}, nothing raised")
        fail += 1

    RC = ("OK, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, UNREADABLE_PLAN, UNANSWERABLE"
          " = 0, 2, 3, 4, 5, 6\n")

    # ── defined_codes ──────────────────────────────────────────────────────────────────────
    case("the rc tuple is read from the AST, names paired with values",
         defined_codes(RC), {"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3, "BAD_RESPONSE": 4,
                             "UNREADABLE_PLAN": 5, "UNANSWERABLE": 6})
    case("a new code is picked up without touching this guard",
         defined_codes(RC.replace(", UNANSWERABLE =", ", UNANSWERABLE, SEVENTH =")
                         .replace("5, 6\n", "5, 6, 7\n")).get("SEVENTH"), 7)
    # ⛔ CANNOT-RUN, NOT A SILENT EMPTY ANSWER. An empty dict would make every downstream rule
    # vacuously green, which is the strongest available false claim.
    raises("a matcher with NO rc tuple is a cannot-run", lambda: defined_codes("x = 1\n"), CannotRun)
    raises("a matcher that does not parse is a cannot-run",
           lambda: defined_codes("def broken(\n"), CannotRun)
    raises("TWO rc tuples is a cannot-run — the guard must not pick one and guess",
           lambda: defined_codes(RC + RC), CannotRun)
    case("an assignment missing one rc name is not the rc tuple",
         defined_codes(RC + "A, B = 1, 2\n"), defined_codes(RC))

    # ── handled_codes ──────────────────────────────────────────────────────────────────────
    HOOK_OK = (
        'case "$RC" in\n'
        '  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n'
        '  3) [ -n "$OUT" ] && PAYLOAD="stale. Detail: $OUT" ;;\n'
        '  5) PAYLOAD="unreadable."\n'
        '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n'
        '  6) PAYLOAD="no corpus."\n'
        '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n'
        '  *) : ;;\n'
        'esac\n')
    case("every arm is found", handled_codes(HOOK_OK), {0, 3, 5, 6})
    case("the catch-all is not a code", 42 in handled_codes(HOOK_OK), False)
    case("a hook with no arms yields the empty set", handled_codes("echo hi\n"), set())

    # ── unguarded_detail_arms — #201's shape ───────────────────────────────────────────────
    case("a guarded Detail: clause is fine", unguarded_detail_arms(HOOK_OK), [])
    BAD = HOOK_OK.replace('  5) PAYLOAD="unreadable."\n     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n',
                          '  5) PAYLOAD="unreadable. Detail: $OUT" ;;\n')
    case("an UNGUARDED Detail: clause is caught — the exact #201 regression",
         unguarded_detail_arms(BAD), [5])
    case("...and it names only the offending arm", unguarded_detail_arms(BAD) == [5, 6], False)
    case("an arm that forwards $OUT with no label is not a problem",
         unguarded_detail_arms('case "$RC" in\n  0) PAYLOAD="$OUT" ;;\n  *) : ;;\nesac\n'), [])
    case("the LAST arm before the catch-all is still bounded, not run to the end of file",
         unguarded_detail_arms(
             'case "$RC" in\n  5) PAYLOAD="x. Detail: $OUT" ;;\n  *) : ;;\nesac\n'
             'echo [ -n "$OUT" ]\n'), [5])

    # ── verdict ────────────────────────────────────────────────────────────────────────────
    D = {"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3, "BAD_RESPONSE": 4,
         "UNREADABLE_PLAN": 5, "UNANSWERABLE": 6}
    case("the live shape agrees", verdict(D, {0, 3, 5, 6}, []), [])
    case("a defined code with no arm and no written reason is refused — #202's shape",
         len(verdict({**D, "SEVENTH": 7}, {0, 3, 5, 6}, [])), 1)
    # ⛔ NO UNGUARDED `[0]`, AND ITS ABSENCE TRUNCATED THIS SUITE. Written as `verdict(...)[0]`,
    # any mutation that empties the list raised IndexError here and the run DIED — so every case
    # BELOW this line never executed, and a mutation whose named case sits lower looked
    # unattributable. Measured 2026-09-30: the harness reported `expect` matched 0 red cases and
    # named a different one, over a sweep that then refused to issue a coverage verdict at all.
    # ⚠ Same rule as "a mutation must produce a wrong ANSWER, not a crash", pointing the other way:
    # a CASE that can raise hides every case after it.
    case("...and the message names the code and the row it needs",
         any("rc 7 (SEVENTH)" in x for x in verdict({**D, "SEVENTH": 7}, {0, 3, 5, 6}, [])), True)
    # ⛔ THE ESCAPE'S OWN FALSIFIER, and my first attempt at this case was WRONG: it passed
    # handled={0,3,5}, which leaves rc 6 genuinely undeclared, so the refusal was correct and the
    # case was asserting the opposite of what it meant. The escape is only testable by REMOVING a
    # row and watching the same input flip.
    _saved = DELIBERATELY_UNHANDLED.pop(4)
    try:
        case("a defined code with NO arm and NO row is refused (rc 4, row removed)",
             len(verdict(D, {0, 3, 5, 6}, [])), 1)
    finally:
        DELIBERATELY_UNHANDLED[4] = _saved
    case("...and restoring its written reason makes the SAME input pass",
         verdict(D, {0, 3, 5, 6}, []), [])
    case("a DEAD arm is refused", len(verdict(D, {0, 3, 5, 6, 9}, [])), 1)
    case("an unguarded arm is refused even when every code is handled",
         len(verdict(D, {0, 3, 5, 6}, [5])), 1)
    # ⚠ AND THE TABLE MUST BE TOTAL OVER WHAT IT CLAIMS: every row names a code the matcher
    # actually defines, or the row is a reason for something that does not exist.
    case("every DELIBERATELY_UNHANDLED row names a defined code",
         sorted(set(DELIBERATELY_UNHANDLED) - set(defined_codes(RC).values())), [])

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

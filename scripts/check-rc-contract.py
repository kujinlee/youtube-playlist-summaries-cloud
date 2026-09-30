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
    python3 scripts/check-rc-contract.py --self-test  # 50 cases
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
    2: "CANNOT RUN means NOTHING WAS ATTEMPTED, and round 3 H2 established that it carries three "
       "shapes rather than one: no plan armed; no mode flag at all (`main`); and argparse's own "
       "usage exit, which is also 2 — measured, `--fier` and `--fire --extra` both exit 2, and "
       "that number belongs to argparse's convention rather than to this contract. ⚠ THE PREVIOUS "
       "WORDING SAID ONLY 'no plan armed' AND WAS THEREFORE FALSE TWICE OVER. "
       "⛔ AND THE PREVIOUS WORDING ENDED 'if you find yourself widening this sentence again, "
       "split the code instead' — so this correction owes that test an answer. It is not a "
       "widening: all three shapes are the SAME meaning, which is that the matcher never got to "
       "look, and a caller is right to be silent about every one of them. The meaning that did NOT "
       "belong — 'armed, and the answer cannot be reached' — was split out as rc 6 in #202 and "
       "extended to `--arm` and `--fire` in round 3. ⚠ Argparse's 2 is also not mine to renumber "
       "without wrapping its exit, and doing that to win a documentation argument would trade a "
       "true sentence for a worse program.",
    4: "RESPONSE REJECTED can only arise on the `--arm` path, and this hook runs `--fire` only. "
       "⛔ THE EVIDENCE THIS ROW USED TO GIVE WAS FALSE — round 3 M1. It said 'every "
       "`ResponseRejected` raise site is inside `parse_response`'. Derived by AST rather than "
       "asserted: FIVE are (`:612`, `:618`, `:633`, `:639`, `:642`) and ONE is in "
       "`no_duplicate_keys` (`:580`). ⚠ The conclusion survives — `no_duplicate_keys` has exactly "
       "one caller, passed as `object_pairs_hook` inside `parse_response`, and `parse_cache` "
       "passes none — but it survives for a DIFFERENT reason than the one written here, and a row "
       "whose reason is false is a rubber stamp however right its verdict. "
       "⚠ AND THE FALSE SENTENCE WAS COPIED from the architecture review, where it was already "
       "false at the reviewed tree. A citation inherited without re-deriving it. "
       "⚠ Nothing asserts the property mechanically, and it lives on the far side of the seam from "
       "the code that depends on it — so if `--fire` ever validates a cached name as a response, "
       "this entry is what will be silently wrong.",
}

# ⛔ ROUND 3 M1 — THIS WAS `^\s{2}(\d+)\)`, WHICH MATCHED ONLY TWO-SPACE INDENTATION, AND THE
# GUARD BUILT TO CATCH SILENT WRONGNESS WAS SILENTLY WRONG. Reproduced by the reviewer: a `4)` arm
# indented FOUR spaces is invisible, so `handled_codes` returns {0,3,5,6}, `unguarded_detail_arms`
# returns [], and `verdict` returns [] — while bash would handle rc 4 and build an unguarded
# `Detail:` payload. That is exactly this guard's own subject.
#
# ⛔ AND WIDENING THE PATTERN IS NOT THE WHOLE FIX. This repo's recorded verdict for a hand-rolled
# reader is that it "CANNOT be made correct. It CAN be made unable to be silently wrong" — so the
# indentation is now free AND `arm_soundness` below enumerates every arm-shaped line in the `case`
# block and refuses anything it cannot classify. A shape this does not understand becomes a
# CANNOT-RUN instead of a quietly missing arm.
_ARM_RE = re.compile(r"^[ \t]*(\d+)\)", re.M)
# Any arm head at all — a number, the catch-all, or a pattern this guard does not model.
_ARM_SHAPE_RE = re.compile(r"^[ \t]*([^\s#][^)\n]*)\)", re.M)
# ⛔ ROUND 3 M4 — THIS REQUIRED THE LABEL AND `$OUT` TO BE ADJACENT, so splitting the hook's own
# append idiom across two statements made a #201 defect invisible (measured). The two halves are
# separate now and an arm is judged on whether it mentions BOTH anywhere within itself, which is
# the property that matters: an arm promising a detail while able to have none.
_OUT_LABEL = re.compile(r"(?:Detail|detail):")
_OUT_REF = re.compile(r"\$OUT|\$\{OUT\}")
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


def case_block(hook_src: str) -> str | None:
    """-> the text between `case ... in` and its `esac`, or None if that cannot be located.

    ⚠ BOUNDED ON PURPOSE. Scanning the whole file for arm shapes would read a heredoc, a comment
    block or any parenthesised prose as an arm; scanning only inside the `case` keeps membership
    decidable by syntax, which is the same argument `peer-sites.py` records for asking about peers
    within a CONTAINER rather than similar lines anywhere.
    """
    start = re.search(r"^\s*case\s+.*\s+in\s*$", hook_src, re.M)
    if not start:
        return None
    end = re.search(r"^\s*esac\s*$", hook_src[start.end():], re.M)
    if not end:
        return None
    return hook_src[start.end():start.end() + end.start()]


def structural_lines(block: str) -> list[str]:
    """-> the lines of the block that BEGIN outside any quoted string.

    ⛔ ROUND 3 B2 — THIS TRACKED DOUBLE QUOTES ONLY AND THE DOCSTRING CLAIMED AN UNMODELLED FORM
    BECAME A CANNOT-RUN. It did not: `arm_soundness` refuses a head it cannot CLASSIFY, and a bare
    integer inside a SINGLE-quoted string classifies perfectly well. The reviewer adjudicated it
    against real bash — one single-quoted multi-line payload and the guard reported
    `handled {0,3,5,6}`, sound, `verdict` empty, exit 0, while bash dropped rc 5 entirely. A guard
    giving a WRONG ANSWER where its own docstring promised a refusal is #202's shape inside the
    instrument built to catch #202.

    ⚠ BASH QUOTING, MODELLED AS A THREE-STATE MACHINE rather than a parity count: inside double
    quotes a backslash escapes, inside SINGLE quotes nothing escapes and only `'` ends the string,
    and a `"` inside single quotes is literal (and vice versa). A parity count over both characters
    gets every one of those wrong.

    ⚠ WHAT IS STILL NOT MODELLED IS NOW REFUSED RATHER THAN DESCRIBED — see `unmodelled_quoting`.
    """
    out: list[str] = []
    state = None  # None | '"' | "'"
    for line in block.split("\n"):
        if state is None:
            out.append(line)
        i = 0
        while i < len(line):
            c = line[i]
            if state == "'":
                if c == "'":
                    state = None
            elif state == '"':
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    state = None
            else:
                if c == "\\":
                    i += 2
                    continue
                # ⛔ A COMMENT IS NOT CODE, AND SCANNING ONE OPENED A PHANTOM STRING. Measured on
                # the live hook: an apostrophe in a comment ("the NAG's message") put the machine
                # into single-quote state, so the next arm head began "inside a string" and every
                # reader downstream saw the wrong lines. In bash a `#` at a word boundary starts a
                # comment and runs to end of line; quotes inside it are literal text.
                if c == "#" and (i == 0 or line[i - 1] in " \t"):
                    break
                if c in ('"', "'"):
                    state = c
            i += 1
    return out


def unmodelled_quoting(block: str) -> list[str]:
    """A SOUNDNESS CHECK over quoting forms — what this module cannot read must REFUSE.

    ⛔ ROUND 3 B2's OTHER HALF, and the reason the docstring's promise is now true instead of
    merely written. `structural_lines` models double and single quotes. It does NOT model
    `$'...'` (ANSI-C quoting, where backslash escapes differ) or heredocs (`<<`, `<<-`), and a
    line inside either could be read as structure. So their PRESENCE is refused outright: the
    guard says "I cannot read this" instead of answering over text it has misparsed.
    """
    problems: list[str] = []
    if re.search(r"\$'", block):
        problems.append("the `case` block uses ANSI-C quoting (`$'…'`), whose escaping this guard "
                        "does not model. No statement about which codes are handled is possible.")
    # ⛔ ROUND 4 H1 — THIS WAS `<<-?\s*[\w'\"]` AND MISSED AN ESCAPED DELIMITER. Bash accepts
    # `<<\EOF`, whose first character is a backslash and therefore outside that class, so the
    # guard answered over heredoc BODY text and reported rc 5 as handled where bash has no `5)`
    # arm at all — adjudicated against real bash by the reviewer. That is the exact failure shape
    # B2's fix was written to close, one character narrower.
    # ⭐ SO THE DETECTOR IS PESSIMISTIC NOW, NOT PRECISE: any `<<` that is not a herestring is
    # refused, whatever follows it. A soundness check is only as sound as its detector, and the
    # asymmetry is deliberate — a spurious cannot-run is LOUD and costs a person one look, while a
    # missed one is silent and costs a wrong answer. `(?!<)` excludes `<<<`, bash's herestring,
    # which the live hook does use (outside the `case` block) and which has no unmodelled body.
    # ⚠ THE LOOK-BEHIND IS REQUIRED, and my own adjacent negative caught its absence: `<<(?!<)`
    # still matches `<<<` at OFFSET 1, where the lookahead sees the quote rather than a third `<`.
    # So a herestring would have been refused and this guard would be red on the real repo.
    if re.search(r"(?<!<)<<(?!<)", block):
        problems.append("the `case` block contains a heredoc (`<<`), whose body this guard does "
                        "not model. No statement about which codes are handled is possible.")
    return problems


def arm_soundness(block: str) -> list[str]:
    """A SOUNDNESS CHECK — every arm-shaped line is accounted for, or the guard cannot run.

    ⛔ ROUND 3 M1's OTHER HALF. `handled_codes` answers "which codes are handled"; this answers
    "did I understand every arm I was looking at". Without it, an arm shape this module does not
    model — `4|5)`, `[45])`, a quoted pattern — is simply absent from the answer, and an absent
    arm reads as an unhandled code or as no finding at all. Distinct from a falsifier: a falsifier
    protects the CLAIM, this protects the READING the claim is derived from.
    """
    problems: list[str] = []
    for m in _ARM_SHAPE_RE.finditer("\n".join(structural_lines(block))):
        head = m.group(1).strip()
        if head == "*" or head.isdigit():
            continue
        problems.append(
            f"the `case` block holds an arm head this guard does not model: {head!r}. It is "
            f"neither a bare integer nor the `*` catch-all, so no statement about which codes are "
            f"handled is possible. Treat this as NOT RUN and teach the guard the shape."
        )
    return problems


def handled_codes(hook_src: str) -> set[int]:
    """-> every integer a `case` arm names, at ANY indentation, on STRUCTURAL lines only."""
    return {int(m.group(1))
            for m in _ARM_RE.finditer("\n".join(structural_lines(hook_src)))}


def unguarded_detail_arms(hook_src: str) -> list[int]:
    """-> arms that interpolate $OUT into a labelled clause with no `-n "$OUT"` guard. #201's shape.

    An arm runs from its `N)` to the next `N)` or to `*)`. Within that span, a `Detail: $OUT` is
    only honest if some `[ -n "$OUT" ]` appears in the same span — either guarding the whole
    assignment, as `0)` and `3)` do, or guarding the clause's append, as `5)` and `6)` now do.
    """
    spans = []
    marks = [(m.start(), int(m.group(1))) for m in _ARM_RE.finditer(hook_src)]
    # ⛔ ROUND 3 H1 — M1 FREED `_ARM_RE`'s INDENTATION AND LEFT THIS LINE AT TWO SPACES, so M1
    # was fixed as an INSTANCE. Measured by the reviewer: two hooks identical but for the
    # indentation of `*)`, and at four spaces a genuine #201 defect in the `6)` arm went
    # unreported while `arm_soundness` stayed clean. The mutation added for M1 targets `_ARM_RE`
    # and cannot see this line, which is why it survived the fix.
    m_catchall = re.search(r"^[ \t]*\*\)", hook_src, re.M)
    end_of_case = m_catchall.start() if m_catchall else len(hook_src)
    for i, (pos, code) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else end_of_case
        spans.append((code, hook_src[pos:stop]))
    bad = []
    for code, body in spans:
        if (_OUT_LABEL.search(body) and _OUT_REF.search(body)
                and not _NONEMPTY_GUARD.search(body)):
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
    # ⛔ THE READING IS CHECKED BEFORE THE CLAIM IS MADE — round 3 M1. An arm shape this module
    # does not model would otherwise be simply absent from `handled`, and an absent arm reads as
    # "no finding" rather than as "I could not look".
    block = case_block(hook_src)
    if block is None:
        print("FAILED: could not locate the hook's `case ... in` / `esac` block, so no statement "
              "about which codes it handles is possible. Treat this as NOT RUN.")
        return 2
    unsound = unmodelled_quoting(block) + arm_soundness(block)
    if unsound:
        print(f"FAILED: {len(unsound)} arm shape(s) this guard cannot classify — treat as NOT RUN:")
        for u in unsound:
            print(f"  ✗ {u}")
        return 2
    handled = handled_codes(block)
    if not handled:
        print("FAILED: found no `case` arms in the hook at all, which cannot be right. NOT RUN.")
        return 2
    problems = verdict(defined, handled, unguarded_detail_arms(block))
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

    # ── round 3 M1: indentation must not hide an arm, and an unmodelled shape must REFUSE ──
    # ⛔ THE REVIEWER'S EXACT REPRO. A `4)` arm indented four spaces was invisible, so `verdict`
    # returned [] while bash would handle rc 4 and build an unguarded `Detail:` payload.
    FOUR_SPACE = ('case "$RC" in\n'
                  '    4) PAYLOAD="rejected. Detail: $OUT" ;;\n'
                  '  0) : ;;\n  3) : ;;\n  5) : ;;\n  6) : ;;\n  *) : ;;\nesac\n')
    case("an arm indented FOUR spaces is still an arm — round 3 M1",
         4 in handled_codes(case_block(FOUR_SPACE) or ""), True)
    case("...and its unguarded Detail: is caught, which it was not before",
         unguarded_detail_arms(case_block(FOUR_SPACE) or ""), [4])
    case("a tab-indented arm is an arm",
         handled_codes(case_block('case "$RC" in\n\t7) : ;;\n  *) : ;;\nesac\n') or ""), {7})
    # ⛔ THE SOUNDNESS CHECK: a shape this guard does not model must REFUSE, not vanish.
    case("an OR-pattern arm is a cannot-run, not a silently missing arm",
         len(arm_soundness(case_block('case "$RC" in\n  4|5) : ;;\n  *) : ;;\nesac\n') or "")), 1)
    case("a bracket-class arm is a cannot-run too",
         len(arm_soundness(case_block('case "$RC" in\n  [45]) : ;;\n  *) : ;;\nesac\n') or "")), 1)
    case("...and the canonical block is sound", arm_soundness(case_block(HOOK_OK) or ""), [])
    # ⚠ THE BLOCK BOUND ITSELF: prose outside `case` must not be read as an arm.
    case("text after esac is not part of the block",
         "9)" in (case_block('case "$RC" in\n  0) : ;;\n  *) : ;;\nesac\nfoo 9) bar\n') or ""),
         False)
    case("no case block at all is a cannot-run", case_block("echo hi\n"), None)
    case("a case block with no esac is a cannot-run",
         case_block('case "$RC" in\n  0) : ;;\n'), None)

    # ── round 3 M1, third move: a multi-line payload's continuation is CONTENT, not an arm ──
    # ⛔ THE SHAPE THAT ACTUALLY FIRED ON THE LIVE HOOK. The rc=3 arm's payload spans lines and its
    # continuation begins at column 0 with `(one model call, …). Detail: $OUT" ;;`. A line-local
    # reader calls that an arm head; it is inside an open double quote.
    MULTILINE = ('case "$RC" in\n'
                 '  3) [ -n "$OUT" ] && PAYLOAD="stale, so no entry was\n'
                 'surfaced for this step. Run `--arm` to match this plan\n'
                 '(one model call, ~16s, covers every step). Detail: $OUT" ;;\n'
                 '  *) : ;;\nesac\n')
    case("a multi-line payload's continuation is not an arm head",
         arm_soundness(case_block(MULTILINE) or ""), [])
    case("...and the arm it belongs to is still found", handled_codes(case_block(MULTILINE) or ""),
         {3})
    case("an escaped quote does not flip the string state",
         arm_soundness(case_block('case "$RC" in\n  3) X="a \\" b\n(not an arm). y" ;;\n  *) : ;;\nesac\n')
                       or ""), [])
    # ⚠ AND THE OTHER DIRECTION: a genuine arm on a structural line must still be seen, so the
    # quote tracking cannot be satisfied by simply ignoring everything.
    case("a real arm AFTER a multi-line payload is still found",
         handled_codes(case_block(MULTILINE.replace('  *) : ;;', '  6) : ;;\n  *) : ;;')) or ""),
         {3, 6})

    # ── round 3 B2 — SINGLE QUOTES, THE FORM THAT GAVE A WRONG ANSWER ───────────────────────
    # ⛔ The docstring promised an unmodelled quoting form became a cannot-run. It did not: a bare
    # integer inside a SINGLE-quoted string classifies fine, so the reviewer's hook reported
    # handled {0,3,5,6} / sound / verdict empty / exit 0 while real bash dropped rc 5.
    SINGLE = ("case \"$RC\" in\n"
              "  3) PAYLOAD='stale, and this is a long message\n"
              "  5) not an arm — inside the single-quoted payload\n"
              "  it ends here' ;;\n"
              "  *) : ;;\nesac\n")
    case("a SINGLE-quoted payload's continuation is not an arm — round 3 B2",
         handled_codes(case_block(SINGLE) or ""), {3})
    case("...and the guard does not invent rc 5 from inside that string",
         5 in handled_codes(case_block(SINGLE) or ""), False)
    # ⛔ A COMMENT IS NOT CODE. An apostrophe in a comment put the machine into single-quote state
    # on the LIVE hook, so the next arm head read as string content — measured, and the reason the
    # soundness check refused twice before this was modelled.
    COMMENTED = ('case "$RC" in\n  # the NAG\'s message is deduped\n  5) : ;;\n  *) : ;;\nesac\n')
    case("an apostrophe in a COMMENT does not open a string",
         handled_codes(case_block(COMMENTED) or ""), {5})
    # ⛔ AND WHAT IS STILL NOT MODELLED MUST REFUSE, which is what makes the docstring true now.
    case("ANSI-C quoting is refused, not guessed at",
         len(unmodelled_quoting("  3) PAYLOAD=$'a\\nb' ;;\n")), 1)
    case("a heredoc is refused, not guessed at",
         len(unmodelled_quoting("  3) cat <<EOF\nstuff\nEOF\n")), 1)
    # ⛔ ROUND 4 H1's EXACT REPRO. `<<\EOF` is a legal escaped delimiter and the old class-based
    # detector missed it, so the guard counted a heredoc BODY line as an arm.
    case("an ESCAPED heredoc delimiter is refused too — round 4 H1",
         len(unmodelled_quoting("  3) cat <<\\EOF\n  5) heredoc body, not an arm\nEOF\n")), 1)
    case("...and a quoted delimiter is refused",
         len(unmodelled_quoting("  3) cat <<'EOF'\nbody\nEOF\n")), 1)
    case("...and a tab-stripping delimiter is refused",
         len(unmodelled_quoting("  3) cat <<-EOF\nbody\nEOF\n")), 1)
    # ⚠ THE ADJACENT NEGATIVE, and it is load-bearing: `<<<` is a HERESTRING, which the live hook
    # uses. Refusing it would make this guard red on the real repo forever.
    case("a herestring is NOT a heredoc and must not be refused",
         unmodelled_quoting('  0) python3 -c x <<<"$PAYLOAD" ;;\n'), [])
    case("the live shape uses neither, so it is not refused",
         unmodelled_quoting(case_block(HOOK_OK) or ""), [])

    # ── round 3 H1 — the CATCH-ALL bound was left at two spaces when M1 freed the arm reader ──
    # ⚠ THE CATCH-ALL'S BODY CARRIES THE GUARD, and that is what makes this fixture SENSITIVE.
    # Two earlier versions were INERT and each passed for an ambient reason: with nothing after
    # `esac` the bound cannot matter (`case_block` already strips it), and with an empty catch-all
    # body the last arm absorbing `*) : ;;` changes no answer. MEASURED both ways — only when the
    # catch-all body holds `[ -n "$OUT" ]` does a broken bound swallow it and silence a true
    # finding: fixed `[6]`, broken `[]`.
    FOUR_STAR = ('case "$RC" in\n  6) PAYLOAD="x"\n     PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n'
                 '    *) [ -n "$OUT" ] && : ;;\nesac\n')
    case("a four-space catch-all still bounds the last arm — round 3 H1",
         unguarded_detail_arms(case_block(FOUR_STAR) or ""), [6])
    case("...and a tab-indented catch-all does too",
         unguarded_detail_arms(case_block(FOUR_STAR.replace("    *)", "\t*)")) or ""), [6])

    # ── round 3 M4 — the label and $OUT need not be ADJACENT ─────────────────────────────────
    SPLIT = ('case "$RC" in\n  5) PAYLOAD="x. Detail:"\n     PAYLOAD="$PAYLOAD $OUT" ;;\n'
             '  *) : ;;\nesac\n')
    case("a Detail: promise split across two statements is still caught — round 3 M4",
         unguarded_detail_arms(case_block(SPLIT) or ""), [5])
    case("...and ${OUT} counts as a reference too",
         unguarded_detail_arms(case_block(SPLIT.replace("$OUT", "${OUT}")) or ""), [5])
    # ⚠ THE ADJACENT NEGATIVE: an arm mentioning a label but never $OUT promises nothing.
    case("an arm with a label and no $OUT is not a problem",
         unguarded_detail_arms(case_block('case "$RC" in\n  5) PAYLOAD="no Detail: here" ;;\n  *) : ;;\nesac\n') or ""), []),

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

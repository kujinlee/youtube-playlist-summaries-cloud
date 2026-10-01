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
    python3 scripts/check-rc-contract.py --self-test  # 40 cases
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
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
    # ⛔ ROUND 4 B2 — THERE IS NO ROW FOR rc 0, AND THERE MUST NOT BE. One existed, excusing the
    # absence of the `0)` arm with the reason "rc 0 IS handled … listed only so the table below is
    # total". That cosmetic motive DEFEATED R1 on the most important code in the contract:
    # measured, deleting the arm that forwards every match left the guard printing
    # `handled [3,5,6]` and then `rc contract OK`, while bash forwarded nothing at all. A row
    # whose premise is "this is already handled" is a row that stops checking whether it is.
    # ⚠ AND ITS PREMISE WAS TESTED BY NOTHING: every other row is falsifiable by removal, and the
    # suite popped row 4 and never row 0.
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


# ⛔ THE BASH LEXER IS GONE. WHAT REPLACED IT IS AN OBSERVATION.
# ─────────────────────────────────────────────────────────────────────────────────────────────
# ⭐ THIS IS THE REDESIGN THE ARMING CONDITION CALLED FOR, and `dev-process.md:108` fired for the
# first time in this fold to produce it. Round 3's B2, round 4's Codex H1 and round 4's B1/M1/M2
# were all findings in ONE component — `structural_lines` + `unmodelled_quoting`, 58 non-comment
# lines — across two consecutive rounds, every one of them caused by the previous round's fix.
# `review-method.md`'s test, *can a redesign remove it?*, answered YES: each was an instance of one
# sentence, **"my hand-rolled bash lexer differs from bash's"**:
#
#   round 3 B2        a bare integer inside a SINGLE-quoted string classified as an arm
#   round 3 (live)    an apostrophe in a COMMENT opened a phantom single-quote state
#   round 4 Codex H1  `<<\EOF`, an escaped heredoc delimiter, slipped the refusal
#   round 4 B1        `$( … )` and backticks open a nested context; nothing refused them
#   round 4 M1        the pessimistic `<<` refusal then fired on a COMMENT — 5 of 5 legitimate
#                     probes refused, including the comment documenting the constraint itself
#
# Six more quoting forms would have followed, because the set of ways bash can quote a line is not
# finite in any useful sense and I was enumerating REJECTIONS.
#
# ⭐ SO THE QUESTION IS ADJUDICATED BY THE ONLY AUTHORITY THAT CAN ANSWER IT: bash. The hook is
# RUN against a stub matcher that exits with a chosen code and prints chosen output, and what it
# forwards is OBSERVED. Every quoting form — single, double, ANSI-C, heredoc, command
# substitution, backtick, comment — is handled correctly because bash handles it, and this module
# no longer has an opinion about any of them.
#
# ⚠ THE MEASURED CASE FOR IT, from the round-4 reviewer: 209 production lines guarding a 14-line
# executable `case` block, of which 49 are the rules R1/R2/R3 (zero Blockings in any round) and 91
# re-implement bash's lexer (EVERY Blocking and High in this component). "The guard earns its
# existence; its reader does not earn 91 lines."
#
# ⚠ WHAT THIS COSTS, stated rather than discovered: the guard now EXECUTES the hook, so it needs a
# `bash` on PATH and it is slower — one process per probe. It also cannot see an arm for a code
# outside the probe range; that bound is named in `dead_arms`.


def _stub_tree(hook_src: str, rc: int, out: str, td: str) -> Path:
    """Stage a tree the hook will accept, with a matcher stub that exits `rc` and prints `out`.

    ⚠ The hook resolves its own repo root from `BASH_SOURCE`, so the layout matters and nothing
    else does: it needs `.claude/hooks/<itself>` and `scripts/recall-llm.py`.
    """
    root = Path(td)
    (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    hook = root / ".claude" / "hooks" / "surface-recall.sh"
    hook.write_text(hook_src, encoding="utf-8")
    stub = root / "scripts" / "recall-llm.py"
    # ⚠ `repr(out)` rather than an f-string interpolation: the payloads under test contain quotes,
    # backslashes and newlines, and building the stub by concatenation is how this module's
    # predecessor got into trouble in the first place.
    stub.write_text(
        "import sys\n"
        f"sys.stdout.write({out!r})\n"
        f"sys.exit({rc})\n",
        encoding="utf-8")
    return hook


def observe(hook_src: str, rc: int, out: str) -> str:
    """-> exactly what the hook FORWARDS when the matcher exits `rc` having printed `out`.

    The empty string means the hook stayed silent. ⛔ A non-zero bash exit or unparseable output is
    a CANNOT-RUN and never an empty answer: silence and "I could not look" must not be the same
    observation, which is the contract this guard exists to police.
    """
    with tempfile.TemporaryDirectory() as td:
        hook = _stub_tree(hook_src, rc, out, td)
        try:
            proc = subprocess.run(["bash", str(hook)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError as exc:
            raise CannotRun(f"no `bash` on PATH, so the hook cannot be adjudicated ({exc})") from exc
        except subprocess.TimeoutExpired as exc:
            raise CannotRun(f"the hook did not finish within 30s at rc={rc}") from exc
        if proc.returncode != 0:
            raise CannotRun(f"the hook exited {proc.returncode} at rc={rc}, which it documents it "
                            f"never does ('NEVER BLOCKS, NEVER FAILS THE CALL')")
        text = proc.stdout.strip()
        if not text:
            return ""
        try:
            return json.loads(text)["hookSpecificOutput"]["additionalContext"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise CannotRun(f"the hook printed something that is not its documented envelope at "
                            f"rc={rc}: {text[:120]!r} ({exc})") from exc


# A payload the hook cannot mistake for empty, used as the "there IS detail" probe.
_PROBE = "PROBE-DETAIL-TEXT"


def handled_codes(hook_src: str, codes: set[int]) -> set[int]:
    """-> the codes the hook actually ACTS on, observed by running it.

    A code is handled when the hook forwards something for it with detail available. ⚠ A code whose
    only behaviour is silence is NOT handled, which is the whole point: #202 was a code the hook
    received and dropped.
    """
    return {rc for rc in sorted(codes) if observe(hook_src, rc, _PROBE)}


def dangling_detail(hook_src: str, codes: set[int]) -> list[int]:
    """-> codes whose payload promises a detail the hook does not have. Backlog #201's shape.

    Observed, not parsed: run each code with NO output from the matcher and look for a label with
    nothing after it. That is exactly what a reader saw from the second firing onward, so it is
    what this asks about.
    """
    bad = []
    for rc in sorted(codes):
        payload = observe(hook_src, rc, "")
        if not payload:
            continue
        for label in ("Detail:", "detail:"):
            head, sep, tail = payload.partition(label)
            if sep and not tail.strip():
                bad.append(rc)
                break
    return bad


def dead_arms(hook_src: str, defined: set[int], probe_max: int = 15) -> list[int]:
    """-> codes the hook acts on that the matcher cannot emit. A dead arm reads as coverage.

    ⚠ BOUNDED, AND THE BOUND IS THE HONEST PART: codes 0..`probe_max` are probed. An arm for a
    code above that is invisible here. The contract's codes are single digits and adding a
    two-digit one would be a deliberate act, so the bound is stated rather than defended as
    complete.
    """
    return [rc for rc in range(probe_max + 1)
            if rc not in defined and observe(hook_src, rc, _PROBE)]


def verdict(defined: dict[str, int], handled: set[int], dangling: list[int],
            dead: list[int] | None = None) -> list[str]:
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
    for code in sorted(dead or []):
        problems.append(
            f"the hook ACTS on rc {code} and no matcher constant has that value — a dead arm, "
            f"which reads as coverage and is not. Observed by running the hook at that code."
        )
    for code in dangling:
        problems.append(
            f"at rc {code} the hook forwards a payload whose `Detail:` label has nothing after "
            f"it when the matcher printed no detail — OBSERVED by running it. That is what a "
            f"reader saw from the second firing onward, forever — backlog #201."
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
    # ⛔ ADJUDICATED BY RUNNING, NOT BY READING — see the observer section for why, and for the
    # arming condition that produced it. Every `CannotRun` here is a refusal, never a pass.
    try:
        codes = set(defined.values())
        handled = handled_codes(hook_src, codes)
        dangling = dangling_detail(hook_src, codes)
        dead = dead_arms(hook_src, codes)
    except CannotRun as exc:
        print(f"FAILED: {exc}. Treat this as NOT RUN.")
        return 2
    if not handled:
        print("FAILED: the hook acted on NONE of the matcher's codes, which cannot be right — "
              "either the stub tree is wrong or the hook is inert. Treat this as NOT RUN.")
        return 2
    problems = verdict(defined, handled, dangling, dead)
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
    CODES = {0, 2, 3, 4, 5, 6}

    # ── defined_codes — AST over the matcher. Unchanged by the redesign, and it has never had
    # a finding in four rounds, which is why it survived while the bash reader did not. ────────
    case("the rc tuple is read from the AST, names paired with values",
         defined_codes(RC), {"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3, "BAD_RESPONSE": 4,
                             "UNREADABLE_PLAN": 5, "UNANSWERABLE": 6})
    case("a new code is picked up without touching this guard",
         defined_codes(RC.replace(", UNANSWERABLE =", ", UNANSWERABLE, SEVENTH =")
                         .replace("5, 6\n", "5, 6, 7\n")).get("SEVENTH"), 7)
    raises("a matcher with NO rc tuple is a cannot-run", lambda: defined_codes("x = 1\n"), CannotRun)
    raises("a matcher that does not parse is a cannot-run",
           lambda: defined_codes("def broken(\n"), CannotRun)
    raises("TWO rc tuples is a cannot-run — the guard must not pick one and guess",
           lambda: defined_codes(RC + RC), CannotRun)
    case("an assignment missing one rc name is not the rc tuple",
         defined_codes(RC + "A, B = 1, 2\n"), defined_codes(RC))

    # ── the OBSERVER. Every case below runs real bash against a real hook. ───────────────────
    # ⚠ A SHARED SKELETON, so each fixture differs from the live hook only in its `case` block.
    def _hook(case_body: str) -> str:
        return ('#!/usr/bin/env bash\n'
                'set -uo pipefail\n'
                'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
                'OUT="$(python3 "$REPO_ROOT/scripts/recall-llm.py" --fire 2>&1)"; RC=$?\n'
                'PAYLOAD=""\n'
                'case "$RC" in\n' + case_body +
                '  *) : ;;\n'
                'esac\n'
                '[ -n "$PAYLOAD" ] || exit 0\n'
                "python3 -c 'import json,sys; "
                'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse",'
                '"additionalContext":sys.stdin.read()}}))\' <<<"$PAYLOAD"\n'
                'exit 0\n')

    CANON = _hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n'
                  '  3) [ -n "$OUT" ] && PAYLOAD="stale. Detail: $OUT" ;;\n'
                  '  5) PAYLOAD="unreadable."\n'
                  '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n'
                  '  6) PAYLOAD="no corpus."\n'
                  '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n')

    case("the canonical hook's handled codes are observed, not parsed",
         handled_codes(CANON, CODES), {0, 3, 5, 6})
    case("a silent code is NOT handled — #202 was a code the hook received and dropped",
         2 in handled_codes(CANON, CODES), False)
    case("the canonical hook promises no detail it lacks", dangling_detail(CANON, CODES), [])
    case("and it has no dead arm", dead_arms(CANON, CODES), [])

    # ⛔ #201's SHAPE, OBSERVED: a label with nothing after it when the matcher printed nothing.
    DANGLE = _hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n'
                   '  5) PAYLOAD="unreadable. Detail: $OUT" ;;\n')
    case("an unconditional Detail: label is caught by running the hook — backlog #201",
         dangling_detail(DANGLE, CODES), [5])
    # ⚠ THE ADJACENT NEGATIVE: the same arm, guarded, is fine.
    case("...and the guarded form is not flagged",
         dangling_detail(_hook('  5) PAYLOAD="unreadable."\n'
                               '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;\n'),
                         CODES), [])

    # ⛔ ROUND 4 B2 — THE ARM THAT FORWARDS EVERY MATCH. There is no escape row for rc 0 any more,
    # so deleting its arm must be refused rather than excused.
    NO_ZERO = _hook('  3) [ -n "$OUT" ] && PAYLOAD="stale. Detail: $OUT" ;;\n')
    case("deleting the 0) arm is observed as unhandled — round 4 B2",
         0 in handled_codes(NO_ZERO, CODES), False)
    case("...and the verdict refuses it, because rc 0 has no escape row",
         len(verdict(defined_codes(RC), handled_codes(NO_ZERO, CODES),
                     dangling_detail(NO_ZERO, CODES), [])) >= 1, True)

    # ⛔ THE FIVE QUOTING FORMS THAT DEFEATED THE LEXER ACROSS TWO ROUNDS. Each hook below claims a
    # `5)` arm in TEXT and has none in CODE; bash sends rc 5 to the catch-all, and so must this.
    for label, body in (
        ("command substitution — round 4 B1",
         '  3) PAYLOAD="stale $(echo \'5) not an arm\')" ;;\n'),
        ("backticks — round 4 B1, same shape",
         '  3) PAYLOAD="stale `echo \'5) not an arm\'`" ;;\n'),
        ("a single-quoted payload — round 3 B2",
         "  3) PAYLOAD='stale\n  5) not an arm\n  ends here' ;;\n"),
        ("an apostrophe in a comment — the live-hook shape",
         '  # the NAG\'s message is deduped\n  3) PAYLOAD="stale" ;;\n'),
        ("ANSI-C quoting",
         "  3) PAYLOAD=$'stale\\n  5) not an arm' ;;\n"),
    ):
        case(f"a 5) arm claimed only in text is NOT handled — {label}",
             5 in handled_codes(_hook(body), CODES), False)

    # ⛔ A HEREDOC PRINTS RAW TEXT, WHICH IS NOT THE HOOK'S ENVELOPE — so it is a CANNOT-RUN
    # rather than an answer. Round 4 Codex H1's `<<\EOF` is included, the form the old
    # class-based detector missed.
    raises("a heredoc arm that prints raw text is a cannot-run",
           lambda: handled_codes(_hook('  3) cat <<\\EOF\n  5) body\nEOF\n     ;;\n'), CODES),
           CannotRun)

    # ⛔ A DEAD ARM, OBSERVED. `7)` is acted on and no constant has that value.
    case("an arm for a code the matcher cannot emit is a dead arm",
         dead_arms(_hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n  7) PAYLOAD="dead" ;;\n'),
                   CODES), [7])
    case("...and the probe range is stated rather than assumed",
         dead_arms(_hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n  7) PAYLOAD="dead" ;;\n'),
                   CODES, probe_max=6), [])

    # ⛔ A HOOK THAT FAILS OR TALKS NONSENSE IS A CANNOT-RUN, NEVER A SILENT PASS.
    raises("a hook that exits non-zero is a cannot-run",
           lambda: observe('#!/usr/bin/env bash\nexit 3\n', 0, "x"), CannotRun)
    raises("a hook that prints something other than its envelope is a cannot-run",
           lambda: observe('#!/usr/bin/env bash\necho not-json\n', 0, "x"), CannotRun)
    case("a hook that prints nothing is silence, which is a real answer",
         observe('#!/usr/bin/env bash\nexit 0\n', 0, "x"), "")

    # ── EVERY OBSERVER PARAMETER IS EXERCISED AT TWO DISTINCT VALUES ────────────────────────
    # ⛔ `check-fixture-variation` refused this suite until it was, naming five parameters passed
    # the SAME value at every call site — `handled_codes.codes`, `dangling_detail.codes`,
    # `dead_arms.defined`, `observe.rc` and `observe.out`. A parameter no case can tell apart from
    # a constant leaves every clause that reads it unguarded, and this repo's record is that the
    # fix is to VARY the value, never to take an EXEMPT row.
    case("handled_codes honours a NARROWER code set — the parameter is read, not assumed",
         handled_codes(CANON, {0, 3}), {0, 3})
    case("...and an empty code set observes nothing at all",
         handled_codes(CANON, set()), set())
    case("dangling_detail honours a narrower set too",
         dangling_detail(DANGLE, {0, 3}), [])
    case("dead_arms with a DIFFERENT defined set reclassifies the same hook",
         dead_arms(_hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n  7) PAYLOAD="x" ;;\n'),
                   {0, 7}), [])
    # ⚠ `observe` at two distinct codes and two distinct payloads, so neither argument is a
    # constant this suite could not notice being ignored.
    case("observe reports the payload for rc 3 and its own text",
         "alpha" in observe(CANON, 3, "alpha"), True)
    case("...and at rc 6 with a different payload",
         "beta" in observe(CANON, 6, "beta"), True)
    case("...and the code it is given decides which arm answers",
         observe(CANON, 2, "gamma"), "")

    # ── verdict — pure, and unchanged in shape by the redesign ──────────────────────────────
    D = defined_codes(RC)
    case("the live shape agrees", verdict(D, {0, 3, 5, 6}, [], []), [])
    case("a defined code with no arm and no row is refused — #202's shape",
         len(verdict({**D, "SEVENTH": 7}, {0, 3, 5, 6}, [], [])), 1)
    case("...and the message names the code and the row it needs",
         any("rc 7 (SEVENTH)" in x for x in verdict({**D, "SEVENTH": 7}, {0, 3, 5, 6}, [], [])),
         True)
    # ⛔ EVERY ESCAPE ROW IS FALSIFIABLE BY REMOVAL — round 4 B2. The suite used to pop one row,
    # and the row it never popped was the one whose premise was false.
    for _code in sorted(DELIBERATELY_UNHANDLED):
        _saved = None
        try:
            _saved = DELIBERATELY_UNHANDLED.pop(_code)
            case(f"a defined code with NO arm and NO row is refused (rc {_code}, row removed)",
                 len(verdict(D, {0, 3, 5, 6} - {_code}, [], [])) >= 1, True)
        finally:
            if _saved is not None:
                DELIBERATELY_UNHANDLED[_code] = _saved
    case("a dead arm is refused", len(verdict(D, {0, 3, 5, 6}, [], [9])), 1)
    case("a dangling detail is refused even when every code is handled",
         len(verdict(D, {0, 3, 5, 6}, [5], [])), 1)
    case("every DELIBERATELY_UNHANDLED row names a defined code",
         sorted(set(DELIBERATELY_UNHANDLED) - set(D.values())), [])

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

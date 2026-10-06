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
  ⛔ R3 WAS HERE AND IS NOW `scripts/check-surface-recall.py`'s. It asked what the READER sees,
      which is a property of the hook alone — see the pointer above the DELIBERATELY_UNHANDLED
      table for why that relocation closed round 7 B2 by construction.

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
  * an arm interpolates `$OUT` after other text with no `-n` guard;

DOES NOT CHECK (round 5 L2 — stated, because an undeclared gap reads as covered)
  * THE THIRD DIRECTION: a status the matcher can EMIT that no constant DEFINES. python's own
    `1` from an uncaught exception and `127` from a missing `python3` both reach the hook, and
    nothing here reconciles them — R1 reads defined->handled and R2 reads arm->defined, so a
    status that is neither is invisible to both. Backlog row owed.
  * either file is missing, UNREADABLE or unparseable -> exit 2, CANNOT RUN, never a pass.

Usage:
    python3 scripts/check-rc-contract.py
    python3 scripts/check-rc-contract.py --self-test  # 56 cases
"""
from __future__ import annotations

import ast
import concurrent.futures
import json
import os
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

# ⛔ R3 LIVES IN `scripts/check-surface-recall.py` NOW, AND THIS IS A POINTER, NOT A COPY.
# `DECLARED_RENDER` and the equality that enforces it moved there on 2026-10-01. The reason is
# structural and it explains four rounds of history: R3's subject is THE HOOK'S RENDERED TEXT —
# this file's matcher entered only as the source of the code set — so R3 was never a cross-file
# rule, and every Blocking in rounds 3 to 7 landed on it while R1 and R2 produced none.
# ⭐ AND IT FIXED ROUND 7 B2 BY CONSTRUCTION. This file observes the hook by STAGING A MINIMAL
# TREE, which is a proxy for the repo; the hook's own guard runs the REAL hook IN THE REAL REPO
# through the ARGV seam, so there is no fabricated world left to be unfaithful.
# Measured: an arm branching on `$REPO_ROOT/.claude/settings.json` renders a dangling `Detail:`
# in the real repo — the new guard returns [5], this file's observer returned [].
# ⚠ THE SAME FIDELITY GAP STILL AFFECTS R1 AND R2 BELOW, and it is filed rather than hidden: an
# arm that acts only in the real repo can leave a dead arm invisible here. See backlog #209.
# ⚠ A SECOND COPY OF THE DECLARATION HERE WOULD DRIFT — the most-measured failure in this
# repository (17 instances, `check-vocabulary-collisions.py`). There is exactly one.

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
        # ⛔ ROUND 5 M3 + L4 — THE RAW COUNTS, NEVER THE FILTERED ONES. `len(names) != len(vals)`
        # compared the two lists AFTER each had independently dropped what it did not recognise,
        # so a drop at DIFFERENT indices on each side left the lengths equal and `zip` bound every
        # name to the wrong number. Measured: `OK, mod.X, CANNOT_RUN, … = 0,2,3,4,5,6,'s'` returned
        # exactly the live-looking {0,2,3,4,5,6} while python assigns `CANNOT_RUN=3 … ='s'` — 5 of
        # 6 misbound, and the whole guard then printed `rc contract OK` over it. ⚠ This was the ONE
        # branch of this function that failed WRONG while the other three failed closed, and the
        # docstring above asserts the opposite, which is why it earns a row despite needing a
        # source no plausible refactor produces.
        # ⚠ `len(set(vals))` is L4: two names sharing a value made `verdict`'s set arithmetic
        # report `rc contract OK` over five distinct codes while claiming six, or — worse — blame a
        # LIVE hook arm as a dead one. The matcher's own suite catches it cross-file, so this is
        # the diagnosis being wrong rather than the defect shipping.
        # ⚠ IT ACCEPTS THE REAL MATCHER TODAY, and that is the falsifier this repair owed:
        # measured at HEAD, raw targets=6 names=6 raw values=6 ints=6 distinct=6.
        if not (len(tgt.elts) == len(names) == len(node.value.elts)
                == len(vals) == len(set(vals))):
            raise CannotRun(
                f"the rc tuple assignment is not readable without guessing: "
                f"{len(tgt.elts)} target element(s) of which {len(names)} are plain names, "
                f"{len(node.value.elts)} value(s) of which {len(vals)} are ints, "
                f"{len(set(vals))} of those distinct. Every count must agree, because pairing "
                f"two independently filtered lists by POSITION is how a name binds to the wrong "
                f"number — round 5 M3/L4."
            )
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
            # ⛔ A SCRUBBED ENVIRONMENT — ROUND 8 H2, AND IT IS A REGRESSION I INTRODUCED. Round
            # 7 L1 fixed exactly this in the hook's own guard and round 7 H2 copied only the STDERR
            # REFUSAL back here — so this observer gained a refusal it could trip on its own
            # ambient noise. Measured: `PYTHONVERBOSE=1 python3 scripts/check-rc-contract.py
            # --self-test` exited 1 with "the hook wrote to STDERR ... NOT RUN". A guard whose
            # verdict depends on the caller's environment is backlog #56's shape — the reason a
            # gate gets switched off. Fixing an instance in one file and not its sibling is the
            # class this fold keeps paying for.
            _env = {k: v for k, v in os.environ.items() if k in SUBPROCESS_ENV_KEYS}
            proc = subprocess.run(["bash", str(hook)], capture_output=True, text=True,
                                  timeout=30, env=_env)
        except FileNotFoundError as exc:
            raise CannotRun(f"no `bash` on PATH, so the hook cannot be adjudicated ({exc})") from exc
        except subprocess.TimeoutExpired as exc:
            raise CannotRun(f"the hook did not finish within 30s at rc={rc}") from exc
        # ⛔ STDERR IS A REFUSAL HERE TOO — ROUND 7 H2. Round 6 H1's repair landed in
        # `check-surface-recall.render` and NOT here, so R1 and R2 went on reading a bash FATAL
        # ERROR as silence: the hook is `set -uo pipefail` with no `-e` and `exit 0`s by design,
        # so a misspelled tool inside an arm cannot be seen in its exit status. Measured on the
        # shipped hook: 12 of 12 invocations across six codes write EMPTY stderr, so refusing on
        # any stderr costs nothing here and converts an invisible failure into a cannot-run.
        # ⚠ Backlog #209 said the repair was owed; it did not say a working copy already existed
        # 400 lines away, which is why this sat unfixed through a whole round.
        if proc.stderr.strip():
            raise CannotRun(
                f"the hook wrote to STDERR at rc={rc}, which it cannot report through its exit "
                f"status: {proc.stderr.strip()[:200]!r}. Round 6 H1 / round 7 H2 — NOT RUN."
            )
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
# ⛔ ONE ALLOWLIST, NAMED, AND ITS SIBLING RECONCILES AGAINST IT BY A CASE — ROUND 8 H1. The scrub
# was hand-copied between this file and `check-surface-recall.py` with nothing comparing the two:
# the fix for a DRIFT defect was a second copy of itself.
# ⛔ `PYTHONDONTWRITEBYTECODE` IS LOAD-BEARING AND WAS MISSING — ROUND 2 MEDIUM (PR #366).
# The scrub above is an ALLOW-LIST, so it dropped the one variable the mutation harness sets
# to keep bytecode caches impossible while it measures. Reproduced at `77316edc`: a scrubbed
# child importing a module wrote `__pycache__/*.pyc` with the parent holding the variable.
# ⚠ The sibling case below asserted only that the two copies AGREE, which a wrong set held
# consistently satisfies — so the PROPERTY ("a scrubbed spawn writes no cache") is asserted
# directly now, over each file's own constant, and is what the mutation entries name.
SUBPROCESS_ENV_KEYS = ("PATH", "HOME", "TMPDIR", "LANG", "PYTHONDONTWRITEBYTECODE")

_PROBE = "PROBE-DETAIL-TEXT"


def handled_codes(hook_src: str, codes: set[int]) -> set[int]:
    """-> the codes the hook actually ACTS on, observed by running it.

    A code is handled when the hook forwards something for it with detail available. ⚠ A code whose
    only behaviour is silence is NOT handled, which is the whole point: #202 was a code the hook
    received and dropped.
    """
    return {rc for rc in sorted(codes) if observe(hook_src, rc, _PROBE)}


def dead_arms(hook_src: str, defined: set[int], probe_max: int = 255) -> list[int]:
    """-> codes the hook acts on that the matcher cannot emit. A dead arm reads as coverage.

    ⛔ ROUND 5 H1 — THIS PROBED 0..15 AND CALLED THE BOUND HONEST, WHICH IT WAS, AND A FAIL-OPEN,
    WHICH IT ALSO WAS. The reviewer put a `16)` arm in a hook and the guard reported agreement
    while `observe(hook, 16, …)` returned its payload: real, reachable, undefined executable code
    passing as clean. R2's contract — "every arm names a code the matcher can actually emit" — was
    not being met for anything above 15.

    ⭐ AND THE REPAIR IS NOT A BIGGER SAMPLE, IT IS NOTICING THE DOMAIN IS FINITE. A shell exit
    status is EIGHT BITS: measured, `bash -c 'exit 300'` reports 44, and a Python `sys.exit(300)`
    through bash reports 44 as well. So 0..255 is not a wider window — it is the WHOLE observable
    domain, and an arm written as `300)` is unreachable by construction rather than unsampled.
    Bounded black-box sampling became exhaustive enumeration, which is the difference between
    "I looked at some of it" and "there is no more of it to look at".

    ⚠ COST, MEASURED: 76 ms per probe serial, so 256 of them is ~20s. Run concurrently instead —
    each probe is an independent subprocess in its own temporary tree, so there is no shared state
    to serialise, and the wall clock comes back to a few seconds. `probe_max` stays a parameter
    because a case exercises a narrowed range, and because a parameter no case varies is one no
    case can tell from a constant.
    """
    codes = [rc for rc in range(probe_max + 1) if rc not in defined]
    if not codes:
        return []
    found: list[int] = []
    # ⚠ `max_workers` is modest on purpose: each probe spawns bash plus two short-lived pythons,
    # and oversubscribing a CI runner to save two seconds is a bad trade.
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for rc, payload in zip(codes, pool.map(lambda c: observe(hook_src, c, _PROBE), codes)):
            if payload:
                found.append(rc)
    return sorted(found)


def verdict(defined: dict[str, int], handled: set[int], dead: list[int]) -> list[str]:
    """PURE. -> the list of problems, empty when the two languages agree.

    ⛔ NO PARAMETER HAS A DEFAULT — round 5 H2. `dead` carried `| None = None`, so deleting ONE
    argument at the ONE call site switched R2 off entirely while the suite stayed green and the
    live run stayed rc=0 over a real `7)` dead arm. The case meant to cover it called this
    function directly and passed either way; the defect was in the WIRING, which is why each rule
    also has an end-to-end case through `main` over a staged tree that is wrong on purpose.
    """
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
    # ⚠ ROUND 5 L1 — CAPPED, AND THE CAP CARRIES THE DIAGNOSIS. A forwarding `*)` catch-all makes
    # EVERY unmatched status look like an arm, so the honest-but-useless output was ~250 lines each
    # naming an individual code, none of them the cause. One line that names the real shape beats
    # 250 that name the symptom.
    _dead = sorted(dead)
    if len(_dead) > 8:
        problems.append(
            f"the hook ACTS on {len(_dead)} different codes the matcher cannot emit "
            f"(e.g. {_dead[:4]} … {_dead[-2:]}) — at this volume the cause is a catch-all that "
            f"FORWARDS rather than one that is silent, which also makes R1 vacuous by making "
            f"every defined code look handled. Fix the `*)` arm, not the codes."
        )
    else:
        for code in _dead:
            problems.append(
                f"the hook ACTS on rc {code} and no matcher constant has that value — a dead arm, "
                f"which reads as coverage and is not. Observed by running the hook at that code."
            )
    return problems


def _read_or_refuse(path: Path) -> str:
    """-> the file's text, or CannotRun. Round 5 M2.

    `is_file()` establishes EXISTENCE, never READABILITY, and the header promised exit 2 for
    "missing or unparseable" while a permission-denied file exited 1 with a PermissionError
    traceback — a false sentence in the one file whose whole job is policing false sentences.
    Reproduced at `chmod 000`. Every OSError is the same answer: NOT RUN, never a pass.
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CannotRun(f"{path.name} exists but cannot be read ({exc.__class__.__name__})") from exc


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    for f in (MATCHER, HOOK):
        if not f.is_file():
            print(f"FAILED: {f.relative_to(ROOT)} not found — treat this as NOT RUN.")
            return 2
    try:
        defined = defined_codes(_read_or_refuse(MATCHER))
        hook_src = _read_or_refuse(HOOK)
    except CannotRun as exc:
        print(f"FAILED: {exc}. Treat this as NOT RUN.")
        return 2
    # ⛔ ADJUDICATED BY RUNNING, NOT BY READING — see the observer section for why, and for the
    # arming condition that produced it. Every `CannotRun` here is a refusal, never a pass.
    try:
        codes = set(defined.values())
        handled = handled_codes(hook_src, codes)
        # ⚠ THE INERT-HOOK REFUSAL MOVED UP HERE, and it is not cosmetic: it used to sit after
        # `dead_arms`, so an inert hook paid for 256 probes (measured 2.93s) before being refused,
        # and its self-test case cost the same. Refuse on the cheapest evidence that settles it.
        if not handled:
            print("FAILED: the hook acted on NONE of the matcher's codes, which cannot be right "
                  "— either the stub tree is wrong or the hook is inert. Treat this as NOT RUN.")
            return 2
        dead = dead_arms(hook_src, codes)
    except CannotRun as exc:
        print(f"FAILED: {exc}. Treat this as NOT RUN.")
        return 2
    problems = verdict(defined, handled, dead)
    print(f"rc contract: {len(defined)} code(s) defined, {len(handled)} handled by an arm, "
          f"{len(DELIBERATELY_UNHANDLED)} declared unhandled")
    if problems:
        print(f"FAILED — {len(problems)} disagreement(s) between the matcher and the hook:")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print("rc contract OK — every defined code is handled or declared, and no arm is dead. "
          "What the READER sees is check-surface-recall.py's rule, not this one")
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
    # ⛔ ROUND 7 H2 — A BASH FATAL ERROR IS A REFUSAL HERE TOO. Round 6 H1's repair landed only
    # in the hook's own guard, so R1 and R2 went a whole round still reading a fatal error as
    # silence. The hook exits 0 by design, so stderr is the only channel that can carry it.
    raises("a hook that writes to STDERR is a cannot-run, never silence — round 7 H2",
           lambda: observe(_hook('  5) echo "boom" >&2\n     PAYLOAD="x" ;;\n'), 5, _PROBE),
           CannotRun)

    # ⛔ R3'S CASES AND ITS ELEVEN-ARM CORPUS MOVED WITH THE RULE to
    # `scripts/check-surface-recall.py`, which observes the REAL hook in the REAL repo.
    # They are not deleted, they are RELOCATED — a retirement whose subject survives
    # elsewhere would be a ratchet fall dressed as bookkeeping, and the count is recorded
    # at both sites.

    # ⛔ ROUND 4 B2 — THE ARM THAT FORWARDS EVERY MATCH. There is no escape row for rc 0 any more,
    # so deleting its arm must be refused rather than excused.
    NO_ZERO = _hook('  3) [ -n "$OUT" ] && PAYLOAD="stale. Detail: $OUT" ;;\n')
    case("deleting the 0) arm is observed as unhandled — round 4 B2",
         0 in handled_codes(NO_ZERO, CODES), False)
    case("...and the verdict refuses it, because rc 0 has no escape row",
         len(verdict(defined_codes(RC), handled_codes(NO_ZERO, CODES), [])) >= 1, True)

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
    # ⛔ ROUND 5 H1 — AN ARM ABOVE THE OLD 15-CODE WINDOW. Real, reachable, undefined executable
    # code that passed as clean while `observe` returned its payload.
    case("a dead arm at 16 is caught — round 5 H1, the old window stopped at 15",
         dead_arms(_hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n  16) PAYLOAD="dead" ;;\n'),
                   CODES), [16])
    # ⚠ THE RANGE IS INCLUSIVE OF `probe_max`, pinned cheaply rather than by a 256-probe sweep —
    # `range(probe_max + 1)` is exactly the kind of off-by-one worth a case of its own.
    case("the probe range INCLUDES probe_max itself",
         dead_arms(_hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n  6) PAYLOAD="dead" ;;\n'),
                   {0, 2, 3, 4, 5}, probe_max=6), [6])
    # ⭐ WHY 0..255 IS EXHAUSTIVE RATHER THAN A WIDER SAMPLE, pinned by ONE probe instead of 256:
    # a shell exit status is eight bits, so `exit 300` ARRIVES AS 44 and an arm written `300)` can
    # never be reached. That makes the enumeration complete, not merely large — and the truth of
    # it is bash's, observed here, not an assumption of mine.
    case("an exit above 255 truncates, so an arm above 255 is unreachable by construction",
         observe(_hook('  44) PAYLOAD="truncated-300-lands-here" ;;\n'), 300, _PROBE).strip(),
         "truncated-300-lands-here")
    # ⚠ `probe_max` is still a parameter and still varied, so no clause reading it is unguarded.
    case("a narrowed probe range is honoured",
         dead_arms(_hook('  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;\n  16) PAYLOAD="dead" ;;\n'),
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
    case("the live shape agrees", verdict(D, {0, 3, 5, 6}, []), [])
    case("a defined code with no arm and no row is refused — #202's shape",
         len(verdict({**D, "SEVENTH": 7}, {0, 3, 5, 6}, [])), 1)
    case("...and the message names the code and the row it needs",
         any("rc 7 (SEVENTH)" in x for x in verdict({**D, "SEVENTH": 7}, {0, 3, 5, 6}, [])),
         True)
    # ⛔ EVERY ESCAPE ROW IS FALSIFIABLE BY REMOVAL — round 4 B2. The suite used to pop one row,
    # and the row it never popped was the one whose premise was false.
    for _code in sorted(DELIBERATELY_UNHANDLED):
        _saved = None
        try:
            _saved = DELIBERATELY_UNHANDLED.pop(_code)
            case(f"a defined code with NO arm and NO row is refused (rc {_code}, row removed)",
                 len(verdict(D, {0, 3, 5, 6} - {_code}, [])) >= 1, True)
        finally:
            if _saved is not None:
                DELIBERATELY_UNHANDLED[_code] = _saved
    case("a dead arm is refused", len(verdict(D, {0, 3, 5, 6}, [9])), 1)
    case("many dead arms collapse to ONE problem naming the catch-all — round 5 L1",
         len(verdict(D, {0, 3, 5, 6}, list(range(20, 60)))), 1)
    case("...and that one problem names the COUNT and the real cause, not a code",
         all(t in verdict(D, {0, 3, 5, 6}, list(range(20, 60)))[0]
             for t in ("40 different codes", "catch-all that FORWARDS")), True)
    case("...while a handful are still listed individually",
         len(verdict(D, {0, 3, 5, 6}, [9, 11])), 2)

    case("every DELIBERATELY_UNHANDLED row names a defined code",
         sorted(set(DELIBERATELY_UNHANDLED) - set(D.values())), [])
    # ⛔ THE LABEL LOOP, THE SHAPE LOOP AND THE WHOLE R4 BLOCK ARE RETIRED HERE, WITH THEIR
    # SUBJECT. They tested `dangling_detail` and `silent_codes`, two functions that no longer
    # exist: `_CORPUS` above contains the same arms (every label and every shape among them)
    # and asserts the stronger property, and silence is just "not the declared sentence" now.
    # ⚠ A retirement whose subject survives would be a ratchet FALL dressed as bookkeeping;
    # these are recorded at both sites with the count and the reason.

    # ── M2 — EXISTENCE IS NOT READABILITY ───────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as _td:
        raises("a path that exists and cannot be read is CannotRun, never a pass",
               lambda: _read_or_refuse(Path(_td)), CannotRun)

    # ── M3 / L4 — THE FALSIFIER THIS REPAIR OWED, IN BOTH DIRECTIONS ────────────────────────
    _TUPLE = "OK, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, UNREADABLE_PLAN, UNANSWERABLE"
    raises("a target the reader cannot pair is refused, not guessed — round 5 M3",
           lambda: defined_codes("OK, mod.X, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, "
                                 "UNREADABLE_PLAN, UNANSWERABLE = 0, 2, 3, 4, 5, 6, 's'"),
           CannotRun)
    # ⚠ THIS CASE EXISTS BECAUSE THE ONE BELOW DID NOT DISCRIMINATE. The sweep reported the
    # raw-TARGET mutation as a SURVIVOR: with 7 targets AND 7 values the mutated chain still
    # failed on `len(node.value.elts) != len(vals)`, so both versions raised and no case could
    # tell them apart. Here the VALUES line up with the NAMES (7 targets, 6 values), which is the
    # only shape where the target count is the sole thing standing between a reader and a guess.
    raises("a target the reader drops is refused even when the VALUES line up",
           lambda: defined_codes("OK, mod.X, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, "
                                 "UNREADABLE_PLAN, UNANSWERABLE = 0, 2, 3, 4, 5, 6"),
           CannotRun)
    raises("...and a subscript target is the same shape",
           lambda: defined_codes("OK, D['k'], CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, "
                                 "UNREADABLE_PLAN, UNANSWERABLE = 0, 2, 3, 4, 5, 6, 's'"),
           CannotRun)
    raises("two codes sharing a value are refused — round 5 L4",
           lambda: defined_codes(f"{_TUPLE} = 0, 2, 3, 4, 5, 5"), CannotRun)
    raises("...including when the collision lands on a code with no arm",
           lambda: defined_codes(f"{_TUPLE} = 0, 2, 3, 2, 5, 6"), CannotRun)
    case("...and the REAL matcher at HEAD still reads clean — the control that makes the four "
         "refusals above mean something",
         defined_codes(MATCHER.read_text(encoding="utf-8", errors="replace")),
         {"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3, "BAD_RESPONSE": 4,
          "UNREADABLE_PLAN": 5, "UNANSWERABLE": 6})

    # ── H2's WIRING — ONE end-to-end run of `main` over a tree that is wrong FOUR WAYS ───────
    # ⛔ THIS IS THE CASE CLASS ROUND 5 H2 PROVED WAS MISSING. Every rule above is checked by
    # calling its function directly, and `verdict(…, dead, …)` passed with a dead list while the
    # CALL SITE in `main` had stopped passing one — 43/43 green, live rc=0, clean over a real
    # dead arm. A rule with no wiring case is a rule a refactor can silently detach.
    # ⚠ It costs one full `main()` — 256 concurrent probes — so all four rules share ONE tree.
    def _main_over(hook_src: str, matcher_src: str) -> tuple[int, str]:
        import contextlib
        import io as _io
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scripts").mkdir()
            (root / ".claude" / "hooks").mkdir(parents=True)
            m = root / "scripts" / "recall-llm.py"
            m.write_text(matcher_src)
            h = root / ".claude" / "hooks" / "surface-recall.sh"
            h.write_text(hook_src)
            saved = (globals()["ROOT"], globals()["MATCHER"], globals()["HOOK"])
            globals()["ROOT"], globals()["MATCHER"], globals()["HOOK"] = root, m, h
            try:
                buf = _io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = main([])
                return rc, buf.getvalue()
            finally:
                globals()["ROOT"], globals()["MATCHER"], globals()["HOOK"] = saved

    _WRONG_FOUR_WAYS = _hook(
        '  3) PAYLOAD="stale. Reason: $OUT" ;;\n'              # R3: unguarded, novel label
        '  5) [ -n "$OUT" ] && PAYLOAD="unreadable. Detail: $OUT" ;;\n'  # R4: silent at rc 5
        '  6) PAYLOAD="no corpus." ;;\n'
        '  7) PAYLOAD="dead arm" ;;\n')                        # R2: rc 7 is emitted by nothing
    _rc, _out = _main_over(_WRONG_FOUR_WAYS, RC)               # R1: no `0)` arm, and no row
    case("main refuses a tree that is wrong four ways", _rc, 1)
    case("R1 is WIRED — the missing 0) arm reaches the verdict",
         "rc 0 (OK) is defined" in _out, True)
    case("R2 is WIRED — dead_arms' result is still READ at the call site (round 5 H2)",
         "ACTS on rc 7" in _out, True)

    # ⚠ THE CONTROL STAGES THE REAL HOOK, NOT CANON, AND THE REASON IS THE NEW RULE: `main`
    # consults the module-global DECLARED_RENDER, which approves the SHIPPED sentences. A synthetic
    # fixture renders different text, so R3 would fire on every code and the control would be red
    # for a reason that has nothing to do with wiring. Observed while writing this: rc=1, 6 of 6
    # codes "undeclared". The declaration and the hook are one unit; a control must stage both.
    _rc_ok, _out_ok = _main_over(_read_or_refuse(HOOK), RC)
    case("...and the SAME wiring reports a correct tree as OK — the control", _rc_ok, 0)
    _INERT, _ = _main_over(_hook('  *) : ;;\n'), RC)
    case("an inert hook is NOT RUN, never a pass — and is refused before the 256 probes",
         _INERT, 2)
    # ⚠ `main`'s ONE argv-sensitive branch had no case at all, and argv was `[]` at every call
    # site — so `check-fixture-variation.py` was right that nothing could tell it from a literal.
    # The suite is stubbed out rather than re-entered, because `main(["--self-test"])` for real is
    # unbounded recursion; `main` resolves `_self_test` from module globals at call time.
    # ── R2 MEDIUM — THE PROPERTY THIS GUARD'S OWN SCRUB MUST HOLD (PR #366). The sibling case in
    # `check-surface-recall.py` asserts only that the two allowlists AGREE, which a wrong set held
    # consistently satisfies — and that is how the harness came to claim "no suite the harness
    # spawns may WRITE a cache" over a tree where a scrubbed spawn still did.
    # ⚠ The case lives HERE, not beside its sibling, because `check-plan-code.run_suite` runs only
    # the MUTATED file's suite (:808) — a cross-file case can never be a mutation's `expect`.
    # ⚠ The probe SETS the variable in the source environment instead of reading the caller's, so
    # this verdict cannot depend on how the guard was invoked — backlog #56's shape. It scrubs with
    # the LIVE constant, so severing the key goes red here.
    def _scrubbed_spawn_writes_cache(keys) -> list[str]:
        """-> the `.pyc` names a scrubbed child leaves behind. `[]` is the property holding."""
        with tempfile.TemporaryDirectory() as _td:
            (Path(_td) / "_pyc_probe.py").write_text("VALUE = 1\n")
            _src = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            subprocess.run([sys.executable, "-c", "import _pyc_probe"], timeout=30, check=True,
                           capture_output=True,
                           env={**{k: v for k, v in _src.items() if k in keys},
                                "PYTHONPATH": _td})
            return sorted(q.name for q in (Path(_td) / "__pycache__").glob("*.pyc"))

    case("a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium",
         _scrubbed_spawn_writes_cache(SUBPROCESS_ENV_KEYS), [])

    _saved_st = globals()["_self_test"]
    globals()["_self_test"] = lambda: 99
    try:

        case("main dispatches --self-test to the suite", main(["--self-test"]), 99)
        case("...and an argv WITHOUT it does not reach the suite", main(["--nope"]) != 99, True)
    finally:
        globals()["_self_test"] = _saved_st

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

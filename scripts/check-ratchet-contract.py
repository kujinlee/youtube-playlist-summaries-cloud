#!/usr/bin/env python3
"""Every ratchet obeys the ratchet contract — enforced, not merely written down.

WHY THIS EXISTS. `docs/process-checklists.md` → *Writing a RATCHET* was going to ship as prose
describing a convention that, when measured, only ONE of three ratchets followed. This project's own
roadmap names that failure mode: "of six mechanisms proposed on 2026-07-30, five went unbuilt and the
only thing added was prose." A convention with no enforcement is the seventh.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT — the contract has six rules; two are statically
decidable and those are the two enforced here. Claiming the rest would be the exact defect the gate
work exists to remove.

  R1  a `--self-test` entry point            ENFORCED
  R2  no fail-open exception handler         ENFORCED  (AST: `except:` whose body returns success)
  R3  something EXECUTES it, or `NO-CALLER:`  ENFORCED
  R4  a mutation manifest, or `NO-MUTATIONS:` ENFORCED — R1 asks whether a self-test EXISTS;
      only a mutation asks whether it would NOTICE the guard breaking. Measured 2026-09-05:
      six review passes found four of ~ten vacuous cases; reverting each fix found the rest
      in minutes. Debt baseline 24, MEASURED not estimated.
  --  exit semantics in all three directions NOT CHECKABLE statically — needs the tool run
  --  baseline is a dated named constant     NOT ENFORCED ON PURPOSE. Measured 2026-08-11:
      check-arch-findings.py carries a per-metric `baseline: int` dataclass field, and
      check-guard-coverage.py is a COVERAGE ratchet with no numeric baseline at all. A rule
      demanding a module-level constant would be enforcing one script's SHAPE on two that are
      legitimately different — which is how a conformance check becomes busywork.
  --  scope declared / no repo mutation      prose-level, human judgment

Usage:
    python3 scripts/check-ratchet-contract.py
    python3 scripts/check-ratchet-contract.py --self-test  # 35 cases
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Existing debt, MEASURED 2026-08-11 (not estimated — the first estimate was wrong by half).
# Discovery found SIX ratchets; four predated the contract and had no --self-test:
#   check-arch-findings.py, check-guard-coverage.py, check-sentinel-meanings.py,
#   check-vocabulary-collisions.py
# The prose being enforced originally said "there are three" — written from memory, undercounted by
# half, and this script is what caught it. Ratchet so the NEXT one cannot skip; lower as they gain one.
#
# ⟳ 2026-08-19 — 4 → 0. All four gained a --self-test (task #54), 56 cases, mutation-tested 16/16.
# THE REASON THEY WENT WITHOUT ONE FOR EIGHT DAYS IS WORTH KEEPING: three of the four read the
# catalog through `docker exec … psql`, so their only entry point needed a live Postgres and "give
# it a self-test" read as "stand up a database". It never happened. The fix was not a database —
# it was noticing that the RULE and the FETCH are different things, and only the fetch needed the
# container. Each now has a pure `evaluate()` the cases drive directly.
#
# This is now a HARD FLOOR: at 0, the next ratchet without a --self-test fails immediately.
BASELINE = 0

SELF_TEST_RE = re.compile(r"--self.test", re.IGNORECASE)
RATCHET_DOCSTRING_RE = re.compile(r"\bratchet\b", re.IGNORECASE)
CI_RATCHET_STEP_RE = re.compile(
    r"-\s*name:\s*[^\n]*\bratchet\b[^\n]*\n\s*run:\s*(?:python3\s+)?(\S+)", re.IGNORECASE)


@dataclass
class Violation:
    script: str
    rule: str
    detail: str


def discover_ratchets(ci_yaml: str, script_texts: dict[str, str]) -> list[str]:
    """Ratchet scripts, from TWO independent sources so neither alone can be evaded.

    A registry list would be evadable by simply not registering — the "rule that depends on
    remembering" shape. CI step names cannot be skipped (the step must exist for the check to run
    at all) and a self-described ratchet is caught even before it is wired up."""
    found: list[str] = []
    for m in CI_RATCHET_STEP_RE.finditer(ci_yaml):
        p = m.group(1)
        if p not in found:
            found.append(p)
    for path, text in sorted(script_texts.items()):
        doc = ast.get_docstring(ast.parse(text)) or "" if text.strip() else ""
        if RATCHET_DOCSTRING_RE.search(doc) and path not in found:
            found.append(path)
    return found


def fail_open_handlers(text: str) -> list[int]:
    """Line numbers of `except` handlers that swallow into SUCCESS.

    `return 0` from an exception handler means "I could not run, therefore all is well" — the single
    most expensive rule in the contract. Returning None is NOT flagged: that is the documented way to
    say "unknown" and hand the fail-closed decision to the caller."""
    out: list[int] = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant)):
                continue
            val = sub.value.value
            # ⚠ `type(val) is int`, not `val == 0`. In Python `False == 0`, so the
            # original comparison read a fail-CLOSED predicate (`except ValueError:
            # return False`) as an exit code — a false positive that sat unexposed
            # until the population widened to every guard on disk.
            if type(val) is int and val == 0:
                out.append(sub.lineno)
    return out


GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")
# ⚠ SAME LINE, deliberately: `\s*` would cross the newline and adopt the NEXT
# LINE of the docstring as the written reason, turning the opt-out into a rubber
# stamp for any guard whose docstring happens to continue.
#
# ⟲ CORRECTED. This comment first said `\s*` would "match the closing `\"\"\"`".
# That is FALSE — `ast.get_docstring` strips, so the quotes are never in the text
# it sees, and the mutation SURVIVED the battery against the bare fixture. The
# claim was written from how the source looks, not from what the parser returns.
# `OPTED_OUT_BARE_THEN_PROSE` is the input that makes the distinction real.
# ⛔ SAME TIGHTENING AS R4's ESCAPE, AND FOR THE SAME REASON — review r1 found this one four
# lines above the diff that fixed its sibling. `NO-CALLER:[ \t]*(\S[^\n]*)` matched line 15 of
# this file's own docstring ("or `NO-CALLER:`  ENFORCED"). Fixing R4 and not R3 was
# instance-not-class, in the branch whose subject IS a rule that exempts itself.
NO_CALLER_RE = re.compile(r"NO-CALLER:[ \t]+([A-Za-z][^\n]*)")

# ⛔ THE MARKERS, ASSEMBLED — defined HERE, beside the patterns they mirror, because the first
# fixture that needs them appears long before the escape cases do. Adjacent string literals
# concatenate at compile time, so the runtime values are exact while this source never contains
# either marker followed by a space and a letter. That is the only thing standing between this
# file and granting itself the two opt-outs it exists to police; the `self_exemption` case asserts
# it, because a convention that has already failed twice here is not a mechanism.
_NM = "NO-" "MUTATIONS:"
_NC = "NO-" "CALLER:"


def invocation_re(basename: str) -> re.Pattern[str]:
    """A mention that INVOKES, not a mention that describes.

    `docs/dev-process.md` lists a script in a table headed *What is mechanically
    enforced* and nothing runs it. A substring match would read that table row as
    a caller — which is the very finding this rule exists to catch, so the rule
    must not be satisfiable by prose.
    """
    return re.compile(r"(?:python3?\s+|\./|\bbash\s+|\bsh\s+)(?:\S*/)?" + re.escape(basename))


def discover_guards(script_paths: list[str]) -> list[str]:
    """EVERY guard on disk. The population is the FILESYSTEM.

    ⚠ This replaces the CI-step + self-declaring-docstring discovery. Both
    presupposed the guard was already wired or already labelled itself, so a
    guard nobody runs was invisible to the very inventory built to police guards.
    MEASURED 2026-08-30: 14 of 24 discovered, and the 10 it missed included the
    only two that nothing executes. The old docstring was right that a registry
    is evadable "by simply not registering" — and then chose two populations that
    are evadable the same way. The filesystem cannot be evaded by omission.
    """
    return sorted(p for p in script_paths if GUARD_PATH_RE.fullmatch(p))


def check_caller(path: str, text: str, caller_blob: str) -> list[Violation]:
    """R3 — something executes this guard, or it says in writing why not."""
    try:
        doc = ast.get_docstring(ast.parse(text)) or ""
    except SyntaxError:
        doc = text
    optout = NO_CALLER_RE.search(doc)
    if optout:
        return []
    basename = path.rsplit("/", 1)[-1]
    if invocation_re(basename).search(caller_blob):
        return []
    return [Violation(path, "R3_no_caller",
                      "nothing executes it — wire it into CI, a gate script or a hook, "
                      "or declare `NO-CALLER: <reason>` in its docstring")]


def evaluate(texts: dict[str, str], caller_blob_for: dict[str, str],
             manifest_stems: set[str]) -> list[Violation]:
    """The whole verdict, in one place both `main()` and the suite drive.

    ⚠ EXTRACTED FOR THE WIRING, not for tidiness. With R1/R2/R3 applied inline in
    `main()`, deleting the `check_caller` call would have left every caller case
    green — coverage of the function, none of its use. `check-plan-code.py:704`
    records the same lesson in its own words: "Extracting the function bought
    coverage of the function; the wiring inherited the same blind spot." This is
    that sentence taken seriously.
    """
    out: list[Violation] = []
    for rel in discover_guards(list(texts)):
        out.extend(check_contract(rel, texts[rel]))
        out.extend(check_caller(rel, texts[rel], caller_blob_for.get(rel, "")))
        # ⚠ R3 IS WIRED HERE, for the reason this function's docstring already gives: applied in
        # main() instead, deleting this line would leave every check_manifest case green — coverage
        # of the function, none of its use. `manifest_stems` is REQUIRED, not defaulted, so a caller
        # cannot silently get the vacuous "everything has a manifest" answer.
        out.extend(check_manifest(rel, texts[rel], manifest_stems))
    # ⚠ WIRED HERE FOR THE REASON THIS FUNCTION'S DOCSTRING ALREADY GIVES. Applied in main(),
    # deleting this block would leave every widened-population case green — coverage of the
    # functions, none of their use. Only R4 is applied: R1-R3 were never asked of these files and
    # widening four rules at once would be a different change wearing this one's name.
    _widened = discover_self_tested_nonguards(list(texts), texts)
    _violating = {rel for rel in _widened
                  if check_manifest(rel, texts[rel], manifest_stems)}
    # `set(texts)` is the EXAMINED set, not `_widened`: a pinned script that stopped being
    # self-tested drops out of `_widened` entirely, and its pin would then go stale in silence.
    out.extend(widened_debt_drift(_violating, set(texts)))
    return out


def check_contract(path: str, text: str) -> list[Violation]:
    v: list[Violation] = []
    if not SELF_TEST_RE.search(text):
        v.append(Violation(path, "R1_no_self_test",
                           "no `--self-test` — nothing proves its discriminators are load-bearing"))
    for line in fail_open_handlers(text):
        v.append(Violation(path, "R2_fail_open",
                           f"line {line}: an `except` handler returns 0 — 'could not run' reported as success"))
    return v


# R4 — A MUTATION MANIFEST, OR A WRITTEN REASON.
# (R4, not R3: `R3_no_caller` is taken. Reusing the number would make two different rules
#  indistinguishable in the violation output, which is where a reader looks first.)
#
# WHY THIS RULE EXISTS, and it is the most expensive lesson this project has measured.
# R1 asks whether a guard HAS a self-test. It cannot ask whether that self-test would NOTICE the
# guard breaking. On 2026-09-05, backlog #95 shipped roughly TEN cases that passed with AND without
# the bug they named. SIX adversarial review passes found four of them; reverting each fix and
# watching a named case go red found the rest in MINUTES.
#
# That asymmetry is the whole argument: reading does not find vacuity, and running does. Adding more
# review rounds buys a decaying return on the one defect class that dominates this codebase's
# guards; a manifest converts that recurring per-slice cost into a one-time CI cost.
#
# ⚠ THE ESCAPE IS A WRITTEN REASON, NOT A FLAG — `NO-MUTATIONS: <why>` in the docstring, exactly as
# NO-CALLER works above. A boolean opt-out is a rubber stamp; a sentence has an author and can be
# argued with. Same rule, same shape, deliberately.
# ⛔ THE REASON MUST BEGIN WITH A LETTER, AFTER AT LEAST ONE SPACE — AND THIS GUARD EXEMPTED
# ITSELF FOR AS LONG AS IT HAS EXISTED BECAUSE IT DID NOT. The old pattern was
# `NO-MUTATIONS:[ \t]*(\S[^\n]*)`, and line 16 of THIS file's own docstring reads
# "a mutation manifest, or `NO-MUTATIONS:` ENFORCED — R1 asks whether …". The regex matched it
# and took "` ENFORCED — R1 asks whether a self-test EXISTS;" as the written reason, so the guard
# that demands a manifest from every other guard was never asked for one. Measured 2026-09-12:
# it was the ONLY file affected, across all 34 guards.
#
# ⚠ This is the shape `check-plan-code.py` records for its abandoned pre-flight — `"[FAIL] " in
# source` is unfalsifiable because the comment explaining the contract QUOTES the marker. A rule
# that documents its own escape hatch will match that documentation unless the pattern excludes it.
# `[ \t]+` rejects "NO-MUTATIONS:`" (no space); `[A-Za-z]` rejects "NO-MUTATIONS: <why>".
NO_MUTATIONS_RE = re.compile(r"NO-MUTATIONS:[ \t]+([A-Za-z][^\n]*)")

# MEASURED 2026-09-05, not estimated: 28 guards discovered on disk, 4 carry a manifest
# (check-dashboard-entry, check-plan-code, check-selftest-counts, check-theme-token-coverage),
# so 24 do not. The first estimate for R1's own debt was "three" and the truth was six — written
# from memory, undercounted by half — so this number was produced by running discover_guards
# against scripts/mutations/ rather than by counting by eye.
#
# ⚠ EXACT MATCH, NOT A CEILING. `!=`, not `>`. A ceiling lets the debt be paid down silently and
# then re-accrued back up to the old number, which is how a ratchet stops ratcheting. Paying one
# down FAILS this check until the constant is lowered in the SAME commit — the identity-not-
# cardinality rule that `check-plan-code.EXPECTED_MUTATIONS` already applies to mutation counts.
# ⚠ 23, AND THE NUMBER CAME FROM THE TOOL, NOT FROM A SCRIPT THAT RE-IMPLEMENTED IT. A throwaway
# measurement written alongside this change said 24: it globbed scripts/*.py and applied its own
# idea of the population, and it disagreed with `discover_guards` + `check_manifest` by one. The
# recorded shape is *a second implementation of one rule DRIFTS* — so the baseline is whatever
# `python3 scripts/check-ratchet-contract.py` prints, and nothing else.
MANIFEST_BASELINE = 0


def check_manifest(path: str, text: str, manifest_stems: set[str]) -> list[Violation]:
    """PURE. The manifest SET is passed in, never globbed here.

    ⚠ Separating the RULE from the FETCH is not style. Three ratchets in this repo went eight days
    untestable because their only entry point needed Docker, and "give it a self-test" read as
    "stand up a database". A rule that reads the filesystem inherits the filesystem's availability.
    """
    if Path(path).stem in manifest_stems:
        return []
    if NO_MUTATIONS_RE.search(text):
        return []
    return [Violation(path, "R4_no_mutation_manifest",
                      "no scripts/mutations/<name>.json and no written `NO-MUTATIONS: <why>` — "
                      "its self-test is unproven against the guard actually breaking")]


# ── R4's POPULATION WAS DRAWN BY FILENAME, AND THAT IS THE HOLE ──────────────────────────────
# ⟳ 2026-09-12. R4's RULE was always right; `discover_guards` is `scripts/check-[\w.-]+\.py`, so
# the question "would your suite NOTICE this breaking?" was asked of 34 files because of what they
# are CALLED. 40 of 55 scripts are in scope (34 guards ∪ 22 self-declared ratchets) and R4 is
# green for all of them; EIGHT outside it have a self-test and no manifest.
#
# MEASURED the day PR #293 merged, then RE-measured in review r1, because the first version of
# this comment was wrong twice: it listed FOUR (a scratch measurement that excluded self-declared
# ratchets while the real discovery excludes only guards), and it recorded `m4_catalog.py rc=0` as
# evidence of a working suite. Running all eight:
#
#     explainer-serve.py          88/88
#     codex-review.py             63/63   the adversarial-review gate itself
#     build-m4-schema.py          22/22
#     verify-exclusion-reasons.py 11/11
#     prior-art.py                PASS
#     m4_catalog.py               rc=0 and ZERO BYTES — it ignores the flag; there is no suite
#     gen-m4-manifest.py          rc=1 CANNOT RUN (cannot create its scratch directory)
#     subject_status.py           rc=1 — 16/17, a suite RED on master that nothing runs
#
# ⛔ `m4_catalog.py rc=0` WAS CANNOT-RUN READ AS SUCCESS, inside the evidence for a comment saying
# each was "verified by RUNNING". An exit code cannot tell a passing suite from an ignored
# argument; only the absent output can. That file is in this population by PROSE — the documented
# fail-closed case — and `NO-MUTATIONS:` is the honest escape for it.
#
# `codex-review.py` is the sharpest entry: it decides whether a review gate RAN, and this project
# has measured that gate failing open twice. Its 63 cases have never been asked whether they would
# go red if it broke.
#
# ⚠ THE DISCOVERY IS DELIBERATELY THE SAME `SELF_TEST_RE` R1 USES, prose false-positives and all.
# A second detector would drift from R1's — this repo has measured that seven times — and the
# failure direction here is safe: a script swept in by prose ALONE cannot satisfy R4, so it fails
# CLOSED and names itself, and "the regex matched prose; there is no suite" is a perfectly good
# `NO-MUTATIONS:` reason. A cheap, honest escape beats a cleverer detector.
# ⚠ THIS SET CAME FROM RUNNING THE TOOL, NOT FROM A MEASUREMENT WRITTEN ALONGSIDE IT — the rule
# `MANIFEST_BASELINE` already states in its own words: "the baseline is whatever
# `python3 scripts/check-ratchet-contract.py` prints, and nothing else". The first version of this
# constant listed FOUR, because the scratch measurement that produced it excluded self-declared
# ratchets from the population while `discover_self_tested_nonguards` excludes only GUARDS. Eight
# violate. A second implementation of one rule drifts; it drifted here, in the commit adding the
# rule, and the tool caught it on the first run.
WIDENED_MANIFEST_DEBT: frozenset[str] = frozenset({
    "scripts/build-m4-schema.py",
    "scripts/codex-review.py",
    "scripts/explainer-serve.py",
    "scripts/gen-m4-manifest.py",
    "scripts/m4_catalog.py",
    "scripts/prior-art.py",
    "scripts/subject_status.py",
    "scripts/verify-exclusion-reasons.py",
})


def discover_self_tested_nonguards(script_paths: list[str], texts: dict[str, str]) -> list[str]:
    """Scripts that prove themselves with a `--self-test` but are not NAMED `check-*`. PURE.

    R4 asks whether a suite would notice its subject breaking. Nothing about that question is
    specific to a guard — it is just as live for a 928-line review wrapper — and the only reason
    it was not asked is that the population was a filename pattern.
    """
    guards = set(discover_guards(script_paths))
    return sorted(p for p in script_paths
                  if p not in guards and SELF_TEST_RE.search(texts.get(p, "")))


def widened_debt_drift(violating: set[str], examined: set[str]) -> list[Violation]:
    """PURE. The pinned debt set vs what is actually on disk, BOTH directions.

    ⚠ IDENTITY, NOT CARDINALITY — the same rule `MANIFEST_BASELINE` states for its own count and
    `check-plan-code.EXPECTED_MUTATIONS` applies to mutation counts. A ceiling would let the debt
    be paid down silently and re-accrued back to eight, which is how a ratchet stops ratcheting.
    Paying one down FAILS until the constant is lowered in the SAME commit.

    ⛔ `examined` IS REQUIRED, AND IT IS NOT A CONVENIENCE. A pinned path that was never READ is
    not "paid" — it is NOT EXAMINED, and reporting the first as the second is this project's most
    expensive recorded shape: a corpus that contains none of the subject returning a confident
    verdict. Measured here on the first run: the wiring cases drive `evaluate()` with a synthetic
    two-entry corpus, and without this parameter all eight pinned entries reported as paid. The
    caller must say what it looked at; a default would let a caller get the vacuous answer.
    """
    out: list[Violation] = []
    for path in sorted(violating - WIDENED_MANIFEST_DEBT):
        out.append(Violation(path, "R4W_no_mutation_manifest",
                             "a self-tested script outside the guard population has no "
                             "scripts/mutations/<name>.json and no `NO-MUTATIONS: <why>` — write "
                             "one, or add it to WIDENED_MANIFEST_DEBT with the reason"))
    for path in sorted((WIDENED_MANIFEST_DEBT & examined) - violating):
        out.append(Violation(path, "R4W_debt_paid_not_recorded",
                             "pinned as manifest debt but it no longer violates R4 — it gained a "
                             "manifest, declared `NO-MUTATIONS:`, or stopped being self-tested. "
                             "Remove it from WIDENED_MANIFEST_DEBT in the SAME commit, so the "
                             "debt cannot be re-accrued silently"))
    return out


# ── self-test ────────────────────────────────────────────────────────────────────────────────
SELF_TEST_OK = '''"""A ratchet."""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
NO_SELF_TEST = '''"""A ratchet."""
def main():
    return 0
'''
FAIL_OPEN = '''"""A ratchet with --self-test."""
def main():
    try:
        run()
    except Exception:
        print("could not check")
        return 0
    return 0
'''
RETURNS_NONE = '''"""A ratchet with --self-test."""
def probe():
    try:
        return measure()
    except Exception:
        return None
'''
RETURNS_FALSE = '''"""A ratchet with --self-test."""
def valid_date(s):
    try:
        parse(s)
        return True
    except ValueError:
        return False
'''

# ── R3, and its opt-out ──────────────────────────────────────────────────────────────────────
# A guard nobody executes is the failure this project has recorded FOUR times and
# fixed four times, one instance each: the 2026-07-30 architecture review's finding
# #2 ("a correct module exists and nobody calls it"), and three more in
# `check-schema-gates.sh` comments at :52, :86 and :109. The class-check was never
# built, on an inventory that already globbed every guard.
HAS_CALLER_STUB = '''"""A guard."""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
# ⚠ ASSEMBLED, like the R4 fixtures below and for the same measured reason: a fixture that spells
# the marker out grants THIS file the very opt-out it is testing. `_NC` is defined near the escape
# cases; this f-string keeps the literal out of the source while the runtime value is exact.
OPTED_OUT = f'''"""A guard.

{_NC} run by hand during a schema promotion; wiring it into CI would need a
live Postgres that CI does not have.
"""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
OPTED_OUT_BARE = '''"""A guard.

NO-CALLER:
"""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
# ⚠ THE ONE THAT MAKES `[ \\t]*` LOAD-BEARING. The bare fixture above does NOT:
# `ast.get_docstring` strips, so there is nothing after the colon for `\\s*` to
# swallow and both spellings refuse it. My first comment claimed otherwise and
# the battery caught it — a false equivalence claim, the round-3 shape again.
# HERE the docstring continues, so `\\s*` would cross the newline and adopt the
# NEXT LINE as the written reason. That is the rubber stamp.
OPTED_OUT_BARE_THEN_PROSE = '''"""A guard.

NO-CALLER:
It reads the live catalog, which CI has no credentials for.
"""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''

# (name, script path, script text, the blob of everything that could invoke it, expected rules)
CALLER_CASES: list[tuple[str, str, str, str, list[str]]] = [
    ("a guard named by a CI step has a caller", "scripts/check-a.py", HAS_CALLER_STUB,
     "      - run: python3 scripts/check-a.py\n", []),
    ("a guard invoked from a shell gate has a caller", "scripts/check-b.py", HAS_CALLER_STUB,
     'run "3/15 guard coverage" ./scripts/check-b.py\n', []),
    ("a guard NOTHING executes is a violation", "scripts/check-c.py", HAS_CALLER_STUB,
     "nothing here mentions it\n", ["R3_no_caller"]),
    ("...unless it declares NO-CALLER with a written reason", "scripts/check-d.py", OPTED_OUT,
     "nothing here mentions it\n", []),
    ("a BARE NO-CALLER with no reason is still a violation — the opt-out is not a rubber stamp",
     "scripts/check-e.py", OPTED_OUT_BARE, "nothing here mentions it\n", ["R3_no_caller"]),
    ("...and a bare NO-CALLER cannot adopt the NEXT LINE of the docstring as its reason",
     "scripts/check-e2.py", OPTED_OUT_BARE_THEN_PROSE, "nothing here mentions it\n",
     ["R3_no_caller"]),
    ("a guard mentioned ONLY in prose docs has no caller — docs are not callers",
     "scripts/check-f.py", HAS_CALLER_STUB,
     "| `scripts/check-f.py` | listed in a table under 'mechanically enforced' |\n",
     ["R3_no_caller"]),
]

# The POPULATION is the filesystem. (name, paths on disk, expected)
POPULATION_CASES: list[tuple[str, list[str], list[str]]] = [
    ("every check-*.py on disk is in the population",
     ["scripts/check-a.py", "scripts/check-b.py"], ["scripts/check-a.py", "scripts/check-b.py"]),
    ("a guard wired into NOTHING is still in the population — that is the whole point",
     ["scripts/check-orphan.py"], ["scripts/check-orphan.py"]),
    ("a non-guard script is not in the population",
     ["scripts/gen-dashboard.py", "scripts/check-a.py"], ["scripts/check-a.py"]),
]


# ── R4's WIDENED POPULATION, and its debt drift ──────────────────────────────────────────────
_ST = '"""x"""\nif "--self-test" in sys.argv: pass\n'
_NO_ST = '"""x"""\nprint(1)\n'

# (name, script_paths, texts, expected) — `script_paths` is SEPARATE from `texts.keys()` on
# purpose: they are different arguments and the last case is the one where they disagree.
# ⭐ THE CASE THAT KEEPS THIS FILE HONEST, and the only one that reads its own source.
# Both escapes are opt-outs from rules THIS file enforces. It has now granted itself one of them
# twice — first because the docstring documented it, then because a test fixture demonstrated it —
# so the durable guard is not a cleverer regex but an assertion that the source does not satisfy
# either escape, by ANY route: prose, fixture, or a comment explaining the defect.
# ⚠ Reads the file it is running FROM, so under a staged mutation copy it checks the copy.
def self_exemption() -> tuple[bool, bool]:
    """(exempt-from-R4, exempt-from-R3) for THIS file's own source."""
    own = Path(__file__).read_text(errors="ignore")
    return bool(NO_MUTATIONS_RE.search(own)), bool(NO_CALLER_RE.search(own))


WIDENED_POP_CASES: list[tuple[str, list[str], dict[str, str], list[str]]] = [
    ("a self-tested NON-guard is in the widened population",
     ["scripts/tool.py"], {"scripts/tool.py": _ST}, ["scripts/tool.py"]),
    # ⚠ A GUARD MUST NOT APPEAR HERE. R4 already asks it; counting it twice would charge one file
    # against two baselines and make paying the debt impossible to record in one commit.
    ("a check-* guard is NOT in the widened population",
     ["scripts/check-x.py"], {"scripts/check-x.py": _ST}, []),
    ("a non-guard with no self-test is not asked for a manifest",
     ["scripts/tool.py"], {"scripts/tool.py": _NO_ST}, []),
    # ⭐ THE TWO ARGUMENTS DISAGREE, which is the only case that proves they are two arguments.
    # A path the caller listed but whose text was never read must NOT be assumed self-tested:
    # `texts.get(p, "")` returns empty and the file drops out. Reading an unread file as
    # "has a self-test" would demand a manifest on the strength of never having looked.
    ("a listed path whose text was never read is not assumed self-tested",
     ["scripts/tool.py", "scripts/unread.py"], {"scripts/tool.py": _ST}, ["scripts/tool.py"]),
]

# ── the NO-MUTATIONS escape, and the self-exemption it granted for as long as it existed ─────
# ⛔ THE MARKERS ARE ASSEMBLED AT RUNTIME, NOT WRITTEN AS LITERALS, AND THIS IS THE WHOLE POINT.
# The first version of this fix tightened the regex and then shipped
# the marker spelled out, followed by a plain reason, as a fixture — which the tightened regex
# MATCHES, re-granting this file the exemption it had just removed. Review r1 caught it as
# Blocking, masked only because the file now has a manifest (checked first). Adjacent string
# literals concatenate at compile time, so the runtime value is the marker while the SOURCE never
# contains it. The self-exemption case below is what keeps this true.
ESCAPE_CASES: list[tuple[str, str, bool]] = [
    ("a real written reason exempts", f"{_NM} a pure wrapper, no branches to weaken", True),
    # ⭐ THE CASE THAT WOULD HAVE CAUGHT THE SELF-EXEMPTION. This file's own docstring says
    # "a mutation manifest, or `NO-MUTATIONS:` ENFORCED — …", and the original pattern matched it,
    # taking "` ENFORCED — …" as the reason. The guard demanding manifests was never asked for one.
    ("a guard that only DOCUMENTS the escape is not exempted by it",
     f"  R4  a mutation manifest, or `{_NM}` ENFORCED — R1 asks whether", False),
    ("a placeholder is not a reason", f"`{_NM} <why>` in the docstring", False),
]

WIDENED_DRIFT_CASES: list[tuple[str, set[str], set[str], list[str]]] = [
    ("an UNPINNED violator fails",
     {"scripts/new.py"}, {"scripts/new.py"}, ["R4W_no_mutation_manifest"]),
    ("a pinned violator is silent — that is what the pin is for",
     {"scripts/codex-review.py"}, {"scripts/codex-review.py"}, []),
    ("a pinned entry that was EXAMINED and no longer violates fails",
     set(), {"scripts/codex-review.py"}, ["R4W_debt_paid_not_recorded"]),
    # ⭐ THE CORPUS CASE, and it is the one that caught a real defect on the first run. Absence
    # from the corpus is NOT-EXAMINED, never "paid". Without the `examined` argument the wiring
    # cases below — which drive evaluate() with a two-entry synthetic corpus — reported all eight
    # pinned entries as paid. Deleting the `& examined` clause turns this case red.
    ("a pinned entry NOT examined is silent, not 'paid'",
     set(), set(), []),
]

CASES: list[tuple[str, str, list[str]]] = [
    ("a conforming ratchet has no violations", SELF_TEST_OK, []),
    ("a missing --self-test is flagged", NO_SELF_TEST, ["R1_no_self_test"]),
    ("an except handler returning 0 is flagged", FAIL_OPEN, ["R2_fail_open"]),
    ("returning None from except is NOT flagged — that is fail-closed delegation",
     RETURNS_NONE, []),
    # ⚠ FOUND BY WIDENING THE POPULATION, 2026-08-30. `check-dashboard-entry.py:34`
    # is `except ValueError: return False` — a PREDICATE saying "not a valid date",
    # which is fail-CLOSED. R2 flagged it because in Python `False == 0`, so the
    # constant comparison could not tell an exit code from a boolean. The old
    # narrow population never included this script, so the false positive sat
    # unexposed. `is not False` alone would not do it either — `0 is not False`
    # is True but `0 == 0` still matches; the type is what separates them.
    ("returning False from except is NOT flagged — a predicate is not an exit code",
     RETURNS_FALSE, []),
]

DISCOVERY_CASES: list[tuple[str, str, dict[str, str], list[str]]] = [
    ("a CI step named ...ratchet is discovered",
     "      - name: Gate falsifiability ratchet\n        run: python3 scripts/check-x.py\n",
     {}, ["scripts/check-x.py"]),
    ("a self-described ratchet is discovered even when not wired into CI",
     "", {"scripts/check-y.py": '"""Ratchet: every guard is classified."""\n'}, ["scripts/check-y.py"]),
    ("a non-ratchet script is not discovered",
     "", {"scripts/check-z.py": '"""Plain static check."""\n'}, []),
    ("a script found in BOTH sources is listed once",
     "      - name: X ratchet\n        run: python3 scripts/check-y.py\n",
     {"scripts/check-y.py": '"""Ratchet."""\n'}, ["scripts/check-y.py"]),
]


def self_test() -> int:
    failures = 0
    for name, text, expected in CASES:
        got = sorted({v.rule for v in check_contract("t.py", text)})
        if got != sorted(expected):
            # ⛔ `[FAIL] <name>`, NAME ALONE ON THE LINE — a contract with the mutation
            # harness, not a display choice. `check-plan-code.parse_fail_names` reads a red case
            # with `startswith("[FAIL] ")` then `[7:]`; this file printed `  FAIL {name}`, which
            # it cannot see at all, so every mutation aimed here would be KILLED and
            # UNATTRIBUTED — "matched 0 red case(s)" while each one dies by the case it names.
            # ⟳ 2026-09-12: fixed here the same day PR #293 paid it for `gen-goals-page.py` and
            # wrote "the tenth is only a matter of time" in its own body. This is the tenth.
            print(f"[FAIL] {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1
    for name, ci, scripts, expected in DISCOVERY_CASES:
        got = discover_ratchets(ci, scripts)
        if got != expected:
            print(f"[FAIL] {name}\n       expected {expected}\n       got      {got}")
            failures += 1
    for name, path, text, blob, expected in CALLER_CASES:
        got = sorted({v.rule for v in check_caller(path, text, blob)})
        if got != sorted(expected):
            print(f"[FAIL] {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1
    for name, paths, expected in POPULATION_CASES:
        got = discover_guards(paths)
        if got != expected:
            print(f"[FAIL] {name}\n       expected {expected}\n       got      {got}")
            failures += 1
    for name, paths_, texts_, expected in WIDENED_POP_CASES:
        got = discover_self_tested_nonguards(paths_, texts_)
        if got != expected:
            print(f"[FAIL] {name}\n       expected {expected}\n       got      {got}")
            failures += 1
    _r4x, _r3x = self_exemption()
    if (_r4x, _r3x) != (False, False):
        print(f"[FAIL] this file does not exempt ITSELF from either escape\n"
              f"       expected (False, False)\n       got      {(_r4x, _r3x)}")
        failures += 1
    for name, text_, want in ESCAPE_CASES:
        got = bool(NO_MUTATIONS_RE.search(text_))
        if got != want:
            print(f"[FAIL] {name}\n       expected {want}\n       got      {got}")
            failures += 1
    for name, violating, examined, expected in WIDENED_DRIFT_CASES:
        got = sorted({v.rule for v in widened_debt_drift(violating, examined)})
        if got != sorted(expected):
            print(f"[FAIL] {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1

    # ⚠ THE WIRING, not the helpers. Every case above drives a function directly;
    # none would notice if `evaluate` stopped calling one. These two drive the
    # whole verdict, so removing either arm turns them red.
    wiring = [
        ("evaluate APPLIES the caller rule, not just defines it",
         {"scripts/check-w.py": HAS_CALLER_STUB}, {"scripts/check-w.py": "nothing"},
         ["R3_no_caller", "R4_no_mutation_manifest"]),
        # ⚠ THE WIRING CASE FOR R4. Without it, deleting the check_manifest call from evaluate()
        # leaves every check_manifest case green — the exact blind spot this list exists for.
        ("evaluate APPLIES the manifest rule, not just defines it",
         {"scripts/check-w.py": SELF_TEST_OK},
         {"scripts/check-w.py": "python3 scripts/check-w.py"},
         ["R4_no_mutation_manifest"]),
        # ⚠ THE WIRING CASE FOR THE WIDENED R4. Without it, deleting the
        # discover_self_tested_nonguards/widened_debt_drift block from evaluate() leaves every
        # case above green — coverage of the functions, none of their use. This is the same
        # blind spot this list's own header describes, one rule later.
        ("evaluate APPLIES the widened manifest rule to a NON-guard",
         {"scripts/check-w.py": SELF_TEST_OK, "scripts/tool.py": SELF_TEST_OK},
         {"scripts/check-w.py": "python3 scripts/check-w.py"},
         ["R4W_no_mutation_manifest", "R4_no_mutation_manifest"]),
        ("evaluate APPLIES the self-test rule too",
         {"scripts/check-w.py": NO_SELF_TEST}, {"scripts/check-w.py": "python3 scripts/check-w.py"},
         ["R1_no_self_test", "R4_no_mutation_manifest"]),
    ]
    # Empty on purpose: the stub guards have no manifest, so R4 fires unless a case opts out.
    manifests: set[str] = set()
    for name, texts, blobs, expected in wiring:
        got = sorted({v.rule for v in evaluate(texts, blobs, manifests)})
        if got != sorted(expected):
            print(f"[FAIL] {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1

    total = (len(CASES) + len(DISCOVERY_CASES) + len(CALLER_CASES)
             + len(POPULATION_CASES) + len(WIDENED_POP_CASES)
             + len(ESCAPE_CASES) + len(WIDENED_DRIFT_CASES) + len(wiring) + 1)
    print(f"self-test: {total - failures}/{total} passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    ci_path = ROOT / ".github/workflows/ci.yml"
    if not ci_path.exists():
        print("FAILED: .github/workflows/ci.yml not found — ratchets could not be discovered.")
        print("Treat this as NOT RUN.")
        return 1

    # ⟳ 2026-09-12: `check-*.py` -> `*.py`. The guard rules are UNCHANGED — `discover_guards`
    # still filters by GUARD_PATH_RE, so `evaluate()`'s R1-R3 loop sees exactly the same 34 files.
    # What the narrower glob did was make R4's WIDENED population unreachable: the discovery could
    # only ever see what main() had read, so `discover_self_tested_nonguards` returned [] and all
    # four pinned debt entries reported as PAID. The rule was right and the corpus was empty —
    # measured, on the first run, which is why the debt is pinned by IDENTITY: a cardinality
    # ceiling would have read an empty corpus as "no violations" and passed.
    texts = {}
    for p in sorted((ROOT / "scripts").glob("*.py")):
        rel = str(p.relative_to(ROOT))
        try:
            texts[rel] = p.read_text(errors="ignore")
        except OSError:
            print(f"FAILED: could not read {rel} — treat this as NOT RUN.")
            return 1

    ratchets = discover_guards(list(texts))
    if not ratchets:
        # Zero means discovery broke, not that all is well. (No count is quoted here on
        # purpose: the population moves, and a stored figure is stale at the commit that adds it.)
        print("FAILED: discovered ZERO guards, which cannot be right. Treat this as NOT RUN.")
        return 1

    # ── WHAT COUNTS AS A CALLER ──────────────────────────────────────────────
    # Executable sources only. `docs/` is deliberately absent: a row in a table
    # headed "What is mechanically enforced" is a CLAIM about a caller, not one,
    # and reading it as a caller is the exact defect R3 exists to catch.
    caller_sources: list[Path] = [ci_path]
    caller_sources += sorted((ROOT / "scripts").glob("*.sh"))
    caller_sources += sorted((ROOT / ".claude" / "hooks").glob("*"))
    caller_sources += sorted((ROOT / "scripts").glob("*.py"))
    if len(caller_sources) < 3:
        print("FAILED: found almost no executable sources to search for callers. NOT RUN.")
        return 1

    blob_for: dict[str, str] = {}
    for rel in ratchets:
        # ⚠ A guard's OWN text is excluded. Every one of these scripts names
        # itself in its usage docstring, so including it would let each guard
        # satisfy R3 by describing how to run it — measured on
        # check-producer-enumeration.py, whose only three mentions anywhere in
        # the repo are its own docstring and its own print().
        blob_for[rel] = "\n".join(
            p.read_text(errors="ignore") for p in caller_sources
            if p.is_file() and str(p.relative_to(ROOT)) != rel)

    # THE FETCH, kept out of the rule: check_manifest is pure and takes this set.
    manifest_stems = {q.stem for q in (ROOT / 'scripts/mutations').glob('*.json')}
    violations = evaluate(texts, blob_for, manifest_stems)

    print(f"guards discovered ({len(ratchets)}): " + ", ".join(ratchets))
    if not violations:
        print("ratchet contract OK")
        return 0

    for v in violations:
        print(f"  {v.script}  [{v.rule}]\n      → {v.detail}")
    print(f"\nsummary: {len(violations)} violation(s), baseline {BASELINE}")

    # R4 has its own baseline: the manifest debt is 24 guards deep and is paid down
    # separately from R1/R2/R3. Counting them in ONE number would let a new fail-open
    # handler hide behind a manifest that got written the same week.
    manifest_v = [v for v in violations if v.rule == "R4_no_mutation_manifest"]
    other_v = [v for v in violations if v.rule != "R4_no_mutation_manifest"]
    print(f"  (of which {len(manifest_v)} are R4 manifest debt, baseline {MANIFEST_BASELINE})")

    if len(manifest_v) != MANIFEST_BASELINE:
        verb = "GREW" if len(manifest_v) > MANIFEST_BASELINE else "SHRANK"
        print(f"RATCHET FAILED: R4 manifest debt {verb} — {len(manifest_v)} vs baseline "
              f"{MANIFEST_BASELINE}. Set MANIFEST_BASELINE to {len(manifest_v)} in THIS commit; "
              f"an exact match is what stops paid-down debt being silently re-accrued.")
        return 1

    if len(other_v) > BASELINE:
        print("RATCHET FAILED: a ratchet was added or changed without following the contract.")
        print("See docs/process-checklists.md → Writing a RATCHET.")
        return 1
    if len(other_v) < BASELINE:
        print(f"Only {len(other_v)} remain — LOWER THE BASELINE to lock the gain in.")
    else:
        print("at baseline — not growing.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

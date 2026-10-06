#!/usr/bin/env python3
"""The hook's OWN guard: what `.claude/hooks/surface-recall.sh` shows a reader is what a human approved.

⛔ THIS FILE EXISTS BECAUSE THE HOOK HAD NOTHING. Backlog #196, measured 2026-09-30: mutation
manifests naming the hook — NONE; self-test cases driving it end to end — ZERO. `GUARD_PATH_RE` in
`check-ratchet-contract.py` is `scripts/check-[\\w.-]+\\.py`, so a `.sh` caller inherits no rule at
all, and THAT is why both live defects (#201, #202) survived 188 green cases on the python side.

⭐ IT RUNS THE REAL HOOK, IN THE REAL REPO, and substitutes only the matcher — through the one
ARGV seam at `surface-recall.sh:42`. Round 7 B2 is why: `check-rc-contract.py` observed
the hook by staging a MINIMAL tree, a staged tree is a PROXY FOR THE REPO, and the set of things a
shell script can read is open. Reproduced — an arm branching on `$REPO_ROOT/.claude/settings.json`
rendered a dangling `Detail:` in the real repo while the guard reported CLEAN. There is no
fabricated world here to be unfaithful.

FAILS IF
--------
  * the hook renders anything but the DECLARED sentence for a code, with no detail available;
  * a code the matcher defines has no declared sentence, or vice versa;
  * the hook writes to STDERR -> exit 2, CANNOT RUN, never a pass (round 6 H1: the hook is
    `set -uo pipefail` with no `-e` and `exit 0`s by design, so a fatal error inside an arm is
    INVISIBLE in its exit status — measured, a misspelled tool forwarded a hollow promise at every
    firing while four separate rules reported clean);
  * the hook is missing, unreadable, or prints something that is not its documented envelope.

Usage:
    python3 scripts/check-surface-recall.py
    python3 scripts/check-surface-recall.py --self-test  # 59 cases
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "surface-recall.sh"
MATCHER = ROOT / "scripts" / "recall-llm.py"
TIMEOUT = 30.0

# ⛔ ONE ALLOWLIST, NAMED — ROUND 8 H1. The scrub was hand-copied into `check-rc-contract.observe`
# with nothing comparing the two, so the fix for a DRIFT defect was itself a second copy. A shared
# module would be heavier than the problem; a case that REFUSES a divergence is the remedy this
# repo uses where one place is impractical, and there is one below.
# ⛔ `PYTHONDONTWRITEBYTECODE` IS LOAD-BEARING AND WAS MISSING — ROUND 2 MEDIUM (PR #366).
# The scrub above is an ALLOW-LIST, so it dropped the one variable the mutation harness sets
# to keep bytecode caches impossible while it measures. Reproduced at `77316edc`: a scrubbed
# child importing a module wrote `__pycache__/*.pyc` with the parent holding the variable.
# ⚠ The sibling case below asserted only that the two copies AGREE, which a wrong set held
# consistently satisfies — so the PROPERTY ("a scrubbed spawn writes no cache") is asserted
# directly now, over each file's own constant, and is what the mutation entries name.
SUBPROCESS_ENV_KEYS = (
    "PATH", "HOME", "TMPDIR", "LANG",
    "PYTHONDONTWRITEBYTECODE",
)

# The name this file's fixtures carry, and the name `check-ratchet-contract` excludes from caller
# evidence. One convention, two files; the case below refuses a divergence — round 8 M2.
FIXTURE_PREFIX = "_selftest-"


class CannotRun(Exception):
    """The question could not be ASKED. Never a pass — this repo's rule, and this file's own."""


# ⭐⭐ WHAT THE READER MUST SEE WHEN THERE IS NO DETAIL. Moved here from `check-rc-contract.py`
# 2026-10-01, because its subject is the HOOK'S RENDERED TEXT and not the cross-file contract — the
# reason four rounds of findings landed on it while R1/R2 produced none.
#
# ⛔ IT REPLACED FOUR PROXIES, AND THE HISTORY IS THE ARGUMENT. #201 is a SEMANTIC property — "this
# sentence promises a detail it does not have" — and every mechanical proxy for it had a boundary a
# later round found: adjacency to a literal `Detail:` (r3 M4); a two-entry LABEL vocabulary, beaten
# by `Reason:` and by `Details:` (r5 H1); "the text PRECEDING $OUT", beaten by `$OUT.`, `[$OUT]` and
# text on both sides (r6 B1); "the surround SURVIVES the detail's deletion", beaten the same day by
# renders differing for a NON-detail reason — a truncation below the probe's own length, a
# transforming `$( … )`, a fatal error read as silence, an else-branch differing by ONE interior
# character. Measured over one eleven-arm corpus: the label vocabulary caught 5 of 11, the render
# comparison that replaced it caught 3 — FEWER — and this equality catches 11.
#
# ⭐ SO IT STOPS ASKING THE SEMANTIC QUESTION. Not "is this a promise?" but "is this the sentence a
# human approved?" — which has a definite answer and needs no vocabulary. The judgement moved to a
# reader, ONCE, in a diff: the only authority a question about meaning has.
#
# ⛔⛔ EVERY STRING IS TYPED BY HAND AFTER READING IT. DO NOT GENERATE THEM FROM THE HOOK. Deriving
# them records whatever the hook currently does, a bug included, and the gate passes forever over
# it. That is the one way to make this file worthless and it is the quicker path, so it is the one
# someone will take.
#
# ⚠ WHAT THIS DOES NOT DO: it detects DRIFT, not BADNESS. Edit a message, update the string here in
# the same commit, and the gate passes saying nothing about whether the NEW sentence is good. The
# protection is that both sentences appear in a PR diff where a reader judges again. That is weaker
# than a mechanical check and is the honest price of asking a machine a question it can answer.
#
# ⚠ THE NEWLINES ARE REAL: the hook wraps two payloads across source lines and the reader receives
# the newline. A declared string without it is a transcription error, and this guard will say so.
#
# Each entry read and judged 2026-10-01:
#   0  the whole payload is `[ -n "$OUT" ]`-guarded, so no matches means no message. Correct.
#      ⚠ ROUND 8 L1 — THE JUSTIFICATION WAS INCOMPLETE, and the omission is the interesting half:
#      rc 0 has a SECOND producer. `recall-llm.py:1133-1134` returns OK for a PAUSED thread, not
#      only for "nothing matched" — so this declaration approves silence for two different
#      situations, and only one of them was considered when it was approved. The silence is still
#      judged correct for both (a paused thread is a deliberate state the reader chose), but the
#      reasoning now covers what it actually governs. ⤳ If that judgement is ever revisited it is
#      the same question as backlog #211 for rc 3: one declared slot, more than one meaning.
#   2  no arm; the silent catch-all. Declared unhandled with a reason in `check-rc-contract.py`.
#   3  the ENTIRE payload is guarded, not merely the detail, so a stale-cache note with nothing
#      to report renders nothing.
#      ⛔ ROUND 7 H3 — THIS ENTRY'S FIRST JUSTIFICATION NAMED THE WRONG MECHANISM, and the
#      correction matters because it weakens the judgement rather than supporting it. It said the
#      silence avoids "nagging for the same step". `do_fire`'s dedupe key is the MESSAGE, not
#      (plan, step) — the matcher says so itself: *"its key is the MESSAGE rather than
#      (plan, step)"* — and both stale-cache producers build step-INDEPENDENT text. So a stale
#      cache speaks ONCE and is then silent for the plan's whole remaining life, which is not
#      "quiet instead of nagging" at all.
#      ⚠ THAT MAKES THIS DECLARATION A LIVE DESIGN QUESTION RATHER THAN A SETTLED ONE: it is
#      arguably #202's conflation — an armed plan whose cache is stale, reaching the reader as
#      silence — and the rc 5 entry below argues the OPPOSITE for the same situation. Filed as
#      backlog #211. Declared as the hook behaves TODAY, deliberately: changing it is a product
#      decision about what a reader should see, not a guard decision, and this file's job is to
#      make the current behaviour visible rather than to change it silently.
#   4  no arm; as rc 2.
#   5  the static sentence alone. Ends in a full stop, makes a whole claim, promises nothing.
#   6  as rc 5, plus the clause separating a missing corpus from a bad plan. Complete.
DECLARED_RENDER: dict[int, str] = {
    0: "",
    2: "",
    3: "",
    4: "",
    5: "recall-llm: a plan IS armed and the matcher cannot read it, so NO memory entry was\n"
       "surfaced for this step — this is not 'nothing applies'.",
    6: "recall-llm: a plan IS armed and the memory corpus cannot be reached, so NO memory\n"
       "entry was surfaced for this step — this is not 'nothing applies'. The plan is fine; "
       "the corpus is\nmissing.",
}

# ⛔ THE SECOND POLARITY — ROUND 8 H3. `DECLARED_RENDER` approves what the reader sees when there
# is NO detail, and nothing approved what they see when there IS one. Measured: keep the `-n` guard
# and TRUNCATE — `[ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: ${OUT:0:16}"` — and the reader gets a
# chopped detail while both suites stayed green, because the only with-detail assertions were an
# `endswith("Detail: WIDGET")` over six characters and a 22-character `startswith`. A suffix proxy
# and a prefix proxy: exactly the shape this file's thesis rejects, inside the rule that replaced
# it. This is #209's single-polarity gap, present in its own successor.
# ⚠ `{detail}` is the ONLY placeholder, and the template is typed by hand like its sibling.
DECLARED_WITH_DETAIL: dict[int, str] = {
    0: "{detail}",
    3: "recall-llm: the recall cache for this plan is absent or stale, so no memory entry was\n"
       "surfaced for this step. Run `python3 scripts/recall-llm.py --arm` to match this plan's "
       "steps\n(one model call, ~16s, covers every step). Detail: {detail}",
    5: DECLARED_RENDER[5] + " Detail: {detail}",
    6: DECLARED_RENDER[6] + " Detail: {detail}",
}

_STUB = ("import os, sys\n"
         "sys.stdout.write(os.environ.get('STUB_OUT', ''))\n"
         "sys.exit(int(os.environ.get('STUB_RC', '0')))\n")


def _render_once(target: Path, rc: int, out: str, scrub: bool) -> str:
    """ONE observation of the hook. `scrub=False` passes the AMBIENT environment through."""
    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "stub_matcher.py"
        stub.write_text(_STUB, encoding="utf-8")
        env = ({k: v for k, v in os.environ.items() if k in SUBPROCESS_ENV_KEYS} if scrub
               else dict(os.environ))
        env.update(STUB_RC=str(rc), STUB_OUT=out)
        try:
            # ⛔ THE MATCHER ARRIVES AS ARGV, NOT AS AN ENV VAR — round 7 M1. An env var is
            # AMBIENT: anything in the session could set it and nothing in a diff would show it.
            # `settings.json:57` passes no argument, so this override is reachable only by a
            # deliberate caller.
            proc = subprocess.run(["bash", str(target), str(stub)], capture_output=True,
                                  text=True, timeout=TIMEOUT, cwd=str(ROOT), env=env)
        except FileNotFoundError as exc:
            raise CannotRun("bash is not on PATH, so the hook cannot be run") from exc
        except subprocess.TimeoutExpired as exc:
            raise CannotRun(f"the hook did not finish in {TIMEOUT}s at rc {rc}") from exc
    if proc.stderr.strip():
        raise CannotRun(
            f"the hook wrote to STDERR at rc {rc}, which it cannot report through its exit "
            f"status: {proc.stderr.strip()[:200]!r}. Round 6 H1 — treat this as NOT RUN."
        )
    if proc.returncode != 0:
        raise CannotRun(f"the hook exited {proc.returncode} at rc {rc}; it exits 0 by design")
    body = proc.stdout.strip()
    if not body:
        return ""
    try:
        doc = json.loads(body)
        return doc["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError) as exc:
        raise CannotRun(
            f"the hook printed something that is not its documented envelope at rc {rc} "
            f"({body[:120]!r}) — silence and malformed output must stay distinguishable"
        ) from exc


def render(rc: int, out: str, hook: Path | None = None) -> str:
    """-> what the hook FORWARDS when the matcher exits `rc` printing `out`. The real hook, here.

    ⛔ TWO OBSERVATIONS — ROUND 8 H2, AND THE SCRUB I ADDED IS WHAT CREATED THE NEED. Scrubbing the
    environment fixed round 7 L1 (an ambient `PYTHONVERBOSE` turned the gate into a refusal) and in
    doing so made the ENVIRONMENT a staged proxy — round 7 B2 one dimension over. Reproduced by the
    round-8 reviewer: an arm `if [ -n "${USER:-}" ]; then PAYLOAD="$PAYLOAD Detail: $OUT"; fi`
    renders a dangling `Detail:` for a real reader while this guard returned [] — #201 verbatim, and
    this docstring's old claim of "no fabricated world here to be unfaithful" was false in exactly
    the dimension the hook's own comment enumerates.

    ⭐ THE SCRUBBED RUN STILL DECIDES THE VERDICT, which is what preserves L1. The ambient run is
    advisory: if it RAISES we ignore it (that is L1's own protection, and ambient noise is why the
    scrub exists), and if it SUCCEEDS and DISAGREES, the disagreement IS the finding — what the
    reader sees then depends on something no declaration can approve.

    ⛔ STDERR IS A REFUSAL — round 6 H1. The hook cannot report a fatal error through its exit
    status (`set -uo pipefail`, no `-e`, `exit 0` by design), so a misspelled tool inside an arm
    looked exactly like a clean run. Measured on the shipped hook: 12 of 12 invocations across six
    codes write EMPTY stderr, so refusing on any stderr costs nothing.
    """
    target = HOOK if hook is None else hook
    if not target.is_file():
        raise CannotRun(f"{target} is not a file, so the hook cannot be run at all")
    scrubbed = _render_once(target, rc, out, scrub=True)
    try:
        ambient = _render_once(target, rc, out, scrub=False)
    except CannotRun:
        return scrubbed
    if ambient != scrubbed:
        raise CannotRun(
            f"at rc {rc} the hook renders DIFFERENTLY under the ambient environment than under a "
            f"scrubbed one, so what a reader sees depends on something no declaration can "
            f"approve.\n      scrubbed: {scrubbed!r}\n      ambient : {ambient!r}\n"
            f"      Round 8 H2 — treat this as NOT RUN."
        )
    return scrubbed


def undeclared_detail(declared: dict[int, str],
                      hook: Path | None = None) -> list[tuple[int, str, str]]:
    """-> (code, rendered, declared) for every code whose WITH-DETAIL render is not approved.

    Round 8 H3. The same equality as `undeclared_render`, on the other polarity. A code with no
    with-detail template is SKIPPED here rather than refused — rc 2 and rc 4 have no arm at all, so
    there is nothing for a detail to appear in.
    """
    bad = []
    probe = "A-DETAIL-THAT-IS-LONG-ENOUGH-TO-TRUNCATE"
    for rc in sorted(declared):
        got = render(rc, probe, hook=hook).rstrip()
        want = declared[rc].replace("{detail}", probe).rstrip()
        if got != want:
            bad.append((rc, got, want))
    return bad


def undeclared_render(declared: dict[int, str],
                      hook: Path | None = None) -> list[tuple[int, str, str]]:
    """-> (code, rendered, declared) for every code whose render is not the approved sentence."""
    bad = []
    for rc in sorted(declared):
        got = render(rc, "", hook=hook).rstrip()
        want = declared[rc].rstrip()
        if got != want:
            bad.append((rc, got, want))
    return bad


# ⛔ ROUND 7 H1 — THE ONE PROPERTY THE RELOCATION LOST, AND IT IS THE PROPERTY #201 NAMES.
# The equality asks whether the hook renders the APPROVED sentence. It cannot ask whether the
# approved sentence is any good — so #201's own literal arm (an unconditional `Detail: $OUT`),
# with its render DECLARED here, passes. Measured by the round-7 reviewer: the new guard returns
# [] on exactly that, while HEAD's `dangling_detail` predicate on the same payload returns True.
# ⭐ AND THE VOCABULARY IS SAFE HERE WHERE IT WAS NOT SAFE THERE. That distinction is the whole
# reason this is not a fifth proxy. Applied to arbitrary SHELL RENDERS the label list was an OPEN
# set, and four rounds each found its boundary. Applied to SIX HAND-WRITTEN LITERALS it is a net
# over a CLOSED, reviewed set: if it misses a spelling the cost is that one careless declaration
# edit goes unflagged — not that the rule is wrong. It is a second line, never the rule, and the
# rule is the equality below.
_DANGLING_LABELS = ("Detail:", "detail:", "Details:", "details:", "Reason:", "reason:")

# ⭐ AND A TEST THAT NEEDS NO VOCABULARY AT ALL — ROUND 8 M3, which refuted the argument above.
# The claim was that a label list is safe over a CLOSED hand-reviewed set of six. Measured by the
# reviewer: 10 of 11 plausible dangling declarations ESCAPE the six spellings. A sentence that ends
# in a connector promises continuation whatever word precedes it, and this catches all 10 while
# passing every shipped declaration (four are empty, two end in a full stop — derived, not assumed).
# ⚠ It is still an enumeration, of PUNCTUATION rather than English, and that is a smaller and far
# more stable set — but the honest framing is "a better net", not "closed".
_DANGLING_TERMINATORS = (":", "-", "—", ";", ",")


def declaration_dangles(declared: dict[int, str]) -> list[tuple[int, str]]:
    """PURE. -> (code, label) for every DECLARED sentence that is itself a dangling promise."""
    out = []
    for rc in sorted(declared):
        hit = None
        for label in _DANGLING_LABELS:
            _, sep, tail = declared[rc].partition(label)
            if sep and not tail.strip():
                hit = label
                break
        if hit is None:
            end = declared[rc].rstrip()[-1:]
            if end in _DANGLING_TERMINATORS:
                hit = end
        if hit is not None:
            out.append((rc, hit))
    return out


def _defined_codes() -> dict[str, int]:
    """The matcher's rc tuple, read by the ONE reader that owns it.

    ⛔ IMPORTED, NEVER RE-DERIVED. `check-rc-contract.defined_codes` parses it from the AST and
    refuses anything it cannot pair; a second copy of that rule here would drift, which is this
    repository's most-measured failure. `spec_from_file_location` is the established idiom —
    `begin-plan.py`, `check-closing-table.py`, `check-merge-ready.py` and `check-memory-link.py`
    all load a sibling this way.
    """
    src = ROOT / "scripts" / "check-rc-contract.py"
    spec = importlib.util.spec_from_file_location("_rc_contract_for_hook", src)
    if spec is None or spec.loader is None:
        raise CannotRun(f"{src.name} could not be loaded, so the defined codes cannot be read")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_rc_contract_for_hook"] = mod
    try:
        # ⛔ `BaseException`, AND ROUND 7 M3 IS WHY. A sibling reaching `SystemExit(0)` at module
        # level made this exit 0 with ZERO BYTES — a fail-open in the one import this file depends
        # on. Measured: `SystemExit(0)` -> rc=0 silent; unparseable -> rc=1 plus a raw traceback;
        # `SystemExit(7)` -> rc=7. Three of four missed the documented rc=2.
        spec.loader.exec_module(mod)
    except BaseException as exc:  # noqa: BLE001 - SystemExit is the whole point
        raise CannotRun(
            f"{src.name} could not be executed to read the defined codes "
            f"({exc.__class__.__name__}: {exc}). NOT RUN."
        ) from exc
    try:
        return mod.defined_codes(MATCHER.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        raise CannotRun(f"{MATCHER.name} cannot be read ({exc.__class__.__name__})") from exc
    except mod.CannotRun as exc:
        raise CannotRun(str(exc)) from exc


def coverage(defined: dict[str, int], declared: dict[int, str]) -> list[str]:
    """PURE. -> problems when the declared set and the matcher's set are not the SAME set.

    This is the one cross-file question this file asks, and it is here rather than in
    `check-rc-contract.py` so the dependency runs ONE WAY: this file imports that one, never back.
    """
    problems = []
    for code in sorted(set(defined.values()) - set(declared)):
        name = next(n for n, c in defined.items() if c == code)
        problems.append(
            f"rc {code} ({name}) is defined by the matcher and has NO declared reader sentence, so "
            f"nobody has approved what a reader sees when it fires with no detail."
        )
    for code in sorted(set(declared) - set(defined.values())):
        problems.append(
            f"rc {code} has a declared reader sentence and no matcher constant defines it — a "
            f"declaration for a code that cannot happen, which reads as coverage and is not."
        )
    return problems


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    try:
        defined = _defined_codes()
        problems = coverage(defined, DECLARED_RENDER)
        for code, label in declaration_dangles(DECLARED_RENDER):
            problems.append(
                f"the DECLARED sentence for rc {code} is itself a dangling promise — it ends with "
                f"{label!r} and nothing after it. Approving that text approves backlog #201. The "
                f"equality below cannot see this, because it only asks whether the hook renders "
                f"what was approved — round 7 H1."
            )
        bad = undeclared_render(DECLARED_RENDER)
        bad += undeclared_detail(DECLARED_WITH_DETAIL)
    except CannotRun as exc:
        print(f"FAILED: {exc}. Treat this as NOT RUN.")
        return 2
    for code, got, want in bad:
        problems.append(
            f"at rc {code} the hook does NOT render the sentence DECLARED_RENDER approves when the "
            f"matcher printed no detail.\n"
            f"      declared: {want!r}\n"
            f"      rendered: {got!r}\n"
            f"      If the new sentence is the intended one, update DECLARED_RENDER BY HAND after "
            f"reading it; the diff is where the judgement belongs."
        )
    print(f"surface-recall: {len(DECLARED_RENDER)} declared sentence(s), run against the REAL hook "
          f"in the REAL repo")
    if problems:
        print(f"FAILED — {len(problems)} problem(s):")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print("surface-recall OK — every declared code renders exactly its approved sentence")
    return 0


# ─────────────────────────────────────────────────────────────────── the suite
import contextlib  # noqa: E402 - suite-only imports, kept next to the suite that needs them
import hashlib     # noqa: E402
import os as _os   # noqa: E402


@contextlib.contextmanager
def _fixture_hook(text: str):
    """A fixture hook AT A REAL REPO PATH, removed afterwards.

    ⛔ IT MUST LIVE IN THE REPO, AND THAT IS THE WHOLE POINT OF THIS FILE. The hook derives
    `REPO_ROOT` from `${BASH_SOURCE[0]}`, so a fixture in /tmp sees a repo that does not exist and
    an arm reading `$REPO_ROOT/.claude/settings.json` would take the wrong branch — reproducing
    round 7 B2 inside the very suite built to prevent it. The last case below proves no fixture
    survives, and `check-rc-contract.py`'s own rounds established that a guard which edits the repo
    corrupts its peers, so the name carries the pid and the removal is in a `finally`.
    """
    # ⚠ THE PREFIX IS A CONVENTION HELD IN TWO FILES — round 8 M2. `check-ratchet-contract`
    # excludes it from caller evidence, and a consistent rename here would silently restore round 8
    # H1's false green. A case below reconciles the two. ⛔ The reviewer's derived alternative —
    # "caller evidence must be git-TRACKED" — was MEASURED AND REJECTED: the mutation harness
    # stages a COPY with no `.git`, so `git ls-files` returns nothing there and the rule would
    # exclude every hook, making R3 vacuous for all 43 guards. See backlog #215.
    path = HOOK.parent / f"{FIXTURE_PREFIX}{_os.getpid()}.sh"
    # ⛔ THE FIXTURE OWNS THE REPO FILE ITS ARM MAY BRANCH ON, AND THE FIRST VERSION DID NOT.
    # The round-7 B2 corpus arm below branched on `.claude/settings.json` — a file that happens to
    # exist in the real repo. `check-plan-code`'s HARNESS_TREE stages `.claude/hooks` and NOT
    # `.claude/settings.json`, so inside the mutation harness's staged copy the arm took its else
    # branch, rendered the approved sentence, and the case failed — making the CONTROL red and this
    # file impossible to mutation-test at all. The case reproduced, against itself, the very defect
    # it was written to test. A case whose outcome is a property of the ENVIRONMENT is this repo's
    # recorded `a-case-can-pass-for-an-ambient-reason`, with the sign flipped; the remedy is the
    # same one — BUILD THE WORLD.
    # ⚠ ROUND 7 L4 — THE MARKER IS DERIVED FROM THE FIXTURE'S OWN PATH. The first version had the
    # arm fall back to a GLOB (`_selftest-marker-*`), so a peer's marker or a stale one satisfied
    # it and the case could pass without its own world being built. `${BASH_SOURCE[0]%.sh}.marker`
    # is exact and needs no pid guess at all.
    marker = HOOK.parent / f"{FIXTURE_PREFIX}{_os.getpid()}.marker"
    try:
        marker.write_text("a file the FIXTURE owns, so the arm means the same thing in the real "
                          "repo, in a staged copy, and in CI\n", encoding="utf-8")
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
        yield path
    finally:
        path.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)


def _self_test() -> int:
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            print(f"[FAIL] {name}\n       expected {want!r}\n       got      {got!r}")
            fail += 1

    def refuses(name: str, fn) -> None:
        """A REFUSAL, and any other exception is a FAILURE rather than a pass — a crash is red for
        every reason at once and is attributable to no case."""
        nonlocal ok, fail
        try:
            fn()
        except CannotRun:
            ok += 1
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name}\n       expected CannotRun, got {exc!r}")
        else:
            print(f"[FAIL] {name}\n       expected CannotRun, nothing raised")
        fail += 1

    SHIPPED = HOOK.read_text(encoding="utf-8")
    _before = hashlib.sha256(SHIPPED.encode()).hexdigest()

    # ── the observer, against the REAL hook ────────────────────────────────────────────────
    case("rc 5 with no detail renders the static sentence alone",
         render(5, "").rstrip(), DECLARED_RENDER[5])
    case("...and with a detail it renders the sentence PLUS the detail",
         render(5, "WIDGET").rstrip().endswith("Detail: WIDGET"), True)
    case("a code with no arm renders nothing", render(4, "anything"), "")
    case("the code decides which arm answers", render(6, "X").startswith("recall-llm: a plan IS"),
         True)
    case("a hostile payload survives the envelope — braces and a JSON fragment",
         '{"a": [1,2]}' in render(5, '{"a": [1,2]}'), True)
    case("...and a trailing newline in the detail does not break it",
         "LINE" in render(5, "LINE\n\n"), True)
    case("silence is EMPTY, not malformed — the two must stay distinguishable", render(2, "x"), "")

    # ── refusals. Every one is a cannot-run, never a pass ─────────────────────────────────
    refuses("a hook that writes to STDERR is a refusal — round 6 H1",
            lambda: _refuse_probe('printf "boom" >&2\nexit 0\n'))
    refuses("a hook that exits NON-ZERO is a refusal",
            lambda: _refuse_probe('exit 3\n'))
    refuses("a hook that prints something that is not its envelope is a refusal",
            lambda: _refuse_probe('echo "not json at all"\n'))
    # ⚠ THE ADJACENT CASE, and the mutation sweep is why it exists. The one above fails at
    # `json.loads`, so it never reaches the ENVELOPE lookup — the mutation that turns that lookup
    # into a `.get()` chain SURVIVED, because no case fed it output that parses and is still the
    # wrong shape. Valid JSON without the envelope must be a refusal, not silence.
    refuses("...and VALID JSON of the wrong shape is a refusal, not silence",
            lambda: _refuse_probe('echo \'{"other": 1}\'\n'))
    refuses("a hook that is not a file at all is a refusal",
            lambda: render(5, "", hook=HOOK.parent / "does-not-exist.sh"))

    # ── R3 — THE EQUALITY, and the corpus of every arm that ever defeated it ──────────────
    case("the SHIPPED hook renders exactly its declared sentences",
         undeclared_render(DECLARED_RENDER), [])
    _wrong = {**DECLARED_RENDER, 5: "A SENTENCE THE HOOK NEVER RENDERS"}
    case("a declaration the hook does not match is reported",
         [rc for rc, _g, _w in undeclared_render(_wrong)], [5])
    case("...and the report carries BOTH sentences, because a reader has to judge the new one",
         [(len(g) > 0, w) for _rc, g, w in undeclared_render(_wrong)],
         [(True, "A SENTENCE THE HOOK NEVER RENDERS")])
    case("undeclared_render answers only about the codes DECLARED to it",
         undeclared_render({0: "", 3: ""}), [])

    # ⭐⭐ THE PINNED CORPUS — one arm per proxy-boundary found across FOUR rounds. Each presented
    # backlog #201's reader-visible defect. Measured over this same table: the label vocabulary
    # caught 5 of 11, the render comparison that replaced it caught 3, this equality catches 11.
    # ⛔ DO NOT regenerate it: its value is that a reader JUDGED each render to be a broken promise.
    STATIC = DECLARED_RENDER[5]
    _CORPUS = (
        ("r3 M4   append in a SEPARATE statement", f'     PAYLOAD="$PAYLOAD Detail: $OUT" ;;'),
        ("r5 H1   a label the vocabulary never knew", '     PAYLOAD="$PAYLOAD Reason: $OUT" ;;'),
        ("r5 H1   ONE added letter", '     PAYLOAD="$PAYLOAD Details: $OUT" ;;'),
        ("r6 B1   a suffix AFTER $OUT", '     PAYLOAD="$PAYLOAD Detail: $OUT." ;;'),
        ("r6 B1   $OUT in brackets", '     PAYLOAD="$PAYLOAD Detail: [$OUT]" ;;'),
        ("r6 B1   text on BOTH sides", '     PAYLOAD="$PAYLOAD got $OUT ok" ;;'),
        ("r6 B1   TWO interpolations", '     PAYLOAD="$PAYLOAD a $OUT b $OUT c" ;;'),
        ("r6 B1a  TRUNCATED below the old probe's length",
         '     PAYLOAD="$PAYLOAD Detail: ${OUT:0:16}" ;;'),
        ("r6 B1a  TRANSFORMED, so no literal probe appears",
         '     PAYLOAD="$PAYLOAD Detail: $(printf %s "$OUT" | tr -d -)" ;;'),
        ("r6 B1b  an else-branch differing by ONE interior character",
         '     if [ -n "$OUT" ]; then PAYLOAD="$PAYLOAD Detail: $OUT";'
         ' else PAYLOAD="$PAYLOAD  Detail:"; fi ;;'),
        # ⛔ ROUND 7 B2 — THE ARM THAT ONLY A REAL-REPO RUN CAN SEE. It branches on a file the old
        # staged observer never staged, so that observer reported CLEAN while the reader met #201.
        ("r7 B2   branches on a REPO FILE — invisible to a STAGED observer, seen here",
         '     if [ -f "${BASH_SOURCE[0]%.sh}.marker" ];'
         ' then PAYLOAD="$PAYLOAD Detail: $OUT"; else PAYLOAD="$PAYLOAD"; fi ;;'),
    )
    for _why, _arm in _CORPUS:
        _src = (SHIPPED.split('case "$RC" in')[0] + 'case "$RC" in\n'
                + f'  5) PAYLOAD="{STATIC}"\n' + _arm + '\n  *) : ;;\nesac\n'
                + SHIPPED.split("esac\n", 1)[1])
        with _fixture_hook(_src) as _fx:
            case(f"the corpus arm is refused — {_why}",
                 [rc for rc, _g, _w in undeclared_render({5: STATIC}, hook=_fx)], [5])

    # ── H1 — ONE ALLOWLIST, RECONCILED. Two hand-copies was the fix for a drift defect. ────
    _sib = __import__("importlib").util.spec_from_file_location(
        "_sib_env", ROOT / "scripts" / "check-rc-contract.py")
    _sibmod = __import__("importlib").util.module_from_spec(_sib)
    sys.modules["_sib_env"] = _sibmod
    _sib.loader.exec_module(_sibmod)
    case("the subprocess env allowlist is the SAME in both guards — round 8 H1",
         tuple(SUBPROCESS_ENV_KEYS), tuple(_sibmod.SUBPROCESS_ENV_KEYS))

    # ── r3 MEDIUM — THE PROPERTY MUST BE TAKEN THROUGH THE PRODUCTION SPAWN, NOT THE CONSTANT.
    # r2's fix asserted the VALUE of `SUBPROCESS_ENV_KEYS`; nothing asserted `_render_once` READS
    # it, so replacing the reference with an inline literal missing the key left this suite green
    # at 59/59 — and an inline hand-copied scrub IS round 8 H1's original defect, the very thing
    # this constant exists to prevent. Measured before the repair.
    # ⛔ So the probe drives the REAL scrub through the REAL spawn: a fixture hook that imports a
    # module. It is red in BOTH directions — the constant losing the key, and `_render_once`
    # ceasing to consult it — and the two mutation entries name this one case.
    # ⚠ It SETS the variable rather than reading the caller's, so the verdict cannot depend on how
    # the guard was invoked (backlog #56's shape), and it restores the prior value in a `finally`.
    def _production_spawn_writes_cache() -> list[str]:
        """-> `.pyc` names the REAL scrubbed spawn leaves behind. `[]` is the property holding."""
        _probe = tempfile.mkdtemp()
        _hook_src = (
            '#!/usr/bin/env bash\n'
            'set -uo pipefail\n'
            f'printf \'V = 1\\n\' > "{_probe}/_pycprobe.py"\n'
            f'PYTHONPATH="{_probe}" python3 -c \'import _pycprobe\' >/dev/null 2>&1\n'
            'python3 -c \'import json,sys; print(json.dumps({"hookSpecificOutput":'
            '{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))\' '
            '<<<"probe-detail"\n'
            'exit 0\n')
        _saved = os.environ.get("PYTHONDONTWRITEBYTECODE")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            with _fixture_hook(_hook_src) as _fx:
                _render_once(_fx, 5, "probe-detail", True)
        finally:
            if _saved is None:
                os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            else:
                os.environ["PYTHONDONTWRITEBYTECODE"] = _saved
        return sorted(q.name for q in (Path(_probe) / "__pycache__").glob("*.pyc"))

    case("a spawn scrubbed by THIS guard's allowlist writes no bytecode cache — r2 Medium",
         _production_spawn_writes_cache(), [])
    _rat = __import__("importlib").util.spec_from_file_location(
        "_sib_rat", ROOT / "scripts" / "check-ratchet-contract.py")
    _ratmod = __import__("importlib").util.module_from_spec(_rat)
    sys.modules["_sib_rat"] = _ratmod
    _rat.loader.exec_module(_ratmod)
    case("the fixture prefix this file WRITES is the one the ratchet guard EXCLUDES — round 8 M2",
         FIXTURE_PREFIX, _ratmod.FIXTURE_PREFIX)

    # ── M3 — the terminator test, which refuted the label list's "closed set" argument ─────
    case("a declaration ending in a CONNECTOR dangles whatever word precedes it",
         [lab for _rc, lab in declaration_dangles({5: "x Context", 6: "y Note-"})], ["-"])
    case("...and every shipped declaration passes it",
         declaration_dangles(DECLARED_RENDER), [])

    # ── H2 — an arm that reads an AMBIENT variable is a refusal, not a clean pass ───────────
    _AMB = (f'  5) PAYLOAD="{DECLARED_RENDER[5]}"\n'
            '     if [ -n "${USER:-}" ]; then PAYLOAD="$PAYLOAD Detail: $OUT"; fi ;;\n')
    _shipped_head, _, _shipped_tail = SHIPPED.partition('case "$RC" in')
    with _fixture_hook(_shipped_head + 'case "$RC" in\n' + _AMB + "  *) : ;;\nesac\n"
                       + SHIPPED.split("esac\n", 1)[1]) as _fx:
        refuses("an arm reading an AMBIENT variable is a refusal — round 8 H2",
                lambda: render(5, "", hook=_fx))

    # ── H3 — the WITH-DETAIL polarity ──────────────────────────────────────────────────────
    case("the SHIPPED hook renders exactly its declared WITH-DETAIL text",
         undeclared_detail(DECLARED_WITH_DETAIL), [])
    _wrongd = {**DECLARED_WITH_DETAIL, 5: DECLARED_RENDER[5] + " Detail: TRUNCATED"}
    case("a with-detail render that is not the approved one is reported",
         [rc for rc, _a, _b in undeclared_detail(_wrongd)], [5])
    # ⛔ THE CASE H3 WAS OWED, and `check-fixture-variation.py` is what made me notice it was
    # missing: `undeclared_detail(hook=…)` took its default at every call site, so the parameter
    # was indistinguishable from a literal — and the arm that MOTIVATED the rule had only ever been
    # checked by hand. It keeps the `-n` guard and TRUNCATES, which is exactly why the no-detail
    # equality cannot see it.
    with _fixture_hook(SHIPPED.replace(
            '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;',
            '     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: ${OUT:0:16}" ;;')) as _fxt:
        case("a TRUNCATED detail is refused — round 8 H3's own arm",
             [rc for rc, _a, _b in undeclared_detail(DECLARED_WITH_DETAIL, hook=_fxt)], [5, 6])
        case("...while the no-detail equality passes it, which is why both polarities exist",
             undeclared_render(DECLARED_RENDER, hook=_fxt), [])

    # ── the cross-file question, the ONE this file asks ───────────────────────────────────
    D = {"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3, "BAD_RESPONSE": 4,
         "UNREADABLE_PLAN": 5, "UNANSWERABLE": 6}
    # ── H1 — the net over the DECLARED LITERALS ───────────────────────────────────────────
    case("no declared sentence is itself a dangling promise",
         declaration_dangles(DECLARED_RENDER), [])
    case("...and #201's own text WOULD be refused if someone approved it",
         declaration_dangles({5: DECLARED_RENDER[5] + " Detail:"}), [(5, "Detail:")])
    case("...whatever the label spelling, over this CLOSED set of six",
         [declaration_dangles({5: f"x {lab}"})[0][1] for lab in _DANGLING_LABELS],
         list(_DANGLING_LABELS))
    case("...and a sentence with text AFTER the label is not a dangling promise",
         declaration_dangles({5: "x Detail: something"}), [])

    case("equal sets agree", coverage(D, DECLARED_RENDER), [])
    case("a defined code with NO declared sentence is refused",
         len(coverage({**D, "SEVENTH": 7}, DECLARED_RENDER)), 1)
    case("...and the message names the code and its constant",
         "rc 7 (SEVENTH)" in coverage({**D, "SEVENTH": 7}, DECLARED_RENDER)[0], True)
    case("a declared sentence for a code nothing defines is refused",
         len(coverage(D, {**DECLARED_RENDER, 9: "x"})), 1)
    case("the matcher's real tuple is READ, not re-derived", _defined_codes(), D)

    def _renders_despite(var: str, val: str) -> bool:
        """Does the hook still render its declared sentence with `var` set in the environment?

        ⛔ A `CannotRun` HERE IS A CLEAN FALSE, NOT A CRASH. The first version put the call
        directly in the case expression, so the mutation that restores the wholesale environment
        made `render` raise straight through the suite: the harness reported "the suite went RED
        but printed no `[FAIL]` line, so NOTHING COULD SEE THE KILL". A traceback is red for every
        reason at once and is attributable to no case.
        """
        _os.environ[var] = val
        try:
            return render(5, "").rstrip() == DECLARED_RENDER[5]
        except CannotRun:
            return False
        finally:
            _os.environ.pop(var, None)

    case("an ambient PYTHONVERBOSE does not turn the gate into a refusal — round 7 L1",
         _renders_despite("PYTHONVERBOSE", "1"), True)

    # ⛔ THE WIRING CASE FOR H1'S NET, AND ITS ABSENCE IS THE THIRD INSTANCE OF ONE CLASS IN THIS
    # FOLD. Round 5 H2: `dead_arms` ran and its result was discarded, suite green. Round 6: the
    # same for R4. Here: `declaration_dangles` had a case for the FUNCTION and none for the CALL
    # SITE, so the mutation that stopped `main` reading its result SURVIVED. A rule with no wiring
    # case is a rule a refactor can silently detach.
    import contextlib as _ctx
    import io as _io
    _saved_decl = dict(DECLARED_RENDER)
    try:
        globals()["DECLARED_RENDER"] = {**_saved_decl, 5: _saved_decl[5] + " Detail:"}
        _buf = _io.StringIO()
        with _ctx.redirect_stdout(_buf):
            _rc_main = main([])
        _out_main = _buf.getvalue()
        # ⚠ IT COUNTS THE PROBLEMS, NOT THE EXIT CODE, AND THE SWEEP IS WHY. A dangling DECLARED
        # sentence also fails the EQUALITY — the hook renders the approved text, which the modified
        # declaration no longer is — so `main` returns 1 whether or not the net is wired, and a
        # case on the rc could not tell them apart. Two problems with the wiring, one without.
        case("H1 is WIRED — the net's result reaches the verdict through main",
             (_rc_main, _out_main.count("✗")), (1, 2))
        case("...and the message names the DECLARED sentence as the dangling one",
             "is itself a dangling promise" in _out_main, True)
    finally:
        globals()["DECLARED_RENDER"] = _saved_decl

    # ⛔ THE WIRING CASE FOR `coverage` — ROUND 8's BLOCKING, AND THE FOURTH INSTANCE OF ONE
    # CLASS IN THIS FOLD. r5 H2: `dead_arms` ran and its result was discarded. r6: the same for R4.
    # r7: the same for `declaration_dangles`. And this one was written WHILE fixing that third
    # instance — the manifest covered `coverage`'s INTERNALS and `declaration_dangles`'s WIRING,
    # and nobody covered `coverage`'s wiring. Reproduced by the reviewer: replace
    # `problems = coverage(defined, DECLARED_RENDER)` with `problems = []` and the suite still
    # printed 43/43 while the live guard still printed OK.
    # ⚠ IT ASSERTS THE PROBLEM COUNT, NOT THE EXIT CODE: a declaration missing a defined code
    # trips `coverage` and NOT the equality, so the rc alone would not separate the two.
    _saved_cov = dict(DECLARED_RENDER)
    try:
        globals()["DECLARED_RENDER"] = {k: v for k, v in _saved_cov.items() if k != 4}
        _buf2 = _io.StringIO()
        with _ctx.redirect_stdout(_buf2):
            _rc_cov = main([])
        _out_cov = _buf2.getvalue()
        # ⚠ H4 — THE MATCHER IS STAGED, NOT THE REAL ONE, so `defined = _defined_codes()` cannot
        # be severed to a literal dict and still pass: a staged SEVENTH code must reach `coverage`.
        _saved_m = globals()["MATCHER"]
        case("coverage is WIRED — its result reaches the verdict through main",
             (_rc_cov, _out_cov.count("✗")), (1, 1))
        case("...and the message names the code nobody approved a sentence for",
             "rc 4 (BAD_RESPONSE) is defined by the matcher and has NO declared" in _out_cov, True)
    finally:
        globals()["DECLARED_RENDER"] = _saved_cov

    # ⛔ THE WIRING CASE FOR THE WITH-DETAIL POLARITY — THE SEVENTH INSTANCE OF ONE CLASS IN THIS
    # FOLD, and I wrote it two hours after filing #213 about the other six. The rule had a case
    # calling `undeclared_detail` DIRECTLY, so the mutation that stops `main` reading its result
    # SURVIVED. Adding a rule and WIRING a rule are separate acts and only one has a test by
    # default — which is #213's own sentence, now with a seventh data point.
    _saved_wd = dict(DECLARED_WITH_DETAIL)
    try:
        globals()["DECLARED_WITH_DETAIL"] = {**_saved_wd,
                                             5: DECLARED_RENDER[5] + " Detail: NOT-WHAT-IT-SENDS"}
        _buf3 = _io.StringIO()
        with _ctx.redirect_stdout(_buf3):
            _rc_wd = main([])
        _out_wd = _buf3.getvalue()
        case("the WITH-DETAIL polarity is WIRED — its result reaches the verdict through main",
             (_rc_wd, _out_wd.count("✗")), (1, 1))
        case("...and the message shows the detail the reader would actually get",
             "NOT-WHAT-IT-SENDS" in _out_wd, True)
    finally:
        globals()["DECLARED_WITH_DETAIL"] = _saved_wd

    # ⚠ `main`'s ONE argv-sensitive branch had no case, and argv was `[]` at every call site —
    # `check-fixture-variation.py` was right that nothing could tell it from a literal. The suite
    # is STUBBED rather than re-entered, because `main(["--self-test"])` for real is unbounded
    # recursion; `main` resolves `_self_test` from module globals at call time.
    _saved_st = globals()["_self_test"]
    globals()["_self_test"] = lambda: 99
    try:
        case("main dispatches --self-test to the suite", main(["--self-test"]), 99)
        case("...and an argv WITHOUT it does not reach the suite", main(["--nope"]) != 99, True)
    finally:
        globals()["_self_test"] = _saved_st

    # ── the structural property: production observes the REAL FILE ────────────────────────
    case("render defaults to the SHIPPED hook, so the live run has no fixture to be unfaithful to",
         render.__defaults__, (None,))
    case("...and the suite left the shipped hook byte-identical",
         hashlib.sha256(HOOK.read_text(encoding="utf-8").encode()).hexdigest(), _before)
    # ⛔ PID-SCOPED, AND A BARE GLOB HERE WAS ROUND 7 B1 — A BLOCKING THAT VOIDED THE WHOLE GATE.
    # `run_mutations` restores ONLY the mutated source file (`orig = (d / fname).read_text()` …
    # `write_text(orig)`), so mutation entry 10 — which makes the fixture deliberately NOT be
    # removed — left `_selftest-<pid>.sh` in the staged tree. A bare glob then failed the
    # AFTER-control, and a red after-control makes `--mutate .` return NotMeasured over ALL 1163
    # entries, deterministically. Measured end to end: before-control 36/36, 11 caught and
    # attributed, after-control rc=1 on this case.
    # ⚠ IT ALSO FIXES M4: two concurrent `--self-test` runs share this directory, and a bare glob
    # saw the PEER's fixture — a false red reproduced at 2 of 6 stagger offsets.
    case("...and no fixture hook of THIS RUN survived the suite",
         sorted(q.name for q in HOOK.parent.glob(f"{FIXTURE_PREFIX}{_os.getpid()}.sh")), [])
    case("...nor this run's fixture MARKER — the file the corpus arm branches on",
         sorted(q.name for q in HOOK.parent.glob(f"{FIXTURE_PREFIX}{_os.getpid()}.marker")), [])

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


def _refuse_probe(body: str) -> str:
    """Run a deliberately broken fixture hook, for the refusal cases."""
    with _fixture_hook("#!/usr/bin/env bash\nset -uo pipefail\n" + body) as fx:
        return render(5, "", hook=fx)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Which recorded lesson fires at this moment? — matched by MEANING, one model call per PLAN.

WHAT THIS REPLACES, AND THE MEASUREMENT THAT RETIRED IT
-------------------------------------------------------
`scripts/recall-match.py` (branch `c5-recall-matcher`) compared the situation to each trigger by
token overlap weighted by IDF. It was REFUTED on 2026-09-29, and the refutation is in
`scripts/fixtures/recall-replication-2026-09-29.json` — a labelled set committed BEFORE either arm
ran, with 20 must-fire paraphrases authored by an agent that never saw the triggers and 60 dull
engineering moments authored by an agent that never saw any of it:

    lexical, top-1      3/20 must-fire     7 false fires of 60   (11.7%)
    LLM, meaning        20/20 must-fire    0 false fires of 60   (isolated re-run, 80/80)

⛔ AND THE CHEAP HYBRID IS REFUTED TOO, SO DO NOT ADD A PREFILTER. With the threshold floored to 0
so nothing is cut, lexical recall@10 is 12/20 and recall@20 is *also* 12/20 — eight correct entries
rank 66th to 108th. A shortlist stage can only LOSE recall, so lexical-shortlist + LLM scores at
best 12/20 against 20/20 for the model alone. There is no token scoring, no stemming, no IDF and no
threshold anywhere in this file, and adding one would make it worse by a measured margin.

WHY THE CALL HAPPENS AT ARM TIME, WHICH IS THE WHOLE DESIGN
-----------------------------------------------------------
`claude -p` answered a trivial prompt in **6.41s** (measured 2026-09-29), against the 125 ms of the
hook this replaces. At the ~275 tool-call invocations of one session that is 29 minutes, so the call
cannot sit on a frequent boundary.

It does not have to. `scripts/begin-plan.py` writes EVERY step of a plan up front, each carrying its
own `Doing:` line, so **all the situations are knowable before any of them happens**:

    --arm    ONE model call for the whole plan (~3.5 plans/day), every step matched at once,
             the answers written to .claude/recall-cache/<plan-stem>.json
    --fire   NO model call at all: sentinel -> plan -> first unticked step -> dict lookup

⭐ STRUCTURE: EVERY DECISION IS A PURE FUNCTION; THE REST IS PLUMBING. A model call cannot be
mutation-tested — that is the honest cost of this mechanism, and the answer is to make the
untestable surface as small as it can be rather than to accept the gap. So what to send, what to
accept back, what counts as stale, what the reader sees and what every refusal is are all pure
functions with cases and a mutation entry each.

⚠ WHAT IS NOT COVERED BY A CASE, stated rather than implied. `call_model` reaches outside this
machine and no case touches it. The IO assembly under it — `read_armed_plan`, `read_corpus`,
`prepared_prompt`, `do_arm`, `do_fire` — holds no rule of its own, but it does hold the WIRING, and
a covered predicate with miswired branches is a defect this repository has measured repeatedly. That
wiring was verified by RUNNING it, 2026-09-29: paused → silent rc=0, no cache → 3, edited situation
→ 3, tick-only edit → served, no sentinel → 2, zero triggers → 2, and three rejected replies → 4
with the on-disk cache byte-identical afterwards. Execution, not a case.

⛔ AND THE ISOLATION OF THE MODEL CALL IS NOT MUTATED, WHICH IS DECLARED RATHER THAN IMPLIED.
`call_model`'s `cwd=sandbox` and the refusal above it have NO mutation entry: no case can reach
them, and writing an `expect` that names no real case is exactly the "hole with a label on it" that
shipped on the refuted branch. Two candidate entries were written and DROPPED for that reason. So
the sweep's green says nothing about this line. ⚠ Its property IS covered — `outside_repo` has four
cases and two mutations — and the wiring was verified by EXECUTION on 2026-09-30: from the repo the
reply was 1,278 chars of prose (rc=4); from a temp directory, 75 chars of clean JSON; after the fix,
`--arm` completed in 11.2s with all five steps parsed. ⭐ This is the review's own closing point
applied honestly: a mutation cannot delete a call that is absent, and the sweep does not stage
`.claude/hooks/`, so a perfect score can sit over exactly the region that holds the defect.

⛔ AND ONE OF THOSE CLAIMS WAS FALSE AS FIRST WRITTEN — kept here rather than quietly corrected.
The list also read "corpus unreachable → 2", which held for `--arm` and NOT for `--fire`: fire reads
only the cache, and the cache stores the trigger TEXT as well as the name, so it touched the corpus
not at all and exited 0 with a match printed. One run was generalised to both modes. Found by
re-running it, not by re-reading it. `cached_entry_verdict` is the repair and both modes refuse now:
`--fire` under a redirected HOME → 2, and a cache naming a renamed-away entry → 3 — the second
re-measured by actually moving a corpus file and restoring it.

⛔ FAIL CLOSED — "nothing fires" AND "could not look" MUST NOT LOOK THE SAME
----------------------------------------------------------------------------
A matcher that prints nothing when the corpus is missing reports a PASS it did not earn, and a zero
over nothing is not a finding. This is not a hypothetical: the refuted matcher's own `corpus_verdict`
exists because the decision was once inline in `main()`, where no case could reach it — and flipping
the empty-corpus branch to OK left its suite GREEN (`git show c5-recall-matcher:scripts/recall-match.py`,
that function's docstring). So here every one of those outcomes is a pure function with a case:

    rc=0   matched, or the model genuinely answered NONE for this step over a NON-EMPTY corpus
    rc=2   CANNOT RUN — no memory directory, zero parseable triggers, no armed plan, or no
           readable plan FILE. ⛔ This is the ROUTINE absence: on a machine with no plan armed it
           is the normal state, and a caller is right to stay silent about it.
    rc=3   STALE CACHE — the plan's SITUATIONS have been edited since it was armed, this step was
           never matched, or the cache file is unparseable. NEVER served: a cached answer for a
           different situation is a wrong answer, not an old one. Ticking a box is NOT a change of
           situation and does not stale.
    rc=5   UNREADABLE PLAN — a plan IS armed and cannot be read: no step matching
           `- [ ] **Step N of M**`, or a step with neither a `Doing:` line nor a title. ⛔ SPLIT
           OUT OF rc=2 BY REVIEW ROUND 1 (B1), and the split IS the fix. While both were 2 a
           caller could not tell "nothing is armed" from "something is armed and I am blind to
           it", so the catch-all that correctly ignores the first swallowed the second. Measured:
           87 committed plans under `docs/superpowers/plans/` are in the unreadable shape today.
    rc=4   RESPONSE REJECTED — the model's reply named an entry that is not in the corpus, or did
           not answer exactly the steps it was asked about. Never guessed at.
    rc=6   CANNOT ANSWER — a plan IS armed, the cache is valid, and the answer cannot be reached
           anyway: the corpus directory is gone. ⛔ SPLIT OUT OF rc=2 BY BACKLOG #202, and it is
           rc=5's split repeated on the side no round examined. While this was 2 the hook's
           catch-all swallowed it exactly as it once swallowed rc=5 — measured, 290 bytes of
           control against ZERO. ⚠ Distinct from rc=5 on purpose: that one says the PLAN cannot be
           read, and blaming the plan for a missing corpus is a wrong answer under a right code.

Usage:
    scripts/recall-llm.py --arm            # ONE model call, matches every step of the armed plan
    scripts/recall-llm.py --fire           # no model call; the entry for the current step
    scripts/recall-llm.py --print-prompt    # exactly what --arm would send. No call, no cost
    scripts/recall-llm.py --self-test  # 199 cases
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

OK, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, UNREADABLE_PLAN, UNANSWERABLE = 0, 2, 3, 4, 5, 6

# Resolved from THIS FILE's path, never from the cwd, so a worktree gets its own sentinel and its
# own cache — the same reason `begin-plan.py` does it that way.
ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude" / "executing-plan"
CACHE_DIR = ROOT / ".claude" / "recall-cache"

TRIGGER_PREFIX = "FIRES-WHEN:"
# The literal the model answers with when nothing fires. A STRING, not None, because it travels
# through JSON and must survive a round trip as a positive answer rather than an absence.
NONE = "NONE"
MODEL = "opus"
CALL_TIMEOUT = 600


class Refusal(Exception):
    """A loud, named refusal carrying the exit code it must produce.

    Every path that cannot answer raises one of these. There is deliberately no handler anywhere
    in this file that turns one into a success — `main` prints it and returns `exc.rc`, which is
    never 0.
    """

    rc = CANNOT_RUN
    label = "CANNOT RUN"

    def __init__(self, message: str):
        super().__init__(message)


class StaleCache(Refusal):
    rc = STALE_CACHE
    label = "STALE CACHE"


class ResponseRejected(Refusal):
    rc = BAD_RESPONSE
    label = "RESPONSE REJECTED"


class UnreadablePlan(Refusal):
    """A plan IS armed and cannot be read. ⛔ DELIBERATELY NOT `CANNOT RUN`.

    Review round 1, B1: `do_fire` never consulted `plan_verdict`, so a plan whose checkboxes do not
    match `_BOX_RE` returned `None` from `first_unticked` by the same route as a FINISHED plan and
    exited 0 in silence — "nothing fires" and "could not look" arriving at the reader as the same
    observation, which is the refuted matcher's own H3 reproduced in its replacement. Measured:
    87 committed plans under `docs/superpowers/plans/` are in that shape today.

    ⛔ A FIFTH CODE, NOT `CANNOT_RUN`, AND THAT IS THE OTHER HALF OF THE FIX. The caller must tell
    "no plan is armed" — genuinely routine, and correctly silent — from "a plan is armed and I
    cannot read it", which the reader needs to hear. Both were rc 2, so the hook's catch-all
    swallowed the second along with the first and the repair would have been invisible. The
    alternative, matching on message text, is H4's defect and not a fix.
    """

    rc = UNREADABLE_PLAN
    label = "UNREADABLE PLAN"


def unanswerable_if_armed(exc: Refusal) -> Refusal:
    """PURE. -> the exception to re-raise once a plan IS known to be armed.

    ⛔ ROUND 3 H1. Backlog #202 split rc 6 out of rc 2 on the `--fire` path and LEFT `--arm`
    CARRYING THE CONJUNCTION — which is B1's error for the third time, and the reviewer enumerated
    every surviving path: `read_corpus` for a missing corpus directory, zero entry files or zero
    parseable triggers; `call_model` for a missing CLI, a timeout, a non-zero exit or empty output;
    and `do_arm`'s cache write after the answer is already paid for. Every one of those happens
    AFTER the plan has been read, so none of them is the routine absence rc 2 is reserved for.

    ⭐ ONE RULE, CONSULTED AT THE TWO BOUNDARIES WHERE THE ARMED SCOPE OPENS — not a class change
    at each raise site. The review record for this file says BOUNDARY RELOCATION is what actually
    closed four of the six defects that produced this whole fold, while per-site edits produced the
    next round's findings. `prepared_prompt` opens the scope once the plan parses; `do_arm` opens
    it again for everything after `prepared_prompt` returns.

    ⚠ THE PREDICATE IS THE CODE, NOT THE CLASS — and it was `type(exc) is Refusal and exc.rc ==
    CANNOT_RUN` until a mutation proved the first half UNFALSIFIABLE. No `Refusal` subclass carries
    rc 2 (`StaleCache` 3, `ResponseRejected` 4, `UnreadablePlan` 5, `Unanswerable` 6), so the rc
    test already excludes every one of them and widening `type(...) is` to `isinstance` changed
    nothing a case could see. An unfalsifiable clause reads as care and defends nothing.
    ⭐ Dropping it is also the more correct rule: what makes a refusal non-routine here is the CODE
    it carries, not which class produced it. A future subclass with rc 2 SHOULD convert, and under
    the old predicate it silently would not have.
    """
    if exc.rc == CANNOT_RUN:
        return Unanswerable(str(exc))
    return exc


class Unanswerable(Refusal):
    """A plan IS armed and the answer cannot be reached — for a reason that is NOT the plan.

    ⛔ A SIXTH CODE, AND IT IS B1's SPLIT REPEATED ON THE SIDE NOBODY LOOKED AT. B1 took
    `UNREADABLE_PLAN` out of `CANNOT_RUN` because a caller must tell "no plan is armed" — routine,
    and correctly silent — from "a plan is armed and I am blind to it", which the reader needs. That
    fixed the PLAN side. `rc=2` still carried the same conjunction on the CORPUS side, and every
    later round looked at the plan side.

    ⛔ MEASURED 2026-09-30, backlog #202, over a GREEN control: an armed plan, a cache valid by the
    module's own `plan_fingerprint`, the named entry present, and only `HOME` changed — control
    forwards 290 bytes, test forwards **0**, over a 161-char message whose last three words are
    "NOTHING WAS SURFACED". The hook was right to ignore rc 2; rc 2 was wrong to mean two things.

    ⚠ NOT `UNREADABLE_PLAN`, though it would have been one line fewer. That label says the PLAN is
    the problem, and here the plan is fine — pointing the reader at their checkboxes when the corpus
    is missing is a wrong answer wearing a right code. One meaning per code is this repo's own rule
    (`check-sentinel-meanings.py`), applied where that guard cannot see.
    """

    rc = UNANSWERABLE
    label = "CANNOT ANSWER"


# ─────────────────────────────────────────────────────── the plan, and the sentinel
# ⚠ `- [ ]` or `- [x]`, then `**Step N of M**`, then an em-dash and the title. This is the shape
# `begin-plan.py:175` writes; the number is taken from the STEP, never from the position in the
# file, because a cache keyed by position silently rebinds every answer when a step is inserted.
# ⛔ ROUND 2 H2. `begin-plan.py:86` accepts `^- \\[( |x)\\] (.*)$` and `cmd_plan` arms any in-repo
# markdown, so a plan can hold boxes that `_BOX_RE` below does NOT match. `plan_steps` then returns
# only the ones it could read, `plan_verdict` sees a NON-EMPTY list and accepts, and `first_unticked`
# points at a LATER step — so the reader standing at step 1 is handed step 2's lesson, at rc 0, with
# no warning. Round 1 named this half of B1 and the fold closed only the all-silent half.
# ⚠ This is the failure the prompt itself calls the most expensive one it can produce: a wrong
# lesson costs more than no lesson. Counting boxes LOOSELY is what tells "no boxes at all" (nothing
# to read) from "boxes I cannot read" (something is there and I am blind to part of it).
_LOOSE_BOX_RE = re.compile(r"^- \[[ x]\]", re.M)

_BOX_RE = re.compile(r"^- \[([ x])\] \*\*Step (\d+) of \d+\*\*(?:\s*—\s*(.*))?$", re.M)
_DOING_RE = re.compile(r"^\s*-\s*\*\*Doing:\*\*\s*(.+)$", re.M)
_PAUSED_RE = re.compile(r"^paused:", re.M)
_PLAN_RE = re.compile(r"^plan:\s*(.+)$", re.M)


def plan_steps(plan_text: str) -> list[tuple[int, str]]:
    """PURE. -> [(step number, situation)] for EVERY step, ticked or not.

    ⭐ TICKED STEPS ARE INCLUDED, and that is the point of arming: the call happens once, before
    any step has run, so it must match the steps that are about to be ticked as well as the one
    outstanding now. Filtering to the unticked step here would put the model call back on a
    per-step boundary, which is the 6.41s-per-fire design this file exists to avoid.

    The situation is the `Doing:` line. A step with no `Doing:` line falls back to its TITLE —
    `begin-plan.py` only writes `Doing:` when it was given one, and a title is a real intent
    statement. A step with neither yields the empty string and `plan_verdict` refuses the plan,
    rather than this function dropping it and making the plan look shorter than it is.
    """
    out: list[tuple[int, str]] = []
    boxes = list(_BOX_RE.finditer(plan_text))
    for i, m in enumerate(boxes):
        end = boxes[i + 1].start() if i + 1 < len(boxes) else len(plan_text)
        doing = _DOING_RE.search(plan_text[m.end():end])
        situation = doing.group(1).strip() if doing else (m.group(3) or "").strip()
        out.append((int(m.group(2)), situation))
    return out


def plan_verdict(steps: list[tuple[int, str]], plan_text: str = "") -> tuple[int, str]:
    """PURE. -> (rc, message) for a parsed plan. A plan nothing can be read out of is UNREADABLE.

    Two ways a plan is unusable, and neither may be reported as "this plan has nothing to match":
    no recognisable step at all (a hand-written file in a different shape), and a step whose
    situation is empty (it would be sent to the model as a blank line and matched against nothing).
    """
    # ⛔ ROUND 2 H2 — THE MIXED PLAN. A plan whose boxes are only PARTLY readable is worse than one
    # that is wholly unreadable: the unreadable ones vanish, the list is non-empty, and the reader is
    # handed a LATER step's lesson while standing at an earlier one. Compared here rather than
    # downstream, because by the time `first_unticked` runs the missing box is indistinguishable
    # from one that was never written.
    if plan_text:
        loose = len(_LOOSE_BOX_RE.findall(plan_text))
        if loose > len(steps):
            return UNREADABLE_PLAN, (
                f"UNREADABLE PLAN: {loose} checkbox(es) are present but only {len(steps)} match "
                f"`- [ ] **Step N of M**`, so the step you are on may be one of the {loose - len(steps)} "
                f"this cannot read — and a later step's lesson would be surfaced instead. Renumber "
                f"them in that shape, or re-arm with `begin-plan.py`.")
    if not steps:
        return UNREADABLE_PLAN, ("UNREADABLE PLAN: the plan file carries no recognisable "
                            "`- [ ] **Step N of M**` step, so nothing was matched.")
    # ⛔ H3. DUPLICATE STEP NUMBERS WERE ACCEPTED, and the numbers are the cache's keys. `plan_steps`
    # takes the number from the step TEXT and never checks uniqueness, so a plan numbered per task
    # (1, 2, 1, 2 — the ordinary shape when numbering restarts) produced duplicate keys. The model
    # was then sent "1. situation ALPHA" AND "1. situation GAMMA", and ONE answer bound to BOTH
    # moments. Refused here rather than patched downstream: a plan whose steps cannot be told apart
    # has no well-defined "current step" at all.
    dupes = sorted({n for n in (x for x, _ in steps) if [y for y, _ in steps].count(n) > 1})
    if dupes:
        return UNREADABLE_PLAN, (f"UNREADABLE PLAN: step number(s) {dupes} appear more than once, "
                                 f"so a cached answer could not be bound to one moment. Number the "
                                 f"steps uniquely across the whole plan.")
    blank = [n for n, s in steps if not s]
    if blank:
        return UNREADABLE_PLAN, (f"UNREADABLE PLAN: step(s) {blank} carry neither a `Doing:` "
                            f"line nor a title, so there is no situation to match them on.")
    return OK, ""


def first_unticked(plan_text: str) -> int | None:
    """PURE. -> the NUMBER of the first `- [ ]` step, or None when every box is ticked."""
    for m in _BOX_RE.finditer(plan_text):
        if m.group(1) == " ":
            return int(m.group(2))
    return None


def paused(sentinel_text: str) -> bool:
    """PURE. -> True when the sentinel carries a `paused:` line.

    ⚠ ANCHORED TO THE START OF A LINE, not a substring test. A pause REASON is free text and can
    itself contain the word — `paused: waiting on the paused: review` — and so can a plan path.
    A substring test reads those as a pause that is not there and goes silent on a live thread.
    """
    return _PAUSED_RE.search(sentinel_text) is not None


def sentinel_plan(sentinel_text: str) -> str | None:
    """PURE. -> the plan path the sentinel names, or None if it names none."""
    m = _PLAN_RE.search(sentinel_text)
    return m.group(1).strip() if m and m.group(1).strip() else None


# ────────────────────────────────────────────────────────────────── the corpus
def frontmatter_description(text: str) -> str | None:
    """PURE. -> the `description:` value of a leading `---` frontmatter block, unquoted.

    Returns None when there is no frontmatter or no `description:` key, so a file that was never
    given a trigger is COUNTED as trigger-less rather than scored as an empty one.
    """
    m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
    if not m:
        return None
    for line in m.group(1).split("\n"):
        if line.startswith("description:"):
            val = line[len("description:"):].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            return val
    return None


def parse_trigger(description: str) -> str | None:
    """PURE. -> the trigger clause of a `description:` value, or None if it carries none.

    The trigger runs to the first em-dash, which is what the 2026-09-29 corpus rewrite used to
    separate the trigger from the pre-existing summary. Measured over the live corpus: 142 of the
    144 descriptions carry such a dash and every one of them is commentary, not part of the moment.
    """
    d = description.strip()
    if not d.startswith(TRIGGER_PREFIX):
        return None
    return d[len(TRIGGER_PREFIX):].split("—", 1)[0].strip() or None


def decode_verdict(err: UnicodeDecodeError | OSError | None, what: str, path: str,
                   label: str = "CANNOT RUN") -> tuple[int, str]:
    """PURE. -> (rc, message) for a file that could not be READ. Never a traceback, never rc 1.

    ⛔ H1. FOUR CALL SITES READ A FILE AS UTF-8 AND NONE OF THEM NAMED THE FAILURE: the corpus
    entries, the cache, the plan and the sentinel. A file that is not valid UTF-8 escaped as a
    `UnicodeDecodeError` traceback and the process exited **1** — a code this contract does not
    define, from the one script whose whole thesis is that every outcome is named — and the hook's
    catch-all then swallowed it into silence. `parse_cache` had already closed exactly this hole for
    malformed JSON; it was open for encoding and for the filesystem.

    ⚠ ONE RULE, ONE PLACE. Four call sites each growing their own `try` is four chances to drift,
    which is what `check-vocabulary-collisions.py` exists to refuse. This returns the verdict and
    the callers raise it.
    """
    if err is None:
        return OK, ""
    kind = ("is not valid UTF-8" if isinstance(err, UnicodeDecodeError)
            else f"could not be read ({err.__class__.__name__})")
    # ⚠ THE LABEL IS A PARAMETER BECAUSE THE CLASS IS. A cache read raises `StaleCache` (rc 3) and
    # a plan read raises `Refusal` (rc 2); a sentence reading "CANNOT RUN" over an rc of 3 makes the
    # message contradict the code, which is the same defect as a code contradicting a docstring.
    return CANNOT_RUN, (f"{label}: the {what} at {path} {kind}, so NOTHING was matched. "
                        f"This is not 'nothing applies' — the file could not be read at all.")


def read_or_refuse(path: Path, what: str, refusal: type = Refusal) -> str:
    """-> the file's text, or a raised `refusal` carrying `decode_verdict`'s sentence.

    ⛔ ROUND 2 #2 — THE CLASS IS A PARAMETER BECAUSE NAMING A FAILURE IS NOT ENOUGH IF THE CALLER
    IGNORES THE CODE. H1 stopped an undecodable cache from being a traceback, but it became a bare
    `Refusal` at rc 2 — and the hook's catch-all correctly ignores rc 2, because "no plan armed" is
    the routine state. So the reader still heard nothing: exactly B1's shape, reproduced inside
    B1's own fix. A bad cache is a STALE cache (rc 3, which the hook forwards, and whose repair is
    specific: re-arm), while an unreadable plan or sentinel really is CANNOT RUN.
    """
    # ⛔ ROUND 2 (Claude) — THIS WAS AN `is` COMPARISON AGAINST ONE CLASS, so a third refusal class
    # silently got the wrong sentence and a subclass would slip through entirely. The label now
    # belongs to the class, which is the only place that cannot disagree with it.
    label = getattr(refusal, "label", "CANNOT RUN")
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise refusal(decode_verdict(exc, what, str(path), label)[1]) from exc


def memory_dir(cwd: Path | None = None) -> Path | None:
    """-> the memory directory for this project, or None when it does not exist.

    The corpus lives OUTSIDE the repository, under the harness's per-project slug: the absolute
    repo path with every non-alphanumeric character replaced by `-`. Derived, never hardcoded, so
    a worktree or a clone at another path still finds its own corpus.
    """
    root = (cwd or ROOT).resolve()
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
    d = Path.home() / ".claude" / "projects" / slug / "memory"
    return d if d.is_dir() else None


def memory_files(d: Path) -> list[Path]:
    """-> every corpus file. `MEMORY.md` is the INDEX, not an entry, and is excluded."""
    return [p for p in sorted(d.glob("*.md")) if p.name != "MEMORY.md"]


def load_triggers(d: Path) -> list[tuple[str, str]]:
    """-> [(entry name, trigger)] for every file that carries one. The name is the filename stem.

    ⛔ NO `except` THAT SWALLOWS A READ FAILURE. A file this cannot read is a file whose lesson
    cannot fire, and quietly skipping it shrinks the corpus without saying so — which is the
    fail-open shape the whole rc contract above exists to refuse. It raises instead.
    """
    out: list[tuple[str, str]] = []
    for p in memory_files(d):
        desc = frontmatter_description(read_or_refuse(p, "memory entry"))
        trig = parse_trigger(desc) if desc else None
        if trig:
            out.append((p.stem, trig))
    return out


LIVE_OK, LIVE_UNREADABLE, LIVE_NO_TRIGGER = "ok", "unreadable", "no-trigger"


def live_trigger_for(entry: str, d: Path | None) -> tuple[str, str | None]:
    """-> (status, trigger). Status is LIVE_OK, LIVE_UNREADABLE or LIVE_NO_TRIGGER.

    ⛔ H2. One file, not the corpus: `--fire` is a cache lookup measured at 0.12s and re-reading 145
    entries to display one sentence would spend the whole design.

    ⛔ ROUND 2 #1 — THIS RETURNED A BARE `None` AND THAT None MEANT TWO DIFFERENT THINGS: "I could
    not read the file" and "the file is fine and carries no FIRES-WHEN". The caller fell back to the
    cached text for both, so an entry REWRITTEN WITHOUT FRONTMATTER still surfaced the old cached
    sentence — the very defect H2 was raised about, surviving its own fix. Reproduced by the
    reviewer. `check-sentinel-meanings.py` exists to refuse exactly this (one nullable, one
    meaning), and `lookup`'s docstring in this same file already says so about its own None.

    The two now separate because they need OPPOSITE responses: unreadable is bookkeeping (fall back,
    the name still resolves), while no-trigger is MATERIAL — an entry that carries no trigger cannot
    fire at all, so a cache naming it is stale.
    """
    if d is None:
        return LIVE_UNREADABLE, None
    try:
        desc = frontmatter_description((d / f"{entry}.md").read_text(encoding="utf-8"))
    except (UnicodeDecodeError, OSError):
        return LIVE_UNREADABLE, None
    trig = parse_trigger(desc) if desc else None
    return (LIVE_OK, trig) if trig else (LIVE_NO_TRIGGER, None)


def corpus_verdict(n_triggers: int, n_files: int) -> tuple[int, str]:
    """PURE. -> (rc, message) for a loaded corpus. CANNOT RUN is an OUTCOME, not a quiet pass.

    Two distinct failures with two distinct messages, because they call for different repairs: no
    files at all means the corpus is not where this looked, and files with no triggers means the
    `FIRES-WHEN:` rewrite has not reached them.
    """
    if n_files == 0:
        return CANNOT_RUN, ("CANNOT RUN: the memory directory holds ZERO entry files, so nothing "
                            "was checked. A zero over an empty corpus is not a finding.")
    if n_triggers == 0:
        return CANNOT_RUN, (f"CANNOT RUN: {n_files} memory file(s) read, ZERO carry a "
                            f"'{TRIGGER_PREFIX}' trigger. Nothing was matched.")
    return OK, ""


# ─────────────────────────────────────────────────────────────────── the prompt
# ⛔ THIS WORDING IS THE MEASURED ARTEFACT, NOT A DRAFT. It is the prompt that scored 20/20
# must-fire and 0/60 false fires in the isolated run of 2026-09-29. Five clauses are load-bearing
# and each has a self-test case asserting it is still here plus a mutation entry that deletes it:
#   * match on MEANING, not on shared words
#   * NONE is a first-class answer, and the proportion that match is NOT disclosed
#   * a loose or thematically adjacent match is an ERROR, strictly worse than NONE
#   * the test: would this change what the person does next?
#   * routine engineering work usually matches nothing
# A clause deleted here is a measurement invalidated, so the cases pin the LITERAL text rather
# than comparing the prompt to a constant — a case that reads the template it is checking cannot
# notice the template changing.
PROMPT = """You are matching MOMENTS to recorded LESSONS.

Below are {n_triggers} TRIGGERS. Each is the situation in which one specific recorded lesson
applies, followed by the name of the file holding it. After them are {n_situations} SITUATIONS —
things a person is about to do. For each situation, name the single entry whose trigger genuinely
describes that moment, or NONE.

HOW TO DECIDE

* Match on MEANING, not on shared words. The same moment written in completely different
  vocabulary is a MATCH. Two sentences sharing a word but describing different moments are NOT.
* NONE is a first-class answer and is very often the right one. The proportion of these
  situations that match something is NOT disclosed to you — do not infer it, and do not try to
  distribute your answers.
* A loose match, or one that is merely thematically adjacent, is an ERROR — strictly worse than
  NONE. A wrong lesson costs more than no lesson, because it spends the reader's willingness to
  look at this channel at all.
* The test is: WOULD THIS CHANGE WHAT THE PERSON DOES NEXT? If the entry is merely interesting,
  or about the same general area of work, the answer is NONE.
* If the person is ALREADY DOING what the lesson advises, the answer is NONE. A lesson the
  action already embodies changes nothing: telling someone who is adding an accessible name
  that icon-only buttons need accessible names is noise, not recall.
* Routine engineering work usually matches nothing. Most ordinary moments carry no lesson from
  this corpus, and saying so is the correct answer, not a failure to find one.

TRIGGERS

{triggers}

SITUATIONS

{situations}

ANSWER

Reply with a single JSON object and nothing else. Its keys are the situation numbers as strings —
exactly the numbers listed above, all of them, and no others. Each value is either an entry name
spelled exactly as it appears above, or "NONE".

{{"{example_key}": "NONE"}}
"""


def build_prompt(triggers: list[tuple[str, str]], steps: list[tuple[int, str]]) -> str:
    """PURE. -> the one prompt that matches EVERY step against EVERY trigger.

    ⛔ EVERY trigger and EVERY step, in one call. Sending a subset of the corpus is the refuted
    shortlist; sending one step per call is the refuted 6.41s-per-fire boundary.

    Situations are numbered by their STEP NUMBER, not by position, so the reply's keys are the
    cache's keys and no re-indexing happens anywhere between the model and the lookup.
    """
    trig_block = "\n".join(f"* {t}\n  -> {name}" for name, t in triggers)
    sit_block = "\n".join(f"{n}. {s}" for n, s in steps)
    return PROMPT.format(n_triggers=len(triggers), n_situations=len(steps),
                         triggers=trig_block, situations=sit_block,
                         example_key=steps[0][0] if steps else 1)


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """PURE. -> the object, or raises on a REPEATED key. Used as `json.loads`'s `object_pairs_hook`.

    ⛔ H3. WITHOUT THIS THE DUPLICATE IS INVISIBLE. `json.loads` keeps the LAST value for a repeated
    key and reports nothing, so `{"2": "running-codex", "2": "NONE"}` arrives as a clean one-key
    object and the answer the model gave first is silently discarded — guessing, in a function whose
    whole contract is to reject rather than guess. The collapse happens inside the parser, so NO
    comparison made afterwards can see it.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ResponseRejected(f"the reply answers step {key!r} more than once, so one of its "
                                   f"answers was silently discarded by the JSON parser")
        seen.add(key)
    return dict(pairs)


def parse_response(text: str, step_numbers: list[int],
                   valid_names: list[str]) -> dict[int, str]:
    """PURE. -> {step number: entry name or NONE}. REJECTS rather than guesses.

    ⛔ EVERY REFUSAL BELOW IS A RAISE, because each has a plausible-looking silent alternative
    that would ship a wrong answer instead:
      * not JSON at all                  -> not "assume NONE everywhere"
      * a key missing, or one too many   -> not "match up what we can"
      * a name not in the corpus         -> not "take the closest spelling"
      * a non-string value               -> not "stringify it"
    A model that answered about different steps than it was asked about did not answer this
    question, and a hallucinated entry name is the one failure that would surface a file that
    does not exist.

    Tolerant only of PACKAGING: a ```json fence, or prose either side of the object.
    """
    body = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", body, re.S)
    if fence:
        body = fence.group(1).strip()
    start, stop = body.find("{"), body.rfind("}")
    if start < 0 or stop < start:
        # ⛔ CARRY THE EVIDENCE. This raised a bare sentence and threw the reply away, so the one
        # error path that exists to be diagnosed could not be. Measured 2026-09-30: a real rc=4
        # took a captured re-run to explain, and the cause (the subprocess inheriting this repo's
        # hooks) was invisible from the message alone.
        raise ResponseRejected(
            f"the reply contains no JSON object at all ({len(text)} chars). "
            f"First 300: {text.strip()[:300]!r}")
    try:
        obj = json.loads(body[start:stop + 1], object_pairs_hook=no_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ResponseRejected(f"the reply is not valid JSON — {exc}") from exc
    # ⚠ NO `isinstance(obj, dict)` CHECK, and its absence is deliberate: the slice above starts at
    # a `{` and ends at a `}`, so `json.loads` can only return a dict or raise. A branch no input
    # can reach reads as depth and cannot be falsified by any case, which is worse than not having
    # it — so the packaging refusal above is the one that carries this.
    # ⛔ H3, AND MY FIRST FIX FOR IT WAS VACUOUS — recorded because the sweep caught it and I did
    # not. Swapping this comparison from sets to sorted sequences changes NOTHING: `json.loads`
    # collapses duplicate keys before this function sees them, so a dict's keys are unique by
    # construction and `sorted(keys) == sorted(set(keys))` is always true. Measured. The duplicate
    # must be caught in the RAW TEXT — `no_duplicate_keys` does that via `object_pairs_hook`. The
    # sequence comparison stays only because it is the honest shape for comparing sequences.
    want = sorted(str(n) for n in step_numbers)
    got = sorted(obj)
    if got != want:
        missing, extra = sorted(set(want) - set(got)), sorted(set(got) - set(want))
        raise ResponseRejected(f"the reply answers the wrong steps — missing {missing}, "
                               f"unexpected {extra}")
    allowed = set(valid_names)
    picks: dict[int, str] = {}
    for key, value in obj.items():
        if not isinstance(value, str):
            raise ResponseRejected(f"step {key}: the answer is a {type(value).__name__}, "
                                   f"not an entry name")
        if value != NONE and value not in allowed:
            raise ResponseRejected(f"step {key}: {value!r} is not an entry in this corpus")
        picks[int(key)] = value
    return picks


# ──────────────────────────────────────────────────────────────────── the cache
def plan_fingerprint(plan_text: str) -> str:
    """PURE. -> a fingerprint of the plan's SITUATIONS: every step number and its `Doing:` line.

    ⛔ NOT THE MTIME, AND NOT THE FILE'S BYTES EITHER — and the second half of that is a defect
    this function shipped with for one run. Both of those move when `--tick` rewrites a checkbox,
    which changes NOTHING about any step's situation, so either would throw the whole cache away on
    every tick and buy a 6.41s model call per step: exactly the design this file exists to reject.
    An mtime is additionally wrong in the other direction — a plan restored from a copy can carry
    an older mtime than the cache it should invalidate.

    Fingerprinting what `plan_steps` derives answers the only question a cache has to ask: are
    these still the same situations, under the same numbers? A tick is invisible to it; editing a
    `Doing:` line, renumbering, adding or removing a step all change it.
    """
    payload = "\n".join(f"{n}\t{s}" for n, s in plan_steps(plan_text))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def cache_path(slug: str) -> Path:
    """-> the cache file for a plan stem. One file per plan, so two armed trees cannot collide."""
    return CACHE_DIR / f"{slug}.json"


def cache_document(plan: str, plan_text: str, picks: dict[int, str],
                   triggers: dict[str, str], corpus_size: int, when: str) -> dict:
    """PURE. -> the cache document. The fingerprint travels WITH the answers it belongs to.

    `triggers` holds the trigger text of the PICKED entries only, so `--fire` needs no corpus read
    and stays a dictionary lookup even if the memory directory is unreachable.
    """
    return {
        "plan": plan,
        "fingerprint": plan_fingerprint(plan_text),
        "corpus_size": corpus_size,
        "model": MODEL,
        "armed": when,
        "picks": {str(n): v for n, v in sorted(picks.items())},
        "triggers": triggers,
    }


def cache_verdict(cache: dict, plan_text: str) -> tuple[int, str]:
    """PURE. -> (rc, message). A cache that does not belong to THESE situations is never served.

    ONE clause, on purpose. A first version also checked that every step of the plan appears in
    the cache — which, once the fingerprint covers the step NUMBERS as well as their text, is a
    branch no caller can reach: a plan that gained a step has a different fingerprint and is
    refused above it. An unreachable second clause reads as depth and cannot fail, so the absent
    step is left to `lookup`, which raises. One concern, one mechanism.

    STALE rather than CANNOT RUN because the repair is cheap and specific: re-arm.
    """
    want = plan_fingerprint(plan_text)
    got = cache.get("fingerprint")
    if got != want:
        return STALE_CACHE, (f"STALE CACHE: armed against {got}, the plan on disk is {want}. Its "
                             f"situations have been edited since. Re-run --arm; a cached answer "
                             f"for different situations is a wrong answer, not an old one.")
    return OK, ""


def parse_cache(text: str) -> dict:
    """PURE. -> the cache document, or a raised StaleCache. A HALF-WRITTEN cache is not an empty one.

    ⛔ THIS EXISTS BECAUSE THE rc CONTRACT HAD A HOLE. Without it, `json.loads` on a truncated cache
    file escaped as a JSONDecodeError traceback and the process exited **1** — a code this file's
    docstring does not define, from the one script whose whole thesis is that every outcome is
    named. An interrupted `--arm` write is exactly how such a file appears.
    """
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StaleCache(f"STALE CACHE: the cache file is not valid JSON ({exc}) — most likely a "
                         f"half-written file. Re-run --arm.") from exc
    if not isinstance(doc, dict):
        raise StaleCache(f"STALE CACHE: the cache file holds a {type(doc).__name__}, not an "
                         f"object. Re-run --arm.")
    # ⛔ H1(c)(d). VALIDATING ONLY THE TOP LEVEL WAS THE HOLE. `"picks": 5` reached `lookup`'s
    # `key not in picks` and `"triggers": ["x"]` reached `.get(...)`, each escaping as a traceback
    # at rc 1 — a code this contract does not define, which the hook's catch-all then swallowed.
    # A shape check one level down closes both, and says which key is wrong rather than that
    # something is.
    for key in ("picks", "triggers"):
        if key in doc and not isinstance(doc[key], dict):
            raise StaleCache(f"STALE CACHE: the cache's {key!r} is a "
                             f"{type(doc[key]).__name__}, not an object. Re-run --arm.")
    return doc


def lookup(cache: dict, step: int) -> str | None:
    """-> the entry name for `step`, or None meaning THE MODEL ANSWERED NONE.

    ⛔ None MEANS EXACTLY ONE THING HERE. A step absent from the cache RAISES instead of returning
    None, because "nothing fires" and "this step was never matched" call for opposite responses —
    silence versus a refusal — and a single nullable return that meant both is the conjunction
    `check-sentinel-meanings.py` exists to refuse.
    """
    picks = cache.get("picks") or {}
    key = str(step)
    if key not in picks:
        raise StaleCache(f"STALE CACHE: step {step} is not in this cache. Re-run --arm.")
    value = picks[key]
    return None if value == NONE else value


def cached_entry_verdict(entry: str | None, corpus_present: bool, entry_present: bool
                         ) -> tuple[int, str]:
    """PURE. -> (rc, message). A cache naming an entry the corpus NO LONGER HOLDS is not served.

    ⛔ WHY THIS EXISTS, and it was found by verification rather than by review. `--fire` reads only
    the cache — which stores the trigger TEXT as well as the name — so it originally touched the
    corpus not at all. Measured 2026-09-29: with `HOME` redirected so the corpus was unreachable,
    `--fire` printed a match and exited 0. The BEHAVIOUR was defensible and the GAP was real: the
    fingerprint covers the plan's situations, so nothing noticed the corpus at all. Rename or delete
    an entry after arming and the reader is handed a name that opens nothing.

    ⚠ FINGERPRINTING THE WHOLE CORPUS WOULD BE THE WRONG FIX — every memory edit would invalidate
    every cache and buy back the 16.1s call this design exists to avoid, and the corpus genuinely
    does change mid-plan (141 -> 144 entries during this script's own build). The weaker check
    catches the harmful case for one `stat`: does the named entry still resolve?

    THREE inputs, not two, because `corpus_present` and `entry_present` fail for different reasons
    and deserve different messages: a missing DIRECTORY is CANNOT RUN (the world is wrong), a
    missing ENTRY is STALE CACHE (the cache is wrong, and re-arming fixes it).
    """
    if entry is None:
        return OK, ""          # the model said NONE. There is nothing to resolve.
    if not corpus_present:
        return CANNOT_RUN, ("CANNOT RUN: the memory corpus directory is unreachable, so the cached "
                            f"entry {entry!r} cannot be verified or opened. NOTHING WAS SURFACED.")
    if not entry_present:
        return STALE_CACHE, (f"STALE CACHE: the cache names {entry!r}, which the corpus no longer "
                             f"holds — it was renamed or deleted since this plan was armed. "
                             f"Re-run --arm. Surfacing a name that opens nothing is worse than "
                             f"surfacing nothing.")
    return OK, ""


def surface_marker(plan_stem: str, step: int) -> str:
    """PURE. -> the token identifying WHICH (plan, step) was last surfaced."""
    return f"{plan_stem}:{step}"


def nag_once(marker: Path, current: str) -> bool:
    """-> may the nag be SAID this time? Records that it was, so the next call is silent.

    ⛔ M4. Shares `should_surface`'s rule rather than restating it — a second copy of a dedupe is a
    second copy of a rule, which `check-vocabulary-collisions.py` exists to refuse. ⚠ It is
    best-effort for the same reason the surface marker is: failing to RECORD a nag must never
    suppress it, so an unwritable directory means the nag repeats rather than vanishes.
    """
    try:
        last = marker.read_text(encoding="utf-8").strip() if marker.is_file() else None
    except (UnicodeDecodeError, OSError):
        last = None
    if not should_surface(last, current):
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(current, encoding="utf-8")
    except OSError:
        pass
    return True


def should_surface(last: str | None, current: str) -> bool:
    """PURE. -> may this entry be printed? False when this exact step was already surfaced.

    ⛔ WHY THIS EXISTS. The caller is `PostToolUse(Bash, begin-plan.py)`, and `begin-plan.py` is run
    for `--status` and `--banner` as well as `--tick`, so the same step can be re-surfaced several
    times without the situation having changed at all. The refuted lexical matcher's own hook says
    the consequence out loud: *a hook that printed on every call would be trained away within an
    hour* — which was measured at 275 firings a session. Firing per INVOCATION instead of per STEP
    TRANSITION rebuilds that in miniature.

    ⚠ NOT a timestamp and NOT a count. The question is only ever *is this the same step as last
    time*, and a marker of (plan, step) answers exactly that: a tick changes it, re-running
    `--status` does not, and switching plans does. A clock would make the answer depend on when it
    was asked, which is a different question nobody needs.
    """
    return last != current


# ─────────────────────────────────────────────────────────────────── the output
def render(entry: str, trigger: str) -> str:
    """PURE. -> the line the reader sees when something fires.

    The TRIGGER is printed, not just the name: the name alone asks the reader to remember what the
    file is about, and the trigger is the sentence that tells them whether it applies right now.
    """
    return (f"⭐ recall — this moment matches a recorded lesson:\n"
            f"   {entry}\n"
            f"   FIRES-WHEN: {trigger}\n"
            f"   (open the memory file of that name for the detail)")


def fire_output(entry: str | None, trigger: str | None) -> str:
    """PURE. -> what `--fire` prints. EMPTY for a NONE answer, which is a real answer.

    Kept separate from `render` so the decision *whether to say anything* has a case of its own.
    A NONE that printed a reassuring line would put a fire on every step, which is the 52.7%
    firing rate with an 11.7% false-fire rate that the refuted hook measured.
    """
    if entry is None:
        return ""
    return render(entry, trigger or "(trigger not cached)")


def outside_repo(candidate: str, repo: str) -> bool:
    """PURE. -> is `candidate` outside `repo`? The property the model call depends on.

    ⛔ WHY THIS IS A FUNCTION AND NOT AN INLINE `cwd=`. `call_model` has no case, by design, so a
    later edit could drop its `cwd` and nothing would notice — and the consequence is not a crash
    but CONTAMINATION: `claude -p` launched inside this repo loads `.claude/settings.json`, hits the
    Stop guard on an armed plan, and answers with prose instead of JSON. Measured 2026-09-30.
    Extracting the PROPERTY — the working directory is not inside this tree — gives the mutation
    harness something to bite on, which an inline keyword argument cannot provide.

    ⚠ It asserts the property, not the mechanism: it does not prove a hook cannot fire, only that
    the subprocess is rooted where this repo's settings file is not found. That is the whole of the
    contamination path measured, and it is stated rather than implied.
    """
    c, r = Path(candidate).resolve(), Path(repo).resolve()
    return r not in c.parents and c != r


# ───────────────────────────────────────────────────── the ONE impure function
def call_model(prompt: str) -> str:
    """THE ONLY IMPURE FUNCTION. Runs `claude -p` and returns its answer verbatim.

    ⛔ NO self-test case calls this, by design — it costs money, and a case that stubbed it would be
    testing the stub. Everything around it is pure and covered instead.

    MEASURED 2026-09-29, this script's own first real call: 16.1s for a 15,336-character prompt
    (144 triggers, 4 situations) on `--model opus`. The 6.41s in the addendum measurement is a
    TRIVIAL prompt on `--model haiku` — a floor for CLI startup, not a figure for this call. Either
    way the conclusion is the same and it is the reason for the whole arm-time design: this cannot
    sit on a per-step boundary.

    A non-zero exit, a timeout or an empty answer is a REFUSAL. An empty answer in particular must
    never be read as "nothing matches": that is the same shape as an empty corpus.
    """
    # ⛔ RUN IT OUTSIDE THE REPOSITORY. MEASURED 2026-09-30, on this function's SECOND real call:
    # `claude -p` launched with the repo as cwd is a full Claude Code session in this project, so it
    # loads `.claude/settings.json` and every hook in it. It hit the Stop guard, which saw
    # `.claude/executing-plan` naming a plan with unticked steps, REFUSED to let it stop, and the
    # session then explained itself at length — burying its JSON in prose about plan ownership.
    # `parse_response` rejected the reply (rc=4), correctly and uselessly.
    #
    # ⚠ THE FIRST CALL SUCCEEDED WITH A PLAN EQUALLY ARMED, so this is NON-DETERMINISTIC, which is
    # worse than a hard failure: it would have shipped and failed occasionally. Measured both ways —
    # from the repo, 1,278 chars of narrative; from a temp directory, 75 chars of clean JSON.
    #
    # The prompt is entirely self-contained (it carries the triggers and the situations), so the
    # subprocess needs NO repo access. An empty cwd outside the tree means no settings file is
    # found and no hook can fire. ⚠ This is the reason `call_model` has no case: nothing around it
    # was wrong, and it was never run in the state it actually runs in — mid-plan, hooks armed.
    try:
        with tempfile.TemporaryDirectory() as sandbox:
            if not outside_repo(sandbox, str(ROOT)):
                raise Refusal(f"CANNOT RUN: refusing to call the model from {sandbox!r}, which is "
                              f"inside {ROOT!r} — this repo's hooks would reach the subprocess.")
            proc = subprocess.run([  # noqa: S603 - a fixed argv, the prompt is not shell-interpreted
                "claude", "-p", prompt, "--model", MODEL],
                capture_output=True, text=True, timeout=CALL_TIMEOUT,
                cwd=sandbox, stdin=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise Refusal("CANNOT RUN: the `claude` CLI is not on PATH, so no call was made.") from exc
    except subprocess.TimeoutExpired as exc:
        raise Refusal(f"CANNOT RUN: the model call did not finish in {CALL_TIMEOUT}s. "
                      f"NOTHING WAS MATCHED.") from exc
    if proc.returncode != 0:
        raise Refusal(f"CANNOT RUN: `claude -p` exited {proc.returncode}. "
                      f"{proc.stderr.strip()[:400]}")
    if not proc.stdout.strip():
        raise Refusal("CANNOT RUN: `claude -p` returned an empty answer, which is not the same "
                      "thing as 'nothing matched'.")
    return proc.stdout


# ──────────────────────────────────────────────────────────────── IO assembly
def read_armed_plan() -> tuple[str, Path, str]:
    """-> (sentinel text, plan path, plan text). Every failure here is a raised Refusal."""
    # ⛔ ROUND 2 (Claude), BLOCKING — THE LINE BETWEEN rc 2 AND rc 5 IS THE SENTINEL'S EXISTENCE,
    # and every failure below it used to be rc 2. NO sentinel means no plan is armed: genuinely
    # routine, and a caller is right to stay silent. ONCE THE SENTINEL EXISTS A PLAN IS ARMED, and
    # every way of failing to reach a usable one is "armed and I am blind to it" — which is exactly
    # what rc 5 was invented for in round 1, and which round 1 gave to only ONE of the five ways.
    # Measured through the real hook: a sentinel naming a vanished plan, a sentinel naming no plan,
    # and an undecodable sentinel or plan were all rc 2 and therefore SILENT — B1's own sentence,
    # in the only mode the hook runs, reproduced by the commit whose message says it closed it.
    # ⚠ `.claude/plans/` is gitignored, so a branch switch produces the vanished-plan case routinely.
    if not SENTINEL.is_file():
        raise Refusal(f"CANNOT RUN: no plan is armed ({SENTINEL} absent), so there is no "
                      f"situation to match.")
    sentinel_text = read_or_refuse(SENTINEL, "sentinel", UnreadablePlan)
    named = sentinel_plan(sentinel_text)
    if not named:
        raise UnreadablePlan("UNREADABLE PLAN: a plan is armed but the sentinel names no plan "
                             "file, so there is no situation to match. Re-arm it.")
    plan = ROOT / named if not Path(named).is_absolute() else Path(named)
    if not plan.is_file():
        raise UnreadablePlan(f"UNREADABLE PLAN: the sentinel names {named}, which is not a readable "
                             f"file — most often a plan that was never committed, after a branch "
                             f"switch. Re-arm, or clear the sentinel.")
    return sentinel_text, plan, read_or_refuse(plan, "plan file", UnreadablePlan)


def read_corpus() -> list[tuple[str, str]]:
    """-> the trigger corpus, or a raised Refusal. Never an empty list."""
    d = memory_dir()
    if d is None:
        raise Refusal("CANNOT RUN: no memory directory for this project — nothing was checked.")
    triggers = load_triggers(d)
    rc, msg = corpus_verdict(len(triggers), len(memory_files(d)))
    if rc != OK:
        raise Refusal(msg)
    return triggers


def prepared_prompt() -> tuple[str, Path, str, list[tuple[int, str]], list[tuple[str, str]]]:
    """Everything `--arm` needs before it spends anything. Shared with `--print-prompt`.

    ⚠ The prompt is built BEFORE the call, and `--print-prompt` returns from exactly here, so what
    a reader inspects is the same string the model is sent rather than a reconstruction of it.
    """
    _sentinel, plan, plan_text = read_armed_plan()
    steps = plan_steps(plan_text)
    rc, msg = plan_verdict(steps, plan_text)
    if rc != OK:
        # ⛔ ROUND 2 #3. This raised a bare `Refusal` (rc 2) for the SAME verdict `do_fire` reports
        # as rc 5, so `--print-prompt` and `--arm` disagreed with `--fire` about what an unreadable
        # plan is. One meaning, one code, in every mode — otherwise the contract is per-entry-point
        # and a caller cannot rely on it.
        raise UnreadablePlan(msg)
    # ⛔ THE ARMED SCOPE OPENS HERE — round 3 H1. Above this line a refusal can mean "nothing is
    # armed"; below it the plan has parsed, so a bare CANNOT_RUN is a plan that IS armed and an
    # answer that cannot be reached. `unanswerable_if_armed` is the one rule; this is one of its
    # two boundaries.
    try:
        triggers = read_corpus()
    except Refusal as exc:
        raise unanswerable_if_armed(exc) from exc.__cause__
    return build_prompt(triggers, steps), plan, plan_text, steps, triggers


def do_arm() -> int:
    prompt, plan, plan_text, steps, triggers = prepared_prompt()
    # ⛔ THE SECOND BOUNDARY OF THE ARMED SCOPE — round 3 H1. `prepared_prompt` above handles its
    # own (and is the path `--print-prompt` shares); everything below it runs with a plan known to
    # be armed, so `call_model`'s missing CLI / timeout / non-zero / empty output and the cache
    # write are all rc 6, not the routine rc 2.
    # ⚠ It wraps the BODY and not the call above it: wrapping `prepared_prompt()` too would convert
    # "no sentinel" — the genuine routine absence — into rc 6, which is the conjunction inverted.
    try:
        return _arm_body(prompt, plan, plan_text, steps, triggers)
    except Refusal as exc:
        raise unanswerable_if_armed(exc) from exc.__cause__


def _arm_body(prompt: str, plan, plan_text: str, steps, triggers) -> int:
    """Everything `--arm` does once the plan is known good. Split out so the armed scope has a
    boundary a case can drive, rather than a `try` wrapped around an inlined body."""
    print(f"recall-llm: ONE call for {len(steps)} step(s) against {len(triggers)} triggers "
          f"({len(prompt)} chars) …", file=sys.stderr)
    picks = parse_response(call_model(prompt), [n for n, _ in steps],
                           [name for name, _ in triggers])
    by_name = dict(triggers)
    doc = cache_document(
        str(plan.relative_to(ROOT)) if plan.is_relative_to(ROOT) else str(plan),
        plan_text, picks,
        {v: by_name[v] for v in picks.values() if v != NONE},
        len(triggers), datetime.now(timezone.utc).isoformat(timespec="seconds"))
    # ⛔ ROUND 2 H3 — THE ANSWER IS ALREADY PAID FOR BY THIS LINE. An unwritable cache directory
    # raised OSError here and exited 1 — a code this contract does not define — AFTER the model call
    # had been made and answered, throwing the answer away with it. H1 covered file READS and left
    # writes open, and `--arm` is the one path where losing the result costs money rather than a
    # retry. The picks are printed regardless below, so a failed write degrades to "you must re-arm
    # next time" rather than "that call bought nothing".
    out = cache_path(plan.stem)
    # Written to a sibling and RENAMED: `os.replace` is atomic within a directory, so an interrupted
    # arm leaves the previous cache intact instead of a truncated one. `parse_cache` still refuses a
    # truncated file — this removes the way THIS code could produce one, not every way one can
    # arrive (a hand edit, an older format, a bad disk).
    tmp = out.with_suffix(".json.partial")
    written = True
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(out)
    except OSError as exc:
        written = False
        print(f"⚠ the cache could NOT be written ({exc}). The answer below was still paid for and "
              f"is printed in full; nothing will be surfaced automatically until --arm succeeds.")
    fired = sum(1 for v in picks.values() if v != NONE)
    where = str(out.relative_to(ROOT)) if written else "(not written)"
    print(f"{where}: {fired} of {len(picks)} step(s) matched an entry")
    for n, v in sorted(picks.items()):
        print(f"   step {n}: {v}")
    if not written:
        # ⛔ ROUND 3 B1 — THE FOURTH INSTANCE, AND THE FIRST ON A `return` RATHER THAN A `raise`.
        # This read `return OK if written else CANNOT_RUN`, so an unwritable cache exited rc 2 —
        # the routine "nothing is armed" code — after the model call had been made AND PAID FOR.
        # `do_arm`'s `except Refusal` boundary could never see it, because a `return` is not a
        # raise. ⚠ AND MY OWN COMMENT AT `do_arm` CLAIMED THIS PATH BY NAME: "…and the cache write
        # are all rc 6, not the routine rc 2." That sentence was FALSE when it was written, about
        # code in the same edit.
        # ⭐ THE LESSON IS THE SHAPE, NOT THE LINE: three times the rule was relocated to a
        # boundary and the boundary was placed on the RAISE path only. A `return` is an exit from
        # the armed scope too, and no case or mutation reached this line — 196/196, rc-contract
        # rc=0 and 0 survivors were all green over it.
        raise Unanswerable(
            "CANNOT ANSWER: the answer was paid for and could not be cached, so nothing will be "
            "surfaced automatically until --arm succeeds. The picks are printed above.")
    return OK


def do_fire(again: bool = False) -> int:
    """`--fire`, with every REPEATED message suppressed — not just one branch's.

    ⛔ ROUND 2 H5. Round 1's M4 found the useful message rate-limited while the nag was not, and the
    fix added `nag_once` at exactly ONE branch: the missing-cache-file one. Measured, that left
    SEVEN other non-OK paths un-deduped, including the two most reachable stale states — a stale
    fingerprint (produced by editing any `Doing:` line after arming) and an unreadable plan — each
    re-emitting a four-line block into the model's context on EVERY invocation.

    ⭐ SO THE DEDUPE MOVED FROM A BRANCH TO THE BOUNDARY, and its key is the MESSAGE rather than
    (plan, step): the early refusals do not know a step yet, and "have I just said this exact
    sentence?" is the question all eight paths actually share. One rule, one place — the per-branch
    version is deleted rather than joined by seven more.

    ⚠ The rc is NEVER deduped. Only the sentence is: the contract must not lie about the outcome,
    and the hook forwards on non-empty output.
    """
    try:
        return _fire(again)
    except Refusal as exc:
        # ⛔ NO ARMED-SCOPE CONVERSION HERE, AND THE FIRST ATTEMPT AT ROUND 3 M3 PUT ONE HERE AND
        # IT WAS INERT. `exc = unanswerable_if_armed(exc)` followed by a bare `raise` does nothing:
        # a bare raise re-raises the ACTIVE exception, not the rebound name, so only the dedupe
        # path below would have seen it. ⚠ AND THE TEST PASSED FOR THAT REASON — "no sentinel stays
        # rc 2" was green because the fix was a no-op, not because the placement was right.
        # ⛔ THE PLACEMENT WAS ALSO WRONG. `_fire`'s armed scope does not begin at the top of
        # `_fire`; it begins once `read_armed_plan()` has succeeded, exactly as in
        # `prepared_prompt`. Wrapping the whole call would convert the ROUTINE absence — no
        # sentinel — into rc 6, which is the conjunction inverted. The boundary is inside `_fire`.
        msg = str(exc)
        if msg and not nag_once(CACHE_DIR / ".last-said", hashlib.sha256(
                msg.encode("utf-8")).hexdigest()[:16]):
            raise type(exc)("") from exc.__cause__
        raise


def _fire(again: bool = False) -> int:
    # ⛔ ROUND 3 M3 — THE THIRD ENTRANCE TO THE ARMED SCOPE, placed where the scope actually opens.
    # `read_armed_plan()` is OUTSIDE it: its failure means nothing is armed, which is the routine
    # rc 2 the hook is right to ignore. Everything after it runs with a plan demonstrably armed, so
    # a bare `Refusal` there is an armed plan that cannot be answered. Latent rather than live
    # today — nothing below currently raises a bare `Refusal` — but `read_or_refuse`'s DEFAULT
    # class is `Refusal`, so the next read under `--fire` that takes the default would land as the
    # routine code with a plan armed, which is this fold's error a fifth time.
    sentinel_text, plan, plan_text = read_armed_plan()
    try:
        return _fire_armed(again, sentinel_text, plan, plan_text)
    except Refusal as exc:
        raise unanswerable_if_armed(exc) from exc.__cause__


def _fire_armed(again: bool, sentinel_text: str, plan, plan_text: str) -> int:
    """Everything `--fire` does once a plan is known to be armed. Split out so the boundary has a
    seam a case can drive — a `try` around an inlined body has none, which is what made round 3
    M3's first fix both misplaced and inert."""
    if paused(sentinel_text):
        return OK  # a paused thread has no current step. Silence here is an answer, not a failure.
    # ⛔ B1. THIS CALL IS THE FIX, AND ITS ABSENCE WAS THE BLOCKING. `first_unticked` returns None
    # for TWO different worlds — every box ticked, and no box I can parse — so consulting it first
    # made an unreadable plan indistinguishable from a finished one, at rc 0, in silence.
    rc, msg = plan_verdict(plan_steps(plan_text), plan_text)
    if rc != OK:
        raise UnreadablePlan(msg)
    step = first_unticked(plan_text)
    if step is None:
        return OK  # every box ticked: NOW this means only one thing.
    # ⛔ M4. THE NAG IS THE COMMON CASE AND WAS THE ONLY THING NOT RATE-LIMITED. `--arm` is a
    # manual, paid step that nothing runs automatically, so "never armed" is the DEFAULT state of
    # every plan — and the dedupe sat after `fire_output`, reached only on a correct match. So the
    # useful message was rate-limited and the nag was not, which is backwards. The rc stays 3 every
    # time (the contract must not lie about the outcome); only the MESSAGE is deduped, and the hook
    # forwards on non-empty output, exactly as it now does for rc 0.
    cache_file = cache_path(plan.stem)
    if not cache_file.is_file():
        raise StaleCache(f"STALE CACHE: {cache_file.name} does not exist — this plan was never "
                         f"armed for recall. Run `scripts/recall-llm.py --arm`.")
    cache = parse_cache(read_or_refuse(cache_file, "recall cache", StaleCache))
    rc, msg = cache_verdict(cache, plan_text)
    if rc != OK:
        raise StaleCache(msg)
    entry = lookup(cache, step)
    d = memory_dir()
    rc, msg = cached_entry_verdict(entry, d is not None,
                                   d is not None and (d / f"{entry}.md").is_file())
    if rc == CANNOT_RUN:
        # ⟳ backlog #202: was `raise Refusal(msg)` — rc 2, which the hook correctly ignores as the
        # routine "nothing is armed" state, so a 161-char message ending "NOTHING WAS SURFACED"
        # reached the reader as ZERO BYTES. A plan IS armed here; the corpus is what vanished.
        raise Unanswerable(msg)
    if rc != OK:
        raise StaleCache(msg)
    # ⛔ H2. THE CACHED TRIGGER TEXT WAS SHOWN WITHOUT EVER BEING RE-READ. `cached_entry_verdict`
    # checks the entry still RESOLVES; it does not look at what the file now says. Measured: a cache
    # armed while the trigger read "about to quote a green check as evidence", the corpus file then
    # rewritten to "restoring a database from a dump", printed the OLD sentence — one that exists
    # nowhere — and invited the reader to open a file that would not say it. `render`'s own
    # docstring says why that string matters: it is what tells the reader whether this applies now.
    # The LIVE text wins, and a divergence is SAID rather than hidden: it is the reader's signal
    # that the entry may no longer be the right match at all.
    cached_trigger = (cache.get("triggers") or {}).get(entry or "")
    status, live_trigger = live_trigger_for(entry, d) if entry else (LIVE_UNREADABLE, None)
    if status == LIVE_NO_TRIGGER:
        raise StaleCache(f"STALE CACHE: {entry!r} no longer carries a FIRES-WHEN trigger, so it "
                         f"cannot fire at all — the cache names a match that has stopped being "
                         f"one. Re-run --arm.")
    text = fire_output(entry, live_trigger or cached_trigger)
    if entry and live_trigger and cached_trigger and live_trigger != cached_trigger:
        text += ("\n   ⚠ this entry's trigger has been REWRITTEN since the plan was armed; the line "
                 "above is the live one. The match was made against the old wording.")
    # ⛔ ROUND 2 H4. Falling back on LIVE_UNREADABLE keeps a match alive whose NAME still resolves —
    # deliberate, because bookkeeping must not suppress a lesson. But it was SILENT, so `--fire`
    # served a healthy-looking match from an entry `--arm` refuses outright (`load_triggers` raises
    # on an unreadable entry). The two modes disagreed and the reader could not tell. Said now.
    elif entry and status == LIVE_UNREADABLE and cached_trigger:
        text += ("\n   ⚠ this entry could not be READ just now, so the line above is the cached "
                 "wording and may be stale. `--arm` would refuse this corpus outright.")
    if not text:
        return OK
    marker_file = CACHE_DIR / ".last-surfaced"
    current = surface_marker(plan.stem, step)
    # ⚠ NOT `read_or_refuse`, and the asymmetry is deliberate. The marker is BOOKKEEPING: an
    # unreadable one means only that the dedupe cannot be trusted, and refusing over it would let a
    # corrupt byte suppress a correct lesson — the same mistake as writing it before the print.
    # Treated as absent, which reprints at worst.
    try:
        last = marker_file.read_text(encoding="utf-8").strip() if marker_file.is_file() else None
    except (UnicodeDecodeError, OSError):
        last = None
    if not (again or should_surface(last, current)):
        return OK          # this exact step was already surfaced. Silence is the design.
    # ⛔ H1(e). PRINT BEFORE RECORDING, AND THIS ORDER IS THE FIX. The marker was written first, so
    # an unwritable `.claude/recall-cache/` raised PermissionError with everything upstream already
    # correct — cache valid, fingerprint matched, entry resolved — and the matched lesson was never
    # printed at all. Measured: writable -> the entry reaches the model; `chmod 500` -> no output,
    # hook rc 0. **The bookkeeping for a message was allowed to destroy the message.**
    print(text)
    # ⚠ AND THE RECORD IS BEST-EFFORT, DELIBERATELY. If the marker cannot be written the dedupe is
    # lost and this step may be surfaced twice. A duplicate lesson is a far cheaper failure than a
    # lost one, so this must never raise — but it must not be SILENT either, or a permanently
    # unwritable directory degrades to "reprints forever" with nothing saying why.
    try:
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.write_text(current, encoding="utf-8")
    except OSError as exc:
        print(f"(recall-llm: the entry above was surfaced, but the dedupe marker could not be "
              f"written — {exc}. This step may be surfaced again.)")
    return OK


# ────────────────────────────────────────────────────────────────── self-test
def _self_test() -> int:  # noqa: C901 - a flat list of cases is the readable shape
    ok = fail = 0

    def _live_trigger_probe(body):
        with tempfile.TemporaryDirectory() as _td:
            d = Path(_td)
            f = d / "e.md"
            f.write_bytes(body) if isinstance(body, bytes) else f.write_text(body)
            return live_trigger_for("e", d)

    def _nag_probe(seed, current, first):
        with tempfile.TemporaryDirectory() as _td:
            marker = Path(_td) / ".last-nagged"
            if not first:
                nag_once(marker, seed)
            return nag_once(marker, current)

    def _nag_unwritable():
        import os
        with tempfile.TemporaryDirectory() as _td:
            d = Path(_td) / "ro"
            d.mkdir()
            os.chmod(d, 0o500)
            try:
                return nag_once(d / ".last-nagged", "p:1") and nag_once(d / ".last-nagged", "p:1")
            finally:
                os.chmod(d, 0o700)

    def _caught_msg(thunk):
        try:
            thunk()
        except Refusal as exc:
            return str(exc)
        return ""

    def _fire_with_an_unreadable_entry():
        import io, os, contextlib
        with tempfile.TemporaryDirectory() as tdC:
            root, home = Path(tdC) / "repo", Path(tdC) / "home"
            pl = root / ".claude" / "plans" / "w.md"
            pl.parent.mkdir(parents=True)
            pl.write_text("### T\n\n- [ ] **Step 1 of 1** — Go\n  - **Doing:** a situation\n",
                          encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text("plan: .claude/plans/w.md\n",
                                                             encoding="utf-8")
            cd = root / ".claude" / "recall-cache"
            cd.mkdir()
            (cd / "w.json").write_text(json.dumps(cache_document(
                ".claude/plans/w.md", pl.read_text(encoding="utf-8"), {1: "the-entry"},
                {"the-entry": "THE CACHED WORDING"}, 1, "2026-09-30T00:00:00+00:00")),
                encoding="utf-8")
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
            corpus = home / ".claude" / "projects" / slug / "memory"
            corpus.mkdir(parents=True)
            (corpus / "the-entry.md").write_bytes(b"\xff\xfe not utf-8")
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"],
                     os.environ.get("HOME"))
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = cd
                os.environ["HOME"] = str(home)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    do_fire()
                return buf.getvalue()
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved[:3]
                if saved[3] is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved[3]

    def _write_bad_plan(root, sent):
        (root / ".claude" / "plans" / "w.md").write_bytes(b"\xff\xfe nope")
        sent.write_text("plan: .claude/plans/w.md\n", encoding="utf-8")

    def _raises_rc(thunk):
        try:
            thunk()
        except Refusal as exc:
            return exc.rc
        return OK

    def _raises_msg(thunk):
        try:
            thunk()
        except Refusal as exc:
            return str(exc)
        return ""

    def check(label, thunk, want):
        """⛔ TAKES A CALLABLE, NOT A VALUE. With an eager argument, a mutation that makes the code
        RAISE kills the suite before this line runs, so it goes red with no `[FAIL] <case>` line
        and `check-plan-code.parse_fail_names` can attribute the mutation to nothing. Evaluating
        inside the try turns a crash into a NAMED failure, which is the report-format contract.
        """
        nonlocal ok, fail
        try:
            got = thunk()
        except Exception as exc:                      # noqa: BLE001 - a raise IS the failure here
            fail += 1
            print(f"[FAIL] {label}: got {f'raised {type(exc).__name__}: {exc}'!r} want {want!r}")
            return
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    def raises(label, thunk, exc_type, fragment=""):
        """⛔ EVERY failure line here is `[FAIL] <label>: got <x> want <y>`, and that is the
        HARNESS's grammar, not a house style. `check-plan-code.parse_fail_names` truncates a
        `[FAIL]` line at its LAST `": got "` to recover the case name; a line reading
        `[FAIL] <label>: returned …` yields the whole sentence as the name instead, and the
        mutation that this case caught is then reported UNATTRIBUTABLE. Measured 2026-09-29: six
        of this file's 39 mutations came back "caught by something else" for exactly that reason.
        """
        nonlocal ok, fail
        try:
            got = thunk()
        except exc_type as exc:
            if fragment and fragment not in str(exc):
                fail += 1
                print(f"[FAIL] {label}: got {str(exc)!r} want a message containing "
                      f"{fragment!r}")
                return
            ok += 1
            return
        except Exception as exc:                      # noqa: BLE001
            fail += 1
            print(f"[FAIL] {label}: got {f'raised {type(exc).__name__}: {exc}'!r} "
                  f"want {f'a raised {exc_type.__name__}'!r}")
            return
        fail += 1
        print(f"[FAIL] {label}: got {got!r} want {f'a raised {exc_type.__name__}'!r}")

    # ── the plan ────────────────────────────────────────────────────────────────────────
    PLAN = (
        "# demo\n\n"
        "### Task 1: Record the measurements\n\n"
        "- [x] **Step 1 of 3** — Record the measurements\n"
        "  - **Doing:** committing the recall@k ceiling and the latency probe\n"
        "  - **Why:** an unrecorded measurement is re-derived wrongly\n\n"
        "### Task 2: Build the matcher\n\n"
        "- [ ] **Step 2 of 3** — Build the matcher\n"
        "  - **Doing:** scripts/recall-llm.py, one call per plan at arm time\n"
        "  - **Why:** 6.41s per call\n\n"
        "### Task 3: Wire the caller\n\n"
        "- [ ] **Step 3 of 3** — Wire the caller\n"
        "  - **Doing:** the arm-time hook plus a self-test\n"
        "  - **Why:** a guard needs a caller\n")
    TITLE_ONLY = ("### Task 1: Pad the corpus\n\n- [ ] **Step 1 of 2** — Pad the corpus to 1000\n\n"
                  "### Task 2: Re-run\n\n- [ ] **Step 2 of 2** — Re-run the 80-item probe\n")

    check("plan_steps reads every step, ticked and unticked alike",
          lambda: [n for n, _ in plan_steps(PLAN)], [1, 2, 3])
    check("plan_steps takes the Doing line as the situation",
          lambda: plan_steps(PLAN)[1][1],
          "scripts/recall-llm.py, one call per plan at arm time")
    check("plan_steps does not take the Why line",
          lambda: any("6.41s per call" in s for _, s in plan_steps(PLAN)), False)
    check("plan_steps numbers by the STEP, not by position in the file",
          lambda: plan_steps("### T\n\n- [ ] **Step 7 of 9** — x\n  - **Doing:** y\n")[0][0], 7)
    check("plan_steps falls back to the step TITLE when there is no Doing line",
          lambda: plan_steps(TITLE_ONLY)[0][1], "Pad the corpus to 1000")
    check("plan_steps on a file with no steps is empty, not an error",
          lambda: plan_steps("# just prose\n\nnothing here is a checkbox.\n"), [])
    check("plan_steps does not read a ticked step's Doing line into its neighbour",
          lambda: plan_steps(PLAN)[0][1],
          "committing the recall@k ceiling and the latency probe")

    check("plan_verdict passes a real plan", lambda: plan_verdict(plan_steps(PLAN))[0], OK)
    check("plan_verdict refuses a plan with no recognisable step as UNREADABLE, not CANNOT RUN",
          lambda: plan_verdict([])[0], UNREADABLE_PLAN)
    check("plan_verdict names WHICH steps have no situation",
          lambda: "[4]" in plan_verdict([(4, "")])[1], True)
    check("plan_verdict refuses a step whose situation is empty",
          lambda: plan_verdict([(1, "a real one"), (2, "")])[0], UNREADABLE_PLAN)

    check("first_unticked is the first UNTICKED step, not the first step",
          lambda: first_unticked(PLAN), 2)
    check("first_unticked is None when every box is ticked",
          lambda: first_unticked(PLAN.replace("- [ ]", "- [x]")), None)
    check("first_unticked on a plan whose FIRST box is open",
          lambda: first_unticked(TITLE_ONLY), 1)

    check("paused reads a paused sentinel", lambda: paused("plan: p.md\npaused: CI is red\n"), True)
    check("paused is False for a live sentinel", lambda: paused("plan: p.md\narmed: now\n"), False)
    check("paused ignores the word inside a REASON, because it is anchored to the line start",
          lambda: paused("plan: p.md\nreason: the paused: thread over there\n"), False)

    check("sentinel_plan reads the path",
          lambda: sentinel_plan("plan: .claude/plans/x.md\narmed: now\n"), ".claude/plans/x.md")
    check("sentinel_plan is None when no plan is named",
          lambda: sentinel_plan("armed: now\n"), None)

    # ── the corpus ──────────────────────────────────────────────────────────────────────
    FM = ('---\nname: a-check-result-is-not-the-claim\n'
          'description: "FIRES-WHEN: about to quote a green check as evidence — ⭐⭐ a green check '
          'says nothing about the BASE"\nmetadata:\n  type: feedback\n---\n\nbody\n')
    check("frontmatter_description unquotes the value",
          lambda: frontmatter_description(FM).startswith("FIRES-WHEN: about to quote"), True)
    check("frontmatter_description is None with no frontmatter",
          lambda: frontmatter_description("# just a heading\n"), None)
    check("frontmatter_description is None when the block carries no description",
          lambda: frontmatter_description("---\nname: x\n---\n\nbody\n"), None)
    check("frontmatter_description reads only the LEADING block, never a --- rule further down",
          lambda: frontmatter_description(
              "# heading\n\n---\ndescription: FIRES-WHEN: a decoy\n---\n"), None)
    check("frontmatter_description reads an UNQUOTED value too",
          lambda: frontmatter_description("---\ndescription: FIRES-WHEN: scoring a matcher\n---\n"),
          "FIRES-WHEN: scoring a matcher")

    check("parse_trigger strips the trailing em-dash commentary",
          lambda: parse_trigger("FIRES-WHEN: about to open a PR — PR #324 MERGED (af4d9033)"),
          "about to open a PR")
    check("parse_trigger keeps a trigger that has no em-dash at all",
          lambda: parse_trigger("FIRES-WHEN: using .abortSignal() with postgrest-js"),
          "using .abortSignal() with postgrest-js")
    check("parse_trigger requires the FIRES-WHEN prefix",
          lambda: parse_trigger("PR #324 MERGED (af4d9033)"), None)
    check("parse_trigger returns None for an empty trigger",
          lambda: parse_trigger("FIRES-WHEN:  — only commentary"), None)

    check("corpus_verdict refuses an empty directory", lambda: corpus_verdict(0, 0)[0], CANNOT_RUN)
    check("corpus_verdict refuses files that carry no trigger",
          lambda: corpus_verdict(0, 144)[0], CANNOT_RUN)
    check("corpus_verdict passes a real corpus", lambda: corpus_verdict(144, 145)[0], OK)
    check("the no-files message and the no-triggers message are different sentences",
          lambda: corpus_verdict(0, 0)[1] == corpus_verdict(0, 7)[1], False)
    check("the no-triggers message reports how many files were read",
          lambda: "7 memory file(s) read" in corpus_verdict(0, 7)[1], True)
    check("the empty-directory refusal says the directory held no entry files",
          lambda: "ZERO entry files" in corpus_verdict(0, 0)[1], True)

    import tempfile
    def _corpus_dir(td):
        d = Path(td)
        (d / "a-side-job-gets-a-name-first.md").write_text(
            '---\ndescription: "FIRES-WHEN: something arrives mid-session that is not the '
            'thread you are on — ⭐ slug + branch first"\n---\n\nbody\n', encoding="utf-8")
        (d / "no-trigger-yet.md").write_text(
            "---\ndescription: an old-style summary with no trigger\n---\n\nbody\n",
            encoding="utf-8")
        (d / "MEMORY.md").write_text(
            '---\ndescription: "FIRES-WHEN: never — this is the index"\n---\n\nrows\n',
            encoding="utf-8")
        return d

    with tempfile.TemporaryDirectory() as td:
        d = _corpus_dir(td)
        check("load_triggers names entries by their filename stem",
              lambda: [n for n, _ in load_triggers(d)], ["a-side-job-gets-a-name-first"])
        check("load_triggers keeps the trigger text",
              lambda: load_triggers(d)[0][1],
              "something arrives mid-session that is not the thread you are on")
        check("memory_files EXCLUDES MEMORY.md, which is the index and not an entry",
              lambda: [p.name for p in memory_files(d)],
              ["a-side-job-gets-a-name-first.md", "no-trigger-yet.md"])
        check("memory_files counts a file with no trigger, so the two failures stay distinct",
              lambda: len(memory_files(d)) - len(load_triggers(d)), 1)

    # A SECOND corpus and an EMPTY one, so `d` is not a constant any case could be blind to —
    # `check-fixture-variation.py` reported it unvaried, which is the r6 class: the rule under
    # test reads the directory and every case handed it the same one.
    with tempfile.TemporaryDirectory() as td2:
        other = Path(td2)
        (other / "running-codex.md").write_text(
            '---\ndescription: "FIRES-WHEN: a Codex review has gone quiet — DOUBLE the timeout"\n'
            '---\n\nbody\n', encoding="utf-8")
        check("load_triggers reads the directory it is GIVEN — another corpus, another entry",
              lambda: [n for n, _ in load_triggers(other)], ["running-codex"])
        check("memory_files reads the directory it is GIVEN",
              lambda: [p.name for p in memory_files(other)], ["running-codex.md"])
    with tempfile.TemporaryDirectory() as td3:
        empty = Path(td3)
        check("load_triggers over an EMPTY directory is an empty list, which corpus_verdict then "
              "refuses rather than serving as nothing-fires",
              lambda: load_triggers(empty), [])
        check("memory_files over an empty directory is an empty list",
              lambda: memory_files(empty), [])

    # ── the prompt ──────────────────────────────────────────────────────────────────────
    TRIGS = [("a-check-result-is-not-the-claim", "about to quote a green check as evidence"),
             ("a-side-job-gets-a-name-first", "something arrives that is not the thread you are on"),
             ("running-codex", "a Codex review has gone quiet")]
    STEPS = [(2, "opening the PR for backlog #192"), (3, "wiring the arm-time hook")]
    P = build_prompt(TRIGS, STEPS)

    check("build_prompt sends EVERY trigger, never a shortlist",
          lambda: all(name in build_prompt(TRIGS, STEPS) for name, _ in TRIGS), True)
    check("build_prompt sends every step",
          lambda: all(s in build_prompt(TRIGS, STEPS) for _, s in STEPS), True)
    check("build_prompt numbers a situation by its STEP NUMBER, not from 1",
          lambda: "\n2. opening the PR for backlog #192" in build_prompt(TRIGS, STEPS), True)
    check("build_prompt declares how many triggers it sent",
          lambda: "3 TRIGGERS" in build_prompt(TRIGS, STEPS), True)
    check("build_prompt's example key is a real step number, so the format example cannot "
          "suggest a step that was not asked about",
          lambda: '{"2": "NONE"}' in build_prompt(TRIGS, STEPS), True)
    check("build_prompt reads its `triggers` argument — a different corpus makes a different "
          "prompt",
          lambda: "running-codex" in build_prompt(TRIGS[:1], STEPS), False)
    check("build_prompt reads its `steps` argument — a different plan makes a different prompt",
          lambda: "wiring the arm-time hook" in build_prompt(TRIGS, STEPS[:1]), False)
    # The five load-bearing clauses of the measured prompt. LITERALS, not comparisons against
    # PROMPT: a case that reads the template cannot notice the template changing.
    check("the prompt says to match on MEANING rather than shared words",
          lambda: "Match on MEANING, not on shared words" in P, True)
    check("the prompt makes NONE a first-class answer",
          lambda: "NONE is a first-class answer" in P, True)
    check("the prompt withholds the proportion that match",
          lambda: "is NOT disclosed to you" in P, True)
    check("the prompt calls a thematically adjacent match an ERROR, worse than NONE",
          lambda: "merely thematically adjacent, is an ERROR" in P, True)
    check("the prompt carries the would-this-change-what-they-do-next test",
          lambda: "WOULD THIS CHANGE WHAT THE PERSON DOES NEXT" in P, True)
    check("the prompt says routine engineering work usually matches nothing",
          lambda: "Routine engineering work usually matches nothing" in P, True)

    # ── the response ────────────────────────────────────────────────────────────────────
    NAMES = [n for n, _ in TRIGS]
    check("parse_response reads a bare JSON object",
          lambda: parse_response('{"2": "running-codex", "3": "NONE"}', [2, 3], NAMES),
          {2: "running-codex", 3: "NONE"})
    check("parse_response tolerates a ```json fence",
          lambda: parse_response('```json\n{"2": "NONE", "3": "NONE"}\n```', [2, 3], NAMES),
          {2: "NONE", 3: "NONE"})
    check("parse_response tolerates prose either side of the object",
          lambda: parse_response('Here you go:\n{"9": "NONE"}\nHope that helps.', [9], NAMES),
          {9: "NONE"})
    raises("parse_response REJECTS an entry name that is not in the corpus",
           lambda: parse_response('{"2": "a-plausible-invention"}', [2], NAMES),
           ResponseRejected, "not an entry in this corpus")
    raises("parse_response REJECTS a reply that is missing a step",
           lambda: parse_response('{"2": "NONE"}', [2, 3], NAMES),
           ResponseRejected, "missing ['3']")
    raises("parse_response REJECTS a reply carrying a step nobody asked about",
           lambda: parse_response('{"2": "NONE", "4": "NONE"}', [2], NAMES),
           ResponseRejected, "unexpected ['4']")
    raises("parse_response REJECTS a reply that is not JSON at all",
           lambda: parse_response("I think step 2 matches running-codex.", [2], NAMES),
           ResponseRejected, "no JSON object")
    raises("parse_response REJECTS malformed JSON rather than salvaging it",
           lambda: parse_response('{"2": "NONE",}', [2], NAMES),
           ResponseRejected, "not valid JSON")
    raises("parse_response REJECTS a bare JSON list, which carries no object at all",
           lambda: parse_response('["NONE"]', [2], NAMES), ResponseRejected, "no JSON object")
    check("parse_response prefers a FENCED object over stray braces in the prose around it",
          lambda: parse_response('I first considered {"9": "x"} here.\n```json\n{"2": "NONE"}\n```',
                                 [2], NAMES), {2: "NONE"})
    raises("parse_response REJECTS a non-string answer",
           lambda: parse_response('{"2": 1}', [2], NAMES), ResponseRejected, "not an entry name")
    check("parse_response reads its `valid_names` argument — the same reply is accepted under a "
          "corpus that holds the name",
          lambda: parse_response('{"2": "a-plausible-invention"}', [2],
                                 ["a-plausible-invention"]), {2: "a-plausible-invention"})

    # ── the cache ───────────────────────────────────────────────────────────────────────
    check("plan_fingerprint changes when a Doing line is edited",
          lambda: plan_fingerprint(PLAN) == plan_fingerprint(
              PLAN.replace("one call per plan", "one call per step")), False)
    # ⛔ THE CASE THAT CAUGHT THE FIRST VERSION OF THIS FUNCTION. It hashed the file's bytes, which
    # every `--tick` rewrites, so the cache it protects would have been thrown away — and a 6.41s
    # call bought — on every single step. The docstring claimed the opposite in the same commit.
    check("plan_fingerprint is UNCHANGED by ticking a box, so a tick does not buy a new call",
          lambda: plan_fingerprint(PLAN) == plan_fingerprint(PLAN.replace("- [ ]", "- [x]")),
          True)
    check("plan_fingerprint changes when a step is ADDED",
          lambda: plan_fingerprint(PLAN) == plan_fingerprint(
              PLAN + "- [ ] **Step 4 of 4** — New\n  - **Doing:** a fourth situation\n"), False)
    check("plan_fingerprint changes when the step NUMBERS change but the text does not",
          lambda: plan_fingerprint(PLAN) == plan_fingerprint(
              PLAN.replace("**Step 3 of 3**", "**Step 9 of 3**")), False)
    check("plan_fingerprint is stable for identical text",
          lambda: plan_fingerprint(PLAN) == plan_fingerprint(PLAN[:]), True)
    check("plan_fingerprint ignores prose around the steps — a comment added to the plan does "
          "not invalidate the cache",
          lambda: plan_fingerprint(PLAN) == plan_fingerprint(
              PLAN.replace("# demo", "# demo\n\nsome notes a human added")), True)
    check("cache_path is one file per plan stem",
          lambda: (cache_path("llm-recall-matcher").name, cache_path("slice-a").name),
          ("llm-recall-matcher.json", "slice-a.json"))
    check("cache_path puts the cache under .claude/recall-cache",
          lambda: cache_path("x").parent.name, "recall-cache")

    DOC = cache_document("p.md", PLAN, {1: NONE, 2: "running-codex", 3: NONE},
                         {"running-codex": "a Codex review has gone quiet"}, 144,
                         "2026-09-29T00:00:00+00:00")
    check("cache_document stores the plan's fingerprint alongside the answers",
          lambda: DOC["fingerprint"], plan_fingerprint(PLAN))
    check("cache_document keys picks by step number as strings",
          lambda: sorted(DOC["picks"]), ["1", "2", "3"])
    check("cache_document caches the picked entry's trigger, so --fire needs no corpus",
          lambda: DOC["triggers"]["running-codex"], "a Codex review has gone quiet")
    check("cache_document records the corpus size the answers were chosen from",
          lambda: DOC["corpus_size"], 144)
    check("cache_document records which model answered",
          lambda: DOC["model"], MODEL)
    # A SECOND document, differing in EVERY argument, because `check-fixture-variation.py` reported
    # all six of `cache_document`'s parameters passed one value each — every clause that reads one
    # was unguarded, however many cases read the result.
    DOC2 = cache_document(".claude/plans/slice-a.md", TITLE_ONLY, {1: NONE, 2: NONE},
                          {}, 300, "2026-10-01T09:30:00+00:00")
    check("cache_document records the plan it was armed FOR, not a fixed name",
          lambda: DOC2["plan"], ".claude/plans/slice-a.md")
    check("cache_document fingerprints the plan text it was GIVEN",
          lambda: DOC2["fingerprint"], plan_fingerprint(TITLE_ONLY))
    check("two cache documents for two different plans do not share a fingerprint",
          lambda: DOC["fingerprint"] == DOC2["fingerprint"], False)
    check("cache_document keys the picks it was GIVEN — a two-step plan has two",
          lambda: sorted(DOC2["picks"]), ["1", "2"])
    check("cache_document caches NO triggers when no step matched anything",
          lambda: DOC2["triggers"], {})
    check("cache_document records the corpus size it was GIVEN",
          lambda: DOC2["corpus_size"], 300)
    check("cache_document records the arming time it was GIVEN",
          lambda: DOC2["armed"], "2026-10-01T09:30:00+00:00")

    check("cache_verdict passes its own plan", lambda: cache_verdict(DOC, PLAN)[0], OK)
    check("cache_verdict REFUSES a cache armed against an edited situation",
          lambda: cache_verdict(DOC, PLAN.replace("arm time", "fire time"))[0], STALE_CACHE)
    check("cache_verdict SERVES a plan whose only change is a ticked box",
          lambda: cache_verdict(DOC, PLAN.replace("- [ ]", "- [x]"))[0], OK)
    check("cache_verdict REFUSES a plan that has gained a step",
          lambda: cache_verdict(DOC, PLAN + "- [ ] **Step 4 of 4** — New\n"
                                            "  - **Doing:** a fourth situation\n")[0], STALE_CACHE)
    check("cache_verdict quotes BOTH fingerprints, so the reader can see which side moved",
          lambda: (DOC["fingerprint"] in cache_verdict(DOC, PLAN.replace("arm", "fire"))[1]
                   and plan_fingerprint(PLAN.replace("arm", "fire"))
                   in cache_verdict(DOC, PLAN.replace("arm", "fire"))[1]), True)
    check("cache_verdict REFUSES a cache with no fingerprint at all",
          lambda: cache_verdict({"picks": {"2": NONE}}, PLAN)[0], STALE_CACHE)
    check("a stale-cache verdict is NOT the same code as a cannot-run one",
          lambda: STALE_CACHE == CANNOT_RUN, False)

    # ── cached_entry_verdict (4). Added 2026-09-29 after `--fire` was measured serving a cached
    # entry under a redirected HOME, i.e. without the corpus that name has to resolve in.
    # ⚠ Each case varies a DIFFERENT argument, so none is satisfied by a constant the others supply.
    check("cached_entry_verdict serves an entry the corpus still holds",
          lambda: cached_entry_verdict("a-test-that-cannot-fail", True, True)[0], OK)
    check("cached_entry_verdict REFUSES an entry the corpus no longer holds",
          lambda: cached_entry_verdict("renamed-away", True, False)[0], STALE_CACHE)
    check("...and it NAMES the entry, so the reader knows which one vanished",
          lambda: "renamed-away" in cached_entry_verdict("renamed-away", True, False)[1], True)
    check("a missing corpus DIRECTORY is CANNOT RUN, not STALE — the world is wrong, not the cache",
          lambda: cached_entry_verdict("a-shim-can-fail-in-both-directions", False, False)[0],
          CANNOT_RUN)
    check("a NONE answer needs no corpus, so it is served even when the corpus is gone",
          lambda: cached_entry_verdict(None, False, False)[0], OK)

    # ── M4 · the nag is deduped, the rc is not (4) ──────────────────────────────────────
    # ⛔ `--arm` is manual and paid, so "never armed" is the DEFAULT state of every plan. The
    # dedupe sat after `fire_output` — reached only on a correct match — so the USEFUL message was
    # rate-limited and the nag was not. Backwards.
    def _nag(marker_dir, current):
        return nag_once(Path(marker_dir) / ".last-nagged", current)

    check("the nag is said the FIRST time for a step",
          lambda: _nag_probe("plan-a:1", "plan-a:1", first=True), True)
    check("...and STAYS SILENT the second time for the same step",
          lambda: _nag_probe("plan-a:1", "plan-a:1", first=False), False)
    check("a DIFFERENT step nags again, because the situation has changed",
          lambda: _nag_probe("plan-a:1", "plan-a:2", first=False), True)
    check("an unwritable marker directory lets the nag REPEAT rather than vanish",
          lambda: _nag_unwritable(), True)

    # ── H3 · duplicate step numbers (4) ─────────────────────────────────────────────────
    _dup = ("- [ ] **Step 1 of 2** — A\n  - **Doing:** ALPHA\n"
            "- [ ] **Step 2 of 2** — B\n  - **Doing:** BETA\n"
            "- [ ] **Step 1 of 2** — C\n  - **Doing:** GAMMA\n")
    _uniq = ("- [ ] **Step 1 of 2** — A\n  - **Doing:** ALPHA\n"
             "- [ ] **Step 2 of 2** — B\n  - **Doing:** BETA\n")
    check("a plan whose step numbers REPEAT is unreadable — a cached answer could bind to two moments",
          lambda: plan_verdict(plan_steps(_dup))[0], UNREADABLE_PLAN)
    check("...and it names WHICH numbers repeat, since the author must renumber them",
          lambda: "[1]" in plan_verdict(plan_steps(_dup))[1], True)
    check("a plan numbered uniquely is fine — the rule is duplication, not repetition of shape",
          lambda: plan_verdict(plan_steps(_uniq))[0], OK)
    check("parse_response REJECTS a reply that answers one step twice",
          lambda: _raises_rc(lambda: parse_response('{"1": "NONE", "2": "a", "2": "NONE"}',
                                                    [1, 2], ["a"])), BAD_RESPONSE)
    check("...and it names WHICH step was answered twice",
          lambda: "'2'" in _raises_msg(lambda: parse_response('{"1": "NONE", "2": "a", "2": "NONE"}',
                                                              [1, 2], ["a"])), True)
    check("parse_response compares SEQUENCES: a duplicate key cannot satisfy three situations",
          lambda: _raises_rc(lambda: parse_response('{"1": "NONE", "2": "NONE", "2": "NONE"}',
                                                    [1, 2, 3], [])), BAD_RESPONSE)

    # ── H2 · the trigger text shown is the LIVE one (4) ─────────────────────────────────
    check("no corpus is UNREADABLE, so the cached text is used",
          lambda: live_trigger_for("x", None), (LIVE_UNREADABLE, None))
    check("live_trigger_for reads the trigger the corpus holds NOW",
          lambda: _live_trigger_probe('---\ndescription: "FIRES-WHEN: reading it live"\n---\n'),
          (LIVE_OK, "reading it live"))
    check("an entry whose file cannot be read is UNREADABLE — bookkeeping, so the match survives",
          lambda: _live_trigger_probe(b"\xff\xfe not utf-8"), (LIVE_UNREADABLE, None))
    # ⛔ ROUND 2 #1: these two statuses were ONE bare None, so the caller fell back to the cached
    # sentence for both and an entry rewritten without frontmatter still printed the old wording —
    # H2's defect surviving H2's fix. They need OPPOSITE responses, so they are distinct values.
    check("an entry with no FIRES-WHEN is NO-TRIGGER, which is material, not bookkeeping",
          lambda: _live_trigger_probe('---\ndescription: "no trigger here"\n---\n'),
          (LIVE_NO_TRIGGER, None))
    check("the three statuses are all distinct, so no two conditions share a meaning",
          lambda: len({LIVE_OK, LIVE_UNREADABLE, LIVE_NO_TRIGGER}), 3)

    # ── decode_verdict / H1 (6) ─────────────────────────────────────────────────────────
    # ⛔ Seven paths exited 1 — a code this contract does not define — and the hook's catch-all
    # swallowed all of them into silence. Four were files read as UTF-8 with no named failure.
    _ude = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
    check("no error is not a refusal", lambda: decode_verdict(None, "plan file", "/p")[0], OK)
    check("an undecodable file is CANNOT RUN, never an exit 1 traceback",
          lambda: decode_verdict(_ude, "plan file", "/p")[0], CANNOT_RUN)
    check("...and it says the file is not valid UTF-8, so the reader knows what to fix",
          lambda: "not valid UTF-8" in decode_verdict(_ude, "plan file", "/p")[1], True)
    check("...and it names WHICH file and WHERE, since four different ones reach it",
          lambda: ("recall cache" in decode_verdict(_ude, "recall cache", "/c/x.json")[1]
                   and "/c/x.json" in decode_verdict(_ude, "recall cache", "/c/x.json")[1]), True)
    check("an OSError is named by its CLASS, not mislabelled as an encoding problem",
          lambda: ("PermissionError" in decode_verdict(PermissionError(13, "denied"), "plan file", "/p")[1]
                   and "not valid UTF-8" not in decode_verdict(PermissionError(13, "denied"), "plan file", "/p")[1]),
          True)
    check("...and it insists this is not 'nothing applies' — the whole point of naming it",
          lambda: "not 'nothing applies'" in decode_verdict(_ude, "sentinel", "/s")[1], True)
    # ⛔ ROUND 2: an rc-3 refusal carrying a "CANNOT RUN" sentence makes the message contradict the
    # code, which is the same defect as code contradicting a docstring.
    check("the sentence's label can match the rc the caller will raise",
          lambda: decode_verdict(_ude, "recall cache", "/c", "STALE CACHE")[1].startswith("STALE CACHE:"),
          True)
    check("...and it still defaults to CANNOT RUN for the readers that are one",
          lambda: decode_verdict(_ude, "plan file", "/p")[1].startswith("CANNOT RUN:"), True)

    # ── parse_cache below the top level / H1(c)(d) (3) ──────────────────────────────────
    check("a cache whose `picks` is not an object is STALE, not an exit-1 traceback",
          lambda: _raises_rc(lambda: parse_cache('{"picks": 5}')), STALE_CACHE)
    check("a cache whose `triggers` is a list is STALE too",
          lambda: _raises_rc(lambda: parse_cache('{"triggers": ["x"]}')), STALE_CACHE)
    check("...and it names WHICH key is wrong, not merely that something is",
          lambda: "'picks'" in _raises_msg(lambda: parse_cache('{"picks": 5}')), True)

    # ── outside_repo (4). Added 2026-09-30 after `call_model`'s SECOND real call was contaminated
    # by this repo's own hooks: launched with the repo as cwd, `claude -p` loaded
    # `.claude/settings.json`, hit the Stop guard on an armed plan, and answered with 1,278 chars of
    # prose instead of JSON. The first call had succeeded in the same state, so it is
    # non-deterministic. `call_model` has no case, so the PROPERTY is extracted to be testable.
    check("a temp directory elsewhere is outside the repo",
          lambda: outside_repo("/tmp/somewhere-else", "/repo/root"), True)
    check("a path INSIDE the repo is NOT outside it",
          lambda: outside_repo("/repo/root/docs/memory", "/repo/root"), False)
    check("the repo root is not outside ITSELF — the boundary is inclusive",
          lambda: outside_repo("/repo/root", "/repo/root"), False)
    check("a sibling whose name merely PREFIXES the repo path is outside it",
          lambda: outside_repo("/repo/root-other", "/repo/root"), True)
    # ⛔ `repo` was the SAME value in all four cases above, so nothing could tell it apart from a
    # constant and the clause reading it was unguarded. Caught by `check-fixture-variation.py`, for
    # the second time in this session — the same defect class, in the same session, after I had
    # already fixed it once in `check-memory-link.py`. These two vary it in both directions.
    check("the SAME candidate is inside one repo root and outside another",
          lambda: (outside_repo("/a/b/c", "/a"), outside_repo("/a/b/c", "/z")), (False, True))
    check("a deeper repo root than the candidate makes it outside",
          lambda: outside_repo("/a/b", "/a/b/c/d"), True)

    # ── the prompt's RUBRIC (2). Added 2026-09-30 after the scaling probes disagreed.
    # ⛔ Two independent matchers, same corpus family, differed on 5 of 60 ordinary situations and
    # ALL FIVE sat on one boundary: is a lesson the action ALREADY EMBODIES a match? One invented
    # the rule "already doing it -> NONE" and the other never had it. An undefined rubric at the
    # mechanism's most frequent decision is non-determinism, so the rule is stated in the prompt now.
    check("the prompt tells the matcher that an already-embodied lesson is NONE",
          lambda: "ALREADY DOING what the lesson advises" in build_prompt(
              [("e", "a trigger")], [(1, "a situation")]), True)
    check("...and still says a merely-adjacent match is an error, which is the other half",
          lambda: "thematically adjacent" in build_prompt(
              [("e", "a trigger")], [(1, "a situation")]), True)

    # ── should_surface / surface_marker (4) ─────────────────────────────────────────────
    check("should_surface prints a step not yet surfaced",
          lambda: should_surface(None, surface_marker("plan-a", 2)), True)
    check("should_surface STAYS SILENT on the step it already surfaced",
          lambda: should_surface(surface_marker("plan-a", 2), surface_marker("plan-a", 2)), False)
    check("a tick — the same plan, the NEXT step — surfaces again",
          lambda: should_surface(surface_marker("plan-b", 3), surface_marker("plan-b", 4)), True)
    check("the same step NUMBER under a DIFFERENT plan is a different situation",
          lambda: should_surface(surface_marker("plan-c", 1), surface_marker("plan-d", 1)), True)

    check("parse_cache reads a real cache document",
          lambda: parse_cache(json.dumps(DOC))["fingerprint"], DOC["fingerprint"])
    raises("parse_cache REFUSES a half-written cache file rather than exiting on a traceback",
           lambda: parse_cache('{"picks": {"2": "NON'), StaleCache, "not valid JSON")
    raises("parse_cache REFUSES a cache file that holds a list",
           lambda: parse_cache('[{"picks": {}}]'), StaleCache, "holds a list")
    check("parse_cache reads the TEXT it is given — a second document round-trips too",
          lambda: parse_cache(json.dumps(DOC2))["corpus_size"], 300)

    check("lookup returns the entry for a matched step", lambda: lookup(DOC, 2), "running-codex")
    check("lookup returns None for a step the model answered NONE for",
          lambda: lookup(DOC, 3), None)
    raises("lookup RAISES for a step that is absent, which is not the same as NONE",
           lambda: lookup(DOC, 9), StaleCache, "step 9 is not in this cache")
    check("lookup reads its `step` argument — two steps give two different answers",
          lambda: lookup(DOC, 2) == lookup(DOC, 3), False)
    check("lookup reads its `cache` argument — the same step under another cache differs",
          lambda: lookup({"picks": {"2": "a-side-job-gets-a-name-first"}}, 2),
          "a-side-job-gets-a-name-first")

    # ── the output ──────────────────────────────────────────────────────────────────────
    check("render names the entry", lambda: "running-codex" in render(
        "running-codex", "a Codex review has gone quiet"), True)
    check("render prints the TRIGGER, not only the name",
          lambda: "FIRES-WHEN: a Codex review has gone quiet" in render(
              "running-codex", "a Codex review has gone quiet"), True)
    check("render reads its `entry` argument",
          lambda: "a-side-job-gets-a-name-first" in render("a-side-job-gets-a-name-first", "t"),
          True)
    check("fire_output is EMPTY for a NONE answer",
          lambda: fire_output(None, "a trigger that must not be printed"), "")
    check("fire_output renders a real match",
          lambda: fire_output("running-codex", "a Codex review has gone quiet").splitlines()[1]
          .strip(), "running-codex")
    check("fire_output says the trigger was not cached rather than printing an empty line",
          lambda: "(trigger not cached)" in fire_output("running-codex", None), True)

    # ── the rc contract ─────────────────────────────────────────────────────────────────
    check("OK is 0, and the three refusals are distinct non-zero codes",
          lambda: sorted({OK, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE}), [0, 2, 3, 4])
    check("a ResponseRejected carries the RESPONSE code, not the generic one",
          lambda: ResponseRejected("x").rc, BAD_RESPONSE)
    check("a StaleCache carries the STALE code", lambda: StaleCache("x").rc, STALE_CACHE)
    check("a bare Refusal is CANNOT RUN", lambda: Refusal("x").rc, CANNOT_RUN)
    check("an UnreadablePlan carries its OWN code, not CANNOT RUN — the hook must route on it",
          lambda: (UnreadablePlan("x").rc, UnreadablePlan("x").rc == CANNOT_RUN),
          (UNREADABLE_PLAN, False))
    check("the five rc values are all distinct, so no two conditions share a meaning",
          lambda: sorted({OK, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, UNREADABLE_PLAN}),
          [0, 2, 3, 4, 5])
    # ⛔ B1, end to end. `first_unticked` returns None for BOTH worlds; only `do_fire` consulting
    # `plan_verdict` can tell them apart, and that call was what the Blocking said was missing.
    check("an unreadable plan and a FINISHED plan both give first_unticked None — the conflation",
          lambda: (first_unticked("- [ ] **Step 1: no N of M**\n"),
                   first_unticked("- [x] **Step 1 of 1** — done\n  - **Doing:** a situation\n")),
          (None, None))
    check("...but plan_verdict separates them, which is why do_fire must ask it first",
          lambda: (plan_verdict(plan_steps("- [ ] **Step 1: no N of M**\n"))[0],
                   plan_verdict(plan_steps("- [x] **Step 1 of 1** — done\n"
                                           "  - **Doing:** a situation\n"))[0]),
          (UNREADABLE_PLAN, OK))

    # ── do_fire's WIRING, driven end to end (1) ──────────────────────────────────────────
    # ⛔ THE ONLY CASE THAT CROSSES THE IO BOUNDARY, and it exists because unit coverage does not
    # compose: `cached_entry_verdict` is covered five ways, and deleting the five lines in `do_fire`
    # that CALL it left every one of those cases green. A mutation of a call site is invisible to a
    # test of the callee. This builds a whole world — repo root, sentinel, plan, cache, and a corpus
    # that does NOT hold the cached entry — and asserts the refusal comes out of `do_fire` itself.
    def _fire_on_a_corpus_missing_its_entry():
        import os
        with tempfile.TemporaryDirectory() as td4:
            root, home = Path(td4) / "repo", Path(td4) / "home"
            plan = root / ".claude" / "plans" / "w.md"
            plan.parent.mkdir(parents=True)
            plan.write_text("### Task 1: Go\n\n- [ ] **Step 1 of 1** — Go\n"
                            "  - **Doing:** a situation\n", encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text(
                "plan: .claude/plans/w.md\n", encoding="utf-8")
            cache_dir = root / ".claude" / "recall-cache"
            cache_dir.mkdir()
            (cache_dir / "w.json").write_text(json.dumps(cache_document(
                ".claude/plans/w.md", plan.read_text(encoding="utf-8"),
                {1: "an-entry-since-renamed"}, {"an-entry-since-renamed": "a trigger"},
                1, "2026-09-29T00:00:00+00:00")), encoding="utf-8")
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
            corpus = home / ".claude" / "projects" / slug / "memory"
            corpus.mkdir(parents=True)
            (corpus / "some-other-entry.md").write_text(
                "---\ndescription: \"FIRES-WHEN: doing something else\"\n---\nbody\n",
                encoding="utf-8")
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"],
                     os.environ.get("HOME"))
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = cache_dir
                os.environ["HOME"] = str(home)
                return do_fire()
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved[:3]
                if saved[3] is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved[3]

    raises("do_fire itself refuses a cached entry the live corpus no longer holds",
           _fire_on_a_corpus_missing_its_entry, StaleCache, "no longer holds")

    # ── B1's WIRING, driven end to end (1) ──────────────────────────────────────────────
    # ⛔ Every case above is pure, and B1 was a MISSING CALL: `plan_verdict` was correct and
    # `do_fire` never asked it. A callee's tests cannot see that. This arms a plan in the shape
    # `begin-plan.py`'s own parser accepts — and 87 committed plans use — and asserts the refusal
    # comes out of `do_fire`, not that a pure function would have returned it.
    def _fire_on_an_unreadable_plan():
        import os
        with tempfile.TemporaryDirectory() as td6:
            root = Path(td6) / "repo"
            plan = root / ".claude" / "plans" / "u.md"
            plan.parent.mkdir(parents=True)
            plan.write_text("### Task 1: Write the tests\n\n"
                            "- [ ] **Step 1: Write the tests**\n"
                            "  - **Doing:** writing the failing tests\n", encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text(
                "plan: .claude/plans/u.md\n", encoding="utf-8")
            # ⛔ CACHE_DIR IS SWAPPED HERE TOO, AND ITS ABSENCE MADE THIS CASE AMBIENT. This is a
            # near-copy of `_armed_world`, and when that one gained cache isolation for backlog
            # #202 this one kept the blind spot — the shape this repo has measured seventeen times.
            # MEASURED 2026-09-30: with the real `CACHE_DIR`, `do_fire`'s dedupe read the LIVE
            # `.claude/recall-cache/.last-said` (written minutes earlier by the session's own hook),
            # decided this sentence had already been said, and emptied it — so the case failed on
            # `got ''`. Its outcome depended on whether the hook had fired earlier in the session,
            # which is not a property of the code under test.
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"])
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = root.resolve() / ".claude" / "recall-cache"
                globals()["CACHE_DIR"].mkdir(parents=True, exist_ok=True)
                return do_fire()
            finally:
                (globals()["ROOT"], globals()["SENTINEL"],
                 globals()["CACHE_DIR"]) = saved

    raises("do_fire REFUSES an armed plan it cannot read, instead of exiting 0 in silence",
           _fire_on_an_unreadable_plan, UnreadablePlan, "this cannot read")

    # ── H2 · the MIXED plan, which is worse than a wholly unreadable one (4) ────────────
    # ⛔ Round 1 named this half of B1 and the fold closed only the all-silent half. A plan whose
    # boxes are PARTLY readable loses the unreadable ones silently, leaves a non-empty step list, and
    # hands the reader a LATER step's lesson while they stand at an earlier one — rc 0, no warning.
    # The prompt itself calls that the most expensive failure it can produce.
    _MIXED = ("### Task 1\n\n- [ ] **Step 1: the shape begin-plan accepts**\n"
              "  - **Doing:** GAMMA, where the reader is standing\n"
              "- [ ] **Step 2 of 2** — B\n  - **Doing:** a situation\n")
    _NO_BOXES = "### Task 1\n\njust prose, no checkboxes at all\n"
    check("a plan with boxes this CANNOT read is refused, even though others parsed",
          lambda: plan_verdict(plan_steps(_MIXED), _MIXED)[0], UNREADABLE_PLAN)
    check("...and it counts BOTH, so the reader can see how many vanished",
          lambda: ("2 checkbox(es) are present but only 1" in plan_verdict(plan_steps(_MIXED), _MIXED)[1]),
          True)
    check("without the mixed check it would have ACCEPTED and pointed at the later step",
          lambda: (plan_verdict(plan_steps(_MIXED))[0], first_unticked(_MIXED)), (OK, 2))
    check("a plan with NO boxes at all still gets the no-recognisable-step message",
          lambda: "no recognisable" in plan_verdict(plan_steps(_NO_BOXES), _NO_BOXES)[1], True)

    # ── H5 · the dedupe is at the BOUNDARY, so all eight paths share it (3) ─────────────
    def _twice_on(build):
        import os
        with tempfile.TemporaryDirectory() as tdB:
            root = Path(tdB) / "repo"
            (root / ".claude" / "plans").mkdir(parents=True)
            cd = root / ".claude" / "recall-cache"
            cd.mkdir()
            sent = root / ".claude" / "executing-plan"
            build(root, sent)
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"])
            said = []
            try:
                globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"] = (
                    root.resolve(), sent, cd)
                for _ in range(2):
                    try:
                        do_fire()
                        said.append("")
                    except Refusal as exc:
                        said.append(str(exc))
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved
            return (bool(said[0]), bool(said[1]))

    check("an rc-5 unreadable plan is SAID once and silent after — not only the cache branch",
          lambda: _twice_on(_write_bad_plan), (True, False))
    check("a plan that VANISHED is also deduped, which the per-branch version never covered",
          lambda: _twice_on(lambda r, s: s.write_text("plan: .claude/plans/gone.md\n",
                                                      encoding="utf-8")), (True, False))
    # ⛔ THIS CASE WAS VACUOUS AND THE SWEEP CAUGHT IT. It built TWO separate worlds, each with a
    # fresh marker, so a constant dedupe key was undetectable — the mutation replacing the message
    # hash with a literal SURVIVED. Two different refusals must occur in ONE world, sharing ONE
    # marker, or nothing is being compared.
    def _two_refusals_one_world():
        import os
        with tempfile.TemporaryDirectory() as tdD:
            root = Path(tdD) / "repo"
            (root / ".claude" / "plans").mkdir(parents=True)
            cd = root / ".claude" / "recall-cache"
            cd.mkdir()
            sent = root / ".claude" / "executing-plan"
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"])
            said = []
            try:
                globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"] = (
                    root.resolve(), sent, cd)
                for build in (_write_bad_plan,
                              lambda r, t: t.write_text("armed: yes\n", encoding="utf-8")):
                    build(root, sent)
                    try:
                        do_fire()
                        said.append("")
                    except Refusal as exc:
                        said.append(str(exc))
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved
            return (bool(said[0]), bool(said[1]))

    check("the dedupe is keyed on the MESSAGE, so a DIFFERENT refusal in the SAME world is still said",
          lambda: _two_refusals_one_world(), (True, True))

    # ── H4 · an unreadable entry is announced, not silently cached-over (1) ─────────────
    check("an entry that cannot be read says so, because --arm would refuse this corpus outright",
          lambda: "could not be READ just now" in _fire_with_an_unreadable_entry(), True)

    # ── the BLOCKING from round 2: five ways to be armed-and-unusable, one boundary (5) ─
    # ⛔ rc 5 existed for exactly this and round 1 gave it to ONE of the five ways. The line is the
    # SENTINEL'S EXISTENCE: no sentinel is "nothing armed" (routine, silent, rc 2); a sentinel that
    # exists means a plan IS armed, so every failure to reach a usable one must reach the reader.
    def _armed_world(build, cache=None):
        import os
        with tempfile.TemporaryDirectory() as tdA:
            root = Path(tdA) / "repo"
            (root / ".claude" / "plans").mkdir(parents=True)
            sent = root / ".claude" / "executing-plan"
            if build:
                build(root, sent)
            # ⛔ CACHE_DIR IS SWAPPED TOO, and it was not until backlog #202 needed a case that
            # reaches the cache. Without it `_fire` read the REAL repo's `.claude/recall-cache/`
            # while every other path pointed at the temp root — so any cache-dependent case would
            # have passed or failed for an ambient reason. The existing cases are unaffected: they
            # all refuse before the cache is opened. ⚠ HOME is deliberately NOT swapped, which is
            # what makes the corpus unreachable here: the temp root hashes to a slug that has no
            # corpus, which is exactly #202's world.
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"])
            try:
                globals()["ROOT"], globals()["SENTINEL"] = root.resolve(), sent
                globals()["CACHE_DIR"] = root.resolve() / ".claude" / "recall-cache"
                globals()["CACHE_DIR"].mkdir(parents=True, exist_ok=True)
                if cache is not None:
                    cache(globals()["CACHE_DIR"], root.resolve())
                do_fire()
                return OK
            except Refusal as exc:
                return exc.rc
            finally:
                (globals()["ROOT"], globals()["SENTINEL"],
                 globals()["CACHE_DIR"]) = saved

    check("NO sentinel stays CANNOT RUN — nothing is armed, and silence is correct",
          lambda: _armed_world(None), CANNOT_RUN)
    # ── round 3 H1 — THE CONJUNCTION SURVIVED ON `--arm`, AND THIS IS ITS FALSIFIER ─────────
    # ⛔ #202 split rc 6 out of rc 2 on `--fire` and left `--arm` carrying it — B1's error a third
    # time. The rule is `unanswerable_if_armed`; these cases drive the RULE and then each of its
    # two BOUNDARIES, because a rule with no wiring case is a rule a refactor can silently detach.
    check("a bare CANNOT_RUN inside the armed scope becomes CANNOT ANSWER",
          lambda: unanswerable_if_armed(Refusal("m")).rc, UNANSWERABLE)
    # ⚠ THE FOUR ADJACENT NEGATIVES. Each subclass already says something more specific, and
    # widening the rule to `isinstance` would flatten all five into one — the conjunction again.
    check("...but StaleCache keeps rc 3",
          lambda: unanswerable_if_armed(StaleCache("m")).rc, STALE_CACHE)
    check("...and UnreadablePlan keeps rc 5",
          lambda: unanswerable_if_armed(UnreadablePlan("m")).rc, UNREADABLE_PLAN)
    check("...and ResponseRejected keeps rc 4",
          lambda: unanswerable_if_armed(ResponseRejected("m")).rc, BAD_RESPONSE)
    check("...and an Unanswerable is not re-wrapped",
          lambda: type(unanswerable_if_armed(Unanswerable("m"))).__name__, "Unanswerable")

    # ── round 3 B1 + M3 — A `return` IS AN EXIT FROM THE ARMED SCOPE, AND `_fire` IS ITS THIRD
    # ENTRANCE ────────────────────────────────────────────────────────────────────────────────
    def _arm_unwritable_cache():
        """`--arm` with the answer paid for and the cache unwritable. Round 3 B1's exact world."""
        saved = (globals()["prepared_prompt"], globals()["call_model"],
                 globals()["parse_response"], globals()["CACHE_DIR"])
        try:
            globals()["prepared_prompt"] = lambda: (
                "p", ROOT / ".claude" / "plans" / "p.md", "t", [(1, "s")], [("n", "trig")])
            globals()["call_model"] = lambda _p: '{"1": "n"}'
            globals()["parse_response"] = lambda *_a: {1: "n"}
            globals()["CACHE_DIR"] = Path("/dev/null/nope")   # unwritable by construction
            return do_arm()
        except Refusal as exc:
            return exc.rc
        finally:
            (globals()["prepared_prompt"], globals()["call_model"],
             globals()["parse_response"], globals()["CACHE_DIR"]) = saved

    # ⛔ THIS LINE WAS `return OK if written else CANNOT_RUN`, so a PAID answer that could not be
    # cached exited on the routine "nothing is armed" code, and `do_arm`'s `except Refusal`
    # boundary could never see it because a return is not a raise.
    check("--arm: a paid answer that cannot be cached is CANNOT ANSWER, not the routine rc 2",
          _arm_unwritable_cache, UNANSWERABLE)

    def _fire_with_bare_refusal():
        """A bare `Refusal` raised INSIDE `--fire`'s armed scope. Round 3 M3."""
        def _boom(_t):
            raise Refusal("CANNOT RUN: some future read under --fire")
        saved = globals()["paused"]
        try:
            globals()["paused"] = _boom
            return _armed_world(lambda r, sent: (
                (r / ".claude" / "plans" / "p.md").write_text(
                    "- [ ] **Step 1 of 1** — Do\n  - **Doing:** doing it\n", encoding="utf-8"),
                sent.write_text("plan: .claude/plans/p.md\n", encoding="utf-8")))
        finally:
            globals()["paused"] = saved

    # ⛔ THE BOUNDARY MUST BE LIVE, AND THE FIRST ATTEMPT AT M3 WAS INERT: it rebound `exc` in
    # `do_fire` and then used a bare `raise`, which re-raises the ACTIVE exception and not the
    # rebound name. The "no sentinel stays rc 2" check passed over that no-op, which is why this
    # case asserts the CONVERSION rather than only the preservation.
    check("--fire: a bare CANNOT_RUN raised after the plan is read is CANNOT ANSWER",
          _fire_with_bare_refusal, UNANSWERABLE)
    # ⚠ AND THE PRESERVATION, at the same boundary: `read_armed_plan` is OUTSIDE the armed scope,
    # so no sentinel is still the routine absence. Wrapping the whole of `_fire` would invert it.
    check("...while no sentinel is STILL the routine rc 2, because the plan read is outside it",
          lambda: _armed_world(None), CANNOT_RUN)

    def _prepared_with(read_plan, mem):
        """Drive `prepared_prompt`'s boundary with the plan read and the corpus stubbed."""
        saved = (globals()["read_armed_plan"], globals()["memory_dir"])
        try:
            globals()["read_armed_plan"], globals()["memory_dir"] = read_plan, mem
            prepared_prompt()
            return OK
        except Refusal as exc:
            return exc.rc
        finally:
            globals()["read_armed_plan"], globals()["memory_dir"] = saved

    _ok_plan = lambda: ("plan: p.md\n", Path("p.md"),
                        "- [ ] **Step 1 of 1** — Do\n  - **Doing:** doing it\n")

    def _no_plan():
        raise Refusal("CANNOT RUN: no plan is armed")

    # ⛔ THE WIRING CASE FOR BOUNDARY A. Deleting the `try` in `prepared_prompt` leaves every case
    # above green — they drive the rule, not its use.
    check("prepared_prompt: an armed READABLE plan with no corpus is CANNOT ANSWER, not rc 2",
          lambda: _prepared_with(_ok_plan, lambda: None), UNANSWERABLE)
    # ⚠ AND THE OTHER DIRECTION AT THE SAME BOUNDARY: the routine absence must survive, or the
    # fix has merely inverted the conjunction.
    check("...while NO plan armed stays the routine rc 2",
          lambda: _prepared_with(_no_plan, lambda: None), CANNOT_RUN)

    def _arm_body_failing():
        """Drive `do_arm`'s boundary: the plan parses, the body then raises a bare CANNOT_RUN."""
        saved = (globals()["prepared_prompt"], globals()["_arm_body"])
        try:
            globals()["prepared_prompt"] = lambda: ("p", Path("p.md"), "t", [(1, "s")], [("n", "t")])

            def _boom(*_a, **_k):
                raise Refusal("CANNOT RUN: the model could not be reached")

            globals()["_arm_body"] = _boom
            do_arm()
            return OK
        except Refusal as exc:
            return exc.rc
        finally:
            globals()["prepared_prompt"], globals()["_arm_body"] = saved

    # ⛔ THE WIRING CASE FOR BOUNDARY B, and the reason `_arm_body` is a separate function: a `try`
    # around an inlined body has no seam a case can reach.
    check("do_arm: a bare CANNOT_RUN after the plan parsed is CANNOT ANSWER",
          lambda: _arm_body_failing(), UNANSWERABLE)

    # ── backlog #202 — THE CORPUS SIDE OF rc=2's CONJUNCTION ────────────────────────────────
    # ⛔ THIS WORLD IS ENTIRELY VALID EXCEPT FOR THE CORPUS: the sentinel names a readable plan,
    # the cache carries the fingerprint this module itself computes, and the named entry is the
    # one the cache picked. Only `memory_dir()` fails — the temp ROOT hashes to a slug with no
    # corpus behind it. Before #202 this returned rc 2, which the hook is RIGHT to ignore, so a
    # 161-char message ending "NOTHING WAS SURFACED" reached the reader as zero bytes.
    def _readable_plan(r, sent):
        (r / ".claude" / "plans" / "p.md").write_text(
            "- [ ] **Step 1 of 1** — Do the thing\n  - **Doing:** doing the thing\n",
            encoding="utf-8")
        sent.write_text("plan: .claude/plans/p.md\n", encoding="utf-8")

    def _valid_cache(cdir, root):
        text = (root / ".claude" / "plans" / "p.md").read_text(encoding="utf-8")
        (cdir / "p.json").write_text(json.dumps({
            "plan": ".claude/plans/p.md", "fingerprint": plan_fingerprint(text),
            "corpus_size": 1, "model": MODEL, "armed": "2026-09-30T00:00:00+00:00",
            "picks": {"1": "some-entry"},
            "triggers": {"1": "FIRES-WHEN: doing the thing"}}), encoding="utf-8")

    check("an armed plan with a VALID cache and no corpus is CANNOT ANSWER, not routine silence",
          lambda: _armed_world(_readable_plan, _valid_cache), UNANSWERABLE)
    # ⚠ THE ADJACENT NEGATIVE, so the code above cannot be satisfied by a rule that always fires:
    # the SAME world with the model's answer being NONE has nothing to resolve, so the corpus is
    # never consulted and the correct outcome is a silent rc 0.
    def _none_cache(cdir, root):
        text = (root / ".claude" / "plans" / "p.md").read_text(encoding="utf-8")
        (cdir / "p.json").write_text(json.dumps({
            "plan": ".claude/plans/p.md", "fingerprint": plan_fingerprint(text),
            "corpus_size": 1, "model": MODEL, "armed": "2026-09-30T00:00:00+00:00",
            "picks": {"1": NONE}, "triggers": {}}), encoding="utf-8")

    check("...but a cached NONE needs no corpus, so the same world is a silent OK",
          lambda: _armed_world(_readable_plan, _none_cache), OK)
    # ⚠ AND THE SIXTH CODE MUST BE DISTINCT FROM THE FIFTH, asserted rather than assumed: they are
    # different questions and a shared value would re-create the conjunction one code along.
    check("CANNOT ANSWER and UNREADABLE PLAN are different codes",
          lambda: len({OK, CANNOT_RUN, STALE_CACHE, BAD_RESPONSE, UNREADABLE_PLAN, UNANSWERABLE}), 6)

    check("a sentinel naming a VANISHED plan is UNREADABLE, not silence (a branch switch does this)",
          lambda: _armed_world(lambda r, s: s.write_text("plan: .claude/plans/gone.md\n",
                                                         encoding="utf-8")), UNREADABLE_PLAN)
    check("a sentinel naming NO plan is UNREADABLE",
          lambda: _armed_world(lambda r, s: s.write_text("armed: yes\n", encoding="utf-8")),
          UNREADABLE_PLAN)
    check("an undecodable SENTINEL is UNREADABLE, not CANNOT RUN",
          lambda: _armed_world(lambda r, s: s.write_bytes(b"\xff\xfe nope")), UNREADABLE_PLAN)
    check("an undecodable PLAN FILE is UNREADABLE, not CANNOT RUN",
          lambda: _armed_world(_write_bad_plan), UNREADABLE_PLAN)

    # ── H2's WIRING, driven end to end (2) ──────────────────────────────────────────────
    # ⛔ The `_live_trigger_probe` cases test `live_trigger_for` ALONE, so every one of them passes
    # with `do_fire` still printing the CACHED text — measured: that mutation SURVIVED the sweep.
    # Only a world where the two DIVERGE can tell which one reached the reader.
    def _fire_with_a_rewritten_trigger():
        import io, os, contextlib
        with tempfile.TemporaryDirectory() as td7:
            root, home = Path(td7) / "repo", Path(td7) / "home"
            pl = root / ".claude" / "plans" / "w.md"
            pl.parent.mkdir(parents=True)
            pl.write_text("### T\n\n- [ ] **Step 1 of 1** — Go\n  - **Doing:** a situation\n",
                          encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text("plan: .claude/plans/w.md\n",
                                                             encoding="utf-8")
            cd = root / ".claude" / "recall-cache"
            cd.mkdir()
            (cd / "w.json").write_text(json.dumps(cache_document(
                ".claude/plans/w.md", pl.read_text(encoding="utf-8"), {1: "the-entry"},
                {"the-entry": "THE CACHED WORDING"}, 1, "2026-09-30T00:00:00+00:00")),
                encoding="utf-8")
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
            corpus = home / ".claude" / "projects" / slug / "memory"
            corpus.mkdir(parents=True)
            (corpus / "the-entry.md").write_text(
                '---\ndescription: "FIRES-WHEN: THE LIVE WORDING"\n---\nbody\n', encoding="utf-8")
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"],
                     os.environ.get("HOME"))
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = cd
                os.environ["HOME"] = str(home)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    do_fire()
                return buf.getvalue()
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved[:3]
                if saved[3] is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved[3]

    check("do_fire prints the LIVE trigger, not the cached one, when they have diverged",
          lambda: ("THE LIVE WORDING" in _fire_with_a_rewritten_trigger()
                   and "THE CACHED WORDING" not in _fire_with_a_rewritten_trigger()), True)
    check("...and it SAYS the trigger was rewritten, so the reader knows the match used old wording",
          lambda: "REWRITTEN since the plan was armed" in _fire_with_a_rewritten_trigger(), True)

    # ── H1(e)'s ORDERING, driven end to end (1) ─────────────────────────────────────────
    # ⛔ ROUND 2 #4. The mutation named for this regression DELETED `print(text)` instead of moving
    # the marker write before it, so its case failed because nothing printed — not because the
    # ordering broke. An unfaithful guard for the named defect. This drives a world whose cache
    # directory is READ-ONLY and asserts the matched lesson is printed ANYWAY, which is the property
    # H1(e) is about: the bookkeeping for a message must not destroy the message.
    def _fire_with_an_unwritable_marker():
        import io, os, contextlib
        with tempfile.TemporaryDirectory() as td8:
            root, home = Path(td8) / "repo", Path(td8) / "home"
            pl = root / ".claude" / "plans" / "w.md"
            pl.parent.mkdir(parents=True)
            pl.write_text("### T\n\n- [ ] **Step 1 of 1** — Go\n  - **Doing:** a situation\n",
                          encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text("plan: .claude/plans/w.md\n",
                                                             encoding="utf-8")
            cd = root / ".claude" / "recall-cache"
            cd.mkdir()
            (cd / "w.json").write_text(json.dumps(cache_document(
                ".claude/plans/w.md", pl.read_text(encoding="utf-8"), {1: "the-entry"},
                {"the-entry": "a trigger"}, 1, "2026-09-30T00:00:00+00:00")), encoding="utf-8")
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
            corpus = home / ".claude" / "projects" / slug / "memory"
            corpus.mkdir(parents=True)
            (corpus / "the-entry.md").write_text(
                '---\ndescription: "FIRES-WHEN: a trigger"\n---\nbody\n', encoding="utf-8")
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"],
                     os.environ.get("HOME"))
            os.chmod(cd, 0o500)
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = cd
                os.environ["HOME"] = str(home)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    do_fire()
                return buf.getvalue()
            finally:
                os.chmod(cd, 0o700)
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved[:3]
                if saved[3] is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved[3]

    check("a READ-ONLY cache directory does not destroy the matched lesson",
          lambda: "the-entry" in _fire_with_an_unwritable_marker(), True)

    # ── r2 #1's WIRING and r2 #2's WIRING, both driven where the defect lives (2) ───────
    # ⛔ SIXTH TIME TONIGHT: the case tested the callee while the mutation sat at the CALL SITE, so
    # both of these survived a green 168-case suite. `live_trigger_for`'s statuses are covered four
    # ways and `do_fire` could still ignore LIVE_NO_TRIGGER; `decode_verdict`'s label is covered two
    # ways and `read_or_refuse` could still hard-code it.
    def _fire_on_a_trigger_less_entry():
        import io, os, contextlib
        with tempfile.TemporaryDirectory() as td9:
            root, home = Path(td9) / "repo", Path(td9) / "home"
            pl = root / ".claude" / "plans" / "w.md"
            pl.parent.mkdir(parents=True)
            pl.write_text("### T\n\n- [ ] **Step 1 of 1** — Go\n  - **Doing:** a situation\n",
                          encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text("plan: .claude/plans/w.md\n",
                                                             encoding="utf-8")
            cd = root / ".claude" / "recall-cache"
            cd.mkdir()
            (cd / "w.json").write_text(json.dumps(cache_document(
                ".claude/plans/w.md", pl.read_text(encoding="utf-8"), {1: "the-entry"},
                {"the-entry": "THE CACHED OLD TRIGGER"}, 1, "2026-09-30T00:00:00+00:00")),
                encoding="utf-8")
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
            corpus = home / ".claude" / "projects" / slug / "memory"
            corpus.mkdir(parents=True)
            # the entry EXISTS — so `cached_entry_verdict` passes — but carries no frontmatter
            (corpus / "the-entry.md").write_text("just body text, no frontmatter\n", encoding="utf-8")
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"],
                     os.environ.get("HOME"))
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = cd
                os.environ["HOME"] = str(home)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    do_fire()
                return buf.getvalue()
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved[:3]
                if saved[3] is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved[3]

    raises("do_fire REFUSES an entry that has lost its trigger, instead of serving the cached wording",
           _fire_on_a_trigger_less_entry, StaleCache, "no longer carries a FIRES-WHEN")

    # ⛔ THESE CALL `read_or_refuse` DIRECTLY, AT SEPARATE SITES WITH DIFFERENT LITERALS, AND THAT
    # IS THE POINT. A single helper wrapping the call gave the suite ONE textual call site, so
    # `check-fixture-variation.py` could not tell `path`, `what` or `refusal` from constants — and
    # it went red in CI, which neither `--self-test` nor `--mutate .` can see. The world-builder
    # returns the file; the calls are here.
    def _undecodable(name):
        d = Path(tempfile.mkdtemp())
        f = d / name
        f.write_bytes(b"\xff\xfe not utf-8")
        return f

    def _caught(thunk):
        try:
            thunk()
        except Refusal as exc:
            return (type(exc).__name__, str(exc).split(":")[0])
        return ("none", "")

    check("read_or_refuse raises the CLASS it was given, with a sentence that matches it",
          lambda: _caught(lambda: read_or_refuse(_undecodable("w.json"), "recall cache", StaleCache)),
          ("StaleCache", "STALE CACHE"))
    check("...and the default reader is still CANNOT RUN, both class and sentence",
          lambda: _caught(lambda: read_or_refuse(_undecodable("plan.md"), "plan file")),
          ("Refusal", "CANNOT RUN"))
    check("...and a third reader names ITSELF, so `what` is not a constant either",
          lambda: "sentinel" in _caught_msg(lambda: read_or_refuse(_undecodable("executing-plan"),
                                                                  "sentinel", Refusal)),
          True)

    # ── do_fire's DEDUPE wiring, driven end to end (2) ───────────────────────────────────
    # ⛔ The case above raises before it ever reaches the marker, so it cannot see this wiring at
    # all — the same compose failure one layer along. This world has the entry PRESENT, calls
    # do_fire TWICE, and captures what each call printed.
    def _fire_twice(again_on_second=False):
        import io, os, contextlib
        with tempfile.TemporaryDirectory() as td5:
            root, home = Path(td5) / "repo", Path(td5) / "home"
            plan = root / ".claude" / "plans" / "w.md"
            plan.parent.mkdir(parents=True)
            plan.write_text("### Task 1: Go\n\n- [ ] **Step 1 of 1** — Go\n"
                            "  - **Doing:** a situation\n", encoding="utf-8")
            (root / ".claude" / "executing-plan").write_text(
                "plan: .claude/plans/w.md\n", encoding="utf-8")
            cache_dir = root / ".claude" / "recall-cache"
            cache_dir.mkdir()
            (cache_dir / "w.json").write_text(json.dumps(cache_document(
                ".claude/plans/w.md", plan.read_text(encoding="utf-8"),
                {1: "the-entry"}, {"the-entry": "a trigger"},
                1, "2026-09-29T00:00:00+00:00")), encoding="utf-8")
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
            corpus = home / ".claude" / "projects" / slug / "memory"
            corpus.mkdir(parents=True)
            (corpus / "the-entry.md").write_text(
                "---\ndescription: \"FIRES-WHEN: a situation\"\n---\nbody\n", encoding="utf-8")
            saved = (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"],
                     os.environ.get("HOME"))
            try:
                globals()["ROOT"] = root.resolve()
                globals()["SENTINEL"] = root / ".claude" / "executing-plan"
                globals()["CACHE_DIR"] = cache_dir
                os.environ["HOME"] = str(home)
                outs = []
                for i in range(2):
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        do_fire(again=(again_on_second and i == 1))
                    outs.append(buf.getvalue())
                return outs
            finally:
                (globals()["ROOT"], globals()["SENTINEL"], globals()["CACHE_DIR"]) = saved[:3]
                if saved[3] is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved[3]

    check("do_fire prints on the FIRST call for a step",
          lambda: "the-entry" in _fire_twice()[0], True)
    check("do_fire is SILENT on the second call for the SAME step",
          lambda: _fire_twice()[1], "")
    check("...unless --again is passed, which is the deliberate escape",
          lambda: "the-entry" in _fire_twice(again_on_second=True)[1], True)

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


# ────────────────────────────────────────────────────────────────────────── main
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--arm", action="store_true",
                    help="ONE model call: match every step of the armed plan and cache it")
    ap.add_argument("--fire", action="store_true",
                    help="no model call: print the entry for the current unticked step")
    ap.add_argument("--again", action="store_true",
                    help="re-surface a step already surfaced once "
                         "(the dedupe is per (plan, step), not per day)")
    ap.add_argument("--print-prompt", action="store_true",
                    help="print exactly what --arm would send. No call, no cost")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return _self_test()
    chosen = [f for f, v in (("--arm", a.arm), ("--fire", a.fire),
                             ("--print-prompt", a.print_prompt)) if v]
    if len(chosen) != 1:
        print("CANNOT RUN: name exactly one of --arm / --fire / --print-prompt / --self-test. "
              "NOTHING WAS MATCHED.", file=sys.stderr)
        return CANNOT_RUN
    try:
        if a.print_prompt:
            print(prepared_prompt()[0])
            return OK
        return do_arm() if a.arm else do_fire(again=a.again)
    except Refusal as exc:
        # NOT a fail-open handler: every Refusal subclass carries a NON-ZERO rc, and this is the
        # only place they are caught. The alternative — letting them escape as a traceback — is
        # loud too but names Python's call stack instead of naming what could not be answered.
        # ⚠ A DELIBERATELY EMPTY message is the M4 dedupe: the rc still says 3 every time, and only
        # the sentence is rate-limited. Printing it anyway would emit a bare newline, which a caller
        # capturing both streams then has to strip.
        if str(exc):
            print(str(exc), file=sys.stderr)
        return exc.rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

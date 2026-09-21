#!/usr/bin/env python3
"""Every CI job pins the Python interpreter, the pins agree, and the pin actually took effect.

    python3 scripts/check-python-pin.py              # in CI: asserts. locally: advises.
    python3 scripts/check-python-pin.py --self-test  # 84 cases

    exit 0 = pinned, agreeing, and (in CI) in effect   exit 1 = a real disagreement
    exit 2 = CANNOT RUN — no workflow or no pin found, which is never a pass

WHY THIS EXISTS
---------------
MEASURED 2026-09-16, PR #315. CI and a developer machine disagreed about the SAME COMMIT: the
mutation harness reported `723 mutations, 723 killed, 723 attributed` locally and `722 attributed`
in CI, with one entry flagged *"RED but printed no `[FAIL] <case>` line, so NOTHING COULD SEE THE
KILL"*.

The cause was an interpreter difference nobody had declared. `Path.is_file()` raises `OSError`
(ENAMETOOLONG) for an over-long path — **except on Python 3.13+, which widened the errno set it
swallows**. The dev machine ran 3.14 and got `False`; the runner raised, and it raised while the
self-test's case list was still being BUILT, so the suite exited non-zero having printed nothing a
parser could attribute.

⛔ THE VERSION GAP WAS THE SYMPTOM. THE DEFECT WAS THAT NOTHING WAS PINNED. Measured the same day:
`ci.yml` invoked bare `python3` **45 times** — every guard in the one REQUIRED status check — and
never called `setup-python`. The `schema-gates` job did not pin either. The ONLY `python-version:`
in the repository belonged to `prod-drift`, the scheduled job that runs a single script. So GitHub
could change the behaviour of 45 guards by bumping a runner image: no commit, no diff, nothing to
attribute a new failure to. That is the same shape as backlog #137 itself — a signal with no owner.

THE PREDICATE, AND WHY IT IS NOT "JOBS THAT RUN PYTHON"
------------------------------------------------------
⚠ The obvious rule — *a job that invokes `python3` must pin it* — WOULD NOT HAVE CAUGHT THE BUG.
The `schema-gates` job runs `scripts/check-schema-gates.sh`, which invokes the fifteen Python gates
INTERNALLY; the job block contains no literal `python3` at all. That is the #137 lesson one file
over: a text scan cannot see an indirect invocation, and *the lesson is the PREDICATE, not the list*.

So the rule is the decidable one: **every job pins, or is exempt with a written reason.** A job that
genuinely runs no Python says so out loud. A new job fails until someone states which case it is,
which is the direction that cannot fail silently.

⚠ THE BLAST RADIUS, STATED — r1 Medium 2 (claude), folded as a sentence rather than a behaviour
change. This guard runs inside the REQUIRED check, so the moment an unpinned workflow ARRIVES it
reddens every open pull request at once, not just the one that added it. A workflow can arrive
without anyone in this repository writing it: GitHub's CodeQL default setup and Dependabot both
author workflow files. The fix is two lines of YAML or one `EXEMPT_JOBS` entry, and the message says
so — but whoever meets it first will not have caused it.

WHAT IT ASSERTS WHERE — one rule, two questions
-----------------------------------------------
⚠ The same mismatch means different things in the two places, and collapsing them would be wrong:

  * in CI (`GITHUB_ACTIONS` set): the running interpreter MUST match the pin. That asserts the pin
    TOOK EFFECT — a `setup-python` step that is present but ineffective is exactly the sort of green
    nothing that this repository files findings about.
  * locally: a mismatch is ADVISORY and exits 0. It prints which interpreter CI uses so a developer
    reading a local green knows it is provisional. ⛔ It deliberately does NOT fail: backlog #56
    measured that a gate which is red from birth gets switched off, and most contributors will not
    be on the pinned version. A gate nobody runs protects nothing.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
from typing import NamedTuple
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / ".github" / "workflows"

# ⚠ BOTH SPELLINGS — r1 Low 2 (claude), and r2 corrected its own guess that the jobless refusal
# would cover this "for free": a file that is never READ cannot be jobless. GitHub accepts both
# extensions, this repository happens to use only one, and a guard that reads only what its own
# corpus happens to contain is the shape this work has already paid for twice.
WORKFLOW_GLOBS = ("*.yml", "*.yaml")

# Jobs that genuinely run no Python, with the reason. ⚠ A NAME plus a REASON, not a count: a bare
# count is satisfied by exempting a new job and fixing an old one, which is how an allow-list stops
# meaning anything. Empty today — every job in this repository runs Python, directly or through a
# shell script — and that is itself worth stating, because an empty allow-list is the strongest
# form and someone will be tempted to add to it rather than add two lines of YAML.
EXEMPT_JOBS: dict[str, str] = {}


class Step(NamedTuple):
    r"""One step of a workflow job: the indent of its `- `, and every line BELONGING to it.

    `body` INCLUDES the dash line with the dash blanked to a space, so a key written on the dash
    line (`- uses: x`) and the same key written under a `name:` are both plain `key:` lines to a
    caller scanning for one.

    ⚠ r3 (claude) F4 — THE FIRST DRAFT CALLED THAT EQUIVALENCE "the whole point of this type", AND
    THE CODE DOES NOT EARN THE CLAIM. Blanking the dash is cosmetic: dropping it leaves every
    caller's `^\s*key:` match working, and the mutation SURVIVED. What the blanking does NOT do is
    restore the dash line's true indent — `body[0]` reports the column of the text after the dash,
    not of the dash — so an indent-sensitive scan (`with:` detection) cannot use it. No caller does
    today. Written down rather than repaired, because the honest statement is cheaper than a
    guarantee nothing needs.
    """

    indent: int
    body: list[str]


def _steps(text: str) -> list[Step]:
    r"""PURE. Split a workflow into steps, each owning the lines indented under its `- `.

    ⛔ THIS EXISTS BECAUSE `declared_pins` WAS WRONG THREE TIMES IN THREE ROUNDS, always the same
    way. Each repair narrowed the SPAN it searched — "any line in the file" -> "inside the step" ->
    "inside the step's `with:`" — and never named the THING. The step itself stayed identified by
    `^(\s*)-\s+uses:\s*actions/setup-python`, a pattern that only matches when nothing is
    written before `uses:`. r2's first probe found the fourth shape immediately: give the step a
    `name:` — the ordinary idiom, and how 62 of this repository's 70 steps are written — and the
    pin became invisible while the job read as UNPINNED. The error message then told the author to
    add the step they could already see, or to add the job to `EXEMPT_JOBS`.

    ⭐ COORDINATOR'S CALL, 2026-09-21, recorded because a stopping decision looks arbitrary later.
    r2 (claude) read `docs/dev-process.md`'s THRASHING arming condition as met for `declared_pins`
    specifically — three consecutive rounds, each finding caused by the previous round's fix — and
    left the call to the coordinator. `docs/review-method.md` gives ONE test: *can a redesign
    remove it?* Here it can, and does: identifying a step by what it CONTAINS dissolves H1 and the
    three shapes before it, because none of them was about `with:` or indentation — all four were
    about the opening line. So the answer to thrashing is this redesign, NOT a Phase 6 review:
    Phase 6 exists to FIND a structural defect, and this one was already found and named.
    ⚠ ITS FALSIFIER, PRE-COMMITTED: if a FOURTH `declared_pins` finding arrives in round 3, the
    redesign did not dissolve the class and Phase 6 fires. That is the observation that makes this
    a call rather than a preference.

    A line scan, not a YAML parse — PyYAML is not installed here and every sibling guard reads
    workflows as text.
    """
    # ⛔⛔ THE MASK RUNS **HERE**, NOT IN THE CALLER — and putting it in the caller was the fifth
    # defect on this function, found by Codex r3 against `cfefc377`+`dc4efd1b` with a fixture my
    # own probe had missed:
    #
    #       - name: write fake workflow
    #         run: |
    #           - uses: actions/setup-python@v5      <- a DASH LINE inside a block scalar
    #             with:
    #               python-version: '9.9'
    #
    # `_structural` was applied to each step's body AFTER the split, so it never got the chance:
    # the split itself saw that dash and manufactured a PHANTOM STEP owning the fake `with:`.
    # `declared_pins` returned ['9.9'] for a job with no setup-python at all.
    #
    # ⭐ THE LAYERING IS THE LESSON. "Which lines are STRUCTURE" is logically prior to "which step
    # OWNS a line", so the mask belongs to the splitter. Filtering after the split asks the second
    # question before the first, which is the same ordering error in a new costume — the previous
    # four all asked "where do I look?" before "what am I looking at?".
    # ⟳ r3 (claude) F3, Medium — A DASH IS A STEP BOUNDARY ONLY WHEN IT IS A **SIBLING**, and the
    # first version of this got that wrong in a way that DROPPED LINES. It treated every `- ` as a
    # new step, so a nested list inside a step —
    #
    #       - name: Set up Python
    #         env:
    #           LIST:
    #             - a                 <- opened a phantom step at indent 12
    #         uses: actions/setup-python@v5
    #         with:
    #           python-version: '3.12'
    #
    # — opened a step at indent 12, and the next line (indent 8) was SHALLOWER, so the close branch
    # fired and pushed a `Step(-1, [])` sentinel. Every later line was then discarded until the next
    # dash: `uses:` and the pin belonged to NO step, and `declared_pins` returned []. A real pin
    # vanished. Fail-closed, so not a false green — but the consequence is r2's H1 exactly: the
    # author sees a pinned step, the guard says UNPINNED, and the message routes them to EXEMPT_JOBS.
    #
    # ⛔ THE SENTINEL ENDED THE FILE, NOT THE STEP. There is no sentinel now, and no discard branch:
    # a line is either a sibling dash (new step), a dedent out of the list (close), or body.
    # ⟳ r4 (codex) High — A DASH IS ONLY A STEP IF IT IS UNDER `steps:`. The previous rule scanned
    # every structural dash in the file, so a `strategy.matrix.include` entry — a perfectly ordinary
    # list of mappings — was parsed as a step:
    #
    #       strategy:
    #         matrix:
    #           include:
    #             - uses: actions/setup-python@v5
    #               with:
    #                 python-version: '9.9'
    #       steps:
    #         - run: python3 --version
    #
    # Measured: `declared_pins -> ['9.9']`, `unpinned_jobs -> []`, `verdict -> rc 0 "python pin OK"`
    # for a job with NO setup-python step at all. A FALSE GREEN — the direction this guard must
    # never fail in — and it predates the sibling rewrite rather than being caused by it.
    #
    # ⭐ THE SEVENTH DEFECT IN THIS FUNCTION, AND IT IS THE SAME ROOT CAUSE AS THE OTHER SIX: the
    # guard reads YAML by scanning lines, so anything SHAPED like a step is a step. Each repair has
    # taught it one more thing that shape alone cannot tell it — where the step ENDS, which lines
    # are CONTENT, which dashes are SIBLINGS, and now which list it is IN. That accumulation is the
    # subject of backlog #153 (the architecture review), which asks whether this should parse or
    # refuse rather than keep learning YAML one defect at a time.
    # ⟳ r5 (claude) F1 + F2 — ONE RULE, TWO DEFECTS, BOTH CAUSED BY ASKING THE WRONG QUESTION.
    # The r4 repair asked *is this line the text `steps:`?* and had no notion of WHERE it sits:
    #
    #   F1, an EIGHTH defect (false green): a matrix DIMENSION named `steps` —
    #       strategy: {matrix: {steps: [ {uses: actions/setup-python, with: {python-version: 9.9}} ]}}
    #       ...declared a pin for a job whose only real step is `run: echo hi`.
    #   F2, a REGRESSION I introduced (MISS): an action INPUT named `steps` —
    #       - uses: someone/thing@v1
    #         with: {steps: [a]}
    #       ...silently re-scoped `steps_indent` to the inner key, and the real setup-python step's
    #       body lines were then eaten by the dedent check. A pin visible at 5206e020 vanished.
    #
    # ⭐ A JOB'S STEP LIST IS THE SHALLOWEST `steps:` IN THE FILE. A matrix dimension and an action
    # input are both necessarily NESTED DEEPER than the job key that owns them, so one invariant —
    # computed once, before any splitting — closes both. That is why this is not a ninth patch:
    # it replaces "which line says steps" with "which steps is the job's", which is the question
    # the previous version could not ask.
    #
    # ⚠ ITS BOUND, because this file has been burned by unstated ones: if a workflow ever nests a
    # job's `steps:` DEEPER than some other `steps:` key, this picks the wrong one. Measured: no
    # such shape exists in this repository, and a composite action (`runs:` -> `steps:`) is fine
    # because its `steps:` is the only one in the file. The general answer is backlog #153.
    # ⟳ r6 (codex) High — `steps` IS A VALID JOB ID, and that inverts the shallowest-`steps:`
    # invariant into a false green:
    #
    #       jobs:
    #         steps:                      <- a JOB KEY at indent 2, matched by _STEPS_KEY
    #           strategy: {matrix: {include: [ ...setup-python, python-version 3.12... ]}}
    #           steps:                    <- the job's REAL step list, at indent 4
    #             - run: python3 --version
    #
    # `min(depths)` picked the job-id line, so the matrix entry was credited and `verdict` returned
    # "python pin OK" for a job whose only step runs `python3 --version`. GitHub allows any job id
    # starting with a letter or `_`, so `steps` is legal.
    #
    # A job key is EXACTLY the shape `job_names` already recognises, and that rule is not restated
    # here: the same regex is applied to the same `jobs:` block, so the two cannot disagree about
    # what a job key is.
    structural = _structural(text.split("\n"))
    job_key: list[bool] = []
    in_jobs = False
    for ln in structural:
        if re.match(r"^jobs:\s*(#.*)?$", ln):
            in_jobs = True
            job_key.append(False)
            continue
        if in_jobs and ln and not ln.startswith(" ") and not ln.startswith("#"):
            in_jobs = False                       # a new top-level key ends the jobs block
        job_key.append(bool(in_jobs and re.match(r"^  ([A-Za-z_][\w-]*):(\s.*)?$", ln)))
    depths = [len(ln) - len(ln.lstrip()) for ln, is_job in zip(structural, job_key)
              if _STEPS_KEY.match(ln) and not is_job]
    job_steps_indent = min(depths) if depths else None

    out: list[Step] = []
    cur: Step | None = None
    steps_indent: int | None = None          # the indent of the `steps:` KEY we are inside
    for idx, line in enumerate(structural):
        m = re.match(r"^(\s*)-(\s.*)$", line)
        indent = len(line) - len(line.lstrip())
        opens_steps = _STEPS_KEY.match(line)
        if (opens_steps and len(opens_steps.group(1)) == job_steps_indent
                and not job_key[idx]):
            steps_indent, cur = len(opens_steps.group(1)), None
            continue
        if steps_indent is None:
            continue                          # not inside a steps: sequence — nothing here is a step
        if line.strip() and indent <= steps_indent and not m:
            steps_indent, cur = None, None    # dedented out of the steps: block entirely
            continue
        if m and (cur is None or len(m.group(1)) <= cur.indent):
            cur = Step(len(m.group(1)), [" " + m.group(2)])
            out.append(cur)
            continue
        if cur is None:
            continue
        # ⚠ TWO CLAUSES HERE ARE UNFALSIFIABLE BY VALID YAML, AND THAT IS STATED RATHER THAN LEFT
        # AS AN ABSENCE (r3 F4). Measured on a copy after every other clause was given a case:
        #   * `<=` vs `<` below — a NON-dash, NON-comment, NON-blank line at exactly the dash's
        #     indent is not valid YAML (it would be a mapping key sibling to a list item). Comments
        #     and blanks, which CAN sit there, are handled before this line — the comment case was
        #     the sixth defect, so this boundary is now the only unobservable part.
        #   * the dash blanking in `Step` — cosmetic, reasoned about in that class's docstring.
        # Both survive mutation because no legal input distinguishes them, not because nothing
        # looked. Backlog #151 is the standing row for this class on the sibling guard.
        if line.strip() and indent <= cur.indent:
            cur = None                       # dedented out of this list entirely
            continue
        cur.body.append(line)                # deeper than the dash: it is this step's, dash or not
    return out


# ⟳ r5 (codex) Medium — `steps:` MAY CARRY YAML NODE PROPERTIES, and the first version of this
# opener accepted only a bare key plus an optional comment. Measured against `020b04ad`:
#
#     steps: &py          -> declared_pins []   unpinned_jobs ['w.yml:verify']
#     steps: !!seq        -> same
#
# A PINNED job read as UNPINNED — fail-closed, but r2 H1's failure mode again, and a regression
# introduced by the scoping rule itself. An anchor (`&name`) or a tag (`!tag` / `!!tag`) is node
# METADATA, not a value; a real scalar value (`steps: '3'`) still correctly fails to match, which
# is what keeps an unrelated key named `steps` from opening a scope.
_STEPS_KEY = re.compile(r"^(\s*)steps:\s*(?:[&!]\S+\s*)*(#.*)?$")


_BLOCK_SCALAR = re.compile(r"^(\s*)[\w.\-]+:\s*[|>][-+0-9]*\s*(#.*)?$")


def _structural(body: list[str]) -> list[str]:
    r"""PURE. The lines of a step that are YAML STRUCTURE, with block-scalar CONTENT removed.

    ⛔⛔ THE FOURTH `declared_pins` DEFECT, AND I FOUND IT IN MY OWN REDESIGN — 2026-09-21, before
    round 3 returned. Recognising a step by what it CONTAINS fixed r2's H1 and opened a false green
    in the other direction:

        - name: docs
          run: |
            cat <<'EOF'
            uses: actions/setup-python@v5     <- TEXT, inside a shell heredoc, inside a YAML
            EOF                                  block scalar. Not a step declaration.
          with:
            python-version: '9.9'             <- read as a PIN. The job is not pinned at all.

    A false green is the direction this guard must never fail in, and it is the same family as r1's
    High. ⭐ THE ROOT CAUSE OF ALL FOUR IS ONE THING: this guard reads YAML by scanning lines, so
    text that LOOKS like structure is indistinguishable from structure. Each earlier repair moved
    the boundary — "any line" -> "inside the step" -> "inside the `with:`" -> "inside the step,
    identified by contents" — and none of them ever asked which lines are structure AT ALL.

    So this is not a fifth narrowing. It removes block-scalar CONTENT once, for every consumer, and
    both scans in `declared_pins` run over the result. A `run: |`, `script: >`, or any `key: |-`
    owns every line indented past it; those lines are data and are dropped.

    ⚠ WHAT THIS STILL CANNOT DO, stated rather than implied: it is not a YAML parser. A flow
    mapping (`with: {python-version: '9.9'}`) or a quoted string containing a newline escape is
    still read as text. Those shapes do not occur in this repository's workflows today — which is
    exactly the kind of sentence that has been wrong twice on this branch, so it is written as a
    KNOWN BOUND, not as a guarantee.
    """
    out: list[str] = []
    scalar_indent: int | None = None
    for line in body:
        here = len(line) - len(line.lstrip())
        if scalar_indent is not None:
            if line.strip() and here <= scalar_indent:
                scalar_indent = None               # dedented out of the block scalar
            else:
                continue                            # its CONTENT: data, never structure
        # ⟳ r3 F4 follow-through — A COMMENT IS NOT STRUCTURE, and treating it as structure was a
        # SIXTH defect, found by chasing an "unfalsifiable" clause rather than exempting it. A
        # comment sits at ANY indent in valid YAML, so one written at the step's own dash indent
        # satisfied the close test and ENDED THE STEP: `uses:` and the pin after it belonged to
        # nothing and `declared_pins` returned []. A real pin vanished — the MISS direction, and
        # r2's H1 experience again. ⭐ It is fixed HERE, not in the close test, for the same reason
        # the block-scalar mask moved into the splitter: "which lines are structure" is one
        # question with one owner, and a comment is the other way text can impersonate it.
        if line.lstrip().startswith("#"):
            continue
        m = _BLOCK_SCALAR.match(line)
        if m:
            scalar_indent = len(m.group(1))
            out.append(line)                        # the KEY is structure; its body is not
            continue
        out.append(line)
    return out


def declared_pins(text: str) -> list[str]:
    """PURE. Every `python-version:` that BELONGS TO an `actions/setup-python` step, in file order.

    ⛔⛔ IT USED TO MATCH ANY LINE SHAPED LIKE A PIN, WHICH IS A FALSE GREEN — r1 High (codex),
    reproduced: a `python-version:` inside a shell heredoc, or in an unrelated action's `with:`
    block, made a job with NO `setup-python` at all read as pinned, `unpinned_jobs` returned `[]`
    and `verdict` returned 0. A guard that can be satisfied by a line of prose is worse than no
    guard, because it reports the absence of the thing it was built to find.

    ⚠ THIS IS THE THIRD TIME ON THIS WORK THAT THE PREDICATE WAS THE DEFECT. The rule is not "text
    that looks like a pin" but "a pin attached to the action that actually installs the
    interpreter". Backlog #137's filter made the same mistake about paths, and this file's own
    docstring warns about it for `python3` — then did it one function over.

    A line scan, not a YAML parse: PyYAML is not installed here and sibling guards read workflows as
    text. A pin counts only between a `- uses: actions/setup-python…` line and the start of the
    next step at the same or shallower indent.
    """
    pins: list[str] = []
    for step in _steps(text):        # already structural — `_steps` owns the mask
        # ⛔ A STEP IS RECOGNISED BY WHAT IT CONTAINS, NOT BY HOW IT OPENS. See the REDESIGN note
        # in this function's docstring: the previous three versions all asked "does the line that
        # STARTS the step name setup-python?", which is only true when nothing is written before
        # `uses:` — and 62 of this repository's 70 steps write `- name:` first.
        if not any(re.match(r"^\s*uses:\s*actions/setup-python", ln) for ln in step.body):
            continue
        in_with, with_indent = False, 0
        for later in step.body:
            here = len(later) - len(later.lstrip())
            opens = re.match(r"^\s*with:\s*(#.*)?$", later)
            if opens and here > step.indent:
                in_with, with_indent = True, here
                continue
            if in_with and later.strip() and here <= with_indent:
                in_with = False            # left the `with:` mapping
            if not in_with:
                continue
            got = re.match(r"^\s*python-version:\s*(.+?)\s*$", later)
            if got:
                # ⚠ strip an inline comment BEFORE quotes — r1 Medium 1 (claude): a pin written
                # `python-version: '3.12'  # matches the Dockerfile` otherwise parsed as
                # `'3.12'  # matches…` and reddened the REQUIRED check with a nonsense message.
                value = got.group(1).split("#")[0]
                pins.append(value.strip().strip("'\""))
    return pins


def job_names(text: str) -> list[str]:
    """PURE. The job keys of a workflow, in file order.

    Jobs are the two-space-indented keys under a top-level `jobs:`. Anything more clever needs a
    YAML parser; anything less cannot tell a job from a step key.
    """
    out: list[str] = []
    in_jobs = False
    for line in text.split("\n"):
        # ⚠ a trailing comment on `jobs:` used to make EVERY job invisible — r1 High 2.
        if re.match(r"^jobs:\s*(#.*)?$", line):
            in_jobs = True
            continue
        if in_jobs:
            if line and not line.startswith(" ") and not line.startswith("#"):
                break                      # a new top-level key ends the jobs block
            # ⛔ THE TAIL IS LOOSE, THE INDENT IS NOT — r1 High 2 (claude), measured both ways.
            # Requiring nothing after the colon made a job key with a trailing comment, or a YAML
            # anchor (`deploy: &d`), INVISIBLE — and an invisible job is a PASSING job. The
            # reviewer mutated the tail loose and the suite stayed green (nothing depended on the
            # strictness), then mutated the INDENT loose and three cases killed it. So the tail
            # opens and the two spaces stay.
            m = re.match(r"^  ([A-Za-z_][\w-]*):(\s.*)?$", line)
            if m:
                out.append(m.group(1))
    return out


def unreadable_jobs(text: str) -> int:
    """PURE. Two-space key-shaped lines inside `jobs:` that the job regex cannot read.

    ⛔ TESTING FOR *ZERO* JOBS WAS NOT ENOUGH — r2 Medium 1 (claude). The refusal it replaced fired
    only on an all-or-nothing file, and its comment claimed it turned "any future unparseable shape
    into a loud NOT CHECKED". A file with ONE readable job and one unreadable one is not jobless, so
    nothing refused — and `job_blocks` then sliced the invisible job's text into its visible
    neighbour, crediting that neighbour with a pin it does not have. Reproduced with a QUOTED job
    key (`"prod-drift":`), which GitHub accepts and the regex rejects: rc=0, `python pin OK`, over a
    job with no `setup-python` at all. That is both r1 Highs at once, restored.
    """
    n, in_jobs = 0, False
    for line in text.split("\n"):
        if re.match(r"^jobs:\s*(#.*)?$", line):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line.startswith(" ") and not line.startswith("#"):
            break
        if re.match(r"^  \S", line) and ":" in line \
                and not re.match(r"^  ([A-Za-z_][\w-]*):(\s.*)?$", line):
            n += 1
    return n


def job_blocks(text: str) -> dict[str, str]:
    """PURE. Each job's own text, so a pin in ONE job is not credited to its sibling.

    ⛔ THIS SPLIT IS THE WHOLE POINT, AND FILE-LEVEL WOULD HAVE MISSED THE REAL BUG. Measured
    2026-09-16: `schema-gates.yml` contained a `python-version:` the entire time — in `prod-drift`.
    A file-level rule would have called that file pinned while the `schema-gates` job, which runs
    the fifteen gates, had no pin at all.
    """
    names = job_names(text)
    blocks: dict[str, str] = {}
    lines = text.split("\n")
    starts = {}
    for i, line in enumerate(lines):
        m = re.match(r"^  ([A-Za-z_][\w-]*):(\s.*)?$", line)
        if m and m.group(1) in names and m.group(1) not in starts:
            starts[m.group(1)] = i
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    for idx, (name, start) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(lines)
        # ⟳ r6 (codex) High, second half — THE BLOCK IS THE JOB'S BODY, NOT ITS KEY LINE. It used
        # to start AT the key, and `declared_pins` is called on both whole files and blocks. So a
        # job literally named `steps` shipped its own key line into the block, where — with no
        # `jobs:` header to mark it — the job-key exclusion could not see it, `min(depths)` picked
        # indent 2, and the matrix entry was credited again. `declared_pins` was fixed for the FILE
        # and still wrong for the BLOCK, which is the call `unpinned_jobs` actually makes.
        # The key is already this dict's KEY; carrying it in the value bought nothing.
        blocks[name] = "\n".join(lines[start + 1:end])
    return blocks


def unpinned_jobs(workflows: dict[str, str], exempt: dict[str, str]) -> list[str]:
    """PURE. `file:job` for every job that pins nothing and is not exempt — empty is correct."""
    missing = []
    for fname, text in sorted(workflows.items()):
        for job, block in sorted(job_blocks(text).items()):
            # ⚠ KEYED `file:job` — r1 Medium 3 (claude). Keyed by bare job name, one exemption
            # covered a same-named job in EVERY workflow, present and future.
            if f"{fname}:{job}" in exempt:
                continue
            if not declared_pins(block):
                missing.append(f"{fname}:{job}")
    return missing


def running_version(version_info: "tuple[int, int]") -> str:
    """PURE. The running interpreter as a `major.minor` string, the granularity a pin uses."""
    return f"{version_info[0]}.{version_info[1]}"


def asserts_here(env: "dict[str, str]") -> bool:
    """PURE. Whether this run must ASSERT the pin rather than merely advise about it.

    ⛔ EXTRACTED BECAUSE IT WAS THE ONE LINE NOTHING COULD DRIVE — r1 High 3 (claude). It lived
    inline in `main` as `bool(os.environ.get("GITHUB_ACTIONS"))`: the single decision that arms the
    whole assertion, with no case and no mutation touching it. A rule nobody can drive is
    documentation.
    """
    return bool(env.get("GITHUB_ACTIONS"))


def pin_took_effect(executable: str, tool_location: "str | None") -> "bool | None":
    """PURE. Did the running interpreter come FROM `setup-python`? `None` = no evidence either way.

    ⛔⛔ THE VERSION COMPARISON CANNOT ANSWER THIS, AND BELIEVING IT COULD WAS THIS BRANCH'S BIGGEST
    CLAIM — r1 High 1 (claude). `running != pin` compares major.minor, and the runner image's
    AMBIENT `python3` is already 3.12.3, so the comparison holds whether or not `setup-python` did
    anything. It is satisfied by the exact pre-branch world this guard exists to end.

    ⚠ THE SCENARIO IS A ONE-WORD EDIT. `actions/setup-python@v5` takes `update-environment`, visible
    in this branch's own run log. Set it `false` and the action still installs 3.12.14, still logs
    *"Successfully set up CPython"*, and leaves `PATH` untouched — `python3` stays the system 3.12.3,
    the version matches, and the guard prints `python pin OK` while all 45 guards run unpinned. The
    step would be present, ineffective and green: verbatim the shape this file says it catches.

    So provenance, not equality. `setup-python` exports `pythonLocation`
    (`/opt/hostedtoolcache/Python/3.12.14/x64` in this branch's log) and nothing else does; an
    interpreter running from under it came from the action.
    """
    # ⚠ `not tool_location`, NOT `is None` — r2 Low 2 (claude), and the distinction is FAIL-OPEN.
    # Narrowed to `is None`, an EMPTY `pythonLocation` gives `root = ""` and `startswith("/")` is
    # True for every absolute path on earth, certifying provenance for the ambient interpreter —
    # the precise defect this function exists to stop, restored by a plausible tightening.
    no_evidence = not tool_location
    if no_evidence:
        return None
    root = tool_location.rstrip("/")
    is_the_root = executable == root
    return is_the_root or executable.startswith(root + "/")


def verdict(workflows: dict[str, str], running: str, in_ci: bool,
            exempt: "dict[str, str] | None" = None, executable: str = "",
            tool_location: "str | None" = None) -> "tuple[int, str]":
    """PURE. `(exit code, message)`. Order matters and is asserted by its own cases."""
    exempt = EXEMPT_JOBS if exempt is None else exempt
    if not workflows:
        return 2, ("CANNOT RUN — no workflow files were read, so nothing could be compared.\n"
                   "  A zero over an empty corpus is not a pass. NOT CHECKED.")
    pins = sorted({p for text in workflows.values() for p in declared_pins(text)})
    if not pins:
        # ⚠ ASKED BEFORE the per-job question on purpose: with no pin anywhere, every job is
        # unpinned and the per-job list is just noise repeating one fact.
        return 2, ("CANNOT RUN — no `python-version:` was found in any workflow, so the interpreter\n"
                   "  CI runs is undeclared and there is nothing to compare against. That is the\n"
                   "  state this guard exists to end, not a pass. NOT CHECKED.")
    if len(pins) > 1:
        return 1, (f"FAILED — workflows pin DIFFERENT Python versions: {', '.join(pins)}.\n"
                   "  CI would then run guards on one interpreter and gates on another, and a\n"
                   "  version-dependent defect would surface in only one of them.")
    pin = pins[0]
    # ⛔ A WORKFLOW WITH NO JOBS IS NOT A THING THAT EXISTS — r1 High 2 (claude). The job scan is a
    # line scan, so an indentation this repo does not happen to use (four spaces is valid YAML)
    # makes every job INVISIBLE, and an invisible job is a PASSING job. Loosening the regex fixed
    # four shapes; this refuses the rest instead of guessing, turning any future unparseable shape
    # from a silent pass into a loud NOT CHECKED. ⚠ It is the guard being calibrated on its own
    # corpus that made this reachable at all.
    jobless = sorted(f for f, text in workflows.items()
                     if not job_names(text) or unreadable_jobs(text))
    if jobless:
        return 2, ("CANNOT RUN — a job could not be read in: " + ", ".join(jobless) + "\n"
                   "  A workflow with no jobs does not exist, so the scan is what broke — most\n"
                   "  likely an indentation or shape this line scan does not handle. Every job in\n"
                   "  such a file would otherwise be invisible, and an invisible job PASSES.\n"
                   "  NOT CHECKED.")
    missing = unpinned_jobs(workflows, exempt)
    if missing:
        return 1, (f"FAILED — {len(missing)} job(s) pin no Python version:\n    "
                   + "\n    ".join(missing)
                   + f"\n  Add `uses: actions/setup-python@v5` with `python-version: '{pin}'`, or\n"
                     "  add the job to EXEMPT_JOBS with the reason it runs no Python.\n"
                     "  ⚠ A pin in a SIBLING job does not cover this one — measured 2026-09-16.")
    if in_ci:
        # ⛔ PROVENANCE BEFORE VERSION — r1 High 1. The version comparison alone is satisfied by the
        # runner's ambient 3.12.3, so it cannot tell a working pin from no pin at all.
        effect = pin_took_effect(executable, tool_location)
        if effect is None:
            return 1, ("FAILED — `pythonLocation` is unset, so nothing shows `setup-python` ran.\n"
                       "  Only that action exports it. Without it the interpreter's PROVENANCE is\n"
                       "  unknown, and a version match proves nothing: the runner image's own\n"
                       f"  python3 is already {pin}.x.")
        if not effect:
            return 1, (f"FAILED — the pin did not take effect: the running interpreter\n"
                       f"  ({executable}) is not the one `setup-python` installed ({tool_location}).\n"
                       "  The step is present and ineffective — e.g. `update-environment: false` —\n"
                       "  which is a green that means nothing.")
        if running != pin:
            return 1, (f"FAILED — workflows pin {pin}, this interpreter is {running}.")
    if running != pin:
        return 0, (f"⚠ ADVISORY — this machine runs Python {running}; CI runs {pin}.\n"
                   "  Treat a local green as PROVISIONAL: interpreter versions differ in ways that\n"
                   "  change guard outcomes. MEASURED 2026-09-16 — `Path.is_file()` raises\n"
                   "  ENAMETOOLONG on 3.12 and returns False on 3.13+, which made CI and a dev\n"
                   "  machine disagree about the same commit.\n"
                   f"  Not a failure: most contributors will not be on {pin}, and a gate that is red\n"
                   "  from birth gets switched off (backlog #56).")
    # ⚠ r2 Low 5 (claude): a passing provenance check printed no provenance, so the log could not
    # show WHICH interpreter was certified — the evidence was discarded at the moment it was earned.
    where = f", from {tool_location}" if in_ci and tool_location else ""
    return 0, f"python pin OK — every job pins {pin}, and this interpreter is {running}{where}"


def _read_workflows() -> dict[str, str]:
    """IMPURE. Every workflow file's text, keyed by name."""
    if not WORKFLOW_DIR.is_dir():
        return {}
    found: dict[str, str] = {}
    for pattern in WORKFLOW_GLOBS:
        for wf in sorted(WORKFLOW_DIR.glob(pattern)):
            found[wf.name] = wf.read_text(encoding="utf-8", errors="replace")
    return found


def self_test() -> int:
    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

    # A provenance pair that satisfies the r1 High 1 check: the interpreter lives under the
    # location `setup-python` exports. Passed explicitly so the CI-mode cases say which world
    # they are in.
    _LOC, _EXE = "/opt/hostedtoolcache/Python/3.12.14/x64", "/opt/hostedtoolcache/Python/3.12.14/x64/bin/python3"

    def _wf(job: str, version: str) -> str:
        """A minimal workflow with ONE job pinned through a real setup-python step."""
        return (f"jobs:\n  {job}:\n    steps:\n      - uses: actions/setup-python@v5\n"
                f"        with:\n          python-version: '{version}'\n")

    PINNED = ("jobs:\n"
              "  verify:\n"
              "    steps:\n"
              "      - uses: actions/setup-python@v5\n"
              "        with:\n"
              "          python-version: '3.12'\n")
    TWO_JOBS_ONE_PIN = ("jobs:\n"
                        "  schema-gates:\n"
                        "    steps:\n"
                        "      - run: scripts/check-schema-gates.sh\n"
                        "  prod-drift:\n"
                        "    steps:\n"
                        "      - uses: actions/setup-python@v5\n"
                        "        with:\n"
                        "          python-version: '3.12'\n")

    case("a declared pin is read, quotes stripped", declared_pins(PINNED), ["3.12"])
    case("...and a workflow with none declares none", declared_pins("jobs:\n  a:\n"), [])
    case("...and an unquoted pin reads the same",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n"
                       "        with:\n"
                       "          python-version: 3.12\n"), ["3.12"])
    # ⛔ r1 HIGH (codex), AS CASES — BOTH FALSE-GREEN SHAPES IT REPRODUCED. A `python-version:` that
    # belongs to no `setup-python` step made a job with NO pin at all read as pinned: `unpinned_jobs`
    # returned [] and the verdict returned 0. A guard satisfied by a line of prose reports the
    # absence of the very thing it exists to find.
    # ⛔⛔ r2 HIGH (codex) — THE PIN MUST BE THE INPUT THE ACTION READS, which is `with.python-version`.
    # Scoping it to "inside the setup-python step" was the SECOND version of this predicate and still
    # too loose: a `python-version:` under `env:` in that same step is not an action input, so a job
    # whose setup-python never declared a version reported `python pin OK`. Third iteration — each
    # time I narrowed the SPAN instead of naming the THING.
    case("a python-version under env: in the setup-python step is NOT a pin",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n"
                       "        env:\n          python-version: '3.12'\n"), [])
    case("...while the same value under with: is",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    case("...and an env: sibling AFTER with: does not add a second, false pin",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"
                       "        env:\n          python-version: '3.11'\n"), ["3.12"])
    case("a python-version inside a run-block heredoc is NOT a pin",
         declared_pins("    steps:\n      - run: |\n          python-version: '3.12'\n"), [])
    case("...nor is one in an UNRELATED action's with: block",
         declared_pins("    steps:\n      - uses: someone/not-setup-python@v1\n"
                       "        with:\n          python-version: '3.12'\n"), [])
    # ⛔⛔ THE SHAPE THE WHOLE REDESIGN EXISTS FOR — r2 (claude) H1, and the reason `_steps` was
    # written. `declared_pins` was wrong three rounds running, and every previous version asked
    # "does the line that OPENS the step name setup-python?". That is only true when nothing is
    # written before `uses:` — and 62 of this repository's 70 steps open with `- name:`. The pin
    # became invisible, the job read as UNPINNED, and the error told the author to add the step
    # they were looking at or to exempt the job. ⚠ THE SUITE HAD NO CASE FOR THE ORDINARY IDIOM,
    # which is why three rounds of narrowing the SPAN never found it.
    case("a step whose `- name:` comes BEFORE `uses:` is still a setup-python step",
         declared_pins("    steps:\n      - name: Set up Python\n"
                       "        uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    case("...and `id:`/`if:` before `uses:` do not hide it either",
         declared_pins("    steps:\n      - id: py\n        if: always()\n"
                       "        name: Set up Python\n"
                       "        uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    case("...and `name:` AFTER `uses:` still works, the shape that always did",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n"
                       "        name: Set up Python\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⚠ THE NEGATIVE DIRECTION OF THE REDESIGN, asserted rather than assumed. Recognising a step
    # by what it CONTAINS is a wider net than matching its opening line, so the two false-green
    # shapes r1 found must be re-proved under the new rule, not inherited from the old one.
    case("a named step around an UNRELATED action is still not a pin",
         declared_pins("    steps:\n      - name: Cache things\n        uses: actions/cache@v4\n"
                       "        with:\n          python-version: '9.9'\n"), [])
    # ⛔⛔ THE FOURTH `declared_pins` DEFECT — found by the coordinator in the coordinator's OWN
    # redesign, 2026-09-21, before round 3 returned. Recognising a step by its CONTENTS fixed r2's
    # H1 and opened a FALSE GREEN in the other direction: a `uses: actions/setup-python` line
    # sitting in a shell heredoc made the step count, so an unrelated `python-version` in its
    # `with:` read as the pin and an UNPINNED job reported as pinned. The suite could not see it —
    # every existing heredoc case used a step with no `setup-python` anywhere, so none of them
    # reached the identification.
    case("setup-python INSIDE a run-block heredoc does not make a step a setup-python step",
         declared_pins("    steps:\n      - name: docs\n        run: |\n          cat <<'EOF'\n"
                       "          uses: actions/setup-python@v5\n          EOF\n"
                       "        with:\n          python-version: '9.9'\n"), [])
    # ⛔⛔ CODEX r3's FIXTURE — the FIFTH defect, and the one my own probe missed. A DASH LINE
    # inside a block scalar manufactured a PHANTOM STEP that owned the fake `with:` beneath it, so
    # a job with no setup-python anywhere returned a pin. My first repair filtered each step's body
    # AFTER the split, which never ran: the split had already happened. The mask now lives in
    # `_steps`, because "which lines are structure" is prior to "which step owns a line".
    case("a DASH LINE inside a block scalar does not manufacture a step",
         declared_pins("    steps:\n      - name: write fake workflow\n        run: |\n"
                       "          - uses: actions/setup-python@v5\n"
                       "            with:\n              python-version: '9.9'\n"), [])
    case("...and the job around it reads as UNPINNED, which is the whole point",
         sorted(unpinned_jobs({"w.yml": "jobs:\n  verify:\n    steps:\n"
                               "      - name: write fake workflow\n        run: |\n"
                               "          - uses: actions/setup-python@v5\n"
                               "            with:\n              python-version: '9.9'\n"},
                              exempt=())), ["w.yml:verify"])
    case("...nor does one in a FOLDED scalar",
         declared_pins("    steps:\n      - name: docs\n        script: >\n"
                       "          uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '9.9'\n"), [])
    case("...nor one under a chomping indicator (`|-`)",
         declared_pins("    steps:\n      - name: docs\n        run: |-\n"
                       "          uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '9.9'\n"), [])
    # ⚠ AND THE POSITIVE DIRECTION OF THE SAME MASK: dropping block-scalar CONTENT must not drop
    # the step around it. A real setup-python step followed by a step with a `run:` block still
    # yields its pin.
    case("a real pin survives a neighbouring step that owns a run block",
         declared_pins("    steps:\n      - name: Set up Python\n        uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"
                       "      - name: after\n        run: |\n          echo hi\n"), ["3.12"])
    # ⟳ r3 (claude) F5, Medium — THIS CASE USED TO PASS FOR AN AMBIENT REASON, and that is exactly
    # why the fourth defect got through it. The old fixture had NO `uses:` and NO `with:`, so it was
    # rejected by the contents test before any heredoc question arose: measured, widening the
    # contents regex to `actions/` or removing the contents test entirely left it GREEN. Nothing
    # touching heredoc handling could fail a case whose label is about heredoc handling. r2 named
    # this exact pair as the thing to watch and the rewrite re-acquired the same defect.
    # The fixture now carries a real `uses:` inside the heredoc AND a real `with:` outside it, so
    # the only thing that makes it pass is the block-scalar mask.
    case("a named step whose heredoc CONTAINS a pin line is still not a pin",
         declared_pins("    steps:\n      - name: write a file\n        run: |\n"
                       "          cat > x <<'EOF'\n"
                       "          uses: actions/setup-python@v5\n"
                       "          python-version: '9.9'\n          EOF\n"
                       "        with:\n          python-version: '9.9'\n"), [])
    # ⟳ r3 (claude) F4, Medium — SEVEN OF TEN CLAUSES OF `_steps` WERE HELD BY NOTHING, including
    # every clause of the sentinel apparatus F3 proved wrong. You could delete the whole thing and
    # the suite stayed green, which is why F3 was never going to be caught here. The sentinel is
    # gone; these two cases hold the clauses that replaced it.
    case("a SIBLING step is a new step — a pin in the SECOND of two is still found",
         declared_pins("    steps:\n      - uses: actions/cache@v4\n        with:\n          key: x\n"
                       "      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⟳ r3 F4 follow-through, the SIXTH defect — a comment at the step's own dash indent satisfied
    # the close test and ENDED THE STEP, so the pin after it vanished. Legal YAML, MISS direction.
    # ⟳ r4 (codex) High — the SEVENTH defect: a `strategy.matrix.include` entry was parsed as a
    # step, so a job with NO setup-python reported as pinned. A FALSE GREEN. ⚠ Note the fixture is
    # a WHOLE WORKFLOW, not a step fragment: the defect lives in which LIST a dash is in, and a
    # fragment cannot express that. All 22 fragment fixtures in this suite were wrapped in a real
    # `steps:` sequence for the same reason — r3 F5's lesson, that a fixture unlike real input
    # cannot fail the way real input does.
    case("a matrix.include entry is NOT a step, so its pin does not count",
         declared_pins("jobs:\n  verify:\n    strategy:\n      matrix:\n        include:\n"
                       "          - uses: actions/setup-python@v5\n            with:\n"
                       "              python-version: '9.9'\n"
                       "    steps:\n      - run: python3 --version\n"), [])
    case("...and the job around it reads UNPINNED",
         sorted(unpinned_jobs({"w.yml": "jobs:\n  verify:\n    strategy:\n      matrix:\n"
                               "        include:\n          - uses: actions/setup-python@v5\n"
                               "            with:\n              python-version: '9.9'\n"
                               "    steps:\n      - run: python3 --version\n"}, exempt=())),
         ["w.yml:verify"])
    case("a real step still counts when a matrix.include sits beside it",
         declared_pins("jobs:\n  verify:\n    strategy:\n      matrix:\n        include:\n"
                       "          - uses: actions/setup-python@v5\n            with:\n"
                       "              python-version: '9.9'\n"
                       "    steps:\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⟳ r5 (claude) F1 — an EIGHTH defect, and F2 a REGRESSION I introduced one commit earlier.
    # Both died to one invariant: a job's step list is the SHALLOWEST `steps:` in the file, so a
    # matrix dimension or an action input that happens to be NAMED `steps` is necessarily deeper.
    case("a matrix DIMENSION named `steps` is not the job's step list",
         declared_pins("jobs:\n  verify:\n    strategy:\n      matrix:\n        steps:\n"
                       "          - uses: actions/setup-python@v5\n            with:\n"
                       "              python-version: '9.9'\n"
                       "    steps:\n      - run: echo hi\n"), [])
    case("an action INPUT named `steps` does not hide the real pin (r5 F2 regression)",
         declared_pins("jobs:\n  verify:\n    steps:\n      - name: odd\n"
                       "        uses: someone/thing@v1\n        with:\n          steps:\n"
                       "            - a\n      - name: Set up Python\n"
                       "        uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⟳ r5 F3 — the CLOSING half of the steps: rule had no falsifier, and both defects above lived
    # there. A list AFTER the steps block must not be read as steps.
    case("a list after the steps block is not read as steps",
         declared_pins("jobs:\n  a:\n    steps:\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"
                       "    outputs:\n      o: v\n  b:\n    strategy:\n      matrix:\n"
                       "        include:\n          - uses: actions/setup-python@v5\n"
                       "            with:\n              python-version: '9.9'\n"), ["3.12"])
    # ⟳ r5 (codex) Medium — a `steps:` key may carry YAML NODE PROPERTIES. Accepting only a bare
    # key made a PINNED job read as UNPINNED: a regression introduced by the scoping rule itself.
    case("`steps:` with a YAML anchor still opens the step list",
         declared_pins("jobs:\n  a:\n    steps: &py\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    case("...and with a TAG",
         declared_pins("jobs:\n  a:\n    steps: !!seq\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⚠ THE NEGATIVE THAT KEEPS THE WIDENING HONEST: a real SCALAR value is not a step list, so an
    # unrelated key named `steps` must still not open a scope.
    case("a scalar `steps: '3'` is not a step list",
         declared_pins("jobs:\n  a:\n    env:\n      steps: '3'\n    steps:\n"
                       "      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⟳ r6 (codex) High — `steps` IS A VALID JOB ID, which inverted the shallowest-`steps:`
    # invariant: the job-key line at indent 2 beat the job's real step list at indent 4, so a
    # matrix entry was credited and `verdict` returned "python pin OK" for a job whose only step
    # runs `python3 --version`. TWO fixes, because `declared_pins` is called on whole FILES and on
    # job BLOCKS: job keys are excluded from the depth scan, AND a block is now the job's BODY.
    case("a job literally named `steps` does not become its own step list",
         declared_pins("jobs:\n  steps:\n    strategy:\n      matrix:\n        include:\n          - uses: actions/setup-python@v5\n            with:\n              python-version: '3.12'\n    steps:\n      - run: python3 --version\n"), [])
    case("...and that job reads UNPINNED, which is the consequence that matters",
         sorted(unpinned_jobs({"w.yml": "jobs:\n  steps:\n    strategy:\n      matrix:\n        include:\n          - uses: actions/setup-python@v5\n            with:\n              python-version: '3.12'\n    steps:\n      - run: python3 --version\n"}, exempt=())), ["w.yml:steps"])
    case("...while a job named `steps` WITH a real pin still passes",
         sorted(unpinned_jobs({"w.yml": "jobs:\n  steps:\n    steps:\n"
                               "      - uses: actions/setup-python@v5\n"
                               "        with:\n          python-version: '3.12'\n"},
                              exempt=())), [])
    case("a COMMENT at the dash indent does not end a step",
         declared_pins("    steps:\n      - name: Set up Python\n      # a comment, legal at any indent\n"
                       "        uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    case("...but a comment INSIDE a block scalar is still its CONTENT, not structure",
         declared_pins("    steps:\n      - name: x\n        run: |\n"
                       "          # uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '9.9'\n"), [])
    case("a BLANK LINE inside a step does not end it",
         declared_pins("    steps:\n      - name: Set up Python\n        uses: actions/setup-python@v5\n\n"
                       "        with:\n          python-version: '3.12'\n"), ["3.12"])
    # ⛔ AND THE STEP BOUNDARY, DRIVEN. The two cases above never reach it — neither fixture has a
    # `setup-python` step, so the scan loop never starts and the clause that ENDS a step was
    # unexercised (it survived mutation). Here a real pin is followed by a DIFFERENT action
    # carrying its own `python-version:`; without the boundary the second bleeds in and the two
    # read as a disagreement.
    case("a later step's python-version does NOT bleed into the setup-python step before it",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n"
                       "        with:\n          python-version: '3.12'\n"
                       "      - uses: someone/other@v1\n"
                       "        with:\n          python-version: '3.11'\n"), ["3.12"])
    case("...and a job holding only those still reports as unpinned",
         unpinned_jobs({"w.yml": "jobs:\n  verify:\n    steps:\n      - run: |\n"
                                 "          python-version: '3.12'\n"}, {}), ["w.yml:verify"])
    case("job keys are found", job_names(PINNED), ["verify"])
    case("...and both of two are", job_names(TWO_JOBS_ONE_PIN), ["schema-gates", "prod-drift"])
    case("...while a STEP key is not mistaken for a job",
         job_names("jobs:\n  verify:\n    steps:\n      - uses: x\n        with:\n"), ["verify"])
    # ⚠ THE FIXTURE'S TRAILING KEY IS VALUELESS ON PURPOSE. Written as `group: x` this case was
    # AMBIENT — the job regex rejects a key that has a value, so the break clause was never what
    # excluded it and deleting the break left the suite green. `group:` alone is job-shaped, so
    # only the break can reject it.
    case("...and a top-level key after jobs ends the block",
         job_names("jobs:\n  verify:\n    steps: []\nconcurrency:\n  group:\n"), ["verify"])
    # ⛔ THE CASE THE REAL BUG WOULD HAVE FAILED. `schema-gates.yml` held a `python-version:` the
    # whole time — in `prod-drift` — while the job running the fifteen gates had none.
    case("a pin in a SIBLING job does not cover its neighbour",
         unpinned_jobs({"w.yml": TWO_JOBS_ONE_PIN}, {}), ["w.yml:schema-gates"])
    case("...while a job that pins is not reported",
         unpinned_jobs({"w.yml": PINNED}, {}), [])
    case("...and an exempt job is not reported either",
         unpinned_jobs({"w.yml": TWO_JOBS_ONE_PIN}, {"w.yml:schema-gates": "runs no python"}), [])
    case("job blocks do not bleed into each other",
         "python-version" in job_blocks(TWO_JOBS_ONE_PIN)["schema-gates"], False)
    case("...and the pinning job's block does contain it",
         "python-version" in job_blocks(TWO_JOBS_ONE_PIN)["prod-drift"], True)
    # ⚠ A THIRD input to `job_blocks`, so the parameter is VARIED rather than a constant wearing a
    # signature. `check-fixture-variation.py` flagged exactly this on the first draft of this file —
    # the guard catching its own author, one day after backlog #137 closed for the same defect.
    case("...and a single-job workflow yields that job's block whole",
         "python-version" in job_blocks(PINNED)["verify"], True)
    case("the running version is major.minor", running_version((3, 12)), "3.12")
    case("...and a two-digit minor is not truncated", running_version((3, 14)), "3.14")

    # ── verdict, and the ORDER of its questions ────────────────────────────────────────────────
    # ⚠ ASSERTS THE MESSAGE, NOT JUST THE CODE — r-lesson from backlog #137's `declared_not_derived`.
    # With the empty-corpus guard deleted, execution falls through to the NO-PINS guard and returns
    # the same 2 by another route, so an exit-code case cannot see its own clause.
    case("no workflows at all is CANNOT RUN, never a pass",
         (verdict({}, "3.12", True)[0], "no workflow files were read" in verdict({}, "3.12", True)[1]),
         (2, True))
    case("...and so is a corpus with no pin anywhere",
         verdict({"w.yml": "jobs:\n  a:\n    steps: []\n"}, "3.12", True)[0], 2)
    case("...and THAT is asked before the per-job question, which would only repeat it",
         "no `python-version:`" in verdict({"w.yml": "jobs:\n  a:\n"}, "3.12", True)[1], True)
    case("disagreeing pins FAIL",
         verdict({"a.yml": _wf("x", "3.12"), "b.yml": _wf("y", "3.11")}, "3.12", True)[0], 1)
    case("...and the message names both", "3.11, 3.12" in
         verdict({"a.yml": _wf("x", "3.12"), "b.yml": _wf("y", "3.11")}, "3.12", True)[1], True)
    case("an unpinned job FAILS", verdict({"w.yml": TWO_JOBS_ONE_PIN}, "3.12", True)[0], 1)
    # ⚠ ...and the SAME workflow passes once that job is exempt — which is what varies
    # `verdict.exempt`, and is the only case that proves the verdict consults it at all rather than
    # reading the module constant behind it.
    case("...and the SAME workflow passes once that job is exempt, so the verdict really reads it",
         verdict({"w.yml": TWO_JOBS_ONE_PIN}, "3.12", True,
                 {"w.yml:schema-gates": "runs no python"}, _EXE, _LOC)[0], 0)
    # ⛔ r1 MEDIUM 3 — the key includes the FILE. Keyed by bare job name, one exemption silently
    # covered a same-named job in every other workflow, present and future.
    case("...and an exemption in ANOTHER file does not cover this one",
         unpinned_jobs({"w.yml": TWO_JOBS_ONE_PIN}, {"other.yml:schema-gates": "runs no python"}),
         ["w.yml:schema-gates"])
    case("...and the failure names it",
         "w.yml:schema-gates" in verdict({"w.yml": TWO_JOBS_ONE_PIN}, "3.12", True)[1], True)
    # ⛔ THE TWO-QUESTIONS-ONE-RULE SPLIT. Same inputs, different place, deliberately different code.
    case("IN CI a mismatch FAILS, because it means the pin did not take effect",
         verdict({"w.yml": PINNED}, "3.14", True)[0], 1)
    # ⚠ WITH PROVENANCE SATISFIED, so this reaches the VERSION clause rather than stopping at the
    # provenance one. Without this the version test inside `in_ci` was unreachable and its mutation
    # survived — every CI case happened to match the pin.
    case("...and it still FAILS when provenance is fine but the VERSION is wrong",
         verdict({"w.yml": PINNED}, "3.14", True, None, _EXE, _LOC)[0], 1)
    case("...but LOCALLY the same mismatch is ADVISORY and exits 0",
         verdict({"w.yml": PINNED}, "3.14", False)[0], 0)
    case("...and the advisory names the version CI actually runs",
         "CI runs 3.12" in verdict({"w.yml": PINNED}, "3.14", False)[1], True)
    # ⚠ THE EXPECTED VALUE IS A LITERAL, NOT A CALL — r1 Low 1 (claude): this case used to compute
    # its own `want` by invoking the very function under test, so it could not fail.
    case("a matching interpreter WITH provenance is OK in CI",
         verdict({"w.yml": PINNED}, "3.12", True, None, _EXE, _LOC)[0], 0)
    case("...and the OK message names the pin",
         "every job pins 3.12" in verdict({"w.yml": PINNED}, "3.12", True, None, _EXE, _LOC)[1], True)
    # ⛔⛔ r1 HIGH 1, AS CASES — the version comparison alone is satisfied by the runner's AMBIENT
    # 3.12.3, so it cannot tell a working pin from no pin. Provenance can.
    # ⚠ ASSERTS THE MESSAGE — the code alone cannot see this clause, because falling through to the
    # next one (`not effect`, where `not None` is True) returns the same 1 by another route. Same
    # masking shape as backlog #137's `declared_not_derived`, third occurrence across the two branches.
    case("IN CI, a matching VERSION with no provenance FAILS — the ambient python matches too",
         (verdict({"w.yml": PINNED}, "3.12", True, None, "/usr/bin/python3", None)[0],
          "`pythonLocation` is unset" in
          verdict({"w.yml": PINNED}, "3.12", True, None, "/usr/bin/python3", None)[1]), (1, True))
    case("...and an interpreter NOT under the exported location FAILS, which is update-environment: false",
         verdict({"w.yml": PINNED}, "3.12", True, None, "/usr/bin/python3", _LOC)[0], 1)
    case("pin_took_effect says None when nothing exported a location",
         pin_took_effect("/usr/bin/python3", None), None)
    case("...True when the interpreter lives under it",
         pin_took_effect(_EXE, _LOC), True)
    case("...and False when it does not",
         pin_took_effect("/usr/bin/python3", _LOC), False)
    case("...and a sibling directory sharing a PREFIX is not under it",
         pin_took_effect("/opt/hostedtoolcache/Python/3.12.14/x64-other/bin/python3", _LOC), False)
    # ⛔ r1 HIGH 3 — the one line that arms the assertion, now drivable.
    case("GITHUB_ACTIONS arms the assertion", asserts_here({"GITHUB_ACTIONS": "true"}), True)
    case("...and its absence does not", asserts_here({}), False)
    case("...and an empty value does not either", asserts_here({"GITHUB_ACTIONS": ""}), False)
    # ⛔ r1 HIGH 2 — a workflow whose jobs cannot be read is CANNOT RUN, not a pass.
    # ⛔ r2 MEDIUM 1 — an UNREADABLE job among readable ones. A quoted key is accepted by GitHub and
    # rejected by the job regex; the old refusal only fired on an all-or-nothing file, so this
    # passed with rc=0 while `job_blocks` credited the invisible job's pin to its neighbour.
    _QUOTED = ("jobs:\n  verify:\n    steps:\n      - run: echo hi\n"
               '  "prod-drift":\n    steps:\n      - uses: actions/setup-python@v5\n'
               "        with:\n          python-version: '3.12'\n")
    # ⛔ r1 LOW 2 — the corpus must read BOTH extensions; `.yaml` was unguarded and its removal
    # survived mutation.
    case("the corpus reads both workflow extensions", sorted(WORKFLOW_GLOBS), ["*.yaml", "*.yml"])
    case("a job key the scan cannot read is COUNTED, not ignored", unreadable_jobs(_QUOTED), 1)
    case("...and a workflow containing one is CANNOT RUN even though another job IS readable",
         verdict({"w.yml": _QUOTED}, "3.12", True, None, _EXE, _LOC)[0], 2)
    case("...while a workflow whose jobs all parse counts none unreadable",
         unreadable_jobs(PINNED), 0)
    # ⛔ r2 MEDIUM 3 — r1's inline-comment fix had no case at all; deleting it left the suite green.
    case("an inline comment on the pin line is stripped from the VALUE",
         declared_pins("    steps:\n      - uses: actions/setup-python@v5\n        with:\n"
                       "          python-version: '3.12'  # matches the Dockerfile\n"), ["3.12"])
    # ⛔ r2 LOW 2 — three clauses of pin_took_effect were undriven, and the first is FAIL-OPEN:
    # narrowed to `is None`, an EMPTY location makes startswith("/") true for every absolute path.
    case("an EMPTY exported location is no evidence, not proof of provenance",
         pin_took_effect("/usr/bin/python3", ""), None)
    case("...and a trailing slash on the location does not break it",
         pin_took_effect(_EXE, _LOC + "/"), True)
    case("...and the location itself, as an executable, counts as under it",
         pin_took_effect(_LOC, _LOC), True)
    case("a workflow yielding NO jobs is CANNOT RUN, because an invisible job passes",
         verdict({"w.yml": PINNED, "four.yml": "jobs:\n    deploy:\n        steps: []\n"},
                 "3.12", True, None, _EXE, _LOC)[0], 2)
    # ⛔ r2 LOW 3 — `verdict`'s docstring says the order "is asserted by its own cases"; the jobless
    # refusal's POSITION was not. Both conditions hold here, and the jobless one must answer.
    case("the unreadable-job refusal is asked BEFORE the unpinned-job question",
         "could not be read" in
         verdict({"w.yml": _QUOTED}, "3.12", True, None, _EXE, _LOC)[1], True)
    case("...and it names the file that could not be read",
         "four.yml" in verdict({"w.yml": PINNED, "four.yml": "jobs:\n    deploy:\n        steps: []\n"},
                               "3.12", True, None, _EXE, _LOC)[1], True)

    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"  ok     {name}" if ok else f"  [FAIL] {name}: got {got!r} want {want!r}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    rc, msg = verdict(_read_workflows(), running_version(sys.version_info[:2]),
                      asserts_here(dict(os.environ)), None,
                      sys.executable, os.environ.get("pythonLocation"))
    print(msg, file=sys.stderr if rc else sys.stdout)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

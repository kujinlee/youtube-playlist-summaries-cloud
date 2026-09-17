#!/usr/bin/env python3
"""Every CI job pins the Python interpreter, the pins agree, and the pin actually took effect.

    python3 scripts/check-python-pin.py              # in CI: asserts. locally: advises.
    python3 scripts/check-python-pin.py --self-test  # 28 cases

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
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / ".github" / "workflows"

# Jobs that genuinely run no Python, with the reason. ⚠ A NAME plus a REASON, not a count: a bare
# count is satisfied by exempting a new job and fixing an old one, which is how an allow-list stops
# meaning anything. Empty today — every job in this repository runs Python, directly or through a
# shell script — and that is itself worth stating, because an empty allow-list is the strongest
# form and someone will be tempted to add to it rather than add two lines of YAML.
EXEMPT_JOBS: dict[str, str] = {}


def declared_pins(text: str) -> list[str]:
    """PURE. Every `python-version:` value a workflow declares, in file order.

    A LINE SCAN, not a YAML parse, and deliberately: PyYAML is not installed in this repository and
    two sibling guards already read workflows as plain text (`check-ratchet-contract.py`'s
    `ci_path`, and `check-review-recorded.py` before #137 moved its authority elsewhere).
    """
    return [m.group(1).strip().strip("'\"")
            for m in re.finditer(r"^\s*python-version:\s*(.+?)\s*$", text, re.M)]


def job_names(text: str) -> list[str]:
    """PURE. The job keys of a workflow, in file order.

    Jobs are the two-space-indented keys under a top-level `jobs:`. Anything more clever needs a
    YAML parser; anything less cannot tell a job from a step key.
    """
    out: list[str] = []
    in_jobs = False
    for line in text.split("\n"):
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs:
            if line and not line.startswith(" ") and not line.startswith("#"):
                break                      # a new top-level key ends the jobs block
            m = re.match(r"^  ([A-Za-z_][\w-]*):\s*$", line)
            if m:
                out.append(m.group(1))
    return out


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
        m = re.match(r"^  ([A-Za-z_][\w-]*):\s*$", line)
        if m and m.group(1) in names and m.group(1) not in starts:
            starts[m.group(1)] = i
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    for idx, (name, start) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(lines)
        blocks[name] = "\n".join(lines[start:end])
    return blocks


def unpinned_jobs(workflows: dict[str, str], exempt: dict[str, str]) -> list[str]:
    """PURE. `file:job` for every job that pins nothing and is not exempt — empty is correct."""
    missing = []
    for fname, text in sorted(workflows.items()):
        for job, block in sorted(job_blocks(text).items()):
            if job in exempt:
                continue
            if not declared_pins(block):
                missing.append(f"{fname}:{job}")
    return missing


def running_version(version_info: "tuple[int, int]") -> str:
    """PURE. The running interpreter as a `major.minor` string, the granularity a pin uses."""
    return f"{version_info[0]}.{version_info[1]}"


def verdict(workflows: dict[str, str], running: str, in_ci: bool,
            exempt: "dict[str, str] | None" = None) -> "tuple[int, str]":
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
    missing = unpinned_jobs(workflows, exempt)
    if missing:
        return 1, (f"FAILED — {len(missing)} job(s) pin no Python version:\n    "
                   + "\n    ".join(missing)
                   + f"\n  Add `uses: actions/setup-python@v5` with `python-version: '{pin}'`, or\n"
                     "  add the job to EXEMPT_JOBS with the reason it runs no Python.\n"
                     "  ⚠ A pin in a SIBLING job does not cover this one — measured 2026-09-16.")
    if in_ci and running != pin:
        return 1, (f"FAILED — the pin did not take effect: workflows pin {pin}, this interpreter is\n"
                   f"  {running}. A `setup-python` step that is present but ineffective is a green\n"
                   "  that means nothing.")
    if running != pin:
        return 0, (f"⚠ ADVISORY — this machine runs Python {running}; CI runs {pin}.\n"
                   "  Treat a local green as PROVISIONAL: interpreter versions differ in ways that\n"
                   "  change guard outcomes. MEASURED 2026-09-16 — `Path.is_file()` raises\n"
                   "  ENAMETOOLONG on 3.12 and returns False on 3.13+, which made CI and a dev\n"
                   "  machine disagree about the same commit.\n"
                   f"  Not a failure: most contributors will not be on {pin}, and a gate that is red\n"
                   "  from birth gets switched off (backlog #56).")
    return 0, f"python pin OK — every job pins {pin}, and this interpreter is {running}"


def _read_workflows() -> dict[str, str]:
    """IMPURE. Every workflow file's text, keyed by name."""
    if not WORKFLOW_DIR.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))}


def self_test() -> int:
    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

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
         declared_pins("      python-version: 3.12\n"), ["3.12"])
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
         unpinned_jobs({"w.yml": TWO_JOBS_ONE_PIN}, {"schema-gates": "runs no python"}), [])
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
         verdict({"a.yml": "jobs:\n  x:\n          python-version: '3.12'\n",
                  "b.yml": "jobs:\n  y:\n          python-version: '3.11'\n"}, "3.12", True)[0], 1)
    case("...and the message names both", "3.11, 3.12" in
         verdict({"a.yml": "jobs:\n  x:\n          python-version: '3.12'\n",
                  "b.yml": "jobs:\n  y:\n          python-version: '3.11'\n"}, "3.12", True)[1], True)
    case("an unpinned job FAILS", verdict({"w.yml": TWO_JOBS_ONE_PIN}, "3.12", True)[0], 1)
    # ⚠ ...and the SAME workflow passes once that job is exempt — which is what varies
    # `verdict.exempt`, and is the only case that proves the verdict consults it at all rather than
    # reading the module constant behind it.
    case("...and the SAME workflow passes once that job is exempt, so the verdict really reads it",
         verdict({"w.yml": TWO_JOBS_ONE_PIN}, "3.12", True,
                 {"schema-gates": "runs no python"})[0], 0)
    case("...and the failure names it",
         "w.yml:schema-gates" in verdict({"w.yml": TWO_JOBS_ONE_PIN}, "3.12", True)[1], True)
    # ⛔ THE TWO-QUESTIONS-ONE-RULE SPLIT. Same inputs, different place, deliberately different code.
    case("IN CI a mismatch FAILS, because it means the pin did not take effect",
         verdict({"w.yml": PINNED}, "3.14", True)[0], 1)
    case("...but LOCALLY the same mismatch is ADVISORY and exits 0",
         verdict({"w.yml": PINNED}, "3.14", False)[0], 0)
    case("...and the advisory names the version CI actually runs",
         "CI runs 3.12" in verdict({"w.yml": PINNED}, "3.14", False)[1], True)
    case("a matching interpreter is OK in CI", verdict({"w.yml": PINNED}, "3.12", True), (0, verdict({"w.yml": PINNED}, "3.12", True)[1]))
    case("...and the OK message names the pin",
         "every job pins 3.12" in verdict({"w.yml": PINNED}, "3.12", True)[1], True)

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
                      bool(os.environ.get("GITHUB_ACTIONS")))
    print(msg, file=sys.stderr if rc else sys.stdout)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

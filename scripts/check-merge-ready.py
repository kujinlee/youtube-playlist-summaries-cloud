#!/usr/bin/env python3
"""Is this branch's pull request actually ready to merge? One command, one verdict.

    python3 scripts/check-merge-ready.py           # this branch's PR
    python3 scripts/check-merge-ready.py --pr 324
    python3 scripts/check-merge-ready.py --self-test # 211 cases
    python3 scripts/check-merge-ready.py --pr 324 --app-tests-passed <head sha>   # after a local
                                                 # test:integration + test:e2e run at that head

    0 = READY   1 = NOT READY   2 = CANNOT RUN   3 = HOLD (ready, but a house-rule exception
    applies: do NOT merge, tell the owner — see `hold_reasons`)

⛔ WHY THIS EXISTS, MEASURED 2026-09-20. Twice in one day a branch was declared "ready to merge"
on the strength of a local gate sweep, and twice CI refused it. Both times the refusal was
correct and both times the failing gate was one a working copy CANNOT ANSWER:

  * `check-dashboard-entry.py` asks whether the BRANCH recorded what it changed.
  * `check-review-recorded.py` asks whether a review round saw the code, and reads the PULL
    REQUEST BODY for its waiver — so it only runs on a `pull_request` event at all.

MEASURED over `.github/workflows/ci.yml`: **52 steps carry a `run:`, and exactly 2 are gated on
`github.event_name == 'pull_request'`.** A local sweep covers 50 of 52 and is blind to precisely
the two that have blocked every pull request this session. "All my gates are green" and "this PR
can merge" were never the same claim, and the gap is small enough to be invisible and reliable
enough to be certain.

⭐ THE PR-ONLY LIST IS DERIVED FROM THE WORKFLOW, NEVER HAND-WRITTEN. A second copy of "which
steps are PR-only" would drift the first time someone adds one, and it would drift SILENTLY —
this checker would go on reporting ready while a new gate refused. `pr_only_steps()` parses
`ci.yml`, so adding a PR-only step to CI adds it here with no edit. This is
`docs/portable-practices.md` §21/§25: the RULE is pure and the FETCH is separate, and the thing
that goes wrong is almost never the rule.

NO-CALLER: this is run BY a human (or an agent acting for one) immediately before merging, and
wiring it into CI would be circular — it READS `gh pr checks`, so a CI job running it would be
waiting on a verdict that includes itself. Its subject is the PULL REQUEST, which does not exist
at the moment CI's own steps run. The gates it invokes are each separately called by CI; what has
no caller is the act of asking them all at once, which is exactly the question CI cannot ask.

⚠ "CANNOT RUN" IS A FAILURE. No `gh`, no network, no pull request for this branch, an unreadable
workflow — every one of those returns **2** and says to treat the answer as NOT RUN. A merge-
readiness checker that shrugs is worse than none, because its silence reads as a pass.
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / ".github" / "workflows"
# ⛔ EVERY WORKFLOW, NOT `ci.yml` ALONE — Claude r1, Medium. The first version parsed one file and
# claimed the pull-request-only list was "derived, never hand-written"; the FILE SCOPE was the
# hand-written part. `schema-gates` is the other required context on every PR, so a gate added
# there was invisible to a derivation that congratulated itself on being immune to exactly that.
WORKFLOW = WORKFLOW_DIR / "ci.yml"   # kept: the steps this script can actually invoke live here

# ⛔ MATCH THE `if:` FIELD, NOT ANY LINE CONTAINING THE STRING — code review r1 (Codex), Medium.
# The first version substring-scanned every line after a `name:`, which was wrong in BOTH
# directions and one of them is the dangerous one:
#   * `if: github.event_name == "pull_request"` (double quotes, valid YAML) returned NOTHING —
#     a PR-only step MISSED, which is this script silently reporting READY while a gate refuses.
#   * `# if: …` in a comment, and `run: echo "github.event_name == 'pull_request'"`, both returned
#     the step — a false positive that would run a gate CI does not.
# Today's ci.yml happens to use single quotes throughout, so neither was live; the claim that the
# list is DERIVED was the part that was brittle, and a derivation only as good as one spelling is
# a hand-written list wearing a parser.
IF_FIELD = re.compile(r"^\s*if:\s*(?P<cond>.+?)\s*$")
# `github.event_name` compared to `pull_request` in either quote style, with or without `${{ }}`.
PR_ONLY_COND = re.compile(r"github\.event_name\s*==\s*['\"]pull_request['\"]")

# ⛔ origin/master, NEVER bare `master`. Measured 2026-09-20: the local ref was TWO PRs stale, and
# `git rev-list --count HEAD..master` answered 0 — a reassuring number about the wrong subject. A
# review package built from it silently contained an entire already-merged PR.
BASE_REF = "origin/master"

# One spelling, read by both reporting sites. rc=2 is `??` and not `NO`: a check that could not
# run is an ABSENT check, and showing it as a failure sends the reader to fix the wrong thing.
MARK = {0: "ok ", 1: "NO ", 2: "?? "}

# GitHub's MergeStateStatus, verified by live introspection rather than recalled — Codex r2, Low,
# which checked with `gh api graphql`: the enum is BEHIND, BLOCKED, CLEAN, DIRTY, HAS_HOOKS,
# UNKNOWN, UNSTABLE. An earlier comment here added DRAFT, which is not a member; draftness is its
# own `isDraft` field and is checked separately above. An enumeration that invents a member is the
# same defect as one that omits it.
# The MergeStateStatus values for which GitHub will merge. ⚠ UNSTABLE is allowed HERE because this
# function answers "would GitHub merge it"; the CI check below is deliberately STRICTER and refuses
# any non-passing check, required or not. Claude r1, Low: the old comment claimed UNSTABLE "must
# not be refused", which the overall verdict then refused one line later — an intent the tool did
# not have. Saying which layer is strict, and why, is the honest version.
MERGEABLE_STATES = ("CLEAN", "UNSTABLE", "HAS_HOOKS")


# ── THE RULES, pure ───────────────────────────────────────────────────────────────────────────
def _cond_at(lines: list[str], idx: int) -> str | None:
    """The condition value of the `if:` at `lines[idx]`, following a folded/literal scalar. PURE.

    ⛔ `if: >` and `if: |` put the condition on the FOLLOWING lines — Codex r2, High. Reading only
    the physical `if:` line returned an empty condition and the step was silently dropped.
    """
    m = re.match(r"(\s*)-?\s*if:\s*(.*)$", lines[idx])
    if not m:
        return None
    indent, first = len(m.group(1)), m.group(2).strip()
    if first not in (">", "|", ">-", "|-", ">+", "|+"):
        return first
    out = []
    for line in lines[idx + 1:]:
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= indent:
            break
        out.append(line.strip())
    return " ".join(out)


def pr_only_steps(workflow: str) -> list[str]:
    """Names of the workflow STEPS gated on a pull_request event. PURE.

    ⛔ FOURTH SHAPE IN THREE ROUNDS, AND EVERY EARLIER ONE FAILED IN THE SILENT DIRECTION — which
    for this script means reporting READY while a gate refuses. The history is the argument for
    `unattributed_conditions()` below, not a series of near-misses:
      * v1 substring-scanned after a `name:`: a DOUBLE-QUOTED condition returned nothing.
      * v2 matched the `if:` field but bound it to the nearest preceding `- name:`, so a JOB-level
        condition attached to the last step of the PREVIOUS job.
      * v3 was a block parser that took the FIRST `if:`-looking line ANYWHERE in the block — so an
        `if:` inside a `run: |` body or a `with:` map shadowed the real step-level one, and the
        step vanished. Folded scalars (`if: >`) vanished too.

    ⭐ THE REAL LESSON, and why the fix is not a fifth regex: this is a hand-rolled YAML parser and
    the project is stdlib-only, so `yaml` is unavailable. A hand-rolled parser CANNOT be made
    correct. It CAN be made unable to be silently wrong — which is what the soundness check does.

    An `if:` counts only at the step's own KEY INDENT: deeper is inside `with:`/`run:`, shallower
    belongs to the job.
    """
    lines = workflow.split("\n")
    names: list[str] = []
    step_indent: int | None = None
    key_indent: int | None = None
    name = cond = None

    def flush() -> None:
        nonlocal name, cond
        if name and cond and PR_ONLY_COND.search(cond):
            names.append(name)
        name = cond = None

    for n, line in enumerate(lines):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if re.match(r"\s*-\s", line) and (step_indent is None or indent <= step_indent):
            flush()
            step_indent, key_indent = indent, indent + 2
        elif step_indent is not None and indent <= step_indent:
            flush()
            step_indent = key_indent = None
        if step_indent is None:
            continue
        # ⚠ AT THE KEY INDENT ONLY. `- name: x` puts its key at `indent + 2`; a `with:` entry or a
        # `run: |` body line is deeper and must not be read as the step's condition.
        at_key = indent == key_indent or (re.match(r"\s*-\s", line) and indent == step_indent)
        if not at_key:
            continue
        m = re.match(r"\s*-?\s*name:\s*(.+?)\s*$", line)
        if m and name is None:
            name = m.group(1)
        if re.match(r"\s*-?\s*if:\s*", line):
            c = _cond_at(lines, n)
            if c and cond is None:
                cond = c
    flush()
    return names


def job_level_gates(workflow: str) -> list[str]:
    """Job names gated on a pull_request event. PURE.

    A gated JOB has no step name, so `pr_only_steps` cannot report it and must not pretend to.
    Folded scalars are followed here too — Codex r2, High: a job with `if: >` was dropped, which
    violated this function's whole contract of naming what the other one cannot.
    """
    lines = workflow.split("\n")
    jobs: list[str] = []
    current: str | None = None
    for n, line in enumerate(lines):
        m = re.match(r"  (\w[\w-]*):\s*$", line)
        if m:
            current = m.group(1)
            continue
        if current and re.match(r"    if:\s*", line):
            c = _cond_at(lines, n)
            if c and PR_ONLY_COND.search(c):
                jobs.append(current)
            current = None
    return jobs


# ⭐ EVERY `pull_request` MENTION IN EVERY WORKFLOW, ACCOUNTED FOR BY HAND, WITH A REASON.
# This is a RATCHET, the same shape as EXPECTED_MUTATIONS and EXAMINED_KEYS: a newly appearing
# mention is REFUSED until a human classifies it. Keyed by (file, stripped line) -> (count, why).
#
# ⛔ IT DOES NO PARSING, AND THAT IS THE ENTIRE POINT — Claude r2, High, which broke the previous
# design two ways. That version audited the parser by re-detecting condition LINES, and its
# detector was WEAKER than the parser it audited: `_cond_at()` joins a folded scalar's
# continuation lines before matching, the auditor matched single lines, so a condition split
# across a line break was invisible to BOTH — the parser did not claim it and the auditor saw
# nothing left over. A real gate vanished with the soundness check reporting clean. It also
# compared a COUNT against a COUNT, so a claim with no matching line created a surplus that
# absorbed a genuine miss. An auditor that re-implements its subject's hardest job, more weakly,
# certifies a parse it could not perform.
#
# ⛔ AND THE FIRST VERSION OF THIS PARAGRAPH OVERCLAIMED — Codex r3, High. It said a substring scan
# "cannot be weaker than the parser". False: PR-ONLY-NESS CAN BE EXPRESSED WITHOUT THE WORD.
# `ci.yml` runs on exactly `pull_request` and `push`, so `if: github.event_name != 'push'` gates a
# step on pull requests only — the parser does not claim it (PR_ONLY_COND matches equality to
# 'pull_request') and a scan for `pull_request` sees nothing to leave over. Verified by probe:
# both returned empty. Not present in either workflow today, but the CLAIM was wrong, and a claim
# that a hole is closed is worse than a known hole.
#
# So the scan keys on `github.event_name` TOO, which is the class rather than the instance: any
# event-name gating, in any spelling — `!=`, `||`, `contains()` — must be accounted for. That is a
# wider over-approximation and costs four more allow-list entries, all in schema-gates.yml, each
# of which has to say why it is not a pull-request gate this script must run.
#
# It over-approximates on purpose: the cost of a new mention is a REFUSAL TO ANSWER that a human
# clears in one line, and the cost of the alternative was a confident READY over a gate nobody
# knew about. Over-approximation is the only safe direction here.
#
# ⚠ STILL NOT AIRTIGHT, and saying so is the point of the sentence that replaced the overclaim: a
# gate keyed on something other than `github.event_name` — `startsWith(github.ref, 'refs/pull/')`,
# `github.head_ref` (unset on a push), `github.base_ref`, `github.event.number`, or a composite
# action's own workflow — would escape both. Measured 2026-09-20: neither workflow contains any
# such form. The bound is stated rather than implied.
#
# ⚠ AND A SECOND BOUND — Claude r3, Low. An entry's REASON can be true today and false tomorrow
# without its key changing, because PR-only-ness by exclusion is a property of (line × TRIGGER
# SET) and only the line is keyed. `if: github.event_name != 'schedule'` is not a pull-request
# gate only because `schema-gates.yml` also runs on `push`; delete that trigger and the same line
# becomes one, with the key, the allowance and every rule here unchanged. Rare and conspicuous,
# so it is recorded rather than mechanised — but an allow-list reason is a claim with an
# expiry date, and the expiry is not in the key.
ACCOUNTED_MENTIONS: dict[tuple[str, str], tuple[int, str]] = {
    # ⟳ 2026-10-20, backlog #173. The mutation sweep now skips when no `scripts/**` file changed,
    # and the step that decides needs the BASE REF — which differs by event: `origin/<base_ref>`
    # on a pull request, `HEAD^` on a push. ⚠ THIS IS NOT A PR-ONLY GATE and must not be read as
    # one: the step runs on EVERY event and the sweep step it gates runs on every event too. The
    # mention is a base-ref selection inside a shell block, not a conditional on the step.
    ("ci.yml", 'if [ "${{ github.event_name }}" = "pull_request" ]; then'):
        (1, "backlog #173's base-ref selection — picks origin/<base_ref> vs HEAD^ for the "
            "changed-file diff; it gates nothing and runs on every event"),
    ("ci.yml", "pull_request:"):
        (1, "the workflow TRIGGER — says when CI runs, gates nothing"),
    ("ci.yml", "if: github.event_name == 'pull_request'"):
        # ⟳ 2026-10-15: 2 -> 3. `check-reference-namespace.py` is PR-only BY NECESSITY, not by
        # choice: its subject is "what this branch ADDED", so it needs a base ref, and
        # `GITHUB_BASE_REF` is set only on a pull_request event. ⚠ Its `--self-test` runs
        # UNCONDITIONALLY in the same workflow, so the guard still has one witness on every push —
        # a guard whose every caller is conditional has none.
        # ⟳⟳ 2026-10-15, backlog #49: 3 -> 4. `check-doc-citations.py` is PR-only for the same
        # reason as its neighbour — its subject is what this branch ADDED, so it needs a base
        # ref. Its `--self-test` is unconditional too, so it keeps a witness on every push.
        (4, "the four pull-request-only steps: the two this script invokes itself, plus the "
            "reference-namespace and doc-citations gates, neither of which can run without a "
            "base ref"),
    ("ci.yml", "BODY: ${{ github.event.pull_request.body }}"):
        (2, "the env those two steps read their waiver from"),
    ("schema-gates.yml", "pull_request:"):
        (1, "the workflow TRIGGER — schema-gates has no pull-request-only step or job"),
    # ⟳ Codex r3, High: the detector now keys on `github.event_name` as well, because PR-only-ness
    # can be expressed by EXCLUSION. These four are every event-name mention in schema-gates.yml,
    # and none gates on pull requests.
    ("schema-gates.yml",
     "group: schema-gates-${{ github.workflow }}-${{ github.event_name }}-${{ github.ref }}"):
        (1, "a concurrency KEY, not a condition — it groups runs, it does not gate them"),
    ("schema-gates.yml", "if: github.event_name != 'schedule'"):
        (1, "gates the PR/push job away from the SCHEDULED run; true on a pull request AND on a "
            "push, so it is not pull-request-only and this script has no step to invoke for it"),
    ("schema-gates.yml",
     "if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"):
        (1, "the prod-drift job — the opposite of pull-request-only; never runs on a PR"),
}


def workflow_files(directory: Path) -> list[Path]:
    """Every GitHub Actions workflow in `directory`. PURE apart from the listing.

    ⛔ `.yaml` IS A WORKFLOW TOO — Claude r3, Medium, and it is r1's Medium one level down. That
    round found the FILE SCOPE was the hand-written part of a derivation congratulating itself on
    being derived; the fix parsed every file instead of `ci.yml` — and left the PATTERN hand-written.
    GitHub: a workflow "must have either a `.yml` or a `.yaml` file extension." A `release.yaml`
    carrying a pull-request gate was invisible to the parser, to the job rule AND to the ratchet, so
    nothing stray appeared and the script printed READY. Not live (no `.yaml` today) — but a NEW
    workflow is exactly where the extension is a coin flip, and a new workflow is the case the
    ratchet exists for.

    One home for the pattern, so the next reader cannot fix two of the three call sites.
    """
    return sorted(set(directory.glob("*.yml")) | set(directory.glob("*.yaml")))


def unaccounted_mentions(workflow: str, filename: str) -> list[str]:
    """Non-comment lines mentioning `pull_request` that ACCOUNTED_MENTIONS does not cover. PURE.

    ⚠ A line appearing MORE often than its allowance is unaccounted too — otherwise adding a
    second copy of an approved gate would pass on the first one's ticket, which is how a ratchet
    keyed on presence rather than count leaks.
    """
    seen: dict[tuple[str, str], int] = {}
    stray: list[str] = []
    for line in workflow.split("\n"):
        s = line.strip()
        if s.startswith("#"):
            continue
        if "pull_request" not in s and "github.event_name" not in s:
            continue
        key = (filename, s)
        seen[key] = seen.get(key, 0) + 1
        allowed = ACCOUNTED_MENTIONS.get(key, (0, ""))[0]
        if seen[key] > allowed:
            stray.append(f"{filename}: {s}")
    return stray


def verdict(results: dict[str, int]) -> tuple[int, str]:
    """Collapse per-check exit codes into one answer. PURE.

    ⚠ 2 BEATS 1. A check that could not run is not a failing check — it is an ABSENT check, and
    reporting "not ready, 1 failure" for it would send the reader to fix the wrong thing. The
    order matters more than it looks: `any(v == 1 …)` first would swallow a CANNOT RUN whenever
    anything else happened to fail.
    """
    if not results:
        return 2, "CANNOT RUN — nothing was checked. Treat this as NOT RUN."
    if any(v == 2 for v in results.values()):
        cannot = sorted(k for k, v in results.items() if v == 2)
        return 2, ("CANNOT RUN — " + ", ".join(cannot)
                   + " could not reach what they measure. Treat this as NOT RUN.")
    if any(v != 0 for v in results.values()):
        failed = sorted(k for k, v in results.items() if v != 0)
        return 1, "NOT READY — " + ", ".join(failed)
    return 0, "READY — every gate CI will run has been run here, including the PR-only ones"


def mergeability(info: dict, local_head: str | None) -> tuple[int, str]:
    """Can GitHub actually merge this PR, setting checks aside? PURE.

    ⛔ CODE REVIEW r1 (Codex), HIGH — AND IT IS THIS SCRIPT'S ONE CATASTROPHIC FAILURE. The first
    version read only the check buckets, so a DRAFT, a CONFLICTED branch, a PR based on the wrong
    branch, or `--pr` aimed at somebody else's green PR all reported **READY**. "Checks are green"
    and "GitHub will merge this" are different claims, and a merge-readiness checker that conflates
    them is worse than none: it is confidently wrong at the exact moment someone is trusting it.

    ⚠ `head` is compared to the LOCAL HEAD on purpose. `--pr 999` on an unrelated branch is the
    easiest way to get a false READY, and it is not hypothetical — this checker takes a `--pr`.
    A missing local head (detached, no git) is CANNOT RUN, not a pass.
    """
    missing = [k for k in ("state", "isDraft", "baseRefName", "headRefOid", "mergeStateStatus")
               if k not in info]
    if missing:
        return 2, "could not read " + ", ".join(missing) + " from gh"
    problems = []
    if info["state"] != "OPEN":
        problems.append(f"state is {info['state']}, not OPEN")
    if info["isDraft"]:
        problems.append("it is a DRAFT")
    if info["baseRefName"] != "master":
        problems.append(f"base is {info['baseRefName']}, not master")
    # ⛔ `UNKNOWN` IS NOT A STATE OF THE BRANCH — IT IS "NOT COMPUTED YET", AND IT IS WHAT GITHUB
    # RETURNS FIRST. Claude r1, High, measured live on PR #317: one query returned UNKNOWN and the
    # next returned DIRTY, in the same second. Mergeability is computed lazily and the first read
    # kicks the job off. So a CLEAN pull request and a CONFLICTED one look identical on first read,
    # and the ordinary invocation — a human running this right after pushing, which is the moment
    # the script is FOR — got a false NOT READY. Worse, it was an absent measurement reported as a
    # failure, which `verdict()` has a comment forbidding three functions up.
    if info["mergeStateStatus"] == "UNKNOWN":
        return 2, ("GitHub has not computed mergeability yet (UNKNOWN) — it is calculated lazily "
                   "and the first read only starts the job. Re-run in a moment.")
    # ⚠ Three of the seven mean GitHub will merge: CLEAN, UNSTABLE (a non-required check is
    # failing) and HAS_HOOKS (passing, with pre-receive hooks — GHE only, latent here). The set
    # itself is at MERGEABLE_STATES, with the enum verified by introspection rather than memory.
    if info["mergeStateStatus"] not in MERGEABLE_STATES:
        problems.append(f"mergeStateStatus is {info['mergeStateStatus']}")
    if local_head is None:
        return 2, "could not read the local HEAD to compare against the PR head"
    if info["headRefOid"] != local_head:
        problems.append(f"PR head {info['headRefOid'][:8]} is not the local HEAD {local_head[:8]} "
                        f"— this is a different commit than the one checked out")
    if problems:
        return 1, "; ".join(problems)
    return 0, f"open, not draft, based on master, head {local_head[:8]}, {info['mergeStateStatus']}"


def ci_conclusion(checks: list[dict]) -> tuple[int, str]:
    """Read `gh pr checks --json` output into a verdict. PURE.

    ⚠ A check still PENDING is not a pass, and neither is an empty list — a pull request whose CI
    has not started reports no checks at all, and "no failures" over nothing is the vacuous-pass
    shape this repository keeps filing findings about.
    """
    if not checks:
        return 2, "no checks reported yet — CI may not have started"
    buckets = [c.get("bucket", "") for c in checks]
    if any(b == "pending" for b in buckets):
        return 2, "still running"
    bad = sorted(c.get("name", "?") for c in checks if c.get("bucket") not in ("pass", "skipping"))
    if bad:
        return 1, "failing: " + ", ".join(bad)
    return 0, f"{len(checks)} check(s) green"


# ── THE FETCH, impure ─────────────────────────────────────────────────────────────────────────
def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("text", True)
    return subprocess.run(cmd, capture_output=True, cwd=ROOT, **kw)


def as_text(out) -> str:
    """git's output as text WITHOUT newline translation — r7: text mode turned a `\\r` in a path into
    `\\n`, so `check-a\\r.py` and `check-a\\n.py` became one key and one file's blob stood in for the
    other's. Bytes in, `surrogateescape` out: reversible, and a CR stays a CR."""
    return out.decode("utf-8", "surrogateescape") if isinstance(out, bytes) else out


def _pr_number(explicit: int | None) -> tuple[int | None, str]:
    if explicit:
        return explicit, ""
    r = _run(["gh", "pr", "view", "--json", "number", "--jq", ".number"])
    if r.returncode != 0 or not r.stdout.strip().isdigit():
        return None, (r.stderr.strip() or "no pull request found for this branch")
    return int(r.stdout.strip()), ""


# ── THE TWO PR-BODY ESCAPES, AND WHICH GATE EACH ANSWERS ──────────────────────
# ⛔ THEY ARE NOT INTERCHANGEABLE, AND NOTHING SAID SO UNTIL NOW. MEASURED
# 2026-09-26: PRs #351 and #352 both carried `NO-REVIEW:` and both went CI-red on
# the dashboard-entry ratchet. `check-review-recorded` duly passed — it had been
# answered — while `check-dashboard-entry` refused, because nothing had answered
# IT. Each gate reports only its own verdict, so the reader sees a refusal beside a
# declaration they believe covers it, and concludes the gate is wrong.
#
# This script is the only place that holds BOTH verdicts and the body at once, so
# it is the only place the confusion is visible. That is why the diagnosis lives
# here and not in a forty-first guard: one mechanism per concern.
GATE_ESCAPE = {"dashboard entry": "NO-ENTRY:", "review recorded": "NO-REVIEW:"}

# Anything shaped like an escape but not spelled as one. ⚠ MEASURED against the
# real matcher, not guessed: `NO_ENTRY:`, `no-entry:`, `NO-ENTRY` without a colon,
# the token mid-line, indented 4+, or inside a fence ALL grant nothing silently.
ESCAPE_LOOKALIKE = re.compile(r"(?i)\bno[-_ ]?(?:entry|review)\b")


@functools.lru_cache(maxsize=1)
def _dashboard_gate():
    """The gate that OWNS the escape grammar, imported rather than re-implemented.

    ⛔ `exemption_reason(body, marker)` is parameterised by marker and is declared
    "ONE DEFINITION, shared with gen-dashboard.py". Re-deriving the rule here would
    be a second implementation of it, and this repo has recorded that shape drifting
    seventeen times — a weaker stand-in passes what the real one refuses.
    """
    src = Path(__file__).with_name("check-dashboard-entry.py")
    spec = importlib.util.spec_from_file_location("_cde_for_merge_ready", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── THE HOUSE RULE'S EXCEPTIONS (2026-10-25) ──────────────────────────────────────────────────
# ⛔ THE OWNER'S RULE, set 2026-10-25: *merge when READY, unless the PR loosens a gate, needs a
# deploy first, relied on a NO-REVIEW waiver, or changed app code without the local integration
# and end-to-end tests* — and on an exception, HOLD and tell the owner. The three readings were
# chosen on a selection card AGAINST MEASURED BASE RATES over the 30 merged PRs before it: "any
# gate-file edit" would have held 18/30 and was rejected; LOOSENING holds 5/30 including PR #398;
# NO-REVIEW 8/30 (0 of the last 14); app code and migrations 0/30.
# ⛔ THE DETECTOR IS SYNTACTIC, AND REVIEW IS THE PRIMARY PROTECTION (owner's ruling, r8 card A). A
# PR reaches READY only after its review rounds; this stage is a second net for loosenings that
# leave TEXT on a failure path. A SEMANTIC loosening — a condition removed far above the loop that
# fails on it, a threshold changed, a helper's meaning changed without failure-path text — is
# outside what a diff rule can see, and is stated here rather than chased.
# ⚠ LOOSENING IS DETECTED BY PROXIES, and they are bounds, not a proof. A weakening that lowers no
# pin or count, edits no baseline, removes no line on a failure path and drops no gate invocation
# merges as READY. ⚠ They target an HONEST change, not an evasion: a failure line re-added inside
# dead code reads as a MOVE, a removal more than FAIL_WINDOW source lines from any failure word
# is outside the window, and a gate whose failure path uses none of FAIL_PATH's idioms is unseen.
HOLD_RC = 3
BASELINE_FILE = re.compile(r"^docs/reviews/.*baseline\.json$")
PIN_LINE = re.compile(r'^\s*"(?P<path>scripts/[^"]+)":\s*(?P<n>\d+),')
PIN_TOTAL = re.compile(r"sum\(EXPECTED_MUTATIONS\.values\(\)\),\s*(?P<n>\d+)\)")
CASE_COUNT = re.compile(r"--self-test\s*#\s*(?P<n>\d+) cases")
# A line on a failure path: the FAIL word, a fails/failures tally, a non-zero exit, or a hook's
# `deny` — r1 CLAUDE H3: the hooks block with `deny "…"` and `exit 2`, and the first pattern saw neither.
# ⟳ r8/r9 (HONEST): ANY non-zero integer status (3, 10, -1), and `raise` / `assert` — a validation
# exception turned into a `print` lets execution continue. Measured cost: 9 -> 10 of 40 PRs.
# ⟳ r10: `sys.exit(<anything but 0 / None / nothing>)` — `sys.exit("invalid input")` exits 1.
FAIL_PATH = re.compile(r"\bFAIL\b|\bfails\b|\bfailures?\b|\breturn\s+-?[1-9]\d*\b|\bexit\s+-?[1-9]\d*\b"
                       r"|sys\.exit\((?!\s*(?:0|None)?\s*\))|SystemExit\(|\bdeny\b|\braise\b|\bassert\b")
# ⟳ backlog #354: Node's — `process.exit(<anything but 0 / nothing>)`, a non-zero `process.exitCode`, `throw` —
# ONLY in a Node source file. A Python gate embeds JS stubs in strings (`page_chrome.py`), and reading their
# `throw` there newly held PR #397 in the 40-PR replay; `throw` is not Python, so in a `.py` it is a string.
NODE_SRC = re.compile(r"\.(ts|mts|cts|js|mjs|cjs)$")
# ⟳ r1 (executed): `process.exit (1)` is ordinary syntax; `exitCode === 0` is a comparison; `||=` assigns.
NODE_FAIL_PATH = re.compile(FAIL_PATH.pattern + r"|process\.exit\s*\((?!\s*0?\s*\))"
                            r"|process\.exitCode\s*(?:\|\||&&|\?\?)?=(?!=)(?!\s*0\b)"
                            r"|\bthrow\b")
# ⟳ r8 (HONEST): EVERY script, not only `check-*` — a gate's logic moved into a helper it imports
# (`scripts/gate_logic.py`) changes the gate without touching it. Measured cost: 8 -> 9 of 40 PRs.
# ⟳ backlog #354 (r11 HONEST): TypeScript/JavaScript too — `check-service-confinement.ts` runs in CI.
GATE_CODE = re.compile(r"^(scripts/[^/]+\.(py|sh|ts|mts|cts|js|mjs|cjs)|scripts/ci/.+|\.claude/hooks/.+)$")
# Where a gate is INVOKED rather than written (r1 CLAUDE M1): dropping the line that runs a check
# disables it without touching the check. A removed line here naming a gate, not re-added, holds.
# ⚠ backlog #356: a TypeScript gate is run through `package.json`'s `check:` scripts, and that call site is NOT
# guarded — r1's attempt classified package.json as a caller while collection never read its hunks (r2).
GATE_CALLER = re.compile(r"^(\.github/workflows/[^/]+\.ya?ml|\.claude/settings(\.local)?\.json"
                         r"|scripts/check-schema-gates\.sh|scripts/ci/.+)$")
GATE_REF = re.compile(r"scripts/check-|\.claude/hooks/|--self-test|--mutate")
MIGRATION = re.compile(r"^supabase/migrations/")
APP_CODE = re.compile(r"^(app|lib|components|worker|supabase)/")


def _unquote(p: str) -> str:
    """PURE. Undo git's C-quoting — r3: `"a/gat\\303\\251.yml"` parsed to None and its deletion was READY."""
    if len(p) >= 2 and p[0] == p[-1] == '"':
        return p[1:-1].encode("ascii", "backslashreplace").decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")
    return p


def _side(field: str, prefix: str) -> str | None:
    """PURE. One `---`/`+++`/header path: unquoted, its tab delimiter cut (r3: git appends a TAB after
    a path containing a space, and the kept tab made `GATE_CODE` miss it), and its `a/`/`b/` dropped.
    `/dev/null` is None."""
    if not field.startswith('"'):
        field = field.split("\t")[0]
    field = _unquote(field)
    return field[len(prefix):] if field.startswith(prefix) else None


class PathsDisagree(ValueError):
    """The machine path list and the patch text do not describe the same files."""


def name_status(z: str) -> list[dict]:
    """PURE. `git diff --name-status -z -M` -> [{status, old, new, copy}], one per changed file.

    ⛔ BACKLOG #353, THE CLASS FIX. Four review rounds found a new path shape each time — C-quoting,
    a tab after a spaced path, a binary deletion with no `+++`, a ` b/` inside a path, literal
    Unicode under `core.quotePath=false` — because paths were recovered from the HUMAN format.
    This format is for programs: NUL-separated, never quoted, never tab-delimited, and the status
    letter says outright what happened (A, D, M, T, R<score> old new, C<score> old new)."""
    toks = z.split("\0")
    if toks and toks[-1] == "":
        toks.pop()
    out, i = [], 0
    while i < len(toks):
        st = toks[i]
        k, n = st[:1], (3 if st[:1] in ("R", "C") else 2)
        if not k or i + n > len(toks):
            raise PathsDisagree(f"--name-status entry {st!r} at token {i} is incomplete")
        if k in ("R", "C"):
            old, new = toks[i + 1], toks[i + 2]
        else:
            p = toks[i + 1]
            old, new = (None, p) if k == "A" else (p, None) if k == "D" else (p, p)
        out.append({"status": k, "old": old, "new": new, "copy": k == "C"})
        i += n
    return out


def diff_files(diff: str) -> list[dict]:
    """PURE. THE ONE DIFF PARSER — every loosening detector reads this and parses nothing itself.

    Per file in a `git diff` text: `old` and `new` path (None for `/dev/null`), and `hunks`, each a
    list of raw `+`/`-`/` ` lines. A pure rename or a mode change has paths and no hunks.
    ⛔ REDESIGN after r2's lost bet: there were TWO parsers, each deciding paths and comments for
    itself. r1's deletion fix landed in both by hand; r2 then found a RENAME lost by both (each
    kept only the destination) and comments filtered in one and not the other — one rule,
    implemented twice, drifting. Paths are decided here and comments by `is_comment`, once.
    """
    out: list[dict] = []
    cur, hunk = None, None
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            m = re.match(r'diff --git ("(?:[^"\\]|\\.)*"|a/.+?) ("(?:[^"\\]|\\.)*"|b/.+)$', line)
            o, n = (_side(m[1], "a/"), _side(m[2], "b/")) if m else (None, None)
            cur, hunk = {"old": o, "new": n, "hunks": [], "copy": False}, None
            out.append(cur)
        elif cur is None:
            continue
        elif hunk is None and line.startswith(("rename from ", "copy from ")):
            cur["old"] = _unquote(line.split(" ", 2)[2])
            cur["copy"] = line.startswith("copy ")
        elif hunk is None and line.startswith(("rename to ", "copy to ")):
            cur["new"] = _unquote(line.split(" ", 2)[2])
        elif hunk is None and line.startswith("deleted file mode"):
            cur["new"] = None              # r3: a BINARY deletion has no `+++ /dev/null` to say so
        elif hunk is None and line.startswith("new file mode"):
            cur["old"] = None
        elif hunk is None and line.startswith("--- "):
            cur["old"] = _side(line[4:], "a/")
        elif hunk is None and line.startswith("+++ "):
            cur["new"] = _side(line[4:], "b/")
        elif line.startswith("@@"):
            hunk = []
            cur["hunks"].append(hunk)
        elif hunk is not None and line[:1] in ("+", "-", " "):
            hunk.append(line)
    return out


def is_comment(text: str) -> bool:
    """PURE. The ONE comment rule (Python, shell and YAML all use `#`). ⚠ A Node file's `//` and `/* */` are
    read as CODE — false holds only. backlog #354 r2: a rule treating a leading `*` as a comment hid a
    continuation line `* 2` -> `* 0` (exit 2 -> 0, READY), so Node comments are backlog #356, not guessed at."""
    return text.strip().startswith("#")


def _paths(f: dict) -> list[str]:
    return [p for p in (f["old"], f["new"]) if p]


def _name(f: dict) -> str:
    return f"{f['old']} -> {f['new']}" if f["old"] and f["new"] and f["old"] != f["new"] else (f["new"] or f["old"])


def _code(f: dict, sign: str) -> list[str]:
    """The stripped non-comment lines of one side (`-` removed, `+` added) of a file's hunks."""
    return [l[1:].strip() for hk in f["hunks"] for l in hk
            if l.startswith(sign) and l[1:].strip() and not is_comment(l[1:])]


def diff_lines(diff: str, fs: list[dict] | None = None) -> dict[str, tuple[list[str], list[str]]]:
    """PURE. {path: (removed, added)} — a VIEW of `diff_files`, keyed by the new path, or the old
    one for a deletion. Raw lines, comments included: the pin and count readers match their own
    patterns."""
    out: dict[str, tuple[list[str], list[str]]] = {}
    for f in (fs if fs is not None else diff_files(diff)):
        key = f["new"] or f["old"]
        if key is None:
            continue
        rm, ad = out.setdefault(key, ([], []))
        for hk in f["hunks"]:
            rm += [l[1:] for l in hk if l.startswith("-")]
            ad += [l[1:] for l in hk if l.startswith("+")]
    return out


# How far from a failure-path line a removed line still counts as ON that path. ⚠ MEASURED, not
# chosen: PR #398's real weakening — `("4 NO IMPROVEMENT", …)` leaving the FAIL loop — carries no
# failure word itself and sits 4 lines above `fails.append`. Window 0 caught only its reworded
# docstring; 5 catches the dispatch line too, and holds 5 of the 32 PRs before this rule.
FAIL_WINDOW = 5


def failure_path_removals(diff: str, k: int = FAIL_WINDOW, fs: list[dict] | None = None) -> dict[str, list[str]]:
    """PURE. {gate: removed code lines within `k` lines of a failure-path line in the hunk}.

    Reads a `git diff -U<k>` text. A file is a gate if EITHER path is (r2: a rename out of scope
    kept only the destination). A comment line neither counts nor anchors, and a line added back
    identically anywhere in the same file is a MOVE, not a removal. ⛔ Distance is in OLD-FILE
    lines: r1 found six added comment lines pushed an adjacent removal out of the window, so an
    added line has no position and cannot anchor — only the source as it WAS is measured.
    """
    out: dict[str, list[str]] = {}
    for f in (fs if fs is not None else diff_files(diff)):
        if not any(GATE_CODE.match(p) for p in _paths(f)):
            continue
        node = any(NODE_SRC.search(p) for p in _paths(f))
        fail = NODE_FAIL_PATH if node else FAIL_PATH
        # ⟳ r9 (HONEST): a MOVE keeps its INDENTATION. Stripped comparison read `return 1` pushed under
        # a new `if verbose:` as moved, cancelling a real removal — in Python indentation is meaning.
        readded = [l[1:].rstrip() for hk in f["hunks"] for l in hk
                   if l.startswith("+") and l[1:].strip() and not is_comment(l[1:])]
        for hk in f["hunks"]:
            old_side = [l for l in hk if not l.startswith("+")]
            code = [(i, l) for i, l in enumerate(old_side) if not is_comment(l[1:])]
            for i, l in code:
                t = l[1:].strip()
                if not l.startswith("-") or not t:
                    continue
                if l[1:].rstrip() in readded:
                    readded.remove(l[1:].rstrip())
                    continue
                if any(abs(j - i) <= k and fail.search(w[1:]) for j, w in code):
                    out.setdefault(_name(f), []).append(t)
    return out


def gate_invocation_removals(diff: str, fs: list[dict] | None = None) -> dict[str, list[str]]:
    """PURE. {caller: removed non-comment lines naming a gate, not added back} — r1 CLAUDE M1.

    ⛔ r2 CODEX M2: comments are excluded through `is_comment`, the same rule the failure path
    uses, so a reworded comment naming a check is not a dropped invocation."""
    out: dict[str, list[str]] = {}
    for f in (fs if fs is not None else diff_files(diff)):
        if not any(GATE_CALLER.match(p) for p in _paths(f)):
            continue
        back = _code(f, "+")
        gone = [r for r in _code(f, "-") if GATE_REF.search(r) and r not in back]
        if gone:
            out[_name(f)] = gone
    return out


def scope_exits(diff: str, fs: list[dict] | None = None) -> list[str]:
    """PURE. Gate files whose OLD path is in scope and whose new path is gone or out of scope —
    deleted, or renamed where nothing runs it (r2 CODEX M1: a workflow moved out of
    `.github/workflows/` stops running, and a pure rename carries no hunk for the others to see)."""
    def role(p):
        return (bool(p and GATE_CODE.match(p)), bool(p and GATE_CALLER.match(p)))
    # ⛔ r3: the ROLE must survive, not just "some gate": a workflow renamed to `scripts/check-x.py`
    # is still "a gate path" and no longer runs. A COPY leaves the source in place, so it never exits.
    # ⟳ r4 XM3: an exit is a role LOST — `check-old.sh` -> `check-schema-gates.sh` GAINS the caller
    # role and keeps the code role, which `!=` read as an exit.
    return [f"{f['old']} is {'deleted' if f['new'] is None else 'renamed to ' + f['new']}"
            for f in (fs if fs is not None else diff_files(diff))
            if not f["copy"] and any(o and not n for o, n in zip(role(f["old"]), role(f["new"])))]


def changed_paths(status: str) -> list[str]:
    """PURE. Every path the machine list names, old and new — a baseline renamed AWAY still counts."""
    return sorted({p for e in name_status(status) for p in (e["old"], e["new"]) if p})


# What keeps git's output the PLAIN one whatever the reader's config says. `--no-ext-diff`: a
# configured `diff.external` runs for EVERY diff, blob-to-blob included, and can print nothing.
# `--no-relative`: paths from the root. (`--no-textconv` was here for r5's per-path patches and is
# GONE with them: a blob diff has no path, so no attribute — textconv, `-diff` — can apply to it.)
GIT_PLAIN = ["--no-ext-diff", "--no-relative"]


def status_cmd(base: str) -> list[str]:
    """The machine list of what changed — every file's status and exact paths (backlog #353)."""
    return ["git", "--literal-pathspecs", "diff", "--name-status", "-z", "-M", *GIT_PLAIN,
            f"{base}...HEAD"]


# Hunks are read only where a detector looks: gate code and callers, the pins, the declared counts.
# Everything else (app code, docs, images) is classified by PATH alone, so its bytes are never read.
HUNK_ROOTS = ("scripts/", ".claude/", ".github/")
GITLINK = "160000"
SYMLINK = "120000"


def tree_index(z: str) -> dict[str, tuple[str, str]]:
    """PURE. `git ls-tree -r -z` -> {path: (mode, object id)}. NUL-separated, so paths are exact."""
    out: dict[str, tuple[str, str]] = {}
    for rec in z.split("\0"):
        if rec:
            meta, path = rec.split("\t", 1)
            mode, _kind, oid = meta.split(" ")
            out[path] = (mode, oid)
    return out


def patch_hunks(patch: str) -> list[list[str]]:
    """PURE. Every hunk in a patch, its header lines ignored — the caller already knows the file."""
    out: list[list[str]] = []
    hunk = None
    for line in patch.split("\n"):
        if line.startswith("diff --git "):
            hunk = None
        elif line.startswith("@@"):
            hunk = []
            out.append(hunk)
        elif hunk is not None and line[:1] in ("+", "-", " "):
            hunk.append(line)
    return out


def blob_hunks(read, old: "tuple[str, str] | None", new: "tuple[str, str] | None") -> list[list[str]]:
    """The hunks between two EXACT BLOBS — no path is involved, so no pathspec and no attribute can
    change them (r6: a pathspec matched a DIRECTORY's descendants, and a `-diff` attribute turned a
    gate's change into "Binary files differ" with no hunks — both FALSE READYs). `--text` forces
    hunks even for content git would call binary. A gitlink is a commit, not a blob: no hunks."""
    def blob(x):
        return x is not None and x[0] != GITLINK
    if not (blob(old) or blob(new)):
        return []
    if blob(old) and blob(new):
        if old[1] == new[1]:
            return []
        return patch_hunks(read(["git", "diff", f"-U{FAIL_WINDOW}", "--no-color", "--text", *GIT_PLAIN,
                                 old[1], new[1]]))
    oid, sign = (new[1], "+") if blob(new) else (old[1], "-")
    lines = read(["git", "cat-file", "blob", oid]).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [[sign + line for line in lines]] if lines else []


def git_reader(run):
    """The ONE way the house rule reads git, shared by `main()` and the real-git self-test: BYTES
    (`text=False`) decoded by `as_text`, and a non-zero exit RAISES, which `main()` turns into
    CANNOT RUN — never an empty answer."""
    def read(cmd):
        r = run(cmd, text=False)
        if r.returncode != 0:
            raise PathsDisagree(f"`{' '.join(cmd[:6])} …` exited {r.returncode}")
        return as_text(r.stdout)
    return read


def gather(read, base: str) -> tuple[list[str], list[dict]]:
    """(changed paths, one record per changed file) — what `main()` and the real-git self-test BOTH
    use, so they cannot drift. `read(cmd)` returns a command's stdout or raises.

    ⛔ THE THIRD FORM, and why the first two fell. r5: patch sections paired with the machine list
    BY POSITION — a type change is one entry and two sections — gave a FALSE READY. r6: per-path
    patches — a pathspec matches a directory's descendants, and attributes rewrite a path's patch —
    gave two more. Now the list says WHICH files changed, both trees (read once, NUL-separated) say
    which BLOB each side is, and the hunks are the diff of those two blobs. Ownership is by
    construction, and nothing about a path, its attributes or a pathspec enters the hunks."""
    mb = read(["git", "merge-base", base, "HEAD"]).strip()
    st = read(status_cmd(base))
    old_t = tree_index(read(["git", "ls-tree", "-r", "-z", "--full-tree", mb]))
    new_t = tree_index(read(["git", "ls-tree", "-r", "-z", "--full-tree", "HEAD"]))
    fs = []
    changed = set(changed_paths(st))
    for e in name_status(st):
        looked = any(p.startswith(HUNK_ROOTS) for p in (e["old"], e["new"]) if p)
        fs.append({"old": e["old"], "new": e["new"], "copy": e["copy"], "status": e["status"],
                   "hunks": blob_hunks(read, old_t.get(e["old"]) if e["old"] else None,
                                       new_t.get(e["new"]) if e["new"] else None) if looked else []})
    # ⛔ r7: a gate that is a SYMLINK runs its TARGET, which may live anywhere and change alone. Each
    # gate symlink whose target changed gets that target's blob diff UNDER THE GATE'S NAME, so the
    # detectors judge it as the gate. ⚠ One level: a target that is itself a link is not followed.
    for path, (mode, oid) in sorted(new_t.items()):
        if mode != SYMLINK or not (GATE_CODE.match(path) or GATE_CALLER.match(path)):
            continue
        tgt = posixpath.normpath(posixpath.join(posixpath.dirname(path), read(["git", "cat-file", "blob", oid])))
        if tgt in changed and tgt != path:
            fs.append({"old": path, "new": path, "copy": False, "status": "M", "via": tgt,
                       "hunks": blob_hunks(read, old_t.get(tgt), new_t.get(tgt))})
    return changed_paths(st), fs


def hold_reasons(files: list[str], diff: str, head: str | None,
                 app_tests_at: str | None, no_review: bool, fs: list[dict] | None = None) -> list[str]:
    """PURE. Why a READY pull request must still be HELD for the owner. Empty = no exception.

    `no_review` is the review gate's OWN matcher's answer for `NO-REVIEW:` (passed in, so the
    rule stays pure and cannot disagree with the gate about where a waiver counts).
    """
    out: list[str] = []
    per = diff_lines(diff, fs)
    # 1. LOOSENS A GATE — six proxies, all reading `diff_files` through its views.
    for f in files:
        if BASELINE_FILE.match(f):
            out.append(f"loosens a gate: {f} is a pinned baseline and this PR edits it")
    removed, added = per.get("scripts/check-plan-code.py", ([], []))
    old = {m["path"]: int(m["n"]) for m in map(PIN_LINE.match, removed) if m}
    new = {m["path"]: int(m["n"]) for m in map(PIN_LINE.match, added) if m}
    for path in sorted(old):
        if path in new and new[path] < old[path]:
            out.append(f"loosens a gate: the mutation pin for {path} drops {old[path]} -> {new[path]}")
        elif path not in new:                       # r1 CLAUDE M2: deleted or renamed away
            out.append(f"loosens a gate: the mutation pin for {path} ({old[path]}) is removed")
    ot = [int(m["n"]) for m in map(PIN_TOTAL.search, removed) if m]
    nt = [int(m["n"]) for m in map(PIN_TOTAL.search, added) if m]
    if ot and nt and nt[0] < ot[0]:
        out.append(f"loosens a gate: the declared mutation total drops {ot[0]} -> {nt[0]}")
    for path, (rm, ad) in sorted(per.items()):
        oc = [int(m["n"]) for m in map(CASE_COUNT.search, rm) if m]
        nc = [int(m["n"]) for m in map(CASE_COUNT.search, ad) if m]
        if oc and nc and nc[0] < oc[0]:
            out.append(f"loosens a gate: {path} declares fewer self-test cases, {oc[0]} -> {nc[0]}")
    for path, gone in sorted(failure_path_removals(diff, fs=fs).items()):
        out.append(f"loosens a gate: {path} removes or rewrites {len(gone)} line(s) on a "
                   f"failure path, e.g. {gone[0][:70]!r}")
    for path, gone in sorted(gate_invocation_removals(diff, fs).items()):
        out.append(f"loosens a gate: {path} drops or rewrites {len(gone)} gate invocation(s), "
                   f"e.g. {gone[0][:70]!r}")
    for exit_ in scope_exits(diff, fs):
        out.append(f"loosens a gate: {exit_}, so nothing runs it as a gate any more")
    # 2. NEEDS A DEPLOY FIRST.
    migs = [f for f in files if MIGRATION.match(f)]
    if migs:
        out.append(f"needs a deploy first: {len(migs)} migration file(s), e.g. {migs[0]} — apply to "
                   f"production before merging")
    # 3. RELIED ON A WAIVER.
    if no_review:
        out.append("relied on a waiver: the body declares NO-REVIEW:, so no review covered the final tree")
    # 4. APP CODE WITHOUT THE LOCAL TESTS — cleared only by a run pinned to THIS head.
    app = [f for f in files if APP_CODE.match(f)]
    if app and (head is None or app_tests_at != head):
        # ⚠ SELF-ATTESTED (r1, both halves): the flag is a SHA compared to the head; nothing here
        # runs the tests or reads their result. It pins WHICH tree the merger claims to have tested.
        out.append(f"app code changed ({len(app)} file(s), e.g. {app[0]}) and nobody has attested "
                   f"a local test:integration + test:e2e pass at this head — run both, then re-run "
                   f"with --app-tests-passed {head or '<head sha>'} (an attestation; not verified)")
    return out


def final_verdict(code: int, line: str, holds: list[str]) -> tuple[int, str]:
    """PURE. A HOLD applies only to an otherwise-READY PR; NOT READY and CANNOT RUN win."""
    if code != 0 or not holds:
        return code, line
    return HOLD_RC, ("HOLD — ready by every gate, but the house rule's exceptions apply. Do NOT "
                     "merge; tell the owner: " + "; ".join(holds))


def granted_escapes(pr_body: str) -> dict[str, str | None]:
    """{marker: reason or None}, decided by the gate's own matcher. NOT pure — it imports."""
    er = _dashboard_gate().exemption_reason
    return {m: er(pr_body, m) for m in sorted(set(GATE_ESCAPE.values()))}


def escape_diagnosis(refused: list[str], granted: dict[str, str | None],
                     pr_body: str) -> list[str]:
    """PURE. Why a REFUSING gate did not see the escape its author thinks they wrote.

    Three distinguishable states, and the distinction is the whole point — each has a
    different repair:

      MISDIRECTED  the other gate's escape is granted and this one's is not. The
                   author answered the wrong gate. Name the token this gate wants.
      INVISIBLE    this gate's exact token IS in the body and was not counted, so
                   its placement killed it: indented 4+, inside a fence, or not at
                   the start of its own line.
      MISSPELLED   something escape-shaped is present but is not the literal token.

    ⚠ It runs ONLY on gates that already refused, so it can never turn a pass into a
    failure and adds no false-positive surface. It explains a verdict; it is not one.
    ⚠ And it never advises taking the escape. Usually the right answer is the entry
    or the review — both 2026-09-26 branches genuinely warranted one.
    """
    out: list[str] = []
    for gate in refused:
        want = GATE_ESCAPE.get(gate)
        if want is None or granted.get(want):
            continue
        other = next((m for g, m in GATE_ESCAPE.items() if g != gate), None)
        if other is not None and granted.get(other):
            out.append(f"{gate}: the body declares `{other}`, which answers the OTHER gate. "
                       f"This one is only answered by `{want}` — or by doing the work.")
        elif want in pr_body:
            out.append(f"{gate}: `{want}` IS in the body and was not counted. It must start its "
                       f"own line, unindented (4+ columns is a code block), outside any fence.")
        elif other is not None and other in pr_body:
            # ⭐ FOUND BY THE FALSIFIER, 2026-09-26, and it is the state the incident was
            # actually in. Both PR bodies wrote `NO-REVIEW:` inside BACKTICKS, so the
            # matcher granted nothing — and the review gate happened to pass for an
            # unrelated reason, so nobody learned the declaration was inert. Saying only
            # "wrong token" would have been true and would have hidden this.
            out.append(f"{gate}: this gate needs `{want}`, which is absent. ⚠ And `{other}` is "
                       f"in the body but was NOT granted either — so that declaration is inert "
                       f"too. Both must start their own line, unindented, outside fences and "
                       f"NOT wrapped in backticks.")
        elif (hit := ESCAPE_LOOKALIKE.search(pr_body)) is not None:
            out.append(f"{gate}: the body contains {hit.group(0)!r}, which is not `{want}`. "
                       f"The gate matches that literal exactly — case, hyphen and colon.")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pr", type=int, default=None)
    ap.add_argument("--app-tests-passed", metavar="SHA", default=None,
                    help="the PR head at which test:integration and test:e2e passed locally")
    args = ap.parse_args(argv)

    if not WORKFLOW.is_file():
        print(f"CANNOT RUN — {WORKFLOW} is missing. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    gated = pr_only_steps(WORKFLOW.read_text())
    if not gated:
        # An empty derivation is not "nothing to check" — it means the parse found nothing, and a
        # zero over nothing is not a finding. Measured: there are 2 today.
        print("CANNOT RUN — parsed 0 pull-request-only steps from the workflow, which cannot be "
              "right. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    pr, why = _pr_number(args.pr)
    if pr is None:
        print(f"CANNOT RUN — {why}. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    print(f"pull request           : #{pr}")
    print(f"base                   : {BASE_REF}")
    print(f"pull-request-only steps: {len(gated)} derived from ci.yml — {', '.join(gated)}")
    # ⚠ NAMED, NOT INVOKED. A job gated on a pull_request event has no step this script can run,
    # and every OTHER workflow's gates are outside what it drives. Saying so is the difference
    # between a known gap and a silent one — Claude r1, Medium.
    # ⭐ SOUNDNESS BEFORE ANYTHING ELSE. Three rounds produced three parsers and each MISSED a
    # gate silently. A fourth regex is the same bet; refusing to answer when the parse is
    # incomplete is not. A parser bug now costs a refusal, which is recoverable.
    for wf in workflow_files(WORKFLOW_DIR):
        stray = unaccounted_mentions(wf.read_text(), wf.name)
        if stray:
            print(f"CANNOT RUN — {wf.name} carries {len(stray)} mention(s) of `pull_request` "
                  f"that ACCOUNTED_MENTIONS does not cover. One of them may be a gate this script "
                  f"does not invoke, and a READY verdict would be computed without it. Classify "
                  f"each and add it there with a reason:", file=sys.stderr)
            for s in stray[:4]:
                print(f"    {s}", file=sys.stderr)
            print("  Treat this as NOT RUN.", file=sys.stderr)
            return 2

    for wf in workflow_files(WORKFLOW_DIR):
        jobs = job_level_gates(wf.read_text())
        extra = pr_only_steps(wf.read_text()) if wf != WORKFLOW else []
        if jobs or extra:
            print(f"  ⚠ {wf.name}: pull-request-only {'job(s) ' + ', '.join(jobs) if jobs else ''}"
                  f"{' step(s) ' + ', '.join(extra) if extra else ''} — NOT invoked here; CI runs them")
    print()

    results: dict[str, int] = {}

    body_file = Path(_run(["mktemp"]).stdout.strip() or "/tmp/_mr_body.md")
    rb = _run(["gh", "pr", "view", str(pr), "--json", "body", "--jq", ".body"])
    if rb.returncode != 0:
        print("CANNOT RUN — could not read the pull-request body, which the review gate needs "
              "for its waiver. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    body_file.write_text(rb.stdout)

    # The two gates a working copy cannot answer. Invoked the way CI invokes them.
    for name, cmd in [
        # ⚠ BOTH ARGUMENTS, because CI passes both (ci.yml:422) — code review r1 (Codex), Low.
        # Without `--pr-body-file` the gate cannot see a `NO-ENTRY:` waiver, so this script would
        # report NOT READY for a branch CI passes: right answer, wrong reason, and the reader goes
        # looking for an entry they already waived.
        ("dashboard entry", ["python3", "scripts/check-dashboard-entry.py",
                             "--base", BASE_REF, "--pr-body-file", str(body_file)]),
        ("review recorded", ["python3", "scripts/check-review-recorded.py",
                             "--base", BASE_REF, "--pr-body-file", str(body_file)]),
        ("review rounds", ["python3", "scripts/check-review-rounds.py"]),
    ]:
        r = _run(cmd)
        results[name] = r.returncode
        mark = MARK.get(r.returncode, "?? ")
        tail = (r.stdout or r.stderr).strip().split("\n")
        print(f"  {mark} {name:18s} rc={r.returncode}  {tail[0][:88] if tail else ''}")

    # ⛔ THE ESCAPE CROSS-CHECK. Runs only over gates that ALREADY refused, so it
    # cannot manufacture a failure — it explains one. See escape_diagnosis().
    _refused = [n for n, rc in results.items() if rc == 1]
    if _refused:
        try:
            _granted = granted_escapes(body_file.read_text())
        except Exception as exc:                      # a broken import must not hide the verdict
            print(f"     ⚠ escape cross-check NOT RUN ({exc.__class__.__name__}) — "
                  f"treat the gate verdicts above as the answer")
            _granted = None
        if _granted is not None:
            for _line in escape_diagnosis(_refused, _granted, body_file.read_text()):
                print(f"     ⛔ {_line}")

    # ⚠ TWICE, deliberately. The first read STARTS GitHub's lazy mergeability computation and
    # returns UNKNOWN; the second usually has the answer. Measured on PR #317: UNKNOWN then DIRTY,
    # same second. One retry, not a loop — if it is still UNKNOWN the rule says CANNOT RUN, which
    # is true and actionable, rather than spinning.
    for _attempt in (1, 2):
        ri = _run(["gh", "pr", "view", str(pr), "--json",
                   "state,isDraft,baseRefName,headRefOid,mergeStateStatus"])
        if "UNKNOWN" not in ri.stdout:
            break
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip() or None
    try:
        info = json.loads(ri.stdout) if ri.stdout.strip() else {}
    except json.JSONDecodeError:
        info = {}
    mcode, mnote = mergeability(info, head)
    results["mergeability"] = mcode
    print(f"  {MARK[mcode]} {'mergeability':18s} rc={mcode}  {mnote}")

    rc = _run(["gh", "pr", "checks", str(pr), "--json", "name,bucket"])
    try:
        code, note = ci_conclusion(json.loads(rc.stdout) if rc.stdout.strip() else [])
    except json.JSONDecodeError:
        code, note = 2, "could not parse `gh pr checks` output"
    results["CI"] = code
    print(f"  {MARK[code]} {'CI':18s} rc={code}  {note}")

    code, line = verdict(results)
    # ⛔ THE HOUSE RULE (see hold_reasons). Computed over the PR's own diff against the base.
    try:
        files, fs = gather(git_reader(_run), BASE_REF)
        gathered = True
    except Exception as exc:              # r10: ANY collection error fails CLOSED, never a crash
        code, line = 2, (f"CANNOT RUN — could not read the branch's diff ({exc.__class__.__name__}: {exc}), so the house "
                         "rule's exceptions were NOT checked. Treat this as NOT RUN.")
        holds, gathered = [], False
    if gathered:
        try:
            nr = granted_escapes(body_file.read_text()).get("NO-REVIEW:") is not None
        except Exception as exc:
            nr = None
            code, line = 2, (f"CANNOT RUN — the NO-REVIEW matcher failed ({exc.__class__.__name__}), "
                             f"so the waiver exception was NOT checked. Treat this as NOT RUN.")
        # Paths from the machine list — never `.split()` of `--name-only`, which cut a path
        # containing a space into two "files"; hunks from each file's own patch.
        holds = (hold_reasons(files, "", head, args.app_tests_passed, bool(nr), fs=fs)
                 if nr is not None else [])
    for h in holds:
        print(f"  HOLD {h}")
    code, line = final_verdict(code, line, holds)
    print()
    print(line)
    if code == HOLD_RC:
        return code
    if code:
        print("  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is "
              "why this script exists and why 'all my gates are green' is a different claim.")
    return code


# ── SELF-TEST ─────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    cases, failures = 0, 0

    def check(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    WF = """jobs:
  verify:
    steps:
      - name: unit tests
        run: npm test
      - name: dashboard entry ratchet
        if: github.event_name == 'pull_request'
        run: python3 scripts/check-dashboard-entry.py
      - name: check-review-recorded (PR only)
        if: github.event_name == 'pull_request'
        env:
          BODY: ${{ github.event.pull_request.body }}
        run: python3 scripts/check-review-recorded.py
"""
    check("both pull-request-only steps are found, in order", pr_only_steps(WF),
          ["dashboard entry ratchet", "check-review-recorded (PR only)"])
    check("a step with no `if:` is not pull-request-only", "unit tests" in pr_only_steps(WF), False)
    check("a workflow with no gated step yields none", pr_only_steps("      - name: x\n        run: y\n"), [])
    check("an `if:` on a DIFFERENT condition is not collected",
          pr_only_steps("      - name: x\n        if: github.event_name == 'push'\n        run: y\n"), [])
    # ⚠ The condition must attach to the step it FOLLOWS, not to a later one.
    check("the condition binds to its own step, not the next",
          pr_only_steps("      - name: a\n        run: x\n      - name: b\n"
                        "        if: github.event_name == 'pull_request'\n        run: y\n"), ["b"])
    # ⛔ THIS CASE EXISTS BECAUSE ITS MUTATION SURVIVED — TWICE, for two different reasons, and
    # the second is the interesting one. Dropping `current = None` first survived because no
    # fixture had a SECOND line carrying the condition. The fixture written to fix that used a
    # `run:` line echoing the condition — and then the Codex-Medium fix, which made the parser
    # match the `if:` FIELD rather than any line, HOLLOWED THAT CASE OUT: a `run:` line is no
    # longer a condition, so the case stopped exercising `current = None` and the mutation
    # survived again, silently. A fix that removes a signal removes its falsifier with it.
    # Two `if:` lines is what the disarm actually guards against now.
    check("a step with two condition lines is counted ONCE",
          pr_only_steps("      - name: b\n        if: github.event_name == 'pull_request'\n"
                        "        if: github.event_name == 'pull_request'\n        run: y\n"), ["b"])
    # ── CODEX r1 MEDIUM: the hostile spellings, verbatim. Each defeated the substring scan. ──
    # ⛔ The double-quote case is the dangerous one: it MISSED a pull-request-only step, which is
    # this script reporting READY while a gate refuses. The other two over-reported, which is
    # merely noisy.
    check("a DOUBLE-QUOTED condition is still pull-request-only",
          pr_only_steps('      - name: x\n        if: github.event_name == "pull_request"\n        run: y\n'), ["x"])
    check("the same condition inside a COMMENT is not a step condition",
          pr_only_steps("      - name: x\n        # if: github.event_name == 'pull_request'\n        run: y\n"), [])
    check("the same condition ECHOED BY THE COMMAND is not a step condition",
          pr_only_steps("      - name: x\n        run: echo \"github.event_name == 'pull_request'\"\n"), [])
    check("the `${{ }}` wrapper form is recognised",
          pr_only_steps("      - name: x\n        if: ${{ github.event_name == 'pull_request' }}\n        run: y\n"), ["x"])
    # ⚠ The REAL workflow, not a fixture: the derivation must agree with what CI actually gates.
    check("the derivation finds exactly the FOUR steps ci.yml gates today",
          sorted(pr_only_steps(WORKFLOW.read_text())) if WORKFLOW.is_file() else [],
          ["check-review-recorded (PR only)", "dashboard entry ratchet",
           "doc citations resolve", "reference namespaces are qualified"])

    check("the real workflow has pull-request-only steps — an empty answer here is CANNOT RUN",
          len(pr_only_steps(WORKFLOW.read_text())) > 0 if WORKFLOW.is_file() else True, True)

    check("all green is READY", verdict({"a": 0, "b": 0})[0], 0)
    check("one failure is NOT READY", verdict({"a": 0, "b": 1})[0], 1)
    check("...and it names the failing check", "b" in verdict({"a": 0, "b": 1})[1], True)
    # ⛔ 2 BEATS 1, and testing them separately would let the ordering bug through.
    check("a CANNOT RUN alongside a failure still reports CANNOT RUN",
          verdict({"a": 1, "b": 2})[0], 2)
    check("...and says NOT RUN rather than naming a failure count",
          "NOT RUN" in verdict({"a": 1, "b": 2})[1], True)
    check("nothing checked is CANNOT RUN, not READY", verdict({})[0], 2)

    # ── CLAUDE r1: the parser shapes that escaped BOTH earlier versions ────────────────────
    JOBS = ("jobs:\n  a:\n    steps:\n      - name: last of a\n        run: x\n"
            "  b:\n    if: github.event_name == 'pull_request'\n"
            "    steps:\n      - name: real\n        run: y\n")
    # ⛔ v2 returned ['last of a'] here — wrong in BOTH directions at once: it named a step that is
    # not gated and missed the job that is. A job-level `if:` is the form schema-gates.yml writes.
    check("a JOB-level condition does not attach to the previous job's last step",
          pr_only_steps(JOBS), [])
    check("...and the gated JOB is reported by its own rule, so the gap is named not silent",
          job_level_gates(JOBS), ["b"])
    check("a job gated on a DIFFERENT event is not collected",
          job_level_gates("jobs:\n  a:\n    if: github.event_name == 'schedule'\n"), [])
    check("`- if:` as a step's FIRST key, before name:, is still found",
          pr_only_steps("      - if: github.event_name == 'pull_request'\n"
                        "        name: x\n        run: y\n"), ["x"])

    # ── CODEX r2, two Highs — both SILENT MISSES of a real gate ────────────────────────────
    # An `if:` inside a `run: |` body or a `with:` map used to SHADOW the step's own condition.
    check("an `if:` inside a run: body does not shadow the step's own condition",
          pr_only_steps("      - name: shell\n        run: |\n"
                        "          if: github.event_name == 'push'\n"
                        "        if: github.event_name == 'pull_request'\n"), ["shell"])
    check("an `if:` inside a with: map does not shadow it either",
          pr_only_steps("      - name: upload\n        with:\n"
                        "          if: github.event_name == 'push'\n"
                        "        if: github.event_name == 'pull_request'\n"), ["upload"])
    check("a FOLDED condition (`if: >`) is read from its continuation lines",
          pr_only_steps("      - name: folded\n        if: >\n"
                        "          github.event_name == 'pull_request'\n        run: echo ok\n"), ["folded"])
    check("a folded condition on a JOB is reported too, not dropped",
          job_level_gates("jobs:\n  b:\n    if: >\n"
                          "      github.event_name == 'pull_request'\n    steps:\n      - name: x\n"), ["b"])

    # ── THE ALLOW-LIST RATCHET — Claude r2, High, replacing an auditor that was WEAKER than
    # the parser it audited and so certified a parse it could not perform. ──────────────────
    # ⛔ THE ESCAPE THAT BROKE THE PREVIOUS DESIGN. A condition split across a line break was
    # invisible to the parser AND to the auditor, so a real gate vanished with the soundness
    # check reporting clean. A substring scan cannot miss it, because it is not parsing.
    SPLIT = ("      - name: x\n        if: github.event_name ==\n"
             "          'pull_request'\n        run: y\n")
    check("a condition split across a line break is CAUGHT even though no rule claims it",
          (pr_only_steps(SPLIT), unaccounted_mentions(SPLIT, "ci.yml") != []), ([], True))
    check("an unknown mention is reported with its file and line text",
          unaccounted_mentions("      on-pull_request-magic: true\n", "ci.yml"),
          ["ci.yml: on-pull_request-magic: true"])
    # ⚠ A ratchet keyed on PRESENCE rather than COUNT leaks: a second copy of an approved line
    # would ride in on the first one's ticket.
    check("a SECOND copy of an approved line is unaccounted — the allowance is a count",
          len(unaccounted_mentions("  pull_request:\n  pull_request:\n", "schema-gates.yml")), 1)
    # ⛔ CLAUDE r3, Medium: `.yaml` is a workflow too, and a `release.yaml` carrying a gate was
    # invisible to all three mechanisms — no stray, no CANNOT RUN, a printed READY.
    with tempfile.TemporaryDirectory() as _d:
        _p = Path(_d)
        (_p / "ci.yml").write_text("x")
        (_p / "release.yaml").write_text("y")
        (_p / "notes.md").write_text("z")
        check("both workflow extensions are found, and nothing else is",
              [f.name for f in workflow_files(_p)], ["ci.yml", "release.yaml"])

    # ⛔ CODEX r3, High: PR-ONLY-NESS CAN BE EXPRESSED WITHOUT THE WORD. `ci.yml` runs on exactly
    # `pull_request` and `push`, so `!= 'push'` gates a step on pull requests only — and it
    # escaped both the parser and a scan keyed on `pull_request`. The detector keys on
    # `github.event_name` too, which is the class rather than this instance.
    check("a gate expressed by EXCLUSION is caught even with no `pull_request` in it",
          unaccounted_mentions("      - name: x\n        if: github.event_name != 'push'\n", "ci.yml"),
          ["ci.yml: if: github.event_name != 'push'"])
    # ⚠ The other direction, and it is why the four schema-gates entries exist: widening the
    # detector must not make the checker refuse to answer on a normal repository.
    check("schema-gates' own event-name lines are accounted for, not a false CANNOT RUN",
          unaccounted_mentions("    if: github.event_name != 'schedule'\n", "schema-gates.yml"), [])

    check("a commented-out mention is not a gate and is not flagged",
          unaccounted_mentions("      # if: github.event_name == 'pull_request'\n", "ci.yml"), [])
    # ⚠ THE OTHER DIRECTION. A checker that refuses to answer on a normal repository is useless.
    check("the real workflows are fully accounted for — no false CANNOT RUN",
          [w.name for w in workflow_files(WORKFLOW_DIR)
           if unaccounted_mentions(w.read_text(), w.name)] if WORKFLOW_DIR.is_dir() else [], [])

    # ── CLAUDE r1, High: UNKNOWN is "not computed yet", and it is what GitHub returns FIRST ──
    UNK = {"state": "OPEN", "isDraft": False, "baseRefName": "master",
           "headRefOid": "abc123", "mergeStateStatus": "UNKNOWN"}
    check("UNKNOWN is CANNOT RUN, not a refusal — GitHub has not computed it yet",
          mergeability(UNK, "abc123")[0], 2)
    check("...and it says so, rather than naming a state the branch is not in",
          "not computed" in mergeability(UNK, "abc123")[1], True)
    # ⚠ Claude r1, Low: the old comment enumerated the refusal set and omitted this one.
    check("HAS_HOOKS is mergeable — GitHub merges it",
          mergeability({**UNK, "mergeStateStatus": "HAS_HOOKS"}, "abc123")[0], 0)

    # ── MERGEABILITY — code review r1 (Codex), High: the catastrophic false READY ───────────
    OK = {"state": "OPEN", "isDraft": False, "baseRefName": "master",
          "headRefOid": "abc123", "mergeStateStatus": "CLEAN"}
    check("an open, clean, on-master PR at the local head is mergeable",
          mergeability(OK, "abc123")[0], 0)
    check("a DRAFT is not mergeable", mergeability({**OK, "isDraft": True}, "abc123")[0], 1)
    check("a PR based on another branch is not mergeable",
          mergeability({**OK, "baseRefName": "develop"}, "abc123")[0], 1)
    check("a CONFLICTED PR is not mergeable",
          mergeability({**OK, "mergeStateStatus": "DIRTY"}, "abc123")[0], 1)
    # ⚠ UNSTABLE means a NON-REQUIRED check is failing and GitHub still permits the merge.
    check("UNSTABLE is mergeable — GitHub permits it, so this must not refuse it",
          mergeability({**OK, "mergeStateStatus": "UNSTABLE"}, "abc123")[0], 0)
    # ⛔ The easiest false READY there is, and this script TAKES a --pr argument.
    check("a PR whose head is not the local HEAD is refused",
          mergeability(OK, "def456")[0], 1)
    check("...and the message says which commit is which",
          all(s in mergeability(OK, "def456")[1] for s in ("abc123", "def456")), True)
    check("a closed PR is not mergeable", mergeability({**OK, "state": "MERGED"}, "abc123")[0], 1)
    check("a missing field is CANNOT RUN, not a pass", mergeability({}, "abc123")[0], 2)
    check("no local HEAD is CANNOT RUN, not a pass", mergeability(OK, None)[0], 2)

    check("no checks reported is CANNOT RUN, not a vacuous pass", ci_conclusion([])[0], 2)
    check("a pending check is not a pass",
          ci_conclusion([{"name": "verify", "bucket": "pending"}])[0], 2)
    check("a failing check is NOT READY",
          ci_conclusion([{"name": "verify", "bucket": "fail"}])[0], 1)
    check("...and names it", "verify" in ci_conclusion([{"name": "verify", "bucket": "fail"}])[1], True)
    check("skipping does not count as failing",
          ci_conclusion([{"name": "a", "bucket": "pass"}, {"name": "b", "bucket": "skipping"}])[0], 0)

    # ── the escape cross-check (2026-09-26) ──────────────────────────────────
    D, R = "dashboard entry", "review recorded"
    NE, NR = "NO-ENTRY:", "NO-REVIEW:"
    none2 = {NE: None, NR: None}
    check("a refusing gate whose own escape is granted says nothing",
          escape_diagnosis([D], {NE: "docs only", NR: None}, "NO-ENTRY: docs only"), [])
    _mis = escape_diagnosis([D], {NE: None, NR: "prose"}, "NO-REVIEW: prose")
    check("MISDIRECTED: the dashboard gate refused while NO-REVIEW is granted", len(_mis), 1)
    check("...and it names the token THIS gate wants", NE in _mis[0], True)
    check("...and names the one that answers the other gate", NR in _mis[0], True)
    # ⛔ THE CASE THAT DISTINGUISHES MISDIRECTED FROM INERT-OTHER, added because a mutation
    # silencing MISDIRECTED SURVIVED: control fell through to INERT-OTHER, whose message also
    # carries both tokens and is also one line, so every assertion above still passed. The
    # distinguishing PROPERTY is that the other escape WAS granted — so it is not inert, and
    # saying it is would be false.
    check("...and does NOT call the other declaration inert, because it was granted",
          "inert" in _mis[0], False)
    check("...whereas the INERT case does say so — the two states are distinguishable",
          "inert" in escape_diagnosis([D], none2, "NO-REVIEW: ungranted")[0], True)
    check("MISDIRECTED mirrors: the review gate refused while NO-ENTRY is granted",
          NR in escape_diagnosis([R], {NE: "docs", NR: None}, "NO-ENTRY: docs")[0], True)
    check("INVISIBLE: the exact token is present but granted nothing",
          "must start its own line" in
          escape_diagnosis([D], none2, "    NO-ENTRY: indented four")[0], True)
    check("MISSPELLED: an underscore lookalike names the literal the gate wants",
          NE in escape_diagnosis([D], none2, "NO_ENTRY: typo")[0], True)
    check("MISSPELLED: lowercase is diagnosed too",
          len(escape_diagnosis([D], none2, "no-entry: lower")), 1)
    check("...and names the lowercase text it actually found",
          "no-entry" in escape_diagnosis([D], none2, "no-entry: lower")[0], True)
    check("a body with no escape at all produces no diagnosis",
          escape_diagnosis([D], none2, "just a normal PR body"), [])
    check("a gate with no escape of its own (review rounds) is never diagnosed",
          escape_diagnosis(["review rounds"], none2, "NO-ENTRY: x"), [])
    check("NOTHING is said when no gate refused — it explains, never accuses",
          escape_diagnosis([], none2, "NO_ENTRY: typo"), [])
    # ⭐ THE STATE THE REAL INCIDENT WAS IN — found by replaying the actual PR bodies.
    check("INERT OTHER: the other token is present but was granted nothing",
          "inert" in escape_diagnosis([D], none2, "`NO-REVIEW:` backticked, so no gate sees it")[0],
          True)
    check("...and it says backticks are one of the causes",
          "backticks" in escape_diagnosis([D], none2, "`NO-REVIEW:` backticked")[0], True)
    check("a MISSPELLED diagnosis names the lookalike it found",
          "NO_ENTRY" in escape_diagnosis([D], none2, "NO_ENTRY: typo")[0], True)
    check("both gates refusing can yield two diagnoses",
          len(escape_diagnosis([D, R], none2, "NO_ENTRY: typo and NO_REVIEW: typo")), 2)
    # ⛔ THE REAL MATCHER, not a copy of its rule — these assert the imported gate's behaviour.
    _g = granted_escapes("NO-ENTRY: docs only")
    check("the imported matcher grants a well-formed NO-ENTRY", _g[NE], "docs only")
    check("...and grants nothing for the other marker", _g[NR], None)
    check("the imported matcher refuses a 4-column-indented token",
          granted_escapes("    NO-ENTRY: x")[NE], None)
    check("the imported matcher refuses a fenced token",
          granted_escapes("```\nNO-ENTRY: x\n```")[NE], None)

    # ── THE HOUSE RULE'S EXCEPTIONS (2026-10-25) — each fired by TWO DISTINCT inputs, and each
    # with an ADJACENT input that must stay quiet, so no branch passes on one fixture's constant.
    def DF(path, *hunk):
        return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n" + "\n".join(hunk) + "\n"
    def H(files=(), diff="", head="abc", at=None, nr=False):
        return hold_reasons(list(files), diff, head, at, nr)
    def _raises(fn, exc):
        try:
            fn()
        except exc:
            return True
        except Exception:                 # the WRONG exception is a red case, not a crashed suite
            return False
        return False
    def has(rs, word):
        return any(word in r for r in rs)
    check("no exception: an ordinary docs-and-script PR is not held", H(["docs/x.md", "scripts/foo.py"]), [])
    for bl in ("docs/reviews/decision-scheme/baseline.json", "docs/reviews/other/baseline.json"):
        check(f"a pinned baseline edit is a loosening ({bl.split('/')[2]})",
              has(H([bl]), "pinned baseline"), True)
    check("...but a file merely NAMED like one outside docs/reviews/ is not",
          H(["scripts/baseline.json"]), [])
    PC = "scripts/check-plan-code.py"
    for o, n in ((128, 125), (30, 2)):
        check(f"a mutation pin that DROPS {o} -> {n} is a loosening",
              has(H([PC], DF(PC, f'-    "scripts/a.py": {o},', f'+    "scripts/a.py": {n},')), f"{o} -> {n}"), True)
    check("...but a pin that RISES is not", H([PC], DF(PC, '-    "scripts/a.py": 125,', '+    "scripts/a.py": 129,')), [])
    for o, n in ((2021, 2017), (900, 10)):
        check(f"a declared mutation total that drops {o} -> {n} is a loosening",
              has(H([PC], DF(PC, f"-    case(\"t\", sum(EXPECTED_MUTATIONS.values()), {o})",
                               f"+    case(\"t\", sum(EXPECTED_MUTATIONS.values()), {n})")), "total drops"), True)
    for o, n in ((274, 271), (9, 1)):
        check(f"a declared self-test count that drops {o} -> {n} is a loosening",
              has(H(["scripts/z.py"], DF("scripts/z.py", f"-    python3 scripts/z.py --self-test  # {o} cases",
                                         f"+    python3 scripts/z.py --self-test  # {n} cases")), "fewer self-test"), True)
    check("...but a count that rises is not",
          H(["scripts/z.py"], DF("scripts/z.py", "-    z --self-test  # 271 cases", "+    z --self-test  # 274 cases")), [])
    G = "scripts/check-x.py"
    # ⭐ PR #398's own shape: the removed line names no failure word; `fails.append` is 4 lines on.
    _398 = DF(G, '     ("3 LOST", t3(rows)),', '-    ("4 NO IMPROVEMENT", t4(rows)),', '     ("5 RANKER", t5(rows)),',
             '     ):', '         if result:', '             fails.append((name, result))')
    check("⭐ a check entry REMOVED from beside a fails list is a loosening (PR #398's shape)",
          has(H([G], _398), "failure path"), True)
    # Direct calls with DISTINCT literals in every position, beside `H`'s one call site.
    check("a PR #398-shaped removal AND a waiver give both reasons, with no head at all",
          [r.split(":")[0] for r in hold_reasons([G], _398, None, None, True)],
          ["loosens a gate", "relied on a waiver"])
    check("app code cleared at head 'f00d' stays cleared with nothing else wrong",
          hold_reasons(["worker/run.ts"], "", "f00d", "f00d", False), [])
    check("a removed `return 1` in a gate is a loosening",
          has(H([".claude/hooks/h.sh"], DF(".claude/hooks/h.sh", "-    return 1", "+    return 0")), "failure path"), True)
    check("...but the SAME line MOVED (removed and re-added) is not",
          H([G], DF(G, '-    ("4 NO IMPROVEMENT", t4(rows)),', '+    ("4 NO IMPROVEMENT", t4(rows)),',
                   '     fails.append(x)')), [])
    check("...and a removed COMMENT beside a fails list is not",
          H([G], DF(G, "-    # FAIL here once", "     fails.append(x)")), [])
    check("...and the same removal in a NON-gate script is not",
          H(["tools/page.py"], DF("tools/page.py", "-    return 1", "+    return 0")), [])
    _far = DF(G, "-    x = 1", *[f"     y{i} = {i}" for i in range(6)], "     fails.append(x)")
    check("...and a removal SIX lines from the failure path is outside the window", H([G], _far), [])
    # r1 (both halves): a DELETED gate dropped every removed line, so deleting a check was READY.
    def DEL(path, *gone):
        return (f"diff --git a/{path} b/{path}\ndeleted file mode 100644\n--- a/{path}\n+++ /dev/null\n"
                f"@@ -1,{len(gone)} +0,0 @@\n" + "\n".join("-" + g for g in gone) + "\n")
    check("⭐ DELETING a gate script outright is a loosening",
          has(H([G], DEL(G, "if bad:", "    return 1", "x = 2")), "failure path"), True)
    check("...and so is deleting a hook in a subdirectory",
          has(H([".claude/hooks/sub/b.sh"], DEL(".claude/hooks/sub/b.sh", "case $x in", '  *) deny "no";;')),
              "failure path"), True)
    check("...but deleting a NON-gate script is not",
          H(["tools/page.py"], DEL("tools/page.py", "if bad:", "    return 1")), [])
    # r1: distance was counted over the COMBINED diff, so added lines pushed a removal out.
    check("⭐ six ADDED comment lines do not push an adjacent removal out of the window",
          has(H([G], DF(G, '-    ("4 NO IMPROVEMENT", t4(rows)),', *[f"+    # why {i}" for i in range(6)],
                        '     fails.append(x)')), "failure path"), True)
    check("...nor do eight added CODE lines",
          has(H([G], DF(G, "-    check_entry(rows)", *[f"+    y{i} = {i}" for i in range(8)],
                        "     failures += 1")), "failure path"), True)
    # r1 CLAUDE H3: the hooks' blocking idioms.
    check("a hook's removed `deny` is a loosening",
          has(H([".claude/hooks/a.sh"], DF(".claude/hooks/a.sh", '-  deny "no --no-verify"', "+  :")), "failure path"), True)
    check("...and so is a hook's `exit 2` turned into `exit 0`",
          has(H([".claude/hooks/b.sh"], DF(".claude/hooks/b.sh", "-    exit 2", "+    exit 0")), "failure path"), True)
    check("...but a removed `echo` in a hook, on no failure path, is not",
          H([".claude/hooks/a.sh"], DF(".claude/hooks/a.sh", "-  echo hi", "+  echo hello")), [])
    # r1 CLAUDE M1: a gate disabled where it is INVOKED.
    CI = ".github/workflows/ci.yml"
    check("⭐ a CI step that runs a check, removed, is a loosening",
          has(H([CI], DF(CI, "-        run: python3 scripts/check-x.py --self-test")), "gate invocation"), True)
    check("...and so is a hook dropped from settings.json",
          has(H([".claude/settings.json"], DF(".claude/settings.json", '-  "command": "bash .claude/hooks/h.sh"')),
              "gate invocation"), True)
    check("...but the same CI line MOVED is not",
          H([CI], DF(CI, "-        run: python3 scripts/check-x.py --self-test",
                     "+        run: python3 scripts/check-x.py --self-test")), [])
    check("...nor a removed CI line that names no gate",
          H([CI], DF(CI, "-        node-version: 20", "+        node-version: 22")), [])
    # r2 CODEX M1/M2 — after the REDESIGN to one parser. Renames carry both paths; comments are
    # one rule for every detector.
    def REN(old, new, *hunk):
        head = f"diff --git a/{old} b/{new}\nsimilarity index 90%\nrename from {old}\nrename to {new}\n"
        return head + (f"--- a/{old}\n+++ b/{new}\n@@ -1 +1 @@\n" + "\n".join(hunk) + "\n" if hunk else "")
    check("⭐ a gate RENAMED out of scope with `return 1` -> `return 0` is a loosening (failure path)",
          has(H([G], REN(G, "tools/validate-x.py", "-    return 1", "+    return 0")), "failure path"), True)
    check("...and the rename itself is a scope exit",
          has(H([G], REN(G, "tools/validate-x.py", "-    return 1", "+    return 0")), "renamed to tools/validate-x.py"), True)
    check("⭐ a workflow MOVED out of .github/workflows/ with no hunk at all is a loosening",
          has(H([CI], REN(".github/workflows/gate.yml", ".github/archived/gate.yml")), "renamed to .github/archived"), True)
    check("...and so is a hook moved into docs/ with its `deny` dropped",
          has(H([".claude/hooks/a.sh"], REN(".claude/hooks/a.sh", "docs/a.sh", '-  deny "x"', "+  :")), "failure path"), True)
    check("...but a workflow renamed WITHIN .github/workflows/ is not",
          H([CI], REN(".github/workflows/a.yml", ".github/workflows/b.yml")), [])
    check("...nor a docs file renamed anywhere",
          H(["docs/b.md"], REN("docs/a.md", "docs/b.md", "-old", "+new")), [])
    check("⭐ a reworded workflow COMMENT naming a check is not a dropped invocation (r2 false HOLD)",
          H([CI], DF(CI, "-  # scripts/check-x.py guards the table", "+  # The table guard runs below",
                     "   - run: python3 scripts/check-x.py")), [])
    check("...nor a reworded shell comment in check-schema-gates.sh",
          H(["scripts/check-schema-gates.sh"], DF("scripts/check-schema-gates.sh",
                                                  "-# --self-test of each gate", "+# each gate's self-test")), [])
    check("...but the invocation BESIDE such a comment, removed, still is",
          has(H([CI], DF(CI, "-  # scripts/check-x.py guards the table", "-  - run: python3 scripts/check-x.py")),
              "gate invocation"), True)
    check("a deleted workflow is a scope exit",
          has(H([CI], DEL(".github/workflows/old.yml", "on: push")), "old.yml is deleted"), True)
    # r3 CODEX — PATH IDENTITY. Each header below is copied from a REAL `git diff -M -C` run in a
    # scratch repository, not composed from memory of the format.
    _q = ('diff --git "a/.github/workflows/gat\\303\\251.yml" "b/.github/workflows/gat\\303\\251.yml"\n'
          'deleted file mode 100644\nindex 4050f61..0000000\n--- "a/.github/workflows/gat\\303\\251.yml"\n'
          '+++ /dev/null\n@@ -1,2 +0,0 @@\n-on: push\n-      - run: python3 scripts/check-x.py --self-test\n')
    check("⭐ a deleted workflow whose path git C-QUOTES (non-ASCII) is a scope exit",
          has(H([CI], _q), "gaté.yml is deleted"), True)
    _sp = ("diff --git a/scripts/check-space name.py b/scripts/check-space name.py\n"
           "--- a/scripts/check-space name.py\t\n+++ b/scripts/check-space name.py\t\n"
           "@@ -1,2 +1,2 @@\n     if bad:\n-        return 1\n+        return 0\n")
    check("⭐ a gate whose path has a SPACE (git appends a tab) still has its failure path read",
          has(H([G], _sp), "check-space name.py removes"), True)
    _bin = ("diff --git a/.github/workflows/bin.yml b/.github/workflows/bin.yml\ndeleted file mode 100644\n"
            "index b3f526e..0000000\nBinary files a/.github/workflows/bin.yml and /dev/null differ\n")
    check("⭐ a BINARY-diffed workflow deleted (no `+++ /dev/null`) is a scope exit",
          has(H([CI], _bin), "bin.yml is deleted"), True)
    _new = ("diff --git a/.github/workflows/n.yml b/.github/workflows/n.yml\nnew file mode 100644\n"
            "index 0000000..b3f526e\nBinary files /dev/null and b/.github/workflows/n.yml differ\n")
    check("...but a binary workflow ADDED is not",
          H([CI], _new), [])
    check("⭐ a workflow renamed INTO scripts/check-*.py keeps no workflow role, so it is an exit",
          has(H([CI], REN(".github/workflows/mv.yml", "scripts/check-disabled.py")), "renamed to scripts/check-disabled.py"), True)
    check("...but a check renamed to another check keeps its role",
          H([G], REN("scripts/check-a.py", "scripts/check-b.py")), [])
    _cp = ("diff --git a/.github/workflows/cp.yml b/docs-gate.yml\nsimilarity index 100%\n"
           "copy from .github/workflows/cp.yml\ncopy to docs-gate.yml\n")
    check("⭐ a workflow COPIED out leaves the source running, so it is not an exit",
          H([CI], _cp), [])
    check("...while the same pair as a RENAME is",
          has(H([CI], _cp.replace("copy from", "rename from").replace("copy to", "rename to")), "renamed to docs-gate.yml"), True)
    # ⛔ BACKLOG #353 — A REAL GIT REPOSITORY, every path shape four rounds found, read through the
    # SAME collection `main()` runs (`gather`). Fixture text proves what the parser does to
    # the fixture; only git's own output proves what it does to git's output.
    _gw = Path(tempfile.mkdtemp())
    import fixture_git  # backlog #373: this fixture once committed into an exported GIT_DIR
    def _grun(cmd, **kw):
        kw.setdefault("text", True)
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]], cwd=_gw,
                              capture_output=True, env=fixture_git.env(HOME=str(_gw)), **kw)
    _gread = git_reader(_grun)
    def _g(*a):
        return _gread(["git", *a])
    def _w(rel, text):
        (_gw / rel).parent.mkdir(parents=True, exist_ok=True)
        (_gw / rel).write_text(text)
    try:
        _g("init", "-q")
        _g("config", "core.quotePath", "false")      # r4 XM2: literal Unicode inside quoted paths
        for _n in ("gaté", "bin", "😀", "mv"):
            _w(f".github/workflows/{_n}.yml", f"name: {_n}\njobs:\n  {_n}:\n    steps:\n      - run: python3 scripts/check-{_n}.py\n")
        _w(".gitattributes", ".github/workflows/bin.yml -diff\n")
        _w("scripts/check-space name.py", "def main():\n    if bad:\n        return 1\n    return 0\n")
        _w(".claude/hooks/a b/z", "#!/bin/sh\ndeny() { exit 2; }\n")
        _w("scripts/check-old.sh", "#!/bin/sh\n# the old schema gate runner\nexit 0\n")
        _w("docs/reviews/x y/baseline.json", '{"median": 4}\n')
        _w("docs/a.md", "one\n")
        # r5 HIGH: a TYPE CHANGE (two patch sections for one entry), a submodule under
        # diff.submodule=log (no section), a textconv and an external driver over gates, and a
        # glob-looking gate name — each beside a gate weakening that must still be ITS gate's.
        _w("docs/t", "plain file\n")
        _w("scripts/check-tc.py", "def main():\n    if bad:\n        return 1\n    return 0\n")
        _w("scripts/check-ext.py", "def main():\n    if worse:\n        return 1\n    return 0\n")
        _w("scripts/check-[ab].py", "def main():\n    if odd:\n        return 1\n    return 0\n")
        _w("scripts/check-a.py", "def main():\n    return 0\n")
        _w("scripts/check-node.ts", "if (bad) {\n  process.exit(1);\n}\n")   # backlog #354
        # r6: a gate renamed while a DIRECTORY named like its old path appears; a `-diff` (binary)
        # attribute on a gate; a gate holding a NUL byte; a gate deleted outright.
        _w("scripts/check-rn.py", "def main():\n    if gone:\n        return 1\n    return 0\n")
        _w("scripts/check-bin.py", "def main():\n    if bin:\n        return 1\n    return 0\n")
        _w("scripts/check-nul.py", "# a\0b\ndef main():\n    if nul:\n        return 1\n    return 0\n")
        _w("scripts/check-del.py", "def main():\n    if dead:\n        return 1\n    return 0\n")
        # r7: two paths that differ only by CR vs LF, and a gate that is a SYMLINK to an outside target.
        _w("scripts/check-c\n.py", "import sys\nif bad:\n    sys.exit(1)\n")
        _w("scripts/check-c\r.py", "import sys\nsys.exit(0)\n")
        _w("tools/gate.py", "import sys\nif worst:\n    sys.exit(1)\n")
        (_gw / "scripts/check-linked.py").symlink_to("../tools/gate.py")
        _w(".gitattributes", ".github/workflows/bin.yml -diff\nscripts/check-tc.py diff=tc\nscripts/check-ext.py diff=ext\nscripts/check-bin.py -diff\n")
        _g("config", "diff.tc.textconv", "true")
        _g("config", "diff.ext.command", "true")
        _g("config", "diff.submodule", "log")
        _g("config", "diff.external", "true")        # an external diff for EVERY diff, printing nothing
        _g("add", "-A")
        _g("update-index", "--add", "--cacheinfo", "160000," + "1" * 40 + ",zmodule")
        _g("commit", "-qm", "base")
        _base = _g("rev-parse", "HEAD").strip()
        for _n in ("gaté", "bin", "😀"):
            _g("rm", "-q", f".github/workflows/{_n}.yml")
        _w("scripts/check-space name.py", "def main():\n    if bad:\n        return 0\n    return 0\n")
        (_gw / ".claude/hooks/a b/z").chmod(0o755)
        _g("mv", "scripts/check-old.sh", "scripts/check-schema-gates.sh")
        _g("mv", ".github/workflows/mv.yml", "scripts/check-disabled.py")
        _w("docs/reviews/x y/baseline.json", '{"median": 5}\n')
        _w("docs/a.md", "two\n")
        (_gw / "docs/t").unlink(); (_gw / "docs/t").symlink_to("a.md")
        for _n, _c in (("tc", "bad"), ("ext", "worse"), ("[ab]", "odd")):
            _w(f"scripts/check-{_n}.py", f"def main():\n    if {_c}:\n        return 0\n    return 0\n")
        _g("add", "-A")
        _g("mv", "scripts/check-rn.py", "scripts/check-rn2.py")
        _w("scripts/check-rn2.py", "def main():\n    if gone:\n        return 0\n    return 0\n")
        _w("scripts/check-rn.py/example.txt", "        return 1\n")
        _w("scripts/check-bin.py", "def main():\n    if bin:\n        return 0\n    return 0\n")
        _w("scripts/check-nul.py", "# a\0b\ndef main():\n    if nul:\n        return 0\n    return 0\n")
        _g("rm", "-q", "scripts/check-del.py")
        _w("scripts/check-c\n.py", "import sys\nif bad:\n    sys.exit(0)\n")
        _w("scripts/check-node.ts", "if (bad) {\n  process.exit(0);\n}\n")
        _w("tools/gate.py", "import sys\nif worst:\n    sys.exit(0)\n")
        _g("add", "-A")
        _g("update-index", "--add", "--cacheinfo", "160000," + "2" * 40 + ",zmodule")
        _g("commit", "-qm", "head")
        _files, _fs = gather(_gread, _base)
        _real = hold_reasons(_files, "", "h", "h", False, fs=_fs)
        _err = None
    except Exception as exc:                          # git missing or the parse raised: say so
        _real, _err = [], f"{exc.__class__.__name__}: {exc}"
    finally:
        shutil.rmtree(_gw, ignore_errors=True)
    check("⭐ the real-git world parses with no error (C-quoting, tabs, binary, ` b/`, emoji)", _err, None)
    check("real git: a deleted workflow with a NON-ASCII name is a scope exit", has(_real, "gaté.yml is deleted"), True)
    check("real git: a deleted workflow with an EMOJI name under core.quotePath=false is a scope exit",
          has(_real, "😀.yml is deleted"), True)
    check("real git: a BINARY-diffed workflow deleted is a scope exit", has(_real, "bin.yml is deleted"), True)
    check("real git: a gate with a SPACE in its path has its failure path read",
          has(_real, "scripts/check-space name.py removes"), True)
    check("real git: a workflow renamed into scripts/check-*.py is a scope exit",
          has(_real, "mv.yml is renamed to scripts/check-disabled.py"), True)
    check("real git: a baseline under a path WITH A SPACE is held (no `.split()` of the file list)",
          has(_real, "docs/reviews/x y/baseline.json is a pinned baseline"), True)
    check("real git: a hook under `a b/` with a MODE-ONLY change is not held (r4 false HOLD)",
          has(_real, "a b/z"), False)
    check("real git: a check renamed so it GAINS a role is not an exit (r4 false HOLD)",
          has(_real, "check-old.sh"), False)
    check("real git: an ordinary docs edit is not held", has(_real, "docs/a.md"), False)
    check("⭐ real git (r5 HIGH): a gate weakened beside a TYPE CHANGE and a submodule is still ITS gate's",
          has(_real, "scripts/check-space name.py removes"), True)
    check("real git: a textconv driver over a gate cannot hide its weakening",
          has(_real, "scripts/check-tc.py removes"), True)
    check("real git: an external diff driver over a gate cannot hide its weakening",
          has(_real, "scripts/check-ext.py removes"), True)
    # ⚠ git matches a pathspec LITERALLY FIRST, so this passes with or without --literal-pathspecs;
    # without it a glob name can only pull in a sibling's hunks (a false HOLD), never lose its own.
    # The flag itself is pinned by the RESTRICTED case below, which is what its mutation names.
    check("real git: a gate named like a GLOB (`check-[ab].py`) has its own patch read",
          has(_real, "scripts/check-[ab].py removes"), True)
    check("⭐ real git (r6): a gate renamed beside a DIRECTORY named like its old path keeps its weakening",
          has(_real, "check-rn2.py removes"), True)
    check("real git (r6): a `-diff` (binary) attribute on a gate cannot hide its weakening",
          has(_real, "scripts/check-bin.py removes"), True)
    check("real git: a gate whose content holds a NUL byte still has its hunks read (--text)",
          has(_real, "scripts/check-nul.py removes"), True)
    check("real git: a DELETED gate's failure path is read from its old blob",
          has(_real, "scripts/check-del.py removes"), True)
    check("⭐ real git (r7): of two paths differing only by CR vs LF, the CHANGED one keeps its weakening",
          (has(_real, "scripts/check-c\n.py removes"), has(_real, "scripts/check-c\r.py")), (True, False))
    check("⭐ real git (r7): a gate SYMLINKED to an outside target holds when the target weakens",
          has(_real, "scripts/check-linked.py removes"), True)
    check("...and the target itself, outside the gate roots, is not read under its own name",
          has(_real, "tools/gate.py removes"), False)
    check("⭐ real git (backlog #354): a TypeScript gate's `process.exit(1)` -> `0` is held",
          has(_real, "scripts/check-node.ts removes"), True)
    check("real git: the world REALLY holds a type change (T) and a submodule entry",
          (("docs/t", "T") in {(f["new"], f["status"]) for f in _fs},
           ("zmodule", "M") in {(f["new"], f["status"]) for f in _fs}) if _err is None else _err, (True, True))
    check("real git: the type-changed docs file and the submodule hold nothing of their own",
          (has(_real, "docs/t"), has(_real, "zmodule")), (False, False))
    check("patch_hunks reads every hunk of a TWO-section patch (a type change) and no header",
          patch_hunks("diff --git a/t b/t\ndeleted file mode 100644\n--- a/t\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
                      "diff --git a/t b/t\nnew file mode 120000\n--- /dev/null\n+++ b/t\n@@ -0,0 +1 @@\n+y\n"),
          [["-x"], ["+y"]])
    check("changed_paths keeps a renamed file's OLD path too (a baseline renamed away is still edited)",
          changed_paths("R100\0docs/reviews/d/baseline.json\0docs/old.json\0A\0n.md\0"),
          ["docs/old.json", "docs/reviews/d/baseline.json", "n.md"])
    check("patch_hunks keeps a removed line whose TEXT starts `-- ` (shown as `--- `) inside its hunk",
          patch_hunks("diff --git a/g b/g\n--- a/g\n+++ b/g\n@@ -1,2 +1 @@\n--- not a header\n keep\n"),
          [["--- not a header", " keep"]])
    _asked: list = []
    def _rd(cmd):
        _asked.append(cmd[1] if cmd[1] != "--literal-pathspecs" else "status")
        if "merge-base" in cmd:
            return "mb0\n"
        if "--name-status" in cmd:
            return "R100\0scripts/o p\0scripts/n\0A\0docs/d.md\0"
        if cmd[1] == "ls-tree":
            return ("100644 blob aaa\tscripts/o p\0" if cmd[-1] == "mb0" else
                    "100644 blob bbb\tscripts/n\x00100644 blob ddd\tdocs/d.md\0")
        if cmd[1] == "diff":
            return "@@ -1 +1 @@\n-a\n+b\n" if cmd[-2:] == ["aaa", "bbb"] else "WRONG BLOBS"
        return "never read\n"
    check("⭐ gather diffs each entry's EXACT BLOBS (old tree's, new tree's) and reads no file outside the gate roots",
          (gather(_rd, "b0"), _asked),
          ((["docs/d.md", "scripts/n", "scripts/o p"],
            [{"old": "scripts/o p", "new": "scripts/n", "copy": False, "status": "R", "hunks": [["-a", "+b"]]},
             {"old": None, "new": "docs/d.md", "copy": False, "status": "A", "hunks": []}]),
           ["merge-base", "status", "ls-tree", "ls-tree", "diff"]))
    check("tree_index reads modes and ids by exact path, a space and a gitlink included",
          tree_index("100644 blob a1\tx y\x00160000 commit c2\tsub\0"), {"x y": ("100644", "a1"), "sub": ("160000", "c2")})
    _read_gl: list = []
    check("blob_hunks: a gitlink on both sides has no hunks, and reads nothing",
          (blob_hunks(lambda c: _read_gl.append(c) or "@@ -1 +1 @@\n-x\n+y\n", ("160000", "c1"), ("160000", "c2")),
           _read_gl), ([], []))
    check("tree_index of an empty tree is empty", tree_index(""), {})
    check("as_text keeps a CR a CR (no newline translation) and passes text through",
          (as_text(b"a\rb\n"), as_text("x\ry")), ("a\rb\n", "x\ry"))
    check("git_reader RAISES on a failed command rather than answering empty",
          _raises(lambda: git_reader(lambda c, **k: subprocess.CompletedProcess(c, 128, b"", b""))(["git", "x"]),
                  PathsDisagree), True)
    check("blob_hunks: an ADDED blob is every line added, a DELETED one every line removed",
          (blob_hunks(lambda c: "x\ny\n", None, ("100644", "n1")), blob_hunks(lambda c: "z\n", ("100755", "o1"), None)),
          ([["+x", "+y"]], [["-z"]]))
    check("...and a modify and a delete each name one path", changed_paths("M\0a\0D\0b\0"), ["a", "b"])
    check("...and the machine list's range follows the base it is given, literally",
          (status_cmd("f00dbab")[-1], "--literal-pathspecs" in status_cmd("origin/master")), ("f00dbab...HEAD", True))
    check("...and an incomplete --name-status entry",
          _raises(lambda: name_status("R100\0only-one\0"), PathsDisagree), True)
    check("name_status reads a rename, an add and a delete",
          [(e["status"], e["old"], e["new"]) for e in name_status("R091\0a b\0c\0A\0n\0D\0o\0")],
          [("R", "a b", "c"), ("A", None, "n"), ("D", "o", None)])
    # r8 (HONEST): a helper the gate imports, and a status other than 1 or 2.
    check("⭐ a weakened HELPER module (not `check-*`) is a loosening — the gate imports it",
          has(H(["scripts/gate_logic.py"], DF("scripts/gate_logic.py", "     if bad:", "-        return 1", "+        return 0")),
              "gate_logic.py removes"), True)
    check("...but the same edit outside scripts/ is not", H(["tools/gate_logic.py"], DF("tools/gate_logic.py",
          "     if bad:", "-        return 1", "+        return 0")), [])
    check("⭐ a gate's `sys.exit(3)` turned into success is a loosening (any non-zero status)",
          has(H([G], DF(G, "     if refused:", "-        sys.exit(3)", "+        sys.exit(0)")), "failure path"), True)
    check("...and so is a `return 7`",
          has(H([G], DF(G, "     if odd:", "-        return 7", "+        return 0")), "failure path"), True)
    check("...but `return 0` -> `return 0` with an unrelated line removed beside it is not a failure path",
          H([G], DF(G, "-    x = 1", "     return 0")), [])
    # r9 (HONEST-SYNTACTIC): re-indentation is not a move; any non-zero int; raise.
    check("⭐ `return 1` pushed under a new `if verbose:` is NOT a move — it is a loosening",
          has(H([G], DF(G, "     if bad:", '-        print("invalid input")', "-        return 1", "+        if verbose:",
                        '+            print("invalid input")', "+            return 1", "     return 0")), "failure path"), True)
    check("...while the SAME line at the SAME indentation moved is still a move",
          H([G], DF(G, "     if bad:", "-        return 1", "+        return 1", "     return 0")), [])
    check("a gate's `sys.exit(10)` turned into success is a loosening",
          has(H([G], DF(G, "     if worse:", "-        sys.exit(10)", "+        sys.exit(0)")), "failure path"), True)
    check("...and so is `sys.exit(-1)`",
          has(H([G], DF(G, "     if odd:", "-        sys.exit(-1)", "+        sys.exit(0)")), "failure path"), True)
    check("⭐ `sys.exit(\"invalid input\")` turned into a `print` is a loosening (r10: it exits 1)",
          has(H([G], DF(G, "     if bad:", '-        sys.exit("invalid input")', '+        print("invalid input")')),
              "failure path"), True)
    check("...but `sys.exit(0)`, `sys.exit()` and `sys.exit(None)` removed are not failure statements",
          [H([G], DF(G, f"-    {x}", "+    pass")) for x in ("sys.exit(0)", "sys.exit()", "sys.exit(None)")], [[], [], []])
    check("...and a `raise` turned into a `print`",
          has(H([G], DF(G, "     if bad:", '-        raise ValueError("invalid input")', '+        print("invalid input")')),
              "failure path"), True)
    # backlog #354 (r11 HONEST): a TypeScript/JavaScript gate is gate code, and Node's exits are failure paths.
    TS = "scripts/check-service-confinement.ts"
    check("⭐ a `.ts` gate's `process.exit(1)` turned into `process.exit(0)` is a loosening (backlog #354)",
          has(H([TS], DF(TS, "   if (leaks.length) {", "-    process.exit(1);", "+    process.exit(0);")), "failure path"), True)
    check("...and so is an `.mjs` gate's `throw` turned into a `console.error`",
          has(H(["scripts/ts-comment-spans.mjs"], DF("scripts/ts-comment-spans.mjs", "   if (bad) {",
                "-    throw new Error('unterminated');", "+    console.error('unterminated');")), "failure path"), True)
    check("...and `process.exitCode = 1` dropped",
          has(H([TS], DF(TS, "   if (bad) {", "-    process.exitCode = 1;", "+    console.log('bad');")), "failure path"), True)
    check("...but `process.exit(0)`, `process.exit()` and `process.exitCode = 0` removed are not failure statements",
          [H([TS], DF(TS, f"-  {x}", "+  void 0;")) for x in ("process.exit(0);", "process.exit();", "process.exitCode = 0;")],
          [[], [], []])
    check("...but a Python gate's JS stub string holding `throw` is not a failure path (PR #397's shape)",
          H([G], DF(G, "  stub = \"if(!ok)throw new Error('stub');\"", "-  b = 40", "+  b = 43")), [])
    # backlog #354 r1 (both halves, executed): the Node patterns' own syntax, Node comments, and the npm call site.
    check("⭐ r1 CODEX H: `process.exit (1)` -> `process.exit (0)` — a space before the bracket — is a loosening",
          has(H([TS], DF(TS, "   if (bad) {", "-    process.exit (1);", "+    process.exit (0);")), "failure path"), True)
    check("r1 CODEX M: an edit beside `process.exitCode === 0` (a comparison, not an assignment) is not held",
          H([TS], DF(TS, "   if (process.exitCode === 0) {", '-    console.log("complete");', '+    console.log("done");', "   }")), [])
    check("...while `process.exitCode ||= 1` dropped is a loosening (r1 CLAUDE L2)",
          has(H([TS], DF(TS, "   if (bad) {", "-    process.exitCode ||= 1;", "+    console.log('bad');")), "failure path"), True)
    # ⛔ A STATED BOUND (backlog #356, split off at r2): the npm call site of a TypeScript gate is not guarded.
    check("BOUND (stated, backlog #356): `run: npm run check:confinement` dropped from a workflow is NOT held",
          H([".github/workflows/ci.yml"], DF(".github/workflows/ci.yml", "       - run: npm ci",
            "-      - run: npm run check:confinement")), [])
    # ⛔ A STATED BOUND (r1 CLAUDE M1): a failure block wrapped in `/* */` ADDS lines and removes none, so the
    # removal rule cannot see it — the same class as Python's `if False:` around a `return 1`. Review catches it.
    check("BOUND (stated, backlog #354 r1): a Node failure block wrapped in `/* */` is NOT held",
          H([TS], DF(TS, "+  /*", "   if (bad) {", "     process.exit(1);", "   }", "+  */")), [])
    check("...and a `.ts` file OUTSIDE scripts/ is not gate code", H(["tests/lib/x.ts"], DF("tests/lib/x.ts",
          "   if (bad) {", "-    process.exit(1);", "+    process.exit(0);")), [])
    # ⛔ A STATED BOUND, asserted so it cannot be forgotten (owner, r8 card A): a SEMANTIC loosening — a
    # condition removed far above the loop that fails on it — leaves no failure-path text within the
    # window. If this case ever goes RED, the bound has closed: update the comment above GATE_CODE.
    check("BOUND (stated, r8): a condition removed 7 lines above its failure line is NOT held",
          H([G], DF(G, "     checks = [", "-        False,", "         True,", "     ]", "     x = 1", "     y = 2",
                    "     z = 3", "     for c in checks:", "         if not c:", "             return 1")), [])
    # r1 CLAUDE M2: a pin deleted, or renamed away, is a drop to nothing.
    check("a mutation pin DELETED is a loosening",
          has(H([PC], DF(PC, '-    "scripts/a.py": 30,')), "scripts/a.py (30) is removed"), True)
    check("...and so is one renamed to another key",
          has(H([PC], DF(PC, '-    "scripts/b.py": 12,', '+    "scripts/c.py": 12,')), "scripts/b.py (12) is removed"), True)
    for mig in ("supabase/migrations/0028_x.sql", "supabase/migrations/0099_y.sql"):
        r = H([mig], at="abc")
        check(f"a migration needs a deploy first ({mig[-10:]})", has(r, "deploy first"), True)
    check("...and a migration is app code too, so it also needs the local tests",
          has(H(["supabase/migrations/0028_x.sql"]), "app code changed"), True)
    check("a NO-REVIEW waiver is held", has(H(nr=True), "NO-REVIEW"), True)
    for f in ("lib/gemini.ts", "app/page.tsx"):
        check(f"app code with no local test run is held ({f})", has(H([f], at=None), "app code changed"), True)
        check(f"...and is cleared by a run pinned to THIS head ({f})", H([f], at="abc"), [])
    check("...but NOT by a run at a DIFFERENT head", has(H(["lib/x.ts"], at="old"), "app code changed"), True)
    check("...nor when the head is unknown", has(H(["lib/x.ts"], head=None, at=None), "app code changed"), True)
    check("HOLD applies only to a READY PR", final_verdict(0, "READY", ["x"])[0], HOLD_RC)
    check("...the held verdict names the reason", "x" in final_verdict(0, "READY", ["x"])[1], True)
    check("...NOT READY wins over a hold", final_verdict(1, "NOT READY", ["x"])[0], 1)
    check("...CANNOT RUN wins over a hold", final_verdict(2, "CANNOT RUN", ["x"])[0], 2)
    check("...and no hold leaves READY as READY", final_verdict(0, "READY", []), (0, "READY"))

    # ⛔ THE CALL SITE, not only the rules — unit coverage does not compose. `main()` is driven
    # end to end over a FAKE `_run`, so deleting the wiring reddens these even with every pure
    # case above still green. Two distinct holds, one clean PR, and one cleared app-code PR.
    import contextlib, io
    _real_run = globals()["_run"]
    _tmp = Path(tempfile.mkdtemp()) / "body.md"
    def _fake(files, diff, body="", status=None, tree=""):
        # The machine list defaults to one `M` per file; `diff` is every file's patch (no hunks
        # unless a case gives some), since each file's patch is asked for separately.
        if status is None:
            status = "".join(f"M\0{f}\0" for f in files)
        def run(cmd, **kw):
            def cp(out="", rc=0):
                return subprocess.CompletedProcess(cmd, rc, out, "")
            if cmd[0] == "mktemp":
                return cp(str(_tmp))
            if cmd[:3] == ["gh", "pr", "view"] and "body" in cmd:
                return cp(body)
            if cmd[:3] == ["gh", "pr", "view"]:
                return cp(json.dumps({"state": "OPEN", "isDraft": False, "baseRefName": "master",
                                      "headRefOid": "abc", "mergeStateStatus": "CLEAN"}))
            if cmd[:3] == ["gh", "pr", "checks"]:
                return cp(json.dumps([{"name": "verify", "bucket": "pass"}]))
            if cmd[:2] == ["git", "rev-parse"]:
                return cp("abc\n")
            if cmd[:3] == ["git", "--literal-pathspecs", "diff"] and "--name-status" in cmd:
                return cp(status)
            if cmd[:2] == ["git", "merge-base"]:
                return cp("mb\n")
            if cmd[:2] == ["git", "ls-tree"]:
                return cp(tree)                     # no blobs unless a case gives some
            if cmd[:2] == ["git", "diff"]:
                return cp(diff)
            return cp("ok\n")                       # the three gate scripts
        return run
    def _main(files, pr, tests_at=None, diff="", body="", status=None, tree=""):
        globals()["_run"] = _fake(files, diff, body, status, tree)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                if tests_at is None:
                    rc = main(["--pr", pr])
                else:
                    rc = main(["--pr", pr, "--app-tests-passed", tests_at])
        finally:
            globals()["_run"] = _real_run
        return rc, buf.getvalue()
    _rc, _o = _main(["docs/reviews/decision-scheme/baseline.json"], "1")
    check("⭐ main() HOLDS a READY PR that edits a pinned baseline, rc=3, naming why",
          (_rc, "HOLD — ready by every gate" in _o, "pinned baseline" in _o), (3, True, True))
    _rc, _o = _main(["docs/x.md"], "7", body="intro\nNO-REVIEW: docs only\n")
    check("⭐ main() HOLDS a READY PR whose body declares NO-REVIEW:, rc=3",
          (_rc, "NO-REVIEW" in _o), (3, True))
    _rc, _o = _main(["docs/x.md"], "12")
    check("main() leaves a clean READY PR as READY, rc=0", (_rc, "HOLD" in _o), (0, False))
    # #353: the MACHINE list decides paths. The header says `docs/g.yml` both sides; the list says a
    # workflow was renamed there — so only a main() that reads the list holds it.
    _rc, _o = _main(["docs/g.yml"], "21", status="R100\0.github/workflows/g.yml\0docs/g.yml\0")
    check("⭐ main() takes paths from --name-status, not the patch header (a rename only the list shows)",
          (_rc, "g.yml is renamed to docs/g.yml" in _o), (3, True))
    _rc, _o = _main(["docs/h.md"], "22", status="R100\0docs/h.md\0")
    check("...and REFUSES (CANNOT RUN) on a machine list it cannot read",
          (_rc, "CANNOT RUN" in _o), (2, True))
    # r10: ANY collection error is CANNOT RUN — a malformed `ls-tree` reply raises ValueError, not
    # PathsDisagree. The case catches a crash itself so a narrowed handler shows as a RED case.
    try:
        _rc, _o = _main(["scripts/x.py"], "23", status="M\0scripts/x.py\0", tree="garbage-without-a-tab\0")
        _crash = None
    except Exception as exc:
        _rc, _o, _crash = None, "", exc.__class__.__name__
    check("⭐ main() turns an UNEXPECTED collection error into CANNOT RUN, rc=2 (never a crash)",
          (_rc, "CANNOT RUN" in _o, _crash), (2, True, None))
    # r1 CLAUDE M3: the pure NO-ENTRY case never passed its body anywhere — this one does.
    _rc, _o = _main(["docs/y.md"], "9", body="intro\nNO-ENTRY: docs only\n")
    check("⭐ main() does NOT hold a PR whose body declares only NO-ENTRY: (owner: NO-REVIEW only)",
          (_rc, "HOLD" in _o), (0, False))
    _rc, _o = _main(["lib/x.ts"], "3", "abc")
    check("main() clears app code with a local test run pinned to the head, rc=0",
          (_rc, "HOLD" in _o), (0, False))

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))

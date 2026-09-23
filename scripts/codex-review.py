#!/usr/bin/env python3
"""Dispatch a Codex adversarial review that FAILS LOUDLY instead of silently no-opping.

WHY THIS EXISTS
---------------
The adversarial review is a quality gate (docs/dev-process.md). A gate that can pass without
running is worse than no gate, because it manufactures false confidence. Two ways that happened:

1. `scripts/codex-frontier-model.py` ranks by the cache's `priority`, but the cache carries no
   minimum-client-version field, so it can return a model the pinned Codex CLI rejects. On
   2026-07-18 — still reproducible 2026-07-19 — it returns `gpt-5.6-sol`, and the run dies with
   HTTP 400 "requires a newer version of Codex", producing a review FILE containing only an error.
2. `docs/plugins.md` records those runs as exiting 0, so callers checking only the exit code
   treated them as clean reviews. (Measured 2026-07-19: a direct `codex exec` exits **1**. The
   exit-0 report comes from the plugin's background-task path, not the CLI. Since the two sources
   disagree, this wrapper treats the exit code as advisory and never as proof of success.)

HOW SUCCESS IS DETERMINED — read this before changing anything
--------------------------------------------------------------
Via `codex exec -o/--output-last-message <FILE>`, which writes ONLY the agent's final message.
Success is "that file exists and holds substantive content". Nothing else counts.

This replaced an earlier version that parsed stdout, and the replacement was not a refactor — it
was a retreat from an unwinnable problem. Adversarial review of that version
(docs/reviews/codex-dispatch-wrapper-codex{,-v2}.md) found hole after hole, all ONE shape:
`codex exec` multiplexes CLI banner, the echoed prompt, the tool-call transcript, and the final
reply onto a single stdout stream with unanchored text markers. So:
  - a prompt quoting a bare `codex` line was misparsed as the reply marker;
  - a prompt containing `tokens used` spoofed the completion check;
  - a review that QUOTED an error was indistinguishable from a run that HIT one;
  - the extracted "review" grew to 308 KB because it swallowed the whole tool transcript.
Every regex fix created a mirror bug on another channel. `-o` removes the ambiguity structurally:
the final message arrives on its own channel and nothing else can be mistaken for it.

Verified 2026-07-19 on both paths: success → file written with exactly the reply; unsupported model
→ file NOT created at all.

stdout is still captured, but ONLY to EXPLAIN a failure in the log. It cannot change what the
wrapper does — every failure path falls through to the next candidate, and any run where no
candidate yields a message ends in a loud non-zero exit.

Usage:
  scripts/codex-review.py --out docs/reviews/task-N-foo-codex.md "<review prompt>"
  scripts/codex-review.py --out <file> --prompt-file <file> [--timeout 900] [--model <slug>]
  scripts/codex-review.py --self-test  # 115 cases

Exit codes:  0 = a real review was written   |   1 = no candidate produced one (gate did NOT run)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import importlib.util
import sys
import tempfile
from importlib import import_module

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_frontier = import_module("codex-frontier-model")
resolve_candidates = _frontier.resolve_candidates

# Minimum characters in the final message below which we refuse to call it a review. Even a terse
# "no findings" verdict clears this comfortably; an empty or stub message does not.
MIN_REVIEW_CHARS = 200

# Structured HTTP status from the CLI's own `ERROR: {...}` diagnostic. Advisory only (see above).
ERROR_LINE = re.compile(r'^ERROR:\s*\{.*"status"\s*:\s*(\d+)', re.MULTILINE)

# Statuses that usually mean an account-wide fault rather than a model-specific one. Used ONLY to
# annotate the log line so the operator knows a Claude fallback is likely needed; it does not stop
# the loop (see classify()).
ACCOUNT_FAULT_STATUSES = {401, 403, 429}

# Auth failures the CLI prints as prose rather than a JSON ERROR line. Narrow on purpose: matched
# against stdout, which includes the echoed prompt, and a review prompt legitimately discusses rate
# limits and 401s. Diagnostic only — it cannot pass a bad review and no longer ends the loop early.
AUTH_PROSE = re.compile(r"usage limit|not logged in|please (?:re-?)?login|authentication failed",
                        re.IGNORECASE)


class Outcome:
    OK = "ok"                    # a real review — accept
    TRY_NEXT = "try_next"        # anything else — fall through to the next candidate
    # NOTE: there is deliberately no ABORT. See the comment in classify() — an early-abort branch
    # gave text in the echoed prompt a way to steer control flow, which round 3 and round 4 each
    # exploited through a different matcher.



def _names_own_output(body: str, out_path: str) -> bool:
    """Does the final message refer to the file it is about to be written to? PURE.

    Matched on the BASENAME, because the agent may print an absolute path, a repo-relative path or a
    markdown link. A genuine review has no reason to name its own destination — it does not know it.
    """
    base = os.path.basename(out_path)
    return bool(base) and base in body


# ── backlog #68: a failed gate must not be able to leave an artifact ────────────────────────────
# MEASURED 2026-08-28/29, round 3 of the project-dashboard plan review. The wrapper passes codex
# only `-o <tempfile>`; the real `--out` is never given to the agent. The brief said "write to the
# review path you were given" — which named nothing — so the agent INFERRED
# `docs/reviews/plan-project-dashboard-r3-codex.md` from the prior-round filenames listed in the
# brief, and under `-s danger-full-access` wrote there. Over a COMMITTED artifact. Four models were
# tried, each overwriting the last, and the file's verdict flipped from NO to YES between one read
# and the next. THE WRAPPER WROTE NOTHING AT ANY POINT — every version on disk came from the
# agents' own writes, which is precisely why "we only write on success" was not protection.
#
# The wrapper cannot stop an agent writing where it likes. It CAN refuse to be the thing that
# silently loses a filed review, and it can SEE the writes and say so.

def prompt_demands_a_file(text: str) -> "str | None":
    """The phrase telling the agent to WRITE a file, or None. PURE.

    This is the one input that guarantees a rejected capture: the wrapper decides success solely by
    whether the final message IS the review, so a brief that tells the agent to write a file makes
    the final message a *report of having written one* — which `_names_own_output` then correctly
    rejects. Round 3 used one shared brief for both halves; correct for the Claude subagent, which
    writes files, fatal for Codex. Round 2's brief, same wrapper and same model ladder, never
    mentions writing anything and captured cleanly. ONE SENTENCE was the entire difference.

    Deliberately narrow. It matches an instruction aimed at the agent about *the review*, not any
    mention of writing — a review prompt discussing a script that writes files must not trip it.

    ⟳ WIDENED 2026-09-04 (task #222), because it MISSED a live breach. Round 4 used one brief for
    both halves again and this guard stayed silent: it only knew the IMPERATIVE word order.
    Measured against the round-4 text, before the fix:

        write the review to docs/reviews/x.md                     -> FIRED
        Write your findings to the file below                     -> FIRED
        except for the one review file you are asked to write     -> MISSED  <- the actual breach
        save the review at this path                              -> MISSED
        your review should be written to disk                     -> MISSED

    The three added forms are a RELATIVE CLAUSE, `at` as the preposition, and the PASSIVE. The
    passive one is deliberately anchored on `your` — an unanchored `report will be written` fires
    on a brief describing the code under review, which is the false positive the docstring above
    forbids, and a warning people learn to ignore protects nothing.
    """
    patterns = (
        r"write\s+(?:the|your|it|this)\s+(?:review|findings|report|output)\s+to\b",
        r"write\s+to\s+the\s+(?:review|output)\s+path\b",
        # `at` added: "save the review at this path" reads as a location, not a destination.
        r"save\s+(?:the|your)\s+(?:review|findings|report)\s+(?:to|as|in|at)\b",
        r"(?:create|produce)\s+(?:a|the)\s+file\s+at\b",
        r"output\s+file\s*[:=]",
        # Relative clause. THE ROUND-4 BREACH: a prohibition that carves out one permitted write
        # ("you must not write any files, except for the one review file you are asked to write")
        # still instructs a write, and the capture is rejected exactly the same way.
        r"file\s+you\s+(?:are\s+)?(?:asked|told|expected|supposed)\s+to\s+write\b",
        # Passive, anchored on `your` so it cannot reach the code being reviewed.
        r"your\s+(?:review|findings|report|output)\s+(?:should|must|needs?\s+to|is\s+to)\s+be\s+"
        r"(?:written|saved|placed|put)\b",
    )
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            if not _is_negated(text, m.start()):
                return m.group(0)
    return None


# ⚠ NEGATION, found 2026-09-04 while WRITING a corrected brief with this very guard.
# "do not write your review to a file" matched `write your review to` and the guard refused the
# run — a FALSE POSITIVE on the one wording that gets the contract right. It predates the #222
# widening (pattern 1 is original); the existing prohibition case used "write no file", which has
# no `write ... to`, so nothing covered the negated form.
#
# Fail-closed, so it was never unsafe — but it made the CORRECT brief unusable, which is worse
# than useless for a guard whose whole job is to let a correct brief through.
#
# The window is deliberately short. A negator sentences away is not negating this clause, and a
# long window would let "never" in an unrelated sentence silently disarm a real demand.
_NEGATORS = re.compile(r"\b(?:do\s+not|don't|never|must\s+not|should\s+not|cannot|can't|no\s+need\s+to|"
                       r"without|refrain\s+from|avoid)\b[^.!?\n]{0,40}$", re.I)


def _is_negated(text: str, start: int) -> bool:
    """True when a negator governs the match starting at `start`. PURE.

    Looks back at most 60 characters AND never across a sentence boundary — `[^.!?\\n]` in the
    pattern is what stops a previous sentence's "do not" from reaching forward.
    """
    return bool(_NEGATORS.search(text[max(0, start - 60):start]))


def _digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ── backlog #68 (d): THE VERDICT IS WRITTEN DOWN, BECAUSE THE EXIT CODE CAN BE THROWN AWAY ──
#
# The exit code is a channel with exactly one consumer and no memory. Measured 2026-08-28: the call
# was wrapped as `python3 scripts/codex-review.py … ; echo "WRAPPER_RC=$?"`, so the reported status
# was the ECHO's. `WRAPPER_RC=1` sat unread in a log while the run was treated as successful and the
# round's Codex half never ran. That is the `$?`-after-the-wrong-command trap, measured a FOURTH
# time in this repo.
#
# ⚠ THE OBVIOUS FIX IS NOT ENOUGH, AND SAYING SO IS THE POINT. "Write a file the caller must read"
# only moves the problem if the CALLER is still the reader — a file ignored is an exit code ignored
# with extra steps. So the verdict lands INSIDE the repository, where `check-review-rounds.py`
# reads it in CI. The consumer is deliberately NOT the caller.
#
# It is a subdirectory of `docs/reviews/` on purpose: `dir_snapshot` is non-recursive, so the
# wrapper's own verdict writes cannot register as agent intrusions into the artifact root.
VERDICT_DIR = os.path.join("docs", "reviews", "verdicts")
# ⟳ 2 (2026-09-13): `head` and `dirty`. The verdict could say the gate RAN and not what it ran
# AGAINST, so nothing downstream could tell a review of the tree that will merge from a review of
# the tree as it stood before three fixes landed. `check-review-recorded.py` reads both.
VERDICT_SCHEMA = 2


def run_token(head: "str | None", prompt_text: str) -> str:
    """A short, deterministic name for THIS run. PURE — no clock, no filesystem, no git call.

    ⭐ **THIS IS THE ALLOCATOR, AND ITS ABSENCE WAS r4 H1.** `c3ad7727` was titled *"the verdict
    path had no allocator"* and then did not add one: it REFUSED one collision shape (a derived
    path that is already tracked) and left the namespace unallocated. Measured in round 4 — the
    call shape `docs/plugins.md` documents as PREFERRED,

        --out "$(mktemp -d)/r.md"

    reduces to the basename `r` for every caller, so every review in the repo derived
    `docs/reviews/verdicts/r.verdict.json`. That file is not tracked, so the new refusal passed it,
    and run B destroyed run A's testimony exactly as before. The fix that was shipped protected
    against the instance that had already happened and not against the path everyone is told to use.

    ⚠ **PURE ON PURPOSE, AND THAT IS WHY IT TAKES `head` RATHER THAN ASKING GIT.** The two
    alternatives considered both fuse the rule to a fetch: scanning `VERDICT_DIR` for a free `-NN`
    suffix needs the filesystem (and races), and reading HEAD here needs git. This repo has paid for
    that fusion — it is why `verdict_collision` takes `tracked` as an argument and `path_is_tracked`
    does the asking. The caller gathers `head` from `reviewed_state()`, which it already calls.

    **What the identity is, stated so a reader can predict it:** the same HEAD and the same prompt
    text yield the SAME token. That is deliberate — re-running one review is the same run and should
    land on its own testimony rather than accumulating debris. Two DIFFERENT reviews, which is the
    H1 scenario, differ in prompt text and so cannot collide however `--out` is named. A review of a
    different commit differs in HEAD, which is the r3 incident that cost a restore.

    ⚠ `head is None` (git could not answer) does not make two runs the same run: the prompt still
    separates them. It is folded in as a literal rather than dropped so the token is always defined.
    """
    h = hashlib.sha256()
    h.update((head or "no-head").encode("utf-8"))
    h.update(b"\x00")
    h.update(prompt_text.encode("utf-8"))
    return h.hexdigest()[:8]


def verdict_path(out_path: str, override: "str | None" = None,
                 run_id: "str | None" = None) -> str:
    """Where this run's testimony goes. PURE.

    Defaults into the repo — not next to `--out`, which the documented safe call shape puts
    OUTSIDE the repo precisely so a stray write cannot reach an artifact. A verdict written there
    would be invisible to CI, which is the whole failure being fixed.

    `run_id` is what makes the namespace ALLOCATED rather than merely guarded — see `run_token`.
    It is optional so the function stays usable (and testable) without one, but `main` always
    passes it; a caller that omits it gets the old, collision-prone naming and that is why the
    refusal below survives as a fallback rather than being deleted.
    """
    if override:
        return os.path.abspath(override)
    stem = os.path.basename(out_path)
    for ext in (".md", ".markdown", ".txt"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    stem = stem or "review"
    if run_id:
        stem = f"{stem}.{run_id}"
    return os.path.join(REPO_ROOT, VERDICT_DIR, f"{stem}.verdict.json")


def refusal_verdict_path(vpath: str) -> str:
    """Where a REFUSED dispatch leaves its testimony. PURE, and it must not be `vpath`.

    r4 M5: the collision refusal was the one exit that wrote no verdict, so its only channel was the
    caller's exit code — the channel this file's own header calls unreliable, and which this repo has
    recorded an agent ignoring four times. Downstream, a refused run and a run that never happened
    were indistinguishable, which is precisely the property the verdict mechanism exists to abolish.

    The comment it replaces framed that as forced (write to `vpath` and destroy the thing being
    protected, or write nothing). It was not forced: the refusal can testify under a name derived
    from `vpath` that is not `vpath`. `check-review-rounds.read_verdicts` globs `*.json` and needs
    only a `gate_ran` field, so this needs no grammar change downstream.
    """
    base = vpath[: -len(".verdict.json")] if vpath.endswith(".verdict.json") else vpath
    return f"{base}.refused.verdict.json"


def verdict_collision(vpath: str, *, tracked: "bool | None", override_given: bool) -> "str | None":
    """Would writing here destroy COMMITTED testimony about a different run? -> refusal, or None.

    PURE — `tracked` is passed in, because the git query is the caller's to make. This repo has paid
    for fusing a rule to its fetch: it makes the rule untestable without the world the fetch needs.

    ⛔ **THIRD MEASURED INSTANCE, 2026-09-23.** `verdict_path` DERIVES this name from `--out`'s
    basename, so the namespace has no allocator: any two reviews that pick the same output name write
    the same verdict. A round-3 review dispatched with `--out codex-r3.md` overwrote a COMMITTED
    `codex-r3.verdict.json` belonging to a different review from an earlier session — 6,677 chars the
    first time this happened, and both files honestly reported `"review": "codex-r3.md"`, so the stem
    cannot distinguish them. `check-review-recorded.py` catches a MISSING verdict (the file shows as
    MODIFIED, not ADDED, so it sees nothing) and **nothing catches an overwrite.**

    ⭐ **IT REFUSES THE ACCIDENT AND ALLOWS THE DELIBERATE ACT, which is the whole design.** A
    DERIVED path that is already tracked is a refusal: the caller never chose it, so the destruction
    is a side effect of naming an output file. An EXPLICIT `--verdict` is allowed through, because
    replacing committed testimony on purpose is a decision someone made and can be seen making in the
    command line. A blanket refusal would break the legitimate re-run, and a blanket allow is the
    status quo that has now failed three times.

    ⚠ `tracked=None` means the git query could not be answered, and that is a REFUSAL, not a pass.
    Proceeding would clobber on exactly the machines where nobody can tell afterwards.
    """
    if override_given:
        return None
    if tracked is None:
        return (f"CANNOT RUN — could not ask git whether {vpath} is already tracked, so this run "
                f"cannot tell a fresh verdict path from one holding committed testimony. Pass "
                f"--verdict <path> to choose deliberately. TREAT THIS AS NOT RUN.")
    if tracked:
        return (f"REFUSED — the verdict path derived from --out is already TRACKED: {vpath}\n"
                f"  It holds committed testimony, and writing over it would destroy evidence that\n"
                f"  a different run's gate ran. Nothing in this repo detects that overwrite: the\n"
                f"  file shows as MODIFIED rather than ADDED, so check-review-recorded sees a\n"
                f"  verdict present and is satisfied. THIRD measured instance.\n"
                f"  Fix: give --out a name unique to this review — the convention is\n"
                f"  <subject>-r<N>-codex.md, which yields <subject>-r<N>-codex.verdict.json — or\n"
                f"  pass --verdict <path> to replace that testimony deliberately.\n"
                f"  ⚠ --allow-overwrite does NOT authorise this: it governs the review artifact\n"
                f"  (--out) only. Two artifacts, two deliberate acts, neither implying the other.")
    return None


def build_probe_repo(repo_dir: str, git: str = "git") -> bool:
    """Build a throwaway git repository holding one TRACKED file. -> did it work?

    ⚠ **`git` IS A PARAMETER FOR ONE REASON: without it, the failure branch is unreachable from a
    case (r4 M2).** `7840a3be` claimed "a case asserting the repository was really built, so an
    environment without git fails loudly instead of reporting three passes". Measured in round 4:
    `subprocess.run` does not return a code when the executable is missing — it RAISES — so with git
    genuinely absent the suite died with `FileNotFoundError` before that case ran. The loudness was
    real, but it came from a traceback rather than the named mechanism, and the `False` branch it
    guarded required git to be PRESENT and `init`/`config`/`add` to fail, which nothing drives.

    A traceback is not a case: it names nothing, the mutation harness cannot attribute a kill to it,
    and this repo files that shape as *a suite that dies by crashing is a suite whose kill nobody can
    attribute*. Taking the executable's name lets a case hand it one that does not exist.
    """
    try:
        for cmd in (["init", "-q"], ["config", "user.email", "t@example.invalid"],
                    ["config", "user.name", "t"]):
            if subprocess.run([git, "-C", repo_dir] + cmd, capture_output=True).returncode != 0:
                return False
        with open(os.path.join(repo_dir, "tracked.txt"), "w", encoding="utf-8") as f:
            f.write("committed\n")
        return subprocess.run([git, "-C", repo_dir, "add", "tracked.txt"],
                              capture_output=True).returncode == 0
    except OSError:
        return False


def path_is_tracked(path: str, repo_root: "str | None" = None) -> "bool | None":
    """Is this path tracked by git? -> True / False / None when the question cannot be answered.

    ⚠ **None IS NOT False.** Returning False on a failed `git` call would be a fail-open handler in
    front of a rule whose entire job is to refuse — `check-ratchet-contract.py` exists to catch that
    shape, and the rule above turns None into a CANNOT RUN rather than a shrug.

    ⚠ **`repo_root` IS A PARAMETER BECAUSE THE FIRST VERSION'S CASES PASSED FOR AN AMBIENT REASON,
    and the mutation harness caught it by REFUSING.** They asserted True for a real tracked file and
    False for an absent one — both true only while the suite ran inside this git checkout. The
    harness stages a `copytree` of the tree with NO `.git`, so there `git` exits 128, this returns
    None for both, and the CONTROL went red at 100/102 before any mutation was applied: *every
    verdict below would be an artefact. Treat this as NOT CHECKED.* The suite now BUILDS a throwaway
    repository and drives all three outcomes inside it, so the answers come from a world the case
    made rather than one it happened to be standing in.
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    try:
        rel = os.path.relpath(path, root)
        r = subprocess.run(["git", "-C", root, "ls-files", "--error-unmatch", "--", rel],
                           capture_output=True, text=True)
    except (OSError, ValueError):
        return None
    if r.returncode == 0:
        return True
    # git distinguishes "not tracked" (1) from a broken invocation (128: not a repo, bad option).
    if r.returncode == 1:
        return False
    return None


def verdict_record(*, gate_ran: bool, exit_code: int, out_path: str, reason: str,
                   model: "str | None" = None, attempts: "list[str] | None" = None,
                   intrusions_seen: "list[str] | None" = None,
                   head: "str | None" = None, dirty: "dict[str, str] | None" = None,
                   prompt: "str | None" = None) -> dict:
    """The testimony, as data. PURE — no clock, no filesystem, so a case can assert every field.

    `gate_ran` is the load-bearing field and is stated SEPARATELY from `exit_code`, not derived
    from it by the reader. A reader that re-derives the verdict from a number is a second
    implementation of the rule, and this project has measured what those do.

    `head` and `dirty` describe WHAT was reviewed; `reviewed_state` below gathers them. `head` is
    always present, `None` when it could not be established — an absent field and a null one read
    the same to a downstream `.get()`, but only the null one distinguishes "no answer" from "old
    schema" when a human opens the file.

    ⛔ `dirty is None` AND `dirty == {}` ARE DIFFERENT ANSWERS, and `dict(dirty or {})` erased the
    difference — r11 Medium. `None` means the wrapper could not describe the tree; `{}` means it
    looked and the tree was clean. Collapsing them made a failed measurement read as a clean tree,
    which is how the gate came to accuse the author who held their fixes back.

    `prompt` is the r11 High that no mechanism can close, recorded rather than hidden: the entries
    in `dirty` are the whole working tree (`add -A`, no pathspec), so they say what was IN the tree
    at dispatch, not what the round's prompt covered. A guarded file merely dirty at dispatch is
    credited by every reviewer dispatched against that tree. The wrapper cannot know what a reviewer
    READ — no representation can — so the honest move is to record the prompt the run was dispatched
    with and let a human see the scope those entries were taken under.
    """
    return {
        "schema": VERDICT_SCHEMA,
        "tool": "codex-review",
        "gate_ran": bool(gate_ran),
        "exit_code": int(exit_code),
        "review": os.path.basename(out_path),
        "model": model,
        "reason": reason,
        "attempts": list(attempts or []),
        "intrusions": list(intrusions_seen or []),
        "head": head,
        "dirty": None if dirty is None else dict(dirty),
        "prompt": prompt,
    }


REDIRECT_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")


def unredirected(env: "dict[str, str] | None" = None) -> dict:
    """PURE given `env`. The environment with git's REPOSITORY-REDIRECTION variables removed.

    ⛔ `git -C <root>` DOES NOT MEAN "the repository at root" — r11 High, and this one was
    demonstrated rather than argued. With `GIT_DIR` exported, `reviewed_state` describes a
    DIFFERENT repository: measured, it returned the other repo's HEAD and fabricated a deletion of
    a file nobody deleted — and an all-zero entry is the one shape the consumer's `is_absent`
    credits without an equality check.

    ⚠ IT IS NOT HYPOTHETICAL AND THAT IS THE POINT. r10 closed the same class for config FILES
    (`GIT_CONFIG_GLOBAL`/`_SYSTEM`/`NOSYSTEM`) and left the env-var door open; during r11 a reviewer
    probing exactly that ran this file's own `--self-test` under an exported `GIT_DIR` aimed at the
    live worktree, and the FIXTURE's `git commit` moved a real branch ref off its pushed merge
    commit onto a scratch fixture commit. Recoverable, and recovered — but the hole was open in the
    fixture as well as in the subject, which is why both call sites use this.

    `GIT_INDEX_FILE` is deliberately NOT stripped: `reviewed_state` sets it on purpose, to a
    throwaway index, and stripping it here would fight its own caller. `GIT_CONFIG_*` is likewise
    left alone in the SUBJECT — r11 measured that `reviewed_state` records exactly what a real
    commit stores under a host clean filter, so neutralising config there would be the defect.
    """
    out = dict(os.environ if env is None else env)
    for var in REDIRECT_VARS:
        out.pop(var, None)
    return out


def reviewed_state(repo_root: "str | None" = None) -> "tuple[str | None, dict[str, str] | None]":
    """`(HEAD commit, {uncommitted path: "<mode> <object-id>" the reviewer was handed})`. IMPURE.

    WHY BOTH, and the second one is not decoration. `head` alone answers the question for a clean
    tree. But the documented practice is to hold a round's fixes UNCOMMITTED so the reviewer sees
    the state that will actually merge — measured on backlog #296, where exactly that was done on
    purpose. Under that practice `head` is the commit BEFORE the reviewed fixes, and a downstream
    check reading it alone would accuse the careful author of shipping unreviewed code.

    ⛔ THE TREE ENTRY, NOT THE PATH, AND NOT THE CONTENT ALONE. Two review rounds on this function:
    r1 found that a list of dirty PATHS let "review `lib/x.py` at v2, edit it to v3, commit" pass,
    because the name still matched — the ordinary fix-it-again loop, not an exotic evasion. r2 then
    found that content alone let a MODE-ONLY change through: same bytes, newly executable, credited
    as reviewed. What the reviewer saw is the tree ENTRY — mode and object id — so that is what is
    recorded, and `git` is asked for it rather than reconstructing it here.

    ⚠ NEVER RAISES, and never blocks the review. A wrapper that cannot describe the tree still has
    a gate to run and testimony to file.

    ⛔ THE COST OF FAILING IS STATED IN TWO PLACES, AND IT USED TO BE WRONG IN THREE — r11 Medium,
    found independently by two review lenses. The docstring said a failure costs a `None` head; only
    `rev-parse` honoured that. The other three exits returned a REAL head with an EMPTY map, which
    is byte-identical to a round dispatched against a genuinely clean tree — so a FAILED measurement
    read downstream as "nothing was uncommitted", and the gate then accused the author who had done
    the documented careful thing of shipping unreviewed code. A false accusation indistinguishable
    from a true one. `CLAUDE.md`: a check that cannot reach what it measures must say so.

    So the second element is now `None` — not `{}` — whenever the tree could not be described, and
    `check-review-recorded.classify_verdict` counts a null `dirty` as UNUSABLE, which routes to
    CANNOT RUN rather than to a pass. `{}` keeps its real meaning: the tree WAS clean.
    """
    root = repo_root or REPO_ROOT

    def git(*args: str, env: "dict[str, str] | None" = None) -> "str | None":
        try:
            p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                               timeout=60, env=unredirected(env))
        except (OSError, subprocess.SubprocessError):
            return None
        return p.stdout if p.returncode == 0 else None

    head = git("rev-parse", "HEAD")
    if head is None:
        return None, None
    # ⛔ ASK GIT WHAT IT WOULD STORE — do not compute it. r2 broke three attempts at doing this by
    # hand: `git diff --name-only` + `hash-object` recorded a symlink as the hash of its TARGET's
    # contents (git stores the link text), omitted untracked files entirely (a new file present at
    # review time then read as never-seen), and carried no MODE, so flipping the executable bit
    # after the round was credited as reviewed — the r1 Blocking in another costume.
    #
    # A throwaway index answers all three at once, in git's own words: `read-tree HEAD` then
    # `add -A` produces exactly the entries a commit would hold, and `diff-index` names the ones
    # that differ from HEAD. `GIT_INDEX_FILE` keeps it out of the real index, which a concurrent
    # agent's `git add` would otherwise collide with (docs/review-method.md, hazard 2).
    dirty: "dict[str, str]" = {}
    try:
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, GIT_INDEX_FILE=os.path.join(td, "index"))
            if git("read-tree", "HEAD", env=env) is None:
                return head.strip(), None
            # ⚠ BEST EFFORT, NOT ALL-OR-NOTHING — r3 Medium. `add -A` fails on an out-of-cone
            # untracked path under a sparse checkout, and returning {} there discarded the entries
            # it HAD staged: one unrelated file turned a full record into no record, and every
            # reviewed file then read as never-seen. A partial record fails CLOSED (unrecorded
            # paths count as unseen); an empty one throws away evidence that exists.
            git("add", "-A", env=env)
            raw = git("diff-index", "--cached", "-z", "--no-renames", "HEAD", env=env)
    except OSError:
        return head.strip(), None
    if raw is None:
        return head.strip(), None
    # Raw `-z` records are `:<srcmode> <dstmode> <srcsha> <dstsha> <status>\0<path>\0`.
    fields = raw.split("\0")
    for i in range(0, len(fields) - 1, 2):
        meta, path = fields[i], fields[i + 1]
        if not meta.startswith(":") or not path:
            continue
        parts = meta[1:].split()
        if len(parts) < 5:
            continue
        # ⚠ A DELETION IS RECORDED, NOT SKIPPED — r3 Medium. The first version dropped all-zero
        # destinations as "no content to credit", so a reviewer who saw a file DELETED left no
        # trace of it and the branch was accused of merging an unreviewed deletion. Absence is a
        # tree state. The zero entry git itself writes here says exactly that, so nothing is
        # invented: the check compares against the same zeros for a path absent from HEAD.
        dirty[path] = f"{parts[1]} {parts[3]}"
    return head.strip(), dirty


def write_verdict(path: str, record: dict) -> "str | None":
    """Write the testimony. Returns an error string, or None on success.

    ⚠ A FAILURE HERE IS A CANNOT-RUN, not a warning. If the verdict cannot be written then nothing
    outside this process can later establish whether the gate ran — which is the exact condition
    this mechanism exists to abolish. The caller turns this into exit 2.
    """
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write("\n")
        return None
    except OSError as exc:
        return f"{exc}"


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The directories an agent has actually been observed to guess its way into. `docs/reviews/` is
# NOT optional and is NOT derived from `--out`:
#
# ⚠ MEASURED ON THIS BRANCH, 2026-09-01, while verifying this very fix. A test run with
# `--out <tempdir>/exists.md` ended with a real adversarial review at
# `docs/reviews/codex-gate-artifact-safety-review.md` — a path never passed to anything. The agent
# inferred it from the BRANCH NAME and wrote it under `-s danger-full-access`. The first version of
# this code snapshotted only `--out`'s directory, so it watched the temp dir and reported nothing
# while the write landed in the repo. The round-3 failure reproduced live, on the branch fixing it,
# past the fix. Watching `--out` alone protects the unsafe call shape and misses the safe one, which
# is backwards: the documented mitigation puts `--out` OUTSIDE the repo precisely so a direct write
# cannot reach an artifact — and that is exactly when `--out`'s directory is the wrong thing to watch.
ARTIFACT_ROOTS = ("docs/reviews",)


def watched_dirs(out_path: str) -> "list[str]":
    """Every directory whose contents must not change behind the wrapper's back. PURE-ish."""
    dirs = [os.path.dirname(os.path.abspath(out_path)) or "."]
    for rel in ARTIFACT_ROOTS:
        d = os.path.join(REPO_ROOT, rel)
        if os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    return dirs


def snapshot_all(dirs: "list[str]") -> "dict[str, dict[str, str]]":
    return {d: dir_snapshot(d) for d in dirs}


def intrusions(before: "dict[str, dict[str, str]]", after: "dict[str, dict[str, str]]",
               ours: "set[str]") -> "list[tuple[str, str, str]]":
    """(directory, filename, what) for every change the wrapper did not make. PURE."""
    out = []
    for d, b in before.items():
        for line in unexpected_writes(b, after.get(d, {}), ours):
            name, _, what = line.partition(": ")
            out.append((d, name, what))
    return out


def quarantine(created: "list[tuple[str, str]]", dest: str) -> "list[str]":
    """Move agent-CREATED files out of the artifact tree. Returns what moved.

    ⚠ ONLY created files, and that limit is stated rather than papered over. An OVERWRITTEN file
    cannot be restored from a hash — the snapshot keeps digests, not bytes — so the honest remedy
    there is `git checkout --`, which the caller is told verbatim. Keeping a full byte copy of
    `docs/reviews/` (600+ files) on every run to cover a case git already covers would be the more
    expensive half of a worse trade.
    """
    moved = []
    os.makedirs(dest, exist_ok=True)
    for d, name in created:
        src = os.path.join(d, name)
        try:
            os.replace(src, os.path.join(dest, name))
            moved.append(src)
        except OSError:
            continue
    return moved


def dir_snapshot(directory: str) -> "dict[str, str]":
    """{filename: sha256} for the files directly in `directory`. Missing dir -> {}. PURE-ish."""
    try:
        names = os.listdir(directory)
    except OSError:
        return {}
    out = {}
    for n in sorted(names):
        p = os.path.join(directory, n)
        if os.path.isfile(p):
            try:
                out[n] = _digest(p)
            except OSError:
                continue
    return out


def unexpected_writes(before: "dict[str, str]", after: "dict[str, str]",
                      written_by_us: "set[str]") -> "list[str]":
    """Files the AGENT changed or created behind the wrapper's back. PURE.

    `written_by_us` is what this process deliberately wrote, so promoting a review is not reported
    as an intrusion. Everything else in the review directory changing during a review run means the
    agent reached past `-o <tempfile>` — the round-3 failure, which nothing detected at the time.

    ⛔ IT CANNOT NAME THE WRITER, AND MUST NOT PRETEND TO (backlog #92). The evidence is a
    before/after digest map for a directory. That supports exactly one claim — *this file changed
    while the run was in flight* — and never *the agent changed it*. The wording used to assert the
    second, and DUAL REVIEW GUARANTEES A CONCURRENT WRITER BY CONSTRUCTION: both halves are told to
    write into `docs/reviews/`, so the correct documented workflow trips this every time the halves
    overlap. Measured false accusations are on record in FOUR review docs (`209-r1-codex`,
    `spec-…-r1-codex`, `spec-…-r2-codex`, `code-…-r5-coordinator`) before anyone filed it.
    The detector is still worth having — a real intrusion looks like this too — so the fix is to
    report what is observed and let the reader adjudicate, not to soften the alarm.
    """
    problems = []
    for name, sha in sorted(after.items()):
        if name in written_by_us:
            continue
        if name not in before:
            problems.append(f"{name}: CREATED during the run (writer unattributed)")
        elif before[name] != sha:
            problems.append(f"{name}: OVERWRITTEN during the run (writer unattributed)")
    for name in sorted(set(before) - set(after)):
        problems.append(f"{name}: DELETED during the run")
    return problems


def classify(exit_code: int, stdout: str, message: "str | None",
             min_chars: int = MIN_REVIEW_CHARS, timed_out: bool = False,
             out_path: str = "") -> "tuple[str, str]":
    """Decide whether this run produced a real review. Returns (Outcome, human reason).

    `message` is the content of the --output-last-message file, or None if the CLI never wrote it.
    Subject to the timeout rule below, that single value decides pass/fail; stdout only explains a
    failure.
    """
    # A timed-out run is killed mid-flight, so anything already in the message file is by definition
    # a PARTIAL review — and a partial adversarial review is worse than none, because its silence on
    # a topic reads as "nothing found there". This check must precede the length check: the earlier
    # version tested length first and would certify a truncated file that happened to clear the
    # threshold, contradicting this module's own "a hung review must fail the gate". Caught by the
    # round-3 adversarial review (docs/reviews/codex-dispatch-wrapper-codex-v3.md).
    # Keyed off an explicit flag, not exit code 124 — a real process can legitimately return 124.
    if timed_out:
        return Outcome.TRY_NEXT, "timed out — any partial message is an incomplete review"

    body = (message or "").strip()
    if len(body) >= min_chars:
        # ⛔ A SUMMARY OF A REVIEW IS "SUBSTANTIVE" AND IS NOT A REVIEW — measured 2026-08-25, M4 r7.
        # The final message read "Wrote the Round 7 review to docs/reviews/plan-m4-v2-r7-codex.md"
        # followed by four one-line conclusions. It cleared min_chars comfortably, so this function
        # returned OK, and the caller then wrote that summary OVER the path the agent had just
        # written the real review to. The premises, the quoted code and every measurement were lost.
        #
        # The length rule was itself the fix for an earlier fail-open (exit codes certifying HTTP-400
        # runs). It answers "did the model say anything?" and cannot answer "is this the artifact?".
        # The tell is SELF-REFERENCE: a review does not name the file it is being written to, because
        # it does not know it. A report of having written one always does.
        #
        # Root cause was in the PROMPT — it told the agent it had a review file — but a wrapper whose
        # whole purpose is refusing to record a gate that did not run should not depend on every
        # future prompt being worded correctly.
        if out_path and _names_own_output(body, out_path):
            return Outcome.TRY_NEXT, (
                f"the final message NAMES ITS OWN OUTPUT FILE ({os.path.basename(out_path)}), so it "
                "is a report of having written a review, not the review. The review itself was not "
                "captured — see the prompt rule 'YOUR FINAL MESSAGE IS THE REVIEW ITSELF'")
        return Outcome.OK, f"{len(body)} chars"

    # No usable message. Diagnose WHY — for the operator's benefit only. Nothing below changes
    # control flow: every path returns TRY_NEXT, so the loop always walks the full candidate list.
    #
    # There is deliberately no early-abort. Rounds 3 and 4 each found the same defect in a different
    # matcher — first AUTH_PROSE, then ERROR_LINE — where text in the ECHOED PROMPT (stdout carries
    # the prompt as well as the CLI's own output) could trip an account-fault branch and stop the
    # wrapper trying models that would have worked. Patching the second matcher would have invited a
    # third. Removing the branch removes the class: stdout can no longer influence what we do, only
    # what we say. The cost is a few fast-failing attempts when the fault really is account-wide,
    # which is worth strictly more than the risk of skipping a model that would have produced the
    # review.
    err = ERROR_LINE.search(stdout)
    if err:
        status = int(err.group(1))
        note = " (account-level — later models will likely fail too)" if status in ACCOUNT_FAULT_STATUSES else ""
        return Outcome.TRY_NEXT, f"CLI reported HTTP {status}{note}"

    if AUTH_PROSE.search(stdout):
        return Outcome.TRY_NEXT, "possible auth/quota fault (advisory match on stdout)"

    if message is None:
        return Outcome.TRY_NEXT, f"CLI wrote no final message (exit {exit_code})"

    return Outcome.TRY_NEXT, (
        f"final message was only {len(body)} chars (< {min_chars}) — "
        f"this is the silent no-op, NOT a clean review"
    )


def run_codex(model: str, prompt: str, timeout: int) -> "tuple[int, str, str | None, bool]":
    """One `codex exec`. Returns (exit_code, stdout, final_message_or_None, timed_out).

    stdin is closed: `codex exec` otherwise blocks on "Reading additional input from stdin..." and
    hangs forever under automation (observed 2026-07-19 — indistinguishable from a slow model).
    A timeout is mandatory for the same reason: a hung review must fail the gate, not stall it.
    """
    fd, msg_path = tempfile.mkstemp(prefix="codex-review-", suffix=".md")
    os.close(fd)
    os.unlink(msg_path)  # the CLI creates it; absence is the signal we rely on
    timed_out = False
    try:
        try:
            p = subprocess.run(
                # ⟳ `-s danger-full-access` — ADDED 2026-08-07, and it fixes a gate that had been
                # running at HALF STRENGTH without saying so.
                #
                # THERE ARE TWO INDEPENDENT SANDBOXES and disabling the outer one does nothing to
                # the inner one. Claude Code's `dangerouslyDisableSandbox` governs launching THIS
                # process; `codex exec` then applies its OWN Seatbelt policy to itself, and with no
                # `-s` flag that default is `workspace-write`. MEASURED in round 7: the reviewer
                # could not reach Docker —
                #   dial unix /Users/…/docker.sock: connect: operation not permitted
                # — so it reported `0/35 mutations … SQL did not run` and reviewed by READING. Its
                # findings were right, but this artifact was moved out of prose into executable SQL
                # at round 4→5 precisely because reading is the most expensive way to find defects.
                # A reviewer that cannot execute is reviewing the round-4 way.
                #
                # `trust_level = "trusted"` in ~/.codex/config.toml does NOT help: it governs
                # approval prompts, not socket access. And there is no narrower setting that works —
                # the verifier needs a unix socket outside any workspace root, so `workspace-write`
                # cannot reach it no matter where the files are put.
                #
                # The trade is deliberate: every use of this wrapper is "run an adversarial review
                # that must execute the suite", against a local Postgres, on the author's own
                # machine. Full access is the requirement, not a convenience.
                ["codex", "exec", "-m", model, "-s", "danger-full-access",
                 "-o", msg_path, prompt],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )
            code, out = p.returncode, p.stdout
        except subprocess.TimeoutExpired as e:
            partial = e.output or ""
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", "replace")
            code, out, timed_out = 124, partial + f"\n[wrapper] timed out after {timeout}s", True
        except FileNotFoundError:
            return 127, "[wrapper] `codex` not found on PATH", None, False

        message = None
        if os.path.exists(msg_path):
            with open(msg_path, encoding="utf-8", errors="replace") as f:
                message = f.read()
        return code, out, message, timed_out
    finally:
        if os.path.exists(msg_path):
            os.unlink(msg_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", help="the review prompt")
    ap.add_argument("--prompt-file", help="read the prompt from this file instead")
    ap.add_argument("--out", help="write the review here (required unless --self-test)")
    ap.add_argument("--model", help="force a single slug; disables fallback")
    ap.add_argument("--timeout", type=int, default=900,
                    help="per-attempt timeout in seconds. The 900s default suits a SMALL "
                         "review; a full-file sweep that runs a mutation harness needs "
                         "2700-3600. Measured 2026-09-16: three reviews of a 2,100-line "
                         "file 'timed out' at 900s and were read as Codex being "
                         "unavailable; the same review completed first try at 3600s and "
                         "found two defects three other rounds had missed.")
    ap.add_argument("--min-chars", type=int, default=MIN_REVIEW_CHARS,
                    help="minimum final-message length that counts as a real review")
    ap.add_argument("--allow-overwrite", action="store_true",
                    help="permit --out to replace an existing file (refused by default: backlog #68)")
    ap.add_argument("--verdict", help="write the run's verdict here "
                                      f"(default: {VERDICT_DIR}/<review-stem>.<run-token>.verdict.json, "
                                      "where the run token is derived from the dispatch HEAD and the "
                                      "prompt). Also the deliberate escape when the derived path "
                                      "holds committed testimony — --allow-overwrite governs --out "
                                      "only and does not authorise replacing a verdict.")
    ap.add_argument("--self-test", action="store_true", help="run classifier checks and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not args.out:
        ap.error("--out is required")
    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    if not prompt:
        ap.error("provide a prompt argument or --prompt-file")

    # ── backlog #68 (b): the one input that guarantees a rejected capture ──
    # Warn rather than refuse: a brief is free to *discuss* writing files, and a wrapper that
    # refused would eventually be worked around. But this is loud, and it is repeated in the
    # failure block below, because in round 3 the run "succeeded" in the caller's eyes while the
    # gate had not run at all.
    demand = prompt_demands_a_file(prompt)
    if demand:
        print(f"[codex-review] ⚠ THE PROMPT TELLS THE AGENT TO WRITE A FILE ({demand!r}).\n"
              f"[codex-review]   This wrapper decides success ONLY by whether the final message IS\n"
              f"[codex-review]   the review, so such a brief makes the final message a report of\n"
              f"[codex-review]   having written one — which is then correctly rejected. Round 3 lost\n"
              f"[codex-review]   a whole review half to exactly this one sentence.\n"
              f"[codex-review]   Say instead: 'your final message IS the review; write no file.'",
              file=sys.stderr)

    # ── backlog #68 (a): see the agent's own writes ──
    # The wrapper writes `--out` only on success, which was never the protection it looked like:
    # under `-s danger-full-access` the AGENT writes wherever it infers, and in round 3 it inferred
    # a committed review path from the filenames listed in the brief. Snapshot the destination
    # directory so an intrusion is detected and named instead of being discovered days later.
    out_dir = os.path.dirname(os.path.abspath(args.out)) or "."
    out_name = os.path.basename(args.out)
    watched = watched_dirs(args.out)
    before = snapshot_all(watched)

    # ── backlog #68 (d): every exit from here on leaves testimony on disk ──
    # `emit` is the ONLY way out below, so a new branch cannot forget to record one. A verdict that
    # cannot be written downgrades the run to CANNOT RUN (2) rather than reporting the outcome it
    # was about to report — an unrecorded success is indistinguishable from the failure this fixes.
    # Taken ONCE, here, before any candidate runs — this is the tree the reviewer is handed. Taken
    # at `emit` instead it would describe the tree after the run, and a commit made while a 15-minute
    # review was in flight would be recorded as something the reviewer had seen.
    # ⟳ **r4 H1: THIS MOVED ABOVE `vpath`, AND THE ORDER IS NOW LOAD-BEARING.** The allocator names
    # the run from the dispatch HEAD, so the state has to be gathered before the path is derived.
    head_at_dispatch, dirty_at_dispatch = reviewed_state()
    vpath = verdict_path(args.out, args.verdict,
                         run_id=run_token(head_at_dispatch, prompt))
    # ⛔ BEFORE ANY TESTIMONY IS WRITTEN, and before `emit` exists — because `emit` WRITES to `vpath`,
    # so a refusal discovered inside it would have to destroy the thing it is protecting in order to
    # report that it was protecting it.
    _collision = verdict_collision(vpath, tracked=path_is_tracked(vpath),
                                   override_given=bool(args.verdict))
    if _collision:
        print(f"[codex-review] {_collision}", file=sys.stderr)
        # ⟳ **r4 M5 — THE REFUSAL NOW TESTIFIES, under a name that collides with nothing.** This was
        # the ONE exit that left nothing on disk, so downstream a refused dispatch and a dispatch
        # that never happened read identically — the exact indistinguishability the verdict
        # mechanism was built to abolish, re-opened for one path. It is written to
        # `refusal_verdict_path(vpath)`, never `vpath`, so reporting the protection cannot perform
        # the destruction it is protecting against.
        _rpath = refusal_verdict_path(vpath)
        _rerr = write_verdict(_rpath, verdict_record(
            gate_ran=False, exit_code=2, out_path=args.out,
            reason=f"refused: {_collision.splitlines()[0]}",
            head=head_at_dispatch, dirty=dirty_at_dispatch,
            prompt=getattr(args, "prompt_file", None)))
        if _rerr:
            print(f"[codex-review]   ⚠ and the refusal itself could not be recorded: {_rerr}",
                  file=sys.stderr)
        else:
            print(f"[codex-review]   testimony (gate_ran=false): {_rpath}", file=sys.stderr)
        return 2

    def emit(rc: int, *, gate_ran: bool, reason: str, model=None, attempts=None, hits=None) -> int:
        rec = verdict_record(gate_ran=gate_ran, exit_code=rc, out_path=args.out, reason=reason,
                             model=model, attempts=attempts,
                             head=head_at_dispatch, dirty=dirty_at_dispatch,
                             prompt=getattr(args, "prompt_file", None),
                             intrusions_seen=[f"{os.path.join(d, n)}: {w}" for d, n, w in (hits or [])])
        err = write_verdict(vpath, rec)
        if err:
            print(f"[codex-review] CANNOT RUN — the verdict could not be written to {vpath}: {err}.\n"
                  f"[codex-review]   Nothing outside this process can now establish whether the gate\n"
                  f"[codex-review]   ran, which is the very condition the verdict exists to abolish.\n"
                  f"[codex-review]   Treat this run as NOT RUN.", file=sys.stderr)
            return 2
        print(f"[codex-review] verdict: gate_ran={str(gate_ran).lower()} -> {vpath}", file=sys.stderr)
        return rc

    if out_name in before.get(out_dir, {}) and not args.allow_overwrite:
        print(f"[codex-review] REFUSING — {args.out} already exists.\n"
              f"[codex-review]   A filed review is an artifact; replacing it silently is what this\n"
              f"[codex-review]   check exists to stop (measured: four models overwrote one file in\n"
              f"[codex-review]   turn, and its verdict flipped from NO to YES between two reads).\n"
              f"[codex-review]   Choose a new path, or pass --allow-overwrite deliberately.",
              file=sys.stderr)
        return emit(2, gate_ran=False,
                    reason="refused: --out already exists and --allow-overwrite was not given")

    models = [args.model] if args.model else resolve_candidates()
    print(f"[codex-review] candidates: {', '.join(models)}", file=sys.stderr)

    attempts = []
    for slug in models:
        print(f"[codex-review] trying {slug} ...", file=sys.stderr)
        code, stdout, message, timed_out = run_codex(slug, prompt, args.timeout)
        outcome, reason = classify(code, stdout, message, args.min_chars, timed_out,
                                   out_path=args.out)
        attempts.append(f"  {slug}: {outcome} — {reason}")

        if outcome == Outcome.OK:
            # OK is only returned when the stripped message cleared min_chars, so it is non-empty.
            # Recompute rather than re-deriving from the Optional, so the file we write is exactly
            # what was validated.
            body = (message or "").strip()
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(f"<!-- codex-review: model={slug} -->\n\n")
                f.write(body + "\n")
            hits = intrusions(before, snapshot_all(watched), {out_name})
            if hits:
                print("[codex-review] ⚠ WATCHED FILES CHANGED DURING THE RUN "
                      "(this does NOT identify the writer):", file=sys.stderr)
                for d, name, what in hits:
                    print(f"[codex-review]     {os.path.join(d, name)} — {what}", file=sys.stderr)
                print("[codex-review]   The review above was captured from the final message and is "
                      "valid, but those\n[codex-review]   files are not it. ADJUDICATE BEFORE "
                      "BLAMING THE AGENT — if a concurrent review\n[codex-review]   half or the "
                      "coordinator was writing into docs/reviews/, this is the expected,\n"
                      "[codex-review]   documented workflow and not an intrusion (backlog #92). "
                      "Otherwise inspect with\n[codex-review]   `git diff` / `git status`, restore "
                      "any overwrite with `git checkout --`, and fix\n[codex-review]   the brief so "
                      "it does not tell the agent to write.", file=sys.stderr)
            print(f"[codex-review] OK via {slug} -> {args.out} ({reason})", file=sys.stderr)
            return emit(0, gate_ran=True, reason=reason, model=slug, attempts=attempts,
                        hits=hits)

        print(f"[codex-review] {slug} unusable: {reason}", file=sys.stderr)

    print("\n[codex-review] FAILED — no candidate produced a usable review.", file=sys.stderr)
    print("\n".join(attempts), file=sys.stderr)
    # A FAILED GATE MUST NOT LEAVE AN ARTIFACT. The wrapper writes nothing on this path — but the
    # agent may have, which is the round-3 failure exactly. Say so, loudly, on the path where the
    # caller is about to conclude "the gate did not run".
    hits = intrusions(before, snapshot_all(watched), set())
    if hits:
        # ⛔ WHY QUARANTINING IS SAFE AGAIN — backlog #92, and it was NOT safe before 2026-09-04.
        # `quarantine()` below MOVES every file this run saw appear at the top level of
        # docs/reviews/, and a digest snapshot cannot tell a Codex intrusion from a CONCURRENT
        # CLAUDE HALF writing its own review. Reproduced on temp dirs: a legitimate
        # `slice-r6-claude.md` was moved out of the reviews directory. ⚠ AND THIS IS THE FALLBACK
        # PATH — docs/plugins.md says a failed or rate-limited Codex run must be replaced by a
        # Claude adversarial review, so the run most likely to quarantine was the very run whose
        # replacement was being written beside it.
        # THE FIX IS A LAYOUT, NOT A PREDICATE (the user chose it): review halves now land in
        # `docs/reviews/<writer>/`, which this NON-RECURSIVE snapshot cannot see. Nothing legitimate
        # is written to the top level during a run, so anything appearing there IS unexpected and
        # moving it is right. `check-review-rounds.py` reads both layouts and refuses a basename
        # filed in both. ⚠ IF YOU EVER MAKE THE SNAPSHOT RECURSIVE, this reasoning dies with it and
        # the concurrent-half hazard comes straight back.
        print("[codex-review] ⚠ AND WATCHED FILES CHANGED DESPITE THE FAILURE "
              "(writer NOT identified — see backlog #92):", file=sys.stderr)
        for d, name, what in hits:
            print(f"[codex-review]     {os.path.join(d, name)} — {what}", file=sys.stderr)
        # A FAILED GATE MUST NOT LEAVE AN ARTIFACT. Reporting alone was not enough: if the caller
        # misses the exit code — the measured fourth occurrence of that trap — an agent-written file
        # sits in docs/reviews/ looking exactly like a filed gate artifact. So created files are
        # MOVED OUT. Overwrites cannot be undone from a digest; git is the remedy and is named.
        created = [(d, n) for d, n, what in hits if what.startswith("CREATED")]
        if created:
            dest = tempfile.mkdtemp(prefix="codex-review-quarantine-")
            moved = quarantine(created, dest)
            if moved:
                print(f"[codex-review]   QUARANTINED {len(moved)} agent-created file(s) -> {dest}",
                      file=sys.stderr)
                print("[codex-review]   A failed gate leaves no artifact behind. Nothing was "
                      "deleted; inspect them there.", file=sys.stderr)
        if any(w.startswith("OVERWRITTEN") or w.startswith("DELETED") for _, _, w in hits):
            print("[codex-review]   ⚠ An existing file was overwritten or deleted and CANNOT be "
                  "restored from a digest.\n[codex-review]   Run `git checkout -- <path>` for each "
                  "one listed above.", file=sys.stderr)
    if demand:
        print(f"[codex-review] ⚠ LIKELY CAUSE: the prompt says {demand!r}. See the warning above.",
              file=sys.stderr)
    # ⛔ A TIMEOUT IS A STATEMENT ABOUT THE BUDGET, NOT ABOUT CODEX — and this message used to send
    # the caller straight to the fallback without saying so. MEASURED 2026-09-16: three reviews of a
    # 2,100-line file "timed out" at the 900s default, were read as Codex being unavailable, and the
    # branch merged on single-half review with `REVIEW GAP: codex` recorded three times. The SAME
    # review completed on the first attempt at `--timeout 3600` and found two defects the three
    # Claude rounds had missed — an encoded-dot bypass and an unescaped filename injected into HTML.
    # The user's note: this had happened before, and doubling the timeout resolved it then too.
    # ⚠ ADDITIVE, not instead-of — r1 Medium 3. The first version printed this in place of the
    # fallback line, so a genuinely unavailable Codex lost its instruction.
    advice = timeout_advice(attempts, args.timeout)
    if advice:
        print("[codex-review] " + advice.replace("\n", "\n[codex-review] "), file=sys.stderr)
    print("[codex-review] The Codex gate did NOT run. Fall back to a Claude adversarial review "
          "and note the gap in the review doc.", file=sys.stderr)
    return emit(1, gate_ran=False,
                reason="no candidate produced a usable review", attempts=attempts, hits=hits)


def timeout_advice(attempts: "list[str]", timeout: int) -> "str | None":
    """The 'raise your budget' message, or None when that is not the diagnosis. PURE.

    ⛔ EXTRACTED SO IT CAN BE FALSIFIED — r1 Medium 4. Inline in `main()`, the whole branch could be
    deleted and this file's suite stayed at **85/85**: a message nothing asserts is a message that
    will be quietly removed by the next refactor, which is exactly the class this project's mutation
    manifests exist to catch. A pure function of (attempts, timeout) is casable; a print inside a
    failure path is not.

    ⚠ `all`, NOT `any`, and the distinction is the finding: a run where one candidate timed out and
    another died of auth is NOT a budget problem, and telling the caller to double the timeout would
    send them round a loop that cannot succeed. Returns None for an empty list too — no attempts
    means no evidence either way.
    """
    if not attempts or not all("timed out" in a for a in attempts):
        return None
    return ("⚠ EVERY ATTEMPT TIMED OUT, AND THAT IS PROBABLY THIS CALLER'S BUDGET, NOT CODEX.\n"
            f"  --timeout was {timeout}s. RE-RUN ONCE AT {timeout * 2}s BEFORE FALLING BACK — a "
            "full-file sweep that runs a mutation harness needs 2700-3600s.\n"
            "  Fall back only if it times out again at the larger budget, or fails for a "
            "non-timeout reason (auth, HTTP 4xx/5xx, usage limit).")


def case_line(ok: bool, name: str, got, want, reason: str = "") -> str:
    """PURE. The ONE `[PASS]`/`[FAIL]` line shape this suite prints.

    ⛔ THIS FUNCTION EXISTS BECAUSE THE FIX FOR THE PREVIOUS BREAK COULD NOT FAIL — r13 High, and it
    was proved by execution rather than argued: reverting the classifier printer to its broken shape
    left the whole 618-mutation gate at `618 killed, 618 attributed, 0 survivor(s)`, rc=0,
    byte-identical to the repaired tree. All nine manifest entries for this file name `chk` cases, so
    nothing measured the printer at all.

    That matters because this file has broken the `[FAIL] <case>` contract TWICE. r11 found `chk`
    emitting `got={got!r}`; r12 found the classifier printer, twenty-one lines away, still emitting
    `got={got} ({reason})` — the same defect, in the same function, in the round convened to remove
    it. Both survived for as long as they did because nothing had tried to attribute a kill here.
    A third recurrence would have been equally silent.

    TWO printers were TWO copies of one contract, which is the duplicate-mechanism shape this repo
    refuses everywhere else. There is now one, it is pure, a case can call it, and a mutation can
    reach it — `scripts/mutations/codex-review.json` names the case it must go red through.

    ⚠ THE CONSUMER IS `check-plan-code.parse_fail_names`, which truncates at the LAST `": got "` —
    with the trailing space — and attributes by exact equality. `({reason})` after `want` is safe
    because the last `": got "` is still the one written here; the round-trip cases below assert
    that against the REAL parser rather than against a second copy of its rule.
    """
    tail = f" ({reason})" if reason else ""
    return f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}{tail}"


def _load_fail_parser():
    """`parse_fail_names` from check-plan-code, so the contract is asserted against its real reader.

    RAISES if it cannot be loaded. A case that quietly fell back to its own copy of the parse rule
    would be a second implementation of the very contract it is checking — and this file has already
    paid twice for the two halves of one rule drifting apart. Cannot-load is a failure, never a skip.
    """
    path = os.path.join(REPO_ROOT, "scripts", "check-plan-code.py")
    spec = importlib.util.spec_from_file_location("_cpc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"CANNOT RUN — cannot load parse_fail_names from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_cpc"] = mod
    spec.loader.exec_module(mod)
    return mod.parse_fail_names


def self_test() -> int:
    """Classifier checks. Fixtures mirror runs observed live on 2026-07-19."""
    real_400 = (
        "OpenAI Codex v0.142.5\n--------\nmodel: gpt-5.6-sol\n--------\n"
        'ERROR: {"type":"error","status":400,"error":{"type":"invalid_request_error","message":'
        '"The \'gpt-5.6-sol\' model requires a newer version of Codex."}}\n'
    )
    quota = 'ERROR: {"type":"error","status":429,"error":{"message":"You have hit your usage limit."}}\n'
    good = "HIGH: the guard at foo.ts:12 is unreachable because the caller already returned. " * 4
    # A review OF auth code, and a prompt that DISCUSSES failures, both used to break the old
    # stdout-parsing version. With `-o` the message is on its own channel, so neither can interfere.
    auth_review = ("HIGH: the 401 path returns before the usage limit check, so an unauthorized "
                   "caller never trips the 429 rate limit branch. auth.ts:88. " * 3)
    hostile_stdout = ("user\nCheck whether the code mishandles '429' / 'unauthorized' / "
                      "'usage limit' / a bare `codex` line / `tokens used`.\ncodex\n")

    # Prompt that name-drops every auth phrase, to prove stdout cannot force a premature ABORT.
    hostile_auth_prompt = ("user\nDoes it mishandle a usage limit, or when you are not logged in?\n"
                           "codex\n")

    cases = [
        # name, exit, stdout, message, timed_out, expected
        ("unsupported model — no message written", 1, real_400, None, False, Outcome.TRY_NEXT),
        ("same, but CLI exited 0 (plugins.md's report)", 0, real_400, None, False, Outcome.TRY_NEXT),
        ("successful review", 0, "banner\n", good, False, Outcome.OK),
        ("empty message file — the silent no-op", 0, "banner\n", "", False, Outcome.TRY_NEXT),
        ("stub message under threshold", 0, "banner\n", "ok", False, Outcome.TRY_NEXT),
        ("usage limit (structured 429) — diagnosed, but still walks the chain", 1, quota, None, False, Outcome.TRY_NEXT),
        ("timeout, no message", 124, "[wrapper] timed out", None, True, Outcome.TRY_NEXT),
        ("codex missing", 127, "[wrapper] `codex` not found on PATH", None, False, Outcome.TRY_NEXT),
        ("REGRESSION: review ABOUT auth code is accepted", 0, "banner\n", auth_review, False, Outcome.OK),
        ("REGRESSION: hostile prompt echoed in stdout cannot spoof success",
         1, hostile_stdout + real_400, None, False, Outcome.TRY_NEXT),
        ("REGRESSION: hostile prompt cannot invalidate a real review",
         0, hostile_stdout, good, False, Outcome.OK),
        ("run errored but CLI wrote a COMPLETE message — message wins",
         1, "banner\n", good, False, Outcome.OK),
        # v3-High: length was checked before the timeout, so a truncated-but-long partial passed.
        ("v3-High: TIMED OUT with a long partial message must NOT pass",
         124, "[wrapper] timed out", good, True, Outcome.TRY_NEXT),
        # v3-Medium: prose auth match must not end the fallback chain (was ABORT).
        ("v3-Medium: auth words in the echoed prompt do not abort the chain",
         1, hostile_auth_prompt, None, False, Outcome.TRY_NEXT),
        # v4-Medium: same shape via the STRUCTURED matcher — a prompt QUOTING a 429 ERROR line.
        ("v4-Medium: a quoted 429 ERROR line in the prompt does not abort the chain",
         1, "user\nfixture: " + quota + "codex\n", None, False, Outcome.TRY_NEXT),
        # ⛔ M4 r7, MEASURED: a SUMMARY of a review is substantive and is not a review. The real
        # final message named its own output path and was written OVER the review the agent had
        # just saved there. The tell is self-reference — a review cannot name its own destination.
        ("r7-Blocking: a final message that NAMES ITS OWN OUTPUT FILE is a report, not a review",
         0, "", ("Wrote the Round 7 review to docs/reviews/plan-m4-v2-r7-codex.md.\n\n"
                 "Result: NOT CONVERGED.\n\nFindings filed:\n"
                 "- Blocking: TRUNCATE is omitted from the live privilege digest.\n"
                 "- High: proargdefaults is excluded for a false reason.\n"
                 "Cleanup verified: remaining_dbs|<none>\n" + "padding. " * 30),
         False, Outcome.TRY_NEXT),
        ("r7: a REAL review that never names the output path still passes",
         0, "", ("**Blocking: the digest omits TRUNCATE.**\n\nPremise:\n"
                 "- scripts/m4_catalog.py:155 REL_PRIVS = (SELECT, INSERT, UPDATE, DELETE)\n\n"
                 "Executed:\n```\nanon TRUNCATE before: false\nafter: true\ngate exit=0\n```\n"
                 "NOT CONVERGED\n" + "padding. " * 30),
         False, Outcome.OK),
    ]
    failures = 0
    OUT = "docs/reviews/plan-m4-v2-r7-codex.md"
    for name, code, out, msg, t_out, want in cases:
        got, reason = classify(code, out, msg, MIN_REVIEW_CHARS, t_out, out_path=OUT)
        ok = got == want
        # ⛔ THE SECOND PRINTER, AND r12 IS WHY THIS COMMENT EXISTS. The r11 Blocking repair fixed
        # `chk`'s printer 21 lines below and left this one emitting `got={got} ({reason})` — the
        # exact broken shape the round was convened to remove — so all 17 `classify` cases, the half
        # that decides whether a review gate RAN, stayed invisible to `parse_fail_names`. The r11
        # coordinator document and the comment below both asserted "the printer is now canonical",
        # and both were false about this file. Fixing the instance and calling it the class, inside
        # the same function, in the round whose brief named that as the question to answer.
        # ⚠ `({reason})` AFTER `want` is deliberate and safe: the parser truncates at the LAST
        # `": got "`, which is still the one this line writes, and no `reason` contains that string.
        print(case_line(ok, name, got, want, reason))
        if not ok:
            failures += 1
    # ── backlog #68: the artifact-safety half ──────────────────────────────────────────────────
    extra = 0

    def chk(name: str, got, want) -> None:
        nonlocal failures
        nonlocal extra
        extra += 1
        ok = got == want
        # ⛔ THE CANONICAL LINE, AND IT USED TO BE `got={got!r}` — r11 Blocking (Codex half).
        # `check-plan-code.parse_fail_names` truncates a case name at the LAST `": got "`, WITH the
        # trailing space, and attributes a kill by `w == f` — exact equality, not a substring. So
        # `: got=` never matched, every parsed name kept its `: got=…` tail, and no manifest entry
        # for this file could EVER be attributed. It went unnoticed because nothing had tried:
        # `codex-review.py` sat in `WIDENED_MANIFEST_DEBT` with no mutations at all until r11, so
        # the contract had no consumer. Adding the manifest is what made the producer's silence
        # audible. This is the recorded *a guard's own output is a CONTRACT* shape, in the file that
        # decides whether a review gate ran.
        print(case_line(ok, name, got, want))
        if not ok:
            failures += 1

    # (b) The exact sentence from the round-3 brief must be caught.
    # ── timeout_advice — r1 Medium 4: this branch was deletable at 85/85 before these ──────
    # ⛔ THE COST OF NOT HAVING THEM IS ON THE RECORD: a 900s default was read as "Codex is
    # unavailable" three rounds running, a branch merged on single-half review, and the review that
    # finally ran found two defects the other half had missed. The advice is the fix; these are what
    # keep it.
    _to = ["  gpt-5.5: try_next — timed out — any partial message is an incomplete review"]
    chk("every attempt timed out -> advise raising the budget",
        timeout_advice(_to, 900) is not None, True)
    chk("…and it names the DOUBLED number, not a fixed one",
        "1800s" in (timeout_advice(_to, 900) or ""), True)
    chk("…which tracks the caller's actual --timeout",
        "7200s" in (timeout_advice(_to, 3600) or ""), True)
    # ⛔ `all`, NOT `any` — a mixed failure is not a budget problem, and doubling the timeout would
    # send the caller round a loop that cannot succeed.
    chk("a MIXED failure is not a budget diagnosis",
        timeout_advice(_to + ["  gpt-5.4: try_next — HTTP 401"], 900), None)
    chk("a non-timeout failure is not a budget diagnosis",
        timeout_advice(["  gpt-5.5: try_next — usage limit"], 900), None)
    # ⛔ NO ATTEMPTS IS NO EVIDENCE — not an implicit pass for either reading.
    chk("no attempts at all yields no advice", timeout_advice([], 900), None)

    chk("round 3's actual sentence is caught",
        bool(prompt_demands_a_file("Output\n\nWrite the review to the review path you were given.")),
        True)
    chk("`Output file:` header is caught",
        bool(prompt_demands_a_file("Output file: docs/reviews/x.md")), True)
    chk("`save your findings as` is caught",
        bool(prompt_demands_a_file("Then save your findings as a markdown file.")), True)
    # ⚠ FALSE POSITIVES ARE THE REAL RISK. A review prompt legitimately DISCUSSES code that writes
    # files; a matcher that trips on that would train people to ignore the warning.
    chk("a prompt reviewing file-writing code does NOT trip it",
        prompt_demands_a_file(
            "Review gen-dashboard.py. It will write the page to ~/explainers and must not "
            "overwrite a file it did not create. Does _write_sandbox hold?"), None)
    chk("round 2's brief (which captured cleanly) does NOT trip it",
        prompt_demands_a_file(
            "You are reviewing a plan. Report Blocking/High/Medium/Low findings with file:line."),
        None)

    # ── task #222: the three phrasings this guard MISSED in round 4 ────────────────────────────
    # Each is the literal text measured against the live guard, not a paraphrase. The guard was
    # built for backlog #68 round 3 — the identical failure — and stayed silent one round later,
    # so these are regression cases for a defect that has now occurred twice.
    chk("round 4's ACTUAL breach — a prohibition carving out one permitted write — is caught",
        bool(prompt_demands_a_file(
            "You must not write any files, except for the one review file you are asked to "
            "write.")), True)
    chk("`save the review at <path>` is caught (`at`, not `to`)",
        bool(prompt_demands_a_file("Please save the review at this path: /tmp/r.md")), True)
    chk("the PASSIVE form is caught",
        bool(prompt_demands_a_file("Your review should be written to disk when you finish.")),
        True)
    chk("`must be saved` is the same instruction in other clothes",
        bool(prompt_demands_a_file("Your findings must be saved under docs/reviews/.")), True)
    # ⚠ THE PASSIVE PATTERN IS THE ONE THAT COULD OVER-REACH, so it is anchored on `your`.
    # Without that anchor this next case fires, and the guard starts crying wolf about the code
    # under review — which is how a warning becomes noise and stops being read.
    chk("a brief DESCRIBING code that writes a report does NOT trip the passive pattern",
        prompt_demands_a_file(
            "The report will be written to disk by gen-dashboard.py; check the sandbox holds."),
        None)
    chk("the Codex brief's OWN prohibition does not trip it — it forbids writing, not demands it",
        prompt_demands_a_file(
            "Your final message IS the review; write no file."), None)

    # ── NEGATION: found 2026-09-04 by using this guard on a corrected brief ────────────────────
    # These are FALSE POSITIVES the guard produced against wording that gets the contract RIGHT.
    # Fail-closed, so never unsafe — but it refused the correct brief, and a guard that blocks the
    # right answer is worse than absent, because the fix people reach for is to weaken the guard.
    chk("`do not write your review to a file` is a PROHIBITION, not a demand",
        prompt_demands_a_file("Do not write your review to a file."), None)
    chk("`never save the review at` is a prohibition too",
        prompt_demands_a_file("You should never save the review at any path."), None)
    chk("`must not write the findings to` is a prohibition",
        prompt_demands_a_file("You must not write the findings to disk."), None)
    # ⚠ AND THE NEGATION MUST NOT BE A UNIVERSAL OFF-SWITCH. If a stray negator anywhere could
    # disarm the guard, the widening in #222 would be undone by one careless sentence.
    chk("a negator in a PREVIOUS sentence does not reach across the full stop",
        bool(prompt_demands_a_file(
            "Do not use the network. Write the review to docs/reviews/x.md.")), True)
    chk("a negator far away in the SAME sentence does not reach either",
        bool(prompt_demands_a_file(
            "Do not worry about formatting, style, tone, length, or ordering of the sections, "
            "and write the review to docs/reviews/x.md")), True)
    chk("a real demand LATER in the text is still caught when an earlier one is negated",
        bool(prompt_demands_a_file(
            "Do not write your review to a file.\nActually, save your findings as report.md.")),
        True)

    # (a) The intrusion detector.
    base = {"a.md": "sha-a", "b.md": "sha-b"}
    chk("nothing changed -> no report", unexpected_writes(base, dict(base), set()), [])
    chk("the file WE wrote is not an intrusion",
        unexpected_writes(base, {**base, "out.md": "new"}, {"out.md"}), [])
    # ⚠ THE REPORT NAMES THE OBSERVATION, NEVER THE WRITER (backlog #92). Asserting the exact
    # wording is the point: a digest diff cannot see who wrote, and the old text said "by the
    # agent", which the documented dual-review workflow falsified on four recorded runs.
    chk("a newly created file is reported WITHOUT naming a writer",
        unexpected_writes(base, {**base, "guessed.md": "x"}, set()),
        ["guessed.md: CREATED during the run (writer unattributed)"])
    # THE ROUND-3 FAILURE ITSELF: a committed review silently replaced.
    chk("an overwritten committed review is reported",
        unexpected_writes(base, {**base, "a.md": "different"}, set()),
        ["a.md: OVERWRITTEN during the run (writer unattributed)"])
    chk("a deleted file is reported",
        unexpected_writes(base, {"a.md": "sha-a"}, set()),
        ["b.md: DELETED during the run"])
    chk("a missing directory snapshots empty, never raises",
        dir_snapshot("/nonexistent/path/for/self/test"), {})

    # THE DEFECT THIS BRANCH REPRODUCED IN ITSELF. Watching only --out's directory means that when
    # --out is OUTSIDE the repo — the documented safe call shape — docs/reviews/ goes unwatched, and
    # that is exactly where the agent guessed its way to. Measured live on this branch.
    chk("docs/reviews is watched even when --out is outside the repo",
        os.path.join(REPO_ROOT, "docs/reviews") in watched_dirs("/tmp/elsewhere/out.md"), True)
    chk("--out's own directory is watched too",
        "/tmp/elsewhere" in watched_dirs("/tmp/elsewhere/out.md"), True)
    chk("no directory is watched twice",
        len(watched_dirs(os.path.join(REPO_ROOT, "docs/reviews/x.md")))
        == len(set(watched_dirs(os.path.join(REPO_ROOT, "docs/reviews/x.md")))), True)
    chk("an intrusion is reported with the directory it happened in",
        intrusions({"/d": {}}, {"/d": {"g.md": "x"}}, set()),
        [("/d", "g.md", "CREATED during the run (writer unattributed)")])

    # A failed gate must LEAVE NOTHING, not merely complain. Reporting alone was the first version,
    # and it fails whenever the caller misses the exit code — the measured fourth occurrence.
    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "reviews"); os.makedirs(src_dir)
        stray = os.path.join(src_dir, "guessed.md")
        with open(stray, "w") as f:
            f.write("an agent wrote this")
        moved = quarantine([(src_dir, "guessed.md")], os.path.join(td, "q"))
        chk("a created file is moved out of the artifact tree", moved, [stray])
        chk("…and is gone from where the agent put it", os.path.exists(stray), False)
        chk("…and still exists in quarantine, never deleted",
            os.path.exists(os.path.join(td, "q", "guessed.md")), True)

    # ── backlog #68 (d): the verdict ──
    chk("the default verdict lands INSIDE the repo, not beside --out",
        verdict_path("/tmp/anywhere/plan-x-r3-codex.md").startswith(
            os.path.join(REPO_ROOT, VERDICT_DIR)), True)
    chk("…named after the review, with the extension stripped",
        os.path.basename(verdict_path("/tmp/a/plan-x-r3-codex.md")),
        "plan-x-r3-codex.verdict.json")
    chk("an explicit --verdict wins", os.path.basename(verdict_path("/a/b.md", "/c/mine.json")),
        "mine.json")
    # ── r4 H1: THE ALLOCATOR. The refusal below is now the FALLBACK; this is the mechanism ──────
    # ⛔ **THE CASE THAT WOULD HAVE CAUGHT H1 IS THE FIRST ONE, AND IT IS THE DOCUMENTED CALL SHAPE.**
    # `docs/plugins.md` tells every caller to use `--out "$(mktemp -d)/r.md"`. Two reviews in one
    # session both reduced to the basename `r`, both derived `r.verdict.json`, and the second
    # destroyed the first — untracked, so the tracked-file refusal never fired. Dropping `run_id`
    # from `verdict_path` makes these two paths equal again and reds this case.
    # ⚠ TWO DISTINCT INPUTS on every property below: a token compared against ONE other value cannot
    # tell a real digest from a constant.
    _tokA = run_token("abc123", "review prompt A")
    _tokB = run_token("abc123", "review prompt B")
    _tokA2 = run_token("abc123", "review prompt A")
    _tokC = run_token("deadbee", "review prompt A")
    chk("H1: two DIFFERENT reviews at one HEAD cannot collide, even under the documented "
        "`--out \"$(mktemp -d)/r.md\"` shape that names them both `r`",
        verdict_path("/tmp/one/r.md", run_id=_tokA) == verdict_path("/tmp/two/r.md", run_id=_tokB),
        False)
    chk("…and the SAME review re-run lands on its own testimony rather than accumulating debris",
        verdict_path("/tmp/one/r.md", run_id=_tokA)
        == verdict_path("/tmp/three/r.md", run_id=_tokA2), True)
    chk("the token separates two reviews by PROMPT at one head, at two distinct prompts",
        (_tokA == _tokB, _tokA == _tokA2), (False, True))
    chk("…and by HEAD at one prompt — the r3 incident, where an earlier session's verdict was lost",
        (_tokA == _tokC, len(_tokC)), (False, 8))
    chk("a head that git could not answer for still separates runs by prompt, never fusing them",
        run_token(None, "p1") == run_token(None, "p2"), False)
    chk("…and is stable for one run, so an unanswerable head is not a random name",
        run_token(None, "p1"), run_token(None, "p1"))
    chk("the allocated name still carries the review stem, so a human can read it",
        os.path.basename(verdict_path("/tmp/a/plan-x-r3-codex.md", run_id="0f0f0f0f")),
        "plan-x-r3-codex.0f0f0f0f.verdict.json")
    chk("…and WITHOUT a run id the old naming survives, which is why the refusal is kept as a "
        "fallback rather than deleted",
        os.path.basename(verdict_path("/tmp/a/plan-x-r3-codex.md")),
        "plan-x-r3-codex.verdict.json")
    # ── r4 M5: a refusal testifies, under a name that is NEVER the one being protected ──────────
    _prot = os.path.join(REPO_ROOT, VERDICT_DIR, "codex-r3.verdict.json")
    chk("the refusal's testimony is never the path it is protecting",
        refusal_verdict_path(_prot) == _prot, False)
    chk("…and it is still a verdict file, so `read_verdicts` picks it up with no grammar change",
        os.path.basename(refusal_verdict_path(_prot)), "codex-r3.refused.verdict.json")
    chk("…at a second, distinct input, so the name is derived rather than a constant",
        os.path.basename(refusal_verdict_path("/r/v/other-r9-codex.verdict.json")),
        "other-r9-codex.refused.verdict.json")
    # ── the derived verdict path is a namespace with NO ALLOCATOR (third instance, 2026-09-23) ──
    # ⚠ THE RULE IS DRIVEN AT ALL FOUR OF ITS INPUTS, not only the one that fires. A case that
    # exercises only `tracked=True` leaves the pass-through directions unfalsifiable, and the
    # dangerous mistake in a refusal is refusing the wrong thing, not failing to refuse.
    chk("a DERIVED verdict path over a TRACKED file is refused",
        bool(verdict_collision("/r/docs/reviews/verdicts/codex-r3.verdict.json",
                               tracked=True, override_given=False)), True)
    chk("…and the refusal NAMES the path, so the reader can see which evidence was at risk",
        "codex-r3.verdict.json" in (verdict_collision(
            "/r/docs/reviews/verdicts/codex-r3.verdict.json",
            tracked=True, override_given=False) or ""), True)
    chk("…and it says what to do instead, rather than only that it refused",
        all(t in (verdict_collision("/r/v/x.verdict.json", tracked=True, override_given=False) or "")
            for t in ("--verdict", "--out")), True)
    chk("an UNTRACKED path is not a collision — a scratch verdict is free to be replaced",
        verdict_collision("/r/v/fresh.verdict.json", tracked=False, override_given=False), None)
    # ⭐ THE DELIBERATE ACT IS ALLOWED THROUGH, and this case is the one that keeps the rule honest:
    # refusing an explicit --verdict would break the legitimate replacement and teach callers to
    # route around the guard, which is how a guard becomes a prefix everyone types past.
    chk("an EXPLICIT --verdict over a tracked file is ALLOWED — chosen, not derived",
        verdict_collision("/r/v/codex-r3.verdict.json", tracked=True, override_given=True), None)
    # ⛔ CANNOT RUN IS A REFUSAL. `tracked=None` means git could not answer; passing there would
    # clobber on exactly the machines where nobody can reconstruct what was lost.
    _unk = verdict_collision("/r/v/x.verdict.json", tracked=None, override_given=False)
    chk("an UNANSWERABLE git query refuses rather than proceeding", bool(_unk), True)
    chk("…and says CANNOT RUN, so it is not read as a found collision",
        "CANNOT RUN" in (_unk or ""), True)
    chk("…but an explicit --verdict still wins over an unanswerable query",
        verdict_collision("/r/v/x.verdict.json", tracked=None, override_given=True), None)
    # ── the FETCH, in a repository this case BUILDS ────────────────────────────────────────────
    # ⛔ **THE FIRST VERSION OF THESE CASES PASSED FOR AN AMBIENT REASON AND THE HARNESS REFUSED THE
    # WHOLE SWEEP OVER IT.** They asked this repo about its own files — true only while the suite ran
    # inside this checkout. `--mutate .` stages a `copytree` with NO `.git`, so git exited 128, both
    # answers came back None, and the CONTROL was red at 100/102 before any mutation ran:
    # *every verdict below would be an artefact. Treat this as NOT CHECKED.* A red control is the
    # harness working — it refused to report coverage it had not earned.
    # ⚠ All three outcomes are driven in ONE built world, so no answer depends on where the suite is
    # standing: a file that is added, a file that is absent, and a path OUTSIDE the root (git's third
    # answer, rc=128). `git -c` keeps identity out of the user's config.
    with tempfile.TemporaryDirectory() as td:
        _repo = os.path.join(td, "r"); os.makedirs(_repo)
        _git_ok = build_probe_repo(_repo)
        # ⛔ **r4 M2 — THE `False` BRANCH HAD NO FALSIFIER, AND A try/except ALONE WOULD NOT GIVE IT
        # ONE.** The builder is a function taking the git executable's NAME so a case can hand it one
        # that does not exist; that is the only input in reach that drives the branch. Asserting it
        # here, beside the case that consumes `_git_ok`, is what turns "an environment without git
        # fails loudly" from a sentence in a commit message into something the suite can check.
        _probe2 = os.path.join(td, "probe2"); os.makedirs(_probe2)
        chk("an ABSENT git binary is REPORTED, not raised — so the guard case below is reached "
            "rather than pre-empted by a traceback",
            build_probe_repo(_probe2, git="definitely-not-git-xyzzy"), False)
        # ⛔ CANNOT RUN IS A FAILURE. If git is unavailable this must not quietly report three passes.
        chk("the throwaway repository was really built — otherwise the three cases below are void",
            _git_ok, True)
        chk("path_is_tracked says True for a file that repo really tracks",
            path_is_tracked(os.path.join(_repo, "tracked.txt"), _repo), True)
        chk("…and False for one it does not, which no constant can satisfy alongside the above",
            path_is_tracked(os.path.join(_repo, "absent.txt"), _repo), False)
        # ⛔ **THE THIRD OUTCOME, AND IT SURVIVED UNTIL A CASE DROVE IT.** git answers this question
        # three ways — 0 tracked, 1 not tracked, **128 the question was invalid** — and the two cases
        # above drive only the first two. Measured: collapsing `returncode == 1 -> False` into a bare
        # `return False` passed 101/101, so the fail-open direction of the FETCH was unfalsifiable
        # while the same direction of the RULE was covered. ⚠ A REACHABLE input, not a contrived one
        # — ⟳ **but NOT for the reason first written here (r4 M1).** That said `--out` is documented
        # to live outside the repo, where git answers 128. It cannot: `path_is_tracked` is called on
        # `vpath`, and `verdict_path` joins its result under `REPO_ROOT` for every possible `--out`,
        # so `relpath` never yields `../…`. The cause that DOES reach it was measured one commit
        # later and not back-fitted: **`REPO_ROOT` need not be a git repository at all** — the
        # mutation harness stages a `copytree` with no `.git`, and a source export has none either.
        # `git ls-files` exits 128 there, and reading that as "not tracked" is the shrug this refuses.
        # ⚠⚠ ITS FIRST FORM WAS `path_is_tracked("/etc/hosts")` AGAINST THE AMBIENT ROOT, AND THAT
        # PASSED FOR THE WRONG REASON IN HALF THE WORLDS IT RUNS IN. Inside this checkout it returned
        # None because the path is outside the repository; inside the harness's staged tree it
        # returned None because there is no repository at all. Same verdict, different cause — so the
        # case could not tell the behaviour it names from the absence of git. Driving it against a
        # root this block BUILT makes the cause the one the name claims.
        chk("…and None for a path OUTSIDE that root — git's third answer, never read as False",
            path_is_tracked(os.path.join(td, "elsewhere.txt"), _repo), None)
    # gate_ran is STATED, not derived. This case exists so that a later "simplification" which
    # computes it from exit_code fails here rather than in production: the two are independent
    # fields on purpose, and a reader must never have to infer one from the other.
    _r = verdict_record(gate_ran=False, exit_code=0, out_path="x/y.md", reason="r")
    chk("gate_ran is independent of exit_code", (_r["gate_ran"], _r["exit_code"]), (False, 0))
    chk("the verdict names the review it is about", _r["review"], "y.md")
    # ⚠ r11 Low: `VERDICT_SCHEMA` was stamped into every record and asserted by nothing — deleting
    # the field changed no case and no gate outcome, so it was an unfalsifiable constant. The
    # LITERAL is the point: comparing against `VERDICT_SCHEMA` would agree with any value it took.
    # (Full schema VALIDATION stays deferred by r5's and r6's explicit agreement; this is only the
    # narrower claim that the field is really written.)
    chk("the record states which schema it is, as a number a reader can check", _r["schema"], 2)
    with tempfile.TemporaryDirectory() as td:
        vp = os.path.join(td, "deep", "v.json")
        chk("write_verdict creates its directory and returns no error",
            write_verdict(vp, _r), None)
        with open(vp, encoding="utf-8") as f:
            chk("…and round-trips the record", json.load(f)["gate_ran"], False)
        # An unwritable path must yield an ERROR STRING, not an exception and not silence — the
        # caller turns it into exit 2 (CANNOT RUN). Silence here would recreate the whole defect:
        # a run whose testimony nobody can find.
        clash = os.path.join(td, "afile")
        with open(clash, "w", encoding="utf-8") as f:
            f.write("not a directory")
        chk("an unwritable verdict path reports an error rather than passing quietly",
            isinstance(write_verdict(os.path.join(clash, "v.json"), _r), str), True)

    # ── schema 2: WHAT was reviewed, not only THAT it was ──
    # The pair exists because either one alone is wrong about a real workflow: `head` alone accuses
    # an author who held fixes uncommitted so the reviewer would see the final state, and `dirty`
    # alone cannot place the round in the branch's history at all.
    _s = verdict_record(gate_ran=True, exit_code=0, out_path="x/y.md", reason="r",
                        head="abc123", dirty={"scripts/a.py": "b10b"})
    chk("the verdict records the commit the reviewer was handed", _s["head"], "abc123")
    # ⛔ CONTENT, NOT A PATH LIST — r1 Blocking. A path alone still matches after the file is edited
    # AGAIN, so the check subtracted it and certified content nobody reviewed. Reproduced in a
    # scratch repo; the entry is what makes "the reviewer saw THIS" answerable — and after r4 its
    # second field is an OBJECT ID: a blob for a file, a commit for a gitlink, zeros for a deletion.
    chk("…and the TREE ENTRY each uncommitted file held — mode and object id, not merely its name",
        _s["dirty"], {"scripts/a.py": "b10b"})
    # ⚠ NULL, NOT ABSENT. Both read as falsey downstream, but an absent field is indistinguishable
    # from a schema-1 verdict written before the question could be asked, and the reader must be
    # able to tell "this run could not say" from "this run predates the field".
    chk("a run that could not describe the tree says so with null, not by omitting the field",
        ("head" in _r, _r["head"]), (True, None))
    # ⛔ `None` AND `{}` ARE DIFFERENT ANSWERS — r11 Medium. `dict(dirty or {})` collapsed them, so a
    # failed measurement was byte-identical to a clean tree and the gate accused the careful author.
    _n = verdict_record(gate_ran=True, exit_code=0, out_path="x/y.md", reason="r",
                        head="abc123", dirty=None)
    chk("a null dirty map survives into the record as null, not as an empty map",
        ("dirty" in _n, _n["dirty"]), (True, None))
    _e = verdict_record(gate_ran=True, exit_code=0, out_path="x/y.md", reason="r",
                        head="abc123", dirty={})
    chk("…while an EMPTY map stays empty, because 'the tree was clean' is a real answer",
        _e["dirty"], {})
    # ⛔ THE SCOPE THE ENTRIES WERE TAKEN UNDER — r11 High. `dirty` is the whole working tree, so it
    # says what was IN the tree at dispatch, not what the prompt covered. No mechanism can close
    # that; recording the prompt lets a human see it.
    _p = verdict_record(gate_ran=True, exit_code=0, out_path="x/y.md", reason="r",
                        prompt="/tmp/r11.md")
    chk("the verdict records the prompt the run was dispatched with", _p["prompt"], "/tmp/r11.md")
    chk("…and says null rather than omitting it when there was none", _r["prompt"], None)
    # ⛔ REPOSITORY REDIRECTION IS STRIPPED — r11 High, the finding that moved a real branch ref.
    _env_in = {"GIT_DIR": "/elsewhere/.git", "GIT_WORK_TREE": "/elsewhere",
               "GIT_COMMON_DIR": "/elsewhere/.git", "GIT_INDEX_FILE": "/tmp/i", "PATH": "/bin"}
    chk("git -C means what it says: GIT_DIR, GIT_WORK_TREE and GIT_COMMON_DIR are removed",
        sorted(unredirected(_env_in)), ["GIT_INDEX_FILE", "PATH"])
    # ⚠ `.get`, NOT `[...]` — the same contract `check-review-recorded.py` records for its own
    # fixture: the mutation that adds GIT_INDEX_FILE to REDIRECT_VARS raised KeyError here, so the
    # suite CRASHED and printed no `[FAIL] <case>` line, and the harness reported the entry as
    # unattributable rather than as a kill. A case must FAIL, not crash.
    chk("…GIT_INDEX_FILE is KEPT, because reviewed_state sets it on purpose",
        unredirected(_env_in).get("GIT_INDEX_FILE"), "/tmp/i")
    chk("…and the caller's mapping is not mutated in place",
        "GIT_DIR" in _env_in, True)
    # ⛔ THE `[FAIL] <case>` CONTRACT, ASSERTED AGAINST ITS REAL READER — r13 High. This file broke
    # that contract twice (r11: `chk`; r12: the classifier printer, 21 lines away) and the r12 repair
    # was measurably unfalsifiable: reverting it left the 618-mutation gate green. These cases are
    # the falsifier, and `scripts/mutations/codex-review.json` names one of them.
    # ⚠ THE PARSER IS IMPORTED, NOT RE-DERIVED. A local copy of "truncate at the last ': got '" would
    # be a second implementation of the exact rule whose two copies caused both earlier breaks.
    _pfn = _load_fail_parser()
    chk("the FAIL line this suite prints parses back to the case name, via the harness's OWN parser",
        _pfn(case_line(False, "a plain case", 1, 2)), ["a plain case"])
    chk("…and the trailing (reason) the classifier printer adds does not disturb that",
        _pfn(case_line(False, "a classifier case", "ok", "try_next", "323 chars")),
        ["a classifier case"])
    chk("…even when the case name itself contains a colon, which truncating at the FIRST would break",
        _pfn(case_line(False, "r7: a name with a colon", 1, 2, "why")), ["r7: a name with a colon"])
    chk("a PASS line is not a case name — only a line starting with [FAIL] is",
        _pfn(case_line(True, "a passing case", 1, 1)), [])
    # The literal shape, pinned separately: the round-trip above would still hold if BOTH this line
    # and the parser moved together, and they live in different files precisely so they cannot.
    #
    # ⚠ ASSERTED AS BOOLEANS, NOT BY COMPARING THE LINE ITSELF, and that is a contract not a style
    # choice. A `[FAIL]` line quoted inside a `[FAIL]` line puts a SECOND `": got "` into the output,
    # and `parse_fail_names` truncates at the LAST one — so the case's own name would be cut at the
    # quoted text and the kill would be attributed to a name nobody wrote. The same family as the
    # `.get`-not-`[...]` rule this suite's sibling already records: a case must fail READABLY.
    chk("the line keeps the canonical shape the harness documents",
        case_line(False, "n", 1, 2, "r").endswith("[FAIL] n: got 1 want 2 (r)"), True)
    chk("…and omits the parenthesis entirely when there is no reason",
        case_line(False, "n", 1, 2).endswith("[FAIL] n: got 1 want 2"), True)
    with tempfile.TemporaryDirectory() as td:
        _head, _dirty = reviewed_state(td)
        chk("reviewed_state outside a git repository returns no head rather than raising",
            _head, None)
        # ⛔ `None`, NOT `{}` — r11 Medium. It could not look, and the empty map is reserved for
        # "it looked and the tree was clean". Downstream `classify_verdict` counts null as UNUSABLE.
        chk("…and says it could not describe the tree with null, not with an empty map",
            _dirty, None)

    # ⛔ THE SUCCESS PATH HAD NO CASE AT ALL, and `check-fixture-variation` is what said so: every
    # call passed the same `repo_root`, so no case could tell the parameter from a constant — and
    # the throwaway-index mechanism, the whole point of this function, was covered only by live
    # probes run by hand. A real repository is built here so the cases carry it instead.
    #
    # ⚠ IF GIT IS ABSENT THESE GO RED, deliberately. A case that quietly passes when it could not
    # reach its subject is the CANNOT-RUN-as-success shape this project keeps paying for.
    with tempfile.TemporaryDirectory() as td2:
        # ⛔ ISOLATED FROM THE HOST'S GIT CONFIG — r10 High, measured. Inheriting it made the suite
        # red for `commit.gpgsign=true` or a global `core.hooksPath` whose pre-commit hook fails,
        # which is a host policy and not a defect in `reviewed_state`. A guard that goes red for
        # the machine it runs on gets switched off.
        # ⛔ AND ISOLATED FROM REPOSITORY REDIRECTION — r11 High, DEMONSTRATED rather than argued.
        # r10 closed config FILES here and left `GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR` inherited,
        # so running this suite under an exported `GIT_DIR` sent the `git commit` two lines below
        # into whatever repository that variable named. During r11 that happened to the live
        # worktree: the fixture's "base" commit moved a real branch ref off its pushed merge commit.
        # `unredirected` also strips `GIT_INDEX_FILE`'s neighbours without touching it, because
        # `reviewed_state` sets that one deliberately.
        _env = dict(unredirected(), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                    GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")

        def _git(*a):
            return subprocess.run(["git", "-C", td2, *a], capture_output=True, text=True, env=_env)
        _git("init", "-q", ".")
        _git("config", "user.email", "t@example.com")
        _git("config", "user.name", "t")
        _git("config", "commit.gpgsign", "false")
        _git("config", "core.hooksPath", os.path.join(td2, "no-hooks"))
        # ⛔ `unchanged.txt` AND `gone.txt` EXIST BECAUSE TWO CASES BELOW WERE NAMED FOR SCENARIOS
        # THIS FIXTURE DID NOT CONTAIN — r11 High. "a file identical to HEAD is not recorded as
        # handed over" asserted `"unchanged" in _dirty2` over a repository holding no unchanged file
        # and no path of that name, so it was False for EVERY possible implementation: measured, a
        # mutation diffing against the empty tree (recording every tracked file whether it changed
        # or not) left the suite at 75/75. And the r3 Medium — A DELETION IS RECORDED, NOT SKIPPED —
        # had no case at all on the producer side, so restoring the skip also survived, even though
        # the CONSUMER has four cases pinning the all-zero spelling. Two halves of one wire format
        # with only one end held.
        for _n, _c in (("a.txt", "one\n"), ("unchanged.txt", "never touched\n"), ("gone.txt", "x\n")):
            with open(os.path.join(td2, _n), "w", encoding="utf-8") as f:
                f.write(_c)
        _git("add", "-A")
        _commit = _git("commit", "-q", "--no-verify", "--no-gpg-sign", "-m", "base")
        # ⚠ CHECKED, not assumed — r10 measured an IndexError three cases later when the commit had
        # silently failed. A fixture that cannot be built is CANNOT RUN and must say so here.
        chk("the case fixture's own commit succeeded (else everything below is meaningless)",
            (_commit.returncode, _commit.stderr.strip()[:60]), (0, ""))
        # modified-and-uncommitted, plus an UNTRACKED file: r2 found `git diff HEAD` missed the
        # second, and the throwaway index is what fixed it.
        with open(os.path.join(td2, "a.txt"), "w", encoding="utf-8") as f:
            f.write("two\n")
        with open(os.path.join(td2, "b.txt"), "w", encoding="utf-8") as f:
            f.write("new\n")
        os.unlink(os.path.join(td2, "gone.txt"))
        _head2, _dirty2 = reviewed_state(td2)
        _dirty2 = _dirty2 or {}
        chk("in a real repository reviewed_state reports the commit it was handed",
            bool(_head2) and len(_head2 or "") == 40, True)
        chk("…and records the MODIFIED file as a tree entry",
            bool(re.fullmatch(r"\d{6} [0-9a-f]{40}", _dirty2.get("a.txt", ""))), True)
        # ⛔ THE DESTINATION MODE, AND `\d{6}` WAS NOT ENOUGH TO SAY SO — r11 High. Raw `diff-index`
        # records are `:<srcmode> <dstmode> <srcsha> <dstsha> <status>`; for an UNTRACKED file the
        # SOURCE mode is `000000`, so reading `parts[0]` instead of `parts[1]` would record
        # `000000 <sha>` for every newly-added file — which can never equal the final tree's
        # `100644 <sha>`, so the gate would falsely fail any branch that adds a file. `000000`
        # matches `\d{6}`, which is why the old assertion survived that mutation.
        chk("…and the UNTRACKED one too, at its DESTINATION mode, not the 000000 source mode",
            _dirty2.get("b.txt", "").split()[:1], ["100644"])
        # ⛔ r3 Medium, on the producer side at last: absence is a tree state, and the zeros git
        # writes here are what the consumer's `is_absent` reads.
        chk("…and a DELETED file is recorded as the all-zero entry, not skipped",
            _dirty2.get("gone.txt", "").split()[:1], ["000000"])
        chk("…whose object id is zeros too, which is what absence compares equal to",
            set((_dirty2.get("gone.txt", "").split() or [""])[-1]), {"0"})
        # The entry must be what git ITSELF would store, or the comparison downstream is against a
        # number of our own invention.
        #
        # ⚠ `os.environ`, NOT `_env` — r11 Medium, and the fix is what caused the defect. r10 gave
        # the FIXTURE a config-neutralised environment and left the SUBJECT under the host's, so
        # this one comparison put the two configurations on opposite sides of a `==`: under a global
        # clean filter the suite went red for a HOST POLICY, which is precisely what r10 filed.
        # Measured which side is right — the subject is: `reviewed_state` records exactly what a
        # real commit stores under that filter, so the repair belongs here, in the case.
        _lstree = subprocess.run(["git", "-C", td2, "hash-object", "--", "a.txt"],
                                 capture_output=True, text=True,
                                 env=unredirected()).stdout.strip()
        chk("…and the recorded object id is the one git computes for that content",
            (_dirty2.get("a.txt", "") .split() or [""])[-1], _lstree)
        # An UNCHANGED file is not the reviewer's credit to claim — and there is now one in the
        # fixture for the assertion to be about.
        chk("a file identical to HEAD is not recorded as handed over",
            "unchanged.txt" in _dirty2, False)
        chk("…while the files that DID change are all there, so that is not vacuous emptiness",
            sorted(_dirty2), ["a.txt", "b.txt", "gone.txt"])
        # ⛔ THE INDEX IT STAGES INTO IS NOT THE REPOSITORY'S OWN — r11 High. Removing the
        # `GIT_INDEX_FILE` isolation left the suite at 75/75, and `review-method.md` hazard 2 is
        # exactly this: a concurrent agent's `git add` colliding in a shared index. Asked of the
        # FIXTURE's repository, because that is the one `reviewed_state` was pointed at — a first
        # draft asked it of the host repo, where the mutation cannot show up at all, and therefore
        # SURVIVED. A case must be about the thing the mutation moves.
        _staged = subprocess.run(["git", "-C", td2, "diff", "--cached", "--name-only"],
                                 capture_output=True, text=True, env=_env)
        chk("the repository's own index is untouched — the staging went to a throwaway one",
            _staged.stdout.strip(), "")
        # And the real repo's answer must DIFFER from the non-repo one — the parameter matters.
        chk("the repo_root argument is load-bearing: two roots, two different answers",
            _head2 == _head, False)

    # ⛔ THERE WAS AN `extra += 13` HERE AND IT WAS DOUBLE-COUNTING — r12 Medium, and it is worse
    # than filed. `chk` already does `extra += 1` on every call, so this literal added a second
    # count for the block above: 13 of the declared 92 cases had no assertion behind them, could
    # never fail, and printed nothing. The real total is `len(cases) + chk calls` = 79.
    #
    # ⚠ I GREW IT. The line read `extra += 8` before this branch and I changed it to 13 when I
    # added five fixture cases — reasoning about the literal instead of asking what incremented
    # `extra`. So the inflation is pre-existing and the round that was paying down this file's
    # measurement debt made it larger.
    #
    # ⚠ AND `check-selftest-counts.py` CANNOT SEE THIS, structurally: it compares the suite's own
    # printed denominator against the suite's own declared count, and both are authored here. A
    # literal added to `extra` moves them together, so the gate stays green over fiction. That is
    # the declared-count-drift class this project has paid for three times, one layer in.
    total = len(cases) + extra
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

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
  scripts/codex-review.py --self-test  # 63 cases

Exit codes:  0 = a real review was written   |   1 = no candidate produced one (gate did NOT run)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
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
VERDICT_SCHEMA = 1


def verdict_path(out_path: str, override: "str | None" = None) -> str:
    """Where this run's testimony goes. PURE.

    Defaults into the repo — not next to `--out`, which the documented safe call shape puts
    OUTSIDE the repo precisely so a stray write cannot reach an artifact. A verdict written there
    would be invisible to CI, which is the whole failure being fixed.
    """
    if override:
        return os.path.abspath(override)
    stem = os.path.basename(out_path)
    for ext in (".md", ".markdown", ".txt"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return os.path.join(REPO_ROOT, VERDICT_DIR, f"{stem or 'review'}.verdict.json")


def verdict_record(*, gate_ran: bool, exit_code: int, out_path: str, reason: str,
                   model: "str | None" = None, attempts: "list[str] | None" = None,
                   intrusions_seen: "list[str] | None" = None) -> dict:
    """The testimony, as data. PURE — no clock, no filesystem, so a case can assert every field.

    `gate_ran` is the load-bearing field and is stated SEPARATELY from `exit_code`, not derived
    from it by the reader. A reader that re-derives the verdict from a number is a second
    implementation of the rule, and this project has measured what those do.
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
    }


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
    ap.add_argument("--timeout", type=int, default=900, help="per-attempt timeout in seconds")
    ap.add_argument("--min-chars", type=int, default=MIN_REVIEW_CHARS,
                    help="minimum final-message length that counts as a real review")
    ap.add_argument("--allow-overwrite", action="store_true",
                    help="permit --out to replace an existing file (refused by default: backlog #68)")
    ap.add_argument("--verdict", help="write the run's verdict here "
                                      f"(default: {VERDICT_DIR}/<review-stem>.verdict.json)")
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
    vpath = verdict_path(args.out, args.verdict)

    def emit(rc: int, *, gate_ran: bool, reason: str, model=None, attempts=None, hits=None) -> int:
        rec = verdict_record(gate_ran=gate_ran, exit_code=rc, out_path=args.out, reason=reason,
                             model=model, attempts=attempts,
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
    print("[codex-review] The Codex gate did NOT run. Fall back to a Claude adversarial review "
          "and note the gap in the review doc.", file=sys.stderr)
    return emit(1, gate_ran=False,
                reason="no candidate produced a usable review", attempts=attempts, hits=hits)


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
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} ({reason})")
        if not ok:
            print(f"         expected {want}")
            failures += 1
    # ── backlog #68: the artifact-safety half ──────────────────────────────────────────────────
    extra = 0

    def chk(name: str, got, want) -> None:
        nonlocal failures
        nonlocal extra
        extra += 1
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r}")
        if not ok:
            print(f"         expected {want!r}")
            failures += 1

    # (b) The exact sentence from the round-3 brief must be caught.
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
    # gate_ran is STATED, not derived. This case exists so that a later "simplification" which
    # computes it from exit_code fails here rather than in production: the two are independent
    # fields on purpose, and a reader must never have to infer one from the other.
    _r = verdict_record(gate_ran=False, exit_code=0, out_path="x/y.md", reason="r")
    chk("gate_ran is independent of exit_code", (_r["gate_ran"], _r["exit_code"]), (False, 0))
    chk("the verdict names the review it is about", _r["review"], "y.md")
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
    extra += 8

    total = len(cases) + extra
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

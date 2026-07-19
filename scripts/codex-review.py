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
  scripts/codex-review.py --self-test

Exit codes:  0 = a real review was written   |   1 = no candidate produced one (gate did NOT run)
"""
from __future__ import annotations

import argparse
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


def classify(exit_code: int, stdout: str, message: "str | None",
             min_chars: int = MIN_REVIEW_CHARS, timed_out: bool = False) -> "tuple[str, str]":
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
                ["codex", "exec", "-m", model, "-o", msg_path, prompt],
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

    models = [args.model] if args.model else resolve_candidates()
    print(f"[codex-review] candidates: {', '.join(models)}", file=sys.stderr)

    attempts = []
    for slug in models:
        print(f"[codex-review] trying {slug} ...", file=sys.stderr)
        code, stdout, message, timed_out = run_codex(slug, prompt, args.timeout)
        outcome, reason = classify(code, stdout, message, args.min_chars, timed_out)
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
            print(f"[codex-review] OK via {slug} -> {args.out} ({reason})", file=sys.stderr)
            return 0

        print(f"[codex-review] {slug} unusable: {reason}", file=sys.stderr)

    print("\n[codex-review] FAILED — no candidate produced a usable review.", file=sys.stderr)
    print("\n".join(attempts), file=sys.stderr)
    print("[codex-review] The Codex gate did NOT run. Fall back to a Claude adversarial review "
          "and note the gap in the review doc.", file=sys.stderr)
    return 1


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
    ]
    failures = 0
    for name, code, out, msg, t_out, want in cases:
        got, reason = classify(code, out, msg, MIN_REVIEW_CHARS, t_out)
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got} ({reason})")
        if not ok:
            print(f"         expected {want}")
            failures += 1
    print(f"\n{len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

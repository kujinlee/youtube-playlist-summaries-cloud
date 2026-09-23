#!/usr/bin/env python3
"""Did this turn announce a multi-step job and then stop partway with nothing armed?

WHY THIS EXISTS (task #224 residue, user decision 2026-09-04)
--------------------------------------------------------------
`scripts/begin-plan.py` made arming the Stop guard cost one command and made that command also
print the `## ▶ STEP n of N` banner. That removes the EXCUSE for leaving the guard dormant. It
does not remove the POSSIBILITY: a banner typed by hand looks identical to the human, and the
guard stays asleep. The coupling is conventional, not mechanical.

This is the mechanical half, and it runs WARN-ONLY by default at the user's instruction — it
reports, it never blocks. Warn-only is a real risk in this repo (a warning nobody must act on has
failed here before), so the mitigation is that every firing is APPENDED TO A LOG.

⚠ THE LOG COULD NOT ANSWER "does it false-alarm?" UNTIL backlog #96 WAS FIXED, and it is the
reason the fix mattered. It recorded true partway-stops and closing-banner artifacts in the same
shape, so counting its lines yielded a rate partly manufactured by the reader. #96 is now fixed —
this guard judges the PREVIOUS completed turn — so entries written from here ARE evidence.
⚠ The log was re-baselined on 2026-09-05 for the earlier partial fix and AGAIN when #96 landed:
entries produced by a reader that could not see closing banners cannot be compared with entries
from one that can, and mixing them rebuilds the defect the row describes.

THE DISCRIMINATOR, AND WHY IT IS NOT BACKLOG #48's
---------------------------------------------------
Backlog #48 discarded a Stop hook that read the closing SENTENCE for a promise: it was satisfiable
by rewording while still doing nothing. This reads a STRUCTURAL marker that `CLAUDE.md` requires
before every step of a multi-step job and that the user visually checks for. Rewording it away
means dropping the convention they enforce — the evasion is visible to them, which is the property
the sentence-reader never had.

THE RULE, stated so its false alarms are predictable:

    warn  <=>  the HIGHEST banner in this turn is `STEP i of N` with i < N,  AND
               `.claude/executing-plan` names no plan.

Taking the HIGHEST was MEANT to make the common case quiet: a turn that announces five steps and
finishes all five emits `STEP 5 of 5`, so i == N and nothing fires, leaving exactly "announced a
multi-step job, stopped partway" — the failure measured four times (backlog #44, #53, 2026-09-03).

⚠ THAT MITIGATION DID NOT WORK UNTIL backlog #96 WAS FIXED, and the history is kept because it
explains the shape of the code. The banner that CLOSES a sequence normally sits in the turn's FINAL
assistant message, which is NOT readable while that turn is still being written. So `i < N` was true
far more often than "stopped partway" was.

MEASURED over 524 transcripts / 2104 completed turns: only 48 turns ever used a banner, and of
those, 9 hid their closing banner from a live reader while 8 had that invisibility CHANGE the
verdict — about one bannered turn in six. The race also ran the OTHER way: session 2ace2045 shows a
turn the live reader let through QUIET that was owed a warning.

THE FIX (backlog #96): this guard now judges the PREVIOUS completed turn, whose final message is
durably on disk, using the sentinel sample taken at THAT turn's own Stop. See THE JOURNAL below.

It also answers the INVERSE — a plan armed, work done in the repo, and NO banner emitted at all.
That is the direction that actually failed on 2026-09-04, when begin-plan.py printed banners to the
stdout of a Bash call, which is shown to the assistant and not reliably to the human.

WHO READS A WARNING depends on the exit code, and both readers are intended: on a BLOCKED stop the
hook exits 2 and Claude reads it (the actor, when the next banner is due); on an unblocked stop it
exits 1 and the human reads it (the auditor). See .claude/hooks/block-idle-stop.sh.

WHAT IT CANNOT SEE, stated rather than hidden:
  * ✅ THE BANNER THAT CLOSES ITS OWN TURN — FIXED (backlog #96). Kept here because the evidence
    explains the design. `run_decide` used to read the transcript of the IN-FLIGHT turn, whose final
    assistant message is not flushed when Stop hooks run. MEASURED TWICE BY TIMESTAMP: session
    `f3ab79ef` emitted `STEP 3 of 3` at 22:33:49 and the hook logged `STEP 2 of 3` in the same
    second; session `2ace2045` has `## ▶ STEP 6 of 6` timestamped 0.172s BEFORE the hook fired, and
    the hook logged `STEP 5 of 6` — so record order in the JSONL is message sequence, NOT read-time
    visibility. It now judges the PREVIOUS completed turn instead.
  * ⚠ A SESSION'S FINAL TURN, which is structural and permanent: a turn is only observable once it
    is finished, so the last one is never judged. Accepted when #96 was specified.
  * ⚠ ONE TURN OF LATENCY. The `unbannered` nudge used to arrive mid-plan, where the assistant could
    act on it, and now arrives a turn later. The mitigation is that the BLOCKING guard,
    `scripts/check-plan-progress.py`, is untouched and still fires live — only the advisory moved.
  * ⚠ DURABILITY IS STILL AN ARGUMENT, NOT A PROOF. Judging one turn back gives a full turn of
    margin instead of none, which is strictly better, but nothing here establishes that the prior
    turn is ALWAYS flushed by the next Stop. A corpus cannot settle it — a recorded transcript shows
    final file state, never what was readable at hook time. Spec falsifier F11.
  * ⚠ AN ARMED PLAN + A TURN THAT EDITS NOTHING + NO BANNER — silent in ALL THREE classes, and
    this branch is what establishes it (r1 claude M3). `unheralded` excludes it for `armed`;
    `unbannered` excludes it for `not edited`. MEASURED over the same 2,293 `cli` turns: of the
    207 large bannerless turns, **54 (26%)** edited nothing inside the repo. ⭐ The sting is that
    this branch's own measurement REFUTES `edited` — 52.2% recall, separating 2.48x against turn
    size's 5.03x — and then leaves it gating the sibling class, whose missed state is the one the
    entry below calls "the normal mode, not an edge case". Merging the two classes was considered
    and REJECTED: `unbannered` is live, with its own falsifiers and mutations, and moving it to fix
    a gap in the `not armed` half would change a rule nobody asked to change. ⚠ The placement
    comment at that branch says the gap "is entirely in the `not armed` half" — measured, it is
    not, and those 54 turns are what it is not.
  * ⚠ A TURN SPLIT BY AN INJECTED BOUNDARY, for the `unheralded` class — UNEXERCISED HERE, NOT
    IMMUNE, and the distinction is the whole point of this entry. A window opened by a record that
    `_meta_carries_a_message` accepts is a fresh turn, so a job interrupted partway yields a
    fragment holding the WORK and not the BANNER — which is exactly `unheralded`'s firing state.
    Backlog #146 measured `Another Claude session sent a message` as 332 such openers and 125
    manufactured warnings for the sibling guard. MEASURED 2026-09-22 over the 2,293 `cli` turns
    this guard actually judges: **0** of them are opened that way. All 90 message-carrying meta
    openers are `<local-command-caveat>` (a slash command the human typed), and every one opens a
    window `is_judgable` rejects for holding no assistant record. So the corpus does not produce
    the shape — and nothing in the code prevents it. `coalesce_injected` is deliberately NOT
    applied here (see check-closing-table.py); backlog #148 asks this question for the guard as a
    whole and is still open. Do not read the 0 as a property of the rule.
  * SUBAGENT edits. Measured: 0 `isSidechain:true` records across 508 transcripts for this project —
    subagent work lives in its own session file, so a coordinator turn that dispatches five
    reviewers reads as edited=False. `subagent-driven-development` is the Phase 3 DEFAULT here, so
    this is the normal mode, not an edge case.
  * work done entirely through Bash — a script that rewrites a file, a git operation. Widening to
    any mutating tool was rejected: a turn running `gh pr view` to answer a question would warn.
  * work in a git WORKTREE, which sits outside ROOT and so reads as outside the repo.
  * a SYMLINK inside the repo pointing outside it. resolve() follows the link before
    is_relative_to, so the edit reads as outside. (The converse — a link from outside INTO the
    repo — reads as inside.) Same silent-under-fire class as the two entries around it.
  * macOS CASE-INSENSITIVITY. Measured: Path.resolve() does not canonicalise case on darwin, so a
    file_path recorded with different case fails is_relative_to(ROOT) and the edit is silently
    unseen. Low probability, but it under-fires QUIETLY, which is the dangerous direction.
  * whether the work was genuinely finished. `i < N` with the job actually complete is a real false
    alarm; that is why this warns rather than blocks, and why it logs.
  * whether the banner was any GOOD. The predicate is presence, not quality.
  * the hook's RUNTIME behaviour. The reachability case is STRUCTURAL — it reads the hook as text
    and proves order in the file, nothing more.

FAILS CLOSED ON ITS OWN BLINDNESS. No transcript, an unreadable one, or zero assistant text parsed
-> exit 2 with CANNOT RUN. A check that cannot reach what it measures is never a pass (CLAUDE.md),
and "no banner found" is indistinguishable from "could not read the file" unless it says so.

Usage (the hook calls form 1):
    python3 scripts/check-banner-armed.py --decide < <stop-hook-json>
    python3 scripts/check-banner-armed.py --self-test  # 159 cases
Exit codes for --decide:  0 = nothing to say   1 = WARN (non-blocking)   2 = CANNOT RUN
"""
from __future__ import annotations

import argparse
import contextlib          # self-test only: F97b captures stderr to prove the flush note rides
import datetime as _dt
import importlib.util
import io                  # self-test only: see `contextlib` above
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import observer_log  # noqa: E402  — the ONE owner of the record grammar (backlog #166, #170)
SENTINEL = ROOT / ".claude/executing-plan"
WARN_LOG = ROOT / ".claude/banner-warnings.log"
# ⛔ A SEPARATE FILE, AND THAT IS THE POINT (backlog #97). The late flush is an OBSERVATION, not a
# warning: it fires on the ordinary case, whereas WARN_LOG's stated job (`:451-454`) is to be the
# false-alarm rate of the WARNING. Mixing them puts a line in WARN_LOG under a class that did not
# fire — which is #97's own second defect — and destroys `wc -l` as a warning count. The existing
# `.gitignore` glob `.claude/banner-warnings*.log` deliberately does NOT match this name.
FLUSH_LOG = ROOT / ".claude/banner-flush-observations.log"

QUIET, WARN, CANNOT_RUN = 0, 1, 2

_UNSET = object()   # `steps` was not consulted. Distinct from None = "unreadable".

# The banner CLAUDE.md mandates: `## ▶ STEP 3 of 6 — title`. The separator between the numbers is
# matched loosely (`of`), but the `## ▶ STEP` opener is not — a looser opener would match prose
# ABOUT the convention, and this file, the skill docs and the dashboard all discuss it.
BANNER_RE = re.compile(r"^##\s*▶\s*STEP\s+(\d+)\s+of\s+(\d+)\b", re.M)


# ── Pure core ─────────────────────────────────────────────────────────────────────────────────

class TurnWindow(NamedTuple):
    """One turn: the real-user record that OPENED it, and everything emitted after it.

    ⚠ THE OPENER IS SEPARATE FROM THE BODY, AND CARRYING IT IS NOT COSMETIC. `records_since_last_user`
    has always excluded the boundary record (`start = i + 1`), and the body must keep excluding it or
    every existing caller changes meaning. But three things need the opener's identity:
      * the journal key — the turn a sentinel sample describes (spec §3.4);
      * the log line — which turn a verdict is about, now that it is not the live one (§6);
      * falsifier F3 — that the selector names the same turn regardless of the live window's extent.
    A flat `list[dict]` can serve the body or the identity, never both. This pair serves both.

    `opener` is None only for the degenerate no-boundary window (see `windows`).
    """
    opener: dict | None
    body: list[dict]


def _is_turn_boundary(rec: dict) -> bool:
    """PURE. True iff this record is a REAL user message that starts a new turn.

    Two kinds of `user` record are not the human typing, and treating them as turn boundaries
    truncates the window:
      * a tool RESULT — without this, the window is cut at the last tool call.
      * an `isMeta` record — a skill injection, or THIS HOOK's own block feedback. Measured
        2026-09-04: the block message sat 72 records after the `STEP 2 of 4` banner for the step
        still in progress, so the banner fell out of window by construction.

    `promptSource` is deliberately NOT part of this rule. Measured over 30 transcripts: skipping
    it too collapses 142 windows to 70, and 52 of the 72 removed boundaries begin a GENUINELY NEW
    turn. A window that never resets is as wrong as one that resets too often.

    ⚠ THIS IS THE ONE PLACE THE RULE LIVES. `windows` and `records_since_last_user` both call it;
    neither restates it. A second implementation of one rule drifts — recorded, and paid for here.
    """
    if rec.get("type") != "user":
        return False
    if _is_tool_result(rec):
        return False
    if rec.get("isMeta") is True and not _meta_carries_a_message(rec):
        return False
    return True


def _parse_records(lines: list[str]) -> list[dict]:
    records = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except (ValueError, TypeError):
            continue
    return records


def windows(records: list[dict]) -> list[TurnWindow]:
    """PURE. Split records into per-turn windows on the SAME boundary rule as before.

    ⚠ THE DEGENERATE CASE IS LOAD-BEARING, and an earlier draft of the spec asserted it away.
    With NO real-user boundary at all, the previous code returned EVERY record (`start` stayed 0).
    A naive split would return `[]`, and `[-1]` would then raise IndexError *inside a Stop hook* —
    turning a warn-only observer into a traceback. Reachable: a transcript whose only `user` records
    are tool results and injected `isMeta` records has no boundary, and both exclusions are real.
    So: one window, `opener=None`, body = everything. That preserves the old semantics exactly.
    """
    bounds = [i for i, rec in enumerate(records) if _is_turn_boundary(rec)]
    if not bounds:
        return [TurnWindow(None, list(records))]
    out: list[TurnWindow] = []
    for n, b in enumerate(bounds):
        end = bounds[n + 1] if n + 1 < len(bounds) else len(records)
        out.append(TurnWindow(records[b], records[b + 1:end]))
    return out


def is_judgable(window: TurnWindow) -> bool:
    """PURE. True iff this window represents a turn the assistant actually took.

    ⛔ THE PREDICATE IS "CONTAINS AN ASSISTANT RECORD", NOT "AN ASSISTANT TEXT BLOCK", and both
    review halves rejected the text-block form independently. A turn can make only tool calls and
    emit no text — an Edit, its result, stop. Under the text-block form that window reads as empty,
    and TWO things break at once:
      * it is SKIPPED, so the plan-without-a-banner class becomes structurally unreachable for
        exactly the turns it targets — that window has edits, unticked steps and no banner, which
        is precisely `decide`'s `:309` branch;
      * it desynchronises the journal, which is keyed at every Stop — and a Stop fires for any
        assistant activity, text or not.
    "A turn happened" must mean one thing. An assistant record is what a Stop hook fires for, so
    that is the definition both the selector and the journal use.

    Slash-command shells still drop out: `/foo` and its `<local-command-stdout>` reply are two
    consecutive boundaries, so the window between them holds ZERO records — excluded for having no
    assistant activity, not for having no text.
    """
    return any(rec.get("type") == "assistant" for rec in window.body)


def judged_window(wins: list[TurnWindow]) -> TurnWindow | None:
    """PURE. The turn to judge: the last judgable window that is NOT the live one.

    ⚠ NOT "step back N from the end". The spec's earlier phrasing — *the last judgable window
    before the live one* — invites an ordinal step-back from a window whose extent is still moving
    while the turn is in flight, and that silently selects T-2 instead of T-1. The live window is
    the last one, whatever it currently contains; excluding it wholesale makes the answer
    independent of how much of it has been written (falsifier F3).

    None means NO SUBJECT — the first judgable turn of a session, or a transcript with only one
    window. That is QUIET, and must never be conflated with CANNOT RUN.
    """
    for window in reversed(wins[:-1]):
        if is_judgable(window):
            return window
    return None


def records_since_last_user(lines: list[str]) -> list[dict] | None:
    """Records emitted after the most recent REAL user message. None if unparseable.

    ⚠ NOW DELEGATES to `windows`, so the boundary rule has exactly one implementation.

    ⛔ AND THAT IS WHY THE SPEC'S F6 CANNOT BE A STANDING SELF-TEST CASE. F6 says this function
    still equals `windows(records)[-1].body`. After this refactor it is that expression, so a case
    asserting the equality compares the code to itself and can never fail — the same tautology
    F11 turned out to be (measured: 1828 windows, 0 violations, true by construction).
    F6 is therefore a ONE-TIME MIGRATION CHECK, run against the PRE-refactor implementation over
    the transcript corpus, and recorded in the commit. What stands here instead are cases asserting
    the specific documented behaviours: each exclusion, and the degenerate no-boundary window.
    """
    records = _parse_records(lines)
    if not records:
        return None
    return windows(records)[-1].body


# ⚠ r8 R8-5 (closing-table round 8), Low — THE SECOND STRING BELOW IS ALSO HARDCODED IN
# `check-closing-table._INJECTED`, FOR THE OPPOSITE PURPOSE. Here it means *this meta record IS a
# real new instruction, so KEEP the boundary*; there it means *that boundary was not a PERSON, so
# FOLD it*. Both readings are deliberate — the two guards answer different questions and are
# allowed to disagree — but if the harness ever rewords the injection, both stop matching, every
# self-test stays green, and the behaviour reverts in silence. Nothing observes the literal against
# a real transcript. ⛔ If you change this tuple, read that one.
_META_IS_REALLY_A_MESSAGE = (
    "The user sent a new message while you were working",
    "Another Claude session sent a message",
    "<local-command-caveat>",
)


def _meta_carries_a_message(rec: dict) -> bool:
    """PURE. True when an `isMeta` record is a real new instruction, not an injection.

    ⚠ `isMeta` does NOT mean "not the human typing" — measured over 700 transcripts, of the 405
    boundaries the isMeta rule removes, ~100 carry a genuine message: 30 relay the human's own text
    and 67 are a slash command they typed. Treating those as non-boundaries widens the window across
    a real turn, and the error direction is QUIETING in both branches.
    """
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content
                           if isinstance(b, dict) and b.get("type") == "text")
    return isinstance(content, str) and content.lstrip().startswith(_META_IS_REALLY_A_MESSAGE)


def texts_of(records: list[dict]) -> list[str]:
    out: list[str] = []
    for rec in records:
        if rec.get("type") == "assistant":
            out.extend(_text_blocks(rec))
    return out


_EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")


def edited_paths_of(records: list[dict]) -> list[str]:
    """Every file path an editing tool touched in this window.

    ⚠ AN EDIT THAT FAILED IS NOT WORK. A `tool_use` is an ATTEMPT; the paired `tool_result` says
    whether it landed. Measured over 40 transcripts: 238 edit tool_uses and 22 error results — a
    refused Edit ("Found 2 matches...") would otherwise read as a repo change and fire the warning
    on a turn that changed nothing, which is the cry-wolf failure this guard must not ship. An
    edit with NO paired result is COUNTED: at stop time results exist, so an unpaired one is an
    in-flight edit rather than a refused one.

    `notebook_path` is UNVERIFIED — NotebookEdit appeared 0 times across the measured corpus.
    `MultiEdit` is absent because it does not exist in this runtime (measured x0 by three
    independent reviewers).
    """
    failed: set[str] = set()
    for rec in records:
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                tid = b.get("tool_use_id")
                if isinstance(tid, str):
                    failed.add(tid)

    out: list[str] = []
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") not in _EDIT_TOOLS:
                continue
            if b.get("id") in failed:
                continue          # the edit was REFUSED — no work happened
            inp = b.get("input") or {}
            path = inp.get("file_path") or inp.get("notebook_path")
            if isinstance(path, str) and path:
                out.append(path)
    return out


# ⛔ THE THRESHOLD IS A MEASUREMENT, NOT A TASTE — and it is calibrated to the counting rule in
# `tool_uses_of` BELOW. Changing either without re-running the other makes this number meaningless.
#
# MEASURED 2026-09-22 over 803 transcripts for this project -> 2,293 MAIN-SESSION turns, of which
# 201 emitted a banner and 2,092 did not.
#
# ⚠ THE POPULATION IS `entrypoint == "cli"`, AND THE FIRST CUT OF THIS GOT IT WRONG. Subagent
# sessions live in their own files and the Stop hook never judges them, so counting them quotes a
# rate over the wrong denominator. The first attempt excluded them by a PROXY — "does the file use
# `StructuredOutput`" — which let 44 subagent turns through, because 40 `sdk-py` files happen not
# to use that tool. `entrypoint` is set by the runtime rather than chosen by me, and it separates
# the corpus exactly: `cli` holds 2,293 turns and ALL 201 banners; `sdk-py` and `sdk-cli` hold 735
# turns and ZERO. The proxy is kept in the record only because it is what a convenient exclusion
# looks like from the inside.
#
#   threshold   catches, of the 201 turns a human DID banner   fires on unbannered   rate
#      >= 20                 57.2%                                284              1 per  8.1 turns
#      >= 25                 49.8%                                207              1 per 11.1 turns
#      >= 30                 42.3%                                146              1 per 15.7 turns
#      >= 40                 31.8%                                 85              1 per 27.0 turns
#
# 25 chosen by the user 2026-09-22 from a selection card carrying this table (to within the 0.5pp
# the population correction above moved it; the correction did not change the ordering or the call).
#
# ⚠ THAT RIGHT-HAND COLUMN IS NOT A FALSE-ALARM RATE, and reading it as one is the mistake backlog
# #96 recorded against this very guard's log. `armed` state cannot be recovered from a transcript,
# so it is an UPPER BOUND on volume: an armed turn among those is caught by the `unbannered` class
# instead, and a large unbannered turn is frequently the defect itself rather than a false alarm.
#
# ⭐ WHY TURN SIZE AND NOT `edited`, which backlog #95 proposed as "most plausible": measured, only
# 52.2% of the turns a human bannered edited a repo file at all — so `edited` misses HALF the
# population it is meant to describe. This file's own docstring predicted that without quantifying
# it ("a coordinator turn that dispatches five reviewers reads as edited=False ... the normal mode,
# not an edge case"). On the corrected population turn size separates the two groups 5.03x at this
# threshold, against `edited`'s 2.48x — so it is twice the discriminator, not a marginal one.
LARGE_TURN = 25


def tool_uses_of(records: list[dict]) -> int:
    """How many tool calls this window made. The proxy for "this was a multi-step job".

    ⚠ EVERY `tool_use` COUNTS, INCLUDING ONE WHOSE RESULT WAS AN ERROR — deliberately UNLIKE
    `edited_paths_of`, which excludes refused edits because a failed edit changed no bytes. The
    question here is different: a step that was attempted and failed is still a step the reader who
    was away cannot follow. Calibrating LARGE_TURN above counted it this way, so excluding errors
    would silently move the threshold off its measurement.

    The `type == "assistant"` filter is FREE, verified rather than assumed: measured across all
    3,028 turns in the corpus, counting with and without it gives an identical number in 3,028 of
    3,028 cases. It is kept because it states where tool calls legitimately live, matching
    `texts_of` and `edited_paths_of`.
    """
    n = 0
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        n += sum(1 for b in content
                 if isinstance(b, dict) and b.get("type") == "tool_use")
    return n


def assistant_texts_since_last_user(lines: list[str]) -> list[str] | None:
    """The text half of the window. Kept because the self-test exercises it directly.

    ⚠ NOT "unchanged": the isMeta rule in records_since_last_user changes what this returns for a
    window containing a meta boundary. It is the same function of a different window.
    """
    records = records_since_last_user(lines)
    return None if records is None else texts_of(records)


def _is_tool_result(rec: dict) -> bool:
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
    return False


def _text_blocks(rec: dict) -> list[str]:
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    return [b["text"] for b in content
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]


def highest_banner(texts: list[str]) -> tuple[int, int] | None:
    """The (step, total) of the furthest-along banner emitted, or None if there was no banner.

    HIGHEST, not last: banners are emitted in order, but a reprint (`--banner`) or a correction can
    put an earlier number after a later one, and reading the last would then invent a regression.
    """
    best: tuple[int, int] | None = None
    for t in texts:
        for m in BANNER_RE.finditer(t):
            step, total = int(m.group(1)), int(m.group(2))
            if best is None or step > best[0]:
                best = (step, total)
    return best


# The log's `reason` column. ⛔ THESE ARE RETURNED BY `decide()`, NEVER RE-DERIVED FROM ITS OUTPUT,
# and that is a repair rather than a style choice. Until 2026-09-22 `run_decide` reconstructed the
# class by asking "was there a banner?" — which worked only while the two classes happened to differ
# on that question. `unbannered` and `unheralded` BOTH have `banner is None`, so the old
# reconstruction would file every `unheralded` warning as `unbannered`: verbatim backlog #97's
# second defect, which mislabelled 10 of 15 entries and contaminated the evidence base that the
# promote-to-blocking decision reads. One owner for "which class fired" is the whole fix.
REASON_UNARMED = "unarmed"          # a banner ran, nothing was armed
REASON_UNBANNERED = "unbannered"    # a plan was armed and edits happened, no banner
REASON_UNHERALDED = "unheralded"    # NEITHER armed NOR bannered, and the turn was large


def decide(texts: list[str] | None, armed: bool,
           steps=_UNSET, edited: bool = False,
           tool_uses: int = 0, paused: bool = False) -> tuple[int, str, str]:
    """-> (exit_code, message, reason). Pure: every input is passed in.

    `reason` is "" for every non-WARN verdict and one of the REASON_* constants for a WARN. It is
    returned rather than recomputed by the caller — see the constants above for what that cost once.
    """
    if texts is None:
        return CANNOT_RUN, (
            "CANNOT RUN: the stop-hook payload named no readable transcript, so this check could "
            "not look for a step banner. TREAT THIS AS NOT RUN — do not read the absence of a "
            "warning as 'nothing was announced'."), ""

    # Blindness is a property of the sentinel and the plan file, NOT of whether the assistant
    # happened to type a heading — so it is answered before the banner is even looked at.
    if armed and steps is None:
        return CANNOT_RUN, (
            "CANNOT RUN: .claude/executing-plan names a plan this check could not measure — "
            "missing, unreadable, or containing zero `- [ ]` step checkboxes — or "
            "`scripts/check-plan-progress.py`, whose checkbox rule this borrows, could not be "
            "imported. TREAT THIS AS NOT RUN — do not read the absence of a warning as 'a banner "
            "was not owed'."), ""

    banner = highest_banner(texts)
    if banner is None:
        unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
        if armed and unticked > 0 and edited:
            return WARN, (
                f"⚠ PLAN WITHOUT A BANNER — this turn edited a file in the repo with "
                f"{unticked} step(s) still unticked, and emitted no `## ▶ STEP i of N`.\n"
                "\n"
                "   The banner is the affordance: a reader who was away cannot tell what you\n"
                "   are doing from a wall of tool calls. begin-plan.py prints one to the STDOUT\n"
                "   of a Bash call, which is shown to you and NOT reliably to the human — so\n"
                "   printing it there is not emitting it. It must be in your own visible text.\n"
                "\n"
                "   If this stop is being blocked, you are reading this mid-plan: emit the\n"
                "   banner for the step you are on before continuing. If the plan is genuinely\n"
                "   waiting on in-flight work, `begin-plan.py --pause <why>` stands it down.\n"
                f"   Logged to {WARN_LOG.relative_to(ROOT)}."), REASON_UNBANNERED

        # ── THE THIRD CLASS: neither armed NOR bannered (added 2026-09-22) ───────────────────
        # The branch this guard was blind to, and the one that actually fires in practice. The two
        # older classes each require something to be PRESENT — a banner (`unarmed`) or an armed plan
        # (`unbannered`) — so a turn that did substantial work with NEITHER fell straight through to
        # QUIET. MEASURED: over the warn log's entire 76-entry history, 100% are `unarmed` and the
        # `unbannered` class has fired ZERO times, because when a plan is armed a banner generally
        # does get emitted. The real failure is a big turn with no plan and no banner, and it was
        # the one state nothing could see.
        #
        # ⚠ IT IS DELIBERATELY PLACED AFTER the armed class rather than merged with it. Merging
        # would change when `unbannered` fires — a live class with its own falsifiers and mutations
        # — to fix a gap that is entirely in the `not armed` half. Nothing above this line moved.
        if not armed and not paused and tool_uses >= LARGE_TURN:
            return WARN, (
                f"⚠ WORK WITHOUT A BANNER — this turn made {tool_uses} tool calls, armed no plan, "
                f"and emitted no `## ▶ STEP i of N`.\n"
                "\n"
                "   A reader who was away cannot tell what you were doing from a wall of tool\n"
                "   calls — that is the whole reason the banner exists. This is the state the\n"
                "   other two checks here are both structurally blind to: `unarmed` needs a\n"
                "   banner to exist and `unbannered` needs a plan to be armed, so a job with\n"
                "   NEITHER was silent until 2026-09-22.\n"
                "\n"
                "   If this was one long job, arm a plan and banner each step:\n"
                "\n"
                f"     scripts/begin-plan.py <slug> \"title|doing|why\" ...   # writes the plan AND the banner\n"
                "\n"
                "   ⚠ Printing the banner via that script is NOT emitting it — it goes to the\n"
                "   STDOUT of a Bash call, which reaches you and not reliably the human. It must\n"
                "   be in your own visible text.\n"
                "\n"
                f"   ⚠ THIS CAN BE A FALSE ALARM AND THE THRESHOLD SAYS SO: {LARGE_TURN} tool calls\n"
                "   is a PROXY for 'multi-step job', not a reading of one. A single mechanical\n"
                "   sweep can exceed it legitimately. It does not block your stop.\n"
                f"   Logged to {WARN_LOG.relative_to(ROOT)} as `{REASON_UNHERALDED}`."
            ), REASON_UNHERALDED
        return QUIET, "", ""

    step, total = banner
    if step >= total:
        return QUIET, "", ""
    # ⟳ 2026-09-22, r1 claude M2 — `or paused` IS A BEHAVIOUR CHANGE TO THE OLDEST CLASS, and it is
    # here because the message below was stating a FALSEHOOD. `_armed_from_text` maps a paused plan
    # to armed=False, so a stand-down reached this branch and emitted "⚠ BANNER WITHOUT A PLAN —
    # and .claude/executing-plan names nothing" while the sentinel named `plans/p.md`. The sibling
    # blocking guard says the opposite out loud in the same state (`check-plan-progress.py:174`
    # returns `⏸ PAUSED (<why>)`), and `_armed_from_text`'s docstring requires the two to agree —
    # they agreed on the verdict and contradicted each other in the sentence.
    #
    # ⭐ It also makes the pause excuse uniform: backlog #95's shipped fix states "`paused` now
    # stands down here as it does in the blocking guard", and until this line that was true of one
    # class out of three. This is the class holding 100% of the warn log's 76 entries, so it is the
    # one where crying wolf through a deliberate stand-down costs most.
    if armed or paused:
        return QUIET, "", ""

    return WARN, (
        f"⚠ BANNER WITHOUT A PLAN — this turn's HIGHEST VISIBLE banner is `STEP {step} of "
        f"{total}`, and .claude/executing-plan names nothing.\n"
        "\n"
        "   ⚠ THAT NUMBER MAY BE LOW, AND THIS CHECK CANNOT TELL. It cannot see the banner that\n"
        "   CLOSES a turn — it reads a transcript that is still being written (backlog #96) — so\n"
        f"   a job that announced and finished all {total} steps can look partway-done here.\n"
        "   Do NOT read this as proof that work was left unannounced. Read it only as: a\n"
        "   multi-step job ran with no plan armed.\n"
        "\n"
        "   This does not block your stop by itself. Another check may be blocking it.\n"
        "   This is the WARN-ONLY half of task #224: the Stop guard\n"
        "   (check-plan-progress.py) can only refuse a premature stop if a plan was armed, and\n"
        "   arming it is one command:\n"
        "\n"
        f"     scripts/begin-plan.py <slug> \"title|doing|why\" ...   # writes the plan AND the banner\n"
        f"     scripts/begin-plan.py --plan <existing-plan.md>      # or arm on a real plan\n"
        "\n"
        "   If the job really is finished, this is a false alarm and it has been logged as one —\n"
        f"   see {WARN_LOG.relative_to(ROOT)}. ⚠ That log MIXES real partway-stops with backlog\n"
        "   #96 artifacts and the two cannot be told apart after the fact, so it is NOT yet a\n"
        "   false-alarm rate. It was re-baselined 2026-09-05 for exactly that reason."
    ), REASON_UNARMED


def log_line(reason: str, detail: str, when: str, session: str) -> str:
    """This guard's warn payload, over the SHARED record grammar. -> `v1⇥when⇥session⇥reason⇥detail`

    `reason` discriminates the two warning classes. The banner-less class has NO banner by
    construction, so the previous shape — (step, total), written only when a banner existed —
    could never record it, and a class the log cannot express reads as never having fired.

    ⟳ **2026-09-23, backlog #166 + #170 — THE GRAMMAR MOVED TO `observer_log`, AND `session` IS NOW
    SANITISED.** It was interpolated raw here (`session or '-'`) while the sibling one file over had
    already fixed exactly that: a TAB in the Stop payload's `session_id` added a column, a newline
    added a record. Measured on this function before the change: 5 columns and 2 records.

    ⛔ **THE STALE REFERRER LIST IS GONE RATHER THAN CORRECTED.** It read *"Nothing parses this file
    (searched 2026-09-04: only this module, its self-test, a comment in block-idle-stop.sh, and
    prose in docs/dashboard-entries.md)"*. Re-measured 2026-09-22: `block-idle-stop.sh` contains
    **no** reference to this log — it names the SCRIPT, which is a different thing. The
    load-bearing half (*nothing parses this file*) held and is now verified family-wide across all
    four logs; the enumeration had expired, and an enumeration that has to be re-derived to stay
    true does not belong in a docstring.
    """
    return observer_log.record(session, reason, detail, when=when)


def flush_line(before: int, after: int, when: str, session: str) -> str:
    """One appended observation, over the same shared grammar. A DIFFERENT file.

    It carries counts rather than a `reason` because there is only one thing it can record — which
    is precisely why it must not live in the warn log, where `reason` is what tells two classes
    apart and a third value would make that column mean two different kinds of thing.

    ⚠ **THIS IS THE FOURTH PRODUCER, AND BACKLOG #166 COUNTED THREE.** It shares the two leading
    columns and diverges after them, which made it invisible to a count that keyed on the name
    `log_line`. It was injectable for the same reason the others were, and it is fixed by the same
    move — a producer is not safe because nobody thought to list it.
    """
    return observer_log.record(session, before, after, when=when)


# ── I/O shell ─────────────────────────────────────────────────────────────────────────────────

def _armed_from_text(text: str) -> bool:
    """PURE. True iff the sentinel names a plan AND has not been stood down.

    `paused:` is honoured because check-plan-progress.decide() honours it — the two must agree
    about what "armed" means, or this guard's principal firing state becomes the one documented
    escape (begin-plan.py --pause, for being legitimately blocked on in-flight work).

    ⟳ 2026-09-06, backlog #99: THE AGREEMENT STILL HOLDS AND THE OTHER GUARD GOT LOUDER. decide()
    returns WARN (3) rather than a silent ALLOW on some paused states. That is a change to what it
    SAYS, not to whether it allows, so "armed" means the same thing in both places and this
    function is unchanged. Do not read a WARN over there as a divergence from `not armed` over
    here — they are the same verdict, differently voiced.
    ⚠ 2026-09-22 — THE CONCLUSION ABOVE STILL HOLDS; ITS PREMISE MOVED, which is worth more than
    the correction. This used to say *"when a paused plan still has steps outstanding"*, and that
    state is now exit 0 and SILENT in the common case: WARN fires only when the outstanding count
    has FALLEN since the pause, or when no count was recorded. A reader who checks a derivation by
    re-reading its premise would have found a false one and a true conclusion. The premise is not
    restated here any more — `scripts/check-plan-progress.py`'s module docstring owns that table.

    ⚠ THE `":" not in line` SKIP IS LOAD-BEARING, and it is the SECOND parser problem, not a
    style choice. check-plan-progress.parse_sentinel skips any line without a colon. Without this
    line, `**paused**` (no colon) reads as key "**paused**" here and as nothing there — this guard
    would stand down while the blocking guard still blocks, suppressing the very warning that
    would explain the block. Measured 2026-09-04; the trigger is a hand-edited sentinel, which is
    what check-plan-progress's own block message tells the human to write.
    """
    named = False
    for line in text.splitlines():
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        if key == "paused":
            return False
        if key == "plan" and line.split(":", 1)[-1].strip():
            named = True
    return named


def _paused_from_text(text: str) -> bool:
    """PURE. True iff the sentinel has been deliberately stood down.

    ⛔ THIS EXISTS BECAUSE `armed` COLLAPSES TWO DIFFERENT STATES AND THE THIRD CLASS NEEDS THEM
    APART. `_armed_from_text` returns False both for "no plan at all" and for "a plan explicitly
    paused" — fine for the two older classes, which only ever fire when something is PRESENT. The
    `unheralded` class fires on ABSENCE, so without this it would warn during a deliberate stand
    down: measured before shipping, a paused sentinel plus a 30-call turn returned WARN.

    That direction matters more than it looks. Since backlog #94 `--pause` means *blocked on
    in-flight work* — waiting on a dispatched review is the standard case, and it is precisely the
    kind of turn that runs long. So the naive version cried wolf in the one state the project
    deliberately silences, which is backlog #97's failure reintroduced by the slice written to
    avoid it. Backlog #95's shipped fix says it plainly: "`paused` now stands down here as it does
    in the blocking guard."

    ⚠ THE `":" not in line` SKIP IS THE SAME LOAD-BEARING RULE as its sibling above, for the same
    measured reason — a hand-edited `**paused**` must not read as a pause here while reading as
    nothing in check-plan-progress.parse_sentinel. The two functions must agree about the grammar
    or they disagree about whether the guard is standing down.
    """
    for line in text.splitlines():
        if ":" not in line:
            continue
        if line.split(":", 1)[0].strip() == "paused":
            return True
    return False


def _paused():
    """True / False. Unreadable or absent -> False, and that is SAFE in this direction.

    A pause is an EXCUSE from warning, so failing to read one can only produce a warning that was
    not owed — never silence that was. The opposite default would let an unreadable sentinel
    suppress the class. `_armed()` already maps an unreadable sentinel to None -> CANNOT RUN, so
    the honest-blindness report is made there and is not duplicated here.
    """
    try:
        return _paused_from_text(SENTINEL.read_text())
    except (OSError, UnicodeDecodeError):
        # ⚠ ONE NAME, NOT TWO (r1 coordinator F3). `FileNotFoundError` IS an `OSError`, and listing
        # it separately here would imply a distinction that is not being drawn — `_armed()` lists
        # both precisely BECAUSE it answers them differently (absent -> False, unreadable -> None
        # -> CANNOT RUN). Here every failure collapses to the same answer, deliberately.
        return False


def _load_plan_progress():
    """Import check-plan-progress.py BY PATH — the hyphen makes it un-importable by name."""
    spec = importlib.util.spec_from_file_location(
        "_plan_progress", ROOT / "scripts" / "check-plan-progress.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/check-plan-progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for n in ("count_steps", "parse_sentinel"):
        if not hasattr(mod, n):
            raise ImportError(
                f"scripts/check-plan-progress.py no longer defines {n} — this guard borrows the "
                f"checkbox rule rather than copying it.")
    return mod


def _plan_steps():
    """-> (done, total), or None if the plan cannot be measured. Never raises `Exception`.

    None covers BOTH "no readable plan file" and "zero checkboxes parsed" — the owning guard
    treats zero checkboxes as CANNOT RUN, not as "finished", and this guard must agree.

    `except Exception` deliberately: exec_module runs arbitrary module-level code. Measured — one
    undefined name at module scope in the borrowed file escaped a narrow list as a traceback and
    exit 1, indistinguishable at the hook from a genuine warning.
    """
    try:
        mod = _load_plan_progress()
        fields = mod.parse_sentinel(SENTINEL.read_text())
        plan = (ROOT / fields["plan"]).resolve()
        done, total = mod.count_steps(plan.read_text())
        return None if total == 0 else (done, total)
    except Exception:
        return None


def _edit_inside_repo(paths: list[str], root: Path) -> bool:
    """True iff any path is a FILE inside `root` that counts as plan work.

    `is_relative_to`, never str.startswith: a sibling checkout `<root>-old` prefix-matches.
    Relative paths are REFUSED — the tool inputs record file_path but never the cwd it was
    relative to. `parts` must be NON-EMPTY, or `root` itself passes the `.git` test vacuously.
    """
    for candidate in (Path(p) for p in paths):
        if not candidate.is_absolute():
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            continue
        parts = resolved.relative_to(root).parts
        if not parts or parts[0] == ".git":
            continue
        if resolved.is_dir():
            continue          # a directory is not a file this turn edited
        return True
    return False


def _armed():
    """True / False, or None when the sentinel EXISTS but cannot be read.

    ⚠ FileNotFoundError is the normal "nothing armed" case and is False. Anything else — a
    permission error, undecodable bytes — means this check cannot reach what it measures, and the
    module docstring promises that is never a quiet pass. None is that third state; run_decide
    maps it to CANNOT RUN.
    """
    try:
        return _armed_from_text(SENTINEL.read_text())
    except FileNotFoundError:
        return False
    except (OSError, UnicodeDecodeError):
        return None


JOURNAL_DIR = ROOT / ".claude/banner-turn-state"


def _steps_to_json(steps):
    """`_UNSET` and None both store as null — the pair (armed, steps) recovers the distinction."""
    if steps is _UNSET or steps is None:
        return None
    return [steps[0], steps[1]]


def _steps_from_json(armed, raw):
    """Inverse of `_steps_to_json`, and the asymmetry is deliberate.

    `steps` is consulted ONLY when armed (`run_decide` sets `_UNSET` otherwise), so a null under
    `armed=False` means "never consulted" (`_UNSET`) while a null under `armed=True` means
    "unmeasurable" (None) — which `decide` turns into CANNOT RUN at `:298`. Collapsing them would
    convert an unreadable plan into a quiet pass.
    """
    if not armed:
        return _UNSET
    return None if raw is None else (raw[0], raw[1])


def sample_for(journal: dict | None, turn_uuid: str | None):
    """PURE. -> (armed, steps, paused) sampled at `turn_uuid`'s Stop, or None if we hold no sample.

    ⚠ `paused` DEFAULTS TO FALSE WHEN THE KEY IS ABSENT, which is exactly what a journal written
    before 2026-09-22 looks like. The cost is bounded to the single turn that straddles the
    upgrade, and it falls in the safe direction — a warning that was not owed, never silence that
    was. Reporting CANNOT RUN instead would make every session's first post-upgrade stop blind.

    Checks BOTH slots. The `prev_*` pair exists because a blocked stop re-fires this hook inside
    the SAME turn: the first Stop of turn T judges T-1 and rewrites the current slot with T, and a
    continuation Stop still needs T-1. With one slot the guard reports CANNOT RUN against a subject
    it held moments earlier — on a path check-plan-progress is DESIGNED to take.
    """
    if not journal or not turn_uuid:
        return None
    if journal.get("sampled_turn_uuid") == turn_uuid:
        armed = journal.get("armed")
        return (armed, _steps_from_json(armed, journal.get("steps")),
                bool(journal.get("paused", False)))
    if journal.get("prev_turn_uuid") == turn_uuid:
        armed = journal.get("prev_armed")
        return (armed, _steps_from_json(armed, journal.get("prev_steps")),
                bool(journal.get("prev_paused", False)))
    return None


def _late_flush(journal: dict | None, turn_uuid: str | None, seen_now: int):
    """PURE. -> (len_at_its_own_stop, len_now) when the judged turn GREW since its stop, else None.

    This is the runtime half of falsifier F11, and it exists because the corpus form could not
    fail. A recorded transcript shows final file state; it can never show what was READABLE when a
    hook ran. Comparing the count this turn had at its OWN stop against the count one stop later is
    the only way to observe a late flush from inside the guard.

    ⛔ THE COUNT IS OF ASSISTANT TEXT, NOT OF RECORDS (backlog #97). The shipped form counted every
    record, so a tool result landing after the Stop read as a late flush even when the closing
    banner had been plainly visible — ten consecutive false observations, one per turn. What is
    counted now is `len(texts_of(window))`: not a proxy for the durability question but the LITERAL
    list `decide()` consumes, so growth in it means the verdict's own input was incomplete at the
    turn's own stop, and growth outside it cannot change any verdict this guard reaches.

    ⚠ THE CALLER MUST NOT WARN ON THE RESULT. A late flush is backlog #96's own mechanism, i.e. the
    normal case; escalating it is what #97 exists to undo.

    Growth is the only direction worth reporting: a shrinking window would mean the file was
    rewritten, which is a different defect and not this one.
    """
    if not journal or not turn_uuid:
        return None
    # ⚠ THE KEYS ARE RENAMED, NOT REUSED, and the one turn of blindness is deliberate. A journal
    # written by the shipped code holds `sampled_turn_len` — an ALL-RECORDS count. Reusing the name
    # would compare that against a text count and under-report silently and forever; the rename
    # makes the stale record simply invisible, which yields silence rather than a fabrication.
    for uuid_key, len_key in (("sampled_turn_uuid", "sampled_text_len"),
                              ("prev_turn_uuid", "prev_text_len")):
        if journal.get(uuid_key) == turn_uuid:
            before = journal.get(len_key)
            if isinstance(before, int) and seen_now > before:
                return before, seen_now
            return None
    return None


def _read_journal(session_id: str) -> dict | None:
    """None when there is nothing readable — a first Stop, or an unreadable file.

    ⚠ Those two are NOT the same, and the caller separates them: no prior turn at all is QUIET
    (no subject), while a prior turn with no matching sample is CANNOT RUN.
    """
    try:
        data = json.loads((JOURNAL_DIR / f"{session_id}.json").read_text())
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _write_journal(session_id: str, record: dict) -> bool:
    """Atomic replace. -> True on success, False on any failure (never raises).

    ⚠ PER SESSION, and that is a Blocking finding from review round 1, not a nicety. One shared
    path is written by every session in the working copy — this project runs concurrent sessions
    routinely — so session B's Stop clobbers session A's sample and BOTH then report CANNOT RUN for
    as long as they overlap. A file per session also needs no read-modify-write, so two sessions
    cannot lose each other's records to a torn update.
    """
    if not session_id:
        return False
    tmp = JOURNAL_DIR / f".{session_id}.tmp"
    try:
        JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(record, indent=2, sort_keys=True))
        tmp.replace(JOURNAL_DIR / f"{session_id}.json")
        return True
    except (OSError, TypeError, ValueError):
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _log_flush(session: str, late: tuple) -> bool:
    """Append one F11 observation. -> True on success, False on any failure (never raises).

    ⚠ RETURNS the failure rather than reporting it, because the caller is the only place that knows
    whether a verdict is already being printed. Silence here would be a fail-open handler, which
    `check-ratchet-contract.py` refuses in a guard — and rightly, since the whole point of this
    record is that the durability question is answered by observation rather than by argument.
    """
    when = observer_log.now()
    try:
        FLUSH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FLUSH_LOG.open("a") as fh:
            fh.write(flush_line(late[0], late[1], when, session))
        return True
    except OSError:
        return False


def run_decide(payload: str) -> int:
    try:
        data = json.loads(payload) if payload.strip() else {}
    except (ValueError, TypeError):
        data = {}

    session_id = str(data.get("session_id", "") or "")

    # ── 1. select the judged turn ─────────────────────────────────────────────────────────────
    all_records: list[dict] | None = None
    path = data.get("transcript_path")
    if isinstance(path, str) and path:
        try:
            all_records = _parse_records(Path(path).read_text().splitlines())
        except OSError:
            all_records = None

    if not all_records:
        print("CANNOT RUN: the stop-hook payload named no readable transcript, so this check could "
              "not look for a step banner. TREAT THIS AS NOT RUN — do not read the absence of a "
              "warning as 'nothing was announced'.", file=sys.stderr)
        return CANNOT_RUN

    wins = windows(all_records)
    live = wins[-1]
    judged = judged_window(wins)

    # ── 2. sample the sentinel for the LIVE turn ──────────────────────────────────────────────
    # ⚠ THIS IS THE SAMPLE POINT THE FIX DEPENDS ON, AND IT WAS ALREADY CORRECT.
    # block-idle-stop.sh runs this guard AHEAD of check-plan-progress precisely because that
    # script UNLINKS the sentinel when the last step is ticked. So `armed_now` describes the turn
    # ENDING NOW. Until backlog #96 it was used to judge that same turn and then thrown away; it is
    # now kept for one turn, which is the entire fix.
    armed_now = _armed()
    # Sampled HERE, beside `armed_now`, so both describe the same turn. A pause read at judging
    # time would describe a different moment than the verdict it excuses.
    paused_now = _paused()
    steps_now = _plan_steps() if armed_now else _UNSET

    # ── 3. judge the PRIOR turn, using the sample taken at ITS stop ───────────────────────────
    already = _read_journal(session_id)
    judged_uuid = None if judged is None or judged.opener is None else judged.opener.get("uuid")
    code, message = QUIET, ""
    reason = ""                    # set ONLY by decide(); see REASON_* for why it is not re-derived
    steps = _UNSET                 # bound before the log block below can read it
    if judged is not None:
        if already and already.get("last_judged_uuid") == judged_uuid and judged_uuid:
            code, message = QUIET, ""        # exactly one verdict per turn (§3.4b)
        else:
            sample = sample_for(already, judged_uuid)
            if sample is None:
                code, message = CANNOT_RUN, (
                    "CANNOT RUN: this check judges the PREVIOUS completed turn, and it holds no "
                    f"record of what .claude/executing-plan said when that turn ended "
                    f"({JOURNAL_DIR.relative_to(ROOT)}). Judging it against any other turn's sample "
                    "would be a guess. TREAT THIS AS NOT RUN — do not read the absence of a warning "
                    "as 'a banner was not owed'.")
            else:
                armed_then, steps_then, paused_then = sample
                if armed_then is None:
                    # ⛔ `null` MEANS "THE SENTINEL WAS UNREADABLE WHEN THAT TURN ENDED", NOT
                    # "no plan was armed" — and None is FALSY, so passing it to decide() would make
                    # a turn we could not measure look like a turn with nothing armed, and WARN at
                    # `:331` about a plan that may well have existed. `_armed()` maps the same state
                    # to CANNOT RUN at `:486`; the journalled form must mean the same thing one turn
                    # later, or the round trip through JSON silently changes a verdict.
                    code, message = CANNOT_RUN, (
                        "CANNOT RUN: when the turn now being judged ended, .claude/executing-plan "
                        "existed but could not be read, so this check cannot tell whether a banner "
                        "was owed. TREAT THIS AS NOT RUN.")
                else:
                    texts = texts_of(judged.body)
                    edited = _edit_inside_repo(edited_paths_of(judged.body), ROOT)
                    code, message, reason = decide(
                        texts, armed_then, steps=steps_then, edited=edited,
                        tool_uses=tool_uses_of(judged.body), paused=paused_then)
                    steps = steps_then           # the log block below reads it
                    # ⛔ NOTE WHAT IS *NOT* HERE: the QUIET -> WARN promotion this shipped with
                    # (backlog #97). A late flush is backlog #96's own mechanism — the NORMAL case
                    # — so escalating it warned on ten consecutive turns, which is the cry-wolf
                    # failure #95 and #96 existed to remove. The observation is RECORDED and never
                    # changes the verdict.
                    late = _late_flush(already, judged_uuid, len(texts))
                    if late:
                        if not _log_flush(str(data.get("session_id", "")), late):
                            # ⚠ NOT SWALLOWED, AND NOT MERELY PRINTED. The hook allows a QUIET stop
                            # SILENTLY (block-idle-stop.sh:29), so stderr on a QUIET turn reaches
                            # nobody — the same "emitted, reaching nobody" defect as printing a
                            # banner to Bash stdout. Losing the record is the F11 instrument failing
                            # to run, so it is reported as CANNOT RUN, which does surface. The
                            # message says plainly that the VERDICT was sound.
                            extra = (
                                "CANNOT RUN: the late-flush observation could not be written to "
                                f"{FLUSH_LOG.name}, so falsifier F11's evidence for THIS turn is "
                                "lost. ⚠ The banner verdict itself ran and was sound — it is the "
                                "durability record that is missing. TREAT F11 AS NOT MEASURED "
                                "HERE, not the banner check.")
                            message = f"{message}\n\n   {extra}" if message else extra
                            code = CANNOT_RUN
                        elif code != QUIET:
                            # Only rides along with a warning that was going to be shown anyway.
                            # Appending it to an otherwise-silent turn would move the cry-wolf into
                            # another channel rather than removing it.
                            message = (message + "\n\n   " if message else "") + (
                                f"⚠ LATE FLUSH OBSERVED: when this turn's own stop hook ran, the "
                                f"assistant text this verdict reads held {late[0]} block(s); one "
                                f"stop later it holds {late[1]}. {late[1] - late[0]} arrived after "
                                "the hook had already read the file. That is the backlog #96 race, "
                                "measured directly — judging one turn back gave enough margin "
                                "here, but the margin is not unbounded.")

    # ── 4. WRITE the journal — unconditional, and it outranks the verdict ─────────────────────
    # A CANNOT RUN *about this turn* must still leave a usable sample for the next one, or one
    # transient fault becomes two dead turns with no path back (review r1, High). And on the first
    # judgable Stop of a session both "no subject" and a failed write are true at once — if QUIET
    # returned first, a failed write would become a QUIET PASS (review r1, Medium).
    live_uuid = None if live.opener is None else live.opener.get("uuid")
    record = {
        "sampled_turn_uuid": live_uuid,
        # ⛔ F11's ONLY POSSIBLE FALSIFIER. How much ASSISTANT TEXT this turn had WHEN ITS OWN STOP
        # RAN. One stop later the same turn is re-read; if it is now LONGER, text arrived after the
        # hook looked — a late flush, measured rather than argued. The spec's earlier F11 compared
        # transcript ORDER instead and passed 1828/1828 because `windows()` splits on order, so it
        # restated the splitter. Flush timing is not a property of a finished file: only an
        # observation taken at hook time can see it, and this is that observation.
        #
        # ⚠ `texts_of`, NOT `len(live.body)` (backlog #97). Counting every record made a trailing
        # tool result look like a late flush; this counts the exact list `decide()` consumes at
        # `:742`, so growth here means the VERDICT'S OWN INPUT was incomplete at the turn's stop.
        "sampled_text_len": len(texts_of(live.body)),
        "armed": armed_now,
        # ⛔ SAMPLED, NOT RE-READ AT JUDGING TIME, for the same reason `armed` is. The verdict is
        # about the PREVIOUS turn, so what matters is whether the plan was stood down WHEN THAT
        # TURN ENDED — resuming a plan between the two stops must not retroactively remove the
        # excuse, and pausing between them must not retroactively grant one.
        "paused": paused_now,
        "steps": _steps_to_json(steps_now),
        "prev_turn_uuid": (already or {}).get("sampled_turn_uuid"),
        "prev_armed": (already or {}).get("armed"),
        "prev_paused": (already or {}).get("paused", False),
        "prev_steps": (already or {}).get("steps"),
        # ⚠ NO CASE ASSERTS THE `or` CARRY, AND THAT IS RECORDED RATHER THAN HIDDEN (r5 Low 4).
        # Replacing the whole expression with a bare `judged_uuid` survives the suite. The carry
        # preserves the exactly-once gate across a stop that judged nothing. r5 tried and COULD NOT
        # construct a reachable input where it changes the outcome: within one session the
        # transcript only grows, so a stop that judged something is followed by stops that judge
        # something, and the states where `judged_uuid` is None AFTER a judgement — a changed
        # `transcript_path` under the same `session_id`, or an opener record with no `uuid` — are
        # not producible from the driving surface. It is kept because the cost of being wrong is
        # re-warning about a turn already warned about, and the cost of keeping it is one `or`.
        # ⛔ If a later round DOES reach it, this comment is the thing to delete, not to extend.
        "last_judged_uuid": judged_uuid or (already or {}).get("last_judged_uuid"),
    }
    if live_uuid == (already or {}).get("sampled_turn_uuid"):
        # A CONTINUATION stop inside the same turn: keep the older sample rather than shifting the
        # window, or the turn we still owe a verdict falls out of both slots.
        record["prev_turn_uuid"] = (already or {}).get("prev_turn_uuid")
        record["prev_armed"] = (already or {}).get("prev_armed")
        record["prev_paused"] = (already or {}).get("prev_paused", False)
        record["prev_steps"] = (already or {}).get("prev_steps")
        record["prev_text_len"] = (already or {}).get("prev_text_len")
    else:
        record["prev_text_len"] = (already or {}).get("sampled_text_len")
    if not _write_journal(session_id, record):
        extra = ("CANNOT RUN: the per-turn record could not be written to "
                 f"{JOURNAL_DIR.relative_to(ROOT)}, so the NEXT stop will have no sample for this "
                 "turn and cannot judge it. TREAT THAT TURN AS NOT CHECKED.")
        message = f"{message}\n\n   {extra}" if message else extra
        code = CANNOT_RUN

    if code == CANNOT_RUN:
        if message:
            print(message, file=sys.stderr)
        return CANNOT_RUN

    if armed_now is None and code == QUIET and judged is None:
        # Nothing judged AND the sentinel is unreadable: say so rather than pass quietly.
        print("CANNOT RUN: .claude/executing-plan exists but could not be read, so the sample "
              "stored for this turn is unusable. TREAT THIS AS NOT RUN.", file=sys.stderr)
        return CANNOT_RUN

    texts = texts_of(judged.body) if judged is not None else []

    if code == WARN:
        # ⛔ `reason` COMES FROM decide(). It used to be reconstructed here by asking "was there a
        # banner?", which silently became wrong the moment a THIRD class shared `banner is None`
        # with `unbannered` — see the REASON_* constants. Only `detail` is derived, and each class
        # derives its own, because the detail is the one thing that genuinely differs per class.
        banner = highest_banner(texts or [])
        if reason == REASON_UNARMED:
            # ⚠ THE `"?"` IS UNREACHABLE BY CONSTRUCTION AND IS KEPT ANYWAY, said out loud rather
            # than left for the next reader to work out (r1 coordinator F2). `decide()` returns
            # REASON_UNARMED only from the branch below `banner is not None`, and `banner` here is
            # recomputed from the SAME `judged.body`, so the two cannot disagree. It stays because
            # the alternative is `banner[0]` raising inside a Stop hook if that ever stops being
            # true — a TypeError here would surface as a broken guard, not as a missing detail.
            # It is a crash barrier, not a branch; that is why no case asserts it.
            detail = f"STEP {banner[0]} of {banner[1]}" if banner else "?"
        elif reason == REASON_UNHERALDED:
            # ⚠ AND SO IS THE `else 0` — the SECOND crash barrier in this block, declared because
            # the `"?"` eight lines up is declared and this one was not (r5 Low 5; r1 coordinator
            # F2 asked for exactly this sentence about exactly this kind of expression). `reason`
            # is non-empty only on a path where `judged is not None`, so the `else` is unreachable
            # by construction and removing it is an EQUIVALENT MUTANT, not a defect — measured at
            # 150/150. It stays so that a future path reaching here with no judged turn logs a
            # wrong count instead of raising a TypeError inside a Stop hook. No case asserts it.
            detail = f"{tool_uses_of(judged.body) if judged is not None else 0} tool calls"
        else:
            unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
            detail = f"{unticked} unticked"
        when = observer_log.now()
        try:
            WARN_LOG.parent.mkdir(parents=True, exist_ok=True)
            with WARN_LOG.open("a") as fh:
                fh.write(log_line(reason, detail, when, str(data.get("session_id", ""))))
        except OSError as e:
            # NOT swallowed: the log IS the justification for warn-only mode, so losing it is
            # part of the warning rather than a detail. Still non-blocking, still exit WARN.
            message += f"\n\n   ⚠ AND THE LOG COULD NOT BE WRITTEN ({e}) — the false-alarm " \
                       f"rate is not being recorded."

    if message:
        print(message, file=sys.stderr)
    return code


# ── Self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))
        if ok:
            print(f"  PASS  {name}")
            return
        # ⛔ THE FAILURE LINE SHAPE IS A CONTRACT WITH THE MUTATION HARNESS, NOT A STYLE CHOICE.
        # `check-plan-code.py:855-856` attributes a kill by scanning for lines that START WITH
        # "[FAIL] " and splitting on the LAST ": got ". This suite printed "  FAIL  {name}", which
        # that parser cannot see — so every mutation against this guard died while reporting
        # "matched 0 red case(s) … caught by something else: []". MEASURED 2026-09-06: the
        # `armed: null` mutation genuinely turns Cx-M2 red (90/91 on a temp copy), and the harness
        # still could not name it.
        #
        # ⚠ THIS IS THE RECORDED SHAPE *a report format is a CONTRACT*, where "the guard did not
        # fire" and "nothing could see it fire" produce identical output — it once masked three
        # real bugs behind 12 mutations reporting zero red cases. It stayed invisible here for as
        # long as this guard had no manifest, because nothing ever parsed its output.
        print(f"  [FAIL] {name}: got {ok!r} want {True!r}")

    def safe(predicate) -> bool:
        """Evaluate a predicate so a RAISE is a FAILED CASE, not an aborted run.

        ⚠ WITHOUT THIS, A KILL AND A CRASH ARE INDISTINGUISHABLE — and the crash is WORSE, because
        it also hides every case after it. MEASURED (code review r2): narrowing `_armed`'s
        `except (OSError, UnicodeDecodeError)` to `except UnicodeDecodeError` lets a PermissionError
        escape through `case(...)`, so the run aborts with ZERO `FAIL` lines printed and no
        `N/N cases passed` summary. A mutation harness grepping for `FAIL` reads that as "no case
        caught it". The same revert against the M1 fixture executes only 52 of 78 cases, silently
        dropping F6/F6b/F6c and every edited_paths_of case.

        This is the recorded *a report format is a CONTRACT* shape: "the guard did not fire" and
        "nothing could see it fire" produce the same output. Pass any predicate that can raise.
        """
        try:
            return bool(predicate())
        except Exception as exc:                      # noqa: BLE001 — a raise IS the failure here
            print(f"        (raised {type(exc).__name__}: {exc})")
            return False

    def asst(text: str) -> str:
        return json.dumps({"type": "assistant",
                           "message": {"content": [{"type": "text", "text": text}]}})

    def user(text: str) -> str:
        return json.dumps({"type": "user", "message": {"content": text}})

    def tool_result() -> str:
        return json.dumps({"type": "user", "message": {
            "content": [{"type": "tool_result", "content": "ok"}]}})

    B = "## ▶ STEP {} of {} — doing a thing"

    # ── the rule ───────────────────────────────────────────────────────────────────────────
    case("a partway banner with nothing armed WARNS",
         decide([B.format(2, 5)], armed=False)[0] == WARN)
    # ⚠ THE MESSAGE USED TO SAY "3 step(s) unannounced" AND THAT WAS A CLAIM IT COULD NOT MAKE
    # (backlog #96, option B, 2026-09-05). The closing banner is invisible to this check, so the
    # arithmetic `total - step` describes what was VISIBLE, not what was left undone — mine said
    # "1 step(s) unannounced" on a turn where zero were.
    # ⚠ THE ABSENCE ASSERTION BELOW IS NOT VACUOUS: that exact phrase was in the delivered message
    # until this commit, so the case goes red if the arithmetic is ever put back. (The recorded
    # trap is an absence assertion against a phrase the message NEVER contained; this is the
    # other kind.)
    case("...and it does NOT assert how many steps are left — it cannot know that",
         "step(s) unannounced" not in decide([B.format(2, 5)], armed=False)[1])
    case("...and it says so out loud, naming the reason rather than hedging vaguely",
         "MAY BE LOW" in decide([B.format(2, 5)], armed=False)[1]
         and "CLOSES a turn" in decide([B.format(2, 5)], armed=False)[1])
    case("...and it names the one command that fixes it",
         "begin-plan.py" in decide([B.format(2, 5)], armed=False)[1])
    case("...and it does not claim nothing is blocked — another check may be blocking",
         "does not block your stop by itself" in decide([B.format(2, 5)], armed=False)[1])
    case("the SAME turn, armed -> quiet",
         decide([B.format(2, 5)], armed=True)[0] == QUIET)
    case("a FINISHED job (i == N) -> quiet even unarmed — the main false alarm, handled",
         decide([B.format(5, 5)], armed=False)[0] == QUIET)
    case("no banner at all -> quiet (an ordinary turn is not a multi-step job)",
         decide(["just some prose, no banner here"], armed=False)[0] == QUIET)
    case("a 1-of-1 job is finished, not partway",
         decide([B.format(1, 1)], armed=False)[0] == QUIET)

    # ── HIGHEST, not last ──────────────────────────────────────────────────────────────────
    case("the HIGHEST banner decides, not the last one printed",
         decide([B.format(1, 3), B.format(3, 3), B.format(1, 3)], armed=False)[0] == QUIET)
    case("highest_banner reads across separate messages",
         highest_banner([B.format(1, 4), B.format(3, 4)]) == (3, 4))
    case("highest_banner returns None when nothing matched",
         highest_banner(["## Not a banner", "▶ STEP 2 of 3 without the heading"]) is None)
    case("prose ABOUT the convention does not match — the opener is strict",
         highest_banner(["we require `## ▶ STEP n of N` before each step",
                         "the STEP 2 of 5 banner is mandatory"]) is None)
    case("a banner must start its line, not sit mid-sentence",
         highest_banner(["as I said ## ▶ STEP 2 of 5 — nope"]) is None)
    case("a banner on a later line of the same message IS found",
         highest_banner(["intro text\n" + B.format(2, 6)]) == (2, 6))

    # ── fails closed ───────────────────────────────────────────────────────────────────────
    code, msg, _reason = decide(None, armed=False)
    case("an unreadable transcript is CANNOT RUN, never a quiet pass", code == CANNOT_RUN)
    case("...and it says TREAT THIS AS NOT RUN", "TREAT THIS AS NOT RUN" in msg)
    case("an EMPTY transcript is CANNOT RUN, not 'no banner'",
         assistant_texts_since_last_user([]) is None)

    # ── transcript windowing ───────────────────────────────────────────────────────────────
    lines = [user("go"), asst("first turn " + B.format(1, 2)), user("next"), asst("second turn")]
    case("only THIS turn is read — a banner from a previous turn is out of window",
         highest_banner(assistant_texts_since_last_user(lines) or []) is None)
    lines2 = [user("go"), asst(B.format(1, 3)), tool_result(), asst("after the tool call")]
    case("a TOOL RESULT is not a turn boundary — banners before it stay in window",
         highest_banner(assistant_texts_since_last_user(lines2) or []) == (1, 3))
    case("...which is the whole window, not just the tail",
         len(assistant_texts_since_last_user(lines2) or []) == 2)
    case("a malformed JSONL line is skipped, not fatal",
         highest_banner(
             assistant_texts_since_last_user(["{not json", user("go"), asst(B.format(2, 4))])
             or []) == (2, 4))
    case("string-form assistant content is read too",
         assistant_texts_since_last_user(
             [user("go"), json.dumps({"type": "assistant", "message": {"content": "plain"}})])
         == ["plain"])
    case("a transcript of only non-assistant records yields an empty window, not None",
         assistant_texts_since_last_user([user("go")]) == [])
    case("an empty window is QUIET, not a warning — nothing was announced",
         decide([], armed=False)[0] == QUIET)

    # ── the log ────────────────────────────────────────────────────────────────────────────
    case("the log line is tab-separated and states the state and the detail",
         log_line("unarmed", "STEP 2 of 5", "2026-09-04T07:00:00-07:00", "sess").split("\t")[2:]
         == ["sess", "unarmed", "STEP 2 of 5\n"])


    # ── the window: isMeta is not a boundary, a task notification is ───────────────────────
    def meta(text: str) -> str:
        return json.dumps({"type": "user", "isMeta": True, "message": {"content": text}})

    def notif(text: str) -> str:
        return json.dumps({"type": "user", "promptSource": "system",
                           "message": {"content": text}})

    def edit(path: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}]}})

    case("F5 an isMeta record is NOT a turn boundary — the banner stays in window",
         highest_banner(texts_of(records_since_last_user(
             [user("go"), asst(B.format(2, 4)), meta("Stop hook feedback: DO NOT STOP"),
              asst("kept working")]) or [])) == (2, 4))
    case("R6 a task notification IS a turn boundary — 52 of 72 such records begin a real turn",
         highest_banner(texts_of(records_since_last_user(
             [user("go"), asst(B.format(2, 4)), notif("<task-notification/>"),
              asst("new turn")]) or [])) is None)
    case("edited_paths_of finds an Edit's file_path in the window",
         edited_paths_of(records_since_last_user([user("go"), edit("/a/b.py")]) or [])
         == ["/a/b.py"])
    case("edited_paths_of ignores a non-editing tool",
         edited_paths_of([{"type": "assistant", "message": {"content": [
             {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}]) == [])

    # ── armed means "currently obligates a banner" ─────────────────────────────────────────
    case("R5 a paused sentinel is NOT armed — pause is the in-flight-work escape",
         _armed_from_text("plan: x.md\narmed: t\npaused: waiting on CI\n") is False)
    case("...but a plain armed sentinel still is",
         _armed_from_text("plan: x.md\narmed: t\n") is True)
    case("...and a sentinel with no plan value is not armed", _armed_from_text("armed: t\n") is False)
    case("a colon-less `paused` line is SKIPPED, so this parser agrees with parse_sentinel",
         _armed_from_text("plan: x.md\npaused\n") is True)

    # ── blindness, answered before the banner ──────────────────────────────────────────────
    case("F2 armed + unreadable plan + a banner present is still CANNOT RUN",
         decide([B.format(2, 5)], armed=True, steps=None)[0] == CANNOT_RUN)
    case("F3 armed + a plan parsing to zero checkboxes is CANNOT RUN, never quiet",
         decide([], armed=True, steps=None)[0] == CANNOT_RUN)
    case("...and it says TREAT THIS AS NOT RUN",
         "TREAT THIS AS NOT RUN" in decide([], armed=True, steps=None)[1])
    case("a PAUSED plan with an unreadable file is quiet, not CANNOT RUN — stood down",
         decide([], armed=False, steps=None)[0] == QUIET)
    case("the default _UNSET means 'not consulted' and changes nothing",
         decide([B.format(2, 5)], armed=True)[0] == QUIET)

    # ── the branch that was the point ──────────────────────────────────────────────────────
    S = (1, 4)
    case("F1 armed + work left + an edit + NO banner WARNS — the direction that failed",
         decide([], armed=True, steps=S, edited=True)[0] == WARN)
    case("...and the message hedges about blocking rather than denying it",
         "If this stop is being blocked" in decide([], armed=True, steps=S, edited=True)[1])
    case("...and it names the plan-without-banner direction",
         "PLAN WITHOUT A BANNER" in decide([], armed=True, steps=S, edited=True)[1])
    case("R1 armed + work left + NO edit -> quiet (catches `edited` hardcoded true)",
         decide([], armed=True, steps=S, edited=False)[0] == QUIET)
    case("R2 not armed + an edit -> quiet (catches dropping the armed term)",
         decide([], armed=False, steps=S, edited=True)[0] == QUIET)
    case("R4 a banner IS present -> the existing branches decide (catches a reorder)",
         decide([B.format(2, 4)], armed=True, steps=S, edited=True)[0] == QUIET)
    case("a finished plan (0 unticked) + an edit -> quiet",
         decide([], armed=True, steps=(4, 4), edited=True)[0] == QUIET)

    # ── the THIRD class: neither armed nor bannered (2026-09-22) ───────────────────────────
    # ⚠ EVERY CASE HERE PASSES `steps=_UNSET` (the default) ON PURPOSE. The class is defined on the
    # `not armed` half, and an armed sentinel with steps would route to the class above — so a case
    # that set both would pass for whichever branch happened to win, which is the ambient-reason
    # failure this repo has recorded four times on one file.
    # ⛔ THE ONE PLACE THE THRESHOLD IS WRITTEN AS A LITERAL, AND IT IS DELIBERATE. Every other
    # case derives _BIG/_SMALL from LARGE_TURN, so they all move WITH the constant and not one of
    # them can notice it changing — the recorded shape *fixing a PREMISE is not covering the
    # BRANCH*. 25 is a calibrated measurement (see the table at the constant), so altering it must
    # fail loudly rather than silently re-tune the guard.
    case("W0 the threshold is 25 — the calibrated value, pinned against a silent re-tune",
         LARGE_TURN == 25)
    # ⛔ `_BIG` IS NOT `LARGE_TURN`, AND THAT IS r4's SWEEP, NOT A STYLE CHOICE. It used to be
    # exactly the threshold — and the warning message quotes the count AND, in a different
    # sentence, the threshold ("⚠ THIS CAN BE A FALSE ALARM … {LARGE_TURN} tool calls"). With the
    # two numbers equal, the case labelled *catches a hardcoded message* was satisfied by the
    # THRESHOLD sentence, so freezing the count to any constant left it green. Offsetting `_BIG`
    # makes the count appear nowhere else in the message. W2 still probes the boundary exactly.
    _BIG, _SMALL = LARGE_TURN + 3, LARGE_TURN - 1
    case("W1 not armed + no banner + a LARGE turn WARNS — the branch that was silent",
         decide([], armed=False, tool_uses=_BIG)[0] == WARN)
    case("...and it names the work-without-banner direction",
         "WORK WITHOUT A BANNER" in decide([], armed=False, tool_uses=_BIG)[1])
    # ⛔ TWO DISTINCT INPUTS, IN ONE CASE — r5 High 1, and this case is why the property exists.
    # For three consecutive rounds a case literally named *catches a hardcoded message* was
    # satisfied BY a hardcoded message. It called the producer ONCE and asserted the literal that
    # call supplied, so the constant equal to that literal always passed. r4 tried to fix it by
    # moving `_BIG` off the threshold; that only changed WHICH constant survives — freezing the
    # count at `LARGE_TURN + 3` then passed, and `LARGE_TURN + 3` is the value r4 itself chose.
    #
    # ⭐ THE PROPERTY, which replaces the whole class rather than its instances: **a case asserting
    # a derived value must exercise its producer at two DISTINCT inputs.** No constant can satisfy
    # an assertion evaluated at two different inputs — not the threshold, not either fixture's
    # literal, not a value chosen later. Pairwise-distinct FIXTURES do not give this: that is a
    # property of having two call sites that happen to disagree, and r5 measured it holding for
    # exactly 2 of 11 derived-value sites, by coincidence of fixture design.
    _lo, _hi = LARGE_TURN + 1, LARGE_TURN + 97
    case("...and it reports the COUNT IT SAW — asserted at TWO distinct inputs, so no constant "
         "satisfies it (catches a hardcoded message, which for three rounds it did not)",
         f"{_lo} tool calls" in decide([], armed=False, tool_uses=_lo)[1]
         and f"{_hi} tool calls" in decide([], armed=False, tool_uses=_hi)[1])
    case("R5-533 the PLAN-WITHOUT-A-BANNER message reports the unticked count it was given, at "
         "two distinct inputs — nothing read this number before",
         "3 step(s) still unticked" in decide([], armed=True, steps=(1, 4), edited=True)[1]
         and "7 step(s) still unticked" in decide([], armed=True, steps=(0, 7), edited=True)[1])
    case("R5-602 the BANNER-WITHOUT-A-PLAN message reports the step AND the total it saw, at two "
         "distinct inputs — a frozen `STEP 2 of 5` tells the reader a specific false thing about "
         "their own turn, in the sentence asking them not to over-read it",
         "`STEP 7 of 8" in decide([B.format(7, 8)], armed=False)[1]
         and "`STEP 1 of 9" in decide([B.format(1, 9)], armed=False)[1])
    case("R5-607 ...and so does the `all N steps` clause further down the same message",
         "all 8 steps" in decide([B.format(7, 8)], armed=False)[1]
         and "all 9 steps" in decide([B.format(1, 9)], armed=False)[1])

    # The two PURE log producers, each at two distinct inputs. `flush_line`'s counts are the
    # evidence base for backlog #96/#97 — the case written against exactly this defect (Cx-M1)
    # pinned the STRING and left the counts and the session ambient, because its only scenario
    # supplies `fl-text`, 1 and 2 and it asserts those literals.
    case("R5-636 log_line carries the SESSION it was given, at two distinct inputs",
         log_line("unarmed", "d", "T", "sess-a").split("\t")[2] == "sess-a"
         and log_line("unarmed", "d", "T", "sess-b").split("\t")[2] == "sess-b")
    case("R5-646 flush_line carries BOTH measured counts, at two distinct input pairs — the "
         "counts ARE the evidence, and a constant pair keeps the file populated while recording "
         "nothing that was measured",
         flush_line(4, 11, "T", "s").split("\t")[-2:] == ["4", "11\n"]
         and flush_line(1, 2, "T", "s").split("\t")[-2:] == ["1", "2\n"])
    case("R5-646b ...and its session column too",
         flush_line(1, 2, "T", "sess-a").split("\t")[2] == "sess-a"
         and flush_line(1, 2, "T", "sess-b").split("\t")[2] == "sess-b")
    # ⛔ THE TIMESTAMP COLUMN, AND THE FOLD THAT ADDED THESE CASES IS WHAT EXPOSED IT.
    # `check-fixture-variation.py` went RED on this file at `02218390` and the red was committed:
    # the R5-646 cases gave `flush_line` its first DIRECT call sites, and all four passed the same
    # `'T'`, so that guard's rule — do two cases pass different values for this parameter? — had
    # something to fail on for the first time. ⚠ The two rules are NOT the same rule and neither
    # subsumes the other: it asks whether two CASES differ in a parameter, r5's property asks
    # whether ONE CASE exercises a producer at two inputs. `STEP 2 of 5` and `STEP 2 of 3` satisfy
    # the first and still let half the value be frozen, which is exactly the survivor r5 found.
    # Varying `when` satisfies the first; asserting it at two inputs satisfies the second, and the
    # column is the only thing in the observation log that orders the records.
    case("R5-646c ...and its TIMESTAMP column, which nothing read — a `when` that is the same "
         "string at every call site leaves any clause reading it unguarded",
         flush_line(1, 2, "T", "s").split("\t")[1] == "T"
         and flush_line(1, 2, "2026-09-22T13:59:00-07:00", "s").split("\t")[1]
         == "2026-09-22T13:59:00-07:00")
    case("W2 one call BELOW the threshold is quiet — the boundary is exact, not approximate",
         decide([], armed=False, tool_uses=_SMALL)[0] == QUIET)
    # ⛔ THE BOUNDARY NEEDS ITS OWN CASE, AND FIXING THE AMBIENT-CONSTANT CLASS IS WHAT TOOK IT
    # AWAY. `_BIG` used to be exactly `LARGE_TURN`, so W1 tested the `>=` edge as a side effect and
    # killed the `>=` -> `>` mutation. Offsetting `_BIG` to escape the message's threshold sentence
    # (r4) left `28 > 25` true under that mutant, and the sweep reported it as a SURVIVOR at
    # 911/912 while the suite stayed green — the THIRD time on this branch a class-fix silently
    # disarmed an existing falsifier, and the third time only the sweep saw it.
    #
    # ⭐ THE TWO PROPERTIES PULL OPPOSITE WAYS and therefore cannot share a case: the ambient-
    # constant property needs the asserted value AWAY from the threshold, the boundary falsifier
    # needs it EXACTLY ON it. W1 holds the first; this holds the second.
    case("W2b a turn AT the threshold exactly WARNS — `>=`, not `>`; the one case that pins the "
         "comparison itself, which no other case can while `_BIG` is offset",
         decide([], armed=False, tool_uses=LARGE_TURN)[0] == WARN)
    # ⛔ W3'S LABEL WAS A LIE AND THE LIE WAS LOAD-BEARING (r1 claude H1). It claimed to catch
    # "dropping the banner term" while passing `armed=True` — under which `not armed` is already
    # false, so the class cannot fire wherever the branch sits and W3 is QUIET for a reason with
    # nothing to do with banners. It is not a dead case (deleting `if armed or paused` reddens it);
    # it is MISLABELLED, and its label was the only place the banner term was claimed to be covered.
    # The recorded shape *a case can pass for an AMBIENT reason* — committed three cases after this
    # block's own opening comment warns against exactly it.
    case("W3 a large turn with a banner AND a plan armed is quiet — the ARMED term, which is what "
         "this case actually exercises",
         decide([B.format(2, 5)], armed=True, tool_uses=_BIG)[0] == QUIET)
    # ⭐ W11 IS THE REAL BANNER-TERM CASE. "no banner" is the one term of the four that is NOT
    # written in the `if`: it is carried entirely by the branch's POSITION inside `if banner is
    # None:`. Hoisting the test above `banner = highest_banner(texts)` is one edit, keeps all three
    # explicit terms, and left the suite at 131/131 — while warning "WORK WITHOUT A BANNER … and
    # emitted no `## ▶ STEP i of N`" at a turn that emitted five of them, and relabelling every
    # `unarmed` entry as `unheralded`. `armed=False` here is the whole point: the banner is then
    # the ONLY thing keeping this quiet.
    case("W11 a large UNARMED turn that CLOSED its sequence is quiet — the class is defined on "
         "`no banner`, and that term is carried only by where the branch sits",
         decide([B.format(5, 5)], armed=False, tool_uses=_BIG)[0] == QUIET)
    case("W12 ...and a large UNARMED turn stopped PARTWAY is the `unarmed` class, never this one — "
         "the hoist relabels every one of the log's 76 entries",
         decide([B.format(2, 5)], armed=False, tool_uses=_BIG)[2] == REASON_UNARMED)
    case("W4 a large turn with a plan ARMED is not this class (catches dropping `not armed`)",
         decide([], armed=True, steps=(1, 4), tool_uses=_BIG)[2] != REASON_UNHERALDED)
    case("W5 a large UNARMED turn reports THIS class, not the sibling that shares banner=None",
         decide([], armed=False, tool_uses=_BIG)[2] == REASON_UNHERALDED)
    case("W6 the armed sibling still reports ITS OWN class — the two are not merged",
         decide([], armed=True, steps=S, edited=True)[2] == REASON_UNBANNERED)
    case("W7 the bannered class still reports ITS OWN class",
         decide([B.format(2, 5)], armed=False)[2] == REASON_UNARMED)
    case("W8 every QUIET verdict carries an EMPTY reason — a class cannot be logged unfired",
         decide([], armed=False, tool_uses=_SMALL)[2] == ""
         and decide([B.format(5, 5)], armed=False)[2] == "")
    case("W9 CANNOT RUN carries an empty reason too",
         decide(None, armed=False)[2] == "" and decide([], armed=True, steps=None)[2] == "")
    # ⭐ BACKLOG #95'S OWN STATED FALSIFIER, transcribed rather than paraphrased: "a session that
    # arms a plan, edits a file inside the repo and emits no banner must WARN; a session that arms a
    # plan and spends the turn answering a question must stay QUIET." The first half is F1 above.
    # The second is here, and it is the cry-wolf direction — the one #97 shipped wrong.
    case("#95's falsifier: a turn that just ANSWERS — no edits, few calls — stays QUIET",
         decide(["here is the answer to your question"], armed=True, steps=S,
                edited=False, tool_uses=3)[0] == QUIET)
    case("...and the same answering turn is QUIET when nothing is armed either",
         decide(["here is the answer"], armed=False, tool_uses=3)[0] == QUIET)
    case("W10 the threshold is a CONSTANT the message quotes — they cannot disagree",
         str(LARGE_TURN) in decide([], armed=False, tool_uses=_BIG)[1])

    # ── the PAUSE excuse, which the first cut of this class got wrong ──────────────────────
    # ⛔ FOUND BY REVIEW BEFORE SHIPPING, AND THE SUITE DID NOT NOTICE: adding `not paused` left
    # 122/122 green, because every case above leaves `paused` at its default. A fix nothing can
    # falsify is the recorded shape *a test that cannot fail* — these are its falsifiers.
    case("P1 a PAUSED plan + a large turn is QUIET — the class stands down like its siblings",
         decide([], armed=False, tool_uses=_BIG, paused=True)[0] == QUIET)
    case("P2 ...and the SAME turn unpaused still WARNS, so the excuse is doing the work",
         decide([], armed=False, tool_uses=_BIG, paused=False)[0] == WARN)
    case("P3 a paused sentinel reads as paused",
         _paused_from_text("plan: x.md\narmed: t\npaused: waiting on CI\n") is True)
    case("P4 a plain armed sentinel is NOT paused",
         _paused_from_text("plan: x.md\narmed: t\n") is False)
    case("P5 a colon-less `paused` is SKIPPED — the same grammar the sibling parser uses, so "
         "the two cannot disagree about whether the guard stood down",
         _paused_from_text("plan: x.md\n**paused**\n") is False)
    # r1 claude L2 — P5 pins the COLON rule; nothing pinned the KEY-EQUALITY rule. Loosening `==`
    # to `.startswith` left the suite at 131/131, and a key like `paused_at:` would then stand this
    # reader down while `_armed_from_text`'s `==` keeps the plan armed — the two readers
    # disagreeing about a stand-down, which is the exact failure both docstrings cite the grammar
    # rules to prevent. Latent (no writer emits such a key) and pinned anyway, because "no writer
    # does this today" is a fact about writers, not about the rule.
    case("P10 a key that merely STARTS WITH `paused` is not a pause — the match is equality, so "
         "this reader cannot stand down over a key that leaves the sibling armed",
         _paused_from_text("plan: x.md\npaused_at: 2026-09-22\n") is False)
    # ⛔ r3 M-A — P10 PINNED ONE READER AND THE PROPERTY NEEDS BOTH. L2 named both functions in one
    # sentence and the r1 fold pinned only the one it was shown; loosening `_armed_from_text` the
    # same way produces the identical disagreement from the other side, and left the suite at
    # 138/138. Measured on `plan: plans/p.md\narmed: t\npaused_at: …`: delivered reads armed=True,
    # paused=False, verdict QUIET; the mutant reads armed=False and warns "WORK WITHOUT A BANNER …
    # armed no plan" at a turn with a plan armed. The recorded *a shim fails BOTH ways* — fixing
    # the half you were shown is instance-not-class, which is the same error this round found in
    # H-A one mechanism over.
    case("P10b ...and the SIBLING reader has the same rule — a `paused_at:` key must leave the "
         "plan ARMED, or the two disagree about a stand-down from the other side",
         _armed_from_text("plan: x.md\narmed: t\npaused_at: 2026-09-22\n") is True)
    # M2's falsifier: the pause now stands the OLDEST class down too, and the message it used to
    # emit asserted the sentinel "names nothing" while it named a plan.
    case("P11 a PARTWAY banner with a paused plan is quiet — the pause excuse reaches the "
         "`unarmed` class, not only the newest one",
         decide([B.format(2, 5)], armed=False, paused=True)[0] == QUIET)
    case("P12 ...and the SAME turn unpaused still warns, so the excuse is doing the work",
         decide([B.format(2, 5)], armed=False, paused=False)[2] == REASON_UNARMED)
    case("P6 the two sentinel readers agree on a paused file: armed False AND paused True",
         _armed_from_text("plan: x.md\npaused: why\n") is False
         and _paused_from_text("plan: x.md\npaused: why\n") is True)
    # ⚠ `is not None and …[2]`, NOT a bare `[2]` — `sample_for` returns `tuple | None`, so on a
    # None the bare form raises INSIDE the case expression, before `case()` is reached. That is a
    # kill by CRASH: it aborts the suite, every case after it silently never runs, and the harness
    # records a "kill" that names no guard — the hazard `safe()` and `_logtext()` both exist for,
    # reproduced here in three cases this branch added. The explicit test is also strictly
    # stronger: a None return is now a named red instead of a stack trace. (It was pyright that
    # pointed at these — three `reportOptionalSubscript` errors that master does not have.)
    _j = {"sampled_turn_uuid": "u", "armed": False, "steps": None, "paused": True}
    _p7 = sample_for(_j, "u")
    case("P7 sample_for carries the paused flag out of the CURRENT slot",
         _p7 is not None and _p7[2] is True)
    _p8 = sample_for({"prev_turn_uuid": "p", "prev_armed": False, "prev_steps": None,
                      "prev_paused": True}, "p")
    case("P8 ...and out of the PREVIOUS slot, which a blocked stop reads instead",
         _p8 is not None and _p8[2] is True)
    _p9 = sample_for({"sampled_turn_uuid": "u", "armed": False, "steps": None}, "u")
    case("P9 a journal written BEFORE this field existed reads as not-paused, not as a crash — "
         "the straddle turn warns rather than going silent",
         _p9 is not None and _p9[2] is False)

    case("tool_uses_of counts a tool call in an assistant record",
         tool_uses_of([{"type": "assistant", "message": {"content": [
             {"type": "tool_use", "name": "Bash", "input": {}}]}}]) == 1)
    case("tool_uses_of counts EVERY call in one record, not one per record",
         tool_uses_of([{"type": "assistant", "message": {"content": [
             {"type": "tool_use", "name": "Bash", "input": {}},
             {"type": "tool_use", "name": "Read", "input": {}}]}}]) == 2)
    case("tool_uses_of ignores text blocks",
         tool_uses_of([{"type": "assistant", "message": {"content": [
             {"type": "text", "text": "hello"}]}}]) == 0)
    case("tool_uses_of ignores a non-assistant record carrying a tool_use shape",
         tool_uses_of([{"type": "user", "message": {"content": [
             {"type": "tool_use", "name": "Bash", "input": {}}]}}]) == 0)
    case("tool_uses_of COUNTS a call whose result errored — unlike edited_paths_of, by design",
         tool_uses_of([{"type": "assistant", "message": {"content": [
             {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}},
             {"type": "user", "message": {"content": [
                 {"type": "tool_result", "tool_use_id": "t1", "is_error": True}]}}]) == 1)
    case("tool_uses_of survives a record whose content is not a list",
         tool_uses_of([{"type": "assistant", "message": {"content": "plain string"}}]) == 0)

    _r = Path("/repo")
    case("R3 an edit outside the repo does not count (the scratchpad case)",
         _edit_inside_repo(["/tmp/scratch/x.md"], _r) is False)
    # ⚠ the root MUST be Path.cwd() here. Against an arbitrary root a relative path resolves
    # outside it anyway, so the case passes with OR without the fix — measured vacuous.
    case("a relative path is REFUSED — nothing records the cwd it was relative to",
         _edit_inside_repo(["docs/x.md"], Path.cwd()) is False)
    case("a sibling checkout does not prefix-match (/repo-old is not inside /repo)",
         _edit_inside_repo(["/repo-old/x.md"], _r) is False)
    case("a .git write is not plan work", _edit_inside_repo(["/repo/.git/HEAD"], _r) is False)
    case("the repo ROOT ITSELF is not a file inside the repo (parts is empty)",
         _edit_inside_repo(["/repo"], _r) is False)
    case("...but .github IS ordinary work, not a .git write",
         _edit_inside_repo(["/repo/.github/workflows/ci.yml"], _r) is True)
    case("an ordinary repo file counts", _edit_inside_repo(["/repo/scripts/x.py"], _r) is True)

    # M1 — the None state needs a real unreadable file; asserting on _armed_from_text would
    # test the parser, not the failure mode. (First draft of this case did exactly that.)
    import tempfile as _tf1
    with _tf1.TemporaryDirectory() as _d1:
        _bad = Path(_d1) / "executing-plan"
        _bad.write_bytes(b"plan: x.md\n\xff\xfe not utf-8 \xff\n")
        _sv = SENTINEL
        globals()["SENTINEL"] = _bad
        try:
            case("M1 a sentinel that EXISTS but cannot be read is None, not a quiet False",
                 safe(lambda: _armed() is None))
            globals()["SENTINEL"] = Path(_d1) / "does-not-exist"
            case("...while a missing sentinel is the ordinary unarmed case, False",
                 safe(lambda: _armed() is False))

            # The OSError ARM (code review r2, Medium). _armed's docstring names TWO causes —
            # "a permission error, undecodable bytes" — and only the second had a case. Narrowing
            # `except (OSError, UnicodeDecodeError)` to `except UnicodeDecodeError` left the suite
            # at 75/75, and a chmod-000 sentinel then escapes as an uncaught PermissionError. That
            # traceback exits 1, which is WARN in this module's own table (:70), and the hook reads
            # only `!= "0"` — so a CRASHED guard and a genuine warning are the same event at the
            # hook. That is the exact failure _plan_steps records as measured and defends against
            # (:381-383); this sibling had the same defence held by nothing.
            # ⚠ SKIPPED AS ROOT, which can read a 000 file — the case would go vacuous, not red.
            import os as _os
            _perm = Path(_d1) / "no-read"
            _perm.write_text("plan: x.md\narmed: t\n")
            _os.chmod(_perm, 0o000)
            globals()["SENTINEL"] = _perm
            if _os.geteuid() != 0:
                case("...and a PERMISSION-DENIED sentinel is None too, not an uncaught traceback",
                     safe(lambda: _armed() is None))
            _os.chmod(_perm, 0o600)
        finally:
            globals()["SENTINEL"] = _sv
    case("M2 the blindness message names the import cause it can actually have",
         "could not be imported" in decide([], armed=True, steps=None)[1])

    # ── F4: the SIDE-EFFECT test. Round 1's H1 was that no test executed run_decide. ───────
    # ⚠ BOTH fixture repairs are required and neither works alone (measured, round 2):
    #   (i)  Path(_d).resolve() — on darwin /var is a symlink to /private/var, so an unresolved
    #        root makes every edited path fail is_relative_to and `edited` is False -> QUIET.
    #   (ii) a real scripts/check-plan-progress.py — _load_plan_progress resolves it under the
    #        PATCHED ROOT; without it exec_module raises, _plan_steps returns None, and the
    #        CANNOT_RUN hoist fires before the WARN branch.
    import shutil as _sh, tempfile as _tf
    with _tf.TemporaryDirectory() as _d:
        _fx = Path(_d).resolve()
        (_fx / ".claude").mkdir()
        (_fx / "plans").mkdir()
        (_fx / "scripts").mkdir()
        _sh.copy(ROOT / "scripts" / "check-plan-progress.py", _fx / "scripts")
        (_fx / "plans" / "p.md").write_text("- [x] one\n- [ ] two\n- [ ] three\n- [ ] four\n")
        (_fx / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")
        # ⚠ EVERY END-TO-END CASE BELOW NOW NEEDS TWO TURNS (backlog #96). The guard judges the
        # PREVIOUS completed turn against the sentinel sample taken at THAT turn's own Stop, so a
        # one-turn fixture has no subject and exercises nothing. `_drive` seeds the journal with
        # turn 1 live, then re-runs with turn 2 open so turn 1 becomes the judged turn — which is
        # exactly the sequence a real session produces.
        _tr = _fx / "t.jsonl"
        _log = _fx / ".claude/banner-warnings.log"

        def _logtext() -> str:
            """The warn log's contents, or "" when it does not exist yet.

            ⛔ NEVER `_logtext()` DIRECTLY IN A FIXTURE. A mutation that stops the guard
            logging also stops the file being created, so a bare read raises FileNotFoundError,
            which ABORTS THE WHOLE SUITE — every case after it silently never runs. MEASURED
            2026-09-06 on the `judged_window` mutation: four cases went red, the run then died,
            and F3/F9/F10/F11 never executed at all. The mutation harness recorded it as "killed",
            which is true and useless: killed BY A CRASH names no guard.
            This is the `safe()` docstring's warning reproduced one layer out, in the fixture.
            """
            return _log.read_text() if _log.exists() else ""

        def _turn(uid: str, blocks: list) -> list:
            return [json.dumps({"type": "user", "uuid": uid, "message": {"content": "go"}}),
                    json.dumps({"type": "assistant", "message": {"content": blocks}})]

        def _edit_block(path: str) -> dict:
            return {"type": "tool_use", "id": "e1", "name": "Edit", "input": {"file_path": path}}

        _UNTOUCHED = object()   # "leave the sentinel exactly as it is", distinct from "delete it"

        def _sentinel(state) -> None:
            """Put the sentinel into `state`: None deletes it, str writes it, bytes write it raw.

            ⚠ `bytes` IS NOT A CONVENIENCE. The UNREADABLE sentinel is a third state, distinct
            from both "nothing armed" and "a plan is armed", and it can only be produced by
            writing something that is not UTF-8. Without it the `before`/`after` pair could not
            reach `armed_now is None` at the JUDGING stop, which is the input r5 Medium 3 needs.
            """
            if state is _UNTOUCHED:
                return
            _s = _fx / ".claude" / "executing-plan"
            if state is None:
                _s.unlink(missing_ok=True)
            elif isinstance(state, bytes):
                _s.write_bytes(state)
            else:
                _s.write_text(state)

        def _drive(path: Path, subject: list, session: str = "s",
                   before=_UNTOUCHED, after=_UNTOUCHED) -> int:
            """Seed the journal with `subject` live, then judge it once a later turn opens.

            ⟳ r3 L-A — `before`/`after` ARE THE WHOLE HELPER NOW. A second copy of this protocol
            (`_drive_changing`) was added by the r1 fold and duplicated it line for line, differing
            only by two sentinel writes; if the drive protocol ever changed in one, the other would
            silently describe a different world while every case depending on it stayed green. One
            owner, the recorded *a second implementation of one rule DRIFTS*.

            ⛔ `before`/`after` ARE WHAT MAKE SAMPLING OBSERVABLE AT ALL. With the sentinel held in
            ONE state across both stops — which is every call that omits them — "sampled at the
            judged turn's stop" and "re-read at judging time" produce identical output, so a
            re-read passes the whole suite. Every case that pins the journal round trip must pass
            a `before`/`after` pair that DIFFER.
            """
            for stale in JOURNAL_DIR.glob("*.json"):
                stale.unlink()
            _sentinel(before)
            path.write_text("\n".join(subject))
            run_decide(json.dumps({"transcript_path": str(path), "session_id": session}))
            _sentinel(after)
            path.write_text("\n".join(subject + _turn("later", [{"type": "text", "text": "x"}])))
            return run_decide(json.dumps({"transcript_path": str(path), "session_id": session}))

        # ⛔ FLUSH_LOG IS REDIRECTED TOO, AND FORGETTING IT WOULD BE SILENT. Every self-test run
        # observes late flushes by construction (the fixtures rewrite the transcript between
        # stops), so an un-redirected constant would append to the reader's REAL observation log
        # on every suite run — including every mutation run — and quietly manufacture the very
        # evidence F11 is supposed to gather. Same class as the HOME-redirect finding.
        _saved = (ROOT, SENTINEL, WARN_LOG, FLUSH_LOG, JOURNAL_DIR)
        globals()["ROOT"] = _fx
        globals()["SENTINEL"] = _fx / ".claude/executing-plan"
        globals()["WARN_LOG"] = _fx / ".claude/banner-warnings.log"
        globals()["FLUSH_LOG"] = _fx / ".claude/banner-flush-observations.log"
        globals()["JOURNAL_DIR"] = _fx / ".claude/banner-turn-state"
        try:
            _subject = _turn("t1", [_edit_block(str(_fx / "scripts" / "x.py"))])

            # THE SEED RUN ITSELF IS A CASE: the first judgable turn has no subject, and that is
            # QUIET (not CANNOT RUN) — but it must still leave a sample, or the next stop is blind.
            for _s in (_fx / ".claude/banner-turn-state").glob("*.json"):
                _s.unlink()
            _tr.write_text("\n".join(_subject))
            _rcSeed = run_decide(json.dumps({"transcript_path": str(_tr), "session_id": "s"}))
            case("the FIRST judgable turn is QUIET (no subject) and still stores a sample",
                 _rcSeed == QUIET
                 and (_fx / ".claude/banner-turn-state" / "s.json").exists())

            _rc = _drive(_tr, _subject)
            case("F4 run_decide WARNS on the new class AND appends a line — the side effect",
                 _rc == WARN and _log.exists()
                 and _logtext().rstrip("\n").endswith("\tunbannered\t3 unticked"))

            # ⛔ THE BACKLOG #96 CASE ITSELF. A turn whose ONLY banner is its closing `n of n` was
            # warned about before this change, because the live reader could not see that message.
            # Judged one turn later it is QUIET. This is the falsifier the row named.
            (_fx / ".claude" / "executing-plan").unlink()
            _closing = _turn("c1", [{"type": "text", "text": "## ▶ STEP 3 of 3 — done"}])
            _before = _logtext() if _log.exists() else ""
            _rcC = _drive(_fx / "closing.jsonl", _closing)
            case("F1 a turn ending `STEP n of n` with nothing armed is QUIET, and logs nothing",
                 _rcC == QUIET and _logtext() == _before)
            case("F2 ...while a turn whose highest banner is BELOW its total still WARNS",
                 _drive(_fx / "partway.jsonl",
                        _turn("p1", [{"type": "text", "text": "## ▶ STEP 2 of 5 — mid"}])) == WARN)
            (_fx / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")

            # H1 — the total==0 -> CANNOT RUN mapping. ⚠ The plan must be broken BEFORE the seed
            # run: the verdict is computed from the sample taken at the judged turn's own stop, so
            # breaking it afterwards would change nothing and the case would pass vacuously.
            (_fx / "plans" / "p.md").write_text("just prose, no checkboxes at all\n")
            _before = _logtext()
            _rc0 = _drive(_tr, _subject)
            case("H1 a plan with ZERO checkboxes is CANNOT RUN through run_decide, not quiet",
                 _rc0 == CANNOT_RUN)
            case("...and nothing is logged for a run that could not measure",
                 _logtext() == _before)
            (_fx / "plans" / "p.md").write_text("- [x] one\n- [ ] two\n- [ ] three\n- [ ] four\n")

            # M5 — spec R3 at the WIRING, not just the predicate: `edited` hardcoded True in
            # run_decide would pass the old predicate-level case and fail this one.
            _before = _logtext()
            _rcO = _drive(_fx / "outside.jsonl",
                          _turn("o1", [_edit_block("/tmp/scratch/not-in-repo.md")]))
            case("M5 an edit OUTSIDE the repo stays QUIET through run_decide, and logs nothing",
                 _rcO == QUIET and _logtext() == _before)

            # F9 — a BLOCKED stop re-fires this hook inside the same turn. The judged turn must get
            # exactly ONE verdict, and must not fall out of both journal slots (review r1 Blocking).
            for _s in (_fx / ".claude/banner-turn-state").glob("*.json"):
                _s.unlink()
            _tr9 = _fx / "blocked.jsonl"
            _tr9.write_text("\n".join(_subject))
            run_decide(json.dumps({"transcript_path": str(_tr9), "session_id": "s9"}))
            _tr9.write_text("\n".join(_subject + _turn("live9", [{"type": "text", "text": "a"}])))
            _first = run_decide(json.dumps({"transcript_path": str(_tr9), "session_id": "s9"}))
            _logged_once = _logtext()
            _tr9.write_text("\n".join(_subject + _turn("live9", [{"type": "text", "text": "a"}])
                                      + [json.dumps({"type": "assistant", "message": {
                                          "content": [{"type": "text", "text": "continued"}]}})]))
            _second = run_decide(json.dumps({"transcript_path": str(_tr9), "session_id": "s9"}))
            case("F9 a continuation stop issues NO second verdict for a turn already judged",
                 _first == WARN and _second == QUIET and _logtext() == _logged_once)

            # F10 — two sessions in one working copy must not clobber each other's samples.
            #
            # ⛔ THIS CASE WAS VACUOUS UNTIL 2026-09-06 AND THE MUTATION HARNESS PROVED IT.
            # Both sessions used the SAME opener uuid, so a shared journal file was undetectable:
            # session B's record carried the same key session A was about to look for, A found a
            # "matching" sample, and the case passed while the defect was fully present. MEASURED —
            # with the per-session path mutated away (BOTH the read and the write, which is the
            # realistic regression), F10 stayed green and only an unrelated case went red.
            #
            # ⚠ Mutating the WRITE path alone hides this: reads then look for `<session>.json`,
            # find nothing, and everything fails loudly for the wrong reason. A one-sided mutation
            # made the case look load-bearing. The turn uuids must DIFFER, or "we kept our own
            # sample" and "we read someone else's identical-looking one" are the same observation.
            for _s in (_fx / ".claude/banner-turn-state").glob("*.json"):
                _s.unlink()
            _trA, _trB = _fx / "a.jsonl", _fx / "b.jsonl"
            _subjA = _turn("uA", [_edit_block(str(_fx / "scripts" / "x.py"))])
            _subjB = _turn("uB", [_edit_block(str(_fx / "scripts" / "y.py"))])
            # ⚠ SESSION B MUST STOP TWICE, and that is the second thing this case got wrong.
            # With a SHARED file and B stopping once, B reads A's record and faithfully carries
            # `uA` into `prev_turn_uuid` — so A still finds its sample in the prev slot and judges
            # correctly. The `prev_*` pair, which exists to fix round 1's BLOCKED-STOP Blocking,
            # therefore MASKS round 1's CONCURRENCY Blocking. One fix disarmed the other's
            # falsifier, and only the mutation harness could see it.
            # Two stops from B push `uA` out of BOTH slots, which is what losing a sample means.
            _trA.write_text("\n".join(_subjA))
            _trB.write_text("\n".join(_subjB))
            run_decide(json.dumps({"transcript_path": str(_trA), "session_id": "sA"}))
            run_decide(json.dumps({"transcript_path": str(_trB), "session_id": "sB"}))
            _trB.write_text("\n".join(_subjB + _turn("lB", [{"type": "text", "text": "y"}])))
            run_decide(json.dumps({"transcript_path": str(_trB), "session_id": "sB"}))
            _trA.write_text("\n".join(_subjA + _turn("lA", [{"type": "text", "text": "x"}])))
            case("F10 a second session's stop does NOT cost the first its sample",
                 run_decide(json.dumps({"transcript_path": str(_trA),
                                        "session_id": "sA"})) == WARN)

            # ── F11: the LATE FLUSH, observed rather than argued ──────────────────────────────
            # ⛔ THE OLD F11 COULD NOT FAIL. It asserted the judged window's last record precedes
            # the live window's first — true BY CONSTRUCTION, because windows() splits on record
            # order. Measured over the corpus: 1828 windows, 0 violations, and it would have
            # reported 0 violations against a completely broken guard. What follows is the only
            # form that can fail: the count this turn had at ITS OWN stop, versus one stop later.
            # ⛔ AND THE EXIT CODE IS NO LONGER WHAT F11 READS (backlog #97). The shipped form
            # asserted `grow=True -> WARN` against `grow=False -> QUIET`. Dropping the escalation
            # makes BOTH sides QUIET, so that pair would assert nothing — F11 vacuous for the THIRD
            # time, after being a tautology in spec v2 and v3. Note the recurring shape: each time,
            # the assertion had re-anchored onto something that could not vary. It now reads the
            # OBSERVATION RECORD, which is the only thing the fix leaves varying.
            (_fx / ".claude" / "executing-plan").unlink()
            _flush = _fx / ".claude/banner-flush-observations.log"

            def _flushtext() -> str:
                """The observation log's contents, or "" when it does not exist yet.

                ⛔ SAME TRAP AS `_logtext`: a mutation that stops the guard recording also stops
                the file being created, so a bare read would raise FileNotFoundError and abort the
                whole suite — killed by a crash, naming no guard.
                """
                return _flush.read_text() if _flush.exists() else ""

            def _flush_scenario(session: str, grow: str, pad: int = 0) -> tuple:
                """-> (exit code, observation lines added, warn lines added).

                `pad` adds N extra PLAIN-PROSE text blocks to the judged turn and N more to what
                arrives late, moving the observed pair from (1, 2) to (1+pad, 2+2*pad) — so the
                three numbers in the LATE FLUSH note (before, after, and their difference) all
                change together. It exists because the note was asserted only by F97b, at the one
                scenario this helper could produce, which made `1 / 2 / 1` a constant that
                satisfied the only case reading it (r5 High 1). Prose carries no banner, so the
                highest banner and therefore the VERDICT are unchanged by padding.

                `grow` selects WHAT arrives after the turn's own stop:
                  'text'  — a closing assistant banner (a real late flush)
                  'none'  — nothing (the control: the check must not fire unconditionally)
                  'tool'  — only a tool RESULT, which is a `user` record and so lands inside the
                            same window without being a boundary. This is the live false positive:
                            record count grows, assistant text does not.
                  'plain' — closing assistant text with NO banner at all. This is the exact shape
                            of the ten `unbannered / 0 unticked` lines measured on master.
                """
                for _s in JOURNAL_DIR.glob("*.json"):
                    _s.unlink()
                before_obs = len(_flushtext().splitlines())
                before_warn = len(_logtext().splitlines())
                trf = _fx / f"flush-{session}.jsonl"
                lead = ("just prose" if grow == "plain" else "## ▶ STEP 2 of 3 — mid")
                # ⚠ Only 'text' closes the sequence. 'warnable' grows by text that carries NO
                # banner, so the highest banner stays 2 of 3 and decide() still warns — which is
                # the whole point of that case: a real warning and an observation at once.
                tail = ("more prose" if grow in ("plain", "warnable")
                        else "## ▶ STEP 3 of 3 — done")
                _pad = [{"type": "text", "text": f"pad {i}"} for i in range(pad)]
                partial = _turn("f1", [{"type": "text", "text": lead}] + _pad)
                closing = json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "text", "text": tail}] + _pad}})
                tool_result = json.dumps({"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "tr1", "content": "ok"}]}})
                # What its OWN stop saw: everything except whatever is due to arrive late.
                seeded = (partial if grow in ("text", "plain", "warnable")
                          else partial + [closing])
                trf.write_text("\n".join(seeded))
                run_decide(json.dumps({"transcript_path": str(trf), "session_id": session}))
                grown = partial + [closing] + ([tool_result] if grow == "tool" else [])
                trf.write_text("\n".join(grown + _turn("f2", [{"type": "text", "text": "x"}])))
                rc = run_decide(json.dumps({"transcript_path": str(trf), "session_id": session}))
                return (rc,
                        len(_flushtext().splitlines()) - before_obs,
                        len(_logtext().splitlines()) - before_warn)

            case("F11a a judged turn whose ASSISTANT TEXT grew records ONE observation, "
                 "stays QUIET, and warns NOT AT ALL",
                 safe(lambda: _flush_scenario("fl-text", "text") == (QUIET, 1, 0)))
            # ⚠ READS THE LOG LEFT BY THE CASE ABOVE — it must stay directly beneath it.
            # Cx-Medium (code review r1) — F11a COUNTS the observation and never reads it, so a
            # `flush_line` that returned a constant string passed 94/94 on a mutated copy. That is
            # the recorded rule *a guard's own output is a CONTRACT with whatever parses it*: the
            # counts ARE the evidence, and a line that has lost them records that something
            # happened while destroying what was measured. The judged turn held ONE text block at
            # its own stop and TWO one stop later, so those are the values the line must carry.
            case("Cx-M1 ...and the observation LINE carries the measured counts, not just a line",
                 safe(lambda: _flushtext().rstrip("\n").split("\n")[-1].split("\t")[-3:]
                      == ["fl-text", "1", "2"]))
            case("F11b a turn that did NOT grow records nothing — the check is not vacuous",
                 safe(lambda: _flush_scenario("fl-none", "none") == (QUIET, 0, 0)))
            case("F11c growth by a TOOL RESULT alone records nothing — the live false positive",
                 safe(lambda: _flush_scenario("fl-tool", "tool") == (QUIET, 0, 0)))
            case("F97a an unarmed BANNERLESS turn whose text grew adds NO warn-log line — "
                 "the ten measured `unbannered / 0 unticked` lines cannot recur",
                 safe(lambda: _flush_scenario("fl-plain", "plain") == (QUIET, 1, 0)))

            # F97b — a REAL warning and a late flush in the same turn. The warning must keep its
            # own true reason, and the flush note must ride along in the message rather than
            # replacing or renaming it. `grow='text'` leaves the highest banner at 2 of 3 only
            # because the late record IS the closing banner; here the late text carries no banner,
            # so decide() still sees an incomplete sequence with nothing armed.
            _errbuf = io.StringIO()
            with contextlib.redirect_stderr(_errbuf):
                _rcF = _flush_scenario("fl-warn", "warnable")
            case("F97b a real warning and a late flush coexist: the warning keeps its own reason "
                 "and the flush note rides along in the message",
                 _rcF[0] == WARN and _rcF[1] == 1 and _rcF[2] == 1
                 and _logtext().rstrip("\n").endswith("\tunarmed\tSTEP 2 of 3")
                 and "LATE FLUSH OBSERVED" in _errbuf.getvalue())

            # ⛔ THE NOTE'S THREE COUNTS — r5 High 1, the second integration site, and the same
            # shape as Cx-M1 one layer out. F97b is the ONLY case that surfaces this note, and it
            # asserted that the note APPEARS, never what it says. The helper produced exactly one
            # warnable scenario, whose numbers are 1, 2 and 1, so freezing the note at
            # `held 1 block(s) … holds 2. 1 arrived after` satisfied the only case reading it. The
            # note is the reader's own account of backlog #96's race, measured directly; frozen,
            # it reports a race that did not happen at the size it did not happen at.
            #
            # `pad=2` drives the SAME code at 3 / 6 / 3. No constant satisfies both, in any one of
            # the three slots — the difference is asserted too, because `{late[1] - late[0]}` is a
            # third producer and 2 - 1 == 1 would have let `1` stand in for it.
            _errbuf2 = io.StringIO()
            with contextlib.redirect_stderr(_errbuf2):
                _rcF2 = _flush_scenario("fl-warn2", "warnable", pad=2)
            case("R5-1051 the LATE FLUSH note reports the counts it MEASURED — driven at two "
                 "distinct scenarios (1/2/1 and 3/6/3), so no constant satisfies any of its "
                 "three numbers",
                 _rcF2[0] == WARN and _rcF2[1] == 1
                 and "held 1 block(s); one stop later it holds 2. 1 arrived after"
                     in _errbuf.getvalue()
                 and "held 3 block(s); one stop later it holds 6. 3 arrived after"
                     in _errbuf2.getvalue())

            # F97c (author self-review) — THE NEW ERROR PATH HAD NO FALSIFIER, while the sibling
            # journal-write failure has had one since round 1 (F7). The asymmetry is the finding:
            # this slice ADDED a failure mode and asserted nothing about it. It matters more than
            # it looks, because the hook allows a QUIET stop SILENTLY, so "the instrument could not
            # record" is invisible unless the exit code carries it.
            _blocker = _fx / "not-a-dir"
            _blocker.write_text("a FILE where the log's parent directory would have to be, so "
                                "mkdir raises and the append cannot happen")
            _savedflush = globals()["FLUSH_LOG"]
            globals()["FLUSH_LOG"] = _blocker / "obs.log"
            try:
                _rcU2 = safe(lambda: _flush_scenario("fl-unwritable", "text")[0] == CANNOT_RUN)
            finally:
                globals()["FLUSH_LOG"] = _savedflush
            case("F97c an UNWRITABLE observation log is CANNOT RUN, never silence — the verdict "
                 "was sound but F11's evidence for that turn is gone",
                 _rcU2)
            (_fx / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")

            # Cx-M2 (code review r2) — the FOLD'S OWN M1 FIX had no wiring test. The case below
            # in the tempdir block asserts `_armed() is None`: the PREDICATE. Nothing proved
            # run_decide MAPS that None to CANNOT RUN. MEASURED: mutating `if armed is None:` to
            # `if False:` at the run_decide guard left the suite at 75/75 — the fix was delivered
            # naked. This is the SAME shape as M5 directly above ("predicate, not wiring"), which
            # the fold fixed for `edited` and reintroduced for `armed` in the same commit.
            #
            # ⚠ WHY THIS DISCRIMINATES: with the early return deleted, None is falsy, so
            # `steps` becomes _UNSET, decide()'s `armed and ...` guard is false, and the result
            # is QUIET — not CANNOT_RUN. Asserting CANNOT_RUN is therefore not the codebase's
            # default answer for this input, which is the property a case needs to be worth having.
            # ⚠ THE SENTINEL MUST BE UNREADABLE AT THE **SEED** RUN, not at the judging run — the
            # verdict comes from the sample taken when the judged turn ended. Breaking it afterwards
            # would leave the stored sample intact and the case would pass for the wrong reason.
            # This also exercises the journalled `armed: null` round trip: null means "unreadable
            # then", NOT "nothing armed", and None is falsy, so a naive read would WARN about a plan
            # that may have existed instead of reporting CANNOT RUN.
            (_fx / ".claude" / "executing-plan").write_bytes(
                b"plan: plans/p.md\n\xff\xfe not utf-8 \xff\n")
            _rcB = _drive(_fx / "unreadable.jsonl", _subject)
            case("Cx-M2 an UNREADABLE sentinel is CANNOT RUN through run_decide, not a quiet False",
                 _rcB == CANNOT_RUN)
            (_fx / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")

            # ⛔ THE OTHER SIDE OF THE SAME GUARD — r5 Medium 3, and it is the side that says
            # NOTHING IS WRONG. `:1111` reads `armed_now is None and code == QUIET and judged is
            # None`; dropping `and judged is None` left the suite green at 150/150 and changed the
            # answer on an ordinary input. Cx-M2 above pins the CANNOT-RUN direction and cannot see
            # this, because it holds the sentinel unreadable at BOTH stops.
            #
            # The input: a turn that was judged and whose verdict is a SOUND QUIET, at a stop where
            # the sentinel happens to be unreadable — which is what `begin-plan.py` writing it looks
            # like for an instant, so this is routine, not exotic. Pristine stays QUIET; the mutant
            # reports CANNOT RUN about a turn that WAS checked. The unreadable sentinel is not lost
            # by staying quiet: it is journalled as `armed: null` and surfaces on the NEXT stop,
            # where it is the live turn's own excuse that is missing. This repo treats CANNOT RUN as
            # never a pass, so manufacturing one is cry-wolf on the one channel that surfaces.
            _rcM3 = _drive(_fx / "sound-quiet-unreadable.jsonl",
                           _turn("q1", [{"type": "text", "text": "a short bannerless turn"}]),
                           session="s-m3", before=None,
                           after=b"plan: plans/p.md\n\xff\xfe not utf-8 \xff\n")
            case("R5-1111 a SOUND QUIET verdict survives a sentinel that is unreadable at the "
                 "judging stop — CANNOT RUN is for the turn that has no verdict, not for one "
                 "that has a good one",
                 _rcM3 == QUIET)
            (_fx / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")

            # H3 — the UNARMED class, the guard's only previously-shipped behaviour, had no
            # execution coverage at all. Three log mutations survived because of it.
            #
            # ⛔ TWO DRIVES AT DISTINCT (step, total) PAIRS, IN ONE CASE — r5 High 1, the
            # integration half of the property stated at W1. The log's own detail is built at
            # `detail = f"STEP {banner[0]} of {banner[1]}"`, and the only two cases that read it —
            # this one and F97b — BOTH used step 2 (`STEP 2 of 5` here, `STEP 2 of 3` there). All
            # the distinctness r4 relied on lived in the TOTAL, so freezing HALF the value,
            # `f"STEP 2 of {banner[1]}"`, survived at 150/150 while every `unarmed` entry in the
            # warn log — 100% of its 76-entry history — would record step 2 whatever step the turn
            # actually reached. ⚠ PAIRWISE-DISTINCT FIXTURES ACROSS CASES DO NOT GIVE THIS. A
            # composite value has to be exercised COMPONENT-WISE, which means both components
            # varying within the assertion, which in turn means both drives living in one case.
            (_fx / ".claude" / "executing-plan").unlink()
            _rcU = _drive(_fx / "unarmed.jsonl",
                          _turn("u1", [{"type": "text",
                                        "text": "## ▶ STEP 2 of 5 — doing a thing"}]))
            _tailU = _logtext().rstrip("\n").split("\n")[-1]
            _rcU_b = _drive(_fx / "unarmed-b.jsonl",
                            _turn("u1b", [{"type": "text",
                                           "text": "## ▶ STEP 7 of 9 — a different step"}]),
                            session="s-unarmed-b")
            _tailU_b = _logtext().rstrip("\n").split("\n")[-1]
            case("H3 the UNARMED class still warns AND logs its own reason and detail — at TWO "
                 "distinct (step, total) pairs, so NEITHER half of `STEP i of N` can be frozen",
                 _rcU == WARN and _rcU_b == WARN
                 and _tailU.endswith("\tunarmed\tSTEP 2 of 5")
                 and _tailU_b.endswith("\tunarmed\tSTEP 7 of 9"))

            # ── W-INT: the THIRD class, driven end to end (2026-09-22) ────────────────────
            # ⛔ THE UNIT CASES ABOVE CANNOT REACH THE DEFECT THIS ONE COVERS. They call decide()
            # with `tool_uses=` supplied by hand, so `run_decide` failing to COUNT or to PASS it
            # leaves every one of them green while the class is dead on arrival — the recorded
            # shape *unit coverage does NOT compose: mutate the CALL SITE*. The comment on H3
            # directly above records the same omission costing three surviving log mutations.
            #
            # The sentinel is still unlinked from H3, which is the state this class is defined on.
            assert not (_fx / ".claude" / "executing-plan").exists()
            # ⚠ `LARGE_TURN + 7`, NOT `LARGE_TURN` (r1 claude M1). With exactly LARGE_TURN calls the
            # logged count and the threshold are the SAME NUMBER, so `detail = f"{LARGE_TURN} tool
            # calls"` — a logger that hardcodes the constant — passed 131/131. That column is the
            # evidence the promote-to-blocking decision reads; under the mutant every entry sits
            # exactly on the boundary and the observed distribution is manufactured by the logger.
            # The W0 comment had already diagnosed this hazard ("every other case derives from
            # LARGE_TURN and so moves with it") and it was applied to one site only.
            _WBIG = LARGE_TURN + 7
            _big = _turn("w1", [{"type": "tool_use", "id": f"b{i}", "name": "Bash",
                                 "input": {"command": "echo hi"}}
                                for i in range(_WBIG)])
            _rcW = _drive(_fx / "unheralded.jsonl", _big)
            case("W-INT run_decide WARNS on a large unarmed bannerless turn — the class is WIRED, "
                 "not merely implemented",
                 _rcW == WARN)
            case("W-INT ...and it logs under its OWN reason, never the sibling that shares "
                 "banner=None (backlog #97's mislabelling cannot recur), with the count IT SAW "
                 "rather than the threshold — the two are deliberately different numbers here",
                 _logtext().rstrip("\n").endswith(
                     f"\t{REASON_UNHERALDED}\t{_WBIG} tool calls")
                 and str(LARGE_TURN) != str(_WBIG))

            # The same turn ONE call smaller must be silent all the way through — otherwise the
            # case above would pass for any turn at all and the threshold would be decorative.
            _beforeW = _logtext()
            _small = _turn("w2", [{"type": "tool_use", "id": f"s{i}", "name": "Bash",
                                   "input": {"command": "echo hi"}}
                                  for i in range(LARGE_TURN - 1)])
            _rcS = _drive(_fx / "heralded-small.jsonl", _small)
            case("W-INT a turn ONE call below the threshold is QUIET and appends NOTHING — "
                 "the boundary survives the wiring, and the log stays countable",
                 _rcS == QUIET and _logtext() == _beforeW)

            # P-INT — the pause excuse, driven end to end. The unit cases pass `paused=` by hand,
            # so they cannot see run_decide failing to SAMPLE it, to JOURNAL it, or to pass it on.
            # That is three wiring steps, and the sample is the subtle one: the flag must describe
            # the turn being JUDGED, so it travels through the journal rather than being re-read.
            _beforeP = _logtext()
            (_fx / ".claude" / "executing-plan").write_text(
                "plan: plans/p.md\narmed: t\npaused: blocked on a dispatched review\n")
            _bigP = _turn("p1", [{"type": "tool_use", "id": f"p{i}", "name": "Bash",
                                  "input": {"command": "echo hi"}}
                                 for i in range(LARGE_TURN + 5)])
            _rcP = _drive(_fx / "paused-big.jsonl", _bigP)
            case("P-INT a PAUSED plan silences the class end to end — no warning, no log line. "
                 "Since backlog #94 a pause means 'blocked on in-flight work', which is exactly "
                 "the shape of turn that runs long",
                 _rcP == QUIET and _logtext() == _beforeP)

            # ...and the control that stops P-INT passing for an ambient reason: the SAME turn,
            # same size, with the pause removed, must warn. Without this, deleting the whole class
            # would keep P-INT green.
            (_fx / ".claude" / "executing-plan").unlink()
            _rcP2 = _drive(_fx / "unpaused-big.jsonl", _bigP)
            case("P-INT control: the identical turn with the pause REMOVED does warn",
                 _rcP2 == WARN)

            # ── H2 — the SAMPLE must be what the verdict consumes, not a re-read ──────────
            # ⛔ EVERY CASE ABOVE HOLDS THE SENTINEL IN ONE STATE ACROSS BOTH STOPS, so
            # "sampled at that turn's stop" and "re-read at judging time" are behaviourally
            # IDENTICAL to all of them: `paused=_paused()` at the call site — the thing two
            # comments in this file explicitly forbid — passed 131/131 (r1 claude H2). These
            # two legs are the only place in the suite where the sampled value and the live
            # value DIFFER, which is the only place the distinction can be observed.
            _PAUSED_TXT = ("plan: plans/p.md\narmed: t\n"
                           "paused: waiting on a dispatched review\n")
            _ARMED_TXT = "plan: plans/p.md\narmed: t\n"
            _b1 = _logtext()
            _rcH2a = _drive(_fx / "h2-resume.jsonl", _bigP,
                            before=_PAUSED_TXT, after=None)
            case("H2a a turn that RAN while paused stays quiet even though the plan was RESUMED "
                 "before it was judged — the verdict reads the SAMPLE, not the live sentinel",
                 _rcH2a == QUIET and _logtext() == _b1)
            _b2 = _logtext()
            _rcH2b = _drive(_fx / "h2-pause.jsonl", _bigP, before=None, after=_PAUSED_TXT)
            case("H2b ...and the mirror — pausing AFTER that turn ended does not retroactively "
                 "excuse it, so the sample cannot be read as 'whatever the sentinel says now'",
                 _rcH2b == WARN and _logtext() != _b2)

            # ── H-A (r3) — the SAME mechanism, for `armed` and `steps` ───────────────────
            # ⛔ THE r1 FOLD FIXED THE INSTANCE AND NOT THE CLASS, inside the comment that names
            # the class. H2 was never a finding about the word `paused`; it was about the journal
            # round trip — *the value the verdict consumes must be the one sampled at the judged
            # turn's stop*. The fix comment says so itself: "SAMPLED, NOT RE-READ AT JUDGING TIME
            # … for the same reason `armed` is". H2a/H2b vary ONLY `paused`; in both legs
            # `armed_then` is False, so neither can see `armed` being re-read. Measured: `texts,
            # _armed(), …` at the call site left the suite at 138/138 while INVERTING the verdict
            # in both directions. The recorded *after fixing, SEARCH for the class*.
            #
            # ⚠ Both are PRE-EXISTING (`armed_then, steps_then = sample` is on master). Filed and
            # fixed here for the reason the fold accepted M2, also pre-existing: this branch makes
            # them cheap — two legs through the helper it already wrote.
            #
            # The scenario is the guard's own documented one: `check-plan-progress.py` UNLINKS the
            # sentinel when the last box is ticked, which is why this observer runs first. So a
            # turn that ran armed is routinely judged after the sentinel has gone.
            _b3 = _logtext()
            _rcA1 = _drive(_fx / "ha-cleared.jsonl", _bigP,
                           before=_ARMED_TXT, after=None)
            case("H-A1 a turn that RAN with a plan armed stays quiet even though the sentinel was "
                 "cleared before it was judged — `armed` is consumed from the SAMPLE too, not only "
                 "`paused`",
                 _rcA1 == QUIET and _logtext() == _b3)
            _b4 = _logtext()
            _rcA2 = _drive(_fx / "ha-armed-after.jsonl", _bigP,
                           before=None, after=_ARMED_TXT)
            case("H-A2 ...and the mirror — arming a plan AFTER that turn ended does not "
                 "retroactively excuse it",
                 _rcA2 == WARN and _logtext() != _b4)
            # `steps` travels with `armed` and feeds BOTH the `unbannered` detail and the
            # `armed and steps is None` CANNOT-RUN guard, so a re-read makes both describe the
            # wrong turn. Seeding armed-with-a-plan and judging armed-with-NO-plan-file separates
            # `steps_then` from `steps_now` while `armed` stays True on both sides.
            _rcA3 = _drive(_fx / "ha-steps.jsonl", _bigP,
                           before=_ARMED_TXT, after="plan: plans/gone.md\narmed: t\n")
            case("H-A3 `steps` is consumed from the sample as well — a plan file that vanishes "
                 "between the two stops must not turn a measured turn into CANNOT RUN",
                 _rcA3 != CANNOT_RUN)

            # ── H-B (r3) — the PREVIOUS journal slot, reached through run_decide ─────────
            # ⛔ TWO EARLIER ROUNDS CONCLUDED THIS PATH WAS UNREACHABLE AND BOTH WERE WRONG.
            # r1 hedged ("I tried and failed to construct an input"); r2 answered "no clean
            # run-generated path"; the r1 fold hardened the hedge into an ASSERTION in a
            # reader-facing page — the recorded *an inference stated as MEASURED*. Six single
            # edits to this wiring left the suite at 138/138: four cry wolf, two turn a sound
            # verdict into CANNOT RUN, which this project's rule says is never a pass.
            #
            # ⭐ WHY IT LOOKED UNREACHABLE. The prev slot needs `prev_turn_uuid == U` while
            # `last_judged_uuid != U`, and every stop that judges something sets the latter. The
            # only separator is a window that was NON-JUDGABLE when live and judgable one stop
            # later — which requires the transcript to GROW, i.e. backlog #96's late flush, the
            # mechanism this file exists to measure. Both earlier passes searched a transcript
            # written before the first stop, where it cannot exist by construction. The precursor
            # is ordinary, not exotic: 322 non-judgable non-live windows across the 65 `cli`
            # transcripts.
            def _drive_prev_slot(path: Path, late_body: list, before, mid,
                                 session: str = "p", continuation: bool = False) -> int:
                """Three stops; `Wa` is non-judgable at A and judgable at C, so it lands in the
                PREVIOUS slot — sampled at A, judged at C, with the sentinel changed in between.

                ⛔ `continuation=True` ADDS A FOURTH STOP AND IT IS NOT DECORATION. It repeats stop
                B with the transcript UNCHANGED, so `live_uuid == already["sampled_turn_uuid"]` and
                `run_decide` takes its continuation branch — the one that PRESERVES the older prev
                slot instead of shifting the window. Without this leg the two `record["prev_paused"]
                = …` carries in that branch are unreachable, and both survived as single edits at
                145/145 while the three-stop legs below killed the other six. Measured, not assumed.
                """
                for _st in JOURNAL_DIR.glob("*.json"):
                    _st.unlink()
                _u = lambda uid: json.dumps(
                    {"type": "user", "uuid": uid, "message": {"content": "go"}})
                _a = lambda body: json.dumps({"type": "assistant", "message": {"content": body}})
                _sentinel(before)
                path.write_text(_u("Wa"))                                    # stop A
                run_decide(json.dumps({"transcript_path": str(path), "session_id": session}))
                _sentinel(mid)
                path.write_text("\n".join([_u("Wa"), _u("Wb")]))             # stop B
                run_decide(json.dumps({"transcript_path": str(path), "session_id": session}))
                if continuation:
                    # SAME transcript, so the live window has not moved: a blocked-stop re-fire.
                    run_decide(json.dumps({"transcript_path": str(path), "session_id": session}))
                path.write_text("\n".join([                                  # stop C — Wa flushes
                    _u("Wa"), _a(late_body), _u("Wb"), _u("Wc"),
                    _a([{"type": "text", "text": "x"}])]))
                return run_decide(json.dumps({"transcript_path": str(path),
                                              "session_id": session}))

            _body30 = [{"type": "tool_use", "id": f"x{i}", "name": "Bash",
                        "input": {"command": "echo hi"}} for i in range(LARGE_TURN + 5)]
            _bp = _logtext()
            _rcB1 = _drive_prev_slot(_fx / "prev-paused.jsonl", _body30, _PAUSED_TXT, None)
            case("H-B1 the PREVIOUS slot is REACHABLE from a clean journal through run_decide — a "
                 "window non-judgable when live and judgable one stop later — and the pause "
                 "sampled THERE still excuses the turn",
                 _rcB1 == QUIET and _logtext() == _bp)
            _bp2 = _logtext()
            _rcB2 = _drive_prev_slot(_fx / "prev-none.jsonl", _body30, None, None)
            # ⚠ THIS ALSO ASSERTS THE LOGGED COUNT, and it is the SECOND such assertion on
            # purpose (r4). W-INT logs `LARGE_TURN + 7`; this drive logs `LARGE_TURN + 5`. While
            # W-INT was the only integration case reading a logged tool count, freezing the log
            # detail to that fixture's size satisfied it and survived at 147/147. Two different
            # counts mean no constant satisfies both.
            #
            # ⛔ `!= _bp2` IS A CONJUNCT, NOT A CASUALTY — r5 Medium 2. The r4 fold REPLACED the
            # growth assertion with the `endswith` above, and measured on the staged copy, that
            # clause is ALREADY TRUE when it is evaluated: the preceding H-A drive had logged
            # `unheralded / 30 tool calls`, and the two lines differ only in the session column,
            # which `endswith` does not read. So the tail match alone cannot tell "this drive
            # logged the right line" from "this drive logged nothing and I am reading someone
            # else's". The growth check is what makes it THIS drive's line, and the freeze above
            # still dies through the other drive's count. The repair is one word: `and`.
            case("H-B1 control: the identical three-stop shape with NOTHING in the previous slot "
                 "does warn, and logs the count THIS turn made — a second, different count, so "
                 "the log detail cannot be a constant, and the line is one THIS drive wrote",
                 _rcB2 == WARN
                 and _logtext() != _bp2
                 and _logtext().rstrip("\n").endswith(
                     f"\t{REASON_UNHERALDED}\t{LARGE_TURN + 5} tool calls"))
            _rcB3 = _drive_prev_slot(_fx / "prev-armed.jsonl", _body30, _ARMED_TXT, None)
            case("H-B2 `prev_armed` and `prev_steps` travel with it — a turn that ran ARMED is "
                 "quiet, and never CANNOT RUN, when judged out of the previous slot",
                 _rcB3 == QUIET and _rcB3 != CANNOT_RUN)
            # ⛔ THE CONTINUATION CARRY. Seed PAUSED at A, CLEAR before B, then re-fire B with the
            # transcript unchanged: the continuation branch must PRESERVE Wa's pause across that
            # re-fire. Two single edits to it — dropping the carry, and reading `paused` (Wb's,
            # now False) instead of `prev_paused` (Wa's, True) — survived every other leg here.
            _bp3 = _logtext()
            _rcB4 = _drive_prev_slot(_fx / "prev-cont.jsonl", _body30, _PAUSED_TXT, None,
                                     continuation=True)
            case("H-B3 a BLOCKED-STOP re-fire preserves the previous slot's pause — the "
                 "continuation branch carries `prev_paused`, and reads the PREVIOUS turn's value "
                 "rather than the current one",
                 _rcB4 == QUIET and _logtext() == _bp3)

            # ── H-A4 — the `steps` SAMPLE, on the path the LOG reads ────────────────────
            # ⛔ THIS CASE EXISTS BECAUSE A HAND-VERIFICATION TESTED A DIFFERENT EDIT THAN THE
            # MANIFEST SHIPS. `steps` is bound twice on this path: as `decide()`'s ARGUMENT (the
            # verdict) and as the local the LOG BLOCK reads (the detail). H-A3 pins the first;
            # the manifest entry mutates the second, so it survived a full sweep at 908/909 while
            # every by-hand probe said killed. The two counts must DIFFER for the detail to be
            # observable at all — pointing the sentinel at a second plan file with a different
            # tick count is the only way to separate `steps_then` from `steps_now`.
            # ⛔ THREE DISTINCT COUNTS, AND THE THIRD IS r4's FINDING. The first cut seeded from
            # `p.md` — the ambient fixture plan, 3 unticked — and asserted "3 unticked". So did the
            # pre-existing F4 case. A log block hardcoding `unticked = 3` therefore satisfied BOTH
            # and survived at 149/149: the case proved "not the CURRENT plan's count" and not "the
            # SAMPLED plan's count", which is the claim. Seeding from `r.md` (2) makes the asserted
            # value ambient NOWHERE, and leaves F4's 3 and this 2 pinning each other — a constant
            # satisfying one now reddens the other. The recorded *a case can pass for an AMBIENT
            # reason*, second instance on this branch after r1's H1.
            (_fx / "plans" / "q.md").write_text(
                "- [x] one\n- [x] two\n- [x] three\n- [ ] four\n")            # 1 unticked (now)
            (_fx / "plans" / "r.md").write_text(
                "- [x] one\n- [x] two\n- [ ] three\n- [ ] four\n")            # 2 unticked (sampled)
            _rcS = _drive(_fx / "steps-sample.jsonl", _subject,
                          before="plan: plans/r.md\narmed: t\n",
                          after="plan: plans/q.md\narmed: t\n")
            case("H-A4 the LOGGED `unticked` count is COMPUTED from the plan sampled when the "
                 "judged turn ended — 2 then, 1 now, and 3 in every other fixture here, so no "
                 "constant satisfies this case and F4 at once",
                 _rcS == WARN
                 and _logtext().rstrip("\n").endswith("\tunbannered\t2 unticked"))
            (_fx / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")
            (_fx / ".claude" / "executing-plan").unlink(missing_ok=True)
        finally:
            (globals()["ROOT"], globals()["SENTINEL"], globals()["WARN_LOG"],
             globals()["FLUSH_LOG"], globals()["JOURNAL_DIR"]) = _saved

    # ── F6: reachability. STRUCTURAL, not an execution test — see the plan. ────────────────
    # ⛔ THIS CASE'S SUBJECT IS THE REPO, NOT THIS SCRIPT, AND THAT BROKE THE MUTATION HARNESS
    # (backlog #96, 2026-09-06). `mutate_delivered` copies the whole `scripts/` tree and nothing
    # else — deliberately, because these scripts import each other as siblings — so
    # `.claude/hooks/` is absent there. Until this slice the guard had no manifest, so its suite
    # never ran inside the harness and nobody found out; adding one turned the CONTROL red with
    # FileNotFoundError, which correctly refused to report any mutation verdict at all.
    #
    # ⚠ NEITHER OBVIOUS FIX IS ACCEPTABLE. Passing when the file is missing is fail-open — the
    # case exists to prove the hook still invokes this guard, and "the file was not there" would
    # silently satisfy it. Failing whenever it is missing makes the manifest permanently unusable.
    #
    # The discriminator is whether `.claude/` EXISTS. A scripts-only copy has no `.claude` at all;
    # a real checkout that lost the hook has `.claude` and no hook, which IS a regression and must
    # fail. So absence is only excused where the whole directory is absent, and the excuse is
    # PRINTED rather than silent.
    _claude_dir = ROOT / ".claude"
    _hook_path = _claude_dir / "hooks" / "block-idle-stop.sh"
    if not _hook_path.exists():
        case("reachability NOT CHECKED — scripts-only tree, no .claude/ to read "
             "(this is the mutation harness; a real checkout missing the hook FAILS here)",
             not _claude_dir.exists())
        _hook = ""
    else:
        _hook = _hook_path.read_text()
    # ⚠ _obs PINS THE INVOCATION, NOT THE FILENAME (code review r2, Medium). A bare
    # "check-banner-armed.py" is matched by str.index at its FIRST occurrence ANYWHERE — comments
    # included — and L3 put a five-line comment about the observer directly above the blocking
    # check. Naming the file in that comment is the natural next edit and it silently disarms this
    # case: MEASURED, the observer restored to its pre-slice position below the blocking check,
    # plus that one reworded clause, gave PASS/PASS/PASS at 75/75 with the hook in the broken
    # order. Anchors bind by TEXT, so improving the prose breaks the guard and the suite stays
    # green — the recorded shape. No comment plausibly contains the `" --decide` suffix.
    _obs, _blk = 'check-banner-armed.py" --decide', 'check-plan-progress.py" "${ARGS[@]}"'
    if _hook:
        case("F6 the banner guard is invoked BEFORE the blocking check that can exit early",
             _obs in _hook and _blk in _hook and _hook.index(_obs) < _hook.index(_blk))
        case("F6b the hook uses REPO_ROOT — $ROOT is empty and would block every stop",
             "$ROOT/scripts" not in _hook)
    # F6c — the guard being INVOKED is not the same as its result being READ. Deleting BANNER_RC
    # from the exit arithmetic leaves an unblocked stop at exit 0, which discards the warning:
    # the guard would run, log, report success, and reach nobody. This slice's own failure, one
    # layer out. Structural, like F6.
        case("F6c BANNER_RC reaches the hook's exit arithmetic, not just the invocation",
             '"$BANNER_RC" != "0"' in _hook)


    # ── an ATTEMPTED edit is not an edit (code review r1) ──────────────────────────────────
    def edit_id(path: str, tid: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": "Edit", "input": {"file_path": path}}]}})

    def result(tid: str, err: bool) -> str:
        return json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": tid, "is_error": err, "content": "x"}]}})

    case("a FAILED Edit does not count as work — 22 error results in 40 transcripts",
         edited_paths_of(records_since_last_user(
             [user("go"), edit_id("/a/b.py", "t1"), result("t1", True)]) or []) == [])
    case("...but a SUCCEEDED Edit does",
         edited_paths_of(records_since_last_user(
             [user("go"), edit_id("/a/b.py", "t1"), result("t1", False)]) or []) == ["/a/b.py"])
    case("...and an UNPAIRED Edit counts — at stop time that is in-flight, not refused",
         edited_paths_of(records_since_last_user(
             [user("go"), edit_id("/a/b.py", "t1")]) or []) == ["/a/b.py"])
    case("...and one failed edit does not suppress a different successful one",
         edited_paths_of(records_since_last_user(
             [user("go"), edit_id("/a/bad.py", "t1"), edit_id("/a/ok.py", "t2"),
              result("t1", True), result("t2", False)]) or []) == ["/a/ok.py"])
    def use(path: str, tid: str, name: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": name, "input": {"file_path": path}}]}})

    case("M3 a Write counts too — deleting it from _EDIT_TOOLS narrows detection silently",
         edited_paths_of(records_since_last_user(
             [user("go"), use("/a/w.py", "w1", "Write")]) or []) == ["/a/w.py"])
    # ⚠ THE INPUT KEY IS `notebook_path`, NOT `file_path` (code review r2, Low). The first draft
    # of this case used use(), which always emits file_path — so it exercised _EDIT_TOOLS
    # membership and never the `or inp.get("notebook_path")` fallback at :209, which is the ONLY
    # branch NotebookEdit actually takes in the real runtime. Deleting that fallback left the
    # suite at 75/75. The tested shape was the one that never occurs.
    def use_nb(path: str, tid: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": "NotebookEdit",
             "input": {"notebook_path": path}}]}})

    case("...and a NotebookEdit counts, via the notebook_path key it actually sends",
         edited_paths_of(records_since_last_user(
             [user("go"), use_nb("/a/n.ipynb", "n1")]) or []) == ["/a/n.ipynb"])
    case("...but an unrelated tool still does not",
         edited_paths_of(records_since_last_user(
             [user("go"), use("/a/r.py", "r1", "Read")]) or []) == [])

    case("a DIRECTORY inside the repo is not a file this turn edited",
         _edit_inside_repo([str(ROOT / "scripts")], ROOT) is False)
    case("...while a real file in that directory is",
         _edit_inside_repo([str(ROOT / "scripts" / "check-banner-armed.py")], ROOT) is True)


    # ── isMeta is not a synonym for "not the human" (code review r1, M4) ───────────────────
    def meta_msg(text: str) -> str:
        return json.dumps({"type": "user", "isMeta": True, "message": {"content": text}})

    case("an isMeta record RELAYING the human IS a boundary — 30 such in the corpus",
         highest_banner(texts_of(records_since_last_user(
             [user("go"), asst(B.format(2, 4)),
              meta_msg("The user sent a new message while you were working: do X"),
              asst("new turn")]) or [])) is None)
    case("...as is a slash command the human typed — 67 such in the corpus",
         highest_banner(texts_of(records_since_last_user(
             [user("go"), asst(B.format(2, 4)),
              meta_msg("<local-command-caveat>Caveat: ...</local-command-caveat>"),
              asst("new turn")]) or [])) is None)
    case("...but a system-reminder injection is still NOT a boundary",
         highest_banner(texts_of(records_since_last_user(
             [user("go"), asst(B.format(2, 4)),
              meta_msg("<system-reminder>background context</system-reminder>"),
              asst("kept working")]) or [])) == (2, 4))

    # ── window selection (backlog #96) ────────────────────────────────────────────────────
    # ⛔ THE SPEC'S F6 IS DELIBERATELY ABSENT HERE. It says records_since_last_user still equals
    # windows(...)[-1].body — which, after the refactor, is that function's DEFINITION, so a case
    # asserting it compares the code to itself and can never fail. That is the tautology F11 turned
    # out to be (measured: 1828 windows, 0 violations, true by construction). F6 was instead run ONCE
    # as a migration check against the PRE-refactor implementation over the whole corpus:
    # 526 transcripts, 526 identical, 0 different. What stands below is each documented BEHAVIOUR.
    def rec(line: str) -> dict:
        return json.loads(line)

    def asst_toolonly(path: str) -> str:
        """An assistant turn that edits a file and emits NO text — the F8 case."""
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Edit", "input": {"file_path": path}}]}})

    def uuser(text: str, uid: str) -> str:
        return json.dumps({"type": "user", "uuid": uid, "message": {"content": text}})

    case("windows() carries the OPENER, and the body still excludes it",
         safe(lambda: (lambda ws: ws[-1].opener["uuid"] == "u2" and
                       [r.get("type") for r in ws[-1].body] == ["assistant"])(
             windows([rec(uuser("first", "u1")), rec(asst("a")),
                      rec(uuser("second", "u2")), rec(asst("b"))]))))

    case("windows() on a transcript with NO real-user boundary returns ONE window, opener=None",
         safe(lambda: (lambda ws: len(ws) == 1 and ws[0].opener is None and len(ws[0].body) == 2)(
             windows([rec(asst("a")), rec(tool_result())]))))

    case("F8 — a turn with only tool calls and NO assistant text IS judgable",
         safe(lambda: is_judgable(TurnWindow(None, [rec(asst_toolonly("/tmp/x.py"))]))))

    case("...but a slash-command shell window, holding ZERO records, is NOT judgable",
         safe(lambda: not is_judgable(TurnWindow(rec(uuser("/goal x", "u1")), []))))

    case("F3 — the empty slash-command window is skipped and the SUBSTANTIVE turn is judged",
         safe(lambda: judged_window(windows([
             rec(uuser("real work", "u1")), rec(asst(B.format(3, 3))),
             rec(uuser("/goal fix", "u2")),                  # opens an EMPTY window
             rec(uuser("<local-command-stdout>ok</local-command-stdout>", "u3")),
             rec(asst("live turn")),
         ])).opener["uuid"] == "u1"))

    case("F3 — the judged turn does NOT move when more records arrive in the LIVE window",
         safe(lambda: (lambda base, grown: judged_window(windows(base)).opener["uuid"]
                       == judged_window(windows(grown)).opener["uuid"])(
             [rec(uuser("work", "u1")), rec(asst(B.format(2, 4))),
              rec(uuser("next", "u2")), rec(asst("live"))],
             [rec(uuser("work", "u1")), rec(asst(B.format(2, 4))),
              rec(uuser("next", "u2")), rec(asst("live")), rec(asst("more")), rec(tool_result())])))

    case("F5 — one window only means NO SUBJECT (None), never a raise",
         safe(lambda: judged_window(windows([rec(uuser("only turn", "u1")), rec(asst("x"))]))
              is None))

    case("the degenerate no-boundary transcript yields no subject, and does NOT raise",
         safe(lambda: judged_window(windows([rec(asst("a"))])) is None))

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Warn when a step banner was emitted with no plan armed.")
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.decide:
        sys.exit(run_decide(sys.stdin.read()))
    ap.print_help()
    sys.exit(CANNOT_RUN)

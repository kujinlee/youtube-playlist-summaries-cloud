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
failed here before), so the mitigation is that every firing is APPENDED TO A LOG. The question
"does it false-alarm?" then has a number rather than an impression, and the decision to promote it
to blocking can be made from data.

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

Taking the HIGHEST is what makes the common case quiet. A turn that announces five steps and
finishes all five emits `STEP 5 of 5` as its highest banner, so i == N and nothing fires. What
remains is exactly "announced a multi-step job, stopped partway" — the failure measured four times
(backlog #44, #53, 2026-09-03).

WHAT IT CANNOT SEE, stated rather than hidden:
  * a multi-step job never announced at all. Smaller class than what bit us — the five steps WERE
    announced every time — but real. This is not full coverage and must not be described as such.
  * whether the work was genuinely finished. `i < N` with the job actually complete is a real false
    alarm; that is why this warns rather than blocks, and why it logs.

FAILS CLOSED ON ITS OWN BLINDNESS. No transcript, an unreadable one, or zero assistant text parsed
-> exit 2 with CANNOT RUN. A check that cannot reach what it measures is never a pass (CLAUDE.md),
and "no banner found" is indistinguishable from "could not read the file" unless it says so.

Usage (the hook calls form 1):
    python3 scripts/check-banner-armed.py --decide < <stop-hook-json>
    python3 scripts/check-banner-armed.py --self-test  # 25 cases
Exit codes for --decide:  0 = nothing to say   1 = WARN (non-blocking)   2 = CANNOT RUN
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/executing-plan"
WARN_LOG = ROOT / ".claude/banner-warnings.log"

QUIET, WARN, CANNOT_RUN = 0, 1, 2

# The banner CLAUDE.md mandates: `## ▶ STEP 3 of 6 — title`. The separator between the numbers is
# matched loosely (`of`), but the `## ▶ STEP` opener is not — a looser opener would match prose
# ABOUT the convention, and this file, the skill docs and the dashboard all discuss it.
BANNER_RE = re.compile(r"^##\s*▶\s*STEP\s+(\d+)\s+of\s+(\d+)\b", re.M)


# ── Pure core ─────────────────────────────────────────────────────────────────────────────────

def assistant_texts_since_last_user(lines: list[str]) -> list[str] | None:
    """Assistant text emitted after the most recent real user message. None if unparseable.

    A tool RESULT arrives as a `user`-typed record, so keying on `type == "user"` alone would cut
    the window at the last tool call and hide every banner before it. Records whose content is a
    tool result are therefore not treated as turn boundaries.
    """
    records = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except (ValueError, TypeError):
            continue
    if not records:
        return None

    start = 0
    for i, rec in enumerate(records):
        if rec.get("type") != "user":
            continue
        if _is_tool_result(rec):
            continue
        start = i + 1

    out: list[str] = []
    for rec in records[start:]:
        if rec.get("type") == "assistant":
            out.extend(_text_blocks(rec))
    return out


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


def decide(texts: list[str] | None, armed: bool) -> tuple[int, str]:
    """-> (exit_code, message). Pure: every input is passed in."""
    if texts is None:
        return CANNOT_RUN, (
            "CANNOT RUN: the stop-hook payload named no readable transcript, so this check could "
            "not look for a step banner. TREAT THIS AS NOT RUN — do not read the absence of a "
            "warning as 'nothing was announced'.")

    banner = highest_banner(texts)
    if banner is None:
        return QUIET, ""

    step, total = banner
    if step >= total:
        return QUIET, ""
    if armed:
        return QUIET, ""

    return WARN, (
        f"⚠ BANNER WITHOUT A PLAN — this turn announced `STEP {step} of {total}` and is ending "
        f"with {total - step} step(s) unannounced, while .claude/executing-plan names nothing.\n"
        "\n"
        "   Nothing is blocked. This is the WARN-ONLY half of task #224: the Stop guard\n"
        "   (check-plan-progress.py) can only refuse a premature stop if a plan was armed, and\n"
        "   arming it is one command:\n"
        "\n"
        f"     scripts/begin-plan.py <slug> \"title|doing|why\" ...   # writes the plan AND the banner\n"
        f"     scripts/begin-plan.py --plan <existing-plan.md>      # or arm on a real plan\n"
        "\n"
        "   If the job really is finished, this is a false alarm and it has been logged as one —\n"
        f"   see {WARN_LOG.relative_to(ROOT)}. That log is the evidence for whether this should\n"
        "   ever become blocking.")


def log_line(step: int, total: int, when: str, session: str) -> str:
    """One appended record. Tab-separated so the log stays greppable and countable."""
    return f"{when}\t{session or '-'}\tSTEP {step} of {total}\tunarmed\n"


# ── I/O shell ─────────────────────────────────────────────────────────────────────────────────

def _armed() -> bool:
    try:
        text = SENTINEL.read_text()
    except OSError:
        return False
    for line in text.splitlines():
        if line.split(":", 1)[0].strip() == "plan" and line.split(":", 1)[-1].strip():
            return True
    return False


def run_decide(payload: str) -> int:
    try:
        data = json.loads(payload) if payload.strip() else {}
    except (ValueError, TypeError):
        data = {}

    texts: list[str] | None = None
    path = data.get("transcript_path")
    if isinstance(path, str) and path:
        try:
            texts = assistant_texts_since_last_user(Path(path).read_text().splitlines())
        except OSError:
            texts = None

    code, message = decide(texts, _armed())

    if code == WARN:
        banner = highest_banner(texts or [])
        if banner:
            when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
            try:
                WARN_LOG.parent.mkdir(parents=True, exist_ok=True)
                with WARN_LOG.open("a") as fh:
                    fh.write(log_line(banner[0], banner[1], when, str(data.get("session_id", ""))))
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
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

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
    case("...and the message says how many steps are left",
         "3 step(s) unannounced" in decide([B.format(2, 5)], armed=False)[1])
    case("...and it names the one command that fixes it",
         "begin-plan.py" in decide([B.format(2, 5)], armed=False)[1])
    case("...and it says plainly that nothing is blocked",
         "Nothing is blocked" in decide([B.format(2, 5)], armed=False)[1])
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
    code, msg = decide(None, armed=False)
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
    case("the log line is tab-separated and states the banner and the state",
         log_line(2, 5, "2026-09-04T07:00:00-07:00", "sess").split("\t")[2:]
         == ["STEP 2 of 5", "unarmed\n"])

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

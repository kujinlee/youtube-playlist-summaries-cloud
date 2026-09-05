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

It also answers the INVERSE — a plan armed, work done in the repo, and NO banner emitted at all.
That is the direction that actually failed on 2026-09-04, when begin-plan.py printed banners to the
stdout of a Bash call, which is shown to the assistant and not reliably to the human.

WHO READS A WARNING depends on the exit code, and both readers are intended: on a BLOCKED stop the
hook exits 2 and Claude reads it (the actor, when the next banner is due); on an unblocked stop it
exits 1 and the human reads it (the auditor). See .claude/hooks/block-idle-stop.sh.

WHAT IT CANNOT SEE, stated rather than hidden:
  * SUBAGENT edits. Measured: 0 `isSidechain:true` records across 508 transcripts for this project —
    subagent work lives in its own session file, so a coordinator turn that dispatches five
    reviewers reads as edited=False. `subagent-driven-development` is the Phase 3 DEFAULT here, so
    this is the normal mode, not an edge case.
  * work done entirely through Bash — a script that rewrites a file, a git operation. Widening to
    any mutating tool was rejected: a turn running `gh pr view` to answer a question would warn.
  * work in a git WORKTREE, which sits outside ROOT and so reads as outside the repo.
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
    python3 scripts/check-banner-armed.py --self-test  # 61 cases
Exit codes for --decide:  0 = nothing to say   1 = WARN (non-blocking)   2 = CANNOT RUN
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/executing-plan"
WARN_LOG = ROOT / ".claude/banner-warnings.log"

QUIET, WARN, CANNOT_RUN = 0, 1, 2

_UNSET = object()   # `steps` was not consulted. Distinct from None = "unreadable".

# The banner CLAUDE.md mandates: `## ▶ STEP 3 of 6 — title`. The separator between the numbers is
# matched loosely (`of`), but the `## ▶ STEP` opener is not — a looser opener would match prose
# ABOUT the convention, and this file, the skill docs and the dashboard all discuss it.
BANNER_RE = re.compile(r"^##\s*▶\s*STEP\s+(\d+)\s+of\s+(\d+)\b", re.M)


# ── Pure core ─────────────────────────────────────────────────────────────────────────────────

def records_since_last_user(lines: list[str]) -> list[dict] | None:
    """Records emitted after the most recent REAL user message. None if unparseable.

    Two kinds of `user` record are not the human typing, and treating them as turn boundaries
    truncates the window:
      * a tool RESULT — without this, the window is cut at the last tool call.
      * an `isMeta` record — a skill injection, or THIS HOOK's own block feedback. Measured
        2026-09-04: the block message sat 72 records after the `STEP 2 of 4` banner for the step
        still in progress, so the banner fell out of window by construction.

    `promptSource` is deliberately NOT part of this rule. Measured over 30 transcripts: skipping
    it too collapses 142 windows to 70, and 52 of the 72 removed boundaries begin a GENUINELY NEW
    turn. A window that never resets is as wrong as one that resets too often.
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
        if _is_tool_result(rec) or rec.get("isMeta") is True:
            continue
        start = i + 1
    return records[start:]


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


def assistant_texts_since_last_user(lines: list[str]) -> list[str] | None:
    """Back-compat wrapper: the text half of the window. Existing callers unchanged."""
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


def decide(texts: list[str] | None, armed: bool,
           steps=_UNSET, edited: bool = False) -> tuple[int, str]:
    """-> (exit_code, message). Pure: every input is passed in."""
    if texts is None:
        return CANNOT_RUN, (
            "CANNOT RUN: the stop-hook payload named no readable transcript, so this check could "
            "not look for a step banner. TREAT THIS AS NOT RUN — do not read the absence of a "
            "warning as 'nothing was announced'.")

    # Blindness is a property of the sentinel and the plan file, NOT of whether the assistant
    # happened to type a heading — so it is answered before the banner is even looked at.
    if armed and steps is None:
        return CANNOT_RUN, (
            "CANNOT RUN: .claude/executing-plan names a plan this check could not measure — "
            "missing, unreadable, or containing zero `- [ ]` step checkboxes. TREAT THIS AS "
            "NOT RUN — do not read the absence of a warning as 'a banner was not owed'.")

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
                f"   Logged to {WARN_LOG.relative_to(ROOT)}.")
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
        "   This does not block your stop by itself. Another check may be blocking it.\n"
        "   This is the WARN-ONLY half of task #224: the Stop guard\n"
        "   (check-plan-progress.py) can only refuse a premature stop if a plan was armed, and\n"
        "   arming it is one command:\n"
        "\n"
        f"     scripts/begin-plan.py <slug> \"title|doing|why\" ...   # writes the plan AND the banner\n"
        f"     scripts/begin-plan.py --plan <existing-plan.md>      # or arm on a real plan\n"
        "\n"
        "   If the job really is finished, this is a false alarm and it has been logged as one —\n"
        f"   see {WARN_LOG.relative_to(ROOT)}. That log is the evidence for whether this should\n"
        "   ever become blocking.")


def log_line(reason: str, detail: str, when: str, session: str) -> str:
    """One appended record. Tab-separated so the log stays greppable and countable.

    `reason` discriminates the two warning classes. The banner-less class has NO banner by
    construction, so the previous shape — (step, total), written only when a banner existed —
    could never record it, and a class the log cannot express reads as never having fired.

    Nothing parses this file (searched 2026-09-04: only this module, its self-test, a comment in
    block-idle-stop.sh, and prose in docs/dashboard-entries.md).
    """
    return f"{when}\t{session or '-'}\t{reason}\t{detail}\n"


# ── I/O shell ─────────────────────────────────────────────────────────────────────────────────

def _armed_from_text(text: str) -> bool:
    """PURE. True iff the sentinel names a plan AND has not been stood down.

    `paused:` is honoured because check-plan-progress.decide() honours it — the two must agree
    about what "armed" means, or this guard's principal firing state becomes the one documented
    escape (begin-plan.py --pause, for being legitimately blocked on in-flight work).

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
    """PURE. True iff any path is a FILE inside `root` that counts as plan work.

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


def _armed() -> bool:
    try:
        return _armed_from_text(SENTINEL.read_text())
    except OSError:
        return False


def run_decide(payload: str) -> int:
    try:
        data = json.loads(payload) if payload.strip() else {}
    except (ValueError, TypeError):
        data = {}

    records: list[dict] | None = None
    path = data.get("transcript_path")
    if isinstance(path, str) and path:
        try:
            records = records_since_last_user(Path(path).read_text().splitlines())
        except OSError:
            records = None
    texts = None if records is None else texts_of(records)

    armed = _armed()
    steps = _plan_steps() if armed else _UNSET      # local: the log block below reads it
    edited = _edit_inside_repo(edited_paths_of(records or []), ROOT)
    code, message = decide(texts, armed, steps=steps, edited=edited)

    if code == WARN:
        banner = highest_banner(texts or [])
        if banner:
            reason, detail = "unarmed", f"STEP {banner[0]} of {banner[1]}"
        else:
            unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
            reason, detail = "unbannered", f"{unticked} unticked"
        if True:
            when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
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
    case("the log line is tab-separated and states the state and the detail",
         log_line("unarmed", "STEP 2 of 5", "2026-09-04T07:00:00-07:00", "sess").split("\t")[1:]
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
    case("...and the message does NOT claim nothing is blocked",
         "Nothing is blocked" not in decide([], armed=True, steps=S, edited=True)[1])
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
        _tr = _fx / "t.jsonl"
        _tr.write_text("\n".join([
            json.dumps({"type": "user", "message": {"content": "go"}}),
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Edit",
                 "input": {"file_path": str(_fx / "scripts" / "x.py")}}]}}),
        ]))
        _saved = (ROOT, SENTINEL, WARN_LOG)
        globals()["ROOT"] = _fx
        globals()["SENTINEL"] = _fx / ".claude/executing-plan"
        globals()["WARN_LOG"] = _fx / ".claude/banner-warnings.log"
        try:
            _rc = run_decide(json.dumps({"transcript_path": str(_tr), "session_id": "s"}))
            _log = _fx / ".claude/banner-warnings.log"
            case("F4 run_decide WARNS on the new class AND appends a line — the side effect",
                 _rc == WARN and _log.exists()
                 and _log.read_text().rstrip("\n").endswith("\tunbannered\t3 unticked"))
        finally:
            globals()["ROOT"], globals()["SENTINEL"], globals()["WARN_LOG"] = _saved

    # ── F6: reachability. STRUCTURAL, not an execution test — see the plan. ────────────────
    _hook = (ROOT / ".claude/hooks/block-idle-stop.sh").read_text()
    _obs, _blk = "check-banner-armed.py", 'check-plan-progress.py" "${ARGS[@]}"'
    case("F6 the banner guard is invoked BEFORE the blocking check that can exit early",
         _obs in _hook and _blk in _hook and _hook.index(_obs) < _hook.index(_blk))
    case("F6b the hook uses REPO_ROOT — $ROOT is empty and would block every stop",
         "$ROOT/scripts" not in _hook)


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
    case("a DIRECTORY inside the repo is not a file this turn edited",
         _edit_inside_repo([str(ROOT / "scripts")], ROOT) is False)
    case("...while a real file in that directory is",
         _edit_inside_repo([str(ROOT / "scripts" / "check-banner-armed.py")], ROOT) is True)

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

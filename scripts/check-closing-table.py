#!/usr/bin/env python3
"""Did a turn CLOSE A JOB and then report it in prose instead of a CHECK / RESULT table?

WHY THIS EXISTS (user decision 2026-09-20)
-------------------------------------------
`docs/process-checklists.md` → *Closing a job: the CHECK / RESULT table* has required the table
since 2026-09-04. Asked on 2026-09-20 whether a "done protocol" existed, the assistant searched,
found it, and discovered it had been closing with prose anyway — then "fixed" that by writing the
rule into a memory file.

⛔ THAT FIX IS THE ONE THIS PROJECT HAS ALREADY MEASURED FAILING, for this exact class of rule.
`docs/dev-process.md` on the selection card: *"the rule was written in §19 and two memory files and
still went **1-for-3 in one session**, because it was recalled rather than read."* It stopped being
violated when `enforce-selection-card.sh` began REFUSING the malformed card at the point it was
offered. A record is not a mechanism. This file is the mechanism.

WARN-ONLY, AND LOGGED
---------------------
Like `check-banner-armed.py`, this reports and never blocks — a blocking gate on a formatting miss
is the kind this repo has measured getting switched off (backlog #56). Warn-only is a real risk
here, so every firing is APPENDED TO A LOG, and the log is what can later answer *does it
false-alarm?* Nothing parses that file; it exists to be counted by a human.

THE RULE, stated so its false alarms are predictable
-----------------------------------------------------

    warn  <=>  the judged turn CLOSED A JOB,  AND
               its FINAL assistant text block contains no CHECK / RESULT table.

"CLOSED A JOB" is read from the turn's own Bash calls — `git commit`, `git push`, `gh pr merge`, or
a `begin-plan.py --tick`. ⚠ AN ATTEMPT IS NOT WORK: a `tool_use` whose paired `tool_result` is an
error does not count, which is `check-banner-armed.edited_paths_of`'s measured rule applied to a
different tool.

WHY THE TRIGGER LIVES IN THE TURN AND NOT IN A SENTINEL
--------------------------------------------------------
`check-banner-armed.py` needs a journal because its trigger (*was a plan armed when that turn
ended?*) is external state that has already changed by the time the turn is judged. Ours is not:
whether a turn ran `git push` is a permanent property of that turn's own records. So there is no
journal, no sample, no late-flush, and no way for the two to disagree about a turn.

WHAT THIS CANNOT SEE — stated here and in the warning text, because a guard that covers half a rule
and reads as covering all of it is a hazard this repo has paid for more than once:

  * ⛔ **WHETHER THE ROWS COULD HAVE COME BACK ❌.** That is rule 3 of the format, and it is the
    rule that separates a real table from a decorated assertion. A shape check sees a table. It
    cannot see whether the checks were falsifiable. Same stated bound as the selection-card guard's
    *"SHAPE ONLY: it cannot see two options that are the SAME WORK."*
  * **A job closed WITHOUT git.** Measured on the day this was written: a memory-index
    consolidation merged 39 files, split an oversized file and rewrote an index — touching no
    tracked file, so this guard is blind to it.
  * **A close split across text blocks.** Only the FINAL assistant text block is read. A table
    emitted and then followed by a chatty paragraph in a separate block reads as absent.
  * **`git commit` mid-job.** A turn that commits and continues next turn looks identical to a turn
    that commits and closes. This is the main false-alarm source, it is why the guard is warn-only,
    and the log is how its rate gets measured rather than guessed.

WHY NOT READ THE CLOSING SENTENCE — backlog #48 already tried
---------------------------------------------------------------
A Stop hook that read the closing SENTENCE for a promise was built and DISCARDED: *"satisfiable by
rewording while still doing nothing."* This reads a STRUCTURAL marker that the checklist requires
and the user visually checks for. Rewording it away means dropping the convention they enforce, so
the evasion is visible to them — the property the sentence-reader never had. Same discriminator
`check-banner-armed.py` records for the step banner.

ONE TURN OF LATENCY, INHERENTLY
--------------------------------
The in-flight turn's final assistant message is NOT flushed when Stop hooks run (measured twice by
timestamp, backlog #96). So this judges the PREVIOUS completed turn, whose text is always flushed by
the next Stop. A warning therefore arrives one turn after the miss. That is a property of the
transcript, not a choice.

FAILS CLOSED ON ITS OWN BLINDNESS. No readable transcript, or a transcript that parses to zero
records, is CANNOT RUN — never a quiet pass. ⚠ But a judged turn with NO assistant text at all is
QUIET and deliberately so: that is a partway stop, which `check-banner-armed.py` owns. Two guards
warning about one turn is the duplicate-mechanism shape this repo has a script to hunt.

Exit codes for --decide:  0 = nothing to say   1 = WARN (non-blocking)   2 = CANNOT RUN

Usage:
    python3 scripts/check-closing-table.py --decide      # reads the Stop-hook payload on stdin
    python3 scripts/check-closing-table.py --self-test   # 37 cases
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
WARN_LOG = ROOT / ".claude/closing-table-warnings.log"

QUIET = 0
WARN = 1
CANNOT_RUN = 2

# ── The trigger ────────────────────────────────────────────────────────────────────────────────
# Each entry is (label, regex). The label is what the warning names, so a reader is told WHICH act
# closed the job rather than being asked to guess.
#
# ⚠ ANCHORED AT A WORD BOUNDARY, NOT A BARE SUBSTRING. `git push` appears inside plenty of strings
# that never push — the hook's own comments, a grep pattern, this docstring. The boundary does not
# make that impossible (a heredoc containing the literal command still matches); it makes the
# common accidental case quiet. The residue is a false WARN, which is the safe direction for a
# warn-only observer and is recorded in the log where its rate can be counted.
CLOSING_ACTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a commit",      re.compile(r"(?<![\w-])git\s+commit(?![\w-])")),
    ("a push",        re.compile(r"(?<![\w-])git\s+push(?![\w-])")),
    ("a merge",       re.compile(r"(?<![\w-])gh\s+pr\s+merge(?![\w-])")),
    ("a plan tick",   re.compile(r"begin-plan\.py[^\n|;&]*--tick(?![\w-])")),
)

# ── The marker ─────────────────────────────────────────────────────────────────────────────────
# A markdown table whose header names a check column and a result column, followed by the
# separator row that makes it a table rather than a line of prose containing two pipes.
_SEPARATOR = re.compile(r"^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")
_CHECK_CELL = re.compile(r"^\s*\**\s*check(?:s)?\s*\**\s*$", re.I)
_RESULT_CELL = re.compile(r"^\s*\**\s*result(?:s)?\s*\**\s*$", re.I)


def _cells(line: str) -> list[str] | None:
    """PURE. The cells of a markdown table row, or None if this line is not one.

    A row must open AND close with a pipe. Requiring both is what keeps an ordinary sentence
    containing a pipe — `grep -c foo | wc -l` inside prose — from being read as a table row.
    """
    s = line.strip()
    if not s.startswith("|") or not s.endswith("|") or len(s) < 3:
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def has_closing_table(text: str) -> bool:
    """PURE. True iff `text` contains a CHECK / RESULT table.

    ⛔ THE SEPARATOR ROW IS REQUIRED, and that is the whole defence against a false pass. Without
    it, a single line `| check | result |` typed inside a sentence — or inside THIS docstring —
    satisfies the guard. With it, the marker is a real rendered table, which is the thing the user
    visually checks for.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        cells = _cells(line)
        if not cells or len(cells) < 2:
            continue
        if not any(_CHECK_CELL.match(c) for c in cells):
            continue
        if not any(_RESULT_CELL.match(c) for c in cells):
            continue
        if i + 1 < len(lines) and _SEPARATOR.match(lines[i + 1]):
            return True
    return False


# ── Borrowing the turn rule rather than copying it ─────────────────────────────────────────────
def _load_banner_guard():
    """Import check-banner-armed.py BY PATH — the hyphen makes it un-importable by name.

    ⛔ BORROWED, NOT COPIED. Turn segmentation is ONE rule with ONE owner. A second implementation
    of it here would drift from the first, and this repo runs `check-vocabulary-collisions.py`
    precisely to hunt duplicate mechanisms. The `hasattr` sweep below turns a silent divergence
    into a loud ImportError naming the symbol that moved.
    """
    spec = importlib.util.spec_from_file_location(
        "_banner_armed", ROOT / "scripts" / "check-banner-armed.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/check-banner-armed.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in ("_parse_records", "windows", "judged_window", "texts_of"):
        if not hasattr(mod, name):
            raise ImportError(
                f"scripts/check-banner-armed.py no longer defines {name} — this guard borrows the "
                f"turn rule rather than copying it.")
    return mod


# ── Reading the judged turn ────────────────────────────────────────────────────────────────────
def _content_blocks(rec: dict) -> list[dict]:
    content = (rec.get("message") or {}).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _errored_tool_ids(records: list[dict]) -> set[str]:
    """PURE. tool_use ids whose paired result reported an error.

    ⚠ AN ATTEMPT IS NOT WORK. A `git push` that was refused by a hook did not close anything, and
    counting it would make the guard fire on turns where nothing shipped. This is
    `check-banner-armed.edited_paths_of`'s measured rule, applied to Bash.
    """
    bad: set[str] = set()
    for rec in records:
        for block in _content_blocks(rec):
            if block.get("type") == "tool_result" and block.get("is_error") is True:
                tid = block.get("tool_use_id")
                if isinstance(tid, str):
                    bad.add(tid)
    return bad


def closing_acts_of(records: list[dict]) -> list[str]:
    """PURE. Labels of the job-closing acts this turn actually completed. Deduped, ordered.

    Only `Bash` tool_use blocks are read. An act named in prose — including the assistant merely
    SAYING it will push — is not an act, which is the distinction backlog #48 was discarded for
    failing to make.
    """
    errored = _errored_tool_ids(records)
    found: list[str] = []
    for rec in records:
        for block in _content_blocks(rec):
            if block.get("type") != "tool_use" or block.get("name") != "Bash":
                continue
            if block.get("id") in errored:
                continue
            command = (block.get("input") or {}).get("command")
            if not isinstance(command, str):
                continue
            for label, pattern in CLOSING_ACTS:
                if pattern.search(command) and label not in found:
                    found.append(label)
    return found


def _log_display() -> str:
    """The log path as a reader should see it. NEVER raises.

    ⚠ MEASURED BY THIS FILE'S OWN SELF-TEST, first run: this was `WARN_LOG.relative_to(ROOT)`, and
    `relative_to` RAISES when the path is not under the root — which is exactly what happens when a
    test redirects the log to a temp dir, and would also happen for any future caller that moves it.
    A warn-only observer that raises is worse than one that says nothing, because a traceback out of
    a Stop hook is indistinguishable from the hook being broken.
    """
    try:
        return str(WARN_LOG.relative_to(ROOT))
    except ValueError:
        return str(WARN_LOG)


def decide(final_text: str | None, acts: list[str]) -> tuple[int, str]:
    """PURE. The whole rule. `final_text` is None when the turn emitted no assistant text.

    Returns (exit code, message).
    """
    if not acts:
        return QUIET, ""
    if final_text is None:
        # A partway stop. check-banner-armed.py owns that class; two guards warning about one turn
        # is the duplicate-mechanism shape this repo hunts with a script.
        return QUIET, ""
    if has_closing_table(final_text):
        return QUIET, ""
    return WARN, (
        f"CLOSING TABLE MISSING — the previous turn completed {', '.join(acts)} and closed with "
        f"prose.\n"
        f"  docs/process-checklists.md -> 'Closing a job: the CHECK / RESULT table' requires a "
        f"table, one row per claim, evidence IN the row.\n"
        f"  Why not prose: a paragraph asserting the work is indistinguishable from a paragraph "
        f"asserting it wrongly (measured 2026-09-04).\n"
        f"  This is a WARNING, not a block, and it is appended to {_log_display()}.\n"
        f"  ⛔ SHAPE ONLY: this guard sees THAT a table is present. It cannot see whether every "
        f"row was a check that could have come back ❌ — which is rule 3, and the rule that "
        f"separates a real table from a decorated assertion.")


def log_line(acts: list[str], when: str, session: str) -> str:
    """One appended record. Tab-separated so the log stays greppable and countable."""
    return f"{when}\t{session or '-'}\t{'+'.join(acts) or '-'}\n"


def _append_log(line: str) -> bool:
    """Best effort. A log that cannot be written must not turn an observer into a traceback."""
    try:
        WARN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with WARN_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except OSError:
        return False


def final_text_of(texts: list[str]) -> str | None:
    """PURE. The closing message: the LAST non-empty assistant text block, or None."""
    for text in reversed(texts):
        if text.strip():
            return text
    return None


def run_decide(payload: str) -> int:
    try:
        data = json.loads(payload) if payload.strip() else {}
    except (ValueError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    session_id = str(data.get("session_id", "") or "")

    path = data.get("transcript_path")
    records: list[dict] | None = None
    if isinstance(path, str) and path:
        try:
            banner = _load_banner_guard()
            records = banner._parse_records(Path(path).read_text().splitlines())
        except (OSError, ImportError) as exc:
            print(f"CANNOT RUN: {exc}", file=sys.stderr)
            records = None

    if not records:
        print("CANNOT RUN: the stop-hook payload named no readable transcript, so this check could "
              "not look for a closing table. TREAT THIS AS NOT RUN — do not read the absence of a "
              "warning as 'no table was owed'.", file=sys.stderr)
        return CANNOT_RUN

    banner = _load_banner_guard()
    judged = banner.judged_window(banner.windows(records))
    if judged is None:
        return QUIET            # no subject yet — QUIET, never CANNOT RUN

    acts = closing_acts_of(judged.body)
    code, message = decide(final_text_of(banner.texts_of(judged.body)), acts)

    if code == WARN:
        when = _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        _append_log(log_line(acts, when, session_id))
        print(message, file=sys.stderr)
    return code


# ── Self-test ──────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    import tempfile

    failures: list[str] = []

    def check(label: str, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # ---- has_closing_table: the marker ----------------------------------------------------
    good = "| check | result |\n|---|---|\n| a | ✅ |"
    check("table: canonical", has_closing_table(good), True)
    check("table: bold header cells",
          has_closing_table("| **check** | **result** |\n|---|---|\n| a | ✅ |"), True)
    check("table: plural header",
          has_closing_table("| checks | results |\n|---|---|\n| a | ✅ |"), True)
    check("table: case-insensitive",
          has_closing_table("| CHECK | RESULT |\n|---|---|\n| a | ✅ |"), True)
    check("table: aligned separator",
          has_closing_table("| check | result |\n|:---|---:|\n| a | ✅ |"), True)
    check("table: extra columns",
          has_closing_table("| check | result | note |\n|---|---|---|\n| a | ✅ | b |"), True)
    check("table: preceded by prose",
          has_closing_table("Done.\n\n| check | result |\n|---|---|\n| a | ✅ |"), True)
    # ⛔ The separator is what stops this docstring — and any sentence — passing.
    check("table: header with NO separator row",
          has_closing_table("| check | result |\nnot a table"), False)
    check("table: words in prose only",
          has_closing_table("I ran every check and the result was green."), False)
    check("table: wrong headers",
          has_closing_table("| step | status |\n|---|---|\n| a | ✅ |"), False)
    check("table: check column but no result column",
          has_closing_table("| check | note |\n|---|---|\n| a | b |"), False)
    check("table: result column but no check column",
          has_closing_table("| item | result |\n|---|---|\n| a | b |"), False)
    check("table: unterminated row", has_closing_table("| check | result\n|---|---|"), False)
    check("table: empty text", has_closing_table(""), False)
    check("table: a piped shell line in prose",
          has_closing_table("run `grep -c foo | wc -l` to check the result"), False)

    # ---- closing_acts_of: the trigger -------------------------------------------------------
    def bash(cmd, tid="t1"):
        return {"type": "assistant",
                "message": {"content": [{"type": "tool_use", "id": tid, "name": "Bash",
                                         "input": {"command": cmd}}]}}

    def result(tid="t1", error=False):
        return {"type": "user",
                "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                         "is_error": error}]}}

    check("acts: git commit", closing_acts_of([bash("git commit -m x")]), ["a commit"])
    check("acts: git push", closing_acts_of([bash("git push -u origin b")]), ["a push"])
    check("acts: gh pr merge", closing_acts_of([bash("gh pr merge 1 --auto")]), ["a merge"])
    check("acts: plan tick",
          closing_acts_of([bash("python3 scripts/begin-plan.py --tick")]), ["a plan tick"])
    check("acts: read-only git is not an act", closing_acts_of([bash("git log --oneline")]), [])
    check("acts: git status is not an act", closing_acts_of([bash("git status --short")]), [])
    check("acts: none", closing_acts_of([bash("ls -la")]), [])
    check("acts: deduped",
          closing_acts_of([bash("git push", "a"), bash("git push", "b")]), ["a push"])
    check("acts: two distinct, in order",
          closing_acts_of([bash("git commit -m x", "a"), bash("git push", "b")]),
          ["a commit", "a push"])
    # ⚠ An attempt is not work: a push the hook refused did not close anything.
    check("acts: errored tool_use ignored",
          closing_acts_of([bash("git push", "a"), result("a", error=True)]), [])
    check("acts: successful tool_use counted",
          closing_acts_of([bash("git push", "a"), result("a", error=False)]), ["a push"])
    check("acts: non-Bash tool ignored",
          closing_acts_of([{"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "x", "name": "Edit",
               "input": {"command": "git push"}}]}}]), [])
    check("acts: substring is not a match",
          closing_acts_of([bash("git pushover; legit-commit")]), [])
    check("acts: prose mentioning a push is not an act",
          closing_acts_of([{"type": "assistant",
                            "message": {"content": [{"type": "text",
                                                     "text": "next I will git push"}]}}]), [])

    # ---- decide: the whole rule --------------------------------------------------------------
    check("decide: no acts -> quiet", decide("anything", [])[0], QUIET)
    check("decide: acts + table -> quiet", decide(good, ["a push"])[0], QUIET)
    check("decide: acts + prose -> warn", decide("All done!", ["a push"])[0], WARN)
    check("decide: acts + no text at all -> quiet (partway stop is the banner guard's)",
          decide(None, ["a push"])[0], QUIET)
    check("decide: warning names the act", "a push" in decide("All done!", ["a push"])[1], True)
    check("decide: warning states the SHAPE-ONLY bound",
          "SHAPE ONLY" in decide("All done!", ["a push"])[1], True)

    # ---- _log_display: found by this suite's FIRST run ---------------------------------------
    # ⚠ These two exist because `decide` used `WARN_LOG.relative_to(ROOT)` and that RAISES for a
    # path outside the repo. Without them the fix is unfalsifiable: reverting it would go green.
    _real = globals()["WARN_LOG"]
    try:
        globals()["WARN_LOG"] = ROOT / ".claude/x.log"
        check("log display: inside the repo is relative", _log_display(), ".claude/x.log")
        globals()["WARN_LOG"] = Path("/tmp/elsewhere/x.log")
        check("log display: outside the repo does not raise", _log_display(),
              "/tmp/elsewhere/x.log")
        check("decide: renders a redirected log without raising",
              "/tmp/elsewhere/x.log" in decide("All done!", ["a push"])[1], True)
    finally:
        globals()["WARN_LOG"] = _real

    # ---- final_text_of -----------------------------------------------------------------------
    check("final: last non-empty wins", final_text_of(["a", "b"]), "b")
    check("final: skips trailing blank", final_text_of(["a", "   "]), "a")
    check("final: all blank -> None", final_text_of(["", "  "]), None)
    check("final: empty list -> None", final_text_of([]), None)

    # ---- run_decide: the boundaries ----------------------------------------------------------
    check("run: empty payload -> CANNOT RUN", run_decide(""), CANNOT_RUN)
    check("run: malformed json -> CANNOT RUN", run_decide("{not json"), CANNOT_RUN)
    check("run: payload is a list -> CANNOT RUN", run_decide("[]"), CANNOT_RUN)
    check("run: no transcript_path -> CANNOT RUN", run_decide('{"session_id":"s"}'), CANNOT_RUN)
    check("run: unreadable transcript -> CANNOT RUN",
          run_decide('{"transcript_path":"/nonexistent/x.jsonl"}'), CANNOT_RUN)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        empty = tmp / "empty.jsonl"
        empty.write_text("")
        check("run: transcript with zero records -> CANNOT RUN",
              run_decide(json.dumps({"transcript_path": str(empty)})), CANNOT_RUN)

        # A real two-turn transcript: turn 1 pushes and closes with prose, turn 2 is live.
        def user(text):
            return {"type": "user", "message": {"role": "user", "content": text}}

        def say(text):
            return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}

        def write(name, records):
            p = tmp / name
            p.write_text("\n".join(json.dumps(r) for r in records))
            return p

        prose = write("prose.jsonl", [
            user("do it"), bash("git push"), say("All done, pushed it."),
            user("next"), say("working"),
        ])
        # WARN_LOG is repo-relative; redirect it so the self-test cannot write to the real log.
        real_log = globals()["WARN_LOG"]
        globals()["WARN_LOG"] = tmp / "warnings.log"
        try:
            check("run: judged turn pushed + prose -> WARN",
                  run_decide(json.dumps({"transcript_path": str(prose), "session_id": "s"})), WARN)
            check("run: the warning was logged",
                  (tmp / "warnings.log").exists() and "a push" in (tmp / "warnings.log").read_text(),
                  True)

            tabled = write("tabled.jsonl", [
                user("do it"), bash("git push"), say("Done.\n\n" + good),
                user("next"), say("working"),
            ])
            check("run: judged turn pushed + table -> QUIET",
                  run_decide(json.dumps({"transcript_path": str(tabled)})), QUIET)

            noacts = write("noacts.jsonl", [
                user("hi"), say("hello"), user("next"), say("working"),
            ])
            check("run: judged turn closed nothing -> QUIET",
                  run_decide(json.dumps({"transcript_path": str(noacts)})), QUIET)

            # ⛔ THE LIVE TURN IS NEVER JUDGED — one turn of latency is the point, not a bug.
            live_only = write("live.jsonl", [user("do it"), bash("git push"), say("All done.")])
            check("run: only one turn -> QUIET (no subject yet)",
                  run_decide(json.dumps({"transcript_path": str(live_only)})), QUIET)
        finally:
            globals()["WARN_LOG"] = real_log

    declared = re.search(r"--self-test\s+#\s*(\d+)\s+cases", __doc__ or "")
    total = 37
    if not declared or int(declared.group(1)) != total:
        failures.append(
            f"declared self-test count {declared.group(1) if declared else 'MISSING'} != {total} "
            f"— the docstring is the pinned declaration read by check-selftest-counts.py")

    if failures:
        print(f"check-closing-table --self-test: {len(failures)} FAILED", file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"{total}/{total} passed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Warn when a turn closed a job and reported it in prose, not a CHECK/RESULT table.")
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.decide:
        sys.exit(run_decide(sys.stdin.read()))
    ap.print_help()
    sys.exit(CANNOT_RUN)

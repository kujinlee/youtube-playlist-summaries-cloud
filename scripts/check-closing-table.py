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
  * **THE LAST TURN OF A SESSION IS NEVER JUDGED.** One turn of latency means the final close of a
    session has no following Stop to judge it. Structural, and the direction is under-firing.
  * **A CLOSE REACHED BY ANOTHER SPELLING.** `alias g=git; g push`, a wrapper script, or
    `subprocess.run(["git","push"])` inside a heredoc are all invisible — the trigger reads shell
    text, not process trees. Likewise a heredoc BODY line beginning `git push` fires falsely.
  * **AN HTML TABLE.** `<table><tr><th>Check</th>…` is a perfectly readable closing table and is
    not recognised; only the markdown form is. Deliberate — `process-checklists.md` shows markdown.
  * **A PARTIALLY-SUCCESSFUL ACT.** `is_error` on the paired result means "no close happened", but
    a `git push` can update one ref and fail another. That reads here as no close at all.

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

FAILS CLOSED ON ITS OWN BLINDNESS. No readable transcript, a transcript that parses to zero
records, or a borrowed turn rule that no longer behaves as borrowed, is CANNOT RUN — never a quiet
pass. ⟳ r1 Codex (High): a judged turn with NO assistant text at all used to be QUIET, deferred to
`check-banner-armed.py` as "a partway stop". That was wrong. Its class is *announced N steps,
stopped at i<N with no plan armed*; a turn that COMPLETED a close and said nothing is this rule's
subject in its purest form, and deferring made it the one case both guards ignored. It now WARNS.

Exit codes for --decide:  0 = nothing to say   1 = WARN (non-blocking)   2 = CANNOT RUN

Usage:
    python3 scripts/check-closing-table.py --decide      # reads the Stop-hook payload on stdin
    python3 scripts/check-closing-table.py --self-test   # 84 cases
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
# closed the job rather than being asked to guess. Every pattern is anchored at `^` and matched
# against ONE COMMAND SEGMENT, never against the whole command string.
#
# ⛔ MATCHING ANYWHERE IN THE COMMAND WAS THE FIRST DESIGN AND IT WAS WRONG. Measured while writing
# this file, before any reviewer saw it: `grep -n 'git push' file` and `echo 'git push'` both fired,
# and `git commit --dry-run` counted as a commit. A `grep` for that exact string is something this
# session runs routinely, so the guard would have nagged about work that never happened — and a
# warn-only observer that cries wolf is one that gets switched off (backlog #56). Splitting into
# command segments and anchoring makes the match mean "this segment RUNS git", which is the claim
# the rule actually rests on.
CLOSING_ACTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # `git -C <dir> push` and friends: the global options sit between `git` and the subcommand.
    ("a commit",      re.compile(r"^git\s+(?:-[A-Za-z]\s+\S+\s+)*commit(?![\w-])")),
    ("a push",        re.compile(r"^git\s+(?:-[A-Za-z]\s+\S+\s+)*push(?![\w-])")),
    ("a merge",       re.compile(r"^gh\s+pr\s+merge(?![\w-])")),
    # ⚠ THE INTERPRETER IS PART OF THE SEGMENT. Anchoring at `^` broke this the moment the trigger
    # moved to command segments: the real invocation is `python3 scripts/begin-plan.py --tick`, so
    # the segment starts with `python3`, not with the script. Caught by the suite, not by reading.
    # `--tick` is required — `--resume` and `--pause` advance nothing and close nothing.
    ("a plan tick",
     re.compile(r"^(?:\S*python[\d.]*\s+)?\S*begin-plan\.py(?![\w-]).*(?<![\w-])--tick(?![\w-])")),
)

# A segment that only REHEARSES or DESCRIBES an act did not perform one.
# ⟳ r1 Codex, High: `--help` was missing. `git push --help` and `gh pr merge --help` print a manual
# page and close nothing, and both fired.
_REHEARSAL = re.compile(r"(?<![\w-])--(?:dry-run|help)(?![\w-])")

# Leading `VAR=value` assignments are part of the invocation, not a different command.
_ENV_PREFIX = re.compile(r"^(?:[A-Za-z_][A-Za-z_0-9]*=(?:\"[^\"]*\"|'[^']*'|\S*)\s+)+")

# Shell operators that end one command and begin another. A newline counts: a multi-line Bash call
# is many commands. ⚠ A heredoc BODY is also newline-separated, so a heredoc whose text contains a
# line beginning `git push` still matches — that bound is named in the docstring and left standing
# rather than chased with a shell parser this guard has no business containing.
_SEGMENT_SPLIT = re.compile(r"\n|;|&&|\|\||\||&")


def mask_quotes(command: str) -> str:
    """PURE. `command` with every quoted span blanked, LENGTH PRESERVED.

    ⛔ TWO DEFECTS, ONE ROOT — found by probing round 1's own fixes before round 2 returned. The
    shell operators and the rehearsal flags were both matched against raw text, so quotes were
    invisible:
      * `echo "a; git push"` SPLIT on the quoted `;` and the tail `git push"` read as a real push;
      * `git commit -m "document --dry-run"` was SKIPPED as a rehearsal because the flag appeared
        in the COMMIT MESSAGE.
    One fires falsely and one misses a real close — opposite directions, same cause. Blanking
    quoted spans (rather than removing them) keeps every offset, so the masked string can be split
    and matched directly.

    ⚠ It does NOT understand heredocs, backslash escapes or nested shells; those stay stated bounds.
    """
    out: list[str] = []
    quote: str | None = None
    for ch in command:
        if quote is not None:
            out.append(" ")
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def command_segments(command: str) -> list[str]:
    """PURE. `command` split into individually-runnable segments, env prefixes stripped.

    A segment is what a `^`-anchored pattern is allowed to match, so that "the command mentions
    git push" and "the command runs git push" stop being the same question. Operates on the
    QUOTE-MASKED form — see `mask_quotes`.
    """
    out: list[str] = []
    for raw in _SEGMENT_SPLIT.split(mask_quotes(command)):
        seg = raw.strip()
        # ⟳ r2 Codex, Medium — ORDER MATTERS, and it was backwards. Env prefixes were stripped
        # BEFORE the subshell paren, so `(GIT_SSH=x git push)` left `GIT_SSH=x git push` with the
        # prefix intact — `^git` never matched and a real push was missed. Brackets first, then
        # assignments, then trailing brackets.
        seg = seg.lstrip("({").lstrip()
        while True:
            stripped = _ENV_PREFIX.sub("", seg, count=1)
            if stripped == seg:
                break
            seg = stripped.strip()
        seg = seg.rstrip(")}").rstrip()
        if seg:
            out.append(seg)
    return out

# ── The marker ─────────────────────────────────────────────────────────────────────────────────
# A markdown table whose header names a check column and a result column, followed by the
# separator row that makes it a table rather than a line of prose containing two pipes.
# ⛔ ONE DASH IS ENOUGH, and requiring two was a measured false negative. GitHub-flavoured markdown
# needs a single `-` per cell, so `|-|-|` renders as a perfectly good table — and the first version
# of this regex said `-{2,}`, which would have nagged the user for a table they had written
# correctly. A warn-only observer's false alarms are the thing that gets it switched off.
_SEPARATOR = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
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
    # ⟳ r1 Codex, Medium: a table INSIDE A CODE FENCE satisfied the marker. A closing message that
    # merely SHOWS an example table — this file's own docstring does — is not a report.
    #
    # ⛔ A FENCE ONLY HIDES THINGS IF IT CLOSES, and the first version of this got that wrong: it
    # toggled on every marker, so a SINGLE stray ``` earlier in the message suppressed every table
    # after it, turning a correct report into a false warning. Probed before round 2 returned.
    # Fence regions are therefore paired up first, and an unterminated marker fences nothing.
    markers = [i for i, ln in enumerate(lines)
               if ln.lstrip().startswith("```") or ln.lstrip().startswith("~~~")]
    fenced_lines: set[int] = set()
    for a, b in zip(markers[::2], markers[1::2]):
        fenced_lines.update(range(a, b + 1))
    for i, line in enumerate(lines):
        if i in fenced_lines:
            continue
        cells = _cells(line)
        if not cells or len(cells) < 2:
            continue
        if not any(_CHECK_CELL.match(c) for c in cells):
            continue
        if not any(_RESULT_CELL.match(c) for c in cells):
            continue
        if i + 1 >= len(lines) or not _SEPARATOR.match(lines[i + 1]):
            continue
        # ⟳ r1 Codex, Medium: a header plus a separator and NO CLAIM ROWS was accepted. An empty
        # table reports nothing, and rule 1 of the format is *one row per claim* — zero claims
        # cannot satisfy it.
        if i + 2 < len(lines) and _cells(lines[i + 2]):
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

    # ⛔ THE hasattr SWEEP ALONE IS THEATRE — r1 Codex, Medium, and it is right. It catches a
    # RENAME and is blind to the thing that actually matters: `judged_window` changing from "the
    # previous completed turn" to "the live turn" would silently change this guard's SUBJECT while
    # every symbol still resolved. So the borrowed semantics are ASSERTED, not assumed, on a
    # two-turn fixture whose answer is unambiguous: the judged window must be the FIRST, never the
    # live one, and a single-window transcript must have no subject at all.
    probe = [
        {"type": "user", "message": {"role": "user", "content": "one"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "a"}]}},
        {"type": "user", "message": {"role": "user", "content": "two"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "b"}]}},
    ]
    try:
        wins = mod.windows(probe)
        judged = mod.judged_window(wins)
        texts = mod.texts_of(judged.body) if judged is not None else None
        lone = mod.judged_window(mod.windows(probe[:2]))
    except Exception as exc:                       # noqa: BLE001 — any failure is CANNOT RUN
        raise ImportError(f"check-banner-armed.py's turn rule could not be exercised: {exc}")
    if len(wins) != 2 or texts != ["a"] or lone is not None:
        raise ImportError(
            "check-banner-armed.py's turn rule has CHANGED SEMANTICS without changing names: a "
            f"two-turn probe gave windows={len(wins)}, judged texts={texts!r}, "
            f"single-window judged={lone!r}; expected 2, ['a'], None. This guard judges the "
            "PREVIOUS completed turn and cannot borrow a rule that no longer means that.")
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
            for segment in command_segments(command):
                if _REHEARSAL.search(segment):
                    continue                      # `--dry-run` performs nothing
                for label, pattern in CLOSING_ACTS:
                    if pattern.search(segment) and label not in found:
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
        # ⟳ r1 Codex, High — THIS USED TO RETURN QUIET, and the reasoning was wrong. It deferred to
        # check-banner-armed.py as "a partway stop". But that guard's class is *announced N steps,
        # stopped at i<N with no plan armed*; it says nothing about a turn that COMPLETED a
        # job-closing act and emitted no text at all. That turn has a close and no report, which is
        # this rule's subject in its purest form — the user is told nothing whatsoever. Deferring
        # made it the one case both guards ignored.
        return WARN, (
            f"CLOSING TABLE MISSING — the previous turn completed {', '.join(acts)} and reported "
            f"NOTHING: no closing message at all.\n"
            f"  docs/process-checklists.md -> 'Closing a job: the CHECK / RESULT table'.\n"
            f"  This is a WARNING, not a block.")
    if has_closing_table(final_text):
        return QUIET, ""
    return WARN, (
        f"CLOSING TABLE MISSING — the previous turn completed {', '.join(acts)} and closed with "
        f"prose.\n"
        f"  docs/process-checklists.md -> 'Closing a job: the CHECK / RESULT table' requires a "
        f"table, one row per claim, evidence IN the row.\n"
        f"  Why not prose: a paragraph asserting the work is indistinguishable from a paragraph "
        f"asserting it wrongly (measured 2026-09-04).\n"
        # ⟳ r2 Codex, Low: this used to ASSERT "it is appended to <path>", and `run_decide` then
        # appended a contradicting sentence when the write failed. The emitted warning still
        # carried the false claim. `decide` is pure and cannot know whether the write succeeded,
        # so it no longer claims — the caller, which does know, states the outcome.
        f"  This is a WARNING, not a block.\n"
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

    # ⟳ r1 Codex, Medium: LOADED ONCE. The second `_load_banner_guard()` call sat outside this
    # try, so an import or semantic failure there escaped as a traceback and exit 1 — not the
    # documented CANNOT RUN (2). A guard with two failure sites documents one of them.
    path = data.get("transcript_path")
    banner = None
    records: list[dict] | None = None
    if isinstance(path, str) and path:
        try:
            banner = _load_banner_guard()
            records = banner._parse_records(Path(path).read_text().splitlines())
        except (OSError, ImportError) as exc:
            print(f"CANNOT RUN: {exc}", file=sys.stderr)
            banner, records = None, None

    if banner is None or not records:
        print("CANNOT RUN: the stop-hook payload named no readable transcript, so this check could "
              "not look for a closing table. TREAT THIS AS NOT RUN — do not read the absence of a "
              "warning as 'no table was owed'.", file=sys.stderr)
        return CANNOT_RUN

    judged = banner.judged_window(banner.windows(records))
    if judged is None:
        return QUIET            # no subject yet — QUIET, never CANNOT RUN

    acts = closing_acts_of(judged.body)
    code, message = decide(final_text_of(banner.texts_of(judged.body)), acts)

    if code == WARN:
        when = _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        # ⟳ r1 Codex, Low: the message used to PROMISE the warning had been logged while
        # `_append_log` could return False on OSError and nobody looked. A guard that misreports
        # its own evidence trail is the shape this repo keeps paying for, one level in.
        if _append_log(log_line(acts, when, session_id)):
            message += f"\n  Logged to {_log_display()}."
        else:
            message += (f"\n  ⚠ AND THIS WARNING COULD NOT BE LOGGED — {_log_display()} is not "
                        f"writable, so it is NOT in the record and cannot be counted later.")
        print(message, file=sys.stderr)
    return code


# ── Self-test ──────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    import tempfile

    failures: list[str] = []

    def _safe(fn):
        """Run `fn`, turning any exception into a VALUE.

        ⛔ A raise inside the suite kills it with a traceback and prints no `[FAIL] ` line, so
        check-plan-code scores the mutation RED-BUT-UNATTRIBUTABLE — noticed, uncreditable.
        Measured on this file's own manifest twice.
        """
        try:
            return fn()
        except Exception as exc:                            # noqa: BLE001
            return f"RAISED {type(exc).__name__}"

    def check(label: str, got, want):
        # ⛔ THE FAILURE LINE IS A CONTRACT, NOT A STYLE CHOICE — r1 Codex, Blocking.
        # `check-plan-code.run_mutations` attributes a kill by taking lines whose strip() starts
        # `[FAIL] ` and splitting on the LAST ": got ". The first version of this printer emitted
        # `  ✗ {label}: got {got!r}, want {want!r}` — a comma, and no marker — so Codex measured
        # 9 of 10 mutations going RED-BUT-UNATTRIBUTABLE: the suite noticed, and the harness could
        # not tell which case noticed. That is this project's recorded *a report format is a
        # CONTRACT* defect, where 12 mutations reported "0 red cases" over a line shape nothing
        # could parse. Keep this format byte-identical to check-merge-ready.py's.
        if got != want:
            failures.append(f"{label}: got {got!r} want {want!r}")

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
    # ⛔ Measured false negative of the first regex, which demanded two dashes. `|-|-|` is valid
    # GFM and renders; rejecting it would nag the user for a table they wrote correctly.
    check("table: single-dash separator is valid markdown",
          has_closing_table("| check | result |\n|-|-|\n| a | ✅ |"), True)
    check("table: indented inside a list item",
          has_closing_table("- done:\n\n  | check | result |\n  |---|---|\n  | a | ✅ |"), True)
    check("table: extra columns",
          has_closing_table("| check | result | note |\n|---|---|---|\n| a | ✅ | b |"), True)
    check("table: preceded by prose",
          has_closing_table("Done.\n\n| check | result |\n|---|---|\n| a | ✅ |"), True)
    # ⛔ The separator is what stops this docstring — and any sentence — passing.
    check("table: header with NO separator row",
          has_closing_table("| check | result |\nnot a table"), False)
    # ⛔ The case above cannot kill the separator mutation on its own: with no separator AND no
    # data row, the data-row rule rejects it for a different reason and the mutation survives.
    # This input has a data row and no separator, so ONLY the separator rule can reject it.
    check("table: rows with no separator between them are not a table",
          has_closing_table("| check | result |\n| a | b |\n| c | d |"), False)
    check("table: words in prose only",
          has_closing_table("I ran every check and the result was green."), False)
    check("table: wrong headers",
          has_closing_table("| step | status |\n|---|---|\n| a | ✅ |"), False)
    check("table: check column but no result column",
          has_closing_table("| check | note |\n|---|---|\n| a | b |"), False)
    check("table: result column but no check column",
          has_closing_table("| item | result |\n|---|---|\n| a | b |"), False)
    check("table: unterminated row", has_closing_table("| check | result\n|---|---|"), False)
    # ⟳ r1 Codex, Blocking: the mutation for the closing-pipe rule SURVIVED, because the case above
    # still passes once `endswith` is dropped — `_cells` then chops the final `t` from `result` and
    # the header stops matching for a DIFFERENT reason. This input dies properly: without the rule,
    # `| check | result |x` slices to a header that does match.
    check("table: trailing text after the closing pipe is not a row",
          has_closing_table("| check | result |x\n|---|---|\n| a | b |"), False)
    check("table: empty text", has_closing_table(""), False)
    check("table: a piped shell line in prose",
          has_closing_table("run `grep -c foo | wc -l` to check the result"), False)
    # ⟳ r1 Codex, Medium — both measured, both accepted before the fix.
    check("table: inside a code fence is an EXAMPLE, not a report",
          has_closing_table("```\n| check | result |\n|---|---|\n| a | b |\n```"), False)
    check("table: tilde fence too",
          has_closing_table("~~~\n| check | result |\n|---|---|\n| a | b |\n~~~"), False)
    check("table: header + separator but NO claim rows reports nothing",
          has_closing_table("| check | result |\n|---|---|"), False)
    check("table: a real table AFTER a closed fence still counts",
          has_closing_table("```\ncode\n```\n\n| check | result |\n|---|---|\n| a | b |"), True)
    # ⛔ An UNTERMINATED fence must hide nothing — otherwise one stray ``` earlier in the message
    # silences a correct report. This is the fence fix's own falsifier.
    check("table: an unclosed fence before the table hides nothing",
          has_closing_table("```\nsnippet\n\n| check | result |\n|---|---|\n| a | b |"), True)
    # A blank line ENDS a markdown table, so a header+separator followed by a blank and then a row
    # is two tables, the first of which has no claims. Rejecting it is correct, not a miss.
    check("table: a blank line ends the table, so the header has no claim rows",
          has_closing_table("| check | result |\n|---|---|\n\n| a | b |"), False)

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
    check("acts: --resume is not a tick",
          closing_acts_of([bash("python3 scripts/begin-plan.py --resume")]), [])
    # ⟳ r1 Codex, High: `--help` prints a manual page and closes nothing.
    check("acts: git push --help closes nothing",
          closing_acts_of([bash("git push --help")]), [])
    check("acts: gh pr merge --help closes nothing",
          closing_acts_of([bash("gh pr merge --help")]), [])
    # ⛔ Quote-blindness, both directions, probed before r2 returned.
    check("acts: a quoted operator does not split the command",
          closing_acts_of([bash('echo "a; git push"')]), [])
    check("acts: a rehearsal flag inside a commit MESSAGE is not a rehearsal",
          closing_acts_of([bash('git commit -m "document --dry-run"')]), ["a commit"])
    check("acts: a real pipe still splits",
          closing_acts_of([bash("git push 2>&1 | tee log")]), ["a push"])
    check("mask: quoted spans are blanked, length preserved",
          (mask_quotes('a "bc" d'), len(mask_quotes('a "bc" d'))), ("a      d", 8))
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
    # ⛔ These six are the measured false fires of the FIRST design, which matched anywhere in the
    # command string. `grep -n 'git push'` is a command this session runs routinely.
    check("acts: echo of the command is not the command",
          closing_acts_of([bash("echo 'git push'")]), [])
    check("acts: grep for the command is not the command",
          closing_acts_of([bash("grep -n 'git push' file")]), [])
    check("acts: --dry-run rehearses and performs nothing",
          closing_acts_of([bash("git commit --dry-run")]), [])
    check("acts: && chain still counts the real act",
          closing_acts_of([bash("cd /x && git push origin b")]), ["a push"])
    check("acts: an env prefix is part of the invocation",
          closing_acts_of([bash("GIT_SSH=x git push")]), ["a push"])
    check("acts: a git global option before the subcommand",
          closing_acts_of([bash("git -C /repo push")]), ["a push"])
    check("acts: a git global option before commit too",
          closing_acts_of([bash("git -C /repo commit -m x")]), ["a commit"])
    # ⟳ r2 Codex, Medium: brackets had to be stripped BEFORE env assignments.
    check("acts: a subshell with an env prefix is still a push",
          closing_acts_of([bash("(GIT_SSH=x git push)")]), ["a push"])
    check("acts: a plain subshell is still a push",
          closing_acts_of([bash("(git push)")]), ["a push"])
    # Assert the PROPERTY, not a transcribed literal — the first version of this case hand-counted
    # the spaces and was off by one, which is the same class of error the guard exists to catch.
    check("mask: a different string keeps length and drops every quote",
          (lambda s, r: (len(r) == len(s), "'" in r or '"' in r, r.startswith("git commit -m")))(
              "git commit -m 'hi there'", mask_quotes("git commit -m 'hi there'")),
          (True, False, True))
    check("segments: splits on newline, ; and &&",
          command_segments("a\nb; c && d"), ["a", "b", "c", "d"])
    check("segments: strips an env prefix", command_segments("A=1 B=2 git push"), ["git push"])
    check("acts: prose mentioning a push is not an act",
          closing_acts_of([{"type": "assistant",
                            "message": {"content": [{"type": "text",
                                                     "text": "next I will git push"}]}}]), [])

    # ---- decide: the whole rule --------------------------------------------------------------
    check("decide: no acts -> quiet", decide("anything", [])[0], QUIET)
    check("decide: acts + table -> quiet", decide(good, ["a push"])[0], QUIET)
    check("decide: acts + prose -> warn", decide("All done!", ["a push"])[0], WARN)
    check("decide: the pure verdict makes NO claim about logging",
          "appended" in decide("All done!", ["a push"])[1] or
          "Logged to" in decide("All done!", ["a push"])[1], False)
    # ⟳ r1 Codex, High: this asserted QUIET and the deferral to the banner guard was wrong.
    check("decide: acts + NO text at all -> warn (a close with no report at all)",
          decide(None, ["a push"])[0], WARN)
    check("decide: the no-report warning says so",
          "reported\nNOTHING" in decide(None, ["a push"])[1].replace("reported NOTHING", "reported\nNOTHING"),
          True)
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
        # ⛔ CATCH, DO NOT LET IT CRASH. If the guard raises here the suite dies with a
        # traceback and prints NO `[FAIL] ` line, so check-plan-code cannot attribute the kill
        # and the mutation is scored unattributable — red, but useless as evidence. Converting
        # the exception into a value keeps the report parseable, which is the whole contract.
        check("log display: outside the repo does not raise", _safe(_log_display),
              "/tmp/elsewhere/x.log")
        # ⟳ r2 Codex, Low: decide() no longer renders the log path at all — the CALLER states the
        # outcome, because only it knows whether the write succeeded. What must still never raise
        # is _log_display itself, asserted directly above.
        check("log display: a repo-relative path is unchanged by the redirect guard",
              _safe(lambda: _log_display().startswith("/tmp/elsewhere")), True)
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
                  _safe(lambda: run_decide(json.dumps(
                      {"transcript_path": str(prose), "session_id": "s"}))), WARN)
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
    total = 84
    if not declared or int(declared.group(1)) != total:
        failures.append(
            f"declared self-test count {declared.group(1) if declared else 'MISSING'} != {total} "
            f"— the docstring is the pinned declaration read by check-selftest-counts.py")

    if failures:
        print(f"check-closing-table --self-test: {len(failures)} FAILED")
        for f in failures:
            print(f"  [FAIL] {f}")
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

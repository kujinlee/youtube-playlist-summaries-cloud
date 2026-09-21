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
journal, no sample and no late-flush.

⟳ r7 (independent Claude half), Medium — THIS PARAGRAPH USED TO END *"and no way for the two to
disagree about a turn"*, AND THAT WAS FALSE WHEN IT WAS WRITTEN. `coalesce_injected` below
re-segments the borrowed windows for THIS guard only, so at one Stop `check-banner-armed.py` can
judge window *k* while this file judges a merged *k-1..k*. They disagree about the subject by
construction. That is a deliberate composition, argued in `coalesce_injected`'s own docstring — it
answers a narrower question (*was that boundary a PERSON?*) on top of the borrowed one — but a
correct design described by a false sentence is still a false sentence, and this one sat at the top
of the file through six review rounds.

⚠ THE OPEN HALF, NAMED RATHER THAN QUIETLY DROPPED: if a notification-split turn is the wrong
subject here, it is plausibly the wrong subject for the banner guard too — its *announced N steps,
stopped at i<N* class has the same false-alarm shape on a fragment cut between a banner and its
work. That delta has NOT been measured, in either direction. Backlog #148. Do not apply this fold
there on suspicion: changing the borrowed rule is precisely what `coalesce_injected` refuses to do.

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
    `subprocess.run(["git","push"])` are invisible — the trigger reads shell text, not process
    trees. ⟳ The heredoc half is NARROWED, not closed — `mask_heredocs` blanks bodies, handles a
    QUEUE of terminators and matches them strictly (POSIX: exact line; `<<-` strips TABS only).
    ⚠ The first version of this sentence said CLOSED and r4 refuted it with two leaks; an opener
    whose delimiter never appears now opens nothing, so a left-shift (`x << y`) and a quoted
    `<<EOF` are inert. It still does not understand `$(...)`, a backslash-continued `<<`, or a
    delimiter built by expansion.
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
    python3 scripts/check-closing-table.py --self-test   # 132 cases
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


# A record the SYSTEM injected into the user channel. Not a person taking a turn.
# ⟳ r7 (independent Claude half), High — A TEAMMATE MESSAGE SPLITS A TURN EXACTLY LIKE A
# NOTIFICATION, and it was the highest-volume real case while being the one absent from this list.
# Measured over 766 real transcripts by replaying the shipped functions at every turn boundary:
#
#     window opener                             occurrences   isMeta   folded before r7
#     <task-notification                            650         None        yes
#     Another Claude session sent a message         332         None        NO
#     <system-reminder  (AS AN OPENER)                0          —          yes
#
# Folding the teammate case removes 125 of 744 warnings — 16.8% of everything this guard has ever
# emitted was a fragment manufactured by a boundary no person made. Note the third row: half of
# this list was unexercised by reality while the real case went unlisted, which is why the number
# above is the justification and the enumeration is not.
#
# ⛔ DO NOT "DERIVE" THIS FROM check-banner-armed._META_IS_REALLY_A_MESSAGE, and the r7 review's own
# first draft made that mistake. That tuple names records which ARE a real new instruction —
# `_meta_carries_a_message` returning True KEEPS the boundary — so consulting it argues the exact
# opposite of this fold. It is also unreachable for these records: `_is_turn_boundary` only
# consults it when `isMeta is True`, and all 332 teammate records carry `isMeta: None`.
# The warrant is this function's OWN predicate, one line down: *was that boundary a PERSON?*
# A teammate Claude session is not a person. That is the whole test, and it is why the two guards
# are allowed to answer differently here (see the docstring at the top of this file).
_INJECTED = re.compile(
    r"^\s*(?:<(?:task-notification|system-reminder)\b"
    r"|Another Claude session sent a message)")


def coalesce_injected(windows_in: list, make) -> list:
    """Fold a window opened by a SYSTEM-INJECTED record back into the turn it interrupted.

    ⛔ FOUND ON THE REAL TRANSCRIPT, not in a fixture — every test before this used synthetic
    records. A `<task-notification>` record is `type: "user"`, carries no `isMeta`, and the borrowed
    boundary rule therefore calls it a NEW TURN. So a background job finishing mid-turn SPLITS that
    turn, and the split lands between the act and the report: the fragment before the notification
    has the `git push` and no table, and would WARN falsely. This session receives such
    notifications constantly, so the false-alarm rate would have been material.

    ⚠ THIS IS NOT A SECOND IMPLEMENTATION OF THE BORROWED RULE, and the distinction is the whole
    justification. `check-banner-armed.windows` answers *where does a turn boundary fall* and is
    still the only answer to that question. This answers a different and narrower one — *was that
    boundary a PERSON?* — and composes on top of the first. Changing the borrowed rule instead would
    silently change the banner guard's subject, which is precisely what this file refuses to do.
    """
    out: list = []
    for window in windows_in:
        opener = getattr(window, "opener", None)
        content = (opener or {}).get("message", {}).get("content") if opener else None
        if out and isinstance(content, str) and _INJECTED.match(content):
            prev = out[-1]
            out[-1] = make(prev.opener, list(prev.body) + [opener] + list(window.body))
        else:
            out.append(window)
    return out


# ── The EFFECT veto ────────────────────────────────────────────────────────────────────────────
# ⛔ EFFECTS VETO AN ACT; THEY DO NOT DETECT ONE — and that asymmetry is the whole design, measured
# rather than assumed. Over 209 real Bash calls in one session:
#
#     trigger                 fires   false+   MISSES
#     command text (shipped)    13       3        0
#     effect signature only      7       2        3      <- 3 real commits whose `[branch sha]`
#     union (text OR effect)     -       3        0         line was cut off by `| tail -3`
#
# So replacing text with effects trades false alarms for MISSES, and a guard that exists to catch
# something must not under-fire. But a VETO is safe in exactly the way detection is not: output
# truncation yields NO veto, so a truncated result leaves the act standing. The veto only fires on
# POSITIVE evidence that the act did not happen — git's own refusal phrasing, or our own tool's.
#
# Measured example: `begin-plan.py --tick` printing `refusing: this plan is PAUSED`. The command
# text says a step was ticked; the output says nothing was.
_VETO: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a plan tick", re.compile(r"^refusing:", re.M)),
    ("a commit",    re.compile(r"^nothing to commit|^no changes added to commit", re.M)),
    ("a push",      re.compile(r"^Everything up-to-date$|^\s*! \[rejected\]|^error: failed to push",
                               re.M)),
    ("a merge",     re.compile(r"is not mergeable|^X Pull request", re.M)),
)


# The signature the act prints when it SUCCEEDS — git's own wording, or our own tool's. Derived by
# reading real tool_results out of a transcript, not from memory.
_SUCCESS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a commit",    re.compile(r"^\[\S+ [0-9a-f]{7,40}\] ", re.M)),
    # ⛔ `To <url>` IS NOT A SUCCESS SIGNATURE — git prints it on FAILURE too. A rejected push
    # emits:
    #     To https://github.com/owner/repo.git
    #      ! [rejected]        main -> main (fetch first)
    #     error: failed to push some refs to '...'
    # With the bare `To` line in this pattern, adjudication saw "success" in that very output and
    # stood the veto down, so a genuinely rejected push counted as a close. Only a REF UPDATE
    # (`sha..sha  ref -> ref`) or a new branch says the push landed; the rejected form carries
    # `!` where the shas would be, so it cannot match either.
    ("a push",      re.compile(r"^\s*\* \[new branch\]\s"
                               r"|^\s+[0-9a-f]{7,40}\.\.[0-9a-f]{7,40}\s+\S+ -> \S+$", re.M)),
    ("a plan tick", re.compile(r"^ticked step \d+ of \d+ in ", re.M)),
)


def vetoed(act: str, outputs: str) -> bool:
    """PURE. True iff `outputs` carries POSITIVE evidence that `act` did not happen.

    ⟳ r5 Codex, High — A FAILURE PHRASE IS NOT EVIDENCE IF THE SUCCESS SIGNATURE IS ALSO THERE.
    The veto was paired to the CALL (r4's fix) but the act's unit is a SEGMENT, and one call runs
    many segments. Codex's repro, which is not exotic:

        cat old-push.log       # the log happens to contain `error: failed to push some refs`
        git push               # and this one succeeds

    One call, one combined output, so the stale error vetoed the real push — a MISS, which is the
    direction this branch has consistently refused. Output cannot be attributed to a segment, so
    attribution is not the fix; ADJUDICATION is. If the same output ALSO carries the act's success
    signature, the failure phrase did not come from the act that matters, and the veto stands down.

    This reuses the effect signatures measured during the redesign — the ones that were rejected as
    a DETECTOR because `| tail` truncates them. As a tie-breaker their truncation is harmless: no
    signature simply means the veto behaves as it did before.
    """
    if not any(label == act and pattern.search(outputs) for label, pattern in _VETO):
        return False
    return not any(label == act and pattern.search(outputs) for label, pattern in _SUCCESS)


# ── Heredoc bodies ─────────────────────────────────────────────────────────────────────────────
# ⛔ MEASURED FALSE POSITIVES, in this very session: two review-prompt heredocs containing the text
# `gh pr merge` and `begin-plan.py … --tick` were counted as acts. A heredoc BODY is data being
# written to a file, never a command being run. This is the same closed-form treatment that fixed
# quoting — blank the region, preserve the lines — and NOT another open-ended lexer rule.
_HEREDOC_START = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z_0-9]*)\2")


def mask_heredocs(command: str) -> str:
    """PURE. `command` with every heredoc BODY blanked, line count preserved.

    ⟳ r4 Codex, Medium — TWO LEAKS, both measured, both from taking the easy version:

      * **one pending terminator.** `cat <<A <<B` opens TWO heredocs on one line; tracking a single
        terminator closed at `A` and let the rest — still B's body — back into detection.
        A QUEUE is required, and it drains in order, which is what the shell does.
      * **`line.strip() == terminator`.** POSIX ends a `<<` heredoc only on a line that is EXACTLY
        the delimiter, with no leading whitespace; `<<-` strips leading TABS and nothing else. The
        lenient version ended the body at ` EOF` (a space, inside the data) and released the real
        lines after it.

    Both repros reported a `git push` that was heredoc DATA. The docstring bound this closes is
    written as "the common case", not "closed" — see below; the first version overclaimed.
    """
    lines = command.split("\n")

    def _terminated(terminator: str, dashed: bool, after: int) -> bool:
        """Does this opener's delimiter actually appear on a later line?

        ⛔ AN OPENER THAT NEVER CLOSES OPENS NOTHING — the same rule this file already applies to
        markdown fences, and it is the only fix that does not require a shell parser. Found by
        probing before r5 reported, and both instances were MISSES, the dangerous direction:

            python3 -c "print(x << y)"   -> `<< y` read as a heredoc named `y`
            echo "use <<EOF here"        -> a QUOTED `<<EOF` read as an opener

        Each swallowed every real command after it. Requiring the delimiter to exist makes a
        left-shift and a quoted mention inert, because neither is followed by a line that is just
        `y` or `EOF`. A genuinely malformed heredoc leaks — but that command would not run either.
        """
        for later in lines[after + 1:]:
            if (later.lstrip("\t") if dashed else later) == terminator:
                return True
        return False

    out: list[str] = []
    pending: list[tuple[str, bool]] = []          # (terminator, strip-leading-tabs)
    for index, line in enumerate(lines):
        if not pending:
            out.append(line)
            for found in _HEREDOC_START.finditer(line):
                terminator, dashed = found.group(3), found.group(1) == "-"
                if _terminated(terminator, dashed, index):
                    pending.append((terminator, dashed))
            continue
        out.append("")                            # every body line, and the terminator itself
        terminator, dashed = pending[0]
        candidate = line.lstrip("\t") if dashed else line
        if candidate == terminator:
            pending.pop(0)
    return "\n".join(out)


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
    i = 0
    while i < len(command):
        ch = command[i]
        # ⟳ r3 Codex, High — BACKSLASH ESCAPES. The first version treated any matching quote byte
        # as a closer, so `echo "a \"; git push"` masked to a string whose `;` and `git push` were
        # OUTSIDE quotes, producing a FALSE act; and `git commit -m "a \" --dry-run"` exposed the
        # flag from inside the message and MISSED a real commit. Both directions, one omission.
        # In POSIX shell a backslash escapes inside double quotes and NOT inside single quotes.
        if quote == '"' and ch == "\\" and i + 1 < len(command):
            out.append("  ")
            i += 2
            continue
        if quote is None and ch == "\\" and i + 1 < len(command):
            out.append(command[i:i + 2])       # outside quotes it escapes one char; keep both
            i += 2
            continue
        if quote is not None:
            out.append(" ")
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(" ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def command_segments(command: str) -> list[str]:
    """PURE. `command` split into individually-runnable segments, env prefixes stripped.

    A segment is what a `^`-anchored pattern is allowed to match, so that "the command mentions
    git push" and "the command runs git push" stop being the same question. Operates on the
    QUOTE-MASKED form — see `mask_quotes`.
    """
    out: list[str] = []
    for raw in _SEGMENT_SPLIT.split(mask_quotes(mask_heredocs(command))):
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
    # ⟳ r3 Codex, High — A FENCE IS CLOSED BY ITS OWN CHARACTER, AT ITS OWN LENGTH OR LONGER.
    # Pairing markers purely by POSITION associated a stray ``` with a later ~~~, so a real table
    # sitting between them was hidden — and under this file's own "an unterminated marker fences
    # nothing" rule it should have been visible. CommonMark: the closer must use the same character
    # and be at least as long as the opener.
    def _marker(ln: str) -> tuple[str, int] | None:
        s = ln.lstrip()
        for ch in ("`", "~"):
            if s.startswith(ch * 3):
                return ch, len(s) - len(s.lstrip(ch))
        return None

    fenced_lines: set[int] = set()
    open_at: int | None = None
    open_mark: tuple[str, int] | None = None
    for i, ln in enumerate(lines):
        mark = _marker(ln)
        if mark is None:
            continue
        if open_at is None:
            open_at, open_mark = i, mark
        elif open_mark is not None and mark[0] == open_mark[0] and mark[1] >= open_mark[1]:
            fenced_lines.update(range(open_at, i + 1))
            open_at, open_mark = None, None
    # An opener that never closes fences NOTHING — deliberately left unrecorded.
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
    for name in ("_parse_records", "windows", "judged_window", "texts_of", "TurnWindow"):
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


def paired_outputs(records: list[dict]) -> dict[str, str]:
    """PURE. tool_use id -> the text of ITS OWN result.

    ⛔ PAIRED, NOT WHOLE-WINDOW — r4 Codex, High, and it FALSIFIED THE PROPERTY THIS DESIGN RESTS
    ON. The first version concatenated every result in the turn and applied it to every act, on the
    reasoning that "a turn that pushes in one call and reports the failure in the next should still
    be vetoed". That reasoning is wrong, and the counter-example is ordinary:

        git push            -> error: failed to push some refs      (rejected, then rebased)
        git push            -> To github.com ...                     (succeeds)

    Whole-window scoping let the FIRST call's failure cancel the SECOND call's real push, so the
    guard MISSED a close — exactly what the comment two screens up promised could never happen.
    A veto is only safe if it cannot outlive the call that produced its evidence.

    It also closes the sibling hole: with whole-window text, any command printing the literal
    `Everything up-to-date` — a `cat`, a `printf`, this review document itself — cancelled a real
    push. Paired scoping makes the evidence come from the act's own invocation or not at all.

    ⟳ r5 Codex, Medium — PAIRED BY ORDER AND BY UNIQUENESS, not by dictionary overwrite. The first
    version accepted any result with a matching id, so two things produced MISSES:

      * a result appearing BEFORE its `tool_use` was accepted as that call's output;
      * a DUPLICATE id let a later result overwrite an earlier one, so a success could be replaced
        by a veto phrase.

    Neither occurs in the transcripts checked, which is exactly why it must be asserted rather than
    assumed — an invariant nobody checks is one nobody notices breaking. A violated pairing now
    yields NO output for that call, which means NO veto, which means no miss.
    """
    out: dict[str, str] = {}
    seen_uses: set[str] = set()
    ambiguous: set[str] = set()
    for rec in records:
        for block in _content_blocks(rec):
            kind = block.get("type")
            if kind == "tool_use":
                tid = block.get("id")
                if isinstance(tid, str):
                    if tid in seen_uses:
                        ambiguous.add(tid)       # the id is not unique; trust nothing about it
                    seen_uses.add(tid)
                continue
            if kind != "tool_result":
                continue
            tid = block.get("tool_use_id")
            if not isinstance(tid, str) or tid not in seen_uses:
                continue                          # a result before its use pairs with nothing
            if tid in out:
                ambiguous.add(tid)                # two results for one call
                continue
            content = block.get("content")
            if isinstance(content, str):
                out[tid] = content
            elif isinstance(content, list):
                out[tid] = "\n".join(x.get("text", "") for x in content
                                     if isinstance(x, dict) and isinstance(x.get("text"), str))
    for tid in ambiguous:
        out.pop(tid, None)
    return out


def closing_acts_of(records: list[dict]) -> list[str]:
    """PURE. Labels of the job-closing acts this turn actually completed. Deduped, ordered.

    Only `Bash` tool_use blocks are read. An act named in prose — including the assistant merely
    SAYING it will push — is not an act, which is the distinction backlog #48 was discarded for
    failing to make.
    """
    errored = _errored_tool_ids(records)
    outputs = paired_outputs(records)
    found: list[str] = []
    for rec in records:
        for block in _content_blocks(rec):
            if block.get("type") != "tool_use" or block.get("name") != "Bash":
                continue
            tid = block.get("id")
            if tid in errored:
                continue
            command = (block.get("input") or {}).get("command")
            if not isinstance(command, str):
                continue
            # ⛔ THE VETO IS EVALUATED PER CALL, against THIS call's own result (r4 High). It only
            # ever removes, and a call with no result vetoes nothing — so truncation still cannot
            # produce a miss, and one call's failure can no longer cancel another call's success.
            own_output = outputs.get(tid, "") if isinstance(tid, str) else ""
            for segment in command_segments(command):
                if _REHEARSAL.search(segment):
                    continue                      # `--dry-run` performs nothing
                for label, pattern in CLOSING_ACTS:
                    if (pattern.search(segment) and label not in found
                            and not vetoed(label, own_output)):
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

    judged = banner.judged_window(
        coalesce_injected(banner.windows(records), banner.TurnWindow))
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
    cases = 0

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
        nonlocal cases
        cases += 1
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
    # ⟳ r3 Codex, High — a fence closes only with its OWN character, at its own length or longer.
    check("table: a stray ``` is not closed by a later ~~~",
          has_closing_table("``` stray\n| check | result |\n|-|-|\n| a | b |\n~~~\ncode\n~~~"), True)
    check("table: a matched backtick fence still hides its table",
          has_closing_table("```\n| check | result |\n|---|---|\n| a | b |\n```"), False)
    check("table: a longer closer still closes a shorter opener",
          has_closing_table("```\n| check | result |\n|---|---|\n| a | b |\n````"), False)
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
    # ⟳ r3 Codex, High — escaped quotes, BOTH directions from one omission.
    check("acts: an ESCAPED quote does not end the quoted span",
          closing_acts_of([bash(r'echo "a \"; git push"')]), [])
    check("acts: an escaped quote does not expose a rehearsal flag",
          closing_acts_of([bash(r'git commit -m "a \" --dry-run"')]), ["a commit"])
    check("acts: a single-quoted span has no escapes",
          closing_acts_of([bash("echo 'a; git push'")]), [])
    # ⛔ MEASURED FALSE POSITIVES in this session: two review-prompt heredocs whose BODY named
    # `gh pr merge` and `begin-plan.py --tick` were counted as acts. A heredoc body is data.
    check("acts: a heredoc BODY is data, not a command",
          closing_acts_of([bash("cat > /tmp/p.md <<'EOF'\ngh pr merge 1\nEOF")]), [])
    check("acts: an unquoted heredoc body is blanked too",
          closing_acts_of([bash("cat > /tmp/p.md <<EOF\ngit push\nEOF")]), [])
    check("acts: a real command AFTER a heredoc still counts",
          closing_acts_of([bash("cat > /tmp/p.md <<'EOF'\ngit push\nEOF\ngit commit -m x")]),
          ["a commit"])
    check("heredoc mask: line count is preserved",
          len(mask_heredocs("a <<'E'\nb\nE\nc").split("\n")), 4)

    # ---- the EFFECT VETO: effects remove an act, they never add one -------------------------
    def _with_output(cmd, out):
        return [bash(cmd, "v1"),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "v1", "content": out}]}}]

    check("veto: a REFUSED tick is not a tick",
          closing_acts_of(_with_output("python3 scripts/begin-plan.py --tick",
                                       "refusing: this plan is PAUSED")), [])
    check("veto: a successful tick survives",
          closing_acts_of(_with_output("python3 scripts/begin-plan.py --tick",
                                       "ticked step 4 of 4 in .claude/plans/x.md")), ["a plan tick"])
    check("veto: nothing to commit is not a commit",
          closing_acts_of(_with_output("git commit -m x", "nothing to commit, working tree clean")),
          [])
    check("veto: Everything up-to-date is not a push",
          closing_acts_of(_with_output("git push", "Everything up-to-date")), [])
    # ⛔ THE PROPERTY THAT MAKES THE VETO SAFE: no output means no veto, so a truncated result
    # leaves the act standing. This is why effects veto and do not detect.
    check("veto: an EMPTY result vetoes nothing (truncation must not cause a miss)",
          closing_acts_of(_with_output("git push", "")), ["a push"])
    check("veto: unrelated output vetoes nothing",
          closing_acts_of(_with_output("git push", "some unrelated chatter")), ["a push"])
    # ⛔ A VETO IS PER-ACT. Without the `label == act` test, ANY failure phrase would veto EVERY
    # act — a plan refusing to tick would cancel a real push in the same turn.
    check("veto: another act's failure phrase does not veto this one",
          closing_acts_of(_with_output("git push", "refusing: this plan is PAUSED")), ["a push"])

    # ⛔ r4 Codex, HIGH — this FALSIFIED the property the veto design rests on. Whole-window
    # scoping let call 1's failure cancel call 2's real push, so the veto INTRODUCED a miss.
    def _two_calls(c1, o1, err1, c2, o2):
        return [bash(c1, "p1"),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "p1", "content": o1, "is_error": err1}]}},
                bash(c2, "p2"),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "p2", "content": o2}]}}]

    check("veto: a FAILED push does not cancel a later successful one",
          closing_acts_of(_two_calls("git push", "error: failed to push some refs", True,
                                     "git push", "To github.com\n   b85f697c..3b5e4a18  main -> main")),
          ["a push"])
    check("veto: unrelated stdout elsewhere in the turn cannot impersonate evidence",
          closing_acts_of(_two_calls("git push", "To github.com\n   b85f697c..3b5e4a18  main -> main", False,
                                     "cat notes.txt", "Everything up-to-date")),
          ["a push"])

    # ⛔ r5 Codex, HIGH — the veto was paired to the CALL, but the act's unit is a SEGMENT, and one
    # call runs many. A stale error in a cat'ed log vetoed a real push in the same call. The fix is
    # adjudication, not attribution: if the SUCCESS signature is present too, the failure phrase
    # did not come from the act that matters.
    check("veto: a stale failure in the same call cannot beat a success signature",
          closing_acts_of(_with_output(
              "cat old-push.log\ngit push",
              "error: failed to push some refs\nTo github.com:a/b.git\n   b85f697c..3b5e4a18  main -> main")),
          ["a push"])
    check("veto: without a success signature the failure still vetoes",
          closing_acts_of(_with_output("git push", "error: failed to push some refs")), [])
    # ⛔ `To <url>` IS PRINTED ON FAILURE TOO. With it in _SUCCESS, adjudication saw
    # "success" in a REJECTED push's own output and stood the veto down. Found by probing
    # git's real wording before r6 reported. Only a ref update or a new branch means it landed.
    check("veto: a REJECTED push is still vetoed despite its `To <url>` line",
          closing_acts_of(_with_output("git push", "To https://github.com/o/r.git\n ! [rejected]        main -> main (fetch first)\nerror: failed to push some refs to 'https://github.com/o/r.git'")), [])
    check("veto: a real ref update IS a success signature",
          closing_acts_of(_with_output("git push",
              "To https://github.com/o/r.git\n   b85f697c..3b5e4a18  br -> br")), ["a push"])
    # ⛔ r6 Codex's own probe shape: a WRAPPER that masks the exit status, so `is_error` is False
    # and only the veto can catch the failure. `git push; echo done` always exits 0.
    check("veto: a rejected push inside a status-masking wrapper is still vetoed",
          closing_acts_of(_with_output("git push; echo done",
              "To github.com:o/r.git\n ! [rejected]        main -> main (fetch first)\n"
              "error: failed to push some refs\ndone")), [])
    check("veto: a new branch IS a success signature",
          closing_acts_of(_with_output("git push",
              "To https://github.com/o/r.git\n * [new branch]        br -> br")), ["a push"])
    # ⛔ This case exists because the success-signature fix made the WHOLE-WINDOW mutation
    # survivable: with every output joined, call 2's success signature rescued the act and the
    # mutation went unnoticed. Here call 2's output is TRUNCATED (empty, as `| tail` leaves it),
    # so only paired scoping can save the push — which is exactly the property under test.
    check("veto: a truncated success is saved by PAIRING, not by adjudication",
          closing_acts_of(_two_calls("cat old.log", "Everything up-to-date", False,
                                     "git push", "")),
          ["a push"])

    # ⛔ r5 Codex, MEDIUM — pairing must respect ORDER and UNIQUENESS, or a veto attaches to the
    # wrong call. Neither shape occurs in real transcripts, which is why it is asserted.
    def _dup_id():
        return [bash("git push", "d"),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "d",
                     "content": "To github.com\n   b85f697c..3b5e4a18  main -> main"}]}},
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "d",
                     "content": "Everything up-to-date"}]}}]

    check("pairing: a DUPLICATE id is ambiguous, so it vetoes nothing",
          closing_acts_of(_dup_id()), ["a push"])
    check("pairing: a result BEFORE its tool_use pairs with nothing",
          closing_acts_of([
              {"type": "user", "message": {"content": [
                  {"type": "tool_result", "tool_use_id": "z", "content": "Everything up-to-date"}]}},
              bash("git push", "z")]), ["a push"])

    # ⛔ r4 Codex, MEDIUM — two heredoc leaks, both reported a `git push` that was DATA.
    check("heredoc: TWO heredocs in one command both stay blanked",
          closing_acts_of([bash("cat <<A <<B\nx\nA\ngit push\nB")]), [])
    check("heredoc: a space-indented terminator does NOT end the body",
          closing_acts_of([bash("cat <<EOF\n EOF\ngit push\nEOF")]), [])
    check("heredoc: `<<-` strips leading TABS, so a tabbed terminator DOES end it",
          closing_acts_of([bash("cat <<-EOF\n\tEOF\ngit push")]), ["a push"])
    # ⛔ AN OPENER THAT NEVER CLOSES OPENS NOTHING — both of these were MISSES, found by probing
    # before r5 reported. A fake opener swallowed every real command after it.
    check("heredoc: a left-shift by a NAME is not an opener",
          closing_acts_of([bash('python3 -c "print(x << y)"\ngit push')]), ["a push"])
    check("heredoc: a QUOTED <<EOF mentioned in text is not an opener",
          closing_acts_of([bash('echo "use <<EOF here"\ngit push')]), ["a push"])
    check("heredoc: an unterminated REAL heredoc leaks rather than swallowing",
          closing_acts_of([bash("cat <<EOF\ngit push")]), ["a push"])
    check("heredoc mask: a different heredoc, so the parameter is not a constant",
          mask_heredocs("cat <<X\nsecret\nX").split("\n")[1], "")
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

    # ---- coalesce_injected: a boundary is only a turn if a PERSON made it -------------------
    class _W:
        def __init__(self, opener, body):
            self.opener, self.body = opener, body

    def _win(content, body):
        return _W({"type": "user", "message": {"content": content}} if content is not None else None,
                  body)

    _a, _b = _win("real question", ["A"]), _win("<task-notification> x", ["B"])
    _merged = coalesce_injected([_a, _b], _W)
    check("coalesce: a notification does not start a turn", len(_merged), 1)
    check("coalesce: its records join the turn it interrupted",
          [x for x in _merged[0].body if isinstance(x, str)], ["A", "B"])
    check("coalesce: a REAL user message still starts a turn",
          len(coalesce_injected([_a, _win("another question", ["B"])], _W)), 2)
    check("coalesce: a system-reminder is injected too",
          len(coalesce_injected([_a, _win("<system-reminder>hi", ["B"])], _W)), 1)
    check("coalesce: a leading injected window has nothing to join",
          len(coalesce_injected([_win("<task-notification> x", ["A"])], _W)), 1)
    # ⟳ r7 High, the 332-opener case. The exact opener text as it appears on the real transcript.
    _tm = coalesce_injected(
        [_a, _win("Another Claude session sent a message: <teammate-msg>do X</teammate-msg>",
                  ["B"])], _W)
    check("coalesce: a TEAMMATE message does not start a turn", len(_tm), 1)
    check("coalesce: the teammate fragment's records join the interrupted turn",
          [x for x in _tm[0].body if isinstance(x, str)], ["A", "B"])
    # ⛔ THE NEAR-MISS IS THE POINT. The fold keys on the phrase at the START of the content; a
    # person QUOTING it mid-sentence is still a person taking a turn, and swallowing their turn
    # would be a MISS — the direction this guard must never fail in.
    check("coalesce: the phrase QUOTED mid-message is still a real turn",
          len(coalesce_injected(
              [_a, _win("why did Another Claude session sent a message appear?", ["B"])], _W)), 2)
    check("coalesce: a near-miss spelling is NOT folded",
          len(coalesce_injected([_a, _win("Another Claude session said something", ["B"])], _W)), 2)
    # Vary `make` with the REAL type the caller passes, so the parameter is not a constant AND the
    # composition is exercised against the actual namedtuple rather than only a stand-in.
    def _real_turnwindow_case():
        TW = _load_banner_guard().TurnWindow
        return len(coalesce_injected(
            [TW({"type": "user", "message": {"content": "q"}}, []),
             TW({"type": "user", "message": {"content": "<task-notification> x"}}, [])], TW))

    check("coalesce: composes with the REAL TurnWindow the caller uses",
          _safe(_real_turnwindow_case), 1)

    # ---- the borrowed-rule drift alarm, exercised by actually DRIFTING it -------------------
    # ⟳ r3 Codex, Medium: the semantic probe had no mutation, because nothing exercised it. A
    # `hasattr` sweep cannot see `judged_window` changing MEANING while every symbol resolves, so
    # the probe is the only thing standing between that drift and a silently different subject.
    # This stands up a fake check-banner-armed.py and asserts the loader REFUSES it.
    _fake_module = "\n".join([
        "from typing import NamedTuple",
        "class TurnWindow(NamedTuple):",
        "    opener: dict | None",
        "    body: list",
        "def _parse_records(lines): return []",
        "def windows(records): return [TurnWindow(None, list(records))]",
        "def judged_window(wins): return wins[-1]   # DRIFTED: live turn, not the previous one",
        "def texts_of(records): return []",
    ])

    def _drifted_loader_case():
        with tempfile.TemporaryDirectory() as d:
            fake_root = Path(d)
            (fake_root / "scripts").mkdir()
            (fake_root / "scripts" / "check-banner-armed.py").write_text(_fake_module)
            real_root = globals()["ROOT"]
            globals()["ROOT"] = fake_root
            try:
                _load_banner_guard()
                return "LOADED"                     # must not happen
            except ImportError as exc:
                return "REFUSED" if "CHANGED SEMANTICS" in str(exc) else f"WRONG: {exc}"
            finally:
                globals()["ROOT"] = real_root

    check("guard: a drifted borrowed turn rule is CANNOT RUN",
          _safe(_drifted_loader_case), "REFUSED")

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

            # ⛔ FOUND ON THE REAL TRANSCRIPT. A background job finishing mid-turn injects a
            # `<task-notification>` record with `type: "user"` and no `isMeta`, which the borrowed
            # boundary rule calls a NEW TURN — splitting the turn between the act and the report.
            # Without coalescing, this transcript warns although the close carries a table.
            # ⚠ THE NOTIFICATION MUST BE THE LAST BOUNDARY for this to bite: only then is the
            # ACT fragment the judged window. With the notification in the middle, the fragment
            # that gets judged is the harmless one and the case cannot tell coalescing apart —
            # which is exactly how the first version of this case let its mutation survive.
            split = write("split.jsonl", [
                user("do it"), bash("git push"),
                user("<task-notification>\n<task-id>x</task-id>\n</task-notification>"),
                say("Done.\n\n" + good),
            ])
            check("run: a notification splitting a turn does NOT warn falsely",
                  _safe(lambda: run_decide(json.dumps({"transcript_path": str(split)}))), QUIET)

            # ...and the guard must still fire when that same split turn closes with PROSE.
            split_prose = write("split_prose.jsonl", [
                user("do it"), bash("git push"),
                user("<task-notification>\n<task-id>x</task-id>\n</task-notification>"),
                say("All done!"),
                user("next"), say("working"),
            ])  # notification mid-turn; the merged turn is judged and closes with prose
            check("run: a split turn closing with prose still warns",
                  _safe(lambda: run_decide(json.dumps({"transcript_path": str(split_prose)}))), WARN)

            # ⛔ THE LIVE TURN IS NEVER JUDGED — one turn of latency is the point, not a bug.
            live_only = write("live.jsonl", [user("do it"), bash("git push"), say("All done.")])
            check("run: only one turn -> QUIET (no subject yet)",
                  run_decide(json.dumps({"transcript_path": str(live_only)})), QUIET)
        finally:
            globals()["WARN_LOG"] = real_log

    # ⛔ DERIVED, NOT DECLARED TWICE — found 2026-09-21 while fixing r7's F2, by the fix itself.
    # This was `total = 128`, a hardcoded literal, and the line below compared it to the docstring's
    # hardcoded 128. `check-selftest-counts.py` then compared the docstring to what this suite
    # PRINTED — which was that same literal. Three numbers, one source, nothing counting anything:
    # adding the five teammate-fold cases left it reporting "128/128 passed", and DELETING fifty
    # would have done the same. The sibling guards this pattern was copied from do it correctly
    # (`check-merge-ready.py:529`, `check-review-rounds.py:280` both `cases += 1` inside `check`),
    # so this file was the outlier — and it is the one that shipped on a `NO-REVIEW:` waiver.
    # The external observer only ever verifies a number the suite MEASURES about itself.
    total = cases
    declared = re.search(r"--self-test\s+#\s*(\d+)\s+cases", __doc__ or "")
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

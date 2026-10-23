#!/usr/bin/env python3
"""Rebuild the work-line links that predate the `parent:` field — by REPLAYING the transcripts.

    python3 scripts/backfill-work-lines.py                  # DRY RUN: print the table, write nothing
    python3 scripts/backfill-work-lines.py --write          # apply the `keep`/`keep-banner` rows
    python3 scripts/backfill-work-lines.py --plans DIR      # read (and with --write, change) DIR
    python3 scripts/backfill-work-lines.py --ground-truth   # the replay must reproduce a live link
    python3 scripts/backfill-work-lines.py --self-test  # 243 cases

WHY THIS EXISTS
---------------
`begin-plan.py` has recorded `<!-- parent: <slug> -->` since 2026-10-22: the plan armed in
`.claude/executing-plan` when a NEW plan is first armed is its parent, and nothing armed is `-`.
Every plan written before that day has no marker, so `gen-work-lines.py` draws it as a line of
one. Measured 2026-10-22: of 125 plans, 104 have their arming `begin-plan` call in the session
transcripts — so the sentinel's history is not lost, it is written down call by call.

⭐ THE OWNER'S DECISION (option A, 2026-10-22): REPLAY, DON'T GUESS — AND LABEL WHAT WAS REPLAYED.
Every `begin-plan.py` call in the transcripts is replayed in timestamp order through the SAME
rule the live code uses (`begin-plan.cmd_begin` / `_derive_parent`, `check-plan-progress.run_decide`):

  * at a NEW plan's first successful arm, the armed plan is its parent; nothing armed is `-`;
  * a sentinel naming a file that is not a `.claude/plans/*.md` plan records NO parent (live:
    `_plan_slug`);
  * re-arming an existing plan never changes its parent;
  * the Stop hook clears a fully-ticked, un-paused plan at the end of a turn — so a turn
    boundary (`stop_hook_summary`, or an `end_turn`) in a top-level session clears it;
  * `--finish` clears; `--pause` / `--resume` toggle whether the Stop hook may clear.

⛔ WHERE THE STATE CANNOT BE DETERMINED, NO PARENT IS RECORDED — never a guess. That covers a call
whose result is missing or unreadable, a step count that was never printed, a hand edit of the
sentinel or the armed plan, a Stop hook that ran somewhere the sentinel may not be, another
session or agent changing plan state WHILE the arm ran, and a plan file that existed before its
first recorded arm (the transcripts begin 2026-09-22, `begin-plan` on 2026-09-04: a later re-arm
would otherwise be mistaken for the creation). A plausible lineage is worse than an absent one,
because it will be believed.

⚠ ONE DIVERGENCE FROM TODAY'S LIVE CODE, BY THE OWNER'S RULE. Since 2026-10-22 the live code, with
nothing armed, asks whether the LAST FINISHED plan (same session, PR still open) continues the
line. That needs a PR's state at a past moment, which no transcript holds; the backfill rule is
"nothing armed -> `-`". It touches only plans written before that code existed.

⛔ ONLY PLANS WITH NO `parent:` MARKER ARE TOUCHED, and every reconstructed link is LABELLED:

    <!-- parent: <slug-or-dash> -->
    <!-- parent-source: transcript <session-id-8> <ISO time of the arm> -->

`gen-work-lines.py` reads the second line and draws such a node distinctly, so live evidence and
rebuilt history can always be told apart.

⭐ BANNERS ARE A CROSS-CHECK, NOT A SOURCE. A `⤳ SWITCHED from `X` … → `Y`` line in the assistant's
own text, in the same turn as Y's first arm, is what was SAID at the time. If it names a parent
that disagrees with the replay, Y gets NO marker and is listed — two witnesses that disagree are
not evidence for either.

⭐ OPTION A FOR BANNERS (the owner, after reading the dry run, 2026-10-22). When the replay's `-`
exists ONLY because the plan armed just before was CLEARED (a turn-end clear or `--finish`), and
the banners in the arm's turn name EXACTLY that cleared plan as the one being left, the plan is
linked to it — labelled `parent-source: banner <session-8> <ISO>` with the BANNER's own session
and time, never `transcript`, so the page can say what the link rests on. Every other
disagreement stays unlinked and listed, and a banner never overrides a parent the replay found
ARMED at the time.

⛔ THE LINE: REVIEWED REPOSITORY CODE vs AD-HOC CODE (round 3; round 2 drew it at "read-only
tools" and lost 63 of 82 links, including the one recorded live). A Bash command keeps a
checkout's state KNOWN only if EVERY simple command in it (split on `;`, `&&`, `||`, `|` and
newlines, and recursively inside `$(…)` and backticks) is one of:
  * a `begin-plan.py` / `check-plan-progress.py` call (these ARE the events);
  * a TRACKED repository script run as `python3 <checkout>/scripts/<name>.py`, where `<name>`
    was committed under `scripts/` on some branch (`tracked_scripts`);
  * a member of `SAFE`, under that member's own condition (one constant, a reason per member).
  * INLINE Python whose text is in the command — a `python3 -` heredoc, `python3 -c '…'`, or a
    heredoc fed to a tracked script — when `inline_safe` finds none of `INLINE_UNSAFE` (round
    4, narrowed in round 5). The threat model is ACCIDENT, not adversary: an accidental change
    to the sentinel needs the code to NAME it, a plan tool, or a whole-tree delete. Code that
    builds the path from pieces that never spell it would defeat this, and that is accepted. A body that cannot be extracted
    (unterminated, or a `-c` holding a `$` the shell expanded) stays opaque.
Anything else is AD-HOC code: inline code that fails that inspection, `-m`, a script outside a
checkout's `scripts/` (Codex r2's real instance was `/tmp/steps.py`, 2026-10-17), an untracked
name, a variable-built interpreter path, `node`, `bash`/`sh`/`zsh`, `eval`, `source`/`.`,
`xargs`, or an unknown command. `env` and `timeout` prefixes are judged by the command they
run. Ad-hoc code makes EVERY checkout UNKNOWN. A file operation or output
redirection makes UNKNOWN only the checkouts whose sentinel or plans its paths name; an
unresolvable path reaches all. This happens BEFORE any arm in that command is processed. A lone
`rm -f` of a sentinel stays a known "nothing armed", but only when nothing else in the command is
opaque. Every plan first armed while its checkout is UNKNOWN gets NO marker, with the reason
named. A call inside a loop ran an unknown number of times, so it makes its checkout UNKNOWN.

⭐ THE PREMISE, VERIFIED ACROSS HISTORY (2026-10-22). It is that no tracked script but begin-plan
and check-plan-progress ever wrote the REAL sentinel. Every added line in `git log --all -p --
scripts/` that writes, unlinks or renames an `executing-plan` path was searched. Outside those
two scripts, every one targets a TEMPORARY root inside a self-test:
  * `check-banner-armed.py`: `(_fx / ".claude" / "executing-plan").write_text(…)`/`.unlink()`,
    with `_fx = Path(_d)` from a TemporaryDirectory. Its own `SENTINEL = ROOT /
    ".claude/executing-plan"` is only ever READ (`SENTINEL.read_text()`). It also runs
    `begin-plan.py --finish` with `str(_fx / "scripts" / "begin-plan.py")`, a staged copy.
  * `recall-llm.py`: `(root / ".claude" / "executing-plan").write_text(…)` in its self-test
    world. Its `SENTINEL` is only read (`is_file()`, `read_or_refuse`).
  * `check-plan-code.py`: `(_s / PROJECT_STATE / "executing-plan").write_text(…)` in a staged
    tree.
  * `check-ci-watched.py`: its `SENTINEL` is a different file (`_repo_sentinel()`, the CI-watch
    marker), not the plan sentinel.
  * `mutations/*.json`: anchors quoting begin-plan's and check-plan-progress's own writes.
No script was found writing the real sentinel in production, so none is treated as opaque by
date. ⚠ A tracked name is judged by its CURRENT history: a script run before its first commit
(still ad hoc then) is trusted as if reviewed. That is a stated bound, not a measured absence.

⭐ CHECKPOINTS COME ONLY FROM THE TOOLS' OWN STATE LINES: begin-plan's arm / tick / `--status` /
`--finish` output, `check-plan-progress.py --status`, and the Stop hook's `Clearing` message in a
session at this checkout. A read of the sentinel (`cat`, `sed -n`, `head`) is NEVER one — its
output cannot be attributed to the file (round 2, Codex 1). A checkpoint that disagrees resets the
replay and unmarks every plan first armed since the last checkpoint. A checkpoint can move UNKNOWN
to known, but it never authorises a parent for an arm made while unknown. Before the first
checkpoint the state is UNKNOWN.

⛔ A COMMAND IS NOT OVER WHEN IT STARTS (r3 Claude M1). Each opaque or uncertain command has an
END: a foreground one's tool result, a background one's completion or `TaskStop` record, or —
when neither is found, as for a shell `&` — the last event of its session. Until then, the
checkouts it can reach stay UNKNOWN, and a checkpoint inside that window resolves nothing. And a
turn end counts as the Stop hook's clear ONLY in a session that shows the hook at all (r3 Claude
L1): 272 SDK security-review transcripts here record no hook of any kind.

⚠ THE RESIDUAL BOUND, STATED PLAINLY. An arm made outside any transcript — another tool, an editor,
a human in a shell — is invisible to this replay. And agreeing checkpoints do NOT prove the
interval between them: an invisible arm followed by a visible one leaves every later checkpoint
agreeing. The allow-list closes what the transcripts can show; it cannot close what they never
recorded. The replay models what begin-plan PRINTED; when a working-tree copy of begin-plan was
edited and then run (2026-10-22, before the parent field merged), its event semantics are not
verified, only its output read (r3 Claude I1).

⚠ A STATED BOUND (r1 Claude F6, not fixed). A plan's parent is taken from its FIRST recorded arm.
A plan file deleted and re-created by a later arm carries the later arm's live parent; the birth
check cannot see this, because the new file is born after the first arm. No such case was found
on 2026-10-22 (the one inspected gave `-` at both arms).

FAILS IF
--------
  * `--ground-truth`: the replay over the real transcripts does not reproduce the link the live
    code recorded on 2026-10-22 (`work-lines-backfill` <- `banner-thread-armed`), or a checkpoint
    disagreement was not resolved -> exit 1 (the agree/disagree counts are printed either way);
    the transcripts are absent or hold no `begin-plan` call -> exit 2, CANNOT RUN, never a pass.
  * any run: the plans directory or the transcripts directory cannot be read -> exit 2.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STARTED = "-"
PLAN_REL = ".claude/plans"
SENTINEL_REL = ".claude/executing-plan"
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")   # `begin-plan.normalise_slug`'s alphabet
GROUND_TRUTH = ("work-lines-backfill", "banner-thread-armed")
# A plan file whose birth time is MORE than this before its first recorded arm existed before it.
BIRTH_SLACK_S = 120.0

PARENT_LINE = re.compile(r"^<!--\s*parent:\s*(.+?)\s*-->\s*$", re.M)
SOURCE_LINE = re.compile(r"^<!--\s*parent-source:\s*(.+?)\s*-->\s*$", re.M)
BANNER = re.compile(r"SWITCHED\s+from\s+\*?`([^`]+)`[^\n]*?→\s*\*{0,2}`([^`]+)`")
_PREFILTER = ('"Bash"', "<task-id>", "TaskStop", "KillShell", '"hookEvent"', "begin-plan",
              "SWITCHED", '"end_turn"', "stop_hook_summary",
              "executing-plan",
              ".claude/plans/")
_TOOL_RESULT_ID = re.compile(r'"tool_use_id"\s*:\s*"([^"]+)"')
_WRITE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def main_checkout(start: Path = ROOT) -> Path:
    """The MAIN working tree — the one whose sentinel the transcripts' sessions armed. A worktree
    has its own `.claude/`, so the default must not be this script's own checkout."""
    try:
        r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           cwd=start, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return start
    if r.returncode != 0 or not r.stdout.strip():
        return start
    return Path(r.stdout.strip()).parent


def transcripts_for(root: Path) -> Path:
    """`~/.claude/projects/<root with every non-alphanumeric as '-'>` — Claude Code's own naming."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(root))


# ── shell parsing: just enough to find a `begin-plan.py` call and where it ran ────────────────

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(cmd: str) -> str:
    """Drop every heredoc BODY. A body is data — a Python script that names `begin-plan.py` in a
    string is not a call to it."""
    lines, out, i = cmd.split("\n"), [], 0
    while i < len(lines):
        ln = lines[i]
        out.append(ln)
        i += 1
        for m in _HEREDOC.finditer(ln):
            while i < len(lines) and lines[i].strip() != m.group(2):
                i += 1
            i += 1
    return "\n".join(out)


def heredoc_bodies(cmd: str) -> list[str | None]:
    """Each heredoc's BODY, in marker order; None for one whose terminator never comes (an
    unterminated body cannot be inspected, so what it feeds stays opaque)."""
    lines, out, i = cmd.split("\n"), [], 0
    while i < len(lines):
        ln = lines[i]
        i += 1
        for m in _HEREDOC.finditer(ln):
            body = []
            while i < len(lines) and lines[i].strip() != m.group(2):
                body.append(lines[i])
                i += 1
            out.append("\n".join(body) if i < len(lines) else None)
            i += 1
    return out


# ⭐ INLINE CODE IS INSPECTED, NOT ASSUMED OPAQUE (round 4; narrowed in round 5 — the
# coordinator's decision). THE THREAT MODEL IS ACCIDENT, NOT ADVERSARY: this reconstructs the
# owner's own history, and an inline script's full TEXT is in the transcript. THE PREMISE: an
# accidental change to `.claude/executing-plan` needs that path, or a plan tool, to appear in the
# code's text — or a whole-tree delete, which removes files it never names. Code that writes
# scratch files, imports repository modules to read them, or runs `git` names none of these, and
# measured on 2026-10-22 that was most inline code: the round-4 list (`subprocess`, `importlib`,
# `Path(…).write_…`, …) kept 92 plans unlinked for code that only READ.
# ⚠ STATED PLAINLY: code that assembles the path from pieces that never spell `.claude` or
# `executing-plan` — `ROOT / ('.cl' + 'aude') / …` — defeats this. That is accepted, because no
# accident does that; only an adversary would, and the owner is not one.
INLINE_UNSAFE: dict[str, str] = {
    r"executing-plan": "names the sentinel itself",
    r"\.claude": "names the directory holding the sentinel and the plans",
    r"begin-plan": "names the tool that writes the sentinel",
    r"check-plan-progress": "names the tool that clears the sentinel",
    r"\bshutil\.rmtree\b": "deletes a whole tree without naming what is inside it",
}
_INLINE_UNSAFE = re.compile("|".join(f"(?:{k})" for k in INLINE_UNSAFE))


def inline_safe(code: str | None) -> bool:
    """Can this inline Python (a heredoc body, a `-c` argument) NOT have touched a sentinel by
    accident? None — a body that could not be extracted — is never safe."""
    return code is not None and not _INLINE_UNSAFE.search(code)


def _read_word(cmd: str, i: int) -> tuple[str, int]:
    """One shell word starting at `i`, quotes removed, and the index just past it."""
    n, out = len(cmd), []
    while i < n and cmd[i] not in " \t;|&()\n":
        if cmd[i] in "'\"":
            j = cmd.find(cmd[i], i + 1)
            j = n if j < 0 else j
            out.append(cmd[i + 1:j])
            i = j + 1
            continue
        out.append(cmd[i])
        i += 1
    return "".join(out), i


def _subst_end(cmd: str, i: int) -> int:
    """The index of the character closing the command substitution that opens at `i`."""
    n = len(cmd)
    if cmd[i] == "`":
        j = cmd.find("`", i + 1)
        return n - 1 if j < 0 else j
    depth, j = 0, i + 1
    while j < n:
        if cmd[j] == "(":
            depth += 1
        elif cmd[j] == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n - 1


def _subst_inner(cmd: str, i: int, j: int) -> str:
    return cmd[i + 1:j] if cmd[i] == "`" else cmd[i + 2:j]


def tokenize(cmd: str) -> list[tuple[str, str]]:
    """[(kind, text)]: 'w' a word (quotes removed), 'op' an operator, 'redir' a redirection's
    TARGET — so `2>&1` is never an argument, and `>> .claude/executing-plan` is a visible write."""
    toks: list[tuple[str, str]] = []
    i, n = 0, len(cmd)
    word, has_word = [], False

    def flush():
        nonlocal word, has_word
        if has_word:
            toks.append(("w", "".join(word)))
        word, has_word = [], False

    while i < n:
        c = cmd[i]
        if c == "\\" and i + 1 < n:
            if cmd[i + 1] == "\n":
                i += 2
                continue
            word.append(cmd[i + 1]); has_word = True; i += 2
            continue
        if c == "'":
            j = cmd.find("'", i + 1)
            j = n if j < 0 else j
            word.append(cmd[i + 1:j]); has_word = True; i = j + 1
            continue
        if c == '"':
            i += 1
            while i < n and cmd[i] != '"':
                if cmd[i] == "\\" and i + 1 < n and cmd[i + 1] in '"\\$`':
                    word.append(cmd[i + 1]); i += 2
                    continue
                if cmd[i] == "`" or cmd[i:i + 2] == "$(":
                    # command substitution RUNS code: its inner command is judged on its own
                    j = _subst_end(cmd, i)
                    toks.append(("subst", _subst_inner(cmd, i, j)))
                    word.append(cmd[i:j + 1]); i = j + 1
                    continue
                word.append(cmd[i]); i += 1
            has_word = True; i += 1
            continue
        if c == "`" or (c == "$" and i + 1 < n and cmd[i + 1] == "("):
            j = _subst_end(cmd, i)
            toks.append(("subst", _subst_inner(cmd, i, j)))
            word.append(cmd[i:j + 1]); has_word = True; i = j + 1
            continue
        if c in " \t":
            flush(); i += 1
            continue
        if c == "#" and not has_word:
            # a comment runs to the end of the line; it is not a command (measured: `# note`
            # lines were read as an unknown command `#` and poisoned the checkout)
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        if c in "<>" or (c == "&" and i + 1 < n and cmd[i + 1] == ">"):
            # a redirection: an all-digit word before it is its fd, not an argument
            if has_word and "".join(word).isdigit():
                word, has_word = [], False
            flush()
            start = i
            i += 1
            while i < n and cmd[i] in "<>":
                i += 1
            out = ">" in cmd[start:i]
            if i < n and cmd[i] == "&" and c != "&":
                i += 1
                while i < n and (cmd[i].isdigit() or cmd[i] == "-"):
                    i += 1
                continue
            while i < n and cmd[i] in " \t":
                i += 1
            target, i = _read_word(cmd, i)
            toks.append(("redir" if out else
                         "heredoc" if cmd[start:start + 2] == "<<" else "inredir", target))
            continue
        if c in ";|&()\n":
            flush()
            if cmd[i:i + 2] in ("&&", "||"):
                toks.append(("op", cmd[i:i + 2])); i += 2
            else:
                toks.append(("op", c)); i += 1
            continue
        word.append(c); has_word = True; i += 1
    flush()
    return toks


_VAR = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


def expand(word: str, env: dict[str, str]) -> str | None:
    """`~` and `$VAR` from assignments made earlier in the same command; None if unresolvable."""
    if word.startswith("~"):
        word = str(Path.home()) + word[1:]
    bad = False

    def sub(m):
        nonlocal bad
        if m.group(1) in env:
            return env[m.group(1)]
        bad = True
        return ""
    out = _VAR.sub(sub, word)
    return None if bad or "$(" in word or "`" in word else out


_INTERP = re.compile(r"^(?:\S*/)?python[0-9.]*$")
# ⟳ r1 Claude F1: `do python3 scripts/begin-plan.py --tick` was not a call, because `do` is not
# an interpreter — and `for i in 1 2 3 4; do … --tick; done` is how steps are ticked in bulk here.
_RESERVED = {"do", "then", "else", "elif", "!", "time", "{", "}", "if", "fi", "esac", "done"}
_LOOP_OPEN = {"for", "while", "until", "select"}
_SCRIPTS = {"begin-plan.py": "begin-plan", "check-plan-progress.py": "progress"}
_SENT_TAIL = "/" + SENTINEL_REL

# ⛔ THE LINE IS REVIEWED REPOSITORY CODE vs AD-HOC CODE (round 3, the coordinator's decision; the
# round-2 allow-list drew it at "read-only tools" and cost 63 of 82 links, including the live one).
# A command keeps a checkout's state KNOWN only if every simple command in it is a begin-plan /
# check-plan-progress call, a TRACKED repository script, or a SAFE member below under that
# member's own condition. Each reason says why the tool CANNOT change a sentinel. Anything else —
# `python3 -`/`-c`/`-m`, a script outside a checkout's `scripts/` or never tracked, any interpreter
# fed a heredoc, `node`, `bash`/`sh`/`zsh`, `eval`, `source`/`.`, `xargs`, an unknown command —
# is AD-HOC code and makes EVERY checkout unknown, before any arm in that command.
TRACKED_SCRIPTS: frozenset[str] | None = None   # None: ask git (see tracked_scripts)
SAFE: dict[str, str] = {
    # ⟳ r3 Claude L2: `.claude/` is NOT wholly gitignored — its hooks and settings.json are
    # tracked. What IS ignored is exactly the two paths that matter here: `.claude/executing-plan`
    # (.gitignore:89) and `.claude/plans/` (:96). An ignored, untracked path is never written by
    # commit, push, merge, checkout or reset; `clean -x` deletes ignored files and `stash -a`
    # (or `-u`) stashes untracked ones, so those two stay opaque.
    "git": "every subcommand but `clean` and `stash`: the sentinel and `.claude/plans/` are "
           "ignored and untracked, so no other subcommand writes them. Hooks run, but they are "
           "reviewed repository code",
    "ls": "lists directory entries; it writes nothing",
    "cat": "prints files to stdout; a redirection of that output is judged on its own",
    "head": "prints the start of files", "tail": "prints the end of files",
    "grep": "prints matching lines", "wc": "prints counts",
    "cut": "prints fields", "sort": "prints sorted lines (an `-o FILE` is judged as a write)",
    "uniq": "prints lines (a second operand is an OUTPUT file, judged as a write)",
    "tr": "translates stdin to stdout", "jq": "prints JSON", "column": "prints columns",
    "sed": "never `-i`: without it sed prints its result and edits no file",
    "awk": "only with no `system`, `getline`, `>` or `|` in its program: it prints text",
    "echo": "prints its arguments", "printf": "prints its arguments", "date": "prints the time",
    "sleep": "waits", "pgrep": "lists processes",
    "pkill": "signals processes; it writes no file",
    "gh": "talks to GitHub; it writes nothing under `.claude/`",
    "true": "does nothing", "false": "does nothing", "test": "evaluates a condition",
    "[": "evaluates a condition", "diff": "prints differences", "comm": "prints common lines",
    "basename": "prints a name", "dirname": "prints a name", "realpath": "prints a path",
    "stat": "prints metadata", "xxd": "prints a hex dump", "od": "prints a dump",
    "file": "prints a file type", "which": "prints a path", "type": "prints a command's kind",
    "exit": "ends the shell", "export": "sets variables in the shell only",
    "pwd": "prints the directory", "ps": "lists processes",
    "mktemp": "creates a NEW temp path; one under `.claude/` named by an argument is a write",
    "find": "never with -delete, -exec, -execdir, -ok, -okdir, -fprint* or -fls: it prints paths",
    "cd": "moves the shell only; a path that cannot be resolved makes the cwd unknown",
}
# File operations reach only the sentinels and plan files their PATHS name (or a directory
# containing them). They run no code, so a target elsewhere cannot change a sentinel.
FILE_OPS = {"rm", "unlink", "mv", "cp", "tee", "truncate", "touch", "mkdir", "ln", "chmod",
            "sed", "sort", "uniq", "mktemp"}
# Interpreter flags that take no code: `python3 -u -c …` is still `-c`.
_PY_FLAGS = {"-u", "-B", "-E", "-I", "-s", "-S", "-O", "-OO", "-q", "-b", "-bb", "-W", "-X"}


def tracked_scripts() -> frozenset[str]:
    """Every `scripts/*.py` name ever committed on any branch of this repository — REVIEWED
    code. Asked of git once; an unanswerable git gives the empty set, so every script is ad hoc
    (the safe direction)."""
    global TRACKED_SCRIPTS
    if TRACKED_SCRIPTS is None:
        try:
            r = subprocess.run(["git", "log", "--all", "--name-only", "--format=", "--",
                                "scripts/*.py"], cwd=ROOT, capture_output=True, text=True,
                               timeout=60)
            names = r.stdout.split() if r.returncode == 0 else []
        except (OSError, subprocess.SubprocessError):
            names = []
        TRACKED_SCRIPTS = frozenset(os.path.basename(x) for x in names
                                    if os.path.dirname(x) == "scripts" and x.endswith(".py"))
    return TRACKED_SCRIPTS


def _safe(name: str, args: list[str]) -> bool:
    """Is this simple command a SAFE member, under that member's own condition?"""
    if name not in SAFE or name == "cd":
        return False
    if name == "git":
        rest = list(args)
        while rest and rest[0].startswith("-"):
            flag = rest.pop(0)
            if flag in ("-C", "-c") and rest:
                rest.pop(0)
        return bool(rest) and rest[0] not in ("clean", "stash")
    if name == "sed":
        return not any(x.startswith("-i") or x == "--in-place" for x in args)
    if name == "awk":
        prog = [x for x in args if not x.startswith("-")]
        return not any(k in x for x in prog for k in ("system", "getline", ">", "|"))
    if name == "sort":
        return not any(x.startswith("-o") or x == "--output" for x in args)
    if name == "uniq":
        return len([x for x in args if not x.startswith("-")]) < 2
    if name == "mktemp":
        return not any(".claude" in x for x in args)
    if name == "find":
        return not any(x in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fls")
                       or x.startswith("-fprint") for x in args)
    return True


@dataclass
class Call:
    """One invocation of `begin-plan.py` (or `check-plan-progress.py`): its arguments, the
    checkout whose sentinel it touches, and whether it ran inside a loop."""
    args: list[str]
    root: str | None      # None: the script path or cwd could not be resolved
    loop: bool = False
    script: str = "begin-plan"


@dataclass
class Op:
    """One step of a Bash command, in COMMAND ORDER."""
    kind: str             # 'call' | 'rmsent' | 'opaque'
    root: str | None = None
    call: Call | None = None
    paths: list[str] | None = None    # opaque: the file paths it writes; None = it runs code
    why: str = ""
    bg: bool = False                  # left running by a shell `&`


def _resolve(word: str, env: dict[str, str], cur: str | None) -> str | None:
    p = expand(word, env)
    if p is None or (cur is None and not os.path.isabs(p)):
        return None
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(cur, p))


def parse_command(cmd: str, cwd: str | None) -> list[Op]:
    """Every call and every operation that could change a sentinel, IN ORDER. Each call is
    resolved to its checkout (`begin-plan.ROOT` is the script's own); a path is resolved against
    the record's cwd as changed by `cd`. A command made only of SAFE members, tracked scripts
    and calls yields only calls. A command substitution is judged by the commands INSIDE it."""
    toks = tokenize(strip_heredocs(cmd))
    bodies = heredoc_bodies(cmd)
    # a body can be matched to the command it feeds only when every marker became a token
    aligned = len(bodies) == sum(1 for k, _t in toks if k == "heredoc")
    fed_count = 0
    body: str | None = None
    ops: list[Op] = []
    env: dict[str, str] = {}
    cur: str | None = cwd
    depth = 0
    words: list[str] = []
    redirs: list[str] = []
    substs: list[str] = []
    heredoc = False
    seg = 0                             # where the current pipeline's ops begin

    def opaque(why: str, paths: list[str] | None) -> None:
        ops.append(Op("opaque", paths=paths, why=why))

    def finish(ws: list[str], rs: list[str], subs: list[str], fed: bool,
               body: str | None) -> None:
        nonlocal cur, depth
        while ws and (ws[0] in _RESERVED or ws[0] in _LOOP_OPEN):
            w = ws.pop(0)
            if w in _LOOP_OPEN:
                depth += 1
                if w in ("for", "select"):
                    ws = []            # the loop's header names values; it runs nothing
            elif w == "done":
                depth = max(0, depth - 1)
        for inner in subs:
            # ⭐ round 3: a substitution is safe iff every command inside it is
            ops.extend(parse_command(inner, cur))
        if ws and ws[0] == "export" and all(
                re.match(r"^[A-Za-z_][A-Za-z0-9_]*(=|$)", w) for w in ws[1:]):
            # `export VAR=…` is an assignment the rest of the command can resolve
            ws = [w for w in ws[1:] if "=" in w]
            if not ws:
                return
        while ws and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", ws[0]):
            k, v = ws[0].split("=", 1)
            env[k] = expand(v, env) or v
            ws = ws[1:]
        outs = [r for r in rs if r != "/dev/null"]
        if outs:
            paths = [_resolve(r, env, cur) for r in outs]
            opaque("an output redirection", None if None in paths else paths)
        if not ws:
            return
        # ⭐ PREFIXES: `env [VAR=…]`, `timeout [opts] <dur>` and `nohup` run the command after
        # them, so it is that command that is judged (round 4; `nohup` added in the r3 fold).
        while ws and ws[0] in ("env", "timeout", "nohup"):
            if ws[0] == "nohup":
                ws = ws[1:]
            elif ws[0] == "env":
                ws = ws[1:]
                while ws and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", ws[0]) or ws[0] == "-i"):
                    ws = ws[1:]
            else:
                ws = ws[1:]
                while ws and ws[0].startswith("-"):
                    ws = ws[2:] if ws[0] in ("-s", "-k", "--signal", "--kill-after") else ws[1:]
                ws = ws[1:]        # the duration
        if not ws:
            return
        if ws[0] == "cd":
            d = expand(ws[1], env) if len(ws) >= 2 else None
            cur = None if d is None or cur is None else os.path.normpath(os.path.join(cur, d))
            return
        for k in range(min(3, len(ws))):
            script = _SCRIPTS.get(os.path.basename(ws[k]))
            if script is None:
                continue
            if not all(_INTERP.match(w) or w.startswith("$") or w == "env" for w in ws[:k]):
                break
            p = _resolve(ws[k], env, cur)
            root = None if p is None else os.path.dirname(os.path.dirname(p))
            ops.append(Op("call", root, call=Call(ws[k + 1:], root, depth > 0, script)))
            return
        w0 = expand(ws[0], env)
        if w0 is not None and _INTERP.match(w0):
            # ⭐ ROUND 3: TRACKED repository code is reviewed code. Measured across `git log --all
            # -p -- scripts/`: no script but begin-plan and check-plan-progress ever wrote the
            # REAL sentinel (see the module docstring), so running one changes no sentinel.
            # `-`, `-c`, `-m`, a path outside a checkout's `scripts/`, an untracked name, or a
            # heredoc on stdin is ad-hoc code.
            # ⭐ ROUND 4: INLINE code (`-c`, a heredoc on stdin) is INSPECTED by `inline_safe`.
            a = ws[1:]
            while a and a[0] in _PY_FLAGS:
                a = a[2:] if a[0] in ("-W", "-X") else a[1:]
            stdin_ok = not fed or inline_safe(body)
            if a and a[0] == "-c":
                code = a[1] if len(a) > 1 else None
                # a `$` may be a variable the shell expanded: the text that ran is not here
                if code is not None and "$" not in code and inline_safe(code) and stdin_ok:
                    return
            elif not a or a[0] == "-":
                if fed and inline_safe(body):
                    return
            elif not a[0].startswith("-"):
                p = _resolve(a[0], env, cur)
                if (p is not None and stdin_ok
                        and os.path.basename(os.path.dirname(p)) == "scripts"
                        and os.path.basename(p) in tracked_scripts()):
                    return
            opaque(f"`{' '.join(ws[:2])[:60]}` runs ad-hoc code", None)
            return
        name, args = os.path.basename(ws[0]), ws[1:]
        if _safe(name, args):
            return
        if name in FILE_OPS:
            files = [a for a in args if a and not a.startswith("-")]
            if name == "mktemp":
                files = files + [args[i + 1] for i, a in enumerate(args[:-1])
                                 if a in ("-p", "--tmpdir")]
            if name == "sed":
                files = files[1:]          # the first operand is sed's SCRIPT, not a file
            if name == "sort":
                files = [args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-o", "--output")]
            if name == "uniq":
                files = files[1:2]         # `uniq IN OUT`: only OUT is written
            paths = [_resolve(a, env, cur) for a in files]
            sents = [p for p in paths if p and p.endswith(_SENT_TAIL)]
            if name in ("rm", "unlink") and paths and len(sents) == len(paths):
                for p in sents:
                    ops.append(Op("rmsent", p[:-len(_SENT_TAIL)]))
                return
            opaque(f"`{name}` writes files", None if None in paths else paths)
            return
        opaque(f"`{name}` is ad-hoc code: not a tracked script and not a SAFE tool", None)

    for kind, text in toks + [("op", ";")]:
        if kind == "w":
            words.append(text)
        elif kind == "redir":
            redirs.append(text)
        elif kind == "subst":
            substs.append(text)
        elif kind == "heredoc":
            heredoc = True
            body = bodies[fed_count] if aligned else None
            fed_count += 1
        elif kind == "inredir":
            continue
        else:
            finish(words, redirs, substs, heredoc, body)
            words, redirs, substs, heredoc, body = [], [], [], False, None
            if text == "&":
                # ⛔ r3 Claude M1: a shell `&` leaves the pipeline before it RUNNING
                for o in ops[seg:]:
                    o.bg = True
            if text != "|":
                seg = len(ops)
    return ops


def find_calls(cmd: str, cwd: str) -> list[Call]:
    """The `begin-plan.py` calls a command makes, in order (a view of `parse_command`)."""
    return [o.call for o in parse_command(cmd, cwd)
            if o.kind == "call" and o.call.script == "begin-plan"]


def reaches(op: Op, roots: list[str]) -> list[str] | None:
    """The checkouts an opaque op can change; None = every checkout (it runs code, or a path
    could not be resolved). A path reaches a checkout when it is its sentinel, a file under its
    plans, or a directory containing either."""
    if op.paths is None:
        return None
    out = []
    for r in roots:
        guarded = (r + _SENT_TAIL, os.path.join(r, PLAN_REL))
        for p in op.paths:
            if p == guarded[0] or p.startswith(guarded[1] + "/") or any(
                    g.startswith(p.rstrip("/") + "/") for g in guarded):
                out.append(r)
                break
    return out


def classify(args: list[str]) -> tuple[str, str | None]:
    """(sub, value) exactly as `begin-plan.main` dispatches. Read-only and failed parses are
    ('ro', None): they change no state."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("steps", nargs="*")
    for f in ("--plan", "--pause", "--serving"):
        ap.add_argument(f)
    for f in ("--tick", "--banner", "--status", "--resume", "--finish", "--self-test",
              "--help"):
        ap.add_argument(f, action="store_true")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            a = ap.parse_args(args)
    except SystemExit:
        return "ro", None
    if a.help or a.self_test or a.banner:
        return "ro", None
    if a.status:
        # ⟳ r1 Claude F4: `--status` was "read-only" and its output thrown away — but it is a
        # direct OBSERVATION of the sentinel, so it is a checkpoint.
        return "status", None
    if a.tick:
        return "tick", None
    if a.pause is not None:
        return "pause", a.pause
    if a.resume:
        return "resume", None
    if a.finish:
        return "finish", None
    if a.plan:
        return "plan", a.plan
    if a.slug:
        return "arm", a.slug
    return "ro", None


# ── reading what each call PRINTED ────────────────────────────────────────────────────────────

_REFUSED = re.compile(r"refusing:")
# ⭐ THE STATE LINE IS THE WITNESS. `_print_state` ends every arm and tick with one of these, and
# most calls were piped through `tail`, which keeps exactly that line. It names the plan and its
# count, so it observes the sentinel directly — an UNKNOWN state is RESYNCED by the next one.
_STATE = re.compile(r"\(plan: (\S+) — (\d+)/(\d+) ticked|✅ every step in (\S+) is ticked")
_PRIMARY = {
    "arm": re.compile(r"armed: \S+ -> (\S+) \((\d+) steps\)"),
    "plan": re.compile(r"armed: \S+ -> (\S+)[ \t]*$", re.M),
    "tick": re.compile(r"ticked step (\d+) of (\d+) in (\S+)|nothing to tick — every step in "
                       r"(\S+) is already done|(CANNOT RUN: the sentinel names)"),
    "pause": re.compile(r"^paused: |The Stop guard will now allow the turn to end|WHEN THE WORK "
                        r"RESUMES, run `scripts/begin-plan.py --resume` FIRST", re.M),
    "resume": re.compile(r"^resumed:", re.M),
    "finish": re.compile(r"cleared \.claude/executing-plan|(nothing was armed\.)"),
    "status": re.compile(r"^(\S+\.md): (\d+)/(\d+) steps ticked|^(no plan is being executed)",
                         re.M),
}
_ANY_PRIMARY = re.compile("|".join(f"(?:{p.pattern})" for p in _PRIMARY.values()), re.M)
_NOT_RUN = re.compile(r"doesn't want to proceed|tool use was rejected|"
                      r"Permission to use \w+ has been denied", re.I)


def _state_info(m: re.Match) -> dict:
    if m.group(4):
        return {"rel": m.group(4).rstrip(".,"), "done": None, "n": None, "full": True}
    d, n = int(m.group(2)), int(m.group(3))
    return {"rel": m.group(1), "done": d, "n": n, "full": d >= n}


def read_outcomes(calls: list[tuple[str, str | None]], text: str | None,
                  is_error: bool) -> list[tuple[str, dict]]:
    """[(outcome, info)] per call: 'ok' | 'refused' | 'unknown' | 'ro'. Calls are matched to the
    output IN ORDER, each from where the previous one's evidence ended.

    For arm / --plan / --tick, `info` is what the output OBSERVED of the sentinel afterwards:
    `rel` (the armed plan), `done`/`n` (its count) and `full` — from the primary line, the state
    line that follows it, or the state line alone when `tail` cut the rest."""
    if text is None:
        return [("unknown", {})] * len(calls)
    if is_error and _NOT_RUN.search(text) and not _ANY_PRIMARY.search(text) \
            and not _STATE.search(text):
        return [("refused", {})] * len(calls)
    out, pos = [], 0
    printers = [i for i, (sub, _v) in enumerate(calls) if sub in ("arm", "plan", "tick")]
    for idx, (sub, val) in enumerate(calls):
        if sub == "ro":                    # read-only: changes nothing, so nothing is matched
            out.append(("ro", {}))
            continue
        prim = _PRIMARY[sub].search(text, pos)
        no = _REFUSED.search(text, pos)
        # ⛔ A BARE state line belongs to the LAST call that prints one. `--tick && --finish &&
        # begin-plan next | tail` keeps only the arm's line; read in order, the tick took it, and
        # the new plan's first arm became "unreadable" (measured: backlog-117-r3, fold-r4-claude).
        st = (_STATE.search(text, pos)
              if sub in ("arm", "plan", "tick") and idx == printers[-1] else None)
        first = min((m for m in (prim, no, st) if m), key=lambda m: m.start(), default=None)
        if first is None:
            out.append(("unknown", {}))
            continue
        if first is no:
            out.append(("refused", {})); pos = no.end()
            continue
        info: dict = {}
        end = first.end()
        if first is prim:
            g = prim.groups()
            if sub == "arm":
                info = {"rel": g[0], "done": 0, "n": int(g[1]), "full": False}
            elif sub == "plan":
                info = {"rel": g[0], "done": None, "n": None, "full": None}
            elif sub == "finish":
                info = {"none": bool(g[0])}
            elif sub == "status":
                if g[3]:
                    info = {"none": True}
                else:
                    nxt = _ANY_PRIMARY.search(text, end)
                    tail = text[end:nxt.start() if nxt else len(text)]
                    info = {"rel": g[0], "done": int(g[1]), "n": int(g[2]),
                            "paused": bool(re.search(r"^PAUSED: ", tail, re.M))}
            elif sub == "tick":
                if g[4]:
                    out.append(("refused", {})); pos = end
                    continue
                info = ({"rel": g[2], "done": int(g[0]), "n": int(g[1]),
                         "full": int(g[0]) >= int(g[1])} if g[0] else
                        {"rel": g[3], "done": None, "n": None, "full": True})
            if sub in ("arm", "plan", "tick"):
                # the state line printed right after it, unless another call's line comes first
                nxt = _STATE.search(text, end)
                other = _ANY_PRIMARY.search(text, end)
                if nxt and (not other or nxt.start() < other.start()):
                    info = _state_info(nxt); end = nxt.end()
        else:
            info = _state_info(st)
        if sub == "arm" and os.path.normpath(info["rel"]) != f"{PLAN_REL}/{val}.md":
            out.append(("unknown", {}))     # a line about some OTHER plan is no witness here
            continue
        out.append(("ok", info)); pos = end
    # ⭐ `--finish` CANNOT FAIL: `cmd_finish` unlinks with `missing_ok` and returns OK. So when its
    # own line was cut by `tail` but a LATER call in the same command left evidence, the shell got
    # past it — it ran, and the sentinel was cleared. Measured: 12 such calls, nearly all
    # `--finish … && begin-plan <next> … | tail`, the exact moment a new line starts.
    for i, ((sub, _v), (oc, _info)) in enumerate(zip(calls, out)):
        if sub == "finish" and oc == "unknown" and any(o in ("ok", "refused")
                                                       for o, _ in out[i + 1:]):
            out[i] = ("ok", {"inferred": True})
    return out


# ── the events ────────────────────────────────────────────────────────────────────────────────

@dataclass
class Event:
    ts: str
    stream: str           # the transcript FILE — a subagent is its own stream
    order: int
    session: str
    kind: str             # 'cmd' | 'tool' | 'stop' | 'clearing' | 'prompt' | 'banner'
    data: dict = field(default_factory=dict)
    end: str = ""         # when its result arrived (cmd)


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


_HEADING = re.compile(r"^## ▶")
_THREAD = re.compile(r"^> \*\*Thread:\*\*")
_FENCE = re.compile(r"^\s*(```|~~~)")


def live_banners(text: str) -> list[tuple[str, str]]:
    """(from, to) of each `⤳ SWITCHED` banner in the assistant's OWN live text: the `> **Thread:**`
    line of a banner block directly under a `## ▶` heading, outside any fenced block.

    ⟳ r1 Codex 3: any `SWITCHED from … → …` in the text counted, so an old transcript quoted in a
    fence fabricated the evidence a banner link rests on. A quote of a banner is not a banner."""
    out, fenced, in_banner = [], False, False
    for ln in text.split("\n"):
        if _FENCE.match(ln):
            fenced, in_banner = not fenced, False
            continue
        if fenced:
            continue
        if _HEADING.match(ln):
            in_banner = True
            continue
        if not in_banner:
            continue
        if not ln.strip():
            continue
        if not ln.startswith("> "):
            in_banner = False
            continue
        if _THREAD.match(ln):
            out += [(m.group(1).strip(), m.group(2).strip()) for m in BANNER.finditer(ln)]
    return out


_TS = re.compile(r'"timestamp"\s*:\s*"([^"]+)"')
_TASK_ID = re.compile(r"<task-id>([\w-]+)</task-id>")
_BG_ID = re.compile(r"running in background with ID: ([\w-]+)")


_CLEARING = re.compile(r"every step in `([^`]+)` is ticked \((\d+)/(\d+)\)\. Clearing")


def read_transcripts(tdir: Path) -> list[Event]:
    """Every event that can move or OBSERVE any checkout's sentinel, from every transcript.

    ⚡ 638 MB on 2026-10-22: lines are filtered by substring BEFORE `json.loads`, and a tool
    result is parsed only when its `tool_use_id` is one this file is waiting for.
    """
    files = sorted(tdir.glob("*.jsonl")) + sorted(tdir.glob("*/subagents/*.jsonl"))
    events: list[Event] = []
    for f in files:
        top = f.parent == tdir
        pending: dict[str, Event] = {}
        mine: list[Event] = []          # this file's events; filtered below, then kept
        hooks = False                   # does this session show the project's Stop hook?
        ended: dict[str, str] = {}      # background task id -> when it completed or was stopped
        last_line = ""
        with open(f, encoding="utf-8", errors="replace") as fh:
            for no, line in enumerate(fh):
                if '"timestamp"' in line:
                    last_line = line
                if "<task-id>" in line and "<status>" in line:
                    tsm = _TS.search(line)
                    for tid in _TASK_ID.findall(line):
                        ended.setdefault(tid, tsm.group(1) if tsm else "")
                is_tr = '"tool_result"' in line
                if is_tr:
                    ids = [i for i in _TOOL_RESULT_ID.findall(line) if i in pending]
                    if not ids:
                        continue
                elif not (any(k in line for k in _PREFILTER)
                          or ('"type":"user"' in line and top)):
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                ts, sess = r.get("timestamp") or "", r.get("sessionId") or ""
                cwd = r.get("cwd") or ""
                typ, msg = r.get("type"), r.get("message") or {}
                base = dict(ts=ts, stream=str(f), order=no, session=sess)
                if typ == "user" and is_tr:
                    for c in msg.get("content") or []:
                        if isinstance(c, dict) and c.get("tool_use_id") in pending:
                            ev = pending.pop(c["tool_use_id"])
                            ev.end = ts
                            ev.data["result"] = _text_of(c.get("content"))
                            ev.data["is_error"] = bool(c.get("is_error"))
                            m = _BG_ID.search(ev.data["result"])
                            if m:
                                ev.data["task"] = m.group(1)
                    continue
                if typ == "user" and top and not r.get("isMeta"):
                    content = msg.get("content")
                    if isinstance(content, str) or (isinstance(content, list) and all(
                            isinstance(c, dict) and c.get("type") == "text" for c in content)):
                        mine.append(Event(kind="prompt", **base))
                    continue
                if typ == "system" and r.get("subtype") == "stop_hook_summary" and top:
                    hooks = True
                    mine.append(Event(kind="stop", data={"cwd": cwd, "hook": True}, **base))
                    continue
                if typ == "attachment" and top:
                    a = r.get("attachment") or {}
                    if a.get("hookEvent") or str(a.get("type", "")).startswith("hook_"):
                        hooks = True
                    m = _CLEARING.search(str(a.get("content") or a.get("stdout") or ""))
                    if a.get("hookEvent") == "Stop" and m:
                        mine.append(Event(kind="clearing", data={
                            "cwd": cwd, "rel": m.group(1)}, **base))
                    continue
                if typ != "assistant":
                    continue
                if top and msg.get("stop_reason") == "end_turn":
                    mine.append(Event(kind="stop", data={"cwd": cwd, "hook": False}, **base))
                for c in msg.get("content") or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text" and "SWITCHED" in c.get("text", ""):
                        for frm, to in live_banners(c["text"]):
                            mine.append(Event(kind="banner", data={"frm": frm, "to": to},
                                                **base))
                    if c.get("type") != "tool_use":
                        continue
                    inp = c.get("input") or {}
                    if c.get("name") == "Bash":
                        # ⛔ EVERY command is parsed (round 2): any command may run code, and a
                        # command that never names begin-plan can still change a sentinel.
                        cmd = inp.get("command") or ""
                        ops = parse_command(cmd, cwd)
                        if ops:
                            ev = Event(kind="cmd", data={
                                "ops": ops, "cmd": cmd,
                                "bg": bool(inp.get("run_in_background"))}, **base)
                            mine.append(ev)
                            pending[c.get("id", "")] = ev
                    elif c.get("name") in ("TaskStop", "KillShell", "KillBash"):
                        tid = inp.get("task_id") or inp.get("shell_id") or inp.get("bash_id")
                        if tid:
                            ended.setdefault(tid, ts)
                    elif c.get("name") in _WRITE_TOOLS:
                        p = os.path.normpath(inp.get("file_path") or inp.get("notebook_path")
                                             or "/")
                        if SENTINEL_REL in p or ".claude/plans/" in p or p.endswith("/.claude"):
                            mine.append(Event(kind="tool", data={"paths": [p]}, **base))
        last = _TS.search(last_line)
        last_ts = last.group(1) if last else ""
        for ev in mine:
            if ev.kind == "cmd":
                # ⛔ r3 Claude M1: a command is not over when it STARTS. A foreground one ends at
                # its result; a background one at its completion or stop record — or, when none
                # is found, at the last event of its session.
                ev.data["until"] = ((ended.get(ev.data.get("task", "")) or last_ts)
                                    if ev.data["bg"] else (ev.end or ev.ts))
                ev.data["session_end"] = last_ts       # where a shell `&`'s window ends
        # ⛔ r3 Claude L1: a turn end is the Stop hook's clear only in a session that shows the
        # hook at all. 272 SDK security-review sessions here record no hook of any kind.
        events.extend(ev for ev in mine
                      if not (ev.kind == "stop" and not ev.data["hook"] and not hooks))
    events.sort(key=lambda e: (e.ts, e.stream, e.order))
    return events


# ── the replay ────────────────────────────────────────────────────────────────────────────────

@dataclass
class Armed:
    rel: str
    n: int | None
    lo: int
    hi: int
    paused: bool | None


UNKNOWN = "UNKNOWN"
START = (UNKNOWN, "before the first transcript, so not yet observed")


def _slug_of(rel: str) -> str | None:
    """The live `_plan_slug` rule: only a `.claude/plans/*.md` file names a plan."""
    d, b = os.path.split(os.path.normpath(rel))
    return b[:-3] if d == PLAN_REL and b.endswith(".md") else None


def _rel(path: str, root: str) -> str:
    p = os.path.normpath(path)
    return os.path.relpath(p, root) if os.path.isabs(p) else p


def observed(info: dict, root: str) -> Armed:
    """The sentinel a call's output OBSERVED: armed, un-paused, at the printed count."""
    rel = _rel(info["rel"], root)
    if info["n"] is None:
        return Armed(rel, 1, 1, 1, False) if info["full"] else Armed(rel, None, 0, 0, False)
    return Armed(rel, info["n"], info["done"], info["done"], False)


def describe(state: object) -> str:
    if state is None:
        return "nothing armed"
    if isinstance(state, Armed):
        n = "?" if state.n is None else state.n
        tick = f"{state.lo}" if state.lo == state.hi else f"{state.lo}-{state.hi}"
        return (f"{state.rel} {tick}/{n}"
                + {True: " paused", None: " paused?", False: ""}[state.paused])
    return f"UNKNOWN ({state[1]})"


def replay(events: list[Event], root: str, stats: dict | None = None) -> dict[str, dict]:
    """`root`'s plans: slug -> {parent, why, session, ts, stream, banners, …}. `parent` None
    means NO MARKER. Every checkout's sentinel is replayed SEPARATELY (r1 Codex 1).

    ⭐ CHECKPOINTS (r1 Claude F4; narrowed in r2). Only the TOOLS' own state lines count:
    `--status`, the state line of an arm or tick, `--finish`'s reply, and the Stop hook's own
    `Clearing` message — never a read of the file (r2 Codex 1). At each, the replayed state is compared
    with what was observed. A disagreement RESETS the replay to the observation and UNMARKS every
    plan first armed since the last checkpoint — those parents were derived from a state now known
    to be wrong. Before the first checkpoint the state is UNKNOWN (r1 Claude F3).
    """
    states: dict[str, object] = {}
    cleared: dict[str, str | None] = {}
    seen: dict[str, dict[str, dict]] = {}
    pending: dict[str, list[str]] = {}
    counts: dict = {"agree": 0, "disagree": 0, "resolved": 0, "resync": 0, "where": [],
                    "in_window": 0}

    def get(r: str) -> object:
        return states.get(r, START)

    def unknown(why: str) -> tuple:
        return (UNKNOWN, why)

    def poison(r: str | None, why: str) -> None:
        """`r`'s state is unknown from here; None = no checkout can be named, so all of them."""
        if r is None:
            for k in list(states):
                states[k] = unknown(why)
            states[None] = unknown(why)    # type: ignore[index]
        else:
            states[r] = unknown(why)

    def known_roots() -> list[str]:
        return sorted({k for k in states if k is not None} | {root})

    def checkpoint(r: str, obs: tuple, ts: str, label: str) -> bool:
        """Compare `r`'s replayed state with an observation. Returns whether it agreed (a
        resync from UNKNOWN counts as agreeing). The CALLER then sets the observed state."""
        cur = get(r)
        if isinstance(cur, tuple):
            counts["resync"] += 1
            agree = True
        elif obs[0] == "none":
            agree = cur is None
        elif obs[0] == "cleared":      # the hook / --finish saw THIS plan armed and cleared it
            agree = (isinstance(cur, Armed) and (obs[1] is None or os.path.normpath(cur.rel)
                                                 == os.path.normpath(obs[1]))) or (
                cur is None and obs[1] is not None and cleared.get(r) == _slug_of(obs[1]))
        else:
            agree = isinstance(cur, Armed) and (
                os.path.normpath(cur.rel) == os.path.normpath(obs[1]))
        if not isinstance(cur, tuple):
            counts["agree" if agree else "disagree"] += 1
        if not agree:
            counts["where"].append(f"{ts} {label}: replay had {describe(cur)}, observed "
                                   f"{' '.join(str(x) for x in obs)}")
            for slug in pending.get(r, []):
                rec = seen[r][slug]
                rec["parent"], rec["why"] = None, (f"replay contradicted by an observation "
                                                   f"({label}) at {ts}")
            counts["resolved"] += 1
        pending[r] = []
        return agree

    trail: list[tuple[str, str, str]] = []     # (when, what moved it, the state after) — --explain
    snap, last = get(root), None
    bps = [e for e in events if e.kind == "cmd"]

    def overlapping(e: Event, r: str) -> bool:
        """Did another stream change `r`'s plan state while `e` ran?"""
        lo, hi = e.ts, e.end or e.ts
        for o in bps:
            if o.stream == e.stream or not (o.ts <= hi and (o.end or o.ts) >= lo):
                continue
            if any(op.kind in ("opaque", "rmsent")
                   or op.kind == "call" and op.root in (r, None)
                   and _sub(op.call)[0] != "ro" for op in o.data["ops"]):
                return True
        for o in events:
            if o.stream == e.stream or not lo <= o.ts <= hi:
                continue
            st = get(r)
            if o.kind in ("tool", "clearing") or (o.kind == "stop" and isinstance(st, Armed)
                                                  and st.paused is not True
                                                  and (st.n is None or st.hi >= st.n)):
                return True
        return False

    # ⛔ r3 Claude M1: WINDOWS. (root or None = every checkout, start, until, stream, bg). While a
    # command that may change a checkout is still running, that checkout stays UNKNOWN, and a
    # checkpoint inside the window resolves nothing.
    windows: list[tuple] = []

    def active(r: str, e: Event) -> str | None:
        # ⚠ no exemption for the command's own stream: tool calls in one message can run in
        # PARALLEL, so a sibling call may start before this one's result. Sequential calls start
        # after it ends, so they are outside the window anyway.
        for w in windows:
            if w[0] in (r, None) and w[1] < e.ts < w[2]:
                return w[2]
        return None

    for e in events:
        windows[:] = [w for w in windows if w[2] > e.ts]
        for r in known_roots():
            until = active(r, e)
            if until:
                counts["in_window"] += 1 if e.kind == "cmd" and r == root else 0
                states[r] = unknown(f"a command that may change it was still running (until "
                                    f"{until})")
        if last is not None and get(root) != snap:
            trail.append((last.ts, f"{last.kind} in {Path(last.stream).stem[:8]}",
                          describe(get(root))))
            del trail[:-6]
        snap, last = get(root), e
        if e.kind == "stop":
            # The Stop hook runs in the session's project (`root`) — or in its cwd. Where both
            # readings name the same checkout its clear is CERTAIN; anywhere else it MAY have
            # happened, so a plan that may be fully ticked becomes unknown.
            for r in [k for k in states if k is not None]:
                st = get(r)
                if not isinstance(st, Armed) or st.paused is True:
                    continue
                maybe_full = st.n is None or st.hi >= st.n
                full = st.n is not None and st.lo >= st.n
                certain = r == root and e.data.get("cwd") == root
                if not certain or st.paused is None:
                    if maybe_full and (certain or r in (root, e.data.get("cwd"))):
                        states[r] = unknown("a turn ended where the Stop hook's effect "
                                            "cannot be known")
                elif full:
                    cleared[r], states[r] = _slug_of(st.rel), None
                elif maybe_full:
                    states[r] = unknown("a turn ended after a tick whose result was not read")
            continue
        if e.kind == "clearing":
            if e.data["cwd"] != root:
                continue
            rel = e.data["rel"]
            checkpoint(root, ("cleared", rel), e.ts, "the Stop hook's Clearing message")
            cleared[root], states[root] = _slug_of(rel), None
            continue
        if e.kind == "tool":
            for r in reaches(Op("opaque", paths=e.data["paths"]), known_roots()) or []:
                poison(r, "an edit tool wrote its sentinel or a plan file")
            continue
        if e.kind != "cmd":
            continue
        ops = e.data["ops"]
        calls = [o for o in ops if o.kind == "call"]
        subs = [_sub(o.call) for o in calls]
        changing = [o for o, (s_, _v) in zip(calls, subs) if s_ != "ro"]
        roots = {o.root for o in changing}
        # ⛔ r1 Codex 1: output is one stream. When the calls that print span more than one
        # checkout (or one that cannot be resolved), no line of it can be attributed.
        ambiguous = len(roots) > 1 or None in roots
        outs = (read_outcomes(subs, e.data.get("result"), e.data.get("is_error", False))
                if not ambiguous else [("unknown", {})] * len(calls))
        by_call = {id(o): (s_, oc) for o, s_, oc in zip(calls, subs, outs)}
        # ⛔ THE ALLOW-LIST, APPLIED FIRST (round 2, Codex 3). Anything opaque in the command
        # poisons every checkout it can reach BEFORE any call in it is processed, so an arm in
        # the same command derives no parent. A lone `rm -f` of a sentinel stays a known removal
        # only when nothing else in the command is opaque.
        opaques = [o for o in ops if o.kind == "opaque"]
        until = e.data.get("until") or e.end or e.ts
        bg = e.data.get("bg", False)
        if bg:
            # a call left running in the background printed nothing yet: its checkout is unknown
            for o in calls:
                if _sub(o.call)[0] != "ro":
                    poison(o.root, "a begin-plan call ran in the background")
                    windows.append((o.root, e.ts, until, e.stream, True))
        for o in opaques:
            reach = reaches(o, known_roots())
            # a shell `&` op has no end record of its own: its window runs to the session's end
            o_until = max(until, e.data.get("session_end") or until) if o.bg else until
            for r in ([None] if reach is None else reach):
                windows.append((r, e.ts, o_until, e.stream, bg or o.bg))
        if opaques:
            for o in opaques + [Op("opaque", paths=[x.root + _SENT_TAIL], why="`rm`")
                                for x in ops if x.kind == "rmsent"]:
                reach = reaches(o, known_roots())
                why = f"the same command ran an unrecognised operation: {o.why}"
                if reach is None:
                    poison(None, why)
                for r in reach or []:
                    poison(r, why)
        for op in ops:
            if op.kind == "rmsent":
                if not opaques:
                    # a removal is a KNOWN state — but a hand `rm` is no clear a banner may cite
                    states[op.root], cleared[op.root] = None, None
                continue
            if op.kind != "call":
                continue
            (sub, val), (oc, data) = by_call[id(op)]
            r = op.root
            if sub == "ro":
                continue
            if ambiguous or op.call.loop:
                why = ("its output could not be attributed to one checkout" if ambiguous else
                       "a begin-plan call inside a shell loop ran an unknown number of times")
                if sub == "arm" and r is not None and val not in seen.get(r, {}):
                    seen.setdefault(r, {})[val] = {"parent": None, "why": why, "cleared": None,
                                                   "session": e.session, "ts": e.ts,
                                                   "stream": e.stream}
                if sub != "status":
                    poison(r, why)
                continue
            if oc == "refused":
                continue
            if sub == "status":
                if oc == "ok":
                    obs = ("none",) if data.get("none") else ("armed", data["rel"])
                    checkpoint(r, obs, e.ts, "--status")
                    states[r] = (None if data.get("none") else
                                 Armed(_rel(data["rel"], r), data["n"], data["done"],
                                       data["done"], data["paused"]))
                continue
            if sub == "arm":
                slug = val
                mine = seen.setdefault(r, {})
                if slug not in mine:
                    st = get(r)
                    if oc == "unknown":
                        mine[slug] = {"parent": None, "why": "its first arm's output was not "
                                      "readable, so whether it armed then cannot be told"}
                    else:
                        if st is None:
                            par, why = STARTED, ""
                        elif isinstance(st, Armed):
                            par = _slug_of(st.rel)
                            why = "" if par else (f"the sentinel named {st.rel}, which is "
                                                  f"not a plan file")
                        else:
                            par, why = None, f"the sentinel's state was unknown: {st[1]}"
                        if par is not None and overlapping(e, r):
                            par, why = None, ("another session or agent changed plan state "
                                              "while this arm ran")
                        mine[slug] = {"parent": par, "why": why, "cleared": cleared.get(r)}
                        pending.setdefault(r, []).append(slug)
                    mine[slug].update(session=e.session, ts=e.ts, stream=e.stream,
                                      before=describe(st),
                                      trail=list(trail) if r == root else [])
                states[r] = (unknown(f"the output of arming {slug} was not readable")
                             if oc == "unknown" else observed(data, r))
            elif sub == "plan":
                states[r] = (unknown("the output of --plan was not readable")
                             if oc == "unknown" else observed(data, r))
            elif sub == "tick":
                if oc == "ok":
                    # the state line OBSERVES which plan was armed — a checkpoint — and a tick
                    # that succeeded proves it was not paused (`cmd_tick` refuses)
                    checkpoint(r, ("armed", data["rel"]), e.ts, "a tick's state line")
                    states[r] = observed(data, r)
                elif isinstance(get(r), Armed):
                    st = get(r)
                    hi = st.hi + 1 if st.n is None else min(st.n, st.hi + 1)
                    states[r] = Armed(st.rel, st.n, st.lo, hi, st.paused)
            elif sub in ("pause", "resume"):
                if isinstance(get(r), Armed):
                    st = get(r)
                    p = (sub == "pause") if oc == "ok" else None
                    states[r] = Armed(st.rel, st.n, st.lo, st.hi, p)
            elif sub == "finish":
                if oc == "ok" and data.get("inferred"):
                    # it ran, but printed nothing that survived: no OBSERVATION, only the effect.
                    # Finishing nothing changes nothing, so `cleared` survives a finish of None.
                    st = get(r)
                    if not (st is None):
                        cleared[r] = _slug_of(st.rel) if isinstance(st, Armed) else None
                elif oc == "ok" and data.get("none"):
                    checkpoint(r, ("none",), e.ts, "--finish: nothing was armed")
                elif oc == "ok":
                    st = get(r)
                    agree = checkpoint(r, ("cleared", None), e.ts, "--finish cleared a plan")
                    cleared[r] = _slug_of(st.rel) if agree and isinstance(st, Armed) else None
                states[r] = (None if oc == "ok" else
                             unknown("the output of --finish was not readable"))
    if stats is not None:
        stats.update(counts)
    mine = seen.get(root, {})
    _attach_banners(mine, events)
    return mine


def _sub(call: Call) -> tuple[str, str | None]:
    if call.script == "progress":
        return ("status", None) if "--status" in call.args else ("ro", None)
    return classify(call.args)


def _attach_banners(seen: dict[str, dict], events: list[Event]) -> None:
    """Each plan gets the banners said IN THE TURN of its first arm, in that stream."""
    by_stream: dict[str, list[Event]] = {}
    for e in events:
        if e.kind in ("prompt", "banner"):
            by_stream.setdefault(e.stream, []).append(e)
    for slug, rec in seen.items():
        rec.setdefault("banners", [])
        if "ts" not in rec:
            continue
        evs = by_stream.get(rec["stream"], [])
        before = [p.ts for p in evs if p.kind == "prompt" and p.ts <= rec["ts"]]
        after = [p.ts for p in evs if p.kind == "prompt" and p.ts > rec["ts"]]
        lo, hi = (max(before) if before else ""), (min(after) if after else "￿")
        mine = [b for b in evs
                if b.kind == "banner" and b.data["to"] == slug and lo <= b.ts < hi]
        rec["banners"] = [b.data["frm"] for b in mine]
        rec["banner_src"] = [{"frm": b.data["frm"], "session": b.session, "ts": b.ts}
                             for b in mine]


# ── the decision, per plan on disk ────────────────────────────────────────────────────────────

def birth_time(p: Path) -> float | None:
    st = p.stat()
    return getattr(st, "st_birthtime", None)


def _epoch(ts: str) -> float:
    return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _banner_link(rec: dict, banners: list[str]) -> dict | None:
    """The banner that names EXACTLY the plan a clear just removed, if the slug-shaped banners
    in the arm's turn name that plan and nothing else; else None."""
    named = [b for b in banners if SLUG.fullmatch(b)]
    if not rec.get("cleared") or named != [rec["cleared"]]:
        return None
    return next((b for b in rec.get("banner_src", []) if b["frm"] == rec["cleared"]), None)


def decide(plans: dict[str, str], seen: dict[str, dict], births: dict[str, float | None]
           ) -> list[dict]:
    """PURE. One row per plan on disk: {slug, replay, banner, verdict, why, marker}."""
    rows = []
    for slug in sorted(plans):
        text = plans[slug]
        rec = seen.get(slug)
        rep = rec["parent"] if rec else None
        banners = sorted(set(rec.get("banners", []))) if rec else []
        row = {"slug": slug, "replay": rep, "banner": ", ".join(banners) or "", "marker": None}
        if PARENT_LINE.search(text):
            row.update(verdict="untouched", why="already has a parent marker"
                       + (" (reconstructed)" if SOURCE_LINE.search(text) else " (live)"))
        elif rec is None:
            row.update(verdict="no-marker", why="no recorded arm in the transcripts")
        elif rep is None:
            row.update(verdict="no-marker", why=rec["why"])
        elif births.get(slug) is None:
            row.update(verdict="no-marker", why="the file's creation time is unavailable, so "
                       "its first recorded arm cannot be shown to be its creation")
        elif births[slug] < _epoch(rec["ts"]) - BIRTH_SLACK_S:
            row.update(verdict="no-marker", why="the file existed before its first recorded "
                       "arm, so that arm was not its creation")
        # ⛔ A SLUG-SHAPED name is a witness even when no such plan is on disk: measured, six
        # banners named a thread armed in ANOTHER checkout (`quiet-stop-observers`) or one never
        # armed at all, and filtering to plans on disk silently KEPT all six. Prose such as
        # `(session start)` names no thread and is no witness.
        # ⭐ OPTION A (owner, 2026-10-22): the replay's `-` came ONLY from a clear, and every
        # slug-shaped banner in the arm's turn names EXACTLY the plan that clear removed. The
        # link is the banner's, so it is labelled with the BANNER's session and time — never as
        # a transcript replay. A banner never overrides a parent the replay found ARMED.
        elif rep == STARTED and _banner_link(rec, banners):
            src = _banner_link(rec, banners)
            row.update(verdict="keep-banner",
                       why=f"the replay's `-` follows clearing {rec['cleared']}, which a banner "
                           f"names as the plan being left",
                       marker=(f"<!-- parent: {rec['cleared']} -->\n<!-- parent-source: banner "
                               f"{src['session'][:8]} {src['ts']} -->"))
        elif any(b != rep for b in banners if SLUG.fullmatch(b)):
            row.update(verdict="no-marker", why=f"a banner said {row['banner']}, the replay "
                       f"says {rep}")
        else:
            row.update(verdict="keep", why="",
                       marker=(f"<!-- parent: {rep} -->\n<!-- parent-source: transcript "
                               f"{rec['session'][:8]} {rec['ts']} -->"))
        rows.append(row)
    return rows


def apply_marker(text: str, marker: str) -> str:
    """The two lines go on their own lines directly under the title."""
    lines = text.split("\n")
    if lines and lines[0].startswith("#"):
        return "\n".join([lines[0], "", marker] + lines[1:])
    return marker + "\n\n" + text


def read_plans(plan_dir: Path) -> dict[str, str]:
    if not plan_dir.is_dir():
        raise ValueError(f"{plan_dir} is not a directory")
    return {f.stem: f.read_text(errors="replace") for f in sorted(plan_dir.glob("*.md"))
            if f.is_file()}


def render_table(rows: list[dict]) -> str:
    w = max([len(r["slug"]) for r in rows] + [4])
    out = [f"{'plan':<{w}}  {'replayed parent':<34}  {'banner says':<30}  verdict"]
    for r in rows:
        out.append(f"{r['slug']:<{w}}  {str(r['replay'] or '—'):<34}  {r['banner'] or '—':<30}  "
                   f"{r['verdict']}{': ' + r['why'] if r['why'] else ''}")
    tally: dict[str, int] = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    out.append("")
    out.append("totals: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items()))
               + f" (of {len(rows)} plans)")
    dis = [r for r in rows if r["why"].startswith("a banner said")]
    out.append(f"banner disagreements: {len(dis)}"
               + "".join(f"\n  {r['slug']}: {r['why']}" for r in dis))
    return "\n".join(out)


def run(plan_dir: Path, tdir: Path, root: str, write: bool, births=None) -> tuple[int, str]:
    """(rc, report). rc 2 = CANNOT RUN and nothing is written."""
    try:
        plans = read_plans(plan_dir)
    except (ValueError, OSError) as exc:
        return 2, f"CANNOT RUN — {exc}"
    if not tdir.is_dir():
        return 2, f"CANNOT RUN — no transcripts at {tdir}"
    seen = replay(read_transcripts(tdir), root)
    if births is None:
        births = {s: birth_time(plan_dir / f"{s}.md") for s in plans}
    rows = decide(plans, seen, births)
    report = render_table(rows)
    if write:
        n = 0
        # ⛔ `.claude/last-plan` FINGERPRINTS the last finished plan (`check-plan-progress.
        # record_last_plan`), and `begin-plan` records NO parent once that file's bytes change. So
        # writing a marker into it would cost the NEXT live link; it is left for a later run.
        last = _last_plan_slug(plan_dir.parent / "last-plan")
        for r in rows:
            if r["verdict"] not in ("keep", "keep-banner"):
                continue
            if r["slug"] == last:
                report += (f"\nskipped {last}: .claude/last-plan fingerprints it, and changing "
                           f"its bytes would cost the next plan its live parent")
                continue
            p = plan_dir / f"{r['slug']}.md"
            st = p.stat()
            # ⟳ r1 Claude F5: ATOMIC — a temp file beside it, then `os.replace`, so an interrupted
            # run leaves the old plan or the new one, never a truncated one.
            tmp = p.with_name(f".{p.name}.backfill-tmp")
            tmp.write_text(apply_marker(plans[r["slug"]], r["marker"]))
            # ⛔ the page dates a plan by its mtime: a backfill must not make every plan "today"
            os.utime(tmp, (st.st_atime, st.st_mtime))
            os.replace(tmp, p)
            n += 1
        report += f"\nwrote {n} plan file(s) in {plan_dir}"
    else:
        report += ("\nDRY RUN — nothing was written. --write applies the `keep` and "
                   "`keep-banner` rows.")
    return 0, report


def _last_plan_slug(path: Path) -> str | None:
    try:
        m = re.search(r"^plan:\s*(\S+)\s*$", path.read_text(), re.M)
    except OSError:
        return None
    return _slug_of(m.group(1)) if m else None


def ground_truth(tdir: Path, root: str) -> tuple[int, str]:
    """The replay must reproduce the live link, and every checkpoint DISAGREEMENT must have been
    resolved — reset to the observation, with the plans armed since the last checkpoint unmarked.
    The agree/disagree counts are reported either way: a disagreement is a measured error rate."""
    if not tdir.is_dir():
        return 2, f"CANNOT RUN — no transcripts at {tdir}. Treat the ground-truth check as NOT RUN."
    events = read_transcripts(tdir)
    if not any(e.kind == "cmd" and any(o.kind == "call" and o.root == root
                                       for o in e.data["ops"]) for e in events):
        return 2, (f"CANNOT RUN — {tdir} holds no begin-plan call for {root}. Treat the "
                   f"ground-truth check as NOT RUN.")
    stats: dict = {}
    got = replay(events, root, stats).get(GROUND_TRUTH[0], {}).get("parent")
    line = (f"checkpoints: agree {stats['agree']}, disagree {stats['disagree']} (resolved "
            f"{stats['resolved']}), resync from unknown {stats['resync']}")
    if stats["disagree"] != stats["resolved"]:
        return 1, f"FAIL — {stats['disagree'] - stats['resolved']} disagreement(s) unresolved\n{line}"
    if got != GROUND_TRUTH[1]:
        return 1, (f"FAIL — the replay gives {GROUND_TRUTH[0]} the parent {got!r}; the live code "
                   f"recorded {GROUND_TRUTH[1]!r}\n{line}")
    return 0, (f"OK — the replay reproduces {GROUND_TRUTH[0]} <- {GROUND_TRUTH[1]}\n{line}"
               + "".join(f"\n  disagreement {w}" for w in stats["where"]))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, help="the checkout whose sentinel is replayed "
                    "(default: the main working tree)")
    ap.add_argument("--plans", type=Path, help="the plans directory (default: ROOT/.claude/plans)")
    ap.add_argument("--transcripts", type=Path, help="default: ~/.claude/projects/<root>")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--ground-truth", action="store_true")
    ap.add_argument("--explain", metavar="SLUG", help="print how the replay decided one plan")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    root = (a.root or main_checkout()).resolve()
    tdir = a.transcripts or transcripts_for(root)
    if a.explain:
        rec = replay(read_transcripts(tdir), str(root)).get(a.explain)
        if rec is None:
            print(f"{a.explain}: no recorded arm in the transcripts")
            return 0
        print(f"{a.explain}: first armed {rec.get('ts')} in {Path(rec.get('stream', '')).stem}")
        for when, what, after in rec.get("trail", []):
            print(f"  {when}  {what:<22}  -> {after}")
        print(f"  sentinel at that arm: {rec.get('before')}")
        print(f"  replayed parent: {rec['parent']!r}  {rec.get('why', '')}")
        print(f"  banners in that turn: {rec.get('banners') or 'none'}")
        return 0
    if a.ground_truth:
        rc, msg = ground_truth(tdir, str(root))
        print(msg)
        return rc
    rc, msg = run(a.plans or root / PLAN_REL, tdir, str(root), a.write)
    print(msg)
    return rc


# ── self-test: CONSTRUCTED transcripts only, never the real ones ──────────────────────────────

class _Fx:
    """A fake transcript directory. Every event advances one clock by 10 seconds."""

    def __init__(self, root: str):
        self.root, self.t, self.lines = root, _dt.datetime(2026, 10, 1, 12, 0, 0), {}
        self.n = 0

    def _ts(self, step: float = 10.0) -> str:
        self.t += _dt.timedelta(seconds=step)
        return self.t.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _put(self, stream: str, rec: dict) -> None:
        self.lines.setdefault(stream, []).append(json.dumps(rec))

    def bash(self, cmd: str, result: str | None, *, stream="sess-aaaa1111", cwd=None,
             is_error=False, run_s: float = 1.0, bg: bool = False) -> str:
        self.n += 1
        tid = f"toolu_{self.n:04d}"
        ts = self._ts()
        sess = stream.split("/")[0]
        self._put(stream, {"type": "assistant", "timestamp": ts, "sessionId": sess,
                           "cwd": cwd or self.root, "message": {"role": "assistant",
                           "stop_reason": "tool_use", "content": [{"type": "tool_use",
                           "id": tid, "name": "Bash", "input": dict(
                               {"command": cmd}, **({"run_in_background": True} if bg else {}))}]}})
        if result is not None:
            end = (self.t + _dt.timedelta(seconds=run_s)).strftime("%Y-%m-%dT%H:%M:%S.500Z")
            self._put(stream, {"type": "user", "timestamp": end, "sessionId": sess,
                               "message": {"role": "user", "content": [{"type": "tool_result",
                               "tool_use_id": tid, "is_error": is_error, "content": result}]}})
        return ts

    def tool_stop(self, task_id: str, *, stream="sess-aaaa1111") -> None:
        self.n += 1
        self._put(stream, {"type": "assistant", "timestamp": self._ts(), "sessionId": stream,
                           "cwd": self.root, "message": {"role": "assistant", "content": [
                               {"type": "tool_use", "id": f"toolu_{self.n:04d}",
                                "name": "TaskStop", "input": {"task_id": task_id}}]}})

    def tool(self, name: str, path: str, *, stream="sess-aaaa1111") -> None:
        self.n += 1
        self._put(stream, {"type": "assistant", "timestamp": self._ts(), "sessionId": stream,
                           "cwd": self.root, "message": {"role": "assistant", "content": [
                               {"type": "tool_use", "id": f"toolu_{self.n:04d}", "name": name,
                                "input": {"file_path": path}}]}})

    def stop(self, *, stream="sess-aaaa1111", cwd=None) -> None:
        self._put(stream, {"type": "system", "subtype": "stop_hook_summary",
                           "timestamp": self._ts(), "sessionId": stream.split("/")[0],
                           "cwd": cwd or self.root})

    def prompt(self, text="go on", *, stream="sess-aaaa1111") -> None:
        self._put(stream, {"type": "user", "timestamp": self._ts(), "sessionId": stream,
                           "message": {"role": "user", "content": text}})

    def say(self, text: str, *, stream="sess-aaaa1111") -> None:
        self._put(stream, {"type": "assistant", "timestamp": self._ts(), "sessionId": stream,
                           "cwd": self.root, "message": {"role": "assistant",
                           "stop_reason": "end_turn", "content": [{"type": "text",
                                                                   "text": text}]}})

    def task_done(self, task_id: str, *, stream="sess-aaaa1111", status="completed") -> None:
        """The harness's notice that a background task ended."""
        self._put(stream, {"type": "user", "timestamp": self._ts(), "sessionId": stream,
                           "message": {"role": "user", "content": (
                               f"<task-notification>\n<task-id>{task_id}</task-id>\n"
                               f"<status>{status}</status>\n</task-notification>")}})

    def hook_note(self, *, stream="sess-aaaa1111") -> None:
        """Some project hook ran in this session (a PostToolUse one, say)."""
        self._put(stream, {"type": "attachment", "timestamp": self._ts(), "sessionId": stream,
                           "cwd": self.root, "attachment": {"type": "hook_success",
                           "hookEvent": "PostToolUse", "content": "ok"}})

    def clearing(self, slug: str, d: int, n: int, *, stream="sess-aaaa1111",
                 kind: str = "hook_success") -> None:
        """The Stop hook's own message when it clears a fully-ticked plan."""
        msg = (f"✅ every step in `.claude/plans/{slug}.md` is ticked ({d}/{n}). "
               f"Clearing .claude/executing-plan.")
        self._put(stream, {"type": "attachment", "timestamp": self._ts(), "sessionId": stream,
                           "cwd": self.root, "attachment": {"type": kind,
                           "hookEvent": "Stop", "content": msg, "stdout": msg + "\n"}})

    def write(self, tdir: Path) -> Path:
        for stream, lines in self.lines.items():
            p = tdir / (stream + ".jsonl")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("\n".join(lines) + "\n")
        return tdir


def _arm_out(slug: str, n: int) -> str:
    return f"armed: .claude/executing-plan -> .claude/plans/{slug}.md ({n} steps)\n\n## ▶ STEP 1"


def _tick_out(i: int, n: int, slug: str = "one") -> str:
    """What `cmd_tick` prints: the tick line, then `_print_state`'s state line."""
    rel = f".claude/plans/{slug}.md"
    tail = (f"✅ every step in {rel} is ticked. The Stop guard will allow the turn to end"
            if i >= n else f"## ▶ STEP {i + 1}\n\n(plan: {rel} — {i}/{n} ticked. `--tick` …)")
    return f"ticked step {i} of {n} in {rel}\n\n{tail}"


def _self_test() -> int:
    import tempfile
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    BP = "python3 scripts/begin-plan.py"

    NONE_OUT = "no plan is being executed (no .claude/executing-plan)"
    # The self-test never asks git: these are the "tracked" scripts of its constructed world.
    global TRACKED_SCRIPTS
    _saved_tracked = TRACKED_SCRIPTS
    TRACKED_SCRIPTS = frozenset({"recall-llm.py", "gen-work-lines.py", "check-docs.py"})

    def world(build, root="/w/repo", stats=None, start=True):
        """Replay a constructed transcript; slug -> parent. It opens with an OBSERVED empty
        sentinel unless `start` is False — the replay no longer assumes one (r1 Claude F3)."""
        fx = _Fx(root)
        if start:
            fx.bash("python3 scripts/begin-plan.py --status", NONE_OUT)
        build(fx)
        with tempfile.TemporaryDirectory() as d:
            seen = replay(read_transcripts(fx.write(Path(d))), root, stats)
        return {k: v["parent"] for k, v in seen.items()}, seen

    # ── review round 1: each reviewer's path to a WRONG link, reproduced ─────────────────────

    def fresh(build):
        """Start from an OBSERVED empty sentinel — the replay no longer assumes one (F3)."""
        def b(f):
            f.bash(f"{BP} --status", NONE_OUT)
            build(f)
        return b

    def _loop_unread(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"for i in 1 2; do {BP} --tick >/dev/null 2>&1; done", "")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ F1: a call inside a shell LOOP ran an unknown number of times — no marker after it",
         world(fresh(_loop_unread))[0]["two"], None)

    def _loop_status(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"for i in 1 2; do {BP} --tick; done; {BP} --status",
               "ticked step 2 of 2 in .claude/plans/one.md\n"
               ".claude/plans/one.md: 2/2 steps ticked, 0 remaining")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⭐ F1/F4: ...and the `--status` after the loop is a CHECKPOINT that resyncs it",
         world(fresh(_loop_status))[0]["two"], STARTED)

    def _rm_then_arm(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"rm -f .claude/executing-plan && {BP} two a b c", _arm_out("two", 3))
    case("⛔ F2: a sentinel `rm` in the SAME command as an arm is applied, in order, before it",
         world(fresh(_rm_then_arm))[0]["two"], STARTED)

    def _status_then_rm(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --status; rm -f .claude/executing-plan",
               ".claude/plans/one.md: 0/1 steps ticked, 1 remaining")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ Codex 2: `--status; rm -f .claude/executing-plan` — the rm is not hidden by the call",
         world(fresh(_status_then_rm))[0]["two"], STARTED)

    def _pause_by_hand(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1, "one"))
        f.bash(f"sed -i '' '/^paused:/d' .claude/executing-plan && printf 'paused: x\\n' >> "
               f".claude/executing-plan && {BP} --banner", "## ▶ STEP 1")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ F2: a hand edit beside a call makes the state UNKNOWN — the turn end may not clear it",
         world(fresh(_pause_by_hand))[0]["two"], None)

    def _two_roots(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"( {BP} --tick; cd /w/other; {BP} side a ) | tail -1",
               "(plan: .claude/plans/side.md — 0/1 ticked. `scripts/begin-plan.py --tick` …)")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    _tr = world(fresh(_two_roots))[0]
    case("⛔ Codex 1: output from a command spanning TWO checkouts is attributed to neither",
         (_tr["two"], "side" in _tr), (None, False))

    def _quoted_banner(fence):
        def b(f):
            f.bash(f"{BP} one a", _arm_out("one", 1))
            f.bash(f"{BP} --finish", "cleared .claude/executing-plan")
            f.prompt()
            f.say(fence)
            f.bash(f"{BP} two a", _arm_out("two", 1))
        return b
    _pl3 = {s_: f"# {s_}\n\n- [ ] a\n" for s_ in ("one", "two")}
    _bi3 = {s_: _dt.datetime(2026, 10, 1, 13, tzinfo=_dt.timezone.utc).timestamp() for s_ in _pl3}
    _qb = [{r["slug"]: r["verdict"] for r in decide(_pl3, world(fresh(_quoted_banner(t_)))[1],
                                                     _bi3)}["two"] for t_ in (
        "Old transcript:\n```\n## ▶ STEP 1\n\n> **Thread:** ⤳ SWITCHED from `one` → `two`\n```",
        "> ## ▶ STEP 1\n>\n> > **Thread:** ⤳ SWITCHED from `one` → `two`",
        "As I said: ⤳ SWITCHED from `one` → `two`",
        "## ▶ STEP 1\n\n> **Thread:** ⤳ SWITCHED from `one` (done) → `two` · 0 of 1")]
    case("⛔ Codex 3: a banner counts only as LIVE text under a `## ▶` heading — fenced, quoted "
         "and prose mentions do not", _qb, ["keep", "keep", "keep", "keep-banner"])

    def _no_start(f):
        f.bash(f"{BP} first a", _arm_out("first", 1))
    case("⛔ F3: before any checkpoint the state is UNKNOWN — the first arm gets no marker",
         world(_no_start, start=False)[0]["first"], None)

    def _contradicted(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} mid a", _arm_out("mid", 1))
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    _ct_stats: dict = {}
    _ct = world(fresh(_contradicted), stats=_ct_stats)
    case("⭐ F4: an observation that CONTRADICTS the replay resets it, and unmarks every plan armed "
         "since the last agreeing checkpoint",
         (_ct[0], "contradicted by an observation" in _ct[1]["mid"]["why"],
          {k: _ct_stats.get(k) for k in ("disagree", "resolved")}),
         ({"one": None, "mid": None, "two": STARTED}, True,
          {"disagree": 1, "resolved": 1}))

    def _agreed(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --status", ".claude/plans/one.md: 0/1 steps ticked, 1 remaining")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    _ag_stats: dict = {}
    case("...and one that AGREES leaves the replay's links standing",
         (world(fresh(_agreed), stats=_ag_stats)[0], _ag_stats.get("agree", 0) >= 1),
         ({"one": STARTED, "two": "one"}, True))

    def _opaque(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("python3 - <<'EOF'\nfrom pathlib import Path\n"
               "Path('.claude/executing-plan').write_text('plan: x')\nEOF", "")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ F2: a Python heredoc that writes a sentinel cannot be ordered — no marker after it",
         world(_opaque)[0]["two"], None)

    def _hook_cleared(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"{BP} --tick | tail -0", "")
        f.clearing("one", 2, 2)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⭐ F4: the Stop hook's own `Clearing` message is a checkpoint: the plan WAS cleared",
         world(fresh(_hook_cleared))[0]["two"], STARTED)

    def _finish_after_clear(f):
        f.bash(f"{BP} prev a", _arm_out("prev", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1, "prev"))
        f.stop()
        f.prompt()
        f.say("## ▶ STEP 1\n\n> **Thread:** ⤳ SWITCHED from `prev` (done) → `nxt` · 0 of 1")
        f.bash(f"{BP} --finish >/dev/null 2>&1; {BP} nxt a", _arm_out("nxt", 1))
    _fa_stats: dict = {}
    _fa = world(_finish_after_clear, stats=_fa_stats)[1]
    case("⛔ a --finish whose output was discarded is no OBSERVATION: finishing an already-cleared "
         "plan is not a disagreement, and the banner link survives",
         (_fa_stats.get("disagree"), {r["slug"]: r["verdict"] for r in decide(
             {"prev": "# prev\n", "nxt": "# nxt\n"}, _fa,
             {"prev": _epoch("2026-10-01T12:00:00Z"), "nxt": _epoch("2026-10-01T12:00:00Z")})}
          ["nxt"]), (0, "keep-banner"))

    # ── review round 2 (Codex): the ALLOW-LIST ─────────────────────────────────────────────
    def _stale_read(f):
        f.bash(f"{BP} bbs a", _arm_out("bbs", 1))
        f.bash("cat /tmp/old-sentinel; cat .claude/executing-plan >/dev/null",
               "plan: .claude/plans/r8-fold.md\n")
        f.bash(f"{BP} p6 a", _arm_out("p6", 1))
    case("⛔ Codex r2-1: a READ is never a checkpoint — stale output cannot reset the replay",
         world(_stale_read)[0]["p6"], "bbs")

    def _subprocess_arm(f):
        f.bash(f"{BP} bbs a", _arm_out("bbs", 1))
        f.bash("python3 - <<'PY'\nimport subprocess\nsubprocess.run(['python3', "
               "'scripts/begin-plan.py', 'round-6-scoped', 'a'])\nPY",
               "armed: .claude/executing-plan -> .claude/plans/round-6-scoped.md (1 steps)")
        f.bash(f"{BP} p6 a", _arm_out("p6", 1))
    case("⛔ Codex r2-2: code run by an interpreter may arm anything — the next arm gets no marker",
         world(_subprocess_arm)[0]["p6"], None)

    def _write_then_arm(f):
        f.bash(f"{BP} bbs a", _arm_out("bbs", 1))
        f.bash("python3 - <<'PY'\nfrom pathlib import Path\nPath('.claude/executing-plan')"
               f".unlink()\nPY\n{BP} p6 a", _arm_out("p6", 1))
    _wa = world(_write_then_arm)[1]["p6"]
    case("⛔ Codex r2-3: an opaque op poisons the checkout BEFORE an arm in the same command",
         (_wa["parent"], "unknown" in _wa["why"]), (None, True))

    # Each allow-list member keeps the state KNOWN (the arm after it gets `one`); each opaque
    # class makes it UNKNOWN (no marker). One literal command per member and per class.
    def _between(cmd, out=""):
        def b(f):
            f.bash(f"{BP} one a", _arm_out("one", 1))
            f.bash(cmd, out)
            f.bash(f"{BP} two a", _arm_out("two", 1))
        return b
    for _cmd in ("git log --oneline -3", "git show HEAD --stat", "git diff --stat",
                 "git status --short", "git rev-parse HEAD", "git branch --show-current",
                 "git ls-remote origin", "git fetch -q origin", "ls -la .claude/plans",
                 "cat .claude/plans/one.md", "head -3 docs/x.md", "tail -2 docs/x.md",
                 "grep -n plan docs/x.md", "wc -l docs/x.md", "sed -n 1,3p docs/x.md",
                 "awk '{print $1}' docs/x.md", "echo hi", "printf 'x\\n'", "date '+%H:%M'",
                 "cd docs && ls", "cat docs/x.md > /dev/null 2>&1", "W=/w/repo; ls $W",
                 "echo done > /tmp/note.txt", "sed -i '' s/a/b/ docs/x.md",
                 # ⟳ round 3 (the coordinator's line: REVIEWED repository code vs AD-HOC code)
                 "python3 scripts/recall-llm.py --arm 2>&1 | tail -5",
                 "python3 /w/repo/scripts/gen-work-lines.py --out /tmp/w.html",
                 "/usr/local/bin/python3.12 scripts/check-docs.py",
                 "cut -d: -f1 docs/x.md", "sort docs/x.md | uniq -c", "tr a b < docs/x.md",
                 "jq . docs/x.json", "column -t docs/x.md", "sleep 1", "pgrep -f x",
                 "pkill -f x", "gh pr list", "true", "false", "test -f docs/x.md",
                 "[ -f docs/x.md ]", "diff docs/a docs/b", "comm docs/a docs/b",
                 "basename docs/x.md", "dirname docs/x.md", "realpath docs", "stat docs/x.md",
                 "xxd docs/x.md", "od -c docs/x.md", "file docs/x.md", "which python3",
                 "type ls", "sed -E 's/a/b/' .claude/executing-plan", "git checkout -b x",
                 "git commit -qm m", "git push -u origin x", "git reset --hard HEAD",
                 "git -C /w/repo merge --ff-only x", "echo $(git rev-parse HEAD)",
                 "echo `date`", "exit 0", "export X=1", "X=1 git status",
                 "# a note to self\nls docs", "export D=/tmp/d && echo x > \"$D/log\"",
                 "export X", "export -p",
                 # ⟳ round 4: INLINE code is INSPECTED (the threat model is accident, not
                 # adversary, and the code's full text is in the transcript)
                 "python3 - <<'PY'\nimport re, json\nprint(re.compile('x').pattern)\nPY",
                 "python3 -c 'print(1)'", "python3 -u -c 'import sys; print(sys.argv)'",
                 "python3 scripts/recall-llm.py <<'EOF'\nx\nEOF",
                 "python3 - <<'PY'\nopen('/tmp/out.txt', 'w').write('x')\nPY",
                 "python3 - <<'PY'\nfrom pathlib import Path\nprint(Path('docs').read_text())\nPY",
                 "echo $(python3 -c 'print(2)')", "python3 -c 'from ast import literal_eval'",
                 "pwd", "ps aux", "mktemp -d", "mktemp /tmp/x.XXXX",
                 "find docs -name '*.md'", "timeout 60 git status",
                 "timeout -s KILL 5 python3 scripts/check-docs.py",
                 # ⟳ round 5: ordinary analysis code is SAFE — it names no sentinel or plan tool
                 "python3 - <<'PY'\nfrom pathlib import Path\nPath('/tmp/scratch.json').write_text('{}')\nPY",
                 "python3 - <<'PY'\nimport importlib.util\nspec = importlib.util.spec_from_file_location('g', 'scripts/gen-work-lines.py')\nPY",
                 "python3 - <<'PY'\nimport subprocess\nprint(subprocess.run(['git', 'log', '-1'], capture_output=True).stdout)\nPY",
                 "python3 -c 'import os; os.system(\"git status\")'",
                 "python3 scripts/recall-llm.py <<'EOF'\nimport shutil\nEOF",
                 "python3 -c 'import os; os.popen(\"ls\")'", "python3 -c 'exec(\"1\")'",
                 "python3 -c 'eval(\"1\")'", "python3 -c 'import importlib'",
                 "python3 - <<'PY'\nf = 'x'\nopen(f, 'w').write('y')\nPY",
                 "python3 - <<'PY'\nfrom pathlib import Path\nPath('a').rename('b')\nPY",
                 "timeout 60 python3 -c 'import subprocess'"):
        case(f"allow-listed, or reaching no sentinel, keeps the state known: "
             f"{_cmd.replace(chr(10), ' ⏎ ')[:100]}",
             world(_between(_cmd))[0]["two"], "one")
    for _cmd in ("python3 - <<'PY'\nimport os\nos.remove('.claude/x')\nPY", "python3 scripts/other.py",
                 "node x.js",
                 "bash run.sh", "sh -c 'true'", "eval x", "source env.sh", "xargs echo < f",
                 "awk 'BEGIN{system(\"true\")}'", "echo x >> .claude/executing-plan",
                 # ⟳ round 3: AD-HOC code stays opaque, wherever it hides
                 "python3 /tmp/steps.py",
                 "python3 /tmp/recall-llm.py",
                 "python3 scripts/untracked-adhoc.py",
                 
                 "python3 scripts/recall-llm.py <<'EOF'\nprint('.claude')\nEOF",
                 "echo $(python3 -c 'print(\".claude\")')",
                 "python3 -m pytest", "git clean -fdx", "git stash -u",
                 # ⟳ round 5: the premise is that an ACCIDENT names the sentinel, a plan tool or
                 # a whole-tree delete — these name one, so they stay opaque
                 "python3 - <<'PY'\nfrom pathlib import Path\nprint(list(Path('.claude/plans').glob('*')))\nPY",
                 "python3 - <<'PY'\nimport shutil\nshutil.rmtree('build')\nPY",
                 "timeout 60 python3 -c 'print(\"executing-plan\")'",
                 "echo `node x.js`", ". env.sh",
                 "zsh x.sh", "sort -o .claude/executing-plan docs/x.md",
                 "uniq docs/x.md .claude/executing-plan", "$P scripts/check-docs.py",
                 # ⟳ round 4: each INLINE token class, and the shapes that stay opaque
                 "python3 - <<'PY'\nprint(open('.claude/executing-plan').read())\nPY",
                 "python3 - <<'PY'\nprint('executing-plan')\nPY",
                 "python3 -c 'print(\"begin-plan\")'", "python3 -c 'x=\"check-plan-progress\"'",
                 
                 
                 
                 
                 
                 
                 
                 
                 
                 
                 
                 
                 
                 
                 "python3 - <<'PY'\nprint(1)\n", "python3 -c \"$CODE\"", "python3",
                 "find docs -delete", "find . -exec rm {} ;", "find . -execdir true ;",
                 "find . -ok true ;", "find . -fprint /tmp/x", "mktemp .claude/executing-plan",
                 "timeout 5 node x.js",
                 "printf 'p\\n' > /w/repo/.claude/executing-plan",
                 "sed -i '' s/a/b/ .claude/executing-plan", "tee .claude/executing-plan < f",
                 "mv .claude/executing-plan /tmp/x", "cp /tmp/x .claude/executing-plan",
                 "rm -f .claude/plans/one.md", "rm -rf .claude", "cd \"$NOPE\" && rm -f x"):
        case(f"an opaque op makes the checkout UNKNOWN: {_cmd.replace(chr(10), ' ⏎ ')[:100]}",
             world(_between(_cmd))[0]["two"], None)
    case("⛔ the SECOND heredoc's body is the one its command is fed",
         world(_between("cat <<'A'\nx\nA\npython3 - <<'B'\nprint('.claude')\nB"))[0]["two"],
         None)
    case("⭐ `rm -f` of the sentinel ALONE is a known removal: the next arm starts a line",
         world(_between("rm -f .claude/executing-plan"))[0]["two"], STARTED)
    case("⛔ ...but not beside another opaque op — then the whole command is UNKNOWN",
         world(_between("rm -f .claude/executing-plan; python3 x.py"))[0]["two"], None)
    case("a reachable checkout is poisoned; ANOTHER checkout's sentinel write leaves this one known",
         world(_between("echo x >> /w/other/.claude/executing-plan"))[0]["two"], "one")

    # ── review round 3 (Claude): background commands, hookless sessions, real shapes ──────
    BG_OUT = "Command running in background with ID: bx1. Output is being written to: /tmp/x"

    def _bg_window(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("for g in a b; do python3 scripts/$g.py; done", BG_OUT, bg=True)
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
        f.task_done("bx1")
        f.bash(f"{BP} --status", ".claude/plans/two.md: 0/1 steps ticked, 1 remaining")
        f.bash(f"{BP} three a", _arm_out("three", 1))
    _bw = world(_bg_window)[0]
    case("⛔ M1: a checkpoint INSIDE a background command's run does not resolve it; one after "
         "its completion record does", (_bw["two"], _bw["three"]), (None, "two"))

    def _bg_stopped(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("python3 -c 'print(\".claude\")'", BG_OUT, bg=True)
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
        f.tool_stop("bx1")
        f.bash(f"{BP} --status", ".claude/plans/two.md: 0/1 steps ticked, 1 remaining")
        f.bash(f"{BP} three a", _arm_out("three", 1))
    _bs = world(_bg_stopped)[0]
    case("...and a TaskStop ends the window like a completion record",
         (_bs["two"], _bs["three"]), (None, "two"))

    def _shell_bg(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("python3 -c 'print(\".claude\")' &", "")
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ M1: a shell `&` has no end record — unknown until the session's last event",
         world(_shell_bg)[0]["two"], None)

    def _fg_other_stream(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("python3 -c 'print(\".claude\")'", "", run_s=100, stream="sess-bbbb2222")
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ M1: another session's checkpoint during a long FOREGROUND opaque command does not "
         "resolve it", world(_fg_other_stream)[0]["two"], None)

    def _amp_scope(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("kill 1; (nohup python3 scripts/check-docs.py > /tmp/l 2>&1 &)", "")
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("a shell `&` leaves only ITS pipeline running: the foreground op before it ends with "
         "the command", world(_amp_scope)[0]["two"], STARTED)

    def _parallel_sibling(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("python3 -c 'print(\".claude\")'", "", run_s=100)
        f.bash(f"{BP} --status", NONE_OUT)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ a PARALLEL sibling call in the same session, started before the opaque one returned, "
         "is inside its window", world(_parallel_sibling)[0]["two"], None)

    def _attachment_evidence(f):
        f.hook_note()
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1, "one"))
        f.say("done")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("...and a hook ATTACHMENT (any hook) is evidence the session runs the Stop hook",
         world(_attachment_evidence)[0]["two"], STARTED)

    def _hookless(evidence):
        def b(f):
            if evidence:
                f.stop()               # a Stop-hook record: this session runs the project's hooks
            f.bash(f"{BP} one a", _arm_out("one", 1))
            f.bash(f"{BP} --tick", _tick_out(1, 1, "one"))
            f.say("done")              # an end_turn
            f.bash(f"{BP} two a", _arm_out("two", 1))
        return b
    case("⛔ L1: a turn end in a session with NO hook evidence clears nothing",
         world(_hookless(False))[0]["two"], "one")
    case("...and one in a session that shows the Stop hook clears the fully-ticked plan",
         world(_hookless(True))[0]["two"], STARTED)

    def _nonblocking_clear(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"{BP} --tick | tail -0", "")
        f.clearing("one", 2, 2, kind="hook_non_blocking_error")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("I1: a Clearing message wrapped as `hook_non_blocking_error` is still a checkpoint",
         world(_nonblocking_clear)[0]["two"], STARTED)

    # ── the shell: finding the call and where it ran ─────────────────────────────────────────
    case("a relative script path resolves against ITS cwd",
         [c.root for c in find_calls(f"{BP} --finish", "/w/elsewhere")], ["/w/elsewhere"])
    case("--finish is a state change; --status reads only",
         (classify(["--finish"]), classify(["--banner"])), (("finish", None), ("ro", None)))
    case("a plain call is found, with its arguments, against the record's cwd",
         [(c.args, c.root) for c in find_calls(f'{BP} kid "a|b|c" 2>&1 | tail -3', "/w/repo")],
         [(["kid", "a|b|c"], "/w/repo")])
    case("⛔ `cd` earlier in the command moves the root — a worktree's sentinel is another file",
         [c.root for c in find_calls(f"cd /w/wt && {BP} --tick", "/w/repo")], ["/w/wt"])
    case("an absolute script path names its own checkout, whatever the cwd",
         [c.root for c in find_calls("python3 /w/other/scripts/begin-plan.py --tick", "/w/repo")],
         ["/w/other"])
    case("⛔ a heredoc BODY that names begin-plan.py is data, not a call",
         find_calls("python3 - <<'EOF'\nimport subprocess\nsubprocess.run(['scripts/begin-plan.py'"
                    ", '--tick'])\nscripts/begin-plan.py --finish\nEOF\necho done", "/w/repo"), [])
    case("a quoted mention (grep, echo) is not a call",
         find_calls("grep -n 'scripts/begin-plan.py --tick' docs/x.md", "/w/repo"), [])
    case("two calls in one command are found IN ORDER",
         [c.args for c in find_calls(f"{BP} --tick && {BP} --finish", "/w/repo")],
         [["--tick"], ["--finish"]])
    case("a variable from an earlier assignment resolves the cd",
         [c.root for c in find_calls(f"W=/w/wt2; cd \"$W\" && {BP} --tick", "/w/repo")],
         ["/w/wt2"])
    case("an unresolvable cd leaves the root UNKNOWN, not guessed",
         [c.root for c in find_calls(f"cd \"$UNSET\" && {BP} --tick", "/w/repo")], [None])
    case("dispatch follows begin-plan.main: --tick wins over a slug, --self-test is read-only",
         [classify(a)[0] for a in (["--tick"], ["s", "x"], ["--self-test"], ["--plan", "p.md"],
                                   ["--pause", "why"], ["--bogus"])],
         ["tick", "arm", "ro", "plan", "pause", "ro"])

    # ── the replay: the brief's cases ────────────────────────────────────────────────────────
    got, _ = world(lambda f: (f.bash(f"{BP} root a b", _arm_out("root", 2)),
                              f.bash(f"{BP} kid a", _arm_out("kid", 1))))
    case("⭐ arming while another plan is armed records the armed plan as the parent",
         got, {"root": STARTED, "kid": "root"})
    case("...and arming with NOTHING armed records `-` (a started line)", got["root"], STARTED)

    def _cleared(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1))
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⭐ a fully-ticked plan is CLEARED at the turn boundary, so the next arm is `-`",
         world(_cleared)[0]["two"], STARTED)

    def _no_boundary(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1))
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("...ADJACENT: fully ticked but no turn has ended — it is still armed, so it IS the parent",
         world(_no_boundary)[0]["two"], "one")

    def _half(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"{BP} --tick", _tick_out(1, 2))
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("...and a boundary does NOT clear a plan with steps outstanding",
         world(_half)[0]["two"], "one")

    def _paused(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1))
        f.bash(f"{BP} --pause 'waiting on CI'", "paused: waiting on CI\nThe Stop guard will")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⭐ a PAUSED plan survives the boundary and stays the parent",
         world(_paused)[0]["two"], "one")

    def _resumed(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --pause w", "paused: w\n")
        f.bash(f"{BP} --resume", "resumed: the Stop guard is armed again")
        f.bash(f"{BP} --tick", _tick_out(1, 1))
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("...and after --resume the boundary clears it again", world(_resumed)[0]["two"], STARTED)

    def _finished(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        f.bash(f"{BP} --finish", "cleared .claude/executing-plan")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⭐ --finish clears the sentinel: the next arm starts a line",
         world(_finished)[0]["two"], STARTED)

    def _rearm(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} two a", _arm_out("two", 1))
        f.bash(f"{BP} one a b", _arm_out("one", 2))
    case("⭐ re-arming an existing plan KEEPS its first parent", world(_rearm)[0],
         {"one": STARTED, "two": "one"})

    def _refused(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --finish", "refusing: something", is_error=True)
        f.bash(f"{BP} 'Bad Slug' a", "refusing: slug must be a-z0-9-", is_error=True)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⭐ a FAILED begin-plan call is ignored: the refused --finish cleared nothing",
         world(_refused)[0], {"one": STARTED, "two": "one"})

    def _rejected(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --finish", "The user doesn't want to proceed with this tool use.",
               is_error=True)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("...and a call the user REJECTED never ran", world(_rejected)[0]["two"], "one")

    def _unread(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --finish 2>&1 | grep nothing", "")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ a state change whose output was NOT READABLE leaves no marker downstream",
         world(_unread)[0]["two"], None)

    def _tailed(f):
        f.bash(f"{BP} one a b", _arm_out("one", 2))
        # `tail` kept only the LAST line: the new plan's state line. The tick and the --finish
        # printed nothing that survived — measured, this is how most new lines were started.
        f.bash(f"{BP} --tick && {BP} --finish && {BP} two a b c | tail -1",
               "(plan: .claude/plans/two.md — 0/3 ticked. `scripts/begin-plan.py --tick` when …)")
    case("⭐ `--finish && begin-plan next | tail`: the bare state line is the ARM's, and the "
         "finish it got past cleared the sentinel", world(_tailed)[0]["two"], STARTED)

    def _missing(f):
        f.bash(f"{BP} one a", None)
        f.bash(f"{BP} two a", _arm_out("two", 1))
    _m = world(_missing)[0]
    case("⛔ a call whose RESULT IS MISSING: neither it nor the next plan gets a marker",
         (_m["one"], _m["two"]), (None, None))

    def _unread_tick(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick | head -0", "")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ an unread tick that MAY have been the last makes the boundary's effect unknown",
         world(_unread_tick)[0]["two"], None)

    def _unread_tick_early(f):
        f.bash(f"{BP} one a b c", _arm_out("one", 3))
        f.bash(f"{BP} --tick | head -0", "")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("...but one that CANNOT have been the last leaves the plan armed",
         world(_unread_tick_early)[0]["two"], "one")

    def _worktree(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"cd /w/wt && {BP} --finish", "cleared .claude/executing-plan")
        f.bash(f"cd /w/wt && {BP} side a", _arm_out("side", 1))
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ calls in ANOTHER checkout touch another sentinel and are not replayed here",
         world(_worktree)[0], {"one": STARTED, "two": "one"})

    def _nonplan(f):
        f.bash(f"{BP} --plan docs/plans/design.md",
               "armed: .claude/executing-plan -> docs/plans/design.md\n\n(plan: x — 0/3 ticked")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    _np = world(_nonplan)[1]["two"]
    case("⛔ a sentinel naming a non-plan file records NO parent, and says why",
         (_np["parent"], "not a plan file" in _np["why"]), (None, True))

    def _handrm(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash("printf 'plan: .claude/plans/x.md\\n' > .claude/executing-plan", "")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("⛔ a hand edit of the sentinel makes its state unknown", world(_handrm)[0]["two"], None)

    def _subagent_stop(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --tick", _tick_out(1, 1))
        f.stop(stream="sess-aaaa1111/subagents/agent-x")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("a SUBAGENT's turn end runs no Stop hook, so it clears nothing",
         world(_subagent_stop)[0]["two"], "one")

    def _overlap(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} two a", _arm_out("two", 1), run_s=30)
        f.bash(f"{BP} --finish", "cleared .claude/executing-plan", stream="sess-bbbb2222")
    _ov = world(_overlap)[1]["two"]
    case("⛔ another session changing state WHILE the arm ran: no marker, and the reason says so",
         (_ov["parent"], "another session" in _ov["why"]), (None, True))

    def _plan_resync(f):
        f.bash(f"{BP} one a", _arm_out("one", 1))
        f.bash(f"{BP} --finish", "cleared .claude/executing-plan")
        f.bash(f"{BP} --plan .claude/plans/one.md",
               "armed: .claude/executing-plan -> .claude/plans/one.md\n\n✅ every step in "
               ".claude/plans/one.md is ticked.")
        f.stop()
        f.bash(f"{BP} two a", _arm_out("two", 1))
    case("--plan on a fully-ticked plan is cleared at the boundary like any other",
         world(_plan_resync)[0]["two"], STARTED)

    # ── the inputs are CARRIED: two distinct transcript dirs, roots and row sets ────────────
    _fx_a, _fx_b = _Fx("/w/repo"), _Fx("/w/repo")
    _fx_a.bash(f"{BP} aa a", _arm_out("aa", 1))
    _fx_b.bash(f"{BP} bb a", _arm_out("bb", 1))
    _fx_b.bash(f"cd /w/other && {BP} cc a", _arm_out("cc", 1))
    with tempfile.TemporaryDirectory() as d:
        _ev = {k: read_transcripts(f.write(Path(d) / k)) for k, f in (("a", _fx_a), ("b", _fx_b))}
        _evo = _ev["b"]
    case("read_transcripts reads ITS directory: two dirs, two different call sets",
         [sorted(o.call.args[0] for e in _ev[k] if e.kind == "cmd" for o in e.data["ops"])
          for k in ("a", "b")],
         [["aa"], ["bb", "cc"]])
    case("replay replays against ITS root: the same events, another root, another answer",
         (sorted(replay(_ev["b"], "/w/repo")), sorted(replay(_evo, "/w/other"))),
         (["bb"], ["cc"]))
    case("render_table renders ITS rows: two row sets, two tallies",
         [render_table([{"slug": s_, "replay": "-", "banner": "", "verdict": v, "why": ""}
                        for s_, v in rows_]).splitlines()[-2] for rows_ in
          ([("a", "keep")], [("b", "keep"), ("c", "no-marker")])],
         ["totals: keep 1 (of 1 plans)", "totals: keep 1, no-marker 1 (of 2 plans)"])

    # ── banners, provenance, and the decision per plan ───────────────────────────────────────
    def _banner(frm):
        def b(f):
            f.bash(f"{BP} one a", _arm_out("one", 1))
            f.bash(f"{BP} other a", _arm_out("other", 1))
            f.bash(f"{BP} --finish", "cleared .claude/executing-plan")
            f.bash(f"{BP} one a", _arm_out("one", 1))
            f.prompt()
            f.say(f"## ▶ STEP 1\n> **Thread:** ⤳ SWITCHED from `{frm}` (done) → `two` · 0 of 1")
            f.bash(f"{BP} two a", _arm_out("two", 1))
        return b
    _plans = {s: f"# {s}\n\n- [ ] a\n" for s in ("one", "other", "two")}
    _births = {s: _dt.datetime(2026, 10, 1, 13, tzinfo=_dt.timezone.utc).timestamp()
               for s in _plans}
    _agree = {r["slug"]: r for r in decide(_plans, world(_banner("one"))[1], _births)}
    case("⭐ a banner that AGREES with the replay keeps the link",
         (_agree["two"]["verdict"], _agree["two"]["banner"]), ("keep", "one"))
    _dis = {r["slug"]: r for r in decide(_plans, world(_banner("other"))[1], _births)}
    case("⛔ a banner that DISAGREES: no marker, and the row names both witnesses",
         (_dis["two"]["verdict"], _dis["two"]["marker"], "other" in _dis["two"]["why"],
          "says one" in _dis["two"]["why"]), ("no-marker", None, True, True))
    case("...and the disagreement is LISTED under the table",
         "two: a banner said other" in render_table(list(_dis.values())), True)
    _seen_b = world(_banner("one"))[1]

    # ── option A (owner, 2026-10-22): a banner LINKS a plan whose `-` only follows a clear ────
    def _after_clear(how, frm, *, first="prev"):
        def b(f):
            if first:
                f.bash(f"{BP} {first} a", _arm_out(first, 1))
                if how == "finish":
                    f.bash(f"{BP} --finish", "cleared .claude/executing-plan")
                else:
                    f.bash(f"{BP} --tick", _tick_out(1, 1, first))
                    f.stop()
            f.prompt()
            f.say(f"## ▶ STEP 1\n\n> **Thread:** ⤳ SWITCHED from `{frm}` (1/1 done) → `nxt` · 0 of 1")
            f.bash(f"{BP} nxt a", _arm_out("nxt", 1))
        return b
    _pl2 = {s: f"# {s}\n\n- [ ] a\n" for s in ("prev", "nxt", "elsewhere")}
    _bi2 = {s: _births["one"] for s in _pl2}
    _rows = {k: {r["slug"]: r for r in decide(_pl2, world(w)[1], _bi2)}["nxt"] for k, w in (
        ("finish", _after_clear("finish", "prev")), ("turn", _after_clear("turn", "prev")),
        ("other", _after_clear("finish", "elsewhere")),
        ("fresh", _after_clear("finish", "prev", first=None)))}
    case("⭐ just CLEARED by --finish + a banner naming exactly that plan: linked, sourced `banner`",
         (_rows["finish"]["verdict"], bool(re.fullmatch(
             r"<!-- parent: prev -->\n<!-- parent-source: banner sess-aaa "
             r"2026-10-01T12:\d\d:\d\d\.000Z -->", _rows["finish"]["marker"] or ""))),
         ("keep-banner", True))
    case("...and the same when the Stop hook's turn-end clear was what cleared it",
         (_rows["turn"]["verdict"], (_rows["turn"]["marker"] or "").split("\n")[0]),
         ("keep-banner", "<!-- parent: prev -->"))
    case("⛔ the banner's OWN session and time are the source — never the arm's",
         [r_["marker"].split("banner ")[1] if r_["marker"] else None for r_ in decide(
             {"nxt": "# nxt\n"},
             {"nxt": {"parent": "-", "cleared": "prev", "session": "armsess1-x",
                      "ts": "2026-10-01T12:00:00Z", "banners": ["prev"],
                      "banner_src": [{"frm": "prev", "session": "bansess9-y",
                                      "ts": "2026-10-01T11:59:00Z"}]}},
             {"nxt": _epoch("2026-10-01T12:00:00Z")})],
         ["bansess9 2026-10-01T11:59:00Z -->"])
    case("⛔ just cleared + a banner naming ANOTHER plan: no marker, and still listed",
         (_rows["other"]["verdict"], "a banner said elsewhere" in _rows["other"]["why"]),
         ("no-marker", True))
    case("⛔ nothing was cleared (a fresh start) + a banner: no marker — `-` was not a clear",
         _rows["fresh"]["verdict"], "no-marker")
    case("⛔ a banner never overrides a replay that found a parent ARMED at the time",
         {r["slug"]: r["verdict"] for r in decide(_plans, world(_banner("other"))[1],
                                                  _births)}["two"], "no-marker")
    case("a banner from ANOTHER turn is not about this arm",
         _seen_b["other"]["banners"], [])
    case("a banner naming PROSE, not a thread, is no witness",
         {r["slug"]: r["verdict"] for r in decide(_plans, world(_banner("session start"))[1],
                                                  _births)}["two"], "keep")
    case("⛔ ...but a SLUG naming no plan on disk still disagrees (a thread in another checkout)",
         {r["slug"]: r["verdict"] for r in decide(_plans, world(_banner("elsewhere-plan"))[1],
                                                  _births)}["two"], "no-marker")
    _k = _agree["two"]["marker"]
    case("⭐ the marker is labelled: parent line + `parent-source: transcript <8> <ISO>`",
         bool(re.fullmatch(r"<!-- parent: one -->\n<!-- parent-source: transcript sess-aaa "
                           r"2026-10-01T12:\d\d:\d\d\.000Z -->", _k or "")), True)
    _two_sessions = {r["slug"]: r["marker"] for r in decide(
        {"a1": "# a1\n", "b2": "# b2\n"},
        {"a1": {"parent": "-", "session": "11112222-x", "ts": "2026-10-01T12:00:00Z",
                "banners": []},
         "b2": {"parent": "zz", "session": "99998888-y", "ts": "2026-10-02T09:30:00Z",
                "banners": []}},
        {"a1": _epoch("2026-10-01T12:00:00Z"), "b2": _epoch("2026-10-02T09:30:00Z")})}
    case("...and the session, time and parent are CARRIED — two distinct inputs prove it",
         _two_sessions, {
             "a1": "<!-- parent: - -->\n<!-- parent-source: transcript 11112222 "
                   "2026-10-01T12:00:00Z -->",
             "b2": "<!-- parent: zz -->\n<!-- parent-source: transcript 99998888 "
                   "2026-10-02T09:30:00Z -->"})
    _marked = dict(_plans, two="# two\n\n<!-- parent: - -->\n- [ ] a\n")
    case("⛔ a plan that ALREADY has a marker is untouched, whatever the replay says",
         {r["slug"]: (r["verdict"], r["marker"]) for r in decide(_marked, _seen_b, _births)}["two"],
         ("untouched", None))
    case("a plan with no recorded arm gets no marker",
         decide({"ghost": "# ghost\n"}, {}, {"ghost": 0.0})[0]["verdict"], "no-marker")
    _early = dict(_births, two=_dt.datetime(2026, 9, 5, tzinfo=_dt.timezone.utc).timestamp())
    case("⛔ a file BORN before its first recorded arm: that arm was a re-arm, so no marker",
         {r["slug"]: r["verdict"] for r in decide(_plans, _seen_b, _early)}["two"], "no-marker")
    case("...and an unknown birth time is no marker too, never an assumption",
         {r["slug"]: r["verdict"] for r in decide(_plans, _seen_b, dict(_births, two=None))}["two"],
         "no-marker")
    case("...and with no title line, the marker opens the file",
         apply_marker("- [ ] b\n", "<!-- parent: q -->"), "<!-- parent: q -->\n\n- [ ] b\n")
    case("the marker goes on its own lines directly under the title",
         apply_marker("# t\n\n> intro\n- [ ] a\n", "<!-- parent: p -->\n<!-- parent-source: s -->"),
         "# t\n\n<!-- parent: p -->\n<!-- parent-source: s -->\n\n> intro\n- [ ] a\n")

    # ── run(): dry run vs --write, over a constructed world on disk ──────────────────────────
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "repo"
        pd = root / PLAN_REL
        pd.mkdir(parents=True)
        for s in ("one", "two", "live"):
            (pd / f"{s}.md").write_text(f"# {s}\n\n- [ ] a\n")
        (pd / "live.md").write_text("# live\n\n<!-- parent: - -->\n- [ ] a\n")
        os.utime(pd / "one.md", (1_700_000_000, 1_700_000_000))
        fx = _Fx(str(root))
        fx.bash(f"{BP} --status", NONE_OUT)
        fx.bash(f"{BP} one a", _arm_out("one", 1))
        fx.bash(f"{BP} two a", _arm_out("two", 1))
        fx.bash(f"{BP} live a", _arm_out("live", 1))
        tdir = fx.write(Path(d) / "t")
        births = {s: _dt.datetime(2026, 10, 1, 12, tzinfo=_dt.timezone.utc).timestamp()
                  for s in ("one", "two", "live")}
        before = {p.name: p.read_text() for p in pd.iterdir()}
        _ino_before = {p.name: p.stat().st_ino for p in pd.iterdir()}
        rc, rep = run(pd, tdir, str(root), False, births)
        case("⛔ the DRY RUN writes nothing", (rc, {p.name: p.read_text() for p in pd.iterdir()}
                                              == before, "DRY RUN" in rep), (0, True, True))
        rc, rep = run(pd, tdir, str(root), True, births)
        case("--write applies the `keep` rows, and only them",
             (rc, (pd / "two.md").read_text().split("\n")[2], (pd / "live.md").read_text()
              == before["live.md"], "wrote 2 plan file(s)" in rep),
             (0, "<!-- parent: one -->", True, True))
        case("⛔ --write keeps the file's mtime: the page dates plans by it",
             int((pd / "one.md").stat().st_mtime), 1_700_000_000)
        case("⛔ F5: --write REPLACES the file (a new inode, via os.replace) and leaves no temp file",
             ((pd / "two.md").stat().st_ino != _ino_before["two.md"],
              [x.name for x in pd.iterdir() if "backfill-tmp" in x.name]), (True, []))
        (pd / "three.md").write_text("# three\n\n- [x] a\n")
        (root / ".claude" / "last-plan").write_text("plan: .claude/plans/three.md\nsha256: x\n")
        fx.bash(f"{BP} three a", _arm_out("three", 1))
        tdir = fx.write(Path(d) / "t")
        births["three"] = births["one"]
        rc3, rep3 = run(pd, tdir, str(root), True, births)
        case("⛔ --write SKIPS the plan .claude/last-plan fingerprints, and says why",
             ((pd / "three.md").read_text(), "skipped three" in rep3),
             ("# three\n\n- [x] a\n", True))
        rc2, _ = run(pd, tdir, str(root), True, births)
        case("a second --write is a no-op: reconstructed plans now have a marker",
             ((pd / "two.md").read_text().count("parent-source"), rc2), (1, 0))
        _other = run(pd, tdir, "/w/not-this-root", False, {})
        case("run() replays against ITS root and reads ITS births: another root sees no arm",
             [ln for ln in _other[1].splitlines() if ln.startswith("totals:")],
             ["totals: no-marker 1, untouched 3 (of 4 plans)"])
        case("a missing plans directory is CANNOT RUN (2)",
             run(Path(d) / "nope", tdir, str(root), False, births)[0], 2)
        case("a missing transcripts directory is CANNOT RUN (2)",
             run(pd, Path(d) / "no-t", str(root), False, births)[0], 2)

    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "repo"
        pd = root / PLAN_REL
        pd.mkdir(parents=True)
        for s_ in ("prev", "nxt"):
            (pd / f"{s_}.md").write_text(f"# {s_}\n\n- [ ] a\n")
        fx = _Fx(str(root))
        fx.bash(f"{BP} --status", NONE_OUT)
        _after_clear("finish", "prev")(fx)
        bi = {s_: _births["one"] for s_ in ("prev", "nxt")}
        run(pd, fx.write(Path(d) / "t"), str(root), True, bi)
        case("--write applies a `keep-banner` row too, labelled `banner`",
             (pd / "nxt.md").read_text().split("\n")[2:4][1].startswith(
                 "<!-- parent-source: banner sess-aaa "), True)

    # ── the ground-truth check is CANNOT RUN without its subject, never a pass ───────────────
    with tempfile.TemporaryDirectory() as d:
        case("⛔ --ground-truth with no transcripts is CANNOT RUN (2)",
             ground_truth(Path(d) / "absent", "/w/repo")[0], 2)
        (Path(d) / "empty.jsonl").write_text("")
        case("⛔ ...and with transcripts that hold no begin-plan call, also CANNOT RUN (2)",
             ground_truth(Path(d), "/w/repo")[0], 2)
        fx = _Fx("/w/repo")
        fx.bash(f"{BP} --status", NONE_OUT)
        fx.bash(f"{BP} {GROUND_TRUTH[1]} a", _arm_out(GROUND_TRUTH[1], 1))
        fx.bash(f"{BP} {GROUND_TRUTH[0]} a", _arm_out(GROUND_TRUTH[0], 1))
        case("--ground-truth passes when the replay reproduces the link",
             ground_truth(fx.write(Path(d) / "gt"), "/w/repo")[0], 0)
        fx2 = _Fx("/w/repo")
        fx2.bash(f"{BP} --status", NONE_OUT)
        fx2.bash(f"{BP} {GROUND_TRUTH[0]} a", _arm_out(GROUND_TRUTH[0], 1))
        case("--ground-truth replays ITS root: the same transcripts, another root, CANNOT RUN",
             ground_truth(Path(d) / "gt", "/w/not-the-root")[0], 2)
        case("...and FAILS (1) when it does not",
             ground_truth(fx2.write(Path(d) / "gt2"), "/w/repo")[0], 1)

    TRACKED_SCRIPTS = _saved_tracked
    print(f"\n{cases - failures}/{cases} self-test cases passed")
    drift = _count_drift(cases)
    if drift:
        print(drift)
        return 1
    return 1 if failures else 0


def _count_drift(actual: int) -> str | None:
    m = re.search(r"--self-test\s+#\s*(\d+) cases", __doc__ or "")
    if not m:
        return "CANNOT RUN — the docstring no longer declares a case count."
    if int(m.group(1)) != actual:
        return f"[DRIFT] the docstring declares {m.group(1)} cases; the suite ran {actual}"
    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

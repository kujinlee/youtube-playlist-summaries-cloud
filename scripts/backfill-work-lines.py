#!/usr/bin/env python3
"""Rebuild the work-line links that predate the `parent:` field — by REPLAYING the transcripts.

    python3 scripts/backfill-work-lines.py                  # DRY RUN: print the table, write nothing
    python3 scripts/backfill-work-lines.py --write          # apply the `keep`/`keep-banner` rows
    python3 scripts/backfill-work-lines.py --plans DIR      # read (and with --write, change) DIR
    python3 scripts/backfill-work-lines.py --ground-truth   # the replay must reproduce a live link
    python3 scripts/backfill-work-lines.py --self-test  # 85 cases

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

⭐ CHECKPOINTS (review round 1, Claude F4 — the structural fix). The transcripts also hold direct
OBSERVATIONS of the sentinel: a `cat`/`sed -n` of it, `--status` (either script), the state line
of an arm or tick, `--finish`'s reply, and the Stop hook's own `✅ … Clearing` message. At each the
replayed state is compared with the observation. A disagreement RESETS the replay to what was
observed and leaves NO MARKER on every plan first armed since the last checkpoint ("replay
contradicted by an observation"). Before the first checkpoint the state is UNKNOWN, not "nothing
armed" (F3) — the transcripts begin mid-history.

⛔ ALSO FROM ROUND 1. Every call in a command is found, in order, including inside `for … done`; a
call in a loop ran an unknown number of times, so the state is UNKNOWN until the next checkpoint
(F1). A sentinel write in the same command as a call is applied IN COMMAND ORDER — `rm` is a known
"nothing armed" (but no clear a banner may cite), any other edit is UNKNOWN; a Python heredoc that
writes a sentinel cannot be ordered and makes every checkout UNKNOWN (F2). Each checkout's sentinel
is replayed SEPARATELY, and output from a command whose calls span two checkouts is attributed to
neither (Codex 1). A banner counts only as the assistant's live text in the banner block under a
`## ▶` heading — never fenced, block-quoted or in a tool result (Codex 3). `--write` is atomic.

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
_PREFILTER = ("begin-plan", "SWITCHED", '"end_turn"', "stop_hook_summary", "executing-plan",
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


def heredoc_bodies(cmd: str) -> str:
    """Every heredoc BODY, joined — what `strip_heredocs` removes. Data to the shell, but a Python
    body can still WRITE the sentinel, and where it does the order is not knowable."""
    lines, out, i = cmd.split("\n"), [], 0
    while i < len(lines):
        ln = lines[i]
        i += 1
        for m in _HEREDOC.finditer(ln):
            while i < len(lines) and lines[i].strip() != m.group(2):
                out.append(lines[i])
                i += 1
            i += 1
    return "\n".join(out)


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
                word.append(cmd[i]); i += 1
            has_word = True; i += 1
            continue
        if c == "$" and i + 1 < n and cmd[i + 1] == "(":
            depth, j = 0, i
            while j < n:
                if cmd[j] == "(":
                    depth += 1
                elif cmd[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            word.append(cmd[i:j + 1]); has_word = True; i = j + 1
            continue
        if c in " \t":
            flush(); i += 1
            continue
        if c in "<>" or (c == "&" and i + 1 < n and cmd[i + 1] == ">"):
            # a redirection: an all-digit word before it is its fd, not an argument
            if has_word and "".join(word).isdigit():
                word, has_word = [], False
            flush()
            i += 1
            while i < n and cmd[i] in "<>":
                i += 1
            if i < n and cmd[i] == "&" and c != "&":
                i += 1
                while i < n and (cmd[i].isdigit() or cmd[i] == "-"):
                    i += 1
                continue
            while i < n and cmd[i] in " \t":
                i += 1
            target, i = _read_word(cmd, i)
            toks.append(("redir", target))
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
_PLAN_FILE = re.compile(r"^(.*)/\.claude/plans/([a-z0-9][a-z0-9-]*)\.md$")


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
    """One step of a Bash command, in COMMAND ORDER. ⟳ r1 Claude F2 / Codex 2: a write and a call
    in one command were examined by an `if`/`elif`, so the write was never seen at all."""
    kind: str             # 'call' | 'write' | 'read' | 'planwrite'
    root: str | None
    call: Call | None = None
    effect: str = ""      # write: 'rm' (removed — nothing armed) | 'edit' (content unknown)
    slug: str = ""        # planwrite


def _target(word: str, env: dict[str, str], cur: str | None) -> tuple | None:
    """('sentinel', root) / ('plan', root, slug) when `word` names one of those files; root None
    when the path cannot be resolved. None when it names neither."""
    if not (word.endswith(SENTINEL_REL) or ".claude/plans/" in word):
        return None
    p = expand(word, env)
    full = (None if p is None or (cur is None and not os.path.isabs(p))
            else os.path.normpath(os.path.join(cur or "/", p)))
    if word.endswith(SENTINEL_REL) and (full is None or full.endswith(_SENT_TAIL)):
        return ("sentinel", None if full is None else full[:-len(_SENT_TAIL)])
    m = _PLAN_FILE.match(full or "")
    return ("plan", m.group(1), m.group(2)) if m else None


def parse_command(cmd: str, cwd: str) -> list[Op]:
    """Every call, sentinel write, sentinel read and plan-file write a Bash command makes, IN
    ORDER, each against the checkout it resolves to (`begin-plan.ROOT` is the script's own
    checkout; a path is resolved against the record's cwd as changed by `cd` in the command)."""
    toks = tokenize(strip_heredocs(cmd))
    ops: list[Op] = []
    env: dict[str, str] = {}
    cur: str | None = cwd
    depth = 0
    words: list[str] = []
    redirs: list[str] = []

    def finish(ws: list[str], rs: list[str]) -> None:
        nonlocal cur, depth
        while ws and (ws[0] in _RESERVED or ws[0] in _LOOP_OPEN):
            w = ws.pop(0)
            if w in _LOOP_OPEN:
                depth += 1
                if w in ("for", "select"):
                    ws = []            # the loop's header, not a command
            elif w == "done":
                depth = max(0, depth - 1)
        while ws and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", ws[0]):
            k, v = ws[0].split("=", 1)
            env[k] = expand(v, env) or v
            ws = ws[1:]
        for r in rs:
            t = _target(r, env, cur)
            if t and t[0] == "sentinel":
                ops.append(Op("write", t[1], effect="edit"))
            elif t:
                ops.append(Op("planwrite", t[1], slug=t[2]))
        if not ws:
            return
        if ws[0] == "cd" and len(ws) >= 2:
            d = expand(ws[1], env)
            cur = None if d is None or cur is None else os.path.normpath(os.path.join(cur, d))
            return
        for k in range(min(3, len(ws))):
            script = _SCRIPTS.get(os.path.basename(ws[k]))
            if script is None:
                continue
            if not all(_INTERP.match(w) or w.startswith("$") or w == "env" for w in ws[:k]):
                return
            p = expand(ws[k], env)
            root = (None if p is None or (cur is None and not os.path.isabs(p)) else
                    os.path.dirname(os.path.dirname(os.path.normpath(
                        p if os.path.isabs(p) else os.path.join(cur, p)))))
            ops.append(Op("call", root, call=Call(ws[k + 1:], root, depth > 0, script)))
            return
        name = os.path.basename(ws[0])
        args = ws[1:]
        targets = [(i, _target(a, env, cur)) for i, a in enumerate(args)]
        targets = [(i, t) for i, t in targets if t]
        for i, t in targets:
            last = i == len(args) - 1
            if name in ("rm", "unlink") or (name == "mv" and not last):
                kind = "rm"
            elif name in ("truncate", "tee") or (name in ("mv", "cp") and last) or (
                    name == "sed" and any(a.startswith("-i") for a in args)):
                kind = "edit"
            elif name in ("cat", "head", "tail", "grep", "sed", "awk", "nl"):
                kind = "read"
            else:
                continue
            if t[0] == "plan":
                if kind != "read":
                    ops.append(Op("planwrite", t[1], slug=t[2]))
            elif kind == "read":
                ops.append(Op("read", t[1]))
            else:
                ops.append(Op("write", t[1], effect=kind))

    for kind, text in toks + [("op", ";")]:
        if kind == "w":
            words.append(text)
        elif kind == "redir":
            redirs.append(text)
        else:
            finish(words, redirs)
            words, redirs = [], []
    return ops


def find_calls(cmd: str, cwd: str) -> list[Call]:
    """The `begin-plan.py` calls a command makes, in order (a view of `parse_command`)."""
    return [o.call for o in parse_command(cmd, cwd)
            if o.kind == "call" and o.call.script == "begin-plan"]


_OPAQUE_WRITE = re.compile(r"executing-plan[\"']?\)?\s*\.\s*(?:write_text|unlink|open)|"
                           r"executing-plan[\"'][^\n]*[\"'][wa]\+?[\"']")


def opaque_sentinel_write(cmd: str) -> bool:
    """A heredoc body (a Python script) that writes or removes a sentinel. Its target and its
    order against the shell's own steps cannot be resolved."""
    return bool(_OPAQUE_WRITE.search(heredoc_bodies(cmd)))


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
        with open(f, encoding="utf-8", errors="replace") as fh:
            for no, line in enumerate(fh):
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
                    continue
                if typ == "user" and top and not r.get("isMeta"):
                    content = msg.get("content")
                    if isinstance(content, str) or (isinstance(content, list) and all(
                            isinstance(c, dict) and c.get("type") == "text" for c in content)):
                        events.append(Event(kind="prompt", **base))
                    continue
                if typ == "system" and r.get("subtype") == "stop_hook_summary" and top:
                    events.append(Event(kind="stop", data={"cwd": cwd}, **base))
                    continue
                if typ == "attachment" and top:
                    a = r.get("attachment") or {}
                    m = _CLEARING.search(str(a.get("content") or a.get("stdout") or ""))
                    if a.get("hookEvent") == "Stop" and m:
                        events.append(Event(kind="clearing", data={
                            "cwd": cwd, "rel": m.group(1)}, **base))
                    continue
                if typ != "assistant":
                    continue
                if top and msg.get("stop_reason") == "end_turn":
                    events.append(Event(kind="stop", data={"cwd": cwd}, **base))
                for c in msg.get("content") or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text" and "SWITCHED" in c.get("text", ""):
                        for frm, to in live_banners(c["text"]):
                            events.append(Event(kind="banner", data={"frm": frm, "to": to},
                                                **base))
                    if c.get("type") != "tool_use":
                        continue
                    inp = c.get("input") or {}
                    if c.get("name") == "Bash":
                        cmd = inp.get("command") or ""
                        if not any(k in cmd for k in ("begin-plan", "check-plan-progress",
                                                      "executing-plan", ".claude/plans/")):
                            continue
                        ops = parse_command(cmd, cwd)
                        opaque = opaque_sentinel_write(cmd)
                        if ops or opaque:
                            ev = Event(kind="cmd", data={"ops": ops, "opaque": opaque,
                                                         "cmd": cmd}, **base)
                            events.append(ev)
                            pending[c.get("id", "")] = ev
                    elif c.get("name") in _WRITE_TOOLS:
                        p = os.path.normpath(inp.get("file_path") or inp.get("notebook_path")
                                             or "/")
                        t = _target(p, {}, "/")
                        if t:
                            events.append(Event(kind="tool", data={"target": t}, **base))
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


_PLAN_LINE = re.compile(r"^plan:\s*(\S+)\s*$", re.M)
_NO_FILE = re.compile(r"executing-plan[^\n]*No such file|No such file[^\n]*executing-plan")
_FALLBACK = re.compile(r"executing-plan[^\n|;&]*\|\|\s*echo\s+(['\"])(.+?)\1")


def read_observation(cmd: str, text: str | None) -> tuple | None:
    """What a READ of the sentinel printed: ('armed', rel, paused) / ('none',) / None (no clean
    reading). Exactly one `plan:` line, or the command's own `|| echo …` fallback / `No such
    file`, with no `plan:` line at all."""
    # ⛔ ONE sentinel named in the whole command. Measured 2026-10-22: a command reading BOTH the
    # main checkout's sentinel (inside `$(…)`, unparsed) and a worktree's printed the main one's
    # "No such file", which was read as the worktree's — a false disagreement.
    if text is None or "last-plan" in cmd or strip_heredocs(cmd).count("executing-plan") != 1:
        return None
    plans = _PLAN_LINE.findall(text)
    if len(plans) == 1:
        return ("armed", plans[0], bool(re.search(r"^paused:", text, re.M)))
    if plans:
        return None
    fb = _FALLBACK.search(cmd)
    if _NO_FILE.search(text) or (fb and fb.group(2) in text):
        return ("none",)
    return None


def replay(events: list[Event], root: str, stats: dict | None = None) -> dict[str, dict]:
    """`root`'s plans: slug -> {parent, why, session, ts, stream, banners, …}. `parent` None
    means NO MARKER. Every checkout's sentinel is replayed SEPARATELY (r1 Codex 1).

    ⭐ CHECKPOINTS (r1 Claude F4 — the structural fix). The transcripts hold direct OBSERVATIONS
    of the sentinel: a `cat` of it, `--status`, the state line of an arm or tick, `--finish`'s
    reply, and the Stop hook's own `Clearing` message. At each, the replayed state is compared
    with what was observed. A disagreement RESETS the replay to the observation and UNMARKS every
    plan first armed since the last checkpoint — those parents were derived from a state now known
    to be wrong. Before the first checkpoint the state is UNKNOWN (r1 Claude F3).
    """
    states: dict[str, object] = {}
    cleared: dict[str, str | None] = {}
    seen: dict[str, dict[str, dict]] = {}
    pending: dict[str, list[str]] = {}
    counts: dict = {"agree": 0, "disagree": 0, "resolved": 0, "resync": 0, "where": []}

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
            if o.data["opaque"] or any(op.kind == "write" and op.root in (r, None)
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

    for e in events:
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
            t = e.data["target"]
            if t[0] == "sentinel":
                poison(t[1], "the sentinel was written by an edit tool")
            elif isinstance(get(t[1]), Armed) and _slug_of(get(t[1]).rel) == t[2]:
                st = get(t[1])
                states[t[1]] = Armed(st.rel, None, 0, 0, st.paused)
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
        mutated: set = set()
        for op in ops:
            if op.kind == "write":
                mutated.add(op.root)
                if op.effect == "rm" and op.root is not None:
                    # a removal is a KNOWN state — but a hand `rm` is no clear a banner may cite
                    states[op.root], cleared[op.root] = None, None
                else:
                    poison(op.root, "the sentinel was written by hand")
                continue
            if op.kind == "planwrite":
                st = get(op.root) if op.root is not None else None
                if isinstance(st, Armed) and _slug_of(st.rel) == op.slug:
                    states[op.root] = Armed(st.rel, None, 0, 0, st.paused)
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
        # A READ of the sentinel is a checkpoint only when nothing in the command changed that
        # checkout — then where it sits in the command does not matter.
        reads = [op for op in ops if op.kind == "read" and op.root is not None]
        if len(reads) == 1 and reads[0].root not in mutated and reads[0].root not in roots:
            obs = read_observation(e.data["cmd"], e.data.get("result"))
            r = reads[0].root
            if obs:
                checkpoint(r, obs[:2], e.ts, "a read of the sentinel")
                states[r] = (None if obs[0] == "none" else
                             Armed(_rel(obs[1], r), None, 0, 0, obs[2]))
        if e.data["opaque"]:
            # ⛔ a Python heredoc wrote some sentinel: neither which one nor when is knowable
            poison(None, "a script in the command wrote a sentinel")
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
             is_error=False, run_s: float = 1.0) -> str:
        self.n += 1
        tid = f"toolu_{self.n:04d}"
        ts = self._ts()
        sess = stream.split("/")[0]
        self._put(stream, {"type": "assistant", "timestamp": ts, "sessionId": sess,
                           "cwd": cwd or self.root, "message": {"role": "assistant",
                           "stop_reason": "tool_use", "content": [{"type": "tool_use",
                           "id": tid, "name": "Bash", "input": {"command": cmd}}]}})
        if result is not None:
            end = (self.t + _dt.timedelta(seconds=run_s)).strftime("%Y-%m-%dT%H:%M:%S.500Z")
            self._put(stream, {"type": "user", "timestamp": end, "sessionId": sess,
                               "message": {"role": "user", "content": [{"type": "tool_result",
                               "tool_use_id": tid, "is_error": is_error, "content": result}]}})
        return ts

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

    def clearing(self, slug: str, d: int, n: int, *, stream="sess-aaaa1111") -> None:
        """The Stop hook's own message when it clears a fully-ticked plan."""
        msg = (f"✅ every step in `.claude/plans/{slug}.md` is ticked ({d}/{n}). "
               f"Clearing .claude/executing-plan.")
        self._put(stream, {"type": "attachment", "timestamp": self._ts(), "sessionId": stream,
                           "cwd": self.root, "attachment": {"type": "hook_success",
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
        f.bash('cat .claude/executing-plan 2>/dev/null || echo "(none armed)"', "(none armed)\n")
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
        f.bash("cat .claude/executing-plan", "plan: .claude/plans/one.md\narmed: 2026\n")
        f.bash(f"{BP} two a", _arm_out("two", 1))
    _ag_stats: dict = {}
    case("...and one that AGREES leaves the replay's links standing",
         (world(fresh(_agreed), stats=_ag_stats)[0], _ag_stats.get("agree", 0) >= 1),
         ({"one": STARTED, "two": "one"}, True))

    def _two_sentinels(f):
        f.bash(f"cd /w/wt && {BP} side a", _arm_out("side", 1))
        f.bash('echo "[$(cat /w/repo/.claude/executing-plan)]"; cat /w/wt/.claude/executing-plan',
               "cat: /w/repo/.claude/executing-plan: No such file or directory\n[]\n")
        f.bash(f"cd /w/wt && {BP} two a", _arm_out("two", 1))
    _ts_stats: dict = {}
    case("⛔ a command naming TWO sentinels is no observation of either — one's reply is not the "
         "other's", (world(_two_sentinels, root="/w/wt", stats=_ts_stats, start=False)[0]["two"],
                      _ts_stats.get("disagree")), ("side", 0))

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

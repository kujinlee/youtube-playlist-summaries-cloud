#!/usr/bin/env python3
"""Rebuild the work-line links that predate the `parent:` field — by REPLAYING the transcripts.

    python3 scripts/backfill-work-lines.py                  # DRY RUN: print the table, write nothing
    python3 scripts/backfill-work-lines.py --write          # apply the table's `keep` rows
    python3 scripts/backfill-work-lines.py --plans DIR      # read (and with --write, change) DIR
    python3 scripts/backfill-work-lines.py --ground-truth   # the replay must reproduce a live link
    python3 scripts/backfill-work-lines.py --self-test  # 63 cases

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

FAILS IF
--------
  * `--ground-truth`: the replay over the real transcripts does not reproduce the link the live
    code recorded on 2026-10-22 (`work-lines-backfill` <- `banner-thread-armed`) -> exit 1;
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


def tokenize(cmd: str) -> list[tuple[str, str]]:
    """[(kind, text)] with kind 'w' (a word, quotes removed) or 'op'. Redirections are DROPPED
    with their target, so `2>&1` and `> out` never become arguments."""
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
        if c in "<>":
            # a redirection: an all-digit word before it is its fd, not an argument
            if has_word and "".join(word).isdigit():
                word, has_word = [], False
            flush()
            i += 1
            while i < n and cmd[i] in "<>":
                i += 1
            if i < n and cmd[i] == "&":
                i += 1
                while i < n and (cmd[i].isdigit() or cmd[i] == "-"):
                    i += 1
                continue
            while i < n and cmd[i] in " \t":
                i += 1
            # swallow the target word
            sub = tokenize_word(cmd, i)
            i = sub
            continue
        if c == "&" and i + 1 < n and cmd[i + 1] == ">":
            flush(); i += 2
            while i < n and cmd[i] in " \t":
                i += 1
            i = tokenize_word(cmd, i)
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


def tokenize_word(cmd: str, i: int) -> int:
    """The index just past one shell word starting at `i` (a redirection target)."""
    n = len(cmd)
    while i < n and cmd[i] not in " \t;|&()\n":
        if cmd[i] in "'\"":
            j = cmd.find(cmd[i], i + 1)
            i = n if j < 0 else j + 1
            continue
        i += 1
    return i


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


@dataclass
class Call:
    """One `begin-plan.py` invocation: its arguments and the checkout whose sentinel it touched."""
    args: list[str]
    root: str | None      # None: the script path or cwd could not be resolved


def find_calls(cmd: str, cwd: str) -> list[Call]:
    """Every `begin-plan.py` executed by a Bash command, in order, with the root it ran against.

    The ROOT is the script's own checkout (`begin-plan.ROOT = Path(__file__).parent.parent`): the
    path is resolved against the record's cwd as changed by `cd` earlier in the same command.
    """
    toks = tokenize(strip_heredocs(cmd))
    calls: list[Call] = []
    env: dict[str, str] = {}
    cur = cwd
    simple: list[str] = []

    def finish(words: list[str]) -> None:
        nonlocal cur
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            k, v = words[0].split("=", 1)
            env[k] = expand(v, env) or v
            words = words[1:]
        if not words:
            return
        if words[0] == "cd" and len(words) >= 2:
            d = expand(words[1], env)
            cur = None if d is None or cur is None else os.path.normpath(os.path.join(cur, d))
            return
        for k in range(min(3, len(words))):
            if os.path.basename(words[k]) != "begin-plan.py":
                continue
            lead = words[:k]
            if not all(_INTERP.match(w) or w.startswith("$") or w == "env" for w in lead):
                return
            p = expand(words[k], env)
            if p is None or cur is None and not os.path.isabs(p or ""):
                calls.append(Call(words[k + 1:], None))
                return
            full = os.path.normpath(p if os.path.isabs(p) else os.path.join(cur, p))
            calls.append(Call(words[k + 1:], os.path.dirname(os.path.dirname(full))))
            return

    for kind, text in toks + [("op", ";")]:
        if kind == "w":
            simple.append(text)
        else:
            finish(simple)
            simple = []
    return calls


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
    if a.help or a.self_test or a.banner or a.status:
        return "ro", None
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
    "finish": re.compile(r"cleared \.claude/executing-plan|nothing was armed\."),
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
            out[i] = ("ok", {})
    return out


# ── the events ────────────────────────────────────────────────────────────────────────────────

@dataclass
class Event:
    ts: str
    stream: str           # the transcript FILE — a subagent is its own stream
    order: int
    session: str
    kind: str             # 'bp' | 'mut' | 'stop' | 'prompt' | 'banner'
    data: dict = field(default_factory=dict)
    end: str = ""         # when its result arrived (bp)


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def read_transcripts(tdir: Path, root: str) -> list[Event]:
    """Every event that can move the sentinel at `root`, from every transcript under `tdir`.

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
                if typ != "assistant":
                    continue
                if top and msg.get("stop_reason") == "end_turn":
                    events.append(Event(kind="stop", data={"cwd": cwd}, **base))
                for c in msg.get("content") or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text" and "SWITCHED" in c.get("text", ""):
                        for m in BANNER.finditer(c["text"]):
                            events.append(Event(kind="banner", data={"frm": m.group(1).strip(),
                                                                     "to": m.group(2).strip()},
                                                **base))
                    if c.get("type") != "tool_use":
                        continue
                    inp = c.get("input") or {}
                    if c.get("name") == "Bash":
                        cmd = inp.get("command") or ""
                        if "begin-plan.py" in cmd:
                            mine = [k for k in find_calls(cmd, cwd)
                                    if k.root is None or k.root == root]
                            subs = [classify(k.args) for k in mine]
                            if any(s != "ro" for s, _ in subs):
                                ev = Event(kind="bp", data={"calls": mine, "subs": subs}, **base)
                                events.append(ev)
                                pending[c.get("id", "")] = ev
                        elif "executing-plan" in cmd or ".claude/plans/" in cmd:
                            what = bash_mutation(cmd, cwd, root)
                            if what:
                                events.append(Event(kind="mut", data={"what": what}, **base))
                    elif c.get("name") in _WRITE_TOOLS:
                        p = os.path.normpath(inp.get("file_path") or inp.get("notebook_path")
                                             or "")
                        if p == os.path.join(root, SENTINEL_REL):
                            events.append(Event(kind="mut", data={"what": ("sentinel",)}, **base))
                        elif os.path.dirname(p) == os.path.join(root, PLAN_REL) and \
                                p.endswith(".md"):
                            events.append(Event(kind="mut", data={
                                "what": ("plan", Path(p).stem)}, **base))
    events.sort(key=lambda e: (e.ts, e.stream, e.order))
    return events


_SENT = r"\S*\.claude/executing-plan(?!\.state)\b"
_SENTINEL_WRITE = re.compile(
    r"\b(?:rm|mv|unlink|truncate|tee(?:\s+-a)?)\b[^;&|\n]*" + _SENT  # removes / moves / writes it
    + r"|\bcp\b[^;&|\n]*\s" + _SENT + r"\s*(?:$|[;&|)])"           # copied ONTO it
    + r"|>>?\s*" + _SENT                                            # redirected into it
    + r"|\bsed\s+-i\b[^;&|\n]*" + _SENT
    + r"|[\"']" + r"\.claude/executing-plan[\"']\)?\s*\.\s*(?:write_text|unlink)", re.M)
_PLAN_WRITE = re.compile(
    r"(?:\bsed\s+-i\b[^;&|\n]*|>>?\s*|\btee(?:\s+-a)?\s+|\b(?:cp|mv)\b[^;&|\n]*\s)"
    r"\S*\.claude/plans/([a-z0-9][a-z0-9-]*)\.md")
_CD = re.compile(r"(?:^|[;&|(]\s*)cd\s+(\S+)", re.M)


def bash_mutation(cmd: str, cwd: str, root: str) -> tuple | None:
    """A non-`begin-plan` Bash command that WROTE the sentinel or a plan file at `root`.

    ⚠ Leans over-inclusive: a false hit only turns a link into NO marker; a missed write could
    turn one into a WRONG marker, which is the failure this script must not have. But a READ
    (`cat`, `ls`, `2>/dev/null`) is not a write — measured 2026-10-22, matching any `>` on the
    line flagged 175 commands, nearly all of them reads."""
    here = cwd
    for m in _CD.finditer(cmd):
        d = m.group(1).strip("'\"")
        here = None if "$" in d else os.path.normpath(os.path.join(here or "/", os.path.expanduser(d)))
    if here != root and root + "/.claude/" not in cmd:
        return None
    if _SENTINEL_WRITE.search(cmd):
        return ("sentinel",)
    m = _PLAN_WRITE.search(cmd)
    return ("plan", m.group(1)) if m else None


# ── the replay ────────────────────────────────────────────────────────────────────────────────

@dataclass
class Armed:
    rel: str
    n: int | None
    lo: int
    hi: int
    paused: bool | None


UNKNOWN = "UNKNOWN"


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


def replay(events: list[Event], root: str) -> dict[str, dict]:
    """slug -> {parent, why, session, ts, stream, banners}. `parent` None means NO MARKER."""
    state: object = None                       # None | Armed | (UNKNOWN, why)
    seen: dict[str, dict] = {}
    bps = [e for e in events if e.kind == "bp"]

    def unknown(why: str) -> tuple:
        return (UNKNOWN, why)

    def overlapping(e: Event) -> bool:
        """Did another stream change plan state while `e` ran?"""
        lo, hi = e.ts, e.end or e.ts
        for o in bps:
            if o.stream == e.stream:
                continue
            if any(s != "ro" for s, _ in o.data["subs"]) and o.ts <= hi and (o.end or o.ts) >= lo:
                return True
        for o in events:
            if o.stream == e.stream or not lo <= o.ts <= hi:
                continue
            # a turn ending elsewhere matters only if it could have cleared the armed plan
            if o.kind == "mut" or (o.kind == "stop" and isinstance(state, Armed)
                                   and state.paused is not True
                                   and (state.n is None or state.hi >= state.n)):
                return True
        return False

    trail: list[tuple[str, str, str]] = []     # (when, what moved it, the state after) — --explain
    snap, last = state, None
    for e in events:
        if last is not None and state != snap:
            trail.append((last.ts, f"{last.kind} in {Path(last.stream).stem[:8]}", describe(state)))
            del trail[:-6]
        snap, last = state, e
        if e.kind == "stop":
            if not isinstance(state, Armed) or state.paused is True:
                continue
            maybe_full = state.n is None or state.hi >= state.n
            full = state.n is not None and state.lo >= state.n
            elsewhere = e.data.get("cwd") != root
            if state.paused is None or elsewhere:
                if maybe_full:
                    state = unknown("a turn ended where the Stop hook's effect cannot be known")
            elif full:
                state = None
            elif maybe_full:
                state = unknown("a turn ended after a tick whose result was not read")
            continue
        if e.kind == "mut":
            what = e.data["what"]
            if what[0] == "sentinel":
                state = unknown("the sentinel was written by hand")
            elif isinstance(state, Armed) and _slug_of(state.rel) == what[1]:
                state = Armed(state.rel, None, 0, 0, state.paused)
            continue
        if e.kind != "bp":
            continue
        outs = read_outcomes(e.data["subs"], e.data.get("result"), e.data.get("is_error", False))
        for (sub, val), call, (oc, data) in zip(e.data["subs"], e.data["calls"], outs):
            if sub == "ro":
                continue
            if call.root is None:
                if oc != "refused":
                    state = unknown("a begin-plan call ran in a checkout that cannot be resolved")
                continue
            if oc == "refused":
                continue
            if sub == "arm":
                slug = val
                if slug not in seen:
                    if oc == "unknown":
                        seen[slug] = {"parent": None, "why": "its first arm's output was not "
                                      "readable, so whether it armed then cannot be told"}
                    else:
                        if state is None:
                            par, why = STARTED, ""
                        elif isinstance(state, Armed):
                            par = _slug_of(state.rel)
                            why = "" if par else (f"the sentinel named {state.rel}, which is "
                                                  f"not a plan file")
                        else:
                            par, why = None, f"the sentinel's state was unknown: {state[1]}"
                        if par is not None and overlapping(e):
                            par, why = None, ("another session or agent changed plan state "
                                              "while this arm ran")
                        seen[slug] = {"parent": par, "why": why}
                    seen[slug].update(session=e.session, ts=e.ts, stream=e.stream,
                                      before=describe(state), trail=list(trail))
                state = (unknown(f"the output of arming {slug} was not readable")
                         if oc == "unknown" else observed(data, root))
            elif sub == "plan":
                state = (unknown("the output of --plan was not readable")
                         if oc == "unknown" else observed(data, root))
            elif sub == "tick":
                if oc == "ok":
                    # a tick that SUCCEEDED proves the plan was not paused (`cmd_tick` refuses)
                    state = observed(data, root)
                elif isinstance(state, Armed):
                    hi = state.hi + 1 if state.n is None else min(state.n, state.hi + 1)
                    state = Armed(state.rel, state.n, state.lo, hi, state.paused)
            elif sub in ("pause", "resume"):
                if isinstance(state, Armed):
                    p = (sub == "pause") if oc == "ok" else None
                    state = Armed(state.rel, state.n, state.lo, state.hi, p)
            elif sub == "finish":
                state = None if oc == "ok" else unknown("the output of --finish was not readable")
    _attach_banners(seen, events)
    return seen


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
        lo, hi = (max(before) if before else ""), (min(after) if after else "\uffff")
        rec["banners"] = [b.data["frm"] for b in evs
                          if b.kind == "banner" and b.data["to"] == slug and lo <= b.ts < hi]


# ── the decision, per plan on disk ────────────────────────────────────────────────────────────

def birth_time(p: Path) -> float | None:
    st = p.stat()
    return getattr(st, "st_birthtime", None)


def _epoch(ts: str) -> float:
    return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


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
    seen = replay(read_transcripts(tdir, root), root)
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
            if r["verdict"] != "keep":
                continue
            if r["slug"] == last:
                report += (f"\nskipped {last}: .claude/last-plan fingerprints it, and changing "
                           f"its bytes would cost the next plan its live parent")
                continue
            p = plan_dir / f"{r['slug']}.md"
            st = p.stat()
            p.write_text(apply_marker(plans[r["slug"]], r["marker"]))
            # ⛔ the page dates a plan by its mtime: a backfill must not make every plan "today"
            os.utime(p, (st.st_atime, st.st_mtime))
            n += 1
        report += f"\nwrote {n} plan file(s) in {plan_dir}"
    else:
        report += "\nDRY RUN — nothing was written. --write applies the `keep` rows."
    return 0, report


def _last_plan_slug(path: Path) -> str | None:
    try:
        m = re.search(r"^plan:\s*(\S+)\s*$", path.read_text(), re.M)
    except OSError:
        return None
    return _slug_of(m.group(1)) if m else None


def ground_truth(tdir: Path, root: str) -> tuple[int, str]:
    if not tdir.is_dir():
        return 2, f"CANNOT RUN — no transcripts at {tdir}. Treat the ground-truth check as NOT RUN."
    events = read_transcripts(tdir, root)
    if not any(e.kind == "bp" for e in events):
        return 2, (f"CANNOT RUN — {tdir} holds no begin-plan call for {root}. Treat the "
                   f"ground-truth check as NOT RUN.")
    got = replay(events, root).get(GROUND_TRUTH[0], {}).get("parent")
    if got != GROUND_TRUTH[1]:
        return 1, (f"FAIL — the replay gives {GROUND_TRUTH[0]} the parent {got!r}; the live code "
                   f"recorded {GROUND_TRUTH[1]!r}")
    return 0, f"OK — the replay reproduces {GROUND_TRUTH[0]} <- {GROUND_TRUTH[1]}"


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
        rec = replay(read_transcripts(tdir, str(root)), str(root)).get(a.explain)
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

    def world(build, root="/w/repo"):
        """Replay a constructed transcript; slug -> parent."""
        fx = _Fx(root)
        build(fx)
        with tempfile.TemporaryDirectory() as d:
            seen = replay(read_transcripts(fx.write(Path(d)), root), root)
        return {k: v["parent"] for k, v in seen.items()}, seen

    # ── the shell: finding the call and where it ran ─────────────────────────────────────────
    case("a relative script path resolves against ITS cwd",
         [c.root for c in find_calls(f"{BP} --finish", "/w/elsewhere")], ["/w/elsewhere"])
    case("--finish is a state change; --status reads only",
         (classify(["--finish"]), classify(["--status"])), (("finish", None), ("ro", None)))
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
        f.bash("rm -f .claude/executing-plan", "")
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
        _ev = {k: read_transcripts(f.write(Path(d) / k), "/w/repo")
               for k, f in (("a", _fx_a), ("b", _fx_b))}
        _evo = read_transcripts(Path(d) / "b", "/w/other")
    case("read_transcripts reads ITS directory: two dirs, two different call sets",
         [sorted(e.data["subs"][0][1] for e in _ev[k] if e.kind == "bp") for k in ("a", "b")],
         [["aa"], ["bb"]])
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
        fx.bash(f"{BP} one a", _arm_out("one", 1))
        fx.bash(f"{BP} two a", _arm_out("two", 1))
        fx.bash(f"{BP} live a", _arm_out("live", 1))
        tdir = fx.write(Path(d) / "t")
        births = {s: _dt.datetime(2026, 10, 1, 12, tzinfo=_dt.timezone.utc).timestamp()
                  for s in ("one", "two", "live")}
        before = {p.name: p.read_text() for p in pd.iterdir()}
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

    # ── the ground-truth check is CANNOT RUN without its subject, never a pass ───────────────
    with tempfile.TemporaryDirectory() as d:
        case("⛔ --ground-truth with no transcripts is CANNOT RUN (2)",
             ground_truth(Path(d) / "absent", "/w/repo")[0], 2)
        (Path(d) / "empty.jsonl").write_text("")
        case("⛔ ...and with transcripts that hold no begin-plan call, also CANNOT RUN (2)",
             ground_truth(Path(d), "/w/repo")[0], 2)
        fx = _Fx("/w/repo")
        fx.bash(f"{BP} {GROUND_TRUTH[1]} a", _arm_out(GROUND_TRUTH[1], 1))
        fx.bash(f"{BP} {GROUND_TRUTH[0]} a", _arm_out(GROUND_TRUTH[0], 1))
        case("--ground-truth passes when the replay reproduces the link",
             ground_truth(fx.write(Path(d) / "gt"), "/w/repo")[0], 0)
        fx2 = _Fx("/w/repo")
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

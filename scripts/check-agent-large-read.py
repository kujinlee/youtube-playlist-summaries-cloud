#!/usr/bin/env python3
"""Refuse a SUBAGENT's read of more than 300 lines of a file in one call (backlog #457).

WHY THIS EXISTS. Every line a tool call returns stays in the agent's context and is re-read at cache rates on
every later call. ESTIMATED in the 11-01 usage audit (230M weighted, 2 characters per token): Bash results over
8 KB were 5.75% of the total, and 72% of that (4.1% of the total) was FILE READS — `sed -n`, `cat` and `grep` on
`scripts/*.py` (~2.3%) and on other files (~1.8%). The gate scripts' own output was only 0.2%. Read is gated with
Bash: refusing only `cat` would move the same bytes to the Read tool.

⟳ NO RE-READ RULE (removed in PR #469 round 1). A second rule refused a re-read of lines the same agent had already
read from an unchanged file. It needed per-agent state, and it produced most of the round's false refusals: after a
compaction or context editing had removed the earlier lines, on the retry of a call that had failed, on the Read
that Edit requires after a `sed -n` read, and on lines "read" by a pipeline stage that never printed them. It
targeted 57 of the 257 large reads (~0.9% of usage), and Claude Code 2.1.309 already answers an exact repeat Read of
an unchanged file with "File unchanged since last read" (MEASURED in the binary). This hook keeps no state.

THE DECISION, for a PreToolUse payload (the first that applies wins):

    allow        the tool is neither Read nor Bash
    allow        the caller is not a subagent: no non-empty top-level `agent_id`. The ONE reader of that field is
                 `check-usage-pace.sent_by_subagent`, imported, never re-derived.
    NOT CHECKED  `tool_input` is not an object
    allow        Bash with `run_in_background: true` (its output goes to a file, not the context)
    NOT CHECKED  the call names a file or range this hook cannot read (below)
    deny         the call puts more than 300 lines of files into the context (`MAX_LINES`)
    allow        otherwise

THE READ PAYLOAD, MEASURED on Claude Code 2.1.309, 2026-11-01, with a marker hook dumping its stdin in a throwaway
`claude -p`: `tool_input` is `{file_path, offset, limit}`, and `offset` and `limit` are ABSENT when the model does
not pass them (no nulls). The main session's payload has no `agent_id`; a subagent's carries `agent_id` and
`agent_type` at the top level. A Read with no `limit` returns up to 2000 lines (`READ_DEFAULT_LIMIT`, the tool's
documented default). A Read of a notebook (`.ipynb`), a PDF or an image (`png`, `jpg`, `jpeg`, `gif`, `webp`) is
allowed (`NOT_TEXT`): MEASURED in the 2.1.309 binary, the Read tool takes the extension lower-cased, resets
`offset`/`limit` for a notebook and returns every cell, renders a PDF by `pages` and an image whole, so a refusal
could not be satisfied with a narrower call. Any other file with a NUL byte in its first 8 KB is binary and not
counted.

WHAT BASH FORMS ARE READ: a SIMPLE command only. ⟳ Narrowed in PR #469 round 2, the move PR #468 made: each
round of review found new edge cases in pipeline and heredoc parsing, an open surface. The command is ONE invocation
of `cat`, `head`, `tail` or `sed` on file operands, with no newline (a heredoc
has one), `$(` or backtick in it, and no token that is a shell operator (`|`, `|&`, `;`, `&&`, `||`, `&`, `(`, `)`, `<`, `<<`, `>`).
`2>/dev/null`, `2>>f` and `2>&1` are removed first: they are not stdout. `$VAR`, `${VAR}` and `~/` are expanded
from the environment. A file operand with `*`, `?` or `[` is expanded as a glob relative to the cwd. `sed` reads
all its files as ONE stream, so its ranges and a `q` count against their concatenation; `head` and `tail` count per
file. `-` is stdin, not a file.

A LIST of simple commands joined by `;` or `&&` (backlog #465) is SUMMED: it is split on those two operators only,
when unquoted (`split_list`), and each part is a simple
reader counted as above, or one of `LIST_ZERO` (`echo`, `true`, `:`, `pwd`, `ls`, `wc`: no lines counted);
the FIRST part may be `cd DIR &&` (the later parts resolve there, joined as master's prefix was). So
`sed -n 1,200p a; echo ---; sed -n 1,200p b` is 400 lines, denied. Every part is counted as if it runs: `&&` after a
failure is an over-count, a refusal of a list that could have printed that much. ESTIMATED (PR #469 body): lists of
several readers were 21% of the subagent file-read cost over 300 lines. ⟳ NARROWED in PR #471 round 1, failing toward
allow, rather than modelling more shell: `printf` is not in `LIST_ZERO` (`printf -v` assigns); any `cd` other than
one leading `cd DIR &&` (after `;` it may fail and the list goes on; a second `cd` is logical, not filesystem,
traversal) allows the whole list; only ONE trailing `;` is accepted, and any other empty part (`;;`, a leading `;`,
a trailing `&&`, `a && ; b`: bash refuses these as syntax errors) allows the whole list; and so does `$'` anywhere
(ANSI-C quoting, whose `\'` the split does not track).
A list whose reader name is quoted or partly quoted (e.g. `ca't' big; cat a`) is not recognised as a reader, so the list is
allowed (architecture review 2026-11-02, docs/reviews/architecture-review-2026-11-02-large-read-parser.md).
⟳ PR #471 round 2, the same move: a command with no unquoted `;`/`&&`, or only master's one `cd DIR &&`, takes
master's path UNCHANGED (`simple_spans`), so it gets master's verdict. A LIST is summed only when it holds none of
`LIST_STRICT` — `<`, `>`, a backslash, `$'`, `$(`, a backtick — anywhere: no redirect is parsed inside a list, since
each round-1 fix of that parsing yielded a new defect. So `cat a 2>/dev/null; cat b` (400 lines) is ALLOWED, a stated
bound and a change from master, whose `\\S+` redirect target swallowed the `;` and denied it as one `cat`. `grep` is
not in `LIST_ZERO`: `grep "" big` prints the whole file.

⚠ BOUND, stated (not NOT CHECKED: it is common and not an error): ANY OTHER Bash command is allowed silently, exit 0,
nothing printed — and IN DOUBT, THE WHOLE LIST IS ALLOWED. That includes every pipeline, `cat big | head -n 400` and
`cat small | sed -n 1,400p big` among them; a list with ANY part that is not a reader, `cd DIR` or `LIST_ZERO` (a
pipeline, `||`, `&`, an assignment, `export`, `pushd`, `printf`, `cd -`, a `cd` that is not one leading
`cd DIR &&`, `grep`, `{ ...; }`, `if`/`for`); an unquoted `#`; a redirect, a backslash, `$'`, `$(` or a
backtick anywhere in a list; an empty part other than one trailing `;`; a
QUOTED operand that is all operator characters (`cat a ';'; cat b`: `shlex` drops the quotes, so `';'` reads as an
operator and the part is unknown — 401 lines printed, allowed); a heredoc; a subshell; a reader inside `$(...)`;
output and input redirection; and an assignment prefix. ESTIMATED on
this session's transcripts (PR #469 body): a pipeline was 6% of that cost.

⚠ NOT COVERED, allowed silently: `python -c "print(open(f).read())"`, `awk`, `nl`, `less`, `bat`, `xxd`,
`git show`, `git diff`, `grep`, and `sed` without `-n` (which prints every line).

⚠ NOT CHECKED, ALLOWED, AND SAID (stderr, exit 1, never a deny, never a traceback): a payload that is not a JSON
object or not UTF-8, a `tool_input` that is not an object, a `cwd` that is not a string, a Read `file_path` that is
not a string or an `offset`/`limit` that is not an integral number (the payload's integers arrive as floats:
`parse_json` reads every integer as one), a simple reader command `shlex` cannot split, a `sed -n` script that is
not line ranges and `q`, a line number or count of more than 18 digits, `sed -s`, a glob that matches nothing, and
a `$VAR` with no value.

⚠ BOUNDS, stated. (1) A file of more than 300 lines is read in ranges of at most 300. (2) A glob is expanded by
Python's `glob`, which skips dot-files as bash does but cannot see quoting: `cat '*.txt'` is expanded too. (3) The
`==> f <==` headers `head` and `tail` print for several files are not counted.

    python3 scripts/check-agent-large-read.py --hook < payload.json
    python3 scripts/check-agent-large-read.py --self-test  # 108 cases

EXIT CODES: `--hook` 0 = allowed (silent) or denied (the decision on stdout as JSON) · 1 = NOT CHECKED.

FAILS IF: a subagent's Read or `cat`/`sed -n`/`head`/`tail` call that puts more than 300 lines of a text file into
its context as a SIMPLE command (above), or as a `;`/`&&` LIST of them that together print more than 300 lines, is
allowed; or a main-session call, a call of at most 300 lines, any other compound command (a pipeline, `||`, a list
with a part this hook does not know), or a Read of a notebook, PDF or image is denied.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import shlex
import sys
from pathlib import Path

MAX_LINES = 300
READ_DEFAULT_LIMIT = 2000
HEAD_DEFAULT = 10
BINARY_SNIFF = 8192
NOT_TEXT = frozenset({"ipynb", "pdf", "png", "jpg", "jpeg", "gif", "webp"})

_spec = importlib.util.spec_from_file_location("check_usage_pace",
                                               Path(__file__).resolve().parent / "check-usage-pace.py")
_pace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pace)
sent_by_subagent = _pace.sent_by_subagent
parse_json = _pace.parse_json

READER_WORD = re.compile(r"\b(cat|sed|head|tail)\b")
READERS = ("cat", "sed", "head", "tail")
# A newline (several commands, or a heredoc and its body) or a command substitution makes a command not simple. A
# heredoc on one line is caught by `OPERATOR` (`<<`).
COMPOUND = re.compile(r"\n|\$\(|`")
# A token made only of these is a shell operator: a pipe, a list, a background `&`, a subshell or a redirection.
OPERATOR = re.compile(r"[();<>|&]+")
STDERR_REDIRECT = re.compile(r"(?<!\S)(\d?>&\d|2>>?\s*\S+)")
VAR = re.compile(r"\$\{(\w+)\}|\$(\w+)")
GLOB_CHARS = re.compile(r"[*?[]")
# At most 18 digits: a longer number is NOT CHECKED, never a traceback from `int` (4300 digits is its limit).
SED_RANGE = re.compile(r"(\d{1,18})(?:,(\d{1,18}|\$))?p")
SED_QUIT = re.compile(r"(\d{0,18})q")
COUNT = re.compile(r"\d{1,18}")
# backlog #465: a list is split only on unquoted `;` and `&&`; any of these unquoted leaves the whole command unsplit.
LIST_DOUBT = "|&()<>#"
# ⟳ PR #471 round 2: a LIST (a `;`/`&&` beyond master's `cd DIR &&`) holding any of these is allowed whole. No
# redirect is parsed inside a list: each round-1 fix of that parsing yielded a new defect.
LIST_STRICT = ("<", ">", "\\", "$'", "`", "$(")  # `$'` matters only with a `\'`, so the backslash already covers it
# A list part starting with one of these prints no lines of a file this hook counts and changes no state the later
# parts depend on. Any OTHER non-reader part (an assignment, `export`, `pushd`, `source`, `{`, `if`) keeps the whole
# list allowed: a closed set, so an unforeseen command fails toward allow. Not `printf`: `printf -v D x` assigns.
# Not `grep` (PR #471 round 2): `grep "" big` prints the whole file.
LIST_ZERO = frozenset({"echo", "true", ":", "pwd", "ls", "wc"})
HEAD_NOARG = ("-q", "-v", "--quiet", "--silent", "--verbose")
END = 10 ** 12

ADVICE = ("TO GET THE CONTENT: `grep -n '<symbol>' <file>` to find the line, then read a narrow range of at most "
          f"{MAX_LINES} lines — Read with `offset` and `limit`, or `sed -n 'a,bp' <file>`. A reviewer that must see "
          f"a whole file reads it in ranges of {MAX_LINES}.")


class Unreadable(ValueError):
    """The call cannot be judged: the hook says NOT CHECKED and allows it."""


def line_count(path: str) -> int | None:
    """The number of lines in a regular text file, or None for a missing, special or binary file."""
    try:
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            head = fh.read(BINARY_SNIFF)
            if b"\0" in head:
                return None
            n, last = head.count(b"\n"), head[-1:]
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                n, last = n + chunk.count(b"\n"), chunk[-1:]
    except OSError:
        return None
    return n + (1 if last not in (b"", b"\n") else 0)


def take(stream: list, lo: int, hi: int) -> list:
    """Lines `lo`..`hi` (1-based, inclusive) of a stream of `(path, first, last)` pieces."""
    out, pos = [], 0
    for path, a, b in stream:
        n = b - a + 1
        s, e = max(lo, pos + 1), min(hi, pos + n)
        if s <= e:
            out.append((path, a + s - pos - 1, a + e - pos - 1))
        pos += n
    return out


def size(stream: list) -> int:
    return sum(b - a + 1 for _, a, b in stream)


def count_arg(tok: str) -> int:
    if not COUNT.fullmatch(tok):
        raise Unreadable(f"the line count {tok!r} is not a number")
    return int(tok)


def stage_op(word: str, args: list[str]):
    """`(op, files, per_file)` for one `cat`/`head`/`tail`/`sed` command: `op(stream)` keeps the lines it prints,
    applied to each file's stream when `per_file`, else to their concatenation. `op` is None for a command whose
    output is not lines of its files (`sed -i`, `sed` without `-n`, `tail -f`, `head -c`)."""
    files, it = [], iter(args)
    if word == "cat":
        files = [a for a in args if not a.startswith("-")]
        return (lambda s: s), files, False
    if word in ("head", "tail"):
        n, from_start, all_but = HEAD_DEFAULT, False, False
        for a in it:
            if a in ("-f", "-F", "--follow", "-c") or a.startswith(("--bytes", "-c")):
                return None, [], True
            if a in HEAD_NOARG:
                continue
            if a == "-n" or a == "--lines":
                a = "-n" + next(it, "")
            if a.startswith("--lines="):
                a = "-n" + a[len("--lines="):]
            if a.startswith("-n"):
                v = a[2:]
            elif a.startswith("-") and len(a) > 1:
                v = a[1:]
            elif word == "tail" and a.startswith("+") and not files:
                v = a
            else:
                files.append(a)
                continue
            from_start = word == "tail" and v.startswith("+")
            all_but = word == "head" and v.startswith("-")
            n = count_arg(v.lstrip("+-") if all_but else v.lstrip("+"))
        if all_but:  # `head -n -K`: every line but the last K
            return (lambda s: take(s, 1, size(s) - n)), files, True
        if word == "head":
            return (lambda s: take(s, 1, n)), files, True
        if from_start:
            return (lambda s: take(s, n, END)), files, True
        return (lambda s: take(s, size(s) - n + 1, END)), files, True
    quiet, script = False, None
    for a in it:
        if a.startswith("-i") or a == "--in-place" or a.startswith("--in-place="):
            return None, [], False
        if a == "--separate" or (a.startswith("-") and not a.startswith("--") and "s" in a[1:]):
            raise Unreadable("`sed -s` numbers each file separately, which this hook does not model")
        if a in ("-e", "--expression"):
            script = (script + ";" if script else "") + next(it, "")
        elif a in ("-n", "--quiet", "--silent"):
            quiet = True
        elif a.startswith("-") and len(a) > 1:
            quiet = quiet or "n" in a[1:]
        elif script is None:
            script = a
        else:
            files.append(a)
    if not quiet:
        return None, [], False
    cmds = []
    for part in re.split(r"[;\n]", script or ""):
        part = part.strip()
        if not part:
            continue
        q = SED_QUIT.fullmatch(part)
        if q:
            cmds.append(("q", int(q.group(1) or 1), 0))
            continue
        m = SED_RANGE.fullmatch(part)
        if not m:
            raise Unreadable(f"the sed -n script {script!r} is not line ranges")
        lo = int(m.group(1))
        cmds.append(("p", lo, lo if m.group(2) is None else END if m.group(2) == "$" else int(m.group(2))))
    # `Nq` stops the stream at line N: a `p` before it in the script prints line N, a `p` after it does not.
    quits = [(i, n) for i, (c, n, _) in enumerate(cmds) if c == "q"]
    ranges = [(lo, min([hi, *(n if j > i else n - 1 for j, n in quits)]))
              for i, (c, lo, hi) in enumerate(cmds) if c == "p"]
    return (lambda s: [p for lo, hi in ranges for p in take(s, lo, hi)]), files, False


def expand(tok: str, env: dict) -> str:
    def sub(m):
        name = m.group(1) or m.group(2)
        if env.get(name) is None:
            raise Unreadable(f"${name} has no value here")
        return env[name]
    if tok == "~" or tok.startswith("~/"):
        tok = env.get("HOME", "~") + tok[1:]
    return VAR.sub(sub, tok)


def operands(tok: str, cwd: str, env: dict) -> list[str]:
    """The paths one file operand names: a glob is expanded relative to `cwd`, as the shell would."""
    path = os.path.join(cwd, expand(tok, env))
    if not GLOB_CHARS.search(path):
        return [path]
    found = sorted(glob.glob(path))
    if not found:
        raise Unreadable(f"the glob {tok!r} matches no file")
    return found


def simple_command(command: str) -> tuple[str | None, list[str]] | None:
    """`(cd_dir, words)` for a SIMPLE reader command — `cd_dir` the one `cd DIR &&` prefix or None — else None."""
    if not READER_WORD.search(command) or COMPOUND.search(command.strip()):
        return None
    try:
        lex = shlex.shlex(STDERR_REDIRECT.sub(" ", command), posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError as exc:
        raise Unreadable(f"shlex cannot split the command ({exc})") from None
    cd_dir = None
    if len(tokens) > 3 and tokens[0] == "cd" and tokens[2] == "&&":
        cd_dir, tokens = tokens[1], tokens[3:]
    if tokens[0] not in READERS or any(OPERATOR.fullmatch(t) for t in tokens):
        return None
    return cd_dir, tokens


def simple_spans(command: str, cwd: str, env: dict) -> list:
    """The `(path, first, last)` line ranges a SIMPLE reader command puts into the context; [] for any other.
    ⟳ PR #471 round 2: master's `bash_spans`, unchanged."""
    simple = simple_command(command)
    if simple is None:
        return []
    cd_dir, tokens = simple
    if cd_dir is not None:
        cwd = os.path.join(cwd, expand(cd_dir, env))
    op, files, per_file = stage_op(tokens[0], tokens[1:])
    if op is None:
        return []
    pieces = []
    for f in files:
        if f == "-":  # stdin, not a file
            continue
        for path in operands(f, cwd, env):
            n = line_count(path)
            if n:
                pieces.append([(os.path.realpath(path), 1, n)])
    return ([x for piece in pieces for x in op(piece)] if per_file
            else op([x for piece in pieces for x in piece]))


def bash_spans(command: str, cwd: str, env: dict) -> list:
    """The line ranges a Bash command puts into the context. ⟳ PR #471 round 2: a command with no unquoted `;` or
    `&&`, or only master's one `cd DIR &&`, takes master's path (`simple_spans`) and gets master's verdict; any other
    is a LIST (`list_spans`)."""
    parts, _ = split_list(command)
    if len(parts) == 1:
        return simple_spans(command, cwd, env)
    if len(parts) == 2 and parts[0][1] == "&&":
        simple = simple_command(command)
        if simple is not None and simple[0] is not None:  # master's `cd DIR && <reader>`
            return simple_spans(command, cwd, env)
    return list_spans(command, parts, cwd, env)


def split_list(command: str) -> tuple[list[tuple[str, str]], bool]:
    """The `(part, separator)` pairs of a LIST joined by unquoted `;` and `&&` (backlog #465) — the separator after
    the part, "" for the last — and whether the command has any other unquoted shell operator character (`|`, `&`,
    `(`, `)`, `<`, `>`) or an unquoted `#`: in doubt, `list_spans` does not sum it. Quotes and backslashes are
    tracked, so `'a;b'`, `"x && y"` and `x\\;y` do not split. ⟳ PR #471 round 2: no redirect is recognised here. After
    an unbalanced quote the rest is one part, which `shlex` then cannot split (`list_spans` allows it)."""
    parts, cur, quote, doubt, i = [], [], None, False, 0
    while i < len(command):
        c = command[i]
        if quote:
            cur.append(c)
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"':
                cur.append(command[i + 1:i + 2])
                i += 1
        elif c in "'\"":
            quote = c
            cur.append(c)
        elif c == "\\":
            cur.append(command[i:i + 2])
            i += 1
        elif c == ";":
            parts.append(("".join(cur), ";"))
            cur = []
        elif command.startswith("&&", i):
            parts.append(("".join(cur), "&&"))
            cur = []
            i += 1
        else:
            doubt = doubt or c in LIST_DOUBT
            cur.append(c)
        i += 1
    return [*parts, ("".join(cur), "")], doubt


def list_spans(command: str, parts: list[tuple[str, str]], cwd: str, env: dict) -> list:
    """The line ranges a LIST of simple commands puts into the context, SUMMED over its parts (backlog #465): each
    part is a simple reader (counted as `simple_spans` counts one) or a command in `LIST_ZERO` (counted as no lines),
    and the FIRST part may be `cd DIR &&` (the later parts resolve there). Any other part — a pipeline, an
    assignment, `export`, `{`, `if`, `grep`, any other `cd`, an empty part but one trailing `;` — and any of
    `LIST_STRICT` (a redirect, a backslash, `$'`, `$(`, a backtick) or an unquoted `|&()#` anywhere make the WHOLE
    list [] (allowed): fail toward allow (PR #471 rounds 1 and 2 narrowed it). ⟳ Round 3: a part `simple_command`
    reads through a `cd` prefix (`cd . '&&' cat big`, quote-unaware after `shlex`) also allows the whole list."""
    if COMPOUND.search(command.strip()) or any(x in command for x in LIST_STRICT):  # in doubt, the whole list
        return []
    parts, doubt = split_list(command)
    if doubt:
        return []
    if len(parts) > 1 and not parts[-1][0].strip() and parts[-2][1] == ";":
        parts = parts[:-1]  # ONE trailing `;`
    spans = []
    for n, (part, sep) in enumerate(parts):
        if not part.strip():  # `;;`, a leading `;`, a trailing `&&`: bash refuses the list, it runs nothing
            return []
        simple = simple_command(part)
        if simple is not None:
            if simple[0] is not None:  # PR #471 round 3: master's `cd DIR &&` prefix parser stays in master's path
                return []
            spans += simple_spans(part, cwd, env)
            continue
        try:
            words = shlex.split(part)
        except ValueError:  # never a traceback from the hook
            return []
        if words and words[0] == "cd":
            if not (n == 0 and sep == "&&" and len(words) == 2 and words[1] != "-"):
                return []
            cwd = os.path.join(cwd, expand(words[1], env))
        elif not (words and words[0] in LIST_ZERO):
            return []
    return spans


def read_spans(ti: dict) -> list:
    """The `(path, first, last)` line range a Read call puts into the context."""
    path, offset, limit = ti.get("file_path"), ti.get("offset", 1), ti.get("limit", READ_DEFAULT_LIMIT)
    if not isinstance(path, str):
        raise Unreadable(f"its file_path {path!r} is not a string")
    for k, v in (("offset", offset), ("limit", limit)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not float(v).is_integer():
            raise Unreadable(f"its {k} {v!r} is not an integer")
    if os.path.splitext(path)[1].lower().lstrip(".") in NOT_TEXT:
        return []
    offset, limit = int(offset), int(limit)
    n = line_count(path)
    if not n:
        return []
    return take([(os.path.realpath(path), 1, n)], max(offset, 1), max(offset, 1) + max(limit, 1) - 1)


def decide(doc: dict, env: dict) -> str | None:
    """The denial reason for a parsed PreToolUse payload, or None to allow; raises Unreadable for NOT CHECKED."""
    tool = doc.get("tool_name")
    if tool not in ("Read", "Bash") or not sent_by_subagent(json.dumps(doc)):
        return None
    ti = doc.get("tool_input")
    if not isinstance(ti, dict):
        raise Unreadable(f"its tool_input is not an object ({type(ti).__name__})")
    if tool == "Bash":
        if ti.get("run_in_background") is True:
            return None
        cmd, cwd = ti.get("command"), doc.get("cwd")
        if not isinstance(cmd, str):
            raise Unreadable(f"its command {cmd!r} is not a string")
        if cwd is not None and not isinstance(cwd, str):
            raise Unreadable(f"its cwd {cwd!r} is not a string")
        spans = bash_spans(cmd, cwd or os.getcwd(), env)
    else:
        spans = read_spans(ti)
    total = size(spans)
    if total > MAX_LINES:
        return (f"⛔ REFUSED (backlog #457): this call puts {total} lines of "
                f"{', '.join(sorted({p for p, _, _ in spans}))} into your context, over {MAX_LINES}. Every line "
                "stays in your context and is re-read at cache rates on every later call. " + ADVICE)
    return None


def main(argv: list[str] | None = None, stdin_bytes: bytes | None = None, env: dict | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--hook"]:
        print("usage: check-agent-large-read.py --hook < payload  |  --self-test", file=sys.stderr)
        return 1
    try:
        raw = sys.stdin.buffer.read() if stdin_bytes is None else stdin_bytes
        try:
            doc = parse_json(raw.decode("utf-8"))
        except ValueError as exc:
            doc = exc
        if not isinstance(doc, dict):
            raise Unreadable(f"the hook payload is not a JSON object ({type(doc).__name__})")
        reason = decide(doc, os.environ if env is None else env)
    except (Unreadable, OSError) as exc:
        print(f"⚠ check-agent-large-read: {exc}; this call was NOT CHECKED for a large read (backlog #457).",
              file=sys.stderr)
        return 1
    if reason is not None:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    return 0


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()` (backlog #382): the repo's rule for every suite."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import tempfile
    ok = fail = 0
    root = tempfile.mkdtemp(prefix="large-read-")
    big, small, b300, b301 = (os.path.join(root, f) for f in ("big.txt", "small.txt", "b300.txt", "b301.txt"))
    for path, n in ((big, 500), (small, 100), (b300, 300), (b301, 301)):
        Path(path).write_text("".join(f"line {i}\n" for i in range(1, n + 1)))
    two_a, two_b = os.path.join(root, "a.txt"), os.path.join(root, "b.txt")
    Path(two_a).write_text("x\n" * 200)
    Path(two_b).write_text("y\n" * 200)
    binary = os.path.join(root, "img.bin")
    Path(binary).write_bytes(b"\x89PNG\0" + b"\n" * 1000)

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r}, want {want!r}")

    def p(tool="Read", agent="a1", **ti):
        doc = {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": tool, "cwd": "/", "tool_input": ti}
        if agent:
            doc.update(agent_id=agent, agent_type="general-purpose")
        return doc

    def verdict(doc, env=None):
        try:
            return "deny" if decide(doc, {"HOME": root} if env is None else env) else "allow"
        except Unreadable:
            return "not checked"
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}"

    def sh(cmd, **kw):
        return verdict(p("Bash", command=cmd), **kw)

    # Read
    case("a subagent's Read of a 500-line file with no limit is denied", verdict(p(file_path=big)), "deny")
    case("Read limit 300 on a 500-line file (the boundary) is allowed", verdict(p(file_path=big, limit=300)), "allow")
    case("Read limit 301 on a 500-line file is denied", verdict(p(file_path=big, limit=301)), "deny")
    case("a 300-line file read whole is allowed, a 301-line file is denied",
         [verdict(p(file_path=b300)), verdict(p(file_path=b301))], ["allow", "deny"])
    case("Read offset 250 with no limit reads 251 lines of 500: allowed",
         verdict(p(file_path=big, offset=250)), "allow")
    case("Read offset 200 with no limit reads 301 lines of 500: denied", verdict(p(file_path=big, offset=200)), "deny")
    case("the MAIN session (no agent_id) is never denied", verdict(p(agent=None, file_path=big)), "allow")
    case("an agent_id the MODEL wrote into tool_input is not a subagent",
         verdict(p(agent=None, file_path=big, agent_id="a1")), "allow")
    case("a binary file is not counted", verdict(p(file_path=binary)), "allow")
    not_text = []
    for ext in ("ipynb", "PDF", "png", "jpg", "jpeg", "gif", "webp"):
        f = os.path.join(root, f"text-body.{ext}")
        Path(f).write_text("{\n" * 500)
        not_text.append(verdict(p(file_path=f, limit=301)))
    case("a 500-line notebook, PDF or image (any case, no NUL) is allowed: Read ignores offset/limit for them",
         not_text, ["allow"] * 7)
    case("a missing file is allowed (the tool reports it)", verdict(p(file_path=root + "/none.txt")), "allow")
    case("a file_path that is not a string is NOT CHECKED", verdict(p(file_path=3)), "not checked")
    case("a limit that is not an integer is NOT CHECKED (a string, a boolean)",
         [verdict(p(file_path=big, limit="300")), verdict(p(file_path=big, limit=True))], ["not checked"] * 2)
    case("a limit that is a float with a fraction, or infinite, is NOT CHECKED",
         [verdict(p(file_path=big, limit=1.5)), verdict(p(file_path=big, limit=float("inf")))], ["not checked"] * 2)
    case("an offset that is not an integer is NOT CHECKED", verdict(p(file_path=big, offset="1")), "not checked")
    no_nl = os.path.join(root, "nonl.txt")
    Path(no_nl).write_text("z\n" * 300 + "z")
    case("a last line without a newline is counted: 300 newlines + 1 line is denied", verdict(p(file_path=no_nl)),
         "deny")
    case("a tool other than Read and Bash is not gated", verdict(p("Grep", file_path=big)), "allow")
    case("a tool_input that is not an object is NOT CHECKED", verdict({**p(), "tool_input": "x"}), "not checked")
    # Bash
    case("`cat` of a 500-line file is denied", sh(f"cat {big}"), "deny")
    case("`cat` of a 100-line file is allowed", sh(f"cat {small}"), "allow")
    case("`cat -n` (a flag) of a 500-line file is denied", sh(f"cat -n {big}"), "deny")
    Path(root, "-n").write_text("f\n" * 250)
    case("a flag is not a file operand, even when a file has its name: `cat -n small.txt` is 100 lines",
         sh(f"cd {root} && cat -n small.txt"), "allow")
    case("`cat` of two 200-line files is 400 lines: denied", sh(f"cat {two_a} {two_b}"), "deny")
    case("a PIPE is not a simple command: allowed silently, even `cat big | head -n 400` (bound, stated)",
         [sh(f"cat {big} | grep line"), sh(f"cat {big} | head -n 400"), sh(f"cat {big} |& grep line"),
          sh(f"cat {small} | head -n 400 {big}")], ["allow"] * 4)
    case("`||` and `&` after a reader are not a list this hook sums: allowed (bound, stated)",
         [sh(f"cat {big} || echo"), sh(f"cat {big} &"), sh(f"cat {big} || cat {big}")], ["allow"] * 3)
    # backlog #465: a list of simple commands joined by `;` or `&&` is SUMMED.
    case("a `;` list of readers is summed: `sed -n 1,200p a; sed -n 1,200p b` (400) is denied; a trailing `;`",
         [sh(f"sed -n 1,200p {two_a}; sed -n 1,200p {two_b}"), sh(f"cat {big}; echo"), sh(f"cat {big};")],
         ["deny"] * 3)
    case("a newline, `$(` or a backtick anywhere keeps a list allowed whole",
         [sh(f"cat {big}; echo $(date)"), sh(f"cat {big}; echo `date`"), sh(f"cat {big}; echo\necho")],
         ["allow"] * 3)
    case("the sum is of DISTINCT parts: 120 + 190 = 310 is denied, 120 + 170 = 290 is allowed",
         [sh(f"head -n 120 {big}; tail -n 190 {big}"), sh(f"head -n 120 {big}; tail -n 170 {big}")],
         ["deny", "allow"])
    case("a list's denial states the summed count: 120 + 190 of big is '310 lines'; 120 + all 100 of small is allowed",
         ["310 lines" in (decide(p("Bash", command=f"head -n 120 {big}; tail -n 190 {big}"), {}) or ""),
          sh(f"head -n 120 {big}; tail -n 190 {small}")], [True, "allow"])
    case("an `&&` list is summed, and a leading `cd DIR &&` moves the later parts: both denied",
         [sh(f"cat {small} && cat {b300}"), sh(f"cd {root} && sed -n 1,200p a.txt && sed -n 1,200p b.txt")],
         ["deny"] * 2)
    case("`echo` between readers counts nothing: 150 + 150 is allowed (the boundary), 150 + 151 is denied",
         [sh(f"sed -n 1,150p {two_a}; echo ---; sed -n 1,150p {two_b}"),
          sh(f"sed -n 1,150p {two_a}; echo ---; sed -n 1,151p {two_b}")], ["allow", "deny"])
    case("a QUOTED `;` or `&&` does not split: one `echo` is allowed; 200 + 200 around `';x;'` is denied",
         [sh(f"echo 'x; cat {big}'"), sh(f'echo "x && cat {big}"'),
          sh(f"head -n 200 {big} ';x;' ; head -n 200 {big}")], ["allow", "allow", "deny"])
    case("a list with a PIPELINE part is allowed whole, even when the pipe's first word counts nothing",
         [sh(f"cat {small}; cat {big} | head -n 5"), sh(f"cat {big}; echo x | grep x")], ["allow"] * 2)
    case("a list with a part this hook does not know is allowed whole: an assignment, `export`, `{`, `python3`",
         [sh(f"D=x; cat {big}"), sh(f"export D=x && cat {big}"), sh(f"{{ cat {big}; }}"),
          sh(f"cat {big}; python3 x.py")], ["allow"] * 4)
    case("an unquoted `#` keeps a list unsplit: `cd DIR && cat small # ; cat big` is allowed",
         sh(f"cd {root} && cat small.txt # ; cat big.txt"), "allow")
    dash = os.path.join(root, "dash")
    os.makedirs(os.path.join(dash, "-"))
    Path(dash, "-", "big.txt").write_text("d\n" * 500)
    case("`cd -` (the previous directory, unknown here) keeps a list allowed whole",
         verdict({**p("Bash", command="cd - && cat big.txt && echo"), "cwd": dash}), "allow")
    # PR #471 round 1: the counts in these names are what bash printed for the same command.
    logical = os.path.join(root, "logical")
    os.makedirs(os.path.join(root, "physical", "child"))
    os.makedirs(logical)
    os.symlink(os.path.join("..", "physical", "child"), os.path.join(logical, "link"))
    Path(logical, "big.txt").write_text("l\n" * 500)
    case("any `cd` but ONE leading `cd DIR &&` keeps a list allowed whole: after `;` (`cd missing; cat a; cat b`, 400), "
         "a second `cd` (`cd logical/link; cd ..; cat big`, 500), a `cd` that is not first",
         [sh(f"cd {root}; cat big.txt"), sh(f"cd {root}/missing; cat {two_a}; cat {two_b}"),
          sh(f"cd {logical}/link; cd ..; cat big.txt"), sh(f"cd {root} && cd . && cat big.txt"),
          sh(f"cat {small} && cd {root} && cat big.txt")], ["allow"] * 5)
    case("a list part master's prefix parser reads as `cd DIR && reader` keeps the list allowed whole: "
         "`true; cd . '&&' cat big` (bash: 0 lines), `cat a; cd . '&&' cat big` (200)",
         [verdict({**p("Bash", command="true; cd . '&&' cat big.txt"), "cwd": root}),
          verdict({**p("Bash", command=f"cat {two_a}; cd . '&&' cat big.txt"), "cwd": root})],
         ["allow"] * 2)
    # PR #471 round 2: a command with no `;`/`&&` but master's one `cd DIR &&` takes master's path, master's verdict.
    Path(root, " 2>x(big)").write_text("q\n" * 100)
    Path(root, "  (big)").write_text("q\n" * 500)
    case("master's path, master's verdict: `cd DIR 2>/dev/null && cat big` (500), `... && head -n 400 big` (400), "
         "`cat big 2>&-` (500) and `cd - && cat big` are denied; `cat ' 2>x(big)'` (a quoted name) is NOT CHECKED",
         [sh(f"cd {root} 2>/dev/null && cat big.txt"), sh(f"cd {root} 2>/dev/null && head -n 400 big.txt"),
          sh(f"cat {big} 2>&-"), verdict({**p("Bash", command="cd - && cat big.txt"), "cwd": dash}),
          verdict({**p("Bash", command="cat ' 2>x(big)'"), "cwd": root})], ["deny"] * 4 + ["not checked"])
    case("an escaped `;` is not a separator: `head -n 400 big x\\;y` is one command, master's path, denied",
         sh(f"head -n 400 {big} x\\;y"), "deny")
    case("master's path keeps master's false refusal: `cat big 2>/dev/null|head -5` (5 printed) is denied",
         sh(f"cat {big} 2>/dev/null|head -5"), "deny")
    case("a LIST with a redirect, a backslash, `$'`, `$(` or a backtick is allowed whole (bound, stated): "
         "`cat a; cat b 2>err\\;x` (400), `cat small 2>&1big; true` (0), `cat a;2>/dev/null cat b` (400), "
         "`cat a 2>/dev/null; cat b` (400), `head -n 200 big x\\;y; head -n 200 big` (400)",
         [sh(f"cat {two_a}; cat {two_b} 2>err\\;x"), sh(f"cat {small} 2>&1big; true"),
          sh(f"cat {two_a};2>/dev/null cat {two_b}"), sh(f"cat {two_a} 2>/dev/null; cat {two_b}"),
          sh(f"head -n 200 {big} x\\;y; head -n 200 {big}")], ["allow"] * 5)
    case("`grep` is not a zero-line part (`grep \"\" big` prints the file): `grep x small; cat a; cat b` is allowed",
         sh(f"grep x {small}; cat {two_a}; cat {two_b}"), "allow")
    case("`printf` is not a zero-line part (`printf -v D a; cat \"$D\"` assigns): `printf x; cat big` (500) is allowed",
         [sh(f"printf x; cat {big}"), sh('printf -v D a; cat "$D"', env={"D": big})], ["allow"] * 2)
    case("an empty part but ONE trailing `;` keeps a list allowed: `cat big;;`, `; cat big`, `cat big &&`, "
         "`cat a && ; cat b` (bash: a syntax error, 0 lines)",
         [sh(f"cat {big};;"), sh(f"; cat {big}"), sh(f"cat {big} &&"), sh(f"cat {two_a} && ; cat {two_b}")],
         ["allow"] * 4)
    case("`$'` anywhere keeps a list allowed: `echo $'\\';cat big;echo ' \\'` is one `echo` (1 line)",
         sh(f"echo $'\\';cat {big};echo ' \\'"), "allow")
    case("a newline, a heredoc, `$( ... )` and backticks are not a simple command: allowed",
         [sh(f"echo hi\ncat {big}"), sh(f"cat <<EOF\nx\nEOF\ncat {big}"), sh(f"cat {big} <<EOF"),
          sh(f"X=$(cat {big})"), sh(f"echo `cat {big}`")], ["allow"] * 5)
    case("an input redirection and a subshell are not a simple command: allowed",
         [sh(f"cat < {big}"), sh(f"(cd {root} && cat big.txt)")], ["allow"] * 2)
    Path(root, "-").write_text("f\n" * 250)
    case("`-` is stdin, not a file, even with a file named `-` in the cwd: `head -n 300 - small.txt` is 100 lines",
         [sh(f"cd {root} && head -n 300 - small.txt"), sh(f"cat - {big}")], ["allow", "deny"])
    case("a newline after a reader is two commands: `cat big` then `echo hi`, allowed", sh(f"cat {big}\necho hi"),
         "allow")
    case("a quoted `$( ... )` operand and a backtick operand are not a simple command: allowed",
         [sh(f'cat "$(echo {small})" {big}'), sh(f"cat `echo x` {big}")], ["allow"] * 2)
    case("process substitution `<( ... )` is not a simple command: allowed", sh(f"cat {big} <(echo)"), "allow")
    case("a reader word that is not the command is not read: `echo -n cat big` is allowed", sh(f"echo -n cat {big}"),
         "allow")
    case("`cat` written to a file is allowed", sh(f"cat {big} > {root}/copy.txt"), "allow")
    case("`2>/dev/null` and `2>&1` do not hide stdout", [sh(f"cat {big} 2>/dev/null"), sh(f"cat {big} 2>&1")],
         ["deny"] * 2)
    case("a relative path after `cd DIR &&` is resolved there", sh(f"cd {root} && cat big.txt"), "deny")
    case("a second `&&` after the `cd DIR &&` prefix is a list, summed: denied",
         sh(f"cd {root} && cat big.txt && echo"), "deny")
    case("`pushd DIR &&` is not `cd`, and `cd DIR ||` is not a list: both allowed",
         [sh(f"cd {root} || cat big.txt"), sh(f"pushd {root} && cat big.txt")], ["allow"] * 2)
    case("`cd` with a variable is expanded from the environment", sh("cd $D && cat big.txt", env={"D": root}), "deny")
    case("a relative path resolves against the payload's cwd", verdict({**p("Bash", command="cat big.txt"),
                                                                         "cwd": root}), "deny")
    case("a cwd that is not a string is NOT CHECKED", verdict({**p("Bash", command="cat big.txt"), "cwd": 23}),
         "not checked")
    case("a relative glob is expanded where `cd` left it: `cat big.t?t` is denied",
         sh(f"cd {root} && cat big.t?t"), "deny")
    case("a glob over several files counts them all: `cat [ab].txt` is 400 lines, denied",
         sh(f"cat {root}/[ab].txt"), "deny")
    case("a glob that matches nothing is NOT CHECKED", sh(f"cat {root}/nomatch*"), "not checked")
    case("an environment variable is expanded", sh("cat ${D}/big.txt", env={"D": root}), "deny")
    case("`~/` is the environment's HOME", sh("cat ~/big.txt"), "deny")
    case("a variable with no value is NOT CHECKED", sh("cat $NOPE/big.txt"), "not checked")
    case("an unbalanced quote in a reader command is NOT CHECKED", sh(f"cat '{big}"), "not checked")
    case("a command naming no reader is not parsed: an unbalanced quote is allowed", sh("echo 'hi"), "allow")
    case("an unbalanced quote in a LATER list part is allowed, not a traceback: `cat small; echo 'x`", sh(f"cat {small}; echo 'x"), "allow")
    case("master's path reads a quoted operand of operator characters as an operator: `cat big ';'` (500) is allowed (bound, stated)", sh(f"cat {big} ';'"), "allow")
    case("`sed -n '1,300p'` is allowed, '1,301p' is denied",
         [sh(f"sed -n '1,300p' {big}"), sh(f"sed -n '1,301p' {big}")], ["allow", "deny"])
    case("`sed -n '200,$p'` on 500 lines is 301: denied", sh(f"sed -n '200,$p' {big}"), "deny")
    case("`sed -n` with two ranges sums them (100 + 201)", sh(f"sed -n '1,100p;200,400p' {big}"), "deny")
    case("`sed -n -e R -e R` sums its expressions", sh(f"sed -n -e 1,100p -e 200,400p {big}"), "deny")
    case("`sed -n 'Np'` is one line: '100p' is allowed", sh(f"sed -n '100p' {big}"), "allow")
    case("`sed` reads its files as ONE stream: '1,200p' over two 200-line files is 200 lines, allowed",
         sh(f"sed -n '1,200p' {two_a} {two_b}"), "allow")
    case("... and '1,400p' over them is 400 lines, denied", sh(f"sed -n '1,400p' {two_a} {two_b}"), "deny")
    case("`sed -s` (each file numbered alone) is NOT CHECKED: `-s`, `-ns`, `--separate`",
         [sh(f"sed -s -n '1,200p' {two_a} {two_b}"), sh(f"sed -ns '1,200p' {two_a} {two_b}"),
          sh(f"sed --separate -n '1,200p' {two_a} {two_b}")], ["not checked"] * 3)
    case("`-n` inside a flag group (`sed -En`) is quiet: '1,400p' is denied", sh(f"sed -En '1,400p' {big}"), "deny")
    case("`sed -n '1,400p;1q'` stops at line 1: allowed", sh(f"sed -n '1,400p;1q' {big}"), "allow")
    case("a bare `q` stops at line 1: allowed", sh(f"sed -n '1,400p;q' {big}"), "allow")
    case("a `p` before `301q` prints line 301 (denied); a `p` after it does not (allowed)",
         [sh(f"sed -n '1,400p;301q' {big}"), sh(f"sed -n '301q;1,400p' {big}")], ["deny", "allow"])
    case("`sed -n` with a pattern script is NOT CHECKED", sh(f"sed -n '/def/p' {big}"), "not checked")
    case("`sed -i` edits, it does not read, even with -n and a range", sh(f"sed -n -i '1,400p' {big}"), "allow")
    case("`sed` without -n is not counted", sh(f"sed 's/a/b/' {big}"), "allow")
    case("`head` defaults to 10 lines", sh(f"head {big}"), "allow")
    case("`head -n 400`, `head -400` and `head --lines=400` are denied",
         [sh(f"head -n 400 {big}"), sh(f"head -400 {big}"), sh(f"head --lines=400 {big}")], ["deny"] * 3)
    case("`head -n -100` is every line but 100 (400): denied; `head -n -250` (250) is allowed",
         [sh(f"head -n -100 {big}"), sh(f"head -n -250 {big}")], ["deny", "allow"])
    case("`head` counts per file: `head -n 250` of two 200-line files is 400, denied",
         sh(f"head -n 250 {two_a} {two_b}"), "deny")
    case("`head -q` and `-v` are flags, not counts", [sh(f"head -q -n 400 {big}"), sh(f"head -v -n 5 {big}")],
         ["deny", "allow"])
    case("`tail -n 50` is allowed, `tail -n +100` (401 lines) is denied",
         [sh(f"tail -n 50 {big}"), sh(f"tail -n +100 {big}")], ["allow", "deny"])
    case("`tail -n 400` is the last 400 lines: denied", sh(f"tail -n 400 {big}"), "deny")
    case("`tail -f` follows, it is not counted", sh(f"tail -f {big}"), "allow")
    case("a line count that is not a number is NOT CHECKED", sh(f"head -n x {big}"), "not checked")
    case("a number of more than 18 digits is NOT CHECKED, not a traceback: a sed `q`, a sed range, a head count",
         [sh(f"sed -n '{'9' * 4301}q' {big}"), sh(f"sed -n '{'9' * 4301}p' {big}"),
          sh(f"sed -n '1,{'9' * 4301}p' {big}"), sh(f"head -n {'9' * 4301} {big}")], ["not checked"] * 4)
    case("... and 18 digits are read: `head -n 999999999999999999` of 500 lines is denied",
         sh(f"head -n {'9' * 18} {big}"), "deny")
    case("run_in_background: true is allowed", verdict(p("Bash", command=f"cat {big}", run_in_background=True)),
         "allow")
    case("the MAIN session's `cat` is never denied", verdict(p("Bash", agent=None, command=f"cat {big}")), "allow")
    case("a command that is not a string is NOT CHECKED", verdict(p("Bash", command=["cat"])), "not checked")
    case("the denial says how to get the content: grep -n, offset/limit, sed -n and the limit",
         all(x in (decide(p(file_path=big), {}) or "") for x in ("grep -n", "500 lines", "offset", "sed -n", "300")),
         True)

    def drive(data):
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["--hook"], data, {})
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}", "", ""
        return rc, out.getvalue(), err.getvalue()

    rc, out, _ = drive(json.dumps(p(file_path=big)).encode())
    case("main --hook: a denial is the PreToolUse deny JSON at exit 0",
         (rc, json.loads(out or "{}").get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
    case("main --hook: an allowed call prints nothing at exit 0", drive(json.dumps(p(file_path=small)).encode())[:2],
         (0, ""))
    case("main --hook: a Read with offset and limit (integers parsed as floats) is judged, not NOT CHECKED",
         drive(json.dumps(p(file_path=big, offset=1, limit=100)).encode())[:2], (0, ""))
    rc, out, _ = drive(json.dumps(p(file_path=big, offset=1, limit=400)).encode())
    case("main --hook: a Read whose float limit is over 300 is denied", "deny" in out, True)
    rc, out, err = drive(b"{not json")
    case("main --hook: an unreadable payload is NOT CHECKED — exit 1, said on stderr, no decision",
         (rc, out, "NOT CHECKED" in err), (1, "", True))
    rc, out, err = drive(b"\xff\xfe")
    case("main --hook: a payload that is not UTF-8 is NOT CHECKED, no traceback", (rc, out, "NOT CHECKED" in err),
         (1, "", True))
    rc, out, err = drive(json.dumps({**p("Bash", command="cat big.txt"), "cwd": 23}).encode())
    case("main --hook: a cwd that is not a string is NOT CHECKED, no traceback", (rc, out, "NOT CHECKED" in err),
         (1, "", True))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())

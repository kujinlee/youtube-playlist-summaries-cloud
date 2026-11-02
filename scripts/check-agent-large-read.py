#!/usr/bin/env python3
"""Refuse a SUBAGENT's read of more than 300 lines of a file in one call, and its re-read of lines it already read
from a file that has not changed (backlog #457).

WHY THIS EXISTS. Every line a tool call returns stays in the agent's context and is re-read at cache rates on
every later call. ESTIMATED in the 11-01 usage audit (230M weighted, 2 characters per token): Bash results over
8 KB were 5.75% of the total, and 72% of that (4.1% of the total) was FILE READS — `sed -n`, `cat` and `grep` on
`scripts/*.py` (~2.3%) and on other files (~1.8%). 57 of the 257 large reads re-read a file the same agent had
already read. The gate scripts' own output was only 0.2%. Read is gated with Bash: refusing only `cat` would move
the same bytes to the Read tool.

THE DECISION, for a PreToolUse payload (the first that applies wins):

    allow        the tool is neither Read nor Bash
    allow        the caller is not a subagent: no non-empty top-level `agent_id`. The ONE reader of that field is
                 `check-usage-pace.sent_by_subagent`, imported, never re-derived.
    NOT CHECKED  `tool_input` is not an object
    allow        Bash with `run_in_background: true` (its output goes to a file, not the context)
    NOT CHECKED  the call names a file or range this hook cannot read (below)
    deny         the call puts more than 300 lines of files into the context (`MAX_LINES`)
    deny         more than 50 of those lines (`REREAD_MAX_LINES`) were already read by the SAME agent from the
                 same path at the same modification time and size; a changed file is always allowed
    allow        otherwise; the lines read are recorded for this agent

THE READ PAYLOAD, MEASURED on Claude Code 2.1.309, 2026-11-01, with a marker hook dumping its stdin in a throwaway
`claude -p`: `tool_input` is `{file_path, offset, limit}`, and `offset` and `limit` are ABSENT when the model does
not pass them (no nulls). The main session's payload has no `agent_id`; a subagent's carries `agent_id` and
`agent_type` at the top level. A Read with no `limit` returns up to 2000 lines (`READ_DEFAULT_LIMIT`, the tool's
documented default). A binary file (a NUL byte in its first 8 KB: images, PDFs) is not counted.

WHAT BASH FORMS ARE READ. Only a command that names `cat`, `sed`, `head` or `tail` is parsed at all. It is split on
`&&`, `||`, `;`, `&` and newlines into pipelines (a heredoc's body is data, so only the first line of a command
with `<<` is read). `cd DIR` moves the directory relative paths resolve against, and `NAME=value` sets a variable
`$NAME` expands to (else the environment's). In a pipeline whose FIRST stage is `cat`, `head`, `tail` or
`sed -n 'a,bp'` on files, every later stage must be `head`, `tail`, `cat` or `sed -n 'a,bp'` for the lines to be
counted; any other later stage (`grep`, `wc`, `awk`) filters the output and the pipeline is allowed. A stage that
writes stdout to a file (`>`, `>>`) is allowed. `2>/dev/null` and `2>&1` are not output redirects.

⚠ NOT COVERED, allowed silently: `python -c "print(open(f).read())"`, `awk`, `nl`, `less`, `bat`, `xxd`, `git show`,
`git diff`, `sed` without `-n` (which prints every line), `grep` with a pattern that matches most lines, and any
reader inside `$(...)`. These are stated in the PR body (#457 re-scoped).

⚠ NOT CHECKED, ALLOWED, AND SAID (stderr, exit 1, never a deny, never a traceback): a payload that is not a JSON
object or not UTF-8, a `tool_input` that is not an object, a Read `file_path` that is not a string or an
`offset`/`limit` that is not an integral number (the payload's
integers arrive as floats: `parse_json` reads every integer as one), a command `shlex` cannot split, a `sed -n` script that is not line
ranges, and a `$VAR` with no value.

⚠ BOUNDS, stated. (1) The state is one small JSON file per agent under `<system temp>/claude-agent-reads/`, entries
older than 24 h dropped and other agents' files older than 24 h deleted. Two PARALLEL calls of one agent can lose
one record (each writes the whole file): a missed refusal, never a false one. (2) A read is recorded when the hook
ALLOWS it; if a later hook or the permission check refuses the call, its lines are recorded anyway, and a re-read
of them is refused while the file is unchanged. (3) An edit by ANOTHER process changes the modification time, so
the re-read is allowed. (4) A file of more than 300 lines is read in ranges of at most 300.

    python3 scripts/check-agent-large-read.py --hook < payload.json
    python3 scripts/check-agent-large-read.py --self-test  # 67 cases

EXIT CODES: `--hook` 0 = allowed (silent) or denied (the decision on stdout as JSON) · 1 = NOT CHECKED.

FAILS IF: a subagent's Read or `cat`/`sed -n`/`head`/`tail` call that puts more than 300 lines of a text file into
its context is allowed; or a re-read of more than 50 unchanged lines it already read is allowed; or a main-session
call, a call of at most 300 lines, a filtered pipeline, or a read of a CHANGED file is denied.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import sys
import tempfile
import time
from pathlib import Path

MAX_LINES = 300
REREAD_MAX_LINES = 50
READ_DEFAULT_LIMIT = 2000
HEAD_DEFAULT = 10
STATE_TTL_S = 24 * 3600
STATE_DIRNAME = "claude-agent-reads"
BINARY_SNIFF = 8192

_spec = importlib.util.spec_from_file_location("check_usage_pace",
                                               Path(__file__).resolve().parent / "check-usage-pace.py")
_pace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pace)
sent_by_subagent = _pace.sent_by_subagent
parse_json = _pace.parse_json

READER_WORD = re.compile(r"\b(cat|sed|head|tail)\b")
READERS = ("cat", "sed", "head", "tail")
SEPARATORS = ("&&", "||", ";", "&", ";;")
STDERR_REDIRECT = re.compile(r"(?<!\S)(\d?>&\d|2>>?\s*\S+)")
VAR = re.compile(r"\$\{(\w+)\}|\$(\w+)")
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
SED_RANGE = re.compile(r"(\d+)(?:,(\d+|\$))?p")
SED_QUIT = re.compile(r"\d*q")
COUNT = re.compile(r"\d+")
END = 10 ** 12

ADVICE = ("DO THIS INSTEAD: `grep -n '<symbol>' <file>` to find the line, then read a narrow range of at most "
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
    """`(op, files)` for one `cat`/`head`/`tail`/`sed` stage: `op(stream)` keeps the lines it prints. `op` is None
    for a stage that does not print lines of its input (`sed -i`, `sed` without `-n`, `tail -f`, `head -c`)."""
    files, it = [], iter(args)
    if word == "cat":
        files = [a for a in args if not a.startswith("-") or a == "-"]
        return (lambda s: s), files
    if word in ("head", "tail"):
        n, from_start = HEAD_DEFAULT, False
        for a in it:
            if a in ("-f", "-F", "--follow", "-c") or a.startswith(("--bytes", "-c")):
                return None, []
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
            if v.startswith("-"):  # `head -n -K`: all but the last K, so the whole file bounds it
                count_arg(v[1:])
                n = END
            else:
                n = count_arg(v.lstrip("+"))
        if word == "head":
            return (lambda s: take(s, 1, n)), files
        if from_start:
            return (lambda s: take(s, n, END)), files
        return (lambda s: take(s, size(s) - n + 1, END)), files
    quiet, script = False, None
    for a in it:
        if a.startswith("-i") or a == "--in-place" or a.startswith("--in-place="):
            return None, []
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
        return None, []
    ranges = []
    for part in re.split(r"[;\n]", script or ""):
        part = part.strip()
        if not part or SED_QUIT.fullmatch(part):
            continue
        m = SED_RANGE.fullmatch(part)
        if not m:
            raise Unreadable(f"the sed -n script {script!r} is not line ranges")
        lo = int(m.group(1))
        hi = lo if m.group(2) is None else END if m.group(2) == "$" else int(m.group(2))
        ranges.append((lo, hi))
    return (lambda s: [p for lo, hi in ranges for p in take(s, lo, hi)]), files


def expand(tok: str, vars_: dict, env: dict) -> str:
    def sub(m):
        name = m.group(1) or m.group(2)
        v = vars_.get(name, env.get(name))
        if v is None:
            raise Unreadable(f"${name} has no value here")
        return v
    if tok == "~" or tok.startswith("~/"):
        tok = env.get("HOME", "~") + tok[1:]
    return VAR.sub(sub, tok)


def bash_spans(command: str, cwd: str, env: dict) -> list:
    """The `(path, first, last)` line ranges a Bash command puts into the context."""
    if not READER_WORD.search(command):
        return []
    text = command.split("\n", 1)[0] if "<<" in command else command
    text = STDERR_REDIRECT.sub(" ", text).replace("\n", " ; ")
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError as exc:
        raise Unreadable(f"shlex cannot split the command ({exc})") from None
    segments, cur = [], []
    for t in tokens:
        if t in SEPARATORS:
            segments.append(cur)
            cur = []
        else:
            cur.append(t)
    segments.append(cur)
    vars_, spans = {}, []
    for seg in segments:
        stages, cur = [], []
        for t in seg:
            if t == "|":
                stages.append(cur)
                cur = []
            else:
                cur.append(t)
        stages.append(cur)
        first = stages[0]
        while first and ASSIGNMENT.match(first[0]):
            name, _, value = first[0].partition("=")
            if len(first) == 1 and len(stages) == 1:
                vars_[name] = expand(value, vars_, env)
            first = first[1:]
        if not first:
            continue
        if first[0] == "cd" and len(stages) == 1:
            cwd = os.path.join(cwd, expand(first[1], vars_, env)) if len(first) > 1 else env.get("HOME", cwd)
            continue
        if first[0] not in READERS or any(t in (">", ">>", "&>", ">|") for st in stages for t in st):
            continue
        later = stages[1:]
        if not all(st and st[0] in READERS for st in later):
            continue
        op, files = stage_op(first[0], first[1:])
        if op is None or not files:
            continue
        stream = []
        for f in files:
            path = os.path.join(cwd, expand(f, vars_, env))
            n = line_count(path)
            if n:
                stream += op([(os.path.realpath(path), 1, n)])
        for st in later:
            op2, _ = stage_op(st[0], st[1:])
            stream = stream if op2 is None else op2(stream)
        spans += stream
    return spans


def read_spans(ti: dict) -> list:
    """The `(path, first, last)` line range a Read call puts into the context."""
    path, offset, limit = ti.get("file_path"), ti.get("offset", 1), ti.get("limit", READ_DEFAULT_LIMIT)
    if not isinstance(path, str):
        raise Unreadable(f"its file_path {path!r} is not a string")
    for k, v in (("offset", offset), ("limit", limit)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not float(v).is_integer():
            raise Unreadable(f"its {k} {v!r} is not an integer")
    offset, limit = int(offset), int(limit)
    n = line_count(path)
    if not n:
        return []
    return take([(os.path.realpath(path), 1, n)], max(offset, 1), max(offset, 1) + max(limit, 1) - 1)


def load_state(state_dir: str, aid: str, now: float) -> tuple[Path, list]:
    """This agent's recorded reads younger than 24 h; other agents' state files older than 24 h are deleted."""
    d = Path(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.json"):
        try:
            if now - f.stat().st_mtime > STATE_TTL_S:
                f.unlink()
        except OSError:
            pass
    path = d / (re.sub(r"[^A-Za-z0-9_-]", "_", aid)[:64] + ".json")
    try:
        reads = json.loads(path.read_text())["reads"]
    except (OSError, ValueError, KeyError, TypeError):
        reads = []
    return path, [r for r in reads if isinstance(r, dict) and now - r.get("at", 0) <= STATE_TTL_S]


def decide(doc: dict, env: dict, state_dir: str, now: float) -> str | None:
    """The denial reason for a parsed PreToolUse payload, or None to allow (and record the lines read); raises
    Unreadable for NOT CHECKED."""
    tool = doc.get("tool_name")
    if tool not in ("Read", "Bash") or not sent_by_subagent(json.dumps(doc)):
        return None
    ti = doc.get("tool_input")
    if not isinstance(ti, dict):
        raise Unreadable(f"its tool_input is not an object ({type(ti).__name__})")
    if tool == "Bash":
        if ti.get("run_in_background") is True:
            return None
        cmd = ti.get("command")
        if not isinstance(cmd, str):
            raise Unreadable(f"its command {cmd!r} is not a string")
        spans = bash_spans(cmd, doc.get("cwd") or os.getcwd(), env)
    else:
        spans = read_spans(ti)
    total = size(spans)
    if total > MAX_LINES:
        return (f"⛔ REFUSED (backlog #457): this call puts {total} lines of "
                f"{', '.join(sorted({p for p, _, _ in spans}))} into your context, over {MAX_LINES}. Every line "
                "stays in your context and is re-read at cache rates on every later call. " + ADVICE)
    if not spans:
        return None
    state_path, reads = load_state(state_dir, doc["agent_id"], now)
    stats = {p: os.stat(p) for p, _, _ in spans}
    fresh = [r for r in reads if r.get("path") not in stats or
             (r.get("mtime_ns"), r.get("size")) == (stats[r["path"]].st_mtime_ns, stats[r["path"]].st_size)]
    seen = 0
    for p, a, b in spans:
        lines = set()
        for r in fresh:
            if r["path"] == p:
                lines.update(range(max(a, r["lo"]), min(b, r["hi"]) + 1))
        seen += len(lines)
    if seen > REREAD_MAX_LINES:
        return (f"⛔ REFUSED (backlog #457): you already read {seen} of these lines of "
                f"{', '.join(sorted(stats))}, and the file has not changed since (same size and modification time). "
                "They are still in your context: use them, or read only the lines you have not read. A changed file "
                "is always readable again.")
    fresh += [{"path": p, "lo": a, "hi": b, "mtime_ns": stats[p].st_mtime_ns, "size": stats[p].st_size, "at": now}
              for p, a, b in spans]
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"reads": fresh}))
    os.replace(tmp, state_path)
    return None


def main(argv: list[str] | None = None, stdin_bytes: bytes | None = None, env: dict | None = None,
         state_dir: str | None = None) -> int:
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
        reason = decide(doc, os.environ if env is None else env,
                        state_dir or os.path.join(tempfile.gettempdir(), STATE_DIRNAME), time.time())
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
    ok = fail = 0
    root = tempfile.mkdtemp(prefix="large-read-")
    big, small, b300, b301 = (os.path.join(root, f) for f in ("big.txt", "small.txt", "b300.txt", "b301.txt"))
    for path, n in ((big, 500), (small, 100), (b300, 300), (b301, 301)):
        Path(path).write_text("".join(f"line {i}\n" for i in range(1, n + 1)))
    two_a, two_b = os.path.join(root, "a.txt"), os.path.join(root, "b.txt")
    Path(two_a).write_text("x\n" * 200)
    Path(two_b).write_text("y\n" * 200)
    binary = os.path.join(root, "img.png")
    Path(binary).write_bytes(b"\x89PNG\0" + b"\n" * 1000)
    clock = [1_000_000.0]

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

    def verdict(doc, env=None, state=None):
        state = state or tempfile.mkdtemp(prefix="large-read-state-")
        clock[0] += 1
        try:
            return "deny" if decide(doc, {"HOME": root} if env is None else env, state, clock[0]) else "allow"
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
    case("a missing file is allowed (the tool reports it)", verdict(p(file_path=root + "/none.txt")), "allow")
    case("a file_path that is not a string is NOT CHECKED", verdict(p(file_path=3)), "not checked")
    case("a limit that is not an integer is NOT CHECKED (a string, a boolean)",
         [verdict(p(file_path=big, limit="300")), verdict(p(file_path=big, limit=True))], ["not checked"] * 2)
    case("a limit that is a float with a fraction, or infinite, is NOT CHECKED",
         [verdict(p(file_path=big, limit=1.5)), verdict(p(file_path=big, limit=float("inf")))], ["not checked"] * 2)
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
    case("`cat` of two 200-line files is 400 lines: denied", sh(f"cat {two_a} {two_b}"), "deny")
    case("`cat` piped to grep is allowed", sh(f"cat {big} | grep line"), "allow")
    case("`cat` piped to wc is allowed", sh(f"cat {big} | wc -l"), "allow")
    case("`cat` piped to head -n 300 is allowed, head -n 301 denied",
         [sh(f"cat {big} | head -n 300"), sh(f"cat {big} | head -n 301")], ["allow", "deny"])
    case("`cat -n` piped to sed -n '1,301p' is denied", sh(f"cat -n {big} | sed -n '1,301p'"), "deny")
    case("`cat` written to a file is allowed", sh(f"cat {big} > {root}/copy.txt"), "allow")
    case("`2>/dev/null` and `2>&1` do not hide stdout", [sh(f"cat {big} 2>/dev/null"), sh(f"cat {big} 2>&1")],
         ["deny"] * 2)
    case("a relative path after `cd DIR &&` is resolved there", sh(f"cd {root} && cat big.txt"), "deny")
    case("a relative path resolves against the payload's cwd", verdict({**p("Bash", command="cat big.txt"),
                                                                         "cwd": root}), "deny")
    case("`NAME=value;` then `$NAME/file` is expanded", sh(f"W={root}; cat $W/big.txt"), "deny")
    case("an environment variable is expanded", sh("cat ${D}/big.txt", env={"D": root}), "deny")
    case("`~/` is the environment's HOME", sh("cat ~/big.txt"), "deny")
    case("a variable with no value is NOT CHECKED", sh("cat $NOPE/big.txt"), "not checked")
    case("an unbalanced quote in a reader command is NOT CHECKED", sh(f"cat '{big}"), "not checked")
    case("a command naming no reader is not parsed: an unbalanced quote is allowed", sh("echo 'hi"), "allow")
    case("a heredoc body is data: `cat > f <<EOF` with `cat big` inside is allowed",
         sh(f"cat > {root}/out.txt <<'EOF'\ncat {big}\nEOF"), "allow")
    case("a newline separates commands", sh(f"echo hi\ncat {big}"), "deny")
    case("`sed -n '1,300p'` is allowed, '1,301p' is denied",
         [sh(f"sed -n '1,300p' {big}"), sh(f"sed -n '1,301p' {big}")], ["allow", "deny"])
    case("`sed -n '200,$p'` on 500 lines is 301: denied", sh(f"sed -n '200,$p' {big}"), "deny")
    case("`sed -n` with two ranges sums them (100 + 201)", sh(f"sed -n '1,100p;200,400p' {big}"), "deny")
    case("`sed -n -e R -e R` sums its expressions", sh(f"sed -n -e 1,100p -e 200,400p {big}"), "deny")
    case("`sed -n 'Np'` is one line", sh(f"sed -n '400p' {big}"), "allow")
    case("`sed -n` with a pattern script is NOT CHECKED", sh(f"sed -n '/def/p' {big}"), "not checked")
    case("`sed -i` edits, it does not read, even with -n and a range", sh(f"sed -n -i '1,400p' {big}"), "allow")
    case("`head` defaults to 10 lines", sh(f"head {big}"), "allow")
    case("`head -n 400`, `head -400` and `head --lines=400` are denied",
         [sh(f"head -n 400 {big}"), sh(f"head -400 {big}"), sh(f"head --lines=400 {big}")], ["deny"] * 3)
    case("`head -n -10` is every line but 10: denied", sh(f"head -n -10 {big}"), "deny")
    case("`tail -n 50` is allowed, `tail -n +100` (401 lines) is denied",
         [sh(f"tail -n 50 {big}"), sh(f"tail -n +100 {big}")], ["allow", "deny"])
    case("`tail -f` follows, it is not counted", sh(f"tail -f {big}"), "allow")
    case("a line count that is not a number is NOT CHECKED", sh(f"head -n x {big}"), "not checked")
    case("run_in_background: true is allowed", verdict(p("Bash", command=f"cat {big}", run_in_background=True)),
         "allow")
    case("the MAIN session's `cat` is never denied", verdict(p("Bash", agent=None, command=f"cat {big}")), "allow")
    case("a command that is not a string is NOT CHECKED", verdict(p("Bash", command=["cat"])), "not checked")
    # Re-reads
    st = tempfile.mkdtemp(prefix="large-read-state-")
    case("a re-read of 100 unchanged lines by the same agent is denied",
         [verdict(p(file_path=big, limit=100), state=st), verdict(p(file_path=big, limit=100), state=st)],
         ["allow", "deny"])
    case("the record crosses tools: `sed -n '1,100p'` after Read of 1-100 is denied",
         sh(f"sed -n '1,100p' {big}", state=st), "deny")
    case("another agent may read the same lines", verdict(p(agent="a2", file_path=big, limit=100), state=st), "allow")
    case("an overlap of 50 lines is allowed, 51 is denied",
         [verdict(p(file_path=big, offset=51, limit=100), state=st),
          verdict(p(file_path=big, offset=100, limit=100), state=st)], ["allow", "deny"])
    os.utime(big, ns=(os.stat(big).st_atime_ns, os.stat(big).st_mtime_ns + 10 ** 9))
    case("a CHANGED file (a new modification time) may be read again", verdict(p(file_path=big, limit=100), state=st),
         "allow")
    st2 = tempfile.mkdtemp(prefix="large-read-state-")
    case("a refused large read is not recorded: a narrow read after it is allowed",
         [verdict(p(file_path=small, agent="a3"), state=st2), verdict(p(file_path=big, agent="a3"), state=st2),
          verdict(p(file_path=big, limit=100, agent="a3"), state=st2)], ["allow", "deny", "allow"])
    clock[0] += STATE_TTL_S + 10
    case("a record older than 24 h no longer refuses", verdict(p(file_path=big, limit=100, agent="a3"), state=st2),
         "allow")
    old = Path(st2) / "zz-stale.json"
    old.write_text("{}")
    os.utime(old, (1, 1))
    verdict(p(file_path=small, agent="a3"), state=st2)
    case("another agent's state file older than 24 h is deleted", old.exists(), False)
    case("the denial names grep -n, the limit and the remedy",
         all(x in (decide(p(file_path=big), {}, tempfile.mkdtemp(), 0.0) or "")
             for x in ("grep -n", "500 lines", "offset", "300")), True)

    def drive(data, state):
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["--hook"], data, {}, state)
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}", "", ""
        return rc, out.getvalue(), err.getvalue()

    st3 = tempfile.mkdtemp(prefix="large-read-state-")
    rc, out, _ = drive(json.dumps(p(file_path=big)).encode(), st3)
    case("main --hook: a denial is the PreToolUse deny JSON at exit 0",
         (rc, json.loads(out or "{}").get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
    case("main --hook: an allowed call prints nothing at exit 0",
         drive(json.dumps(p(file_path=small)).encode(), st3)[:2], (0, ""))
    case("main --hook: a Read with offset and limit (integers parsed as floats) is judged, not NOT CHECKED",
         drive(json.dumps(p(file_path=big, offset=1, limit=100)).encode(), st3)[:2], (0, ""))
    rc, out, _ = drive(json.dumps(p(file_path=big, offset=1, limit=400)).encode(), st3)
    case("main --hook: a Read whose float limit is over 300 is denied", "deny" in out, True)
    rc, out, err = drive(b"{not json", st3)
    case("main --hook: an unreadable payload is NOT CHECKED — exit 1, said on stderr, no decision",
         (rc, out, "NOT CHECKED" in err), (1, "", True))
    rc, out, err = drive(b"\xff\xfe", st3)
    case("main --hook: a payload that is not UTF-8 is NOT CHECKED, no traceback", (rc, out, "NOT CHECKED" in err),
         (1, "", True))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())

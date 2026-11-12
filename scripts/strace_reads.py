#!/usr/bin/env python3
"""Parse one `strace -f -yy` log into resolved calls, or a named refusal (backlog #586, plan slice 2).

    python3 scripts/strace_reads.py --self-test  # 134 cases

A PURE LIBRARY, no caller yet: slice 3 classifies the calls this module resolves, slice 4 records with it. Spec:
`docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` §2, "Normalising strace's paths", and the
§8.4 normalisation cases. Every rule here is a REFUSAL, never a model (plan Global Constraints): a line, a path or
a process this module cannot place makes the whole trace INCOMPLETE with one of `REASONS`, and the target takes
today's selection.

Three steps, each its own function:
  * `parse_log` — the tokenizer. Every line is a call (`<unfinished ...>` and `<... resumed>` halves JOINED per
    pid), a signal line (`--- SIG… ---`) or an exit line (`+++ exited` / `+++ killed`), both dropped. Any other
    line is `log did not parse`, never skipped. An unpaired half is `unmatched unfinished/resumed`.
  * `process_tree` — pass one: every `clone`/`clone3`/`fork`/`vfork` return names a child, with the clone's
    ENTRY line and whether it shares the filesystem context (`CLONE_FS`). A line from a pid no clone created
    (other than the root) is `unknown pid`; a clone whose flags do not parse, or carry `CLONE_NEW*`, is
    `unmodelled clone`.
  * `resolve_calls` — pass two: the absolute path(s) each call names. A SUCCESSFUL open takes the kernel's `-yy`
    label; every other path is joined with its directory label, or with the cwd model (one cwd per shared
    filesystem context; a child without `CLONE_FS` copies its parent's cwd at the clone's entry line). Then the
    refusals of spec §2, in the order `REASONS` lists them.

⟳ ROUND 1 (PR #565), eleven fail-opens, two classes. (1) A return value and a flags operand are read as FIELDS:
`RET` is the return grammar (a label that does not close, or a last line with no newline, is `log did not parse`);
`outcome` decides success (`= ?` is unknown: a cwd change with an unknown outcome is `unknown return`, and every
other caller reads it in the direction that over-reports); `FLAG_OPERAND` names the one operand an `AT_*` flag is
read from. (2) Where the model is short of the kernel it REFUSES: `link`/`linkat` of a runtime link, `renameat2`
beyond RENAME_NOREPLACE and `openat2` RESOLVE_IN_ROOT (`unmodelled flags`), every /proc magic link incl.
`task/<tid>/`, and any cwd change whose entry-to-return window overlaps, in its filesystem context, another cwd
change, a cwd-relative call or a copying clone (`cwd race`, `_cwd_overlap`).

⟳ BACKLOG #602 (the Phase 6 review, finding P1), replacing plan Task 2.2's `external path removed` rule. The plan
refused a removal "outside the copy that no earlier call in the log created"; that creation-provenance model was
broken three times in slice 1. This module decides by LOCATION, with no per-log creation state: a SUCCESSFUL
`unlink`/`unlinkat`/`rmdir`/`rename*` (either side) whose path, resolved by the rules above (no `..` folding;
runtime and pre-existing links refused), lies outside the copy, `Ctx.home` and `Ctx.tmpdir` is `external path
removed`. A file the trace itself created there is NOT exempt. ⚠ It is only as wide as `Ctx.tmpdir`: until
slice 4 sets `TMPDIR` in the recording environment (backlog #600/#602), a suite's `/tmp` removals are outside
every allowed root and refuse.

⚠ BOUNDS, stated rather than hidden:
  * Links. A RUNTIME link is a path a `symlink`/`symlinkat` that did not fail named, or that a `rename*` that did
    not fail moved one to, taken over the WHOLE log (not only earlier lines, so a use before creation refuses too).
    A path any NON-FINAL component of which is one is refused; the final component is refused too unless the call
    does not follow it (`NOFOLLOW_FINAL`, and the calls whose `FLAG_OPERAND` carries `AT_SYMLINK_NOFOLLOW`), and a
    trailing `/` or `/.` always follows it. A `link`/`linkat` SOURCE is always checked as followed. A link that appears without
    a logged call (an `io_uring` submission: slice 3 refuses `io_uring_setup`) is invisible here. A PRE-EXISTING
    link is found only by `os.path.realpath` at parse time and only INTO the copy; a pre-existing link under
    `home` or `tmpdir` that points outside is not looked for, because both are FRESH per run (spec §2,
    `CHILD_HOME`; backlog #602, a per-run `TMPDIR`) and the copy stages no symlink (`copytree` dereferences).
  * A successful open's label is the kernel's resolution AT THAT MOMENT, so none of the link rules apply to it.
  * `..` is never folded; `.` and repeated `/` are, which cannot change what the kernel resolves.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import tempfile
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "scripts" / "fixtures" / "strace-lines"

# Every refusal this module can return, spelled as spec §2's `trace` list. Slice 3 adds its own (an unclassified
# syscall, io_uring, the mount family, ...).
REASONS: tuple[str, ...] = (
    "log did not parse",
    "unmatched unfinished/resumed",
    "unmodelled clone",
    "unknown pid",
    "undecodable path",
    "unresolved path",
    "unresolved ..",
    "unresolved /proc path",
    "unmodelled flags",
    "cwd model disagrees",
    "cwd race",
    "unknown return",
    "through a runtime link",
    "through a pre-existing link",
    "deleted label",
    "real checkout",
    "through a repo link",
    "rename in the copy",
    "external path removed",
)


@dataclass(frozen=True)
class Call:
    """One whole call. `args` is the text between `name(` and its closing `)`, both halves joined; `ret` the text
    after `= `; `label` the `-yy` decoration of the return value (`3</t/a.py>` gives `/t/a.py`), C escapes
    decoded, or None. `seq` is the log line of the call's ENTRY (its `<unfinished ...>` half when split) and `end`
    the line it completed on (`end == seq` for a one-line call)."""
    pid: int
    name: str
    args: str
    ret: str
    label: "str | None"
    seq: int
    end: int


@dataclass(frozen=True)
class Ctx:
    """Where one traced run lived. `copy` is the staged tree the suite ran in; `workspace` the real checkout
    (`$GITHUB_WORKSPACE`); `staged_roots` the staged roots, relative; `repo_links` the staged paths that are
    symlinks in R's tree, relative; `cwd0` the suite's cwd; `home` the child `HOME` and `tmpdir` the run's
    per-run `TMPDIR` (backlog #602; "" = unset, which exempts nothing)."""
    copy: str
    workspace: str
    staged_roots: "tuple[str, ...]"
    repo_links: "frozenset[str]"
    cwd0: str
    home: str
    tmpdir: str


# ── the tokenizer ───────────────────────────────────────────────────────────────────────────────────────
NAME = r"[A-Za-z_][A-Za-z_0-9]*|\?\?\?"
LINE = re.compile(rf"^(\d+)\s+(?:<\.\.\. ({NAME}) resumed>(.*)|({NAME})\((.*))$")
UNFINISHED = "<unfinished ...>"
SIGNAL = re.compile(r"^(\d+)\s+--- (?:SIG[A-Z0-9]+ \{.*\}|stopped by SIG[A-Z0-9]+) ---$")
EXITED = re.compile(r"^(\d+)\s+\+\+\+ (?:exited with \d+|killed by SIG[A-Z0-9]+(?: \(core dumped\))?) \+\+\+$")
RET_LABEL = re.compile(r"^(\d+)<(.*)>$")
# A return value: `?` (the call did not complete: `= ? ERESTARTSYS ...`, `= ? <unavailable>`), or a number with an
# optional `-yy` label that CLOSES, then optional text after a space. Anything else (`= 3</t/a` cut before its `>`)
# is `log did not parse`: a return is read as FIELDS, never searched as text (round 1, X4).
RET = re.compile(r"^(?:\?(?:\s.*)?|(?:-?\d+|0x[0-9a-fA-F]+)(?:<.*>)?(?:\s+\S.*)?)$")
ERRNO = re.compile(r"^-1 E[A-Z0-9]+(?:\s|$)")


def outcome(ret: str) -> "bool | None":
    """True if the call succeeded, False if it failed (`-1 E...`), None if the log cannot say (`= ?`, a negative
    return without an errno). Every caller decides what None means in the direction that never under-reports."""
    if ERRNO.match(ret):
        return False
    if ret.startswith("?") or ret.startswith("-"):
        return None
    return True
DEVICE = re.compile(r"<(?:char|block) \d+:\d+>$")
FORKS = ("clone", "clone3", "fork", "vfork")
OPENS = ("open", "openat", "openat2", "creat")


def scan_args(s: str) -> "tuple[list[str], int] | None":
    """The top-level arguments of `s` (the text after `name(`) and the index of their matching unquoted `)`.
    None if it never closes. Quotes, (), [], {} and -yy labels (a `<` after an alphanumeric or `]`, nesting
    inside a label) are respected. (The reader of `scripts/strace-measure.py`, slice 1.)"""
    args, cur, stack, i, n = [], [], [], 0, len(s)
    pairs = {"(": ")", "[": "]", "{": "}"}
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            if j >= n:
                return None
            cur.append(s[i:j + 1])
            i = j + 1
            if s[i:i + 3] == "...":
                cur.append("...")
                i += 3
            continue
        if c == "<" and (stack and stack[-1] == ">" or (cur and (cur[-1][-1:].isalnum() or cur[-1][-1:] == "]"))):
            stack.append(">")
        elif c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1]:
            stack.pop()
        elif not stack and c == ")":
            args.append("".join(cur).strip())
            return ([a for a in args if a != ""] if args != [""] else []), i
        elif not stack and c == ",":
            args.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    return None


SIMPLE_ESCAPES = {'"': b'"', "\\": b"\\", "n": b"\n", "t": b"\t", "r": b"\r", "v": b"\v", "f": b"\f"}


def decode_path(s: str) -> "str | None":
    """strace's C escapes in `s` (a string's content, without its quotes) decoded: `\\"`, `\\\\`, `\\n` and the
    other single-letter ones, octal `\\ooo`, `\\xHH`. None if any escape is not one of those."""
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i]
        if c != "\\":
            out += c.encode("utf-8", "surrogateescape")
            i += 1
            continue
        nxt = s[i + 1:i + 2]
        if nxt == "x":
            if not re.fullmatch(r"[0-9a-fA-F]{2}", s[i + 2:i + 4]):
                return None
            out.append(int(s[i + 2:i + 4], 16))
            i += 4
        elif nxt and nxt in "01234567":
            j = i + 1
            while j < len(s) and j < i + 4 and s[j] in "01234567":
                j += 1
            out.append(int(s[i + 1:j], 8) & 0xFF)
            i = j
        elif nxt in SIMPLE_ESCAPES and nxt:
            out += SIMPLE_ESCAPES[nxt]
            i += 2
        else:
            return None
    return os.fsdecode(bytes(out))


def ret_label(ret: str) -> "tuple[str | None, bool]":
    """The `-yy` label of a return value (`3</t/a>` → `/t/a`; a device suffix `<char 1:3>` dropped) and whether
    it decoded. A label that is not a path (`pipe:[1]`, `socket:[2]`) is returned as printed."""
    m = RET_LABEL.match(ret)
    if not m:
        return None, True
    inner = DEVICE.sub("", m.group(2))
    if not inner.startswith("/"):
        return inner, True
    decoded = decode_path(inner)
    return decoded, decoded is not None


def _call(pid: int, name: str, body: str, seq: int, end: int) -> "Call | None":
    """`body` (the text after `name(`, halves joined) as a Call, or None if it does not close with `) = ret`."""
    scanned = scan_args(body)
    if scanned is None:
        return None
    _args, close = scanned
    m = re.fullmatch(r"\s*=\s*(.*)", body[close + 1:])
    if not m:
        return None
    ret = m.group(1).strip()
    if not RET.match(ret):
        return None
    label, ok = ret_label(ret)
    if not ok:
        return Call(pid, name, body[:close], ret, None, seq, -1)
    return Call(pid, name, body[:close], ret, label, seq, end)


def parse_log(text: str) -> "tuple[list[Call], str | None]":
    """Every call in `text`, in the order it COMPLETED, or the first refusal. Signal and exit lines are dropped;
    an `<unfinished ...>` half waits for its pid's `<... name resumed>` half."""
    calls: list[Call] = []
    pending: dict = {}          # pid -> (name, the unfinished half's argument text, its line)
    for seq, line in enumerate(text.splitlines()):
        ex = EXITED.match(line)
        if ex:
            if int(ex.group(1)) in pending:    # its unfinished half can never resume
                return calls, "unmatched unfinished/resumed"
            continue
        if SIGNAL.match(line):
            continue
        m = LINE.match(line)
        if not m:
            return calls, "log did not parse"
        pid = int(m.group(1))
        if m.group(2):                                         # `<... name resumed>rest`
            head = pending.pop(pid, None)
            if head is None or head[0] != m.group(2):
                return calls, "unmatched unfinished/resumed"
            name, body, start = head[0], head[1] + m.group(3), head[2]
        else:
            name, body, start = m.group(4), m.group(5), seq
            if body.endswith(UNFINISHED):
                if pid in pending:
                    return calls, "unmatched unfinished/resumed"
                pending[pid] = (name, body[:-len(UNFINISHED)], seq)
                continue
        c = _call(pid, name, body, start, seq)
        if c is None:
            return calls, "log did not parse"
        if c.end < 0:
            return calls, "undecodable path"
        calls.append(c)
    if pending:
        return calls, "unmatched unfinished/resumed"
    if text and not text.endswith("\n"):          # the last line was cut: what it omitted cannot be known
        return calls, "log did not parse"
    return calls, None


# ── the process tree (pass one) ─────────────────────────────────────────────────────────────────────────
CLONE_FLAGS = re.compile(r"(?:^|[{\s,])flags=([^,}\s]*)")
FLAG_LIST = re.compile(r"[A-Z][A-Z0-9_]*(?:\|[A-Z][A-Z0-9_]*)*")


def clone_flags(call: Call) -> "tuple[str, ...] | None":
    """The flags of a clone/clone3 (fork and vfork take none: `()`), or None if they do not parse or create a
    namespace (`CLONE_NEW*`), which this module does not model."""
    if call.name in ("fork", "vfork"):
        return ()
    m = CLONE_FLAGS.search(call.args)
    if not m or not FLAG_LIST.fullmatch(m.group(1)):
        return None
    flags = tuple(m.group(1).split("|"))
    if any(f.startswith("CLONE_NEW") for f in flags):
        return None
    return flags


def process_tree(calls: "list[Call]", root: int) -> "tuple[dict[int, tuple[int, int, bool]], str | None]":
    """child pid → (parent pid, the clone's ENTRY line, shares the filesystem context), from every clone's return
    value; then every call's pid must be the root or a child."""
    tree: dict = {}
    for c in calls:
        if c.name not in FORKS or outcome(c.ret) is False:
            continue
        flags = clone_flags(c)
        child = re.match(r"(\d+)(?:$|\s)", c.ret)
        if flags is None or not child:
            return tree, "unmodelled clone"
        pid = int(child.group(1))
        if pid in tree or pid == root:                 # a recycled pid is not modelled
            return tree, "unmodelled clone"
        tree[pid] = (c.pid, c.seq, "CLONE_FS" in flags)
    for c in calls:
        if c.pid != root and c.pid not in tree:
            return tree, "unknown pid"
    return tree, None


# ── path resolution (pass two) ──────────────────────────────────────────────────────────────────────────
# name -> the (dirfd index or None, path index) pairs of the paths it names. A path a call only WRITES INTO (a
# readlink buffer, a symlink's target text) is not one.
PATH_ARGS: dict = {
    **{n: ((None, 0),) for n in (
        "open", "creat", "stat", "lstat", "statfs", "access", "readlink", "execve", "chdir", "truncate", "chmod",
        "chown", "lchown", "utime", "utimes", "mknod", "mkdir", "rmdir", "unlink", "getxattr", "lgetxattr",
        "listxattr", "llistxattr", "setxattr", "lsetxattr", "removexattr", "lremovexattr")},
    **{n: ((0, 1),) for n in (
        "openat", "openat2", "newfstatat", "statx", "faccessat", "faccessat2", "readlinkat", "execveat",
        "fchmodat", "fchmodat2", "fchownat", "utimensat", "futimesat", "mknodat", "mkdirat", "unlinkat")},
    "inotify_add_watch": ((None, 1),),
    "symlink": ((None, 1),),
    "symlinkat": ((1, 2),),
    "link": ((None, 0), (None, 1)),
    "linkat": ((0, 1), (2, 3)),
    "rename": ((None, 0), (None, 1)),
    "renameat": ((0, 1), (2, 3)),
    "renameat2": ((0, 1), (2, 3)),
}
REMOVERS = ("unlink", "unlinkat", "rmdir", "rename", "renameat", "renameat2")
RENAMES = ("rename", "renameat", "renameat2")
LINKS = ("symlink", "symlinkat")
HARDLINKS = ("link", "linkat")
CWD_CHANGES = ("chdir", "fchdir")
# Calls that act on a final component that is a link rather than following it. NOT `link`/`linkat`'s SOURCE: a hard
# link of a symlink is a second symlink, and `AT_SYMLINK_FOLLOW` follows it, so either way the source is checked as
# followed (round 1, X2/C5); their destination (operand 1) does not exist yet and is never followed.
NOFOLLOW_FINAL = REMOVERS + LINKS + ("lstat", "readlink", "readlinkat", "lgetxattr", "llistxattr", "lsetxattr",
                                     "lremovexattr", "lchown")
# name -> the index of its `AT_*` flags operand. The flag is read from THAT operand, parsed, never searched for in
# the argument text, where a filename can spell it (round 1, X1).
FLAG_OPERAND = {"newfstatat": 3, "statx": 2, "faccessat2": 3, "fchownat": 4, "utimensat": 3, "fchmodat2": 3,
                "execveat": 4, "linkat": 4, "renameat2": 4}
# The renameat2 flags this module models: none, or RENAME_NOREPLACE (a plain rename that may fail). RENAME_EXCHANGE
# moves the destination to the source as well, RENAME_WHITEOUT leaves a device behind: refused (round 1, C4).
RENAME_FLAGS = frozenset({"RENAME_NOREPLACE"})
# A /proc or /dev MAGIC link: it resolves against another process's state, which a path cannot show. Refused when
# anything is looked up below it, or when the call follows it; `readlink` of one reads only its text (round 1, C3).
PROC = re.compile(r"^(?:/proc/[^/]+(?:/task/[^/]+)?/(?:fd/[^/]+|cwd|root|exe|map_files/[^/]+)"
                  r"|/dev/(?:fd/[^/]+|stdin|stdout|stderr))(?=/|$)")
DIRFD = re.compile(r"^(?:(\d+)|AT_FDCWD)(?:<(.*)>)?$")
DESC = re.compile(r"^\d+<(.*)>$")


def components(path: str) -> "list[str]":
    """`path`'s components, `.` and empty ones dropped (they cannot change what the kernel resolves); `..` KEPT."""
    return [p for p in path.split("/") if p not in ("", ".")]


def norm(path: str) -> str:
    return "/" + "/".join(components(path))


def under(path: str, root: str) -> bool:
    """`path` is `root` or below it. An empty root holds nothing."""
    if not root:
        return False
    r = norm(root)
    return path == r or path.startswith(r.rstrip("/") + "/")


def rel_to_copy(path: str, ctx: Ctx) -> "str | None":
    """The staged-tree relative path of `path` (`""` for the copy itself), or None if it lies outside the copy."""
    p, c = norm(path), norm(ctx.copy)
    if p == c:
        return ""
    if p.startswith(c.rstrip("/") + "/"):
        return p[len(c.rstrip("/")) + 1:]
    return None


def _desc_path(arg: str) -> "tuple[str | None, bool]":
    """A descriptor argument's label as a path (`3</t/a>` → `/t/a`), None if it is not a path label, and whether
    it decoded."""
    m = DESC.match(arg)
    if not m:
        return None, True
    inner = DEVICE.sub("", m.group(1))
    if not inner.startswith("/"):
        return None, True
    d = decode_path(inner)
    return d, d is not None


def flag_tokens(arg: str) -> "tuple[str, ...] | None":
    """A flags operand as its names (`0` gives none), or None if it is not a `|`-list of names (`AT_X|0x100`)."""
    if arg == "0":
        return ()
    if not FLAG_LIST.fullmatch(arg):
        return None
    return tuple(arg.split("|"))


def _flags(call: Call, args: "list[str]") -> "tuple[tuple[str, ...] | None, str | None]":
    """`call`'s parsed flags operand (None if it takes none) and a refusal for a flag this module does not model."""
    if call.name == "openat2":                         # `{flags=..., resolve=...}`: RESOLVE_IN_ROOT moves `/`
        if len(args) < 3 or not args[2].startswith("{"):
            return None, "unmodelled flags"
        m = re.search(r"(?:\{|,\s*)resolve=([^,}]*)", args[2])
        toks = flag_tokens(m.group(1)) if m else ()
        if toks is None or "RESOLVE_IN_ROOT" in toks:
            return None, "unmodelled flags"
        return None, None
    if call.name not in FLAG_OPERAND:
        return None, None
    i = FLAG_OPERAND[call.name]
    toks = flag_tokens(args[i]) if i < len(args) else None
    if toks is None:
        return None, "unmodelled flags"
    if call.name == "renameat2" and not set(toks) <= RENAME_FLAGS:
        return None, "unmodelled flags"
    return toks, None


def follows_final(name: str, k: int, flags: "tuple[str, ...] | None", text: str) -> bool:
    """Whether the call named `name` follows the final component of its `k`-th path operand, spelled `text`. A
    trailing `/` or `/.` makes the kernel follow it whatever the call (round 1, C7)."""
    if text and text.split("/")[-1] in ("", ".") and components(text):
        return True
    if name in HARDLINKS:
        return k == 0
    if name in NOFOLLOW_FINAL:
        return False
    return "AT_SYMLINK_NOFOLLOW" not in (flags or ())


def _named(call: Call, args: "list[str]", cwd: str):
    """The (path, from_label, operand index, follows its final component) tuples `call` names, the cwd labels it
    carries, whether any path was resolved against the cwd, or a refusal."""
    out, cwd_labels, path_dirfds, by_cwd = [], [], set(), False
    opened = call.name in OPENS and outcome(call.ret) is True
    flags, why = _flags(call, args)
    if why:
        return None, None, False, why
    for k, (fd_i, p_i) in enumerate(PATH_ARGS.get(call.name, ())):
        if p_i >= len(args):
            return None, None, False, "undecodable path"
        base, at_cwd = cwd, True
        if fd_i is not None:
            if fd_i >= len(args):
                return None, None, False, "undecodable path"
            path_dirfds.add(fd_i)
            m = DIRFD.match(args[fd_i])
            if not m:
                return None, None, False, "unresolved path"
            at_cwd = m.group(1) is None                # AT_FDCWD, labelled or not, is the cwd
            if m.group(2) is not None:
                lab = decode_path(DEVICE.sub("", m.group(2)))
                if lab is None:
                    return None, None, False, "undecodable path"
                if not lab.startswith("/"):
                    return None, None, False, "unresolved path"
                if m.group(1) is None:
                    cwd_labels.append(lab)
                base = lab
            elif m.group(1) is not None:              # an undecorated descriptor: nothing names its directory
                base = None
        raw = args[p_i]
        if raw == "NULL" and call.name == "utimensat":
            text = ""
        else:
            q = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', raw)
            text = decode_path(q.group(1)) if q else None
            if text is None:
                return None, None, False, "undecodable path"
        if opened and call.label is not None and call.label.startswith("/"):
            continue                                   # the kernel's label stands for this path (below)
        follow = follows_final(call.name, k, flags, text)
        if text.startswith("/"):
            out.append((norm(text) if ".." not in components(text) else "/" + "/".join(components(text)),
                        False, k, follow))
        elif base is None:
            return None, None, False, "unresolved path"
        else:
            by_cwd = by_cwd or at_cwd
            out.append(("/" + "/".join(components(base) + components(text)), False, k, follow))
    for i, a in enumerate(args):
        if i in path_dirfds:
            continue
        p, ok = _desc_path(a)
        if not ok:
            return None, None, False, "undecodable path"
        if p is not None:
            out.append((p, True, -1, False))
    if call.label is not None and call.label.startswith("/"):
        out.append((call.label, True, -1, False))
    return out, cwd_labels, by_cwd, None


def _cwd_pass(calls, tree, ctx, root):
    """Pass A: every call's named paths, by the cwd model, in line order: (index → paths, or the first refusal)."""
    events = sorted([(c.seq, 0, i) for i, c in enumerate(calls)] + [(c.end, 1, i) for i, c in enumerate(calls)])
    cwd: list = []                 # context id -> cwd
    pid_ctx: dict = {}
    snapshot: dict = {}            # child pid -> its parent's cwd at the clone's entry line
    named: dict = {}
    by_cwd: set = set()            # calls that resolved a path against the cwd

    def ctx_of(pid):
        if pid in pid_ctx:
            return pid_ctx[pid]
        if pid == root:
            cwd.append(norm(ctx.cwd0))
            pid_ctx[pid] = len(cwd) - 1
        elif pid in tree:
            parent, _seq, shares = tree[pid]
            if shares:
                pc = ctx_of(parent)
                if pc is None:
                    return None
                pid_ctx[pid] = pc
            else:
                if pid not in snapshot:
                    return None
                cwd.append(snapshot[pid])
                pid_ctx[pid] = len(cwd) - 1
        else:
            return None
        return pid_ctx[pid]

    def child_of(c):
        if c.name not in FORKS:
            return None
        m = re.match(r"(\d+)(?:$|\s)", c.ret)
        if not m or int(m.group(1)) not in tree or tree[int(m.group(1))][1] != c.seq:
            return None
        return int(m.group(1))

    for _line, phase, i in events:
        c = calls[i]
        k = ctx_of(c.pid)
        if k is None:
            return named, "unknown pid"
        child = child_of(c)
        if phase == 0:
            scanned = scan_args(c.args + ")")
            if scanned is None:
                return named, "log did not parse"
            paths, cwd_labels, rel, why = _named(c, scanned[0], cwd[k])
            if why:
                return named, why
            if any(norm(lab) != cwd[k] for lab in cwd_labels):
                return named, "cwd model disagrees"
            for p, from_label, _op, follow in paths:
                if not from_label and ".." in p.split("/"):
                    return named, "unresolved .."
                magic = PROC.match(p) if not from_label else None
                if magic and (follow or len(p) > magic.end()):
                    return named, "unresolved /proc path"
            named[i] = paths
            if rel:
                by_cwd.add(i)
            if child is not None:
                snapshot[child] = cwd[k]
            continue
        if c.name in CWD_CHANGES:
            done = outcome(c.ret)
            if done is None:                          # `= ?`: the kernel may or may not have moved it
                return named, "unknown return"
            if done:
                targets = [p for p, _l, _o, _f in named[i]]
                if len(targets) != 1:
                    return named, "unresolved path"
                cwd[k] = targets[0]
    return named, _cwd_overlap(calls, tree, root, by_cwd)


def _cwd_overlap(calls, tree, root, by_cwd) -> "str | None":
    """`cwd race` if a cwd change's window (its entry line to its return line) overlaps, in the SAME filesystem
    context, another cwd change, a call that resolved a path against the cwd, or a clone whose child copies the cwd
    (round 1, X3/C1/C2). The kernel may apply a chdir at any moment in its window and resolve a path at any moment
    in the other's, so the model's one order (a path at its entry, a chdir at its return) is not the only one.
    Refused rather than modelled. Each pid's own calls never overlap one another."""
    def group(pid):
        while pid != root and pid in tree and tree[pid][2]:
            pid = tree[pid][0]
        return pid

    def copies(c):
        m = re.match(r"(\d+)(?:$|\s)", c.ret) if c.name in FORKS else None
        child = int(m.group(1)) if m else None
        return child in tree and tree[child][1] == c.seq and not tree[child][2]

    changes = [i for i, c in enumerate(calls) if c.name in CWD_CHANGES and outcome(c.ret) is not False]
    if not changes:
        return None
    hits = {i for i, c in enumerate(calls) if i in by_cwd or c.name in CWD_CHANGES or copies(c)}
    for w in changes:
        cw, g = calls[w], group(calls[w].pid)
        for i in hits:
            c = calls[i]
            if i != w and c.seq <= cw.end and cw.seq <= c.end and group(c.pid) == g:
                return "cwd race"
    return None


def _runtime_links(calls, named) -> "set[str]":
    """Every path a successful symlink named, closed over successful renames that moved it (or a directory above
    it). Over the WHOLE log: a use before the link's creation refuses too."""
    links = {named[i][0][0] for i, c in enumerate(calls)
             if c.name in LINKS and i in named and named[i] and outcome(c.ret) is not False}
    moves = [(named[i][0][0], named[i][1][0]) for i, c in enumerate(calls)
             if c.name in RENAMES and i in named and len(named[i]) >= 2 and outcome(c.ret) is not False]
    while True:
        more = {dst + link[len(src):] for src, dst in moves for link in links if under(link, src)} - links
        if not more:
            return links
        links |= more


def resolve_calls(calls: "list[Call]", tree: dict, ctx: Ctx) -> "tuple[list[tuple[Call, list[str]]], str | None]":
    """Each call with the absolute paths it names (`.git` paths dropped), or ([], the first refusal)."""
    by_line = sorted(calls, key=lambda c: c.seq)
    root = next((c.pid for c in by_line if c.pid not in tree), 0)
    named, why = _cwd_pass(calls, tree, ctx, root)
    if why:
        return [], why
    links = _runtime_links(calls, named)
    copy_real = os.path.realpath(ctx.copy)
    out = []
    for i in sorted(named, key=lambda j: calls[j].seq):
        c = calls[i]
        kept = []
        for p, from_label, op, follow in named[i]:
            if from_label:
                if p.endswith(" (deleted)"):
                    p = p[:-len(" (deleted)")]
                    if under(p, ctx.copy):
                        return [], "deleted label"
            else:
                comps = components(p)
                last = len(comps) if follow else len(comps) - 1
                if any("/" + "/".join(comps[:n]) in links for n in range(1, last + 1)):
                    return [], "through a runtime link"
                if not under(p, ctx.copy) and under(os.path.realpath(p), copy_real):
                    return [], "through a pre-existing link"
            if under(p, ctx.workspace):
                return [], "real checkout"
            rel = rel_to_copy(p, ctx)
            if rel is not None and any(under("/" + rel, "/" + link) for link in ctx.repo_links):
                return [], "through a repo link"
            if c.name in RENAMES and op >= 0 and under(p, ctx.copy):
                return [], "rename in the copy"
            if (c.name in REMOVERS and op >= 0 and outcome(c.ret) is not False
                    and not any(under(p, r) for r in (ctx.copy, ctx.home, ctx.tmpdir))):
                return [], "external path removed"
            if ".git" not in components(p):
                kept.append(p)
        out.append((c, kept))
    return out, None


def resolve_log(text: str, ctx: Ctx) -> "tuple[list[tuple[Call, list[str]]], str | None]":
    """`parse_log`, `process_tree` (the first line's pid is the root) and `resolve_calls` over `text`."""
    calls, why = parse_log(text)
    if why:
        return [], why
    if not calls:
        return [], None
    tree, why = process_tree(calls, min(calls, key=lambda c: c.seq).pid)
    if why:
        return [], why
    return resolve_calls(calls, tree, ctx)


# ── self-test ───────────────────────────────────────────────────────────────────────────────────────────
def _samples() -> dict:
    """(syscall, shape) → the recorded line, from slice 1's fixture (never typed from memory)."""
    d = json.loads((FIXTURES / "samples.json").read_text())
    out = {(s["syscall"], s["shape"]): s["line"] for s in d["samples"]}
    for s in d["shapes"]:
        out.setdefault((s["kind"], s["shape"]), s["line"])
    for i, s in enumerate(d["unnamed_syscall"]):
        out[("???", i)] = s["line"]
    return out


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(name, got_fn, want):
        nonlocal ok, fail
        try:
            got = got_fn()
        except Exception as e:      # a crash is a red case, named, never a pass
            got = f"RAISED {type(e).__name__}: {e}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

    S = _samples()

    def L(key, pid, *subs):
        """The recorded line `key`, its pid replaced and each (old, new) substituted (a case may shorten a path)."""
        line = re.sub(r"^\d+", str(pid), S[key])
        for old, new in subs:
            assert old in line, (key, old)
            line = line.replace(old, new)
        return line

    LIB = "/opt/hostedtoolcache/Python/3.12.16/x64/lib/libpython3.12.so.1.0"
    MISS = "/opt/hostedtoolcache/Python/3.12.16/x64/lib/glibc-hwcaps/x86-64-v3/libpython3.12.so.1.0"
    STAT = "/var/lib/crypto-config/profiles/current/openssl.conf.d"
    SYM = "/tmp/fixture-tmp-td74stb7/tmpk11z8pdq/.git/tt8ZTqp"
    REN = ("/tmp/fixture-tmp-3xec1v1d/tmp828gr67c/repo/.claude/plans/.one.md.backfill-tmp",
           "/tmp/fixture-tmp-3xec1v1d/tmp828gr67c/repo/.claude/plans/one.md")

    def probe(path, pid=1, cwd="/t"):          # a failed openat: a path-only call
        return L(("openat", "= -1 E"), pid, (f'"{MISS}"', f'"{path}"'), ("AT_FDCWD</t>", f"AT_FDCWD<{cwd}>"))

    def opened(arg, label, pid=1, flags="O_RDONLY|O_CLOEXEC"):   # a successful openat and its kernel label
        return L(("openat", "-yy label"), pid, (f'"{LIB}"', f'"{arg}"'), (f"3<{LIB}>", f"3<{label}>"),
                 ("O_RDONLY|O_CLOEXEC", flags))

    def stat(path, pid=1):                      # a failed stat: a cwd-relative single-path call
        return L(("stat", "= -1 E"), pid, (f'"{STAT}"', f'"{path}"'))

    def chdir(path, pid=1):
        return L(("chdir", "= N"), pid, ('"/tmp/fixture-tmp-td74stb7/tmpk11z8pdq"', f'"{path}"'))

    def symlink(target, linkpath, pid=1):
        return L(("symlink", "= N"), pid, ('"testing"', f'"{target}"'), (f'"{SYM}"', f'"{linkpath}"'))

    def unlink(path, pid=1, failed=False):
        if failed:
            return L(("unlink", "= -1 E"), pid, ('".git/logs/AUTO_MERGE"', f'"{path}"'))
        return L(("unlink", "= N"), pid, ('"/tmp/y4w8ft5b"', f'"{path}"'))

    def rename(src, dst, pid=1):
        return L(("rename", "= N"), pid, (f'"{REN[0]}"', f'"{src}"'), (f'"{REN[1]}"', f'"{dst}"'))

    def fork(parent, child):                    # a clone WITHOUT CLONE_FS, split across two lines
        return [L(("clone", "unfinished"), parent), L(("clone", "resumed"), parent, ("= 2623", f"= {child}"))]

    def thread(parent, child):                  # a CLONE_FS clone3 on one line
        return L(("clone3", "= N"), parent, ("= 3221", f"= {child}"), ("[3221]", f"[{child}]"))

    CTX = Ctx(copy="/t", workspace="/runner/work/x", staged_roots=("scripts",),
              repo_links=frozenset({"docs/alias"}), cwd0="/t", home="/t/.home", tmpdir="/tmp")

    def with_(ctx, **kw):
        return Ctx(**{**ctx.__dict__, **kw})

    def run(lines, ctx=CTX):
        """Every resolved call's paths in line order, or the refusal."""
        got, why = resolve_log("\n".join(lines) + "\n", ctx)
        return why if why else [paths for _c, paths in sorted(got, key=lambda cp: cp[0].seq)]

    def why(lines, ctx=CTX):
        return resolve_log("\n".join(lines) + "\n", ctx)[1]

    # ── Task 2.1: the tokenizer and the process tree ──
    joined = [L(("clone", "unfinished"), 2622), L(("clone", "resumed"), 2622)]
    case("a resumed line joins its unfinished half",
         lambda: [(c.name, c.ret, "child_tidptr" in c.args, c.seq, c.end) for c in parse_log("\n".join(joined))[0]],
         [("clone", "2623", True, 0, 1)])
    case("an unfinished half with no resume is refused",
         lambda: parse_log(joined[0] + "\n")[1], "unmatched unfinished/resumed")
    case("a resumed half with no unfinished half is refused",
         lambda: parse_log(joined[1] + "\n")[1], "unmatched unfinished/resumed")
    case("a resumed half of ANOTHER call is refused",
         lambda: parse_log(joined[0] + "\n" + L(("vfork", "resumed"), 2622) + "\n")[1],
         "unmatched unfinished/resumed")
    case("an unfinished half whose pid exits is refused",
         lambda: parse_log(joined[0] + "\n" + L(("exit", "exit: +++ exited with N +++"), 2622) + "\n")[1],
         "unmatched unfinished/resumed")
    # The end-of-log check would refuse the case above anyway; here a resume follows the exit (a recycled pid), so
    # only the exit check stands between the two halves and a silent join of two different processes' calls.
    case("an unfinished half whose pid exits is refused even when a resume follows",
         lambda: parse_log(joined[0] + "\n" + L(("exit", "exit: +++ exited with N +++"), 2622) + "\n"
                           + joined[1] + "\n")[1],
         "unmatched unfinished/resumed")
    case("the unnamed ??? halves join",
         lambda: [(c.name, c.ret) for c in parse_log(S[("???", 0)] + "\n" + S[("???", 1)] + "\n")[0]],
         [("???", "?")])
    sig = S[("signal", "signal: --- SIGCHLD {si_signo=SIGCHLD, si_code=CLD_EXITED, si_pid=N, si_uid=N, si_status=N, "
               "si_utime=N, si_stime=N} ---")]
    case("a signal and an exit line give no call and no reason",
         lambda: parse_log(sig + "\n" + L(("exit", "exit: +++ exited with N +++"), 2619) + "\n"), ([], None))
    case("an unknown line shape is refused, never skipped",
         lambda: parse_log(sig + "\nstrace: Process 2620 attached\n")[1], "log did not parse")
    case("a call that never closes is refused",
         lambda: parse_log(L(("unlink", "= N"), 1, (") ", " ")) + "\n")[1], "log did not parse")
    case("a return label decodes, a device suffix dropped",
         lambda: [c.label for c in parse_log(opened("/t/a", "/t/\\303\\251.py") + "\n"
                                             + L(("dup2", "-yy label"), 1) + "\n")[0]],
         ["/t/é.py", "pipe:[20851]"])
    case("a return label's device suffix is dropped",
         lambda: [c.label for c in parse_log(opened("/dev/null", "/dev/null<char 1:3>") + "\n")[0]], ["/dev/null"])
    case("a descriptor argument's device suffix is dropped",
         lambda: run([L(("dup2", "= -1 E"), 1)]), [["/dev/null"]])
    case("a second unfinished half on one pid is refused",
         lambda: parse_log("\n".join([joined[0], joined[0], joined[1]]) + "\n")[1], "unmatched unfinished/resumed")
    case("an undecodable return label is refused",
         lambda: parse_log(opened("/t/a", "/t/\\q") + "\n")[1], "undecodable path")
    case("an octal-escaped path decodes", lambda: decode_path("\\303\\251.py"), "é.py")
    case("an unknown escape does not decode", lambda: decode_path("\\q"), None)
    case("a hex escape and a quote decode", lambda: decode_path('\\x41\\"b'), 'A"b')
    case("a plain path decodes to itself", lambda: decode_path("/t/a.py"), "/t/a.py")

    early = [L(("spawn", "spawn: cloneN({flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|"
                "CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID, child_tid=X, parent_tid=X, exit_signal=N, "
                "stack=X, stack_size=X, tls=X} <L>"), 12),
             L(("getcwd", "= N"), 13),
             L(("clone3", "resumed"), 12, ("= 3256", "= 13"))]
    case("a child's lines before its parent's clone return are placed",
         lambda: process_tree(parse_log("\n".join(early))[0], 12), ({13: (12, 0, True)}, None))
    case("a fork child does not share the filesystem context",
         lambda: process_tree(parse_log("\n".join(fork(2622, 2623)))[0], 2622), ({2623: (2622, 0, False)}, None))
    case("a vfork child is placed",
         lambda: process_tree(parse_log(L(("vfork", "unfinished"), 5) + "\n"
                                        + L(("vfork", "resumed"), 5, ("= 2620", "= 6")))[0], 5),
         ({6: (5, 0, False)}, None))
    lone = [L(("getcwd", "= N"), 2547), L(("getcwd", "= N"), 999)]
    case("a pid no clone created is refused", lambda: process_tree(parse_log("\n".join(lone))[0], 2547)[1],
         "unknown pid")
    case("the root alone is not refused", lambda: process_tree(parse_log(lone[0])[0], 2547), ({}, None))
    flags = "CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD"
    case("a clone whose flags do not parse is refused",
         lambda: process_tree(parse_log("\n".join([joined[0].replace(flags, "0x1200011"), joined[1]]))[0], 2622)[1],
         "unmodelled clone")
    case("a clone into a new namespace is refused",
         lambda: process_tree(parse_log("\n".join([joined[0].replace(flags, "CLONE_NEWNS|" + flags),
                                                   joined[1]]))[0], 2622)[1], "unmodelled clone")
    case("a pid two clones returned is refused",
         lambda: process_tree(parse_log("\n".join(joined + joined))[0], 2622)[1], "unmodelled clone")
    case("a failed clone creates no child",
         lambda: process_tree(parse_log(joined[0] + "\n" + joined[1].replace(
             "= 2623", "= -1 EAGAIN (Resource temporarily unavailable)"))[0], 2622), ({}, None))

    for name in ("whole-git.log", "whole-threaded.log"):
        text = "".join((FIXTURES / name).read_text().splitlines(True)[1:])    # line 1 is the measure header
        case(f"{name} parses and resolves end to end with no reason",
             lambda text=text: (lambda r: (len(r[0]) > 1000, r[1]))(resolve_log(text, CTX)), (True, None))
        case(f"{name}: with no TMPDIR its /tmp removals are refused (backlog #602)",
             lambda text=text: resolve_log(text, with_(CTX, tmpdir=""))[1], "external path removed")

    # ── Task 2.2: the cwd model ──
    case("a relative stat after chdir joins the new cwd",
         lambda: run([chdir("/t/sub"), stat("a.py")]), [["/t/sub"], ["/t/sub/a.py"]])
    case("a relative stat before chdir joins cwd0", lambda: run([stat("a.py"), chdir("/t/sub")]),
         [["/t/a.py"], ["/t/sub"]])
    case("a fork child's relative stat uses the cwd copied at the clone's entry",
         lambda: run(fork(1, 2) + [chdir("/t/p", 1), stat("a", 2)])[-1], ["/t/a"])
    case("a fork child's own chdir moves it",
         lambda: run(fork(1, 2) + [chdir("/t/c", 2), stat("a", 2)])[-1], ["/t/c/a"])
    case("a CLONE_FS thread's chdir moves another thread's relative stat",
         lambda: run([thread(1, 2), chdir("/t/d", 2), stat("x", 1)])[-1], ["/t/d/x"])
    case("a CLONE_FS thread's chdir moves another thread's probe (its AT_FDCWD label agrees)",
         lambda: run([thread(1, 2), chdir("/t/d", 2), probe("y", 1, cwd="/t/d")])[-1], ["/t/d/y"])
    case("an AT_FDCWD label that disagrees with the model is refused",
         lambda: why([thread(1, 2), chdir("/t/d", 2), probe("y", 1, cwd="/t")]), "cwd model disagrees")
    case("a failed chdir does not move the cwd",
         lambda: run([L(("chdir", "= -1 E"), 1, ("<... chdir resumed>)", 'chdir("/t/no")')), stat("a")])[-1],
         ["/t/a"])
    race = [thread(1, 3), joined[0].replace("2622", "1", 1), chdir("/t/r", 3),
            joined[1].replace("2622", "1", 1).replace("= 2623", "= 2")]
    case("a chdir in the shared context while a fork is in flight is refused", lambda: why(race), "cwd race")
    case("a chdir after the fork returned is not a race",
         lambda: run([race[0], race[1], race[3], race[2], stat("a", 2)])[-1], ["/t/a"])
    case("openat through a directory descriptor label",
         lambda: run([L(("newfstatat", "-yy label"), 1)]),
         [["/tmp/fixture-tmp-3xec1v1d/tmpjvdpetc3/sess-aaaa1111"]])
    case("a relative path through an undecorated descriptor is refused",
         lambda: why([L(("newfstatat", "-yy label"), 1, ("3</tmp/fixture-tmp-3xec1v1d/tmpjvdpetc3>", "3"))]),
         "unresolved path")
    case("an empty path with AT_EMPTY_PATH names the descriptor itself",
         lambda: run([L(("statx", "-yy label"), 1)]), [["/usr/share/coreutils/locales/uucore/en-US.ftl"]])
    case("an undecodable argument path is refused", lambda: why([probe("/t/\\q")]), "undecodable path")

    # ── Task 2.2: the refusals of spec §2 ──
    case("a successful .. open is resolved by its label", lambda: run([opened("../t/x.py", "/t/x.py")]),
         [["/t/x.py"]])
    case("a failed .. probe is refused", lambda: why([probe("../t/x.py")]), "unresolved ..")
    case("a failed outside/link/../flag is refused", lambda: why([probe("/tmp/link/../flag")]), "unresolved ..")
    case("a . component is folded, not refused", lambda: run([probe("/t/./docs//x")]), [["/t/docs/x"]])
    case("a successful open via a since-deleted temp link gives its staged name",
         lambda: run([symlink("/t/docs/x", "/tmp/L"), opened("/tmp/L", "/t/docs/x"), unlink("/tmp/L")])[1],
         ["/t/docs/x"])
    case("a failed probe through a runtime link is refused",
         lambda: why([symlink("/t/docs", "/tmp/L"), probe("/tmp/L/x")]), "through a runtime link")
    case("a probe BEFORE the link's creation is refused too",
         lambda: why([probe("/tmp/L/x"), symlink("/t/docs", "/tmp/L")]), "through a runtime link")
    case("a probe of a sibling of a runtime link is not refused",
         lambda: run([symlink("/t/docs", "/tmp/L"), probe("/tmp/Lx/y")])[-1], ["/tmp/Lx/y"])
    case("a runtime link a rename moved is still one",
         lambda: why([symlink("/t/docs", "/tmp/L"), rename("/tmp/L", "/tmp/M"), probe("/tmp/M/x")]),
         "through a runtime link")
    case("a runtime link under a renamed directory is still one",
         lambda: why([symlink("/t/docs", "/tmp/d/L"), rename("/tmp/d", "/tmp/e"), probe("/tmp/e/L/x")]),
         "through a runtime link")
    case("a following call on the runtime link itself is refused",
         lambda: why([symlink("/t/docs", "/tmp/L"), stat("/tmp/L")]), "through a runtime link")
    case("a non-following call on the runtime link itself is not",
         lambda: run([symlink("/t/docs", "/tmp/L"), unlink("/tmp/L")]), [["/tmp/L"], ["/tmp/L"]])

    base = pathlib.Path(tempfile.mkdtemp(prefix="strace-reads-"))     # real links: macOS and Linux alike
    (base / "copy" / "docs").mkdir(parents=True)
    os.symlink("/", base / "L")
    copy = norm(str(base / "copy"))
    rctx = Ctx(copy=copy, workspace="/nonexistent-workspace", staged_roots=(), repo_links=frozenset(),
               cwd0=copy, home=copy + "/.home", tmpdir=str(base))
    case("a failed L/<copy>/docs/x with L -> / is refused (a pre-existing link)",
         lambda: why([probe(f"{base}/L{copy}/docs/x", cwd=copy)], rctx), "through a pre-existing link")
    case("a failed probe of another outside path is not refused",
         lambda: run([probe(f"{base}/other/x", cwd=copy)], rctx), [[f"{base}/other/x"]])
    case("#602: a probe through a pre-existing link, then its unlink outside every root, is refused",
         lambda: why([probe(f"/var/L{copy}/docs/value", cwd=copy), unlink("/var/L")], rctx),
         "external path removed")

    case("a read under a repo link is refused", lambda: why([probe("/t/docs/alias/x")]), "through a repo link")
    case("a read beside a repo link is counted", lambda: run([probe("/t/docs/aliasx")]), [["/t/docs/aliasx"]])
    case("a path under the workspace is the real checkout",
         lambda: why([probe("/runner/work/x/scripts/a.py")]), "real checkout")
    case("a path beside the workspace is not", lambda: run([probe("/runner/work/xy/a.py")]),
         [["/runner/work/xy/a.py"]])
    case("a /proc/*/fd path with no label is refused", lambda: why([probe("/proc/self/fd/3")]),
         "unresolved /proc path")
    case("a /proc/*/cwd path with no label is refused", lambda: why([stat("/proc/12/cwd/a")]),
         "unresolved /proc path")
    case("a successful /proc/*/fd open is resolved by its label",
         lambda: run([opened("/proc/self/fd/3", "/t/a.py")]), [["/t/a.py"]])
    case("another /proc path is not refused", lambda: run([probe("/proc/self/status")]), [["/proc/self/status"]])
    fstat = L(("fstat", "-yy label"), 1)
    case("a deleted label in the copy is refused",
         lambda: why([fstat.replace(f"3<{LIB}>", "3</t/a.py (deleted)>")]), "deleted label")
    case("a deleted label outside the copy is stripped",
         lambda: run([fstat.replace(f"3<{LIB}>", "3</tmp/a.py (deleted)>")]), [["/tmp/a.py"]])
    case("a rename with a side in the copy is refused", lambda: why([rename("/tmp/a", "/t/b")]),
         "rename in the copy")
    case("a rename between two /tmp paths is not", lambda: run([rename("/tmp/a", "/tmp/b")]),
         [["/tmp/a", "/tmp/b"]])
    case("a .git path in a temp repo is dropped, the same process's working-tree read counted",
         lambda: run([probe("/tmp/r/.git/HEAD"), probe("/tmp/r/file")]), [[], ["/tmp/r/file"]])
    case(".github and .githooks are ordinary",
         lambda: run([probe("/t/.github/workflows/ci.yml"), probe("/t/.githooks/pre-push")]),
         [["/t/.github/workflows/ci.yml"], ["/t/.githooks/pre-push"]])

    # ── backlog #602: the stateless location rule for `external path removed` ──
    case("#602: a remover through a runtime link is refused",
         lambda: why([symlink("/var", "/tmp/L"), unlink("/tmp/L/x")]), "through a runtime link")
    case("#602: an O_CREAT open without O_EXCL, then an unlink outside the roots, is refused",
         lambda: why([opened("/var/x", "/var/x", flags="O_WRONLY|O_CREAT|O_TRUNC"), unlink("/var/x")]),
         "external path removed")
    case("#602: the same unlink with no earlier creation gives the same answer",
         lambda: why([unlink("/var/x")]), "external path removed")
    case("#602: an unlink under TMPDIR is not refused",
         lambda: run([opened("/tmp/x", "/tmp/x", flags="O_WRONLY|O_CREAT|O_TRUNC"), unlink("/tmp/x")]),
         [["/tmp/x"], ["/tmp/x"]])
    case("#602: an unlink under the child HOME is not refused",
         lambda: run([unlink("/w/.home/x")], with_(CTX, home="/w/.home")), [["/w/.home/x"]])
    case("#602: an unlink in the copy is not refused", lambda: run([unlink("/t/scratch")]), [["/t/scratch"]])
    case("#602: a rename whose destination is outside is refused",
         lambda: why([rename("/tmp/new", "/var/L")]), "external path removed")
    case("#602: a rename whose source is outside is refused",
         lambda: why([rename("/var/L", "/tmp/x")]), "external path removed")
    case("#602: an rmdir outside is refused",
         lambda: why([L(("rmdir", "= N"), 1, ("/tmp/fixture-tmp-3xec1v1d/tmp2bbtqwnp", "/var/d"))]),
         "external path removed")
    case("#602: an unlinkat through a dirfd outside is refused",
         lambda: why([L(("unlinkat", "-yy label"), 1, ("3</tmp/fixture-tmp-3xec1v1d", "3</var/fixture"))]),
         "external path removed")
    case("#602: a failed unlink is not a removal and is not refused",
         lambda: run([unlink("/var/x", failed=True)]), [["/var/x"]])
    case("#602: a TMPDIR that is unset exempts nothing",
         lambda: why([unlink("/tmp/x")], with_(CTX, tmpdir="")), "external path removed")

    # ── round 1 (PR #565): every reviewer input, each a fail-open on the slice-2 head, then the adjacent probes ──
    ENOENT = "= -1 ENOENT (No such file or directory)"

    def succeeds(line):                               # the same line, returning success
        assert ENOENT in line, line
        return line.replace(ENOENT, "= 0")

    def link(src, dst, pid=1):
        return L(("link", "= N"), pid, ('".git/objects/c1/tmp_obj_oaWls9"', f'"{src}"'),
                 ('".git/objects/c1/b0730e0133447badcfd47fd144e254807b06e1"', f'"{dst}"'))

    LK = ("/tmp/fixture-tmp-ui1umrq2/tmpv8wu6lj0/late",
          "/tmp/fixture-tmp-ui1umrq2/fixture-home-hslp48gl/.local/state/gh/device-id")

    def linkat(src, dst, flags, pid=1, src_fd="AT_FDCWD</t>"):
        return L(("linkat", "= N"), pid, (f'AT_FDCWD<{LK[0]}>, "{LK[1]}.tmp.985797497"', f'{src_fd}, "{src}"'),
                 (f'AT_FDCWD<{LK[0]}>, "{LK[1]}", 0)', f'AT_FDCWD</t>, "{dst}", {flags})'))

    RA = "4</tmp/fixture-tmp-ui1umrq2/tmpv8wu6lj0/killed/.remember/compaction/S-kill>"

    def renameat2(src, dst, flags, pid=1):
        return L(("renameat", "= N"), pid, ("renameat(", "renameat2("), (RA, "AT_FDCWD</t>"),
                 ('".receipt.json.7078.fcef515a"', f'"{src}"'), ('"receipt.json")', f'"{dst}", {flags})'))

    def mkdir(path, pid=1):
        return L(("mkdir", "= N"), pid, ('"/tmp/fixture-tmp-3xec1v1d"', f'"{path}"'))

    def readlink(path, pid=1):                   # a call that does NOT follow its final component
        return L(("readlink", "= -1 E"), pid, ('"/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3.12"', f'"{path}"'))

    def nfstatat(path, flags, pid=1):            # newfstatat(AT_FDCWD</t>, path, buf, flags)
        return L(("newfstatat", "= -1 E"), pid, ('"/opt/hostedtoolcache/Python/3.12.16/x64/lib/glibc-hwcaps/x86-64-v3/"',
                                                  f'"{path}"'), ("0x7ffd417b73e0, 0)", f"0x7ffd417b73e0, {flags})"))

    def statx(path, flags, pid=1):
        return L(("statx", "= -1 E"), pid, ('"/t/scripts/node_modules/typescript"', f'"{path}"'),
                 ("AT_STATX_SYNC_AS_STAT,", f"{flags},"))

    def split_access(path, pid=1):               # a path-only call split across two lines
        return [L(("access", "unfinished"), pid, ('"/etc/ld.so.preload"', f'"{path}"')),
                L(("access", "resumed"), pid)]

    def split_chdir(path, pid=1, name="chdir", ret=None):
        head = L(("chdir", "unfinished"), pid, ('"/tmp/fixture-tmp-td74stb7/tmpk11z8pdq"', f'"{path}"'))
        tail = L(("chdir", "resumed"), pid)
        if name == "fchdir":
            head = head.replace(f'chdir("{path}"', f"fchdir(3<{path}>")
            tail = tail.replace("chdir", "fchdir")
        if ret is not None:
            tail = tail.replace("= 0", ret)
        return [head, tail]

    def fchdir(path, pid=1):
        return L(("fstat", "-yy label"), pid, (f"fstat(3<{LIB}>, {{st_mode=S_IFREG|0777, st_size=29948232, ...}})",
                                               f"fchdir(3<{path}>)"))

    def oneline_fork(parent, child):            # a one-line clone WITHOUT CLONE_FS
        return L(("clone", "unfinished"), parent, (" <unfinished ...>", f", child_tidptr=0x79c7f31b6e50) = {child}"))

    RUN = with_(CTX, tmpdir="/tmp/run", repo_links=frozenset())

    # Root class 1: text read where the meaning is structural.
    case("X1: a link NAMED AT_SYMLINK_NOFOLLOW is still followed by stat",
         lambda: why([symlink("/t/scripts/needed.py", "/tmp/run/AT_SYMLINK_NOFOLLOW"),
                      succeeds(stat("/tmp/run/AT_SYMLINK_NOFOLLOW")), unlink("/tmp/run/AT_SYMLINK_NOFOLLOW")], RUN),
         "through a runtime link")
    trunc = opened("/tmp/run/preexisting-link/needed.py", "/t/scripts/needed.py", flags="O_RDONLY")[:-1]
    case("X4: a log truncated inside a return label is refused", lambda: resolve_log(trunc, RUN)[1],
         "log did not parse")
    case("X4: a return label missing its > is refused even on a whole line",
         lambda: why([trunc], RUN), "log did not parse")
    case("C6: chdir = ? ERESTARTSYS is not applied (an unknown cwd change is refused)",
         lambda: why([chdir("/t/sub").replace("= 0", "= ? ERESTARTSYS (To be restarted if SA_RESTART is set)"),
                      stat("a.py")], RUN), "unknown return")
    case("C6: a resumed chdir = ? <unavailable> is refused",
         lambda: why(split_chdir("/t/sub", ret="= ? <unavailable>") + [stat("a.py")], RUN), "unknown return")
    case("C7: a trailing slash follows a final runtime link (readlink L/)",
         lambda: why([symlink("/t/sub", "/tmp/run/L"), readlink("/tmp/run/L/")], RUN), "through a runtime link")
    # Root class 2: a model of the kernel that is short of it.
    case("X2: link() of a runtime symlink is refused",
         lambda: why([symlink("/t/scripts", "/tmp/run/L"), link("/tmp/run/L", "/tmp/run/M"),
                      succeeds(stat("/tmp/run/M/needed.py")), unlink("/tmp/run/M"), unlink("/tmp/run/L")], RUN),
         "through a runtime link")
    case("C5a: link() of a runtime symlink to the copy root is refused",
         lambda: why([symlink("/t", "/tmp/run/A"), link("/tmp/run/A", "/tmp/run/A2"),
                      succeeds(stat("/tmp/run/A2/a.py"))], RUN), "through a runtime link")
    case("C5b: linkat(AT_SYMLINK_FOLLOW) through a runtime link is refused",
         lambda: why([symlink("/t/a.py", "/tmp/run/L"), linkat("/tmp/run/L", "/tmp/run/H", "AT_SYMLINK_FOLLOW"),
                      opened("/tmp/run/H", "/tmp/run/H")], RUN), "through a runtime link")
    case("C4: renameat2 RENAME_EXCHANGE is refused",
         lambda: why([symlink("/t", "/tmp/run/A"), mkdir("/tmp/run/B"),
                      renameat2("/tmp/run/B", "/tmp/run/A", "RENAME_EXCHANGE"), succeeds(stat("/tmp/run/B/a.py"))], RUN),
         "unmodelled flags")
    case("C3: /proc/self/task/<tid>/cwd is refused", lambda: why([succeeds(stat("/proc/self/task/1/cwd/a.py"))], RUN),
         "unresolved /proc path")
    case("C3: /proc/<pid>/task/<tid>/fd/N is refused", lambda: why([succeeds(stat("/proc/1/task/1/fd/3/a.py"))], RUN),
         "unresolved /proc path")
    case("X3: a relative call in flight across a CLONE_FS sibling's chdir is a cwd race",
         lambda: why([thread(1, 2), split_access("needed.py", 1)[0], chdir("/t/scripts", 2),
                      split_access("needed.py", 1)[1]], RUN), "cwd race")
    case("C1: a chdir in flight across a CLONE_FS sibling's relative call is a cwd race",
         lambda: why([thread(1, 2), split_chdir("/t/sub", 1)[0], stat("a.py", 2), split_chdir("/t/sub", 1)[1]], RUN),
         "cwd race")
    case("C2: a chdir in flight across a sibling's whole fork is a cwd race",
         lambda: why([thread(1, 2), split_chdir("/t/sub", 1)[0], oneline_fork(2, 3), split_chdir("/t/sub", 1)[1],
                      stat("a.py", 3)], RUN), "cwd race")

    # Adjacent probes, the class rather than the sample.
    case("adjacent: a newfstatat path NAMED AT_SYMLINK_NOFOLLOW with flags 0 follows",
         lambda: why([symlink("/t", "/tmp/run/AT_SYMLINK_NOFOLLOW"), nfstatat("/tmp/run/AT_SYMLINK_NOFOLLOW", "0")],
                     RUN), "through a runtime link")
    case("adjacent: a real AT_SYMLINK_NOFOLLOW operand on the link itself is not refused",
         lambda: run([symlink("/t", "/tmp/run/L"), nfstatat("/tmp/run/L", "AT_SYMLINK_NOFOLLOW")], RUN)[-1],
         ["/tmp/run/L"])
    case("adjacent: a statx flag operand that does not parse is refused",
         lambda: why([statx("/tmp/run/x", "AT_STATX_SYNC_AS_STAT|0x100")], RUN), "unmodelled flags")
    case("adjacent: renameat2 RENAME_WHITEOUT is refused",
         lambda: why([renameat2("/tmp/run/B", "/tmp/run/A", "RENAME_WHITEOUT")], RUN), "unmodelled flags")
    case("adjacent: a file NAMED RENAME_EXCHANGE renamed with RENAME_NOREPLACE is modelled (the move tracked)",
         lambda: why([symlink("/t", "/tmp/run/RENAME_EXCHANGE"),
                      renameat2("/tmp/run/RENAME_EXCHANGE", "/tmp/run/C", "RENAME_NOREPLACE"),
                      succeeds(stat("/tmp/run/C/a.py"))], RUN), "through a runtime link")
    case("adjacent: linkat(AT_EMPTY_PATH) of a descriptor ON a runtime link is refused",
         lambda: why([symlink("/t", "/tmp/run/L"), linkat("", "/tmp/run/M", "AT_EMPTY_PATH",
                                                          src_fd="3</tmp/run/L>")], RUN), "through a runtime link")
    case("adjacent: linkat without a flag, of a runtime link, is refused",
         lambda: why([symlink("/t", "/tmp/run/L"), linkat("/tmp/run/L", "/tmp/run/M", "0")], RUN),
         "through a runtime link")
    case("adjacent: a hard link of an ordinary temp file is not refused",
         lambda: run([link("/tmp/run/f", "/tmp/run/g")], RUN), [["/tmp/run/f", "/tmp/run/g"]])
    case("adjacent: an fchdir in flight across a sibling's relative call is a cwd race",
         lambda: why([thread(1, 2), split_chdir("/t/sub", 1, name="fchdir")[0], stat("a.py", 2),
                      split_chdir("/t/sub", 1, name="fchdir")[1]], RUN), "cwd race")
    case("adjacent: two CLONE_FS siblings' chdirs in flight together are a cwd race",
         lambda: why([thread(1, 2), split_chdir("/t/a", 1)[0], chdir("/t/b", 2), split_chdir("/t/a", 1)[1]], RUN),
         "cwd race")
    case("adjacent: an AT_FDCWD-relative probe in flight across a sibling's chdir is a cwd race",
         lambda: why([thread(1, 2), split_chdir("/t/sub", 1)[0], probe("a.py", 2), split_chdir("/t/sub", 1)[1]], RUN),
         "cwd race")
    case("adjacent: an absolute call across a sibling's chdir is not a race",
         lambda: run([thread(1, 2), split_chdir("/t/sub", 1)[0], stat("/t/a.py", 2), split_chdir("/t/sub", 1)[1]],
                     RUN)[2], ["/t/a.py"])
    case("adjacent: a relative call across a chdir in ANOTHER (forked) context is not a race",
         lambda: run(fork(1, 2) + [split_chdir("/t/sub", 2)[0], stat("a.py", 1), split_chdir("/t/sub", 2)[1]],
                     RUN)[2], ["/t/a.py"])
    case("adjacent: fchdir = ? is refused",
         lambda: why([fchdir("/t/sub").replace("= 0", "= ? ERESTARTSYS (To be restarted if SA_RESTART is set)")], RUN),
         "unknown return")
    case("adjacent: a successful fchdir moves the cwd",
         lambda: run([fchdir("/t/sub"), stat("a.py")], RUN)[-1], ["/t/sub/a.py"])
    case("adjacent: /proc/thread-self/cwd is refused", lambda: why([succeeds(stat("/proc/thread-self/cwd/a.py"))], RUN),
         "unresolved /proc path")
    case("adjacent: /proc/self/task/<tid>/root is refused",
         lambda: why([succeeds(stat("/proc/self/task/7/root/t/a.py"))], RUN), "unresolved /proc path")
    case("adjacent: following /proc/self/exe is refused", lambda: why([succeeds(stat("/proc/self/exe"))], RUN),
         "unresolved /proc path")
    case("adjacent: readlink of /proc/self/exe reads only the link text and is not refused",
         lambda: run([readlink("/proc/self/exe")], RUN), [["/proc/self/exe"]])
    case("adjacent: a readlink BELOW a /proc magic link is refused (non-final, though the call does not follow)",
         lambda: why([readlink("/proc/self/cwd/L")], RUN), "unresolved /proc path")
    case("adjacent: /proc/self/task/<tid>/status is an ordinary file",
         lambda: run([succeeds(stat("/proc/self/task/1/status"))], RUN), [["/proc/self/task/1/status"]])
    case("adjacent: a log whose last line has no newline is refused (truncated)",
         lambda: resolve_log(stat("/tmp/run/x"), RUN)[1], "log did not parse")
    case("adjacent: a descriptor return label cut before its > is refused",
         lambda: why([L(("dup2", "-yy label"), 1)[:-1]], RUN), "log did not parse")
    case("adjacent: a trailing /. follows a final runtime link",
         lambda: why([symlink("/t/sub", "/tmp/run/L"), readlink("/tmp/run/L/.")], RUN), "through a runtime link")
    case("adjacent: a remover with a trailing slash follows a final runtime link",
         lambda: why([symlink("/t/sub", "/tmp/run/L"), unlink("/tmp/run/L/")], RUN), "through a runtime link")
    case("adjacent: a symlink = ? ERESTARTSYS still counts as a runtime link",
         lambda: why([symlink("/t", "/tmp/run/L").replace("= 0", "= ? ERESTARTSYS (To be restarted)"),
                      stat("/tmp/run/L/a.py")], RUN), "through a runtime link")
    case("adjacent: openat2 RESOLVE_IN_ROOT is refused (an absolute path is under the dirfd)",
         lambda: why([L(("openat", "= -1 E"), 1, ("openat(", "openat2("), ("O_RDONLY|O_CLOEXEC)",
                                                                           "{flags=O_RDONLY, resolve=RESOLVE_IN_ROOT}, 24)"))], RUN),
         "unmodelled flags")

    case("rel_to_copy: the copy itself", lambda: rel_to_copy("/t", CTX), "")
    case("rel_to_copy: a path under it", lambda: rel_to_copy("/t/scripts/a.py", CTX), "scripts/a.py")
    case("rel_to_copy: a sibling with the copy as prefix is outside", lambda: rel_to_copy("/tx/a", CTX), None)
    case("rel_to_copy: a deeper copy with a trailing slash",
         lambda: rel_to_copy("/w/c/docs/a.md", with_(CTX, copy="/w/c/")), "docs/a.md")
    case("norm folds . and doubled slashes", lambda: norm("/a/./b//c/"), "/a/b/c")

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    print("usage: strace_reads.py --self-test  (a library: slice 3 and slice 4 import it)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

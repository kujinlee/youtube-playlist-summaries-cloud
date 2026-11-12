#!/usr/bin/env python3
"""Parse one `strace -f -yy` log into resolved calls, or a named refusal (backlog #586, plan slice 2).

    python3 scripts/strace_reads.py --self-test  # 92 cases

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

⟳ BACKLOG #602 (the Phase 6 review, finding P1), replacing plan Task 2.2's `external path removed` rule. The plan
refused a removal "outside the copy that no earlier call in the log created"; that creation-provenance model was
broken three times in slice 1. This module decides by LOCATION, with no per-log creation state: a SUCCESSFUL
`unlink`/`unlinkat`/`rmdir`/`rename*` (either side) whose path, resolved by the rules above (no `..` folding;
runtime and pre-existing links refused), lies outside the copy, `Ctx.home` and `Ctx.tmpdir` is `external path
removed`. A file the trace itself created there is NOT exempt. ⚠ It is only as wide as `Ctx.tmpdir`: until
slice 4 sets `TMPDIR` in the recording environment (backlog #600/#602), a suite's `/tmp` removals are outside
every allowed root and refuse.

⚠ BOUNDS, stated rather than hidden:
  * Links. A RUNTIME link is a path a successful `symlink`/`symlinkat` named, or that a successful `rename*`
    moved one to, taken over the WHOLE log (not only earlier lines, so a use before creation refuses too). A path
    any NON-FINAL component of which is one is refused; the final component is refused too unless the call does
    not follow it (`NOFOLLOW_FINAL`, and `*at` calls passing `AT_SYMLINK_NOFOLLOW`). A link that appears without
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
    "cwd model disagrees",
    "cwd race",
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
        if c.name not in FORKS or c.ret.startswith("-1 "):
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
# Calls that act on a final component that is a link rather than following it.
NOFOLLOW_FINAL = REMOVERS + LINKS + ("lstat", "readlink", "readlinkat", "lgetxattr", "llistxattr", "lsetxattr",
                                     "lremovexattr", "lchown", "link", "linkat")
PROC = re.compile(r"^/proc/[^/]+/(?:fd/[^/]+|cwd|root)(?:/|$)|^/dev/(?:fd/[^/]+|stdin|stdout|stderr)(?:/|$)")
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


def _named(call: Call, args: "list[str]", cwd: str):
    """The (path, from_label, operand index) triples `call` names, the cwd labels it carries, or a refusal."""
    out, cwd_labels, path_dirfds = [], [], set()
    opened = call.name in OPENS and not call.ret.startswith("-1 ")
    for k, (fd_i, p_i) in enumerate(PATH_ARGS.get(call.name, ())):
        if p_i >= len(args):
            return None, None, "undecodable path"
        base = cwd
        if fd_i is not None:
            if fd_i >= len(args):
                return None, None, "undecodable path"
            path_dirfds.add(fd_i)
            m = DIRFD.match(args[fd_i])
            if not m:
                return None, None, "unresolved path"
            if m.group(2) is not None:
                lab = decode_path(DEVICE.sub("", m.group(2)))
                if lab is None:
                    return None, None, "undecodable path"
                if not lab.startswith("/"):
                    return None, None, "unresolved path"
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
                return None, None, "undecodable path"
        if opened and call.label is not None and call.label.startswith("/"):
            continue                                   # the kernel's label stands for this path (below)
        if text.startswith("/"):
            out.append((norm(text) if ".." not in components(text) else "/" + "/".join(components(text)),
                        False, k))
        elif base is None:
            return None, None, "unresolved path"
        else:
            out.append(("/" + "/".join(components(base) + components(text)), False, k))
    for i, a in enumerate(args):
        if i in path_dirfds:
            continue
        p, ok = _desc_path(a)
        if not ok:
            return None, None, "undecodable path"
        if p is not None:
            out.append((p, True, -1))
    if call.label is not None and call.label.startswith("/"):
        out.append((call.label, True, -1))
    return out, cwd_labels, None


def _cwd_pass(calls, tree, ctx, root):
    """Pass A: every call's named paths, by the cwd model, in line order: (index → paths, or the first refusal)."""
    events = sorted([(c.seq, 0, i) for i, c in enumerate(calls)] + [(c.end, 1, i) for i, c in enumerate(calls)])
    cwd: list = []                 # context id -> cwd
    pid_ctx: dict = {}
    snapshot: dict = {}            # child pid -> its parent's cwd at the clone's entry line
    open_copies: dict = {}         # context id -> clones in flight whose child COPIES the context
    named: dict = {}

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
            paths, cwd_labels, why = _named(c, scanned[0], cwd[k])
            if why:
                return named, why
            if any(norm(lab) != cwd[k] for lab in cwd_labels):
                return named, "cwd model disagrees"
            for p, from_label, _op in paths:
                if not from_label and ".." in p.split("/"):
                    return named, "unresolved .."
                if not from_label and PROC.match(p):
                    return named, "unresolved /proc path"
            named[i] = paths
            if child is not None:
                snapshot[child] = cwd[k]
                if not tree[child][2]:
                    open_copies[k] = open_copies.get(k, 0) + 1
            continue
        if child is not None and not tree[child][2]:
            open_copies[k] -= 1
        if c.name in ("chdir", "fchdir") and not c.ret.startswith("-1 "):
            if open_copies.get(k, 0) > 0:
                return named, "cwd race"
            targets = [p for p, _l, _o in named[i]]
            if len(targets) != 1:
                return named, "unresolved path"
            cwd[k] = targets[0]
    return named, None


def _runtime_links(calls, named) -> "set[str]":
    """Every path a successful symlink named, closed over successful renames that moved it (or a directory above
    it). Over the WHOLE log: a use before the link's creation refuses too."""
    links = {named[i][0][0] for i, c in enumerate(calls)
             if c.name in LINKS and i in named and named[i] and not c.ret.startswith("-1 ")}
    moves = [(named[i][0][0], named[i][1][0]) for i, c in enumerate(calls)
             if c.name in RENAMES and i in named and len(named[i]) >= 2 and not c.ret.startswith("-1 ")]
    while True:
        more = {dst + link[len(src):] for src, dst in moves for link in links if under(link, src)} - links
        if not more:
            return links
        links |= more


def _follows_final(call: Call) -> bool:
    return call.name not in NOFOLLOW_FINAL and "AT_SYMLINK_NOFOLLOW" not in call.args


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
        for p, from_label, op in named[i]:
            if from_label:
                if p.endswith(" (deleted)"):
                    p = p[:-len(" (deleted)")]
                    if under(p, ctx.copy):
                        return [], "deleted label"
            else:
                comps = components(p)
                last = len(comps) if _follows_final(c) else len(comps) - 1
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
            if (c.name in REMOVERS and op >= 0 and not c.ret.startswith("-1 ")
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
    sys.path.insert(0, str(ROOT / "scripts"))
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

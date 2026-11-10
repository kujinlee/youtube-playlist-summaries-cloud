#!/usr/bin/env python3
"""Measure strace on the runner: what every manifest target's `--self-test` does under `strace -f -yy`.

    python3 scripts/strace-measure.py --shard I/N --seeds A,B --out DIR   # writes DIR/shard-I.json (+ raw lines)
    python3 scripts/strace-measure.py --merge DIR... --out FILE [--jobs JOBS.json]   # the merged summary
    python3 scripts/strace-measure.py --self-test   # the log reader's rules, offline

A MEASUREMENT INSTRUMENT, not a guard (backlog #586 plan, slice 1, Task 1.1); its one caller is
`.github/workflows/strace-measure.yml`, which runs the self-test before measuring. Its output is reviewed by
hand, and slice 3's subset case pins what the parser's tables may hold against it. It supplies the constants the
later slices pin: `STRACE_VERSION`, `MEASURED_SYSCALLS`, `MEASURED_IOCTLS`, `TRACE_FACTOR`, whether `-yy` decorates
`AT_FDCWD`, and which suites trip a refusal trigger (spec §2, "The build plan's FIRST step").

NO-MUTATIONS: a one-shot measurement instrument whose output is a reviewed measurement document that nothing gates on; its self-test cases the log reader against the review's constructed inputs and recorded lines, each shown red on the pre-fix reader when written (review round 1), and slice 2 re-implements the reader with its own mutated suite.

Per target in the shard, per seed: a PLAIN run, then a TRACED run (`strace -f -yy -o <log> python3 <target>
--self-test`), each in a FRESH `stage_tree` copy with a fresh `CHILD_HOME`, under `mutation_env(copy, seed)`,
timeout `SUITE_TIMEOUT * 10`. The harness's own pieces are loaded with importlib (the spike's method), so the
staged tree, the environment and the green test are exactly the ones `--mutate` uses.

⚠ WHAT IT DOES NOT DO. It does not parse paths into read sets (slice 2 does, from the raw lines kept here),
and it tracks no cwd: a relative unlink/rename/rmdir whose directory it cannot name from a `-yy` label is listed
as UNRESOLVED, never guessed to be inside or outside the copy. EVERY unlink/rename (both sides)/rmdir whose path
resolves outside the copy is LISTED; nothing is exempted (review round 2, Codex X1: twice, creation-provenance
EXEMPTION hid an external removal, so the exemption is gone, not patched). Each listed removal carries
`created_in_log`, an ANNOTATION from creation EVIDENCE (`removed_and_created`): a successful `O_CREAT|O_EXCL` open,
`mkdir*`, `mknod*`, `link*`, `symlink*`, or a successful `rename*` whose source was itself created; a path under a
created DIRECTORY is created too. A successful removal, a rename's source and a replaced destination CLEAR the
evidence for that path and its subtree, so the annotation is not stale; correctness no longer depends on it. Slice
2 decides its refusal rule from the list. An `<unfinished ...>` half is JOINED with its pid's `<... resumed>` half
before its arguments and result are read; an unpaired half (including one still pending at its pid's `+++ exited`
or `+++ killed`) is counted (`unpaired_halves`), never dropped.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import math
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_harness():
    """`check-plan-code.py` as a module. Registered in `sys.modules` before exec: its dataclasses need it."""
    spec = importlib.util.spec_from_file_location("check_plan_code", ROOT / "scripts" / "check-plan-code.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_plan_code"] = mod
    spec.loader.exec_module(mod)
    return mod


# ── the log ─────────────────────────────────────────────────────────────────────────────────────────────
# `strace -f -o FILE` prefixes every line with the pid. A call either completes on its line, or is split
# into `name(args <unfinished ...>` and a later `<... name resumed>rest` on the SAME pid; the two halves are
# JOINED before the arguments and the result are read. `???` is a name strace prints when it cannot read the
# syscall number (a thread exiting mid-call; recorded in run 42901768433).
NAME = r"[A-Za-z_][A-Za-z_0-9]*|\?\?\?"
LINE = re.compile(rf"^(\d+)\s+(?:<\.\.\. ({NAME}) resumed>(.*)|({NAME})\((.*))$")
UNFINISHED = "<unfinished ...>"
SIGNAL = re.compile(r"^(\d+)\s+--- (SIG[A-Z0-9]+|[A-Z]+) ")
EXITED = re.compile(r"^(\d+)\s+\+\+\+ (exited|killed) ")
# Matched ONLY against the text after the argument scanner's closing `)`, never searched for in the line.
RETURN = re.compile(r"\s*= (-?\d+|0x[0-9a-f]+|\?)(<.*>)?(?: (E[A-Z0-9]+))?")
FAMILY = {"unshare", "setns", "chroot", "pivot_root", "mount", "umount2", "open_tree", "move_mount", "fsopen",
          "fsmount", "fspick", "mount_setattr", "io_uring_setup"}
REMOVERS = {"unlink", "unlinkat", "rmdir", "rename", "renameat", "renameat2"}
CREATORS = {"open", "openat", "openat2", "mkdir", "mkdirat", "mknod", "mknodat", "link", "linkat", "symlink",
            "symlinkat"}
FORKS = {"clone", "clone3", "fork", "vfork"}
KEEP_FAMILY_LINES = 20
KEEP_SHAPES = 200
# Listed removals kept per record, by annotation. The COUNTS are always whole; the not-created ones (what slice 2's
# refusal rule is about) are kept generously, the created ones (temp files, mostly) only as samples.
KEEP_REMOVALS = {"not_created_in_log": 500, "created_in_log": 50}


def scan_args(s: str) -> "tuple[list[str], int] | None":
    """The top-level arguments of `s` (the text after `name(`) and the index of their matching unquoted `)`.
    None if it never closes (a shape this scanner cannot balance). Quotes, (), [], {} and -yy labels (a `<`
    after an alphanumeric or `]`, nesting inside a label) are respected."""
    args, cur, stack, i, n = [], [], [], 0, len(s)
    pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            cur.append(s[i:j + 1])
            i = j + 1
            if s[i:i + 3] == "...":
                cur.append("...")
                i += 3
            continue
        if c == "<" and (stack and stack[-1] == ">" or (cur and (cur[-1][-1:].isalnum() or cur[-1][-1:] == "]"))):
            stack.append(">")
        elif c in "([{":
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


def split_args(s: str) -> "list[str] | None":
    scanned = scan_args(s)
    return None if scanned is None else scanned[0]


def decode_c(raw: str) -> str:
    """strace's C escapes (`\\x20`, `\\n`, octal) decoded, as a path."""
    out, i = bytearray(), 0
    while i < len(raw):
        c = raw[i]
        if c != "\\" or i + 1 >= len(raw):
            out += c.encode("utf-8", "surrogateescape")
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt == "x":
            out.append(int(raw[i + 2:i + 4], 16))
            i += 4
        elif nxt in "01234567":
            j = i + 1
            while j < len(raw) and j < i + 4 and raw[j] in "01234567":
                j += 1
            out.append(int(raw[i + 1:j], 8))
            i = j
        else:
            out += {"n": b"\n", "t": b"\t", "r": b"\r", "v": b"\v", "f": b"\f"}.get(nxt, nxt.encode())
            i += 2
    return os.fsdecode(bytes(out))


def unquote(arg: str) -> "str | None":
    """The path a strace string argument names, C escapes decoded. None if `arg` is not a whole string."""
    m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', arg)
    return decode_c(m.group(1)) if m else None


def label_of(arg: str) -> "str | None":
    """The path inside a dirfd's -yy label (`3</a/b>`, `AT_FDCWD</cwd>`), C escapes decoded. None if
    undecorated."""
    m = re.fullmatch(r"(?:\d+|AT_FDCWD)<(.*)>", arg)
    return decode_c(m.group(1)) if m else None


def resolve(dirfd: "str | None", path_arg: str) -> "str | None":
    p = unquote(path_arg)
    if p is None:
        return None
    if p.startswith("/"):
        return os.path.normpath(p)
    base = label_of(dirfd) if dirfd is not None else None
    return os.path.normpath(os.path.join(base, p)) if base else None


def removed_and_created(name: str, args: list, ok: bool, ret_label: "str | None", kind_of):
    """`(removed, created)`: the (dirfd, path-arg) pairs this call removes or replaces, and the `(path, kind)`
    it PROVABLY created, `kind` "dir" (its whole subtree is new) or "file" (the path only).

    CREATION EVIDENCE (review round 1, Codex X1/X2, Claude F4): a SUCCESSFUL `O_CREAT|O_EXCL` open (`O_CREAT`
    alone, and `creat`, succeed on an existing file), `mkdir*`, `mknod*`, `link*`, `symlink*` (a symlink is a
    "file": what lies beneath it was not created), or a successful `rename*` whose SOURCE was itself created
    (`kind_of(path)` says how). Anything else is possibly pre-existing."""
    removed, created = [], []
    a = args
    if name in ("unlink", "rmdir") and a:
        removed.append((None, a[0]))
    elif name == "unlinkat" and len(a) >= 2:
        removed.append((a[0], a[1]))
    elif name == "rename" and len(a) >= 2:
        removed += [(None, a[0]), (None, a[1])]
    elif name in ("renameat", "renameat2") and len(a) >= 4:
        removed += [(a[0], a[1]), (a[2], a[3])]
    if not ok:
        return removed, []
    if name == "rename" and len(a) >= 2:
        src, dst = resolve(None, a[0]), resolve(None, a[1])
        if src and kind_of(src):
            created.append((dst, kind_of(src)))
    elif name in ("renameat", "renameat2") and len(a) >= 4:
        src, dst = resolve(a[0], a[1]), resolve(a[2], a[3])
        if src and kind_of(src):
            created.append((dst, kind_of(src)))
    elif name == "open" and len(a) >= 2 and "O_CREAT" in a[1] and "O_EXCL" in a[1]:
        created.append((ret_label or resolve(None, a[0]), "file"))
    elif name in ("openat", "openat2") and len(a) >= 3 and "O_CREAT" in a[2] and "O_EXCL" in a[2]:
        created.append((ret_label or resolve(a[0], a[1]), "file"))
    elif name == "mkdir" and a:
        created.append((resolve(None, a[0]), "dir"))
    elif name == "mkdirat" and len(a) >= 2:
        created.append((resolve(a[0], a[1]), "dir"))
    elif name == "mknod" and a:
        created.append((resolve(None, a[0]), "file"))
    elif name == "mknodat" and len(a) >= 2:
        created.append((resolve(a[0], a[1]), "file"))
    elif name in ("link", "symlink") and len(a) >= 2:
        created.append((resolve(None, a[1]), "file"))
    elif name == "linkat" and len(a) >= 4:
        created.append((resolve(a[2], a[3]), "file"))
    elif name == "symlinkat" and len(a) >= 3:
        created.append((resolve(a[1], a[2]), "file"))
    return removed, [(p, k) for p, k in created if p]


def shape(line: str) -> str:
    """A line with its varying parts blanked: pid, strings, labels, numbers."""
    s = re.sub(r"^\d+\s+", "", line)
    s = re.sub(r'"(?:[^"\\]|\\.)*"(?:\.\.\.)?', '"S"', s)
    s = re.sub(r"<(?:[^<>]|<[^<>]*>)*>", "<L>", s)
    s = re.sub(r"0x[0-9a-f]+", "X", s)
    return re.sub(r"\d+", "N", s)


def return_tags(line: str) -> "set[str]":
    tags = set()
    if line.endswith(UNFINISHED):
        tags.add("unfinished")
    elif re.match(r"^\d+\s+<\.\.\. ", line):
        tags.add("resumed")
    if re.search(r"\)\s+= -1 E[A-Z0-9]+", line):
        tags.add("= -1 E")
    elif re.search(r"\)\s+= -?(?:\d+|0x[0-9a-f]+)$", line):
        tags.add("= N")
    if re.search(r"(?:\d|\])<[^>]", line):
        tags.add("-yy label")
    if "AT_FDCWD<" in line:
        tags.add("AT_FDCWD<")
    return tags or {"other"}


def analyse_log(log: pathlib.Path, copies: "list[str]", samples: dict, shapes: dict, who: str) -> dict:
    """Everything Task 1.1 records from one traced log. `samples` and `shapes` are the SHARD's raw-line
    stores, filled first-come."""
    syscalls, ioctls, family_counts = {}, {}, {}
    family_lines, removals, unresolved, unparsed, unpaired = [], [], [], [], []
    by_note = {"created_in_log": 0, "not_created_in_log": 0}     # EVERY listed removal, counted by annotation
    created: dict = {}           # path -> "dir" | "file", in the order the log proves them
    pending: dict = {}           # pid -> (name, the unfinished half's argument text, its line)
    root_pid = None
    at_fdcwd = deleted = forks = threads = 0
    execs: set = set()

    def kind_of(p: str) -> "str | None":
        """How `p` was created by this log: its own kind, "file" if it lies under a created directory (created, but
        its kind is not known, so it is never claimed to cover a subtree), else None."""
        if p in created:
            return created[p]
        return "file" if any(k == "dir" and p.startswith(c.rstrip("/") + "/") for c, k in created.items()) else None

    def forget(p: str) -> None:
        """`p` no longer names what the log created (it was removed, moved away, or replaced): drop the evidence for
        it and everything beneath it (review round 2, Codex X1)."""
        for c in [c for c in created if c == p or c.startswith(p.rstrip("/") + "/")]:
            del created[c]

    def inside(p: str) -> bool:
        return any(p == c or p.startswith(c + "/") for c in copies)

    def count(name: str) -> None:
        syscalls[name] = syscalls.get(name, 0) + 1

    def orphan(name: str, line: str) -> None:
        """An unpaired half: COUNTED, and a remover's unknown path is unresolved — never dropped."""
        unpaired.append(line)
        if name in REMOVERS:
            unresolved.append(line)

    def call(pid: str, name: str, body: str, line: str) -> None:
        """One whole call: `body` is the text after `name(`, its two halves already joined."""
        nonlocal forks, threads
        if name in FORKS:
            if "CLONE_THREAD" in body:
                threads += 1
            else:
                forks += 1
        if name in FAMILY:
            family_counts[name] = family_counts.get(name, 0) + 1
            if len(family_lines) < KEEP_FAMILY_LINES:
                family_lines.append(line)
        scanned = scan_args(body)
        args, end = scanned if scanned else (None, None)
        if name == "execve" and pid != root_pid:
            ex_path = re.match(r'("(?:[^"\\]|\\.)*")', body)
            if ex_path and unquote(ex_path.group(1)) is not None:
                execs.add(unquote(ex_path.group(1)))
        if name == "ioctl" and args and len(args) >= 2:
            ioctls[args[1]] = ioctls.get(args[1], 0) + 1
        if name not in REMOVERS and name not in CREATORS:
            return
        if args is None:
            if name in REMOVERS:      # a remover this scanner cannot balance is counted, never dropped
                unresolved.append(line)
            return
        r = RETURN.match(body, end + 1)
        ok = bool(r) and r.group(1) not in ("-1", "?")
        ret_label = label_of("0" + r.group(2)) if r and r.group(2) else None
        removed, made = removed_and_created(name, args, ok, ret_label, kind_of)
        for dirfd, parg in removed:
            p = resolve(dirfd, parg)
            if p is None:
                unresolved.append(line)
            elif not inside(p):
                # LISTED, never exempted (review round 2, Codex X1): the evidence only ANNOTATES, so a stale or
                # incomplete provenance rule can mislabel a removal but can no longer hide one.
                note = kind_of(p) is not None
                key = "created_in_log" if note else "not_created_in_log"
                by_note[key] += 1
                if by_note[key] <= KEEP_REMOVALS[key]:
                    removals.append({"path": p, "line": line, "created_in_log": note, "ok": ok})
        if ok:      # a removed path, a rename's source and its replaced destination no longer name what was created
            for dirfd, parg in removed:
                p = resolve(dirfd, parg)
                if p is not None:
                    forget(p)
        for p, k in made:
            created[p] = k

    with open(log, encoding="utf-8", errors="surrogateescape") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line:
                continue
            sig, ex = SIGNAL.match(line), EXITED.match(line)
            if ex and ex.group(1) in pending:     # its unfinished half can never resume (review round 2, Codex X5)
                head = pending.pop(ex.group(1))
                orphan(head[0], head[2])
            if sig or ex:
                key = ("signal" if sig else "exit") + ": " + shape(line)
                if key not in shapes and len(shapes) < KEEP_SHAPES:
                    shapes[key] = {"line": line, "target": who}
                continue
            m = LINE.match(line)
            if not m:
                if len(unparsed) < 20:
                    unparsed.append(line)
                continue
            pid = m.group(1)
            if root_pid is None:
                root_pid = pid
            name = m.group(2) or m.group(4)
            if "AT_FDCWD<" in line:
                at_fdcwd += 1
            deleted += line.count(" (deleted)>")
            for tag in return_tags(line):
                if (name, tag) not in samples:
                    samples[(name, tag)] = {"line": line, "target": who}
            if m.group(2):                                    # `<... name resumed>rest`
                head = pending.pop(pid, None)
                if head is None or head[0] != name:
                    if head is not None:
                        orphan(head[0], head[2])
                    count(name)
                    orphan(name, line)
                    continue
                call(pid, name, head[1] + m.group(3), head[2] + " … " + line)
                continue
            body = m.group(5)
            if name in FORKS:
                key = "spawn: " + shape(line)
                if key not in shapes and len(shapes) < KEEP_SHAPES:
                    shapes[key] = {"line": line, "target": who}
            count(name)
            if body.endswith(UNFINISHED):                     # `name(args <unfinished ...>`: wait for its half
                if pid in pending:
                    orphan(pending[pid][0], pending[pid][2])
                pending[pid] = (name, body[:-len(UNFINISHED)], line)
                continue
            call(pid, name, body, line)
    for name, _head, line in pending.values():                # never resumed (killed, or the log was cut)
        orphan(name, line)
    return {"syscalls": syscalls, "ioctls": ioctls, "at_fdcwd_decorated_lines": at_fdcwd,
            "deleted_labels": deleted, "family_counts": family_counts, "family_lines": family_lines,
            "external_removals": removals, "external_removal_count": sum(by_note.values()),
            "external_removal_counts": dict(by_note),
            "unresolved_removals": unresolved[:20], "unresolved_removal_count": len(unresolved),
            "unpaired_halves": len(unpaired), "unpaired_samples": unpaired[:20],
            "unparsed_lines": unparsed, "forks": forks, "threads": threads, "spawner": forks > 0,
            "runs_git": any(e.endswith("/git") for e in execs), "execs": sorted(execs)[:50]}


# ── a run ───────────────────────────────────────────────────────────────────────────────────────────────
def run(cmd: list, cwd: pathlib.Path, env: dict, limit: float) -> dict:
    """One run, its process GROUP killed on timeout (strace's tracees would otherwise outlive it)."""
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         errors="surrogateescape", start_new_session=True)
    try:
        out, err = p.communicate(timeout=limit)
        timed_out = False
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        timed_out = True
    return {"rc": p.returncode, "out": out, "err": err, "secs": round(time.monotonic() - t0, 2),
            "timeout": timed_out}


def one_run(h, target: str, seed: int, traced: bool, work: pathlib.Path, keep: pathlib.Path) -> dict:
    copy = pathlib.Path(tempfile.mkdtemp(prefix="sm-", dir=work))
    try:
        problems = h.stage_tree(ROOT, copy)
        if problems:
            return {"staging": problems}
        (copy / h.CHILD_HOME).mkdir()
        # The flag is the TARGET's, not this file's own `--self-test`.
        cmd = [sys.executable, target, "--self" + "-test"]
        log = keep / "trace.log"
        if traced:
            cmd = ["strace", "-f", "-yy", "-o", str(log)] + cmd
        r = run(cmd, copy, h.mutation_env(copy, seed), h.SUITE_TIMEOUT * 10)
        merged = h.merged_output(r["out"], r["err"])
        rec = {"rc": r["rc"], "cases": h.summary_total(merged), "green": h.control_is_green(r["rc"], merged),
               "secs": r["secs"], "timeout": r["timeout"]}
        if traced:
            rec["strace_stderr"] = [ln for ln in r["err"].splitlines() if ln.startswith("strace:")][:20]
            rec["log_bytes"] = log.stat().st_size if log.exists() else None
            rec["copy"] = str(copy)
        if not rec["green"]:
            rec["tail"] = merged[-1500:]
        return rec
    finally:
        shutil.rmtree(copy, ignore_errors=True)


def measure_shard(index: int, total: int, seeds: "list[int]", out: pathlib.Path) -> int:
    h = load_harness()
    muts, problems = h.load_manifests(ROOT)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 2
    targets = h.shard_slice(sorted({m["file"] for m in muts}), index, total)
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = out / f"raw-{index}"
    raw_dir.mkdir(exist_ok=True)
    samples, shapes, records = {}, {}, {}
    whole = {"git": None, "threaded": None}     # (log bytes, target, seed) of the SMALLEST qualifying log
    t_shard = time.monotonic()
    work = pathlib.Path(tempfile.mkdtemp(prefix="strace-measure-"))
    try:
        for target in targets:
            records[target] = {}
            for seed in seeds:
                print(f"[{time.strftime('%H:%M:%S')}] {target} seed {seed}", flush=True)
                keep = work / "keep"
                shutil.rmtree(keep, ignore_errors=True)
                keep.mkdir()
                plain = one_run(h, target, seed, False, work, keep)
                traced = one_run(h, target, seed, True, work, keep)
                log = keep / "trace.log"
                if log.exists():
                    copy = traced.pop("copy", "")
                    traced.update(analyse_log(log, [copy, os.path.realpath(copy)], samples, shapes,
                                              f"{target} seed {seed}"))
                    for kind, flag in (("git", traced["runs_git"]), ("threaded", traced["threads"] > 0)):
                        size = log.stat().st_size
                        if flag and (whole[kind] is None or size < whole[kind][0]):
                            dest = raw_dir / f"whole-{kind}.log"
                            shutil.copyfile(log, dest)
                            whole[kind] = (size, target, seed, copy)
                else:
                    traced["log_missing"] = True
                records[target][str(seed)] = {"plain": plain, "traced": traced}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    header = {
        "strace_version": first_line(["strace", "-V"]), "uname_r": first_line(["uname", "-r"]),
        "ImageOS": os.environ.get("ImageOS"), "ImageVersion": os.environ.get("ImageVersion"),
        "node": first_line(["node", "-v"]), "python": first_line([sys.executable, "-V"]),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "sha": os.environ.get("GITHUB_SHA"),
    }
    doc = {"header": header, "shard": [index, total], "seeds": seeds, "targets": records,
           "elapsed_secs": round(time.monotonic() - t_shard, 1),
           "whole_logs": {k: (None if v is None else {"file": f"raw-{index}/whole-{k}.log", "bytes": v[0],
                                                       "target": v[1], "seed": v[2], "copy": v[3]})
                          for k, v in whole.items()}}
    (out / f"shard-{index}.json").write_text(json.dumps(doc, indent=1, sort_keys=True))
    (raw_dir / "lines.json").write_text(json.dumps(
        {"run_id": header["run_id"], "shard": index,
         "samples": [{"syscall": k[0], "shape": k[1], **v} for k, v in sorted(samples.items())],
         "shapes": [{"shape": k, **v} for k, v in sorted(shapes.items())]}, indent=1))
    print(f"shard {index}/{total}: {len(targets)} targets, {doc['elapsed_secs']}s")
    return 0


def first_line(cmd: list) -> "str | None":
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"UNAVAILABLE: {e}"
    text = (r.stdout or r.stderr).strip()
    return text.splitlines()[0] if text else None


# ── merge ───────────────────────────────────────────────────────────────────────────────────────────────
def merge(dirs: "list[pathlib.Path]", out: pathlib.Path, jobs: "pathlib.Path | None") -> int:
    shards = sorted((json.loads(p.read_text()) for d in dirs for p in d.rglob("shard-*.json")),
                    key=lambda s: s["shard"][0])
    if not shards:
        print("CANNOT RUN — no shard-*.json under the given directories. NOTHING WAS MERGED.", file=sys.stderr)
        return 2
    headers = {json.dumps(s["header"] | {}, sort_keys=True) for s in shards}
    total = shards[0]["shard"][1]
    syscalls, ioctls, family, deleted, removals, unresolved, unpaired = {}, {}, {}, {}, {}, {}, {}
    ratios, case_diff, red, timeouts, unparsed, strace_err = [], [], [], [], {}, {}
    at_fdcwd_targets = set()
    targets = {}
    # COVERAGE per (target, seed) record (review round 2, Codex X2): a field a record lacks was NOT MEASURED there, and
    # one measured record must not make the whole merge read as measured. A total is null unless EVERY record has it.
    records = paired_records = annotated_records = 0
    removal_counts: dict = {}   # target -> annotation -> the max over its seeds
    for s in shards:
        for t, by_seed in s["targets"].items():
            targets[t] = s["shard"][0]
            for seed, r in by_seed.items():
                pl, tr = r["plain"], r["traced"]
                for name in tr.get("syscalls", {}):
                    syscalls.setdefault(name, set()).add(t)
                for tok in tr.get("ioctls", {}):
                    ioctls.setdefault(tok, set()).add(t)
                for name in tr.get("family_counts", {}):
                    family.setdefault(name, set()).add(t)
                if tr.get("at_fdcwd_decorated_lines"):
                    at_fdcwd_targets.add(t)
                if tr.get("deleted_labels"):
                    deleted[t] = max(deleted.get(t, 0), tr["deleted_labels"])
                records += 1
                for x in tr.get("external_removals", []):
                    note = {True: "created_in_log", False: "not_created_in_log"}.get(x.get("created_in_log"),
                                                                                       "not_annotated")
                    removals.setdefault(t, {}).setdefault(note, set()).add(x["path"])
                if "external_removal_counts" in tr:
                    annotated_records += 1
                    for note, n in tr["external_removal_counts"].items():
                        per = removal_counts.setdefault(t, {})
                        per[note] = max(per.get(note, 0), n)
                if tr.get("unresolved_removal_count"):
                    unresolved[t] = max(unresolved.get(t, 0), tr["unresolved_removal_count"])
                if "unpaired_halves" in tr:
                    paired_records += 1
                if tr.get("unpaired_halves"):
                    unpaired[t] = max(unpaired.get(t, 0), tr["unpaired_halves"])
                if tr.get("unparsed_lines"):
                    unparsed[t] = tr["unparsed_lines"][:3]
                if tr.get("strace_stderr"):
                    strace_err[t] = tr["strace_stderr"]
                if pl.get("secs") and tr.get("secs") is not None:
                    ratios.append({"target": t, "seed": seed, "spawner": tr.get("spawner"),
                                   "plain": pl["secs"], "traced": tr["secs"],
                                   "ratio": round(tr["secs"] / pl["secs"], 2),
                                   "_exact": tr["secs"] / pl["secs"]})
                if pl.get("cases") != tr.get("cases"):
                    case_diff.append({"target": t, "seed": seed, "plain": pl.get("cases"),
                                      "traced": tr.get("cases")})
                for kind, x in (("plain", pl), ("traced", tr)):
                    if not x.get("green"):
                        red.append({"target": t, "seed": seed, "run": kind, "rc": x.get("rc"),
                                    "timeout": x.get("timeout"), "staging": x.get("staging")})
                    if x.get("timeout"):
                        timeouts.append({"target": t, "seed": seed, "run": kind})
    spawner_ratios = [r for r in ratios if r["spawner"]]
    # The ceiling of the max UNROUNDED ratio (review round 1, Codex X5): rounding first turns 20.001 into 20.
    worst = max(spawner_ratios, key=lambda r: r["_exact"], default=None)
    trace_factor = None if worst is None else math.ceil(worst["_exact"])
    for r in ratios:
        del r["_exact"]
    doc = {
        "headers": [json.loads(h) for h in sorted(headers)],
        "shards_present": [s["shard"][0] for s in shards], "shards_expected": total,
        "seeds": shards[0]["seeds"], "target_count": len(targets),
        "syscalls": {k: len(v) for k, v in sorted(syscalls.items())},
        "ioctls": {k: len(v) for k, v in sorted(ioctls.items())},
        "at_fdcwd_decorated": bool(at_fdcwd_targets), "at_fdcwd_decorated_targets": len(at_fdcwd_targets),
        "refusal_triggers": {k: sorted(v) for k, v in sorted(family.items())},
        "deleted_labels": dict(sorted(deleted.items())),
        # Every listed removal outside the copy, by its `created_in_log` annotation; nothing is exempted. The created
        # ones are mostly temp files, so only 20 paths per target are kept; the counts are whole.
        "external_removals": {t: {note: sorted(paths)[:20] if note == "created_in_log" else sorted(paths)
                                  for note, paths in sorted(by.items())} for t, by in sorted(removals.items())},
        "external_removal_counts": {t: dict(sorted(c.items())) for t, c in sorted(removal_counts.items())
                                    if any(c.values())},
        "external_removal_totals": None if annotated_records < records else {
            "created_in_log": sum(c.get("created_in_log", 0) for c in removal_counts.values()),
            "not_created_in_log": sum(c.get("not_created_in_log", 0) for c in removal_counts.values()),
            "targets_with_not_created": sum(1 for c in removal_counts.values() if c.get("not_created_in_log")),
            "records": records},
        "external_removal_coverage": {"annotated": annotated_records, "records": records},
        "unresolved_removals": dict(sorted(unresolved.items())),
        "unpaired_halves": dict(sorted(unpaired.items())) if records and paired_records == records else None,
        "unpaired_halves_coverage": {"measured": paired_records, "records": records},
        "unparsed_line_samples": dict(sorted(unparsed.items())),
        "strace_stderr": dict(sorted(strace_err.items())),
        "trace_factor": trace_factor,
        "trace_factor_from": worst,
        "spawner_targets": sorted({r["target"] for r in spawner_ratios}),
        "ratio_all_targets_max": max((r["ratio"] for r in ratios), default=None),
        "ratios": ratios,
        "case_count_differs": case_diff, "not_green": red, "timeouts": timeouts,
        "shard_elapsed_secs": {str(s["shard"][0]): s["elapsed_secs"] for s in shards},
        "shard_elapsed_sum_secs": round(sum(s["elapsed_secs"] for s in shards), 1),
        "whole_logs": {str(s["shard"][0]): s["whole_logs"] for s in shards},
    }
    if jobs is not None:
        doc["jobs"] = job_durations(json.loads(jobs.read_text()))
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"merged {len(shards)}/{total} shards, {len(targets)} targets -> {out}")
    return 0


def job_durations(view: dict) -> dict:
    """From `gh run view --json jobs`: each job's wall seconds (startedAt..completedAt) and their sum."""
    from datetime import datetime
    per = {}
    for j in view.get("jobs", []):
        a, b = j.get("startedAt"), j.get("completedAt")
        if a and b:
            per[j["name"]] = (datetime.fromisoformat(b.replace("Z", "+00:00"))
                              - datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds()
    return {"per_job_secs": dict(sorted(per.items())), "sum_secs": sum(per.values()),
            "max_secs": max(per.values(), default=None)}


# ── self-test ───────────────────────────────────────────────────────────────────────────────────────────
# The log reader's rules, cased offline. Every constructed input below is a review-round-1 finding's own input
# (docs/reviews/{codex,claude}/586-slice1-r1-*.md), each run red against the pre-fix reader before it was fixed;
# the `???` lines are REAL, recorded in run 42901768433 (shard 5, `scripts/compaction-state.py`, seed 0).
FIXTURES = ROOT / "scripts" / "fixtures" / "strace-lines"


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _read(text: str, copies: "list[str] | None" = None, samples: "dict | None" = None,
          shapes: "dict | None" = None, who: str = "case") -> dict:
    """`analyse_log` over `text`, the copy being `/t` unless `copies` says otherwise."""
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "trace.log"
        p.write_text(text)
        return analyse_log(p, ["/t"] if copies is None else copies, {} if samples is None else samples,
                           {} if shapes is None else shapes, who)


def _stores(text: str, samples: dict, shapes: dict, who: str):
    """The shard's two raw-line stores after `analyse_log` filled them from `text` as `who`."""
    _read(text, samples=samples, shapes=shapes, who=who)
    return ({k: v["target"] for k, v in samples.items()}, {k: v["target"] for k, v in shapes.items()})


def _shard(index: int, of: int, target: str, plain: float, traced: float, traced_extra: "dict | None" = None) -> dict:
    return {"header": {}, "shard": [index, of], "seeds": [0], "elapsed_secs": 1.0, "whole_logs": {},
            "targets": {target: {"0": {"plain": {"secs": plain, "cases": 1, "green": True},
                                       "traced": {"secs": traced, "cases": 1, "green": True,
                                                  "spawner": True, **(traced_extra or {})}}}}}


def _merge(shards: "list[list[dict]]", key: str, jobs: "dict | None" = None):
    """`merge`'s `key` over `shards`, one DIRECTORY per inner list, and a `gh run view --json jobs` view if given."""
    with tempfile.TemporaryDirectory() as d:
        dirs = []
        for i, group in enumerate(shards):
            sub = pathlib.Path(d) / f"dir-{i}"
            sub.mkdir()
            for sh in group:
                (sub / f"shard-{sh['shard'][0]}.json").write_text(json.dumps(sh))
            dirs.append(sub)
        jobs_file = None
        if jobs is not None:
            jobs_file = pathlib.Path(d) / "jobs.json"
            jobs_file.write_text(json.dumps(jobs))
        out = pathlib.Path(d) / "merged.json"
        with contextlib.redirect_stdout(open(os.devnull, "w")):
            merge(dirs, out, jobs_file)
        return json.loads(out.read_text())[key]


def _merge_ratio(plain: float, traced: float, key: str = "trace_factor", traced_extra: "dict | None" = None):
    """`merge`'s `key` (default `trace_factor`) over one spawner target with these wall times."""
    return _merge([[_shard(1, 1, "t.py", plain, traced, traced_extra)]], key)


def _self_test_body() -> int:
    ok = fail = 0

    def check(label, got_fn, want):
        nonlocal ok, fail
        try:
            got = got_fn()
        except Exception as e:      # a crash is a red case, named, never a pass
            got = f"RAISED {type(e).__name__}: {e}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}\n       got  {got!r}\n       want {want!r}")

    # Since review round 2 NOTHING outside the copy is exempted: every removal is LISTED, annotated `created_in_log`.
    # `ext`/`lines` read the removals NOT proved created by the log (the annotation the round-1 cases are about);
    # `listed` reads the whole list, in log order, with its annotation.
    ext = lambda text: sorted({r["path"] for r in _read(text)["external_removals"] if r.get("created_in_log") is not True})
    lines = lambda text: sorted({r["line"] for r in _read(text)["external_removals"] if r.get("created_in_log") is not True})
    listed = lambda text: [(r["path"], r.get("created_in_log")) for r in _read(text)["external_removals"]]

    # Creation evidence (Codex X1, Claude F4): only a successful O_CREAT|O_EXCL proves the open created the path.
    check("X1 an O_CREAT open WITHOUT O_EXCL of an outside file, then its unlink, is an external removal",
          lambda: ext('1 openat(AT_FDCWD</t>, "/external/existing", O_CREAT|O_WRONLY, 0600) = 3</external/existing>\n'
                      '1 unlink("/external/existing") = 0\n'), ["/external/existing"])
    check("X1 Claude F4's truncate-then-delete of ~/.gitconfig is an external removal",
          lambda: ext('100 openat(AT_FDCWD</t>, "/home/runner/.gitconfig", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666)'
                      ' = 3</home/runner/.gitconfig>\n100 unlink("/home/runner/.gitconfig") = 0\n'),
          ["/home/runner/.gitconfig"])
    check("X1 a successful O_CREAT|O_EXCL open IS creation: its later unlink is annotated created",
          lambda: ext('1 openat(AT_FDCWD</t>, "/external/new", O_WRONLY|O_CREAT|O_EXCL, 0600) = 3</external/new>\n'
                      '1 unlink("/external/new") = 0\n'), [])
    check("X1 a FAILED O_CREAT|O_EXCL open is not creation",
          lambda: ext('1 openat(AT_FDCWD</t>, "/external/old", O_WRONLY|O_CREAT|O_EXCL, 0600) = -1 EEXIST (File exists)\n'
                      '1 unlink("/external/old") = 0\n'), ["/external/old"])
    check("X1 creat() truncates an existing file: not creation",
          lambda: ext('1 creat("/external/c", 0644) = 3</external/c>\n1 unlink("/external/c") = 0\n'), ["/external/c"])
    check("X1 a successful mknodat is creation",
          lambda: ext('1 mknodat(AT_FDCWD</t>, "/external/fifo", S_IFIFO|0600) = 0\n1 unlink("/external/fifo") = 0\n'), [])
    # A failed rename creates nothing (Codex X2); a rename creates its new side only if its source was created.
    check("X2 a FAILED renameat does not mark its destination created",
          lambda: ext('1 renameat(3</external>, "absent", 3</external>, "existing") = -1 ENOENT (No such file or directory)\n'
                      '1 unlinkat(3</external>, "existing", 0) = 0\n'), ["/external/absent", "/external/existing"])
    # A rename ONTO an outside path is itself reported: it replaces whatever was there.
    check("X2 a successful rename of a CREATED file creates its destination: only the rename is reported",
          lambda: lines('1 openat(AT_FDCWD</t>, "/external/tmp1", O_WRONLY|O_CREAT|O_EXCL, 0600) = 3</external/tmp1>\n'
                        '1 rename("/external/tmp1", "/t/x") = 0\n1 rename("/t/x", "/external/final") = 0\n'
                        '1 unlink("/external/final") = 0\n'), ['1 rename("/t/x", "/external/final") = 0'])
    check("X2 a successful rename of a PRE-EXISTING file does not make its destination created",
          lambda: ext('1 rename("/t/old", "/external/dst") = 0\n1 unlink("/external/dst") = 0\n'), ["/external/dst"])
    check("X2 a path under a created DIRECTORY is created; under a created SYMLINK it is not",
          lambda: ext('1 mkdir("/external/d", 0700) = 0\n1 unlink("/external/d/x") = 0\n'
                      '1 symlink("/home/runner", "/external/s") = 0\n1 unlink("/external/s/.gitconfig") = 0\n'),
          ["/external/s/.gitconfig"])
    check("X2 a renamed created directory keeps its subtree created: only the rename is reported",
          lambda: lines('1 mkdir("/external/d", 0700) = 0\n1 rename("/external/d", "/external/e") = 0\n'
                        '1 unlink("/external/e/x") = 0\n'), ['1 rename("/external/d", "/external/e") = 0'])
    # The return is read after the argument scanner's matching unquoted `)` (Codex X3).
    check("X3 a `) = 7` inside a quoted path is not the return: the failed open creates nothing",
          lambda: ext('1 openat(AT_FDCWD</t>, "/external/) = 7", O_CREAT|O_WRONLY|O_EXCL, 0600) = -1 EACCES (Permission denied)\n'
                      '1 unlink("/external/) = 7") = 0\n'), ["/external/) = 7"])
    # unfinished/resumed are JOINED per pid before the arguments and the result are read (Codex X4).
    check("X4 a resumed tail's arguments are read: ioctl's request token",
          lambda: _read('1 ioctl(3</dev/tty>, <unfinished ...>\n1 <... ioctl resumed>TCGETS, 0x123) = 0\n')["ioctls"],
          {"TCGETS": 1})
    check("X4 a joined call is counted once",
          lambda: _read('1 ioctl(3</dev/tty>, <unfinished ...>\n1 <... ioctl resumed>TCGETS, 0x123) = 0\n')["syscalls"],
          {"ioctl": 1})
    check("X4 a removal whose path is in the resumed tail is read",
          lambda: ext('7 unlinkat(3</external>, <unfinished ...>\n8 getpid() = 8\n'
                      '7 <... unlinkat resumed>"victim", 0) = 0\n'), ["/external/victim"])
    check("X4 interleaved pids are joined to their own halves",
          lambda: ext('7 unlinkat(3</external>, <unfinished ...>\n8 unlinkat(3</t>, <unfinished ...>\n'
                      '8 <... unlinkat resumed>"in-copy", 0) = 0\n7 <... unlinkat resumed>"out", 0) = 0\n'),
          ["/external/out"])
    check("X4 a join's return decides creation: a resumed failure creates nothing",
          lambda: ext('1 mkdir("/external/d", 0700 <unfinished ...>\n1 <... mkdir resumed>) = -1 EEXIST (File exists)\n'
                      '1 unlink("/external/d/x") = 0\n'), ["/external/d/x"])
    for label, text, want in (
            ("an orphan resumed half", '1 <... unlinkat resumed>"x", 0) = 0\n', 1),
            ("an unfinished half never resumed", '1 unlinkat(3</external>, "x", 0 <unfinished ...>\n', 1),
            ("a resumed half naming a different call", '1 read(3, <unfinished ...>\n1 <... write resumed>) = 1\n', 2)):
        check(f"X4 {label} is COUNTED as unpaired", lambda t=text: _read(t)["unpaired_halves"], want)
    check("X4 an unpaired REMOVER half is unresolved, not dropped",
          lambda: _read('1 <... unlinkat resumed>"x", 0) = 0\n')["unresolved_removal_count"], 1)
    # `???` is a syscall name strace prints when it cannot read the number (Claude F2; REAL lines, run 42901768433).
    q = '7044  ???( <unfinished ...>\n7044  <... ??? resumed>)                = ?\n'
    check("F2 the recorded `???` pair parses: no line unparsed", lambda: _read(q)["unparsed_lines"], [])
    check("F2 ... and is recorded as the name `???`, joined once", lambda: _read(q)["syscalls"], {"???": 1})
    check("F2 ... and pairs", lambda: _read(q)["unpaired_halves"], 0)
    # TRACE_FACTOR is the ceiling of the UNROUNDED ratio (Codex X5).
    check("X5 200.01 s traced over 10 s plain is 20.001: TRACE_FACTOR 21", lambda: _merge_ratio(10, 200.01), 21)
    check("X5 an exact 20.0 stays 20", lambda: _merge_ratio(10, 200), 20)
    check("X4 merge: shards whose reader never counted unpaired halves report null (NOT MEASURED), not {}",
          lambda: _merge_ratio(10, 200, key="unpaired_halves"), None)
    check("X4 merge: a shard that counted them reports the count",
          lambda: _merge_ratio(10, 200, key="unpaired_halves", traced_extra={"unpaired_halves": 3}), {"t.py": 3})
    # The parameters every case above holds constant (check-fixture-variation), each varied where it decides.
    check("copies: an unlink under the SECOND copy root (the driver passes the copy and its realpath) is inside",
          lambda: sorted(r["path"] for r in _read('1 unlink("/real/t/x") = 0\n', copies=["/t", "/real/t"])
                         ["external_removals"]), [])
    check("copies: the same unlink with only the first root is outside",
          lambda: sorted(r["path"] for r in _read('1 unlink("/real/t/x") = 0\n', copies=["/t"])
                         ["external_removals"]), ["/real/t/x"])
    check("samples/shapes/who: the shard's stores are filled first-come, each line credited to the target that "
          "logged it; a store already holding a key keeps its first owner",
          lambda: _stores('1 unlink("/t/x") = 0\n1 --- SIGCHLD {si_signo=SIGCHLD} ---\n',
                          {("unlink", "= N"): {"line": "earlier", "target": "first.py"}}, {}, "second.py"),
          ({("unlink", "= N"): "first.py"}, {"signal: --- SIGCHLD {si_signo=SIGCHLD} ---": "second.py"}))
    check("dirs: shards split across TWO directories: the factor is the max over them (alone, NOT proof both are read; see r2 X4)",
          lambda: _merge([[_shard(1, 2, "a.py", 1, 5)], [_shard(2, 2, "b.py", 1, 7)]], "trace_factor"), 7)
    check("jobs: a `gh run view --json jobs` view gives each job's wall seconds and their sum",
          lambda: _merge([[_shard(1, 1, "t.py", 1, 2)]], "jobs",
                         {"jobs": [{"name": "s (1)", "startedAt": "2026-11-10T00:00:00Z", "completedAt": "2026-11-10T00:01:40Z"},
                                   {"name": "s (2)", "startedAt": "2026-11-10T00:00:00Z", "completedAt": "2026-11-10T00:00:30Z"},
                                   {"name": "s (3)", "startedAt": "2026-11-10T00:00:00Z", "completedAt": None}]}),
          {"per_job_secs": {"s (1)": 100.0, "s (2)": 30.0}, "sum_secs": 130.0, "max_secs": 100.0})

    # ── review round 2 (docs/reviews/codex/586-slice1-r2-codex.md), each red on the round-1 reader ──
    # X1 (High): creation evidence EXEMPTED removals, and stale evidence hid a pre-existing directory moved onto a
    # created name. The class is removed: nothing is exempted; evidence only ANNOTATES, and a removal or a rename
    # source clears it (so the annotation is not misleading either).
    codex_x1 = ('1 mkdir("/external/d", 0700) = 0\n1 rmdir("/external/d") = 0\n'
                '1 rename("/t/preexisting", "/external/d") = 0\n1 unlink("/external/d/valuable") = 0\n')
    check("r2 X1 nothing is exempted: an unlink of an O_EXCL-created outside file is LISTED, annotated created",
          lambda: listed('1 openat(AT_FDCWD</t>, "/external/new", O_WRONLY|O_CREAT|O_EXCL, 0600) = 3</external/new>\n'
                         '1 unlink("/external/new") = 0\n'), [("/external/new", True)])
    check("r2 X1 Codex's input: the rmdir clears d's evidence, so the directory renamed onto d and its contents "
          "are listed NOT created",
          lambda: listed(codex_x1),
          [("/external/d", True), ("/external/d", False), ("/external/d/valuable", False)])
    check("r2 X1 Codex's variant: the created directory MOVED away (a rename source) leaves no evidence at d",
          lambda: listed('1 mkdir("/external/d", 0700) = 0\n1 rename("/external/d", "/external/e") = 0\n'
                         '1 rename("/t/preexisting", "/external/d") = 0\n1 unlink("/external/d/valuable") = 0\n'),
          [("/external/d", True), ("/external/e", False), ("/external/d", False), ("/external/d/valuable", False)])
    check("r2 X1 a pre-existing object renamed onto a created FILE's name replaces its evidence",
          lambda: listed('1 openat(AT_FDCWD</t>, "/external/f", O_WRONLY|O_CREAT|O_EXCL, 0600) = 3</external/f>\n'
                         '1 rename("/t/old", "/external/f") = 0\n1 unlink("/external/f") = 0\n'),
          [("/external/f", True), ("/external/f", False)])
    check("r2 X1 a file inside a created directory, renamed out, is not claimed a created DIRECTORY",
          lambda: listed('1 mkdir("/external/d", 0700) = 0\n1 rename("/external/d/sub", "/external/s") = 0\n'
                         '1 unlink("/external/s/x") = 0\n'),
          [("/external/d/sub", True), ("/external/s", False), ("/external/s/x", False)])
    check("r2 X1 the record counts its removals BY ANNOTATION",
          lambda: _read(codex_x1)["external_removal_counts"], {"created_in_log": 1, "not_created_in_log": 2})
    # X5 (Low): a pid's pending half is orphaned at its exit; a later resumed half on that pid pairs with nothing.
    for how in ("exited with 0", "killed by SIGKILL"):
        check(f"r2 X5 an unfinished remover half is orphaned at `+++ {how} +++`: nothing fabricated, both halves "
              "unpaired and unresolved",
              lambda h=how: (lambda r: (r["external_removals"], r["unpaired_halves"], r["unresolved_removal_count"]))(
                  _read(f'7 unlinkat(3</external>, <unfinished ...>\n7 +++ {h} +++\n'
                        '7 <... unlinkat resumed>"victim", 0) = 0\n')), ([], 2, 2))
    # X2 (Medium): one measured record made the whole merge "measured".
    measured, unknown = _shard(1, 2, "measured.py", 1, 2, {"unpaired_halves": 0}), _shard(2, 2, "unknown.py", 1, 2)
    check("r2 X2 Codex's input: a merge where one target never measured pairing reports null, not {}",
          lambda: _merge([[measured, unknown]], "unpaired_halves"), None)
    check("r2 X2 ... and says how many (target, seed) records measured it",
          lambda: _merge([[measured, unknown]], "unpaired_halves_coverage"), {"measured": 1, "records": 2})
    check("r2 X2 every record measured, none unpaired: {} (none observed), not null",
          lambda: _merge([[measured, _shard(2, 2, "other.py", 1, 2, {"unpaired_halves": 0})]], "unpaired_halves"), {})
    # The merged removal list, by annotation; its totals are null unless every record was annotated (X2's lesson).
    ann = {"external_removals": [{"path": "/x", "line": "l1", "created_in_log": False},
                                 {"path": "/y", "line": "l2", "created_in_log": True}],
           "external_removal_count": 2, "external_removal_counts": {"created_in_log": 1, "not_created_in_log": 1}}
    check("r2 X1 merge lists each target's removals by annotation",
          lambda: _merge([[_shard(1, 1, "t.py", 1, 2, ann)]], "external_removals"),
          {"t.py": {"created_in_log": ["/y"], "not_created_in_log": ["/x"]}})
    check("r2 X1 merge totals the removals by annotation",
          lambda: _merge([[_shard(1, 1, "t.py", 1, 2, ann)]], "external_removal_totals"),
          {"created_in_log": 1, "not_created_in_log": 1, "targets_with_not_created": 1, "records": 1})
    check("r2 X1 merge totals are null when a record carries no annotation counts",
          lambda: _merge([[_shard(1, 2, "t.py", 1, 2, ann), _shard(2, 2, "u.py", 1, 2)]], "external_removal_totals"),
          None)
    # X3 (Medium): the sample store case supplied the only sample it checked. From an EMPTY store: insertion AND owner.
    check("r2 X3 an EMPTY sample store gains the line, credited to the target that logged it",
          lambda: (lambda st: (_read('1 unlink("/t/x") = 0\n', samples=st, who="second.py"), st)[1])({}),
          {("unlink", "= N"): {"line": '1 unlink("/t/x") = 0', "target": "second.py"}})
    # X4 (Medium): the two-directory case's answer came from the last directory alone.
    two_dirs = [[_shard(1, 2, "a.py", 1, 5)], [_shard(2, 2, "b.py", 1, 7)]]
    check("r2 X4 shards split across TWO directories: BOTH targets are merged",
          lambda: _merge(two_dirs, "spawner_targets"), ["a.py", "b.py"])
    check("r2 X4 ... and both shards are present", lambda: _merge(two_dirs, "shards_present"), [1, 2])

    # Low findings.
    check("F5 a REMOVER line the splitter cannot balance is unresolved, never dropped",
          lambda: _read('100 unlinkat(3</home/runner/a<b>, "f", 0) = 0\n')["unresolved_removal_count"], 1)
    check("F8 a -yy label's C escapes are decoded before resolving",
          lambda: ext('1 mkdir("/external/my dir", 0700) = 0\n1 unlinkat(3</external/my\\x20dir>, "f", 0) = 0\n'), [])
    # The recorded logs: every line parses (a property of the fixtures this run committed, MEASURED by this case).
    for name in ("whole-git.log", "whole-threaded.log"):
        p = FIXTURES / name
        # The fixture's first line is its provenance header (`# strace-measure run …`), not strace output.
        check(f"recorded {name}: no line unparsed",
              lambda p=p: _read("".join(p.read_text().splitlines(True)[1:]))["unparsed_lines"]
              if p.exists() else "CANNOT RUN — fixture missing", [])

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--shard", help="I/N, 1-based")
    ap.add_argument("--seeds", help="A,B: PYTHONHASHSEED values, each run under every one")
    ap.add_argument("--merge", nargs="+", type=pathlib.Path, help="directories holding shard-*.json")
    ap.add_argument("--jobs", type=pathlib.Path, help="with --merge: `gh run view --json jobs` output")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--self-test", action="store_true", help="case the log reader offline")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if a.out is None:
        ap.error("--out is required")
    if a.merge:
        return merge(a.merge, a.out, a.jobs)
    if not a.shard or not a.seeds:
        ap.error("--shard and --seeds are required without --merge")
    m = re.fullmatch(r"([1-9]\d*)/([1-9]\d*)", a.shard)
    if not m or int(m.group(1)) > int(m.group(2)):
        ap.error(f"--shard {a.shard!r} is not I/N with 1 <= I <= N")
    seeds = [int(x) for x in a.seeds.split(",")]
    if len(seeds) != len(set(seeds)) or not seeds:
        ap.error("--seeds must be distinct integers")
    return measure_shard(int(m.group(1)), int(m.group(2)), seeds, a.out)


if __name__ == "__main__":
    sys.exit(main())

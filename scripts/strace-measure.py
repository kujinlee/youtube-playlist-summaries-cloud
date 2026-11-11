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
it tracks no cwd, and it does NOT CLASSIFY REMOVALS (backlog #601, the Phase 6 review's R1.1). For removers
(`unlink*`, `rmdir`, `rename*`) it keeps three things: the raw call counts (each record's `syscalls`, merged per
target as `removal_calls`), the UNRESOLVED list (a remover whose path it cannot write down from the line alone: a
relative path with no `-yy` label, an unbalanced line, an unpaired half), and the raw-line samples. Whether a removal
lies inside or outside the copy, or was created earlier in the log, is judged nowhere here: three review rounds showed
that strace text cannot prove "no pre-existing path outside the copy was removed" (backlog #600), and slice 2's
refusal rule decides by LOCATION with no per-log creation state (backlog #602). An `<unfinished ...>` half is JOINED
with its pid's `<... resumed>` half before its arguments are read; an unpaired half (including one still pending at
its pid's `+++ exited` or `+++ killed`) is counted (`unpaired_halves`), never dropped.
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
FAMILY = {"unshare", "setns", "chroot", "pivot_root", "mount", "umount2", "open_tree", "move_mount", "fsopen",
          "fsmount", "fspick", "mount_setattr", "io_uring_setup"}
REMOVERS = {"unlink", "unlinkat", "rmdir", "rename", "renameat", "renameat2"}
FORKS = {"clone", "clone3", "fork", "vfork"}
KEEP_FAMILY_LINES = 20
KEEP_SHAPES = 200


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


def nameable(dirfd: "str | None", path_arg: str) -> bool:
    """Whether the path a remover names can be written down from its line alone: an absolute string, or a relative
    one under a `-yy`-labelled dirfd. Nothing is folded, resolved or judged inside/outside (backlog #601)."""
    p = unquote(path_arg)
    if p is None:
        return False
    return p.startswith("/") or bool(dirfd is not None and label_of(dirfd))


def removed_paths(name: str, args: list) -> list:
    """The (dirfd, path-arg) pairs this remover names: a rename's source AND its destination."""
    a = args
    if name in ("unlink", "rmdir") and a:
        return [(None, a[0])]
    if name == "unlinkat" and len(a) >= 2:
        return [(a[0], a[1])]
    if name == "rename" and len(a) >= 2:
        return [(None, a[0]), (None, a[1])]
    if name in ("renameat", "renameat2") and len(a) >= 4:
        return [(a[0], a[1]), (a[2], a[3])]
    return []


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


def analyse_log(log: pathlib.Path, samples: dict, shapes: dict, who: str) -> dict:
    """Everything Task 1.1 records from one traced log. `samples` and `shapes` are the SHARD's raw-line
    stores, filled first-come."""
    syscalls, ioctls, family_counts = {}, {}, {}
    family_lines, unresolved, unparsed, unpaired = [], [], [], []
    pending: dict = {}           # pid -> (name, the unfinished half's argument text, its line)
    root_pid = None
    at_fdcwd = deleted = forks = threads = 0
    execs: set = set()

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
        if name not in REMOVERS:
            return
        if args is None:          # a remover this scanner cannot balance is counted, never dropped
            unresolved.append(line)
            return
        for dirfd, parg in removed_paths(name, args):
            if not nameable(dirfd, parg):
                unresolved.append(line)

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
                    traced.update(analyse_log(log, samples, shapes, f"{target} seed {seed}"))
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
    syscalls, ioctls, family, deleted, unresolved, unpaired = {}, {}, {}, {}, {}, {}
    ratios, case_diff, red, timeouts, unparsed, strace_err = [], [], [], [], {}, {}
    at_fdcwd_targets = set()
    targets = {}
    # COVERAGE per (target, seed) record (review round 2, Codex X2): a field a record lacks was NOT MEASURED there, and
    # one measured record must not make the whole merge read as measured. A total is null unless EVERY record has it.
    records = paired_records = analysed_records = 0
    removal_calls: dict = {}    # target -> remover syscall -> its call count, the max over the target's seeds
    log_missing = []            # (target, seed) records whose traced run left no log: nothing was analysed (r3 F6)
    for s in shards:
        for t, by_seed in s["targets"].items():
            targets[t] = s["shard"][0]
            for seed, r in by_seed.items():
                pl, tr = r["plain"], r["traced"]
                # A record is ANALYSED when analyse_log ran on it (it always emits `syscalls`). Every table below that
                # comes from analyse_log is null unless EVERY record was analysed (review round 3, F6: the r2 X2 rule
                # applied to the class, not to two fields).
                if "syscalls" in tr:
                    analysed_records += 1
                if tr.get("log_missing"):
                    log_missing.append([t, seed])
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
                for name, n in tr.get("syscalls", {}).items():
                    if name in REMOVERS:
                        per = removal_calls.setdefault(t, {})
                        per[name] = max(per.get(name, 0), n)
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
    whole = records > 0 and analysed_records == records      # else each analysed table is NOT MEASURED: null
    doc = {
        "headers": [json.loads(h) for h in sorted(headers)],
        "shards_present": [s["shard"][0] for s in shards], "shards_expected": total,
        "seeds": shards[0]["seeds"], "target_count": len(targets),
        "syscalls": {k: len(v) for k, v in sorted(syscalls.items())} if whole else None,
        "ioctls": {k: len(v) for k, v in sorted(ioctls.items())} if whole else None,
        "at_fdcwd_decorated": bool(at_fdcwd_targets) if whole else None,
        "at_fdcwd_decorated_targets": len(at_fdcwd_targets) if whole else None,
        "refusal_triggers": {k: sorted(v) for k, v in sorted(family.items())} if whole else None,
        "deleted_labels": dict(sorted(deleted.items())) if whole else None,
        "analysis_coverage": {"analysed": analysed_records, "records": records, "log_missing": log_missing},
        # The raw remover call counts per target (the max over its seeds), unclassified (backlog #601).
        "removal_calls": {t: dict(sorted(c.items())) for t, c in sorted(removal_calls.items())} if whole else None,
        "unresolved_removals": dict(sorted(unresolved.items())) if whole else None,
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


def _read(text: str, samples: "dict | None" = None, shapes: "dict | None" = None, who: str = "case") -> dict:
    """`analyse_log` over `text`."""
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "trace.log"
        p.write_text(text)
        return analyse_log(p, {} if samples is None else samples, {} if shapes is None else shapes, who)


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

    # Backlog #601 (the Phase 6 review's R1.1): the reader classifies no removal, so the cases that pinned the
    # removal-provenance model (round 1 X1-X3, round 2 X1, round 3 F3/F4, F8, the `copies` roots) went with it. What a
    # remover still yields is its raw count and, when its path cannot be written down from the line, `unresolved`.
    unres = lambda text: _read(text)["unresolved_removal_count"]
    # unfinished/resumed are JOINED per pid before the arguments are read (Codex X4).
    check("X4 a resumed tail's arguments are read: ioctl's request token",
          lambda: _read('1 ioctl(3</dev/tty>, <unfinished ...>\n1 <... ioctl resumed>TCGETS, 0x123) = 0\n')["ioctls"],
          {"TCGETS": 1})
    check("X4 a joined call is counted once",
          lambda: _read('1 ioctl(3</dev/tty>, <unfinished ...>\n1 <... ioctl resumed>TCGETS, 0x123) = 0\n')["syscalls"],
          {"ioctl": 1})
    check("X4 a remover whose path is in the resumed tail is read: a labelled dirfd and a string path, nameable",
          lambda: unres('7 unlinkat(3</external>, <unfinished ...>\n8 getpid() = 8\n'
                        '7 <... unlinkat resumed>"victim", 0) = 0\n'), 0)
    check("X4 interleaved pids are joined to their own halves: only pid 8's unlabelled relative unlink is unresolved",
          lambda: _read('7 unlinkat(3</external>, <unfinished ...>\n8 unlinkat(AT_FDCWD, <unfinished ...>\n'
                        '8 <... unlinkat resumed>"rel", 0) = 0\n7 <... unlinkat resumed>"out", 0) = 0\n')
          ["unresolved_removals"],
          ['8 unlinkat(AT_FDCWD, <unfinished ...> … 8 <... unlinkat resumed>"rel", 0) = 0'])
    for label, text, want in (
            ("an orphan resumed half", '1 <... unlinkat resumed>"x", 0) = 0\n', 1),
            ("an unfinished half never resumed", '1 unlinkat(3</external>, "x", 0 <unfinished ...>\n', 1),
            ("a resumed half naming a different call", '1 read(3, <unfinished ...>\n1 <... write resumed>) = 1\n', 2)):
        check(f"X4 {label} is COUNTED as unpaired", lambda t=text: _read(t)["unpaired_halves"], want)
    check("X4 an unpaired REMOVER half is unresolved, not dropped",
          lambda: unres('1 <... unlinkat resumed>"x", 0) = 0\n'), 1)
    # What `unresolved` means: a remover whose path is not written on its line.
    check("unresolved: a relative unlink (no dirfd, so no -yy label) is unresolved; an absolute one is not",
          lambda: unres('1 unlink(".git/objects/e3/tmp_obj_x") = 0\n1 unlink("/tmp/a") = 0\n'), 1)
    check("unresolved: a rename names TWO paths, each judged, the DESTINATION too: a relative path under a labelled "
          "dirfd is nameable, an undecorated or dirfd-less relative one is not",
          lambda: unres('1 renameat(3</d>, "a", AT_FDCWD, "b") = 0\n1 rename("/tmp/a", "rel") = 0\n'), 2)
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
    # X5 (Low): a pid's pending half is orphaned at its exit; a later resumed half on that pid pairs with nothing.
    for how in ("exited with 0", "killed by SIGKILL"):
        check(f"r2 X5 an unfinished remover half is orphaned at `+++ {how} +++`: both halves unpaired and unresolved",
              lambda h=how: (lambda r: (r["unpaired_halves"], r["unresolved_removal_count"]))(
                  _read(f'7 unlinkat(3</external>, <unfinished ...>\n7 +++ {h} +++\n'
                        '7 <... unlinkat resumed>"victim", 0) = 0\n')), (2, 2))
    # X2 (Medium): one measured record made the whole merge "measured".
    measured, unknown = _shard(1, 2, "measured.py", 1, 2, {"unpaired_halves": 0}), _shard(2, 2, "unknown.py", 1, 2)
    check("r2 X2 Codex's input: a merge where one target never measured pairing reports null, not {}",
          lambda: _merge([[measured, unknown]], "unpaired_halves"), None)
    check("r2 X2 ... and says how many (target, seed) records measured it",
          lambda: _merge([[measured, unknown]], "unpaired_halves_coverage"), {"measured": 1, "records": 2})
    check("r2 X2 every record measured, none unpaired: {} (none observed), not null",
          lambda: _merge([[measured, _shard(2, 2, "other.py", 1, 2, {"unpaired_halves": 0})]], "unpaired_halves"), {})
    # X3 (Medium): the sample store case supplied the only sample it checked. From an EMPTY store: insertion AND owner.
    check("r2 X3 an EMPTY sample store gains the line, credited to the target that logged it",
          lambda: (lambda st: (_read('1 unlink("/t/x") = 0\n', samples=st, who="second.py"), st)[1])({}),
          {("unlink", "= N"): {"line": '1 unlink("/t/x") = 0', "target": "second.py"}})
    # X4 (Medium): the two-directory case's answer came from the last directory alone.
    two_dirs = [[_shard(1, 2, "a.py", 1, 5)], [_shard(2, 2, "b.py", 1, 7)]]
    check("r2 X4 shards split across TWO directories: BOTH targets are merged",
          lambda: _merge(two_dirs, "spawner_targets"), ["a.py", "b.py"])
    check("r2 X4 ... and both shards are present", lambda: _merge(two_dirs, "shards_present"), [1, 2])

    # ── review round 3 (docs/reviews/claude/586-slice1-r3-claude.md) ──
    # F6: the r2 X2 rule over the CLASS: every analyse_log table is null unless every record was analysed.
    seen = {"syscalls": {"unlink": 1}, "family_counts": {"io_uring_setup": 1}, "deleted_labels": 2,
            "unresolved_removal_count": 3}
    nolog = {"log_missing": True}
    half = [[_shard(1, 2, "t.py", 1, 2, seen), _shard(2, 2, "u.py", 1, 2, nolog)]]
    for key in ("refusal_triggers", "deleted_labels", "unresolved_removals", "syscalls", "removal_calls"):
        check(f"r3 F6 a record with no log makes `{key}` null (NOT MEASURED), not a silent absence",
              lambda k=key: _merge(half, k), None)
    check("r3 F6 ... and the merge names the record whose log is missing",
          lambda: _merge(half, "analysis_coverage"), {"analysed": 1, "records": 2, "log_missing": [["u.py", "0"]]})
    whole = [[_shard(1, 2, "t.py", 1, 2, seen), _shard(2, 2, "u.py", 1, 2, {"syscalls": {"read": 1}})]]
    check("r3 F6 every record analysed: the tables are read (refusal triggers)",
          lambda: _merge(whole, "refusal_triggers"), {"io_uring_setup": ["t.py"]})
    check("r3 F6 every record analysed: unresolved removals",
          lambda: _merge(whole, "unresolved_removals"), {"t.py": 3})

    # The raw remover counts per target (backlog #601): the MAX over a target's seeds, removers only.
    def _two_seeds(a: int, b: int) -> dict:
        sh = _shard(1, 1, "t.py", 1, 2)
        sh["seeds"] = [0, 1]
        sh["targets"]["t.py"] = {str(seed): {"plain": {"secs": 1, "cases": 1, "green": True},
                                             "traced": {"secs": 2, "cases": 1, "green": True, "spawner": True,
                                                        "syscalls": {"unlink": n, "rename": 1, "read": 9}}}
                                 for seed, n in ((0, a), (1, b))}
        return sh
    check("removal_calls: a target's remover count is the MAX over its seeds (not the sum); non-removers are not kept",
          lambda: _merge([[_two_seeds(3, 5)]], "removal_calls"), {"t.py": {"rename": 1, "unlink": 5}})

    # Low findings.
    check("F5 a REMOVER line the splitter cannot balance is unresolved, never dropped",
          lambda: unres('100 unlinkat(3</home/runner/a<b>, "f", 0) = 0\n'), 1)
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

#!/usr/bin/env python3
"""Measure strace on the runner: what every manifest target's `--self-test` does under `strace -f -yy`.

    python3 scripts/strace-measure.py --shard I/N --seeds A,B --out DIR   # writes DIR/shard-I.json (+ raw lines)
    python3 scripts/strace-measure.py --merge DIR... --out FILE [--jobs JOBS.json]   # the merged summary

A MEASUREMENT INSTRUMENT, not a guard (backlog #586 plan, slice 1, Task 1.1): no `--self-test`, no caller but
`.github/workflows/strace-measure.yml`. Its output is reviewed by hand, and slice 3's subset case pins what
the parser's tables may hold against it. It supplies the constants the later slices pin: `STRACE_VERSION`,
`MEASURED_SYSCALLS`, `MEASURED_IOCTLS`, `TRACE_FACTOR`, whether `-yy` decorates `AT_FDCWD`, and which suites trip
a refusal trigger (spec §2, "The build plan's FIRST step").

Per target in the shard, per seed: a PLAIN run, then a TRACED run (`strace -f -yy -o <log> python3 <target>
--self-test`), each in a FRESH `stage_tree` copy with a fresh `CHILD_HOME`, under `mutation_env(copy, seed)`,
timeout `SUITE_TIMEOUT * 10`. The harness's own pieces are loaded with importlib (the spike's method), so the
staged tree, the environment and the green test are exactly the ones `--mutate` uses.

⚠ WHAT IT DOES NOT DO. It does not parse paths into read sets (slice 2 does, from the raw lines kept here),
and it tracks no cwd: a relative unlink/rename/rmdir whose directory it cannot name from a `-yy` label is listed
as UNRESOLVED, never guessed to be inside or outside the copy. "Created earlier in the same log" is a path a
successful creating call (an `O_CREAT` open, `mkdir*`, the new side of `rename*`/`link*`/`symlink*`) produced,
or any path under such a directory.
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
# into `name(args <unfinished ...>` and a later `<... name resumed>rest`.
LINE = re.compile(r"^(\d+)\s+(?:<\.\.\. ([A-Za-z_0-9]+) resumed>(.*)|([A-Za-z_][A-Za-z_0-9]*)\((.*))$")
SIGNAL = re.compile(r"^(\d+)\s+--- (SIG[A-Z0-9]+|[A-Z]+) ")
EXITED = re.compile(r"^(\d+)\s+\+\+\+ (exited|killed) ")
RETURN = re.compile(r"\)\s+= (-?\d+|0x[0-9a-f]+|\?)(<[^\n]*>)?(?: (E[A-Z0-9]+))?")
FAMILY = {"unshare", "setns", "chroot", "pivot_root", "mount", "umount2", "open_tree", "move_mount", "fsopen",
          "fsmount", "fspick", "mount_setattr", "io_uring_setup"}
REMOVERS = {"unlink", "unlinkat", "rmdir", "rename", "renameat", "renameat2"}
FORKS = {"clone", "clone3", "fork", "vfork"}
KEEP_FAMILY_LINES = 20
KEEP_SHAPES = 200


def split_args(s: str) -> "list[str] | None":
    """The top-level arguments of `s` (the text after `name(`), up to the matching `)`. None if it never
    closes (an `<unfinished ...>` line, or a shape this splitter cannot balance). Quotes, (), [], {} and -yy
    labels (a `<` after an alphanumeric or `]`, nesting inside a label) are respected."""
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
            return [a for a in args if a != ""] if args != [""] else []
        elif not stack and c == ",":
            args.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    return None


def unquote(arg: str) -> "str | None":
    """The path a strace string argument names, C escapes decoded. None if `arg` is not a whole string."""
    m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', arg)
    if not m:
        return None
    raw, out, i = m.group(1), bytearray(), 0
    while i < len(raw):
        c = raw[i]
        if c != "\\":
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


def label_of(arg: str) -> "str | None":
    """The path inside a dirfd's -yy label (`3</a/b>`, `AT_FDCWD</cwd>`). None if undecorated."""
    m = re.fullmatch(r"(?:\d+|AT_FDCWD)<(.*)>", arg)
    return m.group(1) if m else None


def resolve(dirfd: "str | None", path_arg: str) -> "str | None":
    p = unquote(path_arg)
    if p is None:
        return None
    if p.startswith("/"):
        return os.path.normpath(p)
    base = label_of(dirfd) if dirfd is not None else None
    return os.path.normpath(os.path.join(base, p)) if base else None


def removed_and_created(name: str, args: list, ok: bool, ret_label: "str | None"):
    """`(removed, created)`: the (dirfd, path-arg) pairs this call removes or replaces, and the resolved paths it
    creates if it succeeded."""
    removed, created = [], []
    a = args
    if name in ("unlink", "rmdir") and a:
        removed.append((None, a[0]))
    elif name == "unlinkat" and len(a) >= 2:
        removed.append((a[0], a[1]))
    elif name == "rename" and len(a) >= 2:
        removed += [(None, a[0]), (None, a[1])]
        created.append(resolve(None, a[1]))
    elif name in ("renameat", "renameat2") and len(a) >= 4:
        removed += [(a[0], a[1]), (a[2], a[3])]
        created.append(resolve(a[2], a[3]))
    if ok:
        if name in ("open", "creat") and a and (name == "creat" or "O_CREAT" in "".join(a[1:])):
            created.append(ret_label or resolve(None, a[0]))
        elif name in ("openat", "openat2") and len(a) >= 3 and "O_CREAT" in "".join(a[2:]):
            created.append(ret_label or resolve(a[0], a[1]))
        elif name == "mkdir" and a:
            created.append(resolve(None, a[0]))
        elif name == "mkdirat" and len(a) >= 2:
            created.append(resolve(a[0], a[1]))
        elif name in ("link", "symlink") and len(a) >= 2:
            created.append(resolve(None, a[1]))
        elif name == "linkat" and len(a) >= 4:
            created.append(resolve(a[2], a[3]))
        elif name == "symlinkat" and len(a) >= 3:
            created.append(resolve(a[1], a[2]))
    return removed, [c for c in created if c]


def shape(line: str) -> str:
    """A line with its varying parts blanked: pid, strings, labels, numbers."""
    s = re.sub(r"^\d+\s+", "", line)
    s = re.sub(r'"(?:[^"\\]|\\.)*"(?:\.\.\.)?', '"S"', s)
    s = re.sub(r"<(?:[^<>]|<[^<>]*>)*>", "<L>", s)
    s = re.sub(r"0x[0-9a-f]+", "X", s)
    return re.sub(r"\d+", "N", s)


def return_tags(line: str) -> "set[str]":
    tags = set()
    if line.endswith("<unfinished ...>"):
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
    family_lines, removals, unresolved, unparsed = [], [], [], []
    created: list = []
    root_pid = None
    at_fdcwd = deleted = forks = threads = 0
    execs: set = set()

    def is_created(p: str) -> bool:
        return any(p == c or p.startswith(c.rstrip("/") + "/") for c in created)

    def inside(p: str) -> bool:
        return any(p == c or p.startswith(c + "/") for c in copies)

    with open(log, encoding="utf-8", errors="surrogateescape") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line:
                continue
            sig, ex = SIGNAL.match(line), EXITED.match(line)
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
            syscalls[name] = syscalls.get(name, 0) + 1
            if "AT_FDCWD<" in line:
                at_fdcwd += 1
            deleted += line.count(" (deleted)>")
            for tag in return_tags(line):
                if (name, tag) not in samples:
                    samples[(name, tag)] = {"line": line, "target": who}
            if m.group(2):          # a resumed tail: its arguments were on the unfinished line
                continue
            body = m.group(5)
            if name in FORKS:
                key = "spawn: " + shape(line)
                if key not in shapes and len(shapes) < KEEP_SHAPES:
                    shapes[key] = {"line": line, "target": who}
                if "CLONE_THREAD" in body:
                    threads += 1
                else:
                    forks += 1
            if name in FAMILY:
                family_counts[name] = family_counts.get(name, 0) + 1
                if len(family_lines) < KEEP_FAMILY_LINES:
                    family_lines.append(line)
            unfinished = body.endswith("<unfinished ...>")
            # An unfinished call's arguments are whole on its line; only its return is elsewhere. It is read
            # as NOT succeeded, so it never counts as creating anything (toward reporting more, not less).
            args = split_args(body[:-len("<unfinished ...>")].rstrip() + ")" if unfinished else body)
            if name == "execve" and pid != root_pid:
                ex_path = re.match(r'("(?:[^"\\]|\\.)*")', body)
                if ex_path and unquote(ex_path.group(1)) is not None:
                    execs.add(unquote(ex_path.group(1)))
            if name == "ioctl" and args and len(args) >= 2:
                ioctls[args[1]] = ioctls.get(args[1], 0) + 1
            if args is None or (name not in REMOVERS and name not in (
                    "open", "openat", "openat2", "creat", "mkdir", "mkdirat", "link", "linkat", "symlink",
                    "symlinkat")):
                continue
            r = None if unfinished else RETURN.search(body)
            ok = bool(r) and r.group(1) not in ("-1", "?")
            ret_label = r.group(2)[1:-1] if r and r.group(2) else None
            removed, made = removed_and_created(name, args, ok, ret_label)
            for dirfd, parg in removed:
                p = resolve(dirfd, parg)
                if p is None:
                    unresolved.append(line)
                elif not inside(p) and not is_created(p):
                    removals.append({"path": p, "line": line})
            created += made
    return {"syscalls": syscalls, "ioctls": ioctls, "at_fdcwd_decorated_lines": at_fdcwd,
            "deleted_labels": deleted, "family_counts": family_counts, "family_lines": family_lines,
            "external_removals": removals[:50], "external_removal_count": len(removals),
            "unresolved_removals": unresolved[:20], "unresolved_removal_count": len(unresolved),
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
        cmd = [sys.executable, target, "--self-test"]
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
    syscalls, ioctls, family, deleted, removals, unresolved = {}, {}, {}, {}, {}, {}
    ratios, case_diff, red, timeouts, unparsed, strace_err = [], [], [], [], {}, {}
    at_fdcwd_targets = set()
    targets = {}
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
                if tr.get("external_removal_count"):
                    removals.setdefault(t, set()).update(x["path"] for x in tr["external_removals"])
                if tr.get("unresolved_removal_count"):
                    unresolved[t] = max(unresolved.get(t, 0), tr["unresolved_removal_count"])
                if tr.get("unparsed_lines"):
                    unparsed[t] = tr["unparsed_lines"][:3]
                if tr.get("strace_stderr"):
                    strace_err[t] = tr["strace_stderr"]
                if pl.get("secs") and tr.get("secs") is not None:
                    ratios.append({"target": t, "seed": seed, "spawner": tr.get("spawner"),
                                   "plain": pl["secs"], "traced": tr["secs"],
                                   "ratio": round(tr["secs"] / pl["secs"], 2)})
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
    worst = max(spawner_ratios, key=lambda r: r["ratio"], default=None)
    doc = {
        "headers": [json.loads(h) for h in sorted(headers)],
        "shards_present": [s["shard"][0] for s in shards], "shards_expected": total,
        "seeds": shards[0]["seeds"], "target_count": len(targets),
        "syscalls": {k: len(v) for k, v in sorted(syscalls.items())},
        "ioctls": {k: len(v) for k, v in sorted(ioctls.items())},
        "at_fdcwd_decorated": bool(at_fdcwd_targets), "at_fdcwd_decorated_targets": len(at_fdcwd_targets),
        "refusal_triggers": {k: sorted(v) for k, v in sorted(family.items())},
        "deleted_labels": dict(sorted(deleted.items())),
        "external_removals": {k: sorted(v) for k, v in sorted(removals.items())},
        "unresolved_removals": dict(sorted(unresolved.items())),
        "unparsed_line_samples": dict(sorted(unparsed.items())),
        "strace_stderr": dict(sorted(strace_err.items())),
        "trace_factor": None if worst is None else math.ceil(worst["ratio"]),
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--shard", help="I/N, 1-based")
    ap.add_argument("--seeds", help="A,B: PYTHONHASHSEED values, each run under every one")
    ap.add_argument("--merge", nargs="+", type=pathlib.Path, help="directories holding shard-*.json")
    ap.add_argument("--jobs", type=pathlib.Path, help="with --merge: `gh run view --json jobs` output")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args(argv)
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

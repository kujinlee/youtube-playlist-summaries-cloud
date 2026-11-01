#!/usr/bin/env python3
"""The per-PR gate battery in ONE call, one line per gate, skipping what a last green already answered.

    python3 scripts/gates-for-pr.py                 # run the battery; skip gates whose inputs are unchanged
    python3 scripts/gates-for-pr.py --no-skip       # run every gate (greens are still recorded)
    python3 scripts/gates-for-pr.py --list          # the gate set and where each came from; runs nothing
    python3 scripts/gates-for-pr.py --self-test  # 61 cases

    0 = every gate in the set PASSED or was SKIPPED   1 = a gate FAILED
    2 = CANNOT RUN — the set could not be derived, or a gate ended CANNOT RUN / TIMEOUT / KILLED

WHY THIS EXISTS (backlog #438). The 2026-10-30 usage study measured 1,306 gate commands that finished in
under 10 s, each issued as its own Bash call, and 152 re-runs of one check over an unchanged tree (93 of
them the mutation sweep); 44 runs hit the 10-minute limit. One call per battery, and a skip for a gate
whose inputs have not moved, removes both. A battery cut off by that limit is RESUMABLE: each green is
recorded the moment its gate ends, so the next call skips what already passed.

THE GATE SET IS DERIVED, NEVER LISTED BY HAND:
  * every step of `ci.yml`'s `verify` job whose `run:` is ONE `python3 scripts/<x>.py …` line. A PR-only
    step's `"origin/$GITHUB_BASE_REF"` becomes `origin/<--base>`. Everything else in the job (node, a
    multi-line block, another CI variable, `NOT_LOCAL`) is printed as OUT OF SET with its reason, so the
    reader sees what this run does NOT claim. `schema-gates.yml` is out of set: it needs CI's Postgres.
  * one `check-plan-code.py --mutate . --only <script>` per script a moved file touches (the script, or
    a manifest naming it) — the owner's LOCAL rule, partial here, the full sweep in CI's shards.

THE INPUT DIGEST IS MEASURED, NOT DECLARED. Each gate runs under an audit-hook tracer (a generated
`sitecustomize` on `PYTHONPATH`, so its Python children are traced too). What it opened and listed, inside
the repository or out, is its input set; the digest hashes those contents now plus: the interpreter
version, the gate's arguments, TODAY'S DATE (a gate may read the clock), the variables `ENV_DIGESTED`
names, and the NAME LIST of every non-ignored file in the tree (a gate may only `stat` a path, which no
audit event reports, so any add or delete re-runs every gate). A gate that runs `git` in the repository
also takes HEAD, the uncommitted diff, the untracked files and every revision its git commands NAME as
input — or EVERY ref, for a command that enumerates them (`git_refs`). A skip is a match of the LAST
GREEN's input set, re-digested now.

NEVER SKIPPED, AND THE LINE SAYS WHY: a gate that runs anything other than Python or `git` (`gh`, `node`,
a shell), a Python child the tracer cannot follow (`-I`/`-E`/`-S`, or an environment without the tracer),
`os.system`, a write inside the repository, or a tracer that did not load.

NEVER RECORDED GREEN: any exit but 0, a TIMEOUT or a signal (the runner itself being killed records
nothing for the gate in flight — the record is written only after it ends), and a PASS whose inputs, the
tree's file list, or (for a git-reading gate) the tree or ANY ref moved while it ran.

⚠ BOUNDS, STATED RATHER THAN HIDDEN. Environment variables outside `ENV_DIGESTED` are not digested. A
`stat` of a path OUTSIDE the repository is not seen. A gate that answers differently on the same inputs
(the network, randomness) is assumed not to exist outside the never-skip list above. The tracer costs
about 30% of a gate's run time (measured: 29 s plain, 37.5 s traced, `check-rc-contract --self-test`).
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

import fixture_git

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = Path(".github/workflows/ci.yml")
CI_JOB = "verify"
LEDGER_DIR = Path(".claude/gates-for-pr")      # under the MAIN checkout, git-ignored
LEDGER_FILE = "last-green.json"
KEEP_PER_GATE = 4
DEFAULT_TIMEOUT = 300
BASE_REF = '"origin/$GITHUB_BASE_REF"'
PY_RUN = re.compile(r"^python3\s+(scripts/[\w.-]+\.py)(.*)$")
ENV_DIGESTED = re.compile(r"^(CI|HOME|TZ|LANG|LC_\w+|GITHUB_\w+|ALLOW_\w+)$")

# CI steps that pass the `python3 scripts/…` shape but read something only an EARLIER CI step produces.
# A name here that no longer matches a step REFUSES the run, so the list cannot silently go stale.
NOT_LOCAL: dict[str, str] = {
    "Roadmap test counts match the suite": "reads jest-results.json, which only CI's `npm test` step writes",
}


def _load(alias: str, filename: str):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def _pin():
    return sys.modules.get("_g4pr_pin") or _load("_g4pr_pin", "check-python-pin.py")


def _merge_ready():
    return sys.modules.get("_g4pr_mr") or _load("_g4pr_mr", "check-merge-ready.py")


# ── the gate set ──────────────────────────────────────────────────────────────────────────────────


class Gate(NamedTuple):
    name: str                    # the CI step's name, or the mutation slice's
    script: str                  # repository-relative
    args: tuple[str, ...]
    source: str

    @property
    def mode(self) -> str:
        return " ".join(self.args) or "(no arguments)"


def step_keys(step) -> dict[str, str]:
    """PURE. A step's OWN keys — the dash line and the lines at its key indent, never a `run: |` body."""
    keys: dict[str, str] = {}
    lines = [step.body[0]] + [ln for ln in step.body[1:]
                             if len(ln) - len(ln.lstrip()) == step.indent + 2]
    for ln in lines:
        m = re.match(r"^\s*([A-Za-z_][\w-]*):\s*(.*?)\s*$", ln)
        if m and m.group(1) not in keys:
            keys[m.group(1)] = m.group(2)
    return keys


def ci_gates(workflow: str, base: str) -> tuple[list[Gate], list[tuple[str, str]], str | None]:
    """PURE. (gates, out-of-set steps with the reason, an error that makes the set underivable)."""
    blocks = _pin().job_blocks(workflow)
    if CI_JOB not in blocks:
        return [], [], f"the workflow has no `{CI_JOB}` job"
    pr_only = _merge_ready().PR_ONLY_COND
    gates: list[Gate] = []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for step in _pin()._steps(blocks[CI_JOB]):
        keys = step_keys(step)
        run = keys.get("run")
        if run is None:
            continue                       # a `uses:` action — setup, not a gate
        name = keys.get("name") or run
        seen.add(name)
        if name in NOT_LOCAL:
            out.append((name, NOT_LOCAL[name]))
            continue
        cond = keys.get("if", "")
        if cond and not pr_only.search(cond):
            out.append((name, f"runs only when `{cond}`"))
            continue
        if run[:1] in ("|", ">"):
            out.append((name, "a multi-line CI step: it needs CI's own context (the PR body, step outputs)"))
            continue
        line = run.replace(BASE_REF, f"origin/{base}")
        m = PY_RUN.match(line)
        if not m:
            out.append((name, f"not a Python gate: `{run}`"))
            continue
        if "$" in line:
            out.append((name, "reads a variable only CI sets"))
            continue
        gates.append(Gate(name, m.group(1), tuple(shlex.split(m.group(2))), f"ci.yml job {CI_JOB}"))
    if not gates:
        return [], out, f"the `{CI_JOB}` job yielded no Python gate — a parse that finds nothing is not a pass"
    stale = sorted(set(NOT_LOCAL) - seen)
    if stale:
        return [], [], f"NOT_LOCAL names a step the `{CI_JOB}` job no longer has: {', '.join(stale)}"
    return gates, out, None


def mutation_targets(changed: set[str], manifests: dict[str, set[str]]) -> list[str]:
    """PURE. Scripts whose mutation slice must run: named by a moved manifest, or moved themselves."""
    out: set[str] = set()
    for manifest, files in manifests.items():
        if manifest in changed:
            out |= files
        out |= files & changed
    return sorted(out)


def mutation_gates(targets: list[str]) -> list[Gate]:
    return [Gate(f"mutations of {t}", "scripts/check-plan-code.py", ("--mutate", ".", "--only", t),
                 "the local partial sweep (moved manifests only; CI runs them all)") for t in targets]


# ── the trace: what a gate read, and whether that is all it read ──────────────────────────────────


TRACER = r'''
import os as _o, sys as _s, json as _j, threading as _t
_TRACE, _SITE = {trace!r}, {site!r}
def _chain():
    import importlib.machinery as m, importlib.util as u
    spec = m.PathFinder.find_spec("sitecustomize", [p for p in _s.path if _o.path.abspath(p or ".") != _SITE])
    if spec and spec.loader:
        spec.loader.exec_module(u.module_from_spec(spec))
_chain()
_SKIP = tuple(_o.path.realpath(p) + _o.sep for p in {{_s.base_prefix, _s.prefix, _s.exec_prefix}})
_fd = _o.open(_o.path.join(_TRACE, "%d-%d.jsonl" % (_o.getpid(), id(_s))), _o.O_WRONLY | _o.O_CREAT | _o.O_APPEND, 0o600)
_tl = _t.local()
_WF = _o.O_WRONLY | _o.O_RDWR | _o.O_CREAT | _o.O_TRUNC | _o.O_APPEND
_EV = frozenset(("open", "os.listdir", "os.scandir", "os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.replace",
                 "os.symlink", "os.link", "os.truncate", "shutil.rmtree", "subprocess.Popen", "os.posix_spawn",
                 "os.exec", "os.spawn", "os.system"))
def _w(rec):
    _o.write(_fd, (_j.dumps(rec) + "\n").encode())
def _abs(p):
    return None if isinstance(p, int) or p is None else _o.path.abspath(_o.fsdecode(p))
def _fdpath(fd):
    # shutil.rmtree and os.fwalk list a directory by DESCRIPTOR; name it, or say it cannot be named.
    try:
        import fcntl
        return _o.fsdecode(fcntl.fcntl(fd, fcntl.F_GETPATH, bytes(1024))).rstrip("\0")
    except (ImportError, AttributeError, OSError):
        pass
    try:
        return _o.readlink("/proc/self/fd/%d" % fd)
    except OSError:
        return None
def _traced(env):
    e = _o.environ if env is None else env
    pp = e.get("PYTHONPATH") if "PYTHONPATH" in e else e.get(b"PYTHONPATH")
    pp = _o.fsdecode(pp) if pp else ""
    return _SITE in pp.split(_o.pathsep)
def _spawn(argv, cwd, env):
    argv = [argv] if isinstance(argv, (str, bytes)) else list(argv or [])
    _w({{"k": "p", "argv": [_o.fsdecode(a) if isinstance(a, (str, bytes)) else str(a) for a in argv],
        "cwd": _abs(cwd) or _o.getcwd(), "traced": _traced(env)}})
def _hook(ev, a):
    if ev not in _EV or getattr(_tl, "busy", False):
        return
    _tl.busy = True
    try:
        if ev == "open":
            p = _abs(a[0])
            if p is None or p.startswith(_SKIP) or "__pycache__" in p:
                return
            mode, flags = a[1], a[2] or 0
            w = any(c in mode for c in "wax+") if isinstance(mode, str) else bool(flags & _WF)
            _w({{"k": "w" if w else "r", "p": p}})
        elif ev in ("os.listdir", "os.scandir"):
            p = _fdpath(a[0]) if isinstance(a[0], int) else _abs(a[0] if a[0] is not None else ".")
            _w({{"k": "d", "p": p}} if p else {{"k": "u", "why": ev + " on a descriptor whose path is unknown"}})
        elif ev in ("os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.replace", "os.symlink", "os.link",
                    "os.truncate", "shutil.rmtree"):
            for x in a[:2]:
                if isinstance(x, (str, bytes, _o.PathLike)):
                    _w({{"k": "w", "p": _abs(x)}})
        elif ev == "subprocess.Popen":
            _spawn(a[1], a[2], a[3])
        elif ev in ("os.posix_spawn", "os.exec"):
            _spawn(a[1], None, a[2])
        elif ev == "os.spawn":
            _spawn(a[2], None, a[3])
        else:
            _w({{"k": "u", "why": "os.system runs a shell"}})
    except Exception as e:
        try:
            _w({{"k": "u", "why": ("the tracer failed on %s: %r" % (ev, e))[:200]}})
        except Exception:
            pass
    finally:
        _tl.busy = False
_w({{"k": "start", "pid": _o.getpid()}})
_s.addaudithook(_hook)
'''


class Inputs(NamedTuple):
    files: tuple[str, ...]       # repository-relative, or absolute when outside it
    dirs: tuple[str, ...]
    git: tuple[tuple[str, ...], ...] = ()   # each git command run IN the repository, argv after `git`

    @property
    def tree(self) -> bool:
        return bool(self.git)


def ignored_roots() -> tuple[str, ...]:
    roots = {tempfile.gettempdir(), "/tmp", "/var/folders", "/dev", sys.base_prefix, sys.prefix, sys.exec_prefix}
    return tuple(sorted({os.path.realpath(r).rstrip(os.sep) + os.sep for r in roots}))


def place(path: str, root: str, ignored: tuple[str, ...]) -> str | None:
    """PURE but for `realpath`. The ledger's name for a path: repository-relative, absolute, or None (not an
    input — a temp file the gate made, the interpreter's own files, a device). The repository wins over
    `ignored`, because a checkout may itself sit under a temp directory."""
    real = os.path.realpath(path)
    if "__pycache__" in real.split(os.sep):
        return None
    if real == root or real.startswith(root + os.sep):
        return os.path.relpath(real, root)
    if real.startswith(ignored) or real + os.sep in ignored:
        return None
    return real


def _is_python(argv0: str) -> bool:
    return bool(re.fullmatch(r"python[\d.]*", os.path.basename(argv0))) or \
        os.path.realpath(argv0) == os.path.realpath(sys.executable)


def _untraceable_flag(argv: list[str]) -> str | None:
    for tok in argv[1:]:
        if not tok.startswith("-") or tok.startswith("--"):
            return None
        if tok in ("-c", "-m"):
            return None
        hit = [c for c in "IES" if c in tok[1:]]
        if hit:
            return f"-{hit[0]}"
    return None


def classify(records: list[dict], root: str, ignored: tuple[str, ...]) -> tuple[Inputs | None, str]:
    """PURE but for `realpath`. The gate's input set, or (None, why it cannot be bounded)."""
    if not any(r.get("k") == "start" for r in records):
        return None, "the tracer did not load, so what it read is unknown"
    files: set[str] = set()
    dirs: set[str] = set()
    gits: set[tuple[str, ...]] = set()
    for r in records:
        k = r.get("k")
        if k == "u":
            return None, r.get("why", "an untraceable operation")
        if k in ("r", "d"):
            p = place(r["p"], root, ignored)
            if p is not None:
                (files if k == "r" else dirs).add(p)
        elif k == "w":
            p = place(r["p"], root, ignored)
            if p is not None and not os.path.isabs(p):
                return None, f"it writes {p} inside the repository"
        elif k == "p":
            argv = r.get("argv") or [""]
            prog = os.path.basename(argv[0])
            if _is_python(argv[0]):
                flag = _untraceable_flag(argv)
                if flag:
                    return None, f"it starts Python with {flag}, which the tracer cannot follow"
                if not r.get("traced"):
                    return None, "it starts Python in an environment without the tracer"
            elif prog == "git":
                cwd = r.get("cwd") or root
                if "-C" in argv[1:-1]:
                    cwd = os.path.join(cwd, argv[argv.index("-C") + 1])
                where = place(cwd, root, ignored)
                if where is None:
                    continue                       # git in a temp fixture the gate built
                if os.path.isabs(where):
                    return None, f"it runs git in {where}, outside the repository"
                gits.add(tuple(argv[1:]))
            else:
                return None, f"it runs {prog}, whose reads the tracer cannot see"
    return Inputs(tuple(sorted(files)), tuple(sorted(dirs)), tuple(sorted(gits))), ""


GIT_GLOBAL_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"})
# A command that ENUMERATES refs, or takes revisions on stdin, reads refs it never names.
GIT_BROAD = frozenset({"for-each-ref", "branch", "show-ref", "tag", "reflog", "fetch", "pull", "ls-remote",
                       "remote", "worktree", "describe", "name-rev", "show-branch", "pack-refs", "gc", "fsck",
                       "bundle", "push", "replace", "notes", "stash", "for-each-repo"})
GIT_BROAD_FLAGS = ("--all", "--branches", "--remotes", "--tags", "--glob", "--reflog", "--walk-reflogs", "-g",
                   "--stdin", "--batch", "--batch-check", "--batch-command")


def git_refs(argv: tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
    """PURE. (does this git command read refs it does not name, the revision-like words it names). `argv` is
    what follows `git`. A word that is a path, not a revision, costs one `missing` line in the digest."""
    args = list(argv)
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GIT_GLOBAL_WITH_VALUE else 1
    if i >= len(args):
        return False, ()
    sub, rest = args[i], args[i + 1:]
    if "--" in rest:
        rest = rest[:rest.index("--")]
    if sub in GIT_BROAD or any(r == f or r.startswith(f + "=") for r in rest for f in GIT_BROAD_FLAGS):
        return True, ()
    words: set[str] = set()
    for r in rest:
        if r.startswith("-"):
            if "=" not in r:
                continue
            r = r.split("=", 1)[1]
        for part in re.split(r"\.\.\.?", r):
            part = part.lstrip("^")
            if part and "\n" not in part:
                words.add(part)
    return False, tuple(sorted(words))


def read_trace(trace_dir: Path) -> list[dict]:
    out: list[dict] = []
    for f in sorted(trace_dir.glob("*.jsonl")):
        for line in f.read_text(errors="replace").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                out.append({"k": "u", "why": "a trace line was cut off"})
    return out


# ── the digest ────────────────────────────────────────────────────────────────────────────────────


class World:
    """What a digest reads: file contents, directory names, the tree's name list, and (for a gate that ran
    git in the repository) the tree and the refs. `today` and `env` are fields so a case can vary them."""

    def __init__(self, root: Path, today: str | None = None, env: dict[str, str] | None = None):
        self.root = root
        self.today = today or dt.date.today().isoformat()
        env = os.environ if env is None else env
        self.env = sorted((k, v) for k, v in env.items() if ENV_DIGESTED.match(k))
        self._memo: dict[str, str] = {}

    def invalidate(self) -> None:
        """Forget the tree-wide reads. Called after every gate runs: a run is what can move the tree."""
        self._memo.clear()

    def _once(self, key: str, fn) -> str:
        if key not in self._memo:
            self._memo[key] = fn()
        return self._memo[key]

    def _git(self, *args: str, stdin: bytes | None = None) -> bytes:
        p = subprocess.run(["git", "-C", str(self.root), *args], input=stdin, capture_output=True, timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.decode(errors='replace').strip()[:200]}")
        return p.stdout

    def _untracked(self) -> list[str]:
        raw = self._git("ls-files", "-o", "--exclude-standard", "-z").decode(errors="replace").split("\0")
        return [n for n in raw if n and not n.startswith(f"{LEDGER_DIR}/")]

    def names(self) -> str:
        return self._once("names", self._names)

    def _names(self) -> str:
        raw = self._git("ls-files", "-co", "--exclude-standard", "-z").decode(errors="replace").split("\0")
        keep = sorted(n for n in raw if n and not n.startswith(f"{LEDGER_DIR}/"))
        return hashlib.sha256("\0".join(keep).encode()).hexdigest()

    def core(self) -> str:
        """HEAD, the uncommitted diff and every untracked file's content: the tree as git would read it."""
        return self._once("core", self._core)

    def _core(self) -> str:
        h = hashlib.sha256()
        h.update(self._git("rev-parse", "HEAD"))
        h.update(self._git("diff", "HEAD", "--binary"))
        for n in self._untracked():
            h.update(f"{n}\0{self.content(n)}\n".encode())
        return h.hexdigest()

    def refs(self) -> str:
        return self._once("refs", lambda: hashlib.sha256(self._git("for-each-ref", "--format=%(refname) %(objectname)")).hexdigest())

    def named(self, words: tuple[str, ...]) -> str:
        if not words:
            return ""
        out = self._git("cat-file", "--batch-check", stdin=("\n".join(words) + "\n").encode())
        return hashlib.sha256(out).hexdigest()

    def tree(self, gits: tuple[tuple[str, ...], ...]) -> str:
        broad, words = False, set()
        for argv in gits:
            b, w = git_refs(argv)
            broad |= b
            words |= set(w)
        refs = self.refs() if broad else self.named(tuple(sorted(words)))
        return f"{self.core()} {refs}"

    def _path(self, p: str) -> Path:
        return Path(p) if os.path.isabs(p) else self.root / p

    def content(self, p: str) -> str:
        path = self._path(p)
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except IsADirectoryError:
            return "dir"
        except FileNotFoundError:
            return "absent"
        except OSError as e:
            return f"unreadable:{e.errno}"

    def listing(self, p: str) -> str:
        try:
            names = sorted(n for n in os.listdir(self._path(p)) if n not in ("__pycache__", ".DS_Store"))
        except FileNotFoundError:
            return "absent"
        except OSError as e:
            return f"unreadable:{e.errno}"
        return hashlib.sha256("\0".join(names).encode()).hexdigest()

    def mtime_ns(self, p: str) -> int:
        try:
            return self._path(p).stat().st_mtime_ns
        except OSError:
            return 0


def digest(inputs: Inputs, world: World) -> str:
    """The input digest: everything the last green read, read again now. Order-fixed, so it is a function
    of the inputs and nothing else. The gate and its mode are the ledger's KEY (`last_green`), not hashed
    here: a key a hash also carried could be dropped from the lookup with no case noticing."""
    h = hashlib.sha256()
    for part in ("gates-for-pr/1", sys.version, world.today, json.dumps(world.env), world.names()):
        h.update(part.encode() + b"\n")
    for f in inputs.files:
        h.update(f"f {f} {world.content(f)}\n".encode())
    for d in inputs.dirs:
        h.update(f"d {d} {world.listing(d)}\n".encode())
    if inputs.tree:
        h.update(f"t {world.tree(inputs.git)}\n".encode())
    return h.hexdigest()[:16]


def moved_during(inputs: Inputs, world: World, start_ns: int) -> str | None:
    """PURE over `world`. An input whose modification time is after the gate started, or None."""
    for p in inputs.files + inputs.dirs:
        if world.mtime_ns(p) > start_ns:
            return p
    return None


# ── the ledger ────────────────────────────────────────────────────────────────────────────────────


def read_ledger(path: Path) -> tuple[list[dict], str | None]:
    if not path.exists():
        return [], None
    try:
        data = json.loads(path.read_text())
        entries = data["green"]
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise ValueError("`green` is not a list of records")
        return entries, None
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [], f"the ledger {path} is unreadable ({e}); nothing is skipped and it will be rewritten"


def last_green(entries: list[dict], gate: Gate, world: World) -> str | None:
    """PURE over `world`. The digest of a last green for THIS gate and mode whose inputs still digest the
    same, or None. Keyed on (gate, input digest, mode): a green in one mode never answers another."""
    for e in reversed(entries):
        if e.get("gate") != gate.script or e.get("mode") != gate.mode:
            continue
        inp = e.get("inputs") or {}
        inputs = Inputs(tuple(inp.get("files", ())), tuple(inp.get("dirs", ())),
                        tuple(tuple(g) for g in inp.get("git", ())))
        if digest(inputs, world) == e.get("digest"):
            return e["digest"]
    return None


def record_green(path: Path, gate: Gate, d: str, inputs: Inputs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries, _ = read_ledger(path)
        entries.append({"gate": gate.script, "mode": gate.mode, "name": gate.name, "digest": d,
                        "inputs": {"files": list(inputs.files), "dirs": list(inputs.dirs),
                                   "git": [list(g) for g in inputs.git]},
                        "at": dt.datetime.now().isoformat(timespec="seconds")})
        mine = [e for e in entries if (e.get("gate"), e.get("mode")) == (gate.script, gate.mode)]
        drop = {id(e) for e in mine[:-KEEP_PER_GATE]}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 1, "green": [e for e in entries if id(e) not in drop]}))
        os.replace(tmp, path)


# ── running a gate ────────────────────────────────────────────────────────────────────────────────


class Outcome(NamedTuple):
    status: str                  # PASS | FAIL | CANNOT RUN | TIMEOUT | KILLED
    rc: int | None
    secs: float
    records: list[dict]


def status_of(rc: int | None, timed_out: bool) -> str:
    """PURE. Only a clean exit 0 is a PASS; the repo's exit 2 is CANNOT RUN, never a pass."""
    if timed_out:
        return "TIMEOUT"
    if rc is None or rc < 0:
        return "KILLED"
    return {0: "PASS", 2: "CANNOT RUN"}.get(rc, "FAIL")


def run_gate(gate: Gate, root: Path, timeout: float, log: Path) -> Outcome:
    work = Path(tempfile.mkdtemp(prefix="gates-for-pr-"))
    try:
        site, trace = work / "site", work / "trace"
        site.mkdir()
        trace.mkdir()
        (site / "sitecustomize.py").write_text(TRACER.format(trace=str(trace), site=str(site)))
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(site)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        start = time.monotonic()
        timed_out = False
        with open(log, "wb") as out:
            p = subprocess.Popen([sys.executable, gate.script, *gate.args], cwd=root, env=env, stdout=out,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                rc = p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
            except BaseException:
                _kill(p)
                raise
            if timed_out:
                _kill(p)
                rc = p.returncode
        return Outcome(status_of(rc, timed_out), rc, time.monotonic() - start, read_trace(trace))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _kill(p: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(p.pid, signal.SIGKILL)
    p.wait()


class Snapshot(NamedTuple):
    names: str
    core: str
    refs: str


def snapshot(world: World) -> Snapshot:
    return Snapshot(world.names(), world.core(), world.refs())


def unstable(inputs: Inputs, world: World, before: Snapshot, start_ns: int) -> str | None:
    """What moved while the gate ran, or None. A green over inputs that moved is not a green of anything."""
    moved = moved_during(inputs, world, start_ns)
    if moved:
        return moved
    if world.names() != before.names:
        return "the tree's file list"
    if inputs.tree and world.core() != before.core:
        return "the tree"
    if inputs.tree and world.refs() != before.refs:
        return "a ref"
    return None


# ── the run ───────────────────────────────────────────────────────────────────────────────────────


def changed_paths(root: Path, base: str) -> tuple[set[str] | None, str]:
    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, timeout=120)
    mb = git("merge-base", f"origin/{base}", "HEAD")
    if mb.returncode != 0:
        return None, f"origin/{base} does not resolve here ({mb.stderr.strip()[:120]})"
    diff = git("diff", "--name-only", mb.stdout.strip())
    new = git("ls-files", "-o", "--exclude-standard")
    if diff.returncode or new.returncode:
        return None, "git could not list the moved files"
    return set(diff.stdout.split()) | set(new.stdout.split()), ""


def manifest_files(root: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for m in sorted((root / "scripts" / "mutations").glob("*.json")):
        entries = json.loads(m.read_text())
        out[str(m.relative_to(root))] = {e["file"] for e in entries if isinstance(e, dict) and "file" in e}
    return out


def gate_set(root: Path, base: str) -> tuple[list[Gate], list[tuple[str, str]], str | None]:
    wf = root / WORKFLOW
    if not wf.is_file():
        return [], [], f"{WORKFLOW} is missing"
    gates, out, err = ci_gates(wf.read_text(), base)
    if err:
        return gates, out, err
    out.append(("schema-gates.yml", "needs CI's Postgres container — run scripts/check-schema-gates.sh"))
    changed, why = changed_paths(root, base)
    if changed is None:
        return gates, out, f"the mutation slices cannot be chosen: {why}"
    try:
        manifests = manifest_files(root)
    except (OSError, ValueError) as e:
        return gates, out, f"a mutation manifest is unreadable: {e}"
    return gates + mutation_gates(mutation_targets(changed, manifests)), out, None


def line(status: str, name: str, detail: str) -> str:
    return f"{status:<11} {name}  {detail}".rstrip()


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="master")
    ap.add_argument("--no-skip", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per gate")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    gates, out, err = gate_set(root, a.base)
    if err:
        print(f"CANNOT RUN — {err}. Treat this as NOT RUN.")
        return 2
    if a.list:
        for g in gates:
            print(line("GATE", g.name, f"{g.script} {g.mode} · {g.source}"))
        for name, why in out:
            print(line("OUT OF SET", name, f"— {why}"))
        return 0
    main_dir, why = _load("_g4pr_ss", "session-state.py").main_checkout(root)
    if why:
        print(f"CANNOT RUN — the ledger has no home: {why}. Treat this as NOT RUN.")
        return 2
    ledger = main_dir / LEDGER_DIR / LEDGER_FILE
    logs = Path(tempfile.mkdtemp(prefix="gates-for-pr-logs-"))
    world = World(root)
    entries, warn = read_ledger(ledger)
    if warn:
        print(f"WARNING — {warn}")
    print(f"gates-for-pr: {len(gates)} gates · ledger {ledger} · logs {logs}", flush=True)
    tally: dict[str, int] = {}
    for i, g in enumerate(gates):
        world.invalidate()              # time has passed since the last gate; read the tree afresh
        try:
            hit = None if a.no_skip else last_green(entries, g, world)
            before = snapshot(world)
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            print(f"CANNOT RUN — the tree cannot be digested: {e}. Treat this as NOT RUN.")
            return 2
        if hit:
            tally["SKIPPED"] = tally.get("SKIPPED", 0) + 1
            print(line("SKIPPED", g.name, f"(last green {hit})"), flush=True)
            continue
        log = logs / f"{i:03d}-{re.sub(r'[^A-Za-z0-9]+', '-', g.name)[:60]}.log"
        start_ns = time.time_ns()
        o = run_gate(g, root, a.timeout, log)
        world.invalidate()
        tally[o.status] = tally.get(o.status, 0) + 1
        detail = f"({o.secs:.1f}s)" if o.status == "PASS" else \
            f"rc={o.rc} ({o.secs:.1f}s) · not recorded · {log}" if o.status != "TIMEOUT" else \
            f"killed at {a.timeout:.0f}s · not recorded · {log}"
        if o.status == "PASS":
            inputs, why = classify(o.records, os.path.realpath(root), ignored_roots())
            if inputs is None:
                detail += f" · never skipped: {why}"
            else:
                inputs = inputs._replace(files=tuple(sorted(set(inputs.files) | {g.script})))
                moved = unstable(inputs, world, before, start_ns)
                if moved:
                    detail += f" · not recorded: {moved} changed while it ran"
                else:
                    record_green(ledger, g, digest(inputs, world), inputs)
        print(line(o.status, g.name, detail), flush=True)
    for name, why in out:
        print(line("OUT OF SET", name, f"— {why}"))
    order = ("PASS", "SKIPPED", "FAIL", "CANNOT RUN", "TIMEOUT", "KILLED")
    print("summary: " + " · ".join(f"{tally[s]} {s.lower()}" for s in order if tally.get(s))
          + f" · {len(out)} CI steps out of set (above)")
    if tally.get("FAIL"):
        return 1
    if tally.get("CANNOT RUN") or tally.get("TIMEOUT") or tally.get("KILLED"):
        return 2
    return 0


# ── self-test ─────────────────────────────────────────────────────────────────────────────────────


def self_test() -> int:
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    results: list[tuple[str, bool]] = []

    def case(name: str, got, want) -> None:
        ok = got == want
        results.append((name, ok))
        if not ok:
            print(f"  [FAIL] {name}\n       got:  {got!r}\n       want: {want!r}")

    # ── the derivation, over a workflow text ──
    wf = WF_FIXTURE
    gates, out, err = ci_gates(wf, "master")
    case("a one-line python step is a gate, with its arguments",
         [(g.name, g.script, g.args) for g in gates][:2],
         [("gate a", "scripts/a.py", ("--self-test",)), ("gate b", "scripts/b.py", ())])
    case("a PR-only step is IN the set, its base ref rewritten to --base",
         [g.args for g in gates if g.name == "pr only"], [("--base", "origin/master")])
    case("...and to a different --base when one is given",
         [g.args for g in ci_gates(wf, "main")[0] if g.name == "pr only"], [("--base", "origin/main")])
    case("node, a multi-line block, another CI variable and a non-PR condition are OUT OF SET, with reasons",
         sorted(n for n, _ in out), ["Roadmap test counts match the suite", "ci var", "multi", "node tests",
                                     "push only"])
    case("...and a `uses:` action is neither", any(n.startswith("actions/") for n, _ in out), False)
    case("a step NOT_LOCAL names is out of set with that reason",
         "jest-results" in dict(out).get("Roadmap test counts match the suite", ""), True)
    case("a NOT_LOCAL name that no longer matches a step REFUSES the set (it cannot go stale silently)",
         ci_gates(wf.replace("name: Roadmap test counts", "name: Renamed test counts"), "master")[2],
         "NOT_LOCAL names a step the `verify` job no longer has: Roadmap test counts match the suite")
    case("a workflow with no verify job cannot yield a set", ci_gates("jobs:\n  other:\n    steps: []\n", "m")[2],
         "the workflow has no `verify` job")
    case("a verify job with no python gate is CANNOT RUN, never an empty pass",
         "yielded no Python gate" in (ci_gates(WF_HEAD + "      - name: n\n        run: npm test\n", "m")[2] or ""),
         True)
    case("the live ci.yml yields a non-empty set with the namespace and fixture-variation gates in it",
         {"scripts/check-reference-namespace.py", "scripts/check-fixture-variation.py"} <=
         {g.script for g in ci_gates((ROOT / WORKFLOW).read_text(), "master")[0]}, True)
    # ── which mutation slices run ──
    mf = {"scripts/mutations/a.json": {"scripts/a.py"}, "scripts/mutations/b.json": {"scripts/b.py", "scripts/c.py"}}
    case("a moved script with a manifest gets its slice", mutation_targets({"scripts/a.py"}, mf), ["scripts/a.py"])
    case("a moved MANIFEST runs every script it names", mutation_targets({"scripts/mutations/b.json"}, mf),
         ["scripts/b.py", "scripts/c.py"])
    case("nothing moved, nothing runs", mutation_targets({"docs/x.md"}, {}), [])
    case("a slice is check-plan-code --mutate . --only <script>", mutation_gates(["scripts/a.py"])[0].args,
         ("--mutate", ".", "--only", "scripts/a.py"))
    case("...one slice per target, in order", [g.name for g in mutation_gates(["scripts/x.py", "scripts/y.py"])],
         ["mutations of scripts/x.py", "mutations of scripts/y.py"])
    # ── the status of an exit ──
    case("exit 0 is the only PASS", [status_of(rc, False) for rc in (0, 1, 2, 3, -9, None)],
         ["PASS", "FAIL", "CANNOT RUN", "FAIL", "KILLED", "KILLED"])
    case("a timeout is TIMEOUT whatever the exit code", status_of(0, True), "TIMEOUT")
    # ── which refs a git command reads ──
    case("a named revision and a range are the words a git command reads",
         git_refs(("log", "-1", "--format=%H", "origin/master..HEAD", "--", "docs")),
         (False, ("%H", "HEAD", "origin/master")))
    case("global options before the subcommand are skipped, values included",
         git_refs(("-C", "/r", "-c", "a=b", "rev-parse", "^x...y")), (False, ("x", "y")))
    case("a command that ENUMERATES refs reads them all", git_refs(("for-each-ref", "refs/heads")), (True, ()))
    case("...and so does --all, or revisions on stdin",
         [git_refs(("log", "--all"))[0], git_refs(("rev-list", "--stdin"))[0], git_refs(("cat-file", "--batch"))[0]],
         [True, True, True])
    # ── what a trace means ── (real directories, so macOS's `realpath` of /tmp and /home cannot move them)
    scratch = Path(tempfile.mkdtemp(prefix="gates-for-pr-cls-"))
    root, other = os.path.realpath(scratch / "repo"), os.path.realpath(scratch / "other")
    tmpd = os.path.realpath(scratch / "tmp")
    ign, ign2 = (tmpd + os.sep,), (os.path.realpath(scratch / "tmp2") + os.sep,)
    outside = "/nonexistent-gates-for-pr/.cfg"
    start = {"k": "start"}
    case("reads inside the repo are relative, outside are absolute, temp is dropped",
         classify([start, {"k": "r", "p": root + "/a.py"}, {"k": "r", "p": outside},
                   {"k": "r", "p": tmpd + "/f"}, {"k": "d", "p": root + "/docs"}], root, ign),
         (Inputs((outside, "a.py"), ("docs",)), ""))
    case("...the same reads against ANOTHER root and ANOTHER ignore list: nothing is relative, temp is kept",
         classify([start, {"k": "r", "p": root + "/a.py"}, {"k": "r", "p": tmpd + "/f"}], other, ign2),
         (Inputs((root + "/a.py", tmpd + "/f"), ()), ""))
    case("no start record: the tracer did not load, so the gate is unbounded",
         classify([{"k": "r", "p": root + "/a.py"}], root, ign)[1], "the tracer did not load, so what it read is unknown")
    case("a write inside the repository is unbounded", classify([start, {"k": "w", "p": root + "/out.html"}], root, ign)[1],
         "it writes out.html inside the repository")
    case("...a write to temp is not", classify([start, {"k": "w", "p": tmpd + "/x"}], root, ign)[0] is not None, True)
    case("python with -I cannot be followed",
         classify([start, {"k": "p", "argv": ["python3", "-I", "x.py"], "traced": True, "cwd": root}], root, ign)[1],
         "it starts Python with -I, which the tracer cannot follow")
    case("python in an environment without the tracer cannot be followed",
         classify([start, {"k": "p", "argv": ["/usr/bin/python3", "x.py"], "traced": False, "cwd": root}], root,
                  ign)[1], "it starts Python in an environment without the tracer")
    case("traced python with -c is followed",
         classify([start, {"k": "p", "argv": ["python3", "-c", "-I"], "traced": True, "cwd": root}], root, ign)[1],
         "")
    case("git in a temp fixture is bounded and adds nothing",
         classify([start, {"k": "p", "argv": ["git", "init"], "cwd": tmpd + "/fx"}], root, ign)[0], Inputs((), ()))
    case("git in the repository makes the tree, and that command's refs, an input",
         classify([start, {"k": "p", "argv": ["git", "diff", "origin/master"], "cwd": root + "/scripts"}], root,
                  ign)[0].git, (("diff", "origin/master"),))
    case("git -C <repo> from a temp cwd is still the repository",
         classify([start, {"k": "p", "argv": ["git", "-C", root, "log"], "cwd": tmpd}], root, ign)[0].tree, True)
    case("an untraceable operation the tracer reported is unbounded, with its reason",
         classify([start, {"k": "u", "why": "os.system runs a shell"}], root, ign)[1], "os.system runs a shell")
    case("any other program (gh, node, a shell) is unbounded",
         [classify([start, {"k": "p", "argv": [p, "x"], "cwd": root}], root, ign)[1] for p in ("gh", "/bin/sh")],
         ["it runs gh, whose reads the tracer cannot see", "it runs sh, whose reads the tracer cannot see"])
    shutil.rmtree(scratch, ignore_errors=True)
    # ── end to end: main() over a repository this case builds ──
    results.extend(_end_to_end())
    passed = sum(ok for _, ok in results)
    print(f"{passed}/{len(results)} cases passed")
    return 0 if passed == len(results) else 1


WF_HEAD = "on: [pull_request]\njobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n"
WF_SLOW = """\
      - name: slow
        run: python3 scripts/e.py
"""
WF_FIXTURE = WF_HEAD + """\
      - uses: actions/checkout@v4
      - name: gate a
        run: python3 scripts/a.py --self-test
      - name: gate b
        run: python3 scripts/b.py
      - name: reads a ref
        run: python3 scripts/g.py
      - name: shells out
        run: python3 scripts/c.py
      - name: cannot
        run: python3 scripts/d.py
""" + WF_SLOW + """\
      - name: dies
        run: python3 scripts/k.py
      - name: pr only
        if: github.event_name == 'pull_request'
        run: python3 scripts/f.py --base "origin/$GITHUB_BASE_REF"
      - name: node tests
        run: npm test
      - name: multi
        run: |
          python3 scripts/a.py
      - name: ci var
        run: python3 scripts/a.py --sha $GITHUB_SHA
      - name: push only
        if: github.event_name == 'push'
        run: python3 scripts/a.py
      - name: Roadmap test counts match the suite
        run: python3 scripts/a.py --results jest-results.json
"""

GATE_SCRIPTS = {
    "a.py": "from pathlib import Path\nPath({log!r}).open('a').write('a\\n')\nPath('data/a.txt').read_text()\n",
    "b.py": "from pathlib import Path\nPath({log!r}).open('a').write('b\\n')\nPath('data/b.txt').read_text()\n"
            "Path('data/flag').exists()\n",
    "g.py": "import subprocess\nfrom pathlib import Path\nPath({log!r}).open('a').write('g\\n')\n"
            "subprocess.run(['git', 'log', '-1', '--format=%H', 'origin/master'], check=True, capture_output=True)\n",
    "c.py": "import subprocess\nfrom pathlib import Path\nPath({log!r}).open('a').write('c\\n')\n"
            "subprocess.run(['/bin/sh', '-c', 'true'])\n",
    "d.py": "import sys\nfrom pathlib import Path\nPath({log!r}).open('a').write('d\\n')\nsys.exit(2)\n",
    "e.py": "import time\nfrom pathlib import Path\nPath({log!r}).open('a').write('e\\n')\ntime.sleep(30)\n",
    "k.py": "import os, signal\nfrom pathlib import Path\nPath({log!r}).open('a').write('k\\n')\n"
            "os.kill(os.getpid(), signal.SIGKILL)\n",
    "f.py": "from pathlib import Path\nPath({log!r}).open('a').write('f\\n')\n",
}


def _end_to_end() -> list[tuple[str, bool]]:
    res: list[tuple[str, bool]] = []

    def case(name: str, got, want) -> None:
        ok = got == want
        res.append((name, ok))
        if not ok:
            print(f"  [FAIL] {name}\n       got:  {got!r}\n       want: {want!r}")

    tmp = Path(tempfile.mkdtemp(prefix="gates-for-pr-st-"))
    try:
        repo, runs, empty = tmp / "repo", tmp / "runs.log", tmp / "empty"
        (repo / "scripts" / "mutations").mkdir(parents=True)
        (repo / "data").mkdir()
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / WORKFLOW).write_text(WF_FIXTURE)
        for n, body in GATE_SCRIPTS.items():
            (repo / "scripts" / n).write_text(body.format(log=str(runs)))
        (repo / "data" / "a.txt").write_text("a1")
        (repo / "data" / "b.txt").write_text("b1")
        empty.mkdir()

        def git(*a: str) -> None:
            subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True,
                           env=fixture_git.env(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                                               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e"))
        git("init", "-q", "-b", "master")
        git("add", "-A")
        git("commit", "-q", "-m", "one")
        git("update-ref", "refs/remotes/origin/master", "HEAD")

        def run(*extra: str) -> tuple[int, str, list[str]]:
            runs.write_text("")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--timeout", "1.5", *extra], root=repo)
            return rc, buf.getvalue(), runs.read_text().split()

        def status(out: str, name: str) -> str:
            for ln in out.splitlines():
                if re.match(rf"^\S+(?: RUN| OF SET)?\s+{re.escape(name)}(\s|$)", ln):
                    return ln.split("  ")[0].strip()
            return "MISSING"

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--list"], root=repo)
        case("--list names the gates and runs nothing",
             (rc, "GATE        gate a  scripts/a.py --self-test" in buf.getvalue(), runs.exists()), (0, True, False))

        rc, out, ran = run()
        case("first run: every gate executes once", sorted(ran), ["a", "b", "c", "d", "e", "f", "g", "k"])
        case("...a and b PASS, d CANNOT RUN, e TIMEOUT, k KILLED",
             [status(out, n) for n in ("gate a", "gate b", "cannot", "slow", "dies")],
             ["PASS", "PASS", "CANNOT RUN", "TIMEOUT", "KILLED"])
        case("...and the run is CANNOT RUN (2), not green, while any gate did not finish", rc, 2)
        case("...a gate that shells out says it is never skipped, and why",
             "never skipped: it runs sh" in [ln for ln in out.splitlines() if "shells out" in ln][0], True)
        case("...out-of-set steps are printed, not hidden", status(out, "node tests"), "OUT OF SET")

        rc, out, ran = run()
        case("UNCHANGED inputs: a, b and the git-reading gate are not re-run", sorted(set(ran) & set("abg")), [])
        case("...their lines say SKIPPED with the last green's digest, never PASS",
             [bool(re.search(rf"^SKIPPED +gate {n}  \(last green [0-9a-f]{{16}}\)$", out, re.M)) for n in "ab"],
             [True, True])
        case("...a TIMEOUT, a KILLED and a CANNOT RUN were never recorded green, so they run again",
             sorted(x for x in ran if x in "dek"), ["d", "e", "k"])
        case("...and the unbounded gate runs again", "c" in ran, True)
        entries = read_ledger(repo / LEDGER_DIR / LEDGER_FILE)[0]
        gate_a = next(g for g in ci_gates(WF_FIXTURE, "master")[0] if g.name == "gate a")
        case("a green answers its own mode, and never another mode of the same script",
             (last_green(entries, gate_a, World(repo)) is not None,
              last_green(entries, gate_a._replace(args=("--other",)), World(repo))), (True, None))
        case("the same green does not answer tomorrow, and an empty ledger answers nothing",
             (last_green(entries, gate_a, World(repo, today="2000-01-01")), last_green([], gate_a, World(repo))),
             (None, None))
        case("a missing ledger is empty, not an error",
             read_ledger(repo / LEDGER_DIR / "no-such-ledger.json"), ([], None))
        inp = Inputs(("data/a.txt",), ())
        case("the date is an input: the same files digest differently tomorrow",
             digest(inp, World(repo, today="2000-01-01")) == digest(inp, World(repo, today="2000-01-02")),
             False)
        case("a variable ENV_DIGESTED names is an input; any other variable is not",
             [digest(inp, World(repo, env=e)) == digest(inp, World(repo, env={}))
              for e in ({"CI": "true"}, {"SOME_OTHER_VAR": "1"})], [False, True])
        case("a different input set digests differently in the same world",
             digest(Inputs(("data/b.txt",), ()), World(repo)) == digest(inp, World(repo)), False)
        (repo / WORKFLOW).write_text(WF_FIXTURE.replace(WF_SLOW, ""))   # the timeout is proven; stop paying for it
        rc, out, ran = run()
        case("an uncommitted edit to a file NO gate opened re-runs only the git-reading gate (it reads the tree)",
             sorted(set(ran) & set("abg")), ["g"])

        git("update-ref", "refs/heads/unrelated", "HEAD")
        rc, out, ran = run()
        case("a ref the git-reading gate does not name moves: it is still skipped", "g" in ran, False)

        (repo / "data" / "a.txt").write_text("a2")
        git("commit", "-qam", "touch a's input")
        rc, out, ran = run()
        case("a commit that touches ONE gate's input re-runs that gate", "a" in ran, True)
        case("...and does not re-run the gate whose inputs did not move", "b" in ran, False)
        case("...but HEAD moved, and the git-reading gate reads the tree, so it re-runs", "g" in ran, True)

        git("update-ref", "refs/remotes/origin/master", "HEAD")
        rc, out, ran = run()
        case("the ref the git-reading gate NAMES moves: it re-runs, and nothing else does",
             sorted(set(ran) & set("abg")), ["g"])

        (repo / "scripts" / "b.py").write_text(GATE_SCRIPTS["b.py"].format(log=str(runs)) + "# moved\n")
        rc, out, ran = run()
        case("editing a gate's own script re-runs it (uncommitted counts)", ("a" in ran, "b" in ran), (False, True))

        (repo / "data" / "flag").write_text("")
        rc, out, ran = run()
        case("a file a gate only stat()s appearing re-runs gates (the tree's name list is an input)",
             ("a" in ran, "b" in ran), (True, True))

        rc, out, ran = run("--no-skip")
        case("--no-skip runs every gate", sorted(ran), ["a", "b", "c", "d", "f", "g", "k"])

        ledger = repo / LEDGER_DIR / LEDGER_FILE
        ledger.write_text("{not json")
        rc, out, ran = run()
        case("an unreadable ledger skips nothing and says so", ("a" in ran, "ledger" in out and "unreadable" in out),
             (True, True))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--timeout", "1.5"], root=empty)
        case("a root with no workflow is CANNOT RUN, and nothing runs", (rc, buf.getvalue().startswith("CANNOT RUN")),
             (2, True))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


if __name__ == "__main__":
    sys.exit(main())

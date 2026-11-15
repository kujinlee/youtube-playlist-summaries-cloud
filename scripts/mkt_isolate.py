#!/usr/bin/env python3
"""Build a stranger's world — fresh HOME, allow-listed PATH, an audit-hook capture — and run one command in it
(marketplace-inventory plan, Task 2; spec §6 and §7 item 0b).

    python3 scripts/mkt_isolate.py --self-test  # 73 cases
    python3 scripts/mkt_isolate.py --root DIR --allow CMD,... [--cwd DIR] [--timeout S] [--port N] -- ARGV...

build_world(root, allow) makes the world under an EMPTY root: home/, tmp/, bin/ (one symlink per allow-listed
command, nothing else), hook/sitecustomize.py. Its env is built from nothing (ENV_KEYS). preflight(world, port)
returns every reason the author's environment would leak in (root or a HOME entry inside the repository, an env key
or PATH beyond the world's, a bindir entry off the allow-list or resolving into the repo, the explainer port already
listening; what `measured` reads from the world's own Python and git); empty means clear. "Inside the repository"
is compared FOLDED (`fold`), so a case alias of the checkout is inside it. run_isolated(world, argv, cwd, timeout) runs one command and returns a RunRecord:
rc, stdout, stderr, the files Python processes OPENED (audit hook), the programs EXECUTED, and what is UNOBSERVABLE —
every non-Python program, every Python process that never loaded the hook, and the ALWAYS entries. It refuses a
world that fails `boundary` or `measured`, whoever called `preflight`.
Anything this cannot do is CANNOT RUN (rc 2), never an empty record.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import functools
import importlib.util
import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# The world's whole environment: built from nothing, so a key outside this set is a leak (preflight refuses it).
ENV_KEYS = frozenset({"HOME", "TMPDIR", "PATH", "LANG", "PYTHONPATH", "GIT_CONFIG_NOSYSTEM"})
# The world's directories, by field and name under the root. `boundary` refuses a World whose fields differ.
LAYOUT = (("home", "home"), ("bindir", "bin"), ("tmpdir", "tmp"), ("hookdir", "hook"))
# r1 Codex 2: a `pyvenv.cfg` at the world root makes a Python started as `<root>/bin/python3` a virtual environment
# with NO system site-packages — the caller's installed packages and their `.pth` files are not on `sys.path`. It
# acts only on an interpreter that finds it (one that re-execs another, like macOS's `/usr/bin/python3` shim, does
# not), so `preflight` VERIFIES the effect in each allowed Python rather than trusting the file.
VENV_CFG = "pyvenv.cfg"
VENV_TEXT = "include-system-site-packages = false\n"
# r1 Codex 3: git config keys that carry the author's credentials or rewrite where git fetches. A world's git that
# reports any of them is refused by `preflight`; the system file is switched off by GIT_CONFIG_NOSYSTEM in the env.
GIT_LEAK_KEYS = r"^(credential\..*|url\..*\.(insteadof|pushinsteadof))$"
# A program name the capture counts as a Python interpreter — the only kind the audit hook runs inside.
PYTHON_NAME = re.compile(r"^python[\d.]*$")
# What the capture cannot see, in EVERY record (spec §6: "state what it cannot see"). Prefixed so a case can tell
# these apart from the per-program entries, which name the program.
ALWAYS = (
    "ALWAYS: file access by non-Python processes (git, node, gh, cat, ...) — the hook runs only inside Python",
    "ALWAYS: network access — nothing here captures sockets",
    "ALWAYS: anything before a Python interpreter imports sitecustomize (startup, the stdlib imported before it)",
    "ALWAYS: the OS user's keychain — the world runs as the author's OS user, so a program that asks the keychain "
    "directly is answered as the author (isolation-baseline.md, bound (e))",
)
AUDIT_LOG = "audit.jsonl"
# r1 Claude M1: the one key a run adds to the world's env — a fresh token per `run_isolated` call, inherited by every
# process the run starts and stamped on each event, so a record holds its own processes' events and no survivor's.
RUN_KEY = "MKT_ISOLATE_RUN"

# The audit hook, written into the world's PYTHONPATH as `sitecustomize.py`. It SHADOWS any sitecustomize the
# interpreter ships (isolation-baseline.md names the one shadowed). One JSON line per event, appended to the log
# beside it through ONE descriptor opened before the hook is installed (so the log's own open is not an event).
# A failed write RAISES inside the audited operation: a lost event is never a silent gap.
SITECUSTOMIZE = r"""# mkt_isolate.py's audit hook (marketplace-inventory plan Task 2). Generated; do not edit.
import json as _json
import os as _os
import sys as _sys

_FD = _os.open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "audit.jsonl"),
               _os.O_WRONLY | _os.O_APPEND | _os.O_CREAT, 0o600)


def _s(x):
    return _os.fsdecode(x) if isinstance(x, (str, bytes, _os.PathLike)) else str(x)


def _argv(a):
    return [_s(a)] if isinstance(a, (str, bytes, _os.PathLike)) else [_s(x) for x in (a or [])]


def _hook(event, args):
    if event == "open":
        if isinstance(args[0], (str, bytes, _os.PathLike)):
            _put({"ev": "open", "path": _os.path.abspath(_os.fsdecode(args[0]))})
    elif event == "subprocess.Popen":
        argv = _argv(args[1])
        _put({"ev": "exec", "via": event, "prog": _s(args[0]) if args[0] is not None else argv[0], "argv": argv})
    elif event in ("os.exec", "os.posix_spawn"):
        _put({"ev": "exec", "via": event, "prog": _s(args[0]), "argv": _argv(args[1])})
    elif event == "os.spawn":
        _put({"ev": "exec", "via": event, "prog": _s(args[1]), "argv": _argv(args[2])})
    elif event == "os.system":
        _put({"ev": "exec", "via": event, "prog": "/bin/sh", "argv": ["/bin/sh", "-c", _s(args[0])]})


_RUN = _os.environ.get("MKT_ISOLATE_RUN")


def _put(rec):
    rec["pid"] = _os.getpid()
    rec["run"] = _RUN
    _os.write(_FD, (_json.dumps(rec, default=str) + "\n").encode())


_put({"ev": "start", "exe": _sys.executable})
_sys.addaudithook(_hook)
"""


class CannotRun(Exception):
    """The run cannot reach its subject. Said loudly as `CANNOT RUN: <why>`, rc 2 — never an empty record."""


@dataclasses.dataclass(frozen=True)
class World:
    root: Path
    home: Path
    bindir: Path
    tmpdir: Path
    hookdir: Path
    allow: tuple[str, ...]
    env: dict[str, str]


@dataclasses.dataclass
class RunRecord:
    rc: int
    stdout: str
    stderr: str
    opened: list[str]
    executed: list[str]
    unobservable: list[str]


def fold(text: str) -> str:
    """`text` as a case-insensitive, normalisation-insensitive filesystem (macOS's default) compares names. An
    EXCLUSION compares folded, so a case alias of a refused place is refused (r2 Codex 1); an inclusion compares
    exact."""
    return unicodedata.normalize("NFKC", text).casefold()


def _reaches(path: Path, top: Path) -> bool:
    """`path`, every link followed, is `top` or below it under ANY case alias: `resolve()` keeps the spelling it is
    given, so `/Repo/x` does not compare below `/repo` although it is the same directory there. For exclusions."""
    a, b = fold(str(Path(path).resolve())), fold(str(Path(top).resolve()))
    return a == b or a.startswith(b.rstrip("/") + "/")


def _inside(path: Path, top: Path) -> bool:
    """`path`, every link followed, is `top` or below it (also resolved)."""
    try:
        Path(path).resolve().relative_to(Path(top).resolve())
    except ValueError:
        return False
    return True


def build_world(root: Path, allow: list[str]) -> World:
    """A fresh world under `root` (absent or empty): `home/`, `tmp/`, `bin/` (one symlink per allow-listed command,
    to its absolute path on the CALLER's PATH) and `hook/sitecustomize.py`. The env is built from nothing."""
    root = Path(root).absolute()
    for c in allow:
        if not c or "/" in c or c in (".", ".."):
            raise CannotRun(f"allow-list entry {c!r} is not a command name (a name is looked up; a path is not)")
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise CannotRun(f"world root {root} is not an empty directory: a world is built fresh, never reused")
    found = {}
    for c in allow:
        p = shutil.which(c)
        if p is None:
            raise CannotRun(f"allow-listed command {c!r} is not on the caller's PATH")
        found[c] = os.path.abspath(p)
    home, bindir, tmpdir, hookdir = (root / n for n in ("home", "bin", "tmp", "hook"))
    for d in (home, bindir, tmpdir, hookdir):
        d.mkdir(parents=True, exist_ok=True)
    for c, p in found.items():
        (bindir / c).symlink_to(p)
    (hookdir / "sitecustomize.py").write_text(SITECUSTOMIZE)
    (root / VENV_CFG).write_text(VENV_TEXT)
    return World(root, home, bindir, tmpdir, hookdir, tuple(allow), world_env(root))


def world_env(root: Path) -> dict[str, str]:
    """The whole environment of the world under `root`: built from nothing, every value the world's own."""
    root = Path(root)
    return {"HOME": str(root / "home"), "TMPDIR": str(root / "tmp"), "PATH": str(root / "bin"), "LANG": "C.UTF-8",
            "PYTHONPATH": str(root / "hook"), "GIT_CONFIG_NOSYSTEM": "1"}


def _checkouts(repo: Path = REPO) -> list[Path]:
    """The checkouts a world must not reach: `repo` and, when `repo` is a linked worktree, its MAIN checkout (r1
    Claude M2). Read from the `.git` file and `commondir`, never by running git (whose env a caller may redirect)."""
    repo = Path(repo).resolve()
    tops, dotgit = [repo], repo / ".git"
    if dotgit.is_file():
        m = re.match(r"gitdir:\s*(.+)", dotgit.read_text().strip())
        if m:
            gitdir = (repo / m.group(1).strip()).resolve()
            common = gitdir
            if (gitdir / "commondir").is_file():
                common = (gitdir / (gitdir / "commondir").read_text().strip()).resolve()
            if common.parent not in tops:
                tops.append(common.parent)
    return tops


def boundary(world: World) -> list[str]:
    """PURE of subprocesses: every way the World's own fields and env differ from the world under its root. Run by
    `preflight` AND by `run_isolated` (r1 Codex 4: a check only a caller runs is a check a caller can skip)."""
    reasons = []
    for top in _checkouts():
        if _reaches(world.root, top):
            reasons.append(f"world root {world.root} lies inside the repository {top}")
    for field, name in LAYOUT:
        if Path(getattr(world, field)) != Path(world.root) / name:
            reasons.append(f"world {field} {getattr(world, field)} is outside its place {Path(world.root) / name}")
    want = world_env(world.root)
    extra = sorted(set(world.env) - ENV_KEYS)
    if extra:
        reasons.append(f"world env holds key(s) outside the declared set: {', '.join(extra)}")
    for key in sorted(ENV_KEYS):
        if world.env.get(key) != want[key]:
            reasons.append(f"world env {key}={world.env.get(key)!r} is not the world's own ({want[key]!r})")
    return reasons


@functools.lru_cache(maxsize=1)
def _explainer_serve():
    path = REPO / "scripts" / "explainer-serve.py"
    try:
        spec = importlib.util.spec_from_file_location("mkt_isolate_explainer_serve", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except (OSError, ImportError, AttributeError) as e:
        raise CannotRun(f"cannot read the explainer port from {path}: {type(e).__name__}: {e}") from e
    return mod


def explainer_port(env: dict[str, str]) -> int:
    """The port `explainer-serve.py` would serve on in an environment `env` — its OWN `port_from`, never a typed
    number. A value it calls an error is CANNOT RUN (the server would refuse it too)."""
    port, err = _explainer_serve().port_from(env.get("EXPLAINER_SERVE_PORT", ""))
    if err:
        raise CannotRun(f"EXPLAINER_SERVE_PORT in the world: {err}")
    return port


def preflight(world: World, port: int | None = None) -> list[str]:
    """Every reason the world leaks the author's, empty = clear (Review Focus 3). `port` defaults to the explainer
    server's port in the world's env; the self-test passes an ephemeral one."""
    reasons = boundary(world)       # the env, key by key and value by value, PATH included
    if world.home.is_dir():
        for entry in sorted(world.home.iterdir()):
            if any(_reaches(entry, top) for top in _checkouts()):
                reasons.append(f"HOME/{entry.name} resolves inside the repository ({entry.resolve()})")
    else:
        reasons.append(f"world HOME {world.home} is not a directory")
    if world.bindir.is_dir():
        for entry in sorted(world.bindir.iterdir()):
            if entry.name not in world.allow:
                reasons.append(f"bindir entry {entry.name} is not on the allow-list {list(world.allow)}")
            if any(_reaches(entry, top) for top in _checkouts()):
                reasons.append(f"allow-listed command {entry.name} resolves inside the repository "
                               f"({entry.resolve()})")
    else:
        reasons.append(f"world bindir {world.bindir} is not a directory")
    reasons += measured(world)
    port = explainer_port(world.env) if port is None else port
    with socket.socket() as s:
        s.settimeout(1.0)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            reasons.append(f"port {port} is already listening: a server the stranger did not start would answer")
    return reasons


def measured(world: World) -> list[str]:
    """What only the world's OWN commands can tell (r1 Codex 2 and 3): each allow-listed Python's `sys.path` and
    installed distributions, and git's credential and URL-rewrite config. Run by `preflight` AND by `run_isolated`
    (r2 Codex 4), so the package set is verified at every run, whoever calls. Costs one process per such command."""
    reasons = []
    for name in world.allow:
        if not (world.bindir / name).exists():
            continue
        if _is_python(name):
            reasons += _python_leaks(world, name)
        elif name == "git":
            reasons += _git_leaks(world)
    return reasons


def _is_python(prog: str) -> bool:
    return bool(PYTHON_NAME.match(Path(prog).name))


_PY_PROBE = ("import sys, json, importlib.metadata as md; "
             "print(json.dumps([sys.path, sys.base_prefix, sorted(d.metadata['Name'] for d in md.distributions())]))")


def _python_leaks(world: World, name: str) -> list[str]:
    """r1 Codex 2, MEASURED in the world's own interpreter: a `sys.path` entry that is not the cwd, inside the world,
    or the interpreter's stdlib (inside `sys.base_prefix` with no `site-packages`/`dist-packages` component), and
    every installed distribution. A probe that cannot run is a refusal, never a pass."""
    try:
        p = subprocess.run([name, "-c", _PY_PROBE], executable=str(world.bindir / name), env=world.env,
                           cwd=world.root, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        paths, base, dists = json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        return [f"{name}: cannot verify the world's sys.path ({type(e).__name__}: {e})"]
    leaks = foreign_paths(paths, base, world.root)
    reasons = []
    if leaks:
        reasons.append(f"{name}: sys.path reaches outside the world and the stdlib (site-packages or a .pth "
                       f"entry): {', '.join(leaks)}")
    if dists:
        reasons.append(f"{name}: installed distributions are importable in the world: {', '.join(dists)}")
    return reasons


def foreign_paths(paths: list[str], base: str, root: Path) -> list[str]:
    """PURE but for resolving links. The `sys.path` entries a world's Python must not have: all but the cwd (""),
    entries inside the world, and the stdlib — inside `base` (sys.base_prefix) with no `site-packages` or
    `dist-packages` component, since a Linux python keeps those INSIDE its prefix (/usr/lib/python3/dist-packages)."""
    return [x for x in paths if x and not _inside(Path(x), root)
            and not (_inside(Path(x), Path(base)) and not {"site-packages", "dist-packages"} & set(Path(x).parts))]


def _git_leaks(world: World) -> list[str]:
    """r1 Codex 3, MEASURED with the world's own git and env: any credential or URL-rewrite key it would use."""
    try:
        p = subprocess.run(["git", "config", "--show-origin", "--get-regexp", GIT_LEAK_KEYS],
                           executable=str(world.bindir / "git"), env=world.env, cwd=world.root,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"git: cannot read the world's git config ({type(e).__name__}: {e})"]
    if p.returncode == 1 and not p.stdout.strip():
        return []
    if p.returncode != 0:
        return [f"git: cannot read the world's git config (rc {p.returncode}: {p.stderr.strip()})"]
    return [f"git: the world's git has author-supplied config: {line}" for line in p.stdout.strip().splitlines()]


def read_audit(text: str, top: str, run: str | None = None, alive=None) -> tuple[list[str], list[str], list[str]]:
    """PURE. (opened, executed, unobservable) from one run's audit log and the program the run started (`top`).

    `executed` is `top` then every launch the hook saw; a `posix_spawn` repeating the `Popen` just before it in the
    same pid is the same launch (subprocess may spawn through it). Every non-Python program executed is named as
    unobservable, and so is every Python process that never wrote a `start` event (started `-I`/`-E`/`-S`, or
    its sitecustomize shadowed): its opens are NOT CAPTURED, never zero. A line that does not parse is CANNOT RUN.

    r1 Claude M1: every event carries the run token its process inherited (`MKT_ISOLATE_RUN`), so an event whose
    token is not `run` belongs to a process ANOTHER record started and that outlived it: it is not attributed here,
    and an `earlier:` entry says so. `alive(pid)`, when given, is asked of every pid that started under `run`; a live
    one OUTLIVED the record and is named by pid."""
    events = []
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            ev = json.loads(raw)
        except ValueError:
            raise CannotRun(f"audit log line {n} does not parse: {raw[:80]!r}") from None
        if not isinstance(ev, dict) or ev.get("ev") not in ("start", "open", "exec"):
            raise CannotRun(f"audit log line {n} is not an event: {raw[:80]!r}")
        events.append(ev)
    foreign = [ev for ev in events if ev.get("run") != run]
    events = [ev for ev in events if ev.get("run") == run]
    started = [ev["pid"] for ev in events if ev["ev"] == "start"]
    opened, seen, executed, last, starts = [], set(), [top], {}, 0
    for ev in events:
        if ev["ev"] == "start":
            starts += 1
        elif ev["ev"] == "open":
            if ev["path"] not in seen:
                seen.add(ev["path"])
                opened.append(ev["path"])
        else:
            prev = last.get(ev["pid"])
            if (ev["via"] == "os.posix_spawn" and prev is not None and prev["via"] == "subprocess.Popen"
                    and prev["argv"] == ev["argv"]):
                last[ev["pid"]] = None
                continue
            executed.append(ev["prog"])
            last[ev["pid"]] = ev
    unobservable = list(ALWAYS)
    for prog in executed:
        if not _is_python(prog):
            unobservable.append(f"{Path(prog).name}: a non-Python process ({prog}); its file access is NOT CAPTURED")
    missing = sum(_is_python(p) for p in executed) - starts
    if missing > 0:
        unobservable.append(f"python: {missing} Python process(es) ran without the audit hook (-I, -E, -S or a "
                            f"shadowed sitecustomize), or had not loaded it when the record was read (a process "
                            f"that outlived the record); their file access is NOT CAPTURED here")
    if foreign:
        pids = ", ".join(str(p) for p in sorted({ev["pid"] for ev in foreign}))
        unobservable.append(f"earlier: {len(foreign)} event(s) from pid(s) {pids}, which another record started, "
                            f"are NOT attributed to this one (they stay in the world's audit log)")
    for pid in started:
        if alive is not None and alive(pid):
            unobservable.append(f"outlived the record: pid {pid} was still running when the record was read; what it "
                                f"does later is NOT in this record (it stays in the world's audit log)")
    return opened, executed, unobservable


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_isolated(world: World, argv: list[str], cwd: Path, timeout: int) -> RunRecord:
    """Run `argv` in the world: its env only, `argv[0]` looked up on the world's PATH (or an executable path inside
    the world root), in `cwd`, which must lie inside the world root (r1 Claude M2). The world must pass `boundary`
    and `measured` here, whoever called `preflight` (r1 Codex 4, r2 Codex 4). NOT checked here: the HOME and bindir
    entries and the explainer port, which are `preflight`'s alone.
    The audit log is APPENDED to and never emptied (r1 Claude M1): a record reads the bytes written from its start to its top process's exit, so events a surviving process writes
    later stay in the log, a later record does not claim them, and each record names a survivor by pid. A command the
    world cannot reach, an OS error starting it, or a timeout is CANNOT RUN. Bound: a grandchild that outlives a
    timeout is not killed."""
    if not argv:
        raise CannotRun("nothing to run: argv is empty")
    bad = boundary(world)
    if not bad:                     # the measured checks start the world's commands: only in a world that holds
        bad = measured(world)
    if bad:
        raise CannotRun("the world's boundary does not hold: " + "; ".join(bad))
    if not _inside(Path(cwd), world.root):
        raise CannotRun(f"cwd {cwd} does not resolve inside the world root {world.root}: a stranger has no "
                        f"directory of the author's to run in")
    prog = argv[0]
    if "/" in prog:
        top = prog
        if not (Path(prog).is_absolute() and _inside(Path(prog), world.root) and os.access(prog, os.X_OK)):
            raise CannotRun(f"{prog}: a path must be an executable inside the world root {world.root}")
    else:
        top = shutil.which(prog, path=world.env["PATH"])
        if top is None:
            raise CannotRun(f"{prog}: not on the world's PATH (allow-list: {', '.join(world.allow)})")
    log = world.hookdir / AUDIT_LOG
    with open(log, "ab") as fh:
        start = fh.tell()
    token = secrets.token_hex(8)
    try:
        p = subprocess.run(argv, executable=top, cwd=cwd, env={**world.env, RUN_KEY: token}, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CannotRun(f"timed out after {timeout} s: {argv!r}") from None
    except OSError as e:
        raise CannotRun(f"{prog}: {type(e).__name__}: {e}") from None
    with open(log, "rb") as fh:
        fh.seek(start)
        text = fh.read().decode("utf-8", errors="replace")
    # A survivor may be mid-write: only whole lines are this record's (a partial last line is the next one's).
    text = text[:text.rfind("\n") + 1]
    opened, executed, unobservable = read_audit(text, top, run=token, alive=_alive)
    return RunRecord(p.returncode, p.stdout, p.stderr, opened, executed, unobservable)


USAGE = ("usage: mkt_isolate.py --root DIR --allow CMD,... [--cwd DIR] [--timeout S] [--port N] -- ARGV...\n"
         "       mkt_isolate.py --self-test")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    if "--" not in argv:
        print(USAGE, file=sys.stderr)
        return 2
    cut = argv.index("--")
    ap = argparse.ArgumentParser(prog="mkt_isolate.py", usage=USAGE)
    ap.add_argument("--root", required=True)
    ap.add_argument("--allow", required=True)
    ap.add_argument("--cwd")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--port", type=int)
    opts = ap.parse_args(argv[:cut])
    try:
        world = build_world(Path(opts.root), [c for c in opts.allow.split(",") if c])
        reasons = preflight(world, opts.port)
        if reasons:
            print("CANNOT RUN: preflight refused: " + "; ".join(reasons), file=sys.stderr)
            return 2
        cwd = Path(opts.cwd) if opts.cwd else world.root / "work"
        cwd.mkdir(parents=True, exist_ok=True)
        rec = run_isolated(world, argv[cut + 1:], cwd, opts.timeout)
    except CannotRun as e:
        print(f"CANNOT RUN: {e}", file=sys.stderr)
        return 2
    print(json.dumps(dataclasses.asdict(rec), indent=2))
    return 0


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

    def raises(fn):
        """The CannotRun message `fn` raised, or what it returned instead (a red case either way)."""
        try:
            got = fn()
        except CannotRun as e:
            return f"CANNOT RUN: {e}"
        return f"RETURNED {got!r}"

    def fresh(allow=("python3",)):
        return build_world(Path(tempfile.mkdtemp(prefix="mkt-world-")), list(allow))

    def free_port():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        return p

    def fixture(text="fixture\n"):
        d = Path(tempfile.mkdtemp(prefix="mkt-fx-"))
        f = d / "fixture.txt"
        f.write_text(text)
        return str(f)

    def run(w, argv, timeout=60):
        return run_isolated(w, argv, w.home, timeout)

    def specific(rec, word):
        """The unobservable entries naming one program — the static four never name one."""
        return [u for u in rec.unobservable if u.startswith(word + ":")]

    STATIC = 4

    # --- build_world -------------------------------------------------------------------------------
    case("world env has no key outside the declared set",
         lambda: sorted(set(fresh().env) - ENV_KEYS), [])
    case("world env holds every declared key (an identity: the declared set is what is built)",
         lambda: sorted(fresh().env), sorted(ENV_KEYS))
    case("world HOME and TMPDIR lie inside the root, for two different roots",
         lambda: [(Path(w.env["HOME"]).parent == w.root, Path(w.env["TMPDIR"]).parent == w.root)
                  for w in (fresh(), fresh(("git",)))], [(True, True), (True, True)])
    case("world PATH is exactly its bindir",
         lambda: (lambda w: w.env["PATH"] == str(w.bindir))(fresh()), True)
    case("bindir holds exactly the allow-list, for two allow-lists",
         lambda: [sorted(os.listdir(fresh(a).bindir)) for a in (("python3", "git"), ("cat",))],
         [["git", "python3"], ["cat"]])
    case("PATH holds only allow-listed commands (command -v ls fails, git is found)",
         lambda: (lambda w: [subprocess.run(["/bin/sh", "-c", f"command -v {c}"], env=w.env,
                                            capture_output=True).returncode == 0 for c in ("ls", "git")])(
             fresh(("git",))), [False, True])
    case("an allow-listed command that cannot be found is CANNOT RUN",
         lambda: raises(lambda: fresh(("no-such-cmd-mkt",))).startswith("CANNOT RUN: allow-listed command"), True)
    case("an allow entry that is a path, not a name, is CANNOT RUN",
         lambda: raises(lambda: fresh(("/bin/cat",))).startswith("CANNOT RUN: allow-list entry"), True)
    case("a non-empty root is CANNOT RUN (a world is never reused)",
         lambda: (lambda d: (Path(d, "x").write_text("x"),
                             raises(lambda: build_world(Path(d), ["cat"])).startswith("CANNOT RUN: world root"))[1])(
             tempfile.mkdtemp(prefix="mkt-world-")), True)

    # --- explainer_port ----------------------------------------------------------------------------
    def es_default():
        import importlib.util
        spec = importlib.util.spec_from_file_location("mkt_es_probe", REPO / "scripts" / "explainer-serve.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.port_from("")[0]
    case("explainer_port is explainer-serve's own default when the world sets no port",
         lambda: explainer_port({}) == es_default(), True)
    case("explainer_port follows EXPLAINER_SERVE_PORT in the world's env, as the server does",
         lambda: explainer_port({"EXPLAINER_SERVE_PORT": "7419"}), 7419)

    case("fold: two spellings one case-insensitive filesystem holds as ONE name fold to one string — by case "
         "and by Unicode form — and a different name does not",
         lambda: [fold(".CLAUDE/Plans") == fold(".claude/plans"), fold("caf\u00e9") == fold("CAFE\u0301"),
                  fold("\uff41b") == fold("AB"), fold(".claude/plans") == fold(".claude/plan")],
         [True, True, True, False])

    # --- preflight ---------------------------------------------------------------------------------
    case("a fresh world on a free port is clear",
         lambda: preflight(fresh(), port=free_port()), [])
    case("a fresh world with two allowed commands on a free port is clear",
         lambda: preflight(fresh(("git", "cat")), port=free_port()), [])

    def explainers_into(target):
        w = fresh()
        (w.home / "explainers").symlink_to(target)
        return [r for r in preflight(w, port=free_port())]
    case("preflight refuses a HOME whose explainers dir resolves into the repo",
         lambda: [("explainers" in r and "inside the repository" in r) for r in
                  explainers_into(REPO / "docs" / "explainers")], [True])
    case("adjacent: an explainers dir that resolves outside the repo is clear",
         lambda: explainers_into(tempfile.mkdtemp(prefix="mkt-ex-")), [])
    case("preflight refuses a HOME whose .claude resolves into the repo",
         lambda: (lambda w: ((w.home / ".claude").symlink_to(REPO / ".claude"),
                             [(".claude" in r) for r in preflight(w, port=free_port())])[1])(fresh()), [True])

    def listening():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        p = s.getsockname()[1]
        try:
            return [str(p) in r and "listening" in r for r in preflight(fresh(), port=p)]
        finally:
            s.close()
    case("preflight refuses when the explainer port is already listening",
         listening, [True])

    def repo_command():
        exe = next(p.name for p in sorted((REPO / "scripts").iterdir())
                   if p.is_file() and os.access(p, os.X_OK) and p.suffix in (".sh", ".py"))
        old = os.environ["PATH"]
        os.environ["PATH"] = f"{REPO / 'scripts'}{os.pathsep}{old}"
        try:
            w = fresh(("cat", exe))
        finally:
            os.environ["PATH"] = old
        return [(exe in r and "inside the repository" in r) for r in preflight(w, port=free_port())]
    case("preflight refuses an allow-listed command that resolves inside the repository",
         repo_command, [True])

    def tampered(**change):
        w = fresh(("cat",))
        return preflight(dataclasses.replace(w, **change), port=free_port())
    def env_key():
        w = fresh(("cat",))
        return [("GH_TOKEN" in r) for r in preflight(dataclasses.replace(w, env={**w.env, "GH_TOKEN": "x"}),
                                                     port=free_port())]
    case("preflight refuses an env key outside the declared set", env_key, [True])
    case("preflight refuses a world root inside the repository",
         lambda: any("world root" in r and "inside the repository" in r
                     for r in tampered(root=REPO / "mkt-never-created")), True)

    # r2 fold: `resolve()` keeps the spelling it is given, so a CASE ALIAS of the checkout compared exact is "outside".
    # The WHOLE path's case is swapped: a linked worktree's alias would otherwise still sit, exactly spelled, inside
    # its main checkout. Nothing is created there (on a case-sensitive filesystem the path does not exist).
    ALIAS = Path(str(REPO).swapcase())
    case("preflight refuses a world root inside a CASE ALIAS of the repository",
         lambda: any("world root" in r and "inside the repository" in r
                     for r in tampered(root=ALIAS / "mkt-never-created")), True)
    case("preflight refuses a HOME entry that resolves into a case alias of the repo",
         lambda: [("explainers" in r and "inside the repository" in r) for r in
                  explainers_into(ALIAS / "docs" / "explainers")], [True])

    def alias_command():
        w = fresh(("cat",))
        (w.bindir / "cat").unlink()
        (w.bindir / "cat").symlink_to(ALIAS / "scripts" / "mkt_isolate.py")
        return [("cat" in r and "inside the repository" in r) for r in preflight(w, port=free_port())]
    case("preflight refuses an allow-listed command that resolves into a case alias of the repository",
         alias_command, [True])

    case("preflight refuses a world whose PATH is not exactly its bindir",
         lambda: (lambda w: [("PATH" in r) for r in preflight(
             dataclasses.replace(w, env={**w.env, "PATH": f"{w.bindir}{os.pathsep}/usr/bin"}), port=free_port())])(
             fresh(("cat",))), [True])
    case("preflight refuses a world whose HOME or bindir is not a directory",
         lambda: [len([r for r in tampered(**{k: Path(tempfile.mkdtemp(prefix="mkt-gone-")) / "gone"})
                       if "not a directory" in r]) for k in ("home", "bindir")], [1, 1])

    def extra_bin():
        w = fresh(("cat",))
        (w.bindir / "gh").symlink_to(shutil.which("cat"))
        return [("gh" in r and "allow-list" in r) for r in preflight(w, port=free_port())]
    case("preflight refuses a bindir entry that is not on the allow-list", extra_bin, [True])

    # r1 Codex 4: env VALUES, not only key names. Each isolation-critical key set to a foreign value is refused.
    def foreign_value(key):
        w = fresh(("cat",))
        bad = str(Path(tempfile.mkdtemp(prefix="mkt-foreign-")))
        return any(key in r for r in preflight(dataclasses.replace(w, env={**w.env, key: bad}), port=free_port()))
    case("preflight refuses a foreign VALUE for each isolation key (HOME, TMPDIR, PYTHONPATH, LANG, "
         "GIT_CONFIG_NOSYSTEM)",
         lambda: [foreign_value(k) for k in ("HOME", "TMPDIR", "PYTHONPATH", "LANG", "GIT_CONFIG_NOSYSTEM")],
         [True] * 5)
    case("preflight refuses a world whose home, tmpdir or hookdir lies outside its root",
         lambda: [any(k in r and "outside" in r for r in
                      tampered(**{k: Path(tempfile.mkdtemp(prefix="mkt-elsewhere-"))}))
                  for k in ("home", "tmpdir", "hookdir")], [True, True, True])

    # r1 Codex 2: the world's interpreter must not see the caller's installed packages.
    def py_paths(w):
        out = subprocess.run([str(w.bindir / "python3"), "-c",
                              "import sys, json, importlib.metadata as md; "
                              "print(json.dumps([sys.path, [d.metadata['Name'] for d in md.distributions()]]))"],
                             env=w.env, cwd=w.root, capture_output=True, text=True, timeout=60).stdout
        paths, dists = json.loads(out)
        return ([p for p in paths if {"site-packages", "dist-packages"} & set(Path(p).parts)], dists)
    case("the world's Python has no site-packages on sys.path and no installed distribution",
         lambda: py_paths(fresh()), ([], []))

    def site_back():
        w = fresh()
        (w.root / VENV_CFG).unlink()
        return any("sys.path" in r and "site-packages" in r for r in preflight(w, port=free_port()))
    case("preflight refuses a world whose Python sees site-packages (pyvenv.cfg removed)", site_back, True)
    case("foreign_paths: site-packages and dist-packages INSIDE the prefix are foreign; the stdlib, the world and "
         "the cwd are not", lambda: foreign_paths(
             ["", "/pfx/lib/python3.12", "/pfx/lib/python3.12/site-packages", "/pfx/lib/python3/dist-packages",
              "/w/hook", "/elsewhere"], "/pfx", Path("/w")),
         ["/pfx/lib/python3.12/site-packages", "/pfx/lib/python3/dist-packages", "/elsewhere"])
    case("adjacent: the same entries judged against ANOTHER world and prefix — what is foreign follows root and base",
         lambda: foreign_paths(["", "/pfx/lib/python3.12", "/w/hook", "/q/lib/python3.13", "/q/lib/site-packages"],
                               "/q", Path("/pfx")),
         ["/w/hook", "/q/lib/site-packages"])

    # r1 Codex 3: git config the author's machine supplies (system file, credential helpers, URL rewrites).
    def git_system():
        w, d = fresh(("git",)), Path(tempfile.mkdtemp(prefix="mkt-sysgit-"))
        (d / "gitconfig").write_text("[credential]\n\thelper = planted-system-helper\n")
        p = subprocess.run(["git", "config", "--get", "credential.helper"], executable=str(w.bindir / "git"),
                           env={**w.env, "GIT_CONFIG_SYSTEM": str(d / "gitconfig")}, cwd=w.root,
                           capture_output=True, text=True, timeout=60)
        return (p.returncode, p.stdout)
    case("a git in the world reads no system config (a planted GIT_CONFIG_SYSTEM is ignored)", git_system, (1, ""))

    def git_planted(text):
        w = fresh(("git",))
        (w.home / ".gitconfig").write_text(text)
        return [r for r in preflight(w, port=free_port()) if "git" in r]
    case("preflight refuses a world whose git has a credential helper or a URL rewrite, naming the key",
         lambda: [any(k in r for r in git_planted(t)) for k, t in
                  (("credential.helper", "[credential]\n\thelper = store\n"),
                   ("insteadof", '[url "https://x@example.com/"]\n\tinsteadOf = https://example.com/\n'))],
         [True, True])
    case("adjacent: a world git with only an identity configured is clear",
         lambda: git_planted("[user]\n\tname = stranger\n"), [])

    # r1 Claude M2: a linked worktree's main checkout counts as the repository too.
    def worktree_checkouts():
        d = Path(tempfile.mkdtemp(prefix="mkt-wt-")).resolve()
        main_co, wt = d / "main", d / "wt"
        g = dict(capture_output=True, check=True, timeout=60)
        subprocess.run(["git", "init", "-q", str(main_co)], **g)
        subprocess.run(["git", "-C", str(main_co), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                        "--allow-empty", "-m", "x"], **g)
        subprocess.run(["git", "-C", str(main_co), "worktree", "add", "-q", str(wt)], **g)
        return [_checkouts(main_co), _checkouts(wt)]
    case("_checkouts: a main checkout is itself; a linked worktree is itself AND its main checkout",
         lambda: [[p.name for p in ps] for ps in worktree_checkouts()],
         [["main"], ["wt", "main"]])

    # --- run_isolated ------------------------------------------------------------------------------
    # r2 Codex 4: what preflight MEASURES in the world, run_isolated measures too — a caller cannot skip it.
    def run_unmeasured(kind):
        if kind == "python":
            w = fresh()
            (w.root / VENV_CFG).unlink()
            return raises(lambda: run(w, ["python3", "-c", "print(1)"]))
        w = fresh(("git", "cat"))
        (w.home / ".gitconfig").write_text("[credential]\n\thelper = store\n")
        return raises(lambda: run(w, ["cat", fixture()]))
    case("run_isolated refuses a world whose Python sees site-packages, with no preflight call before it",
         lambda: (lambda got: got.startswith("CANNOT RUN: the world's boundary does not hold: ")
                  and "site-packages" in got or got)(run_unmeasured("python")), True)
    case("run_isolated refuses a world whose git has a credential helper, whatever command is run",
         lambda: (lambda got: got.startswith("CANNOT RUN: the world's boundary does not hold: ")
                  and "credential.helper" in got or got)(run_unmeasured("git")), True)
    def opens(text):
        w, f = fresh(), fixture(text)
        rec = run(w, ["python3", "-c", "import sys; open(sys.argv[1]).read()", f])
        return f in rec.opened
    case("audit hook records an open of a fixture file", lambda: opens("a\n"), True)

    def second_run():
        w, f1, f2 = fresh(), fixture("one\n"), fixture("two\n")
        code = "import sys; open(sys.argv[1]).read()"
        run(w, ["python3", "-c", code, f1])
        rec = run(w, ["python3", "-c", code, f2])
        # ...and reads from its own start: a record that re-read the first run's events would name them "earlier:",
        # a false claim that a process of the first run outlived it.
        return (f1 in rec.opened, f2 in rec.opened, [u for u in rec.unobservable if u.startswith("earlier:")])
    case("a second run does not inherit the first run's opens, nor name them as a survivor's", second_run,
         (False, True, []))

    def non_python():
        w, f = fresh(("cat",)), fixture()
        rec = run(w, ["cat", f])
        return (rec.stdout, len(specific(rec, "cat")), f in rec.opened)
    case("a non-Python child is listed as unobservable, never as zero opens",
         non_python, ("fixture\n", 1, False))

    def grandchild():
        w, f = fresh(("python3", "cat")), fixture()
        rec = run(w, ["python3", "-c", "import subprocess,sys; subprocess.run(['cat', sys.argv[1]])", f])
        return ([Path(e).name for e in rec.executed], len(specific(rec, "cat")))
    case("a non-Python grandchild launched from Python is executed and unobservable",
         grandchild, (["python3", "cat"], 1))

    def no_hook(flag):
        w, f = fresh(), fixture()
        rec = run(w, ["python3", *flag, "-c", "import sys; open(sys.argv[1]).read()", f])
        return (f in rec.opened, any("without the audit hook" in u for u in rec.unobservable))
    case("a Python child started with -I is unobservable (the hook never loaded)", lambda: no_hook(["-I"]),
         (False, True))
    case("adjacent: a plain Python child loads the hook and has no missing-hook entry", lambda: no_hook([]),
         (True, False))

    case("every record carries the four static unobservables, for two commands",
         lambda: [len([u for u in run(fresh(a), argv).unobservable if u.startswith("ALWAYS:")])
                  for a, argv in ((("python3",), ["python3", "-c", "pass"]), (("cat",), ["cat", "/dev/null"]))],
         [STATIC, STATIC])
    case("rc, stdout and stderr are the child's",
         lambda: (lambda r: (r.rc, r.stdout, r.stderr))(
             run(fresh(), ["python3", "-c", "import sys; print('x'); print('e', file=sys.stderr); sys.exit(3)"])),
         (3, "x\n", "e\n"))
    # macOS CoreFoundation sets `__CF_USER_TEXT_ENCODING` INSIDE the child (measured 2026-11-15: absent from the
    # env passed, present in the child's os.environ). Nothing here passes it, so it is dropped before comparing.
    # The one key a run adds is its run token (r1 Claude M1): a 16-hex value, fresh per run, carrying nothing.
    def child_env():
        w = fresh()
        got = [{k: v for k, v in json.loads(run(w, ["python3", "-c",
                "import os,json; print(json.dumps(dict(os.environ)))"]).stdout).items()
                if not k.startswith("__CF_")} for _ in range(2)]
        tokens = [g.pop(RUN_KEY, "") for g in got]
        return (got[0] == w.env, got[1] == w.env, all(re.fullmatch(r"[0-9a-f]{16}", t) for t in tokens),
                tokens[0] != tokens[1])
    case("the child's environment is the world's, key for key, plus a fresh run token (bar macOS's __CF_ keys)",
         child_env, (True, True, True, True))
    def in_cwd():
        w2 = fresh()
        work = w2.root / "elsewhere"
        work.mkdir()
        got = run_isolated(w2, ["python3", "-c", "import os; print(os.getcwd())"], work, 30).stdout.strip()
        return Path(got).resolve() == work.resolve()
    case("the child runs in the cwd it is given, not HOME", in_cwd, True)
    case("an argv[0] not on the world's PATH is CANNOT RUN",
         lambda: raises(lambda: run(fresh(), ["ls"])).startswith("CANNOT RUN: ls"), True)
    case("an explicit path outside the world root is CANNOT RUN (the allow-list is not bypassed by a path)",
         lambda: raises(lambda: run(fresh(), ["/bin/cat", "/dev/null"])).startswith("CANNOT RUN: /bin/cat"), True)

    def inside_world():
        w = fresh()
        tool = w.root / "installed" / "hello.sh"
        tool.parent.mkdir()
        tool.write_text("#!/bin/sh\necho hello from the world\n")
        tool.chmod(0o755)
        rec = run(w, [str(tool)])
        return (rec.rc, rec.stdout, len(specific(rec, "hello.sh")))
    case("adjacent: an executable path inside the world root runs, and is named unobservable",
         inside_world, (0, "hello from the world\n", 1))
    case("a run past its timeout is CANNOT RUN",
         lambda: raises(lambda: run(fresh(), ["python3", "-c", "import time; time.sleep(30)"], timeout=1)
                        ).startswith("CANNOT RUN: timed out"), True)

    # r1 Codex 4: the boundary is enforced where the command runs, not only by a preflight a caller may skip.
    case("run_isolated refuses a world whose HOME value is not its own, and starts nothing",
         lambda: (lambda w: raises(lambda: run(dataclasses.replace(
             w, env={**w.env, "HOME": tempfile.mkdtemp(prefix="mkt-foreign-")}), ["python3", "-c", "pass"])
                                   ).startswith("CANNOT RUN: the world's boundary"))(fresh()), True)

    # r1 Claude M2: a cwd is part of what the stranger has. One outside the world (the repository here) leaks.
    case("run_isolated refuses a cwd outside the world root, for the repository and a foreign directory",
         lambda: [raises(lambda: run_isolated(fresh(), ["python3", "-c", "pass"], c, 30)).startswith(
             "CANNOT RUN: cwd ") for c in (REPO / "scripts", Path(tempfile.mkdtemp(prefix="mkt-cwd-")))],
         [True, True])

    def cwd_link():
        w = fresh()
        (w.root / "into-repo").symlink_to(REPO / "scripts")
        return raises(lambda: run_isolated(w, ["python3", "-c", "pass"], w.root / "into-repo", 30)).startswith(
            "CANNOT RUN: cwd ")
    case("...and a cwd inside the world that LINKS outside it", cwd_link, True)

    # r1 Claude M1: a process that outlives the record (a detached server) — named, and its events never lost.
    DETACH = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', "
              "'import os, sys, time\\nfor _ in range(200):\\n    time.sleep(0.05)\\n    "
              "if os.path.exists(sys.argv[1]): break\\nopen(sys.argv[2]).read()\\nopen(sys.argv[3], \"w\").close()', "
              "sys.argv[1], sys.argv[2], sys.argv[3]], start_new_session=True, stdin=subprocess.DEVNULL, "
              "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)")

    def outlived():
        import time
        w, f = fresh(), fixture("late\n")
        go, done = w.tmpdir / "go", w.tmpdir / "done"
        first = run(w, ["python3", "-c", DETACH, str(go), f, str(done)])
        # The survivor is named whether or not it had loaded the hook when the record was read: by pid if it had
        # ("outlived the record"), as an executed Python with no hook if not ("python:"). Exactly one, either way.
        named = [u for u in first.unobservable if "outlived the record" in u or u.startswith("python:")]
        second = run(w, ["python3", "-c", "import sys; open(sys.argv[1], 'w').close()", str(go)])
        for _ in range(200):
            if done.exists():
                break
            time.sleep(0.05)
        third = run(w, ["python3", "-c", "pass"])
        log = (w.hookdir / AUDIT_LOG).read_text()
        return (len(named), done.exists(), f in second.opened or f in third.opened, f in log)
    case("a detached process that outlives its record is named, its late open is in the world's log, and no "
         "later record claims it", outlived, (1, True, False, True))

    case("adjacent: a run whose processes all exit names nothing as outliving the record",
         lambda: [u for u in run(fresh(), ["python3", "-c", "pass"]).unobservable if "outlived" in u], [])

    # --- read_audit (pure) ---------------------------------------------------------------------------
    def line(**kv):
        return json.dumps(kv)
    PY = "/usr/bin/python3"
    case("read_audit: a posix_spawn echoing the Popen before it is ONE execution",
         lambda: read_audit("\n".join([
             line(ev="start", pid=1),
             line(ev="exec", pid=1, via="subprocess.Popen", prog="/bin/cat", argv=["/bin/cat", "f"]),
             line(ev="exec", pid=1, via="os.posix_spawn", prog="/bin/cat", argv=["/bin/cat", "f"])]), PY)[1],
         [PY, "/bin/cat"])
    case("adjacent: a posix_spawn of a DIFFERENT argv is a second execution",
         lambda: read_audit("\n".join([
             line(ev="start", pid=1),
             line(ev="exec", pid=1, via="subprocess.Popen", prog="/bin/cat", argv=["/bin/cat", "f"]),
             line(ev="exec", pid=1, via="os.posix_spawn", prog="/bin/cat", argv=["/bin/cat", "g"])]), PY)[1],
         [PY, "/bin/cat", "/bin/cat"])
    case("read_audit: opens are deduplicated in first-seen order",
         lambda: read_audit("\n".join([line(ev="start", pid=1), line(ev="open", pid=1, path="/b"),
                                       line(ev="open", pid=1, path="/a"), line(ev="open", pid=1, path="/b")]),
                            PY)[0], ["/b", "/a"])
    case("read_audit: a non-Python top with no start event is unobservable by name, not missing a hook",
         lambda: [u.split(":")[0] for u in read_audit("", "/bin/cat")[2] if not u.startswith("ALWAYS:")],
         ["cat"])
    case("read_audit: a Python top with no start event is a missing hook",
         lambda: [("without the audit hook" in u) for u in read_audit("", PY)[2] if not u.startswith("ALWAYS:")],
         [True])
    case("read_audit: a line that does not parse is CANNOT RUN, never skipped",
         lambda: raises(lambda: read_audit("{not json", PY)).startswith("CANNOT RUN: audit log"), True)

    case("read_audit: a JSON line that is not an event is CANNOT RUN, never skipped",
         lambda: raises(lambda: read_audit(line(ev="close", pid=1), "/bin/cat")).startswith("CANNOT RUN: audit log"),
         True)

    case("read_audit: events from a process ANOTHER record started are not attributed to this one, and are named",
         lambda: (lambda r: (r[0], r[1], [u for u in r[2] if u.startswith("earlier:")] != []))(read_audit("\n".join([
             line(ev="start", pid=1, run="r2"), line(ev="open", pid=1, run="r2", path="/mine"),
             line(ev="open", pid=9, run="r1", path="/theirs"),
             line(ev="exec", pid=9, run="r1", via="subprocess.Popen", prog="/bin/cat", argv=["/bin/cat"])]), PY,
             run="r2")),
         (["/mine"], [PY], True))
    case("read_audit: a started pid still alive at the end is named as outliving the record, by pid",
         lambda: [u for u in read_audit("\n".join([line(ev="start", pid=1), line(ev="start", pid=7)]), PY,
                                        alive={7}.__contains__)[2] if "outlived the record" in u and "pid 7" in u]
         != [], True)

    # --- the CLI -----------------------------------------------------------------------------------
    def cli(args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(args)
        return rc, out.getvalue(), err.getvalue()

    def cli_ok():
        root = Path(tempfile.mkdtemp(prefix="mkt-cli-")) / "w"
        rc, out, _ = cli(["--root", str(root), "--allow", "python3", "--port", str(free_port()),
                          "--", "python3", "-c", "print(41 + 1)"])
        rec = json.loads(out)
        return (rc, rec["rc"], rec["stdout"], sorted(rec))
    case("CLI writes the RunRecord as JSON", cli_ok,
         (0, 0, "42\n", ["executed", "opened", "rc", "stderr", "stdout", "unobservable"]))

    def cli_cannot(allow, argv):
        root = Path(tempfile.mkdtemp(prefix="mkt-cli-")) / "w"
        rc, out, err = cli(["--root", str(root), "--allow", allow, "--port", str(free_port()), "--", *argv])
        return (rc, out, err.startswith("CANNOT RUN:"))
    case("CLI: an unreachable command is CANNOT RUN (rc 2)",
         lambda: cli_cannot("no-such-cmd-mkt", ["no-such-cmd-mkt"]), (2, "", True))
    case("CLI: an argv[0] outside the allow-list is CANNOT RUN (rc 2)",
         lambda: cli_cannot("cat", ["python3", "-c", "pass"]), (2, "", True))

    def cli_refused():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        try:
            root = Path(tempfile.mkdtemp(prefix="mkt-cli-")) / "w"
            rc, out, err = cli(["--root", str(root), "--allow", "cat", "--port", str(s.getsockname()[1]),
                                "--", "cat", "/dev/null"])
        finally:
            s.close()
        return (rc, out, "preflight refused" in err)
    case("CLI: a preflight refusal starts nothing (rc 2, no record)", cli_refused, (2, "", True))

    def cli_repo_cwd():
        root = Path(tempfile.mkdtemp(prefix="mkt-cli-")) / "w"
        rc, out, err = cli(["--root", str(root), "--allow", "python3", "--port", str(free_port()),
                            "--cwd", str(REPO / "scripts"), "--", "python3", "-c", "import mkt_stage"])
        return (rc, out, err.startswith("CANNOT RUN: cwd "))
    case("CLI: --cwd inside the repository is CANNOT RUN (rc 2), never a run that imports the author's scripts",
         cli_repo_cwd, (2, "", True))

    def no_separator():
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["--root", "/nonexistent-mkt", "--allow", "cat"])
        return (rc, err.getvalue().startswith("usage:"))
    case("CLI: no `--` before the command is a usage error (rc 2), and builds nothing", no_separator, (2, True))

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

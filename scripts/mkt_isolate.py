#!/usr/bin/env python3
"""Build a stranger's world — fresh HOME, allow-listed PATH, an audit-hook capture — and run one command in it
(marketplace-inventory plan, Task 2; spec §6 and §7 item 0b).

    python3 scripts/mkt_isolate.py --self-test  # 49 cases
    python3 scripts/mkt_isolate.py --root DIR --allow CMD,... [--cwd DIR] [--timeout S] [--port N] -- ARGV...

build_world(root, allow) makes the world under an EMPTY root: home/, tmp/, bin/ (one symlink per allow-listed
command, nothing else), hook/sitecustomize.py. Its env is built from nothing (ENV_KEYS). preflight(world, port)
returns every reason the author's environment would leak in (root or a HOME entry inside the repository, an env key
or PATH beyond the world's, a bindir entry off the allow-list or resolving into the repo, the explainer port already
listening); empty means clear. run_isolated(world, argv, cwd, timeout) runs one command and returns a RunRecord:
rc, stdout, stderr, the files Python processes OPENED (audit hook), the programs EXECUTED, and what is UNOBSERVABLE —
every non-Python program, every Python process that never loaded the hook, and the three ALWAYS entries.
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
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# The world's whole environment: built from nothing, so a key outside this set is a leak (preflight refuses it).
ENV_KEYS = frozenset({"HOME", "TMPDIR", "PATH", "LANG", "PYTHONPATH"})
# A program name the capture counts as a Python interpreter — the only kind the audit hook runs inside.
PYTHON_NAME = re.compile(r"^python[\d.]*$")
# What the capture cannot see, in EVERY record (spec §6: "state what it cannot see"). Prefixed so a case can tell
# these apart from the per-program entries, which name the program.
ALWAYS = (
    "ALWAYS: file access by non-Python processes (git, node, gh, cat, ...) — the hook runs only inside Python",
    "ALWAYS: network access — nothing here captures sockets",
    "ALWAYS: anything before a Python interpreter imports sitecustomize (startup, the stdlib imported before it)",
)
AUDIT_LOG = "audit.jsonl"

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


def _put(rec):
    rec["pid"] = _os.getpid()
    _os.write(_FD, (_json.dumps(rec, default=str) + "\n").encode())


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
    env = {"HOME": str(home), "TMPDIR": str(tmpdir), "PATH": str(bindir), "LANG": "C.UTF-8",
           "PYTHONPATH": str(hookdir)}
    return World(root, home, bindir, tmpdir, hookdir, tuple(allow), env)


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
    reasons = []
    if _inside(world.root, REPO):
        reasons.append(f"world root {world.root} lies inside the repository {REPO}")
    extra = sorted(set(world.env) - ENV_KEYS)
    if extra:
        reasons.append(f"world env holds key(s) outside the declared set: {', '.join(extra)}")
    if world.env.get("PATH") != str(world.bindir):
        reasons.append(f"world PATH {world.env.get('PATH')!r} is not exactly its bindir {world.bindir}")
    if world.home.is_dir():
        for entry in sorted(world.home.iterdir()):
            if _inside(entry, REPO):
                reasons.append(f"HOME/{entry.name} resolves inside the repository ({entry.resolve()})")
    else:
        reasons.append(f"world HOME {world.home} is not a directory")
    if world.bindir.is_dir():
        for entry in sorted(world.bindir.iterdir()):
            if entry.name not in world.allow:
                reasons.append(f"bindir entry {entry.name} is not on the allow-list {list(world.allow)}")
            if _inside(entry, REPO):
                reasons.append(f"allow-listed command {entry.name} resolves inside the repository "
                               f"({entry.resolve()})")
    else:
        reasons.append(f"world bindir {world.bindir} is not a directory")
    port = explainer_port(world.env) if port is None else port
    with socket.socket() as s:
        s.settimeout(1.0)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            reasons.append(f"port {port} is already listening: a server the stranger did not start would answer")
    return reasons


def _is_python(prog: str) -> bool:
    return bool(PYTHON_NAME.match(Path(prog).name))


def read_audit(text: str, top: str) -> tuple[list[str], list[str], list[str]]:
    """PURE. (opened, executed, unobservable) from one run's audit log and the program the run started (`top`).

    `executed` is `top` then every launch the hook saw; a `posix_spawn` repeating the `Popen` just before it in the
    same pid is the same launch (subprocess may spawn through it). Every non-Python program executed is named as
    unobservable, and so is every Python process that never wrote a `start` event (started `-I`/`-E`/`-S`, or
    its sitecustomize shadowed): its opens are NOT CAPTURED, never zero. A line that does not parse is CANNOT RUN."""
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
                            f"shadowed sitecustomize); their file access is NOT CAPTURED")
    return opened, executed, unobservable


def run_isolated(world: World, argv: list[str], cwd: Path, timeout: int) -> RunRecord:
    """Run `argv` in the world: its env only, `argv[0]` looked up on the world's PATH (or an executable path inside
    the world root). The audit log is emptied first, so a record holds this run only. A command the world cannot
    reach, an OS error starting it, or a timeout is CANNOT RUN. Bound: a grandchild that outlives a timeout is not
    killed."""
    if not argv:
        raise CannotRun("nothing to run: argv is empty")
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
    log.write_text("")
    try:
        p = subprocess.run(argv, executable=top, cwd=cwd, env=world.env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CannotRun(f"timed out after {timeout} s: {argv!r}") from None
    except OSError as e:
        raise CannotRun(f"{prog}: {type(e).__name__}: {e}") from None
    opened, executed, unobservable = read_audit(log.read_text(), top)
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
        """The unobservable entries naming one program — the static three never name one."""
        return [u for u in rec.unobservable if u.startswith(word + ":")]

    STATIC = 3

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

    # --- run_isolated ------------------------------------------------------------------------------
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
        return (f1 in rec.opened, f2 in rec.opened)
    case("a second run does not inherit the first run's opens", second_run, (False, True))

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

    case("every record carries the three static unobservables, for two commands",
         lambda: [len([u for u in run(fresh(a), argv).unobservable if u.startswith("ALWAYS:")])
                  for a, argv in ((("python3",), ["python3", "-c", "pass"]), (("cat",), ["cat", "/dev/null"]))],
         [STATIC, STATIC])
    case("rc, stdout and stderr are the child's",
         lambda: (lambda r: (r.rc, r.stdout, r.stderr))(
             run(fresh(), ["python3", "-c", "import sys; print('x'); print('e', file=sys.stderr); sys.exit(3)"])),
         (3, "x\n", "e\n"))
    # macOS CoreFoundation sets `__CF_USER_TEXT_ENCODING` INSIDE the child (measured 2026-11-15: absent from the
    # env passed, present in the child's os.environ). Nothing here passes it, so it is dropped before comparing.
    case("the child's environment is the world's, key for key (bar macOS's in-process __CF_ keys)",
         lambda: (lambda w: {k: v for k, v in json.loads(run(w, ["python3", "-c",
                             "import os,json; print(json.dumps(dict(os.environ)))"]).stdout).items()
                             if not k.startswith("__CF_")} == w.env)(fresh()), True)
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

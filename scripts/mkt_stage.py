#!/usr/bin/env python3
"""Package declared files into a throwaway local marketplace, and install one of its plugins in a stranger's world
(marketplace-inventory plan, Task 3; spec §6 and §7 item 0).

    python3 scripts/mkt_stage.py --self-test  # 63 cases
    python3 scripts/mkt_stage.py --out DIR --package NAME --version V [--skill PATH]... [--file PATH]...
                                 [--marketplace NAME]

stage(packages, out) writes `<out>/.claude-plugin/marketplace.json` and, per PackageSpec, a plugin directory
`<out>/<name>/` holding `.claude-plugin/plugin.json`, every declared skill directory at `skills/<its last name>`
(so `.agents/skills/shared` lands at `skills/shared` and a skill's `../shared/x.md` resolves as it does in the
repository) and every declared file at its repo-relative path. It COPIES and never rewrites (the plan's
*Evaluate, never repair*): bytes and permission bits are the source's. A link is copied as the contents it points
to, never as a link. Everything is planned before anything is written, so a refusal writes nothing.
install(world, mkt_root, plugin) runs `claude plugin marketplace add` and `claude plugin install <plugin>@<mkt>`
inside a `mkt_isolate` world and returns the installed directory.
Anything this cannot do is CANNOT RUN (rc 2): a declared path that is absent, absolute, outside the repository, a
dangling or looping link, an empty package, two declarations landing on one path, a failed `claude` call, an
installed directory that is not there after a zero exit.

THE DECLARED COUNT EXCLUDES ONE LIVE CASE. `the written marketplace.json passes claude plugin validate` calls the
real `claude`, in a world built by `mkt_isolate`. Where `claude` is absent (CI has none) it prints
`NOT RUN: claude missing` and is counted as not run. It is tallied apart from the N/N line in both places, so the
declared count is the same with and without `claude`; a live failure still prints `[FAIL]` and exits 1.

Bounds: staging ships what is on DISK under a declared skill directory, not what git tracks; `install` is exercised
here only against a stand-in for `run_isolated` (the first live install is the plan's Task 4).
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path

from mkt_isolate import CannotRun, World, build_world, run_isolated

REPO = Path(__file__).resolve().parent.parent
# The marketplace's default name. A local, throwaway one: never the published marketplace (spec §6, §10).
MARKETPLACE = "mkt-local"
# Plugin and marketplace names: what `claude plugin install <plugin>@<marketplace>` can address.
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]*$")
# Where this repository keeps its skills. A FILE from below here is refused in `files`: its skill directory is
# declared under `skills`, which is what maps it to `<plugin>/skills/<name>`.
SKILLS_HOME = ".agents/skills"
# The plugin's own metadata directory. A declared file may not land in it.
META = ".claude-plugin"


@dataclasses.dataclass(frozen=True)
class PackageSpec:
    name: str
    version: str
    skills: list[str]
    files: list[str]


def plan(spec: PackageSpec, repo: Path) -> list[tuple[Path, str]]:
    """Every (source file, path under the plugin root) `spec` ships, links resolved. Writes nothing."""
    top = Path(repo).resolve()
    dests: dict[str, Path] = {}

    def add(src: Path, dest: str) -> None:
        if dest in dests:
            raise CannotRun(f"two declarations land on {dest} in package {spec.name}: {dests[dest]} and {src}")
        dests[dest] = src

    for s in spec.skills:
        rel = _declared(s)
        real = _real(top / rel, top, rel)
        if not real.is_dir():
            raise CannotRun(f"{rel} is not a directory: a skill is declared by its directory")
        found = _tree(real, rel, top, frozenset())
        if not found:
            raise CannotRun(f"{rel} holds no files: an empty skill directory is not a skill")
        for src, sub in found:
            add(src, f"skills/{Path(rel).name}/{sub}")
    for f in spec.files:
        rel = _declared(f)
        real = _real(top / rel, top, rel)
        if not real.is_file():
            raise CannotRun(f"{rel} is not a regular file: `files` takes files (a skill directory goes in `skills`)")
        if _below(real, top / SKILLS_HOME):
            raise CannotRun(f"{rel} is under {SKILLS_HOME}: declare its skill directory in `skills`, which is what "
                            f"lands it at skills/<name>")
        if rel.split("/")[0] == META:
            raise CannotRun(f"{rel} would land in the plugin's own {META}, which staging writes")
        add(real, rel)
    if not dests:
        raise CannotRun(f"package {spec.name} declares no files: an empty package cannot be staged")
    return [(src, dest) for dest, src in dests.items()]


def _declared(path: str) -> str:
    """A declared path, normalised (`./` dropped). Refused unless repo-relative with no `..`."""
    parts = Path(path).parts
    if not parts or Path(path).is_absolute() or ".." in parts:
        raise CannotRun(f"declared path {path!r} is not a repo-relative path (no absolute path, no `..`, not empty)")
    return "/".join(parts)


def _below(path: Path, top: Path) -> bool:
    return path == top or top in path.parents


def _real(path: Path, top: Path, rel: str) -> Path:
    """`path` with every link followed. Refused when absent, dangling, looping, or outside the repository `top`."""
    if not os.path.lexists(path):
        raise CannotRun(f"{rel} does not exist in {top}")
    try:
        real = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise CannotRun(f"{rel} is a dangling or looping link") from None
    if not _below(real, top):
        raise CannotRun(f"{rel} resolves to {real}, outside the repository {top}: staging it would ship a file "
                        f"the repository does not hold")
    return real


def _tree(real: Path, rel: str, top: Path, above: frozenset) -> list[tuple[Path, str]]:
    """Every file below directory `real` as (resolved source, path relative to it), links followed. `above` holds
    the resolved directories on the way down: meeting one again is a link cycle."""
    out, here = [], above | {real}
    for name in sorted(os.listdir(real)):
        child = _real(real / name, top, f"{rel}/{name}")
        if child.is_dir():
            if child in here:
                raise CannotRun(f"{rel}/{name} links back to a directory above it: a link cycle")
            out += [(src, f"{name}/{sub}") for src, sub in _tree(child, f"{rel}/{name}", top, here)]
        elif child.is_file():
            out.append((child, name))
        else:
            raise CannotRun(f"{rel}/{name} is neither a file nor a directory")
    return out


def stage(packages: list[PackageSpec], out: Path, marketplace: str = MARKETPLACE, repo: Path = REPO) -> Path:
    """Write the marketplace under `out` (absent or empty, outside `repo`) and return its root."""
    top, out = Path(repo).resolve(), Path(out).absolute()
    if not packages:
        raise CannotRun("no packages: a marketplace with nothing in it cannot be staged")
    if not NAME_RE.match(marketplace):
        raise CannotRun(f"marketplace name {marketplace!r} is not a name ({NAME_RE.pattern})")
    seen = set()
    for spec in packages:
        if not NAME_RE.match(spec.name):
            raise CannotRun(f"package name {spec.name!r} is not a name ({NAME_RE.pattern})")
        if not VERSION_RE.match(spec.version):
            raise CannotRun(f"package {spec.name}: version {spec.version!r} is not a version ({VERSION_RE.pattern})")
        if spec.name in seen:
            raise CannotRun(f"two packages are named {spec.name}")
        seen.add(spec.name)
    if _below(out.resolve(), top):
        raise CannotRun(f"{out} is inside the repository {top}: a marketplace is staged outside it")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise CannotRun(f"{out} is not an empty directory: a marketplace is staged fresh, never onto another")
    plans = [(spec, plan(spec, top)) for spec in packages]     # every refusal happens before the first write
    for spec, pairs in plans:
        plugin = out / spec.name
        for src, dest in pairs:
            dst = plugin / dest
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, stat.S_IMODE(src.stat().st_mode))
        _write_json(plugin / META / "plugin.json",
                    {"name": spec.name, "version": spec.version, "description": _description(spec.name)})
    _write_json(out / META / "marketplace.json",
                {"name": marketplace, "owner": {"name": "mkt_stage.py"},
                 "plugins": [{"name": spec.name, "source": f"./{spec.name}", "description": _description(spec.name),
                              "version": spec.version} for spec in packages]})
    return out


def _description(name: str) -> str:
    return f"{name}: staged by mkt_stage.py for a local experiment"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")


def read_marketplace(mkt_root: Path) -> tuple[str, dict[str, str]]:
    """The marketplace's name and each plugin's version, read from the staged `marketplace.json`."""
    path = Path(mkt_root) / META / "marketplace.json"
    try:
        data = json.loads(path.read_text())
        name, versions = data["name"], {p["name"]: p["version"] for p in data["plugins"]}
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise CannotRun(f"{path}: not a readable marketplace manifest ({type(e).__name__}: {e})") from None
    return name, versions


def install(world: World, mkt_root: Path, plugin: str, timeout: int = 120, run=run_isolated) -> Path:
    """Add the marketplace and install `plugin` inside `world`; return the installed directory, which exists."""
    mkt, versions = read_marketplace(mkt_root)
    if plugin not in versions:
        raise CannotRun(f"plugin {plugin!r} is not in marketplace {mkt} ({', '.join(sorted(versions))})")
    cwd = world.root / "work"
    cwd.mkdir(parents=True, exist_ok=True)
    said = ""
    for argv in (["claude", "plugin", "marketplace", "add", str(mkt_root)],
                 ["claude", "plugin", "install", f"{plugin}@{mkt}"]):
        said = " ".join(argv[:4] if argv[2] == "marketplace" else argv)
        rec = run(world, argv, cwd, timeout)
        if rec.rc != 0:
            raise CannotRun(f"{said} exited {rec.rc}: {rec.stderr.strip() or rec.stdout.strip()}")
    # Measured 2026-11-11 under a fresh HOME (the plan's Task 3 probe): the installed tree lands here.
    installed = world.home / ".claude" / "plugins" / "cache" / mkt / plugin / versions[plugin]
    if not installed.is_dir():
        raise CannotRun(f"{said} exited 0 but {installed} is not a directory: nothing was installed where "
                        f"the experiment reads it")
    return installed


USAGE = ("usage: mkt_stage.py --out DIR --package NAME --version V [--skill PATH]... [--file PATH]... "
         "[--marketplace NAME]\n       mkt_stage.py --self-test")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    ap = argparse.ArgumentParser(prog="mkt_stage.py", usage=USAGE)
    ap.add_argument("--out", required=True)
    ap.add_argument("--package", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--skill", action="append", default=[])
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--marketplace", default=MARKETPLACE)
    opts = ap.parse_args(argv)
    try:
        root = stage([PackageSpec(opts.package, opts.version, opts.skill, opts.file)], Path(opts.out),
                     opts.marketplace)
    except CannotRun as e:
        print(f"CANNOT RUN: {e}", file=sys.stderr)
        return 2
    print(root)
    return 0


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = live_fail = 0

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

    def tmp(prefix="mkt-stage-"):
        return Path(tempfile.mkdtemp(prefix=prefix)).resolve()

    X_BYTES = b"#!/usr/bin/env python3\r\nprint('x')  \t\n\xff\xfe no newline at end   "
    Y_BYTES = b"Y = 1\n"

    def put(path, data, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)

    def repo():
        """A fixture repository: two skills, the shared directory (no SKILL.md), `.claude/skills/a -> b`, two
        scripts (one executable, with bytes any 'tidying' would change), and an OUTSIDE directory beside it."""
        top = tmp("mkt-repo-")
        r = top / "repo"
        put(r / ".agents/skills/brief/SKILL.md",
            b"---\nname: brief\ndescription: a brief\n---\nFollow ../shared/contract.md\n")
        put(r / ".agents/skills/brief/refs/deep.md", b"deep\n")
        put(r / ".agents/skills/shared/contract.md", b"the contract\n")
        put(r / ".agents/skills/b/SKILL.md", b"---\nname: b\ndescription: the b skill\n---\nb body\n")
        (r / ".claude/skills").mkdir(parents=True)
        (r / ".claude/skills/a").symlink_to("../../.agents/skills/b")
        put(r / "scripts/x.py", X_BYTES, 0o755)
        put(r / "scripts/lib/y.py", Y_BYTES)
        put(top / "outside/secret.md", b"the author's own\n")
        put(top / "outside/skill/SKILL.md", b"outside skill\n")
        return r

    def spec(skills=(), files=(), name="pkg", version="0.0.1"):
        return PackageSpec(name, version, list(skills), list(files))

    def staged(r, skills=(), files=(), name="pkg", version="0.0.1"):
        """Stage one package from fixture repo `r`; return its plugin root."""
        return stage([spec(skills, files, name, version)], tmp() / "out", repo=r) / name

    def tree(top):
        """Every file under `top` as a sorted list of posix paths; a symlink is listed with a trailing `@`."""
        out = []
        for d, dirs, names in os.walk(top):
            for n in dirs + names:
                p = Path(d, n)
                if p.is_symlink():
                    out.append(p.relative_to(top).as_posix() + "@")
                elif p.is_file():
                    out.append(p.relative_to(top).as_posix())
        return sorted(out)

    def sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    def refused(fn, start):
        """`fn` is CANNOT RUN with a message starting `start`."""
        got = raises(fn)
        return True if got.startswith("CANNOT RUN: " + start) else got

    # --- where declared things land ----------------------------------------------------------------
    case("a declared file lands at its repo-relative path under the plugin",
         lambda: (lambda p: [(p / f).is_file() for f in ("scripts/x.py", "scripts/lib/y.py")])(
             staged(repo(), files=["scripts/x.py", "scripts/lib/y.py"])), [True, True])
    case("a declared skill dir lands at skills/<name>, with its nested files",
         lambda: tree(staged(repo(), skills=[".agents/skills/brief"])),
         [".claude-plugin/plugin.json", "skills/brief/SKILL.md", "skills/brief/refs/deep.md"])
    case(".agents/skills/shared lands at <plugin>/skills/shared, so ../shared/x.md resolves from an installed skill",
         lambda: (lambda p: (p / "skills/brief" / "../shared/contract.md").read_bytes())(
             staged(repo(), skills=[".agents/skills/brief", ".agents/skills/shared"])), b"the contract\n")
    case("the plugin tree holds exactly the declared files and plugin.json (an identity, not a count)",
         lambda: tree(staged(repo(), skills=[".agents/skills/shared"], files=["scripts/lib/y.py"])),
         [".claude-plugin/plugin.json", "scripts/lib/y.py", "skills/shared/contract.md"])
    case("plan lists (source, destination) for skills then files, and writes nothing",
         lambda: (lambda r: [(s.relative_to(r).as_posix(), d) for s, d in
                             plan(spec([".agents/skills/shared"], ["scripts/x.py"]), r)])(repo()),
         [(".agents/skills/shared/contract.md", "skills/shared/contract.md"), ("scripts/x.py", "scripts/x.py")])
    case("plan refuses what stage would refuse, before anything exists to write to",
         lambda: refused(lambda: plan(spec(files=["scripts/absent.py"]), repo()), "scripts/absent.py does not exist"),
         True)
    case("a `./` in a declared file path does not change where it lands",
         lambda: tree(staged(repo(), files=["./scripts/./x.py"])), [".claude-plugin/plugin.json", "scripts/x.py"])

    # --- links -------------------------------------------------------------------------------------
    case("a symlinked skill dir is copied as the contents its link points to, not as a link",
         lambda: (lambda p: ((p / "skills/a").is_symlink(), tree(p),
                             (p / "skills/a/SKILL.md").read_bytes().endswith(b"b body\n")))(
             staged(repo(), skills=[".claude/skills/a"])),
         (False, [".claude-plugin/plugin.json", "skills/a/SKILL.md"], True))

    def linked_file():
        r = repo()
        (r / ".agents/skills/brief/alias.md").symlink_to("../shared/contract.md")
        (r / "scripts/z.py").symlink_to("lib/y.py")
        p = staged(r, skills=[".agents/skills/brief"], files=["scripts/z.py"])
        return [(p / f).is_symlink() or (p / f).read_bytes() for f in ("skills/brief/alias.md", "scripts/z.py")]
    case("a symlinked FILE, in a skill or declared, is copied as the bytes it points to",
         linked_file, [b"the contract\n", Y_BYTES])

    def linked_subdir():
        r = repo()
        (r / ".agents/skills/brief/more").symlink_to("../shared")
        return tree(staged(r, skills=[".agents/skills/brief"]))
    case("a symlinked directory INSIDE a skill is copied as contents",
         linked_subdir, [".claude-plugin/plugin.json", "skills/brief/SKILL.md", "skills/brief/more/contract.md",
                         "skills/brief/refs/deep.md"])

    def outside(kind):
        r = repo()
        if kind == "file":
            (r / "scripts/leak.md").symlink_to("../../outside/secret.md")
            return refused(lambda: staged(r, files=["scripts/leak.md"]), "scripts/leak.md resolves to ")
        if kind == "skill":
            (r / ".agents/skills/leak").symlink_to("../../../outside/skill")
            return refused(lambda: staged(r, skills=[".agents/skills/leak"]), ".agents/skills/leak resolves to ")
        (r / ".agents/skills/brief/leak.md").symlink_to("../../../../outside/secret.md")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"]),
                       ".agents/skills/brief/leak.md resolves to ")
    case("a declared file linking OUTSIDE the repository is CANNOT RUN", lambda: outside("file"), True)
    case("a declared skill dir linking OUTSIDE the repository is CANNOT RUN", lambda: outside("skill"), True)
    case("a link INSIDE a skill pointing outside the repository is CANNOT RUN", lambda: outside("nested"), True)

    def dangling():
        r = repo()
        (r / ".agents/skills/brief/gone.md").symlink_to("nowhere.md")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"]),
                       ".agents/skills/brief/gone.md is a dangling or looping link")
    case("a dangling link inside a skill is CANNOT RUN, never a skipped file", dangling, True)

    def cycle():
        r = repo()
        (r / ".agents/skills/brief/up").symlink_to("..")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"]), ".agents/skills/brief/up/brief links back")
    case("a link cycle inside a skill is CANNOT RUN, never an endless walk", cycle, True)

    def self_link():
        r = repo()
        (r / ".agents/skills/brief/me").symlink_to(".")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"]), ".agents/skills/brief/me links back")
    case("a link to its own directory is a cycle too", self_link, True)

    def fifo():
        r = repo()
        os.mkfifo(r / ".agents/skills/brief/pipe")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"]),
                       ".agents/skills/brief/pipe is neither a file nor a directory")
    case("something in a skill that is neither file nor directory is CANNOT RUN, never skipped", fifo, True)

    # --- declarations that cannot be staged ----------------------------------------------------------
    case("a declared path that does not exist is CANNOT RUN",
         lambda: [refused(lambda: staged(repo(), files=["scripts/absent.py"]), "scripts/absent.py does not exist"),
                  refused(lambda: staged(repo(), skills=[".agents/skills/absent"]),
                          ".agents/skills/absent does not exist")], [True, True])
    case("an absolute declared path is CANNOT RUN (a declaration is repo-relative)",
         lambda: (lambda r: [refused(lambda: staged(r, files=[str(r / "scripts/x.py")]), "declared path "),
                             refused(lambda: staged(r, skills=[str(r / ".agents/skills/brief")]),
                                     "declared path ")])(repo()), [True, True])
    case("a declared path with `..` is CANNOT RUN",
         lambda: refused(lambda: staged(repo(), files=["scripts/../scripts/x.py"]), "declared path "), True)
    case("an empty declared path is CANNOT RUN",
         lambda: [refused(lambda: staged(repo(), files=[e]), "declared path ") for e in ("", ".")], [True, True])
    case("a skill entry that is a file is CANNOT RUN",
         lambda: refused(lambda: staged(repo(), skills=[".agents/skills/brief/SKILL.md"]),
                         ".agents/skills/brief/SKILL.md is not a directory"), True)
    case("a file entry that is a directory is CANNOT RUN",
         lambda: refused(lambda: staged(repo(), files=["scripts/lib"]), "scripts/lib is not a regular file"), True)
    case("a FILE from under .agents/skills declared in files is CANNOT RUN (it would land outside skills/)",
         lambda: refused(lambda: staged(repo(), files=[".agents/skills/shared/contract.md"]),
                         ".agents/skills/shared/contract.md is under .agents/skills"), True)
    case("...and so is the same file reached through a link (.claude/skills/a/SKILL.md)",
         lambda: refused(lambda: staged(repo(), files=[".claude/skills/a/SKILL.md"]),
                         ".claude/skills/a/SKILL.md is under .agents/skills"), True)
    case("two skills landing on one name is CANNOT RUN (.agents/skills/b and its link named b)",
         lambda: (lambda r: ((r / ".claude/skills/b").symlink_to("../../.agents/skills/b"),
                             refused(lambda: staged(r, skills=[".agents/skills/b", ".claude/skills/b"]),
                                     "two declarations land on skills/b/SKILL.md"))[1])(repo()), True)
    case("a file declared twice is CANNOT RUN",
         lambda: refused(lambda: staged(repo(), files=["scripts/x.py", "./scripts/x.py"]),
                         "two declarations land on scripts/x.py"), True)

    def meta_file():
        r = repo()
        put(r / ".claude-plugin/plugin.json", b"{}\n")
        return refused(lambda: staged(r, files=[".claude-plugin/plugin.json"]),
                       ".claude-plugin/plugin.json would land in the plugin's own .claude-plugin")
    case("a declared file landing in the plugin's .claude-plugin is CANNOT RUN", meta_file, True)
    case("a package declaring nothing is CANNOT RUN",
         lambda: refused(lambda: staged(repo()), "package pkg declares no files"), True)

    def empty_skill():
        r = repo()
        (r / ".agents/skills/hollow/sub").mkdir(parents=True)
        return refused(lambda: staged(r, skills=[".agents/skills/hollow"], files=["scripts/x.py"]),
                       ".agents/skills/hollow holds no files")
    case("a skill directory holding no files is CANNOT RUN, even beside a real file", empty_skill, True)
    case("no packages at all is CANNOT RUN",
         lambda: refused(lambda: stage([], tmp() / "out", repo=repo()), "no packages"), True)

    # --- names ---------------------------------------------------------------------------------------
    case("a package name `claude plugin install` cannot address is CANNOT RUN, for two bad names",
         lambda: [refused(lambda: staged(repo(), files=["scripts/x.py"], name=n), "package name ")
                  for n in ("Has Space", "../up")], [True, True])
    case("a version that is empty or a path is CANNOT RUN",
         lambda: [refused(lambda: staged(repo(), files=["scripts/x.py"], version=v), "package pkg: version ")
                  for v in ("", "1/2")], [True, True])
    case("two packages with one name is CANNOT RUN",
         lambda: (lambda r: refused(lambda: stage([spec(files=["scripts/x.py"]), spec(files=["scripts/lib/y.py"])],
                                                  tmp() / "out", repo=r), "two packages are named pkg"))(repo()),
         True)
    case("a marketplace name that is not a name is CANNOT RUN",
         lambda: (lambda r: refused(lambda: stage([spec(files=["scripts/x.py"])], tmp() / "out",
                                                  marketplace="my mkt", repo=r), "marketplace name "))(repo()), True)

    # --- the out directory ---------------------------------------------------------------------------
    def out_not_empty():
        out = tmp()
        (out / "left-over").write_text("x")
        return refused(lambda: stage([spec(files=["scripts/x.py"])], out, repo=repo()), f"{out} is not an empty")
    case("a non-empty out directory is CANNOT RUN (a marketplace is staged fresh)", out_not_empty, True)
    case("an EMPTY existing out directory is used",
         lambda: (lambda out: stage([spec(files=["scripts/x.py"])], out, repo=repo()) == out)(tmp()), True)
    case("an out directory inside the repository is CANNOT RUN (experiments run outside it)",
         lambda: (lambda r: (refused(lambda: stage([spec(files=["scripts/x.py"])], r / "build/mkt", repo=r),
                                     f"{r / 'build/mkt'} is inside the repository"),
                             (r / "build").exists()))(repo()), (True, False))

    def refusal_writes_nothing():
        r, out = repo(), tmp() / "out"
        got = refused(lambda: stage([spec(files=["scripts/x.py"], name="good"),
                                     spec(files=["scripts/absent.py"], name="bad")], out, repo=r),
                      "scripts/absent.py does not exist")
        return (got, out.exists())
    case("a refusal in the SECOND package writes nothing at all", refusal_writes_nothing, (True, False))

    # --- the no-repair rule --------------------------------------------------------------------------
    def bytes_unchanged():
        r = repo()
        p = staged(r, skills=[".agents/skills/brief", ".agents/skills/shared"],
                   files=["scripts/x.py", "scripts/lib/y.py"])
        pairs = [(".agents/skills/brief/SKILL.md", "skills/brief/SKILL.md"),
                 (".agents/skills/brief/refs/deep.md", "skills/brief/refs/deep.md"),
                 (".agents/skills/shared/contract.md", "skills/shared/contract.md"),
                 ("scripts/x.py", "scripts/x.py"), ("scripts/lib/y.py", "scripts/lib/y.py")]
        return ([sha(r / s) == sha(p / d) for s, d in pairs], (p / "scripts/x.py").read_bytes() == X_BYTES)
    case("staging copies bytes unchanged", bytes_unchanged, ([True] * 5, True))
    case("staging keeps permission bits: an executable stays one, a plain file stays plain",
         lambda: (lambda p: [stat.S_IMODE((p / f).stat().st_mode) for f in ("scripts/x.py", "scripts/lib/y.py")])(
             staged(repo(), files=["scripts/x.py", "scripts/lib/y.py"])), [0o755, 0o644])
    case("staging leaves the source tree as it was",
         lambda: (lambda r: (lambda before: (staged(r, skills=[".claude/skills/a"], files=["scripts/x.py"]),
                                             tree(r) == before)[1])(tree(r)))(repo()), True)

    # --- the manifests ---------------------------------------------------------------------------------
    def two_packages():
        r, out = repo(), tmp() / "out"
        root = stage([spec(files=["scripts/x.py"], name="one", version="0.0.1"),
                      spec([".agents/skills/brief"], name="two", version="1.2.0")], out, repo=r)
        return (root, json.loads((root / ".claude-plugin/marketplace.json").read_text()), tree(root),
                [json.loads((root / n / ".claude-plugin/plugin.json").read_text()) for n in ("one", "two")], out)

    def desc(n):
        return f"{n}: staged by mkt_stage.py for a local experiment"
    case("stage returns the out directory, as the marketplace root",
         lambda: (lambda t: t[0] == t[4])(two_packages()), True)
    case("marketplace.json names the marketplace and lists each package with its own source and version",
         lambda: two_packages()[1],
         {"name": "mkt-local", "owner": {"name": "mkt_stage.py"},
          "plugins": [{"name": "one", "source": "./one", "description": desc("one"), "version": "0.0.1"},
                      {"name": "two", "source": "./two", "description": desc("two"), "version": "1.2.0"}]})
    case("each package gets its own plugin.json, with its own name and version",
         lambda: two_packages()[3], [{"name": "one", "version": "0.0.1", "description": desc("one")},
                                     {"name": "two", "version": "1.2.0", "description": desc("two")}])
    case("each package's files land under its own directory, and nowhere else",
         lambda: two_packages()[2],
         [".claude-plugin/marketplace.json", "one/.claude-plugin/plugin.json", "one/scripts/x.py",
          "two/.claude-plugin/plugin.json", "two/skills/brief/SKILL.md", "two/skills/brief/refs/deep.md"])
    case("the marketplace name is the caller's when given",
         lambda: read_marketplace(stage([spec(files=["scripts/x.py"])], tmp() / "out", marketplace="other-mkt",
                                        repo=repo())), ("other-mkt", {"pkg": "0.0.1"}))
    case("read_marketplace returns the name and every plugin's version",
         lambda: read_marketplace(two_packages()[0]), ("mkt-local", {"one": "0.0.1", "two": "1.2.0"}))
    case("read_marketplace on a directory with no marketplace.json is CANNOT RUN",
         lambda: (lambda d: refused(lambda: read_marketplace(d), f"{d / '.claude-plugin/marketplace.json'}: "))(
             tmp()), True)

    def bad_manifest(text):
        d = tmp()
        put(d / ".claude-plugin/marketplace.json", text)
        return refused(lambda: read_marketplace(d), f"{d / '.claude-plugin/marketplace.json'}: ")
    case("read_marketplace on a manifest that is not JSON, or lacks a field, is CANNOT RUN",
         lambda: [bad_manifest(t) for t in (b'{"name":', b'{"name": "m"}', b'{"name": "m", "plugins": [{"name": "p"}]}',
                                            b'[1]')], [True] * 4)

    # --- install (against a stand-in for run_isolated; the first live install is Task 4) ---------------
    class Rec:
        def __init__(self, rc, stderr=""):
            self.rc, self.stdout, self.stderr = rc, "", stderr

    def world():
        return build_world(tmp("mkt-world-") / "w", ["cat"])

    def fake(calls, rcs=(0, 0), make=True, version="1.2.0", mkt="mkt-local", plugin="two"):
        """A stand-in for run_isolated: records each call, answers with `rcs` in turn, and (when `make`) creates
        the installed directory on a successful `install`, where the real CLI was measured to put it."""
        def run(w, argv, cwd, timeout):
            calls.append((list(argv), Path(cwd), timeout))
            rc = rcs[len(calls) - 1]
            if make and argv[:3] == ["claude", "plugin", "install"]:
                (w.home / ".claude/plugins/cache" / mkt / plugin / version).mkdir(parents=True)
            return Rec(rc, "boom from claude")
        return run

    def installed(plugin="two", **kw):
        root, w, calls = two_packages()[0], world(), []
        try:
            got = install(w, root, plugin, run=fake(calls, plugin=plugin, **kw))
        except CannotRun as e:
            return (f"CANNOT RUN: {e}", root, w, calls)
        return (got, root, w, calls)

    case("install runs `marketplace add <root>` then `install <plugin>@<marketplace>`, in that order",
         lambda: (lambda t: [c[0] for c in t[3]] == [["claude", "plugin", "marketplace", "add", str(t[1])],
                                                    ["claude", "plugin", "install", "two@mkt-local"]])(installed()),
         True)
    case("install returns the installed directory under the WORLD's home, for two plugins and versions",
         lambda: [(lambda t: t[0] == t[2].home / ".claude/plugins/cache/mkt-local" / p / v and t[0].is_dir())(
             installed(p, version=v)) for p, v in (("two", "1.2.0"), ("one", "0.0.1"))], [True, True])
    case("install runs from a directory inside the world, never the caller's",
         lambda: (lambda t: [c[1] == t[2].root / "work" and c[1].is_dir() for c in t[3]])(installed()),
         [True, True])
    case("install passes its timeout to each call, for two timeouts",
         lambda: [(lambda calls: (install(world(), two_packages()[0], "two", timeout=s, run=fake(calls)),
                                  [c[2] for c in calls])[1])([]) for s in (7, 300)], [[7, 7], [300, 300]])
    case("an installed directory that is NOT there after a zero exit is CANNOT RUN",
         lambda: (lambda t: (str(t[0]).startswith("CANNOT RUN: claude plugin install two@mkt-local exited 0 but "),
                             len(t[3])))(installed(make=False)), (True, 2))
    case("an installed directory for ANOTHER version does not count",
         lambda: str(installed(version="9.9.9")[0]).startswith("CANNOT RUN: claude plugin install two@mkt-local "
                                                               "exited 0 but "), True)
    case("a failed `marketplace add` is CANNOT RUN, carries claude's stderr, and install is never run",
         lambda: (lambda t: (t[0], len(t[3])))(installed(rcs=(1, 0))),
         ("CANNOT RUN: claude plugin marketplace add exited 1: boom from claude", 1))
    case("a failed `install` is CANNOT RUN even if a directory is there",
         lambda: (lambda t: (t[0], len(t[3])))(installed(rcs=(0, 3))),
         ("CANNOT RUN: claude plugin install two@mkt-local exited 3: boom from claude", 2))
    case("a plugin the marketplace does not list is CANNOT RUN, and nothing is run",
         lambda: (lambda t: (str(t[0]).startswith("CANNOT RUN: plugin 'nope' is not in marketplace mkt-local"),
                             t[3]))(installed("nope")), (True, []))

    # --- CLI -----------------------------------------------------------------------------------------
    def cli(args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = main(args)
            except SystemExit as e:
                rc = e.code
        return rc, out.getvalue(), err.getvalue()

    def cli_stages():
        # The CLI stages from REPO, so it declares this very file: the one real path a self-test may rely on.
        out = tmp() / "out"
        rc, o, _ = cli(["--out", str(out), "--package", "cli-pkg", "--version", "0.1.0",
                        "--file", "scripts/mkt_stage.py"])
        return (rc, o == f"{out}\n", read_marketplace(out), sha(out / "cli-pkg/scripts/mkt_stage.py") == sha(__file__))
    case("CLI: stages one package and prints the marketplace root (rc 0)",
         cli_stages, (0, True, ("mkt-local", {"cli-pkg": "0.1.0"}), True))

    def cli_options():
        out = tmp() / "out"
        rc, _, _ = cli(["--out", str(out), "--package", "p2", "--version", "2.0.0", "--marketplace", "named-mkt",
                        "--skill", "scripts/mutations", "--file", "scripts/mkt_stage.py",
                        "--file", "scripts/mkt_isolate.py"])
        return (rc, read_marketplace(out), (out / "p2/skills/mutations/mkt_isolate.json").is_file(),
                (out / "p2/scripts/mkt_isolate.py").is_file())
    case("CLI: --marketplace, --skill and a repeated --file all reach stage",
         cli_options, (0, ("named-mkt", {"p2": "2.0.0"}), True, True))

    def cli_refusal():
        out = tmp() / "out"
        rc, o, e = cli(["--out", str(out), "--package", "p", "--version", "1", "--file", "scripts/no-such-file.py"])
        return (rc, o, e.startswith("CANNOT RUN: scripts/no-such-file.py does not exist"), out.exists())
    case("CLI: a refusal is CANNOT RUN on stderr (rc 2), prints no root and writes nothing",
         cli_refusal, (2, "", True, False))
    def no_out():
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                rc = main(["--package", "p", "--version", "1", "--file", "scripts/mkt_stage.py"])
            except SystemExit as e:
                rc = e.code
        return (rc, err.getvalue().startswith("usage:"))
    case("CLI: a missing --out is a usage error (rc 2)", no_out, (2, True))

    # --- the live case: tallied apart, so the declared count is the same with and without `claude` ------
    LIVE = "the written marketplace.json passes claude plugin validate"
    if shutil.which("claude") is None:
        print(f"NOT RUN: claude missing — `{LIVE}` was not run and is not counted")
    else:
        def validate(root):
            w = build_world(tmp("mkt-world-") / "w", ["claude"])
            return run_isolated(w, ["claude", "plugin", "validate", str(root)], w.home, 120).rc

        def live():
            good = two_packages()[0]
            broken = two_packages()[0]
            (broken / ".claude-plugin/marketplace.json").write_text('{"name":')   # the control: validate CAN fail
            return (validate(good), validate(broken) != 0)
        try:
            got = live()
        except Exception as e:
            got = f"RAISED {type(e).__name__}: {e}"
        if got == (0, True):
            print(f"LIVE ok: `{LIVE}` (and a broken manifest fails it); not in the count below")
        else:
            live_fail += 1
            print(f"[FAIL] {LIVE}: got {got!r} want (0, True)")

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail or live_fail else 0


if __name__ == "__main__":
    sys.exit(main())

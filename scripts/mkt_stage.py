#!/usr/bin/env python3
"""Package declared files into a throwaway local marketplace, and install one of its plugins in a stranger's world
(marketplace-inventory plan, Task 3; spec §6 and §7 item 0).

    python3 scripts/mkt_stage.py --self-test  # 119 cases
    python3 scripts/mkt_stage.py --out DIR --package NAME --version V [--skill PATH]... [--file PATH]...
                                 [--marketplace NAME]
    python3 scripts/mkt_stage.py --declare docs/marketplace/components.json docs/marketplace/shipping-sets.json

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

THE SHIPPING-SET DECLARATION (plan Task 6). `--declare MAP OUT` stages every `plugin` package of the component
map (`spec_from_map`: a file below the skills home names its skill directory, a directory entry its tracked files),
installs each in ONE fresh stranger world, and writes what `declare(installed, m, package)` reads from each INSTALLED
tree: every installed file, and per component the installed files under its installed path, with a count. `declare`
lists the installed directory and nothing else (no repository read, never the publishability scan's output: spec §7
item 2); a link is recorded by its resolved path, and one that dangles, leaves the tree or names a directory is
CANNOT RUN, as is a component with no installed file. A `reusable-workflow` package (ci-layer) is never installed:
`workflow_entry` lists its files from the map, links resolved, with counts and no `installed_files` (spec §2c; C4
argued). `measured_at` is the repository's HEAD. Bound: the map is read through check-shipping-sets.py's
`load_map`, so a map it refuses is CANNOT RUN here.

THE DECLARED COUNT EXCLUDES ONE LIVE CASE. `the written marketplace.json passes claude plugin validate` calls the
real `claude`, in a world built by `mkt_isolate`. Where `claude` is absent (CI has none) it prints
`NOT RUN: claude missing` and is counted as not run. It is tallied apart from the N/N line in both places, so the
declared count is the same with and without `claude`; a live failure still prints `[FAIL]` and exits 1.

THE DECLARED COUNT ALSO EXCLUDES THE FILESYSTEM CASES: a case alias, an NFD name, the sampled sweep of red case 9.
Their answer is the volume's, so they print `FS ok` (or `[FAIL]`, exit 1) where the volume decides them and `NOT RUN:
<why>` where it cannot (Linux CI is case-sensitive); the declared count is the same on macOS and on Linux.

THE SOURCE RULE (Phase 6, architecture-review-2026-11-15-harness-ships-elsewhere-b) decides by OBJECT, never by
spelling. `plan` resolves once, each as (st_dev, st_ino): the PRIVATE roots (`.claude/plans`) and the skills home
(`.agents/skills`), links followed; and every object git TRACKS, by `lstat` of each `git ls-files` name (a name with
a parent that is a link on disk is skipped). `_real` walks a declaration a component at a time from the root (r2
Codex 2). A link must be tracked and have a RELATIVE target, which replaces it; `..` past the root and more than
MAX_LINKS links are refused. Every object the walk STANDS on, the root it starts from included, is refused when it
IS a private root (or, in `files`, the skills home), however it was spelled or reached (r3 F1, F4: a tracked link
`.claude -> dot`, a private root that is itself a link). A private root or skills home that IS the repository or a
directory holding it is refused at `plan`, whatever is declared (r4 Codex 1: `.claude/plans -> ..`). The regular file at the end must be tracked and have exactly one name (no hard link). "Tracked"
also checks the SPELLING: the walked path must equal a name git tracks for that object after NFC on both sides
(r3 F3), case EXACT (coordinator override: one manifest, one answer on macOS and on Linux), and a mis-cased
declaration is refused naming the tracked spelling. "Inside the repository" for the out directory is
`mkt_isolate._reaches`: identity up the ancestors.
THE DESTINATION RULE: the one text fold is `_dest_key` (NFD, casefold, NFC — canonical, never compatibility: `x²`
and `x2` are two files, r3 F2), and `_claim` claims every PREFIX of every destination, so two spellings of one
directory, a file where a directory must be (P6-N1: a file `skills` beside a skill) and the plugin's own
`.claude-plugin` are refused at `plan`, before anything is written.
Bounds: another filesystem's identity rules (another volume, HFS+, a network share) are not tested; the
destination key is a guess at the TARGET's filesystem (case-insensitive, canonical), stricter than a case-sensitive
one; the tree is checked, then copied (a change in between is not seen); an object whose type changes between
`lstat` and the copy is not seen; a hard link whose other name was deleted has one name and ships; a tracked file
ships its working-tree bytes, not its committed ones; `install` is exercised
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
import subprocess
import sys
import tempfile
import types
import unicodedata
from pathlib import Path

from mkt_isolate import CannotRun, World, _reaches, build_world, run_isolated

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
# r1 Codex 1: repository paths never shipped, however declared or reached (a file, a skill dir, a link) and even
# when tracked: the author's private plans. `.git` needs no entry — git tracks nothing under it, and only a tracked
# file ships (r1 Claude M3).
PRIVATE = (".claude/plans",)
# How many links one declared path may walk through before it is called a loop (Linux's own limit is 40).
MAX_LINKS = 40


@dataclasses.dataclass(frozen=True)
class PackageSpec:
    name: str
    version: str
    skills: list[str]
    files: list[str]


def plan(spec: PackageSpec, repo: Path) -> list[tuple[Path, str]]:
    """Every (source file, path under the plugin root) `spec` ships, links resolved. Writes nothing.
    A source is decided by the OBJECT the filesystem resolves it to (`_real`), a destination by `_dest_key`."""
    top = Path(repo).resolve()
    names = _tracked(top)
    tracked = _Tracked(_tracked_objects(top, names), names)
    private = _roots(top, PRIVATE, "the author's private files are never shipped")
    home = _roots(top, (SKILLS_HOME,), "declare its skill directory in `skills`, which is what lands it at "
                                       "skills/<name>")
    claims: dict[str, tuple[str, bool, Path] | None] = {_dest_key(META): None}     # staging writes the plugin's own
    out: list[tuple[Path, str]] = []

    def add(src: Path, dest: str) -> None:
        _claim(claims, dest, src, spec.name)
        out.append((src, dest))

    for s in spec.skills:
        rel = _declared(s)
        real, st = _real(top, rel, tracked, private)
        if not stat.S_ISDIR(st.st_mode):
            raise CannotRun(f"{rel} is not a directory: a skill is declared by its directory")
        found = _tree(real, rel, top, frozenset(), tracked, private)
        if not found:
            raise CannotRun(f"{rel} holds no files: an empty skill directory is not a skill")
        for src, sub in found:
            add(src, f"skills/{Path(rel).name}/{sub}")
    for f in spec.files:
        rel = _declared(f)
        real, st = _real(top, rel, tracked, {**private, **home})
        if not stat.S_ISREG(st.st_mode):
            raise CannotRun(f"{rel} is not a regular file: `files` takes files (a skill directory goes in `skills`)")
        add(real, rel)
    if not out:
        raise CannotRun(f"package {spec.name} declares no files: an empty package cannot be staged")
    return out


def _declared(path: str) -> str:
    """A declared path, normalised (`./` dropped). Refused unless repo-relative with no `..`."""
    parts = Path(path).parts
    if not parts or Path(path).is_absolute() or ".." in parts:
        raise CannotRun(f"declared path {path!r} is not a repo-relative path (no absolute path, no `..`, not empty)")
    return "/".join(parts)


def _dest_key(text: str) -> str:
    """The ONE text fold in staging: a destination as a case-insensitive, canonically-normalising filesystem
    (macOS's default) names it, so two destinations with one key are one file where the package is installed.
    Canonical (NFD, casefold, NFC), never compatibility (NFKC): `x²` and `x2` are two names there (r3 F2)."""
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", text).casefold())


def _claim(claims: dict, dest: str, src: Path, package: str) -> None:
    """Claim EVERY prefix of `dest` under `_dest_key`. Refused when a key is held under another spelling (one
    directory on a case-insensitive target), when either holder is a file (a file where a directory must be, or a
    second copy), or when the key is the plugin's metadata directory (pre-claimed, held by None)."""
    parts = dest.split("/")
    for i in range(1, len(parts) + 1):
        here, leaf = "/".join(parts[:i]), i == len(parts)
        key = _dest_key(here)
        if key not in claims:
            claims[key] = (here, leaf, src)
            continue
        held = claims[key]
        if held is None:
            raise CannotRun(f"{dest} would land in the plugin's own {META}, which staging writes")
        if held[0] != here or held[1] or leaf:
            spelled = f" (spelled {held[0]} and {here}: one name where the package is installed)" \
                if held[0] != here else ""
            raise CannotRun(f"two declarations land on {here} in package {package}: {held[2]} and {src}{spelled}")


@dataclasses.dataclass(frozen=True)
class _Tracked:
    objects: dict          # (st_dev, st_ino) -> the NFC spellings git tracks that object under
    names: frozenset       # every tracked name, as `_tracked` returns it


def _ident(st: os.stat_result) -> tuple[int, int]:
    return st.st_dev, st.st_ino


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _tracked(top: Path) -> frozenset[str]:
    """Every path git tracks in `top` (repo-relative, posix). Asked of a git started with no config but the
    repository's own and no inherited GIT_* variable, so a caller's env cannot point it at another index. A
    repository git cannot list is CANNOT RUN: what is tracked cannot then be told. Names are decoded as the
    filesystem's (`os.fsdecode`), so a tracked name that is not UTF-8 is a name like any other (r2 Codex 3)."""
    env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": os.environ.get("HOME", "/"), "LANG": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    try:
        p = subprocess.run(["git", "-C", str(top), "ls-files", "-z", "--cached"], env=env, capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CannotRun(f"{top}: git cannot list what is tracked ({type(e).__name__}: {e})") from None
    if p.returncode != 0:
        raise CannotRun(f"{top} is not a git checkout git can list (rc {p.returncode}: "
                        f"{p.stderr.decode(errors='replace').strip()}): staging ships tracked files only")
    return frozenset(os.fsdecode(x) for x in p.stdout.split(b"\0") if x)


def _tracked_objects(top: Path, names) -> dict:
    """{identity: NFC spellings} of every object git tracks, by `os.lstat` of each name. A name one of whose parent
    directories is a LINK on disk is skipped: the object there is not the one git recorded (`a/x` tracked, `a`
    since replaced by a link to `hidden`, does not make `hidden/x` tracked)."""
    linked: dict[str, bool] = {}
    objects: dict = {}
    for name in names:
        parts = name.split("/")
        parent_link = False
        for i in range(1, len(parts)):
            d = "/".join(parts[:i])
            if d not in linked:
                linked[d] = os.path.islink(top / d)
            if linked[d]:
                parent_link = True
                break
        if parent_link:
            continue
        try:
            st = os.lstat(top / name)
        except (OSError, ValueError):
            continue
        objects.setdefault(_ident(st), set()).add(_nfc(name))
    return objects


def _roots(top: Path, paths, why: str) -> dict:
    """{identity: (declared name, why)} of each path, links FOLLOWED (`os.stat`): the place itself, whatever it is
    reached through. An absent root protects nothing because nothing is there; any other error is CANNOT RUN.
    A root that IS the repository, or a directory HOLDING it (`.claude/plans -> ..`, `-> ../..`), is CANNOT RUN
    (r4 Codex 1): every file here would be under it, and no declaration's walk ever steps on a directory above
    the one it starts from, so the rule is refused whole rather than left to the walk."""
    roots = {}
    holding = {_ident(os.stat(d)): d for d in (top, *top.parents)}
    for p in paths:
        try:
            st = os.stat(top / p)
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError as e:
            raise CannotRun(f"cannot tell what {p} is in {top} ({type(e).__name__}: {e})") from None
        if _ident(st) in holding:
            raise CannotRun(f"{p} is the repository {top} itself, or a directory holding it ({holding[_ident(st)]}): "
                            f"every file in the repository would then be under {p}, so nothing here can be staged")
        roots[_ident(st)] = (p, why)
    return roots


def _tracked_as(rel: str, inner: str, st: os.stat_result, tracked: _Tracked) -> None:
    """The object at link-free `inner` is one git tracks, under that spelling up to NFC (r3 F3; case EXACT, so one
    manifest gives one answer on a case-insensitive Mac and on case-sensitive Linux)."""
    spelled = tracked.objects.get(_ident(st))
    if not spelled:
        raise CannotRun(f"{rel} is not tracked by git ({inner}): staging ships tracked files only, never an "
                        f"untracked or ignored one")
    if _nfc(inner) not in spelled:
        raise CannotRun(f"{rel} is spelled otherwise than git tracks it: git tracks {', '.join(sorted(spelled))}; a "
                        f"declaration is spelled exactly as git tracks it, case included ({inner})")


def _real(top: Path, rel: str, tracked: _Tracked, forbidden: dict) -> tuple[Path, os.stat_result]:
    """(link-free path, `lstat`) of declared `rel`, WALKED from the root one component at a time, never resolved in
    one step (r2 Codex 2), each component `lstat`ed. A link must be tracked, with a RELATIVE target, and is replaced
    by its target's components; `..` pops, past the root is refused; more than MAX_LINKS links is a loop. The
    object the walk STANDS on is refused when its IDENTITY is in `forbidden` (a private root, or the skills home
    for `files`), however it was spelled or reached (Phase 6), and that is asked every time the walk stands
    anywhere: on the root it STARTS from, on each object stepped onto, on the directory a `..` or a link's target
    returns it to, and on the object it ends on (r4 Codex 1: the starting root was never asked). A forbidden
    identity makes everything below it forbidden, because nothing below is reached except by standing on it.
    A regular file at the end must be tracked and have exactly one name."""
    pending, cur, hops, st = list(Path(rel).parts), [], 0, os.lstat(top)
    while True:
        if _ident(st) in forbidden:
            root, why = forbidden[_ident(st)]
            raise CannotRun(f"{rel} is under {root} ({'/'.join(cur) or os.curdir}): {why}")
        if not pending:
            break
        name = pending.pop(0)
        if name == os.curdir:
            continue
        if name == os.pardir:
            if not cur:
                raise CannotRun(f"{rel} resolves to {top.parent}, outside the repository {top}: staging it would "
                                f"ship a file the repository does not hold")
            cur.pop()
            st = os.lstat(top.joinpath(*cur))
            continue
        cur.append(name)
        inner = "/".join(cur)
        try:
            st = os.lstat(top / inner)
        except (FileNotFoundError, NotADirectoryError):
            if hops:
                raise CannotRun(f"{rel} is a dangling or looping link") from None
            hint = sorted(n for n in tracked.names if _dest_key(n) == _dest_key(rel))
            raise CannotRun(f"{rel} does not exist in {top}" + (f"; git tracks {', '.join(hint)}: a declaration is "
                            f"spelled exactly as git tracks it, case included" if hint else "")) from None
        if stat.S_ISLNK(st.st_mode):
            _tracked_as(rel, inner, st, tracked)
            hops += 1
            if hops > MAX_LINKS:
                raise CannotRun(f"{rel} is a dangling or looping link")
            target = os.readlink(top / inner)
            if os.path.isabs(target):
                raise CannotRun(f"{rel} links to an absolute path ({inner} -> {target}): a checkout anywhere else "
                                f"would not hold it, so staging refuses it wherever it points")
            cur.pop()
            st = os.lstat(top.joinpath(*cur))      # a target of `.` or `` names the directory holding the link
            pending = list(Path(target).parts) + pending
    if stat.S_ISREG(st.st_mode):
        inner = "/".join(cur)
        _tracked_as(rel, inner, st, tracked)
        if st.st_nlink > 1:
            raise CannotRun(f"{rel} is a file with {st.st_nlink} names (hard links): another name may sit in a place "
                            f"never shipped, so a file with more than one name is refused ({inner})")
    return top.joinpath(*cur), st


def _tree(real: Path, rel: str, top: Path, above: frozenset, tracked: _Tracked, forbidden: dict
          ) -> list[tuple[Path, str]]:
    """Every file below directory `real` as (link-free source, path relative to it), each entry walked by `_real`
    from its declared spelling. `above` holds the IDENTITIES of the directories on the way down: meeting one again
    is a link cycle."""
    out, here = [], above | {_ident(os.stat(real))}
    for name in sorted(os.listdir(real)):
        child, st = _real(top, f"{rel}/{name}", tracked, forbidden)
        if stat.S_ISDIR(st.st_mode):
            if _ident(st) in here:
                raise CannotRun(f"{rel}/{name} links back to a directory above it: a link cycle")
            out += [(src, f"{name}/{sub}") for src, sub in _tree(child, f"{rel}/{name}", top, here, tracked,
                                                                   forbidden)]
        elif stat.S_ISREG(st.st_mode):
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
    if _reaches(out, top):
        raise CannotRun(f"{out} is inside the repository {top} (the filesystem's answer, not a compare of "
                        f"spellings): a marketplace is staged outside it")
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


# ---- the shipping-set declaration (marketplace-inventory plan, Task 6) ------------------------------------------
# Where the declaration's ci-layer entry says it came from: a reusable workflow has no installed tree (spec §2c; C4
# for it stays argued), so its files are listed from the map, never from an install.
WORKFLOW_FROM = "components.json (no installed tree: spec §2c, C4 argued)"
DECLARE_VERSION = "0.1.0"
# The commands the declaring world is built with (the spike's three, docs/marketplace/spike-record.md).
DECLARE_ALLOW = ("python3", "git", "claude")


def _inside_path(path: str, top: Path) -> bool:
    """`path` (already resolved) is `top` (resolved) or below it, by path components."""
    top_s = os.path.realpath(top)
    return path == top_s or path.startswith(top_s.rstrip(os.sep) + os.sep)


def _installed_path(f: str) -> str:
    """Where a component path lands under the plugin root: below the skills home at `skills/<rest>` (`stage` puts a
    skill directory at skills/<its last name>), anything else at its repository path."""
    home = SKILLS_HOME + "/"
    return "skills/" + f[len(home):] if f.startswith(home) else f


def _package(m, package: str) -> str:
    if package not in m.packages:
        raise CannotRun(f"package {package!r} is not in the map's packages ({', '.join(sorted(m.packages))})")
    return m.packages[package].get("channel")


def _carried(m, package: str) -> list[dict]:
    """The components `package` carries: its own and every library `shared_with` it."""
    return [c for c in m.components if c["package"] == package or package in c.get("shared_with", [])]


def installed_files(installed: Path) -> dict[str, str]:
    """{installed-relative path: installed-relative path it resolves to} for every file under `installed`, read by
    listing `installed` and nothing else. A link is followed to its target, which must be a file inside the tree;
    one that leaves it, or dangles, is CANNOT RUN (a declaration never names a file the install did not hold)."""
    top = os.path.realpath(installed)
    if not os.path.isdir(top):
        raise CannotRun(f"{installed} is not a directory: nothing is installed there")
    out: dict[str, str] = {}

    def unlisted(e: OSError):
        # os.walk skips a directory it cannot list unless told otherwise: the declaration would then be whole in
        # form and missing everything under it (review r1 XM7).
        raise CannotRun(f"cannot list {e.filename}: {e.strerror}")
    for d, dirs, files in os.walk(top, onerror=unlisted):
        for name in sorted(files) + sorted(x for x in dirs if os.path.islink(os.path.join(d, x))):
            p = os.path.join(d, name)
            rel = os.path.relpath(p, top).replace(os.sep, "/")
            real = os.path.realpath(p)
            if os.path.islink(p) and (not _inside_path(real, top) or not os.path.isfile(real)):
                raise CannotRun(f"{rel} is a link to {os.readlink(p)}, which is not a file inside the installed "
                                f"tree {installed}")
            out[rel] = os.path.relpath(real, top).replace(os.sep, "/")
    return out


def declare(installed: Path, m, package: str) -> dict:
    """The declaration of plugin `package` installed at `installed`: every file the install holds (links recorded by
    their resolved path) and, per component it carries, the installed files under that component's installed path,
    with a count. Walks `installed` only: never the repository, never the publishability scan's output (spec §7
    item 2). A component with no installed file is CANNOT RUN, never an empty entry."""
    channel = _package(m, package)
    if channel != "plugin":
        raise CannotRun(f"package {package!r} has channel {channel}: only a plugin package is installed and "
                        f"declared from its installed tree")
    files = installed_files(installed)
    comps: dict[str, dict] = {}
    for c in sorted(_carried(m, package), key=lambda c: c["id"]):
        wanted = [_installed_path(f) for f in c["files"]]
        got = {real for path, real in files.items()
               if any(path.startswith(w) if w.endswith("/") else path == w for w in wanted)}
        if not got:
            raise CannotRun(f"component {c['id']!r}: none of {c['files']} is in the installed tree (looked for "
                            f"{wanted})")
        comps[c["id"]] = {"files": sorted(got), "expected_count": len(got)}
    return {"channel": "plugin", "installed_files": sorted(set(files.values())), "components": comps}


def _expand(c: dict, names: frozenset) -> list[str]:
    """A component's files, a trailing-`/` entry expanded to the tracked files under it."""
    out: set[str] = set()
    for f in c["files"]:
        out |= {n for n in names if n.startswith(f)} if f.endswith("/") else {f}
    return sorted(out)


def spec_from_map(m, package: str, version: str, repo: Path = REPO) -> PackageSpec:
    """The PackageSpec that stages plugin `package` from the map: a file below the skills home names its skill
    directory (`.agents/skills/<d>`, once), a directory entry its tracked files, any other file itself."""
    names = _tracked(Path(repo).resolve())
    skills: set[str] = set()
    files: set[str] = set()
    for c in _carried(m, package):
        for f in _expand(c, names):
            if f.startswith(SKILLS_HOME + "/"):
                skills.add(f"{SKILLS_HOME}/{f[len(SKILLS_HOME) + 1:].split('/')[0]}")
            else:
                files.add(f)
    return PackageSpec(package, version, sorted(skills), sorted(files))


def workflow_entry(m, package: str, repo: Path = REPO) -> dict:
    """The declaration of a reusable-workflow package: its components' files from the map (a directory expanded to
    its tracked files, a link recorded by its resolved repository path), with counts, and NO installed_files —
    nothing is installed (spec §2c)."""
    channel = _package(m, package)
    if channel != "reusable-workflow":
        raise CannotRun(f"package {package!r} has channel {channel}: it is declared from its installed tree, not "
                        f"from the map")
    top = Path(repo).resolve()
    names = _tracked(top)
    comps = {}
    for c in sorted(_carried(m, package), key=lambda c: c["id"]):
        got = {os.path.relpath(os.path.realpath(top / f), top).replace(os.sep, "/") for f in _expand(c, names)}
        comps[c["id"]] = {"files": sorted(got), "expected_count": len(got)}
    return {"channel": "reusable-workflow", "declared_from": WORKFLOW_FROM, "components": comps}


def _load_map(path: Path, repo: Path):
    """The map, through check-shipping-sets.py's own `load_map` (one rule, one place). Its refusals are CANNOT RUN
    here: a declaration is never derived from a map that breaks a rule."""
    import importlib.util
    name = "mkt_stage_check_shipping_sets"
    mod = sys.modules.get(name)
    if mod is None:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "check-shipping-sets.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod             # its dataclass resolves its module by name
        spec.loader.exec_module(mod)
    try:
        return mod.load_map(path, repo)
    except mod.CannotRun as e:
        raise CannotRun(str(e)) from None
    except mod.Refused as e:
        raise CannotRun(f"the map is refused: {e}") from None


def declare_all(map_path: Path, repo: Path = REPO, work: Path | None = None, which=shutil.which, run=run_isolated,
                allow=DECLARE_ALLOW) -> dict:
    """The whole declaration: each `plugin` package staged from the map, installed in ONE fresh stranger world and
    declared from its installed tree; each `reusable-workflow` package declared from the map."""
    m = _load_map(Path(map_path), repo)
    if which("claude") is None:
        raise CannotRun("claude missing: --declare installs each plugin package with it")
    plugins = sorted(p for p, v in m.packages.items() if v.get("channel") == "plugin")
    work = Path(tempfile.mkdtemp(prefix="mkt-declare-")) if work is None else Path(work)
    mkt = stage([spec_from_map(m, p, DECLARE_VERSION, repo) for p in plugins], work / "mkt", repo=repo)
    world = build_world(work / "world", list(allow))
    out = {p: declare(install(world, mkt, p, run=run), m, p) for p in plugins}
    out.update({p: workflow_entry(m, p, repo) for p, v in m.packages.items() if v.get("channel") != "plugin"})
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0:
        raise CannotRun(f"git cannot name HEAD in {repo}: {head.stderr.strip()}")
    return {"measured_at": head.stdout.strip(), "packages": dict(sorted(out.items()))}


DECLARE_USAGE = "usage: mkt_stage.py --declare MAP OUT_JSON"


def declare_main(argv: list[str], repo: Path = REPO, **kw) -> int:
    """`--declare MAP OUT_JSON`: write the declaration; CANNOT RUN (rc 2) writes nothing."""
    if len(argv) != 2:
        print(DECLARE_USAGE, file=sys.stderr)
        return 2
    try:
        data = declare_all(Path(argv[0]), repo, **kw)
    except CannotRun as e:
        print(f"CANNOT RUN: {e}", file=sys.stderr)
        return 2
    _write_json(Path(argv[1]), data)
    print(argv[1])
    return 0


USAGE = ("usage: mkt_stage.py --out DIR --package NAME --version V [--skill PATH]... [--file PATH]... "
         "[--marketplace NAME]\n       mkt_stage.py --self-test")


def main(argv=None, repo: Path = REPO) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    if argv[:1] == ["--declare"]:
        return declare_main(argv[1:], repo)
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
                     opts.marketplace, repo)
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
    ok = fail = live_fail = fs_fail = 0

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
        git(r, "init", "-q", "--template=")      # no sample hooks: an init is most of a case's time
        git(r, "add", "-A")
        return r

    def git(r, *args, stdin=None):
        return subprocess.run(["git", "-C", str(r), *args], check=True, capture_output=True, input=stdin).stdout

    def track_as(r, path, data=b"spelled\n", write=True):
        """Track `path` under EXACTLY that spelling, and (when `write`) put `data` there. `git add` on a
        case-insensitive filesystem may record another spelling of a name that already exists; this cannot."""
        if write:
            put(r / path, data)
        blob = git(r, "hash-object", "-w", "--stdin", stdin=data).decode().strip()
        git(r, "update-index", "--index-info", stdin=f"100644 {blob}\t".encode() + os.fsencode(path) + b"\n")

    def spec(skills=(), files=(), name="pkg", version="0.0.1"):
        return PackageSpec(name, version, list(skills), list(files))

    def staged(r, skills=(), files=(), name="pkg", version="0.0.1", track=True):
        """Stage one package from fixture repo `r`; return its plugin root. `track` first adds everything git
        does not ignore, as a case that built files on top of `repo()` means them to be part of it."""
        if track:
            git(r, "add", "-A")
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

    # A case whose answer is the FILESYSTEM's (a case alias, an NFD name) is tallied apart, like the live case, so
    # the declared count is the same on a case-insensitive volume (macOS) and a case-sensitive one (Linux CI). It
    # prints `FS ok` or `[FAIL]` where it runs, `NOT RUN: <why>` where it cannot, and a failure still exits 1.
    def caseless():
        d = tmp()
        (d / "ci-probe").mkdir()
        return (d / "CI-PROBE").is_dir()
    CASELESS = caseless()

    def fs_case(name, got_fn, want, needs=None):
        """`needs` is None (run where the volume is case-insensitive) or a precondition returning a reason it
        does not hold (NOT RUN), else None."""
        nonlocal fs_fail
        why = needs() if needs else (None if CASELESS else "the volume is case-sensitive")
        if why:
            print(f"NOT RUN: {why} — `{name}` was not run and is not counted")
            return
        try:
            got = got_fn()
        except Exception as e:
            got = f"RAISED {type(e).__name__}: {e}"
        if got == want:
            print(f"FS ok: `{name}`; not in the count below")
        else:
            fs_fail += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

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

    def absolute(where):
        r = repo()
        if where == "outside":
            (r / "scripts/abs.md").symlink_to(r.parent / "outside/secret.md")
            return refused(lambda: staged(r, files=["scripts/abs.md"]), "scripts/abs.md links to an absolute path")
        (r / "scripts/abs.py").symlink_to(r / "scripts/lib/y.py")
        return refused(lambda: staged(r, files=["scripts/abs.py"]), "scripts/abs.py links to an absolute path")
    case("a link with an ABSOLUTE target outside the repository is CANNOT RUN", lambda: absolute("outside"), True)
    # Phase 6 red case 7: an absolute target is refused wherever it points (a checkout elsewhere breaks it).
    case("a link with an absolute target spelled below the repository root is CANNOT RUN too",
         lambda: absolute("inside"), True)

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

    # --- what ships: tracked files only, never the author's private ones (r1 Claude M3, Codex 1) -------------
    def untracked_in_skill():
        r = repo()
        put(r / ".agents/skills/brief/.DS_Store", b"finder\n")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"], track=False),
                       ".agents/skills/brief/.DS_Store is not tracked by git")
    case("an untracked file inside a declared skill is CANNOT RUN, naming it — never shipped, never skipped",
         untracked_in_skill, True)

    def ignored_file():
        r = repo()
        put(r / ".gitignore", b".env.local\n")
        put(r / ".env.local", b"SECRET=1\n")
        return refused(lambda: staged(r, files=[".env.local"]), ".env.local is not tracked by git")
    case("a gitignored file declared in files is CANNOT RUN, naming it", ignored_file, True)

    def untracked_link():
        r = repo()
        (r / "scripts/alias.py").symlink_to("x.py")
        return refused(lambda: staged(r, files=["scripts/alias.py"], track=False),
                       "scripts/alias.py is not tracked by git")
    case("an untracked LINK to a tracked file is CANNOT RUN: the link itself is what is declared",
         untracked_link, True)
    case("adjacent: a tracked link to a tracked file stages",
         lambda: (lambda r: ((r / "scripts/alias.py").symlink_to("x.py"),
                             (staged(r, files=["scripts/alias.py"]) / "scripts/alias.py").read_bytes())[1])(repo()),
         X_BYTES)

    def not_git():
        r = repo()
        shutil.rmtree(r / ".git")
        return refused(lambda: staged(r, files=["scripts/x.py"], track=False), f"{r} is not a git checkout")
    case("a repository git cannot list is CANNOT RUN (what is tracked cannot be told)", not_git, True)

    def private(kind):
        r = repo()
        put(r / ".claude/plans/p.md", b"the author's plan\n")
        git(r, "add", "-f", ".claude/plans/p.md")          # tracked, so only the private-path guard can refuse it
        if kind == "file":
            return refused(lambda: staged(r, files=[".claude/plans/p.md"]), ".claude/plans/p.md is under .claude/plans")
        if kind == "skill":
            return refused(lambda: staged(r, skills=[".claude/plans"]), ".claude/plans is under .claude/plans")
        (r / ".agents/skills/brief/plan.md").symlink_to("../../../.claude/plans/p.md")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"]),
                       ".agents/skills/brief/plan.md is under .claude/plans")
    case("a TRACKED file under .claude/plans declared in files is CANNOT RUN", lambda: private("file"), True)
    case("...declared as a skill directory", lambda: private("skill"), True)
    case("...reached through a link inside a skill", lambda: private("link"), True)

    # r2 Codex 1: a CASE ALIAS of a private path. On a case-insensitive filesystem `.CLAUDE/PLANS` IS `.claude/plans`;
    # on a case-sensitive one it is another directory, which is why these are filesystem cases (tallied apart).
    def private_alias(kind):
        r = repo()
        git(r, "add", "-A")
        track_as(r, ".CLAUDE/PLANS/secret.md", b"PRIVATE FIXTURE\n")
        if kind == "file":
            return refused(lambda: staged(r, files=[".CLAUDE/PLANS/secret.md"], track=False),
                           ".CLAUDE/PLANS/secret.md is under .claude/plans")
        if kind == "skill":
            return refused(lambda: staged(r, skills=[".CLAUDE/PLANS"], track=False),
                           ".CLAUDE/PLANS is under .claude/plans")
        (r / ".agents/skills/brief/plan.md").symlink_to("../../../.Claude/Plans/secret.md")
        git(r, "add", ".agents/skills/brief/plan.md")
        if not (r / ".Claude/Plans/secret.md").exists():      # a case-sensitive filesystem: the alias is its own file
            track_as(r, ".Claude/Plans/secret.md", b"PRIVATE FIXTURE\n")
        return refused(lambda: staged(r, skills=[".agents/skills/brief"], track=False),
                       ".agents/skills/brief/plan.md is under .claude/plans")
    fs_case("a tracked file under a CASE ALIAS of .claude/plans (.CLAUDE/PLANS) declared in files is CANNOT RUN",
            lambda: private_alias("file"), True)
    fs_case("...the case alias declared as a skill directory", lambda: private_alias("skill"), True)
    fs_case("...the case alias reached through a link inside a skill", lambda: private_alias("link"), True)
    case("adjacent: a tracked file under .claude/plans-kept (the private name is a whole component) stages",
         lambda: (lambda r: (put(r / ".claude/plans-kept/ok.md", b"kept\n"),
                             (staged(r, files=[".claude/plans-kept/ok.md"]) / ".claude/plans-kept/ok.md").read_bytes()
                             )[1])(repo()), b"kept\n")

    # r2 Codex 2: a link in a declared path's PARENTS. Every link walked must be tracked, wherever it sits.
    def parent_link(how):
        r = repo()
        put(r / "target/data.md", b"data\n")
        git(r, "add", "-A")
        (r / "alias").symlink_to("target")
        if how == "ignored":
            put(r / ".gitignore", b"alias\n")
            git(r, "add", "-A")
        if how == "tracked":
            git(r, "add", "-A")
            return (staged(r, files=["alias/data.md"], track=False) / "alias/data.md").read_bytes()
        return refused(lambda: staged(r, files=["alias/data.md"], track=False),
                       "alias/data.md is not tracked by git (alias)")
    case("an UNTRACKED directory link in a declared file's parents is CANNOT RUN, naming the link",
         lambda: parent_link("untracked"), True)
    case("...and so is a GITIGNORED one", lambda: parent_link("ignored"), True)
    case("adjacent: a TRACKED directory link in a declared file's parents stages the file it reaches",
         lambda: parent_link("tracked"), b"data\n")

    def link_chain():
        # tracked link -> UNTRACKED link -> tracked file: the middle link is one a fresh checkout does not have.
        r = repo()
        (r / "scripts/first.py").symlink_to("second.py")
        git(r, "add", "-A")
        (r / "scripts/second.py").symlink_to("x.py")
        return refused(lambda: staged(r, files=["scripts/first.py"], track=False),
                       "scripts/first.py is not tracked by git (scripts/second.py)")
    case("a tracked link that reaches its file through an UNTRACKED link is CANNOT RUN, naming the middle link",
         link_chain, True)

    def link_through_private():
        # A link whose target only PASSES THROUGH the private directory and comes back out.
        r = repo()
        put(r / ".claude/plans/p.md", b"the author's plan\n")
        (r / "scripts/round.py").symlink_to("../.claude/plans/../../scripts/x.py")
        return refused(lambda: staged(r, files=["scripts/round.py"]), "scripts/round.py is under .claude/plans")
    case("a link whose target passes THROUGH .claude/plans and back out is CANNOT RUN", link_through_private, True)

    def link_loop():
        r = repo()
        (r / "scripts/a.py").symlink_to("b.py")
        (r / "scripts/b.py").symlink_to("a.py")
        return refused(lambda: staged(r, files=["scripts/a.py"]), "scripts/a.py is a dangling or looping link")
    case("two links naming each other are CANNOT RUN (a loop), never an endless walk", link_loop, True)

    # r2 Codex 3: a tracked name that is not UTF-8 belongs to git's index, not to this package.
    def odd_index_name():
        r = repo()
        git(r, "add", "-A")
        track_as(r, os.fsdecode(b"scripts/bad-\xff.py"), write=False)
        return (staged(r, files=["scripts/x.py"], track=False) / "scripts/x.py").read_bytes()
    case("an unrelated tracked name that is not UTF-8 does not stop staging a declared file",
         odd_index_name, X_BYTES)

    # The same class in the other exclusions: each compares IDENTITY, so a case alias is not a way round.
    def skills_home_alias():
        r = repo()
        git(r, "add", "-A")
        track_as(r, ".AGENTS/SKILLS/extra/note.md")
        return refused(lambda: staged(r, files=[".AGENTS/SKILLS/extra/note.md"], track=False),
                       ".AGENTS/SKILLS/extra/note.md is under .agents/skills")
    fs_case("a file under a case alias of .agents/skills declared in files is CANNOT RUN", skills_home_alias, True)

    def meta_alias():
        r = repo()
        git(r, "add", "-A")
        track_as(r, ".CLAUDE-PLUGIN/plugin.json", b"{}\n")
        return refused(lambda: staged(r, files=[".CLAUDE-PLUGIN/plugin.json"], track=False),
                       ".CLAUDE-PLUGIN/plugin.json would land in the plugin's own .claude-plugin")
    case("a declared file landing in a case alias of the plugin's .claude-plugin is CANNOT RUN", meta_alias, True)

    def dest_alias():
        r = repo()
        git(r, "add", "-A")
        track_as(r, "scripts/X.py", X_BYTES)
        return refused(lambda: staged(r, files=["scripts/x.py", "scripts/X.py"], track=False),
                       "two declarations land on scripts/X.py")
    case("two declarations whose destinations differ only in case are CANNOT RUN (one would overwrite the other)",
         dest_alias, True)

    # --- Phase 6 (architecture-review-2026-11-15): a source path is decided by the OBJECT the filesystem resolves it
    # to, never by its spelling; a destination by one key (`_dest_key`) over every prefix. Red cases 1-11. ------------
    def refused_stage(r, start, skills=(), files=()):
        """(`stage` is CANNOT RUN with a message starting `start`, its out directory exists afterwards)."""
        out = tmp() / "out"
        return refused(lambda: stage([spec(skills, files)], out, repo=r), start), out.exists()

    def claude_is_a_link():
        # Red case 1 (F1): `.claude` a TRACKED link to `dot`. The private directory's own name there is dot/plans.
        r = repo()
        shutil.rmtree(r / ".claude")
        put(r / "dot/plans/secret", b"PRIVATE FIXTURE\n")
        (r / ".claude").symlink_to("dot")
        git(r, "add", "-A")
        return [refused_stage(r, ".claude/plans/secret is under .claude/plans", files=[".claude/plans/secret"]),
                refused_stage(r, ".claude/plans is under .claude/plans", skills=[".claude/plans"]),
                refused_stage(r, "dot/plans/secret is under .claude/plans", files=["dot/plans/secret"])]
    case("a TRACKED link .claude -> dot: .claude/plans/secret, skill .claude/plans and dot/plans/secret are each "
         "CANNOT RUN, and nothing is written", claude_is_a_link, [(True, False)] * 3)

    def plans_is_a_link():
        # Red case 2: the private root ITSELF a tracked link, `.claude/plans -> ../dot`. What it reaches is private.
        r = repo()
        put(r / "dot/secret", b"PRIVATE FIXTURE\n")
        put(r / "dot/SKILL.md", b"a skill\n")
        (r / ".claude/plans").symlink_to("../dot")
        git(r, "add", "-A")
        return [refused_stage(r, "dot/secret is under .claude/plans", files=["dot/secret"]),
                refused_stage(r, "dot is under .claude/plans", skills=["dot"])]
    case("a TRACKED link .claude/plans -> ../dot: dot/secret and skill dot are CANNOT RUN, nothing written",
         plans_is_a_link, [(True, False)] * 2)

    # --- r4 Codex 1 (BLOCKER): a private root that IS the repository, or a directory holding it. Every file here is
    # then under it, and the walk never stepped on the root it starts from. --------------------------------------
    def root_repo(link, target):
        """`repo()` plus a tracked `secret`, a tracked `alias -> .`, and a tracked link `link -> target`."""
        r = repo()
        put(r / "secret", b"PRIVATE FIXTURE\n")
        (r / "alias").symlink_to(".")
        if (r / link).is_dir():
            shutil.rmtree(r / link)
        (r / link).symlink_to(target)
        git(r, "add", "-A")
        return r

    def plans_is_the_repo():
        r = root_repo(".claude/plans", "..")
        return [refused_stage(r, ".claude/plans is the repository", files=[f]) for f in
                (".claude/plans/secret", "secret", "alias/secret")]
    case("a TRACKED link .claude/plans -> .. (the repository itself): .claude/plans/secret, secret and alias/secret "
         "are each CANNOT RUN naming the root, nothing written", plans_is_the_repo, [(True, False)] * 3)
    case("...and .claude/plans -> ../.. (a directory HOLDING the repository): secret is CANNOT RUN, nothing written",
         lambda: refused_stage(root_repo(".claude/plans", "../.."), ".claude/plans is the repository",
                               files=["secret"]), (True, False))
    case("...and the skills home .agents/skills -> .. (the repository itself): a declared file is CANNOT RUN",
         lambda: refused_stage(root_repo(".agents/skills", ".."), ".agents/skills is the repository",
                               files=["scripts/x.py"]), (True, False))

    def walk_starts_forbidden():
        # `_real` on its own, the root's identity forbidden by hand (independent of `_roots`): the object the walk
        # STARTS on, returns to by `..`, or stands on after a link to `.`, is checked like any object stepped on.
        r = root_repo(".claude/plans", "..")
        names = _tracked(r)
        tracked = _Tracked(_tracked_objects(r, names), names)
        root = {_ident(os.stat(r)): ("ROOT", "why")}
        rels = ("secret", "alias/secret", "scripts/../secret", ".claude/plans/secret")
        return ([refused(lambda rel=rel: _real(r, rel, tracked, root), f"{rel} is under ROOT (.)") for rel in rels],
                [_real(r, rel, tracked, {})[0] == r / "secret" for rel in rels])   # the control: nothing forbidden
    case("_real refuses the root it STARTS on when that identity is forbidden: secret, alias/secret (alias -> .), "
         "scripts/../secret and .claude/plans/secret (-> ..); with nothing forbidden each resolves to secret",
         walk_starts_forbidden, ([True] * 4, [True] * 4))
    case("adjacent: a private root that is an ordinary directory below the repository refuses nothing outside it "
         "(scripts/x.py stages with .claude/plans present)",
         lambda: (lambda r: (put(r / ".claude/plans/p.md", b"plan\n"),
                             (staged(r, files=["scripts/x.py"]) / "scripts/x.py").read_bytes() == X_BYTES)[1])(repo()),
         True)

    def compatibility_twins():
        # Red case 3 (F2): names a filesystem keeps DISTINCT (compatibility forms, not canonical) are two files.
        r = repo()
        got = []
        for a, b in (("x\u00b2.md", "x2.md"), ("\uff21.md", "A.md")):
            put(r / a, b"first\n")
            put(r / b, b"second\n")
            if (r / a).read_bytes() != b"first\n":
                return f"the volume holds {a!r} and {b!r} as one file: this case's premise is false here"
            p = staged(r, files=[a, b])
            got.append(((p / a).read_bytes(), (p / b).read_bytes()))
        return got
    case("x\u00b2.md + x2.md, and \uff21.md + A.md, stage as two files with their own bytes", compatibility_twins,
         [(b"first\n", b"second\n")] * 2)

    NFD = unicodedata.normalize("NFD", "caf\u00e9.md")

    def nfd_fixture():
        r = repo()
        put(r / ".agents/skills/nfd/SKILL.md", b"---\nname: nfd\ndescription: d\n---\n")
        put(r / ".agents/skills/nfd" / NFD, b"accented\n")
        git(r, "-c", "core.precomposeunicode=true", "add", "-A")
        return r

    def nfd_premise():
        r = nfd_fixture()
        index = os.fsdecode(git(r, "ls-files", "-z", ".agents/skills/nfd")).split("\0")
        listed = os.listdir(r / ".agents/skills/nfd")
        if ".agents/skills/nfd/" + unicodedata.normalize("NFC", NFD) not in index:
            return "git's index does not hold the NFC spelling here (no core.precomposeunicode)"
        if NFD not in listed:
            return "the volume does not return the NFD spelling from listdir"
        return None

    fs_case("an NFD name on disk that git's index holds as NFC (core.precomposeunicode) STAGES (red case 4, F3)",
            lambda: tree(staged(nfd_fixture(), skills=[".agents/skills/nfd"], track=False)),
            [".claude-plugin/plugin.json", "skills/nfd/SKILL.md", "skills/nfd/" + NFD], needs=nfd_premise)

    def agents_is_a_link():
        # Red case 5 (F4): `.agents` a TRACKED link to `ag`. The skills home is ag/skills under its link-free name.
        r = repo()
        os.rename(r / ".agents", r / "ag")
        (r / ".agents").symlink_to("ag")
        git(r, "add", "-A")
        return [refused(lambda: staged(r, files=[".agents/skills/b/SKILL.md"], track=False),
                        ".agents/skills/b/SKILL.md is under .agents/skills"),
                refused(lambda: staged(r, files=["ag/skills/b/SKILL.md"], track=False),
                        "ag/skills/b/SKILL.md is under .agents/skills")]
    case("a TRACKED link .agents -> ag: .agents/skills/b/SKILL.md and ag/skills/b/SKILL.md in files are CANNOT RUN",
         agents_is_a_link, [True, True])

    def hard_link():
        # Red case 6: `p/h`, a tracked second NAME of a private file. A file with more than one name is refused.
        r = repo()
        put(r / ".claude/plans/secret", b"PRIVATE FIXTURE\n")
        (r / "p").mkdir()
        os.link(r / ".claude/plans/secret", r / "p/h")
        git(r, "add", "p/h")
        return refused(lambda: staged(r, files=["p/h"], track=False), "p/h is a file with 2 names")
    case("a tracked hard link p/h to a private file is CANNOT RUN, and the refusal says it has 2 names", hard_link,
         True)

    def parent_moved(declared):
        # Red case 8: `a/x` tracked, then `a` moved to `hidden` and an UNTRACKED link `a -> hidden` left in its place.
        r = repo()
        put(r / "a/x", b"ax\n")
        git(r, "add", "-A")
        os.rename(r / "a", r / "hidden")
        (r / "a").symlink_to("hidden")
        return refused(lambda: staged(r, files=[declared], track=False), f"{declared} is not tracked by git")
    case("a tracked name whose parent became an UNTRACKED link: hidden/x and a/x are CANNOT RUN (not tracked)",
         lambda: [parent_moved("hidden/x"), parent_moved("a/x")], [True, True])

    def sweep():
        # Red case 9: `_dest_key` equality with .claude/plans against the volume's own identity, over single
        # substitutions at each of its 13 positions. A BOUNDED SAMPLE (the full BMP is ~850,000 stats, 52 s on 8
        # processes): every code point in U+0001-U+07FF, U+1E00-U+218F, U+FB00-U+FB4F and U+FF00-U+FFEF, minus `/`.
        base = tmp("mkt-sweep-")
        (base / ".claude/plans").mkdir(parents=True)
        want = os.stat(base / ".claude/plans")
        points = [c for lo, hi in ((0x1, 0x7FF), (0x1E00, 0x218F), (0xFB00, 0xFB4F), (0xFF00, 0xFFEF))
                  for c in range(lo, hi + 1) if c != 0x2F]
        key, misses, wrong = _dest_key(".claude/plans"), [], []
        for i, ch in enumerate(".claude/plans"):
            if ch == "/":
                continue
            for c in points:
                s = ".claude/plans"[:i] + chr(c) + ".claude/plans"[i + 1:]
                try:
                    same = os.path.samestat(os.stat(base / s), want)
                except (OSError, ValueError):
                    same = False
                if same and _dest_key(s) != key:
                    misses.append(s)
                if _dest_key(s) == key and not same:
                    wrong.append(s)
        return len(points) * 12, misses[:3], wrong[:3]
    fs_case("the destination key agrees with the volume's identity of .claude/plans on every sampled substitution "
            "(red case 9: 0 misses, 0 wrong refusals)", lambda: sweep()[1:], ([], []))

    def dest_prefixes():
        # Red case 10: every PREFIX of every destination is claimed under one key.
        got = []
        r = repo()
        git(r, "add", "-A")
        track_as(r, "Dir/x", b"x\n")
        track_as(r, "dir/y", b"y\n")
        got.append(refused_stage(r, "two declarations land on dir in package pkg", files=["Dir/x", "dir/y"]))
        r = repo()
        put(r / "skills", b"a file named skills\n")         # P6-N1: was an uncaught IsADirectoryError after a write
        git(r, "add", "-A")
        got.append(refused_stage(r, "two declarations land on skills in package pkg",
                                 skills=[".agents/skills/brief"], files=["skills"]))
        r = repo()
        put(r / "skills/brief", b"a file where a skill lands\n")
        git(r, "add", "-A")
        got.append(refused_stage(r, "two declarations land on skills/brief in package pkg",
                                 skills=[".agents/skills/brief"], files=["skills/brief"]))
        r = repo()
        put(r / "A.md", b"upper\n")
        put(r / "d/a.md", b"lower\n")
        p = staged(r, files=["A.md", "d/a.md"])
        got.append(((p / "A.md").read_bytes(), (p / "d/a.md").read_bytes()))
        return got
    case("destinations: Dir/x + dir/y, a file `skills` + a skill (P6-N1) and a file skills/brief + skill brief are "
         "CANNOT RUN writing nothing; A.md + d/a.md stage", dest_prefixes,
         [(True, False)] * 3 + [(b"upper\n", b"lower\n")])

    def plans_spelling():
        # Coordinator override: a declaration is spelled as git tracks it (NFC both sides), case EXACT, so one
        # manifest gives one answer on a case-insensitive Mac and on case-sensitive Linux CI.
        r = repo()
        put(r / "docs/a.md", b"a\n")
        git(r, "add", "-A")
        got = raises(lambda: staged(r, files=["DOCS/a.md"], track=False))
        return got.startswith("CANNOT RUN: DOCS/a.md "), "git tracks docs/a.md" in got
    case("DOCS/a.md declared where git tracks docs/a.md is CANNOT RUN, naming the tracked spelling (case is exact)",
         plans_spelling, (True, True))

    def foreign_git_env():
        # A caller's GIT_DIR naming another repository, which tracks the file this one does not, changes nothing.
        r, other = repo(), repo()
        for top in (r, other):
            put(top / "scripts/new.py", b"new\n")
        git(other, "add", "-A")
        old = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = str(other / ".git")
        try:
            return refused(lambda: staged(r, files=["scripts/new.py"], track=False),
                           "scripts/new.py is not tracked by git")
        finally:
            os.environ.pop("GIT_DIR") if old is None else os.environ.__setitem__("GIT_DIR", old)
    case("what is tracked is asked of the repository's own git, never one a caller's GIT_DIR names",
         foreign_git_env, True)

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

    def out_alias():
        r = repo()
        out = r.parent / r.name.upper() / "build/mkt"
        return (refused(lambda: stage([spec(files=["scripts/x.py"])], out, repo=r), f"{out} is inside the repository"),
                (r / "build").exists(), out.exists())
    fs_case("an out directory under a CASE ALIAS of the repository is CANNOT RUN too", out_alias,
            (True, False, False))

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
    def cli(args, r=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = main(args, repo=repo() if r is None else r)
            except SystemExit as e:
                rc = e.code
        return rc, out.getvalue(), err.getvalue()

    def cli_stages():
        # A fixture repository: the copy the mutation harness runs in is not a git checkout (r1 Claude M3).
        out = tmp() / "out"
        rc, o, _ = cli(["--out", str(out), "--package", "cli-pkg", "--version", "0.1.0", "--file", "scripts/x.py"])
        return (rc, o == f"{out}\n", read_marketplace(out), (out / "cli-pkg/scripts/x.py").read_bytes() == X_BYTES)
    case("CLI: stages one package and prints the marketplace root (rc 0)",
         cli_stages, (0, True, ("mkt-local", {"cli-pkg": "0.1.0"}), True))

    def cli_options():
        out = tmp() / "out"
        rc, _, _ = cli(["--out", str(out), "--package", "p2", "--version", "2.0.0", "--marketplace", "named-mkt",
                        "--skill", ".agents/skills/brief", "--file", "scripts/x.py", "--file", "scripts/lib/y.py"])
        return (rc, read_marketplace(out), (out / "p2/skills/brief/refs/deep.md").is_file(),
                (out / "p2/scripts/lib/y.py").is_file())
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
                rc = main(["--package", "p", "--version", "1", "--file", "scripts/x.py"], repo=repo())
            except SystemExit as e:
                rc = e.code
        return (rc, err.getvalue().startswith("usage:"))
    case("CLI: a missing --out is a usage error (rc 2)", no_out, (2, True))

    # --- Task 6: the shipping-set declaration, derived from the INSTALLED tree -----------------------------
    def a_map(**over):
        comps = [{"id": "brief", "package": "pkg", "roles": ["entry-point"], "files": [".agents/skills/brief/"]},
                 {"id": "contract", "package": "pkg", "roles": ["data"],
                  "files": [".agents/skills/shared/contract.md"]},
                 {"id": "x", "package": "pkg", "roles": ["entry-point"], "files": ["scripts/x.py"]},
                 {"id": "lib", "package": "pkg", "roles": ["library"], "files": ["scripts/lib/"],
                  "shared_with": ["other"]},
                 {"id": "wf", "package": "wf", "roles": ["entry-point"], "files": ["scripts/x.py"]}]
        data = {"packages": {"pkg": {"channel": "plugin"}, "other": {"channel": "plugin"},
                             "wf": {"channel": "reusable-workflow"}}, "components": comps}
        data.update(over)
        return types.SimpleNamespace(measured_at="m", exclusions=[], **data)

    def installed_tree(extra=()):
        """An installed plugin as `install` leaves it: skills at skills/<name>, files at their repo paths."""
        top = tmp("mkt-installed-") / "pkg" / "0.1.0"
        for rel in ("skills/brief/SKILL.md", "skills/brief/refs/deep.md", "skills/shared/contract.md",
                    "scripts/x.py", "scripts/lib/y.py", ".claude-plugin/plugin.json", *extra):
            put(top / rel, b"bytes\n")
        return top

    case("declare: each component's files are the installed files under its installed path (a skill at "
         "skills/<name>), with a count; installed_files is the whole tree",
         lambda: declare(installed_tree(extra=("scripts/x.py.orig",)), a_map(), "pkg"),
         {"channel": "plugin",
          "installed_files": [".claude-plugin/plugin.json", "scripts/lib/y.py", "scripts/x.py", "scripts/x.py.orig",
                              "skills/brief/SKILL.md", "skills/brief/refs/deep.md", "skills/shared/contract.md"],
          "components": {"brief": {"files": ["skills/brief/SKILL.md", "skills/brief/refs/deep.md"],
                                   "expected_count": 2},
                         "contract": {"files": ["skills/shared/contract.md"], "expected_count": 1},
                         "lib": {"files": ["scripts/lib/y.py"], "expected_count": 1},
                         "x": {"files": ["scripts/x.py"], "expected_count": 1}}})
    case("declare: a library shared_with a package is declared under that package too, and nothing else is",
         lambda: declare(installed_tree(), a_map(), "other")["components"],
         {"lib": {"files": ["scripts/lib/y.py"], "expected_count": 1}})

    def unlistable():
        """Review r1 XM7 (the reviewer's input): skills/a/ holds a readable SKILL.md and hidden/secret.md, and
        hidden/ cannot be listed. The control is the same tree with the directory readable."""
        top = tmp("mkt-unlistable-") / "pkg" / "0.1.0"
        for rel in ("skills/brief/SKILL.md", "skills/brief/hidden/secret.md", "scripts/x.py", "scripts/lib/y.py",
                    "skills/shared/contract.md"):
            put(top / rel, b"bytes\n")
        if os.geteuid() == 0:
            return "root lists every directory"
        control = "skills/brief/hidden/secret.md" in declare(top, a_map(), "pkg")["installed_files"]
        hidden = top / "skills/brief/hidden"
        hidden.chmod(0)
        try:
            return control, raises(lambda: declare(top, a_map(), "pkg")).replace(str(top), "TOP")
        finally:
            hidden.chmod(0o755)
    case("declare: a directory of the installed tree that cannot be listed is CANNOT RUN — never a declaration "
         "silently missing what is under it (review r1 XM7; the control declares the hidden file)",
         unlistable,
         "root lists every directory" if os.geteuid() == 0 else
         (True, "CANNOT RUN: cannot list TOP/skills/brief/hidden: Permission denied"))

    def audited_declare():
        """Every path declare OPENS or LISTS, against a control: the same hook does see a read outside."""
        top = installed_tree()
        (top / "skills/brief/link.md").symlink_to("../shared/contract.md")
        outside = top.parent.parent / "outside.md"
        outside.write_text("the author's\n")
        seen: list[str] = []
        recording = [False]

        def hook(event, args):
            if recording[0] and event in ("open", "os.listdir", "os.scandir") and args and \
                    isinstance(args[0], (str, bytes, os.PathLike)):
                seen.append(os.path.realpath(os.fsdecode(args[0])))
        sys.addaudithook(hook)
        recording[0] = True
        try:
            declare(top, a_map(), "pkg")
            during = [p for p in seen if not _inside_path(p, top)]
            del seen[:]
            outside.read_text()                             # the control: a read outside IS recorded
            control = [p for p in seen if not _inside_path(p, top)]
        finally:
            recording[0] = False
        return (during, control == [os.path.realpath(outside)])
    case("declare reads no file outside the installed dir (an audit hook over open/listdir/scandir; the control "
         "read outside is recorded)", audited_declare, ([], True))

    def linked():
        top = installed_tree()
        (top / "skills/brief/link.md").symlink_to("../../scripts/x.py")
        d = declare(top, a_map(), "pkg")
        return (d["components"]["brief"], "skills/brief/link.md" in d["installed_files"])
    case("a symlink in the installed tree is recorded by its resolved path",
         linked, ({"files": ["scripts/x.py", "skills/brief/SKILL.md", "skills/brief/refs/deep.md"],
                   "expected_count": 3}, False))

    def leaving():
        top = installed_tree()
        (top.parent / "elsewhere.py").write_text("x\n")
        (top / "scripts/out.py").symlink_to("../../elsewhere.py")
        return raises(lambda: declare(top, a_map(), "pkg"))
    case("a link leaving the installed tree is CANNOT RUN",
         lambda: leaving().startswith("CANNOT RUN: scripts/out.py is a link to "), True)

    def sibling():
        top = installed_tree()
        put(top.parent / (top.name + "-other") / "x.py", b"x\n")
        (top / "scripts/out.py").symlink_to(f"../../{top.name}-other/x.py")
        return raises(lambda: declare(top, a_map(), "pkg"))
    case("a link into a sibling whose name extends the installed dir's is outside it (CANNOT RUN)",
         lambda: sibling().startswith("CANNOT RUN: scripts/out.py is a link to "), True)

    def dir_link():
        top = installed_tree()
        (top / "scripts/libs").symlink_to("lib")
        return raises(lambda: declare(top, a_map(), "pkg"))
    case("a link to a directory in the installed tree is CANNOT RUN (a declaration names files)",
         lambda: dir_link().startswith("CANNOT RUN: scripts/libs is a link to lib, which is not a file inside "
                                       "the installed tree "), True)

    def dangling():
        top = installed_tree()
        (top / "scripts/gone.py").symlink_to("nowhere.py")
        return raises(lambda: declare(top, a_map(), "pkg"))
    case("a dangling link in the installed tree is CANNOT RUN",
         lambda: dangling().startswith("CANNOT RUN: scripts/gone.py is a link to "), True)

    def omitted():
        top = installed_tree()
        (top / "scripts/x.py").unlink()
        return raises(lambda: declare(top, a_map(), "pkg"))
    case("a component with no file in the installed tree is CANNOT RUN, never an empty entry",
         omitted, "CANNOT RUN: component 'x': none of ['scripts/x.py'] is in the installed tree "
                  "(looked for ['scripts/x.py'])")
    case("a reusable-workflow package is never declared from an install (CANNOT RUN)",
         lambda: raises(lambda: declare(installed_tree(), a_map(), "wf")),
         "CANNOT RUN: package 'wf' has channel reusable-workflow: only a plugin package is installed and declared "
         "from its installed tree")
    case("a package the map does not name is CANNOT RUN",
         lambda: raises(lambda: declare(installed_tree(), a_map(packages={"zz": {"channel": "plugin"}}), "nope")),
         "CANNOT RUN: package 'nope' is not in the map's packages (zz)")

    def specced():
        r = repo()
        s = spec_from_map(a_map(), "pkg", "0.1.0", r)
        return (s.name, s.version, s.skills, s.files)
    case("spec_from_map: a file under the skills home names its skill directory, once; a directory entry expands "
         "to its tracked files; a file is itself",
         specced, ("pkg", "0.1.0", [".agents/skills/brief", ".agents/skills/shared"],
                   ["scripts/lib/y.py", "scripts/x.py"]))
    case("spec_from_map: a shared_with library is carried by the package it is shared with",
         lambda: (lambda sp: (sp.version, sp.skills, sp.files))(
             spec_from_map(a_map(components=a_map().components[3:4]), "other", "2.0.0", repo())),
         ("2.0.0", [], ["scripts/lib/y.py"]))

    def ci_entry():
        r = repo()
        (r / "scripts/lib/z.py").symlink_to("../x.py")
        git(r, "add", "-A")
        return workflow_entry(a_map(), "wf", r)
    case("workflow_entry: a reusable-workflow package is declared from the map (links resolved, counts), with "
         "no installed_files",
         ci_entry, {"channel": "reusable-workflow",
                    "declared_from": "components.json (no installed tree: spec §2c, C4 argued)",
                    "components": {"wf": {"files": ["scripts/x.py"], "expected_count": 1}}})

    def ci_link():
        r = repo()
        m = a_map()
        m.components[4]["files"] = ["scripts/lib/"]
        (r / "scripts/lib/z.py").symlink_to("../x.py")
        git(r, "add", "-A")
        return workflow_entry(m, "wf", r)["components"]["wf"]
    case("workflow_entry: a tracked link is recorded by its resolved path",
         ci_link, {"files": ["scripts/lib/y.py", "scripts/x.py"], "expected_count": 2})
    case("workflow_entry: a plugin package is refused (it is declared from its install)",
         lambda: raises(lambda: workflow_entry(a_map(), "pkg", repo())),
         "CANNOT RUN: package 'pkg' has channel plugin: it is declared from its installed tree, not from the map")

    def declare_cli(*args, r=None, **kw):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = declare_main(list(args), repo=repo() if r is None else r, **kw)
        return rc, out.getvalue(), err.getvalue()

    def map_file(r, comps, packages=None):
        mp = tmp() / "map.json"
        full = [{"roles": ["entry-point"], "effort": 1, "phase": "1", **c} for c in comps]
        mp.write_text(json.dumps({"packages": packages or {"pkg": {"channel": "plugin"}}, "components": full}))
        return mp

    def stand_in(calls):
        """A stand-in for run_isolated: `marketplace add` notes the marketplace, `install` copies the staged plugin
        to where `install` reads it."""
        state = {}

        def run(world, argv, cwd, timeout):
            calls.append(argv[2])
            if argv[2] == "marketplace":
                state["mkt"] = Path(argv[4])
            else:
                plugin, mkt = argv[3].split("@")
                shutil.copytree(state["mkt"] / plugin,
                                world.home / ".claude/plugins/cache" / mkt / plugin / DECLARE_VERSION)
            return types.SimpleNamespace(rc=0, stdout="", stderr="")
        return run

    def declared_offline():
        r = repo()
        git(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "fixture")
        mp = map_file(r, [{"id": "brief", "package": "pkg", "files": [".agents/skills/brief/"]},
                          {"id": "x", "package": "pkg", "files": ["scripts/x.py"]},
                          {"id": "y", "package": "wf", "files": ["scripts/lib/y.py"]}],
                      {"pkg": {"channel": "plugin"}, "wf": {"channel": "reusable-workflow"}})
        out, calls = tmp() / "decl.json", []
        # `which` is a stand-in too: the install is, so the case must not depend on a real `claude` (CI has none —
        # PR #598, mutation shard 35's control was 117/118 there)
        rc, o, e = declare_cli(str(mp), str(out), r=r, run=stand_in(calls), allow=["python3"],
                               which=lambda name: f"/stand-in/{name}")
        d = json.loads(out.read_text())
        head = git(r, "rev-parse", "--short", "HEAD").decode().strip()
        return (rc, o == f"{out}\n", e, d["measured_at"] == head, calls, sorted(d["packages"]),
                d["packages"]["pkg"]["components"]["brief"]["expected_count"], d["packages"]["wf"]["components"])
    case("CLI: --declare stages and installs each plugin package once, declares it from the install, adds the "
         "reusable-workflow entry from the map, and stamps HEAD (a stand-in install)",
         declared_offline, (0, True, "", True, ["marketplace", "install"], ["pkg", "wf"], 2,
                            {"y": {"files": ["scripts/lib/y.py"], "expected_count": 1}}))
    case("CLI: --declare with a map that breaks a rule is CANNOT RUN (rc 2), never a declaration",
         lambda: (lambda r: declare_cli(str(map_file(r, [{"id": "x", "package": "nope", "files": ["scripts/x.py"]}])),
                                        str(tmp() / "out.json"), r=r))(repo()),
         (2, "", "CANNOT RUN: the map is refused: component 'x': package 'nope' is not a key in packages\n"))
    def declare_usage():
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:  # unrouted, argparse exits on `--declare`: a red VALUE, never an aborted suite
                rc = main(["--declare"], repo=repo())
            except SystemExit as e:
                rc = ("argparse exited", e.code)
            rc3 = declare_main(["m.json", "o.json", "extra"], repo=tmp())
        return (rc, rc3, err.getvalue())
    case("CLI: --declare with no map or out path is a usage error (rc 2), routed by main",
         declare_usage, (2, 2, (DECLARE_USAGE + "\n") * 2))
    case("CLI: --declare with an unreadable map is CANNOT RUN (rc 2)",
         lambda: (lambda t: (t[0], t[2].startswith("CANNOT RUN: cannot read the map")))(
             declare_cli(str(tmp() / "no-map.json"), str(tmp() / "out.json"))), (2, True))

    def no_claude():
        r = repo()
        out, calls = tmp() / "out.json", []
        rc, _, e = declare_cli(str(map_file(r, [{"id": "x", "package": "pkg", "files": ["scripts/x.py"]}])), str(out),
                               r=r, which=lambda name: None, run=stand_in(calls), allow=["python3"])
        return (rc, e, out.exists(), calls)
    case("CLI: --declare without `claude` on PATH is CANNOT RUN, installs nothing and writes nothing",
         no_claude, (2, "CANNOT RUN: claude missing: --declare installs each plugin package with it\n", False, []))

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
    return 1 if fail or live_fail or fs_fail else 0


if __name__ == "__main__":
    sys.exit(main())

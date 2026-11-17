#!/usr/bin/env python3
"""The publishability scan (marketplace-inventory plan, Tasks 8-12; spec §5): for every component of the map,
what in its shipping set couples it to this repository.

    python3 scripts/check-publishability.py --self-test  # 20 cases
    python3 scripts/check-publishability.py [--map P] [--sets P] [--out P]

It EVALUATES and never repairs: no file of a component is written. One line per component is printed, then a
summary line; `--out P` also writes the report as JSON. rc 0 when every component was scanned, rc 2 (CANNOT RUN)
when any was not: a component that could not be scanned has NO score, and a missing score is never a clean one.

THE REPORT is `{"measured_at": <commit>, "components": {id: entry}}`. A scanned entry is
`{"status": "scanned", "findings": [...], "mentions": [...]}`; one that could not be scanned is
`{"status": "CANNOT RUN", "why": <reason>}` and nothing else, so no reader can take an absent list for zero.

THE FILE SET of a component (`resolve`) is what the map lists, with every symlink resolved: a directory entry is
the tracked files under the REAL directory, so a set reached through `.claude/skills/x -> .agents/skills/x` is
the files, not the link. It is then compared MEMBER FOR MEMBER with what `shipping-sets.json` declares for the
component, and with the declared `expected_count`. Three things are CANNOT RUN: a set that resolves to no file,
a set whose members differ from the declared ones (equal cardinality does not help: identity is compared), and
a count that differs. A component the declaration does not name is CANNOT RUN too.
"""
from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAP = "docs/marketplace/components.json"
SETS = "docs/marketplace/shipping-sets.json"
SCANNED = "scanned"
CANNOT_RUN = "CANNOT RUN"


def _shipping_sets():
    """`check-shipping-sets.py`, loaded as a module: its hyphenated name cannot be imported."""
    spec = importlib.util.spec_from_file_location("check_shipping_sets",
                                                  Path(__file__).resolve().parent / "check-shipping-sets.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # a dataclass in it resolves its own module through sys.modules
    spec.loader.exec_module(mod)
    return mod


SS = _shipping_sets()
CannotRun = SS.CannotRun


@functools.lru_cache(maxsize=None)
def _tracked(base: Path) -> tuple:
    return tuple(SS.tracked(base))


def _real(base: Path, rel: str, cid: str) -> tuple[Path, str]:
    """`rel` with every symlink resolved: `(the real path, its repository path)`. Outside the tree is CANNOT RUN."""
    real = (base / rel).resolve()
    try:
        return real, real.relative_to(base).as_posix()
    except ValueError:
        raise CannotRun(f"{cid}: {rel} resolves outside the repository ({real})") from None


def resolve(component: dict, decl: dict, root: Path = REPO) -> list[Path]:
    """The files of `component` (a map entry), symlinks resolved, PROVEN equal to what `decl` (its package's entry
    in the declaration) says the component ships. Anything else raises CannotRun (module docstring)."""
    cid, base = component["id"], Path(root).resolve()
    declared = decl.get("components", {}).get(cid)
    if declared is None:
        raise CannotRun(f"{cid}: the declaration of package {component['package']} does not name it")
    found: set[str] = set()
    for entry in component["files"]:
        real, rel = _real(base, entry, cid)
        if entry.endswith("/"):
            found |= {_real(base, t, cid)[1] for t in _tracked(base) if t.startswith(rel + "/")}
        elif real.is_file():
            found.add(rel)
    if not found:
        raise CannotRun(f"{cid}: the set resolved to no file ({', '.join(component['files'])})")
    place = SS.source_path if decl["channel"] == "plugin" else (lambda f: f)
    want = {_real(base, place(f), cid)[1] for f in declared["files"]}
    if found != want:
        raise CannotRun(f"{cid}: the resolved set is not the declared one: resolved and not declared "
                        f"{sorted(found - want)}; declared and not resolved {sorted(want - found)}")
    if len(found) != declared["expected_count"]:
        raise CannotRun(f"{cid}: {len(found)} file(s) resolved, the declaration expects "
                        f"{declared['expected_count']}")
    return [base / f for f in sorted(found)]


def _head(root: Path) -> str:
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise CannotRun(f"cannot read the commit of {root}: {r.stderr.strip()}")
    return r.stdout.strip()


def scan(map_path: Path, sets_path: Path, root: Path = REPO) -> dict:
    """The ScanReport for the map at `map_path`, judged against the declaration at `sets_path`. A map or a
    declaration that cannot be read raises CannotRun: there is then no report at all."""
    try:
        m = SS.load_map(map_path, root)
    except SS.Refused as e:
        raise CannotRun(f"the map {map_path} is refused: {e}") from e
    packages = SS.load_declaration(sets_path)
    report = {"measured_at": _head(root), "components": {}}
    for c in sorted(m.components, key=lambda c: c["id"]):
        try:
            if c["package"] not in packages:
                raise CannotRun(f"{c['id']}: the declaration names no package {c['package']}")
            resolve(c, packages[c["package"]], root)
            report["components"][c["id"]] = {"status": SCANNED, "findings": [], "mentions": []}
        except CannotRun as e:
            report["components"][c["id"]] = {"status": CANNOT_RUN, "why": str(e)}
    return report


def render(report: dict) -> list[str]:
    """One line per component, then the summary line."""
    lines, entries = [], report["components"]
    for cid, e in sorted(entries.items()):
        lines.append(f"{cid}: scanned, {len(e['findings'])} finding(s), {len(e['mentions'])} mention(s)"
                     if e["status"] == SCANNED else f"{cid}: {CANNOT_RUN}: {e['why']}")
    done = sum(e["status"] == SCANNED for e in entries.values())
    return lines + [f"{len(entries)} component(s): {done} scanned, {len(entries) - done} {CANNOT_RUN}"]


def main(argv=None, root: Path = REPO) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--map", default=None)
    ap.add_argument("--sets", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    root = Path(root)
    try:
        report = scan(root / (a.map or MAP), root / (a.sets or SETS), root)
    except CannotRun as e:
        print(f"{CANNOT_RUN}: {e}")
        return 2
    print("\n".join(render(report)))
    if a.out:
        (root / a.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 2 if any(e["status"] != SCANNED for e in report["components"].values()) else 0


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
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

    def world(files: dict, links: dict | None = None) -> Path:
        """A committed git repository holding `files` (path -> text) and `links` (path -> symlink target)."""
        root = Path(tempfile.mkdtemp(prefix="publishability-")).resolve()
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        for rel, target in (links or {}).items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, root / rel)
        git = ["git", "-C", str(root), "-c", "user.name=f", "-c", "user.email=f@example.invalid",
               "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "fixture"], check=True)
        return root

    def comp(cid: str, files: list, package: str = "pk", roles=("entry-point",)) -> dict:
        return {"id": cid, "effort": 3, "roles": list(roles), "phase": "1", "package": package, "files": files}

    def put(root: Path, comps: list, declared: dict, channel: str = "plugin") -> tuple[Path, Path]:
        """Write a map of `comps` and a declaration `declared` (component id -> declared files) into `root`."""
        installed = sorted({f for fs in declared.values() for f in fs})
        m = {"measured_at": "fixture", "packages": {"pk": {"channel": channel}}, "components": comps,
             "exclusions": []}
        s = {"measured_at": "fixture", "packages": {"pk": {
            "channel": channel, "installed_files": installed,
            "components": {cid: {"files": fs, "expected_count": len(fs)} for cid, fs in declared.items()}}}}
        (root / "map.json").write_text(json.dumps(m))
        (root / "sets.json").write_text(json.dumps(s))
        return root / "map.json", root / "sets.json"

    def entry(root: Path, comps: list, declared: dict, cid: str) -> dict:
        return scan(*put(root, comps, declared), root=root)["components"][cid]

    def out(run) -> tuple[int, list[str]]:
        """`run()` (a call of `main`) with its stdout captured: `(rc, lines)`."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run()
        return rc, buf.getvalue().splitlines()

    safe = "print('nothing coupled')\n"
    coupled = "import subprocess\nsubprocess.run(['python3', 'scripts/elsewhere.py'])\n"

    # --- Task 8: the file set -------------------------------------------------------------------------------
    w_ok = world({"scripts/safe.py": safe, "scripts/coupled.py": coupled, "skills/local.md": "a file\n"})
    case("a component whose resolved set equals the declared one is scanned",
         lambda: entry(w_ok, [comp("c", ["scripts/coupled.py"])], {"c": ["scripts/coupled.py"]}, "c")["status"],
         SCANNED)
    w_empty = world({"scripts/safe.py": safe, "data/keep/x.txt": "x\n"})
    (w_empty / "data/emptied").mkdir()
    case("an emptied set is CANNOT RUN",
         lambda: entry(w_empty, [comp("c", ["data/emptied/"])], {"c": ["data/emptied/x.txt"]}, "c"),
         {"status": CANNOT_RUN, "why": "c: the set resolved to no file (data/emptied/)"})
    case("a substituted member with equal cardinality is CANNOT RUN",
         lambda: entry(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/coupled.py"]}, "c"),
         {"status": CANNOT_RUN, "why": "c: the resolved set is not the declared one: resolved and not declared "
                                       "['scripts/safe.py']; declared and not resolved ['scripts/coupled.py']"})
    case("a declared count that is not the resolved count is CANNOT RUN",
         lambda: (lambda m, s: (s.write_text(s.read_text().replace('"expected_count": 1', '"expected_count": 2')),
                                scan(m, s, root=w_ok)["components"]["c"])[1])(
             *put(w_ok, [comp("c", ["scripts/coupled.py"])], {"c": ["scripts/coupled.py"]})),
         {"status": CANNOT_RUN, "why": "c: 1 file(s) resolved, the declaration expects 2"})
    case("a component the declaration does not name is CANNOT RUN",
         lambda: entry(w_ok, [comp("c", ["scripts/coupled.py"]), comp("d", ["scripts/safe.py"])],
                       {"c": ["scripts/coupled.py"]}, "d"),
         {"status": CANNOT_RUN, "why": "d: the declaration of package pk does not name it"})
    w_link = world({".agents/skills/x/SKILL.md": "Run `python3 scripts/elsewhere.py`.\n",
                    ".agents/skills/x/notes.md": "notes\n"},
                   links={".claude/skills": "../.agents/skills"})
    case("a set walked through a symlinked directory finds the known positive",
         lambda: [str(p.relative_to(w_link)) for p in resolve(
             comp("x", [".claude/skills/x/"]),
             {"channel": "plugin", "components": {"x": {"files": ["skills/x/SKILL.md", "skills/x/notes.md"],
                                                        "expected_count": 2}}}, root=w_link)],
         [".agents/skills/x/SKILL.md", ".agents/skills/x/notes.md"])
    case("resolve: a reusable-workflow declaration is read in repository paths, a single file resolved",
         lambda: [str(p.relative_to(w_ok)) for p in resolve(
             comp("c", ["skills/local.md"]),
             {"channel": "reusable-workflow", "components": {"c": {"files": ["skills/local.md"],
                                                                   "expected_count": 1}}}, root=w_ok)],
         ["skills/local.md"])
    case("resolve: a listed file that is not on disk is no member, and a set of only that is CANNOT RUN",
         lambda: resolve(comp("g", ["scripts/gone.py"]),
                         {"channel": "plugin", "components": {"g": {"files": ["scripts/gone.py"],
                                                                    "expected_count": 1}}}, root=w_ok),
         "RAISED CannotRun: g: the set resolved to no file (scripts/gone.py)")
    w_esc = world({"in/a.txt": "a\n"}, links={"in/esc": "../.."})
    case("resolve: an entry that resolves outside the repository is CANNOT RUN",
         lambda: resolve(comp("e", ["in/esc/"]),
                         {"channel": "plugin", "components": {"e": {"files": ["in/a.txt"], "expected_count": 1}}},
                         root=w_esc),
         f"RAISED CannotRun: e: in/esc/ resolves outside the repository ({w_esc.parent})")
    case("the report for a CANNOT RUN component carries no findings field that reads as zero",
         lambda: sorted(entry(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/coupled.py"]}, "c")),
         ["status", "why"])
    case("a scanned entry carries findings and mentions, and no why",
         lambda: sorted(entry(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/safe.py"]}, "c")),
         ["findings", "mentions", "status"])
    case("the report's measured_at is the commit of the tree scanned",
         lambda: scan(*put(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/safe.py"]}),
                      root=w_ok)["measured_at"],
         subprocess.run(["git", "-C", str(w_ok), "rev-parse", "HEAD"], capture_output=True,
                        text=True).stdout.strip())
    case("CLI: every component scanned is rc 0, one line per component and a summary",
         lambda: out(lambda: main(["--map", "map.json", "--sets", "sets.json"], root=put(
             w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/safe.py"]})[0].parent)),
         (0, ["c: scanned, 0 finding(s), 0 mention(s)", "1 component(s): 1 scanned, 0 CANNOT RUN"]))
    case("CLI: one CANNOT RUN component is rc 2 and the line says why, beside a scanned one",
         lambda: out(lambda: main(["--map", "map.json", "--sets", "sets.json"], root=put(
             w_empty, [comp("c", ["data/emptied/"]), comp("k", ["data/keep/"])],
             {"c": ["data/emptied/x.txt"], "k": ["data/keep/x.txt"]})[0].parent)),
         (2, ["c: CANNOT RUN: c: the set resolved to no file (data/emptied/)",
              "k: scanned, 0 finding(s), 0 mention(s)", "2 component(s): 1 scanned, 1 CANNOT RUN"]))
    w_bad = world({"scripts/safe.py": safe})
    (w_bad / "map.json").write_text(json.dumps({"measured_at": "f", "packages": {"pk": {"channel": "plugin"}},
                                                "components": [comp("c", ["scripts/safe.py"])], "exclusions": []}))
    (w_bad / "sets.json").write_text(json.dumps({"measured_at": "f", "packages": {}}))
    case("CLI: an emptied shipping-sets.json is rc 2, CANNOT RUN, and no component line",
         lambda: out(lambda: main(["--map", "map.json", "--sets", "sets.json"], root=w_bad)),
         (2, [f"CANNOT RUN: the declaration {w_bad / 'sets.json'} names no packages"]))
    (w_bad / "refused.json").write_text(json.dumps({"packages": {}}))
    case("CLI: a map the map rules refuse is rc 2, CANNOT RUN",
         lambda: out(lambda: main(["--map", "refused.json", "--sets", "sets.json"], root=w_bad)),
         (2, [f"CANNOT RUN: the map {w_bad / 'refused.json'} is refused: the map has no `packages`"]))
    (w_bad / "two.json").write_text(json.dumps({
        "measured_at": "f", "packages": {"pk": {"channel": "plugin"}, "other": {"channel": "plugin"}},
        "components": [comp("c", ["scripts/safe.py"], package="other")], "exclusions": []}))
    (w_bad / "one.json").write_text(json.dumps({"measured_at": "f", "packages": {"pk": {
        "channel": "plugin", "installed_files": ["scripts/safe.py"],
        "components": {"c": {"files": ["scripts/safe.py"], "expected_count": 1}}}}}))
    case("a component whose package the declaration does not hold is CANNOT RUN",
         lambda: scan(w_bad / "two.json", w_bad / "one.json", root=w_bad)["components"],
         {"c": {"status": CANNOT_RUN, "why": "c: the declaration names no package other"}})
    (w_bad / "broken.json").write_text("{")
    case("CLI: an unreadable map is rc 2, CANNOT RUN",
         lambda: (lambda rc, out: (rc, out[0][:len("CANNOT RUN: cannot read the map")]))(
             *out(lambda: main(["--map", "broken.json", "--sets", "sets.json"], root=w_bad))),
         (2, "CANNOT RUN: cannot read the map"))
    case("CLI: --out writes the report, a CANNOT RUN entry as it is",
         lambda: (lambda d: (out(lambda: main(["--map", "map.json", "--sets", "sets.json", "--out", "report.json"],
                                                 root=d))[0],
                             json.loads((d / "report.json").read_text())["components"]))(
             put(w_ok, [comp("c", ["scripts/safe.py"]), comp("k", ["scripts/coupled.py"])],
                 {"c": ["scripts/coupled.py"], "k": ["scripts/coupled.py"]})[0].parent),
         (2, {"c": {"status": CANNOT_RUN,
                    "why": "c: the resolved set is not the declared one: resolved and not declared "
                           "['scripts/safe.py']; declared and not resolved ['scripts/coupled.py']"},
              "k": {"status": SCANNED, "findings": [], "mentions": []}}))

    if os.environ.get("PLAN_CODE_MUTATION_RUN") == "1":
        print("NOT RUN under the mutation harness: 1 live-tree cases (CI's ordinary step runs them)")
    else:
        case("the live tree: every component of the real map is scanned, none CANNOT RUN",
             lambda: sorted({e["status"] for e in scan(REPO / MAP, REPO / SETS)["components"].values()}),
             [SCANNED])

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

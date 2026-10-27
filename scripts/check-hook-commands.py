#!/usr/bin/env python3
"""Every hook in `.claude/settings.json` is launched in ONE exact shape, through `run-hook.sh` (backlog #223).

WHY THIS FILE EXISTS (measured live 2026-10-02).
  Every hook was registered as `bash .claude/hooks/<name>.sh`, and the harness runs that from the
  SESSION's working directory. After one `cd scripts && …`, every hook (the push gate included)
  printed `No such file or directory`, the harness reported it as NON-BLOCKING, and nothing stopped.

  The fix is `bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh`. The launcher is
  found through the stable project dir. It then walks up from the physical cwd to the nearest
  directory holding both `.git` and `run-hook.sh` and runs the hook from THAT checkout, with no git
  process; the project dir only when there is none. That is the old relative form extended to
  subdirectories: at any checkout root it picks the copy the relative form picked.
  ⟳ PR #409 round 2 refuted the git-asking version: an inherited `GIT_CEILING_DIRECTORIES` made
  discovery fail into the project (main) checkout, and a hook missing in a worktree ran MAIN's copy.
  ⟳ PR #409 round 1 (both halves) refuted the first version twice:
    - anchoring at `$CLAUDE_PROJECT_DIR` alone ran the MAIN checkout's hooks from a linked
      worktree, so a pending plan gate there was ignored (exit 0 where it had been 2);
    - its guard was a DENYLIST of relative tokens, and `sh -c '…'`, `"$PWD"/…`,
      `cd x && bash y`, `FOO=… bash $FOO`, `||true`, and a misspelt `$CLAUDE_PROJECT_DIRX` all
      slipped past it while still failing from a subdirectory.
  So this is an ALLOWLIST of exactly one shape: anything else is refused, whatever it would have
  done. The cost is stated: a command that would work but is not the canonical form is refused
  too. That is deliberate. There is one way to register a hook, and the launcher's behaviour is
  tested here.

WHAT IT REFUSES:
  1. a `type: command` hook whose command is not exactly CANONICAL;
  2. a canonical command naming a hook file that does not exist in `.claude/hooks/`;
  3. a hook file in `.claude/hooks/` that no command registers and that is not in UNREGISTERED
     with a reason. A registry entry that IS registered, or names no file, is stale and refused.
  Missing or unparseable settings, a malformed hooks block, and ZERO commands are CANNOT RUN.

  It also RUNS the launcher (`--self-test`) over real git worlds, including a linked worktree with
  the project dir naming the main checkout, which is round 1's regression.

WHAT WOULD MAKE THIS FAIL (its falsifier): a hook command in `.claude/settings.json` that is not
the canonical launcher form, or a launcher that runs the main checkout's hook from inside a linked
worktree of this repository.

⚠ BOUNDS. Only the TRACKED `.claude/settings.json` is read; `settings.local.json` is per-machine.
⚠ The harness's mutation runner runs `python3 <file> --self-test` on the file it mutates, so it
cannot mutate `run-hook.sh` itself. The launcher's mutations were applied by hand (recorded in
the PR #409 round-1 and round-2 coordinator records). The cases below are what turn them red.

    python3 scripts/check-hook-commands.py --self-test  # 36 cases

EXIT CODES (repo convention): 0 = every hook canonical and registered · 1 = a violation ·
2 = CANNOT RUN (never a pass).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_REL = ".claude/settings.json"
HOOKS_REL = ".claude/hooks"
LAUNCHER = "run-hook.sh"
CANONICAL = re.compile(
    r'bash "\$\{CLAUDE_PROJECT_DIR:-\.\}"/\.claude/hooks/run-hook\.sh ([A-Za-z0-9_][A-Za-z0-9._-]*\.sh)')

# Hook files that are deliberately NOT registered, each with its reason. A file not here and not
# registered is refused: an unregistered hook is a gate with no caller.
UNREGISTERED: dict[str, str] = {
    "check-memory-index-budget.sh": "advisory; deliberately not registered, see the NOT REGISTERED "
                                    "note above the memory-index step in .github/workflows/ci.yml",
}


class Malformed(Exception):
    """The hooks block does not have the shape the harness reads: CANNOT RUN, never a pass."""


def hook_commands(settings: dict) -> list[tuple[str, str]]:
    """(event, command) for every hook of type "command". Raises Malformed on an unexpected shape."""
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise Malformed("`hooks` is not an object")
    out = []
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise Malformed(f"`hooks.{event}` is not a list")
        for g in groups:
            inner = g.get("hooks") if isinstance(g, dict) else None
            if not isinstance(inner, list):
                raise Malformed(f"a `hooks.{event}` entry has no `hooks` list")
            for h in inner:
                if not isinstance(h, dict):
                    raise Malformed(f"a `hooks.{event}` hook is not an object")
                if h.get("type") == "command":
                    cmd = h.get("command")
                    if not isinstance(cmd, str):
                        raise Malformed(f"a `hooks.{event}` command is not a string")
                    out.append((event, cmd))
    return out


def problems(commands: list[tuple[str, str]], on_disk: set[str], unregistered: dict[str, str]) -> list[str]:
    """The rule, pure. `on_disk` = the file names in `.claude/hooks/`."""
    out, registered = [], set()
    for event, cmd in commands:
        m = CANONICAL.fullmatch(cmd)
        if not m:
            out.append(f"{event}: {cmd!r} is not the one launcher form — write "
                       f"bash \"${{CLAUDE_PROJECT_DIR:-.}}\"/.claude/hooks/run-hook.sh <name>.sh")
            continue
        name = m.group(1)
        if name == LAUNCHER:
            out.append(f"{event}: {cmd!r} registers the launcher as a hook")
        elif name not in on_disk:
            out.append(f"{event}: {cmd!r} names {HOOKS_REL}/{name}, which does not exist — it would launch nothing")
        registered.add(name)
    if LAUNCHER not in on_disk:
        out.append(f"{HOOKS_REL}/{LAUNCHER} does not exist — every registered hook would launch nothing")
    for f in sorted(on_disk - registered - {LAUNCHER}):
        if f.endswith(".sh") and f not in unregistered:
            out.append(f"{HOOKS_REL}/{f} is registered by no command and has no UNREGISTERED reason — a gate with no caller")
    for f in sorted(unregistered):
        if f in registered:
            out.append(f"UNREGISTERED lists {f}, which IS registered — stale entry")
        elif f not in on_disk:
            out.append(f"UNREGISTERED lists {f}, which does not exist — stale entry")
    return out


def check(path: Path, root: Path, unregistered: dict[str, str] = UNREGISTERED) -> tuple[int, list[str]]:
    """Return (exit_code, messages). Anything that stops the rule being applied is CANNOT RUN."""
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 2, [f"CANNOT RUN — {path} does not exist. Treat this as NOT RUN, not as a pass."]
    except (OSError, ValueError) as exc:
        return 2, [f"CANNOT RUN — cannot read {path}: {exc}. Treat this as NOT RUN."]
    if not isinstance(settings, dict):
        return 2, [f"CANNOT RUN — {path} is not a JSON object. Treat this as NOT RUN."]
    try:
        commands = hook_commands(settings)
    except Malformed as exc:
        return 2, [f"CANNOT RUN — {path}: {exc}. Treat this as NOT RUN."]
    if not commands:
        return 2, [f"CANNOT RUN — {path} registers ZERO hook commands. Treat this as NOT RUN."]
    hooks_dir = root / HOOKS_REL
    on_disk = {p.name for p in hooks_dir.iterdir() if p.is_file()} if hooks_dir.is_dir() else set()
    found = problems(commands, on_disk, unregistered)
    return (1 if found else 0), found or [f"{len(commands)} hook command(s), every one the launcher form"]


# ─── the launcher, RUN over real git worlds ────────────────────────────────────────────────────

_PROBE = 'printf "%s|%s|%s" "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)" "$#" "$(cat)"\n'


def _git(cwd: Path, *args: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def _repo(at: Path, launcher: Path) -> Path:
    """A git repo with the launcher and a probe hook that prints <its root>|<argc>|<stdin>."""
    (at / HOOKS_REL).mkdir(parents=True)
    shutil.copy(launcher, at / HOOKS_REL / LAUNCHER)
    (at / HOOKS_REL / "probe.sh").write_text(_PROBE)
    (at / "sub").mkdir()
    (at / "sub/.keep").write_text("")
    _git(at, "init", "-q", "-b", "main")
    _git(at, "add", "-A")
    _git(at, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return at


def launch(cwd: Path, project: Path | None, *argv: str, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    """Run the PROJECT's launcher the way the harness would: from `cwd`, with `CLAUDE_PROJECT_DIR`."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "CLAUDE_PROJECT_DIR"}
    env.update(extra_env or {})
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    launcher = (project or cwd) / HOOKS_REL / LAUNCHER
    r = subprocess.run(["bash", str(launcher), *argv], cwd=cwd, env=env, input="PAYLOAD",
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout


def self_test(launcher: Path = REPO_ROOT / HOOKS_REL / LAUNCHER) -> int:
    import tempfile

    good = 'bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh x.sh'
    disk = {"x.sh", "y.sh", LAUNCHER}
    reg = {"y.sh": "deliberately unregistered"}

    def cmds(*c):
        return [("PreToolUse", x) for x in c]

    def on_cmd(found):  # only the findings ABOUT a command, not the registry lines they cause
        return [f for f in found if f.startswith("PreToolUse:")]

    bypasses = [  # every one escaped round 1's denylist and still failed from a subdirectory
        "bash .claude/hooks/x.sh", "sh -c 'bash .claude/hooks/x.sh'", 'bash "$PWD"/.claude/hooks/x.sh',
        "cd .claude/hooks && bash x.sh", "FOO=.claude/hooks/x.sh bash $FOO",
        'bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh x.sh||true',
        'bash "${CLAUDE_PROJECT_DIRX:-.}"/.claude/hooks/run-hook.sh x.sh',
        'bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/x.sh',  # round 1's own fix: anchored, but no launcher
    ]
    cases = [
        ("the one launcher form passes", problems(cmds(good), disk, reg), 0),
        ("⭐ the shipped defect — `bash .claude/hooks/x.sh` — is refused",
         on_cmd(problems(cmds("bash .claude/hooks/x.sh"), disk, reg)), 1),
        ("every round-1 bypass is refused — one finding each, by the allowlist",
         on_cmd(problems(cmds(*bypasses), disk, reg)), len(bypasses)),
        ("an absolute path is refused too — one shape, not 'anything that resolves'",
         on_cmd(problems(cmds("bash /opt/hooks/x.sh"), disk, reg)), 1),
        ("the canonical form naming a hook that does not exist is refused",
         on_cmd(problems(cmds(good.replace("x.sh", "gone.sh")), disk, reg)), 1),
        ("registering the launcher itself as a hook is refused",
         on_cmd(problems(cmds(good.replace(" x.sh", " run-hook.sh")), disk, reg)), 1),
        ("a missing launcher is refused even when every command is canonical",
         problems(cmds(good), {"x.sh", "y.sh"}, reg), 1),
        ("a hook file nobody registers and nobody explains is refused",
         problems(cmds(good), disk | {"z.sh"}, reg), 1),
        ("...and the SAME file passes once it has an UNREGISTERED reason",
         problems(cmds(good), disk | {"z.sh"}, {**reg, "z.sh": "why"}), 0),
        ("a stale UNREGISTERED entry — the file is registered — is refused",
         problems(cmds(good), disk, {**reg, "x.sh": "why"}), 1),
        ("a stale UNREGISTERED entry — no such file — is refused",
         problems(cmds(good), disk, {**reg, "q.sh": "why"}), 1),
    ]
    failures = 0
    print("check-hook-commands --self-test")
    for name, got, want in cases:
        ok = len(got) == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {len(got)} want {want}")

    more: list[tuple[str, object, object]] = []
    with tempfile.TemporaryDirectory() as td:
        t = Path(td).resolve()
        root = t / "w"
        (root / HOOKS_REL).mkdir(parents=True)
        for f in ("x.sh", LAUNCHER):
            (root / HOOKS_REL / f).write_text("exit 0\n")
        p = root / SETTINGS_REL
        more.append(("a missing settings file is CANNOT RUN", check(p, root, {})[0], 2))
        p.write_text("{not json")
        more.append(("unparseable settings are CANNOT RUN", check(p, root, {})[0], 2))
        p.write_text("[]")
        more.append(("a settings file that is a JSON array is CANNOT RUN, not a crash", check(p, root, {})[0], 2))
        p.write_text(json.dumps({"hooks": {"Stop": {"hooks": []}}}))
        more.append(("a malformed hooks block is CANNOT RUN, not a crash", check(p, root, {})[0], 2))
        p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "prompt", "prompt": "x"}]}]}}))
        more.append(("ZERO command hooks is CANNOT RUN — a zero over nothing is not a pass", check(p, root, {})[0], 2))
        p.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": good}]}]}}))
        more.append(("a canonical command whose hook exists under ROOT passes", check(p, root, {})[0], 0))
        (root / HOOKS_REL / "extra.sh").write_text("exit 0\n")
        more.append(("...and the same settings with an unexplained extra hook under ROOT are refused",
                     check(p, root, {})[0], 1))
        more.append(("...and pass again when UNREGISTERED explains that extra hook",
                     check(p, root, {"extra.sh": "why"})[0], 0))
        (root / HOOKS_REL / "extra.sh").unlink()
        alt = t / "alt-settings.json"  # the settings PATH is read as given, not rebuilt from root
        alt.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bash .claude/hooks/x.sh"}]}]}}))
        more.append(("the settings file is the PATH given — a defective file elsewhere is refused", check(alt, root, {})[0], 1))
        empty = t / "empty-root"
        empty.mkdir()
        more.append(("the same good settings judged against a ROOT with no hooks are refused", check(p, empty, {})[0], 1))
        more.append(("main() over a compliant world exits 0", main([], root=root, unregistered={}), 0))
        p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bash .claude/hooks/x.sh"}]}]}}))
        more.append(("⭐ main() over the shipped defect exits 1", main([], root=root), 1))
        more.append(("main() over a world with no settings file exits 2 (CANNOT RUN)", main([], root=t / "none"), 2))

        # The launcher, over real git: a main checkout, a linked worktree of it, an unrelated repo.
        main_co = _repo(t / "main", launcher)
        wt = t / "wt"
        _git(main_co, "worktree", "add", "-q", str(wt))
        other = _repo(t / "other", launcher)
        bare_dir = t / "nogit"
        bare_dir.mkdir()
        (main_co / HOOKS_REL / "only-main.sh").write_text(_PROBE)  # untracked: the worktree never gets it
        nested = _repo(main_co / "nested", launcher)  # a checkout INSIDE main, as a submodule root is
        plain = t / "plain"  # a copy of the hooks with NO .git — not a checkout
        (plain / HOOKS_REL).mkdir(parents=True)
        shutil.copy(launcher, plain / HOOKS_REL / LAUNCHER)
        (plain / HOOKS_REL / "probe.sh").write_text(_PROBE)
        (plain / "sub").mkdir()
        more += [
            ("⭐ from a linked worktree's SUBDIRECTORY, with the project dir naming MAIN, the WORKTREE's hook runs",
             launch(wt / "sub", main_co, "probe.sh"), (0, f"{wt}|0|PAYLOAD")),
            ("from the main checkout's subdirectory, the main checkout's hook runs",
             launch(main_co / "sub", main_co, "probe.sh"), (0, f"{main_co}|0|PAYLOAD")),
            ("from ANOTHER checkout with its own launcher, ITS hook runs — as the relative form did at its root",
             launch(other / "sub", main_co, "probe.sh"), (0, f"{other}|0|PAYLOAD")),
            ("⭐ an inherited GIT_CEILING_DIRECTORIES cannot steer it — the worktree's hook still runs (round 2)",
             launch(wt / "sub", main_co, "probe.sh", extra_env={"GIT_CEILING_DIRECTORIES": str(wt)}),
             (0, f"{wt}|0|PAYLOAD")),
            ("⭐ a hook MISSING in the worktree is NOT RUN — main's copy is never substituted (round 2)",
             launch(wt / "sub", main_co, "only-main.sh"), (1, "")),
            ("a checkout nested inside main (a submodule root) keeps ITS hooks (round 2)",
             launch(nested / "sub", main_co, "probe.sh"), (0, f"{nested}|0|PAYLOAD")),
            ("a hooks copy with no .git is not a checkout — the project's hook runs",
             launch(plain / "sub", main_co, "probe.sh"), (0, f"{main_co}|0|PAYLOAD")),
            ("from outside any git repo, the project's hook runs",
             launch(bare_dir, main_co, "probe.sh"), (0, f"{main_co}|0|PAYLOAD")),
            ("with the project dir UNSET, from the checkout root, the old relative behaviour holds",
             launch(main_co, None, "probe.sh"), (0, f"{main_co}|0|PAYLOAD")),
            ("no argument after the hook name reaches the hook (surface-recall relies on it)",
             launch(main_co, main_co, "probe.sh", "extra"), (0, f"{main_co}|0|PAYLOAD")),
            ("a path-shaped hook name is refused, exit 1", launch(main_co, main_co, "../hooks/probe.sh")[0], 1),
            ("a hook name that does not exist exits 1, NOT RUN", launch(main_co, main_co, "gone.sh")[0], 1),
        ]
    for name, got, want in more:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    total = len(cases) + len(more)
    print(f"\n{total - failures}/{total} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT,
         unregistered: dict[str, str] = UNREGISTERED) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    code, messages = check(root / SETTINGS_REL, root, unregistered)
    if code == 0:
        print(f"ok — {SETTINGS_REL}: {messages[0]}")
        return 0
    label = "CANNOT RUN" if code == 2 else "HOOK REGISTRATION"
    print(f"{label} — {SETTINGS_REL}", file=sys.stderr)
    for m in messages:
        print(f"  {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())

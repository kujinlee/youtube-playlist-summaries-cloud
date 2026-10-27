#!/usr/bin/env python3
"""Every hook in `.claude/settings.json` is registered in ONE exact shape, and every hook file is registered.

This is the STABLE HALF of backlog #223, shipped by a true SPLIT (PR #409, the owner's choice A, 2026-10-26).

THE OPEN DEFECT IT DOES NOT FIX, stated first so nobody reads this guard as the fix.
  Every hook is registered as `bash .claude/hooks/<name>.sh`, and the harness runs that from the
  SESSION's working directory. After one `cd scripts && …`, every hook, the push gate included,
  fails to launch, and the harness calls that NON-BLOCKING (measured live 2026-10-02). Three designs
  for launching from the right checkout each lost a review round (PR #409 r1–r3: the project dir ran
  the MAIN checkout's hooks from a worktree; asking git was steerable by `GIT_CEILING_DIRECTORIES`; a
  launcher marker skipped every worktree made before it existed). Rounds 2 and 3 were both caused by
  the previous fold, which is the thrashing rule, so the launcher is its own subject (backlog #364),
  designed after an architecture review. The shape below is TODAY's shape, known defective, and it
  is the ONE place to change when that design lands.

WHAT IT REFUSES:
  1. a `type: command` hook whose command is not exactly CANONICAL — so a second, divergent way of
     registering a hook (`sh -c '…'`, `"$PWD"/…`, `cd … &&`, an absolute path) cannot creep in, and the
     launcher, when it comes, replaces one shape rather than many;
  2. a canonical command naming a hook file that does not exist (it would launch nothing);
  3. a hook file in `.claude/hooks/` that no command registers and that is not in UNREGISTERED with a
     reason — a gate with no caller. A registry entry that IS registered, or names no file, is stale.
  Missing or unparseable settings, a malformed hooks block, and ZERO commands are CANNOT RUN.

WHAT WOULD MAKE THIS FAIL (its falsifier): a hook command in a second shape, a registered hook that
does not exist, or a hook file nobody registers or explains.

⚠ BOUND: only the TRACKED `.claude/settings.json` is read; `settings.local.json` is per-machine.
⟳ backlog #365 (from PR #409 round 4): a hook entry with no `type`, a `type` that is not a string, or one
  outside KNOWN_TYPES (the five in Claude Code 2.1.309's schema) is Malformed → CANNOT RUN instead of skipped;
  an `UNREGISTERED` reason must be a non-empty STRING. A type Claude Code ships AFTER 2.1.309 fails loudly
  here until it is named, which is the safe direction.
⟳ backlog #368: a command hook carrying `args` (Claude Code 2.1.309's runner code spawns `command` as ONE
  executable with no shell — read, not run end to end) or `shell` (it changes which shell runs the command) is
  REFUSED: either way it is not run the way the one registration shape assumes.

    python3 scripts/check-hook-commands.py --self-test  # 33 cases

EXIT CODES (repo convention): 0 = every hook canonical and registered · 1 = a violation ·
2 = CANNOT RUN (never a pass).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_REL = ".claude/settings.json"
HOOKS_REL = ".claude/hooks"
# Every hook type in Claude Code 2.1.309's hook schema (PR #412 r1, both halves: `agent`, `http` and `mcp_tool` were
# missing, so a legitimate hook of those types would have read as CANNOT RUN in CI). Anything else is CANNOT RUN.
KNOWN_TYPES = frozenset({"command", "prompt", "agent", "http", "mcp_tool"})
CANONICAL = re.compile(r"bash \.claude/hooks/([A-Za-z0-9_][A-Za-z0-9._-]*\.sh)")

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
                if not isinstance(h.get("type"), str) or h.get("type") not in KNOWN_TYPES:
                    raise Malformed(f"a `hooks.{event}` hook has type {h.get('type')!r}, which this guard does not "
                                    f"know (known: {sorted(KNOWN_TYPES)})")
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
            out.append(f"{event}: {cmd!r} is not the one registration form — write bash .claude/hooks/<name>.sh")
            continue
        name = m.group(1)
        if name not in on_disk:
            out.append(f"{event}: {cmd!r} names {HOOKS_REL}/{name}, which does not exist — it would launch nothing")
        registered.add(name)
    for f in sorted(on_disk - registered):
        if f.endswith(".sh") and f not in unregistered:
            out.append(f"{HOOKS_REL}/{f} is registered by no command and has no UNREGISTERED reason — a gate with no caller")
    for f in sorted(unregistered):
        if not isinstance(unregistered[f], str) or not unregistered[f].strip():
            out.append(f"UNREGISTERED lists {f} with an EMPTY reason — an exemption must say why")
        if f in registered:
            out.append(f"UNREGISTERED lists {f}, which IS registered — stale entry")
        elif f not in on_disk:
            out.append(f"UNREGISTERED lists {f}, which does not exist — stale entry")
    return out


EXECUTION_OVERRIDES = ("args", "shell")


def execution_overrides(settings: dict) -> list[str]:
    """The rule, pure: a command hook carrying a field that changes HOW its command runs (backlog #368).
    Call only after `hook_commands` has accepted the structure."""
    out = []
    for event, groups in settings.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                if h.get("type") != "command":
                    continue
                for key in EXECUTION_OVERRIDES:
                    if key in h:
                        out.append(f"{event}: {h.get('command')!r} carries `{key}`, which changes how the command runs — "
                                   "the one registration shape assumes a plain shell command")
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
    found = problems(commands, on_disk, unregistered) + execution_overrides(settings)
    return (1 if found else 0), found or [f"{len(commands)} hook command(s), every one canonical and present"]


def self_test() -> int:
    import tempfile

    good = "bash .claude/hooks/x.sh"
    disk = {"x.sh", "y.sh"}
    reg = {"y.sh": "deliberately unregistered"}

    def cmds(*c):
        return [("PreToolUse", x) for x in c]

    def on_cmd(found):  # only the findings ABOUT a command, not the registry lines they cause
        return [f for f in found if f.startswith("PreToolUse:")]

    divergent = [  # second shapes — each would be one more thing the launcher has to replace
        "sh -c 'bash .claude/hooks/x.sh'", 'bash "$PWD"/.claude/hooks/x.sh', "cd .claude/hooks && bash x.sh",
        "FOO=.claude/hooks/x.sh bash $FOO", "bash .claude/hooks/x.sh||true", "bash ./.claude/hooks/x.sh",
        'bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/x.sh', "bash /opt/hooks/x.sh",
    ]
    cases = [
        ("the one registration form passes", problems(cmds(good), disk, reg), 0),
        ("every divergent shape is refused — one finding each", on_cmd(problems(cmds(*divergent), disk, reg)),
         len(divergent)),
        ("a trailing argument is a second shape too", on_cmd(problems(cmds(good + " --x"), disk, reg)), 1),
        ("the one form naming a hook that does not exist is refused",
         on_cmd(problems(cmds("bash .claude/hooks/gone.sh"), disk, reg)), 1),
        ("a hook file nobody registers and nobody explains is refused",
         problems(cmds(good), disk | {"z.sh"}, reg), 1),
        ("...and the SAME file passes once it has an UNREGISTERED reason",
         problems(cmds(good), disk | {"z.sh"}, {**reg, "z.sh": "why"}), 0),
        ("a non-.sh file in the hooks directory is not a hook", problems(cmds(good), disk | {"README.md"}, reg), 0),
        ("a stale UNREGISTERED entry — the file is registered — is refused",
         problems(cmds(good), disk, {**reg, "x.sh": "why"}), 1),
        ("⭐ an UNREGISTERED entry with an EMPTY reason is refused (backlog #365)",
         problems(cmds(good), disk | {"z.sh"}, {**reg, "z.sh": "  "}), 1),
        ("⭐ ...and so is a NON-STRING reason — str(None) is 'None', not a reason",
         problems(cmds(good), disk | {"z.sh"}, {**reg, "z.sh": None}), 1),
        ("a plain command hook carries no execution override",
         execution_overrides({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": good}]}]}}), 0),
        ("⭐ `args` and `shell` on two hooks are two findings; the same keys on a NON-command hook are not (backlog #368)",
         execution_overrides({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": good, "args": []},
                                                            {"type": "command", "command": good, "shell": "bash"},
                                                            {"type": "prompt", "args": [], "shell": "x"}]}]}}), 2),
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
        (root / HOOKS_REL / "x.sh").write_text("exit 0\n")
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
        more.append(("a registered hook that exists under ROOT passes", check(p, root, {})[0], 0))
        (root / HOOKS_REL / "extra.sh").write_text("exit 0\n")
        more.append(("...and an unexplained extra hook under ROOT is refused", check(p, root, {})[0], 1))
        more.append(("...and passes again when UNREGISTERED explains it", check(p, root, {"extra.sh": "why"})[0], 0))
        (root / HOOKS_REL / "extra.sh").unlink()
        alt = t / "alt-settings.json"  # the settings PATH is read as given, not rebuilt from root
        alt.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "sh -c x"}]}]}}))
        alt_rc, alt_msgs = check(alt, root, {})
        more.append(("the settings file is the PATH given — a divergent file elsewhere is refused FOR ITS SHAPE",
                     (alt_rc, any("is not the one registration form" in m for m in alt_msgs)), (1, True)))
        empty = t / "empty-root"
        empty.mkdir()
        more.append(("the same good settings judged against a ROOT with no hooks are refused", check(p, empty, {})[0], 1))
        more.append(("main() over a compliant world exits 0", main([], root=root, unregistered={}), 0))
        p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "sh -c 'bash .claude/hooks/x.sh'"}]}]}}))
        # ⚠ unregistered={} on purpose: with the default registry this world ALSO has a stale entry, and
        # the case would exit 1 with the divergent command removed (r3 CLAUDE F4).
        import io
        from contextlib import redirect_stderr
        with redirect_stderr(io.StringIO()) as err:
            rc = main([], root=root, unregistered={})
        more.append(("⭐ main() over a divergent registration exits 1 and NAMES the shape",
                     (rc, "is not the one registration form" in err.getvalue()), (1, True)))
        for bad in ({}, {"type": "commmand", "command": "bash .claude/hooks/x.sh"}, {"type": []}, {"type": {}}):
            p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": good}, bad]}]}}))
            more.append((f"⭐ a hook entry with type {bad.get('type')!r} is CANNOT RUN, not skipped or a crash (backlog #365)",
                         check(p, root, {})[0], 2))
        # ⚠ An INDEPENDENT copy of the schema's types, not derived from KNOWN_TYPES: derived, a dropped type
        # vanished from this list too and the case stayed green (the r1 fold's own first attempt).
        for key, val in (("args", []), ("shell", "powershell")):
            p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": good, key: val}]}]}}))
            rc_, msgs_ = check(p, root, {})
            more.append((f"⭐ a command hook carrying `{key}` is REFUSED — it would not run as a plain shell command (backlog #368)",
                         (rc_, any(f"carries `{key}`" in m for m in msgs_)), (1, True)))
        others = [{"type": k} for k in ("prompt", "agent", "http", "mcp_tool")]
        p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": good}] + others}]}}))
        more.append(("⭐ every KNOWN non-command type passes beside a canonical command (r1: dropping one stayed green)",
                     check(p, root, {})[0], 0))
        more.append(("main() over a world with no settings file exits 2 (CANNOT RUN)", main([], root=t / "none"), 2))
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

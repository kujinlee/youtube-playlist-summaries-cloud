#!/usr/bin/env python3
"""Every hook `command` in `.claude/settings.json` names its script by an ANCHORED path (backlog #223).

WHY THIS FILE EXISTS (measured live 2026-10-02).
  Every hook was registered as `bash .claude/hooks/<name>.sh`. The harness runs that from the
  SESSION's working directory, so after one Bash call of the form `cd scripts && …` every hook —
  the push gate included — printed `No such file or directory` and the harness reported it as a
  NON-BLOCKING error. Nothing stopped. The gates were sound; their invoker was not.

  The fix anchors each command at `${CLAUDE_PROJECT_DIR:-.}`, which the harness sets for hook
  commands. The `:-.` fallback keeps today's behaviour if it is ever unset, so the change cannot
  make a hook LESS reachable than before. This script is the half that survives the next edit of
  the settings file: without it, one pasted `bash .claude/hooks/new.sh` brings the class back.

WHAT IT REFUSES, per hook command of type "command":
  - a token that names a file under the repo (it exists relative to the repo root) by a RELATIVE
    path — `bash .claude/hooks/x.sh`, `python3 scripts/y.py`;
  - an anchored path whose file does NOT exist — a typo or a rename would otherwise launch nothing,
    which is the same silent non-blocking failure by another route.
  A token is anchored when it starts with `/`, `$CLAUDE_PROJECT_DIR` or `${CLAUDE_PROJECT_DIR`.

WHAT WOULD MAKE THIS FAIL (its falsifier): a hook command in `.claude/settings.json` names a repo
file by a path that does not resolve from a working directory other than the repo root.

⚠ BOUND: it reads the TRACKED `.claude/settings.json` only. `settings.local.json` is untracked and
per-machine, and a hook registered there is outside this guard.

    python3 scripts/check-hook-commands.py --self-test  # 19 cases

EXIT CODES (repo convention): 0 = every command anchored · 1 = a relative or dangling path ·
2 = CANNOT RUN (missing/unparseable settings, a malformed hooks block, or ZERO commands found —
a zero over nothing is not a finding).
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_REL = ".claude/settings.json"
ANCHORS = ("/", "$CLAUDE_PROJECT_DIR", "${CLAUDE_PROJECT_DIR")


class Malformed(Exception):
    """The hooks block does not have the shape the harness reads — CANNOT RUN, never a pass."""


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


def anchored_rel(token: str) -> str | None:
    """The repo-relative part of an anchored token, or None when the token is not anchored."""
    for a in ("${CLAUDE_PROJECT_DIR:-.}", "${CLAUDE_PROJECT_DIR}", "$CLAUDE_PROJECT_DIR"):
        if token.startswith(a + "/"):
            return token[len(a) + 1:]
    return None


def problems(commands: list[tuple[str, str]], exists) -> list[str]:
    """The rule, pure: `exists(rel)` answers whether a repo-relative path names a real file."""
    out = []
    for event, cmd in commands:
        try:
            tokens = shlex.split(cmd)
        except ValueError as exc:
            out.append(f"{event}: cannot tokenise {cmd!r}: {exc}")
            continue
        for tok in tokens:
            if tok.startswith("-") or "/" not in tok:
                continue
            rel = anchored_rel(tok)
            if rel is not None:
                if not exists(rel):
                    out.append(f"{event}: {cmd!r} names {rel}, which does not exist — the hook would launch nothing")
            elif not tok.startswith(ANCHORS) and exists(tok):
                out.append(f"{event}: {cmd!r} names {tok} by a RELATIVE path — inert whenever the session's "
                           f"cwd is not the repo root; write \"${{CLAUDE_PROJECT_DIR:-.}}\"/{tok}")
    return out


def check(path: Path, root: Path) -> tuple[int, list[str]]:
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
    found = problems(commands, lambda rel: (root / rel).is_file())
    return (1 if found else 0), found or [f"{len(commands)} hook command(s), every one anchored"]


def self_test() -> int:
    import tempfile

    real = {"scripts/y.py", ".claude/hooks/x.sh"}
    has = real.__contains__
    none = lambda _rel: False  # noqa: E731 — a world where no repo file exists

    def cmds(*c):
        return [("PreToolUse", x) for x in c]

    cases = [
        ("the anchored form with its fallback passes",
         problems(cmds('bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/x.sh'), has), 0),
        ("the bare $CLAUDE_PROJECT_DIR form passes",
         problems(cmds('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh"'), has), 0),
        ("⭐ the shipped defect — `bash .claude/hooks/x.sh` — is refused",
         problems(cmds("bash .claude/hooks/x.sh"), has), 1),
        ("a relative path to a SCRIPT, not a hook, is refused too — the class, not the instance",
         problems(cmds("python3 scripts/y.py --quiet"), has), 1),
        ("an absolute path passes",
         problems(cmds("bash /opt/hooks/z.sh"), has), 0),
        ("an anchored path to a file that does not exist is refused — it would launch nothing",
         problems(cmds('bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/x.sh'), none), 1),
        ("a slashed token that names no repo file is not a path claim (adjacent negative)",
         problems(cmds("echo done/ok"), has), 0),
        ("...and the same relative token is NOT refused in a world where it is no repo file",
         problems(cmds("bash .claude/hooks/x.sh"), none), 0),
        ("two relative tokens in one command are two findings",
         problems(cmds("bash .claude/hooks/x.sh scripts/y.py"), has), 2),
        ("an untokenisable command is a finding, not a crash",
         problems(cmds('bash "unterminated'), has), 1),
    ]
    failures = 0
    print("check-hook-commands --self-test")
    for name, got, want in cases:
        ok = len(got) == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {len(got)} want {want}")

    file_cases = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".claude/hooks").mkdir(parents=True)
        (root / ".claude/hooks/x.sh").write_text("exit 0\n")
        p = root / "settings.json"
        file_cases.append(("a missing settings file is CANNOT RUN", check(root / "nope.json", root)[0], 2))
        p.write_text("{not json")
        file_cases.append(("unparseable settings are CANNOT RUN", check(p, root)[0], 2))
        p.write_text(json.dumps({"hooks": {"Stop": {"hooks": []}}}))
        file_cases.append(("a malformed hooks block is CANNOT RUN, not a crash", check(p, root)[0], 2))
        p.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "prompt", "prompt": "x"}]}]}}))
        file_cases.append(("ZERO command hooks is CANNOT RUN — a zero over nothing is not a pass",
                           check(p, root)[0], 2))
        anchored = {"hooks": {"PreToolUse": [{"hooks": [
            {"type": "command", "command": 'bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/x.sh'}]}]}}
        p.write_text(json.dumps(anchored))
        file_cases.append(("an anchored command whose hook exists under ROOT passes", check(p, root)[0], 0))
        with tempfile.TemporaryDirectory() as td2:
            other = Path(td2)  # the same settings, judged against a root that has no hooks
            file_cases.append(("...and the SAME settings against a root without the hook is refused — "
                               "existence is read under the root given, not the repo's", check(p, other)[0], 1))
            (root / SETTINGS_REL).parent.mkdir(parents=True, exist_ok=True)
            (root / SETTINGS_REL).write_text(json.dumps(anchored))
            file_cases.append(("main() over a compliant world exits 0", main([], root=root), 0))
            (root / SETTINGS_REL).write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": "bash .claude/hooks/x.sh"}]}]}}))
            file_cases.append(("⭐ main() over the shipped defect exits 1", main([], root=root), 1))
            file_cases.append(("main() over a world with no settings file exits 2 (CANNOT RUN)",
                               main([], root=other), 2))
    for name, got, want in file_cases:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    total = len(cases) + len(file_cases)
    print(f"\n{total - failures}/{total} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    code, messages = check(root / SETTINGS_REL, root)
    if code == 0:
        print(f"ok — {SETTINGS_REL}: {messages[0]}")
        return 0
    label = "CANNOT RUN" if code == 2 else "RELATIVE HOOK PATH"
    print(f"{label} — {SETTINGS_REL}", file=sys.stderr)
    for m in messages:
        print(f"  {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())

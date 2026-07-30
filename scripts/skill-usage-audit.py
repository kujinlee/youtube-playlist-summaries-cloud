#!/usr/bin/env python3
"""Aggregate skill usage across every Claude Code session transcript.

Answers "which of my installed skills do I actually use?" so unused ones can be
trimmed and load-bearing ones kept. Companion to `session-skill-report.py`,
which reports a SINGLE session; this one sweeps all of them.

Three distinct signals, counted separately on purpose:

  invoked   Skill tool_use block            -- a deliberate choice, by me or auto-matched
  typed     user message starting "/name"   -- a deliberate choice, by you
  injected  SessionStart hook text          -- fires every session whether or not it is wanted

`injected` matters as much as `invoked`: a skill can shape every single session
without ever being invoked. superpowers:using-superpowers is the case in point --
zero invocations, but injected into every session by a SessionStart hook. Judging
it by invocations alone would say "unused, safe to remove" about the skill that
governs how every other skill gets picked.

KNOWN BLIND SPOTS -- read before trimming anything:
  1. Subagent activity is not in these transcripts (no isSidechain records exist),
     so a skill used INSIDE a dispatched subagent is invisible here. This project
     leans on subagent-driven-development, so review/TDD skills may be undercounted.
  2. Tool-triggered guidance is invisible. The Artifact tool requires loading
     `artifact-design` before writing a page; that shows as an invocation only
     because the Skill tool was called explicitly.
  3. A dormant skill is not necessarily a useless one -- some are internal helper
     contracts loaded by other skills (see codex:codex-cli-runtime), and some cover
     situations that simply have not come up yet.

Usage:
    python3 scripts/skill-usage-audit.py
    python3 scripts/skill-usage-audit.py --project youtube-playlist-summaries-cloud
    python3 scripts/skill-usage-audit.py --json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

HOME = Path.home()
PROJECTS_ROOT = HOME / ".claude" / "projects"
PLUGIN_CACHE = HOME / ".claude" / "plugins" / "cache"
SETTINGS = HOME / ".claude" / "settings.json"

# "/name" or "/name args" -- the lookahead stops pasted paths like /Users/foo
# from being mistaken for a slash command.
USER_SLASH_RE = re.compile(r"^/([\w:-]+)(?=\s|$)")
# Hook text naming a skill, e.g. 'superpowers:using-superpowers' skill
HOOK_SKILL_RE = re.compile(r"['\"]([\w-]+:[\w-]+)['\"]\s+skill", re.IGNORECASE)

# Slash commands built into the CLI -- commands, not skills.
BUILTIN_COMMANDS = {
    "compact", "clear", "help", "config", "init", "cost", "model", "resume",
    "context", "export", "doctor", "fast", "review", "login", "logout", "status",
}
# Skills bundled in the Claude Code binary; they have no directory to scan for.
BUILTIN_SKILLS = {
    "artifact-design", "artifact-capabilities", "dataviz", "claude-api", "run",
    "simplify", "update-config", "keybindings-help", "loop", "schedule",
    "fewer-permission-prompts", "claude-in-chrome", "security-review",
}


def load_enabled_plugins() -> tuple[set[str], set[str]]:
    """Return (enabled, disabled) plugin names from settings.json."""
    try:
        raw = json.loads(SETTINGS.read_text()).get("enabledPlugins", {})
    except (OSError, json.JSONDecodeError):
        return set(), set()
    enabled = {k.split("@")[0] for k, v in raw.items() if v}
    disabled = {k.split("@")[0] for k, v in raw.items() if not v}
    return enabled, disabled


def discover_installed(cwd: Path) -> dict[str, dict[str, Any]]:
    """Inventory every installed skill, keyed by its qualified name."""
    enabled, disabled = load_enabled_plugins()
    found: dict[str, dict[str, Any]] = {}

    # Plugin skills: cache/<marketplace>/<plugin>/<version>/skills/<name>/SKILL.md
    for skill_md in PLUGIN_CACHE.rglob("skills/*/SKILL.md"):
        parts = skill_md.parts
        try:
            i = parts.index("skills")
            plugin = parts[i - 2]
        except (ValueError, IndexError):
            continue
        name = skill_md.parent.name
        key = f"{plugin}:{name}"
        if plugin in disabled:
            state = "DISABLED"
        elif plugin in enabled:
            state = "enabled"
        else:
            # Cached but absent from settings.json -- e.g. installed outside the
            # plugin manager. Available, just not explicitly toggled on.
            state = "untracked"
        # A plugin can be cached at several versions; keep one row per skill.
        found.setdefault(key, {"key": key, "source": plugin, "bare": name, "state": state})

    # Personal and project skills: <root>/.claude/skills/<name>/SKILL.md
    for root, label in ((HOME, "personal(~/.claude)"), (cwd, "project(.claude)")):
        for skill_md in (root / ".claude" / "skills").glob("*/SKILL.md"):
            name = skill_md.parent.name
            found.setdefault(name, {"key": name, "source": label, "bare": name, "state": "enabled"})

    return found


def scan(project_filter: str | None) -> dict[str, Any]:
    """Sweep every transcript, tallying the three signals per skill."""
    invoked: dict[str, int] = defaultdict(int)
    typed: dict[str, int] = defaultdict(int)
    injected: dict[str, int] = defaultdict(int)
    last_seen: dict[str, str] = {}
    sessions = 0
    projects: set[str] = set()

    if not PROJECTS_ROOT.exists():
        return {"invoked": invoked, "typed": typed, "injected": injected,
                "last_seen": last_seen, "sessions": 0, "projects": projects}

    def mark(name: str, when: str) -> None:
        if when > last_seen.get(name, ""):
            last_seen[name] = when

    for transcript in PROJECTS_ROOT.glob("*/*.jsonl"):
        project = transcript.parent.name
        if project_filter and project_filter not in project:
            continue
        projects.add(project)
        sessions += 1

        for line in transcript.open(encoding="utf-8", errors="ignore"):
            # Cheap prefilter -- most lines mention none of the three signals.
            if '"Skill"' not in line and '"/' not in line and "SessionStart" not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            when = (record.get("timestamp") or "")[:10]
            message = record.get("message")

            if isinstance(message, dict):
                content = message.get("content")

                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "tool_use" and block.get("name") == "Skill":
                            name = str((block.get("input") or {}).get("skill") or "unknown")
                            invoked[name] += 1
                            mark(name, when)

                if record.get("type") == "user" and isinstance(content, str):
                    match = USER_SLASH_RE.match(content.strip())
                    if match:
                        name = match.group(1)
                        typed[name] += 1
                        mark(name, when)

            attachment = record.get("attachment")
            if isinstance(attachment, dict):
                hook = attachment.get("hookName") or attachment.get("hookEvent")
                if hook == "SessionStart":
                    blob = json.dumps(attachment, ensure_ascii=False)
                    names = set(HOOK_SKILL_RE.findall(blob))
                    if "using-superpowers" in blob:
                        names.add("superpowers:using-superpowers")
                    for name in names:
                        injected[name] += 1
                        mark(name, when)

    return {"invoked": invoked, "typed": typed, "injected": injected,
            "last_seen": last_seen, "sessions": sessions, "projects": projects}


def classify(name: str, installed: dict[str, dict[str, Any]]) -> tuple[str, str]:
    """Return (bucket, state) for a name seen in the transcripts."""
    if name in installed:
        return "skill", installed[name]["state"]
    if name in BUILTIN_SKILLS:
        return "skill", "built-in"
    if ":" in name:
        return "skill", "plugin (other)"
    if name in BUILTIN_COMMANDS:
        return "command", "built-in"
    return "unknown", "?"


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--project", help="only scan transcripts whose project dir matches this substring")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    cwd = Path.cwd()
    installed = discover_installed(cwd)
    data = scan(args.project)
    invoked, typed, injected = data["invoked"], data["typed"], data["injected"]
    last_seen = data["last_seen"]

    # Alias bare names onto their qualified form, so "brainstorming" and
    # "superpowers:brainstorming" are not counted as two different skills.
    bare_to_key = {}
    for key, meta in installed.items():
        bare_to_key.setdefault(meta["bare"], key)

    def canonical(name: str) -> str:
        return name if name in installed else bare_to_key.get(name, name)

    rows: dict[str, dict[str, Any]] = {}
    for signal, counter in (("invoked", invoked), ("typed", typed), ("injected", injected)):
        for name, count in counter.items():
            key = canonical(name)
            row = rows.setdefault(key, {"invoked": 0, "typed": 0, "injected": 0, "last": ""})
            row[signal] += count
            if last_seen.get(name, "") > row["last"]:
                row["last"] = last_seen.get(name, "")

    used_skills, commands, unknown = [], [], []
    for key, row in rows.items():
        bucket, state = classify(key, installed)
        entry = {"skill": key, "state": state, **row,
                 "total": row["invoked"] + row["typed"] + row["injected"]}
        (used_skills if bucket == "skill" else commands if bucket == "command" else unknown).append(entry)

    dormant = sorted(k for k in installed if k not in rows)

    if args.json:
        print(json.dumps({
            "sessions": data["sessions"], "projects": sorted(data["projects"]),
            "installed": len(installed), "used": used_skills,
            "commands": commands, "unknown": unknown, "dormant": dormant,
        }, indent=2))
        return

    used_skills.sort(key=lambda r: -r["total"])
    print(f"Scanned {data['sessions']} session transcripts across {len(data['projects'])} project(s)")
    print(f"Installed skills discovered: {len(installed)}\n")

    print("=" * 84)
    print("USED")
    print("=" * 84)
    print(f"{'invoked':>7} {'typed':>6} {'injected':>9}  {'last seen':10}  {'state':14}  skill")
    print("-" * 84)
    for r in used_skills:
        print(f"{r['invoked']:>7} {r['typed']:>6} {r['injected']:>9}  "
              f"{r['last'] or '?':10}  {r['state']:14}  {r['skill']}")

    if commands:
        print("\n  -- slash commands (not skills) --")
        for r in sorted(commands, key=lambda r: -r["total"]):
            print(f"{r['typed']:>7} {'':6} {'':9}  {r['last'] or '?':10}  {'command':14}  /{r['skill']}")

    if unknown:
        print("\n  -- unrecognised tokens (likely parse noise, not skills) --")
        for r in sorted(unknown, key=lambda r: -r["total"]):
            print(f"{r['total']:>7} {'':6} {'':9}  {r['last'] or '?':10}  {'?':14}  {r['skill']}")

    print()
    print("=" * 84)
    print(f"DORMANT -- never invoked, typed, or injected ({len(dormant)} of {len(installed)})")
    print("=" * 84)
    by_source: dict[str, list[str]] = defaultdict(list)
    for key in dormant:
        by_source[installed[key]["source"]].append(installed[key]["bare"])
    for source, names in sorted(by_source.items(), key=lambda kv: -len(kv[1])):
        sample = next(k for k in dormant if installed[k]["source"] == source)
        tag = "  [plugin DISABLED]" if installed[sample]["state"] == "DISABLED" else ""
        print(f"  {source}{tag} ({len(names)}): {', '.join(sorted(names))}")

    print()
    print("Before trimming, read the KNOWN BLIND SPOTS in this file's docstring --")
    print("subagent usage is invisible here, and some dormant skills are internal helpers.")


if __name__ == "__main__":
    main()

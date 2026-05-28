#!/usr/bin/env python3
"""Render a readable skill-usage report from a Claude Code session transcript."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SKILL_NAME_RE = re.compile(
    r"(?:^|\s|['\"])([\w-]+(?::[\w-]+)?)(?:['\"]| skill)",
    re.IGNORECASE,
)
HOOK_SKILL_RE = re.compile(
    r"['\"]([\w-]+:[\w-]+)['\"]\s+skill",
    re.IGNORECASE,
)
USER_SLASH_RE = re.compile(r"^/([\w:-]+(?:\s+.*)?)$")


@dataclass
class Event:
    index: int
    timestamp: str
    kind: str
    name: str
    detail: str = ""


@dataclass
class Report:
    session_id: str = ""
    cwd: str = ""
    git_branch: str = ""
    claude_version: str = ""
    transcript: Path | None = None
    events: list[Event] = field(default_factory=list)

    @property
    def counts(self) -> Counter[str]:
        return Counter(event.name for event in self.events if event.name)


def encode_project_path(cwd: str) -> str:
    return cwd.rstrip("/").replace("/", "-")


def resolve_transcript(
    *,
    transcript: Path | None,
    session_id: str | None,
    cwd: str | None,
) -> Path:
    if transcript:
        path = transcript.expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Transcript not found: {path}")
        return path

    if not session_id:
        raise ValueError("Provide --transcript or --session-id")

    projects_root = Path.home() / ".claude" / "projects"
    candidates: list[Path] = []

    if cwd:
        candidates.append(projects_root / encode_project_path(cwd) / f"{session_id}.jsonl")

    if projects_root.exists():
        candidates.extend(projects_root.glob(f"*/{session_id}.jsonl"))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"No transcript found for session {session_id}. "
        f"Tried: {', '.join(str(c) for c in candidates)}"
    )


def parse_timestamp(value: str | None) -> str:
    if not value:
        return "??:??:??"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def truncate(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def extract_hook_skills(text: str) -> list[str]:
    names: list[str] = []
    if "using-superpowers" in text or "superpowers:using-superpowers" in text:
        names.append("superpowers:using-superpowers")
    for match in HOOK_SKILL_RE.finditer(text):
        names.append(match.group(1))
    return names


def iter_message_blocks(record: dict[str, Any]) -> Iterable[dict[str, Any]]:
    message = record.get("message")
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                yield block
    elif isinstance(content, str):
        yield {"type": "text", "text": content}


def parse_transcript(path: Path) -> Report:
    report = Report(transcript=path)
    event_index = 0

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not report.session_id:
                report.session_id = str(record.get("sessionId") or path.stem)
            if not report.cwd:
                report.cwd = str(record.get("cwd") or "")
            if not report.git_branch:
                report.git_branch = str(record.get("gitBranch") or "")
            if not report.claude_version:
                report.claude_version = str(record.get("version") or "")

            timestamp = parse_timestamp(record.get("timestamp"))

            attachment = record.get("attachment")
            if isinstance(attachment, dict):
                hook_name = attachment.get("hookName") or attachment.get("hookEvent")
                if hook_name == "SessionStart":
                    blob = json.dumps(attachment, ensure_ascii=False)
                    for skill_name in extract_hook_skills(blob):
                        event_index += 1
                        report.events.append(
                            Event(
                                index=event_index,
                                timestamp=timestamp,
                                kind="hook-injected",
                                name=skill_name,
                                detail="SessionStart",
                            )
                        )

            if record.get("type") == "user":
                message = record.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        match = USER_SLASH_RE.match(content.strip())
                        if match:
                            event_index += 1
                            report.events.append(
                                Event(
                                    index=event_index,
                                    timestamp=timestamp,
                                    kind="user-slash",
                                    name=match.group(1).split()[0],
                                    detail=truncate(match.group(1)),
                                )
                            )

            for block in iter_message_blocks(record):
                block_type = block.get("type")
                if block_type == "tool_use" and block.get("name") == "Skill":
                    skill_input = block.get("input") or {}
                    skill_name = str(skill_input.get("skill") or "unknown")
                    args = skill_input.get("args")
                    detail = truncate(str(args)) if args else ""
                    event_index += 1
                    report.events.append(
                        Event(
                            index=event_index,
                            timestamp=timestamp,
                            kind="skill-tool",
                            name=skill_name,
                            detail=detail,
                        )
                    )
                elif block_type == "tool_use" and block.get("name") == "Task":
                    task_input = block.get("input") or {}
                    subagent = str(task_input.get("subagent_type") or "subagent")
                    description = truncate(str(task_input.get("description") or ""))
                    event_index += 1
                    report.events.append(
                        Event(
                            index=event_index,
                            timestamp=timestamp,
                            kind="subagent",
                            name=subagent,
                            detail=description,
                        )
                    )

    report.events = dedupe_events(report.events)
    return report


def dedupe_events(events: list[Event]) -> list[Event]:
    deduped: list[Event] = []
    seen: set[tuple[str, str, str]] = set()
    for event in events:
        key = (event.timestamp, event.kind, event.name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    for index, event in enumerate(deduped, start=1):
        event.index = index
    return deduped


def render_markdown(report: Report) -> str:
    lines: list[str] = []
    lines.append("# Session Skill Report")
    lines.append("")
    lines.append(f"- **Session:** `{report.session_id}`")
    if report.cwd:
        lines.append(f"- **Project:** `{report.cwd}`")
    if report.git_branch:
        lines.append(f"- **Branch:** `{report.git_branch}`")
    if report.claude_version:
        lines.append(f"- **Claude Code:** `{report.claude_version}`")
    if report.transcript:
        lines.append(f"- **Transcript:** `{report.transcript}`")
    lines.append("")

    if not report.events:
        lines.append("_No skill or slash-command activity found in this transcript._")
        return "\n".join(lines)

    lines.append("## Timeline")
    lines.append("")
    lines.append("| # | Time | Kind | Name | Detail |")
    lines.append("|---:|---|---|---|---|")
    for event in report.events:
        detail = event.detail.replace("|", "\\|")
        lines.append(
            f"| {event.index} | {event.timestamp} | {event.kind} | `{event.name}` | {detail} |"
        )

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for name, count in report.counts.most_common():
        lines.append(f"- `{name}`: {count}")

    return "\n".join(lines)


def render_text(report: Report) -> str:
    lines: list[str] = []
    lines.append("Session Skill Report")
    lines.append("=" * 72)
    lines.append(f"Session     : {report.session_id}")
    if report.cwd:
        lines.append(f"Project     : {report.cwd}")
    if report.git_branch:
        lines.append(f"Branch      : {report.git_branch}")
    if report.claude_version:
        lines.append(f"Claude Code : {report.claude_version}")
    if report.transcript:
        lines.append(f"Transcript  : {report.transcript}")
    lines.append("")

    if not report.events:
        lines.append("No skill or slash-command activity found.")
        return "\n".join(lines)

    lines.append("Timeline")
    lines.append("-" * 72)
    for event in report.events:
        detail = f" — {event.detail}" if event.detail else ""
        lines.append(
            f"{event.index:>3}. {event.timestamp}  [{event.kind:<14}]  {event.name}{detail}"
        )

    lines.append("")
    lines.append("Summary")
    lines.append("-" * 72)
    for name, count in report.counts.most_common():
        lines.append(f"  {count:>3}x  {name}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path, help="Path to a session .jsonl file")
    parser.add_argument("--session-id", help="Claude Code session id")
    parser.add_argument("--cwd", help="Project cwd used to locate the transcript")
    parser.add_argument(
        "--format",
        choices=("text", "markdown"),
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    try:
        transcript = resolve_transcript(
            transcript=args.transcript,
            session_id=args.session_id,
            cwd=args.cwd,
        )
        report = parse_transcript(transcript)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    output = render_markdown(report) if args.format == "markdown" else render_text(report)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

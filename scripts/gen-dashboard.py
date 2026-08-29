#!/usr/bin/env python3
"""Render the project dashboard from docs/dashboard-entries.md."""
from __future__ import annotations
import argparse
import datetime as _dt
import json
import pathlib
import subprocess
import tempfile
import html as _html
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TECH_MARKER = "<!--tech-->"
BLOCK = re.compile(r"^##\s*\S")


def _gate_module():
    """Load scripts/check-dashboard-entry.py for the grammar it owns.

    The dependency arrow points generator -> gate, never the reverse: a GATE
    must not import the thing it guards, but a page importing a gate is what
    keeps their readings identical by construction. Hyphenated filenames are
    not importable, so importlib is the only route.
    """
    import importlib.util, pathlib
    p = pathlib.Path(__file__).with_name("check-dashboard-entry.py")
    spec = importlib.util.spec_from_file_location("_dash_gate", p)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_GATE = _gate_module()          # the GRAMMAR is required to parse at all
header_error = _GATE.header_error
FLAG = _GATE.FLAG
HEADER = _GATE.HEADER


def _exemption_reader():
    """Resolved LAZILY, so a missing gate file degrades one SECTION rather than
    killing the page. Bound at import, hiding the gate raised FileNotFoundError
    before `no_entry_prs` could return its (None, why) — the falsifier the plan
    states was unreachable, and the whole dashboard would have failed to render
    over a section that is allowed to say "could not check"."""
    return _gate_module().exemption_reason

def parse_entries(text: str) -> list[dict]:
    """Split on column-0 '##' only. A malformed block is RETURNED with an
    error, never dropped — the page must show it in place (spec §6.2).

    `resolves` is a LIST: spec §6.2 says flags are "zero or more", and a
    second [resolved:] used to overwrite the first silently, clearing one item
    and leaving the other open forever with error=None.
    """
    blocks: list[list[str]] = []
    for line in text.split("\n"):
        if BLOCK.match(line):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    out: list[dict] = []
    seen: dict[str, int] = {}
    for b in blocks:
        entry = {"raw": "\n".join(b), "error": None, "needs_you": False, "resolves": [],
                 "date": None, "ordinal": 0, "id": None, "would_be_id": None,
                 "title": "", "plain": "", "tech": None}
        err = header_error(b[0])
        m = HEADER.match(b[0])
        if m is not None and _GATE.valid_date(m.group(1)):
            # The ordinal is claimed as soon as the DATE is known good — BEFORE
            # the flag check — so repairing a typo'd flag does not renumber the
            # entries after it and silently rebind a standing [resolved:].
            date = m.group(1)
            seen[date] = seen.get(date, 0) + 1
            entry["date"], entry["ordinal"] = date, seen[date]
            entry["id"] = f"{date}/{seen[date]}"
            for f in FLAG.findall(m.group(2)):
                if f == "needs-you":
                    entry["needs_you"] = True
                else:
                    entry["resolves"].append(f.split(":", 1)[1].strip())
        elif m is not None:
            # A block whose DATE is malformed never gets an id, so pass 2 could
            # not distinguish "no such entry" from "that entry exists and is
            # unparseable" — and sent the author hunting for a typo that was not
            # there. A bad date is the CANONICAL malformed entry (§6.2's own
            # example, and the one control D exercises), so it was precisely the
            # case the earlier three-way fix did not reach.
            raw_date = m.group(1)
            seen[raw_date] = seen.get(raw_date, 0) + 1
            entry["would_be_id"] = f"{raw_date}/{seen[raw_date]}"
        if err:
            entry["error"] = err
            out.append(entry)
            continue
        body = b[1:]
        cut = next((i for i, l in enumerate(body) if l.strip() == TECH_MARKER), None)
        plain_lines = body if cut is None else body[:cut]
        entry["tech"] = None if cut is None else "\n".join(body[cut + 1:]).strip()
        entry["title"] = next((l.strip() for l in plain_lines if l.strip()), "")
        entry["plain"] = "\n".join(plain_lines).strip()
        if not entry["title"]:
            entry["error"] = "no title line — the first line after the header is blank"
        out.append(entry)

    # PASS 2 — every [resolved:] must name an entry that exists.
    ids = {e["id"] for e in out if e["id"] and not e["error"]}
    for e in out:
        if e["error"]:
            continue
        for r in e["resolves"]:
            if r in ids:
                continue
            if not r:
                e["error"] = "[resolved:] with no entry id after it"
            elif any(o["id"] == r or o["would_be_id"] == r for o in out):
                e["error"] = (f"[resolved: {r}] names an entry that could not be "
                              f"parsed — fix that entry first")
            else:
                e["error"] = f"[resolved: {r}] names no entry in this file"
            break
    return out

def _pos(e: dict) -> tuple:
    return (e["date"] or "", e["ordinal"])


def unresolved(entries: list[dict]) -> list[dict]:
    """needs-you entries not cleared by a LATER [resolved: <id>] (spec §6.2)."""
    by_id = {e["id"]: e for e in entries if e["id"] and not e["error"]}
    cleared = set()
    for e in entries:
        if e["error"]:
            continue
        for r in e["resolves"]:
            t = by_id.get(r)
            if t is not None and _pos(e) > _pos(t):
                cleared.add(t["id"])
    return [e for e in entries
            if e["needs_you"] and not e["error"] and e["id"] not in cleared]


def bucket_days(dates: list[str], entries: list[dict], window: int, today: str) -> list[dict]:
    counts: dict[str, int] = {}
    for d in dates:
        counts[d] = counts.get(d, 0) + 1
    with_entry = {e["date"] for e in entries if not e["error"]}
    flagged = {e["date"] for e in unresolved(entries)}
    end = _dt.date.fromisoformat(today)
    out = []
    for i in range(window):
        d = (end - _dt.timedelta(days=i)).isoformat()
        out.append({"date": d, "commits": counts.get(d, 0),
                    "needs_you": d in flagged, "has_entry": d in with_entry})
    return out

def commit_dates(window: int) -> tuple[list[str] | None, str | None]:
    """Author dates on FIRST-PARENT HEAD. Returns (dates, None) or (None, why).

    `--first-parent` is named explicitly because spec §5 requires it: after a
    squash-merge a plain `git log` counts the branch's own commits too, so
    "commits" would mean two different things depending on how a PR landed —
    and the §9 alarm (a day with commits and no entry) is computed from this.

    §6.2's ref split: the CHART reads HEAD; the renderer reads the working tree.
    """
    try:
        r = subprocess.run(
            ["git", "log", "HEAD", "--first-parent", f"--since={window} days ago",
             "--date=short", "--pretty=%ad"],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run git: {exc}"
    if r.returncode != 0:
        return None, f"git log exited {r.returncode}: {r.stderr.strip()[:200]}"
    return [l for l in r.stdout.split("\n") if l.strip()], None


def _gh_json(args: list[str]) -> tuple[object | None, str | None]:
    """Run `gh` and parse its JSON. Never a bare [] on failure — "nothing" and
    "could not ask" must not look alike."""
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run gh: {exc}"
    if r.returncode != 0:
        return None, f"gh exited {r.returncode}: {r.stderr.strip()[:200]}"
    try:
        return json.loads(r.stdout or "[]"), None
    except json.JSONDecodeError as exc:
        return None, f"gh returned unparseable JSON: {exc}"


def open_prs() -> tuple[list[dict] | None, str | None]:
    data, err = _gh_json(["pr", "list", "--state", "open", "--json", "number,title"])
    if err:
        return None, err
    if not isinstance(data, list) or any(
            not isinstance(p, dict) or "number" not in p or "title" not in p for p in data):
        return None, "gh returned JSON in an unexpected shape"
    return data, None


def no_entry_prs(limit: int = 40) -> tuple[list[dict] | None, str | None]:
    """Merged PRs whose body declared `NO-ENTRY:`, newest first.

    SPEC §7 REQUIRES THIS TO BE DISPLAYED. Without it nothing counts exemptions,
    nobody can see "eleven of the last twelve branches skipped their entry", and
    the page goes on looking healthy while describing less and less.

    Reads the gate's own `exemption_reason`, so the page shows exactly the
    exemptions the gate granted. A display that disagrees with the gate is worse
    than none. Bounded at `limit`: an older exemption stops being shown.
    """
    try:
        reader = _exemption_reader()
    except Exception as exc:
        return None, f"could not load the gate's exemption reader: {exc}"
    data, err = _gh_json(["pr", "list", "--state", "merged", "--limit", str(limit),
                          "--json", "number,title,body,mergedAt"])
    if err:
        return None, err
    if not isinstance(data, list):
        return None, "gh returned JSON in an unexpected shape"
    out = []
    for p in data:
        if not isinstance(p, dict):
            return None, "gh returned JSON in an unexpected shape"
        reason = reader(p.get("body") or "")
        if reason:
            out.append({"number": p.get("number"), "title": p.get("title") or "",
                        "merged": (p.get("mergedAt") or "")[:10], "reason": reason})
    return out, None

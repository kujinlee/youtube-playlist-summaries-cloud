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

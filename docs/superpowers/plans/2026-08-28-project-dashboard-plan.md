# Project Dashboard Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local page at `http://127.0.0.1:7391/dashboard` showing what needs the user, what changed, and one chart of daily activity — plus the gate that makes the entries actually get written.

**Architecture:** Three pure-Python pieces on the server that already exists. `scripts/gen-dashboard.py` parses an append-only markdown store and renders a standing page; `scripts/check-dashboard-entry.py` is a CI ratchet that refuses a branch with no entry; a small change to `scripts/explainer-serve.py` makes `<details>` folds survive live reload. No new process, no new port, no new dependency.

**Tech Stack:** Python 3 standard library only (`argparse`, `re`, `datetime`, `subprocess`, `pathlib`). No pip installs. Rendering is hand-written HTML/CSS; page composition reuses `scripts/brief-compose.py`.

**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5, merged `c5fcb07`).
Section references below (§4, §5, §6.2, §7) are to that spec.

## Global Constraints

- **Python 3 standard library only.** No new dependency, no pip install, no npm.
- **Every script gets `--self-test`** with pure functions only, exiting non-zero on failure, matching `scripts/check-function-revokes.py:113` and `scripts/gen-goals-page.py:457`.
- **`"cannot run" is a FAILURE, never a pass`** (`CLAUDE.md`). Every derivation that can fail must render a distinct *could not tell* state, never a silent empty or a zero.
- **Never `$?` after a pipe** — it reports the last command's status. Use `PIPESTATUS` or avoid the pipe. Measured three times in this repo.
- **Anything longer than a line goes in a file** — `--body-file`, `git commit -F`, `--prompt-file`. A backtick inside a double-quoted bash string is command substitution.
- **The store is append-only.** Nothing edits or deletes an existing entry block; corrections are appended.
- **Bare citations are a defect.** Every path written into code comments or page output is repo-relative and complete.
- Branch + PR for every task group; **merging is a human gate**.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/dashboard-entries.md` | **Create.** The append-only store. Owned by humans and the skill, never rewritten by a script. |
| `scripts/gen-dashboard.py` | **Create.** Parse the store, derive activity and open PRs, render `~/explainers/dashboard.html`. |
| `scripts/check-dashboard-entry.py` | **Create.** The ratchet: a branch touching tracked files must add an entry block or declare `NO-ENTRY:`. |
| `scripts/explainer-serve.py` | **Modify** (`:556-580`). Persist `<details>` open state across live reload. |
| `scripts/check-explainer-delivery.py` | **Modify** (`:53`). Add `dashboard` to `PAGE_SKILLS`. |
| `.claude/skills/dashboard/SKILL.md` | **Create.** The skill that writes entries and delivers the page. |
| `.github/workflows/ci.yml` | **Modify.** Run both new `--self-test`s and the ratchet. |
| `tests/` | **Not used.** These are standalone scripts with built-in `--self-test`, following every existing `scripts/check-*.py`. |

**Why parsing and rendering live in one file.** `gen-goals-page.py` and `gen-backlog-page.py` both do parse-plus-render in a single script with pure parse functions and a `build()`. Splitting would break the established pattern for no gain at this size.

---

## Task 1: The entry store and its parser

**Files:**
- Create: `docs/dashboard-entries.md`
- Create: `scripts/gen-dashboard.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `parse_entries(text: str) -> list[dict]`. Each dict has keys `date` (`str`, `YYYY-MM-DD`), `ordinal` (`int`, 1-based within the date), `id` (`str`, `f"{date}/{ordinal}"`), `title` (`str`), `plain` (`str`), `tech` (`str | None`), `needs_you` (`bool`), `resolves` (`str | None`), `error` (`str | None`), `raw` (`str`). When `error` is non-None every other field except `raw` and `error` is unreliable and the renderer shows `raw`.

- [ ] **Step 1: Write the failing test**

Create `scripts/gen-dashboard.py` containing only this self-test block and a stub:

```python
#!/usr/bin/env python3
"""Render the project dashboard from docs/dashboard-entries.md.

    python3 scripts/gen-dashboard.py              # -> ~/explainers/dashboard.html
    python3 scripts/gen-dashboard.py --self-test  # pure functions only, no I/O
"""
from __future__ import annotations
import sys

def parse_entries(text: str) -> list[dict]:
    raise NotImplementedError

def _self_test() -> int:
    ok = fail = 0
    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")
    e = parse_entries("## 2026-08-28 [needs-you]\nFixed a thing.\n")
    case("one entry parsed", len(e), 1)
    case("date", e[0]["date"], "2026-08-28")
    case("id", e[0]["id"], "2026-08-28/1")
    case("title", e[0]["title"], "Fixed a thing.")
    case("needs_you", e[0]["needs_you"], True)
    case("no error", e[0]["error"], None)
    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0

if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else 0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `NotImplementedError` traceback, non-zero exit.

- [ ] **Step 3: Implement the parser**

Replace the `parse_entries` stub. Every rule below is from spec §6.2:

```python
import datetime as _dt
import re

HEADER = re.compile(r"^## (\S+)(.*)$")
FLAG = re.compile(r"\[(needs-you|resolved:\s*[^\]]+)\]")
TECH_MARKER = "<!--tech-->"

def _valid_date(s: str) -> bool:
    try:
        _dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False

def parse_entries(text: str) -> list[dict]:
    """Split on column-0 '## ' only. A malformed block is RETURNED with an
    error, never dropped — the page must show it in place (spec §6.2)."""
    blocks: list[list[str]] = []
    for line in text.split("\n"):
        if line.startswith("## "):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    out: list[dict] = []
    seen: dict[str, int] = {}
    for b in blocks:
        raw = "\n".join(b)
        entry = {"raw": raw, "error": None, "needs_you": False, "resolves": None,
                 "date": None, "ordinal": 0, "id": None, "title": "", "plain": "", "tech": None}
        m = HEADER.match(b[0])
        date = m.group(1) if m else ""
        if not _valid_date(date):
            entry["error"] = f"not a real calendar date: {date!r}"
            out.append(entry)
            continue
        rest = m.group(2)
        flags = FLAG.findall(rest)
        # An UNKNOWN flag is malformed, never ignored: a typo'd [needs-you]
        # would otherwise silently drop an item off the page's first block.
        leftover = FLAG.sub("", rest).strip()
        if leftover:
            entry["error"] = f"unrecognised text in header: {leftover!r}"
            out.append(entry)
            continue
        for f in flags:
            if f == "needs-you":
                entry["needs_you"] = True
            else:
                entry["resolves"] = f.split(":", 1)[1].strip()
        seen[date] = seen.get(date, 0) + 1
        entry["date"], entry["ordinal"] = date, seen[date]
        entry["id"] = f"{date}/{seen[date]}"
        body = b[1:]
        # Only a line that is EXACTLY the marker splits plain from tech.
        cut = next((i for i, l in enumerate(body) if l.strip() == TECH_MARKER), None)
        plain_lines = body if cut is None else body[:cut]
        entry["tech"] = None if cut is None else "\n".join(body[cut + 1:]).strip()
        entry["title"] = next((l.strip() for l in plain_lines if l.strip()), "")
        entry["plain"] = "\n".join(plain_lines).strip()
        out.append(entry)
    return out
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `6/6 passed`, exit 0.

- [ ] **Step 5: Add the malformed and edge cases**

Append to `_self_test` before the print:

```python
    bad = parse_entries("## 2026-02-30\nImpossible date.\n")
    case("bad date is an error", bad[0]["error"] is not None, True)
    case("bad date still returned", len(bad), 1)
    case("bad date keeps raw", "Impossible date." in bad[0]["raw"], True)

    typo = parse_entries("## 2026-08-28 [needs-yo]\nTypo flag.\n")
    case("unknown flag is an error", typo[0]["error"] is not None, True)

    two = parse_entries("## 2026-08-28\nFirst.\n## 2026-08-28\nSecond.\n")
    case("two entries same date", [x["id"] for x in two], ["2026-08-28/1", "2026-08-28/2"])

    tech = parse_entries("## 2026-08-28\nTitle.\nMore plain.\n<!--tech-->\nPR #1.\n")
    case("plain stops at marker", tech[0]["plain"], "Title.\nMore plain.")
    case("tech captured", tech[0]["tech"], "PR #1.")

    inline = parse_entries("## 2026-08-28\nI mention <!--tech--> inline.\n")
    case("inline marker is text", inline[0]["tech"], None)

    nested = parse_entries("## 2026-08-28\nTitle.\n<!--tech-->\n  ## indented heading\n")
    case("indented ## does not split", len(nested), 1)

    case("empty file", parse_entries(""), [])
    case("no entries yet", parse_entries("# Heading only\n"), [])

    res = parse_entries("## 2026-08-29 [resolved: 2026-08-28/1]\nDone.\n")
    case("resolves parsed", res[0]["resolves"], "2026-08-28/1")
```

- [ ] **Step 6: Run to verify all pass**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `19/19 passed`, exit 0. If "indented ## does not split" fails, the block splitter is matching indented lines — it must test `line.startswith("## ")` against the raw line, not a stripped one.

- [ ] **Step 7: Create the store with its first real entry**

Create `docs/dashboard-entries.md`:

```markdown
# Dashboard entries

Append-only. One `## YYYY-MM-DD` block per entry; newest at the end.
Nothing here is edited or deleted — corrections are appended.
Grammar: `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2.
Rendered by `scripts/gen-dashboard.py`; enforced by `scripts/check-dashboard-entry.py`.

## 2026-08-28
Started building the dashboard — a page that shows what changed while you were away.
<!--tech-->
Spec v5 merged as `c5fcb07` after three dual-adversarial review rounds, none of which converged.
Task 1 of `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`.
```

- [ ] **Step 8: Verify the real store parses**

Run:
```bash
python3 -c "
import pathlib, importlib.util
spec = importlib.util.spec_from_file_location('g', 'scripts/gen-dashboard.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
e = m.parse_entries(pathlib.Path('docs/dashboard-entries.md').read_text())
print(len(e), 'entries;', [x['error'] for x in e])
"
```
Expected: `1 entries; [None]`

- [ ] **Step 9: Commit**

```bash
git add scripts/gen-dashboard.py docs/dashboard-entries.md
git commit -F /tmp/msg-task1.txt
```

Write the message to a file first — the body contains backticks.

---

## Task 2: Derive activity and open pull requests

**Files:**
- Modify: `scripts/gen-dashboard.py`

**Interfaces:**
- Consumes: `parse_entries` from Task 1.
- Produces: `bucket_days(dates: list[str], entries: list[dict], window: int, today: str) -> list[dict]` — each dict has `date` (`str`), `commits` (`int`), `needs_you` (`bool`), `has_entry` (`bool`). And `unresolved(entries: list[dict]) -> list[dict]` returning entries flagged `needs_you` whose `id` is named by no later `resolves`.

- [ ] **Step 1: Write the failing tests**

Append to `_self_test`:

```python
    ents = parse_entries(
        "## 2026-08-26 [needs-you]\nA.\n"
        "## 2026-08-27\nB.\n"
        "## 2026-08-28 [resolved: 2026-08-26/1]\nC.\n")
    case("unresolved is empty after resolve", [x["id"] for x in unresolved(ents)], [])

    ents2 = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-27\nB.\n")
    case("unresolved before resolve", [x["id"] for x in unresolved(ents2)], ["2026-08-26/1"])

    days = bucket_days(["2026-08-28", "2026-08-28", "2026-08-26"], ents2, 3, "2026-08-28")
    case("window length", len(days), 3)
    case("newest first", days[0]["date"], "2026-08-28")
    case("commit count", days[0]["commits"], 2)
    case("zero-commit day present", days[1]["commits"], 0)
    case("entry with no commits is marked", days[1]["has_entry"], True)
    case("needs-you day is flagged", days[2]["needs_you"], True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `NameError: name 'unresolved' is not defined`.

- [ ] **Step 3: Implement both functions**

```python
def unresolved(entries: list[dict]) -> list[dict]:
    """needs-you entries not cleared by a later [resolved: <id>] (spec §6.2)."""
    cleared = {e["resolves"] for e in entries if e["resolves"]}
    return [e for e in entries
            if e["needs_you"] and not e["error"] and e["id"] not in cleared]

def bucket_days(dates: list[str], entries: list[dict], window: int, today: str) -> list[dict]:
    """One bucket per calendar day, newest first, `window` days ending at `today`.

    `dates` is one string per commit. A day with an entry and zero commits is
    still returned with commits=0 — the spec requires it to render a marked
    zero-height bar rather than vanish (§6.1)."""
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `26/26 passed`, exit 0.

- [ ] **Step 5: Add the impure collectors, kept out of the self-test**

```python
import subprocess

def commit_dates(window: int) -> tuple[list[str] | None, str | None]:
    """Author dates on first-parent HEAD. Returns (dates, None) or (None, why).

    first-parent is named explicitly: after squash-merges, plain `git log`
    counts differently and 'commits' would be ambiguous (spec §5)."""
    try:
        r = subprocess.run(
            ["git", "log", "--first-parent", f"--since={window} days ago",
             "--date=short", "--pretty=%ad"],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run git: {exc}"
    if r.returncode != 0:
        return None, f"git log exited {r.returncode}: {r.stderr.strip()[:200]}"
    return [l for l in r.stdout.split("\n") if l.strip()], None

def open_prs() -> tuple[list[dict] | None, str | None]:
    """Open PRs via gh. Returns (prs, None) or (None, why) — never a bare []
    on failure, because 'nothing open' and 'could not ask' must not look alike."""
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number,title"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run gh: {exc}"
    if r.returncode != 0:
        return None, f"gh exited {r.returncode}: {r.stderr.strip()[:200]}"
    import json
    try:
        return json.loads(r.stdout or "[]"), None
    except json.JSONDecodeError as exc:
        return None, f"gh returned unparseable JSON: {exc}"
```

- [ ] **Step 6: Verify both against the real repo**

Run:
```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('g','scripts/gen-dashboard.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
d, err = m.commit_dates(14); print('dates:', len(d) if d else None, 'err:', err)
p, err2 = m.open_prs(); print('prs:', len(p) if p is not None else None, 'err:', err2)
"
```
Expected: a non-zero date count and `err: None`. `prs: 0 err: None` is correct when nothing is open — the distinction from failure is `err`.

- [ ] **Step 7: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -F /tmp/msg-task2.txt
```

---

## Task 3: Render the page

**Files:**
- Modify: `scripts/gen-dashboard.py`

**Interfaces:**
- Consumes: `parse_entries`, `unresolved`, `bucket_days`, `commit_dates`, `open_prs`.
- Produces: `build(entries, days, prs, pr_error, git_error, window) -> str` returning a complete HTML fragment (a `<title>`, one `<style>`, then body markup) suitable for `scripts/brief-compose.py --content`.

- [ ] **Step 1: Write the failing tests**

Append to `_self_test`:

```python
    ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n<!--tech-->\nPR #1.\n")
    d3 = bucket_days(["2026-08-28"], ents3, 2, "2026-08-28")
    html = build(ents3, d3, [], None, None, 2)
    case("needs-you surfaces", "Decide the thing." in html, True)
    case("tech is behind a fold", "<details" in html, True)
    case("tech labelled", "technical detail" in html.lower(), True)

    html_empty = build([], bucket_days([], [], 2, "2026-08-28"), [], None, None, 2)
    case("empty says nothing needs you", "Nothing needs you" in html_empty, True)
    case("empty says no entries yet", "no entries yet" in html_empty.lower(), True)

    html_err = build([], bucket_days([], [], 2, "2026-08-28"), None, "gh exploded", None, 2)
    case("gh failure is NOT 'nothing needs you'", "Nothing needs you" in html_err, False)
    case("gh failure says could not tell", "could not tell" in html_err.lower(), True)

    bad3 = parse_entries("## 2026-99-99\nBroken.\n")
    html_bad = build(bad3, bucket_days([], bad3, 2, "2026-08-28"), [], None, None, 2)
    case("malformed rendered in place", "could not parse" in html_bad.lower(), True)
    case("malformed keeps its raw text", "Broken." in html_bad, True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `NameError: name 'build' is not defined`.

- [ ] **Step 3: Implement `build`**

```python
import html as _html

def _bar(day: dict, tallest: int) -> str:
    h = 4 if day["commits"] == 0 else max(6, round(48 * day["commits"] / max(tallest, 1)))
    cls = "bar needs" if day["needs_you"] else "bar"
    mark = " ●" if day["has_entry"] and day["commits"] == 0 else ""
    label = (f'{day["date"]}: {day["commits"]} commits'
             f'{", needs you" if day["needs_you"] else ""}'
             f'{", entry with no commits" if mark else ""}')
    return (f'<a class="{cls}" href="#d-{day["date"]}" style="height:{h}px" '
            f'title="{_html.escape(label)}" aria-label="{_html.escape(label)}">'
            f'<span class="vh">{mark}</span></a>')

def build(entries, days, prs, pr_error, git_error, window) -> str:
    need = unresolved(entries)
    # "could not tell" is NOT "nothing needs you" — CLAUDE.md's cannot-run rule.
    if pr_error:
        needs_html = (f'<p class="unknown">I could not tell whether anything needs you — '
                      f'{_html.escape(pr_error)}</p>')
    elif not need and not prs:
        needs_html = '<p class="none">Nothing needs you.</p>'
    else:
        rows = [f'<li>{_html.escape(e["title"])} '
                f'<span class="when">{e["date"]}</span></li>' for e in need]
        rows += [f'<li>Pull request #{p["number"]} — {_html.escape(p["title"])}'
                 f' <span class="when">open</span></li>' for p in (prs or [])]
        needs_html = "<ul class=\"needs\">" + "".join(rows) + "</ul>"

    tallest = max([d["commits"] for d in days], default=0)
    chart = ("".join(_bar(d, tallest) for d in reversed(days))
             if not git_error else
             f'<p class="unknown">Could not read the git history — {_html.escape(git_error)}</p>')

    if not entries:
        entries_html = ('<p class="none">No entries yet. They live in '
                        '<code>docs/dashboard-entries.md</code>.</p>')
    else:
        parts = []
        for e in sorted(entries, key=lambda x: (x["date"] or "", x["ordinal"]), reverse=True):
            if e["error"]:
                parts.append(
                    f'<article class="entry broken" id="d-{_html.escape(e["date"] or "?")}">'
                    f'<p class="err">Could not parse this entry — {_html.escape(e["error"])}</p>'
                    f'<pre>{_html.escape(e["raw"])}</pre></article>')
                continue
            tech = ("" if not e["tech"] else
                    f'<details><summary>Raw technical detail</summary>'
                    f'<pre>{_html.escape(e["tech"])}</pre></details>')
            flag = ' <span class="flag">needs you</span>' if e["needs_you"] else ""
            parts.append(
                f'<article class="entry" id="d-{e["date"]}">'
                f'<h3>{_html.escape(e["date"])}{flag}</h3>'
                f'<p class="title">{_html.escape(e["title"])}</p>'
                f'<details><summary>What this means</summary>'
                f'<p>{_html.escape(e["plain"])}</p></details>{tech}</article>')
        entries_html = "".join(parts)

    return f"""<title>Project dashboard</title>
<style>
:root{{--ink:#1b2024;--fg3:#6b7780;--rule:#d8d6ce;--bg:#f7f8fa;--panel:#fff;
--need:#9c5d0e;--need-bg:#f7ebd9;--ok:#2e6349;--err:#8e3627;--err-bg:#f5e3df;
--mono:ui-monospace,SFMono-Regular,Menlo,monospace}}
@media(prefers-color-scheme:dark){{:root{{--ink:#e6e7e3;--fg3:#8b959b;--rule:#2c343a;
--bg:#14181b;--panel:#1b2125;--need:#e0a050;--need-bg:#2c2317;--ok:#6fb894;
--err:#d98873;--err-bg:#2a1a16}}}}
body{{background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;
line-height:1.6;margin:0;font-variant-numeric:tabular-nums}}
.shell{{max-width:820px;margin:0 auto;padding:32px 20px 80px}}
h2{{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;
color:var(--fg3);border-bottom:1px solid var(--rule);padding-bottom:8px;margin:44px 0 16px}}
.none{{color:var(--ok);font-weight:600}}
.unknown{{color:var(--err);background:var(--err-bg);padding:10px 14px;border-radius:4px}}
ul.needs{{list-style:none;padding:0}} ul.needs li{{background:var(--need-bg);
border-left:3px solid var(--need);padding:10px 14px;margin-bottom:8px;border-radius:0 4px 4px 0}}
.when{{font-family:var(--mono);font-size:11px;color:var(--fg3)}}
.chart{{display:flex;align-items:flex-end;gap:4px;height:56px;padding:8px;
background:var(--panel);border:1px solid var(--rule);border-radius:4px;overflow-x:auto}}
.bar{{flex:1;min-width:8px;background:var(--ok);border-radius:2px 2px 0 0;display:block}}
.bar.needs{{background:var(--need)}}
.vh{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
.entry{{background:var(--panel);border:1px solid var(--rule);border-radius:4px;
padding:14px 18px;margin-bottom:10px}}
.entry.broken{{border-color:var(--err);background:var(--err-bg)}}
.entry h3{{font-family:var(--mono);font-size:12px;color:var(--fg3);margin:0 0 6px}}
.entry .title{{margin:0;font-weight:600}}
.flag{{color:var(--need);font-weight:700}}
.err{{color:var(--err);font-weight:600;margin:0 0 8px}}
details{{margin-top:10px}} summary{{cursor:pointer;color:var(--fg3);font-size:14px}}
pre{{white-space:pre-wrap;font-family:var(--mono);font-size:12.5px;overflow-x:auto}}
:focus-visible{{outline:2px solid var(--need);outline-offset:2px}}
</style>
<div class="shell">
<h1>Project dashboard</h1>
<h2>What needs you</h2>{needs_html}
<h2>The last {window} days</h2><div class="chart">{chart}</div>
<h2>What changed</h2>{entries_html}
<h2>Elsewhere</h2><ul>
<li><a href="/goals">Goals</a></li><li><a href="/backlog-table">Backlog</a></li>
<li><a href="/latest">Newest briefing</a></li><li><a href="/">All pages</a></li></ul>
</div>"""
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `35/35 passed`, exit 0.

- [ ] **Step 5: Wire up `main` and write the page**

```python
import argparse, pathlib

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--window", type=int, default=14)
    ap.add_argument("--store", default="docs/dashboard-entries.md")
    ap.add_argument("--out", default=str(pathlib.Path.home() / "explainers" / "dashboard.html"))
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    store = pathlib.Path(a.store)
    entries = parse_entries(store.read_text(encoding="utf-8")) if store.exists() else []
    dates, git_error = commit_dates(a.window)
    prs, pr_error = open_prs()
    today = _dt.date.today().isoformat()
    days = bucket_days(dates or [], entries, a.window, today)
    frag = build(entries, days, prs, pr_error, git_error, a.window)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(frag, encoding="utf-8")
    print(f"wrote {out}  ({len(entries)} entries, window {a.window})")
    if git_error:
        print(f"  ⚠ git: {git_error}")
    if pr_error:
        print(f"  ⚠ gh: {pr_error}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Delete the old `if __name__` block from Task 1.

- [ ] **Step 6: Generate, compose and look at it**

```bash
python3 scripts/gen-dashboard.py --out /tmp/dash-fragment.html
python3 scripts/brief-compose.py --content /tmp/dash-fragment.html \
  --slug dashboard --title "Project dashboard"
python3 scripts/explainer-serve.py
```

⚠ `brief-compose.py` writes a **dated** filename. The dashboard must be a **standing** page — an undated name, so it is excluded from `/latest` (`scripts/explainer-serve.py:35-49`). Rename:

```bash
mv ~/explainers/*-brief-dashboard.html ~/explainers/dashboard.html
```

Then open `http://127.0.0.1:7391/dashboard` and confirm: the entry from Task 1 appears, its fold opens, the chart has bars, and `/latest` still points at the newest *briefing*, not at the dashboard.

- [ ] **Step 7: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -F /tmp/msg-task3.txt
```

---

## Task 4: The gate — an entry cannot be forgotten

**Files:**
- Create: `scripts/check-dashboard-entry.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: nothing (independent of `gen-dashboard.py` on purpose — a gate that imports the thing it guards fails when that thing is broken).
- Produces: `verdict(changed: list[str], added_entry: bool, pr_body: str) -> tuple[int, str]` returning `(exit_code, reason)`. `0` = pass, `1` = refuse.

- [ ] **Step 1: Write the failing test**

Create `scripts/check-dashboard-entry.py`:

```python
#!/usr/bin/env python3
"""Refuse a branch that changes tracked files and records no dashboard entry.

    python3 scripts/check-dashboard-entry.py             # against origin/master..HEAD
    python3 scripts/check-dashboard-entry.py --self-test

WHY THIS EXISTS. Through spec v4 the dashboard's entries were voluntary, and the
spec conceded they would be skipped exactly when busy — so the answer to the
user's rank-1 problem rested on discipline. docs/dev-process.md says: before
adding a rule, ask whether it can be a script. This is that script.
"""
from __future__ import annotations
import sys

EXEMPT_PREFIXES = ("docs/reviews/", "docs/dashboard-entries.md")
NO_ENTRY = "NO-ENTRY:"

def verdict(changed: list[str], added_entry: bool, pr_body: str) -> tuple[int, str]:
    raise NotImplementedError

def _self_test() -> int:
    ok = fail = 0
    def case(name, got, want):
        nonlocal ok, fail
        if got == want: ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")
    case("code change with no entry is refused", verdict(["lib/x.ts"], False, "")[0], 1)
    case("code change with entry passes", verdict(["lib/x.ts"], True, "")[0], 0)
    case("NO-ENTRY declaration passes", verdict(["lib/x.ts"], False, "NO-ENTRY: typo fix")[0], 0)
    case("NO-ENTRY without a reason is refused", verdict(["lib/x.ts"], False, "NO-ENTRY:")[0], 1)
    case("review-only branch is exempt", verdict(["docs/reviews/r1.md"], False, "")[0], 0)
    case("entry-only branch is exempt", verdict(["docs/dashboard-entries.md"], False, "")[0], 0)
    case("no changes at all passes", verdict([], False, "")[0], 0)
    case("mixed exempt and real is refused", verdict(["docs/reviews/r.md","lib/x.ts"], False, "")[0], 1)
    case("refusal explains itself", "entry" in verdict(["lib/x.ts"], False, "")[1].lower(), True)
    case("NO-ENTRY reason is echoed", "typo fix" in verdict(["lib/x.ts"], False, "NO-ENTRY: typo fix")[1], True)
    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0

if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-dashboard-entry.py --self-test`
Expected: `NotImplementedError`.

- [ ] **Step 3: Implement `verdict`**

```python
def verdict(changed: list[str], added_entry: bool, pr_body: str) -> tuple[int, str]:
    real = [p for p in changed if not p.startswith(EXEMPT_PREFIXES)]
    if not real:
        return 0, "no tracked files changed outside the exempt paths"
    if added_entry:
        return 0, "an entry block was added"
    for line in pr_body.split("\n"):
        s = line.strip()
        if s.startswith(NO_ENTRY):
            reason = s[len(NO_ENTRY):].strip()
            if reason:
                return 0, f"exempted by declaration — {reason}"
            return 1, f"{NO_ENTRY} was declared with no reason after it"
    return 1, (f"{len(real)} tracked file(s) changed and no entry was added to "
               f"docs/dashboard-entries.md. Add a '## YYYY-MM-DD' block describing "
               f"the change in plain words, or put 'NO-ENTRY: <reason>' in the PR body.")
```

- [ ] **Step 4: Run to verify all pass**

Run: `python3 scripts/check-dashboard-entry.py --self-test`
Expected: `10/10 passed`, exit 0.

- [ ] **Step 5: Add the git collector and `main`**

```python
import argparse, subprocess

def collect(base: str) -> tuple[list[str], bool, str | None]:
    """(changed paths, whether an entry block was added, error).
    Never `$?` after a pipe — this repo has measured that reporting the wrong
    command's status three times."""
    try:
        names = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                               capture_output=True, text=True, timeout=20)
        patch = subprocess.run(["git", "diff", "-U0", f"{base}...HEAD",
                                "--", "docs/dashboard-entries.md"],
                               capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], False, f"could not run git: {exc}"
    if names.returncode != 0:
        return [], False, f"git diff exited {names.returncode}: {names.stderr.strip()[:200]}"
    changed = [l for l in names.stdout.split("\n") if l.strip()]
    added = any(l.startswith("+## ") for l in patch.stdout.split("\n"))
    return changed, added, None

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--pr-body-file", default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    changed, added, err = collect(a.base)
    if err:
        # cannot run is a FAILURE, never a pass.
        print(f"CANNOT RUN — {err}\nTreat this as NOT CHECKED.")
        return 2
    body = ""
    if a.pr_body_file:
        import pathlib
        p = pathlib.Path(a.pr_body_file)
        body = p.read_text(encoding="utf-8") if p.exists() else ""
    code, reason = verdict(changed, added, body)
    print(("ok — " if code == 0 else "REFUSED — ") + reason)
    return code

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Delete the Task-4 Step-1 `if __name__` block.

- [ ] **Step 6: Prove it refuses, then prove it passes**

```bash
python3 scripts/check-dashboard-entry.py --base origin/master; echo "rc=$?"
```
On this branch, which changed scripts and added an entry in Task 1, expect `ok` and `rc=0`.

Now falsify it — the check is worthless if it cannot go red:

```bash
git stash push docs/dashboard-entries.md
python3 scripts/check-dashboard-entry.py --base origin/master; echo "rc=$?"
git stash pop
```
Expected: `REFUSED` and `rc=1`. **If this prints `ok`, the gate does not work — stop and fix it.**

- [ ] **Step 7: Wire into CI**

In `.github/workflows/ci.yml`, after the `check-function-revokes` steps:

```yaml
      - name: gen-dashboard self-test
        run: python3 scripts/gen-dashboard.py --self-test

      - name: check-dashboard-entry self-test
        run: python3 scripts/check-dashboard-entry.py --self-test
```

Do **not** run the ratchet itself in CI yet — it needs the PR body, and wiring that is Task 6.

- [ ] **Step 8: Commit**

```bash
git add scripts/check-dashboard-entry.py .github/workflows/ci.yml
git commit -F /tmp/msg-task4.txt
```

---

## Task 5: Folds survive live reload

**Files:**
- Modify: `scripts/explainer-serve.py:556-580`

**Interfaces:**
- Consumes: nothing.
- Produces: no Python API. Behavioural: after the injected client reloads a page, every `<details open>` is still open.

- [ ] **Step 1: Confirm it is broken first**

```bash
python3 scripts/explainer-serve.py
open http://127.0.0.1:7391/dashboard
```
Open a fold. Then `touch ~/explainers/dashboard.html`. The page reloads and **the fold closes**. Record that — a fix for a bug you have not reproduced is a guess.

- [ ] **Step 2: Extend the injected reload client**

In `RELOAD_JS`, beside the existing scroll persistence, add:

```javascript
  var DKEY = 'explainer-details:' + here;
  function saveDetails() {
    try {
      var open = [];
      document.querySelectorAll('details').forEach(function (d, i) {
        if (d.open) open.push(d.id || String(i));
      });
      sessionStorage.setItem(DKEY, JSON.stringify(open));
    } catch (e) {}
  }
  function restoreDetails() {
    try {
      var raw = sessionStorage.getItem(DKEY);
      if (!raw) return;
      sessionStorage.removeItem(DKEY);
      var open = JSON.parse(raw);
      document.querySelectorAll('details').forEach(function (d, i) {
        if (open.indexOf(d.id || String(i)) !== -1) d.open = true;
      });
    } catch (e) {}
  }
  restoreDetails();
```

Call `saveDetails()` immediately before the existing `sessionStorage.setItem(KEY, ...)` scroll save, in the same place the reload is triggered.

- [ ] **Step 3: Add self-test rows**

Beside the two existing reload-client cases in `_self_test`:

```python
        case("reload client persists details state",
             lambda: "explainer-details:" in RELOAD_JS and "saveDetails" in RELOAD_JS)
        case("reload client restores details state",
             lambda: "restoreDetails()" in RELOAD_JS)
```

- [ ] **Step 4: Run the self-test**

Run: `python3 scripts/explainer-serve.py --self-test`
Expected: all pass, exit 0, with two more cases than before.

- [ ] **Step 5: Verify the actual behaviour, not the markup**

Restart the server, open the dashboard, open **two** folds, `touch ~/explainers/dashboard.html`, and confirm **both are still open** after the reload.

⚠ Check `document.hidden` first. A backgrounded tab has no geometry and reports false results — measured 2026-08-28, a probe reported "0 of 9 reachable" purely because the tab was hidden.

- [ ] **Step 6: Commit**

```bash
git add scripts/explainer-serve.py
git commit -F /tmp/msg-task5.txt
```

---

## Task 6: The skill, registration, and the regen hook

**Files:**
- Create: `.claude/skills/dashboard/SKILL.md`
- Modify: `scripts/check-explainer-delivery.py:53`
- Create: `.claude/hooks/regen-dashboard.sh`

**Interfaces:**
- Consumes: everything above.
- Produces: the `/dashboard` skill.

- [ ] **Step 1: Register the skill in `PAGE_SKILLS`**

`scripts/check-explainer-delivery.py:53`:

```python
PAGE_SKILLS = ["explain-diff", "brief", "explain-findings", "explain-topic", "dashboard"]
```

⚠ **This check cannot enforce its own list** — it inspects only skills already on it, so an absent one is invisible and it exits green. Verified. This step is manual and ungated; that is why it is a numbered step rather than an assumption.

- [ ] **Step 2: Write the skill**

Create `.claude/skills/dashboard/SKILL.md`:

```markdown
---
name: dashboard
description: Update and open the project dashboard — what needs the user, what changed, and one chart. Use when the user asks for the dashboard, says "what changed", "catch me up", or types /dashboard. Also use after finishing a unit of work, to record the entry the gate requires.
---

# Dashboard

**Announce at start:** "Using the dashboard skill."

## 1. Write the entry FIRST

Append one block to `docs/dashboard-entries.md`. Never edit an existing block.

    ## YYYY-MM-DD [needs-you]
    One plain sentence. What happened, in words the user already knows.
    <!--tech-->
    Commit SHAs, file paths, exact commands.

- `[needs-you]` **only** when a decision is genuinely waiting on the human.
- Clear an earlier one by appending a later entry with `[resolved: YYYY-MM-DD/N]`.
- The title line is what the user reads. No jargon, no abbreviations they have not
  seen defined. The technical fold is where identifiers belong.
- Grammar: `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2.

## 2. Regenerate and deliver

    python3 scripts/gen-dashboard.py --out /tmp/dash-fragment.html
    python3 scripts/brief-compose.py --content /tmp/dash-fragment.html \
      --slug dashboard --title "Project dashboard"
    mv ~/explainers/*-brief-dashboard.html ~/explainers/dashboard.html

The undated filename is required: it makes this a **standing page**, excluded from
`/latest` so regenerating it does not steal the newest-briefing bookmark
(`scripts/explainer-serve.py:35-49`).

**For serving, the question tray, arming the push loop, and verifying the page
before handing it over, follow `.agents/skills/shared/explainer-delivery.md`.**
Cite it; never restate it.

## 3. Deliver the URL

    http://127.0.0.1:7391/dashboard

Say in one line what changed since they last looked.
```

- [ ] **Step 3: Verify the delivery check still passes**

Run: `python3 scripts/check-explainer-delivery.py`
Expected: exit 0. If it fails saying the skill restates the delivery loop, the skill body is repeating commands it should be citing — remove them.

- [ ] **Step 4: Add the regen hook**

Create `.claude/hooks/regen-dashboard.sh`, modelled on `.claude/hooks/regen-goals-page.sh`, firing when `docs/dashboard-entries.md` is written. **Exit 0 unconditionally** — a page regeneration must never fail a turn.

- [ ] **Step 5: Full verification**

```bash
python3 scripts/gen-dashboard.py --self-test
python3 scripts/check-dashboard-entry.py --self-test
python3 scripts/explainer-serve.py --self-test
python3 scripts/check-explainer-delivery.py
python3 scripts/check-docs.py
```
All expected rc=0. Check each separately — never `$?` after a pipe.

- [ ] **Step 6: Commit and open the PR**

```bash
git add .claude/skills/dashboard/SKILL.md scripts/check-explainer-delivery.py .claude/hooks/regen-dashboard.sh
git commit -F /tmp/msg-task6.txt
git push -u origin <branch>
gh pr create --title "..." --body-file /tmp/pr-body.md
```

**Merging is a human gate. Do not merge.**

---

## Self-Review

**Spec coverage.** §4 what-needs-you → Task 3 Step 3. §5 the chart → Tasks 2–3. §6.1 rendered once → Task 3. §6.2 grammar → Task 1 (every row has a case). §7 the gate → Task 4. §8 build split → Tasks 1–4, 6. §9 checks → Tasks 1, 4, 5. §10.1 folds → Task 5. §10.2 store created → Task 1 Step 7. §10.3 `PAGE_SKILLS` → Task 6 Step 1. §10.4 `gh` failure → Task 2 Step 5 + Task 3.

**Gaps, stated rather than hidden:**
- §5's *"control to widen the window"* is a `--window` **argument**, not an in-page control. A reader cannot widen it from the browser. That is a real shortfall against the spec and belongs in the PR description as known, not silently absent.
- §9's affordance probe is inherited from `explainer-delivery.md` §5b rather than restated; Task 6 Step 2 cites it.

**Type consistency.** `parse_entries` returns dicts with `id`/`date`/`ordinal`/`needs_you`/`resolves`/`error`/`raw`/`title`/`plain`/`tech`; `unresolved` and `bucket_days` read only those keys; `build` reads only those plus `bucket_days`' `commits`/`has_entry`. `verdict` in Task 4 shares no types with `gen-dashboard.py` by design.

**Placeholders:** none. Every code step carries the code.

# Project Dashboard Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local page at `http://127.0.0.1:7391/dashboard` showing what needs the user, what changed, and one chart of daily activity — plus the gate that makes the entries actually get written.

**Architecture:** Three pure-Python pieces on the server that already exists. `scripts/gen-dashboard.py` parses an append-only markdown store and renders a standing page; `scripts/check-dashboard-entry.py` is a CI ratchet that refuses a branch with no entry; a small change to `scripts/explainer-serve.py` makes `<details>` folds survive live reload. No new process, no new port, no new dependency.

**Tech Stack:** Python 3 standard library only (`argparse`, `re`, `datetime`, `subprocess`, `pathlib`). No pip installs. Rendering is hand-written HTML/CSS; page composition reuses `scripts/brief-compose.py`.

**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5, merged `c5fcb07`).
Section references below (§4, §5, §6.2, §7) are to that spec.

**Version: v2** — folds in round 1 of the dual adversarial plan review
(`docs/reviews/plan-project-dashboard-r1-codex.md`, `…-r1-claude.md`; both **NOT CONVERGED**,
3 Blocking + 3 High + 3 Medium + 1 Low and 3 Blocking + 5 High + 8 Medium + 7 Low respectively).
Both halves **executed** every Python block in v1 before judging it, which is why they found
defects three prose rounds on the spec did not. What changed, and why, is listed under
*What v2 changed* at the end.

## Global Constraints

- **Python 3 standard library only.** No new dependency, no pip install, no npm.
- **Every script gets `--self-test`** with pure functions only, exiting non-zero on failure, matching `scripts/check-function-revokes.py:113` and `scripts/gen-goals-page.py:457`.
- **`"cannot run" is a FAILURE, never a pass`** (`CLAUDE.md`). Every derivation that can fail must render a distinct *could not tell* state, never a silent empty or a zero.
- **Never `$?` after a pipe** — it reports the last command's status. Use `PIPESTATUS` or avoid the pipe. Measured three times in this repo.
- **Anything longer than a line goes in a file** — `--body-file`, `git commit -F`, `--prompt-file`. A backtick inside a double-quoted bash string is command substitution.
- **The store is append-only.** Nothing edits or deletes an existing entry block; corrections are appended.
- **Bare citations are a defect.** Every path written into code comments or page output is repo-relative and complete.
- **Never write an expected self-test COUNT.** v1 said `19/19` where the truth was `18/18`, and an
  implementer following its own TDD loop would have stopped to hunt for a case that does not exist.
  A count in a plan is a claim about a number that moves every time a case is added. Every "run the
  self-test" step below asserts **exit 0 and no `[FAIL]` lines** instead. If a step names a count
  anywhere, that is a defect in this plan, not in the code.
- **A falsifier must be shown to FIRE.** v1's Task 4 falsifier could not fail — `git stash push` on
  a committed file is a no-op — and the plan told the implementer to read its success as failure.
  Every step below that claims to falsify something states the observation that makes it go red,
  and the implementer must see red before proceeding. This is `docs/portable-practices.md` §17.
- Branch + PR for every task group; **merging is a human gate**.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/dashboard-entries.md` | **Create.** The append-only store. Owned by humans and the skill, never rewritten by a script. |
| `scripts/gen-dashboard.py` | **Create.** Parse the store, derive activity, open PRs and recorded `NO-ENTRY:` exemptions, then **compose and write** `~/explainers/dashboard.html` via `brief-compose.py`. |
| `scripts/check-dashboard-entry.py` | **Create.** The ratchet: a branch touching tracked files must add an entry block or declare `NO-ENTRY:`. |
| `scripts/explainer-serve.py` | **Modify** (`:556-580`). Persist `<details>` open state across live reload. |
| `scripts/check-explainer-delivery.py` | **Modify** (`:53`). Add `dashboard` to `PAGE_SKILLS`. |
| `.agents/skills/dashboard/SKILL.md` | **Create — this is the real file.** The skill that writes entries and delivers the page. |
| `.claude/skills/dashboard` | **Create — a SYMLINK** to `../../.agents/skills/dashboard`. |
| `.claude/hooks/regen-dashboard.sh` | **Create.** Regenerate the page whenever the store is written. |
| `.claude/settings.json` | **Modify.** Register the hook. A hook script with no entry here never runs. |
| `.github/workflows/ci.yml` | **Modify.** Run both new `--self-test`s **and the ratchet itself**. |
| `docs/dev-process.md` | **Modify.** One pointer row per new mechanically-enforced script. |
| `docs/roadmap-to-launch.md` | **Modify.** The dashboard has a merged spec and plan and no roadmap entry. |
| `tests/` | **Not used.** These are standalone scripts with built-in `--self-test`, following every existing `scripts/check-*.py`. |

⚠ **The skill path is not a preference.** Every one of the twenty existing skills is a real
directory under `.agents/skills/` plus a symlink from `.claude/skills/`, and
`scripts/check-explainer-delivery.py:45` sets `SKILLS = ROOT / ".agents" / "skills"`. v1 said to
create a real directory at `.claude/skills/dashboard/`; that fails `check_skill_symlinks` in
`scripts/check-docs.py` (added the same afternoon, `59385bb`) **and** makes
`check-explainer-delivery.py` report `dashboard/SKILL.md is missing`. Verified by both review
halves against a temp tree.

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

# `^##\s*\S` — NOT `startswith("## ")`. A header typed without the space
# ("##2026-08-28") must become a MALFORMED entry, not vanish. v1 dropped it
# silently while its own docstring promised "never dropped"; a missing space is
# a plausible hand-typing slip, and the store is hand-written.
BLOCK = re.compile(r"^##\s*\S")
HEADER = re.compile(r"^##\s*(\S+)(.*)$")
FLAG = re.compile(r"\[(needs-you|resolved:\s*[^\]]*)\]")
TECH_MARKER = "<!--tech-->"

def _valid_date(s: str) -> bool:
    try:
        _dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False

def parse_entries(text: str) -> list[dict]:
    """Split on column-0 '##' only. A malformed block is RETURNED with an
    error, never dropped — the page must show it in place (spec §6.2).

    Two passes. The first assigns ids; the second validates [resolved: <id>]
    against those ids, which CANNOT be done inline because a resolution may
    name an entry that appears later in the file.
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
        raw = "\n".join(b)
        entry = {"raw": raw, "error": None, "needs_you": False, "resolves": None,
                 "date": None, "ordinal": 0, "id": None, "title": "", "plain": "", "tech": None}
        m = HEADER.match(b[0])
        if m is None or not _valid_date(m.group(1)):
            bad = "" if m is None else m.group(1)
            entry["error"] = f"not a real calendar date: {bad!r}"
            out.append(entry)
            continue
        date, rest = m.group(1), m.group(2)
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
                # `[^\]]*` so an EMPTY id is captured as "" and rejected in
                # pass 2, rather than backtracking onto the space and looking
                # like a well-formed resolution of nothing.
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
        if not entry["title"]:
            # §6.2 defines the title as the first non-blank line after the
            # header and does not say what happens when there is none. An
            # entry the page would render as an empty bold line is malformed:
            # the title is the only part the user actually reads.
            entry["error"] = "no title line — the first line after the header is blank"
        out.append(entry)

    # PASS 2 — a [resolved:] naming an id that does not exist is malformed
    # (spec §6.2's third falsifier). This is the failure that matters most,
    # because it is silent in the worst direction: the author appends
    # `[resolved: 2026-08-26/2]`, believes an item is cleared, and it stays on
    # "What needs you" forever with nothing anywhere saying why.
    ids = {e["id"] for e in out if e["id"] and not e["error"]}
    for e in out:
        # `is None`, NOT `not e["resolves"]`. `resolves` is THREE-valued:
        # None = no [resolved:] flag, "" = the flag with nothing after it,
        # a string = a claimed id. A falsy test collapses the first two and
        # lets `[resolved: ]` through as if nothing had been declared —
        # MEASURED while writing v2: the case asserting it is an error failed.
        if e["error"] or e["resolves"] is None:
            continue
        if e["resolves"] not in ids:
            # THREE distinct diagnoses, because "no such entry" is a lie when
            # the entry exists and is merely unparseable — the author would go
            # looking for a typo in the id that is not there.
            if not e["resolves"]:
                e["error"] = "[resolved:] with no entry id after it"
            elif any(o["id"] == e["resolves"] for o in out):
                e["error"] = (f"[resolved: {e['resolves']}] names an entry that "
                              f"could not be parsed — fix that entry first")
            else:
                e["error"] = f"[resolved: {e['resolves']}] names no entry in this file"
    return out
```

⚠ **Order matters in pass 2.** `ids` is built from entries that are *not already* in error, so a
malformed entry cannot be the target of a resolution — which is correct: an entry the page could
not parse has no reliable id to point at.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: exit 0, no `[FAIL]` lines. (Do not check the count — see Global Constraints.)

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

    res = parse_entries("## 2026-08-28\nTarget.\n## 2026-08-29 [resolved: 2026-08-28/1]\nDone.\n")
    case("resolves parsed", res[1]["resolves"], "2026-08-28/1")
    case("valid resolve is not an error", res[1]["error"], None)

    # --- spec §6.2's THIRD falsifier: a [resolved:] naming an unknown id.
    # v1 had neither code nor case for this and its Self-Review claimed
    # "every row has a case".
    ghost = parse_entries("## 2026-08-29 [resolved: 1999-01-01/9]\nDone.\n")
    case("resolve of an unknown id is an error", ghost[0]["error"] is not None, True)
    empty_res = parse_entries("## 2026-08-29 [resolved: ]\nDone.\n")
    case("resolve with an empty id is an error", empty_res[0]["error"] is not None, True)

    # --- the two silent-drop cases
    nospace = parse_entries("##2026-08-28\nNo space after the hashes.\n")
    case("'##' with no space is still an entry", len(nospace), 1)
    case("'##' with no space parses normally", nospace[0]["error"], None)

    notitle = parse_entries("## 2026-08-28\n\n\n")
    case("entry with no title is an error", notitle[0]["error"] is not None, True)
```

- [ ] **Step 6: Run to verify all pass**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: exit 0, no `[FAIL]` lines.

Two diagnostics if something goes red:
- "indented ## does not split" failing means the block splitter is matching indented lines — `BLOCK`
  is anchored with `^` and must be matched against the **raw** line, never a stripped one.
- "resolve of an unknown id is an error" failing means pass 2 was skipped or `ids` was built before
  every entry had an id. It cannot be done in the first pass; a resolution may name a later entry.

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

    # --- "later" is in the docstring; make it true. v1 used a flat set, so an
    # EARLIER entry cleared a LATER one and an entry could clear ITSELF —
    # a way to write a [needs-you] that flags nothing.
    self_res = parse_entries("## 2026-08-26 [needs-you] [resolved: 2026-08-26/1]\nA.\n")
    case("an entry cannot resolve itself",
         [x["id"] for x in unresolved(self_res)], ["2026-08-26/1"])
    early = parse_entries("## 2026-08-25 [resolved: 2026-08-26/1]\nEarly.\n"
                          "## 2026-08-26 [needs-you]\nLater.\n")
    case("an earlier entry cannot resolve a later one",
         [x["id"] for x in unresolved(early)], ["2026-08-26/1"])

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
def _pos(e: dict) -> tuple:
    """Sort position of an entry in the store: date, then ordinal within it."""
    return (e["date"] or "", e["ordinal"])

def unresolved(entries: list[dict]) -> list[dict]:
    """needs-you entries not cleared by a LATER [resolved: <id>] (spec §6.2).

    "Later" is enforced, not merely documented. v1 used a flat set over every
    entry, so an EARLIER entry cleared a later one and an entry could clear
    ITSELF — which is a way to write a [needs-you] that flags nothing.
    """
    by_id = {e["id"]: e for e in entries if e["id"] and not e["error"]}
    cleared = set()
    for e in entries:
        if e["error"] or e["resolves"] is None:
            continue
        target = by_id.get(e["resolves"])
        if target is not None and _pos(e) > _pos(target):
            cleared.add(target["id"])
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
Expected: exit 0, no `[FAIL]` lines.

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
        data = json.loads(r.stdout or "[]")
    except json.JSONDecodeError as exc:
        return None, f"gh returned unparseable JSON: {exc}"
    # Shape-check before trusting it. A non-list would iterate its keys and a
    # missing field would raise KeyError inside the renderer, where the
    # could-not-tell contract no longer exists to catch it.
    if not isinstance(data, list) or any(
            not isinstance(p, dict) or "number" not in p or "title" not in p for p in data):
        return None, "gh returned JSON in an unexpected shape"
    return data, None

def no_entry_prs(limit: int = 40) -> tuple[list[dict] | None, str | None]:
    """Merged PRs whose body declared `NO-ENTRY:`, newest first.

    SPEC §7 REQUIRES THIS TO BE DISPLAYED: "a branch may declare NO-ENTRY:
    <reason> ... which the check accepts and the dashboard DISPLAYS, so a
    skipped entry is a recorded decision rather than a silence."

    v1 built the accepting half and nothing rendered it, which is the whole
    difference between a gate and a formality: the exemption cost nothing,
    left no trace, nobody could see "eleven of the last twelve branches
    declared NO-ENTRY", and the page would go on looking healthy while
    describing less and less. Displaying it makes the reflex self-limiting.

    Derived from `gh`, never stored — the store stays append-only and
    human-owned, and CI never writes to the repository.
    """
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--limit", str(limit),
             "--json", "number,title,body,mergedAt"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run gh: {exc}"
    if r.returncode != 0:
        return None, f"gh exited {r.returncode}: {r.stderr.strip()[:200]}"
    import json
    try:
        data = json.loads(r.stdout or "[]")
    except json.JSONDecodeError as exc:
        return None, f"gh returned unparseable JSON: {exc}"
    if not isinstance(data, list):
        return None, "gh returned JSON in an unexpected shape"
    out = []
    for p in data:
        if not isinstance(p, dict):
            return None, "gh returned JSON in an unexpected shape"
        reason = exemption_reason(p.get("body") or "")
        if reason:
            out.append({"number": p.get("number"), "title": p.get("title") or "",
                        "merged": (p.get("mergedAt") or "")[:10], "reason": reason})
    return out, None
```

⚠ **`exemption_reason` has ONE definition, and it lives in the gate** (`check-dashboard-entry.py`,
Task 4 Step 3). The page must read a PR body exactly as the gate does, or it would display
exemptions the gate never granted, or stay silent about ones it did — and a display that disagrees
with the gate is worse than no display, because it is believed.

The dependency arrow points **generator → gate**, never the reverse. The principle in Task 4's
Interfaces line is that a *gate* must not import the thing it guards; a page importing a gate is
fine, and it is what keeps the two readings identical by construction. Add this loader near the top
of `gen-dashboard.py`:

```python
def _gate_module():
    """Load scripts/check-dashboard-entry.py for its exemption_reason().

    Hyphenated filenames are not importable, and this repo's scripts are all
    hyphenated, so importlib is the only route. A failure here is a CANNOT RUN,
    never a silent "no exemptions" — that is exactly the false-healthy page
    §7 exists to prevent.
    """
    import importlib.util, pathlib
    p = pathlib.Path(__file__).with_name("check-dashboard-entry.py")
    spec = importlib.util.spec_from_file_location("_dash_gate", p)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

and in `no_entry_prs`, replace the direct call with:

```python
    try:
        exemption_reason = _gate_module().exemption_reason
    except Exception as exc:
        return None, f"could not load the gate's exemption reader: {exc}"
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
n, err3 = m.no_entry_prs(); print('no-entry:', len(n) if n is not None else None, 'err:', err3)
"
```
Expected: a non-zero date count and `err: None`. `prs: 0 err: None` is correct when nothing is open — the distinction from failure is `err`. `no-entry: 0` is expected today; no merged PR has ever carried the declaration.

**Then falsify the could-not-tell contract, because it is the one thing here that must not fail quietly.** Run the same snippet with `gh` made unavailable:

```bash
PATH=/usr/bin:/bin python3 -c "…"   # gh is not on this PATH
```
Expected: `prs: None err: could not run gh: …` and the same for `no-entry`. **If either prints `0` with `err: None`, the collector is reporting "nothing" where it means "could not ask" — stop and fix it.** That is this project's most-repeated defect shape, and it is why the collectors return a tuple at all.

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
- Consumes: `parse_entries`, `unresolved`, `bucket_days`, `commit_dates`, `open_prs`, `no_entry_prs`.
- Produces: `build(entries, days, prs, pr_error, git_error, window, exemptions, exempt_error) -> str` returning a complete HTML fragment (a `<title>`, one `<style>`, then body markup) that `main` passes to `scripts/brief-compose.py --content`. **`build` never writes a file, and its output is never served directly** — see Step 5.

- [ ] **Step 1: Write the failing tests**

Append to `_self_test`. `_B` gives every call the two new arguments without repeating them.

```python
    def _B(entries, days, prs=(), pr_error=None, git_error=None, window=2,
           exemptions=(), exempt_error=None):
        return build(entries, days, list(prs) if prs is not None else None, pr_error,
                     git_error, window, list(exemptions) if exemptions is not None else None,
                     exempt_error)

    ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n<!--tech-->\nPR #1.\n")
    d3 = bucket_days(["2026-08-28"], ents3, 2, "2026-08-28")
    html = _B(ents3, d3)
    case("needs-you surfaces", "Decide the thing." in html, True)
    case("tech is behind a fold", "<details" in html, True)
    case("tech labelled", "technical detail" in html.lower(), True)

    html_empty = _B([], bucket_days([], [], 2, "2026-08-28"))
    case("empty says nothing needs you", "Nothing needs you" in html_empty, True)
    case("empty says no entries yet", "no entries yet" in html_empty.lower(), True)

    html_err = _B([], bucket_days([], [], 2, "2026-08-28"), prs=None, pr_error="gh exploded")
    case("gh failure is NOT 'nothing needs you'", "Nothing needs you" in html_err, False)
    case("gh failure says could not tell", "could not tell" in html_err.lower(), True)

    bad3 = parse_entries("## 2026-99-99\nBroken.\n")
    html_bad = _B(bad3, bucket_days([], bad3, 2, "2026-08-28"))
    case("malformed says it could not parse", "could not parse" in html_bad.lower(), True)
    case("malformed keeps its raw text", "Broken." in html_bad, True)

    # --- H5: a gh failure must not DISCARD the needs the store already knows.
    # Two independent sources feed one section; the optional one failing must
    # not suppress the primary one. This is the exact scenario the page exists
    # for: someone returns after time away and gh's token has expired.
    need_html = _B(ents3, d3, prs=None, pr_error="gh exited 1: auth")
    case("a gh failure still shows the store's needs", "Decide the thing." in need_html, True)
    case("a gh failure still says it could not check PRs",
         "could not" in need_html.lower(), True)

    # --- H3: "rendered IN PLACE" is a claim about POSITION, so assert position.
    # v1's case asserted the string appeared somewhere in the document, which
    # passes at any position — including the bottom, where it always landed.
    mixed = parse_entries("## 2026-08-28\nNewest good.\n"
                          "## 2026-02-30\nBroken middle.\n"
                          "## 2026-08-27\nOlder good.\n")
    hm = _B(mixed, bucket_days([], mixed, 2, "2026-08-28"))
    case("malformed renders BETWEEN its neighbours, not at the bottom",
         hm.index("Newest good.") < hm.index("Broken middle.") < hm.index("Older good."), True)

    # --- M3 / Codex-H: ties keep FILE order (spec §6.2).
    tie = parse_entries("## 2026-08-28\nFIRST in file.\n## 2026-08-28\nSECOND in file.\n")
    ht = _B(tie, bucket_days([], tie, 2, "2026-08-28"))
    case("same-date ties keep file order",
         ht.index("FIRST in file.") < ht.index("SECOND in file."), True)

    # --- M1: the id the resolution mechanism depends on must be readable.
    case("the entry id is rendered", "2026-08-28/1" in ht, True)

    # --- M2: duplicate DOM ids are invalid HTML and make the chart's anchors
    # ambiguous. Two entries on one date used to emit id="d-2026-08-28" twice.
    import re as _re
    all_ids = _re.findall(r'\sid="([^"]+)"', ht)
    case("no duplicate DOM ids", len(all_ids), len(set(all_ids)))

    # --- M7: every <details> carries a stable id, so the reload restore in
    # Task 5 keys on identity rather than on document position.
    case("every details has an id", ht.count("<details id=") , ht.count("<details"))

    # --- H4: a zero-commit day with an entry must be VISIBLY marked. The mark
    # must differ OUTSIDE the visually-hidden span, or "visible rather than
    # invisible" is false on screen.
    def _strip_vh(s):
        return _re.sub(r'<span class="vh">.*?</span>', "", s)
    marked = _bar({"date": "2026-08-28", "commits": 0, "needs_you": False, "has_entry": True}, 5)
    plainb = _bar({"date": "2026-08-27", "commits": 0, "needs_you": False, "has_entry": False}, 5)
    case("the marked zero bar differs outside the hidden span",
         _strip_vh(marked).replace("2026-08-28", "D") != _strip_vh(plainb).replace("2026-08-27", "D"),
         True)

    # --- §7: the NO-ENTRY exemption is DISPLAYED, and a failure to read it
    # is a could-not-tell, never a silent "none".
    hx = _B([], bucket_days([], [], 2, "2026-08-28"),
            exemptions=[{"number": 9, "title": "T", "merged": "2026-08-28", "reason": "typo fix"}])
    case("a recorded exemption is displayed", "typo fix" in hx, True)
    case("the exemption names its pull request", "#9" in hx, True)
    hxe = _B([], bucket_days([], [], 2, "2026-08-28"), exemptions=None, exempt_error="gh exploded")
    case("an unreadable exemption list says so", "could not" in hxe.lower(), True)

    # --- L6: a window of zero renders an empty box with no complaint.
    hz = _B([], bucket_days([], [], 0, "2026-08-28"), window=0)
    case("a zero window says so rather than drawing an empty box",
         "could not" in hz.lower() or "no days" in hz.lower(), True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: `NameError: name 'build' is not defined`.

- [ ] **Step 3: Implement `build`**

```python
import html as _html
import re as _re

def _slug(s: str) -> str:
    """A DOM-id-safe form of an entry id: '2026-08-28/1' -> '2026-08-28-1'."""
    return _re.sub(r"[^A-Za-z0-9_-]", "-", s or "")

def _ordered(entries: list[dict]) -> list[dict]:
    """Newest date first; ties keep FILE order; a malformed block stays
    adjacent to its file neighbours (spec §6.2, 'rendered in place').

    v1 got two things wrong from one line
    (`sorted(..., key=(date, ordinal), reverse=True)`):

      * `reverse=True` reversed the ORDINAL too, so same-date entries came out
        backwards. Python's sort is stable *even with* `reverse=True`, so
        sorting on the DATE ALONE gives newest-first with ties in file order.
      * a malformed entry has `date=None`, which mapped to `""` and sorted
        below every real date — so it always rendered at the very bottom of
        the page, furthest from the context that would explain it. Here it
        inherits the date of the nearest PRECEDING valid entry, which puts it
        back among its neighbours.
    """
    keys, last = [], None
    for e in entries:
        if not e["error"]:
            last = e["date"]
        keys.append(last)
    # A malformed block before ANY valid entry inherits the first valid date,
    # so it stays at the top rather than falling to the bottom.
    first = next((k for k in keys if k is not None), "")
    keys = [k if k is not None else first for k in keys]
    return [e for _, e in sorted(zip(keys, entries), key=lambda p: p[0], reverse=True)]

def _bar(day: dict, tallest: int) -> str:
    h = 4 if day["commits"] == 0 else max(6, round(48 * day["commits"] / max(tallest, 1)))
    marked = day["has_entry"] and day["commits"] == 0
    cls = "bar needs" if day["needs_you"] else "bar"
    if marked:
        cls += " marked"
    label = (f'{day["date"]}: {day["commits"]} commits'
             f'{", needs you" if day["needs_you"] else ""}'
             f'{", entry with no commits" if marked else ""}')
    # The dot is a REAL element, not text inside .vh. §6.1 asks for this to be
    # "visible rather than invisible"; v1 put the only difference inside the
    # visually-hidden span, so on screen the two bars were pixel-identical.
    # `.vh` keeps the same fact available to a screen reader.
    dot = '<span class="dot" aria-hidden="true"></span>' if marked else ""
    return (f'<a class="{cls}" href="#day-{day["date"]}" style="height:{h}px" '
            f'title="{_html.escape(label)}" aria-label="{_html.escape(label)}">'
            f'{dot}<span class="vh">{_html.escape(label)}</span></a>')

def build(entries, days, prs, pr_error, git_error, window,
          exemptions, exempt_error) -> str:
    # --- What needs you -------------------------------------------------
    # `need` comes from the local store and is UNAFFECTED by gh. v1 replaced
    # the whole section with the gh error, so a page holding a file that said
    # something needed you reported that it could not tell. Two independent
    # sources feed one section; the OPTIONAL one failing must never suppress
    # the PRIMARY one. "could not tell" is still not "nothing needs you"
    # (CLAUDE.md's cannot-run rule) — it is now scoped to what actually failed.
    need = unresolved(entries)
    rows = [f'<li><a href="#{_slug(e["id"])}">{_html.escape(e["title"])}</a> '
            f'<span class="when">{_html.escape(e["date"])} · {_html.escape(e["id"])}</span></li>'
            for e in need]
    if pr_error:
        pr_note = (f'<p class="unknown">I could not also check open pull requests — '
                   f'{_html.escape(pr_error)}. Treat this as NOT CHECKED.</p>')
    else:
        pr_note = ""
        rows += [f'<li>Pull request #{_html.escape(str(p["number"]))} — '
                 f'{_html.escape(str(p["title"]))}'
                 f' <span class="when">open</span></li>' for p in (prs or [])]
    if rows:
        needs_html = '<ul class="needs">' + "".join(rows) + "</ul>" + pr_note
    elif pr_error:
        needs_html = pr_note          # NEVER "Nothing needs you" on a failure
    else:
        needs_html = '<p class="none">Nothing needs you.</p>'

    # --- The chart ------------------------------------------------------
    if git_error:
        chart = (f'<p class="unknown">Could not read the git history — '
                 f'{_html.escape(git_error)}</p>')
    elif not days:
        # A window of zero or less produced an empty box with no complaint.
        chart = (f'<p class="unknown">No days to show — the window is '
                 f'{_html.escape(str(window))}. Pass --window with a positive number.</p>')
    else:
        tallest = max((d["commits"] for d in days), default=0)
        chart = "".join(_bar(d, tallest) for d in reversed(days))

    # --- What changed ---------------------------------------------------
    if not entries:
        entries_html = ('<p class="none">No entries yet. They live in '
                        '<code>docs/dashboard-entries.md</code>.</p>')
    else:
        parts, anchored = [], set()
        for i, e in enumerate(_ordered(entries)):
            # One DOM id per entry, derived from the entry id — v1 emitted
            # id="d-<date>" for every entry, so two entries on one date
            # produced duplicate ids (invalid HTML) and the chart's anchor
            # resolved to whichever happened to come first.
            eid = _slug(e["id"]) if e["id"] else f"bad-{i}"
            # The chart links to the FIRST entry of each date, deliberately.
            day_anchor = ""
            if e["date"] and e["date"] not in anchored:
                anchored.add(e["date"])
                day_anchor = f'<span class="anchor" id="day-{_html.escape(e["date"])}"></span>'
            if e["error"]:
                parts.append(
                    f'{day_anchor}<article class="entry broken" id="{eid}">'
                    f'<p class="err">Could not parse this entry — {_html.escape(e["error"])}</p>'
                    f'<pre>{_html.escape(e["raw"])}</pre></article>')
                continue
            # Every <details> carries a stable id so the reload restore in
            # Task 5 keys on identity, not on document position — a new entry
            # is appended at the TOP and shifts every index below it.
            tech = ("" if not e["tech"] else
                    f'<details id="{eid}-tech"><summary>Raw technical detail</summary>'
                    f'<pre>{_html.escape(e["tech"])}</pre></details>')
            flag = ' <span class="flag">needs you</span>' if e["needs_you"] else ""
            parts.append(
                f'{day_anchor}<article class="entry" id="{eid}">'
                f'<h3>{_html.escape(e["date"])} '
                f'<span class="eid">{_html.escape(e["id"])}</span>{flag}</h3>'
                f'<p class="title">{_html.escape(e["title"])}</p>'
                f'<details id="{eid}-plain"><summary>What this means</summary>'
                f'<p>{_html.escape(e["plain"])}</p></details>{tech}</article>')
        entries_html = "".join(parts)

    # --- Recorded exemptions (spec §7) ----------------------------------
    # An exemption that leaves no trace is how the gate hollows out: nothing
    # counts it, so nobody can see "eleven of the last twelve branches
    # declared NO-ENTRY", and the page goes on looking healthy while
    # describing less and less.
    if exempt_error:
        exempt_html = (f'<p class="unknown">I could not tell whether any branch skipped its '
                       f'entry — {_html.escape(exempt_error)}. Treat this as NOT CHECKED.</p>')
    elif not exemptions:
        exempt_html = '<p class="none">No branch has skipped its entry.</p>'
    else:
        exempt_html = '<ul class="needs">' + "".join(
            f'<li>No entry recorded — <strong>{_html.escape(str(x["reason"]))}</strong> '
            f'<span class="when">#{_html.escape(str(x["number"]))} · '
            f'{_html.escape(str(x["merged"]))}</span></li>' for x in exemptions) + "</ul>"

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
.chart{{display:flex;align-items:flex-end;gap:4px;height:56px;padding:8px 8px 14px;
background:var(--panel);border:1px solid var(--rule);border-radius:4px;overflow-x:auto}}
.bar{{position:relative;flex:1;min-width:8px;background:var(--ok);
border-radius:2px 2px 0 0;display:block}}
.bar.needs{{background:var(--need)}}
/* §6.1: an entry on a day with ZERO commits must be VISIBLE, not merely
   announced to a screen reader. The dot sits below the bar and the outline
   widens it, so the two states differ on screen and not only in the a11y
   tree. `.bar` is position:relative so the dot has a containing block. */
.bar.marked{{outline:2px solid var(--need);outline-offset:1px}}
.bar .dot{{position:absolute;left:50%;bottom:-11px;width:6px;height:6px;
margin-left:-3px;border-radius:50%;background:var(--need)}}
.vh{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
.anchor{{display:block;height:0;scroll-margin-top:12px}}
.entry{{background:var(--panel);border:1px solid var(--rule);border-radius:4px;
padding:14px 18px;margin-bottom:10px}}
.entry.broken{{border-color:var(--err);background:var(--err-bg)}}
.entry h3{{font-family:var(--mono);font-size:12px;color:var(--fg3);margin:0 0 6px}}
.entry .eid{{color:var(--fg3);opacity:.75}}
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
<h2>Branches that skipped their entry</h2>{exempt_html}
<h2>Elsewhere</h2><ul>
<li><a href="/goals">Goals</a></li><li><a href="/backlog-table">Backlog</a></li>
<li><a href="/latest">Newest briefing</a></li><li><a href="/">All pages</a></li></ul>
</div>"""
```

⚠ **The `{{`/`}}` escapes are load-bearing.** This is one f-string containing CSS; every literal
brace is doubled. Both review halves compiled v1's version and confirmed the escaping was correct —
re-check after editing, because an unbalanced brace here is a `SyntaxError` at import time, which
would take the gate's self-test down with it.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: exit 0, no `[FAIL]` lines.

- [ ] **Step 5: Wire up `main` — which COMPOSES the page, never writes the fragment**

⚠ **This is the shape v1 got wrong, and it would have degraded the page silently on every entry.**
`build()` returns a **fragment** — it starts `<title>…`, with no `<!doctype>`, no
`<meta charset="utf-8">` and **no Ask tray**. v1's `--out` defaulted to
`~/explainers/dashboard.html` and wrote that fragment straight there, so the invocation printed in
the script's own `--help` replaced the composed page with a trayless fragment and nothing failed.
Task 6's regen hook would then have done it automatically on every write to the store.

The two existing standing-page generators both call the composer themselves and fail loud —
`scripts/gen-goals-page.py:487-498` and `scripts/gen-backlog-page.py:1630`. `gen-goals-page.py:482`
states the rule: *"The Ask tray is LIFTED by brief-compose.py, never re-implemented here — one tray,
three page-producing callers."* And `scripts/brief-compose.py:30-31`: *"If no source explainer can be
found … this EXITS NONZERO and writes nothing. A brief that renders without its Ask tray is the
failure this script exists to prevent."* Copy that shape:

```python
import argparse, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--window", type=int, default=14)
    ap.add_argument("--store", default="docs/dashboard-entries.md")
    ap.add_argument("--out", type=pathlib.Path,
                    default=pathlib.Path.home() / "explainers" / "dashboard.html")
    # The escape hatch for inspecting the raw fragment. It is a SEPARATE flag,
    # so the default path can never accidentally emit an uncomposed page.
    ap.add_argument("--fragment-only", type=pathlib.Path, default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if a.window < 1:
        print(f"CANNOT RUN — --window must be at least 1, got {a.window}.", file=sys.stderr)
        return 2
    store = pathlib.Path(a.store)
    entries = parse_entries(store.read_text(encoding="utf-8")) if store.exists() else []
    dates, git_error = commit_dates(a.window)
    prs, pr_error = open_prs()
    exemptions, exempt_error = no_entry_prs()
    today = _dt.date.today().isoformat()
    days = bucket_days(dates or [], entries, a.window, today)
    frag = build(entries, days, prs, pr_error, git_error, a.window, exemptions, exempt_error)

    if a.fragment_only:
        a.fragment_only.write_text(frag, encoding="utf-8")
        print(f"wrote fragment {a.fragment_only}")
        return 0

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "dashboard-fragment.html"
        f.write_text(frag, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "brief-compose.py"),
             "--content", str(f), "--slug", "dashboard", "--out", str(a.out),
             "--title", "Project dashboard"],
            cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 or not a.out.is_file():
        print(f"FAILED — brief-compose did not write {a.out}:\n{r.stdout}{r.stderr}",
              file=sys.stderr)
        return 1

    print(f"wrote {a.out}  ({len(entries)} entries, window {a.window})")
    for label, err in (("git", git_error), ("gh", pr_error), ("gh/exemptions", exempt_error)):
        if err:
            print(f"  ⚠ {label}: {err}")
    print("     http://127.0.0.1:7391/dashboard   (start: python3 scripts/explainer-serve.py)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Update the docstring at the top of the file to match — `python3 scripts/gen-dashboard.py` now
produces a **composed** page at `~/explainers/dashboard.html`.

Delete the old `if __name__` block from Task 1.

- [ ] **Step 6: Generate and look at it**

```bash
python3 scripts/gen-dashboard.py
python3 scripts/explainer-serve.py
```

`--out` writes the **undated** `dashboard.html` directly; passing `--out` to `brief-compose.py` is
what avoids v1's `mv ~/explainers/*-brief-dashboard.html …` glob, which was a hand-run rename with
no error check that would have silently done nothing if the composer's naming ever changed.

The undated filename is what makes this a **standing** page. VERIFIED against
`scripts/explainer-serve.py`: `DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-")` at `:385` and
`is_standing()` at `:389` exclude it from `/latest`, and `resolve_page()` at `:400-417` serves
`/dashboard` from `dashboard.html`.

Then open `http://127.0.0.1:7391/dashboard` and confirm, **looking at the page, not at the markup**:

- the entry from Task 1 appears, with its id (`2026-08-28/1`) visible next to the date;
- its fold opens;
- the chart has bars, and a zero-commit day carrying an entry is **distinguishable from its
  neighbours with the mouse elsewhere** — no hover, no screen reader;
- the **Ask tray is present**. If it is missing, `build`'s fragment reached the file directly and
  Step 5's composer call is not doing its job;
- `/latest` still points at the newest *briefing*, not at the dashboard.

⚠ **Check `document.hidden` before trusting any in-page probe.** A backgrounded tab has no geometry
and reports false results — measured 2026-08-28, a probe reported "0 of 9 reachable" purely because
the tab was hidden.

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

# A PATH match, not a prefix match. "docs/reviews/" is a directory and
# "docs/dashboard-entries.md" is a file; a bare str.startswith() also exempted
# "docs/dashboard-entries.md.bak", and would exempt any future path that
# happened to share the opening characters.
EXEMPT_DIRS = ("docs/reviews/",)
EXEMPT_FILES = ("docs/dashboard-entries.md",)
NO_ENTRY = "NO-ENTRY:"

FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")

def exemption_reason(pr_body: str) -> str | None:
    """The reason after a line-leading `NO-ENTRY:`, or None.

    ONE DEFINITION, shared with scripts/gen-dashboard.py, which imports this
    function so the page displays exactly the exemptions the gate granted
    (spec §7). A display that disagrees with the gate is worse than none.

    AN EXEMPTION MUST BE DELIBERATE, so anything a Markdown reader would treat
    as inert text does not count. Four constructs are skipped, and the gate's
    own refusal message contains the literal string `NO-ENTRY: <reason>` —
    which is exactly what makes quoting it back an accident waiting to happen:

      * fenced code, with the fence closed only by its OWN character. A ```
        block is not closed by ~~~, and an unterminated fence runs to the end.
      * an indented code block — 4+ leading spaces, Markdown's own rule.
      * an HTML comment, possibly spanning lines. THIS IS THE ONE THAT WOULD
        HAVE BITTEN: GitHub pull-request templates put their instructions in
        `<!-- ... -->`, so a template that documented the escape hatch would
        have silently exempted every branch that used it. This repo has no
        template today (checked 2026-08-28) — the hole is latent, not active,
        which is the only reason this is not Blocking.
      * a `>` blockquote, which was already safe because the marker stops
        being line-leading.
    """
    fence_ch = None
    in_comment = False
    for line in pr_body.split("\n"):
        if not in_comment:
            m = FENCE.match(line)
            if m:
                ch = m.group("ch")[0]
                if fence_ch is None:
                    fence_ch = ch
                elif ch == fence_ch:
                    fence_ch = None
                continue
        if fence_ch is not None:
            continue
        probe = line
        while probe:
            if in_comment:
                end = probe.find("-->")
                if end < 0:
                    probe = ""
                    break
                probe, in_comment = probe[end + 3:], False
            else:
                start = probe.find("<!--")
                if start < 0:
                    break
                head, probe, in_comment = probe[:start], probe[start + 4:], True
                if head.strip().startswith(NO_ENTRY):
                    return head.strip()[len(NO_ENTRY):].strip() or ""
        if in_comment or not probe:
            continue
        if len(probe) - len(probe.lstrip(" ")) >= 4:
            continue
        s = probe.strip()
        if s.startswith(NO_ENTRY):
            return s[len(NO_ENTRY):].strip() or ""
    return None

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

    # --- L5: a PATH match, not a prefix match, in both directions.
    case("a lookalike filename is NOT exempt",
         verdict(["docs/dashboard-entries.md.bak"], False, "")[0], 1)
    case("a lookalike directory is NOT exempt",
         verdict(["docs/reviews-not-really/x.ts"], False, "")[0], 1)

    # --- L4: the gate's own error message quoted back must not exempt.
    fenced_body = "```\nNO-ENTRY: example from the docs\n```"
    case("NO-ENTRY inside a code fence does not exempt",
         verdict(["lib/x.ts"], False, fenced_body)[0], 1)
    case("exemption_reason ignores fenced text", exemption_reason(fenced_body), None)
    case("exemption_reason reads a real declaration",
         exemption_reason("NO-ENTRY: typo fix"), "typo fix")
    case("exemption_reason distinguishes empty from absent",
         (exemption_reason("NO-ENTRY:"), exemption_reason("nothing here")), ("", None))

    # --- the inert-text constructs. All MEASURED against the reader, not
    # assumed. The HTML-comment row is the one that would have bitten: a
    # GitHub PR template documents itself inside <!-- ... -->.
    for name, body, want in [
        ("fenced with ~~~",        "~~~\nNO-ENTRY: inside\n~~~",                    None),
        ("unterminated fence",     "```\nNO-ENTRY: inside\n",                       None),
        ("``` is not closed by ~~~", "```\nNO-ENTRY: a\n~~~\nNO-ENTRY: b\n",        None),
        ("indented code block",    "    NO-ENTRY: indented\n",                      None),
        ("multi-line HTML comment", "<!--\nNO-ENTRY: commented out\n-->\n",         None),
        ("one-line HTML comment",  "<!-- NO-ENTRY: nope -->\n",                     None),
        ("blockquoted",            "> NO-ENTRY: quoted\n",                          None),
        ("lowercase is not the marker", "no-entry: lower\n",                        None),
        ("after a CLOSED comment", "<!-- hint -->\nNO-ENTRY: real one\n",     "real one"),
        ("after a CLOSED fence",   "```\ncode\n```\nNO-ENTRY: real one\n",    "real one"),
        ("3 spaces is still a declaration", "   NO-ENTRY: ok\n",                    "ok"),
    ]:
        case(f"exemption_reason — {name}", exemption_reason(body), want)
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
def _is_exempt(path: str) -> bool:
    return path in EXEMPT_FILES or any(path.startswith(d) for d in EXEMPT_DIRS)

def verdict(changed: list[str], added_entry: bool, pr_body: str) -> tuple[int, str]:
    real = [p for p in changed if not _is_exempt(p)]
    if not real:
        return 0, "no tracked files changed outside the exempt paths"
    if added_entry:
        return 0, "an entry block was added"
    reason = exemption_reason(pr_body)
    if reason:
        return 0, f"exempted by declaration — {reason}"
    if reason == "":
        return 1, f"{NO_ENTRY} was declared with no reason after it"
    return 1, (f"{len(real)} tracked file(s) changed and no entry was added to "
               f"docs/dashboard-entries.md. Add a '## YYYY-MM-DD' block describing "
               f"the change in plain words, or put 'NO-ENTRY: <reason>' in the PR body.")
```

⚠ `reason` is three-valued and the order of those two branches matters: a non-empty string exempts,
`""` means the marker was present with nothing after it and must **refuse**, `None` means it was
absent. Testing `if reason:` alone would treat "declared with no reason" as "not declared" and fall
through to a refusal with the wrong message.

- [ ] **Step 4: Run to verify all pass**

Run: `python3 scripts/check-dashboard-entry.py --self-test`
Expected: exit 0, no `[FAIL]` lines.

- [ ] **Step 5: Add the git collector and `main`**

```python
import argparse, datetime as _dt, re, subprocess

# `+##` then optional space then a YYYY-MM-DD that is a real calendar date.
# The date is re-validated below, because the regex alone accepts 2026-02-30.
_ADDED_ENTRY = re.compile(r"^\+##\s*(\d{4}-\d{2}-\d{2})\b")

def _added_entry_line(line: str) -> bool:
    m = _ADDED_ENTRY.match(line)
    if not m:
        return False
    try:
        _dt.date.fromisoformat(m.group(1))
        return True
    except ValueError:
        return False

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
    # An added header must be a REAL DATE, not any line starting "+## ".
    # v1 accepted `## not-a-date`, so a branch whose entry the renderer would
    # show as malformed still satisfied the gate — the check would pass on
    # exactly the entry the page cannot use.
    added = any(_added_entry_line(l) for l in patch.stdout.split("\n"))
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

Also append these cases to `_self_test`, so the tightened header rule is covered by something other
than the eye:

```python
    case("a real date header counts as an added entry",
         _added_entry_line("+## 2026-08-28"), True)
    case("a non-date header does NOT count", _added_entry_line("+## not-a-date"), False)
    case("an impossible date does NOT count", _added_entry_line("+## 2026-02-30"), False)
    case("a REMOVED header does not count", _added_entry_line("-## 2026-08-28"), False)
```

Delete the Task-4 Step-1 `if __name__` block.

- [ ] **Step 6: Prove it passes, then make it actually go RED**

```bash
python3 scripts/check-dashboard-entry.py --base origin/master; echo "rc=$?"
```
On this branch, which changed scripts and added an entry in Task 1, expect `ok` and `rc=0`.

⛔ **Do NOT use `git stash push docs/dashboard-entries.md` here.** v1 did, and it is inert: by this
point the entry has been **committed** for three tasks, so `git stash push` on a clean path prints
*"No local changes to save"*, exits 0, stashes nothing, and the check goes on correctly finding the
entry in `git diff <base>...HEAD`. v1 then instructed *"If this prints `ok`, the gate does not
work — stop and fix it"* — so the one outcome the step could ever produce was defined as failure,
and an implementer following it would set out to repair a mechanism that was working. Reproduced in
a throwaway repository by both review halves. `git stash pop` on the next line would have failed too.

**The only input `collect()` has is `git diff <base>...HEAD`.** A falsifier must remove the entry
from *that diff*. Run this in a scratch repository so nothing is done to the real branch:

```bash
set -e
D=$(mktemp -d); cd "$D"; git init -q .; git config user.email t@t; git config user.name t
mkdir -p docs scripts
cp "$OLDPWD/scripts/check-dashboard-entry.py" scripts/
git add -A; git commit -qm base; git branch -M master; git checkout -qb feature

# CONTROL A — code changed, no entry anywhere. MUST refuse.
mkdir -p lib; echo "x" > lib/x.ts; git add -A; git commit -qm code
python3 scripts/check-dashboard-entry.py --base master; echo "A rc=$?"

# CONTROL B — an entry is added. MUST pass.
printf '## %s\nDid a thing.\n' "$(date +%F)" > docs/dashboard-entries.md
git add -A; git commit -qm entry
python3 scripts/check-dashboard-entry.py --base master; echo "B rc=$?"

# CONTROL C — the entry is REMOVED by a commit, so it leaves the branch diff.
# This is the falsifier: it changes the only input the check reads.
git rm -q docs/dashboard-entries.md; git commit -qm remove
python3 scripts/check-dashboard-entry.py --base master; echo "C rc=$?"

# CONTROL D — the header is present but is NOT a real date. MUST refuse.
# `mkdir -p docs` is NOT optional: control C's `git rm` removed the last file
# in docs/, and git removes the now-empty directory with it. Without this line
# the printf fails, nothing is committed, and D REFUSES because there is still
# no entry at all — passing without ever exercising the date rule. MEASURED
# while writing v2; it is the same false-green shape as the falsifier above.
mkdir -p docs
printf '## not-a-date\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm baddate
git diff -U0 master...HEAD -- docs/dashboard-entries.md | grep '^+##'   # must print +## not-a-date
python3 scripts/check-dashboard-entry.py --base master; echo "D rc=$?"

# CONTROL E — the same commit with a REAL date must pass. Without E, D proves
# only that something refused, not that the DATE was why.
printf '## 2026-08-28\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm gooddate
python3 scripts/check-dashboard-entry.py --base master; echo "E rc=$?"
cd "$OLDPWD"; rm -rf "$D"
```

Required output — **all five, or the gate is not proven**:

```
REFUSED — …                       A rc=1
ok — an entry block was added     B rc=0
REFUSED — …                       C rc=1
+## not-a-date                    (D's grep — if this line is absent, D is vacuous)
REFUSED — …                       D rc=1
ok — an entry block was added     E rc=0
```

**If A, C or D prints `ok`, the gate does not work — stop and fix it.** If B or E prints `REFUSED`,
the collector is not seeing an entry that is genuinely there. C is the falsifier proper: it is the
step that removes `+## <date>` from the diff, which is the only thing `collect()` reads. D and E are
a matched pair — D alone can pass for the wrong reason.

- [ ] **Step 7: Wire into CI — the self-tests now, the ratchet in Task 6**

In `.github/workflows/ci.yml`, after the `check-function-revokes` steps. VERIFIED against the file:
it ends with those two steps, the indentation (`      - name:`) matches, and every other
`python3 scripts/…` step runs bare on `ubuntu-latest` with no Python setup step, so these fit as
written:

```yaml
      - name: gen-dashboard self-test
        run: python3 scripts/gen-dashboard.py --self-test

      - name: check-dashboard-entry self-test
        run: python3 scripts/check-dashboard-entry.py --self-test
```

The ratchet itself needs the PR body, and that wiring is Task 6 Step 5.

⛔ **This deferral is the plan's biggest remaining risk, so it is an acceptance criterion of the PR,
not a step inside a task.** Running the two `--self-test`s proves the *code* works and gates
nothing: until Task 6 lands, §7 — the entire justification for the gate — is a script nobody
executes. **The PR does not open until `check-dashboard-entry` runs against a real PR body in CI
and has been seen to refuse.** Both review halves independently called the unwired ratchet Blocking.

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
      document.querySelectorAll('details[id]').forEach(function (d) {
        if (d.open) open.push(d.id);
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
      document.querySelectorAll('details[id]').forEach(function (d) {
        if (open.indexOf(d.id) !== -1) d.open = true;
      });
    } catch (e) {}
  }
  restoreDetails();
```

Call `saveDetails()` immediately before the existing `sessionStorage.setItem(KEY, ...)` scroll save, in the same place the reload is triggered.

⚠ **Key on `d.id` ONLY — never on the document index.** v1 used `d.id || String(i)`, and since v1's
`build()` emitted no ids on its folds the key was *always* the index. The reload fires when the page
is rewritten, and the commonest rewrite is a new entry appended to the store, which renders
newest-first at the **top** and shifts every fold below it. So the restore would work when the page
had not changed and misapply itself when it had — which is the only reason the page reloaded.
Task 3 Step 3 now emits `id="<entry-id>-plain"` and `id="<entry-id>-tech"` on every fold. A fold
with no id is skipped rather than keyed positionally: on other explainer pages that is the honest
behaviour, since there is nothing stable to key on.

- [ ] **Step 3: Add self-test rows that can actually fail**

Beside the two existing reload-client cases in `_self_test`:

```python
        # COUNT, not presence. "restoreDetails()" is a substring of
        # "function restoreDetails()", so a presence check passes on a client
        # that DEFINES both functions and CALLS neither — i.e. on a build
        # where the feature is entirely dead. Requiring two occurrences means
        # deleting the call site turns the row red.
        case("reload client defines and CALLS saveDetails",
             lambda: RELOAD_JS.count("saveDetails()") >= 2)
        case("reload client defines and CALLS restoreDetails",
             lambda: RELOAD_JS.count("restoreDetails()") >= 2)
        case("reload client keys folds on id, never on position",
             lambda: "details[id]" in RELOAD_JS and "String(i)" not in RELOAD_JS)
```

- [ ] **Step 4: Run the self-test, then MUTATE it**

Run: `python3 scripts/explainer-serve.py --self-test`
Expected: exit 0, no failures.

Then prove the rows are load-bearing. Delete the `restoreDetails();` **call** (leaving the function
definition), re-run, and confirm the row goes **red**. Restore it.

**These three rows still only assert that text was typed.** They cannot observe behaviour, and they
are not the test — Step 5 is. They exist so that deleting the wiring cannot pass silently.

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
- Create: `.agents/skills/dashboard/SKILL.md` — **the real file**
- Create: `.claude/skills/dashboard` — **a symlink** to `../../.agents/skills/dashboard`
- Modify: `scripts/check-explainer-delivery.py:53`
- Create: `.claude/hooks/regen-dashboard.sh`
- Modify: `.claude/settings.json`
- Modify: `.github/workflows/ci.yml` (the ratchet itself)
- Modify: `docs/dev-process.md`, `docs/roadmap-to-launch.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the `/dashboard` skill, and the wiring that makes §7's gate actually gate.

- [ ] **Step 1: Register the skill in `PAGE_SKILLS`**

`scripts/check-explainer-delivery.py:53`:

```python
PAGE_SKILLS = ["explain-diff", "brief", "explain-findings", "explain-topic", "dashboard"]
```

⚠ **This check cannot enforce its own list** — it inspects only skills already on it, so an absent one is invisible and it exits green. Verified. This step is manual and ungated; that is why it is a numbered step rather than an assumption.

- [ ] **Step 2: Write the skill — at `.agents/skills/`, with a symlink**

```bash
mkdir -p .agents/skills/dashboard
ln -s ../../.agents/skills/dashboard .claude/skills/dashboard
ls -l .claude/skills/dashboard        # must print '-> ../../.agents/skills/dashboard'
```

⛔ **Not `.claude/skills/dashboard/` as a real directory.** All twenty existing skills are a real
directory under `.agents/skills/` plus a symlink; `check_skill_symlinks` in `scripts/check-docs.py`
(added `59385bb`) enforces it, and `scripts/check-explainer-delivery.py:45` reads
`.agents/skills`. v1 said to create the real directory in the wrong place, which fails both.

Create `.agents/skills/dashboard/SKILL.md`:

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
- Clear an earlier one by appending a **later** entry with `[resolved: YYYY-MM-DD/N]`.
  The id is printed next to each entry's date on the page — read it there, do not
  count blocks. An id that names no entry makes the block **malformed**, and the
  page will say so rather than silently leaving the item open.
- The title line is what the user reads, and an entry with no title line is malformed.
  No jargon, no abbreviations they have not seen defined. The technical fold is where
  identifiers belong.
- Grammar: `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2.

## 2. Regenerate and deliver

    python3 scripts/gen-dashboard.py

That one command composes and writes `~/explainers/dashboard.html`. It calls
`scripts/brief-compose.py` itself and **exits non-zero if the page is not written** —
never hand-compose, and never write the fragment to that path, because the fragment
has no Ask tray and no charset and nothing would fail.

The undated filename makes this a **standing page**, excluded from `/latest` so
regenerating it does not steal the newest-briefing bookmark
(`scripts/explainer-serve.py:385-417`).

**For serving, the question tray, arming the push loop, and verifying the page
before handing it over, follow `.agents/skills/shared/explainer-delivery.md`.**
Cite it; never restate it.

## 3. Deliver the URL

    http://127.0.0.1:7391/dashboard

Say in one line what changed since they last looked.
```

- [ ] **Step 3: Verify the delivery and docs checks pass**

```bash
python3 scripts/check-explainer-delivery.py; echo "rc=$?"
python3 scripts/check-docs.py; echo "rc=$?"
```
Both expected rc=0. If `check-explainer-delivery.py` reports `dashboard/SKILL.md is missing`, the
skill was created at the wrong path — see Step 2. If it reports that the skill *restates* the
delivery loop, the skill body is repeating commands it should be citing; remove them.

- [ ] **Step 4: Add the regen hook — the script AND its registration**

⚠ **A hook script with no entry in `.claude/settings.json` never runs**, and since the hook exits 0
unconditionally there is no signal either way. v1 described this step in prose and registered
nothing, while its own Self-Review said *"Placeholders: none. Every code step carries the code."*

Create `.claude/hooks/regen-dashboard.sh`:

```bash
#!/usr/bin/env bash
# PostToolUse hook — regenerate the dashboard whenever its ONE source is written.
#
# WHY A HOOK AND A SKILL, when regen-goals-page.sh argues against pairing the two:
# that argument is about a page whose skill would be a wrapper with nothing in it
# but "run the script". This skill has a real, non-mechanical job — WRITING THE
# ENTRY in plain language — which no script can do. The hook covers the other
# case: a human or another skill appends to the store directly.
#
# NEVER BLOCKS, NEVER FAILS THE TURN. Exits 0 unconditionally.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

FILE_PATH=$(cat | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(''); raise SystemExit
print(d.get('tool_input', {}).get('file_path', '') or '')
" 2>/dev/null) || exit 0

case "$FILE_PATH" in
  */docs/dashboard-entries.md|docs/dashboard-entries.md) ;;
  *) exit 0 ;;
esac

OUT=$(python3 "$REPO/scripts/gen-dashboard.py" 2>&1) || {
  echo "⚠  the dashboard store changed but the page was NOT regenerated:"
  echo "$OUT" | tail -4
  echo "   The page at http://127.0.0.1:7391/dashboard is now STALE."
  exit 0
}

echo "↻ dashboard regenerated — http://127.0.0.1:7391/dashboard"
exit 0
```

Then `chmod +x` it and **register it** in `.claude/settings.json`, in the existing
`PostToolUse` → `"matcher": "Edit|Write"` array, beside `regen-goals-page.sh`:

```json
            {
              "type": "command",
              "command": "bash .claude/hooks/regen-dashboard.sh",
              "statusMessage": "Refreshing the dashboard..."
            }
```

**Then prove it fires**, because "registered" is a claim about a file and "fires" is a claim about
the running system:

```bash
python3 -c "import json,pathlib; json.loads(pathlib.Path('.claude/settings.json').read_text())" \
  && echo "settings.json still parses"
```
Then append a scratch line to `docs/dashboard-entries.md` with the Edit tool (not `echo`, which the
hook does not observe) and confirm the turn prints `↻ dashboard regenerated`. **If nothing prints,
the hook is not wired** — do not proceed. Remove the scratch line afterwards; the store is
append-only for *entries*, and a scratch line was never an entry.

- [ ] **Step 5: Wire the ratchet itself into CI — this is what makes §7 real**

Append to `.github/workflows/ci.yml` after the two self-test steps from Task 4:

```yaml
      - name: dashboard entry ratchet
        if: github.event_name == 'pull_request'
        env:
          BODY: ${{ github.event.pull_request.body }}
        run: |
          printf '%s' "$BODY" > /tmp/pr-body.md
          git fetch --no-tags --depth=200 origin "$GITHUB_BASE_REF"
          python3 scripts/check-dashboard-entry.py \
            --base "origin/$GITHUB_BASE_REF" --pr-body-file /tmp/pr-body.md
```

Three things this depends on, each of which fails loudly rather than quietly:

- **The base ref must be fetched.** `actions/checkout` does not fetch the base branch by default,
  and `git diff origin/master...HEAD` against a missing ref exits non-zero → `collect()` returns an
  error → the script prints `CANNOT RUN` and returns **2**. A cannot-run is a failure, not a pass.
- **The PR body reaches the script through a FILE and an env var**, never interpolated into the
  shell. A PR body is arbitrary user text; `${{ }}` directly inside `run:` is a script-injection
  hole, and a backtick in a double-quoted bash string is command substitution — the same root cause
  as the `--body-file` and `--prompt-file` rules in `docs/dev-process.md`.
- **`--depth=200`** because the ratchet needs the merge base, not just the tip.

**Then falsify it in CI, not locally.** Open the PR (Step 7) with **no** entry in the branch and
confirm the check goes **red** with `REFUSED`; then add the entry and confirm it goes green. Until
that red has been seen on GitHub, the gate is unproven — a script that runs in CI and cannot refuse
is the formality this whole task exists to avoid.

- [ ] **Step 6: Pointer rows and the roadmap**

Two new mechanically-enforced scripts arrive with this plan, and `docs/dev-process.md` requires
*"write the script and add a pointer row above"*. Add to its "What is mechanically enforced" table:

| Check | Enforces |
|---|---|
| `scripts/check-dashboard-entry.py` | a branch that changes tracked files records a dashboard entry, or declares `NO-ENTRY: <reason>` — which the dashboard then **displays** (`--self-test`) |
| `scripts/gen-dashboard.py` | the dashboard page is derived, never hand-edited; composed through `brief-compose.py` so it cannot lose its Ask tray (`--self-test`) |

⚠ **The budget is tight and `scripts/check-docs.py:191` enforces it.** `docs/dev-process.md` was
**214 lines against a 220 limit** when this was measured — re-measure with `wc -l` before adding,
because that number moves. Two rows fit; anything longer does not. If the file is at the limit, the
right move is not to skip the rows but to shorten something else in the same PR.

Also add the dashboard to `docs/roadmap-to-launch.md`. It has a merged spec and a merged plan and
**no roadmap entry at all** — the roadmap is the compaction-proof layer, and a slice that lives only
in a plan file is invisible to the next session's reconcile.

- [ ] **Step 7: Commit and open the PR**

```bash
git add .agents/skills/dashboard/SKILL.md .claude/skills/dashboard \
        scripts/check-explainer-delivery.py .claude/hooks/regen-dashboard.sh \
        .claude/settings.json .github/workflows/ci.yml \
        docs/dev-process.md docs/roadmap-to-launch.md
git commit -F /tmp/msg-task6.txt
git log --oneline origin/master..HEAD      # confirm the branch carries ONLY this work
git push -u origin <branch>
gh pr create --title "..." --body-file /tmp/pr-body.md
```

`git log --oneline origin/master..HEAD` is not optional: a PR in this repo once silently carried a
whole other PR, with the right head SHA and a clean intended diff.

**Acceptance criteria for the PR — all four, or it is not ready:**

1. The ratchet has been **seen to refuse** on GitHub, not only locally.
2. The regen hook has been **seen to fire** on a real store write.
3. The served page has its **Ask tray**.
4. `python3 scripts/check-docs.py` and `python3 scripts/check-explainer-delivery.py` are both green.

**Merging is a human gate. Do not merge.**

---

## Self-Review

⚠ **Read this section sceptically. v1's was wrong in a way that mattered:** it asserted
*"§6.2 grammar → Task 1 (every row has a case)"* when one of §6.2's three falsifiers had neither
code nor case, another had a case whose assertion did not test what its name claimed, and a third
rule was actively violated. A self-review is the author checking their own work, and it failed in
the direction self-reviews always fail — toward believing the mapping rather than running it.

**Spec coverage, with the claims that are checked by an executable case marked ✅.**

| Spec | Where | Checked by |
|---|---|---|
| §4 what-needs-you | Task 3 Step 3 | ✅ four cases, incl. the `gh`-failure case that no longer discards the store's needs |
| §5 the chart | Tasks 2–3 | ✅ bucket cases; **✗ the "control to widen the window" is still a CLI argument** — see Gaps |
| §6.1 rendered once, not windowed | Task 3 | ✅ render cases; the marked zero-commit bar now has a case asserting a difference **outside** the visually-hidden span |
| §6.2 grammar | Task 1 | ✅ every row now has a case, **including** the unknown-resolve-id falsifier v1 omitted, the missing-space header, the empty title, tie ordering, and in-place position |
| §7 the gate | Tasks 4, 6 | ✅ refusal cases + the scratch-repo controls A–E; **display** now built (Task 2 `no_entry_prs`, Task 3) — but the CI wiring is Task 6 Step 5 and is an acceptance criterion, not an assumption |
| §8 build split | Tasks 1–4, 6 | n/a — structural |
| §9 checks | Tasks 1, 4, 5 | ✅ self-tests; the affordance probe is inherited, not restated |
| §10.1 folds | Task 5 | partial — three text-shape rows that can now go red, plus a manual two-fold check. **No automated behavioural test exists**; see Gaps |
| §10.2 store created | Task 1 Step 7 | ✅ Step 8 parses the real file |
| §10.3 `PAGE_SKILLS` | Task 6 Step 1 | ✅ via `check-explainer-delivery.py`, which **cannot enforce its own list** — stated in the step |
| §10.4 `gh` failure | Task 2 Step 5 + Task 3 | ✅ including a falsifier that runs with `gh` off the `PATH` |

**Gaps, stated rather than hidden. Four, up from two — two of them were unadmitted in v1.**

1. §5's *"control to widen the window"* is a `--window` **argument**, not an in-page control. A
   reader cannot widen it from the browser. Real shortfall; belongs in the PR description.
2. §9's affordance probe is inherited from `.agents/skills/shared/explainer-delivery.md` §5b rather
   than restated; Task 6 Step 2 cites it.
3. **Task 5 has no automated test of the actual behaviour.** The three self-test rows assert that
   text was typed in a way that a deletion turns red — that is all a static check of a JS string
   can do. The real verification is a human opening two folds and touching the file.
4. **The `NO-ENTRY:` display reads merged PRs through `gh`, so it is bounded by `--limit 40` and
   by `gh` working.** An exemption older than the last forty merged PRs stops being displayed. That
   is acceptable for a page about what changed *recently*, and it is a silent horizon, so it is
   named here rather than discovered later.

**Type consistency.** `parse_entries` returns dicts with
`id`/`date`/`ordinal`/`needs_you`/`resolves`/`error`/`raw`/`title`/`plain`/`tech`; `unresolved` and
`bucket_days` read only those keys; `build` reads those plus `bucket_days`' `commits`/`has_entry`,
and the exemption dicts' `number`/`title`/`merged`/`reason`. The dependency between the two scripts
is one-way — `gen-dashboard.py` imports `exemption_reason` from `check-dashboard-entry.py`, never
the reverse, so the gate still does not depend on the thing it guards.

**Placeholders:** none. Task 6 Step 4's hook is now code, not a description, and its registration is
a step rather than an assumption.

---

## What v2 changed

Grouped by the review finding that forced it. Nothing here was found by re-reading the plan; every
item came from running it.

| # | Change | Task |
|---|---|---|
| B1 | The Task 4 falsifier could not fire (`git stash push` on a committed file is a no-op) **and the plan told the implementer to read its success as failure**. Replaced with scratch-repo controls A–E, one of which removes the entry from the branch diff — the only input the check reads | 4 Step 6 |
| B2 | `build()` returns a fragment; v1's default `--out` wrote it straight to the served page, losing the Ask tray and the charset silently, and the regen hook would have done it on every entry. `main` now calls `brief-compose.py` and fails non-zero | 3 Step 5 |
| B3 | `[resolved:]` naming an unknown id was accepted — silent in the worst direction, leaving an item on "What needs you" forever with no diagnostic. Added a second parser pass | 1 Step 3 |
| B/H | The skill was to be created at `.claude/skills/dashboard/` as a real directory, failing two checks. Moved to `.agents/skills/` + symlink | 6 Step 2 |
| B/H | The ratchet was never wired to a PR body, so it shipped a tested script and not a gate. Wired, with an injection-safe body path, and made an acceptance criterion | 6 Step 5 |
| H1 | §7 requires `NO-ENTRY:` to be **displayed**; nothing rendered it, which is the mechanism by which the gate hollows out leaving no trace. Added `no_entry_prs` + a page section | 2, 3 |
| H3 | A malformed block always rendered at the very bottom, and the case named "rendered in place" asserted only that the string appeared somewhere | 3 |
| H4 | The zero-commit "marked" bar was marked only inside a visually-hidden span — pixel-identical on screen | 3 |
| H5 | A `gh` failure blanked "What needs you", discarding needs the local store knew — in exactly the scenario the page exists for | 3 |
| M1–M8 | Entry ids rendered; duplicate DOM ids removed; same-date ties keep file order; `unresolved` enforces "later"; the hook became code plus registration; Task 5's rows can now fail; folds key on stable ids; `##` with no space is no longer silently dropped | 1–5 |
| L1–L7 | Expected counts removed from every step (v1 said `19/19`, actual `18/18`); untitled entries rejected; `gh` output shape-checked; fenced `NO-ENTRY:` ignored; exempt paths matched as paths; a non-positive window refuses; pointer rows added | all |
| — | The roadmap has no dashboard entry at all. Added | 6 Step 6 |

**Two of v2's own defects were found by running v2, not by reading it** — recorded because they are
the argument for the method, not incidental:

1. The new pass-2 guard was written `if e["error"] or not e["resolves"]`, which treats `""` — the
   flag declared with nothing after it — as "no flag at all". The case asserting `[resolved: ]` is
   malformed **failed**. `resolves` is three-valued; a falsy test collapses two of the three.
2. Control D was written without `mkdir -p docs`. Control C's `git rm` had removed the last file in
   `docs/`, git removed the directory, the `printf` failed, nothing was committed — and D **still
   printed `REFUSED`**, because there was no entry at all. It passed without ever exercising the
   rule it names. Fixed, and paired with control E so that D alone cannot look convincing.

Both are the same shape as B1 and as `docs/portable-practices.md` §17: a check that reports success
about a subject it never reached. Writing that rule into the Global Constraints did not stop it
happening twice on the next page. **Only running it did.**

### v2.1 — a third, found by attacking v2's own new code before the reviewers saw it

Round 1's lesson was *execute the material*, so before dispatching round 2 I ran v2's additions
against their edge cases rather than re-reading them. `_ordered()` held (malformed block first,
last, several consecutively, entire file malformed — all render in place) and pass 2 held. The
exemption reader did not:

| Probe | v2 did | Should |
|---|---|---|
| `<!--`…`NO-ENTRY: x`…`-->` | **exempted the branch** | ignore |
| `    NO-ENTRY: x` (4-space indent) | exempted | ignore — Markdown code block |
| ` ``` ` opened, `~~~` "closing" it | read the line after as a declaration | ignore — a fence closes only with its own character |

**The HTML-comment case is the one that mattered.** GitHub pull-request templates put their
instructions inside `<!-- ... -->`. A template that documented this very escape hatch would have
silently exempted every branch that used it — the gate would have reported success on every PR
while enforcing nothing, and the dashboard's exemption list would have shown it happening, which is
the only reason it would ever have been caught.

**Why this is not Blocking:** it is latent, not active. Measured 2026-08-28 — this repo has **no**
`.github/PULL_REQUEST_TEMPLATE`, and PRs #170–#173 contain zero HTML comments. Nothing is exempt
today that should not be.

`exemption_reason` now tracks fences by their own character, honours the 4-space rule, and skips
HTML comments across line boundaries; 11 new self-test rows cover all of it, including the three
constructs that must **still** be read as real declarations (after a closed comment, after a closed
fence, and a 3-space indent). Re-verified after the change: generator self-test green, gate
self-test green, controls A–E unchanged, and end-to-end a commented-out `NO-ENTRY:` now refuses
while a real one passes.

A fourth, smaller: pass 2 said *"names no entry in this file"* even when the entry existed and was
merely unparseable, sending the author to hunt for a typo that was not there. It now distinguishes
the three cases.

**Round 1 verdict was NOT CONVERGED from both halves. This is v2, and it has not been reviewed.**
Round 2 must run **both** halves — they overlapped on only 2 of roughly 26 findings, which is the
measured argument against treating either as sufficient.

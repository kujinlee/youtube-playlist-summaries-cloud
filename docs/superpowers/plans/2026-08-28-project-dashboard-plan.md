# Project Dashboard Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local page at `http://127.0.0.1:7391/dashboard` showing what needs the user, what changed, and one chart of daily activity — plus the gate that makes the entries actually get written.

**Architecture:** Three pure-Python pieces on the server that already exists. `scripts/gen-dashboard.py` parses an append-only markdown store and renders a standing page; `scripts/check-dashboard-entry.py` is a CI ratchet that refuses a branch with no entry; a small change to `scripts/explainer-serve.py` makes `<details>` folds survive live reload. No new process, no new port, no new dependency.

**Tech Stack:** Python 3 standard library only (`argparse`, `re`, `datetime`, `subprocess`, `pathlib`). No pip installs. Rendering is hand-written HTML/CSS; page composition reuses `scripts/brief-compose.py`.

**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5, merged `c5fcb07`).
Section references below (§4, §5, §6.2, §7) are to that spec.

**Version: v3** — folds in **both halves of round 2**, and reorders the tasks so the gate is built
first. Round 2: Codex 3B/2H/2M, Claude 2B/8H/6M/5L, both NOT CONVERGED; twenty-three fixes in all.

**Every Python block below was executed before it was written down, and then EXTRACTED
PROGRAMMATICALLY from the file that was executed** — 33 symbols, verified byte-for-byte against the
running copy. That is not ceremony: round 2's headline Blocking was a hand transcription that
dropped one word from an assertion and reported 55/55 against a test it had weakened. The suites
stand at **70/70** (generator) and **42/42** (gate), with **19 of 19 mutations caught**.

v2 folded in round 1 of the dual adversarial plan review
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
| `scripts/check-dashboard-entry.py` | **Create FIRST.** The ratchet, **and the owner of the entry-header grammar**. |
| `docs/dashboard-entries.md` | **Create.** The append-only store. Owned by humans and the skill, never rewritten by a script. |
| `scripts/gen-dashboard.py` | **Create.** Parse the store, derive activity, open PRs and recorded `NO-ENTRY:` exemptions, then **compose and write** `~/explainers/dashboard.html` via `brief-compose.py`. |
| `scripts/explainer-serve.py` | **Modify.** Persist `<details>` open state across live reload. |
| `scripts/check-explainer-delivery.py` | **Modify** (`:53`). Add `dashboard` to `PAGE_SKILLS`. |
| `.agents/skills/dashboard/SKILL.md` | **Create — the real file.** |
| `.claude/skills/dashboard` | **Create — a SYMLINK** to `../../.agents/skills/dashboard`. |
| `.claude/hooks/regen-dashboard.sh` + `.claude/settings.json` | **Create + modify.** A hook with no settings entry never runs. |
| `.github/workflows/ci.yml` | **Modify.** `fetch-depth: 0`, both `--self-test`s, **and the ratchet itself**. |
| `docs/dev-process.md` | **Modify.** One pointer row per new mechanically-enforced script. |
| `docs/roadmap-to-launch.md` | **Modify — UPDATE the existing section**, do not add one. |
| `tests/` | **Not used.** Standalone scripts with built-in `--self-test`, following every existing `scripts/check-*.py`. |

⚠ **The skill path is not a preference.** All twenty existing skills are a real directory under
`.agents/skills/` plus a symlink from `.claude/skills/`, and `scripts/check-explainer-delivery.py:46`
sets `SKILLS = ROOT / ".agents" / "skills"`. A real directory under `.claude/skills/` fails
`check_skill_symlinks` in `scripts/check-docs.py` **and** makes the delivery check report
`dashboard/SKILL.md is missing`.

### ⛔ Why the gate is Task 1 and the parser is Task 2

The ratchet and the page must agree on what an entry header **is**, or the gate passes branches whose
entry the page renders under *"Could not parse this entry"*. Round 2 measured **five** header shapes
where they disagreed while the plan claimed they could not.

One grammar, therefore, and it lives in `check-dashboard-entry.py`. `gen-dashboard.py` imports it.
The arrow points **generator → gate** and never the reverse: a *gate* must not import the thing it
guards, but a page importing a gate is what keeps the two readings identical by construction.

That import is why the order changed. Fixing the disagreement by sharing a definition creates a
dependency, and a dependency has an order — building the parser first would recreate the exact
task-ordering defect round 2 filed twice (a step whose stated outcome cannot occur because the file
it needs arrives two tasks later).

---

## Task 1: The gate, and the grammar it owns

**Files:** Create `scripts/check-dashboard-entry.py`.

**Interfaces:**
- Consumes: nothing.
- Produces: `verdict(changed, added_entry, pr_body) -> (exit_code, reason)`; and the shared
  grammar `header_error(line) -> str | None`, `valid_date`, `HEADER`, `FLAG`.

- [ ] **Step 1: Write the failing test**

Create the file with the imports, the constants, the grammar, a stub, and the self-test.

⚠ **`import re` belongs in THIS block.** v2.1 added `FENCE = re.compile(...)` above the block that
imported `re`, so Step 2's expected `NotImplementedError` was really a `NameError` and Step 4's
green was unreachable. Both prior reviewers assembled the *final* file and never executed the
intermediate states this task prescribes.

```python
#!/usr/bin/env python3
"""Refuse a branch that changes tracked files and records no dashboard entry.

    python3 scripts/check-dashboard-entry.py             # against origin/master..HEAD
    python3 scripts/check-dashboard-entry.py --self-test
"""
from __future__ import annotations
import argparse
import datetime as _dt
import re
import subprocess
import sys


def verdict(changed: list[str], added_entry: bool, pr_body: str) -> tuple[int, str]:
    raise NotImplementedError
```

then the constants and the grammar:

```python
EXEMPT_DIRS = ("docs/reviews/",)

EXEMPT_FILES = ("docs/dashboard-entries.md",)

NO_ENTRY = "NO-ENTRY:"

HEADER = re.compile(r"^## (\S+)(.*)$")

FLAG = re.compile(r"\[(needs-you|resolved:\s*[^\]]*)\]")

def valid_date(s: str) -> bool:
    try:
        _dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False

def header_error(line: str) -> str | None:
    """None if `line` is a well-formed entry header, else why not.

    Shared by the parser and the ratchet so they CANNOT disagree about what a
    header is. v2.2 claimed they already agreed; measured, they diverged on
    five shapes — `## D-foo`, `## D.`, a typo'd flag, an unknown-flag payload,
    and a title on the header line — each of which the ratchet waved through
    while the page rendered it under "Could not parse this entry".
    """
    m = HEADER.match(line)
    if m is None:
        return "header must be '## ' then a YYYY-MM-DD date — check the space after the ##"
    if not valid_date(m.group(1)):
        return f"not a real calendar date: {m.group(1)!r}"
    leftover = FLAG.sub("", m.group(2)).strip()
    if leftover:
        return f"unrecognised text in header: {leftover!r}"
    return None

def _added_entry_line(line: str) -> bool:
    return line.startswith("+") and header_error(line[1:]) is None
```

and the self-test from Step 4 below, with `if __name__ == "__main__": sys.exit(_self_test())`.

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/check-dashboard-entry.py --self-test`
Expected: **`NotImplementedError`**, non-zero exit. If you see a `NameError`, an import is missing
from Step 1 — that is the defect this step was rewritten to catch.

- [ ] **Step 3: Implement the exemption reader and the verdict**

```python
FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")

def _indented(text: str) -> bool:
    """4+ COLUMNS of leading whitespace = a Markdown indented code block.

    A tab advances to the next 4-column stop, which CommonMark applies BEFORE
    block parsing. Counting spaces alone let a tab-indented declaration exempt
    a branch — measured.
    """
    col = 0
    for ch in text:
        if ch == " ":
            col += 1
        elif ch == "\t":
            col += 4 - (col % 4)
        else:
            break
        if col >= 4:
            return True
    return False

def exemption_reason(pr_body: str) -> str | None:
    """The reason after a line-leading `NO-ENTRY:`, or None.

    ONE DEFINITION, shared with gen-dashboard.py, so the page displays exactly
    the exemptions the gate granted (spec §7). An exemption must be DELIBERATE,
    so anything a Markdown reader treats as inert does not count: fenced code
    (closed only by its own character), indented code (4+ columns, tabs
    included), HTML comments across lines, and blockquotes.
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
                # The head runs through the SAME indent rule as a bare line. It
                # did not, so an indented declaration exempted the moment the
                # line also carried a comment — measured.
                if not _indented(head) and head.strip().startswith(NO_ENTRY):
                    return head.strip()[len(NO_ENTRY):].strip() or ""
        if in_comment or not probe or _indented(probe):
            continue
        s = probe.strip()
        if s.startswith(NO_ENTRY):
            return s[len(NO_ENTRY):].strip() or ""
    return None

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

⚠ `reason` is **three-valued** and the branch order matters: a non-empty string exempts, `""` means
the marker was present with nothing after it and must **refuse**, `None` means absent. `if reason:`
alone would treat "declared with no reason" as "not declared".

- [ ] **Step 4: Add the self-test and run it**

```python
def _self_test() -> int:
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
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
    case("mixed exempt and real is refused", verdict(["docs/reviews/r.md", "lib/x.ts"], False, "")[0], 1)
    case("refusal explains itself", "entry" in verdict(["lib/x.ts"], False, "")[1].lower(), True)
    case("NO-ENTRY reason is echoed", "typo fix" in verdict(["lib/x.ts"], False, "NO-ENTRY: typo fix")[1], True)
    case("a lookalike filename is NOT exempt", verdict(["docs/dashboard-entries.md.bak"], False, "")[0], 1)
    case("a lookalike directory is NOT exempt", verdict(["docs/reviews-not-really/x.ts"], False, "")[0], 1)

    fenced = "```\nNO-ENTRY: example from the docs\n```"
    case("NO-ENTRY inside a code fence does not exempt", verdict(["lib/x.ts"], False, fenced)[0], 1)
    case("exemption_reason reads a real declaration", exemption_reason("NO-ENTRY: typo fix"), "typo fix")
    case("exemption_reason distinguishes empty from absent",
         (exemption_reason("NO-ENTRY:"), exemption_reason("nothing here")), ("", None))

    for name, body, want in [
        ("fenced ```",                  fenced,                                        None),
        ("fenced with ~~~",             "~~~\nNO-ENTRY: inside\n~~~",                  None),
        ("unterminated fence",          "```\nNO-ENTRY: inside\n",                     None),
        ("``` is not closed by ~~~",    "```\nNO-ENTRY: a\n~~~\nNO-ENTRY: b\n",        None),
        ("indented code block",         "    NO-ENTRY: indented\n",                    None),
        ("TAB-indented code block",     "\tNO-ENTRY: tabbed\n",                        None),
        ("indented, with a comment later on the line",
                                        "    NO-ENTRY: sneaky <!-- c -->\n",           None),
        ("multi-line HTML comment",     "<!--\nNO-ENTRY: commented out\n-->\n",        None),
        ("one-line HTML comment",       "<!-- NO-ENTRY: nope -->\n",                   None),
        ("blockquoted",                 "> NO-ENTRY: quoted\n",                        None),
        ("lowercase is not the marker", "no-entry: lower\n",                           None),
        ("CRLF body still reads",       "NO-ENTRY: crlf\r\n",                        "crlf"),
        ("after a CLOSED comment",      "<!-- hint --> NO-ENTRY: real one\n",    "real one"),
        ("after a CLOSED fence",        "```\ncode\n```\nNO-ENTRY: real one\n",  "real one"),
        ("3 spaces is still a declaration", "   NO-ENTRY: ok\n",                       "ok"),
    ]:
        case(f"exemption_reason — {name}", exemption_reason(body), want)

    # ─── the header grammar, shared with the parser ───
    case("a real date header counts", _added_entry_line("+## 2026-08-28"), True)
    case("a flagged header counts", _added_entry_line("+## 2026-08-28 [needs-you]"), True)
    case("a non-date header does NOT count", _added_entry_line("+## not-a-date"), False)
    case("an impossible date does NOT count", _added_entry_line("+## 2026-02-30"), False)
    case("a REMOVED header does not count", _added_entry_line("-## 2026-08-28"), False)
    case("'##' with no space does NOT count", _added_entry_line("+##2026-08-28"), False)
    # The five shapes v2.2 claimed could not diverge, and did.
    case("a suffixed date does NOT count", _added_entry_line("+## 2026-08-28-foo"), False)
    case("a trailing dot does NOT count", _added_entry_line("+## 2026-08-28."), False)
    case("a typo'd flag does NOT count", _added_entry_line("+## 2026-08-28 [needs-yo]"), False)
    case("a title on the header line does NOT count",
         _added_entry_line("+## 2026-08-28 rambling title text"), False)
    case("header_error names the space", "space" in (header_error("##2026-08-28") or ""), True)
    case("header_error is None on a good header", header_error("## 2026-08-28 [needs-you]"), None)

    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0
```

Run: `python3 scripts/check-dashboard-entry.py --self-test`
Expected: exit 0, no `[FAIL]` lines. **Do not check the count** — see Global Constraints.

- [ ] **Step 5: Add the git collector and `main`**

```python
def collect(base: str) -> tuple[list[str], bool, str | None]:
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
```

- [ ] **Step 6: Prove it passes, then make it actually go RED**

⛔ **No `set -e` in this script, and that is not an oversight.** Controls A, C and D are *expected*
to exit non-zero — that is the whole point. With `set -e` the script dies at Control A on its first
correct refusal, never prints a verdict line, and never reaches B–E. Measured by the round-2
reviewer running the previous version verbatim.

⛔ **Do NOT use `git stash push docs/dashboard-entries.md`.** On a committed file it prints
*"No local changes to save"*, does nothing, exits 0 — and the earlier version of this plan then
told the implementer that success meant the gate was broken. The only input `collect()` has is
`git diff <base>...HEAD`; a falsifier must change **that**.

```bash
D=$(mktemp -d); cd "$D" || exit 1
git init -q .; git config user.email t@t; git config user.name t
mkdir -p docs scripts
cp "$OLDPWD/scripts/check-dashboard-entry.py" scripts/
git add -A; git commit -qm base; git branch -M master; git checkout -qb feature

# A — code changed, no entry anywhere. MUST refuse.
mkdir -p lib; echo "x" > lib/x.ts; git add -A; git commit -qm code
python3 scripts/check-dashboard-entry.py --base master; echo "A rc=$?"

# B — an entry is added. MUST pass.
printf '## 2026-08-28\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm entry
python3 scripts/check-dashboard-entry.py --base master; echo "B rc=$?"

# C — THE FALSIFIER: the entry is removed by a commit, so it leaves the branch diff.
git rm -q docs/dashboard-entries.md; git commit -qm remove
python3 scripts/check-dashboard-entry.py --base master; echo "C rc=$?"

# D — the header is present but NOT a real date. MUST refuse.
# `mkdir -p docs` is NOT optional: C's `git rm` removed the last file in docs/ and
# git removed the directory with it. Without this the printf fails, nothing is
# committed, and D refuses because there is still no entry AT ALL — passing
# without ever exercising the date rule. MEASURED.
mkdir -p docs
printf '## not-a-date\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm baddate
git diff -U0 master...HEAD -- docs/dashboard-entries.md | grep '^+##'   # must print +## not-a-date
python3 scripts/check-dashboard-entry.py --base master; echo "D rc=$?"

# E — the same commit with a REAL date must pass. Without E, D proves only that
# something refused, not that the DATE was why.
printf '## 2026-08-28\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm gooddate
python3 scripts/check-dashboard-entry.py --base master; echo "E rc=$?"

# F — the five shapes the ratchet used to wave through. ALL must refuse.
for h in '## 2026-08-28-foo' '## 2026-08-28.' '## 2026-08-28 [needs-yo]' \
         '## 2026-08-28 rambling title' '##2026-08-28'; do
  printf '%s\nBody.\n' "$h" > docs/dashboard-entries.md
  git add -A; git commit -qm t >/dev/null
  python3 scripts/check-dashboard-entry.py --base master >/dev/null
  printf '  %-32s rc=%s\n' "$h" "$?"
done
cd "$OLDPWD"; rm -rf "$D"
```

Required output — **all of it, or the gate is not proven**:

```
REFUSED — …                       A rc=1
ok — an entry block was added     B rc=0
REFUSED — …                       C rc=1
+## not-a-date                    (D's grep — if absent, D is vacuous)
REFUSED — …                       D rc=1
ok — an entry block was added     E rc=0
  ## 2026-08-28-foo                 rc=1
  ## 2026-08-28.                    rc=1
  ## 2026-08-28 [needs-yo]          rc=1
  ## 2026-08-28 rambling title      rc=1
  ##2026-08-28                      rc=1
```

**If A, C, D or any F row prints `ok`, the gate does not work — stop and fix it.** C is the
falsifier proper; D and E are a matched pair, because D alone can pass for the wrong reason.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-dashboard-entry.py
git commit -F /tmp/msg-task1.txt
```

---

## Task 2: The entry store and its parser

**Files:** Create `docs/dashboard-entries.md`, `scripts/gen-dashboard.py`.

**Interfaces:**
- Consumes: `header_error`, `valid_date`, `HEADER`, `FLAG` from Task 1's gate.
- Produces: `parse_entries(text) -> list[dict]`. Keys: `date`, `ordinal`, `id`, `title`, `plain`,
  `tech`, `needs_you`, `resolves` (**a list**), `error`, `raw`. When `error` is non-None every field
  except `raw`, `error` and `id` is unreliable and the renderer shows `raw`.

- [ ] **Step 1: The module header and the grammar import**

```python
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

_GATE = _gate_module()

header_error = _GATE.header_error

FLAG = _GATE.FLAG

HEADER = _GATE.HEADER
```

with `TECH_MARKER = "<!--tech-->"` and `BLOCK = re.compile(r"^##\s*\S")` above them.

⚠ **`BLOCK` is loose and `HEADER` is strict, deliberately.** `BLOCK` decides what *starts* an entry,
so `##2026-08-28` is still CAPTURED rather than vanishing without a trace. `HEADER` decides whether
the captured block is *well-formed*, and it requires the space — so a missing space is a malformed
entry: visible, explained, and refused by the ratchet.

- [ ] **Step 2: Write the failing test**, then Step 3 implements. Same TDD shape as Task 1:
a `parse_entries` stub raising `NotImplementedError`, the six basic cases, run, see red.

- [ ] **Step 3: Implement the parser**

```python
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
                 "date": None, "ordinal": 0, "id": None, "title": "", "plain": "", "tech": None}
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
            elif any(o["id"] == r for o in out):
                e["error"] = (f"[resolved: {r}] names an entry that could not be "
                              f"parsed — fix that entry first")
            else:
                e["error"] = f"[resolved: {r}] names no entry in this file"
            break
    return out
```

- [ ] **Step 4: Add the malformed and edge cases, and run**

Cases for: a bad date · an unknown flag · two entries on one date · the tech marker · an inline
marker · an indented `##` · an empty file · a valid resolve · **an unknown resolve id** · **an empty
resolve id** · **two `[resolved:]` flags on one header** · `##` with no space · an entry with no
title · **a malformed block still consuming its ordinal**. All are in the assembled `_self_test`
in Task 4 Step 4.

Expected: exit 0, no `[FAIL]` lines.

- [ ] **Step 5: Create the store with its first real entry**

```markdown
# Dashboard entries

Append-only. One `## YYYY-MM-DD` block per entry; **newest at the end**.
Nothing here is edited or deleted — corrections are appended.
Grammar: `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2.
Rendered by `scripts/gen-dashboard.py`; enforced by `scripts/check-dashboard-entry.py`.

## 2026-08-28
Started building the dashboard — a page that shows what changed while you were away.
<!--tech-->
Spec v5 merged as `c5fcb07`. Task 2 of `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`.
```

⚠ **"Newest at the end" is load-bearing**, not a formatting preference: `_ordered` in Task 4 places
malformed blocks relative to their file neighbours, and the render reverses this file.

- [ ] **Step 6: Verify the real store parses**, then commit.

Expected: `1 entries; [None]`.

---

## Task 3: Activity, open pull requests, and recorded exemptions

**Files:** Modify `scripts/gen-dashboard.py`.

**Interfaces:**
- Produces: `unresolved(entries)`, `bucket_days(dates, entries, window, today)`, and the impure
  collectors `commit_dates`, `open_prs`, `no_entry_prs`.

- [ ] **Step 1: Write the failing tests**, then implement:

```python
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
```

⚠ `unresolved` iterates `e["resolves"]` as a **list**. Spec §6.2 says flags are "zero or more"; a
scalar field silently discarded the first of two `[resolved:]` flags, clearing one item and leaving
the other open forever with `error: None`.

- [ ] **Step 2: Add the impure collectors, kept out of the self-test**

`commit_dates(window)` and `open_prs()` return `(value, None)` or `(None, why)` — never a bare `[]`
on failure, because *"nothing open"* and *"could not ask"* must not look alike.

`no_entry_prs(limit=40)` reads merged PR bodies through `gh` and extracts `NO-ENTRY:` declarations
using **the gate's** `exemption_reason`, so the page displays exactly the exemptions the gate
granted. Spec §7 requires this to be **displayed**: without it nothing counts exemptions, nobody can
see *"eleven of the last twelve branches skipped their entry"*, and the page goes on looking healthy
while describing less and less.

⚠ **Bounded at 40 merged PRs.** An exemption older than that stops being displayed. Acceptable for a
page about recent change, and a silent horizon, so it is named here.

- [ ] **Step 3: Verify `commit_dates` and `open_prs` against the real repo**

Expected: a non-zero date count with `err: None`; `prs: 0 err: None` is correct when nothing is open.

⛔ **Do NOT verify `no_entry_prs()` here.** It imports from `check-dashboard-entry.py` — which now
exists, because the gate is Task 1 — but its meaningful check needs a synthetic body, so it lives in
Task 6 Step 5 beside the CI wiring.

**Then falsify the could-not-tell contract**, with `gh` off the `PATH`:

```bash
PATH=/usr/bin:/bin python3 -c "…"
```
Expected: `prs: None err: could not run gh: …`. **If it prints `0` with `err: None`, the collector
is reporting "nothing" where it means "could not ask" — stop and fix it.**

---

## Task 4: Render the page

**Files:** Modify `scripts/gen-dashboard.py`.

- [ ] **Step 1: Write the failing tests** — the full assembled `_self_test` is in Step 4.

- [ ] **Step 2: Implement the helpers**

```python
def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", s or "")

def _ordered(entries: list[dict]) -> list[dict]:
    """Newest date first; ties keep FILE order; a malformed block stays adjacent
    to its file neighbours (spec §6.2, 'rendered in place').

    Valid entries sort by (date descending, file order within a date). A
    malformed block has no usable date, so it is SPLICED back in: immediately
    after whichever of its two file-neighbours renders FIRST.

    That formulation is order-agnostic, and it has to be. v2.2 gave the block
    its preceding neighbour's date and certified it with a fixture written
    newest-FIRST — but the store is written newest-at-the-END (Task 1 Step 7,
    "Append one block"), so the render reverses the file and the block fell to
    the bottom of the page: the exact defect this function exists to fix,
    invisible under the one ordering the fixture used. Keying off a date also
    could not satisfy "ties keep file order" at the same time, because within a
    borrowed date group the malformed block must sit AFTER the entry it
    borrowed from while a genuine tie keeps file order. Splicing separates the
    two rules instead of trying to encode both in one sort key.
    """
    valid = [(i, e) for i, e in enumerate(entries) if not e["error"]]
    order = sorted(valid, key=lambda p: (p[1]["date"] or "", -p[0]), reverse=True)
    rank = {i: r for r, (i, _) in enumerate(order)}
    out = [e for _, e in order]
    for i, e in enumerate(entries):
        if not e["error"]:
            continue
        before = max((j for j, _ in valid if j < i), default=None)
        after = min((j for j, _ in valid if j > i), default=None)
        cands = [j for j in (before, after) if j is not None]
        if not cands:
            out.append(e)
            continue
        anchor = min(cands, key=lambda j: rank[j])
        out.insert(out.index(entries[anchor]) + 1, e)
    return out

def _bar(day: dict, tallest: int) -> str:
    h = 4 if day["commits"] == 0 else max(6, round(48 * day["commits"] / max(tallest, 1)))
    quiet = day["has_entry"] and day["commits"] == 0     # §6.1
    unwritten = day["commits"] > 0 and not day["has_entry"]  # §9 / §7.3
    cls = "bar needs" if day["needs_you"] else "bar"
    if quiet:
        cls += " marked"
    if unwritten:
        cls += " unwritten"
    label = (f'{day["date"]}: {day["commits"]} commits'
             f'{", needs you" if day["needs_you"] else ""}'
             f'{", entry with no commits" if quiet else ""}'
             f'{", SHIPPED WITH NO ENTRY" if unwritten else ""}')
    # Every mark is a REAL element or class, never text inside .vh: §6.1 asks
    # for "visible rather than invisible", and title/aria-label are neither.
    mark = '<span class="dot" aria-hidden="true"></span>' if quiet else ""
    if unwritten:
        mark += '<span class="gapmark" aria-hidden="true"></span>'
    # A bar only links where there is an entry to land on — the anchor is
    # emitted while iterating entries, so a link on a day without one goes
    # nowhere (spec §5).
    tag = "a" if day["has_entry"] else "span"
    href = f' href="#day-{day["date"]}"' if day["has_entry"] else ""
    return (f'<{tag} class="{cls}"{href} style="height:{h}px" '
            f'title="{_html.escape(label)}" aria-label="{_html.escape(label)}">'
            f'{mark}<span class="vh">{_html.escape(label)}</span></{tag}>')

GLOSSARY = [
    ("needs you", "a decision is waiting on you — nothing else on the page is asking for anything"),
    ("entry", "one dated block you or the assistant wrote, in plain words, about what changed"),
    ("no entry recorded", "a branch was merged with its entry deliberately skipped, and said why"),
    ("shipped with no entry", "a day with commits and nothing written about them — the gap the entry rule exists to close"),
]
```

- [ ] **Step 3: Implement `build`**

```python
def build(entries, days, prs, pr_error, git_error, window,
          exemptions, exempt_error) -> str:
    # ─── What needs you ───
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
        needs_html = pr_note
    else:
        needs_html = '<p class="none">Nothing needs you.</p>'

    # ─── The chart ───
    if git_error:
        chart = (f'<p class="unknown">Could not read the git history — '
                 f'{_html.escape(git_error)}</p>')
    elif not days:
        chart = (f'<p class="unknown">No days to show — the window is '
                 f'{_html.escape(str(window))}. Pass --window with a positive number.</p>')
    else:
        tallest = max((d["commits"] for d in days), default=0)
        chart = "".join(_bar(d, tallest) for d in reversed(days))
    # §5: the count is commits, and it under-counts work that was never committed.
    chart_note = ('<p class="note">One bar per day, oldest on the left. It counts commits, '
                  'so work that was never committed does not appear here.</p>')

    # ─── What changed ───
    if not entries:
        entries_html = ('<p class="none">No entries yet. They live in '
                        '<code>docs/dashboard-entries.md</code>.</p>')
    else:
        parts, anchored = [], set()
        for i, e in enumerate(_ordered(entries)):
            eid = _slug(e["id"]) if e["id"] else f"bad-{i}"
            day_anchor = ""
            if e["date"] and not e["error"] and e["date"] not in anchored:
                anchored.add(e["date"])
                day_anchor = f'<span class="anchor" id="day-{_html.escape(e["date"])}"></span>'
            if e["error"]:
                parts.append(
                    f'{day_anchor}<article class="entry broken" id="{eid}">'
                    f'<p class="err">Could not parse this entry — {_html.escape(e["error"])}</p>'
                    f'<pre>{_html.escape(e["raw"])}</pre></article>')
                continue
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

    # ─── Recorded exemptions (spec §7) ───
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

    glossary_html = ('<details id="glossary"><summary>What the words on this page mean</summary>'
                     '<dl>' + "".join(
                         f'<dt>{_html.escape(t)}</dt><dd>{_html.escape(d)}</dd>'
                         for t, d in GLOSSARY) + '</dl></details>')

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
.note{{color:var(--fg3);font-size:13px;margin:8px 0 0}}
.unknown{{color:var(--err);background:var(--err-bg);padding:10px 14px;border-radius:4px}}
ul.needs{{list-style:none;padding:0}} ul.needs li{{background:var(--need-bg);
border-left:3px solid var(--need);padding:10px 14px;margin-bottom:8px;border-radius:0 4px 4px 0}}
.when{{font-family:var(--mono);font-size:11px;color:var(--fg3)}}
.chart{{display:flex;align-items:flex-end;gap:4px;height:56px;padding:8px 8px 14px;
background:var(--panel);border:1px solid var(--rule);border-radius:4px;overflow-x:auto}}
.bar{{position:relative;flex:1;min-width:8px;background:var(--ok);
border-radius:2px 2px 0 0;display:block}}
.bar.needs{{background:var(--need)}}
.bar.marked{{outline:2px solid var(--need);outline-offset:1px}}
.bar.unwritten{{background:repeating-linear-gradient(45deg,var(--err) 0 3px,transparent 3px 6px),
var(--err-bg);border:1px solid var(--err)}}
.bar .dot{{position:absolute;left:50%;bottom:-11px;width:6px;height:6px;
margin-left:-3px;border-radius:50%;background:var(--need)}}
.bar .gapmark{{position:absolute;left:0;right:0;top:-6px;height:3px;background:var(--err)}}
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
#glossary dt{{font-weight:600;margin-top:8px}} #glossary dd{{margin:2px 0 0;color:var(--fg3)}}
pre{{white-space:pre-wrap;font-family:var(--mono);font-size:12.5px;overflow-x:auto}}
:focus-visible{{outline:2px solid var(--need);outline-offset:2px}}
</style>
<div class="shell">
<h1>Project dashboard</h1>
<h2>What needs you</h2>{needs_html}
<h2>The last {window} days</h2><div class="chart">{chart}</div>{chart_note}
<h2>What changed</h2>{entries_html}
<h2>Branches that skipped their entry</h2>{exempt_html}
<h2>Words</h2>{glossary_html}
<h2>Elsewhere</h2><ul>
<li><a href="/goals">Goals</a></li><li><a href="/backlog-table">Backlog</a></li>
<li><a href="/latest">Newest briefing</a></li><li><a href="/">All pages</a></li></ul>
</div>"""
```

⚠ **The `{`/`}` escapes are load-bearing.** This is one f-string containing CSS; every literal
brace is doubled. An unbalanced brace is a `SyntaxError` at import time, which takes the self-test
down with it.

- [ ] **Step 4: The assembled self-test**

```python
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
    case("resolves parsed", res[1]["resolves"], ["2026-08-28/1"])
    case("valid resolve is not an error", res[1]["error"], None)
    ghost = parse_entries("## 2026-08-29 [resolved: 1999-01-01/9]\nDone.\n")
    case("resolve of an unknown id is an error", ghost[0]["error"] is not None, True)
    empty_res = parse_entries("## 2026-08-29 [resolved: ]\nDone.\n")
    case("resolve with an empty id is an error", empty_res[0]["error"] is not None, True)

    # spec §6.2 allows "zero or more" flags — a SECOND [resolved:] used to be
    # silently discarded, clearing one item and leaving the other open forever.
    twin = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-26 [needs-you]\nB.\n"
                         "## 2026-08-27 [resolved: 2026-08-26/1] [resolved: 2026-08-26/2]\nBoth.\n")
    case("two [resolved:] flags are both kept", twin[2]["resolves"],
         ["2026-08-26/1", "2026-08-26/2"])
    case("two [resolved:] flags clear BOTH items", [x["id"] for x in unresolved(twin)], [])

    nospace = parse_entries("##2026-08-28\nNo space after the hashes.\n")
    case("'##' with no space is still an entry", len(nospace), 1)
    case("'##' with no space is MALFORMED", nospace[0]["error"] is not None, True)
    case("'##' with no space says why", "space" in (nospace[0]["error"] or ""), True)
    notitle = parse_entries("## 2026-08-28\n\n\n")
    case("entry with no title is an error", notitle[0]["error"] is not None, True)

    # A malformed block must not RENUMBER its neighbours: repairing a typo'd
    # flag would otherwise silently rebind a standing [resolved:].
    unstable = parse_entries("## 2026-08-28 [needs-yo]\nTypo.\n## 2026-08-28\nReal one.\n")
    case("a malformed block still consumes its ordinal",
         [x["id"] for x in unstable], ["2026-08-28/1", "2026-08-28/2"])

    ents = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-27\nB.\n"
                         "## 2026-08-28 [resolved: 2026-08-26/1]\nC.\n")
    case("unresolved is empty after resolve", [x["id"] for x in unresolved(ents)], [])
    ents2 = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-27\nB.\n")
    case("unresolved before resolve", [x["id"] for x in unresolved(ents2)], ["2026-08-26/1"])
    self_res = parse_entries("## 2026-08-26 [needs-you] [resolved: 2026-08-26/1]\nA.\n")
    case("an entry cannot resolve itself", [x["id"] for x in unresolved(self_res)], ["2026-08-26/1"])
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

    def _B(entries, days, prs=(), pr_error=None, git_error=None, window=2,
           exemptions=(), exempt_error=None):
        return build(entries, days, list(prs) if prs is not None else None, pr_error,
                     git_error, window, list(exemptions) if exemptions is not None else None,
                     exempt_error)

    def _section(html, heading):
        return html.split(f"<h2>{heading}</h2>", 1)[1].split("<h2>", 1)[0]

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
    case("gh failure is announced as NOT CHECKED", "not checked" in html_err.lower(), True)
    case("gh failure surfaces the reason", "gh exploded" in html_err, True)

    # §4's OTHER source. Every fixture used to pass an empty or None PR list, so
    # the gh half of "what needs you" could be deleted with the suite still green.
    html_prs = _B([], bucket_days([], [], 2, "2026-08-28"),
                  prs=[{"number": 42, "title": "Open thing"}])
    needs_prs = _section(html_prs, "What needs you")
    case("an open PR appears in what-needs-you", "Open thing" in needs_prs, True)
    case("the open PR is numbered", "#42" in needs_prs, True)

    bad3 = parse_entries("## 2026-99-99\nBroken.\n")
    html_bad = _B(bad3, bucket_days([], bad3, 2, "2026-08-28"))
    case("malformed says it could not parse", "could not parse" in html_bad.lower(), True)
    case("malformed keeps its raw text", "Broken." in html_bad, True)

    # H5's real assertion: the store's needs survive a gh failure IN THEIR OWN
    # SECTION. Asserting against the whole page passed on the title's copy in
    # "What changed" — i.e. on exactly the defect it names.
    need_html = _B(ents3, d3, prs=None, pr_error="gh exited 1: auth")
    case("a gh failure still shows the store's needs IN THAT SECTION",
         "Decide the thing." in _section(need_html, "What needs you"), True)

    # "In place" on the order the store is ACTUALLY written: newest at the END.
    appended = parse_entries("## 2026-08-27\nOlder good.\n"
                             "## 2026-02-30\nBroken middle.\n"
                             "## 2026-08-28\nNewest good.\n")
    ha = _B(appended, bucket_days([], appended, 2, "2026-08-28"))
    case("malformed renders BETWEEN its neighbours on an APPENDED store",
         ha.index("Newest good.") < ha.index("Broken middle.") < ha.index("Older good."), True)
    case("newest date renders first on an APPENDED store",
         ha.index("Newest good.") < ha.index("Older good."), True)

    tie = parse_entries("## 2026-08-28\nFIRST in file.\n## 2026-08-28\nSECOND in file.\n")
    ht = _B(tie, bucket_days([], tie, 2, "2026-08-28"))
    case("same-date ties keep file order",
         ht.index("FIRST in file.") < ht.index("SECOND in file."), True)
    case("the entry id is rendered", "2026-08-28/1" in ht, True)
    all_ids = re.findall(r'\sid="([^"]+)"', ht)
    case("no duplicate DOM ids", len(all_ids), len(set(all_ids)))
    case("every details has an id", ht.count("<details id="), ht.count("<details"))

    def _marks(bar):
        """What a SIGHTED reader can tell apart: the bar's own classes and its
        child elements. Deliberately ignores the tag, href, style, title and
        aria-label — title needs a hover, aria is not drawn, and the tag/href
        differ for an unrelated reason (a bar only links where an entry exists),
        which would let this assertion pass with every mark deleted."""
        # Scan the OPENING TAG and the CHILDREN separately. A single regex over
        # the whole string picked up the container's own class as a child the
        # moment the container became a <span> (a bar with no entry does not
        # link), which made the two bars differ for a reason unrelated to the
        # mark — the assertion passed with every mark deleted. MEASURED.
        cut = bar.index(">") + 1
        cls = re.search(r'class="([^"]*)"', bar[:cut])
        kids = [k for k in re.findall(r'<span class="([^"]*)"', bar[cut:]) if k != "vh"]
        return (cls.group(1) if cls else "", kids)

    quiet = _bar({"date": "D", "commits": 0, "needs_you": False, "has_entry": True}, 5)
    plainb = _bar({"date": "D", "commits": 0, "needs_you": False, "has_entry": False}, 5)
    case("§6.1 a zero-commit day WITH an entry is marked in SIGHTED output",
         _marks(quiet) != _marks(plainb), True)

    # §9 / §7.3: a day WITH commits and NO entry is the gap the rule exists to close.
    gap = _bar({"date": "D", "commits": 7, "needs_you": False, "has_entry": False}, 7)
    written = _bar({"date": "D", "commits": 7, "needs_you": False, "has_entry": True}, 7)
    case("§9 a day that shipped with NO entry is marked in SIGHTED output",
         _marks(gap) != _marks(written), True)
    case("that mark is named for a reader", "no entry" in gap.lower(), True)

    # §5: a bar only links where there is an entry to land on.
    case("a bar with no entry is not a dead link", 'href="#day-' in gap, False)
    case("a bar with an entry does link", 'href="#day-' in written, True)

    chart_only = _section(_B(ents3, d3), "The last 2 days")
    case("the chart says what it under-counts", "never committed" in chart_only, True)
    # oldest-left: the OLDER day must be drawn before the newer one.
    d2 = bucket_days(["2026-08-28"], [], 2, "2026-08-28")
    two_bars = _section(_B([], d2), "The last 2 days")
    case("the chart draws oldest-first (left to right)",
         two_bars.index("2026-08-27") < two_bars.index("2026-08-28"), True)

    hx = _B([], bucket_days([], [], 2, "2026-08-28"),
            exemptions=[{"number": 9, "title": "T", "merged": "2026-08-28", "reason": "typo fix"}])
    case("a recorded exemption is displayed", "typo fix" in hx, True)
    case("the exemption names its pull request", "#9" in hx, True)
    hxe = _B([], bucket_days([], [], 2, "2026-08-28"), exemptions=None, exempt_error="gh exploded")
    case("an unreadable exemption list says so", "could not" in hxe.lower(), True)

    hz = _B([], bucket_days([], [], 0, "2026-08-28"), window=0)
    case("a zero window says so rather than drawing an empty box",
         "could not" in hz.lower() or "no days" in hz.lower(), True)

    words = _section(_B([], d2), "Words")
    case("the page carries a glossary", "<dl>" in words, True)
    case("the glossary defines its terms",
         "a decision is waiting on you" in words, True)

    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0
```

Run: `python3 scripts/gen-dashboard.py --self-test` — exit 0, no `[FAIL]` lines.

**Then MUTATE it.** A case whose *name* encodes a requirement is the most dangerous kind, because
the name is what gets read during review. Break each behaviour and confirm the named case goes red:
the two bar marks (dot **and** class together — removing one leaves the other), the gh half of §4,
the day anchors, `_ordered`, pass 2, the ordinal rule, the chart direction, the under-count
sentence, and the glossary. **19 of 19 mutations were caught when this suite was written; a survivor
means a case that cannot fail for the thing it names.**

- [ ] **Step 5: Wire up `main` — which COMPOSES the page, never writes the fragment**

`build()` returns a **fragment** — no `<!doctype>`, no `<meta charset>`, **no Ask tray**. `main`
must call `scripts/brief-compose.py` with `--out` and **fail non-zero when the file is not
written**, copying `scripts/gen-goals-page.py:487-498`. A separate `--fragment-only` flag is the
only way to emit the raw fragment, so the default path cannot silently produce a trayless page.
`--window` below 1 is a `CANNOT RUN`, exit 2.

- [ ] **Step 6: Generate and look at it**

```bash
python3 scripts/gen-dashboard.py
python3 scripts/explainer-serve.py
```

Confirm, **looking at the page**: the entry appears with its id; its fold opens; a zero-commit day
carrying an entry is distinguishable **with the mouse elsewhere** — no hover, no screen reader; a
day with commits and **no** entry is marked too; the **Ask tray is present**; `/latest` still points
at the newest *briefing*.

⚠ **Check `document.hidden` before trusting any in-page probe.** A backgrounded tab has no geometry.

---

## Task 5: Folds survive live reload

**Files:** Modify `scripts/explainer-serve.py`.

- [ ] **Step 1: Confirm it is broken first.** Open a fold, `touch` the page, watch it close.

- [ ] **Step 2: Extend `RELOAD_JS`** — save and restore `<details>` open state, keyed on
`d.id` **only**, never on document position:

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

Call `saveDetails()` immediately before the existing scroll save.

⚠ **Key on `d.id` ONLY.** An index key shifts when a new entry is appended and rendered at the top —
so the restore would work when the page had not changed and misapply itself when it had, which is
the only reason the page reloaded. Task 4 emits `id="<entry-id>-plain"` and `-tech` on every fold.

- [ ] **Step 3: Add self-test rows that can actually fail**

```python
        case("reload client defines and CALLS saveDetails",
             lambda: RELOAD_JS.count("saveDetails()") >= 2)
        case("reload client defines and CALLS restoreDetails",
             lambda: RELOAD_JS.count("restoreDetails()") >= 2)
        case("reload client keys folds on id, never on position",
             lambda: "details[id]" in RELOAD_JS and "String(i)" not in RELOAD_JS)
```

**COUNT, not presence:** `"restoreDetails()"` is a substring of `function restoreDetails()`, so a
presence check passes on a build that defines both functions and calls neither.

- [ ] **Step 4: Run, then MUTATE.** Delete the `restoreDetails();` call, leaving the definition;
the row must go **red**. Restore it.

**These rows still only assert that text was typed.** Step 5 is the real test.

- [ ] **Step 5: Verify the behaviour.** Two folds open, `touch` the file, both still open.

- [ ] **Step 6: Commit.**

---

## Task 6: The skill, the hook, and the wiring that makes the gate real

**Files:** `.agents/skills/dashboard/SKILL.md` (+ symlink), `scripts/check-explainer-delivery.py`,
`.claude/hooks/regen-dashboard.sh`, `.claude/settings.json`, `.github/workflows/ci.yml`,
`docs/dev-process.md`, `docs/roadmap-to-launch.md`.

- [ ] **Step 1: Register the skill in `PAGE_SKILLS`** (`scripts/check-explainer-delivery.py:53`).

⚠ This check **cannot enforce its own list** — an absent skill is invisible to it and it exits green.
That is why this is a numbered step rather than an assumption.

- [ ] **Step 2: Write the skill — at `.agents/skills/`, with a symlink**

```bash
mkdir -p .agents/skills/dashboard
ln -s ../../.agents/skills/dashboard .claude/skills/dashboard
ls -l .claude/skills/dashboard        # must print '-> ../../.agents/skills/dashboard'
```

The SKILL.md instructs: append one block, never edit an existing one; `[needs-you]` only when a
decision is genuinely waiting; clear an earlier one with a **later** `[resolved: YYYY-MM-DD/N]`,
reading the id **off the page** rather than counting blocks; the title line is what the user reads.

Regeneration is **one command** — `python3 scripts/gen-dashboard.py` — which composes and writes the
page itself and exits non-zero if it does not. **No `mv ~/explainers/*-brief-dashboard.html` glob.**

**For serving, the question tray, arming the push loop, and verifying the page before handing it
over, follow `.agents/skills/shared/explainer-delivery.md`.** Cite it; never restate it.

- [ ] **Step 3: Verify the delivery and docs checks pass** — both `rc=0`.

- [ ] **Step 4: Add the regen hook — the script AND its registration**

⚠ **A hook script with no entry in `.claude/settings.json` never runs**, and since the hook exits 0
unconditionally there is no signal either way.

Create `.claude/hooks/regen-dashboard.sh` modelled on `.claude/hooks/regen-goals-page.sh` — same
stdin-parsing shape, matching only `docs/dashboard-entries.md`, exiting 0 unconditionally and
printing a warning if regeneration failed. Then register it in the existing `PostToolUse` →
`"Edit|Write"` array beside `regen-goals-page.sh`.

**Then prove it fires**: append a whole throwaway `## <date>` block to the store with the Edit tool
and confirm the turn prints `↻ dashboard regenerated`.

⚠ **A whole BLOCK, not a scratch line.** A bare line appended to a store whose last block is an
entry becomes part of **that entry's** text and renders inside it. Remove the block afterwards.

- [ ] **Step 5: Wire the ratchet into CI — this is what makes §7 real**

Give the existing checkout full history and drop any bespoke fetch:

```yaml
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
```

then, after the `check-function-revokes` steps:

```yaml
      - name: gen-dashboard self-test
        run: python3 scripts/gen-dashboard.py --self-test

      - name: check-dashboard-entry self-test
        run: python3 scripts/check-dashboard-entry.py --self-test

      - name: dashboard entry ratchet
        if: github.event_name == 'pull_request'
        env:
          BODY: ${{ github.event.pull_request.body }}
        run: |
          printf '%s' "$BODY" > /tmp/pr-body.md
          python3 scripts/check-dashboard-entry.py \
            --base "origin/$GITHUB_BASE_REF" --pr-body-file /tmp/pr-body.md
```

⛔ **`fetch-depth: 0` is the fix, and a bespoke `git fetch` is NOT.** `actions/checkout` defaults to
depth 1 on the synthesised merge ref, so `HEAD` is a graft with no computable merge base:

```
fetch_rc=0
CANNOT RUN — git diff exited 128: fatal: origin/master...HEAD: no merge base
ratchet_rc=2
```

An explicit refspec creates `origin/master` and **still leaves that error** — it fixes the symptom
the previous round reported, not the outcome. Measured: full history costs **~1.2s and ~4MB** per
run against this repo's 1,398 commits, and nothing else in CI reads git history.

⚠ **The PR body reaches the script through an env var and a FILE**, never interpolated into the
shell — a PR body is arbitrary user text.

**Also verify `no_entry_prs` here**, now that both files exist:

```bash
python3 -c "…no_entry_prs()…"                 # expect: no-entry: 0  err: None
mv scripts/check-dashboard-entry.py /tmp/hidden.py
python3 -c "…same…"                            # expect: no-entry: None  err: could not load …
mv /tmp/hidden.py scripts/check-dashboard-entry.py
```
**If the second prints `no-entry: 0 err: None`, the loader is swallowing the failure — stop.** `0`
is also the correct answer today, so the falsifier is the only thing that distinguishes them.

**Then falsify the ratchet in CI, not locally.** Open the PR with **no** entry, confirm the check
goes **red** with `REFUSED`, then add the entry and confirm green. Until that red has been seen on
GitHub the gate is unproven.

- [ ] **Step 6: Pointer rows and the roadmap**

Add to `docs/dev-process.md`'s "What is mechanically enforced" table:

| Check | Enforces |
|---|---|
| `scripts/check-dashboard-entry.py` | a branch that changes tracked files records a dashboard entry, or declares `NO-ENTRY: <reason>` — which the dashboard then **displays**. Also owns the entry-header grammar the page imports (`--self-test`) |
| `scripts/gen-dashboard.py` | the dashboard page is derived, never hand-edited; composed through `brief-compose.py` so it cannot lose its Ask tray (`--self-test`) |

⚠ Re-measure the line budget with `wc -l` before adding — `scripts/check-docs.py` enforces it.

**UPDATE** the existing `## Project dashboard` section in `docs/roadmap-to-launch.md` — tick the
build steps and refresh the status line. **Do not add a section**: one already exists, added by the
same commit that shipped the earlier version of this instruction.

- [ ] **Step 7: Commit and open the PR**

```bash
git add -A
git commit -F /tmp/msg-task6.txt
git log --oneline origin/master..HEAD      # confirm the branch carries ONLY this work
git push -u origin <branch>
gh pr create --title "..." --body-file /tmp/pr-body.md
```

`git log --oneline origin/master..HEAD` is not optional: a PR in this repo once silently carried a
whole other PR, with the right head SHA and a clean intended diff.

**Acceptance criteria — all five, or it is not ready:**

1. The ratchet has been **seen to refuse** on GitHub, not only locally.
2. The regen hook has been **seen to fire** on a real store write.
3. The served page has its **Ask tray**.
4. `check-docs.py` and `check-explainer-delivery.py` are both green.
5. Both `--self-test`s pass **and** their mutation checks were run.

**Merging is a human gate. Do not merge.**

---

## Self-Review

⚠ **Read this sceptically.** v1's asserted *"every row has a case"* where one falsifier had neither
code nor case; v2's carried a ✅ on §9 for an alarm that was never built, and a ✅ on §4 for "four
cases" when half of §4's sources had none. **A self-review fails in the direction self-reviews
always fail — toward believing the mapping rather than running it.** Every ✅ below was mutation-
tested: the behaviour was broken and the named case was watched going red.

| Spec | Where | Checked by |
|---|---|---|
| §3 in-scope list | Tasks 2–4 | ✅ glossary now built and asserted on its **content**, not the word (the CSS rule `#glossary` matched, so the whole section could be deleted and the case still passed) |
| §4 what-needs-you | Task 4 | ✅ store half **and** the `gh` half — v2 had no case passing a non-empty PR list, so half of §4 could be deleted silently |
| §5 the chart | Tasks 3–4 | ✅ buckets, oldest-left direction, the under-count sentence, and the bar→entry anchor; **✗ the "control to widen the window" is still a CLI argument** — see Gaps |
| §6.1 rendered once, marked bars | Task 4 | ✅ both marks asserted on **sighted output only** — hover text and screen-reader labels excluded |
| §6.2 grammar | Tasks 1–2 | ✅ every row, including the unknown-resolve-id falsifier, two `[resolved:]` flags, the missing space, the empty title, tie order, ordinal stability, and "in place" on the order the store **actually uses** |
| §7 the gate | Tasks 1, 6 | ✅ verdict cases + controls A–F; **display** built; CI wiring is Task 6 Step 5 and is an acceptance criterion, not an assumption |
| §9 checks | Tasks 1, 4, 5 | ✅ **including the commits-with-no-entry alarm**, which v2 marked ✅ without building |
| §10.1 folds | Task 5 | partial — three text-shape rows that go red when the call is deleted, plus a manual two-fold check. **No automated behavioural test**; see Gaps |
| §10.2 store created | Task 2 Step 5 | ✅ Step 6 parses the real file |
| §10.3 `PAGE_SKILLS` | Task 6 Step 1 | ✅ via `check-explainer-delivery.py`, which **cannot enforce its own list** — stated in the step |
| §10.4 `gh` failure | Tasks 3–4 | ✅ including a falsifier with `gh` off the `PATH` |

**Gaps, stated rather than hidden — five.**

1. §5's *"control to widen the window"* is a `--window` **argument**, not an in-page control.
2. §9's affordance probe is inherited from `.agents/skills/shared/explainer-delivery.md` §5b.
3. **Task 5 has no automated test of the actual behaviour.** Three static rows plus a human opening
   two folds is all a check of a JS string can do.
4. **`no_entry_prs` is bounded at 40 merged PRs** and depends on `gh`. An older exemption stops
   being displayed — a silent horizon, named here.
5. **The gate cannot see a missing title.** `header_error` is shared, so parser and ratchet agree on
   every *header* shape; but a well-formed header over an empty body is malformed to the page and
   invisible at the diff level. Perfect agreement is impossible there, so it is stated instead of
   claimed away — which is what v2 did.

**Type consistency.** `parse_entries` returns dicts whose `resolves` is a **list**; `unresolved`,
`bucket_days` and `build` all iterate it as one. The dependency is one-way: `gen-dashboard.py`
imports the grammar and `exemption_reason` from `check-dashboard-entry.py`, never the reverse, and
the gate is built first so no step depends on a file a later task creates.

**Placeholders:** none.


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

---

## Round 2 — Codex half, and the thing it caught me doing

`docs/reviews/plan-project-dashboard-r2-codex.md`, against `4077817`. **NOT CONVERGED**: 3 Blocking,
2 High, 2 Medium. All seven are addressed below; every fix was re-run, not reasoned about.

### ⛔ The finding that matters most is about the VERIFICATION, not the plan

**Blocking — `gen-dashboard.py --self-test` FAILS.** The case
`case("gh failure says could not tell", "could not tell" in html_err.lower(), True)` asserts a
string the renderer stopped emitting when H5's fix reworded it to *"I could not **also** check open
pull requests"*. A stale assertion against live code — ordinary enough.

**What is not ordinary is that I had run this and reported 55/55.** Transcribing the plan into a
scratch file, I wrote `"could not" in html_err.lower()` — dropping one word — and the weakened
version passed. Codex transcribed faithfully and got `54/55`.

So the green I reported was measured against **an assertion I had softened while copying it**. This
is `docs/portable-practices.md`'s *test harness can launder failures*, committed by the author of
the section warning about it, one commit after writing it. **A transcription is not a copy unless
it is diffed.** The case now asserts the contract — an unchecked source is announced as
`NOT CHECKED` and its reason is surfaced — rather than one version's wording.

### The rest

| Sev | Finding | Fix |
|---|---|---|
| **B** | Task 2 Step 6 verifies `no_entry_prs()`, which imports `check-dashboard-entry.py` — a file **Task 4 creates**. The stated expected output cannot occur in task order | The check moved to **Task 4 Step 6a**, plus a falsifier that hides the gate file and requires a loud `CANNOT RUN` |
| **B** | `set -e` at the top of the Task 4 controls **kills the script at Control A**, whose whole purpose is to exit 1. It never printed a verdict line and never reached B–E | `set -e` removed, with the reason stated so nobody restores it |
| **H** | `git fetch --no-tags --depth=200 origin master` **exits 0 and creates no `origin/master`** on a shallow branch-only checkout, so the CI ratchet cannot run | Explicit refspec `+refs/heads/X:refs/remotes/origin/X`. **Reproduced and re-verified here**: bare form → `origin/master MISSING`, `diff rc=128`; refspec form → ref created, diff clean |
| **H** | `NO-ENTRY:` inside an HTML comment exempts the branch | **Already fixed in v2.1**, independently. Two reviewers reaching the same defect from different directions is the strongest signal available that it was real |
| **M** | A ` ``` ` fence treated as closed by `~~~` | **Already fixed in v2.1** |
| **M** | The parser comment says a spaceless `##2026-08-28` "must become a MALFORMED entry"; the code accepted it as ordinary, and a self-test row asserted the accepting behaviour | The comment was right. `HEADER` now requires the space, the entry is malformed with a diagnostic naming the space, and the gate's `_ADDED_ENTRY` requires it too — so the two can no longer disagree about what an entry is |

**Re-verified after all seven, not assumed:** generator **58/58**, gate **32/32**, controls A–E run
to completion (`A rc=1`, `B rc=0`, `C rc=1`, `+## not-a-date` present, `D rc=1`, `E rc=0`), and the
CI refspec reproduced end to end.

**Two Codex findings were things v2.1 had already fixed**, which is worth noting rather than
glossing: it reviewed `4077817`, and v2.1 landed as `7ce2ac6` while it was running. The overlap is
confirmation, not waste.

**Still NOT CONVERGED, and the Claude half of round 2 has NOT run.** Round 1's two halves overlapped
on 2 of ~26 findings; one reviewer is not the gate. That gap is the next action, and it is recorded
rather than papered over.

---

## v3 — round 2's Claude half, and the task reorder it forced

`docs/reviews/plan-project-dashboard-r2-claude.md` — **2 Blocking, 8 High, 6 Medium, 5 Low, NOT
CONVERGED.** Twenty-one findings, of which **none** duplicated the Codex half and **one** overlapped
the coordinator's mutation pass. Two rounds now say the same thing: a single reviewer is not the gate.

### The two Blocking

| | |
|---|---|
| **B1** | The CI ratchet **still could not run**. v2.2's refspec created `origin/master` and left a second error behind it — `actions/checkout` takes depth 1 on the synthesised merge ref, so `HEAD` is a graft with **no merge base**. Same `ratchet_rc=2`, different sentence. It had been verified against the *symptom the previous round reported* rather than the *outcome*, in a scratch repo that was not shallow and therefore could not observe it. **Fixed with `fetch-depth: 0`** — measured at ~1.2s and ~4MB over 1,398 commits, with nothing else in CI reading history |
| **B2** | Task 4's Step 1 block had no `import re`, so Step 2's expected `NotImplementedError` was a `NameError` and Step 4's green was unreachable. v2.1 added `FENCE` above the block that imported `re`; both prior reviewers assembled the **final** file and never executed the intermediate states the task prescribes |

### The reorder, and why it was not optional

H1 measured **five header shapes** where the ratchet and the parser disagreed, while v2.2's own text
claimed *"they can no longer disagree"* — v2.2 had closed exactly the two shapes Codex named.
Instance-not-class, answered this time with a run rather than a recollection.

The fix is one grammar, owned by the gate and imported by the page. **But that makes the parser
depend on a file the gate task creates** — which is the very defect B2 and H8 filed. Fixing one
finding would have reintroduced another.

**So the gate is now Task 1 and the parser Task 2.** Considered and rejected: a third shared module
(more concept than the problem needs), and inverting the import so the gate depends on the generator
(a gate must never import the thing it guards).

### The rest

| Sev | Finding | Fix |
|---|---|---|
| H2 | §9's alarm — *every day with commits and no entry is visibly marked* — was **not built, had no case, and its Self-Review row carried a ✅**. Bars measured byte-identical | Built, with a hatched bar and a gap mark, asserted on sighted output |
| H3 | Two `[resolved:]` flags on one header: the first silently discarded, `error: None` — verbatim the failure pass 2 exists to prevent, in the sibling case it did not consider | `resolves` is a list; every consumer iterates it |
| H4 | *"Rendered in place"* held only for a newest-**first** file. The store is newest-**last** by the plan's own Step 5, so on a real store the malformed block still fell to the bottom. **The certifying case was built on the one ordering where the bug is invisible** | `_ordered` splices a malformed block after whichever neighbour renders first — order-agnostic, verified under both orderings |
| H5 | The marked-bar row survived losing **both** on-screen marks, because it still compared `title=` and `aria-label=` | Compares the bar's own class and its child elements; hover text and aria excluded |
| H6 | The `gh` half of §4 had **no case at all** — every fixture passed an empty or `None` PR list | A case with a real open PR, asserted inside its own section |
| H7 | The indent rule was bypassable two ways: a **tab**-indented declaration, and the text before an HTML comment, which never ran through the check | Tabs count to the 4-column stop; the head runs through the same rule |
| H8 | *"Replace the direct call"* had a literal reading returning `([], None)` — a confident *"No branch has skipped its entry"* on every page — and Step 6a could not tell, because `0` is also today's correct answer | The finished function is shown; the check is paired with a falsifier that hides the gate file |
| M1–M6 | Ordering untested; a roadmap step duplicating work the same commit already did; a falsifier expecting output its own snippet cannot print; §3's glossary and §5's under-count sentence absent; dead bar links on days without entries; ordinals that shifted when a typo was repaired, silently rebinding a standing `[resolved:]` | all fixed and mutation-checked |
| L1–L5 | A cited line number off by one; a visible declaration after a closed comment; a row passing for an unrelated reason; chart direction untested; a verification step whose "scratch line" becomes part of the previous entry | all fixed |

### Three more found by attacking v3 itself, before any reviewer saw it

Mutation-testing the new suite — 19 mutations — caught three cases that could not fail for what they
named, **all written in the same sitting as the fixes they certify**:

1. The `§6.1` mark comparison read the **container's own class as a child element**, an artifact of
   the §5 fix that made the container tag vary. It passed with every visible mark deleted.
2. The glossary case matched the **CSS rule** `#glossary`, so the entire section could be removed.
3. The CRLF normalisation was **dead code** — `.strip()` already covered it. Removed rather than
   left as a line no test can reach.

**That is the fourth, fifth and sixth instance of one shape today**, after the falsifier that could
not fire, the transcription that weakened its own assertion, and the two vacuous regression cases.
The lesson is not "write better cases": it is that **the only thing distinguishing a real guard from
a decorative one is breaking the code and watching it go red.**

### Standing evidence for v3

```
generator --self-test   70/70
gate      --self-test   42/42
mutations               19/19 caught
controls A–F            A✗ B✓ C✗ D✗ E✓, and all five previously-waved-through shapes refused
symbols embedded        33/33 byte-identical to the executed files
```

**v3 has NOT been reviewed. Round 3 must run both halves.**

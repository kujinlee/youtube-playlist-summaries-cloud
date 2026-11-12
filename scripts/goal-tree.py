#!/usr/bin/env python3
"""The goal tree, logged: why each thread of work exists, what state it is in, and how that changed.

    python3 scripts/goal-tree.py --snapshot --page --print   # what /goal-tree runs
    python3 scripts/goal-tree.py                             # = --snapshot --page (the Refresh button)
    python3 scripts/goal-tree.py --page                      # re-render from the log: no gh; git only
                                                             # to find the MAIN checkout's log
    python3 scripts/goal-tree.py --self-test                 # 481 cases

WHY THIS EXISTS (backlog #363). Asked 2026-10-28 03:41: *"I wonder if this kind of goal tree is logged
every so often (periodically in time or when meaningful changes are made) and I can see the page to learn
how your work has been progressed, the page can be ideal dashboard."* `/goal-tree` printed the tree in
chat and nothing kept it; the work-lines page drew only plans armed with `begin-plan.py`, and none had
been armed since 2026-10-25, so it showed nothing of the work the owner was watching.

⛔ TWO KINDS OF FACT, AND THE PAGE NEVER MIXES THEM.
  * the RELATIONS — which goal a thread serves, and as a fix, a blocker, bookkeeping or a side job — are
    DECLARED by hand in `docs/goal-threads.md`. No tool can see WHY a PR exists; pretending to infer it
    would print a plausible tree that is believed.
  * the STATES — merged (with its SHA), open (draft, mergeability, checks), in flight, closed — are
    DERIVED at snapshot time from `git log origin/master` subjects, `gh pr list` and
    `.claude/inflight.jsonl`. A thread whose backlog rows ALL carry a fate MARKER in their Status cell — a
    bold, capital SUPERSEDED or WITHDRAWN leading the cell, or led by a closing glyph — prints ✖ instead of
    the merge's ✅ (backlog #484; the word anywhere else in the cell is prose, not a fate). An unread
    backlog, or a row it does not have, makes such a leaf CANNOT RUN, never ✅. A declared `waits on …` is
    shown as DECLARED, never as a derived state.

⛔ CANNOT RUN IS NEVER A STATE THAT GETS LOGGED AS ONE. When `git fetch`, `git log` or `gh` fails, every
leaf that needed it says CANNOT RUN in the tree that is printed, and the snapshot is NOT appended (exit
2): a logged "CANNOT RUN" would then read, in the timeline, as a state flip and back. The page keeps the
last complete snapshot and says above it that the live read failed, and why.

⭐ THE LOG STAYS MEANINGFUL: a snapshot whose tree equals the newest logged one (ignoring its time and
the master head it was read at) is not appended. The timeline therefore lists changes, not readings.
The log is `.claude/goal-tree-log.jsonl` in the MAIN checkout (`session-state.main_checkout`): git-ignored,
so a log appended on every merge churns no tracked file, and one log however many worktrees append.

⭐ NEEDS YOU, at the top of the page (owner decision D1, 2026-10-28): ONE list of decisions only the owner
can make, open now, from three sources, each read by its owner's code and never a copy of it:
  * the dashboard's unresolved asks — `gen-dashboard.unresolved()` — plus every entry the store's grammar
    could not read, NAMED as unreadable (it may be an ask);
  * in-flight entries marked `WAITS-ON-OWNER:` — `session-state.waits_on_owner()`, main checkout's ledger;
  * open backlog rows still marked NEEDS-OWNER (`needs_owner`), parsed by `gen-backlog-page.parse`, with
    any line that parser refused to read reported as unreadable; a row whose status says it was settled after
    its marker is FLAGGED "may already be settled" with the remedy, and stays listed (backlog #496).
"Nothing waits on you" is said only when ALL THREE were read; a source that cannot be read — or that holds
even one record it cannot read (a truncated ledger line, an unparseable dashboard entry, a refused backlog
line) — is NOT READ, its readable items are still shown, and the snapshot is not logged, like any other
CANNOT RUN (round 1 X1). Decisions and ACTIONS only the owner can take are two lists (X4:
`NEEDS-OWNER-ACTION`, `WAITS-ON-OWNER: ACTION:`). ⛔ ROUND 2 REDESIGN: no meaning is read out of prose —
items merge only on a DECLARED identity (`decision: backlog #N` / `action: backlog #N`, row AND kind),
each merged source keeping its own text, link and count; a count comes only from `(answers-open: N)`
("several" only where a source says "several answers"); and a row whose tail names a decided or closed
`backlog #N` is flagged "may already be answered", never hidden (C2, Y4). ROUND 3: an item's kind is its OWN
marker, and an identity token that disagrees with it is a CONFLICT shown on the page, never a merge (Z1);
identity and count are read from the WHOLE source entry, a dashboard body included, before the display text
is shortened (Z2).

⭐ IT ABSORBED THE WORK-LINES PAGE (backlog #389, the owner's decision D2): a "PLANS NOT TICKED CLOSED" section
lists every plan in a line that still owes something — its progress, its last touch, what it branched from and
the line's objective — read through gen-work-lines' plan reader (`read_plans_noted`, `build_forest`,
`line_state`), never a copy. A frozen record of the retired page (plan contents withheld pending backlog #194) is at `/work-lines-archive`, linked from
the timeline. One page now answers "which threads are live".

⭐ WHEN, AND WHAT IS CURRENT (backlog #497). Asked 2026-11-04 01:00: *"current … goal-tree.html doesn't show merged
time for listed PRs and do not show parked and queued (planned) tasks for each goals / it would be nice to have
collaps/expand button for older merged PRs / To highlight current or near-term future or recent past tasks, older or
not planned (in near-term) backlogs can be in collapsed view"*. A merged leaf says when (`merged 11-03 19:09 · <sha>`,
the owner's local minute, from master's committer date or gh's `mergedAt`; unread says `time unread`). Each leaf is in
ONE bucket (`bucket`): now, parked, queued and recent are drawn; older and later fold into a closed `<details>` on the
page and into a `… N older` / `… N later` count line in --print, from ONE block structure (`tree_blocks`). The bucket is
computed when the tree is DRAWN and never stored, so a merge crossing the 48 h line logs no snapshot.

THE PAGE IS A REPLAY (round 2 Y7): the tree and the timeline are the stored snapshots, and the page says
which snapshot and how to refresh it; NEEDS YOU is read live whenever this run took a snapshot.

TRIGGERS: `/goal-tree` (`.claude/commands/goal-tree.md`) runs it before printing; the PostToolUse hook
`.claude/hooks/regen-pages.sh` (`scripts/regen-pages.py`) runs it — with every other generated page —
after `gh pr merge`, and alone after an edit of the threads file; the page's Refresh button runs it with
no arguments.

⚠ BOUNDS, stated. A backlog-only thread finds its PR by the `(backlog #N)` subject tail on master and by
`backlog #N` in an open PR's title; a PR that names its row any other way is not found and the thread
reads "no PR names it yet". The in-flight ledger is matched by (KIND, number) (`_ledger_refs`): an entry's
declared `thread` refs, else the `PR #N` / `backlog #N` in its id and text. A bare `#424` or an id's `-424` names
nothing, so such an entry shows IN FLIGHT UNDER NO GOAL rather than on a guessed thread. `gh pr list --state all` is capped at
ALL_LIMIT, so an old PR beyond it reads NOT FOUND, never a guessed state.

EXIT CODES (repo convention): 0 = done · 1 = `docs/goal-threads.md` or the log is malformed ·
2 = CANNOT RUN (a source could not be read, or there is nothing to render).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import html
import importlib.util
import io
import json
import os
import pathlib
import re
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import page_chrome  # noqa: E402
import page_markup  # noqa: E402

ROOT = SCRIPTS.parent
THREADS_REL = "docs/goal-threads.md"
# Answers to questions asked FROM this page (owner 2026-11-11 06:18: Q&A must not clutter the tree). A SEPARATE
# source, so an answer survives every regeneration, keyed to a goal or thread so it survives the tree changing.
ANSWERS_REL = "docs/goal-tree-answers.json"
# ⛔ GIT-IGNORED, IN THE MAIN CHECKOUT (the coordinator's decision, 2026-10-28): a log appended on every
# merge must not churn a tracked file, and a worktree run must append to the ONE log the page reads.
LOG_REL = ".claude/goal-tree-log.jsonl"
DASHBOARD_REL = "docs/dashboard-entries.md"
BACKLOG_REL = "docs/backlog.md"
NEEDS_OWNER = "NEEDS-OWNER"
# backlog #389: the work-lines page's job lives here now, and a frozen record of it is at this url.
WORK_LINES_ARCHIVE = "/work-lines-archive"
# The three sources of the NEEDS YOU list; "nothing waits on you" is said only when ALL were read.
NEEDS_SOURCES = ("dashboard", "ledger", "backlog")
DEFAULT_OUT = pathlib.Path.home() / "explainers" / "goal-tree.html"
RELATIONS = ("fix", "blocker", "bookkeeping", "side")
OPEN_LIMIT = 100
ALL_LIMIT = 300
MERGED_DEPTH = 500

GOAL_RE = re.compile(r"^## GOAL ([a-z0-9]+(?:-[a-z0-9]+)*)$")
REQUEST_RE = re.compile(r'^> (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) "(.+)"$')
THREAD_RE = re.compile(r"^- (\S+) · (.+?) · (.+?)(?: · waits on (.+))?$")
REFS_RE = re.compile(r"(?:backlog|PR) #\d+(?:, (?:backlog|PR) #\d+)*")
REF_RE = page_markup.KEY_REF      # one key grammar, owned by the link function
# A merged subject ends `… (backlog #N) (#PR)` or `… (#PR)`; the PR number is the LAST parenthesis.
SUBJECT_PR_RE = re.compile(r"\(#(\d+)\)\s*$")

GLYPH = {"merged": "✅", "open": "⏳", "inflight": "⏳", "next": "⬜", "blocked": "❌",
         "closed": "✖", "superseded": "✖", "withdrawn": "✖", "notfound": "❓", "cannot": "⚠"}
# backlog #484: a row's STATUS cell can say its work was replaced or dropped, and that beats the merge state —
# a merged PR on a superseded row is not "delivered". ⛔ Read ONLY from a fate MARKER, never from the word:
# a Status cell is append-only prose, and it quotes, negates and narrates the word (row 484's own cell does,
# and an any-word read printed it ✖ withdrawn — r1 H1). A marker is `**SUPERSEDED` / `**WITHDRAWN`, bold and
# in capitals, either LEADING the cell (after an optional glyph and `(was X)`) or led by a closing glyph ✅ /
# ✖ — the form the 2026-10-26 audit APPENDED to rows 124, 125, 127, 189 and 213. Markers are matched in
# `fate_text(status)`, never the raw cell: code spans are removed FIRST (CommonMark: a run of N backticks
# closes only on a run of exactly N, r2 X2), so a quoted marker — or a quoted `Previously:` — is inert; THEN
# the cell is cut at its first `Previously:`, so everything after it is history (r2 X1). A marker is
# cancelled by a LATER bold span that leads with REOPENED (optionally after a date and a dash) — row 327's
# `⟳ **2026-10-25 — REOPENED BY THE OWNER…**` shape, appended after its supersession prose (r2 note).
# ⚠ BOUND: a reopen written any other way (lowercase, unbolded, or not leading its bold span) is not seen,
# and a backslash-escaped backtick is treated as a delimiter.
FATE_RE = re.compile(r"(?:^\s*(?:[✅✖]\ufe0f?\s*)?|[✅✖]\ufe0f?\s*)(?:\(was[^)]*\)\s*)?"
                     r"\*\*(SUPERSEDED|WITHDRAWN)\b([^*]*)")
CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", re.S)
HISTORY_CUT = "Previously:"
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
REOPEN_RE = re.compile(r"\s*(?:\d{4}-\d{2}-\d{2}\s*[—–-]\s*)?REOPENED\b")
# The forward pointer, read only INSIDE the marker's bold span: `by backlog #M`, or several (`#328/#329`).
POINTER_RE = re.compile(r"\bby backlog (#\d+(?:\s*(?:/|,|and|&)\s*#\d+)*)")
# The table a `backlog #N` ref names. The second table (`## Found during testing`) reuses Items' numbers (r1 L1).
ITEMS_SECTION = "Items"
# When a thread names several PRs, the one state shown is the first of these that any of them has:
# a thread is merged only when ALL its PRs are, and an unreadable one makes the whole thread unread.
PRECEDENCE = ("cannot", "open", "notfound", "closed", "merged")
# backlog #497 — WHEN, and what is current. A merged leaf says when it merged (the owner's local minute, from
# master's committer date or gh's `mergedAt`); each leaf falls in ONE recency bucket (`bucket`), and the page
# folds `older` and `later` away. ⛔ The bucket is NEVER stored: it depends on the moment the tree is DRAWN, so
# storing it would log a new snapshot each time a merge crosses the 48 h line with nothing else changed.
MINUTE_FMT = "%Y-%m-%d %H:%M"
TIME_UNREAD = "time unread"
RECENT_HOURS = 48
VISIBLE = ("now", "parked", "queued", "recent")     # drawn open; `older` and `later` are folded
LANDED = ("merged", "closed", "superseded", "withdrawn")
# review r1 C3: `PARKED` in capitals anywhere (a marker, like **SUPERSEDED), or `parked` in ANY case where it
# LEADS a clause (the text's start, or after `; : . ! ? ( —`) — so prose that merely mentions parked work
# (`shows merge times, parked/queued items`) parks nothing. A negated one (`NOT PARKED`, `no longer parked`)
# is struck out first, so it never parks.
PARKED_RE = re.compile(r"\bPARKED\b")
PARKED_LEAD_RE = re.compile(r"(?:^|[;:.!?(—])\s*parked\b", re.IGNORECASE)
PARKED_NOT_RE = re.compile(r"\b(?:not|no\s+longer)\s+parked\b", re.IGNORECASE)
QUEUED_RELATIONS = ("fix", "blocker")    # review r1 C2: declared under a goal, unstarted — that IS the plan


def _sibling(name: str):
    """A hyphenated sibling script, imported by path (one rule, one place — not a copy of it).

    ⚠ OUTSIDE A SWEEP, EVERY CALL IS A FRESH IMPORT, as it always was: a process that rewrites a sibling, or a
    file the sibling reads at import, gets the new one on its next call. The sibling's OWN bytes are compiled
    directly (`compile`, never its `__pycache__`), so a same-size rewrite in the same second, or with the mtime
    put back, is never served old bytecode (r1 Claude F2). A module the sibling itself loads by path is loaded
    by Python's own rules, `.pyc` included, as before this cache existed.

    ⚠ INSIDE `_sibling_sweep()` (backlog #406): the suite asked for the same three siblings ~180 times and each
    call re-executed the whole module, which was most of the suite. In a sweep a sibling is imported ONCE PER
    PATH and that module is returned after. THE BOUND, and the reason it is safe: a sweep reads the tree as it
    stood when it started, as a process's own `import` does. Nothing in it rewrites a real sibling, and the
    mutation harness gives each mutant a fresh process. A sweep that rewrites a sibling, or a file one reads at
    import, is served the first import — which is why the cache lives only there (Phase 6, 2026-11-08:
    `docs/reviews/architecture-review-2026-11-08-goal-tree-sibling-cache.md`). Nothing here writes a sibling's
    attributes; a caller in a sweep that patches one must undo it.

    The memo is one dict and its only writes are whole-key stores, so a re-entrant import (a sibling calling
    `_sibling` during its own) and two threads need no lock: the worst overlap imports one path twice, and
    either module is a correct import of the same bytes."""
    path = str(SCRIPTS / f"{name}.py")
    memo = _SIBLING_MEMO
    if memo is not None and path in memo:
        return memo[path]
    spec = importlib.util.spec_from_file_location("_" + name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(pathlib.Path(path).read_bytes(), path, "exec", dont_inherit=True), mod.__dict__)
    if memo is not None:
        memo[path] = mod
    return mod


# backlog #406: path -> module, and only inside `_sibling_sweep()`. None means every call imports afresh.
_SIBLING_MEMO: dict | None = None


@contextlib.contextmanager
def _sibling_sweep():
    """Import each sibling once per path for the duration (backlog #406). ONLY the self-test (`_self_test_body`)
    opens one: it is the one caller that asks for the same siblings ~180 times, and the one whose files do not
    change while it asks. The previous state is put back in `finally`, so a sweep that raises does not leave the
    memo on; a nested sweep shares the outer one's memo."""
    global _SIBLING_MEMO
    saved = _SIBLING_MEMO
    _SIBLING_MEMO = {} if saved is None else saved
    try:
        yield
    finally:
        _SIBLING_MEMO = saved


_SS = _sibling("session-state")   # clean(), check_summary(), read_ledger(), _run()


class Malformed(ValueError):
    """`docs/goal-threads.md` or the log breaks its grammar. Never caught into a pass."""


# ── the declared input ────────────────────────────────────────────────────────────────────────
def parse_threads(text: str) -> list[dict]:
    """PURE. The threads file -> goals. Raises Malformed naming EVERY bad line, not just the first.

    Above the first `## GOAL` is prose and is ignored; inside a goal every non-blank line must be a
    request or a thread. ⛔ Any other `## ` heading is refused rather than read as the end of a goal: a
    typo in `GOAL` would otherwise turn a whole goal's threads into silently ignored prose.
    """
    goals: list[dict] = []
    problems: list[str] = []
    cur = None
    seen_slugs: set = set()
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if line.startswith("## "):
            m = GOAL_RE.match(line)
            if not m:
                problems.append(f"line {i}: a `## ` heading that is not `## GOAL <slug>`: {line!r}")
                cur = None
                continue
            if m.group(1) in seen_slugs:
                problems.append(f"line {i}: goal `{m.group(1)}` is declared twice")
            seen_slugs.add(m.group(1))
            cur = {"slug": m.group(1), "requests": [], "threads": [], "line": i}
            goals.append(cur)
            continue
        if cur is None or not line.strip():
            continue
        if line.startswith(">"):
            m = REQUEST_RE.match(line)
            if not m:
                problems.append(f'line {i}: a request must be `> YYYY-MM-DD HH:MM "<quote>"`: {line!r}')
                continue
            cur["requests"].append({"when": m.group(1), "quote": m.group(2)})
        elif line.startswith("-"):
            t, bad = parse_thread_line(line)
            if bad:
                problems.append(f"line {i}: {bad}")
                continue
            if any(x["key"] == t["key"] for x in cur["threads"]):
                problems.append(f"line {i}: thread `{t['key']}` is declared twice in goal `{cur['slug']}`")
                continue
            cur["threads"].append(t)
        else:
            problems.append(f"line {i}: inside goal `{cur['slug']}` a line must be a `> ` request or a "
                            f"`- ` thread: {line!r}")
    for g in goals:
        if not g["requests"]:
            problems.append(f"line {g['line']}: goal `{g['slug']}` quotes no request — the root of a "
                            f"tree is the owner's own words")
    if not goals and not problems:
        problems.append("no `## GOAL <slug>` is declared, so there is no tree to draw")
    if problems:
        raise Malformed("\n".join(problems))
    for g in goals:
        g.pop("line")
    return goals


# ── the derived states ────────────────────────────────────────────────────────────────────────

def parse_thread_line(line: str):
    """PURE. One `- <relation> · <refs> · <what>` line -> (thread, None) or (None, why). The ONE reader of the
    grammar: the threads file and a ledger entry's `thread` (backlog #505) both go through it."""
    m = THREAD_RE.match(line)
    if not m:
        return None, f"a thread must be `- <relation> · <refs> · <what>`: {line!r}"
    rel, refs_text, what, waits = m.groups()
    if rel not in RELATIONS:
        return None, f"relation {rel!r} is not one of {', '.join(RELATIONS)}"
    if not REFS_RE.fullmatch(refs_text):
        return None, (f"refs {refs_text!r} must be `backlog #N` / `PR #N`, "
                      f"joined by `, ` — a thread names a backlog row or a PR")
    return {"key": f"{rel} · {refs_text}", "relation": rel,
            "refs": [[k, int(n)] for k, n in REF_RE.findall(refs_text)],
            "what": what.strip(), "waits": waits.strip() if waits else None}, None


def ledger_threads(goals: list[dict], ledger: list[dict]) -> tuple[list[dict], list[str]]:
    """PURE. Hang each ledger entry's DECLARED thread (`goal` + `thread`, backlog #505) under its goal, so work in
    flight sits under the goal it serves before its PR merges the tracked line. The tracked file WINS: a thread
    sharing any ref with a thread `docs/goal-threads.md` declares, in any goal, is not added again (after the merge
    it is the same work). A bad line or an unknown goal is a PROBLEM shown on the page, never dropped in silence."""
    declared = {(k, n) for g in goals for t in g["threads"] for k, n in t["refs"]}
    claimed: dict = {}   # ref -> the ledger entry that hung it first (r1 Codex M1: two entries, two goals, one PR)
    out = [dict(g, threads=list(g["threads"])) for g in goals]
    by_slug = {g["slug"]: g for g in out}
    problems: list[str] = []
    # by ID, never file order: a re-`--add` moves an entry to the END of the file, and file order would flip the
    # winner of a shared ref and log a false move (r2 Codex M1)
    for e in sorted(ledger, key=lambda e: str(e.get("id", ""))):
        if not (e.get("goal") or e.get("thread")):
            continue
        id_ = _SS.clean(e.get("id", ""), 60)
        t, bad = parse_thread_line("- " + str(e.get("thread") or "").removeprefix("- "))
        if bad:
            problems.append(f"entry {id_}: its thread is not read — {bad}")
            continue
        g = by_slug.get(str(e.get("goal") or ""))
        if g is None:
            problems.append(f"entry {id_}: goal {str(e.get('goal'))!r} is not declared in {THREADS_REL}")
            continue
        refs = {tuple(r) for r in t["refs"]}
        if refs & declared:
            continue
        if refs & claimed.keys():
            first = claimed[sorted(refs & claimed.keys())[0]]
            problems.append(f"entry {id_}: its thread's refs are already hung by entry {first} — the id that sorts first wins")
            continue
        claimed.update({r: id_ for r in refs})
        g["threads"].append(dict(t, ledger=id_))
    return out, problems


def _ledger_refs(entry: dict) -> set:
    """The (kind, number) refs a ledger entry names — compared with a thread's refs as PAIRS, so `PR #558` is never
    `backlog #558` (PR #558 r1 E: both sequences are in the 500-600s and grow together, so the collision recurs).
    An entry that declares a `thread` names exactly that thread's STRUCTURED refs; its prose is not an association
    (r1 Codex M3). One with no thread names the KINDED refs in its id and text (`PR #N`, `backlog #N`). ⛔ A bare
    `#N` or an id's `-N` names NOTHING: it carries no kind, and reading it as both hung a review of `#586` on the
    merged backlog #586 threads."""
    if entry.get("thread"):
        t, _ = parse_thread_line("- " + str(entry["thread"]).removeprefix("- "))
        return {(k, n) for k, n in t["refs"]} if t else set()
    return {(k, int(n)) for k, n in REF_RE.findall(f"{entry.get('id', '')} {entry.get('what', '')}")}


def _thread_refs(t: dict) -> set:
    return {(k, n) for k, n in t["refs"]}


def merge_when(full) -> str:
    """PURE. A stored `YYYY-MM-DD HH:MM` -> the leaf's `mm-dd hh:mm`; anything else says TIME_UNREAD, never blank."""
    try:
        return _dt.datetime.strptime(full, MINUTE_FMT).strftime("%m-%d %H:%M")
    except (TypeError, ValueError):
        return TIME_UNREAD


def local_minute(iso, tz=None):
    """PURE given `tz` (None = this machine's zone). gh's `mergedAt` (ISO, with a zone) -> `YYYY-MM-DD HH:MM`
    in the owner's local time, or None when it does not parse or carries no zone (a guessed zone is a wrong time)."""
    try:
        t = _dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.astimezone(tz).strftime(MINUTE_FMT) if t.tzinfo is not None else None


def _merge_time(n: int, src: dict):
    """The merge minute of a MERGED PR #n; None when unread. ⛔ review r1 X2: GitHub's `mergedAt` FIRST — it is
    when the PR merged. Master's committer date is only the fallback (a fast-forwarded commit carries the time it
    was MADE), and a missing committer date never hides a readable `mergedAt`."""
    gh = (src.get("all_merged_at") or {}).get(n)
    if gh:
        return gh
    merged = src["merged_by_pr"] or {}
    return (src.get("merged_at") or {}).get(merged[n]) if n in merged else None


def is_parked(entry: dict) -> bool:
    """A ledger entry that PARKS work rather than doing it: DECLARED `kind` owner-wait, or its text says so
    (`PARKED_RE` / `PARKED_LEAD_RE`, after its negations are struck out)."""
    text = PARKED_NOT_RE.sub(" ", str(entry.get("what", "")))
    return (entry.get("kind") == _SS.KIND_WAIT or bool(PARKED_RE.search(text))
            or bool(PARKED_LEAD_RE.search(text)))


def _age_hours(merged_at, at):
    try:
        return (_dt.datetime.strptime(at, MINUTE_FMT)
                - _dt.datetime.strptime(merged_at, MINUTE_FMT)).total_seconds() / 3600
    except (TypeError, ValueError):
        return None


def bucket(t: dict, at) -> str:
    """PURE. The ONE recency bucket of a derived leaf, drawn at `at` (`YYYY-MM-DD HH:MM`):
      now            — ⛔ FIRST, whatever its state: a ledger entry that is not parked names it (`inflight`,
                       review r1 X1 — work in flight on a thread that already landed is current, never folded);
      recent / older — merged (or closed, `closed_at`) within RECENT_HOURS of `at`, or before that; superseded and
                       withdrawn are older. ⛔ review r2 X1: with `ended_at` (every ref's merge or close minute) the
                       leaf is RECENT when ANY ref ended within the window, whatever the aggregate state says. ⛔ A time (or `at`) that cannot be read is RECENT: an age never read never
                       folds a leaf. A closed leaf with NO `closed_at` key was logged before close times were read: older;
      parked         — a parked ledger entry names it (`is_parked`) and it has not landed;
      queued         — unstarted and planned: a declared `waits on` (state blocked), or an unstarted `fix`/`blocker`
                       thread — declared under its goal, which is the plan (review r1 C2, the owner's "queued (planned)");
      later          — an unstarted `bookkeeping` or `side` thread;
      now            — everything else: an open PR, and ⚠ CANNOT RUN / ❓ NOT FOUND (unknown never folds)."""
    state = t["state"]
    # A snapshot logged before `inflight` was stored still says so in its detail (one spelling, `derive_thread`'s).
    if t.get("inflight", " · in flight: " in str(t.get("detail", ""))):
        return "now"
    if state in ("merged", "closed"):
        if state == "closed" and "closed_at" not in t:
            return "older"
        # ⛔ review r2 X1: every ref's end (`ended_at`); a snapshot logged before it was stored has only the
        # aggregate's own time. OLDER only when EVERY end was read and is past the window.
        ends = t.get("ended_at", [t.get("merged_at") if state == "merged" else t.get("closed_at")])
        ages = [_age_hours(w, at) for w in ends]
        return "older" if ages and all(a is not None and a > RECENT_HOURS for a in ages) else "recent"
    if state in LANDED:
        return "older"
    if t.get("parked"):
        return "parked"
    if state == "blocked":
        return "queued"
    if state == "next":
        return "queued" if t.get("relation") in QUEUED_RELATIONS else "later"
    return "now"


def _pr_state(n: int, src: dict) -> tuple[str, str]:
    """(state, detail) for PR #n. Master's subjects decide `merged` first: they are what landed."""
    merged = src["merged_by_pr"]
    if merged is not None and n in merged:
        return "merged", f"merged {merge_when(_merge_time(n, src))} · {merged[n]}"
    if src["errors"].get("merged") or src["errors"].get("gh"):
        why = src["errors"].get("merged") or src["errors"].get("gh")
        return "cannot", f"CANNOT RUN — {why}"
    pr = src["open"].get(n)
    if pr is not None:
        bits = [f"PR #{n} open"] + (["draft"] if pr.get("isDraft") else [])
        if pr.get("mergeStateStatus"):
            bits.append(_SS.clean(pr["mergeStateStatus"], 20).lower())
        bits.append(_SS.check_summary(pr.get("statusCheckRollup")))
        return "open", " · ".join(bits)
    st = src["all"].get(n)
    if st == "MERGED":
        return "merged", (f"merged {merge_when(_merge_time(n, src))} · "
                          f"{src['all_merge_sha'].get(n) or '(sha unread)'} — not on master's log")
    if st == "CLOSED":
        when = (src.get("all_closed_at") or {}).get(n)
        return "closed", (f"PR #{n} closed {merge_when(when)} without merging" if when
                          else f"PR #{n} closed without merging · close {TIME_UNREAD}")
    return "notfound", f"PR #{n} is not among the {ALL_LIMIT} newest PRs gh listed"


def derive_thread(t: dict, src: dict) -> dict:
    """PURE. One declared thread + the read sources -> the thread with `state` and `detail`."""
    prs = [n for k, n in t["refs"] if k == "PR"]
    rows = [n for k, n in t["refs"] if k == "backlog"]
    # backlog #484: each backlog ref has its OWN fate (None = live). `fates` is None when the backlog was not
    # read, and holds EVERY Items row (fated or None) when it was, so a row absent from it does not exist.
    fates = src.get("fates")
    fate_of = {n: (fates or {}).get(n) for n in rows}
    live_rows = [n for n in rows if fate_of[n] is None]
    whens: list = []          # backlog #497: the merge minute of every merged PR (None where it was not read)
    closes: list = []         # review r1 C6: the close minute of every closed PR (None where it was not read)
    open_pr = None            # review r1 X1: the open PR a backlog-only thread resolved to by its TITLE
    # running-vs-owed r3 Codex M1: EVERY open PR its rows resolve to, not only the first — and (backlog #518) whatever
    # the leaf shows: a MIXED thread (one ref merged, a live row resolving to an open PR) took the merged branch below
    # and owned none, so its open PR showed as stray RUNNING work past the thread's declared wait.
    opened = [p for p in (src.get("open") or {}).values()
              if any(re.search(rf"\bbacklog #{n}\b", p.get("title") or "") for n in live_rows)]
    resolved = [int(q["number"]) for q in opened]
    if prs:
        found = [_pr_state(n, src) for n in prs]
        state = next(s for s in PRECEDENCE if any(f[0] == s for f in found))
        detail = " · ".join(d for _, d in found)
        whens = [_merge_time(n, src) for n, f in zip(prs, found) if f[0] == "merged"]
        closes = [(src.get("all_closed_at") or {}).get(n) for n, f in zip(prs, found) if f[0] == "closed"]
    elif src["errors"].get("merged") or src["errors"].get("gh"):
        state, detail = "cannot", f"CANNOT RUN — {src['errors'].get('merged') or src['errors'].get('gh')}"
    else:
        hit = next(((sha, pr) for sha, pr, subj in src["merged_rows"]
                    if any(re.search(rf"\(backlog #{n}\)", subj) for n in live_rows)), None)
        if hit:
            whens = [(src.get("all_merged_at") or {}).get(hit[1]) or (src.get("merged_at") or {}).get(hit[0])]
            state, detail = "merged", f"merged {merge_when(whens[0])} · {hit[0]} via PR #{hit[1]}"
        elif opened:
            p = opened[0]
            open_pr = int(p["number"])
            state, detail = "open", (f"PR #{p['number']} open" + (" · draft" if p.get("isDraft") else "")
                                     + " · " + _SS.check_summary(p.get("statusCheckRollup")))
        else:
            state, detail = "next", "no PR names it yet"
    if rows:
        # backlog #484 — THE PRECEDENCE, exactly. Each ref contributes its own state and the leaf shows the worst:
        #   1. ⚠ CANNOT RUN — the backlog was not read, or a named row is not in its Items table. Never ✅.
        #   2. ⏳ an open PR, ⏳ an in-flight entry (below), ❓ a PR gh did not list — kept; a fate never hides them.
        #   3. ✖ superseded / withdrawn — ONLY when EVERY backlog ref is fated, and it replaces ONLY the merge ✅
        #      (and the ⬜ / ✖ closed of a leaf whose rows are all fated). An unfated ref is live work, so its
        #      state stands. Across fated rows, superseded beats withdrawn: the pointer says where the goal went.
        #   4. otherwise the state above. Every fate is still NAMED in the detail, whatever the glyph.
        fated = [fate_of[n] for n in rows if fate_of[n]]
        missing = [n for n in rows if n not in (fates or {})]
        if fates is None:
            state, detail = "cannot", (f"CANNOT RUN — {src.get('fates_error') or BACKLOG_REL + ' was not read'}"
                                       f", so a superseded or withdrawn row cannot be ruled out")
        elif missing:
            state, detail = "cannot", ("CANNOT RUN — " + ", ".join(f"backlog #{n}" for n in missing)
                                       + f" is not a row of the {ITEMS_SECTION} table in {BACKLOG_REL}")
        elif fated:
            if not live_rows and state in ("merged", "next", "closed"):
                state = "superseded" if any(f[0] == "superseded" for f in fated) else "withdrawn"
            detail = " · ".join(dict.fromkeys(f[1] for f in fated)) + " · " + detail
    naming = [e for e in src["ledger"] if _ledger_refs(e) & _thread_refs(t)]
    # backlog #497: a PARKED entry is not work in flight — it is shown as parked, and never turns ⬜ into ⏳.
    parked = [_SS.clean(e.get("what", ""), 160) for e in naming if is_parked(e)]
    flying = [_SS.clean(e.get("what", ""), 160) for e in naming if not is_parked(e)]
    if flying and state in ("next", "notfound", "superseded", "withdrawn"):
        state = "inflight"
    if flying:
        detail += " · in flight: " + "; ".join(flying)
    if parked:
        detail += " · parked: " + "; ".join(parked)
    if t.get("ledger"):
        detail += f" · declared in the ledger ({t['ledger']}), not yet on master"
    if t.get("waits") and state in ("next", "inflight"):
        state = "blocked" if state == "next" else state
        detail += f" · waits on {t['waits']} (declared)"
    # The LATEST merge is when the thread landed; one unread minute makes the whole time unread (never a guess).
    merged_at = max(whens) if whens and all(whens) else None
    # running-vs-owed r1 Codex H1/M1: the open PRs this thread's work IS — a named one or the one its row resolved to,
    # read whatever the leaf's worst state is (an unread row must not hide an open PR) and the identity items merge by
    open_prs = sorted({n for n in prs if n in src["open"]} | ({open_pr} if open_pr is not None else set()) | set(resolved))
    out = dict(t, state=state, detail=detail, merged_at=merged_at, parked=bool(parked), inflight=bool(flying),
               open_pr=open_pr, open_prs=open_prs)
    if state == "closed":
        out["closed_at"] = max(closes) if closes and all(closes) else None
    if whens or closes:
        # ⛔ review r2 X1: EVERY ref's merge or close minute (None = unread), so recency is judged across all refs —
        # never only by the time the aggregate state happens to carry.
        out["ended_at"] = whens + closes
    return out


def derive(goals: list[dict], src: dict, now: str) -> dict:
    """PURE. Goals + sources -> one snapshot. `cannot` lists every source that could not be read."""
    goals, thread_problems = ledger_threads(goals, src["ledger"])
    out_goals = [dict(g, threads=[derive_thread(t, src) for t in g["threads"]]) for g in goals]
    # ⛔ review r1 X1: an open PR is represented only by a STRUCTURED association — a thread's refs, or the open PR
    # its backlog row resolved to — never by a mention in detail text (a ledger entry quoting `PR #99` hid PR #99).
    named_prs = {n for g in out_goals for t in g["threads"] for k, n in t["refs"] if k == "PR"}
    # …every open PR a thread's work IS: named, or resolved from its rows by title (running-vs-owed r3 Codex M1:
    # every one, not only the first — `open_prs` holds `open_pr` too, so one line, not two that mask each other)
    named_prs |= {n for g in out_goals for t in g["threads"] for n in t.get("open_prs") or []}
    undeclared = [{"pr": n, "title": _SS.clean(p.get("title") or "", 160),
                   "draft": bool(p.get("isDraft"))}
                  for n, p in sorted(src["open"].items()) if n not in named_prs]
    pairs = {r for g in out_goals for t in g["threads"] for r in _thread_refs(t)}
    unnamed = [e for e in src["ledger"] if not (_ledger_refs(e) & pairs) and not _SS.waits_on_owner(e)]
    loose = [{"id": _SS.clean(e.get("id", ""), 60), "what": _SS.clean(e.get("what", ""), 160)}
             for e in unnamed if not is_parked(e)]
    # backlog #497: a parked entry naming no thread of any goal is its own group — shown, never dropped. So is one
    # whose every named thread has LANDED: its leaves are folded as older, and work that landed is not what is
    # parked (backlog #489). Matching is by (kind, number) since PR #558 r1 E, so `PR #376` no longer reaches a
    # `backlog #376` thread; a landed thread the entry really names still routes it here.
    parked_loose = [{"id": _SS.clean(e.get("id", ""), 60), "what": _SS.clean(e.get("what", ""), 160)}
                    for e in unnamed if is_parked(e)]
    for e in src["ledger"]:
        hits = [t for g in out_goals for t in g["threads"] if _ledger_refs(e) & _thread_refs(t)]
        if hits and is_parked(e) and all(t["state"] in LANDED for t in hits):
            parked_loose.append({"id": _SS.clean(e.get("id", ""), 60), "what": _SS.clean(e.get("what", ""), 160),
                                 "landed": [t["key"] for t in hits]})
    return {"at": now, "head": src.get("head"), "repo": src.get("repo"), "goals": out_goals,
            "undeclared": undeclared, "inflight_loose": loose, "parked_loose": parked_loose, "needs": list(src.get("needs") or []),
            "needs_not_read": [f"{k}: {src['errors'][k]}" for k in NEEDS_SOURCES if src["errors"].get(k)],
            "ledger_problems": list(src.get("ledger_problems") or []) + thread_problems,
            "plans": list(src.get("plans") or []), "plan_notes": list(src.get("plan_notes") or []),
            "cannot": [f"{k}: {v}" for k, v in sorted(src["errors"].items()) if v]}


def fingerprint(snap: dict) -> str:
    """What a snapshot SAYS, without when it was read or the master head it was read at."""
    return json.dumps({k: v for k, v in snap.items() if k not in ("at", "head")}, sort_keys=True)


NO_READER_CHANGE = "no change a reader would see (the stored tree differs only in wording)"


def changes(prev: dict | None, cur: dict) -> list[str]:
    """PURE. One line per difference a reader would care about, oldest-to-newest direction."""
    if prev is None:
        return ["first snapshot"]
    out: list[str] = []

    def index(s):
        return {(g["slug"], t["key"]): t for g in s["goals"] for t in g["threads"]}
    a, b = index(prev), index(cur)
    pg, cg = {g["slug"] for g in prev["goals"]}, {g["slug"] for g in cur["goals"]}
    out += [f"goal added: {s}" for s in sorted(cg - pg)]
    out += [f"goal removed: {s}" for s in sorted(pg - cg)]
    # backlog #505: a LEDGER thread replaced by the tracked one sharing a ref is ONE event — master now declares it —
    # never a false `added` plus a false `removed` (r1 Codex M2: the key or goal may differ across the handoff)
    handed: dict = {}
    # Paired on the ledger thread's PR when it names one, else its backlog row — a sibling sharing only a backlog
    # row is other work, and pairing it would hide a real removal (r2 Codex M2)
    for r in (k for k in a if k not in b and a[k].get("ledger")):
        rr = {tuple(x) for x in a[r]["refs"]}
        rr = {x for x in rr if x[0] == "PR"} or rr
        for k in (k for k in b if k not in a and not b[k].get("ledger") and k not in handed.values()):
            if {tuple(x) for x in b[k]["refs"]} & rr:
                handed[r] = k
                out.append(f"declared on master: [{b[k]['relation']}] {k[1].split(' · ', 1)[1]} (was in the ledger "
                           f"as [{a[r]['relation']}] {r[1].split(' · ', 1)[1]} under {r[0]}): "
                           f"{GLYPH[b[k]['state']]} {b[k]['detail']}")
                break
    for k in b:
        if k in handed.values():
            continue
        if k not in a:
            out.append(f"added [{b[k]['relation']}] {k[1].split(' · ', 1)[1]}: "
                       f"{GLYPH[b[k]['state']]} {b[k]['detail']}")
        elif (a[k]["state"], a[k]["detail"]) != (b[k]["state"], b[k]["detail"]):
            out.append(f"[{b[k]['relation']}] {k[1].split(' · ', 1)[1]}: {a[k]['state']} → "
                       f"{GLYPH[b[k]['state']]} {b[k]['state']} — {b[k]['detail']}")
    out += [f"removed [{a[k]['relation']}] {k[1].split(' · ', 1)[1]}" for k in a if k not in b and k not in handed]
    pu, cu = {u["pr"] for u in prev["undeclared"]}, {u["pr"] for u in cur["undeclared"]}
    out += [f"undeclared PR #{n} appeared" for n in sorted(cu - pu)]
    out += [f"undeclared PR #{n} is gone" for n in sorted(pu - cu)]
    pn = {(n["source"], n["ref"]) for n in prev.get("needs") or []}
    cn = {(n["source"], n["ref"]) for n in cur.get("needs") or []}
    out += [f"needs you, new: {r} ({s})" for s, r in sorted(cn - pn)]
    out += [f"needs you, cleared: {r} ({s})" for s, r in sorted(pn - cn)]
    pp = {_plan_id(p): p for p in prev.get("plans") or []}
    cp = {_plan_id(p): p for p in cur.get("plans") or []}
    out += [f"plan not ticked closed, new: {cp[k]['plan']} ({cp[k]['ticked']}/{cp[k]['total']})"
            for k in sorted(set(cp) - set(pp))]
    out += [f"plan no longer owing: {pp[k]['plan']}" for k in sorted(set(pp) - set(cp))]
    out += [f"plan progress: {cp[k]['plan']} {pp[k]['ticked']}/{pp[k]['total']} → {cp[k]['ticked']}/{cp[k]['total']}"
            for k in sorted(set(pp) & set(cp)) if pp[k]["ticked"] != cp[k]["ticked"]]
    pq, cq = set(prev.get("ledger_problems") or []), set(cur.get("ledger_problems") or [])
    out += [f"ledger problem, new: {q}" for q in sorted(cq - pq)]
    out += [f"ledger problem, cleared: {q}" for q in sorted(pq - cq)]
    pl, cl = {u["id"] for u in prev["inflight_loose"]}, {u["id"] for u in cur["inflight_loose"]}
    out += [f"in flight, under no goal: {i}" for i in sorted(cl - pl)]
    out += [f"no longer in flight: {i}" for i in sorted(pl - cl)]
    (pk, pa), (ck, ca) = snap_agenda(prev), snap_agenda(cur)
    # ⛔ identity is the agenda's (id, at), and steps are compared ONLY between two VALID agendas with the same one:
    # two agendas recorded in one minute are different plans, and an agenda missing its identity is no basis for a
    # move (slice 2, r1 Codex M2, r2 Codex M2)
    if ck == "ok" and (pk != "ok" or (ca["id"], ca["at"]) != (pa["id"], pa["at"])):
        out.append(f"agenda recorded: set {ca['at']}, {len(ca.get('steps') or [])} step(s)")
    elif ck == "ok" and pk == "ok":
        was = {st["n"]: st["state"] for st in pa["steps"]}
        out += [f"agenda step {st['n']}: {was[st['n']]} → {step_glyph(st['state'])} {st['state']} — {st['text']}"
                for st in ca["steps"] if st["n"] in was and was[st["n"]] != st["state"]]
    return out or [NO_READER_CHANGE]


# ── NEEDS YOU: a decision only the owner can make, open now (owner decision D1, 2026-10-28) ────
# An item is {kind, source, ref, href, text, multi, flag, also, identity}. `kind` is "decision" or
# "action" (round 1 X4: running a falsifier is something only the owner can DO, not a question to answer).
#
# ⛔ ROUND 2 REDESIGN — STRUCTURE, NOT FREE TEXT. Rounds 1 and 2 each found the previous fold reading
# meaning out of prose: a row number in a sentence taken as decision identity (merging a different question,
# or an action into a decision), "14 answers open" found inside "backlog #14 answers open", `pr #11` taken for
# a backlog row. Every one of those is now an EXPLICIT TOKEN, and prose is only ever displayed:
#   * IDENTITY — `decision: backlog #N` or `action: backlog #N` in a dashboard ask or a ledger entry. Without
#     it an item never merges, whatever row its text mentions (Y1). A backlog row's own identity is (N, its kind).
#   * COUNT    — `(answers-open: N)`. Without it, "several" only where the source says "several answers"; else
#     nothing (Y3). Never a number found in a sentence.
#   * DEPENDS  — the answered flag reads only `backlog #N` (the word, any case, one or more spaces) (Y4).
ACTION_SUFFIX = "-ACTION"          # `NEEDS-OWNER-ACTION —` in a backlog status
LEDGER_ACTION = "ACTION:"          # `WAITS-ON-OWNER: ACTION: …` in a ledger entry
IDENTITY = re.compile(r"\b(decision|action): backlog #(\d+)\b")
COUNT = re.compile(r"\(answers-open: (\d+)\)")
SEVERAL = re.compile(r"\bseveral answers\b", re.I)
BACKLOG_REF = re.compile(r"\bbacklog +#(\d+)\b", re.I)


def needs_owner(row: dict) -> bool:
    """PURE. Does this backlog row still wait on the OWNER? Open, carries `NEEDS-OWNER` (or
    `NEEDS-OWNER-ACTION`), and the text after its LAST marker does not begin `answered`. ⚠ BOUND: a row
    whose decision was recorded in some other wording, with the marker left in place, still reads as
    waiting — the marker is the claim. backlog #496 FLAGS the measured shape of that (`settled_in_prose`);
    it does not hide it."""
    s = row.get("status") or ""
    i = s.rfind(NEEDS_OWNER)
    return (not row.get("closed") and i >= 0
            and not re.match(r"\W*answered\b", s[i + len(NEEDS_OWNER):], re.I))


# backlog #496: a decision recorded in PROSE leaves the marker asking. Measured 2026-11-03: of the six rows
# NEEDS YOU listed, backlog #306 said `DECIDED … by the owner` after its marker; it was not `answered`, so it was
# still asked. The flag is on a row that stays listed (C2) — never a hide, because prose can be wrong both ways.
#   * `DECIDED` (upper case, this repo's recording word) or `answered by the owner` in the text
#     AFTER the last marker, unless `not`/`never` (optionally `yet`) stands right before it (r1 Codex R4:
#     "not DECIDED", "not yet answered by the owner"). ⚠ Case-sensitive on purpose: backlog #384's own tail says
#     "is decided after backlog #392 is built" — a future call, and the case-insensitive form false-fired on it.
#   * ⚠ BOUND: a status head REWRITTEN without a decision word (backlog #384's shape, 2026-11-02) is NOT seen. A
#     "clause 2" read git history to see it, and three review rounds found three git topologies it got wrong, so
#     the Phase 6 review (docs/reviews/architecture-review-2026-11-06-needs-owner-settled.md) removed it; that
#     class moves to a PR-time diff check, filed as its own backlog row. Nothing here reads git history.
SETTLED_WORDS = re.compile(r"\bDECIDED\b|\banswered by the owner\b")
NEGATED = re.compile(r"\b(?:not|never)(?:\s+yet)?\s*$", re.I)
SETTLED_REMEDY = "if so, write `NEEDS-OWNER answered`"


def settled_in_prose(status: str):
    """PURE. Clause 1 of backlog #496: the flag text when the status records a decision AFTER its last
    marker in the repo's recording words, not negated right before them, else None."""
    tail = status[status.rfind(NEEDS_OWNER):]
    m = next((m for m in SETTLED_WORDS.finditer(tail) if not NEGATED.search(tail[:m.start()])), None)
    return (f"may already be settled: its status says “{m.group(0)}” after the NEEDS-OWNER marker — "
            + SETTLED_REMEDY) if m else None


def multiplicity(text: str):
    """PURE. How many answers one item stands for — ONLY from the `(answers-open: N)` annotation; "several"
    only where the source literally says "several answers"; otherwise None. A number in a sentence is never
    read as a count (round 2 Y3: "backlog #14 answers open" is not fourteen answers)."""
    m = COUNT.search(text)
    if m:
        return int(m.group(1))
    return "several" if SEVERAL.search(text) else None


def identity(text: str):
    """PURE. The EXPLICIT decision identity a dashboard ask or ledger entry declares — (row, kind) from
    `decision: backlog #N` / `action: backlog #N` — or None. Exactly one such token, else None: an entry
    that declares two identities is ambiguous and merges into neither."""
    found = {(int(n), k) for k, n in IDENTITY.findall(text)}
    return next(iter(found)) if len(found) == 1 else None


def _item(kind, source, ref, href, text, ident=None, full=None):
    """One NEEDS YOU item. `kind` is the source's OWN marker; `full` is the WHOLE source entry, from which
    the count is read BEFORE `text` is shortened for display (round 3 Z2).

    ⛔ Z1: an identity token whose kind disagrees with the item's own marker does NOT become the item's
    identity — the item stays separate and carries the conflict, which the page shows."""
    conflict = None
    if ident and ident[1] != kind:
        conflict = (f"declares {ident[1]}: backlog #{ident[0]} but is marked "
                    + ("ACTION" if kind == "action" else "a decision"))
        ident = None
    return {"kind": kind, "source": source, "ref": ref, "href": href, "text": text,
            "multi": multiplicity(full if full is not None else text), "flag": None, "also": [],
            "identity": list(ident) if ident else None, "conflict": conflict}


def needs_from_dashboard(text: str) -> tuple[list[dict], list[str]]:
    """(items, problems). The dashboard's unresolved asks, by `gen-dashboard.unresolved()`. Every entry
    the store's own grammar could not read is a PROBLEM naming its id (X1): it may be an ask, so the
    source is NOT READ — readable asks are still returned."""
    gd = _sibling("gen-dashboard")
    entries = gd.parse_entries(text)
    items = []
    for e in gd.unresolved(entries):
        whole = f"{e.get('title') or ''} {e.get('plain') or ''}"   # Z2: the whole entry, body included
        items.append(_item("decision", "dashboard", e["id"], page_markup.key_link("dashboard", gd._slug(e["id"])),
                           _SS.clean(e.get("title") or "", 160), identity(whole), whole))
    bad = [e["id"] or e.get("would_be_id") or "an entry with no id" for e in entries if e["error"]]
    return items, ([f"{len(bad)} dashboard entr{'y' if len(bad) == 1 else 'ies'} the store's grammar "
                    f"could not read ({', '.join(bad)})"] if bad else [])


def needs_from_ledger(entries: list[dict]) -> list[dict]:
    """In-flight entries marked `WAITS-ON-OWNER:` — session-state's own predicate, not a copy. A
    following `ACTION:` makes it an action rather than a decision."""
    out = []
    for e in entries:
        if not _SS.waits_on_owner(e):
            continue
        rest = e["what"][len(_SS.OWNER_MARKER):].strip()
        ident = identity(rest)
        kind = "action" if rest.startswith(LEDGER_ACTION) else "decision"
        rest = rest[len(LEDGER_ACTION):].strip() if kind == "action" else rest
        out.append(_item(kind, "ledger", _SS.clean(e.get("id", ""), 60), None,
                         _SS.clean(rest, 200), ident, e["what"]))
    return out


def needs_from_backlog(text: str) -> tuple[list[dict], list[str]]:
    """(items, problems). Open rows still marked NEEDS-OWNER, parsed by gen-backlog-page's ONE row parser.
    Any line that parser refused is a PROBLEM (X1). A listed row whose tail names ANOTHER row that is
    closed or recorded as decided/answered is FLAGGED, never hidden (C2): the dependency is prose.
    backlog #496: so is a row whose OWN status records a decision after its marker (`settled_in_prose`)."""
    gb = _sibling("gen-backlog-page")
    unread: list[str] = []
    rows = gb.parse(text.split("\n"), unread)
    by_num = {r["num"]: r for r in rows}
    out = []
    for r in rows:
        if not needs_owner(r):
            continue
        tail = r["status"][r["status"].rfind(NEEDS_OWNER) + len(NEEDS_OWNER):]
        kind = "action" if tail.startswith(ACTION_SUFFIX) else "decision"
        tail = tail[len(ACTION_SUFFIX):] if kind == "action" else tail
        tail = tail.lstrip(" —-")
        it = _item(kind, "backlog", f"backlog #{r['num']}", page_markup.key_link("backlog", r["num"]),
                   _SS.clean(html.unescape(gb.plain(r["title"])), 140) + " — " + _SS.clean(tail, 160),
                   full=f"{r['title']} {tail}")
        it["row"] = r["num"]
        it["identity"] = [r["num"], kind]
        it["flag"] = settled_in_prose(r["status"])   # backlog #496 clause 1: the row's OWN words first
        # Y4: only an explicit `backlog #N` is a row — never a bare `#N`, a `pr #N` or an `issue #N`.
        for n in sorted({int(x) for x in BACKLOG_REF.findall(tail)} - {r["num"]}) if it["flag"] is None else []:
            o = by_num.get(n)
            if o is not None and (o["closed"] or (not needs_owner(o) and re.search(
                    r"\bDECIDED\b|\banswered\b", o["status"], re.I))):
                it["flag"] = f"may already be answered by backlog #{n}"
                break
        out.append(it)
    return out, ([f"{len(unread)} line(s) of {BACKLOG_REL} the row parser could not read"]
                 if unread else [])


def consolidate(items: list[dict]) -> list[dict]:
    """PURE. Items that DECLARE the same decision become ONE item keeping every source (round 2 Y1/Y2).

    The key is an explicit identity — a backlog row AND a kind — and nothing else: a dashboard ask or ledger
    entry merges into a listed row's item only when it carries `decision: backlog #N` / `action: backlog #N`
    matching that row's number and kind. A bare mention of `backlog #N` never merges. Every merged source
    keeps its own text, link and count in `also`; conflicting counts are kept, not resolved."""
    items = [dict(it, also=list(it.get("also") or [])) for it in items]   # never the caller's dicts
    rows = {tuple(it["identity"]): it for it in items if it.get("row") is not None}
    out = []
    for it in items:
        target = (rows.get(tuple(it["identity"]))
                  if it.get("row") is None and it.get("identity") else None)
        if target is not None:
            target["also"].append({k: it[k] for k in ("source", "ref", "href", "text", "multi")})
            continue
        out.append(it)
    return out


def counts_conflict(item: dict) -> bool:
    """PURE. Do the sources of one item state DIFFERENT counts? Both are shown when they do."""
    stated = {v for v in [item.get("multi")] + [a.get("multi") for a in item.get("also") or []]
              if v is not None}   # W2: a declared 0 is a count, and can conflict
    return len(stated) > 1


# ── PLANS NOT TICKED CLOSED: the work-lines page's job, absorbed (backlog #389) ──────────────
def _json_id(key) -> list | str:
    """A plan key as it survives JSON: a `(checkout, slug)` tuple becomes a list, a bare slug stays."""
    return [str(k) for k in key] if isinstance(key, tuple) else str(key)


def _plan_id(p: dict) -> str:
    """The key a snapshot's plan records are compared on — the identity, never the display label (a
    record logged before r1 carries no `id`, and falls back to its label)."""
    return json.dumps(p.get("id", p["plan"]))


def open_plans(plans: list[dict], wl) -> list[dict]:
    """PURE over `wl` (gen-work-lines, THE plan reader). Every plan in a line that still owes something,
    each with its own progress and the line's objective — the question the work-lines page answered.

    The forest, the line state and the labels are gen-work-lines' own (`build_forest`, `line_state`,
    `label`), never a copy. ⚠ "not ticked closed" is not "abandoned": a plan file is a claim about
    progress, and the date is when the file was last touched."""
    roots, _orphans = wl.build_forest(plans)
    out = []
    for root in roots:
        if wl.line_state(root) != "open":
            continue
        stack = [(root, None)]
        while stack:
            n, parent = stack.pop()
            if not n["done"] and not n["empty"]:
                # ⟳ r1 X4: `id` is the reader's (checkout, slug) identity; `plan` is DISPLAY only, and
                # two plans can display alike (`kid` held twice beside a literal `kid @ main.md`).
                out.append({"id": _json_id(wl.plan_key(n)),
                            "plan": wl.label(n), "ticked": n["ticked"], "total": n["total"],
                            "touched": n["touched"], "line": wl.label(root),
                            "serving": root.get("serving"),
                            # a parent build_forest could not find is NAMED, never dropped silently
                            "parent": parent or (f'{n["orphan_parent"]} (no longer exists)'
                                                 if n.get("orphan_parent") else None),
                            "reconstructed": bool(n.get("source"))})
            stack.extend((c, wl.label(n)) for c in n["children"])
    return sorted(out, key=lambda r: (r["touched"], r["plan"]), reverse=True)


def fate_text(status: str) -> str:
    """PURE. The part of a Status cell a fate marker is read from: code spans removed FIRST (matching backtick
    runs, CommonMark-style), THEN cut at the first `Previously:` — everything after it is history (r2 X1, X2)."""
    return CODE_SPAN_RE.sub("", status).split(HISTORY_CUT, 1)[0]


def _reopened_after(t: str, m) -> bool:
    """PURE. True when a bold span AFTER the marker `m` (its own closing `**` skipped) leads with REOPENED."""
    start = m.end() + (2 if t.startswith("**", m.end()) else 0)
    return any(REOPEN_RE.match(b.group(1)) for b in BOLD_RE.finditer(t, start))


# ── reading the world (the only impure part) ──────────────────────────────────────────────────
def row_fates(text: str) -> tuple[dict, list[str]]:
    """PURE. ({row: (state, detail) or None}, problems) for EVERY row of the Items table (backlog #484), read
    by gen-backlog-page's ONE row parser (its `CELL_SPLIT` is check-docs'). None is a live row; a key that is
    absent is a row that does not exist. Only a fate MARKER counts (`FATE_RE`); a SUPERSEDED marker beats a
    WITHDRAWN one, and its pointer is printed only when the marker's own bold span states it — nothing the row
    does not say. Any line the parser refused is a PROBLEM — that row may be the superseded one."""
    gb = _sibling("gen-backlog-page")
    unread: list[str] = []
    fates: dict = {}
    for r in gb.parse(text.split("\n"), unread):
        if r["section"] != ITEMS_SECTION:
            continue
        t = fate_text(r["status"])
        marks = [m for m in FATE_RE.finditer(t) if not _reopened_after(t, m)]
        sup = next((m for m in marks if m.group(1) == "SUPERSEDED"), None)
        if sup:
            ptr = POINTER_RE.search(sup.group(2))
            to = ", ".join(f"backlog #{n}" for n in re.findall(r"#(\d+)", ptr.group(1))) if ptr else ""
            fates[r["num"]] = ("superseded", "superseded" + (f" → {to}" if to else ""))
        elif marks:
            fates[r["num"]] = ("withdrawn", "withdrawn")
        else:
            fates[r["num"]] = None
    problems = [f"{len(unread)} line(s) of {BACKLOG_REL} the row parser could not read"] if unread else []
    return fates, problems


def collect(root: pathlib.Path, run=None, read_plans=None) -> dict:
    """Read git, gh, the ledger and the plans. NEVER RAISES: a failure is recorded in `errors` by source.

    `run(cmd, cwd, timeout) -> (rc, text)` is session-state's `_run` unless a test passes one;
    `read_plans(plan_dir) -> (plans, notes)` is gen-work-lines' `read_plans_noted` unless a test does.
    """
    run = run or _SS._run
    errors: dict[str, str] = {}
    src = {"merged_by_pr": None, "merged_rows": [], "merged_at": {}, "open": {}, "all": {}, "all_merge_sha": {},
           "all_merged_at": {}, "all_closed_at": {},
           "ledger": [], "ledger_problems": [], "needs": [], "head": None, "repo": None,
           "main": root, "errors": errors}
    rc, out = run(["git", "fetch", "--quiet", "origin", "master"], root, 60)
    if rc != 0:
        errors["merged"] = f"git fetch origin master exited {rc}: {_SS.clean(out, 160)}"
    else:
        # backlog #497: the committer date, in the owner's LOCAL zone — a squash merge's committer date is its merge.
        rc, out = run(["git", "log", "origin/master", f"-n{MERGED_DEPTH}", f"--date=format-local:{MINUTE_FMT}",
                       "--format=%h%x09%cd%x09%s"], root, 30)
        if rc != 0 or not out.strip():
            errors["merged"] = f"git log origin/master exited {rc} with {len(out.strip())} chars"
        else:
            by_pr, rows, when = {}, [], {}
            for ln in out.splitlines():
                sha, _, rest = ln.partition("\t")
                date, _, subj = rest.partition("\t")
                when[sha] = date
                m = SUBJECT_PR_RE.search(subj)
                if m:
                    by_pr.setdefault(int(m.group(1)), sha)
                    rows.append((sha, int(m.group(1)), subj))
            src["merged_by_pr"], src["merged_rows"], src["merged_at"] = by_pr, rows, when
            src["head"] = out.split("\t", 1)[0]
    rc, out = run(["gh", "pr", "list", "--state", "open", "--limit", str(OPEN_LIMIT), "--json",
                   "number,title,isDraft,mergeStateStatus,statusCheckRollup"], root, 30)
    try:
        if rc != 0:
            raise ValueError(f"exited {rc}: {_SS.clean(out, 160)}")
        src["open"] = {int(p["number"]): p for p in json.loads(out)}
        rc, out = run(["gh", "pr", "list", "--state", "all", "--limit", str(ALL_LIMIT), "--json",
                       "number,state,mergeCommit,mergedAt,closedAt"], root, 30)
        if rc != 0:
            raise ValueError(f"exited {rc}: {_SS.clean(out, 160)}")
        for p in json.loads(out):
            src["all"][int(p["number"])] = p.get("state")
            if isinstance(p.get("mergeCommit"), dict) and p["mergeCommit"].get("oid"):
                src["all_merge_sha"][int(p["number"])] = p["mergeCommit"]["oid"][:8]
            if p.get("mergedAt"):
                src["all_merged_at"][int(p["number"])] = local_minute(p["mergedAt"])
            if p.get("state") == "CLOSED" and p.get("closedAt"):
                src["all_closed_at"][int(p["number"])] = local_minute(p["closedAt"])
        rc, out = run(["gh", "repo", "view", "--json", "nameWithOwner"], root, 30)
        if rc == 0:
            src["repo"] = json.loads(out).get("nameWithOwner")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        errors["gh"] = f"gh pr list: {_SS.clean(exc, 160)}"
        src["open"] = {}
    # The ledger is git-ignored, so it lives in the MAIN checkout; session-state names it (one rule).
    main, main_why = _SS.main_checkout(root, run)
    src["main"] = main
    why = main_why
    if why:
        errors["ledger"] = why
    else:
        data, why = _SS._read_whole(main / _SS.LEDGER_REL)
        if data is None:
            errors["ledger"] = why
        else:
            src["ledger"], src["ledger_problems"], _raw = _SS._parse(data)
    if src["ledger_problems"]:
        # ⛔ X1: an unreadable ledger line may be an owner-wait, so the source is NOT READ — the
        # readable entries are still used.
        errors["ledger"] = "; ".join(src["ledger_problems"]) + " — NOT READ"
    needs: list[dict] = []
    for key, rel, fn in (("dashboard", DASHBOARD_REL, needs_from_dashboard),
                         ("backlog", BACKLOG_REL, needs_from_backlog)):
        try:
            text = (root / rel).read_text(encoding="utf-8")
            items, problems = fn(text)
        except Exception as exc:                  # noqa: BLE001 - NOT READ, named, never "none"
            errors[key] = f"{rel} NOT READ ({type(exc).__name__}: {_SS.clean(exc, 120)})"
            continue
        needs += items
        if problems:
            errors[key] = "; ".join(problems) + " — NOT READ"
    needs += needs_from_ledger(src["ledger"])
    src["needs"] = consolidate(needs)
    # backlog #484: which rows are SUPERSEDED or WITHDRAWN. Unread (or partly unread) leaves `fates` None,
    # and every thread naming a backlog row then says CANNOT RUN.
    src["fates"], src["fates_error"] = None, None
    try:
        fates, fproblems = row_fates((root / BACKLOG_REL).read_text(encoding="utf-8"))
        if fproblems:
            src["fates_error"] = "; ".join(fproblems)
        else:
            src["fates"] = fates
    except Exception as exc:                      # noqa: BLE001 - CANNOT RUN, named, never ✅
        src["fates_error"] = f"{BACKLOG_REL} NOT READ ({type(exc).__name__}: {_SS.clean(exc, 120)})"
    # No second `errors["backlog"]` here: the NEEDS YOU read above reads the same file through the same
    # parser and already names it NOT READ — a copy would mask that clause (X1's mutation measured it).
    # backlog #389: the plans of EVERY checkout, through the one plan reader. A main checkout with no
    # `.claude/plans/` holds no plan — a fact, said as a note; any other failure is NOT READ.
    src["plans"], src["plan_notes"] = [], []
    wl = _sibling("gen-work-lines")
    plan_dir = main / ".claude" / "plans"
    if main_why:
        errors["plans"] = f"the main checkout could not be named, so its plans were NOT READ ({main_why})"
    else:
        try:
            # ⟳ r1 X3: a main checkout with no `.claude/plans/` does NOT end the read — a linked
            # worktree's plans are still read, through any checkout's directory that exists (the reader
            # enumerates every checkout from there). The missing directory stays a note.
            notes0, read_from = [], plan_dir
            if not plan_dir.is_dir():
                notes0.append(f"no .claude/plans/ in the main checkout ({main}) — no plan is armed there")
                dirs, dnotes = wl.plan_dirs(main)
                notes0 += list(dnotes)
                read_from = next((pd for _, pd in dirs if pd.is_dir()), None)
            if read_from is None:
                src["plan_notes"] = notes0
            else:
                plans, notes = (read_plans or wl.read_plans_noted)(read_from)
                src["plans"], src["plan_notes"] = open_plans(plans, wl), notes0 + list(notes)
        except Exception as exc:                  # noqa: BLE001 - NOT READ, named, never "none"
            errors["plans"] = f"{plan_dir} NOT READ ({type(exc).__name__}: {_SS.clean(exc, 120)})"
    return src


# ── the log ───────────────────────────────────────────────────────────────────────────────────
def read_log(path: pathlib.Path) -> list[dict]:
    """Every logged snapshot, oldest first. Missing is empty; an unreadable line is Malformed."""
    if not path.exists():
        return []
    out = []
    for i, ln in enumerate(path.read_text().split("\n"), 1):
        if not ln.strip():
            continue
        try:
            rec = json.loads(ln)
            if not isinstance(rec, dict) or "goals" not in rec or "at" not in rec:
                raise ValueError("not a snapshot")
        except ValueError as exc:
            raise Malformed(f"{path.name} line {i} is not a snapshot ({exc})") from None
        out.append(rec)
    return out


def append_if_changed(path: pathlib.Path, snap: dict) -> bool:
    """Append `snap` unless it says what the newest logged snapshot says. True when appended.
    ⛔ An incomplete snapshot is REFUSED here too, not only by the caller."""
    if snap["cannot"]:
        raise ValueError("refusing to log a snapshot whose sources could not all be read")
    log = read_log(path)
    if log and fingerprint(log[-1]) == fingerprint(snap):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(snap, sort_keys=True, ensure_ascii=False) + "\n")
    return True


# ── the agenda (backlog #499) ────────────────────────────────────────────────────────────────
# Asked 2026-11-04 06:05 (option A): the CURRENT plan in its own dated block, every earlier one kept
# as a collapsed line "for analytics purpose". ⛔ NAMED "agenda", NOT "plan": in this file a plan is
# an implementation-plan FILE read through gen-work-lines (`open_plans`), and two things called plan
# is the duplicate vocabulary check-vocabulary-collisions.py exists to refuse. The page says "AGENDA —
# the current plan", so the owner's word is still on it.
#
# The owner's three answers, 2026-11-04 15:33: the log is LOCAL and git-ignored (plans change several
# times a day; a PR per change is friction); an agenda is recorded EACH TIME the coordinator states
# one, and a new one replaces the current one WHOLE; a step naming no backlog row or PR is ALLOWED,
# marked, and ticked by hand. A step that names one is DERIVED through `derive_thread`, unchanged —
# so a step and the same row's tree leaf cannot disagree, and the agenda cannot silently go stale.
AGENDA_REL = ".claude/agenda-log.jsonl"
AGENDA_KINDS = ("agenda", "replaced", "tick")
AGENDA_FIELDS = {"agenda": (("id", int), ("window", str), ("steps", list)),
                 "replaced": (("of", int), ("states", list)),
                 "tick": (("of", int), ("step", int))}
WHEN_RE = re.compile(r"^## (\S.*)$")
STEP_RE = re.compile(r"^- (\S.*)$")
# ⛔ the kinds a ref names: exactly what the step grammar (`REF_RE`) writes. A ref of any other kind, or not a
# [kind, int] pair, is MALFORMED where it is read — never a TypeError in derivation (backlog #504).
# DERIVED from the alternation group of `REF_RE` (a new kind added to the grammar is a known kind here, never a log
# the writer produces and the reader refuses)
REF_KINDS = tuple(re.search(r"\(([^()]*)\)", REF_RE.pattern).group(1).split("|"))
FREE = "free"            # a step naming no backlog row or PR: its state is the owner-visible tick, never derived


def parse_agenda(text: str) -> dict:
    """PURE. The coordinator's stated plan -> an agenda. Raises Malformed naming EVERY bad line.

        window: until the weekly reset (Fri 11-06 02:00)
        change-if: the owner reprioritises; usage reaches today's stop
        ## today
        - backlog #499 · slice 1: the agenda store and derived step states
        - restart the page server and check one Refresh click
        ## after the reset
        - backlog #495 · the intermittent sweep case
    """
    window, change_if, when, steps, problems = None, None, None, [], []
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith(("window:", "change-if:")):
            key, val = line.split(":", 1)
            if (window if key == "window" else change_if) is not None:
                problems.append(f"line {i}: a second `{key}:` line — an agenda states each once")
            elif key == "window":
                window = val.strip() or None
            else:
                change_if = val.strip() or None
        elif (m := WHEN_RE.match(line)):
            when = m.group(1).strip()
        elif (m := STEP_RE.match(line)):
            if when is None:
                problems.append(f"line {i}: a step before any `## <when>` group: {line!r}")
                continue
            steps.append({"when": when, "text": m.group(1).strip(),
                          "refs": [[k, int(n)] for k, n in REF_RE.findall(m.group(1))]})
        else:
            problems.append(f"line {i}: an agenda line is `window:`, `change-if:`, `## <when>` or "
                            f"`- <step>`: {line!r}")
    if not window:
        problems.append("no `window:` line — an agenda says what period it covers")
    if not steps:
        problems.append("no steps — an agenda with nothing in it is not a plan")
    if problems:
        raise Malformed("; ".join(problems))
    return {"window": window, "change_if": change_if, "steps": steps}


# ⛔ ONE line model for the reader and both writers, so a log that reads is never refused on write, nor the reverse:
# `\r\n`, a lone `\r` and `\n` each end a line — what `read_text()`'s universal newlines read (r3 Claude N1).
_EOL = re.compile(r"\r\n|\r|\n")
_EOL_B = re.compile(_EOL.pattern.encode())     # the same model over bytes, for the blank repair's byte offsets


def _blank(line: str) -> bool:
    """A line the reader skips — whitespace only, by `str.strip()` — and the ONLY kind the blank repair cuts: one
    predicate, so the two cannot disagree about what is blank (r3 Claude N2)."""
    return not line.strip()


def _agenda_records(text: str, name: str) -> list[dict]:
    out = []
    for i, ln in enumerate(_EOL.split(text), 1):
        if _blank(ln):
            continue
        try:
            rec = json.loads(ln)
            if not isinstance(rec, dict) or rec.get("kind") not in AGENDA_KINDS or "at" not in rec:
                raise ValueError("not an agenda record")
            # ⛔ every field a reader indexes is checked HERE, so a bad record is MALFORMED, never a KeyError
            # in the snapshot (r3 Codex M3)
            for key, typ in AGENDA_FIELDS[rec["kind"]]:
                if not isinstance(rec.get(key), typ) or isinstance(rec.get(key), bool):
                    raise ValueError(f"a {rec['kind']} record needs `{key}` ({typ.__name__})")
            if rec["kind"] == "agenda" and not all(
                    isinstance(st, dict) and isinstance(st.get("when"), str) and isinstance(st.get("text"), str)
                    and isinstance(st.get("refs"), list) for st in rec["steps"]):
                raise ValueError("an agenda step needs `when`, `text` and `refs`")
            if rec["kind"] == "agenda" and not all(_ref_ok(x) for st in rec["steps"] for x in st["refs"]):
                raise ValueError("an agenda step's refs are [kind, number] pairs of a known kind (backlog #504)")
            # ⛔ a frozen state is READ by the history and the page: each is `{n: int, state: str}`, or MALFORMED
            # here — never a TypeError in the snapshot (slice 2, r1 Codex H1)
            if rec["kind"] == "replaced" and not all(
                    isinstance(x, dict) and isinstance(x.get("n"), int) and not isinstance(x.get("n"), bool)
                    and isinstance(x.get("state"), str) for x in rec["states"]):
                raise ValueError("a frozen state needs `n` (int) and `state` (str)")
        except ValueError as exc:
            raise Malformed(f"{name} line {i} is not an agenda record ({exc})") from None
        out.append(rec)
    return out


def read_agenda_log(path: pathlib.Path) -> list[dict]:
    """Every agenda record, oldest first. Missing is empty; an unreadable line is Malformed."""
    return _agenda_records(path.read_bytes().decode("utf-8"), path.name) if path.exists() else []


def agendas(log: list[dict]) -> list[dict]:
    """PURE. The log -> every agenda, oldest first, each with its hand ticks and, once replaced, the
    states its steps were in at that moment. The LAST one is current; the rest are history.
    ⛔ A `tick` or `replaced` record names the agenda it belongs to (`of`, the agenda's `id`), and one
    that names any agenda but the current one, or arrives before any, is MALFORMED — never dropped,
    never attached to whichever agenda happens to be last (r1 Codex H2)."""
    out: list[dict] = []
    for i, rec in enumerate(log, 1):
        if rec["kind"] == "agenda":
            if out and out[-1]["replaced"] is None:
                raise Malformed(f"agenda record {i} (id {rec.get('id')}) follows agenda id {out[-1].get('id')} "
                                f"without closing it")
            if rec.get("id") != len(out) + 1:
                raise Malformed(f"agenda record {i} has id {rec.get('id')!r}, expected {len(out) + 1}")
            out.append(dict(rec, ticked=[], replaced=None))
            continue
        if not out or rec.get("of") != out[-1]["id"] or out[-1]["replaced"] is not None:
            raise Malformed(f"{rec['kind']} record {i} names agenda {rec.get('of')!r}, which is not the open "
                            f"agenda ({out[-1]['id'] if out and out[-1]['replaced'] is None else 'none'})")
        if rec["kind"] == "tick":
            out[-1]["ticked"].append(rec["step"])
        else:
            out[-1]["replaced"] = {"at": rec["at"], "states": rec["states"]}
    return out


def _refset(refs: list) -> frozenset:
    """A step's or thread's refs as a SET: `backlog #2, backlog #1` names what `backlog #1, backlog #2` does."""
    return frozenset(map(tuple, refs))


def derive_agenda(ag: dict | None, src: dict, threads: list[dict] = ()) -> dict | None:
    """PURE. One agenda + the read sources -> its steps with `state` and `detail`. A step naming a
    row or PR goes through `derive_thread`, the tree's own derivation, WITH the `waits` a declared
    thread naming the same refs carries — so a row the tree shows ❌ waiting is not ⬜ here (r1 Codex
    H1). ⚠ BOUND: the policy is ANY WAIT WINS. Two leaves for one row, one waiting, show ⬜ and ❌ in the
    tree; the step shows ❌, agreeing with the waiting leaf only (r3 Codex M1, stated rather than fixed). A free step is FREE until ticked by hand, then `merged` (done), and says which."""
    if ag is None:
        return None
    # ⛔ keyed by the ref SET, and EVERY declared wait counts: two threads naming the same refs, one waiting,
    # make the step wait — in either declaration order (r2 Codex H1, H2)
    declared: dict = {}
    for t in threads:
        if t.get("waits"):
            said = declared.setdefault(_refset(t["refs"]), [])
            if t["waits"] not in said:
                said.append(t["waits"])
    waits = {k: "; ".join(sorted(v)) for k, v in declared.items()}   # sorted: no declaration order (r3 Codex L4)
    steps = []
    for n, st in enumerate(ag["steps"], 1):
        if st["refs"]:
            d = derive_thread({"key": f"step {n}", "refs": st["refs"],
                               "waits": waits.get(_refset(st["refs"]))}, src)
            steps.append(dict(st, n=n, state=d["state"], detail=d["detail"]))
        elif n in ag.get("ticked", []):
            steps.append(dict(st, n=n, state="merged", detail="ticked by hand (names no backlog row or PR)"))
        else:
            steps.append(dict(st, n=n, state=FREE, detail="names no backlog row or PR — ticked by hand"))
    return {"at": ag["at"], "id": ag.get("id"), "window": ag["window"], "change_if": ag.get("change_if"),
            "steps": steps}


def _locked(path: pathlib.Path, write):
    """Read the log and append to it under ONE exclusive lock, so two recorders cannot both read the
    same open agenda and each close it (r1 Codex H2). `write(current_agendas)` returns the lines."""
    import fcntl
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as fh:       # BYTES: a text read translates CRLF, so a length it counts is no file offset (r2 Codex F1)
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        raw = fh.read()
        keep = _blank_tail_cut(raw)
        text = raw[:keep].decode("utf-8")
        # ⛔ validated BEFORE the file is touched: a log refused as malformed is left exactly as it was (r2 Codex F3)
        lines, said = write(agendas(_agenda_records(text, path.name)))
        if keep != len(raw):
            fh.truncate(keep)
        out = "" if not text or text.endswith("\n") else "\n"   # a last line with no newline would fuse with the next record (r3 Codex M2)
        fh.write((out + "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines)).encode("utf-8"))
    return said


def _blank_tail_cut(raw: bytes) -> int:
    """How many bytes of the log to KEEP. Only what is provably not data is cut: the blank lines AFTER the last
    record's own line ending (backlog #504), or the whole of a log that holds nothing but blanks — lines and blanks
    as the READER sees them (`_EOL`, `_blank`; r3 Claude N1, N2). The last record, any blanks on its own line, and
    its line ending — `\n`, `\r\n` or a lone `\r` — are kept byte for byte (r2 Codex F1)."""
    keep = pos = 0                               # an all-blank log holds no record: all of it is cut
    for m in _EOL_B.finditer(raw):
        if not _blank(raw[pos:m.start()].decode("utf-8")):
            keep = m.end()                       # a record's line, kept WITH its own line ending
        pos = m.end()
    if not _blank(raw[pos:].decode("utf-8")):
        keep = len(raw)                          # a last line with no line ending: kept whole, nothing after it
    return keep


def _open_or_refuse(cur: list[dict]) -> None:
    """⛔ A log whose last agenda is CLOSED with no successor is an interrupted write; appending to it would
    leave a record replay refuses, so both writers refuse first (r2 Codex M3)."""
    if cur and cur[-1]["replaced"] is not None:
        raise Malformed(f"agenda id {cur[-1]['id']} was replaced but no new agenda follows (an interrupted "
                        f"write) — repair {AGENDA_REL} before recording or ticking")


def record_agenda(path: pathlib.Path, ag: dict, now: str, src: dict | None, threads: list[dict] = ()) -> str:
    """Append `ag` as the current agenda. The one it replaces is closed FIRST with each step's state
    at this moment (from `src`), so the history records what was done by the time it changed."""
    def write(cur):
        _open_or_refuse(cur)
        lines = []
        if cur:
            prev = cur[-1]
            if src is None:
                states = [{"n": n, "state": "cannot"} for n in range(1, len(prev["steps"]) + 1)]
            else:
                states = [{"n": s["n"], "state": s["state"]} for s in derive_agenda(prev, src, threads)["steps"]]
            lines.append({"kind": "replaced", "at": now, "of": prev["id"], "states": states})
        lines.append(dict(ag, kind="agenda", at=now, id=len(cur) + 1))
        return lines, f"agenda recorded at {now} ({len(ag['steps'])} step(s)) -> {AGENDA_REL}"
    return _locked(path, write)


def tick_agenda(path: pathlib.Path, n: int, now: str) -> str:
    """Tick step `n` of the current agenda by hand. ⛔ REFUSED for a step that names a row or PR —
    its state is derived, and a hand tick there would be a second source of truth — and for a step
    already ticked."""
    def write(cur):
        if not cur:
            raise Malformed("there is no agenda to tick — record one first")
        _open_or_refuse(cur)
        steps = cur[-1]["steps"]
        if not 1 <= n <= len(steps):
            raise Malformed(f"step {n} does not exist: the current agenda has {len(steps)} step(s)")
        if steps[n - 1]["refs"]:
            raise Malformed(f"step {n} names {', '.join(f'{k} #{v}' for k, v in steps[n - 1]['refs'])}: its "
                            f"state is derived, never ticked by hand")
        if n in cur[-1]["ticked"]:
            raise Malformed(f"step {n} is already ticked")
        return [{"kind": "tick", "at": now, "of": cur[-1]["id"], "step": n}], f"agenda step {n} ticked by hand"
    return _locked(path, write)


def _is(x, typ) -> bool:
    return isinstance(x, typ) and not isinstance(x, bool)


def _ref_ok(r) -> bool:
    return _is(r, list) and len(r) == 2 and r[0] in REF_KINDS and _is(r[1], int)


def _steps_ok(steps, keys) -> bool:
    # ⛔ `refs` is a LIST before it is iterated (`"refs": 1` raised TypeError in snap_history and the page replay), and
    # each `n` is UNIQUE (two steps of one n made changes() report a move between identical snapshots) — backlog #504
    return (_is(steps, list) and all(isinstance(st, dict) and _is(st.get("n"), int)
                                     and all(_is(st.get(k), t) for k, t in keys)
                                     and _is(st.get("refs", []), list)
                                     and all(_ref_ok(r) for r in st.get("refs", [])) for st in steps)
            and len({st["n"] for st in steps}) == len(steps))


def snap_agenda(snap: dict) -> tuple[str, object]:
    """PURE. THE ONE READER of a snapshot's `agenda` (slice 2, r2 Codex H1/M2 — the redesign: r1 patched each reader,
    and r2 found the same class in the readers it had not touched). Returns `(kind, value)`:
      absent    — no key: the snapshot predates agendas, and says NOTHING about whether there was one;
      none      — the key holds None: no agenda was recorded;
      malformed — the message: either the log said so, or the value is not an agenda's shape;
      ok        — the agenda, its identity (`id`, `at`) and every step field a reader indexes checked.
    ⛔ No reader indexes `snap["agenda"]` but through this."""
    if "agenda" not in snap:
        return "absent", None
    ag = snap["agenda"]
    if ag is None:
        return "none", None
    if isinstance(ag, dict) and "malformed" in ag:
        return "malformed", str(ag["malformed"])
    if not (isinstance(ag, dict) and _is(ag.get("id"), int) and _is(ag.get("at"), str) and _is(ag.get("window"), str)
            and (ag.get("change_if") is None or _is(ag.get("change_if"), str))
            and _steps_ok(ag.get("steps"), (("state", str), ("text", str), ("when", str), ("detail", str),
                                            ("refs", list)))):
        return "malformed", "the snapshot's agenda is not an agenda (an id, a time, a window and checked steps)"
    return "ok", ag


def snap_history(snap: dict) -> tuple[list, str | None]:
    """PURE. The ONE reader of a snapshot's `agenda_history`: (the earlier agendas, None), or ([], why not)."""
    hist = snap.get("agenda_history", [])
    # ⛔ no `or []`: a FALSY malformed value (false, "", 0) is still malformed, and is said (r3 Codex L2)
    ok = _is(hist, list) and all(
        isinstance(h, dict) and _is(h.get("id"), int) and all(_is(h.get(k), str) for k in ("at", "replaced_at", "window"))
        and _steps_ok(h.get("steps"), (("state", str), ("text", str))) for h in hist)
    return (hist, None) if ok else ([], "the snapshot's earlier agendas are not in an agenda's shape")


_FINISHED = ("merged", "closed", "superseded", "withdrawn")
_STAMP = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d")


def step_goals(snap: dict, ag: dict) -> dict[int, list[str]]:
    """PURE (backlog #509). Step n -> the goals it serves, `GOAL n · slug` — `goal_agenda_steps` INVERTED, so a step's
    goal and a goal's `agenda step` tag are one rule read both ways and cannot disagree. A step no goal declares maps
    to nothing; its line says `no goal` rather than guessing (owner 2026-11-05 08:19)."""
    out: dict[int, list[str]] = {}
    goals = snap.get("goals") or []
    for i, g in sorted(zip(goal_numbers(goals), goals), key=lambda ig: ig[0]):  # the TREE's numbers, in order (r1 Codex M1)
        for n in goal_agenda_steps(g, ag):
            out.setdefault(n, []).append(goal_head(i, g["slug"]))
    return out


def agenda_digest(snap: dict, ag: dict) -> dict:
    """PURE (backlog #509, owner 11-05 14:37). What the agenda block says beyond its steps, as DATA, so the text
    lines (`agenda_context`) and the page's laid-out block read ONE derivation:
      now   — the threads in flight (⏳, not parked), each with its goal and its one-line `what`;
      focus — the steps not yet done, grouped by goal: the plan read as areas, not a flat list;
      late  — threads MERGED after the plan was set that no step names (owner 08:24: a page generated at 08:15 showed
              the plan set 19:55 the day before, and said nothing). Compared only when both times are
              `YYYY-MM-DD HH:MM`; any other stamp says nothing rather than guess;
      done  — every step is done."""
    goals = snap.get("goals") or []
    now, named = [], frozenset().union(*(_refset(st["refs"]) for st in ag["steps"]))
    late, seen = [], set()
    for i, g in sorted(zip(goal_numbers(goals), goals), key=lambda ig: ig[0]):  # the TREE's numbers (r1 Codex M1)
        for t in g["threads"]:
            label = t["key"].split(" · ", 1)[-1]
            # the ledger's `inflight` flag, not only the state: a thread whose row has not landed reads `cannot` while
            # its work is plainly in flight (measured 11-05: #509 and #510, rows filed in a PR still open)
            # ⛔ …and never a FINISHED one: a ledger entry left naming a merged PR keeps its flag (measured 11-05: four
            # merged threads, PR #411 among them, read as in flight on the live tree)
            # running-vs-owed r2 Codex H1: a thread with an OPEN PR is in flight whatever its worst state reads
            if ((t.get("inflight") or t.get("open_prs") or t["state"] in ("open", "inflight")) and not t.get("parked")
                    and (t["state"] not in _FINISHED or t.get("open_prs"))):   # backlog #518: a finished leaf still OWNING an open PR is live
                # owner 11-05 15:45 (card A): RUNNING is an open PR nothing declares a wait on; the rest is OWED, with the
                # wait it declares (`· waits on …`) or none recorded — the tree cannot see a background job or agent
                ops = t.get("open_prs") or ([t["open_pr"]] if t.get("open_pr") is not None else [])
                now.append({"label": label, "goal": goal_head(i, g["slug"]), "what": t.get("what") or "",
                            "running": bool(ops or t["state"] == "open") and not t.get("waits"),
                            "waits": t.get("waits"),
                            # one PR reached by two declarations is ONE item (r1 Codex M1): merged by EVERY PR (r2 M1)
                            "prs": list(ops)})
            ended = t.get("merged_at")
            if (t["state"] == "merged" and isinstance(ended, str) and _STAMP.fullmatch(ended)
                    and _STAMP.fullmatch(ag["at"]) and ended > ag["at"]
                    and not named.intersection(_refset(t.get("refs") or [])) and label not in seen):
                seen.add(label)
                late.append(f"{label} (merged {ended[5:]})")
    # r1 Codex M2: ledger work no goal claims is in flight too — the tree lists it under IN FLIGHT, UNDER NO GOAL
    # r1 Codex M2 (agenda-digest): its purpose too — the ledger's `what`, cut to one line
    now += [{"label": u["id"], "goal": "no goal", "what": _one_line(u.get("what")), "running": False, "waits": None}
            for u in snap.get("inflight_loose") or [] if isinstance(u, dict) and "id" in u]
    # owner 11-05 15:45: an open PR no goal declares is RUNNING work too — listed by its title, not only counted
    # kept OUT of `now`, so the text lines are unchanged; the page lists them under Running now
    stray = [{"label": f"PR #{u['pr']}", "goals": ["no goal"], "what": _one_line(u.get("title")), "running": True,
              "waits": None}
             for u in snap.get("undeclared") or [] if isinstance(u, dict) and isinstance(u.get("pr"), int)]
    focus: dict[str, list[dict]] = {}
    sg = step_goals(snap, ag)
    for st in ag["steps"]:
        if st["state"] not in ("merged", "closed") and st["refs"]:
            for gl in sg.get(st["n"]) or ["no goal"]:
                focus.setdefault(gl, []).append(st)
    # r1 Codex L1 (item 4): say how old the plan is beside the snapshot's own time, when both are minute stamps
    at, mins = snap.get("at"), None
    if isinstance(at, str) and _STAMP.fullmatch(at) and _STAMP.fullmatch(ag["at"]) and at >= ag["at"]:
        try:  # r3 Codex L1: the pattern admits 2026-02-30 and 24:00, which strptime refuses — say nothing, never crash
            mins = int((_dt.datetime.strptime(at, MINUTE_FMT) - _dt.datetime.strptime(ag["at"], MINUTE_FMT)).total_seconds()
                       // 60)
        except ValueError:
            mins = None
    # r1 Codex M1 (agenda-digest): every step not done is LEFT, a free one too — the recap never says "none left"
    # while All steps still shows an open one
    left = sum(st["state"] not in ("merged", "closed") for st in ag["steps"])
    return {"now": now, "undeclared": len(snap.get("undeclared") or []), "stray": stray, "focus": focus, "left": left, "at": at,
            "mins": mins,
            "late": late, "done": bool(ag["steps"]) and all(st["state"] in ("merged", "closed") for st in ag["steps"])}


def agenda_recap(d: dict) -> str:
    """PURE (owner 11-05 14:37: "these in flight items and focus should help me to capture current thrust"). One
    sentence read off the digest: how much is in flight, across how many goals, and where the next steps lean."""
    goals_now = {x["goal"] for x in d["now"] if x["goal"] != "no goal"}
    items = agenda_now_items(d)   # one piece of work under two goals is ONE piece
    run = sum(x["running"] for x in items) + len(d.get("stray") or [])   # an undeclared open PR is running too
    items = items + list(d.get("stray") or [])
    # owner 11-05 15:45: say what is RUNNING apart from what is OWED — never "in flight" for work nobody is doing
    head = (f"{run} running and {len(items) - run} owed across {len(goals_now)} "
            f"goal{'s' if len(goals_now) != 1 else ''}" if items else "Nothing is running or owed")
    left = d.get("left", 0)   # every step not done, a free one too; a step under two goals counts once
    if not left:
        return head + "; no step of the plan is left."
    if not d["focus"]:
        return head + f"; {left} step{'s' if left != 1 else ''} left, none on a goal's work."
    top, steps = max(d["focus"].items(), key=lambda kv: len(kv[1]))   # ties keep the first goal, in step order
    return head + f"; the plan's next steps lean on {top} ({len(steps)} of {left} left)."


def _one_line(text, limit: int = 140) -> str:
    """PURE. A free-text field as one line of at most `limit` characters, cut with `…`."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= limit else t[:limit - 1] + "…"


def agenda_now_items(d: dict) -> list[dict]:
    """PURE. The digest's NOW entries merged BY WORK ITEM, in first-seen order: one item serving two goals is one entry
    carrying both goals, so the page lists each piece of work once."""
    # running-vs-owed r2 Codex M1: two entries are ONE item when they share a label or ANY open PR, and an entry that
    # shares with two items joins them — so a thread naming PR #21 and PR #30 is one item with a row resolved to #30
    groups: list[dict] = []
    for x in d["now"]:
        prs = set(x.get("prs") or [])
        hits = [g for g in groups if x["label"] in g["labels"] or prs & g["prs"]]
        if not hits:
            hits = [{"labels": set(), "prs": set(), "item": {"label": x["label"], "goals": [], "what": "",
                                                            "running": False, "waits": None}}]
            groups.append(hits[0])
        g = hits[0]
        for o in hits[1:]:                           # the later items fold into the first, in first-seen order
            g["labels"] |= o["labels"]; g["prs"] |= o["prs"]
            _fold_item(g["item"], o["item"]["goals"], o["item"])
            groups.remove(o)
        g["labels"].add(x["label"]); g["prs"] |= prs
        _fold_item(g["item"], [x["goal"]], x)
    return [g["item"] for g in groups]


def _fold_item(it: dict, goals: list, x: dict) -> None:
    """One entry folded into an item: its goals, its purpose if the item has none, a wait under ANY goal holds it."""
    for gl in goals:
        if gl not in it["goals"]:
            it["goals"].append(gl)
    it["what"] = it["what"] or x["what"]
    it["waits"] = it["waits"] or x.get("waits")
    it["running"] = (it["running"] or x.get("running", False)) and not it["waits"]


def agenda_context(snap: dict, ag: dict) -> list[tuple[str, str]]:
    """PURE (backlog #509). The digest as (kind, text) lines, for --print: now, focus, age, stale."""
    d, out = agenda_digest(snap, ag), []
    loose = d["undeclared"]
    out.append(("now", "now: " + (" · ".join(f"⏳ {x['label']} → {x['goal']}" for x in d["now"]) if d["now"]
                                   else "nothing in flight")
                + (f" · + {loose} open PR(s) no goal declares (UNDECLARED, below)" if loose else "")))
    if d["focus"]:
        out.append(("focus", "focus: " + " · ".join(
            f"{gl} (step{'s' if len(sts) > 1 else ''} {', '.join(str(st['n']) for st in sts)})"
            for gl, sts in d["focus"].items())))
    if d["mins"] is not None:
        out.append(("age", f"age: set {d['mins'] // 60} h {d['mins'] % 60:02d} m before this snapshot ({d['at']})"))
    if d["late"]:
        out.append(("stale", f"⚠ STALE — merged after this plan was set, and named by no step: {', '.join(d['late'])}. "
                             "Re-record the agenda."))
    if d["done"]:
        out.append(("stale", "⚠ every step is done — the plan is finished. Record the next one."))
    return out


def agenda_lines(snap: dict) -> list[str]:
    """PURE. The current agenda as text, grouped by when. Empty when none is recorded, or none was captured."""
    kind, ag = snap_agenda(snap)
    if kind in ("absent", "none"):
        return []
    if kind == "malformed":
        return [f"AGENDA — NOT READ: MALFORMED — {ag}"]
    out = [f"AGENDA — the current plan, set {ag['at']} · {ag['window']}"]
    if ag.get("change_if"):
        out.append(f"  changes if: {ag['change_if']}")
    out += [f"  {text}" for _, text in agenda_context(snap, ag)]
    out += [f"  {ln}" for ln in agenda_step_lines(snap, ag)]
    hist, bad = snap_history(snap)
    if bad:
        out.append(f"  ⚠ earlier agendas NOT READ — {bad}")
    if hist:
        out.append(f"  earlier agendas ({len(hist)}), newest first — collapsed on the page")
        out += ["    " + history_line(h) for h in hist]
    return out


def agenda_step_items(snap: dict, ag: dict) -> list[tuple[str, str]]:
    """PURE. The steps grouped by when, each ending with its goals, as (kind, line) with kind "when" or "step" — ONE
    source for the text and the page, so the page never slices them out of the text by counting the lines above (r1
    Codex L2), and never tells a group from a step by its indentation (PR #559 r1: a hand-edited log can indent a when)."""
    out, sg, when = [], step_goals(snap, ag), None
    for st in ag["steps"]:
        if st["when"] != when:
            when = st["when"]
            out.append(("when", when))
        goal = (" → " + ", ".join(sg.get(st["n"]) or ["no goal"])) if st["refs"] else ""
        out.append(("step", f"  {st['n']}. {step_glyph(st['state'])} {st['text']} — {st['detail']}{goal}"))
    return out


def agenda_step_lines(snap: dict, ag: dict) -> list[str]:
    """PURE. The text form of agenda_step_items."""
    return [ln for _, ln in agenda_step_items(snap, ag)]


def step_glyph(state: str) -> str:
    """PURE. A step's glyph: a leaf's, except a free step not yet ticked is ◇."""
    return "◇" if state == FREE else GLYPH.get(state, "?")


def agenda_history(cur: list[dict]) -> list[dict]:
    """PURE. Every REPLACED agenda, NEWEST FIRST (owner, 2026-11-04 06:06: kept "for analytics purpose", one
    collapsed line each). A step's state is the one frozen when its agenda was replaced, never re-derived — the
    history says what was done BY THEN. ⚠ A step the frozen list does not name is `cannot`, never a guess."""
    out = []
    for ag in reversed(cur):
        if ag["replaced"] is None:
            continue
        frozen = {x.get("n"): x.get("state") for x in ag["replaced"]["states"] if isinstance(x, dict)}
        out.append({"id": ag["id"], "at": ag["at"], "replaced_at": ag["replaced"]["at"], "window": ag["window"],
                    "steps": [dict(st, n=n, state=frozen.get(n) or "cannot")
                              for n, st in enumerate(ag["steps"], 1)]})
    return out


def history_line(h: dict) -> str:
    """PURE. An earlier agenda as ONE line — the same words in --print and on the page's collapsed summary."""
    done = sum(1 for st in h["steps"] if st["state"] == "merged")
    return (f"agenda #{h['id']} · set {h['at']} · replaced {h['replaced_at']} · "
            f"{done}/{len(h['steps'])} done by then · {h['window']}")


def goal_agenda_steps(g: dict, ag: dict | None) -> list[int]:
    """PURE. The current agenda's steps that name a ref one of this goal's threads names — the goal's `agenda step
    n` tag, so a step can be found in the tree and a goal on the agenda. A free step names nothing, so tags none."""
    if snap_agenda({"agenda": ag})[0] != "ok":
        return []
    refs = {tuple(r) for t in g["threads"] for r in t.get("refs") or []}
    return [st["n"] for st in ag["steps"] if refs.intersection(_refset(st["refs"]))]


# ── rendering ─────────────────────────────────────────────────────────────────────────────────
# PURE. Text split into (piece, href) — every `PR #N` and `backlog #N` becomes a link. The ONE
# implementation is `page_markup.key_segments` (backlog #470); this name is the tree's import of it.
segments = page_markup.key_segments


def _leaf(t: dict, b: str, rel: bool = False) -> str:
    """One leaf's text. A parked or queued leaf says so; a folded leaf carries its relation (its branch is gone)."""
    label = f"{b} · " if b in ("parked", "queued") else ""
    return (f'{GLYPH[t["state"]]} {label}' + (f'[{t["relation"]}] ' if rel else "")
            + f'{t["key"].split(" · ", 1)[1]} · {t["what"]} — {t["detail"]}')


def goal_head(n: int, slug: str) -> str:
    """PURE. A goal's numbered title, `GOAL 3 · slug` — ONE spelling for --print, the page heading and its anchor."""
    return f"GOAL {n} · {slug}"


def goal_numbers(goals: list[dict]) -> list[int]:
    """PURE. Each goal's number, in file order: its rank by its FIRST request's time, ties in file order (review r1
    X3). A goal added with a later first request moves no other number, wherever in the file it is declared; ⚠ one
    added with an earlier (or equal, declared above) time, or a goal deleted, still renumbers those after it."""
    order = sorted(range(len(goals)), key=lambda i: (goals[i]["requests"][0]["when"], i))
    rank = {i: r for r, i in enumerate(order, 1)}
    return [rank[i] for i in range(len(goals))]


def _goal_blocks(g: dict, at, n: int, tags: list[int] = ()) -> list:
    """PURE. Goal number `n` as ONE `("goal", n, slug, first_request, counts, tags, blocks)` block (see `tree_blocks`).
    The visible buckets keep the relation branches; `older` and `later` become one FOLD each, a last sibling whose
    text line counts what the page folds away. `counts` is set only when NOTHING is current: the page then folds
    the whole goal under its heading."""
    rest = g["requests"][1:]
    lines = [f'     + {r["when"]} "{r["quote"]}"' for r in rest]
    marked = [(t, bucket(t, at)) for t in g["threads"]]
    shown = [(t, b) for t, b in marked if b in VISIBLE]
    folds = []
    older = [t for t, b in marked if b == "older"]
    if older:
        what = "merged" if all(t["state"] == "merged" for t in older) else "merged or closed"
        folds.append(("older", f"older ({len(older)}) — {what} more than {RECENT_HOURS} h before {at}",
                      f"… {len(older)} older {what} (collapsed on the page)", older, "older"))
    later = [t for t, b in marked if b == "later"]
    if later:
        folds.append(("later", f"later ({len(later)}) — not started, bookkeeping or an aside",
                      f"… {len(later)} later (collapsed on the page)", later, "later"))
    rels = [r for r in RELATIONS if any(t["relation"] == r for t, _ in shown)]
    if not g["threads"]:
        lines.append("└─ (no thread declared)")
    n_items = len(rels) + len(folds)
    for ri, rel in enumerate(rels):
        last_rel = ri == n_items - 1
        lines.append(("└─ " if last_rel else "├─ ") + rel)
        ts = [(t, b) for t, b in shown if t["relation"] == rel]
        for ti, (t, b) in enumerate(ts):
            stem = "   " if last_rel else "│  "
            lines.append(stem + ("└─ " if ti == len(ts) - 1 else "├─ ") + _leaf(t, b))
    blocks: list = [("pre", lines)]
    for fi, (cls, summary, text, ts, b) in enumerate(folds):
        stem = "└─ " if len(rels) + fi == n_items - 1 else "├─ "
        blocks.append(("fold", cls, stem + summary, stem + text, [("pre", [_leaf(t, b, rel=True) for t in ts])]))
    counts = None
    if g["threads"] and not shown:
        # Nothing current: the WHOLE goal folds on the page, its counts beside its heading; the text is unchanged.
        counts = "nothing current (" + ", ".join(f"{len(f[3])} {f[0]}" for f in folds) + ")"
    return [("goal", n, g["slug"], g["requests"][0], counts, list(tags), blocks), ("pre", [""])]


def tree_blocks(snap: dict, at=None) -> list:
    """PURE. The tree as blocks: `("pre", lines)` or `("fold", cls, summary, text, blocks)`. The page draws a fold
    as a collapsed `<details>`; the text prints its `text` line instead of its contents, or — when `text` is None
    (a whole folded goal) — its contents. ONE structure, so --print and the page cannot disagree (backlog #363).
    `at` is the moment the tree is drawn (default: the snapshot's own time), and decides only the buckets."""
    at = snap["at"] if at is None else at
    blocks: list = []
    # ⭐ The owner, 2026-11-04 01:14: goals are NUMBERED so they can be found. The number is never a goal's place
    # among the shown ones, so it is stable whatever folds — and (review r1 X3) it is `goal_numbers`, by TIME.
    numbers = goal_numbers(snap["goals"])
    for i, g in enumerate(snap["goals"]):
        blocks += _goal_blocks(g, at, numbers[i], goal_agenda_steps(g, snap.get("agenda")))
    lines: list[str] = []
    if snap["undeclared"]:
        lines.append("UNDECLARED — open PRs no goal names (shown, never folded in)")
        for i, u in enumerate(snap["undeclared"]):
            lines.append(("└─ " if i == len(snap["undeclared"]) - 1 else "├─ ")
                         + f'PR #{u["pr"]}{" (draft)" if u["draft"] else ""} · {u["title"]}')
        lines.append("")
    if snap["inflight_loose"]:
        lines.append("IN FLIGHT, UNDER NO GOAL (from .claude/inflight.jsonl)")
        for i, u in enumerate(snap["inflight_loose"]):
            lines.append(("└─ " if i == len(snap["inflight_loose"]) - 1 else "├─ ")
                         + f'{u["id"]} · {u["what"]}')
        lines.append("")
    parked_loose = snap.get("parked_loose") or []
    if parked_loose:
        lines.append("PARKED / QUEUED — NO GOAL (parked ledger entries naming no live thread; shown, never dropped)")
        for i, u in enumerate(parked_loose):
            lines.append(("└─ " if i == len(parked_loose) - 1 else "├─ ") + f'{u["id"]} · {u["what"]}'
                         + (" · names only LANDED threads: " + "; ".join(u["landed"]) if u.get("landed") else ""))
        lines.append("")
    plans = snap.get("plans") or []
    if plans:
        lines.append(f"PLANS NOT TICKED CLOSED — {len(plans)}, from every checkout's .claude/plans/ "
                     f"(not ticked closed is not abandoned; the date is the file's last touch)")
        for i, p in enumerate(plans):
            why = (f'line {p["line"]}: "{p["serving"]}"' if p.get("serving")
                   else f'line {p["line"]}, no objective recorded')
            lines.append(("└─ " if i == len(plans) - 1 else "├─ ")
                         + f'{p["plan"]} · {p["ticked"]}/{p["total"]} · {p["touched"]}'
                         + (f' · branched from {p["parent"]}' + (" (reconstructed)" if p.get("reconstructed") else "")
                            if p.get("parent") else "")
                         + f' · {why}')
        lines.append("")
    for n in snap.get("plan_notes") or []:
        lines.append(f"⚠ plans: {n}")
    for p in snap.get("ledger_problems") or []:
        lines.append(f"⚠ ledger: {p}")
    for c in snap["cannot"]:
        lines.append(f"⚠ CANNOT RUN — {c}")
    merged: list = []
    for bk in blocks + [("pre", lines)]:       # adjacent runs of lines are ONE `<pre>`
        if bk[0] == "pre" and merged and merged[-1][0] == "pre":
            merged[-1] = ("pre", merged[-1][1] + bk[1])
        else:
            merged.append(bk)
    # The tree never ends on a blank line.
    if merged and merged[-1][0] == "pre" and merged[-1][1][-1:] == [""]:
        merged[-1] = ("pre", merged[-1][1][:-1])
    return [bk for bk in merged if bk[0] != "pre" or bk[1]]


def _flat(blocks: list) -> list[str]:
    out: list[str] = []
    for b in blocks:
        if b[0] == "pre":
            out += b[1]
        elif b[0] == "goal":
            _, n, slug, first, _counts, tags, inner = b
            out += [f'{goal_head(n, slug)} ({first["when"]}) "{first["quote"]}"' + tag_text(tags)] + _flat(inner)
        else:
            out += [b[3]] if b[3] is not None else _flat(b[4])
    return out


def tag_text(tags: list[int]) -> str:
    """PURE. A goal's agenda tag, ` · agenda step 3, 4`, or "" — one spelling for --print and the page."""
    return f" · agenda step {', '.join(map(str, tags))}" if tags else ""


def tree_lines(snap: dict, at=None) -> list[str]:
    """PURE. The box-drawing tree, one string per line, refs left as text (`render_*` link them)."""
    return _flat(tree_blocks(snap, at))


def needs_state(snap: dict) -> str:
    """PURE. "items", "none" (all three sources read, nothing found) or "not-read" (empty, and at
    least one source was NOT READ — which is never reported as nothing)."""
    if snap.get("needs"):
        return "items"
    return "not-read" if snap.get("needs_not_read") or "needs" not in snap else "none"


def _item_line(n: dict) -> str:
    bits = [f'[{n["source"]}] {n["ref"]} · {n["text"]}']
    if n.get("multi") is not None:
        bits.append(f'stands for {n["multi"]} open answers')
    if n.get("flag"):
        bits.append(f'⚠ {n["flag"]}')
    if n.get("conflict"):
        bits.append(f'⚠ {n["conflict"]}')
    for a in n.get("also") or []:
        bits.append(f'also recorded in {a["source"]} {a["ref"]}: {a["text"]}'
                    + (f' (stands for {a["multi"]} open answers)' if a.get("multi") is not None else ""))
    if counts_conflict(n):
        bits.append("⚠ the sources state different counts")
    return " · ".join(bits)


def story(ch: list[str]) -> str:
    """PURE. ONE sentence for a timeline entry (owner 2026-11-05 17:28: "one prose summary for the story line"): what
    happened, by kind, naming only what LANDED and the goals that opened. The change lines stay underneath, muted."""
    if ch == ["first snapshot"]:
        return "The first snapshot."
    if ch == [NO_READER_CHANGE]:   # timeline-story r3 P2: the producer's own "nothing to see" is never "1 change(s)"
        return "No change a reader would see; only the wording moved."

    def ref(line):  # "[fix] PR #511 · what" → "PR #511"
        return line.split("] ", 1)[1].split(" · ", 1)[0]

    def n(*pfx):
        return sum(c.startswith(pfx) for c in ch)

    def names(refs):   # at most three named, then a count, so one sentence stays one line
        return ", ".join(refs[:3]) + (f" and {len(refs) - 3} more" if len(refs) > 3 else "")
    # A state line is "[rel] name: A → GLYPH B — detail". The TRANSITION is read from its own slot, never searched
    # for in the whole line: a detail can say "→ ✅ merged" (timeline-story r1 Codex P2)
    trans = [(ref(c[:m.start()]), m[1], m[2]) for c in ch if c.startswith("[")
             for m in [re.search(r": (\w+) → \S+ (\w+) — ", c)] if m]
    added = [(ref(k), rest) for c in ch if c.startswith("added [") for k, _, rest in [c[6:].partition(": ")]]
    # an added thread already merged LANDED in this interval (its glyph is the merged one), so it is told as landed
    landed = [r for r, a, b in trans if b == "merged" and a != "merged"] + [
        r for r, rest in added if rest.startswith(GLYPH["merged"])]
    moved = [f"{r} → {b}" for r, a, b in trans if b != "merged" and a != b]
    goals = [c.split(": ", 1)[1] for c in ch if c.startswith("goal added: ")]
    bits = [f"{head} {names(refs)}" for head, refs in (
        ("goal opened:", goals), ("landed", landed),
        # "added [rel] KEY: GLYPH detail" — a key is refs only, so it ends at the first ": " (timeline-story r2 P2)
        ("added", [r for r, rest in added if not rest.startswith(GLYPH["merged"])]),
        # "declared on master: [rel] name (was in the ledger as …): …" — the ref ends at the hand-off note (r1 P2)
        ("declared on master:", [ref(c[20:].split(" (was in the ledger", 1)[0]) for c in ch
                                 if c.startswith("declared on master: ")]),
        ("moved", moved), ("removed", [ref(c[8:]) for c in ch if c.startswith("removed [")]),
        ("goal removed:", [c.split(": ", 1)[1] for c in ch if c.startswith("goal removed: ")])) if refs]
    for count, one, many in ((sum(a == b for _, a, b in trans) + n("[") - len(trans), "a thread's detail changed",
                              "{} threads' details changed"),
                             (n("needs you, new: "), "a new ask for you", "{} new asks for you"),
                             (n("needs you, cleared: "), "an ask cleared", "{} asks cleared"),
                             (n("agenda "), "the agenda changed", "the agenda changed"),
                             # a plan newly owed is not progress (r1 P2): three kinds, three words
                             (n("plan not ticked closed, new: "), "a plan newly owing", "{} plans newly owing"),
                             (n("plan no longer owing: "), "a plan no longer owing", "{} plans no longer owing"),
                             (n("plan progress: "), "plan progress", "plan progress"),
                             (n("in flight, ", "no longer in flight", "ledger problem", "undeclared PR"),
                              "in-flight work changed", "in-flight work changed")):
        if count:
            bits.append(one if count == 1 else many.format(count))
    out = "; ".join(bits) or f"{len(ch)} change(s)"
    return out[0].upper() + out[1:] + "."


def needs_lines(snap: dict) -> list[str]:
    """PURE. The NEEDS YOU block as text, for --print; the page draws the same items as links. Two
    lists (X4): decisions only the owner can make, and actions only the owner can take."""
    st, items = needs_state(snap), snap.get("needs") or []
    if st == "none":
        return ["NEEDS YOU — nothing waits on you (dashboard asks, the in-flight ledger and the backlog "
                "were all read)"]
    out = []
    if st == "not-read":
        out.append("NEEDS YOU — NOT KNOWN: a source was NOT READ, so an empty list here is not an "
                   "all-clear")
    for kind, title in (("decision", "decision(s) only you can make, open now"),
                        ("action", "action(s) only you can take")):
        group = [n for n in items if n.get("kind", "decision") == kind]
        if not group:
            continue
        several = sum(1 for n in group if n.get("multi"))   # a declared 0 stands for no answers
        out.append(f"NEEDS YOU — {len(group)} {title}"
                   + (f" ({several} of them stand for several answers)" if several else ""))
        out += [("└─ " if i == len(group) - 1 else "├─ ") + _item_line(n) for i, n in enumerate(group)]
    out += [f"⚠ NOT READ — {w}" for w in snap.get("needs_not_read") or []]
    return out


def _ref_html(source: str, ref: str, href: str | None) -> str:
    if href:
        return f'<a href="{html.escape(href, quote=True)}">{html.escape(ref)}</a>'
    return f'<code>{html.escape(ref)}</code> <span class="src">(.claude/inflight.jsonl)</span>'


def needs_html(snap: dict) -> str:
    st, items = needs_state(snap), snap.get("needs") or []
    lines = needs_lines(snap)
    parts = [f'<section class="needs {st}">']
    heads = [ln for ln in lines if ln.startswith("NEEDS YOU")]
    if st == "none":   # owner 2026-11-05 17:28: nothing waiting is said quietly, never as a bright heading
        parts.append(f'<p class="quiet" title="{html.escape(heads[0])}">Needs you — nothing</p>')
    elif st != "items":
        parts.append(f"<h2>{html.escape(heads[0])}</h2>")
    for kind in ("decision", "action"):
        group = [n for n in items if n.get("kind", "decision") == kind]
        if not group:
            continue
        head = next(h for h in heads if ("decision(s)" if kind == "decision" else "action(s)") in h)
        parts.append(f"<h2>{html.escape(head)}</h2><ul>")
        for n in group:
            extra = ""
            if n.get("multi") is not None:
                extra += f' · <b>stands for {html.escape(str(n["multi"]))} open answers</b>'
            if n.get("flag"):
                extra += f' · <span class="warn">⚠ {html.escape(n["flag"])}</span>'
            if n.get("conflict"):
                extra += f' · <span class="warn">⚠ {html.escape(n["conflict"])}</span>'
            for a in n.get("also") or []:
                extra += (f' · also recorded in <span class="src">{html.escape(a["source"])}</span> '
                          + _ref_html(a["source"], a["ref"], a.get("href")) + ": " + html.escape(a["text"])
                          + (f' (stands for {html.escape(str(a["multi"]))} open answers)'
                             if a.get("multi") is not None else ""))
            if counts_conflict(n):
                extra += ' · <span class="warn">⚠ the sources state different counts</span>'

            parts.append(f'<li><span class="src">{html.escape(n["source"])}</span> '
                         f'{_ref_html(n["source"], n["ref"], n.get("href"))} · '
                         f'{html.escape(n["text"])}{extra}</li>')
        parts.append("</ul>")
    parts += [f'<p class="warn">⚠ NOT READ — {html.escape(w)}</p>'
              for w in snap.get("needs_not_read") or []]
    parts.append("</section>")
    return "".join(parts)


def agenda_html(snap: dict) -> str:
    """The AGENDA section, under NEEDS YOU: the current plan grouped by when, then every earlier agenda as ONE
    collapsed line (its `history_line`), newest first, expanding to its steps in their frozen states."""
    (kind, ag), repo = snap_agenda(snap), snap.get("repo")
    if kind == "absent":
        # ⛔ a snapshot taken before agendas were recorded CANNOT say there was none (slice 2, r1 Codex M3), nor
        # promise the next one will carry one (r2 Codex L3)
        return ('<section class="agenda none"><h2>AGENDA — not captured in this snapshot</h2><p class="lede">It '
                'was taken before agendas were recorded.</p></section>')
    if kind == "none":
        return ('<section class="agenda none"><h2>AGENDA — none recorded</h2><p class="lede">Recorded with '
                '<code>python3 scripts/goal-tree.py --record-agenda FILE</code> each time a plan is stated.</p>'
                '</section>')
    lines = agenda_lines({"agenda": snap["agenda"]})
    if kind == "malformed":
        return f'<section class="agenda"><h2 class="warn">{html.escape(lines[0])}</h2></section>'
    # owner 11-05 14:37: the heading in the goals' accent style; the plan's when and window on a meta line beneath
    d = agenda_digest(snap, ag)
    age = f" ({d['mins'] // 60} h {d['mins'] % 60:02d} m before this snapshot)" if d["mins"] is not None else ""
    parts = ['<section class="agenda">', '<h2 class="agenda-h">Agenda</h2>',
             f'<p class="meta">the current plan · set {html.escape(ag["at"])}{age} · {html.escape(ag["window"])}</p>']
    if ag.get("change_if"):
        parts.append(f'<p class="meta">changes if: {html.escape(ag.get("change_if") or "")}</p>')
    # …then a recap sentence, what is in flight one per line with its purpose, and the focus by goal (backlog #509)
    parts.append(f'<p class="recap">{html.escape(agenda_recap(d))}</p>')
    chip = lambda g: f'<span class="chip">{html.escape(g)}</span>'
    item = lambda x, tail="": (f'<li>{"".join(chip(g) for g in x["goals"])} {_html_line(x["label"], repo)}'
                               + (f' <span class="what">— {_html_line(x["what"], repo)}</span>' if x["what"] else "")
                               + tail + "</li>")
    items = agenda_now_items(d)
    run = [x for x in items if x["running"]] + list(d.get("stray") or [])
    owed = [x for x in items if not x["running"]]
    # owner 11-05 15:45 (card A): RUNNING apart from OWED, and each owed item says what it waits for
    parts.append('<div class="digest"><div><h3>Running now</h3><ul>' + "".join(item(x) for x in run)
        + ("" if run else "<li>nothing running</li>")
        + (f'<li class="warn">{d["undeclared"]} of these PRs no goal declares (UNDECLARED, below)</li>'
           if d["undeclared"] else "") + "</ul>"
        + '<p class="lede">open PRs only: a background job or an agent is not visible to this page</p>'
        + '<h3>Owed — not being worked</h3><ul>' + "".join(
            item(x, f' <span class="waits">waits for: {_html_line(x["waits"], repo) if x["waits"] else "not recorded"}'
                    "</span>") for x in owed)
        + ("" if owed else "<li>nothing owed</li>") + "</ul></div>")
    parts.append('<div><h3>Focus — the next steps, by goal</h3>' + "".join(
        f'<p class="focus-g">{chip(gl)}</p><ul>' + "".join(
            f'<li><b>{st["n"]}.</b> {_html_line(st["text"], repo)}</li>' for st in sts) + "</ul>"
        for gl, sts in d["focus"].items()) + ("" if d["focus"] else f'<p class="lede">{"no remaining step names a goal" if d["left"] else "no step left"}</p>')
        + "</div></div>")
    for kind_, text in agenda_context(snap, ag):
        if kind_ == "stale":
            parts.append(f'<p class="warn">{_html_line(text, repo)}</p>')
    parts.append('<h3>All steps</h3>')
    parts.append('<pre class="tree">' + "\n".join(
        f'<span class="ag-when">{_html_line(ln, repo)}</span>' if k == "when" else _html_line(ln, repo)
        for k, ln in agenda_step_items(snap, ag)) + "</pre>")
    hist, bad = snap_history(snap)
    if bad:
        parts.append(f'<p class="warn">⚠ earlier agendas NOT READ — {html.escape(bad)}</p>')
    if hist:
        parts.append(f'<h3>Earlier agendas ({len(hist)}), newest first</h3>')
        for h in hist:
            steps = [f"{st['n']}. {step_glyph(st['state'])} {st['text']}" for st in h["steps"]]
            parts.append(f'<details class="fold agenda-hist"><summary>{_html_line(history_line(h), repo)}</summary>'
                         '<pre class="tree">' + "\n".join(_html_line(x, repo) for x in steps) + "</pre></details>")
    parts.append("</section>")
    return "".join(parts)


def render_text(snap: dict, at=None) -> str:
    ag = agenda_lines(snap)
    return "\n".join(needs_lines(snap) + [""] + (ag + [""] if ag else []) + tree_lines(snap, at))


def _id_attr(t: str, ids: set | None) -> str:
    """` id="t-<kind>-<N>"` at a key's FIRST occurrence when `ids` collects them, else "" (spec §3:
    a key under several goals gets its id once, in render order; later ones are plain links)."""
    m = page_markup.KEY_REF.fullmatch(t)
    if ids is None or not m:
        return ""
    key = f"{m.group(1).lower()}-{m.group(2)}"
    if key in ids:
        return ""
    ids.add(key)
    return f' id="{page_markup.thread_id(key)}"'


def _html_line(line: str, repo: str | None, ids: set | None = None, qa: dict | None = None,
               hoist: list | None = None) -> str:
    out = []
    for t, h in segments(line, repo):
        a = _id_attr(t, ids)
        if h:
            out.append(f'<a{a} href="{html.escape(h, quote=True)}">{html.escape(t)}</a>')
        elif a:
            out.append(f'<span{a}>{html.escape(t)}</span>')
        else:
            out.append(html.escape(t))
        if a and qa:   # the key's FIRST occurrence on the live tree carries its answers, once
            if hoist is None:
                out.append(qa_html(qa.get(_thread_key(t), [])))
            elif qa.get(_thread_key(t)):    # inside a CLOSED fold: the marker goes after the fold (r1 C)
                hoist.append((t, qa[_thread_key(t)]))
    return "".join(out)


def _thread_key(t: str) -> str:
    m = page_markup.KEY_REF.fullmatch(t)
    return f"{m.group(1).lower()}-{m.group(2)}" if m else ""


def load_answers(path: pathlib.Path) -> tuple[list[dict], str]:
    """The answers file as a list of {key, asked, q, a}, and "" — or ([], <why>) when it cannot be read. A
    missing file is no answers yet, not an error. An entry missing a field is REFUSED by name, never skipped."""
    if not path.is_file():
        return [], ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data["answers"]
    except (ValueError, KeyError, TypeError, OSError) as e:   # OSError: a file it may not read (r3 L3)
        return [], f"{path.name} is unreadable ({type(e).__name__}: {e})"
    # ⛔ PR #558 r1 A: every SHAPE check is a refusal by name, never an exception — the page must still be written
    if not isinstance(rows, list):
        return [], f"{path.name}: `answers` is {type(rows).__name__}, not a list"
    bad = [i for i, r in enumerate(rows)
           if not isinstance(r, dict) or not all(isinstance(r.get(f), str) and r.get(f) for f in ("key", "q", "a"))]
    if bad:
        return [], f"{path.name}: entr{'y' if len(bad) == 1 else 'ies'} {bad} lack key, q or a"
    odd = [i for i, r in enumerate(rows) if "asked" in r and not isinstance(r["asked"], str)]
    if odd:
        return [], f"{path.name}: entr{'y' if len(odd) == 1 else 'ies'} {odd} carr{'ies' if len(odd) == 1 else 'y'} a non-text asked"
    # ⛔ PR #558 r2: JSON's `\ud800` escape parses to an unpaired surrogate, which no UTF-8 writer can encode — the
    # page write then raised and NO page was written. Refused here by name, like every shape above.
    def _encodes(s: str) -> bool:
        try:
            s.encode("utf-8")
            return True
        except UnicodeEncodeError:
            return False
    unenc = [i for i, r in enumerate(rows)
             if not all(_encodes(r[f]) for f in ("key", "q", "a", "asked") if isinstance(r.get(f), str))]
    if unenc:
        return [], f"{path.name}: entr{'y' if len(unenc) == 1 else 'ies'} {unenc} carr{'ies' if len(unenc) == 1 else 'y'} text that is not valid UTF-8"
    return rows, ""


def answers_by_key(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["key"].strip(), []).append(r)
    return out


def _qa_item(r: dict) -> str:
    when = f'<time>{html.escape(r["asked"])}</time> ' if r.get("asked") else ""
    paras = "".join(f"<p>{html.escape(p.strip())}</p>" for p in r["a"].split("\n\n") if p.strip())
    return (f'<div class="qa-item"><p class="qa-q">{when}<b>Q.</b> {html.escape(r["q"])}</p>'
            f'<div class="qa-a">{paras}</div></div>')


def qa_html(rows: list[dict], about: str = "") -> str:
    """A small `💬 N answer(s)` marker whose Q&A sits in a CLOSED `<details>` — never `open` (owner 2026-11-11
    06:18: interlacing Q&A with the tree is the clutter; collapse is the remedy). "" when there are none.
    `about` names the thread when the marker is HOISTED out of the closed fold its key sits in (r1 C)."""
    if not rows:
        return ""
    n = len(rows)
    head = f'💬 {n} answer{"" if n == 1 else "s"}' + (f" — {html.escape(about)} (folded above)" if about else "")
    return (f'<details class="qa"><summary>{head}</summary><div class="qa-body">'
            + "".join(_qa_item(r) for r in rows) + "</div></details>")


def older_qa_html(qa: dict, seen: set) -> str:
    """Answers whose goal or thread is NOT on the live tree: one collapsed section at the bottom, never dropped."""
    gone = [(k, r) for k, rows in qa.items() if k not in seen for r in rows]
    if not gone:
        return ""
    items = "".join(f'<p class="qa-key">{html.escape(k)}</p>{_qa_item(r)}' for k, r in gone)
    return (f'<details class="qa qa-older"><summary>💬 Older questions ({len(gone)}) — their goal or thread is '
            f'no longer on the tree</summary><div class="qa-body">{items}</div></details>')


def _hoisted(hoist: list) -> str:
    return "".join(qa_html(rows, about=t) for t, rows in hoist)


def _goal_html(b: tuple, repo, seen, qa=None, hoist=None) -> str:
    """One goal as its own bordered `<section>`, headed `GOAL n · slug` in the heading colour (owner, 2026-11-04
    01:14). A goal with nothing current keeps that heading as the summary of a CLOSED `<details>`."""
    _, n, slug, first, counts, tags, inner = b
    anchor = f' id="goal-{html.escape(slug, quote=True)}"' if seen is not None else ""   # by SLUG: a number can move
    asked = ""
    if seen is not None and f"goal:{slug}" not in seen:
        seen.add(f"goal:{slug}")
        asked = qa_html((qa or {}).get(f"goal:{slug}", []))
    head = (f'<h3 class="goal-h"><span class="goal-n">GOAL {n} ·</span> '
            f'<span class="goal-slug">{html.escape(slug)}</span></h3>'
            + (f'<span class="goal-agenda">{html.escape(tag_text(tags)[3:])}</span>' if tags else ""))
    quote = (f'<p class="goal-q"><time>{html.escape(first["when"])}</time> '
             f'{_html_line(chr(34) + first["quote"] + chr(34), repo)}</p>')
    if counts is not None:   # the markers sit OUTSIDE the fold, so a folded goal still shows it has answers —
        mine = [] if hoist is None else hoist   # its own, and its threads' (r1 C)
        body = _blocks_html(inner, repo, seen, qa, mine)
        return (f'<section class="goal"{anchor}><details class="fold goal"><summary>{head}'
                f'<span class="goal-counts"> — {html.escape(counts)}</span></summary>{quote}{body}</details>'
                f'{asked}{_hoisted(mine) if hoist is None else ""}</section>')
    body = _blocks_html(inner, repo, seen, qa, hoist)
    return f'<section class="goal"{anchor}>{head}{asked}{quote}{body}</section>'


def _blocks_html(blocks: list, repo, seen, qa=None, hoist=None) -> str:
    """`hoist` is None outside any closed fold. Inside one, a thread's answers are COLLECTED into it instead of
    drawn beside the key, and the OUTERMOST fold draws them right after itself, each naming its thread — so a
    marker is never hidden in a fold, as a goal's never was (PR #558 r1 C)."""
    out = []
    for b in blocks:
        if b[0] == "pre":
            if any(ln for ln in b[1]):      # a blank separator line is the section border's job on the page
                out.append('<pre class="tree">' + "\n".join(_html_line(ln, repo, seen, qa, hoist) for ln in b[1])
                           + "</pre>")
        elif b[0] == "goal":
            out.append(_goal_html(b, repo, seen, qa, hoist))
        else:
            mine = [] if hoist is None else hoist
            out.append(f'<details class="fold {b[1]}"><summary>{_html_line(b[2], repo)}</summary>'
                       + _blocks_html(b[4], repo, seen, qa, mine) + "</details>"
                       + (_hoisted(mine) if hoist is None else ""))
    return "".join(out)


def render_tree_html(snap: dict, ids: bool = False, at=None, qa: dict | None = None,
                     seen: set | None = None) -> str:
    """The tree as one `<div class="tree">` of `<pre>` runs and collapsed folds (`tree_blocks`). `ids=True` for
    the LIVE tree only: the timeline's past trees sit on the same page, so their ids would collide with it
    (backlog #470)."""
    seen = (set() if seen is None else seen) if ids else None
    return '<div class="tree">' + _blocks_html(tree_blocks(snap, at), snap.get("repo"), seen, qa) + "</div>"


TIMELINE_SHOWN = 6   # newest timeline entries shown open; the rest fold (owner 2026-11-05 17:28)


def render_page(log: list[dict], built: str, live: dict | None = None, answers: list[dict] = (),
                answers_error: str = "") -> str:
    """PURE. The page body: the newest snapshot as the current tree, then the timeline newest first.

    `live` is this run's derivation when it could not be logged (its `cannot` is non-empty), so the
    reader is told the tree below is older than the attempt, and why."""
    newest = log[-1]
    parts = ['<main>', '<p class="meta">DECLARED IN docs/goal-threads.md · STATES DERIVED FROM GIT, '
             'GH AND THE IN-FLIGHT LEDGER</p>', '<h1>Goal tree</h1>',
             page_chrome.chrome_bar("goal-tree", built),
             f'<p class="lede">Built <time>{html.escape(built)}</time> · newest snapshot '
             f'<time class="newest">{html.escape(newest["at"])}</time> (master '
             f'{html.escape(str(newest.get("head") or "unread"))}) · {len(log)} snapshot(s) logged.</p>',
             # ⭐ Y7: SAY it is a replay. The tree and timeline below are the stored snapshot, not a fresh
             # read, so a change to a source since then is invisible until the next snapshot.
             f'<p class="replay"><b>This page replays the snapshot taken at '
             f'<time class="replayed">{html.escape(newest["at"])}</time>.</b> NEEDS YOU is '
             + (f'read live at <time>{html.escape(live["at"])}</time>' if live is not None
                else 'from that snapshot too')
             + '. To refresh: <code>python3 scripts/goal-tree.py --snapshot --page</code>, or the '
             'Refresh button.</p>',
             '<p class="lede">Each thread hangs under the owner request it serves. The relation '
             '(fix, blocker, bookkeeping, side) is declared by hand; the state is read from git and gh '
             'when the snapshot is taken. ✅ merged · ⏳ open or in flight · ⬜ next · ❌ waits '
             '(declared) · ✖ closed, superseded (→ where the goal went) or withdrawn · ⚠ could not be '
             'read.</p>']
    if live is not None and live["cannot"]:
        parts.append('<p class="warn">⚠ The live read at ' + html.escape(live["at"]) + ' could NOT '
                     'run, so it was not logged: ' + html.escape("; ".join(live["cannot"])) +
                     '. The tree below is the newest COMPLETE snapshot.</p>')
    # ⭐ NEEDS YOU FIRST, above the tree (owner decision D1): read from THIS run when there was one,
    # complete or not, because a decision that appeared since the newest snapshot is the one to see.
    parts.insert(6, needs_html(live if live is not None else newest))
    # backlog #499: the AGENDA under NEEDS YOU — from the snapshot the tree below is, so step and leaf agree
    parts.insert(7, agenda_html(newest))
    # backlog #497: the current tree is bucketed at the BUILD time, as --print is at its run, so the two agree.
    qa, seen = answers_by_key(list(answers)), set()
    parts += ['<h2>Now</h2>', render_tree_html(newest, ids=True, at=built, qa=qa, seen=seen)]
    if answers_error:
        parts.append(f'<p class="warn">⚠ Answers to questions asked here are NOT shown: {html.escape(answers_error)}</p>')
    parts += ['<h2>Timeline</h2>',
              '<p class="lede">Newest first. A snapshot is logged only when the tree changed. Before this '
              f'page, the plan history was drawn by the work-lines page, now retired and FROZEN: '
              f'<a href="{WORK_LINES_ARCHIVE}">the work-lines archive</a> (backlog #389).</p>']
    # owner 2026-11-05 17:28: each entry reads as ONE sentence; its change lines are muted inside; past the newest
    # TIMELINE_SHOWN the entries fold into one "older" block, so the list does not run on
    for i in range(len(log) - 1, -1, -1):
        if i == len(log) - 1 - TIMELINE_SHOWN:
            parts.append(f'<details class="older"><summary>{i + 1} older snapshot(s), back to '
                         f'<time>{html.escape(log[0]["at"])}</time></summary>')
        snap, ch = log[i], changes(log[i - 1] if i else None, log[i])
        parts.append(f'<details class="snap"><summary><time>{html.escape(snap["at"])}</time> · '
                     f'<span class="story">{html.escape(story(ch))}</span></summary><ul class="lines">'
                     + "".join(f'<li>{_html_line(c, snap.get("repo"))}</li>' for c in ch)
                     + '</ul>' + render_tree_html(snap) + '</details>')
    if len(log) > TIMELINE_SHOWN:
        parts.append('</details>')
    parts += [older_qa_html(qa, seen), '</main>']   # at the BOTTOM: answers whose key left the tree
    return "\n".join(parts)


CSS = """
/* --good/--defect/--structure: read by the LIFTED Ask tray and SHIM (brief-compose); declared in every palette
   so the theme toggle is not half-live (brief-compose refuses a light palette that misses one). */
:root{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;--ink-faint:#838a9b;
      --rule:#ddd9d0;--pending:#8f6410;--link:#1d5fa8;--accent:#8a5a2b;
      --good:#2f7d63;--defect:#a3323c;--structure:#33607a;
      --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
      --ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;
      --ink-soft:#b4bac9;--ink-faint:#7d8496;--rule:#2e313b;--pending:#d9a441;--link:#7fb2ee;--accent:#cb9a68;
      --good:#6fcf9a;--defect:#f0937c;--structure:#82b4ee;}}
:root[data-theme="dark"]{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;--ink-soft:#b4bac9;
      --ink-faint:#7d8496;--rule:#2e313b;--pending:#d9a441;--link:#7fb2ee;--accent:#cb9a68;
      --good:#6fcf9a;--defect:#f0937c;--structure:#82b4ee;}
:root[data-theme="light"]{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;
      --ink-faint:#838a9b;--rule:#ddd9d0;--pending:#8f6410;--link:#1d5fa8;--accent:#8a5a2b;
      --good:#2f7d63;--defect:#a3323c;--structure:#33607a;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--ui);line-height:1.5}
main{max-width:72rem;margin:0 auto;padding:2rem 1rem}
h1{font-size:2rem;margin:.2rem 0 1rem}
h2{font-size:1.15rem;margin:1.6rem 0 .5rem}
.meta{font-family:var(--mono);font-size:.7rem;color:var(--ink-faint);letter-spacing:.04em}
.lede{color:var(--ink-soft);max-width:70ch}
.warn{color:var(--pending);font-weight:600}
a{color:var(--link)}
div.tree{overflow-x:auto}
div.tree>pre.tree,section.goal{background:var(--card);border:1px solid var(--rule);border-radius:.5rem;
         padding:.7rem 1.1rem .9rem;margin:0 0 1rem}
h3.goal-h{margin:.1rem 0 .3rem;color:var(--accent);font-family:var(--ui);font-weight:600;font-size:1rem;
         display:inline-block}
h3.goal-h .goal-slug{font-size:1.4rem;font-weight:700}
details.qa{display:inline-block;vertical-align:top;margin:0 0 0 .6ch;font-family:var(--ui);white-space:normal}
details.qa>summary{cursor:pointer;font-size:.72rem;color:var(--ink-faint);list-style:none}
details.qa>summary::-webkit-details-marker{display:none}
details.qa[open]{display:block;margin:.3rem 0 .5rem}
details.qa .qa-body{background:var(--bg);border:1px solid var(--rule);border-left:3px solid var(--accent);
         border-radius:.3rem;padding:.3rem .8rem;margin-top:.25rem;max-width:72ch;font-size:.85rem;line-height:1.45}
details.qa .qa-q{margin:.3rem 0;color:var(--ink)} details.qa .qa-a p{margin:.25rem 0;color:var(--ink-soft)}
details.qa .qa-q time{font-family:var(--mono);font-size:.72rem;color:var(--ink-faint)}
details.qa-older{display:block;margin:1.6rem 0 0} details.qa-older>summary{font-size:.85rem}
details.qa .qa-key{margin:.6rem 0 0;font-family:var(--mono);font-size:.72rem;color:var(--ink-faint)}
.goal-q{margin:0 0 .5rem;color:var(--ink-soft);font-size:.85rem;max-width:none}
.goal-q time{font-family:var(--mono);font-size:.75rem;color:var(--ink-soft)}
details.fold.goal>summary{white-space:normal;font-family:var(--ui);font-size:.9rem}
.goal-counts{color:var(--ink-soft)}
pre.tree{margin:0;font-family:var(--mono);font-size:.78rem;line-height:1.55;white-space:pre}
details.fold summary{cursor:pointer;font-family:var(--mono);font-size:.78rem;color:var(--ink-soft);
         white-space:pre}
details.fold pre.tree{padding-left:3ch;color:var(--ink-soft)}
details.fold.goal pre.tree{padding-left:0}
details.snap{border-bottom:1px solid var(--rule);padding:.35rem 0}
details.snap summary{cursor:pointer;font-size:.9rem}
details.snap time{font-family:var(--mono);font-size:.78rem;color:var(--ink-faint)}
details.snap ul{font-size:.85rem;margin:.4rem 0}
details.snap ul.lines{color:var(--ink-faint)}
details.older>summary{cursor:pointer;font-size:.85rem;color:var(--ink-faint);padding:.4rem 0}
.replay{background:var(--card);border:1px solid var(--rule);border-radius:.4rem;padding:.4rem .8rem;
        font-size:.9rem}
section.needs{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--pending);
              border-radius:.5rem;padding:.4rem 1.1rem .7rem;margin:1rem 0}
section.needs.none{background:none;border:none;padding:0;margin:.4rem 0}
section.needs p.quiet{margin:0;font-size:.8rem;color:var(--ink-faint)}
section.needs h2{margin:.5rem 0}
section.needs ul{margin:.3rem 0;padding-left:1.1rem;font-size:.9rem}
section.needs li{margin:.2rem 0}
section.agenda{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--accent);
               border-radius:.5rem;padding:.4rem 1.1rem .7rem;margin:1rem 0}
section.agenda.none{border-left-color:var(--rule)}
section.agenda pre.tree{overflow-x:auto}
section.agenda .ag-when{display:inline-block;margin-top:.55rem;font-family:var(--ui);font-size:.92rem;
  font-weight:700;color:var(--accent)}
section.agenda .ag-when::first-letter{text-transform:uppercase}
section.agenda h2{margin:.5rem 0}
section.agenda h3{font-size:.9rem;margin:.8rem 0 .3rem;color:var(--ink-soft)}
.waits{color:var(--warn,#d29922);font-size:.85rem;white-space:nowrap}
h2.agenda-h{margin:.4rem 0 .1rem;color:var(--accent);font-size:1.4rem;font-weight:700}
section.agenda .meta{margin:.1rem 0}
section.agenda .recap{margin:.6rem 0 .2rem;font-size:1rem;max-width:none}
section.agenda .digest{display:grid;grid-template-columns:repeat(auto-fit,minmax(22rem,1fr));gap:.2rem 2rem}
section.agenda .digest ul{list-style:none;margin:.2rem 0 .5rem;padding:0;font-size:.88rem}
section.agenda .digest li{margin:.25rem 0}
section.agenda .chip{display:inline-block;font-family:var(--mono);font-size:.7rem;color:var(--accent);
               border:1px solid var(--accent);border-radius:.8rem;padding:0 .5rem;margin-right:.3rem}
section.agenda .what{color:var(--ink-soft)}
section.agenda .focus-g{margin:.4rem 0 0}
.goal-agenda{margin-left:.6rem;font-family:var(--mono);font-size:.75rem;color:var(--accent)}
section.needs .src{font-family:var(--mono);font-size:.72rem;color:var(--ink-faint)}
"""


PAGE_TITLE = "Goal tree"
# The lift is bounded: a Refresh runs `goal-tree.py` with no arguments (= `--snapshot --page`) and explainer-serve
# waits REGEN_TIMEOUTS["goal-tree"] (60 s) for the WHOLE run. A compose that hangs must leave time to write the
# tray-less page and say so. ⚠ MEASURED 2026-11-11 on the real 8.2 MB page (round 1 Claude half): the compose
# alone 18.2 s, the whole `--page` 28.0 s, so the rest of `--page` ~9.8 s. MEASURED in the PR #558 r1 fold
# (`time python3 scripts/goal-tree.py --snapshot`, two runs): 5.3 s and 6.3 s. With a HUNG compose the run is
# 6.3 + 9.8 + COMPOSE_TIMEOUT; at 30 that is 46.1 s, leaving ~14 s of the 60 for the fallback write and the
# Refresh's own fresh-clone setup (not measured here). 30 is still 1.6x the measured normal compose.
# (Round 1 G: the old 40 left ~4 s — 6.3 + 9.8 + 40 = 56.1.)
COMPOSE_TIMEOUT = 30


def write_page(out: pathlib.Path, log: list[dict], built: str, live: dict | None = None, *,
               tray_source: str | None = None, answers_path: pathlib.Path | None = None,
               composer: list[str] | None = None) -> str:
    """Write the page, with the Ask tray LIFTED by `brief-compose.py` — never retyped (owner 2026-11-11:
    "goal-tree page do not have interactive 'ask' feature"). The same mechanism the backlog and dashboard
    pages use; `brief-compose.py`'s docstring records why the tray is never hand-copied.

    Returns "" when the tray was lifted, else the reason it was not. A missing tray is NOT fatal — a fresh
    clone has no explainer to lift one from, and a tree without the Ask button is still worth having — but
    it is never silent: the caller prints the reason. `tray_source` names the page to lift from (the
    self-test passes a tracked one); None lets `brief-compose` pick the newest page that has a tray.
    `answers_path` (default `ANSWERS_REL`) holds the answers to questions asked here; an unreadable one is
    said on the page AND on stderr, and the page is still written. `composer` replaces the brief-compose
    command (its arguments are appended) — the self-test's seam for a compose that exits 0 and writes no tray."""
    answers, answers_error = load_answers(answers_path or ROOT / ANSWERS_REL)
    if answers_error:
        print(f"⚠  goal tree: answers NOT shown — {answers_error}", file=sys.stderr)
    # Every key left as TEXT (NEEDS YOU's prose, the lede) becomes a link too (backlog #470).
    body = page_markup.link_html(render_page(log, built, live, answers, answers_error), log[-1].get("repo"))
    fragment = (f"<title>{PAGE_TITLE}</title>"
                f"<style>{CSS}\n{page_chrome.chrome_css()}</style>{body}"
                f"<script>{page_chrome.chrome_script()}</script>")
    page_chrome.assert_wired(fragment, "goal-tree.py")
    out.parent.mkdir(parents=True, exist_ok=True)
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        frag = pathlib.Path(td) / "goal-tree-fragment.html"
        frag.write_text(fragment, encoding="utf-8")
        cmd = (composer or [sys.executable, str(SCRIPTS / "brief-compose.py")]) + ["--content", str(frag),
               "--slug", "goal-tree", "--title", PAGE_TITLE, "--out", str(out)]
        if tray_source:
            cmd += ["--source", str(tray_source)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=COMPOSE_TIMEOUT)
            why = "" if r.returncode == 0 else (r.stderr.strip() or r.stdout.strip() or
                                                f"brief-compose exited {r.returncode} with no output")
        except subprocess.TimeoutExpired:
            why = f"brief-compose did not finish in {COMPOSE_TIMEOUT}s"
    # ⛔ ASKED OF THE FILE, not of the exit code: rc 0 with no tray on disk is the failure this exists for.
    if not why:
        written = out.read_text(encoding="utf-8") if out.is_file() else ""
        if not _has_tray(written):
            why = f"brief-compose exited 0 but {out} carries no Ask tray"
    if why:
        out.write_text(f"<!doctype html><meta charset=utf-8>"
                       f"<meta name=viewport content='width=device-width,initial-scale=1'>{fragment}")
    return why


def page_report(out: pathlib.Path, why: str) -> list[str]:
    """PURE. What `--page` prints for `write_page`'s answer. ⛔ The WHOLE reason, every line of it: brief-compose
    puts its headline on line 1 and the actionable part on line 2 (the backlog page learned it, r2 R2-9)."""
    if not why:
        return [f"goal tree page -> {out}  (Ask tray lifted)"]
    return ([f"goal tree page -> {out}", "⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:"]
            + ["   " + line for line in why.splitlines()]
            + ["   The page renders and refreshes; only the ask-a-question button is missing."])


def _has_tray(page: str) -> bool:
    """`brief-compose.has_tray`, ASKED of that module — one definition of what a tray is."""
    return _sibling("brief-compose").has_tray(page)


# ── the command ───────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None, *, root: pathlib.Path = ROOT, run=None,
         now: str | None = None) -> int:
    ap = argparse.ArgumentParser(description="Log the goal tree and render its page (backlog #363).")
    ap.add_argument("--snapshot", action="store_true", help="derive the states and log them if changed")
    ap.add_argument("--page", action="store_true", help="render the page from the log")
    ap.add_argument("--print", dest="print_", action="store_true", help="print the tree as text")
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--record-agenda", type=pathlib.Path, metavar="FILE",
                    help="record FILE as the current agenda, replacing the current one (backlog #499)")
    ap.add_argument("--tick-agenda", type=int, metavar="N",
                    help="tick step N of the current agenda by hand (only a step naming no row or PR)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.self_test:
        return _self_test()
    if not (a.snapshot or a.page or a.print_ or a.record_agenda or a.tick_agenda is not None):
        a.snapshot = a.page = True
    now = now or _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    main_root, why = _SS.main_checkout(root, run or _SS._run)
    if why:
        print(f"CANNOT RUN — the log lives in the MAIN checkout's {LOG_REL}, and {why}.")
        return 2
    # ⛔ backlog #610: the SERVED page is built only from a fresh origin/master, by regen-pages.py's private clone
    # (backlog #408), which alone sets REGEN_MAIN_CHECKOUT. A direct run here would overwrite it from WHATEVER tree
    # runs it: on 11-11 a bare run from a checkout 42 commits behind showed merged steps as CANNOT RUN. An explicit
    # --out (a test, a preview) is still allowed: it does not replace what the owner opens.
    if a.page and a.out == DEFAULT_OUT and not os.environ.get(_SS.MAIN_CHECKOUT_ENV):
        print(f"CANNOT RUN — the served page {DEFAULT_OUT} is built only from a fresh origin/master: run "
              f"`python3 scripts/regen-pages.py --page goal-tree`. Nothing was logged or written. (A preview: "
              f"add --out <file>.)")
        return 2
    log_path = main_root / LOG_REL
    agenda_path = main_root / AGENDA_REL
    rc, live = 0, None
    try:
        threads = root / THREADS_REL
        # the declared threads lend a step their `waits`; read only by the modes that derive (not --page)
        declared = ([t for g in parse_threads(threads.read_text()) for t in g["threads"]]
                    if (a.record_agenda or a.snapshot) and threads.is_file() else [])
        if a.record_agenda:
            try:
                text = a.record_agenda.read_text(encoding="utf-8")
            except OSError as exc:
                print(f"CANNOT RUN — the agenda file {a.record_agenda} was not read ({type(exc).__name__}); "
                      f"nothing was recorded.")
                return 2
            ag = parse_agenda(text)
            src = collect(root, run)
            # ⛔ the replaced agenda's states are only as good as the sources: an unread one is said
            print(record_agenda(agenda_path, ag, now,
                                None if src["errors"] and any(src["errors"].values()) else src, declared))
        if a.tick_agenda is not None:
            print(tick_agenda(agenda_path, a.tick_agenda, now))
        if a.snapshot:
            if not threads.is_file():
                print(f"CANNOT RUN — {THREADS_REL} does not exist, so there is no tree to draw.")
                return 2
            src = collect(root, run)
            live = derive(parse_threads(threads.read_text()), src, now)
            # ⛔ a malformed agenda log is SAID on the agenda block and in the exit code, and never takes the
            # snapshot down with it — the tree was read whole (r2 Codex M4)
            try:
                cur = agendas(read_agenda_log(agenda_path))
                live["agenda"] = derive_agenda(cur[-1] if cur else None, src, declared)
                live["agenda_history"] = agenda_history(cur)
            except Malformed as exc:
                live["agenda"] = {"malformed": str(exc)}
                live["agenda_history"] = []
                print(f"MALFORMED — {exc}")
                rc = 1
            if live["cannot"]:
                print("CANNOT RUN — the snapshot was NOT logged: " + "; ".join(live["cannot"]))
                rc = 2
            else:
                print("goal tree: " + ("snapshot logged" if append_if_changed(log_path, live)
                                       else "unchanged since the newest snapshot, not logged")
                      + f" -> {LOG_REL}")
        log = read_log(log_path)
    except Malformed as exc:
        print(f"MALFORMED — {exc}")
        return 1
    if a.page:
        if not log:
            print(f"CANNOT RUN — {LOG_REL} holds no complete snapshot, so no page was rendered.")
            return 2
        # A `backlog #N` naming no row is marked text, not a link to nothing (backlog #470).
        warn = _sibling("gen-backlog-page").publish_rows(root)
        if warn:
            print(warn)
        print("\n".join(page_report(a.out, write_page(a.out, log, now, live))))
    if a.print_:
        shown = live if live is not None else (log[-1] if log else None)
        if shown is None:
            print(f"CANNOT RUN — no snapshot to print ({LOG_REL} is empty).")
            return 2
        print(render_text(shown, now))
    return rc


# Fixtures for the NEEDS YOU sources, in each source's real grammar.
DASH_FIXTURE = ("## 2026-10-01 [needs-you]\nPick one for backlog #5.\n\n## 2026-10-02 [needs-you]\nAnother.\n\n"
                "## 2026-10-03 [resolved: 2026-10-02/1]\nDone.\n")
DASH_BAD = DASH_FIXTURE + "\n## 2026-10-04 [bogus-flag]\nx\n"
BACKLOG_FIXTURE = ("# B\n\n## Items\n\n| # | Item | Touches | Size | Bundle | Status |\n"
                   "|---|---|---|---|---|---|\n"
                   "| 5 | **Pick a name** — body | x | S | (t) | NEEDS-OWNER — waits on you |\n"
                   "| 6 | **Done one** | x | S | (t) | NEEDS-OWNER — answered 10-27 |\n"
                   "| 7 | ✅ **Closed** | x | S | (t) | ✅ fixed NEEDS-OWNER — old |\n"
                   "| 8 | **Plain** | x | S | (t) | OPEN |\n"
                   "| 9 | **Run it** | x | S | (t) | NEEDS-OWNER-ACTION — run the falsifier |\n"
                   "| 10 | **Depends** | x | S | (t) | NEEDS-OWNER — waits on backlog #11's call |\n"
                   "| 11 | **Parent** | x | S | (t) | DECIDED 2026-10-28 by the owner: A |\n")
BACKLOG_BAD = BACKLOG_FIXTURE + "| x9 | broken row | x |\n"


# ── self-test ─────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """No git and no gh: every source is a fixture, injected through `run`. Wrapped anyway, so that a
    later case that does reach git cannot inherit the caller's GIT_* (backlog #373). The body runs in ONE
    `_sibling_sweep()` (backlog #406); what a caller OUTSIDE a sweep sees is observed first, before it starts."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    """backlog #406: observe a caller outside any sweep, THEN run every case inside one sweep."""
    outside = _sibling_outside_probe()
    with _sibling_sweep():
        return _self_test_cases(outside=outside)


def _rewrite_same_stamp(f: pathlib.Path, text: str) -> None:
    """Rewrite `f` at the SAME size and put its mtime back: nothing a stat can see has changed."""
    st = f.stat()
    assert len(text.encode()) == st.st_size, "the rewrite must keep the size"
    f.write_text(text, encoding="utf-8")
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))


def _sibling_outside_probe() -> dict:
    """backlog #406: what `_sibling` does for a caller that is NOT in a sweep — every real caller, since only the
    self-test opens one. Run before the self-test's sweep starts, so it sees the module's own default state."""
    import py_compile
    import tempfile
    got = {"fresh": _sibling("gen-work-lines") is not _sibling("gen-work-lines")}
    real = SCRIPTS
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        (d / "sib-x.py").write_text("V = 1\n", encoding="utf-8")
        (d / "sib-s.py").write_text("V = 1\n", encoding="utf-8")
        (d / "dep-d.py").write_text("W = 1\n", encoding="utf-8")
        (d / "sib-d.py").write_text(
            "import importlib.util, pathlib\n"
            "_s = importlib.util.spec_from_file_location('_dep_d', pathlib.Path(__file__).with_name('dep-d.py'))\n"
            "_m = importlib.util.module_from_spec(_s)\n"
            "_s.loader.exec_module(_m)\n"
            "V = _m.W\n", encoding="utf-8")
        globals()["SCRIPTS"] = d
        try:
            x1 = _sibling("sib-x").V
            (d / "sib-x.py").write_text("V = 22\n", encoding="utf-8")
            got["rewritten"] = (x1, _sibling("sib-x").V)
            # r1 Codex F1 + Claude F2: same size, mtime put back, and a .pyc of the OLD source waiting.
            s1 = _sibling("sib-s").V
            py_compile.compile(str(d / "sib-s.py"), cfile=importlib.util.cache_from_source(str(d / "sib-s.py")),
                               doraise=True)
            _rewrite_same_stamp(d / "sib-s.py", "V = 2\n")
            got["same_stamp"] = (s1, _sibling("sib-s").V)
            # r1 Codex F2: only the file the sibling LOADS changes.
            d1 = _sibling("sib-d").V
            (d / "dep-d.py").write_text("W = 22\n", encoding="utf-8")
            got["dependency"] = (d1, _sibling("sib-d").V)
        finally:
            globals()["SCRIPTS"] = real
    return got


def _self_test_cases(*, outside: dict) -> int:
    import contextlib
    import io
    import tempfile
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    def malformed(text):
        try:
            parse_threads(text)
        except Malformed as exc:
            return str(exc)
        return "ACCEPTED"

    good = ("# preamble\n- prose list item above the first goal is ignored\n\n"
            "## GOAL alpha-one\n"
            '> 2026-10-26 09:51 "do the first thing"\n'
            '> 2026-10-27 03:28 "and keep going"\n'
            "- fix · backlog #10, PR #20 · the first fix\n"
            "- side · PR #21 · an aside\n"
            "- fix · backlog #11 · not started · waits on the owner\n"
            "## GOAL beta\n"
            '> 2026-10-28 03:41 "the second goal"\n'
            "- bookkeeping · PR #20 · filed rows\n")
    # ── backlog #406: a sibling is imported ONCE PER PATH inside a sweep, and afresh outside one ──────────
    case("backlog #406: the same sibling twice is ONE import", _sibling("gen-work-lines") is _sibling("gen-work-lines"),
         True)
    case("backlog #406: OUTSIDE a sweep, the same sibling twice is TWO imports", outside["fresh"], True)
    case("backlog #406: OUTSIDE a sweep, a sibling REWRITTEN in this process is imported afresh",
         outside["rewritten"], (1, 22))
    case("backlog #406: OUTSIDE a sweep, a SAME-SIZE rewrite with the mtime put back is the new source, never a "
         "stale .pyc (r1 Codex F1, Claude F2)", outside["same_stamp"], (1, 2))
    case("backlog #406: OUTSIDE a sweep, a change ONLY in a file the sibling's import loads is seen (r1 Codex F2)",
         outside["dependency"], (1, 22))
    _real_scripts = SCRIPTS
    with tempfile.TemporaryDirectory() as _std:
        _sd = pathlib.Path(_std)
        (_sd / "a").mkdir()
        (_sd / "b").mkdir()
        (_sd / "a" / "sib-p.py").write_text("V = 1\n", encoding="utf-8")
        (_sd / "b" / "sib-p.py").write_text("V = 2\n", encoding="utf-8")
        (_sd / "sib-n.py").write_text("V = 1\n", encoding="utf-8")
        # goal-tree itself has `from __future__ import annotations`; a sibling must not compile under it.
        (_sd / "sib-f.py").write_text("def f(a: int): pass\nV = f.__annotations__['a'] is int\n", encoding="utf-8")
        try:
            globals()["SCRIPTS"] = _sd / "a"
            _p1 = _sibling("sib-p").V
            globals()["SCRIPTS"] = _sd / "b"
            _p2 = _sibling("sib-p").V
            globals()["SCRIPTS"] = _sd
            _f = _sibling("sib-f").V
            # A nested sweep shares the outer one's memo: what it imported is still the module after it ends.
            with _sibling_sweep():
                _n_inner = _sibling("sib-n")
            _n_shared = _sibling("sib-n") is _n_inner
            # A sweep that RAISES puts the previous state back (r3 Claude F1/F5's lesson: the restore is in
            # `finally`, and a case makes that load-bearing). Opened from the no-sweep state, as a real caller would.
            _held, globals()["_SIBLING_MEMO"] = _SIBLING_MEMO, None
            try:
                try:
                    with _sibling_sweep():
                        _sibling("sib-n")
                        raise ValueError("the sweep fails")
                except ValueError:
                    pass
                _after_raise = (_SIBLING_MEMO is None, _sibling("sib-n") is not _sibling("sib-n"))
            finally:
                globals()["_SIBLING_MEMO"] = _held
        finally:
            globals()["SCRIPTS"] = _real_scripts
    case("backlog #406: one name in two directories is two imports — the memo is keyed on the PATH", (_p1, _p2),
         (1, 2))
    case("backlog #406: a sibling compiles as ITSELF, never under goal-tree's own `from __future__` flags", _f, True)
    case("backlog #406: a NESTED sweep shares the outer memo, so its import is still the module after it ends",
         _n_shared, True)
    case("backlog #406: a sweep that RAISES leaves no memo on — every call after it is a fresh import again",
         _after_raise, (True, True))
    case("backlog #406: ...and SCRIPTS is restored, so the real siblings are read again",
         _sibling("gen-work-lines").__name__, "_gen_work_lines")

    goals = parse_threads(good)

    # ── the grammar ──────────────────────────────────────────────────────────────────────────
    case("goals are read in order, by slug", [g["slug"] for g in goals], ["alpha-one", "beta"])
    case("the first request is the goal's own words, with its time",
         goals[0]["requests"][0], {"when": "2026-10-26 09:51", "quote": "do the first thing"})
    case("every request is kept, not only the first", len(goals[0]["requests"]), 2)
    case("refs are read as (kind, number) pairs, in order",
         goals[0]["threads"][0]["refs"], [["backlog", 10], ["PR", 20]])
    case("a thread's what is read up to the optional waits field",
         (goals[0]["threads"][2]["what"], goals[0]["threads"][2]["waits"]),
         ("not started", "the owner"))
    case("a thread with no waits field has waits None", goals[0]["threads"][1]["waits"], None)
    case("the same refs under ANOTHER relation or goal is a different thread",
         goals[1]["threads"][0]["key"], "bookkeeping · PR #20")
    case("⛔ a relation outside the closed set is refused",
         "relation 'fixx' is not one of" in malformed(good.replace("- side ·", "- fixx ·")), True)
    case("⛔ a thread naming neither a backlog row nor a PR is refused",
         "must be `backlog #N` / `PR #N`" in malformed(good.replace("PR #21 ·", "the docs ·")), True)
    case("⛔ refs followed by anything but ` · ` are refused — the whole field must be refs",
         "must be `backlog #N`" in malformed(good.replace("PR #21 ·", "PR #21 maybe ·")), True)
    case("⛔ a bare #N is not a ref — the namespace is required",
         "must be `backlog #N`" in malformed(good.replace("PR #21 ·", "#21 ·")), True)
    case("⛔ a line inside a goal that is neither a request nor a thread is refused",
         "must be a `> ` request" in malformed(good + "stray prose\n"), True)
    case("⛔ a mistyped GOAL heading is refused, not read as prose that hides its threads",
         "not `## GOAL <slug>`" in malformed(good.replace("## GOAL beta", "## GAOL beta")), True)
    case("⛔ a request without a time is refused",
         "a request must be" in malformed(good.replace('> 2026-10-28 03:41 "', '> 2026-10-28 "')), True)
    case("⛔ a goal that quotes no request is refused",
         "quotes no request" in malformed(good.replace('> 2026-10-28 03:41 "the second goal"\n', "")),
         True)
    case("⛔ a duplicated goal slug is refused",
         "declared twice" in malformed(good.replace("## GOAL beta", "## GOAL alpha-one")), True)
    case("⛔ a duplicated thread in one goal is refused",
         "declared twice in goal" in malformed(good + "- bookkeeping · PR #20 · again\n"), True)
    case("⛔ a file with no goal at all is refused", "no `## GOAL" in malformed("# just prose\n"), True)
    case("⛔ EVERY bad line is named, not only the first",
         len(re.findall(r"^line \d+:", malformed(good.replace("- side ·", "- fixx ·") + "stray\n"),
                        re.M)), 2)
    case("a bad line names its LINE NUMBER",
         "line 8:" in malformed(good.replace("- side ·", "- fixx ·")), True)

    # ── the derived states ───────────────────────────────────────────────────────────────────
    def src(**kw):
        base = {"merged_by_pr": {20: "aaaa111"}, "merged_rows": [("aaaa111", 20, "x (backlog #10) (#20)")],
                "open": {21: {"number": 21, "title": "aside", "isDraft": True,
                              "mergeStateStatus": "CLEAN",
                              "statusCheckRollup": [{"conclusion": "SUCCESS"}]},
                         30: {"number": 30, "title": "work (backlog #11)", "isDraft": False,
                              "statusCheckRollup": []},
                         99: {"number": 99, "title": "old thing", "isDraft": False}},
                "all": {20: "MERGED", 21: "OPEN", 22: "CLOSED", 23: "MERGED"},
                "all_merge_sha": {23: "bbbb2222"}, "ledger": [], "ledger_problems": [],
                "head": "aaaa111", "repo": "o/r", "errors": {}, "fates_error": None,
                "fates": {n: None for n in range(1, 100)}}   # rows 1-99 exist, none fated
        base.update(kw)
        return base

    def every_line(blocks):
        """Every line of a tree's blocks, the CONTENTS of each fold included (what the page holds, open or not)."""
        return [ln for bk in blocks for ln in (bk[1] if bk[0] == "pre" else every_line(bk[-1]))]

    def one(t, s):
        return derive_thread(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n' + t)[0]["threads"][0], s)

    m = one("- fix · backlog #10, PR #20 · f\n", src())
    case("a PR in master's subjects is MERGED, with its SHA", (m["state"], m["detail"]),
         ("merged", "merged time unread · aaaa111"))
    o = one("- side · PR #21 · a\n", src())
    case("an open PR shows draft, mergeability and the checks summary",
         (o["state"], o["detail"]), ("open", "PR #21 open · draft · clean · 1 pass"))
    case("a closed PR is CLOSED, never open", one("- side · PR #22 · c\n", src())["state"], "closed")

    # ── backlog #505: a ledger entry declares its thread before master does ──────────────────────
    _g2 = parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked\n'
                        '## GOAL h\n> 2026-01-01 00:00 "q"\n- side · PR #21 · aside\n')
    _e = {"id": "w505", "what": "build it", "goal": "g", "thread": "fix · PR #30 · in flight"}
    _lt = derive(_g2, src(ledger=[_e]), "T")
    _hung = [t for t in _lt["goals"][0]["threads"] if t["key"] == "fix · PR #30"]
    case("backlog #505: a ledger entry's thread hangs under ITS goal, in flight, saying it is not yet on master",
         (len(_hung), _hung[0]["state"] if _hung else None,
          "declared in the ledger (w505), not yet on master" in (_hung[0]["detail"] if _hung else ""),
          [u["pr"] for u in _lt["undeclared"]], _lt["inflight_loose"]),
         (1, "open", True, [99], []))
    case("backlog #505: the TRACKED file wins — a ledger thread sharing a ref with any declared thread is not added",
         [[t["key"] for t in g["threads"]] for g in ledger_threads(_g2, [dict(_e, thread="fix · PR #21 · dup")])[0]],
         [["fix · backlog #10"], ["side · PR #21"]])
    case("backlog #505: an unknown goal and a bad line are PROBLEMS on the page, never dropped",
         [x.split(" — ")[0] if "not read" in x else x for x in derive(_g2, src(ledger=[
             dict(_e, goal="nope"), dict(_e, id="w2", thread="fix · issue #3 · x")]), "T")["ledger_problems"]],
         ["entry w2: its thread is not read", "entry w505: goal 'nope' is not declared in docs/goal-threads.md"])
    _g1 = parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #12 · other\n')
    case("backlog #505: the SAME entry is judged against the goals it is given — hung under one goal set, "
         "a problem under a set without its goal, and suppressed under a set that declares its ref",
         ([len(g["threads"]) for g in ledger_threads(_g1, [_e])[0]], ledger_threads(_g1[:0] + parse_threads(
             '## GOAL h\n> 2026-01-01 00:00 "q"\n- side · PR #9 · x\n'), [_e])[1],
          [len(g["threads"]) for g in ledger_threads(parse_threads(
              '## GOAL g\n> 2026-01-01 00:00 "q"\n- side · PR #30 · tracked\n'), [_e])[0]]),
         ([2], ["entry w505: goal 'g' is not declared in docs/goal-threads.md"], [1]))
    _gh = parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n## GOAL h\n> 2026-01-01 00:00 "q"\n')
    _two = ledger_threads(_gh, [_e, dict(_e, id="w9", goal="h", thread="side · PR #30 · again")])
    case("backlog #505: two ledger entries hanging the same ref — the FIRST wins, the second is a named problem "
         "(r1 Codex M1)", ([[t["key"] for t in g["threads"]] for g in _two[0]], _two[1]),
         ([["fix · PR #30"], []], ["entry w9: its thread's refs are already hung by entry w505 — the id that sorts first wins"]))
    _pre = derive(_g2, src(ledger=[_e]), "T1")
    _post = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked\n'
                                 '## GOAL h\n> 2026-01-01 00:00 "q"\n- side · PR #21 · aside\n'
                                 '- side · backlog #11, PR #30 · tracked now\n'), src(ledger=[_e]), "T2")
    _ch = changes(_pre, _post)
    case("backlog #505: the MERGE hand-off is one 'declared on master' line, never a false added + removed, even "
         "when its key and goal changed (r1 Codex M2)",
         ([l.split(":")[0] for l in _ch if "PR #30" in l], any(l.startswith(("added", "removed")) for l in _ch)),
         (["declared on master"], False))
    _a0 = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked\n'), src(), "T1")
    _a1 = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked\n'
                               '- fix · PR #20 · new: with a colon\n'), src(), "T2")
    case("timeline story, from the REAL producer: an added thread is named by its key alone, never its state or "
         "detail (r2 P2)", story(changes(_a0, _a1)), "Landed PR #20.")   # the fixture's PR #20 is merged
    case("timeline story, from the REAL producer: a hand-off names its ref alone, never the ledger note (r1 P2)",
         story([l for l in _ch if l.startswith("declared on master: ")]), "Declared on master: backlog #11, PR #30.")
    _w1, _w2 = dict(_e, id="b-first"), dict(_e, id="a-second", goal="h", thread="side · PR #30 · again")
    case("backlog #505: the winner of a shared ref is the id that sorts first, whatever the FILE order — a re-add "
         "moves an entry to the end and must not move the thread (r2 Codex M1)",
         [[[t["key"] for t in g["threads"]] for g in ledger_threads(_gh, L)[0]] for L in ([_w1, _w2], [_w2, _w1])],
         [[[], ["side · PR #30"]]] * 2)
    _lp = derive(_g2, src(ledger=[dict(_e, thread="fix · backlog #12, PR #30 · x")]), "T1")
    _sib = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked\n'
                                '- side · backlog #12, PR #99 · sibling\n- fix · backlog #11, PR #30 · successor\n'
                                '## GOAL h\n> 2026-01-01 00:00 "q"\n- side · PR #21 · aside\n'), src(), "T2")
    _lone = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked\n'
                                 '- side · backlog #12, PR #99 · sibling\n'
                                 '## GOAL h\n> 2026-01-01 00:00 "q"\n- side · PR #21 · aside\n'), src(), "T2")
    case("backlog #505: the hand-off pairs on the ledger thread's PR — a sibling sharing only a backlog row is NOT its "
         "successor, and a ledger thread with no successor is still REMOVED (r2 Codex M2)",
         ([l.split(":")[0] for l in changes(_lp, _sib) if "declared on master" in l],
          [l.split(":")[0] for l in changes(_lp, _lone) if l.startswith(("declared", "removed"))]),
         (["declared on master"], ["removed [fix] backlog #12, PR #30"]))
    case("backlog #505: a ledger problem appearing and clearing is on the timeline, never 'no change' (r2 Codex L1)",
         [[l.split(":")[0] for l in changes(x, y) if "ledger problem" in l] for x, y in (
             (_pre, derive(_g2, src(ledger=[_e, dict(_e, id="w3", goal="nope")]), "T2")),
             (derive(_g2, src(ledger=[_e, dict(_e, id="w3", goal="nope")]), "T2"), _pre))],
         [["ledger problem, new"], ["ledger problem, cleared"]])
    case("backlog #505: a ledger thread associates by its STRUCTURED refs, never a number in its prose (r1 Codex M3)",
         _ledger_refs({"id": "x", "what": "w", "thread": "fix · PR #30 · depends on PR #777"}), {("PR", 30)})
    # ⛔ PR #558 r1 E: a ledger entry matches a thread by (KIND, number) — `PR #40` is not `backlog #40` — and a bare
    # `#N` in prose, or an id's `-N`, names nothing. Three DISTINCT entries in ONE case, each with one right home.
    _ge = parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #40, PR #20 · the row\n'
                        '- side · PR #40 · the pr\n- side · PR #41 · other\n')
    _gl = derive(_ge, src(ledger=[
        {"id": "ask-40", "what": "pr work, see #41", "goal": "g", "thread": "side · PR #40 · the pr"},
        {"id": "row-41", "what": "row work", "goal": "g", "thread": "fix · backlog #40 · x"},
        {"id": "z", "what": "CI on PR #41"}]), "T")
    case("⛔ PR #558 r1 E: ledger PR #N attaches to PR #N, never to backlog #N; bare #N and an id's -N name nothing",
         {t["key"]: t["detail"].split(" · in flight: ", 1)[1] if " · in flight: " in t["detail"] else None
          for t in _gl["goals"][0]["threads"]},
         {"fix · backlog #40, PR #20": "row work", "side · PR #40": "pr work, see #41", "side · PR #41": "CI on PR #41"})
    case("...an entry naming only a bare #N is IN FLIGHT UNDER NO GOAL, never hung on a thread with that number",
         derive(_ge, src(ledger=[{"id": "w-40", "what": "review of #40"}]), "T")["inflight_loose"],
         [{"id": "w-40", "what": "review of #40"}])
    case("backlog #505: parse_thread_line reads ONE line — a thread, a bad relation, bad refs, no separators",
         [(t and t["key"], bad and bad.split(" ")[0]) for t, bad in (
             parse_thread_line("- side · PR #7 · x"), parse_thread_line("- fixx · PR #7 · x"),
             parse_thread_line("- fix · issue #7 · x"), parse_thread_line("- just words"))],
         [("side · PR #7", None), (None, "relation"), (None, "refs"), (None, "a")])
    case("backlog #505: an entry with no goal or thread hangs nothing (the ledger's ordinary entries)",
         ledger_threads(_g2, [{"id": "x", "what": "PR #30"}]) == (_g2, []), True)
    case("a PR merged off master's log says so, with gh's SHA",
         one("- side · PR #23 · c\n", src())["detail"], "merged time unread · bbbb2222 — not on master's log")
    case("a PR gh did not list is NOT FOUND, never a guess",
         one("- side · PR #77 · c\n", src())["state"], "notfound")
    case("a backlog-only thread finds its merge by the subject tail",
         one("- fix · backlog #10 · f\n", src(open={}))["detail"], "merged time unread · aaaa111 via PR #20")
    case("a backlog-only thread finds an OPEN PR by its title",
         one("- fix · backlog #11 · f\n", src())["detail"], "PR #30 open · NO CHECKS")
    case("a backlog-only thread nothing names is NEXT",
         one("- fix · backlog #12 · f\n", src())["state"], "next")
    case("⛔ the subject tail must be the backlog row itself — #100 is not #10",
         one("- fix · backlog #10 · f\n",
             src(open={}, merged_rows=[("cccc", 5, "y (backlog #100) (#5)")]))["state"], "next")
    b = one("- fix · backlog #12 · f · waits on the owner\n", src())
    case("a declared wait on an unstarted thread is BLOCKED, and says it is declared",
         (b["state"], b["detail"].endswith("waits on the owner (declared)")), ("blocked", True))
    case("⛔ a declared wait never overrides a derived MERGED",
         one("- fix · PR #20 · f · waits on the owner\n", src())["state"], "merged")
    # PR #558 r1 E: the entry names its row by KIND (`backlog #12`); an id's `-12` alone names nothing
    led = [{"id": "build-12", "what": "subagent building backlog #12"}]
    fl = one("- fix · backlog #12 · f\n", src(ledger=led))
    case("a ledger entry naming the row makes an unstarted thread IN FLIGHT",
         (fl["state"], fl["detail"]), ("inflight", "no PR names it yet · in flight: subagent building backlog #12"))
    case("a ledger entry naming '#N' in its text attaches too",
         one("- side · PR #21 · a\n", src(ledger=[{"id": "x", "what": "CI on PR #21"}]))["detail"]
         .endswith("in flight: CI on PR #21"), True)
    case("...and an OPEN PR stays open — in flight is a note, not a downgrade",
         [(r["state"], "in flight: merging PR #21" in r["detail"]) for r in
          [one("- side · PR #21 · a\n", src(ledger=[{"id": "merge-21", "what": "merging PR #21"}]))]][0],
         ("open", True))   # PR #558 r1 E: the entry names PR #21 by kind, so it ATTACHES — and still downgrades nothing
    gh_down = src(errors={"gh": "gh pr list: exited 1: no network"}, open={}, all={})
    case("⛔ gh down: an unmerged PR leaf says CANNOT RUN, never a guessed state",
         one("- side · PR #21 · a\n", gh_down)["state"], "cannot")
    case("...while a PR master's own log shows merged is still MERGED (git answered)",
         one("- fix · PR #20 · a\n", gh_down)["state"], "merged")
    case("⛔ git down: a backlog-only leaf says CANNOT RUN",
         one("- fix · backlog #12 · f\n", src(errors={"merged": "git fetch exited 128"},
                                               merged_by_pr=None))["state"], "cannot")
    case("several PRs: merged only when ALL are, else the worst state",
         one("- fix · PR #20, PR #21 · f\n", src())["state"], "open")

    # ── backlog #484: a fate MARKER in a backlog row's Status cell beats the merge ──────────────────────
    def bl(*rows, testing=""):
        return ("# B\n\n## Items\n\n| # | Item | Touches | Size | Bundle | Status |\n|---|---|---|---|---|---|\n"
                + "".join(f"| {n} | {item} | x | S | (t) | {status} |\n" for n, item, status in rows)
                + (f"\n## Found during testing\n\n| # | Item | Status |\n|---|---|---|\n{testing}" if testing else ""))

    def fated_line(text):
        fates, problems = row_fates(text)
        snap = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10, PR #20 · f\n'),
                      src(fates=fates), "t")
        # backlog #497: a ✖ leaf is folded into `older`, so read every leaf, folded or not, without its fold tag.
        return [ln.split("└─ ")[-1].replace("[fix] ", "") for ln in every_line(tree_blocks(snap))
                if "backlog #10" in ln], problems

    def lead(status):
        """The rendered leaf for `backlog #10, PR #20` (PR #20 merged) whose row 10 has this Status cell."""
        return fated_line(bl((10, "**T**", status)))[0][0].split(" — ", 1)[1]

    # Row 484's REAL Status cell at this fold — the cell an any-word read printed ✖ withdrawn (r1 H1).
    ROW_484 = ("✅ **FIXED 2026-11-02, PR #480** — the leaf's state is DERIVED from the row's Status cell (no second "
               "declaration): `SUPERSEDED by backlog #M` prints ✖ superseded → backlog #M, `WITHDRAWN` prints ✖ "
               "withdrawn, both beating the merge; an unread backlog is CANNOT RUN. Backlog #405's leaf now prints ✖.")
    case("⛔ backlog #484: a LEADING SUPERSEDED marker whose PR merged prints ✖ and ITS forward pointer (two M)",
         [fated_line(bl((10, "**Early stop**", f"✅ **SUPERSEDED by backlog #{m} (2026-11-02)** — moved")))
          for m in (481, 37)],
         [([f"✖ backlog #10, PR #20 · f — superseded → backlog #{m} · merged time unread · aaaa111"], []) for m in (481, 37)])
    case("backlog #484: several forward pointers in the marker are all printed, each as a backlog ref",
         [lead(f"✅ **SUPERSEDED by backlog {p} (2026-11-02)**") for p in ("#328/#329", "#40, #41 and #42")],
         ["superseded → backlog #328, backlog #329 · merged time unread · aaaa111",
          "superseded → backlog #40, backlog #41, backlog #42 · merged time unread · aaaa111"])
    case("⛔ backlog #484: a leading marker WITHOUT a pointer prints a bare `superseded` — a ref outside it is not read",
         [lead(s) for s in ("✅ **SUPERSEDED 2026-11-02** — goal moved to backlog #481", "**SUPERSEDED**")],
         ["superseded · merged time unread · aaaa111"] * 2)
    case("⛔ backlog #484: a leading WITHDRAWN marker prints ✖ withdrawn (glyph, and `(was X)`)",
         [fated_line(bl((10, "**Dropped**", s), (11, "**Other**", "OPEN")))
          for s in ("✖ **WITHDRAWN 2026-11-02** — refuted", "✅ (was 🟠) **WITHDRAWN**")],
         [(["✖ backlog #10, PR #20 · f — withdrawn · merged time unread · aaaa111"], [])] * 2)
    case("⛔ backlog #484 (r1 H1): the word in the cell's PROSE is not a fate — row 484's own cell, and a negation",
         [lead(s) for s in (ROW_484, "🟠 **OPEN** — a **WITHDRAWN** row prints ✖; this one is NOT WITHDRAWN")],
         ["merged time unread · aaaa111"] * 2)
    case("⛔ backlog #484 (r1 M1): the audit's APPENDED dated marker is read (rows 124 and 189's shapes)",
         [lead(s) for s in ("pending — found 2026-09-15 by PR #295 r5 ✅ **SUPERSEDED 2026-10-26 (audit)** — gone",
                            "🟡 **OPEN — filed 2026-09-26.** Remains: x. ✅ **SUPERSEDED 2026-10-26 (audit)** — y")],
         ["superseded · merged time unread · aaaa111"] * 2)
    case("backlog #484: a marker after `Previously: `, or inside a code span, is history or quotation — not read",
         [lead(s) for s in ("🟠 **OPEN** — reopened. Previously: ✅ **SUPERSEDED by backlog #12**",
                            "✅ **FIXED** — a cell like `✅ **SUPERSEDED by backlog #12**` prints ✖")],
         ["merged time unread · aaaa111"] * 2)
    case("⛔ backlog #484 (r2 X1): the cell is CUT at its first `Previously:` — prose, spaces, several markers",
         [lead(s) for s in ("🟠 **OPEN** — reopened. Previously: pending — ✅ **SUPERSEDED by backlog #12**",
                            "🟠 **OPEN** — reopened. Previously:   ✅ **SUPERSEDED by backlog #12**",
                            "🟠 **OPEN**. Previously: ✖ **WITHDRAWN 2026-10-01** — then ✅ **SUPERSEDED by backlog "
                            "#12** — x",
                            "🟠 **OPEN**. Previously: ✅ **SUPERSEDED by backlog #12**. Previously: pending")],
         ["merged time unread · aaaa111"] * 4)
    case("backlog #484 (r2 X1) adjacent: a marker BEFORE `Previously:` is still read",
         lead("pending — ✅ **SUPERSEDED by backlog #12** — Previously: 🟠 **OPEN**"),
         "superseded → backlog #12 · merged time unread · aaaa111")
    case("⛔ backlog #484 (r2 X2): a code span of N backticks closes only on N — double, triple, an inner backtick",
         [lead(s) for s in ("✅ **FIXED** — use ``✅ **SUPERSEDED by backlog #12**`` as an example",
                            "✅ **FIXED** — use `` a`b ✅ **SUPERSEDED by backlog #12** `` as an example",
                            "✅ **FIXED** — ```✖ **WITHDRAWN**``` x")],
         ["merged time unread · aaaa111"] * 3)
    case("backlog #484 (r2 X2) adjacent: an UNCLOSED run is literal, and two spans do not swallow what is between",
         [lead(s) for s in ("✅ **FIXED** `` unclosed ✅ **SUPERSEDED by backlog #12** — and `x`",
                            "`a` ✅ **SUPERSEDED by backlog #12** `b`")],
         ["superseded → backlog #12 · merged time unread · aaaa111"] * 2)
    case("backlog #484 (r2): code spans go FIRST — a QUOTED `Previously:` does not cut the cell",
         lead("🟠 **OPEN** — the `Previously:` rule; ✅ **SUPERSEDED by backlog #12**"),
         "superseded → backlog #12 · merged time unread · aaaa111")
    case("⛔ backlog #484 (r2 note): a LATER bold span leading with REOPENED cancels the fate (row 327's shape)",
         [lead(s) for s in ("deferred — ✅ **SUPERSEDED by backlog #328/#329** (x). ⟳ **2026-10-25 — REOPENED BY "
                            "THE OWNER, and the question is now KEEP**",
                            "✖ **WITHDRAWN 2026-11-01** — x. **REOPENED 2026-11-02** — y")],
         ["merged time unread · aaaa111"] * 2)
    case("backlog #484 (r2 note) adjacent: a reopen BEFORE the marker, unbolded, or not LEADING its span cancels nothing",
         [lead(s) for s in ("⟳ **REOPENED 2026-10-25** — x ✅ **SUPERSEDED by backlog #12**",
                            "✅ **SUPERSEDED by backlog #12** REOPENED in prose, then **FIXED**",
                            "✅ **SUPERSEDED by backlog #12** — **owner: NOT REOPENED**",
                            "✅ **SUPERSEDED by backlog #11** **REOPENED** ✅ **SUPERSEDED by backlog #12**")],
         ["superseded → backlog #12 · merged time unread · aaaa111"] * 4)
    case("backlog #484: a marker led by an EMPHASIS glyph is not a fate (rows 48 and 213's other clauses)",
         [lead(s) for s in ("✅ **CLOSED 2026-08-21** ⟳⛔ **SUPERSEDED BY EVENTS 2026-08-24**",
                            "🔴 **OPEN** ⛔⟳ **SUPERSEDED AS THE REMEDY 2026-10-01**")],
         ["merged time unread · aaaa111"] * 2)
    case("backlog #484: a LOWERCASE `superseded by` is not a marker (row 327's shape), nor `WITHDRAWN` unbolded",
         [lead(s) for s in ("deferred 2026-10-20 by the owner — superseded by backlog #328/#329",
                            "✖ WITHDRAWN 2026-11-02 — refuted")],
         ["merged time unread · aaaa111"] * 2)
    case("backlog #484: a SUPERSEDED marker beats a WITHDRAWN one in the same cell, in either order",
         [lead(s) for s in ("✖ **WITHDRAWN 2026-11-01** — x ✅ **SUPERSEDED by backlog #12** — y",
                            "✅ **SUPERSEDED by backlog #12** — y ✖ **WITHDRAWN 2026-11-01** — x")],
         ["superseded → backlog #12 · merged time unread · aaaa111"] * 2)
    case("backlog #484 adjacent negative: a ✅ Status with no marker still prints ✅ merged",
         fated_line(bl((10, "**Fixed**", "✅ **FIXED 2026-11-02** — merged"))),
         (["✅ backlog #10, PR #20 · f — merged time unread · aaaa111"], []))
    case("⛔ backlog #484: SUPERSEDED / WITHDRAWN in the TITLE only is not the Status cell — still ✅",
         fated_line(bl((10, "✅ **SUPERSEDED by backlog #77 and WITHDRAWN, in the title only**", "✅ FIXED"))),
         (["✅ backlog #10, PR #20 · f — merged time unread · aaaa111"], []))
    case("⛔ backlog #484 (r1 L1): only the Items table's rows have fates — the second table's same number does not",
         [row_fates(bl((10, "**T**", "OPEN"), testing=f"| {n} | **t** | ✖ **WITHDRAWN** |\n"))[0] for n in (10, 12)],
         [{10: None}, {10: None}])

    # Several refs: each contributes its own state (the precedence comment in `derive_thread`).
    SUP, WD = ("superseded", "superseded → backlog #12"), ("withdrawn", "withdrawn")

    def multi(t, **f):
        d = one(t, src(fates={n: None for n in range(1, 100)} | {int(k[1:]): v for k, v in f.items()}))
        return d["state"], d["detail"]

    case("⛔ backlog #484 (r1 M3.1): two fated rows — superseded beats withdrawn in either order",
         [multi("- fix · backlog #10, backlog #11, PR #20 · f\n", r10=a, r11=b) for a, b in ((WD, SUP), (SUP, WD))],
         [("superseded", "withdrawn · superseded → backlog #12 · merged time unread · aaaa111"),
          ("superseded", "superseded → backlog #12 · withdrawn · merged time unread · aaaa111")])
    case("backlog #484 (r1 M3.2): two rows with the same fate name it once",
         [multi(f"- fix · backlog #10, backlog #11, PR #{p} · f\n", r10=WD, r11=WD) for p in (20, 22)],
         [("withdrawn", "withdrawn · merged time unread · aaaa111"), ("withdrawn", "withdrawn · PR #22 closed without merging · close time unread")])
    case("⛔ backlog #484 (r1 M2, Codex 4): a fated row beside a LIVE row keeps the merge ✅, either order",
         [multi("- fix · backlog #10, backlog #11, PR #20 · f\n", **{k: SUP}) for k in ("r10", "r11")],
         [("merged", "superseded → backlog #12 · merged time unread · aaaa111")] * 2)
    case("⛔ backlog #484 (r1 M2): with no PR, a live row's own state stands beside a fated one (⬜ next, ⏳ open)",
         [multi(f"- fix · backlog #10, backlog #{n} · f\n", r10=SUP) for n in (12, 11)],
         [("next", "superseded → backlog #12 · no PR names it yet"),
          ("open", "superseded → backlog #12 · PR #30 open · NO CHECKS")])
    case("...and a leaf whose rows are ALL fated, with no PR, is ✖ — not ⬜ next, and not the fated row's merge",
         [multi(f"- fix · backlog #{n} · f\n", **{f"r{n}": f}) for n, f in ((10, SUP), (11, WD))],
         [("superseded", "superseded → backlog #12 · no PR names it yet"), ("withdrawn", "withdrawn · no PR names it yet")])
    case("⛔ backlog #484 (r1 M3.4): an OPEN PR beats a fate — ⏳ stays, the fate is named",
         [multi("- fix · backlog #10, PR #21 · f\n", r10=f)[0] for f in (SUP, WD)], ["open", "open"])
    case("⛔ backlog #484 (r2 X3): a PR gh did not list beats a fate — ❓ notfound stays, the fate is named",
         [multi("- fix · backlog #10, PR #999 · f\n", r10=f) for f in (SUP, WD)],
         [("notfound", f"{f[1]} · PR #999 is not among the {ALL_LIMIT} newest PRs gh listed") for f in (SUP, WD)])
    case("⛔ backlog #484: an IN-FLIGHT entry beats a fate — ⏳ stays, the fate is named",
         [one("- fix · backlog #10 · f\n", src(fates={10: f}, ledger=[{"what": "x (backlog #10)"}]))["state"]
          for f in (SUP, WD)], ["inflight", "inflight"])
    case("⛔ backlog #484 (Codex 3, r1 L2): a ref to a row the backlog does not have is CANNOT RUN, never ✅",
         [multi(f"- fix · backlog #{n}, PR #20 · f\n") for n in (500, 777)],
         [("cannot", f"CANNOT RUN — backlog #{n} is not a row of the Items table in docs/backlog.md")
          for n in (500, 777)])
    case("⛔ backlog #484: an unreadable backlog makes a backlog-ref leaf CANNOT RUN, never ✅",
         (lambda d: (GLYPH[d["state"]], d["detail"]))(one("- fix · backlog #10, PR #20 · f\n", src(
             fates=None, fates_error="docs/backlog.md NOT READ (FileNotFoundError: gone)"))),
         ("⚠", "CANNOT RUN — docs/backlog.md NOT READ (FileNotFoundError: gone), so a superseded or "
               "withdrawn row cannot be ruled out"))
    case("...while a PR-only leaf needs no backlog row and is still merged",
         one("- fix · PR #20 · f\n", src(fates=None, fates_error="x"))["state"], "merged")
    case("backlog #484: a line the row parser refuses is a fates PROBLEM (that row may be the superseded one)",
         row_fates(BACKLOG_BAD), ({n: None for n in range(5, 12)},
                                  ["1 line(s) of docs/backlog.md the row parser could not read"]))

    case("derive_thread keeps the declared fields beside the derived ones",
         {k: v for k, v in derive_thread(goals[1]["threads"][0], src(merged_by_pr={})).items()
          if k in ("relation", "what", "state")},
         {"relation": "bookkeeping", "what": "filed rows", "state": "merged"})
    case("derive keeps exactly the goals it is given",
         [g["slug"] for g in derive(goals[1:], src(), "t")["goals"]], ["beta"])
    snap = derive(goals, src(ledger=[{"id": "loose-7", "what": "unrelated job"}]), "2026-10-28 04:00")
    case("an open PR no goal names is listed as UNDECLARED, never folded in",
         [u["pr"] for u in snap["undeclared"]], [99])
    case("an undeclared PR's title is cleaned of line separators",
         snap["undeclared"][0]["title"], "old thing")
    case("a ledger entry under no goal is listed on its own",
         snap["inflight_loose"], [{"id": "loose-7", "what": "unrelated job"}])
    case("the snapshot carries its time, master head and repo",
         (snap["at"], snap["head"], snap["repo"]), ("2026-10-28 04:00", "aaaa111", "o/r"))
    case("a complete read has no CANNOT RUN reasons", snap["cannot"], [])
    case("a failed source is named in the snapshot's CANNOT RUN list",
         derive(goals, gh_down, "t")["cannot"], ["gh: gh pr list: exited 1: no network"])

    # ── backlog #497: WHEN a thread merged, its recency bucket, and the folds ─────────────────────────────
    case("backlog #497: a stored minute prints as the owner's `mm-dd hh:mm`, anything else as TIME UNREAD",
         [merge_when(x) for x in ("2026-11-03 19:09", "2026-01-05 07:00", None, "", "11-03 19:09", "soon")],
         ["11-03 19:09", "01-05 07:00"] + [TIME_UNREAD] * 4)
    _utc = _dt.timezone.utc
    _kst = _dt.timezone(_dt.timedelta(hours=9))
    case("backlog #497: gh's mergedAt is converted to the given zone; no zone or no parse is None, never a guess",
         [local_minute("2026-11-03T10:09:00Z", _utc), local_minute("2026-11-03T10:09:00Z", _kst),
          local_minute("2026-11-03T23:30:00+00:00", _kst), local_minute("2026-11-03T10:09:00", _utc),
          local_minute("nope", _utc), local_minute(None, _utc)],
         ["2026-11-03 10:09", "2026-11-03 19:09", "2026-11-04 08:30", None, None, None])
    _ts = src(merged_at={"aaaa111": "2026-11-03 19:09", "dddd444": "2026-11-01 08:00"},
              merged_by_pr={20: "aaaa111", 21: "dddd444"}, all_merged_at={23: "2026-10-30 12:00"})
    case("⛔ backlog #497: a merged leaf carries its merge TIME before its SHA — PR, backlog-only, and off-log",
         [one("- fix · PR #20 · f\n", _ts)["detail"], one("- fix · backlog #10 · f\n", dict(_ts, open={}))["detail"],
          one("- side · PR #23 · c\n", _ts)["detail"]],
         ["merged 11-03 19:09 · aaaa111", "merged 11-03 19:09 · aaaa111 via PR #20",
          "merged 10-30 12:00 · bbbb2222 — not on master's log"])
    case("⛔ backlog #497: an unread merge minute says TIME UNREAD, never a blank or a guessed time",
         [one("- fix · PR #20 · f\n", src())["detail"], one("- side · PR #23 · c\n", src())["detail"]],
         ["merged time unread · aaaa111", "merged time unread · bbbb2222 — not on master's log"])
    case("backlog #497: a thread's merged_at is its LATEST merge; one unread minute makes it unread; unmerged is None",
         [one("- fix · PR #20, PR #21 · f\n", _ts)["merged_at"],
          one("- fix · PR #20, PR #21 · f\n", dict(_ts, merged_at={"aaaa111": "2026-11-03 19:09"}))["merged_at"],
          one("- fix · backlog #10 · f\n", dict(_ts, open={}))["merged_at"], one("- side · PR #21 · a\n", src())["merged_at"],
          one("- side · PR #23 · c\n", _ts)["merged_at"]],
         ["2026-11-03 19:09", None, "2026-11-03 19:09", None, "2026-10-30 12:00"])

    def bk(state, merged_at=None, parked=False):
        return bucket({"state": state, "merged_at": merged_at, "parked": parked}, "2026-11-05 19:09")
    case("⛔ backlog #497: a merge is RECENT up to exactly 48 h before the drawing, OLDER one minute past it",
         [bk("merged", "2026-11-03 19:09"), bk("merged", "2026-11-03 19:08"), bk("merged", "2026-11-05 19:00")],
         ["recent", "older", "recent"])
    case("⛔ backlog #497: a merge whose age cannot be read is RECENT — an unread time never folds a leaf away",
         [bk("merged"), bk("merged", "garbage"),
          bucket({"state": "merged", "merged_at": "2026-01-01 00:00"}, "t")], ["recent"] * 3)
    case("backlog #497: closed (logged without a close time), superseded and withdrawn are OLDER; next with no "
         "relation is LATER; blocked (declared wait) is QUEUED",
         [bk(s) for s in ("closed", "superseded", "withdrawn", "next", "blocked")],
         ["older", "older", "older", "later", "queued"])
    case("⛔ backlog #497: open, in flight, CANNOT RUN and NOT FOUND are all NOW — never folded",
         [bk(s) for s in ("open", "inflight", "cannot", "notfound")], ["now"] * 4)
    case("⛔ backlog #497: a parked leaf that has not landed is PARKED; one that merged or closed is aged instead",
         [bk(s, parked=True) for s in ("next", "blocked", "open", "inflight")]
         + [bk("merged", "2026-11-05 10:00", True), bk("merged", "2026-10-01 10:00", True), bk("closed", parked=True)],
         ["parked"] * 4 + ["recent", "older", "older"])
    case("backlog #497: a parked entry is one DECLARED owner-wait or one saying PARKED (a capital word, whole), "
         "or `parked` leading its text",
         [is_parked(e) for e in ({"kind": "owner-wait", "what": "x"}, {"kind": "routine", "what": "PR #3 PARKED"},
                                 {"what": "PARKED: later"}, {"kind": "routine", "what": "parked it"},
                                 {"kind": "owner-instruction", "what": "UNPARKEDNESS"}, {"what": "w"},
                                 {"kind": "routine", "what": "we parked it"})],
         [True, True, True, True, False, False, False])
    _pk = one("- fix · backlog #12 · f\n", src(ledger=[{"id": "park-12", "what": "backlog #12 PARKED till 11-10"}]))
    case("⛔ backlog #497: a parked entry does NOT make an unstarted leaf in flight — it is shown as parked",
         (_pk["state"], _pk["parked"], _pk["detail"]),
         ("next", True, "no PR names it yet · parked: backlog #12 PARKED till 11-10"))
    _pk2 = one("- fix · backlog #12 · f\n", src(ledger=[{"id": "park-12", "what": "backlog #12 w", "kind": "owner-wait"},
                                                      {"id": "build-12", "what": "building backlog #12"}]))
    case("backlog #497 adjacent: a routine entry beside the parked one still makes it in flight, and both are named",
         (_pk2["state"], _pk2["parked"], _pk2["detail"]),
         ("inflight", True, "no PR names it yet · in flight: building backlog #12 · parked: backlog #12 w"))
    _lp = derive(goals, src(ledger=[{"id": "park-77", "what": "PR #77 PARKED", "kind": "owner-wait"},
                                    {"id": "loose-7", "what": "unrelated job"}]), "2026-10-28 04:00")
    case("⛔ backlog #497: a parked entry naming NO thread is its own group, and not 'in flight under no goal'",
         (_lp["parked_loose"], _lp["inflight_loose"]),
         ([{"id": "park-77", "what": "PR #77 PARKED"}], [{"id": "loose-7", "what": "unrelated job"}]))
    _lpl = derive(goals, src(ledger=[{"id": "park-20", "what": "PR #20 PARKED"}]), "2026-10-28 04:00")
    case("⛔ backlog #497: a parked entry naming only LANDED threads joins that group, naming them — never hidden in a fold",
         (_lpl["parked_loose"], [t["parked"] for g in _lpl["goals"] for t in g["threads"]],
          "└─ park-20 · PR #20 PARKED · names only LANDED threads: fix · backlog #10, PR #20; bookkeeping · PR #20"
          in tree_lines(_lpl)),
         ([{"id": "park-20", "what": "PR #20 PARKED", "landed": ["fix · backlog #10, PR #20", "bookkeeping · PR #20"]}],
          [True, False, False, True], True))
    case("backlog #497 adjacent: a parked entry naming a LIVE thread stays on that thread, not in the group",
         derive(goals, src(ledger=[{"id": "park-21", "what": "PR #21 PARKED"}]), "t")["parked_loose"], [])
    _lpt = "\n".join(tree_lines(_lp))
    case("backlog #497: ...and that group is printed, after the in-flight one, never dropped",
         (_lpt.index("IN FLIGHT, UNDER NO GOAL") < _lpt.index("PARKED / QUEUED — NO GOAL"),
          "└─ park-77 · PR #77 PARKED" in _lpt), (True, True))

    # The bucketed tree, drawn at 2026-11-05 19:09: one goal with every bucket, one with only older/later.
    _bg = parse_threads('## GOAL mix\n> 2026-11-01 00:00 "q"\n'
                        "- fix · PR #21 · open one\n- fix · PR #20 · new merge\n- fix · PR #24 · old merge\n"
                        "- side · backlog #12 · unplanned\n- side · backlog #13 · waiting · waits on backlog #21\n"
                        "- side · backlog #14 · parked one\n- bookkeeping · PR #22 · shut\n"
                        '## GOAL done\n> 2026-11-02 00:00 "r"\n- fix · PR #25 · ancient\n- side · backlog #15 · someday\n')
    _bs = src(merged_by_pr={20: "aaaa111", 24: "eeee555", 25: "ffff666"},
              merged_at={"aaaa111": "2026-11-05 08:00", "eeee555": "2026-11-01 08:00", "ffff666": "2026-10-02 08:00"},
              ledger=[{"id": "park-14", "what": "backlog #14 waits for the owner", "kind": "owner-wait"}],
              all_closed_at={22: "2026-10-20 08:00"})
    _bsnap = derive(_bg, _bs, "2026-11-05 19:09")
    _bt = tree_lines(_bsnap)
    case("⛔ backlog #497: --print shows now, recent, queued and parked leaves, labelled, and folds the rest to counts",
         _bt[:11],
         ['GOAL 1 · mix (2026-11-01 00:00) "q"',
          "├─ fix",
          "│  ├─ ⏳ PR #21 · open one — PR #21 open · draft · clean · 1 pass",
          "│  └─ ✅ PR #20 · new merge — merged 11-05 08:00 · aaaa111",
          "├─ side",
          "│  ├─ ❌ queued · backlog #13 · waiting — no PR names it yet · waits on backlog #21 (declared)",
          "│  └─ ⬜ parked · backlog #14 · parked one — no PR names it yet · parked: backlog #14 waits for the owner",
          "├─ … 2 older merged or closed (collapsed on the page)",
          "└─ … 1 later (collapsed on the page)",
          "",
          'GOAL 2 · done (2026-11-02 00:00) "r"'])
    case("⛔ backlog #497: a goal with NOTHING current prints its header and its two counts only",
         _bt[11:13], ["├─ … 1 older merged (collapsed on the page)", "└─ … 1 later (collapsed on the page)"])
    case("⛔ backlog #497: the folded leaves are NOT in the text — the count stands for them",
         [any(w in ln for ln in _bt) for w in ("old merge", "shut", "unplanned", "ancient", "someday")], [False] * 5)
    case("⭐ backlog #497: the bucket moves with the DRAWING time, not the snapshot — the same tree drawn 3 days on",
         tree_lines(_bsnap, "2026-11-08 19:09")[:5],
         ['GOAL 1 · mix (2026-11-01 00:00) "q"', "├─ fix", "│  └─ ⏳ PR #21 · open one — PR #21 open · draft · clean · 1 pass",
          "├─ side", "│  ├─ ❌ queued · backlog #13 · waiting — no PR names it yet · waits on backlog #21 (declared)"])
    with tempfile.TemporaryDirectory() as d:
        _lp497 = pathlib.Path(d) / "log.jsonl"
        case("⭐ backlog #497: crossing the 48 h line with nothing else changed is NOT a new snapshot",
             [append_if_changed(_lp497, _bsnap), append_if_changed(_lp497, dict(_bsnap, at="2026-11-09 19:09"))],
             [True, False])

    import html.parser as _hp

    class _Folds(_hp.HTMLParser):
        """Every `<details>` (class, summary, OPEN or not) and every text run with the classes of the details
        it sits inside — what a reader sees without clicking is text inside no closed `<details>`."""
        def __init__(self):
            super().__init__()
            self.stack, self.folds, self.texts, self._sum = [], [], [], None

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "details":
                self.stack.append((a.get("class") or "", "open" in a))
                self.folds.append([a.get("class") or "", "open" in a, ""])
            elif tag == "summary":
                self._sum = self.folds[-1]

        def handle_endtag(self, tag):
            if tag == "details":
                self.stack.pop()
            elif tag == "summary":
                self._sum = None

        def handle_data(self, data):
            if self._sum is not None:
                self._sum[2] += data
            else:
                self.texts.append((data, [c for c, op in self.stack if not op]))

    _fp = _Folds()
    _tree_html = render_tree_html(_bsnap, at="2026-11-05 19:09")
    _fp.feed(_tree_html)
    case("⛔ backlog #497: the page folds `older` and `later` CLOSED with the count in each summary, and folds a goal "
         "with nothing current",
         [(c, op, sm.split(" — ")[0]) for c, op, sm in _fp.folds],
         [("fold older", False, "├─ older (2)"), ("fold later", False, "└─ later (1)"),
          ("fold goal", False, "GOAL 2 · done"), ("fold older", False, "├─ older (1)"),
          ("fold later", False, "└─ later (1)")])
    case("⛔ backlog #497 FAILS IF: a now, recent, queued or parked leaf is inside a closed fold",
         [w for w in ("open one", "new merge", "waiting", "parked one")
          if not any(w in t and not cl for t, cl in _fp.texts)], [])
    case("backlog #497: ...and every folded leaf IS on the page, inside its fold",
         [w for w in ("old merge", "shut", "unplanned", "ancient", "someday")
          if not any(w in t and cl for t, cl in _fp.texts)], [])
    case("⛔ backlog #497 (#363's rule): each page fold's count equals the --print count line it replaces",
         [int(re.search(r"\((\d+)\)", sm).group(1)) for c, _, sm in _fp.folds if c != "fold goal"],
         [int(re.search(r"… (\d+)", ln).group(1)) for ln in _bt if "(collapsed on the page)" in ln])
    case("backlog #497: merge_when and is_parked called directly on two distinct inputs each",
         (merge_when("2026-12-31 23:59"), merge_when(None),
          is_parked({"kind": "owner-wait", "what": "w"}), is_parked({"kind": "routine", "what": "w"})),
         ("12-31 23:59", TIME_UNREAD, True, False))
    case("⭐ backlog #497: --print's tree is tree_lines at the SAME drawing time, and another time draws another tree",
         (render_text(_bsnap, "2026-11-08 19:09").endswith("\n".join(tree_lines(_bsnap, "2026-11-08 19:09"))),
          render_text(_bsnap, "2026-11-08 19:09") == render_text(_bsnap)), (True, False))
    def folds_of(blocks):
        """(goal number, fold class) of every fold, at any depth, and `goal` for a goal folded whole."""
        out = []
        for bk in blocks:
            if bk[0] == "goal":
                out += ([(bk[1], "goal")] if bk[4] else []) + [(bk[1], c) for _, c in folds_of(bk[-1])]
            elif bk[0] == "fold":
                out.append((None, bk[1]))
        return out
    case("backlog #497: tree_blocks folds by the drawing time it is given, and a tree with no old leaf folds nothing",
         ([len(bk[-1]) for bk in tree_blocks(_bsnap, "2026-11-05 19:09") if bk[0] == "goal"],
          [len(bk[-1]) for bk in tree_blocks(_bsnap, "2026-11-08 19:09") if bk[0] == "goal"],
          folds_of(tree_blocks(snap)), folds_of(tree_blocks(_bsnap, "2026-11-08 19:09"))),
         ([3, 3], [3, 3], [], [(1, "older"), (1, "later"), (2, "goal"), (2, "older"), (2, "later")]))
    case("backlog #497: the folded tree emits thread ids only when asked, inside a fold too",
         ('id="t-pr-24"' in render_tree_html(_bsnap, ids=True, at="2026-11-08 19:09"),
          "id=" in render_tree_html(snap, at="2026-10-28 04:00")), (True, False))
    # ── the owner, 2026-11-04 01:14: each GOAL its own block, numbered, the slug in the heading colour ─────────
    case("⛔ goal blocks: --print numbers each goal by its first request's time, `GOAL n · slug`",
         [ln for ln in tree_lines(snap) if ln.startswith("GOAL ")],
         ['GOAL 1 · alpha-one (2026-10-26 09:51) "do the first thing"', 'GOAL 2 · beta (2026-10-28 03:41) "the second goal"'])
    _live = render_tree_html(_bsnap, ids=True, at="2026-11-05 19:09")
    case("⛔ goal blocks: every goal is its OWN section with its SLUG anchor, in declaration order (the live tree)",
         re.findall(r'<section class="goal"( id="[^"]*")?>', _live), [' id="goal-mix"', ' id="goal-done"'])
    case("goal blocks: a past tree's sections carry no anchor, so the page's ids stay unique",
         re.findall(r'<section class="goal"( id="[^"]*")?>', render_tree_html(_bsnap, at="2026-11-05 19:09")), ["", ""])
    case("⛔ goal blocks: the heading is `GOAL n ·` and the slug, the slug in its own span; the page and --print "
         "name the same goals with the same numbers",
         [f"{n} {sl}" for n, sl in re.findall(r'<span class="goal-n">GOAL (\d+) ·</span> <span class="goal-slug">([^<]+)</span>',
                                             _live)],
         [ln.split(" (", 1)[0].replace("GOAL ", "").replace(" · ", " ") for ln in _bt if ln.startswith("GOAL ")])
    case("⛔ goal blocks: a goal with nothing current keeps its NUMBERED heading as its closed fold's summary",
         re.search(r'<section class="goal" id="goal-done"><details class="fold goal"><summary><h3 class="goal-h">'
                   r'<span class="goal-n">GOAL 2 ·</span> <span class="goal-slug">done</span></h3>'
                   r'<span class="goal-counts"> — nothing current \(1 older, 1 later\)</span></summary>', _live) is not None,
         True)
    _quiet = dict(_bsnap, goals=[dict(g, threads=[t for t in g["threads"]
                                                  if bucket(t, "2026-12-30 00:00") in ("older", "later")])
                                 for g in _bsnap["goals"]])
    case("⭐ goal blocks: the number is STABLE — goal 2 is goal 2 whether goal 1 is open or folded whole",
         [re.findall(r'<section class="goal" id="goal-(\w+)">(<details)?[^>]*>?(?:<summary>)?<h3 class="goal-h">'
                     r'<span class="goal-n">GOAL (\d) ·', render_tree_html(sn, ids=True, at=a))
          for sn, a in ((_bsnap, "2026-11-05 19:09"), (_quiet, "2026-12-30 00:00"))],
         [[("mix", "", "1"), ("done", "<details", "2")], [("mix", "<details", "1"), ("done", "<details", "2")]])
    case("goal blocks: the heading colour is the common look's --accent (gold), declared in all four palettes",
         ("h3.goal-h{" in CSS and "color:var(--accent)" in CSS.split("h3.goal-h{", 1)[1].split("}", 1)[0],
          CSS.count("--accent:#8a5a2b"), CSS.count("--accent:#cb9a68")), (True, 2, 2))
    _np = render_page([_bsnap], "2026-11-05 19:09")

    # ── ANSWERS to questions asked from this page (owner 2026-11-11 06:18): a marker, the Q&A COLLAPSED ──────────
    _qa = [{"key": "goal:mix", "asked": "11-11 06:20", "q": "why <this>?", "a": "first para\n\nsecond para"},
           {"key": "pr-21", "asked": "11-11 06:21", "q": "is 21 open?", "a": "yes"},
           {"key": "pr-21", "asked": "11-11 06:22", "q": "still?", "a": "still"},
           {"key": "goal:gone-away", "asked": "10-01 09:00", "q": "orphan q", "a": "orphan a"},
           {"key": "pr-999", "asked": "10-02 09:00", "q": "orphan thread q", "a": "orphan thread a"}]
    _ap = render_page([_bsnap], "2026-11-05 19:09", answers=_qa)
    _det = re.findall(r"<details class=\"qa[^\"]*\"[^>]*>", _ap)
    case("⛔ answers: EVERY Q&A renders COLLAPSED — a <details> with no `open` attribute (the clutter remedy)",
         (len(_det), [d for d in _det if "open" in d]), (3, []))
    case("⛔ answers: a goal's answer is a small marker right under ITS heading, inside its own section",
         re.search(r'<section class="goal" id="goal-mix"><h3 class="goal-h">.*?</h3><details class="qa">'
                   r'<summary>💬 1 answer</summary>', _ap) is not None, True)
    case("⛔ answers: a thread's answers sit beside its key's FIRST occurrence on the live tree, counted",
         re.search(r'id="t-pr-21"[^>]*>PR #21</a><details class="qa"><summary>💬 2 answers</summary>', _ap)
         is not None, True)
    _tail = _ap[_ap.index("<h2>Timeline</h2>"):]
    case("⛔ answers: a key no longer on the tree lands in ONE collapsed 'Older questions' section at the BOTTOM",
         (_ap.count("qa-older"), "qa-older" in _tail, _tail.rstrip().endswith("</details>\n</main>"),
          "orphan q" in _tail and "orphan thread q" in _tail, "goal:gone-away" in _tail),
         (1, True, True, True, True))
    case("answers: a key that IS on the tree is not repeated under Older questions",
         _tail.split("qa-older", 1)[1].count("is 21 open?"), 0)
    case("answers: the Q and A are escaped, and a blank line in an answer is a new paragraph",
         ("why &lt;this&gt;?" in _ap, "<p>first para</p><p>second para</p>" in _ap), (True, True))
    case("answers: only the LIVE tree carries them — a timeline tree does not repeat the marker",
         _ap.count("💬 2 answers"), 1)
    case("answers: no answers renders no marker and no Older section", ("💬" in _np, "qa-older" in _np), (False, False))
    case("answers: a folded goal's marker sits OUTSIDE its fold, so it is visible while the goal is closed",
         re.search(r'<section class="goal" id="goal-done"><details class="fold goal">.*?</details>'
                   r'<details class="qa"><summary>💬 1 answer</summary>',
                   render_page([_bsnap], "2026-11-05 19:09", answers=[dict(_qa[0], key="goal:done")])) is not None,
         True)
    case("answers: qa_html is EMPTY for no answers and counts in the plural for several",
         (qa_html([]), re.findall(r"<summary>([^<]+)</summary>", qa_html(_qa[1:3])), qa_html(_qa[1:3]).count("qa-item")),
         ("", ["💬 2 answers"], 2))
    case("answers: a HOISTED marker names its own thread, escaped — two threads, two names (r1 C)",
         [re.findall(r"<summary>([^<]+)</summary>", qa_html(_qa[1:2], about=a)) for a in ("PR #7", "backlog #<9>")],
         [["💬 1 answer — PR #7 (folded above)"], ["💬 1 answer — backlog #&lt;9&gt; (folded above)"]])
    _rs = set()
    _rt = render_tree_html(_bsnap, ids=True, at="2026-11-05 19:09", qa={"pr-21": _qa[1:2]}, seen=_rs)
    case("⛔ answers: render_tree_html attaches only the answers it is GIVEN, and fills the caller's `seen` with every "
         "goal and thread key it drew — the set the Older section is computed from",
         (_rt.count("💬"), "pr-21" in _rs, "goal:mix" in _rs, "goal:done" in _rs, "pr-999" in _rs,
          "💬" in render_tree_html(_bsnap, ids=True, at="2026-11-05 19:09")),
         (1, True, True, True, False, False))
    with tempfile.TemporaryDirectory() as _atd:
        _ad = pathlib.Path(_atd)
        (_ad / "bad.json").write_text("{not json")
        (_ad / "hole.json").write_text(json.dumps({"answers": [_qa[1], {"key": "pr-1", "q": "no answer"}]}))
        (_ad / "ok.json").write_text(json.dumps({"answers": _qa[:2]}))
        _la = [load_answers(_ad / n) for n in ("missing.json", "bad.json", "hole.json", "ok.json")]
    case("⛔ answers file: missing = none yet; unreadable or an entry missing a field is REFUSED by name, never skipped",
         [(len(r), bool(e)) for r, e in _la] + [_la[2][1]],
         [(0, False), (0, True), (0, True), (2, False), "hole.json: entry [1] lack key, q or a"])
    case("⛔ answers file unreadable: the page SAYS so, beside the tree",
         '<p class="warn">⚠ Answers to questions asked here are NOT shown: bad.json is unreadable'
         in render_page([_bsnap], "2026-11-05 19:09", answers_error=_la[1][1]), True)
    case("answers file: the tracked one parses (an empty list until a question is answered)",
         load_answers(ROOT / ANSWERS_REL)[1], "")

    def _never_raises(f):
        try:
            return f()
        except Exception as e:   # the property under test: a malformed file is a REASON, never an exception
            return ("RAISED", type(e).__name__)

    with tempfile.TemporaryDirectory() as _mtd:
        _md = pathlib.Path(_mtd)
        for _n, _body in (("null.json", {"answers": None}), ("five.json", {"answers": 5}),
                          ("asked.json", {"answers": [dict(_qa[1], asked=7)]}), ("top.json", [1])):
            (_md / _n).write_text(json.dumps(_body))
        _lm = [_never_raises(lambda n=n: load_answers(_md / n)) for n in ("null.json", "five.json", "asked.json", "top.json")]
    case("⛔ r1 A: a malformed SHAPE is refused by name, never raised — `answers` null or a number, a non-text `asked`, "
         "a top-level list",
         [(r[0], r[1].split(" ", 1)[0]) if r[0] != "RAISED" else r for r in _lm],
         [([], "null.json:"), ([], "five.json:"), ([], "asked.json:"), ([], "top.json")])
    case("...and each says WHAT is wrong",
         [r[1].split(": ", 1)[-1] if r[0] != "RAISED" else r for r in _lm[:3]],
         ["`answers` is NoneType, not a list", "`answers` is int, not a list", "entry [0] carries a non-text asked"])

    # ⛔ r2: an unpaired surrogate (JSON `\ud800`) in ANY text field is refused by name, and the page is still WRITTEN.
    # r3 M1: EVERY checked field, each at its own entry (key@1, q@3, a@4, asked@5), so dropping any one field from the
    # check drops its index and turns this red.
    with tempfile.TemporaryDirectory() as _std:
        _sd = pathlib.Path(_std)
        (_sd / "s4.json").write_text(json.dumps({"answers": [
            _qa[1], dict(_qa[1], key="goal:gone\ud800"), _qa[2], dict(_qa[1], q="q\udc00"),
            dict(_qa[1], a="x\ud800"), dict(_qa[1], asked="\udfff")]}))
        (_sd / "sa.json").write_text(json.dumps({"answers": [dict(_qa[1], a="x\ud800")]}))
        (_sd / "locked.json").write_text(json.dumps({"answers": [_qa[1]]}))
        (_sd / "locked.json").chmod(0)
        _ls = [_never_raises(lambda n=n: load_answers(_sd / n)) for n in ("s4.json", "locked.json")]
        (_sd / "locked.json").chmod(0o600)
        _sp = _sd / "page.html"
        with contextlib.redirect_stderr(io.StringIO()) as _serr:   # r3 L4: the expected warning stays out of the run
            _sw = _never_raises(lambda: write_page(_sp, [_bsnap], "2026-11-05 19:09", answers_path=_sd / "sa.json",
                                                   composer=[sys.executable, "-c", "pass"]))
        _swrote = _sp.is_file() and "not valid UTF-8" in _sp.read_text(encoding="utf-8")
    case("⛔ r2/r3: text no UTF-8 writer can encode is refused by name — in `key`, `q`, `a` and `asked`, each at its own entry",
         _ls[0][1].split(": ", 1)[-1] if _ls[0][0] != "RAISED" else _ls[0],
         "entries [1, 3, 4, 5] carry text that is not valid UTF-8")
    case("⛔ r3 L3: an answers file it may not read is refused by name, never raised",
         (_ls[1][0], _ls[1][1].startswith("locked.json is unreadable (PermissionError")) if _ls[1][0] != "RAISED" else _ls[1],
         ([], True))
    case("...and the page is still written, saying so on stderr", (_sw[0] if isinstance(_sw, tuple) else None, _swrote,
         "not valid UTF-8" in _serr.getvalue()), (None, True, True))

    # ⛔ r1 B: EVERY escaped field, each with markup in it — removing any ONE escape turns its own term red.
    _xq = [{"key": "pr-21", "asked": "11-11 <i>x</i>", "q": "q", "a": "say <b>hi</b>\n\n<script>x</script>"},
           {"key": "goal:<gone>", "asked": "a", "q": "q2", "a": "a2"}]
    _xp = render_page([_bsnap], "2026-11-05 19:09", answers=_xq, answers_error="bad <u>file</u>")
    case("⛔ r1 B: the answer BODY is escaped, every paragraph", ("<p>say &lt;b&gt;hi&lt;/b&gt;</p>" in _xp,
         "<p>&lt;script&gt;x&lt;/script&gt;</p>" in _xp, "<b>hi</b>" in _xp, "<script>x</script>" in _xp),
         (True, True, False, False))
    case("⛔ r1 B: `asked` is escaped", ("<time>11-11 &lt;i&gt;x&lt;/i&gt;</time>" in _xp, "<i>x</i>" in _xp),
         (True, False))
    case("⛔ r1 B: an Older-questions KEY is escaped",
         ('<p class="qa-key">goal:&lt;gone&gt;</p>' in _xp, "goal:<gone>" in _xp), (True, False))
    case("⛔ r1 B: the answers-file ERROR line is escaped",
         ("NOT shown: bad &lt;u&gt;file&lt;/u&gt;" in _xp, "<u>file</u>" in _xp), (True, False))

    # ⛔ r1 C: a thread's marker is never hidden in a CLOSED fold — PR #24 sits in goal mix's `older` fold and PR #25
    # in the folded goal `done`; each marker is hoisted to just after its fold and names its thread.
    def _in_fold(page, needle):
        """For each `needle`, whether it sits inside a `<details class="fold …">` (closed until opened)."""
        out, stack = [], []
        for m in re.finditer(r'<details(?: class="([^"]*)")?[^>]*>|</details>|' + re.escape(needle), page):
            if m.group(0) == needle:
                out.append(any("fold" in c.split() for c in stack))
            elif m.group(0) == "</details>":
                stack.pop()
            else:
                stack.append(m.group(1) or "")
        return out

    _cf = render_page([_bsnap], "2026-11-05 19:09",
                      answers=[dict(_qa[1], key="pr-24"), dict(_qa[1], key="pr-25", q="in a folded goal")])
    case("⛔ r1 C: a thread's 💬 marker is OUTSIDE every closed fold, naming the thread it belongs to",
         (_in_fold(_cf, "<summary>💬 1 answer"), re.findall(r"<summary>(💬 1 answer[^<]*)</summary>", _cf),
          "qa-older" in _cf),
         ([False, False], ["💬 1 answer — PR #24 (folded above)", "💬 1 answer — PR #25 (folded above)"], False))
    case("r1 C adjacent: a thread NOT in a fold keeps its marker inline beside the key, unlabelled",
         (_in_fold(_ap, "<summary>💬 2 answers"), "💬 2 answers —" in _ap), ([False], False))
    case("backlog #497: the page's current tree is bucketed at its BUILD time, like --print at its run",
         ('<details class="fold older"><summary>├─ older (2)' in _np,
          '<details class="fold older"><summary>├─ older (3)' in render_page([_bsnap], "2026-11-08 19:09")),
         (True, True))
    # ── round 1 of backlog #497's review: NOTHING CURRENT IS EVER INSIDE A COLLAPSED GROUP ─────────────────
    def visible(snap_, at_, words):
        """The words that are NOT drawn outside every closed fold of the page (want: [])."""
        fp = _Folds()
        fp.feed(render_tree_html(snap_, ids=True, at=at_))
        shown_ = "".join(t for t, cl in fp.texts if not cl)     # a link splits a line into several text runs
        return [w for w in words if w not in shown_]
    # X1 (Codex's input): a routine ledger entry naming a thread that MERGED long ago, and an open PR it mentions.
    _x1g = parse_threads('## GOAL alpha\n> 2026-11-01 00:00 "ship"\n- fix · backlog #10, PR #20 · build\n')
    _x1 = derive(_x1g, src(merged_at={"aaaa111": "2026-10-01 12:00"},
                           ledger=[{"id": "build-99", "kind": "routine", "what": "building PR #99 after PR #20"}]),
                 "2026-11-04 12:00")
    _x1t = _x1["goals"][0]["threads"][0]
    case("⛔ review r1 X1: in-flight ledger work on a MERGED thread is NOW — in --print, and outside every page fold",
         (bucket(_x1t, "2026-11-04 12:00"), any("in flight: building PR #99 after PR #20" in ln
                                                for ln in tree_lines(_x1, "2026-11-04 12:00")),
          visible(_x1, "2026-11-04 12:00", ["in flight: building PR #99 after PR #20"])),
         ("now", True, []))
    case("⛔ review r1 X1: an open PR mentioned only in a ledger entry's text is still UNDECLARED, never hidden",
         [u["pr"] for u in _x1["undeclared"]], [21, 30, 99])
    # X1 (the Claude half's input): the same for a CLOSED thread and a backlog-only merged thread.
    _x1c = derive(parse_threads('## GOAL g\n> 2026-11-01 00:00 "q"\n- fix · PR #22 · shut\n'
                                "- fix · backlog #10 · old\n"),
                  src(merged_at={"aaaa111": "2026-10-20 12:00"},
                      ledger=[{"id": "re-22", "what": "reopening PR #22 as a new PR"},
                              {"id": "fu-10", "what": "follow-up fix for backlog #10 r2 fold"}]), "2026-11-04 12:00")
    case("⛔ review r1 X1: ...a closed or a backlog-only merged thread with in-flight work is NOW, drawn open",
         ([bucket(t, "2026-11-04 12:00") for t in _x1c["goals"][0]["threads"]],
          visible(_x1c, "2026-11-04 12:00", ["reopening PR #22 as a new PR", "follow-up fix for backlog #10 r2 fold"])),
         (["now", "now"], []))
    case("review r1 X1 adjacent: a backlog-only thread resolved to an open PR by its TITLE still represents that PR",
         [u["pr"] for u in derive(parse_threads('## GOAL g\n> 2026-11-01 00:00 "q"\n- fix · backlog #11 · w\n'),
                                  src(), "t")["undeclared"]], [21, 99])
    # X2 (Codex's input): GitHub's mergedAt wins over the commit date; a missing commit date never hides it.
    _x2 = src(merged_by_pr={20: "abc1234"}, merged_at={"abc1234": "2026-10-01 12:00"},
              all_merged_at={20: "2026-11-04 09:00"})
    _x2a, _x2b = one("- fix · backlog #10, PR #20 · build\n", _x2), one("- fix · backlog #10, PR #20 · build\n",
                                                                         dict(_x2, merged_at={}))
    case("⛔ review r1 X2: a merged leaf's time is GitHub's mergedAt, not the commit date, and stays RECENT",
         [(t["detail"], t["merged_at"], bucket(t, "2026-11-04 12:00")) for t in (_x2a, _x2b)],
         [("merged 11-04 09:00 · abc1234", "2026-11-04 09:00", "recent")] * 2)
    case("review r1 X2 adjacent: with no mergedAt, the commit date is the fallback (backlog-only path too)",
         [one("- fix · PR #20 · f\n", dict(_x2, all_merged_at={}))["detail"],
          one("- fix · backlog #10 · f\n", dict(_x2, open={}, all_merged_at={}, merged_rows=[
              ("abc1234", 20, "x (backlog #10) (#20)")]))["detail"],
          one("- fix · backlog #10 · f\n", dict(_x2, open={}, merged_rows=[
              ("abc1234", 20, "x (backlog #10) (#20)")]))["detail"]],
         ["merged 10-01 12:00 · abc1234", "merged 10-01 12:00 · abc1234 via PR #20",
          "merged 11-04 09:00 · abc1234 via PR #20"])
    # X3 (Codex's prepend and the Claude half's insert): a goal added later in TIME does not renumber the others.
    _x3a = '## GOAL alpha\n> 2026-11-01 00:00 "ship"\n- fix · backlog #10, PR #20 · build\n'
    _x3b = '## GOAL beta\n> 2026-11-02 00:00 "two"\n- side · PR #21 · a\n'
    _x3n = '## GOAL new\n> 2026-11-03 00:00 "new goal"\n'

    def heads(text):
        sn = derive(parse_threads(text), src(), "2026-11-04 12:00")
        return ([ln.split(" (", 1)[0] for ln in tree_lines(sn) if ln.startswith("GOAL ")],
                re.findall(r'<section class="goal" id="([^"]+)"', render_tree_html(sn, ids=True)))
    case("⛔ review r1 X3: goals are numbered by their FIRST request's time and anchored by SLUG — prepending or "
         "inserting a newer goal moves no number and no anchor",
         [heads(_x3a + _x3b), heads(_x3n + _x3a + _x3b), heads(_x3a + _x3n + _x3b)],
         [(["GOAL 1 · alpha", "GOAL 2 · beta"], ["goal-alpha", "goal-beta"]),
          (["GOAL 3 · new", "GOAL 1 · alpha", "GOAL 2 · beta"], ["goal-new", "goal-alpha", "goal-beta"]),
          (["GOAL 1 · alpha", "GOAL 3 · new", "GOAL 2 · beta"], ["goal-alpha", "goal-new", "goal-beta"])])
    case("review r1 X3 adjacent: goals with the SAME first time are numbered in file order",
         heads(_x3a + _x3b.replace("2026-11-02", "2026-11-01"))[0], ["GOAL 1 · alpha", "GOAL 2 · beta"])
    # C2 (the Claude half's input): an unstarted fix/blocker under a goal is planned — QUEUED; bookkeeping/side LATER.
    _c2 = derive(parse_threads('## GOAL dev-speed-first\n> 2026-11-02 09:05 "q"\n'
                               "- fix · backlog #81 · REPLACES backlog #40 for the same goal\n"
                               "- blocker · backlog #82 · stops the fix\n- bookkeeping · backlog #83 · rows\n"
                               "- side · backlog #84 · aside\n"), src(), "2026-11-04 12:00")
    case("⛔ review r1 C2: an unstarted fix or blocker is QUEUED (planned), drawn open and labelled; "
         "unstarted bookkeeping and side stay LATER",
         ([bucket(t, "2026-11-04 12:00") for t in _c2["goals"][0]["threads"]],
          visible(_c2, "2026-11-04 12:00", ["queued · backlog #81", "queued · backlog #82"])),
         (["queued", "queued", "later", "later"], []))
    case("⛔ review r1 C2: the `later` fold no longer claims 'nothing plans it' — it says what it holds",
         [ln for ln in tree_lines(_c2, "2026-11-04 12:00") if "later" in ln]
         + re.findall(r"later \(\d+\) — [^<]*", render_tree_html(_c2, at="2026-11-04 12:00")),
         ["└─ … 2 later (collapsed on the page)", "later (2) — not started, bookkeeping or an aside"])
    # C3 (the Claude half's input): `parked` in any case, as a word leading a clause; NOT PARKED does not park.
    case("⛔ review r1 C3: 'parked' is matched in any case where it LEADS a clause, PARKED in capitals anywhere, "
         "and a negated one parks nothing",
         [is_parked({"kind": "routine", "what": w}) for w in (
             "parked: backlog #60 until the owner walks the spec", "Parked — waits for the walkthrough",
             "PR #376 (marketplace-inventory spec) PARKED; needs owner walkthrough", "build done; parked till 11-10",
             "PR #21 is NOT PARKED any more", "not parked: building", "no longer parked; resumed",
             "the page shows merge times, parked/queued items per goal", "show parked and queued work")],
         [True, True, True, True, False, False, False, False, False])
    _c3 = one("- side · backlog #60 · a\n", src(ledger=[{"id": "p", "what": "parked: backlog #60 until the owner walks"}]))
    case("review r1 C3: ...so that entry labels its thread PARKED, not in flight",
         (_c3["state"], bucket(_c3, "2026-11-04 12:00")), ("next", "parked"))
    # C5 (the Claude half's measurement): the fold controls and goal counts use --ink-soft (AA in both themes).
    case("⛔ review r1 C5: fold summaries, goal counts and the goal quote's time are --ink-soft, never --ink-faint",
         [("color:var(--ink-soft)" in CSS.split(sel, 1)[1].split("}", 1)[0])
          for sel in ("details.fold summary{", ".goal-counts{", ".goal-q time{")], [True] * 3)
    # C6 (the Claude half's input): a PR closed within 48 h is RECENT, with its close time; an older one is OLDER.
    _c6 = src(all_closed_at={22: "2026-11-04 10:00"})
    _c6r, _c6o = one("- fix · PR #22 · shut\n", _c6), one("- fix · PR #22 · shut\n",
                                                           src(all_closed_at={22: "2026-10-01 10:00"}))
    case("⛔ review r1 C6: a PR closed minutes ago is RECENT, says when, and is drawn open; an old closure is OLDER",
         [(t["detail"], bucket(t, "2026-11-04 12:00")) for t in (_c6r, _c6o)],
         [("PR #22 closed 11-04 10:00 without merging", "recent"),
          ("PR #22 closed 10-01 10:00 without merging", "older")])
    case("review r1 C6 adjacent: an unread close time is RECENT (never folds); a snapshot logged before close "
         "times were read stays OLDER",
         [bucket(one("- fix · PR #22 · shut\n", src()), "2026-11-04 12:00"),
          bucket({"state": "closed", "merged_at": None}, "2026-11-04 12:00")], ["recent", "older"])
    # r2 X1 (Codex's input): a recent MERGE beside an old CLOSURE — the aggregate is `closed`, recency is not.
    def r2x1(merged, closed):
        s = src(all_merged_at={20: merged} if merged else {}, all_closed_at={22: closed})
        sn = derive(parse_threads('## GOAL alpha\n> 2026-11-01 00:00 "ship"\n- fix · PR #20, PR #22 · retry\n'),
                    s, "2026-11-04 12:00")
        t = sn["goals"][0]["threads"][0]
        return (t["state"], bucket(t, "2026-11-04 12:00"),
                [ln for ln in tree_lines(sn, "2026-11-04 12:00") if "older" in ln])
    case("⛔ review r2 X1: a thread is RECENT when ANY of its PRs merged or closed within the window — a merge 3 h "
         "ago is not folded because the thread also names a PR closed a month ago",
         r2x1("2026-11-04 09:00", "2026-10-01 12:00"), ("closed", "recent", []))
    case("review r2 X1 adjacent: every ref old -> still OLDER and folded; one ref's time unread -> RECENT",
         [r2x1("2026-10-02 09:00", "2026-10-01 12:00")[:2], r2x1(None, "2026-10-01 12:00")[:2]],
         [("closed", "older"), ("closed", "recent")])
    # ── the log: only changes are kept ───────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as d:
        lp = pathlib.Path(d) / "log.jsonl"
        later = dict(snap, at="2026-10-28 05:00", head="ffff999")
        flipped = derive(goals, src(merged_by_pr={20: "aaaa111", 21: "dddd444"}), "2026-10-28 06:00")
        appended = [append_if_changed(lp, snap), append_if_changed(lp, later),
                    append_if_changed(lp, flipped)]
        case("⭐ a snapshot equal but for its time and head is NOT logged — the log lists changes",
             appended, [True, False, True])
        case("a log is judged against ITSELF — the same snapshot starts a fresh log",
             append_if_changed(pathlib.Path(d) / "other.jsonl", later), True)
        case("the log reads back oldest first", [s["at"] for s in read_log(lp)],
             ["2026-10-28 04:00", "2026-10-28 06:00"])
        try:
            append_if_changed(lp, derive(goals, gh_down, "t"))
            refused = "LOGGED"
        except ValueError:
            refused = "refused"
        case("⛔ an incomplete snapshot is refused by the log itself, not only by its caller",
             refused, "refused")
        lp.write_text(lp.read_text() + "{not json\n")
        try:
            read_log(lp)
            bad = "read"
        except Malformed as exc:
            bad = "line 3" in str(exc)
        case("⛔ an unreadable log line is MALFORMED, naming the line", bad, True)

    ch = changes(snap, flipped)
    case("a state flip is reported as old → new, with the new detail",
         any(c.startswith("[side] PR #21: open → ✅ merged") for c in ch), True)
    case("an undeclared PR leaving is reported",
         "undeclared PR #99 is gone" in changes(snap, dict(snap, undeclared=[])), True)
    case("the first snapshot says so", changes(None, snap), ["first snapshot"])
    grown = dict(snap, goals=snap["goals"] + [{"slug": "gamma", "requests": [], "threads": []}])
    case("an added goal is reported", "goal added: gamma" in changes(snap, grown), True)
    case("a removed thread is reported",
         "removed [side] PR #21" in changes(snap, dict(snap, goals=[
             dict(snap["goals"][0], threads=[t for t in snap["goals"][0]["threads"]
                                             if t["relation"] != "side"]), snap["goals"][1]])), True)
    case("the ledger entry going away is reported",
         "no longer in flight: loose-7" in changes(snap, dict(snap, inflight_loose=[])), True)

    # ── NEEDS YOU ────────────────────────────────────────────────────────────────────────────
    case("an open row marked NEEDS-OWNER waits on the owner",
         needs_owner({"status": "audited: NEEDS-OWNER — pick one", "closed": False}), True)
    case("⛔ a marker followed by 'answered' does not", needs_owner(
        {"status": "NEEDS-OWNER — answered 2026-10-27", "closed": False}), False)
    case("⛔ only the LAST marker counts — an old answered one does not clear a new ask", needs_owner(
        {"status": "NEEDS-OWNER — answered · later: NEEDS-OWNER — a new question", "closed": False}), True)
    case("⛔ a closed row does not wait, marker or not",
         needs_owner({"status": "✅ NEEDS-OWNER — x", "closed": True}), False)
    case("a row without the marker does not wait", needs_owner({"status": "OPEN", "closed": False}),
         False)
    _d, _dp = needs_from_dashboard(DASH_FIXTURE)
    case("the dashboard source is gen-dashboard's unresolved(), with no problem on a clean store",
         ([n["ref"] for n in _d], _dp), (["2026-10-01/1"], []))
    _d2, _dp2 = needs_from_dashboard(DASH_BAD)
    case("⛔ X1: an entry the store cannot read is a PROBLEM naming its id; readable asks are kept",
         ([n["ref"] for n in _d2], _dp2),
         (["2026-10-01/1"], ["1 dashboard entry the store's grammar could not read (2026-10-04/1)"]))
    _b, _bp = needs_from_backlog(BACKLOG_FIXTURE)
    case("the backlog source lists open NEEDS-OWNER rows only, by its own parser",
         ([n["ref"] for n in _b], _bp), (["backlog #5", "backlog #9", "backlog #10"], []))
    case("⛔ X1: a line the row parser refuses is a PROBLEM, never an item",
         needs_from_backlog(BACKLOG_BAD)[1], ["1 line(s) of docs/backlog.md the row parser could not read"])
    case("a backlog need carries the row's title and the clause after the marker",
         _b[0]["text"], "Pick a name — waits on you")
    case("⭐ X4: NEEDS-OWNER-ACTION is an ACTION, not a decision, and its marker is not in the text",
         [(n["ref"], n["kind"], n["text"]) for n in _b if n["kind"] == "action"],
         [("backlog #9", "action", "Run it — run the falsifier")])
    case("⭐ C2: a row waiting on ANOTHER row that is decided is FLAGGED, and stays listed",
         [(n["ref"], n["flag"]) for n in _b],
         [("backlog #5", None), ("backlog #9", None),
          ("backlog #10", "may already be answered by backlog #11")])
    case("⛔ C2: no flag when the other row still waits on the owner itself",
         needs_from_backlog(BACKLOG_FIXTURE.replace(
             "DECIDED 2026-10-28 by the owner: A",
             "part 1 DECIDED; NEEDS-OWNER — part 2 still open"))[0][2]["flag"], None)
    case("⛔ C2: a `PR #N` in the tail is not a row, so it never flags",
         needs_from_backlog(BACKLOG_FIXTURE.replace("waits on backlog #11's call",
                                                    "half shipped in PR #11"))[0][2]["flag"], None)
    case("⛔ Y4: only an explicit `backlog #N` flags — never pr #N, PR  #N, issue #N or color #N",
         [needs_from_backlog(BACKLOG_FIXTURE.replace("waits on backlog #11's call", t))[0][2]["flag"]
          for t in ("half shipped in pr #11", "half shipped in PR  #11", "issue #11 describes precedent",
                    "color #11", "waits on Backlog  #11")],
         [None, None, None, None, "may already be answered by backlog #11"])
    case("⛔ C2: a closed other row flags too",
         needs_from_backlog(BACKLOG_FIXTURE.replace("| 11 | **Parent**", "| 11 | ✅ **Parent**").replace(
             "DECIDED 2026-10-28 by the owner: A", "✅ done"))[0][2]["flag"],
         "may already be answered by backlog #11")
    # ── backlog #496: a decision recorded in prose, with the marker left asking ──────────────────
    # The FAILS-IF corpus: the six rows NEEDS YOU listed on 2026-11-03, VERBATIM from origin/master
    # 11a70deb, each with its status head as it stood at the commit that wrote its marker (derived by
    # `git log -S`, independently of this code). backlog #306 and backlog #384 were already settled; the other four were not.
    _c = json.loads((SCRIPTS / "fixtures" / "needs-owner-2026-11-03.json").read_text(encoding="utf-8"))
    _ctext = "# B\n\n## Items\n\n" + "\n".join(_c["header"] + [v["line"] for v in _c["rows"].values()]) + "\n"

    def _flags(text):
        return {n["row"]: n["flag"] for n in needs_from_backlog(text)[0]}
    _cf = _flags(_ctext)
    case("⭐ backlog #496 FAILS-IF: on the 2026-11-03 corpus backlog #306 is flagged as settled; backlog #384 (a head "
         "rewritten, no decision word) is NOT — that class moved to the PR-time check, a separate backlog row",
         (bool(_cf[306]), bool(_cf[384])), (True, False))
    case("⛔ backlog #496 adjacent negatives: backlog #2, backlog #86, backlog #198, backlog #307 (each still open that day) are not",
         [_cf[n] for n in (2, 86, 198, 307)], [None, None, None, None])
    case("⛔ backlog #496: every corpus row stays LISTED — a flag, never a hide (C2)",
         sorted(_cf), [2, 86, 198, 306, 307, 384])
    case("backlog #496 clause 1: the flag names the word it found and the remedy",
         _cf[306], "may already be settled: its status says “DECIDED” after the NEEDS-OWNER marker — "
                   "if so, write `NEEDS-OWNER answered`")

    def _one(status):
        t = BACKLOG_FIXTURE.replace("NEEDS-OWNER — waits on you", status)
        return _flags(t)[5]
    case("backlog #496 clause 1: `answered by the owner` after the marker flags too",
         _one("NEEDS-OWNER — pick A or B ⟳ 2026-10-28: answered by the owner's card: A"),
         "may already be settled: its status says “answered by the owner” after the NEEDS-OWNER marker — "
         "if so, write `NEEDS-OWNER answered`")
    case("⛔ backlog #496 clause 1: a DECIDED BEFORE the last marker is an older question, never this one",
         _one("DECIDED 2026-10-20 by the owner: A ⟳ NEEDS-OWNER — a new question"), None)
    case("⛔ backlog #496 clause 1: a lower-case 'decided' is prose about a future call (backlog #384's own tail)",
         _one("NEEDS-OWNER — pick A ⟳ whether briefs stay is decided after backlog #392 is built"), None)
    # r1 Codex R4: a decision word NEGATED right before it is the question still open, not a record.
    case("⛔ backlog #496 clause 1: `not DECIDED` after the marker does not flag (r1 Codex R4)",
         _one("NEEDS-OWNER — not DECIDED; still choose A or B"), None)
    case("⛔ backlog #496 clause 1: `not yet answered by the owner` does not flag (r1 Codex R4)",
         _one("NEEDS-OWNER — not yet answered by the owner"), None)
    case("backlog #496 clause 1: a `not` FAR before the word does not negate it (adjacent to R4)",
         _one("NEEDS-OWNER — the owner was not sure, then DECIDED A"),
         "may already be settled: its status says “DECIDED” after the NEEDS-OWNER marker — "
         "if so, write `NEEDS-OWNER answered`")
    case("backlog #496 clause 1: a negated word does not hide a LATER un-negated one",
         _one("NEEDS-OWNER — not DECIDED on 10-20 ⟳ 10-28: answered by the owner: A"),
         "may already be settled: its status says “answered by the owner” after the NEEDS-OWNER marker — "
         "if so, write `NEEDS-OWNER answered`")
    # r1 Claude F6: clause 1 and a closed cross-reference both apply — the row's OWN words win.
    case("backlog #496: clause 1 wins over a cross-reference to a decided row (r1 Claude F6)",
         _one("NEEDS-OWNER — DECIDED by the owner, as backlog #11 recorded"),
         "may already be settled: its status says “DECIDED” after the NEEDS-OWNER marker — "
         "if so, write `NEEDS-OWNER answered`")


    case("the ledger source is session-state's WAITS-ON-OWNER predicate, marker stripped",
         [(n["ref"], n["kind"], n["text"]) for n in needs_from_ledger(
             [{"id": "a", "what": "WAITS-ON-OWNER: choose"}, {"id": "b", "what": "owner said hi"},
              {"id": "c", "what": "WAITS-ON-OWNER: ACTION: restart Docker"}])],
         [("a", "decision", "choose"), ("c", "action", "restart Docker")])
    case("⛔ a title is plain TEXT, not HTML — the page escapes it once, so it is never escaped twice",
         needs_from_backlog(BACKLOG_FIXTURE.replace("**Pick a name**", "**Pick O'Brien's name**"))[0][0]
         ["text"].startswith("Pick O'Brien's name"), True)
    case("...and the clause is the row's own, not a constant",
         needs_from_backlog(BACKLOG_FIXTURE.replace("waits on you", "pick X or Y"))[0][0]["text"],
         "Pick a name — pick X or Y")
    case("an empty dashboard store has no asks", needs_from_dashboard(""), ([], []))
    case("an empty ledger has no owner-waits", needs_from_ledger([]), [])
    # Y3: a count only from the explicit annotation.
    case("⭐ Y3: a count comes ONLY from `(answers-open: N)`; 'several answers' says several; else nothing",
         [multiplicity(t) for t in ("roles page (answers-open: 14)", "several answers open",
                                    "write each answer into its box", "pick A or B")],
         [14, "several", None, None])
    case("⛔ Y3: a number in a SENTENCE is never a count (Codex's three)",
         [multiplicity(t) for t in ("backlog #14 answers open question", "PR #14 questions open tomorrow",
                                    "Not 14 answers open any more; pick A or B")], [None, None, None])
    # Y1: identity is an explicit token, never a row number in prose.
    case("Y1: an identity is read only from `decision: backlog #N` / `action: backlog #N`",
         [identity(t) for t in ("decision: backlog #5 — pick", "action: backlog #9 — run it",
                                "about backlog #5", "decision: backlog #5 and decision: backlog #9")],
         [(5, "decision"), (9, "action"), None, None])
    case("...and an `Action: backlog #N` (capitalised) is not the token", identity("Action: backlog #5"), None)
    _tri = consolidate(_d + _b + needs_from_ledger(
        [{"id": "ask-1", "what": "WAITS-ON-OWNER: decision: backlog #5 — Choose A or B (answers-open: 3)"}])
        + needs_from_dashboard(DASH_FIXTURE.replace("Pick one for backlog #5.",
                                                    "Pick one (decision: backlog #5)."))[0])
    case("⭐ Y1: sources that DECLARE one decision become ONE item that keeps every source",
         [(n["ref"], [(a["source"], a["ref"]) for a in n["also"]]) for n in _tri],
         [("2026-10-01/1", []), ("backlog #5", [("ledger", "ask-1"), ("dashboard", "2026-10-01/1")]),
          ("backlog #9", []), ("backlog #10", [])])
    case("⭐ Y2: a merged source keeps its own text and count",
         [(a["text"], a.get("multi")) for a in _tri[1]["also"]],
         [("decision: backlog #5 — Choose A or B (answers-open: 3)", 3),
          ("Pick one (decision: backlog #5).", None)])
    _y1 = consolidate(_b + needs_from_ledger([
        {"id": "act", "what": "WAITS-ON-OWNER: ACTION: run the command for backlog #5"},
        {"id": "other", "what": "WAITS-ON-OWNER: decide an entirely different question about backlog #5"},
        {"id": "kind", "what": "WAITS-ON-OWNER: action: backlog #5 — run it"}]))
    case("⛔ Y1: a bare mention, or the right row with the WRONG KIND, never merges (Codex's two + kind)",
         [(n["ref"], n["kind"]) for n in _y1],
         [("backlog #5", "decision"), ("backlog #9", "action"), ("backlog #10", "decision"),
          ("act", "action"), ("other", "decision"), ("kind", "decision")])
    case("...and the row keeps no stray source", _y1[0]["also"], [])
    _kind = consolidate(_b + needs_from_ledger(
        [{"id": "act5", "what": "WAITS-ON-OWNER: ACTION: action: backlog #5 — run it"}]))
    case("⛔ Y1: an ACTION declaring `action: backlog #5` never merges into row 5's DECISION",
         ([n["ref"] for n in _kind], _kind[0]["also"]),
         (["backlog #5", "backlog #9", "backlog #10", "act5"], []))
    # Z1: the kind is the source's OWN marker; a disagreeing token is a conflict, never a merge.
    _z1 = consolidate(_b + needs_from_ledger(
        [{"id": "probe", "what": "WAITS-ON-OWNER: ACTION: decision: backlog #5 — run the command"}]))
    case("⭐ Z1: an ACTION declaring `decision: backlog #5` stays a separate ACTION, with the conflict shown",
         ([(n["ref"], n["kind"], n.get("conflict")) for n in _z1 if n["ref"] == "probe"], _z1[0]["also"],
          "⚠ declares decision: backlog #5 but is marked ACTION" in _item_line(_z1[-1])),
         ([("probe", "action", "declares decision: backlog #5 but is marked ACTION")], [], True))
    case("Z1: a dashboard ask declaring an ACTION is a decision with a conflict",
         needs_from_dashboard(DASH_FIXTURE.replace("Pick one for backlog #5.",
                                                   "Pick one (action: backlog #9)."))[0][0]["conflict"],
         "declares action: backlog #9 but is marked a decision")
    # Z2: identity AND count come from the whole entry — a dashboard body included — before shortening.
    _z2 = needs_from_dashboard("## 2026-10-01 [needs-you]\nPick a name.\n\n"
                               "decision: backlog #5 (answers-open: 14)\n")[0]
    case("⭐ Z2: a dashboard ask's identity and count are read from its BODY, the title kept for display",
         [(n["text"], n["identity"], n["multi"]) for n in _z2], [("Pick a name.", [5, "decision"], 14)])
    case("Z2: ...and the merged provenance keeps that count",
         [(a["ref"], a.get("multi")) for a in consolidate(_b + _z2)[0]["also"]], [("2026-10-01/1", 14)])
    case("Z2: a count past the display cut is still read",
         [(len(n["text"]) <= 200, n["multi"]) for n in needs_from_ledger(
             [{"id": "long", "what": "WAITS-ON-OWNER: " + "x" * 300 + " (answers-open: 7)"}])],
         [(True, 7)])
    _conf = consolidate([dict(_b[0], text="Pick a name (answers-open: 2)", multi=2)] + needs_from_ledger(
        [{"id": "ask-1", "what": "WAITS-ON-OWNER: decision: backlog #5 (answers-open: 3)"}]))
    case("⭐ Y2: CONFLICTING counts are both kept and flagged, never resolved",
         (counts_conflict(_conf[0]), _conf[0]["multi"], _conf[0]["also"][0]["multi"],
          "⚠ the sources state different counts" in _item_line(_conf[0])), (True, 2, 3, True))
    case("agreeing counts are not a conflict", counts_conflict(dict(_conf[0], multi=3)), False)
    # W2: a declared ZERO is a count — kept, shown and compared like any other.
    _z0 = consolidate(_b + needs_from_dashboard("## 2026-10-01 [needs-you]\nPick a name.\n\n"
                                                "decision: backlog #5 (answers-open: 0)\n")[0])
    # Decisions only, so these HTML reads depend on the count rule alone, not on the action list's heading.
    _z0html = needs_html({"needs": [n for n in _z0 if n["kind"] == "decision"], "needs_not_read": []})
    case("⭐ W2: a declared 0 survives in merged provenance and is SHOWN, in text and in HTML",
         (_z0[0]["also"][0]["multi"], "(stands for 0 open answers)" in _item_line(_z0[0]),
          "(stands for 0 open answers)" in _z0html), (0, True, True))
    case("⭐ W2: 0 against 2 IS a conflict",
         counts_conflict(dict(_z0[0], multi=2)), True)
    case("W2: an item's own declared 0 is shown, in text and in HTML",
         ("stands for 0 open answers" in _item_line(dict(_z0[0], multi=0, also=[])),
          "stands for 0 open answers</b>" in needs_html(
              {"needs": [dict(_z0[0], multi=0, also=[])], "needs_not_read": []})), (True, True))
    case("consolidating never changes the caller's items", [n["also"] for n in _b], [[], [], []])
    _ns = derive(goals, src(needs=[]), "t")
    case("⭐ an empty list read from ALL three sources says nothing waits on you",
         (needs_state(_ns), needs_lines(_ns)[0].startswith("NEEDS YOU — nothing waits on you")),
         ("none", True))
    _one = dict(_item("decision", "backlog", "backlog #5", "/backlog-table#i5", "t", (5, "decision")),
                row=5)
    _nd = derive(goals, src(needs=[_one]), "t")
    case("needs are reported in the timeline as new and as cleared",
         (changes(_ns, _nd)[0], changes(_nd, _ns)[0]),
         ("needs you, new: backlog #5 (backlog)", "needs you, cleared: backlog #5 (backlog)"))
    case("a list with items says how many", needs_lines(_nd)[:2],
         ["NEEDS YOU — 1 decision(s) only you can make, open now", "└─ [backlog] backlog #5 · t"])
    _mixed = derive(goals, src(needs=consolidate(_tri + [_item(
        "decision", "ledger", "roles", None, "the roles page; several answers open")])), "t")
    _ml = needs_lines(_mixed)
    case("⭐ X4: decisions and actions are two lists, each with its own count",
         [ln for ln in _ml if ln.startswith("NEEDS YOU")],
         ["NEEDS YOU — 4 decision(s) only you can make, open now (1 of them stand for several answers)",
          "NEEDS YOU — 1 action(s) only you can take"])
    case("Y3: the item standing for several answers says so, without a number",
         any(ln.endswith("roles · the roles page; several answers open · stands for several open answers")
             for ln in _ml), True)
    case("an item's other sources are printed with it, text and count included",
         any("backlog #5" in ln and "also recorded in ledger ask-1: decision: backlog #5 — Choose A or B "
             "(answers-open: 3) (stands for 3 open answers)" in ln for ln in _ml), True)
    _pg = render_page([_ns, _mixed], "t")
    case("owner 17:28: NOTHING waiting is said quietly — a muted line, never a bright NEEDS YOU heading",
         (needs_html(_ns).count('>Needs you — nothing</p>'), "<h2>" in needs_html(_ns),
          'title="NEEDS YOU — nothing waits on you (dashboard asks' in needs_html(_ns)), (1, False, True))
    case("⭐ the NEEDS YOU list is at the top, above the tree, and every source links",
         (_pg.index('<section class="needs') < _pg.index("<h2>Now</h2>"),
          '<a href="/backlog-table#i5">backlog #5</a>' in _pg,
          '<a href="/dashboard#2026-10-01-1">2026-10-01/1</a>' in _pg,
          "action(s) only you can take</h2>" in _pg), (True, True, True, True))
    case("⭐ Y7: the page says it REPLAYS a snapshot, when, and how to refresh it",
         ('This page replays the snapshot taken at <time class="replayed">t</time>' in _pg,
          "python3 scripts/goal-tree.py --snapshot --page" in _pg,
          _pg.index('class="replay"') < _pg.index('<section class="needs')), (True, True, True))
    case("Y7: a live NEEDS YOU read is named as live",
         "NEEDS YOU is read live at <time>t2</time>" in render_page([_nd], "t", dict(_ns, at="t2")), True)
    case("a live read's needs are shown over the newest snapshot's",
         "nothing waits on you" in render_page([_nd], "t", _ns), True)

    # ── PLANS NOT TICKED CLOSED: the work-lines job, absorbed (backlog #389) ─────────────────
    _wl = _sibling("gen-work-lines")
    _pf = [_wl.parse_plan("ship", "<!-- parent: - -->\n<!-- serving: ship the page -->\n- [x] a", "2026-10-20"),
           _wl.parse_plan("kid", "<!-- parent: ship -->\n- [x] a\n- [ ] b", "2026-10-22"),
           _wl.parse_plan("fin", "<!-- parent: - -->\n- [x] a", "2026-10-25"),
           _wl.parse_plan("bare", "- [ ] a\n- [ ] b\n- [ ] c", "2026-10-21"),
           _wl.parse_plan("nosteps", "# just a title", "2026-10-26")]
    _op = open_plans(_pf, _wl)
    case("⭐ #389: every plan in a line that still owes something is listed, with ITS progress and the "
         "LINE's objective; finished and step-less plans are not",
         [(p["plan"], p["ticked"], p["total"], p["line"], p["serving"], p["parent"]) for p in _op],
         [("kid", 1, 2, "ship", "ship the page", "ship"), ("bare", 0, 3, "bare", None, None)])
    case("#389: newest first, by the plan file's last touch",
         [p["touched"] for p in _op], ["2026-10-22", "2026-10-21"])
    case("#389: a link rebuilt from transcripts is marked reconstructed",
         open_plans([_wl.parse_plan("p", "<!-- parent: - -->\n- [ ] a", "t"),
                     _wl.parse_plan("q", "<!-- parent: p -->\n<!-- parent-source: transcript x -->\n- [ ] a",
                                    "t")], _wl) and {x["plan"]: x["reconstructed"] for x in open_plans(
             [_wl.parse_plan("p", "<!-- parent: - -->\n- [ ] a", "t"),
              _wl.parse_plan("q", "<!-- parent: p -->\n<!-- parent-source: transcript x -->\n- [ ] a", "t")],
             _wl)}, {"p": False, "q": True})
    case("#389: nothing owing is an empty list", open_plans(_pf[2:3], _wl), [])
    case("#389: a plan whose recorded parent no longer exists says so, instead of reading as a new line",
         [p["parent"] for p in open_plans([_wl.parse_plan("lost", "<!-- parent: gone -->\n- [ ] a", "t")], _wl)],
         ["gone (no longer exists)"])
    import types as _types
    _wl_up = _types.SimpleNamespace(build_forest=_wl.build_forest, line_state=_wl.line_state,
                                    plan_key=_wl.plan_key, label=lambda r: r["slug"].upper())
    case("#389: names are the plan READER's labels, never re-derived here",
         [(p["plan"], p["line"], p["parent"]) for p in open_plans(_pf, _wl_up)],
         [("KID", "SHIP", "SHIP"), ("BARE", "BARE", None)])
    _ps = derive(goals, dict(src(needs=[]), plans=_op, plan_notes=["a checkout could not be read"]), "t")
    _pt = tree_lines(_ps)
    case("⭐ #389: the tree draws the plans section, one line per plan, objective included",
         ([ln for ln in _pt if ln.startswith("PLANS NOT TICKED CLOSED")][:1] != [],
          any(ln.startswith("├─ kid · 1/2 · 2026-10-22 · branched from ship · line ship: \"ship the page\"")
              for ln in _pt),
          "⚠ plans: a checkout could not be read" in _pt), (True, True, True))
    _ps2 = dict(_ps, plans=[dict(_op[0], ticked=2), {**_op[1], "plan": "new-one", "id": "new-one"}])
    case("#389: the timeline reports a plan's progress, a new owing plan, and one no longer owing",
         sorted(c for c in changes(_ps, _ps2) if c.startswith("plan")),
         ["plan no longer owing: bare", "plan not ticked closed, new: new-one (0/3)",
          "plan progress: kid 1/2 → 2/2"])
    # ⟳ r1 X4 (Codex's collision): `kid` held in main AND a worktree, beside a literal `kid @ main.md` in
    # main. Two records display as `kid @ main`; ticking the LITERAL file must still read as progress.
    _c1 = {**_wl.parse_plan("kid", "- [ ] a\n- [ ] b", "2026-10-01"), "key": ("/m", "kid"), "where": "main"}
    _c2 = {**_wl.parse_plan("kid @ main", "- [ ] a\n- [ ] b", "2026-10-01"), "key": ("/m", "kid @ main")}
    _c3 = {**_wl.parse_plan("kid", "- [ ] a", "2026-10-01"), "key": ("/w", "kid"), "where": "wt"}
    _before = open_plans([_c1, _c2, _c3], _wl)
    # Ticking the main checkout's `kid` — the record a label-keyed dict overwrites with the literal
    # `kid @ main.md`, measured: keyed by label, this progress vanished from the timeline.
    _c1t = {**_wl.parse_plan("kid", "- [x] a\n- [ ] b", "2026-10-01"), "key": ("/m", "kid"), "where": "main"}
    _after = open_plans([_c1t, _c2, _c3], _wl)
    case("⭐ #389 r1 X4: two plans that DISPLAY alike stay two records, keyed by (checkout, slug)",
         (sorted(p["plan"] for p in _before), len({_plan_id(p) for p in _before})),
         (["kid @ main", "kid @ main", "kid @ wt"], 3))
    case("⭐ #389 r1 X4: ticking one of two alike-labelled plans IS progress in the timeline, not a wording change",
         [c for c in changes(dict(_ps, plans=_before), dict(_ps, plans=_after)) if c.startswith("plan")],
         ["plan progress: kid @ main 0/2 → 1/2"])
    case("⭐ #389: the page links the FROZEN work-lines archive",
         f'<a href="{WORK_LINES_ARCHIVE}">the work-lines archive</a>' in render_page([_ps], "t"), True)

    # ── rendering ────────────────────────────────────────────────────────────────────────────
    txt = "\n".join(tree_lines(snap))
    case("--print leads with the NEEDS YOU block, then the tree",
         [ln.split(" — ")[0] for ln in render_text(snap).splitlines()[:3]],
         ["NEEDS YOU", "", 'GOAL 1 · alpha-one (2026-10-26 09:51) "do the first thing"'])
    case("the tree's root is the goal's own words, quoted, with its time",
         txt.splitlines()[0], 'GOAL 1 · alpha-one (2026-10-26 09:51) "do the first thing"')
    case("each relation is a branch, and the last one closes with └─",
         [ln for ln in txt.splitlines()[:8] if ln.startswith(("├─", "└─"))], ["├─ fix", "└─ side"])
    case("a leaf carries its glyph, refs, what and derived detail",
         "│  ├─ ✅ backlog #10, PR #20 · the first fix — merged time unread · aaaa111" in txt, True)
    case("the undeclared section is drawn", "UNDECLARED — open PRs no goal names" in txt, True)
    case("a tree drawn from a later snapshot shows ITS states",
         any("✅ PR #21 · an aside — merged time unread · dddd444" in ln for ln in tree_lines(flipped)), True)
    case("a CANNOT RUN source is printed in the tree",
         "⚠ CANNOT RUN — gh: gh pr list" in render_text(derive(goals, gh_down, "t")), True)
    case("PR refs link to GitHub, backlog refs to the backlog page",
         [h for _, h in segments("PR #20 and backlog #10", "o/r") if h],
         ["https://github.com/o/r/pull/20", "/backlog-table#i10"])
    case("with no repo read, a PR ref is plain text, never a guessed URL",
         [h for _, h in segments("PR #20", None)], [None])
    case("text in the tree is escaped", "&lt;b&gt;" in _html_line("<b> PR #1", "o/r"), True)
    # ── backlog #470: the live tree emits `t-<kind>-<N>` ids, ONCE per key, and past trees emit none.
    _ids = set()
    _two = _html_line("PR #20 and backlog #10", "o/r", _ids) + _html_line("PR #20 again", "o/r", _ids)
    case("the live tree gives a key its id at its FIRST occurrence only",
         (_two.count('id="t-pr-20"'), _two.count('id="t-backlog-10"')), (1, 1))
    case("...and the id is on the link to that key",
         '<a id="t-pr-20" href="https://github.com/o/r/pull/20">PR #20</a>' in _two, True)
    case("a PR with no repo still carries its id, on plain text",
         _html_line("PR #20", None, set()), '<span id="t-pr-20">PR #20</span>')
    case("without an id set, no id is emitted (a timeline's past tree)",
         'id=' in _html_line("PR #20 and backlog #10", "o/r"), False)
    log2 = [snap, flipped]
    page = render_page(log2, "2026-10-28 07:00")
    case("the page's ids are unique: the live tree has them, the timeline's trees do not",
         (page.count('id="t-pr-20"'), len(re.findall(r'id="(t-[^"]+)"', page))
          == len(set(re.findall(r'id="(t-[^"]+)"', page)))), (1, True))
    case("the page states its build time and the newest snapshot's time",
         ("<time>2026-10-28 07:00</time>" in page,
          '<time class="newest">2026-10-28 06:00</time>' in page), (True, True))
    case("⭐ the CURRENT tree is the newest snapshot, drawn above the timeline",
         page.index("Now") < page.index("Timeline") and
         page.index("✅ <a") < page.index("Timeline"), True)
    case("the timeline is newest first",
         page.index("<time>2026-10-28 06:00</time>") < page.index("<time>2026-10-28 04:00</time>"),
         True)
    case("every snapshot expands to its full tree", page.count('<div class="tree">'), 3)
    case("a log of ONE snapshot renders it as current and as the first timeline entry",
         render_page([snap], "t").count('<span class="story">The first snapshot.</span>'), 1)
    # owner 2026-11-05 17:28: ONE sentence per entry, naming the work; the change lines muted beneath
    case("timeline story: each kind is named by its ref — landed, added, moved with its new state, removed, a goal",
         story(["goal added: product", "[fix] PR #511 · recap: open → ✅ merged — e5f6",
                "added [fix] backlog #517 · split: ⬜ next", "[fix] backlog #511 · x: next → ❌ blocked — the reset",
                "removed [side] PR #9"]),
         "Goal opened: product; landed PR #511; added backlog #517; moved backlog #511 → blocked; removed PR #9.")
    case("timeline story: a detail that SAYS '→ ✅ merged' is not a landing, and a detail-only change is not a move "
         "(r1 P2)", story(["[fix] PR #20 · w: open → ⏳ open — notes: x → ✅ merged — y",
                           "[fix] PR #21 · w: merged → ✅ merged — sha changed"]), "2 threads' details changed.")
    case("timeline story: a plan newly owed, one no longer owing and progress are three different words (r1 P2)",
         story(["plan not ticked closed, new: a (0/3)", "plan no longer owing: b", "plan progress: c 1/3 → 2/3"]),
         "A plan newly owing; a plan no longer owing; plan progress.")
    case("timeline story: past three refs it counts the rest, so one sentence stays one line",
         story([f"added [fix] PR #{n} · w: ⬜ next" for n in (1, 2, 3, 4, 5)]), "Added PR #1, PR #2, PR #3 and 2 more.")
    case("timeline story: the asks and the agenda are told by kind",
         story(["needs you, new: backlog #9 (backlog)", "needs you, new: PR #8 (dashboard)",
                "needs you, cleared: PR #7 (ledger)", "agenda recorded: set t, 2 step(s)"]),
         "2 new asks for you; an ask cleared; the agenda changed.")
    case("timeline story, from the REAL producer: a wording-only snapshot says so, never '1 change(s)' (r3 P2)",
         story(changes(_a0, dict(_a0, at="T9"))) if changes(_a0, dict(_a0, at="T9")) == [NO_READER_CHANGE] else "n/a",
         "No change a reader would see; only the wording moved.")
    # backlog #520: a tree that differs in its stored WORDING alone (the thread's text), not merely in `at`
    _w1 = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #10 · tracked, reworded\n'), src(), "T3")
    case("backlog #520: two snapshots whose stored trees differ only in a thread's wording tell 'no change a reader "
         "would see', through the real derive and changes()",
         (_a0 != dict(_w1, at=_a0["at"]), changes(_a0, _w1), story(changes(_a0, _w1))),
         (True, [NO_READER_CHANGE], "No change a reader would see; only the wording moved."))
    # a thread first seen ALREADY merged landed in that interval — "added" alone hid the landing (seen 11-05 18:55)
    case("timeline story: a thread added already merged is told as landed, not merely added",
         story(["added [fix] backlog #519: ✅ merged 11-05 18:50 · 5408912 via PR #514",
                "added [fix] backlog #520: ⬜ next"]), "Landed backlog #519; added backlog #520.")
    case("timeline story: a line of no known kind still yields a sentence — a count, never an empty summary",
         story(["something new"]), "1 change(s).")
    _tl = render_page([snap] * (TIMELINE_SHOWN + 2), "t")
    case("the timeline entry's summary is the story; its change lines sit muted inside, not in the summary",
         ('<span class="story">The first snapshot.</span></summary><ul class="lines"><li>first snapshot</li>' in _tl,
          "change(s): first snapshot" in _tl), (True, False))
    case("past the newest TIMELINE_SHOWN entries the rest fold into ONE older block, which counts them",
         (_tl.count('<details class="older">'), "2 older snapshot(s), back to" in _tl,
          _tl.split('class="older"')[0].count('<details class="snap">')), (1, True, TIMELINE_SHOWN))
    case("...and the older block closes after the oldest entry, so the page's tags balance",
         _tl.count("<details") == _tl.count("</details>"), True)
    case("a timeline no longer than TIMELINE_SHOWN has no older block",
         '"older"' in render_page([snap] * TIMELINE_SHOWN, "t"), False)
    case("a failed live read is announced above the tree, with its reason",
         "could NOT run, so it was not logged: gh: gh pr list" in
         render_page(log2, "t", derive(goals, gh_down, "2026-10-28 08:00")), True)
    def _wired(page):
        try:
            page_chrome.assert_wired(page, "goal-tree self-test")
            return True
        except SystemExit:
            return False

    # The tray is lifted from a TRACKED explainer, so the case does not depend on what ~/explainers holds.
    _bc = _sibling("brief-compose")
    tray_src = next((f for f in sorted((ROOT / "docs" / "explainers").glob("*.html"), reverse=True)
                     if _bc.TRAY_BEGIN in (t := f.read_text(encoding="utf-8", errors="ignore"))
                     and _bc.has_tray(t)), None)
    case("CANNOT RUN guard: a tracked explainer with a marked Ask tray exists to lift from",
         tray_src is not None, True)
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "p.html"
        why = write_page(out, log2, "2026-10-28 07:00", tray_source=tray_src and str(tray_src))
        built = out.read_text()
        (pathlib.Path(d) / "a.json").write_text(json.dumps({"answers": [
            {"key": "goal:long-gone", "asked": "10-01 09:00", "q": "where did it go?", "a": "kept"}]}))
        (pathlib.Path(d) / "b.json").write_text("{")
        write_page(pathlib.Path(d) / "pa.html", log2, "2026-10-28 07:00", tray_source=tray_src and str(tray_src),
                   answers_path=pathlib.Path(d) / "a.json")
        with contextlib.redirect_stderr(io.StringIO()) as _err:
            write_page(pathlib.Path(d) / "pb.html", log2, "2026-10-28 07:00", tray_source=tray_src and str(tray_src),
                       answers_path=pathlib.Path(d) / "b.json")
        _pa, _pb = ((pathlib.Path(d) / n).read_text() for n in ("pa.html", "pb.html"))
        case("⛔ write_page reads the answers file it is GIVEN: an orphan lands under Older questions on the written "
             "page; an unreadable one is said on the page AND on stderr",
             ("💬 Older questions (1)" in _pa, "where did it go?" in _pa,
              "Answers to questions asked here are NOT shown: b.json is unreadable" in _pb,
              "answers NOT shown — b.json is unreadable" in _err.getvalue()),
             (True, True, True, True))
        case("the written page is chrome-wired (theme palettes and the Refresh button)",
             (page_chrome.missing_palettes(built), 'data-page="goal-tree"' in built), ([], True))
        # ⭐ owner 2026-11-11: the goal-tree page had no Ask tray. It is LIFTED, so it posts where every tray does.
        case("⛔ the written page carries the Ask tray, lifted by brief-compose — and says so",
             (why, _bc.has_tray(built), built.count('id="tray"'), _bc.TRAY_BEGIN in built,
              "/questions" in built), ("", True, 1, True, True))
        case("...the lifted page is still ONE chrome bar, wired, with the goal tree's own Refresh",
              (built.count('id="chrome-theme"'), built.count('data-page="goal-tree"'),
              _wired(built), "<title>Goal tree</title>" in built,
              built.lower().startswith("<!doctype html>")), (1, 1, True, True, True))
        notray = pathlib.Path(d) / "plain.html"
        notray.write_text("<title>x</title><style>body{}</style><p>no tray here</p>", encoding="utf-8")
        out_no = pathlib.Path(d) / "no.html"
        why_no = write_page(out_no, log2, "2026-10-28 07:00", tray_source=str(notray))
        plain = out_no.read_text()
        case("⛔ a source with no tray: the page is STILL written, chrome-wired, without a tray, and the reason returned",
             (bool(why_no), "no Ask tray" in why_no, _bc.has_tray(plain), page_chrome.missing_palettes(plain),
              'data-page="goal-tree"' in plain, plain.lower().startswith("<!doctype html>")),
             (True, True, False, [], True, True))
        rep = page_report(out_no, "headline\nthe actionable line")
        case("⛔ --page says the tray is missing, with EVERY line of the reason",
             (rep[1].startswith("⚠  WITHOUT the Ask tray"), "   the actionable line" in rep,
              page_report(out, "") == [f"goal tree page -> {out}  (Ask tray lifted)"]), (True, True, True))
        # ⛔ r1 B: the tray is asked of the FILE — a compose that exits 0 and writes no tray is a reason, not success
        shim = pathlib.Path(d) / "compose-shim.py"
        shim.write_text("import sys, pathlib\na = sys.argv\n"
                        "pathlib.Path(a[a.index('--out') + 1]).write_text("
                        "pathlib.Path(a[a.index('--content') + 1]).read_text())\n", encoding="utf-8")
        out_shim = pathlib.Path(d) / "shim.html"
        why_shim = write_page(out_shim, log2, "2026-10-28 07:00", composer=[sys.executable, str(shim)])
        case("⛔ r1 B: brief-compose exiting 0 with NO tray on disk is reported, and the page is still written",
             (why_shim.startswith("brief-compose exited 0 but"), "carries no Ask tray" in why_shim,
              out_shim.read_text().lower().startswith("<!doctype html>")), (True, True, True))
        # ⛔ r1 A, end to end: a malformed answers file never stops the page being written
        (pathlib.Path(d) / "n.json").write_text(json.dumps({"answers": None}))
        out_n = pathlib.Path(d) / "n.html"
        with contextlib.redirect_stderr(io.StringIO()) as _errn:
            _wn = _never_raises(lambda: write_page(out_n, log2, "2026-10-28 07:00", tray_source=tray_src and str(tray_src),
                                                   answers_path=pathlib.Path(d) / "n.json"))
        case("⛔ r1 A: `answers: null` — the page is STILL written and says why, on the page and on stderr",
             (_wn, out_n.is_file() and "NOT shown: n.json: `answers` is NoneType" in out_n.read_text(),
              "n.json: `answers` is NoneType" in _errn.getvalue()), ("", True, True))
        out_down = pathlib.Path(d) / "sub" / "down.html"
        write_page(out_down, [snap], "2026-10-28 08:30", derive(goals, gh_down, "2026-10-28 08:30"),
                   tray_source=tray_src and str(tray_src))
        case("write_page creates its directory and carries the failed live read",
             ("could NOT run" in out_down.read_text(), "<time>2026-10-28 08:30</time>" in
              out_down.read_text()), (True, True))

    # ── collect, through a fake `run` (no git, no gh) ───────────────────────────────────────
    def fake(answers):
        calls = []

        def run(cmd, cwd, timeout):
            calls.append(cmd[:3])
            for prefix, ans in answers:
                if cmd[:len(prefix)] == prefix:
                    return ans
            return 1, "unexpected command"
        return run, calls

    with tempfile.TemporaryDirectory() as d:
        r = pathlib.Path(d)
        # The ledger lives in the MAIN checkout, which is NOT `root` here — as in a worktree run.
        (r / "main" / ".claude").mkdir(parents=True)
        (r / "main" / ".git").mkdir()
        (r / "main" / ".claude" / "inflight.jsonl").write_text(
            '{"id": "build-12", "what": "w"}\n{"id": "ask-1", "what": "WAITS-ON-OWNER: decision: backlog #5 — pick A or B"}\n')
        (r / "docs").mkdir()
        (r / DASHBOARD_REL).write_text(DASH_FIXTURE)
        (r / BACKLOG_REL).write_text(BACKLOG_FIXTURE)
        ok = [(["git", "fetch"], (0, "")),
              (["git", "log"], (0, "abc1234\t2026-11-03 19:09\tone (backlog #10) (#20)\nabc0000\t2026-11-02 10:00\tno pr here\n")),
              (["gh", "pr", "list", "--state", "open"], (0, '[{"number": 21, "title": "t"}]')),
              (["gh", "pr", "list", "--state", "all"], (0, '[{"number": 22, "state": "CLOSED"}]')),
              (["gh", "repo"], (0, '{"nameWithOwner": "o/r"}')),
              (["git", "rev-parse"], (0, str(r / "main" / ".git") + "\n"))]
        run_ok, _ = fake(ok)
        s = collect(r, run_ok)
        case("collect reads master's subjects into PR -> SHA, skipping subjects with no PR",
             (s["merged_by_pr"], s["head"]), ({20: "abc1234"}, "abc1234"))
        case("backlog #497: collect reads each master commit's LOCAL committer minute, keyed by SHA",
             s["merged_at"], {"abc1234": "2026-11-03 19:09", "abc0000": "2026-11-02 10:00"})
        run_c, calls_c = fake(ok)
        collect(r, lambda cmd, cwd, timeout: (calls_c.append(list(cmd)), run_c(cmd, cwd, timeout))[1])
        case("backlog #497: ...asking git for the committer date in the owner's LOCAL zone, minute precision",
             [c for c in calls_c if c[:2] == ["git", "log"]][0][-2:],
             [f"--date=format-local:{MINUTE_FMT}", "--format=%h%x09%cd%x09%s"])
        run_m, _ = fake([x if x[0][:4] != ["gh", "pr", "list", "--state"] or x[0][4] != "all" else
                         (x[0], (0, '[{"number": 23, "state": "MERGED", "mergedAt": "2026-11-03T10:09:00Z", '
                                    '"mergeCommit": {"oid": "bbbb2222cccc"}}, {"number": 22, "state": "CLOSED"}]'))
                         for x in ok])
        _sm = collect(r, run_m)
        case("backlog #497: collect reads gh's mergedAt for a PR off master's log, as a local minute",
             (_sm["all_merged_at"], _sm["all_merge_sha"]),
             ({23: local_minute("2026-11-03T10:09:00Z")}, {23: "bbbb2222"}))
        case("collect reads open PRs, all PR states, the repo and the MAIN checkout's ledger",
             (sorted(s["open"]), s["all"], s["repo"], [e["id"] for e in s["ledger"]], s["errors"]),
             ([21], {22: "CLOSED"}, "o/r", ["build-12", "ask-1"], {}))
        case("⭐ NEEDS YOU gathers all three sources and merges only the one that DECLARES its decision",
             [(n["ref"], n["href"], [a["ref"] for a in n["also"]]) for n in s["needs"]],
             [("2026-10-01/1", "/dashboard#2026-10-01-1", []),
              ("backlog #5", "/backlog-table#i5", ["ask-1"]),
              ("backlog #9", "/backlog-table#i9", []), ("backlog #10", "/backlog-table#i10", [])])
        (r / BACKLOG_REL).write_text(BACKLOG_FIXTURE)
        (r / "main" / ".claude" / "inflight.jsonl").write_text(
            '{"id": "build-12", "what": "w"}\n{"id":"pick","what":"WAITS-ON-OWNER: Choose A or B"\n')
        (r / DASHBOARD_REL).write_text("")
        (r / BACKLOG_REL).write_text("# B\n")
        s_trunc = collect(r, run_ok)
        snap_trunc = derive(goals, s_trunc, "t")
        case("⛔ X1: a truncated ledger line makes the ledger NOT READ — never 'nothing waits on you'",
             (s_trunc["errors"].get("ledger", "").endswith("NOT READ"), needs_state(snap_trunc),
              "nothing waits on you" in render_text(snap_trunc)), (True, "not-read", False))
        try:
            append_if_changed(r / "trunc.jsonl", snap_trunc)
            logged = "LOGGED"
        except ValueError:
            logged = "refused"
        case("⛔ X1: ...and that snapshot is not logged", logged, "refused")
        case("...while the readable ledger entries are still used",
             [e["id"] for e in s_trunc["ledger"]], ["build-12"])
        (r / BACKLOG_REL).write_text(BACKLOG_BAD)
        case("⛔ X1: a backlog line the parser refuses makes the backlog NOT READ",
             collect(r, run_ok)["errors"].get("backlog", "").endswith("NOT READ"), True)
        _s_bad = collect(r, run_ok)
        case("⛔ backlog #484: a partly unreadable backlog leaves no fates, so a backlog leaf is CANNOT RUN",
             (_s_bad["fates"], _s_bad["fates_error"], one("- fix · backlog #10, PR #20 · f\n", _s_bad)["state"]),
             (None, "1 line(s) of docs/backlog.md the row parser could not read", "cannot"))
        (r / BACKLOG_REL).write_text(BACKLOG_FIXTURE.replace("| OPEN |", "| ✖ **WITHDRAWN 2026-11-02** |"))
        case("backlog #484: collect reads each row's fate from the backlog it is given",
             collect(r, run_ok)["fates"], {n: (("withdrawn", "withdrawn") if n == 8 else None) for n in range(5, 12)})
        (r / BACKLOG_REL).unlink()
        _s_gone = collect(r, run_ok)
        case("⛔ backlog #484: a missing backlog is CANNOT RUN for its rows, and named in the errors",
             (_s_gone["fates"], _s_gone["fates_error"].startswith("docs/backlog.md NOT READ (FileNotFoundError"),
              _s_gone["errors"].get("backlog", "").startswith("docs/backlog.md NOT READ")), (None, True, True))
        (r / DASHBOARD_REL).write_text(DASH_BAD)
        case("⛔ X1: an unreadable dashboard entry makes the dashboard NOT READ",
             collect(r, run_ok)["errors"].get("dashboard", "").endswith("NOT READ"), True)
        (r / "main" / ".claude" / "inflight.jsonl").write_text(
            '{"id": "build-12", "what": "w"}\n{"id": "ask-1", "what": "WAITS-ON-OWNER: decision: backlog #5 — pick A or B"}\n')
        (r / DASHBOARD_REL).write_text(DASH_FIXTURE)
        (r / BACKLOG_REL).write_text(BACKLOG_FIXTURE)
        case("an owner-wait in the ledger is a need, not 'in flight under no goal'",
             [u["id"] for u in derive(goals, s, "t")["inflight_loose"]], ["build-12"])
        run_nogit, _ = fake(ok[:-1] + [(["git", "rev-parse"], (128, "not a git repository"))])
        s_nogit = collect(r, run_nogit)
        case("⛔ #389: no main checkout: the plans are NOT READ too",
             s_nogit["errors"].get("plans", "").startswith("the main checkout could not be named"), True)
        case("#389: a main checkout with no .claude/plans/ holds no plan — said as a note, not an error",
             (collect(r, run_ok)["plans"], "plans" in collect(r, run_ok)["errors"],
              any("no .claude/plans/" in n for n in collect(r, run_ok)["plan_notes"])), ([], False, True))
        (r / "main" / ".claude" / "plans").mkdir()
        _s_pl = collect(r, run_ok, read_plans=lambda d: (_pf, ["note from the reader"]))
        case("⭐ #389: collect reads the MAIN checkout's plans through the plan reader",
             ([p["plan"] for p in _s_pl["plans"]], _s_pl["plan_notes"]), (["kid", "bare"], ["note from the reader"]))
        def _boom_reader(d):
            raise ValueError("unreadable")
        case("⛔ #389: a plan reader that fails is NOT READ, never an empty list",
             collect(r, run_ok, read_plans=_boom_reader)["errors"].get("plans", "").endswith(
                 "NOT READ (ValueError: unreadable)"), True)
        (r / "main" / ".claude" / "plans").rmdir()
        case("⛔ no main checkout: the ledger is NOT READ — never read from the worktree instead",
             (s_nogit["errors"].get("ledger", "").startswith("git rev-parse"), s_nogit["ledger"]),
             (True, []))
        run_nofetch, calls = fake([(["git", "fetch"], (128, "fatal: unable to access"))] + ok[2:])
        s = collect(r / "main", run_nofetch)
        case("⛔ a failed fetch is a CANNOT RUN source, and the stale origin/master is NOT read",
             ("merged" in s["errors"], ["git", "log", "origin/master"] in calls), (True, False))
        (r / DASHBOARD_REL).rename(r / "docs" / "moved.md")
        s_nodash = collect(r, run_ok)
        snap_nodash = derive(goals, dict(s_nodash, needs=[]), "t")
        case("⛔ an unreadable source is NOT READ, and an empty list is then NOT an all-clear",
             (s_nodash["errors"].get("dashboard", "").startswith(f"{DASHBOARD_REL} NOT READ"),
              needs_state(snap_nodash), "nothing waits on you" in render_text(snap_nodash)),
             (True, "not-read", False))
        (r / "docs" / "moved.md").rename(r / DASHBOARD_REL)
        run_502, _ = fake(ok[:2] + [(["gh", "pr", "list", "--state", "open"], (1, "HTTP 502"))] + ok[3:])
        case("⛔ a failed gh is a CANNOT RUN source, never an empty PR list read as 'none open'",
             collect(r, run_502)["errors"].get("gh", "").startswith("gh pr list: exited 1"), True)
        run_junk, _ = fake(ok[:2] + [(["gh", "pr", "list", "--state", "open"], (0, "not json"))] + ok[3:])
        case("⛔ unparseable gh output is CANNOT RUN too", "gh" in collect(r, run_junk)["errors"], True)

        # ── main, end to end over the fixture world ─────────────────────────────────────────
        (r / THREADS_REL).write_text(good)
        out = r / "page.html"
        run, _ = fake(ok)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rcs = [main(["--snapshot", "--page", "--out", str(out)], root=r, run=run, now="2026-10-28 09:00"),
                   main(["--snapshot", "--page", "--print", "--out", str(out)], root=r, run=run,
                        now="2026-10-28 09:05")]
        said = buf.getvalue()
        case("main logs a first snapshot, then declines an unchanged one",
             (rcs, said.count("snapshot logged"), "unchanged since the newest snapshot" in said),
             ([0, 0], 1, True))
        case("--print prints the tree it just derived", 'GOAL 1 · alpha-one (2026-10-26 09:51)' in said, True)
        case("main wrote the page", out.is_file() and "<h1>Goal tree</h1>" in out.read_text(), True)

        # ── the agenda (backlog #499) ───────────────────────────────────────────────────────────
        # restored below: later cases count this log. ⛔ Read only if THERE — a mutant that moves the log must
        # reach the case that names it, not crash here first (the CI sweep caught exactly that)
        _log_p = r / "main" / LOG_REL
        _log_before = _log_p.read_text() if _log_p.is_file() else None
        AG = ("window: until the reset\nchange-if: the owner reprioritises\n## today\n"
              "- PR #20 · land the merged one\n- backlog #11 · the row an open PR works on\n- restart the server\n"
              "## after\n- backlog #12 · not started\n")
        ag = parse_agenda(AG)
        case("an agenda parses its window, change-if, groups, steps and refs",
             (ag["window"], ag["change_if"], [st["when"] for st in ag["steps"]], ag["steps"][1]["refs"],
              ag["steps"][2]["refs"]),
             ("until the reset", "the owner reprioritises", ["today"] * 3 + ["after"], [["backlog", 11]], []))

        def ag_bad(text):
            try:
                parse_agenda(text)
            except Malformed as exc:
                return str(exc)
            return None
        _bad = ag_bad("- a step before a group\n## g\nstray\n")
        case("⛔ a malformed agenda names EVERY problem: a step before a group, a stray line, no window",
             ("line 1: a step before any" in _bad, "line 3: an agenda line is" in _bad, "no `window:` line" in _bad),
             (True, True, True))
        case("⛔ a second `window:` line is refused, not silently overwritten",
             "a second `window:` line" in (ag_bad("window: a\nwindow: b\n## g\n- x\n") or ""), True)
        case("⛔ an agenda with no steps is refused, not recorded as an empty plan",
             "no steps" in (ag_bad("window: w\n## g\n") or ""), True)

        # the step's state IS the tree leaf's state for the same refs — two distinct worlds, one case
        _s1, _s2 = src(), src(merged_by_pr={}, merged_rows=[], all={})
        _same = []
        for _w in (_s1, _s2):
            _d = derive_agenda(dict(ag, at="t", ticked=[]), _w)["steps"]
            _same.append([st["state"] for st in _d[:2]]
                         == [derive_thread({"key": "k", "refs": st["refs"], "waits": None}, _w)["state"]
                             for st in ag["steps"][:2]])
        _d1 = derive_agenda(dict(ag, at="t", ticked=[]), _s1)["steps"]
        _d2 = derive_agenda(dict(ag, at="t", ticked=[]), _s2)["steps"]
        case("⭐ a step naming a row or PR is derived by the TREE's own derivation, in two distinct worlds",
             (_same, [st["state"] for st in _d1], _d2[0]["state"]),
             ([True, True], ["merged", "open", FREE, "next"], "notfound"))
        case("a free step is FREE until ticked by hand, then done — and says which",
             ([st["state"] for st in derive_agenda(dict(ag, at="t", ticked=[3]), _s1)["steps"]][2],
              "ticked by hand" in derive_agenda(dict(ag, at="t", ticked=[3]), _s1)["steps"][2]["detail"]),
             ("merged", True))
        # r1 Codex H1 — a declared `waits on` lends the step its ❌, in two distinct worlds
        _leaf = {"key": "k", "refs": [["backlog", 12]], "waits": "PR #20"}
        _wag = parse_agenda("window: w\n## g\n- backlog #12 · the waiting row\n- backlog #13 · undeclared\n")
        _par = []
        for _w in (src(), src(merged_by_pr={}, merged_rows=[], all={})):
            _st = derive_agenda(dict(_wag, at="t", id=1, ticked=[]), _w, [_leaf])["steps"]
            _par.append((_st[0]["state"], derive_thread(_leaf, _w)["state"], _st[1]["state"]))
        case("⭐ a step whose row the tree declares `waits on` reads ❌ blocked, as the leaf does (r1 Codex H1)",
             _par, [("blocked", "blocked", "next"), ("blocked", "blocked", "next")])
        # r2 Codex H1/H2 — the ref SET, and ANY declared wait, in either declaration order
        _t_go = {"key": "a", "refs": [["backlog", 1], ["backlog", 2]], "waits": None}
        _t_wait = {"key": "b", "refs": [["backlog", 2], ["backlog", 1]], "waits": "the owner"}
        _oag = parse_agenda("window: w\n## g\n- backlog #2, backlog #1 · reversed\n- backlog #1, backlog #2 · same order\n")
        _ord = [[st["state"] for st in derive_agenda(dict(_oag, at="t", id=1, ticked=[]), src(), ths)["steps"]]
                for ths in ([_t_go, _t_wait], [_t_wait, _t_go])]
        case("⭐ a step waits if ANY declared thread naming the same ref SET waits, in any ref or declaration order "
             "(r2 Codex H1, H2)", _ord, [["blocked", "blocked"], ["blocked", "blocked"]])
        _t_wait2 = {"key": "c", "refs": [["backlog", 1], ["backlog", 2]], "waits": "PR #20"}
        _both = derive_agenda(dict(_oag, at="t", id=1, ticked=[]), src(), [_t_wait, _t_go, _t_wait2])["steps"][0]["detail"]
        _rev = derive_agenda(dict(_oag, at="t", id=1, ticked=[]), src(), [_t_wait2, _t_go, _t_wait])["steps"][0]["detail"]
        case("the joined waits read the same in either declaration order (r3 Codex L4)", _rev == _both, True)
        case("...and EVERY distinct declared wait is said, not only the first (r2 Codex H1)",
             ("waits on PR #20; the owner (declared)" in _both, _both.count("the owner")), (True, 1))
        _txt = agenda_lines({"agenda": derive_agenda(dict(ag, at="2026-11-04 09:00", id=1, ticked=[3]), _s1)})
        # ⟳ backlog #509: a NOW line and a focus line now sit between `changes if` and the steps (+2 lines)
        case("agenda_lines groups by when, numbers the steps, and marks a free step ◇ until ticked",
             (_txt[0], _txt[1], _txt[4], _txt[7].strip()[:4], _txt[-1].strip()[:4], len(_txt)),
             ("AGENDA — the current plan, set 2026-11-04 09:00 · until the reset",
              "  changes if: the owner reprioritises", "  today", "3. ✅", "4. ⬜", 10))

        # ── backlog #509: each step's goal, a NOW line, the focus by goal, a stale flag (owner 2026-11-05) ──────
        def _th(key, state, refs, merged_at=None, parked=False):
            return {"key": key, "state": state, "refs": refs, "merged_at": merged_at, "parked": parked}
        # r1 Codex M1: alpha is declared FIRST but asked LATER, so the tree numbers it 2 — file order would say 1
        _g509 = [{"slug": "alpha", "requests": [{"when": "2026-11-04 08:00"}], "threads": [
                      _th("fix · backlog #11", "open", [["backlog", 11]]),
                      _th("fix · backlog #40", "merged", [["backlog", 40]], "2026-11-04 10:00"),
                      _th("fix · backlog #41", "merged", [["backlog", 41]], "2026-11-04 08:00")]},
                 {"slug": "beta", "requests": [{"when": "2026-11-03 08:00"}], "threads": [
                      _th("fix · backlog #12", "next", [["backlog", 12]]),
                      _th("fix · backlog #13", "merged", [["backlog", 13]], "2026-11-04 11:00"),
                      _th("fix · backlog #14", "inflight", [["backlog", 14]], parked=True),
                      _th("side · PR #42", "inflight", [["PR", 42]]),
                      _th("fix · backlog #11", "open", [["backlog", 11]]),
                      dict(_th("fix · backlog #15", "cannot", [["backlog", 15]]), inflight=True),
                      dict(_th("fix · backlog #17", "merged", [["backlog", 17]], "2026-11-04 08:30"), inflight=True),
                      # r2 Codex L1: EVERY finished state, not only merged
                      *[dict(_th(f"fix · backlog #{n}", st, [["backlog", n]]), inflight=True)
                        for n, st in ((18, "closed"), (19, "superseded"), (20, "withdrawn"))],
                      _th("fix · backlog #16", "cannot", [["backlog", 16]])]}]
        _a509 = {"id": 1, "at": "2026-11-04 09:00", "window": "w", "change_if": None, "steps": [
            {"n": 1, "when": "today", "text": "backlog #11 · a", "detail": "d", "state": "open", "refs": [["backlog", 11]]},
            {"n": 2, "when": "today", "text": "backlog #12 · b", "detail": "d", "state": "next", "refs": [["backlog", 12]]},
            {"n": 3, "when": "today", "text": "restart", "detail": "d", "state": FREE, "refs": []},
            {"n": 4, "when": "after", "text": "backlog #13 · c", "detail": "d", "state": "merged", "refs": [["backlog", 13]]},
            {"n": 5, "when": "after", "text": "backlog #99 · d", "detail": "d", "state": "next", "refs": [["backlog", 99]]}]}
        _sn509 = {"agenda": _a509, "goals": _g509, "undeclared": [{"pr": 77}], "at": "2026-11-05 08:15",
                  "inflight_loose": [{"id": "build-777", "what": "working on backlog #777"}]}
        case("⭐ #509: a step's goals are goal_agenda_steps read backwards — two goals on one step, one goal on two, none on a free or unclaimed step",
             step_goals(_sn509, _a509),
             {1: ["GOAL 1 · beta", "GOAL 2 · alpha"], 2: ["GOAL 1 · beta"], 4: ["GOAL 1 · beta"]})
        case("#509: step_goals over another snapshot — one goal, two steps — numbers that goal 1",
             step_goals({"goals": _g509[1:]}, dict(_a509, steps=_a509["steps"][:2])), {1: ["GOAL 1 · beta"], 2: ["GOAL 1 · beta"]})
        _ctx = dict(agenda_context(_sn509, _a509))
        case("⭐ #509: NOW names each thread in flight with its goal — open, inflight, or a ledger entry whose row reads CANNOT RUN; "
             "not parked, not next, not a CANNOT RUN thread nothing works on, not a MERGED one a stale ledger entry still flags — and the ledger work no goal claims (r1 Codex M2), and counts the undeclared PRs",
             _ctx["now"], "now: ⏳ PR #42 → GOAL 1 · beta · ⏳ backlog #11 → GOAL 1 · beta · ⏳ backlog #15 → GOAL 1 · beta"
                          " · ⏳ backlog #11 → GOAL 2 · alpha · ⏳ build-777 → no goal"
                          " · + 1 open PR(s) no goal declares (UNDECLARED, below)")
        case("#509: with nothing in flight NOW says so, and adds no undeclared count when there is none",
             dict(agenda_context({"agenda": _a509, "goals": [{"slug": "q", "requests": [{"when": "2026-11-01 08:00"}], "threads": []}]}, _a509))["now"],
             "now: nothing in flight")
        case("⭐ #509: focus groups the steps NOT done by goal, a step under each goal it serves; an unclaimed step is `no goal`; a free or done step is not listed",
             _ctx["focus"], "focus: GOAL 1 · beta (steps 1, 2) · GOAL 2 · alpha (step 1) · no goal (step 5)")
        case("⭐ #509 r1 Codex L1: the age line says how old the plan is beside the snapshot's own time; none when the "
             "snapshot is older, or either stamp is not a minute stamp",
             (_ctx.get("age"), "age" in dict(agenda_context(dict(_sn509, at="2026-11-04 08:00"), _a509)),
              "age" in dict(agenda_context(dict(_sn509, at="t"), _a509))),
             ("age: set 23 h 15 m before this snapshot (2026-11-05 08:15)", False, False))
        case("#509 r2 Codex L2: the age counts whole days — Jan 31 23:55 to Mar 1 00:05 is 672 h 10 m (28 days)",
             dict(agenda_context(dict(_sn509, at="2026-03-01 00:05"), dict(_a509, at="2026-01-31 23:55"))).get("age"),
             "age: set 672 h 10 m before this snapshot (2026-03-01 00:05)")
        case("⭐ #509: STALE names a thread merged AFTER the plan was set that no step names — not one merged before, not one a step names",
             _ctx.get("stale"), "⚠ STALE — merged after this plan was set, and named by no step: backlog #40 (merged 11-04 10:00). "
                                "Re-record the agenda.")
        case("#509: the same plan read at an earlier `at` is stale for BOTH merges; at a later one, for none",
             ("backlog #41" in dict(agenda_context(_sn509, dict(_a509, at="2026-11-04 07:00"))).get("stale", ""),
              "stale" in dict(agenda_context(_sn509, dict(_a509, at="2026-11-04 12:00")))), (True, False))
        def _no_crash(bad):
            try:
                return ("age" in dict(agenda_context(dict(_sn509, at="2026-12-31 23:59"), dict(_a509, at=bad))),
                        "<section" in agenda_html(dict(_sn509, at="2026-12-31 23:59", agenda=dict(_a509, at=bad))))
            except Exception as e:  # noqa: BLE001 — the case must FAIL by name, not take the suite down
                return f"CRASH {type(e).__name__}"
        case("#509 r3 Codex L1: an impossible date (Feb 30, 24:00) renders the page with no age line rather than crash",
             [_no_crash(_bad) for _bad in ("2026-02-30 09:00", "2026-01-31 24:00")], [(False, True), (False, True)])
        case("#509 r3 Codex L2: a merge in the SAME minute the plan was set is not stale; one a minute later is",
             ["stale" in dict(agenda_context(_sn509, dict(_a509, at=_eq))) for _eq in ("2026-11-04 10:00", "2026-11-04 09:59")],
             [False, True])
        case("#509: an agenda stamp that is not `YYYY-MM-DD HH:MM` flags nothing stale rather than compare text",
             "stale" in dict(agenda_context(_sn509, dict(_a509, at="(unknown)"))), False)
        _done = dict(_a509, at="2026-11-04 12:00", steps=[dict(st, state="merged") for st in _a509["steps"]])
        case("⭐ #509: a plan whose every step is done says so, and its focus line is gone",
             [k for k, _ in agenda_context(_sn509, _done)], ["now", "age", "stale"])
        _lines509 = agenda_lines(_sn509)
        case("⭐ #509: each step line ends with its goals; an unclaimed step says `no goal`; a free step says nothing",
             [ln.rsplit(" — d", 1)[-1] for ln in _lines509 if ln.startswith("    ")],
             [" → GOAL 1 · beta, GOAL 2 · alpha", " → GOAL 1 · beta", "", " → GOAL 1 · beta", " → no goal"])
        _h509 = agenda_html(dict(_sn509, repo="o/r"))
        case("⭐ #509: the page lays out what is in flight and the focus as lists above the steps, and STALE once in the warning colour",
             (_h509.count('<p class="warn">⚠ STALE'), _h509.count("<h3>Running now</h3>"), _h509.count("<h3>Focus"),
              _h509.index("Running now") < _h509.index('<pre class="tree">')), (1, 1, 1, True))
        _pre509 = _h509.split('<pre class="tree">', 1)[1].split("</pre>", 1)[0]
        case("⭐ owner 11-11 14:52: each `## <when>` group in All steps is a TITLE (its own span, in the accent), and "
             "no step line is one",
             (re.findall(r'<span class="ag-when">([^<]*)</span>', _pre509), _pre509.count('class="ag-when"')),
             (["today", "after"], 2))
        # PR #559 r1: a title by KIND, never by indentation; with a change-if too; escaped; and the style rule exists
        _ti = [agenda_html({"goals": [], "repo": "o/r", "agenda": dict(_a509, change_if=_ci, steps=[
            dict(_a509["steps"][0], when=_w), dict(_a509["steps"][3], when="after")])})
            for _ci, _w in ((None, " today"), ("x", "<b>t</b>"))]
        case("⭐ PR #559 r1: an indented or HTML-bearing group is still a title, escaped, with or without a change-if; the "
             "accent style rule for the title exists",
             ([re.findall(r'<span class="ag-when">(.*?)</span>', _h.split('<pre class="tree">', 1)[1].split("</pre>")[0])
               for _h in _ti],
              "section.agenda .ag-when{" in CSS and "color:var(--accent)}" in CSS.split("section.agenda .ag-when{", 1)[1]
              .split("\n", 2)[1]),
             ([[" today", "after"], ["&lt;b&gt;t&lt;/b&gt;", "after"]], True))
        case("⭐ owner 11-05 14:37: the agenda heading is a short title in the goals' accent style; the plan's time, its AGE "
             "and its window sit on a meta line beneath (r4 X1: the page's age line)",
             ('<h2 class="agenda-h">Agenda</h2>' in _h509,
              '<p class="meta">the current plan · set 2026-11-04 09:00 (23 h 15 m before this snapshot) · w</p>' in _h509,
              "AGENDA —" in _h509), (True, True, False))
        _d509 = agenda_digest(_sn509, _a509)
        case("⭐ owner 11-05 14:37: the recap counts each piece of work ONCE, its goals, and where the next steps lean — a "
             "step under two goals counted once",
             agenda_recap(_d509),
             "2 running and 3 owed across 2 goals; the plan's next steps lean on GOAL 1 · beta (2 of 4 left).")
        case("#509 recap: nothing in flight and no step left says both, in words",
             agenda_recap({"now": [], "focus": {}, "left": 0}), "Nothing is running or owed; no step of the plan is left.")
        case("⭐ r1 Codex M1: an open FREE step is still left — the recap never says none is left while one shows open",
             (agenda_recap(agenda_digest({"goals": []}, dict(_a509, steps=[_a509["steps"][2]]))),
              agenda_digest({"goals": []}, dict(_a509, steps=[dict(_a509["steps"][2], state="merged")]))["left"]),
             ("Nothing is running or owed; 1 step left, none on a goal's work.", 0))
        case("r1 Codex L1: a TIE keeps the first goal in step order, never the alphabetically larger one",
             agenda_recap({"now": [], "left": 2, "focus": {"GOAL 1 · a": [{"n": 1}], "GOAL 2 · b": [{"n": 2}]}}),
             "Nothing is running or owed; the plan's next steps lean on GOAL 1 · a (1 of 2 left).")
        case("⭐ r1 Codex M2: work under no goal keeps its purpose, cut to one line",
             [x["what"] for x in agenda_digest(dict(_sn509, inflight_loose=[{"id": "j", "what": "a\nb"},
                                                                          {"id": "k", "what": "x" * 200}]), _a509)["now"]
              if x["goal"] == "no goal"],
             ["a b", "x" * 139 + "…"])
        case("⭐ r2 Codex M2/M3: the page SHOWS the recap sentence and the undeclared-PR count",
             (f'<p class="recap">{html.escape(agenda_recap(_d509))}</p>' in _h509,
              '<li class="warn">1 of these PRs no goal declares (UNDECLARED, below)</li>' in _h509), (True, True))
        _hf = agenda_html({"goals": [], "repo": "o/r", "agenda": dict(_a509, steps=[_a509["steps"][2]])})
        case("⭐ r2 Codex M1: with only a FREE step open, Focus says no remaining step names a goal — never 'no step left'",
             ('no remaining step names a goal' in _hf, 'no step left' in _hf), (True, False))
        case("r2 Codex L2: the recap's words agree in number — one piece, one goal, one step; two free steps",
             (agenda_recap({"now": [{"label": "x", "goal": "GOAL 1 · a", "what": ""}], "left": 1,
                            "focus": {"GOAL 1 · a": [{"n": 1}]}}),
              agenda_recap({"now": [], "left": 2, "focus": {}})),
             ("0 running and 1 owed across 1 goal; the plan's next steps lean on GOAL 1 · a (1 of 1 left).",
              "Nothing is running or owed; 2 steps left, none on a goal's work."))
        case("r2 Codex L2: one item under two goals keeps the purpose a LATER entry gives when the first has none",
             agenda_now_items({"now": [{"label": "x", "goal": "GOAL 1 · a", "what": ""},
                                       {"label": "x", "goal": "GOAL 2 · b", "what": "why"}]}),
             [{"label": "x", "goals": ["GOAL 1 · a", "GOAL 2 · b"], "what": "why", "running": False, "waits": None}])
        case("r3 Codex L1: an item's purpose is never ERASED by a later entry for it that has none",
             agenda_now_items({"now": [{"label": "x", "goal": "GOAL 1 · a", "what": "why"},
                                       {"label": "x", "goal": "GOAL 2 · b", "what": ""}]})[0]["what"], "why")
        case("⭐ r3 Codex L2 (owner 11-05 14:37): the agenda heading is drawn in the goals' ACCENT colour, as they are",
             (re.search(r"h2\.agenda-h\{[^}]*color:var\(--accent\)", CSS) is not None,
              re.search(r"h3\.goal-h\{[^}]*color:var\(--accent\)", CSS) is not None), (True, True))
        case("r2 Codex L1: a reference in an in-flight purpose is a LINK, like everywhere else on the page",
             '— builds <a href="https://github.com/o/r/pull/9">PR #9</a></span>' in agenda_html(
                 dict(_sn509, repo="o/r", inflight_loose=[{"id": "j", "what": "builds PR #9"}])), True)
        _evil = "<b>&amp;</b>"
        _he = agenda_html({"repo": "o/r", "at": "2026-11-05 08:15",
                           "goals": [{"slug": _evil, "requests": [{"when": "2026-11-03 08:00"}], "threads": [
                               dict(_th("fix · PR #42", "inflight", [["PR", 42]]), what=_evil)]}],
                           "agenda": dict(_a509, window=_evil, change_if=_evil)})
        case("⭐ r1 Codex M3: every value the agenda block interpolates is ESCAPED — goal chip, purpose, window, change-if",
             (_he.count("&lt;b&gt;&amp;amp;&lt;/b&gt;"), "<b>&amp;</b>" in _he), (4, False))
        case("⭐ owner 11-05 14:37: each piece of work in flight is ONE line, with a chip for every goal it serves",
             ([(x["label"], x["goals"]) for x in agenda_now_items(_d509)],
              _h509.count('<span class="chip">GOAL 1 · beta</span><span class="chip">GOAL 2 · alpha</span> '
                          '<a href="/backlog-table#i11">backlog #11</a>')),
             ([("PR #42", ["GOAL 1 · beta"]), ("backlog #11", ["GOAL 1 · beta", "GOAL 2 · alpha"]),
               ("backlog #15", ["GOAL 1 · beta"]), ("build-777", ["no goal"])], 1))
        _gw = [dict(g, threads=[dict(t, what="why it exists") if t["key"] == "side · PR #42" else t for t in g["threads"]])
               for g in _g509]
        case("owner 11-05 14:37: an in-flight line says the work's PURPOSE, the thread's `what`",
             'PR #42</a> <span class="what">— why it exists</span>' in agenda_html(dict(_sn509, goals=_gw, repo="o/r")),
             True)
        # owner 11-05 15:45 (card A): RUNNING is an open PR with no declared wait; everything else is OWED, with its wait
        _rg = [{"slug": "ro", "requests": [{"when": "2026-11-04 08:00"}], "threads": [
                   _th("fix · PR #61", "open", [["PR", 61]]),
                   dict(_th("fix · PR #62", "open", [["PR", 62]]), waits="the owner"),
                   _th("fix · backlog #63", "inflight", [["backlog", 63]]),
                   dict(_th("fix · backlog #64", "inflight", [["backlog", 64]]), open_pr=65),
                   dict(_th("fix · backlog #66", "inflight", [["backlog", 66]]), waits="the weekly reset")]}]
        _rs = {"goals": _rg, "repo": "o/r", "at": "2026-11-05 16:00", "agenda": dict(_a509, steps=[]),
               "undeclared": [{"pr": 88, "title": "stray work"}]}
        _rd = agenda_digest(_rs, _rs["agenda"])
        case("⭐ owner 15:45: an open PR (or a row resolved to one) with no wait RUNS; a declared wait, or no PR, is OWED",
             [(x["label"], x["running"], x["waits"]) for x in _rd["now"]],
             [("PR #61", True, None), ("PR #62", False, "the owner"), ("backlog #63", False, None),
              ("backlog #64", True, None), ("backlog #66", False, "the weekly reset")])
        _rh = agenda_html(_rs)
        _run, _owe = (_rh.split("<h3>Running now</h3>", 1)[1].split("<h3>Owed", 1)[0],
                      _rh.split("<h3>Owed — not being worked</h3>", 1)[1].split("</div>", 1)[0])
        case("⭐ owner 15:45: the page lists running work and OWED work apart — each item in exactly one list",
             ([n for n in ("PR #61", "PR #62", "backlog #63", "backlog #64", "backlog #66", "PR #88")
               if n in _run],
              [n for n in ("PR #61", "PR #62", "backlog #63", "backlog #64", "backlog #66", "PR #88") if n in _owe]),
             (["PR #61", "backlog #64", "PR #88"], ["PR #62", "backlog #63", "backlog #66"]))
        case("⭐ owner 15:45: each owed item says what it WAITS for, and one with no declared wait says so, never a guess",
             ('<span class="waits">waits for: the owner</span>' in _owe,
              '<span class="waits">waits for: the weekly reset</span>' in _owe,
              _owe.count('<span class="waits">waits for: not recorded</span>'), "waits for" in _run), (True, True, 1, False))
        case("owner 15:45: an open PR no goal declares is listed under Running now BY ITS TITLE — never only counted",
             ("— stray work</span>" in _run, "1 of these PRs no goal declares" in _run), (True, True))
        case("owner 15:45: the page says a background job or agent is NOT visible to it, under Running now",
             "a background job or an agent is not visible to this page" in _run, True)
        case("owner 15:45: the recap counts running (an undeclared PR too) and owed, apart",
             agenda_recap(_rd).split(";")[0], "3 running and 3 owed across 1 goal")
        case("owner 15:45: with nothing at all, both lists say so",
             tuple(t in agenda_html(dict(_rs, goals=[], undeclared=[])) for t in ("<li>nothing running</li>", "<li>nothing owed</li>")),
             (True, True))
        case("owner 15:45: the text lines are unchanged — an undeclared PR is still only COUNTED in `now:`",
             [t for k, t in agenda_context(_rs, _rs["agenda"]) if k == "now"][0].endswith(
                 "+ 1 open PR(s) no goal declares (UNDECLARED, below)") and "PR #88" not in agenda_context(_rs, _rs["agenda"])[0][1],
             True)
        case("⭐ owner 15:45: one item under two goals with a wait declared under EITHER is owed, whichever comes first",
             [(x["running"], x["waits"]) for x in (
                 agenda_now_items({"now": [{"label": "x", "goal": "a", "what": "", "running": True, "waits": None},
                                           {"label": "x", "goal": "b", "what": "", "running": False, "waits": "y"}]})
                 + agenda_now_items({"now": [{"label": "x", "goal": "b", "what": "", "running": False, "waits": "y"},
                                             {"label": "x", "goal": "a", "what": "", "running": True, "waits": None}]}))],
             [(False, "y"), (False, "y")])
        case("owner 15:45: a declared wait's reference LINKS and is escaped",
             '<span class="waits">waits for: <a href="https://github.com/o/r/pull/9">PR #9</a> &lt;b&gt;</span>' in agenda_html(
                 dict(_rs, goals=[dict(_rg[0], threads=[dict(_th("fix · PR #62", "open", [["PR", 62]]), waits="PR #9 <b>")])],
                      undeclared=[])), True)
        # r1 Codex H1/M1: the two derived-state scenarios, through the REAL `derive` over parsed thread lines
        _rt = lambda body: parse_threads('## GOAL ga\n> 2026-11-01 08:00 "a"\n' + body)
        _rv = lambda goals, **kw: [(x["label"], x["running"], x["waits"]) for x in agenda_now_items(
            agenda_digest(dict(derive(goals, src(**kw), "t"), at="2026-11-05 16:00"), dict(_a509, steps=[])))]
        case("⭐ r1 Codex H1: a thread naming an OPEN PR runs even when its backlog row cannot be read",
             _rv(_rt("- fix · PR #30, backlog #11 · w\n"), fates=None,
                 ledger=[{"id": "j", "what": "building backlog #11", "on_done": "d", "at": "t"}]),
             [("PR #30, backlog #11", True, None)])
        # backlog #518 moved `resolved` before the precedence, so the case above now also reaches PR #30 through backlog #11's
        # TITLE: a named PR NO row resolves to is what still tests that the named ones are recorded (sweep shard 18, PR #516)
        case("⭐ r1 Codex H1 / backlog #518: a NAMED open PR that no row's title resolves to still runs, its row unread",
             _rv(_rt("- fix · PR #21, backlog #12 · w\n"), fates=None,
                 ledger=[{"id": "j", "what": "building backlog #12", "on_done": "d", "at": "t"}]),
             [("PR #21, backlog #12", True, None)])
        _two = ('## GOAL gb\n> 2026-11-01 09:00 "b"\n- fix · backlog #11 · via its row\n')
        case("⭐ r1 Codex M1: one open PR reached by two declarations (its number; a row whose title resolves to it) is ONE running item",
             _rv(_rt("- fix · PR #30 · named\n" + _two)), [("PR #30", True, None)])
        case("⭐ r1 Codex M1: …and a wait declared on EITHER declaration holds that one item as owed",
             _rv(_rt("- fix · PR #30 · named\n" + _two.replace("via its row", "via its row · waits on the owner"))),
             [("PR #30", False, "the owner")])
        case("⭐ r2 Codex H1: a thread naming an open PR, its row unread and NO ledger entry, is still listed as running",
             _rv(_rt("- fix · PR #30, backlog #11 · w\n"), fates=None), [("PR #30, backlog #11", True, None)])
        case("⭐ r2 Codex M1: a thread naming TWO open PRs is one item with a row resolved to its SECOND, and that row's wait holds it",
             _rv(_rt("- fix · PR #21, PR #30 · both\n" + _two.replace("via its row", "via its row · waits on the owner"))),
             [("PR #21, PR #30", False, "the owner")])
        case("⭐ r3 Codex M1: a thread whose TWO rows resolve to two open PRs owns both — the second is not stray running work",
             _rv(_rt("- fix · backlog #11, backlog #12 · two rows · waits on the owner\n"),
                 open={30: {"number": 30, "title": "a (backlog #11)"}, 31: {"number": 31, "title": "b (backlog #12)"}}),
             [("backlog #11, backlog #12", False, "the owner")])
        case("⭐ backlog #518: a MIXED thread — one row merged, another resolving to an open PR — owns that PR, and its wait holds it",
             _rv(_rt("- fix · backlog #10, backlog #11 · mixed · waits on the owner\n")), [("backlog #10, backlog #11", False, "the owner")])
        case("⭐ backlog #518: …and a named MERGED PR beside a row resolving to an open PR owns it too",
             _rv(_rt("- fix · PR #20, backlog #11 · mixed · waits on the owner\n")), [("PR #20, backlog #11", False, "the owner")])
        case("backlog #518: …so the mixed thread's open PR is not reported UNDECLARED",
             [u["pr"] for u in derive(_rt("- fix · PR #20, backlog #11 · mixed\n"), src(), "t")["undeclared"]], [21, 99])
        case("r3 Codex M1: …so neither resolved PR is reported UNDECLARED",
             [u["pr"] for u in derive(_rt("- fix · backlog #11, backlog #12 · two rows\n"), src(
                 open={30: {"number": 30, "title": "a (backlog #11)"}, 31: {"number": 31, "title": "b (backlog #12)"},
                       32: {"number": 32, "title": "other"}}), "t")["undeclared"]], [32])
        case("⭐ r3 Codex L1: joining two items keeps a wait from EITHER, and running from either when none waits",
             [(x["running"], x["waits"]) for x in agenda_now_items({"now": [
                 {"label": "a", "goal": "g1", "what": "", "running": True, "waits": None, "prs": [21]},
                 {"label": "b", "goal": "g2", "what": "", "running": False, "waits": "w", "prs": [30]},
                 {"label": "c", "goal": "g3", "what": "", "running": True, "waits": None, "prs": [21, 30]}]})
              + agenda_now_items({"now": [
                 {"label": "a", "goal": "g1", "what": "", "running": False, "waits": None, "prs": [21]},
                 {"label": "b", "goal": "g2", "what": "", "running": True, "waits": None, "prs": [30]},
                 {"label": "c", "goal": "g3", "what": "", "running": False, "waits": None, "prs": [21, 30]}]})],
             [(False, "w"), (True, None)])
        case("r2 Codex M1: an entry sharing a PR with TWO items joins them into one, in first-seen order",
             [(x["label"], x["goals"]) for x in agenda_now_items({"now": [
                 {"label": "a", "goal": "g1", "what": "", "running": True, "waits": None, "prs": [21]},
                 {"label": "b", "goal": "g2", "what": "", "running": True, "waits": None, "prs": [30]},
                 {"label": "c", "goal": "g3", "what": "", "running": True, "waits": None, "prs": [21, 30]}]})],
             [("a", ["g1", "g2", "g3"])])
        case("r2 Codex L1: an undeclared PR whose number is not an integer is not listed, and nothing crashes",
             [x["label"] for x in agenda_digest(dict(_rs, undeclared=[{"pr": "7", "title": "t"}, {"pr": 88, "title": "u"}]),
                                                _rs["agenda"])["stray"]], ["PR #88"])
        _fx = _h509.split("<h3>Focus", 1)[1].split("</div>", 1)[0]
        case("⭐ owner 11-05 14:37: the focus is the next steps under a chip per goal, in step order, one step per line",
             re.findall(r'<span class="chip">([^<]*)</span>|<b>(\d+)\.</b>', _fx),
             [("GOAL 1 · beta", ""), ("", "1"), ("", "2"), ("GOAL 2 · alpha", ""), ("", "1"), ("no goal", ""), ("", "5")])
        # r1 Codex L2: every heading and step reaches the page, with one context line or four, with or without change-if
        _kept = []
        for _snp in (dict(_sn509, repo="o/r"), {"agenda": dict(_a509, change_if="x"), "goals": [], "repo": "o/r"}):
            _hp = agenda_html(_snp)
            _pre = _hp.split('<pre class="tree">', 1)[1].split("</pre>", 1)[0]
            _kept.append([re.sub(r"<[^>]+>", "", ln).strip()[:2] for ln in _pre.split("\n")] == ["to", "1.", "2.", "3.", "af", "4.", "5."])
        case("⭐ #509 r1 Codex L2: the page keeps every when heading and every step, whatever lines sit above them",
             _kept, [True, True])
        case("no agenda derives to None, and the text output then shows no block",
             (derive_agenda(None, _s1), agenda_lines({"agenda": None}), "AGENDA" in render_text(derive([], _s1, "t"))),
             (None, [], False))

        # ── slice 2: the history, the goal tag, the page section, the timeline ──────────────────────────────
        _h_cur = [dict(ag, at="t1", id=1, ticked=[],
                       replaced={"at": "t2", "states": [{"n": 1, "state": "merged"}, {"n": 3, "state": FREE}]}),
                  dict(parse_agenda("window: w2\n## g\n- backlog #12 · x\n"), at="t2", id=2, ticked=[],
                       replaced={"at": "t3", "states": [{"n": 1, "state": "next"}]}),
                  dict(ag, at="t3", id=3, ticked=[], replaced=None)]
        _hist = agenda_history(_h_cur)
        case("agenda_history keeps every REPLACED agenda, newest first, the open one left out",
             ([h["id"] for h in _hist], agenda_history([dict(ag, at="t", id=1, ticked=[], replaced=None)])), ([2, 1], []))
        case("⛔ a history step keeps its FROZEN state; one the frozen list omits is `cannot`, never re-derived",
             [st["state"] for st in _hist[1]["steps"]] if len(_hist) > 1 else _hist,
             ["merged", "cannot", FREE, "cannot"])
        case("history_line says when each was set and replaced, and how much was done by then",
             [history_line(h) for h in _hist],
             ["agenda #2 · set t2 · replaced t3 · 0/1 done by then · w2",
              "agenda #1 · set t1 · replaced t2 · 1/4 done by then · until the reset"])
        _cur_ag = derive_agenda(dict(ag, at="t3", id=3, ticked=[]), _s1)
        _lh = agenda_lines({"agenda": _cur_ag, "agenda_history": _hist})
        case("--print lists the earlier agendas under the current one, newest first, one line each",
             _lh[-3:], ["  earlier agendas (2), newest first — collapsed on the page",
                        "    " + history_line(_hist[0]), "    " + history_line(_hist[-1])])
        def _gas(g, a):
            try:
                return goal_agenda_steps(g, a)
            except (KeyError, TypeError) as exc:     # a value, so a mutant reaches this case rather than crashing
                return type(exc).__name__
        case("a goal is tagged with the steps naming a ref its threads name — never a free step, never a bad agenda",
             (goal_agenda_steps({"threads": [{"refs": [["backlog", 11]]}, {"refs": [["PR", 30]]}]}, _cur_ag),
              goal_agenda_steps({"threads": [{"refs": [["PR", 20]]}, {"refs": [["backlog", 12]]}]}, _cur_ag),
              goal_agenda_steps({"threads": [{"refs": [["backlog", 11]]}]}, None),
              _gas({"threads": [{"refs": [["backlog", 11]]}]}, {"malformed": "x"})),
             ([2], [1, 4], [], []))
        case("tag_text is one spelling, and empty for no steps", (tag_text([2, 4]), tag_text([])),
             (" · agenda step 2, 4", ""))
        _gs = derive(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n- fix · backlog #11 · f\n'
                                   '## GOAL h\n> 2026-01-02 00:00 "q2"\n- fix · backlog #40 · f\n'), _s1, "t")
        _gs["agenda"] = _cur_ag
        case("--print tags the goal its step names, and only that goal",
             [ln for ln in tree_lines(_gs) if ln.startswith("GOAL")],
             ['GOAL 1 · g (2026-01-01 00:00) "q" · agenda step 2', 'GOAL 2 · h (2026-01-02 00:00) "q2"'])
        case("the page draws the same tag beside that goal's heading, once",
             render_tree_html(_gs).count('<span class="goal-agenda">agenda step 2</span>'), 1)
        _ah = agenda_html({"agenda": _cur_ag, "agenda_history": _hist})
        case("the page's AGENDA section: the current steps, then each earlier agenda as ONE collapsed line, newest "
             "first",
             (_ah.count('<details class="fold agenda-hist">'), -1 < _ah.find("agenda #2") < _ah.find("agenda #1"),
              "<details open" in _ah, "changes if: the owner reprioritises" in _ah, "4. ⬜ backlog #12" in _ah,
              "1. ✅ backlog #12" in _ah or "1. ⬜ backlog #12" in _ah),
             (2, True, False, True, True, True))
        try:  # a forced change-if line must FAIL this case by name, not take the suite down
            _ah0 = agenda_html({"agenda": derive_agenda(dict(parse_agenda("window: w\n## g\n- x\n"), at="t", id=1,
                                                             ticked=[]), _s1)})
        except Exception as _e:  # noqa: BLE001
            _ah0 = f"CRASH {type(_e).__name__}"
        case("an agenda with no change-if draws every step, none mistaken for the change-if line",
             ("changes if" in _ah0, '<pre class="tree"><span class="ag-when">g</span>\n' in _ah0, "1. ◇ x" in _ah0, "earlier agendas" in _ah0.lower()),
             (False, True, True, False))
        case("no agenda: the page SAYS none is recorded; a malformed one is said as a warning",
             ("AGENDA — none recorded" in agenda_html({"agenda": None}),
              'class="warn">AGENDA — NOT READ: MALFORMED — bad' in agenda_html({"agenda": {"malformed": "bad"}})),
             (True, True))
        case("⛔ a snapshot with NO agenda key says it was not captured — never that there was none (r1 Codex M3)",
             ("not captured in this snapshot" in agenda_html({}), "none recorded" in agenda_html({}),
              "not captured" in agenda_html({"agenda": None})), (True, False, False))
        def _agn(i, at, steps):
            """A snapshot whose agenda has the FULL shape snap_agenda checks; `steps` is [(state, text)]."""
            return {"goals": [], "undeclared": [], "inflight_loose": [],
                    "agenda": {"id": i, "at": at, "window": "w", "change_if": None,
                               "steps": [{"n": n, "state": st, "text": tx, "when": "g", "detail": "d", "refs": []}
                                         for n, (st, tx) in enumerate(steps, 1)]}}
        _p0 = _agn(1, "t1", [("next", "a"), ("open", "b")])
        _p1 = _agn(1, "t1", [("merged", "a"), ("open", "b")])
        _p2 = _agn(2, "t2", [("next", "a")])
        case("the timeline says when an agenda is recorded, and each step whose state moved",
             (changes(_p0, _p1), changes(_p1, _p2)),
             (["agenda step 1: next → ✅ merged — a"], ["agenda recorded: set t2, 1 step(s)"]))
        _p4 = _agn(2, "t1", [("next", "B")])
        case("⛔ a second agenda in the SAME minute is a new agenda, never a false step move (r1 Codex M2)",
             changes(_p1, _p4), ["agenda recorded: set t1, 1 step(s)"])
        # r2 Codex H1/M2 — the class: a malformed value or a missing identity on EITHER side, never a crash, never a move
        _noid = dict(_p0, agenda={k: v for k, v in _p0["agenda"].items() if k != "id"})
        _noat = dict(_p1, agenda={k: v for k, v in _p1["agenda"].items() if k != "at"})
        _worlds = []
        for _a, _b in ((dict(_p0, agenda=True), _p1), (_p0, dict(_p1, agenda=["bad"])), (_noid, _p1), (_p0, _noat),
                       (_noid, dict(_p1, agenda=dict(_noid["agenda"], steps=_p1["agenda"]["steps"]))),
                       (dict(_p0, agenda={"malformed": "x"}), _p1)):
            try:
                _worlds.append([c for c in changes(_a, _b) if c.startswith("agenda")])
            except Exception as exc:     # a value, so the case names the crash (r2 Codex H1)
                _worlds.append(type(exc).__name__)
        case("⛔ a malformed or identity-less agenda on either side never crashes the timeline and never yields a step "
             "move — only a valid new agenda is said to be recorded (r2 Codex H1, M2)", _worlds,
             [["agenda recorded: set t1, 2 step(s)"], [], ["agenda recorded: set t1, 2 step(s)"], [], [],
              ["agenda recorded: set t1, 2 step(s)"]])
        _bad_kinds = [snap_agenda({"agenda": v})[0] for v in
                      (dict(_p0["agenda"], steps=[dict(_p0["agenda"]["steps"][0], refs=[1])]),
                       dict(_p0["agenda"], steps=[dict(_p0["agenda"]["steps"][0], refs=[["backlog", "1"]])]),
                       True, ["bad"], {"malformed": "m"}, dict(_p0["agenda"], id=True), dict(_p0["agenda"], at=None),
                       dict(_p0["agenda"], window=3), dict(_p0["agenda"], change_if=[]),
                       dict(_p0["agenda"], steps=[{"n": 1}]), dict(_p0["agenda"], steps="x"))]
        case("snap_agenda: absent, none, ok, and every malformed shape a reader would index is MALFORMED",
             (snap_agenda({})[0], snap_agenda({"agenda": None})[0], snap_agenda(_p0)[0], _bad_kinds),
             ("absent", "none", "ok", ["malformed"] * 11))
        _bad_render = []
        for _v in (True, ["bad"], dict(_p0["agenda"], steps=[{"n": 1}])):
            try:
                _bad_render.append((agenda_lines({"agenda": _v})[0][:28], 'class="warn"' in agenda_html({"agenda": _v}),
                                    goal_agenda_steps({"threads": [{"refs": [["backlog", 1]]}]}, _v)))
            except Exception as exc:
                _bad_render.append(type(exc).__name__)
        case("⛔ a malformed agenda value is SAID by --print and the page, and tags no goal — never a crash (r2 Codex H1)",
             _bad_render, [("AGENDA — NOT READ: MALFORMED", True, [])] * 3)
        _hb = {"agenda": _p0["agenda"], "agenda_history": [{"id": 1, "at": "a"}]}
        try:
            _hv = (snap_history(_hb)[1] is not None, snap_history({"agenda_history": _hist})[1],
                   [snap_history({"agenda_history": v})[1] is not None for v in (False, "", 0, None)],
                   any("earlier agendas NOT READ" in ln for ln in agenda_lines(_hb)),
                   "earlier agendas NOT READ" in agenda_html(_hb))
        except Exception as exc:       # a value, so a mutant reaches this case rather than crashing
            _hv = type(exc).__name__
        case("⛔ earlier agendas not in an agenda's shape are SAID, never rendered or crashed on — a FALSY one too "
             "(r3 Codex L2)", _hv, (True, None, [True, True, True, True], True, True))
        _h1 = {"id": 1, "at": "a", "replaced_at": "b", "window": "w",
               "steps": [{"n": 1, "state": "merged", "text": "x", "refs": []}]}
        _hrefs = dict(_h1, steps=[dict(_h1["steps"][0], refs=1)])
        _hdup = dict(_h1, steps=[_h1["steps"][0], dict(_h1["steps"][0], text="y")])

        def _hist_said(h):
            """backlog #504: (snap_history refuses it, the page REPLAY says so) — or the crash's name, as a value."""
            try:
                return (snap_history({"agenda_history": [h]})[1] is not None,
                        "earlier agendas NOT READ" in render_page([dict(_ns, agenda=_p0["agenda"], agenda_history=[h])], "t"))
            except Exception as exc:
                return type(exc).__name__
        case("⛔ an earlier agenda's step whose refs is not a list is SAID by snap_history and the page replay, never "
             "a TypeError (backlog #504)", (_hist_said(_hrefs), _hist_said(_h1)), ((True, True), (False, False)))
        case("⛔ an earlier agenda with two steps of one n is SAID by snap_history and the page replay (backlog #504)",
             _hist_said(_hdup), (True, True))
        _pdup = _agn(1, "t1", [("next", "a"), ("merged", "a")])
        _pdup["agenda"]["steps"][1]["n"] = 1
        case("⛔ a current agenda with two steps of one n is MALFORMED, so two identical snapshots report no step "
             "move (backlog #504)",
             (snap_agenda(_pdup)[0], [c for c in changes(_pdup, json.loads(json.dumps(_pdup))) if c.startswith("agenda")]),
             ("malformed", []))
        def _rec_err(states):
            try:
                _agenda_records(json.dumps({"kind": "replaced", "at": "t", "of": 1, "states": states}), "x")
                return None
            except Malformed as exc:
                return str(exc)
        case("⛔ a frozen state that is not {n: int, state: str} is MALFORMED where it is read, never a crash later "
             "(r1 Codex H1)",
             ["a frozen state needs" in (_rec_err(x) or "") for x in
              ([{"n": [], "state": "merged"}], [{"n": 1, "state": {"bad": 1}}], [{"n": True, "state": "next"}], ["x"])]
             + [_rec_err([{"n": 1, "state": "merged"}])], [True, True, True, True, None])

        def _refs_err(refs):
            """backlog #504: an agenda step with these `refs` -> True if refused as MALFORMED for its refs, None if it
            passes, or the crash's name — a value, so a mutant reaches the case rather than crashing it."""
            try:
                _agenda_records(json.dumps({"kind": "agenda", "at": "t", "id": 1, "window": "w",
                                            "steps": [{"when": "g", "text": "x", "refs": refs}]}), "x")
                return None
            except Malformed as exc:
                return "[kind, number] pairs" in str(exc)
            except Exception as exc:
                return type(exc).__name__
        case("⛔ an agenda step's ref that is not a list is MALFORMED where it is read (backlog #504)",
             _refs_err([1]), True)
        case("⛔ an agenda step's ref with no number is MALFORMED where it is read (backlog #504)",
             _refs_err([["backlog"]]), True)
        case("⛔ an agenda step's ref with three parts is MALFORMED where it is read (backlog #504)",
             _refs_err([["backlog", 1, 2]]), True)
        case("⛔ an agenda step's ref of an unknown kind is MALFORMED where it is read (backlog #504)",
             _refs_err([["issue", 1]]), True)
        case("⛔ an agenda step's ref whose number is not an int (a bool, a string) is MALFORMED (backlog #504)",
             [_refs_err([["backlog", True]]), _refs_err([["PR", "1"]]), _refs_err([["backlog", 1.0]])],
             [True, True, True])
        case("...and an agenda step with well-formed refs of every known kind passes (backlog #504, the control)",
             (_refs_err([["backlog", 1], ["PR", 2]]), _refs_err([])), (None, None))
        case("the known ref kinds are exactly the alternatives of the step grammar, each one parsed by it (backlog #504)",
             (sorted(REF_KINDS), [REF_RE.findall(f"{k} #7") for k in sorted(REF_KINDS)]),
             (["PR", "backlog"], [[("PR", "7")], [("backlog", "7")]]))
        # r2 Codex F2: the derivation splits the regex TEXT, so a grammar the split misreads (a group, an escaped `|`,
        # a flag) drifts. Assert from the other side: every `<word> #7` the grammar ACCEPTS, over a probe of each
        # kind's case variants and every word in the pattern text, names a known kind.
        _probe = sorted({v for k in REF_KINDS for v in (k, k.lower(), k.upper(), k.swapcase(), k.title())}
                        | set(re.findall(r"\w+", REF_RE.pattern)) | {"issue", "pr", "Backlog", "Pr"})
        case("⛔ no `<word> #7` the step grammar accepts names a kind outside the known ref kinds — a case-insensitive or "
             "regrouped grammar is caught (backlog #504, r2 Codex F2)",
             sorted({k for w in _probe for k, _n in REF_RE.findall(f"{w} #7")} - set(REF_KINDS)), [])

        _ap = r / "main" / AGENDA_REL

        def replayed(path):
            """The agendas, or the MALFORMED message as a one-item list — a value a case can name, not a crash."""
            try:
                return agendas(read_agenda_log(path))
            except Malformed as exc:
                return [str(exc)]
        _ag2 = parse_agenda("window: tomorrow\n## g\n- backlog #12 · next one\n")
        record_agenda(_ap, ag, "2026-11-04 10:00", _s1)
        record_agenda(_ap, _ag2, "2026-11-04 11:00", _s1)
        _all = replayed(_ap)
        case("⭐ a new agenda REPLACES the current one whole, and the old one keeps its states AT replacement",
             (len(_all), _all[0]["replaced"], _all[1]["replaced"], _all[1]["window"]) if len(_all) == 2 else _all,
             (2, {"at": "2026-11-04 11:00", "states": [{"n": 1, "state": "merged"}, {"n": 2, "state": "open"},
                                                       {"n": 3, "state": FREE}, {"n": 4, "state": "next"}]},
              None, "tomorrow"))
        _ap.unlink()
        record_agenda(_ap, ag, "2026-11-04 10:00", _s1)
        record_agenda(_ap, _ag2, "2026-11-04 11:00", None)
        _ap2 = r / "main" / ".claude" / "agenda-other.jsonl"
        _wa = parse_agenda("window: w\n## g\n- backlog #12 · waits\n")
        record_agenda(_ap2, _wa, "t1", _s1, [{"key": "k", "refs": [["backlog", 12]], "waits": "the owner"}])
        record_agenda(_ap2, _wa, "t2", _s1, [{"key": "k", "refs": [["backlog", 12]], "waits": "the owner"}])
        _other = replayed(_ap2)
        case("a replacement freezes the state the declared threads give a step (❌ waiting), in its own log",
             (_other[0]["replaced"]["states"] if isinstance(_other[0], dict) else _other, _ap.is_file()),
             ([{"n": 1, "state": "blocked"}], True))
        _ap2.unlink()
        case("⛔ replaced while a source was unread: the states say CANNOT, never a guessed state",
             (lambda xs: {x["state"] for x in (xs[0]["replaced"] or {"states": []})["states"]}
              if isinstance(xs[0], dict) else xs)(replayed(_ap)),
             {"cannot"})
        _ap.unlink()

        def tick_err(n):
            try:
                tick_agenda(_ap, n, "t")
            except Malformed as exc:
                return str(exc)
            return None
        _none_yet = tick_err(1)
        record_agenda(_ap, ag, "2026-11-04 10:00", _s1)
        _refused, _range, _ok = tick_err(1), tick_err(9), tick_err(3)
        case("⛔ a tick: refused with no agenda, refused on a DERIVED step, refused out of range; a free one ticks",
             ("no agenda to tick" in (_none_yet or ""), "never ticked by hand" in (_refused or ""),
              "does not exist" in (_range or ""),
              _ok, agendas(read_agenda_log(_ap))[-1]["ticked"]),
             (True, True, True, None, [3]))
        _twice = tick_err(3)
        case("⛔ a step already ticked is refused, not ticked twice (r1 Codex M4)",
             ("already ticked" in (_twice or ""), agendas(read_agenda_log(_ap))[-1]["ticked"]), (True, [3]))

        _bad_fields = [{"kind": "agenda", "at": "t", "id": 1, "window": "w"},
                       {"kind": "agenda", "at": "t", "id": "1", "window": "w", "steps": []},
                       {"kind": "agenda", "at": "t", "id": 1, "window": "w", "steps": [{"text": "x"}]},
                       {"kind": "tick", "at": "t", "of": 1},
                       {"kind": "replaced", "at": "t", "of": 1}]
        _fe = []
        for _rec in _bad_fields:
            try:
                _agenda_records(json.dumps(_rec), "x.jsonl")
                _fe.append(None)
            except Malformed as exc:
                _fe.append("needs" in str(exc))
            except (KeyError, TypeError) as exc:     # a crash where MALFORMED belongs, as a value
                _fe.append(type(exc).__name__)
        case("⛔ a record missing a field a reader indexes is MALFORMED, never a KeyError later (r3 Codex M3)",
             _fe, [True] * 5)
        _nl = r / "nl.jsonl"
        _nl.write_text(json.dumps({"kind": "agenda", "at": "t", "id": 1, "window": "w",
                                   "steps": [{"when": "g", "text": "free", "refs": []}]}))
        tick_agenda(_nl, 1, "t2")
        case("⛔ a log whose last line has no newline is still appended to as SEPARATE records (r3 Codex M2)",
             [x["ticked"] for x in replayed(_nl)] if isinstance(replayed(_nl)[0], dict) else replayed(_nl), [[1]])
        _nl.unlink()
        _ws = r / "ws.jsonl"
        _ws.write_text("  \t ")
        record_agenda(_ws, ag, "t", None)
        case("⛔ a log that is only whitespace, with no final newline, is emptied before the newline repair — no blank "
             "line left ahead of the first record (backlog #504)",
             (_ws.read_text().count("\n"), _ws.read_text()[:1], [x["id"] for x in replayed(_ws)]), (1, "{", [1]))
        _ws.unlink()
        _tw = r / "tw.jsonl"
        _tw.write_text(json.dumps({"kind": "agenda", "at": "t", "id": 1, "window": "w",
                                   "steps": [{"when": "g", "text": "free", "refs": []}]}) + "\n   ")
        record_agenda(_tw, ag, "t2", None)
        case("⛔ a log whose last line is blanks after a record leaves no blank line before the next write (backlog #504)",
             (_tw.read_text().count("\n"), [x["id"] for x in replayed(_tw)], "" in _tw.read_text().split("\n")[:-1]),
             (3, [1, 2], False))
        _tw.unlink()
        _nn = r / "nn.jsonl"
        _nn.write_text("\n")
        record_agenda(_nn, ag, "t", None)
        case("⛔ a log that is a lone newline is emptied too, so the first record is not preceded by a blank line (backlog #504)",
             (_nn.read_text().count("\n"), _nn.read_text()[:1]), (1, "{"))
        _nn.unlink()
        # r2 Codex F1, the input verbatim: a CRLF log whose last record is followed by spaces. The repair cut at a
        # length counted after newline translation, so it removed the tick's closing `}`.
        _crlf_agenda = '{"kind":"agenda","at":"t","id":1,"window":"w","steps":[{"when":"g","text":"free","refs":[]}]}'
        _crlf_tick = '{"kind":"tick","at":"t","of":1,"step":1}'
        _crlf_data = (_crlf_agenda + "\r\n" + _crlf_tick + "   ").encode()
        _cr = r / "crlf.jsonl"
        _cr.write_bytes(_crlf_data)
        record_agenda(_cr, ag, "t2", None)
        case("⛔ a CRLF log is kept byte for byte ahead of the appended record — the blank repair never cuts into a "
             "record or its line ending (backlog #504, r2 Codex F1)",
             (_cr.read_bytes().startswith(_crlf_data),
              [(x["id"], x["ticked"]) for x in replayed(_cr)] if isinstance(replayed(_cr)[0], dict) else replayed(_cr)),
             (True, [(1, [1]), (2, [])]))
        _cr.write_bytes(_crlf_agenda.encode() + b"\r\n\r\n \t")
        record_agenda(_cr, ag, "t2", None)
        case("...and blank lines after a CRLF record are cut after its own CRLF, which is kept (backlog #504, r2 Codex F1)",
             _cr.read_bytes().startswith(_crlf_agenda.encode() + b"\r\n{"), True)
        _cr.unlink()
        # r3 Claude N1 and N2, the reviewer's inputs verbatim (`A` an agenda record, `T` a tick). The line model is
        # written out HERE, independently of the code under test: `\r\n`, a lone `\r` and `\n` each end a line, and a
        # line is blank when `str.strip()` empties it.
        _A, _T = _crlf_agenda.encode(), _crlf_tick.encode()
        _lr = r / "lone-cr.jsonl"

        def _ids(path):
            """Each agenda as (id, ticked steps), or the MALFORMED message as a one-item list."""
            got = replayed(path)
            return [(x["id"], x["ticked"]) for x in got] if all(isinstance(x, dict) for x in got) else got

        def after_record(data):
            """(the log replayed before, `record_agenda`'s outcome, the log replayed after, a blank line left ahead of the
            appended record) for a log holding `data` — every outcome a value a case can name."""
            _lr.write_bytes(data)
            before = _ids(_lr)
            try:
                record_agenda(_lr, ag, "t2", None)
                wrote = "ok"
            except Malformed as exc:
                wrote = f"Malformed: {exc}"
            lines = re.split(r"\r\n|\r|\n", _lr.read_bytes().decode("utf-8"))
            after = _ids(_lr)
            return before, wrote, after, any(not ln.strip() for ln in lines[:-1])
        case("⛔ a log whose lines end in a lone CR is read AND written: the writers' line model is the reader's "
             "(backlog #504, r3 Claude N1)",
             after_record(_A + b"\r" + _T + b"\r"), ([(1, [1])], "ok", [(1, [1]), (2, [])], False))
        case("⛔ a blank tail the reader skips is cut, whatever its whitespace or line ending — one meaning of blank for the "
             "reader and the cut (backlog #504, r3 Claude N2)",
             ([after_record(_A + t)[1:] for t in (b"\n\x0c", b"\n\x0b\n", b"\n\xc2\xa0", b"\r\r\n", b"\r   ")],
              after_record(b"\x0c\n")[1:], _lr.read_bytes()[:1]),
             ([("ok", [(1, []), (2, [])], False)] * 5, ("ok", [(1, [])], False), b"{"))
        _lr.unlink()
        # r2 Codex F3, the input verbatim: an unfinished record whose string ends in spaces. Recording is refused,
        # and the refused log is left exactly as it was — nothing is cut before the log is validated.
        _uf = r / "unfinished.jsonl"

        def refused_unchanged(data):
            """(refused as malformed, the log left exactly as it was) for a log holding `data`."""
            _uf.write_text(data)
            try:
                record_agenda(_uf, ag, "t", None)
                refused = False
            except Malformed:
                refused = True
            return refused, _uf.read_text() == data
        # the second input has a blank tail the repair WOULD cut — so the order (validate, then cut) is what is tested
        case("⛔ a log recording refuses as malformed is left unchanged — nothing is cut before it is validated "
             "(backlog #504, r2 Codex F3)",
             [refused_unchanged('{"kind":"agenda","text":"unfinished   '),
              refused_unchanged('{"kind":"agenda","text":"unfinished\n  \t')],
             [(True, True), (True, True)])
        _uf.unlink()

        def replay_err(recs):
            try:
                agendas(recs)
            except Malformed as exc:
                return str(exc)
            return None
        _A = {"kind": "agenda", "at": "t1", "id": 1, "window": "w", "steps": []}
        _B = {"kind": "agenda", "at": "t2", "id": 2, "window": "w", "steps": []}
        _rA = {"kind": "replaced", "at": "t2", "of": 1, "states": []}
        _bad_replays = [
            [{"kind": "tick", "at": "t0", "of": 1, "step": 1}, _A],              # a tick before any agenda
            [_rA, _A],                                                          # a replacement before any
            [_A, _B, _rA],                                                      # B never closed A; rA arrives late
            [_A, _rA, _B, {"kind": "tick", "at": "t3", "of": 1, "step": 1}],     # a late tick for replaced A
            [_A, _rA, dict(_B, id=3)],                                          # an id out of sequence
            [_A, _rA],                                                          # then a tick on closed A ↓
        ]
        _errs = [replay_err(r) for r in _bad_replays[:5]]
        case("⛔ a replay record naming a closed or absent agenda is MALFORMED, never dropped or misattributed "
             "(r1 Codex H2)", [bool(e) for e in _errs], [True] * 5)
        case("...and a well-formed replace-then-tick replays to the right agenda",
             [(x["id"], x["ticked"], bool(x["replaced"]))
              for x in agendas([_A, _rA, _B, {"kind": "tick", "at": "t3", "of": 2, "step": 1}])],
             [(1, [], True), (2, [1], False)])
        _ap.write_text(_ap.read_text() + json.dumps({"kind": "replaced", "at": "t9", "of": 1, "states": []}) + "\n")
        _int_tick, _int_rec = tick_err(3), None
        try:
            record_agenda(_ap, ag, "t9", _s1)
        except Malformed as exc:
            _int_rec = str(exc)
        case("⛔ after an interrupted write (closed, no successor) both writers refuse and append nothing (r2 Codex M3)",
             ("an interrupted write" in (_int_tick or ""), "an interrupted write" in (_int_rec or ""),
              len(read_agenda_log(_ap))), (True, True, 3))
        _ap.write_text(_ap.read_text() + "not json\n")
        try:
            read_agenda_log(_ap)
            _mal = None
        except Malformed as exc:
            _mal = str(exc)
        case("⛔ an unreadable agenda-log line is MALFORMED, never skipped", "line 4 is not an agenda record" in (_mal or ""), True)
        _ap.unlink()

        # main, end to end: record, print, replace, tick — through the real argument parsing and paths
        _af = r / "agenda.txt"
        _af.write_text(AG)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _rc_rec = main(["--record-agenda", str(_af)], root=r, run=fake(ok)[0], now="2026-11-04 12:00")
            _rc_tick = main(["--tick-agenda", "3"], root=r, run=fake(ok)[0], now="2026-11-04 12:01")
            _rc_pr = main(["--snapshot", "--print", "--out", str(out)], root=r, run=fake(ok)[0], now="2026-11-04 12:02")
        _said = buf.getvalue()
        case("⭐ main records an agenda, ticks it, and --print shows it under NEEDS YOU, before the tree",
             ((_rc_rec, _rc_tick, _rc_pr), "agenda recorded at 2026-11-04 12:00 (4 step(s))" in _said,
              "AGENDA — the current plan, set 2026-11-04 12:00 · until the reset" in _said,
              "3. ✅ restart the server — ticked by hand" in _said,
              _said.find("AGENDA —") != -1 and _said.find("AGENDA —") < _said.find("GOAL 1 ·"),
              (r / "main" / AGENDA_REL).is_file(), (r / AGENDA_REL).exists()),
             ((0, 0, 0), True, True, True, True, True, False))
        _step2 = next((ln for ln in _said.splitlines() if ln.strip().startswith("2. ")), "")
        case("⭐ main lends a step the `waits on` its row's declared thread carries (r1 Codex H1, the call site)",
             "waits on the owner (declared)" in _step2, True)
        case("the logged snapshot carries the agenda, so --page replays it",
             ((read_log(r / "main" / LOG_REL)[-1:] or [{}])[0].get("agenda") or {}).get("at"), "2026-11-04 12:00")
        _af2 = r / "agenda2.txt"
        _af2.write_text("window: later\n## g\n- backlog #12 · next one\n")
        with contextlib.redirect_stdout(io.StringIO()):
            _rc_h = main(["--record-agenda", str(_af2), "--snapshot", "--page", "--out", str(out)], root=r,
                         run=fake(ok)[0], now="2026-11-04 12:05")
        _last = (read_log(r / "main" / LOG_REL)[-1:] or [{}])[0]
        _pg = out.read_text() if out.is_file() else ""
        case("⭐ main logs the history IN the snapshot (so --page replays it), and the page draws the agenda under "
             "NEEDS YOU, above the tree",
             (_rc_h, [h["id"] for h in _last.get("agenda_history") or []], (_last.get("agenda") or {}).get("window"),
              _pg.count('class="fold agenda-hist"'),
              0 < _pg.find('<section class="needs') < _pg.find('<section class="agenda"') < _pg.find("<h2>Now</h2>")),
             (0, [1], "later", 1, True))
        with contextlib.redirect_stdout(io.StringIO()):
            _rc_badtick = main(["--tick-agenda", "1"], root=r, run=fake(ok)[0], now="2026-11-04 12:03")
        case("⛔ main exits 1 on a refused tick (a derived step)", _rc_badtick, 1)
        _b2 = io.StringIO()
        with contextlib.redirect_stdout(_b2):
            try:
                _rc_missing = main(["--record-agenda", str(r / "no-such-agenda.txt")], root=r, run=fake(ok)[0], now="t")
            except OSError as exc:        # a traceback in the CLI — a value here, so the case below names it
                _rc_missing = type(exc).__name__
            _rc_zero = main(["--tick-agenda", "0"], root=r, run=fake(ok)[0], now="t")
        case("⛔ a missing agenda file is CANNOT RUN (2), and `--tick-agenda 0` is a refused tick (1), "
             "never the default run (r1 Codex M3, M5)",
             (_rc_missing, "CANNOT RUN — the agenda file" in _b2.getvalue(), _rc_zero,
              "step 0 does not exist" in _b2.getvalue(), "snapshot logged" in _b2.getvalue()),
             (2, True, 1, True, False))
        (r / "main" / AGENDA_REL).write_text(json.dumps({"kind": "agenda", "at": "old", "id": 1, "window": "w"}) + "\n")
        _b3 = io.StringIO()
        _n_before = len(read_log(r / "main" / LOG_REL))
        with contextlib.redirect_stdout(_b3):
            try:
                _rc_old = main(["--snapshot", "--print", "--out", str(out)], root=r, run=fake(ok)[0],
                               now="2026-11-04 12:09")
            except (KeyError, TypeError) as exc:     # the r3 crash, as a value the case below names
                _rc_old = type(exc).__name__
        case("⛔ a malformed agenda log is SAID (exit 1, the block reads NOT READ) and the snapshot is STILL logged "
             "(r2 Codex M4) — a record MISSING a field included (r3 Codex M3)",
             (_rc_old, "AGENDA — NOT READ: MALFORMED" in _b3.getvalue(), len(read_log(r / "main" / LOG_REL)) - _n_before,
              "GOAL 1 ·" in _b3.getvalue()), (1, True, 1, True))
        (r / "main" / AGENDA_REL).unlink()
        if _log_before is not None:
            _log_p.write_text(_log_before)
        run, _ = fake([(["git", "fetch"], (128, "offline"))] + ok[1:])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_down = main(["--snapshot", "--page", "--out", str(out)], root=r, run=run, now="2026-10-28 09:10")
        case("⛔ main exits 2 when a source cannot run, logs nothing, and the page says why",
             (rc_down, len(read_log(r / "main" / LOG_REL)), "could NOT run" in out.read_text()), (2, 1, True))
        case("⛔ the log is written to the MAIN checkout's git-ignored .claude/, never the root's",
             ((r / "main" / LOG_REL).is_file(), (r / LOG_REL).exists()), (True, False))
        (r / THREADS_REL).write_text(good + "stray\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rc_bad = main(["--snapshot"], root=r, run=fake(ok)[0])
        case("⛔ a malformed threads file exits 1, loudly", rc_bad, 1)
        (r / "main" / LOG_REL).unlink(missing_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            rc_empty = main(["--page", "--out", str(out)], root=r, run=run_ok)
        case("⛔ --page over an empty log is CANNOT RUN, and renders nothing", rc_empty, 2)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_none = main(["--snapshot"], root=r / "main", run=run_ok)
        buf_nomain = io.StringIO()
        with contextlib.redirect_stdout(buf_nomain):
            rc_nomain = main(["--page"], root=r, run=run_nogit)
        case("⛔ no main checkout to hold the log is CANNOT RUN", (rc_nomain, "MAIN checkout" in
             buf_nomain.getvalue()), (2, True))
        case("⛔ a checkout with no threads file is CANNOT RUN, saying which file",
             (rc_none, f"{THREADS_REL} does not exist" in buf.getvalue()), (2, True))
        # ── backlog #610: only regen-pages.py's fresh clone writes the SERVED page ─────────────────────────
        (r / THREADS_REL).write_text(good)
        _g610, _served = globals(), r / "served.html"
        _saved_out, _saved_env = _g610["DEFAULT_OUT"], os.environ.pop(_SS.MAIN_CHECKOUT_ENV, None)
        _g610["DEFAULT_OUT"] = _served
        try:
            for _argv610 in ([], ["--page"], ["--snapshot", "--page"]):
                _b610 = io.StringIO()
                with contextlib.redirect_stdout(_b610):
                    _rc610 = main(_argv610, root=r, run=run_ok, now="2026-11-11 19:40")
                case(f"⛔ backlog #610: a direct run ({' '.join(_argv610) or 'bare'}) never writes the SERVED page, "
                     f"and logs nothing", (_rc610, "regen-pages.py --page goal-tree" in _b610.getvalue(),
                                           _served.exists(), (r / "main" / LOG_REL).exists()), (2, True, False, False))
            with contextlib.redirect_stdout(io.StringIO()):
                _rc610p = main(["--snapshot", "--page", "--out", str(r / "preview.html")], root=r, run=run_ok,
                               now="2026-11-11 19:41")
            case("backlog #610: ...while an explicit --out (a preview) is still written",
                 (_rc610p, (r / "preview.html").is_file(), _served.exists()), (0, True, False))
            os.environ[_SS.MAIN_CHECKOUT_ENV] = str(r / "main")
            with contextlib.redirect_stdout(io.StringIO()):
                _rc610c = main(["--page"], root=r, run=run_ok, now="2026-11-11 19:42")
            case("⛔ backlog #610: ...and inside regen-pages' clone (REGEN_MAIN_CHECKOUT set) the served page IS written",
                 (_rc610c, _served.is_file()), (0, True))
        finally:
            _g610["DEFAULT_OUT"] = _saved_out
            os.environ.pop(_SS.MAIN_CHECKOUT_ENV, None)
            if _saved_env is not None:
                os.environ[_SS.MAIN_CHECKOUT_ENV] = _saved_env

    # ── r1 X3 (Codex's arrangement): a REAL git worktree whose plans exist while the MAIN checkout has
    # no `.claude/plans/` at all. Real git, because `plan_dirs` reads `git worktree list`; the suite runs
    # inside `fixture_git.isolated()`, so no caller GIT_* reaches it.
    import subprocess as _sp
    with tempfile.TemporaryDirectory() as dx:
        _m = pathlib.Path(dx).resolve() / "main"
        _m.mkdir()

        def _git(*args, cwd=_m):
            return _sp.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                            "-C", str(cwd), *args], capture_output=True, text=True, timeout=60)
        _git("init", "-q")
        _git("commit", "-q", "--allow-empty", "-m", "root")
        _side = pathlib.Path(dx).resolve() / "side"
        _git("worktree", "add", "-q", str(_side), "-b", "side")
        (_side / ".claude" / "plans").mkdir(parents=True)
        (_side / ".claude" / "plans" / "side-only.md").write_text("<!-- parent: - -->\n- [ ] a")
        (_m / "docs").mkdir()
        (_m / DASHBOARD_REL).write_text(DASH_FIXTURE)
        (_m / BACKLOG_REL).write_text(BACKLOG_FIXTURE)

        def _run_x3(cmd, cwd, timeout):
            if cmd[:2] == ["git", "rev-parse"]:
                return 0, str(_m / ".git") + "\n"
            if cmd[:2] == ["git", "fetch"]:
                return 0, ""
            if cmd[:2] == ["git", "log"]:
                return 0, "abc1234\t2026-11-03 19:09\tone (#20)\n"
            if cmd[:3] == ["gh", "pr", "list"]:
                return 0, "[]"
            if cmd[:2] == ["gh", "repo"]:
                return 0, '{"nameWithOwner": "o/r"}'
            return 1, "unexpected"
        _sx = collect(_m, _run_x3)
        case("⭐ #389 r1 X3: a worktree's plans are read when the MAIN checkout has no .claude/plans/, "
             "and the missing directory is still a note",
             ([p["plan"] for p in _sx["plans"]], "plans" in _sx["errors"],
              any("no .claude/plans/ in the main checkout" in n for n in _sx["plan_notes"])),
             (["side-only"], False, True))

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""The goal tree, logged: why each thread of work exists, what state it is in, and how that changed.

    python3 scripts/goal-tree.py --snapshot --page --print   # what /goal-tree runs
    python3 scripts/goal-tree.py                             # = --snapshot --page (the Refresh button)
    python3 scripts/goal-tree.py --page                      # re-render from the log, no gh, no git
    python3 scripts/goal-tree.py --self-test                 # 110 cases

WHY THIS EXISTS (backlog #363). Asked 2026-10-28 03:41: *"I wonder if this kind of goal tree is logged
every so often (periodically in time or when meaningful changes are made) and I can see the page to learn
how your work has been progressed, the page can be ideal dashboard."* `/goal-tree` printed the tree in
chat and nothing kept it; the work-lines page draws only plans armed with `begin-plan.py`, and none had
been armed since 2026-10-25, so it showed nothing of the work the owner was watching.

⛔ TWO KINDS OF FACT, AND THE PAGE NEVER MIXES THEM.
  * the RELATIONS — which goal a thread serves, and as a fix, a blocker, bookkeeping or a side job — are
    DECLARED by hand in `docs/goal-threads.md`. No tool can see WHY a PR exists; pretending to infer it
    would print a plausible tree that is believed.
  * the STATES — merged (with its SHA), open (draft, mergeability, checks), in flight, closed — are
    DERIVED at snapshot time from `git log origin/master` subjects, `gh pr list` and
    `.claude/inflight.jsonl`. A declared `waits on …` is shown as DECLARED, never as a derived state.

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
    any line that parser refused to read reported as unreadable.
"Nothing waits on you" is said only when ALL THREE were read; a source that cannot be read is NOT READ,
and a snapshot with a NOT READ source is not logged, like any other CANNOT RUN.

TRIGGERS: `/goal-tree` (`.claude/commands/goal-tree.md`) runs it before printing; a PostToolUse hook
(`.claude/hooks/goal-tree-snapshot.sh`) runs it after `gh pr merge` and after an edit of the threads file;
the page's Refresh button runs it with no arguments.

⚠ BOUNDS, stated. A backlog-only thread finds its PR by the `(backlog #N)` subject tail on master and by
`backlog #N` in an open PR's title; a PR that names its row any other way is not found and the thread
reads "no PR names it yet". The in-flight ledger is matched by NUMBER (`#424`, `merge-424`), so a ledger
entry about backlog #N attaches to a thread naming PR #N too. `gh pr list --state all` is capped at
ALL_LIMIT, so an old PR beyond it reads NOT FOUND, never a guessed state.

EXIT CODES (repo convention): 0 = done · 1 = `docs/goal-threads.md` or the log is malformed ·
2 = CANNOT RUN (a source could not be read, or there is nothing to render).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import importlib.util
import json
import pathlib
import re
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import page_chrome  # noqa: E402

ROOT = SCRIPTS.parent
THREADS_REL = "docs/goal-threads.md"
# ⛔ GIT-IGNORED, IN THE MAIN CHECKOUT (the coordinator's decision, 2026-10-28): a log appended on every
# merge must not churn a tracked file, and a worktree run must append to the ONE log the page reads.
LOG_REL = ".claude/goal-tree-log.jsonl"
DASHBOARD_REL = "docs/dashboard-entries.md"
BACKLOG_REL = "docs/backlog.md"
NEEDS_OWNER = "NEEDS-OWNER"
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
REF_RE = re.compile(r"\b(backlog|PR) #(\d+)\b")
# A merged subject ends `… (backlog #N) (#PR)` or `… (#PR)`; the PR number is the LAST parenthesis.
SUBJECT_PR_RE = re.compile(r"\(#(\d+)\)\s*$")
LEDGER_NUM_RE = re.compile(r"(?:#|(?<=-))(\d+)\b")

GLYPH = {"merged": "✅", "open": "⏳", "inflight": "⏳", "next": "⬜", "blocked": "❌",
         "closed": "✖", "notfound": "❓", "cannot": "⚠"}
# When a thread names several PRs, the one state shown is the first of these that any of them has:
# a thread is merged only when ALL its PRs are, and an unreadable one makes the whole thread unread.
PRECEDENCE = ("cannot", "open", "notfound", "closed", "merged")


def _sibling(name: str):
    """A hyphenated sibling script, imported by path (one rule, one place — not a copy of it)."""
    spec = importlib.util.spec_from_file_location("_" + name.replace("-", "_"), SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
            m = THREAD_RE.match(line)
            if not m:
                problems.append(f"line {i}: a thread must be `- <relation> · <refs> · <what>`: {line!r}")
                continue
            rel, refs_text, what, waits = m.groups()
            if rel not in RELATIONS:
                problems.append(f"line {i}: relation {rel!r} is not one of {', '.join(RELATIONS)}")
                continue
            if not REFS_RE.fullmatch(refs_text):
                problems.append(f"line {i}: refs {refs_text!r} must be `backlog #N` / `PR #N`, "
                                f"joined by `, ` — a thread names a backlog row or a PR")
                continue
            key = f"{rel} · {refs_text}"
            if any(t["key"] == key for t in cur["threads"]):
                problems.append(f"line {i}: thread `{key}` is declared twice in goal `{cur['slug']}`")
                continue
            cur["threads"].append({
                "key": key, "relation": rel,
                "refs": [[k, int(n)] for k, n in REF_RE.findall(refs_text)],
                "what": what.strip(), "waits": waits.strip() if waits else None})
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
def _ledger_numbers(entry: dict) -> set:
    return {int(n) for n in LEDGER_NUM_RE.findall(f"{entry.get('id', '')} {entry.get('what', '')}")}


def _pr_state(n: int, src: dict) -> tuple[str, str]:
    """(state, detail) for PR #n. Master's subjects decide `merged` first: they are what landed."""
    merged = src["merged_by_pr"]
    if merged is not None and n in merged:
        return "merged", f"merged {merged[n]}"
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
        return "merged", f"merged {src['all_merge_sha'].get(n) or '(sha unread)'} — not on master's log"
    if st == "CLOSED":
        return "closed", f"PR #{n} closed without merging"
    return "notfound", f"PR #{n} is not among the {ALL_LIMIT} newest PRs gh listed"


def derive_thread(t: dict, src: dict) -> dict:
    """PURE. One declared thread + the read sources -> the thread with `state` and `detail`."""
    prs = [n for k, n in t["refs"] if k == "PR"]
    rows = [n for k, n in t["refs"] if k == "backlog"]
    if prs:
        found = [_pr_state(n, src) for n in prs]
        state = next(s for s in PRECEDENCE if any(f[0] == s for f in found))
        detail = " · ".join(d for _, d in found)
    elif src["errors"].get("merged") or src["errors"].get("gh"):
        state, detail = "cannot", f"CANNOT RUN — {src['errors'].get('merged') or src['errors'].get('gh')}"
    else:
        hit = next(((sha, pr) for sha, pr, subj in src["merged_rows"]
                    if any(re.search(rf"\(backlog #{n}\)", subj) for n in rows)), None)
        opened = [p for p in src["open"].values()
                  if any(re.search(rf"\bbacklog #{n}\b", p.get("title") or "") for n in rows)]
        if hit:
            state, detail = "merged", f"merged {hit[0]} via PR #{hit[1]}"
        elif opened:
            p = opened[0]
            state, detail = "open", (f"PR #{p['number']} open" + (" · draft" if p.get("isDraft") else "")
                                     + " · " + _SS.check_summary(p.get("statusCheckRollup")))
        else:
            state, detail = "next", "no PR names it yet"
    nums = set(prs) | set(rows)
    flying = [_SS.clean(e.get("what", ""), 160) for e in src["ledger"] if _ledger_numbers(e) & nums]
    if flying and state in ("next", "notfound"):
        state = "inflight"
    if flying:
        detail += " · in flight: " + "; ".join(flying)
    if t.get("waits") and state in ("next", "inflight"):
        state = "blocked" if state == "next" else state
        detail += f" · waits on {t['waits']} (declared)"
    return dict(t, state=state, detail=detail)


def derive(goals: list[dict], src: dict, now: str) -> dict:
    """PURE. Goals + sources -> one snapshot. `cannot` lists every source that could not be read."""
    out_goals = [dict(g, threads=[derive_thread(t, src) for t in g["threads"]]) for g in goals]
    named_prs = {n for g in out_goals for t in g["threads"] for k, n in t["refs"] if k == "PR"}
    named_prs |= {int(m) for g in out_goals for t in g["threads"]
                  for m in re.findall(r"PR #(\d+)", t["detail"])}
    undeclared = [{"pr": n, "title": _SS.clean(p.get("title") or "", 160),
                   "draft": bool(p.get("isDraft"))}
                  for n, p in sorted(src["open"].items()) if n not in named_prs]
    nums = {n for g in out_goals for t in g["threads"] for _, n in t["refs"]}
    loose = [{"id": _SS.clean(e.get("id", ""), 60), "what": _SS.clean(e.get("what", ""), 160)}
             for e in src["ledger"] if not (_ledger_numbers(e) & nums) and not _SS.waits_on_owner(e)]
    return {"at": now, "head": src.get("head"), "repo": src.get("repo"), "goals": out_goals,
            "undeclared": undeclared, "inflight_loose": loose, "needs": list(src.get("needs") or []),
            "needs_not_read": [f"{k}: {src['errors'][k]}" for k in NEEDS_SOURCES if src["errors"].get(k)],
            "ledger_problems": list(src.get("ledger_problems") or []),
            "cannot": [f"{k}: {v}" for k, v in sorted(src["errors"].items()) if v]}


def fingerprint(snap: dict) -> str:
    """What a snapshot SAYS, without when it was read or the master head it was read at."""
    return json.dumps({k: v for k, v in snap.items() if k not in ("at", "head")}, sort_keys=True)


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
    for k in b:
        if k not in a:
            out.append(f"added [{b[k]['relation']}] {k[1].split(' · ', 1)[1]}: "
                       f"{GLYPH[b[k]['state']]} {b[k]['detail']}")
        elif (a[k]["state"], a[k]["detail"]) != (b[k]["state"], b[k]["detail"]):
            out.append(f"[{b[k]['relation']}] {k[1].split(' · ', 1)[1]}: {a[k]['state']} → "
                       f"{GLYPH[b[k]['state']]} {b[k]['state']} — {b[k]['detail']}")
    out += [f"removed [{a[k]['relation']}] {k[1].split(' · ', 1)[1]}" for k in a if k not in b]
    pu, cu = {u["pr"] for u in prev["undeclared"]}, {u["pr"] for u in cur["undeclared"]}
    out += [f"undeclared PR #{n} appeared" for n in sorted(cu - pu)]
    out += [f"undeclared PR #{n} is gone" for n in sorted(pu - cu)]
    pn = {(n["source"], n["ref"]) for n in prev.get("needs") or []}
    cn = {(n["source"], n["ref"]) for n in cur.get("needs") or []}
    out += [f"needs you, new: {r} ({s})" for s, r in sorted(cn - pn)]
    out += [f"needs you, cleared: {r} ({s})" for s, r in sorted(pn - cn)]
    pl, cl = {u["id"] for u in prev["inflight_loose"]}, {u["id"] for u in cur["inflight_loose"]}
    out += [f"in flight, under no goal: {i}" for i in sorted(cl - pl)]
    out += [f"no longer in flight: {i}" for i in sorted(pl - cl)]
    return out or ["no change a reader would see (the stored tree differs only in wording)"]


# ── NEEDS YOU: a decision only the owner can make, open now (owner decision D1, 2026-10-28) ────
def needs_owner(row: dict) -> bool:
    """PURE. Does this backlog row still wait on the OWNER? Open, carries `NEEDS-OWNER`, and the text
    after its LAST marker does not begin `answered`. ⚠ BOUND: a row whose decision was recorded in some
    other wording, with the marker left in place, still reads as waiting — the marker is the claim."""
    s = row.get("status") or ""
    i = s.rfind(NEEDS_OWNER)
    return (not row.get("closed") and i >= 0
            and not re.match(r"\W*answered\b", s[i + len(NEEDS_OWNER):], re.I))


def needs_from_dashboard(text: str) -> list[dict]:
    """The dashboard's unresolved asks, by `gen-dashboard.unresolved()` — and every entry the store's
    own grammar could not read, NAMED as unreadable rather than dropped (it may be an ask)."""
    gd = _sibling("gen-dashboard")
    entries = gd.parse_entries(text)
    out = [{"source": "dashboard", "ref": e["id"], "text": _SS.clean(e.get("title") or "", 160),
            "href": f"/dashboard#{gd._slug(e['id'])}", "unreadable": False}
           for e in gd.unresolved(entries)]
    out += [{"source": "dashboard", "ref": e["id"] or e.get("would_be_id") or "an entry with no id",
             "text": "could not be read: " + _SS.clean(e["error"], 160),
             "href": f"/dashboard#{gd._slug(e['id'])}" if e["id"] else "/dashboard",
             "unreadable": True} for e in entries if e["error"]]
    return out


def needs_from_ledger(entries: list[dict]) -> list[dict]:
    """In-flight entries marked `WAITS-ON-OWNER:` — session-state's own predicate, not a copy."""
    return [{"source": "ledger", "ref": _SS.clean(e.get("id", ""), 60),
             "text": _SS.clean(e["what"][len(_SS.OWNER_MARKER):], 200), "href": None,
             "unreadable": False} for e in entries if _SS.waits_on_owner(e)]


def needs_from_backlog(text: str) -> list[dict]:
    """Open rows still marked NEEDS-OWNER, parsed by gen-backlog-page's ONE row parser; any line that
    parser refused to read is reported as unreadable, never silently skipped."""
    gb = _sibling("gen-backlog-page")
    unread: list[str] = []
    rows = gb.parse(text.split("\n"), unread)
    out = []
    for r in rows:
        if needs_owner(r):
            tail = r["status"][r["status"].rfind(NEEDS_OWNER) + len(NEEDS_OWNER):].lstrip(" —-")
            out.append({"source": "backlog", "ref": f"backlog #{r['num']}",
                        "text": _SS.clean(html.unescape(gb.plain(r["title"])), 140) + " — "
                                + _SS.clean(tail, 160),
                        "href": f"/backlog-table#i{r['num']}", "unreadable": False})
    if unread:
        out.append({"source": "backlog", "ref": f"{len(unread)} line(s) of {BACKLOG_REL}",
                    "text": "could not be read by the row parser, so a row waiting on you may be among them",
                    "href": "/backlog-table", "unreadable": True})
    return out


# ── reading the world (the only impure part) ──────────────────────────────────────────────────
def collect(root: pathlib.Path, run=None) -> dict:
    """Read git, gh and the ledger. NEVER RAISES: a failure is recorded in `errors` by source.

    `run(cmd, cwd, timeout) -> (rc, text)` is session-state's `_run` unless a test passes one.
    """
    run = run or _SS._run
    errors: dict[str, str] = {}
    src = {"merged_by_pr": None, "merged_rows": [], "open": {}, "all": {}, "all_merge_sha": {},
           "ledger": [], "ledger_problems": [], "needs": [], "head": None, "repo": None,
           "main": root, "errors": errors}
    rc, out = run(["git", "fetch", "--quiet", "origin", "master"], root, 60)
    if rc != 0:
        errors["merged"] = f"git fetch origin master exited {rc}: {_SS.clean(out, 160)}"
    else:
        rc, out = run(["git", "log", "origin/master", f"-n{MERGED_DEPTH}", "--format=%h%x09%s"], root, 30)
        if rc != 0 or not out.strip():
            errors["merged"] = f"git log origin/master exited {rc} with {len(out.strip())} chars"
        else:
            by_pr, rows = {}, []
            for ln in out.splitlines():
                sha, _, subj = ln.partition("\t")
                m = SUBJECT_PR_RE.search(subj)
                if m:
                    by_pr.setdefault(int(m.group(1)), sha)
                    rows.append((sha, int(m.group(1)), subj))
            src["merged_by_pr"], src["merged_rows"] = by_pr, rows
            src["head"] = out.split("\t", 1)[0]
    rc, out = run(["gh", "pr", "list", "--state", "open", "--limit", str(OPEN_LIMIT), "--json",
                   "number,title,isDraft,mergeStateStatus,statusCheckRollup"], root, 30)
    try:
        if rc != 0:
            raise ValueError(f"exited {rc}: {_SS.clean(out, 160)}")
        src["open"] = {int(p["number"]): p for p in json.loads(out)}
        rc, out = run(["gh", "pr", "list", "--state", "all", "--limit", str(ALL_LIMIT), "--json",
                       "number,state,mergeCommit"], root, 30)
        if rc != 0:
            raise ValueError(f"exited {rc}: {_SS.clean(out, 160)}")
        for p in json.loads(out):
            src["all"][int(p["number"])] = p.get("state")
            if isinstance(p.get("mergeCommit"), dict) and p["mergeCommit"].get("oid"):
                src["all_merge_sha"][int(p["number"])] = p["mergeCommit"]["oid"][:8]
        rc, out = run(["gh", "repo", "view", "--json", "nameWithOwner"], root, 30)
        if rc == 0:
            src["repo"] = json.loads(out).get("nameWithOwner")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        errors["gh"] = f"gh pr list: {_SS.clean(exc, 160)}"
        src["open"] = {}
    # The ledger is git-ignored, so it lives in the MAIN checkout; session-state names it (one rule).
    main, why = _SS.main_checkout(root, run)
    src["main"] = main
    if why:
        errors["ledger"] = why
    else:
        data, why = _SS._read_whole(main / _SS.LEDGER_REL)
        if data is None:
            errors["ledger"] = why
        else:
            src["ledger"], src["ledger_problems"], _raw = _SS._parse(data)
    needs: list[dict] = []
    for key, rel, fn in (("dashboard", DASHBOARD_REL, needs_from_dashboard),
                         ("backlog", BACKLOG_REL, needs_from_backlog)):
        try:
            needs += fn((root / rel).read_text(encoding="utf-8"))
        except Exception as exc:                  # noqa: BLE001 - NOT READ, named, never "none"
            errors[key] = f"{rel} NOT READ ({type(exc).__name__}: {_SS.clean(exc, 120)})"
    if "ledger" not in errors:
        needs += needs_from_ledger(src["ledger"])
    src["needs"] = needs
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


# ── rendering ─────────────────────────────────────────────────────────────────────────────────
def segments(text: str, repo: str | None) -> list[tuple[str, str | None]]:
    """PURE. Text split into (piece, href) — every `PR #N` and `backlog #N` becomes a link."""
    out, pos = [], 0
    for m in REF_RE.finditer(text):
        out.append((text[pos:m.start()], None))
        kind, n = m.group(1), m.group(2)
        href = (f"https://github.com/{repo}/pull/{n}" if repo else None) if kind == "PR" \
            else f"/backlog-table#i{n}"
        out.append((m.group(0), href))
        pos = m.end()
    out.append((text[pos:], None))
    return [s for s in out if s[0]]


def tree_lines(snap: dict) -> list[str]:
    """PURE. The box-drawing tree, one string per line, refs left as text (`render_*` link them)."""
    lines: list[str] = []
    for g in snap["goals"]:
        first, rest = g["requests"][0], g["requests"][1:]
        lines.append(f'GOAL {g["slug"]} ({first["when"]}) "{first["quote"]}"')
        lines += [f'     + {r["when"]} "{r["quote"]}"' for r in rest]
        rels = [r for r in RELATIONS if any(t["relation"] == r for t in g["threads"])]
        if not rels:
            lines.append("└─ (no thread declared)")
        for ri, rel in enumerate(rels):
            last_rel = ri == len(rels) - 1
            lines.append(("└─ " if last_rel else "├─ ") + rel)
            ts = [t for t in g["threads"] if t["relation"] == rel]
            for ti, t in enumerate(ts):
                stem = "   " if last_rel else "│  "
                lines.append(stem + ("└─ " if ti == len(ts) - 1 else "├─ ")
                             + f'{GLYPH[t["state"]]} {t["key"].split(" · ", 1)[1]} · {t["what"]} — '
                             + t["detail"])
        lines.append("")
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
    for p in snap.get("ledger_problems") or []:
        lines.append(f"⚠ ledger: {p}")
    for c in snap["cannot"]:
        lines.append(f"⚠ CANNOT RUN — {c}")
    return lines[:-1] if lines and lines[-1] == "" else lines


def needs_state(snap: dict) -> str:
    """PURE. "items", "none" (all three sources read, nothing found) or "not-read" (empty, and at
    least one source was NOT READ — which is never reported as nothing)."""
    if snap.get("needs"):
        return "items"
    return "not-read" if snap.get("needs_not_read") or "needs" not in snap else "none"


def needs_lines(snap: dict) -> list[str]:
    """PURE. The NEEDS YOU block as text, for --print; the page draws the same items as links."""
    st, items = needs_state(snap), snap.get("needs") or []
    head = {"items": f"NEEDS YOU — {len(items)} decision(s) only you can make, open now",
            "none": "NEEDS YOU — nothing waits on you (dashboard asks, the in-flight ledger and the "
                    "backlog were all read)",
            "not-read": "NEEDS YOU — NOT KNOWN: a source was NOT READ, so an empty list here is not "
                        "an all-clear"}[st]
    out = [head]
    for i, n in enumerate(items):
        out.append(("└─ " if i == len(items) - 1 else "├─ ")
                   + ("⚠ UNREADABLE " if n["unreadable"] else "")
                   + f'[{n["source"]}] {n["ref"]} · {n["text"]}')
    out += [f"⚠ NOT READ — {w}" for w in snap.get("needs_not_read") or []]
    return out


def needs_html(snap: dict) -> str:
    st, items = needs_state(snap), snap.get("needs") or []
    lines = needs_lines(snap)
    parts = [f'<section class="needs {st}"><h2>{html.escape(lines[0])}</h2>']
    if items:
        parts.append("<ul>")
        for n in items:
            ref = (f'<a href="{html.escape(n["href"], quote=True)}">{html.escape(n["ref"])}</a>'
                   if n.get("href") else f'<code>{html.escape(n["ref"])}</code> '
                   f'<span class="src">(.claude/inflight.jsonl)</span>')
            parts.append(f'<li{" class=unreadable" if n["unreadable"] else ""}>'
                         f'<span class="src">{html.escape(n["source"])}</span> {ref} · '
                         f'{"⚠ UNREADABLE — " if n["unreadable"] else ""}{html.escape(n["text"])}</li>')
        parts.append("</ul>")
    parts += [f'<p class="warn">⚠ NOT READ — {html.escape(w)}</p>'
              for w in snap.get("needs_not_read") or []]
    parts.append("</section>")
    return "".join(parts)


def render_text(snap: dict) -> str:
    return "\n".join(needs_lines(snap) + [""] + tree_lines(snap))


def _html_line(line: str, repo: str | None) -> str:
    return "".join(f'<a href="{html.escape(h, quote=True)}">{html.escape(t)}</a>' if h
                   else html.escape(t) for t, h in segments(line, repo))


def render_tree_html(snap: dict) -> str:
    return '<pre class="tree">' + "\n".join(_html_line(ln, snap.get("repo"))
                                            for ln in tree_lines(snap)) + "</pre>"


def render_page(log: list[dict], built: str, live: dict | None = None) -> str:
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
             '<p class="lede">Each thread hangs under the owner request it serves. The relation '
             '(fix, blocker, bookkeeping, side) is declared by hand; the state is read from git and gh '
             'when the snapshot is taken. ✅ merged · ⏳ open or in flight · ⬜ next · ❌ waits '
             '(declared) · ✖ closed · ⚠ could not be read.</p>']
    if live is not None and live["cannot"]:
        parts.append('<p class="warn">⚠ The live read at ' + html.escape(live["at"]) + ' could NOT '
                     'run, so it was not logged: ' + html.escape("; ".join(live["cannot"])) +
                     '. The tree below is the newest COMPLETE snapshot.</p>')
    # ⭐ NEEDS YOU FIRST, above the tree (owner decision D1): read from THIS run when there was one,
    # complete or not, because a decision that appeared since the newest snapshot is the one to see.
    parts.insert(5, needs_html(live if live is not None else newest))
    parts += ['<h2>Now</h2>', render_tree_html(newest), '<h2>Timeline</h2>',
              '<p class="lede">Newest first. A snapshot is logged only when the tree changed.</p>']
    for i in range(len(log) - 1, -1, -1):
        snap, ch = log[i], changes(log[i - 1] if i else None, log[i])
        parts.append(f'<details class="snap"><summary><time>{html.escape(snap["at"])}</time> · '
                     f'{len(ch)} change(s): ' + _html_line(ch[0], snap.get("repo"))
                     + ('…' if len(ch) > 1 else '') + '</summary><ul>'
                     + "".join(f'<li>{_html_line(c, snap.get("repo"))}</li>' for c in ch)
                     + '</ul>' + render_tree_html(snap) + '</details>')
    parts.append('</main>')
    return "\n".join(parts)


CSS = """
:root{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;--ink-faint:#838a9b;
      --rule:#ddd9d0;--pending:#8f6410;--link:#1d5fa8;
      --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
      --ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;
      --ink-soft:#b4bac9;--ink-faint:#7d8496;--rule:#2e313b;--pending:#d9a441;--link:#7fb2ee}}
:root[data-theme="dark"]{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;--ink-soft:#b4bac9;
      --ink-faint:#7d8496;--rule:#2e313b;--pending:#d9a441;--link:#7fb2ee}
:root[data-theme="light"]{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;
      --ink-faint:#838a9b;--rule:#ddd9d0;--pending:#8f6410;--link:#1d5fa8}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--ui);line-height:1.5}
main{max-width:72rem;margin:0 auto;padding:2rem 1rem}
h1{font-size:2rem;margin:.2rem 0 1rem}
h2{font-size:1.15rem;margin:1.6rem 0 .5rem}
.meta{font-family:var(--mono);font-size:.7rem;color:var(--ink-faint);letter-spacing:.04em}
.lede{color:var(--ink-soft);max-width:70ch}
.warn{color:var(--pending);font-weight:600}
a{color:var(--link)}
pre.tree{background:var(--card);border:1px solid var(--rule);border-radius:.5rem;padding:.9rem 1.1rem;
         font-family:var(--mono);font-size:.78rem;line-height:1.55;overflow-x:auto;white-space:pre}
details.snap{border-bottom:1px solid var(--rule);padding:.35rem 0}
details.snap summary{cursor:pointer;font-size:.9rem}
details.snap time{font-family:var(--mono);font-size:.78rem;color:var(--ink-faint)}
details.snap ul{font-size:.85rem;margin:.4rem 0}
section.needs{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--pending);
              border-radius:.5rem;padding:.4rem 1.1rem .7rem;margin:1rem 0}
section.needs.none{border-left-color:var(--rule)}
section.needs h2{margin:.5rem 0}
section.needs ul{margin:.3rem 0;padding-left:1.1rem;font-size:.9rem}
section.needs li{margin:.2rem 0}
section.needs .src{font-family:var(--mono);font-size:.72rem;color:var(--ink-faint)}
"""


def write_page(out: pathlib.Path, log: list[dict], built: str, live: dict | None = None) -> None:
    body = render_page(log, built, live)
    page = (f"<!doctype html><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Goal tree</title>"
            f"<style>{CSS}\n{page_chrome.chrome_css()}</style>{body}"
            f"<script>{page_chrome.chrome_script()}</script>")
    page_chrome.assert_wired(page, "goal-tree.py")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)


# ── the command ───────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None, *, root: pathlib.Path = ROOT, run=None,
         now: str | None = None) -> int:
    ap = argparse.ArgumentParser(description="Log the goal tree and render its page (backlog #363).")
    ap.add_argument("--snapshot", action="store_true", help="derive the states and log them if changed")
    ap.add_argument("--page", action="store_true", help="render the page from the log")
    ap.add_argument("--print", dest="print_", action="store_true", help="print the tree as text")
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.self_test:
        return _self_test()
    if not (a.snapshot or a.page or a.print_):
        a.snapshot = a.page = True
    now = now or _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    main_root, why = _SS.main_checkout(root, run or _SS._run)
    if why:
        print(f"CANNOT RUN — the log lives in the MAIN checkout's {LOG_REL}, and {why}.")
        return 2
    log_path = main_root / LOG_REL
    rc, live = 0, None
    try:
        if a.snapshot:
            threads = root / THREADS_REL
            if not threads.is_file():
                print(f"CANNOT RUN — {THREADS_REL} does not exist, so there is no tree to draw.")
                return 2
            live = derive(parse_threads(threads.read_text()), collect(root, run), now)
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
        write_page(a.out, log, now, live)
        print(f"goal tree page -> {a.out}")
    if a.print_:
        shown = live if live is not None else (log[-1] if log else None)
        if shown is None:
            print(f"CANNOT RUN — no snapshot to print ({LOG_REL} is empty).")
            return 2
        print(render_text(shown))
    return rc


# Fixtures for the NEEDS YOU sources, in each source's real grammar.
DASH_FIXTURE = ("## 2026-10-01 [needs-you]\nPick one.\n\n## 2026-10-02 [needs-you]\nAnother.\n\n"
                "## 2026-10-03 [resolved: 2026-10-02/1]\nDone.\n\n## 2026-10-04 [bogus-flag]\nx\n")
BACKLOG_FIXTURE = ("# B\n\n## Items\n\n| # | Item | Touches | Size | Bundle | Status |\n"
                   "|---|---|---|---|---|---|\n"
                   "| 5 | **Pick a name** — body | x | S | (t) | NEEDS-OWNER — waits on you |\n"
                   "| 6 | **Done one** | x | S | (t) | NEEDS-OWNER — answered 10-27 |\n"
                   "| 7 | ✅ **Closed** | x | S | (t) | ✅ fixed NEEDS-OWNER — old |\n"
                   "| 8 | **Plain** | x | S | (t) | OPEN |\n| x9 | broken row | x |\n")


# ── self-test ─────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """No git and no gh: every source is a fixture, injected through `run`. Wrapped anyway, so that a
    later case that does reach git cannot inherit the caller's GIT_* (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
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
                "head": "aaaa111", "repo": "o/r", "errors": {}}
        base.update(kw)
        return base

    def one(t, s):
        return derive_thread(parse_threads('## GOAL g\n> 2026-01-01 00:00 "q"\n' + t)[0]["threads"][0], s)

    m = one("- fix · backlog #10, PR #20 · f\n", src())
    case("a PR in master's subjects is MERGED, with its SHA", (m["state"], m["detail"]),
         ("merged", "merged aaaa111"))
    o = one("- side · PR #21 · a\n", src())
    case("an open PR shows draft, mergeability and the checks summary",
         (o["state"], o["detail"]), ("open", "PR #21 open · draft · clean · 1 pass"))
    case("a closed PR is CLOSED, never open", one("- side · PR #22 · c\n", src())["state"], "closed")
    case("a PR merged off master's log says so, with gh's SHA",
         one("- side · PR #23 · c\n", src())["detail"], "merged bbbb2222 — not on master's log")
    case("a PR gh did not list is NOT FOUND, never a guess",
         one("- side · PR #77 · c\n", src())["state"], "notfound")
    case("a backlog-only thread finds its merge by the subject tail",
         one("- fix · backlog #10 · f\n", src(open={}))["detail"], "merged aaaa111 via PR #20")
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
    led = [{"id": "build-12", "what": "subagent building it"}]
    fl = one("- fix · backlog #12 · f\n", src(ledger=led))
    case("a ledger entry naming the row makes an unstarted thread IN FLIGHT",
         (fl["state"], fl["detail"]), ("inflight", "no PR names it yet · in flight: subagent building it"))
    case("a ledger entry naming '#N' in its text attaches too",
         one("- side · PR #21 · a\n", src(ledger=[{"id": "x", "what": "CI on PR #21"}]))["detail"]
         .endswith("in flight: CI on PR #21"), True)
    case("...and an OPEN PR stays open — in flight is a note, not a downgrade",
         one("- side · PR #21 · a\n", src(ledger=[{"id": "merge-21", "what": "w"}]))["state"], "open")
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
    case("the dashboard source is gen-dashboard's unresolved(), plus every entry it could not read",
         [(n["ref"], n["unreadable"]) for n in needs_from_dashboard(DASH_FIXTURE)],
         [("2026-10-01/1", False), ("2026-10-04/1", True)])
    case("a backlog need carries the row's title and the clause after the marker",
         needs_from_backlog(BACKLOG_FIXTURE)[0]["text"], "Pick a name — waits on you")
    case("the ledger source is session-state's WAITS-ON-OWNER predicate, marker stripped",
         [(n["ref"], n["text"]) for n in needs_from_ledger(
             [{"id": "a", "what": "WAITS-ON-OWNER: choose"}, {"id": "b", "what": "owner said hi"}])],
         [("a", "choose")])
    case("⛔ a title is plain TEXT, not HTML — the page escapes it once, so it is never escaped twice",
         needs_from_backlog(BACKLOG_FIXTURE.replace("**Pick a name**", "**Pick O'Brien's name**"))[0]
         ["text"].startswith("Pick O'Brien's name"), True)
    case("...and the clause is the row's own, not a constant",
         needs_from_backlog(BACKLOG_FIXTURE.replace("waits on you", "pick X or Y"))[0]["text"],
         "Pick a name — pick X or Y")
    case("an empty dashboard store has no asks", needs_from_dashboard(""), [])
    case("an empty ledger has no owner-waits", needs_from_ledger([]), [])
    _ns = derive(goals, src(needs=[]), "t")
    case("⭐ an empty list read from ALL three sources says nothing waits on you",
         (needs_state(_ns), needs_lines(_ns)[0].startswith("NEEDS YOU — nothing waits on you")),
         ("none", True))
    _nd = derive(goals, src(needs=[{"source": "backlog", "ref": "backlog #5", "text": "t",
                                     "href": "/backlog-table#i5", "unreadable": False}]), "t")
    case("needs are reported in the timeline as new and as cleared",
         (changes(_ns, _nd)[0], changes(_nd, _ns)[0]),
         ("needs you, new: backlog #5 (backlog)", "needs you, cleared: backlog #5 (backlog)"))
    case("a list with items says how many", needs_lines(_nd)[:2],
         ["NEEDS YOU — 1 decision(s) only you can make, open now", "└─ [backlog] backlog #5 · t"])
    _pg = render_page([_ns, _nd], "t")
    case("⭐ the NEEDS YOU list is at the top, above the tree, and its items link to their source",
         (_pg.index('<section class="needs') < _pg.index("<h2>Now</h2>"),
          '<a href="/backlog-table#i5">backlog #5</a>' in _pg), (True, True))
    case("a live read's needs are shown over the newest snapshot's",
         "nothing waits on you" in render_page([_nd], "t", _ns), True)

    # ── rendering ────────────────────────────────────────────────────────────────────────────
    txt = "\n".join(tree_lines(snap))
    case("--print leads with the NEEDS YOU block, then the tree",
         [ln.split(" — ")[0] for ln in render_text(snap).splitlines()[:3]],
         ["NEEDS YOU", "", 'GOAL alpha-one (2026-10-26 09:51) "do the first thing"'])
    case("the tree's root is the goal's own words, quoted, with its time",
         txt.splitlines()[0], 'GOAL alpha-one (2026-10-26 09:51) "do the first thing"')
    case("each relation is a branch, and the last one closes with └─",
         [ln for ln in txt.splitlines()[:8] if ln.startswith(("├─", "└─"))], ["├─ fix", "└─ side"])
    case("a leaf carries its glyph, refs, what and derived detail",
         "│  ├─ ✅ backlog #10, PR #20 · the first fix — merged aaaa111" in txt, True)
    case("the undeclared section is drawn", "UNDECLARED — open PRs no goal names" in txt, True)
    case("a tree drawn from a later snapshot shows ITS states",
         any("✅ PR #21 · an aside — merged dddd444" in ln for ln in tree_lines(flipped)), True)
    case("a CANNOT RUN source is printed in the tree",
         "⚠ CANNOT RUN — gh: gh pr list" in render_text(derive(goals, gh_down, "t")), True)
    case("PR refs link to GitHub, backlog refs to the backlog page",
         [h for _, h in segments("PR #20 and backlog #10", "o/r") if h],
         ["https://github.com/o/r/pull/20", "/backlog-table#i10"])
    case("with no repo read, a PR ref is plain text, never a guessed URL",
         [h for _, h in segments("PR #20", None)], [None])
    case("text in the tree is escaped", "&lt;b&gt;" in _html_line("<b> PR #1", "o/r"), True)
    log2 = [snap, flipped]
    page = render_page(log2, "2026-10-28 07:00")
    case("the page states its build time and the newest snapshot's time",
         ("<time>2026-10-28 07:00</time>" in page,
          '<time class="newest">2026-10-28 06:00</time>' in page), (True, True))
    case("⭐ the CURRENT tree is the newest snapshot, drawn above the timeline",
         page.index("Now") < page.index("Timeline") and
         page.index("✅ <a") < page.index("Timeline"), True)
    case("the timeline is newest first",
         page.index("<time>2026-10-28 06:00</time>") < page.index("<time>2026-10-28 04:00</time>"),
         True)
    case("every snapshot expands to its full tree", page.count('<pre class="tree">'), 3)
    case("a log of ONE snapshot renders it as current and as the first timeline entry",
         render_page([snap], "t").count("1 change(s): first snapshot"), 1)
    case("a failed live read is announced above the tree, with its reason",
         "could NOT run, so it was not logged: gh: gh pr list" in
         render_page(log2, "t", derive(goals, gh_down, "2026-10-28 08:00")), True)
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "p.html"
        write_page(out, log2, "2026-10-28 07:00")
        built = out.read_text()
        case("the written page is chrome-wired (theme palettes and the Refresh button)",
             (page_chrome.missing_palettes(built), 'data-page="goal-tree"' in built), ([], True))
        out_down = pathlib.Path(d) / "sub" / "down.html"
        write_page(out_down, [snap], "2026-10-28 08:30", derive(goals, gh_down, "2026-10-28 08:30"))
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
            '{"id": "build-12", "what": "w"}\n{"id": "ask-1", "what": "WAITS-ON-OWNER: pick A or B"}\n')
        (r / "docs").mkdir()
        (r / DASHBOARD_REL).write_text(DASH_FIXTURE)
        (r / BACKLOG_REL).write_text(BACKLOG_FIXTURE)
        ok = [(["git", "fetch"], (0, "")),
              (["git", "log"], (0, "abc1234\tone (backlog #10) (#20)\nabc0000\tno pr here\n")),
              (["gh", "pr", "list", "--state", "open"], (0, '[{"number": 21, "title": "t"}]')),
              (["gh", "pr", "list", "--state", "all"], (0, '[{"number": 22, "state": "CLOSED"}]')),
              (["gh", "repo"], (0, '{"nameWithOwner": "o/r"}')),
              (["git", "rev-parse"], (0, str(r / "main" / ".git") + "\n"))]
        run_ok, _ = fake(ok)
        s = collect(r, run_ok)
        case("collect reads master's subjects into PR -> SHA, skipping subjects with no PR",
             (s["merged_by_pr"], s["head"]), ({20: "abc1234"}, "abc1234"))
        case("collect reads open PRs, all PR states, the repo and the MAIN checkout's ledger",
             (sorted(s["open"]), s["all"], s["repo"], [e["id"] for e in s["ledger"]], s["errors"]),
             ([21], {22: "CLOSED"}, "o/r", ["build-12", "ask-1"], {}))
        case("⭐ NEEDS YOU gathers all three sources, each linked to where it came from",
             [(n["source"], n["ref"], n["href"]) for n in s["needs"]],
             [("dashboard", "2026-10-01/1", "/dashboard#2026-10-01-1"),
              ("dashboard", "2026-10-04/1", "/dashboard#2026-10-04-1"),
              ("backlog", "backlog #5", "/backlog-table#i5"),
              ("backlog", "1 line(s) of docs/backlog.md", "/backlog-table"),
              ("ledger", "ask-1", None)])
        case("an owner-wait in the ledger is a need, not 'in flight under no goal'",
             [u["id"] for u in derive(goals, s, "t")["inflight_loose"]], ["build-12"])
        run_nogit, _ = fake(ok[:-1] + [(["git", "rev-parse"], (128, "not a git repository"))])
        s_nogit = collect(r, run_nogit)
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
        case("--print prints the tree it just derived", 'GOAL alpha-one (2026-10-26 09:51)' in said, True)
        case("main wrote the page", out.is_file() and "<h1>Goal tree</h1>" in out.read_text(), True)
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
        (r / "main" / LOG_REL).unlink()
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

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

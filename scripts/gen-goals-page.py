#!/usr/bin/env python3
"""One always-visible page: every GOAL this project is pursuing, and where each one stands.

    python3 scripts/gen-goals-page.py              # -> ~/explainers/goals.html, served at /goals
    python3 scripts/gen-goals-page.py --fragment-only <path>
    python3 scripts/gen-goals-page.py --self-test  # 75 cases, pure functions only

WHY THIS EXISTS
---------------
Asked for "the plan for stable blob addressing" on 2026-08-24, I could not find it and spent an hour
re-deriving a roadmap that already existed. ADR-0010 fixed the *membership* half: every living spec
and plan now declares the goal it belongs to. This is the other half — the view over those
declarations, so a goal is one click rather than one search.

It closes three filed items that were circling the same page: backlog #56 (the roadmap as a page),
#59 (the decision index) and #64's page half. One page, one script, keyed by ANCHOR.

NOTHING ON THIS PAGE IS HAND-MAINTAINED, AND THAT IS THE WHOLE DESIGN
--------------------------------------------------------------------
ADR-0010's rule is *point at the roadmap for state, never copy it* — a page holding its own copy of
"where things stand" becomes the fourth document that drifts, which is the failure the anchor system
exists to prevent. So every field is DERIVED, exactly as `gen-backlog-page.py` renders
`docs/backlog.md` rather than holding a second copy of it:

  membership       <- the `Anchor:` headers on specs/plans          (ADR-0010)
  decision status  <- docs/adr/*.md front matter AND in-body ⟳ amendments
  milestone state  <- the spine's own `### M<n>` headings and their ✅ / ◀ / ⛔ markers
  backlog rows     <- ROOTS/DEPENDS in gen-backlog-page.py, now keyed by anchor slug
  last activity    <- git log, per document

READ THE IN-BODY AMENDMENTS, NOT JUST THE FRONT MATTER. ADR-0006 read `status: proposed` for three
weeks while its body carried `⟳ SUPERSEDED 2026-08-06` and `⟳ CORRECTED 2026-08-06`. A page showing
only the front matter would be confidently wrong, which is worse than showing nothing.

WHAT IT DELIBERATELY DOES NOT SHOW
----------------------------------
A review count per goal. Reviews are not anchored — 716 files, named by round and subject, across
three vocabularies. Counting them means keyword matching, which is the method that failed and caused
all of this. A number that is a lower bound of unknowable size is worse than an empty cell.

And where a goal has no milestone plan, the page says so in a fixed slot rather than leaving a gap.
Measured on the first run: 1 of 9 anchors has a spine. That absence is the finding, and a page that
hid it would be a report about its best subject rather than a dashboard over all of them.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402
import page_markup  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SUBDIRS = ("superpowers/specs", "superpowers/plans")
DEFAULT_OUT = pathlib.Path.home() / "explainers" / "goals.html"

REGISTRY_ROW = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")
ANCHOR = re.compile(r"^>\s*\*\*Anchor:\*\*\s*`([a-z0-9-]+)`\s*—\s*\*\*ADR:\*\*\s*(none|[\d,\s]+?)\s*$")
GOAL = re.compile(r"^>\s*\*\*Goal:\*\*\s*(\S.*)$")
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
FRONT_STATUS = re.compile(r"^status:\s*(.+?)\s*$", re.M)
AMENDMENT = re.compile(r"⟳[^\n]*?\b(SUPERSEDED|CORRECTED|WITHDRAWN|REVERSED|RESCOPED|RE-SCOPED)\b")
MILESTONE = re.compile(r"^#{2,4}\s+(M\d+)\s*[—-]?\s*(.*)$", re.M)
ROOTS_KEY = re.compile(r'^\s{4}"([a-z0-9-]+)":\s*dict\(', re.M)
DEPENDS_ROW = re.compile(r'^\s{4}(\d+):\s*\("([a-z-]+)",\s*"([a-z0-9-]+)"', re.M)

# Milestone state read off the document's OWN markers. Order matters: a heading can carry more than
# one, and "deferred" is the strongest claim a heading makes about itself.
MILESTONE_STATES = (("⛔", "deferred"), ("◀", "next"), ("✅", "done"))


# ---------------------------------------------------------------- pure parsing
def parse_registry(text: str) -> list[dict]:
    """[{slug, adrs, goal}] in file order. PURE."""
    out = []
    for line in text.split("\n"):
        m = REGISTRY_ROW.match(line)
        if m:
            out.append({"slug": m.group(1), "adrs": m.group(2).strip(), "goal": m.group(3).strip()})
    return out


def parse_header(text: str, head_lines: int = 10) -> dict:
    """{anchor, adrs, goal} from a document's opening; anchor is None when absent. PURE."""
    got: dict = {"anchor": None, "adrs": [], "goal": ""}
    for line in text.split("\n")[:head_lines]:
        if m := ANCHOR.match(line):
            got["anchor"] = m.group(1)
            raw = m.group(2)
            got["adrs"] = [] if raw == "none" else [n.strip() for n in raw.split(",") if n.strip()]
        elif m := GOAL.match(line):
            got["goal"] = m.group(1)
    return got


def parse_adr(text: str) -> dict:
    """{status, amendments} — front matter AND the in-body ⟳ trail. PURE.

    The amendment count is the point: ADR-0006 sat at `status: proposed` while its body recorded two
    corrections. Front matter alone is a claim about the day it was written.
    """
    m = FRONT_STATUS.search(text)
    status = m.group(1) if m else ""
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    return {"status": status, "amendments": AMENDMENT.findall(body)}


def parse_milestones(text: str) -> list[dict]:
    """[{id, title, state}] from `### M<n>` headings. PURE.

    State comes from the heading's own marker, never from a table maintained here — that is the
    difference between rendering the plan and keeping a second copy of it.
    """
    out = []
    for mid, rest in MILESTONE.findall(text):
        state = "todo"
        for marker, name in MILESTONE_STATES:
            if marker in rest:
                state = name
                break
        # The title is everything BEFORE the first state marker. Stripping the markers in place
        # instead leaves their sentence behind — "B — ✅ **SHIPPED**" became "B — SHIPPED", which
        # reads as part of the name. The marker is where the title ends, not a character to delete.
        cut = min((rest.index(mk) for mk, _ in MILESTONE_STATES if mk in rest), default=len(rest))
        title = re.sub(r"\*\*|`|~~", "", rest[:cut]).strip(" —-·")
        out.append({"id": mid, "title": title, "state": state})
    return out


def parse_roots(text: str) -> tuple[set[str], list[tuple[int, str, str]]]:
    """(root slugs, [(item, relation, root)]) out of gen-backlog-page.py. PURE."""
    return set(ROOTS_KEY.findall(text)), [
        (int(n), rel, root) for n, rel, root in DEPENDS_ROW.findall(text)
    ]


# ── inline markup is NOT implemented here. Backlog #71.
#
# What used to sit here: an `esc` that escaped `& < >` and `"` but NOT the apostrophe,
# and an `inline_md` that ran a code-span regex and then a bold regex over its output —
# so a `**` inside backticks was emphasised, and `*` was not supported at all.
#
# MEASURED 2026-08-30 over this page's own corpus (docs/anchors.md + docs/adr/*.md):
# 145 emphasis spans across 132 lines and 17 markdown links were being printed as
# literal asterisks and brackets, because the author wrote markup this renderer did not
# know. The apostrophe gap was real too — `esc` fed attribute values at :296 onward.
#
# The docstring here used to justify the narrowness: "goal lines are one sentence, not a
# document." The corpus disagrees, and one behaviour across all four pages was the
# decision (2026-08-30). Both names are kept because the call sites read well with them.
esc = page_markup.escape
inline_md = page_markup.render_inline


STEM_SUFFIX = re.compile(r"-(design|plan)$")


def doc_stem(name: str) -> str:
    """Filename -> the stem a spec and its plan share. PURE.

    `2026-08-29-x-design.md` and `2026-08-29-x.md` both give `2026-08-29-x`.

    ⚠ BOTH suffixes are stripped, measured rather than assumed. 2026-09-11: 91 specs end
    `-design` and 3 are bare; 91 plans are bare and 1 ends `-plan`.

    ⚠ GLOBAL vs ANCHOR-SCOPED, and the difference is large. Over ALL 187 documents this
    rule pairs 61 (stripping `-design` alone pairs 60). But `collect` calls
    `pair_documents` with ONE ANCHOR'S documents, and only 47 documents declare an anchor:
    anchor-scoped the corpus yields 41 threads of which just 6 have both halves. 35
    threads render one side absent — 21 with no plan, 14 with no spec — and that is
    correct, because an anchor-less document is invisible to this page by design. Do not
    read 61 as what the page shows.
    """
    base = name[:-3] if name.endswith(".md") else name
    return STEM_SUFFIX.sub("", base)


def pair_documents(docs: list[dict]) -> list[dict]:
    """Documents -> threads, newest stem first. PURE.

    A thread is {stem, spec, plan, docs}. EITHER SIDE MAY BE None and neither is an error:
    a spec with no plan is work not yet planned; a plan with no spec was written without
    one. The card draws them absent rather than omitting them.

    ⛔ A stem claimed by two specs would FUSE two threads invisibly. Measured 2026-09-11:
    0 stems are claimed by more than two files. The extra is kept in `docs` anyway, and
    `render_threads` renders it — the plan's review found the record keeping it while the
    page dropped it, which put the protection somewhere no reader could see.

    ⚠ The SAME dict object goes into `docs` and into the slot, which is what lets
    `render_threads` identify the extras by `is` rather than by a field that may be absent.
    """
    by_stem: dict[str, dict] = {}
    for d in docs:
        stem = doc_stem(d["name"])
        t = by_stem.setdefault(stem, {"stem": stem, "spec": None, "plan": None, "docs": []})
        t["docs"].append(d)
        slot = "plan" if d.get("kind") == "plan" else "spec"
        if t[slot] is None:
            t[slot] = d
    return sorted(by_stem.values(), key=lambda t: t["stem"], reverse=True)


PR_TAIL = re.compile(r"\(#(\d+)\)\s*$")
# ⚠ THREE ROUNDS OF PLAN REVIEW ON THIS ONE REGEX, each fix narrower than the class:
#   r1: `^docs/` alone missed CONTEXT.md and .agents/   -> 10 real mis-taggings
#   r2: adding a bare `README` matched README-generator.ts -> 4 the other way
#   r3: anchoring with `$` missed worker/CONTEXT.md      -> nested instruction docs
# `(.*/)?` is the class: an instruction document at ANY depth, whole basename only.
# Measured 0 wrong over 19 adversarial paths.
DOC_PATH = re.compile(
    r"^(docs/|\.remember/|\.agents/"
    r"|(.*/)?(README(\.md)?|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)$)")


def prs_from_log(lines) -> list[dict]:
    """`%H\\x01%as\\x01%s` lines -> PR records, newest first, deduped by number. PURE.

    ⚠ ANCHORED AT THE SUBJECT TAIL. `check-backlog-closure.py:107` already paid for this:
    an any-occurrence match fired on 10 of 18 ids, the tail rule on 1, a true positive.
    A commit with no tail was pushed direct to master and is not a PR.
    """
    out, seen = [], set()
    for line in lines:
        parts = line.split("\x01")
        if len(parts) != 3:
            continue
        sha, date, subject = parts
        m = PR_TAIL.search(subject)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append({"sha": sha, "num": m.group(1), "date": date, "subject": subject})
    return out


def files_are_code(files) -> bool:
    """True if any path lies outside this repo's documentation. PURE.

    ⛔ THIS IS A CLAIM ABOUT ONE COMMIT, NOT ABOUT A THREAD, and the spec retracted the
    stronger reading. Measured 2026-09-11: PR #147 (the ADR-0010 header backfill) touches
    ~26 documents plus three scripts, so this returns True on 22 of 47 documents and
    implemented none of them. The renderer therefore says `touched code` and shows each
    PR's document fan-out; it makes no implementation claim.
    """
    return any(f and not DOC_PATH.match(f) for f in files)


def thread_prs(thread: dict, history) -> dict:
    """Thread + a rel->PRs lookup -> the thread with `prs` and `pr_error`. PURE.

    The union over the thread's documents, deduped by PR number, newest first. `history`
    returns None when that document could not be read; ONE such document sets `pr_error`,
    because a shorter list that looks complete is worse than a stated gap.
    """
    merged: dict[str, dict] = {}
    error = False
    # ⚠ EVERY document on the thread, not just the two named slots. `pair_documents`
    # appends all of them to `docs` — spec and plan are members — so `docs` is a superset.
    # Iterating the slots meant a collision's third document never got a history, so a PR
    # reachable only through it vanished from the thread AND from the fan-out.
    for d in thread.get("docs") or [x for x in (thread.get("spec"), thread.get("plan")) if x]:
        if not d or not d.get("rel"):
            # A document the page cannot ADDRESS is not a document git failed to read, so
            # this does not set `pr_error`. Unreachable in production: every record built
            # in `collect` carries a `rel`.
            continue
        got = history(d["rel"])
        if got is None:
            error = True
            continue
        for p in got:
            merged.setdefault(p["num"], p)
    prs = sorted(merged.values(), key=lambda p: (p["date"], p["num"]), reverse=True)
    return {**thread, "prs": prs, "pr_error": error}


def pr_fanout(histories) -> dict[str, int]:
    """PR number -> how many ANCHORED documents reach it. PURE.

    ⚠ ANCHORED, and the qualifier is load-bearing. A document declaring no anchor never
    enters `collect`'s history cache, so it cannot be counted: `on 22 documents` means 22
    of the 47 documents this page can see, not 22 of 187. An unqualified denominator is
    the failure this project records most often.

    ⭐ WHY THIS EXISTS. A PR touching twenty-two documents did not implement any one of
    them. PR #147 backfilled `Anchor:` headers across the corpus and also touched three
    scripts, so it is `touched code` on 22 of 47 documents. The page renders this number
    beside each PR so a bulk edit is visible as one. A THRESHOLD WAS TESTED AND REJECTED:
    discounting PRs above 2 documents also discards #176, a genuine implementation, and
    the distribution (40/12/3/1/1 documents per PR) gives any cut one data point.

    Takes the per-document PR lists from the history cache, BEFORE any thread-level
    dedupe — counting threads under-reports every PR that touched both halves of one.
    """
    out: dict[str, int] = {}
    for prs in histories:
        if not prs:               # None (unreadable) and [] alike contribute nothing
            continue
        for num in {p["num"] for p in prs}:   # one vote per DOCUMENT, not per commit
            out[num] = out.get(num, 0) + 1
    return out


# ---------------------------------------------------------------- collection
def last_touched(path: pathlib.Path) -> str:
    """YYYY-MM-DD, or '' when git cannot answer. Rendered as '—' rather than omitted."""
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%as", "--", str(path)],
                           cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_pr_history(path: pathlib.Path, run=subprocess.run) -> list[dict] | None:
    """PRs that touched `path`, newest first — or None when git cannot answer.

    ⛔ None IS NOT []. None is CANNOT RUN. [] means git answered and named no PR — and for
    a path git has never tracked it also exits 0 with empty output, so [] is precisely
    "git names no PR for this path", which is a slightly weaker claim than "no PR touched
    this document". That is the right answer for an unmerged document.

    `--follow` keeps a renamed document's history. Measured 2026-09-11: it currently adds
    PRs for 0 of 47 documents, because nothing has been renamed — its justification is real
    but untested today. ⚠ Its known hazard is live regardless: rename detection is
    similarity-based, and this repo writes dated specs derived from predecessors, so
    --follow can jump into an ancestor's history and inherit its PRs.

    ⚠ `run` IS INJECTED so this layer is testable at all. Review found the CANNOT-RUN
    predicate here, the `--follow` flag and `git_show_files`' `.splitlines()` all UNMUTATED
    — not because they were forgotten, but because nothing could reach them: `annotate_code`
    took a `show=` parameter and these did not, so a mutation on them would have SURVIVED.
    An untestable rule is an unmutatable one, and this file's most load-bearing property —
    None IS NOT [] — lived on the wrong side of that line.
    """
    try:
        r = run(["git", "log", "--format=%H\x01%as\x01%s", "--follow", "--", str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return prs_from_log(r.stdout.splitlines())


def git_show_files(sha: str, run=subprocess.run) -> list[str] | None:
    """The file list of one commit, or None when git cannot answer.

    ⚠ `.splitlines()`, NOT `.split()`. `git show --name-only` emits one path per line, and
    a path containing a space would split into two entries whose tail matches no DOC_PATH
    branch — turning a documentation PR into a `code` one. No such path exists in this
    repo today; the plan review caught the two halves of one insertion disagreeing, with
    the sibling above already correct.
    """
    try:
        r = run(["git", "show", "--name-only", "--format=", "-1", sha],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def annotate_code(prs: list[dict], show=git_show_files) -> list[dict]:
    """Add `code`: True / False / None to each PR. `show` is injected so this is testable.

    None means the commit could not be read — NOT that it was documentation.
    """
    cache: dict[str, bool | None] = {}
    out = []
    for p in prs:
        sha = p["sha"]
        if sha not in cache:
            files = show(sha)
            cache[sha] = None if files is None else files_are_code(files)
        out.append({**p, "code": cache[sha]})
    return out


def collect(docs: pathlib.Path, gen_text: str) -> list[dict]:
    """One record per registered anchor. Reads the tree; parsing itself is pure above."""
    registry = parse_registry((docs / "anchors.md").read_text())
    if not registry:
        raise SystemExit("gen-goals-page: docs/anchors.md declares no anchors — nothing to render")

    adrs: dict[str, dict] = {}
    for p in sorted((docs / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")):
        adrs[p.name[:4]] = {**parse_adr(p.read_text()), "file": p.name,
                            "title": p.name[5:-3].replace("-", " ")}

    roots, depends = parse_roots(gen_text)
    # Not merely unused: a ROOTS key outside the registry means the backlog graph and the
    # anchor registry have drifted apart, which `check-anchors.py` R5 also enforces. This
    # page would silently render an empty backlog band instead, so it says so.
    stray = sorted(roots - {r['slug'] for r in registry})

    by_anchor: dict[str, list] = {r["slug"]: [] for r in registry}
    for sub in SUBDIRS:
        d = docs / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            h = parse_header(f.read_text())
            if h["anchor"] not in by_anchor:
                continue
            dm = DATED.match(f.name)
            by_anchor[h["anchor"]].append({
                "name": f.name, "rel": f"docs/{sub}/{f.name}", "goal": h["goal"],
                "dated": dm.group(1) if dm else "", "touched": last_touched(f),
                "kind": "plan" if "plans" in sub else "spec",
                "milestones": parse_milestones(f.read_text()),
            })

    # ⚠ MEASURED COST. This is NOT "double last_touched". `last_touched` is `git log -1`;
    # this is `git log --follow` over full history plus one `git show` per unique sha.
    # Measured 2026-09-11: build 2.4s -> 9.7s, about 4.5x, on a hook that fires on every
    # write to any spec, plan, ADR or the registry.
    hist_cache: dict[str, list[dict] | None] = {}

    def history(rel: str):
        if rel not in hist_cache:
            got = git_pr_history(ROOT / rel)
            hist_cache[rel] = None if got is None else annotate_code(got)
        return hist_cache[rel]

    out = []
    for r in registry:
        ds = sorted(by_anchor[r["slug"]], key=lambda d: d["dated"], reverse=True)
        spine = next((d for d in ds if d["milestones"]), None)
        out.append({
            **r,
            "docs": ds,
            "threads": [thread_prs(t, history) for t in pair_documents(ds)],
            "spine": spine,
            "adrs": [{"num": n, **adrs[n]} for n in re.findall(r"\d{4}", r["adrs"]) if n in adrs],
            "backlog": [(i, rel) for i, rel, root in depends if root == r["slug"]],
            "touched": max((d["touched"] for d in ds if d["touched"]), default=""),
        })
    out.sort(key=lambda a: (a["touched"], len(a["docs"])), reverse=True)

    # Global, so computed once across every anchor rather than per card. `hist_cache` is
    # fully populated by now — the comprehension above ran `history()` for every document.
    fan = pr_fanout(hist_cache.values())
    # The page's SIXTH source is the git log, and `regen-goals-page.sh` can only watch
    # files. Merging a PR changes what the Work band should say and fires no hook, because
    # a merge is not a Write. Rendering the sha it was derived from lets a reader see the
    # input rather than infer it. Guarded like every other git call here.
    try:
        _r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, timeout=20)
        head = (_r.stdout.strip() if _r.returncode == 0 else "") or "unknown"
    except (OSError, subprocess.SubprocessError):
        head = "unknown"
    for a in out:
        a["fanout"], a["head"] = fan, head

    if stray:
        # Loud, not silent: an empty backlog band would look like "this goal has no rows".
        print(f"⚠ ROOTS keys outside the registry, backlog bands will be empty for them: "
              f"{', '.join(stray)}", file=sys.stderr)
    return out


# ---------------------------------------------------------------- rendering
CSS = """
  :root{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;--ink-faint:#838a9b;
        --rule:#ddd9d0;--structure:#3f4bb8;--good:#1f7a55;--defect:#b03a2b;--pending:#8f6410;
        --structure-bg:#eceef9;--good-bg:#e7f2ec;--pending-bg:#f6efdd;
        --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
        --ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  @media (prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;
        --ink-soft:#b4bac9;--ink-faint:#7d8496;--rule:#2e313b;--structure:#8f9bf0;--good:#5fc394;
        --defect:#e88a76;--pending:#d9a441;--structure-bg:#1b1e33;--good-bg:#16261f;
        --pending-bg:#262013}}
  :root[data-theme="dark"]{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;--ink-soft:#b4bac9;
        --ink-faint:#7d8496;--rule:#2e313b;--structure:#8f9bf0;--good:#5fc394;--defect:#e88a76;
        --pending:#d9a441;--structure-bg:#1b1e33;--good-bg:#16261f;--pending-bg:#262013}
  :root[data-theme="light"]{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;
        --ink-faint:#838a9b;--rule:#ddd9d0;--structure:#3f4bb8;--good:#1f7a55;--defect:#b03a2b;
        --pending:#8f6410;--structure-bg:#eceef9;--good-bg:#e7f2ec;--pending-bg:#f6efdd}
  body{font-family:var(--ui);color:var(--ink);background:var(--bg);line-height:1.55;
       -webkit-font-smoothing:antialiased}
  .wrap{max-width:62rem;margin:0 auto;padding:3rem 1.5rem 5rem;display:flex;flex-direction:column;
        gap:2.5rem}
  h1,h2,h3{margin:0;line-height:1.2;text-wrap:balance}
  p{margin:0;max-width:68ch}
  code{font-family:var(--mono);font-size:.88em}
  .mast{display:flex;flex-direction:column;gap:.85rem;border-bottom:2px solid var(--ink);
        padding-bottom:1.3rem}
  .eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.13em;text-transform:uppercase;
           color:var(--ink-faint)}
  h1{font-size:clamp(1.8rem,4.4vw,2.6rem);font-weight:620;letter-spacing:-.022em}
  .standfirst{font-size:1.05rem;color:var(--ink-soft);max-width:62ch}
  .goal{background:var(--card);border:1px solid var(--rule);border-left:3px solid var(--structure);
        border-radius:3px;padding:1.25rem 1.4rem;display:flex;flex-direction:column;gap:1rem}
  .goal.quiet{border-left-color:var(--rule)}
  .ghead{display:flex;flex-wrap:wrap;align-items:baseline;gap:.6rem 1rem}
  .slug{font-family:var(--mono);font-size:1.02rem;font-weight:600;color:var(--structure)}
  .goal.quiet .slug{color:var(--ink)}
  .meta{font-family:var(--mono);font-size:.74rem;color:var(--ink-faint);margin-left:auto;
        font-variant-numeric:tabular-nums}
  .sentence{font-size:.98rem;color:var(--ink-soft);max-width:64ch}
  .band{display:flex;flex-direction:column;gap:.45rem}
  .blab{font-family:var(--mono);font-size:.68rem;letter-spacing:.11em;text-transform:uppercase;
        color:var(--ink-faint)}
  .chips{display:flex;flex-wrap:wrap;gap:.4rem}
  .chip{font-family:var(--mono);font-size:.73rem;padding:.22rem .5rem;border-radius:2px;
        border:1px solid var(--rule);color:var(--ink-soft);background:transparent}
  .chip.acc{color:var(--good);background:var(--good-bg);
            border-color:color-mix(in srgb,var(--good) 35%,transparent)}
  .chip.pro{color:var(--pending);background:var(--pending-bg);
            border-color:color-mix(in srgb,var(--pending) 35%,transparent)}
  .chip.sup{color:var(--ink-faint);text-decoration:line-through}
  .chip .amend{color:var(--pending);font-weight:600}
  .rungs{display:flex;flex-wrap:wrap;gap:.35rem}
  .rung{font-family:var(--mono);font-size:.73rem;padding:.24rem .55rem;border-radius:2px;
         border:1px solid var(--rule);color:var(--ink-faint);white-space:nowrap}
  .rung.done{color:var(--good);background:var(--good-bg);
             border-color:color-mix(in srgb,var(--good) 35%,transparent)}
  .rung.next{color:var(--structure);background:var(--structure-bg);font-weight:600;
             border-color:color-mix(in srgb,var(--structure) 45%,transparent)}
  .rung.deferred{color:var(--pending);background:var(--pending-bg);
                 border-color:color-mix(in srgb,var(--pending) 35%,transparent)}
  .absent{font-size:.86rem;color:var(--pending);font-style:italic}
  .docs{display:flex;flex-direction:column;gap:.3rem}
  .doc{display:grid;grid-template-columns:1fr auto;gap:.3rem 1rem;align-items:baseline;
       padding:.35rem 0;border-top:1px solid var(--rule)}
  .doc .n{font-family:var(--mono);font-size:.8rem;color:var(--ink)}
  .doc .t{font-family:var(--mono);font-size:.72rem;color:var(--ink-faint);
          font-variant-numeric:tabular-nums}
  .doc .g{grid-column:1/-1;font-size:.86rem;color:var(--ink-soft);max-width:66ch}
  .thread{border-top:1px solid var(--rule);padding:.4rem 0}
  .thread summary{cursor:pointer;font-family:var(--mono);font-size:.86rem;color:var(--ink)}
  .prline{display:flex;gap:.5rem;align-items:baseline;padding:.15rem 0 .15rem 1rem;
          flex-wrap:wrap}
  .prline .t{font-family:var(--mono);font-size:.72rem;color:var(--ink-faint);
             font-variant-numeric:tabular-nums}
  .prline .g{font-size:.84rem;color:var(--ink-soft);max-width:60ch}
  .tag{font-size:.72rem;padding:.05rem .35rem;border-radius:3px;font-family:var(--mono);
       background:var(--structure-bg);color:var(--structure)}
  .tag.docs{background:var(--pending-bg);color:var(--pending)}
  /* ⚠ --ink, NOT --ink-faint. Measured during review: --rule/--ink-faint is 2.45:1 in
     light and 3.47:1 in dark, both failing WCAG AA at this size — and this is the tag for
     CANNOT RUN, the one state the design argues hardest for. */
  .tag.unknown{background:var(--rule);color:var(--ink)}
  footer{border-top:1px solid var(--rule);padding-top:1.1rem;display:flex;flex-direction:column;
         gap:.6rem;font-size:.82rem;color:var(--ink-faint)}
  .legend{max-width:70ch}
  a{color:var(--structure)}\n  a.n{color:var(--structure);text-decoration:underline;text-underline-offset:3px;\n      text-decoration-color:color-mix(in srgb,var(--structure) 45%,transparent)}\n  a.n:hover{text-decoration-color:var(--structure)}\n  a.chip{text-decoration:none}\n  a.chip:hover{border-color:var(--structure)}
  :focus-visible{outline:2px solid var(--structure);outline-offset:2px}
"""


def excluded_count(total: int, shown: int) -> int:
    """Documents present but not rendered, because they declare no anchor. PURE.

    ⛔ REFUSES on shown > total. That can only mean the two numbers were counted over
    different populations, which is the most-recorded measurement defect in this repo, and
    a negative rendered as "-36 excluded" would be believed. The branch is unreachable in
    production — both counts come from SUBDIRS — so the case exercises it directly and the
    guard is there for a future caller, not for today's.
    """
    if shown > total:
        raise ValueError(f"shown ({shown}) exceeds total ({total}) — populations disagree")
    return total - shown


def render_threads(threads: list[dict], fanout: dict[str, int]) -> str:
    """The Work band's body: one collapsible block per spec/plan thread.

    ⚠ `<details>/<summary>` is this project's existing collapsible — 21 uses in
    `gen-dashboard.py`, 6 in `gen-backlog-page.py`, and none here before this. Reused.

    ⛔ MAKES NO IMPLEMENTATION CLAIM. The tag says what the commit TOUCHED; the fan-out
    says how many anchored documents it touched. An earlier draft said `code` and
    summarised `N code PR(s)`, which presented PR #147 — a 22-document header backfill —
    as the implementation of 22 different goals, and for 5 documents it was the only such
    PR, so those cards would also have suppressed the flag that was their real finding.
    """
    if not threads:
        return '<span class="absent">No spec or plan declares this goal.</span>'
    parts = []
    for t in threads:
        # TWO thread-level states, and they are not the same claim. CANNOT RUN beats
        # "git named no PR", because rendering a broken deriver as an honest absence is
        # the failure this project records most often.
        if t["pr_error"]:
            flag = '<span class="absent">history could not be read — treat as NOT MEASURED</span>'
        elif not t["prs"]:
            flag = '<span class="absent">no pull requests</span>'
        else:
            flag = f'<span class="t">{len(t["prs"])} PR(s)</span>'
        parts.append(f'<details class="thread"><summary>{esc(t["stem"])} {flag}</summary>')
        for side, missing in (("spec", "no spec"), ("plan", "no plan")):
            d = t.get(side)
            if d:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<a href="/src/{esc(d.get("rel", ""))}">'
                             f'{esc(d.get("name", "?"))}</a></div>')
            else:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<span class="absent">{missing}</span></div>')
        # ⛔ IDENTITY, NOT A KEY. `pair_documents` appends the SAME dict object it assigns
        # to the slot, so `is` is exact and needs no field. Keying on `d["rel"]` crashed on
        # a record without one; keying on `d.get("rel")` made every rel-less document
        # collapse to a single `None`, so the extra matched the spec and was dropped — the
        # case written to prove extras render proved the opposite.
        named = [x for x in (t.get("spec"), t.get("plan")) if x]
        for d in t.get("docs", []):
            if not any(d is x for x in named):
                parts.append(f'<div class="prline"><span class="absent">⚠ extra document '
                             f'on this stem</span>'
                             f'<a href="/src/{esc(d.get("rel", ""))}">'
                             f'{esc(d.get("name", "?"))}</a></div>')
        for p in t["prs"]:
            tag = ("unknown" if p.get("code") is None
                   else "touched code" if p["code"] else "docs only")
            cls = "unknown" if p.get("code") is None else ("code" if p["code"] else "docs")
            n = fanout.get(p["num"], 1)
            fan = f'<span class="t">on {n} documents</span>' if n > 1 else ""
            parts.append(f'<div class="prline"><span class="tag {cls}">{tag}</span>'
                         f'<span class="t">#{esc(p["num"])} · {esc(p["date"])}</span>{fan}'
                         f'<span class="g">{inline_md(p["subject"])}</span></div>')
        parts.append("</details>")
    return "\n".join(parts)


def render_goal(a: dict) -> str:
    quiet = "" if a["spine"] else " quiet"
    parts = [f'<article class="goal{quiet}">',
             '<div class="ghead">',
             f'<span class="slug">{esc(a["slug"])}</span>',
             f'<span class="meta">{len(a["docs"])} doc(s) · last touched '
             f'{esc(a["touched"] or "—")}</span>',
             "</div>",
             f'<p class="sentence">{inline_md(a["goal"])}</p>']

    parts.append('<div class="band"><span class="blab">Decisions</span><div class="chips">')
    if a["adrs"]:
        for adr in a["adrs"]:
            s = adr["status"].lower()
            cls = "acc" if s.startswith("accepted") else "pro" if s.startswith("proposed") else ""
            # PASSIVE ("superseded by") vs ACTIVE ("supersedes X") — the chip must not drop the
            # first. MEASURED on the first served run: ADR-0002 reads "accepted — PARTLY SUPERSEDED
            # by ADR-0006", and taking the text before the em-dash rendered it as a plain
            # "accepted", identical to ADR-0001. That is the renderer being narrower than the status
            # it renders, which is the same failure shape M3 spent its care avoiding.
            passive = re.search(r"\bsuperseded\b", s) is not None
            if passive:
                cls = "sup" if not s.startswith("accepted") else cls
            n = len(adr["amendments"])
            bits = []
            if passive:
                bits.append('<span class="amend">superseded</span>')
            if n:
                bits.append(f'<span class="amend">+{n} amended</span>')
            head = adr["status"].split("—")[0].split("(")[0].strip() or "no status"
            tail = (" " + " ".join(bits)) if bits else ""
            parts.append(f'<a class="chip {cls}" href="/src/docs/adr/{esc(adr["file"])}" '
                         f'title="{esc(adr["status"])}">'
                         f'ADR-{adr["num"]} · {esc(head)}{tail}</a>')
    else:
        parts.append('<span class="chip">no ADR recorded</span>')
    parts.append("</div></div>")

    parts.append('<div class="band"><span class="blab">Milestones</span>')
    if a["spine"]:
        parts.append('<div class="rungs">')
        for m in a["spine"]["milestones"]:
            parts.append(f'<span class="rung {m["state"]}" title="{esc(m["title"])}">'
                         f'{esc(m["id"])}</span>')
        parts.append("</div>")
        parts.append(f'<span class="doc t">spine: '
                     f'<a href="/src/{esc(a["spine"]["rel"])}">{esc(a["spine"]["name"])}</a></span>')
    else:
        parts.append('<span class="absent">No milestone plan — this goal has no spine to '
                     "read state from.</span>")
    parts.append("</div>")

    if a["backlog"]:
        parts.append('<div class="band"><span class="blab">Backlog hanging off it</span>'
                     '<div class="chips">')
        for num, rel in sorted(a["backlog"]):
            parts.append(f'<span class="chip">#{num} · {esc(rel)}</span>')
        parts.append("</div></div>")

    # The Documents band is GONE. Every document now sits inside the thread it belongs to,
    # which is what the reader asked for and also removes the band's guaranteed redundancy:
    # it reprinted the goal sentence under every document, identical each time, because a
    # document's `Goal:` line is by construction the same for every document under an
    # anchor. On the status-visibility card that was 20 copies of one sentence.
    n_pr = sum(len(t["prs"]) for t in a["threads"])
    parts.append(f'<div class="band"><span class="blab">Work</span>'
                 f'<span class="t">{len(a["threads"])} thread(s) · {n_pr} PR(s) · '
                 f'derived from git at {esc(a.get("head", "?")[:8])}</span>'
                 f'<div class="docs">')
    parts.append(render_threads(a["threads"], a.get("fanout", {})))
    parts.append("</div></div></article>")
    return "\n".join(parts)


def build(anchors: list[dict], sha: str, stamp: str, generated_at: str = "") -> str:
    spined = sum(1 for a in anchors if a["spine"])
    docs = sum(len(a["docs"]) for a in anchors)
    # ⚠ `total_docs` counts SUBDIRS — superpowers/specs and superpowers/plans — not all of
    # `docs/superpowers/`. Those are the only two subdirectories today, so a sentence
    # saying "under docs/superpowers/" would be true by coincidence of the tree's shape.
    # The rendered text names both directories instead.
    total_docs = sum(1 for sub in SUBDIRS for _ in (DOCS / sub).glob("*.md"))
    hidden = excluded_count(total_docs, docs)
    body = "\n".join(render_goal(a) for a in anchors)
    return f"""<title>Goals — what this project is pursuing, and where each stands</title>
<style>{CSS}
{page_chrome.chrome_css()}</style>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">Generated from the anchor headers · {esc(stamp)} · {esc(sha)}</div>
  <h1>Goals</h1>
  {page_chrome.chrome_bar("goals", generated_at)}
  <p class="standfirst">One card per goal, keyed by its <strong>anchor</strong> — the name that
    survives a rename. <strong>{len(anchors)}</strong> goals, <strong>{docs}</strong> documents,
    <strong>{spined}</strong> with a milestone spine.
    <span class="absent">{hidden} more under docs/superpowers/specs and /plans declare no
    anchor and are not shown.</span></p>
  <p class="standfirst">Nothing here is maintained by hand. Membership comes from the
    <code>Anchor:</code> headers, decision status from <code>docs/adr/</code> including its in-body
    amendment trail, milestone state from each spine's own headings, and dates from
    <code>git log</code>. Regenerate to update it; there is nothing else to edit.</p>
</header>
{body}
<footer>
  <p class="legend"><strong>What this page will not show:</strong> a review count per goal. Reviews
    are not anchored — 716 files named by round and subject, in three vocabularies — so counting them
    means keyword matching, which is the method that failed and caused the anchor system to exist. A
    number that is a lower bound of unknowable size is worse than an empty cell.</p>
  <p class="legend"><strong>“No milestone plan” is information, not a gap.</strong> It marks a goal
    being worked without a spine to read state from, and it is deliberately given a fixed slot rather
    than left blank.</p>
  <p class="legend">Decision: <code>docs/adr/0010-documents-declare-their-anchor.md</code> ·
    Registry: <code>docs/anchors.md</code> · Enforced by
    <code>scripts/check-anchors.py</code>.</p>
</footer>
</div>
<script>{page_chrome.chrome_script()}</script>
"""


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    cases = failures = 0

    def eq(label: str, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        # ⛔ THE FAILURE LINE IS A CONTRACT WITH THE MUTATION HARNESS, not a display choice.
        # `check-plan-code.parse_fail_names` reads a red case with `startswith("[FAIL] ")`
        # then `[7:]`, so a suite reporting failures any other way is one whose kills NOBODY
        # CAN SEE: every mutation reports "matched 0 red case(s)" while each one IS killed
        # by the case it names. This file printed `  ✗ <label>  got … want …` and paid all
        # 14 of its manifest entries for it on 2026-09-12.
        #
        # ⚠ THE COUNT HERE WAS WRITTEN FROM MEMORY AND WAS WRONG BY 3×, in the file whose
        # purpose is to be the durable record of this class. It said "the THIRD file to do
        # so, after gen-backlog-page.py and brief-compose.py". Enumerated in review r1 with
        # `git log -S'[FAIL] '` per file, this is the NINTH since 2026-09-06 — and the
        # THIRD with this exact `  ✗ {label}` shape, after `check-explainer-delivery.py`
        # and `check-gate-falsifiability.py`, both of which paid it five days earlier:
        #
        #   begin-plan · check-plan-progress (2026-09-06) · check-banner-armed (09-06)
        #   check-explainer-delivery · check-gate-falsifiability · check-function-revokes
        #   (2026-09-07) · gen-backlog-page · brief-compose (2026-09-10) · this file
        #
        # ⚠ AND "both of which paid AFTER a convention was written" was false for the first
        # of them. `portable-practices` §22 was introduced BY the same commit that fixed
        # `gen-backlog-page.py` (`050913f6`), so it cannot have paid after itself; only
        # `brief-compose.py` did. Six of the eight predate §22 entirely, and cite each
        # other and this parser rather than it. A convention did not hold, NINE times —
        # which is a much stronger argument for a mechanical guard than "three" was.
        # ⚠ THE NAME STAYS ALONE ON THE `[FAIL]` LINE, AND THE SPLIT IS DELIBERATE — this
        # is a THIRD producer shape and a reader is owed the reason. The canonical form
        # named at `check-plan-code.py:1395` is the single line `[FAIL] {name}: got {got!r}
        # want {want!r}`, and it parses because `parse_fail_names` truncates at the LAST
        # `": got "`. So an earlier draft of this comment was wrong to say that appending
        # the detail "matches no case name": with the canonical `": got "` separator it
        # matches fine. What does NOT parse is appending it with any OTHER separator —
        # which is what this file did (`  ✗ <label>  got …`, two spaces, no colon).
        # Keeping the detail on its own line is immune to both: the continuation does not
        # start with `[FAIL] `, so it is never read as a case, and the name cannot be
        # truncated by a case that happens to contain `": got "` — the hazard
        # `parse_fail_names` documents against itself.
        if ok:
            print(f"  ok     {label}")
        else:
            print(f"  [FAIL] {label}")
            print(f"    got {got!r} want {want!r}")
        failures += 0 if ok else 1

    reg = "| Anchor | ADR(s) | Goal |\n|---|---|---|\n| `alpha` | 0001, 0002 | A goal. |\n"
    eq("registry row parsed", parse_registry(reg),
       [{"slug": "alpha", "adrs": "0001, 0002", "goal": "A goal."}])
    eq("registry ignores the separator row", len(parse_registry(reg)), 1)
    eq("hollow registry yields nothing", parse_registry("# Nothing\n"), [])

    hdr = "# T\n\n> **Anchor:** `alpha` — **ADR:** 0001\n> **Goal:** A goal.\n"
    eq("header parsed", parse_header(hdr), {"anchor": "alpha", "adrs": ["0001"], "goal": "A goal."})
    eq("ADR none is empty, not ['none']",
       parse_header(hdr.replace("0001", "none"))["adrs"], [])
    eq("header below the fold is not read",
       parse_header("# T\n" + "\n" * 12 + hdr)["anchor"], None)

    adr = "---\nstatus: accepted 2026-08-24 (M3) — supersedes X\n---\n\n# T\n\n⟳ CORRECTED 2026-08-06 blah\n⟳ SUPERSEDED later\n"
    eq("adr status read", parse_adr(adr)["status"].startswith("accepted"), True)
    eq("in-body amendments counted", len(parse_adr(adr)["amendments"]), 2)
    eq("front matter is NOT counted as an amendment",
       parse_adr("---\nstatus: accepted — supersedes ADR-0002\n---\n\nbody\n")["amendments"], [])

    spine = ("### M1 — A ⛔ RE-SCOPED AND DEFERRED\n"
             "### M2 — B — ✅ **SHIPPED**\n"
             "### M3 — C ◀ **THE WORK RESUMES HERE**\n"
             "### M4 — D\n")
    ms = parse_milestones(spine)
    eq("milestones found", [m["id"] for m in ms], ["M1", "M2", "M3", "M4"])
    eq("states read off the headings' own markers",
       [m["state"] for m in ms], ["deferred", "done", "next", "todo"])
    eq("markers stripped from the title", ms[1]["title"], "B")
    eq("a doc with no milestones yields none", parse_milestones("# T\n\nprose\n"), [])

    gen = ('    "alpha": dict(\n        label="x",\n    ),\n'
           '    19: ("survives", "alpha",\n         "note"),\n'
           '    20: ("dissolved-by", "alpha", ""),\n')
    roots, dep = parse_roots(gen)
    eq("ROOTS key parsed", roots, {"alpha"})
    eq("DEPENDS rows parsed", dep, [(19, "survives", "alpha"), (20, "dissolved-by", "alpha")])

    # ⚠ The inline-markup case that stood here is DELETED, deliberately (backlog #71).
    # Inline rendering is `page_markup`'s behaviour now and is asserted by its own 73
    # cases; re-asserting it here would be a second copy of one rule, which is the defect
    # this slice exists to remove. What is NOT covered by deleting it — that this file is
    # still BOUND to page_markup rather than to a re-grown local copy — is a structural
    # property of all four generators at once, and belongs in one check, not four cases.

    eq("stem strips -design", doc_stem("2026-08-29-retarget-design.md"), "2026-08-29-retarget")
    eq("stem strips -plan", doc_stem("2026-08-28-dashboard-plan.md"), "2026-08-28-dashboard")
    eq("a bare name is already a stem", doc_stem("2026-08-29-retarget.md"), "2026-08-29-retarget")
    eq("only a TRAILING suffix is stripped",
       doc_stem("2026-09-01-design-review-notes.md"), "2026-09-01-design-review-notes")

    _s = {"name": "2026-08-29-x-design.md", "kind": "spec"}
    _p = {"name": "2026-08-29-x.md", "kind": "plan"}
    # LOAD-BEARING PAIR. The `None`-slot cases below are satisfied by a pair_documents
    # that never fills a slot at all; this case is what kills that. Do not delete one
    # without the other.
    eq("the thread names both halves",
       [pair_documents([_s, _p])[0][k]["name"] for k in ("spec", "plan")],
       ["2026-08-29-x-design.md", "2026-08-29-x.md"])
    eq("a spec and its plan share one thread", len(pair_documents([_s, _p])), 1)
    eq("a spec with no plan is a thread with an empty plan slot",   # pairs with the above
       pair_documents([_s])[0]["plan"], None)
    eq("a plan with no spec is a thread with an empty spec slot",   # pairs with the above
       pair_documents([_p])[0]["spec"], None)
    eq("threads sort newest stem first",
       [t["stem"] for t in pair_documents([{"name": "2026-01-01-a.md", "kind": "plan"}, _p])],
       ["2026-08-29-x", "2026-01-01-a"])
    _s2 = {"name": "2026-08-29-x-plan.md", "kind": "spec"}
    eq("a second document in a slot is kept, not dropped",
       len(pair_documents([_s, _p, _s2])[0]["docs"]), 3)

    _lg = ["aaa\x012026-08-29\x01Retire the plan dependency (#176)",
           "bbb\x012026-08-31\x01Asks state their choices (#186)",
           "ccc\x012026-08-31\x01Asks state their choices (#186)",
           "ddd\x012026-07-01\x01a direct commit with no PR"]
    eq("a squash subject yields its PR number",
       [p["num"] for p in prs_from_log(_lg)], ["176", "186"])
    eq("the date travels with the PR", prs_from_log(_lg)[0]["date"], "2026-08-29")
    eq("a commit with no PR tail is dropped", len(prs_from_log(_lg)), 2)
    eq("a malformed line is skipped, not crashed on", prs_from_log(["garbage"]), [])
    eq("a PR-looking number mid-subject is not the PR",
       prs_from_log(["e\x012026-01-01\x01mentions (#99) in passing, no tail"]), [])

    eq("a script path is code", files_are_code(["scripts/gen-goals-page.py"]), True)
    eq("one code file among docs makes it a code PR",
       files_are_code(["docs/backlog.md", "lib/storage.ts"]), True)
    eq("this repo's documentation outside docs/ is not code",
       files_are_code(["docs/x.md", ".remember/remember.md", "README.md",
                       "CONTEXT.md", "AGENTS.md", "CLAUDE.md",
                       ".agents/skills/brief/SKILL.md"]), False)
    # ⚠ Reported as a LIST, not chained with `and`: a regression names WHICH path class
    # broke rather than only that one did.
    eq("a code file whose name starts with a doc name is still code",
       [files_are_code([f]) for f in
        ("README-generator.ts", "CONTEXT.md.bak", "CLAUDE.md.old", "READMEs.tsx",
         "src/READMEs.tsx", "a/b/CONTEXT.md.ts")], [True] * 6)
    eq("an instruction document at any depth is not code",
       [files_are_code([f]) for f in
        ("worker/CONTEXT.md", "packages/api/AGENTS.md", "sub/dir/README.md")], [False] * 3)

    _prs = [{"sha": "aaa", "num": "186", "date": "2026-08-31", "subject": "s"},
            {"sha": "bbb", "num": "187", "date": "2026-08-31", "subject": "t"}]
    _shown = {"aaa": ["scripts/gen-dashboard.py", "docs/x.md"], "bbb": ["docs/x.md"]}
    _out = annotate_code(_prs, lambda sha: _shown.get(sha))
    eq("a PR touching a script is tagged code", _out[0]["code"], True)
    eq("a doc-only PR is not", _out[1]["code"], False)
    eq("an unreadable commit is unknown, not False",
       annotate_code(_prs[:1], lambda sha: None)[0]["code"], None)
    eq("annotate does not lose or reorder records", [p["num"] for p in _out], ["186", "187"])

    # ── THE CANNOT-RUN PRODUCER, REACHABLE AT LAST (review r1: HIGH-1 and MEDIUM-4) ──────
    # ⛔ `git_pr_history` returning None is the ONLY thing in this file that can ever set
    # `pr_error`, and THREE manifest entries defend what happens DOWNSTREAM of it. The
    # producer itself had no seam, no case and no mutation — so every weakening of it
    # SURVIVED, measured in review, because nothing could stand in for `subprocess`.
    # `annotate_code` has taken a `show=` parameter since it was written and these two did
    # not; their absence from the manifest was UNTESTABILITY, not completeness. An
    # untestable rule is an unmutatable one, and the property this file argues hardest for
    # — None IS NOT [] — was the one living on the wrong side of that line.
    class _R:
        def __init__(self, returncode, stdout=""):
            self.returncode, self.stdout = returncode, stdout

    _argv: list[list[str]] = []

    def _run_ok(cmd, **kw):
        _argv.append(cmd)
        return _R(0, "abc\x012026-09-01\x01a subject (#42)\n")

    def _run_rc1(cmd, **kw):
        return _R(1, "")

    def _run_boom(cmd, **kw):
        raise OSError("git is not on PATH")

    # ⚠ THE WHOLE RECORD, not just the numbers. `[p["num"] for p in …]` needs an `or []`
    # to type-check against `list | None`, and that default is the exact collapse the two
    # cases below exist to forbid — a guard written in the shape of the bug.
    #
    # ⚠ THE PATH VARIES ACROSS THESE CASES, AND THAT IS NOT COSMETIC. The first draft passed
    # `Path("x")` to all three, and `check-fixture-variation.py` refused it: a parameter
    # given one constant everywhere is one no case can tell apart FROM a constant, so the
    # clause that reads it is unguarded. Here that clause decides WHICH document's history
    # is fetched — pin it to a constant and every document on the page inherits one history.
    eq("a readable git log becomes PRs",
       git_pr_history(pathlib.Path("docs/superpowers/specs/a-design.md"), run=_run_ok),
       [{"sha": "abc", "num": "42", "date": "2026-09-01", "subject": "a subject (#42)"}])
    eq("the history is asked for the document it was given, not a fixed one",
       _argv[0][-1], "docs/superpowers/specs/a-design.md")
    # ⛔ THE TWO SENTINELS ARE NOT INTERCHANGEABLE. [] means git answered and named no PR;
    # None means git could not answer. `render_threads` draws those differently on purpose,
    # and collapsing them renders a failed deriver as a confident, honest-looking absence.
    eq("a nonzero git exit is CANNOT RUN, not an empty history",
       git_pr_history(pathlib.Path("docs/superpowers/plans/b.md"), run=_run_rc1), None)
    eq("a git that cannot be launched at all is CANNOT RUN",
       git_pr_history(pathlib.Path("README.md"), run=_run_boom), None)
    # ⚠ THIS ASSERTS THE FLAG, NOT THE BEHAVIOUR, and the limit is stated rather than
    # implied: proving renames are followed needs a repository containing a rename, and
    # this seam hands the stand-in a hard-coded `cwd=ROOT` it cannot redirect. What the
    # case catches is the flag's DELETION. The docstring already records that today's
    # corpus adds PRs for 0 of 47 documents, so nothing stronger is observable here.
    eq("the history query follows renames", "--follow" in _argv[0], True)

    # ⚠ `.splitlines()`, NOT `.split()` — the rule the docstring calls load-bearing and
    # which nothing asserted. A path with a space is the whole point: under `.split()`
    # `docs/a b.md` becomes `docs/a` and `b.md`, whose tails match no DOC_PATH branch, and
    # a documentation-only commit is then tagged as touching code.
    _show_argv: list[list[str]] = []

    def _show_ok(cmd, **kw):
        _show_argv.append(cmd)
        return _R(0, "docs/a b.md\nscripts/x.py\n")

    eq("a git show is split on LINES, so a path with a space stays one path",
       git_show_files("abc1234", run=_show_ok), ["docs/a b.md", "scripts/x.py"])
    # ⚠ Same rule as the path above: the sha varies across these three cases because a
    # constant would leave the clause that USES it unguarded, and that clause decides which
    # commit's file list is read — pin it and every PR inherits one verdict.
    eq("the file list is asked for the commit it was given, not a fixed one",
       _show_argv[0][-1], "abc1234")
    eq("a nonzero git show is CANNOT RUN, not an empty file list",
       git_show_files("def5678", run=_run_rc1), None)
    eq("a git show that cannot be launched is CANNOT RUN",
       git_show_files("beef999", run=_run_boom), None)

    # ⛔ `docs` IS POPULATED, and an empty one here was a case running through DEAD CODE.
    # `thread_prs` iterates `thread.get("docs") or [spec, plan]`, and `pair_documents`
    # appends EVERY document to `docs` — so for any thread `collect` builds, the right-hand
    # side of that `or` is unreachable in production. With `"docs": []` the two headline
    # cases below (the union/NEWEST-FIRST one, and the `pr_error` one) asserted the whole
    # rule against the fallback and never entered the loop production uses. Measured in
    # review r1 (MEDIUM-3): deleting ONLY the dead fallback reddened both of them.
    _sp = {"name": "s-design.md", "rel": "a"}
    _pl = {"name": "s.md", "rel": "b"}
    _t = {"stem": "s", "spec": _sp, "plan": _pl, "docs": [_sp, _pl]}
    # ⚠ REAL DATES. The plan's first draft used "d" and "e"; the sort is (date, num)
    # reverse=True, so "e" > "d" put PR 2 first while the case asserted ["1","2"]. With
    # real dates the ordering is observable and the case also dies if `sorted` is deleted.
    _hist = {"a": [{"sha": "x", "num": "1", "date": "2026-08-29", "subject": "u"}],
             "b": [{"sha": "x", "num": "1", "date": "2026-08-29", "subject": "u"},
                   {"sha": "y", "num": "2", "date": "2026-08-31", "subject": "v"}]}
    eq("a thread's PRs are the union over its documents, deduped, NEWEST FIRST",
       [p["num"] for p in thread_prs(_t, _hist.get)["prs"]], ["2", "1"])
    eq("one unreadable document poisons the thread's verdict",
       thread_prs(_t, lambda rel: None if rel == "b" else _hist["a"])["pr_error"], True)
    eq("a fully readable thread reports no error", thread_prs(_t, _hist.get)["pr_error"], False)
    eq("a thread with no documents has no PRs and no error",
       thread_prs({"stem": "s", "spec": None, "plan": None, "docs": []}, _hist.get),
       {"stem": "s", "spec": None, "plan": None, "docs": [], "prs": [], "pr_error": False})

    eq("fan-out counts the documents a PR touched",
       pr_fanout([[{"num": "147"}, {"num": "9"}], [{"num": "147"}]]), {"147": 2, "9": 1})
    # ⭐ DOCUMENTS, NOT THREADS. thread_prs dedupes a PR touching both halves of one
    # thread, so counting threads under-reports by one for every such PR while the
    # rendered label says "documents".
    eq("a PR touching both halves of one thread counts as two documents",
       pr_fanout([[{"num": "5"}], [{"num": "5"}]]), {"5": 2})
    eq("an unreadable document contributes nothing, and does not crash",
       pr_fanout([None, [{"num": "5"}]]), {"5": 1})
    # ⭐ A collision's third document must get a history too. Iterating only the two
    # named slots meant a PR reachable ONLY through the extra vanished from the thread
    # and from the fan-out.
    _t3 = {"stem": "s", "spec": {"name": "a-design.md", "rel": "a"},
           "plan": {"name": "a.md", "rel": "b"},
           "docs": [{"name": "a-design.md", "rel": "a"}, {"name": "a.md", "rel": "b"},
                    {"name": "a-plan.md", "rel": "c"}]}
    _h3 = {"a": [], "b": [],
           "c": [{"sha": "z", "num": "7", "date": "2026-09-01", "subject": "w"}]}
    eq("a PR reachable only through a collision's extra document is still found",
       [p["num"] for p in thread_prs(_t3, _h3.get)["prs"]], ["7"])

    _fan = {"186": 1, "187": 1, "188": 1, "147": 22, "189": 2}
    # ⚠ THREE PRs, one per tag. With only two, the case named "only the three measured
    # tags can be rendered" was satisfied by a renderer emitting a fourth label for the
    # third state — mutation-verified during review: renaming the `unknown` branch stayed
    # GREEN. It constrained two of the three it claimed.
    _th = [{"stem": "2026-08-31-asks", "spec": {"name": "a-design.md", "rel": "ra"},
            "plan": {"name": "a.md", "rel": "rb"}, "docs": [], "pr_error": False,
            "prs": [{"num": "186", "date": "2026-08-31", "subject": "impl", "code": True},
                    {"num": "187", "date": "2026-08-31", "subject": "docs", "code": False},
                    {"num": "188", "date": "2026-08-30", "subject": "unread", "code": None}]}]
    _h = render_threads(_th, _fan)
    eq("the thread renders inside a details element", "<details" in _h, True)
    # ⭐ THE CASE THE USER ASKED FOR: two PRs on one thread must LOOK different.
    eq("the PRs are distinguishable in the markup",
       (_h.count(">touched code<"), _h.count(">docs only<")), (1, 1))
    # ⚠ THE CLASS IS CAPTURED, NOT JUST MATCHED. This read `class="tag [a-z]+"` with the
    # capture group on the TEXT alone, so the class was unconstrained: the `cls` branch
    # could drop `unknown` and paint an unreadable PR in the `docs` colour while this case
    # stayed green (review r1, MEDIUM-2 — measured as a SURVIVING weakening). The comment
    # above records the same defect being found and fixed on the TAG half; the CLASS half
    # was left in exactly the state it describes. Pairs, so the two cannot drift apart.
    eq("only the three measured tags can be rendered, each in its OWN class",
       sorted(set(re.findall(r'<span class="tag ([a-z]+)">([^<]+)</span>', _h))),
       [("code", "touched code"), ("docs", "docs only"), ("unknown", "unknown")])
    eq("a PR whose files could not be read is tagged unknown", ">unknown<" in _h, True)
    eq("a single-document thread renders no fan-out", _h.count(" documents</span>"), 0)
    # ⭐ THE RETRACTION, ASSERTED: a 22-document PR is shown as a bulk edit.
    _bulk = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
              "docs": [], "pr_error": False,
              "prs": [{"num": "147", "date": "2026-08-01", "subject": "backfill",
                       "code": True}]}]
    eq("a PR touching many documents renders its fan-out",
       "on 22 documents" in render_threads(_bulk, _fan), True)
    # ⭐ THE BOUNDARY THE RULE ACTUALLY TURNS ON. `_fan` held only 1 and 22, so `n > 1`
    # could become `n > 2` and every TWO-document PR would silently lose its fan-out with
    # this suite green (review r1, MEDIUM-5 — measured as a SURVIVING weakening). Two is
    # not a corner case here: the distribution recorded at `pr_fanout` is 40/12/3/1/1
    # documents per PR, so the 2-bucket is the largest non-singleton class on the page.
    _pair = [{"stem": "p", "spec": {"name": "p-design.md", "rel": "rp"}, "plan": None,
              "docs": [], "pr_error": False,
              "prs": [{"num": "189", "date": "2026-09-02", "subject": "two",
                       "code": True}]}]
    eq("a two-document PR is over the fan-out threshold, not on the wrong side of it",
       "on 2 documents" in render_threads(_pair, _fan), True)
    eq("the page makes no implementation claim about any tag",
       "implementation" in render_threads(_bulk, _fan).lower(), False)

    _empty = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
               "docs": [], "prs": [], "pr_error": False}]
    eq("a missing plan is drawn as absent, not omitted",
       "no plan" in render_threads(_empty, {}), True)
    eq("a thread git named no PR for says so",
       "no pull requests" in render_threads(_empty, {}), True)
    # LOAD-BEARING PAIR. The negative below is an absence assertion and passes on an empty
    # string; the positive above it is what kills that. Neither may be deleted alone.
    _broken = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                "docs": [], "prs": [], "pr_error": True}]
    eq("an unreadable history says so instead of showing nothing",
       "could not be read" in render_threads(_broken, {}), True)
    eq("and it does NOT also claim there are no pull requests",
       "no pull requests" in render_threads(_broken, {}), False)

    # ⭐ A collision's extra document must be RENDERED, not merely kept in the record.
    _sp = {"name": "s-design.md", "rel": "r"}
    _ex = {"name": "s-plan.md", "rel": "rx"}
    _coll = [{"stem": "s", "spec": _sp, "plan": None, "docs": [_sp, _ex],
              "prs": [], "pr_error": False}]
    eq("an extra document on a stem is rendered, not silently dropped",
       ("extra document" in render_threads(_coll, {})
        and "s-plan.md" in render_threads(_coll, {})), True)
    # ⚠ Identity, not a key: keying on `d.get("rel")` made every rel-less document
    # collapse to one `None`, so the extra matched the spec and vanished. This fixture
    # has no `rel` at all and is what caught it.
    _sp2 = {"name": "s.md"}
    _ex2 = {"name": "other.md"}
    _norel = [{"stem": "s", "spec": _sp2, "plan": None, "docs": [_sp2, _ex2],
               "prs": [], "pr_error": False}]
    # ⚠ NAMED FOR WHAT IT ASSERTS. This case said "does not crash the renderer", which
    # describes the FIRST bug in the comment above (`d["rel"]`, a KeyError) while its
    # assertion is a PRESENCE check that catches the SECOND (`d.get("rel")`, the silent
    # collapse). Both reviewers landed on it independently in r1, because the manifest
    # entry pointing here told a reader it tested crash-safety when it tests presence.
    eq("a rel-less extra is identified by identity, not collapsed into the spec",
       "extra document" in render_threads(_norel, {}), True)
    eq("and the rel-less extra is still named once",
       render_threads(_norel, {}).count("other.md"), 1)

    eq("no threads renders the absence, not an empty box",
       "No spec or plan" in render_threads([], {}), True)

    def _raises(fn, exc) -> bool:
        try:
            fn()
        except exc:
            return True
        return False

    # ⚠ Deliberately SYNTHETIC numbers. Using the live 187/47 here would read as a corpus
    # claim and invite someone to "correct" it when the corpus moves. This is arithmetic.
    eq("the excluded count is total minus shown", excluded_count(10, 4), 6)
    eq("nothing excluded reads as zero", excluded_count(4, 4), 0)
    eq("showing more than exist is a refusal, not a negative",
       _raises(lambda: excluded_count(4, 10), ValueError), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--fragment-only", type=pathlib.Path,
                    help="write the bare fragment here and skip composing the tray")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    gen = ROOT / "scripts" / "gen-backlog-page.py"
    if not (DOCS / "anchors.md").is_file() or not gen.is_file():
        print("CANNOT RUN — docs/anchors.md or scripts/gen-backlog-page.py is missing. "
              "Treat this as NOT RUN.", file=sys.stderr)
        return 2

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip() or "unknown"
    stamp = subprocess.run(["git", "log", "-1", "--format=%as"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip() or "unknown"

    anchors = collect(DOCS, gen.read_text())
    fragment = build(anchors, sha, stamp,
                     page_chrome.provenance(
                         _dt.datetime.now().strftime('%Y-%m-%d %H:%M'), ROOT))

    if args.fragment_only:
        page_chrome.assert_wired(fragment, "gen-goals-page.py")
        args.fragment_only.write_text(fragment)
        print(f"wrote fragment {args.fragment_only}")
        return 0

    # The Ask tray is LIFTED by brief-compose.py, never re-implemented here — one tray, three
    # page-producing callers. Restating it would be the third copy the delivery-loop extraction
    # (2026-08-24) exists to prevent.
    with tempfile.TemporaryDirectory() as td:
        frag = pathlib.Path(td) / "goals-fragment.html"
        page_chrome.assert_wired(fragment, "gen-goals-page.py")
        frag.write_text(fragment)
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "brief-compose.py"),
             "--content", str(frag), "--slug", "goals", "--out", str(args.out),
             # Without this the composer defaults the document title to "Brief". MEASURED on the
             # first served run — the tab read "Brief" while the page was the goals index.
             "--title", "Goals — what this project is pursuing, and where each stands"],
            cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 or not args.out.is_file():
        print(f"FAILED — brief-compose did not write {args.out}:\n{r.stdout}{r.stderr}",
              file=sys.stderr)
        return 1

    spined = sum(1 for a in anchors if a["spine"])
    print(f"wrote {args.out}  ({len(anchors)} goals, "
          f"{sum(len(a['docs']) for a in anchors)} docs, {spined} with a spine)")
    print("     http://127.0.0.1:7391/goals   (start: python3 scripts/explainer-serve.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

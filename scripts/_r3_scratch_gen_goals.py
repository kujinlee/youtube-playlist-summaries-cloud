#!/usr/bin/env python3
"""One always-visible page: every GOAL this project is pursuing, and where each one stands.

    python3 scripts/gen-goals-page.py              # -> ~/explainers/goals.html, served at /goals
    python3 scripts/gen-goals-page.py --fragment-only <path>
    python3 scripts/gen-goals-page.py --self-test  # 15 cases, pure functions only

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
    """Filename -> the stem a spec and its plan share. PURE."""
    base = name[:-3] if name.endswith(".md") else name
    return STEM_SUFFIX.sub("", base)


def pair_documents(docs: list[dict]) -> list[dict]:
    """Documents -> threads, newest stem first. PURE."""
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
DOC_PATH = re.compile(
    r"^(docs/|\.remember/|\.agents/|(README(\.md)?|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)$)")


def prs_from_log(lines) -> list[dict]:
    """`%H\x01%as\x01%s` lines -> PR records, newest first, deduped by number. PURE."""
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
    """True if any path lies outside this repo's documentation. PURE."""
    return any(f and not DOC_PATH.match(f) for f in files)


def thread_prs(thread: dict, history) -> dict:
    """Thread + a rel->PRs lookup -> the thread with `prs` and `pr_error`. PURE."""
    merged: dict[str, dict] = {}
    error = False
    for side in ("spec", "plan"):
        d = thread.get(side)
        if not d:
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
    """PR number -> how many DOCUMENTS reach it. PURE."""
    out: dict[str, int] = {}
    for prs in histories:
        if not prs:
            continue
        for num in {p["num"] for p in prs}:
            out[num] = out.get(num, 0) + 1
    return out


def excluded_count(total: int, shown: int) -> int:
    """Documents present but not rendered, because they declare no anchor. PURE."""
    if shown > total:
        raise ValueError(f"shown ({shown}) exceeds total ({total}) — populations disagree")
    return total - shown


# ---------------------------------------------------------------- collection
def last_touched(path: pathlib.Path) -> str:
    """YYYY-MM-DD, or '' when git cannot answer. Rendered as '—' rather than omitted."""
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%as", "--", str(path)],
                           cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_pr_history(path: pathlib.Path) -> list[dict] | None:
    """PRs that touched `path`, newest first — or None when git cannot answer."""
    try:
        r = subprocess.run(
            ["git", "log", "--format=%H\x01%as\x01%s", "--follow", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return prs_from_log(r.stdout.splitlines())


def git_show_files(sha: str) -> list[str] | None:
    """The file list of one commit, or None when git cannot answer."""
    try:
        r = subprocess.run(["git", "show", "--name-only", "--format=", "-1", sha],
                           cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def annotate_code(prs: list[dict], show=git_show_files) -> list[dict]:
    """Add `code`: True / False / None to each PR."""
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
    fan = pr_fanout(hist_cache.values())
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
  footer{border-top:1px solid var(--rule);padding-top:1.1rem;display:flex;flex-direction:column;
         gap:.6rem;font-size:.82rem;color:var(--ink-faint)}
  .legend{max-width:70ch}
  a{color:var(--structure)}\n  a.n{color:var(--structure);text-decoration:underline;text-underline-offset:3px;\n      text-decoration-color:color-mix(in srgb,var(--structure) 45%,transparent)}\n  a.n:hover{text-decoration-color:var(--structure)}\n  a.chip{text-decoration:none}\n  a.chip:hover{border-color:var(--structure)}
  :focus-visible{outline:2px solid var(--structure);outline-offset:2px}
"""


def render_threads(threads: list[dict], fanout: dict[str, int]) -> str:
    """The WORK band's body: one collapsible block per spec/plan thread."""
    if not threads:
        return '<span class="absent">No spec or plan declares this goal.</span>'
    parts = []
    for t in threads:
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
                             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
            else:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<span class="absent">{missing}</span></div>')
        named = {d.get("rel") for d in (t.get("spec"), t.get("plan")) if d}
        for d in t.get("docs", []):
            if d.get("rel") not in named:
                parts.append(f'<div class="prline"><span class="absent">⚠ extra document '
                             f'on this stem</span>'
                             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
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
        print(("  ✓ " if ok else "  ✗ ") + label + ("" if ok else f"  got {got!r} want {want!r}"))
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
    # ⭐ ROUND 1 H3 — F7 had ALREADY FIRED before the code was written. Measured over the
    # last 400 PRs: 10 commits whose only non-`docs/` files are markdown — CONTEXT.md and
    # .agents/skills/**. Each was tagged `code`. A single-path case cannot see this class;
    # this one goes red if DOC_PATH loses ANY branch.
    eq("this repo's documentation outside docs/ is not code",
       files_are_code(["docs/x.md", ".remember/remember.md", "README.md",
                       "CONTEXT.md", "AGENTS.md", "CLAUDE.md",
                       ".agents/skills/brief/SKILL.md"]), False)
    # ⭐ ROUND 2 H. The round-1 fix for the above created the OPPOSITE defect: an
    # unanchored `README` also matches `README-generator.ts`, so a real implementation
    # rendered as `docs only`. Latent (no such path exists yet) and fixed by anchoring each
    # literal with `$`. This case dies the moment an anchor is dropped.
    eq("a code file whose name STARTS with a doc name is still code",
       files_are_code(["README-generator.ts"]) and files_are_code(["CONTEXT.md.bak"])
       and files_are_code(["CLAUDE.md.old"]) and files_are_code(["READMEs.tsx"]), True)

    _prs = [{"sha": "aaa", "num": "186", "date": "2026-08-31", "subject": "s"},
            {"sha": "bbb", "num": "187", "date": "2026-08-31", "subject": "t"}]
    _shown = {"aaa": ["scripts/gen-dashboard.py", "docs/x.md"], "bbb": ["docs/x.md"]}
    _out = annotate_code(_prs, lambda sha: _shown.get(sha))
    eq("a PR touching a script is tagged code", _out[0]["code"], True)
    eq("a doc-only PR is not", _out[1]["code"], False)
    eq("an unreadable commit is unknown, not False",
       annotate_code(_prs[:1], lambda sha: None)[0]["code"], None)
    eq("annotate does not lose or reorder records", [p["num"] for p in _out], ["186", "187"])

    _t = {"stem": "s", "spec": {"name": "s-design.md", "rel": "a"},
          "plan": {"name": "s.md", "rel": "b"}, "docs": []}
    # ⚠ REAL DATES. Round 1 Blocking B1: the first version used "d" and "e", and since the
    # sort is (date, num) reverse=True, "e" > "d" put PR 2 first — the case asserted
    # ["1","2"] and the implementation produced ["2","1"]. With real dates the ordering is
    # observable, and this case now also dies if `sorted(...)` is deleted.
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
    # ⭐ ROUND 2 H. This is the case that distinguishes documents from threads: one PR
    # touching BOTH halves of one thread is TWO documents, and the thread-level dedupe
    # would have reported 1 under the label "on N documents".
    eq("a PR touching both halves of one thread counts as two documents",
       pr_fanout([[{"num": "5"}], [{"num": "5"}]]), {"5": 2})
    eq("an unreadable document contributes nothing, and does not crash",
       pr_fanout([None, [{"num": "5"}]]), {"5": 1})

    _fan = {"186": 1, "187": 1, "147": 22}
    _th = [{"stem": "2026-08-31-asks", "spec": {"name": "a-design.md", "rel": "ra"},
            "plan": {"name": "a.md", "rel": "rb"}, "docs": [], "pr_error": False,
            "prs": [{"num": "186", "date": "2026-08-31", "subject": "impl", "code": True},
                    {"num": "187", "date": "2026-08-31", "subject": "docs", "code": False}]}]
    _h = render_threads(_th, _fan)
    eq("the thread renders inside a details element", "<details" in _h, True)
    # ⭐ THE CASE THE USER ASKED FOR: two PRs on one thread must LOOK different.
    eq("the two PRs are distinguishable in the markup",
       _h.count(">touched code<") == 1 and _h.count(">docs only<") == 1, True)
    # ⭐ ROUND 2 M. This was `"implement" not in html`, which passes for `shipped`,
    # `done` or `landed` — the same false claim in other words. Pinning the SET of rendered
    # tag texts fails on any label that is not one of the three measured states.
    eq("only the three measured tags can be rendered",
       sorted(set(re.findall(r'<span class="tag [a-z]+">([^<]+)</span>', _h))),
       ["docs only", "touched code"])
    # ⭐ THE RETRACTION, ASSERTED: a 22-document PR is shown as a bulk edit.
    _bulk = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
              "docs": [], "pr_error": False,
              "prs": [{"num": "147", "date": "2026-08-01", "subject": "backfill", "code": True}]}]
    eq("a PR touching many documents renders its fan-out",
       "on 22 documents" in render_threads(_bulk, _fan), True)
    # ⭐ ROUND 2 L. This was `"on 1 documents" not in html`, which a renderer saying
    # "on 1 document" passes. Counting the fan-out spans cannot be evaded by wording.
    eq("only the multi-document PR renders a fan-out",
       render_threads(_bulk, _fan).count(" documents</span>"), 1)
    eq("and a single-document thread renders none", _h.count(" documents</span>"), 0)

    _empty = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
               "docs": [], "prs": [], "pr_error": False}]
    eq("a missing plan is drawn as absent, not omitted", "no plan" in render_threads(_empty, {}), True)
    eq("a thread git found no PR for says so", "no pull requests" in render_threads(_empty, {}), True)

    # LOAD-BEARING PAIR. The negative below is an absence assertion and passes on an empty
    # string; the positive above it is what kills that. Neither may be deleted alone.
    _broken = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                "docs": [], "prs": [], "pr_error": True}]
    eq("an unreadable history says so instead of showing nothing",
       "could not be read" in render_threads(_broken, {}), True)
    eq("and it does NOT also claim there are no pull requests",
       "no pull requests" in render_threads(_broken, {}), False)

    _unknown = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                 "docs": [], "pr_error": False,
                 "prs": [{"num": "9", "date": "d", "subject": "s", "code": None}]}]
    # `>unknown<` asserts the TEXT NODE. Round 1: `"unknown" in html` also matched the CSS
    # class, so it passed however the visible label changed.
    eq("a PR whose files could not be read is tagged unknown",
       ">unknown<" in render_threads(_unknown, {}), True)

    # ⭐ ROUND 1 H1. Task 1 keeps a collision's extra document; the page must show it.
    _extra = {"name": "s-plan.md", "rel": "rx", "kind": "spec"}
    _coll = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
              "docs": [{"name": "s-design.md", "rel": "r"}, _extra],
              "prs": [], "pr_error": False}]
    eq("an extra document on a stem is rendered, not silently dropped",
       "extra document" in render_threads(_coll, {}) and "s-plan.md" in render_threads(_coll, {}),
       True)
    # ⭐ ROUND 2 L. `d["rel"]` raised KeyError on a record without one. `.get` throughout.
    eq("a document record with no rel does not crash the renderer",
       "extra document" in render_threads(
           [{"stem": "s", "spec": {"name": "s.md"}, "plan": None,
             "docs": [{"name": "other.md"}], "prs": [], "pr_error": False}], {}), True)

    eq("no threads renders the absence, not an empty box",
       "No spec or plan" in render_threads([], {}), True)

    def _raises(fn, exc) -> bool:
        try:
            fn()
        except exc:
            return True
        return False

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

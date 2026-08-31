#!/usr/bin/env python3
"""One always-visible page: every GOAL this project is pursuing, and where each one stands.

    python3 scripts/gen-goals-page.py              # -> ~/explainers/goals.html, served at /goals
    python3 scripts/gen-goals-page.py --fragment-only <path>
    python3 scripts/gen-goals-page.py --self-test  # 16 cases, pure functions only

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


# ---------------------------------------------------------------- collection
def last_touched(path: pathlib.Path) -> str:
    """YYYY-MM-DD, or '' when git cannot answer. Rendered as '—' rather than omitted."""
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%as", "--", str(path)],
                           cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


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

    out = []
    for r in registry:
        ds = sorted(by_anchor[r["slug"]], key=lambda d: d["dated"], reverse=True)
        spine = next((d for d in ds if d["milestones"]), None)
        out.append({
            **r,
            "docs": ds,
            "spine": spine,
            "adrs": [{"num": n, **adrs[n]} for n in re.findall(r"\d{4}", r["adrs"]) if n in adrs],
            "backlog": [(i, rel) for i, rel, root in depends if root == r["slug"]],
            "touched": max((d["touched"] for d in ds if d["touched"]), default=""),
        })
    out.sort(key=lambda a: (a["touched"], len(a["docs"])), reverse=True)
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

    parts.append('<div class="band"><span class="blab">Documents</span><div class="docs">')
    for d in a["docs"]:
        parts.append(f'<div class="doc"><a class="n" href="/src/{esc(d["rel"])}">'
                     f'{esc(d["name"])}</a>'
                     f'<span class="t">{esc(d["kind"])} · {esc(d["touched"] or "—")}</span>'
                     f'<span class="g">{inline_md(d["goal"])}</span></div>')
    parts.append("</div></div></article>")
    return "\n".join(parts)


def build(anchors: list[dict], sha: str, stamp: str, generated_at: str = "") -> str:
    spined = sum(1 for a in anchors if a["spine"])
    docs = sum(len(a["docs"]) for a in anchors)
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
    <strong>{spined}</strong> with a milestone spine.</p>
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

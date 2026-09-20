#!/usr/bin/env python3
"""Render `docs/features.md` as /features — what this system does, and what it deliberately does not.

    python3 scripts/gen-features-page.py              # -> ~/explainers/features.html, served at /features
    python3 scripts/gen-features-page.py --fragment-only <path>
    python3 scripts/gen-features-page.py --self-test  # 12 cases

WHY THIS EXISTS
---------------
Asked on 2026-09-19 *"where can I find currently implemented behaviours?"*, the honest answer was
nowhere: the knowledge existed in six places at once — a spec holding the original intent, a PR body
holding one delta, review documents holding point-in-time findings, a 142-row backlog holding the
gaps, a dashboard holding what changed while you were away. Every one of those records a MOMENT.
None answers *what is true now*.

A HUB OF LINKS, NOT A SYNTHESIS — which is the property that keeps it honest
---------------------------------------------------------------------------
Everything on this page except one `for:` sentence per node is DERIVED. A second copy of a fact can
disagree with the first, and this project has measured that repeatedly; a link cannot. So:

  the tree, the prose   <- docs/features.md          (the only hand-written surface)
  known gaps            <- docs/backlog.md rows whose (area) the node claims
  decisions             <- docs/anchors.md's ADR column, per anchor the node claims
  specs and plans       <- the `Anchor:` headers on docs/superpowers/{specs,plans}/*.md (ADR-0010)
  reviews               <- docs/reviews/** whose filename stem contains the node slug
  recent changes        <- git log subjects carrying (#N)

⚠ TWO OF THOSE SIX ARE KEYWORD MATCHES AND ARE THEREFORE LOWER BOUNDS — reviews (stem contains the
slug) and recent changes (the slug's own words appear in the subject). `gen-goals-page.py` refuses
to show a review COUNT for exactly this reason: "a number that is a lower bound of unknowable size
is worse than an empty cell". The difference here is that these are LINKS, not counts — a reader can
see what matched and judge it — so the page shows them and says what the rule was, rather than
implying completeness. MEASURED 2026-09-19 over 286 PR subjects and 26 nodes: 11 subject matches
across 8 nodes. That sparseness is a fact about the corpus, not a bug in the match.

⚠ THE BUILD TIME IS RENDERED, AND IT IS ABOUT ONE SECTION IN PARTICULAR. `git log` is the one source
no file-watcher can see: merging a PR changes what "recent changes" should say and fires no hook,
because a merge is not a Write. Every other source is a file the regen hook watches. So the page
prints when it was built, which is the only way a reader can tell how far that one section may have
fallen behind.

⛔ REUSES THE SHIPPED BACKLOG PARSER rather than re-deriving "which row, what severity, what is it
about". `gen-backlog-page.parse` already owns that rule — including the `(was 🟡)` and `**Title**`
decoration seven rows carry — and a second implementation of one rule drifts. It is imported
lazily, so `--self-test` stays pure and a broken sibling cannot take this suite down with it.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
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
DEFAULT_OUT = pathlib.Path.home() / "explainers" / "features.html"
SUBDIRS = ("superpowers/specs", "superpowers/plans")


def _load(stem: str):
    """Import a hyphenated sibling script. A plain `import` cannot name these files."""
    spec = importlib.util.spec_from_file_location(
        stem.replace("-", "_"), pathlib.Path(__file__).with_name(f"{stem}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check_features = _load("check-features")
parse_features, Node = check_features.parse_features, check_features.Node

esc = page_markup.escape
inline_md = page_markup.render_inline

ANCHOR_ROW = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]*?)\s*\|")
DOC_ANCHOR = re.compile(r"^>\s*\*\*Anchor:\*\*\s*`([a-z0-9-]+)`")
PR_TAIL = re.compile(r"\(#\d+\)\s*$")

def sev_glyphs(severity: dict[str, str]) -> dict[str, str]:
    """`gen-backlog-page`'s glyph->name map, INVERTED, plus the one name it has no glyph for. PURE.

    ⛔ THIS WAS A LITERAL, AND THE COMMENT ABOVE IT SAID IT WAS DERIVED. Review round 1, and the
    finding is sharper than the defect: the two maps were identical, so there was nothing to fix —
    what the sentence did was tell the next reader asking *"is this a second copy?"* that it was
    not, and stop them looking. The drift it invited was silent, because the caller reads through
    `.get(sev, "·")` and an unknown severity degrades to a bare dot with no error.

    `parse` reports a severity by NAME (`crit`), and only the glyph belongs on this page, so the
    map has to be turned round. Inverting it in code is the difference between a claim and a fact.

    ⚠ `none` is NOT in the upstream map and cannot be: it is what `parse` returns for a row with no
    marker at all. It is therefore a default here, placed FIRST so that an upstream entry for the
    same name would win rather than be silently overridden by this file's guess.
    """
    return {"none": "·"} | {name: glyph for glyph, name in severity.items()}

# Words that carry no identity, so a subject sharing one with a slug says nothing. `job-queue-and-
# worker-lifecycle` shares "and" with half the log.
STOPWORDS = frozenset(
    "a an the and or of on in to at by is it its not be as with for per from into".split())

CHANGE_CAP = 5      # per node. A page of subjects is not a feature map.
REVIEW_CAP = 6      # one node matches 49 review documents; the rest are counted, not listed.
GAP_CAP = 10        # open rows shown inline; the remainder are counted with a link to the table.

SECTIONS = (
    ("backlog", "Known gaps"),
    ("adr", "Decisions"),
    ("docs", "Specs &amp; plans"),
    ("reviews", "Reviews"),
    ("changes", "Recent changes · read from git at build time"),
)


# ---------------------------------------------------------------- pure derivation rules
def slug_words(slug: str) -> list[str]:
    """The parts of a slug that can identify it in prose. PURE.

    Two-character fragments and stopwords are dropped: matching on them is matching on nothing.
    """
    return [w for w in slug.split("-") if len(w) >= 3 and w not in STOPWORDS]


def subject_matches(subject: str, slug: str, words: list[str]) -> bool:
    """Whether a commit subject is plausibly ABOUT this node. PURE, and a LOWER BOUND.

    Two ways in: the slug itself (hyphenated or spaced) appears, or at least two of its identifying
    words do. ⚠ TWO, not one, and it is the difference between a section and a stream: `feature-map`
    on one word matched "a feature's documents must carry an ANCHOR NAME", which is a different
    subject entirely. A slug with only one identifying word takes that word alone, and accepts the
    noise — the alternative is a rule that can never match.
    """
    low = subject.lower()
    if slug in low or slug.replace("-", " ") in low:
        return True
    if not words:
        return False
    need = 2 if len(words) >= 2 else 1
    return sum(1 for w in words if re.search(r"\b" + re.escape(w), low)) >= need


def fragment_parts(entry) -> tuple[str, str]:
    """One fragment -> (label, href). A bare string is a label with no link. PURE.

    Callers build dicts; the string form exists so a caller holding only a name — a self-test, or a
    future source with nothing to link to — can render it rather than being forced to invent a URL.
    """
    if isinstance(entry, str):
        return entry, ""
    return str(entry.get("label", "")), str(entry.get("href", ""))


def absence_line(nodes: list[Node]) -> str:
    """"N declared absence(s)". PURE.

    The spec accepts knowingly that declared absences accumulate and nothing forces one to resolve;
    a CAP was rejected, because it would push people to not declare. This count is what makes the
    growth visible instead, so it is rendered whether it is 0 or 40.
    """
    n = sum(1 for x in nodes if x.state == "absent")
    return f"{n} declared absence" + ("" if n == 1 else "s")


def group_tree(nodes: list[Node]) -> list[tuple[str, list[tuple[Node, list[Node]]]]]:
    """[(trunk, [(node, children)])] in file order. PURE.

    A `####` node hangs off the nearest preceding `###`. One with no parent — level 4 first under a
    trunk — becomes a top-level entry rather than disappearing, because a node the page silently
    dropped is the one failure this whole page exists to remove.
    """
    trunks: list[tuple[str, list[tuple[Node, list[Node]]]]] = []
    by_trunk: dict[str, list[tuple[Node, list[Node]]]] = {}
    for n in nodes:
        if n.trunk not in by_trunk:
            by_trunk[n.trunk] = []
            trunks.append((n.trunk, by_trunk[n.trunk]))
        here = by_trunk[n.trunk]
        if n.level >= 4 and here:
            here[-1][1].append(n)
        else:
            here.append((n, []))
    return trunks


# ---------------------------------------------------------------- collection (reads the tree)
def anchor_adrs(anchors_text: str) -> dict[str, list[str]]:
    """anchor slug -> the ADR numbers its registry row names."""
    out: dict[str, list[str]] = {}
    for line in anchors_text.split("\n"):
        m = ANCHOR_ROW.match(line)
        if m:
            out[m.group(1)] = re.findall(r"\d{4}", m.group(2))
    return out


def anchor_documents(docs: pathlib.Path) -> dict[str, list[dict]]:
    """anchor slug -> the specs and plans whose `Anchor:` header claims it (ADR-0010)."""
    out: dict[str, list[dict]] = {}
    for sub in SUBDIRS:
        d = docs / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            head = f.read_text(errors="replace").split("\n")[:10]
            for line in head:
                m = DOC_ANCHOR.match(line)
                if m:
                    out.setdefault(m.group(1), []).append(
                        {"label": f.name, "href": f"/src/docs/{sub}/{f.name}"})
                    break
    return out


def git_subjects(n: int = 400) -> list[str] | None:
    """The last `n` commit subjects, or None when git cannot answer.

    ⛔ None IS NOT []. None is CANNOT RUN, and the page says so rather than rendering an empty
    Recent-changes band that looks like "nothing touched this".
    """
    try:
        r = subprocess.run(["git", "log", "--format=%s", f"-n{n}"], cwd=ROOT,
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


_BACKLOG_PAGE = None


def backlog_page():
    """`gen-backlog-page` as a module — the shipped backlog parser AND its severity map.

    Loaded lazily and once. Lazily so `--self-test` stays pure and a broken sibling cannot take
    this suite down with it; once because `collect` needs two things out of it. MEASURED before
    relying on it: importing it takes 0.06s and writes nothing, under a redirected `HOME`.
    """
    global _BACKLOG_PAGE
    if _BACKLOG_PAGE is None:
        _BACKLOG_PAGE = _load("gen-backlog-page")
    return _BACKLOG_PAGE


def backlog_rows() -> list[dict]:
    """Every backlog row, parsed by the SHIPPED backlog parser. Raises on an unparseable table."""
    return backlog_page().parse((DOCS / "backlog.md").read_text().split("\n"))


def collect(nodes: list[Node]) -> tuple[dict[str, dict], dict]:
    """(fragments keyed by node slug, notes about what could not be derived)."""
    notes: dict = {}
    adrs = anchor_adrs((DOCS / "anchors.md").read_text())
    docs_by_anchor = anchor_documents(DOCS)

    adr_files = {p.name[:4]: p.name for p in sorted((DOCS / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))}
    rows = backlog_rows()
    glyphs = sev_glyphs(backlog_page().SEVERITY)
    reviews = sorted(p for p in (DOCS / "reviews").rglob("*.md")) if (DOCS / "reviews").is_dir() else []
    subjects = git_subjects()
    notes["git"] = subjects is not None
    prs = [s for s in (subjects or []) if PR_TAIL.search(s)]
    notes["prs_read"] = len(prs)

    out: dict[str, dict] = {}
    for n in nodes:
        f: dict[str, list] = {k: [] for k, _ in SECTIONS}

        mine = [r for r in rows if r["bundle"] in n.areas]
        mine.sort(key=lambda r: (r["closed"], r["num"]))
        f["backlog"] = [{
            "label": f"#{r['num']} {glyphs.get(r['sev'], '·')}"
                     + (f" (was {r['was']})" if r["was"] else "")
                     + f" {r['title']}",
            "href": f"/backlog-table#i{r['num']}",
            "closed": r["closed"],
        } for r in mine]

        for a in n.anchors:
            for num in adrs.get(a, []):
                if num in adr_files:
                    f["adr"].append({"label": f"ADR-{num} · {adr_files[num][5:-3].replace('-', ' ')}",
                                     "href": f"/src/docs/adr/{adr_files[num]}"})
            f["docs"].extend(docs_by_anchor.get(a, []))

        hits = [p for p in reviews if n.slug in p.stem]
        f["reviews"] = [{"label": p.name, "href": f"/src/{p.relative_to(ROOT)}"} for p in hits]

        words = slug_words(n.slug)
        f["changes"] = [{"label": s} for s in prs if subject_matches(s, n.slug, words)][:CHANGE_CAP]

        out[n.slug] = f
    return out, notes


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
        gap:2.2rem}
  h1,h2,h3{margin:0;line-height:1.2;text-wrap:balance}
  p{margin:0;max-width:68ch}
  code{font-family:var(--mono);font-size:.88em}
  .mast{display:flex;flex-direction:column;gap:.85rem;border-bottom:2px solid var(--ink);
        padding-bottom:1.3rem}
  .eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.13em;text-transform:uppercase;
           color:var(--ink-faint)}
  h1{font-size:clamp(1.8rem,4.4vw,2.6rem);font-weight:620;letter-spacing:-.022em}
  .standfirst{font-size:1.05rem;color:var(--ink-soft);max-width:62ch}
  .built{font-size:.9rem;color:var(--ink-soft);max-width:66ch;border-left:3px solid var(--pending);
         background:var(--pending-bg);padding:.6rem .9rem;border-radius:3px}
  .trunk{display:flex;flex-direction:column;gap:1rem}
  .tname{font-family:var(--mono);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;
         color:var(--ink-faint);border-bottom:1px solid var(--rule);padding-bottom:.4rem}
  .node{background:var(--card);border:1px solid var(--rule);border-left:3px solid var(--structure);
        border-radius:3px;padding:1.1rem 1.25rem;display:flex;flex-direction:column;gap:.85rem}
  .node.absent{border-left-color:var(--pending)}
  .kids{display:flex;flex-direction:column;gap:.8rem;margin-left:1.5rem;margin-top:.8rem}
  .kids .node{border-left-width:2px}
  .nhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:.6rem 1rem}
  .slug{font-family:var(--mono);font-size:1.02rem;font-weight:600;color:var(--structure)}
  .node.absent .slug{color:var(--pending)}
  .state{font-family:var(--mono);font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;
         padding:.16rem .45rem;border-radius:2px;border:1px solid var(--rule);color:var(--ink-faint)}
  .state.built{color:var(--good);background:var(--good-bg);
               border-color:color-mix(in srgb,var(--good) 35%,transparent)}
  .state.notbuilt{color:var(--pending);background:var(--pending-bg);
                  border-color:color-mix(in srgb,var(--pending) 40%,transparent)}
  .meta{font-family:var(--mono);font-size:.74rem;color:var(--ink-faint);margin-left:auto}
  .purpose{font-size:.98rem;color:var(--ink-soft);max-width:66ch}
  .why{font-size:.92rem;color:var(--ink-soft);max-width:66ch;border-left:2px solid var(--pending);
       padding-left:.8rem}
  .why b{color:var(--pending)}
  .band{display:flex;flex-direction:column;gap:.35rem}
  .blab{font-family:var(--mono);font-size:.68rem;letter-spacing:.11em;text-transform:uppercase;
        color:var(--ink-faint)}
  .frag{display:flex;gap:.5rem;align-items:baseline;padding:.12rem 0;font-size:.87rem;
        color:var(--ink-soft);max-width:72ch}
  .frag a{color:var(--structure);text-decoration:underline;text-underline-offset:3px;
          text-decoration-color:color-mix(in srgb,var(--structure) 45%,transparent)}
  .frag a:hover{text-decoration-color:var(--structure)}
  details.more{border-top:1px solid var(--rule);padding-top:.3rem;margin-top:.2rem}
  details.more summary{cursor:pointer;font-family:var(--mono);font-size:.76rem;
                       color:var(--ink-faint)}
  .absent-note{font-size:.86rem;color:var(--ink-faint);font-style:italic}
  .warn{border-left:3px solid var(--defect);background:var(--card);padding:.7rem 1rem;
        font-size:.9rem;color:var(--defect);border-radius:3px}
  footer{border-top:1px solid var(--rule);padding-top:1.1rem;display:flex;flex-direction:column;
         gap:.6rem;font-size:.82rem;color:var(--ink-faint)}
  .legend{max-width:70ch}
  a{color:var(--structure)}
  :focus-visible{outline:2px solid var(--structure);outline-offset:2px}
"""


def render_fragments(f: dict) -> list[str]:
    """Every band of one node's fragments. An EMPTY band is omitted; a capped one says so."""
    parts: list[str] = []
    for key, label in SECTIONS:
        entries = list(f.get(key) or [])
        if not entries:
            continue
        # Known gaps: a CLOSED row is not a gap, so it is counted and collapsed rather than
        # dropped — dropping it would make a node with twenty closed rows look untouched.
        closed = [e for e in entries if isinstance(e, dict) and e.get("closed")]
        entries = [e for e in entries if not (isinstance(e, dict) and e.get("closed"))]
        cap = GAP_CAP if key == "backlog" else REVIEW_CAP if key == "reviews" else CHANGE_CAP
        shown, extra = entries[:cap], entries[cap:]
        if not shown and not closed:
            continue
        parts.append(f'<div class="band"><span class="blab">{label}</span>')
        for e in shown:
            text, href = fragment_parts(e)
            body = f'<a href="{esc(href)}">{inline_md(text)}</a>' if href else inline_md(text)
            parts.append(f'<div class="frag">{body}</div>')
        if extra or closed:
            bits = []
            if extra:
                bits.append(f"{len(extra)} more")
            if closed:
                bits.append(f"{len(closed)} closed")
            parts.append(f'<details class="more"><summary>{" · ".join(bits)}</summary>')
            for e in extra + closed:
                text, href = fragment_parts(e)
                body = f'<a href="{esc(href)}">{inline_md(text)}</a>' if href else inline_md(text)
                parts.append(f'<div class="frag">{body}</div>')
            parts.append("</details>")
        parts.append("</div>")
    return parts


def render_node(n: Node, fragments: dict) -> str:
    absent = n.state == "absent"
    f = fragments.get(n.slug) or {}
    n_frag = sum(len(f.get(k) or []) for k, _ in SECTIONS)
    parts = [f'<article class="node{" absent" if absent else ""}" id="{esc(n.slug)}">',
             '<div class="nhead">',
             f'<span class="slug">{esc(n.slug)}</span>',
             f'<span class="state {"notbuilt" if absent else "built"}">'
             f'{"not built" if absent else "built"}</span>',
             f'<span class="meta">{n_frag} fragment(s)</span>',
             "</div>",
             f'<p class="purpose">{inline_md(n.purpose)}</p>']
    if absent:
        # ⛔ THE HALF OF THIS PAGE THAT THE FIRST DESIGN COULD NOT SHOW. A necessary feature that
        # does not exist has no spec, no backlog row and no code — so a rule requiring every node to
        # carry a fragment made its absence permanently invisible. The reason line IS the evidence.
        parts.append(f'<p class="why"><b>expected because</b> '
                     f'{inline_md(n.expected_because or "")}</p>')
        if not n_frag:
            parts.append('<span class="absent-note">No fragment defines it — that is what '
                         "<code>absent</code> means, and the line above is the whole argument "
                         "for the node.</span>")
    else:
        body = render_fragments(f)
        if body:
            parts.extend(body)
        else:
            # A `built` node with nothing under it is a check-features.py failure, not a display
            # state — but the page must not render it as a blank card either.
            parts.append('<span class="absent-note">Built, but this page could derive no '
                         "fragment — check-features.py should have refused this node.</span>")
    parts.append("</article>")
    return "\n".join(parts)


def render(nodes: list[Node], fragments: dict, built_at: str = "",
           notes: dict | None = None, problems=(), generated_at: str = "") -> str:
    """The whole page fragment. `built_at` defaults to NOW, and that default is the point.

    ⚠ The timestamp is not decoration. Five of the six sources are files the regen hook watches; the
    sixth is `git log`, which no file-watcher can see, so the Recent-changes band can lag commits
    made without touching a watched file. Printing when the page was built is what lets a reader
    tell. It is a parameter so a caller that needs a byte-stable page can pass one.
    """
    built_at = built_at or _dt.datetime.now().isoformat(timespec="minutes")
    notes = notes or {}
    built = sum(1 for n in nodes if n.state == "built")
    body: list[str] = []
    for trunk, entries in group_tree(nodes):
        body.append('<section class="trunk">'
                    f'<h2 class="tname">{esc(trunk)}</h2>')
        for node, kids in entries:
            body.append(render_node(node, fragments))
            if kids:
                body.append('<div class="kids">')
                body.extend(render_node(k, fragments) for k in kids)
                body.append("</div>")
        body.append("</section>")

    warn = ""
    if problems:
        warn = ('<p class="warn"><b>docs/features.md does not validate</b> — '
                f'{len(problems)} problem(s), so this page may be rendering a tree its own check '
                'refuses. Run <code>python3 scripts/check-features.py</code>.</p>')
    git_note = ("" if notes.get("git", True) else
                '<p class="warn"><b>git could not be read</b>, so the Recent changes bands are '
                "EMPTY BECAUSE NOTHING WAS MEASURED — not because nothing touched these "
                "features. Treat that section as NOT RUN.</p>")

    return f"""<title>Features — what this system does, and what it deliberately does not</title>
<style>{CSS}
{page_chrome.chrome_css()}</style>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">Derived from docs/features.md · nothing here is a second copy</div>
  <h1>Features</h1>
  {page_chrome.chrome_bar("features", generated_at)}
  <p class="standfirst">One card per node of the feature tree.
    <strong>{len(nodes)}</strong> nodes, <strong>{built}</strong> built,
    <strong>{absence_line(nodes)}</strong>. A node says what it is <em>for</em>; everything
    beneath it — gaps, decisions, specs, reviews, changes — is derived from declarations those
    fragments already carry.</p>
  {warn}{git_note}
  <p class="built"><strong>Built {esc(built_at)}.</strong> Five of this page's six sources are
    files, and the regen hook rebuilds it when one changes. The sixth is <code>git log</code>,
    which no file-watcher can see: merging a PR changes what <em>Recent changes</em> should say and
    fires no hook. That section — and only that one — can lag; this timestamp is how you tell.
    {esc(str(notes.get("prs_read", 0)))} PR subjects were read at that moment.</p>
</header>
{"".join(body)}
<footer>
  <p class="legend"><strong>Two of the six sources are keyword matches, and are lower bounds.</strong>
    A review attaches when its filename stem contains the node slug; a commit attaches when the
    slug, or two of its identifying words, appear in the subject. Neither can claim completeness —
    they are shown as links rather than as a count, so what matched is visible and judgeable.</p>
  <p class="legend"><strong>A node marked <em>“Not built”</em> is information, not a gap in the
    page.</strong> A necessary feature that does not exist has no spec, no row and no code; a page
    that only rendered what exists could never show it. The one-line
    <code>expected-because:</code> is the only barrier to entry, and it is deliberately the only
    one. ⚠ The capitalisation here is load-bearing: the self-test asserts the lower-case marker on
    a card, and this sentence carrying it too would satisfy that case with a node absent from the
    page entirely — measured, it did.</p>
  <p class="legend">Tree: <code>docs/features.md</code> · Enforced by
    <code>scripts/check-features.py</code> · Rendered by
    <code>scripts/gen-features-page.py</code>.</p>
</footer>
</div>
<script>{page_chrome.chrome_script()}</script>
"""


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    cases = failures = 0

    def check(name, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            # ⛔ THE CANONICAL FORM. `check-plan-code.parse_fail_names` reads a red case from a line
            # STARTING `[FAIL] `, split on the last `": got "`. A prettier line makes every mutation
            # report "matched 0 red cases" while each one is killed by the case it names.
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")
        else:
            print(f"  ok     {name}")

    # ⚠ BUILT HERE, from the shipped parser, rather than referenced from elsewhere — an earlier
    # draft of this brief used an undefined `nodes` (plan review r1, Medium 11).
    nodes, _ = parse_features(
        "## PLATFORM\n"
        "### wake-on-visit\nstate: built\nfor: Lets the worker sleep until a visitor needs it.\n"
        "anchors: cloud-publishing\n\n"
        "### dig-job-recovery\nstate: absent\nfor: Un-sticks a dig job whose worker slept.\n"
        "expected-because: dig inherits the same race and nothing rescues it.\n")

    html = render(nodes, {"wake-on-visit": {"backlog": ["#139 a deploy kills the summary"], "adr": []}})
    check("a node's purpose is rendered", "Lets the worker sleep" in html, True)
    check("an absent node is marked", "not built" in html, True)
    check("the absent reason is shown", "expected because" in html.lower(), True)
    check("a linked gap appears", "#139" in html, True)
    check("the absence count is shown", "1 declared absence" in html, True)
    # ⛔ DELIBERATE DEVIATION FROM THE BRIEF, AND THE MEASUREMENT THAT FORCED IT. The brief writes
    # this case as a bare `str(date.today().year) in html`. MEASURED: that case CANNOT FAIL in
    # 2026 — `page_chrome.chrome_script()` emits the JavaScript escape `\\u2026` for an ellipsis,
    # which contains the literal `2026`, and every page carrying the theme control carries that
    # script. Replacing the whole timestamp with the string "unknown" left the case green. The year
    # is still what is asserted; it is anchored to the line that renders it, so the case dies when
    # the build time does.
    check("the build time is rendered",
          f"Built {__import__('datetime').date.today().year}" in html, True)
    # ⛔ A SECOND RENDER, AND IT IS NOT DECORATION — `check-fixture-variation.py` refuses a suite
    # whose only call site passes one value for every parameter: "no case can tell that parameter
    # apart from a constant". With one call, all six of `render`'s parameters were unvaried. This
    # call varies every one of them, and it is put HERE because the nesting it introduces is
    # exactly where a node would be rendered twice: `group_tree` hangs a `####` node off the
    # preceding `###`, and an implementation that both nested it AND left it at top level would
    # satisfy the flat tree above. The brief writes this case over the flat page alone; asserting
    # both is strictly stronger and keeps the case count at seven.
    nested, _ = parse_features(
        "## PLATFORM\n"
        "### job-queue\nstate: built\nfor: Runs the work someone walked away from.\n"
        "areas: (worker)\n"
        "#### wake-on-visit\nstate: built\nfor: Lets the worker sleep until a visitor needs it.\n"
        "anchors: cloud-publishing\n")
    deep = render(nested, {}, built_at="2001-01-01T00:00", notes={"git": False, "prs_read": 0},
                  problems=["features.md:1: a problem"], generated_at="2001-01-01 00:00 · abc1234")
    check("no node is rendered twice",
          (html.count("id=\"wake-on-visit\""), deep.count("id=\"wake-on-visit\"")), (1, 1))

    # ⛔ THE CASE THE REVIEW ASKED FOR COULD NOT BE WRITTEN, AND THAT IS THE PROOF THE FIX WORKED.
    # Round 1 asked for a case asserting every value of `gen-backlog-page.SEVERITY` appears as a
    # key here, going RED when a severity is added upstream and not mirrored. Under a DERIVED map
    # that case cannot ever fail — MEASURED: adding `"🟣": "epic"` upstream leaves this suite green,
    # because the new severity simply arrives. An unfalsifiable assertion is what this repo files
    # findings about, so the case asserts the DERIVATION instead, on a synthetic map. It dies on
    # all three ways the derivation can be lost: replaced by a literal, inverted the wrong way
    # round (`{glyph: name}` — the direction the old constant already had backwards), and the
    # `none` default dropped, which the caller's `.get(sev, "·")` would otherwise hide.
    check("the severity glyphs are derived from the backlog page's map, not a second copy",
          (sev_glyphs({"🟣": "epic"}), sev_glyphs({})),
          ({"none": "·", "epic": "🟣"}, {"none": "·"}))

    # ── THE REGEN HOOK ──────────────────────────────────────────────────────────────────────────
    # ⭐ Code review r1 (Codex), Low. `.claude/hooks/regen-features-page.sh` is the ONLY thing that
    # keeps this page from going stale, and it is shell: no `--self-test` of its own, and it cannot
    # be given a mutation either — `check-plan-code.load_manifests` requires every entry's `file`
    # to equal `scripts/<manifest stem>.py`, and `run_suite` runs the mutated file AS a Python
    # suite, so a `.sh` target would red its own control. The same is true of
    # `.claude/hooks/regen-backlog-page.sh`, whose four cases in `gen-backlog-page.py` set this
    # precedent. So the coverage is here, in the suite of the generator the hook exists to call.
    # ⛔ THE PAYLOADS BELOW ALL STOP SHORT OF THE GENERATOR — an unwatched path and two unreadable
    # payloads — because a case that reached it would rewrite the reader's live ~/explainers page.
    _HOOK = ROOT / ".claude" / "hooks" / "regen-features-page.sh"
    check("the hook this suite runs is present — a missing one is CANNOT RUN, not a pass",
          _HOOK.is_file(), True)

    def _run_hook(payload: str) -> str:
        if not _HOOK.is_file():
            return ("CANNOT RUN: .claude/hooks/regen-features-page.sh is absent from this tree. "
                    "Three cases RUN it, so a tree staged without .claude/hooks is a RED CONTROL "
                    "— stage scripts, docs AND .claude/hooks.")
        r = subprocess.run(["bash", str(_HOOK)], input=payload, capture_output=True, text=True)
        # rc is part of the assertion, not a detail: every path through the hook must exit 0.
        return f"rc={r.returncode} {r.stdout}{r.stderr}".strip()

    # The defect verbatim: this used to be indistinguishable from the line below it.
    check("an unreadable payload is WARNED about, and still exits 0",
          _run_hook("not json").startswith("rc=0 ⚠"), True)
    check("a well-formed payload naming an unwatched file stays silent",
          _run_hook('{"tool_input":{"file_path":"/tmp/not-a-features-source.txt"}}'), "rc=0")
    # ⚠ THE OTHER DIRECTION. A warning on empty stdin would fire on every hand-run of the hook,
    # and a warning nobody can avoid is one nobody reads.
    check("empty stdin stays silent — there is nothing to have failed to parse",
          _run_hook(""), "rc=0")

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

    for p in (DOCS / "features.md", DOCS / "anchors.md", DOCS / "backlog.md"):
        if not p.is_file():
            print(f"CANNOT RUN — {p} is missing. Treat this as NOT RUN.", file=sys.stderr)
            return 2

    nodes, problems = parse_features((DOCS / "features.md").read_text())
    if not nodes:
        print("CANNOT RUN — docs/features.md declares no nodes. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2
    try:
        fragments, notes = collect(nodes)
    except Exception as e:                      # an unparseable backlog is CANNOT RUN, not empty
        print(f"CANNOT RUN — the fragments could not be derived ({e.__class__.__name__}: {e}). "
              "Treat this as NOT RUN.", file=sys.stderr)
        return 2

    if problems:
        # Loud. The page renders anyway with the banner above, because a reader looking at a broken
        # tree needs to SEE it; silence would look like a clean one.
        print(f"⚠ docs/features.md has {len(problems)} problem(s) — "
              f"run scripts/check-features.py:", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)

    fragment = render(nodes, fragments, notes=notes, problems=problems,
                      generated_at=page_chrome.provenance(
                          _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), ROOT))

    if args.fragment_only:
        page_chrome.assert_wired(fragment, "gen-features-page.py")
        args.fragment_only.write_text(fragment)
        print(f"wrote fragment {args.fragment_only}")
        return 0

    # The Ask tray is LIFTED by brief-compose.py, never re-implemented here — one tray, four
    # page-producing callers.
    with tempfile.TemporaryDirectory() as td:
        frag = pathlib.Path(td) / "features-fragment.html"
        page_chrome.assert_wired(fragment, "gen-features-page.py")
        frag.write_text(fragment)
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "brief-compose.py"),
             "--content", str(frag), "--slug", "features", "--out", str(args.out),
             "--title", "Features — what this system does, and what it deliberately does not"],
            cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 or not args.out.is_file():
        print(f"FAILED — brief-compose did not write {args.out}:\n{r.stdout}{r.stderr}",
              file=sys.stderr)
        return 1

    built = sum(1 for n in nodes if n.state == "built")
    n_frag = sum(len(v) for f in fragments.values() for v in f.values())
    print(f"wrote {args.out}  ({len(nodes)} nodes, {built} built, "
          f"{absence_line(nodes)}, {n_frag} fragments)")
    print("     http://127.0.0.1:7391/features   (start: python3 scripts/explainer-serve.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

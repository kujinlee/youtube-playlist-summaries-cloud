#!/usr/bin/env python3
"""Render `docs/features.md` as /features — what this system does, and what it deliberately does not.

    python3 scripts/gen-features-page.py              # -> ~/explainers/features.html, served at /features
    python3 scripts/gen-features-page.py --fragment-only <path>
    python3 scripts/gen-features-page.py --self-test  # 54 cases

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
  decisions             <- the node's own `adrs:` line (ADR-0016)
  specs and plans       <- the `Anchor:` headers on docs/superpowers/{specs,plans}/*.md naming the
                           node's slug, read by `check-anchors.anchored_slugs` (ADR-0010)
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
lazily, so a broken sibling cannot take the rendering cases down with it.

⛔ AND ITS TAG RULE (backlog #381). A row lands under a node through `gen-backlog-page.cell_tags`
and `nearest_claim`, never by comparing the raw cell: a row may carry several `(tag)` groups and
appears under the node claiming EACH of them, and `(cloud/money)` and `(cloud / money)` are one tag.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html as html_lib
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
inline_unlinked = page_markup.render_unlinked

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


def sev_order() -> list[str]:
    """The glyphs in the backlog page's own severity order (🔴 🟠 🟡 🟢 …), then the no-marker `·`.
    Read from `gen-backlog-page.SEVERITY`, never written here, for the reason `sev_glyphs` gives."""
    sev = backlog_page().SEVERITY
    return list(sev) + [sev_glyphs(sev)["none"]]

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


def group_tree(nodes: list[Node]) -> list[tuple[str, Node | None, list]]:
    """[(trunk name, the trunk's own node or None, [(node, children)])] in file order. PURE.

    Recursive to any depth through `Node.parent`: a node hangs under the node its parent link names,
    and `children` has the same `(node, children)` shape all the way down. A node with no parent —
    a level-4 first under a slugless trunk — becomes a top-level entry rather than disappearing,
    because a node the page silently dropped is the one failure this whole page exists to remove.
    A trunk that carries a `slug:` is a level-2 node; it is the entry's second element, and the nodes
    under it are its children.

    ⛔ A SLUGGED TRUNK IS KEYED BY ITS NODE, NOT ITS DISPLAY TEXT (S1 r1, Codex High 1 = Claude F1).
    Keyed by the heading text, a second `## T` carrying `slug: b` overwrote the first's node `a`, which
    then had no card and no index line. Spec §2.2: the slug is the name, unique across the tree; the
    heading is display. So each level-2 node opens its OWN group.

    ⛔ AND A SLUGLESS TRUNK IS NOT MERGED BY ITS TEXT EITHER (S1 r2, Codex Medium). It is no node
    ("a trunk is a node with a slug", spec §2.2), so two `## T` sections have nothing in common but
    display text. Merged, `T a / U b / T c` rendered a, c, b. A PARENTLESS node joins the group just
    before it only when that group is the same slugless section still running; otherwise it opens a
    new one, so the page keeps file order. (Two slugless `## T` sections with no NODE-BEARING trunk
    between them stay one group — an empty `## U` in between opens no group (S1 r3, Claude F3).
    Nothing marks the boundary, neither heading carries an id, and the merge moves no node.)
    """
    trunks: list[list] = []
    slots: dict[tuple[str, str], list] = {}
    for n in nodes:
        if n.level == 2:
            entry = [n.trunk, n, []]
            trunks.append(entry)
            slots.setdefault((n.trunk, n.slug), entry[2])
            continue
        here = slots.get((n.trunk, n.parent)) if n.parent else None
        if here is None:
            if not trunks or trunks[-1][1] is not None or trunks[-1][0] != n.trunk:
                trunks.append([n.trunk, None, []])
            here = trunks[-1][2]
        kids: list = []
        here.append((n, kids))
        slots.setdefault((n.trunk, n.slug), kids)
    return [(name, tnode, entries) for name, tnode, entries in trunks]


def by_slug(nodes: list[Node]) -> dict[str, Node]:
    """Each slug's FIRST node. PURE. (Two nodes sharing a slug are check-features' refusal.)"""
    out: dict[str, Node] = {}
    for n in nodes:
        out.setdefault(n.slug, n)
    return out


def inherits_area(node: Node, by_slug: dict[str, Node]) -> bool:
    """True when some ANCESTOR of `node` claims an area (plan C11). PURE.

    A node's own `areas:` do not count here — this is the inheritance half of "claims no area and
    inherits none" (spec §3.2). The walk stops at a repeated slug, so a malformed tree cannot loop.
    """
    seen: set[str] = set()
    p = by_slug.get(node.parent) if node.parent else None
    while p is not None and p.slug not in seen:
        if p.areas:
            return True
        seen.add(p.slug)
        p = by_slug.get(p.parent) if p.parent else None
    return False


def split_closed(entries: list) -> tuple[list, list]:
    """(open, closed) of one band's entries, in order. PURE.

    ⛔ THE ONE RULE FOR "IS THIS A GAP". The card's Known-gaps band, its heading count and the index
    line all read it, so the three cannot disagree about which rows are open (owner, 2026-11-23:
    a `built` node with 24 open rows read as finished, because nothing counted them).
    """
    closed = [e for e in entries if isinstance(e, dict) and e.get("closed")]
    return [e for e in entries if not (isinstance(e, dict) and e.get("closed"))], closed


def open_gaps(fragment: dict) -> list:
    """One node's OPEN backlog rows — exactly the rows its card lists as Known gaps. PURE."""
    return split_closed(list(fragment.get("backlog") or []))[0]


def gap_label(gaps: list, order: list[str]) -> str:
    """`4 gaps (1🟠 2🟡 1🟢)`, `1 gap (1🟢)`, `0 gaps`. PURE.

    Severities appear in `order` (the backlog page's own severity order, `sev_order`); a glyph not
    in it is shown last rather than dropped, so a count never loses a row. A plain-string fragment
    carries no severity and counts as `·`, the backlog's no-marker glyph.
    """
    if not gaps:
        return "0 gaps"
    counts: dict[str, int] = {}
    for e in gaps:
        g = e.get("sev", "·") if isinstance(e, dict) else "·"
        counts[g] = counts.get(g, 0) + 1
    rank = {g: i for i, g in enumerate(order)}
    parts = " ".join(f"{c}{g}" for g, c in sorted(counts.items(),
                                                   key=lambda kv: rank.get(kv[0], len(rank))))
    return f"{len(gaps)} gap{'' if len(gaps) == 1 else 's'} ({parts})"


def state_html(n: Node) -> str:
    """The state badge, shared by the card heading and its index line — one wording, one place.
    A node with no `state:` (a goal, a trunk) shows NO badge: "" (spec §3.2)."""
    if n.state is None:
        return ""
    absent = n.state == "absent"
    return (f'<span class="state {"notbuilt" if absent else "built"}">'
            f'{"not built" if absent else "built"}</span>')


NO_AREA = "claims no area — gaps not counted"


def gaps_html(n: Node, fragments: dict, order: list[str], nodes_by_slug: dict[str, Node]) -> str:
    """The open-gap count. ⛔ A node that claims no area and inherits none says so (spec §3.2): no
    backlog row can land under it, so "0 gaps" would read as "nothing open" — the misreading the
    count was added to end."""
    if not n.areas and not inherits_area(n, nodes_by_slug):
        return f'<span class="gaps none">{esc(NO_AREA)}</span>'
    gaps = open_gaps(fragments.get(n.slug) or {})
    return f'<span class="gaps{" open" if gaps else ""}">{esc(gap_label(gaps, order))}</span>'


_ID_SAFE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def frag_id(name: str) -> str:
    """⛔ THE ONE ID OF A NODE: its card's `id` and its index link's fragment both read it. PURE.

    A node's name is free heading text. Any character outside `[A-Za-z0-9-]` — `_` included —
    becomes `_<hex>_`, so the map is injective, and the result is made only of characters a browser
    does not percent-encode: `location.hash` equals the link's href exactly, and the handler needs
    no decoding (which threw on a malformed escape — review r1, Codex M1 / Claude m3). The result
    carries `page_markup.feature_id`'s reserved prefix, which no chrome id does, so a node named
    `chrome-theme` cannot share the chrome button's id (review r2, Codex R2-1).
    """
    return page_markup.feature_id("".join(c if c in _ID_SAFE else f"_{ord(c):x}_" for c in name))


def render_index(nodes: list[Node], fragments: dict, order: list[str]) -> str:
    """The tree index: group -> `###` -> `####`, in file order, one linked line per node. PURE.

    ⚠ EACH LINE COUNTS ITS OWN NODE'S GAPS ONLY — no subtotal over a parent's children. A row
    carrying two tags lands under BOTH nodes (backlog #381), so summing a subtree's lines would count
    such a row twice; a de-duplicated subtotal is a second counting rule, and this page keeps one.
    """
    slugs = by_slug(nodes)

    def line(n: Node) -> str:
        return " ".join(p for p in (f'<a href="#{esc(frag_id(n.slug))}">{esc(n.slug)}</a>', state_html(n),
                                    gaps_html(n, fragments, order, slugs)) if p)

    def nest(entries: list) -> str:
        # One nested list on ONE line — exactly today's `####` markup, recursed.
        return "<ul>" + "".join(f"<li>{line(k)}{nest(kk) if kk else ''}</li>" for k, kk in entries) + "</ul>"

    def trunk_name(name: str, tnode: Node | None) -> str:
        if tnode is None:
            return esc(name)
        return " ".join(p for p in (f'<a href="#{esc(frag_id(tnode.slug))}">{esc(name)}</a>',
                                    state_html(tnode), gaps_html(tnode, fragments, order, slugs)) if p)

    out = ['<nav class="tindex" aria-label="Feature tree">',
           '<p class="ilab">Feature tree · each line counts its own node’s open gaps · '
           'select a line to open its card</p>']
    for trunk, tnode, entries in group_tree(nodes):
        out.append(f'<div class="igroup"><span class="iname">{trunk_name(trunk, tnode)}</span><ul>')
        for node, kids in entries:
            out.append(f"<li>{line(node)}")
            if kids:
                out.append(nest(kids))
            out.append("</li>")
        out.append("</ul></div>")
    out.append("</nav>")
    return "\n".join(out)


def index_shape(index_html: str) -> list[tuple[int, str]]:
    """[(list depth, slug)] of every index link, in document order. PURE — the self-test's reader
    of the index, through the same subset tokenizer the page is checked with."""
    depth, out = 0, []
    for t in page_markup.page_tokens(index_html)[0]:
        if t.kind == "start" and t.tag == "ul":
            depth += 1
        elif t.kind == "end" and t.tag == "ul":
            depth -= 1
        elif t.kind == "start" and t.tag == "a":
            href = dict(t.attrs).get("href") or ""
            if href.startswith("#"):
                out.append((depth, href[1:]))
    return out


# Opens the folded card a hash names. Fragment navigation scrolls TO a closed `<details>` but never
# opens it, so without this an index link lands on a one-line summary. Runs on load (a shared link)
# and on hashchange (an index click); re-clicking the CURRENT hash fires no hashchange, so index
# clicks are handled directly too. Ids come from `frag_id`, so a hash is compared and looked up
# verbatim — nothing is decoded, and a malformed escape simply names no card.
OPEN_HASH_JS = """
(function () {
  function openFrom(hash) {
    var id = (hash || "").replace(/^#/, "");
    var el = id && document.getElementById(id);
    if (!el || el.tagName !== "DETAILS") return;
    el.open = true;
    el.scrollIntoView({block: "start"});
  }
  window.addEventListener("hashchange", function () { openFrom(location.hash); });
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest('.tindex a[href^="#"]');
    if (a && a.getAttribute("href") === location.hash) openFrom(location.hash);
  });
  openFrom(location.hash);
})();
"""


def scripts_parse(page: str) -> list[str]:
    """`node --check` over every inline `<script>`: [] when all parse. No `node` is CANNOT RUN,
    reported as a problem — never an empty list, which would read as a pass."""
    import shutil
    node = shutil.which("node")
    bodies = re.findall(r"<script>(.*?)</script>", page, re.S)
    if not node:
        return ["CANNOT RUN: no `node` on PATH — the inline scripts were NOT checked"]
    if not bodies:
        return ["no inline <script> found — nothing was checked"]
    problems = []
    with tempfile.TemporaryDirectory() as td:
        for i, b in enumerate(bodies):
            f = pathlib.Path(td) / f"s{i}.js"
            f.write_text(b)
            r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                problems.append(f"script {i}: {(r.stderr or r.stdout).strip()[:200]}")
    return problems


# The self-test's DOM stand-in for OPEN_HASH_JS (review r1: Claude M1, Codex M3). The script is RUN,
# under `node` in a fresh `vm` context per scenario, against a stub window/document/location whose
# listeners are captured and fired — so a case observes what the script DOES, not which tokens it
# contains. Each scenario: `hash` at load, `els` [[id, tagName]], `steps` applied in order
# ({"fold": id} | {"hash": h, "fire": "hashchange"} | {"fire": "click", "href": h}).
_HASH_DRIVER = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[2], "utf8");
const out = {};
for (const s of JSON.parse(fs.readFileSync(process.argv[3], "utf8"))) {
  const els = {}, on = {window: {}, document: {}};
  // `els` is in document order and the FIRST element with an id wins, as `getElementById`'s does.
  for (const [id, tag] of s.els)
    if (!Object.prototype.hasOwnProperty.call(els, id))
      els[id] = {tagName: tag, open: false, scrolled: 0, scrollIntoView() { this.scrolled++; }};
  const add = (where) => (t, f) => { (on[where][t] = on[where][t] || []).push(f); };
  const location = {hash: s.hash};
  const ctx = {location, window: {addEventListener: add("window")},
               document: {addEventListener: add("document"),
                          getElementById: (id) => Object.prototype.hasOwnProperty.call(els, id) ? els[id] : null}};
  let err = null;
  try {
    vm.runInNewContext(src, ctx);
    for (const st of s.steps || []) {
      if (st.fold) els[st.fold].open = false;
      if (st.hash !== undefined) location.hash = st.hash;
      if (st.fire === "hashchange") (on.window.hashchange || []).forEach((f) => f({}));
      if (st.fire === "click") {
        const a = {getAttribute: (n) => (n === "href" ? st.href : null)};
        const target = {closest: (sel) => (sel.indexOf(".tindex") !== -1 ? a : null)};
        (on.document.click || []).forEach((f) => f({target}));
      }
    }
  } catch (e) { err = String(e); }
  const ids = Object.keys(els).sort();
  out[s.name] = {err, open: ids.filter((k) => els[k].open), scrolled: ids.filter((k) => els[k].scrolled)};
}
process.stdout.write(JSON.stringify(out));
"""


def run_hash_script(js: str, scenarios: list[dict]) -> dict | str:
    """{scenario name: {err, open, scrolled}} from RUNNING `js` per scenario; a str is CANNOT RUN."""
    import json
    import shutil
    node = shutil.which("node")
    if not node:
        return "CANNOT RUN: no `node` on PATH — the hash handler was NOT run"
    with tempfile.TemporaryDirectory() as td:
        d, s, sc = (pathlib.Path(td) / n for n in ("drive.js", "page.js", "scen.json"))
        d.write_text(_HASH_DRIVER)
        s.write_text(js)
        sc.write_text(json.dumps(scenarios))
        r = subprocess.run([node, str(d), str(s), str(sc)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return f"CANNOT RUN: the driver failed: {(r.stderr or r.stdout).strip()[:200]}"
    return json.loads(r.stdout)


def rendered_gap_counts(page: str, order: list[str]) -> dict[str, dict]:
    """Per card id: what its RENDERED markup says, read back from the HTML alone (review r1, Codex
    M2) — `heading` and `index` are the {glyph: n} the gap summaries print, `rows` the open rows its
    Known-gaps band lists as [(key, glyph)]. Shares no code with `open_gaps` / `gap_label`, so a
    band that drops, duplicates or miscounts a row disagrees with the summaries beside it."""
    def summary(text: str | None) -> dict | None:
        if text is None:
            return None
        if text == "claims no area — gaps not counted":
            # An area-less node can hold no row, so its sentence is an EMPTY count: a band that
            # still lists open rows under it disagrees. A literal, not `NO_AREA` — no shared code.
            return {}
        m = re.match(r"(\d+) gaps?(?: \((.*)\))?$", text)
        if not m:
            return {"unparsed": text}
        got = {g: int(c) for c, g in re.findall(r"(\d+)(\S+)", m.group(2) or "")}
        return got if sum(got.values()) == int(m.group(1)) else {"total≠parts": text}

    def glyph_of(row_html: str) -> tuple[str, str]:
        words = re.sub(r"<[^>]+>", "", row_html).split()
        return (words[0] if words else "",
                words[1] if len(words) > 1 and words[1] in order else "·")

    out: dict[str, dict] = {}
    for chunk in page.split('<details class="node')[1:]:
        cid = re.match(r'[^"]*" id="([^"]*)"', chunk).group(1)
        head = re.search(r'<summary class="nhead">.*?<span class="gaps[^"]*">([^<]*)</span>', chunk, re.S)
        band = re.search(r'<span class="blab">Known gaps</span>(.*?)(?:<div class="band">|$)', chunk, re.S)
        rows = re.findall(r'<div class="frag( closed)?">(.*?)</div>', band.group(1), re.S) if band else []
        line = re.search(rf'<a href="#{re.escape(cid)}">[^<]*</a>.*?<span class="gaps[^"]*">([^<]*)</span>',
                         page, re.S)
        out[html_lib.unescape(cid)] = {
            "heading": summary(html_lib.unescape(head.group(1)) if head else None),
            "index": summary(html_lib.unescape(line.group(1)) if line else None),
            "rows": [glyph_of(r) for closed, r in rows if not closed],
            "closed": [glyph_of(r) for closed, r in rows if closed]}
    return out


def row_disagreements(page: str, order: list[str], expected: dict[str, dict]) -> list[str]:
    """Card ids whose RENDERED band rows differ from `expected` (review r2, Codex R2-2), sorted.

    `expected` is {card id: {"open": [(key, glyph)], "closed": [(key, glyph)]}}, written out by the
    caller — the identities, not just the severity totals `gap_disagreements` compares, so a band
    listing `#999 🟡` where `#2 🟡` belongs disagrees. A card on one side only disagrees, and so does
    an id two cards share (the reader would keep only one of them)."""
    ids = re.findall(r'<details class="node[^"]*" id="([^"]*)"', page)
    seen = rendered_gap_counts(page, order)
    bad = {html_lib.unescape(i) for i in ids if ids.count(i) > 1}
    for cid in set(seen) | set(expected):
        got = ({"open": seen[cid]["rows"], "closed": seen[cid]["closed"]} if cid in seen else None)
        want = expected.get(cid)
        if got is None or want is None or got != {"open": list(want["open"]), "closed": list(want["closed"])}:
            bad.add(cid)
    return sorted(bad)


def gap_disagreements(page: str, order: list[str]) -> list[str]:
    """Card ids whose heading or index summary disagrees with the open rows its own band lists."""
    bad = []
    for cid, c in rendered_gap_counts(page, order).items():
        listed: dict[str, int] = {}
        for _, g in c["rows"]:
            listed[g] = listed.get(g, 0) + 1
        keys = [k for k, _ in c["rows"]]
        if c["heading"] != listed or c["index"] != listed or len(keys) != len(set(keys)):
            bad.append(cid)
    return bad


# ---------------------------------------------------------------- collection (reads the tree)
_CHECK_ANCHORS = None


def anchor_documents(docs: pathlib.Path) -> dict[str, list[dict]]:
    """node slug -> the specs and plans whose `Anchor:` header names it (ADR-0010).

    ⛔ READ BY `check-anchors.anchored_slugs`, THE ONE HEADER READER (plan choice C10). This page
    carried its own, looser header regex; a second reader of one header is a second grammar for it,
    and the two can disagree about which documents a node has. ADRs are left out: a node's decisions
    are its own `adrs:` line. Loaded lazily and once, like `backlog_page`."""
    global _CHECK_ANCHORS
    if _CHECK_ANCHORS is None:
        _CHECK_ANCHORS = _load("check-anchors")
    adr_dir = f"docs/{_CHECK_ANCHORS.ADR_SUB}/"
    return {slug: [{"label": rel.rsplit("/", 1)[1], "href": f"/src/{rel}"}
                   for rel in rels if not rel.startswith(adr_dir)]
            for slug, rels in _CHECK_ANCHORS.anchored_slugs(docs).items()}


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


def match_rows(nodes: list[Node], rows: list[dict]) -> dict[str, list[dict]]:
    """PURE over the backlog page's tag rule. Each node's backlog rows, by slug.

    A row lands under the node that `nearest_claim`s EACH tag its cell writes, so a row tagged
    `(tooling) (comprehensibility)` appears under both nodes — the point of backlog #381 — and once
    under a node that claims two of its tags. A tag no node claims lands nowhere here;
    `check-features` is what refuses that, and it reads the same two functions."""
    bp = backlog_page()
    claims: dict[str, str] = {}
    for n in nodes:
        for a in n.areas:
            claims.setdefault(bp.normalise_tag(a), n.slug)
    out: dict[str, list[dict]] = {n.slug: [] for n in nodes}
    for r in rows:
        for leaf in bp.cell_tags(r["bundle"])[0]:
            area = bp.nearest_claim(leaf, claims)
            if area is not None and r not in out[claims[area]]:
                out[claims[area]].append(r)
    return out


def collect(nodes: list[Node]) -> tuple[dict[str, dict], dict]:
    """(fragments keyed by node slug, notes about what could not be derived)."""
    notes: dict = {}
    docs_by_slug = anchor_documents(DOCS)

    adr_files = {p.name[:4]: p.name for p in sorted((DOCS / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))}
    rows = backlog_rows()
    matched = match_rows(nodes, rows)
    glyphs = sev_glyphs(backlog_page().SEVERITY)
    reviews = sorted(p for p in (DOCS / "reviews").rglob("*.md")) if (DOCS / "reviews").is_dir() else []
    subjects = git_subjects()
    notes["git"] = subjects is not None
    prs = [s for s in (subjects or []) if PR_TAIL.search(s)]
    notes["prs_read"] = len(prs)

    out: dict[str, dict] = {}
    for n in nodes:
        f: dict[str, list] = {k: [] for k, _ in SECTIONS}

        mine = sorted(matched[n.slug], key=lambda r: (r["closed"], r["num"]))
        f["backlog"] = [{
            "label": f"#{r['num']} {glyphs.get(r['sev'], '·')}"
                     + (f" (was {r['was']})" if r["was"] else "")
                     + f" {r['title']}",
            "href": page_markup.key_link("backlog", r["num"]),
            "sev": glyphs.get(r["sev"], "·"),
            "closed": r["closed"],
        } for r in mine]

        # A number with no file is `check-features`' refusal (`adr_problems`), not this page's.
        for num in n.adrs:
            if num in adr_files:
                f["adr"].append({"label": f"ADR-{num} · {adr_files[num][5:-3].replace('-', ' ')}",
                                 "href": f"/src/docs/adr/{adr_files[num]}"})
        f["docs"].extend(docs_by_slug.get(n.slug, []))

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
  .tindex{background:var(--card);border:1px solid var(--rule);border-radius:3px;
          padding:1rem 1.25rem;display:flex;flex-direction:column;gap:.7rem}
  .ilab{font-family:var(--mono);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;
        color:var(--ink-faint)}
  .igroup{display:flex;flex-direction:column;gap:.25rem}
  .iname{font-family:var(--mono);font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;
         color:var(--ink-soft);font-weight:600}
  .tindex ul{list-style:none;margin:0;padding-left:1.1rem;display:flex;flex-direction:column;
             gap:.15rem}
  .tindex ul ul{border-left:1px solid var(--rule);margin:.15rem 0 .1rem .3rem;padding-left:.9rem}
  .tindex li{font-size:.86rem;line-height:1.5;overflow-wrap:anywhere}
  .tindex li > a{font-family:var(--mono);font-weight:600;color:var(--structure);
                 text-decoration:none;margin-right:.35rem}
  .tindex li > a:hover{text-decoration:underline}
  .tindex .state{font-size:.62rem;padding:.05rem .35rem;margin-right:.35rem}
  .gaps{font-family:var(--ui);font-size:.8rem;color:var(--ink-faint);white-space:nowrap;
        font-variant-numeric:tabular-nums;letter-spacing:.14em}
  .gaps.open{color:var(--pending)}
  details.node > summary{cursor:pointer;list-style:none}
  details.node > summary::-webkit-details-marker{display:none}
  /* The fold marker hangs off the SLUG, not the wrapping summary, so it wraps with the slug
     instead of standing alone on its own line at 390px (review r1 m5). */
  details.node > summary .slug::before{content:"▸";color:var(--ink-faint);font-size:.8rem;
                                       margin-right:.45rem;font-weight:400}
  details.node[open] > summary .slug::before{content:"▾"}
  details.node:not([open]){padding-top:.7rem;padding-bottom:.7rem}
  details.node{display:block}
  details.node > summary ~ *{margin-top:.85rem}
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
        entries, closed = split_closed(entries)
        cap = GAP_CAP if key == "backlog" else REVIEW_CAP if key == "reviews" else CHANGE_CAP
        shown, extra = entries[:cap], entries[cap:]
        if not shown and not closed:
            continue
        parts.append(f'<div class="band"><span class="blab">{label}</span>')
        for e in shown:
            text, href = fragment_parts(e)
            # The row text sits INSIDE the row's link, so a key in it stays text (`inline_unlinked`),
            # or the page carries an `<a>` in an `<a>` — 29 rows did (backlog #470 review round 1).
            body = f'<a href="{esc(href)}">{inline_unlinked(text)}</a>' if href else inline_md(text)
            parts.append(f'<div class="frag">{body}</div>')
        if extra or closed:
            bits = []
            if extra:
                bits.append(f"{len(extra)} more")
            if closed:
                bits.append(f"{len(closed)} closed")
            parts.append(f'<details class="more"><summary>{" · ".join(bits)}</summary>')
            # A closed row is MARKED as closed, so the markup alone says which listed rows are
            # gaps — the self-test reads the counts back from it (`rendered_gap_counts`).
            for e, cls in [(e, "frag") for e in extra] + [(e, "frag closed") for e in closed]:
                text, href = fragment_parts(e)
                body = f'<a href="{esc(href)}">{inline_unlinked(text)}</a>' if href else inline_md(text)
                parts.append(f'<div class="{cls}">{body}</div>')
            parts.append("</details>")
        parts.append("</div>")
    return parts


def render_node(n: Node, fragments: dict, order: list[str], nodes_by_slug: dict[str, Node]) -> str:
    """One card, FOLDED: the heading (slug, state, open gaps by severity) is the `<summary>`, so a
    folded card still says whether `built` means finished. The index's links open it (OPEN_HASH_JS)."""
    absent = n.state == "absent"
    f = fragments.get(n.slug) or {}
    n_frag = sum(len(f.get(k) or []) for k, _ in SECTIONS)
    parts = [f'<details class="node{" absent" if absent else ""}" id="{esc(frag_id(n.slug))}">',
             '<summary class="nhead">',
             f'<span class="slug">{esc(n.slug)}</span>',
             state_html(n),
             gaps_html(n, fragments, order, nodes_by_slug),
             f'<span class="meta">{n_frag} fragment(s)</span>',
             "</summary>",
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
        elif n.state == "built":
            # A `built` node with nothing under it is a check-features.py failure, not a display
            # state — but the page must not render it as a blank card either.
            parts.append('<span class="absent-note">Built, but this page could derive no '
                         "fragment — check-features.py should have refused this node.</span>")
    parts.append("</details>")
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
    order = sev_order()
    # The index sits ABOVE the build note, so a phone's first screen carries the tree (review r1 m4).
    index_html = render_index(nodes, fragments, order)
    body: list[str] = []
    slugs = by_slug(nodes)

    def cards(entries: list) -> None:
        for node, kids in entries:
            body.append(render_node(node, fragments, order, slugs))
            if kids:
                body.append('<div class="kids">')
                cards(kids)
                body.append("</div>")

    for trunk, tnode, entries in group_tree(nodes):
        body.append('<section class="trunk">'
                    f'<h2 class="tname">{esc(trunk)}</h2>')
        if tnode is not None:
            body.append(render_node(tnode, fragments, order, slugs))
        cards(entries)
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
  <p class="standfirst">One folded card per node of the feature tree, indexed below.
    <strong>{len(nodes)}</strong> nodes, <strong>{built}</strong> built,
    <strong>{absence_line(nodes)}</strong>. A node says what it is <em>for</em>; everything
    beneath it — gaps, decisions, specs, reviews, changes — is derived from declarations those
    fragments already carry.</p>
  {warn}{git_note}
</header>
{index_html}
<p class="built"><strong>Built {esc(built_at)}.</strong> Five of this page's six sources are
    files, and the regen hook rebuilds it when one changes. The sixth is <code>git log</code>,
    which no file-watcher can see: merging a PR changes what <em>Recent changes</em> should say and
    fires no hook. That section — and only that one — can lag; this timestamp is how you tell.
    {esc(str(notes.get("prs_read", 0)))} PR subjects were read at that moment.</p>
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
<script>{OPEN_HASH_JS}</script>
"""


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
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
        "adrs: 0001\n\n"
        "### dig-job-recovery\nstate: absent\nfor: Un-sticks a dig job whose worker slept.\n"
        "expected-because: dig inherits the same race and nothing rescues it.\n")

    html = render(nodes, {"wake-on-visit": {"backlog": ["#139 a deploy kills the summary"], "adr": []}})
    check("a node's purpose is rendered", "Lets the worker sleep" in html, True)
    check("an absent node is marked", "not built" in html, True)
    check("the absent reason is shown", "expected because" in html.lower(), True)
    check("a linked gap appears", "#139" in html, True)
    # backlog #470 review round 1: a row whose title cites a key sits inside the row's own link.
    _nest = render(nodes, {"wake-on-visit": {"backlog": [
        {"label": "#45 residue left when backlog #7 merged", "href": "/backlog-table#i45"}], "adr": []}})
    check("a key in a linked row's text is not a second <a> inside the row's link",
          ([t.start for t in page_markup.page_tokens(_nest)[0] if t.kind == "start" and t.in_a],
           "residue left when backlog #7 merged</a>" in _nest), ([], True))
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
        "adrs: 0001\n")
    deep = render(nested, {}, built_at="2001-01-01T00:00", notes={"git": False, "prs_read": 0},
                  problems=["features.md:1: a problem"], generated_at="2001-01-01 00:00 · abc1234")
    check("no node is rendered twice",
          (html.count("id=\"f-wake-on-visit\""), deep.count("id=\"f-wake-on-visit\"")), (1, 1))
    # ⛔ S1 r1 (Codex High 1 = Claude F1): a trunk's DISPLAY text is not its identity — its slug is
    # (spec §2.2). Two `## ` sections sharing a heading, both slugged, and slugless-then-slugged: every
    # node gets exactly one card and one index line, and each slugged trunk heads its own group.
    _twin = ("## T\nslug: a\nfor: A.\n### c1\nfor: C.\n## T\nslug: b\nfor: B.\n### c2\nfor: D.\n",
             "## T\n### c1\nfor: C.\n## T\nslug: b\nfor: B.\n### c2\nfor: D.\n")
    _twin_got = []
    for _src in _twin:
        _tn = parse_features(_src)[0]
        _tp = render(_tn, {}, built_at="2001-01-01T00:00")
        _tix = render_index(_tn, {}, sev_order())
        _twin_got.append(([(_tp.count(f'id="{frag_id(n.slug)}"'), _tix.count(f'href="#{frag_id(n.slug)}"'))
                           for n in _tn],
                          [(name, t.slug if t else None, [e[0].slug for e in es]) for name, t, es in group_tree(_tn)]))
    check("two trunks sharing a display name keep every node",
          (_twin_got, group_tree([])),
          ([([(1, 1)] * 4, [("T", "a", ["c1"]), ("T", "b", ["c2"])]),
            ([(1, 1)] * 3, [("T", None, ["c1"]), ("T", "b", ["c2"])])], []))
    # ⛔ S1 r2 (Codex Medium): a SLUGLESS trunk is no node (spec §2.2, "a trunk is a node with a
    # slug"), so it has no identity to merge two `## T` sections under. Grouped by heading text, the
    # third section's `c` was pulled up beside `a`, ahead of `b`: the page left file order. Each `## `
    # section opens its own group, slugless or slugged in between, and a slugless `## T` after a slugged
    # one does not join the slugged trunk's children. CONTROL: one slugless trunk with
    # two nodes stays ONE group, so a fix that opened a group per node would also go red.
    # ⛔ S1 r3 (Claude F1): the order is READ through `index_shape`, never `str.index` on the HTML — a
    # dropped node then FAILS this case instead of raising and aborting every case after it.
    _order = ("## T\n### a\nfor: A.\n## U\n### b\nfor: B.\n## T\n### c\nfor: C.\n",
              "## T\n### a\nfor: A.\n## U\nslug: u\nfor: U.\n### b\nfor: B.\n## T\n### c\nfor: C.\n",
              "## T\nslug: t\nfor: T.\n### a\nfor: A.\n## T\n### b\nfor: B.\n",
              "## T\n### a\nfor: A.\n### b\nfor: B.\n")
    _order_got = []
    for _src in _order:
        _on = parse_features(_src)[0]
        _oix = render_index(_on, {}, sev_order())
        _deep = {frag_id(n.slug): n.slug for n in _on if n.level > 2}
        _order_got.append(([(name, t.slug if t else None, [e[0].slug for e in es])
                            for name, t, es in group_tree(_on)],
                           [_deep[f] for _, f in index_shape(_oix) if f in _deep]))
    check("slugless trunks keep file order",
          _order_got,
          [([("T", None, ["a"]), ("U", None, ["b"]), ("T", None, ["c"])], ["a", "b", "c"]),
           ([("T", None, ["a"]), ("U", "u", ["b"]), ("T", None, ["c"])], ["a", "b", "c"]),
           ([("T", "t", ["a"]), ("T", None, ["b"])], ["a", "b"]),
           ([("T", None, ["a", "b"])], ["a", "b"])])

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

    # ── WHICH ROWS A NODE CLAIMS (backlog #381) ─────────────────────────────────────────────────
    tagged, _ = parse_features(
        "## DEV\n"
        "### harness\nstate: built\nfor: Guards.\nareas: (tooling), (process)\n"
        "### status-pages\nstate: built\nfor: Pages.\nareas: (comprehensibility)\n"
        "### spend\nstate: built\nfor: Money.\nareas: (cloud/money)\n"
        "### cloud\nstate: built\nfor: Cloud.\nareas: (cloud)\n")
    _r = lambda num, bundle: {"num": num, "bundle": bundle, "closed": False}
    got = match_rows(tagged, [_r(1, "(tooling) (comprehensibility)"), _r(2, "(cloud / money)"),
                              _r(3, "(cloud/money)"), _r(4, "(Cloud/new), (tooling)"),
                              _r(5, "(tooling) (process)")])
    nums = {k: [r["num"] for r in v] for k, v in got.items()}
    # ⛔ THE FAILS-IF, features half: a two-tag row under BOTH matching features.
    check("a two-tag row appears under BOTH nodes that claim its tags",
          (1 in nums["harness"], 1 in nums["status-pages"]), (True, True))
    check("both spellings of a slashed tag land under the one node that claims it, and only there",
          (nums["spend"], 2 in nums["cloud"] or 3 in nums["cloud"]), ([2, 3], False))
    check("hierarchy and several tags together: an unclaimed leaf falls to its family's node",
          (4 in nums["cloud"], 4 in nums["harness"]), (True, True))
    check("a row is listed ONCE under a node however many of its tags that node claims",
          nums["harness"].count(5), 1)
    # ⛔ THE FAILS-IF, agreement half, over the REAL files. Every real row lands under a node for
    # each tag it writes, and every tag it is filed under on /features is one the backlog page's
    # filter lists for it — so the two pages cannot disagree about any row's tags.
    _bp = backlog_page()
    _real_nodes = parse_features((DOCS / "features.md").read_text())[0]
    _real_rows = backlog_rows()
    _placed = match_rows(_real_nodes, _real_rows)
    _areas = {_bp.normalise_tag(a): n.slug for n in _real_nodes for a in n.areas}
    def _row_disagrees(r: dict) -> bool:
        claim = [_bp.nearest_claim(t, _areas) for t in _bp.cell_tags(r["bundle"])[0]]
        filed = {slug for slug, v in _placed.items() if r in v}
        return (None in claim                                    # a tag /features cannot show
                or filed != {_areas[a] for a in claim}           # filed elsewhere, or missing
                or not set(claim) <= set(_bp.bundle_tags(r["bundle"])))  # a tag the filter lacks
    _disagree = [r["num"] for r in _real_rows if _row_disagrees(r)]
    check("every REAL tagged row lands under a node, and only under tags the backlog filter gives it",
          (len(_real_rows) > 300, _disagree), (True, []))

    # ⚠ THE CALL SITE, not only the function — `collect` is what the page renders from, and a
    # `match_rows` nobody calls would leave every case above green.
    # Two node sets — the real tree and the synthetic multi-area one — so `nodes` is not a constant.
    def _band_mismatch(ns: list[Node], frag: dict) -> list[str]:
        placed = match_rows(ns, _real_rows)
        return [n.slug for n in ns
                if sorted(e["href"] for e in frag[n.slug]["backlog"])
                != sorted(page_markup.key_link("backlog", r["num"]) for r in placed[n.slug])]
    check("the page's backlog band lists exactly the rows match_rows places, for every node",
          (_band_mismatch(_real_nodes, collect(_real_nodes)[0]),
           _band_mismatch(tagged, collect(tagged)[0])), ([], []))

    # ── THE TREE INDEX, THE GAP SUMMARY AND THE FOLD (owner, 2026-11-23) ──────────────────────
    # "the features page is very long and it doesn't show feature list and hierarchical relationship
    # of features" and "'explanation-on-demand' still has many open backlogs, while the feature is in
    # 'Built' state". Three answers: an index first, a gap count beside every state badge, and every
    # card folded.
    _order = sev_order()

    def _caught(f):
        try:
            return f()
        except Exception as e:  # noqa: BLE001 — reported as the case's observed value, never swallowed
            return f"raised {type(e).__name__}: {e}"
    # A lookup that finds nothing reads as "", so a mutation that moves an id reds the cases that
    # read it and the run CONTINUES to the case its manifest names (an AttributeError stopped it).
    _found = lambda m, i: m.group(i) if m else ""
    _g = lambda num, glyph, closed=False: {"label": f"#{num} {glyph} t", "sev": glyph,
                                            "href": f"/backlog-table#i{num}", "closed": closed}
    _frag = {"job-queue": {"backlog": [_g(1, "🟡"), _g(2, "🟢"), _g(3, "🟠"), _g(4, "🟡"),
                                       _g(5, "🔴", closed=True)]}}
    check("the gap summary counts OPEN rows by severity, in the backlog's severity order",
          (gap_label(open_gaps(_frag["job-queue"]), _order), gap_label([], _order),
           gap_label([_g(9, "🟢")], _order), gap_label(open_gaps(_frag["job-queue"]), _order[::-1]),
           # review r1 m2: a plain-string row counts as `·`; a glyph outside `order` is shown LAST
           # (a raise is caught, so a red here is a `[FAIL]` line the mutation harness can read).
           _caught(lambda: gap_label(["plain", {"sev": "🔶"}, _g(1, "🟡")], _order))),
          ("4 gaps (1🟠 2🟡 1🟢)", "0 gaps", "1 gap (1🟢)", "4 gaps (1🟢 2🟡 1🟠)", "3 gaps (1🟡 1· 1🔶)"))
    _tree = render(nested + nodes, _frag)
    _ix_at, _card_at = _tree.find('class="tindex"'), _tree.find('<details class="node')
    check("the index is rendered before the first card",
          (_ix_at != -1, _card_at != -1, -1 < _ix_at < _card_at), (True, True, True))
    _ix = render_index(nested + nodes, _frag, _order)
    check("the index lists every node in file order, a `####` nested one list deeper than its `###`",
          (index_shape(_ix), index_shape(render_index(nodes, _frag, _order))),
          ([(1, "f-job-queue"), (2, "f-wake-on-visit"), (1, "f-wake-on-visit"), (1, "f-dig-job-recovery")],
           [(1, f"f-{n.slug}") for n in nodes]))
    # The index reads the severity order it is GIVEN, not a constant of its own.
    check("the index line orders severities as the order it is passed says",
          "4 gaps (1🟢 2🟡 1🟠)" in _found(re.search(r'href="#f-job-queue">(.*?)(?:</li>|<ul>)',
                                                    render_index(nested + nodes, _frag, _order[::-1]),
                                                    re.S), 1), True)
    # ⛔ ONE COUNTING RULE: the index line and the card heading both read `open_gaps` — a node WITH
    # gaps (one closed row excluded) and a node WITHOUT.
    _line = lambda slug: _found(re.search(rf'href="#{frag_id(slug)}">(.*?)(?:</li>|<ul>)', _ix, re.S), 1)
    _head = lambda slug: _found(re.search(rf'id="{frag_id(slug)}"[^>]*>\s*<summary.*?</summary>', _tree, re.S), 0)
    check("a node's index line and card heading carry the same gap count, with gaps and without",
          ("4 gaps (1🟠 2🟡 1🟢)" in _line("job-queue"), "4 gaps (1🟠 2🟡 1🟢)" in _head("job-queue"),
           # ⟳ node-tree Task 4: the gapless node is `wake-on-visit`, which INHERITS job-queue's
           # area — `dig-job-recovery` claims none, so it now says "claims no area" (spec §3.2).
           "0 gaps" in _line("wake-on-visit"), "0 gaps" in _head("wake-on-visit")),
          (True, True, True, True))
    check("the index line carries the node's state, as the card says it",
          ("built" in _line("job-queue"), "not built" in _line("dig-job-recovery")), (True, True))
    # ⛔ OVER THE REAL TREE: every node's index count is the card's own open-row count.
    _rfrag = collect(_real_nodes)[0]
    _rix = render_index(_real_nodes, _rfrag, _order)
    _rby = by_slug(_real_nodes)
    # ⟳ node-tree Task 4: a real node that claims and inherits no area carries the sentence instead.
    _bad = [n.slug for n in _real_nodes
            if (gap_label(open_gaps(_rfrag[n.slug]), _order) if n.areas or inherits_area(n, _rby)
                else "claims no area — gaps not counted")
            not in _found(re.search(rf'href="#{frag_id(n.slug)}">(.*?)(?:</li>|<ul>)', _rix, re.S), 1)]
    # ...and each counted row's severity is the one its own Known-gaps line shows (`#N <glyph> …`).
    _sevless = [e["label"] for n in _real_nodes for e in open_gaps(_rfrag[n.slug])
                if e["label"].split()[1] != e.get("sev")]
    check("over the REAL tree, every index line's count is the card's own open-row count, by severity",
          (len(_real_nodes) > 30, _bad, _sevless[:3]), (True, [], []))
    # ⛔ S1 r1 (Claude F6): the case above derives WHICH nodes carry the sentence through
    # `inherits_area`, the predicate under test. This one reads the rendered index and compares it to an
    # INDEPENDENT LITERAL — the live nodes that claim and inherit no area: 4 measured at S1, and 6 more
    # at node-tree Task 12 (the three trunks, `token-usage`, `memory-recall`, `memory-hygiene` — spec
    # §4.1, 4.13, 4.23, 4.25–4.27). ⚠ A tree edit that gives one an area, or adds another, is meant to
    # redden this; update the literal by hand.
    check("over the REAL tree, the nodes that claim no area are exactly these",
          sorted(n.slug for n in _real_nodes
                 if NO_AREA in _found(re.search(rf'href="#{frag_id(n.slug)}">(.*?)(?:</li>|<ul>)', _rix, re.S), 1)),
          ["cloud-sync", "dev-infrastructure", "memory-hygiene", "memory-recall", "platform", "product",
           "serve-path-bounding", "share-and-download", "shared-dig-deeper", "token-usage"])
    _cards = re.findall(r"<details class=\"node[^\"]*\"[^>]*>", _tree)
    check("every card is a <details>, and every one is FOLDED",
          (len(_cards), [c for c in _cards if " open" in c]), (len(nested + nodes), []))
    check("every index link targets a card's id",
          sorted(set(re.findall(r'href="#([a-z0-9-]+)"', _ix)))
          == sorted(set(re.findall(r'<details class="node[^"]*" id="([a-z0-9-]+)"', _tree))), True)

    # ── ANY DEPTH, TRUNK NODES, STATELESS AND AREA-LESS NODES (node-tree plan Task 4) ───────────
    # Every case that asserts HTML also asserts it PARSES: `html.parser` reads it, and every
    # `<ul>`/`<li>`/`<div>`/`<details>` it opens is closed in order (a recursion that forgets a close
    # tag renders, and nests everything after it one level too deep).
    from html.parser import HTMLParser as _HP

    class _Balance(_HP):
        _PAIRED = {"ul", "li", "div", "nav", "section", "details", "summary"}

        def __init__(self) -> None:
            super().__init__()
            self.stack: list[str] = []
            self.bad = False

        def handle_starttag(self, tag, attrs) -> None:
            if tag in self._PAIRED:
                self.stack.append(tag)

        def handle_endtag(self, tag) -> None:
            if tag in self._PAIRED and (not self.stack or self.stack.pop() != tag):
                self.bad = True

    def _parses(markup: str) -> bool:
        p = _Balance()
        p.feed(markup)
        p.close()
        return not p.bad and not p.stack and "<ul" in markup

    # The literal is the BASE's rendering (master 561379e6) of this fixture, captured before the
    # rework: two slugless trunks, `###` and `####`, every node counted. Byte-for-byte.
    _two, _ = parse_features(
        "## PLATFORM\n### job-queue\nstate: built\nfor: Q.\nareas: (worker)\n"
        "#### wake-on-visit\nstate: absent\nfor: W.\nexpected-because: e.\n"
        "### jobs-ui\nstate: built\nfor: J.\nareas: (ui)\n"
        "## DEV\n### harness\nstate: built\nfor: H.\nareas: (tooling)\n")
    _two_ix = render_index(_two, {"job-queue": {"backlog": [_g(1, "🟡"), _g(2, "🟠")]},
                                  "harness": {"backlog": [_g(3, "🟢")]}}, _order)
    check("index: today's two levels render unchanged",
          (_two_ix, _parses(_two_ix)),
          ('<nav class="tindex" aria-label="Feature tree">\n<p class="ilab">Feature tree · each line '
           'counts its own node’s open gaps · select a line to open its card</p>\n<div class="igroup">'
           '<span class="iname">PLATFORM</span><ul>\n<li><a href="#f-job-queue">job-queue</a> '
           '<span class="state built">built</span> <span class="gaps open">2 gaps (1🟠 1🟡)</span>\n'
           '<ul><li><a href="#f-wake-on-visit">wake-on-visit</a> <span class="state notbuilt">not '
           'built</span> <span class="gaps">0 gaps</span></li></ul>\n</li>\n<li><a href="#f-jobs-ui">'
           'jobs-ui</a> <span class="state built">built</span> <span class="gaps">0 gaps</span>\n'
           '</li>\n</ul></div>\n<div class="igroup"><span class="iname">DEV</span><ul>\n<li><a href='
           '"#f-harness">harness</a> <span class="state built">built</span> <span class="gaps open">'
           '1 gap (1🟢)</span>\n</li>\n</ul></div>\n</nav>', True))

    _five, _ = parse_features(
        "## DEEP\nslug: deep\nfor: The trunk.\n"
        "### l3\nstate: built\nfor: Three.\nareas: (worker)\n#### l4\nstate: built\nfor: Four.\n"
        "##### l5\nstate: built\nfor: Five.\n###### l6\nstate: built\nfor: Six.\n"
        "#### m4\nstate: built\nfor: Back up.\n### n3\nstate: built\nfor: Sibling.\nareas: (ui)\n")
    _five_ix, _five_page = render_index(_five, {}, _order), render(_five, {})
    check("index: five levels nest in file order",
          (index_shape(_five_ix), [_five_page.count(f'id="f-{s}"') for s in ("l3", "l4", "l5", "l6", "m4")],
           _parses(_five_ix), _parses(_five_page)),
          ([(0, "f-deep"), (1, "f-l3"), (2, "f-l4"), (3, "f-l5"), (4, "f-l6"), (2, "f-m4"), (1, "f-n3")],
           [1, 1, 1, 1, 1], True, True))

    _orph, _ = parse_features("## LOOSE\n#### orphan\nstate: built\nfor: First, and deep.\n"
                              "areas: (worker)\n### after\nstate: built\nfor: After.\nareas: (ui)\n")
    _orph_ix, _orph_page = render_index(_orph, {}, _order), render(_orph, {})
    check("index: an orphan level is kept",
          (index_shape(_orph_ix), _orph_page.count('id="f-orphan"'), _parses(_orph_ix), _parses(_orph_page)),
          ([(1, "f-orphan"), (1, "f-after")], 1, True, True))

    _trk, _ = parse_features("## PRODUCT\nslug: product\nfor: What the product does.\nareas: (ui)\n"
                             "### viewer\nstate: built\nfor: Shows a summary.\n")
    _trk_ix, _trk_page = render_index(_trk, {}, _order), render(_trk, {})
    check("index: a trunk node is linked and carded",
          ('<span class="iname"><a href="#f-product">PRODUCT</a>' in _trk_ix,
           _trk_page.count('id="f-product"'),
           -1 < _trk_page.find('<h2 class="tname">PRODUCT</h2>') < _trk_page.find('id="f-product"')
           < _trk_page.find('id="f-viewer"'),
           _parses(_trk_ix), _parses(_trk_page)),
          (True, 1, True, True, True))

    # `quiet` has no fragment at all: a stateless node may be bare, and is not "should have been refused".
    _sl, _ = parse_features("## GOALS\n### speed\nfor: Faster work.\nareas: (worker)\n"
                            "### quiet\nfor: Nothing under it yet.\nareas: (ui)\n")
    _sl_frag = {"speed": {"backlog": [_g(7, "🟢")]}}
    _sl_ix, _sl_page = render_index(_sl, _sl_frag, _order), render(_sl, _sl_frag)
    _sl_head = _found(re.search(r'id="f-speed"[^>]*>\s*<summary.*?</summary>', _sl_page, re.S), 0)
    check("index: a stateless node shows no badge",
          ('class="state' in _sl_ix, "1 gap (1🟢)" in _sl_ix, 'class="state' in _sl_head,
           "1 gap (1🟢)" in _sl_head, "Built, but" in _sl_page, _parses(_sl_ix), _parses(_sl_page)),
          (False, True, False, True, False, True, True))

    _na, _ = parse_features("## GOALS\n### recall\nstate: built\nfor: Finds the right memory.\n"
                            "adrs: 0003\n")
    _na_ix, _na_page = render_index(_na, {}, _order), render(_na, {})
    _na_head = _found(re.search(r'id="f-recall"[^>]*>\s*<summary.*?</summary>', _na_page, re.S), 0)
    check("index: a node claiming and inheriting no area says so",
          ("claims no area — gaps not counted" in _na_ix, "0 gaps" in _na_ix,
           "claims no area — gaps not counted" in _na_head, "0 gaps" in _na_head,
           _parses(_na_ix), _parses(_na_page)),
          (True, False, True, False, True, True))

    _inh, _ = parse_features("## GOALS\n### parent\nstate: built\nfor: P.\nareas: (worker)\n"
                             "#### child\nstate: built\nfor: C.\n##### grandchild\nstate: built\nfor: G.\n")
    _inh_by = by_slug(_inh)
    _inh_ix = render_index(_inh, {}, _order)
    check("index: an inherited area still counts",
          (inherits_area(_inh_by["child"], _inh_by), inherits_area(_inh_by["grandchild"], _inh_by),
           inherits_area(_inh_by["parent"], _inh_by), inherits_area(_inh_by["child"], {}),
           "claims no area" in _inh_ix, _inh_ix.count("0 gaps"), _parses(_inh_ix)),
          (True, True, False, False, False, 3, True))
    # ⛔ THE HASH HANDLER, RUN (review r1: Claude M1, Codex M3). The script the PAGE carries is
    # executed against a stub DOM (`run_hash_script`); each behaviour is its own case, so removing
    # any one clause — the load call, the hashchange listener, the re-click handler, the DETAILS
    # guard, the scroll — reds the case that names it. A missing `node` is CANNOT RUN, never a pass.
    _page_js = [b for b in re.findall(r"<script>(.*?)</script>", _tree, re.S) 
                if b.strip() != page_chrome.chrome_script().strip()]
    _two = [["a", "DETAILS"], ["b", "DETAILS"]]
    _run = run_hash_script(_page_js[0] if _page_js else "", [
        {"name": "load", "hash": "#a", "els": _two},
        {"name": "change", "hash": "", "els": _two, "steps": [{"hash": "#b", "fire": "hashchange"}]},
        {"name": "reclick", "hash": "#a", "els": _two,
         "steps": [{"fold": "a"}, {"fire": "click", "href": "#a"}]},
        {"name": "notdetails", "hash": "#p", "els": [["p", "P"], ["a", "DETAILS"]]},
        {"name": "missing", "hash": "#nope", "els": _two},
        {"name": "malformed", "hash": "#%E0%A4%A", "els": _two}])
    _obs = (lambda k: _run if isinstance(_run, str) else _run.get(k))
    # ...and the stub can say NO: a script that opens nothing is observed opening nothing.
    _none = run_hash_script("void 0;", [{"name": "load", "hash": "#a", "els": _two}])
    check("the stub DOM observes a failure: a script that opens nothing leaves card a folded",
          _none if isinstance(_none, str) else _none["load"], {"err": None, "open": [], "scrolled": []})
    check("the page's hash handler, RUN: a link loaded with #a opens card a and scrolls it into view",
          _obs("load"), {"err": None, "open": ["a"], "scrolled": ["a"]})
    check("the page's hash handler, RUN: a later hash change to #b opens card b",
          _obs("change"), {"err": None, "open": ["b"], "scrolled": ["b"]})
    check("the page's hash handler, RUN: re-clicking the CURRENT hash's link reopens a re-folded card",
          _obs("reclick"), {"err": None, "open": ["a"], "scrolled": ["a"]})
    check("the page's hash handler, RUN: a hash naming a non-<details> element opens nothing",
          _obs("notdetails"), {"err": None, "open": [], "scrolled": []})
    check("the page's hash handler, RUN: a hash naming no element, or a malformed escape, throws nothing",
          (_obs("missing"), _obs("malformed")),
          ({"err": None, "open": [], "scrolled": []}, {"err": None, "open": [], "scrolled": []}))

    # ⛔ ONE ID PER NODE, SAFE FOR ANY NAME (review r1, Codex M1). A heading is free text, so a
    # name may carry `#`, `?`, `%`, a space, `&`, non-ASCII. Every index link must name its OWN card,
    # no two cards may share an id, and the handler — RUN — must open the card each link names.
    # `s p` and `s_20_p` are the collision pair an encoding that left `_` bare would merge.
    _odd_names = ["100% complete", "a#b", "q?x", "s p", "s_20_p", "a&b", "café", "a_b", "a-b"]
    _odd, _ = parse_features("## ODD\n" + "".join(
        f"### {nm}\nstate: built\nfor: Odd name.\n" for nm in _odd_names))
    _odd_page = render(_odd, {})
    _odd_ids = re.findall(r'<details class="node[^"]*" id="([^"]*)"', _odd_page)
    _odd_hrefs = re.findall(r'<a href="(#[^"]*)"', render_index(_odd, {}, _order))
    _odd_run = run_hash_script(_page_js[0] if _page_js else "", [
        {"name": h, "hash": "", "els": [[html_lib.unescape(i), "DETAILS"] for i in _odd_ids],
         "steps": [{"hash": html_lib.unescape(h), "fire": "hashchange"}]} for h in _odd_hrefs])
    # The stub sets `location.hash` verbatim; a browser percent-encodes a space, `%` or non-ASCII
    # first, so an href that matched only verbatim would still miss. Hence the character class.
    check("every node name, however odd, gets a distinct id its index link opens when RUN",
          (len(_odd_ids), len(set(_odd_ids)), len(_odd_hrefs),
           [h for h in _odd_hrefs if not re.fullmatch(r"#[A-Za-z0-9_-]+", h)],
           _odd_run if isinstance(_odd_run, str) else
           [len(_odd_run[h]["open"]) == 1 and _odd_run[h]["err"] is None for h in _odd_hrefs]),
          (len(_odd_names), len(_odd_names), len(_odd_names), [], [True] * len(_odd_names)))

    # ⛔ A CARD ID NEVER COLLIDES WITH PAGE CHROME (review r2, Codex R2-1). A node may be NAMED like
    # a chrome control; `getElementById` returns the FIRST element with an id — the chrome's, which
    # comes first — so that node's index link would open nothing. Every id on the page is read back
    # through the page tokenizer, and the handler is RUN against all of them in document order.
    _cn_names = ["chrome-theme", "schemer", "chrome-refresh", "chrome-refresh-say"]
    _cn, _ = parse_features("## CHROME\n" + "".join(
        f"### {nm}\nstate: built\nfor: Named like a chrome control.\n" for nm in _cn_names))
    _ids_of = lambda page: [(dict(t.attrs)["id"], t.tag.upper()) for t in page_markup.page_tokens(page)[0]
                            if t.kind == "start" and dict(t.attrs).get("id")]
    _cn_ids = _ids_of(render(_cn, {}))
    _cn_hrefs = re.findall(r'<a href="(#[^"]*)"', render_index(_cn, {}, _order))
    _cn_run = run_hash_script(_page_js[0] if _page_js else "", [
        {"name": h, "hash": "", "els": [list(x) for x in _cn_ids],
         "steps": [{"hash": html_lib.unescape(h), "fire": "hashchange"}]} for h in _cn_hrefs])
    _ids_only = [i for i, _ in _cn_ids]
    # The stub's first-wins rule is itself observed: a `<p>` before a `<details>` of the same id
    # opens nothing, as in a browser — without it, the duplicate above would pass the RUN half.
    _dup = run_hash_script(_page_js[0] if _page_js else "",
                           [{"name": "dup", "hash": "#a", "els": [["a", "P"], ["a", "DETAILS"]]}])
    check("a node named like a chrome control: every id on the page is unique, and its link opens its card",
          (sorted({i for i in _ids_only if _ids_only.count(i) > 1}), len(_cn_hrefs),
           _cn_run if isinstance(_cn_run, str) else
           [_cn_run[h]["open"] == [html_lib.unescape(h[1:])] for h in _cn_hrefs],
           _dup if isinstance(_dup, str) else _dup["dup"]["open"]),
          ([], len(_cn_names), [True] * len(_cn_names), []))
    # ...and the reservation itself: no id a card-less page carries (chrome, every one of them) starts
    # with the card prefix, and a feature key's cross-page link (`key_link`) names the card's own id.
    check("no chrome id carries the card-id prefix, and key_link('feature') targets the card's id",
          (_caught(lambda: [i for i, _ in _ids_of(render([], {}))
                            if i.startswith(page_markup.FEATURE_ID_PREFIX)]),
           len(_ids_of(render([], {}))) > 0,
           [n.slug for n in _real_nodes
            if page_markup.key_link("feature", n.slug) != f"/features#{frag_id(n.slug)}"]),
          ([], True, []))

    # ⛔ THE COUNTS AGAINST THE RENDERED BAND (review r1, Codex M2): a card's heading and its index
    # line must equal the OPEN rows its own Known-gaps band LISTS, read back from the page markup
    # by `rendered_gap_counts` — never from `open_gaps`/`gap_label`, the code under test. Fixture:
    # rows past GAP_CAP, closed rows, a plain-string row, and a row shared by two nodes (two tags).
    # ⟳ Review r2 (Codex R2-2): the band's rows are compared by IDENTITY — key and severity, open and
    # closed, in order — against EXPECTED SETS WRITTEN OUT BY HAND below, never derived from the
    # fixture by the code under test. Severities are literals, so the fixture does not lean on
    # `sev_order` either. 13 open rows exceed GAP_CAP (10), so #20–#22, #90 and #100 are the capped
    # ones behind "more"; #100 is the row shared by two nodes; #91, #92 and #94 are closed.
    _shared = _g(100, "🟠")
    _sev13 = ["🔴", "🟠", "🟡", "🟢", "🟠", "🟡", "🟡", "🔴", "🟢", "🟠", "🟡", "🟢", "🔴"]
    _many_rows = ([_g(10 + i, g) for i, g in enumerate(_sev13)]
                  + ["#90 a plain row", _shared, _g(91, "🔴", closed=True), _g(92, "🟢", closed=True)])
    _many = {"job-queue": {"backlog": _many_rows},
             "wake-on-visit": {"backlog": [_shared, _g(93, "🟡"), _g(94, "🟠", closed=True)]}}
    _many_nodes = nested + [n for n in nodes if n.slug != "wake-on-visit"]   # one card per id
    _many_page = render(_many_nodes, _many)
    _expected_rows = {
        "f-job-queue": {"open": [("#10", "🔴"), ("#11", "🟠"), ("#12", "🟡"), ("#13", "🟢"),
                                 ("#14", "🟠"), ("#15", "🟡"), ("#16", "🟡"), ("#17", "🔴"),
                                 ("#18", "🟢"), ("#19", "🟠"), ("#20", "🟡"), ("#21", "🟢"),
                                 ("#22", "🔴"), ("#90", "·"), ("#100", "🟠")],
                        "closed": [("#91", "🔴"), ("#92", "🟢")]},
        "f-wake-on-visit": {"open": [("#100", "🟠"), ("#93", "🟡")], "closed": [("#94", "🟠")]},
        "f-dig-job-recovery": {"open": [], "closed": []}}
    # Controls: ONE row's id swapped (#11 -> #999, same severity — the totals still agree, which is
    # exactly what the old comparator could not see), and ONE closed row rendered open.
    _swapped = {**_many, "job-queue": {"backlog": [_g(999, "🟠") if isinstance(e, dict) and
                                                   e["label"].startswith("#11 ") else e
                                                   for e in _many_rows]}}
    _reopened = {**_many, "wake-on-visit": {"backlog": [_shared, _g(93, "🟡"), _g(94, "🟠")]}}
    check("every card's rendered band lists exactly the rows written out for it, by id and severity",
          (_caught(lambda: row_disagreements(_many_page, _order, _expected_rows)),
           _caught(lambda: row_disagreements(render(_many_nodes, _swapped), _order, _expected_rows)),
           gap_disagreements(render(_many_nodes, _swapped), _order),
           _caught(lambda: row_disagreements(render(_many_nodes, _reopened), _order, _expected_rows)),
           # a card the expectation does not name, or names but the page lacks, disagrees too
           _caught(lambda: row_disagreements(_many_page, _order,
                                             {k: v for k, v in _expected_rows.items()
                                              if k != "f-dig-job-recovery"} | {"f-gone": {"open": [], "closed": []}})),
           # ...and an id two cards share (the nested fixture renders wake-on-visit twice, alike)
           _caught(lambda: row_disagreements(render(nested + nodes, _many), _order, _expected_rows)),
           # the order is READ: under 🟠 alone, every other glyph reads `·`, so two cards disagree
           _caught(lambda: row_disagreements(_many_page, _order[1:2], _expected_rows))),
          ([], ["f-job-queue"], [], ["f-wake-on-visit"], ["f-dig-job-recovery", "f-gone"],
           ["f-wake-on-visit"], ["f-job-queue", "f-wake-on-visit"]))
    check("every card's heading and index line count exactly the open rows its rendered band lists",
          (gap_disagreements(_many_page, _order),
           gap_disagreements(render(_real_nodes, _rfrag), _order),
           # the comparator can say no: read under an empty order, every severity disagrees
           gap_disagreements(_many_page, []),
           # the reader itself, on a second page and a second order: a glyph outside it reads `·`
           # (read with `.get`, S1 r3 class search after Claude F1: a dropped card FAILS, never raises)
           rendered_gap_counts(_tree, _order).get("f-job-queue", {}).get("rows"),
           rendered_gap_counts(_tree, _order[1:2]).get("f-job-queue", {}).get("rows"),
           rendered_gap_counts(_many_page, _order).get("f-wake-on-visit", {}).get("closed")),
          ([], [], ["f-job-queue", "f-wake-on-visit"],
           [("#1", "🟡"), ("#2", "🟢"), ("#3", "🟠"), ("#4", "🟡")],
           [("#1", "·"), ("#2", "·"), ("#3", "🟠"), ("#4", "·")], [("#94", "🟠")]))
    # ⛔ THE EMITTED ARTIFACT PARSES — the HTML is in the supported subset, the script is a program.
    _js = scripts_parse(_tree)
    check("the emitted page is in the supported HTML subset and every inline script parses",
          (page_markup.subset_problems(_tree), _js), ([], []))
    # ...and the parse check can say no: a script that is not a program, and a page with none.
    _bad_js = scripts_parse("<p>x</p><script>function (</script>")
    check("the script check reports a script that does not parse, and a page with no script",
          (len(_bad_js), _bad_js[0][:9] if _bad_js else "", scripts_parse("<p>x</p>")[0][:9]),
          (1, "script 0:", "no inline"))

    # ── THE REGEN HOOK ──────────────────────────────────────────────────────────────────────────
    # ⭐ Code review r1 (Codex), Low. `.claude/hooks/regen-features-page.sh` is the ONLY thing that
    # keeps this page from going stale, and it is shell: no `--self-test` of its own, and it cannot
    # be given a mutation either — `check-plan-code.load_manifests` requires every entry's `file`
    # to equal `scripts/<manifest stem>.py`, and `run_suite` runs the mutated file AS a Python
    # suite, so a `.sh` target would red its own control. The same is true of
    # `.claude/hooks/regen-backlog-page.sh`, whose four cases in `gen-backlog-page.py` set the
    # PLACEMENT precedent: coverage for a hook lives in the suite of the generator it calls.
    # ⚠ THAT IS ALL THEY SET — code review r2 (Claude). Those cases do not RUN their hook; they
    # read the awk program out of the shell file and run `awk` (`gen-backlog-page.py:2818`).
    # Running the shell script itself, below, is new here and is strictly stronger than the
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

    # ⛔ goal node tree Task 7: `collect` over a WORLD — the real ADRs and backlog, symlinked; NO
    # registry file; one spec naming `probe-a`, one plan naming `probe-b`. Three nodes so a document
    # attached by anything but the node's own slug lands under the wrong one, and an ADR read from
    # anywhere but `adrs:` is missed.
    _gw = globals()
    _keep_docs = _gw["DOCS"]
    with tempfile.TemporaryDirectory() as _wd:
        _w = pathlib.Path(_wd) / "docs"
        _w.mkdir()
        for _name in ("adr", "backlog.md", "features.md"):
            (_w / _name).symlink_to(_keep_docs / _name)
        for _sub, _slug in (("specs", "probe-a"), ("plans", "probe-b")):
            (_w / "superpowers" / _sub).mkdir(parents=True)
            (_w / "superpowers" / _sub / f"2026-01-01-{_slug}.md").write_text(
                f"# {_slug}\n\n> **Anchor:** `{_slug}` — **ADR:** none\n")
        _pn, _ = parse_features("## T\n### probe-a\nstate: built\nfor: A.\n"
                                "### probe-b\nstate: built\nfor: B.\nadrs: 0010, 0016\n"
                                "### probe-c\nstate: built\nfor: C.\nadrs: 0003\n")
        _gw["DOCS"] = _w
        try:
            _wf, _wn = collect(_pn)
        except Exception as e:      # a read of the absent registry is a crash, and the case names it
            _wf, _wn = {"error": f"{type(e).__name__}: {e}"}, {}
        finally:
            _gw["DOCS"] = _keep_docs
        _world = sorted(p.name for p in _w.iterdir())
    _adr_title = {p.name[:4]: p.name[5:-3].replace("-", " ") for p in (DOCS / "adr").glob("[0-9]*.md")}
    check("collect: runs with no registry file", (_world, sorted(_wf)),
          (["adr", "backlog.md", "features.md", "superpowers"], ["probe-a", "probe-b", "probe-c"]))
    check("collect: ADRs come from the node's adrs",
          [[e["label"] for e in _wf.get(s, {}).get("adr", [])] for s in ("probe-a", "probe-b", "probe-c")],
          [[], [f"ADR-0010 · {_adr_title['0010']}", f"ADR-0016 · {_adr_title['0016']}"],
           [f"ADR-0003 · {_adr_title['0003']}"]])
    check("collect: documents attach by the node's own slug",
          [_wf.get(s, {}).get("docs") for s in ("probe-a", "probe-b", "probe-c")],
          [[{"label": "2026-01-01-probe-a.md", "href": "/src/docs/superpowers/specs/2026-01-01-probe-a.md"}],
           [{"label": "2026-01-01-probe-b.md", "href": "/src/docs/superpowers/plans/2026-01-01-probe-b.md"}],
           []])

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
    # Every `PR #N` this page renders links to GitHub (backlog #470); no GitHub remote -> plain text.
    page_markup.use_repo(page_markup.origin_repo(ROOT))

    for p in (DOCS / "features.md", DOCS / "backlog.md"):
        if not p.is_file():
            print(f"CANNOT RUN — {p} is missing. Treat this as NOT RUN.", file=sys.stderr)
            return 2

    nodes, problems = parse_features((DOCS / "features.md").read_text())
    if not nodes:
        print("CANNOT RUN — docs/features.md declares no nodes. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2
    try:
        # A `backlog #N` naming no row is marked text, not a link to nothing (backlog #470).
        page_markup.use_rows(r["num"] for r in backlog_rows())
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
    # Every key left as TEXT by whichever path rendered it becomes a link (backlog #470).
    fragment = page_markup.link_html(fragment, page_markup.REPO)

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

#!/usr/bin/env python3
"""Refuse a document set where one rule is stated in several places and the fold updated only some.

    python3 scripts/check-claim-propagation.py --self-test # 31 cases against synthetic trees

WHY THIS EXISTS
---------------
Measured on `marketplace-inventory`, 2026-10-16. Two adversarial rounds produced 18 then 31
findings, and **18 of the second round's were introduced by the first round's own fix.** Round 2's
Claude half isolated one mechanism behind thirteen of fourteen:

    a rule is stated in more than one place, and the fold updates the site the finding named.

Per finding, the site updated against the site that was not: the spec against the page (four
separate contradictions in one artifact pair); `§5` which *asserts* who derives the shipping-set
declaration against `§7 item 2` which was supposed to *contain* it; `§6` which *requires* an
isolation baseline against `§7` which produces nothing; `§4`'s aggregation row against `§4b`'s
completeness rule. Round 1's Blocking B3 — *"§5 requires a declared set; nothing in §7 produces
one"* — then **recurred one round later in the same pair of sections**, which is the datum that
armed the architecture review.

⛔ **THE REMEDY IS NOT A CONVENTION, BECAUSE A CONVENTION IS WHAT FAILED.** The coordinator wrote the
mechanism against itself after round 2 — *"I folded the spec thoroughly and the page partially"* —
and then did it again in the very next round. A fold checklist that must be remembered competes with
the same recall that produced the defect. This guard is the mechanical half.

WHAT IT CHECKS, AND WHAT IT CANNOT
----------------------------------
1. **A RETIRED claim is not re-asserted.** When a fold retires a rule, the rule's distinctive token
   goes in `RETIRED` below. The token may then appear *only inside a marked retirement block* — a
   block that also says it is a correction. An unmarked occurrence is an assertion of a rule the
   document has replaced, which is what the human would read and approve.

2. **A LIVE claim reaches every site that must state it.** When a rule must be stated at several
   sites, `LIVE` records the token and those sites. A token present at some and absent at others is
   the exact defect above: `§5` asserting what `§7` does not contain.

3. **A DERIVED figure agrees with its source.** The page carries `data-derived="spec-lines"`; its
   text must equal the spec's real line count. Measured: the page said *"213-line spec"* for a
   669-line spec, having been recomposed four times without the figure being re-derived.

⚠ **WHAT IT CANNOT DO, stated rather than discovered.** It cannot tell that two sentences *mean* the
same thing — only that a declared token is present or absent. A rule restated in words no token
matches is invisible to it. So this guard shrinks the class; it does not close it, and
`REGISTRY_IS_INCOMPLETE` below says so in the code rather than only in prose.

⛔ **AND IT IS NOT A SPELL-CHECKER FOR PROSE ABOUT THE RULES.** Every one of these documents quotes
its own retired claims deliberately, to record what changed — that is the house style and it is why
the marked-block exemption exists rather than a blanket ban. `check-plan-file-tags.py` paid for this
lesson first: a bare substring test broke thirteen documents that merely *discussed* a tag.
"""

from __future__ import annotations

import argparse
import html.parser
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# The registry. ONE OWNER: this file. A claim retired by a fold is recorded here
# in the same commit as the fold, which is the only moment anyone knows the token.
# ─────────────────────────────────────────────────────────────────────────────

SPEC = "docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md"
PAGE = "docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html"
PAGE_HTML = "docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.html"

# A retired claim: its token must appear only inside a marked retirement block.
RETIRED: list[dict] = [
    {
        "id": "inheritance-unqualified",
        "token": "inherits its support verdict from the",
        "why": "r2 refuted it: undefined for >1 importer, silently wrong for none; §4 now has five rules",
        "sites": [SPEC, PAGE],
    },
    {
        "id": "figure-origin-misattributed",
        "token": "the commit that wrote the figure",
        "why": "r2 CODEX 9: cacbac17 measured it; 100cf498 republished it already 3.7% stale",
        "sites": [SPEC, PAGE],
    },
    {
        "id": "d5-undecided",
        "token": "deliberately did not decide for you",
        "why": "the owner settled it 2026-10-16; it is D5, a decision of record",
        "sites": [SPEC, PAGE],
    },
    {
        "id": "spec-length-213",
        "token": "213-line spec",
        "why": "r2 CLAUDE B2: the spec is not 213 lines and the figure is now derived",
        "sites": [SPEC, PAGE],
    },
    {
        "id": "criteria-mechanically-countable",
        "token": "mechanically countable",
        "why": "r1 CLAUDE H4 / r1 CODEX 4: counting gives the wrong answer in both directions",
        "sites": [SPEC, PAGE],
    },
    {
        "id": "falsifier-any-blocker",
        "token": "any blocker the install experiment hits",
        "why": "r1 CLAUDE B2: the failure that matters is a degraded result, not a blocker",
        "sites": [SPEC, PAGE],
    },
]

# A live claim: its token must be present at EVERY site listed.
LIVE: list[dict] = [
    {
        "id": "shipping-set-deriver",
        "token": "never reads the scan's output",
        "why": "§5 asserts §7 item 2 names the deriver; r2 CLAUDE H1 found it named neither",
        "sites": [SPEC],
    },
    {
        "id": "isolation-baseline-producer",
        "token": "ISOLATION BASELINE",
        "why": "§6 requires a baseline; r2 CLAUDE H2 found nothing in §7 produced one",
        "sites": [SPEC],
    },
    {
        "id": "plugin-root-self-location",
        "token": "CLAUDE_PLUGIN_ROOT",
        "why": ("asked by the owner from the page 2026-10-16: the collision is not the directory "
                "NAME, it is CWD-relative resolution. Both installed third-party plugins keep "
                "scripts/ and use this variable. Registered at both sites in the same commit"),
        "sites": [SPEC, PAGE],
    },
    {
        "id": "experiment-two-tiers",
        "token": "falsifier for tier A",
        "why": ("asked by the owner from the page 2026-10-16: a real third-party repo is the "
                "falsifier for the seeded throwaway, not a replacement for it. Registered at both "
                "sites in the same commit that adds it"),
        "sites": [SPEC, PAGE],
    },
    {
        "id": "d6-harvest-axis",
        "token": "harvest",
        "why": ("D6, settled by the owner 2026-10-16 from the page: a DON'T-SHIP component can "
                "still yield a transferable practice. Registered at both sites in the same commit "
                "that adds it, which is the discipline C5 had to learn the hard way"),
        "sites": [SPEC, PAGE],
    },
    {
        "id": "c5-redistributable",
        "token": "Redistributable",
        "why": ("r2 CLAUDE M10: added to the spec and NOT the page — the propagation mechanism "
                "recurring a third time, caught by executing the page. Registered at both sites "
                "so the next fold cannot drop one"),
        "sites": [SPEC, PAGE],
    },
    {
        "id": "inheritance-attribution-test",
        "token": "ATTRIBUTED TO CODE IN THAT LIBRARY",
        "why": "r2 CLAUDE H5: without it, page_chrome.py inherits a credential failure it never touches",
        "sites": [SPEC],
    },
]

# Derived figures: an element carrying data-derived="<key>" whose text must equal a computed value.
DERIVED: list[dict] = [
    {
        "key": "spec-lines",
        "page": PAGE,
        "compute": "line-count-of",
        "source": SPEC,
        "why": "r2 CLAUDE B2: the page said 213 for a 669-line spec after four recompositions",
    },
]

# ⛔ Stated in the code, not only in the docstring: this registry is a floor, not a closure.
# A rule restated in words no token above matches is invisible to this guard.
REGISTRY_IS_INCOMPLETE = True

# A block counts as a marked retirement when it carries one of these. Deliberately narrow:
# each is a token this project already uses to mark a correction, so the exemption cannot be
# satisfied by ordinary prose that happens to mention the rule.
RETIREMENT_MARKERS = (
    "⟳",  # ⟳ — this project's correction glyph
    "SUPERSEDED",
    "superseded",
    "previously",
    "refuted",
    "CORRECTED",
    "Corrected",
    "corrected",
    "retired",
    "RETIRED",
    "no longer",
)


class _Blocks(html.parser.HTMLParser):
    """Collect (text, attrs-of-enclosing-chain) for each HTML text node.

    A retired token inside an element whose class mentions `note`, or inside any element whose
    own text carries a retirement marker, is a quotation. Anything else is an assertion.
    """

    # Void elements never get an end tag, so they must not be pushed onto the stack —
    # otherwise one <br> inside a carrier leaves the carrier open for the rest of the document.
    VOID = frozenset(
        "area base br col embed hr img input link meta param source track wbr".split()
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        self.nodes: list[tuple[str, list[tuple[str, dict]]]] = []
        # key -> accumulated text, taken ONLY from nodes whose open-element chain still
        # contains the carrying element. Keyed first-wins so a later stray cannot overwrite.
        self.derived: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):  # noqa: D102
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag.lower() not in self.VOID:
            self.stack.append((tag, a))

    def handle_startendtag(self, tag, attrs):  # noqa: D102
        pass  # self-closing: no children, so it can carry no derived text

    def handle_endtag(self, tag):  # noqa: D102
        # close the most recent matching element, tolerating unclosed inline tags
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
        # no match: an end tag with no open partner. Ignore it rather than corrupting the stack.

    def handle_data(self, data):  # noqa: D102
        if not data.strip():
            return
        self.nodes.append((data, list(self.stack)))
        for _, a in self.stack:
            key = a.get("data-derived")
            if key:
                self.derived.setdefault(key, "")
                self.derived[key] += data.strip()


def _markdown_blocks(text: str) -> list[str]:
    """Blank-line-delimited blocks. A table is one block, so a row inherits its header's marker."""
    return [b for b in re.split(r"\n\s*\n", text) if b.strip()]


def _html_occurrences(text: str, token: str) -> tuple[int, int]:
    """Return (asserted, quoted) counts for `token` in an HTML fragment."""
    p = _Blocks()
    p.feed(text)
    asserted = quoted = 0
    for data, chain in p.nodes:
        if token not in data:
            continue
        classes = " ".join(a.get("class", "") for _, a in chain)
        if "note" in classes or any(m in data for m in RETIREMENT_MARKERS):
            quoted += 1
        else:
            asserted += 1
    return asserted, quoted


def _markdown_occurrences(text: str, token: str) -> tuple[int, int]:
    asserted = quoted = 0
    for block in _markdown_blocks(text):
        if token not in block:
            continue
        hits = block.count(token)
        if any(m in block for m in RETIREMENT_MARKERS):
            quoted += hits
        else:
            asserted += hits
    return asserted, quoted


def _derived_values(text: str) -> dict[str, str]:
    p = _Blocks()
    p.feed(text)
    return dict(p.derived)


def _tree_spec_lines(spec_text: str) -> int:
    """The value a synthetic page must declare. Used by the self-test so its fixture
    cannot drift from its own subject — the defect this guard exists to catch."""
    return len(spec_text.splitlines())


def _is_html(path: str) -> bool:
    return path.endswith((".html", ".htm"))


def audit(root: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return (problems, notes). A problem fails the gate; a note is reported and does not."""
    problems: list[str] = []
    notes: list[str] = []

    wanted = {s for c in RETIRED + LIVE for s in c["sites"]}
    wanted |= {d["page"] for d in DERIVED} | {d["source"] for d in DERIVED}
    missing = sorted(s for s in wanted if not (root / s).is_file())
    present = sorted(wanted - set(missing))

    if not present:
        raise CannotRun(
            "no registered document exists under "
            f"{root} — every one of {len(wanted)} registered path(s) is absent, so a clean "
            "result here would be a zero over nothing"
        )
    for m in missing:
        notes.append(f"registered path absent, not audited: {m}")

    cache: dict[str, str] = {}

    def read(rel: str) -> str:
        if rel not in cache:
            cache[rel] = (root / rel).read_text(encoding="utf-8")
        return cache[rel]

    # 1 — retired claims must not be asserted
    for claim in RETIRED:
        for site in claim["sites"]:
            if site in missing:
                continue
            text = read(site)
            fn = _html_occurrences if _is_html(site) else _markdown_occurrences
            asserted, quoted = fn(text, claim["token"])
            if asserted:
                problems.append(
                    f"RETIRED claim re-asserted: {claim['id']} — {asserted} unmarked "
                    f"occurrence(s) of {claim['token']!r} in {site}\n"
                    f"      why it was retired: {claim['why']}\n"
                    f"      fix: delete it, or put it in a block that marks it as a correction "
                    f"(one of {', '.join(RETIREMENT_MARKERS[:4])}…)"
                )
            elif quoted:
                notes.append(
                    f"{claim['id']}: {quoted} marked quotation(s) in {site} — allowed"
                )

    # 2 — live claims must reach every declared site
    for claim in LIVE:
        absent = [
            s for s in claim["sites"] if s not in missing and claim["token"] not in read(s)
        ]
        auditable = [s for s in claim["sites"] if s not in missing]
        if absent and len(absent) < len(auditable):
            problems.append(
                f"LIVE claim reached only some of its sites: {claim['id']} — "
                f"{claim['token']!r} is absent from {', '.join(absent)} but present elsewhere\n"
                f"      why it must be at every site: {claim['why']}"
            )
        elif absent and len(absent) == len(auditable):
            problems.append(
                f"LIVE claim absent from ALL its sites: {claim['id']} — {claim['token']!r} "
                f"found nowhere in {', '.join(auditable)}\n"
                f"      either the claim was removed and this registry is stale, or the fold "
                f"never landed: {claim['why']}"
            )

    # 3 — derived figures must agree with their source
    for spec in DERIVED:
        if spec["page"] in missing or spec["source"] in missing:
            continue
        found = _derived_values(read(spec["page"]))
        if spec["key"] not in found:
            problems.append(
                f"DERIVED figure absent: the page declares no "
                f'data-derived="{spec["key"]}" element in {spec["page"]}\n'
                f"      it must be present and correct, not hand-written: {spec['why']}"
            )
            continue
        if spec["compute"] != "line-count-of":
            raise CannotRun(f"unknown compute rule {spec['compute']!r}")
        actual = len(read(spec["source"]).splitlines())
        claimed_raw = found[spec["key"]]
        digits = re.sub(r"[^0-9]", "", claimed_raw)
        if not digits:
            problems.append(
                f"DERIVED figure is not a number: {spec['key']} reads {claimed_raw!r}"
            )
        elif int(digits) != actual:
            problems.append(
                f"DERIVED figure disagrees with its source: {spec['key']} says "
                f"{int(digits)}, {spec['source']} has {actual} lines\n"
                f"      {spec['why']}"
            )

    return problems, notes


class CannotRun(RuntimeError):
    """The guard could not reach what it measures. Exit 2 — never a pass."""


# ─────────────────────────────────────────────────────────────────────────────
# self-test
# ─────────────────────────────────────────────────────────────────────────────


def _self_test() -> int:
    import tempfile

    failures: list[str] = []
    n = 0

    def case(name: str, got, want) -> None:
        nonlocal n
        n += 1
        if got != want:
            failures.append(f"  [FAIL] {name}: got {got!r} want {want!r}")

    # ── the block/occurrence primitives, both languages, both directions
    md_assert = "A library inherits its support verdict from the entry-points.\n"
    md_quoted = "⟳ SUPERSEDED: it said a library inherits its support verdict from the x.\n"
    tok = "inherits its support verdict from the"
    case("md: bare assertion counts as asserted", _markdown_occurrences(md_assert, tok), (1, 0))
    case("md: marked block counts as quoted", _markdown_occurrences(md_quoted, tok), (0, 1))
    # ONLY the glyph marks this one, so removing the glyph from the vocabulary must bite.
    case(
        "md: the correction glyph alone marks a retirement",
        _markdown_occurrences("\u27f3 it said a library " + tok + " x\n", tok),
        (0, 1),
    )
    case("md: absent token is neither", _markdown_occurrences("nothing here\n", tok), (0, 0))
    case(
        "md: marker in a DIFFERENT block does not exempt",
        _markdown_occurrences("⟳ corrected elsewhere\n\n" + md_assert, tok),
        (1, 0),
    )
    case(
        "md: two assertions in one block are both counted",
        _markdown_occurrences(md_assert.strip() + " " + md_assert, tok),
        (2, 0),
    )
    html_assert = "<p>a library inherits its support verdict from the entry-points</p>"
    html_note = '<p class="note">it said a library inherits its support verdict from the x</p>'
    html_marked = "<p>⟳ a library inherits its support verdict from the x, refuted</p>"
    case("html: bare <p> is an assertion", _html_occurrences(html_assert, tok), (1, 0))
    case("html: class=note is a quotation", _html_occurrences(html_note, tok), (0, 1))
    case("html: inline marker is a quotation", _html_occurrences(html_marked, tok), (0, 1))
    case(
        "html: nested inside a note ancestor is a quotation",
        _html_occurrences('<div class="note"><span><em>' + tok + "</em></span></div>", tok),
        (0, 1),
    )
    case(
        "html: sibling note does not exempt an assertion",
        _html_occurrences('<p class="note">x</p>' + html_assert, tok),
        (1, 0),
    )

    # ── derived-figure extraction
    case(
        "derived: reads the attribute's text",
        _derived_values('<strong data-derived="spec-lines">669</strong>'),
        {"spec-lines": "669"},
    )
    case("derived: absent attribute yields nothing", _derived_values("<p>669</p>"), {})
    case(
        "derived: nested text is attributed to the carrier",
        _derived_values('<p data-derived="spec-lines"><em>771</em></p>'),
        {"spec-lines": "771"},
    )
    # A void element inside the carrier must not hold the carrier open past its end tag.
    # Without the VOID set, <br> is pushed and never popped, so every later text node on the
    # page is attributed to spec-lines and the figure reads as the whole document.
    case(
        "derived: a void element does not hold the carrier open",
        _derived_values(
            '<p data-derived="spec-lines">771<br></p><p>not part of the figure</p>'
        ),
        {"spec-lines": "771"},
    )
    # ⛔ THE CASE THAT MAKES `VOID` LOAD-BEARING. A void element cannot have children, so an
    # attribute on one carries NO text. Without the VOID set it is pushed, never popped by any
    # end tag, and the following prose is attributed to it. Measured: with this case absent,
    # deleting VOID entirely left 25/25 green — the fixture's silence, not the code's deadness.
    case(
        "derived: a void element carrying the attribute captures nothing",
        _derived_values('<img data-derived="spec-lines">771 lines of prose'),
        {},
    )
    case(
        "derived: text after the carrier closes is not attributed to it",
        _derived_values(
            '<strong data-derived="spec-lines">771</strong>-line spec, and more prose'
        ),
        {"spec-lines": "771"},
    )

    # ── the audit, against synthetic trees
    def tree(spec_text: str, page_text: str) -> pathlib.Path:
        d = pathlib.Path(tempfile.mkdtemp())
        (d / SPEC).parent.mkdir(parents=True, exist_ok=True)
        (d / PAGE).parent.mkdir(parents=True, exist_ok=True)
        (d / SPEC).write_text(spec_text, encoding="utf-8")
        (d / PAGE).write_text(page_text, encoding="utf-8")
        (d / PAGE_HTML).write_text(page_text, encoding="utf-8")
        return d

    live_tokens = "\n\n".join(c["token"] for c in LIVE)
    clean_spec = live_tokens + "\n"

    def page_for(spec_text: str) -> str:
        """Build the page from the spec it describes, so the fixture cannot drift from its own
        subject. Round 2's B2 was exactly a page whose figure no longer matched its spec, and a
        fixture that hard-codes the number reproduces that defect inside the test."""
        return f'<strong data-derived="spec-lines">{_tree_spec_lines(spec_text)}</strong>'

    probs, _ = audit(tree(clean_spec, page_for(clean_spec)))
    case("audit: a clean tree has no problems", probs, [])

    asserted_spec = clean_spec + "\n" + md_assert
    probs, _ = audit(tree(asserted_spec, page_for(asserted_spec)))
    case(
        "audit: a re-asserted retired claim is a problem",
        any("RETIRED claim re-asserted" in p for p in probs),
        True,
    )
    case(
        "audit: and that is its ONLY problem (the fixture does not drift)",
        len(probs),
        1,
    )

    quoted_spec = clean_spec + "\n" + md_quoted
    probs, _ = audit(tree(quoted_spec, page_for(quoted_spec)))
    case("audit: a marked quotation is not a problem", probs, [])

    # a LIVE token present at one site and removed from another
    one_short = "\n\n".join(c["token"] for c in LIVE[1:]) + "\n"
    probs, _ = audit(tree(one_short, page_for(one_short)))
    case(
        "audit: a LIVE claim absent from all its sites is a problem",
        any("LIVE claim absent from ALL" in p for p in probs),
        True,
    )

    probs, _ = audit(tree(clean_spec, '<strong data-derived="spec-lines">99999</strong>'))
    case(
        "audit: a derived figure disagreeing with its source is a problem",
        any("DERIVED figure disagrees" in p for p in probs),
        True,
    )

    probs, _ = audit(tree(clean_spec, "<p>no derived element here</p>"))
    case(
        "audit: a missing derived element is a problem",
        any("DERIVED figure absent" in p for p in probs),
        True,
    )

    probs, _ = audit(tree(clean_spec, '<strong data-derived="spec-lines">many</strong>'))
    case(
        "audit: a non-numeric derived figure is a problem",
        any("not a number" in p for p in probs),
        True,
    )

    # CANNOT RUN, not a pass, when nothing registered exists
    empty = pathlib.Path(tempfile.mkdtemp())
    try:
        audit(empty)
        case("audit: an empty tree raises CannotRun", "no raise", "CannotRun")
    except CannotRun:
        case("audit: an empty tree raises CannotRun", "CannotRun", "CannotRun")

    # the registry must admit its own incompleteness
    case("registry declares itself incomplete", REGISTRY_IS_INCOMPLETE, True)

    # ── main() is DRIVEN from here, not merely defined (ADR-0014). `check-main-drivable.py`
    # refuses a guard whose entry point no case reaches: an exit path nothing exercises is
    # where a fail-open hides, and the rc contract is the part callers actually depend on.
    import contextlib
    import io

    # ⛔ `main(...)` IS CALLED AT FOUR DISTINCT SITES, DELIBERATELY, AND NOT THROUGH A HELPER.
    # `check-fixture-variation` reads the literal call-site EXPRESSION, so routing these through
    # one `drive(argv)` wrapper showed it a single constant and it refused them — correctly: a
    # parameter every call site passes identically is indistinguishable from a literal, and any
    # clause reading it is unguarded. Four sites, four different argv expressions.
    @contextlib.contextmanager
    def quiet():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            yield

    clean_root = tree(clean_spec, page_for(clean_spec))
    with quiet():
        rc_clean = main(["--root", str(clean_root)])
    case("main: a clean tree exits 0", rc_clean, 0)

    # argparse's `--opt=value` form: a different argv SHAPE, not the same list restrung
    with quiet():
        rc_equals = main([f"--root={clean_root}"])
    case("main: the --root=VALUE form is accepted too", rc_equals, 0)

    bad = tree(clean_spec, '<strong data-derived="spec-lines">1</strong>')
    with quiet():
        rc_bad = main(["--root", str(bad), "--root", str(bad)])
    case("main: a disagreeing derived figure exits 1", rc_bad, 1)

    with quiet():
        rc_empty = main(["--root=" + tempfile.mkdtemp()])
    case("main: a tree with no registered document exits 2, not 0", rc_empty, 2)

    print("\n".join(failures) if failures else "", end="" if failures else "")
    if failures:
        print(f"\n{len(failures)} of {n} self-test case(s) FAILED")
        return 1
    print(f"{n}/{n} self-test cases passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        problems, notes = audit(pathlib.Path(args.root))
    except CannotRun as exc:
        print(f"CANNOT RUN — {exc}", file=sys.stderr)
        print("  Treat this as NOT RUN, never as a pass.", file=sys.stderr)
        return 2

    for note in notes:
        print(f"  note: {note}")

    if problems:
        print(f"\nFAILED — {len(problems)} claim-propagation problem(s):\n")
        for p in problems:
            print(f"  ✗ {p}")
        print(
            "\nOne rule, one place. Where a rule must be stated twice, every site is updated "
            "together or this gate refuses the pair."
        )
        return 1

    print(
        f"claim propagation OK — {len(RETIRED)} retired claim(s) not re-asserted, "
        f"{len(LIVE)} live claim(s) at every declared site, "
        f"{len(DERIVED)} derived figure(s) agree with their source"
    )
    if REGISTRY_IS_INCOMPLETE:
        print(
            "  ⚠ this registry is a floor, not a closure: a rule restated in words no "
            "registered token matches is invisible to this guard"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Refuse a page whose DERIVED figure disagrees with the producer that computes it.

    python3 scripts/check-claim-propagation.py --self-test # 41 cases against synthetic trees

⛔ THE FILENAME IS NOW WIDER THAN THE CONTENT, AND IT IS KEPT DELIBERATELY. This script once
checked three things; ADR-0015 superseded two of them and only the derived-figure half remains.
The name is retained because **23 files cite it, 8 of them MERGED review documents** — frozen
testimony that cannot be rewritten — plus `ci.yml`, `CONTEXT.md` and the spec. Same decision, and
the same reason, as `.claude/hooks/block-default-branch-push.sh`, whose filename is narrower than
its content for exactly this reason. ⚠ A reader who remembers the old three-part contract must
read the bound below, not the name.

WHAT IT CHECKS
--------------
**A DERIVED figure agrees with its source.** The page carries `data-derived="spec-lines"`; its text
must equal the spec's real line count. Measured: the page said *"213-line spec"* for a 669-line
spec, having been recomposed four times without the figure being re-derived — and it has caught
that count moving FOUR times since, most recently on 2026-10-17 when adding a canon marker to the
spec made it 1,137 lines while both pages still said 1,136.

⭐ THIS HALF HAS NO EQUIVALENT ANYWHERE ELSE, which is why ADR-0015 kept it while shedding the
rest. No canon marker, no citation rule and no amount of prose discipline notices a number drifting
by one.

WHAT WAS REMOVED, AND WHY — because a reader must not assume it is still covered
--------------------------------------------------------------------------------
⟳ 2026-10-17, ADR-0015 (architecture review `claim-propagation`, backlog #298). Two checks are
GONE: *a RETIRED claim is not re-asserted*, and *a LIVE claim reaches every site that must state
it*. Both policed the same rule stated in two PROSE copies, via a hand-kept token registry.

**They were removed because the repository had already decided the opposite remedy and this guard
was built anyway.** `check-canonical-source.py` — *"a mechanism described in more than one place
drifts. This refuses the second copy"* — landed 2026-10-14 for this same defect class. This file
required *every site to agree*; that one *refuses the second copy*. Opposite architectures for one
concern, which is `a second implementation of one rule drifts` — this repository's most-measured
defect, 17 recorded instances — applied to its own guards.

⛔ AND THE PROSE HALF WAS MEASURED FAILING AT THE MOMENT OF THE DECISION: **three claims were
drifted between the spec and the page while this guard was GREEN over all three** (backlog #297).
A check green over the drift it exists to catch is worse than none, because it creates a belief
that something is covered. The 65 self-test cases rounds 3 and 4 added — chasing `<em>`, a
whitespace text node and a `<br>` — were all artefacts of matching a phrase across two prose
copies, and are retired WITH their subject.

⚠ WHAT NOW PROTECTS PROSE AGREEMENT, STATED PLAINLY: **review, and nothing else.** The canon
mechanism proves a page CITES the spec; it cannot prove the page AGREES with it — `audit()` there
is `hit and not _cites(...)`, so a citing site may restate and contradict. ADR-0015 accepts that
deliberately. The remedy for an existing restatement is to delete the recital and keep the
citation: a citation cannot drift, a recital can.

⛔ AND IT IS NOT A SPELL-CHECKER FOR PROSE ABOUT THE RULES — the lesson that outlives the deleted
half. Every one of these documents quotes its own retired claims deliberately, to record what
changed. `check-plan-file-tags.py` paid for this first: a bare substring test broke thirteen
documents that merely *discussed* a tag.
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

def audited_sites(sites: list[str]) -> list[str]:
    """Expand a registration to the paths that must actually agree.

    ⛔ `PAGE` is the hand-edited fragment; `PAGE_HTML` is what `brief-compose.py` produces from it
    and **the only file a reader ever opens**. r3 CODEX H3: `PAGE_HTML` was defined, written by
    this suite's own fixture, and named by ZERO claims — so a token could reach the fragment and
    miss the served page, and the guard built to catch a dropped site was blind to the one site
    that matters. Measured the same day by the author, who committed exactly that drift: a reflow
    landed in the fragment and the page was never recomposed.

    ⚠ DERIVED, never listed. Adding `PAGE_HTML` to each registration by hand rebuilds the recall
    failure that `page_for` had already paid for once in this very file — a new claim would forget
    it, and forgetting is the defect, not the typing.
    """
    out = list(sites)
    if PAGE in out and PAGE_HTML not in out:
        out.append(PAGE_HTML)
    return out


# Derived figures: an element carrying data-derived="<key>" whose text must equal a computed value.
DERIVED: list[dict] = [
    {
        "key": "spec-path",
        "page": PAGE,
        "compute": "path-of",
        "source": SPEC,
        "why": ("r3 CLAUDE M4: the page declared TWO `data-derived` carriers and only `spec-lines` "
                "was registered, so the path could be changed to "
                "`docs/NOT/A/REAL/PATH-totally-wrong.md` at both sites with the gate green — while "
                "the page told the reader this guard refuses a page whose *derived figures* "
                "disagree. Registered, and the closure rule below makes the plural true"),
    },
    {
        "key": "spec-lines",
        "page": PAGE,
        "compute": "line-count-of",
        "source": SPEC,
        "why": "r2 CLAUDE B2: the page said 213 for a 669-line spec after four recompositions",
    },
]


class _Carriers(html.parser.HTMLParser):
    """Collect the `data-derived` values a page declares, and how many elements declare each.

    ⟳ 2026-10-17 (ADR-0015): WAS `_Blocks`, and it collected two unrelated things — these
    carriers, and per-block prose text with the class of every enclosing element, for matching a
    registered phrase across two prose copies. That second job is GONE: the canon mechanism in
    `check-canonical-source.py` replaces it, so the `BLOCK` set, the `blocks`/`nodes` lists and
    the class accumulation are deleted rather than left unreferenced. The rename is the honest
    fix — the old name described the deleted half — and it is safe by this repository's own
    stated rule: the symbol occurred THREE times in this file and in ZERO mutation anchors across
    all 60 manifests, checked before renaming rather than after.

    ⚠ WHAT THE DELETION COST, stated rather than discovered: rounds 3 and 4 spent 65 cases on
    that prose matcher — inline markup splitting a phrase per text node, a whitespace-only node
    being deleted, and a void element separating words while emitting none. Those cases are
    retired WITH their subject. The three lessons that still bind are the ones below, because
    they are about the ELEMENT STACK, which the carrier chain needs.
    """

    # Void elements never get an end tag, so they must not be pushed onto the stack —
    # otherwise one <br> inside a carrier leaves the carrier open for the rest of the document.
    # ⭐ THIS IS A CARRIER RULE, NOT A PROSE RULE, which is why it survives the deletion: the
    # mutation that pushes void elements reddens `derived: a void element carrying the attribute
    # captures nothing`.
    VOID = frozenset(
        "area base br col embed hr img input link meta param source track wbr".split()
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        # key -> accumulated text, taken ONLY from nodes whose open-element chain still contains
        # the carrying element.
        #
        # ⭐ CONCATENATION IS DELIBERATE, because it is what makes
        # `<strong …>1,<em>118</em></strong>` read as one value. The case the old comment worried
        # about — a second carrier for one key silently appending rather than overwriting — is
        # REFUSED outright instead: `carriers` counts carrier OPENINGS per key, and audit()
        # rejects a key carried more than once. Two carriers for one key is a page defect, not a
        # merge problem.
        self.derived: dict[str, str] = {}
        self.carriers: dict[str, int] = {}

    def handle_starttag(self, tag, attrs):  # noqa: D102
        a = {k: (v if v is not None else "") for k, v in attrs}
        if a.get("data-derived"):
            self.carriers[a["data-derived"]] = self.carriers.get(a["data-derived"], 0) + 1
        if tag.lower() not in self.VOID:
            self.stack.append((tag, a))

    def handle_startendtag(self, tag, attrs):  # noqa: D102
        # A self-closing element has no children, so it can carry no derived TEXT — but it is
        # still a declared carrier, and the closure rule must see it (r4 CODEX H2). It is
        # deliberately NOT pushed onto the stack.
        a = {k: (v if v is not None else "") for k, v in attrs}
        if a.get("data-derived"):
            self.carriers[a["data-derived"]] = self.carriers.get(a["data-derived"], 0) + 1

    def handle_endtag(self, tag):  # noqa: D102
        # close the most recent matching element, tolerating unclosed inline tags
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
        # no match: an end tag with no open partner. Ignore it rather than corrupting the stack.

    def handle_data(self, data):  # noqa: D102
        # ⚠ Whitespace-only text contributes NOTHING to a derived value, because every value is
        # accumulated stripped. It used to contribute a separating space, which existed only for
        # the deleted prose matcher — returning early here is equivalent for carriers, not a
        # narrowing of behaviour.
        if not data.strip():
            return
        for _, a in self.stack:
            key = a.get("data-derived")
            if key:
                self.derived.setdefault(key, "")
                self.derived[key] += data.strip()


def _derived_values(text: str) -> dict[str, str]:
    p = _Carriers()
    p.feed(text)
    return dict(p.derived)


def _derived_carrier_counts(text: str) -> dict[str, int]:
    """How many elements carry each `data-derived` key. More than one is a page defect (M7)."""
    p = _Carriers()
    p.feed(text)
    return dict(p.carriers)


def _tree_spec_lines(spec_text: str) -> int:
    """The value a synthetic page must declare. Used by the self-test so its fixture
    cannot drift from its own subject — the defect this guard exists to catch."""
    return len(spec_text.splitlines())


def audit(root: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return (problems, notes). A problem fails the gate; a note is reported and does not."""
    problems: list[str] = []
    notes: list[str] = []

    wanted = {p for d in DERIVED for p in audited_sites([d["page"]])}
    wanted |= {d["source"] for d in DERIVED}
    # ⛔ AN EMPTY REGISTRY IS CANNOT RUN (r3 CLAUDE M5.2). With `DERIVED` empty, `wanted` is
    # empty, `absent_paths` is empty, nothing raises, and the success line reads "0 derived" — a
    # zero over nothing, which this repository has already paid for once and written down in
    # `check-plan-file-tags.py`: *an empty corpus is CANNOT RUN, because a zero over nothing is
    # not a finding.* This guard had no such assertion.
    # ⟳ 2026-10-17 (ADR-0015): the condition was `not (RETIRED or LIVE or DERIVED)`, a DISJUNCTION
    # over three registries. With two of them gone it is not enough to delete their names — a
    # disjunction over the survivors alone is the same rule, but a reader could reasonably have
    # written `if not DERIVED and not <nothing>` and left an always-false guard. Stated because
    # the near-miss is invisible once the other two names are gone.
    if not DERIVED:
        raise CannotRun(
            "the registry is EMPTY — no derived figure is registered, so a clean result here "
            "would be a zero over nothing"
        )

    absent_paths = sorted(s for s in wanted if not (root / s).is_file())

    # ⛔ AN ABSENT REGISTERED PATH IS CANNOT RUN, NEVER A NOTE (r3 CODEX H1). The first version
    # noted each absent path and skipped it everywhere below, so DELETING a registered document
    # produced `problems == []` and an exit of 0: the live-claim denominator and the derived-figure
    # check both quietly got smaller, and the guard reported success about a document that was
    # gone. Measured by the reviewer against the real spec with the fragment removed.
    # ⚠ The consequence is deliberate: if these documents are ever renamed or archived, this gate
    # goes red and the registry has to be updated with them. A guard whose subject has vanished
    # must not be the thing that stays quiet.
    if absent_paths:
        all_gone = len(absent_paths) == len(wanted)
        raise CannotRun(
            f"{len(absent_paths)} of {len(wanted)} registered path(s) absent under {root}: "
            + ", ".join(absent_paths)
            + ("\n      every registered path is absent, so a clean result would be a zero over "
               "nothing" if all_gone else
               "\n      a site that is not there cannot be compared with the sites that are, so "
               "this is NOT CHECKED rather than clean")
        )

    cache: dict[str, str] = {}

    def read(rel: str) -> str:
        if rel not in cache:
            cache[rel] = (root / rel).read_text(encoding="utf-8")
        return cache[rel]

    # 3 — derived figures must agree with their source
    # ⛔ CLOSURE: EVERY `data-derived` KEY IN AN AUDITED PAGE MUST BE REGISTERED (r3 CLAUDE M4).
    # The loop below looks up each REGISTERED key and ignores every key it does not know, so a page
    # could carry a carrier nothing checks — measured, with a deliberately wrong path, `problems:
    # []`. Without this rule `DERIVED` is a subset test, and the page's own sentence promising
    # *figures* plural was an overstatement rather than a description.
    registered_keys = {d["key"] for d in DERIVED}
    for page in sorted({p for d in DERIVED for p in audited_sites([d["page"]])}):
        for key, count in _derived_carrier_counts(read(page)).items():
            if count > 1:
                problems.append(
                    f"DERIVED key carried {count} times: {page} has {count} elements with "
                    f'data-derived="{key}"\n'
                    f"      their text is CONCATENATED, so the value is a run-together string "
                    f"rather than either figure — carry each key exactly once"
                )
        # ⛔ OPENINGS, NOT VALUES (r4 CODEX H2). This loop read `_derived_values()`, which only
        # acquires a key while processing TEXT — so every textless carrier passed:
        # `<span data-derived="unknown"></span>`, its self-closing spelling, `<img data-derived=…>`
        # and `<input data-derived="unknown" value="999">`, the last of which can DISPLAY a value
        # while being invisible to this rule. Measured: all four appended to the real pages,
        # `problems: []`.
        for key in _derived_carrier_counts(read(page)):
            if key not in registered_keys:
                problems.append(
                    f"UNREGISTERED derived carrier: {page} declares "
                    f'data-derived="{key}", which no DERIVED entry checks\n'
                    f"      a carrier nothing checks reads as guarded and is not; register it or "
                    f"remove the attribute"
                )

    # ⚠ Each derived figure is checked in the fragment AND in the served page composed from it
    # (r3 CODEX H3). `page` is what every message names, so a failure says which of the two is
    # wrong — "the figure is stale" and "the page was never recomposed" are different repairs.
    for spec in DERIVED:
        if spec["compute"] == "line-count-of":
            actual = str(len(read(spec["source"]).splitlines()))
            compare = "digits"
        elif spec["compute"] == "path-of":
            actual = spec["source"]
            compare = "exact"
        else:
            raise CannotRun(f"unknown compute rule {spec['compute']!r}")
        for page in audited_sites([spec["page"]]):
            found = _derived_values(read(page))
            if spec["key"] not in found:
                problems.append(
                    f"DERIVED figure absent: the page declares no "
                    f'data-derived="{spec["key"]}" element in {page}\n'
                    f"      it must be present and correct, not hand-written: {spec['why']}"
                )
                continue
            claimed_raw = found[spec["key"]]
            if compare == "digits":
                digits = re.sub(r"[^0-9]", "", claimed_raw)
                if not digits:
                    problems.append(
                        f"DERIVED figure is not a number: {spec['key']} reads {claimed_raw!r} "
                        f"in {page}"
                    )
                elif digits != actual:
                    problems.append(
                        f"DERIVED figure disagrees with its source: {spec['key']} says "
                        f"{digits} in {page}, {spec['source']} has {actual} lines\n"
                        f"      {spec['why']}"
                    )
            elif claimed_raw.strip() != actual:
                # `path-of`: an EXACT string, because a path that is nearly right is wrong in the
                # one way that matters — it sends the reader somewhere else.
                problems.append(
                    f"DERIVED value disagrees with its source: {spec['key']} says "
                    f"{claimed_raw.strip()!r} in {page}, the registered source is {actual!r}\n"
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
    def tree(spec_text: str, page_text: str, html_text: str | None = None) -> pathlib.Path:
        """`html_text` defaults to the fragment, which is what a recomposed page IS. Passing a
        DIFFERENT one is how the served-page drift of r3 CODEX H3 is constructed."""
        d = pathlib.Path(tempfile.mkdtemp())
        (d / SPEC).parent.mkdir(parents=True, exist_ok=True)
        (d / PAGE).parent.mkdir(parents=True, exist_ok=True)
        (d / SPEC).write_text(spec_text, encoding="utf-8")
        (d / PAGE).write_text(page_text, encoding="utf-8")
        (d / PAGE_HTML).write_text(page_text if html_text is None else html_text,
                                   encoding="utf-8")
        return d

    # ⟳ 2026-10-17 (ADR-0015): this was the concatenation of every LIVE token, because a clean
    # tree had to satisfy the prose registry at the same time. With that registry gone the spec's
    # CONTENT is irrelevant to this guard — only its LINE COUNT is read, by `line-count-of`. So
    # the fixture now says what it is instead of deriving it from a table that no longer exists.
    clean_spec = "\n".join(f"spec line {i}" for i in range(1, 24)) + "\n"

    def page_for(spec_text: str) -> str:
        """Build the page from the spec it describes, so the fixture cannot drift from its own
        subject. Round 2's B2 was exactly a page whose figure no longer matched its spec, and a
        fixture that hard-codes the number reproduces that defect inside the test.

        ⛔ AND IT CARRIES EVERY PAGE-SITE LIVE TOKEN, which the first version did not — so the
        "clean tree" it built was clean only for claims registered at the SPEC alone. The moment a
        claim was registered `[SPEC, PAGE]` the clean-tree case went red by construction, and the
        guard shipped that way in its own first commit (`2bca9fe5`) while its round document
        claimed a green control. Derived from `LIVE`, never listed, so a new page-site claim cannot
        reintroduce it."""
        # ⛔ EVERY REGISTERED CARRIER, derived from `DERIVED` rather than listed — the closure rule
        # (r3 CLAUDE M4) refuses an unregistered carrier, and a fixture that emits only one would
        # fail the moment a second was registered. Which is exactly what happened when `spec-path`
        # joined: five cases went red at once.
        carriers = []
        for d in DERIVED:
            if d["compute"] == "line-count-of":
                val = _tree_spec_lines(spec_text)
            elif d["compute"] == "path-of":
                val = d["source"]
            else:  # an unknown rule is the UNKNOWN-compute case's business, not the fixture's
                val = ""
            carriers.append(f'<strong data-derived="{d["key"]}">{val}</strong>')
        return "\n".join(carriers) + "\n"

    probs, _ = audit(tree(clean_spec, page_for(clean_spec)))
    case("audit: a clean tree has no problems", probs, [])

    # ⟳ 2026-10-17 (ADR-0015): the retired-claim, marked-quotation and LIVE-propagation cases
    # stood here — including the pair that finally pinned PARTIAL propagation after r3 CODEX H2
    # showed the single case was testing the absent-everywhere arm instead. They are retired
    # WITH their subject: the behaviour they covered is gone, not merely untested. What now
    # protects a page that contradicts the spec is review, and nothing else (ADR-0015).
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

    # ⛔ ONE registered path absent is ALSO CannotRun — the case r3 CODEX H1 was filed against.
    # The bug was not "an empty tree passes"; it was "a tree missing ONE document passes", and the
    # empty-tree case above cannot see it, because with nothing present the old code raised for a
    # different reason. These two cases are not interchangeable and the pair is the coverage.
    partial = tree(clean_spec, page_for(clean_spec))
    (partial / PAGE).unlink()
    try:
        audit(partial)
        case("audit: ONE absent registered path raises CannotRun", "no raise", "CannotRun")
    except CannotRun as exc:
        case("audit: ONE absent registered path raises CannotRun", "CannotRun", "CannotRun")
        case(
            "audit: and it NAMES the path it could not read",
            PAGE in str(exc),
            True,
        )
        case(
            "audit: and it does not claim everything is gone when one file is",
            "every registered path is absent" in str(exc),
            False,
        )

    # ⛔ THE SERVED PAGE IS AUDITED TOO (r3 CODEX H3) — and after ADR-0015 only its DERIVED half
    # remains. The token half of this concern is retired with the prose registry; what is left is
    # the figure, which is composed into the served page the same way. This still fails if
    # `audited_sites` ever stops expanding `PAGE`, which was the finding's actual subject.
    # and the derived figure, which is composed into the served page the same way
    probs, _ = audit(
        tree(clean_spec, page_for(clean_spec),
             '<strong data-derived="spec-lines">99999</strong>')
    )
    case(
        "audit: a derived figure wrong ONLY in the served page is a problem",
        any("DERIVED figure disagrees" in p and PAGE_HTML in p for p in probs),
        True,
    )

    # ⟳ 2026-10-17 (ADR-0015): r4 H1's void-separator LOOP stood here — five separators, written
    # as a loop rather than the one reported because it was the THIRD instance of its class in
    # the prose matcher. Retired with that matcher. ⭐ The VOID set it keyed on SURVIVES in
    # `_Carriers`, where it does a different job (keeping a carrier from being left open), and
    # it still has a mutation and a case there.
    # ⛔ H2 (r4 CLAUDE) — THE TWO `wanted |= {… DERIVED …}` LINES, EACH WITH A WITNESS. Both
    # survived at 88/88: one dropped `audited_sites` (so the composed page never enters `wanted`),
    # the other dropped the source entirely. ⚠ The assertion is on the EXCEPTION TYPE, because the
    # mutants raise `FileNotFoundError` — and a case that let that propagate would end the suite in
    # a traceback with no named failure, which is the crash-forging-a-`[FAIL]` shape this file has
    # paid for twice.
    def _audit_outcome(root):
        try:
            audit(root)
            return "no raise"
        except CannotRun:
            return "CannotRun"
        except Exception as exc:        # noqa: BLE001 — the TYPE is the measurement
            return type(exc).__name__

    _saved_pre = DERIVED[:]
    try:
        DERIVED[:] = [{"key": "spec-lines", "page": PAGE, "compute": "line-count-of",
                       "source": SPEC, "why": "self-test fixture"}]
        # the FRAGMENT exists; the COMPOSED page does not, and only DERIVED reaches it
        d = pathlib.Path(tempfile.mkdtemp())
        (d / SPEC).parent.mkdir(parents=True, exist_ok=True)
        (d / PAGE).parent.mkdir(parents=True, exist_ok=True)
        (d / SPEC).write_text("one\ntwo\n", encoding="utf-8")
        (d / PAGE).write_text('<strong data-derived="spec-lines">2</strong>', encoding="utf-8")
        case("audit: an absent COMPOSED page reached only through DERIVED is CannotRun",
             _audit_outcome(d), "CannotRun")
        # and symmetrically, an absent SOURCE registered only through DERIVED
        d2 = pathlib.Path(tempfile.mkdtemp())
        (d2 / PAGE).parent.mkdir(parents=True, exist_ok=True)
        (d2 / PAGE).write_text('<strong data-derived="spec-lines">2</strong>', encoding="utf-8")
        (d2 / PAGE_HTML).write_text('<strong data-derived="spec-lines">2</strong>', encoding="utf-8")
        case("audit: an absent SOURCE reached only through DERIVED is CannotRun",
             _audit_outcome(d2), "CannotRun")
    finally:
        DERIVED[:] = _saved_pre

    # ⛔ M7 — TWO CARRIERS FOR ONE KEY IS A PAGE DEFECT, and the values concatenate rather than
    # either winning. The old comment claimed first-wins; measured, 669 and 99999 gave '66999999'.
    case(
        "derived: two carriers for one key are both seen",
        _derived_carrier_counts(
            '<strong data-derived="spec-lines">669</strong>'
            '<p>x</p><strong data-derived="spec-lines">99999</strong>'
        ),
        {"spec-lines": 2},
    )
    case(
        "derived: and their text CONCATENATES — the documented behaviour, not first-wins",
        _derived_values(
            '<strong data-derived="spec-lines">669</strong>'
            '<p>x</p><strong data-derived="spec-lines">99999</strong>'
        ),
        {"spec-lines": "66999999"},
    )
    probs, _ = audit(tree(
        clean_spec,
        page_for(clean_spec) + '<strong data-derived="spec-lines">99999</strong>\n',
    ))
    case(
        "audit: a key carried TWICE is a problem",
        any("carried 2 times" in p for p in probs),
        True,
    )

    # ⟳ 2026-10-17 (ADR-0015): the prose-matcher cases stood here — the HTML/markdown table
    # divergence, the whitespace-only span's class, the self-closing swallow, and r4 CODEX H1's
    # inline-element pair. All retired WITH their subject. ⭐ The one case in this region that
    # SURVIVES is the self-closing CARRIER below: it reads `_derived_values`, not the matcher,
    # and it is still named by a mutation.

    case("parser: a self-closing carrier holds no text",
         _derived_values('<strong data-derived="spec-lines"/>771 after it'), {})


    # ⛔ H2 (r4 CODEX) — A CARRIER WITH NO TEXT IS STILL A CARRIER. All four spellings below
    # passed the closure rule, because it read extracted VALUES and a key is only acquired while
    # processing text. The `<input>` is the sharp one: it can DISPLAY a value to a reader while
    # being invisible to the check.
    for _spelling in (
        '<span data-derived="unknown"></span>',
        '<span data-derived="unknown"/>',
        '<img data-derived="unknown" src="x">',
        '<input data-derived="unknown" value="999">',
    ):
        case(f"derived: a textless carrier is still counted — {_spelling[:34]}",
             _derived_carrier_counts(_spelling), {"unknown": 1})
    probs, _ = audit(tree(
        clean_spec,
        page_for(clean_spec) + '<input data-derived="unknown" value="999">\n',
    ))
    case(
        "audit: a TEXTLESS unregistered carrier is a problem",
        any("UNREGISTERED derived carrier" in p for p in probs),
        True,
    )

    # ⛔ M2 (r4 CODEX) — THE TOLERANT UNWIND WAS BEHAVIOURALLY UNPINNED. Replacing
    # `del self.stack[i:]` with `self.stack.pop(i)` left 80/80 green; this is the reviewer's own
    # witness, which distinguishes them. Mis-nested inline tags are what the tolerance is FOR.
    case("parser: a mis-nested close unwinds everything inside it",
         _derived_values('<p><span><b data-derived="k">1</span>2</b></p>'),
         {"k": "1"})

    # ⛔ THE CLOSURE RULE (r3 CLAUDE M4): a `data-derived` carrier no entry checks is a problem,
    # not something to ignore. Measured before the fix with a deliberately wrong path at both page
    # sites: `problems: []`.
    probs, _ = audit(tree(
        clean_spec,
        page_for(clean_spec) + '<p data-derived="not-registered-anywhere">42</p>\n',
    ))
    case(
        "audit: an UNREGISTERED data-derived carrier is a problem",
        any("UNREGISTERED derived carrier" in p for p in probs),
        True,
    )
    case(
        "audit: and the problem names the key nothing checks",
        any("not-registered-anywhere" in p for p in probs),
        True,
    )

    # ⛔ AND `path-of` COMPARES EXACTLY, because a path that is nearly right sends the reader
    # somewhere else. The digits rule would have called these equal — both have no digits.
    _wrong_path = page_for(clean_spec).replace(SPEC, "docs/NOT/A/REAL/PATH.md")
    assert SPEC not in _wrong_path, "fixture failed to replace the path"
    probs, _ = audit(tree(clean_spec, _wrong_path))
    case(
        "audit: a path-of value disagreeing with its source is a problem",
        any("DERIVED value disagrees" in p for p in probs),
        True,
    )

    # ⛔ THE THREE FAIL-OPENS r3's CLAUDE HALF MEASURED BY IMPORT-AND-CALL (M5). Each needs the
    # module globals swapped, because each is a property of the REGISTRY rather than of a document,
    # and a fixture tree cannot express "the registry is empty".
    _saved = DERIVED[:]

    def _restore():
        DERIVED[:] = _saved

    try:
        # 2 — an empty registry over any tree is CANNOT RUN, not "0 of everything checked"
        DERIVED[:] = []
        audit(tree("x\n", "<p>y</p>"))
        case("audit: an EMPTY REGISTRY raises CannotRun", "no raise", "CannotRun")
    except CannotRun as exc:
        case("audit: an EMPTY REGISTRY raises CannotRun", "CannotRun", "CannotRun")
        case(
            "audit: and it says the registry is empty, not that a path is missing",
            "registry is EMPTY" in str(exc),
            True,
        )
    finally:
        _restore()

    try:
        # ⛔ L3's third mutant: `wanted` must include the DERIVED pages. When this was written
        # the two `wanted |= {… DERIVED …}` lines were redundant, because SPEC, PAGE and
        # PAGE_HTML all arrived via the prose registry too — so deleting them left the suite
        # green. ⟳ 2026-10-17 (ADR-0015): that registry is GONE, so those two lines are now the
        # ONLY way any path enters `wanted`, and this case is load-bearing by construction.
        DERIVED[:] = [{
            "key": "spec-lines",
            "page": PAGE,
            "compute": "line-count-of",
            "source": SPEC,
            "why": "self-test fixture: the only registration is a DERIVED one",
        }]
        d = pathlib.Path(tempfile.mkdtemp())
        (d / SPEC).parent.mkdir(parents=True, exist_ok=True)
        (d / SPEC).write_text("one\ntwo\n", encoding="utf-8")
        audit(d)  # PAGE and PAGE_HTML are absent and registered ONLY through DERIVED
        case("audit: a DERIVED-only page absence raises CannotRun", "no raise", "CannotRun")
    except CannotRun as exc:
        case("audit: a DERIVED-only page absence raises CannotRun", "CannotRun", "CannotRun")
        case("audit: and it names the DERIVED page nothing else registers",
             PAGE in str(exc), True)
    finally:
        _restore()

    try:
        # 3 — an unknown `compute` rule is refused, not silently line-counted
        DERIVED[:] = [{
            "key": "spec-lines",
            "page": PAGE,
            "compute": "weigh-it-in-kilograms",
            "source": SPEC,
            "why": "self-test fixture",
        }]
        audit(tree(clean_spec, page_for(clean_spec)))
        case("audit: an UNKNOWN compute rule raises CannotRun", "no raise", "CannotRun")
    except CannotRun as exc:
        case("audit: an UNKNOWN compute rule raises CannotRun", "CannotRun", "CannotRun")
        case(
            "audit: and the refusal names the rule it does not know",
            "weigh-it-in-kilograms" in str(exc),
            True,
        )
    finally:
        _restore()

    # ⚠ and the restore must actually have happened, or every case after this point is measuring
    # a mutilated registry — the shape of defect this file exists to catch, inside its own suite.
    case("self-test: the registry was restored after the swaps",
         len(DERIVED), len(_saved))


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
            "\nA derived figure names a producer. Where a page states a number its source "
            "computes, the two agree or this gate refuses the pair."
        )
        return 1

    print(
        f"derived figures OK — {len(DERIVED)} figure(s) agree with their source"
    )
    # ⛔ THE BOUND IS NARROWER THAN IT WAS, AND SAYING SO IS THE POINT (ADR-0015). This guard
    # used to claim two more things — that no RETIRED claim was re-asserted and that every LIVE
    # claim reached every site. Both are GONE, superseded by `check-canonical-source.py`'s canon
    # mechanism, and a reader who remembers the old line must not read this one as still covering
    # them. ⚠ What replaces them is NOT equivalent: the canon guard proves a page CITES the spec,
    # never that it AGREES with it. Agreement between a canon and its citing sites is now enforced
    # by review and by nothing else — ADR-0015 accepts that deliberately, and backlog #297's three
    # live drifted claims are the measured price.
    print(
        "  ⚠ this gate no longer checks prose at all: it compares a page's DERIVED figures with "
        "the producer that computes them. Whether the page's words agree with the spec's words is "
        "ADR-0015's subject and is enforced by review, not here"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

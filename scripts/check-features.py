#!/usr/bin/env python3
"""Validate docs/features.md — the feature tree the /features page renders.

    python3 scripts/check-features.py             # validate the living tree
    python3 scripts/check-features.py --self-test # 48 cases against synthetic trees
"""
import re, sys, pathlib
from dataclasses import dataclass, field

# ⚠ `now` was in this list and was REMOVED: review r1 measured it rejecting 1 in 13 of this repo's
# own purpose-shaped sentences. A rule that blocks legitimate prose gets deleted by the first person
# it blocks, so the list keeps only words that cannot appear in a statement of purpose.
STATUS_TOKENS = re.compile(
    r"(?:[✅🔴🟠🟢⏳◀]|#\d+|\b(?:currently|already|still|yet|planned|done|todo)\b|\bin progress\b)",
    re.IGNORECASE,
)
# ONE owner for the field names: the matcher and the error message that teaches the grammar are
# both derived from this tuple, so a sixth field cannot be added to one and missing from the other.
FIELD_NAMES = ("state", "for", "areas", "anchors", "expected-because")
# ⚠ ONE OWNER, because this fact is read in two places that must not disagree: the comma-split in
# `parse_features` and the duplicate-field REMEDY. Code review r3 (Codex) caught the message
# telling an author to write `state: built, absent` — advice that is right for a list field and
# produces a second, different error for a scalar one. An instruction that does not work costs
# the author a round to discover.
LIST_FIELDS = ("areas", "anchors")
FIELD = re.compile(rf"^({'|'.join(FIELD_NAMES)}):\s*(.*)$")

@dataclass
class Node:
    slug: str
    level: int
    trunk: str
    state: str = ""
    purpose: str = ""
    areas: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    expected_because: str | None = None
    line: int = 0


def parse_features(text: str) -> tuple[list[Node], list[str]]:
    nodes: list[Node] = []
    problems: list[str] = []
    trunk = ""
    seen_fields: set[str] = set()
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if line.startswith("## ") and not line.startswith("###"):
            trunk = line[3:].strip(); continue
        if line.startswith("###"):
            level = len(line) - len(line.lstrip("#"))
            slug = line.lstrip("#").strip()
            if not trunk:
                problems.append(f"features.md:{i}: node `{slug}` sits outside any trunk")
            nodes.append(Node(slug=slug, level=level, trunk=trunk, line=i))
            seen_fields = set(); continue
        m = FIELD.match(line)
        if not m:
            # ⭐ A WRAPPED `for:` LINE MUST NOT BE SILENTLY DROPPED (review r1 High 8). Continuation
            # text used to fail FIELD and get skipped, so `for: …\n  Currently broken, see #322.`
            # left the banned words out of `purpose` entirely and the status-token rule reported
            # nothing. Refusing the line is the "cannot run is a failure" posture.
            #
            # ⛔ AND NO PREFIX IS EXEMPT — code review r1 (Codex), Blocking. This test used to read
            # `not line.startswith(("#", "<!--", ">"))`, which refused ordinary wrapped prose and
            # then waved through exactly the three prefixes that make a line LOOK inert. Measured:
            # `> currently broken, see #322.` inside a node parsed clean, carrying two status
            # tokens past a rule whose whole job is to find them; `<!-- … -->` and a bare `#322 …`
            # are the same hole wearing different hats. There is no legitimate blockquote, comment
            # or stray heading inside a node — every field is one line and headings open nodes —
            # so the exemption bought nothing and cost the rule above. ⚠ DO NOT RE-ADD ONE: any
            # prefix exempted here is a prefix a status line can be written behind. Measured
            # 2026-09-19 against the living tree: 0 lines start with `>`, `<!--` or a non-heading
            # `#` inside any node, so refusing all three breaks nothing that exists.
            if nodes and line.strip():
                problems.append(
                    f"features.md:{i}: `{nodes[-1].slug}` has a line that is neither a field nor a "
                    f"heading: {line.strip()[:40]!r}. A field starts at COLUMN 0 — no leading "
                    f"space or tab — lowercase, written `name:` with no space before the colon, "
                    f"and `name` is one of: {', '.join(FIELD_NAMES)}. Keep it on ONE line — a "
                    f"wrapped `for:` would hide its own status tokens from the check — and no "
                    f"prefix is exempt: a blockquote, an HTML comment and a stray `#` are text "
                    f"inside a node too")
            continue
        if not nodes:
            problems.append(f"features.md:{i}: field `{m.group(1)}` before any node"); continue
        key, value = m.group(1), m.group(2).strip()
        n = nodes[-1]
        # ⛔ A DUPLICATE FIELD IS REFUSED, NOT LAST-WRITE-WINS — code review r1 (Codex), High. The
        # five assignments below used to be unconditional, so a second `anchors:` blanked the first
        # and a second `for:` discarded the first. Both are bypasses, not typos: an `absent` node
        # shed the fragment that contradicts it, and a `for:` shed its own status tokens, in each
        # case BEFORE any rule ran. A gate that owns its grammar rejects a duplicate; and when it
        # does, the FIRST value stands, so the content the duplicate was hiding still reaches the
        # checks instead of being replaced by the clean-looking line that followed it.
        if key in seen_fields:
            remedy = ("Put every value on ONE comma-separated line. " if key in LIST_FIELDS
                      else f"`{key}` holds a single value — keep the one you mean and delete the other. ")
            problems.append(f"features.md:{i}: `{n.slug}` repeats the field `{key}` — a duplicate "
                            f"is refused, not merged. {remedy}"
                            f"Under last-write-wins a later line silently replaces an earlier one, "
                            f"and what it replaces is never searched")
            continue
        seen_fields.add(key)
        if key == "state": n.state = value
        elif key == "for": n.purpose = value
        elif key == "expected-because": n.expected_because = value
        elif key in LIST_FIELDS:
            # ⚠ `setattr` TAKES A NAME `Node` DOES NOT HAVE, SILENTLY — code review r3 (Claude), Low.
            # A dataclass without `__slots__` accepts `setattr(n, "expected-because", …)`, writes a
            # dead attribute, and leaves `n.expected_because` None. Four of the five field names ARE
            # their attribute names; `expected-because` is not, so adding it to LIST_FIELDS would
            # drop the value with no error at all. This assertion is what makes that loud.
            assert hasattr(n, key), f"LIST_FIELDS name {key!r} is not an attribute of Node"
            setattr(n, key, [a.strip() for a in value.split(",") if a.strip()])
        else:
            # ⛔ UNREACHABLE TODAY, AND THAT IS WHY IT IS HERE. `FIELD_NAMES` owns the matcher and the
            # grammar message but NOT this chain, so a sixth name added there alone would match, be
            # dedup-tracked, then be discarded here with no attribute and no problem reported.
            raise AssertionError(f"field {key!r} matched but has no assignment — add one here")
    return nodes, problems


def check_nodes(nodes: list[Node]) -> list[str]:
    problems: list[str] = []
    seen: dict[str, int] = {}
    for n in nodes:
        where = f"features.md:{n.line}: `{n.slug}`"
        if n.slug in seen:
            problems.append(f"{where} is a duplicate of the node on line {seen[n.slug]}")
        seen[n.slug] = n.line
        if n.state not in ("built", "absent"):
            problems.append(f"{where} has state {n.state!r}; expected `built` or `absent`")
        if not n.purpose:
            problems.append(f"{where} has no `for:` line — every node says what it is for")
        else:
            hit = STATUS_TOKENS.search(n.purpose)
            if hit:
                problems.append(f"{where} prose contains the status token {hit.group(0)!r}. A node "
                                f"says what it is FOR; where it stands is what the links are for")
        fragments = len(n.areas) + len(n.anchors)
        if n.state == "built" and fragments == 0:
            problems.append(f"{where} is `built` but names no fragment — add an `anchors:` or "
                            f"`areas:` line, or set `state: absent` with an `expected-because:`")
        if n.state == "built" and n.expected_because:
            problems.append(f"{where} is `built` but carries an `expected-because:` — that line is "
                            f"the argument for an ABSENCE. Remove it, or set `state: absent`")
        if n.state == "absent":
            if not n.expected_because:
                problems.append(f"{where} is `absent` but has no `expected-because:` line")
            if fragments:
                problems.append(f"{where} is `absent` but names {fragments} fragment(s) — flip it to `built`")
    return problems


_TAGS = None


def tags():
    """`gen-backlog-page`, which OWNS the Bundle-cell rule (backlog #381) — loaded lazily and once,
    so the parse and node rules above stay importable without it. A hyphenated file cannot be
    named by a plain `import`."""
    global _TAGS
    if _TAGS is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gen_backlog_page", pathlib.Path(__file__).with_name("gen-backlog-page.py"))
        _TAGS = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_TAGS)
    return _TAGS


def backlog_areas(text: str) -> tuple[set[str], list[str]]:
    """(every tag an item row WRITES, normalised; the PROBLEMS met reading them).

    ⛔ PER TAG, through `gen-backlog-page.cell_tags` — this used to collect the RAW cell, so
    `(cloud/money)` and `(cloud / money)` were two areas and a row could hold one.

    ⛔ AND THE ROWS COME FROM `gen-backlog-page.parse`, the header-aware reader the page itself
    uses (backlog #381 r1, Codex M2). This read `cells[-3]` of every numbered line, which was a
    second copy of the row rule: an extra `|` in a row shifted its cells, the page's parser refused
    the table with a `ShapeError`, and this gate read the fragment that landed in the third-last
    slot and passed. A `ShapeError` is now a PROBLEM — the gate FAILS, naming the row — never
    "no areas", which would be CANNOT RUN and read as a different thing. A malformed cell is a
    problem too, carrying its row number."""
    bp = tags()
    unread: list[str] = []
    try:
        rows = bp.parse(text.split("\n"), unread=unread)
    except bp.ShapeError as e:
        return set(), [f"docs/backlog.md cannot be read as a table, so no area in it can be "
                       f"trusted — {e}"]
    out: set[str] = set()
    bad: list[str] = []
    for r in rows:
        leaves, malformed = bp.cell_tags(r["bundle"])
        out.update(leaves)
        if malformed:
            bad.append(f"backlog.md row {r['num']} — its Bundle cell {r['bundle'][:40]!r} is not a run "
                       f"of `(tag)` groups, so it was read as ONE tag by guesswork; write every tag "
                       f"in its own parentheses, and no `|` inside one")
    # ⛔ THE GATE FAILS ON EVERY PROBLEM THE PARSER REPORTS (backlog #381 r3, Codex X1 = Claude C1).
    # `parse` is forgiving BY DESIGN — the page reports drift and keeps rendering — and it reports a
    # row-like line it could not read (`| ⭐999 |`, `| #999 |`, `| 999a |`, `| abc |`) only to a
    # caller that hands it `unread=`. This gate handed none, so such a row and its tags vanished:
    # master's `cells[-3]` read had failed on them, and this passed. Adopting the page's parser
    # without its strictness was the root of rounds 2 and 3 both; `ShapeError` above and this list
    # are the parser's two channels, and the gate now listens to both.
    bad += [f"docs/backlog.md has a line inside an item table that the parser cannot read as a row, "
            f"so its tags reach no reader — {line.strip()[:80]!r}; the number cell must be a bare "
            f"integer" for line in unread]
    return out, bad


def anchor_slugs(text: str) -> set[str]:
    return set(re.findall(r"^\|\s*`([a-z0-9-]+)`\s*\|", text, re.MULTILINE))


def check_cross(nodes, anchors_declared: set[str], areas_in_use: set[str] | None) -> list[str]:
    """⛔ AREAS ARE COMPARED PER TAG, NORMALISED (backlog #381). An `areas:` entry and an in-use
    tag are equal when `normalise_tag` makes them so, and a tag is claimed by the NEAREST area
    that equals it or is a family above it — the rule `gen-features-page.match_rows` places rows
    by. So "claimed by exactly one node" holds per tag: no two entries normalise alike, and every
    in-use tag has a nearest claimant.

    `areas_in_use=None` means the backlog could NOT BE READ (a `ShapeError`, already reported as a
    failure by `backlog_areas`): the per-area questions are skipped rather than answered over an
    empty set, which would accuse every area of being stale and bury the one real cause."""
    nt, nearest = tags().normalise_tag, tags().nearest_claim
    problems: list[str] = []
    area_claims: dict[str, list[str]] = {}
    anchor_claims: dict[str, list[str]] = {}
    for n in nodes:
        for a in n.anchors:
            anchor_claims.setdefault(a, []).append(n.slug)
            if a not in anchors_declared:
                problems.append(f"features.md:{n.line}: `{n.slug}` names anchor `{a}`, which is not "
                                f"in docs/anchors.md")
        for raw in n.areas:
            area_claims.setdefault(nt(raw), []).append(n.slug)
    # ⛔ STALE MEANS "PLACES NO ROW", so it is asked of the NEAREST claimant, the rule `match_rows`
    # places rows by (backlog #381 r1, Claude M1). Asking "does any in-use tag sit at or below this
    # area" passed `(cloud)` beside `(cloud/money)` with only `cloud / money` in use — an area that
    # claims nothing, which is the "stale alias looks like coverage" this message names. That was
    # LOOSER than master, which compared exactly.
    placing = {nearest(u, area_claims) for u in (areas_in_use or ())}
    for n in (nodes if areas_in_use is not None else ()):
        for raw in n.areas:
            if nt(raw) not in placing:
                problems.append(f"features.md:{n.line}: `{n.slug}` claims area `{raw}`, which no "
                                f"backlog row uses — a stale alias looks like coverage")
    for area, owners in area_claims.items():
        if len(owners) > 1:
            problems.append(f"area `{area}` is claimed {len(owners)} times, by: {', '.join(owners)}"
                            f" — two spellings of one tag are one tag; keep a single entry")
    for anchor, owners in anchor_claims.items():
        if len(owners) > 1:
            problems.append(f"anchor `{anchor}` is claimed by {len(owners)} nodes: {', '.join(owners)}")
    for area in sorted(u for u in (areas_in_use or ()) if nearest(u, area_claims) is None):
        problems.append(f"backlog area `{area}` is claimed by no node — its rows cannot appear")
    for anchor in sorted(anchors_declared - set(anchor_claims)):
        problems.append(f"anchor `{anchor}` is claimed by no node — its specs, plans and ADRs "
                        f"cannot appear on the page")
    return problems


REPO = pathlib.Path(__file__).resolve().parent.parent
FEATURES = REPO / "docs" / "features.md"
ANCHORS_MD = REPO / "docs" / "anchors.md"
BACKLOG = REPO / "docs" / "backlog.md"


def main() -> int:
    for path in (FEATURES, ANCHORS_MD, BACKLOG):
        if not path.exists():
            print(f"CANNOT RUN — {path} is missing. Treat this as NOT RUN.", file=sys.stderr)
            return 2
    nodes, problems = parse_features(FEATURES.read_text())
    if not nodes:
        print("CANNOT RUN — docs/features.md declares no nodes. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    declared = anchor_slugs(ANCHORS_MD.read_text())
    if not declared:
        print("CANNOT RUN — no anchors parsed from docs/anchors.md. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    areas, area_problems = backlog_areas(BACKLOG.read_text())
    if not areas and not area_problems:
        print("CANNOT RUN — no `(area)` tags parsed from docs/backlog.md. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    problems += area_problems
    problems += check_nodes(nodes)
    problems += check_cross(nodes, declared, None if not areas else areas)
    if problems:
        print(f"FAILED — {len(problems)} feature-map problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    built = sum(1 for n in nodes if n.state == "built")
    print(f"feature map: {len(nodes)} nodes ({built} built, {len(nodes) - built} declared absent); "
          f"{len(declared)} anchors and {len(areas)} backlog areas all claimed exactly once")
    return 0


def _self_test() -> int:
    cases, failures = 0, 0
    def check(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            # ⭐ THE CANONICAL FORM. `check-plan-code.py`'s attribution parser accepts ONLY lines
            # starting with `[FAIL] `, the convention across this repo's suites. Review r1 measured
            # that an emoji form makes every mutation kill the suite UNATTRIBUTABLY.
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    TREE = """# Feature map
## PRODUCT
### summarise-a-video
state: built
for: Turns one video's transcript into a summary a person reads.
anchors: cloud-publishing

### rate-limiting-per-account
state: absent
for: Stops one account exhausting the shared spend cap.
expected-because: standard for a hosted multi-tenant service.
"""
    nodes, problems = parse_features(TREE)
    check("two nodes parsed", [n.slug for n in nodes], ["summarise-a-video", "rate-limiting-per-account"])
    check("trunk is carried down", nodes[0].trunk, "PRODUCT")
    check("state read", nodes[0].state, "built")
    check("anchors read", nodes[0].anchors, ["cloud-publishing"])
    check("absent reason read", nodes[1].expected_because, "standard for a hosted multi-tenant service.")
    check("absent node still says what it is for", nodes[1].purpose, "Stops one account exhausting the shared spend cap.")
    check("clean tree has no problems", problems, [])
    check("clean tree passes the rules", check_nodes(nodes), [])
    built_empty = TREE.replace("anchors: cloud-publishing\n", "")
    check("a built node with no fragment fails",
          any("no fragment" in p for p in check_nodes(parse_features(built_empty)[0])), True)
    absent_frag = TREE.replace("expected-because: standard for a hosted multi-tenant service.\n",
                               "expected-because: standard for a hosted multi-tenant service.\nanchors: cloud-publishing\n")
    check("an absent node WITH a fragment fails",
          any("flip it to `built`" in p for p in check_nodes(parse_features(absent_frag)[0])), True)
    absent_noreason = TREE.replace("expected-because: standard for a hosted multi-tenant service.\n", "")
    check("an absent node with no reason fails",
          any("expected-because" in p for p in check_nodes(parse_features(absent_noreason)[0])), True)
    statusy = TREE.replace("for: Turns one", "for: Currently turns one")
    check("a status token in prose fails",
          any("status token" in p for p in check_nodes(parse_features(statusy)[0])), True)
    built_reason = TREE.replace("for: Turns one video's transcript into a summary a person reads.\n",
                                "for: Turns one video's transcript into a summary a person reads.\nexpected-because: leftover from when this was absent.\n")
    check("a built node carrying expected-because fails",
          any("that line is" in p for p in check_nodes(parse_features(built_reason)[0])), True)
    dupe = TREE + "\n### summarise-a-video\nstate: built\nfor: A second one.\nanchors: cloud-sync\n"
    check("a duplicate slug fails",
          any("duplicate" in p for p in check_nodes(parse_features(dupe)[0])), True)
    wrapped = TREE.replace("for: Turns one video's transcript into a summary a person reads.\n",
                           "for: Turns one video's transcript\n  into a summary. Currently broken, see #322.\n")
    wnodes, wproblems = parse_features(wrapped)
    check("a wrapped for: line is REFUSED, not silently dropped",
          any("neither a field nor a heading" in p for p in wproblems), True)
    # ⛔ THE THREE FIXTURES BELOW ARE CODEX'S, VERBATIM WHERE IT GAVE ONE. Each is a line that the
    # old exemption tuple waved through, and each carries the two status tokens (`currently` and
    # `#322`) that made the bypass worth closing — ⚠ ILLUSTRATIVE OF THE ORIGINAL HOLE, NOT
    # LOAD-BEARING FOR THESE ASSERTIONS. Code review r2 (Claude) measured it: each case asserts
    # only that the line was REFUSED, and a refused line hits `continue` above and never reaches
    # `purpose`, so `STATUS_TOKENS` never runs on it — with the tokens deleted, and with a bare
    # `>`, all three stay green. So green here means the line was refused BEFORE any rule could be
    # asked about it, and THAT is the coverage: a line that never reaches `purpose` can never be
    # searched, which is precisely why the exemption was the Blocking. They are three cases and not
    # one because the prefixes fail independently: a repair that remembers `>` and forgets `<!--`
    # must still go red.
    FIRST_FOR = "for: Turns one video's transcript into a summary a person reads.\n"
    quoted = TREE.replace(FIRST_FOR, FIRST_FOR + "> currently broken, see #322.\n")
    check("a `>` blockquote line inside a node is REFUSED, not exempted",
          any("neither a field nor a heading" in p for p in parse_features(quoted)[1]), True)
    commented = TREE.replace(FIRST_FOR, FIRST_FOR + "<!-- currently broken, see #322. -->\n")
    check("an HTML comment line inside a node is REFUSED — a status token cannot ride in on it",
          any("neither a field nor a heading" in p for p in parse_features(commented)[1]), True)
    # Not a heading: `###` and `## ` are handled above, so what is left starting with `#` is prose.
    hashed = TREE.replace(FIRST_FOR, FIRST_FOR + "#322 has it currently broken.\n")
    check("a `#` line that is not a heading is REFUSED",
          any("neither a field nor a heading" in p for p in parse_features(hashed)[1]), True)
    # ⛔ CODEX'S OWN BYPASS: an `absent` node that carries a fragment passes if a later empty
    # `anchors:` blanks it. The second case is the half that matters — refusing the duplicate is
    # worth nothing if the value that survives is still the empty one.
    ABSENT_WHY = "expected-because: standard for a hosted multi-tenant service.\n"
    dup_anchors = TREE.replace(ABSENT_WHY, ABSENT_WHY + "anchors: cloud-publishing\nanchors:\n")
    dnodes, dproblems = parse_features(dup_anchors)
    check("a duplicate field is REFUSED, not applied last-write-wins",
          any("repeats the field `anchors`" in p for p in dproblems), True)
    check("the FIRST value stands, so a blanking duplicate cannot hide the fragment it contradicts",
          any("flip it to `built`" in p for p in check_nodes(dnodes)), True)
    check("`now` is no longer a banned word", STATUS_TOKENS.search("Shows what runs now") is None, True)
    ANCHORS = {"cloud-publishing", "cloud-sync"}
    check("clean cross-check is silent", check_cross(nodes, {"cloud-publishing"}, set()), [])
    bad, _ = parse_features(TREE.replace("cloud-publishing", "no-such-anchor"))
    check("an unknown anchor fails",
          any("no-such-anchor" in p for p in check_cross(bad, ANCHORS, set())), True)
    check("an anchor claimed by NO node fails",
          any("claimed by no node" in p and "cloud-sync" in p
              for p in check_cross(nodes, ANCHORS, set())), True)
    twice_a = TREE + "\n### another\nstate: built\nfor: A second claimant.\nanchors: cloud-publishing\n"
    check("an anchor claimed by TWO nodes fails",
          any("anchor `cloud-publishing` is claimed by 2 nodes" in p
              for p in check_cross(parse_features(twice_a)[0], {"cloud-publishing"}, set())), True)
    areas_tree, _ = parse_features(TREE.replace("anchors: cloud-publishing", "areas: (product)"))
    check("an area no backlog row uses fails",
          any("no backlog row uses" in p
              for p in check_cross(areas_tree, set(), {"cloud"})), True)
    check("an in-use area claimed by nobody fails",
          any("claimed by no node" in p and "`cloud`" in p
              for p in check_cross(areas_tree, set(), {"product", "cloud"})), True)
    twice_area = (TREE.replace("anchors: cloud-publishing", "areas: (product)")
                  + "\n### another\nstate: built\nfor: A second claimant.\nareas: (product)\n")
    check("an area claimed by TWO nodes fails",
          any("area `product` is claimed 2 times" in p
              for p in check_cross(parse_features(twice_area)[0], set(), {"product"})), True)
    def _bl(*rows: str) -> str:
        return ("## Items\n| # | Item | Touches | Size | Bundle | Status |\n|---|---|---|---|---|---|\n"
                + "\n".join(rows) + "\n")
    check("backlog areas are read from the area cell",
          backlog_areas(_bl("| 1 | x | f | S | (worker) | open |")), ({"worker"}, []))
    ESCAPED = r"| 90 | a \| b | f | S | (comprehensibility) | open \| still |"
    check("a row with an ESCAPED PIPE is not dropped", backlog_areas(_bl(ESCAPED)), ({"comprehensibility"}, []))
    # ── PER TAG, NORMALISED (backlog #381) ───────────────────────────────────────────────────────
    check("a cell with two tags puts BOTH in use",
          backlog_areas(_bl("| 1 | x | f | S | (tooling) (cloud / Money) | open |")),
          ({"tooling", "cloud / money"}, []))
    _mal = backlog_areas(_bl("| 2 | x | f | S | cloud | open |"))
    check("a malformed cell is REPORTED with its row, and its one guessed tag is still in use",
          (_mal[0], len(_mal[1]), "row 2" in " ".join(_mal[1]) and "'cloud'" in " ".join(_mal[1])),
          ({"cloud"}, 1, True))
    _pipe = backlog_areas(_bl(r"| 3 | x | f | S | (a \| b) (tooling) | open |"))
    check("a `|` inside a tag group is MALFORMED here too, and named by its row",
          (len(_pipe[1]), "row 3" in " ".join(_pipe[1])), (1, True))
    check("a non-item row is not read as a tag cell",
          backlog_areas(_bl()), (set(), []))
    # ⛔ backlog #381 r1, Codex M2: the TABLE'S shape decides, through the page's own parser.
    _extra = backlog_areas(_bl("| 4 | x | f | S | (tooling) | (tooling) | open |"))
    check("an EXTRA column separator is a gate FAILURE naming the row",
          (_extra[0], len(_extra[1]), "| 4 |" in " ".join(_extra[1])), (set(), 1, True))
    _short = backlog_areas(_bl("| 5 | x | f | S (tooling) | open |"))
    check("a MISSING column separator is a gate FAILURE naming the row",
          (_short[0], len(_short[1]), "| 5 |" in " ".join(_short[1])), (set(), 1, True))
    spelled = parse_features(TREE.replace("anchors: cloud-publishing",
                                          "areas: (cloud/money), (cloud / money)"))[0]
    check("two spellings of one tag on ONE node are a duplicate claim, not two areas",
          any("area `cloud / money` is claimed 2 times" in p
              for p in check_cross(spelled, set(), {"cloud / money"})), True)
    fam = parse_features(TREE.replace("anchors: cloud-publishing", "areas: (cloud)"))[0]
    check("an in-use leaf is claimed by its family's area, and that area is not stale",
          check_cross(fam, set(), {"cloud / new"}), [])
    # ⛔ backlog #381 r3, Codex X1 = Claude C1: a row-like line the parser cannot read is a gate
    # FAILURE naming the line — each was green at 988a5dbf, where master's gate was red.
    _decorated = ("⭐999", "#999", "**999**", "999a", "abc")
    _undecor = [backlog_areas(_bl(f"| {n} | x | f | S | (not-claimed) | open |")) for n in _decorated]
    check("a decorated or non-integer row number is a gate FAILURE naming the line, for every shape",
          [(len(b), f"| {n} |" in " ".join(b)) for n, (_a, b) in zip(_decorated, _undecor)],
          [(1, True)] * len(_decorated))
    _real = BACKLOG.read_text().split("\n")
    _at = next(i for i, l in enumerate(_real) if l.startswith("| 381 |"))
    _inside = backlog_areas("\n".join(_real[:_at + 1] + ["| ⭐999 | 🟡 **Probe** | f | S | (not-claimed) | open |"]
                                       + _real[_at + 1:]))
    check("a decorated row inside a copy of the REAL `## Items` table fails the gate, naming it",
          [p for p in _inside[1] if "⭐999" in p] != [] and len(_inside[1]) == 1, True)
    # ⛔ backlog #381 r2, Codex X1: a header that misspells `Bundle` is a gate FAILURE, not a table
    # whose every row is untagged — master FAILED on this probe, and the round-1 fold passed it.
    _bundel = backlog_areas(_bl("| 1 | x | f | S | (worker) | open |")
                            + "\n## Probe\n| # | Item | Touches | Size | Bundel | Status |\n"
                            "|---|---|---|---|---|---|\n| 999 | 🟡 **Probe** | f | S | (not-claimed) | open |\n")
    check("a table whose header misspells Bundle FAILS the gate, naming the table",
          (_bundel[0], len(_bundel[1]), "`## Probe`" in " ".join(_bundel[1])), (set(), 1, True))
    # ⛔ backlog #381 r4, Codex X1 — the probe verbatim: a table headed `| No |` (or with no header)
    # is a gate FAILURE naming its first line. Master's gate read the row; round 3's parser skipped it.
    _no = backlog_areas(_bl("| 1 | x | f | S | (worker) | open |")
                        + "\n## Probe\n| No | Item | Touches | Size | Bundle | Status |\n"
                        "|---|---|---|---|---|---|\n| ⭐999 | 🟡 **Probe** | f | S | (not-claimed) | open |\n")
    check("a table headed `| No |` FAILS the gate, naming its first line",
          (_no[0], len(_no[1]), "| No |" in " ".join(_no[1])), (set(), 1, True))
    # ⛔ backlog #381 r1, Claude M1: a family area that is nobody's NEAREST claimant places no row.
    both = parse_features(TREE.replace("anchors: cloud-publishing", "areas: (cloud), (cloud/money)"))[0]
    check("a family area that is nobody's NEAREST claimant is stale",
          [p for p in check_cross(both, set(), {"cloud / money"}) if "no backlog row uses" in p and "`(cloud)`" in p] != []
          and not any("`(cloud/money)`" in p for p in check_cross(both, set(), {"cloud / money"})), True)
    check("an UNREADABLE backlog (areas None) asks no per-area question, so the one real cause is not buried",
          tuple(sum("no backlog row uses" in p for p in check_cross(both, set(), a)) for a in (None, set())),
          (0, 2))
    check("a tag that merely SHARES a prefix is not in the family",
          any("claimed by no node" in p for p in check_cross(fam, set(), {"cloudy"})), True)
    # ── THE MESSAGES THEMSELVES — code review r3 (Claude), Medium ───────────────────────────────
    # ⛔ MEASURED BY THE REVIEWER: it put the pre-fix remedy string BACK — the exact defect round 3
    # reported — and this suite stayed 30/30 GREEN. Nothing read the text. The message is on its
    # fourth iteration, every one driven by a review rather than a gate, and the thing each
    # iteration changed was the one thing nothing measured. `check-ratchet-contract` cannot see it:
    # it knows the SCRIPT has a --self-test, not that a branch of it is unfalsifiable.
    def _dup(field: str, a: str, b: str) -> str:
        src = f"# Feature map\n## PRODUCT\n### x\n{field}: {a}\n{field}: {b}\nfor: A thing.\n"
        return " ".join(parse_features(src)[1])

    check("a duplicate SCALAR field is told to delete one, and NOT to use a comma list",
          ("holds a single value" in _dup("state", "built", "absent"),
           "comma-separated" in _dup("state", "built", "absent")), (True, False))
    check("a duplicate LIST field IS told to put the values on one comma-separated line",
          "ONE comma-separated line" in _dup("anchors", "a", "b"), True)
    check("a refused line states the GRAMMAR an author needs, not only the rationale",
          all(s in parse_features("# Feature map\n## PRODUCT\n### x\n state: built\n")[1][0]
              for s in ("COLUMN 0", "no space before the colon", "expected-because")), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())

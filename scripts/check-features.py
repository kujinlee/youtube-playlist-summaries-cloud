#!/usr/bin/env python3
"""Validate docs/features.md — the feature tree the /features page renders.

    python3 scripts/check-features.py             # validate the living tree
    python3 scripts/check-features.py --self-test # 30 cases against synthetic trees
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
FIELD = re.compile(r"^(state|for|areas|anchors|expected-because):\s*(.*)$")

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
                    f"heading: {line.strip()[:40]!r}. Keep each field on ONE line — a wrapped `for:` "
                    f"would hide its own status tokens from the check. No prefix is exempt: a "
                    f"blockquote, an HTML comment and a stray `#` are text inside a node too")
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
            problems.append(f"features.md:{i}: `{n.slug}` repeats the field `{key}` — a duplicate "
                            f"is refused, not merged. Under last-write-wins a later line silently "
                            f"replaces an earlier one, and what it replaces is never searched")
            continue
        seen_fields.add(key)
        if key == "state": n.state = value
        elif key == "for": n.purpose = value
        elif key == "expected-because": n.expected_because = value
        elif key == "areas": n.areas = [a.strip() for a in value.split(",") if a.strip()]
        elif key == "anchors": n.anchors = [a.strip() for a in value.split(",") if a.strip()]
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


CELL_SPLIT = re.compile(r"(?<!\\)\|")


def backlog_areas(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.split("\n"):
        if not line.startswith("| "):
            continue
        cells = CELL_SPLIT.split(line)
        if len(cells) < 7:
            continue
        cell = cells[-3].strip()
        if cell.startswith("(") and cell.endswith(")"):
            out.add(cell)
    return out


def anchor_slugs(text: str) -> set[str]:
    return set(re.findall(r"^\|\s*`([a-z0-9-]+)`\s*\|", text, re.MULTILINE))


def check_cross(nodes, anchors_declared: set[str], areas_in_use: set[str]) -> list[str]:
    problems: list[str] = []
    area_claims: dict[str, list[str]] = {}
    anchor_claims: dict[str, list[str]] = {}
    for n in nodes:
        for a in n.anchors:
            anchor_claims.setdefault(a, []).append(n.slug)
            if a not in anchors_declared:
                problems.append(f"features.md:{n.line}: `{n.slug}` names anchor `{a}`, which is not "
                                f"in docs/anchors.md")
        for area in n.areas:
            area_claims.setdefault(area, []).append(n.slug)
            if area not in areas_in_use:
                problems.append(f"features.md:{n.line}: `{n.slug}` claims area `{area}`, which no "
                                f"backlog row uses — a stale alias looks like coverage")
    for area, owners in area_claims.items():
        if len(owners) > 1:
            problems.append(f"area `{area}` is claimed by {len(owners)} nodes: {', '.join(owners)}")
    for anchor, owners in anchor_claims.items():
        if len(owners) > 1:
            problems.append(f"anchor `{anchor}` is claimed by {len(owners)} nodes: {', '.join(owners)}")
    for area in sorted(areas_in_use - set(area_claims)):
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
    areas = backlog_areas(BACKLOG.read_text())
    if not areas:
        print("CANNOT RUN — no `(area)` tags parsed from docs/backlog.md. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    problems += check_nodes(nodes)
    problems += check_cross(nodes, declared, areas)
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
    # `#322`) the rule above exists to find — so a case going green here means a status line has
    # been read, not that a parser was tidy. They are three cases and not one because the prefixes
    # fail independently: a repair that remembers `>` and forgets `<!--` must still go red.
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
              for p in check_cross(areas_tree, set(), {"(cloud)"})), True)
    check("an in-use area claimed by nobody fails",
          any("claimed by no node" in p and "(cloud)" in p
              for p in check_cross(areas_tree, set(), {"(product)", "(cloud)"})), True)
    twice_area = (TREE.replace("anchors: cloud-publishing", "areas: (product)")
                  + "\n### another\nstate: built\nfor: A second claimant.\nareas: (product)\n")
    check("an area claimed by TWO nodes fails",
          any("area `(product)` is claimed by 2 nodes" in p
              for p in check_cross(parse_features(twice_area)[0], set(), {"(product)"})), True)
    check("backlog areas are read from the area cell",
          backlog_areas("| 1 | x | f | S | (worker) | open |"), {"(worker)"})
    ESCAPED = r"| 90 | a \| b | f | S | (comprehensibility) | open \| still |"
    check("a row with an ESCAPED PIPE is not dropped", backlog_areas(ESCAPED), {"(comprehensibility)"})
    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())

#!/usr/bin/env python3
"""Validate docs/features.md — the feature tree the /features page renders.

    python3 scripts/check-features.py             # validate the living tree
    python3 scripts/check-features.py --self-test # 16 cases against synthetic trees
"""
import re, sys
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
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if line.startswith("## ") and not line.startswith("###"):
            trunk = line[3:].strip(); continue
        if line.startswith("###"):
            level = len(line) - len(line.lstrip("#"))
            slug = line.lstrip("#").strip()
            if not trunk:
                problems.append(f"features.md:{i}: node `{slug}` sits outside any trunk")
            nodes.append(Node(slug=slug, level=level, trunk=trunk, line=i)); continue
        m = FIELD.match(line)
        if not m:
            # ⭐ A WRAPPED `for:` LINE MUST NOT BE SILENTLY DROPPED (review r1 High 8). Continuation
            # text used to fail FIELD and get skipped, so `for: …\n  Currently broken, see #322.`
            # left the banned words out of `purpose` entirely and the status-token rule reported
            # nothing. Refusing the line is the "cannot run is a failure" posture.
            if nodes and line.strip() and not line.startswith(("#", "<!--", ">")):
                problems.append(
                    f"features.md:{i}: `{nodes[-1].slug}` has a line that is neither a field nor a "
                    f"heading: {line.strip()[:40]!r}. Keep each field on ONE line — a wrapped `for:` "
                    f"would hide its own status tokens from the check")
            continue
        if not nodes:
            problems.append(f"features.md:{i}: field `{m.group(1)}` before any node"); continue
        key, value = m.group(1), m.group(2).strip()
        n = nodes[-1]
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
    check("`now` is no longer a banned word", STATUS_TOKENS.search("Shows what runs now") is None, True)
    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else 0)

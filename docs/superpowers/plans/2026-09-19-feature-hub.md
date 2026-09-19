# Feature hub Implementation Plan

> **Anchor:** `feature-map` — **ADR:** none
> **Goal:** Anyone can find what the system does today, what it is missing on purpose, and every fragment that defines each — without searching.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A page at `/features` showing what this system does, what it deliberately does not, and the fragments that define each — derived from declarations, never hand-maintained.

**Architecture:** One hand-written data file (`docs/features.md`) holds a feature tree: trunks, nodes, one purpose sentence each, and alias lines pointing at existing vocabularies. `check-features.py` **owns the grammar** and validates it; `gen-features-page.py` **imports that parser** and renders. This split is deliberate — two parsers for one grammar is the drift shape this repo has measured 13 times, and `check-dashboard-entry.py` already sets the precedent by owning the entry-header grammar that its page imports.

**Tech Stack:** Python, stdlib only — no `yaml` is installed. ⚠ Measured 2026-09-19: this machine runs **3.14**, `schema-gates.yml` pins **3.12**, and the `verify` job takes the runner default. Write for 3.12+; `str | None` and `dataclasses` are fine on both.

**Spec:** `docs/superpowers/specs/2026-09-19-feature-hub-design.md`

## Global Constraints

Copied verbatim from the spec and this repo's enforced conventions. Every task's requirements implicitly include this section.

- **Every guard under `scripts/` needs three things** or `check-ratchet-contract.py` fails it: a `--self-test` entry point (R1), something that EXECUTES it or a written `NO-CALLER:` reason (R3), and a mutation manifest or a written `NO-MUTATIONS:` reason (R4).
- **Declare the self-test count in the docstring, in the canonical form** `--self-test  # N cases`. `check-selftest-counts.py` runs each suite as a subprocess and compares. A number in prose has no owner.
- **"Cannot run" is a FAILURE, never a pass.** Unreadable or missing input → print `CANNOT RUN — … Treat this as NOT RUN.` to stderr and `return 2`.
- **Derived pages are never hand-edited.** Everything on `/features` except each node's `for:` sentence is derived.
- **Node prose may contain no status token.** A status token is: a status marker (`✅ 🔴 🟠 🟢 ⏳ ◀`), a PR/issue reference (`#` followed by digits), or one of the words *currently, already, still, yet, planned, done, TODO*, or the phrase *in progress*. Matching is case-insensitive on word boundaries.
- **Node states:** `built` (≥1 fragment, no `expected-because:`) or `absent` (an `expected-because:` line, zero fragments). Both directions enforced.
- **Python only from the stdlib.** `yaml` and `tomllib`-for-writing are unavailable; `tomllib` (read-only) exists but is not needed here.
- **A self-test prints failures as `  [FAIL] <case name>: got … want …`.** `check-plan-code.py`'s
  attribution parser accepts ONLY lines starting with `[FAIL] `, and it is the convention across this repo's suites.
  Review r1 measured an emoji form making every mutation kill the suite UNATTRIBUTABLY — the third
  recorded instance in this repo. **Fix the print contract BEFORE registering a manifest.**
- **Never write a second splitter for a markdown table.** `check-docs.py:319` owns
  `CELL_SPLIT = re.compile(r"(?<!\\)\|")`; a naive `split("|")` drops every row with an escaped
  pipe, measured on backlog rows #90 and #110.
- Anything longer than a line goes in a FILE, never a shell argument (`git commit -F`, `--body-file`).

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/features.md` | **Data.** The tree, one purpose sentence per node, alias lines. Names, never state. |
| `scripts/check-features.py` | **Owns the grammar.** Parses `features.md`, validates it against `anchors.md` and `backlog.md`. `--self-test`. |
| `scripts/gen-features-page.py` | **Renders.** Imports the parser from `check-features.py`, resolves fragments, writes `~/explainers/features.html`. `--self-test`. |
| `.claude/hooks/regen-features-page.sh` | Rebuild the page when any source changes. Never blocks. |
| `scripts/explainer-serve.py` | Register `features` in `REGENERABLE` and `PAGE_SOURCES`. |
| `.github/workflows/ci.yml` | Two steps: the check, and its self-test. |
| `scripts/mutations/check-features.json` | Mutation manifest for the guard. |

---

## Task 1: The grammar and the node-state rules

**Files:**
- Create: `scripts/check-features.py`
- Create: `docs/features.md` (a minimal 3-node tree, expanded in Task 2)

**Interfaces:**
- Consumes: nothing.
- Produces: `parse_features(text: str) -> tuple[list[Node], list[str]]` returning nodes and problems; `Node` is a dataclass with fields `slug: str`, `level: int`, `trunk: str`, `state: str`, `purpose: str`, `areas: list[str]`, `anchors: list[str]`, `expected_because: str | None`, `line: int`. Also `STATUS_TOKENS: re.Pattern` and `check_nodes(nodes) -> list[str]`. Task 2 adds the cross-file rules; Task 4 imports `parse_features` and `Node`.

- [ ] **Step 1: Write the failing test**

Create `scripts/check-features.py` with only the self-test harness and the cases, so the suite exists before the parser does:

```python
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


def _self_test() -> int:
    cases, failures = 0, 0
    def check(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            # ⭐ THE CANONICAL FORM. `check-plan-code.py`'s attribution parser accepts ONLY lines
            # starting with `[FAIL] `; 39 suites already print it. Review r1 Blocking 2 measured
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/check-features.py --self-test`
Expected: `NameError: name 'parse_features' is not defined`

- [ ] **Step 3: Write the parser and the rules**

Insert above `_self_test`:

```python
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


```

- [ ] **Step 4: Run the self-test to verify it passes**

Run: `python3 scripts/check-features.py --self-test`
Expected: `16/16 self-test cases passed`, exit 0. ⚠ **This was MEASURED, not asserted** — the first version of this plan claimed 12/12 and actually ran 11/12, because its `absent` fixture had no `for:` line while the rule requires one on every node.

- [ ] **Step 5: Create the minimal tree so the script has real input**

Create `docs/features.md`:

```markdown
# Feature map

**What this system does, what it deliberately does not, and where each is defined.** Rendered at
http://127.0.0.1:7391/features by `scripts/gen-features-page.py`; validated by
`scripts/check-features.py`.

**This file holds NAMES and PURPOSE, never STATE.** A node says what it is *for*; where it stands is
derived from the fragments beneath it. Do not add status, progress or "what's next" — a central file
that holds state drifts, and this project has measured that twice (see `docs/anchors.md`).

## PLATFORM

### job-queue-and-worker-lifecycle
state: built
for: Runs summarisation work reliably in the background, one job at a time, without losing or double-charging any of it.
anchors: cloud-publishing

### wake-on-visit
state: built
for: Lets the worker sleep when there is nothing to do and wake when a visitor causes work.
anchors: cloud-publishing
```

- [ ] **Step 6: Run the checker against the real tree**

Run: `python3 scripts/check-features.py --self-test`
Expected: `15/15`. ⚠ **Do NOT run the bare `check-features.py` yet and do not read its exit 0 as a pass** — the entry point returns 0 for any non-`--self-test` invocation until Task 2 gives it a real `main()`. An exit 0 from a script that checked nothing is the "cannot run reported as a pass" shape this repo treats as a failure.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-features.py docs/features.md
git commit -F /tmp/t1.txt
```

Write `/tmp/t1.txt` first (never pass a multi-line message as a shell argument):

```
Feature-map grammar, owned in one place, with the built/absent rule its first version got wrong

`check-features.py` owns the grammar and `gen-features-page.py` will import it rather than
re-implement it -- two parsers for one grammar is the drift shape this repo has measured repeatedly.

The rule worth noting is `absent`. An earlier design required every node to name a fragment, which
made the most valuable entry illegal: a necessary feature that does not exist has no spec, no backlog
row and no code, so its absence stayed invisible. A node is now `built` (names >=1 fragment) or
`absent` (carries an `expected-because:` and names none), and BOTH directions fail -- so a feature
cannot quietly get implemented while the tree still says it does not exist.

16/16 self-test cases pass.
```

---

## Task 2: Cross-file rules — anchors resolve, and every backlog area is claimed exactly once

**Files:**
- Modify: `scripts/check-features.py`

**Interfaces:**
- Consumes: `Node`, `parse_features`, `check_nodes`.
- Produces: `CELL_SPLIT`; `backlog_areas(text) -> set[str]`; `anchor_slugs(text) -> set[str]`; `check_cross(nodes, anchors_declared, areas_in_use) -> list[str]`; a real `main()` returning 0/1/2.

- [ ] **Step 1: Write the failing tests**

Add to `_self_test`, and raise the docstring count from 16 to **24**:

```python
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
    check("backlog areas are read from the area cell",
          backlog_areas("| 1 | x | f | S | (worker) | open |"), {"(worker)"})
    ESCAPED = r"| 90 | a \| b | f | S | (comprehensibility) | open \| still |"
    check("a row with an ESCAPED PIPE is not dropped", backlog_areas(ESCAPED), {"(comprehensibility)"})
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-features.py --self-test`
Expected: `NameError: name 'check_cross' is not defined`

- [ ] **Step 3: Implement the cross-file rules and a real main**

```python
import pathlib   # add to the existing `import re, sys` line

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

```

Change the entry point to:

```python
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
```

- [ ] **Step 4: Run the self-test and the real check**

Run: `python3 scripts/check-features.py --self-test && python3 scripts/check-features.py`
Expected: `24/24 self-test cases passed`, then a FAILED list of unclaimed anchors and areas.

⚠ **The real run is expected to FAIL first — MEASURED, not predicted.** Run against today's repo with a one-node tree it printed:

```
FAILED — N feature-map problem(s):
  ✗ backlog area `(cloud / money)` is claimed by no node — its rows cannot appear
  ✗ backlog area `(cloud)` is claimed by no node — its rows cannot appear
```

That is the tool doing its job. Add `areas:` and `anchors:` lines to `docs/features.md` until it passes. **`(cloud/money)` and `(cloud / money)` will both appear: claim both on the same node's `areas:` line**, which is the point of the design — the duplicate becomes visible side by side.

⚠ Also verify the four CANNOT-RUN paths, all measured to return **rc=2**: `features.md` missing; `features.md` with no nodes; `anchors.md` yielding no anchors; `backlog.md` yielding no `(area)` tags.

- [ ] **Step 5: Commit**

---

## Task 3: The real tree

⚠ **The `Feature` column an earlier draft added to `anchors.md` is GONE.** Review r1 (both halves) found it was written by Task 2 and read by nothing, and that it pointed the opposite way to the `anchors:` line the parser actually uses — two directions for one edge. The spec is amended; the node names its anchors, and `check_cross` requires **every anchor to be claimed by exactly one node**, which is what makes an index that lists its members safe.

**Files:**
- Modify: `docs/features.md` (expand to the full tree)

**Interfaces:**
- Consumes: the COMPLETE checker from Tasks 1 and 2 — `parse_features`, `check_nodes`, `check_cross`, `anchor_slugs`, `backlog_areas` and `main()`. ⚠ This task deliberately comes AFTER them: review r2 Blocking 1 caught an ordering where the tree was written against a checker that did not exist yet, so its Step 1 could not run.
- Produces: a `docs/features.md` with all three trunks, every one of the 13 anchors claimed by exactly one node, and every one of the 21 backlog areas claimed by exactly one node.

- [ ] **Step 1: List everything that must be claimed**

```bash
python3 -c "import re,pathlib;print(sorted(re.findall(r'^\|\s*\`([a-z0-9-]+)\`\s*\|',pathlib.Path('docs/anchors.md').read_text(),re.M)))"
python3 scripts/check-features.py 2>&1 | grep 'claimed by no node'
```

The first prints the 13 anchors; the second every unclaimed backlog area. **Every name in both lists needs a home in Step 2**, or the check stays red.

- [ ] **Step 2: Write the full tree**

Expand `docs/features.md` to all three trunks. Every node needs `state:` and `for:`; `built` nodes need at least one `anchors:` or `areas:` entry. Use the API surface as the source for PRODUCT nodes:

Run: `find app/api -name route.ts | sort` — each route family is a candidate node (`playlists`, `videos`, `share`, `pdf`, `html-doc`, `quick-view`, `jobs`, `ingest`, folder routes).

Include at least one `absent` node, so the state is exercised by real data. A true one, measured this session:

```markdown
### dig-job-recovery
state: absent
for: Un-sticks a dig job whose worker went to sleep at the wrong moment.
expected-because: dig inherits the same worker exit-window race a summary does, but listByPlaylist filters job_kind = summary, so the read-path recoverer cannot see it.
```

- [ ] **Step 4: Run both checks**

Run: `python3 scripts/check-features.py --self-test && python3 scripts/check-features.py`
Expected: `24/24 self-test cases passed`, then `feature map: N nodes (…); 13 anchors and 21 backlog areas all claimed exactly once`.

⚠ Keep going until the second command exits 0. A remaining `claimed by no node` line is not cosmetic — that anchor's specs and ADRs, or that area's backlog rows, cannot appear on the page at all.

- [ ] **Step 5: Commit**

```bash
git add docs/features.md docs/anchors.md
git commit -F /tmp/t2.txt
```

---

## Task 4: The page

**Files:**
- Create: `scripts/gen-features-page.py`
- Modify: `scripts/explainer-serve.py` (register the page)

**Interfaces:**
- Consumes: `parse_features`, `Node` — imported from `check_features` via `importlib` (the filename has a hyphen, so a plain `import` will not work).
- Produces: `~/explainers/features.html`; `render(nodes, fragments) -> str`.

- [ ] **Step 1: Write the failing test**

Create `scripts/gen-features-page.py` with a docstring declaring `--self-test  # 6 cases`, the same `[FAIL]`-printing `check()` helper as Task 1, and these cases. ⚠ **Build `nodes` inside the test** — an earlier draft referenced an undefined `nodes` (review r1 Medium 11):

```python
    nodes, _ = parse_features(
        "## PLATFORM\n"
        "### wake-on-visit\nstate: built\nfor: Lets the worker sleep until a visitor needs it.\n"
        "anchors: cloud-publishing\n\n"
        "### dig-job-recovery\nstate: absent\nfor: Un-sticks a dig job whose worker slept.\n"
        "expected-because: dig inherits the same race and nothing rescues it.\n")
```

then:

```python
    html = render(nodes, {"wake-on-visit": {"backlog": ["#139 a deploy kills the summary"], "adr": []}})
    check("a node's purpose is rendered", "Lets the worker sleep" in html, True)
    check("an absent node is marked", "not built" in html, True)
    check("the absent reason is shown", "expected because" in html.lower(), True)
    check("a linked gap appears", "#139" in html, True)
    check("the absence count is shown", "1 declared absence" in html, True)
    check("no node is rendered twice", html.count("id=\"wake-on-visit\""), 1)
```

Import the parser like this (a hyphenated filename cannot be imported normally):

```python
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location(
    "check_features", pathlib.Path(__file__).with_name("check-features.py"))
check_features = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_features)
parse_features, Node = check_features.parse_features, check_features.Node
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/gen-features-page.py --self-test`
Expected: `NameError: name 'render' is not defined`

- [ ] **Step 3: Implement fragment resolution and rendering**

Resolve per node, all derived:
- **backlog rows** — rows whose area cell is in `node.areas`; render id, severity marker and the first sentence, each linking to `/backlog-table#<id>`.
- **ADRs and specs** — via the anchors named on the node: read `docs/anchors.md` for the ADR numbers, and `docs/superpowers/specs/*.md` + `plans/*.md` for files whose `Anchor:` header matches.
- **recent changes** — `git log --oneline -n 400` subjects matching `\(#\d+\)` whose subject mentions the node slug's words; cap at 5 per node.
- **reviews** — files under `docs/reviews/**` whose stem contains the node slug.

Follow the existing page chrome: read `scripts/gen-goals-page.py` and reuse its theme/header approach rather than inventing a second look.

- [ ] **Step 4: Run the self-test**

Run: `python3 scripts/gen-features-page.py --self-test`
Expected: `6/6 self-test cases passed`

- [ ] **Step 5: Register the page with the server**

⚠ **The dicts are `REGENERABLE` and `PAGE_SOURCES`** — an earlier draft named them `PAGES` and `SOURCES`, which do not exist (review r1 Medium 10). In `scripts/explainer-serve.py`, add to `REGENERABLE` (near line 122) and `PAGE_SOURCES` (near line 140):

```python
    "features": "gen-features-page.py",
```
```python
    "features": ["docs/features.md", "docs/anchors.md", "docs/backlog.md"],
```

⚠ The two dicts are keyed identically and `_stale_sources_covered` in that file's self-test **checks that they are**. Add to both, then run `python3 scripts/explainer-serve.py --self-test`.

- [ ] **Step 6: Generate and look at it**

Run: `python3 scripts/gen-features-page.py && EXPLAINER_DOCS_ROOT=$PWD python3 scripts/explainer-serve.py`
Open `http://127.0.0.1:7391/features`. Confirm the trunks, at least one absent node, and that gap links resolve.

- [ ] **Step 7: Commit**

---

## Task 5: The hook, so the page cannot go quietly stale

**Files:**
- Create: `.claude/hooks/regen-features-page.sh`

**Interfaces:**
- Consumes: `scripts/gen-features-page.py`.
- Produces: nothing importable.

- [ ] **Step 1: Write the hook**

Copy `.claude/hooks/regen-goals-page.sh` and change three things: the source `case` list to `docs/features.md`, `docs/anchors.md`, `docs/backlog.md`; the script it runs; and the URL it prints. **Keep `exit 0` on every path** — the hook must never block a turn.

- [ ] **Step 2: Make it executable and test both paths**

```bash
chmod +x .claude/hooks/regen-features-page.sh
echo '{"tool_input":{"file_path":"docs/features.md"}}' | .claude/hooks/regen-features-page.sh; echo "rc=$?"
echo '{"tool_input":{"file_path":"README.md"}}'        | .claude/hooks/regen-features-page.sh; echo "rc=$?"
```
Expected: the first prints `↻ features view regenerated`, the second is silent. **Both exit 0.**

- [ ] **Step 3: Register the hook**

Add it to `.claude/settings.json` alongside `regen-goals-page.sh`, matching that entry's event and matcher exactly.

- [ ] **Step 4: Commit**

---

## Task 6: Enforcement — CI, and mutations that prove the guard bites

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `scripts/mutations/check-features.json`

**Interfaces:**
- Consumes: `scripts/check-features.py`.
- Produces: a CI-enforced guard satisfying `check-ratchet-contract.py` R1/R3/R4.

- [ ] **Step 1: Wire both CI steps**

After the `check-anchors` steps (near `ci.yml:183`), matching their shape exactly:

```yaml
      - name: check-features
        run: python3 scripts/check-features.py

      - name: check-features self-test
        run: python3 scripts/check-features.py --self-test
```

- [ ] **Step 2: Write the mutation manifest**

Create `scripts/mutations/check-features.json`. Each entry names a case that must go red:

```json
[
  {
    "name": "a built node with no fragment stops failing",
    "file": "scripts/check-features.py",
    "edits": [["        if n.state == \"built\" and fragments == 0:\n", "        if False:\n"]],
    "expect": ["a built node with no fragment fails"]
  },
  {
    "name": "an absent node may carry fragments again",
    "file": "scripts/check-features.py",
    "edits": [["            if fragments:\n", "            if False:\n"]],
    "expect": ["an absent node WITH a fragment fails"]
  },
  {
    "name": "status tokens stop being rejected in node prose",
    "file": "scripts/check-features.py",
    "edits": [["            hit = STATUS_TOKENS.search(n.purpose)\n", "            hit = None\n"]],
    "expect": ["a status token in prose fails"]
  },
  {
    "name": "a built node may carry an absence argument again",
    "file": "scripts/check-features.py",
    "edits": [["        if n.state == \"built\" and n.expected_because:\n", "        if False:\n"]],
    "expect": ["a built node carrying expected-because fails"]
  },
  {
    "name": "an unclaimed backlog area stops being reported",
    "file": "scripts/check-features.py",
    "edits": [["    for area in sorted(areas_in_use - set(area_claims)):\n", "    for area in []:\n"]],
    "expect": ["an in-use area claimed by nobody fails"]
  }
]
```

- [ ] **Step 3: Register both new scripts in the two ratchets that pin them**

Neither is optional; review r1 measured both as red-on-arrival.

1. `scripts/check-plan-code.py` — `EXPECTED_MUTATIONS` (near line 522) pins how many entries each manifest has. Add `"scripts/check-features.py": 5` — ⚠ **a full path, not a bare name.** The runner compares these keys to each manifest's `"file"` value (`check-plan-code.py:1145`), and every existing key is a path (`"scripts/check-anchors.py": 5`). A bare name matches nothing and the run fails before measuring coverage. `POPULATION` is the opposite — **bare names** — so the two registrations do NOT take the same string.
2. `scripts/check-selftest-counts.py` — `POPULATION` (near line 83) lists the scripts whose declared count is verified by running it. Add **both** `check-features.py` and `gen-features-page.py`.

⚠ `gen-features-page.py` is a script under `scripts/` and therefore also owes R4 — a mutation manifest **or a written `NO-MUTATIONS:` reason in its docstring**. Write the reason, and say why:

```
NO-MUTATIONS: this renders; it decides nothing. Its 6 cases assert the rendered STRING, so a
manifest would re-state the same assertions one layer out. The rules that can be got wrong live
in check-features.py, which has one.
```

- [ ] **Step 4: Prove every mutation is killed, over a control proved green first**

```bash
python3 scripts/check-features.py --self-test        # CONTROL — must be green BEFORE mutating
python3 scripts/check-plan-code.py --mutate .        # applies the manifest; each must go red
```
Expected: 5/5 killed. ⚠ **A surviving mutation means the case passes for a reason other than the one it names** — this happened four times in PR #322. Fix the case, not the manifest.

- [ ] **Step 5: Confirm the ratchet contract is satisfied**

Run: `python3 scripts/check-ratchet-contract.py`
Expected: exit 0 — `check-features.py` has a `--self-test` (R1), a CI caller (R3), and a manifest (R4).

- [ ] **Step 6: Confirm the declared self-test count is verified**

Run: `python3 scripts/check-selftest-counts.py`
Expected: the docstring's `# 24 cases` matches what the suite prints. If it drifts, fix the docstring — the count has one home.

- [ ] **Step 7: Commit and open the PR**

Per `docs/dev-process.md` Phase 5: branch + PR, and **merging stays a human gate**. Use `--body-file`, never `--body`.

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Feature tree, three trunks | 3 |
| Anchors attach rather than form the spine | 3 declares them; 2 enforces one-claim-each |
| `built` / `absent` node states, both directions enforced | 1 |
| `expected-because:` required on absences | 1 |
| Prose bounded, status tokens rejected | 1 |
| `areas:` alias map, no per-row backlog edits | 2 |
| Every in-use area claimed exactly once | 2 |
| Anchors resolve to the registry | 2 |
| `backlog.md` unparseable → exit 2 | 2 |
| Page at `/features`, derived | 4 |
| Rebuild hook | 5 |
| CI-wired check with `--self-test` and mutations | 6 |
| Absence count shown on the page | 4 |
| Tests/code modules excluded as fragments | — by omission; no task adds them |
| `/goals` not retired | — by omission; no task touches it |

**Placeholder scan:** none — every code step carries runnable code; the one open-ended step (Task 2's tree contents) names its source (`find app/api -name route.ts`) and a concrete measured example.

**Type consistency:** `parse_features` returns `(list[Node], list[str])` in Tasks 1, 2 and 4. `check_nodes(nodes)` and `check_cross(nodes, anchor_slugs, areas_in_use)` take the same `Node` dataclass throughout. `backlog_areas(text) -> set[str]` feeds `check_cross`'s third parameter in both the self-test and `main()`. The self-test count rises 16 → 24 in Task 2 and is verified by `check-selftest-counts.py` in Task 6.

**What review round 1 changed, so a reader can see which claims are now measured rather than asserted.** Both halves ran this plan's code; it did not pass. The corrections: the self-test fixture gained the `for:` line it was missing (11/12 → 23/23, run from the plan itself); `check()` now prints the canonical `[FAIL] ` line the mutation harness can attribute, which this repo's suites already use; the table read uses `check-docs.py`'s escaped-pipe `CELL_SPLIT`, measured to recover backlog rows #90 and #110 that the naive split dropped; wrapped `for:` lines are refused rather than silently truncated, which had disabled the status-token rule entirely; `now` left the banned-word list after it was measured rejecting 1 in 13 of this repo's own purpose-shaped sentences; the `Feature` column is gone as a duplicate edge; `REGENERABLE`/`PAGE_SOURCES` replace two dict names that do not exist; and Task 6 now registers both scripts in `EXPECTED_MUTATIONS` and `POPULATION`, without which three of its gates were red on arrival.

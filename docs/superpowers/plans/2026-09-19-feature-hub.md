# Feature hub Implementation Plan

> **Anchor:** `feature-map` — **ADR:** none
> **Goal:** Anyone can find what the system does today, what it is missing on purpose, and every fragment that defines each — without searching.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A page at `/features` showing what this system does, what it deliberately does not, and the fragments that define each — derived from declarations, never hand-maintained.

**Architecture:** One hand-written data file (`docs/features.md`) holds a feature tree: trunks, nodes, one purpose sentence each, and alias lines pointing at existing vocabularies. `check-features.py` **owns the grammar** and validates it; `gen-features-page.py` **imports that parser** and renders. This split is deliberate — two parsers for one grammar is the drift shape this repo has measured 13 times, and `check-dashboard-entry.py` already sets the precedent by owning the entry-header grammar that its page imports.

**Tech Stack:** Python 3.12 stdlib only (no yaml, no toml libs — none are installed). Bash for the hook. GitHub Actions for CI.

**Spec:** `docs/superpowers/specs/2026-09-19-feature-hub-design.md`

## Global Constraints

Copied verbatim from the spec and this repo's enforced conventions. Every task's requirements implicitly include this section.

- **Every guard under `scripts/` needs three things** or `check-ratchet-contract.py` fails it: a `--self-test` entry point (R1), something that EXECUTES it or a written `NO-CALLER:` reason (R3), and a mutation manifest or a written `NO-MUTATIONS:` reason (R4).
- **Declare the self-test count in the docstring, in the canonical form** `--self-test  # N cases`. `check-selftest-counts.py` runs each suite as a subprocess and compares. A number in prose has no owner.
- **"Cannot run" is a FAILURE, never a pass.** Unreadable or missing input → print `CANNOT RUN — … Treat this as NOT RUN.` to stderr and `return 2`.
- **Derived pages are never hand-edited.** Everything on `/features` except each node's `for:` sentence is derived.
- **Node prose may contain no status token.** A status token is: a status marker (`✅ 🔴 🟠 🟢 ⏳ ◀`), a PR/issue reference (`#` followed by digits), or one of the words *currently, now, already, still, yet, planned, done, TODO*, or the phrase *in progress*. Matching is case-insensitive on word boundaries.
- **Node states:** `built` (≥1 fragment, no `expected-because:`) or `absent` (an `expected-because:` line, zero fragments). Both directions enforced.
- **Python only from the stdlib.** `yaml` and `tomllib`-for-writing are unavailable; `tomllib` (read-only) exists but is not needed here.
- Anything longer than a line goes in a FILE, never a shell argument (`git commit -F`, `--body-file`).

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/features.md` | **Data.** The tree, one purpose sentence per node, alias lines. Names, never state. |
| `scripts/check-features.py` | **Owns the grammar.** Parses `features.md`, validates it against `anchors.md` and `backlog.md`. `--self-test`. |
| `scripts/gen-features-page.py` | **Renders.** Imports the parser from `check-features.py`, resolves fragments, writes `~/explainers/features.html`. `--self-test`. |
| `.claude/hooks/regen-features-page.sh` | Rebuild the page when any source changes. Never blocks. |
| `docs/anchors.md` | Gains a `Feature` column so each anchor names its node. |
| `scripts/explainer-serve.py` | Register `features` in `PAGES` and `SOURCES`. |
| `.github/workflows/ci.yml` | Two steps: the check, and its self-test. |
| `scripts/mutations/check-features.json` | Mutation manifest for the guard. |

---

## Task 1: The grammar and the node-state rules

**Files:**
- Create: `scripts/check-features.py`
- Create: `docs/features.md` (a minimal 3-node tree, expanded in Task 2)

**Interfaces:**
- Consumes: nothing.
- Produces: `parse_features(text: str) -> tuple[list[Node], list[str]]` returning nodes and problems; `Node` is a dataclass with fields `slug: str`, `level: int`, `trunk: str`, `state: str`, `purpose: str`, `areas: list[str]`, `anchors: list[str]`, `expected_because: str | None`, `line: int`. Also `STATUS_TOKENS: re.Pattern` and `check_nodes(nodes) -> list[str]`. Task 3 adds cross-file rules; Task 4 imports `parse_features` and `Node`.

- [ ] **Step 1: Write the failing test**

Create `scripts/check-features.py` with only the self-test harness and the cases, so the suite exists before the parser does:

```python
#!/usr/bin/env python3
"""Validate docs/features.md — the feature tree the /features page renders.

    python3 scripts/check-features.py             # validate the living tree
    python3 scripts/check-features.py --self-test # 12 cases against synthetic trees

THIS SCRIPT OWNS THE GRAMMAR. `gen-features-page.py` imports `parse_features` from here rather than
re-implementing it. Two parsers for one grammar is the drift this repo has measured repeatedly, and
`check-dashboard-entry.py` already owns the entry-header grammar its page imports.
"""
import re, sys
from dataclasses import dataclass, field

STATUS_TOKENS = re.compile(
    r"(?:[✅🔴🟠🟢⏳◀]|#\d+|\b(?:currently|now|already|still|yet|planned|done|todo)\b|\bin progress\b)",
    re.IGNORECASE,
)

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
            print(f"  ✗ {name}\n      got  {got!r}\n      want {want!r}")

    TREE = """# Feature map
## PRODUCT
### summarise-a-video
state: built
for: Turns one video's transcript into a summary a person reads.
anchors: cloud-publishing

### rate-limiting-per-account
state: absent
expected-because: standard for a hosted multi-tenant service.
"""
    nodes, problems = parse_features(TREE)
    check("two nodes parsed", [n.slug for n in nodes], ["summarise-a-video", "rate-limiting-per-account"])
    check("trunk is carried down", nodes[0].trunk, "PRODUCT")
    check("state read", nodes[0].state, "built")
    check("anchors read", nodes[0].anchors, ["cloud-publishing"])
    check("absent reason read", nodes[1].expected_because, "standard for a hosted multi-tenant service.")
    check("clean tree has no problems", problems, [])
    check("clean tree passes the rules", check_nodes(nodes), [])

    built_empty = TREE.replace("anchors: cloud-publishing\n", "")
    check("a built node with no fragment fails",
          any("no fragment" in p for p in check_nodes(parse_features(built_empty)[0])), True)

    absent_with_fragment = TREE.replace(
        "expected-because: standard for a hosted multi-tenant service.\n",
        "expected-because: standard for a hosted multi-tenant service.\nanchors: cloud-publishing\n")
    check("an absent node WITH a fragment fails",
          any("flip it to `built`" in p for p in check_nodes(parse_features(absent_with_fragment)[0])), True)

    absent_no_reason = TREE.replace("expected-because: standard for a hosted multi-tenant service.\n", "")
    check("an absent node with no reason fails",
          any("expected-because" in p for p in check_nodes(parse_features(absent_no_reason)[0])), True)

    statusy = TREE.replace("for: Turns one", "for: Currently turns one")
    check("a status token in prose fails",
          any("status token" in p for p in check_nodes(parse_features(statusy)[0])), True)

    dupe = TREE + "\n### summarise-a-video\nstate: built\nfor: A second one.\nanchors: cloud-sync\n"
    check("a duplicate slug fails",
          any("duplicate" in p for p in check_nodes(parse_features(dupe)[0])), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/check-features.py --self-test`
Expected: `NameError: name 'parse_features' is not defined`

- [ ] **Step 3: Write the parser and the rules**

Insert above `_self_test`:

```python
FIELD = re.compile(r"^(state|for|areas|anchors|expected-because):\s*(.*)$")


def parse_features(text: str) -> tuple[list[Node], list[str]]:
    """Trunks are `## `, nodes are `### ` or deeper. Fields are `key: value` lines under a node."""
    nodes: list[Node] = []
    problems: list[str] = []
    trunk = ""
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if line.startswith("## ") and not line.startswith("###"):
            trunk = line[3:].strip()
            continue
        if line.startswith("###"):
            level = len(line) - len(line.lstrip("#"))
            slug = line.lstrip("#").strip()
            if not trunk:
                problems.append(f"features.md:{i}: node `{slug}` sits outside any trunk")
            nodes.append(Node(slug=slug, level=level, trunk=trunk, line=i))
            continue
        m = FIELD.match(line)
        if not m:
            continue
        if not nodes:
            problems.append(f"features.md:{i}: field `{m.group(1)}` before any node")
            continue
        key, value = m.group(1), m.group(2).strip()
        n = nodes[-1]
        if key == "state":
            n.state = value
        elif key == "for":
            n.purpose = value
        elif key == "expected-because":
            n.expected_because = value
        elif key == "areas":
            n.areas = [a.strip() for a in value.split(",") if a.strip()]
        elif key == "anchors":
            n.anchors = [a.strip() for a in value.split(",") if a.strip()]
    return nodes, problems


def check_nodes(nodes: list[Node]) -> list[str]:
    """Rules that need only features.md. Cross-file rules arrive in Task 3."""
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
                problems.append(
                    f"{where} prose contains the status token {hit.group(0)!r}. A node says what it "
                    f"is FOR; where it stands is what the links beneath it are for")

        fragments = len(n.areas) + len(n.anchors)
        if n.state == "built" and fragments == 0:
            problems.append(
                f"{where} is `built` but names no fragment — add an `anchors:` or `areas:` line, "
                f"or set `state: absent` with an `expected-because:`")
        if n.state == "absent":
            if not n.expected_because:
                problems.append(
                    f"{where} is `absent` but has no `expected-because:` line. An absence is only "
                    f"legal on the record, with an argument")
            if fragments:
                problems.append(
                    f"{where} is `absent` but names {fragments} fragment(s) — flip it to `built`")
    return problems
```

- [ ] **Step 4: Run the self-test to verify it passes**

Run: `python3 scripts/check-features.py --self-test`
Expected: `12/12 self-test cases passed`, exit 0.

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

Run: `python3 scripts/check-features.py`
Expected: exit 0 — but the `__main__` block only handles `--self-test` so far, so it exits 0 silently. That is correct for this task; Task 3 gives it a real main.

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

12/12 self-test cases pass.
```

---

## Task 2: The real tree, and anchors declaring their node

**Files:**
- Modify: `docs/features.md` (expand to the full tree)
- Modify: `docs/anchors.md` (add a `Feature` column to the registry table)

**Interfaces:**
- Consumes: `parse_features`, `check_nodes` from Task 1.
- Produces: a `docs/features.md` with all three trunks; `docs/anchors.md` rows carrying a feature slug in a new final column.

- [ ] **Step 1: Check whether the anchor parser is positional before touching the table**

Run: `grep -n "ANCHOR\|registry\|split(\"|\")\|cells" scripts/check-anchors.py | head -20`

⚠ If the registry table is read **positionally** (by cell index), adding a column at the end is safe; if it is read by header name, also safe; if it slices from the right (`cells[-2]`), adding a column **will break it** — this repo has a recorded defect where `cells[-2]` hit the wrong cell. Record which it is in the commit message.

- [ ] **Step 2: Add the `Feature` column to `docs/anchors.md`**

Append one column to the header, the separator, and all 13 rows. Example for the first row:

```markdown
| Anchor | ADR(s) | Goal | Feature |
|---|---|---|---|
| `cloud-publishing` | 0001, 0005 | Summaries are produced and published by a hosted service, not only by a local vault. | `summarise-a-video` |
```

Map each of the 13 anchors to a node slug you create in Step 3. Anchors that are platform properties or tooling map to nodes under PLATFORM or DEV INFRASTRUCTURE respectively.

- [ ] **Step 3: Write the full tree**

Expand `docs/features.md` to all three trunks. Every node needs `state:` and `for:`; `built` nodes need at least one `anchors:` or `areas:` entry. Use the API surface as the source for PRODUCT nodes:

Run: `find app/api -name route.ts | sort` — each route family is a candidate node (`playlists`, `videos`, `share`, `pdf`, `html-doc`, `quick-view`, `jobs`, `ingest`, folder routes).

Include at least one `absent` node, so the state is exercised by real data. A true one, measured this session:

```markdown
### dig-job-recovery
state: absent
expected-because: a dig job inherits the same worker exit-window race a summary does, but `listByPlaylist` filters `job_kind = 'summary'`, so the read-path recoverer cannot see it.
```

- [ ] **Step 4: Run both checks**

Run: `python3 scripts/check-features.py --self-test && python3 scripts/check-anchors.py`
Expected: `12/12 self-test cases passed`, and `anchors: 13 registered, all claimed`.

⚠ If `check-anchors.py` now fails, the table is read in a way the new column broke. Fix the parser, do not revert the column — and add a self-test case to `check-anchors.py` covering the column count.

- [ ] **Step 5: Commit**

```bash
git add docs/features.md docs/anchors.md
git commit -F /tmp/t2.txt
```

---

## Task 3: Cross-file rules — anchors resolve, and every backlog area is claimed exactly once

**Files:**
- Modify: `scripts/check-features.py`

**Interfaces:**
- Consumes: `Node`, `parse_features`, `check_nodes`.
- Produces: `backlog_areas(text: str) -> set[str]`; `check_cross(nodes, anchor_slugs, backlog_areas) -> list[str]`; a real `main()` returning 0/1/2.

- [ ] **Step 1: Write the failing tests**

Add to `_self_test`, and raise the docstring count from 12 to **18**:

```python
    ANCHORS = {"cloud-publishing", "cloud-sync"}
    AREAS = {"(product)", "(cloud)", "(worker)"}
    nodes, _ = parse_features(TREE)
    check("clean cross-check is silent", check_cross(nodes, ANCHORS, set()), [])

    bad_anchor, _ = parse_features(TREE.replace("cloud-publishing", "no-such-anchor"))
    check("an unknown anchor fails",
          any("no-such-anchor" in p for p in check_cross(bad_anchor, ANCHORS, set())), True)

    claimed, _ = parse_features(TREE.replace("anchors: cloud-publishing", "areas: (product)"))
    check("an area not used by any backlog row fails",
          any("no backlog row" in p for p in check_cross(claimed, ANCHORS, {"(cloud)"})), True)
    check("an in-use area claimed by nobody fails",
          any("claimed by no node" in p for p in check_cross(claimed, ANCHORS, {"(product)", "(cloud)"})), True)

    twice = TREE.replace("anchors: cloud-publishing", "areas: (product)") + \
        "\n### another\nstate: built\nfor: A second claimant.\nareas: (product)\n"
    twice_nodes, _ = parse_features(twice)
    check("an area claimed by TWO nodes fails",
          any("claimed by 2 nodes" in p for p in check_cross(twice_nodes, ANCHORS, {"(product)"})), True)

    check("backlog areas are read from the row's area cell",
          backlog_areas("| 1 | x | f | S | (worker) | open |"), {"(worker)"})
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-features.py --self-test`
Expected: `NameError: name 'check_cross' is not defined`

- [ ] **Step 3: Implement the cross-file rules and a real main**

```python
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
FEATURES = REPO / "docs" / "features.md"
ANCHORS_MD = REPO / "docs" / "anchors.md"
BACKLOG = REPO / "docs" / "backlog.md"


def backlog_areas(text: str) -> set[str]:
    """Every `(area)` tag in use. The area is the 3rd-from-last cell of a row with >=7 pipes."""
    out: set[str] = set()
    for line in text.split("\n"):
        if not line.startswith("| ") or line.count("|") < 7:
            continue
        cell = line.split("|")[-3].strip()
        if cell.startswith("(") and cell.endswith(")"):
            out.add(cell)
    return out


def check_cross(nodes, anchor_slugs: set[str], areas_in_use: set[str]) -> list[str]:
    problems: list[str] = []
    claims: dict[str, list[str]] = {}
    for n in nodes:
        for a in n.anchors:
            if a not in anchor_slugs:
                problems.append(
                    f"features.md:{n.line}: `{n.slug}` names anchor `{a}`, which is not in "
                    f"docs/anchors.md")
        for area in n.areas:
            claims.setdefault(area, []).append(n.slug)
            if area not in areas_in_use:
                problems.append(
                    f"features.md:{n.line}: `{n.slug}` claims area `{area}`, which no backlog row "
                    f"uses — a stale alias hides nothing and looks like coverage")
    for area, owners in claims.items():
        if len(owners) > 1:
            problems.append(f"area `{area}` is claimed by {len(owners)} nodes: {', '.join(owners)}")
    for area in sorted(areas_in_use - set(claims)):
        problems.append(
            f"backlog area `{area}` is claimed by no node — its rows cannot appear on the page")
    return problems


def _anchor_slugs(text: str) -> set[str]:
    return set(re.findall(r"^\|\s*`([a-z0-9-]+)`\s*\|", text, re.MULTILINE))


def main() -> int:
    for path in (FEATURES, ANCHORS_MD, BACKLOG):
        if not path.exists():
            print(f"CANNOT RUN — {path} is missing. Treat this as NOT RUN.", file=sys.stderr)
            return 2
    nodes, problems = parse_features(FEATURES.read_text())
    if not nodes:
        print("CANNOT RUN — docs/features.md declares no nodes. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2
    areas = backlog_areas(BACKLOG.read_text())
    if not areas:
        print("CANNOT RUN — no `(area)` tags parsed from docs/backlog.md. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2
    problems += check_nodes(nodes)
    problems += check_cross(nodes, _anchor_slugs(ANCHORS_MD.read_text()), areas)
    if problems:
        print(f"FAILED — {len(problems)} feature-map problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    built = sum(1 for n in nodes if n.state == "built")
    print(f"feature map: {len(nodes)} nodes ({built} built, {len(nodes) - built} declared absent), "
          f"{len(areas)} backlog areas all claimed")
    return 0
```

Change the entry point to:

```python
if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
```

- [ ] **Step 4: Run the self-test and the real check**

Run: `python3 scripts/check-features.py --self-test && python3 scripts/check-features.py`
Expected: `18/18 self-test cases passed`, then either a summary line or a list of unclaimed areas.

⚠ **The real run is expected to FAIL first**, listing every backlog area no node claims — that is the tool doing its job. Add `areas:` lines to `docs/features.md` until it passes. **`(cloud/money)` and `(cloud / money)` will both appear: claim both on the same node's `areas:` line**, which is the point of the design — the duplicate becomes visible side by side.

- [ ] **Step 5: Commit**

---

## Task 4: The page

**Files:**
- Create: `scripts/gen-features-page.py`
- Modify: `scripts/explainer-serve.py` (register the page)

**Interfaces:**
- Consumes: `parse_features`, `Node` — imported from `check_features` via `importlib` (the filename has a hyphen, so a plain `import` will not work).
- Produces: `~/explainers/features.html`; `render(nodes, fragments) -> str`.

- [ ] **Step 1: Write the failing test**

Create `scripts/gen-features-page.py` with a docstring declaring `--self-test  # 6 cases`, importing the parser, and these cases:

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

In `scripts/explainer-serve.py`, add to `PAGES` (near line 124) and `SOURCES` (near line 141):

```python
    "features": "gen-features-page.py",
```
```python
    "features": ["docs/features.md", "docs/anchors.md", "docs/backlog.md"],
```

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
    "name": "an unclaimed backlog area stops being reported",
    "file": "scripts/check-features.py",
    "edits": [["    for area in sorted(areas_in_use - set(claims)):\n", "    for area in []:\n"]],
    "expect": ["an in-use area claimed by nobody fails"]
  }
]
```

- [ ] **Step 3: Prove every mutation is killed, over a control proved green first**

```bash
python3 scripts/check-features.py --self-test        # CONTROL — must be green BEFORE mutating
python3 scripts/check-plan-code.py --mutate .        # applies the manifest; each must go red
```
Expected: 4/4 killed. ⚠ **A surviving mutation means the case passes for a reason other than the one it names** — this happened four times in PR #322. Fix the case, not the manifest.

- [ ] **Step 4: Confirm the ratchet contract is satisfied**

Run: `python3 scripts/check-ratchet-contract.py`
Expected: exit 0 — `check-features.py` has a `--self-test` (R1), a CI caller (R3), and a manifest (R4).

- [ ] **Step 5: Confirm the declared self-test count is verified**

Run: `python3 scripts/check-selftest-counts.py`
Expected: the docstring's `# 18 cases` matches what the suite prints. If it drifts, fix the docstring — the count has one home.

- [ ] **Step 6: Commit and open the PR**

Per `docs/dev-process.md` Phase 5: branch + PR, and **merging stays a human gate**. Use `--body-file`, never `--body`.

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Feature tree, three trunks | 2 |
| Anchors attach rather than form the spine | 2 (`Feature` column) |
| `built` / `absent` node states, both directions enforced | 1 |
| `expected-because:` required on absences | 1 |
| Prose bounded, status tokens rejected | 1 |
| `areas:` alias map, no per-row backlog edits | 3 |
| Every in-use area claimed exactly once | 3 |
| Anchors resolve to the registry | 3 |
| `backlog.md` unparseable → exit 2 | 3 |
| Page at `/features`, derived | 4 |
| Rebuild hook | 5 |
| CI-wired check with `--self-test` and mutations | 6 |
| Absence count shown on the page | 4 |
| Tests/code modules excluded as fragments | — by omission; no task adds them |
| `/goals` not retired | — by omission; no task touches it |

**Placeholder scan:** none — every code step carries runnable code; the one open-ended step (Task 2's tree contents) names its source (`find app/api -name route.ts`) and a concrete measured example.

**Type consistency:** `parse_features` returns `(list[Node], list[str])` in Tasks 1, 3 and 4. `check_nodes(nodes)` and `check_cross(nodes, anchor_slugs, areas_in_use)` take the same `Node` dataclass throughout. `backlog_areas(text) -> set[str]` feeds `check_cross`'s third parameter in both the self-test and `main()`. The self-test count rises 12 → 18 in Task 3 and is verified by `check-selftest-counts.py` in Task 6.

**One risk called out rather than hidden:** Task 2 modifies `docs/anchors.md`'s table, and this repo has a recorded defect where a positional read (`cells[-2]`) hit the wrong cell after a column moved. Task 2 Step 1 checks the parser *before* the edit, and Step 4 re-runs `check-anchors.py` after it.

#!/usr/bin/env python3
"""Validate docs/features.md — the feature tree the /features page renders.

    python3 scripts/check-features.py             # validate the living tree
    python3 scripts/check-features.py --self-test # 100 cases against synthetic trees
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
# ⟳ goal node tree, Task 1 (spec §2.2): `adrs`, `was`, `done`, `proposed` and `slug` added. `slug`
# is a field ONLY directly under a `## ` trunk, where it makes the trunk a node (plan choice C2).
# ⟳ goal node tree, Task 7: `anchors` LEFT the grammar with the registry it named (ADR-0016). A
# document names its node by slug in its own `Anchor:` header; an ADR sits on the node's `adrs:` line.
FIELD_NAMES = ("state", "for", "areas", "expected-because", "adrs", "was", "done", "proposed", "slug")
# The retired field, refused BY NAME so the message can say what replaced it — the generic
# "neither a field nor a heading" message would list the grammar and leave the author guessing.
RETIRED_FIELDS = {"anchors": "an ADR goes on the node's own `adrs:` line, and a spec or plan names "
                             "the node by its slug in its `> **Anchor:**` header"}
# ⚠ ONE OWNER, because this fact is read in two places that must not disagree: the comma-split in
# `parse_features` and the duplicate-field REMEDY. Code review r3 (Codex) caught the message
# telling an author to write `state: built, absent` — advice that is right for a list field and
# produces a second, different error for a scalar one. An instruction that does not work costs
# the author a round to discover.
LIST_FIELDS = ("areas", "adrs", "was")
FIELD = re.compile(rf"^({'|'.join(FIELD_NAMES)}):\s*(.*)$")
# `adrs:` and `was:` are BARE comma lists (plan choice C1), read into tuples; each entry is checked
# against its own shape, so `adrs: (0001, 0005)` is refused entry by entry — parentheses belong to the
# `(area)` tag of `areas:`, never to a list grammar.
# ⛔ ONE SLUG GRAMMAR (spec §2.2: "lowercase words joined by `-`"), read by `was:` entries AND by every
# CURRENT slug in `check_nodes` (S1 r1, Codex High 2 = Claude F2) — a current name is never held to a
# weaker grammar than a former one, or it could not be renamed later.
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENTRY_SHAPE = {"adrs": (re.compile(r"^\d{4}$"), "four digits, e.g. `0005`"),
               "was": (SLUG, "a slug: lowercase words joined by `-`")}
TUPLE_FIELDS = ("adrs", "was")
# `done:` is the owner's recorded decision, dated like a request (spec §2.2, G9); `proposed:` the moment
# a name was proposed (spec §2.7). Both single-line.
DONE_FORM = 'done: YYYY-MM-DD HH:MM "<the owner\'s words>"'
DONE_FIELD = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) "(.+)"$')
PROPOSED_FIELD = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

@dataclass
class Node:
    slug: str
    level: int
    trunk: str
    state: str | None = None
    purpose: str = ""
    areas: list[str] = field(default_factory=list)
    expected_because: str | None = None
    line: int = 0
    parent: str | None = None
    adrs: tuple[str, ...] = ()
    was: tuple[str, ...] = ()
    done: tuple[str, str] | None = None
    proposed: str | None = None


def parse_features(text: str) -> tuple[list[Node], list[str]]:
    nodes: list[Node] = []
    problems: list[str] = []
    trunk = ""
    seen_fields: set[str] = set()
    # The open branch of the current trunk, shallowest first: a node's parent is the nearest entry of a
    # SMALLER level (spec §2.2; the trunk's own node, level 2, when the trunk carries a slug).
    branch: list[Node] = []
    # True from a `## ` heading until its first non-blank line: the one place a `slug:` line is taken.
    under_trunk = False
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if line.startswith("## ") and not line.startswith("###"):
            trunk = line[3:].strip(); branch = []; under_trunk = True; continue
        if line.startswith("###"):
            under_trunk = False
            level = len(line) - len(line.lstrip("#"))
            slug = line.lstrip("#").strip()
            if not trunk:
                problems.append(f"features.md:{i}: node `{slug}` sits outside any trunk")
            if level > 6:
                problems.append(f"features.md:{i}: node `{slug}` is {level} levels deep — a node "
                                f"heading is `###` to `######`")
            # ⛔ A SKIPPED LEVEL IS REFUSED (plan choice C3): `#####` directly under `###` would make
            # the deeper node a grandchild of nothing. A first node deeper than `###` under a SLUGLESS
            # trunk has no preceding node to skip from, and stays a top-level entry (today's rule).
            if branch and level > branch[-1].level + 1:
                problems.append(f"features.md:{i}: node `{slug}` (level {level}) skips a level under "
                                f"`{branch[-1].slug}` (level {branch[-1].level}) — each heading is one "
                                f"`#` deeper than its parent's")
            while branch and branch[-1].level >= level:
                branch.pop()
            node = Node(slug=slug, level=level, trunk=trunk, line=i,
                        parent=branch[-1].slug if branch else None)
            nodes.append(node); branch.append(node)
            seen_fields = set(); continue
        m = FIELD.match(line)
        if m and m.group(1) == "slug":
            taken, under_trunk = bool(under_trunk and trunk), False
            if not taken:
                problems.append(f"features.md:{i}: a `slug:` line here is refused — only a trunk takes "
                                f"a slug line, written directly under its `## ` heading")
                continue
            node = Node(slug=m.group(2).strip(), level=2, trunk=trunk, line=i)
            nodes.append(node); branch = [node]
            seen_fields = set(); continue
        if line.strip():
            under_trunk = False
        retired = line.split(":", 1)[0] if not m and ":" in line else None
        if retired in RETIRED_FIELDS:
            problems.append(f"features.md:{i}: `{retired}:` is no longer a field — "
                            f"{RETIRED_FIELDS[retired]} (goal node tree, ADR-0016)")
            continue
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
        # five assignments below used to be unconditional, so a second `areas:` blanked the first
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
        elif key == "done":
            dm = DONE_FIELD.match(value)
            if dm:
                n.done = (dm.group(1), dm.group(2))
            else:
                problems.append(f"features.md:{i}: `{n.slug}` has a malformed `done:` line — the form is "
                                f"`{DONE_FORM}`: a date, a time, and the owner's words in double quotes")
        elif key == "proposed":
            if PROPOSED_FIELD.match(value):
                n.proposed = value
            else:
                problems.append(f"features.md:{i}: `{n.slug}` has a malformed `proposed:` line — the "
                                f"form is `proposed: YYYY-MM-DD HH:MM`")
        elif key in TUPLE_FIELDS:
            entries = [a.strip() for a in value.split(",") if a.strip()]
            pattern, shape = ENTRY_SHAPE[key]
            for e in entries:
                if not pattern.match(e):
                    problems.append(f"features.md:{i}: `{n.slug}` has the `{key}:` entry `{e}`, which is "
                                    f"not {shape}. `{key}:` is a bare comma list, with no parentheses")
            setattr(n, key, tuple(e for e in entries if pattern.match(e)))
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


def check_nodes(nodes: list[Node], anchored: frozenset[str] = frozenset()) -> list[str]:
    """The per-node rules. `anchored` is the set of slugs some document's `Anchor:` header names —
    `main` passes `check-anchors.anchored_slugs`, the ONE header reader (plan choice C10). Uniqueness
    is `slug_problems` (G6), not this function."""
    problems: list[str] = []
    for n in nodes:
        where = f"features.md:{n.line}: `{n.slug}`"
        if not SLUG.match(n.slug):
            problems.append(f"{where} is not a slug — a node's name (its heading text, or a trunk's `slug:` "
                            f"value) is lowercase words joined by `-`, the grammar a `was:` entry is held to")
        # `state:` is OPTIONAL (spec §2.2): omitted means the node is a name only — an aim.
        if n.state not in (None, "built", "absent"):
            problems.append(f"{where} has state {n.state!r}; expected `built`, `absent`, or no `state:` line")
        if not n.purpose:
            problems.append(f"{where} has no `for:` line — every node says what it is for")
        else:
            hit = STATUS_TOKENS.search(n.purpose)
            if hit:
                problems.append(f"{where} prose contains the status token {hit.group(0)!r}. A node "
                                f"says what it is FOR; where it stands is what the links are for")
        # ⛔ THE TWO COUNTS ARE DIFFERENT SETS (plan Task 2, r1 F2). Any of these is evidence a
        # `built` node exists; only an AREA — a backlog row, shipped work — contradicts an absence.
        # An ADR or a document describes a gap and may sit under an `absent` node.
        fragments = len(n.areas) + len(n.adrs) + (n.slug in anchored)
        if n.state == "built" and fragments == 0:
            problems.append(f"{where} is `built` but names no fragment — add an `areas:` or `adrs:` "
                            f"line, name it in a spec's or plan's `Anchor:` header, or set `state: "
                            f"absent` with an `expected-because:`")
        # ⛔ ONE RULE FOR WHERE `expected-because:` MAY SIT: on an `absent` node, and nowhere else.
        # It was two refusals, one per state (`built`, then stateless in S1 r1, Claude F3 — the line
        # is never rendered off an `absent` node, so it would sit unseen), and the copies were each
        # written as a TRUTHINESS test, so a bare `expected-because:` (parsed to "") passed both
        # (S1 r2, Codex Low). One rule over PRESENCE (`is not None`) leaves no per-state copy to
        # forget, and no value that reads as the field being absent.
        if n.expected_because is not None and n.state != "absent":
            held = f"is `{n.state}`" if n.state is not None else "has no `state:`"
            problems.append(f"{where} {held} but carries an `expected-because:` — that line is "
                            f"the argument for an ABSENCE. Remove it, or set `state: absent`")
        if n.state == "absent":
            if not n.expected_because:
                problems.append(f"{where} is `absent` but has no `expected-because:` line")
            if n.areas:
                problems.append(f"{where} is `absent` but claims {len(n.areas)} area(s) — flip it to `built`")
    return problems


def current_slugs(nodes: list[Node]) -> set[str]:
    return {n.slug for n in nodes}


def resolve(nodes: list[Node], slug: str) -> str | None:
    """The CURRENT slug for a current or former slug, else None. ⛔ For READING history only (spec
    §2.4): a check of a NEW value asks "is this a current slug", never "does this resolve"."""
    for n in nodes:
        if slug == n.slug or slug in n.was:
            return n.slug
    return None


def slug_problems(nodes: list[Node]) -> list[str]:
    """G6: a slug occurs once across every current slug and every `was:` entry, and no two nodes'
    page ids can meet. A `was:` entry that occurs once and is no current slug is a rename — PASSES."""
    problems: list[str] = []
    first: dict[str, Node] = {}
    for n in nodes:
        if n.slug in first:
            problems.append(f"features.md:{n.line}: `{n.slug}` is a duplicate of the node on line "
                            f"{first[n.slug].line} — two nodes share one slug")
        else:
            first[n.slug] = n
    current = set(first)
    former: dict[str, list[Node]] = {}
    for n in nodes:
        for w in n.was:
            former.setdefault(w, []).append(n)
            if w in current:
                problems.append(f"features.md:{n.line}: `{n.slug}` lists `{w}` in `was:`, which is also a "
                                f"current slug (line {first[w].line}) — a retired name is never re-allocated")
    for w, owners in former.items():
        if len(owners) > 1:
            problems.append(f"`{w}` is listed as a former slug {len(owners)} times, by: "
                            f"{', '.join(f'`{o.slug}` (line {o.line})' for o in owners)} — one rename, one record")
    # ⛔ PAGE IDS MAY NOT MEET (plan Task 2, r2 Codex Major). The views give a slug `s` the ids
    # `goal-s`, `s`, `f-s`, `g-s` and `goal-<w>` per former slug `w`; two nodes can share one only as
    # these PAIRS. A PREFIX ban is wrong: the live node `goal-tree` has no partner.
    for n in nodes:
        if n.slug.startswith("f-") and n.slug[2:] in current:
            problems.append(f"features.md:{n.line}: `{n.slug}` equals the f- id of the node `{n.slug[2:]}` "
                            f"(line {first[n.slug[2:]].line}) — on /features the two would share an id")
        if n.slug.startswith("goal-") and n.slug[5:] in current:
            problems.append(f"features.md:{n.line}: `{n.slug}` equals the goal- id of the node "
                            f"`{n.slug[5:]}` (line {first[n.slug[5:]].line}) — the two would share an id")
        if n.slug.startswith("goal-") and n.slug[5:] in former:
            problems.append(f"features.md:{n.line}: `{n.slug}` equals the goal- id of the former slug "
                            f"`{n.slug[5:]}` (`was:` of `{former[n.slug[5:]][0].slug}`) — its old links "
                            f"would land on the wrong node")
    return problems


def adr_problems(nodes: list[Node], known: set[str]) -> list[str]:
    """Every `adrs:` number is the number of a file under `docs/adr/` (goal node tree Task 5). `known`
    is the set of four-digit numbers those files carry; the shape of an entry is `parse_features`'."""
    return [f"features.md:{n.line}: `{n.slug}` names ADR {a} in `adrs:`, but docs/adr/ holds no "
            f"`{a}-*.md` — a node may cite only a decision that is recorded"
            for n in nodes for a in n.adrs if a not in known]


def adr_numbers(adr_dir: pathlib.Path) -> set[str]:
    """The four-digit numbers of the ADR files in `adr_dir` (`NNNN-<title>.md`)."""
    return {p.name[:4] for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")}


def summary_line(nodes: list[Node]) -> str:
    """The node half of `main`'s OK line. A stateless node is a name only — never counted absent."""
    built = sum(1 for n in nodes if n.state == "built")
    absent = sum(1 for n in nodes if n.state == "absent")
    return f"{len(nodes)} nodes ({built} built, {absent} absent, {len(nodes) - built - absent} stateless)"


# ⛔ THE REQUEST GRAMMAR LIVES HERE, ONCE (goal node tree Task 3). `goal-tree.py`'s `GOAL_RE` and
# `REQUEST_RE` are aliases of these two, read through its `_sibling`, never a second copy.
GOAL_HEADING = re.compile(r"^## GOAL ([a-z0-9]+(?:-[a-z0-9]+)*)$")
REQUEST = re.compile(r'^> (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) "(.+)"$')


def requests_by_goal(text: str) -> dict[str, list[tuple[str, str]]]:
    """`docs/goal-threads.md`'s request lines, by the slug of the `## GOAL` heading they sit under, in
    file order. Any other `## ` heading ends a goal. Validating that file is `goal-tree.py`'s job."""
    out: dict[str, list[tuple[str, str]]] = {}
    cur = None
    for raw in text.split("\n"):
        line = raw.rstrip()
        if line.startswith("## "):
            m = GOAL_HEADING.match(line)
            cur = m.group(1) if m else None
            if cur is not None:
                out.setdefault(cur, [])
            continue
        m = REQUEST.match(line) if cur is not None else None
        if m:
            out[cur].append((m.group(1), m.group(2)))
    return out


def done_problems(nodes: list[Node], requests) -> list[str]:
    """G9: a `done:` line's (when, words) equals a request under a `## GOAL` heading whose slug
    `resolve`s to that node — so a request filed under a former slug still counts.

    `requests` is a zero-argument READER returning `requests_by_goal(...)`. ⛔ It is called only when
    some node carries `done:` (r1 F5): `gen-features-page.py` loads this module, and its worlds have no
    threads file. A reader that cannot read raises; `main` turns that into CANNOT RUN."""
    if not any(n.done for n in nodes):
        return []
    table = requests()
    problems: list[str] = []
    for n in nodes:
        if n.done is None:
            continue
        when, words = n.done
        cited = [r for heading, rs in table.items() if resolve(nodes, heading) == n.slug for r in rs]
        if not any(r[0] == when and r[1] == words for r in cited):
            problems.append(f"features.md:{n.line}: `{n.slug}` is marked done at {when} citing \"{words}\", "
                            f"but docs/goal-threads.md records no such request under a `## GOAL` heading "
                            f"naming this node — copy the request line exactly, time and words")
    return problems


_TAGS = None
_ANCHORS = None


def anchors_module():
    """`check-anchors`, which OWNS the `Anchor:` header reader (`anchored_slugs`) — loaded lazily and
    once, like `tags`. It loads this file in turn; the two are separate module objects, so the cycle
    is a second read of this file, not an import loop."""
    global _ANCHORS
    if _ANCHORS is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_anchors", pathlib.Path(__file__).with_name("check-anchors.py"))
        _ANCHORS = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ANCHORS)
    return _ANCHORS


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


def kind_problems(text: str, slugs: set[str]) -> list[str]:
    """backlog #394: a parent link naming a missing row or an `epic:` that is no current node slug
    (`slugs`) FAILS this gate; a
    row with no kind is a WARNING printed here (reported, never guessed, never a failure). ⚠ The kind
    is read by `gen-backlog-page.kind_mark` and is NEVER an area: the Bundle cell alone holds tags.
    An unknown kind is a `ShapeError` from the parser, which `backlog_areas` already reports."""
    bp = tags()
    try:
        rows = bp.parse(text.split("\n"))
    except bp.ShapeError:
        return []                       # reported once, by `backlog_areas`
    for note in bp.missing_kind_notes(rows):
        print(f"  ⚠ {note}", file=sys.stderr)
    return [f"backlog.md {e}" for e in bp.parent_errors(rows, slugs)]


def check_cross(nodes, areas_in_use: set[str] | None) -> list[str]:
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
    for n in nodes:
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
    for area in sorted(u for u in (areas_in_use or ()) if nearest(u, area_claims) is None):
        problems.append(f"backlog area `{area}` is claimed by no node — its rows cannot appear")
    return problems


REPO = pathlib.Path(__file__).resolve().parent.parent
FEATURES = REPO / "docs" / "features.md"
# Where the `Anchor:` headers are read — `check-anchors.anchored_slugs` walks its specs, plans and ADRs.
DOCS_DIR = REPO / "docs"
BACKLOG = REPO / "docs" / "backlog.md"
GOAL_THREADS = REPO / "docs" / "goal-threads.md"
ADR_DIR = REPO / "docs" / "adr"


def main() -> int:
    for path in (FEATURES, BACKLOG):
        if not path.exists():
            print(f"CANNOT RUN — {path} is missing. Treat this as NOT RUN.", file=sys.stderr)
            return 2
    nodes, problems = parse_features(FEATURES.read_text())
    if not nodes:
        print("CANNOT RUN — docs/features.md declares no nodes. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    areas, area_problems = backlog_areas(BACKLOG.read_text())
    if not areas and not area_problems:
        print("CANNOT RUN — no `(area)` tags parsed from docs/backlog.md. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    problems += area_problems
    problems += kind_problems(BACKLOG.read_text(), current_slugs(nodes))
    # ⛔ THE LIVE SET, read by the one header reader (plan C10): a `built` node whose only fragment is
    # a spec or plan naming it passes here, and fails once that document is gone.
    problems += check_nodes(nodes, frozenset(anchors_module().anchored_slugs(DOCS_DIR)))
    problems += slug_problems(nodes)
    known_adrs = adr_numbers(ADR_DIR)
    if any(n.adrs for n in nodes) and not known_adrs:
        print(f"CANNOT RUN — a node carries `adrs:` and {ADR_DIR} holds no `NNNN-*.md` file, so no "
              f"ADR number can be checked. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    problems += adr_problems(nodes, known_adrs)
    problems += check_cross(nodes, None if not areas else areas)
    try:
        # The threads file is read only when a node carries `done:` — the guard is `done_problems`'.
        problems += done_problems(nodes, lambda: read_threads(GOAL_THREADS))
    except ThreadsUnreadable as e:
        print(f"CANNOT RUN — a node carries `done:` and {GOAL_THREADS} {e}, "
              f"so G9 cannot be checked. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    if problems:
        print(f"FAILED — {len(problems)} feature-map problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    print(f"feature map: {summary_line(nodes)}; "
          f"{len(areas)} backlog areas all claimed exactly once")
    return 0


class ThreadsUnreadable(Exception):
    """`docs/goal-threads.md` gave nothing G9 can compare against — CANNOT RUN, never FAILED."""


def read_threads(path: pathlib.Path) -> dict[str, list[tuple[str, str]]]:
    """`requests_by_goal` over the threads file, or `ThreadsUnreadable` when it cannot be read, is not
    UTF-8 (S1 r1, Codex Medium 3), or holds no `## GOAL` heading (S1 r1, Claude F4: a parse that found
    nothing must not accuse a `done:` line of citing a request that is in fact recorded)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ThreadsUnreadable(f"cannot be read ({type(e).__name__})") from e
    table = requests_by_goal(text)
    if not table:
        raise ThreadsUnreadable("holds no `## GOAL` heading, so a parse of it found nothing")
    return table


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
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
adrs: 0010

### rate-limiting-per-account
state: absent
for: Stops one account exhausting the shared spend cap.
expected-because: standard for a hosted multi-tenant service.
"""
    nodes, problems = parse_features(TREE)
    check("two nodes parsed", [n.slug for n in nodes], ["summarise-a-video", "rate-limiting-per-account"])
    check("trunk is carried down", nodes[0].trunk, "PRODUCT")
    check("state read", nodes[0].state, "built")
    check("adrs read", nodes[0].adrs, ("0010",))
    check("absent reason read", nodes[1].expected_because, "standard for a hosted multi-tenant service.")
    check("absent node still says what it is for", nodes[1].purpose, "Stops one account exhausting the shared spend cap.")
    check("clean tree has no problems", problems, [])
    check("clean tree passes the rules", check_nodes(nodes), [])
    built_empty = TREE.replace("adrs: 0010\n", "")
    check("a built node with no fragment fails",
          any("no fragment" in p for p in check_nodes(parse_features(built_empty)[0])), True)
    # ⟳ goal node tree Task 2: the `absent` arm counts AREAS only (an ADR or a document may describe a
    # gap), so the fragment that contradicts an absence is an `areas:` line.
    absent_frag = TREE.replace("expected-because: standard for a hosted multi-tenant service.\n",
                               "expected-because: standard for a hosted multi-tenant service.\nareas: (product)\n")
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
    dupe = TREE + "\n### summarise-a-video\nstate: built\nfor: A second one.\nareas: (sync)\n"
    # ⟳ goal node tree Task 2: uniqueness moved from `check_nodes` to `slug_problems` (G6).
    check("a duplicate slug fails",
          any("duplicate" in p for p in slug_problems(parse_features(dupe)[0])), True)
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
    # `areas:` blanks it. The second case is the half that matters — refusing the duplicate is
    # worth nothing if the value that survives is still the empty one.
    ABSENT_WHY = "expected-because: standard for a hosted multi-tenant service.\n"
    dup_areas = TREE.replace(ABSENT_WHY, ABSENT_WHY + "areas: (product)\nareas:\n")
    dnodes, dproblems = parse_features(dup_areas)
    check("a duplicate field is REFUSED, not applied last-write-wins",
          any("repeats the field `areas`" in p for p in dproblems), True)
    check("the FIRST value stands, so a blanking duplicate cannot hide the fragment it contradicts",
          any("flip it to `built`" in p for p in check_nodes(dnodes)), True)
    check("`now` is no longer a banned word", STATUS_TOKENS.search("Shows what runs now") is None, True)
    check("clean cross-check is silent", check_cross(nodes, set()), [])
    # ⟳ goal node tree Task 7: the three anchor rules left with `anchors:`; the area rules stand.
    check("cross: areas are still claimed exactly once",
          [[p for p in check_cross(parse_features(TREE.replace("adrs: 0010", f"areas: {a}"))[0], {"product"})
            if "claimed" in p] for a in ("(product)", "(product), (Product)")],
          [[], ["area `product` is claimed 2 times, by: summarise-a-video, summarise-a-video — two "
                "spellings of one tag are one tag; keep a single entry"]])
    areas_tree, _ = parse_features(TREE.replace("adrs: 0010", "areas: (product)"))
    check("an area no backlog row uses fails",
          any("no backlog row uses" in p
              for p in check_cross(areas_tree, {"cloud"})), True)
    check("an in-use area claimed by nobody fails",
          any("claimed by no node" in p and "`cloud`" in p
              for p in check_cross(areas_tree, {"product", "cloud"})), True)
    twice_area = (TREE.replace("adrs: 0010", "areas: (product)")
                  + "\n### another\nstate: built\nfor: A second claimant.\nareas: (product)\n")
    check("an area claimed by TWO nodes fails",
          any("area `product` is claimed 2 times" in p
              for p in check_cross(parse_features(twice_area)[0], {"product"})), True)
    def _bl(*rows: str) -> str:
        return ("## Items\n| # | Item | Touches | Size | Bundle | Status |\n|---|---|---|---|---|---|\n"
                + "\n".join(rows) + "\n")
    check("backlog areas are read from the area cell",
          backlog_areas(_bl("| 1 | x | f | S | (worker) | open |")), ({"worker"}, []))
    ESCAPED = r"| 90 | a \| b | f | S | (comprehensibility) | open \| still |"
    check("a row with an ESCAPED PIPE is not dropped", backlog_areas(_bl(ESCAPED)), ({"comprehensibility"}, []))
    # backlog #394: the kind marker ends the ITEM cell; it is never read as an area.
    check("#394: a kind marker is not an area — only the Bundle cell is",
          backlog_areas(_bl("| 1 | x ⟦kind: task · epic: feature-map⟧ | f | S | (worker) | open |")),
          ({"worker"}, []))
    check("⛔ #394: an unknown kind FAILS the gate, through the parser",
          bool(backlog_areas(_bl("| 1 | x ⟦kind: decision⟧ | f | S | (worker) | open |"))[1]), True)
    import contextlib as _cl, io as _io
    with _cl.redirect_stderr(_io.StringIO()) as _warn:
        _kp = kind_problems(_bl("| 1 | x ⟦kind: task · part of: backlog #9 · epic: nope⟧ | f | S | (w) | o |\n"
                                "| 2 | y | f | S | (w) | o |"), {"feature-map"})
    check("⛔ #394: a parent naming a missing row or an unregistered anchor FAILS the gate",
          _kp, ["backlog.md row 1: `part of: backlog #9` names a row that does not exist",
                "backlog.md row 1: `epic: nope` is not a node in docs/features.md"])
    check("#394: a row with NO kind is a WARNING, not a failure", "row 2 declares no kind" in _warn.getvalue(), True)
    with _cl.redirect_stderr(_io.StringIO()) as _quiet:
        _ok = kind_problems(_bl("| 3 | x ⟦kind: story · epic: feature-map⟧ | f | S | (w) | o |",
                                "| 4 | y ⟦kind: defect · part of: backlog #3⟧ | f | S | (w) | o |"), {"feature-map", "cloud-sync"})
    check("#394: valid kinds and parents raise nothing and warn nothing", (_ok, _quiet.getvalue()), ([], ""))
    # ── PER TAG, NORMALISED (backlog #381) ───────────────────────────────────────────────────────
    check("a cell with two tags puts BOTH in use",
          backlog_areas(_bl("| 1 | x | f | S | (tooling) (cloud / Money) | open |")),
          ({"tooling", "cloud / money"}, []))
    _mal = backlog_areas(_bl("| 2 | x | f | S | cloud | open |"))
    check("a malformed cell is REPORTED with its row, and its one guessed tag is still in use",
          (_mal[0], len(_mal[1]), "row 2" in " ".join(_mal[1]) and "'cloud'" in " ".join(_mal[1])),
          ({"cloud"}, 1, True))
    _empty = backlog_areas(_bl("| 6 | x | f | S | () | open |"))
    check("an EMPTY tag group `()` FAILS the gate, naming its row",
          (len(_empty[1]), "row 6" in " ".join(_empty[1])), (1, True))
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
    spelled = parse_features(TREE.replace("adrs: 0010",
                                          "areas: (cloud/money), (cloud / money)"))[0]
    check("two spellings of one tag on ONE node are a duplicate claim, not two areas",
          any("area `cloud / money` is claimed 2 times" in p
              for p in check_cross(spelled, {"cloud / money"})), True)
    fam = parse_features(TREE.replace("adrs: 0010", "areas: (cloud)"))[0]
    check("an in-use leaf is claimed by its family's area, and that area is not stale",
          check_cross(fam, {"cloud / new"}), [])
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
    both = parse_features(TREE.replace("adrs: 0010", "areas: (cloud), (cloud/money)"))[0]
    check("a family area that is nobody's NEAREST claimant is stale",
          [p for p in check_cross(both, {"cloud / money"}) if "no backlog row uses" in p and "`(cloud)`" in p] != []
          and not any("`(cloud/money)`" in p for p in check_cross(both, {"cloud / money"})), True)
    check("an UNREADABLE backlog (areas None) asks no per-area question, so the one real cause is not buried",
          tuple(sum("no backlog row uses" in p for p in check_cross(both, a)) for a in (None, set())),
          (0, 2))
    check("a tag that merely SHARES a prefix is not in the family",
          any("claimed by no node" in p for p in check_cross(fam, {"cloudy"})), True)
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
          "ONE comma-separated line" in _dup("areas", "(a)", "(b)"), True)
    _ret = [p for p in parse_features("# Feature map\n## PRODUCT\n### x\nfor: A thing.\nanchors: x\n")[1]]
    check("anchors: is no longer a field",
          ([("`anchors:` is no longer a field" in p, "`adrs:`" in p, "`> **Anchor:**`" in p) for p in _ret],
           [p for p in parse_features("# Feature map\n## PRODUCT\n### x\nfor: A thing.\nareas: (x)\n")[1]]),
          ([(True, True, True)], []))
    check("a refused line states the GRAMMAR an author needs, not only the rationale",
          all(s in parse_features("# Feature map\n## PRODUCT\n### x\n state: built\n")[1][0]
              for s in ("COLUMN 0", "no space before the colon", "expected-because")), True)

    # ── THE NODE GRAMMAR — goal node tree, Task 1 (spec §2.2) ───────────────────────────────────
    def _one(body: str, trunk: str = "## PRODUCT\n") -> tuple[list[Node], list[str]]:
        return parse_features("# Feature map\n" + trunk + body)

    _lists = [_one(f"### x\nfor: A thing.\nadrs: {a}\nwas: {w}\n") for a, w in
              (("0001, 0005", "a, b"), ("0012", "c"))]
    check("grammar: adrs and was are bare comma lists",
          [(ns[0].adrs, ns[0].was, ps) for ns, ps in _lists],
          [(("0001", "0005"), ("a", "b"), []), (("0012",), ("c",), [])])
    _bad_adrs = ("1", "(0001", "0005)", "00012", "abcd")
    check("grammar: adrs entry must be four digits",
          [any("features.md:5" in p and f"`{b}`" in p for p in _one(f"### x\nfor: A thing.\nadrs: 0003, {b}\n")[1])
           for b in _bad_adrs] + [_one("### x\nfor: A thing.\nadrs: 0003, 0004\n")[1] == []],
          [True] * len(_bad_adrs) + [True])
    _ns, _ps = _one("### x\nfor: A thing.\n")
    check("grammar: state may be omitted", (_ns[0].state, _ps), (None, []))
    check("grammar: done parses when and words",
          [_one(f'### x\nfor: A thing.\ndone: {d}\n')[0][0].done for d in
           ('2026-11-23 21:20 "it is finished"', '2025-01-02 03:04 "another, longer sentence."')],
          [("2026-11-23 21:20", "it is finished"), ("2025-01-02 03:04", "another, longer sentence.")])
    _bad_done = ('2026-11-23 "it is finished"', '2026-11-23 21:20 it is finished', '2026-11-23 21:20',
                 '21:20 "it is finished"', '2026-11-23 2120 "it is finished"')
    check("grammar: done needs a time and a quote",
          [(_one(f"### x\nfor: A thing.\ndone: {d}\n")[0][0].done,
            any('YYYY-MM-DD HH:MM "' in p for p in _one(f"### x\nfor: A thing.\ndone: {d}\n")[1]))
           for d in _bad_done],
          [(None, True)] * len(_bad_done))
    check("grammar: proposed parses",
          [_one(f"### x\nfor: A thing.\nproposed: {p}\n")[0][0].proposed for p in ("2026-11-24 09:30", "2024-02-29 23:59")]
          + [bool(_one("### x\nfor: A thing.\nproposed: 2026-11-24\n")[1])],
          ["2026-11-24 09:30", "2024-02-29 23:59", True])
    _deep, _dp = _one("### a\nfor: A.\n#### b\nfor: B.\n##### c\nfor: C.\n###### d\nfor: D.\n"
                      "### e\nfor: E.\n#### f\nfor: F.\n##### g\nfor: G.\n")
    check("grammar: depth five and six carry a parent",
          ([(n.slug, n.level, n.parent) for n in _deep], _dp),
          ([("a", 3, None), ("b", 4, "a"), ("c", 5, "b"), ("d", 6, "c"),
            ("e", 3, None), ("f", 4, "e"), ("g", 5, "f")], []))
    check("grammar: a skipped level is refused",
          [any("`a`" in p and "`b`" in p and "skips" in p for p in _one(src)[1]) for src in
           ("### a\nfor: A.\n##### b\nfor: B.\n", "### z\nfor: Z.\n#### a\nfor: A.\n###### b\nfor: B.\n")],
          [True, True])
    _tr, _tp = parse_features("# Feature map\n## PRODUCT\n\nslug: product\nfor: What the product does.\n"
                              "### c\nfor: C.\n#### d\nfor: D.\n"
                              "## PLATFORM\nslug: platform\nfor: What it runs on.\n### e\nfor: E.\n")
    check("grammar: a trunk slug makes a level-2 node",
          ([(n.slug, n.level, n.trunk, n.parent) for n in _tr], _tp),
          ([("product", 2, "PRODUCT", None), ("c", 3, "PRODUCT", "product"), ("d", 4, "PRODUCT", "c"),
            ("platform", 2, "PLATFORM", None), ("e", 3, "PLATFORM", "platform")], []))
    _live_text = FEATURES.read_text()
    _live, _lp = parse_features(_live_text)
    _headings = [l for l in _live_text.split("\n") if re.match(r"^#{3,6} ", l)]
    check("grammar: a slugless trunk yields no node",
          (len(_live), [n for n in _live if n.level == 2], [n.slug for n in _live if n.level == 3 and n.parent],
           len(_one("### a\nfor: A.\n#### b\nfor: B.\n")[0]), _one("### a\nfor: A.\n#### b\nfor: B.\n")[0][0].parent),
          (len(_headings), [], [], 2, None))
    check("grammar: slug under a node is refused",
          [any("only a trunk" in p for p in parse_features(src)[1]) for src in
           ("# F\n## PRODUCT\n### x\nfor: X.\nslug: y\n",
            "# F\n## PRODUCT\nslug: product\nfor: P.\nslug: again\n")],
          [True, True])
    check("grammar: a duplicate was line is refused",
          [any(f"repeats the field `{k}`" in p for p in _one(f"### x\nfor: A thing.\n{k}: {v}\n{k}: {v}\n")[1])
           for k, v in (("was", "old-x"), ("adrs", "0001"), ("done", '2026-11-23 21:20 "w"'))],
          [True, True, True])

    # ── NODE RULES — goal node tree, Task 2 (spec §2.2, §2.4, G6) ──────────────────────────────
    def _nodes(body: str) -> list[Node]:
        return parse_features("# Feature map\n## PRODUCT\n" + body)[0]

    check("rules: a stateless node needs no fragment",
          [check_nodes(_nodes(b)) for b in ("### x\nfor: A name only.\n", "### y\nfor: Another aim.\nareas: (y)\n")],
          [[], []])
    check("rules: adrs is a fragment",
          [check_nodes(_nodes(f"### x\nstate: built\nfor: A thing.\nadrs: {a}\n")) for a in ("0003", "0010, 0016")],
          [[], []])
    _bare = "### {s}\nstate: built\nfor: A thing.\n"
    check("rules: an anchored document is a fragment",
          [check_nodes(_nodes(_bare.format(s=s)), frozenset({s, "other"})) for s in ("x", "y")]
          + [any("no fragment" in p for p in check_nodes(_nodes(_bare.format(s="x")), frozenset({"y"})))],
          [[], [], True])
    check("rules: built with no fragment is refused",
          [any("no fragment" in p for p in check_nodes(_nodes(_bare.format(s=s)))) for s in ("x", "y")],
          [True, True])
    # ⛔ G6 — AN INDEPENDENT LITERAL LIST of the three failing shapes and the passing one, each at two
    # pairs, so the class is exercised by a copy `slug_problems` does not read, and a constant cannot
    # pass. The marker is the clause's own words, so severing one clause reddens only its own case.
    _G6 = (
        ("G6: two nodes may not share a slug", "two nodes share", (
            "### a\nfor: A.\n### a\nfor: A again.\n", "### b\nfor: B.\n#### b\nfor: B again.\n")),
        ("G6: a was entry may not equal a current slug", "is also a current slug", (
            "### a\nfor: A.\nwas: b\n### b\nfor: B.\n", "### c\nfor: C.\nwas: old, d\n### d\nfor: D.\n")),
        ("G6: a former slug listed twice is refused", "is listed as a former slug", (
            "### a\nfor: A.\nwas: old, old\n", "### a\nfor: A.\nwas: old\n### b\nfor: B.\nwas: old\n")),
        ("G6: a rename passes", None, (
            "### a\nfor: A.\nwas: old-a\n", "### b\nfor: B.\nwas: old-b, older-b\n### c\nfor: C.\nwas: old-c\n")),
    )
    for _name, _marker, _trees in _G6:
        _got = [slug_problems(_nodes(t)) for t in _trees]
        check(_name, [(any(_marker in p for p in g) if _marker else g) for g in _got],
              [True, True] if _marker else [[], []])
    _IDS = (
        ("G6: a slug equal to another's f- id is refused", "f- id", (
            ("### x\nfor: X.\n### f-x\nfor: F.\n", ("`x`", "`f-x`")),
            ("### f-y\nfor: F.\n### y\nfor: Y.\n", ("`y`", "`f-y`")))),
        ("G6: a slug equal to another's goal- id is refused", "goal- id of the node", (
            ("### x\nfor: X.\n### goal-x\nfor: G.\n", ("`x`", "`goal-x`")),
            ("### goal-y\nfor: G.\n### y\nfor: Y.\n", ("`y`", "`goal-y`")))),
        ("G6: a slug equal to a former slug's goal- id is refused", "goal- id of the former slug", (
            ("### a\nfor: A.\nwas: x\n### goal-x\nfor: G.\n", ("`x`", "`goal-x`")),
            ("### goal-y\nfor: G.\n### b\nfor: B.\nwas: y\n", ("`y`", "`goal-y`")))),
    )
    for _name, _marker, _pairs in _IDS:
        check(_name, [any(_marker in p and all(w in p for w in _want) for p in slug_problems(_nodes(t)))
                      for t, _want in _pairs], [True, True])
    check("G6: a goal- slug with no partner passes",
          [slug_problems(_nodes(t)) for t in ("### goal-tree\nfor: G.\n### other\nfor: O.\n",
                                              "### goal-x\nfor: G.\n### y\nfor: Y.\nwas: z\n")]
          + [any(m in " ".join(slug_problems(_live)) for m in ("f- id", "goal- id"))],
          [[], [], False])
    _rn = _nodes("### a\nfor: A.\nwas: old-a, older-a\n### b\nfor: B.\nwas: old-b\n")
    _rm = _nodes("### c\nfor: C.\nwas: old-c\n")
    check("resolve: current, former and unknown",
          ([resolve(_rn, "a"), resolve(_rn, "b"), resolve(_rn, "old-a"), resolve(_rn, "older-a"),
            resolve(_rn, "old-b"), resolve(_rn, "nope"), resolve(_rm, "old-c"), resolve(_rm, "old-a")],
           current_slugs(_rn), current_slugs(_rm)),
          (["a", "b", "a", "a", "b", None, "c", None], {"a", "b"}, {"c"}))
    _ABS = "### {s}\nstate: absent\nfor: A gap.\nexpected-because: standard.\n"
    check("rules: absent may carry adrs",
          [check_nodes(_nodes(_ABS.format(s="x") + f"adrs: {a}\n")) for a in ("0015", "0001, 0002")],
          [[], []])
    check("rules: absent may carry an anchored document",
          [check_nodes(_nodes(_ABS.format(s=s)), frozenset({s})) for s in ("x", "harness-ships-elsewhere")],
          [[], []])
    check("rules: absent with an area is refused",
          [[p for p in check_nodes(_nodes(_ABS.format(s="x") + a)) if "flip it to `built`" in p] for a in
           ("areas: (x)\n", "areas: (x), (y)\nadrs: 0015\n")],
          [["features.md:3: `x` is `absent` but claims 1 area(s) — flip it to `built`"],
           ["features.md:3: `x` is `absent` but claims 2 area(s) — flip it to `built`"]])
    check("summary: a stateless node is not counted absent",
          [summary_line(_nodes("### a\nstate: built\nfor: A.\nareas: (a)\n" + _ABS.format(s="b") + "### c\nfor: C.\n")),
           summary_line(_nodes("### a\nfor: A.\n### b\nfor: B.\n" + _ABS.format(s="c")))],
          ["3 nodes (1 built, 1 absent, 1 stateless)", "3 nodes (0 built, 1 absent, 2 stateless)"])
    # ⛔ S1 r1 (Codex High 2 = Claude F2): a CURRENT slug is held to the grammar a `was:` entry is.
    # AN INDEPENDENT LITERAL LIST, both sources (a trunk's `slug:` line and a `###` heading), each
    # failing shape at least twice, so a constant or a check of one source alone cannot pass.
    _NOT_SLUGS = ("## T\nslug: Not A Slug\nfor: P.\n", "## T\nslug:\nfor: P.\n", "## T\nslug: Upper-case\nfor: P.\n",
                  "## T\n### Foo Bar\nfor: X.\n", "## T\n### Upper-case\nfor: X.\n", "## T\n### trailing-\nfor: X.\n",
                  "## T\n### under_score\nfor: X.\n")
    _SLUGS = ("## T\nslug: product\nfor: P.\n", "## T\n### a-b-1\nfor: X.\n", "## T\n### x\nfor: X.\n")
    check("rules: every current slug follows the slug grammar",
          ([any("is not a slug" in p for p in check_nodes(parse_features("# F\n" + t)[0])) for t in _NOT_SLUGS],
           [check_nodes(parse_features("# F\n" + t)[0]) for t in _SLUGS],
           [p for p in check_nodes(_live) if "is not a slug" in p]),
          ([True] * len(_NOT_SLUGS), [[]] * len(_SLUGS), []))
    # ⛔ S1 r1 (Claude F3): `expected-because:` argues for an ABSENCE; a stateless node claims none.
    check("rules: a stateless node may not carry expected-because",
          [any("no `state:`" in p and "expected-because" in p for p in check_nodes(_nodes(b))) for b in
           ("### x\nfor: X.\nexpected-because: e.\n", "### y\nfor: Y.\nareas: (y)\nexpected-because: f.\n")]
          + [check_nodes(_nodes(_ABS.format(s="z")))],
          [True, True, []])
    # ⛔ S1 r2 (Codex Low): the refusal is of the FIELD, not of a non-empty value. A bare
    # `expected-because:` parses to "" and passed both the stateless and the `built` refusal, which
    # tested truthiness; the line was invisible on the page too. CONTROL: the same nodes without the
    # line pass, so a fix that refused every stateless or built node would also go red.
    check("rules: an EMPTY expected-because is still the field",
          [any("expected-because" in p for p in check_nodes(_nodes(b))) for b in
           ("### x\nfor: X.\nexpected-because:\n",
            "### y\nstate: built\nfor: Y.\nareas: (y)\nexpected-because:\n",
            "### x\nfor: X.\n", "### y\nstate: built\nfor: Y.\nareas: (y)\n")],
          [True, True, False, False])
    # ⛔ S1 r3 (Claude F2): a BARE `state:` parses to "", and the merged rule's message tested it by
    # TRUTHINESS, so the node drew two contradicting messages — `has state ''` from the state check,
    # then "has no `state:`" here, with the line right there in the file. EXACTLY ONE message
    # mentions `state:` being absent, and only for the node that truly has no `state:` line (CONTROL:
    # without it, a fix that dropped the "has no `state:`" wording entirely would also pass).
    _bare = check_nodes(_nodes("### x\nstate:\nfor: X.\nexpected-because: e.\n"))
    check("rules: a BARE state: is not reported as a missing state:",
          (sum("has no `state:`" in p for p in _bare), sum("expected-because" in p for p in _bare),
           sum("has no `state:`" in p for p in check_nodes(_nodes("### x\nfor: X.\nexpected-because: e.\n")))),
          (0, 1, 1))

    # ── G9 — `done:` cites a recorded request (goal node tree Task 3, spec §2.5) ───────────────
    _THREADS = ("# Goal threads\nprose above the first goal\n\n## GOAL ship-it\n"
                '> 2026-11-01 09:00 "ship the thing"\n- t1 · fix · a thread\n\n'
                "## GOAL other-aim\n"
                '> 2026-11-02 10:00 "another request"\n\n'
                "## GOAL old-name\n"
                '> 2026-11-03 11:00 "asked under the old name"\n')
    _req = requests_by_goal(_THREADS)
    _DONE = ("### ship-it\nfor: S.\ndone: {d}\n### other-aim\nfor: O.\n"
             "### renamed\nfor: R.\nwas: old-name\ndone: {r}\n")
    def _dp(d: str, r: str = '2026-11-03 11:00 "asked under the old name"'):
        return done_problems(_nodes(_DONE.format(d=d, r=r)), lambda: _req)
    check("G9: done equals a request under its node",
          (_dp('2026-11-01 09:00 "ship the thing"'), _req.get("ship-it"), sorted(_req),
           requests_by_goal('> 2026-01-01 00:00 "above"\n## GOAL a\n> 2026-01-02 00:00 "q"\n'
                            '## Notes\n> 2026-01-03 00:00 "not a goal\'s"\n')),
          ([], [("2026-11-01 09:00", "ship the thing")], ["old-name", "other-aim", "ship-it"],
           {"a": [("2026-01-02 00:00", "q")]}))
    check("G9: one changed character is refused",
          [any("`ship-it`" in p and "goal-threads.md" in p for p in _dp(d)) for d in
           ('2026-11-01 09:00 "ship the thinG"', '2026-11-01 09:00 "ship the thing."')], [True, True])
    check("G9: a different time is refused",
          [any("`ship-it`" in p for p in _dp(d)) for d in
           ('2026-11-01 09:01 "ship the thing"', '2026-11-02 09:00 "ship the thing"')], [True, True])
    check("G9: a request under another node does not count",
          [any("`ship-it`" in p for p in _dp(d)) for d in
           ('2026-11-02 10:00 "another request"', '2026-11-03 11:00 "asked under the old name"')], [True, True])
    check("G9: a request under a former slug counts",
          [_dp('2026-11-01 09:00 "ship the thing"'),
           any("`renamed`" in p for p in _dp('2026-11-01 09:00 "ship the thing"', '2026-11-01 09:00 "ship the thing"'))],
          [[], True])
    # Behaviour 6 through the REAL `main`: its paths pointed at a world whose features carry a `done:` line
    # and whose threads file does not exist. Exit 2 and a CANNOT RUN line — never a pass.
    import contextlib, io, tempfile
    _g = globals()
    _saved = {k: _g[k] for k in ("FEATURES", "GOAL_THREADS")}
    def _drive(threads: bytes | None, name: str = "goal-threads.md"):
        """`main` over the real tree plus one `done:` line, with the threads file holding `threads`
        (None: absent). Returns (exit code, whether stderr said CANNOT RUN)."""
        _g = globals()      # bound HERE: check-main-drivable reads a rebind in the function that calls main
        with tempfile.TemporaryDirectory() as _td:
            _f = pathlib.Path(_td) / "features.md"
            _f.write_text(FEATURES.read_text().replace(
                "\nstate: built\n", '\nstate: built\ndone: 2026-11-01 09:00 "ship the thing"\n', 1))
            _t = pathlib.Path(_td) / name
            if threads is not None:
                _t.write_bytes(threads)
            _g["FEATURES"], _g["GOAL_THREADS"] = _f, _t
            _err = io.StringIO()
            try:
                with contextlib.redirect_stderr(_err), contextlib.redirect_stdout(io.StringIO()):
                    _rc = main()
            except Exception as e:      # an uncaught read error is a crash, not CANNOT RUN
                _rc = type(e).__name__
            finally:
                _g.update(_saved)
            return (_rc, "CANNOT RUN" in _err.getvalue())
    check("G9: an unreadable threads file is CANNOT RUN",
          [_drive(None), _drive(None, "nested/goal-threads.md")], [(2, True), (2, True)])
    # ⛔ S1 r1 (Codex Medium 3): bytes that are not UTF-8 are a read failure, not a crash.
    check("G9: an undecodable threads file is CANNOT RUN",
          [_drive(b"\xff"), _drive(b"## GOAL ship-it\n> 2026-11-01 09:00 \"ship \xfe\"\n")], [(2, True), (2, True)])
    # ⛔ S1 r1 (Claude F4): a file that reads but holds no `## GOAL` heading is a parse that found
    # nothing — CANNOT RUN, never "copy the request line exactly" about a request that IS recorded.
    check("G9: a threads file with no goal heading is CANNOT RUN",
          [_drive(b""), _drive(b"# Goal threads\n## Notes\n> 2026-11-01 09:00 \"ship the thing\"\n"),
           _drive(b"## GOAL ship-it\n> 2026-11-01 09:00 \"a different request\"\n")],
          [(2, True), (2, True), (1, False)])
    def _never():
        raise AssertionError("the threads file was read although no node carries `done:`")
    def _safe(f):
        try:
            return f()
        except Exception as e:
            return type(e).__name__
    _probe = "\n### anchored-only-probe\nstate: built\nfor: A node whose one fragment is a spec naming it.\n"
    def _drive_anchor(named: str):
        """`main` over the live tree plus `_probe`, with `DOCS_DIR` holding ONE spec whose header names
        `named`. Returns (exit code, the probe's no-fragment problem printed, stdout)."""
        _g = globals()      # bound HERE: check-main-drivable reads a rebind in the function that calls main
        _keep = {k: _g[k] for k in ("FEATURES", "DOCS_DIR")}
        with tempfile.TemporaryDirectory() as _td:
            _f = pathlib.Path(_td) / "features.md"
            _f.write_text(FEATURES.read_text() + _probe)
            _d = pathlib.Path(_td) / "docs"
            (_d / "superpowers" / "specs").mkdir(parents=True)
            (_d / "superpowers" / "plans").mkdir(parents=True)
            (_d / "superpowers" / "specs" / "2026-01-01-probe.md").write_text(
                f"# Probe\n\n> **Anchor:** `{named}` — **ADR:** none\n")
            _g["FEATURES"], _g["DOCS_DIR"] = _f, _d
            _err, _out = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stderr(_err), contextlib.redirect_stdout(_out):
                    _rc = main()
            except Exception as e:
                _rc = type(e).__name__
            finally:
                _g.update(_keep)
            return (_rc, "`anchored-only-probe` is `built` but names no fragment" in _err.getvalue(),
                    _out.getvalue())
    # ⚠ The live tree has one node that leans on its documents alone (`serve-path-bounding`, measured at
    # Task 7), so a world holding only the probe's spec fails on THAT node too: the case reads the
    # probe's own line, never the exit code.
    _with, _without = _drive_anchor("anchored-only-probe"), _drive_anchor("some-other-node")
    check("main: a built node with only an anchored document passes", _with[1], False)
    check("main: without its document it is refused", _without[1], True)
    # The summary prints only on a pass, so it is read off the live tree unmodified.
    _sum = io.StringIO()
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(_sum):
        _sum_rc = main()
    check("summary line names no anchor count",
          (_sum_rc, bool(re.search(r"; \d+ backlog areas all claimed exactly once", _sum.getvalue())),
           "anchor" in _sum.getvalue()), (0, True, False))
    check("G9: no done line needs no threads file",
          [_safe(lambda: done_problems(_nodes("### a\nfor: A.\n### b\nstate: built\nfor: B.\nareas: (b)\n"), _never)),
           _safe(lambda: done_problems(_live, _never))],
          [[], []])

    # ── adrs: every number is a file (goal node tree Task 5) ────────────────────────────────────
    _ADR = "### a\nfor: A.\nadrs: {a}\n### b\nfor: B.\nadrs: {b}\n"
    check("adrs: a number with no file is refused",
          [[("`a`" in p, "9999" in p) for p in adr_problems(_nodes(_ADR.format(a="9999", b="0001")), {"0001"})],
           adr_problems(_nodes(_ADR.format(a="0001", b="0002")), {"0001", "0002"})],
          [[(True, True)], []])
    check("adrs: two nodes, one bad number, names only that one",
          [[("`b`" in p, "`a`" in p, "0007" in p) for p in
            adr_problems(_nodes(_ADR.format(a="0003, 0005", b="0005, 0007")), {"0003", "0005"})],
           [("`a`" in p, "0004" in p) for p in
            adr_problems(_nodes(_ADR.format(a="0004", b="0003")), {"0003", "0005"})]],
          [[(True, False, True)], [(True, True)]])

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())

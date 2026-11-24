# One tree of named nodes — implementation plan (slices S1–S5)

> **Anchor:** `status-visibility` — **ADR:** 0010, 0016
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** 🟠 current — DRAFT plan, written 2026-11-24 from the approved spec
`docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` at `2ea4a5e8` (owner approved 2026-11-23 21:20,
spec §6.1). Phase 2: dual adversarial review to convergence or the round cap (`docs/review-method.md` §0 Q4c)
before any task is dispatched. Nothing is built.

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` — a NEW subagent per
> task, per fold and per review round. Steps use checkbox (`- [ ]`) syntax. Read the spec section each task
> names before writing anything; this plan argues from the spec and does not restate it.

**Goal:** `docs/features.md` becomes the one list of names; `docs/anchors.md` is deleted; `docs/goal-threads.md`
keeps threads and requests and stops allocating names; `/goals`, `/features` and `/goal-tree` become three
views of the same 45 nodes.

**Architecture:** One parser (`parse_features` in `scripts/check-features.py`) owns the node set, and every
other script takes the set from it — never from a list of its own. Names move in two slices (S2 the registry,
S3 the goal-tree goals) so a red gate names one cause; the grammar that can hold them lands first (S1) and the
views last (S4). A renamed slug is recorded in `was:` and read back through one function, `resolve`.

**Tech Stack:** Python 3 standard library only; each script's own `--self-test`; mutation manifests under
`scripts/mutations/`; Markdown sources under `docs/`.

**Spec:** `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` — executors read both. ADRs:
`docs/adr/0010-documents-declare-their-anchor.md`, `docs/adr/0016-names-live-in-one-node-tree.md`.

---

## Global Constraints

- **The spec's decisions are closed** (§6.1 records 28 owner answers). A task that seems to need a different
  answer STOPS and notifies; it does not choose.
- **Slice order is S1 → S2 → S3 → S4 → S5**, one pull request per slice, each cut from a fresh `origin/master`
  after the previous slice has merged. A DRAFT pull request is opened at each slice's start so CI runs the
  selected mutation sweep (spec §5.1.1).
- **Every slice leaves every gate green.** FAILS IF, for every slice:
  `python3 scripts/goal-tree.py --snapshot --page --out "$(mktemp -d)/goal-tree.html"` exits non-zero, or any
  `python3 scripts/check-*` step of `.github/workflows/ci.yml` is red.
- **Whole-migration FAILS IF** (spec §5.2): after S3 a snapshot over a log holding pre-rename snapshots
  reports any slug as unknown; or the thread count after S3 differs from the count before it (Task 13).
- **A quote is never rewritten.** Request lines (`> YYYY-MM-DD HH:MM "…"`) in `docs/goal-threads.md` and the
  quoted words of a `done:` line stay byte-identical through every slice (spec §2.4).
- **History is left as written:** `docs/reviews/`, `docs/superpowers/` (except the two documents Task 6
  names), `docs/explainers/`, `docs/dashboard-entries.md`, `docs/backlog.md` row bodies,
  `docs/marketplace/*.json`, and ADR-0016 (spec §5.1, S2 row; §6 Q4).
- **No trigger is added.** No hook, `pages_for` route or `PAGE_SOURCES` entry gains a source; the only
  trigger edits are the removals of `docs/anchors.md` in Task 11 (spec §5.1.1).
- **Every script edit is a two-file edit** with `scripts/mutations/<stem>.json`. The pins that move with it
  are in *Wiring pins* below. A self-test failure line keeps the shape `[FAIL] <case name>: …`, which the
  mutation harness parses.
- **Cite code by symbol, never by line number**, in code comments, commit messages and review documents.
- **Backlog and roadmap ticks ride the slice's own pull request**; each branch records a dashboard entry
  (`scripts/check-dashboard-entry.py`, run AFTER committing).
- **Never read anything under `.claude/plans/`**; the repository is public.

### Wiring pins — owed by every task that edits a self-tested script

| Pin | What moves | How |
|---|---|---|
| W1 | the docstring's declared case count | re-copy from the suite's own `N/N self-test cases passed` line; never type a total |
| W2 | one manifest entry per new guard clause | `scripts/mutations/<stem>.json`, keys `name`, `file`, `edits`, `expect`; `expect` is the exact case name the mutation must redden |
| W3 | `EXPECTED_MUTATIONS` | `scripts/mutations/expected_mutations.py`, the script's entry set to the manifest's new length |
| W4 | anchors that the edit unbound | `python3 scripts/check-plan-code.py --mutate . --only scripts/<name>.py` — every entry red via its named case, none `cannot apply` |
| W5 | `EXAMINED_KEYS` | `scripts/check-fixture-variation.py`, re-derived by its `analyse()` when a self-test fixture gains or loses a key — IN THE SAME TASK AND COMMIT as the edit, never a later one: CI runs `python3 scripts/check-fixture-variation.py`, which reports an examined key whose function is gone (r1 Codex Major, Tasks 8/10). Known pins at this plan's base: `gen-goals-page.py` → `parse_registry.text` (Task 8); `check-features.py` → `check_cross.anchors_declared` (Task 7); `check-anchors.py` → `audit.*` (Task 6, when `audit` gains `nodes`) |
| W6 | `scripts/check-selftest-counts.py --changed` and `scripts/check-ratchet-contract.py` | run; both exit 0 |

### The task cycle

Every task below runs the same cycle, and its checkboxes name only what differs: (1) add the listed cases
to the script's `_self_test_body`, each driving its producer at two distinct inputs in one case where a
derived value is asserted; (2) run the self-test and see each new case `[FAIL]` for the stated reason;
(3) implement; (4) run the self-test green; (5) add the listed mutations and run W1–W6; (6) commit the
explicit paths with `git commit -F <file>`.

---

## Review Focus

Inputs the spec implies and no slice's guard reaches by itself. Each has a case in the task that owns the code.

1. **A rename alone must not read as activity.** Two snapshots that differ only because a slug was renamed
   would log every thread as removed from one goal and added to another. Expected: no change is logged.
   Owner: Task 14, case `history: a rename alone logs no thread move`.
2. **A branch opened before S2 that lands a retired slug after it.** A document merged later with
   `Anchor: dev-speed-first` must fail with the current name in the message, not with "unknown anchor".
   Owner: Task 6, case `G1: a was: slug fails and names the current slug`.
3. **An ADR with no `## ` heading, or a header past any fixed window.** Reading "up to the first `## `"
   must mean the whole file when there is none. Owner: Task 6, case `G1: an ADR with no ## heading is read whole`.
4. **Two pull requests each adding a node under one parent, batched.** The union must keep both nodes whole;
   a field line of one must never land under the other's heading, and no node may change parent unless one
   side moved it. Owner: Task 16, cases `features union: two added nodes keep their own fields`,
   `tree P4: a field line keeps its node heading` and `tree P8: a clean merge that re-parents a node ejects`.
5. **A node with no state and no area.** It must say "claims no area — gaps not counted", never show an empty
   count (spec §3.2). Owner: Task 4, case `index: a node claiming and inheriting no area says so`.

---

## Slice map

| Slice | Branch | Tasks | What merges | Outward-facing? |
|---|---|---|---|---|
| S1 — the tree can hold everything | `node-tree-s1-grammar` | 1–4 | grammar, `resolve`, G6, G9, an N-level index. No name moves | no |
| S2 — the registry folds in | `node-tree-s2-registry` | 5–11 | `adrs:`, two new nodes, `dev-speed`, G1, G3, G4; `docs/anchors.md` deleted; ADR-0010 and ADR-0016 accepted | no |
| S3 — goals become nodes | `node-tree-s3-goals` | 12–16 | the remaining nodes and renames, `also`, `--also`, G2, G5, history through `resolve`, the batch resolver | no |
| S4 — the views | `node-tree-s4-views` | 17–21 | one id, one link kind, two-way links, `/goals` as the tree, G7, G8, the PRIORITY line | no (local pages) |
| S5 — vocabulary | `node-tree-s5-vocabulary` | 22 | `CONTEXT.md`, the comprehensibility-suite spec's §4, two backlog rows closed, one filed | no |

## File map

| File | Slices | Responsibility after the work |
|---|---|---|
| `scripts/check-features.py` | S1 S2 S3 | the node grammar and set; `resolve`; G2, G6, G9; the request and goal-heading grammar |
| `scripts/gen-features-page.py` | S1 S2 S4 | `/features`: N-level index, fragments by node slug, primary counts (G7) |
| `scripts/check-anchors.py` | S2 | G1 over specs, plans and ADRs; G3; the header reader |
| `scripts/gen-backlog-page.py` | S2 | `parent_errors` fed the tree's slugs |
| `scripts/gen-goals-page.py` | S2 S4 | `/goals`: cards from the tree |
| `scripts/check-goal-status.py` | S2 | the armed set derived (G4) |
| `scripts/explainer-serve.py`, `scripts/check-fixture-variation.py`, `scripts/check-publishability.py` | S2 | stop naming the registry |
| `.claude/hooks/regen-goals-page.sh`, `.claude/hooks/regen-features-page.sh` | S2 | drop the registry trigger |
| `scripts/goal-tree.py` | S1 (two aliases) S3 S4 | goals are nodes; `also`; history through `resolve`; the agenda's PRIORITY line |
| `scripts/session-state.py` | S3 | `--also`; G5 |
| `scripts/batch-ci.py` | S3 | a `tree` union policy for `docs/features.md` (resolution as `blocks`; postcondition P8) |
| `scripts/page_markup.py`, `scripts/check-page-links.py` | S4 | one node id, one node link kind; G8 |
| `docs/features.md` | S2 S3 | the 45 nodes |
| `docs/goal-threads.md` | S3 S4 | threads and requests under node headings; the PRIORITY line |
| `docs/anchors.md` | S2 | deleted |

---

## Slice S1 — the tree can hold everything

Spec: §2.2, §2.4, §2.5 (G6, G9), §5.1 S1 row. No name in `docs/features.md` changes in this slice, so
`python3 scripts/check-features.py` must print the same node count before and after it.

### Task 1: The node grammar — new fields, optional state, depths 2–6, a slug on a trunk

**Files:**
- Modify: `scripts/check-features.py` (`FIELD_NAMES`, `LIST_FIELDS`, `FIELD`, `Node`, `parse_features`)
- Modify: `scripts/mutations/check-features.json`

**Interfaces:**
- Consumes: `parse_features`, `Node`, `FIELD_NAMES`, `LIST_FIELDS`, `STATUS_TOKENS` (as they are today)
- Produces: `Node` with the added attributes `parent: str | None`, `adrs: tuple[str, ...]`,
  `was: tuple[str, ...]`, `done: tuple[str, str] | None` (when, words), `proposed: str | None`, and
  `state: str | None`; `DONE_FIELD`, `PROPOSED_FIELD` (compiled patterns); `parse_features(text)` unchanged
  in signature, returning trunk nodes as well when a trunk carries a `slug:` line

Grammar decisions this task fixes (see *Choices the spec left open*, C1–C3):
- `adrs:` and `was:` are BARE comma lists, the form `anchors:` uses today and `parse_features` already
  splits (`value.split(",")`, each entry stripped) — `adrs: 0001, 0005`, `was: dev-speed-first, harness-speed`
  (spec §5.1). No parenthesis is stripped: in `areas: (cloud/frontend)` the parentheses belong to the backlog
  `(area)` TAG, not to a list grammar. An `adrs:` entry is four digits; a `was:` entry is a slug; an entry
  carrying a `(` or `)` is refused as malformed.
- `done: YYYY-MM-DD HH:MM "<words>"` and `proposed: YYYY-MM-DD HH:MM` are single-line fields.
- A trunk stays a `## ` heading with its display text. A column-0 `slug: <slug>` line directly under it makes
  it a node at level 2, which then needs a `for:` line like any node. `slug:` anywhere else is refused.
- A node heading is `###` to `######`. A node's `parent` is the slug of the nearest preceding node of a
  smaller level, or of its trunk when the trunk has a slug, else `None`. A heading that skips a level
  (`#####` directly under `###`) is refused.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | list field parsed | `adrs: 0001, 0005` and, in the same case, `was: a, b` | `Node.adrs == ("0001", "0005")`, `Node.was == ("a", "b")` |
| 2 | malformed ADR number | `adrs: 1, 0005`; and `adrs: (0001, 0005)` | a problem naming the line and the entry, for each (the parenthesised form is NOT a list grammar) |
| 3 | state omitted | a node with `for:` and no `state:` | `state is None`, no problem from the parser |
| 4 | `done:` well-formed | `done: 2026-11-23 21:20 "it is finished"` | `done == ("2026-11-23 21:20", "it is finished")` |
| 5 | `done:` malformed | no time, or no quoted sentence | a problem quoting the required form |
| 6 | `proposed:` parsed | `proposed: 2026-11-24 09:30` | `proposed == "2026-11-24 09:30"` |
| 7 | depth 5 and 6 | `#####` under `####`, `######` under `#####` | nodes with `level` 5 and 6 and the right `parent` |
| 8 | skipped level | `#####` directly under `###` | a problem naming both headings |
| 9 | trunk with a slug | `## PRODUCT` then `slug: product`, `for: …` | a level-2 node `product`; its `###` children have `parent == "product"` |
| 10 | trunk without a slug | today's file | no trunk node; children have `parent is None`; node count unchanged |
| 11 | `slug:` under a node heading | `### x` then `slug: y` | a problem: only a trunk takes a slug line |
| 12 | duplicate new field | two `was:` lines on one node | the existing duplicate-field refusal fires |

- [ ] **Step 1:** add cases `grammar: adrs and was are bare comma lists`, `grammar: adrs entry must be four digits`
  (its loop includes `(0001` and `0005)`),
  `grammar: state may be omitted`, `grammar: done parses when and words`, `grammar: done needs a time and a quote`,
  `grammar: proposed parses`, `grammar: depth five and six carry a parent`, `grammar: a skipped level is refused`,
  `grammar: a trunk slug makes a level-2 node`, `grammar: a slugless trunk yields no node`,
  `grammar: slug under a node is refused`, `grammar: a duplicate was line is refused`.
- [ ] **Step 2:** run `python3 scripts/check-features.py --self-test`; each new case is `[FAIL]`.
- [ ] **Step 3:** implement in `parse_features`. The `else` branch that raises on an unassigned field stays,
  so a field added to `FIELD_NAMES` without a parser arm still fails loudly.
- [ ] **Step 4:** self-test green; `python3 scripts/check-features.py` prints today's node count.
- [ ] **Step 5:** mutations, one per clause: the four-digit test of `adrs:`; the skipped-level refusal; the
  `slug:`-only-under-a-trunk refusal; the `done:` pattern's time group; the parent assignment for a level-5
  node. Then W1–W6.
- [ ] **Step 6:** commit.

**FAILS IF:** `python3 scripts/check-features.py` reports a different node count than at the slice's base, or
`python3 scripts/gen-features-page.py --self-test` goes red (it loads `Node` from this script).

### Task 2: Node rules — optional state, the fragment rule, G6, `resolve`

**Files:**
- Modify: `scripts/check-features.py` (`check_nodes`; new `current_slugs`, `slug_problems`, `resolve`)
- Modify: `scripts/mutations/check-features.json`

**Interfaces:**
- Consumes: `Node` (Task 1)
- Produces: `summary_line(nodes: list[Node]) -> str` (built, absent and stateless counted separately);
  `current_slugs(nodes: list[Node]) -> set[str]`;
  `resolve(nodes: list[Node], slug: str) -> str | None` (the current slug for a current or former slug, else
  `None` — for READING history only); `slug_problems(nodes: list[Node]) -> list[str]` (G6);
  `check_nodes(nodes: list[Node], anchored: frozenset[str] = frozenset()) -> list[str]`, where `anchored` is the
  set of slugs some document's `Anchor:` header names

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | stateless node | no `state:`, no fragment | no problem |
| 2 | `built` with `adrs:` only | `state: built`, `adrs: 0003` | no problem |
| 3 | `built` with an anchored document only | slug in `anchored` | no problem |
| 4 | `built` with nothing | no areas, adrs, anchors, not in `anchored` | the existing no-fragment problem |
| 5 | G6: two nodes share a slug | — | a problem naming both lines |
| 6 | G6: a `was:` entry equals a current slug | node `a` has `was: b` and a node `b` exists | a problem |
| 7 | G6: one former slug listed twice | in one list, and in two lists | a problem in each shape |
| 8 | G6: a `was:` entry that occurs once | the rename case | PASSES |
| 9 | `resolve` of a current slug | — | itself |
| 10 | `resolve` of a former slug | — | the node's current slug |
| 11 | `resolve` of an unknown slug | — | `None` |
| 12 | `absent` still needs `expected-because:` | — | unchanged |
| 13 | `absent` with an `adrs:` line | `state: absent`, `adrs: 0015` (the live `harness-ships-elsewhere` after Task 5) | no problem — only `areas` contradict `absent` |
| 14 | `absent` with an anchored document | slug in `anchored` (the live `harness-ships-elsewhere` after Task 7: three documents) | no problem |
| 15 | `absent` with an area | `state: absent`, `areas: (x)` | the existing "flip it to `built`" problem, counting AREAS only |
| 16 | the summary line | one built, one absent, one stateless node | `(1 built, 1 absent, 1 stateless)` — a stateless node is never counted as absent |
| 17 | G6: a slug that is another node's `f-` id | nodes `x` and `f-x` | a problem naming both: on `/features` the bare id of `f-x` equals the `f-<slug>` id of `x` (Task 17) |
| 18 | G6: a slug that is another node's `goal-` id | nodes `x` and `goal-x` | a problem naming both: the bare id of `goal-x` equals `x`'s primary `goal-x` |
| 19 | G6: a slug that is a former slug's `goal-` id | node `a` with `was: x`, and a node `goal-x` | a problem: the bare id of `goal-x` equals `a`'s second id `goal-x` |
| 20 | G6: a `goal-` slug with no partner | the live `goal-tree`, no node or `was:` entry `tree` | PASSES — the rule is on PAIRS, never on a prefix |

**No two nodes' page ids may meet (r2 Codex Major).** `/features` gives a slug `s` the ids `goal-s`, `s`,
`f-s` and `goal-<w>` for each former slug `w` (Task 17); `/goals` and `/goal-tree` give `goal-s`, `g-s` and
`goal-<w>`. Two different nodes can share an id only when one slug is `f-` + another current slug, or `goal-` +
another current or former slug (every other pairing differs in its prefix, and a former slug equal to a current
one is already G6 behaviour 6). `slug_problems` refuses exactly those pairs, so the views never have to drop
an id. A PREFIX ban is wrong: the live node `goal-tree` begins with `goal-` and has no partner. Verified at
this plan's base: no slug in `docs/features.md`, no `## GOAL` name in `docs/goal-threads.md` and no registry
row of `docs/anchors.md` is `f-` or `goal-` plus another of them, and none of the slugs or `was:` entries
Tasks 5 and 12 add makes one.

**The two fragment counts are different sets (r1 F2).** The `built` arm counts `areas` + `adrs` + anchors +
anchored documents: any one of them is evidence the node exists. The `absent` arm counts `areas` ONLY: a
backlog row is shipped work, which contradicts an absence; an ADR or a spec describes a gap and may sit under
an absent node (spec §4 row 4.45 keeps `harness-ships-elsewhere` absent while giving it `adrs: 0015`).

- [ ] **Step 1:** cases `rules: a stateless node needs no fragment`, `rules: adrs is a fragment`,
  `rules: an anchored document is a fragment`, `rules: built with no fragment is refused`,
  `G6: two nodes may not share a slug`, `G6: a was entry may not equal a current slug`,
  `G6: a former slug listed twice is refused`, `G6: a rename passes`,
  `G6: a slug equal to another's f- id is refused`, `G6: a slug equal to another's goal- id is refused`,
  `G6: a slug equal to a former slug's goal- id is refused`, `G6: a goal- slug with no partner passes`
  (each of the three refusals at two pairs, `x`/`f-x` and `y`/`f-y`, so a constant cannot pass),
  `resolve: current, former and unknown`, `rules: absent may carry adrs`,
  `rules: absent may carry an anchored document`, `rules: absent with an area is refused`,
  `summary: a stateless node is not counted absent` (the summary is built by a pure `summary_line(nodes)`
  that `main` prints, so the case reads the same function). The G6 cases loop an independent literal list of the three failing
  shapes plus the passing one, so the class is exercised by a copy the code does not read.
- [ ] **Step 2:** red. **Step 3:** implement; `main` calls `slug_problems` and passes `frozenset()` for
  `anchored` (the live wiring is Task 7, when the header reader exists in one place). **Step 4:** green.
- [ ] **Step 5:** mutations: each of the three G6 clauses severed singly (each reddens only its own case —
  the identity check that the cases are not interchangeable); `resolve` returning the input for a former
  slug; the `anchored` term dropped from the fragment rule; `adrs` added to the `absent` arm's count
  (reddens `rules: absent may carry adrs`); the `absent` count in `summary_line` computed as
  `len(nodes) - built` again (reddens `summary: a stateless node is not counted absent`); each of the three
  id-collision clauses severed singly (each reddens only its own case); the pair test replaced by a prefix test
  (reddens `G6: a goal- slug with no partner passes`). Then W1–W6.
- [ ] **Step 6:** commit.

**FAILS IF:** a tree holding `was: x` on one node and a node named `x` passes `python3 scripts/check-features.py`;
or a tree holding `state: absent` with `adrs: 0015` and an `expected-because:` fails it; or a tree holding the
nodes `x` and `f-x` (or `x` and `goal-x`) passes it; or the live tree, with its `goal-tree` node, fails it.

### Task 3: G9 — `done:` cites a recorded request

**Files:**
- Modify: `scripts/check-features.py` (new `GOAL_HEADING`, `REQUEST`, `requests_by_goal`, `done_problems`; `main`)
- Modify: `scripts/goal-tree.py` (`GOAL_RE` and `REQUEST_RE` become aliases of the two patterns above, read
  through `_sibling("check-features")`)
- Modify: `scripts/mutations/check-features.json`, `scripts/mutations/goal-tree.json` (rebind only)

**Interfaces:**
- Consumes: `Node.done`, `resolve` (Tasks 1–2); `_sibling` in `scripts/goal-tree.py`
- Produces: `GOAL_HEADING`, `REQUEST` (the patterns `scripts/goal-tree.py` defines today as `GOAL_RE` and
  `REQUEST_RE`, moved, not copied); `requests_by_goal(text: str) -> dict[str, list[tuple[str, str]]]`
  (heading slug → its request lines, in file order); `done_problems(nodes, requests) -> list[str]`

A `done:` line passes when its (when, words) pair equals a request under a `## GOAL` heading whose slug
`resolve`s to that node — so the rule holds both before S3 re-points the headings and after.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | equal to a request under the node | same time, same words | no problem |
| 2 | words differ by one character | — | a problem naming the node and the request file |
| 3 | time differs | — | a problem |
| 4 | the request sits under ANOTHER node | — | a problem |
| 5 | the request sits under a heading that is a `was:` slug of the node | — | no problem |
| 6 | `docs/goal-threads.md` cannot be read AND some node carries `done:` | file absent | `CANNOT RUN`, exit 2 — never a pass |
| 7 | no node carries `done:` | today's file | no problem; the summary line is unchanged |
| 8 | no node carries `done:` and there is no threads file | a self-test world without it | no problem, and the file is never opened — the read is lazy (r1 F5), so `gen-features-page.py`, which loads this module, needs no threads file in its worlds |

- [ ] **Step 1:** cases `G9: done equals a request under its node`, `G9: one changed character is refused`,
  `G9: a different time is refused`, `G9: a request under another node does not count`,
  `G9: a request under a former slug counts`, `G9: an unreadable threads file is CANNOT RUN`,
  `G9: no done line needs no threads file` (its world has no `docs/goal-threads.md`; it passes a reader that
  raises if called, so a mutation that reads eagerly goes red).
- [ ] **Step 2:** red. **Step 3:** implement; move the two patterns and alias them in `scripts/goal-tree.py`.
  `main` reads `docs/goal-threads.md` only when `any(n.done for n in nodes)`.
- [ ] **Step 4:** both self-tests green: `python3 scripts/check-features.py --self-test` and
  `python3 scripts/goal-tree.py --self-test`.
- [ ] **Step 5:** mutations: the words comparison; the time comparison; the under-that-node restriction; the
  `any(n.done …)` guard on the read removed (reddens `G9: no done line needs no threads file`). In
  `scripts/mutations/goal-tree.json` no entry is added; W4 confirms none lost its anchor. Then W1–W6 for both.
- [ ] **Step 6:** commit.

**FAILS IF:** `git grep -n -E 'REQUEST_RE = re\.compile|GOAL_RE = re\.compile' -- scripts/goal-tree.py`
prints a line (the grammar would then live in two places).

### Task 4: `/features` draws any depth, trunk nodes and stateless nodes

**Files:**
- Modify: `scripts/gen-features-page.py` (`group_tree`, `render_index`, `index_shape`, `state_html`,
  `gaps_html`, `render_node`)
- Modify: `scripts/mutations/gen-features-page.json`

**Interfaces:**
- Consumes: `Node.parent`, `Node.level`, `Node.state` (Task 1)
- Produces: `group_tree(nodes: list[Node]) -> list[tuple[str, Node | None, list]]` — one entry per trunk:
  (display name, the trunk's node or `None`, a nested list of `(node, children)` to any depth);
  `inherits_area(node: Node, by_slug: dict[str, Node]) -> bool`

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | today's file | two levels, slugless trunks | the index HTML is byte-identical to the base's |
| 2 | five levels | a `#####` node | nested one `<ul>` per level, in file order |
| 3 | a node whose parent is missing | level 4 first under a trunk | a top-level entry, never dropped (today's rule, kept) |
| 4 | trunk node | trunk with a slug | the trunk's name is a link to its card, and it has a card |
| 5 | stateless node | `state is None` | no state badge; its gap count still shown |
| 6 | no area claimed or inherited | empty `areas`, no ancestor with one | the text "claims no area — gaps not counted" |
| 7 | no own area, an ancestor claims one | — | a count, as today |

- [ ] **Step 1:** cases `index: today's two levels render unchanged` (compares against the literal of the
  base's rendering for a fixed fixture), `index: five levels nest in file order`,
  `index: an orphan level is kept`, `index: a trunk node is linked and carded`,
  `index: a stateless node shows no badge`, `index: a node claiming and inheriting no area says so`,
  `index: an inherited area still counts`. Every case that asserts HTML also asserts it parses
  (`html.parser`, balanced `<ul>`).
- [ ] **Step 2:** red. **Step 3:** implement. **Step 4:** green;
  `python3 scripts/gen-features-page.py --self-test` and `python3 scripts/check-page-links.py` both exit 0.
- [ ] **Step 5:** the existing index mutations (the pin PR #624 added) are REBOUND to the reworked
  `group_tree` and `render_index`, none deleted; add: the recursion's depth bound; the stateless branch of
  `state_html`; the no-area sentence. Then W1–W6.
- [ ] **Step 6:** commit; then the slice's dashboard entry and the *Before every push* list.

**FAILS IF:** the manifest for `scripts/gen-features-page.py` is shorter after this task than before it.

---

## Slice S2 — the registry folds in

Spec: §2.2 (`anchors:` row), §2.5 (G1, G3, G4), §4, §5.1 S2 row and its FAILS IF, §6 Q6, Q10, Q13.
At this plan's base (`2ea4a5e8`) the two S2 searches print 48 lines in 19 files and 18 lines in 5 files;
Task 5 re-runs them at the slice's base and records the numbers in the pull request.

### Task 5: The tree's data — ADRs, two new nodes, `dev-speed`; ADR-0010 accepted

**Files:**
- Modify: `docs/features.md`
- Modify: `docs/adr/0010-documents-declare-their-anchor.md` (status → accepted, spec §6 Q10)
- Modify: `scripts/check-features.py` (one new rule), `scripts/mutations/check-features.json`

**Interfaces:**
- Consumes: the grammar of Task 1; `slug_problems` (Task 2)
- Produces: the nodes `cloud-publishing`, `serve-money-guard`, `dev-speed`; `adr_problems(nodes, known: set[str]) -> list[str]`
  (every `adrs:` number is a file under `docs/adr/`)

Edits to `docs/features.md`, each from the spec's §4 row. `anchors:` lines STAY in this task (the registry
is still read until Task 7), so the tree and the registry agree at every commit.

| Row | Edit |
|---|---|
| 4.3 | new `####` node `cloud-publishing` under `summarise-a-playlist`; `for:` is the registry's sentence; `adrs: 0001, 0005`; NO `state:` (Q13) |
| 4.18 | new `####` node `serve-money-guard` under `spend-control`; `for:` is the registry's sentence; `adrs: 0008`; NO `state:` (Q13) |
| 4.10, 4.12, 4.19, 4.20, 4.43, 4.45 | `adrs:` added: `share-and-download` 0003; `cloud-sync` 0002; `stable-blob-addressing` 0006, 0007; `cloud-blob-key-encoding` 0009; `review-decides-itself` 0014; `harness-ships-elsewhere` 0015 |
| 4.24 | the `harness-speed` block (heading plus its field lines) is MOVED, not re-levelled in place: cut from among `guard-and-gate-harness`'s `####` children and pasted as a `###` block after the last of them (`guard-soundness`) ends, still under DEV INFRASTRUCTURE; heading renamed to `dev-speed`; `was: dev-speed-first, harness-speed`; `for:` is the registry's sentence for `dev-speed-first`; its `state:` line is removed; `areas: (tooling/speed)` stays. A `###` left where the `####` stood would re-parent the five siblings below it (`review-process`, `mutation-and-test-quality`, `hooks-and-session-continuity`, `backlog-and-page-tooling`, `guard-soundness`) with every gate green (r1 F3) |

Before writing the `adrs:` lines, read the registry table in `docs/anchors.md` and copy each ADR column
from it; the list above is the spec's and the registry is the source. Any anchor whose ADR column is not in
the list above is added the same way.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | an `adrs:` number with no file | `adrs: 9999` | a problem naming the node and the number |
| 2 | every ADR number has a file | the live tree | no problem |
| 3 | `harness-speed` kept beside `dev-speed` | both a heading and a `was:` entry | G6 refuses (Task 2's case, now reachable on live data) |

- [ ] **Step 1:** cases `adrs: a number with no file is refused`, `adrs: two nodes, one bad number, names only that one`.
- [ ] **Step 2:** red. **Step 3:** implement `adr_problems`, call it from `main`; edit `docs/features.md`
  and ADR-0010. **Step 4:** green: `python3 scripts/check-features.py`, `python3 scripts/check-anchors.py`,
  `python3 scripts/gen-features-page.py --self-test`, `python3 scripts/gen-goals-page.py --self-test`.
- [ ] **Step 5:** mutation: the membership test of `adr_problems`. Then W1–W6.
- [ ] **Step 6:** commit. Record in the commit message the ADR column of each of the 15 registry rows and
  the node that now carries it.

**FAILS IF:** some ADR number in the registry table of `docs/anchors.md` appears on no node's `adrs:` line.
Check: `grep -o '[0-9]\{4\}' docs/anchors.md | sort -u` against
`grep '^adrs:' docs/features.md | grep -o '[0-9]\{4\}' | sort -u`, restricted to the registry's table rows.
Or `python3 scripts/check-features.py` is red after the edit (the `absent` node `harness-ships-elsewhere` now
carries `adrs: 0015`; Task 2's behaviour 13 is what keeps it green — r1 F2). Or the parent diff below prints
anything but EXACTLY these four lines (r2 Codex Minor — the rename removes a pair as well as adding one):

```
pairs() { python3 -c 'import importlib.util as u,sys; s=u.spec_from_file_location("cf","scripts/check-features.py"); m=u.module_from_spec(s); s.loader.exec_module(m); [print(n.slug, n.parent) for n in m.parse_features(sys.stdin.read())[0]]'; }
diff <(git show origin/master:docs/features.md | pairs | sort) <(pairs < docs/features.md | sort) | grep '^[<>]'
```

```
< harness-speed guard-and-gate-harness
> cloud-publishing summarise-a-playlist
> dev-speed None
> serve-money-guard spend-control
```

Removed: one pair, `harness-speed`'s (the slug is renamed, so the old pair goes). Added: three pairs — the two
new nodes and `dev-speed` (a `###` under the slugless DEV INFRASTRUCTURE trunk, so its parent is `None` until
Task 12 gives the trunk a slug). Changed: NONE — a changed parent shows as a `<` line and a `>` line for the
same slug, and no slug may appear on both sides; one there is a re-parented node (for example one of the five
siblings, had `harness-speed` been re-levelled in place). The `grep` drops `diff`'s hunk headers.

(`parse_features` returns `(nodes, problems)` today. The slice's own parser reads BOTH texts, so both sides
carry Task 1's `parent`.)

### Task 6: `check-anchors.py` reads the tree — G1 over specs, plans and ADRs; G3

**Files:**
- Modify: `scripts/check-anchors.py` (`audit`, `parse_header`, `main`; `REGISTRY_REL`, `REGISTRY_ROW`,
  `parse_registry` removed; new `adr_head`, `anchored_slugs`)
- Modify: `scripts/mutations/check-anchors.json`
- Modify: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` and
  `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` — the `Anchor:` header only, to `dev-speed`
- Modify: `scripts/gen-backlog-page.py` (`registry_anchors` → reads the tree), `scripts/mutations/gen-backlog-page.json`

**Interfaces:**
- Consumes: `parse_features`, `current_slugs`, `resolve`, `Node.proposed` (S1); `ROOTS`, `DEPENDS`,
  `parent_errors` in `scripts/gen-backlog-page.py`
- Produces: `audit(docs, nodes, subdirs=SUBDIRS, cutoff=CUTOFF, floor=FLOOR, roots_text="") -> list[str]`;
  `adr_head(text: str) -> int` (the number of lines before the first `## ` heading, or the whole file);
  `anchored_slugs(docs: pathlib.Path) -> dict[str, list[str]]` (node slug → repo-relative paths of the specs,
  plans and ADRs anchored to it); in `scripts/gen-backlog-page.py`, `node_slugs() -> set[str]` replacing
  `registry_anchors`

Rules kept unchanged: the header is required on living specs and plans (the cutoff), every `ADR:` number
resolves to a file, the floor of 22 headed documents. Rule dropped: every registry entry is claimed by a
document. ADR files are read for G1 only — never required to carry a header, never counted toward the floor.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | header names a current slug | spec, plan or ADR, any date | passes |
| 2 | header names a `was:` slug | `Anchor: dev-speed-first` | fails; the message contains "renamed to `dev-speed`" |
| 3 | header names an unknown slug | — | fails as not a node |
| 4 | header names a `proposed:` node | spec or plan | fails: a name awaiting the owner's pick cannot anchor a document (spec §2.7) |
| 5 | ADR header below line 10 | header at each of lines 8–13 | all six read |
| 6 | ADR with no `## ` heading | — | read whole |
| 7 | ADR with no header | — | no problem |
| 8 | a dated-before-cutoff spec with a bad header | — | fails (G1 is any date) |
| 9 | node with no document | `browse-the-library` | no problem (dropped rule) |
| 10 | `ROOTS` key not a current slug | — | fails (G3) |
| 11 | a `DEPENDS` root that is neither a row number nor a current slug | — | fails (G3) |
| 12 | backlog `epic:` naming a `was:` slug | — | `parent_errors` returns the row; the message names `docs/features.md` |
| 13 | `docs/features.md` unreadable or malformed | — | `CANNOT RUN`, exit 2 |

- [ ] **Step 1:** cases `G1: a current slug passes in a spec, a plan and an ADR`,
  `G1: a was: slug fails and names the current slug`, `G1: an unknown slug fails`,
  `G1: a proposed node cannot anchor a document`, `G1: ADR headers at lines 8 to 13 are all read`,
  `G1: an ADR with no ## heading is read whole`, `G1: an ADR without a header is fine`,
  `G1: an old spec with a bad header still fails`, `a node with no document is fine`,
  `G3: a ROOTS key must be a current slug`, `G3: a DEPENDS root must be a row or a current slug`,
  `the tree unreadable is CANNOT RUN`; in `scripts/gen-backlog-page.py`,
  `parent_errors: an epic naming a former slug is refused` and the existing `epic: nope` case with its
  message re-pointed.
- [ ] **Step 2:** red. **Step 3:** implement; re-point the two observed-reach headers in the same commit.
  `main` prints how many ADR headers it read.
- [ ] **Step 4:** green: `python3 scripts/check-anchors.py --self-test`, `python3 scripts/check-anchors.py`,
  `python3 scripts/gen-backlog-page.py --self-test`, `python3 scripts/check-features.py`.
- [ ] **Step 5:** mutations: the current-slug test; the "renamed to" branch; the `proposed` refusal; the
  ADR window (`adr_head` replaced by `HEAD_LINES`); `docs/adr` dropped from the G1 directories; the
  `DEPENDS` clause. The five existing entries are rebound, not deleted. Then W1–W6 for both scripts.
- [ ] **Step 6:** commit.

**FAILS IF:** the number `main` prints for ADR headers read differs from
`git grep -l -E '^> \*\*Anchor:\*\*' -- docs/adr | wc -l`; or
`git grep -n -F 'Anchor:** `dev-speed-first`' -- docs/superpowers` prints a line.

### Task 7: `anchors:` leaves the grammar; documents attach by node slug

**Files:**
- Modify: `scripts/check-features.py` (`FIELD_NAMES`, `LIST_FIELDS`, `Node`, `check_nodes`, `check_cross`,
  `kind_problems`, `main`; `anchor_slugs` and `ANCHORS_MD` removed), `scripts/mutations/check-features.json`
- Modify: `scripts/gen-features-page.py` (`collect`, `anchor_documents`; `anchor_adrs`, `ANCHOR_ROW` removed;
  the declared input list), `scripts/mutations/gen-features-page.json`
- Modify: `docs/features.md` (every `anchors:` line removed; the preamble's account of the registry rewritten)
- Modify: `scripts/check-fixture-variation.py` — `check_cross.anchors_declared` (and any other key whose
  parameter this task removes) out of `EXAMINED_KEYS` in this commit (W5), with its manifest (W4)

**Interfaces:**
- Consumes: `anchored_slugs` (Task 6), `node_slugs` (Task 6), `Node.adrs`
- Produces: `check_cross(nodes: list[Node], areas_in_use: set[str]) -> list[str]` (the three anchor rules
  gone); `kind_problems(text: str, slugs: set[str]) -> list[str]`; `Node` without `anchors`;
  `check_nodes` called from `main` with the live `anchored` set

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | an `anchors:` line in the tree | — | refused as an unknown field, the message naming `adrs:` and the `Anchor:` header as what replaced it |
| 2 | a `built` node whose only fragment is an anchored document | `share-and-download` on the live tree | passes through `main` (the call site, not only `check_nodes`) |
| 3 | the same node when its documents are absent | fixture without the document | the no-fragment problem |
| 4 | a node's ADR links on `/features` | `adrs: 0003` | the ADR section lists ADR-0003 with its file's title |
| 5 | a node's documents on `/features` | a spec anchored to the node | listed under the node — and under no other |
| 6 | the summary line | — | counts nodes and backlog areas; no anchor count |
| 7 | `docs/anchors.md` absent | fixture without it | both scripts run; neither reads it |

- [ ] **Step 1:** cases in `scripts/check-features.py`: `anchors: is no longer a field`,
  `main: a built node with only an anchored document passes`, `main: without its document it is refused`,
  `cross: areas are still claimed exactly once`, `summary line names no anchor count`; the three removed
  anchor-rule cases are deleted with their mutations. In `scripts/gen-features-page.py`:
  `collect: ADRs come from the node's adrs`, `collect: documents attach by the node's own slug`,
  `collect: runs with no registry file`.
- [ ] **Step 2:** red. **Step 3:** implement both scripts and the `docs/features.md` edit in one commit —
  `gen-features-page.py` loads `Node`, so they cannot land apart.
- [ ] **Step 4:** green: both self-tests, `python3 scripts/check-features.py`,
  `python3 scripts/regen-pages.py --self-test`.
- [ ] **Step 5:** mutations: the live `anchored` argument replaced by `frozenset()` at the call site (reddens
  `main: a built node with only an anchored document passes`); the slug key of `anchor_documents`; the
  `n.adrs` loop. Entries whose clause was deleted are removed and named in the commit message. Then W1–W6.
- [ ] **Step 6:** commit.

**FAILS IF:** `git grep -n -E '^anchors:' -- docs/features.md` prints a line, or
`git grep -n -E 'anchor_slugs|ANCHORS_MD|anchor_adrs' -- scripts` prints a line.

### Task 8: `/goals` reads the tree

**Files:**
- Modify: `scripts/gen-goals-page.py` (`collect`, `render_goal`, `build`; `REGISTRY_ROW`, `parse_registry`
  removed), `scripts/mutations/gen-goals-page.json`
- Modify: `scripts/check-fixture-variation.py` — the `parse_registry.text` entry under `gen-goals-page.py` in
  `EXAMINED_KEYS` is removed IN THIS COMMIT, re-derived by `analyse()` (W5), with its manifest
  `scripts/mutations/check-fixture-variation.json` re-anchored (W4). Leaving it to Task 10 would put
  `python3 scripts/check-fixture-variation.py` red between the two commits.

**Interfaces:**
- Consumes: `parse_features`, `Node.adrs`, `Node.purpose`; `anchored_slugs` (Task 6)
- Produces: `goal_nodes(nodes, anchored) -> list[Node]` — in this slice the nodes that have an anchored
  document or an `adrs:` line, in tree order (C5); `collect(docs, gen_text, nodes)`

The card set is deliberately today's set by another route: `/goals` gains a card per node, laid out as the
tree, in Task 19. Here it changes only where its names, sentences and ADRs come from.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | a node with a document | — | a card; its sentence is the node's `for:` |
| 2 | a node with `adrs:` and no document | — | a card listing the ADRs |
| 3 | a node with neither | — | no card in this slice |
| 4 | a document anchored to an unknown slug | — | the page build REFUSES, naming the document |
| 5 | the `ROOTS`/`DEPENDS` band | `stable-blob-addressing` | rendered as today |

- [ ] **Step 1:** cases `cards: a node with a document`, `cards: a node with only adrs`,
  `cards: a bare node has none yet`, `cards: a document anchored to no node refuses the build`,
  `band: the ROOTS relation still renders`.
- [ ] **Step 2:** red. **Step 3:** implement. **Step 4:** green;
  the page builds FROM THIS CHECKOUT: `python3 scripts/gen-goals-page.py --out "$(mktemp -d)/goals.html"`
  exits 0, and `python3 scripts/check-page-links.py --build --ci` exits 0 (it runs the checkout's own
  generators). Never `regen-pages.py --page`: its `fresh` builds from `origin/master`, so an unmerged
  generator is not what it runs (r1 Codex Major).
- [ ] **Step 5:** mutations: the `goal_nodes` filter's two terms, severed singly; the refusal. Then W1–W6.
- [ ] **Step 6:** commit.

**FAILS IF:** the set of card slugs on the page `python3 scripts/gen-goals-page.py --out` builds from this
checkout differs from {nodes with an anchored document} ∪ {nodes with `adrs:`}, each side computed from the
tree and the documents.

### Task 9: The armed set is derived (G4)

**Files:**
- Modify: `scripts/check-goal-status.py` (`ARMED_ANCHORS` deleted; new `UNARMED`, `armed`; `main`),
  `scripts/mutations/check-goal-status.json`

**Interfaces:**
- Consumes: `anchored_slugs` (Task 6), `parse_features`, `current_slugs`
- Produces: `UNARMED = ("dev-speed", "harness-ships-elsewhere")` — today's two unarmed anchors under their
  current names (spec §6 Q6); `armed(anchored: dict[str, list[str]], unarmed=UNARMED) -> tuple[str, ...]`;
  `stale_exemptions(unarmed, slugs: set[str]) -> list[str]`

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | a node with an anchored document | — | armed |
| 2 | an exempt node | in `UNARMED` | not armed; a missing status WARNS |
| 3 | a node with no document | — | not in the set (nothing to check) |
| 4 | an `UNARMED` entry that is not a current slug | — | fails: a stale exemption |
| 5 | the live tree | — | the armed set equals the 13 slugs the deleted tuple held (compared once, in the pull request, against the base's tuple) |

- [ ] **Step 1:** cases `armed: every anchored node`, `armed: an exemption is not armed`,
  `armed: a stale exemption fails`, `armed: two trees give two sets`.
- [ ] **Step 2:** red. **Step 3:** implement; `verdict` keeps its signature. **Step 4:** green:
  `python3 scripts/check-goal-status.py` exits 0.
- [ ] **Step 5:** mutations: the subtraction of `UNARMED`; the stale-exemption test. The seven existing
  entries are rebound. Then W1–W6.
- [ ] **Step 6:** commit, with the comparison of behaviour 5 in the message.

**FAILS IF:** `git grep -n -F 'ARMED_ANCHORS' -- scripts` prints a line.

### Task 10: The remaining readers stop naming the registry

**Files:**
- Modify: `scripts/explainer-serve.py` (`PAGE_SOURCES["features"]` → `docs/features.md`, `docs/backlog.md`;
  the comment's "three whole files"), `scripts/mutations/explainer-serve.json`
- Verify (no edit): `scripts/check-fixture-variation.py` no longer holds `parse_registry.text` — Task 8 removed
  it with the function it pins; if any other registry-named key remains, it is removed here with its manifest
- Modify: `scripts/check-publishability.py` (the self-test fixtures that spell the registry's path take
  another file name, the asserted tuples following), `scripts/mutations/check-publishability.json`
- Modify: `.claude/hooks/regen-goals-page.sh`, `.claude/hooks/regen-features-page.sh` (the `case` arm and
  the comments)

**Interfaces:**
- Consumes: nothing new
- Produces: nothing new

- [ ] **Step 1:** run each of the three self-tests at the task's base and keep the counts.
- [ ] **Step 2:** make the edits. No case is added: these are removals, and the gate is the search of Task 11.
- [ ] **Step 3:** green: `python3 scripts/explainer-serve.py --self-test` (its every-source-is-a-real-file
  case), `python3 scripts/check-fixture-variation.py --self-test`, `python3 scripts/check-fixture-variation.py`,
  `python3 scripts/check-publishability.py --self-test`, `python3 scripts/check-hook-commands.py`.
- [ ] **Step 4:** W1–W6 for the three scripts; a fixture rename can unbind an anchor, so W4 is not optional.
- [ ] **Step 5:** commit.

**FAILS IF:** any of the three self-tests reports fewer cases than at Step 1.

### Task 11: Delete `docs/anchors.md`; the prose; ADR-0016 accepted; the search

**Files:**
- Delete: `docs/anchors.md`
- Modify: `docs/adr/0016-names-live-in-one-node-tree.md` (status → accepted, naming this slice's pull request)
- Modify: the prose that names the registry — `docs/dev-process.md` (the `check-anchors.py` row),
  `docs/portable-practices.md`, `docs/process-checklists.md`, `docs/roadmap-to-launch.md`, `docs/adr/README.md`,
  `.agents/skills/dashboard/SKILL.md`, `docs/memory/anchor-name-and-stable-id-handoff.md`,
  `docs/marketplace/experiment-tier-a.md`, `docs/marketplace/experiment-tier-b.md`
- Modify: `docs/roadmap-to-launch.md` and `docs/backlog.md` status ticks for this slice; the dashboard entry

**Interfaces:**
- Consumes: Tasks 5–10
- Produces: nothing new

- [ ] **Step 1:** delete the file and edit the prose. Each sentence is re-pointed to what is true now
  ("a node in `docs/features.md`"), never just emptied.
- [ ] **Step 2:** run the slice's whole-tree search. BOTH commands must print nothing:

  ```
  H="':!docs/reviews' ':!docs/superpowers' ':!docs/explainers' ':!docs/dashboard-entries.md' \
     ':!docs/backlog.md' ':!docs/marketplace/*.json' ':!docs/adr/0016-names-live-in-one-node-tree.md'"
  eval git grep -n -F -- 'anchors.md' -- . $H
  eval git grep -n -E -- "'parse_registry|registry_anchors|ANCHORS_MD|anchor_slugs'" -- . $H
  ```

  A printed line is a reader nobody listed: fix it in this task, with its manifest. Stage the deletion first —
  `git grep` reads the index and the working tree, so an unstaged deletion still counts as present.
- [ ] **Step 3:** run the retired-slug search and classify every line it prints into one of FIVE classes; any
  other STRUCTURED use is a defect:

  ```
  for s in dev-speed-first harness-speed; do git grep -n -F -- "$s" -- . ':!docs/reviews'; done
  ```

  1. a `was:` entry in `docs/features.md`;
  2. a quoted request line (`> YYYY-MM-DD HH:MM "…"`) in `docs/goal-threads.md`;
  3. history (the paths *Global Constraints* names);
  4. a self-test fixture (`scripts/goal-tree.py`'s);
  5. **the S2 exception, exactly one line:** `## GOAL dev-speed-first` in `docs/goal-threads.md`. It is a
     structured use and is ALLOWED here only because S3 owns it — Task 13 re-points it and Task 16's search
     has no such exception. Check it is the only one:
     `git grep -n -E '^## GOAL (dev-speed-first|harness-speed)$' -- docs/goal-threads.md` prints exactly one
     line, the `dev-speed-first` heading (r1 Codex Minor).
- [ ] **Step 4:** every `python3 scripts/check-*` step of `.github/workflows/ci.yml`, taken from the file;
  `python3 scripts/explainer-serve.py --self-test`; the page build of *Global Constraints*.
- [ ] **Step 5:** commit; the *Before every push* list; mark the pull request ready.

**FAILS IF:** either command of Step 2 prints a line; or Step 3 prints a line outside its five classes, or
class 5 holds more than its one line; or an `Anchor:` in a spec, plan or ADR does not resolve
(`python3 scripts/check-anchors.py`); or `python3 scripts/explainer-serve.py --self-test` is red.

---

## Slice S3 — goals become nodes

Spec: §2.3, §2.4, §2.5 (G2, G5), §2.7, §4.3, §5.1 S3 row, §5.2. Before the first edit, record the thread
count per goal — at this plan's base it is 144 lines:

```
awk '/^## GOAL/{s=$3} /^- /&&s{c[s]++} END{for(k in c)print k,c[k]}' docs/goal-threads.md | sort
```

| `## GOAL` at `2ea4a5e8` | Threads | Heading after S3 |
|---|---|---|
| `guard-harness-audit` | 22 | `guard-and-gate-harness` |
| `comprehensibility-suite` | 33 | unchanged |
| `compaction-guards` | 1 | `hooks-and-session-continuity` |
| `dashboard-decisions` | 7 | unchanged |
| `token-usage-first` | 29 | `token-usage` |
| `dev-speed-first` | 43 | `dev-speed` |
| `product` | 1 | unchanged |
| `memory-hygiene` | 1 | unchanged |
| `harness-ships-elsewhere` | 7 | unchanged |

### Task 12: The tree's data — trunks get slugs, the goal-only names, the remaining `was:`

**Files:**
- Modify: `docs/features.md`

**Interfaces:**
- Consumes: the grammar of Task 1; G6 (Task 2)
- Produces: the nodes `product`, `platform`, `dev-infrastructure`, `token-usage`, `memory-recall`,
  `memory-hygiene`, `comprehensibility-suite`, `dashboard-decisions` — 45 nodes in all

Edits, each from the spec's §4 row; every NEW purpose sentence is copied from §4 verbatim.

| Row | Edit |
|---|---|
| 4.1, 4.13, 4.23 | under each `## ` heading a `slug:` line (`product`, `platform`, `dev-infrastructure`) and the row's `for:` sentence; no `state:` |
| 4.25 | new `###` node `token-usage`; `was: token-usage-first`; no `state:`, no area |
| 4.26, 4.27 | new `###` node `memory-recall`, and `####` node `memory-hygiene` beneath it; no `state:`, no area |
| 4.30 | `guard-and-gate-harness` gains `was: guard-harness-audit` |
| 4.33 | `hooks-and-session-continuity` gains `was: compaction-guards` |
| 4.36, 4.37, 4.42 | new `###` node `comprehensibility-suite` with `areas: (comprehensibility)`, no `state:`; `status-visibility` and `explanation-on-demand` move beneath it to `####`; `status-visibility` loses the `comprehensibility` area |
| 4.38–4.41 | `feature-map`, `goal-tree`, `work-lines` move to `#####` under `status-visibility`; new `#####` node `dashboard-decisions` beside them, no `state:` |
| 4.39 | `goal-tree`'s `for:` loses its localhost URL (C6) |

- [ ] **Step 1:** make the edits.
- [ ] **Step 2:** `python3 scripts/check-features.py` exits 0 and prints 45 nodes; count independently:
  `grep -c -E '^#{3,6} ' docs/features.md` plus `grep -c '^slug: ' docs/features.md` equals 45.
- [ ] **Step 3:** `python3 scripts/gen-features-page.py --self-test`, `python3 scripts/check-anchors.py`,
  `python3 scripts/check-goal-status.py`, and the page build, all exit 0. `status-visibility` now passes the
  fragment rule through its anchored documents alone — the path Task 7 wired.
- [ ] **Step 4:** commit.

Every insertion and every re-levelling is a MOVE of whole blocks, as in Task 5 (r1 F3): a `###` inserted
above a run of `####` blocks adopts them. Before Step 1, save the `(slug, parent)` pairs with Task 5's
`pairs` function; after the edits, diff them. The ONLY changed pairs allowed are the ones the table above
names: the eight new nodes, `status-visibility` and `explanation-on-demand` (under `comprehensibility-suite`),
and every level-3 node under a trunk
that gains a `slug:` (its parent goes from `None` to the trunk's slug).

The exact expected diff, in Task 5's form (`… | grep '^[<>]'`), so the pass condition can be met (r2 Codex
Minor): REMOVED — none (this task renames no slug; `token-usage-first`, `guard-harness-audit` and
`compaction-guards` were never node slugs, they enter as `was:` entries only). ADDED — one `>` line per new
node: the three trunks with parent `None`; `token-usage`, `memory-recall`, `comprehensibility-suite` with parent
`dev-infrastructure`; `memory-hygiene memory-recall`; `dashboard-decisions status-visibility`. CHANGED — a `<`
and a `>` line for the same slug, and only: `status-visibility` and `explanation-on-demand` (`None` →
`comprehensibility-suite`); every other `###` under a trunk, `dev-speed` included (`None` → the trunk's slug).
UNCHANGED, so printing nothing although they move to `#####`: `feature-map`, `goal-tree`, `work-lines` (their
parent is still `status-visibility`), and every `####` whose `###` parent stays. Before Step 1, write the
expected `<`/`>` lines into a file, derived from this paragraph and the pre-edit `pairs` output, and `diff` it
against the actual: any difference fails.

**FAILS IF:** the parent diff shows a pair outside that list; or the node count is not 45; or a `for:` sentence the spec marks NEW differs from the spec's text;
or `grep -c -E '^state:' docs/features.md` is not 45 minus the 11 stateless nodes (the three trunks,
`dev-speed`, `token-usage`, `memory-recall`, `memory-hygiene`, `comprehensibility-suite`,
`dashboard-decisions`, `cloud-publishing`, `serve-money-guard` — C4).

### Task 13: G2 — headings, `also`, `PRIORITY` and answer keys name a node; the headings re-pointed

**Files:**
- Modify: `scripts/check-features.py` (new `ALSO_FIELD`, `PRIORITY_LINE`, `thread_name_problems`,
  `answer_key_problems`; `main`), `scripts/mutations/check-features.json`
- Modify: `docs/goal-threads.md` — FOUR heading lines, per the table above, and the grammar bullets of its
  preamble; no request line and no thread line changes
- Modify: `docs/goal-tree-answers.json` — any `goal:<old-slug>` key moves to the current slug (none at this
  plan's base)

**Interfaces:**
- Consumes: `GOAL_HEADING`, `REQUEST` (Task 3); `current_slugs`, `resolve` (Task 2)
- Produces: `ALSO_FIELD` (the pattern for the optional ` · also <slug>, <slug>` field, placed before
  ` · waits on `); `PRIORITY_LINE` (the pattern for
  `PRIORITY YYYY-MM-DD "<words>" · <slug> > <slug>…`); `thread_name_problems(text: str, nodes) -> list[str]`;
  `answer_key_problems(answers_text: str, nodes) -> list[str]`; `priority_order(text: str) -> tuple[str, str, list[str]] | None`
  (date, words, slugs)

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | heading names a current slug | — | passes |
| 2 | heading names a `was:` slug | `## GOAL dev-speed-first` | fails, naming `dev-speed` |
| 3 | heading names nothing known | — | fails |
| 4 | `also` slug not current | ` · also nope` | fails, naming the line |
| 5 | `also` naming the line's own primary | — | fails: a thread is not shared with its own heading |
| 6 | a request quoting a retired slug | the four existing lines | NOT read; passes |
| 7 | `PRIORITY` slug not current | — | fails |
| 8 | `PRIORITY` above the first heading only | a second line, or one inside a goal | fails |
| 9 | answer key `goal:<was-slug>` | — | fails, naming the current slug |
| 10 | answer key `backlog-5` / `pr-20` | thread keys | not read as names |
| 11 | a heading with a `proposed:` node | — | passes (work may hang under a proposed name) |
| 12 | answers file missing or not JSON | — | `CANNOT RUN`, exit 2 |

- [ ] **Step 1:** cases `G2: a heading must be a current slug`, `G2: a former heading names its node`,
  `G2: an also slug must be current`, `G2: also may not name the primary`,
  `G2: a request quoting a retired slug is not read`, `G2: a PRIORITY slug must be current`,
  `G2: PRIORITY sits once, in the preamble`, `G2: an answer key on a former slug is refused`,
  `G2: thread keys are not names`, `G2: a proposed node may head threads`,
  `G2: an unreadable answers file is CANNOT RUN`.
- [ ] **Step 2:** red. **Step 3:** implement, then re-point the four headings.
- [ ] **Step 4:** green; then the count: the per-goal command above prints the same nine numbers under the
  new headings, summing to the number recorded before the slice. `git diff --stat` on `docs/goal-threads.md`
  shows four changed heading lines plus the preamble.
- [ ] **Step 5:** mutations: the current-slug test for headings; for `also`; for `PRIORITY`; for answer keys;
  the request-line skip (a mutation that READS quotes must redden behaviour 6's case). Then W1–W6.
- [ ] **Step 6:** commit, listing in the message each old heading, its thread count and the node it became.

**FAILS IF:** the thread count after differs from the count before; or
`git diff origin/master -- docs/goal-threads.md | grep -E '^[-+]> '` prints a line (a request was touched).

### Task 14: `goal-tree.py` reads the tree — `also`, history through `resolve`, a proposed name

**Files:**
- Modify: `scripts/goal-tree.py` (`THREAD_RE`, `parse_thread_line`, `parse_threads`, `ledger_threads`,
  `derive`, `read_log`'s consumers, `needs_from_backlog`'s sibling for proposed names, `main`),
  `scripts/mutations/goal-tree.json`

**Interfaces:**
- Consumes: `parse_features`, `current_slugs`, `resolve`, `ALSO_FIELD`, `Node.proposed` — through
  `_sibling("check-features")`
- Produces: `parse_thread_line(line) -> (thread, None) | (None, why)` where `thread` gains
  `"also": list[str]`; `parse_threads(text: str, nodes=None) -> list[dict]` (with `nodes`, a heading that is
  not a current slug is a problem; without, as today — the self-test's own worlds);
  `resolve_snapshot(snap: dict, nodes) -> dict` (every goal slug in a logged snapshot mapped to its current
  slug, the old one kept as `"then"` when it differs); `needs_from_tree(nodes) -> list[dict]` (one NEEDS YOU
  item per `proposed:` node: "a name awaiting your pick")

Rules changed: "a goal quotes at least one request" is DROPPED (spec §2.2). A goal with threads and no
request is numbered after every requested goal, in tree order. The same-goal duplicate-thread refusal stays.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | `also` parsed | `- fix · PR #5 · x · also token-usage, dev-speed` | `also == ["token-usage", "dev-speed"]`, `what == "x"` |
| 2 | `also` then `waits on` | both fields | both read; `waits` unchanged |
| 3 | `waits on` then `also` | wrong order | refused |
| 4 | a line with neither | every existing line | parsed exactly as today (`key`, `refs`, `what`, `waits`) |
| 5 | a heading that is not a node | with `nodes` | `Malformed`, naming the line |
| 6 | a goal with no request | — | accepted; numbered after the requested ones |
| 7 | a logged snapshot with `dev-speed-first` | pre-rename log | rendered under `dev-speed`; nothing reported unknown |
| 8 | two snapshots differing only by a rename | — | no thread move, no goal added or removed is logged |
| 9 | a ledger entry written before the rename | `goal: token-usage-first` | hung under `token-usage`, no problem |
| 10 | a ledger entry naming an unknown goal | — | a problem on the page, as today |
| 11 | a `proposed:` node | — | one NEEDS YOU item naming it |
| 12 | the tree unreadable | — | `CANNOT RUN`; nothing logged or written |

- [ ] **Step 1:** cases `also: parsed before waits`, `also: after waits is refused`,
  `also: a line without it parses as before` (loops every thread line of a copy of today's
  `docs/goal-threads.md` kept as a fixture literal and compares against the pre-change parse),
  `nodes: a heading that is not a node is refused`, `a goal with no request is numbered last`,
  `history: a pre-rename snapshot resolves`, `history: a rename alone logs no thread move`,
  `ledger: an entry under a former slug hangs under its node`, `ledger: an unknown goal is still a problem`,
  `needs: a proposed name awaits the owner's pick`, `the tree unreadable is CANNOT RUN`.
- [ ] **Step 2:** red. **Step 3:** implement. The self-test fixture that names `dev-speed-first` stays as it
  is — a self-test builds its own world (spec §2.5.1).
- [ ] **Step 4:** green: `python3 scripts/goal-tree.py --self-test`, the page build, and
  `python3 scripts/goal-tree.py --snapshot` run against a scratch copy of a log that holds pre-rename
  snapshots, with no "unknown" in its output.
- [ ] **Step 5:** mutations: the `also` group dropped from `THREAD_RE`; the order rule; the `resolve` call in
  `resolve_snapshot`; the resolve-before-diff ordering (reddens the rename-alone case); the `proposed` filter.
  Then W1–W6. This manifest is the largest in the repository — W4 runs in the DRAFT pull request's sweep as
  well as locally with `--only`.
- [ ] **Step 6:** commit.

**FAILS IF:** a snapshot over a log containing pre-rename snapshots reports any slug as unknown.

### Task 15: `session-state.py` — `--also`, and G5 at the moment of writing

**Files:**
- Modify: `scripts/session-state.py` (`ADD_NEEDS_GOAL`, the `--add` path in `main`, the argument parser),
  `scripts/mutations/session-state.json`

**Interfaces:**
- Consumes: `parse_features`, `current_slugs`, `resolve`, `Node.proposed` (loaded lazily inside the `--add`
  path, so a read-only invocation does not need the tree)
- Produces: `--also SLUG` (repeatable, valid only with `--add`), stored on the entry as `"also": [..]`;
  `goal_refusal(slug: str, nodes) -> str | None` (the refusal text, or `None` when the slug is a current node)

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | `--goal` a current slug | — | added |
| 2 | `--goal` a `was:` slug | `--goal dev-speed-first` | exit non-zero; the message names `dev-speed`; nothing added |
| 3 | `--goal` unknown | — | exit non-zero; the message says how a name is proposed (`proposed:` on a node) |
| 4 | `--goal` a `proposed:` node | — | added |
| 5 | `--also` a current slug, twice | — | both stored, in order |
| 6 | `--also` a `was:` or unknown slug | — | exit non-zero; nothing added |
| 7 | `--also` equal to `--goal` | — | exit non-zero |
| 8 | `--also` without `--add` | — | a stray flag: `CANNOT RUN`, exit 2 (today's rule for `--goal`) |
| 9 | the tree unreadable | — | `CANNOT RUN`, exit 2; nothing added |
| 10 | an entry already in the ledger under a former slug | read, close, re-print | untouched and readable |

- [ ] **Step 1:** cases `G5: a current goal is added`, `G5: a former slug is refused and names its node`,
  `G5: an unknown goal is refused with the way to propose one`, `G5: a proposed node is accepted`,
  `also: stored in order`, `also: a non-current slug is refused`, `also: may not repeat the goal`,
  `also: outside --add is a stray flag`, `G5: the tree unreadable is CANNOT RUN`,
  `an old entry under a former slug is still read`.
- [ ] **Step 2:** red. **Step 3:** implement. The self-test's existing `--goal g` calls run in worlds with
  no tree: give each fixture root a one-node `docs/features.md` through one helper, never by loosening the check.
- [ ] **Step 4:** green. **Step 5:** mutations: the current-slug test; the `proposed` acceptance; the
  `--also` loop's check; the same-as-goal refusal. Then W1–W6.
- [ ] **Step 6:** commit.

**FAILS IF:** `python3 scripts/session-state.py --add x "w" "d" --goal dev-speed-first --thread "fix · PR #1 · x" --after none`
exits 0 in a checkout of this branch (run it against a scratch root, not the live ledger).

### Task 16: `batch-ci.py` — a `tree` union policy for `docs/features.md`

**Files:**
- Modify: `scripts/batch-ci.py` (`UNION_FILES` and the comment above it; `resolve_hunk`'s policy dispatch;
  `postcondition` — the P4 home for `tree`, and a new clause P8; a new pure `_parents`),
  `scripts/mutations/batch-ci.json`

**Interfaces:**
- Consumes: `UNION_FILES`, `resolve_hunk`, `resolve_text`, `postcondition`, `_homes`, `_match`, `SECTION`
- Produces: `UNION_FILES["docs/features.md"] = "tree"` (C7); `NODE_HEADING = re.compile(r"^#{1,6} ")`;
  `_parents(lines: list[str], ident: list) -> list` — for each line, the IDENTITY of the nearest preceding
  heading line with FEWER `#` when the line is itself a heading, else `None`; PURE

**Why not `blocks` as it is (r2 Codex Major).** `SECTION` matches `#` and `##` only, and P4 ("every line sits
under the very heading INSTANCE it sits under in the side it came from") reads its homes through `SECTION`. For
`docs/features.md` the trunks are the only sections, so a merge that lands a `###` above a run of `####` nodes
re-parents them with P4 satisfied — and git does that CLEANLY, with no conflict hunk for `resolve_hunk` to see,
when one branch adds a `###` and the other adds a `####` below it (`_union_violation` then runs `postcondition`
over the clean result, which is the only place it can be caught). Equally, a field line that lands under a
different `###`/`####` heading of the same trunk keeps its `##` home and passes P4. The file's hierarchy is its
meaning, so its union needs a postcondition that reads that hierarchy. This changes `batch-ci.py`, our own
script, beyond the one entry (C7, revised in r2).

**The policy `tree`** is `blocks` for RESOLUTION and `blocks` plus two stricter reads for the POSTCONDITION:
- `resolve_hunk("tree", …)` takes the `blocks` arm unchanged (`if policy in ("blocks", "tree")`) — additions
  only, ours first, an edited base line `Refuse`d by `_added`.
- `postcondition(…, "tree")`: every existing clause, except that P4's homes come from `_homes` with
  `NODE_HEADING` in place of `SECTION` — so a field line must stay under its own node's heading instance — and
  a new clause **P8: every heading keeps its parent.** For each heading line of the result with an identity,
  its `_parents` identity in the result must equal: for a line one side ADDED, its parent in that side; for a
  BASE line, its parent in the base, unless exactly one side changed it, in which case that side's (a
  deliberate re-parenting by one branch survives, as P4 lets a re-sectioning survive); both sides changing it
  is refused (`P8 both sides re-parented a node`). A violation reads
  `P8 a node's parent changed and neither side made that change: <heading>`.
- The prefix cut stays on `SECTION`: it ends at the last `##` of the shared prefix, so every heading after the
  cut has its parent at or after the cut, and every line after it its node heading — no P4 or P8 verdict
  depends on a dropped line. `blocks` and its two files are untouched: P8 and the `NODE_HEADING` home apply to
  `tree` only (the existing `blocks:` and `PC` cases are the witness).

Consequences, unchanged from `blocks`: a node added on each side unions; an edit of a field line inside a
conflicting hunk is refused and the pull request is EJECTED to run alone; an identical addition on both sides
fails P1 and ejects.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | two branches each add a node under one parent | conflicting hunk, through `resolve_text("docs/features.md", …)` | both nodes kept, each with its own fields, ours first; `postcondition(…, "tree")` returns `[]` |
| 2 | both add the SAME node | identical block | P1: EJECTED (the existing bound) — never a silent double |
| 3a | one branch edits a field of an existing node far from the other's added node | a clean merge; `postcondition` over the whole file | `[]`: both changes kept |
| 3b | one branch edits a field line INSIDE the hunk where the other adds a node | conflicting hunk | `Refuse`: ejected, not guessed |
| 4 | both edit the same field line differently | — | `Refuse`: ejected |
| 5 | a base line is missing from the result | — | P3 reports it |
| 6 | the merged file is then parsed | result of 1 | `parse_features` returns no problem and both slugs |
| 7 | path dispatch | the conflicted text of 1, through `resolve_text` with the path `docs/features.md`, and the same text with the path `docs/other.md` | resolved for the first; `Refuse` ("not an append-only file") for the second |
| 8 | a clean merge re-parents a node neither side moved | base `### A`, `#### a1`, `#### a2`, each with field lines; theirs inserts `### B` between `a1` and `a2` (re-parenting `a2` on purpose); ours appends `#### a3` after `a2`. The edits are separated by `a2`'s lines, so `git merge-file` merges cleanly (the case builds the result with it) | P8 names `#### a3` (now under `B`; ours put it under `A`); `a2` follows theirs and is not named. Second input in the same case: ours inserts `#### a3` between `A`'s field lines and `a1` instead — `[]` |
| 9 | a conflicting hunk whose union re-parents | ours adds `### B`, theirs adds `#### a2`, in one hunk under `### A` | `resolve_text` puts `a2` after `B`; P8 ejects it. Reversed sides (ours `#### a2`, theirs `### B`) return `[]` |
| 10 | one side re-parents base nodes on purpose | theirs inserts `### B` above the base `#### a1`, ours adds an unrelated node under another trunk | `[]`: `a1` follows theirs |
| 11 | both sides re-parent one base node differently | ours inserts `### B`, theirs `### C`, each directly above the base `#### a1` | P8: both sides re-parented a node |
| 12 | a field line under another node's heading | one hunk at the end of base `#### a1`'s block: theirs adds the field line `adrs: 0003` to `a1`, ours adds a new `#### o` node; `resolve_text` puts ours first, so `adrs: 0003` lands under `#### o` | P4 names that line under `tree` (EJECTED — the resolver is not taught to place it; an ejection is the safe cost); the SAME four texts under `blocks` return `[]` (the policy scope, and the old blind spot, in one case) |

- [ ] **Step 1:** cases `features union: two added nodes keep their own fields`,
  `features union: the same node added twice ejects`, `features union: a distant edit and an addition both survive`,
  `features union: an edit inside the hunk is refused`, `features union: two edits of one field are refused`,
  `features union: a lost base line is a violation`, `features union: the result parses as a tree`,
  `features union: dispatch is by path`, `tree P8: a clean merge that re-parents a node ejects`,
  `tree P8: a union that re-parents a node ejects`, `tree P8: a one-sided re-parenting survives`,
  `tree P8: both sides re-parenting one node is refused`, `tree P4: a field line keeps its node heading`. Every
  case that resolves a conflict calls `resolve_text` with the path `docs/features.md` — never
  `resolve_hunk("tree", …)` directly — so the policy is reached the way `merge` reaches it. The case
  `the policies: …` that lists `UNION_FILES` gains `("docs/features.md", "tree")`.
- [ ] **Step 2:** red (every case that calls `resolve_text` fails while the entry is absent: it refuses the path;
  every `tree P…` case fails while `postcondition` knows no `tree`).
  **Step 3:** implement `NODE_HEADING`, `_parents`, the `tree` arm of `resolve_hunk`, P4's home choice and P8;
  add the entry; extend `postcondition`'s docstring with P8 and the `tree` home. **Step 4:** green; the existing
  `blocks:` and `PC` cases unchanged.
- [ ] **Step 5:** mutations: the `UNION_FILES["docs/features.md"]` entry removed — `expect` is
  `features union: dispatch is by path` (the case that reaches the policy only through `resolve_text`'s path
  lookup); `"tree"` dropped from `resolve_hunk`'s `blocks` arm (the same case); P8's comparison severed
  (`tree P8: a clean merge that re-parents a node ejects`); P8's one-side-follows rule replaced by "base parent
  always" (`tree P8: a one-sided re-parenting survives`); P8's both-sides refusal severed
  (`tree P8: both sides re-parenting one node is refused`); `_parents`' "fewer `#`" replaced by "any heading"
  (`tree P8: a union that re-parents a node ejects`); P4's `tree` home reverted to `SECTION`
  (`tree P4: a field line keeps its node heading`). Then W1–W6.
- [ ] **Step 6:** commit; the retired-slug search below; the dashboard entry; *Before every push*.

  ```
  for s in dev-speed-first token-usage-first harness-speed guard-harness-audit compaction-guards; do
    git grep -n -F -- "$s" -- . ':!docs/reviews' ':!docs/superpowers' ':!docs/explainers' \
      ':!docs/dashboard-entries.md' ':!docs/backlog.md'; done
  ```

  Every line printed is one of: a `was:` entry in `docs/features.md`; a quoted request in
  `docs/goal-threads.md`; a self-test fixture; ADR-0016. Anything else is fixed here.

**FAILS IF:** the search prints a line outside those four classes.

---

## Slice S4 — the views

Spec: §2.3 (counting), §2.5 (G7, G8), §3, §5.1 S4 row. Old ids are kept as SECOND ids for one release;
removing them is not this plan's work.

### Task 17: One node id and one node link kind

**Files:**
- Modify: `scripts/page_markup.py` (`key_link`; new `node_id`, `NODE_VIEWS`, `second_ids`),
  `scripts/mutations/page_markup.json`

**Interfaces:**
- Consumes: `goal_id`, `feature_id`, `SLUG`, `key_link`
- Produces: `NODE_VIEWS = ("goals", "features", "goal-tree")`; `node_id(slug: str) -> str` returning
  `goal-<slug>`; `key_link("node", slug, view="goals" | "features" | "goal-tree") -> str | None`;
  `second_ids(view: str, slug: str, was: tuple[str, ...] = ()) -> list[str]` — the view's old ids for the slug
  (`goal_id` on `/goals`; on `/features` BOTH the bare `<slug>` that spec §3.5 requires and the `feature_id`
  `f-<slug>` the code emits today; none on `/goal-tree`) and `node_id` of each former slug

The bare `<slug>` id is the approved spec's (§3.5) and is kept although today's code emits `f-<slug>` (C8):
keeping both satisfies the spec and every link the code has written. `frag_id` took the `f-` prefix so that a
node named like a chrome control (`chrome-theme`) cannot share that control's id; a bare id reopens that
collision for one release, so `second_ids` returns NO bare id for a slug that equals a chrome id on the page
(`page_chrome`'s ids), and Task 18's build refuses a duplicate through `check-page-links.py:duplicate_ids`.
Two NODES cannot share an id: G6 (Task 2, behaviours 17–19) refuses every slug pair that would, so
`second_ids` drops nothing for a node-to-node collision (r2 Codex Major). Task 18 adds the build-level case
`ids: no two nodes share an id` over a tree whose slugs come close without colliding (`x`, `fx`, `goal-tree`).

The kinds `goal` and `feature` keep working until Task 21 removes them, so each page moves in its own task.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | each view | `key_link("node", "dev-speed", view=v)` for the three | `/goals#goal-dev-speed`, `/features#goal-dev-speed`, `/goal-tree#goal-dev-speed` |
| 2 | an unknown view | — | raises `ValueError` |
| 3 | `view` omitted for a node | — | raises `ValueError` |
| 4 | a key that is not a slug | `"Dev Speed"` | `None` |
| 5 | second ids | `/features`, slug with two former slugs | the bare `<slug>`, the old `f-<slug>` and two `goal-<was>` ids, no duplicates |
| 6 | a slug equal to a chrome id | `/features`, slug `chrome-theme` | no bare id; `f-chrome-theme` and the `goal-` id only |

- [ ] **Step 1:** cases `key_link: a node on each view`, `key_link: an unknown view raises`,
  `key_link: a node needs a view`, `key_link: a non-slug yields no link`,
  `second_ids: bare, f- and former slugs` (two slugs, so a constant list cannot pass),
  `second_ids: no bare id on a chrome collision`.
- [ ] **Step 2:** red. **Step 3:** implement. **Step 4:** green. **Step 5:** mutations: the view membership
  test; the id prefix; the former-slug loop; the bare id dropped (reddens `second_ids: bare, f- and former
  slugs`); the chrome-collision filter dropped. Then W1–W6. **Step 6:** commit.

**FAILS IF:** `node_id("x")` and the id `scripts/goal-tree.py` emits for a goal section disagree
(the case of Task 20 holds them equal).

### Task 18: `/features` — the shared id, primary counts (G7)

**Files:**
- Modify: `scripts/gen-features-page.py` (`frag_id`, `render_index`, `render_node`, `match_rows`,
  `gaps_html`, `gap_disagreements`, `rendered_gap_counts`), `scripts/mutations/gen-features-page.json`

**Interfaces:**
- Consumes: `node_id`, `second_ids` (Task 17); `Node.parent`; `nearest_claim`,
  `cell_tags` and the `epic:` reader in `scripts/gen-backlog-page.py`
- Produces: `primary_node(row: dict, nodes) -> str` — the row's `epic:` parent when it has one, else the node
  claiming its FIRST area tag (spec §6 Q12); `match_rows(nodes, rows) -> dict[str, dict[str, list]]` with
  `"primary"` and `"shared"` lists per node; `subtree_open(node, matched, by_slug) -> int` (distinct open rows
  under the node)

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | a row with one tag | — | primary under its claimant |
| 2 | a row with two tags | claimants A then B | primary under A; shown under B marked shared, linking to A; counted once |
| 3 | a row with `epic:` and tags | epic names C | primary under C, whatever its tags |
| 4 | a parent's total | a row primary under a child and shared under another child | counted once in the parent |
| 5 | G7 second clause | the sum of primary open counts over all nodes | equals the number of distinct open rows; a build where it does not REFUSES |
| 6 | the card's id | — | `goal-<slug>`; an empty element carries each second id |
| 7 | a former slug | `#goal-harness-speed` | lands on `dev-speed`'s card |
| 8 | a bare old fragment | `#dev-speed`, `#f-dev-speed` | both land on `dev-speed`'s card (spec §3.5: bare `<slug>` is kept) |
| 9 | near-colliding slugs | a tree with `x`, `fx`, `goal-tree` (no `tree`), `a` with `was: y` | the built page has no duplicate id (`check-page-links.py:duplicate_ids` over it returns nothing) — G6 refuses the true collisions before a page is built (Task 2) |

- [ ] **Step 1:** cases `primary: one tag`, `primary: the first tag's claimant`, `primary: epic wins over tags`,
  `G7: a shared row adds nothing to its second node`, `G7: a parent counts distinct rows`,
  `G7: primary counts sum to the distinct open rows` (two fixtures in one case, differing by one shared row),
  `G7: a double count refuses the build`, `ids: goal-<slug> with the old ids kept` (asserts the bare `<slug>`
  AND the `f-<slug>` second ids, at two slugs), `ids: a former slug lands on its node`,
  `ids: no two nodes share an id`.
  NO cross-view link is emitted in this task: `/goals` has no `goal-<slug>` card for every node until Task 19,
  and CI's `check-page-links.py --build --ci` runs `dangling` over the built pages, so a link added here
  would land nowhere until then (r1 Codex BLOCKER). The heading links are Task 21's.
- [ ] **Step 2:** red. **Step 3:** implement. **Step 4:** green;
  `python3 scripts/gen-features-page.py --out "$(mktemp -d)/features.html"` exits 0 and
  `python3 scripts/check-page-links.py --build --ci` exits 0 — both run this checkout's generators, never
  `regen-pages.py`, which builds `origin/master`.
- [ ] **Step 5:** mutations: the `epic:` precedence; the first-tag choice (`[0]` → `[-1]`); the shared rows
  added into the count; the distinct set replaced by a sum; the second-id emission; the bare-slug second id
  dropped from `second_ids`' `/features` arm (reddens `ids: goal-<slug> with the old ids kept`). Then W1–W6.
- [ ] **Step 6:** commit.

**FAILS IF:** on the built page, the sum of the per-node primary open counts differs from
the number of open rows `python3 scripts/gen-backlog-page.py` reads from `docs/backlog.md`.

### Task 19: `/goals` — a card per node, laid out as the tree, with the owner's requests

**Files:**
- Modify: `scripts/gen-goals-page.py` (`goal_nodes`, `collect`, `render_goal`, `build`),
  `scripts/mutations/gen-goals-page.json`

**Interfaces:**
- Consumes: `requests_by_goal` (Task 3), `resolve`, `node_id`, `second_ids`;
  `Node.done`, `Node.was`, `Node.parent`
- Produces: `goal_nodes(nodes, anchored) -> list[Node]` now returning EVERY node in tree order;
  `is_bare(node, anchored, requests) -> bool` (no document, no ADR, no request)

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | every node has a card | the live tree | 45 cards, nested as the tree |
| 2 | a bare node | no document, ADR or request | ONE line: name and purpose (its two links arrive in Task 21) |
| 3 | a node with requests | under its heading in `docs/goal-threads.md` | each request shown with its time, words byte-identical |
| 4 | a request under a former heading | history fixture | shown under the current node |
| 5 | a request copied under two goals | — | shown on each (accepted repetition, spec §2.2) |
| 6 | `done:` | — | shown with its date and words |
| 7 | `was:` | — | former names listed |
| 8 | activity and open-gap counts | — | NOT shown (the links that replace them are Task 21's) |
| 9 | ids | — | `goal-<slug>`, with the old `g-<slug>` kept as a second id |

- [ ] **Step 1:** cases `cards: every node, nested`, `cards: a bare node is one line`,
  `requests: shown verbatim under their node`, `requests: a former heading resolves`,
  `requests: a copied request shows on each node`, `done and was are shown`,
  `cards carry no counts`, `ids: goal-<slug> with g-<slug> kept`.
- [ ] **Step 2:** red. **Step 3:** implement. **Step 4:** green;
  `python3 scripts/gen-goals-page.py --out "$(mktemp -d)/goals.html"` and
  `python3 scripts/check-page-links.py --build --ci`, both from this checkout.
- [ ] **Step 5:** mutations: the `is_bare` terms severed singly; the `resolve` of a request's heading; the
  second id. Then W1–W6. **Step 6:** commit.

**FAILS IF:** the number of cards on the built page differs from the node count `python3 scripts/check-features.py` prints.

### Task 20: `/goal-tree` — shared threads, history under the current name, the PRIORITY line

**Files:**
- Modify: `scripts/goal-tree.py` (`derive`, `_goal_blocks`, `_goal_html`, `render_text`, `agenda_digest`,
  `agenda_html`, `agenda_lines`), `scripts/mutations/goal-tree.json`
- Modify: `docs/goal-threads.md` (the `PRIORITY` line, in the preamble)

**Interfaces:**
- Consumes: `priority_order` (Task 13), `resolve_snapshot` (Task 14), `node_id`, `second_ids` (Task 17)
- Produces: `shared_refs(goals: list[dict]) -> dict[str, list[dict]]` (node slug → the threads that name it in
  `also`, each with its primary); `goal_totals(goal: dict) -> dict` counting DISTINCT refs

The `PRIORITY` line is the owner's words. Take the date and the sentence from the owner's recorded decision
of 2026-11-12 (`docs/memory/owner-priority-order-1102.md` names it; the transcript holds the words). If the
exact sentence cannot be found, STOP and notify — the plan does not supply one. The order it encodes is
`dev-speed > token-usage`; nodes not named are unordered (spec §3.4).

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | a thread with `also` | — | full under its primary; ONE line under each `also` node, marked shared, linking to the primary |
| 2 | counts under an `also` node | — | unchanged by the shared thread |
| 3 | one ref on two lines under one goal's subtree | — | counted once (G7) |
| 4 | a history entry under a former slug | — | drawn under the current node, with "then: `<old>`" once |
| 5 | a node with no thread, ledger entry or request | — | listed by name only, carrying its `node_id` (Task 21's links land on it) |
| 6 | section id | — | `node_id(slug)`; each former slug has a second id, so `#goal-dev-speed-first` lands on `dev-speed` |
| 7 | `PRIORITY` present | — | first line of the agenda: date, words, the order as links; identical in `--print` and on the page |
| 8 | `PRIORITY` absent | — | the agenda as today; no empty line |
| 9 | a node with `done:` and an open thread | — | SHOWN, flagged on the agenda (spec §6 Q9) |

- [ ] **Step 1:** cases `also: one reference line under each other node`, `also: adds nothing to that node's counts`,
  `G7: a ref on two lines counts once`, `history: then: the old name, once`, `a quiet node is listed by name`,
  `ids: the section id is node_id`, `ids: a former slug lands on its node`, `ids: a quiet node has its id`,
  `agenda: PRIORITY leads, same words in print and page`, `agenda: no PRIORITY, no line`,
  `agenda: a done node with an open thread is flagged`.
- [ ] **Step 2:** red. **Step 3:** implement; add the line to `docs/goal-threads.md`. **Step 4:** green;
  `python3 scripts/check-features.py` (G2 reads the new line) and the page build.
- [ ] **Step 5:** mutations: the shared thread added to the count; the distinct set; the "then" condition;
  the PRIORITY branch in `agenda_lines`; the done-and-open flag. Then W1–W6. **Step 6:** commit.

**FAILS IF:** `python3 scripts/goal-tree.py --print` and the built page disagree on the PRIORITY line's text.

### Task 21: Two-way links on all three views; G8 — one id, one link function; the old kinds removed

**Files:**
- Modify: `scripts/check-page-links.py` (`check_sources`, `check_pages`, `fragment_targets`, `dangling`),
  `scripts/mutations/check-page-links.json`
- Modify: `scripts/page_markup.py` (the `goal` and `feature` kinds of `key_link` removed),
  `scripts/mutations/page_markup.json`
- Modify: `scripts/gen-features-page.py`, `scripts/gen-goals-page.py`, `scripts/goal-tree.py` — each node's
  heading gains its two links to the other views, built by `key_link("node", slug, view=…)`; each with its manifest
- Modify: every remaining caller of the two kinds, each with its manifest

The links land HERE, after Tasks 18–20 gave every node its `node_id` on all three pages, so no commit holds a
link whose target is not yet built (r1 Codex BLOCKER: CI's `check-page-links.py --build --ci` runs `dangling`
over the built `/goals` and `/features`; `/goal-tree` is not built in CI, so its links are checked by the local
`--build` of Step 4).

**Interfaces:**
- Consumes: `node_id`, `NODE_VIEWS`, `second_ids`, `key_link("node", …)`
- Produces: `node_id_problems(pages: dict[str, str], nodes) -> list[str]` — on each of the three pages, every
  current slug has exactly one element with id `node_id(slug)`

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | a node element with another id | a card with `id="g-x"` and no `goal-x` | fails (G8) |
| 2 | a node href built by hand | a literal `/goals#goal-` in a generator's source | fails, naming the file |
| 3 | an old fragment | `#g-<slug>`, `#f-<slug>`, `#goal-<was-slug>` | lands (second ids) |
| 4 | a fragment that lands nowhere | — | fails, as today |
| 5 | a slug with two `goal-` elements on one page | — | fails (`duplicate_ids`) |
| 6 | `key_link("goal", …)` | — | raises: unknown kind |
| 7 | heading links, each of the three pages | — | two links per node, to the same `goal-<slug>` id on the other two views, both from `key_link`; each lands |
| 8 | a bare node on `/goals` | — | its one line carries the two links |

- [ ] **Step 1:** cases `G8: a node element must carry goal-<slug>`, `G8: a hand-built node href is refused`,
  `G8: the old fragments still land`, `G8: a dangling node fragment fails`,
  `G8: one goal- id per slug per page`; in `scripts/page_markup.py`, `key_link: goal and feature are gone`
  (replacing the two cases that assert the old hrefs); in each of the three generators,
  `links: each heading links the other two views` (asserts both hrefs at two slugs, and that each parses).
- [ ] **Step 2:** red. **Step 3:** implement; find the remaining callers with
  `git grep -n -E 'key_link\("(goal|feature)"' -- scripts .agents .claude` and move each.
- [ ] **Step 4:** green: the five self-tests; `python3 scripts/check-page-links.py --sources`;
  `python3 scripts/check-page-links.py --build --ci` (the CI gate); and the local `--build`, which also builds
  `/goal-tree` — all from this checkout's generators, never `regen-pages.py`.
- [ ] **Step 5:** mutations: the id comparison; the source scan's node-href pattern; the per-page loop over
  `NODE_VIEWS`; in each generator, one view's link dropped from the heading (reddens that generator's
  `links:` case). Then W1–W6. **Step 6:** commit; the dashboard entry; *Before every push*.

**FAILS IF:** `git grep -n -E 'key_link\("(goal|feature)"' -- scripts .agents .claude` prints a line; or
`python3 scripts/check-page-links.py` reports a fragment that does not land on the regenerated pages.

---

## Slice S5 — vocabulary

### Task 22: `CONTEXT.md`, the suite spec's §4, and the backlog rows

**Files:**
- Modify: `CONTEXT.md` — a "node" entry (a named heading in `docs/features.md` with a purpose sentence; goals,
  features and anchors are all nodes); the `Anchor:` header keyword defined as "the node a document belongs
  to", kept distinct from the mutation term "anchor" already defined there (spec §6 Q7)
- Modify: `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` — §4's goal-facet registry
  re-pointed to the node tree, by a dated note; the rest of the document is history and is not rewritten
- Modify: `docs/backlog.md` — backlog #644 and backlog #472 closed as dissolved by this work, each naming the
  slice that dissolved it; ONE new row filed for spec §6 Q5 (area tags for `token-usage` and `memory-recall`),
  under an area a node already claims
- Modify: `docs/roadmap-to-launch.md` — the step ticked; `docs/features.md` preamble if any sentence still
  describes three lists

**Interfaces:**
- Consumes: nothing
- Produces: nothing

- [ ] **Step 1:** make the edits.
- [ ] **Step 2:** every `python3 scripts/check-*` step of `.github/workflows/ci.yml`, taken from the file —
  not a subset; then `python3 scripts/gen-backlog-page.py --self-test`.
- [ ] **Step 3:** commit; then `python3 scripts/check-dashboard-entry.py` and confirm it says an entry block
  was added; *Before every push*.

**FAILS IF:** `python3 scripts/check-backlog-closure.py` warns about either row; or `python3 scripts/check-features.py`
refuses the new row's area.

---

## Human steps

| When | What | Why it is the owner's |
|---|---|---|
| Task 20 | the exact words and date of the `PRIORITY` line, if the record does not yield them | a quote is the owner's; the plan supplies none |
| any task | a `HOLD` from `scripts/check-merge-ready.py --pr <N>` | the house rule: READY merges, a HOLD is verified line by line and goes to the owner |

## Before every push

Run from the slice's worktree, and read each exit code directly (never after a pipe):
`python3 scripts/check-docs.py` · `python3 scripts/check-reference-namespace.py --base origin/master` ·
`python3 scripts/check-doc-citations.py --base origin/master` · `python3 scripts/check-fixture-variation.py` ·
`python3 scripts/check-selftest-counts.py --changed` · `python3 scripts/check-ratchet-contract.py` ·
`python3 scripts/check-review-recorded.py` · `python3 scripts/check-dashboard-entry.py` (after the commit) ·
`python3 scripts/gen-backlog-page.py --self-test` when `docs/backlog.md` changed. Push with an explicit
refspec: `git push origin HEAD:refs/heads/<branch>`, as its own command.

---

## Choices the spec left open

Each is a mechanical reading, not a new decision; a reviewer who disagrees raises it as a finding.

| # | The spec says | This plan does |
|---|---|---|
| C1 | "`was:` — optional list of former slugs" and writes it as `was: dev-speed-first, harness-speed` (§5.1) | `was:` and `adrs:` are bare comma lists — `was: dev-speed-first, harness-speed`, `adrs: 0001, 0005` — the one list grammar `parse_features` has (`anchors:` uses it); the parentheses of `areas:` belong to each `(area)` tag and are not a list form (r1 F1) |
| C2 | "a trunk is a node with a slug" (§2.2); "an added slug line, not a rename" (§5.1 S3) | the `## ` heading keeps its display text; a `slug:` field line beneath it makes it a node (Task 1) |
| C3 | "heading depth `##` to `######`" and "§4 needs five levels on one branch" | `######` is accepted and unused; a skipped level is refused |
| C4 | §4.4 counts "Nodes with no `state:` — 9", while §6 Q13's answer is "no state on all four until you say built" | 11 stateless nodes: the nine plus `cloud-publishing` and `serve-money-guard` (§6.1 governs) |
| C5 | S2: "`gen-goals-page.py` … read the tree"; §3.1: "It becomes a card per node" | S2 keeps today's card set, derived as nodes with a document or an `adrs:` line (Task 8); the card per node arrives with the views in S4 (Task 19) |
| C6 | row 4.39: `goal-tree`'s purpose is "unchanged, minus its URL" — no slice is named | Task 12 (S3), with the other §4 data edits of that branch |
| C7 | "`batch-ci.py` gains a conflict resolver for `docs/features.md`" — no policy is named | a new policy `tree`: the `blocks` RESOLUTION unchanged (additions union; an in-hunk edit or an identical addition EJECTS the pull request to run alone — r1 Codex Major), with a stricter POSTCONDITION — P4 homes at any heading level and a clause P8, every heading keeps its parent unless exactly one side moved it — because `SECTION` sees only `#`/`##` and a clean merge can re-parent nodes (Task 16; r2 Codex Major). `blocks` itself is unchanged |
| C8 | G8 and §3.5 call today's feature id "bare `<slug>`" | the code emits `f-<slug>` (`feature_id` in `scripts/page_markup.py`); `/features` keeps BOTH as second ids — the bare `<slug>` the approved spec requires and the `f-<slug>` the code has emitted — except no bare id where it would equal a chrome id (Task 17; r1 Codex Major). Two nodes whose ids would meet (`x` with `f-x`; `x`, or a former `x`, with `goal-x`) are refused by G6, never resolved by dropping an id (Task 2; r2 Codex Major) |
| C9 | S1's row lists two scripts, and G9 reads request lines whose grammar `scripts/goal-tree.py` owns | the two patterns MOVE to `scripts/check-features.py` and `scripts/goal-tree.py` aliases them in S1 (Task 3) — a third script touched by two lines, in place of a second copy of a grammar |
| C10 | S1: "A `built` node's fragment may be … an anchored document" | the RULE lands in S1 (`check_nodes` takes the set); the live set is passed in S2 Task 7, once `anchored_slugs` exists in `scripts/check-anchors.py` — S1 has no node that needs it |
| C11 | §3.2: "A node that claims no area and inherits none" | "inherits" is read as: some ancestor node claims an area (Task 4) |
| C12 | Q6: "minus a short named exemption list — today's 2 unarmed anchors" | `UNARMED = ("dev-speed", "harness-ships-elsewhere")`: the two registry anchors absent from `ARMED_ANCHORS`, under their current names |
| C13 | §3.4 writes `PRIORITY 2026-11-12 "<the owner's words>" · dev-speed > token-usage > …` | the line carries a date with no time, as written; its words are a human step if the record does not hold them |
| C14 | §6 Q5: a follow-up backlog row "not in this work" | the row is FILED in S5 (Task 22); nothing in it is built |

## Self-review notes

- **Spec coverage.** §2.2 → Tasks 1, 2, 5, 7, 12. §2.3 → Tasks 13, 14, 15, 18, 20. §2.4 → Tasks 2, 6, 13, 14, 15.
  G1 → 6; G2 → 13; G3 → 6; G4 → 9; G5 → 15; G6 → 2; G7 → 18, 20; G8 → 17, 21; G9 → 3. §2.7 → Tasks 1, 6, 14, 15.
  §3.1 → 19; §3.2 → 4, 18; §3.3 and §3.4 → 20; §3.5 → 17, 21. §4 → Tasks 5 and 12. §5.1.1 → Tasks 10, 11.
  §5.2 → Tasks 13, 14. §6 Q5 → 22; Q6 → 9; Q7 → 22; Q9 → 20; Q10 → 5; Q11 → 1, 6, 14, 15; Q12 → 18; Q13 → 5, 12.
- **Not covered, stated:** removing the second ids after one release; area tags for `token-usage` and
  `memory-recall` (filed, not built); the hand-kept `case` lists of the regen hooks and `PAGE_SOURCES`
  (backlog #710, spec §5.1.1).
- **Ordering inside S2.** Task 5 adds data while the registry is still read; Task 6 moves the header guard to
  the tree and re-points the two documents in the same commit; Task 7 removes `anchors:` from both scripts
  that share `Node`; Task 8 drops `parse_registry` and its `EXAMINED_KEYS` pin in one commit; Task 11 deletes
  the file last. Each commit is green on its own.
- **Ordering inside S4 (r1).** Tasks 18–20 give each page its `node_id` and second ids and emit NO cross-view
  link; Task 21 adds every heading's two links once all three pages carry the targets. Page checks run this
  checkout's generators (`gen-*-page.py --out`, `check-page-links.py --build --ci`), never `regen-pages.py`.
- **Counts typed in this plan** (48 and 18 search lines, 144 threads, the nine per-goal counts) were measured
  at `2ea4a5e8` with the commands printed beside them, and each task re-measures at its own base.

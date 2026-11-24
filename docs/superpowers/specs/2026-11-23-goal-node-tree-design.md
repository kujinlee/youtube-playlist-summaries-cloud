# One tree of named nodes — goals, features and goal-tree goals become one list with three views

> **Anchor:** `status-visibility` — **ADR:** 0010, 0016
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** ✅ approved — the owner walked every ✍ row of §4 and every question of §6 on 2026-11-23 21:03–21:22 (`docs/explainers/2026-11-23-brief-goal-node-tree-spec-walkthrough.html`) and approved "with your answers"; each answer is the recommendation or proposal this spec already carries, so no design text changed (§6.1 lists them). Drafted 2026-11-23 from the owner's decisions of 16:02–16:38; review rounds 1, 2 and 3 FOLDED (`docs/reviews/coordinator/goal-node-tree-spec-r1-coordinator.md`, `-r2-coordinator.md`, `-r3-coordinator.md`); round 3 CONVERGED; the migration (§5.1) redesigned by `docs/reviews/architecture-review-2026-11-23-goal-node-tree-migration.md`.

Why this anchor: the three pages this spec re-bases (`/goals`, `/features`, `/goal-tree`) are the pages
of `status-visibility`, and the document it amends
(`docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`) is anchored there. `feature-map`
was the other candidate; it names one of the three pages, not all of them.

## In plain words

The project keeps three lists of names for "a thing we are working toward or have built": 15 anchors,
9 goal-tree goals and 35 feature nodes. They overlap, they disagree about spelling, and each has its
own page. The owner settled on 2026-11-23 that these are ONE kind of thing — a name with a purpose
sentence, under which documents, activity and bugs hang — and that the names form ONE tree.

This spec says where that tree lives (the file that is a tree today, `docs/features.md`), what a node
carries, how each page becomes a view of it, and — the part to walk through — where each of the 59
existing names goes.

## The owner's decisions this spec designs within (settled, not reopened)

Recorded in the in-flight ledger entry `goal-unify` and the selection-card answers of 2026-11-23 16:11,
16:18 and 16:35. The author did not hear them; they are RECORDED, relayed by the coordinator.

| # | Decision |
|---|---|
| D1 | "goal" has one meaning: a NAME, with a purpose sentence, under which artifacts, activity and bugs are linked |
| D2 | Features are the same kind of thing. One hierarchical tree of named nodes replaces the three lists |
| D3 | Three views of the one tree: `/goals` = definition; `/features` = capability and gaps; `/goal-tree` = activity and history, with the agenda on top as the dashboard |
| D4 | `-first` leaves the slugs (`dev-speed`, `token-usage`); the priority ORDER lives in the agenda |
| D5 | An item (PR, backlog row, thread) may hang under several nodes: one PRIMARY plus others, counted once |
| D6 | No finite/standing kinds. A node has an optional "built" mark and an optional "done" mark, the second set only on the owner's word |
| D7 | `memory-recall` is a node the owner names; it exists in no list today |
| D8 | The `/features` tree index, gap counts and folded cards arrive by a separate change and are built on, not redone |

## 1. Problem — measured at `fa11456f`, 2026-11-23

Every number here was produced by running the named command or reading the cited line in this
worktree. §7 lists which are measured and which are inferred.

**Three name lists, three readers, three guards.**

| List | Names | Read by | Guarded by | Page, element id |
|---|---|---|---|---|
| `docs/anchors.md` | 15 anchors | `scripts/gen-goals-page.py` | `scripts/check-anchors.py` | `/goals`, `g-<slug>` (`scripts/page_markup.py:167`) |
| `docs/goal-threads.md`, `## GOAL` headings | 9 goals | `scripts/goal-tree.py:273` (`parse_threads`) | the same parser, at snapshot time | `/goal-tree`, `goal-<slug>` (`scripts/goal-tree.py:2878`) |
| `docs/features.md` | 35 nodes in 3 trunks | `scripts/check-features.py:41` (`parse_features`) | `scripts/check-features.py` | `/features`, bare `<slug>` (`scripts/gen-features-page.py:447`) |

A fourth, hard-coded list exists: `ARMED_ANCHORS` in `scripts/check-goal-status.py:89` names 13 of the
15 anchors by hand. Nothing in that script reads the registry, so a renamed anchor leaves it silently
stale.

**The lists overlap and disagree.**

- Of the 9 goal-tree goals, 2 share a slug with an anchor (`dev-speed-first`, `harness-ships-elsewhere`).
  The other 7 exist in no other list. `comprehensibility-suite` (33 threads, 13 owner requests) is the
  project's second-busiest goal and has no `/goals` card and no `/features` node.
- Of the 15 anchors, 12 share a slug with a feature node; 3 do not (`cloud-publishing` sits under
  `summarise-a-playlist`, `serve-money-guard` under `spend-control`, `dev-speed-first` under
  `guard-and-gate-harness`).
- `guard-and-gate-harness` (feature) declares the anchor `dev-speed-first`, while the goal that the
  owner's request names that feature for is `guard-harness-audit` — three names, two lists apart.
- `harness-ships-elsewhere` is an anchor, a goal, and a feature node whose `state:` is `absent`.
- `memory-recall` is in none. 12 backlog rows have a title naming recall, a memory file or the memory
  index (10 open); they are spread over 5 area tags and no node claims them as its own.

**One piece of work under several names cannot be said.**

- `docs/goal-threads.md` holds 144 thread lines under 9 goals and 44 request lines. 4 refs are already
  declared under more than one goal (PR #421, PR #422, PR #557, backlog #384), each as a separate
  thread, so each is shown — and counted — once per goal.
- 27 backlog rows carry more than one tag (23 open).
- `parse_threads`, called on the living file at `fa11456f`, REFUSED it: `line 229: thread fix · PR #376
  is declared twice in goal harness-ships-elsewhere`. The cause was a MIS-TYPED REF, not a grammar gap:
  plan Task 16 merged as PR #613 (`36deefc9`), and PR #376 is the marketplace-inventory spec, correctly
  listed at line 226 (the duplicate came in with #613's own commit). Line 229 now names PR #613 — fixed
  in this branch. Measured in a scratch clone: `goal-tree.py --snapshot --page --out <file>` exited 1
  `MALFORMED` before the fix and rendered the page after it. This is NOT evidence for the `also` field;
  the 4 cross-goal refs above are.

**The names are spelled differently, with a priority baked in.** `dev-speed-first` and
`token-usage-first` carry an ordering word in the name. LINES naming a `-first` slug in living files
(`git grep -c`, so lines, not occurrences): 8 in `docs/dashboard-entries.md` (9 occurrences); 6 in
`docs/goal-threads.md` — 2 `## GOAL` headings and 4 copies of one QUOTED owner request (lines 35, 86,
150, 169), which are never rewritten (§2.4); 2 in the observed-reach spec and 1 in its plan (both
`Anchor:` headers); and 1 each in `scripts/goal-tree.py` (a self-test fixture, line 5014),
`docs/features.md`, `docs/backlog.md` and `docs/anchors.md`. More in frozen files under
`docs/reviews/`. 8 of 1830 commit subjects on `origin/master` contain `-first`.

**History holds the old names.** The main checkout's git-ignored `.claude/goal-tree-log.jsonl` holds
358 snapshots, each embedding every goal's slug (`dev-speed-first` in 295, `token-usage-first` in 320).
No pull request can rewrite a git-ignored file in someone's checkout, so a rename has to be resolved
when history is READ.

**The three pages cannot point at one another by name.** Three id schemes (table above) and one link
function (`scripts/page_markup.py:179`, `key_link`) that sends `goal` to `/goals#g-<slug>` and has no
way to reach the same name on `/goal-tree`. Links that depend on the old schemes are few: 3
occurrences of a `/features#<slug>` link in 2 files and 1 of `/goals#g-` in 1 file, under `docs/`,
`scripts/`, `.agents/` and `.claude/commands/`.

**The built mark says little.** 31 of 35 feature nodes say `built`, 4 say `absent`
(`check-features.py`'s own summary line). The node that matters to the owner today is distinguished
by its open gaps, which the heading does not show. That is D8's change, not this spec's.

## Prior art

`python3 scripts/prior-art.py anchors.md goal-threads.md features.md parse_threads "goal slug"` —
3528 documents scanned.

| Found | What it settled | What this spec does with it |
|---|---|---|
| `docs/adr/0010-documents-declare-their-anchor.md` | A document declares its anchor; the registry holds names, not state; "a name, once allocated, does not change" (line 35) | KEPT: the header, the derived index, names-not-state. CHANGED by proposed ADR-0016: where the names live, and that a name can be renamed if the old one is recorded |
| `docs/superpowers/specs/2026-09-19-feature-hub-design.md` §"The spine: a feature tree, not the anchor registry" | The registry was rejected as the spine because it mixes product features, platform properties and dev tooling; a feature node NAMES its anchors, one way | Its conclusion (the tree is the spine) is kept and finished: the anchor stops being a second thing a node points at and becomes the node |
| `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` §3, §4 | One question per page; four closed facets, the goal facet's registry being `docs/anchors.md` | §4's goal-facet registry becomes the tree. Page roles are unchanged except that `/goals` and `/features` now show the same nodes |
| backlog #644 ("one piece of work has one name"), owner card A: the anchor name wins | Measured then: 14 of 15 anchored nodes used a different name; 11 were renamed. Left open: anchor-inside-node pairs, `guard-and-gate-harness` vs `guard-harness-audit`, the comprehensibility names, a check that names agree | DISSOLVED by this spec: its four open parts are rows of §4 and the guard of §2.5 |
| backlog #472 (every feature node resolves a goal anchor; `/goals` and `/features` link both ways) | Open | DISSOLVED: a node is its own goal; §3 gives the two-way link |
| backlog #394 (`epic: <anchor>` parents on backlog rows; the owner's decision R4) | `gen-backlog-page.parent_errors` requires the parent to be in the registry. In use today on 2 rows (`epic: corrections-in-cloud`, `epic: status-visibility`) | KEPT as the backlog's one MEMBERSHIP edge; the parent must be a tree node. ADR-0010's sentence "the backlog gets no header and no new column … a second would be a duplicate mechanism" (ADR-0010, *Scope*) was overtaken by backlog #394; ADR-0016 records that supersession. `ROOTS`/`DEPENDS` is not membership: it is an ORDERING relation to a root (survives / blocked-by / dissolved-by), kept, and its key and root values must be nodes (G3) |
| backlog #363, #389 (goal tree; work lines retired into it) | The goal tree is the activity page | KEPT |
| `CONTEXT.md:140` | "Anchor" is defined there as a MUTATION anchor | The collision backlog #472 noted stays; §6 Q7 asks whether to add the entry now |

Searched for and NOT found: any existing alias or rename mechanism for slugs (`was:`, "renamed to",
"formerly" as a parsed field) in `scripts/` — a rename has never been recorded by machine.

## 2. Data model

### 2.1 Where the tree lives — three options

| Option | What it costs | What it buys | Verdict |
|---|---|---|---|
| A. Extend `docs/features.md` | 4 new fields in one parser; nodes without a state; a deeper heading level | It is a tree today; its guard has 54 self-test cases and a mutation manifest; it holds non-product nodes today (the DEV INFRASTRUCTURE trunk) | **Recommended** |
| B. Extend `docs/anchors.md` | A flat table has to grow a parent column; 35 nodes' fields move into table cells; `check-anchors.py` learns everything `check-features.py` knows | Keeps ADR-0010's file name | Rejected: it rebuilds the tree grammar in a table, and the feature-hub spec rejected this file as the spine for a reason that still holds |
| C. A new file | A third grammar, a third guard, both old files migrated | A neutral name | Rejected: new machinery where an existing mechanism serves the concern |

Recommendation: **A**. `docs/features.md` becomes the one name list; `docs/anchors.md` is deleted in the
slice that moves its ADR column into the tree; `docs/goal-threads.md` keeps threads and requests and
stops allocating names. One guard, `scripts/check-features.py`, owns the node set. Whether the FILE
should then be renamed is §6 Q1 (recommended: no).

### 2.2 Per-node fields

A node is a heading plus fields at column 0, one line each — today's grammar, extended.

| Field | Today | Proposed | Notes |
|---|---|---|---|
| slug | the heading text | unchanged | lowercase words joined by `-`; unique across the WHOLE tree |
| parent | heading depth (`##` trunk, `###`, `####`) | heading depth `##` to `######`; a trunk is a node with a slug | §4 needs five levels on one branch; see ✍ row 4.38 |
| `for:` | mandatory purpose sentence | unchanged | this is D1's purpose sentence; the status-word ban (`scripts/check-features.py:13`) stays |
| `adrs:` | — (the registry's second column) | optional list of ADR numbers | moves from `docs/anchors.md` |
| `state:` | mandatory, `built` or `absent` | OPTIONAL: `built`, `absent`, or omitted | D6's "built" mark. Omitted means the node is a name only — an aim such as `dev-speed` |
| `expected-because:` | mandatory when `absent` | unchanged | |
| `done:` | — | optional: `done: YYYY-MM-DD HH:MM "<the owner's words>"` | D6. A recorded owner decision, quoted and dated like a request; never derived. A node with `done:` and an open thread is SHOWN as such, not refused |
| `was:` | — | optional list of former slugs | the rename record; see §2.4 |
| `areas:` | list of backlog area tags | unchanged | how a backlog row finds its primary node |
| `anchors:` | list of registry slugs | REMOVED (S2) | the node is the name; nothing is left to point at. ⚠ It is today one of the two FRAGMENTS a `built` node must name (`scripts/check-features.py:141-144`), and `gen-features-page.py:312` attaches a node's ADRs and documents through it. Measured: 4 built nodes have `anchors:` as their ONLY fragment (`share-and-download`, `cloud-sync`, `serve-path-bounding`, `cloud-blob-key-encoding`), and `status-visibility` loses its only area to 4.36. So S2 redefines a fragment as `areas:`, `adrs:`, or a document whose `Anchor:` is the node, and attaches documents by the node's own slug |

`done:` and names-not-state: ADR-0010's principle forbids a central file holding state that DRIFTS —
a value that changes as work happens without the file being edited. `done:` is an event with a date
and the owner's words, the same kind of line as `expected-because:` and as a request. It does not
drift; it is either recorded or not.

**Owner requests** stay where they are: `> YYYY-MM-DD HH:MM "<words>"` lines under the node's heading
in `docs/goal-threads.md`, interleaved with the threads they caused (44 today). `/goals` DERIVES a
node's requests from there. They are not copied into the tree file: one home per fact, and the tree
grammar is one-line fields with no dated events. The rule "a goal has at least one request" is
dropped — a node needs none to exist. §6 Q2.

A request is a QUOTE: never rewritten, by a rename or anything else (§2.4). 3 requests are copied
under more than one goal today (one of them under 4); after the migration each copy stays under the
node its goal became, and `/goals` shows it on each — the repetition is accepted and stated, since a
request is the owner's words, not an item D5 counts. Ordering on `/goal-tree`: a node is numbered by
its first request's time, as today (`docs/goal-threads.md:12-13`); a node with threads but no request
is numbered after every requested node, in tree order.

### 2.3 Threads, and work under several nodes (D5)

`docs/goal-threads.md` keeps its grammar with two changes.

1. `## GOAL <slug>` no longer ALLOCATES a name. The slug must be a tree node. The heading is the
   PRIMARY node of every thread beneath it.
2. A thread gains one optional field, before `waits on`:

   ```
   - <relation> · <refs> · <what>[ · also <slug>, <slug>][ · waits on <what>]
   ```

   `also` lists the OTHER nodes the thread serves. Measured: 0 of the 144 living thread lines
   contain ` · also `, so no existing line changes meaning.

Counting is by ITEM — a PR or a backlog row, D5's unit — not by line. A thread is counted where it is
primary. Under an `also` node it is SHOWN, marked as shared with a link to its primary, and adds
nothing to that node's counts. A parent's totals are the DISTINCT refs over its subtree, so a ref on
two lines under one parent counts once there.

A thread LINE is a work record — relation, description, `waits` — and is never merged to dedupe a ref.
Measured: the 4 refs declared under more than one goal today are DISTINCT records, not one record
copied. PR #421 is `bookkeeping` (backlog #383 filed, line 51) under `guard-harness-audit` and `fix`
(the tag parser, line 63) under `comprehensibility-suite`; PR #422 likewise (lines 46, 64); PR #557
carries two descriptions (lines 57, 208); backlog #384 three, one with a `waits` (lines 66, 170, 227).
All 10 lines STAY, each under the node its goal becomes (§4). `also` is for one record that serves
several nodes, written from now on; no existing line is rewritten into it. No §4 merge puts two of
these lines under ONE node, so the parser's same-goal duplicate refusal (`scripts/goal-tree.py:312`)
is not tripped by the migration.

The same shape everywhere an item names a node:

| Item | Primary | Others |
|---|---|---|
| thread | the heading it sits under | `· also <slug>, …` |
| in-flight ledger entry | `session-state.py --add --goal <slug>` | new `--also <slug>` (repeatable) |
| backlog row | ✍ §6 Q12: its `epic: <slug>` parent if it has one (backlog #394), else the node claiming its FIRST area tag (nearest claim). Today a row with several tags is shown under the claimant of EACH (`docs/features.md:15-17`) and has no primary; 27 rows carry several tags (23 open) | the claimants of its other tags, shown as shared |
| document | its `Anchor:` header | none — a document has one home (ADR-0010) |

### 2.4 Renames — `was:`

ADR-0010 made a name permanent. D4 renames two (`dev-speed-first`, `token-usage-first`), and §4
retires three more into other nodes (`harness-speed`, `guard-harness-audit`, `compaction-guards`) —
5 `was:` slugs, subject to the owner's ✍ answers on 4.24, 4.30 and 4.33. The proposed rule (ADR-0016):
a slug MAY change if the node records the old one in `was:`.

- In a LIVING source — a STRUCTURED field that names a node: an `Anchor:` header, a `## GOAL` heading,
  an `also` field, a backlog `epic:`, a `ROOTS` key or root, a `goal:<slug>` answer key, a `PRIORITY`
  slug, a new ledger `--goal`/`--also`, a script constant — a `was:` slug FAILS, with the message
  naming the current slug. The rename is therefore finished in the pull request that makes it. §2.5.1
  enumerates these sources and how they were found.
- A QUOTE is never rewritten and never checked: an owner request line (`> <date> "…"`) in
  `docs/goal-threads.md`, and the quoted words of a `done:` line, are the owner's record. Measured: 4
  `goal-threads.md` lines quote `dev-speed-first` and `token-usage-first` inside one request (lines 35,
  86, 150, 169); they stay as written, and the page shows them under the current node.
- In HISTORY — a `.claude/goal-tree-log.jsonl` snapshot, a `.claude/inflight.jsonl` entry written
  before the rename, a frozen file under `docs/reviews/`, a commit subject — a `was:` slug RESOLVES to
  its node, through one function (`resolve(slug)` beside `parse_features`). The pages show history
  under the current name. `resolve()` is for READING history only; a check of a new value (G1–G5) asks
  "is this a CURRENT slug", never "does this resolve".
- A slug is unique across current slugs AND every `was:` list, so a retired name can never be
  re-allocated to mean something else.

### 2.5 The guard — one name, or the build fails

`scripts/check-features.py` owns the node set. Every use of a name resolves against it.

| # | Rule | FAILS IF |
|---|---|---|
| G1 | Every `Anchor:` header names a node | ANY spec or plan (`docs/superpowers/specs`, `docs/superpowers/plans`) or ADR (`docs/adr`), of ANY date, carries an `Anchor:` slug that is not a current node slug (a `was:` slug fails with "renamed to"). Today's R2 already checks every header in specs and plans regardless of date (`scripts/check-anchors.py`; the cutoff decides only whether a header is REQUIRED, R1); ADRs are not read at all today (`SUBDIRS` holds the two `superpowers` dirs, and `DATED` never matches `0016-…`), though 6 carry a header (0011–0016). S2 adds `docs/adr` to the directories G1 reads; the cutoff keeps governing R1 only. ⚠ An ADR's header sits BELOW its title and status block, at lines 8–13 (measured: 0011 at 12, 0012 at 9, 0013 at 11, 0014 at 11, 0015 at 13, 0016 at 8), and `parse_header` reads `HEAD_LINES = 10` (`scripts/check-anchors.py:61`) — so read with today's window, G1 would see 2 of the 6 and pass the other 4 unchecked. G1 reads an ADR up to its first `## ` heading (each of the 6 headers precedes it), and a case asserts all 6 are read |
| G2 | Every `## GOAL` heading, every `also` slug, every `PRIORITY` slug and every `goal:<slug>` answer key names a node | `check-features.py` finds one in `docs/goal-threads.md` or `docs/goal-tree-answers.json` that is not a current slug. Request lines are quotes and are not read (§2.4) |
| G3 | Every backlog `epic:` parent, every `ROOTS` key and every `DEPENDS` root names a node | `gen-backlog-page.parent_errors`, fed the tree's slugs, returns a row; or a `ROOTS` key or a root named in `DEPENDS` (`scripts/gen-backlog-page.py:617-645`) is not a current slug |
| G4 | No script keeps its own name list | `ARMED_ANCHORS` still exists in `scripts/check-goal-status.py` (Q6's recommendation: derive and delete it). If the owner keeps a hand list instead, the rule becomes: one of its strings is not a current slug. "Any tuple of slugs" is NOT a rule — no detector can recognise one; §2.5.1 is the enumeration it would need |
| G5 | A NEW ledger entry's goal is a node | `session-state.py --add --goal X` or `--also X` exits non-zero when X is not a CURRENT slug — a `was:` slug is refused, naming its node; `resolve()` is used only to read entries written before a rename. Today the flag is checked only for being blank. ✍ §6 Q11: this collides with the owner's rule for a goal that does not exist yet (§2.7) |
| G6 | Slugs are unique, including retired ones | a slug occurs more than once in the COMBINED list of every node's current slug and every entry of every `was:` list — that is, two nodes share a slug, a `was:` entry equals a current slug, or one former slug is listed twice (in one `was:` list or two). A `was:` entry that occurs once and is no current slug PASSES: that is a rename, the case G6 exists to permit. Review r2 found the earlier wording ("a slug appears in any `was:` list") refused every rename; the walk of each `was:` slug through this rule is in `docs/reviews/coordinator/goal-node-tree-spec-r2-coordinator.md` |
| G7 | A node is counted once | on any rendered page, a parent's open-gap or thread total differs from the number of DISTINCT refs under it; or the sum of PRIMARY open-gap counts over all nodes differs from the number of distinct open backlog rows (the second clause catches two siblings counting one row, which the first cannot) |
| G8 | One id, one link function | a page emits a node element whose id is not `goal-<slug>`, or builds a node href outside `page_markup.key_link`. Today `key_link` has two node kinds, `goal` (`g-<slug>`) and `feature` (`/features#<slug>`, `scripts/page_markup.py:979`); both fold into one kind with a `view` |
| G9 | `done:` is the owner's | a `done:` line lacks a date-time and a quoted sentence, or its date-time and words do not equal a request line under that node in `docs/goal-threads.md` (so the mark cites the owner's recorded words rather than an agent's sentence). Bound: it proves the words are recorded, not who said them |

Kept from `check-anchors.py` unchanged: the header is required on living specs and plans, every `ADR:`
resolves to a file, the floor of 22 headed documents. Its "every registry entry is claimed by a
document" rule is DROPPED — it was a rule about a list of anchors; most nodes (a feature such as
`browse-the-library`) have no spec and need none.

G2 and G5 change what is caught WHEN: an unknown goal on a ledger entry is reported today on the
rendered page, after the fact (`scripts/goal-tree.py:350`, `ledger_threads`); it becomes a refusal at
the moment it is written — subject to §6 Q11.

#### 2.5.1 Where a slug is written — the enumeration the guard reads

Found by grepping each name that changes, not by recall. Command, per slug, at the branch's base
(`fa11456f`) plus this spec:

```
for s in dev-speed-first token-usage-first harness-speed guard-harness-audit compaction-guards; do
  git grep -c -F -- "$s" -- . ':!docs/reviews'; done
```

| Slug | Files (lines) outside `docs/reviews/` |
|---|---|
| `dev-speed-first` | `docs/anchors.md` 1, `docs/backlog.md` 1, `docs/dashboard-entries.md` 8, `docs/features.md` 1 (`anchors:` line), `docs/goal-threads.md` 5, observed-reach spec 2 (`Anchor:` header + prose), observed-reach plan 1 (`Anchor:` header), `scripts/goal-tree.py` 1 (self-test fixture), this spec |
| `token-usage-first` | `docs/dashboard-entries.md` 1, `docs/goal-threads.md` 5, this spec |
| `harness-speed` | `docs/features.md` 1 (its heading), this spec |
| `guard-harness-audit` | `docs/backlog.md` 3, `docs/dashboard-entries.md` 1, `docs/goal-threads.md` 5, this spec |
| `compaction-guards` | `docs/backlog.md` 2, `docs/dashboard-entries.md` 1, `docs/goal-threads.md` 1, this spec |

Each hit classified by hand. The `goal-threads.md` hits are 4 `## GOAL` headings (lines 31, 105, 121,
161) and 4 copies of one quoted request; the `backlog.md` hits are prose inside rows 361, 391, 489,
604 and 644 (no `epic:` names them). The search was then widened to every place a slug is written as
a STRUCTURED value, by reading each reader of the three lists (§1) and grepping the field names
(`Anchor:`, `## GOAL`, `epic:`, `ROOTS`, `DEPENDS`, `ARMED_ANCHORS`, `goal:`, `"goal"`):

| Source | Today | Checked by |
|---|---|---|
| `Anchor:` headers in specs, plans, ADRs | 64 specs and plans (63 at the base + this spec) and 6 ADRs (5 at the base + ADR-0016), disjoint. 3 frozen architecture reviews under `docs/reviews/` also carry one and are not read | G1 |
| `## GOAL` headings, `docs/goal-threads.md` | 9 | G2 |
| `also` fields; the `PRIORITY` line | none yet | G2 |
| `goal:<slug>` keys, `docs/goal-tree-answers.json` (read at `scripts/goal-tree.py:2880-2882`; an unmatched key falls to "Older questions") | 0 answers today | G2; a rename moves the key in the same pull request |
| backlog `epic:` | 2 rows | G3 |
| `ROOTS` key and `DEPENDS` roots, `scripts/gen-backlog-page.py:617-645` | 1 key (`stable-blob-addressing`) | G3 |
| `ARMED_ANCHORS`, `scripts/check-goal-status.py:89` | 13 slugs | G4 |
| ledger `goal`/`also`, `.claude/inflight.jsonl` (git-ignored) | per entry | G5 for new; `resolve()` for old |
| `.claude/goal-tree-log.jsonl` (git-ignored) | per snapshot | `resolve()` (history) |
| self-test fixtures (`scripts/goal-tree.py:5014`, `scripts/page_markup.py:978-979`) | 3 | NOT checked: a self-test builds its own world; it is not a living name |
| prose — `docs/backlog.md` bodies, `docs/dashboard-entries.md`, frozen reviews, request quotes, `.claude/agenda-log.jsonl` step text | — | NOT checked: prose and history (§5.2, Q4) |

Bound: this enumerates what the field names and the readers of the three lists show. A future source
that writes a slug under a new field name is not caught until a reader of it is added to this table;
the 5 changing slugs had no hit outside it.

### 2.7 How a name is born — ✍ §6 Q11

Today three routes allocate a name: a row in `docs/anchors.md`, a `## GOAL` heading, a `###` in
`docs/features.md`. After the change there is one: a node in `docs/features.md`, with a parent and a
`for:` sentence. The owner's rule for work with no fitting goal (backlog #514, 2026-11-05,
`scripts/session-state.py:377-381`) is that the AGENT PROPOSES a name and the OWNER PICKS. Today a
proposed name reaches the page and is shown as a problem (`scripts/goal-tree.py:350`), so the work is
recorded before the owner has picked.

G5 as written would refuse that entry, so the agent would have to write the node first — allocating
the name the owner was to pick. Two shapes, not decided here:

- **(recommended) `proposed: <date-time>` on a node.** An agent may write a node carrying it; `--add`
  accepts it; the agenda shows it under NEEDS YOU as "a name awaiting your pick"; G1 refuses it as an
  `Anchor:` on a spec or plan; the owner's pick deletes the line (or renames the node, `was:`).
- **Keep G5 as a page problem.** `--add` accepts any slug, as today, and `/goal-tree` shows an
  unknown one as a problem. The refusal moves no earlier than today.

### 2.6 Concern → mechanism

| Concern | The one mechanism | What it replaces |
|---|---|---|
| Which names exist | `docs/features.md`, read by `parse_features` | `docs/anchors.md`; `## GOAL` as an allocator; `ARMED_ANCHORS` |
| A name's purpose, ADRs, built, done, former names | fields on its node | the registry's columns |
| What a document belongs to | its `Anchor:` header (ADR-0010, kept) | — |
| Why work exists, and what the owner asked | `docs/goal-threads.md` threads and requests | unchanged |
| Work under several nodes | primary by position, others by `also` / `--also` / `epic:` | — (today's 4 cross-goal lines are distinct records and stay, §2.3) |
| A renamed name | `was:` + `resolve()` | nothing — did not exist |
| Linking to a name | `page_markup.key_link`, id `goal-<slug>` | three id schemes |
| Priority order | the agenda (§3.4) | `-first` in a slug |

**What already does this?** The tree: `scripts/check-features.py:41`. The claim rules:
`scripts/check-features.py:234` (`check_cross`). The thread reader: `scripts/goal-tree.py:333`
(`parse_thread_line`, the one reader for file lines and ledger entries — the `also` field is added
there once). The link function: `scripts/page_markup.py:179`. The parent check:
`scripts/gen-backlog-page.py:1294`. Nothing new is built where one of these serves.

## 3. The three views

All three read the same nodes through `parse_features`. Each node's element id is `goal-<slug>` on all
three pages, and each node heading carries two links: to the same id on the other two pages.

| | `/goals` — DEFINITION | `/features` — CAPABILITY and GAPS | `/goal-tree` — ACTIVITY and HISTORY |
|---|---|---|---|
| Question | What is this name for, and what was decided about it? | What can the system do, and what is open against it? | What is happening under it, and what happened? |
| Shows nodes | every node, as the tree | every node, as the tree (D8's index, folded cards) | nodes that have a thread, a ledger entry or a request; others are listed by name only |
| From the tree file | `for:`, `adrs:`, `done:`, `was:`, parent and children | `state:`, `expected-because:`, `areas:`, `for:` | slug, parent, `done:` |
| Derived | documents whose `Anchor:` is the node (specs, plans, ADRs, with their Status); the owner's requests from `docs/goal-threads.md`; the backlog rows that a `ROOTS`/`DEPENDS` relation ties to the node (the band `scripts/gen-goals-page.py:498` renders today — an ORDERING relation, kept) | open backlog rows by severity (primary per §2.3, others shown as shared), the fragments that define the node | threads and their live state, the timeline, ledger entries |
| Does NOT show | activity; the open-gap COUNTS (it links to them) | decisions, requests | purpose beyond one line, documents |

### 3.1 `/goals`

Today a card per registry anchor (15). It becomes a card per node (§4: 45), laid out as the tree. A
node with no document, no ADR and no request renders as one line — name, purpose, links — so 30 new
cards do not bury the 15 that carry decisions. "Open bugs" stay on `/features`; the card links there.

### 3.2 `/features`

Built on D8's change (the tree index, gap counts by severity beside each state, folded cards), which
this spec assumes has landed. Two differences follow from the model, neither a redesign: a node with
no `state:` shows no state badge, only its gaps; and a parent's count is the distinct set under it
(G7). The index is the tree all three pages share. A node that claims no area and inherits none
(today `token-usage` and `memory-recall`, §6 Q5) shows "claims no area — gaps not counted", never an
empty count: an empty count would read as "nothing open", the very misreading D8 was raised to end.

### 3.3 `/goal-tree`

Sections become nodes. A thread appears under its primary; under each `also` node it appears as a
one-line reference. History entries resolve through `was:` and render under the current name, with
the old name shown once ("then: `dev-speed-first`") where it differs.

### 3.4 The agenda — the dashboard on top of `/goal-tree`

NEEDS YOU, current focus, recent activity: as today, derived. One addition: the PRIORITY ORDER, which
D4 moved out of the slugs. It has to be written down somewhere a machine can read. Proposed: one line
in the preamble of `docs/goal-threads.md`, dated and quoted like a request —

```
PRIORITY 2026-11-12 "<the owner's words>" · dev-speed > token-usage > …
```

— rendered at the top of the agenda; every slug in it must be a node (G2). Nodes not named are
unordered. §6 Q3.

### 3.5 Cross-links and old fragments

`key_link` gets ONE node kind with a `view` (`goals`, `features`, `goal-tree`), replacing today's two
(`goal` → `g-<slug>`, `feature` → `/features#<slug>`), and is the only place a node href is built (G8).
The old element ids are kept as SECOND ids for one release (`g-<slug>`, bare `<slug>`) so the 4
measured in-repo links and any bookmark keep landing; a `was:` slug also gets an id, so
`/goal-tree#goal-dev-speed-first` reaches `dev-speed`. FAILS IF `scripts/check-page-links.py` (the
dangling-fragment check that exists today) reports a fragment that does not land on the regenerated
pages.

## 4. The name mapping — every existing name, and where it goes

Derived from the three files at `fa11456f`: 15 anchors (A), 9 goal-tree goals (G), 35 feature nodes
(F) — 59 names — plus the owner-named `memory-recall` and the 3 trunk headings. They become **45
nodes**. ✍ marks a judgment call the owner decides; the recommendation is what the row shows.

How to read "merged from": A = anchor, G = goal-tree goal, F = feature node. A purpose sentence is the
existing `for:` line unless marked NEW (written for this spec) or (A) (taken from the anchor's
sentence).

### 4.1 PRODUCT

| # | Node | Parent | Purpose | Merged from | Notes |
|---|---|---|---|---|---|
| 4.1 | `product` | — (trunk) | NEW: Turns YouTube playlists into summaries a person can read, keep and share. | trunk heading PRODUCT + G `product` | ✍ a trunk becomes a node with a slug, so the goal `product` (1 thread, 1 request) lands on the trunk instead of becoming a 46th name |
| 4.2 | `summarise-a-playlist` | `product` | Turns every video in a YouTube playlist into a summary a person can read. | F | loses its `anchors: cloud-publishing` line |
| 4.3 | `cloud-publishing` | `summarise-a-playlist` | (A) Summaries are produced and published by a hosted service, not only by a local vault. | A | ✍ NEW CHILD rather than a merge: the anchor is narrower than the node it sat in (backlog #644, part a). `adrs: 0001, 0005`. ✍ `state: built` is the author's claim (§6 Q13). Alternative: merge, with `was: cloud-publishing` — then 2 anchored documents re-point |
| 4.4 | `ingest-a-playlist` | `summarise-a-playlist` | unchanged | F | |
| 4.5 | `magazine-rendering` | `summarise-a-playlist` | unchanged | F | |
| 4.6 | `browse-the-library` | `product` | unchanged | F | |
| 4.7 | `dig-deeper` | `product` | unchanged | F | |
| 4.8 | `dig-job-recovery` | `dig-deeper` | unchanged | F | `state: absent` |
| 4.9 | `corrections-in-cloud` | `product` | unchanged | A + F | same name, one node |
| 4.10 | `share-and-download` | `product` | unchanged | A + F | `adrs: 0003` |
| 4.11 | `shared-dig-deeper` | `share-and-download` | unchanged | F | `state: absent` |
| 4.12 | `cloud-sync` | `product` | unchanged | A + F | `adrs: 0002` |

### 4.2 PLATFORM

| # | Node | Parent | Purpose | Merged from | Notes |
|---|---|---|---|---|---|
| 4.13 | `platform` | — (trunk) | NEW: Keeps the hosted service correct, bounded and affordable underneath the product. | trunk heading PLATFORM | follows from ✍ 4.1 |
| 4.14 | `job-queue-and-worker-lifecycle` | `platform` | unchanged | F | |
| 4.15 | `wake-on-visit` | `job-queue-and-worker-lifecycle` | unchanged | F | |
| 4.16 | `serve-path-bounding` | `platform` | unchanged | A + F | |
| 4.17 | `spend-control` | `platform` | unchanged | F | loses its `anchors:` line |
| 4.18 | `serve-money-guard` | `spend-control` | (A) Serving a summary cannot spend money twice, and the protection is enforced rather than accidental. | A | ✍ NEW CHILD, same reasoning as 4.3: `spend-control` also covers the spend ceiling. `adrs: 0008`. ✍ `state: built` is the author's claim, unchecked: ADR-0008 records a dependency on grant granularity, not a built mechanism (§6 Q13) |
| 4.19 | `stable-blob-addressing` | `platform` | unchanged | A + F | `adrs: 0006, 0007`; stays the one `ROOTS` key |
| 4.20 | `cloud-blob-key-encoding` | `stable-blob-addressing` | unchanged | A + F | `adrs: 0009` |
| 4.21 | `concurrency-safety` | `platform` | unchanged | F | |
| 4.22 | `access-control` | `platform` | unchanged | F | |

### 4.3 DEV INFRASTRUCTURE

| # | Node | Parent | Purpose | Merged from | Notes |
|---|---|---|---|---|---|
| 4.23 | `dev-infrastructure` | — (trunk) | NEW: Makes building this system fast, checked and understandable to its owner. | trunk heading DEV INFRASTRUCTURE | follows from ✍ 4.1 |
| 4.24 | `dev-speed` | `dev-infrastructure` | (A) A change gets its verdict as fast as the evidence allows, with mutation coverage identical. | A `dev-speed-first` + G `dev-speed-first` + F `harness-speed` | ✍ THREE names become one. RENAME per D4; `was: dev-speed-first, harness-speed`. ✍ MERGE of `harness-speed` — its purpose line is the same aim. ✍ NEW PARENT: lifted from under `guard-and-gate-harness` to the trunk, because 43 threads serve it and most are not guards. No `state:` (an aim). Claims area `tooling/speed`. 2 anchored documents re-point |
| 4.25 | `token-usage` | `dev-infrastructure` | NEW: Keeps the tokens agents spend inside the usage limits, so the limit is not what stops the work. | G `token-usage-first` | RENAME per D4; `was: token-usage-first`. ✍ parent: a sibling of `dev-speed`, split out of `harness-speed`'s sentence, which named token usage as one of four things. No `state:`. ✍ no backlog area names it today — §6 Q5 |
| 4.26 | `memory-recall` | `dev-infrastructure` | NEW ✍: Brings the right memory to the turn that needs it. | owner-named, D7 | ✍ the purpose sentence is the author's; the owner's own words for it were not in front of the author. No `state:`. ✍ parent: the trunk, beside `dev-speed` and `token-usage`, the three the owner listed together |
| 4.27 | `memory-hygiene` | `memory-recall` | NEW: Keeps each memory file short and opening with its current rule, so that what is recalled is right. | G `memory-hygiene` | ✍ CHILD of `memory-recall` rather than merged: hygiene is about what a file says, recall about which file is found. Alternative: merge, `was: memory-hygiene` (1 thread, 2 requests). No `state:` (§6 Q13) |
| 4.28 | `prod-smoke` | `dev-infrastructure` | unchanged | A + F | |
| 4.29 | `automated-test-suites` | `dev-infrastructure` | unchanged | F | |
| 4.30 | `guard-and-gate-harness` | `dev-infrastructure` | unchanged | F + G `guard-harness-audit` | ✍ MERGE: the goal is the audit OF this node — the owner's request names it ("guard-and-gate-harness section has very large number of open backlogs"). `was: guard-harness-audit`; its 22 threads and 4 requests move under this heading. Loses `anchors: dev-speed-first` (backlog #644, part b) |
| 4.31 | `review-process` | `guard-and-gate-harness` | unchanged | F | |
| 4.32 | `mutation-and-test-quality` | `guard-and-gate-harness` | unchanged | F | |
| 4.33 | `hooks-and-session-continuity` | `guard-and-gate-harness` | unchanged | F + G `compaction-guards` | ✍ MERGE: the node's sentence names compactions; the goal has 1 thread and 2 requests. `was: compaction-guards`. Alternative: a child node |
| 4.34 | `backlog-and-page-tooling` | `guard-and-gate-harness` | unchanged | F | |
| 4.35 | `guard-soundness` | `guard-and-gate-harness` | unchanged | F | |
| 4.36 | `comprehensibility-suite` | `dev-infrastructure` | NEW: Gives each status and explainer page one question to answer under one design, so the project can be understood from its pages. | G `comprehensibility-suite` | ✍ NEW PARENT over `status-visibility` and `explanation-on-demand` (backlog #644, part c): the owner's request lists both kinds of page. Claims area `comprehensibility`, which moves up from `status-visibility`. No `state:` |
| 4.37 | `status-visibility` | `comprehensibility-suite` | unchanged | A + F | ✍ moves down one level; its anchored documents (23 at the base; 25 with this spec and ADR-0016) keep their header |
| 4.38 | `feature-map` | `status-visibility` | unchanged | A + F | ✍ the FIFTH heading level (§2.2) — the one BRANCH where the tree is five deep (4.38–4.41 all sit at `#####`), a consequence of ✍ 4.36 |
| 4.39 | `goal-tree` | `status-visibility` | unchanged, minus its URL | F | the node is the page as a feature; the name stays. Its `for:` line carries a localhost URL that belongs to the fragments |
| 4.40 | `work-lines` | `status-visibility` | unchanged | F | `state: absent` (retired) |
| 4.41 | `dashboard-decisions` | `status-visibility` | NEW: Shows the owner every decision waiting on them, and what each one is. | G `dashboard-decisions` | ✍ NEW CHILD beside `feature-map` and `goal-tree` — it is the dashboard page's work (7 threads, 2 requests). Alternative: merge into `status-visibility`. ✍ a plainer name (`dashboard`) would be a rename; not recommended. No `state:` (§6 Q13) |
| 4.42 | `explanation-on-demand` | `comprehensibility-suite` | unchanged | A + F | ✍ moves down one level |
| 4.43 | `review-decides-itself` | `dev-infrastructure` | unchanged | A + F | `adrs: 0014`. NOT moved: it and `review-process` (4.31) are close; whether one belongs under the other is §6 Q8 |
| 4.44 | `process-harness` | `dev-infrastructure` | unchanged | F | loses its `anchors:` line |
| 4.45 | `harness-ships-elsewhere` | `process-harness` | unchanged | A + G + F | THREE lists, one name: a clean merge. `adrs: 0015`; `state: absent` stays until it is installed somewhere else |

### 4.4 The mapping, counted

| | Count |
|---|---|
| Names in | 59 (15 A + 9 G + 35 F), + 1 owner-named, + 3 trunk headings |
| Nodes out | 45 |
| Anchors that are a same-name feature node today (merge by name) | 12 |
| Anchors that become a new child | 2 (`cloud-publishing`, `serve-money-guard`) |
| Goals that land on an existing node | 5 (`dev-speed-first`, `harness-ships-elsewhere`, `guard-harness-audit`, `compaction-guards`, `product`) |
| Goals that become a new node | 4 (`comprehensibility-suite`, `dashboard-decisions`, `token-usage`, `memory-hygiene`) |
| Slugs retired into `was:` | 5 (`dev-speed-first`, `harness-speed`, `token-usage-first`, `guard-harness-audit`, `compaction-guards`) |
| Nodes with no `state:` | 9 (3 trunks, `dev-speed`, `token-usage`, `memory-recall`, `comprehensibility-suite`, `memory-hygiene`, `dashboard-decisions`) — §6 Q13 |
| ✍ rows | 14 (4.1, 4.3, 4.18, 4.24, 4.25, 4.26, 4.27, 4.30, 4.33, 4.36, 4.37, 4.38, 4.41, 4.42) |

Nodes that receive a new purpose sentence need the owner's eye: 4.1, 4.13, 4.23, 4.25, 4.26, 4.27,
4.36, 4.41.

## 5. Migration

### 5.1 Order — each step leaves every gate green

**Entry condition: D8's `/features` change has merged.** ⟳ Met 2026-11-23: PR #624
(`features-tree-index`) merged as `e8eab72e`. It builds `render_index` on the two-level `group_tree`
(`group_tree` in `scripts/gen-features-page.py`) and pins 27 mutations. S1 changes depths and trunks, so S1
reworks `render_index` and that pin; starting S1 first would make D8 redo its grouping instead.

| Slice | What changes | Scripts and files touched (each script a two-file edit with its mutation manifest) |
|---|---|---|
| S1 — the tree can hold everything | `parse_features` accepts `adrs:`, `was:`, `done:`, `proposed:` (if §6 Q11 says so), an optional `state:`, heading depths 2–6 and a slug on a trunk; `resolve()`; G6, G9. No name moves. A `built` node's fragment may be `areas:`, `adrs:` OR an anchored document (§2.2), so S2 can drop `anchors:` | `check-features.py`; `gen-features-page.py` (`group_tree` / `render_index` assume two levels, `group_tree` in `scripts/gen-features-page.py`; the 27-entry pin) |
| S2 — the registry folds in | the 15 anchors' ADR columns become `adrs:`; `cloud-publishing` and `serve-money-guard` become nodes; the 4.24 node `dev-speed` is made HERE by RENAMING the `harness-speed` heading and lifting it to the trunk (`was: dev-speed-first, harness-speed`) — never as a new node beside it, which G6 refuses (`harness-speed` would be a current slug and a `was:` entry at once) and the 2 observed-reach documents' `Anchor: dev-speed-first` re-point to it — otherwise they fail G1 in this slice (only the TREE side of 4.24; the `## GOAL dev-speed-first` heading moves in S3, and no guard reads it before S3); `anchors:` is removed and documents attach by node slug, and with it `check_cross`'s three anchor rules (`scripts/check-features.py:249-253`, `:271-273`, `:276-278`: names an anchor not in the registry, claimed by several nodes, claimed by none) and its read of `ANCHORS_MD` (`:284`, `:289`, `:297`), which would otherwise fail on the deleted file — found in review r2's same-class search; `check-anchors.py` reads the tree for G1 (now including `docs/adr`, any date) and G3, and drops the claimed-by-a-document rule; `gen-goals-page.py` and `gen-features-page.py` read the tree; `ARMED_ANCHORS` is derived (G4); `docs/anchors.md` is deleted — the gate on its readers is the whole-tree search in the S2 FAILS IF below, NOT the list in the next cell; every former consumer of the registry's slug set takes the tree's CURRENT slugs instead (G3): the backlog `epic:` parent check (`check-features.py` `kind_problems`, `gen-backlog-page.py` `parent_errors` and the page build that refuses on it), the summary count, and the self-test messages that name the registry; ADR-0016 moves from proposed to accepted | **Found at draft time — a lead for the plan, NOT exhaustive and NOT the gate** (the plan re-runs the S2 search at its own base). Scripts: `check-anchors.py`, `check-features.py`, `gen-goals-page.py`, `gen-features-page.py` (`:286` `anchor_adrs`, `:312` `n.anchors`, `:745` input list), `check-goal-status.py`, `gen-backlog-page.py` (`:4370-4375` `parse_registry`, `:1306` `parent_errors` message), `explainer-serve.py` (`:257` `PAGE_SOURCES["features"]`; its self-test asserts each source is a real file), `check-fixture-variation.py` (`:1452` names `parse_registry.text`), `check-publishability.py` (self-test fixtures `:2127`, `:2153`). Hooks: `regen-goals-page.sh` (`:36`) and `regen-features-page.sh` (`:61`, and its comments) drop `docs/anchors.md`; no hook gains a source (§5.1.1). Prose that names the registry: `docs/dev-process.md`, `docs/portable-practices.md`, `docs/process-checklists.md`, `docs/roadmap-to-launch.md`, `docs/adr/README.md`, `docs/features.md` preamble, `.agents/skills/dashboard/SKILL.md`, `docs/memory/anchor-name-and-stable-id-handoff.md`, the two `docs/marketplace/experiment-tier-*.md`. **The history set**, left as written and excluded from the S2 search: `docs/reviews/`, `docs/superpowers/`, `docs/explainers/`, `docs/dashboard-entries.md`, `docs/backlog.md` (row bodies are dated filings; 9 rows name the registry), `docs/marketplace/*.json` (scan files and `inventory.json` notes), and ADR-0016 itself, which records the retirement |
| S3 — goals become nodes, with the remaining renames | the goal-only names enter the tree per §4; the other `was:` renames; `docs/goal-threads.md` `## GOAL` headings re-pointed and merged (request lines untouched, §2.4); the `also` field; `--also`; G2 (including `goal:<slug>` answer keys), G5; `resolve()` reads history; `batch-ci.py` gains a conflict resolver for `docs/features.md`, where new names now land (it has one for `goal-threads.md`, `scripts/batch-ci.py:95-101`); `goal-tree.py` reads the tree from this slice (`resolve()`, the node set) — no trigger changes with it (§5.1.1); the three trunk headings get their slugs `product`, `platform` and `dev-infrastructure` HERE, where the goal `product` lands on its trunk (✍ row 4.1; an added slug line, not a rename, since no old name exists). S2's lift of `dev-speed` "to the trunk" needs no trunk slug: a node's parent is its heading position (`parse_features`, `scripts/check-features.py:41`) | `goal-tree.py`, `session-state.py`, `check-features.py`, `batch-ci.py` |
| S4 — the views | id `goal-<slug>` on three pages with the old ids kept as second ids; one `key_link` node kind with `view`; two-way links; `/goals` renders the tree and the requests; G7, G8; the agenda's PRIORITY line; `/goals` now derives requests from `docs/goal-threads.md`, and no trigger changes with it: that edit reaches the page when it merges (§5.1.1) | `page_markup.py`, `gen-goals-page.py`, `gen-features-page.py`, `goal-tree.py`, `check-page-links.py` |
| S5 — vocabulary | `CONTEXT.md` gains "node"; the comprehensibility-suite spec's §4 goal-facet registry is re-pointed; backlog #644 and backlog #472 are closed as dissolved | documents only |

Per-slice FAILS IF, beyond the guards each slice adds:

- **every slice:** `python3 scripts/goal-tree.py --snapshot --page --out <file>` (the page build, not
  `--print`) exits non-zero, or any check in `.github/workflows/ci.yml` is red.
- **S2:** an `Anchor:` in a spec, plan or ADR does not resolve; `explainer-serve.py --self-test` is
  red; or EITHER search below prints a line. The search reads the whole tracked tree minus the history
  set of the S2 row — it does not read a list of readers, so a reader nobody listed still fails it:

  ```
  H="':!docs/reviews' ':!docs/superpowers' ':!docs/explainers' ':!docs/dashboard-entries.md' \
     ':!docs/backlog.md' ':!docs/marketplace/*.json' ':!docs/adr/0016-names-live-in-one-node-tree.md'"
  eval git grep -n -F -- 'anchors.md' -- . $H
  eval git grep -n -E -- "'parse_registry|registry_anchors|ANCHORS_MD|anchor_slugs'" -- . $H
  ```

  Measured at `256c7b4f`: 48 lines in 19 files, and 18 lines in 5 files — the work S2 owes, so neither
  search is vacuous. The token is `anchors.md`, not `docs/anchors.md`, because three readers build the
  path as `DOCS / "anchors.md"`. Bound: a reader that spells the name another way (a concatenated or
  configured path) is not printed; none exists today.
- **A slice that retires any other name** (a renamed slug in S2 or S3) is gated the same way for
  STRUCTURED uses by G1–G5, which read every source of §2.5.1; prose uses are history (§2.4, §5.2).

#### 5.1.1 What rebuilds each page — the design adds no trigger

Review rounds 1–3 each found a page trigger or a reader that a hand-kept list had missed; the
architecture review `docs/reviews/architecture-review-2026-11-23-goal-node-tree-migration.md` replaced
both lists. For triggers, the measured rule is that none is owed:

- **Every page is built from a fresh `origin/master`, never from the checkout that was edited**
  (backlog #408; `scripts/regen-pages.py`, `fresh()` at `:431`, "the ONE way a page is built"). An edit
  hook therefore cannot show the edit that fired it — each says so ("the page shows MASTER, not the edit
  that fired this hook", `.claude/hooks/regen-goals-page.sh`).
- **A merge rebuilds every page, whatever was edited**: `pages_for` (`scripts/regen-pages.py:594`)
  returns every key of `explainer-serve.REGENERABLE` after a command containing `gh pr merge`.
- So when S2, S3 or S4 makes a page read a new file, an edit of that file reaches the page when it
  merges, by the trigger that exists. No hook, `pages_for` route or `PAGE_SOURCES` entry is added. The
  only trigger edits are REMOVALS of `docs/anchors.md` in S2, and the S2 search forces them.

Not covered, and not this design's (backlog #710): the hooks' `case` lists and `PAGE_SOURCES` remain
hand-kept copies of what each generator reads; the `/_stale` banner will name fewer files than a page
reads, as it already does; a merge made outside this session rebuilds nothing until a hook fires or
Refresh is pressed.

S2 and S3 are the two that change names; they are separate so that a red gate names one cause.
Every script a slice edits is a two-file edit with its mutation manifest (`scripts/mutations/<name>.json`);
the two hooks S2 edits are shell files with no manifest, and their edit is the removal the S2 search checks.
A DRAFT pull request at each slice's start runs the selected sweep.

### 5.2 How history keeps resolving

| History | Holds | After a rename |
|---|---|---|
| `.claude/goal-tree-log.jsonl` (git-ignored, per checkout; 358 snapshots here) | each goal's slug, per snapshot | never rewritten. Read through `resolve()`; an old slug renders under the current node |
| `.claude/inflight.jsonl` (git-ignored) | a `goal` per entry | entries written before the rename resolve through `was:`; new entries must use the current slug (G5) |
| `.claude/agenda-log.jsonl` (git-ignored) | no slug FIELD: measured read-only, 54 records, keys `kind, at, window, change_if, steps, id, of, states, step`; slugs appear only inside free step text (`harness-ships-elsewhere` ×32, `memory-hygiene` ×1) | prose; not parsed, nothing to resolve |
| `docs/goal-tree-answers.json` (tracked) | `goal:<slug>` keys; 0 answers today | LIVING, not history: a rename moves the key in the same pull request (G2). Test: an answer keyed on a renamed node still renders on that node, not under "Older questions" |
| commit subjects (8 of 1830 contain `-first`) | prose | not parsed for slugs — threads match on `backlog #N` / `PR #N` refs (`scripts/goal-tree.py:143`), so nothing breaks (INFERRED from the regex; no reader of slugs in subjects was found) |
| `docs/reviews/` (frozen) | prose | untouched; frozen files are outside G1–G4 |
| `docs/dashboard-entries.md` (8 lines with a `-first` slug) | dated entries | ✍ treated as history and left, or rewritten as living — §6 Q4 |
| owner request lines in `docs/goal-threads.md` (4 quote a `-first` slug) | quotes | never rewritten (§2.4) |
| old page fragments | `#g-<slug>`, `#<slug>`, `#goal-<old-slug>` | kept as second ids (§3.5) |

FAILS IF, for the whole migration: after S3, `python3 scripts/goal-tree.py --snapshot` over a log
containing pre-rename snapshots reports any slug as unknown; or any thread present before S3 is absent
after it (144 thread lines in, 144 out — no line is merged, §2.3 — each under the node its goal
became, accounted for by name in the pull request).

### 5.3 What this does not do

No backlog area tag is renamed or re-homed beyond the two moves §4 names (`tooling/speed` to
`dev-speed`, `comprehensibility` to `comprehensibility-suite`). No page is redesigned beyond its node
set, ids and links. The 12 memory-related backlog rows are not retagged (§6 Q5). The line-229
refusal is not this work's: it was a mis-typed ref, corrected on this spec's branch (§1).

## 6. Questions for the owner

Beyond the 14 ✍ rows of §4, which are decided in the walkthrough (Q11–Q13 were added in review round 1;
the table keeps Q10 last so earlier references stay valid):

| # | Question | Recommendation |
|---|---|---|
| Q1 | Should `docs/features.md` be renamed once it holds goals too (say `docs/nodes.md`)? | **No.** 12 files name it; the page `/features` keeps its name; a rename buys a word and costs a slice. Revisit if the name misleads in use |
| Q2 | Owner requests: stay in `docs/goal-threads.md` and be derived onto `/goals`, or move into the tree file as a node field? | **Stay.** They are dated events interleaved with the threads they caused; the tree file is names and one-line fields |
| Q3 | Where is the priority order written? | **One dated, quoted `PRIORITY` line in the preamble of `docs/goal-threads.md`**, shown on the agenda. The alternative, an `order:` field per node, spreads one decision over many lines |
| Q4 | `docs/dashboard-entries.md` has 8 lines naming an old slug in dated entries. History, or living? | **History** — an entry records what was true when written; it resolves through `was:` |
| Q5 | Should `token-usage` and `memory-recall` get their own backlog area tags, so their open rows are counted on `/features`? | **Yes, as a follow-up row, not in this work.** Until then both show threads and no gaps; 12 memory rows sit under 5 other tags |
| Q6 | `check-goal-status.py` arms 13 anchors by a hand-kept list. Derive it how? | **Arm every node that has an anchored document, minus a short named exemption list** — today's 2 unarmed anchors. The 3 documents under them that declare no state would then need one, or the exemption |
| Q7 | Add "node" to `CONTEXT.md` now, and settle "anchor" (a header keyword there, a mutation term in `CONTEXT.md:140`)? | **Yes, in S5.** Keep the `Anchor:` header keyword — 64 specs and plans and 6 ADRs carry it — and define it as "the node a document belongs to" |
| Q8 | `review-decides-itself` and `review-process` are two nodes on one subject. Parent and child? | **Leave both** in this work; raise it with the next review-process change |
| Q9 | A node marked `done:` that later gets a thread: refuse, or show? | **Show**, flagged on the agenda. Refusing would make the owner undo a decision to record a fix |
| Q11 | How is a new name born (§2.7)? G5 refuses an unknown goal at `--add`, which collides with the owner's rule that the agent PROPOSES and the owner PICKS (backlog #514) | **A `proposed: <date-time>` node field**: the agent may write it, `--add` accepts it, the agenda shows it as awaiting your pick, a spec may not anchor to it. Alternative: keep an unknown goal as a page problem, as today |
| Q12 | A backlog row with several area tags (27 rows, 23 open): which node is its primary? Today it shows under the claimant of EACH tag and has no primary | **Its `epic:` parent if it has one, else the node claiming its first tag**; the others show it as shared and do not count it (G7's second clause). Alternative: an explicit primary marker in the tag cell |
| Q13 | The `state:` of new nodes: `cloud-publishing` and `serve-money-guard` are given `built` by the author; `memory-hygiene` and `dashboard-decisions` get none | **None on all four until you say `built`**: an aim with no state shows its gaps, and `built` on a node the author did not verify would repeat "built hides open gaps". Alternative: `built` on the two anchors, as the draft had |
| Q10 | ADR-0010 is still `proposed`. ADR-0016 supersedes part of a decision that was never formally accepted. Accept ADR-0010 first? | **Yes** — its check has shipped and passes (`check-anchors.py`, 15 registered, floor 22 held), which is its own stated acceptance condition |

### 6.1 The owner's answers — walkthrough of 2026-11-23

Recorded from the walkthrough page's decision cards (each click arrives in `~/explainers/questions.md`). "Yes" accepts the row as §4 proposes it; "Recommended (…)" takes the recommendation quoted.

| Row or question | Answer | When (PST) |
|---|---|---|
| 4.1 | Yes | 11-23 21:03 |
| 4.3 | Yes | 11-23 21:22 |
| 4.18 | Yes | 11-23 21:06 |
| 4.24 | Yes | 11-23 21:22 |
| 4.25 | Yes | 11-23 21:22 |
| 4.26 | Recommended (put it under the trunk, beside dev-speed and token-usage) | 11-23 21:10 |
| 4.27 | Recommended (a child) | 11-23 21:10 |
| 4.30 | Recommended (merge) | 11-23 21:10 |
| 4.33 | Recommended (merge) | 11-23 21:10 |
| 4.36 | Recommended (yes) | 11-23 21:22 |
| 4.37 | Recommended (yes, as a consequence of 4.36) | 11-23 21:20 |
| 4.38 | Recommended (yes) | 11-23 21:20 |
| 4.41 | Recommended (new child, name kept) | 11-23 21:20 |
| 4.42 | Recommended (yes, as a consequence of 4.36) | 11-23 21:20 |
| Q1 | Recommended (no) | 11-23 21:20 |
| Q2 | Recommended (they stay) | 11-23 21:20 |
| Q3 | Recommended (one dated, quoted PRIORITY line) | 11-23 21:20 |
| Q4 | Recommended (history) | 11-23 21:20 |
| Q5 | Recommended (yes, but as a follow-up backlog row, not in this work) | 11-23 21:20 |
| Q6 | Recommended (arm every node that has an anchored document, minus a short named list of exemptions) | 11-23 21:20 |
| Q7 | Recommended (yes, in S5) | 11-23 21:20 |
| Q8 | Recommended (leave both as they are) | 11-23 21:20 |
| Q9 | Recommended (show it) | 11-23 21:20 |
| Q10 | Recommended (yes) | 11-23 21:20 |
| Q11 | Recommended (a proposed: <date-time> field on a node) | 11-23 21:20 |
| Q12 | Recommended (its epic: parent if it has one, otherwise the node that claims its first tag) | 11-23 21:20 |
| Q13 | Recommended (no state on all four until you say built) | 11-23 21:20 |
| APPROVE | Recommended (approve with your answers) | 11-23 21:20 |

## 7. What was measured, and what was inferred

| Claim | How |
|---|---|
| 15 anchors; 12 share a slug with a feature node | MEASURED — `grep '^| \`' docs/anchors.md`; compared by hand with the 35 headings |
| 35 feature nodes, 3 trunks, 31 built, 4 absent, 15 anchors and 29 areas claimed once | MEASURED — `python3 scripts/check-features.py` |
| 9 goals, 144 thread lines, 44 request lines, per-goal counts | MEASURED — a script over `docs/goal-threads.md` |
| 4 refs under more than one goal; 0 lines contain ` · also ` | MEASURED — same script |
| `parse_threads` refused the living file at line 229, and the cause was a mis-typed ref | MEASURED — imported `scripts/goal-tree.py`, called on the file text; `gh pr view 613` and `git log -S` for the cause; `goal-tree.py --snapshot --page --out <file>` in a scratch clone: rc 1 `MALFORMED` before the one-line fix, page written after |
| Every reader of `docs/anchors.md` (§5.1 S2) | MEASURED — `git grep -c -F anchors.md`, each hit read and classified living or history |
| Where a changing slug is written (§2.5.1) | MEASURED — `git grep -c -F` per slug, each hit classified by hand; structured sources by grepping field names and reading each list's readers. Bound stated there |
| `.claude/agenda-log.jsonl` has no slug field | MEASURED — read-only, main checkout, 54 records |
| 4 built nodes rely on `anchors:` as their only fragment | MEASURED — `parse_features` over `docs/features.md`, nodes whose `areas` is empty and `anchors` is not |
| At the base `fa11456f`: 63 specs and plans carry an `Anchor:` header (23 under `status-visibility`), 5 ADRs do, 3 frozen reviews do. On this branch: 64 and 6 (this spec and ADR-0016, both `status-visibility`) | MEASURED (re-run in review r2, which found the earlier "63 documents across `docs/`" mislabelled: the 63 were specs and plans only) — `check-anchors.py`'s `ANCHOR` regex; specs, plans and reviews over their first 10 lines, ADRs over the whole file, counted per directory |
| `-first` LINE counts (`git grep -c`); 8 of 1830 commit subjects | MEASURED — `git grep -c`, `git log origin/master --format=%s` |
| 358 snapshots; slug counts in them | MEASURED — read-only, on the main checkout's git-ignored log, 2026-11-23; it differs per checkout |
| 660 backlog rows, 27 multi-tag (23 open); 12 memory-titled rows over 5 tags | MEASURED — `gen-backlog-page.parse` |
| Files naming each list: 17, 11, 12 | MEASURED — `grep -l` over scripts, hooks, commands, workflows, `.agents`, `docs/*.md`, `CONTEXT.md` |
| Old-fragment links: 3 and 1 | MEASURED — `grep -rEo` over `docs scripts .agents .claude/commands`; bookmarks outside the repository are not counted |
| `ARMED_ANCHORS` is not checked against the registry | MEASURED — no occurrence of the registry's name or a registry reader in `scripts/check-goal-status.py` |
| `--goal` is checked only for blankness at `--add` | INFERRED from reading `scripts/session-state.py`; not run. The owner's rule behind it (`ADD_NEEDS_GOAL`, `:377-381`) was read |
| Commit subjects are not parsed for slugs | INFERRED from the ref regex; no exhaustive search of readers |
| D8's change provides the index, gap counts and folded cards | PARTLY MEASURED — a local branch holds 2 commits doing so in `scripts/gen-features-page.py`; it is NOT on `origin/master` and may change before it lands |
| 45 nodes out; the counts of §4.4 | DERIVED from §4's rows; changes with any ✍ answered differently |
| The cost of each slice | NOT ESTIMATED — no figure is given because none was measured |
| The owner's decisions D1–D8 | RECORDED — relayed by the coordinator and present in the ledger entry `goal-unify`; not heard by the author |

## Out of scope

Redesigning any page beyond its node set, ids and links. Retagging backlog rows. Any product
behaviour. Publishing: this is the harness's own pages, and whether the node tree ships in the
marketplace plugin is that goal's decision.

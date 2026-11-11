# The comprehensibility suite — one question per page, one home per key

> **Anchor:** `status-visibility` — **ADR:** 0010
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** 🟠 needs-you — walked through with the owner 2026-11-02 09:20–09:40 (every §8 choice answered); adversarial rounds 1–3 folded (19 + 4 + 4 findings, `docs/reviews/coordinator/comprehensibility-spec-r{1,2,3}-coordinator.md`; r3 after a Phase 6 review of the status facet); §10 Q1 answered (backlog #384, Phase 1). Nothing here is built yet.
Every answer below was given by the owner on the roles review page
(`docs/explainers/2026-10-28-topic-suite-roles-review.fragment.html`), 2026-10-28 and 2026-11-02 ~09:25.

## In plain words

The project has seven page producers (`gen-dashboard`, `gen-goals-page`, `gen-backlog-page`,
`gen-features-page`, the goal tree, `/brief`, the `explain-*` skills). Each was added for one
moment's need, so several answer the same question and give different answers. (Backlog #384's own
list of seven had `gen-work-lines`; D2 retired it and the goal tree took its place.)

This spec gives every page **one question**, says **who reads it and when**, and says what it must
**not** repeat. Wherever a page needs a fact another page owns, it **links** to it instead of copying.
Every identifier (a backlog row, a PR, a goal, a feature) becomes a link to **one** home page, drawn
by **one** shared function. Tags shrink to **four** closed lists.

Why it matters, in the owner's words (2026-11-02): comprehensibility is the *direction* lane of the
same goal as development speed — *"If I cannot correctly understand what you are doing or how the
project is progressing, dev speed in local sense doesn't have much meaning."*

**The suite's one principle** (owner, 2026-10-28 20:47): *"pages provides a perspective view which
contains links to other pages."* A page composes a view of content other pages own, by pointer, and
never keeps its own copy. This is ADR-0010's rule (a central file of NAMES is safe, one of STATE
drifts), applied to pages.

## 1. Decisions and answers

| Item | Answer (owner) | When |
|---|---|---|
| **D1** "Needs you" | One definition — a decision or an action only the owner can make or take (§10 Q1, 11-02) — shown on the goal-tree page as **two disjoint sets, each with ONE source** (§8 Q2): **blocking now** (source: in-flight ledger entries with `entry_kind() == "owner-wait"`) and **waiting until picked** (source: backlog rows with `status: needs-you` that NO live ledger entry references). Rules in §6 row 4 | 10-28 03:47; refined 11-02 09:35 |
| **D2** Work-lines | The goal tree absorbs it; work-lines retired, history archived | done, PR #434 |
| **D3** Freshness | Every merge rebuilds dashboard, goals, backlog, features and goal tree | done, PR #433 (`.claude/hooks/regen-pages.sh`) |
| **R1** Goal tree | Accepted as written; it is the home page | 11-02 |
| **R2** Backlog | Accepted: the ONLY place an item's state is decided | 11-02 |
| **R3** Dashboard | A pure change log; "what changed" is a query *since T*, T free-form or from a dropdown (backlog #392) | 10-28 19:12, 19:17 |
| **R4** Goals | Settled by Agile kinds: story / task / defect plus explicit parent links (backlog #394, built) | 10-28 20:35 |
| **R5** Features | Accepted: the map of what exists and what is missing | 11-02 |
| **R6** Briefs | Settled by R-open-3; whether briefs are retired is decided after backlog #392 is built | 10-28 20:46, 11-02 |
| **R7** Explainers | Accepted: an explainer declares the item it is about; that item's page links back | 11-02 |
| **R8** Work-lines | Done (PR #434, `d0acfa85`) | 11-02 |
| **L1** Linking | Accepted: one shared function renders every key as a link to its one home page | 11-02 |
| **R-open-1** Goal unit | A: keep `/goals` and `/features`; each feature node declares its goal anchor; programmes stay prose in the roadmap | 11-02 |
| **R-open-2** PR links | A: GitHub's PR page | 11-02 |
| **R-open-3** Briefs | A: dated snapshots — keep narrative and decision, link to the generated page, stop restating its counts | 11-02 |
| **R-open-4** Home | A: the goal-tree page | 11-02 |
| **R-open-5** Tags | A: four closed facets — goal, area, kind, status — and nothing else (backlog #385) | 11-02 |

## 2. The pages

| Page | Its one question | Reader, moment |
|---|---|---|
| `/goal-tree` (**home**) | What is the agent working on now, why, what is it waiting on — and how did it get here? | Owner, any time |
| `/backlog-table` | What work exists that is not done, and what state is each item in? | Owner choosing next; agent filing or closing |
| `/dashboard` | What changed, and why did it matter? | Owner, returning after a gap |
| `/goals` | What are we trying to achieve, and what belongs to each aim? | Owner when direction is in question; agent placing new work |
| `/features` | What does the system do today, and what is missing from each part? | Anyone, before asking for something new |
| a brief | Where did one body of work stand on day D, and what decision did it need then? | Owner, for a catch-up at a moment |
| an explainer | How does this one subject work? | Owner, wanting to understand, asking on the page |
| `/work-lines-archive` | (none — frozen history through 2026-10-25) | — |

| Page | Sources | Links out to | Must NOT restate |
|---|---|---|---|
| goal tree | `docs/goal-threads.md`, git and `gh`, the in-flight ledger, backlog `status: needs-you` (D1) | PR → GitHub · row → backlog · goal → `/goals` · timeline entry → its past tree · change line → its dashboard entry | a row's detail (backlog), the narrative of a change (dashboard) |
| backlog | `docs/backlog.md`, read by the one shared parser (backlog #381) | item → its PR · area → `/features` · goal → `/goals` · a needs-you item → the goal tree's set | progress on an item (goal tree), how it was built (the PR), what changed since T (goal tree, row 6) |
| dashboard | `docs/dashboard-entries.md` | entry → its PR, its backlog row, its goal | "needs you" (D1), open PRs or where a thread stands (goal tree) |
| goals | `docs/anchors.md`, roadmap, spec and plan headers, ADRs, `ROOTS`/`DEPENDS` | goal → its feature nodes, its rows, its specs and ADRs, its threads' PRs | what is built (features), what is in flight (goal tree) |
| features | `docs/features.md`, the rows its areas claim | node → its rows, its goal, its ADRs and specs | a gap's detail (the row), intent (goals) |
| brief | the moment it was written | every item → its live home page | current state, and any count a generated page computes |
| explainer | the subject, read at the time; answers written into the page | its declared subject (row 7) | status (goal tree or backlog) |

**In-role, checked (M4):** `/goals` renders each spec/plan's document state (§4, *not a facet*) and the
spine's milestone rungs; it is the only page that renders either, and each links to its source document.
Its per-thread PR list is membership ("what belongs"), rendered through `key_link`.

## 3. Keys and their one home page

| Entity | Key, as written | Home page | Link (fragment id the home page must emit) |
|---|---|---|---|
| Goal | anchor slug | `/goals` | `/goals#<slug>` — goal cards carry NO id today (row 1 adds it) |
| Feature | node slug | `/features` | `/features#<slug>` |
| Backlog item | `backlog #N` | `/backlog-table` | `/backlog-table#iN` |
| Pull request | `PR #N` | GitHub | `https://github.com/<owner>/<repo>/pull/N`, repo from `gen-dashboard.repo_slug()`; **no repo → plain text, never a guessed URL** |
| Change | a dated dashboard entry | `/dashboard` | `/dashboard#<date>-<n>` (`gen-dashboard._slug`) |
| Topic | explainer slug | the explainer page | `/<slug>` |
| Thread | a row or PR on the goal tree | `/goal-tree` | `/goal-tree#t-<kind>-<N>` — the tree is one `<pre>` with no ids today (row 1 adds them) |

**Thread ids (Codex #3).** A thread's id is its key (`t-backlog-N`, `t-pr-N`). A key that appears under
several goals gets the id at its FIRST occurrence in render order; later occurrences link to it. A past
tree (timeline) is its own page, so its ids do not collide with the live one.

**The one shared link function.** `key_link(kind, key) -> str | None` (the href, `None` when no honest
link exists) and `link_keys(text) -> str` (renders every key found in prose), in **`scripts/page_markup.py`**,
the inline renderer gen-dashboard, gen-goals-page, gen-backlog-page, gen-features-page and explainer-serve
import. The goal tree does NOT import it: its `segments(text, repo)` (`goal-tree.py`) is today's
`link_keys`, so row 1 MOVES it into `page_markup` and the goal tree imports it. `page_chrome` owns the
chrome (theme, stamp, refresh bar), not content, so it is the wrong home. Hand-built hrefs today, outside
tests — MEASURED on `e2ac6e41` by a search that spans line breaks: backlog 3 (`gen-features-page.py` once,
`goal-tree.py` twice), PR 2 (`goal-tree.py`; `gen-dashboard.py:966-967`, split over two lines), dashboard 1
(`goal-tree.py`). All six move to `key_link`. A key inside a code span stays plain text (the
`check-reference-namespace.py` exemption). On generated pages a key is always written QUALIFIED
(`backlog #N`, `PR #N`); a bare `#N` chip (`gen-goals-page`'s backlog band) becomes qualified.

## 4. The tag vocabulary — four closed facets

| Facet | Closed values | Registry (the only place a value is added) | Written on a backlog row as |
|---|---|---|---|
| **goal** | the anchor slugs | `docs/anchors.md` | DERIVED, a set: the union of the resolved anchors of every feature node that claims any of the row's areas |
| **area** | the `areas:` values | `docs/features.md` (already enforced by `check-features.py`) | the Bundle cell, several allowed (backlog #381) |
| **kind** | `story`, `task`, `defect` | backlog #394 | `⟦kind: …⟧` (all 422 rows carry it — MEASURED, `befd0e6d`) |
| **status** | `open`, `parked`, `needs-you`, `done` | this spec | the FIRST WORD of the existing `Status` column, then free prose |

**Goal derivation (Codex #5, Claude H2).** A node's *resolved* anchors are its own `anchors:` list, else
its parent's resolved anchors, else — for a top node — the explicit `anchors: none — <reason>` (resolves to
the empty set). A row's goal is the deduplicated union over every node claiming any of its areas (an area
claimed by two nodes contributes both — `gen-features-page` already places such a row under both). An empty
union renders "no goal" and is reported, never hidden. An unmatched area is already refused by `check-features.py`.

**`ROOTS`/`DEPENDS` stay, as DEPENDENCY, not membership (Claude H2).** `gen-backlog-page.DEPENDS` maps a row to
`(relation, root, note)` — `survives`, `partly-dissolved-by`, `blocked-by`, `dissolved-by` — on one root, the
anchor `stable-blob-addressing`. Rows 20–22 are `dissolved-by` it: deleted by that goal, not serving it. So the
derived facet does not duplicate DEPENDS; `/goals` shows two bands, "rows serving this goal" (facet) and "rows
depending on its root" (DEPENDS, relation shown), replacing "Backlog hanging off it". ADR-0010's *Scope*
("Its anchor mechanism already exists: `ROOTS`") gets a ⟳ amendment saying so (row 3).

**Status, one home (Claude H5; r2 Codex 1; r3 per the architecture review).** The backlog has NO severity column
(severity is a leading glyph) and HAS a free-text `Status` column (`docs/backlog.md:30`). The facet is that column's
first word, so the row keeps one home for its state. **The migration rule (row 2):** strip a cell's leading glyphs,
emphasis and `(was …)`/`(filed …)` parenthetical, map its first word to one of the four values, PREPEND the value, and
keep the old cell verbatim after it (glyphs, `ACTION:` markers, prose). **The owner decides, at row 2's build,** every
row the rule cannot settle — from a list row 2's code produces: a first word that maps to no value, a cell whose later
`✅` contradicts it, and every candidate for `needs-you` (no first word maps there; an action keeps its `ACTION:`
marker, §10 Q1). There is NO default. The Item cell's `✅` is removed; the state is the facet. The backlog page's
`open/closed/all` filter treats `open`, `parked` and `needs-you` as not closed.
**Falsifiers:** after migration the parser refuses any first word outside the four; row 2's test pins the per-value
counts its code computed on its build commit. The spec carries no per-row counts — they belong to that build
(`docs/reviews/architecture-review-2026-11-02-spec-status-facet.md`).

**Not a facet: a document's state (Claude H3).** `check-goal-status.py` keeps its own closed vocabulary
(`✅ shipped`, `🟠 current`/`needs-you`, `⏸ parked`, `⛔ obsolete`) for spec/plan headers. It is the state of a
DOCUMENT, not of a backlog item, and is not a tag. Shared words mean the same thing (`parked`, `needs-you`).
A document waiting on the owner is in-flight work, so it is in "blocking now" through an `owner-wait` ledger
entry; `/goals` renders the header badge as document state and links to the goal tree, and counts nothing.

Nothing else is a tag. Parentage (`part of: backlog #N`, `epic: <anchor>`) is a link, not a tag
(backlog #394 ruling 2). Review `component:` stays free text (backlog #385).

## 5. Concern → mechanism

| Concern | Mechanism | What already does this, and why it is not enough |
|---|---|---|
| An item's state | backlog `status` facet, read by the shared parser | `✅` in the Item cell on 150 of 422 rows (MEASURED, `befd0e6d`); the Status column is free prose, so no page can read a state from it |
| What needs the owner NOW | goal tree "blocking now", from `owner-wait` ledger entries | three lists gave three counts for the SAME kind (37, 12, 0 — MEASURED 2026-10-27, roles page) |
| What needs the owner LATER | goal tree "waiting until picked", from `status: needs-you` rows no live entry references | as above |
| What changed | dashboard entries (why) + the goal tree's since-T query (what) | the dashboard alone cannot answer "since T" |
| A key's link | `page_markup.key_link` | six hand-built hrefs; 0 PR links on generated pages against 18–157 PR mentions per page (MEASURED, inventory 2026-10-27) |
| A page being current | rebuild on merge (D3, built, PR #433) + the freshness falsifier (§7) | the hook fires only on a session's `gh pr merge`; a merge in the GitHub UI or another clone is not rebuilt |
| A feature's goal | resolved `anchors:` (explicit, inherited, or `none — <reason>`) | 13 of 28 nodes declare one (MEASURED, `befd0e6d`) |

## 6. What changes, as proposed backlog rows (in order — NOT filed)

1. **`page_markup.key_link` / `link_keys`: one function renders every key as a link** (L1). Move the six
   hand-built hrefs and `goal-tree.segments` onto it; emit the `/goals#<slug>` and `/goal-tree#t-…` ids (§3);
   re-bind the mutations anchored on the moved text (`scripts/mutations/goal-tree.json`, the PR-href pair);
   a check that every internal `#fragment` a generated page links to resolves on its target page.
2. **The backlog `status` facet: four values, the first word of the `Status` column** (R-open-5, backlog #90).
   Migrate by §4's rule; the owner decides the rows its code lists (incl. every `needs-you`); its test pins the
   computed counts; drop `✅` from Item cells; the parser refuses an unknown or missing value.
3. **Every feature node resolves a goal anchor** (R-open-1); `/goals` and `/features` link both ways; the goal
   facet is derived (§4); `/goals` gets its two row bands; ADR-0010 ⟳ Scope amendment; CONTEXT.md updated
   (*goal anchor* vs a mutation's *Anchor*; the five rebuilt pages; "needs you"; the four facets).
4. **The goal tree's two "needs you" sets** (D1, §8 Q2):
   - *Predicate.* "Blocking now" is `session-state.entry_kind(e) == "owner-wait"` — the declared field. Legacy
     `WAITS-ON-OWNER:`-prefix entries are migrated to `kind: owner-wait`; `needs_from_ledger` moves off
     `waits_on_owner()`. `owner-instruction` (an instruction FROM the owner) is not in either set.
   - *Reference (r3 M3).* A ledger entry references backlog row N iff it carries the declared field `row: N`
     (`session-state.py --add … --row N`, stored beside `kind`). Only that field counts — a `backlog #N` in `what`
     or `on_done` references nothing. Legacy `WAITS-ON-OWNER:` entries migrate with no `row` field.
   - *Identity and disjointness.* An item is identified by its backlog row. "Waiting until picked" = rows with
     `status: needs-you` MINUS rows ANY live ledger entry references (D1's rule, whatever the entry's kind). An
     entry that picks such a row MUST be `owner-wait` (the work cannot pass the owner), so picking is one write
     and the item moves sets atomically; a live entry of another kind referencing a `needs-you` row is a defect
     §7's completeness falsifier reports. An entry closing UNANSWERED returns the row to "waiting" with no write.
   - *Answering — one order (r2 Codex 3).* (1) Write the ROW: status leaves `needs-you` (to `open`, `parked` or
     `done`, per the answer) and its prose records `answered <date> — closes entry <id>`. (2) Close the ENTRY.
     Between them the item is in "blocking now" only (entry live; row no longer `needs-you`), never back in
     "waiting". An interruption is recovered at the next tray load or session start: a live `owner-wait` entry
     that a row's `closes entry <id>` names is closed. Entry-first is FORBIDDEN — it returns the answered item to
     "waiting". An unpicked row is answered by (1) alone; an `owner-wait` entry with no row, by (2) alone.
   - *Dashboard asks (Claude H4).* Each readable unresolved ask becomes an `owner-wait` entry (if its work is in
     flight) or a backlog row with `status: needs-you`; the 29 unreadable asks are repaired then converted, or
     closed. Then `needs_from_dashboard` and the dashboard input to `consolidate` are deleted, and `[needs-you]`
     stops being a dashboard entry kind. The choose/Send answer tray moves to the goal tree's two sets: an
     answer writes the item's own source, in the order above.
5. **The dashboard becomes a pure change log**: drop `gen-dashboard.open_prs()` and its "What needs you"
   section in favour of a link to the goal tree (R3; backlog #384's recorded C3).
6. **The goal tree's "what changed since T" query** — already backlog #392; each change line links to its
   dashboard entry; the backlog's "Since your last visit" selector becomes a link to it with the same T.
7. **An explainer declares its subject** (R7): `<meta name="subject" content="…">` in the fragment, one of
   `backlog #N`, `goal:<slug>`, `feature:<slug>`, `PR #N`, `concept`. The generator of the subject's home page
   reads the fragments and draws the back-link; `PR #N` (GitHub) and `concept` get none. Pages written before
   this spec are not rewritten (§8 Q7).
8. **A check reports unlinked keys in hand-written explainer fragments** (§8 Q7) — report, never fail.
9. **Briefs stop restating counts and link to the generated page** (R-open-3); fix `brief-compose.py`'s
   default filename, which labelled 4 topic pages "brief" (MEASURED, roles page).
10. **Decide whether briefs retire**, after row 6 ships (R6; the owner's 20:46 answer).
11. **Close backlog #385** once rows 2 and 3 land; its facets are defined here.
12. **One check that no two pages declare the same question** — built LAST (§8 Q9). Each page TYPE declares a
    question id and its sentence in one registry (a constant in `page_markup`, read by every generator,
    `brief-compose` and `explainer-serve`; a brief or explainer page carries its type's id). Fails on a
    duplicate id, a duplicate sentence, a page type with no declaration, and on each §2 *Must NOT restate*
    cell made concrete (a needs-you count off the goal tree; an open-PR list off the goal tree; a since-T
    selector off the goal tree). **Bound:** it catches identical declarations and the listed restatements, not
    two differently worded questions that overlap — that remains a review question.

## 7. Falsifiers — the observation that shows each rule is not kept

| Rule | It is NOT being kept when… |
|---|---|
| One question per page | row 12's check fails, or a status question gets two different answers from two pages |
| A page is a perspective | a page shows a count or state another page owns, as text and not a link (e.g. a brief stating an open-row count) |
| The backlog decides state | any page shows an item's state that differs from the backlog row's `status` |
| One source per "needs you" set | the dashboard or backlog page shows its own needs-you COUNT; "blocking now" differs from the `owner-wait` entries; "waiting until picked" differs from `needs-you` rows minus those ANY live ledger entry references |
| The sets are disjoint and complete | a row appears in both sets (overlap); or a row with `status: needs-you`, or a live `owner-wait` entry, appears in neither (absence); or a live entry that is not `owner-wait` references a `needs-you` row |
| A reference is the `row:` field | a `needs-you` row leaves "waiting until picked" while no live entry carries `row:` equal to it (e.g. matched by a `backlog #N` in an entry's text) |
| Answering is ordered | an answered item appears in "waiting until picked" at any point; or a live `owner-wait` entry named by a row's `closes entry <id>` survives the next session start |
| Every key is a link | a generated page contains `backlog #N`, `PR #N` or a bare `#N` chip outside a code span and outside an `<a>` |
| One link function | an href to `/backlog-table#i`, `/goals#`, `/features#`, `/dashboard#`, `/goal-tree#` or `github.com/…/pull/` is built anywhere in `scripts/` except `page_markup.key_link` (and its tests) |
| Links resolve | an internal link's `#fragment` has no matching id on its target page |
| Four closed facets | a row carries a facet value no registry declares and the parser accepts it; or a fifth facet appears |
| Feature → goal | a feature node whose RESOLVED anchor is unresolved (no own, no inherited, no top-level `none — <reason>`), or names a slug `anchors.md` lacks, passes `check-features.py` |
| Explainer ↔ subject | an explainer written after this spec with no `subject` meta, or a row/goal/feature subject whose page does not link back |
| Pages are current | a generated page's recorded source commit is not the REMOTE master tip (`git ls-remote origin refs/heads/master` — never the local `origin/master`, which a missing fetch freezes) more than **1 minute** after that tip was merged (GitHub's time: the PR's `mergedAt`, else the tip's committer date) — including when the rebuild never ran or failed. A failed remote query is NOT RUN, never a pass (r2 Codex 4) |
| Briefs are snapshots | a brief written after this spec contains a number that a generated page computes |

## 8. Choices the owner's earlier answers did not settle — answered in the walkthrough, 2026-11-02

| # | Choice | Answer |
|---|---|---|
| 1 | Goal tree answers WHAT changed since T; the dashboard keeps WHY | owner: A, as drafted |
| 2 | Source of "needs you" | owner: **two kinds, two sets** — *"Need you list in goals are decision task for backlogs which become relevant when the backlog item is being worked and in-flight ledger need you seems different kind of need-you for current working order … those two different need-you decisions can be presented as separate sets as two separate concerns."* Adopted as D1's refinement (§1, row 4, §7) |
| 3 | ~~Status facet in the `⟦…⟧` block~~ ⟳ r1: the first word of the existing `Status` column (one home; no severity column exists) | coordinator (mechanical) |
| 4 | A row's goal is DERIVED through its area's feature node | owner: A |
| 5 | The 15 of 28 feature nodes with no anchor inherit the parent's; a top node with none declares `anchors: none — <reason>` | owner: A |
| 6 | The link function lives in `page_markup.py` | coordinator (mechanical) |
| 7 | Hand-written explainer fragments are not rewritten; a check reports their unlinked keys | owner: A |
| 8 | The dashboard's open-PR list is dropped; the goal tree owns open PRs | owner: A |
| 9 | The duplicate-question check is kept and built last (now row 12) | owner: A |

## 9. What was measured, and what was inferred

| Number | Status | Source |
|---|---|---|
| 28 feature nodes, 13 with `anchors:` | MEASURED | `docs/features.md` on `befd0e6d`; re-measured r1 |
| 422 backlog rows, all with `⟦kind:` | MEASURED | `grep -c` on `docs/backlog.md`, `befd0e6d`; re-measured r1 |
| 6 hand-built hrefs (3 backlog, 2 PR, 1 dashboard) | MEASURED | search spanning line breaks over `scripts/`, tests excluded, `e2ac6e41` (r1 corrected 3+1) |
| 37 / 12 / 0 needs-you counts; 29 unreadable | MEASURED | inventory, 2026-10-27 18:10 (roles page) |
| 0 PR links; 18–157 PR mentions per page; 358 feature → row links | MEASURED | inventory, 2026-10-27 |
| 49 of 68 dated pages are briefs; 4 mislabelled | MEASURED | roles page, 2026-10-27/28 |
| `✅` in the Item cell on 150 of 422 rows | MEASURED | `gen-backlog-page.parse`, `sev == "done"`, `befd0e6d` (= `origin/master` at r3; was 117 of 333 on `9ac7c80d`) |
| seven page producers | MEASURED, then updated | backlog #384, `f0dfef07`; `gen-work-lines` replaced by the goal tree after D2 |
| 12 proposed rows, their order | ESTIMATED | this spec's judgement |
| 1-minute freshness bound | OWNER | D3, "not more than a minute behind" |

## 10. Questions for the owner

**Q1 — Do owner ACTIONS belong in "needs you"?** (Claude r1 H4: `NEEDS-OWNER-ACTION`, `WAITS-ON-OWNER: ACTION:` were
homeless under D1.) **Answered 2026-11-02 09:56, the owner: A — the recommendation.** "Needs you" is a decision OR an
action only the owner can take; both sit in the same two sets, each item marked `decision` or `action` by the existing
`ACTION:` marker; status keeps its four values. D1 (§1) reads accordingly. Rounds 2 and 3 raised no new question; which existing rows become `needs-you` is the owner's, at row 2's build (§4).

## Out of scope

Building any of the rows above; retagging rows; the review `component:` vocabulary; any new page.
After the walkthrough the rows are filed, then each is planned and built on its own branch.

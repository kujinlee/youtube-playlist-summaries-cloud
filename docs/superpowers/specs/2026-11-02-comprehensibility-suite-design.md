# The comprehensibility suite — one question per page, one home per key

> **Anchor:** `status-visibility` — **ADR:** 0010
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** 🟠 needs-you — DRAFT for the owner's walkthrough (backlog #384, Phase 1). Nothing here is built yet.
Every answer below was given by the owner on the roles review page
(`docs/explainers/2026-10-28-topic-suite-roles-review.fragment.html`), 2026-10-28 and 2026-11-02 ~09:25.

## In plain words

The project has seven page producers (`gen-dashboard`, `gen-goals-page`, `gen-backlog-page`,
`gen-features-page`, the goal tree, `/brief`, the `explain-*` skills — backlog #384). Each was added
for one moment's need, so several answer the same question and give different answers.

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
| **D1** "Needs you" | One definition — a decision only the owner can make, open now — and one list, on the goal-tree page. Dashboard asks and backlog decision rows link to it | 10-28 03:47 |
| **D2** Work-lines | The goal tree absorbs it; work-lines retired, history archived | 10-28 03:47; done, PR #434 |
| **D3** Freshness | Every merge rebuilds dashboard, goals, backlog, features and goal tree | 10-28 03:47 |
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
| goal tree | `docs/goal-threads.md`, git and `gh` for every state, the in-flight ledger, backlog status `needs-you` (D1) | PR → GitHub · row → backlog · goal → `/goals` · timeline entry → its past tree · change line → its dashboard entry | a row's detail (backlog), the narrative of a change (dashboard) |
| backlog | `docs/backlog.md`, read by the one shared parser (backlog #381) | item → its PR · area → `/features` · goal → `/goals` · a needs-you item → the goal tree's list | progress on an item (goal tree), how it was built (the PR) |
| dashboard | `docs/dashboard-entries.md` | entry → its PR, its backlog row, its goal | "needs you" (D1), open PRs or where a thread stands (goal tree) |
| goals | `docs/anchors.md`, roadmap, spec and plan headers, ADRs | goal → its feature nodes, its open rows, its specs and ADRs | what is built (features), what is in flight (goal tree) |
| features | `docs/features.md`, the rows its areas claim | node → its rows, its goal, its ADRs and specs | a gap's detail (the row), intent (goals) |
| brief | the moment it was written | every item → its live home page | current state, and any count a generated page computes |
| explainer | the subject, read at the time; answers written into the page | its subject item (row, PR, goal or feature) | status (goal tree or backlog) |

## 3. Keys and their one home page

| Entity | Key, as written | Home page | Link |
|---|---|---|---|
| Goal | anchor slug | `/goals` | `/goals#<slug>` |
| Feature | node slug | `/features` | `/features#<slug>` |
| Backlog item | `backlog #N` | `/backlog-table` | `/backlog-table#iN` |
| Pull request | `PR #N` | GitHub | `https://github.com/<owner>/<repo>/pull/N`, repo from `git remote get-url origin` |
| Change | a dated dashboard entry | `/dashboard` | `/dashboard#<date>-<n>` |
| Topic | explainer slug | the explainer page | `/<slug>` |
| Thread | a row or PR on the goal tree | `/goal-tree` | `/goal-tree#<key>` |

**The one shared link function.** `key_link(kind, key) -> str` (the href) and
`link_keys(text) -> str` (renders every key found in prose), in **`scripts/page_markup.py`**.
Why there: `page_markup` is already the ONE inline renderer every generator imports as a library
(its docstring: four generators disagreed on 11 of 13 inputs before it existed), so a key in prose
becomes a link at the same step that renders the prose. `page_chrome` owns the chrome — theme,
stamp, refresh bar — not content, so it is the wrong home. Today the backlog href is hand-built in
three places (`gen-features-page.py` once, `goal-tree.py` twice) and the PR href in one
(`goal-tree.py`) — MEASURED on `befd0e6d` by `grep -n 'backlog-table#i\|github.com/.*pull' scripts/`.
Those call sites move to `key_link`. A key inside a code span stays plain text (a quotation, the
same exemption `check-reference-namespace.py` makes).

## 4. The tag vocabulary — four closed facets

| Facet | Closed values | Registry (the only place a value is added) | Written on a backlog row as |
|---|---|---|---|
| **goal** | the anchor slugs | `docs/anchors.md` | derived: the row's area → its feature node → that node's anchor |
| **area** | the `areas:` values | `docs/features.md` (already enforced by `check-features.py`) | the Bundle cell, several allowed (backlog #381) |
| **kind** | `story`, `task`, `defect` | backlog #394 | `⟦kind: …⟧` (all 422 rows carry it — MEASURED, `befd0e6d`) |
| **status** | `open`, `parked`, `needs-you`, `done` | this spec | `⟦… · status: …⟧`, split out of the severity column (backlog #90) |

Nothing else is a tag. Parentage (`part of: backlog #N`, `epic: <anchor>`) is a link, not a tag
(backlog #394 ruling 2). Severity stays a separate column with glyphs only. Review `component:`
stays free text (backlog #385).

## 5. Concern → mechanism

| Concern | Mechanism | What already does this, and why it is not enough |
|---|---|---|
| An item's state | backlog `status` facet, read by the shared parser | the severity column holds `✅` as a status on 117 of 333 rows (MEASURED, backlog #385) |
| What needs the owner | the goal tree's needs-you list, fed by `status: needs-you` | three lists gave three counts (37, 12, 0 — MEASURED 2026-10-27, roles page) |
| What changed | dashboard entries (why) + the goal tree's since-T query (what) | the dashboard alone cannot answer "since T" |
| A key's link | `page_markup.key_link` | four hand-built hrefs; 0 PR links on generated pages against 18–157 PR mentions per page (MEASURED, inventory 2026-10-27) |
| A page being current | rebuild on every merge (D3) | `/dashboard` and `/goals` measured stale (built 10-25, 10-23) |
| A feature's goal | `anchors:` on every feature node | 13 of 28 nodes declare one (MEASURED, `befd0e6d`) |

## 6. What changes, as proposed backlog rows (in order — NOT filed)

1. **Every merge rebuilds the five generated pages** (D3). First, because every later change is
   invisible on a stale page.
2. **`page_markup.key_link` / `link_keys`: one function renders every key as a link** (L1); move the
   four hand-built hrefs onto it.
3. **The backlog `status` facet: four closed values, split out of the severity column** (R-open-5,
   backlog #90). The parser refuses an unknown value.
4. **Every feature node declares its goal anchor** (R-open-1); `/goals` and `/features` link both ways.
5. **One "needs you" list on the goal tree, fed by `status: needs-you`** (D1); dashboard asks and
   backlog decision rows link to it; the 29 unreadable dashboard asks repaired or closed first.
6. **The dashboard becomes a pure change log**: drop `gen-dashboard.open_prs()` in favour of a link
   to the goal tree (R3; backlog #384's recorded C3).
7. **The goal tree's "what changed since T" query** — already backlog #392; each change line links to
   its dashboard entry.
8. **An explainer declares its subject item, and that item's page links back** (R7).
9. **Briefs stop restating counts and link to the generated page** (R-open-3); fix
   `brief-compose.py`'s default filename, which labelled 4 topic pages "brief" (MEASURED, roles page).
10. **Decide whether briefs retire**, after row 7 ships (R6; the owner's 20:46 answer).
11. **One check that no two pages declare the same question** — reads a declared question per page
    and fails on a duplicate (backlog #384's own FAILS IF).
12. **Close backlog #385** once rows 3 and 4 land; its facets are defined here.

## 7. Falsifiers — the observation that shows each rule is not kept

| Rule | It is NOT being kept when… |
|---|---|
| One question per page | two pages' declared questions match, or a status question gets two different answers from two pages |
| A page is a perspective | a page shows a count or state another page owns, as text and not a link (e.g. a brief stating an open-row count) |
| The backlog decides state | any page shows an item's state that differs from the backlog row's `status` |
| One "needs you" list | the dashboard or backlog page shows its own needs-you COUNT, or the goal tree's list differs from the rows with `status: needs-you` |
| Every key is a link | a generated page contains `backlog #N` or `PR #N` outside a code span and outside an `<a>` |
| One link function | an href to `/backlog-table#i`, `/goals#`, `/features#` or `github.com/…/pull/` is built anywhere in `scripts/` except `page_markup.key_link` (and its tests) |
| Four closed facets | a row carries a facet value no registry declares and the parser accepts it; or a fifth facet appears in a row's `⟦…⟧` block |
| Feature → goal | a feature node with no `anchors:` line (and no recorded reason) passes `check-features.py` |
| Explainer ↔ subject | an explainer with no declared subject, or a subject page that does not link back to it |
| Pages are current | a generated page's stamp is older than the newest merge on `origin/master` by more than one rebuild |
| Briefs are snapshots | a brief written after this spec contains a number that a generated page computes |

## 8. Choices this spec makes that the owner's answers did not settle

Each is a walkthrough question.

1. **Goal tree vs dashboard on "what changed".** The goal tree answers WHAT changed since T; the
   dashboard keeps WHY. Both answer half of "what changed" — the owner should confirm that split.
2. **The needs-you list's source** is the backlog `status: needs-you`, so a decision must be a row
   (consistent with backlog #394: a decision is a task plus NEEDS-OWNER).
3. **The status facet's syntax** — written in the row's `⟦…⟧` block beside `kind`, and the severity
   column reduced to glyphs.
4. **A backlog row's goal is DERIVED** through its area's feature node, not written on the row.
5. **Feature nodes with no fitting anchor** (15 of 28 today, e.g. `guard-and-gate-harness`,
   `process-harness`) — inherit the parent node's anchor, or declare `anchors: none — <reason>`.
6. **The link function's home** is `page_markup.py`, not `page_chrome.py`.
7. **Hand-authored explainer fragments** are not rewritten by `link_keys`; a check reports their
   unlinked keys instead.
8. **The dashboard's open-PR list is dropped** rather than kept with a written reason (C3).
9. **Row 11's duplicate-question check** is new tooling the page did not promise.

## 9. What was measured, and what was inferred

| Number | Status | Source |
|---|---|---|
| 28 feature nodes, 13 with `anchors:` | MEASURED | `docs/features.md` on `befd0e6d`, heading-and-line count |
| 422 backlog rows, all with `⟦kind:` | MEASURED | `grep -c` on `docs/backlog.md`, `befd0e6d` |
| 3 hand-built backlog hrefs, 1 PR href | MEASURED | `grep` over `scripts/`, `befd0e6d` |
| 37 / 12 / 0 needs-you counts; 29 unreadable | MEASURED | inventory, 2026-10-27 18:10 (roles page) |
| 0 PR links; 18–157 PR mentions per page; 358 feature → row links | MEASURED | inventory, 2026-10-27 |
| 49 of 68 dated pages are briefs; 4 mislabelled | MEASURED | roles page, 2026-10-27/28 |
| `✅` in severity on 117 of 333 rows | MEASURED | backlog #385, `9ac7c80d` |
| seven page producers | MEASURED | backlog #384, `f0dfef07` |
| 12 proposed rows, their order | ESTIMATED | this spec's judgement |
| "one rebuild" freshness bound | ESTIMATED | D3 says "not more than a minute behind" |

## Out of scope

Building any of the rows above; retagging rows; the review `component:` vocabulary; any new page.
After the walkthrough the rows are filed, then each is planned and built on its own branch.

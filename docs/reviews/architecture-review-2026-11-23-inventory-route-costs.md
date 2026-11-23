# Architecture review — the inventory rows' route costs

- **Date:** 2026-11-23
- **Convened on:** THRASHING — `check-merge-ready.py --pr 619` HOLDs: component `inventory-rows` carried
  fix-induced findings in round 2 (X1, X3) and round 3 (N2) of PR #619's review.
- **Subject:** how each non-SHIP row of `docs/marketplace/inventory.json` prices its cheapest publishing route
  (spec D10), at commit `471db86f` (branch `marketplace-task20`): the `route` object, the `Routes compared` prose
  in `notes`, and what `scripts/check-inventory.py` reads of either.
- **Reviewer:** Claude (Fable 5.2), one agent, no second half.
- **Legend:** **[M]** = a command I ran at `471db86f` (Python 3, macOS). **[I]** = inferred, not run.
- **Instruments and raw output:**
  `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/task20/phase6/`
  (`parse.py` reads every route figure out of the prose, written from scratch; `measure.py` is the census;
  `blind.py` edits a copy of the tree and runs the guard; `proto.py` is the prototype of option (a); outputs in
  `parse-out.txt`, `measure-out.txt`, `blind-out.txt`, `proto-out.txt`). Nothing in the repository was edited.

---

## 1. Verdict

**One real thrash (round 1 → round 2), then a prose floor (round 3). A redesign removes the class. File it; do
not fold it into PR #619.**

| Question | Answer |
|---|---|
| Thrashing or prose floor? | **Both, in sequence.** X1 and X3 are substance: figures were wrong because one number was asked two questions. N2 is presentation: every figure held. |
| Did the gate fire correctly? | **Yes.** Two consecutive rounds, fix-induced, one component. The round 3 coordinator's "Phase 6 does not arm" is a judgment about severity; the arming rule has no severity clause. |
| Do the figures at HEAD hold? | **Yes.** A third independent parser: 34 rows, 40 priced routes, 90 parts; every sum equals its parts; every recorded route is the cheapest priced one. [M] |
| Can a redesign remove the class? | **Yes, most of it.** The guard sees none of the route arithmetic today (7 of 7 planted defects pass). The prototype of option (a) refuses 6 of 8 and makes a seventh unwritable. [M] |
| Recommended | **Option (a)**, a `shared_work` table and per-row `routes` with named parts, checked by `check-inventory.py`. **FILED**, to land before plan Task 21 reads the inventory. |

---

## 2. The arming evidence, classified

| Finding | Caused by | What it was | Class |
|---|---|---|---|
| r2 X1 (Major) | r1 fold of C9 ("price shared work once") | 28 phase-1 template routes priced below the 4 h template they need; S2's 8 h fix counted in no consumer | **Substance — a representation defect** |
| r2 X3 (Minor) | the same fold | two routes at 0.5 h, below the 1 h re-run the row's own basis names | **Substance — hand arithmetic with no check** |
| r3 N2 (Nit) | r2 fold (sums written in prose) | `4 h 1 h next_project … about 3 h`: a sub-sum beside its parts, no separator | **Prose floor** |

**X1's cause is not carelessness.** Round 1's C9 asked that shared work not be counted twice, which is the question
"what does the whole package cost?". Round 2's X1 asked for each component's complete cost, which is D10's
question. Both are fair, and one scalar per row cannot answer both. The r1 fold made it answer the first; the r2
fold made it answer the second, and wrote "the figures are not to be summed across rows" into 34 notes. Measured
at HEAD [M]:

- the sum of the 34 recorded route figures is **256.25 h**;
- the same work with each piece counted once is **48.25 h** (own parts 36.25 h + the template 4 h + S2's fix 8 h);
- the template is a part of 27 chosen routes, S2's fix of 14.

So the published column overstates the work 5.3 times if a reader adds it up, and D10 itself describes the result
as a list of what "could be published at a known price". The warning against summing lives only in `notes`;
`--render` prints the route kind and no cost (`check-inventory.py`, `render`). [M]

**History replay.** One rule, "a template-repository route is at least the template", run against each commit's
`route` objects [M]:

| Commit | What it was | Template routes | Below 4 h |
|---|---|---|---|
| `3719d9e1` | before round 1 | 3 | 2 |
| `e5becb9e` | r1 fold | 33 | **30** |
| `52094467` | r2 fold | 30 | 2 |
| `471db86f` | HEAD | 30 | 2 |

The 30 at the r1 fold are X1's template half, visible to a one-line rule before round 2 ran. The 2 that remain are
`check-rc-contract` and `check-ratchet-contract`, half of backlog #705, and they predate this branch.

**N2 is the floor, and it has the same root.** The arithmetic is right (4 = 1 + 3). It reads wrongly only because
a sum is written as a sentence. A part with one `hours` field cannot be written that way.

---

## 3. The mechanism

**Cause 1 — the route figure's derivation is prose, so the guard cannot see it.** `check-inventory.py` checks that
a non-SHIP row has a `route` whose `kind` is one of four, whose `cost_hours` is finite and positive, and whose
grade is in the vocabulary (`_route_ok`, `[route]`). Nothing relates the figure to anything. Seven defects planted
in a copy of the tree, the guard run on each [M]:

| Planted | Guard |
|---|---|
| control, unedited | rc 3 |
| recorded figure contradicts its prose (13 → 1) | rc 3 |
| a prose sum that does not add up | rc 3 |
| the template priced at 2 h in one row, 4 h in 31 others | rc 3 |
| the r1 increment shape (template and S2 dropped, 1 h recorded) | rc 3 |
| a dearer route recorded as the cheapest | rc 3 |
| the whole `Routes compared` segment deleted | rc 3 |
| shared work "owned by" a row that does not exist | rc 3 |

rc 3 is the D1 checkpoint, the unedited answer. So every round's checking was a scratch script written for that
round (`fold2/check.py`, `r3check.py`, and this review's `parse.py`): three parsers of one prose convention, none
kept. [M] for the count; the first two are named in the coordinator documents.

**Cause 2 — a shared figure is copied, not referenced.** "4 h the template repository" appears as a part 32 times
and "8 h S2's code fix" 18 times. [M] They agree today. Changing either estimate is a hand edit of every copy plus
every recorded total that contains it.

**Cause 3 — "owned by" names a row, not a route that buys the work.** 17 parts say S2's fix is "owned by
brief-compose's row". That row's recorded route is `practice`, 0.25 h, and its own note says the practice "does
NOT fix S2 for any consumer". The 8 h lives in its `cost.public_bar_hours`. [M] So 14 chosen routes depend on work
that no row's recorded route contains. Each row is right under D10; the composition has no home for the shared
work. A lead for Task 22, which files the work items.

**Why it will recur.** [I] The owner rules on backlog #703 (a fifth route) and backlog #704 (the three unreached
libraries) at the Task 21 stop. Ruling (a) on #703 adds a priced route to most of the 34 rows; either ruling on
#704 re-prices three. Backlog #705 re-prices four more. Each is the same hand derivation, checked by a fourth
scratch script.

---

## 4. Options

| | What it is | Closes | Does not close | Cost and blast radius |
|---|---|---|---|---|
| **(a)** | Top-level `shared_work` (id, hours, owner row, what); per non-SHIP row a `routes` list, each route a kind with named `parts` (`own` + hours, or `shared` + id) or a `not_applicable` reason; the guard checks them | sums (unwritable: a total is derived); a shared figure priced two ways (unwritable); the increment shape for the template; a dearer route recorded; a missing comparison; a dangling owner; N2's class | the size of an `own` part (X3); whether a row needs a shared fix such as S2 (a code-reading judgment) | `check-inventory.py` rules, self-test cases, mutation manifest (144 entries today, a two-file edit); 45 rows of data. Additive: the guard already accepts the new keys (rc 3 with them present). [M] |
| **(b)** | Keep the prose; commit a parser of it as a guard rule | sums; cheapest; a missing segment | a shared figure priced two ways unless the parser also learns each phrase; N2's class (the parser must tolerate or refuse each phrasing); any new wording is a parser finding | A regex over free text inside a guard. My parser needed 6 stop phrases and 3 shared-work patterns for 34 rows written by one fold. [M] |
| **(c)** | Leave as is | nothing | all of it | None now; a scratch script per future edit |

**Prototype of (a)** (`proto.py`): the structured form derived from HEAD's prose is 34 rows, 40 routes, 90 parts,
about 7 KB against 30.7 KB of prose segments, and passes its four checks with 0 errors. [M] The same defects,
expressed in the structure:

| Defect | Result |
|---|---|
| recorded figure 13 → 1 | refused, `[route-cheapest]` |
| an own part changed, recorded figure not | refused, `[route-cheapest]` |
| a shared part priced differently in one row | cannot be written |
| the r1 increment shape | refused, `[route-complete]` |
| a dearer route recorded | refused, `[route-cheapest]` |
| no route priced | refused, `[route-parts]` |
| shared owner is not a row | refused, `[route-shared]` |
| only S2 dropped from a row that needs it | **missed** |
| an own part too small (X3's shape), total following it | **missed** |

**Why not (b).** It keeps cause 2 and turns cause 1 into a parser whose input is unconstrained English. That is
the layer the 2026-11-22 review of this same guard removed for its JSON inputs.

**Why not (c).** The figures are right today, so (c) is defensible for this PR. It is not defensible for the
inventory: three known re-pricings are queued before Task 21.

---

## 5. Recommendation — option (a), FILED

### 5.1 The shape

- **`shared_work`**, top level: `[{"id": "template", "hours": 4.0, "owner": "skill-brief", "what": "…"}, …]`.
  Three entries today: the template (4 h), S2's code fix (8 h), the delivery-contract fix (3 h).
- **`routes`**, on every non-SHIP row: one entry per D10 route kind. Either
  `{"kind": …, "parts": [{"own": "<what>", "hours": N} | {"shared": "<id>"}], "limit": "<optional>"}` or
  `{"kind": …, "not_applicable": "<one clause>"}`.
- **`route`** stays as it is (kind, `cost_hours`, grade). Task 21 reads it. It becomes a checked copy.
- The `Routes compared` prose leaves `notes`. The reasons it carries move into `own`, `limit` and
  `not_applicable`; the code citations for an S2 judgment stay in `notes`.

### 5.2 The rules

| Rule | Refuses |
|---|---|
| `[route-parts]` | a non-SHIP row that does not price or excuse each of the four kinds; a part with neither `own` nor `shared` |
| `[route-shared]` | a `shared` id that `shared_work` does not have; an `owner` that is not a row |
| `[route-complete]` | a `template-repository` route without the `template` part |
| `[route-cheapest]` | a `route.cost_hours` or `kind` that is not the minimum over the priced routes |

A fifth, optional and not prototyped [I]: `shared_work[].needed_by`, the rows whose operation fails without that
work, stated once. `[route-complete]` then refuses a listed row that omits the part. This moves the S2 judgment
from 34 notes to one list and would turn "only S2 dropped" into a refusal.

### 5.3 Why FILED, not in PR #619

- **The rows are right.** Three independent parsers agree on 34 of 34. Nothing in this PR is known wrong.
- **Nothing reads the inventory before Task 21**, where the owner stops. The route figures feed no gate: the D1
  checkpoint reads `cost`, not `route` (`checkpoint_fires`). [M]
- **The blast radius is a guard, not data.** New rules, self-test cases and mutations deserve their own review
  rounds. PR #619 is at round 3 of a data review, and the round cap files from round 4.
- **It must precede the queued re-pricings**, or each is done by hand once more.

**Sequence:** merge PR #619 → the filed row (which absorbs backlog #705's re-pricing: the later rows are priced for
the first time *through* the new field) → fold the owner's rulings on backlog #703 and #704 → Task 21.

### 5.4 The backlog row, drafted (not written to `backlog.md`)

> | *next free number* | 🟡 **The inventory's route costs are hand arithmetic in `notes` that `check-inventory.py`
> cannot see: give them a `shared_work` table and per-row `routes` with named parts, and check the recorded route
> against them** — filed 2026-11-23 by the Phase 6 review of PR #619
> (`docs/reviews/architecture-review-2026-11-23-inventory-route-costs.md`). MEASURED at `471db86f`: seven planted
> route defects (a figure contradicting its prose, a sum that does not add up, the template priced two ways, the
> round 1 increment shape, a dearer route recorded, the comparison deleted, a dangling owner) all leave the guard
> at rc 3; the 34 recorded figures sum to 256.25 h for 48.25 h of work, because 27 routes each carry the 4 h
> template and 14 the 8 h S2 fix; 11 later-phase non-SHIP rows carry no route comparison at all. **Do:** add
> top-level `shared_work` (id, hours, owner row) and, on every non-SHIP row, `routes` (each D10 kind priced as
> named parts, own or shared, or excused in one clause); add the rules `[route-parts]`, `[route-shared]`,
> `[route-complete]`, `[route-cheapest]` with self-test cases and mutations; migrate the 34 phase-1 rows
> mechanically (the review's parser derives 40 routes, 90 parts, 0 errors) and price the 11 later-phase rows
> through the new field, which closes backlog #705's re-pricing; remove the `Routes compared` prose. Land it before
> the owner's rulings on backlog #703 and #704 are folded into rows and before plan Task 21. **Fails if** any of
> the seven planted defects, expressed in the new fields, leaves `check-inventory.py` at the unedited tree's exit
> code; or any non-SHIP row has no `routes`; or a `Routes compared` segment remains in `notes`. NOT closed by this
> row: the size of a row's own part, and whether a row needs a shared fix (unless `needed_by` is built).
> ⟦kind: task⟧ | `scripts/check-inventory.py`, `scripts/mutations/check-inventory.json`,
> `docs/marketplace/inventory.json` | M | (process / deliverable #2) | 🟡 **FILED 2026-11-23** |

The area `(process / deliverable #2)` is claimed in `docs/features.md` (line 204) and is the one backlog #703 to
#705 use. [M]

---

## 6. FAILS IF, bounds, and the stop condition

**The recommendation is wrong if** (each an observation):

- the mechanical migration of the 34 phase-1 rows does not reproduce all 34 recorded figures with 0 rule errors.
  Then the prose does not hold what this review measured in it;
- after the migration, a review round finds a wrong route figure in a migrated row that none of the four rules
  reports **and** that is neither of the two stated bounds. Then the structure did not hold the class;
- Task 21 publishes with no route re-priced and no shared estimate changed since `471db86f`. Then the redesign
  bought nothing over option (c), and its cost was misjudged here;
- the filed row needs a change to spec D10 to land. Then it moves the goal and is the owner's, not a filed task.

**Bounds — what (a) does not give:**

- The four rules check arithmetic and references. Every hour figure stays `argued`; nothing was run.
- X3's shape, an own part smaller than the row's stated verification, is caught only by a reader. The structure
  makes the part visible and named; it does not price it.
- Whether a row needs S2's fix is a reading of that row's code path (fails, or degrades at rc 0). Without
  `needed_by` it stays a per-row judgment.
- `[route-complete]` knows one kind-to-part link (the template). A second such link is a second entry.
- The parser that migrates the prose is a one-off; it is this review's instrument, not a guard.

**Stop condition.** After the filed row lands, one review round. A finding fixed by correcting a part or adding a
`shared_work` entry is the design working. A finding that needs a fifth scratch parser is the question returning.

---

## 7. What did we decide this milestone that is not written down

- **A route figure is a component's complete cost, so the column must not be added up.** Stated in 34 `notes`
  and the round 2 coordinator document; not in spec D10, not in `CONTEXT.md`, not in `--render`. [M]
- **0.25 h means "already done, or priced in another row".** The guard refuses 0, so the fold chose a floor. Five
  own parts carry it. [M] It is a sentinel inside an estimate column, defined only in prose.
- **A fix is added to a route only where the operation FAILS without it, not where it degrades.** A page written
  without the Ask tray at rc 0 counts as publishable. That is a product judgment about what a stranger gets, made
  in a review fold.
- **Shared work has an owning row but no owning route** (section 3, cause 3). Nothing says which backlog item
  Task 22 files for S2's fix, since `brief-compose`'s recorded route does not contain it.
- **The four-route comparison was applied to the 34 effort-(3) rows only.** Round 1's disposition says "every
  non-ship row names the four routes". 11 later-phase non-SHIP rows have no comparison. [M] Backlog #705 names four
  of them, for the increment shape; the other seven are not recorded anywhere as unpriced by comparison.
- **27 of 34 phase-1 components are cheapest as a template repository**, which each row says "is not D3's plugin
  channel". [M] The inventory's answer for this package is therefore mostly not a plugin. Backlog #703 holds the
  route question; nothing states this consequence for D3.

---

## 8. Not measured — treat as NOT RUN

- The redesign itself. `proto.py` is a prototype over derived data; no rule was added to `check-inventory.py`, no
  self-test case or mutation written, and the full guard's behaviour with the rules is unknown.
- `needed_by` (5.2). Not prototyped.
- The 11 later-phase rows under the new field. None was priced; the two template rows were only compared with 4 h.
- Whether any hour figure is right. Every one is `argued`.
- The S2 fail-or-degrade citations. Round 3 opened them; this review did not reopen them.
- A second reviewer half. This is one agent's review.
- Linux and CI's Python. Every [M] is macOS.
- The cost of the filed row. Size M is a judgment, not a measurement.

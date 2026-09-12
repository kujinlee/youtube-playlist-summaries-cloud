# A goal knows its items, its pull requests, and whether anyone is still working on it

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**v2, 2026-09-11** (v1 same day; §3.2a and the §5 card revised — the flat PR list became a
`spec → plan → shipped` chain, on the user's refinement). Raised by the user from the live pages: *"current goal list isn't very coherent
with backlog groups or tags"* and *"current dashboard just lists activities without expressing
progress of each goal."* Their framing is the spec's thesis — **backlog, goals and dashboard should
express different aspects of the same project activity**, and they are currently three separate
models that happen to describe the same project.

⚠ **Header order is load-bearing** — `check-anchors.py` sets `HEAD_LINES = 10`.

⚠ **EVERY COUNT IN THIS DOCUMENT IS DATED AND CARRIES ITS METHOD.** Row #90 advertised *"24 cases,
8 mutations"* and both numbers were false within the hour. The counts here describe a **corpus on
2026-09-11**, not a contract; nothing downstream should assert them.

---

## 1. What is actually wrong, measured

The three pages are keyed by three different things and share almost no structure.

| Page | Unit | Count (2026-09-11) | Keyed by | Expresses progress? |
|---|---|---|---|---|
| `/backlog` | item | 113 rows (70 open / 43 closed) | a number | per-row severity only |
| `/goals` | goal | 11 anchors | a stable name | **no** — shows doc count + last-touched |
| `/dashboard` | entry | 160 entries | a date | **no** — reverse-chronological |

**The joins between them barely exist.** Measured by the repo's own parsers, not by hand:

| Join | Mechanism today | Coverage |
|---|---|---|
| item → group | `GROUPS` in `gen-backlog-page.py` | 40 of 70 open items, 6 groups |
| item → tag | the `Bundle` column | 18 free-text values over open rows |
| **item → goal** | `ROOTS` + `DEPENDS` | **6 items, all naming ONE of the 11 anchors** |
| **commit → item** | `(backlog #N)` at subject tail | **7 of 200 subjects** |
| **entry → goal** | — | **nothing; no field exists** |

Three consequences follow, and each is visible on the page right now:

**(a) `/goals` cannot show progress because it has nothing to count.** Ten of eleven anchors have
zero backlog items attached, so the card falls back to `20 doc(s) · last touched 2026-09-08` —
which measures *how much writing happened*, not how far the goal got.

**(b) The page describes a different project than the one being worked on.** Classifying 256
squashed-PR commits (method in §7) puts **~70%** of merged work in harness-and-comprehensibility
territory, against **~10%** in the product goals the registry mostly names. `status-visibility`
holds **20 of the 45** anchor-declaring documents because it became the default home for work that
had no anchor of its own.

⟳ **That pair went stale while this document was being written, and the cause was this document.**
Adding it made the figures 21 of 46 — it declares `status-visibility` itself, for want of an anchor
covering harness work, which is the same gap the sentence describes. Recorded rather than silently
corrected, because it is the §1 warning happening to the paragraph that states it.

**(c) A document's `Goal:` line is reprinted under every document in the card's list.** On the
`status-visibility` card that is 20 identical lines. It is redundant *by construction* — the line is
the same for every document under an anchor — so it can never carry information.

### 1.1 Groups are goals, written a second time

Taking the six hand-written groups and asking how many distinct goals their members map to:

| Group | members | distinct goals | purity |
|---|---:|---:|---:|
| Anonymous users hold more database access than intended | 3 | 1 | **100%** |
| Checks that can be wrong without looking wrong | 3 | 1 | **100%** |
| Paid work can be lost when a video's address changes | 7 | 2 | 86% |
| Money-path edge cases | 6 | 2 | 83% |
| Product features you might actually want | 10 | 3 | 80% |
| **The reusable toolkit — the second deliverable** | 11 | **4** | **36%** |

Five of six groups are one goal each. This repo already runs `check-vocabulary-collisions.py` on the
principle *one mechanism per concern*; **groups and goals are a duplicate protocol**, and it is the
class that guard exists for — hiding in data rather than in code, where the guard cannot see it.

**The outlier is the finding.** The group that fails the pattern is the one whose title names a
*deliverable*. It splits four ways because it sits a level **above** goals, not beside them.

---

## 2. The model

```
DELIVERABLE            the product  ·  the reusable harness
   └── GOAL            an anchor — a name that survives a rename (ADR-0010)
         ├── backlog items     what is LEFT        → open / closed counts
         ├── PRs and commits   what was DONE       → activity, recency
         └── documents         specs, plans, ADRs  → decisions
```

Split by deliverable, open work is **38 product / 32 harness** — near even, and neither page shows
the split at all.

Each page then asks one question of the same model:

| Page | The question it answers |
|---|---|
| **backlog** | what is *left*, per goal |
| **goals** | how far each goal has *got*, and whether it is still moving |
| **dashboard** | what *happened*, and which goal it moved |

⛔ **This does not change what `docs/anchors.md` holds.** Its opening states the file holds **names,
not state**, and that adding status or progress columns is forbidden because a central file holding
state drifts — measured twice in this project. **Every count and every lifecycle state in this
design is computed at render time from items, git and documents.** Nothing is stored in the registry.

---

## 3. The three joins

Only one needs data that does not exist.

### 3.1 doc → goal — exists, unchanged

The `> **Anchor:**` header. 46 documents carry one as of this commit; `check-anchors.py` enforces it
for anything dated 2026-08-25 or later, reading the first `HEAD_LINES = 10` lines
(`check-anchors.py:61`). No change.

### 3.2 PR → goal — DERIVED, no new convention

Resolved in priority order, first hit wins:

1. **A document's declared anchor.** If the PR touches an anchor-declaring spec or plan, inherit
   that anchor. *This is the strongest signal and the one two earlier attempts missed* — see §7.
2. **Code paths touched**, after subtracting the files this project's own policy makes nearly every
   PR touch (`docs/reviews/`, `docs/backlog.md`, `docs/dashboard-entries.md`,
   `docs/roadmap-to-launch.md`, `docs/anchors.md`, `tests/`).
3. **`(backlog #N)` at the subject tail**, resolved through the item's goal. Uses
   `check-backlog-closure.py`'s existing `CLOSING` regex — **called, never re-implemented** (§6).
4. Otherwise **unattributed**, and the page says so rather than guessing.

Measured 2026-09-11: 1 and 2 together attribute **200 of 256** PR commits (**78%**). The design
requires that the remainder is *displayed as unattributed*, not silently dropped.

⚠ **A zero here means the deriver is broken, not that a goal is idle.** The distinction is the
subject of falsifier F4.

### 3.2a The implementation chain — spec → plan → shipped

⟳ **Added v2, 2026-09-11**, on the user's refinement: *"goals lists many docs: spec → plan →
implementation (commits → PRs). Currently it only lists spec and plan doc. I hope related
implementations can be found."*

A flat per-goal PR list satisfies "findable" and **throws away the lineage**, which is the part worth
having. The chain is derivable from three signals that already exist:

| Link | Derivation | Measured 2026-09-11 |
|---|---|---|
| spec ↔ plan | shared stem — `<date>-<stem>-design.md` ↔ `<date>-<stem>.md` | **60 pairs** (94 specs, 92 plans) |
| document → PR | `git log --follow -- <path>`, taking `(#N)` from subjects | **45 of 46 (98%)** anchor-declaring docs |
| document → goal | the declared `Anchor:` header | 46 documents |

The single document recovering no PR is this spec, which is unmerged — **correct behaviour, not a
gap**, and it is the natural falsifier fixture for F7.

⭐ **The PR is the atomic implementation unit here, not a commit range.** This repo squash-merges, so
a branch's whole history collapses to one commit on `master`. Chasing individual commits would
reconstruct something `master` does not contain; the `(#N)` suffix is the durable identity.

**Two work shapes, and the card must distinguish them.** Only **57 of 283** merged PRs have a
document behind them. The rest are direct work — a backlog fix, a guard, a page repair — with no spec
and no plan, and they are not lesser work. So:

* **Document-led work** renders as a chain: `spec → plan → shipped PR`, with any stage that does not
  exist shown as absent rather than omitted. A plan with no shipped PR is *in flight*; a spec with no
  plan is *not started*. Both are states worth seeing.
* **Direct work** renders as a plain PR line, attributed by §3.2's path rules.

⚠ **Coverage is bounded by the anchor requirement, and the page must say so.** `check-anchors.py`
requires a header only for documents dated 2026-08-25 or later, so of 186 documents under
`docs/superpowers/`, **46 declare an anchor** and the remainder are invisible to this page. That is
the registry's deliberate living/dead split, not an error — but an unstated denominator is how a
partial view gets read as a complete one, so the count of excluded documents is rendered.

### 3.3 item → goal — the one new declared field

**The `Bundle` / tag column becomes a controlled vocabulary of goal names.** It already carries 18
values that are *trying* to be goal names, including the live collision `cloud / money` vs
`cloud/money`, and the four-way split `product` / `product / renderer` / `product / addressing` /
`product / dig-deeper`.

This is a per-row declaration, so there is no central map to drift — which matters for the same
reason `anchors.md` refuses to hold state.

**A row may name exactly one goal.** Items that genuinely serve two goals are a real case (#60 is
both a corrections slice and in the addressing group) and the rule is: **name the goal the work
would be scheduled under**, and let the other relationship live in the row's prose. Allowing two
would make every count ambiguous and every progress figure unfalsifiable.

---

## 4. The lifecycle — three states, all derived

The user asked for historical goals to appear as a *done* category. Two states are not enough, and
the reason is `stable-blob-addressing`: **zero activity since 2026-08, and 7 open items, 4 of them
HIGH.** Filing that under "done" would assert something false. Idleness is not completion.

| State | Rule | Goals (2026-09-11) |
|---|---|---|
| **DONE** | no open items | 3 — `cloud-publishing`, `serve-path-bounding`, `cloud-blob-key-encoding` |
| **ACTIVE** | open items **and** activity within the window | 4 |
| **DORMANT** | open items, no activity for the whole window | 9 |

**The window is a declared constant with a stated default of 30 days**, rendered on the page as
*"idle N days"* so the reader can see the input rather than infer it.

### 4.1 What the split exposes, and why it justifies itself

| | goals | open items | **HIGH items** |
|---|---:|---:|---:|
| ACTIVE | 4 | 32 | **6** |
| DORMANT | 9 | 38 | **15** |

**15 of the 21 open HIGH-severity items sit in goals nobody has touched for over a month** —
addressing (4), money (3), corrections (3), anon-privilege (3), sync (1), prod-smoke (1). The
current page renders every one of them identically to actively-worked goals. This sentence is the
single most useful thing the page is not saying, and it is derived, so it cannot go stale.

### 4.2 Counts, never a percentage

Cards show `7 open · 9 closed`, **not** a progress bar. A closed backlog item is not a fraction of a
goal achieved, and this project has recorded the cost of progress figures whose denominator did not
mean what it claimed. A bar implies completion semantics that nothing here can support.

---

## 5. The goal card

Sections are `<details>/<summary>`, **reusing the markup already present** — 21 occurrences in
`gen-dashboard.py`, 6 in `gen-backlog-page.py`, and **0 in `gen-goals-page.py`**, which is the only
one of the three without it.

```
  ACTIVE ───────────────────────────────────────────────────────

  gates-are-honest                    20 open · 5 high · 89 PRs
                                            last activity 2026-09-11
  <goal sentence>
  DECISIONS  [ no ADR recorded ]
  ▸ BACKLOG 20 open · 12 closed   ▸ PULL REQUESTS 89   ▸ DOCUMENTS 4

  DORMANT — open work, nothing merged since ────────────────────

  stable-blob-addressing          ⚠ 7 open · 4 HIGH · idle 34 days
  <goal sentence>
  DECISIONS  [ ADR 0006 ] [ ADR 0007 ]
  ▸ BACKLOG 7 open · 9 closed   ▾ WORK 7 threads · 28 PRs
      mutation-manifest-retarget                          ✅ shipped
         spec  2026-08-29-…-design.md   plan  2026-08-29-….md
         PR #176  2026-08-29  Retire the plan-as-CI-dependency…
      blob-addressing-reservation                      ⏸ in flight
         spec  2026-08-07-…-design.md   plan  —  (none written)
         no PR yet
      ── direct work, no document ──────────────────────────────
         PR #67   2026-08-14  Serve-path deadline
  MILESTONES  <spine, where one exists>

  DONE ─────────────────────────────────────────────────────────
  ▸ cloud-publishing · serve-path-bounding · cloud-blob-key-encoding
```

- **Expanded BACKLOG** lists `#num`, severity marker, title, linked to the backlog page.
- **Expanded WORK replaces the flat PR list** (§3.2a). Document-led work renders as a
  `spec → plan → PR` thread with a state — **shipped**, **in flight**, **not started** — and a
  missing stage is drawn as absent, not omitted. Direct work follows under its own rule, with the
  **attribution method shown** (anchor / path / backlog-ref) so a reader can judge it rather than
  trust it. The count of documents excluded for having no anchor is rendered here too.
- **DOCUMENTS as a separate section disappears** — every document now appears inside the thread it
  belongs to, which is what the user asked for and also kills §1c's twenty repeated goal sentences.
- **DONE goals collapse to a single line** — findable, not competing for attention.

---

## 6. Constraints this design accepts from existing rules

- ⛔ **Never re-implement another script's rule.** PR→item attribution calls
  `check-backlog-closure.py`'s `CLOSING`; severity and row parsing call `gen-backlog-page.py`'s
  `parse`. This project has recorded **seven** instances of a second implementation drifting, and
  **two occurred while measuring for this very spec** — a hand-written severity regex that
  miscounted critical rows, and a hand-written closing regex that reported 0 matches where the real
  one finds 7.
- ⛔ **`docs/anchors.md` holds names, not state** (§2).
- ⛔ **A gate that cannot run is a failure.** Any deriver that finds no git history, no backlog file
  or zero anchor-declaring documents must report **CANNOT RUN**, not an empty page.
- The goals page stays **derived with no hand-maintained content** and keeps its hook
  (`regen-goals-page.sh`); the item→goal source is added to that hook's watched set, whose omission
  is the documented failure mode for a five-source page.

---

## 7. Method, and three wrong measurements worth recording

The PR classification in §1b and §3.2 was wrong three times before it was right, each time in the
same direction, and the sequence is recorded because the failure is reusable.

1. **Ranked raw path frequency.** Top hits were `docs/reviews` (534), `docs/backlog.md` (114),
   `docs/dashboard-entries.md` (114) — files this project's *own policy* makes nearly every PR
   touch. High frequency, zero information.
2. **Subtracted policy files, but ordered the rules badly.** `^tests/` was checked before the domain
   paths, so every PR shipping tests classified as harness. Result: blob-addressing showed 2–4 PRs.
3. **Subtracted `docs/superpowers/` as noise too** — which deleted the entire evidence of a
   design-phase goal. Blob-addressing's work product *was documents*: its convergence ran 17 review
   rounds.

**The fix was not a better rule.** It was using the signal the repo already maintains — the
documents' own `Anchor:` headers — which attributes **57** PRs that no path rule can see. With that
first in priority order, the monthly breakdown reproduces the sequence the user recalled
independently: product build-out (July) → addressing (August, 28 PRs) → comprehensibility and
harness (August onward, 64% of September).

⚠ **A human's recollection is evidence.** The classifier was corrected three times by disagreeing
with it, and the classifier was wrong every time.

---

## 8. Falsifiers

Each states an observation that makes the design **fail**, not a box to tick.

- **F1 — The lifecycle is unfalsifiable if every goal lands in one bucket.** Fails if, over the real
  corpus, all goals compute to the same state. *Measured 2026-09-11: 3 done / 4 active / 9 dormant —
  the rule discriminates today.* Re-measure after the tag migration; a rule that stops
  discriminating is dead whether or not it still runs.
- **F2 — The tag column is not a controlled vocabulary if a row can name a goal that does not
  exist.** Fails if any row's tag is absent from the anchor registry. This is a mechanical check and
  must exist before the migration is called done.
- **F3 — Groups are not retired if any group's membership stops matching its goal.** Fails if a
  retained group contains a member whose declared goal differs from the group's.
- **F4 — PR attribution is broken, not idle, when a goal shows zero PRs.** Fails if a goal with
  merged work in git shows zero attributed PRs. ⚠ **A zero and a correct zero look identical** — the
  page must therefore render the *unattributed* count beside the per-goal counts, so the two cases
  are distinguishable by looking.
- **F5 — The card is stale if the goals hook does not watch the item→goal source.** Fails if editing
  a backlog row's goal does not rebuild the page.
- **F6 — "Idle N days" is a claim about git.** Fails if the rendered idle figure disagrees with the
  last merge touching that goal.
- **F7 — A thread's state is a claim about what shipped.** Fails if a thread marked *shipped* names
  a PR that `git log --follow` on its own documents does not reach, or if a thread marked *in
  flight* has a merged PR touching it. ⚠ **The fixture exists already and is not synthetic:** this
  spec is the one document of 46 that recovers no PR, so it must render as *in flight* today and
  flip to *shipped* on merge. A falsifier that cannot be observed changing is not one.
- **F8 — Excluded documents must be counted, not hidden.** Fails if the page shows anchor-declaring
  documents without stating how many were excluded for lacking an anchor. Measured 2026-09-11: 46 of
  186. A partial view with an unstated denominator reads as a complete one.

---

## 9. Out of scope

- **Renaming the goals.** The five placeholder names (`gates-are-honest`, `product-features`,
  `portable-toolkit`, `local-renderer`, `least-privilege`) are working labels. The user's decision,
  stated 2026-09-11: *"these names are just off my memory. better names can be derived later."* The
  structure does not depend on them.
- **Allocating the new anchors.** `check-anchors.py` refuses an anchor no document claims, so
  minting names is gated on documents existing — a separate step with its own review.
- **Splitting stories from tasks** — `docs/backlog.md` row #90's other half, still 🟡 open and
  needing a decision before anyone builds.
- **The dashboard's goal dimension.** The user's stated order is goals first, dashboard second. The
  dashboard gains a goal per entry only once item→goal exists to derive it from. Named here so the
  sequencing is deliberate rather than forgotten.
- **Retiring the three DONE anchors.** Whether a completed goal is deleted or kept as history is the
  user's call; this design only stops them competing for attention.

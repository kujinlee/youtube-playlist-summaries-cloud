# Feature hub — a derived map of what this system does, and what it deliberately does not

> **Anchor:** `feature-map` — **ADR:** none
> **Goal:** Anyone can find what the system does today, what it is missing on purpose, and every fragment that defines each — without searching.

## Why this exists

**Asked on 2026-09-19, after a day spent reviewing one slice: *"where can I find currently
implemented behaviours?"*** The honest answer was nowhere. The knowledge existed, and it was in six
places at once — a spec holding the original intent, a PR body holding one delta, seven review
documents holding point-in-time findings, code comments holding the corrections, a 142-row backlog
holding the gaps, and a dashboard holding what changed while you were away.

Every one of those is a record of a **moment**. None of them answers *what is true now*.

The traditional fix is a technical writer assembling a formal document at the end. That is too late
to help during development, and it is stale the week after it ships.

### The three pages that already exist, and the question none of them answers

| Page | Answers |
|---|---|
| `/dashboard` | what changed while I was away |
| `/backlog-table` | what is open |
| `/goals` | what we are aiming at |
| — | ⛔ **what does this system currently do** |

## What it is

**A hub of links, not a synthesis.** The page is mostly pointers to living fragments. That is the
property that keeps it honest: a second copy of a fact can disagree with the first, and this project
has measured that repeatedly. A link cannot.

It is rendered at `/features` from `docs/features.md`, and **everything on it except one paragraph
per node is derived** — the same discipline `gen-goals-page.py` states for itself:

> *"ADR-0010's rule is point at the roadmap for state, never copy it — a page holding its own copy of
> 'where things stand' becomes the fourth document that drifts."*

## The spine: a feature tree, not the anchor registry

The obvious move was to hang this off the existing `anchors.md`, which is already a curated,
rename-surviving, machine-validated vocabulary. **That was tried and rejected**, because the anchor
list is not organised by feature — it mixes three different kinds of thing:

| Anchor | Actually a |
|---|---|
| `share-and-download`, `corrections-in-cloud` | product feature |
| `stable-blob-addressing`, `serve-path-bounding` | platform property |
| `prod-smoke`, `review-decides-itself` | development tooling |

No hierarchy over that list reads as feature structure, because the list is not one thing. So the
spine is a purpose-built tree and **anchors attach to it** rather than forming it. Anchors keep
exactly the job ADR-0010 gave them: rename-surviving membership for documents.

⚠ **This is a display taxonomy, not a second coordination mechanism.** Nothing declares membership
*in* the tree directly; every fragment reaches a node through a declaration it already carries. That
distinction is what keeps `scripts/check-vocabulary-collisions.py` satisfied — one mechanism per
concern, reused rather than duplicated.

### Three trunks

```
PRODUCT             — what a person can do
PLATFORM            — how it runs
DEV INFRASTRUCTURE  — the harness, this project's second deliverable
```

Three rather than two because roughly half this repo's backlog is tooling and comprehensibility.
Folding that into "supporting machinery" would misrepresent where the work actually goes, and it is
the half whose shape is hardest to remember.

⭐ **The tree immediately exposes a hole the goal-shaped registry could not:** *Job queue & worker
lifecycle* is the busiest area of the last month — PRs #318, #319, #320, #321, #322 — and no anchor,
spec node or design document claims it. An absence is only visible against a structure that expected
something there.

## Node states: `built` and `absent`

A first version of this design required every leaf to have at least one fragment, reasoning that
empty nodes would accumulate as aspiration. **That rule was wrong, and the objection that killed it
is the more important half of this design:** a page about current behaviour is incomplete without
declared absences. A necessary feature that does not exist has no spec, no backlog row and no code —
so under that rule it could never appear, and its absence stayed invisible.

| State | Must have | Must NOT have | Renders as |
|---|---|---|---|
| `built` | ≥1 fragment | — | a normal node |
| `absent` | a one-line `expected-because:` | any fragment | *"not built — expected because …"* |

```markdown
### rate-limiting-per-account
state: absent
expected-because: standard for a hosted multi-tenant service; one account can
  currently exhaust the shared spend cap.
```

**The justification line is the only barrier to entry, and it is deliberately the only one.**
Aspirational nodes are not blocked by a rule — they are blocked by nobody being able to finish
*"expected because…"* honestly. An optional idea simply has no node, because there is nothing true
to write on that line.

Both directions are enforced: an `absent` node that acquires fragments fails, telling the author to
flip it to `built`. A feature cannot quietly get implemented while the tree still says it does not
exist.

⚠ **Accepted knowingly:** declared absences accumulate, and nothing forces one to resolve. The page
shows a count (*"4 declared absences"*) so growth is visible. A cap was rejected — it would push
people to not declare, which is the failure being fixed.

## What attaches to a node, and how

| Fragment | Attaches via | New work |
|---|---|---|
| specs, plans | the node names its anchors; specs/plans already declare theirs | none — see the amendment below |
| ADRs | the anchor registry's existing ADR column | none |
| **backlog rows (known gaps)** | an `areas:` alias line on the node | ~21 aliases, declared once — **not 140 row edits** |
| review documents | filename stem plus anchor | none |
| recent changes | `git log` subjects carrying `(#N)` | none |
| prose | `features.md`, hand-written | the only rot surface |

### The alias line earns its keep

Backlog rows already carry an informal `(area)` tag, and it has **already drifted** — measured
2026-09-19, `(cloud/money)` and `(cloud / money)` exist as separate values 40 rows apart. Nothing
reads that column, so nothing caught it.

Putting the aliases **inside the node** forces both spellings onto the same line, where the
duplication is obvious, and makes an unclaimed area a failed check rather than a silent orphan.

### ⟳ AMENDED 2026-09-19 — the anchor edge points ONE way, and the `Feature:` column is dropped

This spec first said `anchors.md` would gain a `Feature:` column, so each anchor named its node. The
implementation plan instead had each node name its anchors. **Both directions for one edge is a
duplicate edge**, and review round 1 caught it from both halves — the column was added by the plan
and then read by nothing.

Resolved in favour of **the node naming its anchors**, and the column is not added. The reason the
usual ADR-0010 argument ("the edge lives in the document, so the index is derived") does not apply:
`features.md` IS the index, and an index that lists its own members is the maintained index ADR-0010
rejects — *unless the listing is validated*, which here it is. `check-features.py` requires **every
anchor in the registry to be claimed by exactly one node**, so an anchor added, renamed or removed
turns the check red rather than silently disappearing from the page. That guard is what makes the
cheaper direction safe, and it is the same shape as the `areas:` rule beside it.

### The prose rule

One paragraph per node, and it may say only **what this feature is for**. Never how it works, never
where it stands — those are what the links beneath it are for.

This bound is the whole anti-rot argument for the one hand-written element: a sentence that never
mentions state has almost nothing that can become false, and it cannot contradict the fragments
under it.

**"Says only what it is for" has to be decidable, or the check cannot exist.** A status token is any
of: a status marker (`✅ 🔴 🟠 🟢 ⏳ ◀`), a PR or issue reference (`#` followed by digits), or one of
the words *currently, now, already, still, yet, planned, in progress, done, TODO*. Prose containing
one fails. The list is deliberately short and literal — a fuzzier rule would be argued with rather
than obeyed.

## Components

| File | Role |
|---|---|
| `docs/features.md` | the tree, the prose, the `areas:` aliases. Names, never state |
| `scripts/gen-features-page.py` | renders `/features`; `--self-test` |
| `scripts/check-features.py` | validation; `--self-test`; CI-wired |
| `.claude/hooks/regen-features-page.sh` | rebuild when any source changes |


Served by the existing explainer server on port 7391. No new serving mechanism, no new hook pattern,
no new registry idea — every one of these mirrors something `/goals` or `/backlog` already does.

## Enforcement

`scripts/check-features.py`, wired into CI's `verify` job:

| Rule | Catches |
|---|---|
| every `Feature:` in `anchors.md` resolves to a node | a renamed or deleted node |
| every in-use backlog `(area)` is claimed by **exactly one** node | the measured `cloud/money` duplicate, and future drift |
| a `built` leaf has ≥1 fragment | nodes that claim implementation they cannot evidence |
| an `absent` node has `expected-because:` and no fragments | silent emptiness; and implemented-but-still-declared-absent |
| prose present, and contains no **status token** (below) | prose becoming a status report |
| `backlog.md` unparseable → **exit 2** | "cannot run" being reported as a pass |

## Falsifiers

- Delete a node that `anchors.md` references → `check-features.py` fails naming it.
- Add a `built` leaf with no fragments → fails.
- Add an `absent` node with a fragment → fails, instructing the flip to `built`.
- Introduce a second spelling of an existing backlog area → fails as an unclaimed area.
- Write `currently`, `#322` or `✅` into a node's prose → fails, naming the token.
- Corrupt `docs/backlog.md` → exit 2, reported as NOT RUN rather than passing.

## Deliberately out of scope

- **Tests and code modules never appear as fragments.** They are the only non-drifting record of
  behaviour, and rendering 2,743 test names was the first design considered — it was rejected as
  too granular to read. Node prose plus linked design fragments carry the meaning instead.
- **`/goals` is not retired, and the re-evaluation is SEQUENCED rather than merely deferred**
  (decided 2026-09-19). It stays as-is until the tree's nodes exist, and is then re-examined against
  them — because the question *"does a goal fold into a feature node?"* cannot be answered before
  there are nodes to fold into. The expectation going in, recorded so a later reader can see whether
  it held: **most goals will align naturally with a feature node, and some will not** — the ones that
  will not are likely the anchors already identified as platform properties or tooling rather than
  features. Absorbing a goal into the taxonomy is expected to be cheap; the sequencing exists because
  the *answer* is unknowable now, not because the work is hard.
- **No new backlog rows are required by this design.** Known gaps attach through the alias map if
  they are filed; undeclared gaps stay invisible, which is why `absent` nodes exist.

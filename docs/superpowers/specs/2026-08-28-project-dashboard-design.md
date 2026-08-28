# Project Dashboard — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** **v4 — CUT TO THREE THINGS by user decision 2026-08-28, after two review rounds.**
v1–v3 and both review rounds are in git history and `docs/reviews/spec-project-dashboard-r{1,2}-*.md`.
This version deliberately does less.

---

## 1. Why this exists

The user's words:

> "I am having hard time to understand your output on chat dialogs… I cannot monitor closely what you
> are doing and I lost in flooding text."

Ranked by them:

| Rank | Problem |
|---|---|
| **1** | **Continuity** — cannot hold the thread across a day or a week |
| 2 | Volume with no signal |
| 3 | Terms — re-gloss them periodically; never a sentence that mixes several unfamiliar ones |

Chat is transient. The user cannot re-read a week.

## 2. Why this version is small

Two rounds of dual adversarial review returned **NOT CONVERGED four times out of four**: 4 Blocking
in round 1, 5 in round 2. The decisive finding was not a defect:

> **"The design is best-developed where the problem is smallest."**

Continuity is rank 1 and is delivered by **entries**. Everything v3 had grown — a progress chart,
health lamps, a work-flow diagram, a backlog section, a recurring-mistakes section, bundled Mermaid —
served ranks 2 and 3. Measured: v1 234 lines → v2 324 → v3 **388**; §5 reached twelve numbered units
where v1 had four. Round 1 said the page already had too many blocks; v3 **added** one and removed
none.

The user asked for simplicity twice and did not get it. **Decision 2026-08-28: cut v1 to entries,
what-needs-you, and one chart.**

### What the cut dissolves — this is the argument for it

| Round-1/2 finding | Status after the cut |
|---|---|
| **B2 (r1)** §5.1 cited a source that did not contain what was claimed | **GONE** — no progress chart |
| **B1 (r2)** the replacement derivation renders 100/100/100 and no current milestone | **GONE** — same |
| **B2 (r2)** the derivation cannot be shared with `gen-goals-page.py`, tripping §7's own redesign condition | **GONE** — same |
| **B1 (r1)** "bundled" ≠ "loadable"; no path from plugin dir to served root | **GONE** — nothing is bundled |
| **H6 (r1)** the "no fallback renderer" argument was rationalisation | **GONE** — no Mermaid |
| **H2 (r2)** "both paths run on every build" is false for Mermaid | **GONE** — same |
| Licence audit; Apache-2.0/MPL-2.0 notices (§7a v3) | **GONE** — nothing redistributed |
| Page-class change to `explainer-delivery.md` (§5.5d v3) | **GONE** — no external asset, so no exemption needed |
| **B2 (r1)** request identity on a channel with no id | **DEFERRED to v2** — §7 |
| Health lamps' missing third state; work-flow diagram; backlog counts; recurring mistakes | **DEFERRED to v2** |

**Five of the nine Blocking findings are dissolved rather than fixed.** One prerequisite remains
(§6), where v3 had five and did not order them.

## 3. Scope

### In — three things, plus links
1. **What needs you** — first, unfolded, often empty.
2. **What changed** — dated plain entries, newest first, detail folded.
3. **One chart** — days, which is also how you navigate into the entries.
4. Plain links to `/goals`, `/backlog-table`, `/latest`, `/`. No counts, no derivation — just links.
5. A folded glossary. Static text, no derivation, and it is the whole of the rank-3 fix.

### Out of v1 — with the reason, so re-adding is a decision
Progress chart · health lamps · work-flow diagram · backlog counts section · recurring mistakes ·
the request box · Mermaid · marketplace packaging.

**Why the request box is out even though the user asked for it.** It carried a Blocking: the
`POST /questions` channel records only a timestamp, a page and free text — **no id, no type, no
status** (`explainer-serve.py:671-698`, verified). "Waiting/done" cannot be derived without changing
the server. That change is worth making; it is not worth making before the page has proved useful.

## 4. The page

### 4.1 What needs you
One line per item awaiting the human, each naming the decision — or the words **"Nothing needs you."**
Derived from entries flagged `needs-you`, plus open pull requests.

⚠ **It must distinguish "nothing needs you" from "I could not tell".** If the entry file is unreadable
or `gh` fails, the block says so. `"cannot run" is a FAILURE, never a pass` (`CLAUDE.md`).

### 4.2 What changed
Newest first. Each entry is three layers:

| Layer | Visible | Language |
|---|---|---|
| Title line | yes | plain, one sentence, and whether it needs you |
| Fold 1 | no | **plain** — what happened, why it matters, what it means for you |
| Fold 2 | no | technical, **labelled as such** — commits, paths, commands |

**Fold 1 must be plain.** Summary-plain-but-detail-technical was considered and rejected: opening the
fold would hit the same wall of terms that caused the problem.

Native `<details>`/`<summary>` — no JavaScript, keyboard-accessible, works saved to disk.

### 4.3 The one chart
One bar per day for the last 14 days. **Height = commits authored that day**, on the current branch's
first-parent history — derivable, no judgement, and it under-counts uncommitted work, which the page
states. **Orange = a day carrying an entry flagged `needs-you`.**

Clicking a bar opens that day's entries below it. That is why this is the one chart kept: it is the
only one that is also navigation, and it shows the gap where you were away.

**A day with commits and no entry renders a bar with nothing under it.** That is the visible tell
that I skipped writing — an alarm, not a cure, and §5 says so plainly.

## 5. Where entries come from, and the honest weakness

The user chose: *"start with mainly (b)"* — I write them — *"and when there are important points, you
can put more details."*

**Store: `docs/dashboard-entries.md`**, in the repo, append-only. The skill appends; the script parses
and renders; regeneration is lossless. Round 1 found v2 had **no store at all** — entries lived only
as markup inside the page that regeneration overwrites, so every entry died on the next build.

Format, specified because round 2 found "fields, not a grammar" was not enough:

```
## 2026-08-28  [needs-you]
Fixed a note in the backlog that sent the next person at a method that does not work.
<!--plain-->
...plain detail...
<!--tech-->
...technical detail...
```

- One `##` block per entry. **Multiple entries on one day are separate blocks** — the date is not a key.
- A malformed block is **rendered as an error in place**, never skipped silently.
- Merge conflicts: append-only, newest at the end, so conflicts are rare and resolved by keeping both.

**THE WEAKNESS, STATED NOT SOLVED.** An entry exists only if I write it, and I would skip it exactly
when busy — which is when you most need it. No mechanism fixes that. The empty bar (§4.3) makes the
failure visible; it does not prevent it. **This is the single largest risk to the whole design, and it
sits on the rank-1 problem.**

## 6. The one prerequisite

**Folds must survive live reload.** Measured: the injected reload client (`explainer-serve.py:559-580`)
preserves scroll and refuses to reload while `#qbox` holds a draft, but does **nothing** for
`<details>`. The page rewrites itself whenever a source changes, so every fold you opened snaps shut —
on a page whose design is folding.

The fix persists open/closed state across reload, keyed by the entry's date-and-index, which
`gen-dashboard.py` assigns and which is stable because the store is append-only.
⚠ v3 claimed this "benefits every existing page". **It does not** — the server does not add ids to
pages it did not generate. Withdrawn.

**Falsifier:** open two folds, touch a source file, confirm both are still open after the reload.
It fails today.

## 7. Build

| Piece | Does |
|---|---|
| `scripts/gen-dashboard.py` | parses `docs/dashboard-entries.md`, derives the day counts and open PRs, renders the page |
| Skill `/dashboard` | writes entries in plain language, appends to the store, composes and delivers |

**Decision:** a skill *and* a script, because the plain-English writing is judgement and the counts
must not go stale. `regen-goals-page.sh:4-10` records that a purely derived page gets a script and a
hook and never a skill — that rule holds; this page is not purely derived.

⚠ The skill must be added to `PAGE_SKILLS` in `check-explainer-delivery.py`. **That check cannot
enforce its own list** — verified: it only inspects skills already on it, so an absent skill is
invisible and it exits green. This is a manual step with **no gate behind it**, stated rather than
pretended otherwise.

## 8. How we will know it works

**It fails if** the user opens the dashboard after two days away and still has to ask "what happened?"

Observable sub-criteria, because round 2 rightly called that unattributable on its own:

- the page names the last date an entry was written;
- every day with commits and no entry is visibly marked;
- "what needs you" is present, correct, or explicitly says it could not tell;
- every fold survives a reload.

| Check | Fails when |
|---|---|
| `gen-dashboard.py --self-test` | entry parsing, day bucketing, or the malformed-block path mis-derives |
| fold-survival probe | any `<details>` closes across a reload (§6) |
| affordance probe | ask-buttons are not topmost at their own centre (`explainer-delivery.md` §5b) |

**None of these measure comprehension.** Only the user can report whether it works, and the design is
revised on their word, not on a green check.

## 9. Open questions

1. Activity window — 14 days is a guess; adjust after use.
2. Whether the fold fix (§6) ships here or as its own change.

## 10. What was measured, and when

Every figure here was produced by running something on 2026-08-28. **Three times in one session a
count in this spec went stale within hours because the spec's own edits changed it** — the goals page
grew twice, the backlog page grew when I fixed it. Counts are therefore kept out of this version
wherever they are not load-bearing.

Two stale numbers found and left for their owners: `explainer-delivery.md:68` says `brief-compose.py`
has **14** self-test cases; it has **30**.

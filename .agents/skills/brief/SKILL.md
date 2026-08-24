---
name: brief
description: Build a one-page visual briefing on where a piece of work stands right now — state, evidence, and any decision waiting on the human. Use when the user asks "what is the status", "how has it been going", "catch me up", "where are we", or types /brief. Not for explaining a diff (use explain-diff) or mapping unfamiliar code (use zoom-out).
---

# Brief

Make a **one-page visual briefing** on the current state of a piece of work, for a human who has
been away and has to decide what happens next.

**Announce at start:** "Using the brief skill to build a status page."

## Why this exists (measured 2026-08-17)

The user, returning after several hours: *"I want to have some tool to follow your work as your text
proses are hard for me to follow."*

That day produced nine commits, five adversarial review halves, an architecture review, and a scope
finding that invalidated most of a sixteen-task plan — and it was delivered as a running series of
prose messages. Every message was accurate. Together they were unfollowable, and the one thing the
user actually needed — *a decision was waiting on them* — was buried in paragraph four of the fifth
message.

`/explain-diff` did not fit: it explains a **change**, and that day changed no source file. The gap
is a briefing on **state**, not on a diff.

## The rule that matters most

**Every number, name and status on the page comes from a command run in THIS invocation.**

Not from the conversation, not from a context summary, not from memory. `docs/dev-process.md`
*Session Resume* exists because a compacted summary goes stale; this project has also measured the
cost of a table written from recall (`docs/backlog.md`, and the memory
`never-write-a-cost-table-from-memory`: five rows, four unsupported).

If a figure cannot be derived by a command, either derive it or leave it out. **A briefing that is
confidently wrong is worse than no briefing**, because the whole point is that the reader is not
going to check.

## Step 1 — establish ground truth

Run these; do not skip any. Report the ones that returned nothing.

```bash
git log --oneline -15
git status --short
git branch --show-current
git rev-list --count $(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo master)..HEAD
git diff --stat <last-session-boundary>..HEAD     # pick the boundary from git log dates
```

Then read, in this order — they are the three layers `dev-process.md` requires to agree:

1. `docs/roadmap-to-launch.md` — the compaction-proof layer
2. the task list (`TaskList`) — the current milestone
3. `docs/backlog.md` — anything filed

And the artifacts of the work itself: `docs/reviews/` for the subject, any spec or plan under
`docs/superpowers/`, and `git log` messages, which in this repo carry the reasoning.

**Run the repo's own ratchets** and report exit codes, not their prose output:
`check-docs`, `check-roadmap-consistency`, `check-test-counts`, `check-producer-enumeration`.

**Then read the RUNNING SYSTEM, and compare it to what the roadmap claims.** This is the third
layer, and every check above is blind to it — the ratchets compare documents to documents, and
`check-roadmap-consistency` compares the roadmap to *itself*.

```bash
flyctl releases --app youtube-playlist-summaries | head -3   # what is actually live
grep -n 'Deployed: release' docs/roadmap-to-launch.md        # what the roadmap says is live
```

**A mismatch is the finding.** Measured 2026-08-18: the roadmap said `v6` while `master` carried a
merged money-path fix — *merged ≠ deployed* — and the precedent that makes this non-negotiable is
production once running **eight days behind on a migration** while every file on disk looked correct.

> ⚠ **Why this is a skill step and NOT a gate.** It was nearly built as
> `check-deploy-freshness.py`, which would have needed the deploy SHA hand-recorded in the roadmap
> (a manual step — the exact class that rots) and would have fired on every docs-only commit (noise,
> which gets gates disabled). **The capability was never missing; only the trigger was.** Detection
> is one command, and the moment it matters is the moment someone is about to trust the roadmap —
> which is precisely when a briefing is being written. Before adding a script, ask whether the check
> already exists and merely lacks a moment to run.
>
> Bound honestly: this catches **version** drift (live release vs the claim), not **commit** drift
> (a release built from a stale tree). Version drift is what has actually happened, twice.

**Reconcile the three layers against git.** Where they disagree, the disagreement IS a finding — say
so on the page. Checkboxes are a claim; git is the truth.

## Step 2 — find the shape

Before designing anything, answer these. They decide what the page contains:

- **Is a decision waiting on the human?** If yes it is the subject of the page and everything else
  is evidence for it. If no, say so explicitly — do not manufacture one.
- **What is blocked, and on what?** Distinguish *blocked on a person*, *blocked on a machine*, and
  *not started*.
- **Does the work have a measurable shape?** Rounds of review, defect counts by class, tests over
  time, tasks done vs. remaining, spend. If a trend exists, it is a chart — in prose it is invisible.
- **What was verified vs. inferred?** Mark anything you did not run a command for.

## Step 3 — build the page

**Load the `artifact-design` skill first** — it governs the visual craft. Then write the content as
a fragment (a `<title>`, one `<style>…</style>`, then body markup — no `<html>`/`<head>`/`<body>`).

**For everything after that, follow [`../shared/explainer-delivery.md`](../shared/explainer-delivery.md)** —
composing with `brief-compose.py`, `explainer-serve.py`, why the page is served rather than published
as an Artifact (the CSP blocks the Ask channel), arming the Monitor push loop, verifying the tray,
and delivering `/latest`. It is the ONE description of that loop, shared with `explain-diff` and
`explain-findings`; extracted 2026-08-24 so a third page-producing skill did not become a third copy.

Sections, in this order:

1. **Masthead** — what work, one sentence on where it stands, and a visible stamp if a decision is
   pending. A reader who stops here should still know whether they are needed.
2. **Headline stats** — three to five numbers that characterise the situation. Include at least one
   that is uncomfortable if one exists; a briefing that only reports progress is marketing.
3. **The shape** — the chart from Step 2. One good chart beats three weak ones. Build it from
   HTML/CSS, never ASCII, and give every bar a real `aria-label`.
4. **What is blocked** — a table, one row per item: what, blocked on whom or what, since when.
5. **The decision** — the recommendation, the *strongest* argument against it, and the answer to
   that argument. Both sides get real weight; the reader is deciding, not being sold.
6. **Ground-truth footer** — commit sha, branch, gate states, ratchet results, and the timestamp.
   This is what lets the reader trust the rest.

**Design constraints** (the rest comes from `artifact-design`):

- Colour carries meaning and means the same thing everywhere: one hue for problems, one for
  verified/measured, one for structural facts. Not decoration.
- `font-variant-numeric: tabular-nums` wherever digits align.
- Both themes, per `artifact-design`. Wide content scrolls in its own container.
- Favicon: 🧭.

## Step 4 — say what the page cannot

In your reply, not on the page:

- anything you could not verify, and why
- any layer that disagreed with git
- what you would look at next

Then ask the decision question directly, in one sentence.

## Scope

- **A diff, PR or branch** → `explain-diff`. It has a diff; this does not.
- **Unfamiliar code** → `zoom-out`. That maps modules and callers.
- **This** → the state of a body of work and what it needs from the human.

## Answering the questions that come back

Answer **in the page**, not only in chat — see `../shared/explainer-delivery.md` §6. A briefing whose
answers live in the transcript has the problem it was built to solve.

## Known gaps in this draft

Written 2026-08-17, deliberately shipped before it is good. Refinement is backlog **#50**. Known
weak points, recorded so they are not rediscovered:

- ~~No self-test~~ — **closed the same day**: `scripts/brief-compose.py --self-test`, 14 cases,
  including that it refuses to write when no tray can be lifted.
- **The ground-truth command list is hardcoded** and will drift as the repo changes. Per
  `hardcode-only-what-fails-loudly`: a missing file fails loudly, a *renamed* one fails silently by
  returning nothing. Report empty results rather than skipping them.
- **Staleness is per-figure, not per-page** — measured on the very first invocation, which quoted a
  plan at 3,906 lines that had become 3,905 an hour earlier. A ratchet exit code decays in minutes;
  a review count decays in days. The footer timestamp covers the page as a whole and says nothing
  about which numbers rot fastest. **Consider marking volatile figures inline.**
- **Unmeasured on a project with no decision pending** — the shape it produces then is untested, and
  the risk is that it manufactures a decision to fill the slot.
- ~~**The composed page is never opened by its author.**~~ — **partly closed 2026-08-18.** The page
  was driven in a real browser to verify live reload (below): loaded, changed on disk, observed to
  reload itself, and the no-reload-while-typing guard confirmed with a 53-character draft in the box.
  ⚠ **Still not driven: the `ask` button itself.** The tray's markup is asserted present by
  `brief-compose.py`, and the channel is exercised end-to-end by the reader — but the author has
  never clicked Send. That is the remaining half of the "markup is present" vs "the button works" gap.

- **⭐ The page now RELOADS ITSELF when an answer is posted** (2026-08-18, backlog #50a). No manual
  refresh: `explainer-serve.py` serves `GET /_rev?p=<page>` and **injects** a small poller into every
  HTML it sends. So an answer added to a section appears where the question was asked.
  **Three things worth knowing before touching it:**
  - It is **injected by the server, not written into the page**. The tray is lifted verbatim
    page-to-page by `brief-compose.py`; putting the poller there would reach only pages generated
    afterwards and would repeat the hand-copied-code failure this file already warns about. Nothing
    in `brief-compose.py` changed.
  - `file://` gets nothing, deliberately. The artifact stays self-contained and works in five years;
    live reload is a property of being **served**.
  - It **will not reload while `#qbox` holds a draft or has focus**, and it preserves scroll across
    the reload. A reader mid-question is the one person a reload would hurt most.

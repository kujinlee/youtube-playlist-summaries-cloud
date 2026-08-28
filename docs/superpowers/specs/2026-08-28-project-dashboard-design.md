# Project Dashboard — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** **v1 DRAFT — agreed in conversation 2026-08-28, not yet reviewed.** Written from the
brainstorming session of the same day. Needs dual adversarial review before it becomes a plan.

---

## 1. Why this exists

The user said it directly:

> "I am having hard time to understand your output on chat dialogs. with abriviations, jargons and
> condensed explanations etc. I cannot monitor closely what you are doing and I lost in flooding
> text."

This is a stated, repeated problem, not an inferred one. The memory `output-style-plain-default` has
carried a version of it since 2026-08-12 and it recurred anyway. Writing more carefully in chat helps
but does not fix it, because chat is **transient** — the user cannot go back and re-read a week.

Asked to rank the failure, the user answered:

| Rank | Failure | Their words |
|---|---|---|
| 1 | **Continuity** | Cannot hold the thread across a day or a week; does not know what changed while away |
| 2 | **Volume, no signal** | Too much text, no marker for what matters |
| 3 | **Terms** | "if you occasionally remind me the definition of the acronyms, it will be helpful. Just don't make the prose a mix of unfamiliar terms" |

And: *"Try to be plain and straightforward. No need to use your literary skills."*

**The dashboard targets #1 and #2. #3 is fixed by a glossary on the page plus a change in how I
write, which is independent of this spec.**

## 2. What already exists — this is an addition, not a new system

Measured 2026-08-28. **Nothing here is being rebuilt.**

| Thing | Where | State |
|---|---|---|
| Local web server | `scripts/explainer-serve.py`, `127.0.0.1:7391` | running; serves `~/explainers` only |
| Page index | `GET /` | newest first |
| Newest page | `GET /latest` | redirect |
| Goals view | `GET /goals`, `scripts/gen-goals-page.py` | derived from 5 sources, hook-regenerated |
| Backlog view | `GET /backlog-table`, `scripts/gen-backlog-page.py` | derived, hook-regenerated |
| **Standing pages** | undated filename → extensionless URL | **exists**; excluded from `/latest`; live-reloads an open tab |
| Page → session channel | `POST /questions` → `~/explainers/questions.md` | **the only one**; watched by a `Monitor` |
| Tray lifting | `scripts/brief-compose.py` | lifts the ask-tray verbatim; 14 self-test cases |

**The dashboard is a new standing page** on this server. It needs no new process, no new port, and
no new delivery mechanism.

## 3. Scope

### In

1. One page at a fixed address: `http://127.0.0.1:7391/dashboard`.
2. Overall picture visible; **all detail folded** behind title lines.
3. Five graphics (§5).
4. A dated list of plain, one-sentence entries — "what changed since you last looked".
5. A **backlog section** (§5.6) — counts visible, dependency diagram inline, full table one click away.
6. A request box that can ask for `explain-diff`, `explain-findings`, `explain-topic`, `brief`.
7. A visible list of those requests and whether they are done.
8. A glossary, folded.
9. Links to `/goals`, `/backlog-table`, `/latest`, `/`.

### Out — deliberately, because the user asked for simplicity

- A "mark as read" memory of what the user has already seen.
- A recurring-mistakes section. *(Wanted — the user said "common mistakes etc." — but deferred to v2
  so v1 ships.)*
- Any chart beyond the four in §5.
- Converting `gen-backlog-page.py`'s existing hand-drawn SVG diagram to Mermaid (§5.5 — Mermaid **is**
  in scope for the dashboard; the backlog page's working renderer is not touched in this slice).
- Marketplace packaging itself (§7a — designing so it is *possible* is in scope; doing it is not).

## 4. The rule the whole page obeys

**Every piece of detail is folded. Nothing is deleted.**

The first design removed detail to fight volume. The user corrected it:

> "the details can be in a collapsed section with title line. I can open it to get details when I
> need them. so idea is that show me overall picture with details embedded"

So each entry has **three layers**:

| Layer | Visible by default | Language | Contains |
|---|---|---|---|
| Title line | yes | plain | one sentence; and whether it needs them |
| Fold 1 | no | **plain** | what happened, why it matters, what it means for them |
| Fold 2 | no | technical | commit SHAs, file paths, commands, exact numbers |

**Fold 1 must be plain.** The tempting shortcut — plain summary, technical detail underneath — was
considered and rejected in conversation: the user would open the fold and hit the same wall of terms
that caused the problem. Fold 2 is where the raw material goes, and it is **labelled as such**, so
opening it is a choice.

Built with the browser's native `<details>`/`<summary>`. No JavaScript, works when saved to disk,
keyboard-accessible, survives the five-year test in `explainer-delivery.md` §2.

## 5. The graphics

The user asked for these explicitly: *"graphics and charts are helpful… any graphics friendlier to
human comprehension are welcomed."*

### 5.1 Progress — a milestone track
Horizontal blocks, one per milestone, filled when done, hollow when not, current one marked.
Answers *how far along is the whole thing.* Derived from the `### M<n>` headings and their ✅ / ◀ / ⛔
markers in `docs/roadmap-to-launch.md` — the same source `gen-goals-page.py` already reads.

### 5.2 Activity — the last 14 days
One bar per day, **height = number of commits authored that day** (chosen because it is derivable
with no judgement and cannot drift; it under-counts uncommitted work, which is stated on the page
rather than hidden). **Orange = a day carrying at least one entry marked *needs you*** — that mark is
set by me when writing the entry, so orange is a written claim, not a derived one.

**This is also the navigation.** Clicking a bar opens that day's entries below it. That is what makes
it earn its space rather than decorate: the user looks, sees the gap where they were away, and opens
it.

Derived from `git log` dates plus the entry list (§6).

### 5.3 Health — the check lamps
One small block per automated check, green or red, plus one amber lamp for "waiting on you". This
exact device was built and read successfully on the 2026-08-28 briefing page; it is being reused, not
invented. Derived by running the checks.

### 5.4 How work moves
A left-to-right diagram: `idea → spec → plan → build → review → pull request → merged`, with a marker
on where current work sits. Answers *what are you doing and where is this going* without requiring
the user to know the process.

### 5.5 Mermaid — INCLUDED, bundled with the plugin, and no fallback renderer

⟳ **This section REVERSES an earlier decision in this same spec. The reversal is recorded rather
than edited away, because the first version was wrong for an instructive reason.**

**What the first version said, and why it was wrong.** It refused Mermaid on the grounds that `mmdc`
is not installed and bundling would cost "roughly a megabyte". Both facts were true and the
conclusion did not follow. The check performed was *"is a Mermaid renderer installed?"* — the
question that mattered was *"can this project ship a Mermaid renderer to its users?"* The user then
pointed out that `docs/backlog.md`'s page **already uses Mermaid**, which the search had missed
because it emits Mermaid *source* rather than rendering it. Same failure shape as the memory
`it-already-exists-under-a-name-i-didnt-search`.

**Measured 2026-08-28, correcting the recalled figure:**

| Fact | Value |
|---|---|
| `mermaid` browser bundle, v11.17.2 | **3.41 MB** raw · 0.93 MB gzipped |
| The "~1 MB" in `gen-backlog-page.py:419` | the **gzipped** number — 3.4× under the file that would actually ship |
| License | **MIT** — redistribution permitted with attribution |
| Comparable installed plugins | `superpowers` 4.0 MB · `remember` 10 MB |
| Current page sizes | brief 67 KB · goals 71 KB · backlog-table 477 KB |

**Decision:** Mermaid is bundled with the distributed plugin and served from `127.0.0.1`.
*(Flagged for ADR triage — bundling a 3.4 MB third-party dependency into a published plugin is an
architectural commitment, not an implementation detail.)*

The user's stated intent is to publish this dashboard and its scripts to a marketplace, and asked
what happens to someone who cannot install Mermaid. **That case is designed out rather than handled:**
at 3.4 MB against a 4–10 MB plugin norm, and under a permissive licence, Mermaid ships *inside* the
plugin. No user installs anything, so no user lacks it, so **there is no fallback renderer** — nothing
to build, nothing to test, nothing to rot.

**Rejected: a hand-drawn SVG fallback beside Mermaid.** It was considered seriously — the backlog
page proves the technique works. It is rejected because **a fallback nobody exercises is not a
fallback**, and this project has measured that twice already: the unverified Mermaid source in
`gen-backlog-page.py:477`, and the 29-of-33 unreachable ask-buttons of PR #163. Development would
happen with Mermaid present, the other path would never be seen, and it would become fiction while
still being described as a safety net. Two renderers for one diagram is also
`two-mechanisms-for-one-concern`, which this project has a script to hunt.

**What IS still required, and it is not a fallback.** If `mermaid.min.js` is absent or damaged, the
page must say so **in plain words, in place of the diagram**. A blank box is indistinguishable from a
diagram containing nothing — the `"cannot run" is a FAILURE, never a pass` rule from `CLAUDE.md`
applies directly.

**A side-effect worth having: it fixes a live defect.** `gen-backlog-page.py:477` emits Mermaid
source and states outright that *"its rendering is unverified"* — text handed to the user that
nothing has ever drawn. Once a page renders the same string it offers for export, the export is
correct **because** it is rendered.

⚠ **SCOPE BOUND, stated so it is not silently crossed.** This holds because a dashboard is a **live
view**, regenerated in place like `/goals` and `/backlog-table` — nobody archives it, so
`explainer-delivery.md` §2's "opens on its own in five years" requirement is not in play. **Dated
explainer pages ARE archival and that requirement still binds them.** Putting Mermaid on a dated page
re-opens this question, because a saved file has no server to load the library from. Out of scope
here; must not be assumed settled there.

**Not converting the backlog page in this slice.** Its hand-drawn SVG works. Swapping a working
renderer while building a new page means debugging two things at once. If Mermaid proves out on the
dashboard, converting `gen-backlog-page.py` is an easy follow-up and its own change.

### 5.6 Backlog — a section, not just a link
Added 2026-08-28 at the user's request ("I forgot to include backlogs page. add it too").

Three levels, following §4's folding rule:

| Level | Shows |
|---|---|
| visible | counts — total, closed, open, and how many are on the money path |
| fold 1 | the **dependency diagram** (Mermaid, §5.5), plus the few items that block others, in plain words |
| link | `/backlog-table` for the full 66-row table, which already exists and is not duplicated here |

**Counts are derived by `gen-backlog-page.py`'s existing parser, not re-counted.** A second counter
over the same file is `two-mechanisms-for-one-concern`, and this project has already measured the
cost of a hand-written count drifting (§ the 110-vs-117 correction in `docs/backlog.md` row 65,
fixed the same day this spec was written).

## 6. Where the entries come from

The user chose, in their words: *"start with mainly (b) and when there are important points, you can
put more details with (c)"* —

- **(b) I write them.** One plain entry per work session. This is the default.
- **(c) Layered detail on the ones that matter.** Not on every entry.

**The known weakness, stated rather than hidden:** an entry only exists if I write it. When I am busy
is exactly when I would skip it, and that is when the user most needs it. Two mitigations, both cheap:

1. The **facts** around the entries (§7) are script-derived, so the page is never blank and never
   silently stale even on a day I write nothing.
2. The activity chart is derived from `git log`, so **a day with commits but no written entry shows a
   bar with nothing under it** — the gap is visible instead of invisible. A missing entry must look
   missing.

## 7. Build — two pieces, split on judgement

| Piece | Does | Why it is separate |
|---|---|---|
| `scripts/gen-dashboard.py` | gathers facts: branch, deployed release, check results, milestone state, git activity, open requests. Renders the frame and the graphics. | machines do not forget; these must never be stale |
| Skill `/dashboard` | writes the plain paragraph and the entry text; composes and delivers | needs judgement; cannot be automated |

**Why a skill at all, when `/goals` and `/backlog-table` have none.** `.claude/hooks/regen-goals-page.sh`
records the rule: a purely derived page gets a script and a hook, never a skill, because the skill
would be a wrapper whose whole body is *"run the script"*. That rule holds and is not being broken —
the dashboard is **not** purely derived. The plain-English writing is the entire point of it, and
that is judgement. So it gets both.

**Consequence, which must not be forgotten:** a new page-producing skill **must** be added to
`PAGE_SKILLS` in `scripts/check-explainer-delivery.py` (currently
`["explain-diff", "brief", "explain-findings", "explain-topic"]`). That check exists so a page skill
cannot restate the delivery loop instead of citing it. **An unlisted page skill escapes the check
entirely** — that is written in `explainer-delivery.md` and is a live trap here.

## 7a. Distribution — this is built to be published

Stated by the user 2026-08-28: *"eventually I want to publish this dashboard and related skills and
scripts to marketplace."* That is a **constraint on the design, not a later packaging step**, and it
is what settled §5.5.

| Consequence | Requirement |
|---|---|
| Users will not be this project | nothing may assume `~/code/agentic-ai-docs/...`, this repo's file names, or this machine's Supabase. Every source path is a parameter with a documented default |
| Users will not install extras | Mermaid ships **inside** the plugin (§5.5). Python 3 and a browser are the only assumptions |
| Users will not read this spec | failure messages must be self-explaining. "cannot run" states what is missing and what to do |
| The plugin has a size budget | 3.4 MB of Mermaid against a 4–10 MB norm for installed plugins — acceptable, and recorded so a later addition is a decision rather than a drift |
| MIT attribution | Mermaid's licence text ships with the bundled file |

**Sequencing, so publication does not become a rewrite:** the scripts take their inputs as arguments
from the start. This project is the first user, not the only shape. Actual marketplace packaging is
**out of scope for v1** — but designing so it is possible is not.

⚠ **`docs/backlog.md` #40 already asks to "package explain-diff + explainer-serve as a Claude Code
plugin" (task #75, open).** This dashboard rides the same packaging work. They must be planned
together or the plugin gets built twice.

## 8. The request box, and its honest limit

Four buttons and a text box. Pressing one sends the text through the **existing** `POST /questions`
channel — the same one the ask-tray already uses.

**A button cannot run anything.** It appends a request to `~/explainers/questions.md`. If a session is
live with the `Monitor` armed, I see it within seconds. If nothing is running, it waits until I next
read the file.

**Therefore the page shows every request with its state — `waiting` or `done`.** This is not polish.
A button that looks like it worked while nothing happened is the exact failure class this project
keeps measuring (`a-checklist-item-can-be-an-unfalsifiable-guard`, and the 29-of-33 unreachable
buttons of PR #163). The state list is what makes the button honest.

Request state is derived by comparing `questions.md` entries against pages that exist in
`~/explainers`.

## 9. How we will know it works

**It fails if** the user opens the dashboard after two days away and still has to ask "what happened?"
in chat. That is the observation that falsifies this design, and it is a real one — it can happen
with every gate green.

Mechanical checks, none of which prove the above:

| Check | Fails when |
|---|---|
| `gen-dashboard.py --self-test` | pure functions mis-derive milestone state, activity buckets, or request state |
| `check-explainer-delivery.py` | `dashboard` is absent from `PAGE_SKILLS`, or the skill restates the delivery loop |
| a fold assertion in the compose step | any `<details>` block is missing its `<summary>`, i.e. a section that cannot be opened |
| affordance probe (`explainer-delivery.md` §5b) | ask-buttons are not the topmost element at their own centre |

**⚠ Stated plainly: none of these measure comprehension.** They measure that the page is built
correctly. Only the user can report whether it works, and the design should be revised on their word
rather than on a green check.

## 10. Risks

| Risk | Mitigation |
|---|---|
| I stop writing entries and the page rots | activity chart shows bars with no entries — the gap is visible (§6) |
| The page becomes another wall of text | everything folded by default; only title lines visible |
| Fold 1 drifts back into jargon | it is the reviewed artifact; the user reports it and it is treated as a defect, not a style preference |
| The page is built and never opened by its author | `explainer-delivery.md` §5b applies in full — drive it in a browser, and refuse to conclude from a hidden tab |
| Scope creep back to v2 items | §3 "Out" is binding for v1 |

## 11. Open questions

None blocking. Two to settle during implementation:

1. How many days the activity chart spans — 14 is the starting guess, adjustable once real data is on it.
2. Whether the glossary is hand-written or derived from a term list. Starting hand-written; it is
   short, and deriving it risks the `hardcode-only-what-fails-loudly` failure where a vocabulary
   silently stops matching.

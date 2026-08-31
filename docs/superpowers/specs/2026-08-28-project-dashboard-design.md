# Project Dashboard — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** **v5 — round 3 folded in, and the entry is now GATED rather than voluntary.**
Three dual-adversarial rounds, six reviewer verdicts, all NOT CONVERGED. Reviews retained at
`docs/reviews/spec-project-dashboard-r{1,2,3}-{codex,claude}.md`.
**User decision 2026-08-28: option (a) — add the forcing function.**

---

## 1. Why this exists

> "I am having hard time to understand your output on chat dialogs… I cannot monitor closely what you
> are doing and I lost in flooding text."

| Rank | Problem |
|---|---|
| **1** | **Continuity** — cannot hold the thread across a day or a week |
| 2 | Volume with no signal |
| 3 | Terms — re-gloss periodically; never a sentence mixing several unfamiliar ones |

## 2. What the page is, and what is reliable about it

Round 3 corrected a premise this spec had wrong for four versions. **Entries are not the only
mechanism serving continuity.** The page has three sources and two need no discipline from me:

| Block | Source | Reliable without me remembering? |
|---|---|---|
| §5 the chart | `git log --first-parent` | **Yes** |
| §4 open pull requests | `gh pr list` | **Yes** |
| §4 needs-you, §6 what changed | written by me | **No — now gated, §7** |

**So the page degrades rather than fails.** On a day I write nothing it still answers *when work
happened and what is open* — more than the transcript gives. That is the skeleton of continuity, and
it is free.

**But a page that is *sometimes* complete is worse than one that is never complete, because the reader
cannot tell which day they are looking at.** That is why §7 exists.

### Why this version is smaller than v3
v1 234 lines → v2 324 → v3 388 → v4 208 (all four verified against git 2026-08-28). The cut removed
the progress chart and Mermaid, dissolving five Blocking findings rather than fixing them. **Round 3
verified each dissolution individually.**
⟳ v4 said *"§5 reached twelve numbered units where v1 had four"* — **v1 had five** (§5.1–§5.5); four
was a count of *graphics*. Corrected.

## 3. Scope

**In:** what-needs-you · what-changed · one chart · the entry gate (§7) · plain links · a folded glossary.

**Out of v1:** progress chart · health lamps · work-flow diagram · backlog counts · recurring
mistakes · the request box · Mermaid · marketplace packaging.

**The request box stays out** even though it was asked for: `POST /questions` records only a
timestamp, a page and free text — no id, no type, no status (`scripts/explainer-serve.py:671-698`,
verified) — so "waiting/done" cannot be derived without changing the server.

## 4. What needs you — first, unfolded

One line per item, each naming the decision — or **"Nothing needs you."**
Sources: entries flagged `needs-you` that are **not yet resolved** (§6.2), plus `gh pr list`.

⚠ **It must distinguish "nothing needs you" from "I could not tell".** If the entry file is
unreadable or `gh` fails, the block says which. `"cannot run" is a FAILURE, never a pass`.

## 5. The one chart

One bar per day. **Height = commits on `git log --first-parent HEAD`** for that day — named
explicitly because "commits" is ambiguous once branches and squash-merges exist. It under-counts
uncommitted work, and the page says so.

**Orange = that day has an unresolved `needs-you` entry.**

⟳ **The window is a parameter, default 14 days, with a control to widen it.** v3 established this
after round 1 showed a fixed fortnight is shorter than the absences this page exists for; **v4 dropped
it silently and round 3 caught the regression.** Restored, and recorded here so it cannot be lost
again quietly.

**Clicking a bar scrolls to that day's entries in §6. The chart never renders entry text** — see §6.1.

## 6. What changed

### 6.1 Rendered exactly once
Round 3 found §4.2 and §4.3 of v4 both claiming to present the entries with neither referencing the
other. **The entry list in §6 is the only place entry text is rendered.** The chart is navigation
into it, nothing more.

- **The list is not windowed.** Every entry in the store renders, newest first.
- **The chart is windowed.** An entry older than the window is reachable by scrolling, not by a bar.
- **An entry on a day with zero commits** renders in the list and gets a **zero-height marked bar**,
  so "I wrote about a day with no commits" is visible rather than invisible.

### 6.2 The store and its grammar

**`docs/dashboard-entries.md`**, in the repo, append-only.
**The renderer reads the working tree**, not a committed ref — the dashboard is a local live view and
must show work in progress. The chart reads `HEAD`. Both are stated because round 3 found v4 silent
on which ref, in a repo where docs land through batched PRs behind a human merge gate.

```
## 2026-08-28 [needs-you]
Fixed a note in the backlog that sent the next person at a method that does not work.
<!--tech-->
PR #168, squash 71c7e40. ALTER DEFAULT PRIVILEGES cannot remove PUBLIC's built-in EXECUTE.
```

A grammar, not an example — round 3 found v4's version was still only an example:

| Rule | Definition |
|---|---|
| Block start | `## ` at **column 0**, followed by `YYYY-MM-DD` |
| Date | ISO-8601 **and a real calendar date**; `2026-02-30` is malformed |
| Flags | zero or more of `[needs-you]`, `[resolved: YYYY-MM-DD/N]`, space-separated, after the date |
| Unknown flag | **malformed** — never silently ignored, because a typo'd `[needs-you]` would silently drop an item off §4 |
| Entry id | `YYYY-MM-DD/N`, N = 1-based ordinal **within that date, in file order** |
| Title | the first non-blank line after the header |
| Plain detail | everything up to `<!--tech-->` or the next column-0 `## ` |
| Technical detail | after a line that is **exactly** `<!--tech-->`; optional |
| `##` inside detail | only column-0 `## ` splits blocks; indent or fence it to include one literally |
| Marker in prose | only a line that is exactly `<!--tech-->` is a marker; inline occurrences are text |
| Ordering | rendered **newest-first throughout** — newest date first, and within a date the last entry written renders first. ⟳ **CHANGED 2026-08-31, backlog #75.** This row previously said *"ties keep file order"*, which put a day's OLDEST entry on top. Measured that day: seven entries dated 2026-08-30 formed one tie group, so the newest work sat seven cards below the fold and a **current** page was reported as stale. The rule was harmless at one or two entries a day and defeats the anchor (`status-visibility`) at seven. ⚠ **Id assignment is unchanged** and must stay so — `N` is still file order within the date (row above), because ids are positional and a standing `[resolved: <id>]` points at one; letting render order reach id assignment would silently rebind every resolution |
| Absent or empty file | **not an error** — the page renders "no entries yet" and says where the file would live |
| Malformed block | rendered **in place**, raw, under a visible "could not parse this entry" label, and the page still renders everything else |

**Resolution — because round 3 found §4 could only ever grow.** A `needs-you` item is cleared by a
later entry carrying `[resolved: <id>]`. Append-only is preserved: nothing is edited, the clearing
fact is appended. A `[resolved:]` naming an unknown id is **malformed**.

**Falsifier:** an entry with a bad date, an unknown flag, and a `[resolved:]` pointing at nothing must
each render as an error while the surrounding entries still render.

## 7. The gate — why an entry will actually exist

**This is the change that option (a) buys, and it is the answer to the design's largest risk.**

Through v4 the rank-1 mechanism was voluntary: an entry existed only if I remembered, and I would
skip it exactly when busy. `docs/dev-process.md` gives the remedy: *"Before adding a rule here, ask
whether it can be a script."*

**Bind the entry to an artifact that already cannot be skipped.** Every unit of work in this repo
produces exactly one: a **pull request**, gated on a human merge (`docs/dev-process.md` Phase 5,
*"Branch + PR, always"*).

1. **The entry rides the branch.** It is written to `docs/dashboard-entries.md` in the same branch as
   the work, so it lands when the work lands.
2. **`scripts/check-dashboard-entry.py` refuses a branch that changes tracked files and adds no entry
   block.** With `--self-test` covering the near-misses, like the ratchets already in
   `scripts/check-schema-gates.sh`.
3. **It repairs the alarm as a side effect.** Entry and commits arrive in the same squash, so
   "a bar with no entry" becomes a precise statement — *this work shipped without an entry* — rather
   than an artifact of merge timing, which round 3 showed was the case in v4.

**Decision:** the entry gate ships **with** v1, not after it. A page that promises continuity, rests
it on a voluntary act, and carries an alarm that does not fire is the one version that should not
exist.

**The cost, stated:** an entry written to satisfy a gate can become a compliance artifact rather than
a briefing. That is real. It is smaller than no entry at all, and the user is the only detector of
quality either way (§9).

**Exemptions must be explicit and visible:** a branch may declare `NO-ENTRY: <reason>` in its body,
which the check accepts and the dashboard **displays**, so a skipped entry is a recorded decision
rather than a silence.

## 8. Build

| Piece | Does |
|---|---|
| `scripts/gen-dashboard.py` | parses the store, derives day counts and open PRs, renders the page |
| `scripts/check-dashboard-entry.py` | the gate (§7), with `--self-test` |
| Skill `/dashboard` | writes entries in plain language, appends, composes, delivers |

A skill **and** scripts: the plain-English writing is judgement; the counts must not go stale.
`.claude/hooks/regen-goals-page.sh:4-10` records that a purely derived page gets a script and a hook
and never a skill — that holds, and this page is not purely derived.

⚠ The skill must be added to `PAGE_SKILLS` in `scripts/check-explainer-delivery.py`. **That check
cannot enforce its own list** — verified: it inspects only skills already on it, so an absent skill is
invisible and it exits green. A manual step with **no gate behind it**, stated rather than pretended.

## 9. How we will know it works

**It fails if** the user opens the dashboard after two days away and still has to ask "what happened?"

Observable, because round 2 rightly called that unattributable alone:

- the page names the last date an entry was written;
- every day with commits and no entry is visibly marked;
- "what needs you" is present, correct, or explicitly says it could not tell;
- a resolved `needs-you` item disappears from §4 and stays in §6;
- every fold survives a reload.

| Check | Fails when |
|---|---|
| `gen-dashboard.py --self-test` | any §6.2 grammar rule mis-parses, or a malformed block is skipped instead of shown |
| `check-dashboard-entry.py --self-test` | a branch changing tracked files with no entry and no `NO-ENTRY:` passes |
| fold-survival probe | any `<details>` closes across a reload (§10) |
| affordance probe | ask-buttons are not topmost at their own centre (`.agents/skills/shared/explainer-delivery.md` §5b) |

**None of these measure comprehension.** Only the user can report whether it works.

## 10. Prerequisites — plural, because "one" was wrong

v4 claimed one. Round 3 counted more. Honestly:

1. **Folds survive live reload.** The injected client (`scripts/explainer-serve.py:559-580`) preserves
   scroll and guards `#qbox`, but does **nothing** for `<details>`. ⟳ v4's claim that fixing it
   "benefits every existing page" is **withdrawn** — the server does not add ids to pages it did not
   generate.
2. **The store must be created** — `docs/dashboard-entries.md` does not exist yet.
3. **`/dashboard` added to `PAGE_SKILLS`** — manual, ungated (§8).
4. **`gh` failure behaviour defined** for the open-PR half of §4.

## 11. Open questions

1. Default window — 14 days is a guess (§5); adjust after use.
2. Whether the fold fix (§10.1) ships here or separately.

## 12. Stale numbers found and left for their owners

`brief-compose.py --self-test` returns **30/30** (run 2026-08-28). **Two** documents still say 14:
`.agents/skills/shared/explainer-delivery.md:68` and `.agents/skills/brief/SKILL.md:162`.
⟳ v4 said "two stale numbers" and named one location; both are named now, with full paths — round 2
and round 3 both flagged this document's habit of bare citations.

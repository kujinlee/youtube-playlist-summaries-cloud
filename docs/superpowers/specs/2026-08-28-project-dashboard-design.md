# Project Dashboard — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** **v3 — round 1 of dual adversarial review folded in. NOT yet re-reviewed.**
v1 written 2026-08-28 from the brainstorming session. v2 reversed the Mermaid decision. **v3 answers
round 1: Codex 2 Blocking / 3 High / 3 Medium / 3 Low, Claude 2 Blocking / 9 High / 7 Medium / 4 Low,
both NOT CONVERGED.** Round 2 required before this becomes a plan.

⚠ **The user approved v2 from a spoken summary without reading it** — they were away from their desk.
That is not a human read of this document, and the approval does not transfer to v3.

---

## 0. What round 1 found, and what changed

Reviews: `docs/reviews/spec-project-dashboard-r1-codex.md`, `docs/reviews/spec-project-dashboard-r1-claude.md`.
The two halves overlapped on only three findings out of ~24 — the case for running both.

| # | Finding | v3 |
|---|---|---|
| **B1** (Claude) | Entries had **nowhere to live**; the page holding them is regenerated in place, destroying them | §6a — a durable append-only store |
| **B2** (Claude) | §5.1 cited the wrong file, wrong heading level, and a marker that appears **zero** times | §5.1 rewritten on a verified source |
| **B1** (Codex) | "Bundled" was asserted to mean "loadable"; no path from plugin dir to served root | §5.5b — an install step with a startup assertion |
| **B2** (Codex) | Request state derived by matching text on a stream with **no identity** | §8 — explicit ids + resolution records |
| **H6** (Claude) | "No fallback renderer" was **rationalisation**, and its retained requirement is the same untested path one band down | §5.5c — an *exercised* fallback |
| H1/H1 (both) | §9's flagship check **cannot fail** on an absent skill | §9 rewritten; the check is stated as what it is |
| **H3** (Claude) | Live reload **discards every open fold**, and folding is the whole design | §4a — fold state must survive reload |
| **H7** (Claude) | Health lamps had two states; **"could not run"** was not one | §5.3 — three states |
| **H8** (Claude) | Nothing surfaced *"what needs you"* — a third of the registered goal | §5.0 — it is now the first thing on the page |
| **H4** (Claude) | 14 days is shorter than the absences the page exists for | §5.2 — window is a parameter, with a way to look further back |
| **H9** (Claude) | Deferring recurring-mistakes was the wrong cut | §5.7 — reinstated |
| H2/H3 (Codex), M5 | A shared rule was **waived from inside this spec** | §5.5d — the change moves to the shared doc |
| M1 (Claude) | Licence claim described the npm package, not the shipped artifact | §7a — corrected |
| M4 (Claude) | An **inference was printed inside a table headed "Measured"** | §5.5a — withdrawn |
| H4 (Codex) | `gen-backlog-page.py` refused to build | **Fixed** — commit `4090cc7`, not deferred |
| M1 (Codex) | Duplicate derivation vs `gen-goals-page.py` | §7 — a shared module, or it is not an "addition" |
| M2/M3 (Claude) | Two citations pointed at the wrong file | corrected in place |
| L1–L4 | Stale counts, stale sizes, missing paths, four-vs-five | corrected; §2 now records **when** each was measured |

**Not accepted, with reasons, in §12.**

---

## 1. Why this exists

The user's words:

> "I am having hard time to understand your output on chat dialogs. with abriviations, jargons and
> condensed explanations etc. I cannot monitor closely what you are doing and I lost in flooding text."

Ranked by them when asked:

| Rank | Failure |
|---|---|
| 1 | **Continuity** — cannot hold the thread across a day or a week; does not know what changed while away |
| 2 | **Volume with no signal** — too much text, no marker for what matters |
| 3 | **Terms** — *"if you occasionally remind me the definition of the acronyms, it will be helpful. Just don't make the prose a mix of unfamiliar terms"* |

And: *"Try to be plain and straightforward. No need to use your literary skills."*

Chat is transient; the user cannot re-read a week. The memory `output-style-plain-default` has carried
a version of this since 2026-08-12 and it recurred anyway, which is the argument for a durable page
rather than better chat discipline alone.

## 2. What already exists — measured, with dates

**Nothing here is rebuilt.** Every figure below was produced by running something on the date shown.

| Thing | Where | Measured |
|---|---|---|
| Local server | `scripts/explainer-serve.py`, `127.0.0.1:7391` | running, 2026-08-28 |
| Index / newest / goals / backlog | `GET /`, `/latest`, `/goals`, `/backlog-table` | 2026-08-28 |
| **Standing pages** | undated filename → extensionless URL; excluded from `/latest`; live-reloads | `explainer-serve.py:35-49` |
| Page → session channel | `POST /questions` → `~/explainers/questions.md` | `explainer-serve.py:671-698` |
| Tray lifting | `scripts/brief-compose.py` | **30/30** self-test, run 2026-08-28 |
| Page sizes | brief 69,049 B · goals 81,525 B · backlog-table 488,855 B | `stat`, 2026-08-28 15:0x |

⚠ **Two of those numbers were wrong in v2 and the reason is instructive.**
- v2 said `brief-compose.py` has **14** self-test cases, copied from `explainer-delivery.md:68`.
  Running it returns **30**. **The shared document is stale too** — a number was read rather than run,
  in a project whose rule is that a written count is a claim about a moving number.
- v2 said goals was 71 KB. It was, when measured — then this spec's own edits to `docs/anchors.md`
  and `docs/roadmap-to-launch.md` triggered `regen-goals-page.sh`, and it grew to 81,525 B within the
  hour. **Writing the spec invalidated its own measurement.**

**Therefore:** every count in this document names the command that produced it and the date. A count
without both is a defect.

## 3. Scope

### In
1. One standing page at `http://127.0.0.1:7391/dashboard`.
2. **What needs you**, first and unfolded (§5.0).
3. Overall picture visible; detail folded (§4), and folds that **survive a reload** (§4a).
4. Graphics: progress, activity, health, work-flow, backlog dependencies (§5.1–5.6).
5. A dated list of plain entries, from a durable store (§6a).
6. Recurring mistakes (§5.7).
7. A request box with **identified** requests and honest state (§8).
8. A glossary, folded.
9. Links to `/goals`, `/backlog-table`, `/latest`, `/`.

### Out
- Converting `gen-backlog-page.py`'s existing SVG diagram to Mermaid. **Note this is now a different
  decision from choosing the dashboard's renderer** — H6 showed v2 conflated them.
- Marketplace packaging itself (§7a — designing so it is possible is in scope).
- A "mark as read" memory of what the user has already seen.

## 4. The rule the whole page obeys

**Everything is folded. Nothing is deleted.** Three layers per entry:

| Layer | Visible | Language | Contains |
|---|---|---|---|
| Title line | yes | plain | one sentence; and whether it needs them |
| Fold 1 | no | **plain** | what happened, why it matters, what it means for them |
| Fold 2 | no | technical, **labelled as such** | commits, paths, commands, exact numbers |

Built with native `<details>`/`<summary>` — no JavaScript, keyboard-accessible, works saved to disk.

### 4a. Folds MUST survive live reload — H3

**Measured:** the injected reload client (`explainer-serve.py:559-580`) preserves **scroll**
(`sessionStorage`, `scrollY`) and refuses to reload while `#qbox` holds a draft. **It does nothing
for `<details>`.** The page rewrites itself whenever a source changes, so on a page whose entire
design is folding, every fold the reader opened snaps shut underneath them — most likely while they
are reading.

**Requirement:** the reload client persists the open/closed state of every `<details>` across a
reload, keyed by a stable id, the same way it already persists scroll. This is a change to
`explainer-serve.py`, and it benefits every existing page.
**Falsifier:** open two folds, touch a source file, confirm both are still open after the reload.
It fails today, which is what makes it a real test.

## 5. The page

### 5.0 What needs you — first, unfolded, and possibly empty — H8
A third of the registered goal is *"what needs them"*, and v2 surfaced it nowhere. It is now the
first block: one line per item awaiting the human, each naming the decision, or the words
**"Nothing needs you."** Derived from entries flagged `needs-you` (§6a) plus open pull requests.

### 5.1 Progress — REWRITTEN, because v2's source did not exist — B2
v2 said: *"the `### M<n>` headings and their ✅ / ◀ / ⛔ markers in `docs/roadmap-to-launch.md` — the
same source `gen-goals-page.py` already reads."* **Verified 2026-08-28, three falsehoods:**

| v2 claimed | Measured |
|---|---|
| `### M<n>` headings | all three are `##` (lines 49, 180, 265) |
| `gen-goals-page.py` reads that file | `grep -c roadmap-to-launch scripts/gen-goals-page.py` → **0** |
| a `◀` current-marker | `grep -cE "^#{1,6} M[0-9].*◀"` → **0**. M1 has 🚀, M2 🔗, M3 ✅ |

The `### M<n>` spine I described is `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md`
— the **schema-promotion** roadmap, a different milestone vocabulary. v2 merged the two.

**v3 derivation, chosen because it is verifiable rather than invented:** for each `## M<n>` section
of `docs/roadmap-to-launch.md`, count `- [x]` against `- [ ]`. That yields a real completion ratio
per milestone with no marker vocabulary to invent. "Current" = the first milestone that is neither
0% nor 100%. **Falsifier:** the rendered ratio must equal a hand count for one named milestone.

### 5.2 Activity — window is a parameter — H4
One bar per day. **Height = commits authored that day** (derivable, no judgement; it under-counts
uncommitted work and the page says so). **Orange = a day carrying an entry marked `needs-you`** — a
written claim, not a derived one.

Clicking a bar opens that day's entries. **The window defaults to 14 days and is a parameter**, with
a control to widen it: the absence this page exists for can exceed two weeks, and v2 gave no way to
look further back. Days beyond the window are still in the store (§6a) and reachable.

### 5.3 Health — THREE states, not two — H7
v2 said *"green or red"*. This project's own rule is **`"cannot run" is a FAILURE, never a pass`**, and
a check that could not reach its subject is neither green nor red. Three states: **passed**,
**failed**, **could not run** — the third visually distinct and never silently folded into either.
Plus one lamp for "waiting on you".
**Falsifier:** make a check unable to reach its subject; the lamp must show *could not run*, not green.

### 5.4 How work moves
`idea → spec → plan → build → review → pull request → merged`, with a marker on where current work
sits. Answers *what are you doing and where is this going* without requiring process knowledge.

### 5.5 Mermaid — bundled, WITH an exercised fallback

⟳ **v1 refused Mermaid. v2 reversed that. v3 keeps the reversal and reverses the "no fallback" half.**

#### 5.5a What is measured, and what is not — M4
| Fact | Value | How |
|---|---|---|
| bundle, v11.17.2 | **3,572,661 B** (3.41 MB); gzipped 979,561 B | downloaded + `wc -c`, 2026-08-28 |
| licence | **not simply MIT** — see §7a | read the file's own legal block |
| comparators | `superpowers` 4.0 MB, `remember` 10 MB | `du -sh`, 2026-08-28 |

⛔ **WITHDRAWN from v2:** the row asserting that `gen-backlog-page.py:419`'s "~1MB" *"is the gzipped
number"*. That line says only *"~1MB of library into a 419KB page"*. Nothing says gzipped, and the
sentence is about **inlining**, where raw size applies. It was an attribution of intent to a past
author, **printed inside a table headed "Measured"**, doing rhetorical work for the reversal. The
honest statement: the prior figure understates the raw bundle; why it did is unknown.

#### 5.5b From "bundled" to "loadable" — B1 (Codex), H5
**A plugin's install directory is not the served root.** `explainer-serve.py` serves `~/explainers`;
`/src/` cannot carry a script because non-raw source is wrapped in HTML (`explainer-serve.py:646-659`).
So "bundled, therefore present" was unfounded.

**Required:** an install step that places `mermaid.min.js` in the served root; a fixed URL; a MIME
check; and **a startup assertion that fails loudly when it is absent**, per
`"cannot run" is a FAILURE`.

#### 5.5c The fallback is REINSTATED, in its exercised form — H6
v2 argued *"a fallback nobody exercises is not a fallback"*. That argues against an **unexercised**
path, not against a fallback, and v2 then specified an unexercised path of its own — *"if the file is
absent or damaged, say so in plain words"* — with **no falsifier, no owner and no check row**. Same
flaw, one severity band down, unnoticed.

Verified failure modes v2 did not consider:
- **Truncation.** `globalThis["mermaid"] = …` is the **final line** of the file (read 2026-08-28). A
  partial copy serves HTTP 200 and leaves Mermaid undefined.
- **Absent from the served root** — §5.5b, the *default* state, not an edge case.
- **`file://`.** `explainer-delivery.md:94-96,141` promises **twice** that a saved copy still reads
  and loses only Send. v2 broke that promise for diagrams and did not retire it.
- **Managed browsers, content-security policy, air-gapped machines** — real for the marketplace
  audience §7a invokes.

**Decision:** the dependency graph is rendered by `dependency_svg` (`gen-backlog-page.py:414`), which
**already exists and is exercised on every backlog regeneration**; Mermaid renders the diagrams that
have no SVG renderer. **Both paths run on every build, so neither can rot** — which is what v2's own
argument actually demanded. Mermaid source stays available for export, and is now verified by being
rendered.

#### 5.5d The archival-vs-live rule moves OUT of this spec — M5, H3 (Codex)
v2 waived `explainer-delivery.md` §2 from inside this document. A shared rule is not amendable by one
of its subjects. **v3 requires a named page class — "live view" vs "archival artifact" — added to
`explainer-delivery.md` itself, as its own reviewed change.** Until that lands, this spec claims no
exemption.

### 5.6 Backlog — a section, not just a link
Visible: counts. Fold 1: the dependency diagram (§5.5c) and the items that block others, in plain
words. Link: `/backlog-table` for all 66 rows.

**Counts come from `gen-backlog-page.py`'s parser, never a second counter.**
⚠ **Round 1 found that generator refusing to build** — `GROUPS does not cover the open set … [66]`.
**Fixed in commit `4090cc7`** (rc=0, 66 rows, self-test 55/55), not deferred. v3 additionally requires
that the dashboard **fails loudly** if the parser refuses, rather than rendering last-known counts —
that refusal was invisible for a day, which is how it was found by accident.

### 5.7 Recurring mistakes — REINSTATED — H9
v2 deferred this for simplicity. The user asked for it (*"common mistakes etc."*), and §6 admits the
entry-writing weakness is a **recurring behavioural failure** — the exact category. Deferring the
section that would surface the spec's own weakest point is the wrong cut. Source: the memory files
under `.../memory/`, already written as recurring-failure notes. Folded; three or four at a time.

## 6. Where entries come from

The user chose: *"start with mainly (b)"* — I write them — *"and when there are important points, you
can put more details with (c)"*.

**The admitted weakness:** an entry exists only if I write it, and I would skip it exactly when busy.
Round 1 correctly said the v2 mitigation is an **alarm, not a recovery** — it makes the failure
legible without preventing it. That remains true, and is stated rather than solved.

### 6a. The entry store — B1 (Claude)
v2 had no store. Entries existed only as markup inside a page that is **regenerated in place**, so
the next regeneration destroyed them, and the script could not enumerate which days had entries —
breaking §6's own mitigation.

**`docs/dashboard-entries.md`**, in the repo, append-only. The skill appends; `gen-dashboard.py`
parses and renders; regeneration is lossless. Every sibling names its source this way
(`gen-goals-page.py:164` → `docs/anchors.md`; `gen-backlog-page.py` → `docs/backlog.md`).
In the repo, not `~/explainers`, so entries are versioned, reviewable and survive a lost machine.

Per entry: date, one-line plain title, `needs-you` flag, plain detail, optional technical detail.
**Falsifier:** write an entry, regenerate twice, confirm it survives and its day's bar is not empty.

## 7. Build — two pieces, split on judgement

| Piece | Does |
|---|---|
| `scripts/gen-dashboard.py` | derives facts, parses `docs/dashboard-entries.md`, renders frame + graphics |
| Skill `/dashboard` | writes the plain paragraph and entries; appends to the store; composes and delivers |

**Why a skill here when `/goals` and `/backlog-table` have none.** `regen-goals-page.sh:4-10` records
the rule: a purely derived page gets a script and a hook, never a skill. That holds — the dashboard is
**not** purely derived; the plain-English writing is the deliverable, and it is judgement.

⚠ **Shared derivation, or this is a fourth drifting surface — M1 (Codex).** `gen-goals-page.py`
already derives milestone state and git activity, and its docstring calls that page *"a dashboard"*.
`gen-dashboard.py` **must import** the shared derivation rather than re-implement it; if that proves
impractical, §2's claim of "an addition, not a new system" is withdrawn and this needs redesign.

**Consequence that must not be forgotten:** the skill joins `PAGE_SKILLS` in
`check-explainer-delivery.py`. **See §9 — that check cannot enforce its own list.**

## 7a. Distribution — a constraint, not a later step

*"eventually I want to publish this dashboard and related skills and scripts to marketplace."*

| Consequence | Requirement |
|---|---|
| Users are not this project | no assumed paths; every source is a parameter with a documented default |
| Users install nothing | Mermaid ships in the plugin; Python 3 and a browser are the only assumptions |
| Users never read this spec | failures self-explain: what is missing, what to do |
| Size budget | 3.4 MB against a 4–10 MB norm — recorded, so a later addition is a decision |

⚠ **Licence — v2 was WRONG and this matters for redistribution — M1 (Claude).** v2 said *"MIT —
attribution"*, singular, from `npm view mermaid license`. **That describes the package's own
declaration, not the artifact being shipped.** Read 2026-08-28, `mermaid.min.js`'s own legal block
carries **four distinct copyright holders** and names **Apache License 2.0** and **Mozilla Public
License 2.0** alongside MIT. Redistribution therefore requires the **bundled third-party notices**,
not one MIT line. A pre-publication licence audit is a required task, not a footnote.

⚠ `docs/backlog.md` #40 (task #75) already asks to package `explain-diff` + `explainer-serve` as a
plugin. This rides that work; planned separately, the plugin gets built twice.

## 8. Requests — with identity — B2 (Codex), H2 (Claude)

Four buttons and a text box, sending through the existing `POST /questions` channel.

**A button cannot run anything.** It records a request. A live session sees it in seconds; otherwise
it waits.

⚠ **v2's state list was not implementable.** Measured (`explainer-serve.py:671-698`, and the shape of
`~/explainers/questions.md`): an entry carries **only** a timestamp, a page name and free text. **No
id, no type, no status.** Two identical requests are indistinguishable; one page may answer several.
v2 called text-matching "honesty".

**v3:** the page generates a request **id** and sends it in the payload; `format_question_entry`
records it. When a request is handled, a **resolution line** naming that id is appended. The page
derives `waiting` / `done` by **id match only** — never by guessing. Requires a small
`explainer-serve.py` change, which is ours to make.
**Falsifier:** two requests with byte-identical text must be distinguishable, and resolving one must
not mark the other done.

## 9. How we will know it works

**It fails if** the user opens the dashboard after two days away and still has to ask "what happened?"

Round 1 rightly called that **weak as acceptance**, because it is not attributable — failure could be
stale entries, too many folds, a missing glossary, or wrong priorities. **v3 adds observable
sub-criteria**, each independently checkable:

- the page names the last date an entry was written;
- every day with commits and no entry is visibly marked;
- "what needs you" is present and correct, or explicitly empty;
- the current branch, deployed release, and each check's state are shown;
- every fold survives a reload.

⚠ **§9's flagship check in v2 was stated backwards — H1, both halves.** v2 claimed
`check-explainer-delivery.py` *"fails when `dashboard` is absent from `PAGE_SKILLS`"*. **Measured:**
`PAGE_SKILLS` is a hardcoded list (`:53`); the audit only inspects skills **on** it, so an absent
skill is invisible and the check exits green. **It cannot enforce its own membership.** Stated
correctly: adding `dashboard` to `PAGE_SKILLS` is a manual step with **no gate behind it**, and this
spec does not pretend otherwise. Closing that hole is its own change.

| Check | Fails when |
|---|---|
| `gen-dashboard.py --self-test` | milestone ratios, activity buckets, entry parsing or request state mis-derive |
| fold-survival probe | any `<details>` closes across a reload (§4a) |
| mermaid-absence probe | the asset is missing and the page does **not** say so (§5.5b) |
| SVG-path probe | the dependency graph fails to render with Mermaid unavailable (§5.5c) |
| affordance probe | ask-buttons are not topmost at their own centre (`explainer-delivery.md` §5b) |

**None of these measure comprehension.** They measure that the page was built correctly. Only the
user can report whether it works, and the design is revised on their word, not on a green check.

## 10. Risks

| Risk | Mitigation |
|---|---|
| I stop writing entries | store is enumerable, so empty days are visible (§6a). An alarm, not a cure — stated |
| The page becomes another wall of text | everything folded; only title lines visible |
| Fold 1 drifts into jargon | treated as a defect on the user's report, not a style preference |
| Built but never opened by its author | `explainer-delivery.md` §5b in full; refuse to conclude from a hidden tab |
| Mermaid asset missing in the field | §5.5b assertion + §5.5c exercised SVG path |
| Fourth status surface | §7 shared-module requirement; if impossible, redesign |

## 11. Open questions

1. Default activity window — 14 days is a starting guess (§5.2).
2. Glossary hand-written or derived — starting hand-written; deriving risks a vocabulary that
   silently stops matching.
3. Whether the fold-survival change to `explainer-serve.py` (§4a) ships here or as its own change,
   since it improves every existing page.

## 12. Round-1 findings NOT accepted

- **Codex M2 — "the missing-entry mitigation is only an alarm."** Correct, and **accepted as a
  limitation rather than fixed**: no mechanism can make me write an entry. §6 says so plainly instead
  of claiming a cure.
- **Codex L1 — "KB vs KiB."** Real, but the fix is to record the byte count and the date, which §2
  now does. Unit pedantry is not the defect; unsourced numbers are.

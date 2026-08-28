# Adversarial review — `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` v3, round 2 (Claude half)

**Reviewer:** Claude, independent half of round 2. `docs/reviews/spec-project-dashboard-r2-codex.md`
was deliberately left unopened. Both round-1 reviews were read, because this round judges whether
their findings were really fixed.

**Method.** Every derivation v3 newly specifies was **executed**, not read. §5.1's checkbox count was
run against `docs/roadmap-to-launch.md`. `gen-backlog-page.py` was run and self-tested.
`dependency_svg`'s inputs were opened. The page sizes §2 records were re-`stat`ed. `git log` was
measured for the activity chart's metric.

**Counts:** 2 Blocking · 7 High · 7 Medium · 3 Low.

**Verdict in one line:** v3 fixed most of round 1 honestly, and the one fix that mattered most —
§5.1, the first graphic on the page — replaced a source that did not exist with a source that
produces a **provably useless answer**, which was not checked because nobody ran it.

---

## Round-1 findings: genuinely closed vs only claimed closed

### Genuinely closed — VERIFIED, do not re-review these

| Round-1 finding | Evidence |
|---|---|
| **H4 (Codex)** — `gen-backlog-page.py` refused to build | `python3 scripts/gen-backlog-page.py` → **rc=0**; `--self-test` → **55/55 passed**; commit `4090cc7` exists on this branch |
| **H1 (both)** — §9's flagship check cannot fail | v3 §9 lines 345-350 now state it as an escape with **no gate behind it**, and say so in the body rather than the table. This is a model correction |
| **H7 (Claude)** — health lamps had two states | §5.3 lines 171-176: three states, third visually distinct, with a real falsifier |
| **H4 (Claude)** — 14-day window | §5.2 lines 166-168: window is a parameter, widening control, days beyond it reachable |
| **M4 (Claude)** — inference printed inside a table headed "Measured" | §5.5a lines 192-196: **withdrawn**, with the reason. Exemplary |
| **M1 (Claude)** — licence described the package, not the artifact | §7a lines 302-307: four holders, Apache-2.0 and MPL-2.0 named, audit made a required task |
| **M2/M3 (Claude)** — two citations pointed at the wrong file | Both removed; `grep` finds no `110`/`117` claim and no attribution of `PAGE_SKILLS` to `explainer-delivery.md` |
| **L4** — four-vs-five graphics | §3 In-4 now names five; §3 Out no longer says four |
| **L1** — 14 vs 30 self-test cases | `python3 scripts/brief-compose.py --self-test` → **30/30 passed**; §2 line 77 says 30 |
| **Codex M2 / L1** — not accepted | §12 declines both with reasons that hold. Declining with a reason is a legitimate disposition |

### Claimed closed in §0, but NOT closed

| §0 row | Reality |
|---|---|
| **B2 (Claude)** — *"§5.1 rewritten on a verified source"* | The refutation was verified; **the replacement was not run**. It yields 100% for all three milestones and no current milestone → **Blocking B1** below |
| **M1 (Codex)** — *"§7 — a shared module, or it is not an 'addition'"* | §5.1's new derivation is **not the one `gen-goals-page.py` uses and cannot be**, so §7's escape condition is already true at spec time → **Blocking B2** |
| **H6 (Claude)** — *"§5.5c — an *exercised* fallback"* | Half true. The fallback is reinstated (good), but *"both paths run on every build"* is **false for the Mermaid half** (H2), and the SVG renderer is not the diagram the spec thinks it is (H3) |
| **H8 (Claude)** — *"§5.0 — it is now the first thing on the page"* | Present, and it is the right fix. But it can render **"Nothing needs you."** when its source could not be read (H1) |
| **H9 (Claude)** — *"§5.7 — reinstated"* | Present, but sourced from a machine-local unversioned directory that no other user has (H5) |
| **B1 (Codex) / H5 (Claude)** — *"§5.5b — an install step with a startup assertion"* | The *requirement* is named; the **step** is not. H5's specific questions — who copies, when, on upgrade, on divergence — are all still unanswered (M6) |
| **B2 (Codex) / H2 (Claude)** — *"§8 — explicit ids + resolution records"* | Ambiguity is genuinely fixed by ids. The resolution record has **no actor, no file, and no id grammar**, and question text is written verbatim (H6) |
| **B1 (Claude)** — *"§6a — a durable append-only store"* | The right shape, and I credit it. It was not checked against **this repo's own change process** for `docs/` (H7) |
| **L1–L4** — *"missing paths … corrected"* | **False.** All **eight** `explainer-delivery.md` citations in v3 are bare filenames, and v3 **added four more** than v1 had (M1) |
| **L2** — *"§2 now records **when** each was measured"* | Two of the three page sizes were already wrong **the same day** (M2) |
| **M5 / H3 (Codex)** — *"§5.5d — the change moves to the shared doc"* | Honestly moved out. That honesty creates a contradiction the spec does not resolve: §5.5b specifies a page §5.5d says is not permitted yet (H4) |

---

# BLOCKING

## B1 — §5.1's replacement derivation renders every milestone at 100% and no current milestone. I ran it.

**Claim attacked.** §5.1 lines 156-159:

> *"**v3 derivation, chosen because it is verifiable rather than invented:** for each `## M<n>`
> section of `docs/roadmap-to-launch.md`, count `- [x]` against `- [ ]`. That yields a real
> completion ratio per milestone with no marker vocabulary to invent. "Current" = the first milestone
> that is neither 0% nor 100%. **Falsifier:** the rendered ratio must equal a hand count for one
> named milestone."*

**What I checked.** I implemented the stated rule exactly — split `docs/roadmap-to-launch.md` at each
`##` heading, take the three `## M<n>` sections, count `- [x]` against `- [ ]`:

```
'## M1 — Deploy (the app goes live) 🚀'          lines  49-179   [x]=7  [ ]=0  → 100%
'## M2 — Sync (unify local + cloud, Stage 3) 🔗' lines 180-264   [x]=5  [ ]=0  → 100%
'## M3 — Acceptance ✅ **CLOSED 2026-08-13**'    lines 265-401   [x]=2  [ ]=0  → 100%

WHOLE FILE: [x]=44  [ ]=14      ← all 14 unticked boxes are OUTSIDE the M sections
```

**What is actually true.**

1. **Every milestone is 100%.** The progress graphic — *"graphic number one on a page whose entire
   purpose is orientation"*, in round 1's words — renders three full bars. To a reader who was away,
   it says **the project is finished.**
2. **"Current" is undefined.** *"The first milestone that is neither 0% nor 100%"* matches **nothing**.
   The spec does not say what is rendered then. v2's defect was *no current marker at all*
   (round-1 B2, point 3); v3's derivation produces **the same outcome by a different route.**
3. **The roadmap itself says so, and the spec did not read that far.**
   `docs/roadmap-to-launch.md:33-35`: *"**All three launch milestones (M1 Deploy, M2 Sync, M3
   Acceptance) are closed** … Remaining work lives in `docs/backlog.md`."* The launch-milestone
   vocabulary is **spent**. Meanwhile §5.6 of this same spec renders 66 backlog rows on the same
   page. The dashboard will show *100% complete* directly above *49 open items*.
4. **The bar widths are not comparable anyway.** 7, 5 and 2 checkboxes. An equal-width three-bar
   chart weights M3's two boxes the same as M1's seven.

**The falsifier is aimed at the wrong subject, which is why this survived.** *"The rendered ratio
must equal a hand count for one named milestone"* — I performed that hand count: M1 is 7/7, and the
rule reproduces it. **The falsifier passes while the graphic is useless.** This is the project's own
standing rule, from `CLAUDE.md`: *"A script beats a claim only when it reads the thing the claim is
about."* The claim §5.1 makes is *"the reader can see how far along the whole thing is"*; the
falsifier checks arithmetic.

**Why this is the round's most important finding.** §5.1's *refutation* of v2 is meticulous —
lines 49, 180, 265 are exactly right, `grep -c roadmap-to-launch scripts/gen-goals-page.py` → 0 is
exactly right, the 🚀/🔗/✅ markers are exactly right. **The file was opened to disprove the old rule
and not run to test the new one.** That is a narrower version of the same habit round-1 B2 named, and
it landed in the same section, one revision later.

*(VERIFIED: every count above, by executing the stated rule. INFERRED: nothing — the numbers are the
finding.)*

## B2 — §5.1's fix makes §7's shared-derivation requirement unsatisfiable, so §7's own "needs redesign" condition is already met

**Claims attacked.** §7 lines 283-286:

> *"`gen-goals-page.py` already derives milestone state and git activity … `gen-dashboard.py` **must
> import** the shared derivation rather than re-implement it; if that proves impractical, §2's claim
> of "an addition, not a new system" is withdrawn and this needs redesign."*

versus §5.1's derivation quoted in B1.

**What I checked.** `scripts/gen-goals-page.py`:

- `:65` — `MILESTONE = re.compile(r"^#{2,4}\s+(M\d+)\s*[—-]?\s*(.*)$", re.M)`
- `:71` — `MILESTONE_STATES = (("⛔", "deferred"), ("◀", "next"), ("✅", "done"))`
- `:110-114` — `parse_milestones` docstring: *"State comes from the heading's own **marker**, never
  from a table maintained here."*
- `:193` — `"milestones": parse_milestones(f.read_text())` — applied **per spec/plan file** found
  under `SUBDIRS = ("superpowers/specs", "superpowers/plans")` (`:56`, `:180-194`).

**What is actually true.** The two derivations share nothing but the word *milestone*:

| | `/goals` | dashboard §5.1 |
|---|---|---|
| Source | each `docs/superpowers/{specs,plans}/*.md` | `docs/roadmap-to-launch.md` |
| Unit | `M\d+` headings **inside a document** | `## M<n>` sections of one file |
| State from | emoji markers ⛔ ◀ ✅ | `- [x]` vs `- [ ]` ratio |
| Vocabulary | per-document milestones (e.g. the schema-promotion M1–M7) | the three launch milestones |

There is **no shared function to import**, because there is no shared derivation. §7's requirement
cannot be met for milestone state without one of the two pages changing its meaning — and §5.1
chose its rule specifically to avoid the marker vocabulary `/goals` depends on.

**Why Blocking rather than High.** §7 does not treat this as a preference. It attaches a consequence:
*"if that proves impractical, §2's claim … is withdrawn and **this needs redesign**."* The condition
is satisfiable-or-not **at spec time**, and I have measured that it is not satisfiable. So by the
spec's own terms v3 is already in its redesign branch, and §0's row *"M1 (Codex) | Duplicate
derivation | §7 — a shared module"* records the opposite. Round 1's cross-cutting note predicted
exactly this — *"the two pages will compute milestone state from different files … that is
`two-mechanisms-for-one-concern` arriving by the front door"* — and v3's B2 fix is what made the
prediction come true.

**On the escape hatch, since the prompt asked.** *"Proves impractical"* has no named judge and no
criterion, and its consequence is so heavy (redesign) that no implementer under deadline will ever
invoke it. It would be an escape hatch even if the condition were not already true. It is worse than
that: it is an escape hatch whose trigger has **already fired**, unnoticed, inside the same revision.

---

# HIGH

## H1 — §5.0, the first block on the page, can print "Nothing needs you." when it could not read its source

**Claim attacked.** §5.0 lines 138-141:

> *"It is now the first block: one line per item awaiting the human, each naming the decision, or the
> words **"Nothing needs you."** Derived from entries flagged `needs-you` (§6a) plus **open pull
> requests**."*

**What I checked.** §5.3 (lines 171-176) establishes three states *for health lamps* — passed,
failed, could not run — citing the project rule verbatim: *"`"cannot run" is a FAILURE, never a
pass`"*. I then searched §5.0 for any equivalent. There is none. §5.0 has **two** outcomes: a list,
or "Nothing needs you." I also ran the source it names: `gh pr list --state open` requires network
and an authenticated `gh`; today it returns one row (PR #168). With `gh` absent, unauthenticated, or
offline, the natural implementation renders an empty list.

**What is actually true.** The fix for H8 reintroduced the failure H7 was raised about, in the one
block where it is most expensive. A false *"Nothing needs you."* is not a missing signal — it is an
**all-clear** for a reader whose entire reason for opening the page is to learn whether something is
waiting on them. Round 1's H7 argued this for a *lamp*; §5.0 is the answer to a third of the goal
sentence and it is the first thing on the page.

**§5.0 also has no falsifier.** §4a, §5.1, §5.3, §6a and §8 each carry one. §5.0, §5.2, §5.4, §5.6
and §5.7 do not. Per `CLAUDE.md`: *"State the observation that would make it FAIL. If none can be
named, it is a decision or an investigation wearing a checkbox."*

## H2 — "Both paths run on every build" is false for the Mermaid half, and §9 has no probe that Mermaid ever rendered anything

**Claim attacked.** §5.5c lines 222-226:

> *"the dependency graph is rendered by `dependency_svg` … Mermaid renders the diagrams that have no
> SVG renderer. **Both paths run on every build, so neither can rot** — which is what v2's own
> argument actually demanded."*

**What I checked.** `scripts/gen-backlog-page.py`:

- `dependency_svg` (`:418`) emits SVG markup **at generation time** — it genuinely runs on every build.
- `dependency_mermaid` (`:478`) emits **source text**. Its own docstring, `:481-482`:
  *"⚠ **NOT RENDERED HERE** — mermaid is not installed and this page cannot fetch it, so this string
  is emitted from the same data as the SVG above but **its rendering is unverified**."*
- The self-test cases at `:1532-1546` check the mermaid **string** — that it starts `flowchart LR`,
  has one edge per dependency, escapes backticks and quotes, and has the same edge count as the SVG.
  **Not one of them renders it.**

**What is actually true.** Mermaid renders in the **browser**, at view time. No build step in this
repo executes a Mermaid renderer, and none is proposed. So of §5.5c's two paths, one runs on every
build and one runs nowhere except a reader's browser. The sentence *"neither can rot"* is true of
`dependency_svg` and asserted of Mermaid.

**And §9 leaves the gap exactly where it is.** Its five checks include a *mermaid-absence probe*
(*"the asset is missing and the page does not say so"*) and an *SVG-path probe* (*"the dependency
graph fails to render with Mermaid unavailable"*). **Neither observes Mermaid successfully rendering
a diagram.** So the renderer responsible for four of the page's five graphics has a check for its
absence and no check for its correctness — which is the failure mode `gen-backlog-page.py:481` warned
about in writing four months of commits ago.

Round 1's H6 demanded *"exercises both on every build"*. v3 adopted the sentence without acquiring
the property.

## H3 — `dependency_svg` does not render "the dependency graph". It renders one parked slice and 6 of 49 open items.

**Claim attacked.** §5.5c line 222 (*"the dependency graph is rendered by `dependency_svg`
(`gen-backlog-page.py:414`), which **already exists and is exercised on every backlog
regeneration**"*) and §5.6 line 236 (*"Fold 1: the dependency diagram (§5.5c) and the items that
block others, in plain words"*).

**What I checked.** `scripts/gen-backlog-page.py:354-384`:

```python
ROOTS: dict[str, dict[str, str]] = {
    "stable-blob-addressing": dict(
        label="The stable-addressing slice",
        detail="ADR-0006 — <code>status: proposed</code>, and the schema slice was parked on "
               "2026-08-11 to return to the launch roadmap. …",
    ),
}
...
DEPENDS: dict[int, tuple[str, str, str]] = {
    19: …, 17: …, 52: …, 20: …, 21: …, 22: …,   # six items, all rooted at stable-blob-addressing
}
```

`dependency_svg` (`:418`) iterates `ROOTS`, and for each root the items in `DEPENDS` that name it.
The root box's hardcoded sub-label is `'start here · parked'` (`:470`).

**What is actually true.** The graph is a **hand-maintained six-edge map of one parked decision** —
not a derived view of the backlog's dependency structure. The backlog has 66 rows, 49 open. Put on an
orientation dashboard for someone who has been away, this diagram tells them the shape of the work is
the stable-blob-addressing slice, which `docs/roadmap-to-launch.md:708` records as
**⏸ PARKED 2026-08-11 by user decision**.

So the one graphic v3 moved off Mermaid to make the fallback "exercised" is a graphic that, on this
page, is misleading. §5.6's *"the items that block others"* is a different and larger claim than what
`dependency_svg` draws.

*(VERIFIED: `ROOTS`, `DEPENDS`, the hardcoded caption, the 66/49 counts. INFERRED: that a reader
would misread it — but the caption literally says "start here", so the inference is short.)*

## H4 — §5.5b specifies a page that §5.5d says is not permitted, and the spec does not resolve the order

**Claims attacked.** §5.5b lines 203-205 (*"**Required:** an install step that places
`mermaid.min.js` in the served root; a fixed URL; a MIME check …"*) against §5.5d lines 229-232:

> *"A shared rule is not amendable by one of its subjects. **v3 requires a named page class — "live
> view" vs "archival artifact" — added to `explainer-delivery.md` itself, as its own reviewed
> change.** Until that lands, **this spec claims no exemption.**"*

**What I checked.** `.agents/skills/shared/explainer-delivery.md:35-36`:

> *"**One self-contained HTML file.** Inline CSS and JS. **No external fonts, CDNs, images, or
> network access of any kind** — it must render offline, and in five years."*

A `<script src="/mermaid.min.js">` fetched from `127.0.0.1:7391` is network access, and the rule
admits no locality qualifier.

**What is actually true.** §5.5d is the honest move and I credit it — round 1 M5/H3 was right that a
shared rule cannot be waived from inside one of its subjects. But the consequence was not carried
through: with no exemption claimed, **the dashboard as specified in §5.5b violates a rule the spec
says binds it.** A plan written from v3 today implements a violation.

What is missing is one sentence of sequencing: is the `explainer-delivery.md` change a **prerequisite**
(so this spec cannot be planned until it lands), or does the dashboard ship SVG-only until then? §11's
open questions do not include it. §10's risk table does not carry it. This is a real fork the spec
leaves for the implementer, which is round-1 B1's stated definition of a spec that is not ready.

## H5 — §5.7's source is a machine-local, unversioned, per-user directory, which contradicts §7a and §6a

**Claim attacked.** §5.7 lines 247-248:

> *"Source: the memory files under `.../memory/`, already written as recurring-failure notes."*

**What I checked.** The elided path resolves to
`/Users/kujinlee/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/memory/`
— **88 files**, and they do contain what is claimed (`a-hang-is-not-a-diagnosis.md`,
`a-convention-catches-what-you-read.md`, …, indexed under *"How things go wrong here"*). So the
source exists and holds the content.

**What is actually true, and it is three separate contradictions.**

1. **§7a line 297:** *"Users are not this project | **no assumed paths**; every source is a parameter
   with a documented default."* This directory is keyed to one user's home **and to this repository's
   absolute path** (`-Users-kujinlee-code-agentic-ai-...`). There is no default that works for anyone
   else. §5.7 cannot ship to the marketplace §7a exists to design for.
2. **§6a line 267** argues entries belong *"in the repo, not `~/explainers`, so entries are
   versioned, reviewable and **survive a lost machine**."* §5.7 sources the section that §5.7 itself
   calls the durable one from a directory with none of those three properties.
3. **The path is elided to `.../memory/`** in a document §7a says must be readable by people outside
   this repo — the same defect as round-1 L3, in a section added *by* the round-1 fixes.

**What round 1's H9 actually argued** was that recurring-mistakes is *"the only requested section that
does not rot"*. That argument depended on the material being durable. Sourced this way it is the
**least** durable content on the page.

## H6 — §8's resolution record has no actor, no file and no id grammar, and free-form question text is written verbatim

**Claim attacked.** §8 lines 324-329:

> *"the page generates a request **id** and sends it in the payload; `format_question_entry` records
> it. When a request is handled, a **resolution line** naming that id is appended. The page derives
> `waiting` / `done` by **id match only** — never by guessing."*

**What I checked.** `scripts/explainer-serve.py`:

- `do_POST` (`:671-698`) — reads `Content-Length`, bounds it by `MAX_BODY`, parses JSON, requires
  `question_text(payload)` non-None, appends `format_question_entry(payload, now)` to `QUESTIONS`.
- `format_question_entry` (`:476-488`) returns, with **no escaping of either field**:
  `f"\n---\n\n## {now} — {doc}\n\n{text}\n"`
- `~/explainers/questions.md` — 391 lines, **47** existing `## ` entries, none carrying an id.

**Three things are true, in descending order of importance.**

1. **"Appended" has no actor and no file.** Passive voice throughout. Who writes the resolution
   line — me, by hand, into `~/explainers/questions.md`? Then §8's state display rests on exactly the
   mechanism §6 line 255 admits is unreliable: *"an entry exists only if I write it, and I would skip
   it exactly when busy."* §6 states that weakness for entries and §8 silently inherits it without
   restating it. The failure mode is *a handled request shows `waiting` forever* — **which is
   verbatim the failure round-1 H2 raised**, arriving through the resolution record instead of
   through text matching.
2. **Deriving state from that file makes it a trust boundary, and the text in it is attacker-supplied
   and unescaped.** `{text}` is whatever the reader typed. If the dashboard scans `questions.md` for
   resolution lines, a question whose *body* contains a line in the resolution format forges a
   resolution — or, containing `\n---\n\n## `, splits itself into a second entry. §8 specifies **no
   grammar for the id** (charset, length, uniqueness) and no validation, and `format_question_entry`
   applies none. This is a defect the fix **created**: before v3 nothing parsed that file for state.
3. **The 47 existing id-less entries are unspecified.** Rendered as `waiting` forever, or filtered
   out silently? The spec says nothing, and either choice is visible on the page.

**§8's falsifier does not reach any of this.** *"Two requests with byte-identical text must be
distinguishable, and resolving one must not mark the other done"* tests exactly the round-1 defect and
nothing the fix introduced.

## H7 — §6a puts entries in the repo without checking the repo's own rule for changing `docs/`

**Claim attacked.** §6a lines 264-268: *"**`docs/dashboard-entries.md`**, in the repo, append-only.
The skill appends; `gen-dashboard.py` parses and renders; regeneration is lossless. … In the repo,
not `~/explainers`, so entries are versioned, reviewable and survive a lost machine."*

**I want to be clear that this is the right shape** and it closes round-1 B1's structural problem:
the store is durable, enumerable, and named the way every sibling names its source (`gen-goals-page.py:164`
→ `docs/anchors.md`). `docs/dashboard-entries.md` does not exist yet, which is correct for a spec.

**What I checked.** `docs/dev-process.md`, Phase 5 (*"branch + PR is the standard path (set
2026-07-30)"*), whose table reads: **`Docs` → "Branch + PR, **batched**"**, and *"Standalone doc edits
accumulate."* Merging is a human gate. This repo has a remote, so the "no remote → direct commit"
escape does not apply. Measured: `origin/master`'s last 12 commits are one squashed commit per PR.

**What is actually true.** Writing a dashboard entry is a change to `docs/`. Under this project's own
Phase 5 rule it needs a branch and a PR, batched — and the merge is a **human gate**. So:

- an entry written today is on a branch, and the dashboard rendered from `master` will not show it;
- an entry written today is on a branch, and the dashboard rendered from the **working tree** shows
  entries the user cannot see from anywhere else;
- *"batched"* is explicitly the prescribed remedy for doc-PR friction, and batching is the opposite
  of what a same-day continuity page needs;
- **append-only is not conflict-free.** Two sessions on two branches both appending at the tail of
  one file conflict on merge, every time. §6a says *"append-only"* as if that settled it.

This is a genuine new defect created by the B1 fix: moving the store into the repo bought durability
and inherited the repo's change process. The spec does not mention the trade at all. §11's open
questions are the natural home for it and it is not there.

*(VERIFIED: the dev-process rule, the squash-per-PR history, the absence of any mention in §6a/§10/§11.
INFERRED: that the friction bites daily — that follows from "one entry per session".)*

---

# MEDIUM

## M1 — §0 claims "missing paths … corrected"; v3 has eight bare citations, four more than v1

§0 line 40: *"L1–L4 | Stale counts, stale sizes, **missing paths**, four-vs-five | **corrected**"*.

`grep -n "explainer-delivery" docs/superpowers/specs/2026-08-28-project-dashboard-design.md` → lines
81, 217, 229, 231, 289, 346, 358, 370. `grep -n "\.agents/\|\.claude/skills"` → **no matches**. The
file is at `.agents/skills/shared/explainer-delivery.md`; round-1 L3 said so.

Round 1 found four such citations. v3 has eight. **The count went up and the table says it was
fixed.** This is the class the prompt named: a row claiming a fix the body does not deliver stops
anyone looking again.

## M2 — §2's page sizes were already wrong the same day, which is the defect §2 was written to fix

§2 line 78: *"Page sizes | brief 69,049 B · goals 81,525 B · backlog-table 488,855 B | `stat`,
2026-08-28 15:0x"*. Re-`stat`ed today:

```
87608   /Users/kujinlee/explainers/goals.html          (spec: 81,525 — +6,083 B)
561737  /Users/kujinlee/explainers/backlog-table.html  (spec: 488,855 — +72,882 B)
```

`backlog-table.html` moved because commit `4090cc7` — **this branch's own fix** — let the generator
rebuild after it had been refusing. `goals.html` moved because a hook regenerates it on five source
patterns.

§2 line 88 concludes: *"every count in this document names the command that produced it and the date.
A count without both is a defect."* That remedy **labels** staleness; it does not prevent it, and §2's
own worked example (*"Writing the spec invalidated its own measurement"*) shows the author knew the
half-life was hours. The honest form is to stop printing volatile page sizes at all, or to derive
them. As it stands, §5.5a's size-budget argument (*"3.4 MB against a 4–10 MB norm"*) rests on numbers
that decay within a day.

## M3 — §9's new sub-criteria require page content §5 does not specify

§9 lines 341-343 lists as observable sub-criteria: *"the **current branch**, **deployed release**, and
each check's state are shown"*.

I walked §5.0 through §5.7 and §6a. There is **no block, slot or source** for the current branch or
the deployed release. §5.3's lamps are per-check. Deployed release, in this project, means
`flyctl releases` — network, credentials, and a "cannot run" case that §5.0/§9 do not provide for.

The fix for round-1's "weak acceptance criterion" added requirements to §9 without adding them to §5.
An acceptance criterion for content the design does not contain will either fail forever or be
quietly dropped.

## M4 — §5.2's metric counts squashed PR merges, not work, and does not say which ref

§5.2 line 163: *"**Height = commits authored that day** (derivable, no judgement; it under-counts
uncommitted work and the page says so)."*

Measured on `origin/master` — every one of the last 12 commits is a squash with `(#NNN)` in the
subject and author date == committer date == merge time:

```
9733102  a=2026-08-28 12:20  c=2026-08-28 12:20  docs(portable): … (#167)
d077327  a=2026-08-28 11:04  c=2026-08-28 11:04  fix(gates): … (#166)
```

So a bar's height is **PRs merged that day**, not commits authored that day. On this very branch,
four commits spanning the spec's whole life will become **one** on merge. The stated caveat names only
uncommitted work.

The ref is also unspecified. Rendered from the working tree, today's chart includes branch commits
that vanish on merge; rendered from `master`, work-in-progress is invisible — including the entries
of H7.

## M5 — §4a's "stable id" is unassigned, and "benefits every existing page" is unearned

§4a lines 130-132: *"the reload client persists the open/closed state of every `<details>` across a
reload, **keyed by a stable id**, the same way it already persists scroll. This is a change to
`explainer-serve.py`, and **it benefits every existing page**."*

The citation is right: `RELOAD_JS` (`explainer-serve.py:556-583`) saves and restores only
`window.scrollY` under `KEY = 'explainer-scroll:' + here` (`:559-564`, `:579`), and the comment at
`:551-552` confirms it is injected server-side into *"every page … including the ones already on
disk"*.

But **nothing assigns the ids.** No existing generator emits an id on a `<details>`; round 1 measured
119 of them on `backlog-table.html` alone. A DOM-order key is exactly what a regeneration invalidates
— reorder or remove one section and every fold below it restores the wrong state, which is worse than
closing them all, because it is silent. The dashboard could emit ids from `gen-dashboard.py`; the
other pages cannot without their own changes. So the falsifier (*"open two folds, touch a source file,
confirm both are still open"*) will pass on the dashboard while the claimed universal benefit is
absent — and §11 question 3 asks whether the change ships here or separately without noticing that
half of it lives in the generators, not in `explainer-serve.py`.

## M6 — §5.5b's "startup assertion" has no owner and cannot observe the failure that matters

§5.5b line 205: *"a startup assertion that fails loudly when it is absent"*. Startup of **what**?

- `explainer-serve.py` — then the server refuses to start for every user of the four existing page
  kinds because of an asset only the dashboard needs. That is a regression, not a guard.
- `gen-dashboard.py` — then it checks at **generation** time. The asset can be deleted from
  `~/explainers` afterwards, and `.agents/skills/shared/explainer-delivery.md:28-31` records that
  `~/explainers` is *"**Outside the repository, deliberately** — no `.gitignore` entry, nothing to
  commit by accident"*, i.e. unversioned and hand-cleanable. The view-time failure §5.5c exists for is
  precisely the one a generation-time assertion cannot see.

Round-1 H5 asked four questions — who copies, when, on upgrade, on divergence between the plugin's
bundled copy and the served copy. v3 answers none of them; it restates the requirement in better
words. §0 records this as *"an install step with a startup assertion"*.

## M7 — §9's SVG-path probe measures a mistake nobody is about to make

§9's table: *"SVG-path probe | the dependency graph fails to render **with Mermaid unavailable**"*.

By construction (§5.5c, and `dependency_svg` at `gen-backlog-page.py:418`) the dependency graph is
inline SVG produced at generation time and has **no** Mermaid dependency. The only way this probe
fires is if someone later reimplements that diagram in Mermaid. That is a legitimate regression guard
— I am not calling it vacuous — but it is the cheap half. Naming the observation that would make each
check fail (the project's own gate rule) exposes that the expensive half is missing: **no check fires
when Mermaid is present and renders nothing.** See H2.

---

# LOW

## L1 — `dependency_svg` is cited at the wrong line

§5.5c line 222 cites `gen-backlog-page.py:414`. `def dependency_svg` is at **`:418`**; `:414` is
inside `depends_errors`. Round 1 made the same slip, so this is inherited rather than invented — but
§2's rule is that a citation is a claim about a moving target, and commit `4090cc7` moved it.

## L2 — Importing `dependency_svg` yields unstyled SVG

The function emits markup carrying `class="depmap"`, `n n-root`, `e e-kill`, `elabel`, `nid`,
`ntitle`, `rootlbl`, `rootsub`. Those 18 rules live in `gen-backlog-page.py`'s stylesheet at
`:981-998`, and they resolve **11 CSS variables** (`--panel`, `--line`, `--structural`, `--problem`,
`--pending`, `--measured`, `--ink`, `--ink-3`, `--sans`, `--mono`, `--serif`) defined elsewhere in the
same page. §5.5c's *"already exists and is exercised"* is true of the **function**; the rendered
diagram additionally requires the host page's design system. Small, but it is the difference between
"import it" and "port it", and §7 makes importing a requirement.

## L3 — `explainer-delivery.md:68` still says 14

§2 line 82 says *"**The shared document is stale too** — a number was read rather than run"*.
`.agents/skills/shared/explainer-delivery.md:68` still reads *"It has a `--self-test` (**14 cases**)"*
against a measured 30/30. Noticing a defect in a shared doc and leaving it is how it stayed stale the
first time. This is a one-line fix that belongs in whatever PR carries the spec.

---

# Is this still the simple thing the user asked for?

Asked plainly, answered plainly. **The first screen is now right, and the document is not.**

**Measured growth:** v1 `eb3838e` = 234 lines · v2 `91a1ec0` = 324 · v3 `4897947` = **388**. §5 now
carries 5.0–5.7 plus 5.5a–5.5d — **twelve** numbered units where v1 had four.

**What the page contains,** counting §3 In and §5: what-needs-you, progress, activity, health,
work-flow, diagrams, backlog counts + dependency fold, recurring mistakes, the dated entry list, the
request box, the request-state list, a glossary, four links. Round 1 counted *"roughly eight blocks
before a single entry"* and judged the page would *"orient someone willing to spend five minutes, and
will not answer the sixty-second question."* v3 answered that with §5.0 — **the correct fix, and the
single best change in this revision.** But it also added §5.7 and removed nothing. The block count
went **up**.

**Two structural observations, offered as judgement rather than defect claims.**

1. **The page's answer to the user's rank-1 problem is the one part the spec says will not work.**
   §1 ranks continuity first. Continuity is delivered by entries. §6 line 255 says entries exist only
   if written and would be skipped when busy; §10's risk table says the mitigation is *"An alarm, not
   a cure — stated"*. Everything else on the page — progress, health, work-flow, backlog, recurring
   mistakes, diagrams — answers rank-2 and rank-3, and the graphics are where v3's growth went. The
   design is best-developed where the problem is smallest.
2. **The document has accumulated five prerequisites it does not own or order.** §5.5d (the page
   class, in `explainer-delivery.md`), §9 (closing the `PAGE_SKILLS` hole — *"its own change"*), §7a
   (the pre-publication licence audit — *"a required task"*), §11 q3 (the fold change), §2 (the shared
   doc's stale 14). Each deferral is individually honest and correctly reasoned. As a set they mean
   nobody can tell what must land before the dashboard can be built, and one of them (H4) makes the
   design non-compliant in the meantime. A short *"what must land first, in what order"* list would
   convert five honest deferrals into a plannable sequence.

**Recommendation.** §5.1 needs a source that is actually informative about where the work is — the
launch-milestone vocabulary is spent (`docs/roadmap-to-launch.md:33-35`), and the live state is in
`docs/backlog.md`, which §5.6 already reads through a parser that works. That one change would
dissolve B1 and B2 together, since it also removes the derivation that cannot be shared with
`gen-goals-page.py`.

---

# What I checked and found nothing wrong with

Recorded so round 3 does not redo it. §2's server inventory citations are all correct:
`explainer-serve.py:35-49` is the standing-pages docstring; `:671-698` is `do_POST`; port 7391;
`POST /questions` → `~/explainers/questions.md`. `brief-compose.py --self-test` → 30/30, matching §2.
`gen-backlog-page.py` → rc=0 and 55/55, matching §5.6. `docs/backlog.md` has 66 rows, matching §5.6.
`check-docs.py` → rc=0. `check-anchors.py` → *"10 registered, all claimed … floor 22 held"*.
`check-gate-falsifiability.py` → *"every unticked gate item names what would fail it"*.
§4a's reload-client citation (`:559-580`) is accurate. §5.1's three refutations of v2 are each exactly
right (headings at 49/180/265; `grep -c roadmap-to-launch scripts/gen-goals-page.py` → 0; no `◀`).
§5.5a's withdrawal of the gzip inference is correct and well argued. §12's two non-acceptances are
legitimate dispositions.

---

NOT CONVERGED

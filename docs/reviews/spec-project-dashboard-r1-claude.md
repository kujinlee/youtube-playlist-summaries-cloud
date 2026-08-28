# Adversarial review — `docs/superpowers/specs/2026-08-28-project-dashboard-design.md`, round 1 (Claude half)

**Reviewer:** Claude, independent half of the dual adversarial gate. The Codex half ran separately;
its output was not read, and `docs/reviews/spec-project-dashboard-r1-codex.md` was deliberately left
unopened.

**Subject:** v1 DRAFT, unreviewed, approved by the user from a verbal summary without reading it.

**Method.** Every load-bearing claim the spec makes about existing code was opened and checked.
Where a number was stated as measured, it was re-measured. `mermaid@11.17.2/dist/mermaid.min.js` was
downloaded and inspected rather than reasoned about.

**Counts:** 2 Blocking · 9 High · 7 Medium · 4 Low.

---

## What is correct, stated first so the rest is read fairly

These were checked and hold. They are not filler — several are the kind of claim that is usually wrong.

- **The Mermaid size figures are exact.** Downloaded `mermaid@11.17.2/dist/mermaid.min.js`:
  **3,572,661 bytes = 3.41 MiB** raw, **979,561 bytes = 0.93 MiB** gzipped. Both match §5.5's table.
- **The plugin comparators are right.** `du -sh ~/.claude/plugins/cache/claude-plugins-official/*/`
  → `superpowers` **4.0 M**, `remember` **10 M**.
- **The bundle is usable from a plain `<script>` tag.** It is an esbuild IIFE with **zero** dynamic
  `import(` calls, and its final line is `globalThis["mermaid"] = globalThis.__esbuild_esm_mermaid_nm["mermaid"].default;`.
  No code-splitting problem, which is the failure I expected to find and did not.
- **`gen-backlog-page.py:419` and `:477` say what the spec says they say.** Line 419: *"Vendoring
  mermaid would put ~1MB of library into a 419KB page"*. Lines 477-478: *"⚠ NOT RENDERED HERE —
  mermaid is not installed … its rendering is unverified"*. The live defect §5.5 claims to fix is real.
- **`PAGE_SKILLS` is quoted correctly.** `scripts/check-explainer-delivery.py:53` is exactly
  `["explain-diff", "brief", "explain-findings", "explain-topic"]`.
- **The anchor is registered and the ratchet is green.** `docs/anchors.md:39` carries
  `status-visibility` with the identical goal sentence; `python3 scripts/check-anchors.py` →
  *"anchors: 10 registered, all claimed … floor 22 held"*.
- **§2's inventory of the server is accurate** — port 7391 (`explainer-serve.py:90`), `~/explainers`
  only with post-resolution confinement (`:92`, `safe_path` `:106-120`), standing pages excluded from
  `/latest` (`:380-388`, self-test `:807`), `POST /questions` as the only POST route (`:671-672`),
  `/goals` derived from five sources (docstring `:24-29`; hook case list `regen-goals-page.sh:36-41`).
- **`docs/backlog.md` has exactly 66 numbered rows**, matching §5.6.

The spec is a careful document. The findings below are not a claim that it is sloppy; they are a
claim that several of its load-bearing sentences are about things the author did not open.

---

# BLOCKING

## B1 — The entries have nowhere to live, and the page that would hold them is regenerated in place

**Claim attacked.** §7: `gen-dashboard.py` *"gathers facts … Renders the frame and the graphics"*;
the skill *"writes the plain paragraph and the entry text; composes and delivers"*. §5.5: the
dashboard is *"a **live view**, regenerated in place like `/goals` and `/backlog-table`"*.
§3 In-4: *"A dated list of plain, one-sentence entries"*. §5.2: fourteen days of them.

**What I checked.** Every comparable surface in this repo names its source file explicitly:
`gen-goals-page.py:164` reads `docs/anchors.md`, `:169` globs `docs/adr/*.md`, `:180-193` globs
`docs/superpowers/{specs,plans}/*.md`; `regen-goals-page.sh:36-41` enumerates all five as a case
list. `gen-backlog-page.py` renders `docs/backlog.md`. I then searched the spec for any file, format,
or location for entries. **There is none.** Not in §3, §5.2, §6, §7, or §11.

**What is actually true.** The two halves of §7 are incompatible as written. If `gen-dashboard.py`
regenerates `dashboard.html` — which §5.5 requires, and which is how every other standing page in
this repo works — then the entries, which exist only as markup the skill composed into the previous
copy of that file, are destroyed on the next regeneration. If instead the page is never regenerated
without the skill, then §7's whole justification for splitting the script out (*"machines do not
forget; these must never be stale"*) collapses, because the facts only refresh when a human-driven
skill runs.

**It also breaks §6's own mitigation.** §6 mitigation 2 promises *"a day with commits but no written
entry shows a bar with nothing under it"*. For the script to render that, the script must be able to
enumerate which days have entries. It cannot: entries are the skill's output, held in the artifact
the script overwrites. The one mechanism offered against the spec's admitted weakest point cannot be
built from the architecture the spec specifies.

**Why Blocking rather than High.** This is not a gap to fill during implementation. It determines
what `gen-dashboard.py` is, what the skill hands it, and whether §5.2's navigation is possible at
all. A plan written from this spec would have to invent the answer, and inventing it is a design
decision — which is the definition of a spec that is not ready.

*(VERIFIED: the absence of any named store, and the source-naming convention every sibling follows.
INFERRED: that a durable append-only store — e.g. `docs/dashboard-entries.md`, parsed by the script
and appended to by the skill — is the shape that resolves it. I am not asked to fix it and do not.)*

## B2 — §5.1's data source contains neither the headings nor the markers it is said to contain, and is not the source `gen-goals-page.py` reads

**Claim attacked.** §5.1, in full: *"Derived from the `### M<n>` headings and their ✅ / ◀ / ⛔
markers in `docs/roadmap-to-launch.md` — the same source `gen-goals-page.py` already reads."*

**What I checked.**

```
$ grep -cE "^#{1,6}\s+M[0-9]" docs/roadmap-to-launch.md
3
$ grep -nE "^#{1,6}\s+M[0-9]" docs/roadmap-to-launch.md
49:## M1 — Deploy (the app goes live) 🚀
180:## M2 — Sync (unify local + cloud, Stage 3) 🔗
265:## M3 — Acceptance ✅ **CLOSED 2026-08-13**
```

**Three separate falsehoods in one sentence.**

1. **There are no `### M<n>` headings in that file.** All three are `##`. The regex that would read
   them (`gen-goals-page.py:65`, `^#{2,4}\s+(M\d+)`) happens to tolerate `##`, so this one is
   survivable — but the spec is describing a file it did not open.
2. **`gen-goals-page.py` never reads `docs/roadmap-to-launch.md`.** `collect()` (`:160-193`) opens
   `docs/anchors.md`, `docs/adr/*.md`, and globs `SUBDIRS = ("superpowers/specs", "superpowers/plans")`
   (`:56`). The roadmap is not in that set, and `regen-goals-page.sh:36-41` — the hook whose comment
   calls its own case list *"the checklist"* — does not watch it either. The real `### M<n>` spine is
   `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md`, which carries M1–M7 and is
   the **schema-promotion** roadmap, not the launch roadmap. §5.1 has silently merged two different
   milestone vocabularies.
3. **The "current one marked" state cannot be derived from the named file at all.** `MILESTONE_STATES`
   (`gen-goals-page.py:71`) reads `◀` as *next*. **There is no `◀` on any `## M` heading in
   `docs/roadmap-to-launch.md`** — M1 carries 🚀, M2 carries 🔗, M3 carries ✅. Rendered from the
   stated source, §5.1's graphic would show one of three milestones done, two in an unknown state,
   and **no current marker at all**. The single graphic the user is meant to read first — *"how far
   along is the whole thing"* — has no working source.

**Why Blocking.** §5.1 is graphic number one on a page whose entire purpose is orientation, and its
derivation is not merely imprecise but wrong about which file, which heading level, and which markers
exist. This is the memory `true-about-the-name-silent-about-the-layer` in its exact form: correct
that milestone state is derived from headings and markers, silent about the layer where those
headings actually live.

---

# HIGH

## H1 — §9's flagship mechanical check is stated backwards and can never fail

**Claim attacked.** §9's gate table: *"`check-explainer-delivery.py` | Fails when `dashboard` is
absent from `PAGE_SKILLS`"*.

**What I checked.** `scripts/check-explainer-delivery.py:53` hardcodes `PAGE_SKILLS`. `audit()` at
`:73` is `for name in page_skills:` — a name **not** in that list is never looked at. The script's own
docstring says so at `:35`: *"a skill claims to produce a page but is not in PAGE_SKILLS (add it, or
it escapes the check)"*. I ran it: `python3 scripts/check-explainer-delivery.py --self-test` → 8/8,
and none of the eight cases is "an unlisted page skill is caught", because it cannot be.

**What is actually true.** The check passes cheerfully with `dashboard` absent. The stated failure
condition is the one observation the instrument is structurally incapable of making. This is the
shape `scripts/check-gate-falsifiability.py` was written for — its docstring (`:5-9`) is the B5 story,
*"That script is static … so it CANNOT observe a deployment. The item could only ever pass."*

**The spec contradicts itself about this.** §7 gets it right — *"An unlisted page skill escapes the
check entirely"* — and §9 then lists the escape as the gate. §9's row is the more dangerous of the
two, because a table headed "Mechanical checks" is what a later reader trusts.

## H2 — §8's request-state derivation is keyword matching, on a stream with no key to match on, and the spec calls it honesty

**Claim attacked.** §8: *"Request state is derived by comparing `questions.md` entries against pages
that exist in `~/explainers`"*, offered as what *"makes the button honest"*.

**What I checked.** `explainer-serve.py:487` writes each entry as
`\n---\n\n## {now} — {doc}\n\n{text}\n`. `do_POST` (`:671-698`) accepts a JSON object and reads
exactly two keys, `doc` and `text` (`question_text`, `:451`; the 400 body at `:692` names them). There
is **no request id, no kind field, no status field, and no reply channel**. I read
`~/explainers/questions.md` (391 lines): it is one undifferentiated append stream shared by every
page ever served — dashboard requests will interleave with every ask-tray question from every
explainer.

**What is actually true.** Determining "done" means matching free-form request text against filenames
of the form `YYYY-MM-DD-<kind>-<slug>.html`. That is keyword matching — and `gen-goals-page.py`'s
docstring refuses it by name, in this repo, for this reason (`:36-40`): *"Counting them means keyword
matching, which is the method that failed and caused all of this. A number that is a lower bound of
unknowable size is worse than an empty cell."*

The consequence is worse than an empty cell here. A request that matched nothing shows `waiting`
forever after it was answered; a request that matched the wrong page shows `done` when nothing
happened. §8 is written specifically to prevent *"a button that looks like it worked while nothing
happened"* — and the mechanism it proposes reintroduces that failure through the status field
instead of the button. The section's own citation, `a-checklist-item-can-be-an-unfalsifiable-guard`,
lands on itself.

*(INFERRED, offered as the shape of a fix rather than a fix: the four buttons post structured text
the page itself controls, so a request carries a token the produced page's filename also carries.
That is a design decision and belongs to the author.)*

## H3 — Live reload discards every open fold, and folding is the entire design

**Claim attacked.** §4: *"Every piece of detail is folded. Nothing is deleted."* §5.5: the page is
*"regenerated in place like `/goals` and `/backlog-table`"*, and §2 records that standing pages
*"live-reload an open tab"*.

**What I checked.** The injected reload client in `explainer-serve.py`: `:560-563` saves and restores
**only** `window.scrollY` via `sessionStorage`; `busyTyping()` (`:565-571`) suppresses a reload only
while `#qbox` holds a draft or has focus. `grep -n "details" scripts/explainer-serve.py` returns
nothing relevant — the reload path has no concept of `<details>` state.

**What is actually true.** Every automatic reload collapses every fold the reader had opened. This is
observable today: `grep -c "<details" ~/explainers/backlog-table.html` → **119**. On the backlog page
it is an annoyance. On the dashboard it is the defeat of the design, because §4 makes "open the two
folds I care about" the reader's *only* action, and §5.5 makes the page one that rewrites itself
under them. The most likely moment for a regeneration is right after a commit — i.e. right after the
session did the work the reader came to read about.

The reload client's own comment (`:585-590`) records that the author's previous test of this
mechanism was invalid because it drove a foreground tab. The same trap is open here: a hand test of
the dashboard will open a fold, look at it, and not sit there for the poll interval.

## H4 — The window is 14 days; the absence the page exists for is longer, and there is no way to look further back

**Claim attacked.** §5.2 fixes the activity chart at 14 days and makes it *"also the navigation"*.
§11 open question 1 calls 14 *"a starting guess"*. §9's falsifier is *"after two days away"*.

**What is actually true.** §1's rank-1 failure, in the user's frame, is *"Cannot hold the thread
across a day or a week"*, and the registered goal (`docs/anchors.md:39`) is about *"A person who was
away"*. Two days is the easy case. A three-week absence — the case where the user most needs this —
falls **entirely outside** the chart, and because there is no entry store (B1) there is nothing to
page back through. The spec specifies no older-than-window behaviour at all: not a second view, not
a "before this" link, not a summary of the elided period.

Measured, so this is not hypothetical: `git log --format=%ad --date=short | sort | uniq -c` over the
last 400 commits shows real gaps — zero commits on 2026-08-15, 16, 20, 23 and 26. A 14-day chart
opened after a fortnight away is roughly half empty bars and half unreachable history.

§9's falsifier being written at "two days" is the tell: the success criterion was set to the window
the design already covers.

## H5 — There is no specified path from "bundled in the plugin" to "the browser can load it"

**Claim attacked.** §5.5: *"Mermaid is bundled with the distributed plugin and served from
`127.0.0.1`."* §7a: *"Users will not install extras | Mermaid ships **inside** the plugin"*.

**What I checked.** `explainer-serve.py:92` — `ROOT = pathlib.Path.home() / "explainers"`. `safe_path`
(`:106-120`) resolves every request and re-checks `candidate.relative_to(root.resolve())`, so nothing
outside `~/explainers` is reachable. `.js` **is** servable (`SERVABLE`, `:96`) and gets
`text/javascript` (`:664`) — so the mechanism exists. But a marketplace plugin installs under
`~/.claude/plugins/cache/<marketplace>/<plugin>/` (verified: that is where `superpowers` and
`remember` live), which the server structurally cannot serve. The only second root is
`EXPLAINER_DOCS_ROOT` → `/src/<path>` (`:98-103`), which is read-only, env-gated, off by default, and
mentioned nowhere in the spec.

**What is actually true.** Somebody must copy 3.4 MB into `~/explainers` at install time, on upgrade,
and after any manual cleanup of that directory — and `explainer-delivery.md:28` establishes that
`~/explainers` is deliberately **outside the repository**, unversioned, with nothing tracking its
contents. The spec never names who does this copy, when, or what happens when the plugin's bundled
version and the copied one diverge. §7a's *"Every source path is a parameter with a documented
default"* does not cover it, because the missing thing is not a path parameter but an install step.

This matters most because §5.5's "no fallback" argument runs *"No user installs anything, so no user
lacks it"*. The premise is false as specified: every user must have something installed into
`~/explainers`, by a step that does not exist.

## H6 — §5.5's "no fallback renderer" is over-reached, and its own retained requirement is the thing it just rejected

**Claim attacked.** §5.5: *"there is no fallback renderer — nothing to build, nothing to test,
nothing to rot"*, and the rejection of an SVG path because *"a fallback nobody exercises is not a
fallback"*.

**Judged on the merits, as asked.** The **bundling** decision is sound and I would keep it: the size
is real, the comparators are real, the licence permits redistribution, and the first version's error
(checking "is a renderer installed?" instead of "can we ship one?") is correctly diagnosed. The
**"no fallback"** conclusion does not follow from it, for three reasons.

**First, the argument's middle step is false.** "Installed" ≠ "loads in this browser at this moment".
Verified failure modes the spec does not consider:
- **Truncation.** `globalThis["mermaid"]` is assigned on the **final line** of the 3.5 MB file
  (I read the tail). An interrupted copy, a full disk, or a proxy that truncates yields a file that
  serves 200 and leaves `mermaid` undefined.
- **Not reachable by the server at all** — H5, which is the *default* state, not an edge case.
- **`file://`.** `explainer-delivery.md:94-96` and `:141` promise, twice, that a saved copy still
  reads fine and loses only Send. Under §5.5 the dashboard silently breaks that promise for its
  diagrams, and §3's "Out" list does not retire it.
- **CSP / managed-browser policy / air-gapped machines** — real for the marketplace audience §7a
  invokes, unaddressed.

*(One case from the prompt I could NOT verify and will not assert: that a browser refuses a 3.4 MB
local script. I found no evidence for it.)*

**Second, "a fallback nobody exercises is not a fallback" argues against an unexercised path, not
against a fallback.** There is an exercised option the spec does not consider: `dependency_svg`
(`gen-backlog-page.py:414`) already renders this exact graph as inline SVG and is exercised on every
backlog regeneration. Making SVG the renderer for the one diagram that has a working SVG renderer,
and Mermaid the renderer where none exists, exercises both on every build. §3 "Out" rules out
*converting the backlog page* — a different decision from choosing the dashboard's renderer for the
same graph. The spec treats these as one thing.

**Third, and this is what tips it from judgement into rationalisation:** the requirement §5.5 *does*
retain — *"If `mermaid.min.js` is absent or damaged, the page must say so in plain words, in place of
the diagram"* — is itself an unexercised path with **no falsifier, no owner, and no row in §9's check
table**. "Damaged" is left undefined. So the section rejects an untested safety net and then
specifies an untested safety net one severity band down, and does not notice. If the rot argument is
good, it applies here too; if it does not apply here, it did not defeat the SVG option either.

## H7 — §5.3's health lamps have two states, and the state this project cares most about is not one of them

**Claim attacked.** §5.3: *"One small block per automated check, green or red … Derived by **running
the checks**."*

**What I checked.** `CLAUDE.md`, the user's own standing rule: *"**'Cannot run' is a FAILURE, never a
pass.** If a check cannot reach what it measures — no credentials, no network, a tool missing, a
parse that found nothing — it must fail loudly and say *treat this as NOT RUN*."*
`docs/dev-process.md` records that `test:integration`, `test:e2e` and **all thirteen schema gates**
need a live stack and are **not in CI**; `scripts/check-schema-gates.sh` is the one entry point and
it needs a live Postgres.

**What is actually true, in two parts.**

- **The lamp has no CANNOT-RUN state.** Green/red/amber-for-you cannot express "Docker was not
  running, so this gate did not execute". Rendered as red, it is indistinguishable from a real
  failure and will be dismissed; rendered as green, it is the fail-open this repo has measured
  repeatedly (the memory `a-hang-is-not-a-diagnosis`). A dashboard built to give a non-technical
  reader a trustworthy at-a-glance signal is the *worst* place to lose that distinction.
- **"Derived by running the checks" is unspecified and probably infeasible as a page regeneration.**
  If regeneration runs the gate suite, the page cannot be produced by a hook on a file write — the
  schema gates alone need a live database. If it runs only the cheap subset, then *"one small block
  per automated check"* is false and the page shows a filtered view of health while looking
  comprehensive. The spec does not say which, and it names no hook or trigger at all, where every
  comparable page has one (`regen-goals-page.sh`, `regen-backlog-page.sh`).

## H8 — Nothing on the page surfaces "what needs them", which is a third of the registered goal

**Claim attacked.** The spec's own header and `docs/anchors.md:39`: *"A person who was away can see
the current state, what changed, **and what needs them**"*.

**What I checked.** Walking §3 and §5 for the mechanism that answers the third clause: §5.3 has *one*
amber lamp for "waiting on you"; §5.2 colours a **day** orange if it *"carries at least one entry
marked needs you"*. That is the complete inventory. There is no list of open decisions, no count, no
roll-up, and no ordering of the entry list by whether it needs the reader.

**What is actually true.** To find what needs them, the user must notice an orange bar, click it,
read the title lines under it, and repeat per orange day. For the three-week case (H4) the orange
days may be off the chart entirely. Meanwhile §5.1 (progress), §5.4 (how work moves) and §5.6
(backlog) each get a dedicated graphic for things the user did not rank first.

This is the sharpest version of *does it solve the human problem*: the goal sentence has three
clauses, and the design has a graphic for two of them. §5.3's single amber lamp is a status light,
not an answer to *"what is waiting on me?"*.

## H9 — Deferring the recurring-mistakes section is the wrong item to cut, and the reason given does not survive contact with §6

**Claim attacked.** §3 Out: *"A recurring-mistakes section. *(Wanted — the user said 'common mistakes
etc.' — but deferred to v2 so v1 ships.)*"*

**What is actually true.** Of everything the user asked for, this is the item with the most existing
raw material and the **lowest ongoing maintenance cost**. The material is already mined: the memory
index carries roughly two dozen entries under an explicit heading *"How things go wrong here"*, and
`docs/portable-practices.md` exists as the distilled, project-independent form (backlog task #55 is
literally *"Mine the 54 memories + 623 reviews into docs/portable-practices.md"*).

More importantly it is the **only requested section that does not rot**. §6 names the spec's own
weakest point — entries exist only if the assistant writes them, and it will skip them when busy. A
recurring-mistakes section is written once and re-read; it is the one part of the page that is still
useful on a day nobody wrote an entry, and it is exactly the content that makes the page worth
opening when nothing changed. Deferring the durable, low-maintenance item in order to ship the
fragile, high-maintenance ones inverts the risk the spec identified two sections earlier.

"So v1 ships" is not a reason on its own — no other section was cut for scope, and §5 grew by a whole
subsection (§5.6) on the same day at user request.

---

# MEDIUM

## M1 — The licence claim describes the npm package, not the artifact being redistributed

**Claim attacked.** §5.5: *"License: **MIT** — redistribution permitted with attribution"*.
§7a: *"MIT attribution | Mermaid's licence text ships with the bundled file"* — singular.

**What I checked.** `npm view mermaid license` → `MIT`, which reproduces the spec's check. Then I
looked at what is actually inside the file being shipped. The trailing legal-comment block of
`mermaid.min.js` carries at minimum:

```
Copyright (c) 2013-2014 Ralf S. Engelschall (http://engelschall.com)
Copyright Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors
Copyright OpenJS Foundation and other contributors <https://openjsf.org/>
Copyright Gaetan Renaudeau. MIT License
copyright Koen Bok. MIT License
... "Apache license 2.0 and Mozilla Public License 2.0"
... "MIT license <https://lodash.com/license>"
```

**What is actually true.** The bundle vendors third-party code under at least MIT, Apache-2.0 and
**MPL-2.0**. Shipping "Mermaid's licence text" alone under-attributes, and MPL-2.0 carries
per-file source-availability obligations that MIT does not. For a plugin the user intends to publish
to a marketplace, that is a distribution obligation, not a nicety.

Note the shape, because it is one this project has a name for: the check performed was on the
package's *declared* licence; the claim made was about the *artifact's contents*. Same layer error as
`true-about-the-name-silent-about-the-layer`, in a section that was itself written to correct a layer
error.

**Also missing from §7a's distribution table, and cheap to state:** a pinned version (the spec says
"v11.17.2" in a measurement row, never as a pin), an integrity hash, and an update story. §5.5 flags
itself for "ADR triage"; supply chain belongs in that ADR.

## M2 — §7 attributes a rule to the wrong file, and states it too strongly

**Claim attacked.** §7: *"**An unlisted page skill escapes the check entirely** — that is written in
`explainer-delivery.md` and is a live trap here."*

**What I checked.** I read `.agents/skills/shared/explainer-delivery.md` in full (240 lines). It
**never mentions `PAGE_SKILLS`**, and never discusses escaping the check. The sentence is in
`check-explainer-delivery.py:35`, and a different version of the argument is in
`.claude/hooks/regen-goals-page.sh:7-10`.

**And "entirely" is false.** The restatement half of the check (`:83-96`) globs `*/SKILL.md` across
**every** skill, listed or not, and the self-test proves it: `:148`, *"restatement in another skill
caught"*. An unlisted page skill escapes the **citation** requirement only. The spec's §7 is the
place a later implementer will look to understand the trap, and it will send them to a file that does
not contain it.

## M3 — §5.6's supporting precedent is not in the file it cites

**Claim attacked.** §5.6: *"this project has already measured the cost of a hand-written count
drifting (§ the 110-vs-117 correction in `docs/backlog.md` row 65, fixed the same day this spec was
written)"*.

**What I checked.**

```
$ grep -c "117" docs/backlog.md
0
$ git log --oneline -1 -- docs/backlog.md
201d2d8  (2026-08-27)  fix(gates): backlog 65 — the live-schema gate was blind to ADDED objects (#160)
```

**What is actually true.** "117" does not occur anywhere in `docs/backlog.md`. The only `110` is in
row 65's *"Self-test 67 → **110** cases"* — a self-test case count, not a drifting item count. And
the file's most recent commit is dated **2026-08-27**, not the day the spec was written (2026-08-28).

**The conclusion §5.6 draws is right and I would keep it** — deriving counts from
`gen-backlog-page.py`'s existing parser rather than re-counting is correct, and `66` is the true row
count. The evidence offered for it does not exist as described, which is the precise failure mode of
the memory `never-write-a-cost-table-from-memory`, inside a paragraph arguing against exactly that.

## M4 — The reversal's central re-measurement includes an inference presented as a measurement

**Claim attacked.** §5.5, in a table headed **"Measured 2026-08-28"**: *"The '~1 MB' in
`gen-backlog-page.py:419` | the **gzipped** number — 3.4× under the file that would actually ship"*.

**What I checked.** Line 419-420 reads, in full: *"Vendoring mermaid would put ~1MB of library into a
419KB page to draw seven nodes."* Nothing there says gzipped, and the sentence is about **inlining
into the page**, where the raw size is the figure that applies — so the more natural reading is that
the prior author's number was simply wrong, not that it was a different metric.

**What is actually true.** The measured gzip is 979,561 bytes ≈ 0.93 MB, so the spec's reading is
*plausible*. But it is an attribution of intent to a past author, printed in a table of measurements,
with no evidence. The two rows around it are genuine measurements and are exactly right. This row is
a guess wearing their clothes. The distinction matters because the §5.5 reversal's rhetorical force
comes from "the old number was wrong for an instructive reason" — and the instructive reason is
unverified.

## M5 — §5.5's scope bound amends a shared rule from inside its own spec

**Claim attacked.** §5.5: *"This holds because a dashboard is a **live view** … so
`explainer-delivery.md` §2's 'opens on its own in five years' requirement is not in play."*

**What I checked.** `explainer-delivery.md:33-36` states the rule with no qualifier and no
live-view/archival distinction: *"**One self-contained HTML file.** Inline CSS and JS. **No external
fonts, CDNs, images, or network access of any kind** — it must render offline, and in five years."*
The file *does* draw a distinction, at §4 (`:94-96`) — but in the opposite direction: Send and live
reload are **progressive enhancements** that may degrade on `file://`, explicitly *"never a
dependency"*, because *"the artifact must still open untouched in five years"*.

**What is actually true.** The spec is carving an exemption out of a rule that four other skills obey
(`explain-diff`, `brief`, `explain-findings`, `explain-topic` — table at `explainer-delivery.md:7-12`),
and it is doing it in a subsection of its own design doc rather than in the shared file or an ADR.
The distinction it draws may well be the right one — but the shared file is the single description
this project has a *script* to protect, and a rule that has been exempted somewhere else is a rule
that has quietly become two. §5.5 flags "ADR triage" parenthetically; on this point the ADR is a
prerequisite, not a follow-up.

## M6 — The one retained Mermaid requirement is undefined and ungated

**Claim attacked.** §5.5: *"If `mermaid.min.js` is absent or damaged, the page must say so **in plain
words, in place of the diagram**."*

**What is actually true.** "Damaged" is not defined, and the detectable symptom differs per cause: a
truncated bundle leaves `mermaid` undefined (assignment is on the last line — verified); a CSP or MIME
rejection leaves the same symptom with a different console error; a bundle that loads but throws
during `render()` leaves an empty container, which §5.5 correctly identifies as indistinguishable
from a diagram of nothing. §9's check table has **no row** for this requirement. Per the user's own
gate rule, an item with no named failing observation is a decision wearing a checkbox.

## M7 — The page cannot say whether anyone is listening, at the moment that is most likely to matter

**Claim attacked.** §8: *"If a session is live with the `Monitor` armed, I see it within seconds. If
nothing is running, it waits until I next read the file."*

**What is actually true.** The honesty here is real and I credit it. But consider when the page is
used: the user opens it **because they were away**, which is very likely a time when no session is
running — so the button's most probable state at the exact moment of pressing is "nobody is
listening", and the page shows the same affordance either way. The information is already derivable
and already precedented: `explainer-delivery.md:144` describes the tray's `● live` / `○ local file`
mode chip, and `explainer-serve.py` maintains a pidfile (`:93`, `pid_alive` `:497`). Showing "a
session is running / is not" is a few lines and turns "waiting" from a status into an expectation.

---

# LOW

## L1 — A self-test count in §2 is stale by more than half

§2: *"`scripts/brief-compose.py` | lifts the ask-tray verbatim; **14** self-test cases"*.
Measured: `python3 scripts/brief-compose.py --self-test` → **30/30 passed**. The 14 is copied from
`explainer-delivery.md:68`, which is itself stale — so the error is inherited, not invented, and the
shared file should be corrected too. (`check-explainer-delivery.py --self-test` → 8/8, matching its
docstring at `:37`.)

## L2 — A "current page sizes" row is wrong, and none of the four records a build

§5.5: *"brief 67 KB · goals 71 KB · backlog-table 477 KB"*. Measured:
`backlog-table.html` = 488,855 B = **477 KiB** ✅; newest brief = 69,049 B = **67 KiB** ✅;
`goals.html` = 81,525 B = **79.6 KiB**, not 71. `goals.html` is regenerated by a hook on any of five
source patterns, so this number moves without anyone touching it — which is exactly why `CLAUDE.md`
requires recording *which build* a manual measurement was taken against. None of the four does.

## L3 — Four citations of `explainer-delivery.md` with no path

§4, §9 (twice) and §5.5 cite `explainer-delivery.md` by bare filename. It lives at
`.agents/skills/shared/explainer-delivery.md`; `.claude/skills/shared` is a symlink to it (verified by
`ls -la .claude/skills/`). §7a's own principle — *"Users will not read this spec | failure messages
must be self-explaining"* — applies to the spec's own references, since §7a also says this document
must survive being read by people outside this repo.

## L4 — Internal count mismatch: four charts or five

§3 In-3 says *"Five graphics (§5)"*; §3 Out says *"Any chart beyond the **four** in §5"*; §5 has five
numbered subsections (5.1–5.4 plus 5.6, with 5.5 being the renderer decision rather than a graphic).
Since §3 Out is declared *"binding for v1"* (§10), a scope gate that cannot count its own subjects is
worth one edit.

---

# Cross-cutting observations

These are judgements, not defect claims, and are marked as such.

**On whether it solves the stated problem.** The diagnosis in §1 is right and unusually well
evidenced — chat is transient, and a durable re-readable surface is the correct response. But the
page is specified by what it **contains** and never by what its **first screen shows**. Counting §3:
five graphics, a backlog section, a dated entry list, a request box, a request-state list, a glossary
and four links — roughly eight blocks before a single entry. For a reader with sixty seconds, tired,
possibly on a phone, nothing in the spec says what they see first or what is deliberately given the
top of the page. `gen-goals-page.py` solved the analogous problem by giving *absence* a fixed slot
(docstring `:42`); the dashboard has no equivalent for *"the one thing that matters today"*. Combined
with H8, my honest read is: it will orient someone who arrives willing to spend five minutes, and
will not answer the sixty-second question.

**On reconstructing a week.** §5.2 makes the chart the navigation, and §5.2 argues that this is what
makes it earn its space. That argument holds for *finding* a day. It does not hold for *reconstructing
a week*, which is then seven clicks plus a fold each — and the prompt's standard for failure is
precisely that. There is no specified "everything since <date>" view.

**On the author's own habits.** Two places where the design accommodates rather than corrects.
(a) §4's Fold 2 — *"technical: commit SHAs, file paths, commands, exact numbers"* — is a sanctioned
home for the exact register the user cannot read. The spec defends Fold 1's plainness well and at
length, but there is no cap on Fold 2, no requirement that Fold 1 be complete without it, and no
check that Fold 1 is plain; §10 makes jargon in Fold 1 a defect *the user reports*, which puts
detection on the person who cannot parse jargon in the first place. (b) §1 closes by moving failure
#3 out of scope: *"#3 is fixed by a glossary on the page plus a change in how I write, which is
independent of this spec."* The user's words on #3 were *"Just don't make the prose a mix of
unfamiliar terms"* — a glossary is, structurally, what makes it acceptable to keep doing so. Neither
observation is disqualifying; both are worth the author's attention, because this spec was written by
the party whose output is the problem.

**On duplication.** §2's *"nothing here is being rebuilt"* holds for the server, the standing-page
mechanism, the questions channel and the tray — I checked each. But `gen-goals-page.py`'s own
docstring calls its page *"a dashboard"* (`:43`), and §5.1's milestone track, §5.4's process diagram
and §5.6's backlog counts are all views over sources `/goals` and `/backlog-table` already read. The
spec's defence is that the dashboard *links* to both — true, but a link is not what §5.1 and §5.6
specify; they specify rendering the same data again, in a third place, from a fourth script. Given
B2's finding that §5.1's derivation is not the one `gen-goals-page.py` uses, the two pages will
compute milestone state from **different files**. That is `two-mechanisms-for-one-concern` arriving
by the front door, in a spec that cites that memory twice.

**On day 30, and on the process rather than the page.** §6 is admirably honest that entries exist only
if written. Beyond B1's structural problem, three process cases are unaddressed: a session that ends
**mid-work** (context limit, crash, `/compact`) never reaches the compose step, and interruption is
more common in this repo than busyness — there is a whole memory on the compaction protocol; **two
sessions in one day** share one bar and, per B1, the second overwrites the first's page; and **three
weeks away** falls outside the window entirely (H4). §6's mitigation makes a missing entry *legible*
rather than preventing it, which the spec says plainly and which I accept as a reasonable trade — but
it only works if the script can see the entry store, which it cannot (B1).

---

# What I checked and found nothing wrong with

Recorded so a later round does not redo it: `explainer-serve.py`'s confinement and MIME handling;
`is_standing` / `latest_target` and their self-test cases (`:804-816`); the `POST /questions` fail-loud
path (`question_text`, `:451-463`); `check-anchors.py` (green, floor 22 held);
`check-explainer-delivery.py --self-test` (8/8); the mermaid bundle's global export and absence of
dynamic imports; the `superpowers` / `remember` size comparators; the `gen-backlog-page.py:419` and
`:477` line citations; the 66-row backlog count.

---

NOT CONVERGED

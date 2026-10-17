<!-- canon: marketplace-inventory -->
# Marketplace inventory — what this harness can ship to a stranger, and what cannot

> **Anchor:** `harness-ships-elsewhere` — **ADR:** none
> **Goal:** The harness this project built can be installed and used by someone who has never seen this repository.

**Status: SPEC, awaiting review. Nothing here is implemented.** This document is the Phase 1 artifact
for a milestone whose deliverable is a *decision*, not a published plugin.

⭐ **It is also the claiming document `docs/backlog.md` row 290 asked for.** That row recorded that
registering the comprehensibility suite in `docs/anchors.md` cannot be a one-line edit, because
`check-anchors.py` **R4** refuses a registry name no document claims, and named three candidate
claimants. This spec is candidate (a), and it claims `harness-ships-elsewhere` — which is broader
than the suite alone, because the owner asked for all three efforts to be inventoried.

---

## 1. Why this exists

The owner, 2026-10-15, in their words:

> *"I have been focusing on development process speed enhancement and comprehensibility for me about
> what you are doing… Now is the time to evaluate the efforts. Goal is to publish the features in
> marketplace. Not all of them may not be suitable for publish but let's take inventory and establish
> a milestone."*

Three efforts have been running in parallel. Each was justified on its own terms; none has ever been
asked *"could someone else use this?"* against a stated bar. That question is Deliverable 2's whole
content — **a battle-tested harness and reproducible framework for NEW projects** — and it has been
answered only informally, for one file, once.

**This milestone answers it for every component, with evidence, and records what the answer costs.**

---

## 2. Decisions of record — settled 2026-10-15 by selection card. Do not re-open.

| # | Decision | What it rules out |
|---|---|---|
| **D1** | **Audience: public strangers, full support bar.** Works in any repo, documented for a newcomer, failure modes handled without the author | Rules out "good enough for my next project". Coupling becomes a **release blocker**, not a tidiness note |
| **D2** | **Decomposition: one evaluation spec across all three efforts, then a spec per publishable unit** | Rules out going straight at the comprehensibility suite and deferring the other two with a shallow verdict |
| **D3** | **Route: a self-published marketplace repo**, installed with `/plugin marketplace add <repo>` | Rules out aiming at `claude-plugins-official`, whose acceptance gate would make "done" undefinable. Official submission may become a *later, separate* milestone |
| **D4** | **Method: a mechanical scan across all components, plus one real install experiment** on the comprehensibility suite (effort 3), where the experiment calibrates the scan | Rules out verdicts resting on reading the code and judging it |

**Why D3 is safe to commit to:** the route is proven on this machine, not theorised —
`~/.claude/plugins/marketplaces/` holds `omc`, a third-party self-published marketplace, alongside
the official one. A marketplace is a git repo carrying `.claude-plugin/marketplace.json`.

⚠ **WHAT THAT PROVES, AND WHAT IT DOES NOT (r1 CLAUDE M5, r1 CODEX 10).** It proves the *route*
exists and that a third party can travel it. It says nothing about whether **this** suite can be
packaged onto it — someone else's marketplace is evidence about the mechanism, not about our
artifact. ⛔ **So packaging feasibility is an ASSUMPTION, not a finding**, and it is named in §9 as
the assumption whose failure invalidates D4. §7 item 0 discharges it before any scanning starts.

**Why D4 matters more than it looks.** This repository has measured that *review is the wrong
instrument for a surface*: six review rounds produced roughly seven edge cases, where one corpus run
over 5,287 inputs produced 456 fires and surfaced two real defects. ⚠ **Those are unlike units — edge
cases against inputs-and-fires — and the comparison is offered as an order-of-magnitude contrast, not
a ratio** (r1 CLAUDE M4; the first wording read as 7-versus-5,287 and invited a false 750x).
*"Can a stranger use this?"* is a surface question over **at least 24 components** (17 + 3 + 4 — the
counting rule, the per-effort enumeration and the mapping step that makes 24 a **lower bound rather
than a total** are all in §3). Judgement alone will miss things, and the misses are precisely the ones
a stranger meets first.

---

## 3. Scope — the components, derived from disk rather than recalled

⚠ **Derived 2026-10-15 by enumeration, membership corrected 2026-10-16 (round 1).** The counts
below are a dated measurement, not a live number.

⛔ **THE COUNTING RULE, stated once because round 1 found the addends unobtainable from the prose
(CLAUDE M1, CODEX 1).** **One component = one shippable unit**: a script, a skill, a shared contract,
a hook, or one named data corpus. A mutation manifest is part of the unit it tests and is not counted
separately. An unmerged branch is work in progress, not a shippable unit, and is **not** counted.

⛔ **AND THE RULE IS NOT ENOUGH ON ITS OWN — ROUND 2 FOUND IT NAMES ONE WORD FOR TWO THINGS
(r2 CODEX 5, High).** §5 declares a shipping set *per publishable unit*, while verdicts are
*per component*, and nothing said how supporting files attach. Two layers, stated separately:

| Layer | What it is | What it gets |
|---|---|---|
| **evaluation component** | the unit a verdict is recorded against | a verdict + an evidence grade (§4b) |
| **installable package** | the unit a stranger installs, which may contain several components | a shipping-set declaration (§5, §7 item 2) |

⛔ **EVERY SUPPORTING ARTIFACT MAPS TO A COMPONENT, TO A PACKAGE, OR TO A WRITTEN EXCLUSION.** Round
2 found real omissions that the counting rule permitted because it had no attachment rule: **the four
regen hooks are components while the generators they invoke are not** —
`scripts/gen-backlog-page.py` (**3,390 lines**) and `scripts/gen-features-page.py` (**711 lines**),
both verified as invoked by those hooks. Recall's hook likewise needs the plan-transition mechanism
and its hook registration, neither inventoried nor excluded.

⚠ **The derivation order is therefore: map first, then count.** Round 2's own verdict on the
arithmetic is the point — *"explicitly enumerating the named rows reproduces 17, 3, 4 and 24, but
that proves the arithmetic, not exhaustive membership."* **The total is not evidence of completeness**,
and this spec has now twice reached a reproducing total over an incomplete set.

⚠ Round 2 also ruled on two candidates that do *not* need their own component: the recall prompt is
embedded in `recall-llm.py`, and its cache is generated state. Fixtures and callers still need an
explicit disposition.

Applying the rule to the rows as named: **17 + 3 + 4 = 24.** ⚠ Pending the mapping above, treat 24
as a **lower bound**, not a derived total.

- **Effort (3) = 17** — 4 skills + 3 shared contracts + 6 Python files + 4 regen hooks.
- **Effort (2) = 3** — the sharded `mutation-sweep` job, `scripts/check-plan-code.py`, and the
  velocity document set (counted as one corpus).
- **Effort (1) = 4** — `scripts/recall-llm.py`, `scripts/check-surface-recall.py`,
  `.claude/hooks/surface-recall.sh`, and the memory corpus.

⚠ **THE ARITHMETIC IS UNCHANGED AT 24 AND THE MEMBERSHIP IS NOT — and after round 2, 24 is a floor
rather than a total.** Round 1 found effort (1)'s list was counting two unmerged branches and
omitting the matcher that actually ships (see Effort (1) below), so a figure that reproduced was
standing over a wrong set. Round 2 then found whole artifacts the counting rule never assigned at
all. **Twice now this spec has reached a reproducing total over an incomplete set** — which is this
repository's most-measured failure shape, reached here by arithmetic that happened to agree. ⛔ So the
number is not evidence of completeness, and §3's mapping step is what would make it one.

### Effort (3) — comprehensibility

| Component | Lines |
|---|---|
| `explain-diff` / `brief` / `explain-findings` / `explain-topic` (SKILL.md) | 158 / 195 / 156 / 95 |
| `.agents/skills/shared/` — `explainer-delivery.md`, `corpus-search.md`, `handoff-path.md` | **363 / 73 / 211** at `a4f6d4b5` (⟳ r5 CLAUDE H4: a parenthetical here read **660 at `HEAD`** — wrong by 3 at the commit that typed it (663 at `2e79f464`) and by 5 now (665), and it reinstated the `HEAD` label this section retired 27 lines below. Removed rather than corrected: a dated figure is the only form that stays true, which is this section's own rule) |
| `scripts/brief-compose.py` | 1,780 |
| `scripts/explainer-serve.py` | 2,907 |
| `scripts/page_chrome.py` / `scripts/page_markup.py` | 450 / 438 |
| `scripts/gen-dashboard.py` / `scripts/gen-goals-page.py` | 3,546 / 1,252 |
| `.claude/hooks/regen-{backlog-page,dashboard,features-page,goals-page}.sh` | — |

⛔ **A FINDING BEFORE THE WORK STARTS: the D2 index figure has DECAYED, and at `a4f6d4b5` it is
1.82x low against its own file set.** ⟳ **CORRECTED 2026-10-16 by round 1 (CLAUDE H1), which refuted this
paragraph's first version — and the refutation is the more useful finding.**

⟳ **TENSE CORRECTED 2026-10-16 BY ROUND 3 (CODEX B2): THE INDEX NO LONGER SAYS THIS.** It *said*
*"9 files / 3,599 lines"* and enumerated those nine — the four page-producing skills, the shared
delivery contract, `brief-compose.py`, `explainer-serve.py`, `page_chrome.py`, `page_markup.py` —
and **that is now a dated correction inside the index, not its assertion.** Its headline reads
**"~11,000 lines"** today. The history below is still the finding; the present tense was wrong.

⟳ **CORRECTED AGAIN 2026-10-16 by round 2 (CODEX 9), which found round 1's own history wrong.**
Round 1 said `100cf498` *"introduced the figure"* and that it was *"accurate when written"*. The
figure was introduced four days earlier, and there are **three** stages, not two:

| Stage | Commit | The same nine files measured | Verdict |
|---|---|---|---|
| **originally measured** | `cacbac17`, 2026-09-03 | **3,599** | **exactly right** |
| **republished into the index** | `100cf498`, 2026-09-07 | 3,737 | already **3.7% stale** |
| **re-measured** | `a4f6d4b5`, 2026-10-16 | **6,542** | **1.82x** low |

⛔ **THE THIRD ROW IS DATED, AND IT USED TO SAY `today` / `HEAD` — CORRECTED 2026-10-16 BY ROUND 4
(CODEX B1), WHICH CAUGHT THE FOLD INVALIDATING ITS OWN MEASUREMENT.** It read *today · HEAD ·
6,525 · 1.81x*. ⭐ **The nine files include `explainer-delivery.md`, and the commit two before this
one added 17 lines to it** — the recompose obligation r3 CLAUDE M9 asked for. So `6,525` became
`6,542` and `1.81x` became `1.82x` **because of this branch's own work**, between one commit and the
next.

⚠ **THIS IS THE THIRD TIME A COUNT IN THIS SECTION HAS DECAYED, AND THE FIRST TIME THE CAUSE WAS
THIS DOCUMENT.** It is structural, not careless: *the spec measures a corpus that contains a file
the spec's own branch edits.* A label reading `today` is therefore false the moment anything ships,
and a dated row is the only form that stays true — which is **this section's own rule**, applied to
itself at last: *a count copied from elsewhere must carry the commit it was measured at.*

⛔ **AND THE CLAIM THAT FOLLOWED THIS WAS ITSELF TOO BROAD — CORRECTED BY ROUND 4's CLAUDE HALF
(B1).** It read *"not one figure in this section became wrong"*. **The component table seventeen
lines above still carried `346 / 73 / 211`, undated** — addends that sum to the retired **630**, and
which give the retired **6,525** when used for the nine-file total. So one figure in this section
*had* stayed wrong, in the one place that looked like raw data rather than prose. The row is dated
now. ⚠ The lesson is the reach of a fix, not the arithmetic: every number r4 CODEX B1 reported, and
every number the Claude half re-derived, was correct.

⭐ **AND THE DATED FORM WAS TESTED BY ACCIDENT, IN THE SAME FOLD, WITHIN MINUTES.** Correcting a
false enforcement claim in `explainer-delivery.md` (r4 CODEX B2) added **13 more lines** to that same
counted file. At `HEAD` the shared contracts are therefore no longer 647 and the nine files no longer
6,542 — **and not one figure in this section became wrong**, because every one of them names
`a4f6d4b5` and is still true of `a4f6d4b5`. ⛔ **That is this section's own argument demonstrating
itself twice in one afternoon:** the undated label broke on the first edit after it was written, and
the dated row survived the second.

⛔ **AND A MECHANICAL GUARD WAS CONSIDERED AND REJECTED, WITH THE REASON.** `check-claim-propagation.py`
already refuses a stale *derived* figure and has caught the spec's own line count three times. To do
the same for this one it would need the **nine-file enumeration**, which lives in prose here — so the
guard would hold a second copy of the list, which is precisely the defect it exists to prevent
(`one-rule-one-place`). A dated row needs no second copy. ⚠ What that leaves uncovered, stated
rather than hidden: nothing refuses a *new* undated count in this section.

⛔ **SO THERE ARE TWO FAILURE MODES HERE, AND THE SECOND IS THE ONE WORTH CARRYING.** The count
decayed. ⚠ **TWO DIFFERENT RATIOS LIVE HERE AND ROUND 1 PAIRED THE WRONG ONE WITH THIS ARROW
(r2 CLAUDE M1):** `3,599 → 6,542` is **1.82x** (the gap against what the index SAYS), while
`3,737 → 6,542` is **1.75x** (the growth of the SUBJECT since it was measured) — both at
`a4f6d4b5`, and both re-derived rather than adjusted. The whole point of
the three-stage history is that those are different numbers, so the arrow now carries the right one.
⚠ And `3.7%` is `138/3737` — **the denominator is the value at republication**, stated because an
unlabelled percentage is the same defect one level down. But the figure also **arrived in
`portable-practices.md` already
stale**, because it was *copied from an earlier measurement into a fresh-looking declaration without
being re-measured*. A republished figure inherits staleness **and loses the fact that it is
inherited** — the new document reads as a new measurement. That is a sharper rule than *date your
counts*: ⭐ **a count copied from elsewhere must carry the commit it was measured at, not the commit
it was written into.**

- The first version of this paragraph compared 3,599 against **10,977** — a set of its own
  construction that adds `gen-dashboard.py` and `gen-goals-page.py` (**4,798 lines, 46% of the
  Python total**), neither of which is among the nine. That is a **3.05x cross-corpus ratio**.
  ⚠ **AND THAT SET IS NOT THE ONE THIS SPEC'S OWN TABLE LISTS EITHER (r2 CLAUDE M2):** 10,977 is the
  six Python files plus the four skills — a set that *adds* the two generators and *omits* the three
  shared contracts. A paragraph whose subject is *a measurement is only as good as its corpus* has
  now mis-described its own corpus twice.

⛔ **SO THE DIAGNOSIS CHANGES, AND THAT MATTERS MORE THAN THE NUMBER.** The figure was **derived,
enumerated, dated and correct** (`portable-practices.md:17` says *"Enumerated in `docs/backlog.md`
row 89, not recalled"*, and row 89 contains the enumeration). It was not written from recall. Its
subject then grew **1.75x against the value measured at republication** (3,737 → 6,542, at
`a4f6d4b5`); it is **1.82x** against the figure the index still prints. **The failure mode is a dated count decaying,
not a count invented** — and
§3's own banner already handles decay. **Correcting it is in scope for this milestone**, and the
correction must record *that* reason.

⚠ **AND THIS PARAGRAPH WAS ITSELF A CORRECT MEASUREMENT OVER THE WRONG CORPUS** — placed in the
finding whose entire purpose was to shame that defect. It is left on the record rather than quietly
rewritten, because it is the best available evidence for why §5's CANNOT-RUN rule needs the
companion that B3 forced (see §5).

**The total, for scope sizing only, measured at `a4f6d4b5`:** 10,373 Python + 604 skills + **647**
shared contracts = **11,624 lines** across the 17 components of effort (3). ⟳ Said `630` and
`11,607` until r4 CODEX B1 — the same 17 lines, the same cause as the row above. ⚠ That is a different and larger set than
`portable-practices.md`'s nine, and the two must not be compared without saying so.

⟳ **AND THE OTHER TWO ARE ALSO ALREADY FIXED (r3 CODEX B2).** The index said *"registers 10
anchors"* and that *"a second anchor is owed"*. It now reports **13**, names the 14th as allocated
on this branch, and records that `explanation-on-demand` **exists**, striking the old sentence.

⛔ **ALL THREE WERE CORRECTED IN `b200f2cf` — PR #377, merged to master 2026-10-16 — AND THIS BRANCH
HAS CONTAINED THEM SINCE ITS REBASE THE SAME AFTERNOON.** Verified by `git log -S` on each phrase,
and `git merge-base --is-ancestor` against `master`. So **deliverable 8 as originally written is
discharged**, and the three-claim list was describing a repository state that no longer existed when
it was written down. **What remains, and what D8 therefore delivers, is in §7 item 8** — this
section does not restate it.

### Effort (2) — development velocity

CI mutation sharding (39 references in `.github/workflows/ci.yml`), `scripts/check-plan-code.py`, and
the three velocity documents (spec, plan, `docs/velocity-evidence-2026-09-24.md`). **Q0 is designed in
form and not built** and is one of two items `check-roadmap-consistency` still reports open.

### Effort (1) — recall

⟳ **MEMBERSHIP CORRECTED 2026-10-16 by round 1 (CLAUDE B1, CODEX 1), and this was a Blocking
defect: the list contained only the mechanism the evidence REJECTS, and omitted the one it endorses.**

The four components:

| Component | Lines | Where |
|---|---|---|
| `scripts/recall-llm.py` — the semantic matcher | 2,550 | **`master`** |
| `scripts/check-surface-recall.py` — the lexical matcher and its guard | 820 | `master` |
| `.claude/hooks/surface-recall.sh` — the caller | 113 | `master` |
| the memory corpus | `git ls-tree -r --name-only HEAD -- docs/memory` piped to a count of `.md` files — **159** at HEAD, 157 on `master`. ⚠ r6 CLAUDE M7: that count INCLUDES the `MEMORY.md` index; the component's own producer `recall-llm.memory_files()` EXCLUDES it and returns **158**. Both are stated because the next reader would otherwise 'correct' one to the other — and for C5, which is about what is redistributed, the index is in scope | ⛔ **`docs/memory/`, TRACKED — and this repository is PUBLIC, so the corpus is ALREADY PUBLISHED.** This cell read *outside this repo* and that was false (r6 fold). It changes what C5 asks: not *may we publish this* but *is anything already public that should not be*. ⚠ r6 CLAUDE M7: the FILES are published; the HARNESS PATH is not — `recall-llm.memory_dir()` returns `None` in a clone, so a stranger gets the corpus as documents and no working recall |

⛔ **`scripts/recall-llm.py` IS ON `master`, NOT ON AN UNMERGED BRANCH**, and so are its callers and
its mutation manifest (`scripts/mutations/recall-llm.json`; nine referencing files under `.claude/`
and `scripts/`). The branch the work was done on no longer exists — it folded into `master` — so the
omission was of **landed code**, not of parked work.

⚠ The two unmerged branches `c5-recall-matcher` (6 commits) and `backlog-117-parser-substrate` (10)
are **work in progress, not shippable units**, and are no longer counted as components (§3's counting
rule). They remain out of scope per §10.

⭐ **The measured result that must drive this effort's verdict, because it inverted** — figures taken
from `docs/dashboard-entries.md:12990-12992`, not from recall:

| Mechanism | Recall | True negatives | False-fire rate |
|---|---|---|---|
| lexical top-1 | **3/20** | 53/60 | 11.7% |
| semantic, isolated (80 mixed) | **20/20** | 60/60 | 0% |

⚠ **THE RANGE "19–20/20" MERGED TWO DIFFERENT EXPERIMENTS AND IS NOT USED (r1 CLAUDE M2).** 20/20 is
the validation brief; **19/20 is the re-measurement against the prompt that actually ships**. Both are
stated, with which is which, rather than spanned.

⚠ **AND THE BOUND, stated so it is not inflated:** 0 false fires in 60 is a **95% upper bound of
5.0%** by the rule of three — *not* "no false positives".

⛔ **So this effort's verdict must say WHICH of the three mechanisms it is about.** "It cannot be the
lexical matcher" was unexecutable against a component list that contained nothing else.

---

## 4. The criteria

Criteria 1 and 2 are `docs/portable-practices.md`'s existing filters. D1's public bar adds 3 and 4.

| # | Criterion | Decidable by |
|---|---|---|
| **C1** | **Measured** — it works, with evidence, not a confident belief | existing self-tests and manifests |
| **C2** | **Project-independent** — runs with no Supabase, no Gemini, no Fly | counting is **evidence, not a verdict** — see below |
| **C3** | **Self-contained** — does not depend on parts of this repo that are not shipping | counting is **evidence, not a verdict** — see below |
| **C4** | **Supportable** — a stranger can install it, use it, and recover from failure without the author | ⛔ **not countable** — this is what the install experiment is for. ⟳ It is **NOT** graded against D9 (r3 CODEX M1): see §4d |
| **C5** | ⭐ **Redistributable** — we are permitted to publish it, and it contains nothing that must not be published | ⛔ **not countable, and NOT YET ANSWERABLE** — see below |

⭐ **C5 IS NEW, AND NOBODY HAD ASKED IT (r2 CLAUDE M10).** D1 commits to *"public strangers, full
support bar"*, which means publishing — and **publishing requires a grant.** Measured: there is **no
`LICENSE` file in this repository**, and this spec mentioned licensing **zero** times before this
paragraph. Two sub-questions with different answers:

| What | The question | Who answers it |
|---|---|---|
| the **code** | under what licence is it published? | ✅ **ANSWERED 2026-10-16: MIT** — see below |
| the **corpus** (effort (1)'s memory files — count derived by the §3 producer, **159** at HEAD) | does it contain private content, credentials, or third-party material we may not redistribute? | a **content review**, which nobody has done |

⭐ **D7 — THE CODE HALF IS SETTLED: MIT. Decided 2026-10-16 by the owner.** Chosen over Apache-2.0
and over deferring. ⚠ The comparables were measured, not guessed: `Yeachan-Heo/oh-my-claudecode` ships
**MIT** and `openai/codex-plugin-cc` ships **Apache-2.0**, so either would have met a stranger on
familiar terms; MIT is the shorter and is the convention for tooling this size.

⛔ **AND THE LICENCE BELONGS ON THE MARKETPLACE REPO, NOT ON THIS ONE — THIS IS NOT A TECHNICALITY.**
This repository is **public** and holds the product beside the harness: `app/`, `lib/`,
`components/`, `worker/`, `supabase/` — **262 files** of a working application. A `LICENSE` at this
root would place **all of it** under MIT, which is a far larger decision than the one asked and was
never put. So:

- the **published harness package** is MIT, and the `LICENSE` lands on the marketplace repo whose
  creation §10 defers;
- **this repository stays as it is** — public, unlicensed, all rights reserved — until someone
  decides that separately;
- ⚠ **the copyright holder is not yet named.** No author is declared anywhere (`package.json` has no
  author field, the only `Copyright` line in the tree belongs to a vendored dependency, and the git
  identity is the placeholder `t <t@example.com>`). The GitHub account is `kujinlee`. **A legal name
  or entity is a one-line decision the owner still owns**, and inventing one would be worse than
  leaving it visible.

⚠ **Bound, stated rather than hidden:** no installed marketplace on this machine requires licence
metadata, so this is not a mechanical blocker to *installing* — it is a blocker to *publishing*,
which is what D1 commits to. ⚠ **And it never blocked this milestone**: the spec can be approved, the
scan built and the inventory produced without it, because §10 defers publication. An earlier
framing of this as blocking now was wrong. ⛔ **And a component cannot be `SHIP` with C5 unanswered**, because
unlike C4 there is no weaker-but-honest grade: *"we may not have the right to publish this"* is not
an evidence strength, it is a veto. C5 therefore grades `measured` or blocks.

⛔ **C2 AND C3 ARE NO LONGER CALLED "MECHANICALLY COUNTABLE" (r1 CLAUDE H4, r1 CODEX 4), BECAUSE BOTH
DIRECTIONS OF WRONG ANSWER ARE PRESENT IN THE SUITE TODAY AND WERE MEASURED:**

- **Clean count, unusable component.** `scripts/page_chrome.py` has zero project vocabulary, a
  self-test, and one outgoing import that is also shipping — C1/C2/C3 all pass. It has **no
  `argparse` and no CLI**: a stranger cannot invoke it at all. It is a library.
- **Dirty count, portable component.** `scripts/page_markup.py` matches `supabase` twice — both
  inside a **self-test fixture** asserting that a path glob survives markup rendering. The file is
  fully project-independent.

**So a count is an input to a judgement, not the judgement.** §5 states which region is scanned and
how a non-path reference is recognised.

⭐ **EVERY COMPONENT CARRIES A ROLE, and the role decides what C4 even means for it:**

| Role | What a stranger does with it | How C4 is assessed |
|---|---|---|
| `entry-point` | invokes it directly | per component, by the install experiment |
| `library` | never invokes it; it is a dependency of an entry-point | **inherited** — but only under the rules below |
| `data` | supplies content (e.g. the memory corpus) | **C4 is STRUCK, not graded** — §4b's completeness rule is satisfied by a struck C4 rather than by a grade (r2 CLAUDE M5). ⟳ **C5 IS NOT STRUCK WITH IT (r3 CODEX M2):** the earlier wording said *"graded against C1–C3 only"*, which exempted a `data` component from the one criterion added **for** it — a corpus can pass C1–C3 and still hold material we may not redistribute. A `data` component is graded **C1–C3 and C5** |

⚠ **A component may hold BOTH `entry-point` and `library`** — a module that is executable *and*
imported is not a third role, it carries two, and is assessed as an entry-point while also supplying
inherited evidence. Round 2 found the single-role table could not express this (CODEX 3).

⛔ **INHERITANCE NEEDS AGGREGATION, COVERAGE AND PROVENANCE RULES, AND ROUND 1'S VERSION HAD NONE
(r2 CODEX 3, High, INTRODUCED BY ROUND 1'S FIX).** *"Inherits from the entry-points that import it"*
is undefined the moment there is more than one, and silently wrong when there are none:

| Situation | Rule |
|---|---|
| imported by entry-points that **all** pass | inherits the pass, grade `inherited` |
| imported by a **mix** of passing and failing entry-points | ⛔ **inherits the failure ONLY IF the failure is ATTRIBUTED TO CODE IN THAT LIBRARY** — the entry-point's failure trace reaches it. A failure attributed elsewhere (an absent credential, a missing host binary) leaves the library on the passing importers' evidence |
| imported only by entry-points that are themselves `argued` | the library is **`argued`** — not `inherited` (there is no measured scenario to inherit) and not `none` (something was established) |
| imported by **no** entry-point | **no inheritance is possible** — grade `none`. ⚠ An orphan library is also a scope question: ask why it is shipping at all |
| imported by entry-points that **all** fail | ⟳ **ADDED BY r3 CODEX M3 — the table covered every population but this one.** Apply the same attribution test: a failure **attributed to code in this library** makes it a measured failing component, graded `measured` with that defect named. A failure attributed elsewhere leaves it with **no measured scenario at all** — grade `none`. ⟳ **THE `argued` BRANCH THIS ROW FIRST CARRIED WAS UNREACHABLE AND IS DELETED (r3 CLAUDE M2).** It read *"`argued` if its importers were argued"*; an importer that FAILED the experiment was by definition exercised, while `argued` is defined as *no experiment reached it*, so no importer can be both and every instance fell through to `none` anyway. ⛔ **Do NOT read `inherited` here** either: it is defined through a *successful* named scenario, so applying it literally to an all-failing population returns `none` and discards measured fault evidence |
| imported by a mix of **measured-passing** and **CANNOT RUN** importers | ⟳ **ADDED BY r4 CODEX M1, which is the second population this table has been missing and the first one the previous fix CREATED.** The CANNOT RUN row below makes such an importer `argued`, and the mixed row above resolves only *passing vs failing* — so a library imported by one measured pass and one unrunnable entry-point matched **no row at all**. **The rule: a measured scenario that reached the library is enough.** It is `inherited`, on the strength of the importer that ran; the unrunnable importer contributes nothing in either direction, and the inventory records that it could not run. ⚠ Symmetrically, **measured-FAILING plus CANNOT RUN** is graded by the attribution test alone — the failure counts if it is attributed to code in this library, and the unrunnable importer again contributes nothing |
| an importer the experiment **CANNOT RUN** against | ⟳ **CLASSIFIED BY r3 CLAUDE M2, which found the spec silent and two of its rules pulling opposite ways.** The spine says *"Cannot run is a FAILURE, never a pass"*, which puts it in the failing population; §5 says an unexercised entry-point is `argued`, which puts it outside. **The rule: CANNOT RUN is NOT a failure of the component** — it is a failure to measure, so the importer is `argued` and contributes no failure to inherit, **and the inventory records the reason it could not run.** A component may not be graded `measured` on a run that did not happen |
| part of an **import cycle** | graded by the entry-points at the cycle's boundary; a cycle with no entry-point outside it is `none` |

⛔ **WHY THE IMPLICATION TEST IS LOAD-BEARING, MEASURED ON THE FILE THIS TABLE WAS ADDED TO RESCUE
(r2 CLAUDE H5, High, INTRODUCED BY ROUND 2'S FIX).** Round 2's first version read simply *"mixed
inherits the FAILURE"*. `scripts/page_chrome.py` is imported by **eleven** files, among them
`scripts/gen-dashboard.py`, which invokes `gh` (`gen-dashboard.py:521`). Under §6's fresh-`HOME`
isolation `gh` has no credentials, so that entry-point fails **by construction** — and the unqualified
rule made `page_chrome.py` inherit a failure caused by *an absent credential it never touches*. That
is exactly the phantom backlog row D5 (§4b) was decided to eliminate, reinstated on the same file,
**by the fix for the laundering case in the other direction.** Both directions now need the
attribution test, and that is what the row above states.

⚠ **AND `inherited` MUST NOT LAUNDER `argued` UPWARD (r2 CLAUDE H4).** `inherited` requires at least
one named **`measured`** scenario. Without that clause a library under an entry-point that was itself
only *argued* would be graded `inherited`, which reads stronger than its evidence.

⛔ **AND AN INHERITED PASS MUST NAME THE SCENARIO THAT EXERCISED IT.** The failure round 2
constructed: an entry-point passes through one branch of a library while *an unexercised branch of
the same library* causes a different entry-point's failure — so the library "inherits a pass" from a
run that never touched the code at fault. **An `inherited` grade therefore records which successful
scenario exercised the component**, and a library no scenario exercised is `none`, not `inherited`.
⚠ **Without that, `inherited` launders exactly the component most likely to be at fault.**

⚠ **Why the role exists at all.** `page_chrome.py` cannot be assessed for C4 per component, so the
original text forced `NEEDS-WORK` with defect *"no way to assess it"*, and §7 turns every
`NEEDS-WORK` into a backlog row — **a filed defect for a file that has none.**

**C3 is still expected to be the main killer — but the known shape was mis-stated, and the real one
is worse.** ⟳ **CORRECTED 2026-10-16 (r1 CLAUDE H3, H5; r1 CODEX 4):**

- The literal `scripts/check-*` **does not occur in `brief/SKILL.md` at all** (measured: 0
  occurrences). What its ground-truth block holds is **nine repo-specific items — 4 bare guard names
  (`check-docs`, `check-producer-enumeration`, `check-roadmap-consistency`, `check-test-counts`), 4
  document paths (`docs/backlog.md`, `docs/reviews/`, `docs/roadmap-to-launch.md`,
  `docs/superpowers/`) and 1 tool name (`TaskList`)**. ⛔ **Five of those nine are neither paths nor
  file invocations, so they are invisible to both of §5's original detectors** — the scan would have
  scored at most 4 of 9 on the component D4 elects to calibrate against.
⭐ **AND THE FIX FOR IT IS ALREADY KNOWN, WHICH CHANGES THIS MILESTONE'S OUTLOOK (asked by the owner
from the page, 2026-10-16: *“is it possible to use other path name than scripts… Or pathname for
scripts can be configurable by user?”*).**

**Neither renaming nor configuring is the answer, and the measurement says why.**
`${CLAUDE_PLUGIN_ROOT}` already exists and is substituted by the harness — the official
`openai/codex-plugin-cc` plugin uses it inside its `hooks.json`, and `Yeachan-Heo/oh-my-claudecode`
uses it throughout. ⛔ **AND BOTH OF THOSE PLUGINS KEEP THEIR DIRECTORY NAMED `scripts/`**, which is
the evidence that settles it: **the collision is not caused by the NAME, it is caused by the path
being resolved against the CALLER'S working directory instead of against the package.**

| Option | What it does to the measured failure | Verdict |
|---|---|---|
| a unique name (`comprehensibility_scripts/`) | ⟳ **nothing that was measured** (r3 CODEX B1). The failure is *already* loud in both repos — 4 of 4 exit 2. A unique name would only matter against a **file-name** collision, and neither repo has one | an improvement against an **unobserved** case, and still **not a fix** — CWD-relative either way |
| a user-configurable path | moves the failure to setup time, and adds a config file to ship, document and get wrong | **rejected** — more surface, same class |
| ⭐ **`${CLAUDE_PLUGIN_ROOT}/scripts/…`** | the package resolves **its own** location; the CWD stops mattering | ⭐ **the fix.** No new name, no user configuration, already the ecosystem convention |

⚠ **Measured: our suite uses `${CLAUDE_PLUGIN_ROOT}` NOWHERE.** Every one of the three invocations
in `explainer-delivery.md` — ⟳ **three CALL SITES across TWO distinct filenames** (one
`brief-compose.py`, two `explainer-serve.py`), qualified after r3 CLAUDE L2 found this `3` adjacent
to a `4` with neither saying what it was over —
is CWD-relative, so what answers them is whatever the caller's working directory holds — which in
both repositories measured is **nothing, loudly** (§6, as corrected by r3).

⛔ **FIXING IT REMAINS OUT OF SCOPE (§7 repairs nothing, by D2 and the owner's option A) — but the
inventory must now record the defect WITH its known fix**, because *“C3 blocker, remedy unknown”* and
*“C3 blocker, one-line remedy already conventional”* are different verdicts for a reader deciding
what to do next.

⭐ **AND THIS IS THE FIRST CONCRETE `harvest: practice` ENTRY (D6, §4c):** *a shipped package
resolves its own files from its own location, never from the caller's working directory — and
renaming the directory does not fix it, because the resolution is what is wrong, not the name.*
⟳ The entry's earlier second clause (*"it just fails loudly instead of silently"*) is **struck**: it
priced an outcome r3 CODEX B1 showed had never been measured. That travels to any packaging
ecosystem, which is what D6 exists to capture.

- ⛔ **AND "the problem is concentrated in one file" IS FALSE (r1 CLAUDE H5).**
  `.agents/skills/shared/explainer-delivery.md` scores **0** under the vocabulary detector — and
  carries **three repo-relative `python3 scripts/...` invocations** resolved from the caller's CWD.
  It is the contract **all four** page-producing skills route through, so in a stranger's repo those
  resolve to nothing — measured, **4 of 4 = the 2 distinct filenames × the 2 repositories**, exit 2
  (§6) — or, should a neighbour ever hold a file of
  the same name, to that file. ⚠ Only the first of those two has been observed. That is a C3/C4 blocker for every
  component of effort (3), and it sits in the file this spec previously presented as the good news.
  The existing measurement is C2-only; "concentrated in one file" is a C3 conclusion that a C2
  measurement cannot support.

**Verdicts are per component, and there are exactly three:** `SHIP`, `NEEDS-WORK` (with the named
defect), `DON'T-SHIP` (with the reason). ⛔ **AND D5 (§4b) NARROWS WHAT FOLLOWS — read them
together, because this sentence alone is no longer the rule (r2 CLAUDE B1c).** Under D5 a component
the experiment merely never reached is `argued`, **not** `NEEDS-WORK`, and files no backlog row;
`NEEDS-WORK` means a *named defect*. A fourth verdict — "unknown" — is not permitted; a component
that cannot be assessed is `NEEDS-WORK` whose named defect is *"no way to assess it"*. ⚠ **That rule
now bites only where assessment is genuinely impossible**, because the role table above removes the
case where it was firing on `library` components by construction.

> ⟳ **§4b now precedes §4c (r3 CLAUDE L1).** They printed in the order 4c, 4b for three
> rounds, so D6's harvest axis arrived before the D5 grades it sits beside. The section
> NUMBERS are unchanged, because five review documents and the guard's registry cite them.

## 4b. D5 — the verdict and the strength of its evidence are TWO axes

⭐ **SETTLED 2026-10-16 BY THE OWNER, who found the contradiction by reading the walkthrough page and
asked whether a fourth verdict (`CANNOT-ASSESS`) was the answer. Recorded as a decision of record;
do not re-open.**

**The contradiction they found.** §4 forbids a verdict of "unknown" and then defines a bucket that
*is* unknown under another name — and because §7 files a `docs/backlog.md` row per `NEEDS-WORK`, a
component with no defect generated a filed defect.

**Two different things were being called unknown, and only one of them is work:**

| Which unknown | What it really is | Is `NEEDS-WORK` right? |
|---|---|---|
| *"we have not assessed it yet"* | a temporary state of **our process**; it goes away by doing work | **Yes** — and this is the shrug the three-verdict rule exists to stop |
| *"this cannot be assessed by this method"* | a permanent property of the component **paired with** the method | **No** — it blames the component for a limit of the test |

⛔ **THE DECISION: THE VERDICT AXIS IS UNCHANGED, AND EVERY VERDICT CARRIES AN EVIDENCE GRADE.**
A fourth verdict was considered and **rejected** for two reasons: it re-opens the escape hatch the
three-verdict rule closes, and it still cannot separate *"fit to publish, and we proved it"* from
*"fit to publish, and we argued it"* — which is the distinction that actually matters here, because
§6's bound means two of the three efforts can only ever be argued.

| Verdict (unchanged) | × | Evidence grade (new) |
|---|---|---|
| `SHIP` · `NEEDS-WORK` · `DON'T-SHIP` | × | `measured` — the install experiment exercised it, and the scenario is named |
| | | `inherited` — a `library`, passing via named entry-point scenarios (§4's rules) |
| | | `argued` — C1–C3 plus reasoning; no experiment reached it |
| | | `none` — nothing was established |

**Consequences, stated so they can be checked:**

- **Every component in the inventory carries both fields.** A verdict without a grade is an
  incomplete row, and deliverable 5 is not done until every row has one.
- **`SHIP` + `argued` is permitted, and is the honest label for efforts (1) and (2)** under §6's
  bound. It is *not* equivalent to `SHIP` + `measured`, and the inventory must not present them in a
  way that reads as equivalent.
- **`NEEDS-WORK` is now reserved for a named defect**, including *"no way to assess it"* where that
  is genuinely true after the role rules are applied. A component that is simply unreached by the
  experiment is `argued`, not `NEEDS-WORK`, and **files no backlog row**.
- **`DON'T-SHIP` + `argued` is also permitted** — a component can be ruled out on reasoning.

⚠ **THE COST, RECORDED RATHER THAN DISCOVERED LATER.** Two fields must be read together, and
`SHIP / argued` can be mis-skimmed as plain approval by a reader who scans only the verdict column.
**That risk is a stated cost of this decision**, not a hidden one.

⛔ **AND THE FALSIFIER IS THE CHECKABLE ONE, NOT THE UNOBSERVABLE ONE (r2 CLAUDE M4).** The first
version said the scheme fails *"if the inventory is read and acted on as though `argued` meant
`measured`"* — **nothing can observe how a document was read**, so that falsifier could never fire.
The checkable form, which the same section already implies:

> **The scheme has failed if any `SHIP` row renders its grade outside the same visual unit as its
> verdict, or if any `inherited` grade names no scenario.**

Both are mechanically decidable from the inventory itself, and the stricter alternative — requiring
`measured` or `inherited` for `SHIP` — remains the fallback if they fire.

---

## 4c. D6 — a component that cannot SHIP can still be HARVESTED, and the two are independent

⭐ **SETTLED 2026-10-16 BY THE OWNER, reading the walkthrough.** Their words, against the page's own
line *"it is a technique, not a tool, and techniques travel as prose"*:

> *"effort (2) may not be applicable for other repos with different harness set-up. However, some
> idea may be transferable such as partial mutation (if mutation is widely used method for robust
> codebase), mechanical inspection before paying expensive gates such as CI, another round of reviews
> etc, sharding CI process etc. These ideas may be transferred in prose as optional ideas.
> **We just harvest as much as transferable.**"*

⛔ **SO `DON'T-SHIP` IS NOT THE END OF A COMPONENT'S VALUE, AND THE INVENTORY MUST NOT TREAT IT AS
ONE.** Every component carries a third field, independent of its verdict and its evidence grade:

| Field | Values | What it records |
|---|---|---|
| **harvest** | `practice` · `none` | whether the component yields a transferable *practice* even where no code travels |

**Why this is a real addition rather than a softening.** The verdict axis asks *can a stranger
install and run this?* The harvest axis asks a different question — *is there something here a
stranger could DO, in their own repo, with their own tools?* A component can answer no to the first
and yes to the second, and the original three verdicts had nowhere to put that answer.

⭐ **Effort (2) is the worked example, and it is why this was raised.** Its machinery is this
repository's CI wiring and almost certainly `DON'T-SHIP` as code. The practices behind it are not
repo-specific:

- **partial / scoped mutation** rather than a whole-suite sweep — transferable wherever mutation
  testing is already used;
- **mechanical inspection before paying an expensive gate** — run the cheap local check before
  spending a CI cycle or a review round;
- **sharding an expensive gate** so its wall-clock stops scaling with its subject;
- ⚠ and the one this milestone itself demonstrates: **a guard beats a convention wherever the
  convention has already failed once.**

⚠ **THE BOUND, so the harvest axis cannot become a way to call everything a success.** `harvest:
practice` requires **a named entry written into `docs/portable-practices.md`**, with the measurement
that earned it. A practice asserted but not written is `harvest: none`. ⛔ **And a harvest NEVER
upgrades a verdict** — a `DON'T-SHIP / harvest: practice` component is still not shipping, and the
inventory must not present the harvest in a way that reads as partial approval. That is the same
mis-skim risk D5 records, and it has the same answer: render the fields together.

**§7 gains a deliverable for it** (item 9b), and D2's *"a battle-tested harness and reproducible
framework for NEW projects"* is what it serves — prose was always that deliverable's medium.

---

## 4d. D9 — the support bar the owner commits to, decided before the inventory and not after

⭐ **D9 — BEST-EFFORT, VERSIONED. Decided 2026-10-16 by the owner**, by selection card, after they
answered *yes* to the prior question *does "publishable" need a support policy decided first?*

| What the published package owes | What it does NOT owe |
|---|---|
| **semver tags** — a version a stranger can pin | a response time on issues |
| a **`CHANGELOG`** entry per release | a deprecation schedule |
| **a breaking change gets a major bump** | any commitment to fix what is reported |
| issues are **read** | a commitment to answer them |

⛔ **WHY THIS QUESTION WAS NOT ALREADY ANSWERED BY D1, AND WHY CONFLATING THEM IS THE DEFECT TO
AVOID.** D1's *"full support bar"* is a claim about the **artifact**: criterion C4, a stranger can
install it, use it and recover from failure **without the author**. D9 is a claim about the
**owner's ongoing obligation after publishing**. They are different commitments, and the spec
asserted the first while pricing none of the second — which is how an open-source burden gets
acquired by accident. ⚠ **D9 does not weaken C4**: the artifact bar is unchanged, and under
best-effort support C4 matters *more*, because documentation is the only channel a stranger has.

⭐ **THE REJECTED OPTIONS ARE RECORDED, because the reason one was rejected is the useful part.**

- **No support, dated snapshots** — cheapest and fully honest, and C4 would still hold. Rejected
  because a stranger cannot distinguish a bugfix from a rewrite, so in practice they pin one commit
  and never upgrade: the package becomes a snapshot rather than a thing with a life.
- **Supported, with a stated response window** — the only level that reads as maintained. Rejected
  because it acquires a recurring obligation from strangers on their schedule, and a missed window is
  a broken promise rather than an unmet hope.

⛔ **D9 NAMES WHAT MAKES IT FAIL — AND THE FIRST VERSION NAMED ONLY TWO OF ITS THREE PROMISES
(r3 CODEX M1).** It said *"a release with no version tag, or a tag with no `CHANGELOG` entry"* and
called those two *"the whole promise"*. They are not: the table above also promises **a major bump
for a breaking change**, and a release can satisfy both stated observations while breaking it. The
counterexample is one line — `1.2.0`, tagged, with a changelog entry, carrying a breaking change.

**The failing observations, all three, each checkable by looking at a release:**

| # | Observation that fails D9 |
|---|---|
| 1 | a release with **no version tag** |
| 2 | a version tag with **no `CHANGELOG` entry** |
| 3 | ⟳ a release containing a **breaking change without a major-version bump** |

⛔ **AND D9 IS NOT C4'S GRADING PREDICATE. THAT CLAIM IS WITHDRAWN (r3 CODEX M1), AND THE THREE
CASES THAT KILL IT ARE WORTH KEEPING:**

- compliant versioning, but recovery instructions that say *"contact the author"* → **passes D9,
  fails C4**;
- working independent recovery, but no version tag → **passes C4, fails D9**;
- so the two vary independently, and a predicate that can be satisfied while the thing it supposedly
  grades fails is not a predicate.

⭐ **What survives, and it is the half that was worth asking:** *best-effort response timing does not
weaken C4.* Independent recovery stays gradeable precisely **because** no help is promised — the
documentation is the only channel a stranger has, which raises C4's importance rather than lowering
its bar.

⛔ **AND WITHIN PR 1, D9 CANNOT BE OBSERVED AT ALL — SO IT IS A DEFERRED PUBLICATION REQUIREMENT,
NOT A MILESTONE GATE, AND CALLING IT A GATE HERE WAS THE SAME MISTAKE IN SMALLER TYPE.** §10 defers
the published marketplace repository, and all three failing observations are observations **about a
release**. PR 1 produces no release, no tag and no `CHANGELOG`, so **none of the three can fire
inside this milestone.** D9 becomes checkable at the moment of first publication, and what PR 1
owes is the stated bar itself — §4d, and nothing more.

## 5. The scan — `scripts/check-publishability.py`

Built as a guard because this repo's rule is *before adding a rule, ask whether it can be a script*.
It carries the usual contract: `--self-test` with a declared count verified by running it, a mutation
manifest, a caller, and no fail-open handler.

**Per component it reports:**

1. **project-specific references** — matches against a derived vocabulary (`supabase`, `gemini`,
   `fly`, `youtube-playlist`, repo-rooted paths), not a hand-written list;
2. **cross-repo dependencies** — invocations of files outside the component's declared shipping set;
3. **presence of a self-test and of user-facing documentation;**
4. ⭐ **bare-name references (added by r1 CLAUDE H3, r1 CODEX 4)** — guard names, tool names and
   skill names that are neither paths nor file invocations. Five of the nine references on the
   component D4 calibrates against are of exactly this form, and detectors 1 and 2 cannot see any of
   them;
5. ⭐ **prose-declared skill dependencies (added by r1 CODEX 2)** — a skill that instructs the reader
   to load another skill depends on it. `brief/SKILL.md` and `explain-findings` both require
   `artifact-design`, which appears nowhere in §3's component table. A file-invocation scan finishes
   successfully and never sees this form.

6. ⭐ **runtime prerequisites (added by r2 CODEX 6)** — imports of undeclared installed packages,
   required executables, and environment/configuration reads. ⟳ **THIS ITEM WAS MISSING FROM THIS
   LIST (r3 CLAUDE H3):** the list printed **1, 2, 3, 4, 5, 7** while detector 6 was defined 58
   lines below as *another* list's item 2, so §5 could not enumerate its own subject and item 7's
   *"all six above"* was false — five were above. ⚠ The full statement, including the
   mention-candidate rule that keeps it from repeating detector 1's positional defect, stays at its
   original site below and is **not restated here**; this item exists so the enumeration is complete.

7. ⭐ **inbound registration dependencies (added by r2 CLAUDE H6).** ⛔ **All six detectors above
   look OUTWARD from a component — what it reaches.** None asks the opposite question: *does this
   component need an entry in host configuration, a hook registration, a `PATH` entry, or a plugin
   manifest stanza in order to do anything at all?* The four regen hooks and the recall hook are
   inert without a `settings.json` stanza a stranger does not have, and that dependency is invisible
   to every outward-looking detector.

   ⟳ **THE PREDICATE IS NOT "HAS NO INVOKER" (r3 CODEX M4, which gave it a case in each
   direction).** The first version read *a component with no importer and no invoker must declare
   what registers it*. Invocation and required registration are different properties:

   | | The case | Why the first predicate got it wrong |
   |---|---|---|
   | **false negative** | a hook invoked by its own self-test, but missing its production `settings.json` stanza | it *has* an invoker, so the predicate never asks for the registration that is actually absent |
   | **false positive** | a documented standalone CLI whose caller is the **user** | no in-repo importer or invoker, yet it needs no host registration at all |

   ⛔ **So the predicate is: a component that requires a host registration in order to do anything
   must declare it** — and the detector decides *requires* from how it is reached in production, not
   from whether any caller exists. A **test-only** invoker does not discharge it.

   ⟳ **AND THE EXEMPTION IS NOW AN OBSERVABLE ONE (r3 CLAUDE M3).** The first version exempted *"a
   component whose production caller is a person"*, which §5 commits a **script** to deciding — and
   nothing stated how a script recognises that. An undecidable exemption restates the false
   positive instead of closing it. **The mechanical form: the component itself declares
   `invoked-by: user` in its own documented interface** (a `--help`/usage block for a CLI, or the
   skill's own front matter), and the detector checks for that **declaration**. So:

   | What the scan sees | Verdict |
   |---|---|
   | no production invoker, no registration declared, no `invoked-by: user` | **`NEEDS-WORK`**, defect named |
   | no production invoker, `invoked-by: user` declared | **exempt** — a person is the caller, and the component says so where a stranger reads it |
   | a test-only invoker, nothing declared | **`NEEDS-WORK`** — a self-test is not a caller |

   ⚠ **This moves work onto the components rather than onto the detector, deliberately:** a
   declaration is checkable, an intention is not, and a stranger needs the declaration anyway.

⛔ **THE SCANNED REGION IS STATED, because the choice alone flips a verdict (r1 CLAUDE H4).**

⟳ **ROUND 1'S VERSION OF THIS RULE WAS WRONG IN BOTH DIRECTIONS AND IS REPLACED (r2 CODEX 6, High).**
It excluded fixtures from detector 1 wholesale and included them in the dependency detectors
wholesale, which confuses **a mention** with **a dependency**:

- a portable renderer fixture containing the literal `TaskList` does **not** require that tool;
- a historical comment naming a guard is **not** an invocation;
- but a self-test that genuinely contacts a project service, or needs project credentials, **is** a
  real C2 violation that a location-based exclusion hides.

**So the rule is behavioural, not positional:**

1. **A match is a MENTION CANDIDATE until something makes it a dependency** — an import, an
   invocation, a documented prerequisite, or a runtime configuration read. Mention candidates are
   **reported separately** from dependency findings.
   ⛔ **AND "NEVER ALONE DECIDES A VERDICT" IS MADE ENFORCEABLE, NOT ADVISED (r2 CLAUDE M8).** Every
   non-`SHIP` verdict **cites the dependency-finding ids it rests on**, and the scan **refuses to
   emit a dependency-finding id for a mention candidate.** Then the rule has a falsifier: a non-`SHIP`
   verdict citing no id, or citing a mention candidate's id, is a defect in the inventory.
   ⚠ **A configuration read counts as a prerequisite only when the component FAILS OR DEGRADES
   without it (r2 CLAUDE M7)** — i.e. there is no default, or the default leads to an error path. A
   read with a working default is a **mention candidate**, not a dependency. Without that rule
   detector 6 repeats the positional-matching defect detector 1 was just repaired for.
2. ⭐ **Detector 6 — runtime prerequisites (added by r2 CODEX 6).** ⟳ Enumerated as **item 6 of the
   detector list above** since r3 CLAUDE H3; this is its full statement. A generic Python import of an
   undeclared installed package is *none* of project vocabulary, an external file invocation, a bare
   guard name, or a prose-required skill — **so none of detectors 1–5 looks at it**, and it is
   exactly what breaks a stranger's run first. Detector 6 covers imports, required executables, and
   environment/configuration reads.
3. **Fixtures are exempted by BEHAVIOUR**: a fixture literal that is never resolved, imported or
   invoked is a mention; a fixture that performs a project-dependent action is a dependency.

⛔ **THE SHIPPING SET IS DECLARED PER PUBLISHABLE UNIT, NOT PER COMPONENT (r1 CLAUDE H5).** Read per
component, `explainer-delivery.md` scores dirty because `brief-compose.py` is "outside its set", even
though both ship together; read per unit, it scores clean and the real coupling is the CWD-relative
path, which detector 2 reports against the *installed* layout. The spec previously said neither.

⛔ **It must report CANNOT RUN rather than a clean score when it cannot resolve a component's shipping
set.** A zero over a set it failed to build is this repository's single most-measured failure.

⭐ **AND CANNOT RUN NEEDS A COMPANION, BECAUSE A SET CAN RESOLVE SUCCESSFULLY AND BE WRONG — MEASURED
AGAINST THIS SPEC'S OWN PATHS (r1 CLAUDE B3, Blocking; r1 CODEX 2).** §3 named the shared contracts
as `.claude/skills/shared/`. That path is real, readable and non-empty, so nothing triggers CANNOT
RUN. But its entries are **git symlinks (mode `120000`)** into `.agents/skills/`, and `grep -r` does
not follow a symlink met during a directory walk. With a known positive confirmed first, a walk over
the path this spec named finds **nothing**: `grep -rl 'check-' .claude/skills/ | wc -l` → **0**, while
`.agents/skills/` → **6**. A scan built from §3's own component paths would have reported **zero
project-specific references and zero cross-repo dependencies over a silently empty set** — a clean
score, not CANNOT RUN.

**So the scan must additionally:**

- **resolve symlinks** when building a component's file set, and record the resolved real paths;
- **assert a non-zero expected file count per component** and FAIL when the resolved set is empty or
  smaller than declared — *a zero over a resolvable-but-empty set is indistinguishable from a clean
  component*;
- ⭐ **compare IDENTITIES, not cardinality (r2 CODEX 4, High — round 1's fix did NOT close this).**
  A count check passes on a substitution: declare `coupled.py`, resolve `safe.py`, and
  `len({"safe.py"}) == len({"coupled.py"})` is true. **So the resolved set must equal the declared
  set member-for-member**, not merely in size;
- ⭐ **derive the declaration INDEPENDENTLY of the scan, and validate it.** Round 2's second
  counterexample is worse than the first: omit a dependency, then write the expected count *from the
  already-truncated scan* — and every added check passes, because the oracle and the thing it checks
  have the same author. **§7 item 2 therefore names who derives the declaration and what validates
  it against the installed layout and the dependency closure** — an oracle written from the output
  it is meant to check is not an oracle;
- **carry a mutation per DETECTOR as well as per file-set rule (r2 CLAUDE H7).** Three guard the
  file set — one that **empties** a component's set, one that **substitutes** a member while
  preserving cardinality, and one that **omits** a dependency and writes the count to match — and
  ⛔ **detectors 3, 4, 5 and 6 carry one each**, because round 2 added detector 6 as *the thing that
  breaks a stranger's run first* and then required no mutation to reach it. A detector with no
  mutation is a detector nothing proves fires. ⚠ For detector 6 the **known positive must be
  constructed in the self-test fixture** — a fixture component that imports an absent package —
  rather than relying on a real component happening to have one. ⚠ The empty-set mutation alone
  cannot expose substitution; round 1 required only that one.

⚠ **This spec's own component table now names `.agents/skills/shared/` (the real directory) rather
than the symlink path**, so the measured failure above cannot be reached from §3 as written.

⚠ **A WORKED EXAMPLE OF STATING THE FALSIFIER, because this branch got it wrong three times in a row
(r2 CLAUDE M9).** Round 1 filed *"`regen-features-page.sh` is not executable, unlike its three
siblings"*. Round 2 checked that file, found mode `100755`, and directed the finding be withdrawn.
The coordinator then checked the *claim* and found `regen-dashboard.sh` is the `100644` one. **All
three parties checked a file or a claim, and none checked whether the mode MATTERS.** It does not:
`.claude/settings.json` invokes all four as `bash <path>`, so the executable bit is never consulted.
⛔ **So the inventory records the observation together with what would make it a defect** — *any hook
invoked directly rather than through `bash`* — which is currently false for all four. A true
observation with no consequence is not a defect, and saying so is cheaper than three rounds of
checking the wrong thing.

**Its falsifier, which is the point of D4:** **a blocker OR a degraded result** that the install
experiment hits on a component the scan scored clean is a **scanner defect**, fixed in the scan, not
recorded as a footnote. The scan is not permitted to be an opinion in script form.

⛔ **THE FALSIFIER COVERS DEGRADATION, NOT ONLY BLOCKAGE (r1 CLAUDE B2, Blocking; r1 CODEX 6).** As
first written it keyed on *"any blocker the experiment hits"*, and the failure that matters here is
not a blocker: the suite can **produce a hollow page and report success**. So it now reads — a
component the scan scored clean against which the experiment hits **a blocker OR a degraded result**
is a scanner defect.

⚠ **AND IT IS UNREACHABLE FOR EFFORTS (1) AND (2) BY CONSTRUCTION**, since §6's experiment covers
effort (3) only. For those two the scan has **no falsifier at all** — stated here rather than left to
be discovered, and it is half of why §7 item 0 exists.

---

## 6. The install experiment

A throwaway repository **outside** this one, with no Supabase, no Gemini, no Fly credentials and no
`scripts/check-*`. The suite is added as a **throwaway local marketplace — which is not the published
marketplace repository §10 defers** (r1 CLAUDE H2, r1 CODEX 7: §2 defines a marketplace as a git repo
carrying `.claude-plugin/marketplace.json`, so without this clause §6 required building the artifact
§10 forbids) — and installed the way a stranger would.

⛔ **ISOLATION IS THE EXPERIMENT (r1 CODEX 3, Blocking). A DIFFERENT WORKING DIRECTORY IS NOT
ISOLATION.** Run from a new directory but the author's own environment, the suite passes using
resources a newcomer does not have: `~/.claude/` skills and plugin cache, an already-running
`explainer-serve.py`, and — decisively — `~/explainers/`, **which is a symlink into this very
repository**, so `brief-compose.py`'s source lookup finds a usable page that a stranger has none of.
Round 1 verified the asymmetry: called against a clean-home path the composer exits *"no explainer
directory … run /explain-diff once first."*

**The experiment therefore specifies, and records:**

- a **fresh `HOME`**, with its own `.claude/` config and plugin cache — not the author's;
- **no inherited server**: the server is started by the experiment, from the installed package;
- **no inherited explainer corpus** — in particular `~/explainers/` must not resolve into this repo;
- ⭐ **a DECLARED BASELINE, because a fresh `HOME` is not isolation (r2 CODEX 7, High — round 1's fix
  was incomplete).** `HOME` does not govern `PATH`, the Python interpreter and its installed
  packages, `git` configuration, environment variables, `$TMPDIR` contents, or network access. A
  run can succeed on a repository-specific executable still on `PATH`. **The baseline names what a
  stranger is ASSUMED to have** — interpreter version, package set, available commands, network
  policy — and every deviation from it is recorded as a prerequisite;
- ⭐ **a capture MECHANISM, and its stated limits.** Round 1 required *"a record of every resource
  the run touched"* with nothing to produce it — **an exhaustive-observation requirement with no
  implementation is not evidence of isolation, it is an aspiration.** So: name the mechanism
  (process/filesystem tracing, or an allow-listed environment), and **state what it cannot see**.
  ⚠ An unobservable access must be declared unobservable rather than counted as absent.

**Pass condition, stated so it can fail — and it asserts CONTENT, not mechanism (r1 CLAUDE B2,
Blocking).**

⟳ **ROUND 1'S "NON-EMPTY" TEST IS REPLACED — IT FAILED IN BOTH DIRECTIONS (r2 CODEX 2, High,
INTRODUCED BY ROUND 1'S FIX).** Non-emptiness is not correctness: a page carrying an **incorrect
commit, a fabricated roadmap status and unrelated guard output passes it**. And it produces false
refusals, because **emptiness is sometimes the right answer** — `git status --short` legitimately
returns nothing in a clean checkout (round 2 measured 0 bytes in its own), and the skill explicitly
permits reporting an empty result.

**So the experiment runs against a SEEDED stranger repository with KNOWN facts**, and the pass
condition is:

1. the page is **produced and served**, and the reader can ask a question inside it;
2. each ground-truth item's result **matches the seeded repository's known fact** — including
   *legitimately empty* where that is the known fact. ⛔ The distinction that must be preserved is
   **"correctly empty" versus "returned nothing because the capability is missing"**, and only a
   seeded expectation can tell those apart;
3. ⭐ **one identified USEFUL operation completes through the installed paths (r2 CODEX 8, High).** A
   script that prints `--help` and then cannot locate its packaged resources satisfies "it ran" and
   establishes nothing;
4. ⭐ **recovery is split into a question and a conditional (r2 CLAUDE H3).** The suite documents no
   recovery procedure, so *"one documented recovery scenario succeeds"* had **no subject** — and
   authoring one would collide with §7's no-repair rule. So: **(a)** the inventory answers *does this
   component document how to recover from failure at all?* — answerable today, and the answer is
   **no**, which is itself a C4 finding the inventory carries; and **(b)** a **conditional pass
   condition**: *where a recovery procedure is documented, it succeeds under isolation*. A condition
   over an empty set passes vacuously, and that is recorded rather than hidden;
5. ⭐ **an entry-point COVERAGE MATRIX is recorded** — which entry-points were exercised and which
   were not. **Conclusions are bounded to the exercised ones**; an unexercised entry-point is
   `argued`, never `measured` (§4b).

⛔ **WHY THE MECHANISM-ONLY VERSION COULD NOT FAIL.** In a repo with no `scripts/check-*`, all nine
of `brief`'s ground-truth items return nothing. The skill explicitly says to *report* that rather
than stop (`brief/SKILL.md:42`, and its own note that a renamed file "fails silently by returning
nothing"). Page production does not depend on step 1 — it runs through `brief-compose.py` and
`explainer-serve.py`. So a page gets composed, the server starts, Ask works, **and the old pass
condition was MET** by a page carrying no roadmap, no backlog, no ratchet results and no git
reasoning: `brief`'s entire content. The experiment hit no blocker; it hit a hollow page, and `SHIP`
would have been recorded for the component §4 elects as the expected main killer.

Producing a file that cannot be served is also not a pass — serving is the half that carries the Ask
channel, and `file://` loses it by design.

⭐ **TWO TIERS, AND THEY ANSWER DIFFERENT QUESTIONS (asked by the owner from the page, 2026-10-16:
*“how to find a repo for experiments? we may try a public repo that uses AI and harness”*).**

| Tier | What it is | What only it can answer |
|---|---|---|
| **A — the seeded throwaway** | a repository we build, with **known facts** | *is the result CORRECT?* — only a seeded repo makes *correctly empty* distinguishable from *the capability is missing*, which is the pass condition above |
| **B — a real third-party repo** | someone else's harness repo, cloned | *is our seeding WRONG?* — it is the falsifier for tier A, exactly as tier A is the falsifier for the scan (§5) |

⛔ **NEITHER REPLACES THE OTHER, AND THE ORDER MATTERS.** Tier A is the oracle and cannot be
dropped: we cannot seed known facts into someone else's repository, so a tier-B failure is not
diagnosable on its own. Tier B is where assumptions tier A accidentally satisfies show up — the same
relationship this project has already measured between a mock and a live call (2,808 green tests,
then a 500 on first live press).

⭐ **FINDING A TIER-B REPO COSTS NOTHING — TWO ARE ALREADY ON THIS MACHINE**, both carrying a
`LICENSE`, both real third-party harness repos installed as marketplaces:
`Yeachan-Heo/oh-my-claudecode` and `openai/codex-plugin-cc`.

⚠ **AND MEASURING THEM TODAY, BEFORE ANYTHING IS BUILT, ALREADY YIELDS TWO FINDINGS:**

1. **Neither has ANY of the four document paths `brief`'s ground-truth list looks for**
   (`docs/backlog.md`, `docs/roadmap-to-launch.md`, `docs/reviews/`, `docs/superpowers/`), and
   neither has a `.claude/` directory. So the hollow-page failure (§6's pass condition) is the
   *expected* outcome in a real repo, not an edge case.
2. ⟳ **CORRECTED 2026-10-16 BY ROUND 3 (CODEX B1), WHICH REFUTED THIS ITEM'S FIRST VERSION — and
   the refutation is worth more than the claim was.** It read: *both have a `scripts/` directory,
   so the three CWD-relative invocations silently run the wrong neighbour's file, which is strictly
   worse than a missing file.* ⛔ **THE SECOND HALF WAS NEVER OBSERVED.** Both repositories do have
   a `scripts/` directory — and **neither contains either target file.**

   **Re-measured 2026-10-16 from inside each clone** (`omc` at `679b418`, `openai-codex` at
   `807e03a`), running `brief-compose.py` and `explainer-serve.py` in each — **4 of 4 exit `2`**
   with `can't open file …: [Errno 2] No such file or directory`.

   **So what is measured is a LOUD failure in both real repositories.** A silent wrong-neighbour
   run needs a collision at the **file** name, not at the directory name, and neither repository
   has one. The mechanism is unchanged and so is the remedy — a CWD-relative path is answered by
   whatever the caller's working directory holds — but ⛔ **a possible failure class was written
   down as a measured result, and `hardcode-only-what-fails-loudly` was cited for a case that had
   not happened. That is the defect this whole spec exists to find, committed by the spec.**

⚠ **A tier-B CONSTRAINT, stated so it is not discovered late:** both are **shallow clones (1
commit)**, so every ground-truth item that reasons over git history is unsatisfiable there for a
reason that has nothing to do with portability. A tier-B run needs a full clone, and a failure under
a shallow one is **not evidence about the suite**.

**Tier-B selection criteria, so the choice is not ad hoc:** a permissive licence; a full (not
shallow) clone; an AI-harness layout of its own; and **no write of any kind back to it** — the
experiment runs against a local clone and pushes nothing, which also keeps the licence question
(C5) separate from the portability one.

**What is recorded:** every failure, its cause, and whether the scan predicted it. The experiment's
output is two lists — defects in the suite, and defects in the scan. ⚠ For a tier-B run, a third:
**resources it reached that belong to the host repo rather than the package**, which is the
wrong-neighbour case above.

⚠ **Bound, stated rather than hidden:** the experiment covers the comprehensibility suite only. It
says nothing about efforts (1) and (2), whose verdicts therefore rest on C1–C3 plus argument, and
**must be labelled as such in the inventory.** An install experiment for those is out of scope here
and is a candidate follow-up if either survives.

---

## 7. What PR 1 produces

0b. ⭐ **The ISOLATION BASELINE, written before the spike runs (added by r2 CLAUDE H2).** A document
   naming the interpreter version, the package set, the available commands, the network policy, and
   **what the capture mechanism cannot observe**. ⛔ **§6 REQUIRED a baseline and nothing produced
   one** — which is round 1's Blocking B3 (*"§5 requires a declared shipping set; nothing in §7
   produces one"*) recurring one round later in the same pair of sections. It is **first**, because
   the spike is the first thing that needs an environment to run in. ⟳ It is also now *printed*
   first: it claimed to precede item 0 while appearing after it, and the list carried **two** copies
   of item 1 as a result (found while folding r3).
0. ⭐ **A packaging spike, BEFORE the scan is written (added by r1 CLAUDE M5, r1 CODEX 10).** One
   skill and one script, packaged into a throwaway local marketplace, installed under a fresh `HOME`
   and invoked from an unrelated directory. It discharges D3's packaging assumption (§2) and builds
   the isolated environment §6 needs. ⛔ **If it fails, D4 is unachievable and §9's third falsifier
   has fired** — so it runs early, when that is still cheap to act on.
1. This spec, reviewed and committed.
2. ⭐ **The shipping-set declaration (added by r1 CLAUDE B3, r1 CODEX 2)** — per publishable unit,
   as **data the scan reads**, listing member files with symlinks resolved and an expected file
   count per component.
   ⛔ **WHO DERIVES IT AND WHAT VALIDATES IT (r2 CLAUDE H1 — §5 asserted this item named both, and it
   named neither):** it is derived from the **installed package tree** produced by item 0's spike, by
   a step that **never reads the scan's output**; and it is validated by a third check that walks the
   dependency closure of the installed tree and refuses a declaration missing any member the closure
   reaches. **Three different producers, so no oracle checks its own output.**
   ⚠ Nothing in the original nine deliverables produced this at all, so the scan had only two options
   at build time: CANNOT RUN for all 24 components, which empties deliverable 5, or infer the set —
   the condition §5 warns about, with no gate on the inference.
3. `scripts/check-publishability.py` + `--self-test` + mutation manifest + CI registration,
   **including the empty-set mutation §5 requires.**
3b. ⭐ **THE EXPERIMENT'S OWN ARTIFACTS — ADDED 2026-10-16 BY r3 CLAUDE H2, WHICH FOUND THREE OF
   THEM REQUIRED BY §6 AND PRODUCED BY NOTHING.** Item 4 is the experiment's *record*, i.e. its
   output; it does not build the things the run needs. ⛔ **This is the shape item 0b exists because
   of** — *§6 required a baseline and nothing produced one* — and by the spec's own standard these
   were instances three, four and five of it:

   | Required by | The artifact |
   |---|---|
   | §6 (*"a SEEDED stranger repository with KNOWN facts"*) | **the seeded repository**, built here, so *correctly empty* is distinguishable from *broken* |
   | §6 (*"neither replaces the other, and the order matters"*) | **the tier-B run** against a real third-party clone — ⚠ §10 defers only *an install experiment for efforts (1) and (2)*, never this one |
   | §6 | **the entry-point coverage matrix**, bounding what the run actually exercised |

4. The install-experiment record: failures found, which the scan predicted, and — ⟳ **CORRECTED by
   r3 CODEX M6** — **the resource record the capture mechanism of §6 can actually produce, together
   with what that mechanism cannot see.** The earlier wording demanded *"every resource the run
   touched"*, which is the exhaustive requirement **§6 explicitly retired** as *"an
   aspiration with no implementation"*; restoring it here made the two sections impossible to
   satisfy at once. ⚠ An unobservable access is **declared unobservable**, never counted as absent.
5. **The inventory** — every component of all three efforts with its **role**, its `SHIP` /
   `NEEDS-WORK` / `DON'T-SHIP` verdict, and its evidence. ⚠ Components whose C4 rests on argument
   rather than the experiment are labelled as such (§6's bound).
6. A roadmap milestone, and a `docs/backlog.md` row per `NEEDS-WORK` component — **and only those**.
   ⚠ Under D5 (§4b) `NEEDS-WORK` means *a named defect*, so neither a `library` that inherits a C4
   pass nor a component the experiment simply never reached (`argued`) generates a row. **A row means
   a defect someone can act on**, which is what the original rule produced phantom entries against.
7. `docs/anchors.md` — `harness-ships-elsewhere` registered, claimed by this document. **Closes row 290.**
8. Corrections to `portable-practices.md` — ⟳ **SUBJECT REPLACED 2026-10-16 by round 3 (CODEX B2),
   AND THE DECISION ABOVE IT SURVIVES THE REPLACEMENT.**

   ⭐ **D8 — A CORRECTION LANDS WITH THE WORK THAT FOUND IT, NOT IN A SEPARATE PR. Decided
   2026-10-16 by the owner**, asked through the walkthrough page: *"yes, fix in here."* The reason
   is that **the inventory is what discovers them**, and a correction separated from the evidence
   that found it tends not to land.

   ⛔ **BUT THE THREE CLAIMS IT WAS DECIDED ABOUT WERE ALREADY FIXED** — in `b200f2cf` (PR #377),
   merged to master and present on this branch since its rebase (§3). **The owner answered a
   question whose subject no longer existed**, which is recorded here rather than quietly repaired,
   because *"the inventory found three stale claims"* was itself a stale claim. ⚠ D8 is a rule about
   **placement**, so it is unaffected by which corrections are outstanding; only the list changes.

   **What D8 actually delivers — all three still present in the index today, all three measured.**
   ⚠ This read *"both"* until r3 CLAUDE H4 pointed out that §3 diagnoses a third defect **thirteen
   lines above** the sentence that sends the reader here, and the list it sends them to did not
   carry it. The incompleteness that made B2 necessary, one layer in:

   | The index says | Why it is wrong | Measured against |
   |---|---|---|
   | the old figure *"undercounted its own subject by roughly 3x"* | **3x is a CROSS-SET ratio.** The subject of `3,599` was the **nine** enumerated files, which are **6,542** at `a4f6d4b5` — **1.82x**. The ~11,000 is a **different and larger set** (17 components), and §3 forbids comparing the two without saying so | §3's own three-stage table |
   | *"The problem is concentrated in one file"* | already **measured false** — `explainer-delivery.md` scores **0** on the vocabulary detector and still carries three CWD-relative invocations, so the C3 defect is in the file presented as the good news | §4 (r1 CLAUDE H5) |
   | ⟳ the replacement headline *"~11,000 lines"* and its *"10,373 across six files"* | **the corpus disagrees with the enumeration in its own sentence** — ADDED by r3 CLAUDE H4, which found this list incomplete the same way §3's list was. `1780+2907+450+438+3546+1252 = 10,373`, `+604 = 10,977`: a set that **omits the three shared contracts** (`wc -l` at `a4f6d4b5` → `363 + 73 + 211 = 647`), one of which that very sentence names, while **including the two generators' 4,798 lines**, which the enumeration lists only as four shell hooks. The spec's own full-set figure is **11,624** (§3) | §3, thirteen lines above the pointer that sends the reader here |

   ⚠ **ALL THREE are one-line repairs, and the second is a C3 conclusion a C2 measurement cannot
   support** — which is the same confusion §4 records, appearing once more in the index. ⟳ This said
   *"Both"* until r4 CODEX M3: the third correction was added to the table above and **never reached
   the acceptance condition below it**, so a change fixing only the first two would have satisfied
   the bound while leaving the defect the table had just named. **The propagation defect, inside the
   replacement for the propagation defect** — and the fourth round running in which this one
   mechanism has produced the findings.

   ⛔ **THE COUNTER THE OWNER WEIGHED WAS REAL, SO THE BOUND STANDS, AGAINST THE NEW LIST.** The
   objection: if this milestone stalls, known-wrong sentences stay published for as long as it does.
   **All three repairs are docs-only and depend on nothing else in PR 1**, so they go in as
   its **first commit** and are mergeable alone. **The observation that makes this bound FAIL: PR 1
   open with ANY OF THE THREE corrections not yet committed** (⟳ r4 CODEX M3 — this read *either*,
   over a list of three). At that point the stall risk the owner accepted is live
   and the corrections should be split into their own PR.
9. The scoring rubric as a `portable-practices.md` entry — a reusable publishability test is itself a
   D2 contribution, and this milestone is the measurement that earns it.
9b. ⭐ **THE HARVEST (D6, §4c)** — for every component, a `harvest` field, and for every
   `harvest: practice` a **named entry in `docs/portable-practices.md`** carrying the measurement
   that earned it. ⚠ A practice asserted without an entry is `harvest: none`, and a harvest never
   upgrades a verdict. This is the deliverable that makes a `DON'T-SHIP` component still worth
   having evaluated.
10. A dashboard entry.
11. ⛔ **THE C5 CONTENT REVIEW OF EFFORT (1)'s MEMORY FILES (159 at HEAD, 157 on `master`; the §3 row names the producer) — THE OWNER'S, AND A DELIVERABLE
   RATHER THAN A GAP (r3 CLAUDE H2).** Do those files hold private content, credentials, or
   third-party material that may not be redistributed? ⚠ **This cannot be delegated**: the judgement
   about what is private is the owner's, and nobody else can make it.

   ⛔ **AND IT WAS QUIETLY MAKING DELIVERABLE 5 IMPOSSIBLE, WHICH IS WHY IT IS LISTED RATHER THAN
   ASSUMED.** C5 is a **veto** (§4): a component cannot be `SHIP` with C5 unanswered, it grades
   `measured` or blocks. §4's role table grades a `data` component against **C1–C3 and C5**. §4
   also calls C5 *"not yet answerable"*. So the memory corpus could not be graded at all, while
   deliverable 5 promised *every* component a verdict and §4b said it *"is not done until every row
   has one"*. **Three rules that cannot all hold.**

   ⭐ **RESOLVED BY DECLARING THE INCOMPLETENESS INSTEAD OF HIDING IT:** the corpus's row carries
   **`C5: unanswered — blocked on the content review`**, which satisfies §4b's completeness rule the
   way a *struck* C4 does — by being a stated disposition rather than a missing cell. It is **not**
   a verdict, and ⛔ **the corpus cannot be `SHIP` until the review lands.** The observation that
   makes this fail: an inventory row for the corpus carrying a `SHIP` verdict while item 11 is
   outstanding.

**What PR 1 explicitly does NOT do:** publish anything, create the **published** marketplace repo, or
fix any coupling — including `brief/SKILL.md`'s **nine repo-specific ground-truth items** (4 bare
guard names, 4 document paths, 1 tool name — *not* nine `scripts/check-*` invocations; see §4) and
the three CWD-relative invocations in `explainer-delivery.md`. Fixing a component while also judging
it is how this repository has previously manufactured a false green, and the owner chose option A
specifically to keep evaluation independent of repair.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| The scan becomes an opinion in script form | §5's falsifier: the install experiment can declare the scan defective |
| The inventory is written from recall and drifts | Every count derived by command, dated, and the derivation recorded beside it |
| A derived count DECAYS as its subject grows — the actual 9-files failure (r1 CLAUDE H1) | Every count carries its date and its file set, so a stale figure is visibly stale rather than wrong; §3's banner states this |
| A count is taken over the wrong set, and reproduces | §3's counting rule fixes membership before arithmetic; §5 asserts a non-zero expected file count per component. ⚠ This spec reached a correct total over a wrong set twice in round 1 |
| Efforts (1) and (2) get weaker verdicts than (3) | Stated as a bound in §6 rather than hidden; their verdicts are explicitly labelled argument-based |
| The milestone becomes "publish everything" by momentum | `DON'T-SHIP` is a first-class verdict; a component that fails C1–C4 is recorded as such, and that is a successful outcome of this work |
| **11,624 lines** — the 17 components of effort (3), per §3's derivation at `a4f6d4b5` — is too much to assess per line | Assessment is per component against five criteria (§4), not per line. ⟳ This row said *"~11,000"* until r3 CLAUDE M1: the same subject carried two figures 5.2% apart, and §3's own closing warning — *that is a different and larger set, and the two must not be compared without saying so* — is exactly what this row was then doing silently |

## 9. Falsifiers

- **For the inventory:** a component marked `SHIP` that the install experiment cannot run.
- **For the scan:** a blocker **or a degraded result** the experiment hits on a component the scan
  scored clean (§5).
- **For the scan's completeness:** a component whose resolved file set is empty or smaller than its
  declared count, and which the scan still scored (§5's companion rule).
- **For D3's packaging assumption:** §7 item 0's spike cannot package one skill and one script onto a
  local marketplace and invoke them from elsewhere. D3 claims the route is proven; it is not proven
  that **this artifact** can travel it (r1 CLAUDE M5, r1 CODEX 10).
- **For this spec:** if the install experiment cannot be made to run at all, D4 is unachievable and the
  method must be re-decided with the owner rather than silently downgraded to paper scoring.
- **For D9's support bar (§4d):** a release of the published package with **no version tag**, a tag
  with **no `CHANGELOG` entry**, or ⟳ **a breaking change with no major-version bump** (r3 CODEX M1
  — the third promise, missing from the first version of this bullet). ⚠ **All three are
  observations about a RELEASE, and PR 1 produces none**, so this falsifier becomes checkable at
  first publication and cannot fire inside this milestone.

## 9b / 9c. Provenance — moved out of this document

⟳ **MOVED 2026-10-16 BY ROUND 3 (CLAUDE, the readability finding).** What the spec self-review
caught in this document, and what round 1's dual review found, now live in
[`docs/reviews/coordinator/marketplace-inventory-r3-coordinator.md`](../../reviews/coordinator/marketplace-inventory-r3-coordinator.md)
— **verbatim, nothing deleted and nothing summarised.**

⛔ **WHY THEY MOVED RATHER THAN BEING CUT.** The attribution is why this spec is trustworthy, so it
must not disappear; but it is written to *reviewers*, and this document's one job is to be approved
by its owner. r3 measured the problem rather than asserting it: **166 of 1,059 lines — about one in
six — opened with an emphasis glyph**, and the spec was reading in two registers at once.

## 10. Out of scope, named so the gap is not read as closed

Official-marketplace submission (D3); creating the **published** marketplace repository — ⚠ *not*
the throwaway local marketplace §6 and §7 item 0 require, which is a different artifact (r1 CLAUDE
H2, r1 CODEX 7); fixing any coupling; building Q0; merging the two recall branches
(`c5-recall-matcher`, `backlog-117-parser-substrate`); and an install experiment for efforts (1) and
(2). ⚠ **And the release mechanics D9 (§4d) requires — the version tag and the `CHANGELOG` — land
with that deferred repository, not with PR 1**; what PR 1 owes is the stated bar, nothing more.

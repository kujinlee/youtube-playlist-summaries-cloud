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
*"Can a stranger use this?"* is a surface question over **24 components** (17 + 3 + 4 — the counting
rule and the per-effort enumeration are in §3, derived 2026-10-15). Judgement alone will miss things,
and the misses are precisely the ones a stranger meets first.

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

⚠ **The TOTAL is unchanged at 24 and its MEMBERSHIP is not.** Round 1 found effort (1)'s list was
counting two unmerged branches and omitting the matcher that actually ships (see Effort (1) below),
so a total that reproduced was standing over a wrong set — which is this repository's most-measured
failure shape, reached here by arithmetic that happened to agree.

### Effort (3) — comprehensibility

| Component | Lines |
|---|---|
| `explain-diff` / `brief` / `explain-findings` / `explain-topic` (SKILL.md) | 158 / 195 / 156 / 95 |
| `.agents/skills/shared/` — `explainer-delivery.md`, `corpus-search.md`, `handoff-path.md` | 346 / 73 / 211 |
| `scripts/brief-compose.py` | 1,780 |
| `scripts/explainer-serve.py` | 2,907 |
| `scripts/page_chrome.py` / `scripts/page_markup.py` | 450 / 438 |
| `scripts/gen-dashboard.py` / `scripts/gen-goals-page.py` | 3,546 / 1,252 |
| `.claude/hooks/regen-{backlog-page,dashboard,features-page,goals-page}.sh` | — |

⛔ **A FINDING BEFORE THE WORK STARTS: the D2 index figure has DECAYED, and it is 1.81x low
against its own file set.** ⟳ **CORRECTED 2026-10-16 by round 1 (CLAUDE H1), which refuted this
paragraph's first version — and the refutation is the more useful finding.**

`docs/portable-practices.md` describes the suite as *"9 files / 3,599 lines"* and **enumerates those
nine**: the four page-producing skills, the shared delivery contract, `brief-compose.py`,
`explainer-serve.py`, `page_chrome.py`, `page_markup.py`.

⟳ **CORRECTED AGAIN 2026-10-16 by round 2 (CODEX 9), which found round 1's own history wrong.**
Round 1 said `100cf498` *"introduced the figure"* and that it was *"accurate when written"*. The
figure was introduced four days earlier, and there are **three** stages, not two:

| Stage | Commit | The same nine files measured | Verdict |
|---|---|---|---|
| **originally measured** | `cacbac17`, 2026-09-03 | **3,599** | **exactly right** |
| **republished into the index** | `100cf498`, 2026-09-07 | 3,737 | already **3.7% stale** |
| today | `HEAD` | **6,525** | **1.81x** low |

⛔ **SO THERE ARE TWO FAILURE MODES HERE, AND THE SECOND IS THE ONE WORTH CARRYING.** The count
decayed (3,599 → 6,525, 1.75x growth). But it also **arrived in `portable-practices.md` already
stale**, because it was *copied from an earlier measurement into a fresh-looking declaration without
being re-measured*. A republished figure inherits staleness **and loses the fact that it is
inherited** — the new document reads as a new measurement. That is a sharper rule than *date your
counts*: ⭐ **a count copied from elsewhere must carry the commit it was measured at, not the commit
it was written into.**

- The first version of this paragraph compared 3,599 against **10,977** — a set of its own
  construction that adds `gen-dashboard.py` and `gen-goals-page.py` (**4,798 lines, 46% of the
  Python total**), neither of which is among the nine. That is a **3.05x cross-corpus ratio**.
- The first version of this paragraph compared 3,599 against **10,977** — a set of its own
  construction that adds `gen-dashboard.py` and `gen-goals-page.py` (**4,798 lines, 46% of the
  Python total**), neither of which is among the nine. That is a **3.05x cross-corpus ratio**.

⛔ **SO THE DIAGNOSIS CHANGES, AND THAT MATTERS MORE THAN THE NUMBER.** The figure was **derived,
enumerated, dated and correct** (`portable-practices.md:17` says *"Enumerated in `docs/backlog.md`
row 89, not recalled"*, and row 89 contains the enumeration). It was not written from recall. Its
subject then grew 1.75x. **The failure mode is a dated count decaying, not a count invented** — and
§3's own banner already handles decay. **Correcting it is in scope for this milestone**, and the
correction must record *that* reason.

⚠ **AND THIS PARAGRAPH WAS ITSELF A CORRECT MEASUREMENT OVER THE WRONG CORPUS** — placed in the
finding whose entire purpose was to shame that defect. It is left on the record rather than quietly
rewritten, because it is the best available evidence for why §5's CANNOT-RUN rule needs the
companion that B3 forced (see §5).

**The total, for scope sizing only:** 10,373 Python + 604 skills + 630 shared contracts =
**11,607 lines** across the 17 components of effort (3). ⚠ That is a different and larger set than
`portable-practices.md`'s nine, and the two must not be compared without saying so.

⚠ Two further claims in that same block are stale and must be corrected with it: it says the registry
*"registers 10 anchors"* (it held **13** before this spec, and **14** after it, since this document allocates one) and that *"a second anchor is owed"* for the present-tense
reader (`explanation-on-demand` now exists).

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
| the memory corpus | 157 files | outside this repo |

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
| **C4** | **Supportable** — a stranger can install it, use it, and recover from failure without the author | ⛔ **not countable** — this is what the install experiment is for |

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
| `data` | supplies content (e.g. the memory corpus) | not applicable; C4 is recorded as `n/a` |

⚠ **A component may hold BOTH `entry-point` and `library`** — a module that is executable *and*
imported is not a third role, it carries two, and is assessed as an entry-point while also supplying
inherited evidence. Round 2 found the single-role table could not express this (CODEX 3).

⛔ **INHERITANCE NEEDS AGGREGATION, COVERAGE AND PROVENANCE RULES, AND ROUND 1'S VERSION HAD NONE
(r2 CODEX 3, High, INTRODUCED BY ROUND 1'S FIX).** *"Inherits from the entry-points that import it"*
is undefined the moment there is more than one, and silently wrong when there are none:

| Situation | Rule |
|---|---|
| imported by entry-points that **all** pass | inherits the pass, grade `inherited` |
| imported by a **mix** of passing and failing entry-points | **inherits the FAILURE.** A library implicated in any entry-point's failure is not carried by the others |
| imported by **no** entry-point | **no inheritance is possible** — grade `none`. ⚠ An orphan library is also a scope question: ask why it is shipping at all |
| part of an **import cycle** | graded by the entry-points at the cycle's boundary; a cycle with no entry-point outside it is `none` |

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
- ⛔ **AND "the problem is concentrated in one file" IS FALSE (r1 CLAUDE H5).**
  `.agents/skills/shared/explainer-delivery.md` scores **0** under the vocabulary detector — and
  carries **three repo-relative `python3 scripts/...` invocations** resolved from the caller's CWD.
  It is the contract **all four** page-producing skills route through, so in a stranger's repo those
  resolve to nothing, or to an unrelated neighbour's `scripts/`. That is a C3/C4 blocker for every
  component of effort (3), and it sits in the file this spec previously presented as the good news.
  The existing measurement is C2-only; "concentrated in one file" is a C3 conclusion that a C2
  measurement cannot support.

**Verdicts are per component, and there are exactly three:** `SHIP`, `NEEDS-WORK` (with the named
defect), `DON'T-SHIP` (with the reason). A fourth verdict — "unknown" — is not permitted; a component
that cannot be assessed is `NEEDS-WORK` whose named defect is *"no way to assess it"*. ⚠ **That rule
now bites only where assessment is genuinely impossible**, because the role table above removes the
case where it was firing on `library` components by construction.

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
**That is this decision's falsifier:** if the inventory is read and acted on as though `argued`
meant `measured`, the two-axis scheme has failed and the stricter alternative — requiring
`measured` or `inherited` for `SHIP` — is the fallback. The inventory must therefore render the
grade **beside** the verdict, never in a footnote or a separate table.

---

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
   **reported separately** from dependency findings and never alone decide a verdict.
2. ⭐ **Detector 6 — runtime prerequisites (added by r2 CODEX 6).** A generic Python import of an
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
- **carry three mutations**, each dying via the case it names: one that **empties** a component's
  set, one that **substitutes** a member while preserving cardinality, and one that **omits** a
  dependency and writes the count to match. ⚠ The empty-set mutation alone cannot expose
  substitution — round 1 required only that one.

⚠ **This spec's own component table now names `.agents/skills/shared/` (the real directory) rather
than the symlink path**, so the measured failure above cannot be reached from §3 as written.

**Its falsifier, which is the point of D4:** any blocker the install experiment hits on a component
the scan scored clean is a **scanner defect**, fixed in the scan, not recorded as a footnote. The scan
is not permitted to be an opinion in script form.

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
4. ⭐ **one documented RECOVERY scenario succeeds**, because C4 says *"recover from failure without
   the author"* and no part of the original method tested recovery at all;
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

**What is recorded:** every failure, its cause, and whether the scan predicted it. The experiment's
output is two lists — defects in the suite, and defects in the scan.

⚠ **Bound, stated rather than hidden:** the experiment covers the comprehensibility suite only. It
says nothing about efforts (1) and (2), whose verdicts therefore rest on C1–C3 plus argument, and
**must be labelled as such in the inventory.** An install experiment for those is out of scope here
and is a candidate follow-up if either survives.

---

## 7. What PR 1 produces

0. ⭐ **A packaging spike, BEFORE the scan is written (added by r1 CLAUDE M5, r1 CODEX 10).** One
   skill and one script, packaged into a throwaway local marketplace, installed under a fresh `HOME`
   and invoked from an unrelated directory. It discharges D3's packaging assumption (§2) and builds
   the isolated environment §6 needs. ⛔ **If it fails, D4 is unachievable and §9's third falsifier
   has fired** — so it runs first, when that is still cheap to act on.
1. This spec, reviewed and committed.
2. ⭐ **The shipping-set declaration (added by r1 CLAUDE B3, r1 CODEX 2)** — per publishable unit,
   as **data the scan reads**, listing member files with symlinks resolved and an expected file
   count per component. ⛔ Nothing in the original nine deliverables produced this, so the scan had
   only two options at build time: CANNOT RUN for all 24 components, which empties deliverable 5, or
   infer the set — the condition §5 warns about, with no gate on the inference.
3. `scripts/check-publishability.py` + `--self-test` + mutation manifest + CI registration,
   **including the empty-set mutation §5 requires.**
4. The install-experiment record: failures found, which the scan predicted, **and every resource the
   run touched** (§6).
5. **The inventory** — every component of all three efforts with its **role**, its `SHIP` /
   `NEEDS-WORK` / `DON'T-SHIP` verdict, and its evidence. ⚠ Components whose C4 rests on argument
   rather than the experiment are labelled as such (§6's bound).
6. A roadmap milestone, and a `docs/backlog.md` row per `NEEDS-WORK` component. ⚠ A `library`
   component that inherits a C4 pass does **not** generate a row (§4).
7. `docs/anchors.md` — `harness-ships-elsewhere` registered, claimed by this document. **Closes row 290.**
8. Corrections to `portable-practices.md`'s three stale claims (§3 above) — **the line-count one
   recorded as a decayed dated count, not as a recalled figure** (r1 CLAUDE H1).
9. The scoring rubric as a `portable-practices.md` entry — a reusable publishability test is itself a
   D2 contribution, and this milestone is the measurement that earns it.
10. A dashboard entry.

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
| ~11,000 lines is too much to assess per line | Assessment is per component against four criteria, not per line |

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

## 9b. What the spec self-review caught in this document

Recorded rather than silently fixed, because this spec argues for derived numbers and was itself
written with an invented one.

- **"~13 components" was invented.** The derived figure is **24** (17 + 3 + 4). Nothing depended on
  13; that is the point — a number with no provenance passed straight into a design document whose
  §8 lists exactly this drift as a risk.
- **"the strongest candidate" was ambiguous** in D4 while §6 named the comprehensibility suite
  explicitly. D4 now names it too.

## 9c. What round 1 caught — dual adversarial review, 2026-10-16

Both halves returned **NOT CONVERGED**: Codex 4 Blocking / 6 High / 1 Medium, Claude 3 Blocking /
6 High / 6 Medium / 2 Low. Full documents:
`docs/reviews/codex/marketplace-inventory-r1-codex.md`,
`docs/reviews/claude/marketplace-inventory-r1-claude.md`.

⭐ **The four Blocking defects, and what each one was really about:**

1. **The component list omitted the mechanism the evidence endorses.** `scripts/recall-llm.py`,
   2,550 lines, on `master` — absent, while the lexical matcher the same paragraph rejects was the
   only thing listed. §3's instruction was unexecutable against §3's own scope.
2. **`CANNOT RUN` guarded the wrong failure.** It fires when a set cannot be resolved; the
   dangerous case is a set that resolves **successfully and incompletely**. Reproduced against this
   spec's own stated paths: a walk over `.claude/skills/shared/` finds nothing, because the entries
   are git symlinks and `grep -r` does not follow them — a clean score over an empty set.
3. **The experiment could pass by inheriting the author's machine.** `~/explainers/` is a symlink
   into this repository, so the composer finds a usable page that a stranger has none of.
4. **The pass condition could not fail in the way that matters.** All nine ground-truth items can
   return nothing, a page still composes and serves, Ask still works — a hollow page scoring `SHIP`.

⚠ **AND ROUND 1 REFUTED THIS DOCUMENT'S OWN HEADLINE FINDING**, which is the most useful thing it
did. The *"3x undercount"* was a cross-corpus comparison; same-set the figure was **accurate within
3.7% when written** and is **1.81x** low today. So the lesson drawn from it — *written from recall* —
was wrong, and §8's risk row was mitigating a failure this case is not an instance of. The real
failure is **a dated count decaying**. See §3 and §8.

⚠ **Two numbers in the walkthrough page were produced by nothing** and are corrected with the spec:
`346s` for the sharding result (`ci.yml` records `1758s → 353s`, measured on one machine
2026-10-05; `346` appears nowhere in the repo, and a prior review half had already filed it as a
defect), and *"15 document guards"*, a denominator that exists nowhere.

⛔ **ONE FINDING IS DELIBERATELY NOT FOLDED** — whether `SHIP` may be recorded without demonstrated
C4 evidence. It changes what this milestone promises rather than how it is reached, so it is the
owner's decision and is stated as an open question in §4.

## 10. Out of scope, named so the gap is not read as closed

Official-marketplace submission (D3); creating the **published** marketplace repository — ⚠ *not*
the throwaway local marketplace §6 and §7 item 0 require, which is a different artifact (r1 CLAUDE
H2, r1 CODEX 7); fixing any coupling; building Q0; merging the two recall branches
(`c5-recall-matcher`, `backlog-117-parser-substrate`); and an install experiment for efforts (1) and
(2).

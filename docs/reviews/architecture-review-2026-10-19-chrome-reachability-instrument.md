# Architecture review — the instrument for a reachability claim (PR #378, backlog #300)

> **Anchor:** `review-decides-itself` — **ADR:** 0014
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

**Armed by THRASHING**, per `docs/dev-process.md` Phase 6: *two consecutive rounds whose findings
came from the previous round's own fix, in one component*. Convened on the `chrome-bar-reachable`
branch at `271818c9` (36 commits, open as PR #378, NOT CONVERGED after eight rounds).

**The anchor is not decoration here. This review's sharpest finding is that the loop under review
violated the goal above** — it reached the human for a decision that is written nowhere as the
human's, and it did so for five consecutive rounds.

⚠ **Every number in this document was produced by running something, and the command is named.**
That rule is not boilerplate: four numbers published on this branch were wrong, and one of them was
a *correction* of an earlier wrong number. See finding **F5**.

---

## The question put to this review

**Should the reachability claim move from a text predicate to a rendering assertion?**

*Reachability* is the property **a reader can actually reach the theme and text-style controls on a
generated page**. It depends on document height, viewport, container padding, bar wrapping and
scroll position. Today it is asserted by `page_chrome.assert_wired` and the predicates under it,
which read the emitted HTML/CSS/JS **as text**.

Inventory, as `dev-process.md` requires: `docs/reviews/coordinator/chrome-bar-reachable-r5-coordinator.md`
and `…-r6-coordinator.md`, plus the eight rounds' halves under `docs/reviews/{claude,codex}/`.

## The answer

**Route (b) SPLIT, per the taxonomy backlog #136 already defines.** Merge the delivered feature;
make the instrument its own designed slice. Concretely:

1. **The owner's complaint is fixed** and browser-verified on all five producers. That work ships.
2. **The instrument question (A/C) becomes a separate, designed slice** — not a fold inside this
   loop. #136's own measured lesson (4) is that *a fix introducing a new artifact restarts that
   artifact's clock rather than riding the current round*; a Playwright gate introduced as round 9's
   fold would arrive with zero design work, which is the exact shape that cost PR #313 three rounds.
3. **Candidate D is already adopted** and needs no further work (`scripts/page_chrome.py:30-70`).
4. **Nothing further is folded into `scripts/` on this branch.** That is also what clears the PR's
   last red — see *The terminating move*, which required no owner decision and was available for
   five rounds.

**And the instrument question IS answered: C.** I had planned not to choose it here, on the grounds
that choosing inside a review round is the error this document exists to stop. **Both halves chose C
independently, from different evidence, and the reasons are better than the inventory's** — so the
direction is settled and only the *implementation* is deferred to row 304. That is still route (b):
#136's (b) says ship the stable half and make the unstable half its own item; an item may carry a
recommended direction, and withholding one the review actually established would be a worse
document.

Why not the others, taking the Claude half's grounds because they are measured rather than argued:

* **A** — *"C minus the half that works."* The text layer catches the generator-mistake class its
  bound declares, in **0.53 s** (`time python3 scripts/page_chrome.py --self-test`), and a browser
  gate cannot practically cover 20 fragments × 5 producers × every scroll position. Discarding it
  buys nothing.
* **B** — refuted by B1. The parse gate catches the brace and **misses a 17-byte addition**.
  *"Layout is unverified by construction"* is true of a text predicate and **false of this
  repository**, which ships Playwright, 14 e2e specs, and a config with no `webServer` at all.
* **D** — the status quo, implemented and witnessed. Choosing it is choosing B.

⭐ **AND THE COST OF C IS LOWER THAN BOTH THE r5 NOTE AND MY OWN F3 ESTIMATED, with the precedent
already in the repo.** `playwright.prod.config.ts` is exactly the needed shape and says so —
*"it has **NO `webServer` AT ALL**. There is nothing to start."* — and is already wired as a gate
(`npm run test:e2e:prod`). The stated reason `test:e2e` is not in CI (*"need a live Supabase
stack"*) does not apply to a chrome spec, which needs no server. **The real cost is not CI; it is
mutation coverage** — see the corrected F3 and the Claude half's M4, which names the precise
mechanism I had only gestured at.

---

## F1 — Blocking · structural. Text and parse instruments both accept a page whose controls are dead, and the gate added for this class does not close it

**This is the decisive measurement and it is new.** The r6 note's version of this argument rests on
a dropped brace — invalid JavaScript behind a green suite. Round 6 closed that with a real
`node --check` (`scripts/page_chrome.py:2093`). **The instance is closed; the class is not.** A
*runtime* fault is syntactically valid, so it passes the parse gate, passes every substring
assertion, and leaves every control off-screen.

Measured by me, with my own fixture (`runtime-throw-probe.py`, `browser-probe.mjs`), on a page built
from this branch's own `chrome_css()`, `chrome_bar()` and `chrome_script()` composed the way
`gen-dashboard.py:1219/1370/1390` composes them, at 320×568 scrolled to y=2000:

| Artifact | `assert_wired` | `node --check` | theme button top | in viewport | bar `position` | page errors |
|---|---|---|---|---|---|---|
| unmodified | **ACCEPTS** | **PASS** | `8.19` | **yes** | `fixed` | 0 |
| one prepended `throw` | **ACCEPTS** | **PASS** | `−1912.94` | **no** | `static` | 1 |

The only change is one syntactically valid statement. Two of three instruments cannot see it.

⚠ **PROVENANCE, because this matters more than the result.** The Codex half ran the same experiment
independently and reported `−1926.38`; I reproduced it at `−1912.94`. The figures differ because the
filler differs, and **neither number is a property of the product** — the finding is the
*disagreement between instruments*, not either coordinate. Do not cite either number as a
measurement of the page.

⚠ **My own first fixture was WRONG and `assert_wired` caught it** — it omitted both theme palettes
and the guard rejected it with the correct explanation. Recorded because it is evidence *for* the
text instrument within its declared subject, and against reading this finding as "the guard is bad".

**What this does and does not license.** It refutes "nothing further is needed" (candidate B as
stated). ⛔ **THE SENTENCE THAT STOOD HERE IS WITHDRAWN AND THE WITHDRAWAL IS THE POINT.** It read:
*"executing the script under Node — rather than only parsing it — would close this specific class
far more cheaply, and nothing in the inventory considers that option."* The Claude half considered
it, ran it with `jsdom`, and it **false-greens the silent case** (H3 below). The proportionate
remedy is smaller still — a one-line *no page errors* read — and it closes only the noisy member of
the class. Filed, corrected, as row 305.

⛔ **SUPERSEDED IN STRENGTH BY THE CLAUDE HALF'S S8, AND THE DIFFERENCE MATTERS — my probe proves a
weaker thing than I thought it did.** A prepended `throw` raises a **startup error**, so the cheap
remedy above (execute the script) catches it, and a browser gate would catch it by reading the
console. S8 does not: appending `arm=function(){};` — **17 bytes** — leaves every asserted
expression verbatim and produces **no page error at all**, the button still toggles once reached,
and only *rendered reachability* fails. It therefore survives both my probe's remedy and a
console-watching browser check, and it does so **on a matched pair of real `gen-dashboard.py`
output** rather than on a hand-built fixture.

**So the correct statement of this finding is the Claude half's, not mine:** the suite is
**monotone in the source text** — a containment assertion can detect that an asserted expression
was *changed* or *removed* and is immune **by construction** to anything *added*. Rounds 6-8's
repair (exact contiguous expressions) strengthened only the direction that already worked, and
*addition* is the direction in which both *"something else also supplies it"* and *"something later
overrides it"* live — the shape every missed defect on this branch has had. My runtime-`throw`
measurement is retained because it is independent corroboration that two of three instruments can
report success over dead controls, and because it is what motivated row 305; it is **not** the
decisive datum. ⚠ The manifest shares the blind spot, measured by the Claude half: **31 additions
of 1,553 edits across 62 manifests (2.0%)**, so a sweep reporting *zero survivors* is fully
consistent with this defect being live — which is what r8's *112 killed / 0 survivors* means.

## F2 — High · structural. The arming condition fired at round 3, and five more rounds were folded because convening was blocked on an authority that is written nowhere

The thrashing condition was declared **met at round 3** — `docs/reviews/coordinator/chrome-bar-reachable-r3-coordinator.md:3`,
*"THRASHING OR PROSE FLOOR? — **THRASHING.** The condition in `dev-process.md` is met"* — in a commit
dated **10-18 15:50** whose subject says so (`03b78e94`). Rounds 4, 5, 6, 7 and 8 were then reviewed
and folded. The branch tip is dated **10-19 12:03**. That is **20 hours and five rounds** after the
process's own stop condition fired.

The r5 note says *"The Phase 6 architecture review armed at r3 is the right venue for this, and it
remains the owner's call. I have not convened it."* The r6 note repeats it: *"Not convened here;
`dev-process.md` makes it the owner's call, and this is the second round to say so."*

⛔ **`dev-process.md` does not say that.** Measured with `grep -ci "owner's call"` over the process
corpus:

| Document | `owner's call` | `conven*` |
|---|---:|---:|
| `dev-process.md` | **0** | 1 (a historical aside at `:120`) |
| `review-method.md` | **0** | 5 |
| `process-checklists.md` | **0** | 3 |
| `process-rationale.md` | **0** | 6 |
| `portable-practices.md` | **0** | 4 |

And the document **marks its human gates where it has them** — Phase 1's gate cell says *user
approval*; Phase 5's says *Merging is a human gate*. **Phase 6's gate cell assigns no human.** The
applicable written rule for a round that will not converge is in the Human-in-the-Loop policy:
*"The rule is **notify and continue**"*, with stop-and-wait allowed only if (a) the human replied,
(b) the next action is outward-facing or irreversible, or (c) the fix is not clearly specified.
Convening an internal architecture review is none of the three, and r5 had already specified the
options.

⭐ **This is not a new backlog item — it is the FALSIFIER of open backlog #184 firing.** That row
states its own falsifier: *"a subject's round documents show a decision that the card would have
answered differently, with no record that the card was consulted."* Two coordinator notes record
exactly that. #184 is therefore **witnessed, with a measured cost** — five rounds — and that belongs
on the row. Its sibling #136 owns the stop/continue rubric and already predicted this shape:
*"`review-method.md`'s 'diminishing returns' is today a judgement call wearing a rule's clothing."*

⚠ **The honest counter.** `dev-process.md:118` does say *"Reaching four rounds OBLIGES ASKING, and
does not fire"*, so an obligation to **ask** exists. Asking is not the defect. The defect is that
asking was treated as **blocking** while the owner was away — the same failure the handoff already
records costing 6.5 hours on a two-line change — when the written rule is *notify and continue*.

## F3 — High · structural. Moving the claim to a browser moves it OUT of the mutation harness, and the inventory does not state this cost

Derived by AST, not grep (`ast.parse` over `scripts/check-plan-code.py`): `HARNESS_TREE` has **7**
entries — `scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`,
`.github/workflows`, `.agents/skills`. `node_modules/typescript` is the **only** `node_modules`
entry (23 MB, against 504 MB for the whole tree, per its own comment). No Playwright package is
staged. Independently, `child_env` sets `env["HOME"]` to a redirected path (`:161`), and Playwright
resolves its browser cache from `$HOME`.

So a Playwright reachability assertion would today have **no mutation coverage**, and this
repository's entire quality argument rests on mutation testing. `CONTEXT.md`'s own glossary:
*"an unfalsifiable guard is worse than none, because it creates a belief that something is
covered."*

⚠ **The absolute form of this claim is too strong, and the Codex half was right to narrow it.**
`HARNESS_TREE` does not prove browsers are impossible — suites inherit an environment and spawn
subprocesses. It proves the harness does not **provision** a portable browser.

⭐ **AND THE CLAUDE HALF'S M4 NAMES THE MECHANISM I HAD ONLY GESTURED AT, which turns this from an
estimate into a finding.** The harness's containment-scope note enumerates **Python's**
home-resolution routes (`HOME_ESCAPES`, `:298-305` — `os.path.expanduser('~user')`, hardcoded
absolute paths, and the rest) and is **silent on Node's**, which is precisely the route a browser
case needs: Playwright resolves its browser cache through `os.homedir()`, and `child_env`'s
redirect (`:161`) governs it. So **a browser case placed inside the mutation harness today is a
CANNOT RUN**, and — the part that makes it structural — **no round has said so**. A cannot-run
recorded as a pass is this repository's strongest available false claim, by its own glossary.

**Consequence, and it reverses my own earlier framing.** The CI half of candidate C is *cheap*: the
precedent is `playwright.prod.config.ts`, already a wired gate with no `webServer`. The expensive
half is the harness, and row 304's first task is therefore **not** the assertion — it is extending
the containment note to Node's routes, staging the Playwright packages, pinning
`PLAYWRIGHT_BROWSERS_PATH` outside `$HOME`, and proving a mutation of the new gate is **caught**.
Until that is done, a browser gate would be an unfalsifiable guard, which the glossary says is
worse than none.

## F4 — Medium · structural. `page_chrome.py` is both producer and gate for its own output. Co-location CONFIRMED; the causal claim REFUTED

I proposed this as the mechanism of the thrash: one 2,557-line module defines the producers
(`chrome_css` `:831`, `chrome_script` `:968`, `chrome_bar` `:1302`) and the checkers that read their
emitted text (`assert_wired` `:1335`, `bar_unreachable` `:591`, `self_test` `:1440`), a structure
`CONTEXT.md:109` rules out for the sibling renderer — *"the renderer … is a peer of the generators,
never a gate … and a renderer checks nothing."*

⛔ **The causal half does not survive, and the Codex half refuted it correctly.** `CONTEXT.md:109`
defines *the renderer* as `page_markup.py` specifically; it does not ban a library from validating
its own output. More decisively, **no historical finding on this branch would have been prevented by
moving the checker to another file**: r3's whitespace-sensitive consumer signature stays
whitespace-sensitive, r6's unguarded re-arm stays unguarded, r7's wrong selected bar stays wrong,
r8's deleted mutation entry stays deleted. The causal problem is **what the assertion observes**, not
where the function lives.

What survives is a real but smaller finding: a 2,557-line module with no stated internal boundary
between emitting and checking, and no vocabulary for the distinction (F6). Recorded as Medium, and
explicitly **not** as a mandate to split the file.

## F5 — Medium · transitional. Four numbers published on this branch were wrong, and one was a correction

| Figure | Published as | Actually | Status |
|---|---|---|---|
| green cases over invalid JS | **201** (r6 note `:28`, `:55`) | **190/190** (`page_chrome.py:1178`, `:2071`); 201 belongs to a *different* incident at `:1566` | **uncorrected** |
| consecutive fix-created rounds | **eight**, then corrected to **seven** (`c293e31b`) | **six** (r2–r7); r8's own half calls its growth loop *"measurably PRE-EXISTING"* against parent `bcdc0a61` | **corrected once, still wrong** |
| in-flow bar height | `153.45px` | irreproducible (depends which page `brief-compose` lifts its tray from) | corrected |
| commits on the branch | **33** (handoff) | **36** (`gh pr view 378`) | **uncorrected** |

⛔ **The remedy is to DELETE the count from the inventory, not to correct it a third time.** The
arming condition is *two consecutive rounds in one component*, met at r3 and still met; the count is
not load-bearing for any decision, and `dev-process.md:118` says so in its own words — *"a count was
the wrong repair for it."* A figure that no decision depends on, published four times and wrong four
times, should stop being published.

## F6 — Medium · structural. The governing vocabulary has no words for the property under review

Reproduced with case-insensitive counts over `CONTEXT.md`: `chrome` **0**, `page_chrome` **0**,
`Playwright` **0**, `browser` **0**, `self-test` **0**; `reachab` **2**, both unrelated (blob
addresses `:62`, YAML lines `:133`). Meanwhile the *Verification Stack* section records that it
exists because Architecture Review #7 found *"seven consecutive review rounds had been argued in
words this file did not contain"* (`:121`).

⚠ **The numerical echo proves nothing and I am not arguing from it.** Missing the word "Playwright"
is not a defect. The substantive omission, as the Codex half put it better than my original form:
a reader cannot find, in the governing vocabulary, the distinction between **wiring**, the **pinning
mechanism**, and **rendered reachability** — nor their accepted limits. Three rounds argued that
distinction without a shared word for it, and F1 shows a fourth axis (**operation** — the control
works) that none of the three names.

**Remedy, following Architecture Review #7's own precedent:** add those terms to `CONTEXT.md`'s
Verification Stack section. Prose, cheap, and it is the move that measurably stopped the recurrence
last time.

---

## What this branch decided that isn't written down

The Phase 6 question no tool can see. Each of these is discoverable only by reading one file, which
is ADR-0014's propagation warning (`:35-42`):

* **Candidate D is already adopted** — assertions describe this repository's generators and its
  skill-authored fragments, not adversarial markup, with five shapes enumerated as out of scope and
  witnessed by cases (`page_chrome.py:30-70`). This is a design decision of real consequence and it
  lives in a docstring.
* **One bar**, under the title in flow and pinned after scrolling, with the slot preserving its space.
* **A hand-authored fragment switcher is moved into the bar at runtime**, so one element carries both
  controls.
* **Resize while pinned deliberately retains the last in-flow measurements**, and a measured
  one-pixel overlap is accepted.
* **Text styling is opt-in** for prose producers rather than enabled across the four tabular ones.
* **Composer output depends partly on an externally selected Ask-tray source**, so an identical
  fragment at an identical commit need not reproduce identical pixel measurements. ⚠ This one is
  load-bearing for any future browser gate: fixtures must pin the tray source or the gate is flaky
  by construction.

## The terminating move — PR #378's last red, and that it needed no owner decision

`check-review-recorded` asks two questions and only the second is red: *did **any** round see the
final **guarded** tree?* Two facts settle it, both obtained by **executing** the code rather than
reading it:

* `tail_verdict`'s docstring: *"**ANY** round clears it, not the latest. An EMPTY list is the pass."*
* `is_prose()`, run directly, classifies `docs/backlog.md`, `docs/roadmap-to-launch.md`,
  `docs/dashboard-entries.md`, `docs/reviews/**`, this document and `CONTEXT.md` as **prose**;
  `scripts/page_chrome.py` as **guarded**. And
  `guarded_changes(['docs/backlog.md','docs/reviews/claude/x.md']) -> []`.

**Therefore a round that reviews the current tip and FILES rather than FOLDS clears the gate** — and
every artifact this review produces is prose. The handoff presented three ways forward and said two
were the owner's. In fact the exit required **no owner decision at all**, and it was available at
round 4. ⚠ The `NO-REVIEW:` route remains the owner's and is not needed; note also that backlog #120
already records that editing a PR body alone does not reach CI, which would have made that route
fail quietly.

⭐ **AND THERE IS A SECOND EXIT, DOCUMENTED IN THE GATE ITSELF, WHICH IS STRONGER THAN MINE AND WAS
NEVER USED — the Claude half's H2.** `check-review-recorded.py:48-50` states the practice: *"The
documented practice is to hold a round's fixes UNCOMMITTED so the reviewer sees the state that will
merge."* The rule is `same()` (`:905-909`): a path clears when the tree entry the reviewer was
handed — the head entry overlaid by the verdict's `dirty` map (`:1871`) — equals the entry in the
merging tree, read by `git ls-tree -z HEAD` (`:994`). Entries are content-addressed blob ids, so
**holding a fold dirty, dispatching the round against it, then committing it unmodified preserves
the pass.** That is an exact fixed point.

**Measured: it was never given that input.** Every Codex verdict on this branch recorded
`dirty: 0 paths` — r1, r2, r3, r5, r6, r7, r8, seven of seven dispatched against a fully committed
tree.

⛔ **So the procedural argument must be WITHDRAWN, not weakened.** It is the argument the r6 note
added after round 8 and ranked highest — *"the strongest single argument for moving the claim to a
rendering assertion"* — and it does not survive contact with the gate it cites. The loop did not
fail to terminate; **it was never given the one input that terminates it.** ⚠ This removes an
argument *for* candidate C without weakening C, which B1 carries alone — and that separation is
exactly why the Claude half put B1 first.

⚠ **This does not make the branch CONVERGED.** It makes the gate honest: some round saw the tree that
will merge. Merging remains the owner's.

## NOT RUN — failures, not passes

* The historical dropped-brace artifact. I did not recover the exact committed version; F1 uses a
  constructed runtime fault instead, which is a different (and I argue stronger) input.
* A fresh browser sweep of all five real producers at this tip. The r7 half records one; I did not
  repeat it.
* The full mutation harness. CI's eight shards were still running at the time of writing.
* `schema-gates` was once NOT RUN on this branch from a registry throttle (`toomanyrequests`). That
  is a cannot-run, never a pass. It is `success` at `271818c9`.
* Real device; physical printing; zoom; font-load reflow; late images; the no-`IntersectionObserver`
  fallback in a browser.
* `2026-10-05-topic-why-x-not-y` gets no chrome script at all (incomplete palette) — pre-existing.

## The reviewers' own findings, which outrank mine

⚠ **Read this section before the coordinator findings above.** Two of my six were refuted in their
causal half, one was superseded in strength, and the Blocking finding of this review is the Claude
half's — not mine. I ran the inventory's claims to ground; the halves found the live defect.

| # | Severity | Finding | Status after my verification |
|---|---|---|---|
| **B1** | **Blocking** · structural | The suite is **monotone in the source text** — detects *changed* or *removed*, immune **by construction** to *added*. `arm=function(){};` (17 bytes) leaves every asserted expression verbatim: 223/223, `node --check` passes, `assert_wired` accepts, **no page errors** — and on a matched pair of real `gen-dashboard.py` output the bar never pins, theme control offscreen at `scrollY=900` (`bottom −737.4`). **The owner's original complaint, reinstated with every gate green.** Manifest shares the blind spot: 31 additions of 1,553 edits (2.0%) | **CONFIRMED and adopted as this review's decisive datum.** Supersedes my F1 in strength |
| **H1** | High · structural | `'#chrome-theme,#schemer'` is emitted at three sites; `:1062` and `:1086` have cases, **`:1113` (`ctls`, which computes the pin threshold) has none** — and `:1888-1894` records *noticing this exact class* and then fixes only the case that noticed it. Severance S3 → control offscreen at `scrollY=224`, suite 223/223 | **CONFIRMED.** Fix is one case + one manifest entry and **does not depend on the instrument decision** |
| **H2** | High · structural | The non-termination argument is **false**; the fixed point is the gate's own documented practice (hold the fold dirty, dispatch, commit unmodified), and all **seven** dispatches recorded `dirty: 0 paths` | **CONFIRMED** against `:905-909`, `:994`, `:1871`. Folded into *The terminating move* above |
| **M1** | Medium · transitional | Six receiving rounds (r2–r7), not seven | **CONFIRMED** — matches my F5, derived independently |
| **M2** | Medium · transitional | *"Every real defect of r6–r8 found in a browser"* is **false for round 8** — three of its five findings came from the manifest, a severance sweep and git | **CONFIRMED**; also found by Codex |
| **M3** | Medium · structural | My F4 is co-location, not causation; the split would have prevented no round and would re-anchor roughly half the manifest | **CONFIRMED** — independently of Codex, which refuted it on different grounds |
| **M4** | Medium · structural | The harness's containment note enumerates **Python's** home-resolution routes and is silent on **Node's** — so a browser case inside the harness is a **CANNOT RUN**, and no round has said so | **CONFIRMED.** This is the real cost of C; folded into F3 |
| **L1–L3** | Low | The decisive datum's suite size recorded three ways; **D is the status quo, not a candidate**; **zero ADRs** cover page generation or the chrome | **CONFIRMED** |

⛔ **MY OWN PROCESS FAILURE, RECORDED BECAUSE IT AFFECTED THE EVIDENCE.** I edited `CONTEXT.md` and
added two files under `docs/reviews/` **while the Claude half was reviewing that worktree**. It
detected the overlay, pinned its counts to `git show 271818c9:<path>`, and reported both readings —
so no finding is corrupted. But the hazard is one this project has already paid for twice in one
night (*a live agent's file is not static*), and I reintroduced it. The reviewer handled my mistake;
that is luck, not process.

⛔⟳ **CORRECTED. I WROTE THAT MY TWO LATE LEADS NEVER REACHED THE CLAUDE HALF AND THAT F2 HAD BEEN
REVIEWED BY NOBODY. BOTH WERE WRONG WITHIN SIX MINUTES OF MY WRITING THEM.** The half picked up the
message and filed an addendum (H3–H5, 616 → 811 lines) that attacked both leads and **refuted one of
my conclusions and one of my ownership claims.** I had read its file, seen no mention of the leads,
and inferred they had not landed — an inference stated as a measurement, which is the failure this
document's own F5 is about. The addendum:

| # | Severity | Finding | Effect on this document |
|---|---|---|---|
| **H3** | High · structural | **Lead 1 confirmed from its own fixture — and F1's floated remedy REFUTED.** `jsdom` is already a dependency, so it ran it: unmodified → bar `chrome chrome-pinned`; prepended `throw` → throws, bar `chrome`; **the 17-byte case → no throw, bar `chrome chrome-pinned`**. **The execution instrument returns the healthy page's answer for the dead one** — because jsdom has no layout (`rect {top:0,bottom:0,height:0}` on both) and no `IntersectionObserver`, so the script takes its fallback at `:1172` where `0 - 0 <= 0` fires `pin(true)` on everything | **F1's remedy paragraph is WITHDRAWN.** Row 305 rewritten: the proportionate fix is *read the console* (one line), which catches the `throw` and misses the silent case |
| **H4** | High · structural | **Lead 2 confirmed, with better evidence than my grep.** It searched for the document that would collapse the finding and found **three that say the opposite, imperatively** — `review-method.md:133` (Q5's *Then*: `ARCHITECTURE REVIEW`), `:525` (*"it is the ARMING CONDITION itself"*), `:178` (*"it escalates from FIX to REDESIGN"*) — plus the spine's *Conditional AFK* policy ruling **notify and continue** | **F2 strengthened**, and honestly bounded: `review-method.md:124` *is* a human gate here, but over **tree identity**, which the branch also inverted — and `:125` records the precedent, *"exactly what PR #302 cost, twice"* |
| **H5** | High · structural | **My ownership claim REFUTED. It is neither #184 nor #136 — it is a missing INPUT.** `0 of 15` of this branch's round documents carry the header `round-header-template.md:3` calls mandatory, against **77** compliant elsewhere; `check-review-decision.py` exits **rc=2 CANNOT RUN** on this subject with its own suite at **61/61** | **The #184 amendment is WITHDRAWN and refiled as row 306.** #184's remedy is *build a caller*, and a caller here returns rc=2 — opposite remedies |

⭐ **H5 supplies the causal chain I had only half of.** Not *"the loop deferred to an authority that
does not exist"* alone, but: **the counters the decision procedure needs were never recorded → the
only instrument that reads them cannot run → the arming call had to be made from recall → it was,
five times, and was then attributed to an authority that does not exist.** The repo had already
bought that lesson — `round-header-template.md:5-8`: *"On PR #302 nobody kept either, which is why
four rounds ran where two were owed."* This branch skipped the header in all 15 documents and the
failure recurred as five rounds where **zero** were owed.

⛔ **AND F1 COMMITTED THE ERROR F1 DIAGNOSES.** Its headline is *"the instance is closed; the class
is not"* about the parse gate; its remedy paragraph then closed a new instance (the `throw`) and left
the same class open, one paragraph later. Recorded plainly, because this project's record is that the
fix for a class defect is where the next instance of it appears.

⚠ **What remains single-sourced is now narrower:** F2's *grep* evidence has been independently
reproduced and extended, so the finding stands on two pairs of eyes. Nothing in this document is now
unreviewed.

## Work this review files

Filed in the same turn as this document, per `dev-process.md`:

1. **#184** — amendment **WITHDRAWN** per H5: the card could not have answered at all, which is a
   cannot-run and not this row's falsifier. The branch history is retained on the row as evidence
   about discovery, explicitly not as evidence for its falsifier.
2. **#136** — amended: a second worked example of route (b), again reached by argument.
3. **Row 304** — the instrument slice, direction **C**, with M4's harness prerequisite as its first
   task, H1 as task 0, and B1's 17-byte case as its falsifier. ⚠ Must **not** be sized from row 305.
4. **Row 305** — rewritten after H3. The diagnosis stands; the *remedy* is refuted — jsdom
   execution **false-greens** the silent case. The proportionate fix is a one-line console-error
   read, which closes the noisy member of the class and cannot touch the silent one.
5. **Row 306** — new, filed in place of the withdrawn #184 amendment: `0 of 15` round documents
   carry the mandatory header, `check-review-decision.py` exits rc=2 on this subject, and the
   backfill is minutes of work.
5. **`CONTEXT.md`** — four terms added (wiring / operation / pinning mechanism / rendered
   reachability) with S8 as the worked example, per the Claude half's objection to my first draft.
   Done in this review, following Architecture Review #7's precedent.

⚠ **H1 is a cheap, instrument-independent fix that is NOT folded here**, deliberately: folding it
would re-redden `check-review-recorded` and this review's whole point is that the branch should
stop folding. It belongs to row 304's first commit.

## Reviewer halves

* Codex (`gpt-6.1-sol`): `docs/reviews/codex/arch-chrome-instrument-r1-codex.md`. Chose **C**. Ran
  its own Chromium fault injection. Refuted four of the inventory's six leads and the causal half of
  F4. Its corrections were verified here and **upheld in every case**.
* Claude: `docs/reviews/claude/arch-chrome-instrument-r1-claude.md`.

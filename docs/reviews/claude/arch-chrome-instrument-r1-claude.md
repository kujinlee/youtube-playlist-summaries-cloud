# arch-chrome-instrument — round 1, CLAUDE half

Phase 6 architecture review on `chrome-bar-reachable` (PR #378), subject tip `271818c9`.
Mandate: **refute**. Every number below names the command that produced it.

**1 Blocking · 5 High · 4 Medium · 3 Low.** H3–H5 are an **addendum**, added after this
file was first filed, answering two leads the coordinator derived after dispatching me.

## Instrument, and its bounds

* The three shipped suites, run at tip in the worktree: `page_chrome` **223/223**, `brief-compose`
  **153/153**, `gen-dashboard` **325/325**, `gen-backlog-page` **165/165**, `page_markup` **74/74**,
  `check-plan-code` **178/178**, `check-review-recorded` **194/194** (each `python3 scripts/<f> --self-test`).
* A **severance battery** over an isolated copy of `scripts/` in my scratchpad — never the worktree —
  with a green control proved before every entry (`223/223` + `153/153`). 13 severances attempted.
* **Chromium via the repo's own Playwright** at 320×568, over four hand-built pages and a **matched
  pair of real `gen-dashboard.py` output**.
* `git show`/`git log`/`git diff` only. ⚠ **The worktree is live under me and I pinned to the commit.**
  While I worked, `CONTEXT.md` gained an uncommitted 9-line overlay and two files appeared under
  `docs/reviews/`. Every count I report is taken from `git show 271818c9:<path>` or from a file I
  verified unmodified; where the overlay matters I give both readings.
* ⛔ **I deliberately did not read the Codex half** (`docs/reviews/codex/arch-chrome-instrument-r1-codex.md`)
  **or the coordinator's new top-level inventory doc**. Consensus is not verification, and this
  repository has a recorded case of three agents agreeing while `git diff` refuted them.
* **My own corrections, stated because they bear on trust in the rest.** Three of my first
  severances were invalid as written (two edited a comment or left a brace unbalanced, so they
  tested nothing I claimed) and were rebuilt. My first producer comparison was an **unmatched pair** —
  the two pages came from different trees — and is discarded; the pair reported below is matched and
  differs by 17 bytes.

---

## THE ONE QUESTION, answered first

**Should the reachability claim move from a text predicate to a rendering assertion?**

**Yes — and the reason in the inventory is the wrong reason.** The inventory rests on two arguments
(the invalid-JavaScript datum and the non-termination of the fold-then-review cycle). I measured
both and **both have expired**: the parse gate added in round 6 does catch the dropped brace at tip,
and the non-termination is refuted by the gate's own documented escape, which this branch never used
in seven dispatches.

What survives — and what the inventory does not contain — is B1 below: a 17-byte addition to the
producer reinstates the owner's original complaint on a page produced by a real generator, with
223/223 green, `node --check` green, and `assert_wired` accepting. The case for a rendering
assertion does not need a procedural argument. It needs that one.

---

## Blocking

### B1 — Blocking, **structural**. The suite is monotone in the source text: it detects that an asserted expression was CHANGED or REMOVED and is immune **by construction** to anything ADDED — and the repair adopted in rounds 6–8 strengthened only the direction that already worked

This is the composition defect per-task review cannot see, because every individual case in it is
correct.

**The repair under review.** Rounds 6–8 answered the ambient-supplier class by replacing substring
assertions with whole, exact, contiguous expressions. The file states the reasoning at
`scripts/page_chrome.py:1930-1945`, including its own honest limit at `:1942` (*"It is NOT a
behavioural test"*). The form is always the same:

    case("the reserve is measured in fractional pixels, so pinning cannot shift the page",
         ("var h=bar.getBoundingClientRect().height;" in chrome_script(),
          "offsetHeight" in chrome_script()), (True, False))     # :1952-1954

A containment assertion over emitted text is **monotone**: adding text can never make it False.
So the repair closed removal and change, and left addition open — and addition is the direction in
which *"something else also supplies it"* and *"something later overrides it"* both live, which is
the shape every one of this branch's missed defects has had.

**Measured, both directions.**

*False positive — the suite reddens on an edit that cannot change behaviour.* In the isolated copy,
`"var h=bar..."` → `"var h = bar..."` (one space; the same JavaScript statement):

    222/223 passed
    [FAIL] the reserve is measured in fractional pixels, so pinning cannot shift the page:
           got (False, False) want (True, False)

The case names a layout property and tests a transcript. Its true falsifier is *the source text
changed*, not *the page shifts*. Under `CONTEXT.md`'s own definition — *"**Falsifier** — the
observation that would make a claim fail"* — this is a change detector, not a falsifier, and it
cannot tell an improvement from a regression.

*False negative — the suite stays green over a destroyed feature.* Severance **S8**: after the
verbatim-asserted observer definition at `:1141-1142`, append one statement:

    "io=new IntersectionObserver(function(es){pin(!es[0].isIntersecting);},"
    "{rootMargin:(-tailPx)+'px 0px 0px 0px'});io.observe(slot);};"
    "arm=function(){};"                                    <-- 17 bytes added

Every asserted expression survives verbatim. Results:

| Gate | Under S8 |
|---|---|
| `python3 scripts/page_chrome.py --self-test` | **223/223 passed**, rc=0 |
| `node --check` on `chrome_script()` | **passes** — valid JavaScript |
| `assert_wired(page, …)` | **ACCEPTED** |
| Chromium page errors | **none** |

And in a browser, on a **matched pair generated by a real producer** — both pages built by
`gen-dashboard.py` from one tree under a redirected `$HOME`, differing only by those 17 bytes
(1,329,605 vs 1,329,622 bytes; `grep -c "arm=function(){}"` → 0 and 1), scanned at 320×568 at
`scrollY` 0…900 step 6:

    dash-ctl.html  controls=1  every control reachable at every y in 0..900 step6
    dash-sev.html  controls=1  FAIL: chrome-theme fully offscreen at scrollY=900,
                               bottom=-737.4, class="chrome"

The bar never pins. **That is the owner's original complaint, exactly, reinstated by 17 bytes with
every gate green.** It is not an adversarial-markup case and so is not covered by the declared
subject bound: the input is the repository's own generator output, and the defect is in the
repository's own producer.

**The manifest shares the blind spot, measured.** Classifying every edit in
`scripts/mutations/page_chrome.json` by whether the anchor survives verbatim inside the replacement:

    edits total: 89
    pure ADDITIONS (old preserved verbatim inside new): 4
    pure DELETIONS/weakenings (new is a substring of old): 14
    replacements: 71

Across all 62 manifests: **31 additions of 1,553 edits (2.0%)**. So the mutation harness is 98%
pointed at the direction the suite already covers, and the direction it does not cover is the
direction the repair left open. A sweep reporting *zero survivors* is therefore consistent with B1
being live, which is exactly what r8's `112 killed / 112 attributed / zero survivors` means.

**What would make this finding wrong.** If a case existed that executed the emitted script rather
than reading it, S8 would redden. There is none: the strongest artefact check at tip is a **parse**
(`:2084-2099`), and `node --check` accepts `arm=function(){};` as it accepts `throw`. The finding
also fails if S8 is outside the declared subject — it is not, as shown above. I could not construct
any third defence.

**Severity.** Blocking, because the defect class it describes is the one the branch has spent eight
rounds not closing, and because B1 is the direct answer to THE ONE QUESTION.

---

## High

### H1 — High, **structural**. Of three occurrences of the control selector, two have cases and the third — the one that computes the pin threshold — has none; the file records noticing the class and did not sweep it

`'#chrome-theme,#schemer'` is emitted at three sites:

| Site | Purpose | Asserted by a case? |
|---|---|---|
| `scripts/page_chrome.py:1062` | choosing the bar among several | ✅ `:1993` |
| `scripts/page_chrome.py:1086` | the one guard governing the whole block | ✅ `:1895` |
| **`scripts/page_chrome.py:1113`** | **`ctls` — the boxes the threshold is measured from** | ❌ **none** |

The comment at `:1888-1894` is the part that makes this a composition defect rather than an
oversight. It records that the r6 threshold fix *"introduced a SECOND use of
`#chrome-theme,#schemer` (the `ctls` lookup), so `"…" in chrome_script()` stayed True after the
guard clause was deleted"*, calls it *"Exactly the ambient-pass shape this repository keeps paying
for"* — and then fixes **the case that noticed it** and leaves the newly introduced third site
unasserted. That is *after fixing, SEARCH for the class* not done, on the very finding that names
the class.

**Measured.** Severance **S3**, one token: `querySelectorAll('#chrome-theme,#schemer')` →
`querySelectorAll('#nonexistent-control')`. `ctls` is then empty, `m` stays `Infinity`, `tailPx` is
0, and the threshold the r6/r7 folds exist to compute is gone.

    223/223 passed      node --check: PASSES      assert_wired: ACCEPTED
    S3.html   FAIL: a control fully outside the viewport at scrollY=224,
              bottom=-55.6, class="chrome"
    control   BOTH CONTROLS VISIBLE at every y in 0..600 step4

Fix: one case naming the whole `ctls` statement, and one manifest entry. Cheap, and it does not
depend on the A/B/C/D decision.

### H2 — High, **structural**. The non-termination argument is false, and the fixed point is the gate's own documented practice — which this branch did not use in any of seven dispatches

The r6 coordinator note calls this *"the strongest single argument for moving the claim to a
rendering assertion"*: `check-review-recorded` requires some round to have seen the current tree,
every fold commits guarded code after its round, so the loop terminates only on a round needing no
fold. Brief item 6 asks whether that is a property of the procedure or a bug. **It is neither — it
is a property of a workflow choice, and the gate anticipates it in writing.**

`scripts/check-review-recorded.py:48-50`:

> `dirty` is load-bearing in the other direction. **The documented practice is to hold a round's
> fixes UNCOMMITTED so the reviewer sees the state that will merge**; under it `head` is the commit
> BEFORE those fixes, and a check reading `head` alone would accuse the author who did the careful
> thing.

I verified this against the code rather than the docstring. The rule is `same()` at
`scripts/check-review-recorded.py:905-909`: a path clears if the **tree entry** the reviewer was
handed — head entry overlaid by the verdict's `dirty` map — equals the entry in the merging tree,
read by `git ls-tree -z HEAD` (`:994`). The entry is a content-addressed blob id, so **committing a
fold unchanged after dispatching a round against it preserves the pass.** The fixed point is exact:
hold the fold dirty → dispatch → commit it unmodified → `same()` is True → rc 0, with no further
round required.

**Measured — the escape was never used.** Every Codex verdict this branch recorded:

    r1 dirty: 0 paths      r5 dirty: 0 paths      r8 dirty: 0 paths
    r2 dirty: 0 paths      r6 dirty: 0 paths
    r3 dirty: 0 paths      r7 dirty: 0 paths

Seven of seven dispatched against a fully committed tree. The loop did not fail to terminate; it
was never given the one input that terminates it.

**Consequence for the inventory.** The procedural argument must be **withdrawn**, not weakened. It
is the argument the r6 note added after round 8 and ranks highest, and it does not survive contact
with the gate it cites. ⚠ This does **not** touch the technical case for a rendering assertion — B1
carries that alone, which is why I put B1 first.

**What would make H2 wrong.** If `reviewed_map` ignored the dirty overlay, or if `final` were read
from a commit rather than the tree. Neither: `:1871` reads the map, `:994` reads `ls-tree`, and
cases `:1799` and `:1851` pin both behaviours.

---

## Medium

### M1 — Medium, **transitional**. The arithmetic in evidence item 1 counts round 8, and both of round 8's halves explicitly deny it. Over committed evidence the figure is six, not seven

The brief lists the fix-created rounds as r2:4, r3:5, r4:3-of-8, r5:7-of-8, r6:3-of-6, **r7, r8** —
seven receiving rounds — and flags that an earlier draft said eight. The correction went one round
too few.

* **r7 is supported.** `docs/reviews/codex/chrome-bar-reachable-r7-codex.md` findings 1 and 2 name
  the previous fold as cause (*"The resize's `sync` returns while pinned"*; *"This is the CSS fold
  recreating the class already fixed for `<template>` and `<noscript>`"*).
* **r8 is refuted by both halves.** Codex: *"The last six commits contain substantive fixes. I did
  **not** establish an eighth fix-created-next-finding sequence."* Claude: *"Round 8's Codex half is
  also right that this fold does not establish an eighth fix-created-next-finding round — the one
  growth loop I found still live is measurably PRE-EXISTING"*, and in its verdict: *"**The verdict as
  it stands is still seven rounds, not eight.**"*
* The only committed per-round table (`chrome-bar-reachable-r6-coordinator.md`) lists **five**
  rows, r2–r6.

So the defensible count over committed evidence is **r2–r7, six receiving rounds** (equivalently
six consecutive fix→finding links, r1→r2 through r6→r7). r8-claude's M1 is caused by round 8's own
fold and is correctly described there as *"the first half of"* the shape, not an instance of it.

**This changes no decision** — `dev-process.md` arms on **two** consecutive rounds and six clears it
by a factor of three — and I say that explicitly so the correction is not mistaken for a defence of
continuing. It matters because an inventory that over-counts by one in its headline datum invites
the reader to discount the rest, and this repository's recorded failure mode is *an inference stated
as measured*.

### M2 — Medium, **transitional**. Evidence item 4 — *"every real defect of rounds 6-8 was found in a browser"* — is false for round 8, and the two strongest arguments for A/C both rest on it

Round 8's findings, by the instrument that found each:

| Finding | Instrument |
|---|---|
| r8 Codex **High** — nested slots cause continuous layout growth | **browser** (measured `--chrome-h` 225.6 → 1102.5 → 1965px) |
| r8 Codex **Low** — two ratchet-removed parameters are varied-but-unwitnessed | the **mutation harness** in a temp copy |
| r8 Claude **M1** — a live mutation entry deleted instead of re-anchored | the **manifest and git** |
| r8 Claude **L1** — `compose.generated_at` varied-but-unwitnessed | a **programmatic severance sweep** over 42 parameters |
| r8 Claude **L2** — the growth loop is narrowed, not closed | browser |
| r8 Claude **L3** — a stale comment on the constant the fold redefined | **reading** |

Four of six came from non-browser instruments, and the two coverage findings came from the same kind
of instrument I used for B1. The honest form of item 4 is *"every **reachability** defect of rounds
6–8 was found in a browser, and the **coverage** defects were not"* — which is a sharper claim and
still supports a rendering assertion, because reachability is the property under review.

### M3 — Medium, **structural**. F1 is co-location, not causation. The split it implies would have prevented none of the rounds and would re-anchor roughly half the manifest

F1's structural half reproduces. Classifying every top-level symbol of `scripts/page_chrome.py`:

* producers — `theme_control:643`, `text_style_control:742`, `text_style_css:761`,
  `refresh_control:808`, `stamp:822`, `chrome_css:831`, `chrome_script:968`, `stamp_bar:1222`,
  `place_bar:1239`, `provenance:1275`, `chrome_bar:1302`;
* checkers — `strip_css_comments:171`, `css_of:227`, `_applied_css:239`, `missing_palettes:244`,
  `has_control:272`, `_Scan:353`, `_scan:571`, `_is_document:586`, `bar_unreachable:591`,
  `has_text_control:651`, `missing_text_tokens:660`, `has_text_consumer:692`,
  `missing_text_consumer:701`, `assert_wired:1335`, `_scripts:1427`, `self_test:1440`.

One module, both roles. And `CONTEXT.md:108-112` does rule the shape out for the sibling renderer.
⚠ But read the whole sentence, which the brief's ellipsis removes: *"It is a **peer** of the
generators, never a gate: **the documented generator → gate arrow governs a page importing the guard
that checks it**, and a renderer checks nothing."* The rule is about a **generator importing its own
gate**, and `page_chrome` is not a generator — it is the shared chrome library the five generators
import. So the glossary does not say what F1 cites it as saying.

**The causal claim fails on its own test.** The brief asks me to name a round the split would have
prevented. I classified each fix-created finding by what moved and what broke:

| Round | Fix-created findings | Edit → defect |
|---|---|---|
| r2 | `:277` ×2, `:629`, `:155` | checker fix → checker defect (substring predicates) |
| r3 | `:358`, `:194`, `:199`, `:186` | checker fix → checker defect (regex, then `html.parser`) |
| r4 | the id predicates r2 left | checker → checker |
| r5 | 7 of 8, all in `_Scan` | checker → checker |
| r6 | #2 threshold, #3 braceless `arm()`, #4 dropped brace | **producer → producer** |
| r6 | #6 unfalsifiable cases | case → case |
| r7 | #1 stale threshold after resize | producer → producer |
| r7 | #2 own-ID omission in the new `style` branch | checker → checker |

**Not one is "a producer edit moved the text the checker reads."** Every entry is same-side. A
checker in `page_chrome_gate.py` importing `page_chrome` would hold the identical `_Scan` model of
Chromium, would mis-parse `<noscript>` identically, and would emit the identical dropped brace.
**The split prevents zero rounds — name the round is answerable, and the answer is none.**

**And it has a measured cost.** All 89 anchors in `scripts/mutations/page_chrome.json` resolve at
tip (0 not found); 44 land in producer bodies, 42 in checker bodies, 3 at module level. A split
re-anchors the 42–45 checker-side entries and every module-level one, in a repository whose recorded
hazard is *an anchor is unbound by ANY nearby edit* — 7 orphaned in one session, one of them a
blocking red CI step. So F1 proposes a refactor that moves no finding and buys a known-expensive
risk.

**State F1 as unsupported.** The true mechanism is B1: not *who owns the string*, but *what the
assertion observes*.

### M4 — Medium, **structural**. The mutation harness's containment-scope note enumerates Python's home-resolution routes and is silent on Node's, which is precisely the route a browser case needs — so a browser case inside the harness is a CANNOT RUN, and no round has said so

`child_env` (`scripts/check-plan-code.py:118-184`) redirects `$HOME` as structural containment, and
bounds its own claim at `:146-153`: *"`$HOME` governs `Path.home()` and a bare `~`, and NOTHING ELSE…
`expanduser("~<user>")` both returned the REAL one."* Every route named is Python's.

Node's `os.homedir()` also reads `$HOME` on POSIX, and Playwright resolves its browser cache
through it. **Measured, by hitting it:** running my probe under a redirected `$HOME`,

    browserType.launch: Executable doesn't exist at
      <fakehome>/Library/Caches/ms-playwright/chromium_headless_shell-1223/…

so a browser case spawned by `mutate_delivered` finds no browser and reports a cannot-run — which
`CONTEXT.md:129` correctly calls a **failure**. The fix is one line (thread
`PLAYWRIGHT_BROWSERS_PATH` through `child_env`, which otherwise inherits `os.environ` and would pass
it), but it has to be *known*, and the scope sentence is written in a way that hides it.

This is a real, specific, previously unstated cost input for candidates A and C, and it is the kind
of thing a Phase 6 review exists to surface: the note is not wrong about anything it says, and it is
incomplete in exactly the direction the next change needs.

---

## Low

### L1 — Low, **transitional**. The decisive datum's suite size is recorded three different ways for one event, and the brief inherits the one that is not reproducible

| Figure | Where |
|---|---|
| **184/184** | `docs/reviews/claude/chrome-bar-reachable-r6-claude.md:11`, `:250`, `:265`, `:353` — the reviewer's own run at dispatch |
| **190/190** | `scripts/page_chrome.py:1178` and `:2071` — the module's two accounts of the dropped brace |
| **201** | `docs/reviews/coordinator/chrome-bar-reachable-r6-coordinator.md:28`, and the brief's item 3 |

201 is the suite size at **round 7** (`chrome-bar-reachable-r7-codex.md:92` reports `201/201` for
its own severance, on a later tree). The contemporaneous figure for the brace event is 184/184; the
module's 190/190 is plausibly the suite after the fold that fixed it. The coordinator note's 201 is
not reproducible from anything in the record. A retrospective number needs provenance; cite the
reviewer's run.

### L2 — Low, **transitional**. Candidate D is not a candidate — it is the status quo, implemented and witnessed

D asks to *"declare that the guard protects against generator and skill-authored-fragment mistakes,
not adversarial markup, so the unfixed parser findings become out of scope by construction."* That
is done:

* `scripts/page_chrome.py:30-45` declares it (*"⛔ THE SUBJECT OF EVERY ASSERTION IN THIS FILE…
  They do **NOT** describe adversarial markup"*), including r5's caveat that fragments count;
* `scripts/page_chrome.py:2385-2402` carries five cases under `OUT OF SCOPE BY THE BOUND`, each
  recording behaviour and reddening if the scan is tightened — a falsifier for the bound;
* the r6 note's *Bounds* section records it as in force, and one r5 shape was deliberately promoted
  out of the set on 2026-10-19 with the recording case reddening first.

Offering D alongside A/B/C invites a decision that changes nothing. The real fork is **B (the status
quo, which already includes D) versus A/C**.

### L3 — Low, **structural**. Zero ADRs cover page generation or the chrome, and this branch's three load-bearing decisions live only in a module docstring and in review notes

`ls docs/adr/` is 14 ADRs: twelve are product/schema, and only `0010` (documents declare their
anchor) and `0014` (a guard's main is drivable) are repo tooling. None covers the generated pages.
See *the question no tool can see*, below.

---

## F2 — re-run, and it is half right for a reason the brief could not know

Counts over `git show 271818c9:CONTEXT.md` (the committed subject):

    chrome 0   page_chrome 0   Playwright 0   browser 0   self-test 0   reachab 2
    viewport 0   scroll 0   layout 0   "rendering engine" 0

**F2's five zeros reproduce exactly, and I add four more the brief did not claim** — `viewport`,
`scroll`, `layout` and `rendering engine` are also 0, which is the stronger form of the claim: it
is not that the glossary lacks the *subject's name*, it is that it lacks every term the property is
*composed of*. The two `reachab` hits are at `:53` (blob base addressing) and `:133` (a line-local
YAML rule) and are unrelated, as stated.

**Is the Architecture Review #7 analogy sound, or pattern-matching on seven?** Sound, and the number
is not what carries it. #7's finding was *"seven consecutive review rounds had been argued in words
this file did not contain… with no shared terms, each round could only name the instance in front of
it."* The test is whether the rounds lacked words, not whether they numbered seven. They did, and
specifically: nothing in the glossary distinguishes **the control is present in the markup** from
**the page declares a mechanism that would keep it on screen** from **the control's box intersects
the viewport**. Those are three different claims, `page_chrome` makes the first two and says so, and
six rounds argued about the third with no name for it. The module itself has the words
(`:67-72`: *"narrowing the subject… does not make the module's claim a layout claim"*) and the
glossary does not — words in a 2,557-line file are not shared vocabulary.

⚠ **AND F2 IS ALREADY BEING ANSWERED IN THE LIVE TREE, WHICH I FOUND ONLY BY RE-READING.** An
uncommitted overlay on `CONTEXT.md` adds four terms — *Wiring*, *Pinning mechanism*, *Rendered
reachability*, *Operation* — and two relationship lines. Working-tree counts: `chrome` 4,
`page_chrome` 3, `reachab` 7, `viewport` 3, `scroll` 2, `layout` 1, `rendering engine` 1;
`Playwright` and `browser` remain 0. The distinction it draws is the right one and it is close to
what I would have proposed.

**One substantive objection to it, from my own measurement.** Its worked example for *Operation* is
a page with a prepended `throw`, and *Operation* is defined to require *"the page raises no startup
error"* — so the `throw` case is already excluded by that clause, and the example therefore
illustrates a weaker term than the one it is attached to. **S8 is the example that term wants**: the
page raises **no error** (`pageerrors: none`), the theme button still toggles when reached, so
wiring, parse and operation all hold, and **only rendered reachability fails** (theme control at
bottom −737.4 on real generator output). S8 is the only severance in this record that isolates the
fourth term, and the glossary entry would be stronger with it.

---

## Evidence items 2, 3 and 5 — confirmed, with one correction each

**Item 2, six instruments.** Confirmed in the record: substring (r2 `:277`, `:629`), regex (r3
`:358`), comment-stripping regex (r2 `:155`), `html.parser` (r3/r5, `_Scan:353`), a caller-supplied
fact (`assert_wired(page, where, *, scoped_css_emitted: bool = False)` at `:1335`, and
`missing_text_consumer(page, scoped_css_emitted=False)` at `:701`), exact-expression assertions
(r6–r8, `:1930-1945`). Each failed in a new way, as claimed.

**Item 3, the decisive datum.** The *event* is confirmed in the record and the module memorialises
it at `:1177-1182`. ⛔ **But the datum is CLOSED at tip and the inventory does not say so.** I
re-ran it. Severance S4b, deleting the brace that closes `if(bar&&bar.querySelector(…)){`:

    221/223 passed   rc=1
    [FAIL] the emitted script's braces and parens balance: got (False, True) want (True, True)
    [FAIL] ...and it PARSES as JavaScript — the check that would have caught the brace: PARSE ERROR

Two cases catch it. The r6 note itself records the fix (*"The emitted script is now PARSED by a
case"*), so the coordinator's rebuttal of the honest counter-argument — *"nothing in the suite
watches the artifact"* — was true of the r6 tree and is **false of the tree under review**. Using a
closed datum as the live reason is the weakest part of the inventory, and B1 is the replacement:
something watches the artifact's *syntax*; nothing watches its *behaviour*.

**Item 5, structurally browserless.** Confirmed. `HARNESS_TREE` (`scripts/check-plan-code.py:199-256`)
stages `scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`,
`.github/workflows` — typescript only, for `check-paid-caller-arrival`'s oracle. ⚠ Two corrections:
(a) the file states at `:189-195` that this list *"DOES NOT BOUND WHAT A MUTATION CAN REACH"* and
*"decides only which guards can RUN"*, so "structurally browserless" is right about capability and
must not be read as containment; (b) staging Playwright is the **cheap** half — `node_modules/playwright`
is 5.0 MB and `playwright-core` 12 MB against the 23 MB of typescript already staged. The expensive
half is M4's `$HOME` problem and the 195 MB browser binary that lives outside the repo.

---

## The honest counter-argument

**Stated in full, because it is strong.** The owner's complaint was that the theme and text-style
controls could not be reached. That is fixed. I confirmed it independently rather than inheriting
it: on `gen-dashboard.py` output at 320×568, scanned at 151 scroll positions,
`dash-ctl.html controls=1 every control reachable at every y in 0..900 step6`, and on a hand-built
page carrying both controls, both reachable at every sampled position with the bar pinning at
`position: fixed`. Round 6 measured the same on all five producers. *"The feature is done, stop
reviewing the guard"* is a reasonable position, and eight rounds of defect density in the guard
rather than the feature is evidence for it, not against it.

**Is the coordinator's answer sufficient? No — the answer as given is spent.** Its two legs are the
invalid-JavaScript datum (closed at tip, item 3 above) and the non-termination argument (refuted,
H2). Both were sound when written and neither survives the tree under review.

**The counter-argument fails anyway, on B1.** The reason to keep going is not that the suite once
went green over invalid JavaScript — it no longer does. It is that **17 bytes of valid, parseable,
error-free JavaScript put the shipped feature back to broken on real generator output with every
gate green**, and the only instrument that noticed was a browser. The feature being done is exactly
what makes that matter: a fixed feature with no guard over the property that was fixed will regress,
and this branch's own history is eight rounds of evidence that edits to this producer keep happening.

**And the stop is available by declaration.** `check-review-recorded` provides `NO-REVIEW: <reason>`
in the PR body, which waives both of its questions and is refused if the reason is empty
(`scripts/check-review-recorded.py:96`). That is the owner's judgement about accepting an
unreviewed fold, and it is not mine. ⚠ H2 adds a second, cheaper option the inventory does not
mention: **hold the next fold uncommitted, dispatch one round against the dirty tree, then commit it
unchanged** — the gate's documented practice, which clears the final-tree question with no
declaration and no further round.

---

## The candidates — I choose C

**C — split: wiring in text, reachability in a browser test that runs in CI.**

**Why not the others.**

* **A** (move reachability to Playwright, keep only wiring in text) is wrong because it discards
  what the text layer is good at. The text predicates catch the *generator-mistake* class the bound
  declares and catch it in 0.53 s (`time python3 scripts/page_chrome.py --self-test` → `real
  0m0.530s`); a browser gate cannot practically cover 20 fragments × 5 producers × every scroll
  position. A is C minus the half that works.
* **B** (keep text, add artifact-parse gates, accept layout unverified) is refuted by B1 and S4b
  read together: the parse gate catches the brace and misses the 17-byte addition. "Layout is
  unverified by construction" is true of a text predicate and **false of this repository**, which
  ships Playwright, 14 e2e specs, and a config with no `webServer` at all. Accepting a limit that
  the tools on disk do not impose is the position I would have to defend, and I cannot.
* **D** is the status quo (L2). Choosing it is choosing B.

**The cost of C, measured rather than estimated.** The r5 note priced this as *"Costs
infrastructure."* It does not, and the precedents are both already in the repo and both documented:

1. **A fourth Playwright config with no `webServer`.** `playwright.prod.config.ts` is exactly this
   shape and says so: *"This one goes further — it has **NO `webServer` AT ALL**. There is nothing
   to start."* It is already wired as a gate (`npm run test:e2e:prod`). The reason `test:e2e` is not
   in CI — *"need a live Supabase stack"* — does not apply to a chrome spec, which needs no server
   and no database.
2. **A spec that renders in-process and serves the result to the page.**
   `tests/e2e/darkmode-html.spec.ts` is the worked precedent: it calls `renderMagazineHtml(...)` and
   fulfils the request through `page.route`, with no server.
3. **The assertion.** Mine is 77 lines total (24 Python to build a page from `page_chrome`'s own
   primitives, 26 JS for the band scan, 27 for a 4-position probe) and runs in **10.2 s** for 151
   scroll positions on one page, **2.8 s** for four positions (`time node band2.mjs`, `time node
   probe.mjs`). The predicate is three lines: *for each control, at each sampled scroll position,
   `rect.bottom > 0 && rect.top < innerHeight`.*
4. **CI**: `npx playwright install --with-deps chromium` plus one test invocation. No Supabase.
   Compare `schema-gates`, which builds a Postgres in 14 s and is a required check.
5. **The one real cost, which is M4**: if the browser case is to live *inside* the mutation harness
   so it can be mutation-tested, `PLAYWRIGHT_BROWSERS_PATH` must be threaded through `child_env`,
   and `node_modules/playwright` + `playwright-core` (17 MB) staged into `HARNESS_TREE`. Until that
   is done, the browser gate is a CI step with a `--self-test`-style falsifier of its own and **no
   mutation coverage** — which must be stated, not discovered.

**Scope of C, so it does not become a ninth fold.** One spec, one page per producer, one phone
viewport and one desktop viewport, a scroll band rather than fixed positions. ⛔ Not an attempt to
cover print, zoom, font reflow or real devices — those stay NOT RUN, named.

**What would make C wrong.**

* If a browser assertion over this property proves **flaky**, C is wrong and B is right, because a
  flaky gate is switched off (backlog #56's measured verdict) and a switched-off gate is worse than
  none. My falsifier: the band scan must be green on all five producers at both viewports on 10
  consecutive runs before it becomes a required check. I ran it twice on `gen-dashboard` output with
  identical results; **10 runs over 5 producers is NOT RUN.**
* If the browser gate turns out to need the app stack after all — if, say, a composed explainer
  cannot be generated without a live server — the cost argument collapses into the reason `test:e2e`
  is out of CI. Evidence against: I generated real `gen-dashboard` output with no server. Evidence
  for the risk: **it needed a seeded `~/explainers/`** (`brief-compose` lifts the Ask tray from the
  newest live page, and an empty directory is a hard refusal — *"no explainer directory … run
  /explain-diff once first"*). A spec over `page_chrome`'s own primitives avoids this; a spec over
  the real producers must seed a fixture directory.
* If B1 cannot be reproduced on the other four producers, the finding narrows to one page and C is
  oversized. **NOT RUN** — see below.

---

## The Phase 6 question no tool can see: what did we decide on this branch that is not written down?

Four decisions, each load-bearing, each absent from `CONTEXT.md` (at the committed tip),
`docs/adr/` and the specs.

1. **The declared subject bound** — that these assertions describe markup from this repository's
   generators and explainer skills, never adversarial markup. It is candidate D, it was *decided*,
   it is *implemented*, it is *witnessed by five cases*, and it exists only in a module docstring
   (`scripts/page_chrome.py:30-45`) and two review notes. It bounds what a guard claims, which is
   the exact subject of ADR-0014. **This is the ADR this branch owes.**
2. **That reachability is asserted as a MECHANISM and never as a layout fact** — the sentence at
   `:67-72`. The whole Phase 6 question is a dispute about this decision, and it is recorded in a
   docstring paragraph that a reader has to reach line 67 of a 2,557-line file to find.
3. **"MECHANISM SHARED, PALETTE LOCAL"** (`:17-23`) — one module owns the attribute, the button,
   persistence and the OS fallback; each of six pages keeps its own colours and must define both
   `data-theme` blocks. That is a cross-generator architecture decision with a stated rejected
   alternative (*"Emitting one palette from this module would flatten six pages"*). Textbook ADR,
   no ADR.
4. **That exact-expression assertions are the repair for ambient suppliers** — adopted across
   rounds 6, 7 and 8, argued at `:1930-1945`, and now the suite's dominant idiom. B1 is the finding
   that this decision was half of a repair. It was never written anywhere a future round would read
   before repeating it.

A fifth, smaller one: **one page is knowingly excluded** — `2026-10-05-topic-why-x-not-y` gets no
chrome script because its fragment declares an incomplete palette. That is recorded once, in the r6
note's *NOT RUN*, which is where things go to be forgotten.

---

## NOT RUN

Each is a failure, not a pass.

* **The full mutation sweep.** `python3 scripts/check-plan-code.py --mutate .` over 1,545 declared
  mutations in 62 manifests is beyond this review's budget. I tried to scope it by pruning the
  manifest directory to `page_chrome.json` in a copied tree; the ratchet correctly refused in
  **0.156 s** (`✗ … manifest holds 0 mutation(s), expected N` ×60, then `NOT MEASURED — the
  mutation harness produced no coverage verdict`). I did **not** edit `EXPECTED_MUTATIONS` to get
  past it, because an instrument that edits the harness is measuring a tree it changed. **No
  mutation tally of mine appears anywhere in this review**; the severance battery is what I ran
  instead, and for B1 it is the stronger instrument, since the manifest is 98% non-additive.
* **Four of the five producers in a browser.** Only `gen-dashboard.py` output was measured. The
  others need a seeded `~/explainers/`; I seeded only from repo-tracked `docs/explainers/*.html`
  under a redirected `$HOME` and stopped there rather than touch the reader's live pages.
* **Two of my own severances are unwitnessed in the browser and I am not claiming them.** S10
  (`tailPx` zeroed after the asserted expression) and S5b (the reserve overwritten with `0px`) both
  left the suite at **223/223** and both passed `node --check`, but at my sampled scroll positions
  every control stayed reachable, so the regression is real in the source and **not witnessed in a
  browser**. S5b's defect is a jump at the pin transition, which discrete sampling cannot see by
  construction. Reported as survivors of the suite, not as reachability failures.
* **Flakiness of the proposed gate**: 10 consecutive runs × 5 producers × 2 viewports. Two runs on
  one producer is not that.
* **Real device; physical print; zoom; font-load reflow; late images; the
  no-`IntersectionObserver` fallback in a browser; CI** (I ran nothing in CI).
* **The Codex half and the coordinator's new inventory document**, deliberately unread, for
  independence.

---
---

# ADDENDUM — the coordinator's two post-dispatch leads, measured

Added after the body above was filed. Both leads were put to me as *refute or confirm*; I did both.
**Lead 1 confirms and its proposed cheap remedy is refuted. Lead 2 confirms, with better evidence
than the grep it rests on — and its mechanism is not the one the lead names, which changes the fix.**

### H3 — High, **structural**. Lead 1 confirmed independently — and the cheaper remedy its own finding floats, *execute the script under Node rather than only parsing it*, is the same instance-not-class error one level up

**Confirmed, from my own fixture, not the coordinator's.** Prepending one statement to the emitted
script — `"throw new Error('x');"` immediately after the `/*yps-chrome-v1*/` marker at
`scripts/page_chrome.py:981`:

| Gate | Result |
|---|---|
| `python3 scripts/page_chrome.py --self-test` | **223/223 passed** |
| `node --check` on `chrome_script()` | **passes** |
| `assert_wired(page, …)` | **ACCEPTED** |
| Chromium 320×568, bar `position` | **`static` at every sampled scroll position** |
| theme control | `−155.9 … −2855.9` at scrollY 300 … 3000 |
| `--chrome-h` / `slot.style.minHeight` | **empty** — the script never ran, so nothing was published |

My coordinates differ from both the coordinator's (`−1912.94`) and the Codex half's (`−1926.38`)
because the filler differs; the coordinator is right that **the finding is the disagreement between
instruments, not any coordinate**, and I endorse that framing rather than adding a fourth number to
be cited.

⛔ **BUT THE REMEDY IN F1's OWN *"what this does not license"* PARAGRAPH IS WRONG, AND MEASURABLY SO.**
It says: *"executing the script under Node — rather than only parsing it — would close this specific
class far more cheaply, and nothing in the inventory considers that option."* I considered it and
ran it. `jsdom` is already a dependency (`node_modules/jsdom`), so this is a real option, and it is
cheap. Executing each page with `runScripts: 'dangerously', pretendToBeVisual: true`:

| Page | script threw | bar class after execution |
|---|---|---|
| unmodified (tip) | no | `"chrome chrome-pinned"` |
| one prepended `throw` | **YES — `Uncaught [Error: x]`** | `"chrome"` |
| **S8 (`arm=function(){};`)** | **no** | **`"chrome chrome-pinned"`** |

**The execution instrument returns the HEALTHY page's answer for the dead one.** Not a near miss —
a vacuous green, and I established why rather than guessing:

    control.html   theme rect: {"top":0,"bottom":0,"height":0} | innerHeight: 768 | IntersectionObserver: undefined
    s8.html        theme rect: {"top":0,"bottom":0,"height":0} | innerHeight: 768 | IntersectionObserver: undefined

jsdom implements **no layout** — every rect is zero on both pages — and provides **no
`IntersectionObserver`**, so the script takes its `if(!window.IntersectionObserver)` fallback at
`scripts/page_chrome.py:1172`, where `r.bottom - tailPx <= 0` evaluates `0 - 0 <= 0` → true,
`pin(true)` fires, and **both** pages come back pinned for a reason that has nothing to do with
reachability.

So the ordering of instruments is:

| Instrument | the `throw` | **S8** |
|---|---|---|
| substring / exact-expression cases | miss | **miss** |
| `node --check` (parse) | miss | **miss** |
| console-error read (one line) | **catch** | **miss** |
| Node/jsdom execution | **catch** | **miss, as a false green** |
| Chromium at a real viewport | catch | **catch** |

**This is why lead 1 alone cannot carry the decision, and why B1 must.** The `throw` announces
itself — `pageerrors: [ 'Error: x' ]` in my Chromium run — so it is closed by any instrument that
reads console errors, which is a one-line assertion and very much less than candidate C. **S8 raises
no error at all** (`pageerrors: none`) and survives every instrument short of a layout measurement.
If F1's `throw` were the strongest case, the proportionate answer would be *read the console*, not a
rendering gate. The case for C rests on the member of the class that is silent.

⚠ **And this is F1 committing the error F1 diagnoses.** Its own headline is *"the instance is closed;
the class is not"* about the parse gate. Proposing Node execution as the remedy closes a new instance
(the `throw`) and leaves the same class open — one level up, in the paragraph that was supposed to
state the finding's limits. Recorded plainly because this repository's record shows the fix for a
class defect is where the next instance of it appears.

**Severity High, not Blocking:** the diagnosis is right and already filed as backlog #305; what is
wrong is one sentence about the remedy, and it would have mis-sized the work.

### H4 — High, **structural**. Lead 2 confirmed. I searched specifically for the document that would collapse it, as asked, and found three statements saying the opposite — imperatively

The grep reproduces: `grep -ci "owner.s call"` is **0** in all five of `dev-process.md`,
`review-method.md`, `process-checklists.md`, `process-rationale.md`, `portable-practices.md`. Across
the whole repo the phrase appears only in records (`roadmap-to-launch.md`, `dashboard-entries.md`,
`backlog.md`), one memory file, one 2026-07 spec, and the chrome review documents themselves.

**I looked for the counter-example rather than agreeing.** I enumerated every mention of `Phase 6`,
`architecture review`, `THRASHING`, `arming`, `armed`, `convene` and `convened` across the five
process docs and `CLAUDE.md`. There is no document assigning the convening to the human. There are
three assigning it to the loop:

1. `docs/review-method.md:133` — Q5's table, which is the procedure for exactly this question:
   *"fix-induced findings, two rounds running, one component | **ARCHITECTURE REVIEW**"*. A cell in
   the *Then* column is an action, not a referral.
2. `docs/review-method.md:525` — the stop-condition table: *"**the architecture review.** This is the
   shape the trigger was bought for, and since 2026-09-14 it is the ARMING CONDITION itself"*.
3. `docs/review-method.md:178` — the rule stated as a rule: *"If a component produces findings caused
   by the PREVIOUS round's fixes in two consecutive rounds, **it escalates from FIX to REDESIGN, and
   the next round is a design review — not another defect hunt**."*

And `docs/dev-process.md:93`'s gate cell reads *"per **milestone** — **or on THRASHING: two
consecutive rounds whose findings came from the previous round's fix**"*, with no human marked, in a
column that marks them where they exist (Phase 1 *"user approval"*, Phase 5 *"Merging is a human
gate"*).

⭐ **The strongest evidence is the one neither the lead nor the grep reaches: the spine's
Human-in-the-Loop policy names this exact situation and rules the other way.** `dev-process.md`'s
*Conditional AFK* section lists *"an adversarial-review round that **cannot converge**"* among the
cases that pull the human in, and then says: *"This collides with Iterative Re-Review, which says
keep going. **The rule is notify and continue.** Stop and wait only if (a) the human replies, (b) the
next action is outward-facing or irreversible, or (c) the fix is not clearly specified… **Continuing
while a notification is outstanding is correct; going silent is not.**"* Convening a review is none
of (a), (b) or (c).

**What IS routed to the human, so the finding is bounded and not overstated.** `review-method.md:124`
does mark one human gate in this neighbourhood: *"⛔ Never spend a round on (b) before offering 1–3
to the human"* — where (b) is **tree identity**, and 1–3 are land-editorial-fixes-first, keep the
last fixes uncommitted, and `NO-REVIEW:`. That is a human gate over *how to stop*, not over *whether
to escalate*. ⚠ It also means the branch inverted the one rule that does apply: it ran five rounds on
tree identity without offering options 1–3, which is what H2 measures independently (all seven
verdicts `dirty: {}`), and `:125` records the precedent — *"That is exactly what PR #302 cost,
twice."*

So lead 2 does not collapse. It strengthens: convening was not merely unassigned to the human, it was
assigned to the loop in three places and the spine's own escalation policy says *notify and continue*.

### H5 — High, **structural**. The mechanism is not a missing authority — it is a missing input. **0 of 15** of this branch's round documents carry the header the method doc requires, and the one script that can answer the arming question exits **CANNOT RUN (rc=2)** on this subject

This is the answer to the coordinator's ownership question, and it is **neither #184 nor #136**.

`docs/round-header-template.md:3` — *"Every **coordinator** round document carries this block
immediately after its title."* Its stated purpose (`:5-8`) is this decision and no other: *"The
decision procedure needs two counters — consecutive fix-induced rounds and rounds since a finding in
the deliverable. On PR #302 nobody kept either, **which is why four rounds ran where two were
owed**."* `review-method.md`'s Q6 points at it for the same reason: *"so the counters Q4 and Q5 need
are **derived rather than remembered**."*

Measured:

    this branch's round documents with a ```yaml header:   0 of 15
    round documents elsewhere in docs/reviews/ with one:   77

    $ python3 scripts/check-review-decision.py
    CANNOT RUN — a round document for 'chrome-bar-reachable' has no usable header:
      no ```yaml header block
    $ echo $?
    2

    $ grep -ril "check-review-decision\|ARCHITECTURE_REVIEW\|decision card" \
          docs/reviews/*/chrome-bar-reachable-*.md
    (no output)

Its suite is healthy — `61/61 self-test cases passed` — so this is not a broken guard. It is a
guard whose subject was never written, in 15 documents, across 8 rounds and 3 writers, while 77
documents elsewhere in the same directory comply.

**Why this is not a witnessed instance of #184.** #184's falsifier is *a decision the card would
have answered differently, with no record that the card was consulted.* The card **could not have
answered at all** here. That is a **cannot-run**, which `CONTEXT.md:129` and `CLAUDE.md` both class
as a failure and never as a pass — and the two have opposite remedies. #184's work item is *build a
caller*; building one on this branch produces `rc=2`, so #184's fix does not reach this. Nor is it
#136, which is about the *rubric* for continue-vs-stop; the rubric exists, is written in three
places (H4), and was not consultable.

**So the honest causal chain for the five folded rounds is:** the counters the decision procedure
needs were never recorded → the only instrument that reads them cannot run → the arming call had to
be made from recall → it was, five times, and attributed to an authority that does not exist (H4).
The repo predicted exactly this: *"On PR #302 nobody kept either, which is why four rounds ran where
two were owed."* The template was bought with that failure and this branch skipped it in every
document, so the failure recurred — five rounds where **zero** were owed.

**Cheapest fix, and it is not a new mechanism.** Backfill the header on the three coordinator notes
(`r3`, `r5`, `r6`) from evidence already in them — the per-round fix-induced tables are exactly the
counters — then run `check-review-decision.py` and record its answer. That is minutes, it makes the
arming call derivable rather than argued, and it is the one action that would have prevented this
review's own existence. ⚠ It is also a **new backlog row**, not an amendment to #184 or #136: the
subject is *round documents do not carry the header their own template calls mandatory*, whose
falsifier is a count that is currently 0 of 15 against 77 compliant siblings.


## Verdict

**NOT CONVERGED**, and the reason is **B1**, which is new.

The answer to THE ONE QUESTION is **yes, move it — choose C** — but the inventory's two headline
arguments must be withdrawn before the decision is recorded: the invalid-JavaScript datum is closed
at tip (item 3), and the non-termination argument is false and measurably self-inflicted (H2). The
case stands on B1 alone, which is sufficient: 17 bytes, 223/223 green, parse green, guard accepting,
and the owner's original complaint live on a page a real generator produced.

H1 is a one-line fix and one case, independent of the decision — it should land whatever the owner
chooses. M1, M2 and L1 are corrections to the inventory, not to the code. M3 says F1 is unsupported
and the split it implies should not be built. M4 is the one cost of C that nobody has stated.

**On the addendum.** H3 confirms the runtime-vs-parse lead and **refutes the cheap remedy its own
finding proposes**: Node execution closes the `throw` and returns the healthy page's answer for S8,
because jsdom has no layout (every rect zero, no `IntersectionObserver`). That is the difference
between a one-line console-error check and candidate C, so it decides the size of the work. H4
confirms the authority lead and strengthens it — three imperative statements assign the escalation to
the loop, and the spine's own policy for a non-converging round is *notify and continue*. H5 is the
mechanism neither lead names and is the finding I would keep if I could keep one besides B1: **0 of
15** round documents on this branch carry the header their own template calls mandatory, against 77
compliant siblings, so `check-review-decision.py` exits **CANNOT RUN (rc=2)** and the arming call
could only be made from recall. It is **not** an instance of #184 (whose remedy, a caller, still
yields rc=2 here) or #136 (whose rubric exists and was not consultable) — it is a new row.

⚠ And the smallest thing in this review may be the most useful, now two things. **H2's fixed point
means this branch can clear its final-tree gate without a ninth round** — hold the fold uncommitted,
dispatch one round, commit it unchanged. **H5's backfill is minutes** — the three coordinator notes
already contain the counters in their per-round tables; writing them into the header makes the next
arming call derived rather than argued, which is the whole reason the template exists.

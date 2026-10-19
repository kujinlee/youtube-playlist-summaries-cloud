# chrome-bar-reachable — round 8, CLAUDE half

Primary subject: `e94d0e12` ("Round 8: the reserve becomes per-slot, and the backlog row I filed
an hour ago was wrong"), as the brief names it.

⚠ **THE BRANCH TIP MOVED UNDER THIS REVIEW AND IT CHANGES NOTHING.** When I started, `e94d0e12`
was the tip; it is now `HEAD~1`, because `546aed83` ("Merge remote-tracking branch
'origin/master'") landed at 11:01. `git diff e94d0e12..546aed83 -- scripts/ docs/backlog.md` is
**empty** — the merge carries `docs/dashboard-entries.md` and one design doc only — so every
measurement below is against the subject commit's own content. Said rather than assumed, because
a live tree under a running reviewer is this repository's recorded hazard.

Instrument: the three suites; the shipped mutation harness scoped to the two touched manifests,
run over BOTH this commit and its parent; a programmatic severance sweep over all 42
varied parameters of the two files; and Chromium (Playwright) at 320×568 over seven pages — four
hand-built from the branch's own `chrome_css()`/`chrome_script()`, two composed by the real
`brief-compose.py`, and two controls generated from the PARENT commit `bcdc0a61`. Every compose
ran under a redirected `$HOME`; the reader's live `~/explainers/` was never written (verified: 95
live pages, 0 containing `chrome-slot`).

**The fix is real and I could not refute it. Round 8's Codex half is also right that this fold
does not establish an eighth fix-created-next-finding round — the one growth loop I found still
live is measurably PRE-EXISTING. What this commit did introduce is a silent ratchet fall: a live
mutation entry was deleted rather than re-anchored, and the commit message accounts for one
retirement where there were two removals.**

---

## Blocking / High

**None.** What I tried, and why each attack failed, is in *Refuted* below. The headline claim —
that the per-slot inline reserve ends the continuous growth — reproduces, including through
`compose`, which the commit itself flagged as an unverified path.

---

## Medium

### M1 — Medium. A live mutation entry was deleted instead of re-anchored, so a case still in the suite lost its only falsifier — and the commit's housekeeping paragraph does not mention it

`scripts/mutations/page_chrome.json`, entry `"<body> reserves bottom padding again, for a bar
that pins at the top"`; its `expect` case is `scripts/page_chrome.py:1876`.

The commit's housekeeping paragraph says *"Four mutation anchors moved when the reserve changed;
two were re-anchored mechanically and ONE was RETIRED WITH ITS SUBJECT … A fifth entry was
re-pointed"*. Diffing the manifests across `bcdc0a61..e94d0e12`:

| | page_chrome.json | brief-compose.json |
|---|---|---|
| removed | **2** | 0 |
| added | 3 | 1 |
| changed in place | 2 | 0 |
| total | 87 → 88 | 25 → 26 |

The two re-anchored-in-place entries match the message. The retirement the message describes is
`"the page reserves no space for the pinned bar"`, and it is a correct one: its edit mutated the
`.chrome-slot{min-height:var(--chrome-h,0)}` text this fold deletes, so its subject is gone.

**The second removal is not accounted for anywhere.** Its anchor was

    f".{CHROME_SLOT_CLASS}{{min-height:0}}}}"

which this fold rewrote to `…{{min-height:0!important}}}}`. That is a one-token move, not a
vanished subject: the case it names —

    case("...and <body> no longer reserves anything, or a top-pinned bar would leave a "
         "blank band at the document end",
         "padding-bottom:var(--chrome-h" in chrome_css().replace(" ", ""), False)

— is **still in the suite, unchanged by this commit**. So a live case now has no mutation that
can redden it.

Measured, not argued, in both directions:

* **the entry was live and killing at the parent.** `git archive bcdc0a61` of
  `check-plan-code.HARNESS_TREE`, manifests pruned to the two under review,
  `EXPECTED_MUTATIONS` reduced to `{page_chrome: 87, brief-compose: 25}`:
  `[77/112] <body> reserves bottom padding again, for a bar that pins at the top` →
  `OK — 112 mutation(s), 112 killed, 112 attributed, 0 survivor(s)`.
* **it is re-anchorable in one token.** Re-added to the subject commit's manifest with the anchor
  text updated to `min-height:0!important`, `EXPECTED_MUTATIONS[page_chrome]` 88 → 89:
  `[115/115] <body> reserves bottom padding again…` →
  `OK — 115 mutation(s), 115 killed, 115 attributed, 0 survivor(s)`.

**Why no machine saw it, which is the part worth keeping.** Three entries were added in the same
commit, so `EXPECTED_MUTATIONS['scripts/page_chrome.py']` still *rose* 87 → 88 and the declared
sum still derives as 1543. Every published number is true and the coverage fell underneath them:
`--mutate .` reports on the entries that are present and is blind to one that is gone, and the
ratchet pin measures a total, not a set. This is the repository's own *"the only sanctioned
ratchet FALL is retiring an entry with its subject"* — and the subject here did not disappear.

⚠ **AND IT IS A FINDING CAUSED BY THIS ROUND'S OWN FIX.** That is half of the thrashing shape and
the owner should hold it against round 9: the fold changed one CSS token, four anchors moved, and
the response to the fourth was deletion. It does not make an eighth round of the shape by itself
(the shape needs the NEXT round's finding to come from THIS one's fix), but it is the first half.

Inside the declared subject: yes — the harness contract, not the markup subject.

Fix: restore the entry with the `!important` anchor and bump the pin to 89; or, if it is genuinely
to be retired, say so and say why, as the other retirement does.

---

## Low

### L1 — Low. `compose.generated_at` is varied-but-unwitnessed — the same class the commit's own LOW just closed for `compose.title`, in the same function, not swept

`scripts/brief-compose.py:887` — `chrome_css, chrome_bar, chrome_js = chrome_for(content, generated_at)`.

I reused Codex's method and widened it: for each of the **42** parameters of `page_chrome.py` and
`brief-compose.py` that `check-fixture-variation` reports as VARIED (examined, not in
`KNOWN_UNVARIED`, not `EXEMPT`), I rebound the parameter to a constant at the top of its own
function body inside a temp copy of the shipped harness and ran **both** shipped suites. Controls
first: 223/223 and 151/151 green before any severance.

41 of 42 reddened. **One survived:**

    SURVIVOR  scripts/brief-compose.py:compose.generated_at := "__SEV__"   ['223/223 passed', '151/151 passed']

Confirmed with the realistic shape rather than the synthetic one — the exact defect `compose.title`
had:

    -    chrome_css, chrome_bar, chrome_js = chrome_for(content, generated_at)
    +    chrome_css, chrome_bar, chrome_js = chrome_for(content, "")

→ `brief-compose 151/151 passed`, `page_chrome 223/223 passed`. No mutation entry covers it either:
no entry in `brief-compose.json` or `page_chrome.json` anchors that call. The reader-visible
consequence is observable, so a case *could* witness it —

    stamp_bar('2026-10-19 10:47 PDT') -> …<time>2026-10-19 10:47 PDT</time>…
    stamp_bar('')                     -> …<time></time>…

— every composed page would say `generated` over an empty `<time>`, with every gate passing.

⚠ **PRE-EXISTING, and I checked rather than assumed**: `compose(…, generated_at: str = "")` is
identical at the branch base `cf800e4e`. `chrome_for.generated_at` is separately witnessed (its
severance reddens, 150/151), so the witness exists one level down and the forwarding is the hole.

Filed anyway because of what the commit says about the two it fixed: *"⛔ SATISFYING A RATCHET'S
SOURCE-TEXT RULE IS NOT COVERING THE PARAMETER … a ratchet that keys on variation in the SUITE
TEXT cannot tell variation from witness"*. That is stated as a class, and the sweep stopped at the
two parameters the reviewer happened to name. This is the repository's *after fixing, SEARCH for
the class* in its cheapest possible form — the sweep is 38 seconds of machine time.

Inside the declared subject: yes.

### L2 — Low. The growth loop is narrowed, not closed: a `.chrome-slot` that is ALSO the `.chrome` bar still grows without bound

`scripts/page_chrome.py:1152` — `"slot.style.minHeight=h+'px';"`, with
`h = bar.getBoundingClientRect().height` at `:1150`.

`h` is a **border-box** height. `min-height` resolves against the **content box** unless the page
sets `box-sizing`, and `chrome_css` sets none. So whenever the chosen `slot` *is* the measured
`bar` — `closest()` matches self, so `<div class="chrome-slot chrome">` inside any outer slot
binds `slot === bar` — the write adds the bar's own `padding-block:.45rem` to it on every tick,
`ResizeObserver` fires, and it repeats.

Concrete failing input (served over `http://`, Chromium at 320×568, no scrolling, 11 samples at
220 ms):

    <div class="chrome-slot">
      <div class="chrome-slot chrome"> … #chrome-theme … </div>
    </div>

    --chrome-h        4337.39px  →  6251.34px
    document height      16033   →     17947
    content below     y=4422.30  →  y=6336.25      (2.2 s, still climbing)
    sameEl: true · box-sizing: content-box · barH − chromeH = 14.391px ≡ 2 × .45rem

⚠ **PRE-EXISTING — MEASURED, NOT INFERRED.** The same page generated from the PARENT commit
`bcdc0a61` grows too: `--chrome-h` 4294.22 → 5848.41px, document 15989 → 17544, content
y=4379.13 → y=5933.31 in 1.8 s. So this is **not** an eighth instance of "the fix created the next
finding"; it is the same class the fold narrowed, with one case left in it.

Outside the declared subject, and that is why it is Low rather than High: the module docstring
declares its subject as markup from *"this repository's five generators or … its explainer
skills"*, and `grep` finds exactly two emitters of the slot class — `page_chrome.py:1231`
(`stamp_bar`) and `:1327` (`chrome_bar`) — both of which **wrap** the bar in a separate slot
element. No generator, and no path through `brief-compose`, can put both classes on one element.

What makes it worth a line anyway is the **termination argument**. The code comment at `:1148`
reads *"A nested slot the script did not select now reserves nothing, so it cannot grow and cannot
inflate the bar being measured"*, and the commit message repeats it. Both sentences are true as
written — they are about slots the script did *not* select. Neither states the slot it *did*
select, and the block's `⚠ THE BOUND THIS DESIGN ACCEPTS, STATED:` paragraph lists only the
resize-while-pinned bound. On this repository's own standard a bound enumerates what is witnessed;
this one is one case short.

Closing it is one token: `slot.style.boxSizing='border-box'` alongside the write, or measuring the
slot's content box instead. Neither is urgent.

### L3 — Low. A stale comment, on the very constant the fold changed the meaning of

`scripts/page_chrome.py:328`:

    # ⚠ THE SLOT IS WHY PINNING DOES NOT JUMP THE PAGE. … The slot holds
    # `min-height:var(--chrome-h)` — the height the bar reported while it was still in flow

After this commit the slot holds an **inline** `min-height` the script writes, and
`.chrome-slot{min-height:var(--chrome-h,0)}` is deleted — the CSS note at `:904` says so, and the
new self-test case asserts the class rule's absence. This is `CHROME_SLOT_CLASS`'s own defining
comment: the first thing a reader of the constant sees, and it now names the deleted mechanism as
the live one.

Not caught by anything: `check-docs`, `check-doc-citations` and `check-canonical-source` are all
rc=0, and none of them reads code comments for a mechanism claim.

(For contrast, `:899` — *"The slot holds exactly that and the `<body>` rule is gone"* — is still
true and needs no edit. One comment of the pair moved and the other did not.)

Inside the declared subject: yes.

---

## Refuted — attacks that failed, with the measurement

Listed because a reviewer's negatives are only worth anything if the attempt is on the record.

**R1 — the headline claim reproduces, and ALSO through `compose`.** The commit admits it verified
the nested shape on a hand-built document and not through the composer. I did both.

* Hand-built nested shape (a `.chrome-slot` nested inside the measured bar), 12 samples over
  2.4 s: `--chrome-h` **stable 102.859375px**, document height **stable 11784**, content
  **stable at y=173.38**, `slotMinHeights` **`["102.859px", "(none)"]`** — the unselected slot
  reserves nothing, which is the mechanism the commit claims.
* **Control, same fixture, parent commit `bcdc0a61`:** `--chrome-h` **18490.98 → 28195.83px**,
  document **30245 → 39950**, content **y=18634.47 → y=28339.31** in 2.2 s. The fixture does carry
  the loop; the fix is what stops it.
* **Through the real composer.** `brief-compose.py --content <nested fragment>` under a redirected
  `$HOME`, output loaded over `http://`: **stable over 2.3 s** — `--chrome-h` 78.265625px,
  document 18749, content y=195.14, `slotMinHeights` `["78.2656px", "(none)"]`,
  `allEqual: true` across 11 samples. The commit's self-declared verification gap is closed, on
  the delivery path, with the same verdict.

⚠ The commit's absolute figures (53.17px / 6133 / y=133.05) are **not reproducible** and I am not
calling that a finding: they come from a fixture that is not in the repository, the commit says so
in the line that reports them, and the bar's wrapped height is set by its container's width — the
exact input `:1176` already explains nobody controls. The *properties* reproduce; the pixels are
fixture-local and labelled as such.

**R2 — flat control: no jump, reserve equals the bar.** 10 samples, then a scroll to 1200 and
back. `#below` in document coordinates: **133.891 before the pin, 133.891 after** — zero jump.
Reserve 63.375px against an in-flow bar of exactly 63.375px. The pinned bar measures 64.375px,
i.e. the **1.0px overlap already recorded** as r8 CLAUDE LOW at `:1197` — reproduced, not new.

**R3 — "print now needs `!important`" is true and it works.** Emulating `media: print` on the flat
page: inline `min-height` 63.375px, **computed `min-height` 0px**, bar `position: static`, slot
63.375px (the bar's own height, back in flow). No blank band. The mutation entry
`"print stops releasing the slot's reserve, so the band prints"` and the case
`"the pinned bar returns to the flow in print, and frees its reserved space"` both exist and kill.

**R4 — "a second `sync()` on a DIFFERENT slot leaving the first one's reserve stale" is not
reachable.** `slot` is bound once, at `:1055`–`:1062`, before the `#schemer` move, and is never
re-assigned; `sync` has no parameter and closes over that one binding. There is no second
selection to disagree with. Two script instances cannot select differently either — same
predicate, same DOM order — and `assert_wired` refuses the duplicate ids that would be needed to
get two.

**R5 — the pinned/unpinned guard still covers BOTH writes, and a case proves it.** Both
`slot.style.minHeight=h` and `setProperty('--chrome-h',h)` sit after
`if(bar.classList.contains('chrome-pinned'))return;`, and both read the same `h`. I hoisted the
measurement and the writes above the guard — r6's exact class, a write escaping the guard — and
the suite went **222/223** on *"the reserve, the gap and the re-arm are all behind ONE guard that
returns"*. The pair-case the commit added (*"the same measurement feeds both the slot and
scroll-padding, so they cannot disagree"*) also pins both strings on `h`.

**R6 — "a slot that needs a reserve and never gets one" did not materialise.** The only slot that
can pin is the one holding the bound bar, and that is the one that gets the inline write. A
stamp-only sibling slot never pins, so it needs no reserve — and under the deleted class rule it
*was* getting one, which is the cosmetic band #302 originally described. On that axis the fold is
strictly better, not worse.

**R7 — page CSS overriding the reserve is a WEAKER hazard than before, not a stronger one.** An
inline style beats any normal author rule, so a page declaring `.chrome-slot{min-height:…}` can no
longer silently replace the reserve — under the class rule it could, on source order alone. The
one surviving override is `!important`: a page with `.chrome-slot{min-height:0!important}` gets
computed `min-height` 0 against inline 63.375px and the content jumps **−63.375px** at the pin
(measured). Identical before the fold, no producer emits it, not filed.

**R8 — a padded slot does not loop.** `.chrome-slot{padding-block:10px;border-top:2px}` in page
CSS: stable over 1.8 s, reserve 63.375px not binding against a 85.375px slot, jump at pin **0**.
Only `slot === bar` loops, which is L2.

**R9 — the fix is not retroactive, and there is nothing to retrofit.** `brief-compose` round-trips
a fragment, so the chrome text travels with it: recomposing the pre-fix fragment another agent
produced an hour earlier preserves the deleted `.chrome-slot{min-height:var(--chrome-h,0)}` rule
in the output, and a page carrying that rule plus the new script grows **11978.5 → 17251.4px in
1.8 s** through the real composer with `brief-compose` exiting 0. **Not filed**: the population is
empty — 0 of 81 committed `docs/explainers/*.html`, 0 of 95 live `~/explainers/*.html`, and 0
tracked files of any kind contain `chrome-slot`, because the slot has never shipped. A zero over
nothing is not a finding. The falsifier if it ever does ship: `bar_unreachable` refusing a page
whose CSS matches `\.chrome-slot[^{}]*\{[^}]*min-height:\s*var\(`.

**R10 — backlog row #302 is accurate and its closure is real.** The row quotes its own wrong claim
(*"cosmetic, it occludes nothing"*) verbatim, states the correction with the Codex numbers, keeps
the PRE-EXISTING verdict, and names the fix. Its titled defect — the class selector consuming a
document-level reserve — is gone from `chrome_css` and the new case refuses its return, including
a reintroduction spelled `min-height:var(--chrome-h)`. L2 is a *different* mechanism (an inline
reserve on an element that is both slot and bar) and belongs in a new row, not against this
closure.

**R11 — the two newly-witnessed parameters are genuinely witnessed.** Severed inside the shipped
file and run through the shipped suites:

    assert_wired.where := "p"   → 221/223   [FAIL] the refusal names the CALLER's label…
                                            [FAIL] …and two distinct labels give two distinct messages
    compose.title    := "T"     → 149/151   [FAIL] the requested title reaches the document's <title>…
                                            [FAIL] …and a different request gives a different document

**R12 — every declared number in the commit message reproduces.**

| Claim | Result |
|---|---|
| `page_chrome --self-test` 223/223 | ✅ 223/223, rc=0 |
| `brief-compose --self-test` 151/151 | ✅ 151/151, rc=0 |
| `check-plan-code --self-test` 178/178 | ✅ 178/178, rc=0 |
| `check-docs` rc=0 | ✅ "Documentation integrity OK" |
| `check-features` rc=0 | ✅ 26 nodes, 13 anchors, 21 areas |
| real harness, both whole manifests: 114 / 114 killed / 114 attributed / 0 survivors | ✅ verbatim, 57 s |
| page_chrome 87 → 88, brief-compose 25 → 26 | ✅ both |
| declared sum DERIVED with `ast` as 1543 | ✅ 1543 across 62 files |
| "two re-anchored mechanically" | ✅ 2 changed in place |
| "ONE was RETIRED WITH ITS SUBJECT" | ⚠ **2 removed** — see M1 |
| seven consecutive rounds, not eight | ✅ consistent with `c293e31b` |

Also run, unprompted, because this branch has twice been caught by a guard it did not think to
run: `check-fixture-variation` rc=0 (870 parameters / 67 files / 114 ratcheted),
`check-selftest-counts` rc=0 (53 declared counts, every one verified by running it),
`check-test-counts` rc=0, `check-anchors` rc=0, `check-doc-citations` rc=0,
`check-dashboard-entry` rc=0.

⚠ `check-review-rounds` is **rc=1** — *"chrome-bar-reachable round 8: only codex — claude neither
ran nor recorded a `REVIEW GAP:` line"*. That is this file's absence and it goes green when this
file lands. Noted so the red is not mistaken for something else at merge time.

---

## Verdict

**NOT CONVERGED.**

Nothing I found contradicts the fix. The growth loop the fold was written for is closed on the
nested shape, on the flat control, in print, and — which the commit could not show — through the
real composer; and the one growth loop still live is measurably older than the fold.

The reason for the verdict is **M1**, and it is cheap: one manifest entry re-anchored by one
token, one pin raised 88 → 89, and one sentence in the record corrected from *one retirement* to
*one retirement and one deletion, because…*. It is a Medium rather than a Low because the thing
lost is falsification — the case at `:1876` currently cannot be shown to be able to fail — and
because the loss was invisible to every number the commit published. L1 is one 38-second sweep
and two cases. L2 and L3 are a token and a sentence.

On thrashing: **M1 is a finding caused by round 8's own fix.** One is not the shape; it is the
first half of it. If round 9 produces a finding caused by round 9's fix, the arming condition in
`dev-process.md` is met on this component and the answer is Phase 6, not a ninth fold. The verdict
as it stands is still seven rounds, not eight.

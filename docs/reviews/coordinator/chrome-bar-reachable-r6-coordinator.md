# chrome-bar-reachable — round 6 coordinator note

```yaml
round: 6
fixes_nontrivial: true
subject: chrome-bar-reachable
halves:
  codex: ran
  claude: ran
findings:
  - {id: codex-H1, severity: High, aim: deliverable, fix_induced: false, component: page_chrome, disposition: fixed}
  - {id: codex-M1, severity: Medium, aim: deliverable, fix_induced: false, component: page_chrome, disposition: fixed}
  - {id: codex-M2, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: claude-B1, severity: Blocking, aim: deliverable, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: claude-H1, severity: High, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: claude-H2, severity: High, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: claude-H3, severity: High, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: claude-M1, severity: Medium, aim: deliverable, fix_induced: false, component: brief-compose, disposition: fixed}
  - {id: claude-L1, severity: Low, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
```

## Verdict: THRASHING, not a prose floor. Phase 6 is armed, and this is the evidence.

`dev-process.md` requires this question to be answered in the round document, with
per-finding evidence, rather than by a round count. The answer is thrashing, and round 6
is the clearest instance yet because the thrash happened **inside a single round**.

| Round | Findings caused by the previous fix | Component | Note |
|---|---|---|---|
| r2 | 4 | `page_chrome.py` | substring predicates from r1 |
| r3 | 5 | `page_chrome.py` | regex predicates from r2 |
| r4 | 3 of 8 | `page_chrome.py` | the id predicates r2 left behind |
| r5 | 7 of 8 | `page_chrome.py` | all in `_Scan`, added by r4 |
| r6 | **3 of 6, within the round** | `page_chrome.py` | see below |

Round 6's own sequence, in order, all in one component:

1. Codex found the pin threshold keyed on the SLOT rather than the control (Medium).
2. The fix for it keyed on the LOWEST control. Moving the switcher into the bar — the
   owner's choice, the same round — made the bar wrap to two rows, and then the first
   control to leave the viewport is on the TOP row. **The fix created a new instance of
   the class it fixed.** Measured: theme button at -30.9, schemer at +81.2, unpinned.
3. The fix for THAT shipped `arm()` outside a braceless guard, which Claude measured as a
   **non-terminating render loop on a production generator's page** — 60 class flips per
   second on a stationary dashboard — and which reinstated finding 1 in the same band.
4. The fix for THAT dropped a closing brace. The emitted JavaScript was invalid, every
   control on every page was inert, and **201 text cases were green over it**.
5. The comment-stripping fold shipped a second, NAIVE implementation of a rule this
   repository already owns and records as defective, 400 lines from the original, with a
   measured fail-open on the dominant caller.
6. The three cases written to defend the threshold fix were **lexically unfalsifiable**:
   the reviewer severed the rule two ways and the suite stayed green both times.

## Why this is not a prose floor, stated as the test the method requires

*Can a redesign remove these findings?* **Yes, and the redesign is identifiable.** Every
one of 2, 3, 4 and 6 is a defect in TEXT ASSERTIONS ABOUT A LAYOUT FACT. The property is
*a reader can reach the control*, which depends on document height, viewport, container
padding, wrapping and scroll position. No predicate over HTML can compute it, and six
rounds of instruments — substring, regex, comment-stripping regex, `html.parser`, a
caller-supplied fact, and now exact-expression assertions — have each failed in a new way.

The r5 note put three options to the owner and this round supplies the missing evidence
for option 2. **Every real defect in round 6 was found in a browser, and every fix was
verified in one.** Claude's Blocking was found by counting class mutations on a generated
page; the threshold defect by measuring a button's box at one scroll position; the invalid
JavaScript by reading a console error. The repository already depends on Playwright, and
this round used it throughout. The instrument exists; it is simply not wired into a gate.

⚠ AND THE HONEST COUNTER-ARGUMENT, because it is not weak: the DEFECT DENSITY of round 6
was in the guard, but the owner's actual complaint — the controls are unreachable — is now
fixed and browser-verified on all five producers. A reasonable reading is "the feature is
done, stop reviewing the guard". The reason that is not sufficient is the invalid
JavaScript: a 201-case suite was green while every control on every page was dead. That is
not a prose defect and it will recur, because nothing in the suite watches the artifact.

## What this round actually delivered, and it is not small

* The owner's complaint is fixed on all five producers, measured in a browser at two
  viewports, with both controls reachable at every sampled scroll position.
* `strip_css_comments` and `css_of` now have ONE implementation, in the module both can
  reach, and the CSS-reading predicates read applied CSS rather than raw page text — which
  closed r1's F7 class at its source as well.
* The emitted script is now PARSED by a case (`node --check`), which is the gap that let
  invalid JavaScript ship behind a green suite.
* `page_chrome.self_test` reports an abort as a named failing case, a protection
  `brief-compose` has carried since r1 and that never reached its sibling.

## ⭐ THE ARGUMENT THIS NOTE WAS MISSING, ADDED 2026-10-19 AFTER ROUND 8

**The fold-then-review cycle has no fixed point on this branch, and `check-review-recorded`
proves it mechanically rather than by argument.**

That gate requires some round to have seen the CURRENT tree. But every fold commits guarded
code *after* the review that prompted it. So:

* a round finds something → it is folded → guarded code moves → the gate goes red again;
* the loop terminates only on **a round that requires no fold at all**.

Eight rounds have not produced one. Round 8's Codex half came closest — it found no eighth
fix-created-finding sequence and said the commits under review were substantive — and its
Claude half still returned a Medium (a mutation entry deleted while its replacement was
added, so the pin ROSE while coverage fell), which needed a fold, which re-reddened the gate.

⚠ THIS IS NOT A COMPLAINT ABOUT THE GATE, which is correct and has caught real things. It is
the observation that **"review until converged" is not a terminating procedure here**, and
the reason is the same one this note already gives: the property under review is a LAYOUT
fact, the instrument is text, and each new text instrument has its own defects to find. A
procedure whose stopping condition is "a round with no findings" cannot stop while the
instrument keeps generating them.

That is the strongest single argument for moving the claim to a rendering assertion, and it
is an argument about the PROCEDURE rather than about any one defect — which is why it belongs
in a Phase 6 inventory and not in a round document.

⚠ AND THE HONEST COUNTER: the branch could also stop by DECLARING the stop — the repository
provides `NO-REVIEW: <reason>` in the pull-request body for exactly this. That is a judgement
about accepting an unreviewed fold, which is the owner's and not the coordinator's.

## Recommendation to the owner — a decision, not a defect

Convene the Phase 6 architecture review on ONE question: **should the reachability claim
move from a text predicate to a rendering assertion?** The inventory is this document plus
the r5 note. ⛔ Not convened here; `dev-process.md` makes it the owner's call, and this is
the second round to say so.

## Bounds, unchanged

Reachability remains a MECHANISM assertion in text; the consumption claim is "no at-rule"
and nothing more; pair-coverage is not claimed; branches 1 and 2 of `chrome_for` are
outside the consumer guard. The subject is markup from this repository's generators or its
explainer skills, and four r5 shapes plus one r6 shape are recorded as out of scope with
cases that redden if the scan is tightened.

## NOT RUN

A real device; physical printing; zoom; font-load reflow; late images; the
no-`IntersectionObserver` fallback in a browser; CI (there is no PR yet, so every gate on
this branch is local). One page — `2026-10-05-topic-why-x-not-y` — gets no chrome script
at all because its fragment declares an incomplete palette, so the switcher fix does not
reach it; that is the pre-existing incomplete-palette gap, not this round's work.

## Header provenance — backfilled 2026-10-24 (backlog #306), DERIVED, not remembered

Sources: both halves (`codex/…-r6-codex.md`, `claude/…-r6-claude.md`), and the five fold commits
`38e31fc6`, `a0fe9916`, `2ee4371c`, `cbf0e294`, `003fb932`. Ids are prefixed by half, because
each half numbers from 1.

* **codex-H1** fragment switchers outside the bar scroll away · **codex-M1** the threshold keyed
  on the slot, not the control · **codex-M2** the CSS-comment exclusion · **claude-B1** the
  `arm()` render loop · **claude-H1** the comment strip reached one arm of five · **claude-H2** a
  second, naive comment-strip implementation · **claude-H3** three lexical threshold cases ·
  **claude-M1** the composer's stale r1 premise · **claude-L1** the strip's space un-welds a selector.
* **`fix_induced`:** `true` where the half or the fold commit names a fix written after an earlier
  review as the cause — codex-M2 (the r5 fold's exclusion), claude-B1 (*"Codex finding 2 is
  reinstated by its own fix"*), claude-H1/H2/H3/L1 (all in `38e31fc6`'s fold). `false` for
  codex-H1 (*"a real defect in the owner's original complaint"*), codex-M1 (the origin of the
  sequence above, item 1) and claude-M1 (r1's comment, made stale by the bar's move at `de48f095`).
  ⚠ **That is 6 of 9, and the table above says "3 of 6".** They count different populations: the
  table counts this note's own six-step sequence, two of whose steps — the wrap and the dropped
  brace — were found while folding and were never filed by a reviewer. The header counts filed
  findings only.
* **`aim`:** `deliverable` for the three in the emitted page or its script (codex-H1, codex-M1,
  claude-B1) and for claude-M1, whose file ships — conservatively, since the defect is a stale
  comment rather than behaviour and `deliverable` is the stricter reading. The rest sit in the
  guard or its cases.
* **`disposition`:** codex-H1 `a0fe9916` (owner's option: the switcher joins the bar); codex-M1 and
  codex-M2 `38e31fc6`; claude-B1 and claude-H3 `2ee4371c`; claude-H1 and claude-H2 `cbf0e294`;
  claude-M1 `003fb932`. claude-L1 is **declined** — `003fb932`: *"RECORDED, NOT FIXED … a comment
  inside a selector NAME is adversarial markup, which the declared subject excludes"*.

## The decision procedure, run after the backfill — its answer is STILL CANNOT RUN, for a new reason

Run 2026-10-24 by importing `check-review-decision.py` and calling `rounds_for` then `decide` on
this subject (the script's `main` decides for the CURRENT branch, which is no longer this one):

```
rounds_for('chrome-bar-reachable') -> r3 (6 findings), r5 (8), r6 (9)   — all three headers PARSE
decide(..., 'full-loop', True)    -> CANNOT_RUN: rounds are not gapless: found [3, 5, 6],
                                     expected [1, 2, 3] — refusing to infer adjacency   (rc=2)
```

⛔ **The CANNOT RUN moved from *no header* to *no round 1, 2, 4, 7 or 8*.** The procedure reads
coordinator documents only, and this branch wrote coordinator notes for three of its eight rounds;
the other five exist only as halves, which `round-header-template.md` says structurally cannot carry
`disposition` or `fixes_nontrivial`. So backlog #306's falsifier as written — *15 of 15 compliant* —
is not reachable by the backfill its own WORK names, and **rc=2 here must not be read as "no
thrashing"**. Its arming question was answered in this note's own prose (THRASHING, armed at r3) and
by the Phase 6 review it led to; the instrument has not answered it. Reaching an answer needs five
more coordinator documents written with hindsight, which backlog #318 and #314 caution against, or a
change to what `sequence_error` asks — a decision, not a backfill, and it is recorded on #306.

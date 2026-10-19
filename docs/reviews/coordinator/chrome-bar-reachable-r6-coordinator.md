# chrome-bar-reachable — round 6 coordinator note

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

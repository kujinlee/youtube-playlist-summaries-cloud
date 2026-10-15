---
name: a-bound-enumerates-what-is-witnessed
description: "FIRES-WHEN: writing the ⚠ BOUND / 'what this does NOT cover' paragraph for a seam, double or injection point — ⭐ I listed what the seam TOUCHES and claimed the cases covered it; they witnessed 3 of 4. Enumerate from the ASSERTIONS, never from the signature. A caveat headed 'stated rather than hidden' that is wrong is worse than no caveat"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cacb274e-95ca-4cc6-b810-ebd8b4fe9634
  modified: 2026-10-07T09:39:00.429Z
---

**Measured 2026-10-06/07, PR #364 round 5 (High 1, in the deliverable).** I added a `measure_fn`
seam to `check-page-contrast.py` and wrote the careful bound paragraph myself:

> ⚠ THE BOUND, STATED RATHER THAN HIDDEN. A `measure_fn` double covers this function's DECISION
> path — corpus resolution, **palette selection**, verdict rendering, refusal routing.

**It named four components and the cases witnessed three.** Severing the palette path four ways each
left the suite at **104/104 GREEN**: `extra = ""`, `--raw`/default inverted, the `--extra-css` branch,
and `extra_css` dropped from the call site. ⛔ The first of those **reinstates the original defect the
whole harness exists to prevent** (the gate measuring bare files instead of what a reader sees) — and
the comment three lines above that branch says so in writing.

## Why I got it wrong, which is the transferable part

I enumerated **what the seam passes through** — the signature — instead of **what the cases assert**.
A seam forwards four arguments; a recorder that records two of them proves two. "Covers the decision
path" is a claim about the code's shape; only the assertions can earn it.

> **Write the bound by listing the assertions and asking what each one would notice. Never by
> listing the arguments the seam touches.**

## ⭐ The defect had the shape of the bug it was fixing

The recorder was `def fn(pages, extra_css="", root=None, **kw)`: it recorded `root` — a deliberate
sentinel, asserted twice — and absorbed `extra_css` into a default it never reads. **One argument
threaded and witnessed, its sibling threaded and ignored.** That is exactly backlog #239's shape,
*inside the fix for #239*. After fixing a one-argument-not-threaded defect, grep the siblings:
[[after-fixing-search-for-the-class]].

## ⚠ A self-aware caveat raises the stakes, it does not lower them

The paragraph was headed *"STATED RATHER THAN HIDDEN"*. A reader trusts that heading and stops
checking, so a wrong bound there is worse than silence. Related:
[[a-stated-bound-outlives-its-hole]], [[assert-the-property-not-the-mechanism]],
[[a-framing-widened-to-fit-is-no-longer-a-claim]].

## What to do when a round finds this

Split it: **correcting the false claim is not a fold** and is never optional — ship no knowingly
false sentence, and put the corrected bound on **every** site that carries it (mine sat on one of
three closure rows). **Closing the capability gap is new work** and new ratchet surface, so it is the
owner's call when a fold has been stopped. On #364 the owner chose *file both, stop here*.
See [[a-side-job-gets-a-name-first]], [[feedback-agree-before-filing]].

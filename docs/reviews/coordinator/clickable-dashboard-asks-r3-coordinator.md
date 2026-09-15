# clickable-dashboard-asks — round 3, coordinator adjudication

**REVIEW GAP: claude** — as rounds 1 and 2; this session does not spawn subagents. Cost
stated in the r1 document, unchanged.

* Codex: `docs/reviews/codex/clickable-dashboard-asks-r3-codex.md` (`gpt-5.5`) —
  **0 Blocking, 0 High, 1 Low. CONVERGED.**
* Verdict: `docs/reviews/verdicts/clickable-dashboard-asks-r3-codex.verdict.json`.

Round 3 was called as a **verification round** against the final tree, because both of
round 2's repairs postdated the tree round 2 saw.

## What it verified, by re-derivation rather than inheritance

The brief required re-deriving earlier rounds' cleared attacks. It did, and all held:

| re-derived | result |
|---|---|
| the `f !== stale` identity check | sound — the live artifact removes the old floater (`dashboard.html:6949`) then creates a **fresh** one (`:6954`), so identity can distinguish them |
| the under-3-character path | terminates correctly: the tray removes the old floater and returns without creating one, so the poll exhausts into the bounded fallback |
| the `h4` section resolution | questions render `<h4 class="q">`; the tray injects heading buttons into `h2, h3` only |
| the collapsed-title guard | correctly scoped, with its non-vacuous assertion present |
| every declared count | `325/325`, `128/128`, `EXPECTED_MUTATIONS` 68, declared sum 633, manifest 68 entries — all four agree |

⭐ The identity check was the sharpest attack in the brief precisely because its failure
mode is silent and total: had the tray reused one floater element, `f !== stale` would
never be true and **every** chooser would fall through to the fallback. Independently
measured by the coordinator (`f1 !== f2` across two selections) and by Codex against the
artifact.

## L1 — the rule-scanner's corpus and its value test

**ACCEPTED AND FIXED, both halves.**

(a) It parsed the **whole rendered document**, not the stylesheet, so a script string
`.pick{display:none}` would have been read as CSS and reddened the suite. Not theoretical
housekeeping: the tray's own JavaScript contains `.pick` (via `closest('.pick')`).
Measured after the fix — `.pick` appears **4 times in the document, 3 inside `<style>`**;
the JavaScript mention is now outside the corpus.

(b) The bad-value list spelled out `opacity:0;` and `opacity:0}` to dodge `opacity:.55`,
and so missed CSS-valid `opacity:.0`. The value is now **parsed and compared numerically**,
so no spelling is privileged.

⚠ **This is the third iteration of one lesson on this branch, and that is the finding.**
A page-wide substring assertion went vacuous and CI caught a survivor (r0). Its repair was
another substring assertion, and r2 caught that. That repair's corpus and value test were
both too loose, and r3 caught those. Each fix was correct and each was narrower than the
problem. The class is *"a text test is defined by what it looks at and how it compares"* —
corpus and comparison, and this branch got each wrong once.

**Controls, all RED via the case that names them, over a green 325/325:**

```
opacity:.0                      RED   <- r3 L1(b); the previous version MISSED this
visibility:hidden               RED
opacity:0                       RED
@media(...){...display:none}    RED
```

## ⚠ Stated limits, carried forward and still open

1. **`--mutate .` has never been completed by a reviewer.** r1 stopped at 160/632, r3 at
   240/633, both for time, both saying so. CI runs it in full — and has already caught one
   survivor on this branch that local reasoning missed. **CI is the instrument for
   attribution here, not any review round.**
2. **The wiring assertion is still text-shaped**, as r2 said. A behaviour-shaped test needs
   a browser; a browser is what found the High. Labelled weaker in place.
3. **"Opened as a file → Send copies instead"**, which the page's own mode chip asserts,
   remains unproven — r2 observed the clipboard write reject under headless Chromium.

## Verified on this tree

```
gen-dashboard   --self-test  325/325
check-plan-code --self-test  128/128
manifest 68 entries, EXPECTED_MUTATIONS 68, declared sum 633 — all agree
```

**CONVERGED on findings.** ⚠ The L1 repair above is itself unreviewed code, so the
branch's own gate will observe that the merging tree postdates round 3. Round 4 is
dispatched as a verification round; the decision to stop is the human's.

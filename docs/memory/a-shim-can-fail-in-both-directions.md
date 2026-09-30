---
name: a-shim-can-fail-in-both-directions
description: "FIRES-WHEN: adding a CSS var fallback or shim; fixing only the one name you noticed — MEASURED 2026-08-19 — `--rule: var(--rule, fallback)` is self-referential, so it yielded NO value whether or not the page defined it; the symptom was a missing border, which reads as a design choice"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-19T17:06:00.514Z
---

**A default that references itself has no direction in which it works** — and the symptom can be
invisible by construction.

`scripts/brief-compose.py` shimmed the lifted Ask tray's palette with:

    --rule: var(--rule, #d3d9e2);

Intent: *"keep the page's value if it set one, else use this default."* CSS makes a self-referential
custom property **invalid at computed-value time** — it does not fall back, it resolves to **nothing**.
So it failed if the page defined `--rule` AND if it did not. Both directions, silently.

**Why nothing caught it for months.** An unresolvable `var()` is not a CSS error — the declaration is
simply *dropped*. All four `border: 1px solid var(--rule)` rules in the tray vanished, so `#qbox` —
the box the reader types into — computed `border-style: none`. **A missing hairline reads as a design
choice.** No amount of re-reading finds this; it took measuring computed styles in a browser.

**Two things the fix had to get right, and one it nearly missed:**

1. **Ordering, not just syntax.** The shim splices AFTER the page's CSS, so a plain
   `:root { --rule: … }` would CLOBBER a page that legitimately defines it. Declaring on `html`
   (specificity 0,0,1) instead of `:root` (0,1,0) makes it a real default — the page wins regardless
   of source order.
2. **⭐ The instance vs the class.** Fixing `--rule` alone would have been the error this project
   keeps naming. Measuring found the tray also read `--structure`, `--structure-br`,
   `--structure-bg`, `--bg`, `--good`, `--defect` — **six** unresolved names, not one. `#tray`'s top
   border was dead for the same reason. `assert_shimmed()` now **refuses to compose** when the tray
   reads a property nothing defines, converting "someone might notice" into "it cannot ship".

Mutation-checked: restoring the self-reference fails 3 self-test cases, removing the guard and the
defaults fails 2 more. `--self-test` 14 → 22.

Related: [[a-test-that-cannot-fail]], [[a-convention-catches-what-you-read]],
[[test-harness-can-launder-failures]].

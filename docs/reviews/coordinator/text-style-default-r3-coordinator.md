# Round 3 — `text-style-default` — coordinator — ⟳ NOT CONVERGED (both halves); THRASHING → architecture review; SPLIT

```yaml
round: 3
fixes_nontrivial: true
subject: text-style-default
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: em-guard, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: em-guard, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: em-guard, disposition: deferred}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: em-guard, disposition: deferred}
  - {id: CF5, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: CF6, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Both on `201aa640`, each repro measured in headless Chromium in all six OS-scheme × pressed-theme states.
Duplicates: X1 = CF1 (a block-local `var()` alias overridden later — accepted, 1.00:1, INSIDE the format); X2 = CF4 (a
canonical block in a second `<style>` really follows the shim — rendered 7.53–16.15:1, refused at 2.01–3.75:1); X3 = CF2
(other spellings of the ground: `BODY{}`, `html body{}`, `.ex-body{}`); X4 = CF3 (bold recoloured outside `--em`: a
`.ex-body strong` rule, the role tokens, a `<link>` stylesheet). CF5: the refusal advises declaring `--em` in every
block, which cannot help a pressed state the shim wins. CF6: 26 fragments now, not 25.

**Held:** 193/193; 26/26 real fragments compose, 0 refused (the 10 that run the check render 7.45–8.45:1 wherever a
state is reachable); 15–17 cases red on `f88f10d0`; 49/49 mutations attributed; 2354 real.

**My error, stated:** clause (1) of the round-2 bet said *"no fragment the guard ACCEPTS renders bold below 4.5:1"* —
a rendered-readability promise the redesign itself had disclaimed. X4/CF3 refute a claim I should not have written.

**THRASHING — YES.** Round 2's X1–X3 were induced by round 1's scanner; round 3's X2/CF4 by round 2's per-state model
and X1/CF1 by the `var()` resolution round 2 kept — two consecutive rounds, one component. Convened:
[`architecture-review-2026-10-27-em-guard.md`](../architecture-review-2026-10-27-em-guard.md). Answer: the thrashing
component is the attempt to PREDICT the rendered page; remove it. **Route: SPLIT.** The stable half ships (switcher by
default; the measured omission trap with literal-hex `--bg`/`--em`; no per-state model, no rendered claim); X1 and X2
are dissolved by literal hex and by removing the per-state model; X3 and X4 are DEFERRED to the rendered-contrast
subject, backlog #387, which measures the browser's answer instead of re-deriving it.

# Round 1 — `stub-gaps-and-fg-cycle` — coordinator — ❌ NOT CONVERGED (2 Medium, 6 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: stub-gaps-and-fg-cycle
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: Medium, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: CL1, severity: Low, aim: records, fix_induced: false, component: records, disposition: fixed}
  - {id: F1, severity: Medium, aim: records, fix_induced: false, component: manifest, disposition: fixed}
  - {id: F2, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: F3, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: F4, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: fragments, disposition: fixed}
  - {id: F6, severity: Low, aim: records, fix_induced: false, component: records, disposition: fixed}
```

Both halves confirmed (B): in Chromium only OS-light-nothing-pressed changes colour, the literals match each block, and
`--fg`/`--fg2`/`--fg3` resolve in every state. Codex M: after a default press the options' class and `aria-pressed` were
unasserted (a mutant left plain marked, 233/233). Claude M: the closure said both r5 mutants were manifest entries; the
first was not. Lows: the default press could also delete the saved theme; a constant 40px bar let `Math.round(h)` pass; the
reserve was not re-read after a resize; the fragments' comment still recommended the alias shape that formed the cycle;
the dashboard understated the colour change and omitted the regenerated stamp.

Dispositions: all FIX. The stub's bar is fractional (43.109375px), the reserve is read on load AND after a resize, the
default press asserts the whole store and all three options; five verbatim mutants added (page_chrome 106 → 111, scoped
run 111/111 killed and attributed); the fragments carry a note above each literal line; records corrected. Round 2: Codex.

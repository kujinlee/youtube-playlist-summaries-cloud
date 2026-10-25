# Round 1 — `comprehensibility-chrome-cases` — coordinator — ❌ NOT CONVERGED (1 High, 3 Medium, 2 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: comprehensibility-chrome-cases
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: palette-detection, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: fixed}
```

Both halves independently refuted the branch's diagnosis of backlog #300's seven unpinned pages, in
Chromium: their toggles are NOT half-live. They declare light as the bare `:root` default and exclude it
from the OS-dark block with `:root:not([data-theme="light"])`; `missing_palettes` knew only a literal
`:root[data-theme="light"]` block, so the composer would have removed a working control (Claude High,
Codex Medium). The decision the branch was about to put to the owner rested on that misreading.
Codex Medium: `io.observe(bar)` survived every new case — the stub ignored the observed target.
Claude Medium: a throwing click handler, an inverted initial pressed state and a dead text-style click all
survived — the stub's `addEventListener` accepted anything, contradicting its own "STRICT" comment.
Claude Lows: both `ctls` layouts expected the same margin, so a hard-coded tail survived; a CANNOT RUN
report was sliced to `'C'` and `'AN'`.

Dispositions: all FIX, all in the deliverable. `_light_by_exclusion` (both halves required, top-level
default only; four cases); six pages recomposed and compared old-vs-new in Chromium (text identical,
control reachable, toggle works under OS-dark); the stub records target, listeners and resize target and
presses both controls; layouts expect 150/120; a CANNOT RUN report is returned whole. Every reviewer
survivor is now a manifest entry (+8); scoped run 101/101 killed and attributed. FOLD: coordinator
(`687b2f68`) — small, specified folds, written and measured here. Round 2: Codex.

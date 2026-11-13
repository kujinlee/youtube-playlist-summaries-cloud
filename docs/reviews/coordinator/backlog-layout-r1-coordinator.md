# Round 1 — `backlog-layout` — coordinator — NOT CONVERGED (both halves); every finding fixed by DOING LESS

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-layout
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: enum-run, disposition: fixed}
  - {id: CF1, severity: Medium, aim: deliverable, fix_induced: false, component: label-cut, disposition: fixed}
  - {id: CF2, severity: Medium, aim: deliverable, fix_induced: false, component: provenance, disposition: fixed}
  - {id: CF3, severity: Low, aim: deliverable, fix_induced: false, component: enum-run, disposition: fixed}
  - {id: CF4, severity: Low, aim: deliverable, fix_induced: false, component: same-words-check, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `07600a6c`. XM1 = CF3 (row 378 `WARN (1) or CANNOT RUN (2).`, row 444
`(a) or (b) is recorded`, row 252 `(2) and (3)`).

The owner's requirement is layout only, same words. The rule for the fold: **when a heuristic is unsure, leave one
block** — an un-split row is the old rendering, a wrong split is a new defect.

- **XM1/CF3** — `_enum_run_ok`: a marker run is a list only if every item has at least 3 words after its marker,
  none opens with `or`/`and`/`,`, and no marker directly follows `exit`/`code`/`case`/`item`/`row`/`step` (or
  their plurals). A refused run stays prose.
- **CF1** — the label cut's carry loop also carries a `(1)`/`(a)` marker, so the cut lands before the marker.
- **CF2** — `_prov_span` ends at the first `.`/`?`/`!` at depth 0 outside parentheses. It returns NO muted line
  when a `<strong>`, a ⭐/⛔/⚠ glyph or a sentence end inside an element comes first, or past 40 words. The brief
  said "stop at" bold/glyph; giving up is chosen instead because stopping there would cut mid-sentence.
- **CF4** — the self-test's same-words check now maps every inserted `div`/`ol`/`li` tag to a sentinel. Each
  boundary must sit next to whitespace the source already had.

Measured over all 422 real rows, before → after: rows with a list 72 → 64. Rows with a `— filed …` muted line
310 → 267. Muted lines over 40 words 11 → 0. Same words (strengthened check): 422/422. Rows 89, 189, 252, 378, 412,
418, 419 and 444 were rendered and read: 89 and 189 have no muted line now (their clause is body text); 252 has no
list; in 378 the `FALSIFIER:` sentence is prose and the two real `(1)/(2)` lists stay; in 412, 418 and 419 each
marker opens its own item; in 444 the `Then decide:` list stays and `(a) or (b) is recorded` is prose.

Tests: 221 → 233 self-test cases, all pass. Mutations: 45 → 58 (`EXPECTED_MUTATIONS` pinned). One old mutation was
re-bound: `provenance ends inside parentheses`, whose anchor line changed. The local `--only` sweep refused to run
(about 38 min estimated). So the 14 new and re-bound mutations were run by a scratch runner, each in its own copy of
the tree: 14 of 14 went red on the cases they name. The full sweep is CI's.

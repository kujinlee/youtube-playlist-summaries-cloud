# Round 2 — `comprehensibility-chrome-cases` — coordinator — ❌ NOT CONVERGED (1 High, 2 Medium)

```yaml
round: 2
fixes_nontrivial: true
subject: comprehensibility-chrome-cases
halves:
  codex: ran
  claude: "GAP: alternation (one-half-per-round reading; backlog #339, NEEDS-OWNER)"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: palette-detection, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: stub-page, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: palette-detection, disposition: fixed}
```

REVIEW GAP: claude — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

All three are r1's fold. Codex High, reproduced in Chromium through `brief-compose`: `_light_by_exclusion`
asked only that an exclusion EXIST, so a dark block holding a plain `:root` beside an unrelated
`:root:not([data-theme="light"])` was accepted and rendered dark with light pressed — the fail-silent the
module exists for. ⚠ So r1's record above ("both halves required") stated a sufficiency that was false.
Codex Medium: the brace counter misread valid CSS (`@layer base;`, a `{` in a quoted selector), turning a
working palette into `['light']`. Codex Medium: the stub recorded the resize callback and discarded it.

Dispositions: all FIX. ⛔ **Redesigned, not patched** — the heuristic is replaced by an exact condition
(EVERY token-declaring rule in an OS-dark block is exactly the exclusion selector; a top-level default)
over a small tokenizer, because a third patch to a presence test is the shape that thrashes. Seven
palette cases, all three r2 pages among them; the stub invokes the resize callback and asserts the
re-armed tail. +5 mutations, two re-bound; scoped run 106/106 killed and attributed. The six recomposed
pages re-derive byte-identical apart from their timestamp. FOLD: coordinator.

⚠ **Thrashing watch:** this round's findings are all fix-induced, in `palette-detection` and `stub-page`.
If round 3 carries fix-induced findings in either, that is two consecutive rounds and the architecture
review arms (`dev-process.md`, Phase 6). Round 3: a fresh Claude half.

# Round 1 — `goal-tree-superseded` (PR #480, backlog #484) — coordinator — NOT CONVERGED (both halves); all findings fixed, the fate read NARROWED to a marker

Codex half: `docs/reviews/codex/goal-tree-superseded-r1-codex.md`. Claude half: `docs/reviews/claude/goal-tree-superseded-r1-claude.md`. Both reviewed `02795757`.

```yaml
round: 1
fixes_nontrivial: true
subject: goal-tree-superseded
halves:
  codex: ran
  claude: ran
findings:
  - {id: C-H1, severity: High, aim: deliverable, fix_induced: false, component: fate-read, disposition: fixed}
  - {id: C-M1, severity: Medium, aim: deliverable, fix_induced: false, component: fate-read, disposition: fixed}
  - {id: C-M2, severity: Medium, aim: deliverable, fix_induced: false, component: multi-ref, disposition: fixed}
  - {id: C-M3, severity: Medium, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
  - {id: C-L1, severity: Low, aim: deliverable, fix_induced: false, component: fate-read, disposition: fixed}
  - {id: C-L2, severity: Low, aim: deliverable, fix_induced: false, component: missing-row, disposition: fixed}
  - {id: C-L3, severity: Low, aim: deliverable, fix_induced: false, component: fate-read, disposition: fixed}
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: fate-read, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: fate-read, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: missing-row, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: multi-ref, disposition: fixed}
```

**The two halves converge.** Reading SUPERSEDED / WITHDRAWN anywhere in the Status cell was unsound both ways:
row 484's own cell read as withdrawn (C-H1, X1), and the audit's dated `SUPERSEDED 2026-10-26 (audit)` rows 124,
125, 127, 189 and 213 were missed (C-M1, X2).

**C-H1, X1, C-M1, X2 — fixed by NARROWING the surface to a fate MARKER.** A marker is `**SUPERSEDED` or
`**WITHDRAWN`, bold and in capitals, after code spans are removed, in one of two positions:
- LEADING the Status cell, after an optional glyph and `(was X)`. Row 405 has this form.
- Led by a closing glyph, ✅ or ✖, anywhere in the cell, unless it comes after `Previously: `.

⚠ **The brief asked for the LEADING form only. That form alone was measured against the real backlog and fails the
brief's own required rows.** The audit APPENDED its marker: row 124's cell begins `pending — found 2026-09-15 …`
and row 189's begins `🟡 **OPEN — filed …**`. In both, `✅ **SUPERSEDED 2026-10-26 (audit)**` comes later in the
cell. A glyph-led marker is still a declaration rather than prose, so the surface stays narrow. The emphasis-led
clauses `⟳⛔ **SUPERSEDED BY EVENTS` (row 48) and `⛔⟳ **SUPERSEDED AS THE REMEDY` (row 213) are not markers.
**BOUND:** a row superseded by an appended marker and later REOPENED by an appended clause would still read as
superseded. The backlog's reopen convention moves the old state behind `Previously:`, and that case is handled.

**Row 327 is NOT marked.** Its `superseded by backlog #328/#329` is lowercase, unbolded and not glyph-led, so it is
prose under this grammar. The FAILS-IF in row 484 is narrowed to match: a row whose Status cell carries a fate marker.

**Classification of the real backlog at this fold** (every Items row whose Status contains the word in any case, 25 rows):

| Row | Fate | Why |
|---|---|---|
| 405 | superseded → backlog #481 | leading `✅ **SUPERSEDED by backlog #481` |
| 124, 125, 127, 189, 213 | superseded | appended `✅ **SUPERSEDED 2026-10-26 (audit)**`; no pointer in the bold span |
| 484 | live | leads `✅ **FIXED`; the words appear only in code spans |
| 48 | live | `⟳⛔ **SUPERSEDED BY EVENTS`, emphasis-led |
| 327 | live | lowercase prose |
| 1, 27, 100, 177, 184, 194, 206, 207, 208, 214, 252, 258, 259, 330, 337, 339 | live | the word in prose only (`superseded by dig-deeper`, `withdrawal rule`, `Supersedes the row`, …) |

**C-L3 — fixed.** A row prints only what it states: `superseded → backlog #M` when its marker's bold span says
`by backlog #M` (several print as `backlog #328, backlog #329`), otherwise a bare `superseded`. The "(method refuted,
goal moved)" phrase is gone.

**C-M2, X4 — fixed. Each ref contributes its own state.** The precedence is in a comment in `derive_thread`:
1. ⚠ CANNOT RUN: the backlog was not read, or a named row is missing.
2. ⏳ an open PR, ⏳ an in-flight entry, and ❓ a PR that gh did not list are all kept.
3. ✖ applies only when EVERY backlog ref is fated, and replaces only the merge ✅, or the ⬜ / ✖ closed of an all-fated leaf.
   A live row's own state stands: the no-PR merge and open-title search now reads only the unfated rows.

Every fate is still named in the detail.

**C-M3 — fixed.** The case for each of the four survivors and for Codex's `rows[:1]` is a multi-ref case with two
inputs. Each is registered as a mutation that names its killing case.

**X3, C-L2 — fixed.** `row_fates` now returns every Items row, with None for a live one. A `backlog #N` that is not
in it prints `CANNOT RUN — backlog #N is not a row of the Items table in docs/backlog.md`. All 55 threads in
`docs/goal-threads.md` were checked, and none names a missing row.

**C-L1 — fixed.** Fates are read from the `## Items` table only. The second table's same numbers are ignored.

Self-test: 176 → 192 cases. Mutations for `scripts/goal-tree.py`: 83 → 102. The six entries that anchored the old
regexes were replaced, and the in-flight entry was re-anchored.

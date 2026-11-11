# Round 1 — `backlog-multi-tag` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-multi-tag
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: parser, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: check-features, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: retag, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: check-features, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: retag, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: retag, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: parser, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `f8743a97`. **Both: every pre-existing cell keeps its tags (333 master rows, 334
pre-retag, 0 differ); both readers agree on every row; adversarial cells behave as documented; duplicate claims
caught; both pages render; all 57 mutations killed by their named case; 2266 is the real sum; the retag changes
exactly the 32 ledger rows and 0 closed rows.**

Duplicates: XM1 = Cm5 (a `\|` inside a tag yields a filter that matches nothing — `data-tags` is joined and split
on `|`). XM3 = Cm3 (#288, the explainer delivery procedure's enforcement, left out of the suite while #259 and
#123/#129/#130 were tagged).

- **XM2:** `check-features` reads the Bundle cell positionally (`cells[-3]`), so an extra `|` corrupts the table and
  passes the gate that the backlog page's own parser refuses (`ShapeError`). A second copy of the row-splitting rule —
  the class #381 exists to remove. Fix: read rows through the shared header-aware parser; ShapeError fails the gate.
- **CM1 — a GATE LOOSENING, not live:** the stale-area rule asks "does any in-use tag sit at or below the area"
  instead of "is the area the NEAREST claimant of some in-use tag"; with areas `(cloud)`, `(cloud/money)` and only
  `cloud / money` in use, master is red and this branch green. A mutation and a case pin the loosened form.
- **Cm2:** #300/#303/#304/#349/#352 are page_chrome/brief-compose rows that the status pages also render through;
  tagged explainers only, they left the status-pages band.
- **Cm4:** the #381 row and dashboard say 30/10/3; HEAD gives 29/9/2 (#381 is itself ✅).
- Also folded (the implementer's own flag): the real-backlog equality case needs > 300 single-group rows, 315 remain —
  make its floor relative to the row count, never a lower constant.

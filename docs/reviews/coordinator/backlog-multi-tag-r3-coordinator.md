# Round 3 — `backlog-multi-tag` — coordinator — ⟳ NOT CONVERGED (both halves, one shared finding); SPLIT

```yaml
round: 3
fixes_nontrivial: true
subject: backlog-multi-tag
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: check-features, disposition: fixed}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: check-features, disposition: fixed}
```

Both on `988a5dbf` (a pair: the merge gate reads Codex verdicts; alternation permits a pair). **X1 = C1**, found
independently: a row whose number cell is decorated or non-integer (`⭐999`, `#999`, `**999**`, `999a`, `abc`) fails
the item-row regex; `parse()` records it only when handed `unread=`; `check-features.backlog_areas` hands none, so the
row and its tags vanish from the gate — master exits 1 on the probe, HEAD 0, also inside the real `## Items` table.

**Held, both halves:** ~20 header/fence/alignment/pipe probes, HEAD never green where master is red (stricter in 9);
`TABLE_SCHEMAS` equals the real file's two headers; 61/61 mutations attributed; 2327 is the real sum; 30 distinct open
suite rows (status-pages 14, feature-map 2, explainer-pages 19) match #381, the dashboard and the PR body.

**Thrashing — NO, by the rule's letter, with the shared root stated.** X1/C1 came in with round 1's XM2 fold
(`133d08b1`, adopting the shared parser), not with round 2's schema fix — and the arming condition is *the previous
round's own fix*. Rounds 2 and 3 do share one ROOT, though: the page's parser is forgiving by design (report drift,
keep rendering) and the gate adopted it without adopting strictness. So the fold closes the CLASS: `check-features`
fails on every problem the parser reports, not on this one shape.

**Route: SPLIT** (accrete lost → redesign lost). Stable half ships here, including the class fix — a gate looser than
master's cannot ship. Split off: `gen-features-page.backlog_rows` also drops unread lines (pre-existing on master) →
backlog #383.

Nits (not findings): `988a5dbf`'s message credits the schema check for catching its 8-cell row — it was the width
check; the dashboard's "334 rows" is historical (HEAD parses 336).

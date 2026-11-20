# Round 1 — `decision-tags` — coordinator — NOT CONVERGED (both halves)

Codex (`docs/reviews/codex/decision-tags-r1-codex.md`) and Claude (`docs/reviews/claude/decision-tags-r1-claude.md`) reviewed
`28545f11`, the new §3a of `.agents/skills/shared/explainer-delivery.md`. There was no BLOCKER. Claude found 1 MAJOR and 4 MINOR; Codex found 3 MINOR, which overlap Claude's.
Every finding is a place where §3a described `scripts/brief-compose.py` inaccurately. The code is unchanged; every fold is to the doc text, and each refusal it lists was checked against `_DECISION_REFUSE_ON` and the `_Scan` parser.

```yaml
round: 1
fixes_nontrivial: false
subject: decision-tags
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: explainer-delivery-3a, disposition: fixed}
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: false, component: explainer-delivery-3a, disposition: fixed}
  - {id: Cm2, severity: Medium, aim: deliverable, fix_induced: false, component: explainer-delivery-3a, disposition: fixed}
  - {id: Cm3, severity: Medium, aim: deliverable, fix_induced: false, component: explainer-delivery-3a, disposition: fixed}
  - {id: Cm4, severity: Medium, aim: deliverable, fix_induced: false, component: explainer-delivery-3a, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| CM1 (+ Codex 3) | "a mark the reader could not see is CANNOT RUN" is false: a mark under `display:none` CSS or misnested hidden markup is counted | §3a now names exactly what is refused, and adds the bound: the scanner reads attributes, not CSS |
| Cm1 (+ Codex 1) | the tag was described as placed "after it"; it is the element's first child | corrected |
| Cm2 | "a collapsed `<details>`" was too narrow: an open `<details>` outside its summary, and a mark on `<details>` itself, are refused too | corrected |
| Cm3 | the list omitted the table, form, raw-text and void element refusals and the `ex-decision-n` id collision | listed; the element set is named by its symbol `_DECISION_REFUSE_ON` |
| Cm4 (+ Codex 2) | the counter text differs once everything is answered; a whitespace-only value counts as open | both stated |

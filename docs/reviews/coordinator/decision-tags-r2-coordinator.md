# Round 2 — `decision-tags` — coordinator — NOT CONVERGED (Codex half)

Codex (`docs/reviews/codex/decision-tags-r2-codex.md`) reviewed `650f9395`, the round 1 fold. There was no BLOCKER and there were 3 MINOR findings, all
caused by the fold itself. The round 1 fold had rewritten §3a's refusal sentence as a fuller ENUMERATION of `brief-compose.py`'s refusal rules. Codex found three
rules that the enumeration still omitted:
- `datalist` in `_DECISION_REFUSE_INSIDE`
- the first-`<summary>`-only exemption
- the `name` attribute in the id-collision check

The cause was the same in all three: a prose copy of a code list drifts. The fold therefore stops copying the list. §3a now names the scanner's symbols as the one place the rules live, and keeps only what no symbol holds: the bound that the scanner reads markup, not CSS.

REVIEW GAP: claude — alternation (round 2 is the Codex half's).

```yaml
round: 2
fixes_nontrivial: false
subject: decision-tags
halves:
  codex: ran
  claude: gap
findings:
  - {id: Xm1, severity: Medium, aim: deliverable, fix_induced: true, component: explainer-delivery-3a, disposition: fixed}
  - {id: Xm2, severity: Medium, aim: deliverable, fix_induced: true, component: explainer-delivery-3a, disposition: fixed}
  - {id: Xm3, severity: Medium, aim: deliverable, fix_induced: true, component: explainer-delivery-3a, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| Xm1 | `datalist` is refused as an ancestor; the list omitted it | the list is replaced by its symbols (`_DECISION_REFUSE_INSIDE`) |
| Xm2 | only the FIRST `<summary>` is exempt | named as "the `<details>`/`<summary>` rule" in the scanner |
| Xm3 | a `name` equal to a generated id is refused too | "an `id`/`name` already equal to a generated `ex-decision-n`" |

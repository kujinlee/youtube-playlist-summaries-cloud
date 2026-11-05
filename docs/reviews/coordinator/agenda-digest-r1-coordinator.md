# Round 1 — `agenda-digest` (owner 11-05 14:37) — coordinator — NOT CONVERGED, all four folded

REVIEW GAP: claude — weekly usage at 96%, at the day's stop of 98.2%. Codex half: `docs/reviews/codex/agenda-digest-r1-codex.md`, on `671753cc`.

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-digest
halves:
  codex: ran
  claude: gap
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-recap, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-digest, disposition: fixed}
  - {id: M3, severity: Medium, aim: test, fix_induced: false, component: agenda-html, disposition: fixed}
  - {id: L1, severity: Low, aim: test, fix_induced: false, component: agenda-recap, disposition: fixed}
```

- **M1** — the recap counted only steps naming a ref, so an open free step read as "no step left". Now `left` counts every
  step not merged or closed; "(k of N left)". Case + mutation.
- **M2** — work under no goal dropped its ledger `what`. Now kept, cut to one 140-character line (`_one_line`). Case + mutation.
- **M3** — no case failed if escaping was removed. One case interpolates `<b>&amp;</b>` through the chip, the purpose, the
  window and the change-if; four mutations, one per value.
- **L1** — a tie keeps the first goal in step order; a case + mutation (`(len, name)` key).

Codex also verified: 1,000 generated snapshots give `agenda_context` output identical to origin/master's.

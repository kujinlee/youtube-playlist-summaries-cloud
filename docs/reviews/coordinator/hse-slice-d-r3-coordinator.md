# Round 3 — `hse-slice-d` — coordinator — NOT CONVERGED (Codex half)

Codex (`docs/reviews/codex/hse-slice-d-r3-codex.md`) reviewed `53f2f20f`, the round 2 fold: 2 MAJOR, 2 MINOR, no BLOCKER. It
rebuilt every round 2 input on an outside copy and found each fold holds, the two NARROWED bounds true as stated, and no invalid or
duplicate `unread` location. Two MINORs are fix-induced, both in detector 4's colon-introduction rule (round 2's CM4 fold). Not
thrashing: round 2's fix-induced finding was in detector 2 (`./` targets), a different component, so no one component carries
fix-induced findings in two consecutive rounds.

REVIEW GAP: claude — alternation (round 3 is the Codex half's).

```yaml
round: 3
fixes_nontrivial: true
subject: hse-slice-d
halves:
  codex: ran
  claude: alternation
findings:
  - {id: XM1, severity: High, aim: deliverable, fix_induced: false, component: detector-6-config, disposition: fixed}
  - {id: XM2, severity: High, aim: deliverable, fix_induced: false, component: detector-4-prose, disposition: fixed}
  - {id: Xm1, severity: Medium, aim: deliverable, fix_induced: true, component: detector-4-prose, disposition: fixed}
  - {id: Xm2, severity: Medium, aim: deliverable, fix_induced: true, component: detector-4-prose, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| XM1 | `os.getenv("X") or (None or None)` counted as a working fallback | `_always_none`: `None`, or a boolean operation whose operands are each always None, is no fallback or default; case `r3: an or of operands …` |
| XM2 | blank lines between numbered items broke the list, so item 2 checked item 1 as its introduction | the walk back over a list skips blank lines whose preceding line is a list item; case `r3: blank lines …` |
| Xm1 | (fix-induced) a negated verb ("tools that we never use:") counted as an imperative | a `LEAD_VERBS` match preceded within 24 characters by `NEGATES` (never / not / no / n't) is no imperative; same case |
| Xm2 | (fix-induced) the introduction lookup walked back through an earlier list into its imperative | an earlier list item ends the introducing paragraph; same case |

Live tree, measured on the fold: 296 → 296, the same findings. Self-test 105/105; 4 mutations added and 3 rebound (158), each
killed by its named case.

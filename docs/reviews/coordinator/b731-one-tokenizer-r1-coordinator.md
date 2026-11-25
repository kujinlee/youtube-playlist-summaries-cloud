# Round 1 — `b731-one-tokenizer` — coordinator — both halves ran; 3 distinct findings: 2 fixed, 1 declined

Both halves reviewed head `11f02283`. Both raised finding P independently.

| Id | Raised by | Severity | Finding | Disposition |
|---|---|---|---|---|
| L | Codex 1 | Medium | ADR headers no longer feed `check-goal-status`'s misnamed-slug check. An ADR whose header names `nonexistent` gives exit 1 on master and exit 0 on the branch. `check-anchors` G1 still refuses it (the Claude half measured that over 1,500 random trees: all 41 master-refuses/branch-passes cases were ADRs, and all were refused by `check-anchors`). It is still a loosening of THIS gate, flagged as ids `c0a5723843c4` and `dd509572087b`. | fix: ADR claims feed the misnamed-slug check again |
| P | Codex 2, Claude F1 | Medium | "Enforce on ANY claim" counts a prose example. A spec whose real header names the exempt `dev-speed`, with `Example: **Anchor:** \`alpha\`` in its first 18 lines and no Status line, gives exit 1 on the branch and exit 0 on master. It can also arm a node that no header names. No live document is affected. | **declined**, the refusal pinned by a case: the reader before slice S2 (`68529dd9`, the property case's reference) also refused this input (rc 1, measured by the fold agent), so refusing it is long-standing behaviour, not a new refusal. Only `e96c4775` (PR #637) passed it. Requirements (a) and (b) cannot both hold against that reference. |
| S | Claude F2 | Low | The armed set is filtered with `current_slugs`, which includes proposed nodes, so a loose claim can arm a proposed node. Deleting the filter still leaves 45/45. | fix: filter with settled slugs; add a case that kills the deletion |

Also: the property case's copy of master's reader matches only the tokenizer's pattern and window. It uses `splitlines()` where the tokenizer uses `split("\n")` (Codex note). The fix should make them agree, or pin the difference in a case.

```yaml
round: 1
fixes_nontrivial: true
subject: b731-one-tokenizer
halves:
  codex: ran
  claude: ran
findings:
  - {id: L, severity: Medium, aim: deliverable, fix_induced: false, component: check-goal-status, disposition: fixed}
  - {id: P, severity: Medium, aim: deliverable, fix_induced: false, component: check-goal-status, disposition: declined}
  - {id: S, severity: Low, aim: deliverable, fix_induced: false, component: check-goal-status, disposition: fixed}
```

Reviews: `docs/reviews/codex/b731-one-tokenizer-r1-codex.md`, `docs/reviews/claude/b731-one-tokenizer-r1-claude.md`.

# Round 3 — `goal-node-tree-s2` — coordinator — Claude: 1 Medium, 2 Low; two fixed in `bdaeff75`, one decided by the spec

REVIEW GAP: codex — alternation (rounds 2+ run one half; round 2 was Codex).

Round 3 was bought by `check-merge-ready.py --pr 637`, which HELD for "loosens a gate" after the master merge of
PR #635 voided the earlier answers. The Claude half answered all 72 flagged ids on head `465de1ce`: 65 not a
loosening, 7 findings.

```yaml
round: 3
fixes_nontrivial: true
subject: goal-node-tree-s2
halves:
  codex: gap
  claude: ran
findings:
  - id: F1
    severity: Medium
    aim: deliverable
    fix_induced: true
    component: scripts/check-goal-status.py living_documents
    disposition: fixed
  - id: F2
    severity: Low
    aim: deliverable
    fix_induced: false
    component: scripts/check-anchors.py
    disposition: declined
  - id: F3
    severity: Low
    aim: deliverable
    fix_induced: false
    component: scripts/gen-backlog-page.py parent_errors
    disposition: fixed
```

| id | severity | finding | disposition |
|---|---|---|---|
| F1 | Medium | `living_documents` reads through the strict shared header reader (10 lines, full `— **ADR:**` tail); master armed any `**Anchor:**` in 18 lines. Reproduced: master rc 1, branch rc 0. Latent: all 207 documents agree | **fixed `bdaeff75`** — `parse_header(lenient=True)` applies master's rule only for arming; check-anchors stays strict; one reader. Closes backlog #728 |
| F2 | Low | R4 "every registered anchor is claimed by a document" dropped | **declined — decided in the approved spec**: slice S2's row says check-anchors "drops the claimed-by-a-document rule"; ADR-0016 *Consequences* records it |
| F3 | Low | `epic:` parent check used `current_slugs`, which includes `proposed:` nodes | **fixed `bdaeff75`** — `check-features.settled_slugs` feeds `kind_problems` and `gen-backlog-page.node_slugs` |

Fold evidence (from the fold agent, a fresh Opus): each new case red before and green after; each half of the F1 fix cut in turn
turns the F1 case red. Self-tests: check-anchors 23→24, check-goal-status 40→41, check-features 100→101,
gen-backlog-page 252→253, gen-goals-page 85. Scratch sweeps: check-anchors 13/13, check-goal-status 13/13,
check-features 60/60; gen-backlog-page's full sweep (85, ~37 min) is owed to CI, its three `node_slugs` entries
killed by hand. Anchor resolve 6781, 0 unbound.

Next: round 4, the Claude half again — only the half that answered an id as a finding can withdraw it — on the fold's tree,
with the fresh `--flagged-block`. Round 4 is the cap: its findings are filed unless Blocking.

Claude's review: `docs/reviews/claude/goal-node-tree-s2-r3-claude.md`.

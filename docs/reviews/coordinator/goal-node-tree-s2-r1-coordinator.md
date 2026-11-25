# Round 1 — `goal-node-tree-s2` (PR #637) — coordinator — fold

```yaml
round: 1
fixes_nontrivial: true
subject: goal-node-tree-s2
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: instrument, fix_induced: false, component: mutation-evidence, disposition: declined}
  - {id: C1, severity: Low, aim: instrument, fix_induced: false, component: goals-hook, disposition: filed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: check-goal-status, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: check-goal-status, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: check-goal-status, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
```

Reviewed head `1fdbd53c` (both halves). The halves are `docs/reviews/codex/goal-node-tree-s2-r1-codex.md` (NOT
CONVERGED, one MAJOR) and `docs/reviews/claude/goal-node-tree-s2-r1-claude.md` (CONVERGED, five MINOR). No
finding came from an earlier fold: this is round 1. `fixes_nontrivial` is true because C2 and C4 change what
`check-goal-status` reads and reports, and each adds a case.

| id | Half | Severity | Finding | Disposition |
|---|---|---|---|---|
| X1 | Codex MAJOR | High | The mutation evidence was incomplete: the gen-backlog-page sweep was refused locally, and the check-features and gen-features-page sweeps were still running when Codex reported. | **Declined, with no code change.** The Claude half completed both of the running sweeps: check-features 59/59 and gen-features-page 61/61, each kill attributed to its named case, 0 survivors. The gen-backlog-page sweep is refused locally by the harness's 10-minute budget and is owed to the PR's CI shards. It is still unmeasured; this fold does not claim it. |
| C1 | Claude MINOR-1 | Low | `regen-goals-page.sh` has no `docs/features.md` arm, and its header still describes the registry. | **Header fixed; the missing arm is filed** as another instance on backlog #710 (the hand-kept source lists). The goal-node-tree spec §5.1.1 adds no trigger, so none was added. The header now names the tree as a source, says it has no arm, and points at #710. |
| C2 | Claude MINOR-2 | Low | A mistyped `Anchor:` slug was armed, and check-goal-status asked the document for a Status instead of saying the name is wrong. | **Fixed.** New `misnamed_anchors`: for each slug `anchored_slugs` returns, it applies `check-anchors.name_problem` (the existing wording for "not a node", "a former name" and "a proposed name"). `main` fails with those lines before arming. New case `armed: a slug that is no node FAILS with the naming advice, not a status request`. With the check disabled, the case is red (39/40). New mutation. |
| C3 | Claude MINOR-3 | Low | `globals()["armed"]` worked around a parameter named `armed` that shadowed the function `armed`. | **Fixed.** The parameter is now `armed_override`, and `armed(anchored)` is called directly. Renamed in the five self-test call sites, the `check-fixture-variation` entry and the bound mutation's anchor. |
| C4 | Claude MINOR-4 | Low | `living_documents` kept its own `ANCHOR_LINE` reader: unanchored, over 18 lines. | **Fixed.** The plan's Task 9 does not forbid this. `ANCHOR_LINE` is deleted, and each document's anchor now comes from `check-anchors.parse_header`, the parser behind `anchored_slugs`. `HEAD_LINES = 18` still bounds the Status search. Four self-test fixtures gained the `— **ADR:** none` tail that the shared grammar requires. New case `living_documents reads the anchor with check-anchors' reader, so the two agree`. It covers a bare non-blockquote line and a line below the 10-line window, over two repos. Restoring the old reader turns it red (39/40). New mutation. The live run is byte-identical before and after: 65 of 206 documents, the same 13 armed. |
| C5 | Claude MINOR-5 | Low | The ADR index shows ADR-0010 as PROPOSED, and gen-goals-page comments still say "the registry". | **Fixed.** The `docs/adr/README.md` row now reads ACCEPTED 2026-11-24, partly superseded by ADR-0016. In gen-goals-page, the local `registry` is renamed `goal_rows`. Three comments are reworded: the `goal_nodes` docstring and the two "every write to … the registry" lines. Line 203 is left as written, because it records what the corpus was on 2026-08-30. ADR-0010's body and `inventory.json` are left as written, as the reviewer advised. |
| — | coordinator | — | ADR-0016's status cited "the slice S2 pull request". | Now cites PR #637. |

Mutation sweeps were run with `--only` in a scratch copy:
- check-goal-status: 12/12 killed and attributed (10 → 12, pinned in `expected_mutations.py`).
- gen-goals-page: 32/32.
- check-fixture-variation: **NOT RUN.** It was refused locally, with an estimate of 23.7 minutes against the 10-minute budget. The only change there is one exempt-list string. It is owed to CI.
- gen-backlog-page: **NOT RUN** locally. Only a row note changed in `docs/backlog.md`. `gen-backlog-page.py --self-test` passed, 252/252.

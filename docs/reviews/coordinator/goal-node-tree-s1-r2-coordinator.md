# Round 2 — `goal-node-tree-s1` (PR #631) — coordinator — fold: 2 fixed, 0 rejected, 0 ESCALATE

```yaml
round: 2
fixes_nontrivial: true
subject: goal-node-tree-s1
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: tree-grouping, disposition: fixed}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: true, component: node-rules, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 is the Codex half; the Claude half reviews round 3)

Half: `docs/reviews/codex/goal-node-tree-s1-r2-codex.md` (verdict NOT CONVERGED,
`docs/reviews/verdicts/goal-node-tree-s1-r2-codex.verdict.json`; reviewed head `5a9725b0`). Both findings were
reproduced against `5a9725b0` before acting. Each fix was made test-first: the case was written, seen red against
the unfixed code, and then made green. Each case carries a control that a too-broad fix would also turn red.

`fixes_nontrivial: true`. XM1 replaces `group_tree`'s grouping key. XL1 merges two refusals into one rule. Neither
is a one-token change.

## Findings

**XM1 (Codex Medium) — slugless trunks are grouped by heading text, which breaks file order. FIXED, file order
kept.**

- *Reproduced.* For `## T / ### a / ## U / ### b / ## T / ### c`, `group_tree` returned `[("T", [a, c]), ("U",
  [b])]` and the index rendered a, c, b. The output is the same when `## U` carries `slug: u`.
- *Fix-induced?* **No.** The same input gives the same `[("T", [a, c]), ("U", [b])]` at `2f8c8d9d`, before the r1
  fold. That was measured by loading that commit's `scripts/` into a scratch directory. The r1 fold (XH1 = CF1)
  re-keyed SLUGGED trunks and kept this half "as before".
- *Decision, from spec §2.2* (`docs/superpowers/specs/2026-11-23-goal-node-tree-design.md`). The spec says:
  - The parent row: "heading depth `##` to `######`; **a trunk is a node with a slug**".
  - The slug row: "unique across the WHOLE tree".
  - The ordering rule: "a node with threads but no request is numbered after every requested node, **in tree
    order**".

  A slugless trunk is therefore not a node. It has no identity, so two `## T` sections share nothing except
  display text. Nothing in the spec says such a pair must be refused, and refusing it would add a rule the spec
  does not make. The spec does assume the tree has an order. So the rule is **keep file order** and refuse
  nothing. The live tree has three distinct trunk headings (`PRODUCT`, `PLATFORM`, `DEV INFRASTRUCTURE`), so
  either choice changes nothing that exists today.
- *Fix.* The `slugless` dict is removed (`scripts/gen-features-page.py`, `group_tree`). A parentless node joins
  the group just before it only when that group is the same slugless section still running. Otherwise it opens a
  new group. One bound is stated in the docstring: two ADJACENT slugless `## T` sections stay one group. Nothing
  marks the boundary between them, and merging adjacent groups moves no node.
- *Case.* `slugless trunks keep file order` was red before the fix (`got … ['a', 'c', 'b']`) and is green after.
  It has four inputs:
  - slugless/slugless/slugless;
  - slugless/slugged/slugless;
  - slugged `## T` then slugless `## T` — the later node must not join the slugged trunk's children;
  - CONTROL: one slugless trunk with two nodes stays ONE group.

  Each input asserts both the groups and the order of the index links.
- *Mutations.* Four, gen-features-page 54 → 58:
  - merge by heading text again;
  - drop the slugged-trunk clause;
  - drop the trunk-text clause;
  - CONTROL: a group per parentless node.

  The existing orphan entry was REBOUND onto the rewritten `here = trunks[-1][2]` line, and now sends only a parentless node deeper than `###` (the orphan) to a dead list. A plain `continue` there would drop every `###` node of a slugless trunk, and seven other cases would kill it first. It is not counted in the +4.

**XL1 (Codex Low) — an empty `expected-because:` passes the stateless refusal. FIXED, refused on presence.**

- *Reproduced.* `### x / for: X. / expected-because:` parses to `expected_because == ""`, and `check_nodes`
  returned `[]`. The `built` refusal has the same hole: a `built` node with `areas:` and a bare
  `expected-because:` also returned `[]`. That is the same class at a second site, so both are fixed.
- *Fix-induced?* **Yes.** The r1 fold (CF3) wrote the stateless refusal. At `2f8c8d9d` a stateless node carrying
  even a non-empty `expected-because: e.` returned `[]`. The `built` arm predates r1 (`2f8c8d9d`
  `scripts/check-features.py:219`).
- *Fix.* The two per-state refusals were copies of one rule, and each was written as a truthiness test. They are
  MERGED into one rule over presence (`scripts/check-features.py`, `check_nodes`):
  `if n.expected_because is not None and n.state != "absent"`. The message names the state (`is \`built\`` or `has
  no \`state:\``), so both earlier cases still match. The `absent` arm's `if not n.expected_because` is kept on
  purpose: an empty reason on an `absent` node SHOULD be refused, and it already is.
- *Case.* `rules: an EMPTY expected-because is still the field` was red before the fix (`got [False, False, False,
  False] want [True, True, False, False]`) and is green after. Its inputs are a stateless node and a built node,
  each with a bare field. The CONTROLS are the same two nodes without the line, which must pass. A fix that
  refused every stateless or built node would turn them red.
- *Mutations.* One added, check-features 57 → 58: the merged rule back to truthiness. The r1 `built` and stateless
  entries were REBOUND onto the merged line, and each now exempts only its own state. They are not counted in the
  +1.

## Was either finding fix-induced, and is this thrashing?

- XL1 is fix-induced by r1 (component `node-rules`).
- XM1 is not fix-induced (component `tree-grouping`, present before r1).
- Round 1 had no fix-induced finding, because it was the first round. So this is not two consecutive fix-induced
  rounds, and Phase 6 does not arm.

The decision log (`docs/reviews/decision-scheme/decision-log.jsonl`) now carries both units:
- Each unit's r1 `accrete` is recorded retroactively as LOST.
- Each unit's r2 `redesign` is a prospective bet written before r3.

The ladder never retries a route on one unit. Without these rows, `check-decision-scheme.py` failed trigger 1
(NOT FED) for this subject.

## Loosening answers (Codex)

The fold changes none of the 14 answers. The three that Codex marked as findings (`9a6218192351`, `c5f9105b20f3`,
`1772e62bc392`: stateless nodes, ADR-only built nodes, absent nodes with anchors) are the plan sentences that round
1's coordinator already answered (`goal-node-tree-s1-r1-coordinator.md`, *Loosening answers*). Round 2 raised no
new argument against them.

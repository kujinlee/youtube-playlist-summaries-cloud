# Round 3 — `goal-node-tree-s1` (PR #631) — coordinator — fold: 3 fixed, 0 rejected, 0 ESCALATE

```yaml
round: 3
fixes_nontrivial: false
subject: goal-node-tree-s1
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: instrument, fix_induced: true, component: tree-grouping, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: node-rules, disposition: fixed}
  - {id: F3, severity: Low, aim: docs, fix_induced: true, component: tree-grouping, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 3 is the Claude half; the Codex half reviewed round 2)

Half: `docs/reviews/claude/goal-node-tree-s1-r3-claude.md` (verdict NOT CONVERGED; reviewed head `0e8247e0`). Each
finding was reproduced in a scratch copy of the tree before it was acted on. Each fix that carries a case was made
test-first: the case was seen red against the unfixed code, then green.

`fixes_nontrivial: false`. F2 is one token (`if n.state` → `if n.state is not None`) in a message string; the
refusal itself is unchanged. F3 is a docstring. F1 changes no product code: it swaps the reader one self-test case
uses for the index order (`str.index` → `index_shape`, the reader the other index cases already use), and the
restored mutation below is the mechanical witness that the swap does what it claims. No rendering, grouping or
refusal logic changed in this fold.

## Findings

**F1 (Medium) — the file-order case crashed the suite on a missing node instead of failing. FIXED; the stronger
orphan mutation is restored.**

- *Reproduced, and the reviewer's claim holds.* In a scratch copy, with the pre-r2 orphan mutant applied
  (`here = trunks[-1][2]` → `continue` in `group_tree`) and the OLD reader, `--self-test` printed 7 `[FAIL]`
  lines and then `ValueError: substring not found`; `index: an orphan level is kept` never ran. With the NEW
  reader and the same mutant, the suite runs to the end: 26/51 pass, and `[FAIL] index: an orphan level is kept:
  got ([], 0, True, True) want ([(1, 'f-orphan'), (1, 'f-after')], 1, True, True)` is among the red cases.
- *Fix-induced?* **Yes** — the case was written by the r2 fold (XM1).
- *Fix.* `slugless trunks keep file order` (`scripts/gen-features-page.py`, `_self_test_body`) reads the order as
  `[_deep[f] for _, f in index_shape(_oix) if f in _deep]`. A dropped node is now a short list, a `[FAIL]`, not an
  exception.
- *Class search.* The same raise-instead-of-fail shape sat in the gap-count case: three
  `rendered_gap_counts(...)["f-job-queue"]["rows"]` subscripts raise `KeyError` on a dropped card. They now read
  through `.get(…, {}).get(…)`, so a dropped card yields `None` and the case fails. Under the `continue` mutant that
  case prints `[FAIL] every card's heading and index line count exactly the open rows … got ([], [], [], None, …`,
  so the `.get` path is exercised.
- *The r2 reasoning, corrected.* The r2 coordinator wrote that a plain `continue` "would drop every `###` node of a
  slugless trunk, and seven other cases would kill it first". **That reason was wrong.** The harness does not
  attribute by "first": it needs the named case among the red cases. The real obstacle was the crash above, which
  stopped the orphan case from running at all. With the reader fixed, the plain `continue` mutant is attributed to
  `index: an orphan level is kept`, so it is **restored** as its own manifest entry
  (`scripts/mutations/gen-features-page.json`, "S1 r3: every parentless node is dropped …"). The narrow r2 entry
  (only a parentless node deeper than `###` goes to a dead list) is kept beside it: the two mutants are different
  and each is killed. gen-features-page 58 → 59.

**F2 (Low) — the merged rule's message tested `state` by truthiness, so a bare `state:` read as "has no `state:`".
FIXED.**

- *Reproduced.* `### x / state: / for: X. / expected-because: e.` drew `has state ''; expected …` and then
  `has no \`state:\` but carries an \`expected-because:\``.
- *Fix-induced?* **Yes** — the message was written by the r2 fold (XL1).
- *Fix.* `scripts/check-features.py`, `check_nodes`: `if n.state is not None`.
- *Case.* `rules: a BARE state: is not reported as a missing state:` asserts, for the bare-`state:` node, ZERO
  messages saying "has no `state:`" and exactly ONE about `expected-because`, and, as a CONTROL, exactly one "has
  no `state:`" for a node that truly has no `state:` line (so a fix that dropped that wording entirely is also
  red). Red before the fix: `got (1, 1, 1) want (0, 1, 1)`; green after.
- *Mutation.* One added, check-features 58 → 59: the message back to `if n.state`.

**F3 (Low) — the `group_tree` docstring said only ADJACENT slugless sections merge. FIXED.**

- *Fix-induced?* **Yes** — the bound was written by the r2 fold (XM1).
- *Fix.* The docstring now says two slugless `## T` sections with no NODE-BEARING trunk between them stay one group,
  that an empty `## U` in between opens no group, and that the merge moves no node (neither heading carries an
  id). Prose only; no case, no mutation.

## Was any finding fix-induced, and is this thrashing?

All three are fix-induced by the r2 fold: F1 and F3 in `tree-grouping`, F2 in `node-rules`.

**`node-rules`: fix-induced in r2 (XL1) and r3 (F2), two consecutive rounds. Answer: PROSE FLOOR, not thrashing.**
Per-finding evidence:

- *XL1 (r2)* was a LOGIC defect: an empty `expected-because:` PASSED the refusal. The fix merged two per-state
  copies into one rule over presence.
- *F2 (r3)* is not a logic defect. The reviewer probed the merged rule with empty, space-only and tab values, on
  stateless, `built`, `absent` and slugged-trunk nodes, with a duplicate key and an invalid state, and every
  refusal was correct (r3 Claude doc, *Claims I tried to refute and could not*). F2 is the wording of a message on
  an input that is already refused. The fix is one token, and the r2 redesign's bet ("no node state or field value
  for which an `expected-because:` sits on a non-absent node and passes") held.
- Thrashing means each fix creates the next defect of the same kind. Here the defect kind changed from "the rule
  admits a bad input" to "the rule's message misnames a refused input", and the severity fell from a pass-through
  to text. A redesign would not remove a message string.

**`tree-grouping`**: fix-induced for the first time this round (F1, F3). One round is not two consecutive rounds, and
neither finding is in the grouping logic: F1 is a self-test reader, F3 is a docstring. The reviewer ran seven
crafted inputs against `group_tree` and `render_index` and found file order kept in all of them.

So Phase 6 does not arm. This is the last round before the cap: from r4, findings are FILED unless a BLOCKER.

The decision log (`docs/reviews/decision-scheme/decision-log.jsonl`) settles both r2 redesign bets as WON
(`outcome: stopped`, `rounds_at_termination: 3`): neither unit's prediction was refuted in r3.

## Gates

See the commit's CHECK/RESULT table; the sweeps ran in a scratch copy of the tree, never in the worktree.

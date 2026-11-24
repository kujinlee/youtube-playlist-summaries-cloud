Reviewed head: 0e8247e0509c7689e8040565880cb22d49e0bf7c

# Goal node tree S1 — round 3, Claude half (adversarial)

Subject: `git diff 5a9725b0 0e8247e0` in worktree `node-tree-s1` (PR #631), the round-2 fold described in
`docs/reviews/coordinator/goal-node-tree-s1-r2-coordinator.md`. Spec: `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md`
§2.2. The Codex half is skipped this round by alternation.

## Gates run (stdin closed, at 0e8247e0)

| Check | Result |
|---|---|
| `check-features.py --self-test` | 95/95, rc 0 |
| `gen-features-page.py --self-test` | 51/51, rc 0 |
| `check-features.py` (real tree) | rc 0. 35 nodes: 31 built, 4 absent, 0 stateless |
| `check-review-rounds.py` | rc 0. 1159 parsed, 0 silent gaps |
| `check-plan-code.py --mutate . --only scripts/gen-features-page.py` | 58 mutations, 58 killed, 58 attributed |
| `check-plan-code.py --mutate . --only scripts/check-features.py` | 58 mutations, 58 killed, 58 attributed |
| Real `docs/features.md`, old vs new | `group_tree` shape and `render_index` HTML are byte-identical between `5a9725b0` and `0e8247e0`. I loaded both commits' `gen-features-page.py` on the same file. The full-page diff showed only the git-readability notice and the Recent-changes bands, because the old copy ran outside a repository. |

## Claims I tried to refute and could not

- **File order (XM1).** I ran seven crafted inputs through `group_tree` and `render_index`. All keep file order:
  - interleaved slugless and slugged trunks;
  - a slugless `## T` before and after a slugged `## T`;
  - `####` and `#####` nesting under a regrouped trunk (`T a/a1 · U b · T c/c1/c2`, giving index `a a1 b c c1 c2`);
  - an orphan `####` opening the second `## T` section.
- **Adjacent same-heading slugless trunks.** `## T / ### a / ## T / ### b` gives one group `[a, b]`. The two trunk
  headings have no id (`<h2 class="tname">` and `<span class="iname">` carry none), so a merge changes no anchor and
  moves no node. I agree with the fold that this is harmless. F3 is about how the docstring words the bound.
- **The `expected-because:` rule (XL1).** Every probe behaves as the spec requires:
  - An empty value, a run of spaces, or a tab on a stateless node: refused.
  - Empty or whitespace-only on an `absent` node: refused ("has no `expected-because:` line").
  - `absent` with an empty reason is **not** wrongly accepted. The `absent` arm's `if not n.expected_because` still
    fires, and `value.strip()` collapses whitespace to `""`.
  - A duplicate key is refused at parse time and the first value stands. So `absent` + `a.` + an empty duplicate
    still fails overall, on the parse problem.
  - On a slugged trunk node, an invalid `state: planned`, or `expected-because :` with a space, the field is refused.
    The spaced form is refused by the grammar.
- **The rebound check-features mutations are not weakened.** Each one now exempts exactly one state from the merged
  rule: `not in ("absent","built")`, and `state is not None and …`. That is the precise mutant for each case's
  name, and both are killed and attributed.

## Findings

### F1 — Medium — the new file-order case crashes the suite when a node is missing, instead of failing (fold-induced)

`scripts/gen-features-page.py:1056-1057`. The case `slugless trunks keep file order` sorts the slugs with
`key=lambda s: _oix.index(f'href="#{frag_id(s)}"')`. `str.index` raises `ValueError` when a node is absent from the
index. Dropping a node is exactly the failure this page exists to catch, so on that input the case aborts the whole
`--self-test` instead of printing a `[FAIL]` line. No later case runs, including `index: an orphan level is kept`.

**Repro.** Copy the tree to a scratch directory. Apply the pre-fold orphan mutant (`here = trunks[-1][2]` →
`continue`) and run `--self-test`. You get 7 `[FAIL]` lines and then `ValueError: substring not found` at line 1057.
The orphan case never runs. Next, replace the `sorted(…)` with `[sl for _, sl in index_shape(_oix)]`, the reader the
other index cases use. With that change, the same mutant reports `[FAIL] index: an orphan level is kept` and the file-order case
fails cleanly too.

This matters for the coordinator's account of the orphan mutation's retarget. It says a plain `continue` "would drop
every `###` node … and seven other cases would kill it first". The harness does not attribute by "first". It needs
the named case to be among the red cases (`scripts/check-plan-code.py`, the `unnamed` filter on `w == f` over
`fails`). The real obstacle was this crash. The retargeted mutant is narrower, so it is not weaker evidence for the
orphan case. Even so, the stated reason is wrong, and any future mutant that drops a slugless-trunk node will crash
the suite rather than be attributed.

**Fix.** Read the order with `index_shape(_oix)`, which also asserts that a missing node is missing. Then correct the
coordinator sentence.

### F2 — Low — the merged rule's message tests `state` by truthiness, so `state:` with no value is reported as "has no `state:`" (fold-induced)

`scripts/check-features.py:233`: `held = f"is \`{n.state}\`" if n.state else "has no \`state:\`"`. With
`### x / state: / for: X. / expected-because: e.`, `check_nodes` returns two messages: `has state ''; expected …`, then
`has no \`state:\` but carries an \`expected-because:\``. The second message contradicts the first, and the line is
right there in the file.

The refusal itself is correct. This is the same truthiness-for-presence pattern the fold removed one line below.
**Fix:** use `if n.state is not None`.

### F3 — Low — the `group_tree` docstring says only ADJACENT slugless sections merge; a nodeless trunk in between merges them too

`scripts/gen-features-page.py:203-205`. Take `## T / ### a / ## U / ## T / ### b`, where `## U` has no nodes. It gives
`[("T", None, [a, b])]`, because an empty trunk opens no group and `trunks[-1]` is still `T`. The order stays
`a, b`, and `## U` rendered nothing before the fold either, so the behaviour is harmless. But the bound as written
("Two ADJACENT … sections") is narrower than what the code does.

**Fix:** "…sections with no node-bearing trunk between them stay one group".

## Fix-induced and thrashing

- F1 is caused by XM1's case (component `tree-grouping`).
- F2 is caused by XL1's merged rule (component `node-rules`).
- Round 2's fix-induced finding (XL1) was in `node-rules`. F2 makes that component fix-induced for the second
  consecutive round, but at Low: it is a message string, and the rule is correct.
- `tree-grouping` has its first fix-induced finding this round.

The coordinator should answer the thrashing question for `node-rules`. My read is prose floor, not thrashing: the
refusal logic has held since the merge and F2 touches only the wording.

VERDICT: NOT CONVERGED

<!-- codex-review: model=gpt-6.1-terra -->

**MINOR — A historical document can lose status enforcement when its header no longer matches the shared grammar.** [check-goal-status.py:224](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/node-tree-s2/scripts/check-goal-status.py:224) now treats an `Anchor:` line without the `— **ADR:** …` tail as unanchored. Master’s reader recognized that line and required a status if the slug was armed. For a pre-cutoff document, `check-anchors` does not require a header, so it can also accept the malformed line as absent. The four fixture edits expose this real difference, although the live comparison found no affected spec or plan. Preserve enforcement by detecting and rejecting malformed anchor-like headers, including in pre-cutoff documents.

The constructed unknown slug is rejected with “is not a node” before arming. The `armed_override` callers, fixture-variation entry and mutation anchor agree. Comparing the readers across 3,603 Markdown files found 11 differences outside the 206 living specs and plans, and none within them. The documentation changes reviewed were accurate. Both new cases failed when their respective fixes were disabled in a scratch copy.

Validation passed: check-goal-status self-test 40/40, gen-goals-page self-test 85/85, and the requested live status, anchors and fixture-variation checks.

## Loosening answers
LOOSENING-CHECK ae760b4ab0f9: finding: a current node slug outside the former registry is accepted as an anchor
LOOSENING-CHECK bb1a8c666480: finding: a current node slug outside the former registry is accepted as an anchor
LOOSENING-CHECK f1c9aace0e5c: finding: a current node slug outside the former registry is accepted as an anchor
LOOSENING-CHECK 638463189ba3: not a loosening
LOOSENING-CHECK 3a3a2417a186: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK 2f93ab5c0a6a: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK ae0653c750c9: finding: ROOTS may name a current node outside the former registry
LOOSENING-CHECK aa56b36981a5: finding: ROOTS may name a current node outside the former registry
LOOSENING-CHECK 45c717f44d4b: finding: ROOTS may name a current node outside the former registry
LOOSENING-CHECK 6f62d37ef77e: finding: an unclaimed former registry anchor is accepted as a node
LOOSENING-CHECK b7e6b4a76ac8: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 4daa86e4400b: not a loosening
LOOSENING-CHECK 98804b00886a: not a loosening
LOOSENING-CHECK 4a5b8647cab6: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 61e8188ea1e9: finding: an empty former registry is irrelevant when the node tree is readable
LOOSENING-CHECK f3799c3062d6: finding: an empty former registry is irrelevant when the node tree is readable
LOOSENING-CHECK 084926e46434: not a loosening
LOOSENING-CHECK 1938e73467f3: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK 4622be3b40b8: not a loosening
LOOSENING-CHECK 023b3d0e2c82: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 68b10485a2de: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK 9f3ae631661f: not a loosening
LOOSENING-CHECK 08f9434c73c6: not a loosening
LOOSENING-CHECK bd78b9dd33e3: finding: an epic may name a current node outside the former registry
LOOSENING-CHECK 8d2660d651d0: finding: an epic may name a current node outside the former registry
LOOSENING-CHECK 6d3627dc24c3: finding: an anchor formerly claimed by two nodes is accepted after the separate claims are removed
LOOSENING-CHECK 11fcbf1fb18e: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 1f1bff3ecb85: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK eef5137742b8: finding: an empty former registry is irrelevant when the node tree is readable
LOOSENING-CHECK ff6143ac0ea6: finding: an empty former registry is irrelevant when the node tree is readable
LOOSENING-CHECK 2ec67e35ad65: finding: an epic may name a current node outside the former registry
LOOSENING-CHECK 4b3aefc7bdd5: not a loosening
LOOSENING-CHECK 924ecb78d7df: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK 2125da821a62: not a loosening
LOOSENING-CHECK a4ed6ea66535: not a loosening
LOOSENING-CHECK e7667529e10b: finding: a current node slug outside the former registry is accepted
LOOSENING-CHECK 3f19ab284962: not a loosening
LOOSENING-CHECK 30ac42cf829d: finding: a current node slug outside the former registry is accepted
LOOSENING-CHECK 199affb5f476: finding: a current node slug outside the former registry is accepted
LOOSENING-CHECK 53b9c46b58fe: finding: a current node slug outside the former registry is accepted
LOOSENING-CHECK 1a7f6d5d9263: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK f33bb38157cf: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK 23a3ffcd765a: finding: a node formerly represented by an unclaimed registry anchor is accepted
LOOSENING-CHECK e70f6b50debf: finding: separate duplicate anchor claims no longer exist in the node format
LOOSENING-CHECK 3d6c9265eb4a: finding: separate duplicate anchor claims no longer exist in the node format
LOOSENING-CHECK 8cb847cd39b8: finding: separate duplicate anchor claims no longer exist in the node format
LOOSENING-CHECK bf3e4c151c11: finding: separate duplicate anchor claims no longer exist in the node format
LOOSENING-CHECK 8868390a9f12: not a loosening
LOOSENING-CHECK 81b38ad60d84: not a loosening
LOOSENING-CHECK 02f32358cc56: not a loosening
LOOSENING-CHECK 64b7ae045d6c: not a loosening
LOOSENING-CHECK d73e7d733a1f: not a loosening
LOOSENING-CHECK 4230a5071232: finding: an epic may name a current node outside the former registry
LOOSENING-CHECK cb8bb9964f53: finding: a pre-cutoff document with an armed anchor missing its ADR tail can omit status
LOOSENING-CHECK 41db02b70dc0: finding: a pre-cutoff document with an armed anchor missing its ADR tail can omit status
LOOSENING-CHECK 281fa3f23926: finding: a pre-cutoff document with an armed anchor missing its ADR tail can omit status
LOOSENING-CHECK 004aa7155968: not a loosening
LOOSENING-CHECK 09f7e8cfc7c9: not a loosening
LOOSENING-CHECK 8e23f719a350: finding: an epic may name a current node outside the former registry
LOOSENING-CHECK 99f12f04ec8d: finding: an epic may name a current node outside the former registry
LOOSENING-CHECK af75797e1e03: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 0ec9b46ed751: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 712b76fa3b13: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 8d3677e94d34: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 8d9e61b7a135: finding: an empty former registry is irrelevant when the node tree supplies goal nodes
LOOSENING-CHECK ab380ecc2f26: finding: an empty former registry is irrelevant when the node tree supplies goal nodes
LOOSENING-CHECK dcdf23f85c2d: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK e9fea33a93fe: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 4c6d1d19b1c7: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 025445bdbfb0: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 58818912fab8: finding: the deleted registry may be absent when the node tree is readable
LOOSENING-CHECK 4bc58dfb4b7b: finding: the deleted registry may be absent when the node tree is readable
VERDICT: NOT CONVERGED

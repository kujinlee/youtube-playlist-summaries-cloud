# Round 2 — `backlog-layout` — coordinator — NOT CONVERGED (Codex only); 1 fixed, 2 accepted as a stated bound

```yaml
round: 2
fixes_nontrivial: true
subject: backlog-layout
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: Low, aim: deliverable, fix_induced: true, component: enum-run, disposition: accepted}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: true, component: enum-run, disposition: accepted}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: true, component: same-words-check, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 runs one half; Claude ran in round 1 and is next in round 3).

Codex reviewed `ce241150` (`docs/reviews/codex/backlog-layout-r2-codex.md`). All three findings were caused by the
round-1 fold.

- **X1, X2: accepted, not fixed.** The tightened list rule now refuses some genuine lists. In rows 153, 311 and 423 an
  item ends in `case;` or `step;`, which reads as a reference word. In rows 222, 224 and 340 the items are `(b) or …`
  alternatives. These rows now render unsplit. That fails toward less layout, which is the design's stated bias
  ("when a rule is unsure, leave one block"). An unsplit row looks the same as today's page, and no words change.
  The bound is now stated in one sentence in `layout_body`'s docstring, with the six row numbers. The list
  heuristics are unchanged.
- **X3: fixed.** `_same_words_html` compared tag-stripped text. So `alpha<br>beta` → `<div class="seg">alphabeta</div>`
  passed: two words that `<br>` had kept apart were joined. The new check walks the new HTML with a stack. It strips
  exactly the wrappers `layout_body` adds: `<div class="seg|prov">`, `<ol class="enum">`, the `<li>` directly
  inside that `<ol>`, and their closers. What remains must equal the original HTML byte for byte. The
  boundary-next-to-whitespace check is kept, and now counts an original `<br>` as whitespace.

New self-test case: `layout: the same-words check refuses two words joined across an original <br> (r2 Codex 3)`.
It refuses the reproducer, a bare join with no wrapper (`alpha<br>beta` → `alphabeta`) and a dropped inline tag. It
accepts a cut at the `<br>`. The bare-join and dropped-tag inputs are there because the adjacency check alone also
refuses the reproducer. With only the reproducer, the byte-comparison mutation survived (measured).

Over every real row, same words: 422 of 422. Self-test: 233 → 234 cases, all pass. Mutations: 58 → 61
(`EXPECTED_MUTATIONS` pinned). Four mutations were run by a scratch runner, each in its own copy of the tree: the 3
new ones (byte comparison removed, `<li>` not stripped, `<br>` not counted as a break) and the r1 zero-width
mutation, whose code was rewritten around its unchanged anchor line. 4 of 4 went red on the cases they name. The
full sweep is CI's.

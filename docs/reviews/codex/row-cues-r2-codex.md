<!-- codex-review: model=gpt-6.1-sol -->

Found one issue:

**Medium — any enum list exempts an entire prose wall.** In [scripts/gen-backlog-page.py:1063](scripts/gen-backlog-page.py:1063), `_one_block` returns false whenever `<ol class="enum">` exists, regardless of the text outside it. Executed:

```python
t = ("**T** — " + "wall word " * 100
     + ": (a) first item with enough words here"
     + " (b) second item with enough words here")
unlaid_rows([{"num": 999, "body": t}])
# []
```

This 1,086-character row renders a 1,000-character prose wall before two short list items, yet passes. The guard should assess prose outside the list.

Other checks passed:

- Compared **284 history versions**, **55,635 row instances**, **1,426 distinct row texts**: zero rendered-word losses, lost key groupings relative to the old tokenizer, or provenance-suppressed label cuts. The 466 tokenizer differences reflect rendered Markdown, including preserved literal code characters.
- Literal `¶` survives. U+E000 is removed from input and absent from the generated page; it would still lose literal user content containing that character.
- **76 mutations**, **pin 76**, every anchor resolves exactly once. The standard harness refused its estimated 118-minute local run. Direct runs of each mutant against its declared named cases all produced the expected failures.
- **246/246 self-tests passed**. Page rendered successfully with **458 rows**. Every current body and Status cell preserves visible text through layout; current `unlaid_rows` is empty.

No tracked files modified. `.claude/plans/` was not read.

VERDICT: NOT CONVERGED

<!-- codex-review: model=gpt-6.1-sol -->

**MEDIUM — A remains incomplete: escaped surrogate text prevents page generation.** At `scripts/goal-tree.py:2085`, validation accepts strings containing unpaired Unicode surrogates. Writing the fragment at `scripts/goal-tree.py:2378` then raises outside the error handling.

Concrete UTF-8 answers-file input:

```json
{"answers":[{"key":"goal:missing","q":"q","a":"\ud800","asked":"today"}]}
```

Calling `write_page(..., answers_path=that_file)` with a self-test snapshot produced:

```text
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' ...: surrogates not allowed
page_exists False
stderr ''
```

`load_answers` returned the row with an empty error string. Independently putting `"\ud800"` in `key`, `q`, or `asked` produced the same failure. Thus this malformed string neither writes the page nor produces the promised named warning.

Other fold checks:

- **A:** Constructed twelve files covering top-level null, number, list, missing `answers`, null/number/dict `answers`, invalid entries, non-text `asked`, non-UTF-8 bytes, and truncated JSON. Each wrote a page with the filename in both the page warning and stderr.
- **B:** Removed each protection independently in memory: answer-body escaping, `asked` escaping, Older-key escaping, answers-error escaping, and `_has_tray(written)`. Every mutation returned failure with its corresponding named test red: **`470/471 self-test cases passed`**.
- **C:** The closed older-thread and folded-goal cases pass: both thread markers appear outside the folds and identify their threads. The inline-marker case also passes. No remaining hidden-marker case found.
- **D:** PR #558 now sits under `comprehensibility-suite`; the intended two-goal PR #557 binding remains.
- **E:** A declaration containing `backlog #40, PR #20`, with `PR #777` in its prose and `PR #999` in the entry id, returned exactly `{("backlog", 40), ("PR", 20)}`. An undeclared entry with `id: "PR #9"` returned `{("PR", 9)}`. Read all seven real entries from the main master checkout’s `.claude/inflight.jsonl`: all attach to their intended tracked threads, including PR #557 under both intended goals. No remaining misattachment found.
- **F:** `scripts/explainer-serve.py:237` includes `docs/goal-tree-answers.json` in the goal-tree stale-page sources.
- **G:** The arithmetic at `scripts/goal-tree.py:2344` is correct: `6.3 + 9.8 + 30 = 46.1`, leaving `13.9` seconds. The old 40-second setting totals `56.1`, leaving `3.9` seconds. These measurements provide headroom, not a worst-case guarantee.

Ran `python3 scripts/goal-tree.py --self-test`: **`471/471 self-test cases passed`**. Reviewed both flagged call-site rewrites in context; page preconditions remain, and tray failures gain explicit reporting. Tracked files remain unchanged; no GitHub actions or `.claude/plans/` reads.

## Loosening answers
LOOSENING-CHECK 6f409fec68b9: not a loosening
LOOSENING-CHECK 6b028c4b7f85: not a loosening
VERDICT: NOT CONVERGED

<!-- codex-review: model=gpt-6.1-sol -->

- **R1 — High — `scripts/check-compaction-boundary.py:126–128`: Arbitrary pipeline work is exempted.** `tail -F ~/explainers/questions.md | gh run watch 123` returns `True` from `question_watcher()`, as does the `|&` variant. Downstream stages need not be filters. With no other signal, compaction can proceed while CI is running.

- **R2 — High — `scripts/check-compaction-boundary.py:128`: Process substitution bypasses the chaining check.** `tail -F ~/explainers/questions.md | cat <(gh run watch 123)` is valid Bash and classified as a watcher. The CI process runs immediately, but its Monitor stops blocking compaction.

- **R3 — High — `scripts/check-compaction-boundary.py:271`: Quote stripping hides executable shell separators.** This valid Bash command is classified as a watcher:
  ```bash
  tail -F ~/explainers/questions.md | echo \' ; gh run watch 123 # '
  ```
  The first apostrophe is escaped, but the regex treats it as opening a quoted region and strips the executable `; gh run watch 123`. A newline after an accepted pipeline also bypasses `CHAINED_RE`.

Validation: **87/87 self-tests passed**; all **eight new mutations failed their named cases**. The actual §5 watcher command matches. A harmless double-quoted `";"` is rejected. The passing suite does not cover the unsafe command shapes above.

VERDICT: NOT CONVERGED

# Code review r2 — `backlog-99-paused-tick` (7d1b8c16) — CODEX half

SCOPED to the r1 fold (`git diff 673b4a8b..HEAD`). Model gpt-5.5.

Ran all three suites to completion, including the mutation sweep it could not finish in r1:
35/35, 49/49 (47/47 at review time), 206 mutations / 0 survivors.

⚠ ADJUDICATION BY THE COORDINATOR: the High is CONFIRMED and UNDERSTATED. Codex named U+2028
and U+2029. Enumerating the full `str.splitlines()` set found **eight** separators that
defeated the guard — \\v \\f \\x1c \\x1d \\x1e \\x85 U+2028 U+2029 — and
`parse_sentinel` on the resulting sentinel returned the injected
`{'plan': '.claude/plans/other.md', ...}`. Fixed by asking `splitlines()` itself rather than
lengthening the character list, which is the recorded *measure the population the CODE sees*
shape: the first guard was a hand-written copy of the consumer's rule and covered 2 of 11.

---

<!-- codex-review: model=gpt-5.5 -->

High: `--pause` still accepts Unicode line separators, reopening `plan:` field injection. [scripts/begin-plan.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:414) rejects only `"\n"` and `"\r"`, but the sentinel parser uses `text.splitlines()` at [scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:82), and `strip_field()` uses the same split semantics at [scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:106). Python treats U+2028 and U+2029 as line breaks there. I drove this with `cmd_pause("waiting\u2028plan: .claude/plans/other.md")`: it wrote one accepted `paused:` value, `parse_sentinel()` then produced `{'plan': '.claude/plans/other.md', 'armed': 'now', 'paused': 'waiting'}`, and after `cmd_resume()` the sentinel text was `plan: .claude/plans/p.md\narmed: now\nplan: .claude/plans/other.md\n`. The later injected `plan:` wins, so the guard can supervise and clear based on the wrong plan. The new mutation at [scripts/mutations/begin-plan.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/begin-plan.json:94) only proves the ASCII newline branch; it does not exercise the full `splitlines()` grammar that the parser and remover actually use.

Verification run:
`python3 scripts/check-plan-progress.py --self-test` -> `35/35`
`python3 scripts/begin-plan.py --self-test` -> `47/47`
`python3 scripts/check-plan-code.py --mutate .` -> `206 mutation(s), 0 survivor(s)`

NOT CONVERGED.

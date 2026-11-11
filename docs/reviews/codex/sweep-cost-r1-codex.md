<!-- codex-review: model=gpt-6.1-sol -->

No actionable findings.

`layout_body` reads layout globals, but no current caller or self-test changes them. It reads no files, environment variables, or clock; all call arguments are immutable strings. The state patched by self-tests does not affect its cached output.

`_drifted` depends on more than `unread`, but those dependencies stay fixed across its calls. I found no case requiring recomputation and no cache-induced survivor scenario.

The documentation distinguishes local timings from CI measurements. I found no demonstrably false measurement claim; the historical numbers were not independently reverified.

`python3 scripts/gen-backlog-page.py --self-test`: **247/247 passed**. No mutation sweep run.

VERDICT: CONVERGED

<!-- codex-review: model=gpt-6.1-sol -->

No findings.

- Refusal logic is unchanged; only `_self_test_body`, the case count, and the mutation’s expected assertion changed.
- `scripts/codex-review.py:2967–2982`: concrete input `<tmp>/alias6/docs/reviews/claude/victim-r1-claude.md`, with `alias6 -> h` and `h/docs/reviews -> external/reviews`, bypasses both lexical guards and resolves outside both checkouts on Linux and macOS. Only the resolved-review-roots clause refuses it. The guard assertion, victim reset, `--allow-overwrite`, and exact refusal checks exclude ambient passes.
- Merge `95d778af` introduces no changes under `scripts/`.

Validation: self-test **213/213 passed**; mutation sweep **71/71 killed and attributed**, including r6 X1; zero survivors. Cross-platform conclusion follows from the explicit symlink layout; execution was on this host.

CONVERGED

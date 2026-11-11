<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `f6d01b94`. Two findings:

1. **[P2] W10 inherits the temporary directory’s containing checkout.** `scripts/check-run-hook.py:198` constructs “outside any checkout” beneath `TemporaryDirectory()`, which honors `TMPDIR`. Setting `TMPDIR` to a directory inside a temporary git checkout makes the correct launcher select that containing checkout. I reproduced the guard invoking its hook instead of the fixture project’s hook: ordinary mode exits 1; self-test reports **42/45**, including W10 and control failures. Verify W10’s filesystem ancestry; use a genuinely checkout-free location or report CANNOT RUN when unavailable.

2. **[P3] Published guard counts are stale.** `docs/backlog.md:346` and `docs/dashboard-entries.md:17874` claim **32 cases / 20 mutations** for `check-hook-commands.py`. Executed results are **45/45 cases and 34/34 mutations**, matching the current docstring and PR body.

Otherwise, execution supported the implementation:

- Normal launcher self-test: **63/63**.
- Mutation commands: **9/9 and 34/34 killed and attributed**, including final controls.
- All **16 launcher mutants** independently failed their named worlds, with green controls before and after.
- All 14 registrations preserve their previous fields; CANONICAL accepts them and rejects tested shell additions. LAUNCHER exemption is narrow.
- Independent worktree, submodule, missing-hook, environment, symlink, unusual-path, deleted-cwd, name, stdin and exit-2 probes behaved as intended.
- Hostile global git config and inherited `GIT_*` did not contaminate fixture results.

Live Claude Code blocking and an actual push remain unverified. The real push hook returned `deny` through `/bin/sh -c` from a subdirectory. I did not rerun all 63 CI guard steps. Repository unchanged; experiments stayed in the temporary copy.

VERDICT: NOT CONVERGED

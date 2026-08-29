<!-- codex-review: model=gpt-5.5 -->

Medium — `scripts/gen-dashboard.py:759`: the new guard does not test contrast, only token presence. A single-token CSS edit from `--link:#8cbde0` to `--link:#0000EE` reintroduces the real dark-mode failure at 1.90:1 on `--bg:#14181b`, while the case still passes because `a{color:var(--link)}` exists and `ht.count("--link:") == 2` remains true. Same for `scripts/gen-dashboard.py:764`: changing `--link-visited:#c3a6e0` to `--link-visited:#551A8B` gives 1.62:1 and still passes. This matters because the guard claims to prevent the readable-link regression class, but only prevents deleted rules/definitions. Concrete fix: parse the generated CSS variables in `_self_test()` and assert measured contrast for `--link`, `--link-visited`, and hover ink against both `--bg` and `--panel` in both schemes is at least 4.5:1.

Checks run:
`gen-dashboard.py --self-test`: 105/105 passed.
`gen-backlog-page.py --self-test`: 55/55 passed.
`gen-backlog-page.py`: built `/Users/kujinlee/explainers/backlog-table.html`.
`check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --compare . --verify-evidence`: `OK — compared + evidence-verified: 2 file(s), 43 mutation(s), 0 survivor(s)`.

Measured current ratios: light link 6.58 on bg / 6.99 on panel; light visited 6.85 / 7.28; dark link 8.90 / 8.11; dark visited 8.38 / 7.63; hover ink clears AA in both schemes. `--link-visited:` contains `--link` but not `--link:`, so `ht.count("--link:")` is not accidentally inflated by visited definitions.

I also checked the named neighboring producers: `gen-backlog-page.py`, `gen-goals-page.py`, and `explainer-serve.py` all define link colors via theme variables or dark-mode link rules; I did not find the same UA-default dark-link defect there. Backlog #69 and #70 match the actual open backlog rows and are in the process/CI guardrails group.

NOT CONVERGED — the shipped CSS is currently readable, but the new regression guard is too weak to catch a one-token return to the exact contrast defect.

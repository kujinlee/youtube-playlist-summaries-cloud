<!-- codex-review: model=gpt-5.5 -->

**Findings**

High, [scripts/gen-backlog-page.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1439): `link_contrast_errors()` does not test normal `.num a` link color.  
What is wrong: `.num a` inherits `.num`’s foreground from [line 1122](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1122), but `LINK_FG` only measures `--structural` and hover `--ink`. The page currently has 70 `.num a` links.  
Why it matters: a real contrast regression survives. Control was green (`64/64`). Mutation `color:var(--ink-3)` -> `color:var(--line)` on `.num` kept self-test green (`64/64`) and `link_contrast_errors(page) == []`, while those links rendered at `1.37:1` light and `1.30:1` dark on `--card`.  
Fix: include the inherited normal-state number-link foreground in the contrast model, e.g. add `--ink-3` to the measured foregrounds or add a selector-aware assertion for `.num a` on `.item`/`--card`.

**Checks Run**

Controls passed:

```text
python3 scripts/gen-dashboard.py --self-test                          111/111 passed
python3 scripts/gen-backlog-page.py --self-test                       64/64 passed
python3 scripts/check-plan-code.py ... --compare . --verify-evidence  OK, 2 files / 43 mutations / 0 survivors
```

Backlog palette regex check: actual generated page yields 4 blocks: `:root`, dark-media `:root`, `:root[data-theme="dark"]`, `:root[data-theme="light"]`. It does not match `:root[data-theme="dark"] .diff del{...}`.

`--verify-evidence` is not evidence that the new contrast guards are mutation-covered: the manifest is still 43 existing mutations, and the survivor above is outside it.

NOT CONVERGED: the fix added contrast measurement, but it still misses an actual rendered link class and lets a real low-contrast mutation survive.

<!-- codex-review: model=gpt-5.5 -->

**Findings**

- High: [scripts/check-merge-ready.py:213](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:213) claims the substring scan “cannot be weaker than the parser,” but a real PR-only gate can exist in `ci.yml` without the literal `pull_request`. Since `ci.yml` only runs on `pull_request` and `push`, a step with `if: github.event_name != 'push'` is PR-only. The parser does not claim it because `PR_ONLY_COND` only matches equality to `'pull_request'`, and `unaccounted_mentions()` does not flag it because there is no `pull_request` substring. I verified with a direct probe: `pr_only_steps(...) == []` and `unaccounted_mentions(...) == []`. That means the script can still report READY while skipping a CI gate.

**Verification**

- `python3 scripts/check-merge-ready.py --self-test`: 49/49 passed
- `python3 scripts/check-plan-code.py --self-test`: 128/128 passed
- `python3 scripts/check-plan-code.py --mutate .`: NOT RUN to completion; I interrupted it after 173/780 mutations because it was taking too long for this review.

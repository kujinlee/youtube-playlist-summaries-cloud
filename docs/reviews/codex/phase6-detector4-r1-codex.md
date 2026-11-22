<!-- codex-review: model=gpt-6.1-terra -->

- **BLOCKER — silent loss caused by the build:** [check-publishability.py:358](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/phase6-detector4/scripts/check-publishability.py:358). For this list, the pre-build version reports both terms as dependencies; the build reports both as mentions:

  ```markdown
  Run these:
    - first
  - `CronList` and `acmecorp`
  ```

  In a scratch fixture, detector 4 moved `CronList` from a finding to a mention, and the shared Markdown judgement did the same for detector 1’s vocabulary term `acmecorp`. The earlier, two-space-indented item stops the build’s sibling walk. This refutes the claim that the replacement loses nothing.

- **MAJOR — timing failure, neither silent loss nor precision:** [check-publishability.py:408](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/phase6-detector4/scripts/check-publishability.py:408). A single nonblank line containing `blah CronList ` repeated 5,000 times returned `mention` after **4.23 seconds** for one term; 10,000 repetitions took **17.17 seconds**. This exceeds the spec’s one-second bound. A separate flat-list probe of 100,000 ordinary items followed by one matching item took 0.09 seconds for that term; it did not establish whether quadratic behavior is reachable in a full real-file scan.

The scratch comparisons also covered headings, numbered and nested lists, block quotes, tables, tagged and untagged fences, wrapped sentences, a blank after a colon, HTML comments, front matter, and continuation-line code spans. The loss above is the loss observed in those probes.

The self-test passed **116/116**. Three scratch mutations—disabling heading introduction, wrapped sentences, and every-span matching—each caused relevant new self-test cases to fail. A fresh scan matched [scan-2026-11-17.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/phase6-detector4/docs/marketplace/scan-2026-11-17.json) after removing `measured_at`.

## Loosening answers
LOOSENING-CHECK 1acdaec7c7d4: finding: an introduced list with a two-space-indented first item followed by an unindented item now treats terms in the latter as mentions instead of dependencies
VERDICT: NOT CONVERGED

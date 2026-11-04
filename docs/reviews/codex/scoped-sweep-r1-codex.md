<!-- codex-review: model=gpt-6.1-sol -->

1. **P1 — Computed sibling imports omit an affected manifest.** [scripts/check-plan-code.py:357](scripts/check-plan-code.py:357) adds the extensionless stem only for Python identifiers. Hyphenated siblings loaded through [goal-tree.py:154](scripts/goal-tree.py:154), such as `_sibling("gen-work-lines")`, therefore escape matching.

   Concrete PR input: change [gen-work-lines.py:138](scripts/gen-work-lines.py:138) from:

   ```python
   dict(p, children=[])
   ```

   to:

   ```python
   dict(p, children=[], empty=p["empty"] or p["done"])
   ```

   Observed in an isolated copy using the existing mutation **“#389: a finished plan inside an open line is listed as owing”**:

   | Input | Goal-tree control | Goal-tree mutant |
   |---|---:|---:|
   | Original helper | 205/205, rc 0 | 200/205, rc 1 |
   | Changed helper | 205/205, rc 0 | 205/205, rc 0 |

   The mutation now survives, but `select_manifests("pull_request", ["scripts/gen-work-lines.py"], …)` selects **7/87 manifests, excluding goal-tree**. Expected: include goal-tree or select FULL. This is a runtime dependency omission, independent of the accepted orphaned-anchor residual. Changes to `gen-dashboard.py` and `session-state.py` also omit their goal-tree consumer.

2. **P2 — The master backstop retains the pending-run cancellation hole (#482).** [.github/workflows/ci.yml:29](.github/workflows/ci.yml:29), with the new backstop claim at [line 18](.github/workflows/ci.yml:18).

   Concrete sequence: master run A is active; merge B queues its run; merge C arrives before A finishes. The shared concurrency group replaces pending B with C despite `cancel-in-progress: false`. [GitHub documents this default behavior](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency).

   Observed configuration consequence: B executes neither its full sweep nor `mutation-sweep-complete`; its alert step cannot execute. Expected under “every master push”: B receives full mutation evidence, or its missing evidence becomes visibly actionable. This limitation predates the PR, but the new scoped design relies on that backstop. A later scheduled sweep checks the later tree, not B’s discarded commit.

Other checks:

- Whole-manifest counts, duplicate/anchor validation, and home-escape scans remain before selection. Controls surround execution of selected targets.
- An empty selection explicitly reports “nothing to do,” runs zero mutations, and returns rc 0. Undetermined diffs, push events, and schedules select FULL.
- The required aggregate check rejects non-success shard results. `issues: write` is scoped to that aggregate job; subsequent red runs comment on the existing open alert.
- Docs-only master pushes now receive FULL, consistent with the approved decision. Scheduling `verify` adds work; I found no weakened gate there.

Required suites passed: **check-plan-code 291/291; check-merge-ready 256/256**. Repository `.claude/plans/` content was not read.

VERDICT: NOT CONVERGED

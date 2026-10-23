<!-- codex-review: model=gpt-6.1-sol -->

Three **Blocking** paths still write wrong nonempty links.

All three were executed through `run(..., write=True)` against temporary copies of the real plans, using constructed transcripts and fixture birth times. No repository files or real plans were changed. These establish reproducible failures; wrong links from these shapes in the unmodified real corpus remain **UNVERIFIED**.

1. **Blocking — `scripts/backfill-work-lines.py:790–794`: stale output becomes an authoritative checkpoint.**

   State: `banner-blind-spot` is armed. Run:

   ```sh
   cat /tmp/old-sentinel; cat .claude/executing-plan >/dev/null
   ```

   The old file prints `plan: .claude/plans/r8-fold.md`. The command names the sentinel exactly once, so the parser accepts the unrelated output, resets replay to `r8-fold`, and counts the disagreement as resolved.

   Arm `phase6-chrome-instrument`, then observe its status. Executed write, `rc=0`:

   ```text
   <!-- parent: r8-fold -->
   <!-- parent-source: transcript sess-aaa 2026-10-01T12:00:40.000Z -->
   ```

   Correct parent: `banner-blind-spot`.

   **Fix:** accept read checkpoints only when the output can be attributed exclusively to the sentinel read. Counting sentinel mentions does not establish output provenance; reject compound commands, redirected reads, and unrelated output producers unless attribution is proven.

2. **Blocking — `scripts/backfill-work-lines.py:716–718`: hidden subprocess arms can evade every subsequent checkpoint.**

   State: `banner-blind-spot` is armed. A Python heredoc executes:

   ```python
   subprocess.run([
       'python3', 'scripts/begin-plan.py', 'round-6-scoped', 'a'
   ])
   ```

   Heredoc stripping removes the invocation, and the opaque-write detector does not recognize subprocess execution. The entire command disappears from replay.

   Arm `phase6-chrome-instrument`, then query its status. Executed write, `rc=0`:

   ```text
   <!-- parent: banner-blind-spot -->
   <!-- parent-source: transcript sess-aaa 2026-10-01T12:00:40.000Z -->
   ```

   Correct parent: `round-6-scoped`. Checkpoint statistics report **zero disagreements**: the next arm overwrites the hidden state, so its subsequent status agrees. Agreeing checkpoints do not bound intervening lineage errors.

   The real transcript contains this mechanism at **2026-10-17T21:12:43.480Z**, where `/tmp/steps.py` invokes `begin-plan.py` through `subprocess.run`.

   **Fix:** treat executable wrappers that may invoke plan operations as opaque state changes, retaining affected arms as no-marker until trustworthy pre-arm evidence establishes their parent. Document the remaining completeness bound.

3. **Blocking — `scripts/backfill-work-lines.py:1053–1055`: opaque writes poison state after same-command arms have already received links.**

   State: `banner-blind-spot` is armed. Execute one command:

   ```sh
   python3 - <<'PY'
   from pathlib import Path
   Path('.claude/executing-plan').unlink()
   PY
   python3 scripts/begin-plan.py phase6-chrome-instrument a
   ```

   The opaque write is detected, but replay derives the arm’s parent first and applies UNKNOWN afterward. A subsequent status resync accepts UNKNOWN and clears pending records without invalidating that wrong parent.

   Executed write, `rc=0`:

   ```text
   <!-- parent: banner-blind-spot -->
   <!-- parent-source: transcript sess-aaa 2026-10-01T12:00:30.000Z -->
   ```

   Correct parent: `-`. Statistics show **zero disagreements, two resyncs**.

   **Fix:** poison state before processing any arm in an unorderable command, and explicitly disqualify every arm whose parent could depend on that command’s opaque mutation.

Validation: baseline **85/85** passed, including the supplied round-1 reproductions. Real `--ground-truth` returned `rc=0`, with **386 agree, 1 disagreement resolved, 99 resyncs**.

I independently applied all **48 mutation entries** in memory. Every entry emitted its named expected failure, covering the 15 new and 15 rebound entries. The existing provenance-label mutation additionally raised `IndexError` after emitting its expected failure. Those mutation results do not cover the three counterexamples above.

VERDICT: NOT CONVERGED

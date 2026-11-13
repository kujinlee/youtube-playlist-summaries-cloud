# Round 1 — `mutation-early-stop` (draft PR #476, backlog #405) — coordinator — NOT CONVERGED (both halves)

Codex half: `docs/reviews/codex/mutation-early-stop-r1-codex.md`. Claude half: `docs/reviews/claude/mutation-early-stop-r1-claude.md`. Both reviewed `98beb6b1`.

```yaml
round: 1
fixes_nontrivial: true
subject: mutation-early-stop
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: stop-rule, disposition: fixed}
  - {id: C-H1, severity: High, aim: deliverable, fix_induced: false, component: stop-rule, disposition: fixed}
  - {id: C-M1, severity: Medium, aim: deliverable, fix_induced: false, component: ci-concurrency, disposition: fixed}
```

**What they found:**
- **X1 (Codex), the trailer calls a helper.** `edit_needs_full_run` reads only the enclosing functions of the
  mutant's own edit. It misses a helper the trailer calls, so a mutant in that helper is recorded KILLED early
  and SURVIVED in full.
- **C-H1 (Claude), the PR breaks the exit code itself.** A PR that breaks the trailer of the UNMUTATED file
  (reproduced with `return 0`) or changes a shared module (`fixture_git.py`) gets the same false kill. The edit
  predicate cannot see either.
- **C-M1 (Claude), master runs can be cancelled.** `cancel-in-progress: true` also cancelled push runs on
  master. A later docs-only merge skips its own sweep, so it could cancel an earlier scripts merge's FULL sweep,
  and early stop on pull requests relies on that sweep.

**X1 and C-H1 are ONE class.** Early mode assumed that "the named case printed `[FAIL]`" implies "the suite exits
non-zero". The guard predicted that from the edit's source, and that is a parsing surface with no end. **The fold
no longer predicts it. It relies on a measurement.** A mutant may stop early only when master's FULL sweep has
already run the same file, the same manifest and the same imported code. That is `early_must_run_full`. A mutant
runs in FULL when there is no diff, when the PR changed the target file, when it changed the target's manifest (a
new entry, which is X1's shape), or when it changed any `.py` file whose stem the target's source names (a shared
module or a sibling). The match is on text and is deliberately coarse. It needs no call graph.
- **Cost:** every mutant of a file the PR touches runs in full. A PR that changes `fixture_git.py` gets a full
  sweep.
- **Bound:** the rule does not see an import the source does not spell out.
- **Test:** the FAILS-IF self-test is Claude's reproducer, a trailer ending in `return 0`. Early mode must record
  it SURVIVED both when the PR changed the file and when it changed the manifest. A control is included: the same
  file, untouched by the PR, IS stopped.
- **Local runs:** `--early-stop` now takes `git diff origin/master...HEAD`. When it cannot take the diff, every
  mutant runs in FULL.

**C-M1:** `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. The comments that claimed "a full sweep
on every push to master" now say the sweep runs when the merge touches a sweep-relevant root, and that a push run
is never cancelled.

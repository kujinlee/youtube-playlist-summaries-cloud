# Round 1 — `batch-ci` (PR #529, backlog #534) — coordinator — both halves NOT CONVERGED; all 15 findings FIXED

```yaml
round: 1
fixes_nontrivial: true
subject: batch-ci
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1-F1, severity: Blocking, aim: deliverable, fix_induced: false, component: readiness, disposition: fixed, commit: f9fd9c40}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: landing, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F3, severity: High, aim: deliverable, fix_induced: false, component: landing, disposition: fixed, commit: f9fd9c40}
  - {id: C2, severity: High, aim: deliverable, fix_induced: false, component: landing, disposition: fixed, commit: f9fd9c40}
  - {id: C3, severity: High, aim: deliverable, fix_induced: false, component: run-verdict, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F2, severity: High, aim: deliverable, fix_induced: false, component: union, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F4, severity: Medium, aim: deliverable, fix_induced: false, component: run-verdict, disposition: fixed, commit: f9fd9c40}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: union, disposition: fixed, commit: f9fd9c40}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: attribution, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F5, severity: Medium, aim: deliverable, fix_induced: false, component: attribution, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F6, severity: Medium, aim: deliverable, fix_induced: false, component: coverage, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F7, severity: Medium, aim: instrument, fix_induced: false, component: self-test, disposition: fixed, commit: f9fd9c40}
  - {id: C-refresh, severity: Low, aim: instrument, fix_induced: false, component: self-test, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F8, severity: Low, aim: deliverable, fix_induced: false, component: advisory-line, disposition: fixed, commit: f9fd9c40}
  - {id: R1-F9, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed, commit: f9fd9c40}
```

Codex (`docs/reviews/codex/batch-ci-r1-codex.md`, C1–C5 plus an unnumbered note, recorded here as `C-refresh`) and
Claude (`docs/reviews/claude/batch-ci-r1-claude.md`, R1-F1–F9), both on `4ae91ab3`. Folded on `5e9bbdad`. Nothing
declined, refuted or filed. Each fix has a self-test case that goes red with the fix reverted, and each revert is a
mutation in `scripts/mutations/batch-ci.json`, so the sweep shows the red.

**R1-F1 (Blocking) — decided: admit READY, or NOT READY solely because DIRTY; any HOLD refuses.** `plan` runs
`check-merge-ready.py --pr N` at the PR's head in a temporary worktree (it compares the PR head to the local HEAD, so
it must run there), and `merge_ready_admits` reads the answer. Why DIRTY is admitted: once any member lands, every
other open PR that appended a backlog row is DIRTY, so READY-only would empty every batch. A conflict with master is
the one reason the batch answers itself: it resolves the conflict (append-only files) or ejects the PR. Any `HOLD`
line refuses, whatever the rc, because `final_verdict` prints a NOT READY PR's holds but returns rc 1 for it. `land`
asks again at the head about to merge and requires READY there. Before pushing a refresh, the DIRTY-admissible
answer is enough. Limit, stated in `_merge_ready`: the PR's own copy of the checker runs, as the house rule runs it.

**C1 + R1-F3 — bound and predicted, and the remaining race is stated.** Before each merge `land` re-fetches master
and stops if it moved from the master already validated (the start check, then each post-merge read). It predicts
GitHub's squash with `git merge-tree --write-tree <validated master> <head>`, and stops unless that is the batch's
tree for the step. The race left: `gh pr merge` has no base-SHA guard, so a merge by someone else in the seconds
between that fetch and the squash (one `merge-tree`, one `gh` call) is caught only by the post-merge tree assertion,
which STOPS LOUDLY. The R1-F3 topology (a stacked PR whose batch merge base differs from the squash's) is a real-git
e2e case.

**C2:** the base (and head and state) are re-read immediately before the merge, and the base is also checked before
a refresh is pushed. **C3:** `latest_run` picks the highest run number, then attempt, and `land` needs the latest
run of EVERY workflow green. **R1-F4:** `classify` returns RED only when a job FAILED (the aggregate aside).
Cancelled, skipped, stale, action_required, still running, and a failed run whose shards were only cancelled (a
timeout reads as cancelled) are NO VERDICT, rc 2: re-run, never eject.

**C4 + R1-F2:** `dashboard-entries.md` and `goal-threads.md` union by whole added blocks split at `## `. A block is
dropped only when the other side added the identical block. The decision log unions by records (whole JSON lines,
exact duplicates). Both failures are reproduced through real git merges (`_e2e_union`). **C5 + R1-F5:** a failure
owns its target's `import_closure` (imports at any indentation, `.py` literals, transitively, plus the harness). It
EJECTS only when exactly one member touches anything in that set, which is pure and tested, and at the call site in
the e2e.

**R1-F6 — run, not just stated.** `schema-gates.yml` now runs on `push: batch/**`: its job touches no production,
and each batch has its own concurrency group. `land` requires its latest run green and prints `COVERAGE`: what the
batch tested, and that test:integration and test:e2e (in no workflow) were NOT tested. **R1-F7:** all 11 survivors
now have a killing case and a manifest entry, plus one per new guard. Pin 28 -> 68. **C-refresh:** `_refresh`'s
pre-push tree check is now mutated and killed (a fixture makes the refresh tree differ; nothing is pushed).
**R1-F8:** a 15 s timeout per call, at most 5 compares, and a refused compare or a timeout reads `advisory: not
checked`. Pin 106 -> 110. **R1-F9:** the counts are derived from the suite (123) and the manifest (68); the EXEMPT
reason no longer types a PR count.

**Mutation sweeps (local `--mutate . --only <script> --allow-long-local`, a diagnostic slice, not the gate):**
check-merge-ready 110/110 killed, each attributed to the case it names. batch-ci 65/68 on the first sweep. The three
survivors were fixed before the commit. (1) `a conflict in a file outside UNION_FILES…` was EQUIVALENT: its
replacement policy `"lines"` is unknown, so `resolve_hunk` refused it anyway. It is re-aimed at `"records"`, a real
policy. (2) `a red non-sweep job is attributed through the sweep log` was MASKED: the log left over from the previous
case also led to BISECT. The case now sets a log that would EJECT PR 1, and asserts no EJECT. (3) `land merges onto a
master that moved outside the batch` was MASKED by the later merge-tree prediction. The case now asserts the specific
message, and a new case covers the DRY RUN, where this check is the only guard. Each of the three was re-applied by hand
to a copy of `scripts/` and went red on the case it names. The full batch-ci sweep was NOT re-run after these
three edits; the CI full sweep on push is the gate. The sweeps staged their tree before a few self-test-only additions,
and those can only add kills.

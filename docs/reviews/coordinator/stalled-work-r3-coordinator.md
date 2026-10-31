# Round 3 — `stalled-work` (PR #452, backlog #410) — coordinator — NOT CONVERGED (Claude); the route moves to SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: stalled-work
halves:
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  claude: ran
findings:
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: merged-check, disposition: fixed}
  - {id: F2, severity: Major, aim: deliverable, fix_induced: false, component: merged-check, disposition: fixed}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: true, component: cache, disposition: fixed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: true, component: time-bound, disposition: fixed}
  - {id: F5, severity: Minor, aim: deliverable, fix_induced: false, component: merged-check, disposition: fixed}
  - {id: F6, severity: Minor, aim: deliverable, fix_induced: false, component: merged-check, disposition: fixed}
  - {id: Nit, severity: Low, aim: deliverable, fix_induced: false, component: cache, disposition: fixed}
```

The Claude half reviewed `715bfda6` against synthetic repositories and the real one. **The redesign's shaping held:** no path from a fact to text bypasses `shape`, and a planted schema-valid cache was withheld at render. **The bet is refuted on the merged check, the cache and the failure path:**

| ID | Severity | Finding | Fold (every one TDD: red first, then the fix) |
|---|---|---|---|
| F1 | Major | a merge commit is never compared (`--no-merges`, `git cherry`), so an evil merge is MERGED and told "delete the branch" | MERGED now also needs `git merge-tree --write-tree origin/master <tip>` to equal `origin/master^{tree}`. Case: the reviewer's `evil2` |
| F2 | Major | an orphan branch's `merge-base` exit 1 turns the WHOLE check into an anonymous CANNOT RUN | exit 1 with no output is "not merged". Case: an orphan beside three other tips; the run is rc 1, not 2 |
| F3 | Minor | a cached `merged: true` is re-rendered after the tip moved | a tip fact stores its sha; a hit re-reads each tip's ref from the FILES (worktree HEAD, loose ref, `packed-refs`) and a mismatch is a miss. Cases: a moved tip, and a packed one that stays a hit |
| F4 | Minor | any non-`CannotRun` exception makes the hook fail OPEN: (a) `killpg` raises `PermissionError` on macOS; (b) `kind: []` raises `TypeError` | a catch-all in `main --hook`; the hook SCRIPT prints a fixed CANNOT RUN when the check dies (argparse); `killpg`/`kill` catch `OSError`; the drain is bounded at 1 s, then the pipes are closed; `kind` must be a `str`. Five cases |
| F5 | Minor | a copy master later reverted is MERGED | covered by F1's merge-tree rule. Case: `rev` |
| F6 | Minor | trunk patch-ids recomputed per candidate | memoised per merge base (`Trunk`). Measured, 72 all-'-' candidates: 473 trunk commits 3.3-3.8 s → 2.0-2.2 s; 2,073 commits 6.2-8.4 s → 2.7-2.8 s. Real repo (24 tips, no candidate MERGED): 0.76-0.90 s → 0.65-0.73 s |
| Nit | Low | a resolved item keeps its cached STALLED for up to 10 min | stated in BOUNDS |

**A bound the fold creates, stated rather than hidden:** a rebase-merged tip whose lines master LATER changed (an edit, or a revert as in F5) is now STALLED, not MERGED — the merge conflicts or would change master. It is conservative, like the squash, and has its own case.

**One mutation retired as EQUIVALENT, not with its subject:** R2-3's `--verbatim` → `--stable` now survives (measured, 233/233 green), because `git merge-tree` refuses the whitespace case by itself. Eight entered; each was run against the suite and went red via the case it names. The hook script's own fallback has a case but no mutation: no manifest mutates `.claude/`.

**Route: SPLIT** — the ladder's next rung. ACCRETE (r1) and REDESIGN (r2) are both spent, and `check-decision-scheme.py` refuses an ACCRETE row here as a RETRY (measured). The unstable half is the **cache**: findings in r2 (R2-1, R2-4, R2-5) and r3 (F3, the nit).

**What was done (2026-10-31): SPLIT, executed — the cache is removed from this PR.** The fold first kept the cache with a conditional ("drop it if r4 finds a cache defect"); the coordinator decided otherwise, as r2's decision row pre-registered: SPLIT means ship the uncached check. The cache is filed as **backlog #419** and preserved on the branch `stalled-work-cache` at `7d0aebf7` (pushed; no PR). Removed from `scripts/check-stalled-work.py`: the cache read and write, `CACHE_VERSION`, `valid_snapshot`, the tip-sha re-read and its file readers, the "as of Nm ago" line, and the BOUNDS line about stale cached answers; with them their cases (self-test 233 -> 175, including F3 and the F4 `kind` cases) and 32 mutation entries (112 -> 80). F3 above is therefore **superseded, not fixed**: there is no cached `merged` to go stale. Kept, with their cases and mutations: F1 and F5 (merge-tree), F2 (orphan), F4 (catch-all, `killpg`, bounded drain), F6 (the Trunk memo), the 15 s Budget and the patch-id MERGED rule. The hook measures on every prompt.

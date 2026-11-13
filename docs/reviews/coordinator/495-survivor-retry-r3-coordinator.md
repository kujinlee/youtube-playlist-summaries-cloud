# Round 3 — `495-survivor-retry` (PR #564, backlog #495) — coordinator — Claude NOT CONVERGED; M1 + m1 folded, m2-m4 filed

```yaml
round: 3
fixes_nontrivial: true
subject: 495-survivor-retry
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: M1, severity: High, aim: deliverable, fix_induced: true, component: sweep-flaky-filing, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: true, component: survivor-retry, disposition: fixed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: true, component: sweep-flaky-filing, disposition: filed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: false, component: sweep-flaky-filing, disposition: filed}
  - {id: m4, severity: Low, aim: deliverable, fix_induced: false, component: sweep-flaky-filing, disposition: filed}
```

REVIEW GAP: codex — alternation

Claude (`docs/reviews/claude/495-survivor-retry-r3-claude.md`, reviewed head `d89729a5`). Round 3 is the last
folding round under the round cap (`docs/review-method.md` §0 Q4c), so the fold is narrow: the one MAJOR at its
cause, one docstring corrected, and the rest filed.

- M1 (MAJOR, caused by the r2 fold of X2): `read_flaky` raised on ANY missing shard file before reading the present
  ones, so one missing file (a shard cancelled at the job timeout skips the `!cancelled()` upload) discarded every
  other shard's FLAKY names, and none were filed. Fix at the cause: `read_flaky` returns `(names, missing)`, reading
  only the PRESENT files. `main` files `names` first, then raises naming the missing files as NOT RUN ("treat THOSE
  shards' FLAKY results as NOT CHECKED", with the count filed from the others). This is the "file first, then go red"
  order `main` already uses for the red alert. With files missing and no name read, nothing is filed: "no FLAKY
  mutation" would be a claim about shards that were not read. New case: the review's own run, the REAL step with 37
  of 38 shard files (`shard-5.txt` dropped) and a REAL manifest name in `shard-0.txt`. Result: the name is in the
  `sweep-flaky` issue, the exit is non-zero, and the output names `shard-5.txt`, `NOT RUN` and `1 of 38 shard files`.
  The two `read_flaky` cases that asserted a raise now assert the returned pair, and the missing list names only the
  absent file.
- m1 (MINOR): the `rerun_snapshot` docstring in `scripts/check-plan-code.py` said a loop fails the copy. It now
  states the real bound. A dangling or self-referencing link fails the copy. A directory link to an ancestor is
  copied deeply (~32 nested levels, exponentially more with a second alias) until the OS fails it with ELOOP. No
  real suite leaves one (0 links after all 93 controls, the reviewer's measurement). Text only.
- m2, m3, m4 (MINOR): FILED as backlog #617, not folded. m2: the producer's shard file name and the download's
  `merge-multiple` are not tied to `read_flaky` by a case. m3: FLAKY names are de-duplicated across manifests and the
  line carries no script name. m4: a NOT RUN scan and a `sweep-flaky` issue reach no session.

Self-tests: sweep-red-alert 32 -> 33 (check-plan-code unchanged at 443: m1 is text). Mutation pin: sweep-red-alert
20 -> 23. The three new mutations are: the present files' names dropped when a file is missing; the raise moved
before the filing (the r2 order); and "no FLAKY mutation" printed for unread shards. Five entries were re-bound to
the split read/raise: the filing call, the red-alert order, the unset guard, the missing-file raise and the shard
loop. `--mutate . --only scripts/sweep-red-alert.py`: 23/23 killed, each through the case it names.

## THRASHING — ARMED, filed, not run

Round 2 (Codex X2, X3) and round 3 (Claude M1) both carry findings caused by the previous round's own fold, in ONE
component, `sweep-flaky-filing`. That is the thrashing shape that arms Phase 6 (`docs/dev-process.md`, *The arming
condition is thrashing, not a count*). The review is NOT run inside this PR. It is filed as backlog #618: a Phase 6
architecture review of the sweep-flaky filing path in `scripts/sweep-red-alert.py` and the `ci.yml` shard
upload/download, citing rounds 2 and 3. Its question is whether a redesign (each shard filing its own names, or a
structured record from the harness) removes the per-file contract instead of patching it again. The decision log
records this fold as SPLIT, skipping REDESIGN, because that redesign is the filed review's to decide.

A scoped round 4 follows (ONE half, Codex, scoped to this fold), because this fold changes guarded code. Under the
round cap, its non-BLOCKER findings are FILED.

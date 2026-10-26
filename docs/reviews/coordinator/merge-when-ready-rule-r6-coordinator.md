# Round 6 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (2 High) — BET LOST, NEW UNIT

```yaml
round: 6
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: true, component: hunk-ownership, disposition: fixed}
  - {id: XH2, severity: High, aim: deliverable, fix_induced: true, component: hunk-ownership, disposition: fixed}
```

REVIEW GAP: claude — round 6 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `7aead4a8`, real git 2.49.0. Mutations 58/59 via named cases (the malformed-status
one raised `IndexError` directly), replay 8 of 40 with zero collection errors.

Two FALSE READYs, both in r5's per-path patches and both evasion-shaped: **XH1** a pathspec matches a
directory's descendants — a file under `scripts/check-x.py/` (a directory named like a renamed gate's old
path) put a `return 1` into the gate's hunks and cancelled its removal as a "move"; **XH2** a `-diff`
(binary) attribute on a gate made its patch "Binary files differ" with no hunks.

The owner chose (card, A) to end both by construction. Decision log: r5's split is scored LOST; the #353
path-source unit is closed by a `defer` row (its half held in r5 and r6) naming its successor; a new unit,
**hunk ownership**, opens with a redesign bet written before round 7.

Dispositions — FIXED: hunks are the diff of each entry's EXACT BLOBS. Both trees are read once
(`git ls-tree -r -z`, at the merge base and HEAD, `tree_index`); `blob_hunks` diffs old blob to new blob with
`--text`, or reads a whole blob for an add or delete, and a gitlink (mode 160000) has none. A blob diff has
no path, so no pathspec and no attribute can touch it. Hunks are read only under `scripts/`, `.claude/`,
`.github/`, the only places a detector looks (replay: 1,149 git calls -> 313). `--no-textconv` is removed as
dead (its mutation SURVIVED, measured) and retired with it; `--no-ext-diff` stays, because `diff.external`
applies to every diff, and the real-git world now sets it. The world adds the directory, the `-diff`
attribute, a NUL-byte gate and a deleted gate. 180 cases; mutations 59 -> 62 (three retired with their
subjects, six added), 62/62. Replay 8 of 40 — after correcting my own replay, which substituted `...HEAD`
but not a bare `HEAD` and so diffed one PR against this branch's tree (it read 9).

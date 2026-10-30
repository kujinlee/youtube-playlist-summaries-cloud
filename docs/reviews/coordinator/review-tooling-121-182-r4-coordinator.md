# Round 4 — `review-tooling-121-182` (PR #439, now backlog #121 only) — coordinator — NOT CONVERGED (Codex); the route moves to DEFER, the last rung

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 4
fixes_nontrivial: true
subject: review-tooling-121-182
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: out-path, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: out-write, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: out-write, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
```

Codex reviewed `e4202acd`. **The split held:** the #182 files equal master, #182 is honestly reopened, and the recorded head equals the tree Codex ran in. But three older ways to write into a filed review remain, none of them caused by the split:
- **X1:** a case or NFD spelling of a review tree that doesn't exist yet;
- **X2:** a hard link from the scratch `--out` to a filed review;
- **X3:** a symlink at `--out` created while the review runs.

X4: device identity is untested, and an inode-only mutant survives.

**Thrashing or prose floor?** (Round 4 obliges the question.) Neither. The gap-reader thrashing ended with the split, and nothing in this round is fix-induced except one test gap. These are pre-existing defects in one component, `--out` handling, that a sharper reviewer found once the noise was gone.

**DEFER: one structural fold, then a final-tree round, then stop.**
- X2 and X3: the capture is written to an exclusively created temporary file in the target directory, then atomically renamed, so no existing directory entry, link or late symlink is ever followed.
- X1: refuse any `--out` whose NEAREST EXISTING ancestor is, by identity, inside either tree. Scratch output always lives outside the repository, so this needs no spelling comparison at all.
- X4: a cross-device negative fixture.

Anything a final-tree round finds beyond those is filed, not folded.

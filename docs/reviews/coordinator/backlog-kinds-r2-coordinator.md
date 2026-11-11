# Round 2 — `backlog-kinds` (PR #442, backlog #394, backlog #395) — coordinator — NOT CONVERGED (Codex); the route moves to REDESIGN

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: backlog-kinds
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: namespace-exemption, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: kinds, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: kinds, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: false, component: namespace-exemption, disposition: fixed}
```

Codex reviewed `1cb9710a`, the r1 fold and the master merge. **The merge verified byte-for-byte:** every marker stripped equals origin/master, apart from rows #394 and #395.

**What it found:**
- **X1:** a deleted file whose CONTENT contains `-- a/docs/backlog.md` renders as `--- a/docs/backlog.md` in the diff. The exemption's diff parser takes it for a header and credits the next deleted row to the backlog, so new prose from an out-of-scope file passes. Reproduced with real git.
- **X2:** row #22 documents a false claim and a live wrong result, so it is a defect, not a task.
- **X3:** row #2 awaits a product decision, so it is a task with NEEDS-OWNER, not a story.
- **X4:** the same-file case only ever uses identical paths, so a rename mutant survives.

**X1 is the wall:** a rule that infers structure from text the input controls. The round-1 fold changed WHICH header it trusted, not WHETHER to trust headers. **The redesign reads no diff text for the removed side:**
- A changed line is exempt only when its text, marker stripped, appears VERBATIM in the BASE version of the SAME path (`git show <base>:<path>`, compared as lines).
- A path absent at the base (a new file, or a rename target) exempts nothing.
- Added lines still come from git's per-file diff, which cannot be impersonated across files when it is run per path.

X2–X4 are folded as named.

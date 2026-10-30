# Round 5 — `review-tooling-121-182` (PR #439, backlog #121) — coordinator — the FINAL-TREE round; DEFER closes the unit, and its findings are filed

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 5
fixes_nontrivial: false
subject: review-tooling-121-182
halves:
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  claude: ran
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: out-write, disposition: filed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: filed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: out-write, disposition: filed}
```

The Claude half reviewed `60dc0b14`, the DEFER fold.

**What holds:**
- every round-4 input (a case or NFD spelling of a missing tree, a hard link, a late symlink AT `--out`) is refused or replaced, not written through;
- five ordinary scratch shapes, including `/tmp` and `/var/folders`, are not refused;
- 203/203 cases, 66/66 mutations.

**What it found:**
- **F1:** a symlink swapped into a PARENT directory of `--out` during the run still writes into a filed review. The fix is to pin the parent's directory descriptor after the location check, then create and rename through it; the reviewer verified it in a scratch copy.
- **F2:** a docstring still cites the deleted spelling rule.
- **F3:** if the capture write raises, a paid review ends in a traceback with no verdict.

Under DEFER, the ladder's last rung, these are FILED as backlog #400, not folded. The unit closes at round 5. The decision log records the termination.

# Round 4 — `boundary-compaction-440` — coordinator — CONVERGED (Codex half); one Low filed, not folded

The Codex half reviewed `206fb0bd`, the fold of round 3 on PR #463 (backlog #440, the PreCompact boundary hook).
It named no Q4c BLOCKER and no new defect in the r3 fold.

REVIEW GAP: claude — alternation (round cap: both halves in r1, then one half per round; review-method section 0 Q4c).
Round 4 is BLOCKER-only, and the Codex half found none.

```yaml
round: 4
fixes_nontrivial: false
subject: boundary-compaction-440
halves:
  codex: ran
  claude: gap-alternation
findings:
  - {id: R4-1, severity: Low, aim: deliverable, fix_induced: false, component: summary, disposition: filed}
```

## Dispositions

| # | Finding | Disposition |
|---|---|---|
| R4-1 | `--summary` counts a `ceiling_by: no-headroom` row as "ceiling forced", though the documentation says those rows are excluded. Predates r3 | **FILED**, not folded (Q4c: a Low in a BLOCKER-only round). The fix is to filter numerator and denominator on `ceiling_by`; no second aggregation exists. Filed as backlog #447 in this PR |

## Owner's merge condition: live dry-run, MET

The owner required a live dry-run before merge. Evidence: `dryrun-463.md` in the coordinator scratchpad (head `206fb0bd`).
⚠ This is the REAL `compaction-boundary.sh` and `check-compaction-boundary.py` (byte-identical copies of the worktree)
run on REAL transcripts and real settings resolution. It is NOT a harness-initiated compaction, which cannot be
triggered on demand. Only `precompact-snapshot.sh` was a stub (it appends to a counter). The main checkout was untouched.
Transcripts: copies of the live coordinator session (134 MB) and an Oct 28 session.

| Case | Input | Decision | Verdict | ctx | W | Ceiling | Snapshots | Secs |
|---|---|---|---|---|---|---|---|---|
| A baseline | live transcript, W from settings | BLOCK (deferred) | block-agent | 173604 | 300000 | 450000 | 0 | 0.55 |
| B idle | Oct 28 transcript, idle 331684 s | ALLOW | allow-idle | 84849 | 300000 | 450000 | 1 | 0.15 |
| C over ceiling | live, env W=100000 | ALLOW | allow-ceiling | 173604 | 100000 | 150000 | 1 | 0.33 |
| D unreadable | settings chmod 000 | ALLOW | allow-cannot-run (PermissionError logged) | - | - | - | 1 | 0.26 |
| D2 unparseable | HOME settings = "not json" | ALLOW | allow-cannot-run (does not parse) | - | - | - | 1 | 0.26 |
| E manual | trigger=manual | ALLOW | allow-manual | - | - | - | 1 | 0.14 |

All runs exit 0; slowest 0.55 s against the 20 s hook timeout. A blocked because the live session had open agents
(expected); no snapshot was taken. Each run wrote one JSON log line whose `verdict` matches the table.

## Codex half's own verification (foreground)

Self-test 83/83. Unchanged wrapper copies with counting snapshot stubs: the blocked auto call took zero snapshots;
ceiling allows, malformed payload/transcript/settings, and directory-at-log failures each took exactly one snapshot and
exited 0. Ceiling probes allowed at 180k/200k and 900k/1M, and at the 200k, 950k and 1M no-headroom configurations.
The manual matcher is identical to the pre-PR version. ⚠ A snapshot exit of 7 allowed compaction with one invocation but
discarded its stderr: the evidence supports one ATTEMPT, not a guaranteed capture. No data-loss reproduction.

## Next

Convergence reached under the cap. Record, mark ready, wait for CI, then merge if `check-merge-ready.py` says READY.

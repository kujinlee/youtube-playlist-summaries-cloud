# Round 5 — `idle-stop-guard` — coordinator — ✅ CONVERGED (Claude half) — every finding FILED

Claude (Opus, `docs/reviews/claude/idle-stop-guard-r5-claude.md`) reviewed `70e9188f`: CONVERGED, no BLOCKER.
Self-test 61/61 quoted. No wedge (worst path 3.10 s against the 10 s timeout); no live task refused (the binary
filters `background_tasks` to running/pending, matching `LIVE`); no dead path left from signal (b).

REVIEW GAP: codex — alternation (rounds 2+ run one half; Codex reviewed round 4).

```yaml
round: 5
fixes_nontrivial: false
subject: idle-stop-guard
halves:
  codex: skipped
  claude: ran
findings:
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: background-tasks-signal, disposition: filed}
  - {id: F2, severity: Major, aim: deliverable, fix_induced: false, component: background-tasks-signal, disposition: filed}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: false, component: payload-read, disposition: filed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: docstring, disposition: filed}
```

## Dispositions — round cap: from round 4 every non-BLOCKER is FILED

| Finding | Backlog | Why filed, not fixed |
|---|---|---|
| F1 an idle in-process teammate may read `running` | backlog #668 | Read from the binary, not captured; it OVER-allows in a window (no worse than no guard), never blocks. The capture is the first step. F4 (the docstring bound) rides with it. |
| F2 a background server counts as running work | backlog #669 | Over-allows; the fix needs a rule for which tasks count, a design choice. |
| F3 a payload over 1 MiB is NOT CHECKED | backlog #670 | Not realistic for one message; a docstring fix. |

**Why F1 is not a BLOCKER.** The r5 brief's BLOCKER (1) is an idle announcement that exits 0 *with nothing
running*. In F1 the harness itself reports a task as running; the guard reads it correctly, and the error, if
measured, is the harness's status. Merging strictly improves on today (no guard at all); #668 tightens it.

Converged at round 5. Next: PR, CI, `check-merge-ready.py`, merge on READY.

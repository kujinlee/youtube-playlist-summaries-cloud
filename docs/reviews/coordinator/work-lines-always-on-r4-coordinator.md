# Round 4 — `work-lines-always-on` — coordinator — ✅ CONVERGED (no findings)

```yaml
round: 4
fixes_nontrivial: false
subject: work-lines-always-on
halves:
  codex: ran
  claude: "GAP: alternation — the r3 fold was written by the coordinator (Claude), so r4 is the Codex half"
findings: []
```

REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology step 4 and condition 5 of `process-checklists.md` -> *Who writes a review fold* (PR #385): the round-3 fold was written by the coordinator, which is the Claude side, so round 4 goes to Codex. Not a failure to run.

## ✅ CONVERGED on `7b2d3dee`

Codex verified rather than accepted: the new mutation fails ONLY the case it names (65/66); the
partial-clear raise comes from the mandatory `STATE.unlink`, not from recording or setup; and the
same input raises the same `PermissionError` on `3a2795d1^`, `3a2795d1` and `7b2d3dee` — the
pre-feature behaviour is preserved. All 37 anchors in the manifest are distinct and resolve.

**What follows is documentation only.** This is the first fold made under the PR #385 rule: the
declaration preceded the round, every anchor was re-resolved, and the round went to Codex.

# Round 2 — `work-lines-backfill` — coordinator — ❌ NOT CONVERGED (3 Blocking)

```yaml
round: 2
fixes_nontrivial: true
subject: work-lines-backfill
halves:
  codex: ran
  claude: "GAP: alternation — the r1 fold was written by a Claude implementer subagent, so r2 is the Codex half"
findings: [stale-output-checkpoint, hidden-subprocess-arm, opaque-write-after-arm]
```

REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology step 4: the round-1 fold was written by a Claude implementer subagent, so round 2 goes to the half that did not author it. Not a failure to run.

## The coordinator's call: stop patching shapes, switch to an ALLOW-LIST

Two of the three Blocking findings were introduced by the round-1 fold (checkpoint provenance; opaque
write ordered after the arm), and the third (an arm hidden inside a subprocess) is a class no shape
parser can close. Shell commands are an unbounded SURFACE — review keeps finding the next shape. So
the fold is structural, not another patch: state survives only commands made entirely of RECOGNISED
operations; any command that executes other code or redirects makes that checkout UNKNOWN and every
plan armed while unknown gets no marker; checkpoints come only from the tools' own state lines.
Coverage is traded for safety, consistent with the owner's standing rule that a wrong link is worse
than none. Not thrashing yet (round 1 was the first review), but this is the escalation from patching
to redesign the round topology calls for when a component's fixes keep generating findings.

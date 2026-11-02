# Round 3 — `agent-long-call-guard` (PR #468, backlog #455) — coordinator — CONVERGED (Claude); one Low filed

```yaml
round: 3
fixes_nontrivial: false
subject: agent-long-call-guard
halves:
  codex: skipped
  claude: ran
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: stdin-reading, disposition: filed}
  - {id: I1, severity: Info, aim: deliverable, fix_induced: false, component: timeout-reading, disposition: no-action}
```

REVIEW GAP: codex — alternation. Round 3 runs ONE half; this round it is Claude (`review-method.md` → *Round topology*).

Claude reviewed head `3a695139`: **CONVERGED**. It re-read the Claude Code 2.1.309 binary independently of round 2 and
found no defect introduced by the round-2 fold. The self-test passes 43/43, the scoped mutation sweep kills 36 of 36
with 0 survivors, and `check-selftest-counts.py --changed` returns RC 0.

## Per finding

- **F1 (Low, filed)** — `sys.stdin.read()` sits outside the `try`, so non-UTF-8 stdin prints a `UnicodeDecodeError`
  traceback at exit 1 instead of `NOT CHECKED`. Not fix-induced, non-blocking, and Claude Code cannot send the input.
  Round 3 is the last round that folds non-BLOCKERs, but a Low with no live trigger is filed rather than folded:
  backlog row 463. No script changed.
- **I1 (Info, no action)** — under `CLAUDE_CODE_SIMPLE=1` a `run_in_background` call with a 600000 timeout runs in the
  foreground and the hook allows it. Moot: bare mode never fires settings-file hooks, and this hook is registered in
  `.claude/settings.json`.

## Evidence

Verdict file: `docs/reviews/verdicts/agent-long-call-guard-r3-claude.verdict.json` (CONVERGED, head `3a695139`).

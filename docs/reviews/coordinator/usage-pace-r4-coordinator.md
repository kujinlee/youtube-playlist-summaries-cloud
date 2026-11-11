# Round 4 — `usage-pace` (PR #446, backlog #399) — coordinator — NOT CONVERGED (Codex); the route moves to DEFER, the last rung

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 4
fixes_nontrivial: true
subject: usage-pace
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: payload-read, disposition: fixed}
  - {id: X2, severity: Medium, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: true, component: scope, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
```

Codex reviewed `81673a89`: the round-3 fold first, then both merge commits.

**What held:**
- no valid free-text wake gets through the control-message allowance;
- the main session cannot spawn or wake at 90% or more;
- no cache input silences a valid weekly REFUSE;
- the merge regressed nothing.

**What it found:**
- **X1:** stdin itself has no deadline. A producer that keeps the pipe open holds the hook process alive beyond the deadline. That is not normal harness behaviour, but it refutes the bet's "no hook process outlives its deadline".
- **X2 (fix-induced):** the payload-size check's test bypasses real stdin, so `read(MAX+1) → read(MAX)` survives.
- **X3 (fix-induced):** a schema-invalid control `type` (a list or an object) crashes the lookup and exits 1, which allows the call.
- **X4:** a "missing cache" case passes for an ambient reason.

**DEFER, terminal: one fold, then a final-tree round, then stop.**
- Payload collection is bounded by the same deadline; on timeout, a REFUSE verdict is kept.
- The control-message discriminator must be a STRING before any lookup.
- The size and stdin cases run through a real child process.
- The missing-cache case asserts its precondition and its reason.

Commit `91e4b490`, which states the teammate-report bound, lands with this fold and is seen by the final round. Anything the final round finds is filed.

# Round 2 — `guards-cannot-run` (PR #440) — coordinator — NOT CONVERGED (Codex); the route moves to REDESIGN

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: guards-cannot-run
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: transcript-read, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: payload-path, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: ci-watched, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: false, component: transcript-read, disposition: fixed}
```

Codex reviewed `0a2264de`, the fold first.
- **X1 (fix-induced):** r1's m2, "skip an undecodable line", lets a corrupt record pass QUIET, and the registered Stop hook returns 0.
- **X2:** 200,000-deep JSON escapes as a `RecursionError` traceback.
- **X3:** an EMPTY status string still reads as "CI running".
- **X4:** a FIFO `transcript_path` hangs the Stop hook until the external timeout.

Codex also confirmed what holds. Across 50 real transcripts and 15 real check rows, no branch/master difference. Every r1 input is refused. An all-undecodable transcript stays rc 2.

**The round-1 bet is lost.** Each guard still checks a different subset of the ways input can be bad, and each fold added the next check. So the next rung is a REDESIGN. ONE bounded reader for untrusted input, shared by all five guards, with a closed set of outcomes. It does three things:
- reads only a REGULAR file or stdin, under a byte bound (X4);
- parses with every exception mapped to CANNOT RUN, including `RecursionError` (X2);
- tolerates ONLY a torn FINAL record, so any other undecodable record is CANNOT RUN (X1 reverts m2's breadth).

ci-watched requires a NON-EMPTY known status (X3).

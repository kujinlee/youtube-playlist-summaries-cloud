# Round 3 — `guards-cannot-run` (PR #440) — coordinator — NOT CONVERGED (Claude); the route moves to SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: guards-cannot-run
halves:
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  claude: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: payload-path, disposition: filed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: false, component: transcript-read, disposition: filed}
  - {id: C3, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
  - {id: C4, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: hook-path, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: filed}
```

The Claude half reviewed `c3f820bc`, the shared-reader redesign. **The reader holds everywhere the reviewer could reach it.**

**The two Majors are both older than this PR and lie one field over:**
- **C1:** the payload's `session_id` names a PATH that is read OUTSIDE `bounded_read`, so a FIFO there hangs the Stop hook, and deep JSON or a NUL byte gives a traceback.
- **C2:** a transcript record whose `message` is not an object is skipped mid-transcript, which flips WARN to QUIET.

**The Minors:**
- **C3 (fix-induced):** three survivors on the stdin bound's values and exact-cap edge.
- **C4 (fix-induced):** the guard-level FIFO cases pass for an ambient reason.
- **C5:** the registered hook's own `INPUT=$(cat)` is unbounded.
- **C6:** the three older readers are a duplicate rule mentioned only in prose.

**The redesign's bet is lost, so the route is SPLIT.** This PR ships the shared reader, which holds. C1 and C2 predate it and widen its scope, to every path the payload names and to non-object records, so they are FILED as backlog #409 with C6. The fold takes C3–C5. A final round follows.

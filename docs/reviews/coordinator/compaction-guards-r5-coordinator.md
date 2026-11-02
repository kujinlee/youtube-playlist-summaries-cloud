# Round 5 — `compaction-guards` — coordinator — one stale sentence; DEFER is terminal → STOPPED

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 5
fixes_nontrivial: false
subject: compaction-guards
halves:
  codex: ran
  claude: gap
findings:
  - {id: X5-1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Codex on `fdf15b69`: **no timeout, nonce or owner-provenance failure reproduced.** 512 MiB stdin returns in 0.13 s from
both hooks; held-open stdin with a signal-ignoring capture returns at 13.3 s; a signal-ignoring child is killed at the
real 11.0 s timeout; FIFO, symlink and oversized artifacts are refused in under 0.4 s; a mismatched nonce shows no
snapshot; the print stays at 9,760 characters; the live SessionStart with an escaped holder returns at 31.2 s against its
60 s registration; the real transcript pairs all 45 answers in 0.49 s. 96/96, 68/68; all 94 kept mutations at their
named cases; 2,430 real.

**X5-1** `run_capture`'s docstring still said *"nothing it started survives — except a process that called `setsid`"*,
the guarantee round 4 withdrew. It now states the bound: a descendant that leaves the group by `setsid` or `setpgid`
is not killed; what is bounded is the HOOK's return. No mutation anchor binds that line (0 across every manifest).

**STOPPED.** Defer is terminal on the ladder, and the only finding is one sentence whose fix is certain, so no further
round is owed. Stated bounds, all written in CLAUDE.md, the docstrings, the backlog #361 row and the PR body: owner words
are RECORDED, not proven; session identity is not compaction identity; a descendant that leaves its process group is
not killed. The deferred audit is backlog #391.

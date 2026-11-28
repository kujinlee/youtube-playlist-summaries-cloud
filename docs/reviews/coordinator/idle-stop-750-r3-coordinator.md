# Round 3 — `idle-stop-750` (PR #652, backlog #750 step 1) — coordinator — CONVERGED (Claude); two NITs folded (backlog #751)

The Claude half reviewed `5677ff59` (the round-2 fold: `_open_log` with a non-blocking bounded lock, the path re-check
after locking, and the old lock held until the new file is locked). It could not show the decision log changing the
hook's verdict, exit code or timing on the real `--hook` path. Its own measurements: self-test 77/77; `--only` mutation
run 79/79 killed, each by its named case; a stress run of 16 processes × 4800 writes with 161 forced rotations lost and
duplicated nothing, with the slowest write at 0.27 s; worst-case log time ≈ `LOG_WAIT_S` (0.5 s), well inside the 10 s
hook timeout.

Both NITs were folded in r3 (backlog #751): `log_decision` builds the line inside its `try`, which now catches any
`Exception`, and a short `os.write` is truncated back off and raised as `OSError`, so no torn line is left. Two new
self-test cases (79 total) and four new mutations (83 total) guard the fold. Round 4 (Codex, alternation) reviews it.

| id | sev | fix_induced | finding | disposition |
|---|---|---|---|---|
| Y1 | Low | false | a non-OSError/ValueError from building the line escapes (`:321`, `:335`); unreachable on the real `--hook` path today | fixed (folded r3; backlog #751) |
| Y2 | Low | false | `os.write`'s byte count unchecked (`:334`): a torn line on a near-full disk; no verdict effect | fixed (folded r3; backlog #751) |

**Y2 is NOT fix-induced** — corrected before merge from a first draft that said `true`. Thrashing means a finding *introduced by the previous round's own fix* (`docs/review-method.md` → the thrashing row). The unchecked `os.write` entered with the ROUND-1 fold (`git show eafd6671:scripts/check-idle-stop.py`, the `os.write(fd, ...)` line); round 2 reviewed that tree and did not report it, and the round-2 fold (`5677ff59`) did not change that line. It is a miss carried from an earlier round, not a defect the round-2 fix caused. The Claude review never labelled it fix-induced; the label was the coordinator's.

REVIEW GAP: codex — alternation (round 3 is the Claude half's turn).

```yaml
round: 3
fixes_nontrivial: false
subject: idle-stop-750
halves:
  codex: gap
  claude: ran
findings:
  - {id: Y1, severity: Low, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: Y2, severity: Low, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
```

Review: `docs/reviews/claude/idle-stop-750-r3-claude.md`.

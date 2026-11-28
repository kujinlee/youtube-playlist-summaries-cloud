# Round 2 — `explainer-port-631` (PR #651, backlog #631) — coordinator — NOT CONVERGED (Codex); all folded

Codex reviewed the round-1 fold `9b42334e`. Every finding was caused by that fold. This is the first fix-induced round, so Phase 6 is not armed: if round 3's findings are also fix-induced in `explainer-serve`, it is.

| id | sev | finding | disposition |
|---|---|---|---|
| Y1 | BLOCKER | `argv_runs_script` (`scripts/explainer-serve.py:1526`) accepts the script's path in ANY position of argv, so a foreign Python server given the path as an extra argument is "ours, older code" and `--stop` kills it (reproduced by Codex). The self-test's legacy stand-in passes the path as an extra argument, so its positive control endorses the false positive. Confirmed by the coordinator reading the code. | fold: the script must be the PROGRAM the interpreter runs. argv[0] is a Python interpreter; skip its option flags (including the ones that consume a value); `-c` or `-m` means not ours; the next element must resolve to the script. The stand-in must run the way a real server runs |
| Y2 | MAJOR | the legacy `.serve.pid` is read only on 7391, but master writes it on every port, so a pre-branch server on another port cannot be stopped | fold: read the legacy pidfile on any port; it is still accepted only through the lsof binding, which already proves that pid is the listener on THIS port |
| Y3 | MAJOR | the identity record is written after the fork with no cleanup, so a failed write leaves a running child that cannot be managed | fold: see Y4 |
| Y4 | MAJOR | concurrent starts both write records before either binds, so the loser can overwrite the winner's token | fold: the parent generates the token and passes it to the child. Only the CHILD writes the records, after its bind succeeds, atomically (write a temp file, then rename). A child whose write fails closes the socket and exits, and the parent's token wait then fails with rc 1. A loser that fails to bind writes nothing |

```yaml
round: 2
fixes_nontrivial: true
subject: explainer-port-631
halves:
  codex: ran
  claude: gap
findings:
  - {id: Y1, severity: BLOCKER, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: fixed}
  - {id: Y2, severity: MAJOR, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: fixed}
  - {id: Y3, severity: MAJOR, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: fixed}
  - {id: Y4, severity: MAJOR, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 is Codex's).

Review: `docs/reviews/codex/explainer-port-631-r2-codex.md`.

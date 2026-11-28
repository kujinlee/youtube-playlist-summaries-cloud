# Round 1 — `explainer-port-631` (PR #651, backlog #631) — coordinator — both NOT CONVERGED; all folded

Both halves reviewed `380689fb`. Their findings fall into one class: the server's identity is CLAIMED by whatever answers on the port, and is never BOUND to the process that holds the port or to the pidfile that started it.

| id | from | sev | finding | disposition |
|---|---|---|---|---|
| X1 | codex B1 | BLOCKER | `pid_is_ours` accepts a marked answer whose pid matches, whatever its root, so a forged or sibling answer licenses a SIGTERM to an unrelated pid | fold: per-start random token in the pidfile, echoed by `/__whoami` |
| X2 | codex B2 + claude F1 | BLOCKER | the `ps` fallback is a substring test: a reused pid whose argv mentions `explainer-serve.py`, or a sibling server on another port, is signalled (reproduced by the Claude half) | fold: the fallback needs the OS to report that pid as the LISTENER on our port, and its argv to run the script, compared exactly rather than as a substring |
| X3 | codex M1 | MAJOR | after the fork, the parent counts `port_busy` as success, so a racer that binds first reads "serving", rc 0 | fold: the parent waits for `/__whoami` carrying ITS token, and otherwise returns rc 1 and reaps the child |
| X4 | codex M2 | MAJOR | a foreign listener that echoes the marker, the root and the pidfile's pid is "ours" | fold: the token (X1) |
| X5 | codex M3 + claude F3 | MAJOR/MINOR | an old server from before `/__whoami` makes start/status exit 3 and say another program holds the port | fold: legacy-ours is recognised through X2's binding. start says "already serving (older code; `--stop` then start to pick up changes)", rc 0 |
| X6 | claude F2 | MAJOR | the pidfile is keyed by root, not port: one root on two ports deletes a live server's pidfile, and neither server can then be stopped (reproduced) | fold: the pidfile is per port |
| X7 | codex m1 | MINOR | a transient identity failure, then any `ps` answer, removes the pidfile | fold: remove it only when the pid is dead |
| X8 | claude F4 | MINOR | a listener that drip-feeds a byte every 0.5 s hangs `listener_identity` without limit (reproduced at 20 s) | fold: one overall deadline |
| X9 | claude F5 | MINOR | two safety branches survive mutation (the pid compare; keep the pidfile when ps cannot say) | fold: a case and a mutation for each |
| X10 | claude F6 | NIT | a local process of the same user can impersonate `/__whoami` | fold: state the limit in the docstring |

```yaml
round: 1
fixes_nontrivial: true
subject: explainer-port-631
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: BLOCKER, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X2, severity: BLOCKER, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X3, severity: MAJOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X4, severity: MAJOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X5, severity: MAJOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X6, severity: MAJOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X7, severity: MINOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X8, severity: MINOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X9, severity: MINOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: X10, severity: NIT, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
```

Reviews: `docs/reviews/codex/explainer-port-631-r1-codex.md`, `docs/reviews/claude/explainer-port-631-r1-claude.md`.

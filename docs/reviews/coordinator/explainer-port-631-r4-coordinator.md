# Round 4 — `explainer-port-631` (PR #651, backlog #631) — coordinator — NOT CONVERGED (Codex); B1 fixed, the rest filed (owner decision)

Codex reviewed the Phase 6 redesign `2ff681f1` (token-only identity). The review's pre-committed stop condition was "a
BLOCKER in `classify_listener`, `read_identity` or `stop`", and B1 met it. That made this an owner decision, not a fifth
fold. **The owner, 2026-11-27 14:53, chose A:** fix B1 in this PR and merge; file B2, B3, the MAJOR and the MINOR as ONE
row whose design is that the server stops itself on a signed request and the script never sends a signal. That row is
backlog #748, first in the explain-plugin wave, before publishing.

None of the five findings was introduced by the redesign (`fix_induced: false` for B1–B3 and the MAJOR). The MINOR is in
the delivery doc's exit-1 text, so it does not count toward thrashing in `explainer-serve`.

| id | sev | fix_induced | finding | disposition |
|---|---|---|---|---|
| B1 | BLOCKER | false | `stop()` proves the pid `listener_verdict()` reads from a SECOND record read, then signals the pid from the FIRST; a restart between the reads sends SIGTERM to the old pid (reproduced by Codex with controlled reads) | fixed: `stop()` signals only when the token-proven answer's pid equals the pid it signals; otherwise exit 3. Two cases (mismatch: exit 3 and nothing signalled; match: signalled) and one mutation |
| B2 | BLOCKER | false | `/__whoami` gives the token to any local client, so a replayer can impersonate after the server exits | deferred: backlog #748 |
| B3 | BLOCKER | false | a token-proven pid can exit and be reused before `os.kill` | deferred: backlog #748 |
| M1 | MAJOR | false | the self-test cleanup SIGKILLs a listener on a released ephemeral port identified by `lsof` alone | deferred: backlog #748 |
| m1 | MINOR | true | delivery doc §4 overstates what an exit-1 FAIL line says | deferred: backlog #748 |

REVIEW GAP: claude — alternation (round 4 is Codex's).

```yaml
round: 4
fixes_nontrivial: false
subject: explainer-port-631
halves:
  codex: ran
  claude: gap
findings:
  - {id: B1, severity: BLOCKER, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: fixed}
  - {id: B2, severity: BLOCKER, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: deferred}
  - {id: B3, severity: BLOCKER, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: deferred}
  - {id: M1, severity: MAJOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: deferred}
  - {id: m1, severity: MINOR, aim: deliverable, fix_induced: true, component: explainer-delivery, disposition: deferred}
```

Review: `docs/reviews/codex/explainer-port-631-r4-codex.md`.

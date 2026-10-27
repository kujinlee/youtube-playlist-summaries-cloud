# Round 3 — `hook-args-shell` — coordinator — ⟳ NOT CONVERGED; DEFER (SPLIT skipped, reason recorded): filed, merge on READY

```yaml
round: 3
fixes_nontrivial: false
subject: hook-args-shell
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: tests, disposition: filed}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 3 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `6abb8ff3`. **The production boundary HELD under REAL hook loads** against the installed Claude Code
2.1.309 (isolated `SessionStart` registrations writing marker files): `statusMessage: {}`, `if: 3`, `timeout: true` are
each refused by the guard and NOT run by Claude Code; `statusMessage: ""`, `if: ""`, `timeout: 1.5`/`1e100` accepted and
run; `timeout: -1`/`0` and a group `matcher: {}` pass the guard but are not run — inside the declared bound (timeout
VALUES, group matcher). Every refused and unclassified field refused; Codex's r2 mutations each fail their cases now;
42/42; 30/30 mutations real, independently re-applied.

- **XM1 (FILED, backlog #377):** "a malformed hooks block is CANNOT RUN, not a crash" — a PR #409 case, outside this
  unit — passes for an AMBIENT reason: with the non-list `raise` mutated to `continue`, zero commands remain and that also
  returns 2. The regression IS caught, by this PR's companion case beside a valid command.
- **XL1 (fixed, prose):** stale `FIELD_POLICY` names (now `ACCEPTED`/`REFUSED`); and "refused to load the whole file" —
  true of r2's interactive run, while r3's print-mode run skipped only the entry — now states both: the hook is not run.

**Route DEFER, skipping SPLIT, with the reason in the decision-log row:** no unstable half of this unit remains — the
production boundary held — and the remaining case belongs to PR #409. PR #414 merges on READY after a merge-confirmation
round. 42 cases; 30 mutations.

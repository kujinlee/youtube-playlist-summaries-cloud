# Round 3 — `agent-watchdog` — coordinator — CONVERGED (Claude half), 3 MINOR

The Claude half reviewed the round 2 fold `93c31634` (PR #596, backlog #657):
`docs/reviews/claude/agent-watchdog-r3-claude.md`. CONVERGED: no BLOCKER, no MAJOR, 3 MINOR.

REVIEW GAP: codex — alternation

```yaml
round: 3
fixes_nontrivial: false
subject: agent-watchdog
halves:
  codex: gap
  claude: ran
findings:
  - {id: R3m1, severity: Minor, aim: deliverable, fix_induced: true, component: quiet-window, disposition: fixed}
  - {id: R3m2, severity: Minor, aim: deliverable, fix_induced: false, component: quiet-window, disposition: fixed}
  - {id: R3m3, severity: Minor, aim: deliverable, fix_induced: false, component: report, disposition: fixed}
```

- **R3m1 (fix_induced: true).** The round 2 fold put the entry NAME into the fingerprint but pinned only size and
  time with mutations; dropping the name survives 73/73. Recorded as fix-induced because the reviewer says so and the
  name field is the fold's own code. ⚠ It is a missing witness, not a behaviour defect — whether it completes the
  two-round arming condition: `check-review-decision.py` answered `CANNOT RUN — … severity='Major', not one of
  ['Blocking', 'High', 'Low', 'Medium']` (this subject's round docs use Major/Minor), so it decided nothing. Read
  against the definition in `dev-process.md` (two consecutive rounds with findings caused by the previous round's
  fix, in one component: R2M1/R2M2 then R3m1, all `quiet-window`), **the condition is MET. A Phase 6 architecture
  review of `quiet-window` runs (Fable) before the fold**; a retreat I author for myself is not a gate.
- **R3m2.** Nothing pins `os.lstat` in the walk; a symlink loop would make the `os.stat` mutant CANNOT RUN.
- **R3m3.** The printed re-arm command does not quote paths; a path with a space splits. Loud, not silent.

All three are cheap and are fixed in the round 3 fold (cases first, then `shlex.quote`), after the Phase 6 review.

## Fold

The Phase 6 review (`docs/reviews/architecture-review-2026-11-16-agent-watchdog.md`) found the fingerprint right in
kind and recommended (b), a small restructure inside this fold. **Adopted.** The entry is a three-field
`Entry(NamedTuple)` of `name, mtime_ns, size`; the r2 `kind` field is gone, since no input can change it alone.
Because this fold changes code, `fixes_nontrivial: false` above describes the round as reviewed, not the fold; round
4 is under the round cap, so its findings are FILED unless a BLOCKER, and a third fix-induced `quiet-window` finding
would mean the Phase 6 review misjudged the cause.

| id | disposition | what the fold did |
|---|---|---|
| R3m1 | fixed (as its class) | one class case over an independent literal `FIELDS`: asserts `Entry._fields == FIELDS`, then one world change per field (name, time, size) plus an identity row, each with a control that only that field changed. Mutations: the name left out, a tree name its basename only, its directory only, a clock mixed into the fingerprint, a fourth field with no witness. The git-name-constant mutant is NOT mutated, its reason in the pin comment |
| R3m2 | fixed | a case: a looping and a dangling symlink are observed without CANNOT RUN and are each an entry; a symlink to a directory is not, and BOUNDS now says so. Mutation: `os.stat` for the walk's `os.lstat` |
| R3m3 | fixed | `shlex.quote` on each re-arm spec; a case splits the printed command as a shell does and gets back the same watch for a path with a space and a quote. Mutation: the quote removed |

Re-anchored, same intent: HEAD left out, size and time left out, only the newest time compared (`e.mtime_ns`, was
`e[2]`), the re-arm listing the quiet. Pin 63 -> 70. Filed from the Phase 6 review: backlog #660 (a directory that
becomes a file mid-walk is a false CANNOT RUN) and backlog #661 (`check-review-decision.py` refuses Major/Minor
severities, so it decided nothing for this subject; not covered by backlog #117).

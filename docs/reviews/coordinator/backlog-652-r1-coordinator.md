# Round 1 — `backlog-652` — coordinator — NOT CONVERGED (both halves), one fold

Both halves reviewed `a2da36a2` (`git diff 4ef6dfea a2da36a2`). Both ran the falsifier end to end and it holds: an entry declared `--until 11-06` reads `wait date passed 11-06, not started` on 11-15. The pins match their manifests (goal-tree 545, session-state 167), and every anchor resolves once.

Findings, de-duplicated:
- **F1 (High; Codex MAJOR + Claude MAJOR).** The year of an `until` is guessed at READ time, from a yearless `since`. A passed wait turns live again a year later (Codex). `--set-until` keeps the old `at`, so a December date set in November can read as last December's and alarm early (Claude).
  - **Fix:** settle the year once, at WRITE time. `--add --until` and `--set-until` store a full `YYYY-MM-DD`: the first occurrence of the `mm-dd` on or after the day it is written (Feb 29 goes to the next leap year). The reader accepts only the full form and shows `mm-dd`. A malformed or yearless stored value reads as `until <value> (date not read)`. No ledger entry carries `until` yet, so there is nothing to migrate.
- **F2 (Medium; Codex MINOR + Claude MINOR).** `02-29` can resolve to no date, which leaves a live wait that never alarms. Closed by F1's write-time rule.
- **F3 (Medium; Claude NIT).** A wait declared more than about six months ahead reads as already passed. Closed by F1: the declared date is always on or after the write day.
- **F4 (High; Codex MAJOR).** A passed date retires waits by TEXT after aggregation, so a second entry on the same item with the same wait text loses its live wait.
  - **Fix:** retire by entry (id), not by text. Add a case with two entries waiting on the same text, only one of them passed.
- **F5 (Medium; Codex MAJOR + Claude MINOR).** `--print` shows the expired wait as live (`waits on …`) with no alarm.
  - **Fix:** the `--print` leaf for a passed entry reads `wait date passed <mm-dd>, not started`, not the wait text. Add a case.

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-652
halves:
  codex: ran
  claude: ran
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: goal-tree dated wait, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree dated wait, disposition: fixed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree dated wait, disposition: fixed}
  - {id: F4, severity: High, aim: deliverable, fix_induced: false, component: goal-tree dated wait, disposition: fixed}
  - {id: F5, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree dated wait, disposition: fixed}
```

Reviews: `docs/reviews/codex/backlog-652-r1-codex.md`, `docs/reviews/claude/backlog-652-r1-claude.md`.

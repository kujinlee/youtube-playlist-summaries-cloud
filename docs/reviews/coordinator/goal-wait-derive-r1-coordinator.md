# Round 1 — `goal-wait-derive` (backlog #650, PR #592) — coordinator — ⟳ NOT CONVERGED (both halves); every finding FIXED

```yaml
round: 1
fixes_nontrivial: true
subject: goal-wait-derive
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: blocker-state, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: false, component: session-block, disposition: fixed}
  - {id: C3, severity: High, aim: deliverable, fix_induced: false, component: idle-days, disposition: fixed}
  - {id: C4, severity: High, aim: deliverable, fix_induced: false, component: prerequisite-matcher, disposition: fixed}
  - {id: C5, severity: High, aim: deliverable, fix_induced: false, component: idle-rule, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: session-block, disposition: fixed}
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: wait-resolution, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: blocker-state, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: idle-days, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: idle-days, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: session-block, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: hook, disposition: fixed}
  - {id: F7, severity: Low, aim: deliverable, fix_induced: false, component: session-block, disposition: fixed}
```

Reviews: [`codex/goal-wait-derive-r1-codex.md`](../codex/goal-wait-derive-r1-codex.md) (C1–C6, on `7154c97a`'s parent tree,
524/524) and [`claude/goal-wait-derive-r1-claude.md`](../claude/goal-wait-derive-r1-claude.md) (F1–F7). Folded test-first:
every new case below was run RED against the unfixed code (14 `[FAIL]` and a `NameError`) before the fix. Suite
524 → 537, all green.

| Finding | Disposition | Guarding case (`scripts/goal-tree.py --self-test`) |
|---|---|---|
| C1 + F2 — a PR closed unmerged, a superseded/withdrawn row read "blocker done" | FIXED: `_blocker` has a fourth state, `abandoned`; only a MERGED PR or a CLOSED row is done. The alarm is `prerequisite <ref> <why> — re-plan` | ⭐ r1 Codex 1 / Claude F2 (five refs, ONE case) |
| F1 — a recorded wait whose refs finished still says "waits for" | FIXED: `wait_blockers` resolves every `; `-part's refs (thread line, thread entries, placed and loose ledger entries). When every ref is done or abandoned, the alarm follows the recorded text and the item counts as idle. A wait naming no ref (`the owner`) stays a reason | ⭐ r1 Claude F1 ×2 (five waits; nine spellings, merged and open PR) |
| C5 — the block hid other waits and listed an item with a live reason | FIXED: `owed_reason` returns `(waits, alarm, idle)`. An item is listed only when idle, meaning no live recorded wait and no open or unread prerequisite. A listed line shows `waits for:` and every alarm | ⭐ r1 Codex 5 |
| C2 + F5 — a snapshot with a source not read said "none" | FIXED: any `cannot` / `needs_not_read` / `ledger_problems` gives a first line `CANNOT VERIFY — <source> not read: …; treat as NOT RUN`, bounded. The rows that were read still follow | ⭐ r1 Codex 2 / Claude F5; r1 Codex 2 (incomplete still lists) |
| C3 + F3 — DST fallback / one minute ahead read as ~364 idle days | FIXED as a RULE: of year−1, year and year+1, `idle_days` picks the year nearest `now`. A gap under one day either way is 0, and a full stamp a day or more ahead is None. **Storage not changed:** the ledger's `at` stays `mm-dd HH:MM` (session-state.py owns that format; widening it is out of this fold's scope) | ⭐ r1 Codex 3 / Claude F3 (DST, minute-after, full stamp ahead, year boundary) |
| C4 — `on_done` and negated forms were read as prerequisites | FIXED: prerequisites are read only from the thread line and the entry `what`. The matcher skips an `after` whose own clause contains a negation or ends in `until`. Its docstring lists what it rejects | ⭐ r1 Codex 4 ×2 (negated/until-after; thread and placed entry `on_done`) |
| F4 — idle days were counted to the snapshot's first-logged time | FIXED: `owed_idle_lines(snap, now)` and `owed_idle_report(path, now)`. `main --owed-idle` passes the wall clock, and tests inject it | ⭐ r1 Claude F4 ×2 (two clocks over one snapshot; through `main`) |
| C6 + F6 — error lines unbounded; CANNOT RUN printed twice | FIXED: every line goes through `_bounded`, error lines included. `--owed-idle` exits 2 exactly when it printed its own CANNOT line, and the hook echoes only for other codes (`rc` captured, never `$?` after `\|\|`) | ⭐ r1 Codex 6 / Claude F6 (failing main, missing and broken log, three hook outcomes) |
| F7 — the whole log was read for one line | FIXED: `_last_line` seeks from the end in a doubling window. A missing, empty or unreadable log stays CANNOT READ | ⭐ r1 Claude F7 (1 MB and 2 MB cost the same; a 9000-byte last line read whole) |

**Mutations:** `scripts/mutations/goal-tree.json` 417 → 435. Nineteen are new, at least one per rule above. Eight existing
entries were rebound to the new text. One was retired: after the rebind, *a closed prerequisite PR is not read as done*
had the same anchor and replacement as *a merged prerequisite PR…*, and closed is now guarded as abandoned. A
pre-existing anchor duplicate, *not read is called open* vs *open … reads as not read*, was made distinct. Every one of
the 28 new or rebound mutations was run on a temp copy outside the repo and killed by its named cases. All 5198 anchors
across `scripts/mutations/*.json` resolve exactly once.

**Live effect:** against the real log, the block now opens with `CANNOT VERIFY — ledger_problems not read`. This is
because the newest snapshot records two ledger problems (entries `fable-compare-week` and `memory-hygiene` whose
threads are not read). It exits 2, and the hook stays silent on 2. This is the r1 Codex 2 rule working as intended: before the
fold, the same snapshot read as "none".

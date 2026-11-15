# Round 2 — `goal-wait-derive` (backlog #650, PR #592) — coordinator — ⟳ NOT CONVERGED; every finding FIXED

```yaml
round: 2
fixes_nontrivial: true
subject: goal-wait-derive
halves:
  codex: skipped
  claude: ran
findings:
  - {id: N1, severity: High, aim: deliverable, fix_induced: true, component: session-block, disposition: fixed}
  - {id: N2, severity: High, aim: deliverable, fix_induced: true, component: wait-resolution, disposition: fixed}
  - {id: N3, severity: Low, aim: deliverable, fix_induced: true, component: idle-days, disposition: fixed}
  - {id: N4, severity: Low, aim: deliverable, fix_induced: true, component: prerequisite-matcher, disposition: fixed}
  - {id: N5, severity: Low, aim: deliverable, fix_induced: true, component: hook, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 2 runs one half; owner 2026-10-28).

Review: [`claude/goal-wait-derive-r2-claude.md`](../claude/goal-wait-derive-r2-claude.md) (N1–N5, on `be4d48c6`,
537/537). Folded test-first: the four new cases and the four re-pinned ones were run RED against the unfixed code
(8 `[FAIL]`, 533/541) before any fix. Suite 537 → 541, all green.

## ⚠ Every finding of this round was caused by round 1's fixes

The reviewer tagged **N2** (caused by the F1 fix) and **N3** (caused by the C3/F3 fix). The coordinator's reading is
that the other three sit in code round 1 added as well: N1 is the CANNOT VERIFY trigger added for C2/F5, N4 is the
negation filter added for C4, N5 is the exit code added for F6. All five are therefore marked `fix_induced: true`.
They are in five different components, one finding each.

**The rule for round 3:** if round 3 again reports a finding caused by this fold, in a component that carried a
fix-caused finding here, that is two consecutive rounds of fix-caused findings in one component — THRASHING, and
Phase 6 (an architecture review of that component) is owed in place of a third patch.

**Prediction, stated before round 3:** round 3 (Codex, by alternation) finds nothing caused by this fold in
`wait-resolution`, `idle-days`, `prerequisite-matcher`, `session-block` or `hook`. The likeliest place for it to
lose is `wait-resolution`: the rule for what a recorded wait names is prose-matching, and it has now been wrong in
both directions (round 1: too narrow; round 2: too broad).

## Dispositions

| Finding | Disposition | Guarding case (`scripts/goal-tree.py --self-test`) |
|---|---|---|
| N1 — a ledger placement note made the block say CANNOT VERIFY in every session | FIXED: `OWED_IDLE_UNREAD` is `cannot` and `needs_not_read` only. `ledger_problems` is out: in a logged snapshot it holds only placement notes, and a note drops no entry from the Owed list. No count of notes is appended; the goal-tree page already shows them | ⭐ r2 N1 (NEW): a snapshot built by `derive` from an entry in the real ledger's shape (thread line does not parse, placed by its goal), with a wait and without. The r1 Codex 2 / Claude F5 case and the "incomplete still lists" case are re-based on `cannot` |
| N2 — any ref inside a recorded wait was read as its prerequisite | FIXED: `wait_blockers` resolves a `; `-part in two forms only. (a) The part IS its refs: nothing but `PR #N` / `backlog #N` and the joining words `and or both then plus on for`. (b) The part says `after <ref>`: `named_prerequisites`, the one rule the `what` matcher uses, negation included. A cited ref stays a reason | ⭐ r2 N2 (NEW): eight waits in one case — the reviewer's `asked on PR #590`, the real `fable-compare-week` wait verbatim, `see PR #590`, `PR #590 and the owner`, `not after PR #590` stay reasons; `PR #590`, `after PR #590`, `queued after backlog #70 in the 11-15 budget` go stale |
| N3 — a month-day entry older than about six months read `idle ? days` | FIXED: the year is the latest one that does not put the time after `now`; a time under a day ahead is still this moment's (the r1 DST and minute-ahead rule). 02-29 is looked for back to nine years. A month-day time is now never None for being "ahead" — only a FULL stamp a day or more ahead is | ⭐ r2 N3 (NEW): 198 days, 219 days, 02-29 → 990, a full stamp ahead → None, `02-30` → None. The r1 Codex 3 / Claude F3 case is re-pinned (`11-16` a day ahead → 364, `01-02` at 12-30 → 362) and renamed, and the stale-named base case is renamed |
| N4 — the negation filter rejected real prerequisites | FIXED: `until` alone no longer negates; `:` ends a clause; `no` followed by a hyphen is not the word `no`. `not until after`, `don't wait until after`, a bare `no` are still rejected | ⭐ r2 N4 (NEW): the reviewer's four inputs read, four negated forms rejected. The r1 Codex 4 case is re-pinned (`wait until after PR #451` now names it) and renamed |
| N5 — exit 2 also means "python could not open the script" | FIXED: `OWED_IDLE_RC = 3` is the code for "I printed my own CANNOT line"; the hook stays silent on 0 and 3 only | ⭐ r1 Codex 6 / Claude F6, extended to five hook outcomes: a stand-in that exits 2 in silence and a script that does not exist each get the hook's CANNOT RUN header once. The case pins the literal 3, not the constant |

## Choices this fold made that a reviewer should check

- **N2 form (b) counts ONLY the refs in the `after` form.** `the owner's answer, after PR #442` goes stale when PR
  #442 merges, although it also names the owner. This is the same reading the `what` matcher has always had. The
  failure is loud (an alarm), not silent.
- **N2 on the real ledger:** `memory-hygiene`'s wait says `queued after backlog #511 in the 11-15 budget`. Backlog
  #511 is now read as its prerequisite; it is open, so the item stays not idle. When #511 closes the item will be
  listed as `blocker done … (backlog #511), not started`. That is intended.
- **N4's colon rule lets one negated form through:** `Do not do this: start after PR #5` now reads PR #5 as a
  prerequisite. The effect is a visible `waits for: PR #5 (open)`, never a hidden item.
- **N3 on a month-day time one day ahead:** it now reads as last year's (364 days), where round 1 said None. The
  ledger stores no year, so neither is provable; this is the reviewer's stated rule.
- **A logged snapshot keeps the `wait_blockers` it was derived with.** A snapshot logged by this branch before the
  fold can still carry a cited ref as a blocker until the next `/goal-tree` re-derives it.

## Mutations

`scripts/mutations/goal-tree.json` 435 → 446, pin updated in `scripts/mutations/expected_mutations.py`.

- **Eleven new:** a placement note read as CANNOT VERIFY; `cannot` dropped from the unread set; `needs_not_read`
  dropped; every cited ref a prerequisite; a wait that IS its refs not read; an explicit after-form in a wait not
  read; the joining words refused; a time under a day ahead read as last year's; 02-29 looked for in three years;
  the `no` of `no-op` negating; a colon not ending a clause.
- **Eight rebound.** Five only follow a renamed case or a moved anchor. Three are REPLACED in place, because this
  fold made their mutant the rule or removed their anchor: *the year is the latest not in the future* is now *the
  year is the NEAREST* (N3); *an until-after form is a prerequisite* is now *an until-after form is rejected again*
  (N4); the own-CANNOT exit code now mutates 3 → 2, where it mutated 2 → 1 (N5).
- **Not mutated:** the hook's own line (`[ "$rc" -eq 3 ]`). Every entry in this manifest edits
  `scripts/goal-tree.py`; the hook line is guarded by the five-outcome case, which runs the real hook text.
- All 19 new or rebound mutations were run on a copy outside the repository and each turned every case it names
  red. That copy held `scripts/`, `.claude/` and three docs only, so three unrelated explainer-page cases were red
  in it before any mutation (538/541); they are not counted as kills.
- All 5209 anchors across `scripts/mutations/*.json` resolve exactly once (5198 before this fold).

## Live effect

`python3 scripts/goal-tree.py --owed-idle` against the main checkout's log (snapshot of 2026-11-15 06:07, which
records two ledger placement notes and no source unread):

```
=== OWED AND IDLE: none — every Owed item has a reason (goal tree snapshot of 2026-11-15 06:07) ===
```

Exit 0. Before the fold the same snapshot gave `CANNOT VERIFY — ledger_problems not read`, exit 2. Pushed through
`owed_reason`, all four Owed items carry a live wait and no alarm; `fable-compare-week` no longer shows
`blocker done … (PR #590), not started`.

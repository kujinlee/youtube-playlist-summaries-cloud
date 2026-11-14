# Round 1 — `goal-placement` (backlog #514 c + d, PR #588) — coordinator — ⟳ NOT CONVERGED (both halves); all folded

```yaml
round: 1
fixes_nontrivial: true
subject: goal-placement
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-loosening, severity: Major, aim: deliverable, fix_induced: false, component: add-pairing, disposition: fixed}
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: waits, disposition: fixed}
  - {id: Xm2, severity: Minor, aim: deliverable, fix_induced: false, component: timeline, disposition: fixed}
  - {id: Xm3, severity: Minor, aim: harness, fix_induced: false, component: mutations, disposition: fixed}
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: waits, disposition: fixed}
  - {id: F2, severity: Major, aim: harness, fix_induced: false, component: mutations, disposition: fixed}
  - {id: F3, severity: Major, aim: harness, fix_induced: false, component: mutations, disposition: fixed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: placement, disposition: fixed}
  - {id: F5, severity: Minor, aim: deliverable, fix_induced: false, component: timeline, disposition: fixed}
  - {id: F6, severity: Minor, aim: deliverable, fix_induced: false, component: placement, disposition: fixed}
```

Halves: `docs/reviews/codex/goal-placement-r1-codex.md` (committed as written in `d6e4ecbf`, with its verdict) and
`docs/reviews/claude/goal-placement-r1-claude.md`. Every fix is in **`b296ef3e`**. Nothing was filed: each finding was
small enough to fold.

| Finding | Disposition | Where |
|---|---|---|
| **Codex LOOSENING** (52fb30e94f81, 554ec5c87391): `--add --goal g` with no `--thread` accepted; master refused it (backlog #505). Confirmed against `origin/master`. | FIXED — #505's pairing restored exactly, and its case and two mutations are master's again. Part (c) is now: neither given → refused (exit 2) with the name-the-goal / propose-one message. | `scripts/session-state.py` `ledger_add`, `ADD_NEEDS_GOAL`, `main` |
| **Codex MAJOR + Claude F1** — a placed entry's `waits` hard-coded `None`, so the page said "not recorded" despite a declared wait; the backlog row claimed (d) built. | FIXED — `--add --waits TEXT` stores a trimmed `waits` field; `goal-tree.py` `_ledger_waits` carries it through `derive` (placed and loose) into `agenda_digest`. `running` cannot be derived from the ledger (it sees no job or agent) and stays False; backlog #514's status now says exactly that. | `scripts/goal-tree.py` `_ledger_waits`, `derive`, `agenda_digest`; `docs/backlog.md` row 514 |
| **Codex MINOR + Claude F5** — a placed entry gaining a ref match read "no longer in flight"; parking/unparking a placed entry was no change. | FIXED — `changes` reads a departing id against the current threads' in-flight/parked details → "in flight, now on thread …"; `placed()` carries the parked bit → "parked under goal …" / "unparked, in flight under goal …". | `scripts/goal-tree.py` `changes` |
| **Codex MINOR + Claude F3** — the propose-a-goal mutant cut a string literal (SyntaxError, never reached its case). | FIXED — the mutant now replaces one whole literal fragment with `""`. | `scripts/mutations/session-state.json` |
| **Claude F2** — the goal-only mutant crashed the suite (fixtures added with `--goal` alone) before its named case. | FIXED — every fixture adds `--goal` with `--thread`; the mutant is retired (it is #505's own mutation now). | `scripts/session-state.py` self-test fixtures |
| **Claude F4** — a ref silently overrides the declared goal. | FIXED — the disagreement is a ledger problem: "entry X: declares goal 'g' but its refs place it under … — the ref match wins; fix the goal or the refs". | `scripts/goal-tree.py` `derive` (`ref_problems`) |
| **Claude F6** — the undeclared-goal flag cleaned `' g'` to `g`; `--add` accepted any string. | FIXED — quoted verbatim; `--add` refuses a blank goal or one with surrounding whitespace. | `scripts/goal-tree.py` `derive`; `scripts/session-state.py` `ledger_add` |

**Bound worth stating:** since `--add` always writes a thread, `--waits` reaches the agenda only for an entry placed by
its goal field (thread unreadable, or hand-written without one) or a loose one. A thread-hung entry declares its wait in
the thread line's `· waits on X`, as before.

**Measured:** session-state 137/137, goal-tree 500/500. Every added or re-bound #514/#505 mutation was run on a temp copy
outside the repository (8 session-state, 20 goal-tree): each exited 1 with its named case among the `[FAIL]` lines.
All 5,130 manifest anchors resolve exactly once.

**Route: continue.** Round 2 is owed (alternation: one half).

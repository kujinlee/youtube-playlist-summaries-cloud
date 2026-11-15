# Round 2 — `goal-placement` (backlog #514 c + d, PR #588) — coordinator — ⟳ NOT CONVERGED (Codex); all folded

```yaml
round: 2
fixes_nontrivial: true
subject: goal-placement
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: true, component: waits, disposition: fixed}
  - {id: Xm2, severity: Minor, aim: deliverable, fix_induced: true, component: timeline, disposition: fixed}
  - {id: Xm3, severity: Minor, aim: deliverable, fix_induced: true, component: timeline, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 is one half; the Claude half ran in round 1).

Half: `docs/reviews/codex/goal-placement-r2-codex.md` (committed as written, with its verdict). All three findings were
caused by the r1 fold (`b296ef3e`): r1 carried a ledger entry's `waits` only on the placed and loose paths, and matched
a handoff by the entry's prose. Every fix is in the r2 fold commit; nothing was filed.

| Finding | Disposition | Where |
|---|---|---|
| **Codex MAJOR** — a ledger entry hung on a THREAD (its own `--thread`, or a tracked thread its refs name) lost its `waits`: the agenda said running / not recorded. | FIXED — `derive_thread` keeps the entries naming the thread as `entries` (id, parked, waits), and the leaf says each entry's wait (`· waits on X (ledger entry id)`). `agenda_digest` holds the thread's item by `_join_waits(line's wait, every entry's wait)`. **Decision:** when the thread line also says `· waits on X`, BOTH are shown, the line's first, each once — never one hiding the other. | `scripts/goal-tree.py` `_join_waits`, `derive_thread`, `agenda_digest` |
| **Codex MINOR 1** — the timeline matched a handoff by `what` as a substring of a thread's detail (`audit` inside `audit PR #9`). | FIXED — matched by the entry's ID in the thread's `entries`; prose is never read. | `scripts/goal-tree.py` `changes` (`on_thread`) |
| **Codex MINOR 2** — an entry handed to a thread while parked was reported "in flight". | FIXED — `on_thread` returns the entry's parked bit: "parked, now on thread …". | `scripts/goal-tree.py` `changes` |

**Same-class search (same component).** Two more instances found and fixed in this fold:
- *A field dropped on one path* — `_fold_item` kept only the FIRST wait when two NOW entries joined into one item
  (`it["waits"] or x["waits"]`), so a second distinct wait was hidden. Now `_join_waits` keeps every distinct one.
- *A line the reader sees but the summary does not count* — `story` counted none of r1's "parked under goal",
  "unparked, in flight under goal", nor the new "parked, now on thread": a timeline holding only one of them read
  "1 change(s)". They count as in-flight work now.

No other place matches entries by text: the only detail-text read in the non-test code was `on_thread`. **Leads, not
fixed (outside this component):** (a) `derive_agenda`'s STEP waits are lent only by threads parsed from the tracked file
(`main`, `declared`), so a ledger thread's own `· waits on` and an entry's `--waits` never mark an agenda step blocked —
master behaviour since #505, not caused by this branch; (b) a `parked_loose` entry carries no `waits` and a parked loose
entry that departs gets no timeline line — neither has a reader today (parked work is not in the agenda's NOW).

**Measured:** goal-tree 506/506 (6 new cases, each red before its fix, all six red in one run: 500/506). Mutations
on temp copies outside the repository: all 11 added or rebound goal-tree entries exited 1 with their named case
among the `[FAIL]` lines — 8 new, 3 rebound (the running-vs-owed wait, the later-goal wait, F5a's `on_thread`); F5a's
`was` lookup retired with its subject. Pins goal-tree 388 → 395; all 5,137 manifest anchors resolve exactly once.

**Route: continue.** Round 3 is owed (alternation: the Claude half).

Reviewed head: 84ca2b0a6962f3489db98243f86bbe2c16a07814

# goal-placement (backlog #514 c + d) — round 3 — Claude half

Branch `goal-placement`, PR #588. Diffs read: `722ba87c..84ca2b0a -- scripts/` (the r2 fold) and
`origin/master...HEAD -- scripts/` (the whole change); r1/r2 coordinator documents and the r2 Codex half.

REVIEW GAP: codex — alternation (round 3 is one half; the Codex half ran in round 2).

Method, all EXECUTED: both `--self-test`s in the worktree (goal-tree 506/506 rc=0, session-state 137/137 rc=0); a
probe script (`python3 -I`, outside the repo) importing `scripts/goal-tree.py` and driving `derive`, `changes`,
`story`, `agenda_digest`, `agenda_now_items`, `_join_waits` and `fingerprint` on hand-built goal files and ledgers;
four r2 mutations from `scripts/mutations/goal-tree.json` applied to a TEMP COPY of `scripts/` + `docs/` (explainers
and reviews excluded) outside the repo, each copy's self-test run, with an unmutated control copy (503/506 — the 3
reds are the Ask-tray explainer cases, which need the excluded explainers). Nothing in the repo was modified except
this file and its verdict; no GitHub.

## Attacked, held

- **`_join_waits`** — order kept, each said once, `None`/`""` skipped, all-empty → `None`; a wait that is a
  SUBSTRING of another is kept (`"PR #7", "PR #77"` → `PR #7; PR #77` — equality, never `in`); a wait containing
  `"; "` is split and de-duplicated part-wise (`"a; b", "b"` → `a; b`), `x;y` (no space) is one part. Correct.
- **Thread-hung waits reach the agenda** — the same wait on the thread line AND an entry is ONE wait in the agenda
  (`('PR #21', False, 'PR #77')`); a non-parked entry's wait on a `next` thread makes it `inflight` and OWED with its
  wait; a merged thread with a waiting entry is not in NOW (finished), its leaf still says the wait.
- **`on_thread` by id** — an entry whose refs name TWO threads is reported once, on the first in goal order (no
  duplicate line); an entry REMOVED beside one whose text contains it is "no longer in flight" (the r2 case, held);
  an entry whose id CHANGES (same `what`) gives no false handoff — the old id is "no longer in flight" only when it
  had been loose/placed, and for a thread-hung entry the tree differs only in `entries` → `NO_READER_CHANGE`, which
  is true: the printed leaf does not show ids unless the entry declares a wait.
- **`story`** — `parked, placed under goal …` (r1's line, previously uncounted) now counts as in-flight work; no
  other change line starts with `parked`, so no double count.
- **Old snapshots** — `changes` reads `entries` only from `cur` and via `.get("entries") or []`, so a pre-r2 stored
  snapshot in the timeline (`goal-tree.py:2370`) neither crashes nor invents a handoff.
- **backlog #505's pairing is exactly master's**: `ledger_add`'s `if bool(goal) != bool(thread): raise ValueError`
  is byte-identical to `origin/master:scripts/session-state.py:352`; the branch only ADDS the blank/whitespace-goal
  refusal and the `--add` needs-goal refusal (part c). `ledger_threads` differs from master only by the goal-only
  `continue` block (part d); the thread-only path (goal missing) still reaches master's "goal '' is not declared".
- **Mutations** (temp copy; named case among the `[FAIL]` lines in every one; rc=1 each):
  `a joined wait is said twice` (4 fails = 3 control + named), `(Codex MINOR 2) a parked handoff reads as in flight`
  (4), `(Codex MINOR 1) a handoff is matched to ANY entry on a thread, not this id` (4), `(Codex MAJOR) the entries
  naming a thread are not kept on it` (7).

## Findings

### N1 — NIT — a PARKED entry's wait on a `next` thread leaves it ⬜ next; the same wait on the thread line makes it blocked

`scripts/goal-tree.py:584-592`. fix_induced: **true** (r2 fold added the entry-wait leaf text), component: waits/leaf.

Input: goal `g` with `- fix · backlog #50 · x`, ledger `{"id": "p", "what": "PARKED backlog #50", "kind":
"owner-wait", "waits": "owner"}` → state `next`, detail `no PR names it yet · parked: PARKED backlog #50 · waits on
owner (ledger entry p)`. The same wait written on the line (`· waits on owner`) gives state `blocked`. Nothing is
hidden — the leaf says both "parked" and the wait, and neither version reaches the agenda NOW (parked, resp. not in
the NOW states) — so the glyph differs by source, not the information. Not blocking; if wanted, promote `next` →
`blocked` when any entry declares a wait, as the line rule does.

### N2 — NIT — handoff identity is the id CUT TO 60 characters, so two ids sharing a 60-character prefix collide

`scripts/goal-tree.py:572,751`. fix_induced: **true** (r2 chose id identity), component: timeline.

Input: prev ledger `{"id": "a"*60+"1", "what": "job", "goal": "g"}` (placed) and `{"id": "a"*60+"2", "what": "job2
PR #21"}`; cur drops the first. `changes` says `in flight, now on thread [fix] PR #21: aaaa…` for the entry that
LEFT. The same cut id already keys `inflight_loose`/`placed` (`pl`, `pp_`) on master, so this is the snapshot's
existing identity, consistently applied — reachable only with ids over 60 characters, which the ledger does not
use. Not blocking; filing optional.

## Leads, NOT caused by this branch (pre-existing on master)

- `agenda_digest` (`goal-tree.py:1556`) drops a thread from NOW whenever ANY entry naming it is parked
  (`and not t.get("parked")`): a flying entry with a declared wait beside a parked sibling vanishes from the agenda,
  wait and all (probe E: `[]`). #497's rule, not r2's.
- A `next` thread whose LINE declares a wait becomes `blocked` and is then in no NOW state, so it is not on the
  agenda at all (probe H2: `[]`); and an `open` thread's line wait is in the agenda but not on its leaf (probe J).
  Both master behaviour.

## Thrashing watch

Both findings are fix-induced in the r2 component, and both are NITS with no reader misled about state or waits;
r2's three findings did not recur in any form I could construct. In my judgement this is not a second thrashing
round — the coordinator decides.

VERDICT: CONVERGED

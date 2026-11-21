# Architecture review — `backlog-closed-rule` (`gen-backlog-page.status_closed`): THRASHING, and the grammar that ends it

**Date:** 2026-11-20 · **Subject:** `status_closed` in `scripts/gen-backlog-page.py`, the rule that says whether a
backlog row is closed · **Branch:** `agenda-row-state` (PR #611; backlog #515, #611, #612) · **Measured against:**
`b1e98095` (the round-2 fold) and the round-3 fold that follows this note · **Convened by:** the arming condition in
[`docs/review-method.md`](../review-method.md) → *The arming condition — full account*, as recorded in
[`coordinator/agenda-row-state-r3-coordinator.md`](coordinator/agenda-row-state-r3-coordinator.md).

- **Tags:** **[M]** measured (a command ran and I read its output). **[I]** inferred.

## 1. The thrashing evidence

| round · finding | what it found | what caused it |
|---|---|---|
| r1 C2 (Claude) | `closed = "✅" in status` read a PARTLY-DONE cell (`🟡 … items (1)-(4) ✅ … item (5) open`) as closed | the original rule (any ✅ closes) |
| r2 m1 (Codex, `fix_induced`) | `🟢 FILED 2026-01-01; ✅ FIXED 2026-02-01` under an Item cell with no marker reads OPEN | **C2's fix**: only the FIRST status mark decides, and here it is 🟢 |
| r3 F1 (Claude, `fix_induced`) | `🟠 **REOPENED …** — previously ✅ CLOSED …`, `🟡 PARTLY DONE — (1) ✅ DONE …` and three more read CLOSED | **m1's fix**: a ✅ before a capitalised FIXED/CLOSED/SUPERSEDED/MERGED/DONE closed the row wherever it stood |

Two consecutive rounds (r2, r3) carry a finding caused by the previous round's fix, in one component. That is the
rule's shape **[M, from the round documents; every input above was re-run against the code it names]**. It is not a
prose floor: each finding is a row the backlog page, the goal tree and `check-features` would file on the wrong side.

## 2. Can a redesign remove it?

**Yes — by reading the cell in the grammar it is written in, not by adding clauses.** The backlog writes a row's
NEWEST state at the FRONT of its Status cell and keeps the history after it (row 231: `✅ **DONE 2026-11-15** …
PREVIOUSLY: 🟠 STILL OPEN …`; elsewhere `PREVIOUSLY: **CLOSED 2026-11-03 …**`) **[M, the live file]**. Under that
grammar only the first mark is state; every later mark is history. r1's rule already read it that way. r2's clause
read a later ✅ as state, which is the reverse of the grammar, so any finite list of closing words or positions keeps
producing the next counterexample: a reopened row that remembers its closure, a half written in capitals, an owed
tick named in advance. The chain flips direction because both findings sit on either side of one mis-read: r2 m1 is
a row written oldest-first, against the grammar, and F1 is rows written newest-first that the clause read backwards.

The reviewer's alternative (honour position: let the LAST state win when the cell is in time order) needs the parser
to know which order a cell was written in. Nothing in the cell says so, and the house order is newest-first, so that
rule reads every live history wrongly the moment it is reached **[I]**.

## 3. Decision taken

**Revert the r2 clause. A row is closed when its FIRST status mark is ✅, or when its Item cell is ✅** (the r1 rule).
r2 m1 is REJECTED with its measurement: the clause and its absence read **0 of 636 live rows and 0 of 352 parsed
historical versions** (377 versions of `docs/backlog.md`) differently **[M]**. Its cure is to write the closure first
(`✅ FIXED … — FILED …`), or to lead the Item cell with ✅ — which `check-docs.backlog_marker_errors` already demands
of any row whose Item cell carries a severity marker. The docstring now says so. A case pins F1's five inputs and the
r2 m1 row as OPEN, and the closure-first form as closed; a mutation that reads the LAST mark instead is killed by it.

## 4. Deliberately not handled

- **An oldest-first cell under a marker-less Item cell reads OPEN.** Stated as a BOUND in the `status_closed`
  docstring. It fails toward "still open", which shows work rather than hiding it, and the live exposure is zero.
- **`❌ NOT ✅ DONE` reads closed** (❌ is not an open mark). Pre-existing, no live row has it (r3 refutation 2).
- **No grammar check.** Nothing enforces "newest first" on the Status cell. A writer who appends instead is caught
  only by a reader; a ratchet would need a definition of "state mark" that `check-docs` and this parser share, which
  is a larger change than this PR and has no live failure to motivate it **[I]**.
- **F2 (`agenda-step-state`) and F3 (`wait-date-parse`)** are fix-caused too, but neither is a rule fighting a
  grammar: F2 is a stated precedence trade (an open PR naming a ✅ row holds the step at ⏳), F3 a one-day docstring
  error. Both are dispositioned in the coordinator doc, not here.

**What we decided that is not written down:** that the Status cell is newest-first. Every writer already does it,
but the only written trace was the r1 docstring's examples. The `status_closed` docstring now states it as the
reason for the rule.

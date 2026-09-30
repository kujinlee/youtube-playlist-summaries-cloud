---
name: guard-classification-shape-vs-sequence
description: "FIRES-WHEN: writing or classifying a guard — Classify every guard SHAPE (caller is wrong → reject) or SEQUENCE (caller was merely second → must reconcile); one shallow total pass found two defects seven deep review rounds missed"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-08-08T20:25:42.619Z
---

**Measured 2026-08-08 (PR #57, `0b27094`), run as the opening of round 8 rather than as part of it.**

| | Asks | A violation means | Must |
|---|---|---|---|
| **SHAPE** | is this row well-formed and referentially sound? | the **caller is wrong** | **reject** |
| **SEQUENCE** | who got here first? already happened? in flight? | **concurrency** — the caller did nothing wrong and may already have spent money | **reconcile**: upsert, no-op, or typed outcome. Never a raw rejection |

**The one question — and it is NOT "is this guard correct?":**

> **What does this guard do when the caller is merely SECOND?**

Both defects it found were in guards that are *plainly correct*, which is exactly why seven adversarial
rounds skimmed past them. Result: 32 guards, 28 SHAPE, 4 SEQUENCE — every CHECK and FK was SHAPE and
fine, so the pass concentrates attention on ~4 items, which is most of its value.

- **Free renders could never be overwritten** — an entire *kind* of write unreachable, raw `23505` on
  every re-render, against a comment promising they were "overwritable". Same shape as the item-3
  defect, and it survived because **every fixture wrote a free render exactly once**.
- **§8's retention sweep could never run** — the safety rule raised, so a batch collect aborted on the
  first permanently-current row and rolled back the rest. A guard that made its own purpose
  unreachable.

**The generalisation.** This is the user decision *"the reservation guards spending, not recording"*
(2026-08-07) restated as a property of a **class** rather than of one function. Recording it at one
site is why it went on to break twice more.

**Why the process missed it for so long, which is the transferable part.** Every instrument here is
**opt-in** — an assertion exists because someone thought of the case, a mutation because someone wrote
one, a review finds what a reviewer looked at. They do not have independent blind spots; they share
**one**, so anything nobody thought of is invisible to all of them at once. **Depth and coverage are
different axes**, and seven deep rounds lost to one shallow total sweep.

> **An absence is only visible against an ENUMERATED WHOLE.** Wherever the system names a finite
> population — an enum, a state machine, a set of typed outcomes, the set of guards — coverage over it
> is checkable rather than remembered.

**Now enforced, not remembered** (running it by hand would be the same defect one level up):
`scripts/check-guard-coverage.py` reads `pg_catalog` and fails on any unclassified guard or any
SEQUENCE guard without a mutation; `05_assert.sql` requires every `artifact_kind` to be written a
**second** time. Run everything with `./scripts/check-schema-gates.sh`.

**Ratchet-design note worth keeping:** the pawl is *classification completeness*, **not** the guard
count. A count ratchet would fire on legitimate work (adding a guard *should* change it) and train
everyone to bump the number.

See [[unsatisfiable-ordering-is-the-tell]], [[what-mutation-testing-proves]],
[[what-mutation-testing-proves]], [[blob-addressing-spec-state]].

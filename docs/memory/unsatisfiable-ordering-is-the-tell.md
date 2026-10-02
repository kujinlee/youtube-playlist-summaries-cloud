---
name: unsatisfiable-ordering-is-the-tell
description: "FIRES-WHEN: writing an invariant of the form 'X is always true' — Three of four blob-addressing items were an invariant written as 'X is always true' that meant 'X must be true when Y observes it' — and each announced itself as an unsatisfiable ORDERING, never as a wrong value"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-08-08T00:41:49.307Z
---

**Measured across handoff items 1, 2 and 3 of the stable-blob-addressing review (PRs #52, #53, #55),
2026-08-06/07.** Each was reported as a defect and each dissolved once one rule was reclassified.

The recurring shape:

> An invariant written as **"X is always true"** that actually meant **"X must be true at the moment Y
> observes it."**

- **Item 1** — separated it as *a CHECK governs states, a trigger governs transitions*.
- **Item 2** — the guard lived in the `NOT NULL`, not in the comparison beside it.
- **Item 3** — a generation must be complete *when something RECORDED points at it*, not from the
  moment it exists.

**Why:** the over-strong version is cheap to write and reads as rigour, so it survives review rounds
that check whether the rule is *true* rather than whether it is *reachable*.

**How to apply — the diagnostic is the symptom, not the rule.** Each one announced itself as an
**UNSATISFIABLE ORDERING**, never as a wrong value:

- item 3's was literal — reserve needs the parent row to exist, the CHECKs need it to be complete, and
  the paid call sits between. Both doors locked, measured as `[23503]` one way and `[23514]` the other.

So when two rules make a required sequence impossible, do **not** look for which one is wrong. Ask
which is **P** (physical) and which is **I** (chosen) — per `dev-process.md`'s classification step —
and then ask what the I one *forbids*. In all three cases the I rule was sound in substance and wrong
in its **scope of application**, so the fix was a gate, not a deletion.

**Corollary worth as much as the rule: a green suite can describe a world the system cannot reach.**
All 73 assertions missed item 3's defect because every fixture hand-inserted a *complete* generation
row — the one thing no producer can do. The same pass found `detached_at = 2020-01-01` against a
generation produced in 2026, sitting inside a passing test. Fixtures encode assumptions and nothing
type-checks them.

See [[blob-addressing-spec-state]], [[defined-not-derived-constants]],
[[detached-dig-retention-decision]] (each the individual instance), and
[[test-harness-can-launder-failures]].

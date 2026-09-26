# development-velocity.md — TOMBSTONE. The content moved; this file routes you to it.

> ⛔ **THIS IS NOT A DOCUMENT. It is a forwarding table.** Nothing here is evidence, design, a rule or
> a decision. If you followed a citation to this path, find your section below.
>
> **Why it still exists:** ~23 files under `docs/reviews/` and `docs/dashboard-entries.md` cite this
> path, many by section number. They are dated testimony and are not rewritten, so the path has to
> keep answering *"where did §N go?"*. Deleting the file would turn 23 stale citations into 23
> dangling ones.

## Where each section went

| old § | what it was | where it is now |
|---|---|---|
| **§1** baseline — where the time went | measurement | [`velocity-evidence-2026-09-24.md`](velocity-evidence-2026-09-24.md) §1 |
| **§2** the instrument question | **design** | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §1–§2 |
| **§3** the four SEAM-not-LOGIC signals | **design** | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §2, *The escalation half* |
| **§4** the five timing rules | **design** | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §2, *The timing rules* |
| **§4** the controlled experiment | measurement | [`velocity-evidence-2026-09-24.md`](velocity-evidence-2026-09-24.md) §4 |
| **§5** sweep policy, four items | **design** | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §2, *Sweep policy* |
| **§5** the CI cost figures | measurement — ⛔ one is CRACKED and marked | [`velocity-evidence-2026-09-24.md`](velocity-evidence-2026-09-24.md) §5 |
| **§6** injection rules | **rules in force** | [`process-checklists.md`](process-checklists.md) → *Reduce defect INJECTION* · evidence in [`velocity-evidence-2026-09-24.md`](velocity-evidence-2026-09-24.md) §6 |
| **§7** side jobs | **rules in force** | [`process-checklists.md`](process-checklists.md) → *A SIDE JOB gets a name* · evidence in [`velocity-evidence-2026-09-24.md`](velocity-evidence-2026-09-24.md) §7 |
| **§8** the four rejections | **decisions** | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) → *The four rejections* |
| **§9** the five answered questions | **decisions** | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) → *Decisions of record* |
| **§10** what is left | design brief | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) + [the plan](superpowers/plans/2026-09-25-development-velocity-RECONSTRUCTED-plan.md) |

---

## ⭐ THE CITING SITES — enumerated here because nobody ever enumerated them, and that is what thrashed

⛔ **This list is the point of this file.** Rounds 1, 2 and 3 of the `velocity-backfill` review each
found a reader being routed to a retired section, and each repair covered only the sites the previous
round happened to name. r3's verdict called it **thrashing** and named the structural cause: *no
document lists the inbound sites, so each round's sweep is performed from scratch by hand and each one
is incomplete in a different place.* A grep is not a corpus — one of these sites contains **no
occurrence of the filename at all**.

**LIVE sites — these must all resolve. Changing this file's routing means re-checking every row.**

| site | cites | kind |
|---|---|---|
| `process-checklists.md` → *Reduce defect INJECTION* | old §6 | measurement |
| `process-checklists.md` → *A side job inherits NO design approval* | old §4's experiment | measurement |
| `process-checklists.md` → same rule, the sentence after the §3 redirect | ⛔ **a PRONOUN — "that document" — and NO filename** | design status |
| `roadmap-to-launch.md` → the #177 block | the whole document as "the deliverable" | index |
| `backlog.md` row 177 | old §3, §8, §9, §10 + the cracked 2× figure | design + decisions |
| `superpowers/specs/2026-09-25-decision-card-soundness-design.md` | old §4's experiment column | measurement |
| the spec and the plan of #177 | the evidence document, by section | measurement |

**HISTORICAL sites — dated testimony, deliberately NOT rewritten:** ~23 files under `docs/reviews/`
plus `docs/dashboard-entries.md` (append-only). They cite line numbers that have already moved, which
is why this repo's rule is to cite a **symbol or heading**, never a line.

⚠ **The pronoun row is the one a string sweep cannot find**, and it is why this table is written by
hand rather than generated. r2 swept 3,267 files for the filename and missed it; so did the fold that
answered r2.

---

## The deletion condition, as a checkable list rather than a sentence

This file can be deleted when **both** hold:

- [ ] #177's forward work has landed — Q0 in `review-method.md` §0, and strand ⑸ de-escalation.
- [ ] **every LIVE row above has been repointed at its new home**, so nothing cites this path as
      anything but history.

⛔ **The second box is the one that has been mis-evaluated three times.** It is not *"grep found
nothing"* — the pronoun row proves a grep cannot answer it. Tick it by walking the table.

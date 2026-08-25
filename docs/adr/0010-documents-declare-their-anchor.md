---
status: proposed — accepted when the header check ships and passes on the living set
---

# A document declares the goal it belongs to; the index over documents is derived, never maintained

**2026-08-24.** Asked for "the plan for stable blob addressing", I failed to find
`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` — which *is* that plan — and
spent about an hour re-deriving its contents, reaching a conclusion **the document had already
corrected in itself**. Two independent causes, and only one of them is naming:

- the search was **truncated** — `ls docs/superpowers/plans/ | head -20` over an **82-file**
  directory, and the file sorts at position **80**;
- the plan is named for its **mechanism** (*append-only generations*) while the goal is *stable blob
  addressing*, so a goal-keyword search cannot reach it.

The feature spans three vocabularies — `stable-blob-addressing`, `append-only-generations`,
`cloud-blob-key-encoding` — plus 96 review files. **Each rename was correct when it was made**; the
design genuinely moved. Together they mean the goal and the current plan share no keyword.

**The decision.** Three parts, and only the first is written by hand:

1. **The edge lives in the document.** Every living spec and plan carries a header:
   `Anchor:` (a slug from a registry), `ADR:` (numbers, when a decision exists), `Goal:` (one
   sentence in the anchor vocabulary).
2. **The index is generated** — one card per anchor, grouping its ADRs, spec, plans and review
   count, and **pointing at the roadmap for state rather than copying it**. Nobody edits it.
3. **A check makes the header non-optional** for new documents, and validates that every `Anchor:`
   resolves to the registry and every `ADR:` to a file.

## The principle this rests on

> **A central file that holds NAMES is safe. A central file that holds STATE drifts.**

A registry of anchor slugs is append-only: a name, once allocated, does not change, and a document
citing an unregistered one fails loudly at check time. A relationship map holds *state* —
relationships change every time the design moves, and nothing in the file announces when it stopped
being true.

There is a second asymmetry, and it decides where the edge goes. A document knows **what goal it
belongs to**, and that is stable for the document's whole life. A document does **not** reliably know
its children — every new sibling would require editing a parent, and the edit that is easy to skip is
the one that rots. **Declare upward in the document; derive downward by aggregation.**

## Considered options

Recorded because the rejections are not obvious, and because the failure mode is already measured:
**backlog #59 was filed 2026-08-22 and I proposed the same page as #64(2) on 2026-08-24 without
finding it.** The ADR format's own rule anticipates exactly this — *record the rejected alternative
or someone will suggest it again in six months*. Here it took eleven days.

### 1 — A central relationship document (second-brain style, MD files cross-linking)

**Rejected, and not on principle: this repo already runs one, and it is already wrong.**
`scripts/gen-backlog-page.py:357` carries `ROOTS` and `DEPENDS` — a hand-maintained map of how
backlog items relate. The append-only roadmap's own *Known stale artifacts* section records two
defects in it:

- `DEPENDS[19]` says `survives`; under spec §5.2 it should be `dissolved-by`;
- the root is gated by #23 and **that edge cannot be expressed at all** — `DEPENDS` is
  `item → (relation, root, note)` and `ROOTS` has no parent field.

So the measured result of running this option here is that it drifted within days **and** hit an
expressiveness wall where a true relationship had no slot. Both were caught by a review round, not by
any script — the tell that nothing was keeping it true.

### 2 — Free-text tags plus a tag table

**Rejected as under-specified rather than wrong** — it is most of the chosen design, minus the one
property that decides whether it survives. An uncontrolled tag is a keyword wearing a badge. This
feature accumulated three vocabularies through three *honest* renames; free-text tags would have done
the same, because each new tag would have described the mechanism the design had moved to.

A renamed free-text tag **silently stops matching**, which is the failure mode this project has
already paid for (`hardcode-only-what-fails-loudly`: a vocabulary that silently stops matching is
worse than no check). A registry converts silence into a loud failure.

### 3 — Put the ADR number in the FILENAME (`ADR-0007-stable-blob-address-…md`)

**Rejected on two measurements.** A filename carries one prefix, but a document can serve two
decisions — the append-only roadmap cites **ADR-0006 and ADR-0007**. And renaming breaks links:
`check-docs` validates 47 living-doc links today. A header is multi-valued and moves no files.

### 4 — Do nothing; rely on search

**Rejected by measurement.** Membership derived by keyword across all three vocabularies returns
**7** of 162 specs and plans — and `docs/superpowers/plans/2026-08-22-m1-honest-card.md`, which the
roadmap names in its own fifth line as M1, contains **zero** occurrences of any of the three. Keyword
search cannot see a known member, so the derived set is a lower bound of unknowable size.

## Why `Anchor:` is the primary key and `ADR:` is an attribute

**Not every goal has an ADR.** Corrections-in-cloud spans a spec, a plan and nine merged PRs, and
none of the nine ADRs in `docs/adr/` is about corrections. If the ADR number were the only key, that
whole feature would be unaddressable. The ADR remains the *anchor's* stable identifier where one
exists — which is what survived two renames that destroyed every keyword.

⟳ **This corrects backlog #64**, which named the ADR number as the key.

## Scope — what gets a header, measured rather than estimated

| Set | Count | Header |
|---|---|---|
| All specs + plans | 162 | — |
| Referenced by roadmap / backlog / ADR / dev-process | 15 | yes |
| Modified in the last 30 days | 19 | yes |
| **Union — the living set** | **22** | **backfilled** |
| `docs/reviews/` | 716 | **never** |

The split is **living vs point-in-time**, not old vs new, and it is computable: a document is live if
something still points at it or someone still edits it. A date cutoff was considered and rejected in
the same discussion — the roadmap that was lost is three days old, but the design spec beneath it is
`2026-08-03`, so a cutoff would leave the index blind to exactly the documents people hunt for.

**The backlog gets no header and no new column.** Its anchor mechanism already exists: `ROOTS` is
keyed `"adr-0006-addressing"` and six rows already hang off it via `DEPENDS`. Adding a second would
be a duplicate mechanism for one concern — the condition `scripts/check-vocabulary-collisions.py`
exists to catch. The work there is to make the registry and `ROOTS` share one vocabulary.

## What makes the check FAIL

Stated as an observation, per `docs/dev-process.md`'s rule that a gate names its own falsifier:

- a file added under `docs/superpowers/specs/` or `plans/` whose first 10 lines lack `Anchor:` or
  `Goal:`;
- an `Anchor:` value absent from the registry;
- an `ADR:` number with no corresponding file in `docs/adr/`;
- a registry entry no document claims (a name allocated and never used).

It is a **ratchet**: it fails forward on new documents and does not retroactively red the ~140
historical files that will never carry a header.

## Consequences

- **`check-docs` gains new subject matter.** `check-docs.py:46` sets
  `FROZEN = ("docs/reviews/", "docs/superpowers/")` — specs and plans are deliberately *not*
  link-checked today, as point-in-time artifacts. A header rule over them is a new stance on that
  directory, not an extension of the existing pass. ⟳ Corrects backlog #64, which claimed the latter.
- **The `Goal:` line cannot be generated, and a wrong one is worse than none** — the index renders it
  as fact. Twenty-two sentences written from each document's own opening, not from memory. The `ADR:`
  half is mechanically checkable and catches the likeliest error.
- **The index is downstream.** Backlog **#59** (decision index) and **#64(2)** are the same page
  under two script names; they fold into one, and it has no real input until the headers exist.
- **This is not stable-id work.** It is a detour, taken because it cost an hour on 2026-08-24 and
  will cost more. The headers are bounded; the page is not, and is deliberately deferred.

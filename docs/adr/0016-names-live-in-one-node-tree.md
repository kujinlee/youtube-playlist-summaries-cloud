---
status: proposed 2026-11-23 — accepted when the slice that deletes `docs/anchors.md` merges with
  every gate green. Supersedes PART of ADR-0010 (where the names live; that a name never changes).
  ADR-0010's other decisions stand. ⚠ PROPOSED IS NOT IMPLEMENTED: at the time of writing
  `docs/anchors.md` is still the registry and `scripts/check-anchors.py` still reads it.
---

> **Anchor:** `status-visibility` — **ADR:** 0010, 0016
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

# Names live in one tree of nodes; a name may be renamed if the old one is recorded

**2026-11-23.** The owner asked what the difference is between a goal on the goals page, a goal on
the goal-tree page and a feature on the features page, and settled that there is none: each is a NAME,
with a purpose sentence, under which documents, activity and bugs are linked. The design is
`docs/superpowers/specs/2026-11-23-goal-node-tree-design.md`; this record holds the two decisions in
it that change an earlier ADR.

## What ADR-0010 decided, and what is kept

ADR-0010 decided that a document declares the goal it belongs to in an `Anchor:` / `ADR:` / `Goal:`
header, that the index over documents is derived and never maintained, and that a central file is
safe when it holds NAMES and unsafe when it holds STATE.

All of that is kept. A document still declares; the pages are still derived; an unresolved name still
fails loudly.

## What changes

**1. The membership list is the node tree, not `docs/anchors.md`.**

ADR-0010 made `docs/anchors.md` the registry an `Anchor:` slug must resolve to. Measured on
2026-11-23, the project had three such lists — 15 anchors, 9 goal-tree goals in
`docs/goal-threads.md`, 35 feature nodes in `docs/features.md` — and a fourth hand-kept tuple in
`scripts/check-goal-status.py`. 12 of the 15 anchors were also feature nodes under the same slug; 7
of the 9 goals were in no other list.

The one list is `docs/features.md`, which is a tree already and has the stronger guard. A node carries
what the registry row carried (its purpose sentence, its ADR numbers) as fields. An `Anchor:` header
resolves to a node. `docs/anchors.md` is deleted.

**2. A name may change, if the node records the old one.**

ADR-0010: "a name, once allocated, does not change." The reason given was that a registry of names is
append-only and therefore cannot drift. That reason survives a weaker rule: a slug may be renamed
provided the node lists the former slug in a `was:` field, and

- a former slug used in a LIVING source fails the build, naming the current slug;
- a former slug met in HISTORY — a logged snapshot, a ledger entry, a frozen review, a commit
  subject — resolves to its node;
- a slug is unique across current AND former slugs, so a retired name is never given a new meaning.

The list stays append-only in the sense that mattered: no name is ever lost or reused.

## Considered options

- **Keep three lists and add a check that they agree** (backlog #644's part d). Rejected: it guards a
  duplication instead of removing it, and the 7 goal-only names show the lists were never meant to
  agree — each allocated names the others lacked.
- **Extend `docs/anchors.md` into a tree.** Rejected: it rebuilds the feature tree's grammar in table
  cells, and `docs/superpowers/specs/2026-09-19-feature-hub-design.md` rejected the registry as the
  spine because it mixes kinds of thing, which a tree with trunks holds apart.
- **A new file.** Rejected: a third grammar and a third guard where an existing one serves.
- **Renames forbidden; old names kept for ever.** Rejected by the owner's decision to drop `-first`
  from two slugs: a name that states a priority is wrong the day the priority moves.

## What makes the check FAIL

- an `Anchor:`, a `## GOAL` heading, a thread's `also`, a backlog `epic:` parent or a slug constant
  in a script that is not a current node slug;
- a former slug in any of those;
- a slug that appears twice among current and former slugs;
- `docs/anchors.md` existing after this ADR is accepted.

## Consequences

- ADR-0010's rule "a registry entry no document claims fails" is dropped. It was a rule about a list
  of anchors; most nodes are features with no spec and need none.
- History is never rewritten to follow a rename. The logs that hold old slugs are git-ignored and
  differ per checkout, so they could not be; they are resolved when read.
- "Anchor" remains the header keyword on 63 documents and now means "the node this document belongs
  to". `CONTEXT.md` uses the word for a mutation anchor; the design's question Q7 settles the entry.
- The feature-hub spec's one-way edge (a node NAMES its anchors) has nothing left to point at and is
  removed with the `anchors:` field.

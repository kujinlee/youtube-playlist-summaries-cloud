# Architecture review — the backlog `status` facet in the comprehensibility spec (backlog #384), armed by THRASHING

**Armed by:** fix-induced findings in ONE component, `status-facet`, in two consecutive rounds of
`comprehensibility-spec`:
- round 2: Codex C1 (High) — the migration table r1's H5 fold wrote mapped keywords found inside prose, not the
  Status column's real first words, and its "(none) — 57" bucket identified nothing;
- round 3: Claude M1 (Medium) — the normalisation the r2 fold wrote does not reproduce its own counts (literal rule:
  `✅` 124, OPEN-family ~13; table: 131 and 249); Claude M2 (Medium) — "the 16 not-done rows" seeding `needs-you` are
  neither listed nor sourced (the stated phrases match 27).

Per `docs/dev-process.md` → *Phases* (THE ARMING CONDITION IS THRASHING), that arms Phase 6. Rounds:
`docs/reviews/{codex,claude,coordinator}/comprehensibility-spec-r{1,2,3}-*.md`. Subject: the spec
`docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` at `1dfb7344`. Read first: ADR-0010 (a central
file of NAMES is safe, one of STATE drifts). The owner's answers (§1, §8, §10) are fixed and not re-opened; §8 Q3
(where the facet lives) is the coordinator's own mechanical choice, so it MAY be revisited, and is (option B).

## What kept failing, and why

**Every status-facet finding of rounds 1–3 is about the same kind of text: row-level arithmetic over `docs/backlog.md`
written into prose.**

| Round | Finding | What the text was | Kind |
|---|---|---|---|
| r1 | H5 (not fix-induced) | no home for status; the fold ADDED a 13-keyword table and "57 empty cells" | introduced the arithmetic |
| r2 | C1 (fix-induced) | that table's counts and buckets were wrong against the real cells | arithmetic |
| r3 | M1 (fix-induced) | the r2 normalisation, as written, does not yield the r2 counts | arithmetic |
| r3 | M2 (fix-induced) | a hand-picked set of 16 rows with no list and no provenance | arithmetic (a set) |
| r3 | L1 (not fix-induced) | "`✅` on 117 of 333 rows" from `9ac7c80d`, beside `fde542a7` figures | arithmetic, stale |

The facet's DESIGN — four closed values, the first word of the existing `Status` column, no default, the parser
refusing an unknown word — has drawn NO finding since r1 fixed its home. Every later finding attacks a number or a
row set that a fold typed into the spec. Each fold answers by re-measuring and writing a more detailed table, and
a more detailed table is a larger surface for the next reviewer to re-derive: r1 had one table, r2 a table plus a
normalisation, r3 asks for a full normalisation grammar plus 16 row numbers plus 11 exclusions with reasons.

**Can a redesign remove it?** (`docs/review-method.md` → *The stop condition*.) Yes. These findings are not
branch-coverage defects of a rule; they exist only because the spec restates, by hand, a computation over a corpus.
The same lesson is already in memory (*review is the wrong instrument for a SURFACE*: six rounds found ~7 edge cases,
one corpus run 5,287). A spec reviewer re-deriving 422 rows by hand per round is that instrument.

**The coordinator's hypothesis, tested.** It had two parts.
- *The remedy* (move the arithmetic into row 2's build, computed by code, pinned by a test): **HOLDS** — see option A.
- *The cause* ("reviewers re-derive from a MOVING file each round"): **PARTLY REFUTED.** The backlog did not move
  during this spec's rounds — `git log fde542a7..origin/master -- docs/backlog.md` is empty, and the parser gives
  422 rows / 150 `sev == done` on `befd0e6d`, `fde542a7`, `1dfb7344` and `origin/master` alike. M1 and M2 are not
  drift; they are prose failing to carry a computation (an incomplete grammar, an unlisted set). Only L1 is drift
  (`9ac7c80d`: 333 rows / 117 → `befd0e6d`: 422 / 150). The file DOES move fast in general — 60 commits touched
  `docs/backlog.md` on `origin/master` since 2026-10-26 — so drift is the NEXT failure the table would have had, not
  the one it had. The remedy is right for a stronger reason than the one proposed: prose is the wrong carrier for a
  computation even when the input stands still.

## The options, and what each would have prevented

The six status-related findings of rounds 2–3 are C1, M1, M2, L1 (`status-facet`) and C2, C3 (`needs-you`, whose
input set is the `needs-you` rows). M3 (`needs-you`, not fix-induced) and C4 (`freshness`) are listed for completeness.

| Finding | A: rule + owner-at-build + falsifier; counts in row 2's test | B: facet as `⟦status: …⟧` tag, arithmetic kept | C: keep the table, pin the normalisation as code in the spec |
|---|---|---|---|
| r2 C1 | **prevented** — no table to mis-map | not prevented — the migration from old cells needs the same table | not prevented in r2 (the table was the code's output) |
| r3 M1 | **prevented** — the rule is one sentence of intent; the exact grammar is code, run over the real file | not prevented | prevented (the code IS the rule) |
| r3 M2 | **prevented** — the set is decided by the owner at row 2's build, not claimed as already reviewed | not prevented | not prevented — a hand set is not code |
| r3 L1 | **prevented** — §5 keeps one motivating figure with its commit; nothing beside it to disagree with | not prevented | not prevented |
| r2 C2 | not prevented — a set-membership rule in row 4 | not prevented | not prevented |
| r2 C3 | not prevented — a write-ordering rule in row 4 | not prevented | not prevented |
| r3 M3 | not prevented — fixed separately by a `row:` field | not prevented | not prevented |
| r2 C4 | n/a (freshness) | n/a | n/a |

**A prevents 4 of the 6 status-related findings (all 4 in `status-facet`, 0 of 2 in `needs-you`).** B prevents 0: it
changes where the facet is WRITTEN, but the migration from 422 free-text cells is the same arithmetic, and it reopens
§8 Q3 for nothing (after migration the facet is a clean prepended first word, as easy to parse as a tag). C prevents
1 (M1) and makes the spec carry a program that must be re-run whenever the backlog moves — it keeps the surface and
adds a second copy of row 2's code.

The `needs-you` findings (C2, C3, M3) are a different shape: rules about two sets and one write order, each closed by
a sentence and each with a falsifier in §7. That component had fix-induced findings in r2 only (C2, C3), none in r3
(M3 predates r2), so it is NOT thrashing and is folded as an ordinary round. M3 IS a mechanism defect ("references"
had no definition, and r2 widened it to ANY entry, so prose could hide a row), and the redesign that removes it is
small: a declared `row:` field on the ledger entry, mirroring how `kind:` replaced the `WAITS-ON-OWNER:` prefix.

## Decision (recommended): A

The spec states only:
1. the facet's four closed values and its home (unchanged);
2. the migration RULE in one sentence — strip the cell's leading glyphs, emphasis and a `(was …)`/`(filed …)`
   parenthetical, map the first word to a value, prepend it, keep the old cell verbatim;
3. who decides ambiguous rows — **the owner, at row 2's build**, from a list row 2's code produces (cells whose first
   word maps to nothing, cells a later `✅` contradicts, and every candidate for `needs-you`). This is M2's
   "decided by the owner during row 2" fix, and it keeps the owner's §10 Q1 answer intact;
4. the falsifiers — after migration the parser refuses any first word outside the four, and row 2's test pins the
   counts its code computed on the commit it was built on.

Removed from the spec: the per-value table, the normalisation detail, the 16, the 189, the 20+20, and the §9 line that
sourced them. Row 2's build owns all of them.

## Stop condition for the next round

Round 4 is past the round cap (`docs/review-method.md` §0 Q4c): its findings are FILED unless a BLOCKER. For this
component specifically:
- **A round-4 finding that asks the spec for a COUNT, a row list or a normalisation detail of the status migration
  is filed against row 2's build, never folded into the spec.** Folding it would re-create the surface this review
  removed.
- **The redesign FAILED if** round 4 carries a fix-induced finding in `status-facet` that is NOT about arithmetic — a
  contradiction in the four values, the no-default rule, or the owner-at-build step. That would be a mechanism defect
  in the facet itself and goes to the owner, not to another fold.
- **The redesign HELD if** round 4 has no `status-facet` finding, or only ones of the filed kind above.

## What did we decide that isn't written down?

- **That a spec carries RULES and FALSIFIERS, and a build carries COUNTS.** The spec had been accumulating measured
  per-row tallies as if more precision made it more correct; nothing in `docs/process-checklists.md`'s spec-contents
  list says where a migration's tallies belong. Written down here; a candidate for that list (not edited in this
  branch — it is a process doc, and the round cap says file, not widen).
- **That the owner, not the coordinator, picks which existing rows become `needs-you`.** r2 wrote "each reviewed" as if
  someone had; nobody had a list. The spec now says it, in row 2.
- **That a ledger entry's link to a backlog row is a declared field, not a text match** (M3). Every other ledger
  property that sets membership (`kind`) already went that way; `row` follows it.
- **That status-word normalisation is a one-time migration step, not a permanent parse.** After row 2 the first word is
  one of four exact values and the normaliser is deleted, so its grammar never needed to live in a durable document.

# Backlog #70 implementation — whole-branch review, round 1 (Claude half)

**Subject:** `origin/master..HEAD` on `feat/mutation-manifest-retarget`.
**Codex half:** [`branch-mutation-retarget-r1-codex.md`](branch-mutation-retarget-r1-codex.md).

⚠ **REVIEW GAP: claude — the dispatched independent reviewer had not returned when this was
written.** Per `docs/plugins.md`, do not wait. This half is the coordinator's own verification plus
adjudication of Codex's findings; it is weaker than an independent pass and is recorded as such.

**Verdict: NOT CONVERGED at first pass — 5 defects, 2 of them found by Codex against the
implementation. All fixed; re-review wanted.**

## Found by EXECUTING the plan, after two reviewers had read it

1. **The substitution table read 1:1 and two of its entries occur TWICE.**
   `ev["mutations"].append(` and `ev["survivors"].append(name)` each appear twice in the moved block.
   A single `replace` leaves one behind — `NameError`, or worse, half the evidence silently written
   to the old dict. Caught by asserting an expected *count* per substitution.
   ⚠ **Codex had cleared this table as complete.** True about the names it listed; silent about how
   many times each occurs.
2. **The plan's insertion point put new cases after the line that PRINTS the total.**
   The suite printed `121/121` while the cases pushed `ok` to 125 — and `_drift_rc`, whose entire job
   is to catch a wrong count, **passed**, because it read the counter later than the printer did. A
   stale number shown to a human with a green guard standing behind it.
3. **A fixture anchor was ambiguous** (also Codex, round 1 on the plan).

## Found by Codex against the implementation

4. **Blocking — a live fail-open in `check-dashboard-entry.py:243`.** Mutating
   `added = any(_added_entry_line(l) …)` to `added = True` **survived the whole manifest**. The
   ratchet would then report every branch as having added a dashboard entry. Root cause: the
   success-path case asserted `ch` and `err` but not `ad`, and none of the 11 manifest entries
   touched `added`. Reproduced independently before accepting.
   **Fixed:** the case now asserts `(ch, ad, err)`, and a 12th mutation pins it. 43 → 44 mutations.
   ⚠ **Scope deviation, stated:** the spec said "no change to the 43 entries". Adding a 44th to close
   a fail-open a review found is what a review is for; leaving it would make the branch's own claim —
   *the mutation evidence describes the code that ships* — hollow.
5. **High — `EXPECTED_MUTATIONS` pinned cardinality, not identity.** Replacing one entry with a
   duplicate of another keeps the count at 32 and passes, while real coverage shrinks. Reproduced.
   **This is the same error as `CONTRAST_MIN` earlier the same day**: asserting a proxy (how many)
   instead of the property (which ones), in the guard built to prevent exactly that.
   **Fixed:** `load_manifests` now rejects duplicate names and duplicate edit anchors. Falsified —
   the duplicate is refused by name.

## Verified sound

- **The 106-line extraction is BYTE-IDENTICAL** to its original after exactly the three declared
  substitutions. Proved by reconstructing the expected text and comparing, not by reading a diff.
  This is the load-bearing check for the whole branch.
- Equivalence at one tree: old path and new path both 43/0 before the 44th mutation was added.
- Each path shown individually falsifiable: a broken delivered file makes the control red and the run
  refuse with 0 mutations applied; a deleted manifest entry is refused naming file and both numbers.
- `ci.yml` no longer names the plan (`grep -c` → 0) — the spec's last falsifier, answered by
  observation.
- Codex independently confirmed both `ev[...]` sites converted, `check()`'s ordering preserved, and
  the YAML valid.

## Gates

`check-plan-code` 136/136 · `gen-dashboard` 113/113 · `gen-backlog-page` 73/73 ·
`check-dashboard-entry` 46/46 + 5/5 · `check-docs` · `check-anchors` · `check-arch-findings` ·
`check-roadmap-consistency` · `--mutate .` at **2 files / 44 mutations / 0 survivors**.

**Not run:** `test:integration`, `test:e2e` — no TypeScript changed.

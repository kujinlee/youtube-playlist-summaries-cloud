# Backlog #70 implementation — whole-branch review, round 1 (Claude half)

**Subject:** `origin/master..HEAD` on `feat/mutation-manifest-retarget`.
**Codex half:** [`branch-mutation-retarget-r1-codex.md`](branch-mutation-retarget-r1-codex.md).

⚠ **The gap this document declared is now CLOSED — see [§ The independent pass, arriving
late](#the-independent-pass-arriving-late) at the end.** As originally written this half was the
coordinator's own verification plus adjudication of Codex's findings, recorded as weaker than an
independent pass because the dispatched reviewer had not returned. It returned afterwards, measured
`d16dcd8` rather than the `e006604` it started on, and **reached CONVERGED**. The original text is
left unedited above that section; nothing in it was retracted.

**Verdict: NOT CONVERGED at first pass — 5 defects, 2 of them found by Codex against the
implementation. All fixed; re-review wanted.** → **CONVERGED** on the independent pass, with three
Medium and two Low items of coverage residue carried, none of them correctness.

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

---

## The independent pass, arriving late

Dispatched before the fixes above; returned after them. **It measured `d16dcd8`, not the `e006604`
it began on** — three commits landed under it mid-review — and it re-verified rather than assuming.
**Verdict: CONVERGED.** It independently reproduced the byte-identical extraction, confirmed via
`symtable` that the moved block has **zero free variables**, and controlled its own mutation sweep
with a no-op mutant that correctly survived.

It also confirms three findings were real at `e006604` and already fixed by `af7836e` / `6c7ab80`:
`gen-backlog-page.py --self-test` red on a `GROUPS` entry naming closed #70; `check-review-rounds.py`
red on a Codex half committed with no Claude half and no `REVIEW GAP:`; and the duplicate-manifest
hole (#5 above). **Note the second one: this branch turned that gate red exactly once, by filing a
lone review half — the same shape as the gap this document declared.**

### Residue carried — coverage honesty, not correctness

Three Medium, two Low. Verified by the coordinator before recording; none blocks the PR.

1. **Medium — six survivors exist that the manifest does not cover.** Each injected into the
   delivered file on a copy, then run through the full `--mutate .`: all six returned
   `rc=0, OK — 44 mutations, 0 survivors`. Two proven to change behaviour —
   `check-dashboard-entry.py:112` `probe[end+3:]`→`end+4` makes a valid `NO-ENTRY:` declaration
   return `None`, so the gate refuses it; `gen-dashboard.py:1156` `!=`→`==` inverts the three-way
   store distinction an adjacent comment says cost a round. Also `gen-dashboard.py:225` `or`→`and`,
   measured. Three more plausible, not individually proven.
   **Not a regression** — the same entries had the same holes against the plan's copy, so the branch
   weakens nothing. The problem is that a step named *"Mutation manifest against the delivered
   scripts"* prints a bare survivor count, which invites a completeness reading the manifest does not
   support. The docstring's *"it cannot prove the mutation list is complete"* needs to sit where the
   number is read. **DECISION OWED:** record the measured escape rate in the CI comment, or add
   entries for these classes. Not taken here — it is the user's call whether to spend it.
2. **Medium — the branch enforcing "every shipped manifest is declared" has no falsifier.**
   `check-plan-code.py:392`, `for target in sorted(set(counts) - set(EXPECTED_MUTATIONS))`. Replace
   with `for target in []:` and the suite stays **136/136**. Measured on a clean two-script fixture:
   branch deleted → an undeclared manifest runs and reports `OK — 1 mutation(s), 0 survivors`;
   branch present → `rc=1`. The case named *"the declared counts name every manifest that ships"* is
   **vacuous with respect to its own name** — `:1513`/`:1515` compare against a hardcoded list and
   `sum(...) == 44`; neither reads `scripts/mutations/`. **This is backlog #69's shape exactly**, and
   was already carried as residue before the independent pass confirmed it.
3. **Medium — three dead commands in the plan. ✅ FIXED in this commit.** Steps 5 (`:384`) and 5a
   (`:415`/`:418`) told a reader to run `--compare .`, which at `d16dcd8` exits **1**: the tagged
   blocks it assembled from were deleted. Verified by running it. Both steps are now marked RETIRED
   in place, pointing at `--mutate .`; the surrounding reasoning is kept as the record of *why*
   `--compare` existed, since `--mutate` inherits it.
4. **Low — `--mutate` returns only 0/1** (`:1569`), so no-manifests, missing-dir and a **control
   timeout** are indistinguishable from a survivor — in the one mode CI runs, in a file built around
   `rc=2` being a distinct CANNOT-RUN.
5. **Low —** a red control is labelled `CANNOT RUN — … exited 1` with an empty detail tail.

**Retracted by the reviewer itself:** it initially flagged `unresolved`'s `and`→`or` as a seventh
survivor, then measured it on three fixtures and dropped it as an **equivalent mutant** — ids are
unique per block, and pass 2 already errors on any resolver naming a malformed id.

### Also verified sound by the independent pass

Coverage cannot shrink, checked by execution rather than reasoning: manifest **deleted** → `rc=1`
*"holds 0 mutation(s), expected 32"*; **renamed** → `rc=1` *"target … does not exist"*; **all
manifests gone** → `rc=1` CANNOT RUN; **entry swapped for a duplicate** (count preserved) → refused
at `d16dcd8`. The `try/finally` around `EXPECTED_MUTATIONS` (`:1483`–`:1511`) has no corruption path:
`case()` cannot raise, and the two trailing cases sit after the restore. The 2,128-line deletion left
nothing structural — `check-docs` and `check-anchors` pass and every inbound reference resolves.

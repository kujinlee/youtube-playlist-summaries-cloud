# Round 2 — `586-slice1` — coordinator — Codex NOT CONVERGED; the route changes to REDESIGN

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: PR #557 (DRAFT), branch `586-slice-1-strace`, the round-1 fold (`37db4e63`, `4c9a6fa0`) reviewed by Codex at
head `cfa09bb1` in `docs/reviews/codex/586-slice1-r2-codex.md` (1 High, 3 Medium, 1 Low). The fold is `19d6de5e`.

```yaml
round: 2
fixes_nontrivial: true
subject: 586-slice1
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: strace-merge, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: strace-fixtures, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: true, component: strace-fixtures, disposition: fixed}
  - {id: X5, severity: Low, aim: deliverable, fix_induced: true, component: strace-reader, disposition: fixed}
```

## The route change — accrete LOST, the class is removed

The round-1 bet (decision log, `586-slice1`, route `accrete`) was that round 2 would find no BLOCKER/High and nothing
fix-induced. It found one High not caused by the fold and four that were. It is recorded `continued` with that
observation, and a new prospective row takes route `redesign`.

X1 is the SECOND round in a row where creation-provenance EXEMPTION hid an external removal (round 1: an `O_CREAT`
open counted as creation; round 2: evidence that outlived the object it described). Each round patched the evidence
rule, and each patch left the exemption's failure mode in place: an imperfect provenance rule makes a removal vanish.
The redesign removes the exemption, not the rule's next hole:

- **Nothing outside the copy is exempted.** Every `unlink*`, `rmdir` and `rename*` (source AND destination, which it
  replaces) whose path resolves outside the copy is LISTED. Unresolved removals stay unresolved, as before.
- **`created_in_log` is an annotation.** Each listed removal carries it, from the round-1 evidence rules. Nothing is
  filtered by it, so a wrong annotation mislabels a removal and can no longer hide one.
- **Codex's invalidation still applies, to keep the annotation honest:** a successful removal, a rename's source and a
  replaced destination clear the evidence for that path and its subtree. A path under a created directory is now
  annotated as a created FILE (its kind is unknown), so renaming it never claims a whole subtree.
- **Counts are whole, by annotation** (`external_removal_counts`); the per-record list keeps 500 not-created and 50
  created entries. `--merge` lists each target's paths by annotation and totals them (`external_removal_totals`),
  null unless EVERY record was annotated (X2's lesson applied to the new field).
- **Slice 2 decides its refusal rule from the list.** The instrument no longer decides which removals are harmless.

## X1 (High, not fix-induced) — stale creation evidence exempted a removal

Codex's four lines (`mkdir d; rmdir d; rename /t/preexisting -> d; unlink d/valuable`) are a case; on the round-1
reader they listed nothing. Now: `d` (rmdir) created, `d` (rename destination) NOT created, `d/valuable` NOT created.
Codex's variant (the created directory moved away instead) and a pre-existing file renamed onto a created file's name
are cases too, and a case asserts the counts by annotation (1 created, 2 not). Six X1 cases were red on the round-1
reader; with the fix's `forget` call reverted, four go red again.

## X2 (Medium, fix-induced) — one measured record made the merge read as measured

Codex's `_merge([[a, b]])` (a measured, b not) is a case: it returned `{}`, now `null`. `--merge` counts, per
(target, seed) record, whether `unpaired_halves` was measured, reports `unpaired_halves_coverage`
(`{"measured": 1, "records": 2}` for that input) and gives the per-target map only when every record measured it. A
case checks that a fully measured merge with nothing unpaired still reports `{}`. Reverting to "any record measured"
makes Codex's case red.

## X3 (Medium, fix-induced) — the sample case supplied the only sample it checked

New case: from an EMPTY sample store, one unlink line as `second.py` must store `{line, target: "second.py"}` under
`("unlink", "= N")`. Codex's two mutations, re-applied on a temp copy: `samples[...] = …` → `pass`, and the owner →
`"wrong"`. Both now go red (53/54). The preservation case stays. `check-fixture-variation`'s
`strace-measure.py:analyse_log.samples` exemption now names this case and the mutations it kills.

## X4 (Medium, fix-induced) — the two-directory case's answer came from the last directory

New cases over the same two directories: `spawner_targets` must be `["a.py", "b.py"]` and `shards_present` `[1, 2]`.
Codex's mutation (`for d in dirs[-1:]`) re-applied: both go red (52/54). The old case (`trace_factor` 7) is kept and
relabelled as NOT proof both directories are read. The `merge.dirs` exemption now cites the `r2 X4` cases.

## X5 (Low, fix-induced) — an unfinished half survived its pid's exit

At `+++ exited` or `+++ killed`, the pid's pending half is orphaned (counted unpaired, and unresolved if a remover).
A later `<... resumed>` on that pid then pairs with nothing and is unpaired on its own. Codex's three lines are a
case for both exit shapes: no removal, 2 unpaired, 2 unresolved (on the round-1 reader: `/external/victim`
fabricated, 0 and 0). Reverting the exit handling makes both red.

## The self-test

54 cases (37 + 17). 13 of the new ones were red on the round-1 reader; the 4 others (X3, X4, and the fully-measured
X2 control) are green on it by construction, and their red is the mutations above.

## The measurement run on the fold

Run **42915171820** (head `19d6de5e`, six shards, all green) re-measured with the listing reader:
**0** removals outside the copy annotated not-created, **63,720** annotated created, every one of 184 (target, seed)
records annotated; `unpaired_halves` measured on all 184. Syscall union (118), ioctls (7), strace 6.19, refusal
triggers and the 28 unresolved-removal targets match run 42893595762, so no constant moves. Its worst spawner ratio
(`scripts/regen-pages.py`, 14.18) adds a ceiling of 15 to the `TRACE_FACTOR` table; the max stays 20. Figures in
`docs/reviews/measurements/2026-11-10-strace-on-runner.md`, JSON `…-run3.json`.

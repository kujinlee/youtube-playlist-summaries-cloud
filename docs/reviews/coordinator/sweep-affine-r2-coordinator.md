# Round 2 — `sweep-affine` (backlog #588, PR #590) — coordinator — ⟳ NOT CONVERGED (Codex); all folded

REVIEW GAP: claude — alternation: round 2 runs ONE half (`review-method.md` → *Round topology*), and it went to Codex.

```yaml
round: 2
fixes_nontrivial: true
subject: sweep-affine
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: cost-partition, disposition: fixed}
  - {id: X2, severity: Minor, aim: deliverable, fix_induced: true, component: cost-partition, disposition: fixed}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
```

Codex reviewed `d62d6c4f` (`docs/reviews/codex/sweep-affine-r2-codex.md`, filed in `89607419`). Every new case was
written first and seen RED against the unfixed code before its fix: `check-plan-code.py` 480 → 486 cases (481/486
with the old behaviour stubbed in), `sweep-costs.py` 26 → 28 (27/28, all four long counts `RAISED`).

- **X1 (Codex 1, MAJOR, not fix-induced) a bound per unpriced target is not a bound on what one shard holds of
  them.** `cost_coverage` checked each unpriced target against one shard's share; two of them, 95 entries each, sat
  together in one contiguous shard estimated at 100 s that really took 2,000 s. Fix, `sweep_partition`: the PRICED
  entries are cut by cost (`_cost_cut`, the old body), the UNPRICED ones are DEALT round-robin over all N shards,
  starting at the first shard the priced cut left empty. No shard holds more than `ceil(unpriced / N)` of them
  whatever they cost, which is round-robin's own exposure. The 95% floor and the per-target clause stay, as the
  floor on when a table is worth cutting by. Case, Codex's input verbatim: "⭐ r2: several UNPRICED targets cannot
  sit together in one shard — …" (before: 100 unpriced in one shard, 2,000 s real; after: 5, and 195 s).
  ⟳ **The ordering property that changed:** with unpriced entries present the shards are no longer one contiguous
  cut. Joined end to end they are a permutation of the manifest list, not the list. Each shard still lists its
  entries in manifest order, every entry is in exactly one shard, every shard computes the identical partition, and
  no shard is empty while there are at least N entries. With no unpriced entry (the committed table prices all 96
  targets) the partition is unchanged: on `d62d6c4f`'s manifest the old and new code give the same 38 shards
  (5,172 entries, slowest 753 s).
- **X2 (Codex 2, MINOR, FIX-INDUCED by the r1 fold's `cost_coverage`) coverage was approved against the whole
  manifest while a pull request cuts its diff-selected pool.** One function now names the pool and one judges it:
  `sweep_pool(muts, select)` and `sweep_plan(root, muts, select, total)`. The run (`mutate_delivered`) and `main`'s
  PARTITION line both go through `sweep_plan`; `partition_line`'s target count is the pool's too. Cases: "⭐ r2:
  sweep_plan judges coverage on the SELECTED pool — …", "⭐ r2: main() judges the table against the SELECTED pool —
  …", "⭐ r2: ...and the RUN partitions that pool by the same table — …".
- **X3 (Codex 3, MINOR, not fix-induced) a 4,301-digit count crashed.** Python refuses to convert an integer string
  over 4,300 digits with a plain `ValueError`, which `_env_count` did not catch. `_count` in `scripts/sweep-costs.py`
  refuses a value that is not ASCII digits or is over `COUNT_DIGITS` (9) long, as `Refused`. Case: "⛔ r2: a
  4,301-digit count — env block or verdict line — is a REFUSAL naming the count, never a crash", and its positive
  twin for 9 digits.

**Also folded, found by this fold's own mutation run.** Dealing unpriced entries makes a table that prices NOTHING
partition exactly as round-robin does. That left two existing #588 mutations with nothing to tell them apart from
the code, and a third red with no `[FAIL]` line: (1) "the run reads the table without the coverage rule" SURVIVED,
because its case compared only the control lines; the case now also names which of `other`'s two mutations shard 1
ran. (2) "with no table the shard is NOT round-robin" used an all-unpriced table; it now substitutes `_cost_cut`,
the contiguous cut it always meant. (3) "the cut takes the FAILING cap" raised `IndexError` in the new code;
`sweep_partition` now returns the extra shard, so the named case fails by comparison.

**Same-class search.**
- *A per-item bound standing in for an aggregate bound.* The dealt entries are bounded by COUNT per shard, not by
  time: stated in `sweep_partition`'s docstring, and it is what round-robin gives. `SWEEP_COST_MAX_S` bounds each
  row to a day and nothing bounds their sum, but costs are integer milliseconds and nothing depends on the sum
  being small. `suite_limit` is per suite; the shard's total is `budget_spent`'s. No second defect.
- *A check run on a different population than the one acted on.* ONE more, fixed here: `partition_line` counted
  the whole manifest's targets beside a cut of the pool. Traced and ruled out: `shard_refusal` runs only when there
  is no selection (pool = manifest); `sweep-costs.py`'s `shard_holding` judges the whole manifest, and `parse_log`
  refuses a selected run, so it never reads a pool.
- *An `int()` of unbounded input.* ONE more, fixed here: the VERDICT line's two counts in `parse_log` went through
  a bare `int()`; they now use `_count`. Already bounded: `SHARD_SPEC` and `ci_deadline` (their patterns cap the
  digits), `parse_sweep_costs` (catches `ValueError`). ⚠ NOT FIXED, outside this diff, in `check-plan-code.py`:
  `--seeds` (`p.isdigit() or int(p) > SEED_MAX`: an over-long or non-ASCII-digit seed raises), and the `int()` of a
  suite's own summary count and docstring count. Each reads the operator's flag or this repository's own files.

**Mutations.** check-plan-code 353 → 360 (7 added; 5 re-bound: the #330 selection, the run's table read twice,
main's PARTITION print, the no-table fallback), sweep-costs 27 → 29 (2 added;
2 re-bound). All 61 #588 entries (32 in check-plan-code.json naming #588, all 29 of sweep-costs.json) applied one at
a time, after the final edit, to staged copies outside the repository (control 486/486 and 28/28) through
check-plan-code's own `run_mutations`: **61/61 KILLED, each by its named case, 0 survivors, empty report.** The
re-bound #330 entry, which does not name #588, was run the same way and is killed by its case. Anchor resolve over
all 96 manifests: 5,181 mutations, 5,218 anchors, each found exactly once, no duplicate edit tuples.
Every one of the 5,181 mutations applied and compiled: 0 do not parse.

**Bounds.** The deal bounds the COUNT of unpriced entries a shard holds, never their time: one unpriced target
whose mutations are each very slow is spread evenly, and still slows every shard. A dealt target adds its control
and re-control to each shard it reaches; with at most 5% of entries unpriced that is at most
`ceil(unpriced / N)` extra targets per shard. Predicted with the committed table on this tree (5,181 entries,
96 targets, none unpriced) at N=38: slowest shard 758 s, fastest 716 s; round-robin by the same model 1,213 s.

**Bet for round 3 (one half, alternation):** r3 finds nothing caused by this fold in cost-partition. The r1 bet
(nothing caused by the r1 fold) LOST on X2.

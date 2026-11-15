# Round 1 — `sweep-affine` (backlog #588, PR #590) — coordinator — ⟳ NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: sweep-affine
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: X2, severity: Minor, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: X4, severity: Minor, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: X5, severity: Minor, aim: deliverable, fix_induced: false, component: cost-partition, disposition: fixed}
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: cost-partition, disposition: fixed}
  - {id: CM2, severity: Minor, aim: deliverable, fix_induced: false, component: cost-partition, disposition: fixed}
  - {id: CM3, severity: Minor, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: CM4, severity: Minor, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: CM5, severity: Minor, aim: prose, fix_induced: false, component: cost-partition, disposition: fixed}
  - {id: CM6, severity: Minor, aim: deliverable, fix_induced: false, component: cost-partition, disposition: fixed}
  - {id: CN1, severity: Nit, aim: deliverable, fix_induced: false, component: cost-partition, disposition: fixed}
```

Both halves reviewed `4565f2b2` (Claude filed at `066dabed`, Codex at `7e0e6c35`). Folded in `03e87843`
(`scripts/sweep-costs.py`) and `93c0a988` (`scripts/check-plan-code.py`, the table, manifests, docs). Every new case
was written first and seen RED against the unfixed code before its fix: `sweep-costs.py` 16 → 26 cases (26/26),
`check-plan-code.py` 472 → 480 (480/480; 7 seen red with stubs, the exact-partition case passes on both because it
pins behaviour the review called under-pinned, not a defect).

- **X1 (Codex 1) a run's completeness counted shards, not their identities.** `parse_log` refuses an index outside
  1..total (index 0 was read by negative indexing as the LAST shard), a missing EVENT and a `schedule` run (two hash
  seeds, CM4's half too); `run_identity` refuses two totals, two events, a duplicate and a gap, so a run is exactly
  {1..total}. Case: "⭐ r1: a run must hold shards 1..total exactly once — …".
- **X2 / CM4 (prefix label)** `attribute` compares each progress line EXACTLY against the line `progress_line` renders
  at that position (control, mutation, re-control). Fixture re-cut the way `progress_line` cuts at the trimmed width.
  All 76 real shard logs of both runs still attribute (5,089 + 5,068 mutations).
- **X3 (backwards clock)** a negative gap is refused; `write_table` re-parses the built table through check-plan-code's
  own `parse_sweep_costs` and never writes one it would refuse.
- **X4 / CM3 (crash, not refusal)** `_env_count` and `_secs` turn a malformed count or date into `Refused`; `main`
  catches it (rc 1, `REFUSED — …`).
- **X5 (1e308, non-UTF-8)** `_cost_number` bounds a cost to `SWEEP_COST_MAX_S` (a day), so `* 1000` cannot overflow;
  `load_sweep_costs` returns `(None, reason)` on `UnicodeDecodeError`.
- **CM1 (a table that parses but no longer fits)** NEW RULE, `cost_coverage`: the table is refused, and the run falls
  back to round-robin LOUDLY, when it prices fewer than 95% of the manifest's entries, or when one uncosted target
  holds more entries than one shard's share (`ceil(len/N)`) — the reviewer's worst cases (a renamed costliest target,
  3,216 s; keys without `scripts/`, 2,280 s) both trip it. `sweep_costs_for` = load + this rule, called by both the
  run (`mutate_delivered`) and `main`. Unknown targets are now priced at the p90 defaults, not the median. The
  committed table carries a hand-priced row for `scripts/sweep-costs.py`: ⚠ a NEW target has no CI sample until it
  merges, so a PR adding a big new suite can trip the share clause on its own sweep and fall back — loud, and correct.
  Cases: the coverage unit cases, `sweep_costs_for`, the call-site case through `mutate_delivered`, and "the
  COMMITTED cost table loads and costs EVERY target this repository's manifests mutate".
- **CM2** under `GITHUB_ACTIONS=true` the fallback also prints `::warning title=sweep partition::` on stdout. Case
  pins it on and off.
- **CM5** the docs compare model with model: 1,218 s round-robin → 753 s cut at N=38 (5,172 entries), ~1.6x; fixed
  cost 38–41% of a shard's work; the 1,438–1,611 s job wall clocks are labelled as such. Dashboard entry, backlog #588
  row, both ci.yml comments, the check-plan-code block comment.
- **CM6** an exact hand-worked partition case (3 targets, N=3, estimates [13000, 12000, 5000]).
- **CN1** the nested 9/9 `main()` call's stdout is captured.

**Same-class search.** Identity-vs-count, prefix compares, uncaught parse errors, `* 1000` overflow, and readers of
the table that skip the coverage rule, over both scripts. One candidate traced and ruled out: `VERDICT.match(verdict)`
cannot be `None`, since `verdict` is assigned only where that regex matched. `--shard I/N` already refuses
`not 1 <= index <= total` (`shard_refusal`). `sweep-costs.py`'s `shard_holding` reads `load_sweep_costs` only for an
OLD run tree that has no `sweep_costs_for` — it reproduces what that tree ran. No new instance.

**Mutations.** check-plan-code 346 → 353 (7 added; the NEGATIVE-bound and run-reads-table entries re-bound),
sweep-costs 13 → 27 (14 added; idx, the NAME / control / re-control TARGET and fixed-default entries re-bound).
All 52 #588 entries (25 in check-plan-code.json naming #588, all 27 of sweep-costs.json) applied one at a time to
temp clones of `93c0a988` outside the repository (control 480/480 and 26/26) through check-plan-code's own
`run_mutations`: **52/52 KILLED, each by its named case, 0 survivors, empty report.** The first pass found ONE
defect in the manifest, not the suite: the timestamp entry replaced only the PREFIX of its line, so the comment's
tail was left after `except KeyError as exc:` — a SyntaxError (U+2026), red with no `[FAIL]` line, which the
harness rightly called unattributable. The replacement now keeps the comment marker; re-run 27/27. Same class
over EVERY manifest: each Python mutation applied and compiled — 0 do not parse (control: the old entry does
not). Anchor resolve over all 96 manifests: 5,209 anchors, each found exactly once, no duplicate edit tuples.

**Bounds.** `tabulate`'s ORDER (identity before attribution) and its refusal of a run tree with no `progress_line`
have no dedicated case.

**Bet for round 2 (one half, alternation):** r2 finds nothing caused by this fold in cost-partition or
cost-table-builder.

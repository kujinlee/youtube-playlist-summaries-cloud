Reviewed head: de1bbf59425615877f1ef0cd4ad924fc53f47526

# usage-hook-master r5 — Claude half (HEAD de1bbf59, sweep-costs re-price of check-run-hook.py)

Scope: one commit editing scripts/sweep-costs.json (control/recontrol 1.975/1.942 -> 52, mutation 1.921 -> 42, one `sources` entry appended).

## Findings

### MINOR 1 — stale `samples`/`mutations` counters on the re-priced row
scripts/sweep-costs.json, row `scripts/check-run-hook.py`: still `"samples": 36, "mutations": 36` while the prices now come from a different measurement (34 mutations from one CI job). Nothing reads them for the partition (parse_sweep_costs reads only control/recontrol/mutation; sweep-costs.py:252 writes them on regeneration), so no failing input exists; it is provenance noise only. The sources entry does say "the 36 samples predate...", so the history is recorded.

### MINOR 2 — the price is a mean over a bimodal cost; the plain mean is right for a partition but the tail is 52 s
Per-mutation gaps of the 34 timed check-run-hook mutations are 25.0-25.6 s (11 of them) or 51.0-52.2 s (23); mean 41.65 s. A shard of 20 such mutations estimates 944 s and can really take 500-1040 s; the budget is 1680 s, so no failing input exists. Pricing at the mean is correct for a balance; the worst case (all 52 s) is still inside the budget.

No BLOCKER or MAJOR found.

## Evidence

1. Log (s17.log). Sweep started 09:42:08; mutations 1-147 (other targets) took 151.8 s in total (max 1.6 s each). Mutations 148-182 are check-run-hook.py (47 manifest entries; 35 reached, matched by name against scripts/mutations/check-run-hook.json; 36th ran out: "STOPPED after 2.6s, when this run's time budget ran out"). The "Not reached (115)" list begins with 12 more run-hook entries, then other targets. Control: `[4/8] control scripts/check-run-hook.py` 09:41:00.25 -> `[5/8]` 09:41:52.21 = 51.96 s (supports 52 s control; recontrol assumed equal, it runs the same suite). Mutation gaps for the 34 complete ones: mean 41.65 s, 23 x ~51.8 s, 11 x ~25.3 s. So 42 s is supported (not too low, not too high); 52 s control supported. The 1.9 s price was stale by ~22x. The claim in the commit message (1416 s, 34 mutations, 41.7 s) re-derives exactly (34 x 41.65 = 1416).
2. Loaders. `python3 scripts/sweep-costs.py --self-test` -> `36/36 passed`. `python3 scripts/check-plan-code.py --self-test` -> `506/506 passed`. `load_sweep_costs(pathlib.Path('.'))` on the edited file returns reason `None`, targets['scripts/check-run-hook.py'] == (52000, 52000, 42000), 15 sources. Validation (check-plan-code.py ~1693-1710): schema == 1, defaults, `sources` a non-empty list of str, each row's control/recontrol/mutation pass `_cost_number` (0..SWEEP_COST_MAX_S=86400); 52.0 and 42.0 pass.
3. Partition. `_cost_cut` (check-plan-code.py:1847) is a contiguous cut over ITEMS (each mutation weighs its own cost), not over targets: "BOUND ... no run's estimate exceeds T/total + max(c + f) + max(f)". Nothing keeps a target's entries together, so 47 x 42 s = 1974 s > 1680 s cannot be forced into one shard; entries are split at item granularity (`_greedy_cut(muts, weights, cap)` with a bisected cap, then `_best_split`). I ran `sweep_partition(load_manifests('.')[0], 38, costs)` on the committed tree (6245 mutations): slowest shard estimate 950.4 s; run-hook is spread over shards 19 (20 muts, est 944 s), 20 (20 muts, 944 s) and 21 (7 muts + others, 945 s). Each is far under 1680 s, even at the all-52 s worst case (20 x 52 + 104 = 1144 s). Caveat: I did not reproduce the diff-scoped 89-manifest selection of PR #610; the bound above holds for any list, and the cost-table price is what moves.
4. Pins. grep for 1.921/1.942/1.975 across scripts, .github, .claude: no hits. No test asserts the `sources` length (self-tests above pass with 15). `samples`/`mutations` are only written by sweep-costs.py:252, never read by the partitioner. Working tree clean (git status) apart from this file.

VERDICT: CONVERGED

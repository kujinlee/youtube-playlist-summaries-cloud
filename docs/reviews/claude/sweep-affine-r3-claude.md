Reviewed head: 2114eae50ca7948d672c3b4d98f2587c3933db58

# sweep-affine-shards — round 3, Claude half (backlog #588, PR #590)

REVIEW GAP: codex — alternation: round 3 runs ONE half (`review-method.md` → *Round topology*), and it went to Claude.

```yaml
round: 3
subject: sweep-affine
halves:
  claude: ran
  codex: gap
findings:
  - {id: C3-L1, severity: Low, aim: deliverable, fix_induced: true, component: cost-partition, disposition: filed-or-fold}
```

**Range:** the r2 fold `d62d6c4f..2114eae5` (`sweep_partition` / `_cost_cut`, the deal of unpriced entries,
`sweep_pool` / `sweep_plan`, both call sites, `partition_line`, `sweep-costs.py` `_count` / `COUNT_DIGITS`,
the new cases, the mutation manifests, ci.yml and backlog #588 text), read against the whole change
`origin/master...HEAD`. Read first: r1 / r2 coordinator documents and `docs/reviews/codex/sweep-affine-r2-codex.md`.

**Method.** Every claim marked EXECUTED was run against the worktree's own modules through `importlib`,
or on a **temporary copy outside the repository** (`git archive 2114eae5`) for the mutations. No file in the
tree was changed except this review and its verdict.

- EXECUTED: `python3 scripts/check-plan-code.py --self-test` → `489/489 passed`, rc 0.
- EXECUTED: `python3 scripts/sweep-costs.py --self-test` → `32/32 passed`, rc 0.
- EXECUTED: `python3 scripts/check-fixture-variation.py` → rc 0, `fixture variation OK — 2307 parameter(s)
  examined across 102 file(s)` (its three "now varies" notes name `brief-compose.py` and `codex-review.py`,
  outside this diff).
- EXECUTED: the r2 partition, driven with hand-built inputs (each asserting: exactly N shards, every entry
  exactly once, no empty shard when entries ≥ N, manifest order inside each shard, no shard over
  ceil(unpriced / N) unpriced entries, `sweep_shard(i) == sweep_partition()[i-1]` for EVERY i, and
  `shard_refusal` silent for every i). All HELD for:
  - all unpriced, 63 entries over N=7, which is also **identical to `shard_slice` round-robin**;
  - N > entries (5 over 10);
  - priced < N < entries, with the unpriced block AFTER and BEFORE the priced one (the deal start at the
    first empty shard);
  - priced == N with U ≥ 1, priced == N−1 with U = 1 (entries == N) and U = 2;
  - all unpriced, entries = N + 1;
  - 400 random lists (1–6 targets, 1–40 entries each, ~60% priced, random costs incl. zeros, N 1–45).
- EXECUTED: the stated BOUND, 1,500 random lists (1–8 targets, N 1–40): every shard's PRICED part stays
  within `T_priced/N + max(c+f) + max(f)`, and every whole shard within that plus `ceil(U/N)` × (default
  mutation + default fixed). 0 violations.
- EXECUTED: the committed tree at 2114eae5: 5,181 entries, 96 targets, `sweep_costs_for` approves the
  table, all 38 shard calls return the identical partition, no refusal. Estimated slowest / fastest shard
  758 / 716 s; round-robin by the same model 1,213 s; the bound 827 s. These equal the r2 coordinator's
  numbers.
- EXECUTED: `sweep_plan` on Codex's r2 input, selecting {b, c} (refused, share 5) and {a, b} (approved,
  `1 of 2 target(s) costed … the rest dealt round-robin`), and `partition_line` on each.
- EXECUTED: five r2 mutations, one at a time on the temp copy — see *Mutation re-run*.
- UNVERIFIED: real CI wall-clock under the new partition; only the model was compared.

---

## C3-L1 — LOW — the per-target coverage refusal still gives the PRE-r2 reason, and calls a selected pool "the manifest"

`scripts/check-plan-code.py` `cost_coverage` (the two `return` strings, ~1698–1705). **Fix-induced: yes**, by
the r2 fold, component **cost-partition** (coverage). Two halves of one wording defect:

1. The per-target reason reads *"priced at the defaults, its block would unbalance a shard"*. After r2 that
   mechanism no longer exists: `sweep_partition` never prices an unpriced entry for placement and never keeps
   its block together — it DEALS it. The r2 docstring says the clause "stays as the conservative floor", but
   the text it prints still justifies itself by the removed mechanism.
2. r2 made `muts` the POOL (`sweep_plan`), but the 95% reason still says *"prices X of Y manifest entries …
   it no longer fits the manifest"*. On a pull request the count is the selected pool's.

**Breaking input (EXECUTED):** Codex's r2 manifest (3,610 priced `a`, 95 each unpriced `b`, `c`), a table
pricing `a`, `sweep_plan(root, muts, {b, c}, 38)` →
`scripts/b.py holds 95 entries the table does not price, over one shard's share of 5: priced at the defaults,
its block would unbalance a shard`, printed by `partition_line` as the ROUND-ROBIN FALLBACK reason. Neither
statement is true of the code that runs.

**Impact:** an operator reading a fallback annotation is told the wrong cause. No partition, coverage or
measurement is wrong; the fallback itself is still loud and correct. In this repository the committed-table
case (every manifest target has a row) keeps the refusal from firing on a real run today.

**Fix (text only):** say what the clause now is — e.g. *"holds N entries the table does not price, over one
shard's share of S: too much of the pool is unpriced to cut by the table"* — and "of the N entries being cut"
for the 95% reason. Pinned by the existing cases' substrings, which would move with it.

**Thrashing classification.** This is the second consecutive round with a fix-induced finding in the
cost-partition component (r2 X2 from the r1 fold; this from the r2 fold), so by the letter of
`dev-process.md` it meets the arming condition. ⚠ Read for weight: it is a stale MESSAGE left behind by a
correct structural change, not a behaviour defect caused by it; every property of the r2 partition and pool
I could construct held. The coordinator decides whether a Low wording finding arms Phase 6.

## Checked and NOT a defect

- **`first = nonempty runs % N`** assumes empties are only at the tail. True: `_cost_cut` leaves empties
  only on its `len(muts) <= total` branch, and that branch puts them last; on the other branch `_greedy_cut`
  never closes an empty run and the split loop splits only runs of two or more. With priced > N, `first = 0`.
- **No empty shard** while entries ≥ N: when priced < N, the unpriced count is > N − priced, so the deal,
  starting at shard `priced`, fills every empty one before it wraps.
- **The deal bounds COUNT, not time** — stated in the docstring and the coordinator's *Bounds*, and it is
  round-robin's own exposure. Not a defect; it is the claim made.
- **`sweep_plan` in both callers** reads the same `select` (`main` computes it once and passes it to
  `mutate_delivered`); `shard_refusal` runs only with `select is None`, where pool = manifest and the
  costs are the same object `shard_refusal` is handed.
- **`sweep-costs.py` `shard_holding`** calls the run tree's own `sweep_costs_for` over the whole manifest,
  which is what a full run's `sweep_plan(…, None, …)` judges; `parse_log` refuses a selected run. A
  non-contiguous shard is fine for `attribute`: it reads the shard's own list order, which is the order
  `mutate_delivered` runs (`shard_muts`).
- **`_count`**: `[0-9]+` refuses Unicode digits a bare `\d` + `int()` used to admit (safe direction); 9 digits
  is read, 10 refused; leading zeros count toward the 9 (harmless for a shard count).
- **Docs, like for like.** backlog #588, the dashboard entry and the module comment state 1,218 s → 753 s,
  both MODEL figures on the same 5,172-entry manifest; the r2 coordinator's 1,213 → 758 s is the same model
  on today's 5,181 entries (re-derived above). Each pair is model against model, and the measured wall
  clocks (1,438–1,611 s) are labelled as a different basis. The ci.yml comment's `ceil(unpriced / N)` matches
  the code. ⚠ Minor omission, not filed: the dashboard entry's tech paragraph names the r1 coverage rule and
  not the r2 deal.
- **Observation, not a defect:** `sweep-costs.py` `predict()` calls `sweep_partition` directly, skipping
  `cost_coverage`, so `--predict` models a cost cut even for a table the run would refuse. Pre-existing
  (since the build, `4565f2b2`), not caused by r2.

## Mutation re-run (temp copy, outside the repo)

Control on the copy: `check-plan-code.py` 486/489 — the 3 reds are all `node_modules/typescript` missing from
a `git archive` (HARNESS_TREE), none a #588 case; `sweep-costs.py` 32/32. A mutation counts as KILLED only
when the case its manifest `expect` names is among the `[FAIL]` lines.

| mutation (r2, manifest name abridged) | self-test | named case red? |
|---|---|---|
| the deal starts at shard 1, so a shard can be empty | 485/489 | **KILLED** |
| a shard lists dealt entries after its priced ones | 485/489 | **KILLED** |
| the run asks for the whole manifest's plan, cuts the pool | 485/489 | **KILLED** |
| unpriced entries cut by their estimate with the priced ones | 484/489 | **KILLED** |
| `sweep-costs.py`: the verdict line's counts read by a bare `int()` | 31/32 | **KILLED** |

5/5 killed, each by its named case (the extra reds beyond the 3 environmental ones are the named case and, for
the last check-plan-code row, one more #588 case).

## Verdict

One LOW finding (C3-L1), fix-induced wording in the coverage refusal. No Blocking, High or Medium. The r2
fold's structural claims held under every input I could construct: one partition, identical in all 38 shard
calls, each entry once, no empty shard, manifest order inside a shard, the unpriced count bound, the cost
bound, and coverage judged on the pool in both the run and `main`.

VERDICT: CONVERGED

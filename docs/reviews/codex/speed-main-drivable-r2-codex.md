<!-- codex-review: model=gpt-6-astra -->

- **Minor — LRU test passes for an ambient reason**, `scripts/check-main-drivable.py:4550–4563`. **Fix-induced: yes.** Replacing eviction with `del memo[list(memo)[1]]` survives **445/445**. Concrete input: insert 65 distinct trees into a fresh memo; the mutant retains the oldest and evicts the second-oldest. Earlier suite entries mask this defect: the fold’s test fails with an empty memo but passes with one unrelated prior entry. **Fix:** use a fresh memo and assert exactly which entry the 65th insertion evicts; register this mutant.

- **Minor — capacity boundary is unpinned**, `scripts/check-main-drivable.py:353,4562`. **Fix-induced: yes.** Changing `>` to `>=` survives **445/445**. Concrete input: insert 64 distinct trees; the mutant retains only 63 and rebuilds when queried for the first. The assertion accepts any size `<= 64`. **Fix:** assert 64 retained entries and cache hits before overflow, then eviction on entry 65; register the boundary mutant.

No stale answer reproduced: **68,698 cached-versus-uncached comparisons**, including **573 reused tree addresses**, found zero differences.

Median-of-three timings, Python 3.12, alternating versions over the same working-tree population under heavy concurrent load:

| Comparison | Suite: base → HEAD | CI-shaped live: base → HEAD |
|---|---:|---:|
| Uncached `c6bef051` | 179.87 → 21.52 s | 139.98 → 10.78 s |
| Pre-fold `dc462242` | 18.84 → 20.65 s | 13.70 → 13.92 s |

Live output was identical. The cap preserves most of the speedup.

Both requested commands completed in the foreground: **445/445 self-tests passed; 194 registered mutations killed and attributed, zero registered survivors.** The two additional survivors above refute the recorded bet.

**NOT CONVERGED**

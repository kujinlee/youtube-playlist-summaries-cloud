<!-- codex-review: model=gpt-6.1-sol -->

- **F1 — LOW — New MEASURED mean is incorrectly rounded.** `docs/backlog.md:257` and `docs/dashboard-entries.md:19640` report **1,048 s**. Computing `completedAt - startedAt` from `gh run view 42660040212 --json jobs` gives **1,048.894736842 s**, which rounds to **1,049 s**. **Fix:** use 1,049 s or 1,048.9 s in both locations.

- **F2 — LOW — The fold incorrectly applies aggregate control growth to every suite.** `.github/workflows/ci.yml:1223–1225` says “every flaky suite has ~37% more chances.” The aggregate counts reproduce exactly: **1,620 → 2,218 target-shard pairs**, or +36.9%. Individual targets range from **no increase to +58.3%**. For example, `check-ratchet-contract.py` remains on 16 shards; `check-reference-namespace.py` remains on 22. **Fix:** describe aggregate control-check exposure rising ~37%, with the increase varying by target.

The remaining round-1 corrections hold. The measured N=24 mean is **1,450.75 s**; the target counts, lifespan arithmetic, qualification of queueing, and revised close condition check out.

Run **42660040212** has **38/38 successful shards**, maximum **1,351 s** on shard 9, and **zero over 1,500 s**. Its overall conclusion is **failure** because `verify` failed; `mutation-sweep-complete` succeeded. The record honestly limits its green claim to the shards. Explicitly mentioning `verify` would improve clarity.

Both parents’ notes survived the merge without lost or garbled substantive text. The #231 row reads coherently because the superseded PR #549 note is marked **EARLIER**; both dashboard entries retain separate headers.

**Could NOT check:** independently reconstructing the per-entry timing model and 470 s floor from all 24 logs; account-wide competing workloads; future master or scheduled N=38 results. No files were written or GitHub mutations performed.

NOT CONVERGED

<!-- codex-review: model=gpt-6.1-sol -->

- **F1 — LOW — The two-wave claim needs narrower wording.** `.github/workflows/ci.yml:1219–1228`, repeated in `docs/backlog.md:257` and the dashboard entry. At N=38, a qualifying push launches **41 runner jobs**: 38 shards, `verify`, `schema-gates`, and the dependent `mutation-sweep-complete`. The arithmetic counts the 40 jobs preceding the completion check correctly, but does not prove that the entire run fits into two batches. Other repositories and overlapping runs also consume the account’s concurrency capacity. [GitHub documents this account-wide concurrency scope](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency). **Proposed fix:** describe “two waves of shard work on an otherwise idle account,” count the completion job separately, and qualify the claim that 38 is the largest permissible N.

- **F2 — LOW — The measured baseline uses a different timing boundary from its stated job-wall-clock evidence.** `.github/workflows/ci.yml:1217` says the measured N=24 mean is **1,447 s**. Averaging `completedAt - startedAt` over the 24 shards from `gh run view 42625034608 --attempt 1 --json jobs` gives **1,450.8 s**. The dashboard repeats 1,447 s. **Proposed fix:** use approximately 1,451 s, or explicitly identify the narrower timing boundary producing 1,447 s.

No N=38 correctness break found: all 4,505 entries partition into 38 disjoint slices of 118–119 entries; all indices parse; scoped empty shards explicitly pass; the aggregator and named consumers do not pin 24. The seven cited maxima and both shard-16 budget failures check out. Log reconstruction confirms approximately 23,014 s of mutation work and 11,067 s of controls/re-controls. Raising N buys headroom, while retaining the substantial per-shard floor.

**Could not check:** an actual full N=38 push or two-seed scheduled sweep, account-wide competing workloads, or the historical worst-spread survey exhaustively. No full mutation sweep or self-test suite was run.

NOT CONVERGED

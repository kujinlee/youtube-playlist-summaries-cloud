<!-- codex-review: model=gpt-6.1-sol -->

Review of `session-state` at `fb8ade4a`, mandate **REFUTE**. Repository unchanged; experiments ran in `/tmp/session-state-r4.89796n`.

1. **P1 — The new size cap causes successful ledger updates to erase recorded jobs.**  
   `scripts/session-state.py:151–152,189–196`

   An oversized ledger returns no entries or preserved bytes, only a warning. `ledger_add()` discards that warning and atomically replaces the original ledger with the new entry. Writes themselves have no size check, so supported commands create this condition.

   Executed through the real CLI:

   | Command | Exit | Ledger size |
   |---|---:|---:|
   | `--add running <65000-character description> done` | 0 | 65,070 bytes |
   | `--add cross-limit <1000-character description> done` | 0 | 66,144 bytes |
   | `--add new w d` | 0 | 64 bytes |
   | `--done new` | 0 | 0 bytes |

   Both previously recorded jobs disappeared without an error. Subsequent collection printed:

   ```text
   IN-FLIGHT LEDGER (.claude/inflight.jsonl): none RECORDED — it is written by hand …
   ```

   The manual-ledger qualification does not disclose that successful commands erased existing records. This is **fold-induced by the r3 size-cap fix**, and directly loses the stable-half bet.

   Refuse updates when the existing ledger cannot be read completely; reject an oversized replacement before replacing the original.

2. **P2 — Incomplete valid JSON becomes an affirmative “NO CHECKS.”**  
   `scripts/session-state.py:255–261` validates only that each object contains `number`. Rendering then treats a missing check rollup as an empty rollup.

   A fake `gh` returning exit 0 and:

   ```json
   [{"number":7}]
   ```

   drove the **registered shell hook** to print:

   ```text
   OPEN PRS (1):
     PR #7 `?` head  · ? · checks: NO CHECKS
   ```

   Likewise, `statusCheckRollup: {}` becomes `NO CHECKS`. Neither response establishes that no checks ran. Validate required fields and distinguish missing/unreadable check data from an answered empty rollup.

   This is fault-injection evidence; I did **not** establish that the installed `gh` naturally emits these incomplete responses. A nested numeric conclusion instead produced a traceback and the wrapper’s visible `CANNOT RUN` fallback.

The requested regression probes produced these results:

| Probe | Executed result |
|---|---|
| Ledger add/done race | 60 interleavings retained all 60 new jobs |
| Truncation window | Pausing before `os.replace()` left the previous ledger readable |
| Damaged JSON and invalid UTF-8 | Warnings persisted; damaged line bytes survived an update |
| FIFO through real hook | Immediate `NOT READ` warning; exit 0 |
| Unicode forgery | U+2028/U+2029/U+0085 and zero-width payloads stayed within their lines; one legitimate END marker |
| Unicode sweep | Every Unicode scalar tested; no surviving control/format/separator or added line |
| `gh` failure, invalid JSON, nonzero partial JSON, `[null]` | Visible `CANNOT RUN` |
| Real timeout | **30.18 seconds**, exit 0, “timed out,” complete END marker |
| Held-open hook stdin | **0.57 seconds**, exit 0; child received EOF |
| 100 PRs | Explicit `MAY BE TRUNCATED` warning |
| Same-named branches | Distinct PR numbers retained their own heads, mergeability and checks |
| Registered command from `scripts/` | Exit 127, no block; disclosed backlog #364 limitation |
| Self-tests / mutations | **36/36 passed; all 17 mutations failed their named cases** |

I queried GitHub’s live schema and exercised **all nine check conclusions, six check statuses and five status-context states**. `failing_names()` names every conclusion/state classified as failure. `STALE` remains explicitly `1 stale`, without a failing-name line; `COMPLETED` without a conclusion becomes pending. No omitted failure enum was found. [GitHub check definitions](https://docs.github.com/en/graphql/reference/checks#checkconclusionstate)

I found **no cross-PR attribution** in the exercised valid responses. The removed branch-reading path stays removed. A live run listed eight PRs and named failing checks under their respective numbers.

Documentation is **not wholly true**:

- The [PR body](https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/410) still promises that a failed `git fetch` is flagged as possibly stale. This implementation performs no fetch.
- Its ledger-preservation guarantee and the dashboard’s corresponding claim are contradicted by finding 1.
- The dashboard’s unconditional “Every new session” claim is contradicted by the executed subdirectory launch failure; the PR body and backlog #362 disclose that limitation.
- Backlog #362 correctly remains **IN REVIEW**. Rows #366 and #367 accurately describe the manual-capture gap and deferred attribution work.
- I executed the shell hook end to end, **not an actual Claude compaction**. The prior delivery-path evidence remains distinct from verification that this specific block arrives after compaction.

The SPLIT bet is lost on the stable half. Its precommitted next route is **DEFER**.

VERDICT: NOT CONVERGED

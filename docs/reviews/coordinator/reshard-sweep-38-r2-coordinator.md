# reshard-sweep-38 — round 2 coordinator (PR #550, backlog #231)

**Inputs.** `docs/reviews/codex/reshard-sweep-38-r2-codex.md` (Codex, head af8a5188). Claude alternated out.

REVIEW GAP: claude — alternation

| Finding | Disposition |
|---|---|
| Codex F1 LOW (the N=38 mean is 1,048.9 s, so 1,049, not 1,048) | Fixed in backlog #231's note and the dashboard entry. |
| Codex F2 LOW ("every flaky suite has ~37% more chances" applies an aggregate to each suite) | Fixed in `ci.yml`: ~37% more control runs in aggregate; per target the rise ranges from 0 to ~58%. Codex's suggestion to name `verify` is taken too: the #231 note says the run is red only on `verify`, and `mutation-sweep-complete` passed. |

**Confirmed by Codex.** The round-1 corrections hold (N=24 mean 1,450.75 s, target counts, lifespan arithmetic, the close
condition). Run 42660040212: 38/38 shards green, slowest 1,351 s (shard 9), none over 1,500 s. The merge of origin/master lost
or garbled no text from either side.

**Verdict.** NOT CONVERGED on LOW only; both LOWs are wording and are fixed here. **Stopped at round 2**: there is no finding
above LOW to re-review, and a third round would review two numbers. Decision-log row updated: `stopped`, 2 rounds.

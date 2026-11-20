<!-- codex-review: model=gpt-6.1-terra -->

- **MINOR — [scripts/mkt_seed_repo.py:283](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/agent-a7e79a4c4814b1c10/scripts/mkt_seed_repo.py:283):** The new absence check counts names without requiring them to be distinct. In a temporary copy, replacing all three entries in `ABSENT_RATCHETS` with `check-roadmap-consistency` produced a source naming that path three times, yet the self-test passed `14/14`. The other two ratchets were no longer represented in the fact. Fix-induced: yes.

The extra-token and missing-token source probes, a new wrongly sourced typed fact, and a tracked supposedly absent ratchet each failed the intended case. The condition 4 regrades agree with the cited outcomes. The merge edge recount found 347 → 350, no lost edges, and exactly the three stated gains.

Requested self-test last lines:

- `python3 scripts/mkt_seed_repo.py --self-test`: `14/14 self-test cases passed`
- `python3 scripts/check-shipping-sets.py --self-test`: `140/140 self-test cases passed`

## Loosening answers
LOOSENING-CHECK 639d2b2f0db1: not a loosening
VERDICT: CONVERGED

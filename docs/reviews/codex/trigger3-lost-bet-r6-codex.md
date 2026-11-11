<!-- codex-review: model=gpt-6.1-sol -->

One nonblocking finding; no functional blocker found.

**LOW — `scripts/check-plan-code.py:1393` — stale mutation-equivalence claim.**

- **Input, executed on a copy:** replace `closes_unit`’s expression with `"rounds_at_termination" in row`.
- **What happens:** contrary to “REJECTED as equivalent,” the mutation changes behavior: a stopped DEFER followed by a new unit incorrectly triggers WARN 12. Existing tests catch it: **“269/271 self-test cases passed.”**
- **Fix:** remove the equivalence claim. Also correct the adjacent “119 → 126” comment to **119 → 125**.

Checks completed on copies:

- **271/271** decision-scheme tests; **215/215** plan-code tests.
- **125/125** declared mutations killed and attributed to their named cases; green controls before and after.
- Fixture variation passes; total manifest count is **1,881**, matching the pin.
- Historical logs validate unchanged: **10 master rows**, **11 backfill rows**.
- **1,092 accepted ladder variants:** every exhausted `continued` unit produces exactly one of FAIL 2 or WARN 11.
- Renaming, retroactivity, subject isolation, and ordering probes held. Pre-existing sibling units remain the documented exception.
- No second closure/exhaustion implementation found. The trigger table matches behavior; final-round truth remains explicitly authored and undetectable.

No worktree files modified or git writes performed.

VERDICT: CONVERGED

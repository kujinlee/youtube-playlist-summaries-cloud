<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 206fb0bd482129de6135b35cf3d6461d49ed42aa

No Q4c BLOCKER found. No new defect reproduced in the r3 fold.

**FILE — Low: `--summary` includes no-headroom calls in its “ceiling forced” metric.** At `scripts/check-compaction-boundary.py:510`, I ran `summary()` with:
```json
{"trigger":"auto","verdict":"allow-ceiling","ceiling_by":"no-headroom"}
```
It produced:
```text
allow-ceiling: 1
ceiling forced 1 of 1 allowed auto compactions
```
The documentation says these rows are excluded. This misstates whether deferral merely adds delay. Filter both numerator and denominator using `ceiling_by`. Siblings searched: inspected the log producer and summary aggregation; no second aggregation found. Predates r3; FILE under Q4c.

Foreground verification:

- Self-test: **83/83 passed**.
- Unchanged wrapper copies with counting snapshot stubs: blocked auto call took **zero** snapshots; ceiling allows, malformed payload/transcript/effective settings, and directory-at-log failures each invoked the snapshot **once**, exiting 0.
- Ceiling probes allowed at 180k/200k and 900k/1M, plus the 200k, 950k and 1M no-headroom configurations.
- Manual matcher is identical to the pre-PR version.
- Injected snapshot exit 7 allowed compaction with one invocation, but discarded its stderr. Thus evidence supports exactly one **attempt**, not guaranteed successful capture on snapshot failure; no production data-loss reproduction established.

No files written in the working tree. No `.claude/plans/` files accessed. Under the round cap, the filed metric issue does not require another fold.

VERDICT: CONVERGED

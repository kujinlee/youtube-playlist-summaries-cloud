<!-- codex-review: model=gpt-6.1-sol -->

The re-anchor and reader-variation fixes work, but the exact-case claim is false.

- Self-test: **246/246 passed**.
- Manifests: **2,109 entries**, matching the pin; **no refusals**.
- Fixture variation: **passed**.
- Mutations, tested independently in complete isolated copies:

| Mutation | Failed cases |
|---|---:|
| Remove pre-flight wiring | **3** |
| Accept duplicate matches | 1, exactly named |
| Check edits nonsequentially | 1, exactly named |
| Narrow pre-check to `--only` | 1, exactly named |

The wiring mutation fails its named case **plus** the whole-manifest `--only` case and the upfront two-orphan case (**243/246 passed**). Thus the dashboard’s claim that all four mutations redden exactly their named case is inaccurate. The coordinator’s narrower claim about the re-anchored mutation is confirmed.

VERDICT: NOT CONVERGED

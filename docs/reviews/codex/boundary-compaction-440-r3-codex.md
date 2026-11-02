<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 24a6a63f4d53c20ad5979a1401374b42b705c78f

Reviewed the r2 fold and whole PR. REVIEW GAP: claude — alternation.

1. **High — FILE — fix-induced by r2 R2-3.** `scripts/check-compaction-boundary.py:305`: flooring the ceiling at W removes the hard-limit safety margin while `ctx` still excludes output and subsequent tool results.

   **Ran:** the unchanged shell wrapper in a temporary checkout, with a snapshot counter, `CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000`, fresh assistant usage `{input_tokens:999999, output_tokens:10}`, an outstanding Agent, and a subsequent tool result containing `"x " * 20000`.

   **Produced:** exit 0, `{"decision":"block",…}`, logged `ctx=999999`, `ceiling=1000000`, `verdict=block-agent`; **zero snapshots**. Even the supplied input plus output already totals 1,000,009 before the tool result. The hook therefore blocks using an obsolete size at the hard boundary. The previous 900k clamp would allow this input.

   Siblings searched: ran the scanner/decision with all four Opus/Sonnet 5.5 model names, including `[1m]`; all returned `block-agent`. Both models document a 1M window ([Opus](https://platform.claude.com/docs/en/models/opus-5-5/overview), [Sonnet](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)). Preserve the safety clamp independently of W; classify no-headroom rows separately. **Not Q4c BLOCKER:** reproduced the unsafe decision, not a live model failure or data loss.

2. **Low — FILE — not fix-induced.** `scripts/check-compaction-boundary.py:477`: a log error does not fail open.

   **Ran:** the wrapper with fresh `ctx=500000`, W=1M, an outstanding Agent, and a FIFO at `.claude/compaction-boundary.log`.

   **Produced:** stderr `log NOT WRITTEN … verdict block-agent`, exit 0, a block decision, **zero snapshots**. This refutes “fails open on every error path,” although the ceiling still bounds this particular block.

   Siblings searched: inspected both log open/write operations; both reach the same handler. Evaluation errors do allow and snapshot. Either allow on logging failure or narrow the stated guarantee. **Not Q4c BLOCKER.**

Foreground validation:

- Self-test: **81/81 passed**.
- Required mutation command: **45 killed, 45 attributed, zero survivors**.
- Wrapper counter: ordinary blocked call **0 snapshots**; allowed ceiling call **1**; invalid transcript-path payload **1**.
- Crafted paused and foreign-session sentinels allowed; own-session sentinel blocked.
- Manual matcher is unchanged.

Real transcript: used this checkout’s `f4c29ba2-aef5-4dd0-95ff-e40f317dc8e6.jsonl` under `~/.claude/projects/`. Decision **`allow-idle`**; signals **`[]`**; ctx **45,957**; W **300,000**; idle **4,404 seconds**. The actual repository wrapper exited 0 and reported its snapshot written.

No files under `.claude/plans/` were accessed. No review file was written.

VERDICT: NOT CONVERGED

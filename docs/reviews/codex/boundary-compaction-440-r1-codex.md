<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: cfdcf659c5ea64271e79ba677812105c360c2217

1. **High — FILE — completed foreground Agents remain “open”.** `scripts/check-compaction-boundary.py:164–168`

   **Ran:** an `Agent` call with `run_in_background:false`, followed by its successful result containing:
   ```text
   Review complete.
   agentId: abc123
   <usage>subagent_tokens: 1234
   tool_uses: 1
   duration_ms: 20000</usage>
   ```
   Then fresh assistant usage of 310,000 tokens, W=300,000, no sentinel.

   **Produced:** rc 0, `{"decision":"block", ... "mid-work (agent)" ...}`.

   The installed Claude Code 2.1.309 emits this footer in its **completed** result branch; `agentId:` does not establish background execution. The self-test substitutes `"the report"` for a foreground result, missing the real format. Distinguish launch acknowledgements from completed results.

   **Sibling search:** inspected asynchronous, completed and teammate result handling; the substring classification affects foreground results containing this footer. **Fix-induced:** no.

2. **High — FILE — the ceiling can exceed the model’s hard limit.** `scripts/check-compaction-boundary.py:244`

   **Ran:** fresh usage, sentinel present:
   
   | Configuration | Hook output |
   |---|---|
   | 200k model, W=180,000, context=199,999 | BLOCK; ceiling 270,000 |
   | 1M model, W=1,000,000, context=999,999 | BLOCK; ceiling 1,500,000 |

   Neither configuration can reach the advertised ceiling through successful requests. Claude Code itself caps the configured window at the model’s context window; this hook then multiplies it beyond that limit. A 450k ceiling is feasible for a 1M session, but is unsafe for a 200k session. See [Claude Code’s window rules](https://code.claude.com/docs/en/model-config#context-window-and-auto-compaction).

   Cap deferral below the effective hard window with request/output headroom; fail open when that window is unknown. The probes establish unsafe blocking, **not** an end-to-end overflow or data-loss reproduction.

   **Sibling search:** checked window validation, ceiling calculation and both environment/settings paths; no model-limit guard exists. **Fix-induced:** no.

3. **Medium — FILE — stale Agents make ceiling-driven compaction plausibly routine.** `scripts/check-compaction-boundary.py:202`

   **Ran:** one unanswered Agent from an hour earlier, followed by fresh assistant events. At 310,000 and 449,999 tokens the hook returned BLOCK; at 450,000 it allowed.

   Using the supplied measurement, \(p=11/243=4.53\%\):
   
   - At 20 Agents/day: **0.91 stale opens/day** expected.
   - Assuming independent calls: **60.4%** probability of at least one per day.
   - Across the stated 20-hour tail: approximately **53.8%** probability of at least one.

   These are estimates, not a measured ceiling-compaction rate: session boundaries, inactivity and tail eviction matter. Nevertheless, “ceiling is the usual path” is credible during sustained work—and finding 1 increases the risk beyond lost notifications. Each blocked call adds approximately 1k weighted tokens at 310k context, rising to 15k near 450k.

   Add a bounded Agent lease, for example **30 minutes without evidence of continued activity**, then stop counting it and log its expiry. Validate that policy against actual Agent durations.

   **Sibling search:** compared all three signals; Monitors have expiry handling, Agents do not. **Fix-induced:** no.

4. **High — FILE — fresh tool activity is misclassified as idle.** `scripts/check-compaction-boundary.py:133`

   **Ran:** assistant tool call timestamped 600 seconds earlier, its user `tool_result` timestamped **now**, sentinel present, context=310,000, W=300,000.

   **Produced:** no blocking output; log:
   ```json
   {"idle_s":600,"signals":["plan"],"verdict":"allow-idle"}
   ```

   The transcript’s newest event is fresh, yet only assistant timestamps update `last_at`. A long build finishing during plan execution therefore bypasses the guard and violates row 440’s fresh-transcript FAILS-IF. Track relevant activity across tool results and other event types.

   **Sibling search:** inspected every `last_at` assignment and the idle decision; only the assistant branch updates it. **Fix-induced:** no.

5. **Medium — FILE — malformed transcript records do not fail open.** `scripts/check-compaction-boundary.py:125`

   **Ran:** an old unanswered Agent, fresh 310k assistant usage, then a final line containing `not json`.

   **Produced:** rc 0, BLOCK for `agent`, zero snapshot invocations.

   Parsing errors are silently skipped. A corrupt completion record can therefore preserve an obsolete blocking signal instead of producing `allow-cannot-run`. Preserve tolerance only for the deliberately cut first tail fragment; treat other unreadable records explicitly.

   **Sibling search:** checked JSON decoding, non-object records and replacement UTF-8 decoding; several malformed-record paths discard evidence silently. **Fix-induced:** no.

6. **Medium — FILE — blocking filesystem operations bypass the hook’s internal bounds.** `scripts/check-compaction-boundary.py:275`, `:353`

   **Ran:** separately replaced the transcript and decision log with FIFOs having no writer/reader.

   **Produced:** transcript probe still running at **4 seconds**; log probe still running at **3 seconds**, before any snapshot. Both were terminated by the foreground probe.

   Plain `open()` can block before an exception exists. The registered 20-second runner timeout provides an outer escape, but can allow compaction **without any snapshot**. Runner timeout output is discarded according to the [hook timeout rules](https://code.claude.com/docs/en/hooks#timeouts). Use nonblocking descriptor opens, regular-file validation and bounded I/O.

   **Sibling search:** inspected transcript, settings, git metadata and log I/O; transcript/log opens are concrete reproduced hangs. **Fix-induced:** no.

Validation and limits:

- `python3 scripts/check-compaction-boundary.py --self-test`: **57/57 passed**.
- Foreground probes used unchanged copies of the Python script and shell wrapper in temporary fixtures, with a counting snapshot stub.
- Manual matcher: structurally **unchanged** from `origin/master`.
- Normal BLOCK: **zero** snapshot invocations. Normal ALLOW: **one**.
- Malformed payload, missing transcript, malformed settings without an environment override, and unreadable settings: allowed. A 9MB regular transcript completed using the bounded tail.
- Injecting non-UTF-8 snapshot output caused `UnicodeDecodeError`, shell fallback, and **two** snapshot invocations. This refutes unconditional exactly-once behavior under injected failure; a normal production caller producing those bytes was **not established**.
- I did not establish an idle-timer compaction occurring within five minutes of assistant activity. The installed timer uses cache activity; official documentation describes roughly an hour of inactivity. Finding 4 demonstrates the opposite error: active work incorrectly allowed as idle.
- No `.claude/plans/` files were accessed. Working tree unchanged.

**No finding above is designated Q4c BLOCKER:** the required reproduced false green, data loss/corruption, or security consequence was not established. High findings still warrant fixing under round-1 Q3.

VERDICT: NOT CONVERGED

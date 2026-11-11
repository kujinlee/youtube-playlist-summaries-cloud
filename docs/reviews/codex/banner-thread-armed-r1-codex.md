<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/check-banner-armed.py:623`: correctly finished plans produce false alarms.**  
   **Executed:** In the temporary copy, created a fully ticked `current.md`, armed it, ran `begin-plan.py --finish` successfully, and supplied a completed banner naming `current`. At the following Stop, the observer returned 1 and logged `unarmed-thread`:
   > “⚠ THREAD NOT ARMED — the previous turn ended on thread `current` … .claude/executing-plan names nothing.”

   The completed plan remains available to the work-lines reader, which scans plan files independently of the sentinel. Finishing legitimately removes the sentinel; absence does not prove the thread was never armed.  
   **Fix:** distinguish completed/cleared plans from never-armed threads using recorded lifecycle evidence. Add an end-to-end test that actually runs `--finish`.

2. **Major — `scripts/check-banner-armed.py:597` and `:621`: historical quotations become live thread switches.**  
   **Executed:** With `current` armed, supplied:
   ```text
   This was the reviewer’s quoted example:
   > **Thread:** ⤳ SWITCHED from `old` → `historical`
   ```
   Two observer Stops returned 0, then 1:
   > “⚠ THREAD NOT ARMED — the previous turn ended on thread `historical` … names `current`.”

   Also executed a closing summary containing a valid current banner followed by a repeated historical banner. It likewise warned and logged `step historical`. Neither input changed threads. These warnings contaminate the evidence intended to justify enabling BLOCK.  
   **Fix:** distinguish live banner emissions from quoted/history material. Requiring banner context would eliminate the standalone example, but repeated banners also need explicit historical exclusion.

3. **Major — `scripts/check-banner-armed.py:568`: readable thread names used in recent transcripts are silently ignored.**  
   **Executed:** Recent transcript `a6abe358-4c0b-44cb-a058-5446372998ef.jsonl`, turn `9e24a31a-802e-4aa0-98ca-29d4e979a4c3`, contains:
   ```text
   ## ▶ [10-22 10:27] STEP 3 of 4 — Review round 1 …
   > **Thread:** `work-lines-page` · step 1 ✅ (`479114be`) …
   ```
   Replaying this shape with no armed slug returned:
   > `(0, '', '', '')`

   The extractor requires `plan` before an ordinary slug. Thus even a backticked, readable thread in an actual step banner is missed. This is an additional bound beyond two switches or missing backticks.  
   **Fix:** recognize the leading thread-slug form used in transcripts while excluding later commit IDs and prose references. Add this real shape as a fixture.

4. **Minor — `scripts/check-banner-armed.py:585`: fence handling exposes fenced examples.**  
   **Executed:** Put a switch example inside a four-tilde fence containing an embedded triple-backtick line. The parser treats that backtick line as closing the tilde fence and warns:
   > “⚠ THREAD NOT ARMED — the previous turn ended on thread `historical` …”

   Under Markdown fence rules, the example remains fenced.  
   **Fix:** track fence character and opening length; close only with a compatible fence.

Other checks:

- **209/209 self-tests passed.** All 17 added mutations failed their declared expected cases without tracebacks.
- Replayed recent transcript text containing stamped banners, waiting text, and discussion of `▸` markers. The three original classes stayed quiet with armed or paused samples. Historical sentinel state was supplied as a test assumption, not recovered from transcripts.
- Same-turn target arming, resumed matching threads, and unrelated `Line:` slugs stayed quiet. Subagent text inside tool results was excluded.
- Glyphless standalone switches, unbackticked targets, and two-switch concealment remain misses. Slug comparison is literal: parenthetical text outside backticks works; a differing sentinel stem warns; parenthetical text inside backticks becomes unreadable.
- Upgrade-key absence and previous-slot carry passed their tests. No stale-slot defect was demonstrated.
- **36 copied-hook combinations passed.** Existing exit mappings and ordering were preserved. With `THREAD_BLOCK=False`, the thread return path produces 1, never 4. The progress check’s existing blocking path still exits before CI.

VERDICT: NOT CONVERGED

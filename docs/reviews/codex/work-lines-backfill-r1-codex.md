<!-- codex-review: model=gpt-6.1-sol -->

Found three paths to a wrong nonempty link. Probes used temporary transcripts and plan directories; no repository files were written.

1. **Blocking — `scripts/backfill-work-lines.py:534`: another checkout’s output becomes this checkout’s state.**

   Input: arm `one` in `/w/repo`, then execute:
   ```sh
   ( python3 scripts/begin-plan.py --tick; cd /w/other; python3 scripts/begin-plan.py side a ) | tail -1
   ```
   The surviving output describes `side` in `/w/other`. The parser removes that checkout’s call before matching output, so it attributes `side`’s state line to the real checkout’s tick.

   Executed replay output: **`two side`**. The actual sentinel in `/w/repo` still names `one`; `side` never armed there. `decide()` would authorize the wrong link; that specific write was **UNVERIFIED**.

   **Fix:** retain all calls while assigning output evidence. Reject ambiguous attribution across roots, and validate tick observations against the previously armed path.

2. **Blocking — `scripts/backfill-work-lines.py:541`: sentinel mutations disappear when the command also mentions `begin-plan.py`.**

   Input: arm `one`, execute:
   ```sh
   python3 scripts/begin-plan.py --status; rm -f .claude/executing-plan
   ```
   Then arm `two`. Because mutation detection is an `elif`, the removal is never inspected. Replay retains `one`.

   Executed temporary `--write` output:
   ```text
   rc=0
   <!-- parent: one -->
   <!-- parent-source: transcript sess-aaa 2026-10-01T12:00:30.000Z -->
   ```
   The correct parent is `-`.

   **Fix:** inspect mutations independently of begin-plan detection. Preserve shell-operation order, or mark the resulting state unknown when a mixed command cannot be resolved safely.

3. **Major — `scripts/backfill-work-lines.py:523`: quoted historical banners authorize new links.**

   Input: arm and finish `one`; in the next prompt’s turn, quote an old transcript inside a fenced code block:
   ```text
   Old transcript quoted for review:
   ```
   containing `⤳ SWITCHED from `one` → `two``, then arm `two`.

   Executed temporary `--write` output:
   ```text
   rc=0
   <!-- parent: one -->
   <!-- parent-source: banner sess-aaa 2026-10-01T12:00:40.000Z -->
   ```
   The quoted text is accepted as the current turn’s declaration. It fabricates the banner evidence required to override replay’s `-`.

   **Fix:** exclude fenced examples and quoted historical material; accept only the canonical current-turn banner format. If authenticity cannot be established, leave the disagreement unlinked.

Validation: **70/70 self-tests passed despite these counterexamples.** I also ran the stronger real-transcript check against both live markers: `work-lines-backfill ← banner-thread-armed` and `work-lines-always-on ← -` both matched. That provides two positive controls, but does not establish replay fidelity.

VERDICT: NOT CONVERGED

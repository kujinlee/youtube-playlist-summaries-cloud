<!-- codex-review: model=gpt-6.1-sol -->

No actionable findings at `cdb2c3d8`.

- Self-test: **331/331 passed**.
- Passed 2,205 boundary/DST/window combinations, including early-morning and 10:00 resets.
- Last-night spawn/wake entry points allow below 100% and refuse at exactly 100%.
- Five-hour warnings preserve the weekly verdict; stale caches remain CANNOT RUN and allow.
- No last-night messages retained “fit the room” or “under the stop.”
- Deliberate regressions made all four new cases fail.
- With the current `rise_start`, the last eight hours start after the #510 rise, including across DST.

No GitHub actions or source changes.

VERDICT: CONVERGED

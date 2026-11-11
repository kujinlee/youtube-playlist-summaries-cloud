<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `84c2b95e`. Three false READY findings are **HONEST**; the adversarial-only stop rule does not apply.

1. **High — HONEST: imported gate helpers escape detection.** `scripts/check-merge-ready.py:501,653`.

   Ordinary-work scenario: an author extracts validation into `scripts/gate_logic.py`, then accidentally weakens its return condition. The unchanged `scripts/check-helper.py` imports and runs it.

   Executed in a real Git fixture: changed the helper’s `return 1` to `return 0`. The gate’s exit changed **1 → 0**. `gather()` collected the exact helper diff, but the gate-path filter excluded it:
   ```text
   files: ['scripts/gate_logic.py']
   hold_reasons: []
   final_verdict: (0, 'READY')
   ```
   Regular imports need dependency coverage comparable to the new symlink handling.

2. **Medium — HONEST: nonzero exit statuses beyond 2 are invisible.** `scripts/check-merge-ready.py:499–500`.

   Ordinary-work scenario: a gate uses status 3 for a distinct refusal category, and an error-handling refactor accidentally converts that branch to success.

   Executed real Git change in `scripts/check-status.py`:
   ```diff
   -    sys.exit(3)
   +    sys.exit(0)
   ```
   Gate exit: **3 → 0**; `hold_reasons == []`; verdict **READY**. `FAIL_PATH` recognizes only literal statuses 1 and 2.

3. **Medium — HONEST: ordinary separation between conditions and failure handling defeats the window.** `scripts/check-merge-ready.py:666`.

   Ordinary-work scenario: while reorganizing a validation list, an author accidentally removes a required condition. A shared loop checks that list below the declaration.

   Executed fixture removed `False,` from `checks = [...]`; the unchanged loop’s `return 1` was seven source lines below it. The five-line hunk context ended before the failure anchor. Gate exit: **1 → 0**; no HOLD reasons; verdict **READY**.

   This is already documented as a bound, but the executed shape requires neither crafted input nor deliberate evasion.

Executed verification:

- `python3 scripts/check-merge-ready.py --self-test`: **185/185 passed**.
- All **68 mutations** applied individually over a green control: **67 killed through named assertions; mutation 54 terminated with `IndexError`**, rather than its named assertion.
- Replayed the last **40 first-parent merged PRs**: **8/40 held** — #398, #387, #386, #382, #381, #367, #366, #360. **313 Git calls; zero collection errors.**
- Repository unchanged; no review file written.

VERDICT: NOT CONVERGED

# Code review round 2 — Codex half — scoped to round 1's fix

**Subject:** the `measured` marking + the `all(...)` conjunct. **Date:** 2026-09-03. **Model:** `gpt-5.5`.

> Both halves found the same defect; **this half rated it Blocking and ran it**, the Claude half rated
> it Low and explicitly did not. Codex was right — see the correction in the Claude half.

---

<!-- codex-review: model=gpt-5.5 -->

Blocking: plan mode still reports an rc 2 timeout as a survivor and as a run mutation.

Evidence: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:760) appends the timeout to `ev_muts` with `measured: False`, and [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:762) still appends it to `ev_survivors`. The `--mutate` printer gates this behind `ev["trustworthy"]`, but the normal `check()` path just extends the lists at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:862), evidence renders `SURVIVED` unconditionally at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:896), and the non-`--mutate` final printer reports `len(ev['survivors'])` unconditionally at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2187).

Observation that makes it fail: with a temp plan and a stubbed `run_suite` returning rc 2 only for the mutated run, `main([plan])` prints:

```text
FAILED — plan's copy only, NOT compared: 1 file(s), 1 mutation(s), 1 survivor(s)
```

and `main([plan, "--evidence"])` additionally prints:

```text
mutations declared and run: 1, caught 0
  SURVIVED timeout mutation
```

That is the same false survivor/tally class the fix removed from `--mutate`. This was also true before this change on the plan-mode printer, because that path had no `trustworthy` concept.

Checked: both current `ev_muts.append` sites set `measured`; missing keys fail closed. The `expect` mismatch path is a completed-suite verdict, not another cannot-run. The new mutation anchor matches exactly once, and applying only that edit makes only `a TIMED-OUT mutation is counted but is NOT a verdict` fail. `--self-test` passes `162/162`; `--mutate .` passes with `164 mutation(s), 0 survivor(s)`. Counts are `docstring=162`, `check-plan-code=23`, `sum=164`.

NOT CONVERGED

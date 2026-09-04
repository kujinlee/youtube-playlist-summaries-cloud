# Code review round 1 — Codex half — `ev["trustworthy"]` in check-plan-code.py

**Subject:** commit `4c3d3390`, the CODE. **Date:** 2026-09-03. **Model:** `gpt-5.5`, `-s danger-full-access`.

> ⚠ **THIS HALF FOUND A BLOCKING THAT THE CLAUDE HALF DECLARED CONVERGED OVER.** The Claude half was
> written by the code's author and asserted that both `ev_muts` append sites record a real verdict.
> One of them is a cannot-run. See the correction in the Claude half.

---

<!-- codex-review: model=gpt-5.5 -->

Blocking: `trustworthy` can be true for a mutation that produced no verdict.
[file evidence](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:751): timeout/cannot-run mutations append to `ev_muts`, then continue. [cardinality gate](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:665) treats `len(m_muts) == len(muts)` as trustworthy, and [printer](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2101) prints the tally whenever that flag is true.

Observation that makes it fail: I ran `mutate_delivered` on a temporary delivered tree with one declared mutation that turns the suite into a timeout. Result was:

```text
ok=False
trustworthy=True
declared=1 mutations=1 survivors=1
report: mutation ... suite did NOT COMPLETE ... NOT CHECKED
```

Calling `main(["--mutate", temp_root])` for the same case printed:

```text
FAILED — delivered scripts mutated: 1 file(s), 1 mutation(s), 1 survivor(s)
```

That should be `NOT MEASURED — ... Treat this as NOT CHECKED.` with no counts, because `run_suite` rc `2` is explicitly a cannot-run, not a coverage verdict. Real survivors still need the tally, but timeout survivors are not real verdicts.

Verified:
`python3 scripts/check-plan-code.py --self-test` passed `160/160`.
`python3 scripts/check-plan-code.py --mutate .` passed with `163 mutation(s), 0 survivor(s)`.
Both new/repaired anchors match exactly once and their mutations redden the named cases.
Counts checked: docstring `160`, `EXPECTED_MUTATIONS["scripts/check-plan-code.py"] == 22`, sum `163`.

NOT CONVERGED.

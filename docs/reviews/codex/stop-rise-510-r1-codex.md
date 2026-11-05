<!-- codex-review: model=gpt-6.1-sol -->

Found two Medium issues and one Low issue. No Blocking or High defect found in the implemented curve.

- **Medium — A wrong DST curve passes every test.** On a temporary copy, replacing `local_midnight(resets - 86400)` with `local_midnight(resets) - 86400` still produced **310/310 passed**. These differ across DST: for reset `2026-03-09 00:30 PDT`, the specified start is **Saturday 00:00 PST**; the mutant starts **Saturday 23:00 PST**. Add DST-specific rise assertions; existing DST tests protect the reserve calculation, not this curve. Location: [check-usage-pace.py:899](scripts/check-usage-pace.py#L899).

- **Medium — Renaming a test orphaned another mutation’s required failure.** `#500: the verdict ignores the computed stop` still expects the removed test name `⭐ #500: on the last day the stop is the 97 cap …`. The mutation harness requires **every expected case name to match exactly**, so another failing case cannot satisfy this entry. Rebind this expectation to the renamed #510 case. Location: [check-usage-pace.json:1419](scripts/mutations/check-usage-pace.json#L1419).

- **Low — Current operating instructions still promise a 97% ceiling.** [process-checklists.md:190](docs/process-checklists.md#L190), both spawn/wake hook comments, and [check-usage-pace.py:164](scripts/check-usage-pace.py#L164) retain that claim. Memory notes also retain the old 97% guidance; distinguish the unchanged **pace-line guide** from the newly rising **hard stop**.

Evidence run:

- Baseline: **310/310 passed** in the suite’s PST8PDT zone.
- All **seven #510 mutations plus “#500: the stop is not capped at 97”** died through every named expected case on temporary copies, with no stderr.
- An additional wrong-DST-start mutation **survived 310/310**.
- **245,586 sampled points** across a year and weekly horizons: no cap outside `[97, 99]`, no stop above 99, no stop above the reserve.
- Probed 00:30 and 23:00 resets, spring/fall DST, exact start/end, under one hour remaining, and adjacent floating-point percentages. Comparisons behaved correctly. `pct_up` can display 97.1% while refusing at 97.000022%; that follows the existing upward-rounding convention.
- The specified span is implemented literally: ordinary 23:00 resets have a **46-hour rise**, and spring-forward Monday 00:30 has **46.5 hours**. “Last day” is shorthand, not a consistent 24-hour window.
- Reserve/cap/rising message branches matched their conditions. I found no production reader parsing the changed explanatory prose; hooks use the structured verdict.
- All **3,704 mutation edit anchors** resolve exactly once in their target files. Global find-string uniqueness **fails in six pre-existing groups**: stalled-work, review-rounds/review-recorded, banner-armed/closing-table, python-pin, agent-long-call/agent-large-read, and plan-file-tags. No duplicate find-string exists within the usage-pace manifest.

Tracked files remained unchanged. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED.

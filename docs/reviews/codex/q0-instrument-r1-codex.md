<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 985de1b6f8dbc548e39ca350a408a683628c44c3

- **Medium — docs/review-method.md:50–51:** The side-job hook points to a conflicting seam definition. `docs/process-checklists.md:949–951` explicitly includes “a new module” as seam work, while Q0 line 38 explicitly classifies a new module calling existing contracts as logic. A reader handling that side job receives opposite instrument choices. Align the checklist’s definition with the approved narrowing. Sibling check: compared both definitions and the Phase 6 rule in `dev-process.md`; the conflicting definition is in the cited checklist.

- **Medium — docs/review-method.md:71–73:** “Two or more” signals becomes an uncalibrated classification rule despite lines 59–61 retaining Q5 as the trigger. For example, repeated branch-coverage fixes can remain locally correct and add code, satisfying signals 1 and 2; the existing method explicitly says those can require an exhaustiveness pass rather than redesign (`docs/review-method.md:294–319`). Declaring “Q0 chose wrong” would misclassify that work as a seam problem. Treat the signals as prompts pending calibration, with Q5’s causal test deciding escalation. Sibling check: compared Q5, its documented false-positive safeguard, and spec §3; none establishes a two-signal threshold.

The cited figures, R9-1 result, quotation, and spec references support their claims. No withdrawn observer-log/verdict-path counts appear as evidence in the added text.

VERDICT: NOT CONVERGED

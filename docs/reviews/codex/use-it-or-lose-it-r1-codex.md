<!-- codex-review: model=gpt-6.1-sol -->

- **P2 — Positive room displays as “0% left.”** [check-usage-pace.py:418](scripts/check-usage-pace.py#L418) floors remaining room through `pct`. At 97.99% usage with a 98% stop, WARN leads with “USE IT — 0% is left,” undermining the instruction to keep working. Display positive room below 0.1% as “<0.1%”. REFUSE correctly omits USE IT.

- **P2 — DST can trigger USE IT an entire calendar day early.** [check-usage-pace.py:417](scripts/check-usage-pace.py#L417) subtracts 86,400 seconds before taking local midnight. In Pacific time, a reset at **2027-03-15 00:15 PDT** starts USE IT just after **March 13 midnight PST**, rather than March 14. It also hides the pace line and sends below-WARN owner notifications throughout that extra day. Use calendar-date subtraction; add spring-forward and midnight boundary cases.

Validation: **318/318 self-tests passed**; all five new mutations fail their named cases. Added tests cover ordinary examples but miss these boundaries. Below-WARN WARN does not block spawn/wake hooks; it produces context and an owner `systemMessage` on every prompt.

VERDICT: NOT CONVERGED

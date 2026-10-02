---
name: an-escalation-has-no-closer
description: "FIRES-WHEN: work has mooted a question already raised to the human — A question raised to the human is closed only by a REPLY — so later work that moots it leaves the question standing, open and wrong, in every place that carries it"
metadata:
  type: feedback
---

**MEASURED 2026-09-09 (PR #278).** On 2026-09-08 I escalated a real question about backlog #91:
*should plan mode exist at all, given that 0 of 92 plans reach its file path?* **The next day plan
mode was retired (#270) and its code deleted (#271).** The question was answered — decisively, in
code — and nothing closed it.

It stayed open in **two** places for a full day, and neither is a place anyone would think to look:

* the dashboard ask `2026-09-08/15`, still sitting in *What needs you*;
* backlog row #91's status cell, still carrying it as the outstanding item.

**Why:** ticks, gates and `[resolved:]` markers all close a thing when **work lands**. An escalation
is closed by a **human reply**, so when the answer arrives as *work* instead, no mechanism fires. The
answer and the question never meet.

**Why:** the same slice that moots an escalation is the one that should close it — and it is the one
least likely to, because from inside that slice the question is not what you are working on.

**How to apply:** when a slice retires, deletes or replaces a mechanism, **grep for the escalations
that named it** — the dashboard store, the backlog row, and any memory carrying an ⛔ OPEN. Close
them in that slice's own PR. And when writing an escalation, name the *observation that would answer
it*, not just the question, so a later reader can see it has already happened.

Related: [[coverage-verdict-union-91-merged]], [[retire-plan-mode-merged]],
[[a-check-result-is-not-the-claim]].

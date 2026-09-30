---
name: gates-detect-defects-not-design
description: "FIRES-WHEN: using gate results as evidence that a DESIGN is right — Every gate here answers \"is this correct?\" — a LOCAL question always answerable by patching, so a wrong shape emits defects we fix and each fix makes the gates greener; Phase 6 is the design gate and its per-milestone trigger never fired"
metadata:
  type: feedback
---

**Diagnosed 2026-08-09, after twelve rounds of patching one mechanism.**

Assertions, mutations, guard coverage, adversarial review — all answer **"is this correct?"** That
question is LOCAL, and a local question can always be answered *yes* by patching. So a wrong shape
never fails the gates; it emits a steady stream of defects that get fixed, and **each fix makes the
gates greener**. The process does not merely tolerate patching a bad design — it rewards it.

> Each patch REDUCES local defect count while INCREASING structural incoherence. Only one of those
> was being measured. Any process that measures defects but not coherence drifts to exactly this
> outcome — and feels increasingly rigorous while doing it.

**The correction worth remembering: the design gate EXISTED and was unarmed.** `dev-process.md`
Phase 6 describes this failure in its own opening sentence (*"per-task review is structurally blind
to composition defects … every change can be individually correct while the structure they add up to
degrades"*) and triggers **per milestone**. A spec can run twelve rounds in a week without crossing
one. **The inventory was right; the arming condition was wrong** — so the fix is a trigger, not a new
gate. Adding a gate would have been the wrong lesson.

**And the evidence was already being collected.** The standing shape *"a fix that moved or
reintroduced a defect"* was counted to nine, ten, then eleven across rounds 8–12 — the textbook
signature of a wrong abstraction, carried as **trivia in a prompt** for five rounds because no rule
said what to do when the number went up. *Make it a stop condition, not a statistic.*

**What can be mechanical, and what cannot:**

| Error class | Detector |
|---|---|
| a sentinel meaning two things | script: enumerate nullable/sentinel values, require ONE documented sentence, fail on "and"/"or" |
| two mechanisms for one concern | script: vocabulary collision — a column name-stem already owned elsewhere |
| a component that keeps breaking | rule: 2 consecutive rounds of self-caused defects ⇒ escalate fix → redesign |
| *"this abstraction is wrong"* | **nothing automatic.** Stays with Phase 6 and the human |

The win is not that wrongness becomes preventable; it is that it becomes **countable**, and so
detectable at round 2 instead of round 12.

**✅ ADDRESSED 2026-08-09 (PRs #62 → #63 → #64, stacked).** ADR-0007 (append-only log, no second
protocol); `check-sentinel-meanings.py` + `check-vocabulary-collisions.py` wired into
`check-schema-gates.sh` (now 6 gates), **both allowlists failing on STALE entries** so they cannot
become standing permission; Phase 6 armed on **4 non-converging rounds**; the fix→redesign stop
condition at **2** consecutive self-caused rounds; concern→mechanism table + "what already does
this?" in the spec template.

See [[one-rule-one-place]], [[quote-the-code-dont-characterise-it]],
[[an-instrument-that-edits-the-repo-corrupts-its-peers]].

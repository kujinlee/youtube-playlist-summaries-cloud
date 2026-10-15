---
name: printing-more-evidence-weakens-substring-cases
description: "FIRES-WHEN: I am about to make a report, log line or failure message print MORE of a child's output (a traceback, a captured stream, a diff) — ⛔ every existing case that asserts `any(<token> in report)` gets WEAKER, and some become UNFALSIFIABLE, because the new evidence can supply the token the case credited to the rule. Measured TWICE in one change, 2026-10-13; both caught by the mutation harness, neither by reading."
metadata:
  node_type: memory
  type: feedback
---

**Measured 2026-10-13, PR #371 `check-plan-code.py`.** I made the mutation loop print the child's
`diagnostic_tail(so, se)` on the unattributable-kill path. The diff adds evidence and removes
nothing, so it reads as unable to break anything. It broke two cases.

1. **A PRE-EXISTING case went unfalsifiable.** `a home-escape route in the MUTATION text is
   ignored` asserted `any("getpwuid" in r for r in _rep5)`. Its fixture's replacement text makes
   the fixture's own suite CRASH, so the run reaches the new branch, and **a traceback quotes the
   offending SOURCE LINE** — `getpwuid` and all. The case then passed whether or not
   `home_escapes(repl)` was consulted; its mutation SURVIVED. Found by CI shard 5 as a survivor,
   reproduced on demand at `--shard0 604/1535`.
2. **The case I wrote for the change had the same defect.** It asserted the exception type appears
   in the report. Over a single-line-message fixture `diagnostic_tail` ALSO carries the type
   (stdout is empty there, so stderr gets the whole 400-char window), so the mutation that drops
   the heading from the message left it green: 1 mutation, 0 killed, 1 SURVIVOR.

## The rule

**Assert the sentence only the RULE emits, never a token the EVIDENCE can also carry.** The fix for
(1) was `REPLACEMENT text is scanned` — emitted by exactly one call site, so no traceback, no
target scan and no other refusal can supply it. See [[assert-the-property-not-the-mechanism]].

For (2): a case about evidence must run over a fixture where the other sources CANNOT supply it —
here a message that FLOODS the window — and be **paired** with a case measuring that the other
source fails there. Without the pair the first case cannot show the thing is load-bearing rather
than merely present. [[a-case-can-pass-for-an-ambient-reason]], [[a-forced-choice-test-cannot-fail]].

## ⚠ And the POPULATION is not the cases you thought about

I measured the blast radius as "the five home-escape entries" and reported only 604 affected. The
real population is **every case anywhere that asserts a substring of a mutation report**. Printing
more evidence is a global weakening, and the one case that happened to notice is not the bound.
[[a-bound-enumerates-what-is-witnessed]], [[measure-the-population-the-code-actually-sees]].

**Why it is hard to see:** an additive diff has no deletion to review, and both defects make a test
pass. Nothing goes red at the moment of the change. Only the harness asks the inverted question —
*would this case still fail if the rule were gone?* — which is why
[[what-mutation-testing-proves]] is load-bearing here and reading is not.

## ⭐ THIRD INSTANCE, found by the OTHER review half — and the inverted form, found by my own prose

**2026-10-14, round 18 of PR #371.** A case added one round earlier to prove a report quotes exactly
one line read:

```python
any("ONLY_KILLER" in r and "·" not in r for r in _rep1)
```

`ONLY_KILLER` is the text of the fixture's own injected `raise`, so the **raw traceback** in the
diagnostic tail supplies it whether or not the harness quoted it as a head. Severed so one-head
reports quote nothing at all, the suite stays **300/300** and both new cases still pass. ⭐ Worth
noting who found it: the Codex half, not me, and not the Claude half of the round that wrote it — see
[[dual-review-what-it-catches]].

### ⛔ AND THE SAME SHAPE INVERTED, in a self-check I wrote the same day

Renaming `_tracked_textfiles` → `_walked_textfiles`, I guarded the edit with
`assert "_tracked_textfiles" not in s`. It fired, and the surviving occurrence was **my own new
docstring explaining the rename** — a file documenting a retired name MUST mention it, so the
assertion was unsatisfiable by construction. Nothing was written, so the cost was one retry.

**The general rule, which covers both directions:** a substring test over a text you also AUTHOR is
not a test of the code — the author's own prose is part of the corpus. Narrow it to the construct you
mean (`def \s+NAME\s*\(` and the call form, not the bare token), exactly as the positive case must
be narrowed to the mechanism rather than to any token the fixture happens to emit.

# A harness cannot read a CAUSE out of a child's text — it can only quote it

**Four consecutive rounds on `check-plan-code.py` (r9–r12, 2026-10-13) had ONE root cause, and an
architecture review in the middle of them did not stop it:** the harness inferred *why* a child went
red from text the child controls. Each repair fixed one inference and left the mechanism.

**The three live instances, all measured against real children:**

| the harness believed | the child actually did |
|---|---|
| *"stderr NAMES `ValueError: X`"* — two exceptions | raised **ONE**; the second was fabricated from an indented MESSAGE CONTINUATION |
| *"stderr is EMPTY, so the suite RAN and its PRINTER is the subject"* | `import os; os._exit(1)` — rc 1, stderr empty, **nothing ran, no printer involved** |
| *"killed, attributed to case `fabricated`"* | `raise RuntimeError("no cases ran\n[FAIL] fabricated: got 0 want 1")` — **zero cases executed**; the traceback FORGED the failure name |

⭐ **The repairs that worked were all SUBTRACTIVE or NARROWING**, never a cleverer parser:
require a structural marker (`  File "`) before believing a run of indented lines is a traceback;
validate a type name with Python's own `str.isidentifier()` instead of an ASCII regex; report the
observation (`0 bytes`) and state explicitly that it is NOT evidence of execution; and read failure
names from **stdout only**, because that is the stream the producer writes to.

⛔ **The general rule: a stream a child controls can forge anything the harness greps for.** Ask of
every parse — *could the subject under test produce this text deliberately?* If yes, the parse is a
quotation, not a measurement, and the message must say so. Printing MORE evidence makes this worse,
not better: see [[printing-more-evidence-weakens-substring-cases]].

⚠ **And the arming condition kept firing after its own review.** Phase 6 ran, chose option A, and
round 12 produced three Highs of the same class — so *the architecture review ran* is not evidence
*the thrashing stopped*. Related: [[a-second-implementation-of-one-rule-drifts]],
[[gates-detect-defects-not-design]].

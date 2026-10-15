# A harness cannot read a CAUSE out of a child's text — it can only quote it

⤳ **Provenance:** PR **#371**, branch `backlog-249-260-fixes`, rounds **11–13** of its review (`docs/reviews/{codex,claude}/backlog-249-260-r{11..13}-*.md`); the architecture review is `docs/reviews/architecture-review-2026-10-13.md`. ⚠ Round numbers alone are ambiguous — this repo ran several review subjects on 2026-10-13 — so the branch and the paths are named.

⟳⛔ **THE SPAN IS THREE ROUNDS, NOT FIVE — round 2 of the docs review caught that overclaim.** An earlier version of this file said *rounds 9–13*. Reading those records, **rounds 9–10 concern withdrawal and parser problems**, and their harness mentions are coverage or validation discussion, not this cause. The witnessed span is 11→13; *consecutive* is still the point, and three is what the records support.

⚠⛔ **AND ROUND 13 REFUTED THE REPAIRS DESCRIBED BELOW AS HAVING WORKED.** The frame-marker and the identifier validator both still drop REAL exceptions (`type("bad-name", (Exception,), {})` prints `bad-name: ROOT_MARKER` and is reported as nothing) and still invent fake ones (a frame-shaped line inside an exception MESSAGE yields two headings for one exception). Filed as backlog **#280**, with the enumeration half as **#279**. **The pattern below is real; the repairs are not finished** — which is itself the strongest evidence for the pattern.

**THREE consecutive rounds on `scripts/check-plan-code.py` (2026-10-13) had ONE root cause, and an
architecture review in the middle of them did not stop it:** the harness inferred *why* a child went
red from text the child controls. Each repair fixed one inference and left the mechanism.

**The three live instances, all measured against real children:**

| the harness believed | the child actually did |
|---|---|
| *"stderr NAMES `ValueError: X`"* — two exceptions | raised **ONE**; the second was fabricated from an indented MESSAGE CONTINUATION |
| *"stderr is EMPTY, so the suite RAN and its PRINTER is the subject"* | `import os; os._exit(1)` — rc 1, stderr empty, **nothing ran, no printer involved** |
| *"killed, attributed to case `fabricated`"* | `raise RuntimeError("no cases ran\n[FAIL] fabricated: got 0 want 1")` — **zero cases executed**; the traceback FORGED the failure name |

⭐ **The repairs that were ATTEMPTED were all SUBTRACTIVE or NARROWING**, never a cleverer parser — ⛔ **r5 M2: "that worked" is WITHDRAWN**, because the line above records round 13 refuting exactly these as having worked: two of them still drop real exceptions and still invent fake ones (#279/#280). What the evidence supports is the DIRECTION, not the outcome:
require a structural marker (`  File "`) before believing a run of indented lines is a traceback;
validate a type name with Python's own `str.isidentifier()` instead of an ASCII regex; report the
observation (`0 bytes`) and state explicitly that it is NOT evidence of execution; and read failure
names from **stdout only**, because that is the stream the producer writes to.

⛔ **The general rule: a stream a child controls can forge anything the harness greps for.** Ask of
every parse — *could the subject under test produce this text deliberately?* If yes, the parse is a
quotation, not a measurement, and the message must say so. Printing MORE evidence makes this worse,
not better: see [[printing-more-evidence-weakens-substring-cases]] — ⚠ which is NOT YET COMMITTED (it sits in the main checkout's uncommitted pile, the pile this branch's commit says it is avoiding), so that link dangles until it lands.

⚠ **And the arming condition kept firing after its own review.** Phase 6 ran, chose option A, and
round 12 produced three Highs of the same class — so *the architecture review ran* is not evidence
*the thrashing stopped*. Related: [[a-second-implementation-of-one-rule-drifts]],
[[gates-detect-defects-not-design]].

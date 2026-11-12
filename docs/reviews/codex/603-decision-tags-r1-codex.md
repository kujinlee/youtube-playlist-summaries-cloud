<!-- codex-review: model=gpt-6.1-sol -->

Found two MAJOR defects and two MINOR test gaps. No BLOCKER found.

1. **MAJOR — Hidden/inert decisions inflate the counter and break navigation.** `scripts/brief-compose.py:1139–1143`

   Ran `render_decisions`, then loaded its output in Chromium:

   - `<template><p data-decision>Example</p></template><p data-decision>Real</p>` reports **2 remaining**, but the document contains only one accessible tag: **DECISION 2 of 2**. “Next” targets `decision-1`, which is inside template content and absent from the document’s ID lookup.
   - `<p hidden data-decision>Hidden</p><p data-decision>Visible</p>` reports **2 remaining**, with only decision 2 visible. “Next” targets the hidden decision.

   These are valid HTML inputs accepted without warning. The counter counts decisions the owner cannot review.

2. **MAJOR — Generated IDs collide with existing fragment IDs.** `scripts/brief-compose.py:1168–1179`

   Rendered:

   ```html
   <p id="decision-1">Intro</p><p data-decision>Choose</p>
   ```

   Chromium’s `document.getElementById('decision-1')` returns **Intro**, not the decision tag. The counter’s “next” link therefore navigates to the wrong element. No collision detection or unique namespace exists.

3. **MINOR — First-open test admits a constant answer.** `scripts/brief-compose.py:2789–2791`

   In-memory mutation: replaced both `{open_ns[0]}` interpolations with `{1}`. **207/207 tests still passed.**

   Observation that should make this **FAIL**: answer decision 1 and leave decision 2 open; “next” must target `#decision-2`. Neither existing fixture exercises that state. This mutation would also misdirect the marketplace page, whose first open decision is 7.

4. **MINOR — Colour tests do not establish readable contrast.** `scripts/brief-compose.py:2813–2822`

   In-memory mutation: changed all six dark palette values, in both dark blocks, to `#ffffff`. **207/207 tests still passed.**

   Observation that should make this **FAIL**: dark tags have white text on white backgrounds, **1:1 contrast**. The tests establish token presence and different palette values, not readability.

Verification completed:

- `python3 scripts/brief-compose.py --self-test`: **207/207 passed**.
- Executed all **12 new manifest mutations** in memory: each failed its named expected test. Their observations cover numbering, placement, answered state, escaping, remaining count, link target, completion colour, counter placement, call-site removal, CSS gating, and theme declarations.
- Re-composed the real marketplace fragment and opened it in Chromium: **11 total / 2 remaining / 9 answered**, matching all 11 tags; first open is **7**. No wrong count established there.
- Eight real decision-free fragments composed byte-identically against `origin/master`.
- Nested decisions numbered correctly. Textarea examples were excluded. Closed `<details>` concealed the tag initially; clicking “next” opened it.
- Encoded `<img … onerror=…>` answer rendered as text; **zero image elements**.
- Current light/dark open/answered text contrast: **10.72 / 7.59 / 9.77 / 7.83:1**.
- Tracked worktree remained clean; no commits or GitHub actions.

VERDICT: NOT CONVERGED

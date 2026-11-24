# Round 5 — `decision-buttons` (PR #628) — coordinator — NOT CONVERGED (Claude half); the BLOCKER answered by moving the guarantee into the page

```yaml
round: 5
fixes_nontrivial: true
subject: decision-buttons
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Blocking, aim: deliverable, fix_induced: true, component: sent-state, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 5 is the Claude half)

The Claude half (`docs/reviews/claude/decision-buttons-r5-claude.md`: NOT CONVERGED, one BLOCKER) reviewed head
`ea195790`, the r4 fold. Round 5 is past the round cap (`docs/review-method.md` §0 Q4c), so only the BLOCKER is
folded and nothing else is filed. The review raised nothing else.

## F1 — classification

**Fix-induced by r4: YES.** r4 removed the occurrence suffix from the key and made a key's uniqueness rest on
`render_decisions` refusing twins. That put a new requirement on the code: a Python HTML scan of the source and the
browser's DOM (`textOf`) must read every question the same way. r4's coordinator doc states that bound and calls the
shapes outside it hostile markup. r5 measured that three of them are conforming HTML (an omitted `</li>`, `</td>` or
`</dd>`). Before r4, those same pairs got two keys from the occurrence suffix. Under r4 they get one key outright.
The defect is the r4 fold's own bound turning out to be reachable, so it was caused by that fold.

**The thrashing answer: THRASHING, by the definition.** r4 M1 was fix-induced by r3, in component `sent-state`. r5 F1
is fix-induced by r4, in the same component. Two consecutive rounds whose findings came from the previous round's
fix, in one component, is the Phase 6 arming condition (`docs/dev-process.md` → *THE ARMING CONDITION IS THRASHING*).
It is answered here structurally, not by patching the scan a fourth time. The fix does what a Phase 6 review would
ask of a second implementation of one rule: it gives the rule one authority. Whether to convene a Phase 6 review
anyway is the orchestrator's call. This fold does not convene one.

## F1 — the fix: the page is the authority on its own keys

| Part | What changed |
|---|---|
| **The guarantee** (`DECISION_JS`, the load loop) | Every decision's key (`key()`) is computed first, into `byKey`. Then `twinsOf(tag)` returns the group when a key is on two or more tags. Any such tag, open **or** done, gets a box holding ONLY an error line: `⚠ decisions 1 and 2 are identical (the same label and question), so this card has no buttons — give one a distinct data-decision-label`. The ordinals are read from the tag's `id` (`ex-decision-<n>`). Such a card never calls `load` or `offer`, so it cannot show a restored "sent" and cannot send. A done tag still forgets its own key at load, as r3 has it: the session recorded that decision, so the stored "sent" is spent either way. |
| **The early warning** (`_DecisionScan`, `render_decisions`) | It is kept, and now agrees with the browser on the cheap shapes. `_js_norm` folds and trims exactly JS `\s` (`_JS_WS`): U+FEFF folds, and U+001C–U+001F and U+0085 no longer do, so the scan stops over-refusing those. `_text` leaves out the text under any element in `_QUESTION_SKIP_TAGS` (`button`, `template`) or with class `askbtn` / `ex-pick` (the class attribute is split on ASCII whitespace, as `classList` splits it). The label goes through `_js_norm` too. **Not taught:** implicit end tags other than `<p>` (`li`, `td`, `dd`), and the `&amp.x` entity form. Teaching the scan more of the HTML parser is the thrashing this fold refuses, and the runtime check makes it unnecessary. |

**Measured after the fix** (head below, in this worktree):

- The reviewer's `probe.py` over its own `cases.json`, re-run against the new code. These are now **REFUSED at compose
  time**: `askbtn_span`, `expick_span`, `template_in`, `bom_ws`, `bom_label`, and all the controls the review listed as
  correctly refused. These still **compose** with a shared key: `li_unclosed`, `td_unclosed`, `dd_unclosed`,
  `entity_dot`. Each loaded in jsdom with the real script: **2 of 2 cards show the identical-decisions line, and 0
  cards have buttons.** `control_distinct`, `label_ordinal`, `textarea_rc` and `fs_char` compose with distinct keys,
  and each card has buttons.
- The three real decision pages, loaded in jsdom: marketplace-inventory 13 tags and 13 distinct keys; goal-node-tree-spec
  28 and 28; publishable-components 4 and 4. **0 identical-decisions lines**, 0 page errors. The two all-done pages
  have no boxes, and publishable-components has 4 boxes, all with buttons.
- All 37 `docs/explainers/*.fragment.html` compose (rc 0).

## Cases and mutations

- **New node cases** (the stub-DOM harness that runs the real `DECISION_JS`):
  - **S9:** the omitted-`</li>` pair, built as the browser's DOM builds it (`<ul><li>…Ship?</li><li>x</li></ul>` and
    `<ul><li>…Ship?</li></ul>`). Decision 1 is answered alone first, in this browser, so its key is stored. Then the twin
    page loads. The case asserts: both tags have one key; both cards show the error line; there are 0 buttons on the
    page; 0 POSTs; and the store is untouched. This is "buttons: two tags with ONE key (the omitted-</li> pair) get no
    buttons, no restored 'sent', and an error line naming both — the page is the authority on its own keys (r5)".
  - **S9b:** a done tag and an open tag that share a key. Both show the line, and neither has buttons.
  - **S10:** the same shape with two distinct questions. Both cards offer the buttons, a click POSTs once, and on
    reload "sent" is on that card only.
- **New Python case:** "decision twins r5: the scan folds U+FEFF and leaves out .askbtn/.ex-pick and <template> as the
  browser does, so those twins are REFUSED; a near-miss class and U+001C stay distinct". Its five twins are U+FEFF in
  the question, U+FEFF in the label, a nested-markup `.askbtn`, an `ex-pick` behind a tab-separated class list, and a
  `<template>`. Its adjacent negatives are class `askbtnx` and U+001C.
- **Mutations** (`scripts/mutations/brief-compose.json`). Added (+6): the page's duplicate-key check removed; a
  duplicate card still given buttons and its stored state (the `return` after the error dropped); a done duplicate
  given no error line; the scan's U+FEFF fold removed; `.askbtn`/`.ex-pick` read into the question; a `<template>`'s
  content read into the question. Retargeted: the r4 "`<button>`'s text read into the question" now removes `"button"`
  from `_QUESTION_SKIP_TAGS`. The set is written one member per line so each mutation has its own anchor (the sweep
  refused a shared anchor). Pin 104 → 110 (`scripts/mutations/expected_mutations.py`).

## Decision log

`docs/reviews/decision-scheme/decision-log.jsonl`: the r4 `redesign` bet is scored `outcome: continued`. The bet was
lost, and its stated risk is exactly what r5 measured. One `split` row is appended (`retroactive: false`, `outcome:
null`). The uniqueness guarantee is split off the compose-time refusal and into the page. Its bet: no later round
finds a composed page on which a card shows a sent state it did not send. Its stated risk: a 32-bit FNV collision
between two different decisions now disables both, which fails safe and visibly.

## Gates (worktree, after the fold)

| Check | Result |
|---|---|
| `python3 scripts/brief-compose.py --self-test` | **255/255** (251 + S9, S9b, S10 and the r5 scan case; red first: the S9 case and the scan case failed before the fix) |
| `python3 scripts/ask_answerer.py --self-test` | 125/125 |
| `check-ratchet-contract`, `check-selftest-counts`, `check-docs`, `check-explainer-delivery` | rc 0 each |
| `check-review-rounds`, `check-decision-scheme` | rc 0 each (the scheme check prints only its standing WARNs) |
| `check-plan-code.py --mutate . --only scripts/brief-compose.py --allow-long-local`, run in a scratch copy (a separate git repo) | **110 mutations, 110 killed, 110 attributed to the case each names, 0 survivors, re-control passed, rc 0.** Without `--allow-long-local` the run refused as over the 10-minute local budget and measured nothing. A first run refused because two mutations shared one anchor, so the skip set is now written one member per line. The swept copy differs from this commit only in the docstring's case count on line 38, which no mutation anchors to. This is a diagnostic slice, not the full sweep. |
| `check-review-decision.py` | rc 1, **ARCHITECTURE_REVIEW**: `'sent-state' carried fix-induced findings in r4 and r5`. That matches the thrashing answer above, and the decision is the orchestrator's. |

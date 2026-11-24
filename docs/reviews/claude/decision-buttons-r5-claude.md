# Round 5 — `decision-buttons` (PR #628) — Claude half — NOT CONVERGED

**Subject:** `git diff 48bc031f ea195790`, the r4 fold. Codex's BLOCKER (twins told apart by their order) was
answered with a redesign: `render_decisions` refuses two decisions that have the same label and question, and
`key()` in `DECISION_JS` no longer counts occurrences. **Head reviewed:** `ea195790`.

**Mandate:** past the round cap. Only a BLOCKER gets fixed. I was asked to try to refute the claim that the redesign
removed the class.

**Verdict in one line:** the class is **not** removed. Uniqueness on a page now rests on a Python HTML scan agreeing
with the browser's DOM about each decision's question text, and the two disagree on **conforming** HTML. An omitted
`</li>`, `</td>` or `</dd>` is enough, and `<td data-decision>` is a host two real fragments already use. When they
disagree, two identical decisions compose without a refusal, share one localStorage key, and answering one makes the
other show **"✓ sent"** after a reload. That meets the brief's BLOCKER criterion: *a card shows "sent" for a decision
whose answer was never sent.*

## Gates run (at `ea195790`, in this worktree)

| Check | Result |
|---|---|
| `python3 scripts/brief-compose.py --self-test` | **251/251 passed** |
| `python3 scripts/ask_answerer.py --self-test` | **125/125 passed** |
| `python3 scripts/check-ratchet-contract.py` | rc 0 |
| Mutation pin | `scripts/mutations/brief-compose.json` has 104 entries. `EXPECTED_MUTATIONS["scripts/brief-compose.py"]` is 104 (102 − 2 retired + 4 added). They agree. I did **not** re-run the mutation sweep; the coordinator's 104/104 is theirs, not mine. |
| Every `docs/explainers/*.fragment.html` composed with this head (`--out` to scratch) | **37/37 compose.** The first pass reported two FAILs because I passed a nonexistent `--source`; without `--source` both compose with rc 0. Nothing that composed before is refused now. |
| The three decision pages loaded in jsdom with the real tray script and a `VirtualConsole` capturing page errors | marketplace-inventory: 13 tags, 13 distinct keys, all done. goal-node-tree-spec: 28, 28 distinct, all done. publishable-components: 4, 4 distinct, all open. **0 page errors on each.** Clicking Yes on every open card POSTs 4 distinct lines, and a reload shows 4 "sent" boxes with 0 POSTs. |
| r4 M1 (the script on an all-done page) | **Fixed, verified.** Both all-done pages now carry `DECISION_JS`. I seeded localStorage with every tag's own key and reloaded: 13 → 0 and 28 → 0 keys left. Forget-at-load runs there. |

## Findings

### F1 — BLOCKER — the twin refusal and the browser's key read the question differently, so identical twins still compose and share a key

**Where:** `scripts/brief-compose.py`. `_DecisionScan._text` and `handle_*` build the Python question. The twin
check in `render_decisions` compares it. `textOf` / `questionOf` / `baseKey` in `DECISION_JS` compute the key the
browser uses.

**The design defect:** this is a second implementation of one rule. The key is defined by the browser's DOM text
(`textOf`). The refusal re-derives that text with a hand-written scan of the source. Any input where the scan reads
two questions as different and the DOM reads them as equal passes the refusal and collides in localStorage. The r4
coordinator doc states this bound and calls every such shape "hostile markup". Three of the shapes below are
**conforming HTML**: the end tags of `li`, `td` and `dd` are optional by spec.

**Evidence:** `probe.py` builds a fragment, composes it with the real CLI, and loads the composed page in jsdom with
the real tray. It reads each tag's `exKey`. Every case is a pair that **is** a twin to the browser: same label and
same question as the DOM reads it.

| Case (two decisions) | Python refusal | Browser keys |
|---|---|---|
| control: `<p data-decision>Ship?</p>` ×2 | REFUSED | — |
| `<ul><li data-decision>Ship?<li>x</ul>` + `<ul><li data-decision>Ship?</li></ul>` | **composed** | **COLLISION** `ex-pick:p.html::b29a02e0` ×2 |
| `<table><tr><td data-decision>Ship?<td>x</table>` + the same `td` closed | **composed** | **COLLISION** |
| `<dl><dt data-decision>Ship?<dd>x</dl>` + the same `dt` closed | **composed** | **COLLISION** |
| `Ship?<span class="askbtn">z</span>` vs `Ship?` (`textOf` drops `.askbtn`/`.ex-pick` at any depth; the scan drops only `<button>`) | **composed** | **COLLISION** |
| same with `class="ex-pick"` | **composed** | **COLLISION** |
| `Ship?<template>z</template>` vs `Ship?` (a template's content is not in `childNodes`) | **composed** | **COLLISION** |
| `Ship &amp.x?` vs `Ship &amp;.x?`: `handle_entityref` re-wraps a name that stopped at a non-`;` as `&amp.x;`, which adds a `;` the browser does not | **composed** | **COLLISION** |
| `Ship﻿now?` vs `Ship now?` (JS `\s` folds U+FEFF; Python `str.split` does not) | **composed** | **COLLISION** |
| labels `A﻿B` vs `A B` (same cause, on the label) | **composed** | **COLLISION** `ex-pick:p.html:A B:b29a02e0` ×2 |

**The user-visible failure (end to end, `li` and `td` cases, and the `.askbtn` case):** load the page and click
**Yes on decision 1 only**. One POST goes out, for `DECISION 1 of 2`. The page shows decision 1 "sent" and decision 2
with its buttons. **Reload: both cards show `✓ sent: yes`**, with 0 POSTs. Decision 2's answer was never sent. The
session reading `questions.md` sees one answer and two open decisions. Before r4, the occurrence suffix at least
gave these twins two keys. Now they share one outright, so the redesign made this input worse, not merely unfixed.

**What I could NOT break, for the record:** these were refused correctly: entities in the question (`&amp;` ⇄ `&`,
`&nbsp;` ⇄ U+00A0), whitespace runs, `<br>` joins, a `<button>` with nested markup, labels with entities or extra
whitespace, a done twin beside an open one (`data-decision="yes"` + bare), an `h2`/`h3` heading pair, and a nested
decision whose inner question equals a later one. A label ending in its own `— DECISION 7 of 7` stays distinct from
the bare label. `<textarea>` content differs on both sides (no collision). In the direction that does no harm, the
scan folds U+001C as whitespace and JS does not, so the scan over-refuses there.

**Reach, stated honestly:** this needs an author to write two decisions that are identical to the reader. The r4
fold itself calls that an authoring error. No real fragment does it today: every `<td data-decision>` in
`docs/explainers/` closes its `</td>`, and the 45 real keys are distinct. Even so, it is the exact failure the
redesign claims is now impossible, it is reachable with valid HTML, and it shows "sent" for an unsent answer.

**Suggested fix, one that ends the class rather than patching the scan a fourth time:** make the **page** the
authority over its own keys. `DECISION_JS` already computes every key once, in the load loop, before any box
exists. In that loop, record each key. If a key is seen on a second tag, give **every** tag with that key no
buttons, and add a visible error line like "decisions n and m are identical — give one a distinct
data-decision-label". Then a duplicate key can never write or read shared state. Keep the Python refusal as the
early, friendly error it is. It only needs to be usually right, because the browser check no longer depends on the
two parsers agreeing. Pin it with a node case that builds the `li` pair above (unrefused by Python) and asserts no
`.ex-pick` box on either tag, plus a mutation that removes the duplicate check.

## What the fold gets right

- r4 M1 is fixed and verified on the two real all-done pages (see the gates table).
- Removing the occurrence suffix is right. The new S7 base-key case pins the key's shape against an independent
  FNV-1a computed in Python over UTF-16 code units, which is a good, independent copy.
- Mutation bookkeeping is consistent: 104 = 102 − 2 + 4, and the retargeted `expect` names exist in the self-test.

VERDICT: NOT CONVERGED

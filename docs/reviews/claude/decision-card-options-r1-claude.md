Reviewed head: 12933d937ddb2ce92546fb7cb388838d88bc4e56

# Decision card options (backlog #727), round 1, Claude half

Branch `decision-card-options`, PR #635, diff against `origin/master`. Adversarial mandate: try to refute
the change in `scripts/brief-compose.py` (`_choices`, `render_decisions`, `DECISION_JS` `offerChoices`/`offer`).

## What was run, and what it showed

| Check | Result |
|---|---|
| `python3 scripts/brief-compose.py --self-test` at the head | 261/261 passed (22 s) |
| New manifest entries (the last 7 in `scripts/mutations/brief-compose.json`) | each anchor occurs exactly once in the source; manifest has 117 entries, which matches `expected_mutations.py` |
| Six mutations NOT in the manifest, each applied to a copy and the self-test run | all six turned the suite red: empty-entry check removed (259/261), orphan-rec check removed (259/261), `html_escape` removed from `data-ex-options` (255/261), `data-ex-rec` never written (257/261), `data-ex-options` written on every open tag (259/261), a click sends the rec rather than its own choice (259/261). So the new cases **can fail** |
| Compose-time probe of 18 edge inputs (`render_decisions` on a copy) | `<`, `&`, `"`, `'` round-trip escaped; `""`, `"   "`, `A\|B\|` refused; a newline inside a choice is folded; an upper-case attribute name and a duplicate attribute (first wins, as in a browser) behave like a browser. Problems are F1 to F3 below |
| **Real browser (Playwright Chromium)**: a page composed by the CLI into scratch, served over HTTP, `POST /questions` intercepted | Buttons: `[A — accept <b> & co, ★ B — keep "old" file, C's way, ✎ Other…]`; a heading decision's box sits after the `<h3>`; an option-less card still shows `★ Recommended: … / ✔ Yes / ✖ No / ✎ Other…`. `document.elementFromPoint` at the centre of the ★ button returned that BUTTON, and a `page.mouse.click` at those coordinates sent `**D1 — DECISION 1 of 4**\n   > Pick one?\n   Q: ANSWER: B — keep "old" file`, exactly the choice text. `change` brought the choices back; `A — accept <b> & co` sent literally; after reload each card showed its sent answer; counter `4 decisions · 3 remaining · 1 answered` (one done card that also declares options). No page errors |

## Findings

### MINOR F1: a `|` cannot appear inside a choice, and an author who tries the entity is split silently
`scripts/brief-compose.py:1609`. `HTMLParser` decodes `&#124;` before `_choices` splits, so
`data-decision-options="A &#124; B|C"` composes as three buttons `A`, `B`, `C`, and nothing warns. The
answer sent is then half of the author's choice. The explainer-delivery table (`.agents/skills/shared/explainer-delivery.md:232`)
says the list is `|`-separated, but never says a choice may not contain one.
**Fix:** state the limitation in the docstring and in explainer-delivery §3a. Alternatively, refuse a raw attribute
whose SOURCE text contains `&#124;`, `&vert;` or `&verbar;`. That needs the raw tag text (`get_starttag_text()`), which the scan already uses.

### MINOR F2: a valueless `data-decision-options` or `data-decision-rec` is ignored without a warning
`scripts/brief-compose.py:1534-1535`, `:1604`. `HTMLParser` gives a bare attribute the value `None`, which is
the same as absent, so:
- `<p data-decision data-decision-options>` composes the generic Yes / No card. That is the exact outcome the
  backlog #727 FAILS IF names ("a card with declared choices shows Yes / No");
- `data-decision-options="A|B" data-decision-rec` composes with no ★, and nothing says so.

**Fix:** record presence separately from value (for example `""` for a bare attribute, `None` only when
absent), so that `_choices` refuses a bare options attribute ("at least two") and a bare rec ("not one of").
Add the two inputs to the `_bad` table of the refusal case.

### MINOR F3: when options are declared, a nearby `.rec` line is ignored silently, so the page can disagree with its own card
`scripts/brief-compose.py:1356`. In the browser run, D1's `<p class="rec">Recommend: A.</p>` sat beside a card whose
★ was on B. Options-with-no-rec and a visible `.rec` line also loses the star the old card would have shown. The
doc says the `.rec` line is ignored, so this behaviour is intended; the gap is that nothing tells the author.
**Fix (optional):** at compose time, warn (not refuse) when a decision declares options and the next `.rec`
sibling exists but `data-decision-rec` is absent. Or record in §3a that `data-decision-rec` replaces the `.rec` line for that card.

### MINOR F4: five load-bearing clauses are killed by the suite but are not in the manifest
`scripts/mutations/brief-compose.json`. These are the empty-entry half of `len(opts) < 2 or "" in opts`, the orphan-rec refusal,
the `html_escape` on `data-ex-options`, the `data-ex-rec` write, and the click payload `send(tag, box, o)`.
Each was measured red above, so the risk is a later refactor that unbinds the case without anyone noticing,
not a gap in coverage today. **Fix:** add the five entries (117 → 122) and their `expected_mutations.py` count.

### Nit (not a finding)
`data-decision-options="★ A|A" data-decision-rec="A"` renders two buttons both labelled `★ A`. This is contrived,
and Other… still works. A choice of 300 characters renders one very wide button, because nothing truncates a choice (the old
rec label was cut at 40). Neither changes an answer.

## Not refuted
Escaping of option text, the emitted JS (`node --check` case plus a real Chromium run with no page errors),
a click sending exactly the choice, the answered state and the "all answered" count, option-less identity
(the self-test literal and the browser run), and reachability by a real hit-tested click.

VERDICT: CONVERGED

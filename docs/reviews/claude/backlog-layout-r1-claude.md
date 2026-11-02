Reviewed head: 07600a6c7aa64f5511ff5a57514dfc1dba9267d7

# backlog-layout, round 1, Claude half

Subject: `git diff origin/master...HEAD`. That diff adds `layout_body` and the `.seg`/`.prov`/`ol.enum` CSS to `scripts/gen-backlog-page.py`.
The Codex half was not read.

What was run against 07600a6c:
- `python3 scripts/gen-backlog-page.py --self-test` returned 221/221 passed, rc 0.
- `python3 scripts/gen-backlog-page.py --out <scratch>/bt.html` returned rc 0.
- `python3 scripts/check-theme-token-coverage.py` reported 0 unexplained.
- A scratch script laid out all 422 real rows. It dumped the blocks and list items of rows 2, 67, 89, 90, 189, 252, 307, 378, 405, 412, 418, 419, 444 and 448, and measured these across every row:
  - segment sizes;
  - provenance-line word counts;
  - list items that are fragments;
  - markers left at the end of a block.

Most rows read clearly better. For example, rows 307, 405 and 448 now show each labelled paragraph on its own line, with a one-line grey provenance. The findings below are the rows where the layout makes reading worse.

## Findings

### F1 (MEDIUM): an enumeration marker gets split from its item when the item opens with a bold label (rows 412, 418, 419)

`_label_cuts` (gen-backlog-page.py, the glyph-carry loop) carries only a glyph-only token in front of a label. A `(1)` marker contains parentheses, so it is not carried. The source text in row 412 is `...(run). (1) **Binary:** ... renders the added line. (2) **Symlink:** ...`, and it renders like this:

```
[PROV] — filed 2026-10-30 ... (run).
[SEG]  (1)
[SEG] Binary: a NUL byte ... renders the added line. (2)
[SEG] Symlink: docs/backlog.md replaced by ...
```

The reader sees a lone "(1)" on its own line. After that, each marker sits at the END of the previous paragraph instead of in front of its own. A scan of all 422 rows found 7 blocks ending in a bare marker, all in rows 412, 418 and 419. Row 419 has three of them.

**Fix:** in the carry loop, also carry a token that matches `^\((?:[a-z]|[1-9])\)$` (or `[a-z]\)` / `[1-9]\.`), so the cut moves in front of the marker. Add a fixture `x. (1) **A:** y. (2) **B:** z.` and a real-row case: no block's visible text ends in a bare marker.

### F2 (MEDIUM): the muted provenance line swallows the row's substantive text (rows 189, 89, plus 9 more over 40 words)

`_prov_span` ends the clause at the first depth-0 `. ` (period followed by a space), searching up to 700 characters. It does not stop at `?` or `!`, or at a sentence end inside `<em>`. It also does not stop at a ⭐/⛔ heading glyph. So the row's main argument ends up in 0.76rem grey sans text, which is styled as the line the reader is meant to skip:
- **Row 189 (98 words):** the line runs on from `...who asked it as: if reducing scope is unsafe, how about running the sweep in parallel — multiple containers each running a subset?` into `⭐ THE DISTINCTION THAT MAKES THIS SOUND WHERE backlog #174 IS NOT, and it is the whole reason this row exists: ...`. That second sentence is the row's thesis, and it is rendered as metadata.
- **Row 89 (59 words):** the line carries `MEASURED — the population, enumerated rather than recalled. *Group A, agent-authored (4):* explain-diff, brief, ...`. As a result, Group A sits in the grey line while the parallel Group B is in a normal paragraph.

Rows whose provenance line is over 40 words: 89 (59), 111 (71), 125 (53), 126 (46), 159 (48), 171 (53), 172 (49), 189 (98), 228 (43), 384 (46), 424 (63).

**Fix:**
- End the span at the first `.`, `?` or `!` followed by a space, at any depth outside a code span.
- Also end it before a ⭐/⛔/⚠ glyph or a `<strong>`.
- If the span is still over about 40 words, do not treat it as provenance; leave it in the segment.
- Add a real-row case: no `.prov` is over N words, and none contains ⭐ or ⛔.

### F3 (LOW): back-references are laid out as lists of fragments (rows 252, 378, 444)

`_enum_cuts` turns any in-order `(a) (b)` run into a list, including a run that only refers back to items listed earlier:
- **Row 378:** `FALSIFIER: each of the r3 fixtures prints a WARN (1) or CANNOT RUN (2).` renders as the items "(1) or CANNOT RUN" and "(2).".
- **Row 444:** `FAILS IF: ... no decision (a) or (b) is recorded.` renders as the items "(a) or" and "(b) is recorded.".
- **Row 252:** `(2) and (3) splitting ...` produces the item "(2) and".

All the words survive, but the sentence is broken across bullets that are not separate things.

**Fix:** refuse a run if any item, minus its marker, has fewer than 3 words or starts with `or`/`and`.

### F4 (LOW): the falsifier treats a block boundary as zero-width, so it cannot see a cut that joins or splits words

`visible_text` and the `_LAYOUT_TAG.sub` comparison in `_same_words` both concatenate text across `</div><div>`. A browser does not: it renders a line break there. The construction:

```
layout_body(md("see (x)**Fix:** y"))
→ '<div class="seg">see (x)</div><div class="seg"><strong>Fix:</strong> y</div>'
```

`_same_words` says True. But the reader's text changes from `see (x)Fix: y` to two lines. The reverse failure is also possible: a cut between two words with no whitespace between them would split a token, and the check would still pass.

I measured the real rows: 0 of 422 have a block boundary without whitespace on either side, so this is latent today.

**Fix:** in `_same_words`, map each inserted `<div ...>`/`<li>` to a separator before comparing. Alternatively, add a case asserting that every cut lands next to whitespace.

### Other questions in the brief, with nothing found

- **CSS:** `.prov` uses `var(--ink-3)` and `var(--sans)`. Both are defined in all four palette blocks. The theme-token check reports 0 unexplained. `--ink-3` contrast on `--card` is 4.60 light and 4.57 dark, which passes AA for small text. This page does not opt into the text-style switcher (`textstyle`), so there is nothing to respect there.
- **Other pages:** `page_markup` is unchanged. The other generators (goals, features, goal-tree, brief-compose) import only `cell_tags`, `bundle_tags`, `nearest_claim` and `normalise_tag` from this module, never `card`, `md` or the CSS. The status cell is still plain `md`. No other page changes.
- **Rows 2, 67, 90, 307, 405, 448** read better or the same.
- **Tags:** the tags `md` emits on real rows are code, strong, em, a and del, all inline. So no `<div>` lands inside a `<p>` and gets moved by the parser.

VERDICT: NOT CONVERGED

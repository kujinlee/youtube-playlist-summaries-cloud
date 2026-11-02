Reviewed head: ec26a2a35dcf412c5cc2bd2406467dcb5703fe69

# backlog-layout — round 3, Claude half

Subject: the r2 fold, `git diff ce241150..e6a7abd7 -- scripts/`, read at HEAD ec26a2a3 (the r2 fold plus the master merge
and the dashboard-entry fix). It looks at `_same_words_html` (the self-test's check that the visible words did not change), the three new
mutations, and the final tree as the owner will read it.

## Findings

### F1 — LOW — `scripts/gen-backlog-page.py:3961-3974` — fix_induced: true
**The same-words check now accepts a wrapper inserted INSIDE A TAG, which does change the visible words.** The r2 fold
replaced the `visible_text(old) != visible_text(new)` test with the byte-for-byte comparison. The byte test cannot see
where a wrapper sits. The `_LAYOUT_TAG` strip that the whitespace check then runs removes the whole host tag, and the
sentinel goes with it, so that boundary is never checked.
Reproducer (run through the function as written, extracted from `_self_test_body`):
`_same_words_html('<a href="u">x</a> y', '<a href="u<div class="seg">">x</a> y</div>')` → **True**. A browser shows
`">x y`, not `x y`. The r1 check (visible_text equality) refused this input. `layout_body` cannot produce it today,
because cuts are masked to text outside tags. But this check is the oracle that is meant to catch a `layout_body` that
does produce it.
Fix: keep both tests (`visible_text(old) == visible_text(new)` and the byte compare), or refuse any `\x00` in
`n_html` that falls inside a `<…>` span.

### F2 — LOW — `scripts/gen-backlog-page.py:3965-3969` — fix_induced: true
**The stack never checks tag NAMES, and it accepts a `<li>` under any wrapper, not just under `<ol class="enum">`.**
The comment says the stack strips "the `<li>` directly inside that `<ol>`". The code tests `stack[-1]`, which is any
wrapper, and a closer pops whatever is on top.
Reproducers: `_same_words_html("x y", '<div class="seg"><li>x y</li></div>')` → True (a stray list item, which a
browser gives a marker); `_same_words_html("x y", '<div class="seg">x y</li>')` → True (a closer that does not match its opener).
Neither one changes a word, so this is LOW. Both are malformed output that the oracle passes.
Fix: push the tag name with the flag; a closer must match the name it pops; `<li>` is a wrapper only when the top
entry is the `ol.enum` wrapper.

### F3 — LOW — oracle scope (`_same_words_html` and the all-rows case at `:4096`) — fix_induced: false
**No check over the real rows says a wrapper sits OUTSIDE every inline element.** Input:
`_same_words_html("<em>a b</em> c", '<em>a <div class="seg">b</em> c</div>')` → True, and the same holds inside
`<code>`. The r1 check had this gap too. The fixture case "a label nested inside another element is not split" covers it
for fixtures only. Measured at HEAD: 0 of 432 real rows put a `div`/`ol`/`li` inside an inline element, so nothing is
affected today. Fix (optional): add a depth-0 assertion to the all-rows case.

### Probed and refused correctly (not findings)
- Wrapper class already in the original HTML: not reachable. `md` escapes its input, and `page_markup` emits only
  `a code del em img script strong`, so the original HTML never holds a `div`, `ol` or `li`.
- An entity re-encoded (`&amp;` → `&#38;`): refused. Byte compare.
- Attribute order, or an extra attribute (`<div class="seg" id="z">`): refused. The tag is not a wrapper, so it is kept and the bytes differ.
- Self-closing `<div class="seg"/>`: refused. It is not a wrapper, so it is kept and the bytes differ.
- A cut inside an entity or a word: refused by the whitespace check.

### (2) False refusals — none
`--self-test`: **234/234 passed** at HEAD. The all-rows check, run on its own: **432 rows, 0 refused**. The rows are
432, not 422, because the master merge added rows.

### (3) The three new mutations
They are bound and correctly named. Each anchor matches the source text exactly (`:3973`, the `<li>` clause line, and
the `br = re.compile` line), and each names the case that its edit makes fail:
- Dropping the byte compare makes `alphabeta` pass, so the r2 Codex 3 case goes red.
- Dropping the `<li>` clause leaves `<li>` in `n_html`, so the bytes differ and the fixtures case goes red.
- `(?!)` for `<br>` makes the positive `alpha<br></div><div>beta` input fail its boundary check, so the r2 Codex 3 case goes red.
`EXPECTED_MUTATIONS` 58→61 matches.
**Run, not reasoned:** I applied each of the 3 manifest edits to a temp copy of `scripts/` and `docs/` outside the repo. Each
anchor matched exactly once, and each `--self-test` exited rc=1 with its `expect` case among the `[FAIL]` lines (4, 5
and 4 fails). The full 61-mutation sweep (`--only scripts/gen-backlog-page.py`) was started and had passed 10 of 61
cleanly before this doc was written. It was NOT waited out, so the other 58 are CI's to confirm.

### (4) Final-tree readability: rows rendered from HEAD
Rendered to a scratch HTML file outside the repo, using the page's `.seg`/`.prov`/`ol.enum` rules.
- **#2** (215 chars → 2 blocks): only marginally better. A `(filed 🟡)` line above one short paragraph, with nothing to gain at this length.
- **#90** (4,386 → 7 blocks): clearly better. Each `THE DEEPER PROBLEM` / `FIRST STEP` / `FALSIFIER` / `SHAPE` lead-in opens its own paragraph.
- **#307** (3,531 → 8 blocks, 2 muted): clearly better. The muted provenance, then one `⭐`/`⛔` claim per paragraph.
- **#405** (1,211 → 7 blocks): better. Design / Soundness / Measured / FAILS IF read as a short spec.
- **#448** (1,129 → 5 blocks): better. Observed / Fix direction / FAILS IF are separated, and the provenance is muted.
- **#67, the longest** (8,651 → 12 blocks): much better than one 8.6k-character paragraph. Its `(1) (2)` SHAPE run and its `(i)` run
  stay inline, which is the accepted under-split bias.

VERDICT: CONVERGED

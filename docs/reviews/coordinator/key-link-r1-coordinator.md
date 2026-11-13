# Round 1 — `key-link` (PR #489, backlog #470) — coordinator — NOT CONVERGED (both halves); route REDESIGN: the page reading rebuilt on one HTML tokenizer, every finding FIXED

Codex half: `docs/reviews/codex/key-link-r1-codex.md`. Claude half: `docs/reviews/claude/key-link-r1-claude.md`. Both reviewed `08ffe5d6`.

```yaml
round: 1
fixes_nontrivial: true
subject: key-link
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-1, severity: High, aim: deliverable, fix_induced: false, component: features-row-link, disposition: fixed}
  - {id: X-2, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-3, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-4, severity: Medium, aim: deliverable, fix_induced: false, component: missing-rows, disposition: fixed}
  - {id: X-5, severity: Medium, aim: deliverable, fix_induced: false, component: rule-2, disposition: fixed}
  - {id: X-6, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-7, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: false, component: features-row-link, disposition: fixed}
  - {id: C-F2, severity: Medium, aim: deliverable, fix_induced: false, component: check-page-links, disposition: fixed}
  - {id: C-F3, severity: Low, aim: deliverable, fix_induced: false, component: closure-prose, disposition: fixed}
  - {id: C-F4, severity: Low, aim: deliverable, fix_induced: false, component: missing-rows, disposition: fixed}
  - {id: C-F5, severity: Low, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: C-F6, severity: Low, aim: deliverable, fix_induced: false, component: goal-ids, disposition: fixed}
  - {id: C-F7, severity: Info, aim: deliverable, fix_induced: false, component: summary-links, disposition: decided}
```

**Both halves NOT CONVERGED.** Both built all five pages, and both found the same High: 29 rows on the features page put
an `<a>` inside an `<a>`. Codex found six more defects, and five of them had ONE cause. `page_markup.link_html` and
`check-page-links.py` read HTML with regexes (`TAG_SPLIT`, `VERBATIM`, id and href scans).

## The route: REDESIGN, not a patch per case

Four Codex findings (2, 3, 6 and 7) and Claude's F5 come from the regexes that read HTML. A parser over open-ended
input is a SURFACE (`docs/review-method.md` §0 Q0). Patching each input would keep that surface open, so the fold
replaced it. The decision is logged as route `redesign` in `docs/reviews/decision-scheme/decision-log.jsonl`, and the
`accrete` route was skipped.

**ONE tokenizer.** `page_markup.page_tokens` is Python's `html.parser`. It splits a built page into tokens whose raw
spans cover the page exactly, end to end. It tracks one open-element stack for the whole document, so a comment,
script or style does not reset it. Each data token carries its DECODED text and an `exempt` flag. Each start tag
carries `in_a`. `text_keys(token)` is the single answer to "is this a key that should be a link?". `link_html` uses it
to insert links, and rule 1 of `check-page-links.py` uses it to report keys that were not linked. Ids and hrefs come
from parsed start tags, so a string inside a script or a comment is not an element. `link_html` splices each link into
the raw text of its node and never re-serialises the page.

**Byte-preservation, measured.** I built all five pages once with `link_html` replaced by the identity function, and
once with the real one. After removing the inserted links and the marked-missing spans from both builds, the only
lines that differ are the build timestamps.

## Per finding

**X-1 / C-F1 (High), 29 nested `<a>` on the features page — FIXED at the cause.** `gen-features-page` rendered a row's
text with `inline_md` inside the row's own link. It now uses `page_markup.render_unlinked`, which is the same function
the dashboard's `_inline_unlinked` now aliases (one function, not two). `link_html` can no longer insert an `<a>`
inside an open `<a>`, because the tokenizer's stack holds the `<a>` across comments and styles. Covering checks:
- case *a key in a linked row's text is not a second `<a>` inside the row's link* (gen-features-page), with its
  mutation;
- corpus: features has 0 nested `<a>`. The control, the old head's pages under the new checker, reports 33 nested
  start tags on features.

**C-F2 (Medium), no rule could see F1 — FIXED.** Rule 1b: no `<a>` is opened while an `<a>` is open, and none is left
open at the end. Covering cases: *rule 1b: the features row of round 1…* (the row from the review, verbatim),
*an `<a>` left open at the end is found*, and *a page with an `<a>` in an `<a>` FAILS*. Each case has a mutation.

**X-2 / C-F5, a quoted `>` corrupted an attribute — FIXED.** The parser reads attribute values. Case
*link_html: a quoted `>` in an attribute is not a tag's end, and the attribute is untouched* (Codex's input).

**X-3, a comment, style or script inside `<a>` / `<code>` reset the state — FIXED.** The stack is document-wide.
Cases: comment inside `<a>`, comment inside `<code>`, and `<style>` inside `<a>` (all three of Codex's shapes). The
mutation *the open-element stack is reset at a comment* is killed by the first case.

**X-6, the linker and rule 1 disagreed — FIXED by sharing `text_keys`.** I made one decision per input, and the
linker and the checker follow it the same way:
- `&#35;` is decoded first, so `backlog &#35;7` is a key, linked with its raw spelling kept;
- `<textarea>` is exempt in both;
- `backlog <b>#7</b>` is split across two text nodes, so it is NOT a key in either. That bound is stated in
  `page_markup` and in the checker's docstring.

Case *the linker and rule 1 AGREE*: on eight review inputs, `unlinked_keys(link_html(x)) == []` and no nested `<a>`.

**X-7, ids inside script strings — FIXED.** Ids come from parsed start tags. Cases: *an id-like string inside a SCRIPT
is not an element's id*, *…so a link to it dangles* (Codex's input), and *rule 4: an id inside a script string is not a
declaration*.

**X-4 / C-F3 / C-F4, 13 links to 9 rows that never existed — FIXED by design, and the prose corrected.** The rows are
221, 241, 242, 245–248, 293 and 411. `gen-backlog-page.publish_rows` reads the rows with the backlog page's own parser
and gives them to `page_markup.use_rows`. Every generator calls it, and a key naming any other row renders as
`<span class="key-missing" title="no such backlog row">`. That marked text is exempt in both the linker and the
checker. It is not a link, so it cannot dangle. Covering cases and mutations are in `page_markup` (no link, marked,
scan's branch, not re-linked), `gen-backlog-page` (`publish_rows` reads the rows, and warns when the file is
unreadable) and `gen-goals-page` (a chip naming a missing row).

Row 470's closure text no longer cites the nonexistent rows as keys. Its "11" is replaced by the measured "13
page-to-row links, 9 rows". The dashboard entry is corrected the same way.

C-F4's renumbering caveat is stated in the checker's bounds: a citation of a renumbered row that names a different
existing row resolves cleanly, and no rule here can see it.

**CI for rule 3 (X-4's second half) — FEASIBLE, done without fixtures, using the real data.** A new CI step runs
`check-page-links.py --build --ci`. It builds the four pages that a checkout alone can build: dashboard, goals and
features as `--fragment-only` (no Ask tray needed), and the backlog table whole. It then runs every page rule on them.
The goal-tree page renders from the gitignored local log, so it is NOT RUN in CI. The step says so, and links to it
are counted as unchecked. Measured locally with Python 3.12 (CI's version), `HOME` empty and no `gh` login: rc 0, four
pages, 6 inline scripts parsed.

**X-5, rule 2 exempted everything after `def self_test` — FIXED structurally.** Rule 2 now reads each script's AST.
Only the BODIES of `_self_test*` / `self_test*` functions are exempt. String literals, f-strings and `+` chains are
joined, so `"/goals" + "#" + slug` is found. Comments and docstrings are not read. A file that does not parse is
reported, never passed. Cases cover each of these, using Codex's inputs. The live `scripts/` tree is still clean.

**C-F6, goal-card ids shared the chrome's namespace — FIXED.** `page_markup.goal_id(slug)` returns `g-<slug>`.
`gen-goals-page` emits it, and `key_link("goal", …)` links to it. Case *key_link: goal* and the gen-goals-page id
cases are updated. The mutation *the goal card id loses its g- prefix* is killed.

**C-F7, links inside `<summary>` — DECIDED, kept.** It is valid HTML, and a key should open its home page, so a press
on the key navigates instead of toggling the disclosure. This is written in `page_markup`'s tokenizer comment. Nothing
is built for it.

## The corpus (the main evidence)

I ran `python3 scripts/check-page-links.py --build` on this branch: **rc 0**. It checked 7,913 fragment links and found
none dangling. 0 of them point at a page not built here.

| Page | nested `<a>` | duplicate ids | inline scripts (`node --check`) | unlinked keys | dangling | marked-missing keys |
|---|---|---|---|---|---|---|
| dashboard | 0 | 0 | 3, 0 fail | 0 | 0 | 1 |
| backlog-table | 0 | 0 | 3, 0 fail | 0 | 0 | 50 |
| goals | 0 | 0 | 2, 0 fail | 0 | 0 | 0 |
| features | 0 | 0 | 2, 0 fail | 0 | 0 | 0 |
| goal-tree | 0 | 0 | 1, 0 fail | 0 | 0 | 113 |

Running `link_html` a second time over each built page changes 0 bytes.

New rules 4 and 5 make duplicate ids and unparseable inline scripts gates. A missing `node` is CANNOT RUN, never a
pass.

## Counts

| Suite | Self-test cases before → after |
|---|---|
| page_markup | 123 → 145 |
| check-page-links | 36 → 68 |
| gen-features-page | 18 → 19 |
| gen-goals-page | 81 → 83 |
| gen-backlog-page | 237 → 239 |

| Manifest | Mutation entries before → after |
|---|---|
| page_markup | 23 → 36 |
| check-page-links | 16 → 30 (7 regex-era entries rebound or replaced) |
| gen-features-page | 15 → 16 |
| gen-goals-page | 28 → 29 |
| gen-backlog-page | 65 → 67 |

`EXPECTED_MUTATIONS` and the `EXAMINED_KEYS` pins are updated to match.

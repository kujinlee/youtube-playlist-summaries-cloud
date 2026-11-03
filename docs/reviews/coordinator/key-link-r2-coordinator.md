# Round 2 — `key-link` (PR #489, backlog #470) — coordinator — NOT CONVERGED (Codex); route SPLIT: a supported HTML subset, refused outside it, every finding FIXED

Codex half: `docs/reviews/codex/key-link-r2-codex.md`, which reviewed `668e4cc1`.

REVIEW GAP: claude — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 2
fixes_nontrivial: true
subject: key-link
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X-1, severity: Medium, aim: deliverable, fix_induced: false, component: rule-2, disposition: fixed}
  - {id: X-2, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-3, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-4, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-5, severity: Medium, aim: deliverable, fix_induced: true, component: page-reading, disposition: fixed}
  - {id: X-6, severity: Medium, aim: deliverable, fix_induced: false, component: page-reading, disposition: fixed}
  - {id: X-7, severity: Low, aim: deliverable, fix_induced: true, component: page-reading, disposition: fixed}
  - {id: X-8, severity: Low, aim: deliverable, fix_induced: true, component: page-reading, disposition: fixed}
```

The Codex half is NOT CONVERGED with eight findings. One is about rule 2 (X-1). The other seven (X-2 to X-8) have one
cause. On malformed HTML, or HTML no generator of ours emits, Python's `html.parser` and a browser's HTML5 tree builder
disagree about what is text. The linker and the checker still agreed with each other, because both read through the
same tokenizer. What they disagreed with was the browser.

## The route: SPLIT — a supported subset, not HTML5 emulation

Reaching browser parity case by case is the surface trap that `docs/review-method.md` §0 Q0 warns about. These pages
come from our own five generators, not from arbitrary authors. So the fold **defines a subset in which the two readers
agree, and refuses everything outside it.** The definition lives in one function, `page_markup.subset_problems(page)`.
It returns `line N: <construct>` for every construct outside the subset:

- **Exact token spans.** Each token's raw bytes are exactly that token. Nothing is skipped by the parser (`</>`),
  nothing is swallowed by a start tag (an unterminated `<script>` on 3.12), there is no byte before the first token,
  and text contains no literal `<`.
- **One strict open-element stack.** Every non-void element is closed explicitly and in order. The void set is fixed
  (`VOID`). Only a void element, or an element inside `<svg>`/`<math>`, may self-close. An end tag on a void element is
  refused.
- **No implied end tags.** A start tag that a browser would answer by closing an open element is refused. Modelled:
  a `<p>` closer inside a `<p>` (button scope), `<li>` in `<li>` (stopping at its own list), `<dt>`/`<dd>`, a heading
  inside a heading, `<option>`/`<optgroup>`, `<button>`/`<form>` in themselves, and table parts by depth (stopping at
  their own `<table>`).
- **Content a browser moves or reads as text.** No start tag inside `<script>`, `<style>`, `<textarea>` or `<title>`.
  No text or element that a browser would move out of a table, or drop from a `<select>`.
- **Comments and declarations.** Every comment is closed by `-->`, never `--!>`, `<!-->` or `<!--->`. No CDATA, marked
  section or processing instruction. The only declaration allowed is `<!DOCTYPE html>`. `<plaintext>`, `<xmp>`,
  `<noscript>`, `<noembed>`, `<noframes>` and `<iframe>` are refused.
- **Character references.** Every one ends with `;`, in text and in attribute values.
- **Parser errors.** The `AssertionError` that 3.12's parser raises on `<![foo]>` is a refusal (`OutsideSubset`), not a
  crash.

The bound is stated in `page_markup`. Three things are neither refused nor emulated: HTML elements that break out of
foreign content, the implied `<html>`/`<head>`/`<body>` wrappers (which move no text), and the adoption agency for an
`<a>` inside an `<a>`. The last one is rule 1b's job to report.

**Enforcement.**
- `link_html` calls `require_subset` first, and raises `OutsideSubset` (a `ValueError`) instead of splicing into such a
  page.
- `check-page-links.py` has a new **rule 0**. A page outside the subset FAILS (rc 1), and the output names each
  construct. Its other rules are NOT RUN, and the output says so, because they would be reading a page no browser shows.
  Rule 3 counts links that point at such a page as unchecked.

The route is logged as `split` in `docs/reviews/decision-scheme/decision-log.jsonl`. The r1 `redesign` row now records
`outcome: continued`, with what r2 observed: the bet was lost on its own named observation, because the defects were
again caused by how pages are READ. The split's prediction was written before r3. It holds if r3 finds no page INSIDE
the subset on which `html.parser` (3.12 or 3.14) and a browser disagree about what is text, an element's id, or which
element is open.

## The corpus (the evidence that the subset is ours)

All five built pages and their fragments, under 3.14 and under 3.12, are inside the subset after **one generator
fix**. Before the fix, the only construct outside it was the one round 1 noted: the composed pages (`backlog-table`,
`dashboard`, `features`, `goals`) left `<div id="tray">` open at `</body>`.

**Fix: `brief-compose.extract_tray`.** It lifted the tray markup with a lazy `<div id="tray".*?</div>\s*</div>`. On a
tray whose inner div nests another div, that match stops one `</div>` short. Every composed page then carried the
truncated copy forward, because the next compose lifts it verbatim. The extracted slice now has the missing `</div>`s
appended, so it closes everything it opened. This repairs a truncated source and a whole one alike, in one pass. Two
cases cover it (a nested tray, and a truncated source tray) plus one mutation. **No construct is allowlisted.**

| Page (`--build`) | rule 0 | rules 1, 1b, 3, 4, 5 |
|---|---|---|
| dashboard | inside | 0 failures |
| backlog-table | inside | 0 failures |
| goals | inside | 0 failures |
| features | inside | 0 failures |
| goal-tree | inside | 0 failures |

Run totals: `--build` rc 0, with 7,914 fragment links checked and 11 inline scripts parsed. `--build --ci` rc 0 under
3.14 and under 3.12 (CI's Python). The per-gate numbers are in the commit report.

## Per finding

Each case below uses the review's own input, verbatim. Each has a mutation in `scripts/mutations/*.json`, and each
mutation is attributed to the case it names.

**X-1, rule 2 dropped `%`-formatted hrefs (and `.format`, `join`, f-string constant parts) — FIXED.** `_literal` now
reads the following forms and substitutes each literal argument for its conversion, writing `{}` for an argument that
is not a literal:
- `"…" % x` and `"…" % (a, b)`;
- `"…".format(…)`, with positional and named fields;
- `"…".join([…])`;
- f-strings, whose constant parts like `{'#'}` are read as text.

The children `_literal` read are marked as parts (`_parts`), so a piece is not reported a second time on its own, and
an href passed as an argument to `.format` is still found. Cases: `"/goals#%s" % slug` and `"/pull/%s" % n` (the review's
inputs), a `%` tuple, `.format` positional and named, a join, an f-string constant, an href inside a format argument,
and a `%%` / non-href join negative. The mutations, seven, cover: Mod read; argument substitution; named lookup;
`.format`; join; f-string constants; parts not re-reported.
The bound is restated in the checker's docstring: assembly through VARIABLES or through a `%` DICT is not seen.

**X-2, elements inside `<textarea>` on 3.12 — FIXED by the subset.** A start tag inside RCDATA is refused under 3.12.
Under 3.14 the parser reads that markup as text containing a `<`, which is refused too. Cases: page_markup *Codex r2 2*,
checker *rule 0: a page with r2 2: a textarea FAILS*. The RCDATA rule is reached under 3.12 only, so the self-test
drives it on either Python by emptying `RCDATA_CONTENT_ELEMENTS` for one case. Its mutation is killed under both.

**X-3, `<script/>` and an unterminated `<script>` — FIXED.** A non-void element that self-closes is refused. An
unterminated script is refused for its swallowed bytes (3.12) and for never being closed (both versions). Cases:
page_markup *Codex r2 3* ×2, checker *r2 3* ×2.

**X-4, `<a/>` — FIXED.** It is a non-void self-close. Cases: page_markup *Codex r2 4*, checker *r2 4*.

**X-5, the exempt stack — FIXED, both halves.**
- (a) `<p class="key-missing">x<div>…` is an implied `</p>`, and is refused.
- (b) `page_tokens` now keeps ONE real stack. Every non-void element is pushed, and an end tag pops to its match. So
  the close of an unmarked inner `<span>` no longer pops the marked outer span. Within the subset's strict nesting this
  stack is exact.

Cases: *Codex r2 5a*, and *page_tokens: Codex r2 5b* (the review's input: zero subset problems, and `link_html` leaves
it byte-identical). Mutation: *the exempt stack holds only exempt elements again*.

**X-6, an unterminated comment or CDATA, and `<plaintext>` — FIXED.**
- Under 3.14 a comment whose span is not `<!--…-->` is refused. Under 3.12 the same input is read as a text `<`, which
  is also refused.
- `--!>`, `<!-->` and `<!--->` are refused, because a browser ends a comment there and 3.12 reads on.
- `<plaintext>` is UNSUPPORTED.

Since `link_html` refuses these pages, the review's non-idempotence cannot arise. Cases: three verbatim inputs, a
`<!--a--!>b-->` case, and the comment-rule case.

**X-7, `&amp` before letters — FIXED twice.** The subset refuses any reference without its `;` (`_BARE_REF`), in text
and in attributes. Also, `_decode_map` no longer lets a named reference with no `;` run on through the letters after
it, so each decoded character maps to its own raw interval. Cases:
- *Codex r2 7* (refused);
- *`_decode_map`: a named reference with no `;` is not one piece*;
- *`&amp;` and a numeric reference each map to their own raw interval*.

**X-8, `</>` and `<![foo]>` — FIXED.** Bytes the parser reads as no token are refused: before the first token, after a
start tag, or after an end tag. The 3.12 `AssertionError` is caught in `_events` and becomes a refusal. The self-test
drives that path on either Python by raising it from a patched handler. Cases: the two verbatim inputs, plus *an
AssertionError from inside html.parser is a refusal, never a crash*.

## Python versions

CI runs Python 3.12, and several of these findings read differently on 3.12 and 3.14. Every suite and sweep below ran
under both `python3` (3.14.4) and `/usr/local/bin/python3.12` (3.12.9).

## Counts

| Suite | Self-test cases before → after |
|---|---|
| page_markup | 145 → 192 |
| check-page-links | 68 → 88 |
| brief-compose | 194 → 196 |

| Manifest | Mutation entries before → after |
|---|---|
| page_markup | 36 → 72 (5 r1 entries rebound to the new stack) |
| check-page-links | 30 → 39 (2 rebound) |
| brief-compose | 45 → 46 (1 rebound) |

`EXPECTED_MUTATIONS` is updated to match.

## The round cap

Round 3 is the last folding round. From round 4, findings are FILED unless they are a BLOCKER
(`docs/review-method.md` §0 Q4c).

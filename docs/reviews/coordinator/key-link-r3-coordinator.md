# Round 3 — `key-link` (PR #489, backlog #470) — coordinator — NOT CONVERGED (Claude); one BLOCKER, every finding FIXED, and the class closed by a property over every generator's renderer

Claude half: `docs/reviews/claude/key-link-r3-claude.md`, which reviewed `0ea207e8`.

REVIEW GAP: codex — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 3
fixes_nontrivial: true
subject: key-link
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: true, component: page-reading, disposition: fixed}
  - {id: C-F2, severity: Medium, aim: deliverable, fix_induced: false, component: inline-renderer, disposition: fixed}
  - {id: C-F3, severity: Low, aim: deliverable, fix_induced: true, component: page-reading, disposition: fixed}
  - {id: C-F4, severity: Low, aim: deliverable, fix_induced: true, component: page-reading, disposition: fixed}
```

The Claude half is NOT CONVERGED with four findings. F1 is a BLOCKER: the subset round 2 introduced is stricter than
the text our own renderer emits. A URL in quotes or angle brackets was cut in the middle of a character reference,
and the page then fell outside the subset, so `link_html` raised inside all five generators. F2 is the same class (renderer
output the page gate refuses), and it predates round 2. F3 is a gap in the subset's model, and it falsifies the round 2
prediction on its own terms. F4 is a set of comments that described one patch release of 3.12 as if it were all of them.

## F1 — a URL ending in half a reference — FIXED, instance and class

**The design: drop the cut reference, matching on the escaped text as before.** `scan` reads ESCAPED text, where every
`&` begins a reference that ends in `;`. So a URL match that ends in `&` plus letters, digits or `#` with no `;` can only
have cut such a reference. The new `page_markup.drop_cut_reference` hands that whole reference back to the prose, then
trims any punctuation it exposed (`"https://x.ee/a."` links `https://x.ee/a`), and repeats until nothing changes. The
link then sits next to the author's `"` as `&quot;`, intact.

**Why not match URLs against the decoded text and map back.** A decoded match would see the author's `"`, `'` and `>`.
`INLINE_URL` admits all three inside a URL today (`[^\s<]`), so it would change which URLs exist across the corpus in
order to fix a cut that only ever lands at the URL's end. It would also be the only construct in `scan` that does not
read escaped text. The local fix keeps one reading.

**The instance cases** use the review's four inputs verbatim, plus the dashboard entry it built, plus the exposed-
punctuation shape. The review's own proposed class case, every character `escape` rewrites hard after and hard before
a URL, is a case too.

**The class: a property over every generator's renderer** (`check-page-links.py`: `GENERATOR_RENDERERS`,
`fuzz_inputs`, `generator_renderers`, `renderer_problems`). Each generator's renderer for author text is read by its
own name in its own module, not as `page_markup`'s, because a generator could stop using that. The eight are:

- `gen-dashboard._prose`, `_inline` and `_inline_unlinked`;
- `gen-backlog-page.md`;
- `gen-goals-page.inline_md`;
- `gen-features-page.inline_md` and `inline_unlinked`;
- `goal-tree._html_line`.

Each renderer's output is wrapped where that generator places it (a `<div>`, `<p>`, `<td>` in a table, `<a>`, `<li><a>`,
`<pre>`) and then linked. Four failures are reported: `link_html` RAISES (a crash counts as a failure and is never
swallowed), the linked page is outside the subset, it nests an `<a>` in an `<a>`, or a second `link_html` changes it.

- **The corpus:** the review's 7 inputs verbatim, then 3,000 strings of 1 to 24 tokens drawn by `random.Random(470)`.
- **The alphabet:** `< > & " '`, space, `\n`, `\n\n`, tab, U+00A0, two URLs, `backlog #7`, `PR #3`, `[ ] ( )`,
  `](https://b.c)`, a backtick, `*`, `**`, `_`, `~~`, `&nbsp;`, a `;`-less `&amp`, `&#35;`, `. , ; :`, words, `- `, `|`
  and `#`.
- **The scale:** 3,007 inputs × 8 renderers = 24,056 compositions.

**What it found.** On its first run over the fixed tree it found a THIRD instance of the class. A `[x](y)` written in
text that `render_unlinked` renders, which is the body of a generator's own `<a>`, still became an `<a>`. The case prints the first
three failures, and all three came through `gen-dashboard._inline_unlinked`. It is fixed with F2 (below). After that: **0 failures in 24,056.**

**The control.** A prototype of the same property, run against the head's `page_markup.py`, reported 1,442 failures:
`&quot`, `&#x27`, `&gt`, `&lt` and `&amp` cut off a URL, through `gen-dashboard._prose` and the rest. So the property is
not one that cannot fail.

**Its own falsifiers are cases:** a renderer outside the subset, one nesting an `<a>`, and one that raises are each
reported; the corpus is seeded and leads with the review's inputs; the seed and the count each move the draw; every
renderer in the table is read; and a root with no generators RAISES rather than checking an empty set.

**Containment: loud, unchanged.** Every generator calls `link_html` before it writes anything, so a refusal leaves the
PREVIOUS page in place: stale, never half-written. On a non-zero exit, `.claude/hooks/regen-dashboard.sh`,
`regen-backlog-page.sh`, `regen-goals-page.sh` and `regen-features-page.sh` each:

- print "the page was NOT regenerated";
- print the last four lines of output, which name `OutsideSubset` and the construct;
- print "the page … is now STALE";
- exit 0.

`regen-pages.sh` prints "generated pages may be STALE". Nothing swallows the error. ⚠ **The CHANNEL is weak, though.** It
is PostToolUse hook stdout on exit 0, the channel this repo has measured reaching nobody (the 2026-09-11 `GROUPS`
refusal: a hard refusal on that channel let eight rows accumulate). That is not changed here; the property makes the
refusal unreachable from the generators' own renderers, over the corpus above. Whether the hooks should surface a
failure on a stronger channel is a separate question, and is offered for filing.

## F2 — a URL as a link's text nested an `<a>` — FIXED

`scan(…, keys=False)` is the scan of a link's own text, and it now makes no link of any kind: no key, no bare URL,
and (from the property) no `[x](y)`, which prints as itself. That is the module's rule for markup it will not render:
unpaired delimiters print as themselves, because dropping text is the worse defect. `render_unlinked` says so. The
cases are the review's input verbatim, a bare URL in an unlinked body, and a markdown link in an unlinked body. There is
a mutation for each guard.

## F3 — `<p>` closers and whitespace the subset did not model — FIXED

- **`_P_CLOSERS`** is now the whole set from the HTML Standard. These are the start tags the "in body" insertion mode
  answers with "close a p element" (§13.2.6.4.7), cited in the comment and taken whole rather than added name by name.
  It adds the review's seven (`li`, `dd`, `dt`, `summary`, `center`, `dir`, `listing`) and `plaintext`/`xmp`, which
  were already UNSUPPORTED.
- **`_BUTTON_SCOPE`** is now the spec's scope list as well (§13.2.4.2). It adds `applet`, `marquee` and `object`.
  Without them, a `<p>` OUTSIDE an `<object>` was taken to be closed by a `<div>` inside it. That over-refused, and
  each reader agrees it does not close.
- **Table text** is tested against ASCII whitespace only (`ASCII_WHITESPACE`, tab, LF, FF, CR and space), so U+00A0 is
  text a browser foster-parents.

**The cases** are each of the seven closers (the review's inputs), `&nbsp;` in a table (verbatim), ASCII whitespace in
a table (accepted), and the `<object>` scope. The mutations are three, and the table-text anchor of round 2 is rebound to
the new expression.

**The differential (parse5).** `parse5` is the HTML5 tree builder jsdom uses, from the main checkout's `node_modules`.
`html5lib` is not installed. For every page the subset says is OK, the element path of each non-whitespace text node is
compared between the two readers: under `html.parser`, the subset's own strict stack; under parse5, the tree's
ancestors. `html`, `head`, `body` and an implied `tbody` are dropped from both paths, and the first newline after
`<pre>` / `<textarea>` / `<listing>` is the one stated bound.

- **The corpus:** the 9 built pages (`--build`: five pages and four fragments), the 24,056 property pages, and 21
  handcrafted bodies. Those are the review's F3 inputs plus nested lists, nested `<dl>`, `<details>`, a table cell
  holding a `<p>`, `<button>`, `<select>`, headings, and the three scope elements.
- **Result:** 24,077 pages, 24,069 inside the subset, **0 disagreements**. The 8 outside are 8 of the handcrafted ones.
- **Control:** the head's subset accepts 18 of the 21 handcrafted bodies, and the same differential finds **8
  disagreements** among them: exactly the review's seven closers and `&nbsp;` in a table.

**The round 2 split prediction.** The row in `docs/reviews/decision-scheme/decision-log.jsonl` said the split holds
"if r3 finds no page INSIDE the subset on which `html.parser` … and a browser disagree … about which element is open".
F3 is such a page, so **the prediction is refuted as written**. This fold does not score the row: `outcome` stays null.
Scoring it `continued` obliges a next route (trigger 3), and that is a call about the unit's ladder, not about this
fold. It is flagged to the coordinator.

## F4 — comments that named 3.12.9's parser as "3.12's" — FIXED

Measured on the interpreters to hand:

| Behaviour | 3.12.9 | 3.12.12 | 3.14.4 |
|---|---|---|---|
| An unterminated `<script>` swallows its text | yes | no | no |
| Tags are read inside `<title>` / `<textarea>` (no `RCDATA_CONTENT_ELEMENTS`) | yes | no | no |
| `--!>` does not end a comment | yes | no | no |
| `<![foo]>` raises `AssertionError` | yes | no | no |

The comments now say "old 3.12", and one block in the subset comment defines it with these measurements. That block
says CI runs 3.12.15, which was NOT available to measure (`uv python install 3.12.15`: no download for this platform;
the newest is 3.12.12). The guards stay, because a local `python3.12` is 3.12.9. The `check-page-links` rule 0
comment names 3.12.9 too.

**The case** pins the comments' claim on whatever interpreter runs the suite: a parser raises on `<![foo]>` exactly
when it lacks `RCDATA_CONTENT_ELEMENTS`. **No mutation:** the claim is about the standard library, and no line of
ours decides it. The two guards an old 3.12 needs already have driven cases and mutations, on any Python.

**The round 2 parity claim, restated with its subject.** "`--build --ci` rc 0 under 3.12 (CI's Python)" was measured on
3.12.9. In this fold, `--build --ci` is rc 0 under 3.14.4, 3.12.9 and 3.12.12. Under 3.12.15 it is NOT RUN locally;
CI runs it.

## Counts

| Suite | Self-test cases before → after |
|---|---|
| page_markup | 192 → 205 |
| check-page-links | 88 → 94 |

| Manifest | Mutation entries before → after |
|---|---|
| page_markup | 72 → 79 (1 rebound) |
| check-page-links | 39 → 44 |

`EXPECTED_MUTATIONS` is updated to match.

## The arming condition, stated

Two consecutive rounds now carry fix-induced findings in one component, `page-reading`: round 2's X-5, X-7 and X-8,
and round 3's F1, F3 and F4. That is the THRASHING shape `docs/dev-process.md` names as the Phase 6 trigger. The
property and the differential are this fold's answer to the class: they read every renderer's output and a browser's
tree, where the earlier rounds read examples. Whether a Phase 6 review is convened is the coordinator's call.

## The round cap

Round 3 was the last folding round. **Round 4 is the final-tree check under the cap.** From round 4, findings are FILED
unless they are a BLOCKER (`docs/review-method.md` §0 Q4c).

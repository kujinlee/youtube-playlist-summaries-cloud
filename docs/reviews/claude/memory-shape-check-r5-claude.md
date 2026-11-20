Reviewed head: f03fe93aefef25a496f939fd9c55e7802f4cc7f8

# Memory shape check, round 5, Claude half

Subject: `git diff 011a0094..1418c49a` (the r4 fold: a raw HTML tag's interior is a third uncertain
region), reviewed in the tree at `f03fe93a`. Past the round cap (Q4c): non-BLOCKER findings are FILED.

## What was run (all measured, 2026-11-20)

| Check | Result |
|---|---|
| `python3 scripts/check-memory-shape.py --self-test` | 159/159 passed |
| `python3 scripts/check-memory-shape.py` | ok, 195 files in docs/memory, rc 0 |
| `python3 scripts/check-fixture-variation.py --self-test` | 67/67 passed, rc 0 |
| All 102 mutations of `scripts/mutations/check-memory-shape.json`, on a scratch copy | 102 killed, 0 anchor misses |
| The 11 new mutations, every failing case listed | each fails its `expect` case; reasons below |
| Fold removed (mutation 91, which is the pre-fold `uncertain_regions`) | 19 cases fail: the 8 new CANNOT-READ inputs at hop 1 and hop 2 (16), the reported input, the changed `link_reading` normalisation case, and the `uncertain_regions` unit case |
| Oracle (`markdown-it` 14 with html on + `html.parser`, reused from the r4 fold scratchpad) over hand inputs | see below |
| 40,000-document fuzz, raw-tag alphabet only (`<span`, `<div`, `</b`, `title=`, `=`, both quotes, `>`, `<`, `\n`, `\r\n`, `- `, `> `, `\`, backtick, `<a/`, `<3`, `<-`, `&quot;`, links), seeds 0-39,999 | **0** sure links the page hides; 19,476 documents hold an uncertain link |
| The same fuzz with markdown link/image syntax added (`![`, `[x](`, `](`, `)`, `(<`, `<./`, ` "`) | **165** sure links the page hides (finding 1) |
| Shipping-set edge pin, merge-base vs head, read with `check-shipping-sets.exec_edges` | merge-base 347 / `f52dc45f48609f44`; head 349 / `df1ef55a52b10da7`; gained exactly the two edges the comment names; lost 0 |

## Trying to refute "no sure link is hidden" inside a raw tag

Every input the brief listed, through the oracle and through `link_reading` at the head. None
produced a sure link the page hides:

- quoted `>` (`<span title="a>b [[t1]]">`), single quotes, `<a b='x">[[t1]]'>`: uncertain, hidden. Correct.
- `=` with no value (`<a b= >[[t1]]`), `<a b=c>[[t1]]`, `<a b="x">[[t1]]`: sure, and shown. Correct.
- backslash (`<a b="x\">[[t1]]">`): HTML has no escape, the quote closes at `\"`, `[[t1]]` is shown; sure. Correct.
- `<` inside an attribute, `<x-y z="[[t1]]">`, tab separator, `<a/b="[[t1]]">`: uncertain. Correct (the last is shown: over-refusal, finding 4).
- a tag across lines (`x <span\ntitle="[[t1]]">`), CRLF (`a <b\r\nc="[[t1]]">`), a list item and a blockquote continuing the tag: uncertain to the end of text; hidden. Correct.
- a tag ending exactly at the end of the text, `</span title="[[t1]]">`: correct.
- `<3 [[t1]]>`, `<- [[t1]] ->`: no region, and markdown-it escapes both to text; sure and shown. Correct.
- `` `<a` [[t1]] ``: uncertain to the end of the text, but shown (finding 4, the stated price).

I traced `tag_end` against the WHATWG tokenizer's tag-name, before/after-attribute-name,
before-value, quoted, unquoted and after-quoted states, including `=` as the first character of an
attribute name and a quote in a name or unquoted value: it agrees on every transition I could
construct, and breaks to the end of the text at any newline, which is the conservative side.

## Findings

### 1. MAJOR — a link inside a MARKDOWN-generated attribute is SURE, and the page hides it (measured; not fix-induced)

`scripts/check-memory-shape.py:350` (`uncertain_regions`) and `:359` (`link_reading`). The fold
closed raw tags, but markdown-it writes attributes of its own: an image's `alt`, a link's `title`
and a link's `href`. Text in any of them is read as a sure link and is not on the page.

| Input (MEMORY.md body) | markdown-it renders | `link_reading` at head |
|---|---|---|
| `[Alpha](alpha.md "see [[beta]]")` | `title="see [[beta]]"` | `beta.md` SURE |
| `![diagram [[t1]]](img.png)` | `alt="diagram [[t1]]"` | `t1.md` SURE |
| `![[x](t1.md)](img.png)` | `alt="x"` | `t1.md` SURE |
| `![see [[t1]]][r]` + `[r]: img.png` | `alt="see [[t1]]"` | `t1.md` SURE |
| `[b](<./t2 [[t1]]>)`, `[b](<#x [[t1]]>)` | `href="./t2%20%5B%5Bt1%5D%5D"` | `t1.md` SURE |
| `[b](t2.md#[[t1]])`, `[a](x?[[t1]])` | `[[t1]]` percent-encoded in `href` | `t1.md` SURE |

End to end through `index_violations`: an index whose only line is
`- [Alpha](alpha.md "see [[beta]]")`, with `alpha.md` and `beta.md` present, returns `[]` — an
all-clear, while a rendered page shows no link to `beta.md`. The image and angle-destination forms
likewise keep `alpha.md` reached with no CANNOT-READ. The random fuzz found 165 such documents in
40,000 once link and image syntax was in the alphabet, against 0 for the raw-tag alphabet.

This is the same class as r4's BLOCKER (a link the page hides in an attribute), reached through
markdown rather than a raw tag. I rate it MAJOR, not BLOCKER, on the brief's definition: the 195-file
corpus holds 0 images, 0 link titles and 0 angle-bracket destinations, and a wiki link inside image alt
text or a link title is not something a memory index is written with. The coordinator should note the
inconsistency: r4's `<span title="[[alpha]]">` was equally absent from the corpus and was rated BLOCKER.
Candidate fix, a hypothesis: make the text after `](` up to its `)` (and an image's `![...]` label) a
region, and re-run the fuzz with this alphabet.

### 2. MINOR — the docstring overstates what the angle-bracket destination and the measurement cover (measured; fix-induced: yes, the sentences are new in 1418c49a)

`scripts/check-memory-shape.py:102`: "An angle-bracket destination (`[b](<y.md>)`) is a tag region
too". It is one only when the character after `<` is an ASCII letter or `/` (`_TAG_START_RE`, `:195`).
`[b](<./t2 [[t1]]>)` and `[b](<#x [[t1]]>)` open no region, and the `[[t1]]` they put into the href is
SURE (finding 1). `:97` ("0 sure links the page hides") is true of a generator that writes no markdown
link titles, images or destinations; the bound should say so, as it already names its seeds.

### 3. MINOR — the oracle-blind hiding elements are more than `<script>` / `<style>` (inferred from the HTML standard and default stylesheet; not run in a browser; not fix-induced)

`scripts/check-memory-shape.py:105` names the content of `<script>` and `<style>` as hidden and not a
region. `html.parser` also reports as visible, and a browser does not show: the content of `<title>`
(in body, `display: none`), `<template>` (inert), `<noscript>` (with scripting on), an element with the
`hidden` attribute, and SVG `<desc>`. Each of `<title>[[t1]]</title>`, `<template>[[t1]]</template>`,
`<div hidden>[[t1]]</div>`, `<noscript>[[t1]]</noscript>`, `<svg><desc>[[t1]]</desc></svg>` is SURE at
the head and "visible" in the oracle. The list should say "for example" or name them; the oracle
cannot catch this class, so it is a bound, not a fold.

### 4. MINOR — the tag region refuses links that are shown, where markdown-it does not read a tag (measured; fix-induced: yes; LOUD direction)

`scripts/check-memory-shape.py:318` (`tag_end`). An unclosed `<letter` in a code span
(`` `<a` [[t1]] ``) makes every later link in the file UNCERTAIN to the end of the text, and
`<a/b="[[t1]]">`, `<a b=""[[t1]]>`, `<a =="[[t1]]">` are uncertain though markdown-it escapes each to
text and `[[t1]]` is shown. This is the docstring's stated price (`:100`), paid as CANNOT-READ only where
a verdict depends on it, and the corpus pays 0 today. Recorded so the price is named with an input: one
code span holding `` `<path` `` without its `>` would put every later link of that file behind it.

## The 11 new mutations die for the reason their names say

Each was applied to a scratch copy and every failing case listed (not only the `expect` one):

- 91 (region not added): the 19 cases above, all tag-region inputs. Reason correct.
- 92 (no quote opens a value), 93 (single quote opens none): the quoted-`>` and single-quote inputs go sure. Correct.
- 94 (a quote in a NAME opens a value): only the name-quote input and its unit case. Correct.
- 95 (a quote in an UNQUOTED value opens one): only `<div title=a"b>[[t1]]` going uncertain, and its unit case. Correct.
- 96 (no line break) and 97 (break at the line end): only the container input and the line-end unit case. Correct; 97 is the one that witnesses the "to the end of the TEXT" choice.
- 98 (`</` opens no region): only the closing-tag input. Correct.
- 99 (every tag to the end): only the four sure-beside-a-tag cases, the normalisation case and the unit case. Correct.
- 100 (first tag only) and 101 (`=` after a space): killed only by `uncertain_regions` / `tag_end` UNIT cases, with no end-to-end CANNOT-READ input (for example `<b>x</b> <span title="[[t1]]">`, or `<span title = "x>[[t1]]">`). Not ambient — the unit cases assert exactly these transitions — but the end-to-end witness is missing. Not a finding at this round.

The docstring's stated bound for the region (`:78-81`) matches `tag_end` and `uncertain_regions`
as written; finding 2 is about the two sentences that claim more than that bound.

## Loosening

The flagged id is the shipping-set edge pin (`scripts/check-shipping-sets.py:2247`). It is an exact
equality on the tree's own derived edge set. I re-derived both sides: the merge-base tree reads
347 / `f52dc45f48609f44`, the head 349 / `df1ef55a52b10da7`, gained exactly
`check-memory-shape.py -> fixture_git.py` and `check-selftest-counts.py -> check-memory-shape.py`,
lost none. Every set other than the tree's own, including any that loses an edge, still fails. I
answer it as not a loosening; Codex's r4 answer for the same id stands for the Codex half.

No rule in `check-memory-shape.py` was removed or weakened by the fold: it only adds regions, which
can only move a link from SURE to UNCERTAIN (toward CANNOT-READ, rc 1), never toward an all-clear.

None of the findings is a BLOCKER under the brief's definition, so all four are filed, not folded.

## Loosening answers
LOOSENING-CHECK 639d2b2f0db1: not a loosening

VERDICT: CONVERGED

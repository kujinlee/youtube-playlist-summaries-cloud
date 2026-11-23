Reviewed head: 0fb651733487159989eba73870f1f4863a08598b

# backlog #698, round 1, Claude half (adversarial)

Branch `backlog-698`, PR #620. Subject: `scripts/build-shipped-corpus.py --check` now matches group-D quote words
against markdown-it's rendered text (plus two add-only views) instead of a regex model of links. Acceptance test
(row 698 **Fails if**): any line whose RENDERED text holds a six-word group-D run passes `--check`.

No quote text is reproduced here (the corpus is private memory text). Probes were built programmatically from the
first six-word window of the real sources' rendered quotes; they are named by shape only.

## What was run

| Check | Result |
|---|---|
| `--self-test` in the worktree | 41/41, 10.1 s wall |
| real build, `--out <scratch>` | rc 0, 180 files, 6 D sources (51 quotes), 708 fragments, PASS |
| full `git clone` at 0fb65173 under scratch, only `node_modules/markdown-it` copied in (1.6 MB) | control 41/41 |
| all **34** manifest mutations applied one at a time in that clone, each self-test run | **34/34 killed, every one by the case its `expect` names**; every anchor unique |
| `check-plan-code.stage_tree(clone, dest)` then the self-test under `mutation_env(dest)` | the bundle reaches the staged tree (`docs` is a `HARNESS_TREE` root too, so the plant corpus case finds the real sources); 41/41 |
| 29 false-green probes over the real sources (below) | 10 MISS that a reader would see as the run (C1, C2, C3), 2 homoglyph misses (C5) |
| fake node binaries: invalid UTF-8 stdout; stderr noise + wrong-length JSON; SIGKILLed | rc 1 traceback (C4); rc 2; rc 2 |

Pins: 34 mutations (`expected_mutations.py`) and 41 cases (docstring) match what runs. Fixture-variation keys
match the delivered functions. Sweep re-price: this target becomes 8.0 × (34 + 2) = 288 s of a priced sweep total of
about 36,158 s (+0.75%); the shards are cut by cost over entries, so no single shard's 30-min budget is at risk. CI
`verify` runs `npm ci` (ci.yml:379) before the self-test step (ci.yml:927); `mutation-sweep` runs `npm ci`
(ci.yml:1449) before the harness. Over-refusal: the real build passes; the four self-test adjacent negatives pass.

Probes that HIT (correct): plain control, `&nbsp;` between words, `&#32;`, backslash escape, code span, setext
heading, wrap across source lines, list continuation, blockquote continuation, nested emphasis, text-as-table,
`<div>` HTML block around Markdown, a USED reference definition's title, image alt with a title, `<img>` without alt
between words.

The three views: `views()` returns a set and `check` tests `any(...)`, so each extra view can only add hits. The raw
view cannot mask a renderer failure: a renderer that returns nothing is CANNOT RUN (quote side empty ⇒ `unread`,
and the per-input shape check), and mutation 32/33 are killed.

## Findings

### C1 — MAJOR — an invisible format character inside one word hides the run from all three views
- `fix_induced: false`
- **Input:** an output line holding a real six-word group-D window with a soft hyphen in the middle of its longest
  word, written either as the entity `&shy;` or as the literal U+00AD. Same with `&#8203;` (zero-width space),
  U+200D (zero-width joiner), `&#x2060;` (word joiner). 5 probes.
- **Observed:** all 5 pass `--check` (MISS). `norm` (`scripts/build-shipped-corpus.py:176-181`) maps every
  `[\W_]+` run to a space, and these Unicode `Cf` characters are `\W`, so the word becomes two words in the rendered
  view; the raw view reads the entity name (`shy`) as a word.
- **Expected:** FAIL — a CommonMark viewer (and an LLM reading the raw bytes) shows the word unbroken, so the
  rendered text holds the six-word run. This is row 698's own Fails-if. *What this cannot see* does not name it
  ("a word split ... differently" describes a paraphrase's wording, not an invisible character).
- **Fix:** in `norm`, delete format characters before splitting:
  `text = "".join(c for c in text if unicodedata.category(c) != "Cf")`. The rendered view has already decoded the
  entities, so this covers both spellings; add the five probes as a case, plus a disguise in `disguises()` so the
  plant corpus carries it.

### C2 — MAJOR — `_Visible.BLOCK` omits elements a browser lays out as blocks, so two words JOIN across them
- `fix_induced: false`
- **Input:** three words of a window, then `<center>` immediately followed by the other three, then `</center>`,
  no space at the tag. Same with `<legend>`. 2 probes.
- **Observed:** both pass (MISS). `BLOCK` (`:153-155`) does not list `center`, `legend`, `caption`, `menu`, `dir`,
  `hgroup`, `search`, `listing`, `xmp`, `optgroup`, `option`, so `handle_starttag` adds no break and the rendered
  view reads the two edge words as one; the raw view reads the tag name as a word between them.
- **Expected:** FAIL — the browser's default style for these elements is `display: block`, so the reader sees a
  line break, i.e. the six words. The docstring (`:23`) claims "a block tag or `<br>` separates words".
- **Fix:** an enumerated list will keep missing one, so add a fourth ADD-ONLY view in which EVERY tag boundary is a
  break (a second `_Visible` with every tag treated as block). The joined view stays, so `con<em>clu</em>sion`
  still hits; the split view adds `<center>`, `<legend>` and any future block element. Keep mutation 27's
  direction meaningful by asserting the joined view separately (it already has its own case).

### C3 — MINOR — the rendered view READS content a browser never displays, so it can break a run the reader sees
- `fix_induced: false`
- **Input:** three words, then ` <style>zz</style> `, then the other three. Same with `<script>`, `<template>`, and
  `<span hidden>zz</span>`. 4 probes.
- **Observed:** all 4 pass (MISS). `_Visible.handle_data` keeps the element's text, so `zz` sits between the words
  in the rendered view, and the raw view has the tag names too.
- **Expected:** FAIL — a browser shows the six words adjacent. *What this cannot see* names "CSS that hides or
  reorders text", which reads as stylesheet rules on visible elements; it does not name elements whose content is
  never rendered at all.
- **Fix:** in another add-only view, drop the data inside `script`, `style`, `template`, `noscript`-free
  `head`/`title`, and any element carrying `hidden`; or, at minimum, name these in *What this cannot see*.

### C4 — MINOR — a renderer that writes invalid UTF-8 exits 1 with a traceback, not CANNOT RUN
- `fix_induced: false`
- **Input:** `NODE` pointed at a script that drains stdin, writes `\xff\xfe{` and exits 0; `--check` on the real
  build.
- **Observed:** rc 1 and an uncaught `UnicodeDecodeError` from `subprocess.run(..., text=True)` (`:125-128`);
  `except (OSError, subprocess.TimeoutExpired)` does not catch it. rc 1 is this script's "a check FAILED", so a
  harness sees a red result naming no hit, not "treat as NOT RUN". Fail-closed, but the wrong class. Also,
  `text=True` decodes with the locale encoding, so under a non-UTF-8 locale the node output is silently
  mis-decoded.
- **Expected:** rc 2, `CANNOT RUN: the CommonMark renderer ...`.
- **Fix:** pass `encoding="utf-8"` and add `UnicodeDecodeError` (or `ValueError`) to the caught tuple; add the fake
  binary as a fifth arm of the "renderer that cannot run" case.

### C5 — NIT — homoglyph substitution is an unstated bound
- `fix_induced: false`
- **Input:** the window with one Latin `a` replaced by Cyrillic U+0430.
- **Observed:** passes (MISS); expected for any word matcher.
- **Expected:** not a fix, but *What this cannot see* should name it (a word spelled with look-alike letters from
  another script), so the bound is stated where a reader of the guard looks.
- **Fix:** one clause in the docstring; optionally NFKC plus a confusables fold, which is more than this needs.

Not findings: markdown-it is `^14.2.0` in `package.json` with 14.2.0 installed; a future minor could change layout
but the self-test's plant corpus would catch a behavioural drift. The corpus's real viewers (GitHub's GFM, Obsidian,
an LLM reading raw bytes) differ from the commonmark preset; the docstring names Obsidian aliases and GFM tables, and
the raw view covers a raw-bytes reader except for C1.

VERDICT: NOT CONVERGED

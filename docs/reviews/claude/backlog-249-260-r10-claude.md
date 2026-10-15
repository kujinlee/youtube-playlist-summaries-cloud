# Round 10 — Claude adversarial half · PR #371 `backlog-249-260-fixes`

**Subject:** `git diff 0792dcab..b190b713` · HEAD `b190b713` · the swap `d8c02e22`, this fold `b190b713`.
**Interpreter:** `scratchpad/venv312/bin/python` (3.12.9, `markdown-it-py` 4.2.0, `cmarkgfm`). A bare
`python3.12` raises `ParserUnavailable` by design; nothing below is a CANNOT RUN for that reason.
**Mandate:** refute. The round-10 Codex half found four Highs here; everything it already recorded
(the two cmark divergences, the shared table-cell line map, the `splitlines` ruler, the `main()`
refusal, the moving corpus, the stdlib-only sentence in `check-merge-ready.py`) is treated as known
and is **not** re-reported.

**Direction is the governing axis.** LENIENT = the mask whitens a real block boundary, so a stale
figure is silently reported as history. NOISY = a real span is declined, a dismissible warning.
Every finding below is classified.

---

## Blocking

None.

---

## High

### H1 — A THIRD cmark divergence class, and the first that needs no unusual container: **a GFM table whose header row contains no `|`**. LENIENT.

`scripts/check-withdrawal.py:643-657` states the bound as two constructed shapes plus the shared
table-cell map, and says the three cases exist "so this bound cannot quietly become folklore".
It is incomplete. There is a fourth, and its cause is one `if` in the parser:

```
markdown_it/rules_block/table.py:129-131
    lineText = getLine(state, startLine).strip()
    if "|" not in lineText:
        return False
```

**markdown-it requires a `|` in the header row. cmark-gfm does not** — a one-column table's header
is one cell, and a pipe-free paragraph line supplies it. So the preceding prose line *becomes the
table header* in cmark-gfm (which is what GitHub runs) while markdown-it keeps one paragraph.
Measured, all five LENIENT, all against `cmarkgfm` directly:

| document | guard | cmark-gfm |
|---|---|---|
| ``the count was `wrong:\n| --- |\nholds 1,414 anchors today` `` | span forms | `<table>` — split |
| ``the count was `wrong:\n|-|\nholds 1,414 anchors today` `` | span forms | `<table>` — split |
| ``the count was `wrong:\n| :-: |\nholds 1,414 anchors today` `` | span forms | `<table>` — split |
| ``the count was `wrong:\n  |---|\nholds 1,414 anchors today` `` | span forms | `<table>` — split |
| ``> the count was `wrong:\n> |-|\n> holds 1,414 anchors today` `` | span forms | `<table>` in `<blockquote>` |
| ``- the count was `wrong:\n  |-|\n  holds 1,414 anchors today` `` | span forms | `<table>` in `<li>` |

Two negative controls fix the boundary of the class exactly: a **two-column** delimiter row after a
pipe-free header AGREES (cmark needs header cells == delimiter cells, and a pipe-free header is one
cell), and a one-column delimiter row after a header that **does** contain a pipe AGREES.

**Why this is worth more than its two recorded siblings.** Both of those need an unusual container —
a lazy continuation line, or indented code after a table. This one fires at **top level with ordinary
indentation**, and inside a quote, and inside a list. `|---|` is one of the most common tokens in this
repo's documents. The only thing keeping it harmless today is that every table header here happens to
contain a pipe, and that is a property of the corpus, not of the code.

**Corpus instances: 0**, in both trees — same standing as the recorded two, and derived the same way:
over the pinned `git archive 0792dcab` population (1,806 documents) and over `b190b713` (1,807),
counting lines that are a one-column delimiter row whose predecessor is a non-blank pipe-free line:
**0 and 0**. (A looser scan that allowed multi-column delimiter rows found 1 hit,
`plan-1f-a-codex.md:1214`, whose delimiter is `|---|---|---|` against a one-cell header — cmark forms
no table there, so it is not an instance.)

**⚠ This pre-dates the swap and survives it**, exactly like Codex H4: the deleted predicate gated the
table lookahead on `elif "|" in rest …`, so the hand-rolled code required a pipe in the header too.
It is a *gap in the stated bound*, not a regression — but the docstring claims the bound is stated,
and it is the claim that is wrong.

**Fix:** a fourth case beside the three at `:1461-1477`, pinning current behaviour and naming itself
the day cmark's block offsets become reachable. The docstring's two-item list becomes three.

---

### H2 — The r10 Codex M1 fold swapped one wrong ruler for another, the new one fails **LENIENT**, and the comment justifying it is false.

`scripts/check-withdrawal.py:606-615`:

```
    # ⛔ r10 Codex M1 — `splitlines()` IS THE WRONG RULER HERE. It breaks on VT, FF, NEL, U+2028
    # and U+2029 as well as `\n`; markdown-it counts only `\n`, so any of those five shifted every
    # later line number …
    for line in text.split("\n"):
```

**"markdown-it counts only `\n`" is false.** `markdown_it/rules_core/normalize.py`:

```
NEWLINES_RE = re.compile(r"\r\n?|\n")
```

A **lone `\r`** is a line break to the parser and is not one to `split("\n")`. So the line counts
diverge the other way, the token map's indices run ahead of `offs`, and every span comes back
pointing at text further down the document than the block it describes.

Measured directly — `len(offs)` must equal the parser's line count + 1:

| text | `offs` entries | parser lines | |
|---|---|---|---|
| `a\nb`, `a\r\nb`, `a\nb\n`, `""`, `a\vb`, `a\fb`, `a b`, `a\x85b`, `a\0b` | match | match | ok |
| `a\rb` | **2** | **2** (needs 3) | ⛔ mismatch |

**Direction, A/B against cmark-gfm over 12,000 generated documents per corpus, with an LF control so
the pre-existing non-ruler divergence is subtracted rather than counted:**

| corpus | ruler | LENIENT | NOISY |
|---|---|---|---|
| lone `\r` | **shipped `split("\n")`** | **2,499** | 1,401 |
| lone `\r` | pre-fold `splitlines(keepends=True)` | 507 | 0 |
| lone `\r` | *control: same docs, separator → LF* | 507 | 0 |
| VT/FF/NEL/U+2028/U+2029 | **shipped `split("\n")`** | 505 | 0 |
| VT/FF/NEL/U+2028/U+2029 | pre-fold `splitlines(keepends=True)` | 0 | 1,401 |
| VT/FF/NEL/U+2028/U+2029 | *control: same docs, separator → LF* | 505 | 0 |

⛔ **I ran that control because my first reading of the uncontrolled numbers was wrong, and it
refuted it.** Uncontrolled, the VT row reads as the fold *introducing* 505 lenient shapes. It does
not: 505 is the baseline, the fold lands exactly on it, and the pre-fold ruler read 0 lenient only
because its 1,401 noisy answers masked the baseline. **On the five characters M1 names, the fold is
correct and complete.** The finding is the sixth character: on lone `\r` the fold adds
**+1,992 LENIENT** over the baseline it should reproduce, where the ruler it replaced reproduced it
exactly.

A total that falls while lenient rises is not progress — that rule is this round's own, and the ruler
it was applied to is the one case where it was not applied.

**The repair is measured, not proposed.** Replacing `:611-615` with the parser's own separator:

```python
    offs = [0]
    for _m in re.finditer(r"\r\n?|\n", text):
        offs.append(_m.end())
    offs.append(len(text))
```

| corpus | shipped | with the repair |
|---|---|---|
| lone `\r` | 2,468 L / 1,328 N | **526 L / 0 N** (= baseline) |
| VT/FF/NEL/U+2028/U+2029 | 545 L / 0 N | **545 L / 0 N** (unchanged — M1 is not regressed) |
| plain LF | 482 L / 0 N | **482 L / 0 N** (unchanged) |
| `--self-test` | 175/175 | **175/175** |

⚠ **That the suite is green under both rulers is itself H3**: no case distinguishes them.

---

### H3 — The code this branch wrote has **zero** mutation coverage, and the branch's own guard says so in a warning nothing reads.

`EXPECTED_MUTATIONS["scripts/check-withdrawal.py"]` falls `56 → 30`
(`scripts/check-plan-code.py:700`), and the comment is right that the 26 are *retired with their
subject*. What it does not say is that **the replacement arrived with none**. Not one of the
surviving 30 anchors inside `inline_block_spans` or the new `paragraph_ends_between`; all 30 defend
`history_marker`, the backtick pairing, `backtick_escaped`, the mask memo — functions this branch did
not change. (A substring scan for `offs` matches five entries; all five are `hit_offset`,
`figure_offset_in_window`, `figure_offset_in_hit` — false matches, not coverage.)

**The repo already detects this and does not act on it.** `scripts/check-plan-code.py --diff-coverage 0792dcab`:

```
  scripts/check-withdrawal.py
      _memo_key_probe() changed, and no mutation anchor lands inside it
      inline_block_spans() changed, and no mutation anchor lands inside it
      paragraph_ends_between() changed, and no mutation anchor lands inside it
WARN — 3 function(s) this branch changed carry no mutation that reaches them … rc=0
```

**Measured rather than inferred.** Eight hand-built mutations of the new code, each applied to a
scratch copy, each run against the whole 175-case suite:

| mutation | result |
|---|---|
| **revert the r10 Codex M1 fold** (`split("\n")` → `splitlines(keepends=True)`) | ⛔ **SURVIVED** 175/175 |
| **`if s0 <= start < e0:` → `if start < e0:`** (the span START bound) | ⛔ **SURVIVED** 175/175 |
| `return end >= e0` → `return end > e0` | survived; **no witness found — I treat it as an equivalent mutant, not a hole** |
| drop `a < len(offs)` from the span filter | survived; **strictly redundant** (`b > a` always), equivalent by construction |
| remove `_BLOCK_SPANS.clear()` from `main()` | survived; equivalent for correctness (see *Checked and found SOUND*) |
| bypass the memo entirely (perf-only) | survived — **negative control: the instrument is not killing everything** |
| `tok.type == "inline"` → `"paragraph_open"` | ✅ killed, 174/175 |
| fallthrough `return True` → `return False` | ✅ killed, 173/175 |

The two survivors that matter have witnesses, so they are holes and not equivalences:

- M1-revert — ``the count was `an\x0bchors:\n1,414` today`` : shipped `'was '`, mutant `''`.
- start bound — ``` ```\n`a\n```\nthe count was `anchors:\n1,414` today ``` : shipped `'was '`, mutant `''`.

**Why this is High and not Medium.** Nine rounds of this file's history are lenient regressions that
a case caught only after a reviewer constructed the shape. The mechanism that was supposed to stop
the tenth is a manifest, and the manifest now points entirely at code this PR did not touch. H2 is
the first instance: a fold landed this round, in the expensive direction, and the suite could not
tell. `--diff-coverage` is warn-only by #56's measured verdict and that is defensible as a general
rule; it is not defensible as the only thing standing between this swap and an unseen lenient
regression.

**Fix:** manifest entries for at least the ruler (`split("\n")` → `splitlines`), the span start bound,
and the `tok.type == "inline"` selector — the first two have the witnesses above, ready to become
cases.

---

## Medium

### M1 — `--self-test` is **not** runnable without the parser, and the comment that exempts it says it is.

`scripts/check-withdrawal.py:1985-1997` exempts `--self-test` from the `_MD is None` refusal with:

> ⚠ The self-test is exempt above on purpose: its cases drive the pure functions and must still be
> runnable for someone diagnosing a broken install.

Measured, bare `python3.12`, no parser:

```
check-withdrawal.py --self-test        -> rc=1, uncaught ParserUnavailable traceback
                                          (check-withdrawal.py:1349 -> _marker_at -> mask_inline_code
                                           -> paragraph_ends_between -> inline_block_spans:597)
check-withdrawal.py --base origin/master -> rc=2, the CANNOT RUN sentence   ✅ as designed
```

Two things are wrong. The stated reason for the exemption is false — the cases are not pure, they
drive `mask_inline_code`, which needs the parser from case 1 of that family onward. And the path the
exemption creates reports a **traceback at rc=1**, where this repo's doctrine and this very file's
`ParserUnavailable` docstring say a cannot-run is **rc=2 with the words *treat this as NOT RUN***. A
reader diagnosing a broken install gets the one output shape the exception type was invented to avoid.

Direction: not lenient — it is loud. But it is a load-bearing comment asserting a measured-false
property, which is the failure mode a caveat headed *stated rather than hidden* exists to prevent.

**Fix:** either move the `_MD is None` refusal above the `--self-test` branch (rc=2 for both), or
delete the sentence and say the self-test needs the parser like everything else.

### M2 — `inline_block_spans` **silently drops** a span it cannot place, with no record that it did.

`scripts/check-withdrawal.py:620`:

```
            if a < len(offs) and b < len(offs):
                spans.append((offs[a], offs[b]))
```

`a < len(offs)` is dead (`b > a` for every token map). `b < len(offs)` is reachable only when the
parser counts more lines than `offs` does — i.e. **only** under H2's lone `\r`. When it fires, the
block simply vanishes from the answer, and the offsets of every surviving span are already wrong.
This is the mechanism that turns H2 from a loud failure into a quiet lenient one: the guard's
line ruler and the parser's disagree, and the only code that notices responds by discarding evidence.

"Cannot run is a failure, never a pass" is the house rule, and it applies at span granularity too.
If `b >= len(offs)` the guard has established that its ruler and the parser's disagree about this
document, which is a condition it cannot recover from — it should raise, not drop. With H2's repair
the branch becomes unreachable and the right form is an assertion.

### M3 — the "⛔ FIRST" comment in `mutation-sweep` is no longer true of what follows it.

`.github/workflows/ci.yml:703-706`: the new `Guard dependencies` step was inserted immediately above

```
      # ⛔ FIRST, as in `verify`. If the pin did not take effect, every mutation verdict below
      # is a measurement of an interpreter nobody declared — PR #315 is the instance …
```

The pin check is no longer first; a `pip install` now runs ahead of it, in both jobs. No measurement
is corrupted — a silently-failed `setup-python` would install into the ambient interpreter and the pin
check would still catch it on the next step — but the comment states an ordering the file no longer
has, and PR #315 is in the trail precisely because someone believed a comment about ordering.

---

## Low

### L1 — a third copy of the stdlib-only claim survived the fold.

r10 Codex L1 corrected `scripts/check-merge-ready.py:133`. The same claim lives in a tracked
document that was not touched — `docs/memory/arch-review-153-workflow-readers.md:26`:

> **NOT a real parse** — no guard imports a third-party package, PyYAML is absent, **no
> `requirements.txt`, no `pip install` in either workflow** …

All three clauses are now false. The roadmap's #153 row was amended in place and `requirements.txt`
carries the coupling note, so the *decision* is recorded honestly; this is the one live assertion of
the dead premise that the sweep missed. (The `docs/superpowers/plans/*` "stdlib only" lines are
tech-stack statements about their own slices and read as history; the merged review docs are
testimony and are not rewritten. This file is neither — it is a current note about the repo.)

### L2 — `.github/workflows/ci.yml` lost its trailing newline (`\ No newline at end of file` on the last hunk).

---

## Checked and found SOUND

- **Claim 5, re-derived not re-read.** `scratchpad/parser-swap/final_check.py`, baseline and corpus
  both pinned at `0792dcab`: known-positive control detects exactly 1 of 2 planted (as required),
  then **1,806 documents · 95,778 figures · 0 verdict differences** (77s). The figure reproduces.
- **Claim 6.** Scoped `--mutate` over a pruned **copy** of `HARNESS_TREE`'s six paths (the repo
  itself untouched): control green, **30 mutations, 30 killed, 30 attributed to the case each
  names**, re-control green, 0 survivors, 54s. Every entry still kills via its named case under
  exact attribution — #266's "silently no-op" shape is not present.
- **The new dependency survives `child_env`'s `$HOME` redirect.** The spawned suites in that run
  resolved `markdown_it` normally, so the package is not reached through `HOME` and the harness is
  not quietly measuring a `ParserUnavailable` for every mutation.
- **Claim 7 — the memo cannot go stale, only grow.** Both clear sites are paired
  (`:850-851`, `:2003-2004`); there is no `_MASKED_DOCS.clear()` without a `_BLOCK_SPANS.clear()`
  beside it. Removing the `main()` clear survives the suite, and correctly so: the memo is keyed by
  **value**, so a surviving entry can only be right. What the clear buys is the *size* bound the r6
  Claude H1 comment claims, and nothing more — which is what that comment says.
- **Claim 3, the parts I could reach.** `markdown_it` is imported by exactly one script in the tree
  (`check-withdrawal.py`); no other guard is parser-dependent, so `schema-gates.yml` having
  `setup-python` and no install is correct — none of its fifteen gates can reach it. In both jobs
  that run a parser-dependent step, the install precedes it (`ci.yml:82-83` before `:184`;
  `:703-704` before the sweep). `mutation-sweep-complete` has no checkout, no install, and runs no
  Python — correctly left alone.
- **`check-fixture-variation.py`'s entry for this file names no deleted function** and the full run
  is green: *918 parameters across 67 files, 117 ratcheted, 7 exempt*, rc=0. The 26-mutation fall did
  not orphan it.
- **The suites.** `check-withdrawal --self-test` 175/175 · `check-plan-code --self-test` 237/237 ·
  `check-merge-ready --self-test` 74/74 · `check-plan-code --binding` rc=0, *1537 anchors across
  1529 entries each resolve to exactly one site*.
- **The constructs the brief named, and no divergence found in any of them**: setext headings
  (`===`, `---`, indented), link reference definitions, footnote definitions, nested and tilde
  fences, info strings, malformed delimiter rows (`| -x- |`), ATX edge cases (7 hashes, no space,
  closing sequence), thematic breaks, task items, HTML block types 1–6 at top level and in
  containers, blank lines inside quotes, and CRLF. Bound: **~85,000 distinct constructed documents**
  across three generators (a 45 × 5 × 2 hand grid, 29,416 distinct fuzz documents, 55,308 distinct
  fuzz documents), each adjudicated against `cmarkgfm` directly. Every LENIENT result fell into
  exactly three families: the two Codex already recorded, and H1.
- **Oracle validity.** Before any zero above was believed, the oracle was run on the three recorded
  shapes and two must-agree shapes: **5/5**. It reproduces Codex H3a, H3b, agrees on an ordinary
  wrapped span, agrees that fenced single backticks no longer pair, and agrees that an ATX heading
  splits. A zero from it is a statement about the shapes, not about the instrument.

---

## The question the brief most wanted refuted: is deleting 217 lines a net improvement?

**I could not refute it, and here is the evidence either way rather than a verdict dressed as one.**

For: the swap closes the r5 L1 fence deviation, which is the only one of these classes with
*measured corpus presence* — **597 span-level disagreements with cmark across 121 files**. It closes
the open list-content-column class that nine rounds could not. It does both at **0 verdict
differences over 95,778 figures**, control-checked. And the nine-round trail itself is the argument:
every fix was right and every round found another shape.

Against: it opens three LENIENT classes (two recorded, H1 new) — but all three have **0 corpus
instances**, so on the documents that exist the trade is a 121-file class closed for a 0-file class
opened. That is not close.

**The real cost is not on that ledger, and it is H3.** The hand-rolled code was wrong often and
*defended*: 26 mutations, each naming the round that found its shape. The parser-backed code is right
far more often and defended by nothing. H2 is what that looks like in practice — a fold shipped this
round, in the expensive direction, through a 175-case suite that could not see it.

**What would refute the net-improvement claim:** a LENIENT divergence class with non-zero instances in
the tracked corpus. I looked for one across ~85,000 constructed documents and the full pinned corpus
and did not find it. That is the strongest statement the evidence supports — not that none exists.

---

## CANNOT RUN

**None.** Every instrument this review relied on executed and is replayable from
`scratchpad/r10-claude/`.

⚠ **Two bounds on what was run, stated rather than hidden:**

1. The mutation evidence in *Checked and found SOUND* is a **scoped** run — a copy of the six
   `HARNESS_TREE` paths with `EXPECTED_MUTATIONS` pruned to this one file **in the copy**. It is the
   30 entries for `check-withdrawal.py` under a real control, not the whole 1,529-entry sweep that CI
   runs. It says nothing about the other 71 scripts.
2. `check-merge-ready.py` itself was not run — only its 74-case self-test. Its PR-only gates need
   `gh` against the open PR, which is the coordinator's run, not a reviewer's.

---

## Instruments

All under `scratchpad/r10-claude/` (outside the repo; every mutation was applied to a copy):

| file | what it does |
|---|---|
| `oracle.py` | loads the shipped guard and renders with `cmarkgfm`; `<pre>` stripped, `<code>` text unescaped |
| `control.py` | the 5-case oracle validity control — **run first, 5/5** |
| `grid.py` | 45 middles × 5 containers × lazy/fenced-in hand grid |
| `fuzz.py`, `fuzz2.py` | 29,416 and 55,308 distinct documents, adjudicated against cmark |
| `min1.py`, `min2.py` | minimisation of each candidate family down to the `if` that causes it |
| `corpus_table.py`, `corpus2.py` | H1's instance count over the pinned `git archive` corpora |
| `cr.py`, `crfuzz.py`, `ruler_ab.py` | H2: the ruler mismatch, its direction, and the LF-controlled A/B |
| `fixcheck.py` | H2's proposed repair, measured on three corpora plus the suite |
| `mutate_new.py`, `witness.py` | H3: eight mutations against the suite, then a witness for each survivor |
| `mroot/` | the pruned `HARNESS_TREE` copy the scoped sweep ran against |

**Tree state:** `git status --short` shows exactly one new untracked file, this one; HEAD is
`b190b713`.

**Merging is the human gate and this half makes no recommendation about it.**

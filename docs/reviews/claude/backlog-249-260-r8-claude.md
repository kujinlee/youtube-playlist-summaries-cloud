# Round 8 — Claude adversarial half. PR #371, `backlog-249-260-fixes`

**Subject:** `git diff 3b49db97..d6967caa -- scripts/ docs/` — 6 files, **396 insertions / 63
deletions** (`git diff --stat`, observed). HEAD `d6967caa`, base `origin/master`. One commit:
round 8's Codex fold. Last reviewed by this half at `bbdb3204` (round 7).
**Mandate:** refute, not confirm.

**Tree state:** `git status --short` printed nothing at the reviewed HEAD and nothing after this
review. Every mutation below was applied to a COPY (`vers/*.py` extracted with `git show`, and a
`scripts/` copy under `scratchpad/r8-claude/mutcopy/`). The worktree was not modified.

**Interpreters:** `python3.12` (3.12.9) for everything repo-side; `/tmp/cmvenv/bin/python` (3.12.9,
`cmarkgfm` 4.2.0 + `markdown-it-py` 4.2.0) for the oracle. `python3` on this machine is 3.14 and was
not used.

**Oracle, stated so it can be attacked.** A code span cannot cross a block boundary, because
CommonMark parses inlines *per block*. So for `` <ctx>intro `a\n<MID>\nb` x ``, an inline-code node
exists **iff** no paragraph boundary falls between the backticks, and therefore
`parsers_say_paragraph_ends == not has_code_span`. Three answers are taken per shape: cmark-gfm,
markdown-it `commonmark`, markdown-it `gfm-like` (linkify disabled). A shape where the three do not
agree is excluded and is never a claim about the code.

⛔ **AND I FIXED A DEFECT IN THAT ORACLE BEFORE USING IT — it matters to Claim 2.** The version in
`scratchpad/r7-claude/oracle.py` strips cmark's fenced output with `re.sub(r"<pre>.*?</pre>", …)`.
cmark-gfm emits `<pre lang="ruby">` when a fence carries an **info string**, so the literal `<pre>`
never matched, the fenced `<code` survived the strip, and every info-string-fence shape was recorded
as *"parsers split"*. Observed, same document, both oracles:

    DOC: 'intro `a\n```ruby\nb` x'
     cmark: '<p>intro `a</p>\n<pre lang="ruby"><code>b` x\n</code></pre>\n'
     oracle (original):  (False, True, True)     -> recorded as "parsers split"
     oracle (`<pre\b[^>]*>`): all three agree the paragraph ENDS

On a 132-shape info-string-fence corpus: **original oracle `split=84`, fixed oracle `split=0`**
(`ok` 30 → 114). The fix changes nothing on the note's own 1,620 grid (`split=4` either way, all
four `<span>` shapes), so it does not disturb Claims 1 and 3; it does refute one sentence of the
new fence comment. Everything below uses the fixed strip.

---

## Blocking

### B1 — The measurement note's NOISE COLUMN and its `3b49db97` BASELINE ROW are not reproducible, and the paragraph at `:396` contradicts the table at `:383-387` by a factor of two

`scripts/check-withdrawal.py:380-397`. The note presents this table, introduced by *"Measured now,
cmark-gfm and markdown-it in BOTH dialects agreeing, … = 1,620 shapes"*:

    #   version                                    LENIENT (hides a figure)   noisy   total
    #   `3b49db97` (r7 as shipped)                            42               186      228
    #   r8, quote depth tracked per line                      42               192      234
    #   r8, depth taken from the PARAGRAPH's first line       16               108      124
    #   r8 + the fence clause in BLANK_OR_BLOCK                4               108      112
    #   r8 + the fence clause in BOTH predicates               0               108      108

**Three of those rows reproduce exactly and two do not.** Re-running the generator the brief names
(`scratchpad/r7-claude/corpus_r8.py`, which imports `oracle.py`) against versions extracted with
`git show`, observed:

    r7 / note's own grid: 1620 shapes · LENIENT=214 · noisy=108 · ok=1294 · split=4
    r8 / note's own grid: 1620 shapes · noisy=108 · ok=1508 · split=4
    r8_nofence / note's grid: 1620 shapes · LENIENT=16 · noisy=108 · ok=1492 · split=4
    r8_noABIfence / note's grid: 1620 shapes · LENIENT=4 · noisy=108 · ok=1504 · split=4

(`r8_nofence` = the shipped file with `r"|(?:`{3,}|~{3,})"` replaced by `r""` **and** `` ~` ``
removed from `ANY_BLOCK_ISH`'s class; `r8_noABIfence` = only the latter. Rows 3, 4 and 5 therefore
land on 16/108/124, 4/108/112 and 0/108/108 — to the unit, which is what attributes the table to
this generator.)

**Row 1 is wrong.** The shipped note says `42 / 186 / 228` for `3b49db97`; the same corpus, the same
instrument, measures **`214 / 108 / 322`**. ⚠ *Inference, labelled as such:* `42` is the figure the
docstring at `:498` attributes to a **1,980-shape** corpus (*"all 42 remaining lenient shapes on a
1,980-shape corpus"*), so row 1 looks like a figure carried in from a different corpus — which is
the one error the paragraph at `:391` says the note exists to prevent.

**And the whole NOISE column is measured at the wrong newline.** The generator decides the verdict
with

    def says_ends(doc):
        return mod.mask_inline_code(doc)[doc.index("\n")] == doc[doc.index("\n")]

while its own `LEAD = ["intro", "> intro\nlazy", "> intro"]` puts a newline **before** the span for
one third of the grid. For those 540 shapes `doc.index("\n")` is the newline after `> intro`, which
lies outside the candidate span, is never masked, and so always reports *"the paragraph ends
here"* regardless of what the predicate does. Scoring the same grid at the span's own newline
(`doc.index("\n", doc.index("`a"))`), observed:

    r7             first \n (as the generator does)   LENIENT=214 · noisy=108 · ok=1294 · split=4
    r7             the SPAN's \n (correct)            LENIENT=228 · noisy=88  · ok=1300 · split=4
    r8             first \n (as the generator does)   noisy=108 · ok=1508 · split=4
    r8             the SPAN's \n (correct)            noisy=34  · ok=1582 · split=4
    r8_nofence     first \n (as the generator does)   LENIENT=16 · noisy=108 · ok=1492 · split=4
    r8_nofence     the SPAN's \n (correct)            LENIENT=28 · noisy=34  · ok=1554 · split=4
    r8_noABIfence  first \n (as the generator does)   LENIENT=4  · noisy=108 · ok=1504 · split=4
    r8_noABIfence  the SPAN's \n (correct)            LENIENT=8  · noisy=34  · ok=1574 · split=4

Localised by lead, the phantom noise is entirely in the lazy third:

    ('> intro',      'buggy')   {'ok': 522, 'noisy': 16}
    ('> intro',      'correct') {'ok': 522, 'noisy': 16}
    ('> intro\nlazy','buggy')   {'ok': 448, 'noisy': 90}
    ('> intro\nlazy','correct') {'ok': 522, 'noisy': 16}
    ('intro',        'buggy')   {'ok': 538, 'noisy': 2}
    ('intro',        'correct') {'ok': 538, 'noisy': 2}

So **`108` is really `34`** (74 of the 108 are shapes where nothing about the span was measured),
and the two lenient rows the fence clauses are justified by are understated: `16` is really `28`,
`4` is really `8`. ⤳ The headline `0 lenient` survives both the index defect and the oracle defect,
and that is the one figure in the note I could not break on its own corpus.

**Then the paragraph at `:389-397` disagrees with the table above it three separate ways:**

    # ⚠ AND NOTE WHAT THE LAST TWO ROWS DO NOT DO: the noise count does not move. 108 before the fence
    # clauses and 108 after, so this one was free … The 216 figure in the previous version of this note
    # was a different corpus; comparing across the two would be the error this whole note exists to
    # prevent.
    #
    # … ⚠ THE 216 REMAINING ARE ALL NOISY — the mask declines a span a parser keeps, costing a
    # dismissible warning — and the count ROSE from 186, which is the deliberate trade

1. **`216 REMAINING` contradicts the table's `108` ten lines above**, and contradicts the measured
   value (`34`). Neither 216 nor any multiple of it appears in any run I made.
2. **`the previous version of this note` did not contain 216.** `grep -n 216 vers/r7.py` prints
   nothing; the figure the r7 version carried was `132` (*"⚠ THE 132 THAT REMAIN ARE ALL NOISY"*,
   deleted by this commit), and `grep -n 132 vers/r8.py` now prints nothing. The sentence disowning
   216 as "a different corpus" is itself about a figure that never existed.
3. **`ROSE from 186` is wrong in direction as well as value.** On the generator's own index the
   count is flat (108 → 108); at the correct index it **FELL**, 88 → 34. There is no measured sense
   in which noise rose, so the "deliberate trade" the sentence closes on did not happen on this
   branch.

**Direction and why this is the Blocking.** No code behaviour is at stake — this is prose. But the
reader this note is written for cannot tell rows 1 and the noise column from rows 3-5, which *are*
exact; `docs/backlog.md` row 267 has already copied the wrong figure forward in the same commit
(*"Measured after both clauses: **0 lenient / 108 noisy of 1,620** … (108 before, 108 after)"*); and
the note's own stated purpose is that a figure must be re-derived rather than repeated. The cheapest
honest repair is to delete row 1 and the `216`/`186` paragraph, restate the noise column as **34**
at a corrected index, and fix `says_ends` in whatever generator #268 commits — the figures are
otherwise sound and the direction argument does not depend on them.

---

## High

### H1 — "0 lenient" breaks one step outside the corpus, for the FOURTH time, on a class the grid cannot contain: a paragraph inside a LIST ITEM whose content column is ≥ 4

`scripts/check-withdrawal.py:417` (`BLANK_OR_BLOCK`) and `:448` (`ANY_BLOCK_ISH`). Both cap the
indent at `[ \t]{0,3}`:

    BLANK_OR_BLOCK = re.compile(
        r"[ \t\r]*$"                                # blank
        r"|[ \t]{0,3}(?:[-*+][ \t]+\S"              # a NON-EMPTY bullet
    ANY_BLOCK_ISH = re.compile(r"[ \t\r]*$|[ \t]{0,3}(?:[-*+=_>#<~`]|\d+[.)])")

Three spaces is the right cap **at top level**, where four spaces is indented code. Inside a list
item it is not: the block-start column is the item's *content* column, which is 4 for `- - `, 5 for
`- 1. `, 6 for `- - - `. Every block start at that column is invisible to both predicates, the mask
whitens the newline, and the span absorbs the figure. The note's corpus has a `PREFIX` of quote
spellings and no list container at all, so it cannot see the class.

**Witness, verified against all three oracles and cmark's HTML directly:**

    DOC: '  - intro `a\n    - x\n    b` x'
     HTML: <ul>|<li>intro `a|<ul>|<li>x|b` x</li>|</ul>|</li>|</ul>|
     oracle: (True, True, True)  mask: '  - intro `axxxxx-xxxxxxxb` x'

    DOC: '- - - intro `a\n      # h\n      b` x'
     HTML: <ul>|<li>|<ul>|<li>|<ul>|<li>intro `a|<h1>h</h1>|b` x</li>|</ul>|</li>|</ul>|</li>|</ul>|
     oracle: (True, True, True)  mask: '- - - intro `axxxxxxx#xhxxxxxxxb` x'

All three parsers put a real block boundary between the backticks; the mask's `x`-run shows the
newline whitened, so the span is accepted and a figure inside it is reported as history.
**Direction: LENIENT — the expensive one.**

**Measured, a clean list corpus (14 middles × 7 containers × {LF, CRLF}; the pad is the container's
real content column):**

    list-container corpus: {'ok': 96, 'LENIENT': 100}
    lenient per container (opener, content column):
        20  ('- - ', 4)
        20  ('- - - ', 6)
        20  ('  - ', 4)
        20  ('- 1. ', 5)
        20  ('1. 1. ', 6)

Content columns 2 (`- `) and 3 (`1. `) contribute **zero** — the rule is exactly *content column
≥ 4*. Pre-existing rather than introduced: the same corpus scores `LENIENT=56` at `3b49db97` and
`LENIENT=40` at `d6967caa` on the 168-shape variant, so this fold improved the class without
closing it.

**And the prose/quote space is genuinely clean, which is worth stating beside the failure.** A
randomised corpus of 1-3 middle lines, random quote prefixes per line, tabs included, seed
`20261008`, restricted to top-level and quote contexts:

    6757 distinct random shapes · noisy=343 · ok=6385 · split=29

Zero lenient. With list containers added back, the same generator gives `LENIENT=2126` of 7692, and
every grouped middle line in the top-30 carries ≥ 4 leading spaces — one class, not a scatter.

**LIVE IMPACT TODAY: ZERO, measured, not assumed.** Over all 1,803 tracked `*.md` files, masking
each document with the shipped `mask_inline_code` and asking which masked newlines are followed by
an indent-≥4 block marker:

    1803 tracked .md · 9833 newlines masked inside a span · 1 of them followed by an indent>=4 block marker
       ('docs/reviews/claude/goal-page-mutations-r4-claude.md', 143, '        # want {want!r}`, and it parses because `parse_fail_names` tru')

and that one hit is inside a ``` fence (lines 140-144 of that file), i.e. the already-documented
fence-deferral bound at `mask_inline_code`'s third bullet, not this class. The shape itself is
populated — 604 lines across 82 tracked files match `^ {4,7}([-*+] |[0-9]+[.)] |#{1,6} |> |...)` —
so this is latent, not hypothetical.

### H2 — FOUR statements this commit wrote (or moved) can each be changed so the predicate answers DIFFERENTLY on a two-parser-verified shape, and the 150-case suite stays 150/150. One of them is the lenient direction

Applied to a copy, each run as `python3.12 scripts/check-withdrawal.py --self-test` from a copied
`scripts/` tree. Observed:

    SURVIVED  reds= 0  walk-back takes the LAST line's depth, not the MAX   [150/150 passed]
    SURVIVED  reds= 0  walk-back never stops at a block start   [150/150 passed]
    SURVIVED  reds= 0  quote_depth stops consuming the space after `>`   [150/150 passed]
    killed    reds= 1  the table lookahead stops stripping markers   [149/150 passed]
    SURVIVED  reds= 0  the d<depth branch tests the STRIPPED remainder   [150/150 passed]
    SURVIVED  reds= 0  the early return on no newline in range goes   [150/150 passed]

A surviving mutation is only a finding if it is behaviour-changing, so each was scored against the
oracle and given a minimal tab-free witness:

| mutation | site | parsers say ends | shipped | mutant | direction of the mutant |
|---|---|---|---|---|---|
| `if i < len(line) and line[i] in " \t":` → `if False:` | `:468` | `(True, True, True)` | `True` | `False` | **LENIENT** |
| `if BLANK_OR_BLOCK.match(prest):` → `if False:` | `:506` | `(False, False, False)` | `True` | `False` | lenient in aggregate |
| `if ANY_BLOCK_ISH.match(nxt):` → `…match(rest)` | `:521` | `(False, False, False)` | `True` | `False` | lenient in aggregate |
| `depth = max(depth, pd)` → `depth = pd` | `:508` | — | — | — | differs only on multi-line leads |

Witnesses, verbatim from the run:

    C  quote_depth stops eating the space after `>`
        doc      '> intro `a\n>    > q\nb` x'
        parsers  (cmark, mdit-cm, mdit-gfm) paragraph ends = (True, True, True)
        shipped says ends=True   mutant says ends=False
    B  walk-back never breaks at a block start
        doc      '> - item\nintro `a\n> q\nb` x'
        parsers  ... = (False, False, False)
        shipped says ends=True   mutant says ends=False
    D  d<depth branch tests `rest` instead of `nxt`
        doc      '> > intro `a\n> q\nb` x'
        parsers  ... = (False, False, False)
        shipped says ends=True   mutant says ends=False

**The one that matters is C.** `quote_depth`'s one-space consumption is the mechanism r8 Codex H1
was *about* — `> > ` is depth two — and nothing in the 150 cases pins it. Deleting it leaves the
suite fully green while the predicate goes lenient on 208 shapes of a 4,000-shape fuzz corpus
(`BASELINE … fuzz[LENIENT=0 noisy=179]` vs `C … fuzz[LENIENT=208 noisy=173]`). The manifest's
`⛔ r8 Codex H1` entry mutates a *different* statement in the same function (*"stops after the
FIRST marker and takes the remainder from before it"*), so the function has a named defence for one
of its two statements and none for the other. ⚠ The reason the existing fence/quote cases do not
catch C is that `QUOTE_MARKER = re.compile(r"[ \t]{0,3}>")` already tolerates up to three leading
spaces, so `> > ` still reads as depth two without the explicit consumption — the two clauses
OVERLAP on every spelling the cases use, and only `>    > ` (four spaces, which no case contains)
separates them. That is the r7 `---\r` overlap shape the brief warns about, in new code.

B and D are behaviour-changing in both directions (on a harsher 6,000-shape corpus with multi-line
leads: baseline `LENIENT=114 noisy=851`, B `193/865`, D `181/506`), so they are coverage gaps rather
than defects — I am **not** recommending either change; see L3.

**Direction:** the gap itself is in the lenient direction for C. A case for `>    > q` and a case
whose paragraph's first line is a block start inside a quote would close C and B.

---

## Medium

### M1 — `EXPECTED_MUTATIONS`'s provenance comment says `+2` where the manifest grew by **5**

`scripts/check-plan-code.py:700-702`, added by this commit:

    "scripts/check-withdrawal.py": 44,   # ⟳ r8 Codex H1-H3: +2 — spaced nesting, and the
                                         # paragraph-start depth that closed the last 42.
                                         # ⟳ r7 Claude M1: +1 — the GFM table lookahead.

The count `44` is right (`--binding`: *"1551 anchor(s) across 1543 entries"*; the manifest holds
`entries: 44`; `attribution: 44 entr(ies) applied, 0 problem(s)`), and `39` was the pre-r8 value, so
the trail reads 39 + 2 = 41 ≠ 44. Diffed by name, the commit adds **five** entries and removes none:

    ADDED names:
      + ⛔ r8 Codex H1 — `quote_depth` stops after the FIRST marker …
      + ⛔ r8 Codex H3 — the open paragraph's depth is RE-DERIVED from each line …
      + ⛔ r8 — the paragraph's depth stops being taken from its FIRST line …
      + ⛔ r8 own-corpus — the FENCE clause leaves `BLANK_OR_BLOCK` …
      + ⛔ r8 own-corpus — the fence characters leave `ANY_BLOCK_ISH` …
    REMOVED names: (none)

Two of the five (the fence pair) and one of the three depth entries are unaccounted for in the
comment. This is the file whose own rule is *identity, not cardinality*; the number passes and the
sentence a future reader audits it against does not. **Direction:** documentation only — no gate
reads the comment.

### M2 — backlog #268's statement of what `check-ratchet-contract.py` would require is wrong in BOTH directions

The row says committing the generator *"lands it under `check-ratchet-contract.py`, which will
require a `--self-test`, no fail-open handler, and either a caller or a written `NO-CALLER:`
reason."* Read against the script:

* **R1-R3 are scoped by FILENAME.** `scripts/check-ratchet-contract.py:116`:
  `GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")`, and `discover_guards` is
  `sorted(p for p in script_paths if GUARD_PATH_RE.fullmatch(p))`. `main`'s own comment records
  *"`discover_guards` still filters by GUARD_PATH_RE, so `evaluate()`'s R1-R3 loop sees exactly the
  same 34 files."* A generator committed as `scripts/gen-withdrawal-corpus.py` is therefore subject
  to **none** of R1, R2 or R3. The three requirements the row names apply only if the file is named
  `check-*`.
* **R4 is omitted, and R4 is the population a self-tested non-guard actually lands in.** The
  docstring lists four enforced rules, not three: *"R4 a mutation manifest, or `NO-MUTATIONS:`
  ENFORCED"*. `discover_self_tested_nonguards` is *"Scripts that prove themselves with a
  `--self-test` but are not NAMED `check-*`"*, and `widened_debt_drift` pins that set **by
  identity** (*"IDENTITY, NOT CARDINALITY … Paying one down FAILS until the constant is lowered in
  the SAME commit"*). So the cheapest honest route — give the generator a `--self-test` under a
  `gen-` name — buys exactly the obligation the row leaves out: a `scripts/mutations/<name>.json`,
  or a `NO-MUTATIONS:` sentence in its docstring, or a change to `WIDENED_MANIFEST_DEBT` in the same
  commit.

**Direction:** the row understates option ①'s cost and overstates part of it; a reader sizing the
work from this row sizes the wrong work. Everything else I checked in #268 holds — see SOUND.

### M3 — Claim 2's "the fence clauses cost NO noise" is false outside the grid, and the clause's stated rationale is an artifact of the oracle defect

`scripts/check-withdrawal.py:420-427`:

    r"|(?:`{3,}|~{3,})"                      # ⛔ A FENCE — three or more backticks OR
                                             # tildes … ⚠ A fence WITH an
                                             # INFO STRING splits the two parsers, so this
                                             # deliberately takes the NOISY side of a
                                             # question neither answer can be called wrong
                                             # on: it declines the span (r8, own corpus)

Two separate problems.

**(a) The "splits the two parsers" justification does not survive a correct oracle.** As set out in
the preamble, the split was `<pre lang="ruby">` escaping a `<pre>`-only strip. With
`<pre\b[^>]*>`, the 132-shape info-string corpus goes `split=84 → split=0`, and every one of those
shapes has all three parsers **agreeing** that the fence ends the paragraph. The clause takes the
correct side there, not "the noisy side of a question neither answer can be called wrong on" — the
question has an answer and the clause gets it right. The comment credits a measurement that was
instrument error.

**(b) There IS a genuine noise class, and it is exactly the shape the brief asked for.** A backtick
fence's info string may not contain a backtick, so a line opening with three backticks and
containing another is **not** a fence and the paragraph continues. Observed:

    FIXED oracle, 132 info-string fence shapes: noisy=18 · ok=114
       noisy middles: Counter({'```a`b': 4, '```a``b': 4, '> ```a`b': 4, '> > ```a`b': 4, '> ```a``b': 2})

    DOC: 'intro `a\n```a`b\nb` x'
     cmark: '<p>intro <code>a ```a</code>b\nb` x</p>\n'
     mdit-cm tokens: [('paragraph_open',''), ('inline','intro `a\n```a`b\nb` x'), ('paragraph_close','')]
     oracle: (False, False, False)
     predicate ends? True

All three parsers keep the span; the predicate declines it. **Direction: NOISY — the cheap one**, so
this is not an argument for changing the clause, and I would leave the regex alone. It is an
argument for deleting the "free" and "splits the parsers" sentences, because both are what a future
round would otherwise cite. ⚠ Claim 2's *number* does survive the index correction: noise is flat
with and without the fence clauses on the note's grid at either index (108/108, and 34/34
corrected) — it is the word "no noise" as a property of the clause that is wrong.

---

## Low

### L1 — #267's "the restated falsifier is no longer discriminating" was refuted by this round's own answer

`docs/backlog.md` row 267, new text: *"⚠ **AND THE RESTATED FALSIFIER IS NO LONGER DISCRIMINATING**
— 'a later round finds another shape' has been true every single time it has been asked, which is
the argument for option ① and not a reason to ask a ninth time."*

Two things are wrong with that as a finding rather than an argument. First, *"true every single time
it has been asked"* is n = 2 (r7's fold and r8's) — and the brief's own framing records that the
amendment the Codex half criticised for arguing beyond its evidence did the same thing. Second, and
decisive: the falsifier **fired again this round** (H1 above, a class the row's own corpus cannot
contain, with a three-oracle witness and a measured 100-of-196). A test that fires is
discriminating; what the row has measured is that the *code* keeps being wrong, which is the
opposite of a reason to retire the test. The option-① conclusion is well supported by the eight-round
history; the sentence used to reach it is not, and the row would be stronger with the sentence
deleted and H1 cited instead.

### L2 — the case set does not pin "a fence is a run of ONE character"

Both new negatives fire as advertised — that part of Claim 4 holds (see SOUND). But a third
over-fire direction survives:

    === OVER-FIRE F: one character class, so a MIXED run `` `~~ `` counts as a fence  rc=0  reds=0

i.e. `r"|(?:`{3,}|~{3,})"` → `r"|(?:[`~]{3,})"` leaves 150/150 green. The parsers are unambiguous
that a mixed run is not a fence:

    'the count was `wrong:\n`~~\nholds 1,414 an' oracle(ends)= (False, False, False) predicate ends= False
    'the count was `wrong:\n~``\nholds 1,414 an' oracle(ends)= (False, False, False) predicate ends= False

The mutant would answer `True` there, so it is **noisy**, not lenient — cheap, and the shipped regex
is correct. One negative (`` `~~ `` as a middle line) would close it.

### L3 — a shipped NOISE class in the `d < depth` branch, reported with its trade rather than as a fix

`scripts/check-withdrawal.py:521` matches `ANY_BLOCK_ISH` against the **raw** next line:

            d, rest = quote_depth(nxt)
            ...
            if d < depth:
                if ANY_BLOCK_ISH.match(nxt):
                    return True

When `0 < d < depth` the line still begins with `>`, which is in `ANY_BLOCK_ISH`'s class, so every
depth decrease inside a quote ends the paragraph. CommonMark lazily continues it:

    doc      '> > intro `a\n> q\nb` x'
    parsers  (cmark, mdit-cm, mdit-gfm) paragraph ends = (False, False, False)
    shipped says ends=True

**Direction: NOISY.** ⛔ And the obvious repair is **not** free, which is why this is a Low and not a
recommendation: matching `rest` instead of `nxt` moves a 6,000-shape multi-line corpus from
`LENIENT=114 noisy=851` to `LENIENT=181 noisy=506` — the total improves while the expensive
direction gets worse, which is this note's own named trap. Worth recording in the note as a known
noise source rather than silently carried.

---

## Checked and found SOUND

Each of these is named with what was executed, not with an impression.

* **Claim 1's headline `0 lenient` on its own corpus.** Reproduced exactly:
  `1620 shapes · noisy=108 · ok=1508 · parsers split=4`. It also survives the two instrument defects
  B1 and the preamble describe (0 lenient at the corrected index; 0 lenient with the corrected
  oracle), and it survives a 6,757-shape randomised prose/quote corpus with multi-line middles.
  The only break is H1's list containers, which the corpus does not reach.
* **Rows 3, 4 and 5 of the measurement table** reproduce to the unit (16/108/124, 4/108/112,
  0/108/108), which is what let me attribute the table to `corpus_r8.py` and localise B1 to row 1
  and the column.
* **Claim 3 — the three retargeted anchors mean what their names claim, and each dies via its named
  case.** `--binding`: *"binding OK — 1551 anchor(s) across 1543 entries each resolve to exactly one
  site"*. `attrib.py . check-withdrawal.py`: *"attribution: 44 entr(ies) applied, 0 problem(s)"*.
  Applied individually, the reds are the named cases:
  * `if d > depth:` → `if d > depth or d > 0:` — 1 red, the `⛔ r7: a `>` line CONTINUING a quote…`
    case. The narrowing is semantically exact, not opportunistic: `d > depth` already returns, and
    for `d < depth` with `d > 0` the raw `>` line matches `ANY_BLOCK_ISH` anyway, so the *only*
    behaviour the `or d > 0` adds is "a quote line at the paragraph's own depth ends it" — which is
    verbatim the name's *"a block-quote line always ends the paragraph again, so a quote
    CONTINUATION rejects a genuine span"*. The `if True:` form the brief flags would indeed have
    been broader than the name.
  * the lazy branch → `if False:` — 4 reds including its named `⛔ r7: LAZY CONTINUATION…` case.
  * the table lookahead → `elif False and nxt_end != -1:` — 2 reds including its named
    `⛔ r7M1: a table HEADER plus its DELIMITER row…` case.
* **Claim 4 — the six new cases are falsifiable, and the two negatives discriminate different
  things.** Severing the fence clause from `BLANK_OR_BLOCK` reds exactly the three
  `BLANK_OR_BLOCK`-governed positives (tilde, backtick, CRLF tilde); severing `` ~` `` from
  `ANY_BLOCK_ISH` reds exactly the lazy-line positive. Over-firing the run length to `{2,}` reds the
  `~~` negative and **not** the indent negative; widening `[ \t]{0,3}` to `[ \t]*`, or hoisting the
  fence alternative out of the indent group, reds the four-space negative and **not** the `~~` one.
  The one unpinned over-fire direction is L2.
* **The declared counts.** `--self-test` prints `150/150 passed`; `check-selftest-counts.py` rc=0,
  *"55 script(s) declare a count, every one verified by running it"*; `check-plan-code.py
  --self-test` 237/237 with the `sum(EXPECTED_MUTATIONS.values()) == 1543` case green; the manifest
  holds 44 entries and every `expect` is a list, not a bare string (the #266 trap).
* **The four-space-indented-fence exclusion is real.** `BLANK_OR_BLOCK`'s fence alternative sits
  *inside* the `[ \t]{0,3}(?: … )` group, so `    ~~~` cannot match by backtracking, and OVER-FIRE B
  and C both red the case that asserts it.
* **Repo gates at the reviewed HEAD** (all `python3.12`): `check-fixture-variation` rc=0 (918
  parameters, 67 files), `check-ratchet-contract` rc=0, `check-producer-enumeration` rc=0,
  `check-docs` rc=0, `check-anchors` rc=0, `check-selftest-counts` rc=0.
* **#268's other claims.** Neither `cmarkgfm` nor `markdown-it-py` appears in any CI workflow or
  Python requirement — `grep -rn "cmarkgfm\|markdown.it\|markdown_it" .github/workflows/
  requirements*.txt package.json` returns only `package.json:34 "markdown-it": "^14.2.0"` and its
  `@types`, which is the Node app's dependency and not a Python one, so *"they are NOT CI
  dependencies"* is accurate as written. The CANNOT-RUN framing is accurate too: nothing committed
  replays any figure in the note, which is why reproducing B1 required reaching into
  `scratchpad/r7-claude/`. ⤳ If the owner wants a cheaper option ①, the Node `markdown-it` already
  in `package.json` is worth pricing against a new Python dependency — noted, not filed.
* **The r8 Codex H1/H2/H3 fixes themselves.** Each of the five new depth cases goes red under the
  manifest entry that names it (see the retarget run), and the three-oracle fuzz over prose and
  quote contexts finds no surviving lenient shape in that space at all — so the diagnosis
  (*pairwise comparison, not carried state*) and the repair both hold. H2 of this review is about
  what the **suite** can see, not about these fixes being wrong.

---

## CANNOT RUN

**Treat every item here as NOT RUN, which is a failure and not a pass.**

1. **Table row 2, `r8, quote depth tracked per line → 42 / 192 / 234`, was NOT reproduced.** It
   describes an intermediate patch that exists in no commit and in no file in the tree, so there is
   nothing to extract with `git show` and no way to rebuild it without guessing at the code. Rows 1,
   3, 4 and 5 were measured; row 2's three figures are unverified in either direction. ⚠ This is
   backlog #268's subject reappearing inside this review: the reason the row cannot be checked is
   precisely that the generator and the intermediate versions live outside the repo.
2. **The full `python3.12 scripts/check-plan-code.py --mutate .` sweep was not run.** The brief asked
   for `--binding` plus `attrib.py` scoped to this file, and both ran clean; the repo's own note
   records a scoped sweep costing minutes and the full one costing ~20 minutes of CI, and #266
   records a previous round's full-repo attribution attempt stopping at 35 minutes of CPU without
   finishing. So "every entry in the repo is attributable at `d6967caa`" is **not measured here** —
   only the 44 entries for `check-withdrawal.py`.
3. **`check-review-rounds.py` exits 1 at the reviewed HEAD**, printing
   `REVIEW GAP: codex — usage limit; Claude ran in its place per docs/plugins.md`. I did not
   investigate which round it refers to, because this half's own file did not exist when the gate
   ran; it must be re-run after this file is committed, and a non-zero result then is a real finding
   and not an artifact of my timing.
4. **No candidate fix for H1 was implemented, so "closing it changes no live verdict" is NOT
   established.** What *is* measured is that the class has zero instances in the 1,803 tracked
   markdown files today (the one indent-≥4 hit is inside a fence). Whether a fix that raises the
   indent cap inside a list container would change any document's verdict — the measurement that
   would decide whether this is a fold or a backlog row — was not run.
5. **The `\t`-prefixed container family in my first mixed corpus is an ORACLE ARTIFACT and was
   excluded, not measured.** `'\t- intro `a\n    plain\n    b` x'` renders as
   `<pre><code>- intro `a|plain|b` x|</code></pre>` — the whole document is an indented code block,
   so "no inline code" means "no paragraph at all" rather than "a boundary", and the oracle's
   construction does not apply. Eight shapes were discarded on that basis; whether the mask does the
   right thing *inside* indented code is a separate question I did not measure, and the existing
   fence-deferral bound already says the mask reaches into code blocks.
6. **cmark's answers were taken through HTML**, not through its AST. The strip is now
   `<pre\b[^>]*>.*?</pre>`, which I validated on the exact shapes that defeated the old one, but a
   fenced construct cmark renders without a `<pre>` wrapper would still be mis-read. markdown-it's
   answers come from its token stream and agreed with cmark on every shape reported above, which is
   the only cross-check I have for it.

---

## Instruments

Under `scratchpad/r8-claude/` (not in the repo, and that is #268's point):
`oracle.py` (copied from `r7-claude/`), `oracle2.py` (the `<pre\b[^>]*>` fix), `harness.py`,
`harness2.py` (scores at the span's own newline), `repro.py` / `repro_rows.py` / `repro_rows2.py` /
`repro_fixed.py` / `repro_fixedidx.py` / `leadsplit.py` (B1), `c_list*.py` / `c_mixed*.py` /
`c_wide.py` / `fuzz.py` / `fuzz_top.py` (H1), `overfire2.py` / `overfire3.py` / `retarget.py` /
`extra_muts.py` / `survivors*.py` / `minwit.py` (H2, M3, L2, Claims 3-4),
`realcorpus.py` / `realcorpus2.py` (live impact). `vers/r7.py` and `vers/r8.py` are
`git show 3b49db97:…` and `git show d6967caa:…`; mutants were written to `vers/_*.py` and to
`mutcopy/scripts/`, never into the worktree.

# Round 7 — Claude adversarial half. PR #371, `backlog-249-260-fixes`

**Subject:** `git diff e70aa551..bbdb3204 -- scripts/` — 3 files, **326 insertions / 20 deletions**
(verified: `git diff --shortstat`). HEAD `bbdb3204`, base `origin/master` `74a44551`.
**Mandate:** refute, not confirm.

**Oracle:** `/tmp/cmvenv/bin/python` (3.12.9) with `cmarkgfm` 'github_flavored' and `markdown-it-py`
4.2.0 in **two** configurations (`commonmark`, `gfm-like` with linkify disabled) — a three-way
oracle, not two. Everything else ran under `python3.12`.

**Oracle construction, stated so it can be attacked:** a code span cannot cross a block boundary,
because CommonMark parses inlines *per block*. So for `` intro `a\n<LINE>\nb` x ``, an inline-code
node exists **iff** no paragraph boundary falls between the backticks. Therefore
`parsers_say_paragraph_ends == not has_code_span`. Fenced/indented code blocks are stripped from
cmark's HTML before looking for `<code`, so a `<pre><code>` cannot be mistaken for a span.

**Instrument validated before use** (the repo's own "a 100% is usually an instrument" rule): seven
known shapes, both directions, all three oracles agreeing — blank line / `- b` / `1. b` / `# h` /
bare `---` end a paragraph; plain prose and `2. b` do not. The harness therefore distinguishes
both answers rather than only the one I was hunting.

⚠ **I broke my own instrument twice and both are recorded below rather than quietly fixed** — a
mutation harness that copied the subject out of `scripts/` (control RED, so every mutant read as
"nothing saw the kill"), and a `^\[FAIL\]` regex anchored at column 0 against lines the suite
prints indented. Both produced a uniform 100% before a control caught them. The second is also
**L2**, because the harness's own docstring describes the stricter rule its code does not apply.

---

## Blocking

### B1 — The docstring and backlog #267 assert "**zero** lenient disagreements" as a property of the predicate, when it is a property of the GRID; 19 shapes one step outside it are lenient, and the guard's exit code flips because of them

`scripts/check-withdrawal.py`, the comment block above `BLANK_OR_BLOCK`:

```
# The shipped version has
# **zero** lenient disagreements across all 380 shapes, which is the right profile for a guard whose
# own docstring says a false negative is the expensive one.
...
# ⚠ THE 28 THAT REMAIN ARE ALL NOISY, i.e. the mask declines a span a parser would keep, which costs
# a dismissible warning.
```

and backlog #267: *"**SO THIS ROW IS NOT A BUG REPORT — the guard is currently in its best measured
state.**"*

**The in-grid measurement is honest and it reproduces.** I rebuilt an equivalent
marker × indent × quote family at **760 shapes — double the lead's 380** (19 markers × 5 indents ×
4 quote prefixes × 2 previous-line contexts) and measured **0 LENIENT / 24 noisy**. The pre-fold
version on the same grid gives **28 LENIENT**, matching the stated 28 exactly. Two of the three
stated lenient figures reproduce on a grid that is not even the same size. That is a genuinely
good measurement and I am not disputing it.

**What fails is the sentence's scope.** The grid varies *markers, indents and quote prefixes*. The
CommonMark constructs that interrupt a paragraph are a larger set, and `BLANK_OR_BLOCK` has
clauses for exactly five things (blank, non-empty bullet, setext underline, `1`-ordered item, ATX
heading). Three whole block classes that **do** interrupt a paragraph have no clause at all, and
all three oracles agree against the predicate on every one:

| next line | predicate | cmark | md-it CM | md-it GFM | direction |
|---|---|---|---|---|---|
| `~~~`, `~~~~`, `   ~~~` | False | True | True | True | **LENIENT** |
| `***`, `****`, `***  `, `___`, `_ _ _` | False | True | True | True | **LENIENT** |
| `<div>`, `</div>`, `<table>`, `<pre>`, `<script>`, `<!-- c -->`, `<?php`, `<![CDATA[x`, `<!DOCTYPE h>` | False | True | True | True | **LENIENT** |
| `01. b`, `001) b` | False | True | True | True | **LENIENT** |

**19 lenient shapes, zero parser disagreement.** Note `***` is a thematic break and `___` is one
too, while a bare `---` is covered — so the file handles one of the three thematic-break spellings
and the comment's `[-=]+[ \t]*$` clause is doing setext duty, not thematic-break duty. `_` appears
in neither regex.

**It composes to the exit code, which is what makes this more than a predicate curiosity.** Driving
the real `main(["--strict", "--base", <sha>])` over a built git repository — src changed
`1,414` → `1,416`, copy left stale — with a control:

```
--- (the shipped r7 self-test case, control)   parsers_end=True  rc=1
*** thematic break                            parsers_end=True  rc=0   <-- stale figure PASSED
<!-- c --> html block                          parsers_end=True  rc=0   <-- stale figure PASSED
~~~ fenced code                                parsers_end=True  rc=0   <-- stale figure PASSED
01. ordered list                               parsers_end=True  rc=0   <-- stale figure PASSED
```

The control returns 1 on the shape the suite already pins, so this is not asserting rc=0 for any
input. The guard reports clean on a stale figure it should have caught, which its own docstring
calls the expensive direction.

**⚠ AND THE FAIRNESS POINT, WHICH CHANGES THE REMEDY:** all 19 are lenient in the **pre-fold**
version too. Measured across all three variants on exactly these 19 shapes:

```
before          {'LENIENT': 19}
first_attempt   {'LENIENT': 19}
shipped         {'LENIENT': 19}
```

**The fold introduced none of this and regressed nothing** — in-grid it took lenient 28 → 0, which
is a real improvement. So the code gap is pre-existing (filed as **H1**), and what is *new this
round* is the unscoped claim. That is why this is the Blocking item and H1 is not: shipping a
docstring that states a safety property the function does not have is the thing that stops round 8
from looking. This repository's own standard is that *"a green check over the wrong subject is an
assertion in better packaging, and more dangerous than prose, because nobody re-examines it"* —
and #267's **FAILS IF** is *"a round-8 review finds another CommonMark shape where this predicate
disagrees with both parsers in the LENIENT direction."* That condition is satisfied **19 times**,
in round 7, by the shapes the row's own measurement could not see.

**⛔ DIRECT ANSWER TO QUESTION (a) — is #267's framing honest, or a treadmill dressed as a decision
point?** It is honest in its *provenance* and self-serving in its *conclusion*, and the two are
separable:

* **Honest:** it names its corpus ("380 generated marker/indent/quote shapes"), names its oracles,
  reports the first-attempt regression against itself, pre-commits a falsifier, and says out loud
  that landing near option ② happened "BY MEASUREMENT rather than by decision". Pre-committing a
  falsifier that then fires is the row working as designed, not failing.
* **Not honest as written:** "**the guard is currently in its best measured state**" and "**THIS
  ROW IS NOT A BUG REPORT**" are inferences from the grid to the predicate, and they are false.
  Four cheap clauses — `~~~`/```` ``` ````, `[*_-]{3,}`, a leading `<`, `\d+[.)]` with a `1` start
  check — would move 19 measured lenient shapes to 0 without touching the design question at all.
* **So the treadmill framing is premature rather than wrong.** The choice between "depend on a real
  CommonMark parser" and "stop tracking the spec" is a real design question and worth the owner's
  time. But it is being offered while a bounded, enumerable, non-judgemental set of block starts is
  still missing — and presenting the remaining gap as *design* implies no cheap correctness work is
  left, which is the part that is self-serving. **Fix the 19, then ask the design question against a
  predicate that is actually at its best measured state.**

**Remedy:** (1) scope the sentence — "zero lenient disagreements *across the 380 marker/indent/quote
shapes measured*; constructs outside that family (fenced code, thematic breaks, HTML blocks,
leading-zero ordered lists) are **not** covered and are lenient"; (2) amend #267 to carry the 19
shapes as a named, bounded defect set, so its FAILS IF is not already satisfied on the day it is
filed.

---

## High

### H1 — Three CommonMark block classes that interrupt a paragraph have no clause in `BLANK_OR_BLOCK`, and `01.` defeats the `1`-only ordered-list rule

The code defect behind B1, filed separately because its age and its remedy differ: it is
**pre-existing** (identical in `54625c75`), so it blocks nothing about this fold, but it is now
measured, enumerated and cheap.

```python
BLANK_OR_BLOCK = re.compile(
    r"[ \t\r]*$"                                # blank
    r"|[ \t]{0,3}(?:[-*+][ \t]+\S"              # a NON-EMPTY bullet
    r"|[-=]+[ \t]*$"                            # a setext underline (`-` alone, `=` alone)
    r"|1[.)][ \t]+\S"                           # an ordered item, and only a `1` interrupts
    r"|#{1,6}(?:[ \t]|$)"                        # an ATX heading, at most six hashes
    r")")
```

Missing: a fenced-code opener (`~~~`/`` ``` ``, ≥3 of either, with an optional info string), a
thematic break (`***`/`___`/`---` in ≥3 repetitions with optional internal spaces — only the
`---` spelling is caught, and incidentally, by the setext clause), and an HTML block (types 1–6).

**The `01.` case is a distinct sub-defect inside a clause that looks complete.** The comment says
*"an ordered item, and only a `1` interrupts"*, which is the right rule; `1[.)]` is a **textual**
test for it, and CommonMark's rule is about the parsed *start number*. `01.` and `001)` both parse
to start 1 and both interrupt — measured, all three oracles True, predicate False. The correct
test is `0*1[.)]`, not `1[.)]`.

**What I ran:** `attack.py` over 52 out-of-grid shapes; `regress.py` over the 19 against all three
variants; `live.py` driving `main()` with a control. Figures above.

### H2 — The `\r` tolerance from r6 L1 was applied to ONE of five alternatives, so under CRLF a bare setext underline and an empty ATX heading become lenient

The blank clause carries the comment *"`\r` so a CRLF break still counts (r6 L1)"*. Three of the
other four alternatives terminate with `$` or `[ \t]*$`, and `$` does not match before a `\r`:

```
alternative          '---'   '---\r'    '#'    '#\r'
blank                False   False      False  False
non-empty bullet     False   False      False  False
setext underline     True    False      False  False     <-- loses it
ordered '1'          False   False      False  False
ATX heading          False   False      True   False     <-- loses it
```

Measured end-to-end at the real call site, on the **same text** as the shipped r7 `---` case:

```
LF   bare '---'  parsers_end=True  marker=''        (survivor — correct)
CRLF bare '---'  parsers_end=True  marker='was '    SUPPRESSED
```

So `` `wrong:\r\n---\r\nholds 1,414 anchors today` `` hides the figure while the LF spelling does
not. Lenient under CRLF: bare `-`, `=`, `---` (and `===`), and empty ATX `#`. `###### h\r`,
`- b\r`, `1. b\r` are unaffected, because a space after the marker absorbs the match.

This is **instance-not-class**: r6 L1 found the defect in the blank clause and fixed only that
clause. `ANY_BLOCK_ISH` does not share the bug — its markers need no trailing context — which is
why it only shows up on the fresh-paragraph path. `---` is ubiquitous in this repository's
markdown, and the repo has already decided CRLF is in scope by paying for r6 L1.

**Remedy:** strip a trailing `\r` from `nxt` once in `paragraph_ends_between`, rather than adding
`\r` to four more alternatives — one place, and it cannot drift to a fifth clause later.

### H3 — The first-attempt story (28 lenient → 32) is not reproducible, and the only reconstructible definition of that subject contradicts its direction

Asserted in the code comment, in backlog #267, and in the r7 manifest entry:

```
# ⛔ THE FIRST ATTEMPT HALVED THE TOTAL AND MADE THE EXPENSIVE DIRECTION WORSE — 28 lenient to 32 —
# and the aggregate would have read as an improvement.
```

and the manifest entry for the lazy branch: *"Measured: this is what drove the LENIENT
disagreement count from 28 UP to 32 while the total looked like it improved."*

**That entry defines the first attempt mechanically** — the shipped predicate with the
lazy-continuation branch severed — so the claim is testable even though no commit holds it. I built
exactly that (`elif pq:` → `elif False:`, confirmed to parse) and measured all three variants over
one 760-shape grid:

```
before          LENIENT=  28  noisy=  51  total=  79
first_attempt   LENIENT=  12  noisy=  16  total=  28
shipped         LENIENT=   0  noisy=  24  total=  24
```

`before` = 28 lenient and `shipped` = 0 reproduce the stated figures exactly. **`first_attempt`
gives 12, not 32 — and 12 is *below* the pre-fold baseline of 28, i.e. the expensive direction
IMPROVED.** The claimed regression does not reproduce in direction, let alone magnitude.

Two readings, and I cannot separate them from the repo alone:

1. the lead's actual first attempt differed from the manifest entry's description of it, in which
   case **the manifest entry's name is wrong** — it tells a future reader that severing this branch
   reproduces 28→32, and it does not;
2. the 32 was mis-taken, in which case the lesson drawn from it is drawn from nothing.

Either way a **load-bearing retrospective number has no reproducible provenance**, and it is cited
in three places as the reason to trust the shipped profile. It is also the one number of the three
whose subject is absent from the repository. The lesson itself ("an aggregate improving while the
expensive direction regresses") is sound and worth keeping — but it should be attached to a
measurement that can be re-run, or explicitly marked as unreproduced.

**What I ran:** `variants/{before,first_attempt,shipped}.py` on a copy; `trend.py`. Nothing under
the worktree's `scripts/` was modified.

---

## Medium

### M1 — A GFM table with its delimiter row interrupts a paragraph, and a pairwise predicate structurally cannot see it

The comment justifies excluding `|` precisely by appeal to the delimiter row:

```
#   `| `                          **NO** — a GFM table needs a         yes — a table row is its
#                                 delimiter row                        own statement (r2 Codex)
```

The reasoning is right and the conclusion is drawn one line too early: when the delimiter row **is**
present, a table does start and does interrupt. `paragraph_ends_between` compares only `prev`/`nxt`
line pairs, so it can never see two lines ahead.

```
header + delimiter   | h |  /  |---|      predicate=False  cmark=True  md-it-CM=False  md-it-GFM=True
2-col + delimiter                         predicate=False  cmark=True  md-it-CM=False  md-it-GFM=True
header only (no delimiter)                predicate=False  all three False   (correct)
```

**This is the one place my oracles split, and the split is informative rather than a problem:**
strict CommonMark has no tables, so `md-it-CM` is right to say no; both **GFM** parsers say the
paragraph ends. This repository's markdown is rendered by GitHub, so GFM is the operative dialect
and this is lenient in the dialect that matters. I hold it at Medium rather than High for two
reasons: the oracle agreement is 2-of-3 rather than unanimous, and unlike H1/H2 it cannot be fixed
by adding a clause — it needs lookahead, which is a genuine argument for #267's option ①. It is
better evidence for that design question than anything currently in the row.

### M2 — The two direct `paragraph_ends_between` call sites re-introduce hand-written bounds, and a stale bound passes silently in 3 of 10 perturbations

Question (b). **The call sites are sound as cases and the bounds are correct today** — I verified
both by indexing:

```
quote OPENS    start=7 doc[start]='a'  end=12 doc[end]='`'  span='a\n> b'      peb=True  want=True
bare - setext  start=7 doc[start]='a'  end=13 doc[end]='`'  span='a\n- \nb'    peb=True  want=True
```

Both assert real, distinct behaviour (a `>` that *opens* a quote interrupts; a bare `-` is a setext
underline, not a list item) and both would go red if that behaviour broke. So **this is not merely
a dodge** — the gate was telling you something real (one call site records one argument expression
per parameter, however many documents the cases hand in), and the two new cases are load-bearing,
not padding. On the narrow question asked: **sound.**

**The concern is the mechanism chosen.** `len("intro `")` is a *second copy* of the document
literal's prose prefix, coupled to it by nothing — which is the hazard `_ends_in_span` was
introduced in this very diff to eliminate:

```
⛔ Typed offsets are how this file has already been wrong twice: a hand-counted index put a
figure inside `anchors:` instead of on the number, and again here on a quote fixture.
```

`len()` of a retyped prefix is derived from *a copy of* the text, not from the text. Perturbing only
the literal's prefix, leaving the `len()` expressions as a future edit would:

```
prefix='intro '         slice='a\n> b'      peb=True  passes        (shipped, correct)
prefix='intr '          slice='\n> b`'      peb=True  passes   <-- SILENT: stale bounds, green
prefix='in '            slice=' b` x'       peb=False RED (loud)
prefix='the count '     slice='nt `a\n'     peb=True  passes   <-- SILENT (case 2), green
prefix='introduction '  slice='ction'       peb=False RED (loud)
```

**3 of 10 perturbations keep the case green with the bounds pointing into prose** — the assertion
then holds for a boundary other than the one its name describes. Most perturbations do fail loudly,
which is why this is Medium and not High.

**Remedy that keeps both properties:** vary the *expression* without retyping an offset — e.g. a
second helper that derives bounds from a named opener (`_ends_after(doc, opener)` using
`doc.index(opener)`), or pass `doc.index(...)` expressions inline. That gives
`check-fixture-variation` its distinct expressions *and* keeps every bound derived by `str.index`.

---

## Low

### L1 — `ANY_BLOCK_ISH` is too broad in the cheap direction on 7 of 19 lazy-continuation shapes, including the bare `=` the lead asked about

Question (c), second half. Inside a quote, on a non-`>` line:

```
noisy   '='          predicate=True   parsers all False
noisy   '=='         predicate=True   parsers all False
noisy   '####### b'  predicate=True   parsers all False      (7 hashes is not a heading)
noisy   '#b'         predicate=True   parsers all False      (no space is not a heading)
noisy   '+x' '-x' '*x'  predicate=True  parsers all False    (no space after the marker)
ok      '2. b' '2) b' '999. b' '01. b' '| b' '>x' '[a]: /u' 'plain' '***'
LENIENT '~~~' '<div>' '___'                                  (the same B1/H1 class)
```

So **yes, it is too broad, and on the bare `=` specifically** — but every over-broad case lands in
the *noisy* direction, which is the declared and acceptable one, and the docstring's statement that
the residual is "concentrated in block-quote contexts … from lazy-continuation shapes the broad
`ANY_BLOCK_ISH` test refuses conservatively" is accurate. Tightening it (`[-*+]` requiring a
following space, `#{1,6}` bounded, `=` dropped) would reduce noise and is not urgent. Worth noting
`ANY_BLOCK_ISH` still misses `~~~`, `<`, and `_`, so being "broader" did not make it a superset of
the block starts that matter.

### L2 — `parse_fail_names`' docstring states a stricter rule than its code applies, and the gap cost a measurement cycle

`scripts/check-plan-code.py:2901` (in the diff's file set):

```
      * only a line STARTING with `[FAIL] ` is a case name. A mid-line marker is not — measured
        round 5, where slicing `[7:]` blind produced a confident, wrong name;
```

The code is `l.strip().startswith("[FAIL] ")` — it **strips first**, so an indented line *is*
accepted, which is necessary because `case()` prints `f"  [FAIL] {name}: …"` with two leading
spaces. The behaviour is correct and the sentence describing it is not: a reader implementing
against the docstring (as #266's prototype and I both did) anchors at column 0 and finds zero
failures on a mutant that died properly — reading as "nothing could see the kill" on every entry.
The docstring's point is about *mid-line* markers; it should say "a line whose first non-space text
is `[FAIL] `", which is both what the code does and what the round-5 finding meant.

---

## Checked and found SOUND

**Every arithmetic claim in the brief reproduces.** The brief warned that nine stated figures had
failed to reproduce on this branch; this round, none did.

| claim | how checked | result |
|---|---|---|
| `EXPECTED_MUTATIONS` sums to **1,533** over **62** manifests, every per-file count matching disk | imported the module, summed the dict, counted `scripts/mutations/*.json`, tallied every entry's `file` | **1,533 / 62 / 62**, disk total 1,533, **0 mismatches**, no undeclared files |
| suites **86 / 128 / 155 / 237 / 51** | ran each `--self-test` under 3.12 | `find-claim` 86, `check-withdrawal` 128, `check-provenance` 155, `check-plan-code` 237, `codex-frontier-model` 51 — all ✅ |
| *(stronger, unrequested)* all declared counts | `python3.12 scripts/check-selftest-counts.py` | rc=0, **"55 script(s) declare a count, every one verified by running it"** |
| `--binding` rc=0 over **1,541 anchors / 1,533 entries** | ran it | rc=0, *"1541 anchor(s) across 1533 entries each resolve to exactly one site"*, 67 explained expects |
| diff **326 / 20 over 3 files** | `git diff --shortstat e70aa551..bbdb3204 -- scripts/` | exact |
| in-grid "**0 lenient**" | rebuilt a 760-shape marker × indent × quote grid (2× the lead's) | **0 LENIENT / 24 noisy** — the claim holds within its family, and pre-fold reproduces at 28 |
| `EXPECTED_MUTATIONS` 30 → 34 and sum 1,529 → 1,533 | 4 new JSON entries in the diff; `+4` on both | consistent; the fifth `+1` in the comment trail (r6 Codex M1) was already inside the 30 |

**(c) THE ASYMMETRY BETWEEN `BLANK_OR_BLOCK` AND `ANY_BLOCK_ISH` IS CORRECT, AND THE PARSERS
CONFIRM THE STATED JUSTIFICATION.** The claim is that an empty marker closes a quote but cannot
interrupt a fresh paragraph. Six probes, all three oracles unanimous, predicate matching every one:

```
in-quote,  empty '* '   predicate=True   parsers (True, True, True)
in-prose,  empty '* '   predicate=False  parsers (False, False, False)
in-quote, empty '1. '   predicate=True   parsers (True, True, True)
in-prose, empty '1. '   predicate=False  parsers (False, False, False)
in-quote, plain prose   predicate=False  parsers (False, False, False)
in-prose, plain prose   predicate=False  parsers (False, False, False)
```

The asymmetry is not a hedge — it is the measured behaviour, in both directions, and the comment
explaining it is accurate. This is the strongest-grounded part of the fold.

**The four new mutations all kill via their named cases, over a proven-green control.** Applied to
a staged **copy** of `scripts/` with `HOME` redirected (the redirect #266 calls load-bearing),
attribution read with the harness's **own** `parse_fail_names` rather than a re-derived contract,
`expect` asserted to be a list not a string (#266's trap), and each mutant `ast.parse`d first so a
SyntaxError could not masquerade as a kill:

```
control: rc=0  128/128 passed
KILLED via NAMED case    rc=1 failures=2   r5 Codex H1 (second witness) — blank-line rejection severed
KILLED via NAMED case    rc=1 failures=2   r6 Claude H1 — memo keys on id(text) again
KILLED via NAMED case    rc=1 failures=1   r6 Claude M1 — PARA_END forgets a BLOCK START
KILLED via NAMED case    rc=1 failures=1   r7 Codex H1 — a quote line always ends the paragraph
KILLED via NAMED case    rc=1 failures=1   r7 — the LAZY-CONTINUATION branch severed
```

Each anchor resolved to exactly one site. The two retargeted entries (r5 Codex H1, r6 Claude M1)
genuinely still bind to a live subject in its new form, so "retarget, not retirement" is accurate.

**The memo-by-value fix (r6 Claude H1) is correct and its reasoning is right where I expected it to
be wrong.** `id()` reuse requiring same-size objects *does* make the length a dependent rather than
an independent discriminator, so the deleted sentence was false in the way the docstring now says.
`_memo_key_probe` is a fair deterministic stand-in: it plants the entry an id-keyed memo would
serve and asserts the current key cannot reach it, which is falsifiable without requiring allocator
behaviour no case can force. The `main()`-entry `_MASKED_DOCS.clear()` bounds the memo to one run.
Keying by full text holds a reference to every document plus its mask, but the clear-per-run bounds
it and masking is already O(n), so the trade is sound.

**`paragraph_ends_between` does not crash on any degenerate input I could construct** — six probes:
an unterminated span, a document ending on a newline, a document ending at the opener, `end` past
`len(text)` (10,000), inverted bounds (`start=10, end=2`), and an empty range. All returned a bool;
the `nxt_end == -1 → len(text)` fallback is the reason, and the `nl < end` loop guard makes inverted
and empty ranges trivially False.

**Quote depth is right in all four directions**, which is the part r7 Codex H1 was about: open
(prose → `>`) True, continue (`>` → `>`) False, deepen (`>` → `>>`) True, **shallow (`>>` → `>`)
False** — the fourth is not in the comment's table and all three oracles agree with the code.
Quote-after-list-item, list-inside-quote and `>x` (no space) are all correct.

**Tabs are wrong only in the cheap direction.** CommonMark expands a tab to a four-space stop, so
`\t- b`, ` \t- b` and `\t> b` are indented code and do not interrupt; the predicate's
`[ \t]{0,3}` counts a tab as one character and says they do. All three are **noisy**, and a
tab-only line is correctly blank. Worth knowing, not worth fixing ahead of H1/H2.

**Link reference definitions are correctly excluded** (`[a]: /u`, `   [a]: /u` — cannot interrupt,
predicate False, oracles False), and the seven-hash and no-space heading near-misses
(`####### b`, `#b`) are both correctly False on the fresh-paragraph path.

**The `_drive_span_window` flag removal (r6 Claude L3) is sound.** With the control replaced by a
known positive the parameter had one live value, so its `False` branch was unexercised code shaped
like a choice; the later span is what creates the spurious pair, so making it unconditional is
right. The surviving `suppressed` parameter still takes both values and remains a real known
positive (rc=0 against the case's rc=1).

**The one-rule-per-question argument for keeping `SENTENCE_SPLIT` separate from the mask's rule is
correct**, and I tried to refute it. `2)` is the discriminator: both parsers report a code span in
`` `anchors\n2) 1,414` `` (only a `1` may interrupt), while `SENTENCE_SPLIT` wants a boundary there
because a numbered line reads as a new statement regardless. Collapsing them would break the
masking case, exactly as the comment says. Confirmed: `2. b`/`2) b`/`999. b` oracles all False on
the fresh-paragraph path.

---

## CANNOT RUN

Each of these is a **failure, not a pass** — treat the corresponding claim as unverified.

1. **The lead's exact 380-shape generator is not in the repository**, so I could not re-derive
   28/28/56 → 32/4/36 → 0/28/28 as stated. I built an equivalent 760-shape grid of the same
   described family instead. The pre-fold **28 lenient** and shipped **0 lenient** reproduced
   exactly; the noisy counts did not (51 and 24 against 28 and 28), which is expected on a
   different grid and means **the noisy figures specifically are unverified**.
2. **The first attempt's actual source does not exist anywhere I can reach** — not a commit on the
   branch, not in `scratchpad/r6`. I reconstructed it from the r7 manifest entry's own description
   and it contradicted the claim (**H3**). The claim as stated remains **unverifiable**, and my
   refutation is of the reconstruction, not provably of the original.
3. **The full-repo attribution sweep (#266) is still NOT RUN.** I ran 5 entries of 1 file. Whether
   any of the other ~1,528 entries is unattributable is unmeasured — this is now the **third**
   reviewer to leave it unfinished, and #266's text already says so. It should stop being carried
   as a review task and be sized as work.
4. **`python3 scripts/check-plan-code.py --mutate .` (the full sweep CI runs) was not executed** —
   on this repo that is ~20 minutes and the brief's instruction was to stop measuring and report.
   So "no mutation anywhere in the repo was orphaned by this fold" is **not** established by me;
   `--binding` rc=0 covers anchor resolution only, and #266 is precisely the gap that `--binding`
   cannot see (it reads `edits[i][0]`, never the replacement).
5. **No `~~~`-vs-`` ``` `` equivalence was measured for the fenced-code half of H1.** My oracle
   construction uses backticks as the span delimiters, so a backtick fence cannot be tested through
   it; I measured `~~~` and am inferring the backtick spelling from CommonMark treating them as one
   block type. The backtick fence is the spelling that actually occurs in this repository, so this
   inference is load-bearing for H1's real-world frequency and should be confirmed by a different
   construction before H1's priority is set.

---

## What I ran, for reproduction

All under `scratchpad/r7-claude/`, all against a **copy**; the worktree's `scripts/` is untouched
and `git status` showed only this review file.

| script | what it establishes |
|---|---|
| `oracle.py` + `sanity.py` | the three-way oracle; 7 known shapes, both directions |
| `attack.py` | 52 out-of-grid shapes → 19 LENIENT, 4 noisy, 1 split |
| `e2e.py` | the same shapes at `history_marker`, with the shipped `---` case as control |
| `live.py` | real `main()` over built git repos → rc 1 (control) vs 0 (four lenient shapes) |
| `grid.py` | 760-shape marker × indent × quote grid → 0 LENIENT / 24 noisy |
| `trend.py` + `variants/` | before / first-attempt / shipped → 28, 12, 0 lenient |
| `regress.py` | the 19 lenient shapes are pre-existing in all three variants |
| `asym.py` | the (c) asymmetry (6 probes), `ANY_BLOCK_ISH` breadth (19), CRLF (8) |
| `crlf_b.py` | CRLF suppression at the call site; per-alternative `\r` tolerance |
| `b_rigorous.py` | the shipped bounds are correct; 3 of 10 perturbations silently green |
| `final.py` | GFM tables, quote-in-list, degenerate bounds, tabs |
| `mut3.py` | the 4 new mutations kill via named cases, green control, `ast.parse` guard |

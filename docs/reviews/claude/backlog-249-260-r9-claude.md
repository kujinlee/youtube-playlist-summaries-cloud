# Round 9 — Claude adversarial half, PR #371 `backlog-249-260-fixes`

    HEAD under review   47e33e71
    round 8's fold      7d33721e   (+ aeab1f02, a masked gate)
    scope               git diff d6967caa..47e33e71 -- scripts/ docs/backlog.md
    gates               python3.12 (CI's pin); this machine's python3 is 3.14 and was not used
    oracles             cmarkgfm + markdown-it-py, commonmark AND gfm-like(linkify off)

**Mandate was to REFUTE six named claims, not to confirm them.** Four of the six are refuted, two
hold. ⛔ **The fold's stated residual is wrong in the LENIENT direction**: the note says three
shapes remain, one an oracle artifact and two interleaved containers that #267 owns. Measured over
3,902 adjudicated shapes, **1,199 are LENIENT at HEAD**, in four classes, three of which are neither
interleaved nor nested deeper than one level, and two of which close with a one-token local change
that costs zero noise anywhere I can measure.

⛔ **Merging is the human gate and has not been given. Nothing here recommends merging.** #267's
design question (a real CommonMark parser vs stop tracking the spec) is the owner's call; this half
adds evidence and does not decide it. Convergence (two consecutive rounds with no Blocking and no
High) stands at **0 of 2** and this round does not advance it.

---

## The one table to read

Both halves of this project's direction rule are in it. LENIENT = the mask whitens a real boundary,
so a span swallows a history marker and a **stale figure is reported as history** — silent, and the
expensive direction. NOISY = a real span declined, costing a dismissible warning.

Every corpus below is generated fresh and adjudicated by cmark-gfm **and** markdown-it in **both**
dialects; a shape where the three disagree is excluded, never counted either way.

| corpus | n | split | r8 fold `7d33721e` L/N | **HEAD `47e33e71` L/N** | HEAD + the two fixes below |
|---|---|---|---|---|---|
| grid, the note's own (1,620) | 1620 | 4 | 0 / 34 | **0 / 34** | 0 / 34 |
| list, the note's own (196) | 196 | 0 | 0 / 0 | **0 / 0** | 0 / 0 |
| new-class, the note's own (294) | 294 | 0 | 170 / 0 | **3 / 0** | 1 / 0 |
| **C1** span opens on a LAZY continuation | 196 | 0 | 130 / 0 | **130 / 0** | 0 / 0 |
| **C2** a list inside a quote, block start `>` | 140 | 0 | 10 / 0 | **10 / 0** | 0 / 0 |
| **C3** block start between OUTER and INNER column | 448 | 0 | 384 / 0 | **384 / 0** | 384 / 0 |
| **C4** an ordered marker other than `1` in an item | 672 | 0 | 672 / 0 | **672 / 0** | 672 / 0 |
| **C5** a legal INDENTED paragraph lead | 336 | 0 | 0 / 0 | **0 / 156** | 0 / 156 |
| **TOTAL** | **3902** | **4** | **1366 / 34** | **1199 / 190** | **1057 / 190** |

Read the net of this fold across that corpus: **LENIENT −167, NOISY +156**. The −167 is exactly the
fold's claimed `170 → 3`, which reproduces. The +156 sits entirely in C5, which is the one place the
shipped code says it has no effect (`scripts/check-withdrawal.py:554`).

A separate container sweep — 28 container spellings × 11 pad columns × 18 middles × {LF, CRLF},
**11,052 adjudicated shapes** — puts HEAD at **630 LENIENT / 214 noisy** and agrees on the shape of
the residual: 133 distinct (container, pad) cells.

---

## Blocking

### B1 — the shipped residual claim understates the LENIENT residual by three orders of magnitude, in the note whose only job is to stop that

`scripts/check-withdrawal.py:429-434`:

```
# ⚠ THE THREE RESIDUAL, NAMED RATHER THAN ROUNDED AWAY: one is an ORACLE ARTIFACT — a tab at
# column 0 is four columns of indent, so `'\t- intro …'` is an INDENTED CODE BLOCK and cmark
# renders the whole document as `<pre><code>`, …
# The other TWO are interleaved containers nested deeper than one level, which is the
# bound `list_content_column` states in its own docstring and which #267 owns.
```

restated at `:557-559` and carried into `docs/backlog.md` #267 as *"the residual being one oracle
artifact and two interleaved containers"*.

**Both halves of that sentence are false.**

1. **The count is not three.** Three is the residual *of the 294-shape corpus the fold wrote for
   itself*. Over 3,902 shapes it is **1,199**, in four classes (C1-C4 above), each with a
   three-parser witness. This is the note's own named failure — *"every 'zero' here has been a
   statement about a grid"* (`:398`) — committed for the sixth consecutive round, inside the
   paragraph that states it.
2. **The two shapes it does name are misattributed, and that is the part that misdirects the next
   round.** The note calls them *interleaved containers nested deeper than one level*, hands them to
   `list_content_column`'s docstring bound, and from there to #267 — i.e. to a structural redesign
   that is the owner's call. They are neither. `list_content_column` returns the **correct** column
   on them; the defect is the comparison at `:661`, and the simplest witness is a single quote
   around a single list item:

```
>   - intro `a
>     > q
>     b` x
```

   `cont` is 4, which is right. All three parsers end the paragraph. HEAD does not. There is no
   interleaving and nothing is nested deeper than one level. The one-token repair in H2 below closes
   all ten of my C2 shapes and **both** of the two the note names, with **zero** added noise across
   all 3,902 shapes — so the residual the note parks as a design question costs a comparison.

**Direction: LENIENT.** A reader who trusts `:429-434` concludes the predicate is at its measured
floor and that what is left needs #267. Both conclusions are wrong, and this is the precise
mechanism by which eight of the nine rounds have handed the next round a false floor.

**FAILS IF** — the falsifier I would put on the corrected sentence: a corpus of at least 2,000
adjudicated shapes drawn from container spellings **not** generated by this file's own fixtures
reports more LENIENT shapes than the sentence names.

---

## High

### H1 — the container is lost entirely when the span opens on a LAZY continuation line: 130 of 196, untouched by all three generations of this fix

`scripts/check-withdrawal.py:637-648`. The walk-back carries quote depth as a running **maximum**
(`depth = max(depth, pd)`, `:645`) and then reads the list content column from **one** line only:

```
647:    _, first_rest = quote_depth(text[scan:text.find("\n", scan)])
648:    cont = list_content_column(first_rest)     # ⛔ r8 Claude H1 — 0 at top level, a no-op there
```

A paragraph continuation line may be **lazy** — it omits the container prefix entirely. When the
span opens on such a line, `scan` lands on it, `first_rest` has neither a marker nor an indent, and
`cont` comes back **0**. r9 Codex H1's INDENT fallback does not help: there is no indent to read.

Witness, all three parsers agreeing the paragraph ends, HEAD finding the marker `was ` and therefore
**exempting the figure**:

```
  - first
intro the count was `wrong:
    - x
    holds 1,414 anchors today`
```

    cmark: <ul><li>first\nintro the count was `wrong:<ul><li>x\nholds 1,414 anchors today`</li></ul></li></ul>
    trace: scan_line='intro the count was `wrong:'  cont=0  depth=0
    marker(HEAD) = 'was '   →  the figure is suppressed as history

Measured: **130 of 196** C1 shapes LENIENT at round 8's fold **and** at HEAD — this fold moved the
class by zero. Every content column ≥ 4 is affected; columns 2 and 3 are inside `BLANK_OR_BLOCK`'s
own cap.

**Direction: LENIENT.**

**Fix, verified on a copy** (never the worktree): carry the content column across the walk-back the
way `depth` already is, *including the line that breaks it* — that is where the marker lives.

```python
    scan, cont_seen = line_start, 0
    while scan > 0:
        prev_start = text.rfind("\n", 0, scan - 1) + 1
        pd, prest = quote_depth(text[prev_start:scan - 1])
        if BLANK_OR_BLOCK.match(prest):
            cont_seen = max(cont_seen, list_content_column(prest))
            break
        depth = max(depth, pd)
        cont_seen = max(cont_seen, list_content_column(prest))
        scan = prev_start
    _, first_rest = quote_depth(text[scan:text.find("\n", scan)])
    cont = max(cont_seen, list_content_column(first_rest))
```

C1 **130 → 0**; grid, list and new-class corpora unmoved; noise unchanged at 190 across all 3,902
shapes. ⚠ Adding `cont_seen` only *inside* the loop and not at the `break` leaves all 130 standing —
I measured that first and it does nothing, because the walk-back breaks **at** the marker line.

**FAILS IF:** a paragraph whose span opens on an unindented continuation of a list item reports a
content column of 0.

### H2 — `d2 > d` is the wrong comparison: it can never fire inside a quote, and a strictly better variant passes all 163 cases unchanged

`scripts/check-withdrawal.py:653-663`:

```
660:            d2, rest2 = quote_depth(rest)      # a `>` can sit AT that column, past QUOTE_MARKER's
661:            if d2 > d:                         # 3-space cap — that was the last 10 of the 130
662:                return True
```

`d` is the quote depth already stripped from the line; `d2` is the depth found **past** the content
column. The line's total depth is `d + d2`, and the open paragraph's is `depth`. The test that
belongs here is `d + d2 > depth`. As written, when the list sits inside a quote (`d ≥ 1`) a single
nested `>` gives `d2 = 1` and `1 > 1` is false — the clause is **structurally dead at every quote
depth ≥ 1**, which is exactly where the clause was added for.

Measured: **10 of 140** C2 shapes LENIENT, two per container spelling (`> - - `, `> 1. 1. `,
`>   - `, `> > - - `, `>> - - `) × {LF, CRLF} — unchanged from round 8's fold. Plus the two shapes
B1 misattributes to interleaving.

**Direction: LENIENT.**

**Fix, verified on a copy:** `if d + d2 > depth:`. C2 **10 → 0**, the note's own 294-corpus
**3 → 1** (the remaining one is the acknowledged tab-at-column-0 artifact), grid/list unmoved,
**noise unchanged at 190 across all 3,902 shapes**. Free in both directions.

⛔ **And the statement is unprotected by anything.** Mutating `d2 > d` → `d2 > 0` keeps the suite at
**163/163** while *removing* 12 LENIENT shapes and adding no noise — a strictly better predicate that
no case can tell from the shipped one. The manifest entry that covers this clause mutates it to
`if False:` (`scripts/mutations/check-withdrawal.json`), which pins only that the clause exists, not
what it compares. `d2 >= d` is killed (160/163); `d2 > 0` is not.

**FAILS IF:** `paragraph_ends_between` returns False for a line whose total quote depth exceeds the
open paragraph's, reached past a list content column.

### H3 — `cont` is a single column, but a block start interrupts at ANY column from the OUTERMOST container's upward: 384 of 448

The predicate strips exactly `cont` columns and requires `c >= cont` (`:658`). `cont` is the
**innermost** content column. CommonMark closes the inner item for a block start anywhere at or
right of the **outer** item's content column, so every column in `[outer, inner)` is a boundary the
guard cannot see — and those columns are past `BLANK_OR_BLOCK`'s own 3-space cap whenever the outer
column is ≥ 4.

This bites the fold's **own** container spelling. `scripts/check-withdrawal.py:1440-1442` pins
`- - - ` with its block start at column 6, the innermost column. The same container at columns 4 and
5 is LENIENT:

```
- - - intro `a
    # h
    b` x
```

    parsers (cmark, mdit-cm, mdit-gfm) = (True, True, True)   HEAD: paragraph does not end

Measured per cell: `- -@4` 24, `- -@5` 24, `- - -@4` 48, `- - -@5` 48, `- 1.@4` 24, `- 1.@5` 24,
`- 1.@6` 24, `1. 1. 1.@4..8` 24 each — **384 of 448**, identical at round 8's fold and at HEAD.
Neither of the fixes above touches it, by construction: no single integer can express "any of a set
of columns".

**Direction: LENIENT.** ⚠ This is the finding that bears on #267 rather than on the fold: a scalar
`cont` is the wrong shape for the problem, and the correct local repair is a **list** of open
container columns — which is a block-structure stack, i.e. the thing #267 says to stop hand-rolling.
I state that as evidence; the decision is the owner's.

**FAILS IF:** a block start at the outer content column of a two-level list item does not end the
item's paragraph.

### H4 — `0*1[.)]` is right at top level and wrong inside a list item, which is r8 Claude H1's mistake for the third time: 672 of 672

`scripts/check-withdrawal.py:484`:

```
    r"|0*1[.)][ \t]+\S"        # an ordered item: only the NUMBER ONE interrupts,
                               # and `01.`/`001)` ARE one — measured (r7 H1)
```

The rule is correct where it was measured. Inside a list item it does not apply, because such a line
is not *interrupting a paragraph* — it is **closing the enclosing item**, and any ordered number does
that. The boundary is sharp and I pinned it:

| document | parsers | HEAD |
|---|---|---|
| `intro \`a\n2) x\nb\` x` (top level) | continue | continue — **ok** |
| `> intro \`a\n> 2) x\n> b\` x` (quote) | continue | continue — **ok** |
| `- intro \`a\n2) x\nb\` x` (pad 0 < col 2) | **END** | continue — ⛔ **LENIENT** |
| `- intro \`a\n 2) x\n b\` x` (pad 1 < col 2) | **END** | continue — ⛔ **LENIENT** |
| `- intro \`a\n  2) x\n  b\` x` (pad 2 = col 2) | continue | continue — **ok** |

Measured over 672 shapes (8 containers × {`2`,`3`,`9`,`10`,`999`,`0002`} × {`.`,`)`} × every pad
below the content column × {LF, CRLF}): **672 LENIENT, 0 noisy**, identical at round 8's fold, at
HEAD, and under both fixes above.

⛔ **This is structurally r8 Claude H1 again — a rule that is right at top level and wrong inside an
item — for the third round running.** r8 found it for the indentation cap, r9's Codex half found it
for the column's provenance and its units, and the ordered-marker clause has it too.

**Direction: LENIENT.**

⚠ **What I am NOT recommending.** Widening the clause to `\d{1,9}[.)][ \t]+\S` takes total LENIENT
**815 → 215** at a cost of noise **34 → 54** over the corpora that contain ordered middles. That
trade matches the guard's doctrine, but it is a blind widening of exactly the kind
`list_content_column`'s docstring warns against (`:548-549`): the correct rule is context-dependent —
`0*1` at or right of the content column, any number left of it — and widening makes the clause wrong
in the other direction instead. Recorded as evidence, not as a fix.

**FAILS IF:** `2) x` at column 0 beneath `- intro` does not end the item's paragraph.

### H5 — the fold's own tab case cannot pin tab expansion: a 163/163 mutation makes it LENIENT on 26 shapes

`_column` (`:506-516`) is the fix for r9 Codex H2. Its witness case (`:1470-1474`) is
`-\t- the count was \`wrong:` with the block start at **8** spaces. The container's content column is
**6**. A case whose block start is two columns past the column it means to pin cannot distinguish 6
from 7 or 8 — the "two distinct inputs" failure, with the fixture supplying the slack.

Mutation, applied to a staged copy of `scripts/`:

```
col = (col // 4 + 1) * 4 if ch == "\t" else col + 1     →     col = col + 4 if ch == "\t" else col + 1
```

    self-test: 163/163 passed       corpus: +26 LENIENT, +0 noisy
    witness:  '-\t- intro `a\n      # h\n      b` x'   parsers=(True,True,True)  mutant: continues

I also measured the real column directly: at `-\t- `, pads 6, 7 and 8 all end the paragraph and HEAD
agrees, but **pad 5 is LENIENT at HEAD today** (that one is H3, not this mutation). Adding a case at
the exact content column — pad 6 — kills this mutation and is the missing pin.

**Direction: LENIENT.**

**FAILS IF:** replacing a tab stop with a fixed `+4` leaves the suite green.

---

## Medium

### M1 — "the defect is exactly CONTENT COLUMN >= 4" is false, and a green mutation proves it

`scripts/check-withdrawal.py:547-549` states it in bold, and the self-test negative at `:1447-1449`
is built to assert it. Measured counter-witness, all three parsers ending the paragraph:

```
- > - first
  >   intro `a
  >     # h
  >     b` x
```

    cont = 2   (list_content_column('  intro `a') via the INDENT fallback)
    HEAD: ends — correct, and the clause is what makes it correct

`cont` is **2** and the clause is load-bearing, because the strip runs on a remainder from which the
quote marker has already been removed, so the 2 columns it removes are not the 2 columns
`BLANK_OR_BLOCK`'s cap would have covered. Mutating `if cont:` → `if cont >= 4:` keeps the suite at
**163/163** and adds **+24 LENIENT**. Direction of the false statement: it invites exactly that
narrowing. **Direction of the witness: LENIENT.**

**FAILS IF:** a shape with `cont < 4` changes verdict when the strip clause is skipped.

### M2 — "at top level `cont` is 0 and every clause here is a no-op" is false: this fold added 156 noisy shapes at top level, and the case written to deny it is vacuous

`scripts/check-withdrawal.py:551-555` claims the clause is a no-op at top level and that the grid is
unmoved. The grid is unmoved — its three leads are never indented, so it cannot express the
question. With a legal 1-3 space paragraph indent, r9's INDENT fallback returns that indent as a
content column:

| document | `cont` at r8 fold | `cont` at HEAD | parsers | HEAD |
|---|---|---|---|---|
| `   intro \`a\n    # h\n    b\` x` | 0 | **3** | continue | ends — **noisy** |
| `  intro \`a\n    # h\n    b\` x` | 0 | **2** | continue | ends — **noisy** |
| ` intro \`a\n    # h\n    b\` x` | 0 | **1** | continue | ends — **noisy** |

Measured: C5, **0 → 156 noisy** of 336. And the self-test negative written for precisely this
property is vacuous:

```
1487:  ("...and a 3-space-indented paragraph at TOP LEVEL gains no container, so a block start "
1488:   "needs the usual cap and this stays a genuine span — the clause must not turn a legal "
1489:   "paragraph indent into a list content column",
1490:   _marker_at("   the count was `wrong:\n       # h\n       holds 1,414 anchors today`"),
1491:   "was "),
```

It does gain a container — `cont = 3`. The case passes only because its block start is at column
**7**, four past the indent. At columns 4, 5 or 6 the same "legal paragraph indent" produces a
boundary, and the marker goes from `'was '` to `''`. **Direction: NOISY** — this is a dismissible
warning, not a hidden figure, which is why it is Medium and not High. What is wrong is the
*statement* and the *case*, in a file where those are the deliverable.

**FAILS IF:** `list_content_column` returns non-zero for a top-level paragraph line, while the
docstring says it returns 0.

### M3 — the live-impact claim is false as stated; its conclusion survives

The claim on record: *H1's fix changes no live verdict — both versions over all 1,804 tracked `.md`
files gave identical mask output, with a planted known-positive control.*

Measured, 1,805 tracked `.md` files at HEAD:

| comparison | files whose MASK differs | figures whose `history_marker` differs |
|---|---|---|
| `7d33721e`→`47e33e71` … (via `d6967caa`) | **5** (4 of them existed at `d6967caa`) | 3, all in `docs/reviews/codex/backlog-249-260-r9-codex.md`, which did not exist at `d6967caa` |
| `47e33e71` → HEAD+H1+H2 fixes | **3** | **0** |

176,155 figure occurrences scanned; three planted known positives (C1, C3, C2 shapes) confirmed to
flip, so a null result is not vacuous. Files whose mask changes across the fold:
`docs/reviews/claude/goal-page-mutations-r4-claude.md:143`,
`docs/reviews/spec-1f-a-codex-v3.md:2280`,
`docs/superpowers/plans/2026-06-09-html-doc-magazine-skim.md:581`,
`docs/superpowers/plans/2026-06-17-clickable-section-timestamps.md:714`.

So: **"identical mask output" is wrong on four pre-existing tracked files**; the stronger conclusion
it was offered as evidence for — no live verdict change — is **correct**, by a measurement the claim
did not make. ⚠ The same measurement is what caps the severity of H1-H4: **0 of 176,155 figures
change verdict under the fixes**, so those classes are latent in this repo today, not live.

**Direction: a provenance defect, not a guard direction.** A claim stated about the mask and true
only of the verdict is the shape `a-check-result-is-not-the-claim` names.

**FAILS IF:** the two versions' mask output differs on any tracked `.md` file.

### M4 — #269's corrected step count still comes from a line-shaped rule, and the 2 steps it drops include the gate the row itself calls load-bearing

`docs/backlog.md` #269, corrected this fold: *"Parsed as YAML — the authority — the `verify` job has
**69 steps: 66 with `run`, 3 unnamed `uses:` actions**, and **59** of the 66 are `python3 scripts/…`."*

Re-derived with a YAML parse of `.github/workflows/ci.yml`:

    verify: 69 steps; run:=66; unnamed uses:=3; python3 scripts/=61

69, 66 and 3 reproduce. **61, not 59.** The gap is exactly the two multi-line `run:` blocks whose
`python3 scripts/…` call is not the first line:

    - dashboard entry ratchet        printf … > /tmp/pr-body.md ⏎ python3 scripts/check-dashboard-entry.py …
    - check-review-recorded (PR only) printf … > /tmp/review-pr-body.md ⏎ python3 scripts/check-review-recorded.py …

The second is the **final-tree gate** — the one the row's own next sentence names as the thing a
blind sweep must not skip. The row corrected its step count by switching to YAML and left the
derived count on a first-line rule, so the correction reproduces the defect it was correcting, one
field over. **Direction: it UNDERSTATES the row's own cost figure by 2.**

**FAILS IF:** a `verify` step that runs `python3 scripts/…` anywhere in its `run:` block is not
counted in the 59.

### M5 — `LIST_MARKER`'s leading `[ \t]{0,3}` has no clean falsifier: the only shapes that distinguish it are ones the fold itself declared not a claim

`scripts/check-withdrawal.py:519`. Mutating `[ \t]{0,3}` → `[ \t]{0,0}` keeps the suite at
**163/163** and adds **+13 LENIENT** — but all 13 witnesses are `'\t- intro …'`, and a tab at column
0 is four columns of indent, so cmark renders the whole document as `<pre><code>` and the fold's own
case at `:1480-1486` records that such shapes pin behaviour and are **not** a claim that the answer
is right. I could not construct a witness outside that family: at a single list level the INDENT
fallback covers the loss, and a second marker after leading whitespace is swallowed by the greedy
`[ \t]+` of the first.

So the statement is neither pinned nor refutable with the instruments available. **Direction:
unfalsifiable** — reported as that rather than as a defect, because I did not establish that it is
wrong.

**FAILS IF:** a shape outside the indented-code family distinguishes `[ \t]{0,3}` from `[ \t]{0,0}`.

---

## Low

### L1 — the fold fixed one broken replay instrument by pinning its base revision and left its twin with the identical defect

`scratchpad/r8-verify/final_table.py:18-22` now pins `PRE_H1 = "d6967caa"` with a comment citing r9
Codex's CANNOT RUN. It runs, rc=0, and its table reproduces (see SOUND below).

`scratchpad/r9/fix_proto.py` has the same defect and still raises at HEAD:

    AssertionError: fn: 0 matches     (scratchpad/r9/fix_proto.py:62, from :65)

It patches the **working-tree tip** to synthesise the "before", and the tip now contains the fix — the
exact failure `final_table.py` was just repaired for. `fix_proto.py` is the only instrument that
generates the 294-shape corpus, so **the three figures the brief instructed me to re-derive with it
have no working replay path at HEAD.** Instance fixed, class not searched. **Direction: a
measurement-provenance defect** — #268's `FAILS IF` ("the note still cites a lenient/noisy count that
no committed script can reproduce") is **presently true**, and this fold added three more such
figures to the note it governs.

### L2 — `corpus_r8.py`, named by #268 as the replay path, still scores at the retired index

    /tmp/cmvenv/bin/python r7-claude/corpus_r8.py
    1620 shapes · noisy=108 · ok=1508 · parsers split=4

108 is the **superseded** noise figure — this generator still scores at `doc.index("\n")`, the
lenient-blind index that r9 Codex M2 and r8 Claude B1 both found. So of the two scratchpad
instruments #268 names as the replay path for the note's figures, one reproduces figures the note
has retired and the other raises. ⚠ #268 already says a committed generator "needs a case asserting
it reads the newline INSIDE the candidate span"; this is the measured evidence that the existing one
does not. **Direction: provenance.**

### L3 — `LIST_MARKER`'s greedy `[ \t]+` overstates the content column when ≥5 spaces follow a marker

CommonMark caps the spaces counted after a list marker at 4; with 5 or more the content column is
marker width + 1 and the item opens with an indented code block. `LIST_MARKER`'s `[ \t]+` is greedy,
so `-     ` reports column 7 where CommonMark says 2. Over-stating `cont` makes the strip condition
`c >= cont` fail on lines at the true column, which is the **LENIENT** direction. I could not build
a clean witness: every spelling I tried turns the item's own first line into an indented code block,
so there is no paragraph for the rule to be about and the oracle construction degenerates. Recorded
with its direction so the next round does not re-derive it, and **not** claimed as a live defect.

---

## Checked and found SOUND

- **Claim 2 — the direction claim holds.** 40,000 fuzz documents from a 15-token container alphabet,
  comparing round 8's fold against HEAD: **18 flips, every one `continues → ends` (noisy), zero in
  the lenient direction.** Structurally consistent: within the new block, the whitespace strip and
  the second `quote_depth` pass can only remove prefix characters, every `BLANK_OR_BLOCK` alternative
  but the blank one is prefixed by `[ \t]{0,3}`, the blank alternative survives stripping,
  `quote_depth` is idempotent on its own output, and the only `return` added is a `True`. ⚠ **Stated
  as a bound, not a proof**: 0 of 40,000 on this alphabet. C5's 156 shapes are the measured cost, and
  they are noisy.
- **Claim 3 — every figure in the measurement note reproduces under an independent oracle.**
  grid **1,620 shapes, 4 parser splits, 1,616 adjudicated, 0 LENIENT / 34 noisy**; list **196 / 0 /
  0**; new-class **294 / 3 / 0** with per-class `{tabbed 1, interleaved 2}`. The historical table at
  `:418-424` reproduces: `3b49db97` (r7 as shipped) = **228 / 88 / 316**. The `r8 (the list column
  alone) 170` row reproduces at **`7d33721e`** (`below-marker 130, tabbed 14, interleaved 26`) — ⚠ it
  is **209** at `d6967caa`, so a reader using this review's scope base gets a different number; the
  row's label is accurate and this is not a finding.
- **Claim 5 — the manifest is honest on every axis I could test.** `--binding` rc=0 (1,559 anchors
  across 1,551 entries, each resolving to one site); `scratchpad/r6/attrib.py` → 52 entries applied,
  0 problems; **all 9 entries new in this fold go red via the case they name** (I applied each edit
  to a staged copy of `scripts/` and matched the failing case against the entry's `expect`). The
  retargeted anchor the brief flagged, `col = _column(rest[i:m.end()], col)` → `…, 0)`, **does**
  break the property its name claims — restarting each marker's width at column 0 destroys the run's
  cumulative width (`- - - ` → 2 instead of 6) — and it fails via its named case
  (`:1440-1442`, 161/163). ⚠ The gap is in what the entries *cover*, not in their honesty: see H2 and
  H5 for two statements with green mutations.
- **Claim 6 — M2's correction is true, and the wrong reasoning is gone from both copies.** The
  corrected sentence at `:378-387` is sound, and its figure re-derives **exactly**: **14** r7 grid
  shapes whose genuine LENIENT result scores `ok` at `doc.index("\n")`, the first four being
  `'> intro\nlazy \`a\n~~~\nb\` x'`, its CRLF twin, and the ``` ``` ``` pair — the note's own example
  among them. `docs/backlog.md` #267 carries the corrected version, not the withdrawn one, and the
  falsification table at `:365-371` no longer asserts it.
- **The oracle.** Two independent checks. (1) **Span identity**: requiring the markdown-it halves to
  find the *planted* span rather than any span changes **0 of 2,446** verdicts, so the oracle
  construction is not being satisfied by an unrelated backtick pair. (2) The `<pre>` → `<pre\b[^>]*>`
  correction is real and necessary — **8 of 10** info-string fence shapes flip, because cmark-gfm
  renders ```` ```ruby ```` as `<pre lang="ruby">`, confirming r8 Claude M3 by measurement rather
  than by citation. ⚠ One residual oracle hazard I did **not** eliminate: a document whose middle is
  a literal `<code` HTML block would read as "has a span". No corpus here contains one.
- **`final_table.py` is NOT broken at this HEAD** — the brief says it is, and that is stale. It was
  repaired in this fold (`:18-22` pins `d6967caa`), exits 0, and prints the note's table verbatim.
- **#269's step counts 69 / 66 / 3** reproduce under a YAML parse (the 59 does not — M4).
- **Suites, all run as `python3.12`:** `check-withdrawal.py --self-test` **163/163**;
  `check-plan-code.py --self-test` **237/237**; `check-plan-code.py --binding` rc=0;
  `check-features.py` ok (26 nodes); `check-docs.py` "Documentation integrity OK";
  `check-selftest-counts.py` "55 scripts declare a count, every one verified by running it";
  `check-ratchet-contract.py --self-test` 56/56.
- **Tree discipline:** HEAD is `47e33e71a5d6eee16c4f1e2fb376247951c7503b` and `git status --short`
  shows only this file. Every mutation was applied to a `copytree` staging directory outside the
  repo; nothing in the worktree was edited.

---

## CANNOT RUN

⛔ **Each of these is a FAILURE, not a pass. Treat the named thing as NOT RUN.**

1. **`scratchpad/r9/fix_proto.py` — the re-derivation the brief instructed me to use for the
   new-class corpus — raises `AssertionError` at HEAD** (see L1). **Treat "re-derived with the
   fold's own instrument" as NOT RUN.** I substituted an independent generator that takes both
   versions from `git show <rev>:scripts/check-withdrawal.py` rather than patching the tip, and the
   figures reproduce (Claim 3, above) — so the *figures* are verified, but not by the instrument on
   record, and the instrument on record is still broken.
2. **`python3 scripts/check-plan-code.py --mutate .` was not run.** Local shards are recorded in this
   project's memory as timing out, and a timed-out sweep is NOT MEASURED. **Treat the full mutation
   sweep as NOT RUN.** What I ran instead is a per-entry equivalent for the 9 entries new in this
   fold — each edit applied to a staged copy, self-test executed, failing case matched against the
   entry's `expect` — which covers attribution for the new entries and says nothing about the other
   43 or about the control being green first.
3. **The integration and e2e suites were not run** (they need a live Supabase stack). Out of this
   review's scope, recorded so the gate is not read as having passed.
4. **No claim is established about whether C3 or C4 can be closed without a block-structure stack.**
   I measured that neither of my two fixes touches them and that a scalar `cont` cannot express C3;
   I did **not** build and measure a stack-based variant. The cost of closing them is **NOT
   MEASURED**, and #267's two options are unaffected by this review.

---

## Instruments

All outside the repo, under
`…/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/r9-claude/`:

| file | what it does |
|---|---|
| `oracle2.py` | fresh two-parser oracle: `<pre\b[^>]*>`, plus a span-identity mode |
| `load.py` | loads a module from `git show <rev>:…` — never patches the working tree |
| `corpora.py` | the note's three corpora reproduced verbatim, plus C1-C5 |
| `measure.py`, `final.py` | the consolidated L/N table |
| `fixes.py`, `fixes2.py`, `verify_fixes.py`, `verify2.py` | the two repairs, prototyped on copies |
| `stage.py` | `copytree` a staged `scripts/` outside the repo so a mutant's self-test can run |
| `hunt.py`, `wit.py` | the Claim 4 mutation hunt and its witnesses |
| `attrib9.py` | per-entry attribution for the 9 new manifest entries |
| `live.py`, `live2.py`, `live3.py` | mask-level and verdict-level live impact over 1,805 tracked files |
| `probe1-11.py`, `sweep.py`, `sweep2.py` | root-cause traces, the 11,052-shape sweep, boundary pinning |

Oracle environment: `/tmp/cmvenv` (`cmarkgfm`, `markdown-it-py`, `pyyaml`); GFM dialect
`MarkdownIt("gfm-like").disable("linkify")`. Gates run as `/usr/local/bin/python3.12` (3.12.9).

---

## Verdict

| CHECK | RESULT |
|---|---|
| Claim 1 — the list-container fix is now correct | ⛔ **REFUTED** — four LENIENT classes, 1,199 of 3,902 shapes (B1, H1-H4) |
| Claim 2 — every clause this fold added is noisy-or-neutral | ✅ **HOLDS** — 0 lenient-direction flips in 40,000 fuzz docs; cost is C5's 156 noisy |
| Claim 3 — the measurement note's figures | ✅ **REPRODUCE** under an independent oracle, to the unit |
| Claim 4 — the 163 cases are load-bearing | ⛔ **REFUTED** — 4 green mutations, 3 of them lenient (H2, H5, M1, M5) |
| Claim 5 — the mutation manifest is honest | ✅ **HOLDS** — 9/9 new entries red via their named case; the retarget is sound |
| Claim 6 — M2's correction is now right | ✅ **HOLDS** — the sentence is true and its 14 shapes re-derive |
| "H1's fix changes no live verdict" | ⚠ **CONCLUSION HOLDS, EVIDENCE DOES NOT** — 4 pre-existing files change mask; 0 of 176,155 figures change verdict (M3) |
| #267's own FAILS IF | ⛔ **FIRED AGAIN** — a sixth consecutive round; and H2 + M2 are defects *inside* previous fixes, making three consecutive rounds of that shape |
| #268's own FAILS IF | ⛔ **PRESENTLY TRUE** — three new unreplayable figures, and the only generator for them raises at HEAD (L1, L2) |
| #269's corrected count | ⚠ 69/66/3 reproduce; **59 measures 61** (M4) |
| Suites at HEAD | ✅ 163/163 · 237/237 · binding · features · docs · selftest-counts · ratchet 56/56 |
| Full mutation sweep, `fix_proto.py` replay, integration/e2e | ⛔ **NOT RUN** — see CANNOT RUN |
| Convergence | **0 of 2.** Not clean: 1 Blocking, 5 High |
| Merge | **NOT RECOMMENDED HERE — it is the human's gate and has not been given** |

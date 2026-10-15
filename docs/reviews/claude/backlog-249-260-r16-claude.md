# Round 16 — Claude half, adversarial

**Subject:** `e3a61e93` (the round-16 fold) on `backlog-249-260-fixes`, PR #371.
**Folds:** `docs/reviews/codex/backlog-249-260-r16-codex.md` (0 Blocking / 2 High / 2 Medium).
**Wider diff read:** `2c33738c..e3a61e93`. **Round 15 read:** both halves.

**0 Blocking / 3 High / 3 Medium / 1 Low.** ⛔ **NOT CONVERGED.**

⛔ **Thrashing discipline.** This component is armed. Every finding below asks for a **DELETION** or
a **narrowing** except H1, which adds a falsifier and nothing else — and H1 adds no description of
the child's stream, so it is not a seventh wording. Where a narrowing could be read as a seventh
wording (H2), the primary remedy offered is the deletion and that is said explicitly.

---

## Blocking

None.

---

## High

### H1 — ⛔⛔ THE NARRATION WAS DELETED; THE UNCOVERAGE WAS NOT. ALL SIX REFUTED CLAIMS CAN RETURN, **AND NOW THE DISCLAIMER CAN GO WITH THEM**, AT 296/296 GREEN.

`scripts/check-plan-code.py:3081-3091` is the `elif heads:` branch. Round 15's Claude half filed
that the surviving sentence had **no falsifier in either direction**. Round 16 agreed with the
reviewer that the r15 case policed a PHRASE and not a CLAIM, retired it, and deleted the narration.
⛔ **The deletion removed the claim. It did not remove the hole — it enlarged it**, because the
disclaimer that is now the *only* thing standing between a reader and the six refuted wordings is
itself asserted by nothing.

**Measured, at `e3a61e93`, green control first:**

| step | result |
|---|---|
| control, unmodified tree | **296/296 passed** (rc=0) |
| `:3081-3091` — the whole `said = (...)`, **sentence and disclaimer**, replaced by the refuted claims, `" · ".join(heads)` kept | **296/296 passed** (rc=0) |
| restore | **296/296 passed** (rc=0) |

The replacement text was `"CPython SAID THE FOLLOWING KILLED THE CHILD, at column zero after a block
it labelled, in reverse order, each one a VALIDATED exception class — "` — i.e. wording #1 (false
attribution), #5 (column zero), plus reversed order and the `is_exception_heading` claim #280 was
filed to delete — and **the disclaimer deleted entirely**. I then drove the suite's own `_q`
shutdown fixture through `run_mutations` and read the RENDERED report, so this is not a reasoning
about the parser:

```
⚠ WHAT THE CHILD ITSELF SAID — CPython SAID THE FOLLOWING KILLED THE CHILD, at column zero
after a block it labelled, in reverse order, each one a VALIDATED exception class —
RuntimeError: FIRST_KILLER · ValueError: SHUTDOWN_SECOND:
```

**Concrete failure scenario.** A future round folds a finding anywhere in `run_mutations`, a regex
or a mechanical rewrite touches this `said = (...)` block (one already rewrote a historical comment
into a falsehood on this branch — r15 Claude M), and the report ships asserting that CPython named
the killer. Every guard stays green; `--self-test`, `--binding` and `--mutate .` all pass. The
reader is then told, by the harness, the exact thing six rounds established it cannot know.

**What IS covered here, measured, so the gap is bounded and not overstated:** the join separator
(`:3931`, mutation manifest entry at 0-based 721) and the ORDER of two heads in the rendered report
(`:3951`, which reads `r.index("FIRST_KILLER") < r.index("SHUTDOWN_SECOND")` and does observe a
reversal, because `said` precedes `diagnostic_tail` in the same string). **Nothing reads the prose,
and nothing reads the disclaimer.**

⛔ **WHY THIS IS NOT A SEVENTH WORDING, AND WHY H2'S OWN ARGUMENT DOES NOT RETIRE IT.** The fold's
H2 is right that *a case that asserts a PHRASE cannot police a CLAIM* — for an **assertion**, whose
truth depends on the world. A **disclaimer** is not an assertion; it is a refusal, and its
correctness **is** its presence. "The report refuses to claim causation" is falsified exactly by the
refusal's absence. So the shape H2 retired is the wrong shape for the sentence it was pointed at and
the **right** shape for the four refusals at `:3087-3091`. Apply H2's reasoning to the assertion and
the opposite conclusion to the refusal; the fold applied one of those and skipped the other.

**Remedy — adds no description of the stream.** One case asserting the rendered report still
REFUSES: a child-unproducible token per refusal (exception-hood, causation, CPython authorship,
stream position), and a mutation entry per refusal. Four entries, zero new prose about where the
lines sat.

---

### H2 — ⛔ THE DOCSTRING SUMMARY M1 REWROTE IS **NEWLY FALSE, IN TWO INDEPENDENT WAYS**, AND THE HARNESS'S OWN COMMITTED CASE REFUTES IT. THIS IS THE SEVENTH VERSION OF THE SAME MISTAKE.

`scripts/check-plan-code.py:567`:

```python
"""Every line `stderr` printed immediately AFTER a run of indented lines, in order. PURE.
```

The predecessor (`2c33738c:567`) read *"Every line `stderr` printed at COLUMN ZERO after a frame
block, in order."* M1 removed the false positional clause **and removed a TRUE one with it**, then
added a new false word. Measured, both directions, against the shipped function:

| witness | returns | the summary predicts |
|---|---|---|
| `'  connecting\nREADY\n'` — a run of indented lines, no frame marker | `[]` | `['READY']` ⛔ FALSE |
| `'  File "f"\n\n\n\nEND\n'` — three blank lines between the run and the line | `['END']` | nothing "immediately after" ⛔ FALSE |

⛔ **The first direction is refuted by this file's own committed case**, so the summary now
contradicts the suite that ships beside it — `:4273`, over a **real child**:

```python
_prog = _child_stderr('import sys\nsys.stderr.write("  connecting\\nREADY\\n")\n')
case("⭐ r12 H1: indented output with NO `File \"` line names nothing",
     lines_after_frame_runs(_prog), [])
```

The frame-marker requirement is the r12 Codex H1 fix — the clause whose absence made *"one raised
exception reported as TWO"*. The summary line now states the predecessor's defective rule as the
function's contract. The second direction ("immediately") is falsified by the run loop at `:638`,
which consumes `not lines[i].strip() or lines[i].startswith((" ", "\t"))` — blanks included.

**Concrete failure scenario.** A later round reads the summary, concludes the frame-marker clause is
not part of the contract (the summary says every line after *any* indented run), and reinstates the
predecessor's behaviour or writes a mutation that encodes it. That clause is exactly what the
`ExceptionGroup` bound rests on (`:664`), so the bound goes with it.

⛔ **REMEDY — DELETE, do not reword.** The exact rule already exists in **two** other places (the
`FRAME_LINE` comment at `:546-556` and the implementation comment at `:666-674`); the summary is a
third copy and the third copy is the one that drifted. Primary remedy:

```python
"""Lines quoted from `stderr` by the run rule implemented below, in stream order. PURE.
```

⚠ A variant that states the rule exactly (*"every line that ENDS a run of blank-or-indented lines
carrying at least one `FRAME_LINE`"*) **is a seventh structural wording of this stream** and the
arming applies to it. I am not proposing it. The deletion is proposed because this site has now
produced a false structural sentence in two consecutive rounds, and the rule is already stated
twice elsewhere.

---

### H3 — ⛔ THE SIXTH "COLUMN ZERO" SITE IS THE **ONLY READER-FACING ONE**, M1'S ENUMERATION MISSES IT, AND THIS ROUND HAS NOW **PINNED** IT WITH THE PRESENCE-ONLY SHAPE IT RETIRED NEXT DOOR.

`scripts/check-plan-code.py:3090` — the `else:` arm, three lines below the branch H1 rewrote:

```python
said = ("stderr printed no line at column zero after a frame block, so read the "
        "window — ⚠ and note a traceback with NO frames (for example "
        "under `sys.tracebacklimit = 0`) also lands here")
```

M1 enumerates and corrects *"the docstring opening, the heading definition at `:615` and the
implementation comment"* and the function's name. The complete live population, measured:

```
$ grep -rn -i "column zero" scripts/
:569 :572 :622 :672     r16 M1's own withdrawal notes (correct)
:3075                   the H1 note listing the six wordings (correct)
:3090                   ⛔ A RENDERED REPORT STRING — not corrected, not enumerated
:3893 :3920 :3931       cases and a case NAME that assert it
:4176 :4245 :4295       comments
scripts/mutations/check-plan-code.json:1730 :1747 :1751   entry names and an ANCHOR
```

Four comment/docstring sites were corrected. The one site a **reader of a failing CI job actually
sees** was not, and it carries the refuted wording #5 (*"at column zero after an indented run"*)
near-verbatim.

⚠ **Stated rather than hidden: I did NOT establish that this sentence is false.** I tried. Under the
harness's own definitions the negative direction is unreachable — if a `FRAME_LINE` run is followed
by any non-blank line that does not start `" "`/`"\t"`, that line is reported, so `heads == []`
cannot coexist with such a line; and a real `ExceptionGroup` stderr has **no** unindented line at all
(measured: all six lines indented). The sentence is therefore defensible **only** under the reading
*"column zero" ≡ "ends the blank-or-indented run"* — which is precisely the reading this same commit
declared false at four other sites in the same function. A vocabulary that is false in four places
and load-bearing in a fifth is not a wording preference; it is the class M1 claims to have closed.

⛔ **And this round made it harder to remove, which is the structural half.** The phrase is now
*defended*: the case at `:3892`

```python
case("the no-lines world is named as well, in the redesigned wording",
     any("printed no line at column zero after a frame block" in r for r in _repw3), True)
```

and the manifest entry whose anchor is the literal (`scripts/mutations/check-plan-code.json:1751`).
That is a case asserting the **PRESENCE OF A REFUTED PHRASE** — the exact shape H2 retired for the
sibling branch, in the same commit, three source lines away. Correcting `:3090` now requires editing
a committed case and re-anchoring a manifest entry.

**Concrete failure scenario.** Round 17 or a later fold tries to finish the "column zero" sweep,
`--self-test` goes red at `:3892` and `--binding` reports an orphan, and the cheapest route back to
green is to leave the refuted wording in the report — which is how it survived this round.

**Remedy — the cheapest correct one, and it says LESS.** `:3090` → *"stderr printed no line that
ends a run of frame-marked indented lines, so read the window — ⚠ a traceback with NO frames (for
example under `sys.tracebacklimit = 0`), and an `ExceptionGroup`, also land here"*; retarget `:3892`
and the manifest anchor in the same edit. Alternatively, and more in the spirit of H1: delete the
structural half here too and say only *"this harness read no line it could quote, so read the
window"*, retiring `:3893`'s `sys.tracebacklimit` assertion with it.

---

## Medium

### M1 — ⛔ `:615`'S HEADING DEFINITION IS NOT CORRECTED; A MECHANICAL SUBSTITUTION **DESTROYED IT**. THE DEFINITION IS NOW ABSENT.

`scripts/check-plan-code.py:620-621`:

```
suite, returned None exactly where it was needed. A heading is instead *the first line back at
the first line BACK OUT of a run of indented frame lines*, which holds with or without a header
```

At `2c33738c:615` this read *"A heading is instead \*the first line back at column zero after a run
of indented frame lines\*"*. The edit replaced `column zero after` with `the first line BACK OUT of`
and **left the original subject standing**, yielding *"the first line back at the first line BACK
OUT of a run"* — a duplicated subject that defines nothing. The site's job is to state the rule that
replaces the `_TB_HEADER` literal; after this edit it does not state a rule at all.

This is the same instrument failure as r15 Claude M on this very branch (a regex rewrote a
historical comment into a falsehood), in the same function, one round later.

**Concrete failure scenario.** The only two remaining prose statements of the heading rule are this
one and `:567`, and H2 shows `:567` now states the *predecessor's* rule. A reader who needs the
contract has one broken sentence and one false one.

**Remedy:** `A heading is instead *the first line that ENDS a run of indented frame lines*, which
holds with or without a header`.

---

### M2 — ⭐ THE ONE RESIDUAL CLAIM THE DISCLAIMER DOES NOT COVER: **"THE CHILD PRINTED THEM"** — AND TEXT-MODE NEWLINE TRANSLATION FALSIFIES IT. CODEX NAMED THIS AND THE FOLD DID NOT ADDRESS IT.

Mandate item 2, answered. The disclaimer at `:3087-3091` refuses: exception-hood, causation, CPython
authorship, and *anything about where in the stream they appeared*. The surrounding
`report.append(...)` at `:3093-3107` makes no positional claim (read in full). **One claim survives
undisclaimed:** `:3081` says *"stderr printed these lines, in the order **the child printed them**"*
— an assertion about the child's writes, not about the decoded stream.

`run_suite` reads the child at `:716-717` with `text=True` and no `newline=`, i.e. **universal
newlines**, so every `\r` and `\r\n` becomes `\n` before `lines_after_frame_runs` ever sees it.
Measured with a real child:

```
child wrote (bytes) : b'  File "f", line 1\rKILLED: overwritten\n'
child's LINES        : [b'  File "f", line 1\rKILLED: overwritten']        <- ONE line
harness sees         : '  File "f", line 1\nKILLED: overwritten\n'          <- TWO lines
heads                : ['KILLED: overwritten']
```

The report then tells the reader that `stderr` printed the line `KILLED: overwritten` *in the order
the child printed them*. The child printed no such line; it printed one line containing a carriage
return, which a terminal renders as `KILLED: overwritten` **overwriting** the fragment the harness
silently consumed as a frame. The line-splitting is the harness's decoder's, attributed to the
child.

Codex's r16 review states this directly — *"`\r`/CRLF are normalised by subprocess decoding before
extraction, so the report narrates the normalised stream, not what the child wrote"* — and the fold
deleted four other clauses while retaining this one.

⚠ **The order clause itself is sound** and I am not filing it; see *Checked and found SOUND*. The
defect is the attribution to **the child**.

**Remedy — a two-word narrowing, strictly less claim and no new structural description:** *"in the
order they appear in stderr as this harness decoded it"*, or simply *"in stream order"*.

---

### M3 — ⛔ "THE SINGLE TEXTUAL OCCURRENCE LEFT IS THIS COMMIT'S OWN ACCOUNT OF THE RENAME" IS **FALSE ABOUT THE REPO**. TWO LIVING, PAGE-GENERATING DOCUMENTS STILL NAME THE DEAD SYMBOL AS THE CURRENT ONE.

The commit's M1 says: *"AST-verified: `column_zero_after_frames` is no longer a live identifier; the
single textual occurrence left is this commit's own account of the rename."* That is true of
`scripts/check-plan-code.py` and false of the repository. Measured:

```
docs/roadmap-to-launch.md:3085  * `exception_headings` is renamed **`column_zero_after_frames`**,
                                  because the old name was itself the claim.
docs/backlog.md:294             (×2, inside row #279)
docs/backlog.md:295             (row #280)
docs/reviews/claude/...r14,r15  (frozen testimony — correctly left alone)
```

`docs/roadmap-to-launch.md:3085` asserts, **in the present tense, in a living document**, that the
function *is* named `column_zero_after_frames` — and does so in a sentence whose own point is *"the
old name was itself the claim"*, which is now true of the name it names. `docs/backlog.md` is the
input to `gen-backlog-page.py`, so both are reader-facing surfaces, not history.

⚠ `scripts/check-withdrawal.py` is **not** the guard for this: it reports *"5 figure(s) corrected"*
(rc=0) — it polices withdrawn FIGURES, not withdrawn symbols. Nothing mechanical sees this class,
which is why the M1 sweep's AST verification over one file read as a repo-wide closure.

**Concrete failure scenario.** A future round greps for the heading rule by the name the roadmap
gives, finds nothing in `scripts/`, and concludes the function was deleted rather than renamed —
the same confusion M1 was filed to end.

**Remedy:** correct `docs/roadmap-to-launch.md:3085` to the live name and note the second rename;
correct the two backlog rows. Leave the review docs alone.

---

## Low

### L1 — THE #270 ROW'S ⭐-EMPHASISED PRESENT-TENSE ENTRY COUNT WAS MOVED **BY THIS FOLD**, FROM 19 TO 18, AND IS UNCHANGED.

`docs/backlog.md:285` still carries *"⭐ **But shard 7 carries the SAME 19 `check-plan-code` entries
and passed**"*. Measured both sides of the fold, with the real manifest ordering
(`sorted(glob("*.json"))`, `muts[index-1::total]`):

| tree | shard 7/8 | shard 8/8 |
|---|---|---|
| `2c33738c` (1547 entries) | **19** | 18 |
| `e3a61e93` (1546 entries) | **18** | 18 |

Deleting the r15 falsifier took that count to 18. The row states 19 in the present tense, with a ⭐,
ahead of its own four-clause withdrawal. Low rather than Medium because the sentence is already
withdrawn and the number is load-bearing for nothing — but the fold changed it and the fold edits
this row.

---

## Checked and found SOUND

- ⭐⭐ **The ORDER clause** (`:3081`, "in the order … printed them"). `lines_after_frame_runs` is a
  single forward pass over one string, so its output order is the stream's byte order; only `stderr`
  is read (`:3058`, `heads = lines_after_frame_runs(se)`), so interleaved stdout cannot reach it, and
  split writes to one fd append in order. Covered live: `:3951` reads the rendered report for
  `r.index("FIRST_KILLER") < r.index("SHUTDOWN_SECOND")`, and because `said` precedes
  `diagnostic_tail` in the same string a reversal moves the first occurrence and reddens the case.
  *(The attribution to **the child** is M2; the ORDER itself holds.)*
- ⭐ **The STRIP clause** ("each STRIPPED of surrounding whitespace"), measured over nine classes
  against a frame run: `　` lead → `END`; `\xa0` → `END`; `\x0b` → `END`; `\x0c` → `END`;
  `\x1c` → `END`; trailing `"  \t\xa0"` → `END`; a line whose content is entirely strippable → not
  reported at all (`:675`, `lines[i].strip()` guard); **BOM `﻿` → `'﻿END'`** and **NUL
  `\x00` → `'\x00END'`**, both RETAINED, which is correct because neither is `str.isspace()` and so
  neither is "whitespace". No `\r` can survive to be stripped (M2's normalisation). The clause is
  exact.
- **The six-wordings table and the `['END']` witness.** `lines_after_frame_runs('  File "f"\n　\nEND\n')`
  → `['END']` — reproduced. The `　` line is consumed by the run loop (`not lines[i].strip()`)
  and never quoted, so wording #6 is false in both directions as the table states.
- **The counts, in both directions.** Manifest entries for `check-plan-code.json`: **145 → 144**
  (`git show 2c33738c:` → 145; HEAD → 144). `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` =
  **144**; `sum(EXPECTED_MUTATIONS.values())` = **1546**; actual entries across
  `scripts/mutations/*.json` = **1546** across **62** files, and `EXPECTED_MUTATIONS` has **62**
  keys — so neither direction has an unmatched file. Cases **297 → 296**: the diff deletes exactly
  one `case(...)` call and adds none, and the control is 296/296.
- **`--binding`, 0 unbound:** *"binding OK — 1554 anchor(s) across 1546 entries each resolve to
  exactly one site; 67 expect(s) name no whole literal but ARE explained by one"* (rc=0). The
  deleted sentence orphaned nothing.
- ⭐ **The rename orphaned no anchor, verified independently of the commit.** `git show
  2c33738c:scripts/mutations/*.json | grep -c column_zero_after_frames` → **0** for every one of the
  62 manifests. Old-file references to the old name: **33** (matches). New-file references to the new
  name: **34** = 33 renamed + 1 fresh mention in the r16 M1 note.
- ⭐ **The new NAME is not itself a false claim** — asked directly, per mandate item 4. The function
  returns the line that ENDS a run of blank-or-indented lines containing ≥1 `FRAME_LINE`; the name
  claims position-nothing, and "after" (unlike the docstring's "immediately after") is true across
  intervening blanks. Its only looseness is "frame runs" for *a run containing at least one frame
  line* — ⛔ **and I am NOT proposing a rename.** Six positional claims about this stream have been
  refuted; a seventh identifier is the move the arming exists to stop, and the implementation comment
  at `:666-674` already says *"A RUN OF INDENTED LINES IS NOT A FRAME BLOCK"* in the one place the
  distinction matters.
- **Both retargeted siblings, re-derived zero-based and re-run.** `shard_slice` is
  `muts[index-1::total]` with `--shard0` adding 1, so `--shard0 N/1546` is 0-based global entry `N`
  over `sorted(glob("*.json"))` order. Entry **720** = `return out` → `return out[-1:]`, expect *"a
  raise-from chain names BOTH blocks, in the order the child printed them"* — that case asserts a
  two-element list, so `out[-1:]` is observable. Entry **721** = `" · ".join(heads)` →
  `"".join(heads)`, expect *"the report QUOTES the child's column-zero lines, joined"* — asserts the
  SEPARATOR, which raw stderr carried into the same string cannot supply. Both run:
  `1 file(s), 1 mutation(s), 1 killed, 1 attributed to the case each names, 0 survivor(s)` (24.5s
  and 25.7s). ⚠ Entry 721's name and its expect case name both still say "column zero" — that is
  H3's population, not a separate finding.
- **#270's M2 fix is sound and UNDIAGNOSED is still honest.** Read the row from the top
  (`docs/backlog.md:285`). The deleted clause (*"the second green carried one more mutation entry …
  counts against the load story"*) survives only inside the r16 M2 withdrawal note that quotes it;
  no live sentence draws a conclusion from an entry count. The surviving entry-count OBSERVATION
  (shard 7's count) is immediately followed by its own explicit withdrawal citing `ci.yml:674-675`.
  UNDIAGNOSED is asserted three times and nothing in the row contradicts it. The stale **19** is L1.
- **The 21-invocation guard set, re-run exactly as the commit declares it** — see *Instruments*.
  **20 green / 1 red**, the red being `check-review-rounds` at rc=1 printing *"backlog-249-260 round
  16: only codex — claude neither ran nor recorded a `REVIEW GAP:` line"*. Reproduced.

---

## CANNOT RUN

⛔ Each of these is a FAILURE, not a pass.

1. **The commit's `297/297` "phrase retained" figure is NOT independently reproduced.** It needs the
   `2c33738c` script *and* its manifest inside a complete `HARNESS_TREE` (`scripts`, `supabase`,
   `docs`, `node_modules`). Running `2c33738c:scripts/check-plan-code.py` against the HEAD manifests
   gives **296/297** — one red case, `"...and the entry count they yield is the pinned sum, not a
   typed literal: got 1546 want 1547"` — a cross-tree artifact, i.e. a **RED CONTROL**, so that run
   measures nothing and is not reported as a result. ⚠ The *conclusion* the figure supports is
   established by a stronger instrument anyway: H1's sever at HEAD, over a green control, leaves the
   suite green with the sentence **and the disclaimer** replaced.
2. **A full local `--mutate .`** was not run. Two single-entry shards were (above). A full sweep is a
   CANNOT RUN here, not a slow pass.
3. **The 4s→6s figure under its original conditions** — the commit declares this NOT RUN and I did
   not run it either.
4. ⚠ **`scripts/check-memory-link.py` exits 0 while printing *"WARNING: the harness memory path does
   not exist, so the assistant reads NO corpus here."*** In this worktree it cannot reach its
   subject, so its green is uninformative — treat it as NOT RUN. This is a property of the review
   worktree, not of the tree under review, and it is not filed as a finding; it is recorded so the
   20-green figure is not read as 20 measurements.

**Not filed, per the mandate's known-true list:** `check-review-recorded` red at `e3a61e93` by
design; `check-review-rounds` red for this half's absence; #270 UNDIAGNOSED; #272/#275/#276/#277/#278
filed and deliberately unfixed; nothing merged.

---

## Instruments

**Worktree:** `…/fdb027d3-…/scratchpad/wt-backlog`, HEAD `e3a61e93`, clean before and after.
**Interpreter:** the prepared venv, `./.venv/bin/python` → Python 3.12.9, `.venv/bin` first on `PATH`
for the mutation runs. All guards run with **stdin closed** (`</dev/null`).

**The invocation set, named in full (not "N of N"):**

```
scripts/check-plan-code.py --self-test          rc=0  296/296 passed
scripts/check-plan-code.py --binding            rc=0  1554 anchors / 1546 entries, 0 unbound
scripts/check-docs.py                           rc=0
scripts/check-anchors.py                        rc=0
scripts/check-anchors.py --self-test            rc=0  15/15
scripts/check-arch-findings.py                  rc=0
scripts/check-backlog-closure.py                rc=0  (WARN-only by #56)
scripts/check-explainer-delivery.py             rc=0
scripts/check-features.py                       rc=0
scripts/check-gate-falsifiability.py            rc=0
scripts/check-main-drivable.py                  rc=0
scripts/check-memory-link.py                    rc=0  ⚠ CANNOT RUN — see above
scripts/check-plan-file-tags.py                 rc=0
scripts/check-producer-enumeration.py           rc=0
scripts/check-python-pin.py                     rc=0
scripts/check-ratchet-contract.py               rc=0
scripts/check-rc-contract.py                    rc=0
scripts/check-review-rounds.py                  rc=1  ⛔ round 16: only codex (known-true)
scripts/check-roadmap-consistency.py            rc=0
scripts/check-selftest-counts.py --self-test    rc=0  18/18
scripts/check-surface-recall.py                 rc=0
scripts/check-withdrawal.py                     rc=0  (run for M3; not in the commit's set)
scripts/check-plan-code.py --mutate . --shard0 720/1546   rc=0  1 killed / 1 attributed / 0 surv
scripts/check-plan-code.py --mutate . --shard0 721/1546   rc=0  1 killed / 1 attributed / 0 surv
```

**Direct probes.** `lines_after_frame_runs` loaded by `importlib` from the delivered file (registered
in `sys.modules` first — a bare `spec_from_file_location` + `exec_module` raises inside
`dataclasses` at `:421` and is not a finding about the file) and driven over 13 hand-built streams
plus `str.isspace()` for 9 characters. `run_mutations` driven over the suite's own `_q` shutdown
fixture to read the RENDERED report, both for H1's sever and for the control. Real children spawned
via `subprocess.run(..., text=True)` and `capture_output=True` without `text` side by side, for M2's
byte-level witness. Manifest order and shard arithmetic re-derived in Python from
`sorted(Path('scripts/mutations').glob('*.json'))` and `muts[index-1::total]`, not read from the
commit.

**Controls.** A green control (296/296) was proved immediately before and immediately after H1's
sever, and before each shard run (`[1/1] control` then `[1/1] re-control`, both reported by the
harness). ⚠ Per the mandate: a parse check was NOT accepted as a correctness control anywhere — every
claim about behaviour above comes from running the function or the rendered report, not from reading
the code. No finding below Low rests on a single observation.

**Discipline.** Nothing was committed, pushed or merged. `scripts/check-plan-code.py` was modified
for H1's sever and restored with `git checkout --`; `git status --porcelain` is clean apart from this
review file. No `git` command was run in `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`.

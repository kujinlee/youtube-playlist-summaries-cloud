# Round 14 — Claude half, adversarial. Subject: the round-14 FOLD at `9232cbd9`

Reviewed committed HEAD **`9232cbd9`**; parent `c5660227`; the redesign `ab53945a`; the Codex half it
folds, `docs/reviews/codex/backlog-249-260-r14-codex.md`. Worktree clean before and after (one file
was severed for a falsifier test and restored byte-for-byte; `git status --porcelain` empty, verified).

**Counts: 0 Blocking · 1 High · 3 Medium · 3 Low.**

The single most important finding is **H1**: the replacement for the withdrawn CPython attribution is
**false in 100% of the cases it is printed** — 0 accurate out of 3,720 emissions, exhaustively
measured — and the harness's own flagship fixture prints the refutation three lines beneath the
claim. This is the sixth wording of this sentence and the fifth refutation, and the error changed
kind: rounds 11–13 refuted claims about what a line MEANS; this one is false about **where the line
was printed**, which is the one category the #280 redesign reserved for itself.

---

## Blocking

**None established**, and I want to be explicit about why, because H1 is the strongest finding I
have and an earlier draft of this document filed it here.

Nothing in this fold miscomputes a verdict. The mutation harness kills, attributes and counts
exactly as claimed — I re-ran all of it (see SOUND). What is wrong is what the harness **tells a
reader** about a stream it quotes, and what the repository record claims about that. That is a High,
not a Blocking, and grading it Blocking because the sentence has now failed six times running would
be severity standing in for exasperation. The thing that would make it Blocking — a reader acting on
the false annotation and reaching a wrong conclusion about a real kill — is reachable but was not
witnessed by me in any real sweep, and I say so in CANNOT RUN rather than implying it.

---

## High

**H1 — "its own preceding line began 'Exception ignored in'" is NEVER true. 0 of 3,720 emissions,
exhaustively measured, and the distance is unbounded.**

⛔ Read with M1: between them these are **two of the three positional claims the message makes**, and
the committed record asserts in three places that the positional claims were checked and hold — the
commit message ("the message no longer attributes anything to CPython. It says the line's *own
preceding line began …*"), and `docs/backlog.md:294`, `:295` and `scripts/check-plan-code.py:4194`
("the caller claims only that the child printed those lines at column zero after a frame block —
**which it did**"). ⛔ Neither finding asks for a seventh predicate; both ask for a claim to be
deleted or replaced by the fact the code actually computes.

`scripts/check-plan-code.py:3031-3032`:

```python
                            h + (" [its own preceding line began 'Exception ignored in',"
                                 " which the CHILD wrote]" if ig else "")
```

The boolean rendered there is produced at `:648`:

```python
            out.append((lines[i].strip(), intro.startswith(IGNORED_AT_SHUTDOWN)))
```

and `intro` is computed at `:623-630`, **before the frame block is consumed**:

```python
        # A run of indented lines is a frame block. Decide what INTRODUCED it before consuming
        # it: the nearest preceding non-blank line, looking PAST a bare traceback header, which
        # is what sits between `Exception ignored in:` and its frames.
        intro = ""
        for k in range(i - 1, -1, -1):
            if lines[k].strip() and lines[k].strip() != _TB_HEADER:
                intro = lines[k].strip()
                break
```

`intro` is therefore the line preceding **the frame block**, which the code's own comment says
plainly ("Decide what INTRODUCED **it**"). The line the annotation is attached to is a different
line: `lines[i]` *after* the run loop at `:645`. So `lines[i-1]` is always a member of the consumed
run — indented, or blank — and `intro` sits at index ≤ `i-2`. **The reported line's own preceding
line is structurally never the `intro` line.**

*Measured, not argued.* I transcribed the function to yield the index of each reported line, verified
the transcription agrees with the real function on every input (0 mismatches), and ran it over every
five-line stream built from a 9-element alphabet of real CPython line shapes (`Exception ignored in:
<f>`, the traceback header, space- and tab-indented `File "…"` lines, a frame body, empty, whitespace-
only, two headings) — 59,049 streams:

```
annotations emitted (ig=True): 3,720
the message's literal claim held:     0
distance from the reported line back to the label line:
    2 lines -> 1,944    3 lines -> 1,296    4 lines -> 480      1 line -> 0
```

The canonical CPython shutdown stream, by hand:

```
Exception ignored in: <function f at 0x1>        <- the label
Traceback (most recent call last):
  File "x.py", line 3, in f
    raise ValueError("SHUTDOWN")                 <- the reported line's ACTUAL preceding line
ValueError: SHUTDOWN                             <- the reported line, annotated
```

**And the distance is unbounded**, because `:627-630` looks past every blank line and every
`_TB_HEADER` it meets, not just one. Measured, real call:

```python
se = "Exception ignored in: <f>\n" + ("\n" + _TB_HEADER + "\n") * 20 \
     + '  File "x.py", line 1, in f\n' + "LATE_LINE: v\n"
column_zero_after_frames(se)  ->  [('LATE_LINE: v', True)]
#   reported line at index 42; its preceding line is '  File "x.py", line 1, in f'
#   the label is at index 0  ->  42 lines back
```

⛔ **THE FIXTURE THE NEW CASE USES PRINTS THE REFUTATION THREE LINES BENEATH THE CLAIM.** Rendered
through production `run_mutations` over the `_q` fixture at `:3858-3875` — this is the exact string a
reader of a failed sweep sees:

```
… ValueError: SHUTDOWN_SECOND [its own preceding line began 'Exception ignored in', which the CHILD wrote]. ⛔ THIS HARNESS DOES NOT CLAIM …:
    :
  File "/…/q.py", line 5, in <module>
    raise RuntimeError("FIRST_KILLER")
RuntimeError: FIRST_KILLER
Exception ignored in: <function _Leaky.__del__ at 0x10f27d580>
Traceback (most recent call last):
  File "/…/q.py", line 3, in __del__
ValueError: SHUTDOWN_SECOND
```

`ValueError: SHUTDOWN_SECOND`'s own preceding line is `  File "/…/q.py", line 3, in __del__`. The
label is three lines above it. The harness asserts the adjacency and then prints the evidence that
refutes it, in the same message, every time.

⚠ **What is NOT wrong, stated so the fix is not aimed at the wrong thing.** The *boolean* is sound:
it faithfully records that the nearest preceding non-blank, non-header line **of the frame block**
began with the label, and I found no input where it is set without such a line existing (`intro =
""` when nothing precedes, so a first-line heading and a bare-header-only stream both give `False`).
The defect is entirely in the sentence that renders it.

⭐ **The fix is subtraction, and this is explicitly not a seventh narrowing.** Two options, both
removals:

* delete the second tuple field and the annotation — the raw stderr is already printed directly
  beneath, where the reader can see the label and judge for themselves; or
* render the fact the code computes: *"the frame block this line follows was introduced by a line
  beginning 'Exception ignored in', which the CHILD wrote"*.

⚠ And note the direction of the trade this fold made. The withdrawn wording — `[after a **block**
CPython labelled 'Exception ignored in']` — was **true about position** and false only in its
attribution. The replacement removed a false attribution and introduced a false position. That is
worse on the axis #280 chose: the redesign's whole settlement is that the harness may say where text
appeared and nothing else, so a false positional claim is the one error this component cannot absorb.

---

## Medium

**M1 — "at column zero" is false for four classes of whitespace indentation, and `.strip()` erases
the evidence. The replacement sentence states the normalization and omits the selection — which is
the half of Codex M1 that was not folded, and it also refutes row #280's closure justification.**

`scripts/check-plan-code.py:3027-3029`:

```python
                said = ("stderr printed these lines at column zero after a traceback frame "
                        "block, in the order the child printed them, each STRIPPED of "
                        "surrounding whitespace — "
```

"Column zero" is decided at `:617` by `lines[i].startswith((" ", "\t"))` — space and tab only. Every
other whitespace character leaves a line classified as column-zero, and `.strip()` at `:648` then
removes it from the quotation, so the report says the child printed at column zero a line the child
indented, and shows no trace of the indentation. Measured, real calls, frame block then one line:

| child's line after the frame block | reported as | claimed "at column zero"? |
|---|---|---|
| `　FORGED_IDEOGRAPHIC` (U+3000) | `FORGED_IDEOGRAPHIC` | yes — false |
| ` FORGED_NBSP` (NBSP) | `FORGED_NBSP` | yes — false |
| `\x0bFORGED_VT` (vertical tab) | `FORGED_VT` | yes — false |
| `\x0cFORGED_FF` (form feed) | `FORGED_FF` | yes — false |
| `\x00FORGED_NUL` | `\x00FORGED_NUL` | yes — correct (NUL is not whitespace) |
| `﻿FORGED_BOM` | `﻿FORGED_BOM` | yes — correct (BOM is not whitespace) |
| `CRLF_LINE: x\r` | `CRLF_LINE: x` | yes — correct |

Codex r14 M1 reached two of these (`\fFF_MARKER`, `　`) and framed them as *"`.strip()` both
**filters** and **changes** the quoted lines"*, asking to *"State the actual selection and
normalization"*. **The fold delivered the normalization half only.** The new sentence says the lines
are stripped; it does not say which lines were not reported. The commit message knows this —

> a whitespace-only column-zero line is consumed by the run loop and disappears

— but the **reader of the report** is not told, and the sentence `"stderr printed these lines at
column zero after a traceback frame block"` is a definite description that reads as the complete set.
Reproduced: `'…frames…\n   \nREAL_AFTER\n'` → `[('REAL_AFTER', False)]`; the whitespace-only
column-zero line is consumed by the run loop at `:632-633` and is nowhere in the report.

⚠ **The completeness disclaimer does not cover this.** `:3042-3046` carries *"DOES NOT CLAIM THE LIST
BELOW IS COMPLETE"*, but "the list below" is the list of four **producers** enumerated immediately
after it, not the quoted lines, and the `said` clause is spliced in later in the same f-string. I
read the rendered message end to end (quoted in H1) to confirm the scoping rather than inferring it
from the source.

⛔ **This also refutes a closure justification standing in two documents and a comment.**
`docs/backlog.md:294`, `:295` and `scripts/check-plan-code.py:4192-4194` all close the other
direction of #280 with *"the caller claims only that the child printed these lines at column zero
after a frame block, **which it did**"*. For the four whitespace classes above, it did not. The row
is wrong about its own subject.

⭐ **Removal again, not a predicate.** Do not widen the indentation test — that is the narrowing
sequence restarting on a new character class, and this component is armed for thrashing. Either stop
claiming a position (`"stderr printed these lines, in the order the child printed them, each stripped
of surrounding whitespace; lines consisting only of whitespace are not listed"`), or state the rule
the code actually implements: *"these lines did not begin with a space or a tab"*, which is checkable
and true.

**M2 — Codex r14 H1 had two halves; the second was not folded. The message still calls
child-written text "a traceback frame block", and Codex's own witness still produces it.**

Codex r14 H1, verbatim:

> The frame regex also establishes only **frame-shaped text**, not an authentic traceback frame
> block.

`:3027-3028` still says "after a traceback frame **block**". The decision behind it is `:531`:

```python
FRAME_LINE = re.compile(r'^[ \t]+File "')
```

— text the child writes, which is the same provenance problem as the `intro` boolean and the same
reason `_is_type_name` was deleted. Codex's exact witness, reproduced through the real function:

```python
raise RuntimeError('real\nException ignored in FORGED\n  File "fake", line 1\nPLAIN_TEXT')
# column_zero_after_frames ->
#   [('RuntimeError: real', False), ('Exception ignored in FORGED', False), ('PLAIN_TEXT', True)]
```

`PLAIN_TEXT` follows no traceback frame block — it follows a frame-SHAPED line inside an exception
message — and the report calls it one, and (per H1) annotates it as well. The fold changed the
annotation's wording and left this clause untouched, so the half of H1 that said *"the frame regex
also establishes only frame-shaped text"* is unanswered.

⚠ **Stated fairly: this is not fold-induced, and row #280 argued it was honest.** The claim is
pre-existing from r12's `FRAME_LINE` repair, and the reachability bound in row #280 (*"ZERO in the
delivered corpus"* — no frame-shaped text inside an exception message under `scripts/`) still holds
as far as I checked. It is filed because (a) it was a named half of the finding this commit exists to
fold, and (b) the commit's claim *"nothing decides what a line MEANS"* is false while this clause
stands: `FRAME_LINE` decides a line is a traceback frame, and the message publishes that decision.
The cheap fix is one word: "after an indented run containing a frame-SHAPED line".

**M3 — #270's "load does not explain which one dies" is derived from the one quantity `ci.yml` says
proves nothing, and at the incident commit the two shards are not composed alike.**

The commit message:

> Derived, not assumed: this file's eight shard counts are 18,18,18,18,18,18,19,19, so shards 7 and
> 8 carry the same **load** and load does not explain which one dies.

Codex was careful here and said *count*: "Shards 7 and 8 do carry the same **count**, 19." The fold
upgraded count to **load**, and `.github/workflows/ci.yml:672-675` — the workflow that defines these
shards — says in its own words why that does not follow:

```
        # shard predicted work from the same per-suite costs, at N=8: ROUND-ROBIN 325-374s,
        # a 1.15x spread; CONTIGUOUS 27-491s, a 17.9x spread, with the long shard carrying the
        # expensive block alone. At N=16 contiguous reaches 63x. A per-shard mutation COUNT is
        # even either way, which is exactly why counting them proves nothing.
```

Two concrete objections:

1. **The quantity is one file's count, and a shard runs all 57 files.** The cost model the workflow
   itself uses is `Σ_files (entries in this shard) × (that file's suite time)`. `check-plan-code.py`
   is 19 of shard 8's 193 entries.
2. **At `c5660227` — the commit where shard 8 was cancelled — shards 7 and 8 are NOT composed
   alike.** Re-derived from `shard_slice` (`muts[index-1::total]`) and `load_manifests`' sorted-glob
   order:

   ```
   PARENT c5660227, per-file differences between shard 7 and shard 8:
     gen-goals-page.py (4,3)  check-anchors.py (1,0)  check-roadmap-consistency.py (1,2)
     check-anon-exposure.py (1,2)  check-theme-token-coverage.py (1,0)  observer_log.py (2,3)
     check-review-rounds.py (4,3)  check-vocabulary-collisions.py (0,1)
   ```

   Eight files differ, and the workflow's own figure says round-robin leaves a 1.15x predicted-work
   spread even when counts are even. So "the same load" is **not established** at the commit that
   matters.

⚠ **The conclusion may well be right, and that is not the finding.** At HEAD shards 7 and 8 happen to
have *identical* per-file composition (193 entries each, every file equal), which would support the
claim far better than what was written — but HEAD is not where the cancellation happened. The finding
is that a conclusion now standing in the repository record as *"Derived, not assumed"* is derived
from a quantity the repository elsewhere says proves nothing, and the derivation that would support
it was not done. What would settle it: per-shard predicted work at `c5660227` using the per-suite
costs `ci.yml:650-656` already records.

⛔ **And the thing this hands off to is not measurable here either.** The sentence continues *"the
suite-cost regression becomes the thing to act on"*, on the strength of a 4s → 6s figure the commit
itself lists under NOT RUN. I measured it on an idle machine, two runs per commit:

```
origin/master  74a44551   6.06s  4.89s
c5660227                  5.89s  5.72s
9232cbd9 (HEAD)           5.66s  6.33s
```

**The run-to-run spread on a single commit (master: 4.89–6.06s, 1.24x) is larger than any difference
between commits**, and HEAD is not measurably slower than master. That does not refute the original
4s → 6s observation — a different machine under different load can show it — but it does mean the
regression now nominated as the next action has no reproduced magnitude behind it, and a 2-sample
local timing cannot supply one. If it is to drive work, it needs measuring where it was seen (CI),
with repeats; if it cannot be, the row should say so rather than name it as the thing to act on.

---

## Low

**L1 — The corrected L2 sentence attributes to round 11 two refutations that neither round-11
document contains.**

`scripts/check-plan-code.py:537-541`, the new text:

```
# text the child controls. ⛔ r14 L2 CORRECTED THIS SENTENCE: it said "five consecutive review
# rounds (9-13)", and the list below is FIVE REFUTED ANSWERS ACROSS THREE ROUNDS — 11, 12 and
# 13, two of them in r11 and two in r12.
```

The list's two r11 rows are:

```
#   r11  keyed on the `Traceback` header         -> a top-level SyntaxError omits it, returned None
#   r11  took the FIRST block                    -> a raise-from chain named the cause, not the killer
```

Neither refutation appears in either round-11 document. Searched both halves:

* `"SyntaxError"` across all of `docs/reviews/*/backlog-249-260-r*.md`: 8 files match. In
  `claude/…-r11-claude.md:274` it appears in a list of probe shapes, not as a finding; in
  `codex/…-r12-codex.md:84` likewise ("Real-child probes handled … top-level SyntaxError"). **No
  round refutes an answer on the grounds that a SyntaxError omits the header.**
* `"FIRST block"`/`"first block"` across the same corpus: **0 hits anywhere.**
* Known-positive control for the instrument: the same grep over rounds 12 and 13 returns the
  ASCII-validator row (`claude/…-r12-claude.md:198`, `codex/…-r12-codex.md:24`), the indented-run row
  (`claude/…-r12-claude.md:136`) and the `isidentifier` row (`claude/…-r13-claude.md:369`,
  `codex/…-r13-codex.md:14-19`), so the search does find these when they exist.

What round 11 **did** refute (`claude/…-r11-claude.md:13-70`, H1) is a different pair: the LAST-block
fatality rule (*"the docstring's justification is FALSE as a universal"* — shutdown blocks), and the
header **equality** test matching an indented opener (`:58-62`, measured:
`exception_heading(indented_tb + "0/0 passed\n")` → `'0/0 passed'`), plus `ExceptionGroup`.

So the **count** "two in r11" is defensible, and rounds 9–10 are correctly excluded (I checked: zero
hits for any of these subjects in either r9 or r10 document). What is wrong is that the two r11 rows
describe refutations that happened somewhere other than r11. Codex's L2 only claimed the examples
"cover rounds **11–13**"; the per-round attribution is the fold's own addition, and it is the part
that is unsupported. ⚠ This is the second iteration of this sentence being wrong about its own
history; the cheap repair is to drop the per-round attribution rather than re-derive it, since the
list's purpose is the five answers, not their dates.

**L2 — The commit's shard-count figure describes the parent tree, not the tree it is committed in.**

> this file's eight shard counts are 18,18,18,18,18,18,19,19

Re-derived (`shard_slice`, `load_manifests` sorted-glob order, shards 1-based per `ci.yml:676`):

```
c5660227 (parent):  [18, 18, 18, 18, 18, 18, 19, 19]   sum 146   <- the commit's figure
9232cbd9 (HEAD):    [19, 18, 18, 18, 18, 18, 19, 19]   sum 147
```

The figure is correct for `c5660227`, where the #270 incident occurred, and the commit does date the
shard-8 pass to that commit. But the counts sentence is in the present tense inside a commit whose
own change moves the distribution (the new entry lands at 0-based global 736 ≡ 0 mod 8, i.e. shard
1), so a reader re-deriving at HEAD gets a different vector and reads the commit as wrong. This is
the repo's own rule from `CLAUDE.md` — *"Record which build a manual check was verified against"* —
applied to the one figure in this commit that the commit itself changes. One clause fixes it: "at
`c5660227`".

**L3 — "mutation 131" is a bare index whose other natural reading lands on a different, nearly
identically named entry.**

> mutation 131 RETARGETED: its anchor was the line this fix rewrites.

`131` is the **0-based within-file** index (global 0-based 721 = 590 + 131), consistent with the
`--shard0` convention used beside it. Read 1-based — the convention `shard_slice`'s own docstring
uses for `--shard` (*"`index` is 1-BASED, because it is what a human types"*) — it resolves to global
720, which is:

```
⛔ r11 H1 (name corrected r12 Codex L1) — only the LAST heading is kept, so a `raise … from …` …
```

a *different* entry whose name also begins `⛔ r11 H1`. So the two readings differ, both land on an
`r11 H1` entry, and only one of them is the retarget. Codex's table avoided this by printing both
("In-file index 131 / Zero-based population position 721"). Naming the base, or quoting the
population position as the commit does elsewhere, removes the ambiguity. (`CLAUDE.md`: *"never a bare
`#39` or `M4` — qualify the namespace."*)

---

## Checked and found SOUND

Every figure below I re-derived myself rather than reading it back.

**The falsifier, in both directions — the fold's strongest claim, and it holds.**

* **Forward.** Severed the annotation using the manifest entry's **own** edit text (asserted the
  anchor resolves exactly once first), then ran the suite: `297/298`, with exactly one red and it is
  the named case — `[FAIL] ...and the harness's OWN note is there, in text raw stderr cannot supply:
  got False want True`. Restored from a pre-edit copy; `git status --porcelain` empty.
* **Backward — the fold's "298/298 still passed" on the parent, reproduced.** Built a full
  `HARNESS_TREE` copy (`scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`,
  `.github/workflows`) in scratch, checked out `c5660227:scripts/check-plan-code.py` and its
  manifest into it, and took a **green control first**: `298/298`. Then severed the OLD annotation
  (`+ " · ".join(h + (" [after a block CPython labelled …` → `join(h for h, ig in heads)`):
  **`298/298` still passed.** The case really could not fail, for the reason the commit gives — I
  confirmed by eye in the rendered report (quoted in H1) that `diagnostic_tail` carries CPython's own
  `Exception ignored in: <function _Leaky.__del__ …>` into the same string.
* **No ambient route for the replacement.** `grep -rn "its own preceding line began"` across the repo
  returns exactly three sites, all inside the harness: the emitter `:3031`, the case `:3895`, and the
  mutation's anchor in `scripts/mutations/check-plan-code.json`. Raw stderr cannot supply it.

**Both scoped mutation runs, re-derived and re-run.** `--shard0` is zero-based and stride =
population, so `N/1549` selects exactly one entry. I confirmed the position→entry mapping by calling
`load_manifests` myself rather than trusting the progress line:

| claim | 0-based global | entry it resolves to | run result |
|---|---|---|---|
| the ADDED entry | 736 | `⭐⛔ r14 H1 — the harness's OWN note …` ✓ | 1 killed, 1 attributed, 0 survivors (~20s) |
| the RETARGET | 721 | `⛔ r11 H1 (retargeted AGAIN at r14 …)` ✓ | 1 killed, 1 attributed, 0 survivors |

* **The "unobservable expect" trap is NOT present here.** The roadmap records that one #280 retarget
  survived because its `expect` named a case calling the function directly. Both entries here name
  cases that read the **report** list `_repq` from a real `run_mutations` — `:3895` for the new entry
  and `:3892-3893`'s neighbour `" · "` case for the retarget — and both were observed to die, not
  merely asserted to.
* **Mutation 131's `expect` asserts the JOIN SEPARATOR, not an ambient marker**, as the mandate asked
  me to check: it names `⭐⭐ #280: the report QUOTES the child's column-zero lines, joined`, whose
  assertion is `any(" · " in r for r in _repq)`. Raw stderr has newlines there, not ` · `.

**Every count, re-derived in both directions.**

| claim | re-derived | how |
|---|---|---|
| 298/298 cases | **298/298** | ran it (6.5s, uncontended) |
| entries 146 → 147 | parent **146**, HEAD **147** | `load_manifests` + `EXPECTED_MUTATIONS` |
| declared sum 1548 → 1549 | parent **1548**, HEAD **1549** | `sum(EXPECTED_MUTATIONS.values())` |
| declared == actual | **0 mismatches, all 57 files** | per-file `Counter` vs the dict, both directions |
| binding 1557 / 1549, 0 unbound | `binding OK — 1557 anchor(s) across 1549 entries` | `--binding` |
| no duplicate name or anchor | `load_manifests` problems **`[]`**; 0 duplicate anchors in this file | its own identity rules |

* **Nothing was retired or orphaned to pay for the rise.** Diffed the manifest name sets
  `c5660227` → `9232cbd9`: one name out, two in, net +1 — and the name that left is the retarget's
  *old* name (the entry was edited in place, not replaced), which the JSON diff confirms. So the rise
  is one genuinely new entry. A `--binding` of 0 unbound rules out an orphan.
* Three duplicate names exist in the **global** population (across different files, e.g. the
  `PYTHONDONTWRITEBYTECODE` pair) — pre-existing, and legitimate: `load_manifests` scopes its
  duplicate-name rule per manifest, by design. Not introduced here, not a finding.

**The fold's own r14 L1 (the backlog-row case count) is right, and so is every other figure in those
rows.** ⚠ Not to be confused with *my* L1 above, which is about a different sentence. I checked
the case count at the commits themselves rather than at HEAD, by swapping each revision into the
scratch harness tree:

```
ab53945a^  (cb1de6d9)  291/291 passed     <- the row's "291 →"
ab53945a               298/298 passed     <- the row's "→ 298"   (the "295" it corrected: unsupported)
c5660227               298/298 passed
```

and the rows' other figures, which only the case count was corrected in, are all right for
`ab53945a`: entries **147 → 146**, declared sum **1549 → 1548**, binding 1556/1548 (Codex
reproduced the binding figure independently; I reproduced the entry and sum figures). The roadmap at
`docs/roadmap-to-launch.md:3094` agrees. ⚠ A coincidence worth knowing about but not a defect: the
pre-#280 values (147 entries / sum 1549) are numerically identical to the post-r14-fold values, so
those two numbers now mean two different commits in the same paragraph.

**The fold's own change carries coverage.** `--diff-coverage origin/master` (advisory, `|| true` in
`ci.yml:763`) reports 4 functions with no reaching mutation — `check-withdrawal.py` ×2,
`codex-frontier-model.py`, `find-claim.py`. **None is in `check-plan-code.py`**, and none is from
this commit, which touched only `check-plan-code.py`, its manifest and `docs/backlog.md`.

**Guards, run as a suite and not as a subset.** All 45 `python3 scripts/check-*` invocations from
`.github/workflows/ci.yml` that do not need Postgres, a jest results file or a network base ref:
**44 rc=0, 1 rc=1.** The one red is `check-review-rounds.py`, reporting exactly the known-true
condition:

```
✗ backlog-249-260 round 14: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
```

i.e. this document's absence. The full list was run **twice, independently**, with identical results
(45/45 accounted for, same single red). `check-docs.py`, `check-selftest-counts.py` (which owns the declared
298), `check-anchors.py`, `check-backlog-closure.py`, `check-roadmap-consistency.py`,
`check-ratchet-contract.py`, `check-producer-enumeration.py` and `check-main-drivable.py` are all
green. Which I did **not** run, and why, is in CANNOT RUN.

**The flag is not spuriously set in the "no label" directions.** Checked each case the mandate
named: heading is the first line of the stream → no preceding frame block, so not reported at all;
nothing precedes → `intro = ""` → `False`; a bare `_TB_HEADER` is the only preceding line → looked
past, `intro = ""` → `False`. I found no input that sets the flag without a label line existing
earlier in the stream. The defect in H1 is the rendering, not the boolean.

**Positional probes that came back clean.** `\x00` and `﻿` are not whitespace in Python, so they
survive `.strip()` and the quotation shows them; `\r` from CRLF is stripped as whitespace, and in
production `text=True` decoding normalizes it before this function sees it. Split writes and stream
interleaving cannot affect this function — it receives `se` as one already-assembled string.

**Not findings, checked and dismissed.**

* The commit's *"over a green parse control"* for the sever measurement is a weaker control than the
  repo's own rule prefers, but the measurement it supports **is** a full suite run, and I reproduced
  it with a green suite control either side. No finding.
* `docs/roadmap-to-launch.md:3094`'s counts line was not given the r14 addendum that
  `docs/backlog.md:294-295` received. Its figures are correct for the commit its section describes
  and it does not claim to be current. Asymmetric, not wrong.
* The three `scripts/` guards warned by `--diff-coverage` are pre-existing on this branch.
* #270, #272, #275–#278 remain open and unfixed, as the mandate states. I did not file "still open"
  as a finding. M1's objection to row #280 is not that it is open — it is closed — but that its
  closure sentence is false about its own subject.

---

## CANNOT RUN

⛔ **Treat every item here as NOT RUN, not as a pass.**

* **The full local `--mutate .` sweep: NOT RUN.** Local shards exceed `SUITE_TIMEOUT = 120`. Two
  single-entry runs at stride 1549 do not establish population-wide coverage, and I am not implying
  any. The fold declares this too.
* **A CI replay of the fold: NOT RUN.** I inspected no workflow run and triggered none. Codex's
  GitHub job metadata for the #270 cancellation (shards 1–7 succeeded, shard 8 cancelled,
  23:14:57 → 23:45:16 = 30m19s) is **relayed, not reproduced** — I did not open that run.
* **The 4s → 6s suite-cost figure: NOT reproduced, in either direction.** On an idle machine, two
  runs per commit, the within-commit spread exceeds the between-commit difference (figures in M3),
  so this machine cannot measure a regression of that size and **I am not reporting its absence as
  a refutation**. An earlier sweep of five commits ran while two background jobs competed for the
  CPU (5.14 / 5.93 / 6.09 / 7.22 / 9.37s) — those numbers are inflated by an unknown factor and I
  discarded them rather than quote a trend from them. Magnitude: NOT MEASURED.
* **Guards needing an environment I do not have: NOT RUN.** `check-plan-code.py --mutate .` (above);
  `check-test-counts.py --results jest-results.json` (no jest run — only its `--self-test`);
  `check-function-revokes.py`, `check-storage-grant-pin.py`, `check-storage-independence.py`
  (Postgres/migration environment — only `--self-test` for the last); `check-provenance.py --base
  origin/master` and `check-withdrawal.py --base origin/master` (only their `--self-test`);
  `check-review-recorded.py` in its non-self-test form (red by design at this commit per the mandate
  — only `--self-test`); `check-dashboard-entry.py` in its full form; `check-vocabulary-collisions.py`
  and `check-guard-coverage.py` entry points (catalog/Postgres — only their `--self-test`, which is
  what CI runs); `tsc --noEmit` and the unit suite.
* **The reachability of M1's and M2's forged inputs in the delivered corpus: NOT MEASURED by me.** I
  relied on row #280's recorded bound for frame-shaped-text-in-a-message (zero under `scripts/`) and
  did not re-derive it; I did not search `scripts/` for stderr lines indented with U+3000, NBSP, VT or
  form feed. Both findings are stated as latent on that basis, like #280's own.
* **H1's annotation firing in a REAL sweep: NOT WITNESSED.** Every emission I measured came from
  constructed streams or the harness's own `_q` fixture, both of which I built or the suite builds.
  The route into the delivered corpus is the one r11 recorded — `TemporaryDirectory`'s finalizer
  printing `Exception ignored in:` when cleanup fails, used by 34 scripts — but I did not catch it
  firing, and the full sweep that could is the CANNOT RUN above. H1's severity therefore rests on the
  annotation being false whenever it is printed, which is measured, and **not** on a witnessed
  misreading, which is not.

---

## Instruments

* Worktree `…/scratchpad/wt-backlog` at `9232cbd9`; prepared `.venv/bin/python` **3.12.9** with
  `markdown-it-py 4.2.0` (verified before use — a bare `python3.12` raises `ParserUnavailable` by
  design); `.venv/bin` first on `PATH` for the mutation harness, which spawns `sys.executable`.
* **Commit message read first**, in full, before the diff. Then `git diff c5660227..9232cbd9` per
  file (`docs/backlog.md` row-wise, since the rows are single 10 KB lines), `git show ab53945a`,
  and the r14 Codex half end to end before forming any finding.
* The function was analysed by **transcribing it to yield reported-line indices and proving the
  transcription agrees with the original on every input** (0 mismatches over 59,049 streams), rather
  than by reasoning about it — the repo's "measure what the CODE sees" rule.
* Real `run_mutations` through the production path for the rendered report; real subprocesses for the
  `_q` shutdown fixture; `column_zero_after_frames` called directly for the positional probes.
* Severs restored from a byte-copy taken before editing, with `shasum` on the copy and
  `git status --porcelain` verified empty afterwards. Parent-commit work was done in a **separate
  scratch `HARNESS_TREE` copy**, never by checking anything out in the worktree, and never with any
  `git` command run in the main checkout.
* Every search negative was checked against a known positive with the same instrument before being
  believed (stated inline in L1).
* Guards run as the **full list** extracted mechanically from `.github/workflows/ci.yml`
  (`grep -oE "python3 scripts/check-[a-z0-9-]+\.py"`), not a hand-picked subset.

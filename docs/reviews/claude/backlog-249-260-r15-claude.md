# Round 15 — Claude half, PR #371 (`backlog-249-260-fixes`)

**Subject:** `ce8c2cbf` — *"The annotation is DELETED, as pre-committed"*. Reviewed against the
COMMITTED tree at that SHA. Folds `docs/reviews/codex/backlog-249-260-r15-codex.md` (H1/M1/L1).

**0 Blocking / 2 High / 5 Medium / 2 Low. ⛔ NOT CONVERGED.**

⭐⭐ **THE ONE FINDING:** the fifth sentence written about this stream is **false in the same
POSITION category as wording #2**, and — H2 — **nothing in the suite can see it**. Severing every
clause of the surviving sentence and replacing it with the exact claims #279/#280 were filed to
remove (*"CPython SAID"*, *"KILLED the child"*, *"a VALIDATED exception class"*) leaves
**296/296 GREEN**, over a control proved green first. The commit diagnoses the four false wordings
as *"the case eventually written only ever required the SENTENCE'S PRESENCE, never its TRUTH"*.
After this commit the sentence does not even require its presence.

⚠ Both Highs say **STOP CLAIMING**, not *handle another case*. No predicate, no validator and no
sixth wording is proposed anywhere below; the component is armed for THRASHING and a narrowing is
the move the arming exists to stop.

---

## Blocking

None.

---

## High

### H1 — wording #5 is FALSE: the reported lines are not "at column zero", and this is the same POSITION category that killed wording #2

`scripts/check-plan-code.py:3049-3050` renders

```
                said = ("stderr printed these lines at column zero after an indented run that "
                        "contained at least one line matching `File \"`, in the order the child "
```

The run detector and the run terminator both test `startswith((" ", "\t"))` and nothing else —
`:641` and `:645`:

```
        if not (lines[i].strip() and lines[i].startswith((" ", "\t"))):
...
        while i < n and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
```

while the value reported at `:661` is `lines[i].strip()`, and `str.strip()` strips **every**
`str.isspace()` character. So any line indented with a whitespace character outside `{" ", "\t"}`
(a) terminates the run, (b) is reported, and (c) has its indentation stripped out of the report —
and the harness then asserts the child printed it **at column zero**.

**Measured through real children and the RENDERED report**, not a typed fixture. Child body
(a module-level raise, mutated into a real suite and run through `run_mutations`):

```python
raise RuntimeError('real\n  File "fake", line 1\n　PAD_IDEOGRAPHIC\nValueError: tail')
```

The report reads:

> `… stderr printed these lines at column zero after an indented run that contained at least one
> line matching `File "`, … — RuntimeError: real · PAD_IDEOGRAPHIC. ⛔ THIS HARNESS DOES NOT
> CLAIM …`
>
>     RuntimeError: real
>       File "fake", line 1
>     　PAD_IDEOGRAPHIC
>     ValueError: tail

⭐ **The sting is identical to wording #2's:** `diagnostic_tail` dumps the raw stderr into the same
string, so the report prints its own refutation three lines under the claim — the ideographic space
is visible in the dump and absent from the quotation. Reproduced the same way with `\x0c`
(`PAD_FORMFEED`), `\xa0` (`PAD_NBSP`) and `\x0b` (`PAD_VTAB`); `\r` likewise on the pure function.

**The bound, stated as a bound.** Over all 262,144 six-line streams of an 8-shape alphabet (bare
header, real frame, ordinary col-0 heading, blank, and one line each indented by U+3000, form feed,
NBSP, tab): **127,440 lines reported, 76,464 of them NOT at column zero**, every one of the 76,464
led by exactly `\x0c`, `\xa0` or `　` (25,488 each). ⚠ **The 60.0% is a property of MY
alphabet**, which loads three of eight shapes with such an indent — it is not a real-world rate and
is not offered as one. What it does establish is the exact rule and that nothing else falsifies the
clause: **the claim is false iff the reported line begins with a whitespace character outside
`{" ", "\t"}`**, and true for every other reported line in the grid.

⚠ **NOT fold-induced, and stated rather than hidden:** `at column zero` was already in r14's
wording (`- said = ("stderr printed these lines at column zero after a run of FRAME-SHAPED "`). What
`ce8c2cbf` introduces is the **claim about it** — *"the report now says only what the code
establishes"*, in the commit message and in the docstring at `:562-592`. That claim is what is
false. This is the same move r12 made on the frame-marker bound: the hole predated the fold, the
sentence written to defend it did not.

⚠ **Reachability:** the witness is a child-written exception MESSAGE, which the subject under test
writes and this harness therefore cannot bound. This file already treats U+3000 as a live adversarial
input, not an exotic one — r12 Claude L1 is in the same function's caller at `:3040`: *"three U+3000
ideographic spaces report '3 byte(s)' for 9 bytes"*.

**Concrete failure scenario.** A mutation lands inside a message string containing a non-breaking
space (this repo's scripts are full of `⚠`/`⛔`/U+00A0-adjacent text). The suite dies, the sweep
reports *killed but unattributable*, and the diagnostic tells the reader a line was printed at
column zero when it was printed indented. The reader is diagnosing the printer, which is the one
thing world 1 of this message exists to rule out — so a positional falsehood here steers the
diagnosis, exactly as r14 H1 argued when it refuted wording #2.

**The remedy is the next NARROWING, not a predicate.** Delete the positional clause. The function's
return value supports *"stderr printed these lines, in the order the child printed them, each
STRIPPED of surrounding whitespace"* and nothing more; `at column zero` and
`after an indented run that contained at least one line matching \`File "\`` are both narration
about structure the harness read out of text the child controls, which is #280's thesis. ⛔ Do **not**
widen `startswith` to `str.isspace()`: that is wording #6, and the clause would then still be a
claim about the child's stream that the suite cannot check (H2).

### H2 — the surviving sentence has NO falsifier in either direction: severed to flagrantly false text, the suite is 296/296 GREEN

This is **why** H1 was shippable, and it is a coverage hole the deletion opened.

The commit retired the annotation's own case and its mutation. What covers the `elif heads:` wording
now? Measured over the manifest and the suite:

* **mutations anchored on any clause of this sentence: ZERO.** The only wording-anchored entry in
  `scripts/mutations/check-plan-code.json` targets **world 3** —
  `'                said = ("stderr printed no line at column zero after a frame block, so read the "'`
  — whose case `:3861` asserts `any("printed no line at column zero after a frame block" in r …)`.
* **cases reading this sentence's text: ZERO.** `grep -n 'at column zero'` over the file returns
  `:3049` (the string itself) and `:3861` (world 3's case). World 2's only cover is the ` · `
  separator mutation at position 721.

**Severed and measured on an ISOLATED copy, control first.** Copy = `HARNESS_TREE`'s six paths
(`scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`, `.github/workflows`)
under the scratch directory; the worktree was never modified.

| run | result |
|---|---|
| **CONTROL #1** (5 of 6 paths) | **293/296 — RED.** `[FAIL] ...and every entry actually arrives, nested paths included`. Discarded as **CANNOT RUN**, not published as a finding |
| **CONTROL #2** (complete tree) | **296/296 passed** |
| **SEVERED** — `:3049-3051` replaced, join kept | **296/296 passed** |

The replacement text was chosen to be maximally false, reinstating the three claims #279 and #280
were filed to delete:

```python
                said = ("CPython SAID THE FOLLOWING KILLED THE CHILD, in reverse order, "
                        "each one a VALIDATED exception class, and the run above them was "
                        "written by the interpreter and not by the suite — "
```

So at `ce8c2cbf` the harness can be made to assert causal attribution, interpreter authorship, class
validation **and** reverse ordering — every single claim the #279/#280 redesign removed — with a
green suite and a green `--mutate .` for this file. ⛔ **A sixth wording cannot be prevented by
review, because review is the only instrument that can see this sentence at all.** r14's forged
attribution and r15's four refutations all passed the same way.

Two remedies, and they are not equal:

1. ⭐ **PREFERRED — make the sentence unfalsifiable by making it claim nothing** (H1's remedy):
   quote the lines, name the separator, claim no position, no structure, no origin. Then there is
   nothing for a case to check, and no round can refute it.
2. If any clause is kept, **one case must assert its TRUTH over a constructed stream** — not its
   presence. The presence-only shape is the one this commit's own message identifies as the reason
   four false wordings shipped; adding a second presence-only case repeats it.

---

## Medium

### M1 — the deleted constant's comment was left behind and now annotates `_TB_HEADER`, falsely

`scripts/check-plan-code.py:556-558`:

```
# CPython's own label for a block it did NOT die of. The discriminator for r11 Claude H1 was
# already in the stream the rule was reading.
_TB_HEADER = "Traceback (most recent call last):"
```

`_TB_HEADER` is **not** "CPython's own label for a block it did NOT die of" — it is the traceback
header, and the second sentence is the argument **for** the ignored-label discriminator that this
very commit abandons.

**Provenance measured, not inferred** — `git log -L 556,559:scripts/check-plan-code.py`:

* `7b88ced8` (round 11 Claude) introduced those two comment lines **and**
  `IGNORED_AT_SHUTDOWN = "Exception ignored in"` in one hunk, comment directly above the constant.
* `ce8c2cbf`'s hunk is exactly `-IGNORED_AT_SHUTDOWN = "Exception ignored in"` with the comment
  untouched.

So this is residue of the deleted flag presented as current documentation of a surviving constant —
the "removed too LITTLE" half, and it falsifies the commit's *"WHAT WENT, AND WHY IT HAD TO BE ALL
OF IT"* list on its fourth bullet. **Remedy:** delete both lines with their subject.

### M2 — a comment recording HISTORY was mechanically rewritten into a false historical claim

`scripts/check-plan-code.py:4215-4217`:

```
    # ⚠ The adjacent negative, not an absurd one: ordinary indented progress output. The
    # predecessor returned `["READY"]` here — an exception heading for a child that
    # raised nothing at all.
```

It read `[("READY", False)]` at `c5660227`, `9232cbd9` and `041ddcec`; `ce8c2cbf` rewrote it to
`["READY"]` along with the real tuple→string case conversions.

**Measured by extracting and RUNNING the predecessor**, rather than reasoning about it. The text was
introduced at `5ce6fed2` (*"Round 12 Codex"*, the commit that added `FRAME_LINE`), so "the
predecessor" is the pre-`5ce6fed2` code at `7b88ced8`. Executing that revision's
`exception_headings` plus its `EXCEPTION_LINE`/`IGNORED_AT_SHUTDOWN`/`_TB_HEADER` constants against
the real child's stderr (`'  connecting\nREADY\n'`):

```
PREDECESSOR (pre-5ce6fed2) returns: [('READY', False)]
```

The original comment was **true**. The rewritten one is **false**: the predecessor returned tuples,
and no revision of this code has ever returned `["READY"]` for this child — by the time the return
type became `list[str]` (this commit) the `FRAME_LINE` clause at `:652` already made the answer `[]`,
which is what the adjacent case at `:4220` asserts. This is this repo's *"a mechanical edit damages
what it preserves"* shape: a blind type rewrite applied to a sentence whose subject is a past
revision. **Remedy:** restore `[("READY", False)]`.

⚠ **Checked and NOT a finding:** the ~15 genuine tuple→string conversions in the cases themselves
weaken nothing — in every one the dropped element is the field that no longer exists (full
list-equality assertions keep pinning length and order; the `any(... for _h, _ig in ...)` →
`any(... for _h in ...)` rewrites are inert). M2 is the only one of the set that broke.

### M3 — a surviving case NAME claims the deleted label

`scripts/check-plan-code.py:4164`:

```
    case("...and an atexit callback is the same shape, by the same label",
         column_zero_after_frames(_atex),
         ["RuntimeError: THE_REAL_KILLER", "ValueError: ATEXIT_NOISE"])
```

"by the same label" is `Exception ignored in`. The case asserts no label, the function reads no
label, and the literal exists nowhere in the delivered code as a `Name` or a `Constant` outside
retrospective prose. The case name is the one string the self-test prints on failure and the key
`expect` joins on, so a name asserting a deleted mechanism is residue in the most load-bearing
string in the file. **Remedy:** drop "by the same label" — the case is about shape and still earns
its place.

### M4 — `docs/backlog.md` row #270 still carries the count→load inference the same row WITHDREW, sixty words earlier

The row withdraws it explicitly:

> ⟳⛔ **THAT INFERENCE IS WITHDRAWN 2026-10-13 by round 14's Claude half (M3) …** `ci.yml:674-675`:
> *"A per-shard mutation COUNT is even either way, which is exactly why counting them proves
> nothing."* … ⚠ I had also upgraded the reviewer's careful *same count* into *same load*; the honest
> statement is that the cause is still unknown, **NOT that load is excluded**.

and then makes it again, in the sentence the r15 fold edited around:

> ⭐ The second green carried ONE MORE mutation entry in the very file whose suite cost rose, **which
> counts against the load story rather than for it.**

"Counts against the load story" **is** excluding load, reached from an entry count. ⚠ And it is
unsupported on its own terms, by the row's own earlier paragraph: the extra entry went into
`check-plan-code.json`, and *"the reassignment story was true of TODAY's insertion into
`check-plan-code.json`"* — a mid-list insertion **reassigns** entries across shards under
`muts[index - 1::total]`, so shard 8's composition at `9232cbd9` is not the composition it had at
`c5660227`. The row never establishes that shard 8's load rose, which is the only shard its green is
evidence about. **Remedy: delete the sentence.** #270 is UNDIAGNOSED and says so; this clause adds
an exclusion the row has already agreed it cannot make.

### M5 — rows #279/#280 now end with the #280-era accounting, stated after the r15 accounting and contradicting it

Both rows close with, consecutively:

> ⟳⟳ **r15 then DELETED that annotation and the machinery behind it, so entries fall 147 → 144 …**
> Every one of those falls is the sanctioned kind — **THREE mutations and TWO cases** retired WITH
> THEIR SUBJECT, nothing orphaned, and the two siblings whose subjects survived retargeted in place.
> **The entry fall is the ONE sanctioned kind** — **two mutations** RETIRED WITH THEIR SUBJECT (the
> deleted validators), four RETARGETED, one ADDED as the falsifier for the removal itself, and
> **four self-test cases** retired with the same subject.

The second sentence describes `ab53945a` (the #280 closure, 147 → 146). It carries no round marker,
no date and no `⟳`, sits in the present tense immediately after the r15 sentence, and opens with the
same formula — so the row's **final word** on "the entry fall" states 2 mutations and 4 cases where
r15 retired 3 and 2. The r15 text was inserted in front of a pre-existing sentence without
re-anchoring it. **Remedy:** prefix the older sentence with its revision (`⟳ at ab53945a:`) or fold
it into the trail above, so one row does not state two accountings of one phrase.

---

## Low

### L1 — "Guards: 21 green / 1 red" names no invocation set, and the same commit trail published a different denominator

The commit message's only guard evidence is a bare pair. The denominator matches no set I can
enumerate: **46** `scripts/check-*.py` on disk, **34** distinct guards invoked by `.github/workflows/ci.yml`,
and `9232cbd9` — four commits earlier on this same branch — published **"Guards: 50 green / 1 red"**.
Two incompatible denominators (51 and 22), neither set named, so neither is reproducible and a guard
silently dropped from the second set would be invisible. ⚠ This is the shape the review method
forbids: *name the invocation set; do not publish a bare N of N*. **Remedy:** name the set, or cite
the command that produced it.

### L2 — the quoted pattern in the message is not the code's pattern, and the omitted half is load-bearing

`:3050` says the run `"contained at least one line matching \`File \"\`"`. `FRAME_LINE` is
`^[ \t]+File "` (`:531`) — anchored, with required indentation. Verified: `FRAME_LINE.match('File "a"')`
is `False`, and a stream whose only `File "` line is at column zero reports **nothing**.

The clause is **true** (the stricter pattern implies the looser one), so this is imprecision, not a
falsehood. It matters because the dropped `^[ \t]+` is exactly what keeps the `ExceptionGroup` bound
in the docstring honest — *"its frames are prefixed `  | `, so they do not match `FRAME_LINE`"* —
and `  |   File "` contains `File "`. A reader given the loose pattern cannot derive the stated
bound. **Remedy:** quote the pattern as `^[ \t]+File "`, or drop the clause with H1's.

---

## Checked and found SOUND

Re-derived by hand or by running the thing; not re-litigated.

**The arithmetic, in both directions.**
* Manifests: **62 files, 1,546 entries**; `EXPECTED_MUTATIONS`: **62 keys, sum 1,546**; **zero**
  per-file mismatches in either direction and **zero** targets present in one and absent from the
  other. `scripts/check-plan-code.py`: **144** declared, **144** actual.
* The declared-sum case at `:6498` reads `1546`; the docstring at `:6` reads `296`; the suite runs
  **296/296**; `check-selftest-counts.py` green over **55** scripts that declare a count, each
  verified by running it.
* `--binding`: *"1554 anchor(s) across 1546 entries each resolve to exactly one site"*, rc=0 —
  **0 unbound**, exactly as claimed.
* **No duplicate name or anchor introduced.** Per-file duplicate anchors: **0** at both `ce8c2cbf`
  and `ce8c2cbf^`. The 3 duplicate names I found are **cross-file**, identical at both revisions,
  and outside the rule's scope — `seen_names, seen_anchors` are reset per manifest at `:2383`.

**Every ratchet fall is retired WITH ITS SUBJECT.** The manifest delta is 4 removed + 1 added = −3,
which is the commit's *"three retired, two retargeted"* with the join entry's rename accounted for.
Each retired subject confirmed gone from the delivered file:

| retired | subject | gone? |
|---|---|---|
| mutation: the shutdown flag forced off | `out.append((lines[i].strip(), intro.startswith(IGNORED_AT_SHUTDOWN)))` | ✅ |
| mutation: the look-PAST-the-header removal | `if lines[k].strip() and lines[k].strip() != _TB_HEADER:` | ✅ |
| mutation: the r14 annotation entry | `h + (" [a line ABOVE that run began 'Exception ignored in',"` | ✅ |
| case: the `[False, True]` flag list | the flag itself | ✅ |
| case: the annotation's own falsifier | the annotation itself | ✅ |

**Both retargets, with the position mapping OBSERVED.** Derived independently: `load_manifests`
builds `muts` over `sorted(d.glob("*.json"))` in file order (`:2366`), and `shard_slice` returns
`muts[index - 1::total]` (`:2521`) with `--shard0` adding 1, so `--shard0 K/1546` selects exactly
`muts[K]`. My own enumeration puts `return out[-1:]` at **0-based 720** and the join separator at
**721**. Run:

```
--shard0 720/1546  rc=0  [1/1] ⛔ r11 H1 (name corrected r12 Codex L1) — only the LAST heading is kept, …
                         1 killed, 1 attributed to the case each names, 0 survivor(s)
--shard0 721/1546  rc=0  [1/1] ⛔ r11 H1 (retargeted a THIRD time at r15, when the annotation's deletion…
                         1 killed, 1 attributed to the case each names, 0 survivor(s)
```

Each anchor resolves to **exactly 1** site in the delivered file.

⭐ **And the trap that produced a survivor earlier on this branch is ABSENT — both named `expect`
cases CAN observe their mutations.** Entry 720's case calls `column_zero_after_frames(_tb_chain)`
directly and the mutation is inside that function, so `return out[-1:]` makes the two-element
list-equality assertion red. Entry 721's case reads the **rendered report** (`_repq` from a real
`run_mutations`) and asserts `any(" · " in r …)`, which raw stderr cannot supply because it has
newlines there — so a message-only mutation is visible to it. Attribution in both runs confirms it
rather than my reading it off the source.

**The AST claim, verified by AST.** `intro`: **0** `Name` nodes. `IGNORED_AT_SHUTDOWN`: **0**.
`_TB_HEADER`: **2** — `:558` (the binding) and `:4186` (the case). The only `Constant` containing
`Exception ignored in` is the docstring at `:562`; the three other textual occurrences
(`:568`, `:1285`, `:3905`) are retrospective prose about the deletion. No live reader survives.

**Keeping `_TB_HEADER` is justified, not vestigial.** The case exists and is meaningful —
`:4185-4186`, against a **real child** (`def f(:`):

```
    case("⭐ a top-level SyntaxError has NO traceback header and is still named",
         column_zero_after_frames(_syn), ["SyntaxError: invalid syntax"])
    case("...and THAT is why no header literal is used to find a heading",
         _TB_HEADER in _syn, False)
```

It pins the CPython behaviour the no-header bound rests on, and the constant is its subject. ⚠ The
docstring's *"it was read ONLY by the backward scan"* (`:605`) is correct **as scoped** — it says
"no longer consulted **here**", and at `ce8c2cbf^` the function's only reader was `:628`; the
self-test reader at `:4160` is named by the very next sentence. Not a finding.

**The rest of the sentence's clauses, each tested.** `stderr printed …` — `heads =
column_zero_after_frames(se)` at `:3027` reads stderr **alone**, so interleaved stdout cannot reach
it and split writes only concatenate. `in the order the child printed them` — `out` is appended in
increasing index order over `stderr.split("\n")`. `each STRIPPED of surrounding whitespace` — `.strip()`
at `:661`. `after an indented run that contained at least one line matching \`File "\`` — true by
construction (the run starts at an indented non-blank line; `:652` requires a `FRAME_LINE` match).
Probed and **not** findings: CRLF throughout (the `\r` is stripped; a `"\r"` line reads as blank),
a run of only blank lines (reports nothing), a blank run then `File "` at column zero (nothing),
tab-indented frames (reported, correctly at column zero), blank lines *inside* a run, indented prose
with no `File "` (nothing), `File a` without the quote (nothing), and NUL- or BOM-prefixed headings
(reported unstripped, and both are zero-width — the claim holds).

**The banked green's premise.** `041ddcec` added **only** `docs/reviews/codex/backlog-249-260-r15-codex.md`
and its verdict file (2 files, +129), and `git diff --stat 9dd9c985 041ddcec -- scripts/` is **empty**
— `scripts/` is byte-identical, as the commit says.

**Guards.** Named set #1: `for f in scripts/check-*.py; do python "$f" --self-test; done` — **46 of
46 rc=0**. Named set #2, bare entry points (22 named in *Instruments*) — 19 rc=0; `check-review-rounds`
rc=1 and `check-review-recorded` rc=1, both known-true at this tree and not filed;
`check-closing-table` and `check-banner-armed` rc=2 printing `--decide --self-test`, i.e. they have
no bare entry point and are a usage refusal, not a gate result either way.

**Not re-litigated, per the brief:** #270 UNDIAGNOSED; #272/#275/#276/#277/#278 filed and
deliberately unfixed; `check-review-recorded` red at this tree by design with round 16 owed.

---

## CANNOT RUN

⛔ **Each of these is a FAILURE, not a pass — treat every one as NOT RUN.**

1. **The full local `--mutate .`** — shards blow `SUITE_TIMEOUT` on this hardware. The two scoped
   shards above are not a substitute for it. **NOT RUN.**
2. **`CONTROL #1` for H2** — 293/296 on an incomplete `HARNESS_TREE` copy. Discarded as the
   instrument's failure, published above rather than hidden, and the finding rests only on
   CONTROL #2 (296/296) plus the severed run. **That run: NOT RUN.**
3. **The 117,649-stream / 11,250-annotation figure.** `docs/reviews/codex/backlog-249-260-r15-codex.md:86`
   states the totals but not the shape alphabet, and the code it measured is deleted at this tree,
   so it cannot be re-derived. The commit republishes it as settled. **NOT RUN — treat the figure as
   the codex half's testimony, not as reproduced.**
4. **"severing it was measured GREEN at 298/298 before any case existed for it."** Historical, at
   `c5660227`, on a separate `HARNESS_TREE` copy. Not re-derived here. **NOT RUN.**
5. **"`check-review-recorded` was GREEN at `041ddcec` — the first time since round 13."**
   The guard takes `--base` only, no `--head`, so verifying it needs a tree at that commit; building
   one would mean `git checkout` in a worktree I was told not to disturb. Its *premise* (byte-identical
   `scripts/`) is verified above; the **run** is **NOT RUN**, and so is "first time since round 13".
6. **The original 4s→6s magnitude under its own conditions**, and a **CI replay**. **NOT RUN.** (The
   row now says only that it is a dated observation, which is the correct state — M4 is about a
   different sentence in the same row.)

⚠ **Method note, because it fired on me twice.** `timeout` does not exist on this macOS host — my
first scoped-mutation invocation returned `/bin/bash: timeout: command not found` for **both**
shards, a uniform failure across the whole population and therefore a property of my instrument;
and `rc=$?` after a pipe reported the exit code of `tail`, not the harness. Both were re-run with
the harness's own exit code read directly. A third: `git log -S 'predecessor returned \`'` lost its
argument to command substitution — the repo's documented backtick-in-double-quotes footgun, re-run
single-quoted.

---

## Instruments

Everything below ran at `ce8c2cbf` in the worktree, with the prepared venv
(`.venv/bin/python`, CPython **3.12.9**) and stdin closed (`</dev/null`).
**`git status --porcelain` is clean and HEAD is `ce8c2cbf`; nothing was committed, pushed or merged.**

* **Suite control:** `python scripts/check-plan-code.py --self-test` → **296/296 passed**, 5.70s.
* **Binding:** `--binding` → rc=0, 1554 anchors / 1546 entries.
* **Scoped mutations:** `--mutate . --shard 0 720/1546` and `721/1546`, `PATH` with `.venv/bin`
  first, harness rc read directly (not through a pipe).
* **Rendered reports:** `scripts/check-plan-code.py` imported as a module (registered in
  `sys.modules` before `exec_module`, or `dataclasses` fails), then `run_mutations` driven over a
  one-case temp suite whose mutation prepends a module-level `raise` — the `_q` fixture's shape, so
  the children are real and the report is the real `said` string. 5 children: plain raise (the
  **known positive**, to prove the instrument reaches the `elif heads:` arm before any negative was
  trusted), U+3000, form feed, NBSP, vertical tab.
* **Clause grid:** 262,144 six-line streams over 8 line shapes through
  `column_zero_after_frames`, each reported line matched back to its raw source line.
* **Predecessor replay (M2):** `git show 7b88ced8:scripts/check-plan-code.py`, the function and its
  four constants extracted by regex and `exec`'d, then run on the real child's stderr.
* **AST:** `ast.walk` over the delivered file for `Name` and `Constant` nodes — not grep.
* **Counts:** manifests and `EXPECTED_MUTATIONS` parsed and compared both directions, at
  `ce8c2cbf` and `ce8c2cbf^`.
* **H2 sever:** isolated copy of `HARNESS_TREE`'s six paths under the scratch directory; control
  proved green **before** the sever; worktree untouched.
* **Guard set #1 (46):** every `scripts/check-*.py`, `--self-test`.
* **Guard set #2 (22), bare entry points:** `check-selftest-counts`, `check-ratchet-contract`,
  `check-review-rounds`, `check-review-recorded`, `check-docs`, `check-anchors`,
  `check-producer-enumeration`, `check-sentinel-meanings`, `check-vocabulary-collisions`,
  `check-gate-falsifiability`, `check-dashboard-entry`, `check-backlog-closure`,
  `check-guard-coverage`, `check-withdrawal`, `check-provenance`, `check-closing-table`,
  `check-group-claims`, `check-rc-contract`, `check-main-drivable`, `check-surface-recall`,
  `check-banner-armed`, `check-memory-link`.
* **Provenance:** `git log -L 556,559:scripts/check-plan-code.py`, `git log -S` (single-quoted),
  `git show --stat`, `git diff --stat`, `git diff --word-diff` for the backlog rows.

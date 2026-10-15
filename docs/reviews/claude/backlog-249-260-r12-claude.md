# Round 12 — CLAUDE half, PR #371 `backlog-249-260-fixes`, subject `5ce6fed2`

Adversarial half, run AFTER the Codex half was folded, so the subject is the FIX. Mandate was to
refute, not to re-find: every finding below is either something the fold INTRODUCED, a world it
still mis-grades, or a published figure that does not survive re-derivation. Codex's
H1/H2/H3/M1/L1 are not re-reported.

## Blocking

**None established.** No world was found in which the fold produces a false GREEN, and the two
narrowings it makes (`FRAME_LINE`, `parse_fail_names(so)`) both fail CLOSED where they fail.

## High

**H1 — the H3 narrowing added a THIRD producer to the branch whose message asserts there are
exactly TWO, and the two it names both exclude the true one. The same class as the H2 this commit
folded, created by the H3 this commit folded, in the same function, 110 lines apart.**

`scripts/check-plan-code.py:2836` now reads `parse_fail_names(so)`. Measured, through real
`run_suite_parts` + `run_mutations` over a child whose suite reports on **stderr** — tally and
`[FAIL]` line both — with stdout empty:

```
control rc: 0   stdout: ''   stderr: '1/1 passed\n'
control_is_green(rc, merged)      = True      <-- the control PASSES
control_is_green(rc, stdout-only) = False
run_mutations:  caught=True, attributed=False, measured=True, fails=[]
report: "...the suite went RED but printed no `[FAIL] <case>` line, so NOTHING COULD SEE THE
         KILL. TWO WORLDS PRODUCE THIS AND THIS HARNESS CANNOT TELL THEM APART: either a
         report-format defect in e.py ... or a suite that NEVER REACHED ITS CASES..."
```

The child ran, reached its case, failed, and named that case in the exact grammar
`parse_fail_names` parses — `  [FAIL] the value is one: got 2 want 1`. It is neither of the two
worlds the message enumerates. **Before this commit that world could not reach this branch at
all**, because the merged view carried the line; the narrowing created the producer and left the
enumeration claiming two. A reader is sent to fix a report-format defect in a file whose report
format is correct.

Two aggravating halves, both measured:

1. **One function now decides the same stream question two different ways.** Greenness is
   `control_is_green(rc, out)` — `rc == 0 and "passed" in out` over the MERGED view
   (`:2683`, `:2717`) — so a suite is certified as having run on the strength of its STDERR,
   while attribution then refuses to read that stream. The H3 comment states the split as
   deliberate (*"`out` ... is still what the report and `control_is_green` read; only attribution
   narrows"*) without noticing that the two predicates now answer *"did this suite report?"* and
   *"what did it report?"* from different streams. This repo has recorded **17** instances of a
   second implementation of one rule drifting.
2. **The premise that makes the narrowing safe is a hand grep with no falsifier.** I re-derived
   it and it HOLDS today — `ast`-walked every `print()` call under `scripts/` whose unparsed text
   contains `[FAIL]`: **89 call sites, 89 with no `file=` keyword**, zero `.write` emitters, zero
   `sys.stdout` rebinding to `stderr`, every `redirect_stdout` target a `StringIO` inside a
   self-test, and the one shell emitter (`scripts/ci/start-schema-db.sh:271`) using `echo`
   (stdout) and invoked by no Python guard. But nothing in the repo asserts it. The first guard
   that reports on stderr loses every kill in its file, and the harness blames its report format.

**Fix, smallest first:** make the message's enumeration match its producers — add the third world
(*"or a suite that named its case on STDERR, which attribution no longer reads"*) and say which
stream was searched. Then either make `control_is_green` read the same stream attribution does, or
state in one place which stream is the suite's report. The premise deserves the treatment this
repo gives every other load-bearing enumeration: ~12 lines of `ast`, the 89 producers counted, red
the moment one writes `[FAIL]` to stderr — `check-producer-enumeration.py`'s own shape.

⚠ **Why High and not Blocking:** zero live instances, and the direction is conservative — `ok`
goes False, loudly. ⚠ **Why not Medium:** it is a stated enumeration falsified by its own commit,
and the resulting diagnosis names the wrong subject, which is precisely what H2 was graded High
for three findings earlier in the same round.

## Medium

**M1 — the correction to the F1 width published arithmetic that still adds to THREE. M1's fix
carries M1's own defect.**

`docs/reviews/architecture-review-2026-10-13.md` now says, in the paragraph the fold rewrote:

* heading `:272` — **2 sites, 2 files** (corrected from 3)
* `:282` — "**Two** survive that filter, in two files (⟳ *read three until round 12*):
  `check-plan-code.py:2804` `mut.get("expect")` (fixed by #271 in this session) **and two in
  `check-review-recorded.py`**."  → **1 + 2 = 3**
* `:292` — "the **remaining two sites** are already owned by backlog **#178**" → after the one
  fixed by #271, one site remains, not two.

The enumeration and the dependent count were both keyed to the withdrawn figure and were not moved
with it; the parenthetical `(⟳ read three until round 12)` was inserted immediately beside the
stale "two in". Derived independently: the site removed by the filter is `rec.get("gate_ran")`,
and backlog #178's own row names the two in that file as `:827` `rec.get("dirty")` and `:799`
`rec.get("gate_ran")` — so the survivors are `check-plan-code.py:2804` + `check-review-recorded.py:827`,
which is what the corrected heading says and what the body contradicts.

⚠ **No machine sees this, and one gate's green is specifically not evidence about it.**
`check-withdrawal.py` passes with *"5 figure(s) corrected, and none of them survives elsewhere in
docs/"* — true of the withdrawn figure (`3 sites` / `Three survive`) and structurally blind to the
figures that DEPEND on it, which is where both stale numbers are. `check-docs.py` and
`check-arch-findings.py` are also rc=0.

**Fix:** "and ONE in `check-review-recorded.py` (`:827` `rec.get("dirty")`)" and "the remaining
site is already owned by #178". Leave the `2 callers` sentence alone only if it is re-derived — as
written it inherits the same denominator.

**M2 — `is_exception_heading`'s stated reason why accepting a bare identifier is safe is false, and
the docstring's STATED BOUND is no longer the only bound. Both measured against real CPython
3.12.9 stderr, not read off the parser.**

(a) The new docstring says:

> ⚠ A bare identifier IS accepted (`READY` would pass), and that is deliberate: the *structure*
> rule above is what rejects it, because nothing unindented after a non-frame run is ever
> considered.

The structure rule only rejects it after a **non-frame** run. Give it a genuine frame run with no
heading and `READY` is considered and returned:

```python
# real child: traceback.print_stack(); sys.stderr.write("READY\n")
stderr = '  File "/…/probe.py", line 2, in <module>\n    traceback.print_stack()\nREADY\n'
exception_headings(stderr)  ->  [('READY', False)]
# same shape with traceback.print_tb(...) then sys.stderr.write("DONE\n")  ->  [('DONE', False)]
```

The caller then prints `stderr NAMES READY — in the order the child printed them`. That is H1's
own harm — a fabricated heading — in a narrower world, with a code comment asserting it is closed.

(b) The bound. `ExceptionGroup` yielding nothing is **still true** (re-measured, plain and nested:
`[]` both). It is **not the only one**: a traceback with ZERO frame lines loses a genuinely named
exception, and the caller then says *"stderr names no exception line"* about a stream whose only
content is an exception line.

```python
# real child: sys.tracebacklimit = 0; raise RuntimeError("REAL_KILLER")
stderr = 'RuntimeError: REAL_KILLER\n'
exception_headings(stderr)  ->  []      # also for tracebacklimit = -5
```

⚠ This one is NOT fold-induced — the predecessor returned `[]` here too, because it also required
an indented run. What IS new is the claim written to defend the narrowing: *"CPython emits this
line for every frame it prints … so keying on it loses no real heading."* True of every printed
frame; false of the conclusion, because a heading can be printed with no frames at all.

**Reachability, stated rather than implied, same evidence shape the ExceptionGroup bound already
carries:** `grep -rn 'tracebacklimit' scripts/` → **0**; `grep -rn
'print_tb|print_stack|print_exc|format_tb|format_stack|dump_traceback' scripts/*.py` → **0**. So
neither world is reachable from today's corpus — a bound, not a live defect.

**Fix:** two sentences, no code. Say the bound is *a heading with no frame block of its own is not
seen* (naming both producers and the two zero-counts), and replace the `READY` defence with the
true one: a frame run with no heading hands the next column-zero line to the report.

## Low

**L1 — the empty-stderr message the H2 fix wrote is literally false in the sub-world its own
comment names, and no case asserts that sub-world.** Measured through real `run_mutations`:

```
child: sys.stderr.write(" " * 600 + "\n"); sys.exit(1)
report: "⚠ WHAT THE CHILD ITSELF SAID — the child wrote NOTHING to stderr (601 byte(s)) — which
         rules OUT a traceback this harness can read, and is NOT evidence that the suite ran…"
```

The branch is `if not se.strip():`, and `:2947`'s comment states the sub-world outright — *"a child
that writes only whitespace before exiting 1 lands here too"* — so this was known and the sentence
was still written as `wrote NOTHING`. The byte count is what makes it self-refuting rather than
merely wrong, which is the honest half. Both committed cases (`:3625`, `:3709`) use the genuinely
empty fixture, so the acknowledged sub-world is asserted by nothing.

Second, smaller, same sentence: `se` is a `str` (`text=True`), so `len(se)` is a CHARACTER count
labelled `byte(s)`. `str.strip()` strips Unicode whitespace, so the branch is reachable with
multi-byte content — measured, a child writing three U+3000 ideographic spaces:

```
message says: "the child wrote NOTHING to stderr (3 byte(s))"
actual:        3 characters = 9 bytes
```

**Fix:** `f"the child wrote {len(se)} character(s) to stderr, all whitespace"` for the non-empty
arm and `wrote NOTHING to stderr (0 bytes)` for the empty one — or one sentence that is true of
both, e.g. `nothing but whitespace ({len(se)} character(s))`. Add the whitespace fixture as a
case; it is three lines beside the existing one.

**L2 — the commit body says "All seven touched entries verified individually". The manifest touches
EIGHT. The coverage is fine; the number is not.**

Structural diff of `scripts/mutations/check-plan-code.json` at `5ce6fed2~1..5ce6fed2`, entry by
entry rather than by hunk — in-file 0-based indices `33` (`expect` repointed at the renamed H2
case), `130` (name), `131` (name + edits + expect), `135` (name + edits + expect), and `139–142`
(new). **8 entries, 139 → 143.**

I re-derived the global positions from `load_manifests` + `shard_slice` rather than trusting the
commit (`--shard0 K` → `muts[K]`, stride 1545 selects exactly one) and ran all eight:

| `--shard0` | 1-based | entry | verdict |
|---|---|---|---|
| 623 | 624 | red-with-nothing-readable branch dropped | 1 killed / 1 attributed / 0 survivors |
| 720 | 721 | r11 H1 name corrected | 1 / 1 / 0 |
| 721 | 722 | r11 H1 retargeted + renamed | 1 / 1 / 0 |
| 725 | 726 | r11 H2 retargeted | 1 / 1 / 0 |
| 729 | 730 | r12 H1 FRAME-MARKER clause | 1 / 1 / 0 |
| 730 | 731 | r12 H1 ASCII-only validator | 1 / 1 / 0 |
| 731 | 732 | r12 H3 merged-view attribution | 1 / 1 / 0 |
| 732 | 733 | r12 H2 disclaimer replaced | 1 / 1 / 0 |

The four new entries ARE 1-based 730–733 as stated, and `--shard0` is zero-based as its own case
says. The eighth entry (`623`) is the one the count omits, and it passes too — so this is a wrong
published figure, not a coverage hole. ⚠ Worth saying because the same commit records that the
FIRST run of this verification was off by one: the correction fixed the offset and left the
cardinality.

## Checked and found SOUND

Each of these is something I tried to break and could not; every line was produced by running
something, in the prepared venv (`Python 3.12.9`).

* **Counts.** `--self-test` → **279/279 passed**. `--binding` → **1553 anchor(s) across 1545
  entries**, each resolving to exactly one site, 67 explained `expect`s, no renamed-away `expect`.
  `sum(EXPECTED_MUTATIONS.values())` case passes at 1545; this file's declaration is 143 and the
  manifest holds 143.
* **The "right reason, not an ambient one" question, asked of all EIGHT touched entries** — the
  one the brief flags as having cost four cases this session. I staged `HARNESS_TREE` with the
  harness's own `stage_tree` (missing: `[]`), proved the control green (`279/279`, rc 0), then
  applied each entry's edits and captured the full set of red case names. Every red set is exactly
  the cases about the severed clause, and the named `expect` is in it:
  * `729` → 3 red, all three about the frame marker; expect first.
  * `730` → 2 red, both the non-ASCII pair.
  * `731` → 2 red, both the H3 pair (`caught but NOT attributed`, `REFUSED rather than certified`).
  * `732` → 2 red, the H2 disclaimer pair.
  * `721` → 3 red, all heading-validation cases. `725` → **1** red. `720` → 6, all heading-order.
  * `623` → 9 red (a whole branch deleted), expect among them.
  No fourth ambient-pass case established. In particular `731`'s named case is red because the
  forged `[FAIL]` becomes attributable again, not because the fixture changed shape.
* **H3's premise, re-derived rather than taken.** `ast` sweep of `scripts/**/*.py`: 89 `print()`
  sites whose text contains `[FAIL]`, **all 89 with no `file=`** (stdout); no `.write` emitter; no
  `sys.stdout = sys.stderr`; all 61 `redirect_stdout` targets `StringIO`/local buffers inside
  self-tests; one shell emitter via `echo`, invoked by no Python guard; `run_suite_parts` captures
  the halves separately (`capture_output=True`), so there is no interleaving or buffering path
  between them. The premise holds. (What it lacks is a guard — H1 above.)
* **`_validate` really is uncallable on a verdict.** Ran it: `REQUIRED = {severity, aim,
  fix_induced, disposition}` at `check-review-decision.py:265-271` plus the `component` check, and
  `_validate({"gate_ran": True, "dirty": False, "schema": 1, "review": "…"})` raises
  ``ValueError: finding '?' has no `severity` — refusing``. The arch-review and #178 corrections
  are exactly right on this point.
* **The FRAME_LINE narrowing lost no real heading in any world I could produce.** 17 worlds, all
  REAL CPython children, each graded by the shipped `exception_headings` beside a reconstruction of
  the predecessor: `tracebacklimit=0`, `tracebacklimit=-5`, `print_tb`-only, `print_stack`-only,
  `RecursionError` with `[Previous line repeated …]`, `exec`/`compile` with a synthetic filename,
  `python -c`, `faulthandler` segfault (incl. its unindented `Extension modules:` tail),
  `-W error::DeprecationWarning`, a non-fatal warning followed by a crash, `-X frozen_modules=on`
  import failure, `ExceptionGroup`, nested `ExceptionGroup`, a dotted `pkg.sub.Deep.Err`, a
  digit-containing module part, `Exception ignored in` with no fatal exception, and a
  `SyntaxError` inside an IMPORTED module. **New == old in all 17** — the narrowing changed no
  verdict in any of them. The two gaps I did find (M2) are shared with the predecessor.
* **`is_exception_heading`'s reject direction.** Rejects `0/0 passed`, `[FAIL] a case: got 1 want
  2`, `Extension modules: _x (total: 1)`, `""`, `":x"`, `"a..b: x"`; accepts bare
  `KeyboardInterrupt` and dotted `pkg.mod.CustomError: x`. The dotted-part rule is right for every
  real heading CPython produced above, including `json.decoder.JSONDecodeError` and `m2d.E`.
* **`EXCEPTION_LINE` left no stale citation.** The only surviving mention under `scripts/` is the
  comment at `:3889` that explicitly records the symbol as GONE — which is the code-comment class
  `check-withdrawal` cannot see, and it was corrected in this very commit.
* **Five gates, run.** `check-docs.py` rc=0; `check-arch-findings.py` rc=0 (2/18 criteria, 0
  regressed past baseline); `check-withdrawal.py` rc=0 over 393 documents;
  `check-selftest-counts.py` rc=0 — *"55 script(s) declare a count, every one verified by running
  it"*, which is an independent confirmation of the 279 declaration; `check-anchors.py` rc=0 (13
  registered, floor 22 held). **None of them sees M1**, which is reported as a property of the
  gates, not as reassurance.

## CANNOT RUN

**Treat every line here as NOT RUN, not as a pass.**

* **The full local `--mutate .` sweep.** NOT RUN. Not attempted: shards blow `SUITE_TIMEOUT = 120`
  on this machine, and a scoped run takes ~19s per entry (measured), so the 1545-entry sweep is
  not a laptop operation. **CI is the only authority for the sweep, and I did not replay CI
  either.** What I did run is eight scoped single-entry shards; that is coverage of the touched
  entries and says nothing about the other 1537.
* **`check-test-counts.py --results`** — needs a jest run. NOT RUN.
* **The 26-sites/16-guards figure for backlog #276.** NOT independently reproduced. I verified the
  parts of it that are checkable in isolation (`_validate`, `REQUIRED`) and did not rebuild the
  `ast` finder or re-run the severance sweep, so the population figure and the LOWER-BOUND caveat
  naming `check-anon-exposure.py:631` stand on the fold's measurement alone. ⚠ The brief asked
  specifically whether there are sites the finder cannot see BEYOND `:631`; **I did not answer
  that question**, and the caveat should not be read as reviewed.

## Instruments

Prepared `.venv/bin/python` (3.12.9) with the venv first on `PATH` for the harness's own spawns;
the worktree at `fdb027d3…/wt-backlog`, read-only apart from this file. `load_manifests` +
`shard_slice` driven directly to derive global positions rather than trusting the commit's. Eight
`--mutate . --shard0 K/1545` runs. A staged `HARNESS_TREE` copy under a redirected `HOME` for the
red-set measurements, each mutation applied and reverted around one `--self-test`. `run_mutations`
and `run_suite_parts` called as library functions over purpose-built child suites for the H1/L1
worlds. 17 real CPython children for `exception_headings`, graded beside a reconstruction of the
pre-fold rule. Two `ast` sweeps of `scripts/**/*.py` (the `[FAIL]` producer enumeration; the
`redirect_stdout`/`sys.stdout` rebinding search). `check-review-decision` imported and `_validate`
called on a well-formed verdict. No repository file changed except this review.

## Where I disagree with the Codex half

* **I do not disagree with any finding Codex established.** I reproduced its H1 fixtures as real
  children, its H2 `os._exit(1)` world, and its H3 forged-`[FAIL]` world, and all three behave as
  it reported. Its L1 reading of the two manifest names is right.
* **Its SOUND counts belong to a different tree, and should not be read forward.** Codex recorded
  *"Self-test: 264/264. Binding: 1,549 anchors / 1,541 entries"* — correct for the PRE-fold tree
  it reviewed. The post-fold figures are 279/279 and 1553/1545; a later reader comparing the two
  halves of round 12 will see a mismatch that is scope, not a defect.
* **Where I'd sharpen its H3.** Codex wrote that the exposure *"is inherited, rather than
  introduced by this repair"* and asked for the claim to be narrowed or the child-result contract
  strengthened. The repair chose neither: it narrowed the SOURCE. That closes the forgery and, per
  my H1, opens a third producer on an enumeration the same function states as two — so H3's
  closing sentence turned out to be the load-bearing one and was not acted on.
* **Where I'd sharpen its M1.** Codex established that the three contradictions invalidate the
  published justification. The fold corrected the three it named and left the arithmetic that
  DEPENDED on the withdrawn figure (M1 above) — so M1's own finding class survives its fix, which
  is the fourth consecutive round with that property and is the signal the thrashing arming exists
  to read.
* **One claim of Codex's I could not confirm or refute:** *"All 17 scoped mutation controls
  returned one killed and one attributed: 603,604,605,609,619,623,625,719–728."* Those are
  pre-fold positions and the manifest has since grown by four, so I re-derived mine from
  `load_manifests` instead of re-using the list. Only `623` is common to both, and it passes in
  the post-fold tree.

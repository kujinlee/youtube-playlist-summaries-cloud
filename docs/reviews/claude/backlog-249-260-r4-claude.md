# Round 4, Claude half — the round-4 fold is the fourth consecutive fold-induced defect

**Subject** `git diff e330ca80..5f7bf286 -- scripts/` — re-derived, not taken. HEAD is `5f7bf286`
(the brief said to expect `ea857e4a`; the Codex half's fold had already landed).
**Worktree** `scratchpad/wt-backlog`, branch `backlog-249-260-fixes`, PR #371. Tree clean at start
and unchanged by this review except for this file.
**Interpreter** `python3.12` (3.12.9) throughout. The machine's bare `python3` is 3.14.4 and was
not used for any measurement.

**Verdict: NOT CONVERGED. The round-4 fold is the fourth instance.** 1 High, 3 Medium, 6 Low.
The High and two of the three Mediums are defects *in code `5f7bf286` wrote*, and both of those
Mediums are the same shape the fold's own comments diagnose by name — *instance, not class*. One of
them has its missing class member printed verbatim in the Codex half's own evidence block.

---

## Figures re-derived first (the brief's table, and the brief's own last paragraph)

| claim (brief ll. 216-219, written by the coordinator in the last hour) | re-derived | verdict |
|---|---|---|
| `EXPECTED_MUTATIONS` sums to **1,512** over **62** manifests | declared sum **1512**, 62 keys; disk **1512** entries across 62 `scripts/mutations/*.json` | ✅ |
| suites **86 / 99 / 133 / 237 / 43** | find-claim **86/86**, check-withdrawal **99/99**, check-provenance **133/133**, check-plan-code **237/237**, codex-frontier-model **43/43**, all rc=0 | ✅ |
| `--binding` rc=0 over **1,520** anchors in **1,512** entries | `binding OK — 1520 anchor(s) across 1512 entries`, rc=0 | ✅ |
| `check-fixture-variation.py` rc=0 | rc=0, `908 parameter(s) examined across 67 file(s)` | ✅ |

| claim (brief l. 106, the round-3 range) | re-derived | verdict |
|---|---|---|
| the diff is **625 insertions / 66 deletions over 9 files** | `git diff --shortstat e330ca80..ea857e4a -- scripts/` → `9 files changed, 625 insertions(+), 66 deletions(-)` | ✅ |

The **current** range is larger and the brief does not state it: `git diff --shortstat
e330ca80..5f7bf286 -- scripts/` → **10 files changed, 989 insertions(+), 78 deletions(-)**. The
round-4 fold alone (`ea857e4a..5f7bf286`) is **8 script files, 377 insertions, 24 deletions**.

Also re-derived, from the `mask_inline_code` docstring (its four "measured at `ea857e4a`" lines).
I loaded `git show ea857e4a:scripts/check-withdrawal.py` beside the shipped one and ran
`history_marker` on all four inputs:

| input | old marker | new marker |
|---|---|---|
| ``the count was `anchors: 1,414` today`` | `'was '` | `'was '` |
| ``the count was `anchors:\n1,414` today`` | `''` | `'was '` |
| ``the count was `anchors  \n1,414` today`` | `''` | `'was '` |
| ``the count was `anchors\n1) 1,414` today`` | `''` | `'was '` |

Reproduces exactly. Also re-derived: the five string lengths the three new threshold cases assert
(31, 97, 12, 11, 36) are all correct, and `int(31*0.3)=9`, `int(97*0.3)=29`, `int(97*0.4)=38` —
so `need` is 12, 29 and 38 as the comment says. `_LONGEX` is **55** characters and its literal
`never as done` is **13**, so r4's rename of that case name from *12-char/54-char* to
*13-char/55-char* is the correct repair.

---

## Blocking

None.

---

## High

### H1 — `codex-frontier-model.py`: the four cases the whole H1 fix rests on measure nothing on CI. Severing the probe's world leaves 43/43 green under an empty `HOME`.

**File/symbol** `scripts/codex-frontier-model.py`, `_refusal_code()` (new in `5f7bf286`) and the
four cases it drives.

```python
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "models_cache.json")
        if cache_text is not None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(cache_text)
        CACHE = path
        try:
```

and the fold's claim about them, in `cannot_run`'s own docstring and in the suite comment:

```python
    # ⛔ THIS PINS THE CODE, WHICH IS THE THING THAT WAS WRONG. The four goldens pin the refusal
    # TEXT, and text is exactly what the first fix got right while leaving the code at 1.
```

```python
    case("...and an ABSENT cache does too, so the rule is the module's and not one arm's",
         _refusal_code(None), 2),
```

**Failure scenario.** `CACHE = os.path.expanduser("~/.codex/models_cache.json")` is evaluated at
import. On a machine with **no `~/.codex`** — which is `ubuntu-latest`, and which is also what
`check-plan-code.py`'s `child_env` manufactures for every spawned suite
(`scripts/check-plan-code.py:162`, `env["HOME"] = str(d / CHILD_HOME)`) — removing the line
`CACHE = path` from the probe makes **all four** inputs fall through the
`except FileNotFoundError` arm to `cannot_run(...)`, which exits 2, which is what all four cases
want. The probe stops building its world and the suite does not notice.

**What I ran.** A copy of `scripts/` in `scratchpad/r4/mut` (the repo tree was not touched). Each
mutant was `ast.parse`d before running, and I counted `[FAIL]` lines rather than reading an exit
code through a pipe.

```
control, real HOME        : rc=0  43/43
sever `CACHE = path`, real HOME : rc=1  39/43, 4 [FAIL] lines (all four new cases)
control, HOME=<empty dir> : rc=0  43/43
sever `CACHE = path`, HOME=<empty dir> : rc=0  43/43, 0 [FAIL] lines
```

Also measured, under the real `HOME`: making the probe never *write* the cache file
(`if cache_text is not None:` → `if False:`) leaves **43/43 green, 0 `[FAIL]` lines**. So three of
the four cases — malformed, unparseable, no-candidate — are satisfiable by the *missing-file* arm,
and nothing distinguishes "four arms each exit 2" from "one arm exits 2 and the other three were
never reached". The case name that asserts *"the rule is the module's and not one arm's"* is
precisely the proposition the suite cannot establish.

**Why this is the fold's own class.** The *same commit* added buildability controls to two
`find-claim.py` probes for exactly this reason —

```python
        ("⛔ the chmod-000 world IS buildable here — if THIS fails, the three cases below were "
         "NOT RUN and must not be read as passes (r4: the sibling's missing sentinel)",
         _unreadable_dir_probe()[0] != -1, True),
```

— and wrote `INSTANCE, NOT CLASS` in the comment above one of them. The new
`codex-frontier-model.py` probe has no equivalent: nothing asserts that a *valid* cache makes
`_refusal_code` return its `-1` sentinel, which is the one observation that proves the swap took.

**It also inverts round 3's BLOCKING.** r3's Claude half blocked on `dir_identity` because "a test
whose world only exists on the author's filesystem is a test the author can pass and CI cannot".
This is the same defect with the polarity reversed: the severance is *killed* on the author's
machine (which has a populated `~/.codex`) and *survives* on CI. The declared manifest entry
(`sys.exit(2)` → `sys.exit(1)`) is unaffected — I confirmed it still kills 4 cases under an empty
`HOME` — so the ratchet reports coverage over a probe whose world it cannot see.

**Smallest fix that closes it**: one case asserting `_refusal_code('{"client_version":"1.2.3",
"models":[{"slug":"m","priority":1,"visibility":"list","supported_in_api":true}]}') == -1`. That
single case kills both mutations above on every machine.

---

## Medium

### M1 — `codex-frontier-model.py`: `--write-config` still reports a cannot-run as a violation, with a traceback. Same file, one function over from the arm the fold just fixed.

**File/symbol** `scripts/codex-frontier-model.py`, `write_config()` / `main()`:

```python
    slug = resolve_frontier()
    if args.write_config:
        write_config(slug)
```

`cannot_run`'s new docstring says it is *"The ONE way this module refuses"* and the module
docstring now says it *"Exits **2 — CANNOT RUN** … if the cache is missing, unreadable, malformed,
or yields no candidate"*. `write_config` is outside that enumeration and has no handler at all.

**Failure scenario.** `~/.codex/config.toml` not writable (read-only home, a root-owned
`~/.codex`, a full disk). `docs/plugins.md:136` publishes `--write-config` as the recommended
invocation and `docs/plugins.md:162` names it as *the one sanctioned retry before falling back* —
so this is the arm a reviewer actually runs when the gate is misbehaving.

**What I ran.** A driver in `scratchpad/r4`, in a subprocess so the real exit code is observable,
with a valid cache and `CONFIG` inside a `chmod 000` directory:

```
rc = 1
PermissionError: [Errno 13] Permission denied: '.../locked/config.toml'
has Traceback: True
```

**rc=1 with a traceback** — the exact pairing the fold's own comment calls the defect ("the code
this repository reads as *a violation was found*"), and the exact pairing r3 fixed twice in
`find-claim.py`. `scripts/check-rc-contract.py` is green over this file, so no guard sees it.

Fix is one line: wrap the `write_config` call and route `OSError` through `cannot_run`.

### M2 — `check-provenance.py`: the structural HEAD alternative accepts refs `git rev-parse` rejects, and the sibling it misses was printed in round 3's Codex evidence two lines above the one that got fixed.

**File/symbol** `scripts/check-provenance.py`, `PROVENANCE_RE`'s HEAD arms —
`` `HEAD(?:[~^]\d*)?` `` and `\bHEAD[~^]\d*` — and the comment at `:309-312`:

```python
    # ⟳ r3 Codex MEDIUM — DIGITS ONLY AFTER `~` OR `^`. `` `HEAD[~^]?\d*` `` accepted
    # `` `HEAD123` ``, which `git rev-parse --verify` rejects, and which this branch INTRODUCED
    # (False at 31e8768a, True at e330ca80). Measured against git for each token: `HEAD`,
    # `HEAD~1`, `HEAD~`, `HEAD^` valid and accepted; `HEAD123` invalid and now refused; `HEADS`
```

**Failure scenario — measured, both halves of the pair in one run:**

| token | `PROVENANCE_RE` | `git rev-parse --verify` |
|---|---|---|
| `at HEAD~fiction` | **True** | rc=**128** |
| `at HEAD~1x` | **True** | rc=**128** |
| `at HEAD123` | False | rc=128 |

So the comment's claim of a per-token git correspondence holds for the four tokens it lists and
fails for two it does not. `\d*` matches the empty string, so `HEAD~` followed by *anything*
satisfies the alternative.

**And the class member was in the finding's own output.** `docs/reviews/codex/backlog-249-260-r3-codex.md:203`
and `:216` print, in the Codex half's own evidence block:

```
'at `HEAD123`' True []
'at HEAD~fiction' True []
```

The fold acted on the first line and not the second. That is *instance, not class*, with the class
visible in the same four lines of the review being folded.

**A second, separable half of the same symbol.** The comment at `:274-308` credits the backtick
requirement with curing negation prose — *"It correctly refused `format HEAD` … and then accepted
**"we cannot look at HEAD"**"*, and *"Write `` `HEAD` `` and it counts"*. The second alternative
has no backtick requirement, so the negation class survives for any suffixed HEAD. Measured:

```
'we cannot look at HEAD~1'             provenance=True
'we have not derived this from HEAD~3' provenance=True
'nothing was observed at HEAD^'        provenance=True
```

`git show e330ca80:scripts/check-provenance.py` gives **True** for all three as well, so this half
is *not* introduced by the fold — what is wrong is the comment, which claims a cure it does not
have. Direction is lenient: a row saying *"we could not look at HEAD~1"* passes as sourced.

**Bound, stated honestly:** **0** live instances in `docs/backlog.md`, which is this guard's only
corpus. I scanned every `docs/**/*.md` for `(?<!`)\bHEAD[~^]\d*` and found **10 occurrences across
4 files** — all in `docs/reviews/` and `docs/superpowers/plans/`, none in a backlog row. So this is
a false-accept with no current victim, graded Medium for the comment being wrong about what was
measured rather than for a live miss.

### M3 — `check-provenance.py`: the r4 comment says FOUR witnesses had no case. Measured: FIVE, and the same commit adds five cases.

**File/symbol** `scripts/check-provenance.py:516-518`:

```python
    # ⛔ r4 Codex LOW — FOUR OF THE FIFTEEN WITNESSES HAD NO CASE, so the sentence below ("the
    # witnesses above are kept as cases") was false about a third of them, and a change that made
    # these four worse would have been invisible. Measured: 11 cases over 15 documented witnesses.
```

**What I ran.** `git show ea857e4a:scripts/check-provenance.py | grep -n "⚠ KNOWN"` → **11**
cases; `grep -c` on the shipped file → **16**. Enumerating them against the fifteen witnesses
documented at `:118-124`:

* 10 documented COUNTED witnesses; 6 had a case at `ea857e4a` (`Stage 3`, `Sub-project 2`,
  `item 2 blocked`, `tier 2 users only`, `Python 3 ships`, `Day 2 metrics`). **4 had none.**
* 5 documented MISSED witnesses; 4 had a case (`2 and 3 were red`, `4 from the sweep`,
  `2 in total`, `3 or more rounds`). **1 had none** — `6 that survived`.

So **five of the fifteen had no case**, not four, and the fold adds exactly five. The 11 in
*"11 cases over 15 documented witnesses"* includes `**1 in 60**`, which is **not one of the
fifteen** — the witness list at `:118-124` does not contain it. Coverage before the fold was
**10/15**, not 11/15.

This is #261's class — *wrong in the denominator or the population, never the numerator* — inside
the comment written to close a coverage gap, and the same sentence contradicts itself: *"false
about a third of them"* is 5, while *"FOUR"* is not.

---

## Low

### L1 — `mask_inline_code`'s "TWO BOUNDS, STATED RATHER THAN HIDDEN" is missing the third, and the missing one is the lenient direction.

**File/symbol** `scripts/check-withdrawal.py`, `mask_inline_code()`:

```python
    runs = [m for m in BACKTICK_RUN.finditer(text) if len(m.group(0)) <= 2]
    out = list(text)
    i = 0
    while i + 1 < len(runs):
        open_run, close_run = runs[i], runs[i + 1]
        if len(open_run.group(0)) != len(close_run.group(0)):
            i += 1                      # not a pair; the next run may open one
            continue
```

The pairing rule is *adjacent runs only*. CommonMark's is *the next run of EQUAL length*, skipping
runs of other lengths. Where they differ, `i += 1` discards the opener and promotes the mismatched
run, which can pair two runs that are not a span at all and mask the prose between them. Masking
prose suppresses a sentence boundary, which makes the checker **more** lenient — the direction the
docstring itself calls the one that hides a stale figure.

**Constructed witness**, measured:

```
input   : 'a `b`` c `the count was wrong:\n1,414 anchors` d'
masked  : 'a `b`` c `thexcountxwasxwrong:x1,414xanchors` d'
marker  : 'was '          <- suppressed
```

The runs are `[1, 2, 1, 1]`. CommonMark pairs run0 with run2 (span content ``b`` c ``) and leaves
run3 unpaired, so `wrong:\n` is prose, `(?<=:)\n` fires, and the figure's sentence carries no
marker — a SURVIVOR. The shipped function pairs run2 with run3 and masks the colon boundary.

**Bound, measured over the guard's own corpus.** `docs_files()` returns **393** files; sliced into
`CONTEXT_CHARS` windows that is **54,444** windows. `mask_inline_code` differs from a CommonMark
reference pairing in **44 windows across 13 files**, and in **0** of them does the shipped version
lose a `SENTENCE_SPLIT` boundary the reference keeps. Per *a 0% is usually an instrument*: I ran
the detector against the constructed witness above first and it reports `lost boundaries: [31]`,
so the zero is a real negative and not a dead probe.

Not live, so Low — but the docstring enumerates its bounds explicitly ("fences", "an unclosed
span") and this third one belongs in that list. A caveat headed *stated rather than hidden* that is
incomplete reads as a complete enumeration.

### L2 — the mask also changes the `(?<=[.!?])\s+` alternative, and neither the docstring nor any case says so.

The docstring scopes the fix to the newline alternatives: *"Three of `SENTENCE_SPLIT`'s
alternatives are newline-based"*. Because the mask replaces **all** whitespace inside a span, it
also removes `(?<=[.!?])\s+` matches. Measured:

```
'the version was `v1. 2 build` and 1,414 anchors'  OLD ''  ->  NEW 'was '
'the version was `v1. 2 build 1,414` anchors'      OLD ''  ->  NEW 'was '
```

The new answer is the *correct* one — a `v1. 2` inside a code span is not a sentence end — so this
is a widening in the right direction. But it is a behaviour change in the lenient direction that
is neither stated nor pinned by a case, and the brief's own question #2 asks for it. One case over
a `v1. 2` span would close it.

### L3 — the fold added a backlog row that trips the branch's own `check-provenance`, repeating r3 Claude L4 whose answer was "the row is the thing to fix".

```
$ python3.12 scripts/check-provenance.py --base origin/master     # rc=0
  #263: 1 bolded figure(s), and the row names no commit, ref, path:line or run id. Where was it measured?
WARN — 1 new backlog row carry a bolded figure with no ref, commit or run id saying where it was measured.
```

Row #263 is new in `5f7bf286`. Its bolded figure is `**MEASURED under python 3.12: …**` and the row
names `scripts/find-claim.py` without a line. Row #264, added in the same commit, passes because it
carries `scripts/codex-review.py:1295`. r3's Claude half filed the identical shape against #262 and
concluded *"the guard was right; the row is the thing to fix"*; #262 no longer fires, #263 now
does. Warn-only, hence Low — but the branch ships with its own guard complaining about a row the
branch wrote, which is the state #56's verdict says gets a gate switched off.

### L4 — the three new threshold cases have no manifest entry, unlike all three other fixes in the same fold.

`scripts/mutations/check-plan-code.json` changes by exactly one line in this fold (a case-name
rename) and `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` stays at **127**, while the three
other fixes each bought a manifest entry (`check-withdrawal` 23→24, `find-claim` 24→25,
`codex-frontier-model` 11→12). Existing entries touch `EXPECT_OVERLAP_FLOOR = 12` → `0` and
`need = max(...)` → `need = floor`; nothing covers an adjacent step.

**The cases themselves are sound — I verified every adjacent step dies at the case that names it**,
on a copy of the tree, attributing by `[FAIL]` line (my copy has 3 ambient failures from
`HARNESS_TREE` wanting `supabase/`, so the control is 234/237 and each mutation adds exactly one
new, correctly-named `[FAIL]`):

| mutation | new `[FAIL]` |
|---|---|
| `FLOOR 12 → 13` | *a 12-char literal explains a 31-char expect …* |
| `FLOOR 12 → 11` | *…and an 11-char literal over the SAME expect does NOT …* |
| `FRACTION 0.3 → 0.4` | *a 36-char literal explains a 97-char expect at need=29 …* |
| `FRACTION 0.3 → 0.2` | *a 13-char overlap does NOT explain a 55-char expect …* |

`--diff-coverage e330ca80` is rc=0 (`every non-exempt function changed across 5 file(s) has a
mutation anchored inside it`) and the constants are module-level, so no guard requires this. Low,
and filed for the asymmetry rather than for a hole.

### L5 — `("⚠ KNOWN MISSED — `1 in 60`…", "**1 in 60**", 1)` is mislabelled: the span is COUNTED.

```python
    ("⚠ KNOWN MISSED — `1 in 60`, which is this repo's own phrasing for a false-fire bound",
     "**1 in 60**", 1),
```

Every sibling `KNOWN MISSED` case asserts **0** (a genuine count not seen); every `KNOWN WRONG`
asserts **1** (wrongly counted). Measured: `bolded_figures("**1 in 60**")` →
`['**1 in 60**']`, i.e. **one figure found** — the span *is* counted, via `MULTI_NUM_RE`'s `\d{2,}`
on the `60`, while `single_digit_figures("**1 in 60**")` is `[]`. So the case belongs with the
correct-behaviour cases, not under a `KNOWN MISSED` label whose siblings mean the opposite. It is
also what inflated M3's denominator: this row is one of the 11 and none of the 15.

Pre-existing, not r4 — filed because the brief asks for mislabelled witnesses.

### L6 — the four new `case(...)` calls are tuple-expression statements.

```python
    case("⭐ a MALFORMED cache refuses with 2 — CANNOT RUN, not 1 — and this is the arm whose "
         "comment named rc=1 as the defect while exiting 1",
         _refusal_code('{"client_version":"1.2.3","models":"oops"}'), 2),
```

The trailing comma makes each statement `(case(...),)` — a 1-tuple built and discarded. Every other
`case(...)` in the same function ends without one (e.g. the golden case three lines above). Works
today; it is the shape a later line-continuation changes silently, and it is evidence the block was
pasted out of a list context.

---

## Checked and found SOUND

Each of these I examined and cleared, with what I ran.

* **`figure_offsets_in_hit` + the caller's `all(...)` at zero occurrences — NOT reachable.** The
  function ends `return out or [0]`, so the list is never empty and `all([])` cannot be reached.
  There is a case for it (`figure_offsets_in_hit("no number here", "1,414")` → `[0]`). The
  caller at `:1069` is `all(is_history_context(...) for a in ats)` over that non-empty list.
* **The 5-tuple return of `collect_files`.** All 11 call sites unpack five values
  (`grep -n "collect_files("`): `:527 :576 :579 :581 :657 :680 :788 :839 :841 :843 :846 :1073`,
  every one with five names or five subscripts. No caller unpacks four.
* **`dir_identity`'s shape case can fail on both filesystems.** It asserts
  `(isinstance(i, tuple), len(i), all(isinstance(x, int) for x in i)) == (True, 2, True)` over
  `dir_identity(Path("."))`. Under the `resolve()`-string mutation every component changes, with
  no dependence on case sensitivity. The behavioural alias case is explicitly labelled a
  regression guard and not the discriminator.
* **`_nonfile_entry_probe` asserts something non-trivial.** `dangling.md` carries a `.md` suffix
  and `suffixes is None`, so if the `continue` did not fire it would be appended and
  `len(files)` would be 3, not 2. The branch is genuinely exercised: `os.walk` puts a dangling
  symlink in `filenames`, and `Path.is_file()` returns False without raising (confirmed under
  3.12 — this is the fact backlog #263 rests on, and it is correct).
* **Every chmod is restored on every path.** `_unreadable_dir_probe`, `_top_level_named_probe`
  and `_metadata_failure_probe` all put the `chmod` back in a `finally:` that sits inside the
  `TemporaryDirectory` context, so restore precedes cleanup. The `-1` sentinel returns are inside
  the `try`, so they do not skip it.
* **All three chmod probes have a buildability case** — `grep "IS buildable here"` returns 3 hits
  (`:910`, `:924`, `:943`), covering `_unreadable_dir_probe`, `_metadata_failure_probe` and
  `_top_level_named_probe`. My first hypothesis was that the metadata probe had been left out; it
  had not. (The gap in this class is H1, in a different file.)
* **The self-granted-pass class search, widened past the brief's `access(.*R_OK)`.** I searched
  `os.access`, `geteuid`, `shutil.which` and `^def _.*probe` across all of `scripts/`. Three
  `R_OK` sites, all in `find-claim.py`, all now returning `(-1, False, False)`. One other member
  of the class: `scripts/check-banner-armed.py:1695` registers a case only `if _os.geteuid() != 0`
  — a case that *disappears* as root rather than passing falsely. Declared in its own comment,
  outside this range, not filed.
* **`cannot_run` is the only refusal path in its module.** `grep -n "sys.exit\|cannot_run"` shows
  `sys.exit` surviving at exactly two places: inside `cannot_run` itself, and
  `sys.exit(_self_test())`. All four cache arms route through it. (M1 is an *unhandled* OSError,
  not a second refusal mechanism.)
* **`_refusal_code`'s global swap does not leak.** `CACHE = saved` is in a `finally`, and
  `e.code if isinstance(e.code, int) else 1` means a future `sys.exit(<string>)` regression scores
  1 and fails the case. The goldens that normalise `str(CACHE)` are unaffected — the suite is
  43/43 both before and after the four new cases in file order.
* **The declared manifest entry for H1 is honest.** `    sys.exit(2)` occurs exactly once in the
  file, and mutating it to `sys.exit(1)` kills 4 cases under the real `HOME` **and** under an
  empty `HOME`. The ratchet entry works; H1 is about the probe's world, not this entry.
* **`cannot_run`'s `NoReturn` annotation and the `from typing import NoReturn` import.** Correct
  for 3.12, no runtime effect, and `tsc`/`mypy` are not run over `scripts/`. `codex-review.py`
  imports the module via `import_module("codex-frontier-model")` and binds
  `resolve_candidates` only — the new name does not collide. The caller-side silence is
  already filed as backlog #264 and I agree with that scoping.
* **Backlog #263's reasoning, which the brief asked me to argue against.** I cannot make the other
  side work. Exiting 2 on a non-file entry would make any repository containing one dangling
  symlink permanently CANNOT RUN, and the walk cannot distinguish *vanished* from *never existed*
  without a second stat that races. The row's framing — correct the comment, pin the behaviour,
  file the policy question — is right. One thing the row does not say and could: a **named**
  dangling symlink already *is* CANNOT RUN (`collect_files`' final `else:` returns *"neither a
  file nor a directory"*), so the asymmetry is between named and discovered paths, not between
  "exit 2" and "exit 0".
* **Three new `SENTENCE_SPLIT` boundaries each have a discriminating case** — the colon lead-in,
  the hard break and `1)` — plus the `⛔ r4` case asserting the colon rule still fires *outside* a
  span, which is what stops the mask from being a quiet revert of r3. Verified by the old/new
  table above: all three flip.
* **The tightened HEAD pattern's intended behaviour.** `measured at `HEAD`` True,
  `we cannot look at HEAD` False, `measured at HEAD` False, ``HEAD123`` False, ``HEADS`` False,
  ``HEAD^`` True, ``HEAD~1`` True. Consistent with its documented design; M2 is about the two
  tokens it did not measure and about the negation claim.
* **`single_digit_figures` as a heuristic.** Not filed as imprecise — that is declared. All 15
  documented witnesses now have a case (M3 is about the count in the comment, not the coverage).
  I checked whether the heuristic is load-bearing anywhere it is treated as exact: its only
  consumer is `bolded_figures` → `findings_for` → `verdict`, which is warn-only unless
  `--strict`, and the shipped run over the branch is rc=0 with one WARN. Nothing treats it as
  exact.
* **The repo's own guards over this tree**, all under `python3.12`:
  `check-withdrawal` rc=0 · `check-provenance` rc=0 (1 WARN, see L3) · `check-selftest-counts`
  rc=0 (55 scripts, every declared count verified by running it) · `check-ratchet-contract` rc=0 ·
  `check-rc-contract` rc=0 · `check-docs` rc=0 · `check-main-drivable` rc=0 ·
  `check-gate-falsifiability` rc=0 · `check-fixture-variation` rc=0 ·
  `check-plan-code --binding` rc=0 · `check-plan-code --diff-coverage e330ca80` rc=0.
* **`check-review-rounds` is rc=1 and that is expected, not a finding**:
  `✗ backlog-249-260 round 4: only codex — claude neither ran nor recorded a REVIEW GAP:`. This
  file is the missing half; it closes on commit.

---

## CANNOT RUN

Three things I could not measure, stated so they are not read as passes.

1. **The full `--mutate .` sweep.** Not run — it is the whole 1,512-entry harness and does not
   finish inside this review's budget. Every mutation result above was taken by hand on a **copy**
   of `scripts/` in the scratchpad, never on the worktree, each mutant `ast.parse`d first and each
   kill attributed to a named `[FAIL]` line. **Treat "the sweep is green" as NOT MEASURED by this
   half.** H1 in particular predicts a *surviving* mutation that is not in the manifest, so the
   sweep going green would not refute it.
2. **A case-sensitive filesystem.** This machine is case-insensitive APFS. H1's CI behaviour was
   established by redirecting `HOME` to an empty directory, which reproduces the relevant
   property (`~/.codex` absent) but not case sensitivity. The `_case_alias_probe` cases are, as
   their own comment says, non-discriminating here and I could not exercise them the other way.
3. **The CommonMark reference in L1 is mine, not a parser.** I implemented
   "pair with the next run of equal length" rather than running `cmark`, which is not installed.
   The 44/0 figures are relative to that reference. The constructed witness in L1 does not depend
   on it — the shipped function masking `wrong:` out of prose is directly observable.

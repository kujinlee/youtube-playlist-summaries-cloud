# Adversarial review — `harness-progress-output`, round 3 (Claude half)

**Status: COMPLETE.** Verdict **NOT CONVERGED** — 1 Blocking, 2 High, 1 Medium, 1 Low.

## Proof of subject

`git log --oneline origin/master..HEAD`:

```
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes
```

`git show --stat 5e4bd163`:

```
commit 5e4bd163c6287ad8559f642aadfcda45473a9060
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Fri Sep 11 03:45:52 2026 -0700

    Round 2: a guard whose want moves with its subject has no ceiling

 docs/dashboard-entries.md                          |  33 +-
 docs/reviews/claude/harness-progress-r2-claude.md  | 389 +++++++++++++++++++++
 .../coordinator/harness-progress-r2-codex.md       |  74 ++++
 .../harness-progress-r2-codex.verdict.json         |  16 +
 scripts/check-plan-code.py                         |  85 ++++-
 scripts/mutations/check-plan-code.json             |  34 +-
 6 files changed, 622 insertions(+), 9 deletions(-)
```

Branch `harness-progress-output`, working tree clean at review start.

## Control, proved green FIRST

In the repo:

```
$ python3 scripts/check-plan-code.py --self-test
114/114 passed      rc=0      stderr: 0 bytes
```

In the isolated staging tree (`scripts/` copied, `supabase` `docs`
`node_modules/typescript` `.claude/hooks` symlinked, `$HOME` redirected to an empty
scratch dir — per the brief's `HARNESS_TREE` rule):

```
$ cd <staging>/tree && HOME=<staging>/fakehome python3 scripts/check-plan-code.py --self-test
114/114 passed
```

Every verdict below is over that proved-green control, applying one edit at a time to
the staged copy and restoring it afterwards. The repo itself was never modified.

---

# Verdict: **NOT CONVERGED**

---

## BLOCKING 1 — B1's fix pinned the CONSTANT and left the THRESHOLD open. The progress line can still be made to wrap, at 114/114.

**This is the eighth instance of the class, and — exactly as the brief feared — it is
inside B1's own fix.**

### The premise

`scripts/check-plan-code.py:1193`

```python
PROGRESS_WIDTH = 79
```

`scripts/check-plan-code.py:1221-1225` — the whole of `progress_line`'s body:

```python
    head = f"[{done}/{total}] "
    room = PROGRESS_WIDTH - len(head)
    if len(label) <= room:
        return head + label
    return head + label[:max(room - 1, 0)] + "…"
```

The two cases that guard it, `scripts/check-plan-code.py:2436-2441`:

```python
    _pl_long = progress_line(164, 434, "x" * 300)
    case("a label too long for one row is truncated, and says so",
         (len(_pl_long), _pl_long[-1], _pl_long.startswith("[164/434] ")),
         (79, "…", True))
    case("...and a label that already fits is left exactly alone",
         progress_line(164, 434, "y" * 40), "[164/434] " + "y" * 40)
```

plus one more call site, `scripts/check-plan-code.py:2380`:

```python
         progress_line(7, 38, "check-docs.py"), "[7/38] check-docs.py")
```

### What B1 actually fixed, and what it did not

B1 replaced `want=(PROGRESS_WIDTH, …)` with `want=(79, …)`. That works, and I confirmed
it in four directions over the green control — including ±1, which is the direction a
derived want could never see:

| edit | result |
|---|---|
| `PROGRESS_WIDTH = 200` (the manifest entry) | **113/114**, red via `a label too long for one row is truncated, and says so` |
| `PROGRESS_WIDTH = 80` | **113/114**, red via the same case |
| `PROGRESS_WIDTH = 78` | **113/114**, red via the same case |
| `PROGRESS_WIDTH = 40` | **112/114**, red via that case **and** `...and a label that already fits is left exactly alone` |

So the *constant* now has a ceiling and a floor. **The property r1 M2 was filed for is
not the constant — it is "an emitted progress line occupies one terminal row"** — and
that property is decided by the comparison on line 1223, which no case exercises near
its boundary. `room` is `79 - len("[164/434] ")` = **69**. The only label lengths the
suite ever passes through `progress_line` are **4, 13, 40 and 300**. The boundary is at
69/70, and nothing is measured between 40 and 300.

### The measurement — survivors over the green control

```
== off-by-one WIDER at the fits/truncate BOUNDARY
   if len(label) <= room:  ->  if len(label) <= room + 1:
   rc=0   114/114 passed   redcases=[]

== boundary +20 (a 20-char overhang never truncates)
   if len(label) <= room:  ->  if len(label) <= room + 20:
   rc=0   114/114 passed   redcases=[]

== boundary strict (<)
   if len(label) <= room:  ->  if len(label) < room:
   rc=0   114/114 passed   redcases=[]
```

Three survivors. The control for each was the 114/114 run above; each edit was applied
alone and reverted. For contrast, an edit to the *other* line of the same body **is**
caught, which is what proves the harness was working and the hole is specific:

```
== room ignores head length
   room = PROGRESS_WIDTH - len(head)  ->  room = PROGRESS_WIDTH
   rc=1   113/114   redcases=["a label too long for one row is truncated, and says so"]
```

### The harm is not hypothetical — 82 of the 445 real labels land in the hole

The labels are mutation names (`run_mutations` passes `mut["name"]` to the reporter,
`scripts/check-plan-code.py:980`). Measured over every entry in `scripts/mutations/*.json`
at this commit, against `room = 69`:

```
total mutation labels: 445
   249  fits (<=69)                          — unaffected
     6  exactly 70                           — wrap under a bare off-by-one (`room + 1`)
    82  70..89                               — wrap under `room + 20`
   108  90+                                  — still truncated even at +20
longest label: 232
```

Under `room + 1`, six real runs emit an **80-character** line: one column over a standard
terminal, which is the wrap. Under `room + 20`, **82 of 445 (18%)** emit lines of up to 99
characters. In both cases the suite reports **114/114 passed** and `--mutate .` reports
zero survivors, because no manifest entry edits that line and no case has a label near it.

### Why this is the same class B1 was, one level in

B1's diagnosis, quoted from the commit message, is: *"Counting is not enough; ask whether
the want can differ from the subject."* Applied to the fixed case, the want (`79`) now
genuinely differs from the subject — for the **constant**. But the case's *input* is
`"x" * 300`, chosen to be unambiguously past the threshold, so the case asserts **"a label
300 characters long comes back 79 wide"**. That is true of every threshold between 1 and
299. The ceiling moved from the constant to the comparison and stayed unguarded; the fix
relocated the hole rather than closing it.

The commit's own framing — *"a literal cannot move with the subject, and the manifest
entry that widens the constant dies here"* — is accurate and insufficient. Widening the
**constant** dies. Widening the **line** does not.

### Fix

Case the threshold, not just the far side of it. Two cases with literal wants, both
using labels the current suite never produces:

- a label of exactly `room` characters is returned untouched (pins the `<=` and kills `<`);
- a label of exactly `room + 1` characters is truncated to 79 and ends `…` (pins the `+1`
  survivor, and by construction every wider overhang).

Both want literals, neither derived from `PROGRESS_WIDTH` or `room`. Then add one manifest
entry (`<= room` → `<= room + 1`) naming the second case, so the coverage is held by CI
rather than by a case count.

---

## HIGH 1 — M1's swap RE-CREATES r1 F7's harm for 28 of 38 suites, and the case written to prevent that is green in both worlds.

### The claim under test

`scripts/check-plan-code.py:1409-1412` (the comment M1 added to `run_suite`):

```python
    # ⚠ AND THIS DOES NOT UNDO r1 F7 (2026-09-09), which restored the stderr half because "a
    # control that dies on a TRACEBACK says so only on stderr". That case is a crash BEFORE the
    # suite prints — stdout is empty or short, so the window still reaches into stderr and shows
    # the traceback's end. Both cases are pinned below; neither stream can empty the other's.
```

and the commit message: *"Both ends are now cased, so neither stream can empty the other's
window."*

**Both sentences are false.** Only one end is cased, and it is the end where the order
cannot matter.

### Measurement 1 — the swap is a strict loss on crash-AFTER-output

Three fixtures, each run through a real subprocess, with the two concatenation orders
computed from the *same* `CompletedProcess` so nothing else differs. `control_is_green`
and the `out[-400:]` window are the real functions, imported from the staged tree:

```
--- A crash BEFORE output (the case the commit added)   (stdout 0 B, stderr 237 B, rc 1)
  NEW stderr+stdout: green=False why-in-window=True  tail='RuntimeError: the tree went bad underneath'
  OLD stdout+stderr: green=False why-in-window=True  tail='RuntimeError: the tree went bad underneath'

--- B crash AFTER 800 B of stdout                        (stdout 832 B, stderr 237 B, rc 1)
  NEW stderr+stdout: green=False why-in-window=False tail='XXXXXXXXXXXXXXXXXXXXXXXXXXXX…'
  OLD stdout+stderr: green=False why-in-window=True  tail='RuntimeError: the tree went bad underneath'

--- C crash AFTER 20 [FAIL] lines (a control dying mid-suite)  (stdout 750 B, stderr 237 B, rc 1)
  NEW stderr+stdout: green=False why-in-window=False tail='  [FAIL] case number 19: got 0 want 1'
  OLD stdout+stderr: green=False why-in-window=True  tail='RuntimeError: the tree went bad underneath'
```

Row A is the shape the commit cased — and it is **identical under both orders**, because
stdout is empty. Rows B and C are the shape it did not case, and there the new order
deletes the traceback from the only window a reader is shown.

`out[-400:]` has exactly two consumers, `scripts/check-plan-code.py:912` and
`scripts/check-plan-code.py:944` — both are the `CANNOT RUN — control … did not prove the
suite works` message. So the window's *only* job is explaining a red control, and a
traceback is the most common reason a control is red for a reason other than its own cases.
That is verbatim the harm `scripts/check-plan-code.py:1342-1344` records r1 F7 as having
been filed for:

```python
    # `out[-400:]` tail, and a control that dies on a TRACEBACK says so only on stderr. Losing it
    # turns "the control was red, here is why" into "the control was red" — the diagnostic that
    # makes a red actionable rather than merely true.
```

### Measurement 2 — the affected population is 28 of 38, not an edge case

The 38 mutation targets, each run `--self-test` at this commit, green:

```
suites whose GREEN stdout already exceeds the 400-char window: 28 of 38
```

Worst offenders: `check-paid-caller-arrival.py` **16,701 B**, `gen-backlog-page.py`
**10,563 B**, `check-live-schema.py` **9,600 B**, `brief-compose.py` **9,001 B**,
`check-banner-armed.py` **7,278 B**. For any of those, a crash after the suite has started
printing puts the traceback 9–16 KB outside the window.

For symmetry I measured the population the swap *helps*: only **2 of 38** suites
(`begin-plan.py` 3,807 B, `check-banner-armed.py` 6,268 B) write any stderr at all on a
green run — and for those two `control_is_green` is True, so the window is never printed.
The synthetic 600-B-stderr flooder in M1's motivating measurement has **no counterpart in
the real corpus**. The fix optimised for a fixture and regressed the population.

### Measurement 3 — the guarding case cannot see the thing it is named for

`scripts/check-plan-code.py:2422-2426`:

```python
        (_wdp / "broken.py").write_text('raise RuntimeError("the tree went bad underneath")\n')
        _brc, _bout = run_suite(_wdp, "broken.py")
        case("a suite that dies before printing still shows its traceback in the window",
             (_brc, "the tree went bad underneath" in _bout[-400:]), (1, True))
```

Applying the manifest's own reversal to the staged tree:

```
== revert to stdout-first:  (r.stderr + r.stdout)  ->  (r.stdout + r.stderr)
   rc=1  112/114
   red: "600 B of child stderr cannot push the failure out of the 400-char window"
        "...and the recorded tail is the failure, not the noise"
```

`a suite that dies before printing still shows its traceback in the window` **stays green**.
Its fixture emits zero stdout, so `stderr + stdout` and `stdout + stderr` produce the same
string. The case is green in every ordering; it dies only when the stderr half is *deleted*,
which is what the other entry already tests. It therefore contributes nothing to the
"both ends are pinned" claim it was written to support — a premise fixed without the branch
being covered.

### Fix

The ordering is a genuine trade and one concatenation cannot serve both readers. Either:

- **(a)** stop deciding it by concatenation order: keep the two streams separate and build the
  diagnostic explicitly, e.g. `stderr[-200:] + stdout[-200:]`, or label them — then both are
  in the window regardless of volume; or
- **(b)** keep the swap and case the loss honestly: add a crash-**after**-output fixture whose
  stdout exceeds 400 B, assert what the window is *expected* to contain, and correct the two
  sentences that currently claim the crash case is covered.

Option (a) also removes the need for the flooder's magic 600 vs the window's 400.

---

## HIGH 2 — the three new cases re-derive the properties they are named for, so neither production site is guarded. The commit's claim that the fix "reached" `ev_files[…]["tail"]` is false.

### The claim under test

Commit message, on M1:

> `ev_files[name]["tail"]` records `out.split("\n")[-1]`, so the DURABLE evidence object
> also lost the failure. **r1 listed that field under "not measured" and the fix did not
> reach it.**

— written to say that r2's fix *does* reach it. And the case is named for it,
`scripts/check-plan-code.py:2417-2419`:

```python
        case("...and the recorded tail is the failure, not the noise",
             _nout.split("\n")[-1].strip(), "[FAIL] the value is one")
```

### The defect

That case never touches `ev_files`. It recomputes `out.split("\n")[-1]` — a **second
implementation** of the production line — and asserts on its own copy. Same for the window:
`scripts/check-plan-code.py:2415` and `:2426` both write their own `[-400:]` rather than
reading the production constant.

The production sites are `scripts/check-plan-code.py:906`, `:912` and `:944`:

```python
            ev_files[name] = {"rc": rc, "tail": (out.split("\n")[-1] if out else ""),
                              "blocks": None}
...
                              f"CHECKED.\n    {out[-400:]}")     # :912
...
                    f"CHECKED.\n    {out[-400:]}")               # :944
```

### Measurement — both survive over the green control

```
== PRODUCTION tail :906   out.split("\n")[-1]  ->  out.split("\n")[0]
   rc=0   114/114 passed   redcases=[]

== BOTH production windows :912 and :944   out[-400:]  ->  out[-40:]
   rc=0   114/114 passed   redcases=[]
```

The durable evidence object can be made to record the **first** line of a control's output
instead of the last, and the CANNOT RUN diagnostic can be cut from 400 characters to 40, and
the suite reports **114/114** for both. `ev_files[…]["tail"]` is in exactly the state r1
recorded it in — *not measured* — and this commit added a case named for it that cannot see
it.

What the three new cases *do* guard is real and worth keeping: the concatenation order inside
`run_suite`. Both manifest entries attribute correctly, which I verified rather than assumed
(brief item 5):

```
== F7 RETARGETED: (r.stderr + r.stdout).strip() -> r.stdout.strip()
   rc=1  112/114  red: ["run_suite keeps BOTH halves, so a control's traceback survives into the report",
                        "a suite that dies before printing still shows its traceback in the window"]
== NEW entry:    stderr-first -> stdout-first
   rc=1  112/114  red: ["600 B of child stderr cannot push the failure out of the 400-char window",
                        "...and the recorded tail is the failure, not the noise"]
```

Each `expect` name matches exactly one red case — the rule at
`scripts/check-plan-code.py:1075` (`unnamed = [(w, m) for w, m in unnamed if len(m) != 1]`),
not the weaker "any named hit" the author's own verifier used. Both entries pass the real rule.

### Fix

Assert on the production values, not on copies:

- have the tail case call the code path that builds `ev_files` (or extract the one-liner into
  a named function both the producer and the case call, the way `parse_fail_names` was
  extracted in r2 M2 for exactly this reason);
- give the window a named constant (`DIAGNOSTIC_WINDOW = 400`) used at `:912`, `:944` and in
  the cases — and then pin the *case's* want to a literal, so the B1 lesson is not undone in
  the process.

Either way, add a manifest entry for `:906` so the field stops being held by nothing.

---

## MEDIUM 1 — the `": got "` fix is instance-not-class, and the docstring that frames it warns about the one direction that is SAFE.

### The parser

`scripts/check-plan-code.py:1286-1287`:

```python
    return [l.strip()[7:].rsplit(": got ", 1)[0].strip()
            for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```

Its docstring, `scripts/check-plan-code.py:1267-1269`:

```
    ⚠ SO A CASE NAME CONTAINING `": got "` IS TRUNCATED, and its manifest entry becomes
    unattributable — §22's disease inside the machinery built to prevent it. Zero of the live
    case names contain it today. This function is where that fact is visible.
```

### Both sentences are wrong, measured

Run against the canonical producer at `scripts/check-plan-code.py:1284`
(`f"  [FAIL] {name}: got {got!r} want {want!r}"`):

```
A. a case NAME containing ': got ', in a REAL report line
   line   :   [FAIL] the width: got the wrong value: got 1 want 2
   parsed : ['the width: got the wrong value']
   CORRECT: True

B. the live case at :2532, whose own NAME contains ': got '
   parsed : ["⚠ a case name containing ': got ' is TRUNCATED by the consumer"]
   CORRECT: True

C. a VALUE containing ': got '
   line   :   [FAIL] some case: got '[FAIL] the value is one: got 99' want 'x'
   parsed : ["some case: got '[FAIL] the value is one"]
   CORRECT: False
```

`rsplit(…, 1)` takes the **last** occurrence, and a name is always **before** the real
separator — so a `": got "` in a name is harmless by construction. The hazard is
one-directional, and it is the value direction, which the docstring does not mention.
Meanwhile **1 of the 114 live case names does contain the token** (the case at `:2532`),
which refutes "Zero of the live case names contain it today" — and it parses correctly,
which refutes the warning. I measured the name corpus by instrumenting `case()` in a staged
copy to record every `(name, repr(got), repr(want))` triple; the instrumented suite still
reported 114/114 and wrote 114 records.

The case that is supposed to demonstrate the claim, `scripts/check-plan-code.py:2532-2533`:

```python
    case("⚠ a case name containing ': got ' is TRUNCATED by the consumer",
         parse_fail_names("  [FAIL] the width: got the wrong value"), ["the width"])
```

feeds a line with **no `want` clause** — a shape the producer at `:1284` cannot emit. The
case is green and unfalsifiable with respect to the sentence it is named for.

### The class, and whether a guard is warranted (brief item 6)

Over the 114-case corpus of this suite, **0 values now carry the token** — the fixture fix is
complete *for this file*. But the harness parses the output of **all 38** target suites. Static
scan across them: 61 non-comment lines contain `": got "`; after removing each file's own
producer and the parser itself, **33 candidate lines in 16 files** remain. Two live shapes are
genuinely exposed:

- `scripts/check-test-counts.py:367` —
  `print(f"  [FAIL] {name}: got unexpected {type(exc).__name__} ({exc}) want no exception")`.
  `{exc}` is an arbitrary exception message; one containing `": got "` misparses the name.
- `scripts/check-plan-code.py:1586`, `:1745`, `:1837`, `:2027`, `:2059` — five fixtures whose
  *generated child* prints `[FAIL] …: got …`. The r2 defect was one case asserting on such a
  child's output as its `want`. Nothing stops the sixth.

**Yes, a guard is warranted, but it cannot be added without fixing the parser** — a round-trip
case (`parse_fail_names(report_line(n, got, want)) == [n]` for a value carrying the token) goes
red today, as measurement C shows. The honest sequencing is: make the producer/parser pair
unambiguous first (put the name alone on the line, or split on the *first* `": got "` now that
the name direction is proven safe), then add the round-trip case and a manifest entry. The
commit's own note — *"the parser's asymmetry is untouched and is worth raising separately"* —
is right; this finding is that raising, plus the correction that the docstring points the wrong
way.

---

## LOW 1 — `stderr_progress` cannot raise, but under a non-UTF-8 stderr the line is 84 columns, which breaks the one-row property anyway (brief item 7).

Round 2 flagged the `…` as pre-existing-in-class and did not act. **On "can it raise", round 2's
outcome is right and I agree** — but not for the reason available to it. `sys.stderr` uses the
`backslashreplace` error handler by default, so the character can never raise on the real stream:

```
$ python3 -c "import sys; print(sys.stderr.errors)"
backslashreplace

env LC_ALL=C                      -> stderr encoding utf-8   stderr_progress: OK
env LC_ALL=C PYTHONCOERCECLOCALE=0-> stderr encoding utf-8   stderr_progress: OK
env PYTHONIOENCODING=ascii        -> stderr encoding ascii   stderr_progress: OK
env PYTHONIOENCODING=ascii PYTHONUTF8=0 -> stderr encoding ascii  stderr_progress: OK
```

What it does instead is degrade:

```
$ PYTHONIOENCODING=ascii python3 -c "…; m.stderr_progress(164,434,'x'*300)"
[164/434] xxxxxxxx…xxxx…
COLUMNS emitted: 84
```

`PROGRESS_WIDTH` counts **Python characters**; a terminal counts **columns after encoding**. The
`…` costs 1 character and 6 columns under `backslashreplace`, so every truncated line is 84
columns — it wraps, which is the defect r1 M2 was filed for. 40 of the 445 real labels are
themselves non-ASCII, and the widest such line escapes to 84 columns too.

`PYTHONIOENCODING=ascii` is rare, and `LC_ALL=C` is *not* enough to trigger it (measured above),
so this is Low. If it is ever worth closing, the fix is `"..."` rather than `"…"`, which is
ASCII and costs 2 more characters of label.

### Supporting measurement — the property does hold today

From the live `--mutate .` run's own stderr, 227 emitted progress lines at this commit:

```
max CHARACTER width: 79    min: 24
lines WIDER than 79 chars      : 0
lines truncated (end with …)   : 92  (40%)
lines at exactly 79 chars      : 94
max BYTE width                 : 83
```

The shipped behaviour is correct. Blocking 1 is about the guard, not the behaviour — and note
**2 of those lines sit exactly at the untruncated boundary**, so the threshold Blocking 1
describes is exercised on every real run, not theoretically.

---

## What the commit claims that I independently CONFIRMED

Re-measured rather than read, in a fourth staging tree under a redirected `$HOME`, byte-identical
to `5e4bd163`:

| Claim | Verdict |
|---|---|
| suite **114/114** | ✅ `114/114 passed`, rc 0 |
| nested self-test stderr **0 B** | ✅ `wc -c` on the captured stderr = **0** |
| `EXPECTED_MUTATIONS` sum **445** | ✅ declared sum 445; actual manifest total 445 |
| `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` **50** | ✅ `check-plan-code.json` holds exactly 50 entries |
| `--mutate .` = 38 files, 445 mutations, 445 killed, **445 attributed**, 0 survivors | ✅ verbatim: `OK — delivered scripts mutated: 38 file(s), 445 mutation(s), 445 killed, 445 attributed to the case each names, 0 survivor(s)` |
| the `": got "` fixture fix restores attribution | ✅ 445/445 attributed, up from the 444 the commit reports |
| B1: the width want no longer moves with the subject | ✅ red at 200, 120, 100, 90, 80, 78, 40 — the constant is pinned both ways |
| both touched manifest entries attribute | ✅ each `expect` name matches exactly one red case under the real rule at `:1075` |
| `check-selftest-counts.py` | ✅ green on the subject: *34 script(s) declare a count, every one verified by running it* |

The full `--mutate .` took ~8 min wall clock rather than the commit's `real 365.66`, because a
second 445-mutation run was executing on the same machine throughout. That affects timing only —
no shared database, no shared temp root, separate `$HOME`s — and no mutation timed out (`rc 2`
appears nowhere in the run).

## ⚠ Subject integrity — read this before comparing my numbers to the working tree

`git status` was clean when I started and `114/114` matched. **Partway through this review the
repo's working copy of `scripts/check-plan-code.py` acquired 148 uncommitted insertions**
(`git diff --stat HEAD` = `148 insertions(+), 36 deletions(-)`), introducing `DIAGNOSTIC_WINDOW`,
`diagnostic_tail()` and `run_suite_parts()` — i.e. someone is already implementing option (a) of
High 1 while I write. `HEAD` is still `5e4bd163`.

Every measurement above was taken in a staging tree copied from the repo and verified
`cmp`-identical to `git show 5e4bd163:scripts/check-plan-code.py`:

```
  r3-tree:            IDENTICAL to commit 5e4bd163
  full (--mutate .):  IDENTICAL to commit 5e4bd163
  repo working tree:  DIFFERS from the commit
```

So the findings are about the subject. One consequence worth naming so nobody re-files it: running
`--self-test` **in the repo** now prints `121/121 passed` plus
`[DRIFT] the docstring declares 114 cases; the suite ran 121`. **That is the uncommitted
work-in-progress, not `5e4bd163`** — the same command in the staged copy of the commit is
`114/114 passed` with no drift line, and `check-selftest-counts.py` is green there. I mention it
only because a reader running the command today will see a red that is not this commit's.

(Also observed while isolating that: the WIP's case count is data-driven over `docs/` — creating
this review file alone moved the repo run from 121 to 122. Not a finding against `5e4bd163`; worth
a look before the WIP is committed, because a suite whose case count tracks the documents in the
repo cannot have a stable declared count.)

---

## What the author did not measure (brief item 8)

1. **The truncation THRESHOLD** — only the constant and the far side of the branch. Three
   surviving mutations, Blocking 1. The commit measured `PROGRESS_WIDTH` at 40/80/90/100/120/200
   and concluded the guard now has a ceiling; it never varied the *label length*, which is the
   other operand of the comparison that decides the property.
2. **Crash-after-output.** The commit's own quoted justification — "That case is a crash BEFORE the
   suite prints — stdout is empty" — states the restriction and does not test the complement.
   High 1.
3. **The size of the population the swap affects.** No count of how much stdout or stderr the 38
   real suites emit. 28 of 38 exceed the window on stdout; 2 of 38 write stderr at all. Those two
   numbers decide the direction of the trade and neither was taken.
4. **`ev_files[…]["tail"]` itself.** The commit says r1 "did not reach it" and implies r2 does.
   The production line at `:906` still survives mutation at 114/114. High 2.
5. **The production window size** at `:912`/`:944` — both can go 400 → 40 at 114/114.
6. **The `": got "` class outside this file.** The fix is one fixture in one suite; the harness
   parses 38. Medium 1.
7. **The direction of the parser's asymmetry.** The docstring asserts the name direction is unsafe;
   it is safe by construction, and one live case name exercises it correctly today.
8. **Columns vs characters** under a non-UTF-8 stderr. Low 1.

## What I did not measure

- **Any `--mutate .` over a tree with my proposed fixes in it.** Every finding above is a
  *survivor* or a *false claim*, both of which are demonstrable against the subject alone. I did
  not write the fixes, so I have not shown that the suggested cases go red for the right reason —
  each is a hypothesis until run, and this repo has already been bitten by a filed finding whose
  proposed predicate was wrong over the real corpus.
- **Whether `room + 1` / `room + 20` are mutations anyone would accept into the manifest.** I
  chose them to demonstrate the hole; the manifest's own taste (weakest mutation that still fails
  via the case it names) may prefer a different edit. The hole is the finding, not the edit.
- **The 33 static `": got "` candidates one by one.** I read the list and named the two shapes that
  are genuinely exposed; the rest are each file's own producer. That is a static read, labelled as
  such — the dynamic answer for *currently reachable* red cases is the 445/445 attribution, which
  is clean.
- **`check-plan-code.py` under a real terminal.** All width measurements are of the emitted string,
  taken from the run's captured stderr; I did not render one in a terminal emulator at 80 columns.
- **The WIP `diagnostic_tail()` now in the working tree.** Out of subject, unreviewed here.
- **Timing.** The commit's `real 365.66` is unverifiable from my run, which was contended.

---

# Conclusion

**NOT CONVERGED.**

The brief asked me to assume round 2's fixes introduced a new defect, and they did — in B1's own
fix, which is the eighth instance of the class on this branch and the fourth consecutive round
where the Blocking is the previous round's repair. B1 correctly diagnosed "the want must not move
with the subject" and correctly pinned the constant; it left the *other* operand of the same
comparison unguarded, so the one-terminal-row property still has no ceiling — three mutations
survive at 114/114, and 82 of the 445 real labels sit in the band they open.

M1's swap is the second pattern this branch keeps repeating: a fix aimed at a *fixture* rather than
the *population*. It is a strict regression for 28 of 38 suites, the commit's claim that both ends
are cased is false, and the case written to hold the other end is green in both worlds.

None of this touches the shipped behaviour, which I measured and found correct: the live run emits
227 progress lines, maximum width 79 characters, zero wider. The defects are all in what the guards
can see — which, on a branch whose entire subject is a mutation harness, is the thing being
shipped.

**Recommended next round:** close Blocking 1 (threshold cases + one manifest entry), decide High 1
deliberately rather than by concatenation order, and re-point High 2's cases at the production
sites. Medium 1's parser asymmetry should be split out as its own item — it predates this branch
and fixing it properly changes a contract two files depend on.

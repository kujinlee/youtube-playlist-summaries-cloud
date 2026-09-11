# Adversarial review — `harness-progress-output`, round 6 (Claude half)

**Verdict: NOT CONVERGED — 2 Blocking, 2 High, 3 Medium, 2 Low.** Summary table at the end.
Scope: COVERAGE, per the round brief. Written incrementally while measuring.

## Proof of subject

```
$ git log --oneline origin/master..HEAD
6a660454 Round 5: a fixture must differ from itself along the axis it tests   <-- SUBJECT
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git rev-parse HEAD
6a660454dacf43bc1acf7e9916e1b7cb0f0624b8
$ git status --porcelain
(clean)

$ git show --stat 6a660454
 docs/dashboard-entries.md                          |  28 +-
 docs/reviews/claude/harness-progress-r5-claude.md  | 689 +++++++++++++++++++++
 docs/reviews/coordinator/harness-progress-r5-codex.md      |  89 +++
 docs/reviews/verdicts/harness-progress-r5-codex.verdict.json |  16 +
 scripts/check-plan-code.py                         |  77 ++-
 scripts/mutations/check-plan-code.json             | 112 +++-
 6 files changed, 1000 insertions(+), 11 deletions(-)
```

Subject is HEAD; the working tree is clean, so everything measured below is measured against
`6a660454` itself unless a mutation is explicitly staged in a temp tree.

---


## Method — the corrected predicate, re-derived independently

I did not reuse the author's sweep. I enumerated sub-expressions from the **AST** of every function
this branch introduces or rewrites (`diagnostic_tail`, `merged_output`, `run_suite_parts`,
`run_suite`, `progress_line`, `stderr_progress`), docstrings excluded, and asked both predicates of
each against `scripts/mutations/check-plan-code.json`:

| predicate | question |
|---|---|
| r4's (wrong) | `expr in find` — does any entry's anchor text *contain* this expression? |
| r5's (corrected) | `find.count(expr) > repl.count(expr)` — does any edit actually **remove** it? |

**60 sub-expressions. 4 are anchored-but-never-moved. 10 have no entry at all.** Script:
`/tmp/r6-claude-review/sweep.py` (reviewer's temp dir, not the repo).

Every mutation below was run against a control proved green **first**:

```
$ HOME=<redirected> python3 scripts/check-plan-code.py --self-test
126/126 passed        rc=0        stderr 0 B
```

which independently confirms the commit's claimed suite count. Each probe retargets any manifest
anchor its own edit would orphan, so no result is a measurement of my edit.

---

## BLOCKING — B1. `room = PROGRESS_WIDTH - len(head)` has no case and no entry, and a mutation of it survives

`scripts/check-plan-code.py:1325`. This is the **anchored-but-never-moved** shape r5 named, still
present in the very function r5 swept. One entry's `find` text contains the line verbatim:

```
name:  "the fits/truncate comparison turns strict, so a label that exactly fills the row is
        truncated for no reason"
find:  '    room = PROGRESS_WIDTH - len(head)\n    if len(label) <= room:'
repl:  '    room = PROGRESS_WIDTH - len(head)\n    if len(label) < room:'
```

`find.count("PROGRESS_WIDTH - len(head)") == repl.count(...) == 1`. The line is an **anchor**; the
entry moves the comparison on the next line. A grep for coverage succeeds and the expression is
untouched.

### Measured

```
CONTROL                                        rc=0   126/126 passed
room = PROGRESS_WIDTH - len(head)  ->  room = PROGRESS_WIDTH - 10
                                               rc=0   126/126 passed    SURVIVES
```
(2 manifest anchors bound to that line retargeted in the same edit, so the run measures the
mutation and not the orphan.)

### Why no case can see it

**Every case that exercises `room` uses the pair `(164, 434)`** — `progress_line(164, 434, …)` at
`:2677`, `:2693`, `:2695`, `:2698`. For that pair `head` is `"[164/434] "`, exactly **10**
characters, so `len(head)` and the literal `10` are indistinguishable. The one case using a
different pair — `progress_line(7, 38, "check-docs.py")` at `:2539` — passes a 13-character label,
which fits under **any** value of `room` and therefore never reaches the arithmetic.

This is r5's own lesson at the level above the one it was applied to. r5 asked *"what two inputs
would this case have to tell apart?"* of the **label** and fixed the fixture's magnitude/position.
It never asked it of the **head**: the head is a fixture constant in every case, so `progress_line`
is pinned at exactly one head width and the head-width dependence is untested. The axes r5
enumerated were magnitude and position **of the label**; the untested one is the *other operand*.

### The harm is live on today's corpus, not hypothetical

`run_mutations` calls `progress(position, len(muts), name)` with `len(muts) == 466`, so production
head widths are **8, 9 and 10** characters (`"[1/466] "`, `"[64/466] "`, `"[466/466] "`) — true
`room` of 71, 70, 69. The mutant reports 69 for all three. Measured over the 466 real manifest
names that become labels:

```
head width 8  ->  10 real labels truncated that should not be
head width 9  ->   6 real labels truncated that should not be
```
e.g. `'the tick refusal drops the pause reason, so the reader cannot judge it'` (70 chars) gets an
ellipsis it did not earn — **the exact harm named by the entry "truncation is applied to every
label, so a name that already fits is mangled and given an ellipsis it did not earn"**. The manifest
carries an entry for that harm via one mutation and a second mutation producing the identical harm
walks through.

The opposite direction is worse and is a growth path this branch is already on: at `len(muts) >=
1000` the head reaches 11 characters, true `room` is 68, the mutant says 69, and a 69-character
label yields `11 + 69 = 80` columns — **the line stops being bounded to one row, which is the entire
property `progress_line` exists to hold.** `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` went
36 -> 63 -> 71 on this branch alone and the total is 466.

### Why Blocking rather than Medium

The docstring at `:1294-1300` states the bound as an invariant ("BOUNDED TO ONE ROW", "the head is
always a prefix of the result") and reasons about unreachability from `done`/`total` magnitudes — it
is explicitly aware that the head varies, and nothing tests that it does. A guard whose stated
invariant is false under a surviving one-token mutation is the class this branch has spent five
rounds on.

---

## HIGH — H1. The give-back is asserted only at the two endpoints; its slope is unpinned

`scripts/check-plan-code.py:416` — `err_keep = min(len(err), max(half, window - len(out)))`.

### Measured

```
CONTROL                                                    rc=0  126/126 passed
window - len(out)      ->  window - 2 * len(out)           rc=0  126/126 passed  SURVIVES
window - len(out)      ->  window - len(out) // 2          rc=1  124/126 passed  killed
```

One direction dies, the other does not. **This is r5's H1 finding — "the give-back property was
cased in one direction only" — reproduced at a different point of the same expression, by the fix
for it.** r5 mirrored the *operand* (`len(out)` vs `len(err)`); the *coefficient* is still
one-sided.

### Why no case can see it

The term `window - len(out)` is only live when `0 < len(out) < half`. Outside that band it is
invisible:

* `len(out) == 0` — the coefficient multiplies zero, so every value of it gives 400;
* `len(out) >= 200` — `max(half, …)` clamps and the term is discarded entirely.

Every case that asserts a **precise budget** sits at an endpoint:

| case | `:line` | `len(out)` | regime |
|---|---|---|---|
| `...and a quiet stdout gives its whole half back to stderr` | 2650 | **0** | coefficient invisible |
| `both streams flooded, and the stderr half is exactly half` | 2628 | 5000 | clamped |
| `...and the window never exceeds its budget` | 2658 | 5000 | clamped |
| `...and a quiet stderr gives its whole half back to stdout` | 2667 | 5000 | `err_keep == 0` |
| `...and it is the END of each stream that is kept` | 2641 | 5010 | clamped |

The two cases whose input *is* in the live band assert only **membership**, never a budget:
`:2606` (`len(out) == 27`, asserts `"[FAIL] …" in result`) and `:2598` (`late.py`, asserts the
exception text is present). Membership cannot see a budget that is merely under-spent.

### The harm, quantified on the shape this file already uses as a fixture

A suite that prints a little and then crashes — `late.py` at `:2589` is exactly this, and the
docstring at `:403` says 28 of 38 real suites crash after printing:

```
stdout 101 B, traceback 757 B
  real   err chars kept = 299,  total window 401
  k=2    err chars kept = 200,  total window 302     99 characters of traceback DISCARDED
```

The budget is 400 and the mutant spends 302 of it. That is r5's own H1 harm verbatim ("discarding
half the budget for the failure shape where the traceback is the ONLY evidence there is"), and the
suite is green.

Full profile of the survivor across `len(out)`:

```
len(out):    0    50   100   150   199   200   250   400  5000
real     : 400   401   401   401   401   401   401   401   401
k=2      : 400   351   301   351   400   401   401   401   401
lost     :   0    50   100    50     1     0     0     0     0
```

The peak loss is at `len(out) == 100` — the dead centre of the untested band.

### Answer to brief item 1 — the third axis

Magnitude (r1-r4) and position (r5) are both **properties of a single stream in isolation**. The
untested axis is the **interaction**: the budget each stream receives is a function of the *other*
stream's length, and that function is sampled only where it is constant (both endpoints). A fixture
must differ from itself along the axis the property is about — and the give-back's axis is
`len(out)` in the open interval `(0, half)`, where **no case makes a precise assertion at all**.

---

## HIGH — H2. Both `diagnostic_tail` CALL SITES survive an argument swap, while the function's own order is pinned

`scripts/check-plan-code.py:994` (control diagnostic) and `:1027` (re-control diagnostic).

### Measured

```
CONTROL                                                  rc=0  126/126 passed
:994   diagnostic_tail(so, se) -> diagnostic_tail(se, so)  rc=0  126/126 passed  SURVIVES
:1027  diagnostic_tail(so, se) -> diagnostic_tail(se, so)  rc=0  126/126 passed  SURVIVES
body   err half emitted LAST instead of first               rc=1  124/126 passed  killed
```

The **pure function's** output order dies immediately (two red cases). Both **call sites** that
produce the only report a human ever reads walk through.

`diagnostic_tail(stdout, stderr)` is not symmetric: the second parameter gets the guaranteed floor
`max(half, …)` and is emitted **first**; the first parameter gets the remainder and is emitted
**second**. Passing `(se, so)` therefore reverses both the priority and the order of the real
CANNOT RUN report — stdout is printed above the traceback and is the stream given the floor — for
every control failure in production. Every case stays green.

### Root cause, and it subsumes M2 below

`:2014` in this file already names the class: *"the two on `run_suite_parts` stop at the helper —
NONE of them would notice `mutate_delivered` going back to slicing one merged string. That is the
gap r3 H1 was: a property proved about a helper, and asserted about the caller."* The commit added a
case to close that for one mutation (`diagnostic_tail` replaced by a merged slice, two entries) and
left the **argument order** at the same two sites uncovered.

The reason it survives is uniform: **every case that drives the production report asserts
MEMBERSHIP, never structure.**

| case | `:line` | assertion |
|---|---|---|
| `a CANNOT RUN report says WHY the control died` | 2029 | `any("…" in r for r in _repL)` |
| `...and the AFTER-control report shows the reason` | ~2035 | `"…" in …` |
| `600 B of child stderr cannot push the failure out` | 2576 | `"[FAIL] …" in diagnostic_tail(…)` |
| `a suite that crashes AFTER 800 B of stdout` | 2598 | `"…" in _ltail` |
| `a flooded stderr cannot evict stdout's failure` | 2605 | `"…" in diagnostic_tail(…)` |
| `...and a flooded stdout cannot evict stderr's traceback` | 2608 | `"…" in diagnostic_tail(…)` |

All six structural cases (`:2628`, `:2641`, `:2650`, `:2658`, `:2663`, `:2667`) call
`diagnostic_tail` **directly**. Not one of them reaches `mutate_delivered`. An `in` test cannot see
an order, a priority, or an under-spent budget — so the seam between the pinned helper and the
unpinned call site is exactly where every survivor in this review lives.

---

## MEDIUM — M1. The commit says three `enumerate(…, 1)` starts were entried; two were

`scripts/check-plan-code.py:981`, `:1013`, `:1058` are the three sites. The manifest contains two
entries that move an `enumerate(…, 1)`:

* `"the before-control phase counts from zero"` — `find` is
  `'        for position, name in enumerate(targets, 1):\n            # SILENT UNLESS A CALLER ASKS'`.
  `:981` is followed by that comment; **`:1013` is followed by `if progress is not None:`**, so the
  anchor binds to `:981` only.
* `"the mutation loop counts from zero"` — binds `:1058`.

The **re-control loop at `:1013` has no entry.**

### Measured

```
CONTROL                                             rc=0  126/126 passed
:1013  enumerate(targets, 1) -> enumerate(targets, 0)  rc=1  124/126 passed  killed by CASES
:981   enumerate(targets, 1) -> enumerate(targets, 0)  rc=1  124/126 passed  killed (entry exists)
```

So this is not a hole in the suite — it is r4 L2's class exactly ("the row has a case and no
entry"), which the commit claims to have swept and closed for this row. The behaviour is held only
by a case, and this file's own `EXPECTED_MUTATIONS` comment states the consequence: *"a case is held
only by the self-test COUNT ratchet, which sees the number move rather than the coverage leave."*
The count would not move if the case were rewritten to stop asserting the re-control tuple.

Severity is Medium rather than Low because the **claim in the commit message is wrong** — a reader
checking "were the three enumerate starts closed?" gets yes from the prose and no from the manifest.

---

## MEDIUM — M2. `merged_output`'s argument order is covered in the body and at NO call site

`scripts/check-plan-code.py:495`, `:987`, `:1017`.

Corrected-predicate result over the manifest:

```
'(stderr + stdout)'        moved-by = 2   anchored-by = 2      (the BODY is covered)
'merged_output(out, err)'  moved-by = 0   anchored-by = 0
'merged_output(so, se)'    moved-by = 0   anchored-by = 0
```

### Measured

```
CONTROL                                                  rc=0  126/126 passed
:495   merged_output(out, err) -> merged_output(err, out)  rc=0  126/126 passed  SURVIVES
:987   merged_output(so, se)  -> merged_output(se, so)     rc=1  125/126 passed  killed
:1017  merged_output(so, se)  -> merged_output(se, so)     rc=0  126/126 passed  SURVIVES
```

`:987` dies only because its result flows into `ev_files[…]["tail"]`, which `:2051` asserts
positionally. `:495` and `:1017` have no such consumer and nothing looks at them.

This is **r3 H2 moved one level out**. r3 H2 was "three copies of the ordering rule drifted"; the fix
collapsed them into one implementation and pinned that implementation. The order can now be defeated
at the **call site** instead, where the corrected predicate reports zero coverage — and
`merged_output`'s docstring at `:457` states "STDOUT LAST" as a contract two call sites can violate
while green.

Both survivors look inert on inspection (`:495`'s only production consumer is
`parse_fail_names(out)`, which is line-based, and `:1017`'s is `control_is_green`, a substring test).
**That inspection is exactly the reasoning r4 L1 refuted by running the experiment**, and this
commit established the protocol for settling it — mutate, retarget anchors, run the full harness,
record the number at the clause. The protocol was applied to three clauses this round; these two,
introduced by the same refactor, were not put through it.

---

## BLOCKING — B2. Both control loops report `[n/n]`: the denominator can be deleted and the suite stays green

`scripts/check-plan-code.py:985` and `:1015`.

### Measured

```
CONTROL                                                                  rc=0  126/126 passed
:985   progress(position, len(targets), f"control {name}")
         -> progress(position, position, …)                              rc=0  126/126 passed  SURVIVES
:1015  progress(position, len(targets), f"re-control {name}")
         -> progress(position, position, …)                              rc=0  126/126 passed  SURVIVES
:1065  progress(position, len(muts), name)
         -> progress(position, position, name)                           rc=1  125/126 passed  killed
:1065  progress(position, len(muts), name)
         -> progress(len(muts), len(muts), name)                         rc=1  125/126 passed  killed
```

**The identical property, on three loops. It dies on one and survives on the other two, and the only
difference is the size of the fixture.**

### Why — and the author already knew the rule

Every case that observes the control loops runs on `_mini` (`:1925`), which writes exactly **one**
script (`scripts/thing.py`, `:1934`) and exactly **one** manifest entry (`:1946`). So `targets` has
length 1, and `position == len(targets) == 1` for every observation:

```
case "every phase of --mutate reports its position when a caller asks"   :1986
    want [(1, 1, "control scripts/thing.py"),
          (1, 1, "value is two"),
          (1, 1, "re-control scripts/thing.py")]
```

Three ones. Position, total, and the literal 1 are mutually indistinguishable. The same is true of
`"--mutate itself supplies the reporter"` at `:2010` (`"[1/1] …"` three times).

The `run_mutations` case at `:2715` is the A/B: the author wrote it with **two** mutations —
`for i in (1, 2)` — and wants `[(1, 2, "m1"), (2, 2, "m2")]`. That is precisely the fixture that can
tell position from total, it is why R and S above die, and **it was not carried across to either
control loop.**

### Harm

`progress_line`'s own docstring at `:1281-1284` states the purpose: *"what a reader needs is not
motion but POSITION — which subject, how far, **out of how many**."* The surviving mutation deletes
the third of those three. In production `targets` is 38 files, so the control phase would print

```
[1/1] control scripts/check-anchors.py
[2/2] control scripts/check-arch-findings.py
[3/3] control scripts/check-backlog-closure.py
```

instead of `[1/38] …`, `[2/38] …`, `[3/38] …`. The denominator is gone, "how far through" becomes
unreadable, and this is the **first** phase — the ~40 seconds of a 7-minute run during which the
reader is deciding whether the thing is working at all, which is the entire motivating incident
recorded at `:1286-1289` ("it cost two wrong status reports in one session").

### Relation to B1

B1 and B2 are one defect wearing two faces: **`progress_line` and its callers are pinned at a single
point in every argument except the label.** The label was given magnitude (r1–r4) and position (r5).
`done`, `total` and `len(head)` were never varied at all — `(164, 434)` in every pure case, `(1, 1)`
in every integration case. r5's question — *"what two inputs would this case have to tell apart, and
can it?"* — was asked of one of the three arguments.

---

## Brief item 6 — `--mutate .` reproduced

```
$ HOME=<redirected> python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 38 file(s), 466 mutation(s), 466 killed,
     466 attributed to the case each names, 0 survivor(s)
EXIT=0
```

Staged per the brief (`scripts` copied, `supabase` / `docs` / `.claude` / `node_modules/typescript`
symlinked, `HOME` redirected). **The claim holds exactly: 38 / 466 / 466 / 466 / 0, exit 0.**
Progress stream: **542 lines**, which is the next finding.

---

## MEDIUM — M3. The docstring's own progress-line total is the r4 number, and it went stale inside the commit that changed it

`scripts/check-plan-code.py:1294-1298`:

> *"What is stable, and what this function restores, is the RATE: one line per mutation plus one per
> control and re-control — **534 at this writing**, and it moves whenever the manifest does, which is
> why the arithmetic is given instead of the total."*

### Measured

```
$ wc -l < mutate.err      # the real progress stream of the run above
542
```

`466 + 38 + 38 = 542`. The stated 534 is `458 + 38 + 38` — **the r4-era manifest size.** Traced:

```
c3d53a70 (r3)  sum(EXPECTED_MUTATIONS.values()) == 452
5e4bd163 (r2)  == 445
d6f55881 (r4)  == 458      <-- 534 = 458 + 76
6a660454 (r5)  == 466      <-- the actual stream is 542
```

The same commit that moved the total 458 -> 466 (and says so in its own message) wrote a docstring
paragraph asserting 534. The paragraph's thesis is that the number moves with the manifest; it did
not move with the manifest in the commit that introduced it. Nothing enforces it —
`check-selftest-counts.py` pins declared `--self-test` counts, not this one.

---

## MEDIUM — M4. The LOAD-BEARING vs DEAD comparison is confounded: the two halves were measured against different manifests

`scripts/check-plan-code.py:430-432` presents this as a controlled pair:

```
#     `if err_keep else ""`  removed -> 458 killed, 457 attributed   LOAD-BEARING
#     `if out_keep else ""`  removed -> 466 killed, 466 attributed   DEAD
```

and the commit message frames it as *"Asked separately, with the same experiment, they disagree"*
and *"the identical experiment"*.

They are not the same experiment. **458 is r4's manifest (`d6f55881`); 466 is r5's.** The 457
attribution is inherited from r4 L1's run and was never re-taken at 466.

This is not pedantry about a number — the 8 entries added this round land on the exact lines under
test. Four entries now bind that `return` statement:

| entry | binds | existed at 458? |
|---|---|---|
| `the two kept halves are joined with no separator` | `err[-err_keep:] if err_keep else ""` | **yes** |
| `the stderr half is sliced from the FRONT` | `err[-err_keep:] if err_keep else ""` | **no — added this round** |
| `the stdout half is sliced from the FRONT` | `out[-out_keep:] if out_keep else ""` | **no — added this round** |
| `the empty-half filter is dropped` | `out[-out_keep:] if out_keep else "") if p)` | **no — added this round** |

One of the new ones mutates `err[-err_keep:]` -> `err[:err_keep]` — a different mutation of the very
expression whose guard the experiment deletes. At 458 the `err_keep` clause had **one** entry bound
to it; at 466 it has **two**. Whether the attribution still goes 466/465 is therefore an open
question, not a carried-forward result, and the comment a future reader consults states it as
settled.

The commit's own rule from the same session — *"a count pinned to a PAST event must NOT be
'corrected' to today's number"* — is right for a **historical record**. These two lines are not a
historical record; they are a **live side-by-side comparison** used to justify keeping one clause
and labelling the other dead. A comparison needs both arms taken under the same conditions, or it
needs to say which arm is stale. This one says the opposite.

**I am re-running the `err_keep` arm at 466 now; the result is appended below.**

---

## Brief item 4 — were the retargets fair? Yes, and nothing would have caught an unfair one

Two entries were retargeted **in the commit** (diffed `d6f55881` -> `6a660454`; 8 added, 0 removed,
2 changed in place). The other retargets the commit message mentions happened inside the author's
scratch experiments and did not land.

| entry | anchor moved | code change preserved? |
|---|---|---|
| `stdout's budget stops accounting for what stderr already took` | `# ⛔ THE` -> `# ⛔ THESE` | **yes** — both arms are `window - err_keep` -> `window`, byte for byte |
| `a quiet stderr no longer hands its unused half back` | preceding `max(half, …)` line -> following `# ⛔ THESE TWO` | **yes** — both arms are `window - err_keep` -> `window - half`, byte for byte |

Both are fair: the *anchor* moved, the *edit* did not, and neither entry's `expect` changed. I
checked this by diffing the entries structurally, not by reading the commit message.

### The finding is what surrounds them — Low, below

Both retargets were **forced by a comment edit**, and both landed on **new comment text**. Measured
over the manifest:

```
71 entries for scripts/check-plan-code.py
 5 are disambiguated by a line that is a COMMENT:
     # The tree changed underneath           (pre-existing)
     # ⛔ THESE                                (retargeted this round)
     # ⛔ THESE TWO                            (retargeted this round)
     # ⚠ `min(len(out)                        (added this round)
     # SILENT UNLESS A CALLER ASKS            (added this round)
```

Four of the five arrived or moved in this commit, and this commit's characteristic act is **editing
comments** — it added roughly 40 lines of annotation to `diagnostic_tail` and `progress_line` alone.
So the manifest now has five entries that a future annotation edit orphans.

This fails **loud** (`--mutate .` refuses an unresolved anchor), so it is noise, not a hole — hence
Low. But it creates the situation brief item 4 is worried about: a retarget is a routine,
frequently-required edit, and **nothing mechanically checks that a retarget preserved the mutation.**
`find`/`repl` can be rewritten together into a weaker pair and every gate stays green. Both of this
round's retargets are fine; that is a fact about the author, not about the harness.

---

## Brief item 3 — the LOAD-BEARING verdict, re-measured at 466. **It holds.**

I ran the `err_keep` arm myself, at the shipped manifest size: deleted `if err_keep else ""` from
`:452`, retargeted the **two** entries bound to that text by anchor (`the two kept halves are joined
with no separator`, `the stderr half is sliced from the FRONT`), verified every remaining `find`
resolves exactly once, then ran the full harness.

```
FAILED — delivered scripts mutated: 38 file(s), 466 mutation(s), 466 killed,
         465 attributed to the case each names, 0 survivor(s)
EXIT=1
```

and the lost attribution is the one the comment predicts, by the mechanism it predicts:

```
✗ 'a flooded stdout is allowed to starve stderr of its half…':
    `expect` "...and a flooded stdout cannot evict stderr's traceback" matched 0 red case(s)
    — it was caught by something else: ['both streams flooded…', '...and it is the END…',
      '...and the window never exceeds its budget…']
```

**458/457 -> 466/465. The verdict is LOAD-BEARING at both sizes, and the guard should stay.**

### Correcting my own M4 above

I filed M4 before running this, on the reasoning that the two new entries bound to `err_keep`'s line
could have changed the answer. **They did not.** The confound was real — the two arms were taken at
458 and 466 and the comment calls them "the identical experiment" — but the conclusion it supports
is correct, now on two independent measurements eight entries apart. **M4 is downgraded to Low: the
number `457` in the shipped comment is stale (it is `465` today) and the pairing is presented as
controlled when it was not, but nothing about what ships is wrong.** I am leaving the reasoning above
rather than deleting it, because the re-run is the point: the claim was checkable and is now checked.

The `out_keep` DEAD arm I did **not** re-measure — see *what I did not measure*.

---

## B1, confirmed by a falsifier pair

Two more forms, same control:

```
room = PROGRESS_WIDTH - len(head)  ->  room = 69                       126/126  SURVIVES
room = PROGRESS_WIDTH - len(head)  ->  room = PROGRESS_WIDTH - 10      126/126  SURVIVES
room = PROGRESS_WIDTH - len(head)  ->  room = PROGRESS_WIDTH - len(head.rstrip())
                                                                       124/126  killed
PROGRESS_WIDTH = 79 -> 80  (control for the case's sensitivity)        124/126  killed
```

The pair is the proof: a mutation that changes `room`'s **value at head width 10** dies immediately;
a mutation that severs `room` from `len(head)` while leaving the value 69 at head width 10 survives.
What is unpinned is precisely the **dependence on the head**, not `room` in general — so this is a
missing axis in the fixtures, not a missing case for a known value.

---

## What I did not measure

* **The `out_keep` DEAD arm and the `min(len(out), …)` DEAD arm.** Both are asserted as 466/466 in
  the shipped comments. I reproduced only the arm whose answer would change what ships, per the
  brief. If either is wrong the harness fails loud on the next `--mutate .`, so the cost of not
  re-running them is bounded; the cost of a wrong LOAD-BEARING would have been a deleted guard.
* **Whether M2's two survivors (`:495`, `:1017` argument order) are DEAD or LOAD-BEARING in the
  mutation space.** I measured that they survive the **suite**; I did not run the full-harness
  experiment that r4 L1 proved is the only way to tell inert from attribution-bearing. I say so
  rather than assert inertness, because asserting it from a reading is the exact move r4 L1 refuted.
* **The 33 guards in `scripts/` other than `check-plan-code.py`.** The sweep's population is the six
  functions this branch introduces or rewrites plus the changed regions of `mutate_delivered` and
  `run_mutations`. The same corrected predicate over the other 37 manifest files is untouched work,
  and given that it found four anchored-but-never-moved rows in the one file that has had five
  adversarial rounds, I would expect it to find more elsewhere.
* **Any claim about `docs/dashboard-entries.md`.** Out of scope; not read.
* **Real terminal rendering.** B2's harm (`[1/1] [2/2] [3/3]`) is derived from the argument values,
  not observed in a terminal.

---

## On the scoping

The coverage scoping was right, and this round is evidence for it rather than against. Every finding
above is a missing or unfalsifiable case, and every one sits at a **seam** rather than inside a
module: helper-pinned/caller-unpinned (H2, M2), one-argument-varied/two-fixed (B1, B2), one-endpoint
/other-endpoint (H1). A restructure of the diagnostic subsystem moves those seams; it does not remove
them. I have no measurement showing a redesign would remove a defect, so I make no such proposal.

What I would say instead: the recurring generator is now nameable in one sentence, and it is not
"`diagnostic_tail` is badly structured". It is that **the fixtures vary exactly one argument of each
function under test, and the reviews have been improving that one argument for five rounds.** r5
found the label's position after r4 found the label's magnitude; neither asked about `done`, `total`,
`len(head)`, `len(targets)`, or the *other* stream's length. A cheap mechanical check exists for
this class and does not: *for each parameter of each function under test, do at least two cases pass
values that differ?* Under that rule `progress_line` fails on `done`, on `total`, and on the head
width; `diagnostic_tail` passes on both streams' magnitude and fails on the interior band. That is a
guard, not a rule to remember — which is this project's own standard.

---

## Verdict — **NOT CONVERGED**

| # | Sev | Finding | Measured |
|---|---|---|---|
| B1 | **Blocking** | `room = PROGRESS_WIDTH - len(head)` (`:1325`) is anchored-but-never-moved; the head-width dependence is untested | 2 surviving forms, 126/126; falsifier pair |
| B2 | **Blocking** | Both control loops' `total` argument (`:985`, `:1015`) can be replaced by `position` | 126/126 survives; the same property on `:1065` dies, fixture n=2 vs n=1 |
| H1 | High | The give-back's coefficient (`:416`) is pinned in one direction only; no case asserts a budget in `0 < len(out) < half` | `window - 2*len(out)` survives 126/126; 99 chars of traceback discarded on the `late.py` shape |
| H2 | High | Both `diagnostic_tail` call sites (`:994`, `:1027`) survive an argument swap while the function's own order dies | 126/126 twice; body swap 124/126 |
| M1 | Medium | Two of the three `enumerate(…, 1)` starts are entried; the commit says three. `:1013` has a case and no entry | manifest anchor binds `:981` only; `:1013` killed by cases |
| M2 | Medium | `merged_output`'s argument order is covered in the body and at **no** call site | `:495` and `:1017` survive 126/126; `:987` dies |
| M3 | Medium | The docstring's progress-line total (`:1297`, "534") is the r4 number; the real stream is 542 | `wc -l` on the run's stderr = 542 = 466+38+38 |
| L1 | Low | The LOAD-BEARING/DEAD pair (`:430-432`) was taken at two manifest sizes and is presented as one experiment; `457` is `465` today | re-run: 466/465, **verdict unchanged** |
| L2 | Low | 5 manifest entries are disambiguated by comment text; 4 arrived or moved this round, in a commit whose main act is editing comments | structural diff of the manifest |

**Confirmed as claimed:** suite `126/126`, `EXPECTED_MUTATIONS` `466`, `--mutate .` =
38 files / 466 mutations / 466 killed / 466 attributed / 0 survivors / exit 0, nested self-test
stderr 0 B, 0 unresolved anchors. The r5 fixes for B1, H1, M2 and L2 all hold — I attacked the slice
direction, the output order, the `strip()`, the `if p` filter and the split point, and every one of
those dies. The two retargets in the commit are fair.

Five of the nine findings above are the **same defect as the previous five rounds' Blocking**, in
arguments nobody has varied yet. That is the answer to *"assume `6a660454` does it again"*: it did
not reintroduce a bug in its own fix this time — every one of r5's fixes is solid — but the method
that generated the previous five was applied to one argument out of three, and the rest of the
argument space is still where the defects are.

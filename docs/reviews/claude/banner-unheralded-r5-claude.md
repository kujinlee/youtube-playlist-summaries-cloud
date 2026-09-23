# banner-unheralded — round 5, Claude half (the round-4 fold, and its own survivor's fix)

Subject: `b31064ff` (round 4's fold) and `7f79ac5b` (the fix for the survivor that fold caused),
on `banner-work-without-banner`.

REVIEW GAP: codex — rounds 2+ ALTERNATE by design; the Codex half ran as round 4, and its findings
and its pre-committed stop condition are this round's subject

**Method.** Every claim below was produced by running code, never by reading it. The guard was
staged into an isolated tree (`scripts/` + `.claude/hooks/`, so `ROOT` resolves outside this
checkout) and re-staged from pristine before every mutant. Nothing under `scripts/` was modified
and no mutating `git` command was run. `git status --porcelain` was empty before this round and
afterwards names only this document.

```text
$ python3 tree/scripts/check-banner-armed.py --self-test   # the control, in the staged tree
150/150 self-test cases passed        rc=0
```

---

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | **High** | Of the ELEVEN freezable derived-value sites in delivered code, **two** are pinned, **one is half pinned**, and **eight are not**. Nine single-edit survivors at 150/150 — including one of the three details round 4 believed it had pinned |
| 2 | Medium | H-B1 control's new `endswith` clause is already TRUE before the drive it observes, and it REPLACED the growth assertion rather than joining it |
| 3 | Medium | `and judged is None` at `:1111` is undefended — removing it turns a sound QUIET into CANNOT RUN on a routine input |
| 4 | Low | The `last_judged_uuid` carry is undefended; I could not construct a reachable input where it matters, and say so rather than inflate it |
| 5 | Low | The unheralded log detail's `if judged is not None else 0` is dead, like the `"?"` two lines above it — but unlike the `"?"` it is not declared to be a crash barrier |

---

### High 1 — the fixture-set property is real for two sites, half-real for a third, absent for eight

Round 4's claim, in `b31064ff`: *"asserted values are now mutually DISTINCT, so no single constant
can satisfy two cases at once"*, described as "a property of the FIXTURE SET rather than of any one
case", with a sweep of "7 probes over every derived user-visible value" reporting **7/7 caught**.

I enumerated the population mechanically rather than by eye — every interpolation of a derived
quantity into a user-visible or evidence-facing string, in the delivered code only (above
`def _self_test`). **Sixteen interpolations, eleven independently freezable sites:**

```text
    533  {unticked}                f"{unticked} step(s) still unticked, and emitted no …"
    559  {tool_uses}               f"⚠ WORK WITHOUT A BANNER — this turn made {tool_uses} tool calls…"
    602  {step}  603 {total}       f"…HIGHEST VISIBLE banner is `STEP {step} of {total}`…"
    607  {total}                   f"…announced and finished all {total} steps…"
    636  {session or '-'}          log_line:   f"{when}\t{session or '-'}\t{reason}\t{detail}\n"
    646  {session or '-'}          flush_line: f"{when}\t{session or '-'}\t{before}\t{after}\n"
    646  {before} {after}          flush_line: the measured counts
   1051  {late[0]} 1052 {late[1]} {late[1] - late[0]}   the LATE FLUSH note
   1133  {banner[0]} {banner[1]}   detail = f"STEP {banner[0]} of {banner[1]}"
   1135  {tool_uses_of(judged.body) …}                  detail = f"… tool calls"
   1138  {unticked}                                     detail = f"{unticked} unticked"
```

Freezing each to a constant, one edit at a time, over a control proved green first:

```text
PINNED (killed)
  1138 log unticked          -> 3                 killed 149/150   via H-A4
  1135 log tool calls        -> LARGE_TURN + 7    killed 149/150   via H-B1 control
  1135 log tool calls        -> LARGE_TURN + 5    killed 149/150   via W-INT
  1133 log banner, BOTH      -> "STEP 2 of 5"     killed 149/150   via F97b

SURVIVORS (suite green at 150/150)
  1133 log banner, the STEP  -> "STEP 2 of {banner[1]}"   SURVIVOR   ← r4 believed this pinned
   559 message tool count    -> LARGE_TURN + 3            SURVIVOR   ← r4's own fix caused this
   533 message unticked      -> 3                         SURVIVOR
   602 message step/total    -> "STEP 2 of 5"             SURVIVOR
   607 message total         -> 5                         SURVIVOR
  1051 late-flush counts     -> 1 / 2 / 1                 SURVIVOR
   646 flush_line counts     -> 1 / 2                     SURVIVOR
   646 flush_line session    -> "fl-text"                 SURVIVOR
   636 warn-log session      -> ""  (renders as '-')      SURVIVOR
```

The property is not a property of the fixture set. It is a property of **having two call sites with
different fixtures**, and exactly two sites have that. Where a value is asserted by one case, the
constant equal to that case's literal satisfies it; where it is asserted by none, any constant does.

#### The three that decide this finding

**`:559` — round 4's own fix is what makes it survive.** `_BIG` was moved from `LARGE_TURN` to
`LARGE_TURN + 3` so the count would appear nowhere else in the message, and manifest entry 39 —
*"the warning message's tool count is frozen, leaving only the threshold sentence"* — freezes it at
`LARGE_TURN + 7` and dies correctly. Freezing it at `LARGE_TURN + 3` instead, the value its own
asserting case supplies, survives. The entry tests a **value**; the case's name claims a
**property**:

```python
case("...and it reports the COUNT it saw, not a fixed string (catches a hardcoded message)",
     f"{_BIG} tool calls" in decide([], armed=False, tool_uses=_BIG)[1])
```

One call, one fixture, one literal. This is the third consecutive round in which the case literally
named *catches a hardcoded message* is satisfied by a hardcoded message. Concretely:

```text
  tool_uses= 26  pristine: ⚠ WORK WITHOUT A BANNER — this turn made 26 tool calls, armed no plan,
               MUTANT:  ⚠ WORK WITHOUT A BANNER — this turn made 28 tool calls, armed no plan,
  tool_uses=120  pristine: ⚠ WORK WITHOUT A BANNER — this turn made 120 tool calls, armed no plan
               MUTANT:  ⚠ WORK WITHOUT A BANNER — this turn made 28 tool calls, armed no plan,
```

**`:1133` — one of the three r4 hardened is only half hardened.** Both asserting cases pin the tail
of the log line, and **both use step 2**: `endswith("\tunarmed\tSTEP 2 of 3")` at `:1864` and
`endswith("\tunarmed\tSTEP 2 of 5")` at `:1918`. The distinctness r4 relied on lives entirely in
the TOTAL. Freezing only the step half — `f"STEP 2 of {banner[1]}"` — survives at 150/150, and
every `unarmed` entry in the warn log (100% of its 76-entry history) would record step 2 whatever
step the turn actually reached. This is the counterexample to the fold's own claim, inside the fold's
own repair.

**`:646` — the case authored against exactly this does not stop it.** The comment above Cx-M1
(`:1836-1841`) records: *"a `flush_line` that returned a constant string passed 94/94 on a mutated
copy … the counts ARE the evidence"*. The repair pinned the string; the counts and the session are
still ambient, because the only flush scenario holds `fl-text`, 1 and 2, and the case asserts those
literals:

```python
case("Cx-M1 ...and the observation LINE carries the measured counts, not just a line",
     safe(lambda: _flushtext().rstrip("\n").split("\n")[-1].split("\t")[-3:]
          == ["fl-text", "1", "2"]))
```

`flush_line` returning `f"{when}\t{session or '-'}\t1\t2\n"` satisfies it — measured:

```text
  pristine: 'T\tsess\t4\t11\n'
  MUTANT:   'T\tsess\t1\t2\n'
```

FLUSH_LOG is the evidence base for backlog #96/#97. The file would stay populated while recording
nothing that was measured, which is this repo's recorded *a guard's own output is a CONTRACT*
failure one layer in from the log-format defect the whole slice is about.

#### The four with ZERO asserting cases

Nothing in 150 cases reads the number in *"N step(s) still unticked"*, either number in
*"HIGHEST VISIBLE banner is `STEP i of N`"*, the total in *"announced and finished all N steps"*,
the three counts in the LATE FLUSH note, or either session column. Pristine beside mutant:

```text
=== :533   steps=(0, 7)  pristine: …edited a file in the repo with 7 step(s) still unticked
                         MUTANT:  …edited a file in the repo with 3 step(s) still unticked
=== :602   banner 7 of 8  pristine: …HIGHEST VISIBLE banner is `STEP 7 of 8
                          MUTANT:  …HIGHEST VISIBLE banner is `STEP 2 of 5
=== :607   banner 1 of 9  pristine: a job that announced and finished all 9 steps can look partway-done
                          MUTANT:  a job that announced and finished all 5 steps can look partway-done
```

`:602`'s number is the one the message itself warns *"MAY BE LOW, AND THIS CHECK CANNOT TELL"* — a
frozen `STEP 2 of 5` tells the reader a specific false thing about their own turn, in the sentence
that asks them not to over-read it.

#### Why an eighth probe is the wrong repair

Round 4 added three manifest entries, one per value it had found. That is the instance fix at the
*manifest* layer, and it is why `:559` survives and why `:1133` is half-covered: an entry pins the
constant that was tried, not the class. The class-level property is mechanical and checkable —

> **a case asserting a derived value must exercise its producer at two DISTINCT inputs.**

A constant cannot satisfy an assertion evaluated at two different inputs, whatever the constant, and
it cannot satisfy it *component-wise* either, which is what `:1133` needs and pairwise-distinct
fixtures did not give it. The two sites that survived this round's sweep are exactly the two that
happen to have two call sites with different fixtures — the property already works, it is just
being obtained by coincidence of fixture design rather than required. Restating it as *two distinct
inputs per case* removes the class rather than the nine instances, and it is enforceable by a script
over the suite rather than by remembering to sweep.

---

### Medium 2 — H-B1 control's new clause is true before the drive it observes

`b31064ff` replaced this case's growth assertion with a tail match:

```diff
-                 _rcB2 == WARN and _logtext() != _bp2)
+                 _rcB2 == WARN
+                 and _logtext().rstrip("\n").endswith(
+                     f"\t{REASON_UNHERALDED}\t{LARGE_TURN + 5} tool calls"))
```

The case's own name still claims *"so the case above cannot pass by the path simply never
running"*. That claim was carried by `!= _bp2`, which is gone. Instrumenting the staged copy at the
line where `_bp2` is taken — before the control drive runs:

```text
PROBE last line BEFORE the H-B1-control drive: '…-07:00\ts\tunheralded\t30 tool calls'
PROBE last line AFTER :                        '…-07:00\tp\tunheralded\t30 tool calls'
PROBE: the endswith clause, evaluated on the log BEFORE the drive runs: True
```

The preceding H-A drive already logged `unheralded / 30 tool calls`; the two lines differ only in
the session column, which the clause does not read. The added conjunct asserts something already
true at the moment it is evaluated.

The comment introducing it says W-INT logs `LARGE_TURN + 7` and *"this drive logs `LARGE_TURN + 5`
… Two different counts mean no constant satisfies both."* The second count is real and the
constant-freeze does die (measured in High 1) — but it dies through a line a **different** drive
wrote, and the growth property the case is named for is now unasserted. The fix is one word:
`and`, not replacement.

---

### Medium 3 — the first-stop CANNOT-RUN guard has an undefended term

`check-banner-armed.py:1111`:

```python
if armed_now is None and code == QUIET and judged is None:
```

Dropping `and judged is None` leaves the suite green and changes behaviour on an ordinary input — a
stop whose verdict about the judged turn is a sound QUIET, taken while the sentinel is momentarily
unreadable (which is what `begin-plan.py` writing it looks like for an instant):

```text
[first-stop-cannotrun-drops-judged-term] rc=0 150/150 self-test cases passed -> SURVIVOR

term under test: `and judged is None` at the first-stop CANNOT-RUN guard
  PRISTINE: stop1=QUIET  stop2=QUIET
  MUTANT  : stop1=QUIET  stop2=CANNOT RUN
  (judged turn u1 is a short unarmed bannerless turn; sentinel unreadable at stop 2)
```

The pristine behaviour is right — the unreadable sentinel is journalled as `armed: null` and
reported as CANNOT RUN on the *next* stop, where it actually bites. The mutant reports it a turn
early, about a turn whose verdict was sound. This repo treats CANNOT RUN as never a pass, so a
single edit that manufactures one is a cry-wolf on the channel that surfaces. Falsifier: the
scenario above, asserting QUIET at stop 2.

---

### Low 4 — the `last_judged_uuid` carry is undefended, and I could not show it reachable

`:1087`, `"last_judged_uuid": judged_uuid or (already or {}).get("last_judged_uuid")`. Replacing it
with a bare `judged_uuid` survives at 150/150. The carry preserves the exactly-once gate across a
stop with no subject, and nothing falsifies it.

⚠ **I did not construct a reachable input where the carry changes the outcome**, and record that
rather than assume it. Within one session the transcript only grows, so a stop that judged something
is normally followed by stops that judge something. The states where `judged_uuid` is `None` *after*
a judgement — a changed `transcript_path` under the same `session_id`, or an opener record without a
`uuid` — I could not produce from the driving surface. Filed as Low on the undefended term alone; if
the next round cannot reach it either, the honest close is a written reason on the line, not a case.

---

### Low 5 — a second undeclared crash barrier, two lines from the declared one

`:1135`:

```python
detail = f"{tool_uses_of(judged.body) if judged is not None else 0} tool calls"
```

Inside `if code == WARN:`, `reason` is non-empty only on the path where `judged is not None`, so the
`else 0` is unreachable. Removing it survives at 150/150 — an **equivalent mutant**, not a defect.

It is filed only because its sibling two lines above IS declared:

> *"⚠ THE `"?"` IS UNREACHABLE BY CONSTRUCTION AND IS KEPT ANYWAY, said out loud rather than left
> for the next reader to work out (r1 coordinator F2) … It is a crash barrier, not a branch; that
> is why no case asserts it."*

r1's coordinator F2 asked for exactly that sentence about exactly this kind of expression. The block
now has two such expressions and one sentence. One line of comment closes it.

---

## Attacked, and found sound

Reported so the next round does not re-spend the time.

**The manifest's own claim, re-run independently of the coordinator's sweep.** All 39 entries
applied to the staged copy, over a control proved green first, each required to redden the case its
`expect` names:

```text
CONTROL green: 150/150 self-test cases passed
…
39/39 killed, 0 survivors, 0 not attributed
```

**The pre-check's three properties** (`b31064ff` records that it regressed while being re-typed).
Parsed with `ast`, not regex — a first attempt with a regex reported 27 false orphans because it
mangled the non-ASCII in the case names, which is worth recording as its own small lesson:

```text
live case names: 150      ORPHANED expects: 0
ANCHORS not matching exactly once: 0      duplicate anchor strings: []
```

**Declared counts reconcile.** The docstring says 150 and the suite runs 150.
`EXPECTED_MUTATIONS["scripts/check-banner-armed.py"] == 39`, matching the file on disk; declared sum
**912**, on-disk sum **912**.

**W2b does real and unique work, across a four-wide band** — it is the *sole* red case for four
distinct threshold mutations, and with W2 it pins the boundary at exactly 24/25 from both sides:

```text
tool_uses >  LARGE_TURN       killed — W2b alone
tool_uses >= LARGE_TURN + 1   killed — W2b alone
tool_uses >= LARGE_TURN + 2   killed — W2b alone
tool_uses >= LARGE_TURN + 3   killed — W2b alone
tool_uses >= LARGE_TURN + 4   killed — W1, W2b, W5, W10, P2 and the message case
tool_uses >= LARGE_TURN - 3   killed — W2, W8, W-INT
tool_uses == LARGE_TURN       killed — 12 cases
tool_uses != LARGE_TURN       killed — 10 cases
tool_uses >= 0  /  True       killed — 9 cases
```

So the answer to *"does W2b pin the comparison, or something adjacent?"* is: the comparison. It is
the only case that can see the `>=` edge while `_BIG` is offset, and the band it covers alone is
`(LARGE_TURN, LARGE_TURN + 3]`. `7f79ac5b` is correct and its one line earns its place.

**The behavioural core of `decide` and `run_decide`.** Eighteen single edits that are NOT
derived-value freezes, all eighteen killed:

```text
unbannered-unticked-gt0-to-ge0   killed 149/150     judged-is-live             killed 121/150
finished-ge-to-gt                killed 141/150     steps-from-now             killed 149/150
logblock-banner-from-live        killed 148/150     unheralded-drop-paused     killed 145/150
logdetail-tooluses-from-live     killed 148/150     unarmed-drop-paused        killed 149/150
logblock-texts-from-live         killed 148/150     edited-from-live           killed 146/150
latecheck-strict-to-ge           killed 148/150     decide-tooluses-from-live  killed 144/150
logline-reason-frozen-unarmed    killed 146/150     warnlog detail/reason swap killed 144/150
cannotrun-blindness-drops-armed  killed 149/150     journal-write-swallowed    killed 121/150
logblock-unticked-swapped        killed 148/150     decide-texts-none-dropped  killed (crash)
```

Every substitution of the LIVE window for the JUDGED one — in the verdict, the edit scan, the tool
count, the banner recompute and the log detail — is caught. That is the round-3 class, and it is
closed.

`if code == WARN:` → `if code != QUIET:` survives and is an **equivalent mutant**: `:1106` returns
on CANNOT_RUN before `:1119` can be reached, so only QUIET and WARN arrive there. Not a defect;
recorded so it is not refiled.

**Round 4's other value changes, checked for what they were incidentally covering.** `_BIG`'s move
from 25 to 28 cost exactly one property — the `>=` boundary — and `7f79ac5b` restored it with W2b;
the band sweep above shows nothing else in that neighbourhood is uncovered. H-A4's reseed from
`p.md` (3 unticked) to `r.md` (2) loses nothing: its own falsifier still fires and the value is now
ambient nowhere. The H-B control's change is Medium 2. No other case was disarmed by the fold.

---

## The pre-committed stop condition

`docs/reviews/codex/banner-unheralded-r4-codex.md:164-167` records it, and it is answered here on
its own terms rather than softened:

> *"if round 5 finds a defect whose root is again* instance-not-class *or* ambient constant *— the
> two named above — then the discipline is not holding and the arming condition fires on its own
> terms. A finding with a **new** root does not fire it."*

Root, per finding:

| # | Root | One of r4's two? |
|---|---|---|
| 1 | **ambient constant** AND **instance-not-class** — a case satisfied by the constant its own single fixture supplies; the manifest entry pins the value tried, not the property | **both** |
| 2 | **ambient constant** — the clause is satisfied by a log line a different fixture wrote | **yes** |
| 3 | an uncovered branch term, pre-existing, not caused by any fix | no — new |
| 4 | an uncovered branch term, pre-existing | no — new |
| 5 | documentation of an equivalent mutant | not a defect |

**THE CONDITION IS MET.** There is no reading under which finding 1 escapes it. Its root is both of
the two named roots at once; it was caused by round 4's own fix — `_BIG` moved to `LARGE_TURN + 3`,
and `LARGE_TURN + 3` is precisely the constant that now survives; and it lands inside the repair
that was offered as the class-level answer, one of whose three hardened values turns out to be half
hardened. Rounds 3, 4 and 5 therefore carry findings caused by the previous round's fix, in one
component, three consecutive times — more than `docs/dev-process.md`'s arming condition requires.

**What that should mean in practice, said plainly.** The r4 document's decisive test is *can a
redesign remove it?* For this class the answer is yes, and the redesign is one property, stated in
High 1: *a case asserting a derived value must exercise its producer at two distinct inputs.* That
is a mechanical repair, not an architectural one, and I do not expect a Phase 6 review to be where
it gets designed. But the arming condition is a rule about process, not about my estimate of the
repair's size, and it was pre-committed by the party whose own fixes are under review — which is the
one circumstance in which it must not be re-argued by that party or by me. **It fires. Convene it**,
and note that this round hands it a concrete, mechanical answer rather than an open question.

One qualification I owe the reader: **round 4's answer to the four-rounds question was right about
the trajectory and wrong about the discipline.** It argued the rounds were "descending through
distinct mechanisms" with falling yield — r1 four, r3 nine, r4 one-plus-two. This round found nine
survivors in the single class r4 declared repaired *as a class*, in the same file, in the same kind
of value, one of them inside the repair itself. The yield did not fall. The sweep that reported
**7/7 caught, no constant survives** was measuring a corpus of its own choosing; the mechanical
enumeration is eleven sites, and it had reached three of them.

**VERDICT: NOT CONVERGED**

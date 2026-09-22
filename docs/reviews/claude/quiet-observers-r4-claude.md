# quiet-observers — round 4, Claude half

Subject: `9112886d` on `quiet-stop-observers-wt`.

REVIEW GAP: codex — rounds alternate; the Codex half ran as round 3

**Method.** Everything below was RUN, and every root claim is a parent-commit comparison rather
than an impression. Nothing under `scripts/` was modified in either worktree and no mutating `git`
command was issued: `scripts/` was copied to a scratchpad staging directory, every mutation was
applied to the COPY, and every child process ran under a redirected `$HOME`. For the ancestor
comparisons each commit's `scripts/begin-plan.py` was materialised with `git show <sha>:…` into a
temp directory and imported there, with `ROOT`/`SENTINEL`/`STATE`/`PLAN_DIR` redirected into a
`tempfile.TemporaryDirectory()` — the same technique round 3 used. `check-plan-code.py --mutate .`
was **not** run (the brief forbids it, and one was in flight in the other tree); finding 1 is
instead measured by calling the delivered harness's own `run_mutations` on the single entry at
issue, which costs nothing because it refuses before running any suite.

Controls, in the worktree and again on the staged copy, all green before any mutation and
re-proved green after the last restore:

```
python3 scripts/begin-plan.py --self-test           60/60 self-test cases passed   rc=0
python3 scripts/check-plan-progress.py --self-test  43/43 self-test cases passed   rc=0
python3 scripts/check-ci-watched.py --self-test     32/32 self-test cases passed   rc=0
staged copy, $HOME redirected: begin-plan          60/60 self-test cases passed   rc=0
```

## Findings

| # | Severity | Root | Introduced by r3's fix? |
|---|---|---|---|
| 1 | **Blocking** | `843bada6` (the **r2 fold**) orphaned a mutation anchor in `scripts/mutations/check-plan-progress.json`; `--mutate .` is a required CI step and fails on it | **No** — round 2's fix |
| 2 | Medium | The `paused_unticked` producer is unfalsifiable BY VALUE — a constant and the DONE count both survive 60/60. Present identically at `5018606b`, the original fix | **No** — pre-existing |
| 3 | Medium | The (`paused` present, stamp ABSENT) corner: `--pause` invents a baseline and converts a live WARN into permanent silence. r2's Medium 3, unfixed in one corner. Identical at all four commits | **No** — pre-existing |
| 4 | Low | r3's new VERDICT case asserts `!= WARN`, a negative satisfied by BLOCK. Measured: it never reddens alone, and stays GREEN on the one mutation that breaks the verdict without breaking the field | **YES** |
| 5 | Low | `9112886d`'s commit message and dashboard entry both say the new case runs "9 against a 2-outstanding plan". Measured, it runs against a **1**-outstanding plan | **YES** |

---

### 1 — Blocking: a manifest anchor that binds ZERO times, in a required CI step

`scripts/mutations/check-plan-progress.json` entry 12 anchors on four lines of
`check-plan-progress.py` — three comment lines plus `return ALLOW, "", None`:

```json
{
  "name": "the quiet branch WARNS again, restoring the every-stop notice the user reported",
  "file": "scripts/check-plan-progress.py",
  "edits": [[
    "        # Paused, nothing ticked since: genuinely waiting. Allow, and say nothing — the state is\n        # already visible in the sentinel and in `--banner`, and repeating it every stop is what\n        # made it unreadable.\n        return ALLOW, \"\", None",
    "        return WARN, f\"⏸ PAUSED ({unticked} of {total}) — {paused}\", None"
  ]],
  "expect": ["paused, NOTHING ticked since -> ALLOW and SILENT: the genuinely-waiting case, …"]
}
```

That text is not in the file. Run over **every** entry in **every** manifest — the population is
`scripts/mutations/*.json`, 905 anchors across 52 files, derived by globbing rather than by eye:

```
905 anchors checked; problems: [('check-plan-progress.json', 'the quiet branch WARNS again, restoring ', 0)]

real	0m0.303s
```

Exactly one, and it is this one. Not my own string comparison but **the delivered harness's own
verdict**, obtained by calling `check-plan-code.run_mutations` on that single entry against the
staged tree:

```
THE DELIVERED HARNESS, run on entry 12 of scripts/mutations/check-plan-progress.json:
  ok      = False
  report  = ["mutation 'the quiet branch WARNS again, restoring the every-stop notice the user
             reported': anchor NOT FOUND — it was not applied, so its 'caught' verdict would be
             meaningless"]
  measured= []
```

**This is a red required check.** `.github/workflows/ci.yml:436` runs
`python3 scripts/check-plan-code.py --mutate .` unconditionally, and the comment block directly
above it states the contract this violates in as many words: *"FAILS IF: a mutation survives · **an
anchor is missing or ambiguous** · a suite times out …"*.

**Root, by bisecting the anchor across the branch.** `git show <sha>:scripts/check-plan-progress.py`
for each commit, counting the anchor:

```
9112886d  the r3 fold (SUBJECT)          anchor occurrences = 0
b561e048  round 3's review doc           anchor occurrences = 0
843bada6  the r2 fold                    anchor occurrences = 0   <-- orphaned HERE
5018606b  the ORIGINAL fix               anchor occurrences = 1
84131ec0  the dashboard entry            anchor occurrences = 1
```

And the cause, from `git show 843bada6 -- scripts/check-plan-progress.py`:

```
-        # Paused, nothing ticked since: genuinely waiting. Allow, and say nothing — the state is
+        # Paused and the outstanding count did NOT fall. Allow, and say nothing — the state is
```

That is **round 2's Low 6 fix** — the "genuinely waiting" overclaim I filed in round 2 — landing on
a comment that a mutation anchor was bound to. Anchors bind by TEXT. Round 3 did not look, and
`9112886d` did not fix it.

**Why no gate caught it, which is the part worth keeping.** Five gates are green over this
breakage, and I ran all five:

```
check-review-rounds      rc=0   318 parsed, 0 silent gaps
check-dashboard-entry    rc=0   ok — an entry block was added
check-docs               rc=0   Documentation integrity OK
check-selftest-counts    rc=0   45 script(s) declare a count, every one verified by running it
check-ratchet-contract   rc=0   ratchet contract OK
check-plan-code --self-test  rc=0   128/128 passed
```

The arithmetic gate is green too, and it is the one that looks like it covers this:

```
on-disk manifest: 897 entries across 52 files
declared sum:     897 across 52 entries
AGREE
```

It counts **entries**, not **resolvable anchors**, so a manifest whose entry has stopped naming any
code balances perfectly. The only thing that reads the anchors is the 35-minute sweep, and no sweep
has run since `843bada6`: round 1 recorded 890/890 against `5018606b`'s code, round 2 explicitly
declined to re-run, round 3 did not run it. So the orphan has been live for three rounds with every
cheap gate green.

`843bada6`'s own message states the gap precisely, without noticing it:

> Manifest +6; declared sum 890 -> 896. **Every new entry** verified by hand to redden the case it
> names, over a control proved green first…

*New* entries. The entry this commit broke was an old one, and nothing re-checked those.

⚠ The irony is load-bearing rather than decorative. `check-plan-code.py:1264` — a comment inside the
very file whose gate this is — reads: *"Anchors bind by TEXT, so rewording a comment orphaned a
mutation; that happened five times in one session."* This is the sixth.

**What is lost, not just what is red.** The orphaned entry guards
`paused, NOTHING ticked since -> ALLOW and SILENT` — the quiet branch, which is *the entire
deliverable of this slice*. Its mutation (make the quiet branch WARN again, restoring the every-stop
notice the user reported) is the one that proves the noise removal is real. It fails loud rather
than silently under-covering, which is the right direction, but the branch cannot merge until the
anchor is retargeted.

---

### 2 — Medium: the stamp's VALUE has no falsifier — a constant and the DONE count both survive

`cmd_pause`'s producer is `_stamp = f"paused_unticked: {_total - _done}\n"`. Three mutations against
the staged copy, control proved green first and re-proved after:

```
CONTROL                                                      rc=0  60/60
M1 the recomputed stamp becomes the CONSTANT 1               rc=0  60/60   <- SURVIVES
M2 the stamp writes the DONE count instead of the outstanding rc=0  60/60   <- SURVIVES
M3 (reference) the stamp writes the TOTAL                    rc=1  55/60   killed
restored CONTROL                                             rc=0  60/60
```

M1 replaces the whole producer with a literal. M2 writes `{_done}`. Both leave every case green.

The self-test's own comment asserts the opposite, in the case written to prevent exactly this:

```python
# ⚠ THE VALUE, NOT MERELY THE KEY. The plan here is 2 steps with 1 ticked, so a stamp
# that wrote a constant, or the TOTAL, or the DONE count would all still be present —
# and the guard compares this number, so a wrong one silently changes its verdict.
case("...and it is the OUTSTANDING count, not the total and not the done count", …)
```

The TOTAL half is true (M3 dies). The **constant** and **DONE count** halves are false, and for one
reason: the only plan any stamped case is taken over is 2 steps with 1 ticked, where
`outstanding == done == 1`. The producer is exercised at **one** distinct input across the whole
suite, so the repo's rule — *a case asserting a derived value must exercise its producer at two
distinct inputs* — is unmet, and the constant equal to that literal satisfies it.

The case immediately above it in the file shows what the fix looks like; it was written for r2's
Medium 3 and says so:

> ⛔ TWO DISTINCT INPUTS BY CONSTRUCTION, and the case is worthless without them … Pausing twice at
> the SAME count would pass whether or not the fix is present, which is this repo's recorded
> ambient-constant shape.

**Root — same two mutations against every ancestor's `begin-plan.py`:**

```
9112886d  the r3 fold (SUBJECT)        M1 constant 1  rc=0 SURVIVES 60/60   M2 DONE  rc=0 SURVIVES 60/60
b561e048  r3's doc (== r2 fold code)   M1 constant 1  rc=0 SURVIVES 58/58   M2 DONE  rc=0 SURVIVES 58/58
843bada6  the r2 fold                  M1 constant 1  rc=0 SURVIVES 58/58   M2 DONE  rc=0 SURVIVES 58/58
5018606b  the ORIGINAL fix             M1 constant 1  rc=0 SURVIVES 53/53   M2 DONE  rc=0 SURVIVES 53/53
(reference) M3 TOTAL killed at all four: 55/60, 55/58, 55/58, 51/53)
```

Identical at every commit including the original fix. **Not introduced by round 3, and not by round
2** — it has been there since the field was invented, and `--mutate .`'s 0-survivor result is silent
about it because the manifest's entry for this line mutates `if _total:` to `if False:` and is
attributed to *"…and writes NO stamp"* — it tests the stamp's **presence**, never its value.

---

### 3 — Medium: a `--pause` restatement over a stamp-less pause erases a live WARN

Round 2's Medium 3 was *a second `--pause` silently erases an already-firing #99 warning*. The
r2 fold fixed it where the first pause left a stamp. Where it did not, the defect is unchanged.
Driven end to end against the real commands, control first:

```
B4  HAND-EDITED park (no stamp) -> hand-tick 2 -> `--pause` to restate
   after the hand pause:      WARN  ⏸ PAUSED (4 of 4 outstanding, no count recorded, so whether work resumed c…
   after hand-ticking 2:      WARN  ⏸ PAUSED (2 of 4 outstanding, no count recorded, so whether work resumed c…
   after --pause (rc=0): stamp='2'  ALLOW
```

The middle line is the guard correctly refusing to claim it knows. The last line is that refusal
converted into a definite, permanent silence by a command that never mentions the stamp. Two steps
were ticked while the guard was stood down and nothing will ever say so.

This is not an exotic route. `decide`'s own BLOCK message instructs the human into it:

```
• handing back to the human     → add a line `paused: <why>` to .claude/executing-plan
• BLOCKED ON IN-FLIGHT WORK     → add a line `paused: waiting on <what>` to .claude/executing-plan
```

A pause created that way has no stamp by construction, and the natural next act — running
`--pause "…"` properly — is what discards the signal.

**Root, same scenario against every ancestor:**

```
9112886d  the r3 fold (SUBJECT)        hand pause WARN -> tick 2 WARN -> after --pause  ALLOW  stamp='2'
b561e048  r3's doc (== r2 fold code)   hand pause WARN -> tick 2 WARN -> after --pause  ALLOW  stamp='2'
843bada6  the r2 fold                  hand pause WARN -> tick 2 WARN -> after --pause  ALLOW  stamp='2'
5018606b  the ORIGINAL fix             hand pause WARN -> tick 2 WARN -> after --pause  ALLOW  stamp='2'
```

Byte-identical at all four. **Not introduced by round 3.** It is the uncovered corner of round 2's
own fix: r2 keyed preservation on the stamp being present, r3 re-keyed it on `paused` being present,
and neither reaches `paused` present with the stamp absent, where `_prior` is `None` either way and
the `else` branch recomputes.

⚠ **The repair is a hypothesis and I am labelling it one.** The shape that follows from r2's own
stated principle — *"Restating a reason is not resuming work, so the count from when the work was
ACTUALLY parked is the right one to keep"* — is: when `paused` is already present and there is no
stamp, write **no stamp**, because the pause did not begin now and there is no honest number to
write. That keeps the "cannot tell" verdict the guard had already earned. Whether that is the right
trade against backlog #56's nag verdict is a decision, not a derivation, and I have not made it.

---

### 4 — Low: r3's VERDICT case asserts a negative that a BLOCK satisfies — introduced by r3's fix

`9112886d` added two cases and its message argues the second is the important one:

> TWO cases, not one: the FIELD (the mechanism) and the VERDICT (the property). A case asserting
> only the field would stay green under a `decide` that reached the same wrong answer by another
> route.

```python
case("...and the very next stop does NOT claim steps were ticked",
     pp.decide(SENTINEL.read_text(), plan_on_disk.read_text(), None, False)[0]
     != pp.WARN)
```

The true verdict in that state is `ALLOW` (0). `!= WARN` is also satisfied by `BLOCK` (2) — and
`BLOCK` is what `decide` returns when the sentinel is **not paused at all**, which is a strictly
worse failure than the one the case is watching for. Measured, with per-case FAIL attribution:

```
M5 the manifest entry: r3's guard removed          rc=1   2 red
     • [FAIL] a stray `paused_unticked:` with no `paused:` is NOT inherited as a baseline…
     • [FAIL] ...and the very next stop does NOT claim steps were ticked: got False want True

M6 r3's guard INVERTED                             rc=1   3 red   (both of the above, + r2's case)
M7 keyed on `armed` instead of `paused`            rc=1   2 red   (both of the above)

M8 --pause writes the stamp but NOT the `paused:` line   rc=1  16 red
     • [FAIL] cmd_tick REFUSES on a paused plan
     • [FAIL] the refusal names --resume, the only exit from a pause
     • … 14 more …
     (the VERDICT case is NOT among them)
restored control rc=0 | 60/60 self-test cases passed
```

So: across every mutation that reaches this code the VERDICT case reddens **only** where the FIELD
case already reddens — it has never distinguished anything — and under M8, the one mutation that
breaks the verdict *without* breaking the field, it stays **green**. That is exactly the scenario
its own comment claims it exists to catch. Sixteen other cases kill M8, so the suite is not blind;
the case written to be the property assertion is.

`== pp.ALLOW` (or `(ALLOW, "")`, since silence is the property this branch delivers) would be red
under M8 and costs nothing.

**Root: `9112886d`. Introduced by round 3's fix** — the case did not exist before it.

---

### 5 — Low: the new case's stated input is wrong in two places — introduced by r3's fix

`9112886d`'s commit message, and the dashboard entry it added verbatim:

> ⚠ The stray stamp is deliberately FAR from the true count — **9 against 2 outstanding** — so
> neither case can pass by the two numbers happening to agree.

Measured, by probing the suite at that exact line on the staged copy:

```
  PASS  --pause records the outstanding count at pause time
   [probe] plan at the orphan case (done,total) = (1, 2) -> OUTSTANDING = 1
  PASS  a stray `paused_unticked:` with no `paused:` is NOT inherited as a baseline…
```

The plan is restored to `_plan_paused` immediately above, which is the 2-step plan with 1 ticked.
The case runs against **1** outstanding, not 2. The claim's *substance* survives (9 is far from 1
too, so neither case can pass by agreement), but the number does not — and the "2 outstanding" comes
from round 3's own temp-root probe, not from the case the sentence is about. Two artefacts now
carry it, one of them the dashboard, which is what a reader away from the work reads.

It matters more than a typo because 1 is the value that makes finding 2 true: at
`(done=1, total=2)`, `outstanding == done`, which is why the DONE-count mutation survives. The
sentence asserting the case cannot pass by two numbers agreeing is printed over the one input where
two other numbers do.

---

## The thrashing question, answered on its own terms

The pre-committed arming condition (`docs/dev-process.md`): **two consecutive rounds whose findings
came from the previous round's own fix, in one component.** Round 3's Medium came from round 2's
fix. The question is whether round 4's come from round 3's.

Per finding, with the evidence above:

| # | Severity | Root commit | From r3's fix? | Evidence |
|---|---|---|---|---|
| 1 | Blocking | `843bada6` — the **r2 fold**'s Low-6 comment rewrite | No | anchor count 1→0 bisected across five commits; the orphaning diff quoted |
| 2 | Medium | `5018606b` — the original fix | No | M1/M2 survive at all four commits, M3 dies at all four |
| 3 | Medium | pre-existing at `5018606b` | No | the same drive produces byte-identical output at all four commits |
| 4 | Low | `9112886d` — **r3's fix** | **Yes** | the case did not exist before it |
| 5 | Low | `9112886d` — **r3's fix** | **Yes** | the sentence did not exist before it |

**The literal answer is that it arms.** Round 4 carries findings introduced by round 3's own fix
(4 and 5), in the same component as round 3's Medium (`cmd_pause` and its suite), immediately after
a round whose finding was introduced by round 2's fix. Two consecutive rounds, the stated condition,
met.

**I am not narrowing the rule to avoid that, and I want to be explicit about the temptation.** The
narrowing available is "Low findings in the test layer shouldn't count" — but that clause is not in
the condition, it would be authored here by the party who would pay for it, and this repo records
*a retreat you author for yourself is not a gate* as a measured failure. The right move if the
condition is mis-specified is to respecify it deliberately, not to read it down in the round that
would trip it.

**What the coordinator should weigh alongside that, stated as data rather than as an escape:**

- The **character** differs from the shape the condition was bought for. There, the same component
  produced a **Blocking or High in six consecutive rounds, four introduced by the previous fix**.
  Here round 3's r2-caused finding was a Medium in delivered behaviour; round 4's two r3-caused
  findings are both **Low**, and both are in the *assertions about* the fix — a weak `!=` and a
  wrong number in a commit message — not in what `--pause` does. The delivered behaviour of r3's fix
  is, as far as I could drive it, correct in every corner (see below).
- The **dominant** finding this round is neither r3's nor a new root. It is an **r2 casualty that
  three rounds and six gates missed for three commits**, and its class — *a fix reworded a comment
  and orphaned the mutation anchored to it* — is one this repo has already recorded five times in
  `check-plan-code.py`'s own comments. That is a real structural signal, but it points at
  anchor-binding being unguarded outside the 35-minute sweep, not at `cmd_pause` being thrashed.
- Findings 2 and 3 are **older than the branch**, and neither round 1, 2 nor 3 reached them. Rounds
  are still finding new ground here, which is the opposite of the exhaustion signal thrashing
  describes.

If the condition fires, the cheapest thing Phase 6 could usefully take as its subject is not
`cmd_pause` but **the anchor-binding gap finding 1 exposes**: a 0.3-second whole-manifest
resolution check exists (I ran it), nothing in CI runs it short of the sweep, and the arithmetic
gate that looks like it covers it counts entries rather than anchors.

---

## Attacked, and found sound

So round 5, if there is one, does not re-spend the time.

* **The state space of (`paused`?, `paused_unticked`?, stamp validity) — eleven corners, each
  hand-built into the sentinel and driven through the real `cmd_pause`.** Plan = 4 steps, 1 ticked,
  3 outstanding. `--pause`'s handling is correct in every one except the stamp-less corner
  (finding 3):

  ```
  paused ABSENT, stamp ABSENT   (a first, normal pause)   BLOCK -> rc=0 stamp='3' -> ALLOW      ✓
  paused ABSENT, stamp 9        (r3's corner: the ORPHAN) BLOCK -> rc=0 stamp='3' -> ALLOW      ✓ the fix
  paused PRESENT, stamp 9       (a restatement)           WARN  -> rc=0 stamp='9' -> WARN       ✓ baseline kept
  paused PRESENT, stamp ABSENT  (a HAND-EDITED pause)     WARN  -> rc=0 stamp='3' -> ALLOW      ⛔ finding 3
  paused PRESENT, stamp ''                                WARN  -> rc=0 stamp=''  -> WARN       ✓ garbage kept, stays loud
  paused PRESENT, stamp 'soon'                            WARN  -> rc=0 stamp='soon' -> WARN    ✓
  paused PRESENT, stamp '-1'                              WARN  -> rc=0 stamp='-1' -> WARN      ✓
  paused PRESENT, stamp ' 9 '   (padded)                  WARN  -> rc=0 stamp='9'  -> WARN      ✓ normalised
  paused with EMPTY value, stamp 9                        WARN  -> rc=0 stamp='9'  -> WARN      ✓
  COLONLESS `paused` line, stamp 9                        BLOCK -> rc=0 stamp='3' -> ALLOW      ✓ treated unpaused
  TWO paused lines, TWO stamps (5 then 9)                 WARN  -> rc=0 stamp='9'  -> WARN      ~ see below
  ```

  The three invalid-stamp corners preserve the garbage verbatim, and `decide` reads any
  non-`isdigit` value as absent → WARN. So preservation fails **loud**, which is the direction this
  guard must fail in. The doubled-sentinel corner keeps the LAST stamp (9) rather than the FIRST (5)
  — `parse_sentinel` is last-wins — but strip-before-append means no supported command can produce
  a doubled sentinel any more, so reaching it needs a hand edit that has already written two
  baselines. Noted, not filed.

* **`"paused" in _fields` (what `cmd_pause` asks) vs `fields.get("paused") is not None` (what
  `decide` asks) — do they agree?** Population enumerated by hand over every shape the two rules
  could disagree about, and they agree on all eight:

  ```
  line                     cmd_pause: `in _fields`    decide: paused is not None   agree?
  'paused: why'            True                       True                         YES   (ordinary)
  'paused:'                True                       True                         YES   (empty value)
  'paused'                 False                      False                        YES   (NO COLON)
  '  paused: why'          True                       True                         YES   (leading space)
  'paused : why'           True                       True                         YES   (space before the colon)
  'Paused: why'            False                      False                        YES   (capitalised)
  'paused: a: b'           True                       True                         YES   (a colon in the value)
  'xpaused: why'           False                      False                        YES   (a longer key)
  ```

  They cannot disagree by construction: `parse_sentinel` only ever stores `str`, so membership and
  `is not None` are the same predicate. `decide`'s own comment (`check-plan-progress.py`, the
  `paused = fields.get("paused")` block) records exactly this, and r3 picked the membership form on
  the writer side — different spelling, same rule. Sound.

* **Lifecycle sequences the brief named, all driven against the real commands on a temp root:**

  ```
  B1  --resume -> --pause -> --finish -> --pause   (fresh 4-step plan)
     --resume  rc=1  sentinel exists=True   (refuses: not paused — "never invents a state")
     --pause   rc=0  sentinel exists=True   {..., 'paused': 'reason for pause', 'paused_unticked': '4'}
     --finish  rc=0  sentinel exists=False
     --pause   rc=1  sentinel exists=False  (refuses: nothing armed)

  B2  --pause when the sentinel names a plan that NO LONGER EXISTS
     rc=0  fields={'plan': …, 'armed': …, 'paused': 'parked, and the plan file is gone'}  (NO stamp)
     verdict: WARN  ⏸ PAUSED (parked, and the plan file is gone) — and CANNOT RUN: …
     a SECOND --pause in that state: rc=0, still no stamp, still WARN + CANNOT RUN

  B3  park -> hand-tick 2 -> park again  (r2 Medium 3's own scenario, WITH a stamp)
     after pause 1: stamp='4'  ALLOW
     after hand-ticking 2:     WARN  ⏸ PAUSED, BUT 2 STEP(S) WERE TICKED SINCE …
     after pause 2: stamp='4'  WARN  ⏸ PAUSED, BUT 2 STEP(S) WERE TICKED SINCE …   <- the fix HOLDS
  ```

  B3 is the direct confirmation that r2's Medium 3 is genuinely fixed in the stamped corner, and B2
  that r2's Medium 2 (the unreadable-plan escape) holds through a repeat — the second pause cannot
  inherit, because there is nothing to inherit, and it stays honestly stamp-less rather than
  inventing a number.

* **r3's fix itself is falsifiable, three ways, not just the one in the manifest.** Beyond the
  manifest's own entry (M5), two further mutations of the same predicate die on the named case:
  inverting it (`"paused" not in _fields`, M6 — 3 red) and keying it on a field every sentinel has
  (`"armed" in _fields`, M7 — 2 red). So the case is pinned to `paused` specifically, not merely to
  *some* condition being present. Controls green before and after.

* **The manifest arithmetic is real, not merely self-consistent.** `check-plan-code.py --self-test`
  asserts `sum(EXPECTED_MUTATIONS.values()) == 897`, which is the dict agreeing with a literal.
  Checked against the JSON on disk instead: `897 entries across 52 files` on disk vs
  `897 across 52 entries` declared, no disagreements, and `begin-plan.json` on-disk 15 / declared
  15 — the `14 → 15` and `896 → 897` in the diff both land. ⚠ And this check is what finding 1
  shows to be **blind to anchor resolution**.

* **The two re-targeted manifest entries `9112886d` claims DO bind.** The whole-manifest anchor
  resolution run reports exactly one problem across 905 anchors, and it is in
  `check-plan-progress.json`, not `begin-plan.json`. The retarget itself was done correctly; the
  claim that a check over "every entry in the manifest" caught the class is what did not hold — the
  same run, over the real population, takes 0.3 seconds and reports the orphan.

* **Attribution of the new manifest entry.** M5 (the entry's own mutation) reddens two cases, and
  the `expect` names the FIELD case, which is among them — so `run_mutations` would attribute it
  correctly rather than by coincidence. Verified by capturing the suite's `[FAIL]` lines rather than
  by reading the JSON.

* **Branch gates, all green, and that is finding 1's point rather than a reassurance:**
  `check-review-rounds` rc=0 · `check-dashboard-entry` rc=0 · `check-docs` rc=0 ·
  `check-selftest-counts` rc=0 (45 scripts, each verified by running it — so the `58 → 60` docstring
  update is real) · `check-ratchet-contract` rc=0 (40 guards) · `check-plan-code --self-test` rc=0
  (128/128).

* **`check-plan-code.py --mutate .` was NOT run** — the brief forbids it and one was in flight in
  the sibling tree. This is a stated gap, not a pass: finding 1 says what it would report, measured
  through the harness's own `run_mutations` on the failing entry, and nothing here should be read as
  evidence that the other 896 entries are green. Round 1's 890/890 was taken against `5018606b`'s
  code and three commits have landed since.

**VERDICT: NOT CONVERGED**

Finding 1 is Blocking and cheap: retarget the anchor in
`scripts/mutations/check-plan-progress.json` onto the text that is now in
`check-plan-progress.py`, and re-run the sweep, since no sweep has read this manifest since
`843bada6`. Findings 4 and 5 are one-line corrections in the same commit's work. Findings 2 and 3
are older than the branch and are the only two that need a decision rather than an edit.

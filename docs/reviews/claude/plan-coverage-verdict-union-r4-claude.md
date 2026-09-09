# Post-Plan Gate — backlog #91, round 4, CLAUDE half

Subject: **round 3's own fixes** — `mut_readable` as a fifth return value, both `check()` returns
reading it, the `assembled`/`dropped` census, `verify_evidence`'s `mode`, and the 33 → 41 manifest —
on branch `coverage-verdict-union-91`.
Reviewer: Claude adversarial half. Date: 2026-09-08.

**Verdict: NOT CONVERGED** — 0 Blocking, 1 High, 2 Medium, 2 Low.

⚠ **THE SUBJECT MOVED TWICE WHILE I MEASURED, AND I VERIFIED WHAT I HELD RATHER THAN ASSUMING IT.**
I was briefed at `0a6f6319`. Partway through, `scripts/check-plan-code.py:295` no longer held the
line the brief quotes: the coordinator had already split the r3 list-validation into two branches and
named `honest_zero`, in the working tree, in response to Codex's r4 half. By the time I finished,
that delta was committed as **`746178f6`** ("CI refused two anchors my own sweep cleared").

**Everything below was measured against that content.** The staged tree, the control, the eleven
reverts, the six census fixtures and the three CLI runs all ran after the split existed, so this
review is about `746178f6`, not `0a6f6319`. **HEAD as reviewed: `746178f6`.** Where a finding also
holds at `0a6f6319` and earlier I say so with a per-revision table, because "is this a regression?"
is the question the round-4 trigger turns on.

The coordinator then flagged the same move and asked for the split to be attacked as a subject in
its own right — *does it change behaviour, is `honest_zero` read where it should not be, are the two
new anchors fragile?* **§ The split, attacked directly** answers all three with measurements, and it
is where **M2** comes from.

⭐ **The one High is NOT a regression from round 3's fix — and that is the headline.** Rounds 1, 2
and 3 were 3/3, 3/3 and 3/4 regressions from the previous round's own fixes. Round 4's High is a
defect that has been on this line since **`master`**, which round 3's fix declared closed in a
comment and did not close. Different shape, and the Trajectory section at the end argues it changes
what the fourth round means.

---

## What was EXECUTED

Controls first, and the brief is right that a scripts-only copy makes every verdict under it an
artefact. The tree was staged with the harness's own `stage_tree`, and the control was proved green
**before** any mutation verdict was taken.

| run | result |
|---|---|
| `check-plan-code.py --self-test` (repo) | **223/223**, rc 0 |
| `coverage_verdict.py --self-test` (repo) | **22/22**, rc 0 |
| `stage_tree(REPO, dest)` | `problems: NONE — tree complete`; all four `HARNESS_TREE` entries present (`scripts`, `supabase`, `docs`, `node_modules/typescript`) |
| `run_suite(dest, 'scripts/check-plan-code.py')` in the staged tree | **223/223**, `control_is_green: True` — **CONTROL GREEN**, and every verdict below rests on it |
| `run_suite(dest, 'scripts/coverage_verdict.py')` in the staged tree | **22/22**, green |
| 11 revert-mutations via the harness's own `run_mutations` | **11/11 caught, measured, `survivors: []`** — table in *§ vacuity* |
| static anchor sweep, all 32 manifests | **375 edits, 0 orphaned, 0 ambiguous**; 41 entries, 41 unique names, 0 duplicate anchor tuples |
| 6 census fixtures through `extract()` + `check()` + `evidence()` | table in **H1** |
| 3 refusal causes through `check()` + `evidence()` | table in **M1** |
| 2 real CLI runs (`--compare … --evidence`) | verbatim output in **H1** |
| the same non-python fixture replayed against `master`, `7e2ad668`, `ea2566cc`, `0a6f6319` | regression table in **H1** |
| `check-selftest-counts.py` | rc 0 — 29 scripts declare a count, every one verified by running it |
| `check-docs.py` | rc 0 |
| `check-ratchet-contract.py` | rc 0 |
| `check-producer-enumeration.py` | rc 0 |
| `check-vocabulary-collisions.py --self-test` | rc 0, 10/10 |
| `check-review-rounds.py` | **rc 1** — and the reason is *this file's absence*: `plan-coverage-verdict-union round 4: only codex — claude neither ran nor recorded a REVIEW GAP: line`. It goes green when this review lands |
| `EXPECTED_MUTATIONS` | sum **370**, `scripts/check-plan-code.py` → **41**, both pinned by cases |
| `load_manifests(REPO)` — **the harness's own loader, not a copy of its rule** | **370 entries, `problems: NONE`** |
| differential `extract()` old (`0a6f6319`) vs new (`746178f6`), 19 inputs | **0 behaviour differences** — table in *§ The split* |
| both split messages collapsed to one identical string, staged tree | **223/223 passed** — the basis of **M2** |
| the 2 manifest entries pinning those branches, under that same collapse | both still `caught` |
| orphan prediction for **M1's** fix, applied to a copy, all 41 anchors re-resolved | **entry 23 ORPHANS** |
| orphan prediction for **H1's** fix, same method | **0 orphaned** |

**NOT RUN:** `check-plan-code.py --mutate .`, as instructed. Every mutation verdict came from the
harness's own `run_mutations()` on the staged copy; I did not re-implement the kill rule.

---

## HIGH

### H1 — `assembled` STILL has two owners. A file tagged with a non-python fence enters `files` without incrementing the census, so one durable block prints `0 assembled` two lines above `1 blocks assembled`.

Round 3's H3 fix is stated at `scripts/check-plan-code.py:1425-1428` as a closed class:

> *"⟳ code review r3, H3. **ONE OWNER FOR THE WORD "assembled", and it is `files`.**"*

It is not. The census is incremented in the `is_py` branch — `:254-256`:

```python
            if is_py:
                py_total += 1
                if pending:
                    py_tagged += 1
                    tagged_by_name[pending] = tagged_by_name.get(pending, 0) + 1
```

but a block enters `files` **outside** that branch, and deliberately so — `:266-270`:

```python
            if pending:
                if f.group(1) != "python":
                    problems.append(f"block for {pending!r} is tagged ```{f.group(1)}, not ```python")
                files.setdefault(pending, []).append(text)
                pending = None
```

The problem is reported and **the block is assembled anyway**. So `files` holds a name the census
never counted, and the renderer prints both numbers four lines apart — `:1436` and `:1444`.

**MEASURED — the real CLI, verbatim.** Plan is two lines: `<!-- file: a.py -->` and a ```` ```bash ````
block.

```
$ python3 scripts/check-plan-code.py e2e/planB.md --compare .../scripts --evidence
```
GENERATED by scripts/check-plan-code.py — do not edit by hand.

  python fences: 0 (0 assembled, 0 illustrative)          <-- ZERO assembled

  a.py                          1 blocks assembled -> SyntaxError: invalid syntax   <-- ONE assembled

  subject: the plan's blocks, DIFFED against the delivered files:
    MISSING    a.py

  NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
  mutation entries recorded: 0
```
```

That is r3 H3's sentence unchanged — *"one word carrying two meanings inside one block"* — printed
by the same renderer, on the same page, after the fix that says it has one owner.

**The full enumeration the brief asked for.** Six fixtures, every line `evidence()` can emit, checked
pairwise against one run's facts:

| fixture | census line | per-file line | agree? |
|---|---|---|---|
| A one tagged python block | `1 (1 assembled, 0 illustrative)` | `a.py 1 blocks assembled` | ✅ |
| **B one tagged BASH block** | `0 (0 assembled, 0 illustrative)` | `a.py **1** blocks assembled` | **⛔ NO** |
| **C python + bash, same name** | `1 (**1** assembled, 0 illustrative)` | `a.py **2** blocks assembled` | **⛔ NO** |
| D dropped python block (r3's fixture) | `1 (0 assembled, 1 tagged then DROPPED, 0 illustrative)` | — | ✅ (this is the route r3 fixed) |
| **E dropped BASH block** | `0 (0 assembled, 0 illustrative)` — **no DROPPED clause at all** | — | **⛔ the drop is INVISIBLE** |
| F good python file + dropped bash file | `1 (1 assembled, 0 illustrative)` | `a.py 1 blocks assembled` | ⛔ the drop is invisible |

Row E is the second half of the same defect and it fails r3's *other* stated rationale verbatim:
`:339-340` deducts `tagged_by_name.get(name, 0)`, and `tagged_by_name` only ever counts **python**
fences (`:256`), so a tagged-then-dropped non-python block decrements zero and announces nothing.
The comment at `:332-334` says the drop is stated *"because an exclusion nobody can see is the hiding
vector this renderer already refuses for illustrative blocks."* On row E nobody can see it.

**MEASURED as PRE-EXISTING, not a regression** — same fixture, four revisions:

| revision | `files` | census key | value |
|---|---|---|---|
| `master` | `{'a.py': 1}` | `tagged` | **0** |
| `7e2ad668` r2 fold | `{'a.py': 1}` | `tagged` | **0** |
| `ea2566cc` | `{'a.py': 1}` | `tagged` | **0** |
| `0a6f6319` / `746178f6` | `{'a.py': 1}` | `assembled` | **0** |

So this is not round 3's fix breaking something. It is round 3 fixing the instance it was shown,
writing a comment asserting the class was closed, and leaving the sibling route standing — this
project's recorded *instance-not-class* shape, and the same shape r3's own H1 filed against r2.

**⛔ THE 223-CASE SUITE IS BLIND TO IT IN BOTH DIRECTIONS.** I applied the most plausible fix (move
the increment to the site where a block enters `files`, so `assembled` counts what `files` holds) and
ran the whole suite in the staged tree:

```
FIXED tree self-test rc: 0 | 223/223 passed
```

Nothing goes red when the contradiction is *removed*, and nothing goes red when it is *present*. The
r3 case at `:1836-1838` asserts `"(1 assembled, 0 illustrative)"` on a python fixture only, so the
non-python route has no case at either polarity.

**Severity — High, by the coordinator's own consistency argument, with the mitigator stated.**
Row B's run is already `ok=False` and already prints ``✗ block for 'a.py' is tagged ```bash`` on the
console. That is a genuine mitigator and I am not hiding it. But it is *identical* to r3 H3's
fixture, which was adjudicated High on exactly those terms (r3's own H1 note records that r2 H3 was
High "on a constructed fixture with `ok=False` and the problem in the report"), and the argument r3
used is the one that still applies: **the console line dies with the terminal and the evidence block
is pasted into the plan.** If M2's corpus bound is now judged to downgrade this, it downgrades r3 H3
and r2 H3 retroactively too.

**Fix.** Increment where the block is assembled, not where a python fence is seen:

```python
            if pending:
                if f.group(1) != "python":
                    problems.append(...)
                files.setdefault(pending, []).append(text)
                py_tagged += 1
                tagged_by_name[pending] = tagged_by_name.get(pending, 0) + 1
                pending = None
```
and delete the `if pending:` half of `:254-256`. ⚠ Then **assert both lines in one case**, on a
non-python fixture — the same requirement r3 accepted for the python one, or this recurs a third
time. Note the label `python fences: N (M assembled…)` can then show `M > N`; that is honest (`M`
counts assembled blocks, `N` counts python fences) but the label deserves a word.

**⚠ MEASURED, not predicted: that fix orphans NO manifest anchor.** I applied it and re-resolved all
41 entries — every anchor still resolves exactly once, including entry 39
(`py_tagged -= tagged_by_name.get(name, 0)`, expect *"the census and the subject sentence cannot
contradict each other"*), which was the one I expected to break. r3's M1 does **not** recur here.

**What would prove me wrong:** a demonstration that a non-python block under a file tag cannot reach
`files`. `:266-270` puts it there unconditionally, and fixture B's per-file line is printed from it.

---

## MEDIUM

### M1 — the fix constructs a precise diagnosis and throws it away: three different refusal causes render one identical sentence on the durable half.

`check()`'s new raise names the cause — `:1389-1392`:

```python
            if not mut_readable:
                raise VerdictContractError(
                    "a mutations declaration did not parse, so `declared` counts the "
                    "entries that survived rather than the ones the plan wrote")
```

and `:1395` catches it bare:

```python
        except VerdictContractError:
            verdict = NotMeasured.from_counts(m_muts, declared, ev_files)
```

`from_counts` derives `reason` from arithmetic alone (`coverage_verdict.py:97-100`), and its shortfall
parenthetical fires only when `entries != declared` — which on this path it never does, because
`declared = len(muts)` counts the entries that *survived*. So the exception message, the only place
the cause is named, is discarded.

**MEASURED** — three causes, one `check()` each, the `NOT MEASURED` line of the rendered block:

| cause | verdict | durable line |
|---|---|---|
| RED control (bash block under a file tag) | `NotMeasured` | `NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.` |
| GREEN control, UNREADABLE declaration | `NotMeasured` | *identical, byte for byte* |
| GREEN control, declaration lost to a file tag | `NotMeasured` | *identical, byte for byte* |

A reader holding the pasted block cannot tell "the suite was already failing" from "your mutations
JSON has a trailing comma". The console `report` distinguishes them; the durable artifact does not —
and this file's own argument, made twice (`:1475-1484` and `:3369-3379`), is that the durable half
must not be the *less* informative of the two.

Medium rather than High: nothing here asserts a falsehood. It withholds, correctly, and says so. The
cost is diagnosis, not truth.

**Fix.** `except VerdictContractError as exc:` and let `NotMeasured` carry the cause — either append
`exc` to `report`, or give `from_counts` an optional `cause` the reason renders. ⚠ Whichever, case it
on **two** causes asserting they render *differently*, or the case passes over a constant.

⚠ **AND THIS FIX ORPHANS A MANIFEST ANCHOR — MEASURED BEFORE THE FIX, NOT AFTER.** Entry 23's anchor
spans four lines *including* `except VerdictContractError:` in `check()`:

```
        controls_green=controls_green)
        except VerdictContractError:
            verdict = NotMeasured.from_counts(m_muts, declared, ev_files)
    return ok, report, verdict
```

Naming the exception rewrites line 2, and the anchor resolves 0 times. I applied it to a copy and
re-resolved all 41 entries:

```
mutate_delivered (:1116) handler named:  orphans NONE
check()          (:1395) handler named:  ORPHANS [23]  expect='a RED control makes check() withhold
                                          trust, whatever the tally says'
```

`--self-test` stays green through it; only a full `--mutate .` sees it. Retarget entry 23 onto
`controls_green = False` or the `Measured(...)` construction in the same edit that names the
exception. This is r3 M1's shape, and the same lesson: **there is no anchor a rewrite of its own
subject cannot break, so the sweep is the instrument.**

**What would prove me wrong:** a rendered block, on a green-control run, that names an unreadable
declaration. All three rows above are the same string.

### M2 — the split's whole justification is the one thing nothing checks: collapse both new messages into ONE identical string and the suite is still 223/223.

`746178f6` split one conjunction into two branches, and the reason given at `:286-292` is explicit:

> *"They ARE two rules — 'a declaration is a list' and 'its elements are entries' — and **each now
> says which one failed**."*

That property has no falsifier. I replaced both `problems.append(...)` bodies with the same string —
behaviour untouched, both branches still taken, both still setting `mut_readable = False` — and ran
the whole suite in the staged tree over the green control:

```
BOTH MESSAGES IDENTICAL -> rc: 0 | 223/223 passed
```

The two manifest entries that pin these branches still go red, and that is the point rather than a
reassurance — they mutate the *predicates* (`if not isinstance(parsed, list)` → `hasattr(…)`;
`elif not all(…)` → `elif False`), so they defend the behaviour and say nothing about the messages:

```
caught   any iterable is accepted as a mutations declaration again (r3 H2b)
caught   a list of non-entries is accepted as a declaration again (r3 H2c)
```

The cases at `:1697-1701` assert `(mut_readable, muts == [], len(problems)) == (False, True, 1)` —
**a count, never a text.** And `grep` finds neither message quoted anywhere outside its own
definition (`:297`, `:304`); the message it replaced, `"LIST of entry objects"`, appears nowhere in
the repo at all, so no case was asserting the old text either.

So: the code was restructured for a stated reason, the restructure is correct, and the stated reason
is unguarded. This project has recorded both halves of that — *a FIX that shipped without its CASE*,
and *assert the PROPERTY, not the mechanism*. It matters here more than usual because the split was
**forced by a tool** (the anchor-dedupe guard), so the diagnostic distinction is the only thing that
makes it a design improvement rather than a concession.

Medium, same bar as M1: nothing false is asserted, and the cost is a plan author's debugging time.

**Fix.** One case per branch asserting the message *distinguishes* them — e.g. `"not a LIST"` in the
`{}` fixture's problems and `"elements are not entry objects"` in the `[1, 2]` fixture's — which
fails if either is deleted, if they are swapped, or if they are merged.

**What would prove me wrong:** any case, anywhere, that reads the text of either problem. The 223/223
above is the whole suite run with both texts destroyed.

---

## The split, attacked directly — the three questions the coordinator asked

Recorded separately because a fix written *during* round 4 is, on this branch, the highest-risk
category there is.

**(1) Does the split change BEHAVIOUR anywhere? No — measured, not read.** I loaded `0a6f6319`'s
`extract()` and `746178f6`'s side by side and ran 19 inputs through both, comparing the observable
triple `(len(muts), mut_readable, len(problems))`:

| body | old | new | | body | old | new |
|---|---|---|---|---|---|---|
| `[]` | `(0, True, 0)` | `(0, True, 0)` | | `null` | `(0, False, 1)` | `(0, False, 1)` |
| `[{"name":"a"}]` | `(1, True, 0)` | `(1, True, 0)` | | `0` | `(0, False, 1)` | `(0, False, 1)` |
| `{}` | `(0, False, 1)` | `(0, False, 1)` | | `true` | `(0, False, 1)` | `(0, False, 1)` |
| `""` | `(0, False, 1)` | `(0, False, 1)` | | `"text"` | `(0, False, 1)` | `(0, False, 1)` |
| `{"a":1,"b":2}` | `(0, False, 1)` | `(0, False, 1)` | | `3.5` | `(0, False, 1)` | `(0, False, 1)` |
| `[1, 2]` | `(0, False, 1)` | `(0, False, 1)` | | `[{"a":1}, 2]` | `(0, False, 1)` | `(0, False, 1)` |
| `["x"]` | `(0, False, 1)` | `(0, False, 1)` | | `[[1],[2]]` | `(0, False, 1)` | `(0, False, 1)` |
| `not json` | `(0, False, 1)` | `(0, False, 1)` | | `[{"name":"a",},]` | `(0, False, 1)` | `(0, False, 1)` |

plus the three non-JSON routes (file-tag clobber, second mutations tag, dangling tag): identical.
**`behaviour differences: NONE`.** The `elif`-inside-`else` restructure preserves `want_mut = False`
on every path — it is still the last statement of the `elif want_mut:` block, outside the `try`.
The only difference is the problem *text*, which is M2's subject.

**No case asserts the old text.** `grep -rn "LIST of entry objects"` over `.py`, `.json` and `.md`
returns **nothing**. Nothing was depending on the sentence that was replaced.

**(2) Is `honest_zero` read anywhere it should not be? No.** Two references in the delivered code
and nothing else: assigned at `:1320`, read at `:1324`, both inside the `if not files:` block that
owns it. It does not leak into the main path (which reads `mut_readable` directly at `:1389`), and it
is not a field on anything. The remaining hits are the two manifest anchors and this review.

**(3) Do the two new anchors quote lines the next plausible fix rewrites? No — and the fragile anchor
is an OLD one.** I applied each fix this review recommends to a copy and re-resolved all 41 entries:

| fix | entries orphaned |
|---|---|
| **H1** — census follows `files` rather than python fences | **0** |
| **M2** — a case per message | 0 (it adds cases; it rewrites no line) |
| **M1** — name the exception so the cause can travel | **entry 23** — an anchor written in an earlier round |

Entries 24 (`if honest_zero`), 37 (`if not isinstance(parsed, list):`), 38 (`elif not all(…)`) and 41
(`honest_zero = not muts and mut_readable`) survive all three. The split made the manifest *more*
robust, not less: it moved two entries off a shared line onto two lines each fix touches
independently.

**(4) One thing the coordinator did not ask, which I checked anyway.** `load_manifests`' dedupe is
**per-manifest**, not global — `seen_names, seen_anchors = set(), set()` is re-initialised inside the
`for man in files:` loop (`:950`). Two different scripts' manifests may therefore share an anchor
string, which is correct (they target different files) and worth knowing before anyone "tightens" it.
Also note the guard `continue`s past a duplicate rather than failing at it, so the entry is silently
dropped from `out` and the *count* check is what actually reddens CI — which is exactly the sequence
the coordinator saw.

---

## LOW

**L1 — a plan's mutations declaration can still be lost silently, but only by writing the tag wrong,
and I do not think that is a defect.** `MUT_TAG` is `^\s*<!--\s*mutations\s*-->\s*$`, so
`<!-- mutations --> (the three below)` matches nothing, the following ```` ```json ```` fence is
ignored entirely, and `extract()` returns `muts == []`, `problems == []`, `mut_readable is True` —
a `Measured(declared=0)` over a plan whose text visibly declares three. **MEASURED.**

I am listing this as the honest answer to the brief's first question and then arguing *against* it:
the parser deliberately ignores near-miss tags, and has a case saying so (`:2582-2585`, *"a mutations
tag quoted in prose does not claim the next json block"*). Chasing near-misses would break that case.
The only thing worth noting is the asymmetry: an **invisible fence** is reported loudly (`:239-244`,
*"skipped silently, which takes the block out of every check here without any account of why"*) and
an invisible **tag** is not. If that asymmetry is deliberate, one sentence in `extract()`'s docstring
retires the question permanently.

**L2 — the `honest_zero` split was made to satisfy the mutation tool, and the commit says so.**
`746178f6` splits one conjunction into a named variable plus a branch, and one validation into two
`elif`s, because `run_mutations` refuses two entries that quote the same anchor (`:963-966`). The
code is better for it, the split is behaviour-preserving (measured — *§ The split*), and the comment
is admirably honest (*"the split was forced by a GUARD rather than chosen"*). Recorded, not as a
defect, but because the precedent generalises: any conjunction a reviewer wants two mutations on will
now be split, and *"one line, one mutation"* is a property of the instrument, not of the code. Worth
one line in `review-method.md` before it is applied a third time without noticing.

⚠ **M2 is the sharper half of this.** Splitting *for the instrument* is defensible when the split buys
something — here, two distinct diagnoses. M2 measures that the thing it buys is the one thing nothing
checks. Fix M2 and this Low stops being interesting.

---

## What I checked and found NOTHING wrong with — stated so round 5 does not re-spend it

* **`mut_readable` is COMPLETE against every route that clears `want_mut`.** I enumerated them
  exhaustively rather than sampling: `want_mut` is set only at `:238` and cleared at `:218`
  (file tag → problem + flag), `:238` (second mutations tag → problem + flag), `:296` (a fence,
  every failure branch of which sets the flag) and `:327-329` (end of document → problem + flag).
  `pending` and `want_mut` are **mutually exclusive by construction** — `FILE_TAG` sets
  `(pending, False)` and `MUT_TAG` sets `(None, True)` — so the `if pending:` arm of the fence branch
  can never consume a mutations block. There is no fifth route. The only `muts == []` with
  `mut_readable is True` is the honest `[]`, plus L1's malformed tag, which is not a declaration the
  parser ever saw.
* **`mut_readable` cannot produce a FALSE refusal.** It is only ever set False alongside a problem the
  reader can see; there is no path that sets it without appending. I looked specifically for the
  over-refusal shape — a plan with one GOOD declaration plus one lost one — and it does refuse
  (`NotMeasured`, `declared=1`, one entry `caught=True`), rendering `NOT RUN f returns 2` over a
  mutation that ran and was caught. **That is deliberate and guarded**: manifest entry 29 pins it
  with expect *"...so every entry renders NOT RUN, whatever its own flag says"*, and it errs
  conservative under a header that says NOT CHECKED. Not a finding.
* **The 16 new cases are NOT vacuous.** I reverted each fix piece individually on the staged tree and
  ran the harness's own `run_mutations` over the green 223/223 control. **11 applicable reverts,
  11 caught, 11 measured, zero survivors:**

  | revert | caught |
  |---|---|
  | file-tag clobber no longer sets the flag | ✅ |
  | second-mutations-tag no longer sets the flag | ✅ |
  | `not isinstance(parsed, list)` branch neutered | ✅ |
  | `elif not all(isinstance(entry, dict) …)` branch neutered | ✅ |
  | `JSONDecodeError` no longer sets the flag | ✅ |
  | end-of-document dangling tag no longer sets the flag | ✅ |
  | `honest_zero` ignores `mut_readable` (early return) | ✅ |
  | main-path `if not mut_readable: raise` deleted | ✅ |
  | census does not follow the drop | ✅ |
  | `evidence()`'s DROPPED clause suppressed | ✅ |
  | `verify_evidence` mode keyed off the RESULT again | ✅ |

  Every one asserts a **behaviour**, not an input, and each `mut_readable` case asserts **both** halves
  (a problem the reader can see AND the flag the verdict rests on), so deleting either alone fails it.
  The presence twins are real twins: `:1652` (a well-formed declaration reports READABLE) would fail
  over a parser stuck at False, and `:1845-1847` (an assembled block counts as assembled with no
  DROPPED clause) would fail over a census hardcoded to zero.
* **The THREE narrators now agree on the compare axis, and I looked for a fourth.** `evidence()`'s
  subject (`:1457-1467`), `verify_evidence`'s `mode` (`:1582-1583`) and `main()`'s mode string
  (`:3407-3410`) are all derived from the *flag*, and `compared` is only ever `None` or a non-empty
  dict, so all three worlds line up. The fourth statement I checked — `not_measured_line`'s `subject`
  — is `""` from `evidence()` and `f"{mode}: "` from `main()`, both consistent. **No disagreement
  found.** This is the first round where that is true, and H1 is not an instance of it.
* **All 20 `extract()` call sites are correct.** Every one unpacks five values or indexes `[0]`; no
  site silently discards `mut_readable`. No caller outside this file unpacks `extract()` —
  `check-selftest-counts.py` imports `count_drift`, not the parser.
* **Anchor health.** 375 edits across 32 manifests, **0 orphaned, 0 ambiguous**. 41 entries, 41 unique
  names, no duplicate anchor tuples. **No anchor quotes a comment line or a bare string literal** — I
  checked all 41 specifically for the diagnostic-prose fragility Codex raised, and the two that quote
  a message (35, 36) quote the `problems.append(` *call*, not free prose.
* **The counts are live, not asserted.** `EXPECTED_MUTATIONS` sums to **370** and is pinned by the
  case at `:3241`; `scripts/check-plan-code.py` declares **41** against 41 entries on disk;
  the docstring's `# 223 cases` matches, and `check-selftest-counts.py` re-derives 29 declared counts
  by *running* each script and reports no drift.
* **`RunContext` has no fail-open left.** `tally` defaults to `{}` and `compare_requested` to `False`,
  but every production construction (`:1326`, `:1399`) passes all three explicitly, and `evidence()`
  still requires `ctx`.

---

## Trajectory — the count reaches four, and the CLASS has shifted, which is the harder call

| round | Highs | all regressions from the previous round's fixes? | defect class |
|---|---|---|---|
| 1 | 3 | — | fail-open **defaults** |
| 2 | 3 | ✅ 3 of 3 | **sentinels with an OR** in their meaning |
| 3 | 4 | 3 of 4 | **one fix, one of two paths**; **two narrators, no shared owner** |
| 4 | **1** | **0 of 1** | **a comment asserting a class the fix closed only one instance of** — and, in M2, **a stated justification with no falsifier** |

`dev-process.md` fires Phase 6 at four non-converging rounds, and this is the fourth. But that file's
own instruction is to **read the trigger off the CAUSE, not the count**, and the cause has changed
character rather than repeated:

* **Round 4 introduced no regression.** The one High predates the branch entirely — measured on
  `master`. Rounds 1–3 were each dominated by defects *created by the previous fix*; this one is not.
  I attacked the in-round fix specifically, at the coordinator's request, and it is
  **behaviour-preserving over all 19 inputs I could construct**. That is the first time on this branch
  a round's own fix has survived being attacked as a subject. M2 is a coverage gap in it, not a defect.
* **The two-narrator problem r3 predicted would recur is GONE.** r3's closing sentence was: *"if round
  4 also produces a self-contradicting artifact, the finding is not the sentence — it is that the
  block has no single producer for 'what was this run about'."* I went looking for exactly that and
  found the three narrators agreeing. H1 is a self-contradicting artifact, but not of that kind: it is
  one *number* with two increment sites, not two *sentences* with two variables.
* **The severity curve is falling and the count with it**: 3 → 3 → 4 → 1 High, with Blocking at zero
  throughout.

So the honest reading is that the count says convene Phase 6 and the cause says the loop is closing.
I record both rather than picking for the coordinator, because the rule is written down and it is
theirs to apply. If it helps: **the single question Phase 6 would be worth convening for** is not
`evidence()` — it is *"what is the corpus?"*. Round 3's M2 measured **0 of 92** plans on disk reaching
plan mode's file path at all, and I did not re-measure it because nothing this round could have moved
it. Four rounds of adversarial review have now been spent on a renderer whose only exerciser is its
own `--self-test`. That is a design question, and it is the one this branch has never asked.

---

## Repo state

```
$ git status --porcelain
(empty)
$ git log --oneline -2
746178f6 CI refused two anchors my own sweep cleared — split the rules that shared a line
0a6f6319 Fold round 3 — the parser returns the fact, and one word gets one owner
```

I edited nothing but this review file. Every experiment ran under the session scratchpad; the harness
tree was built by `stage_tree` so it carried `node_modules/typescript`, and `control_is_green` was
`True` before any verdict was taken under it. Both self-tests re-run after all measurements:
**223/223** and **22/22**, still green. `git diff --stat -- scripts/` is empty.

**Verdict: NOT CONVERGED.** H1 is the one I am confident of: it is measured from the shipped CLI, it
is invisible to all 223 cases in both directions, and its fix orphans nothing. M1 is cheap and makes
the durable half say why it refused — ⚠ and it orphans entry 23, which is called here *before* the
fix. M2 is cheaper still: two substring assertions restore the falsifier the split's own justification
is missing. None of the three is a regression — and after three rounds in which almost every High was,
that is the most useful thing in this report.

**Order I would fix them in:** M2 (two lines, and it closes the round-4 fix's own gap), then H1 with
both census lines asserted on a non-python fixture, then M1 with entry 23 retargeted in the same edit.

# Post-Plan Gate — backlog #91, round 3, CLAUDE half

Subject: **round 2's own fixes** (H1 `compared`-state deletion, H2 third sentence +
`compare_requested`, H3 `mut_unreadable`) plus the **three uncommitted manifest entries**, on branch
`coverage-verdict-union-91`.
Reviewer: Claude adversarial half. Date: 2026-09-08.

**Verdict: NOT CONVERGED** — 0 Blocking, 4 High, 2 Medium, 1 Low.

⚠ **Subject pinned before measuring, and it MOVED — harmlessly, and I verified that rather than
assuming it.** I was briefed at `b3c8403d` with `scripts/check-plan-code.py` and
`scripts/mutations/check-plan-code.json` **modified but uncommitted**; that working-tree delta *was*
the three new manifest entries and the `30 → 33` / `359 → 362` count moves, and it is what every
measurement below ran against. While I was writing, the coordinator committed it as **`ea2566cc`**
("Close r2 M1 — three manifest entries for behaviours only cases guarded").

**The content is identical, checked three ways:** `git diff b3c8403d..HEAD --stat` reports the same
`13 +++++++++++--` / `33 +++++++++++…` as the working-tree diff I measured; the three lines every
finding below quotes are still at `:1214`, `:1329` and `:1427`; and the manifest still holds 33
entries against `EXPECTED_MUTATIONS["scripts/check-plan-code.py"] = 33`. Only the commit boundary
moved, so nothing here is re-derived against a different tree. **HEAD as reviewed: `ea2566cc`.**

⭐ **Three of the four Highs are regressions introduced by round 2's own fixes.** Round 1 → 3 Highs,
all regressions. Round 2 → 3 Highs, all regressions. Round 3 → 4 Highs, 3 of them regressions. That
is the recorded failure mode arriving for the third consecutive round, and `dev-process.md` fires
Phase 6 at **four** non-converging rounds. See *Trajectory* at the end — the defect **class is still
shifting**, which `review-method.md` treats as the healthier shape, but the count is now one round
from the trigger.

---

## What was EXECUTED

Controls first. A `HARNESS_TREE` copy was staged with the harness's own `stage_tree`, so
`node_modules/typescript` and `supabase` came with it — the brief records three red controls today
from a scripts-only copy, and a verdict under one of those is an artefact.

| run | result |
|---|---|
| `check-plan-code.py --self-test` (repo) | **207/207**, rc 0 |
| `coverage_verdict.py --self-test` (repo) | **22/22**, rc 0 |
| `stage_tree(REPO, dest)` | `problems: NONE — tree complete`; every `HARNESS_TREE` entry present |
| `run_suite(dest, 'scripts/check-plan-code.py')` in the staged tree | **207/207**, `control_is_green: True` — **CONTROL GREEN**, used for every mutation below |
| 3 single-entry `run_mutations(dest, [entry], {target})` | all `caught=True measured=True survivors=[]` — table in *Manifest* below |
| static anchor sweep, all 32 manifests | **367 edits, 0 orphaned or ambiguous** |
| `check-selftest-counts.py` | rc 0 — "29 script(s) declare a count, every one verified by running it" |
| `check-docs.py` | rc 0 — "Documentation integrity OK" |
| `check-review-rounds.py` | rc 0 — 162 parsed, 0 silent gaps |
| reachability probes over `check()` / `extract()` / `evidence()` / `verify_evidence()` | 5 scripts, tables below |
| the same probes replayed against **4 revisions** (`master`, `063cedc4`, `74238f5a`, `7e2ad668`) | regression tables below |

**NOT RUN:** `check-plan-code.py --mutate .` — a sweep was in flight and I was asked not to contend
for `SUITE_TIMEOUT`. Every mutation verdict below came from the harness's **own** `run_mutations()`
on the staged copy. I did not re-implement the kill rule; the brief records that a copy of it has
twice given this project wrong answers.

---

## HIGH

### H1 — `mut_unreadable` guards ONE of the two return paths. On the path a plan with code takes, an unparseable mutations declaration is STILL `Measured(declared=0)`.

r2 H3's fix is computed **inside** the `if not files:` block and consulted only by that block's
return — `scripts/check-plan-code.py:1214-1221`:

```python
        mut_unreadable = any(p.startswith("mutations block is not valid JSON")
                             or p == "mutations tag has no JSON block after it"
                             for p in problems)
        return (False, report,
                (Measured(files=ev_files, declared=0, mutations=[], survivors=[],
                          controls_green=True)
                 if not muts and not mut_unreadable
                 else NotMeasured.from_counts([], len(muts), ev_files)),
```

The **other** return, 60 lines later, never sees it — `:1268` and `:1276-1277`:

```python
        declared = len(muts)
        …
            verdict = Measured(files=ev_files, declared=declared, mutations=m_muts,
                               survivors=m_survivors, controls_green=controls_green)
```

`declared = len(muts)` is `0` for an unparseable block exactly as it is for an honest zero, and
`verdicts_are_trustworthy([], 0, True)` is True, so the `Measured` is constructed.

**MEASURED**, calling the delivered `check()` on two fixtures that differ only in whether a code
block is present:

| fixture | verdict | `declared` |
|---|---|---|
| `<!-- mutations -->` + a trailing-comma JSON block, **no** file tag (early return) | `NotMeasured` | 0 |
| a **real `<!-- file: m.py -->` python block** + the same trailing-comma JSON block | **`Measured`** | **0** |
| same, with `<!-- mutations -->` and no JSON block at all | **`Measured`** | **0** |

and the durable evidence block for the second row reads, verbatim:

```
  mutations declared and run: 0, caught 0
```

over a plan whose text visibly declares one. That is r1 H2's own sentence unchanged — *a number the
producer invented rather than one it measured* — and it is r2 H3's own sentence unchanged. The fix
closed the branch that had a case and left the sibling standing: this project's recorded
*instance-not-class* shape, and the second time in this file that a fix has closed one route to a
defect while leaving the reachable one (the `:1170-1173` comment narrates the first).

⚠ **Severity is the coordinator's own standard, applied consistently.** r2 H3 was adjudicated High on
a constructed fixture with `ok=False` and the problem in the report. This fixture is identical on all
three counts and sits on the path any plan *with code* takes. If the corpus fact in **M2** is now
judged to downgrade it, that judgement applies retroactively to r2 H3 as well — and the asymmetry
stands regardless of severity: **the same conflation, in the same function, guarded on one return and
not the other.**

**What would prove me wrong:** a demonstration that `problems` cannot hold a mutations-parse failure
while `files` is non-empty. The second and third fixtures above both do it.

---

### H2 — the two matched strings are NOT the complete set. Three routes reach `muts == []` from a declaration that was never read, producing NEITHER string.

The coordinator flagged the string-matching as a convention and asked for a counter-example. There
are three, all measured.

**(a) `FILE_TAG` silently clears `want_mut`** — `scripts/check-plan-code.py:180-183`:

```python
        if (m := FILE_TAG.search(line)):
            if pending:
                problems.append(f"file tag for {pending!r} was followed by another tag, not a block")
            pending, want_mut = m.group(1), False
```

Note the asymmetry **inside one statement**: the clobber of `pending` is reported, the clobber of
`want_mut` is not. The mirror case is reported too (`:192-194`, a file tag followed by the mutations
tag). Three of the four clobber directions announce themselves; the fourth is silent, so
`if want_mut:` at `:253` never fires and the "no JSON block after it" string is never appended.

**(b) and (c) — valid JSON that is not a list.** `muts.extend(json.loads(text))` at `:229` accepts
any iterable:

| mutations block body | `muts` after `extract()` | problems |
|---|---|---|
| `{}` | `[]` | **0** |
| `""` | `[]` | **0** |
| `{"a":1,"b":2}` | `['a', 'b']` | **0** |
| `null` | — | **unhandled `TypeError`** (see L1) |
| `0` | — | **unhandled `TypeError`** (see L1) |

Rows 1 and 2 give `muts == []` with an empty `problems`, so `mut_unreadable` is `False` and the
early return produces `Measured(declared=0)` — the exact state the fix exists to refuse.

**MEASURED end to end** for route (a), on the early-return path:

```
plan text:  <!-- mutations -->
            <!-- file: m.py -->
extract() problems:  ["file tag for 'm.py' has no code block after it"]
NEITHER matched string present:  True
verdict:  Measured   declared=0
evidence: "  mutations declared and run: 0, caught 0"
```

**Fix.** The coordinator already named the right one and deferred it: have `extract()` **return the
fact** rather than have the caller re-derive it from prose. A fourth return value
(`mut_declaration_readable: bool`, set `False` wherever the tag is seen and no list is parsed from it)
removes all three routes at once and cannot drift the way a string set does. The current form is not
merely "a convention" — it is a convention **already measurably incomplete on the day it shipped**,
which is a different claim from the one carried as residue.

**What would prove me wrong:** an enumeration showing `want_mut` cannot be cleared without a problem,
and that `json.loads` cannot yield an empty non-list iterable. Both tables above refute it.

---

### H3 — the new third sentence CONTRADICTS the tally line four lines above it, in the same durable block, on r2 H2's own fixture.

`evidence()` renders the census from `tally['tagged']` at `:1307-1308` and the new subject sentence at
`:1329`:

```python
        out.append(f"  python fences: {tl['python_fences']} "
                   f"({tl['tagged']} assembled, {tl['illustrative']} illustrative)")
…
        out.append("  subject: --compare was given, but no block was assembled, so nothing")
```

`tally['tagged']` counts a fence that was tagged and parsed; `files` is what survived the `unsafe_tag`
drop at `:241-252`. On the assembled-then-dropped fixture those disagree, and **both statements are
printed**:

```
GENERATED by scripts/check-plan-code.py — do not edit by hand.

  python fences: 1 (1 assembled, 0 illustrative)     <-- ONE assembled

  subject: --compare was given, but no block was assembled, so nothing
           was measured against the files in scripts/.     <-- NONE assembled

  mutations declared and run: 0, caught 0
```

**MEASURED as a REGRESSION**, same fixture, four revisions:

| revision | tally line | subject line | |
|---|---|---|---|
| `master` | `1 (1 assembled, …)` | `the PLAN'S COPY of the code. --compare was not given` | consistent |
| `74238f5a` r1 fold | `1 (1 assembled, …)` | `the plan's blocks, DIFFED against the delivered files:` | consistent |
| `7e2ad668` r2 fold | `1 (1 assembled, …)` | `--compare was given, but no block was assembled` | **⛔ CONTRADICTS** |
| HEAD + worktree | `1 (1 assembled, …)` | `--compare was given, but no block was assembled` | **⛔ CONTRADICTS** |

Master and r1 were each *wrong in one direction and self-consistent*. r2's sentence is the first that
makes the artifact disagree with itself, and it does so **on the very fixture the sentence was written
for** — r2 H2's motivating case. The word `assembled` now carries two meanings inside one block: *"a
python fence the parser tagged"* and *"a file that survived into `files`"*. That is the same
one-noun-two-meanings shape as `{}`, relocated from a value into the prose that replaced it.

**Fix.** Pick one owner for the word. Either the subject sentence says what is actually true of the
run — *"--compare was given, but no block SURVIVED to be compared"* — or the tally line accounts for
the drop (`1 (1 tagged, 1 dropped, 0 illustrative)`). ⚠ Whichever is chosen, **assert both lines of
the rendered block in one case**, or this recurs as r2 H1 did.

**What would prove me wrong:** a reading on which `1 assembled` and `no block was assembled` are both
true of the same run. `tally['tagged']` and `len(files)` are two different numbers here, so they are
not.

---

### H4 — `verify_evidence` still keys its mode string off `ctx.compared`, so ONE run reports "--compare was given" and "(no --compare)" in the same output.

`scripts/check-plan-code.py:1426-1427` was never migrated to `compare_requested`:

```python
    mode = ("--compare " + str(ctx.compared and "<dir>" or "")).strip() if (
        ctx.compared) is not None else "(no --compare)"
```

In the new third world `compared is None` and `compare_requested is True`, so this reads `(no
--compare)` while `evidence()` twelve lines earlier prints `--compare was given`.

**MEASURED**, one `check()` result rendered through both functions:

```
ctx.compared = None | ctx.compare_requested = True

evidence():
  subject: --compare was given, but no block was assembled, so nothing
           was measured against the files in scripts/.

verify_evidence():
  --verify-evidence: the pasted evidence block is STALE. It describes a different
  run than the one that just happened, which was (no --compare).
```

**MEASURED as a REGRESSION**, same fixture across the branch:

| revision | `compared` | `verify_evidence` mode | agrees with the subject sentence? |
|---|---|---|---|
| `master` | n/a | `(no --compare)` | ✅ yes (both say not given) |
| `063cedc4` branch base | `None` | `(no --compare)` | ✅ yes |
| `74238f5a` r1 fold | `{}` | `--compare` | ✅ yes (both say given) |
| `7e2ad668` r2 fold | `None` | `(no --compare)` | **⛔ NO** |
| HEAD + worktree | `None` | `(no --compare)` | **⛔ NO** |

r1's `{}` had *incidentally* corrected this line — r2's own review recorded it as a checked-and-clean
item ("H3's fix corrects that line too; it used to say `(no --compare)`"). Deleting the `{}` state
silently reverted that correction, and nothing failed, because the checked-and-clean note was prose
and not a case.

This is r4 H1 by its own definition. The comment at `:1166-1170` describes the original in exactly
these words: *"a run given `--compare` used to emit an evidence block saying '--compare was not
given' while its own final line said the mode was `compared`. Two lines of one output contradicting
each other, on the DURABLE half."* Same defect, direction flipped, third instance on this branch.

**Fix.** `mode` is a statement about the *invocation*, so it must read the flag, not the result:
`"--compare" if ctx.compare_requested else "(no --compare)"`, with the `<dir>` detail still taken
from `ctx.compared` when there is one. **Then case it** — assert the substring in
`verify_evidence()`'s output on both a requested-but-empty run and a bare run.

**What would prove me wrong:** an existing case reading `verify_evidence()`'s output with
`compare_requested=True` and `compared=None`. `grep -n "verify_evidence" scripts/check-plan-code.py`
shows the suite's `--verify-evidence` cases all run on plans with assembled files, where `compared`
is a non-empty dict.

---

## MEDIUM

### M1 — the new r2-H3 entry is anchored on the line that H1's most plausible fix rewrites. Measured, not predicted.

The coordinator's own note on the `EXPECTED_MUTATIONS` bump says the anchors *"deliberately quote a
rendered message, a predicate assignment and an initialisation — NOT the branch expression under
active revision."* That is **true and it is the wrong axis.** The branch expression
(`if not muts and not mut_unreadable`) is indeed avoided — but the *predicate assignment* it points
at instead is `mut_unreadable = any(…)` at `:1214`, indented 8 spaces because it lives inside
`if not files:`. H1's fix must make that value visible to the second return, and the cheapest way is
to hoist it to function scope — which re-indents it to 4 spaces.

**MEASURED** — a plausible hoist applied to a copy, then the anchors re-resolved:

```
entry-2 anchor present now:                                     1
after a plausible HOIST fix, entry-2 anchor resolves: 0 times -> ORPHANED
after the same fix, entry-3 anchor resolves:          1 times -> survives
```

Third orphaning of this class on this branch, and the first that could have been called **before** the
fix rather than after. `--self-test` will stay green through it; only a full `--mutate .` sees it,
which is r2's M2 unchanged.

Not High: nothing is orphaned today (367 edits, 0 orphaned across all 32 manifests, verified above)
and all three entries work. Medium because the fix H1 demands will orphan one of them, and the
instrument that notices costs a full sweep.

**Cheapest mitigation:** anchor entry 2 on the string literal `"mutations tag has no JSON block after
it"` inside the `any(...)`, which survives re-indentation, rather than on the assignment's first line.

### M2 — the CORPUS: zero of 92 plans on disk exercise plan mode's file path at all.

Stated because it bounds every severity on this branch, including round 2's own, and because this
project's recorded failure is *a measurement is only as good as its corpus*.

**MEASURED** — `extract()` run over every plan in `docs/superpowers/plans/`:

```
CORPUS: 92 plan(s) on disk
plans reaching the MAIN path (files non-empty): 0
plans with a LIVE mutations declaration:        0
```

Since backlog #70 retargeted mutations onto `scripts/mutations/*.json`, **no living plan declares a
mutation or tags a file**. So the `Measured` / `NotMeasured` plan-mode distinction — the thing this
whole branch is about — is currently exercised only by `--self-test` and by constructed fixtures.
The one plan that greps positive for both tag families
(`docs/superpowers/plans/2026-08-29-mutation-manifest-retarget.md`) has them inside prose and heredocs;
`extract()` sees 0 files and 0 mutations in it, which I verified rather than assumed.

This does **not** dissolve H1–H4 — they are defects in the delivered producer, reachable from the
command line, and r2's accepted Highs had identical standing. It does mean the honest framing for the
merge decision is *"the durable artifact would lie if this mode were used"*, not *"the durable artifact
is lying today"*.

---

## LOW

**L1 — a mutations block holding `null` or a bare number crashes with an unhandled `TypeError`.**
`scripts/check-plan-code.py:228-231` catches `json.JSONDecodeError` only, so `muts.extend(None)` and
`muts.extend(0)` propagate:

```
  null    UNHANDLED TypeError: 'NoneType' object is not iterable
  0       UNHANDLED TypeError: 'int' object is not iterable
```

Low, not High, because it fails **loud** — a traceback is not a false `Measured`. It is listed here
because the natural fix is the same one H2 asks for: validate that the parsed value is a list of
objects at the point of parsing, and record the fact.

---

## What I checked and found NOTHING wrong with — stated so round 4 does not re-spend it

* **r2 H1's central claim SURVIVES: no empty `compared` dict is reachable.** I attacked this as
  instructed and could not break it. `compared` has exactly **two** assignment sites —
  `:1175` (`None`) and `:1242` (`compare_delivered(...)`). `compare_delivered` (`:555-580`) writes
  `seen[name]` on every iteration of `sorted(names)` and `names` is `files`, which is non-empty past
  the `:1176` guard — so its return is non-empty whenever it is called at all. All three
  `RunContext(` constructions in `scripts/`, `tests/` and `.claude/` are accounted for
  (`:1222`, `:1280`, and `:2783`'s `RunContext()` fixture, which is `None`/`False` and honest).
  **The coordinator was right to delete the state rather than guard it, and right that the reviewer's
  mutation is now equivalent code.**
* **The invariant case is NOT vacuous.** `a DROPPED block with --compare leaves 'compared' None,
  never an empty dict` (`:1613-1614`) is an absence assertion, but its **presence twin** sits
  immediately below at `:1615-1617` asserting `("given, but no block was assembled" in evidence(...),
  "DIFFED …" in evidence(...)) == (True, False)`. Deleting the `--compare` feature outright would
  satisfy the first and fail the second. This is not the *fixing-a-premise-is-not-covering-the-branch*
  shape.
* **`compare_requested` is honest in both directions.** It cannot be `True` without `compare is not
  None` (both construction sites use that expression verbatim), and `main():3142-3149` sets `cmp_dir`
  only under `--compare`, refusing with `CANNOT RUN` if it is not a directory. No caller can reach a
  `True` without asking, or a `False` after asking.
* **All three new manifest entries go red via the case each names**, over the 207/207 green control:

  | entry | ok | caught | measured | survivors | expect matched |
  |---|---|---|---|---|---|
  | third subject sentence collapses into the DIFFED header (r2 H2) | True | True | True | `[]` | `…it says the one honest thing: given, but nothing was assembled` |
  | an UNREADABLE mutations declaration is an honest zero (r2 H3) | True | True | True | `[]` | `a plan whose mutations block does not PARSE is not an honest zero` |
  | `compared` regains its empty-dict meaning (r2 H1) | True | True | True | `[]` | `a DROPPED block with --compare leaves 'compared' None, never an empty dict` |

  Each `expect` matched **exactly one** red case name, which `run_mutations` enforces at `:1141-1148`;
  each anchor resolved exactly once, which it enforces at `:1052-1065`.
* **`EXPECTED_MUTATIONS` is genuinely enforced, so `33` is not a free-floating number.**
  `:921-930` compares the declared count against the entries actually parsed from
  `scripts/mutations/*.json` and reports drift in both directions, including a manifest with no
  declared count. The `30 → 33` bump is therefore checked against the three entries on disk, not
  asserted.
* **`362` is a live sum, correctly moved.** `sum(EXPECTED_MUTATIONS.values())` is 362 and the case at
  `:3009` pins it; `check-selftest-counts.py` re-derives 29 declared counts by **running** each
  script and reports no drift. The docstring's `# 207 cases` matches `count_drift`.
* **Anchor health across the whole repo**, not just this file: 367 edits in 32 manifests, **0**
  orphaned or ambiguous.
* **`check-docs.py`, `check-review-rounds.py`** — both rc 0.

---

## Trajectory — the count is at three, and the class is still shifting

| round | Highs | all regressions from the previous round's fixes? | defect class |
|---|---|---|---|
| 1 | 3 | — | fail-open **defaults** |
| 2 | 3 | ✅ yes | **sentinels with an OR** in their meaning |
| 3 | 4 | 3 of 4 | **one fix, one of two paths** (H1, H2) and **two statements about one subject with no single owner** (H3, H4) |

`dev-process.md` fires Phase 6 at **four** non-converging rounds. This is round 3, so it does not fire
yet — and `review-method.md`'s own test says to read the trigger off the **cause**, not the count. The
cause has moved each round rather than repeating, which is the healthier of the two shapes it
describes. But note what H3 and H4 have in common and what it suggests: `evidence()` and
`verify_evidence()` each narrate the same run to the same reader, from two different variables, with
no shared derivation. Every round so far has fixed one of those narrators and left the other
disagreeing. **If round 4 also produces a self-contradicting artifact, the finding is not the sentence
— it is that the block has no single producer for "what was this run about", and that is a Phase 6
question, not a patch.**

---

## Repo state

```
$ git status --porcelain
?? docs/reviews/claude/plan-coverage-verdict-union-r3-claude.md
```

Clean but for this review file. The two `M` entries I was briefed with were the coordinator's own
manifest work, present before I started, untouched by me, and committed by them as `ea2566cc` during
the write-up — see the provenance note at the top. `git diff --stat -- scripts/` is **empty**, so I
left no footprint on the subject.

I edited nothing but this review file; every experiment ran in the session scratchpad, and the staged
harness tree was built by the harness's own `stage_tree` so it carried `node_modules/typescript` — I
verified `control_is_green` before trusting any verdict taken under it. Both self-tests re-run after
all measurements: **207/207** and **22/22**, still green.

**Verdict: NOT CONVERGED.** H4 is the one I am most confident of — it is three lines to fix, it is
r4 H1 verbatim, and it is a *silent reversion of a correction round 2 recorded as checked-and-clean*,
which is the strongest available argument that prose notes are not coverage. H1 is the one that will
cost the most if carried, because its fix orphans a manifest anchor (M1) and the sweep is the only
instrument that will say so.

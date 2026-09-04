# Code review r5 — Claude half — the round-4 fold

**Subject:** commit `5fc92b73`, files `scripts/check-plan-code.py` and
`scripts/mutations/check-plan-code.json`.
**Reviewer:** Claude half of the dual adversarial gate. **Date:** 2026-09-04.

**Verdict: NOT CONVERGED** — 1 High, 2 Low.

---

## ⚠ Scope note — HEAD is NOT the commit under review

`git rev-parse HEAD` = `5f1b536d`, two commits past `5fc92b73` (`0ba866b4`, `5f1b536d`).
The two files in scope are nonetheless byte-identical between them:

```
$ git diff --stat 5fc92b73 HEAD -- scripts/check-plan-code.py scripts/mutations/check-plan-code.json
(no output)
```

So every measurement below, taken against the working tree, is a measurement of the
reviewed commit's version of these two files. `git status --porcelain` was empty throughout.

## Controls, established before anything was mutated

| Control | Command | Result |
|---|---|---|
| Suite | `python3 scripts/check-plan-code.py --self-test` | `183/183 passed`, rc 0 |
| Mutation run | `python3 scripts/check-plan-code.py --mutate .` | `OK — delivered scripts mutated: 7 file(s), 176 mutation(s), 0 survivor(s)`, rc 0 |
| Clean temp copy | `mutrunner.py CONTROL` (no edit applied) | `rc=0  183/183 passed` |

The commit message's `VERIFIED AFTER` block reproduces exactly. All 35 declared mutations
for this file are caught via the case each names — the 0-survivor result is real.

**Every mutation below was applied to a `shutil.copytree` of `scripts/` in a
`TemporaryDirectory` with `HOME` redirected into that directory. No repo file was edited.**

---

# FINDINGS

## H1 — HIGH — the new gate coverage defends against DELETING the gate, not against WEAKENING it. Four weakenings survive at 183/183, and each prints a tally the run did not earn

**Where:** `scripts/check-plan-code.py:2459` (`--mutate` printer), `:2506` (plan-mode
printer), `:1030` (`evidence()`); mutations 31, 28, 29 in
`scripts/mutations/check-plan-code.json`.

### What is wrong

Round 4's B1 closed a printer that had *no* mutation and *no* case. The mutation it added is:

```json
{ "name": "the --mutate printer stops gating on trustworthiness (r4 B1)",
  "edits": [[ "        if ev[\"trustworthy\"]:", "        if True:" ]],
  "expect": "--mutate mode refuses to print a tally it did not earn" }
```

That is a *deletion* mutation — it hardcodes the gate open. Its sibling mutations 28 and 29
have the same shape (`→ if True:`, `untrustworthy = False`). Nothing anywhere asserts the
gate's **predicate**; only that some gate exists. A weakening that keeps the `if` and adds a
disjunct is invisible to the whole suite.

Measured — control first, then four candidates, each on its own temp copy:

```
[CONTROL]                                                    rc=0  183/183 passed
[M-A  --mutate printer, harmonised to the plan-mode gate]    rc=0  183/183 passed
[M-C  --mutate printer, 'nothing to say' escape]             rc=0  183/183 passed
[M-D  plan-mode printer, same escape]                        rc=0  183/183 passed
[M-E  evidence(), refusal requires a non-empty entry list]    rc=0  183/183 passed
```

M-A is not a contrived edit. It replaces `:2459`'s gate with `:2506`'s gate **verbatim** —
i.e. it makes the two printers use one predicate. That is precisely the cleanup
`scripts/check-vocabulary-collisions.py` exists to encourage ("one mechanism per concern"),
and this file's own r4 commit message reaches for it repeatedly. A future round doing the
obvious de-duplication reintroduces r4's Blocking, and CI stays green.

### The failure scenario, executed end to end

**(a) M-A, on the BEFORE-control-failure path** (`mutate_delivered:751-752` returns early,
so `ev["declared"]` is still `None` while `ev["files"]` already holds the control runs).
A mini tree whose control suite exits 1:

```
===== PRISTINE (as shipped) =====  exit=1
   |   ✗ CANNOT RUN — control run of scripts/thing.py did not prove the suite works (exit 1) ...
   | NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
   >> declares a tally? False

===== M-A  harmonised gate =====  exit=1
   |   ✗ CANNOT RUN — control run of scripts/thing.py did not prove the suite works (exit 1) ...
   | FAILED — delivered scripts mutated: 1 file(s), 0 mutation(s), 0 survivor(s)
   >> declares a tally? True
```

The second output is the exact sentence the printer's own comment at `:2464-2467` forbids:

> NO tally — and that includes the FILE count. On a control-failure run `ev["files"]` holds
> the CONTROL runs, so "7 file(s)" asserts work that measured nothing about mutations, and
> "0 survivor(s)" beside it is this project's success sentence printed over a run that never
> produced a verdict.

**(b) M-C, on a TOTAL SHORTFALL** (`declared = 2`, both anchors absent, so `run_mutations`
skips both and appends nothing — `len(ev["mutations"]) == 0`):

```
#### --mutate printer, TOTAL SHORTFALL (declared 2, 0 verdicts) ####
  PRISTINE       exit=1  final line: NOT MEASURED — ... (0 of 2 declared mutation(s) produced a verdict)
  M-C weakened   exit=1  final line: FAILED — delivered scripts mutated: 1 file(s), 0 mutation(s), 0 survivor(s)
```

**(c) M-E and M-D, on that same shortfall**, via `evidence()` and the plan-mode predicate:

```
#### evidence() on a TOTAL SHORTFALL (declared 2, 0 entries) ####
  PRISTINE       NOT MEASURED — ... (0 of 2 declared mutation(s) produced a verdict) | mutation entries recorded: 0
  M-E weakened   mutations declared and run: 0, caught 0

#### plan-mode printer gate on that SAME ev ####
   pristine   trustworthy or declared is None -> False  (False = refuses; CORRECT)
   M-D        trustworthy or not mutations    -> True  (True = prints tally; WRONG)
```

`mutations declared and run: 0, caught 0` is a clean tally printed into the **durable**
evidence block over a run in which nothing was measured — r3's B4 and r4's H1, restored.

### Root cause — one case drives one of three refusal paths

`grep -n 'main(\["--mutate"' scripts/check-plan-code.py` returns **exactly one** hit, line
2225. That single case drives the AFTER-control path (counts complete, every entry
measured). The `--mutate` printer has three ways to reach its refusal branch, and the other
two have no case at all:

| Path | `declared` | `ev["mutations"]` | Driven by a case? |
|---|---|---|---|
| after-control failure (`:771-780`) | complete | complete | ✅ `:2229`, `:2233` |
| before-control failure / manifest problems / drift (`:690`, `:731`, `:751`) | `None` | `[]` | ❌ none |
| total shortfall — every mutation skipped | > 0 | `[]` | ❌ none |

This is r4's own finding one level in. r4 said "there are TWO printers and r3 covered one".
r5 says: there are THREE refusal paths through the printer r4 fixed, and r4 covered one.

### What would close it

Assert the **property**, not the mechanism: drive `main(["--mutate", …])` on (i) a red
before-control and (ii) a total shortfall, asserting no `file(s)`/`survivor(s)` tally in
either; and add mutations that *weaken* rather than delete each of the three gates. Note
that M-A also argues the two printers should share one predicate — but only once the
shortfall path is covered, or unifying them is itself the regression.

---

## L1 — LOW — `control_is_green` is a substring test, and its docstring claims more than it delivers

**Where:** `scripts/check-plan-code.py:432`

```python
    return rc == 0 and "passed" in out
```

Docstring (`:415`): *"Did this control run actually PROVE the suite works?"*

Measured:

```
  control_is_green(rc=0, '183/183 passed'            ) = True   # real green
  control_is_green(rc=0, ''                          ) = False  # silent, no entrypoint (the r4 M1 case)
  control_is_green(rc=0, '0/0 passed'                ) = True   # a suite that ran ZERO cases
  control_is_green(rc=0, 'skipped: 3 passed earlier' ) = True   # the word in unrelated prose
```

`grep -n '0/0 passed\|ran ZERO\|zero cases' scripts/check-plan-code.py` → no hits; no case
asserts this shape. r4's M1 correctly observed that rc alone cannot separate "green" from
"never ran"; `"passed" in out` still cannot separate "green" from "ran nothing".

**Why LOW and not higher:** the consequence is fail-closed. A suite that detects nothing
lets every mutation survive, so the run reports survivors and exits 1 — loud, not silent. I
found no route from this to a false *catch*. The defect is the overclaiming docstring plus
an unasserted boundary, not a live false green.

---

## L2 — LOW — `EXPECTED_MUTATIONS` pins cardinality and exact duplication, not the SET of guarded sites

**Where:** `scripts/check-plan-code.py:521` (`EXPECTED_MUTATIONS`), `:696-705` (drift),
`load_manifests:636-655` (identity).

The identity check catches a duplicate `name` and a repeated `edits` anchor **tuple**:

```python
            if nm in seen_names:
                ...
            if anchors and anchors in seen_anchors:
```

Both compare against *other entries in the same manifest*. Neither pins which **lines** are
guarded. Deleting entry 31 (the only mutation on `:2459`) and adding any other distinct,
valid entry keeps the count at 35, keeps `sum(EXPECTED_MUTATIONS.values()) == 176` green,
and silently removes the only coverage of the `--mutate` printer's gate. H1 shows each of
the three gates is held by exactly one mutation, so the blast radius is one entry wide.

**⚠ UNVERIFIED — I did not construct a working swap.** This is reasoned from the quoted
code above, not executed; a full `--mutate .` per candidate swap was more budget than a Low
warrants. Treat the mechanism as read, not measured. It is largely subsumed by H1's
recommendation (assert the property, so a site's coverage does not rest on one anchor).

---

# CHECKED AND FOUND CLEAN

So the next round knows what was covered.

1. **Question 4 — every consumer of the trustworthiness verdict, enumerated BY GREP, not
   from the diff.** `grep -n 'ev\["trustworthy"\]\|ev.get("trustworthy")\|not_measured_line'`
   plus a repo-wide `grep -rn trustworthy --include=*.py --include=*.yml --include=*.sh
   --include=*.ts`. **There are exactly THREE consumers, and there is no eighth consumer.**

   | # | Consumer | Site | Mutation | Case | Falsifier real? |
   |---|---|---|---|---|---|
   | 1 | `evidence()` | `:1030`, `:1034`, `:1049` | 29, 33, 34 | `:2298-2308` | ✅ deletion only (H1) |
   | 2 | plan-mode printer | `:2506` | 28 | `:1309` | ✅ deletion only (H1) |
   | 3 | `--mutate` printer | `:2459` | 31 | `:2229`, `:2233` | ✅ deletion only (H1) |

   Producers (`:785`, `:985`) are covered by mutations 23-27. **No consumer outside this
   file**: the only external importer is `scripts/check-selftest-counts.py`, which imports
   `count_drift` and `child_env` and never reads the verdict. The r4 premise re-verified:
   `grep -n check-plan-code .github/workflows/ci.yml` returns four lines, of which the only
   invocations are `:299 --mutate .` and `:305 --self-test`. **CI never runs plan mode.**

   The prediction that round 5 would find an eighth consumer is **refuted**. The count is
   right; the *depth* is what is wrong (H1).

2. **Question 2 — anchor brittleness. Orphaning fails LOUD, so this is not the silent-drift
   class.** Several new anchors are reformat-fragile (mutation 33 anchors
   `        verdict = ("NOT RUN " if untrustworthy\n`, including the line break; 34 anchors a
   full f-string). But an orphaned anchor takes `run_mutations:826-831`, which sets
   `ok = False` and appends nothing, so the cardinality clause fires. **Executed** — a
   manifest whose two anchors are both absent:
   `exit=1`, `NOT MEASURED — … (0 of 2 declared mutation(s) produced a verdict)`,
   `declared=2 entries=0 trustworthy=False`. A refactor that moves this text turns
   `--mutate .` red in CI. Clean.

3. **No mutation is anchored on test code.** All 35 anchors resolve to exactly one site;
   `_self_test` spans lines 1141-2416; every anchor lands at lines 319-2506 **outside** that
   range (checked programmatically per entry). No entry is vacuous by pointing at its own
   oracle.

4. **Question 5 — the new r4 H1 cases are not vacuous.**
   `case("...so every entry renders NOT RUN, whatever its own flag says",
   evidence(_ev_ac).count("NOT RUN ") >= len(_ev_ac["mutations"]), True)` uses `>=`, which
   would be inflated if the header contributed an occurrence. It does not:
   `not_measured_line(...)` returns `'NOT MEASURED — … Treat this as NOT CHECKED.'` and
   `'NOT RUN' in not_measured_line(ev)` is `False`. Rendered output shows `count == 2` for 2
   entries. Both r4 H1 mutations (33, 34) are caught in the baseline run.

5. **Question 3 — `EXPECTED_MUTATIONS` arithmetic** (beyond L2). The suite clobbers the
   global at `:2121`, `:2141`, `:2152`, `:2325`; the restore at `:2334` is inside a
   `finally` (`:2333`) with `_saved = dict(...)` taken at `:2119`, and `:2335-2342` asserts
   the restored key set names all seven manifests. `:2408` pins the sum at 176. A no-op or
   comment-only edit leaves the suite green → SURVIVED → red. Cannot be made vacuous by
   arithmetic alone.

6. **r4's L1 count is correct.** `run_mutations` has exactly four non-appending skip sites —
   unknown target (`:805-808`), ambiguous anchor (`:818-825`), anchor not found
   (`:826-831`), empty `expect` (`:885-891`) — the middle two sharing one `continue` via
   `src = None`. "FOUR places" is right in both the docstring (`:392-397`) and the inline
   comment (`:683-687`).

7. **r4's M1 fix is real.** Mutation 32 (`return rc == 0 and "passed" in out` →
   `return rc == 0`) is caught in the baseline, and both callers (`:746`, `:771`, `:962`)
   now route through the one predicate.

8. **The `evidence()` TypeError I hit is not a defect.** `evidence()` cannot render a
   `mutate_delivered` ev (`files[...]["blocks"]` is `None`, and `:1000` formats it as
   `{f['blocks']:>2}`). `--mutate` mode never calls `evidence()` — `main:2497` gates it on
   `a.evidence`, which `:2443-2450` refuses to combine with `--mutate`. Unreachable.

---

## What I could not do

Nothing in scope was unreachable. No check reported CANNOT RUN. The one item explicitly
labelled unverified is **L2**, above.

---

## VERDICT: NOT CONVERGED

1 High, 2 Low. The High is the eighth instance of this branch's standing pattern — the
defect sits inside the previous round's fix — but with a changed character worth recording:
**r3 and r4 found gates with no falsifier at all; r5 finds falsifiers that exist and are
satisfied by a strictly weaker property than the one the code needs.** The failure has moved
from *absent coverage* to *shallow coverage*. That is progress, and it is also the reason a
ninth round should be scoped to the shape of the assertions rather than to their presence.

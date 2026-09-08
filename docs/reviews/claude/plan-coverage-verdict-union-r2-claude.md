# Post-Plan Gate — backlog #91, round 2, CLAUDE half

Subject: **round 1's own fixes** (H1, H2, H3) on branch `coverage-verdict-union-91`.
Reviewer: Claude adversarial half. Date: 2026-09-08.

⚠ **THE SUBJECT MOVED WHILE I WAS MEASURING.** I was briefed at `74238f5a` and the coordinator
committed `8afbf40f` mid-review. Everything below is re-derived against **`8afbf40f`** unless it
says otherwise; the one finding that `8afbf40f` closed is recorded as corroboration, not as a
finding. Re-baselining is not free and this is the second thing in this branch's history that a
moving tree has cost — see *Corroboration* below.

**Verdict: NOT CONVERGED** — 0 Blocking, 3 High, 2 Medium, 2 Low.

---

## What was EXECUTED

Controls first, in a throwaway `HARNESS_TREE` (`scripts` + `supabase` + `docs` +
`node_modules/typescript`). I reproduced the red-control hazard the brief warned about before
trusting anything: a scripts-only copy fails **3 of 201** cases with `CANNOT RUN — supabase is
missing`, so every verdict under it would be an artefact.

| run | result |
|---|---|
| `coverage_verdict.py --self-test` (repo) | **22/22**, rc 0 |
| `check-plan-code.py --self-test` (repo) | **201/201**, rc 0 |
| same, in the staged harness tree | **201/201** — CONTROL GREEN, used for every mutation below |
| `check-selftest-counts.py` (real) | rc 0 — "29 script(s) declare a count, every one verified by running it" |
| `check-docs.py` (real) | rc 0 |
| **F7 re-derived by hand** | see below — **byte-identical**, twice |
| anchor sweep over all 32 manifests at `8afbf40f` | **0 orphaned or ambiguous anchors** |
| 8 single-mutation runs over the green control | table in *Vacuity* below |

**NOT RUN:** `check-plan-code.py --mutate .` — the coordinator's sweep was in flight and I was asked
not to contend for `SUITE_TIMEOUT`. Every mutation below was run one at a time through the harness's
own `run_mutations()` on a staged copy, which is the same mechanism.

### F7 — re-derived, not taken on trust

```
python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-29-mutation-manifest-retarget.md
python3 scripts/check-plan-code.py … --evidence
diff /tmp/v91/base/plan.txt      <fresh>   ->  IDENTICAL
diff /tmp/v91/base/evidence.txt  <fresh>   ->  IDENTICAL
```

**T2a survives H2.** The honest zero is still `Measured(declared=0)` and F7 is byte-identical. I also
confirmed the mapping directly: `check()` on a plan with no code and no mutations returns
`Measured, declared=0`.

---

## HIGH

### H1 — the H3 fix has NO GUARD ON THE SENTENCE IT EXISTS TO FIX. A one-token edit restores the exact defect and the suite stays 201/201.

Round 1 stated the falsifier the fix owed, in words:

> with it, the invocation above must print `subject: the plan's blocks, DIFFED against the delivered
> files:` and the same invocation *without* `--compare` must still print the "not given" sentence.
> **Both must be asserted by a case, or the fix is a change with no guard.**

The fix asserts `ctx.compared`, not the printed sentence — `scripts/check-plan-code.py:1530-1534`:

```python
        _h3_cmp = check(pl, pathlib.Path(td))[3].compared
        _h3_bare = check(pl)[3].compared
        case("--compare on the early-return path does NOT report 'compare was not given'",
             _h3_cmp is None, False)
        case("...and without --compare it still reports exactly that", _h3_bare, None)
```

`compared` is only an *input* to the sentence. The sentence itself is chosen at
`scripts/check-plan-code.py:1288-1291`:

```python
    cmp = ctx.compared
    if cmp is None:
        out.append("  subject: the PLAN'S COPY of the code. --compare was not given, so")
```

**MEASURED** — one anchor, `if cmp is None:` → `if not cmp:`, applied to a control proved green at
201/201:

```
check-plan-code.py --self-test   rc=0   201/201 passed
coverage_verdict.py --self-test  rc=0   22/22  passed
```

and the defect is back end-to-end, on the durable half. Same invocation, control vs mutant:

```
CONTROL:  subject: the plan's blocks, DIFFED against the delivered files:
MUTANT:   subject: the PLAN'S COPY of the code. --compare was not given, so
                   nothing here was measured against the files in scripts/.
          …
          FAILED — compared: 0 file(s), 0 mutation(s), 0 survivor(s)
```

Two lines of one output contradicting each other — r4 H1, verbatim, reachable from the command line,
and **no case anywhere fails**. Note the shape: T5 closed the default-argument route, r1 H3 closed
the `compared`-value route, and the *renderer* route was never covered by either. Third instance of
one class.

**Fix.** Assert the rendered block, not the context value: call `evidence(v, ctx)` on both
invocations and assert the substring `DIFFED against the delivered files` is present in one and
`--compare was not given` in the other. That is one line longer than what is there and it is what
round 1 asked for.

**What would prove me wrong:** an existing case that reads `evidence()`'s output on the early-return
path with a non-None empty `compared`. There is none — the mutation above is green.

---

### H2 — `compared = {}` asserts a diff that NEVER RAN. On a reachable fixture it converts master's conservative wrong sentence into a permissive one.

`scripts/check-plan-code.py:1161` sets `compared = {}` when `--compare` was given, **before** the
`not files` return. `compare_delivered()` is never called on that path — nothing is diffed. But
`evidence()` renders a non-None `cmp` as the DIFFED header (`:1292-1293`), so the durable block
states that a comparison happened.

The in-code comment says an empty dict means *"compared, and nothing matched"*. On the plain honest
zero that is defensible: zero blocks, zero rows, vacuously true. **It is not defensible on the
fixture where blocks WERE assembled and then dropped.**

**MEASURED — a plan with one `<!-- file: ../evil.py -->` block (assembled, then dropped by the
`unsafe_tag` branch), run with `--compare` and `--evidence`:**

```
BRANCH (8afbf40f)                          MASTER
  python fences: 1 (1 assembled, 0 …)        python fences: 1 (1 assembled, 0 …)
  subject: the plan's blocks, DIFFED         subject: the PLAN'S COPY of the code.
           against the delivered files:               --compare was not given, so
                                                      nothing here was measured against
                                                      the files in scripts/.
```

Master's sentence is **wrong and conservative** — it tells the reader nothing was checked against the
real files. The branch's is **wrong and permissive** — one block assembled, "DIFFED against the
delivered files", zero differences listed, which reads as a clean compare. This project's own rule is
that a permissive false claim on the durable artifact is the worse of the two.

**Not a regression** — master is wrong here too, in the other direction. It is High because the fix
was *specifically* for the evidence misstating its own subject, and on this fixture it still does.

**Fix.** `{}` is the wrong sentinel because it is trying to mean two things. Give the renderer a third
branch: `--compare` was given, and there was nothing to compare —

```
  subject: --compare was given, but no block was assembled, so nothing was
           measured against the files in scripts/.
```

That is the one honest sentence, and unlike `{}` it cannot be confused with a clean diff.
⚠ Whatever is chosen, **assert the rendered sentence** (H1), not the value behind it.

**What would prove me wrong:** a demonstration that `files` cannot be empty while
`tally['tagged'] > 0`. The fixture above does exactly that, so it can.

---

### H3 — `not muts` conflates "declared NONE" with "the declaration could not be READ". Two reachable plans still get `Measured(declared=0)` over a visible `<!-- mutations -->` block.

`scripts/check-plan-code.py:1188-1193` branches on `not muts`. But `extract()` returns `muts == []`
for **three** different worlds, and only one of them is an honest zero
(`scripts/check-plan-code.py:228-231` and `:253-254`):

```python
                try:
                    muts.extend(json.loads(text))
                except json.JSONDecodeError as exc:
                    problems.append(f"mutations block is not valid JSON: {exc}")
    …
    if want_mut:
        problems.append("mutations tag has no JSON block after it")
```

**MEASURED — the verdict object each fixture produces:**

```
badjson.md   (a mutations block with a trailing comma)  ->  Measured  declared=0
notag.md     (a mutations tag with no JSON block)       ->  Measured  declared=0
nofiles.md   (genuinely no mutations at all)            ->  Measured  declared=0
```

Indistinguishable. And the durable evidence block for `badjson.md` says:

```
  mutations declared and run: 0, caught 0
```

over a plan whose text visibly declares two. That is r1 H2's own sentence, unchanged: *"clause 2
passes vacuously, because the number it compares against is one the producer invented rather than one
it measured."* The fix narrowed the hole from "a parseable mutations block" to "an unparseable one" —
and the unparseable case is the one a typo produces, i.e. the likelier one in practice.

This is also the exact shape `scripts/check-sentinel-meanings.py` exists to catch: one value, a
meaning with a conjunction in it. `muts == []` now means *"none were declared **OR** the declaration
could not be read."*

**PRE-EXISTING in output** — master prints byte-identical words (measured against
`git show master:scripts/check-plan-code.py`). High for r1 H2's own stated reason: master carried
`declared: None`, which honestly means "never attempted"; a `Measured` **positively asserts zero were
declared**. The union makes this lie explicit and typed, which is the argument for closing it, not
for stopping halfway.

**Fix.** Branch on whether the mutations *declaration* was readable, not on the count alone. The
cheapest honest form, which avoids reintroducing `declared is None` into plan mode (`main()`'s
printer gates depend on that being unreachable):

```python
        mut_unreadable = any(p.startswith("mutations block is not valid JSON")
                             or p == "mutations tag has no JSON block after it"
                             for p in problems)
        return (False, report,
                (Measured(files=ev_files, declared=0, mutations=[], survivors=[],
                          controls_green=True)
                 if not muts and not mut_unreadable
                 else NotMeasured.from_counts([], len(muts), ev_files)),
                RunContext(tally=tally, compared=compared))
```

⚠ Matching on problem strings is itself a convention. The stronger form is for `extract()` to return
the fact rather than have the caller re-derive it from prose — but that is a wider change, and the
above is falsifiable today. **Whichever is chosen it needs a case over `badjson.md` AND the honest
zero, or it repeats H1.**

**What would prove me wrong:** a demonstration that `problems` cannot contain a mutations-parse
failure while `muts == []`. Both fixtures above do it.

---

## Vacuity — I checked the coordinator's check. The three new cases are NOT vacuous.

Eight single-mutation runs, each over the 201/201 control, applied to a staged copy:

| mutation | suite | red via |
|---|---|---|
| revert H2 — always `Measured(declared=0)` | 199/201 | `…is NOT a measured zero` **and** `…reports how many were declared` |
| invert H2 — always `NotMeasured` | 198/201 | the **presence twin** + 2 pre-existing honest-zero cases |
| `from_counts([], len(muts))` → `from_counts([], 0)` | 200/201 | `…reports how many were declared` |
| revert H3 — `compared = None` | 200/201 | `--compare … does NOT report 'compare was not given'` |
| H3 always-`{}` | 199/201 | the **presence twin** + `without --compare the evidence says the subject was NOT the real files` |
| revert H1 — restore `= True` | cv **21/22** | `H1 clause 1 has no default…` (and `check-plan-code` stays **green**, confirming the case is the sole guard) |
| **delete the subject** — `check()`'s whole `not files` early return | 199/201 | two *pre-existing* cases, `a plan with NO tagged blocks fails rather than reporting 0 files` + `…says nothing was assembled` |
| **`evidence()`: `if cmp is None` → `if not cmp`** | **201/201 GREEN** | ⛔ **nothing** — this is H1 |

**Is a third presence twin owed? No.** The two the coordinator added each fired on the inverted
mutation, and deleting the subject outright is caught by pre-existing cases. H1's own presence twin
already exists at `coverage_verdict.py:216` (`a complete run constructs`), so no twin is missing
there either. The gap is not a missing twin — it is a case asserting the **wrong subject** (H1).

---

## MEDIUM

### M1 — the fold added THREE new behaviours and ZERO manifest entries. The only one with mutation coverage has it by luck.

`git diff 1309fc13..8afbf40f --stat` touches `check-plan-code.py`, `coverage_verdict.py` and
`scripts/mutations/check-plan-code.json` — and the manifest change is a **retarget**, not an
addition (30 → 30 entries; I diffed the parsed JSON, exactly one entry changed, order identical).

`EXPECTED_MUTATIONS`' own history states the norm this misses, in the file itself:

> ⟳ 70 -> 73, comprehensibility slice A (backlog #83). **THREE entries, one per new behaviour.**

The branch followed that norm for its original code (5 new `coverage_verdict` entries). The fold did
not. Consequences, measured:

* **H3's fix (`compared = {} if …`)** has a case but no entry. Nothing prevents the next refactor
  from orphaning it — and unlike the honest-zero entry, there would be no anchor to report NOT FOUND,
  so the loss would be silent rather than loud.
* **H1's fix** has a case but no entry. Its coverage is real today (measured: reverting it goes
  21/22), because the only way to defeat that case is to delete the case.
* **H2's fix** has manifest coverage in ONE direction only — `if not muts` → `if False`, retargeted
  in `8afbf40f`. The direction the fix actually corrected (always-`Measured`) has no entry.

Not High because `--self-test` does cover all three today, and I proved it. Medium because the
branch's own commit message one commit earlier says *"anchors bind by TEXT, so improving the code
removed the coverage guarding it"* — and the fold then shipped three behaviours with nothing pinning
them.

### M2 — the orphaned-anchor class has NO cheap detector. The only instrument that sees it is a full `--mutate .`.

`8afbf40f`'s own account is that `--self-test` stayed green at 201/201 and `--mutate .` was what
caught it. That is correct and it is also the whole problem: `--mutate .` is minutes of CI, so the
signal arrives long after the edit, and this class has now fired **three times**
(2026-09-01 twice, today once). `load_manifests` (`scripts/check-plan-code.py:805-861`) already
preflights duplicate names, duplicate anchors and file/name agreement — it does **not** check that an
anchor resolves. The apply-time check at `:1045-1048` is the only one.

**MEASURED** — a 12-line static sweep reads every entry of all 32 manifests and reports
`orphaned/ambiguous anchors: 0` at `8afbf40f` in **under a second**; at `74238f5a` the same sweep
named the orphan. It is the identical predicate `run_mutations` applies (`count != 1`), just hoisted
out of the expensive loop. Adding it to `load_manifests`' preflight would make the class fail in
`--self-test` time rather than sweep time.

Not High: nothing is currently orphaned, and the expensive detector does work.

---

## The two Mediums carried from round 1 — my verdicts

**r1 M1 (`NotMeasured`'s integrity is a convention, `Measured`'s is a constructor) — does NOT block
merge, but it is now the same open class as H3.**
I enumerated the population: **one** direct `NotMeasured(...)` construction exists anywhere in
`scripts/`, `tests/` or `.claude/` — `coverage_verdict.py:262`, the suite's own fixture — against
**16** `from_counts` sites. The convention is holding, and the H2 fix added a seventeenth. It does not
block because no production site can reach the contradictory object. It should not be carried
silently either: `not_measured_line(v)` prints `v.reason` straight onto the durable block, so a
producer that hand-set `reason` would put false arithmetic on the artifact — which is H3's class
exactly. Fix shape **(b)** from round 1 (delete the field, make `reason` a `@property`) is the right
one and is cheap: it breaks exactly the one fixture above.

**r1 M2 (`Measured` is `frozen=True` but stores its lists by reference) — does NOT block merge.**
I checked every construction site rather than reasoning about it. `check-plan-code.py:1001`, `:1190`,
`:1246`, `:1672`: each constructs immediately before a `return` and nothing touches `m_muts`,
`m_survivors` or `ev_files` afterwards, so the aliasing is unreachable from any live path. It stays a
real hole in the type and a good follow-up (`object.__setattr__` copies, or take tuples), but it is
strictly weaker than H1–H3 and blocking on it would be inflation.

---

## LOW

**L1 — the H1 case catches a bare `TypeError` from any cause.** `coverage_verdict.py:252-259` asserts
"constructing without `controls_green` raises". A future rename of any other field would also raise
`TypeError` and the case would pass for the wrong reason. The sibling `raises()` helper deliberately
narrows to `VerdictContractError` for exactly this reason, and its docstring cites this project's
recorded "negative test that caught any error and passed on a typo". Asserting on
`"controls_green" in str(exc)` closes it.

**L2 — round 1's L1 is unfixed, and H1's fix has changed what it says.** `check-plan-code.py:879-881`
still asserts in the present tense that `trustworthy` *"defaults FALSE, so every path that does not
explicitly earn it — including ones added later — is untrustworthy by construction"*, corrected only
by the ⟳ note *below* it at `:894-898`, and `:1143-1144` still says `check()` gets "the same
default-deny `trustworthy`". There is no `trustworthy`. **But the r1 verdict on this should be
downgraded, not repeated:** r1 called it active misinformation *because* H1 had removed the
default-deny property. H1 is fixed, so the property is true again — enforced by a required
constructor argument instead of a flag. What is stale is the mechanism, not the claim.

---

## What I checked and found NOTHING wrong with — stated so round 3 does not re-spend it

* **F7 / T2a.** Byte-identical, twice, both `--evidence` and bare. The honest-zero mapping survives
  H2 intact.
* **The H2 branch direction.** I looked for a state where `muts` is non-empty and the honest zero is
  still truthful: there is none. Mutations declared with nothing assembled is a refusal in every case
  I could build (empty `files`, `unsafe_tag`-dropped `files`, mutations naming an absent file). The
  `muts != []` half of the branch is correct; only the `muts == []` half is overloaded (H3).
* **The new `NotMeasured` early-return path end to end.** Prints
  `NOT MEASURED — compared: … (0 of 2 declared mutation(s) produced a verdict). Treat this as NOT
  CHECKED.` plus `mutation entries recorded: 0` and **no `caught` figure**, rc 1. Correct.
* **`declared is None` is still unreachable in plan mode.** Both early-return branches and the normal
  return pass a non-None `declared`, so `main()`'s printer gates are unaffected by H2.
* **`verify_evidence`'s mode string under `compared == {}`.** `("--compare " + str({} and "<dir>" or
  "")).strip()` → `"--compare"`. H3's fix corrects that line too; it used to say `(no --compare)`.
* **Clause ordering in `Measured.__post_init__`.** Unchanged by the fold; clause 1 still raises before
  2 and 3, so each mutation's `expect` still names a stable case.
* **`8afbf40f`'s manifest rewrite.** 334 lines out, 334 in looks alarming; it is a reformat. Parsed
  JSON diff: 30 → 30 entries, no names added or removed, order identical, exactly one `edits` pair
  changed. The retargeted entry runs `caught=True, measured=True` and its `expect` matches exactly one
  of the three red case names.

---

## Corroboration — I found `8afbf40f`'s defect independently, before I knew the commit existed

At `74238f5a` my anchor sweep reported the H2 fix had orphaned
`the plan-mode HONEST ZERO becomes a refusal (r3 B2 successor)`, and `run_mutations` on that single
entry returned `anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless`,
`ok=False`. `.github/workflows/ci.yml:301` runs `--mutate .`, so the branch was CI-red at that commit.
The coordinator's sweep found the same thing and fixed it in `8afbf40f` while I was measuring.

Two things worth keeping from that:

1. **The mechanism worked, and it worked because of the cardinality clause this change introduces.**
   358 verdicts for 359 declared means no `Measured` can exist, so the run printed NOT MEASURED
   rather than a clean-looking tally. That is the change defending itself against its own author.
2. **It orphaned the mutation guarding T2a specifically** — the honest zero, the property I was asked
   to attack hardest. For the window between `74238f5a` and `8afbf40f` that property had a case and
   no manifest entry. M1 says the fold left H1's and H3's fixes in exactly that state, and nothing
   will announce it for them.

---

## Repo state

```
$ git status --porcelain
?? docs/reviews/claude/plan-coverage-verdict-union-r2-claude.md
```

Nothing else in the repo was edited. Every experiment ran under the session scratchpad; the harness
tree carried `supabase`, `docs` and `node_modules/typescript`, and I verified the red control a
scripts-only copy produces before trusting any verdict taken under it.

**Verdict: NOT CONVERGED.** H1 is the one I am most confident of and it is cheap: the H3 fix is a
change with no guard, measured, with the mutation named. H2 and H3 are both "the fix went halfway" —
neither is a regression, both are the class the fix claimed to close, both on the durable artifact.
M1 and M2 are about the coverage of the fixes rather than the fixes themselves, and M1 is the one
that will cost a future round if it is carried.

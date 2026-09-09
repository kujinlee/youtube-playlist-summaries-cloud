# Post-Plan Gate — backlog #91, round 1, CLAUDE half

Subject: branch `coverage-verdict-union-91` (3 commits on `master` @ `36aa30fe`).
Reviewer: Claude adversarial half. Date: 2026-09-08.

**Verdict: NOT CONVERGED** — 0 Blocking, 3 High, 2 Medium, 4 Low.

---

## What was EXECUTED (not read)

Every claim below that says "measured" was run. Controls first, in throwaway trees.

| run | result |
|---|---|
| `python3 scripts/coverage_verdict.py --self-test` | **21/21**, rc 0 |
| `python3 scripts/check-plan-code.py --self-test` | **196/196**, rc 0 (10.3s) |
| `begin-plan.py --self-test` | 50/50 · `check-selftest-counts` 18/18 · `check-ratchet-contract` 22/22 · `check-vocabulary-collisions` 10/10 · `check-guard-coverage` 16/16 · `check-docs` 13/13 · `check-anchors` 15/15 |
| `check-selftest-counts.py` (real) | rc 0 — "29 script(s) declare a count, every one verified by running it" |
| `check-docs.py` (real) | rc 0 · `check-ratchet-contract.py` (real) rc 0, 28 guards |
| manifest arithmetic | 32 manifests, **359** entries; `EXPECTED_MUTATIONS` sum **359**, 32 rows. Match. |
| **the 5 new `coverage_verdict` mutations**, one at a time via `run_mutations(d,[m],{target})` on a staged copy | **CONTROL GREEN (21/21)**, then **5/5 KILLED via the case each names** |
| **the 3 new + 4 retargeted `check-plan-code` mutations**, same method | **CONTROL GREEN (196/196)**, then **7/7 KILLED via the case each names** |
| F7 baseline reproduced (`2026-08-29-mutation-manifest-retarget.md`) | reaches the `not files` early return, 12 complaints, `0 file(s), 0 mutation(s), 0 survivor(s)` |
| `extract()` over all 93 plans in `docs/superpowers/plans/` | no live plan reaches the H2 scenario today |

**NOT RUN — needs the full sweep:** `check-plan-code.py --mutate .`. The coordinator had one in
flight and asked me not to contend for `SUITE_TIMEOUT`. Nothing below rests on it: the per-mutation
runs above are the same mechanism, one entry at a time, each over a proven-green control.

---

## Did the spec's §7 prediction survive? Yes — I could not falsify it.

§7 predicts *"an eighth defect will be in the PRODUCTION of a clause, not the CONSUMPTION of a
verdict."* All three Highs below are production-side (H1, H2) or context-production-side (H3). I
looked hard for a consumer that reaches a tally it should not and **found none** — the AttributeError
wall is real: I confirmed that hardcoding either printer gate (`isinstance(verdict, Measured)` →
`True`) reaches `verdict.mutations`, which does not exist on `NotMeasured`.

⚠ Three-for-three is corroboration, not proof. The prediction is also close to unfalsifiable in the
form it is written: once the consumption side is a type error, *every* remaining defect is
production-side by construction. Treat §7 as a description of the new shape, not as a scoring rule.

---

## HIGH

### H1 — `controls_green` DEFAULTS TO `True`. The one clause with a default is the one r3 B1 was about.

**`scripts/coverage_verdict.py:115`**

```python
    controls_green: InitVar[bool] = True
```

`declared`, `mutations` and `survivors` have no defaults — a producer that forgets them gets a
`TypeError`. Clause 1 is the exception: **omit it and the constructor asserts the controls were
green.** This is a fail-open on the exact clause that r2 dropped and r3 B1 had to restore.

**MEASURED (branch as shipped, no patch):**

```
Measured(files={}, declared=0, mutations=[], survivors=[])   ->  constructs
```

**The branch itself makes the opposite argument, 700 lines away.** `check-plan-code.py:1230-1237`,
on removing `evidence(..., ctx=RunContext())`:

> it had a `= RunContext()` default and the default was a **fail-open of exactly the class this whole
> change removes** … Every call site already passes one, so **requiring it costs nothing and removes
> the affordance**. The spec rejects the guarded accessor as "a convention with a nicer name"; a
> defaulted context is that same shape wearing a signature.

That reasoning is correct and it applies verbatim to `controls_green`. There is even a case asserting
the `evidence()` refusal (`:2660-2666`); there is **no twin** for `Measured`.

**Corroboration that the default already misleads a reader.** `check-plan-code.py:879-881` still
says, in the present tense, about the current code:

```python
    # ⟳ 2026-09-03. `trustworthy` answers ONE question: may the caller print the tally as a
    # coverage verdict? It defaults FALSE, so every path that does not explicitly earn it —
    # including ones added later — is untrustworthy by construction.
```

The property that paragraph promises — *default-deny, including for paths added later* — is now
**false**, and it is the specific property H1 removes. (See L1.)

**Failure scenario.** A future producer (spec §7's own prediction) adds a third path into
`mutate_delivered` or a sibling mode and writes
`Measured(files=ev_files, declared=n, mutations=ms, survivors=svs)` — forgetting the kwarg, over a
red control. Constructor passes. The printer emits `OK — … 0 survivor(s)`. Clause 1 is not merely
unchecked; the object positively claims it held.

**Fix, and it costs one token.** Drop the ` = True` and pass `controls_green=True` explicitly at
`check-plan-code.py:1168` (the honest zero, where `:1159-1165` already explains at length why it is
vacuously true there — so the explicit argument documents itself).

**MEASURED on a throwaway copy of `scripts/` (with `supabase`, `docs`, `node_modules/typescript`
present, per the plan's own recorded hazard):**

```
controls_green: InitVar[bool]                        # default removed
+ controls_green=True at check-plan-code.py:1168     # the ONE site that relied on it
->  coverage_verdict --self-test   21/21
->  check-plan-code  --self-test  196/196
```

**Control**: with the default removed and *no* call-site change, `check-plan-code --self-test` dies
with `TypeError: Measured.__init__() missing 1 required positional argument: 'controls_green'` — i.e.
exactly one site relied on it, and the tool says which.

**What would prove me wrong:** a call site that legitimately cannot know whether controls were green.
I found none — `:1001`, `:1222`, `:1620`, `:2651`, `:2723` all pass it explicitly; `:1168` is the only
omission and it is a place where `True` is a deliberate, documented choice.

---

### H2 — the honest zero HARDCODES `declared=0`, discarding `len(muts)`. The constructor cannot check a clause the producer lies about.

**`scripts/check-plan-code.py:1168`**

```python
        return (False, report, Measured(files=ev_files, declared=0, mutations=[], survivors=[]),
                RunContext(tally=tally, compared=compared))
```

`check()` has already computed `files, muts, problems, tally = extract(md)` at `:1142`. This return
throws `muts` away and asserts `declared=0`. Clause 2 — *"every DECLARED mutation produced a
verdict"* — then passes vacuously, because the number it compares against is one the producer
invented rather than one it measured.

`extract()` can return a non-empty `muts` with an empty `files`: the two tag families are parsed
independently (`FILE_TAG` at `:? / MUT_TAG`, `scripts/check-plan-code.py` `extract`), and file tags
are additionally **dropped** by the `unsafe_tag` branch after parsing.

**MEASURED — a plan with a well-formed `<!-- mutations -->` block declaring TWO mutations and no
parseable file tag:**

```
  ✗ no `<!-- file: … -->` tagged Python blocks found — nothing to assemble
```
```
GENERATED by scripts/check-plan-code.py — do not edit by hand.
  ...
  mutations declared and run: 0, caught 0
```
```
FAILED — plan's copy only, NOT compared: 0 file(s), 0 mutation(s), 0 survivor(s)
```

The **durable evidence block** — the artifact `--verify-evidence` re-derives and certifies as FRESH,
the one that outlives the console — states `mutations declared and run: 0` over a plan that declared
two. That is r3 B4's shape (*a header stating a number that is not what was declared*) reproduced
inside the change built to end it.

**This is NOT a regression.** Master prints byte-identical output on the same fixture (measured
against `git show master:scripts/check-plan-code.py`). What the branch changes is the *claim*: master
carried `declared: None`, which honestly means "unknown / never attempted"; the branch replaces it
with a `Measured` that positively asserts **zero were declared**. The union makes the lie explicit
and typed.

**Not live today.** I ran `extract()` over all 93 plans in `docs/superpowers/plans/`: every one with
`files == []` also has `muts == []`. This is latent, which is why it is High and not Blocking.

**Fix.** Branch on `muts`, so that a plan which declared mutations and ran none says so:

```python
        return (False, report,
                (Measured(files=ev_files, declared=0, mutations=[], survivors=[])
                 if not muts else NotMeasured.from_counts([], len(muts), ev_files)),
                RunContext(tally=tally, compared=compared))
```

**MEASURED on a throwaway copy — patched tree:**

* the 2-mutation fixture now prints
  `NOT MEASURED — plan's copy only, NOT compared: the mutation harness produced no coverage verdict (0 of 2 declared mutation(s) produced a verdict). Treat this as NOT CHECKED.`
  and the evidence block prints the same refusal plus `mutation entries recorded: 0`.
* **CONTROL — a plan with no code AND no mutations** (the F7 shape): patched and unpatched trees
  print **byte-identical** output — `mutations declared and run: 0, caught 0` /
  `FAILED — … 0 file(s), 0 mutation(s), 0 survivor(s)`. The honest zero survives untouched.
* `check-plan-code --self-test` on the patched tree: **196/196**.

So the fix is free, preserves T2a's honest zero exactly, and preserves F7.

**What would prove me wrong:** a demonstration that `extract()` cannot return `muts != []` with
`files == {}`. I built one and ran it, so it can.

---

### H3 — `RunContext.compared` is `None` on the honest-zero path EVEN WHEN `--compare` WAS GIVEN. T5 closed the affordance and left the reachable path open.

**`scripts/check-plan-code.py:1151`** initialises `compared = None`; the `not files` return at
`:1169` ships that context **before** the `if compare is not None:` block at `:1187` can ever run.
`evidence()` then reads it at `:1265`:

```python
    cmp = ctx.compared
    if cmp is None:
        out.append("  subject: the PLAN'S COPY of the code. --compare was not given, so")
        out.append("           nothing here was measured against the files in scripts/.")
```

**MEASURED — `check-plan-code.py <plan-with-no-file-tags> --compare <repo-root> --evidence`, branch
as shipped:**

```
  subject: the PLAN'S COPY of the code. --compare was not given, so
           nothing here was measured against the files in scripts/.
  ...
FAILED — compared: 0 file(s), 0 mutation(s), 0 survivor(s)
```

**Two lines of one output contradict each other**: the block says `--compare` was not given; the
final line says the mode was `compared`. The block is the durable half.

This is precisely r4 H1 — *the evidence misstating its own SUBJECT* — and it is precisely what the
plan's T5 (`docs/superpowers/plans/2026-09-08-coverage-verdict-union.md:196-207`) says making `ctx`
required prevents:

> omitting it makes `evidence()` print *"subject: the PLAN'S COPY of the code. --compare was not
> given"* over a run where it **was** given. That is r4 H1's defect … reintroduced as a default
> argument.

T5 removed the **default argument** route. It did not remove the **early-return** route to the same
wrong sentence, and the early-return route is the one a user can actually reach from the command
line. Fixing the affordance and leaving the live instance is this project's recorded
*instance-not-class* shape.

**PRE-EXISTING** — master reproduces it byte-for-byte (measured). It is High because it is live, it
is on the durable artifact, and the branch's own task list claims this class is closed.

**Fix.** Make the early return distinguish "compare given, nothing to compare" from "compare not
given" — e.g. set `compared = {} if compare is not None else None` before the `not files` return.
`evidence()` already handles a non-None empty dict correctly (it prints the DIFFED header with no
rows).

**Falsifier for the fix:** with it, the invocation above must print
`subject: the plan's blocks, DIFFED against the delivered files:` and the same invocation *without*
`--compare` must still print the "not given" sentence. Both must be asserted by a case, or the fix is
a change with no guard. **I did not implement or run this one** — flagged as the shape, not as a
verified patch.

---

## MEDIUM

### M1 — `NotMeasured`'s integrity is a CONVENTION. `Measured`'s is a constructor. The module's own thesis says which of those fails.

`scripts/coverage_verdict.py:154` makes `reason` an ordinary required field, and `:159-167`
documents `from_counts` as *"The ONLY constructor production code uses, so `reason` cannot disagree
with `entries` and `declared`."* Nothing enforces that. The class's own docstring is the enforcement.

**MEASURED:**

```python
NotMeasured(reason="…produced no coverage verdict (99 of 99 declared mutation(s) produced a verdict).",
            declared=3, entries=[])
->  constructs; prints "99 of 99" over declared=3 and zero entries
```

That is brief item 4's exact question — *can a producer build a `reason` that contradicts the
object's own `entries`/`declared`?* — answered **yes**.

Today every production site uses `from_counts` (verified by grep: `:901`, `:941`, `:947`, `:964`,
`:1004`, `:1225`), so this is latent. It is a Medium and not a Low because the module docstring's
central argument is that *"a guarded accessor is a convention with a nicer name"* — and a factory
nobody is forced to use is the same shape. The asymmetry is the finding: one variant is enforced by
construction and its sibling is enforced by a comment.

**Two fix shapes, with their costs stated:**
* (a) `__post_init__` asserts `reason == not_measured_reason(len(entries), declared)`. ⚠ this breaks
  the suite's own direct fixture `NotMeasured(reason="nothing was staged")` at `:239`, which would
  have to move to `from_counts`.
* (b) delete the `reason` field and make it a `@property` over `entries`/`declared`. Then
  `from_counts` is the only constructor *by construction*, which is the stronger form and the one
  consistent with `Measured`.

**Falsifier for either:** the contradictory object above must stop existing, and 21/21 + 196/196 must
stay green. I did not implement either.

### M2 — `Measured` is `frozen=True` and stores its lists BY REFERENCE. `NotMeasured.from_counts` copies; `Measured` does not.

`scripts/coverage_verdict.py:103-137`. `from_counts` defensively copies (`list(entries)`,
`dict(files or {})`, `:166-167`). `Measured` stores `mutations` and `files` as the caller passed them.

**MEASURED:**

```python
muts = [{"measured": True}]
m = Measured(files={}, declared=1, mutations=muts, survivors=[], controls_green=True)
muts.append({"measured": False})
->  m.declared == 1, len(m.mutations) == 2, entry 1 is NOT measured
->  m.declared = 9  raises FrozenInstanceError
```

`frozen=True` advertises an immutability the object does not have: the rebinding is refused, the
contents are not. This is brief item 6, answered: **yes, it is a real hole** — latent, because
`mutate_delivered`/`check()` drop `m_muts` immediately after construction.

It is the wrong variant to leave open. `Measured`'s existence *is* the claim; a post-construction
append converts a validated tally into an unvalidated one with no error anywhere. Copy in
`__post_init__` (`object.__setattr__`) or take tuples. **Falsifier:** the append above must leave
`len(m.mutations) == 1`, and 21/21 + 196/196 must hold.

---

## LOW

**L1 — two present-tense paragraphs describe a mechanism that no longer exists, and one of them
asserts the opposite of the truth.**
`check-plan-code.py:879-881` (*"It defaults FALSE, so every path that does not explicitly earn it —
including ones added later — is untrustworthy by construction"*) and `:1143-1146` (*"`check()` gets
the same default-deny `trustworthy` as `mutate_delivered`"*). There is no `trustworthy`. The ⟳
backlog-#91 note at `:894-898` corrects the first *below* it without deleting it, so a reader meets
the false statement first. Given H1, the stale text now actively asserts a safety property the code
does not have. (The other 20 `trustworthy` hits are historical narrative — *"MEASURED before the
fix"*, *"r2's own defect"* — and are fine.)

**L2 — `NotMeasured.files` is documented as "control runs only" but plan mode puts the assembly
census there.** `coverage_verdict.py:157` says `files: dict = ...  # control runs only — never a
coverage claim`. `check-plan-code.py:1199` fills `ev_files[name] = {"rc", "tail", "blocks": len(...)}`
from the plan-assembly loop, and that same dict travels into `NotMeasured.from_counts(..., ev_files)`
at `:1225`. `evidence()` then renders `N blocks assembled -> <suite tail>` **underneath** a
`NOT MEASURED` refusal. Defensible (assembly and control results are not a mutation tally), but the
field's comment is wrong for one of its two producers, and "no tally beside a refusal" is the rule
this branch enforces elsewhere.

**L3 — the plan's own ledger says nothing was done.** `2026-09-08-coverage-verdict-union.md` has
**11 unticked checkboxes and 0 ticked**, while three section headers read `✅ BUILT` / `✅ DONE` /
`PROVEN REQUIRED`. No `.claude/executing-plan` sentinel exists, so no gate fires — but the two
records inside one document disagree, and the checkbox half is the machine-readable one.

**L4 — T4's third bullet is discharged in the wrong file.** *"Decide and RECORD the
`check-ratchet-contract.py` position: it is a library, not a guard"* is recorded only in
`check-selftest-counts.py:101-104`'s POPULATION comment. `check-ratchet-contract.py` — where someone
auditing that guard's population will look — says nothing. (Verified: its real run discovers 28
guards and correctly excludes `coverage_verdict.py`, alongside the other non-`check-*` libraries.)

---

## What I checked and found NOTHING wrong with

Stated so a later round does not re-spend the time.

* **The mutation retarget (brief item 5) is sound.** 35 → 30 + 5 is not 35 → 30 and 5 new: **five
  entries genuinely MOVED** (same defect, renamed `shared predicate` → `constructor`), and **three
  were replaced by three**. All 12 touched entries were run individually against a proven-green
  control and **all 12 went red via the case they name** — no entry is caught by a sibling (the
  round-5 M1 shape). Matching is `w == f` (`:1117`), exact equality, so the multi-red-case entries
  (e.g. the CONTROL-clause mutation reddens both F3 cases) are still correctly attributed.
* **Are the 3 replacement entries weaker?** They are *different in kind* — the old ones hardcoded the
  gate open; the new ones make the refusal branch leak `len(verdict.entries)` — and the branch
  explains why at `:2967-2977` (hardcoding the gate now crashes with an unattributable
  AttributeError). I confirmed that reasoning: `verdict.files` exists on `NotMeasured`,
  `verdict.mutations` does not. The *property* cases added for r5 H1 (`:2536-2592`, three refusal
  paths driven through `main()`) still cover the weakening direction the gate mutations never could.
  **Net: not weaker.**
* **The `sys.modules` fix (brief item 8) is complete.** I enumerated every dynamic loader in
  `scripts/`, `tests/`, `.claude/` (`spec_from_file_location` / `SourceFileLoader` / `importlib`):
  8 loaders, of which exactly **two** load `check-plan-code.py` — `begin-plan.py:719` and
  `check-selftest-counts.py:182` — and both are fixed. The other six target `check-docs.py`,
  `check-catalog-coverage.py`, `check-dashboard-entry.py`, `check-plan-progress.py` (×2), none of
  which has a dataclass under `from __future__ import annotations`. No importer was missed.
* **`sys.path.insert(0, …)` at `:101`** is the established pattern (15 scripts do it), and I checked
  for stdlib shadowing: `set(scripts/*.py stems) & sys.stdlib_module_names == ∅`.
* **`ok` vs the VERDICT (brief item 2).** I traced every path. In both producers, every route to a
  `NotMeasured` also sets `ok = False` (the four `run_mutations` skip sites, `rc == 2`, both control
  failures, the four early returns). So `NotMeasured ∧ ok` is unreachable, and rc is 1 on every
  refusal. The reverse (`Measured ∧ ¬ok`) is intended and reads correctly — `FAILED — … 1
  survivor(s)` with the report lines saying why. **No misleading output found on this axis.**
* **`RunContext` required (brief item 3).** The `TypeError` case at `:2660-2666` is **not vacuous**:
  restoring the default is a behaviour-preserving edit (every call site passes one), so only that
  case can see it — which is exactly why it is written as a `try/except TypeError` rather than an
  output assertion. The lying-context question, however, is answered YES — see **H3**.
* **F6/F7 (brief item 7).** The plan's F6 argument is **not** self-serving. `EXPECTED_MUTATIONS`
  requires every manifest file to be declared, `--mutate` prints `len(verdict.files)`, and
  `coverage_verdict.py` necessarily joins the corpus — so 31 → 32 is forced by the change, and
  byte-identity is unachievable *by construction*, not by convenience. The plan's restatement
  (mutations and survivors held at 359/0; file count 31 → 32 the only permitted delta) is the right
  strictness. The plan also says F6 is thin, and volunteers that the unmeasured path — #91's whole
  subject — is never reached by it. That is the correct disclosure. **F7** I reproduced: the named
  baseline plan does hit the `not files` return, and it is the only baseline exercising T2a.
* **`Measured.__post_init__` clause ordering.** Clause 1 raises before clauses 2 and 3 are evaluated,
  so a red control cannot be masked by a cardinality error or vice versa; each mutation's `expect`
  therefore names a stable case. Verified by the 5 single-mutation runs.

---

## Answering the coordinator's two direct questions

**"Attack the honest-zero mapping hardest — if it is wrong the whole change is wrong."**
The *variant choice* is **right** and I could not break it. `Measured(declared=0)` over a plan that
assembled nothing is a true statement — zero declared, zero verdicts, no `caught` resting on any
control — and `NotMeasured` genuinely cannot render the F7 line. The `controls_green=True` there is
vacuous in the exact sense `:1159-1165` claims, and I confirmed the boundary: with files present and
a red control, `declared = len(muts)` and the construction still raises.

What is wrong is **one input to it**: the hardcoded `declared=0` (H2). The mapping is sound; the
producer feeding it is not. That is the distinction worth carrying — the whole change does not fall.

**"Try to falsify §7's prediction."** I could not. All three Highs are production-side. See the
section above for why that is weaker evidence than it looks.

---

## Repo state

`git status --porcelain` after this review: the only entry is this file
(`docs/reviews/claude/plan-coverage-verdict-union-r1-claude.md`). All experiments ran in
`/tmp/m91/**` throwaway trees; nothing in the repo was edited.

**Verdict: NOT CONVERGED.** H1 and H2 are one-line fixes, both already measured green (21/21 and
196/196) with controls. H3 is a shape, not a verified patch. M1 and M2 are latent asymmetries that
should be decided rather than carried silently.

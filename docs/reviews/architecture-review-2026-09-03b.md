# Architecture Review #7 — 2026-09-03 (b)

**Trigger:** `docs/dev-process.md:107` — **four non-converging review rounds**, not a milestone.
**Subject:** the verification stack, specifically the mutation-drift-report contract in
`scripts/check-plan-code.py` (merged `87ea0001` / PR #214, `5fc92b73` / PR #215).

> ⚠ **This is the SECOND architecture review today.** `architecture-review-2026-09-03.md` was
> convened this morning over the guard-inventory question (four inventories, nothing reconciles
> them). **Its findings A–E are not re-opened here**, and neither are ADRs 0001–0013.
> This review asks a different question.

---

## The question

**Seven consecutive adversarial review rounds each found a defect inside the previous round's fix.**

| round | verdict | defect found in the previous round's fix |
|---|---|---|
| spec v1–v3 | NOT CONVERGED ×3 | a POSITION standing in for a semantic property, three times |
| code r1 | NOT CONVERGED | a timeout counted as a verdict — inside the fix for that |
| code r2 | NOT CONVERGED | `check()` had no `trustworthy` concept — the sibling producer |
| code r3 | NOT CONVERGED | the shared predicate held HALF the contract; the fix had no falsifier |
| code r4 | NOT CONVERGED | **two printers, and r3 covered the one CI never runs** |

Each round's fix was *individually correct*. Per-task review only ever sees one change, so it
cannot see what they add up to. That is what this review is for.

---

## Finding 1 — 🔴 **The coverage verdict has no interface, and that is the cause of all seven rounds**

Not a metaphor. Every one of the seven defects has the same shape:

- a **producer** of the evidence dict that set `trustworthy` while holding only part of its
  contract, or
- a **consumer** of the evidence dict that read a tally without consulting `trustworthy`.

**Measured** (AST over `scripts/check-plan-code.py`, production code only —
`scratchpad/phase6-ev.py`):

```
  functions that touch `ev`:  not_measured_line, mutate_delivered, check,
                              evidence, verify_evidence, main        (6)

  ev['trustworthy']   WRITTEN by 2: check, mutate_delivered
                      READ    by 2: evidence, main
  ev['mutations']     READ    by 4: check, evidence, main, not_measured_line
  ev['survivors']     READ    by 2: check, main
  ev['files']         READ    by 4: check, evidence, main, mutate_delivered

  READ a tally WITHOUT reading trustworthy:
      ev['mutations']  -> check, not_measured_line
      ev['survivors']  -> check
      ev['files']      -> check, mutate_delivered
```

`ev` is a **plain dict**. Any producer may write any key; any consumer may read any key. The rule
that actually matters — *never read a tally without consulting the verdict* — exists only as
**convention**, re-implemented (or forgotten) at each of six call sites.

**Deletion test.** Delete `ev`: complexity does not vanish, it reappears across six functions that
must then each thread the same six values. So the concept earns its keep. But it is **shallow** —
its interface (seven keys, two writers, six touchers, plus one unwritten ordering rule) is as
complex as what it holds. That is the definition of a shallow module, and the seven rounds are the
bill for it.

**Why per-task review could never converge on this.** Each round correctly fixed *one* toucher.
Nothing about fixing `evidence()` makes `main()` safe; nothing about fixing `main()`'s plan printer
makes its `--mutate` printer safe. The rounds were not failing — they were **enumerating**, one
consumer per round, a set the type system could have closed in one move.

**Evidence this is the mechanism, not a story:** r4's Blocking was found by asking *"which consumers
read a tally?"* and noticing one was unguarded. That question is answerable in one line against a
real interface, and took a full adversarial round against a dict.

---

## Finding 2 — 🟠 **Sixteen guards each re-implement the self-test harness; none share one**

```bash
grep -l "def case(" scripts/check-*.py scripts/gen-*.py scripts/page_*.py | wc -l   # 16
grep -ln "from check_plan_code import|import check_plan_code" scripts/*.py          # (none)
grep -ln "def count_drift" scripts/*.py       # scripts/check-plan-code.py  (1)
grep -ln "count_drift" scripts/*.py           # check-plan-code, check-selftest-counts  (2)
```

Sixteen independent `case()` helpers. One shared helper in the whole stack (`count_drift`), with a
single importer.

This is the **cause** of a defect this project has already paid for: a report format is a contract,
and twelve mutations once reported "0 red cases" over a failure line-shape the consuming harness did
not parse. With sixteen private report formats and one parser, that is a standing hazard rather than
a past incident. **The seam does not exist**: there is no module whose interface is *"a self-test
result"*, so there is nothing for a consumer to depend on except each guard's local string habits.

⚠ **Scoped against this morning's review.** Finding A there was *"four inventories answer one
question"* — a **counting** problem. This is a **shape** problem: even a perfect inventory would not
tell a consumer how to read a guard's output. Different defect, different fix, deliberately stated
so the two are not merged.

---

## Finding 3 — 🟡 **`check-plan-code.py` is 2,517 lines doing four jobs, half of it its own suite**

```
  total lines            2517
  _self_test             1274   (50% of the file)
  top-level functions      20
```

The four jobs, none separated by a seam:

1. **assemble** a plan document's tagged code blocks into a temp tree (`extract`, `check`)
2. **run mutations** over a delivered tree (`mutate_delivered`, `run_mutations`)
3. **render evidence** (`evidence`, `not_measured_line`, `verify_evidence`)
4. **check drift** (`count_drift`, `EXPECTED_MUTATIONS`, `home_escapes`)

Job 4 is the only one another script imports. Jobs 1–3 are reachable only by running the file as a
process. **The interface is the test surface** — and here the only interface is a CLI, which is why
every review round had to construct fixtures through `main()` or reach past the front door with
`importlib`.

**This is the weakest of the three findings and is stated as such.** Splitting a working 2,500-line
guard has real cost and this project has measured before that *levelling* beats *flattening*. It is
listed because it is the reason findings 1 and 2 are expensive to fix, not because it is independently
urgent.

---

## What we decided this milestone that isn't written down

The question `dev-process.md:123` requires. Three answers, and the first is the significant one:

1. ⭐ **`CONTEXT.md` has no vocabulary for the verification stack.** Nine sections; every one is
   about the product (Async Jobs, Cost Guardrails, Storage Seam, Artifacts, Addressing, Personal
   Review, AI Ratings, Detail Layer) except one about page generation. `grep -n
   "mutation|harness|guard|ratchet" CONTEXT.md` returns **one** line, and it is incidental.
   **Seven review rounds were argued in vocabulary the project's own domain model does not contain.**
   Without shared terms each round could only name the instance in front of it — which is exactly the
   failure that recurred. *This is the finding I would act on first even if nothing else changed.*
2. **"Coverage verdict" is now a real concept** with a real invariant (three clauses: controls green,
   every declared mutation produced a verdict, every entry a real verdict) and it is written only in a
   docstring.
3. **Anchors bind by TEXT is a standing property, not an accident.** Four occurrences in this slice
   alone (r3 ×2, r4 ×4 more). It is treated as a surprise each time.

---

## Deepening candidates

Presented per the skill; **no interfaces proposed yet** and nothing filed to `docs/backlog.md` —
triage is the user's step, per review #4's precedent.

### Candidate 1 — give the coverage verdict an interface ⭐ RECOMMENDED

- **Files:** `scripts/check-plan-code.py` (`mutate_delivered`, `check`, `evidence`,
  `not_measured_line`, `verify_evidence`, `main`)
- **Problem:** finding 1. Seven rounds enumerated consumers of a shallow dict one at a time.
- **Solution:** a module whose interface makes the tally **unreachable without the verdict** — the
  numbers are not attributes a consumer may read, they are returned by a call that also returns the
  trust state. A new consumer then *cannot* print an unearned tally; it would not compile/run.
- **Benefits — leverage:** the rule is stated once and enforced by construction, so round 8 cannot
  find an eighth unguarded consumer. **Locality:** the three-clause contract lives with the data it
  describes instead of in a docstring plus six call sites. **Tests:** the interface becomes the test
  surface — today the suite reaches past it with `importlib` and hand-built dicts, which is why
  round 4 could find a Blocking that 177 green cases could not.

### Candidate 2 — one self-test result seam for the sixteen guards

- **Files:** all 16 `scripts/check-*.py` with a private `case()`, plus `check-selftest-counts.py`
- **Problem:** finding 2. Sixteen private report formats, one consuming parser, no seam.
- **Solution:** one module owning *"a self-test result"* — the `case()` helper and the result line
  it prints — imported rather than re-typed.
- **Benefits — leverage:** a consumer depends on one contract instead of sixteen habits.
  **Locality:** the "0 red cases over an unparsed line shape" class becomes structurally impossible.
  ⚠ **Cost is real:** 16 files, and this project has measured that flattening a guard stack can
  invert its own cost/benefit verdict. Worth grilling before committing.

### Candidate 3 — name the verification stack in `CONTEXT.md`

- **Files:** `CONTEXT.md`
- **Problem:** the "not written down" finding above. Cheapest item here by an order of magnitude.
- **Solution:** a section defining *guard*, *ratchet*, *mutation manifest*, *anchor*, *coverage
  verdict*, *control*, in the same register as the existing nine.
- **Benefits:** candidates 1 and 2 both need these words to be discussed at all. **This is a
  precondition for the others, not an alternative to them.**

---

## Verdict

The four-non-converging-rounds trigger fired on a **real** structural defect, and the trigger was
right to fire. But note what it caught: not a runaway spec, and not rounds that were wrong. Rounds
1–4 were each correct and each converged on their own scope. They could not converge *collectively*
because the thing they were reviewing has no interface to converge on.

⚠ **Read the trigger off the CAUSE, not the count** — as `dev-process.md:107` itself instructs. The
cause here shifted mid-slice: rounds 1–3 were positional-proxy defects and round 4's reviewer
confirmed that pattern did **not** recur; round 4's defect was incomplete scope. Both are symptoms
of finding 1. A fifth round scoped to r4's fold would very likely find an eighth consumer, and would
be the wrong instrument.

**Recommendation: candidate 3 first (it is a precondition), then candidate 1. Not round 5.**

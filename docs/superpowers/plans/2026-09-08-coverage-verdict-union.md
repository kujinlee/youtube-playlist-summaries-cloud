# The coverage verdict becomes a type you cannot read wrongly — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #91.** Spec: [`docs/superpowers/specs/2026-09-04-coverage-verdict-interface-design.md`](../specs/2026-09-04-coverage-verdict-interface-design.md) v1.1, APPROVED.

**Goal:** Replace the 7-key `ev` dict in `scripts/check-plan-code.py` with a tagged union
`Measured | NotMeasured` in its own module, so no consumer can reach a coverage tally without having
handled the not-measured case.

**Architecture:** New `scripts/coverage_verdict.py` holds the union, its contract, and the
not-measured clause renderer. `check-plan-code.py` imports it — **never the reverse.** Run-context
that is not verdict data (`tally`, `compared`) travels in a separate frozen `RunContext`.

**Tech Stack:** Python 3 stdlib only (`dataclasses`, `sys`). Self-tests inline via `--self-test`.

---

## ⚠ THE METHOD WAS INVERTED ON PURPOSE — this plan is written FROM a working build

Backlog #95's plan failed its Post-Plan Gate **twice, both times on instrumentation**, because it was
hand-written Markdown that could not be executed. #91 is the same shape of change in the same file.
So the code was built and RUN in a scratch tree **before** this plan was written. Every number below
was measured on 2026-09-08, not estimated.

Scratch tree: `/tmp/v91/work`. Baselines: `/tmp/v91/base/`.
Full evidence: `scratchpad/91-evidence-dossier.md`.

⚠ **A scratch copy MUST include `node_modules/typescript`.** `HARNESS_TREE`
(`check-plan-code.py:315-331`) requires `scripts`, `supabase`, `docs`, `node_modules/typescript`. A
tree without it gives a **191/194 RED control with nothing changed** — measured. Any task saying
"copy to a scratch tree" means this.

## What is DECIDED and must NOT be re-litigated

* **Tagged union.** The guarded accessor is **REJECTED** — it fails exactly as
  `verdicts_are_trustworthy` failed in r3: that helper *was* the "one shared rule" fix and still
  shipped holding two of its three clauses.
* **Its own module** `scripts/coverage_verdict.py`; `check-plan-code.py` imports it, never the reverse.
* `NotMeasured` has **no `survivors` field**; its list is **`entries`**, not `mutations`.
* `Measured.__post_init__` enforces all three clauses and raises `VerdictContractError` otherwise.
* `controls_green` is an **`InitVar`, not a field** — a fact about the run, not the verdict. You
  cannot ask a `Measured` whether its controls were green, because it only exists if they were.

## Measured state of the build

| | |
|---|---|
| `coverage_verdict.py --self-test` | **13/13, rc=0** |
| `check-plan-code.py --self-test` (rewired) | **195/195** (baseline 194/194) |
| `ev` touchers | **7**, not the backlog row's 6 — it omits `_self_test` |
| `EXPECTED_MUTATIONS` | **359** held; 31 → 32 files; this file 35 → **30**, new module **5** |
| `--mutate .` on the rewired tree | `32 file(s), 359 mutation(s), **0 survivor(s)**`, rc=0 |
| Anchors failing to resolve uniquely | **0** |
| F7 (plan stdout + evidence block) | ✅ **byte-for-byte IDENTICAL** |

---

## The mutation-anchor hazard — REAL, and already discharged

35 mutations bind to `check-plan-code.py` by **quoted text**, and the rewire deletes lines many of
them quote. This is the recorded hazard: *a refactor orphans the mutation guarding it, anchors bind
by text, and the suite stays green.* It is real here — the rewired tree's `--self-test` is
**195/195 GREEN**, and `--self-test` structurally cannot see anchor orphaning. Only `--mutate .` can.

**It fails LOUD, which is the safety net** (`check-plan-code.py`, `find not in src` branch):

<!-- illustrative -->
```python
if find not in src:
    ok = False
    report.append(f"mutation {name!r}: anchor NOT FOUND — it was not applied, "
                  f"so its 'caught' verdict would be meaningless")
```

`ok = False`, one report line per orphan, and missing entries make `len(mutations) != declared`, so
the run reports **NOT MEASURED**. ⭐ The retarget is enforced by a **gate**, not by discipline — and
the enforcing clause is the cardinality clause, one of the three this change moves into
`Measured.__post_init__`. The harness catches its own refactor breaking itself.

### MEASURED OUTCOME — the retarget is DONE and the arithmetic holds

| | before | after |
|---|---|---|
| `EXPECTED_MUTATIONS` total | 359 | **359** (held) |
| `scripts/check-plan-code.py` | 35 | **30** |
| `scripts/coverage_verdict.py` | — | **5** |
| manifest entries on disk | 359 | **359** |
| anchors failing to resolve uniquely | — | **0** |

**30 + 5 = 35**, total held at **359**. Five entries were retargeted 1:1 onto the constructor's
clauses; seven more were re-anchored in place. `--mutate .` on the rewired tree:

```
OK — delivered scripts mutated: 32 file(s), 359 mutation(s), 0 survivor(s)   rc=0
```

**0 survivors across 359** — every retargeted mutation still goes red via the case it names.

> ⚠ **A CORRECTION WORTH KEEPING, because it is the shape this project keeps paying for.**
> A first measurement reported **12 ORPHANED / 0 MOVED** and this plan was drafted around it. It was
> **wrong**: the classifier read the manifest from the REAL REPO and matched those anchors against
> the REWIRED code — but a retarget *edits the manifest*, so it compared the old corpus to the new
> code and manufactured twelve phantom orphans. The `--mutate .` run refuted it, printing zero
> `anchor NOT FOUND`. **The code did what I measured; I measured the wrong SET.** Re-measured against
> each tree's own manifest, the table above is the truth.

---

## Tasks

### T1 — `scripts/coverage_verdict.py`: the union ✅ BUILT

- [ ] Land the module: `VerdictContractError`, `Measured`, `NotMeasured`,
      `not_measured_reason(entries, declared)`, `NotMeasured.from_counts(...)`.
- [ ] `--self-test` green.

**Falsifiers (F1–F5, F8):** all verified in the scratch tree — see T6.

### T2 — rewire all SEVEN `ev` touchers ✅ BUILT

`main` · `mutate_delivered` · `evidence` · `check` · `_self_test` · `verify_evidence` ·
`not_measured_line`.

- [ ] `check()` returns `(ok, report, verdict, RunContext)`; `mutate_delivered()` stays a 3-tuple —
      that mode has neither a tally nor a compare.
- [ ] `not_measured_line(nm, subject="")` composes `NOT MEASURED — ` + subject + `nm.reason`.

**⭐ T2a — the HONEST-ZERO mapping. Get this wrong and F7 cannot pass.**
Plan-mode `declared is None` (nothing to assemble) maps to
**`Measured(files, declared=0, mutations=[], survivors=[])` — NOT `NotMeasured`.**

Why, measured: the F7 baseline prints `0 file(s), 0 mutation(s), 0 survivor(s)` via `main`'s second
disjunct (`:2903`), and `NotMeasured` has no `survivors` field. Probe
(`scratchpad/probe_honest_zero.py`), with a control:

| | |
|---|---|
| `Measured(files={}, declared=0, mutations=[], survivors=[], controls_green=True)` | **constructs**, renders the exact F7 line |
| **CONTROL** — same shape, `declared=1`, no verdicts | **raises** `0 verdict(s) for 1 declared mutation(s)` |

Corroborating: `verdicts_are_trustworthy([], 0, True)` is **already `True`** today, so this is
consistent with shipped behaviour, not a change to it.

⭐ **This converts backlog #93 from a comment into a type distinction** — plan-mode
`declared is None` is an honest **measured zero**; `--mutate`-mode `declared is None` means the run
died. Same words, opposite meaning. `check-vocabulary-collisions.py` actively encourages unifying
those two gates, which is what makes it a trap; under the union they are different types.

⚠ `ok` and the VERDICT stay independent: the F7 run is `Measured` **and** `not ok` (rc=1, 12
complaints). "Failed" and "not measured" must not collapse into one concept.

### T3 — retarget the orphaned mutations, hold the arithmetic ✅ DONE, VERIFIED

- [ ] Land `scripts/mutations/coverage_verdict.json` (5 entries) and the reduced
      `check-plan-code.json` (30), each still going red **via the case it names**.
- [ ] `EXPECTED_MUTATIONS`: `check-plan-code.py: 35 → 30`, `coverage_verdict.py: 5`. **Sum held at 359.**
- [ ] Verify: `--mutate .` → `32 file(s), 359 mutation(s), 0 survivor(s)`, rc=0, zero `anchor NOT FOUND`.

⚠ A relocation must not be able to read as a deletion — which is exactly why the sum is held rather
than allowed to fall to 354. The inline-renderer seam held its sum at 73 for the same reason.

⚠ **Verify the retarget against each tree's OWN manifest.** Matching the delivered repo's manifest
against rewired code reports phantom orphans — measured, and it produced a wrong count of 12 in this
very slice.

### T4 — register the new module with the ratchets. **PROVEN REQUIRED.**

`coverage_verdict.py` lands in a **blind spot of both ratchets**:
* `check-ratchet-contract.py:467` globs `scripts/check-*.py` → **no match**; R1/R2/R3 do not bind.
* `check-selftest-counts.py:207` globs `scripts/*.py` → matches, but only *declaring* scripts are
  ratcheted.

Measured in throwaway copies, control first (`scratchpad/probe_ratchet_binding.py`):

| state | rc | |
|---|---|---|
| **A control** — prose "13 cases", unpinned | 0 | 28 declare — module invisible |
| **B** — canonical claim, UNPINNED | **1** | *"declares a case count but is not in POPULATION, so nothing checks it. Add it."* |
| **C** — canonical claim AND pinned | 0 | **29** declare, "every one verified by running it" |

- [ ] Declare the count canonically — `--self-test  # N cases` — in the **MODULE** docstring.
      `declares()` reads `ast.get_docstring(ast.parse(src))` (`:199`), **not** the function's.
- [ ] Add `"coverage_verdict.py"` to `check-selftest-counts.POPULATION`.
- [ ] Decide and RECORD the `check-ratchet-contract.py` position: it is a **library, not a guard**, so
      widening the `check-*` glob is wrong. State the deliberate exclusion rather than leaving it
      unexamined.

⚠ Doing only the first fails CI. Doing neither ships a count that can drift silently — already
measured three times here (`codex-review.py` 35 vs 51; `check-review-rounds.py` 14 vs 22).

### T5 — make `RunContext` required, not defaulted

`evidence(v, ctx=RunContext())` and `verify_evidence(..., ctx=RunContext())` currently **default** the
context. All six in-tree call sites pass one, so this is not a live defect — but omitting it makes
`evidence()` print *"subject: the PLAN'S COPY of the code. --compare was not given"* over a run where
it **was** given. That is r4 H1's defect — misstating the subject of the evidence — reintroduced as a
default argument.

- [ ] Make `ctx` required. Zero cost: every call site already passes it.

⚠ The spec rejects the guarded accessor as *"a convention with a nicer name."* A defaulted context is
the same shape, inside the change that exists to remove that shape.

### T6 — discharge F1–F8

| # | Falsifier | State |
|---|---|---|
| F1 | `Measured` with `len(mutations) != declared` → raises | ✅ verified |
| F2 | entry whose `measured` is not `True` → raises (incl. `1`, `"yes"`) | ✅ verified |
| F3 | `controls_green` not `True` → raises | ✅ verified |
| F4 | `.survivors` on `NotMeasured` → AttributeError | ✅ verified |
| F5 | `.mutations` on `NotMeasured` → AttributeError | ✅ verified |
| F6 | clean `--mutate .` stdout byte-for-byte | ⚠ **one-token delta — see below** |
| F7 | plan-mode stdout + evidence block byte-for-byte | ✅ **IDENTICAL, both files** |
| F8 | delete the constructor's clause-checking → red, naming the case | ⚠ re-run against the REWIRED tree |

**F7 DISCHARGED.** Both `plan.txt` and `evidence.txt` re-derived from the rewired tree are
byte-for-byte identical to the pristine baselines. This is the falsifier that proves T2a's
honest-zero mapping: the run prints `0 file(s), 0 mutation(s), 0 survivor(s)` — a line
`NotMeasured` physically cannot produce.

**⛔ F6 IS OVER-SPECIFIED AND CANNOT PASS AS WRITTEN. Correct the spec.** The entire diff is:

```
< OK — delivered scripts mutated: 31 file(s), 359 mutation(s), 0 survivor(s)
> OK — delivered scripts mutated: 32 file(s), 359 mutation(s), 0 survivor(s)
```

Mutations 359→359, survivors 0→0. The file count moves because **`coverage_verdict.py` joins the
mutation corpus** — the change adds a mutated file, so byte-identity is unachievable by construction.
**Restate F6 as:** *mutation count and survivor count unchanged at 359 / 0; the file count moves
31 → 32, and that is the ONLY permitted difference.* Left as written, a future run reads a
legitimate pass as a failure.

**F6 baseline** — `python3 scripts/check-plan-code.py --mutate .`, rc=0, md5 `365763a12cb4b7963ad00c76069d8963`:
```
OK — delivered scripts mutated: 31 file(s), 359 mutation(s), 0 survivor(s)
```

⚠ **F6 IS THIN AND THE PLAN SAYS SO.** A clean run emits **one line** — `report` is empty on the
happy path — and only ever exercises the `trustworthy=True` printer branch. **The unmeasured path,
the entire subject of #91, is never reached by F6.** What actually defends the `NotMeasured`
rendering is the `_self_test` fixtures and the `--mutate` entry-point cases added for r5 H1. F6 is
necessary, not sufficient. Do not let a green F6 read as broad protection.

**F7 baseline** — subject was UNIDENTIFIED until measured; it is
`docs/superpowers/plans/2026-08-29-mutation-manifest-retarget.md`:
```
python3 scripts/check-plan-code.py <plan>            -> /tmp/v91/base/plan.txt      rc=1
python3 scripts/check-plan-code.py <plan> --evidence -> /tmp/v91/base/evidence.txt  rc=1
```
Re-derived from the pristine tree: **byte-for-byte identical** both times.

⚠ rc=1 — a **failing** plan-mode run, not the "clean" one spec §4 F7 describes. **Keep it:** it is
the only baseline that exercises the `declared is None` branch T2a depends on. **Correct the spec's
F7 wording** to name this subject instead of saying "clean".

---

## Spec corrections this plan carries

* **§5 Q3 DISSOLVES.** It expects "~10 hand-built `ev` dicts, some deliberately building INVALID
  states, which F1–F3 would make unwritable." There are **6** (`:2539-2607`), and none are invalid —
  4 are **unmeasured**, which the union makes a free, unconstrained variant; 2 are valid `Measured`.
  **No escape hatch is needed.** The dict conflated "an unmeasured run" with "an invalid `Measured`".
* **§4 F7** should name its subject (above) rather than say "clean".
* **Backlog row #91** says 6 `ev` touchers; it is **7**.

## What this does NOT fix — stated, not discovered later

An interface stops a consumer reading a tally it should not. It does **not** stop a producer
computing `controls_green` wrongly — that was r4 M1, answered by `control_is_green(rc, out)`, already
shipped. If a round finds an eighth defect, the honest prediction is that it is in the **production**
of a clause, not the **consumption** of a verdict.

## Sequencing

T1 → T2 (incl. T2a) → T3 → **T4** → **T5** → T6.

T1–T3 are built and verified in the scratch tree. **T4 (ratchet registration) and T5 (required
`RunContext`) are the outstanding code work**, plus the F8 re-run and the two spec corrections.

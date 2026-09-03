# Post-Plan Gate round 4 — Claude half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` **v4** (commit `1aacbf35`),
implementing `docs/superpowers/specs/2026-09-02-guard-inventory-population-design.md` v4.
**Scope:** v4's own five fixes, per the brief. **Reviewer:** Claude (Opus 5), 2026-09-03.

**VERDICT: NOT CONVERGED** — 2 Blocking, 2 High, 3 Medium, 4 Low.

> ⚠ **This round's Blockings are again defects in the previous round's own fixes** — both live in
> T4's new `read_population()` extraction, which is round 3's repair. That is the seventh consecutive
> round of this slice with that shape.
>
> ✅ **But the plan otherwise RUNS, end to end, and further than round 3 got.** I applied T1–T9 in a
> temp tree and measured: **`guards discovered (28)`**, `ratchet contract OK`, `self-test 35/35`,
> **`OK — delivered scripts mutated: 8 file(s), 167 mutation(s), 0 survivor(s)`**, `check-docs.py`,
> `check-anchors.py`, `check-selftest-counts.py`, `check-review-rounds.py` all exit 0, and **F1–F7 and
> F9 all pass**. Four of the five things the brief asked me to attack are sound. Details in
> *What I checked and found clean*.

## Method

Full build in `/Users/kujinlee/.claude-tmp/.../scratchpad/tree` (rsync of the branch, no `.git`).
Every task applied literally from the plan's own snippets. No `git` mutation in the working tree; no
Postgres. Every premise below is either executed or quoted with `file:line`.

---

## BLOCKING

### B1 — T4's CANNOT-RUN repair does not close the gap it names, under EITHER reading, and I measured both

`docs/superpowers/plans/2026-09-02-guard-inventory-population.md:490-518`

T4 Step 1 opens with the round-3 finding it exists to fix:

> ⛔ **The CANNOT-RUN branch must be REACHABLE by a case** … v3 then put a new `return 2` **inside
> `main()`** with no case, no mutation and no falsifier. Measured: the branch works … and **nothing
> would notice if it became `return 0`.**

The fix is to add `read_population(scripts_dir) -> tuple[dict[str,str], str|None]` (`:500-502`),
give it a case, and mutate its reason to `None`. **But the plan never says to wire it into `main()`**
— and `main()`'s read loop was already rewritten by T1 Step 6 (`:229-241`) to call `population_paths`
directly. Then T4 Step 2 (`:507-518`) changes `main()` in a *different* way, wrapping `evaluate` in
`try/except SyntaxError: … return 2`.

Those two are competing mechanisms for one concern, and only one can be live.

**Reading A — `main` is rewired to `read_population`.** Then `read_population` refuses before
`evaluate` is ever called, and Step 2's handler is dead code. Executed, with an unparseable
`scripts/zz-unparseable.py` present:

```
CANNOT RUN — a script under scripts/ does not parse: scripts/zz-unparseable.py: invalid syntax
Treat this as NOT RUN.
run rc=2
--- mutate Step 2's handler: return 2 -> return 0 ---
self-test: 35/35 passed      selftest rc=0
run rc=2                     (unchanged)
--- DELETE the whole Step 2 handler ---
self-test: 35/35 passed      selftest rc=0
run rc=2                     (unchanged)
```

Deleting the entire block the plan instructs an implementer to add changes **nothing** — not the
suite, not the exit code, not the message.

**Reading B — `main` keeps T1 Step 6's loop and `read_population` is only reached by its case.** Then
`read_population` is a shadow implementation, and the LIVE cannot-run exit is Step 2's handler.
Executed:

```
--- mutate the LIVE handler: return 2 -> return 0 ---
self-test: 35/35 passed      selftest rc=0   <-- the suite does not notice
run rc=0                     <-- a genuine CANNOT RUN is now reported as SUCCESS
```

**That is verbatim the v3 defect T4 quotes.** The case and the mutation guard the shadow, not the
live path — the *"a second implementation of one rule DRIFTS"* shape, and the same class as T1's own
argument ("coverage of the function, none of its use", `scripts/check-ratchet-contract.py:163-171`).

**OBSERVATION that would make this FAIL:** with T1–T9 applied, delete the `try/except SyntaxError`
block from `main()` and run `--self-test` plus a live run with an unparseable `scripts/*.py`. If both
are byte-identical to before the deletion, the block is unguarded dead code. Measured above: they are.

**What v4 needs to say:** one mechanism. Either `main` consumes `read_population`'s reason (and Step 2
is deleted), or Step 2 is the live exit and `read_population` must not exist. If the first, the plan
must give the wiring — `texts, cannot_run = read_population(...)`, what `main` prints, and that it
returns 2 — because none of that is written down today.

---

### B2 — T4 Step 1 promises a manifest entry that T7 makes impossible; adding it runs ZERO mutations

`plan:505-506` vs `plan:658-699`

T4 Step 1 ends: *"and a manifest entry mutating the reason to `None`, expecting that case."*
**T7's manifest has five entries and none of them is that one**, and `plan:698-699` pins
`EXPECTED_MUTATIONS` at **5** with the sum oracle at **167**.

`scripts/check-plan-code.py:588-597` makes the count exact, not a floor, and checks it **before**
`copytree` — so a sixth entry aborts the run before a single mutation executes. Executed, with T4's
sixth entry added exactly as described:

```
✗ scripts/check-ratchet-contract.py: manifest holds 6 mutation(s), expected 5. Coverage cannot
  change silently — if this is deliberate, change EXPECTED_MUTATIONS in check-plan-code.py in the
  SAME commit and say why in the message
FAILED — delivered scripts mutated: 0 file(s), 0 mutation(s), 0 survivor(s)
EXIT=1
```

**Zero mutations executed** — which is precisely the failure T7 Step 2's own ⛔ block warns about
(`plan:702-707`: *"its `--mutate .` **control** run then refuses, and **zero mutations execute** … A
mutation harness that runs nothing looks exactly like one where everything passed."*). The plan
contains the warning and the trap in the same document.

So an implementer has two choices and both are wrong:
- follow T4 → `--mutate .` red, nothing measured;
- follow T7 → the mutation T4 promises, and that spec §3.4 leans on (*"repaired here with a case"*),
  does not exist. Combined with B1, the CANNOT-RUN exit ships with **no falsifier at all**.

**OBSERVATION:** add T4's sixth entry, run `python3 scripts/check-plan-code.py --mutate .`. If it
exits 1 with `manifest holds 6 mutation(s), expected 5`, the two tasks contradict each other.
Measured above.

**Fix:** decide the count in one place. If the read_population mutation is wanted, T7 says
`EXPECTED_MUTATIONS` is **6** and the sum is **168**, and lists six entries.

---

## HIGH

### H1 — F8 FAILS on T9 Step 0's own required output. The two instructions cannot both be satisfied

`plan:770-785` (F8) vs `plan:808-814` (T9 Step 0)

T9 Step 0 requires the closed rows to keep their history:

> Keep the history (the measurement, the falsified claim) — correct the tense and the mechanism.

For row #73 the measurement **is** the symbol: `docs/backlog.md:101` today reads
*"`grep -rn discover_ratchets scripts/ .github/ .claude/` returns exactly two hits"*. You cannot keep
that measurement without the token. But v4 added `docs/backlog.md` to F8's path list (`plan:782`),
and F8 expects **no output**.

I ran the whole build — T8 corrected all eleven §7 sites, T9 rewrote both row bodies keeping the
history — and then ran F8 verbatim:

```
docs/backlog.md:100:| 72 | ✅ (was 🟠) … the docstring at `discover_ratchets` documented discovery …
docs/backlog.md:101:| 73 | ✅ (was 🟢) … `grep -rn discover_ratchets …` returned exactly two hits …
F8 grep rc=0        (rc=0 means it FOUND matches — F8 expected none)
```

**T10 Step 3 is red at the end of the plan as written.** An implementer who "fixes" it by stripping
the token silently discards the measurement T9 Step 0 orders them to keep — and a closed row can then
no longer name what was deleted.

Note the shape: T8 Step 2's own ⛔ says F8 *"has now been wrong in **four consecutive versions**"*,
one of which was *"unsatisfiable via `docs/`"* because a historical record legitimately contains the
token. **v4 reintroduced exactly that failure through a narrower door.** Fifth version, same class,
and the new path is what caused it. Spec §9's ⛔ box records the identical lesson.

**OBSERVATION:** apply T8 and T9, then run T8 Step 2's grep. Any hit fails. Measured: two.

**Fix:** either drop `docs/backlog.md` from F8's paths and say why in one line (historical rows name
deleted symbols on purpose — that is what a closed row is for), or scope it, e.g.
`--exclude-dir` plus a `grep -v '^docs/backlog.md:.*✅'`. The first is honest and cheaper.

---

### H2 — F8 cannot fail for 7 of the 11 sites T8 exists to correct, and the spec calls it the completeness mechanism

`plan:770-785`; spec `§7` and `§9`

Spec §7 says *"The table is the list; **F8's grep is the mechanism that proves the list complete**."*
F8 greps for **one** token. Spec §7 itself records that the site list was derived by sweeping **six**
claim-shapes (`discover_ratchets`, `check-*.py`, *"two independent sources"*, *"two ways"*,
*"the population is the FILESYSTEM"*, `RATCHET_DOCSTRING_RE`).

Measured on today's tree — `grep -c discover_ratchets` per T8/T9 file:

| Site | hits |
|---|---|
| `scripts/page_markup.py` | 1 |
| `docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md` | 1 |
| `docs/backlog.md` | 1 |
| `docs/process-checklists.md` (3 spots) | **0** |
| `docs/dev-process.md` (the process spine) | **0** |
| `docs/roadmap-to-launch.md` (3 spots) | **0** |
| `scripts/check-test-counts.py` | **0** |
| `scripts/check-review-rounds.py` | **0** |
| `scripts/explainer-serve.py` | **0** |
| `.github/workflows/ci.yml` (2 spots) | **0** |

The false sentences in those seven files use other words. Quoted:

- `docs/dev-process.md:145` — *"the population is the FILESYSTEM; CI-step discovery saw 14 of 24 …
  (`--self-test`: 21 cases)"* — the claim §1 hunts, in the spine, plus a count that moves to 35.
- `.github/workflows/ci.yml:213` — *"its population is glob("check-\*.py")"*.
- `scripts/check-review-rounds.py:46-48` — *"discovers ratchets two ways … **Both are now true.**"*
- `scripts/check-test-counts.py:32` — *"from two independent sources"*.
- `scripts/explainer-serve.py:70` — *"discovers by globbing `scripts/check-\*.py`"*.
- `docs/process-checklists.md:288,295` — *"two independent sources"*, twice.
- `docs/roadmap-to-launch.md:1693` — *"the population at `:395` is `glob("check-\*.py")`"*.

So an implementer can leave **the process spine and CI's own comments asserting the deleted
mechanism** and F8 still passes. This is the *"green check over the wrong subject"* shape: v4's fix
corrected the **paths** dimension and left the **claim-shape** dimension, which is the same
instance-not-class move T8 Step 2 accuses the previous four versions of.

**OBSERVATION:** revert any one of the seven files above to its current text after applying T8, then
run F8. If F8 still returns nothing, it does not guard that site. It does not.

**Fix:** grep the alternation §7 already derived, e.g.
`grep -rnE 'discover_ratchets|RATCHET_DOCSTRING_RE|glob\("check-\*\.py"\)|two independent sources'`
over the same paths, and run it before writing it down — which is the practice spec §12 says the
durable fix is.

---

## MEDIUM

### M1 — T6 makes `check-selftest-counts.py`'s own population count false, and it is not in T8's site list

`plan:621-629`; `scripts/check-selftest-counts.py:74-76` and `:33-34`

T6 adds `check-ratchet-contract.py` to `POPULATION`, taking it from 9 members to 10. The file says,
in two places:

- `:74-76` — *"MEASURED 2026-09-01: of 38 scripts accepting `--self-test`, 8 declared a count
  canonically; **this file is the ninth, so the set below is 9.** Pinned, not derived"*
- `:33-34` — *"only **8** declared a count in the canonical form before this one existed … and this
  script is the ninth"*

After T6 the set is 10 — I ran it: `self-test counts: 10 script(s) declare a count, every one
verified by running it`. Nothing enforces the number (its own `--self-test` stayed 18/18), so it goes
stale silently. **T8's file list does not include `scripts/check-selftest-counts.py`**, and this is
the same class §7 exists for — a live script comment stating as fact a population this PR changes.
It is also the ninth instance of this slice's own recurring count error, arriving through the task
that edits the file.

**OBSERVATION:** after T6, `grep -n 'the ninth' scripts/check-selftest-counts.py` returns two lines
that are now false. **Fix:** add the file to T8's list; say "pinned, not derived" without a literal,
or write 10.

### M2 — `read_population` is the only function in the plan with no body, and the Self-Review says otherwise

`plan:499-502` vs `plan:960-966`

The Self-Review claims *"**Placeholder scan.** No TBD/TODO. **Every code step carries the actual
code.**"* and the *Type consistency* paragraph enumerates `population_paths`, `not_a_guard_reason`
and `discover_guards` — but not `read_population`. T4 gives it a signature and a one-line docstring
and stops. Four decisions are left to the implementer: how a repo-relative path from
`population_paths` is resolved back to a file (I used `scripts_dir.parent / rel`), whether every file
is parsed or only read, what the reason string contains, and how `main` consumes it (B1). Given that
this slice's history is that every under-specified joint became the next round's Blocking, this one
is worth writing out. **OBSERVATION:** the sentence at `:960-961` is false as long as `:499-502` has
no body.

### M3 — T7's fifth mutation is not minimal: it collapses three discriminators into one

`plan:686-691`

The anchor is correct — I verified all five anchors match **exactly once** in the code T1–T3 produce,
including the fifth's backslash continuation, character for character. The mutation passes. But it
replaces `isinstance(value.value, str) \ … and value.value.strip()` with `value.value is not None`,
which breaks the empty, whitespace and non-string discriminators at once. Measured, red cases per
mutation:

```
1 red  <- the population default narrows back to check-*.py
1 red  <- an assignment nested in a function counts as a declaration
1 red  <- a whitespace-only reason counts as a declaration
1 red  <- the detector stops compiling and only parses
3 red  <- a non-string value counts as a declaration
             NOT_A_GUARD: empty reason
             NOT_A_GUARD: whitespace-only reason
             NOT_A_GUARD: non-string value
```

It is accepted because `expect` cardinality is per-entry (`check-plan-code.py:770-772`), not over the
total. But it subsumes entry 3's named case, so the two entries no longer measure independent things,
and *"prefer the weakest mutation that still fails via the case it names"* argues for
`isinstance(value.value, str)` → `isinstance(value.value, (str, bool))`, which reddens only the
non-string case. **Not a gate failure** — filed so it is a decision rather than an accident.

---

## LOW

- **L1 — `plan:846`'s "Measured against T9's end state" is measured against the state *before* Step
  2b, which is part of T9.** I ran both: without the new `GROUPS` tuple, `coverage_errors: []`,
  `undescribed: [88]`; with it (T9's actual end state), `coverage_errors: []`, `undescribed: []`. The
  substance is right and the very next sentence orders the fix; the label is not.
- **L2 — `plan:818` cites `scripts/check-docs.py:456`; the quoted two lines are at `:452-453`.** The
  code is quoted correctly.
- **L3 — `plan:790` warns that `docs/plugins.md` is at its line budget. T8 does not edit
  `docs/plugins.md`.** It does edit `docs/dev-process.md`, which is at **218 / 220** (measured via
  `check-docs.py`'s own `check_line_budgets`). The warning names the file the task leaves alone and
  omits the one it rewrites.
- **L4 — `plan:777` says "⛔ DERIVE the path list from this task's own file list — do not restate
  it", and `plan:779-782` then restates it as eight literal paths.** It happens to agree with T8's
  list today; nothing keeps them agreeing, which is the property the ⛔ asks for.

---

## What I checked and found clean

Everything below was **executed**, not read.

**Baseline before touching anything:** `guards discovered (26)`, `ratchet contract OK`, rc 0,
`self-test: 21/21 passed`.

| Step | Plan's prediction | Measured |
|---|---|---|
| T1 S1b (probe) | `[FAIL]` printed **and exit 1** | `[FAIL] probe: got 1` / `21/22` / **rc=1** ✓ |
| T1 S3 | `NameError: name 'population_paths' is not defined`, *not* a `case` NameError | exactly that ✓ |
| T1 S5 | count rises by **2**, not 3 | 21 → **23** ✓ |
| T1 S7 | `guards discovered (26)`, rc 0, **still 26** | 26, rc 0 ✓ |
| T2 S2 | `NameError: name 'not_a_guard_reason' is not defined` | exactly that ✓ |
| T2 S4 | all **13** `NOT_A_GUARD` cases green | 23 → **36** ✓ |
| T3 S2 | FAIL, payload case returns `[]` | `[FAIL] discover_guards: a NON-check script … got []` ✓ |
| T3 S6 | **`guards discovered (45)`** + a wall of violations | 45, 14 violations, rc 1, `self-test 34/34` ✓ |
| T4 S1 | no `print(f"  FAIL` survives | `exit=1`, no matches ✓ |
| T4 S1 ⚠ | *"By the time this task runs it is ZERO"* | zero ✓ (the twice-mis-stated count is now right) |
| T4 S3 | `[]` on green; exactly the broken case's name when one is broken | `[]`, then `['NOT_A_GUARD: plain assignment']` ✓ |
| T5 S2 | **`guards discovered (28)`**, `ratchet contract OK`, rc 0 | 28, OK, rc 0 ✓ |
| T5 S3 | every `scripts/*.py` compiles | no output ✓ |
| T6 S3 | `check-selftest-counts.py` exits 0 | rc 0, contract listed ✓ |
| T7 S2b | harness self-test all pass | **158/158** ✓ |
| T7 S3 | control green, then **5 mutations, 0 survivors**, each red via the case it names | **167 mutations, 0 survivors, 8 files, exit 0**; per-file `check-ratchet-contract.py: 5 (declared 5)` ✓ |
| T9 S0 | `grep -c` on `docs/backlog.md` → **2** | 2 ✓ |
| T9 S5 | **88 total, 58 open, 30 closed** (from 87/59/28) | 87/59/28 → **88/58/30** through `gen-backlog-page.parse` ✓ |

**The brief's five scoped questions, answered:**

1. **`read_population` composition** — it composes fine with `population_paths` and
   `discover_guards(texts)`; the CANNOT-RUN branch **is** reachable by a case. What is broken is the
   wiring and the promised mutation → **B1, B2**.
2. **T7's fifth entry** — **CLEAN.** Its `before` string matches T2's code character for character,
   including the `\` continuation and the 16-space indent. All five anchors match `1x`; applied, it
   goes red via the case it names. (Minor: 3 red cases, **M3**.)
3. **`EXPECTED_MUTATIONS: 5`, sum `167`** — **CORRECT.** The sum oracle is at
   `check-plan-code.py:2021` and reads `162` today; 162 + 5 = 167. The inventory oracle's sorted
   position (`:1948-1956`, between `check-plan-code.py` and `check-selftest-counts.py`) is right.
   `--self-test` after Step 2: 158/158.
4. **F8 derived from T8's list** — the **paths** now cover every T8 site plus `docs/backlog.md` and
   `.claude/`. The **pattern** does not → **H1, H2**.
5. **T9's `coverage_errors` statement** — **ACCURATE.** `coverage_errors` is at
   `gen-backlog-page.py:775`, its docstring at `:778` says verbatim *"⚠ NO LONGER REPORTS MISSING
   ITEMS — see `undescribed`"*, only `extra`/`dupes` still refuse, and prose describing a closed item
   still refuses — so deleting both tuples **is** still required. `d39fa658` is confirmed an ancestor
   of HEAD (`git merge-base --is-ancestor` → yes), and `.claude/hooks/regen-backlog-page.sh:45` does
   print *"If this is a coverage refusal, add the item to GROUPS"* as the plan says. Recomputed
   `undescribed` for the end state: `[]` (see **L1** for the label).

**Falsifiers F1–F7, F9 — all pass**, run against a temp copy per §9:

```
F1 gen-m4-manifest.py + verify-exclusion-reasons.py present, build-m4-schema.py absent  ✓
F2 count is exactly 28                                                                  ✓
F3 zz-probe present-in-list ✓   F3 exit-1 ✓
F4 NOT_A_GUARD = "a probe" -> exit 0, zz-probe absent                                   ✓
F5 "" / "   " / True / nested-in-a-function  -> file stays IN (4/4)                      ✓
F6 docstring that DOCUMENTS the rule stays IN ✓   docstring that DEMONSTRATES it stays IN ✓
F6b old `NOT-A-GUARD:` text marker stays IN                                             ✓
F7 check-ratchet-contract.py is in its own discovered population                        ✓
F9 BASELINE still 0 (`:53`) and the run is green                                        ✓
```

**Other gates, after the full build:** `check-docs.py` rc 0 (`docs/dev-process.md 218/220 ok`,
`docs/plugins.md 259/260 ok`), `check-anchors.py` rc 0, `check-selftest-counts.py` rc 0,
`check-review-rounds.py` rc 0. I also ran the ten guards T10 Step 4 does **not** list —
`check-roadmap-consistency`, `check-gate-falsifiability`, `check-explainer-delivery`,
`check-guard-coverage`, `check-producer-enumeration`, `check-vocabulary-collisions`,
`check-test-counts`, `check-arch-findings`, `check-plan-progress`, `check-plan-task-order` — all
green except two that are **artefacts of my `.git`-less copy** (verified by running them on an
unmodified `.git`-less copy of `master`, where they are equally red): `check-dashboard-entry` (rc 2)
and `check-plan-task-order` (rc 1). Neither is caused by the plan.

**T5's declarations orphan no mutation anchor.** `grep -l '__future__' scripts/mutations/*.json`
returns nothing, so inserting the assignment after that line cannot break an anchor — and the
167/0 run confirms it empirically for all eight manifested files.

**Things I looked at specifically and did not find a problem with:** the AST rule's treatment of
implicit string concatenation (`("a gen" "erator")` parses to one `ast.Constant` — correct);
`AnnAssign`/`Final` handling; the `compile()` clause actually discriminating the `__future__` case;
`GUARD_PATH_RE` widening to `scripts/[\w.-]+\.py`; the `[FAIL] ` / `: got ` contract against
`check-plan-code.py:723`; the five ordering constraints in the Self-Review (all real, all necessary —
I hit T2→T7 and T3→T7 concretely); and T6's two-edits-one-commit coupling.

---

## Gaps in my coverage

- **No git.** The temp tree has no `.git`, so `check-dashboard-entry.py` (T9 Step 4) and the commit
  steps were **not exercised**. T9 Step 4's entry text is unreviewed; treat the dashboard-entry gate
  as **NOT RUN by me**.
- **T8's rewrites are mine, not the plan's.** The plan gives two sentence *shapes*, not text, so my
  eleven rewrites are one plausible instance. H1 and H2 do not depend on my wording — H2 is a
  property of the grep versus the files' existing text, and H1 reproduces for any #73 body that keeps
  the measurement the plan orders kept.
- **I resolved B1 by choosing reading A** for the end-to-end build (`main` wired to
  `read_population`). The 28 / 35 / 167 results hold under reading B too — the difference is only
  which of the two cannot-run mechanisms is live.
- **`--mutate .` ran once.** 167/0 is a single observation, not a repeated one. The control ran
  before and after per `mutate_delivered`, so it is not a red-control artefact.
- **I did not run CI** (`tsc --noEmit`, the unit suite, `service_role` confinement) or any schema
  gate. The change touches no TypeScript and no SQL, so I judge the risk low — but I did not measure
  it, and *"low risk"* is a judgement, not a result.
- **Codex's half is independent.** Where we disagree, adjudicate by reading the code, not by counting
  votes — this slice's own §12 records the halves splitting three times with the finding-half right.

---

**VERDICT: NOT CONVERGED**

B1 and B2 are one decision: *which mechanism owns the CANNOT-RUN exit, and what is its mutation
count.* H1 and H2 are one decision: *what F8 greps for, and whether `docs/backlog.md` belongs in its
paths.* Both are small edits to the plan. Nothing here challenges the design, and the plan is now
close — everything except the cannot-run joint and F8 was measured working end to end.

# Post-Plan Gate — round 1, Claude half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` at HEAD `3fd19b16`,
implementing `docs/superpowers/specs/2026-09-02-guard-inventory-population-design.md` **v4**.

**Question asked:** would an engineer following this plan literally, with no other context, produce
working code? **Not** whether the design is right — three dual rounds settled that and it is not
re-litigated here.

**Method — the plan was EXECUTED, not read.** A copy of `scripts/`, `.github/`, `.claude/` and
`docs/` at HEAD was made under `/Users/kujinlee/.claude-tmp/plangate/`. T1, T2, T3, T4, T5, T6 and T7
were applied to it as written, and the resulting tree was run: the contract's own suite, the whole
inventory, `scripts/check-plan-code.py --mutate .` (10 min, 166 mutations), `check-selftest-counts.py`,
and T10's falsifier recipe verbatim. Every claim below that says MEASURED was produced by that tree.
Nothing in the live repo was touched; no `git` command was run beyond `git status`/`git log`.

**Counts: 4 Blocking, 2 High, 4 Medium, 2 Low.**

---

## BLOCKING

### B1 — T7's first mutation SURVIVES. T1 does not make the mutated line reachable, and that is the one thing T1 exists to do

`plan:516-518` (the mutation) · `plan:110-119` (T1 Step 3) · `plan:322` (T3 Step 5) ·
`plan:58-61` and `plan:725` (the claim) · `scripts/check-plan-code.py:376` (what a suite run is)

**What breaks.** T7 Step 3 is stated as *"control green first, then 4 mutations, 0 survivors"*.
It is 3 survivors short of that — one mutation is never caught, `--mutate .` exits 1, and
`--mutate .` is what CI runs. The PR cannot go green.

**THE OBSERVATION.** With T1–T5 applied and T7's manifest + `EXPECTED_MUTATIONS` key in place
(and B4's oracles repaired so the control could run at all):

```
$ python3 scripts/check-plan-code.py --mutate .
  ✗ mutation SURVIVED — the population narrows back to check-*.py: the suite stayed green,
    so no case can fail for what it names
FAILED — delivered scripts mutated: 8 file(s), 166 mutation(s), 1 survivor(s)
```

Reproduced standalone as well — applying only that one edit and running the suite gives
`rc=0`, `red cases: []`.

**Why.** T1 extracts the glob, but its three cases call

```python
        got = population_paths(scripts)          # plan:91 — DEFAULT pattern
```

with the **default** `pattern="check-*.py"`, and T3 Step 5 widens the **call-site argument** in
`main()`:

```
In `main`, change `population_paths(ROOT / "scripts")` to `population_paths(ROOT / "scripts", "*.py")`.
```

So the token the mutation rewrites lives on a line inside `main()`. `run_suite`
(`check-plan-code.py:376`) runs `[sys.executable, name, "--self-test"]` and nothing else, and no
self-test case calls `main()`. The extraction bought coverage of `population_paths` **under its old
default** — coverage of the function, none of its use. That is verbatim the sentence the plan quotes
at `plan:60-61` from `check-ratchet-contract.py:163-171` as the reason for doing the extraction.

**The plan already contains the fix and then contradicts it.** `plan:71-72` says
*"`population_paths(scripts_dir, pattern: str = "check-*.py")` — **Task 3 changes the default
pattern**"*. Changing the **default** to `"*.py"`, having `main` call `population_paths(ROOT /
"scripts")` with no second argument, and rewriting T1's three cases to expect `scripts/gen-b.py`
**in** the result puts the widened token on a line three cases drive. Mutating the default then goes
red via a named case. As written, T1's cases pin the default to `check-*.py`, which forecloses that
route.

---

### B2 — `case()` is called eight times and never defined; T4 never covers its output format

`plan:92-97` (T1) · `plan:188-189` (T2) · `plan:274-279` (T3) · `plan:359-368` (T4 Step 1)

**What breaks.** Two ways, in sequence.

1. **Immediately:** `NameError`. `grep -n "def case" scripts/check-ratchet-contract.py` returns
   nothing. The file's `self_test` prints inline at `:343`, `:348`, `:353`, `:358`, `:375`. Twenty
   other scripts in `scripts/` define a local `case()` helper, but with **two incompatible
   signatures** — `case(name, ok)` (`check-docs.py:544`, `check-guard-coverage.py:323`, …) and
   `case(name, got, want)` (`check-plan-code.py:960`, `gen-dashboard.py:1593`, …). The plan's eight
   call sites all use the 3-arg form, but the plan never says to write it, and the file being edited
   has neither.

2. **Then, silently:** T4 Step 1 says *"Change the five failure prints"* — the ones that already
   exist. The `case()` helper an implementer must invent to satisfy T1–T3 is not one of them, and
   **all four of T7's `expect` names name `case()`-driven cases**. If `case()` is written in the
   prevailing style of the file it is being appended to, the mutation goes red and the harness
   cannot see it.

**THE OBSERVATION.** `case()` written as `print(f"  FAIL {name}\n       expected {want}\n
got      {got}")` — the exact format of the five lines it sits beside — then applying T7's second
mutation:

```
(A) case() in prevailing style -> rc=1  parsed red cases=[]
```

Red, and zero cases recoverable. `check-plan-code.py:723-724` filters on
`l.strip().startswith("[FAIL] ")`, so every `expect` resolves to 0 matches and
`check-plan-code.py:778-786` fails the mutation as *"it was caught by something else"* — the
failure mode T4's own Why paragraph (`plan:350-354`) exists to prevent, one layer out from where it
looked.

**Fix:** give T4 (or T1) the literal `case()` body, and state that it must emit
`[FAIL] {name}: got {got}` — the `: got ` separator is load-bearing for
`check-plan-code.py:723`'s `rsplit(": got ", 1)`.

---

### B3 — T7's `expect` for mutation 1 is not the string T3's own code prints

`plan:518` (the expect) · `plan:274-275` (the loop that prints the name) ·
`scripts/check-plan-code.py:757` (the matcher)

**What breaks.** Even once B1 is repaired so something goes red, this mutation is rejected.

**THE OBSERVATION.** T3 Step 1 prints the case name as

```python
        case(f"discover_guards: {label}", discover_guards(texts), expected)
```

so the emitted name is `discover_guards: a NON-check script with no declaration is IN — the payload
case`. T7 expects `a NON-check script with no declaration is IN — the payload case`. Measured
against a red run: `expect '…the payload case' -> 0 exact match(es)`.

`check-plan-code.py:757` is `[f for f in fails if w == f]` — **equality**, deliberately so; the
comment at `:748-753` records round 6 replacing substring matching because *"an `expect` naming a
completely unrelated case, or a mere fragment of a name, still certified the mutation"*. A prefix
short by `discover_guards: ` is exactly that fragment.

T2's three `expect` strings are correct — `f"NOT_A_GUARD: {label}"` (`plan:189`) does carry its
prefix into `plan:524`, `:530`, `:536`. Only the T3-sourced one is short.

---

### B4 — T7 leaves two hardcoded oracles in `check-plan-code.py` red, so its own control refuses to run

`plan:541-546` (T7 Step 2) · `scripts/check-plan-code.py:1949-1956` · `scripts/check-plan-code.py:2022`

**What breaks.** T7 Step 2 says only *"Add the `EXPECTED_MUTATIONS` key … ⚠ The sum rises by 4."*
`check-plan-code.py` asserts its own manifest inventory **twice**, by hand:

```python
    case("the declared counts name every manifest that ships",
         sorted(EXPECTED_MUTATIONS), ["scripts/check-dashboard-entry.py",
                                      "scripts/check-plan-code.py",
                                      …                                       # :1949-1956
    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 162)   # :2022
```

**THE OBSERVATION.** With T7 Step 2 applied exactly as written and nothing else:

```
$ python3 scripts/check-plan-code.py --self-test
[FAIL] the declared counts name every manifest that ships: got [… 8 files …] want [… 7 files …]
[FAIL] the declared counts are the real ones: got 166 want 162
156/158 passed

$ python3 scripts/check-plan-code.py --mutate .
  ✗ CANNOT RUN — control run of scripts/check-plan-code.py exited 1 BEFORE any mutation was
    applied. Every verdict below would be an artefact. Treat this as NOT CHECKED.
FAILED — delivered scripts mutated: 8 file(s), 0 mutation(s), 0 survivor(s)
```

Zero mutations run. T7 Step 3's stated expectation never happens, and the two ⚠ notes under it
(*"if any reports matched 0 red case(s) …"*, *"if any reports mutation SURVIVED …"*) do not fire
either, because no mutation is reached.

Two extra traps an implementer walks into here: the new entry must go in **sorted** position
(between `check-plan-code.py` and `check-selftest-counts.py` — I put it first, and the case stayed
red), and `162` must become `166`, not "rise by 4" in prose.

**This is also the missing ordering constraint** (see M-ORD below): it is the same shape as T6's
*"both steps in the same commit"*, and the Self-Review's *Known ordering constraints* does not have
it.

---

## HIGH

### H1 — `import tempfile` is never added, so T1 Step 4 cannot pass and T1 Step 2's expected error is wrong

`plan:86` · `scripts/check-ratchet-contract.py:29-33`

The file imports `ast`, `re`, `sys`, `dataclass`, `Path` — no `tempfile`. T1 Step 1's block opens
with `with tempfile.TemporaryDirectory() as d:`. T1 Step 3 ("write the minimal implementation")
adds only `population_paths`.

**THE OBSERVATION**, running T1 Step 2 with T1 Step 1 applied verbatim:

```
  File ".../scripts/check-ratchet-contract.py", line 379, in self_test
    with tempfile.TemporaryDirectory() as d:
NameError: name 'tempfile' is not defined. Did you mean: 'compile'?
```

T1 Step 2 states the expected failure as `NameError: name 'population_paths' is not defined`. It is
not — `tempfile` is evaluated first. Both are `NameError`, so an implementer treating the red as
"the expected red" moves to Step 3, adds only `population_paths`, and Step 4 fails again.

### H2 — T4's "five failure prints" is three by the time T4 runs

`plan:357-359` · `scripts/check-ratchet-contract.py:343,348,353,358,375`

T4 names `:343`, `:348`, `:353`, `:358`, `:375`. But T4 runs after T3, and T3 deletes
`DISCOVERY_CASES` (which owns `:348`) and replaces the `POPULATION_CASES` loop with `case(...)`
(which owns `:358`). Three inline prints remain. An implementer looking for five finds three and
has no instruction covering the gap — which is where B2's second half lands.

---

## MEDIUM

### M-ORD — the third ordering constraint, and it is a same-commit coupling

`plan:725-728`

The Self-Review lists T1→T7, T4→T7, T3→T5, and T6's two-edits-one-commit. Two observations:

- **T1→T7's stated reason is false as applied** (B1). The constraint is harmless but the sentence
  under it — *"a mutation on an unreachable line survives"* — describes what happens **with** T1
  done, not without it.
- **T4→T7's stated reason is TRUE**, and I confirmed it by executing the adverse case (B2's
  observation): without the `[FAIL] ` prefix an `expect` resolves to 0 red cases.
- **Missing:** T7's `EXPECTED_MUTATIONS` key and `check-plan-code.py`'s two self-test oracles
  (`:1949-1956`, `:2022`) must land in the **same commit**, for exactly T6's reason — one without
  the other leaves the harness's control red and every downstream verdict unreachable (B4).

T6-after-T2/T3 (the `# N cases` declaration moves when cases are added) holds by task numbering, so
it is unstated rather than violated.

### M2 — T1's Interfaces contradicts T3 Step 5 and T7 about where the widening lives

`plan:71-72` vs `plan:322` and `plan:516-517`. Recorded separately from B1 because repairing B1
means picking one of the two, and the plan currently asserts both.

### M3 — T3 Step 3 re-declares `GUARD_PATH_RE`, which already exists

`plan:290` · `scripts/check-ratchet-contract.py:108`

Spec §5 item 2 frames this as a modification (`GUARD_PATH_RE` → `scripts/[\w.-]+\.py`). T3's code
block presents it as a fresh module-level statement above `discover_guards`. Applied literally there
are two bindings; the later wins, so behaviour is correct — but the 10-line comment at `:109-117`
(about `NO_CALLER_RE`'s `[ \t]*` and the mutation that survived) is left attached to a dead
definition, and that comment is itself a review artefact worth not orphaning.

### M4 — T3 Step 5 does not mention the `DISCOVERY_CASES` **loop** or the `total` expression

`plan:320-324` · `scripts/check-ratchet-contract.py:345-349` and `:378-379`

*"Delete `discover_ratchets` (`:67`), `RATCHET_DOCSTRING_RE` (`:55`), `CI_RATCHET_STEP_RE`, and
their `DISCOVERY_CASES`."* The loop at `:345-349` and `len(DISCOVERY_CASES)` inside the `total`
computation at `:378-379` are two further references; leaving either is a `NameError`. Inferable,
but every other deletion in this step is named by line.

### M5 — nothing files the `NO-CALLER:` backlog row the spec twice promises

Spec §3.3 (*"belongs in the backlog, not smuggled into this PR"*), §6 second bullet, and the plan's
own Global Constraints (`plan:33-34`) all defer the `NO_CALLER_RE` text weakness **to the backlog**.
T9 closes rows #72 and #73 and adds no row. Spec §6's last bullet (`gen-m4-manifest.py`'s
`--self-test` is executed by nothing) is likewise "recorded" nowhere in the plan. Both are one-line
additions to T9, or an explicit statement that filing is the user's step.

---

## LOW

### L1 — T10's copy command swallows its own failure

`plan:671`: `cp -R scripts .github .claude "$T"/ 2>/dev/null`. Two lines above, the plan warns that
the copy *must* include `ci.yml` and the caller sources *"or F3 passes for the wrong reason"*. The
`2>/dev/null` is what would hide a partial copy. `set -e` plus a post-copy existence assertion on
`$T/.github/workflows/ci.yml` costs one line. (The recipe otherwise works — see below.)

### L2 — T6 Step 1 is ambiguous about replacing vs adding the usage line

`plan:473-478` · `scripts/check-ratchet-contract.py:25`. The docstring already carries
`python3 scripts/check-ratchet-contract.py --self-test`. T6 shows a line **with** a count without
saying whether it replaces that one. Both work (`declares` at `check-selftest-counts.py:148-158`
asks `count_drift` on the whole docstring), but one leaves a duplicate.

---

## What I checked and found CLEAN

Every item here was executed, not read.

**The detector — all 13 cases give the plan's stated verdict.** Run standalone against the plan's
`not_a_guard_reason` body, and again inside the assembled file: `13 mismatches: 0`. Including the
three the brief singled out — `implicit concatenation` (`("a gen" "erator")` is folded into one
`ast.Constant` at parse time → `'a generator'`, EXCLUDED), `before __future__`
(`compile()` raises `SyntaxError`, `ast.parse` does not → IN), `unparseable file` → IN. Also
`AnnAssign`, `Final[str]`, `""`, `"   "`, `True`, comment, nested, docstring-documents,
docstring-demonstrates.

**The end state is exactly 28.** After T1–T5 on the temp tree:
`guards discovered (28)` … `ratchet contract OK`, exit 0. The set is the 26 `check-*.py` plus
`gen-m4-manifest.py` and `verify-exclusion-reasons.py`; `build-m4-schema.py` is absent (spec §4.1
upheld). `BASELINE` untouched at `0`, and the run is green — F1, F2, F9 all hold.

**T3's intermediate 45 is exact.** `guards discovered (45)`, exit 1, `14 violation(s), baseline 0`.
The 14 fall across exactly **10** scripts — `brief-compose`, `codex-frontier-model`, `codex-review`,
`m4_base_db`, `m4_catalog`, `prior-art`, `regen-skills-doc`, `session-skill-report`,
`skill-usage-audit`, `subject_status` — **all in the OUT-17**. Spec §4's *"zero code repairs"* and
*"all 10 are OUT"* both hold; the plan's STOP-and-report condition does not fire.

**T5's 17 files are right, and all carry a `from __future__ import`.** The list matches spec §4.4's
5 generators + 5 libraries + 4 tools + 2 reporters + `build-m4-schema` = 17. Line numbers measured:
`gen-backlog-page:52`, `gen-dashboard:3`, `gen-goals-page:45`, `brief-compose:39`,
`regen-skills-doc:27`, `page_markup:53`, `page_chrome:36`, `subject_status:38`, `m4_catalog:76`,
`m4_base_db:32`, `explainer-serve:75`, `prior-art:30`, `codex-review:49`,
`codex-frontier-model:35`, `session-skill-report:4`, `skill-usage-audit:37`, `build-m4-schema:36`.
Spec §3.4a's *"all 17"* claim is confirmed against the tree, not recalled.

**Inserting the declarations breaks nothing.** T5 Step 3's `py_compile` loop over all 45 files:
no output. Fourteen self-tests run individually, all rc=0 — `gen-dashboard 307/307`,
`page_markup 74/74`, `page_chrome 50/50`, `check-dashboard-entry 13/13`, `check-plan-code 158/158`,
`check-theme-token-coverage 12/12`, `check-selftest-counts 18/18`, `check-docs 13/13`,
`check-anchors 15/15`, `check-review-rounds 22/22`, `gen-backlog-page 75/75`,
`explainer-serve 81/81`, `brief-compose 40/40`, `gen-goals-page 15/15`.

**No existing mutation anchor is orphaned by T5.** The full `--mutate .` run applied **166**
mutations across 8 files with **zero** `anchor NOT FOUND` and zero `anchor matches N times`. 165
caught; the single survivor is B1's. Spec §10's ✅ measurement holds under execution.

**T7's other three mutations are sound.** Each anchor occurs **exactly once** in the delivered text
after T1–T4 (checked by `src.count(find)`, the same predicate `run_mutations` uses at
`check-plan-code.py:690`), each goes red, and each `expect` resolves to **exactly one** case:
`NOT_A_GUARD: nested in a function`, `NOT_A_GUARD: whitespace-only reason`,
`NOT_A_GUARD: before __future__`. Note mutation 3 also reddens `NOT_A_GUARD: empty reason` — that is
permitted (`check-plan-code.py:755-760` requires each `expect` to match one case, not that only one
case is red), so it is not a finding.

**The plan's verbatim `discover_guards` docstring does not self-exclude the contract.** That
docstring spells out ``NOT_A_GUARD = "<reason>"``. Applied literally: `guards discovered (28)`,
`check-ratchet-contract.py` present, exit 0. The §3.1 Blocking that killed v1 and v2 does not
return under the AST rule.

**T4's premises are exact.** `scripts/check-ratchet-contract.py` contains **0** occurrences of
`[FAIL] `. The seven manifested scripts carry 1, 2, 1, 3, 18, 2, 2 — the plan says *"1–18"*.
`check-plan-code.py:723-724` is character-for-character what the plan quotes.

**T6's premises are exact, and T6 works.** `.github/workflows/ci.yml:143-144` is
`- name: Ratchet contract` / `run: python3 scripts/check-ratchet-contract.py` (bare, no
`--self-test`). `ci.yml:177-178` wires `check-selftest-counts.py`.
`declaring_scripts` (`check-selftest-counts.py:161-166`) globs `scripts/*.py`. Applying both T6
edits: `self-test counts: 10 script(s) declare a count, every one verified by running it`, rc=0.

**T10's recipe gives `main()` everything it needs.** Run verbatim from the post-T5 tree:
`F3 present-in-list ✓` (probe listed, 29 discovered), `F3 exit-1 ✓` (2 violations: R1 + R3 — so it
fails for the *intended* reason, not the missing-`ci.yml` reason `main:389-392` also returns 1 for),
`F4 rc=0` and `F4 absent ✓`, `F6b stays IN ✓` (a docstring carrying the old `NOT-A-GUARD:` text
marker does not exclude). `ROOT = Path(__file__).resolve().parent.parent` resolves to `$T`, and
`.github/workflows/ci.yml` + `scripts/*.sh` + `.claude/hooks/*` + `scripts/*.py` are all present.

**T9's counts are exact.** Through `gen-backlog-page.parse` — the owning parser, as the plan
insists — `TOTAL 87  OPEN 59  CLOSED 28` today, so 87 / **57** / 30 after closing two. The plan's
`(was 59/28)` is right.

**T8's site list is real.** Every cited line was opened and contains the claimed false statement:
`check-test-counts.py:31-33` (*"from two independent sources"*), `check-review-rounds.py:46-48`
(*"discovers ratchets two ways … Both are now true."*), `page_markup.py:42-45` (names
`discover_ratchets:67`), `explainer-serve.py:68-73`, `ci.yml:212-217` and `:220-223`,
`dev-process.md:145` (which does also carry `--self-test: 21 cases`, as T8 Step 1's ⚠ warns).

**F8 is satisfiable after T8.** Run against the post-T3 tree, the only surviving
`discover_ratchets` hit is `scripts/page_markup.py:45` — and `page_markup.py:42-45` **is** in T8's
site list, so rewriting it clears the grep. (`docs/backlog.md:100` names `RATCHET_DOCSTRING_RE`, but
F8 does not grep that file and T9 edits the row anyway.)

**Spec coverage.** I walked §3.2, §3.3, §3.4, §3.4a, §3.5, §4, §4.1–§4.4, §5 items 1–10, §6, §7,
§8, §9 F1–F9, §10, §11 against the task list. Every §5 item has a task. The only unassigned
obligations are the two "record it in the backlog" bullets in M5.

---

## Gaps in my coverage — say these out loud

1. **`case()` and `import tempfile` are mine, not the plan's.** Every measurement downstream of T1
   is conditional on an implementation the plan does not contain. I chose the variant most
   favourable to the plan (3-arg, `[FAIL] `-prefixed) for the main run, and separately executed the
   adverse variant to produce B2's observation. A different implementer choice changes B2's
   severity, not B1's or B3's.
2. **I did not perform T8 or T9.** So `check-docs.py`, `check-anchors.py`,
   `check-dashboard-entry.py` and `check-review-rounds.py` were run only as `--self-test`, never as
   real runs against a post-T8/T9 tree. T10 Step 4's full sweep is **NOT CHECKED** by me.
3. **One `--mutate .` run only** (~10 minutes). I did not re-run to rule out flakiness, and I
   repaired B4's oracles by hand to get the control green — a real implementation might repair them
   differently.
4. **No git, no TypeScript, no jest, no schema gate, no Postgres, no browser.** Per the brief.
5. **I did not re-derive the classification.** Whether each of the 17 reasons is the *best* wording,
   and whether `build-m4-schema.py` truly belongs OUT, are settled spec questions I took as given.
6. **Commit mechanics unexamined beyond reading** — `.git/COMMIT_MSG_T*`, `git add -A` scope, the
   PR/merge-tick sequence in T9/T10.
7. **Temp tree is HEAD `3fd19b16`.** If the coordinator has since changed `scripts/`, line numbers
   and the 166/162 arithmetic move.

---

**VERDICT: NOT CONVERGED** — executing the plan produces a surviving mutation (B1), a `NameError`
(H1), an undefined `case()` whose output format silently disarms all four `expect` entries (B2), one
`expect` string that cannot match (B3), and a mutation control that refuses to run at all (B4); the
design, the 28, the detector and the falsifiers are all sound.

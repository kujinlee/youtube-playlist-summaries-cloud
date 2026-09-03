# The guard inventory declares its population — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Backlog:** #72 (and #73, which closes with it).
**Status: v3 — rounds 1 and 2 folded in, BOTH halves each round.** The shape the user approved
(declare-out) is unchanged. **The declaration's ENCODING has changed twice**, and §3 explains why the
second change is structural rather than another attempt at the same idea.

| Round | Codex (`gpt-5.5`) | Claude |
|---|---|---|
| 1 | 1 Blocking, 2 High, 2 Medium | 1 Blocking, 5 High, 5 Medium, 4 Low |
| 2 *(scoped to round 1's own fixes)* | 1 Blocking, 2 High, 1 Medium, 1 Low | **2 Blocking**, 4 High, 4 Medium, Low |

Reviews: `docs/reviews/spec-guard-inventory-population-r{1,2}-{codex,claude}.md`.
**Both round-2 Blockings are defects in round 1's own fixes**, which is what the scoping was for.

> ⛔ **THE COUNT IS 28, NOT 29 — and v2's "correction" to 29 was the author's error.**
> Round 1 (Codex) said `build-m4-schema.py` was misclassified; v2 moved it IN and wrote §12 claiming
> *"the finding-half was right"*, citing a memory heuristic. Round 2 (Claude) showed the criterion v2
> wrote **to settle exactly this** derives it **OUT**. See §4.1. v1's number was right; v2's
> correction was not. Recorded rather than quietly reverted, because adopting a reviewer's
> reclassification and then writing a rule that contradicts it is the failure this spec is about.

---

## §1 — The defect, as measured against `77c5676d`

`scripts/check-ratchet-contract.py` polices every guard: each needs a `--self-test` (R1), no `except`
returning `0` (R2), and a caller or a written `NO-CALLER:` reason (R3). Its value depends entirely on
**which files it looks at**. It looks at **26 of 45**, and says otherwise in two places:

| Where | The claim | What the code does |
|---|---|---|
| `discover_ratchets:67` (dead) | discovery from *"TWO independent sources"* | source 2 is unreachable — no caller offers it a non-`check-*` file |
| **`discover_guards:132` (live)** | **"EVERY guard on disk. The population is the FILESYSTEM."** | it is only ever handed a name-filtered list |

⚠ **One narrowing site:** `main:395` — `glob("check-*.py")` — builds `texts`. `evaluate:174` does not
glob; it forwards. `GUARD_PATH_RE` (`:108`) then filters an already-filtered list, which is why the
narrowing is invisible when reading `discover_guards` alone.

**Reproduced by all four review halves:** 45 / 26 / 19; `guards discovered (26)`, exit 0;
`--self-test` 21/21.

### 1.1 — Why backlog #72's own proposal fails

*"Let `RATCHET_DOCSTRING_RE` do the selecting"* enrolls 6 files, of which **1** is a genuine
declaration. `explainer-serve.py`, `page_markup.py` and `prior-art.py` match because they **deny**
being ratchets; `gen-backlog-page.py` and `subject_status.py` by citation. `page_markup.py`'s
docstring predicted this on 2026-08-30, and the sentence that predicted it is the sentence that would
enroll the file. Same class as `**Decide:**` (backlog #81), `NO-ENTRY:`, `REVIEW GAP:`.

### 1.2 — Why the fact was known and did not travel

`scripts/explainer-serve.py:68-73` already recorded the mechanism. **A true statement in a
neighbour's comment did not correct the false one at the source.** §7 exists because of this.

---

## §2 — The decision: declare-out

**The population is every `scripts/*.py`. A file leaves only by saying so in writing.**

- **Honesty-only (rejected).** Correct the docstrings, change no behaviour. Honest, but retires the
  ambition rather than meeting it.
- **Declare-in via a central roster (rejected).** Evadable by omission: a guard nobody adds is a guard
  nobody polices, and noticing what nobody is looking at is the inventory's job.

> ⛔ **v1 attached a false cause to that argument; deleted.** v1 said non-registration is *"precisely
> how `gen-m4-manifest.py` came to be missed"* — refuted by §1.1's own table, where it is the one
> **genuine declaration**. It registered; the *population* never offered it. v1 also cited
> `discover_ratchets:70`'s objection to *"a registry **list**"* against a per-file marker, inverting a
> docstring that offers per-file self-declaration as the defence against rosters.

**Declare-out** is the only shape where **omission fails**: a script that declares nothing is IN and
stays red until someone decides.

---

## §3 — The declaration is an AST node, not text

```python
NOT_A_GUARD = "a page generator; its product is an artefact, not a verdict"
```

A **module-level assignment** to the name `NOT_A_GUARD` whose value is a non-empty string constant,
read via `ast`. Nothing else counts.

### 3.1 — Why text failed, twice, and why this is not a third attempt at the same thing

v1 used an unanchored docstring match. v2 anchored it flush-left. **Round 2 defeated both**, and the
executed counter-cases show why the whole approach is unsound:

| Docstring shape | v1 | v2 flush-left | Should be |
|---|---|---|---|
| genuine declaration | EXCLUDE | EXCLUDE | EXCLUDE |
| prose describing the rule, mid-sentence | EXCLUDE ❌ | in | in |
| **prose describing the rule, marker at line start** | EXCLUDE ❌ | **EXCLUDE ❌** | in |
| example indented under prose | EXCLUDE ❌ | in | in |
| **example that is the body's only content** | EXCLUDE ❌ | **EXCLUDE ❌** | in |
| **body uniformly indented, example inside it** | EXCLUDE ❌ | **EXCLUDE ❌** | in |

`ast.get_docstring(clean=True)` dedents by the **minimum** indent across body lines. So whether a
demonstration survives the anchor depends on an unrelated property of the *rest of the docstring*.
**After cleaning, a declaration and a demonstration of a declaration can be byte-identical.** No
text-position rule can separate them; a third regex would be the third wrong answer.

⚠ **v2's §3.1 measurement was itself the repo's corpus error** — it enumerated "indented example" from
**one instance** instead of from the rule, two paragraphs after §4.3 corrects exactly that. Third of
four instances in this slice (see §12).

⛔ **The consequence was not cosmetic.** With v2's grammar, documenting the rule in the contract's own
docstring — which v2 §5 *instructed* — produced:

```
v2 flush-left  flushleft_demo   run_exit=0  count=28  self_in_population=False   selftest 22/23
```

**The guard removed itself from its own population and printed `ratchet contract OK`.**

### 3.2 — The AST rule, measured across 8 cases

| Input | Result |
|---|---|
| `NOT_A_GUARD = "a page generator…"` at module level | **EXCLUDED** ✅ |
| docstring documenting the rule | IN ✅ |
| docstring showing an example, **any** indentation | IN ✅ |
| a comment `# NOT_A_GUARD = "sneaky"` | IN ✅ |
| assignment nested inside a function | IN ✅ |
| `NOT_A_GUARD = ""` (empty reason) | IN ✅ |
| `NOT_A_GUARD = True` (non-string) | IN ✅ |
| unparseable file | IN ✅ |

Prose cannot forge an AST node. Every failure mode fails **closed** — toward being policed.

The declaration is still a written, reviewable claim in the diff; it is now also greppable and
linter-visible, and it cannot be produced by describing it.

### 3.3 — `NO-CALLER:` keeps the text weakness, and that is a real defect in existing code

v2 proposed anchoring `NO_CALLER_RE` as a free class-fix. **That is retired**: anchoring does not work
(§3.1), and converting `NO-CALLER:` to an AST form is a separate change to a rule this spec does not
otherwise touch.

**Stated as a limit, not fixed here:** a docstring example showing `NO-CALLER: <reason>` opts a guard
out of R3 today. **Measured: zero of the 26 guards carry such a declaration and none has such an
example**, so nothing is broken now. It is a latent hole surfaced by this work and belongs in the
backlog, not smuggled into this PR.

### 3.4 — Unparseable files are IN, and say so properly

`check_caller` (`:148-151`) falls back to `doc = text` on `SyntaxError`, so a token in a comment
counts. `NOT_A_GUARD` detection does not inherit that: it needs a parse tree, and **no parse means
IN**. An unparseable file is exactly what an inventory must not lose.

⚠ Today an unparseable `scripts/*.py` ends the run with a **raw traceback** from
`fail_open_handlers:92`, where `docs/process-checklists.md` rule 1 requires *"exit non-zero and say
treat this as NOT RUN."* Fail-closed, so not a false green, but repaired here with a case. §5 item 9
and this section now specify **one** exit, not two.

### 3.5 — The self-inclusion check, and the wiring it depends on

A standing case asserts `scripts/check-ratchet-contract.py` is in its own discovered population.

⛔ **v2 called this "standing" and it was not.** Nothing executes this script's `--self-test`:
`.github/workflows/ci.yml:144` runs the bare script. The cited precedent
(`check-selftest-counts.py:20`, *"IT CHECKS ITSELF"*) works only because
`check-selftest-counts.run_self_test` (`:183-186`) spawns every `POPULATION` member with
`--self-test`, wired at `ci.yml:178`.

**So §5's `POPULATION` edit is a PREREQUISITE for this section, not test-infra polish.** Without it,
the case that catches §3.1's self-exclusion runs nowhere. Stated here so an implementer cannot defer
one and keep the other.

---

## §4 — The criterion, and the verdicts derived from it

**A script is a guard if it has a mode whose only product is a VERDICT about a subject other than
itself.** Assertions protecting a script's own output are **self-protection, not policing**.

The tempting *"exits non-zero on a defect"* is useless: nearly every script here is fail-closed. What
discriminates is the **product** — a guard's is a verdict, a generator's an artefact, a library's
functions, a tool's information for a human.

### IN (2), both already satisfying R1+R2+R3

| File | Derivation |
|---|---|
| `verify-exclusion-reasons.py` | the verdict is the whole product — it executes another file's written reasons |
| `gen-m4-manifest.py` | `--check` is a verdict-only mode: *"regenerate and FAIL if it differs"*. Subject: the committed manifest |

### 4.1 — `build-m4-schema.py` is OUT, and v2 had it wrong

Applying the criterion, quoted against the file:

- **No verdict-only mode.** Full flag set: `--out`, `--schema`, `--self-test`, `--quiet`
  (`:365-369`). **Zero `--check`.** Every non-self-test mode emits SQL (`:394-398`).
- **The assertion's subject is its own output.** `:245` — `errors += assert_end_state(sql)` where
  `sql = s01 + s03 + s04` is built two lines above.
- **"Can be reduced to its assertions" is a FUTURE state** (`:26-28`, *"⛔ EXPIRES when Tasks 1-2
  land"*). v2 cited it as evidence of what the file **is**.

**Count: 26 + 2 = 28.** ⚠ v2's §12 asserted the finding-half was right on a memory heuristic. The
heuristic is not a law, and here the derivation settles it the other way. **Adjudicate by deriving,
not by counting votes** — including when the vote agrees with a memory.

### 4.2 — `codex-review.py` stays OUT

Its exit codes report on **its own run**; its product is a review file. It *runs* a gate rather than
being one. Confirmed with the user 2026-09-02.

### 4.3 — Library modules are OUT rather than a rule change

`page_markup.py`, `page_chrome.py`, `subject_status.py`, `m4_catalog.py`, `m4_base_db.py` are imported,
never invoked. R3's `invocation_re` (`:121-129`) matches an invocation, not an import — **R3 behaving
correctly**. A library is not a guard. Backlog #72 warns against the mirror error; this spec decides
guards and subjects are **not** the same population.

⚠ Measured importers, self excluded: `page_markup` 4, `m4_catalog` 5, `subject_status` **3**,
`m4_base_db` **3**. v1 said "4–5 each" — wrong for half the set.

### 4.4 — How the OUT set was checked, and how v2's sweep was worthless

**OUT (17):** the five page generators, five library modules, four tools, two reporters, plus
`build-m4-schema.py`.

⛔ **v2 claimed "no fourth surprise" from a sweep for verdict-mode flags
(`--check`/`--verify`/`--assert`/`--audit`). That sweep returns exactly one file** — and **two of the
three files in v2's own IN table had no such flag**. A screen that finds 1 of the 3 things it is
screening for cannot support a completeness claim. Fourth instance of the corpus error, committed two
paragraphs after §4.3 corrects it.

**Replaced by:** the criterion applied by hand to all 19, independently by the author and by round 2's
Claude half, agreeing on 2 IN / 17 OUT.

⚠ **Seven OUT files satisfy R3 today** — `gen-backlog-page`, `gen-dashboard`, `gen-goals-page`,
`regen-skills-doc`, `page_markup`, `page_chrome`, `explainer-serve` (plus `build-m4-schema`, now also
OUT: eight). v1 said "three", enumerated from *"CI invokes their `--self-test`"* — one reason, not the
rule. **They are still declared out: satisfying a rule is not membership of a population**, and that
distinction is this spec's subject.

**Net: 17 declarations, 2 files join, zero code repairs, `BASELINE` stays 0.** Of the 10 non-`check-*`
scripts failing R1/R2/R3 today, **all 10 are OUT** — reproduced by both round-1 halves.

---

## §5 — The change surface

⚠ **Not labelled "complete".** v1's §5 omitted the narrowing line; v2's §5 claimed completeness and
was then extended by §10 — the same self-contradiction, in the section written to fix it. This list is
what is known to be required; §10 and §7 are part of the same change, not additions to it.

**In `scripts/check-ratchet-contract.py`:**

1. **`main:395`** — `glob("check-*.py")` → `glob("*.py")`. **The load-bearing edit**; widening
   `GUARD_PATH_RE` without it is a no-op.
2. **`GUARD_PATH_RE`** → `scripts/[\w.-]+\.py`.
3. **`discover_guards`** takes `texts`, excludes any module with a `NOT_A_GUARD` assignment (§3.2).
4. **`evaluate:174` and `main:403`** pass `texts`, not `list(texts)`. `evaluate` **is** touched.
5. **`RATCHET_DOCSTRING_RE` and `discover_ratchets` deleted** with their `DISCOVERY_CASES` (§8).
6. **Both false docstrings corrected in place**, keeping what made them false.
7. **`POPULATION_CASES` (`:296-304`) rewritten** — all three pass `list[str]` and break on the
   signature change, and the third asserts the **opposite** of the new payload case.
8. **The self-test's failure output becomes `[FAIL] <case name>`** — see §10. Without this the
   mutation manifest cannot go green.
9. **`SyntaxError` → one CANNOT-RUN exit**, not a traceback (§3.4).
10. **`:404`'s stale `"This project has 24"`** reworded as a magnitude, not a count — a number that
    now moves with every declaration would re-create the staleness on a faster clock.

**Outside it:** 17 `NOT_A_GUARD` assignments (§4); the §7 sites; §10's `POPULATION` edit (a
prerequisite for §3.5) and mutation manifest.

---

## §6 — What this does NOT do

- **It does not make lying impossible.** `NOT_A_GUARD = "…"` can be written on a real guard. It is a
  reviewable claim — the trade already accepted for `NO-CALLER:`. What changes is that **silence is
  no longer an option**.
- **It does not fix `NO-CALLER:`'s text weakness** (§3.3). Stated, measured as currently harmless, and
  left for the backlog.
- **It does not verify an IN file is a GOOD guard**, only R1/R2/R3.
- **It does not reach outside `scripts/`.** Moving a guard to another directory remains an evasion no
  gate sees. `.claude/hooks/` files are discovered only as *callers*.
- **It does not police `scripts/*.sh`.**
- **Only `check-ratchet-contract.py`'s own membership is re-verified after merge** (§3.5). There is no
  standing assertion of the total — §9 says why.
- **`gen-m4-manifest.py`'s `--self-test` is executed by nothing** (`:260`) and it is not in
  `check-selftest-counts.POPULATION`. One newly-enrolled guard satisfies R1 on an entry point nothing
  runs. R1 is unchanged here; the gap is recorded, not fixed.

---

## §7 — Every site that states the old population as fact

Ten. v1 corrected two.

| Site | After the change |
|---|---|
| `docs/process-checklists.md:294-296` | wholly false; describes the deleted `discover_ratchets` |
| `docs/process-checklists.md:283-288` | *"There are EIGHT"*, *"two independent sources"* — stale; becomes 28, one source |
| `docs/process-checklists.md:298` | *"Currently 4 violations"* — already false, `BASELINE = 0` |
| `docs/dev-process.md:145` | the false claim §1 hunts, **in the process spine**; its `21 cases` also moves |
| `scripts/check-test-counts.py:31-33` | *"discoverable by it … from two independent sources"* — a **live script docstring** |
| `scripts/page_markup.py:42-45` | false, and names a deleted function |
| `scripts/explainer-serve.py:68-73` | false — the file **is** read now |
| `.github/workflows/ci.yml:213` | *"its population is `glob("check-*.py")"*. ⚠ The `page_chrome` step (`:220-223`) states the same **conclusion** without the quoted mechanism — both go false, by different sentences |
| `docs/roadmap-to-launch.md:1692-1693`, `:1530`, `:1599` | same claim; *"25 guards"* — already stale |
| `docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md:176,183` | same claim, in a **living** spec |
| `docs/backlog.md` rows #72/#73 | edited by this PR anyway; must not be left describing the old mechanism |

---

## §8 — Backlog #73 settles as DELETE

`discover_ratchets` implements declare-**in** by bare-word match, which §1.1 measured as unable to
tell a declaration from a denial. Restoring it would ship the defect. Deleted with its
`DISCOVERY_CASES`. Both rows close in this PR; each closed row **leads** `✅ (was 🟠)` and its
`GROUPS` tuple in `scripts/gen-backlog-page.py` is deleted (the coverage check is bidirectional).

---

## §9 — Falsifiers

| # | Falsifier | Fails if |
|---|---|---|
| F1 | `gen-m4-manifest.py` and `verify-exclusion-reasons.py` appear in `guards discovered (…)` | either absent |
| F2 | Count is exactly **28** | any other number |
| F3 | `scripts/zz-probe.py`, no `--self-test`, no declaration → **appears in the discovered list** AND run exits 1 | absent, or exits 0 |
| F4 | `NOT_A_GUARD = "a probe"` → exits 0 and `zz-probe.py` is absent from the list | it stays IN |
| F5 | `NOT_A_GUARD` nested in a function, or set to `""`, or to a non-string → file stays IN | excluded — the fail-closed property broke |
| F6 | A docstring **documenting** the rule, and one **demonstrating** it at any indent, both leave the file IN | either excluded — v1/v2's Blocking returned |
| F7 | `check-ratchet-contract.py` appears in its own discovered population, **asserted by a case CI actually runs** | absent, or the case has no runner (§3.5) |
| F8 | `grep -rn discover_ratchets scripts/ .github/ .claude/ docs/process-checklists.md docs/dev-process.md docs/roadmap-to-launch.md` returns nothing | any hit |
| F9 | `BASELINE` is still `0` and the run is green | a raised baseline would launder the 10 failures |

> ⛔ **F3, F8 and F9 were repaired, not renumbered.** v1's F3 asserted exit 1 only — which
> `:388-392` also returns when `ci.yml` is missing from the temp copy, and `:417-419` with too few
> caller sources. v1's F6 grepped too narrowly to see `docs/`; **v2 widened it to all of `docs/` and
> made it unsatisfiable** — historical text legitimately contains the token
> (`docs/reviews/architecture-review-2026-08-30.md:73`, and this spec's own row). Both errors are the
> same one: writing the grep without running it. F8 now names the **living process documents**
> explicitly and excludes the review archive. v1's F7 (now F9) holds on the unchanged repo, so it is
> relabelled the anti-laundering check and paired with F2.

**Why no standing count assertion.** A permanent `assert len(guards) == 28` goes stale on the next
legitimate script and trains people to bump it. F7 is the standing membership check; §6 states plainly
that the total is not re-verified.

F3–F7 run against a temp copy — an instrument that edits the repo corrupts its peers. ⚠ **The copy
must include `.github/workflows/ci.yml` and the full caller sources**, or F3 passes for the wrong
reason.

---

## §10 — Test and mutation coverage

⛔ **The self-test's output format is a PREREQUISITE, not a detail.**
`scripts/check-plan-code.py:723-724` collects red case names from lines starting `[FAIL] ` and nothing
else. `check-ratchet-contract.py` contains **zero** occurrences and prints `  FAIL {name}` (`:343`,
`:348`, `:353`, `:358`, `:375`); the seven scripts already in the manifest carry 1–18 each. Without
§5 item 8, every `expect` resolves to **0 red cases** and `check-plan-code.py:778-786` fails the
mutation as *"caught by something else"*. `--mutate .` is what CI runs, so the PR could not go green.
⚠ Omitting `expect` to dodge this is the fail-open the harness's own comments exist to close.

- **Cases:** the eight §3.2 rows, the payload case (non-`check-*`, no declaration → IN), the
  rewritten `POPULATION_CASES`, and §3.5's self-inclusion case.
- **`check-selftest-counts.POPULATION`:** add `check-ratchet-contract.py` **and** its
  `--self-test  # N cases` declaration, in the same commit. Adding one without the other trips
  `:176-179`. **This is what makes §3.5 real** — `run_self_test` (`:183-186`) spawns POPULATION
  members with `--self-test`, wired at `ci.yml:178`, and nothing else runs this script's self-test.
- **Mutation manifest** — new `scripts/mutations/check-ratchet-contract.json` and a new
  `EXPECTED_MUTATIONS` key (`check-plan-code.py:432-497` has none). **The repo's most structurally
  important guard ships today with zero mutation coverage; this is its first.**
  - `main`'s glob narrowed back to `check-*` → red via the payload case.
  - `NOT_A_GUARD` detection accepting a nested assignment → red via the nested case.
  - `NOT_A_GUARD` detection accepting a non-string value → red via that case.
  - ⚠ Each `expect` entry names **exactly one** red case (`check-plan-code.py:739-746`).
- ✅ **Measured: the 17 declarations cannot orphan an existing anchor.** Only `gen-dashboard.py`,
  `page_chrome.py` and `page_markup.py` are both OUT and manifested, and **0** of their anchors'
  `before` text sits inside a module docstring. (`NOT_A_GUARD` is an assignment, not a docstring edit,
  so the surface is smaller still.) `--mutate .` still runs before the PR.

---

## §11 — Delivery

One branch, `fix/guard-inventory-population`, one PR, closing **#72** and **#73**. Merge tick written
before the PR opens. Dashboard entry required; row ticks ride in the same PR.

## §12 — Review record, and the one error that recurred four times

**Four halves, four NOT CONVERGED, 30 findings.** Every one re-verified against the code by the author
before acceptance; none disputed.

**Round 2 justified its scoping:** both Blockings are defects *in round 1's fixes* — the flush-left
anchor (Codex, and Claude's H2 independently) and the criterion contradicting its own reclassification
(Claude B2). A third, Claude B1, is in the *coverage* round 1's fix required.

⚠ **The same error occurred FOUR times in this slice, by the author, including twice in the sections
written to correct it:**

1. v1 §4's *"three OUT files satisfy R3"* — enumerated from CI self-test steps, not the rule. **Eight.**
2. v2 §3.1's grammar table — "indented example" enumerated from one instance, not the rule.
3. v2 §4's *"no fourth surprise"* sweep — screened by a flag that 2 of its own 3 IN files lack.
4. v1/v2's F6/F8 grep — written without being run, first too narrow, then unsatisfiable.

**Enumerate the dimensions from the RULE, then measure.** A screen that cannot find the things you
already know are there proves nothing about the things you do not.

**The halves disagreed on `build-m4-schema.py` in both rounds, and the derivation — not the vote —
settled it.** v2 followed the vote and a memory heuristic, and was wrong (§4.1).

**Round 3 will be scoped to §3's AST mechanism, §4.1's re-derivation, §5 item 8, and the repaired
falsifiers.** Phase 6 fires at four non-converging rounds (`docs/dev-process.md`); this is **two**.

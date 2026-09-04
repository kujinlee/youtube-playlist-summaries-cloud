# Spec review — `2026-09-02-guard-inventory-population-design.md` v1 (`1b649324`)

**Round 1, Claude half.** Branch `fix/guard-inventory-population`. Reviewed 2026-09-02.

**Method.** Every finding below is either a quote with `file:line` or executed output. The proposed
change was **implemented in a throwaway copy** of `scripts/`, `.github/` and `.claude/hooks/` under
`/Users/kujinlee/.claude-tmp/gip/repo` (population widened, `NOT_A_GUARD_RE` added, `evaluate` and
`main` retargeted, 17 `NOT-A-GUARD:` lines inserted) and the spec's falsifiers were run against it.
No `git` mutation, no Postgres, no schema gate. The live tree was read only.

> ⚠ **Independence disclosure.** A repo-wide `grep` for `NOT-A-GUARD` returned ~6 lines from
> `docs/reviews/spec-guard-inventory-population-r1-codex.md`, which the Codex half wrote into the
> working tree while I was reading. I did not open that file and did not follow up on those lines;
> the findings below were reached from the spec and the code. Recording it so the coordinator can
> discount any overlap rather than treat it as independent corroboration.

---

## Blocking

### B1 — `declare-out` is evadable **by accident**, and the first file to evade it is the guard itself

`docs/.../guard-inventory-population-design.md:105` —
`NOT_A_GUARD_RE = re.compile(r"NOT-A-GUARD:[ \t]*(\S[^\n]*)")`, searched over the module docstring.
§3 calls this "one line in the module docstring". It is not: it is *any occurrence anywhere in the
docstring*, including prose that describes the rule and indented examples that demonstrate it.

§1.1 is the section that kills the bare-word alternative, and its argument is exactly this class:

> `page_markup.py`'s docstring *predicted this outcome* on 2026-08-30 and the sentence that predicted
> it is the sentence that would enroll the file. (spec:55-57)

The colon form narrows the class. It does not close it, and the spec asserts closure by omission —
§6's limits list mentions only **deliberate** lying (`spec:195-198`), never accidental declaration.

**Observation — executed against the implemented copy.** Three inputs, all silently EXCLUDED, run
green:

```
=== (c) docstring that DOCUMENTS the rule ===
   """A real guard with a --self-test.
   A file leaves the inventory by writing NOT-A-GUARD: <reason> in its module docstring."""
EXIT=0 ; occurrences of "zz-doc" in the discovered list: 0

=== (d) indented example inside a docstring ===
   Example of the grammar::
       NOT-A-GUARD: a page generator
EXIT=0 ; occurrences of "zz-ex": 0
```

And the sharp one. §5 item 2 requires `check-ratchet-contract.py`'s own docstrings to be **rewritten
to describe the new mechanism**. Adding one such sentence to its module docstring:

```
=== SELF-EXCLUSION: the guard documents its own rule in its module docstring ===
EXIT=0
guards discovered (27): scripts/check-anchors.py, scripts/ch…
occurrences of "check-ratchet-contract" in the discovered list: 0
```

**The guard that polices every guard removed itself from its own population, and the run reported
success.** R1/R2/R3 then apply to nothing about it, and nothing in the repo notices: F2 ("count is
exactly 28") is a one-shot observation taken at implementation time, and §9 explicitly forbids a
standing count assertion —

> `GUARD_PATH_RE` narrowed back … → must go red **via the `gen-m4-manifest` discovery case**, not via
> a count assertion. (spec:253-254)

So after merge there is no mechanism that would ever detect this.

**Why Blocking rather than High:** the spec's entire thesis is *"omission fails"* (spec:88). This is
the same failure with a different cause — the file is omitted from the inventory by a sentence
nobody read as a declaration — and the spec rejects a cheaper alternative (§2, declare-in) on the
grounds that it is evadable. A mechanism whose stated advantage is inevitability must not have an
evasion path that the spec's own §5 instructs the implementer to walk into.

**What would fix it (not prescriptive):** (a) anchor the declaration to the start of a docstring line
(`(?m)^[ \t]*NOT-A-GUARD:`) — noting the repo's counter-lesson that `^marker` cannot see
`**marker**`, so the anchoring must be measured, not assumed; **and** (b) a permanent case asserting
that `check-ratchet-contract.py` is in its own discovered population. Precedent exists verbatim:
`scripts/check-selftest-counts.py:20` — *"⚠ IT CHECKS ITSELF. This script is in `POPULATION`, so its
own declared count is verified by the same external run."*

---

## High

### H1 — §5 says `evaluate` is untouched; the change it specifies makes that impossible, and the one load-bearing line is missing from the change list

`spec:186`:

> `evaluate`, `check_contract`, `check_caller`, `fail_open_handlers`, `invocation_re`, `NO_CALLER_RE`
> and `BASELINE` are untouched.

`spec:174-175` requires `discover_guards` to take *texts, not just paths*. The only in-repo call
sites are:

- `scripts/check-ratchet-contract.py:174` — `for rel in discover_guards(list(texts)):`, **inside
  `evaluate`**
- `scripts/check-ratchet-contract.py:403` — `ratchets = discover_guards(list(texts))`, inside `main`

`list(texts)` passes the *keys*. A signature that needs docstrings cannot be fed keys, so `evaluate`
must change. §5's "untouched" list is wrong about the function §5's own item 1 forces to change.

Worse in practice: **`main`'s glob is not in the change list at all.**
`scripts/check-ratchet-contract.py:395` — `for p in sorted((ROOT / "scripts").glob("check-*.py")):`
is where the narrowing physically happens. §5 lists five changes and never mentions it; the closest
it comes is item 4, which touches a *comment* eleven lines below it. An implementer who applies §5
literally widens `GUARD_PATH_RE` and gets a no-op, because `texts` still only ever contains
`check-*.py`. F1/F2 would eventually catch it, but a change list that omits its own load-bearing edit
is a defect in the spec, not a caught-later detail.

Related, minor accuracy: `spec:29` says *"Both callers (`:174`, `:403`) build the list from
`(ROOT/"scripts").glob("check-*.py")`"*. `:174` does not glob — it forwards whatever `main` handed
it. Stating it that way is what hides the fact that there is exactly **one** narrowing site.

### H2 — §4's "Three files in the OUT set … do satisfy R3 today" is **eight**, and the enumeration method is the repo's recorded failure mode

`spec:165-168`:

> ⚠ Three files in the OUT set — `page_markup.py`, `page_chrome.py` and `gen-dashboard.py`, two
> library modules and a generator — *do* satisfy R3 today, because CI invokes their `--self-test` and
> `invocation_re` sees that as a caller.

**Observation — `check_caller` run over the 17 OUT files with the live caller blob** (same
`caller_sources` composition as `main:413-416`):

```
OUT files that SATISFY R3 today: 8
   gen-backlog-page.py  gen-dashboard.py  gen-goals-page.py  regen-skills-doc.py
   page_markup.py  page_chrome.py  explainer-serve.py  build-m4-schema.py
OUT files fully conforming (R1+R2+R3): 7
   gen-backlog-page.py  gen-dashboard.py  gen-goals-page.py
   page_markup.py  page_chrome.py  explainer-serve.py  build-m4-schema.py
```

Neither reading gives three. The cause is visible in the sentence's own clause — *"because CI invokes
their `--self-test`"*: the set was enumerated from **one reason** (files with a dedicated CI
self-test step) rather than from **the rule** (`invocation_re` over the whole caller blob), so every
file whose caller is a shell gate or another script was missed. That is the pattern recorded as
*"measure the population the CODE sees"* and *"a measurement is only as good as its CORPUS"*.

This number is not load-bearing for the design, which is why I have graded it High rather than
Blocking — but note the round's stated rule ("any number that does not reproduce is Blocking") reads
this as Blocking, and it sits inside the one ⚠ note whose job is honesty about the OUT set.

### H3 — §9's `check-selftest-counts.py` claim is false, and acting on it turns CI red

`spec:249-251`:

> **Cases deleted** with `discover_ratchets`. `scripts/check-selftest-counts.py` ratchets the total,
> so its pinned count moves in the same commit — up or down, whichever the arithmetic gives.

**Observation — executed against the live tree:**

```
scripts declaring a count today: ['check-anchors.py', 'check-plan-code.py',
  'check-plan-task-order.py', 'check-review-rounds.py', 'check-selftest-counts.py',
  'check-test-counts.py', 'explainer-serve.py', 'gen-goals-page.py', 'page_chrome.py']
check-ratchet-contract.py in POPULATION? False
check-ratchet-contract.py declares a count? False
```

`check-ratchet-contract.py` declares no `--self-test  # N cases` line (its usage block is
`scripts/check-ratchet-contract.py:23-26`) and is absent from
`scripts/check-selftest-counts.py:83-92`'s `POPULATION`. **Nothing ratchets its total.** The spec
asserts a protection that does not exist — the precise defect class the spec exists to fix, one layer
up.

And if an implementer closes the gap the way §9 implies, by adding the declaration:

```
If §9 is followed and it starts declaring, without a POPULATION edit:
['check-ratchet-contract.py: declares a case count but is not in POPULATION,
  so nothing checks it. Add it.']
```

— `scripts/check-selftest-counts.py:176-179` fails the build. §9 must either say *"and add it to
`check-selftest-counts.POPULATION` in the same commit"* or drop the claim.

### H4 — the blast radius is six-plus prose sites; §5 corrects two, and F6's grep cannot see the rest

§5 item 2 corrects the two docstrings **inside** `check-ratchet-contract.py`. Every other place in
the repo that states the population as fact is untouched by the spec:

| Site | What it says today | After the change |
|---|---|---|
| `docs/process-checklists.md:294-296` | *"discovers ratchets from two independent sources — CI step names containing "ratchet", and any `scripts/check-*.py` whose docstring declares itself one — so neither a forgotten registry entry nor an unwired script can evade it"* | wholly false; describes the deleted `discover_ratchets` |
| `docs/process-checklists.md:283-288` | *"There are EIGHT"* + *"Do not maintain this list by hand — `python3 scripts/check-ratchet-contract.py` prints it, from two independent sources"* | already stale (26); becomes 28, from one source |
| `docs/process-checklists.md:298` | *"Currently 4 violations, all rule 4"* | already false — `BASELINE = 0`, live run reports 0 |
| `docs/dev-process.md:145` | *"the population is the FILESYSTEM … `--self-test`: 21 cases"* | the false claim §1 hunts, in a **third** site the spec never lists; the case count also moves |
| `scripts/page_markup.py:42-45` | *"The live population is built at `:395` from `glob("check-*.py")` … (`discover_ratchets:67`, which does implement the docstring rule, is now reached only…)"* | false, and names a deleted function |
| `scripts/explainer-serve.py:68-73` | *"that script discovers by globbing `scripts/check-*.py`, so this file is never even read"* | false — the file **is** read, to look for its declaration |
| `.github/workflows/ci.yml:212-215`, `:220-223` | *"`check-ratchet-contract.py` neither sees it nor should: its population is `glob("check-*.py")`"* (×2) | false for both `page_markup.py` and `page_chrome.py` |
| `docs/roadmap-to-launch.md:1692-1693` | same population claim; `:1530`, `:1599` say *"25 guards"* | false / already stale |
| `docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md:176,183` | same claim, in a **living** spec | false |

F6 (`spec:235`) greps `scripts/ .github/ .claude/` for `discover_ratchets`. It catches
`page_markup.py:45` and nothing under `docs/`, where the canonical description lives. §1.2 is the
section that says *"a true statement in a neighbour's comment did not correct the false one at the
source"* — shipping this with `process-checklists.md` still describing two-source discovery reproduces
that shape, in the document that is supposed to be the convention.

### H5 — §2's rejection of declare-in rests on a cause the spec's own §1.1 refutes

`spec:83-85`:

> it is a registry — and `discover_ratchets`'s own docstring already rejected registries as *"evadable
> by simply not registering"*. **That is precisely how `gen-m4-manifest.py` came to be missed.**

That last sentence is false, and §1.1's own table says so: `gen-m4-manifest.py` is row 1, verdict
**"genuine declaration"** (`spec:48`). It *did* register.

**Observation** — `discover_ratchets("", <all 45 scripts/*.py>)` on the live tree:

```
docstring-rule enrolls (non-check): 6
   explainer-serve.py  gen-backlog-page.py  gen-m4-manifest.py
   page_markup.py  prior-art.py  subject_status.py
```

`gen-m4-manifest.py` was missed **by the population**, not by non-registration — which is the whole
of §1. The general evadability argument against declare-in stands on its own; the causal claim
attached to it does not, and it is the sentence doing the persuading.

Secondary, same paragraph: the quoted docstring objection is to *"a registry list"*
(`check-ratchet-contract.py:70`), i.e. a central roster. The same docstring offers a per-file
self-declaration as the **defence against** registries (`:71-72`). Citing it against a per-file marker
inverts what it says.

---

## Medium

### M1 — F3 passes for the wrong reason; F7 passes on the unchanged repo

`spec:232` (F3): *create `scripts/zz-probe.py` with no `--self-test` and no declaration → contract
exits **1***. `spec:238` says F3–F5 run against a temp copy.

**Observation — both from the implemented temp copy:**

```
=== F3 clean ===                          F3 EXIT=1   (expect 1)  ✅
=== F3 WRONG-REASON trap: ci.yml absent ===
FAILED: .github/workflows/ci.yml not found — ratchets could not be discovered.
Treat this as NOT RUN.
EXIT=1
```

A temp copy assembled without `.github/workflows/ci.yml` satisfies F3's stated observation exactly
(`check-ratchet-contract.py:388-392`), as does one with fewer than three caller sources (`:417-419`).
F3 is the falsifier carrying *"omission still escapes, which is the whole point"*, and its assertion
is exit-code-only. It must assert that `zz-probe.py` **appears in the `guards discovered (…)` line**,
not merely that the process exited 1.

`spec:236` (F7): *"`BASELINE` is still `0` and the run is green"*. On today's unchanged tree
`BASELINE = 0` (`check-ratchet-contract.py:52`) and the run is green (verified: `guards discovered
(26)`, exit 0). F7 therefore passes whether or not the change was made — vacuous as evidence of the
change, though still meaningful as a *"did anyone launder the 10 failures"* check. Say which job it
is doing, and pair it with F2.

### M2 — §9 adds a self-test case that contradicts an existing one, and never says the existing three must be rewritten

`scripts/check-ratchet-contract.py:296-304`, `POPULATION_CASES`, third entry:

```python
("a non-guard script is not in the population",
 ["scripts/gen-dashboard.py", "scripts/check-a.py"], ["scripts/check-a.py"]),
```

`spec:245-246` adds *"a non-`check-*` file with no declaration (IN — the payload case)"*. Those two
cases assert opposite verdicts on the same input shape. All three existing cases also pass
`list[str]` and break outright on the signature change (H1). §9's only statement about existing cases
is *"Cases deleted with `discover_ratchets`"* (`spec:249`) — which covers `DISCOVERY_CASES`, not
`POPULATION_CASES`. An implementer hits a red suite with no instruction, at the exact moment the
tempting repair is to weaken the new case.

### M3 — §3 is silent on what happens to a file that does not parse, and both available answers are wrong in a different way

`check_caller` already has a policy — `scripts/check-ratchet-contract.py:148-151`:

```python
try:
    doc = ast.get_docstring(ast.parse(text)) or ""
except SyntaxError:
    doc = text
```

On `SyntaxError` the *entire file text* becomes the "docstring". For `NO-CALLER:` that means a broken
guard can opt out of one rule with a token in a comment. Extending the same pattern to
`NOT-A-GUARD:` removes the file from the population entirely.

**Observation — implemented copy, both branches:**

```
=== (e) syntax error + "NOT-A-GUARD:" in a comment ===   EXIT=0, file silently EXCLUDED
=== (f) syntax error, no declaration anywhere ===        EXIT=1 via uncaught traceback:
    def main(:
             ^
SyntaxError: invalid syntax
```

(f) is fail-closed, so it is not a false green — but it is a Python traceback where
`docs/process-checklists.md`'s rule 1 requires *"exit non-zero and say treat this as NOT RUN"*, and
it comes from `fail_open_handlers` (`:92`), which has no guard of its own. Today the population is 26
files all known to parse; widening to 45 triples the surface, and §6 does not mention it. State the
policy explicitly and add a case.

### M4 — "the concrete answer to what widening actually buys" changes no verdict today, and §4 does not say so

`spec:128-129`: *"`gen-m4-manifest.py` **is the payload of this change** … the concrete answer to
'what does widening actually buy'."*

Measured: `gen-m4-manifest.py` already satisfies R1 (`--self-test` at `scripts/gen-m4-manifest.py:304`
— a real `add_argument`, not a prose mention), R2 and R3 (callers at
`scripts/check-schema-gates.sh:99-100`). So enrolling it produces **no new violation, no new
requirement, and no behaviour change** — the buy is entirely prospective. That is a legitimate reason
to do it; presenting it as *the* concrete answer overstates it, and F1 asserts only presence.

Two things §6 should say and does not: `gen-m4-manifest.py`'s own `--self-test` is never executed by
anything — `scripts/gen-m4-manifest.py:260` records *"the fourteen-gate suite runs `--check` and never
`--self-test`"* — and it is not in `check-selftest-counts.POPULATION`. So the newly-enrolled guard
passes R1 on the existence of an entry point that nothing runs.

### M5 — §6's limits list manufactures coverage by being complete about one axis only

`spec:191-203` is honest about scope (`scripts/` only, `*.py` only, R1–R3 unchanged) and about
deliberate lying. It is silent on every failure mode found above: accidental declaration (B1), a
declaration in a rule-documenting or example context (B1), unparseable files (M3), case sensitivity
(a lowercase `not-a-guard:` does not match — fails closed, but unstated), and the fact that after F2
is ticked **nothing ever re-verifies the population size again**. A "what this does NOT do" section
in a spec whose subject is overclaiming is held to a higher bar than most; as written it reads as a
completeness claim it has not earned.

---

## Low

- **L1 — `spec:156`: "`import`ed by 4–5 scripts each".** Measured importers, self excluded:
  `page_markup` 4, `m4_catalog` 5, `subject_status` **3**, `m4_base_db` **3**. The argument (a library
  is not a guard) is unaffected; the number is wrong for half the set.
- **L2 — the anchor justification overclaims.** `spec:10`: *"`status-visibility` is the anchor every
  tooling spec in this repo has used."* Falsified by
  `docs/superpowers/specs/2026-08-19-prod-readonly-smoke-design.md:3` — a smoke-test harness spec,
  pure tooling, which allocated its own anchor `prod-smoke`. The conclusion (reuse rather than
  allocate) is still reasonable; the universal is not true. Note also that the goal quoted at
  `docs/anchors.md:39` is about *a person who was away* seeing state — the fit for a guard-population
  change is analogical, which the spec does acknowledge.
- **L3 — `spec:257-259` warns that "existing mutation anchors may target `discover_guards`".** There
  are none: no `scripts/mutations/*.json` mentions `check-ratchet-contract.py`, `discover_guards` or
  `GUARD_PATH_RE`, and `EXPECTED_MUTATIONS` (`scripts/check-plan-code.py:432`) has no key for it. The
  real state is that the repo's most structurally important guard ships today with **zero** mutation
  coverage; §9 adds two entries, which is the first coverage it will ever have. Worth saying plainly
  rather than as a retargeting caution.
- **L4 — §5 item 4** calls `:404`'s *"This project has 24"* stale and moves it to 28. Correct, but the
  comment annotates a *"discovery broke"* sanity check; pinning it to a number that now floats with
  every declaration re-creates the same staleness on a faster clock. Consider wording it as a
  magnitude rather than a count.

---

## What I checked and found clean

- **`scripts/*.py` = 45, `check-*.py` = 26, non-`check-*` = 19.** Reproduced exactly.
- **Live run: `guards discovered (26)`, exit 0; `--self-test` 21/21.** Reproduced exactly.
- **§1.1's six docstring-rule enrollments, and the declaration/denial/citation verdicts** — all six
  files reproduce, listed under H5.
- **"10 of 19 fail R1/R2/R3 today, and all 10 are in the OUT set."** Reproduced exactly:
  `brief-compose, codex-frontier-model, codex-review, m4_base_db, m4_catalog, prior-art,
  regen-skills-doc, session-skill-report, skill-usage-audit, subject_status`. Every one is in §4's
  OUT table. **"Zero code repairs" holds.**
- **The count after the change is 28**, and both new members are the two §4 named:
  `guards discovered (28): … scripts/gen-m4-manifest.py, scripts/verify-exclusion-reasons.py` — exit
  0, no violations. F1 ✅ F2 ✅.
- **F4 ✅** (`NOT-A-GUARD: a probe` → exit 0) and **F5 ✅** (bare colon, reason on the next line → file
  stays IN, run exits 1). The `[ \t]` vs `\s` distinction is correctly inherited and load-bearing.
- **§4's two IN files genuinely are guards and genuinely conform** — `verify-exclusion-reasons.py:2`
  (*"EXECUTE the written reasons … instead of re-reading them"*) and `gen-m4-manifest.py:5`
  (`--check` … *"FAIL if it differs (ratchet)"*), both with real `--self-test` entry points.
- **§4.2's R3 reasoning is right on the mechanism** — `invocation_re` (`:121-129`) matches an
  invocation, not an import, so imported modules read as caller-less. That is R3 behaving correctly.
- **`BASELINE` stays 0 and the post-change run is green.** Verified in the implemented copy.
- **No `git` state was mutated**; no schema gate or database was touched.

### Gaps in my coverage (stated so they are visible)

- I did not run `scripts/check-plan-code.py --mutate .`, `check-docs.py`, or the full CI suite against
  the implemented copy — so I have **not** measured whether the 17 docstring insertions collide with
  any existing mutation anchor in `page_markup.json` / `page_chrome.json` / `gen-dashboard.json`
  (anchors bind by text, and I inserted lines into two of those files' docstrings).
- I did not verify §7's backlog mechanics — the `✅ (was 🟠)` lead convention or the `GROUPS` tuple
  deletion in `scripts/gen-backlog-page.py:95`. I confirmed `GROUPS` exists and is hand-maintained
  with a bidirectional coverage check (`gen-backlog-page.py:29-41`); I did not test the closure.
- I did not assess whether `check-guard-coverage.py` or any schema gate maintains a second, now
  divergent, notion of "the guard population" — it is a Postgres-backed gate and out of bounds for
  this round.
- My implemented copy is *my* reading of §5, not the author's. B1, H1 and M3 are about what §5 as
  written instructs; a different implementation could differ in detail (not in class).

---

**VERDICT: NOT CONVERGED** — one Blocking (the opt-out is evadable by accident, demonstrated by the
guard excluding itself while reporting success), five High (a change list that contradicts itself and
omits its load-bearing line; a "measured" three that is eight; a false claim of ratchet protection
that breaks CI if acted on; a blast radius of six-plus uncorrected prose sites; and a rejection
argument refuted by the spec's own table), plus five Medium and four Low.

# Round 8 — Claude adversarial review of `harness-progress-output` @ `e314c235`

**Verdict: NOT CONVERGED** — 1 Blocking, 2 High, 2 Medium, 3 Low.

Scope: COVERAGE, per the round brief. No restructure is proposed; every finding below names a
change of a few lines inside the code r7 already wrote.

---

## Proof of subject

```
$ git rev-parse --abbrev-ref HEAD
harness-progress-output
$ git rev-parse HEAD
e314c235c7aa1c8452af4c5b2a9b06ab90c630e1
$ git log --oneline origin/master..HEAD
e314c235 Round 7: the guard failed the way it was built to detect
48d8cabb Round 6: ask the fixture question with a script, not with a reviewer
6a660454 Round 5: a fixture must differ from itself along the axis it tests
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes
$ git show --stat e314c235 | tail -9
 docs/dashboard-entries.md                          |  29 +-
 docs/reviews/claude/harness-progress-r7-claude.md  | 355 ++++++++++++++++
 .../coordinator/harness-progress-r7-codex.md       |  84 ++++
 .../harness-progress-r7-codex.verdict.json         |  13 +
 scripts/check-fixture-variation.py                 | 452 +++++++++++++++++++--
 scripts/check-plan-code.py                         |  20 +-
 scripts/mutations/check-fixture-variation.json     | 212 +++++++++-
 scripts/mutations/check-plan-code.json             |  13 +
 8 files changed, 1138 insertions(+), 40 deletions(-)
```

## Control, proved green FIRST

```
$ python3 scripts/check-fixture-variation.py --self-test
38/38 passed                                                                   rc=0
$ python3 scripts/check-fixture-variation.py
fixture variation OK — 484 parameter(s) examined across 48 file(s); 124 known-unvaried
ratcheted, 2 exempt with a written reason                                      rc=0
$ python3 scripts/check-plan-code.py --self-test
128/128 passed                                                                 rc=0
```

Every attack below was run in a staged copy at
`…/scratchpad/r8work/tree/scripts`, under `HOME=…/r8work/tree/fakehome`, and the control was
re-proved green in that tree before and after each one:

```
$ HOME=$W/tree/fakehome python3 $W/tree/scripts/check-fixture-variation.py
fixture variation OK — 484 parameter(s) examined across 48 file(s); …            rc=0
```

The repo itself was not edited. This review file is the only thing written under the repo.

**One correction to my own first pass:** I initially grepped for a CI caller with
`grep -rn --include=*.yml` from the repo root and got nothing, and nearly filed "the guard has no
caller". That was my grep, not the code. It is wired, twice:

```
.github/workflows/ci.yml:287        run: python3 scripts/check-fixture-variation.py
.github/workflows/ci.yml:290        run: python3 scripts/check-fixture-variation.py --self-test
```

so the live run over all 48 files, not only the suite, executes on every PR. That matters for the
severity of B1 and H2 below.

---

# Blocking

## B1 — deleting the subject satisfies the ratchet, and the guard CONGRATULATES you for it

`scripts/check-fixture-variation.py:382-385`

```python
# ...and a known entry that no longer fires is DEBT PAID: say so, so the list shrinks
# instead of outliving its subject. Reported, not failed — tightening is a deliberate act.
for gone in sorted(known - seen_known):
    paid.append(f"{t.name}: `{gone}` now varies — delete it from KNOWN_UNVARIED")
```

`seen_known` is populated only from findings that `analyse` **emitted** (`:376-380`). So
`known - seen_known` means *"this entry did not fire"*, and the message asserts *"`{gone}` now
varies"* — a cause the code never measured. A ratcheted entry stops firing for two reasons that
are indistinguishable here:

1. the parameter genuinely started varying — debt paid; or
2. **the parameter stopped being examined at all** — its function was renamed, made private,
   deleted, or its last call site removed.

This is r7's own H2 rule ("an ABSENCE assertion needs a PRESENCE partner on the SAME fixture")
violated by r7's own new code, in exactly the direction r7 H1 named as the thing to avoid: *"the
same perverse shape as a ratchet that can be satisfied by deleting the subject."*

### Measured — a one-token-per-site privatisation, nothing else changed

`check-anchors.py` ratchets three entries (`:120-121`): `audit.cutoff`, `audit.docs`,
`audit.subdirs`. Rename `audit` → `_audit` (definition and all 17 call sites — an ordinary
"make this private" refactor; the file still runs and still parses):

```
$ HOME=$W/tree/fakehome python3 $W/tree/scripts/check-fixture-variation.py
  ⭐ check-anchors.py: `audit.cutoff` now varies — delete it from KNOWN_UNVARIED
  ⭐ check-anchors.py: `audit.docs` now varies — delete it from KNOWN_UNVARIED
  ⭐ check-anchors.py: `audit.subdirs` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — 479 parameter(s) examined across 48 file(s); …
rc=0
```

Three parameters just left the guard's field of view and it printed three gold stars. The examined
total fell 484 → 479 and nothing reads it.

**Nothing else on the branch catches it.** I checked, rather than assumed:

```
$ python3 scripts/check-anchors.py --self-test           (before)   15/15 self-test cases passed
$ HOME=… python3 $W/tree/scripts/check-anchors.py --self-test (after) 15/15 self-test cases passed
```

The case count is unchanged, so `check-selftest-counts.py` sees no drift; `check-anchors.py` is
still in the population, so the `--self-test` case at `:688` ("every ratcheted file is one
discovery returns") still passes; `POPULATION_FLOOR` still reads 48. The only observer was this
guard, and it said ⭐.

### The realistic variant, for completeness

Deleting the 15 cases that drive `audit` (17 lines, whole `check(...)` statements, AST-safe)
produces the same three ⭐ lines, `475 parameter(s)`, rc 0. That one *is* independently caught —
`check-anchors.py` declares 15 cases and `check-selftest-counts.py` would see 0 — so the
privatisation above is the airtight demonstration and the deletion is the common one.

### The two mechanisms r7 added protect DISJOINT sets of files

r7's answer to "deleting the last case makes the guard quieter" was `EXAMINED_FLOOR`. Measured:

```
files with a pinned EXAMINED_FLOOR   : ['check-fixture-variation.py', 'check-plan-code.py']
files with a NON-EMPTY KNOWN_UNVARIED: 34
INTERSECTION                         : []
```

Every one of the 34 files carrying real ratchet debt has no floor, and both floored files have an
empty ratchet (`check-plan-code.py` is `KNOWN_UNVARIED`'s only empty entry, `:148-149`;
`check-fixture-variation.py` is not in it at all). So the mechanism that detects deletion and the
mechanism that rewards it never apply to the same file. There is no configuration in which the
floor catches what the ⭐ line lets through.

### Why Blocking rather than High

The guard runs in CI over all 48 files (`ci.yml:287`). Its single purpose is to detect coverage
that cannot fail. The most direct way to destroy coverage — remove the subject — is not merely
undetected, it is reported as success and the output *instructs the reader to delete the ratchet
entry*, at which point the parameter is unprotected permanently and silently. A reader following
the guard's own advice lowers the ratchet on a false premise.

### The fix is small and stays inside r7's design

`analyse` already computes `seen`; it just does not return it. Return the examined key set (or a
second value), and in `main` split the two cases:

* `(fn, param)` still in `seen`, no finding → **debt paid**, keep the ⭐;
* `(fn, param)` **not in `seen`** → the subject left. That is coverage LOST: report it as a
  finding and fail, with the entry named so the author must either restore the call sites or
  delete the entry deliberately in the commit.

That is the same presence-partner shape r7 applied at `check-plan-code.py:2045-2055` and at
`:667-668` of this file.

---

# High

## H1 — the documented single-file invocation emits two standing false positives

`scripts/check-fixture-variation.py:355` (`paths`, "override the declared POPULATION"),
`:399-401`, `:320-348`.

```
$ python3 scripts/check-fixture-variation.py scripts/check-anchors.py
FAILED — 2 parameter(s) never varied by any case:
  ✗ the exemption `diagnostic_tail.window` is DEAD — the rule passes without it anywhere in the
    population, so it guards nothing today and will mask that parameter the moment it stops
    varying. Delete it; an exemption nobody needs is one nobody re-examines.
  ✗ the exemption `run_suite_parts.d` is DEAD — …
rc=1

$ python3 scripts/check-fixture-variation.py scripts/check-fixture-variation.py
FAILED — 2 parameter(s) never varied by any case:
  ✗ the exemption `diagnostic_tail.window` is DEAD — …
  ✗ the exemption `run_suite_parts.d` is DEAD — …
rc=1
```

The second invocation is the one r7's own review doc used
(`docs/reviews/claude/harness-progress-r7-claude.md:99`).

Both exemptions are correct and load-bearing; the full run proves it (`rc=0`, "2 exempt with a
written reason"). They read as dead because `main` hands `dead_exemptions` the **override set**
as `sources` (`:387`, `:401`), and both exempted functions live only in `check-plan-code.py`
(measured: `run_suite_parts` and `diagnostic_tail` are defined in exactly one file of the 48).

`dead_exemptions`' own docstring, `:331-335`, states the rule this breaks:

> ⚠ DEADNESS IS A PROPERTY OF THE POPULATION, NOT OF ONE FILE, and the first version got that
> wrong. It judged each file alone, so an exemption written for `check-plan-code.py` read as dead
> the moment the population grew to a second file.

r7 fixed that inside `dead_exemptions` and left the identical bug in the caller: when `paths` is
given, `sources` *is* one file. The fix r7 wrote is defeated by the flag on the same page.

r7's own words, at `:216-218`, are the severity argument: *"four standing false positives is how a
guard gets switched off."* Here it is two, on the invocation a developer reaches for first, and
they instruct the reader to delete two correct exemptions.

CI is unaffected (`ci.yml:287` passes no paths), which is why this is High and not Blocking.

**Fix:** judge deadness over `population(root)` regardless of the override — the override selects
what to *report on*, not what the population *is* — or skip `dead_exemptions` entirely when
`a.paths` is set, the way `population_shortfall` is already skipped at `:411`.

**Second, smaller defect in the same output:** the header at `:418` reads
`FAILED — {len(all_findings)} parameter(s) never varied by any case`, but `all_findings` also
carries dead-exemption findings and `EXAMINED_FLOOR` findings (`:390`). Two dead exemptions are
reported as "2 parameter(s) never varied by any case", which is false about both of them.

## H2 — `EXEMPT` has no file scope, while `KNOWN_UNVARIED` does

`scripts/check-fixture-variation.py:230-237` vs `:114` / `:373`.

`KNOWN_UNVARIED` is keyed `filename → (fn.param, …)` and looked up per file
(`known = set(KNOWN_UNVARIED.get(t.name, ()))`, `:373`). `EXEMPT` is keyed `fn.param` alone and
consulted with no file at all (`:308`). r7 widened the population from 2 files to 48 and gave only
one of the two ratchets a file dimension.

### Measured, with its falsifier

A brand-new script in `scripts/` that happens to define a function called `run_suite_parts`:

```python
def run_suite_parts(d, name):
    return d, name

def _self_test():
    case("x", run_suite_parts(TMP, "a"), None)
    case("y", run_suite_parts(TMP, "b"), None)
```

`d` is `TMP` at both sites — a textbook finding. The guard:

```
fixture variation OK — 486 parameter(s) examined across 49 file(s); …            rc=0
```

Rename the parameter `d` → `dd` so the exemption key no longer matches, changing nothing else:

```
FAILED — 1 parameter(s) never varied by any case:
  ✗ new-guard.py: `run_suite_parts(dd=…)` is passed the SAME value at every call site in the
    suite (2x `TMP`). …                                                          rc=1
```

So the pass was the exemption, not the rule. An exemption written about one function in
`check-plan-code.py` silently forgives every same-named function across a 48-file population.

Latent today — measured, `run_suite_parts` and `diagnostic_tail` are each defined in exactly one
file — but this is precisely the reasoning r7 used for L1 at `:282-283` ("Latent when found …
fixed before the population widened into one"), applied here to a population that has *already*
widened.

**Fix:** key `EXEMPT` by `filename → {fn.param: reason}`, matching `KNOWN_UNVARIED`. Two entries
to migrate. `dead_exemptions` keeps its population-wide deadness test unchanged.

---

# Medium

## M1 — 17% of the "484 parameters examined" are the suites' own fixtures

`scripts/check-fixture-variation.py:259-262`

```python
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
        defs.setdefault(node.name, node)
```

The exclusion for test plumbing is spelled as a **naming convention** (leading underscore) while
the property that actually distinguishes plumbing is **location** — defined inside the suite. A
non-underscore helper defined inside `_self_test` is treated as a function under test.

Measured over the live population:

```
examined parameters total: 484
...of which belong to a helper DEFINED INSIDE the suite: 82, across 22 files
```

and of the 124 ratcheted findings, **9 are about suite-local helpers**:

```
check-banner-armed.py       6  asst_toolonly.path, edit.path, meta.text, notif.text,
                               use_nb.path, use_nb.tid
check-paid-caller-arrival.py 1  ck.got
check-selection-card.py      1  card.question
page_chrome.py               1  raises.where
```

This is the noise class manifest entry 5 exists for — *"private helpers are audited as subjects,
so test plumbing is reported as production coverage and the finding list fills with noise"* — and
mutation 5 only covers the underscore half of it. Consequences: the headline number overstates
real subject coverage by 17%; `EXAMINED_FLOOR` is padded by it; and 9 ratchet entries name debt
that can only ever be "paid" by varying arguments to an assertion helper.

**Fix:** exclude functions whose definition is inside the suite node, the same way `case` is
excluded at `:240-242`. `_is_case_arg`'s docstring already states the principle.

## M2 — both floors pin a COUNT, and the SET moves underneath them

The brief asks whether a floor on the count is the right instrument. Measured: no, for both floors.

### `POPULATION_FLOOR` (`:75`, checked at `:411`)

`population()` at `:96-104` silently `continue`s past any file it cannot parse and any file whose
suite is spelled differently. Rename one suite function in `check-guard-coverage.py`
(`def self_test(` → `def run_the_suite(`, one token) and add one unrelated new script that
defines a suite:

```
step 1 (drop one):     CANNOT RUN — 47 script(s) …, below the pinned floor of 48       rc=2
step 2 (add one back): fixture variation OK — 481 parameter(s) examined across 48 file(s)  rc=0

     'check-guard-coverage.py' in population: False
     'brand-new-helper.py'      in population: True
     population size: 48
```

A file that was being examined left the population, the count was replenished by an unrelated one,
and the guard printed "48 file(s)".

The `--self-test` case at `:688` pins membership by name — but only for the 35 files that appear
in `KNOWN_UNVARIED`. **13 of the 48 are pinned by nothing but the count**: `brief-compose.py`,
`build-m4-schema.py`, `check-backlog-closure.py`, `check-docs.py`, `check-fixture-variation.py`,
`check-function-revokes.py`, `check-guard-coverage.py`, `check-plan-file-tags.py`,
`check-plan-task-order.py`, `check-sentinel-meanings.py`, `check-storage-grant-pin.py`,
`check-vocabulary-collisions.py`, `coverage_verdict.py`.

**Fix:** pin the discovered set by name, not its cardinality — the `:688` case already does this
for 35 files; extend it to all 48 (a `POPULATION` tuple beside `POPULATION_FLOOR`, or assert the
discovered basenames against a frozen list).

⚠ The swallow that makes this possible is a **fail-open on the population**, and the project's
fail-open ratchet cannot see it. `check-ratchet-contract.py:14` enforces R2 as *"AST: `except:`
whose body returns success"*, implemented at `:90-105` as handlers that `return 0`:

```
$ python3 scripts/check-ratchet-contract.py
guards discovered (33): … scripts/check-fixture-variation.py …
ratchet contract OK                                                             rc=0
```

`population()` at `:97-100` does not return 0 — it `continue`s, dropping the member. "I could not
read this file, therefore it is not part of the subject" is the same fail-open one level out from
the exit code, and it passes R2 cleanly. That is context for the fix, not a separate finding.

### `EXAMINED_FLOOR` (`:221-224`, checked at `:388-394`)

Same shape one level down, and demonstrated on the guard itself (floor 8, exactly 8 examined):

```
CONTROL:                                                   8 examined (floor 8)
STEP 1  coverage of population_shortfall DELETED ->        6 examined; findings: 0
STEP 2  2 trivial params added                   ->        8 examined; findings: 0
        floor of 8 held: True
```

The coverage deleted in step 1 is of `population_shortfall` — the function r7 *extracted
specifically so a case could reach it*, because its mutation had survived. The floor created to
protect that does not.

Honest qualification: for these two files the deletion in step 1 would also be caught by the
`--self-test` count ratchet (38 cases) and by `--mutate .` refusing an unresolvable `expect`. The
finding is that the floor's own claim at `:219-220` — *"coverage may grow, and a drop is a finding
that names its own number"* — is false as stated, and for the other 46 files there is no floor at
all.

### Coverage of the floor, stated plainly

```
files with a pinned EXAMINED_FLOOR: 2 of 48
examined parameters under any floor: 37 of 484  (92% unpinned)
top files by examined count, all unpinned: gen-backlog-page.py 39, check-banner-armed.py 37,
                                           codex-review.py 31, gen-dashboard.py 30
```

The brief asks whether "EXAMINED_FLOOR covers 2 of 48" is honest or a green tick implying 48. The
*comment* is honest — `:208-220` explains the choice. The *output line* is not: "484 parameter(s)
examined across 48 file(s)" is printed with no indication that 447 of those 484 can vanish without
the exit code changing. Adding the two numbers to the OK line ("…; 37 of 484 under a pinned
floor") costs one f-string and removes the implication.

---

# Low

## L1 — positional-only parameters MISATTRIBUTE arguments, they do not merely vanish

`scripts/check-fixture-variation.py:284-289`

```python
names = [a.arg for a in fn.args.args]
kwonly = [a.arg for a in fn.args.kwonlyargs]
...
for i, arg in enumerate(node.args):
    if i < len(names):
        seen.setdefault((fn.name, names[i]), []).append(ast.unparse(arg))
```

`fn.args.posonlyargs` is never read. r7 L1 fixed `kwonlyargs` and called it "the other half of the
signature grammar" (`:278-283`); there is a third part, and it fails worse. Because positional
arguments are matched to `names` **by index**, a `/` in the signature shifts every mapping:

```
def f(a, /, b): ...
    case("x", f(1, 9), 1)
    case("y", f(2, 9), 2)

  truth: `a` varies (1 vs 2); `b` is 9 at both sites -> `b` must be reported
  guard: []  findings   | examined: 1
```

`b` records the values of `a`, so a genuinely unvaried parameter reads as varied. That is a
**false negative by misattribution** — the direction that matters for a guard — where the kwonly
gap r7 fixed produced a false positive. `EXAMINED_FLOOR` also undercounts (1, not 2).

Latent: measured, **0 of the 48 files in the population use `/`**. Same standard r7 applied at
`:282-283`: fix it before the population grows into one. Two lines —
`names = [a.arg for a in fn.args.posonlyargs + fn.args.args]`, and note that `fn.args.defaults`
already spans posonly+args so the slice at `:300` becomes correct for free.

## L2 — `dead_exemptions` declares every exemption dead over an empty population

`scripts/check-fixture-variation.py:337-341`

```python
needed = any(any(f"`{fn}({param}=" in x for x in analyse(src, name, exempt=trimmed)[0])
             for src, name in sources)
```

`any(... for ... in [])` is `False`, so an empty `sources` makes every exemption "needed nowhere":

```
dead_exemptions([])  -> 2 findings (both live exemptions declared DEAD over an EMPTY population)
```

A zero over nothing reported as a finding is the shape §21 and this file's own `:62-63` exist to
refuse. Unreachable from `main` today only because of a check at a distance (`:362-366`) — the
function itself has no CANNOT-RUN guard, and it is public, called from two places, and the thing
H1 above shows is already being handed populations it was not designed for.

**Fix:** `if not sources: return ["CANNOT RUN — deadness judged over an empty population…"]`.

## L3 — the ratchet comment declares 126; the dict holds 124

`scripts/check-fixture-variation.py:108`

> ⛔ 126 PARAMETERS ACROSS 35 FILES ARE ALREADY UNVARIED … They are frozen here BY NAME

Measured: `sum(len(v) for v in KNOWN_UNVARIED.values())` = **124**; `len(KNOWN_UNVARIED)` = 35. The
program's own output line agrees with 124, and the commit message says "124 ratcheted". 126 is the
*total findings measured before exemptions* (126 − 2 exempt = 124) — a correct number attached to
the wrong noun, in the sentence that says what is frozen. This is the declared-count drift class
`check-selftest-counts.py` exists for, in a comment it cannot read.

---

# The attacks that found nothing

Named, so the CONVERGED parts of this round are not merely unexamined.

* **The guard passes its own rule.** `analyse` on `check-fixture-variation.py`: 0 findings,
  8 parameters examined, `EXAMINED_FLOOR` 8 — zero headroom, which is right for a floor. Every
  parameter r7 added or changed is genuinely varied, not textually varied:
  `population_shortfall(found, floor)` takes (47,48), (48,48), (99,7) — r7's "three call sites all
  passing 48" is really fixed; `population(root)` takes the real repo and an empty temp dir;
  `analyse(exempt=…)` is passed at `:506` and `:509` and omitted elsewhere; `main(argv=…)` has
  seven call sites with seven different values. r7 B1 is closed.
* **Can the ratchet hide a NEW finding behind an old key?** The key is `fn.param` scoped to the
  file (`:373`, `:379`). A renamed function produces a new key and fails loudly (measured: renaming
  a ratcheted subject fails; it is the *deletion* direction that is B1). A file renamed out of the
  population fails the `:688` case for the 35 named files. I could not construct a collision that
  was not contrived.
* **Key extraction is sound.** `x.split("\`")[1].replace("(", ".").replace("=…)", "")` at `:379`
  runs only over `analyse`'s two message shapes; the `EXAMINED_FLOOR` message (which also contains
  backticks) is appended after the filter at `:390`, and `dead_exemptions` output after the loop at
  `:401`. No mis-keying is reachable.
* **Ordering of CANNOT RUN vs deadness vs the floor** (`:399-414`) is correct: an unreadable member
  suppresses every deadness verdict, prints what was collected, and takes rc 2; the population
  shortfall takes rc 2 ahead of the rule's rc 1. §21 is satisfied on the population path.
* **`dead_exemptions` any/all at the edges**: one file — correct (`:578`'s case, verified live);
  an exemption whose function exists in two files — correct for deadness, and it is the
  *forgiveness* scope that is wrong (H2), not this.
* **H2 of r7 (the absence-assertion class)** is applied, not just patched. `check-plan-code.py:2055`
  now asserts `(stream, ok, isinstance(ev, Measured))`; in this file the remaining absence
  assertions at `:452`, `:521`, `:668` and `:711` each carry a presence partner on the same
  fixture, and the bare ones at `:457`, `:533`, `:546`, `:558` are each attributable through a
  sibling case on a neighbouring fixture.
* **The `<omitted, default>` synthesis** at `:300-304` only ever adds a value for a parameter that
  *has* a default, so it cannot manufacture variation for a required parameter.

---

# Re-running `--mutate .`

The brief's claim reproduces exactly.

```
$ python3 scripts/check-plan-code.py --mutate .
[1/39] control scripts/brief-compose.py
…
[493/493] …
[39/39] re-control scripts/page_markup.py
OK — delivered scripts mutated: 39 file(s), 493 mutation(s), 493 killed,
493 attributed to the case each names, 0 survivor(s)
rc=0
```

and the declared numbers agree with the manifests:

```
manifest entries, check-fixture-variation.json : 22
EXPECTED_MUTATIONS["scripts/check-fixture-variation.py"] : 22
sum(EXPECTED_MUTATIONS.values()) : 493 over 39 files
```

**On the "exact one" rule:** I did not re-derive it. `check-plan-code.py:1137-1205` implements it —
each `expect` must match exactly one red case, equality not substring, fragments refused — and
`--mutate .` reports `493 attributed to the case each names`, which is that rule passing 493 times.
My own re-implementation of the anchor/expect check disagreed with the harness on six anchors and
two `expect` names; the disagreement was **my** bug (I was reading a working-tree file that had
changed under me, see below), and re-implementing a rule to predict it is the failure mode this
project already has a memory about. The harness is the measurement.

Two `expect` names are each cited by two manifest entries (`a file below its pinned examined floor
fails`, `main() surfaces a dead exemption as a failure`). That is not a violation — the rule
constrains how many *cases* one `expect` matches, not how many mutations may name one case — and
both mutations in each pair are genuinely different edits (`:388-389` floor lookup vs `:389`
comparison; `:401` deadness wiring vs `:417` findings gate vs `:418-421` FAILED branch).

## ⚠ The working tree moved under me mid-review, and every number above was re-taken

At roughly 09:28 — while this review was in progress — `scripts/check-fixture-variation.py` in the
shared working tree was rewritten by another agent (`git diff --stat`: 190 insertions, 78
deletions), and `docs/reviews/verdicts/harness-progress-r8-codex.verdict.json` appeared at 09:22.
The Codex half had landed and its findings were being implemented.

I noticed because a string I had just read stopped being in the file. Per this project's rule that a
result on a shared resource is contamination until re-measured alone, **I rebuilt the subject from
git and re-ran everything:**

```
$ git archive e314c235 scripts | tar -x -C $W/subject
  e314c235: d5708dba21a50eff9391fba4644019d93dc3f4e7
  extracted: d5708dba21a50eff9391fba4644019d93dc3f4e7
  worktree : 11e6f88f60a1b0754d3a2401eb1de5257168f903   <-- NOT the subject
```

Re-run against the pristine `e314c235` blob, in an isolated tree under a redirected `$HOME`:

```
control          : fixture variation OK — 484 parameter(s) across 48 file(s); 124 ratcheted, 2 exempt  rc=0
control          : 38/38 passed                                                                         rc=0
B1 privatisation : 3x ⭐ "now varies — delete it from KNOWN_UNVARIED"; 479 examined                rc=0
H1 single file   : FAILED — 2 parameter(s) never varied by any case (both are live exemptions)     rc=1
H2 name collision: rc=0 with `d` unvaried; rc=1 once renamed `dd`
M1               : 82 of 484 examined params are suite-local helpers, across 22 files; 9 ratchet entries
M2               : 13 of 48 files unpinned by name; 37 of 484 examined params under a floor
B1 disjointness  : floored ['check-fixture-variation.py','check-plan-code.py']; 34 non-empty ratchets;
                   intersection []
L1 posonly       : `def f(a, /, b)` with b=9 at both sites -> 0 findings, 1 examined
L2               : dead_exemptions([]) -> 2 findings
L3               : comment says 126; sum(KNOWN_UNVARIED) = 124 across 35 files
```

Every finding in this review is measured against `e314c235`, which is what the brief scoped. The
`--mutate .` run staged its copy before the edit landed and its anchors all resolved, so 493/493/0 is
also a statement about the subject.

**And the in-flight working tree already addresses most of this**, which is worth saying plainly
rather than letting this read as eight open items:

| finding | working tree at the time of writing |
|---|---|
| B1 debt-paid on a deleted subject | `:464-475` now separates "paid" from "left", citing the same `audit` → `_audit` 17-call-site refactor |
| H1 dead exemptions on a `paths` override | `:494` — `if not cannot and not a.paths:` |
| H2 `EXEMPT` file scope | `:422` — `for src, name in sources if name == kfile` |
| M1 suite-local helpers | `:330` — an added condition on the `defs` filter |
| M2 identity not cardinality | rewritten as a set comparison; `:243` shows `EXAMINED_FLOOR` grown |
| L1 positional-only | `:356` — `fn.args.posonlyargs + fn.args.args` |
| L2 empty `sources` | `:413` — `if not sources:` |

I did not review that work. It is uncommitted, it was moving while I read it, and the brief scopes
this round to `e314c235`. It needs its own round — in particular `dead_exemptions`' new `kfile`
scoping and the identity-based population line are new code that no case existed for an hour ago,
and M2's own lesson is that a fix to a ratchet is where the next Blocking has come from six times.

---

# What I did not measure

* **The other 47 files' suites.** I ran this guard over them; I did not read them. The 124
  ratcheted entries are taken on trust as pre-existing, except for the 9 I identified as
  suite-local helpers (M1).
* **Whether B1's fix is achievable without changing `analyse`'s return type**, and what that does
  to the 22 manifest anchors. I named the shape; I did not implement it or re-run the manifest
  against it.
* **`ast.AsyncFunctionDef`** is not handled at `:261` or `:101`. I did not check whether any of the
  48 scripts defines one — if one did, it would be invisible to both `defs` and `population`.
  Probably vacuous in a synchronous script corpus, but it is unmeasured, not cleared.
* **Two functions with the same name in one file.** `defs.setdefault(node.name, node)` at `:262`
  keeps the first signature for both. I constructed no case; I did not scan the corpus for it.
* **Whether the 484-parameter CI gate changes PR friction.** Every PR touching any of 48 scripts
  now has to satisfy this rule. That is the branch's intent and out of this round's scope, but no
  one has yet paid its cost on a real unrelated change.
* **The uncommitted rewrite in the working tree.** 190 insertions, 78 deletions of new, uncased
  code that landed while this review was running. I read seven lines of it to write the table
  above and nothing else. It is not reviewed by anybody yet.
* **The Codex half.** This is the Claude half only. `docs/reviews/verdicts/harness-progress-r8-codex.verdict.json`
  exists, so the Codex gate ran; I did not read its findings before or while measuring, which is
  why the overlap between its B1 and my M2 — reached through different substitution vectors (it
  made a file unparseable, I renamed a suite function) — is independent agreement rather than an
  echo. `scripts/check-review-rounds.py` currently reports this round as having one half:

  ```
  ✗ harness-progress round 8: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
  ```

  The verdict JSON is present but the Codex review document under `docs/reviews/coordinator/` is
  not. That is the coordinator's step, not mine.

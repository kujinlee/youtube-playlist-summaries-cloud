# Adversarial review — `harness-progress-output`, round 9 (Claude half)

## Verdict: **NOT CONVERGED** — 2 Blocking, 1 High, 3 Medium, 3 Low

**Subject:** `44446ba084c0252855d67a344d0d6ccb3c2aa658` — *"Round 8: the ratchet congratulated you
for deleting its subject"*. Scope: COVERAGE, by explicit human decision. No restructure is proposed
except where a measurement shows it *removes* a defect rather than moving it (Blocking 2).

Both Blockings are **the subject commit's own two Blockings, reproduced against the subject commit**,
each behind one additional three-line edit. Round 8 diagnosed its two findings correctly —

> "The two Blockings are one defect at two levels: a COUNT is preserved by substitution, a KEY is
> preserved by rewriting the file under it. **Both are proxies for identity.**"
> — `44446ba0` commit message

— and then shipped two new proxies for identity: a per-file **count** (`EXAMINED_FLOOR`, widened from
2 files to 48 in this very commit) and a bare **function name** (`known - keys`). Each is defeated the
same way its predecessor was, and in both cases the guard prints the byte-identical headline line
`fixture variation OK — 402 parameter(s) examined across 48 file(s)` and exits 0.

---

## Proof of subject

```
$ git log --oneline origin/master..HEAD
44446ba0 Round 8: the ratchet congratulated you for deleting its subject   <-- SUBJECT
e314c235 Round 7: the guard failed the way it was built to detect
48d8cabb Round 6: ask the fixture question with a script, not with a reviewer
6a660454 Round 5: a fixture must differ from itself along the axis it tests
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git show --stat 44446ba0 | tail -8
 docs/dashboard-entries.md                          |  40 +-
 docs/reviews/claude/harness-progress-r8-claude.md  | 645 +++++++++++++++++++++
 .../coordinator/harness-progress-r8-codex.md       | 111 ++++
 .../harness-progress-r8-codex.verdict.json         |  13 +
 scripts/check-fixture-variation.py                 | 356 +++++++++---
 scripts/check-plan-code.py                         |   4 +-
 scripts/mutations/check-fixture-variation.json     |  97 +++-
 7 files changed, 1168 insertions(+), 98 deletions(-)
```

The subject was staged out of git, **not read from the worktree**, and the blob hash checked:

```
$ git archive 44446ba0 scripts | tar -x -C $T/repo
$ git rev-parse 44446ba0:scripts/check-fixture-variation.py
2ad6cfa90c7daad05fa595d21994a88dec9993bc
$ git hash-object $T/repo/scripts/check-fixture-variation.py
2ad6cfa90c7daad05fa595d21994a88dec9993bc      <-- identical
```

`HARNESS_TREE`'s other four entries (`supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`)
are symlinks to the repo, as the brief specifies. Every probe below ran in a fresh `cp -R` of the
staged tree; nothing in the repo was modified except this file.

### ⚠ The worktree DID move, and none of these numbers came from it

On finishing I re-checked, and the working tree now carries an uncommitted rewrite:

```
$ git status --porcelain
 M scripts/check-fixture-variation.py
 M scripts/check-plan-code.py
 M scripts/mutations/check-fixture-variation.json
$ git hash-object scripts/check-fixture-variation.py   25c0beeb…   <-- worktree
$ git rev-parse 44446ba0:scripts/…                     2ad6cfa9…   <-- my subject
```

377 lines changed in the main subject file. **Every measurement above was taken against `2ad6cfa9`
in `/tmp`, not against the worktree** — that was the point of staging from `git archive` at the start
rather than discovering the drift late.

Reading that rewrite: `EXAMINED_FLOOR` has been replaced by `EXAMINED_KEYS: dict[str, tuple[str, ...]]`
— a per-file key **set**, which is Blocking 2's recommended fix — and a comment at `:223-226` reads
*"a replacement function with the same name AND the same signature is indistinguishable … twice and
r9 refuted twice"*, so Blocking 1's class is being addressed too. `known - keys` at `:637-639` is
still name-keyed in that draft.

**Two things follow, and they matter for how this document is used.** First, these findings are
recorded against `44446ba0`, the commit I was given; they are not a claim about the uncommitted
rewrite, which I have not reviewed and which is not yet under any gate. Second, I did **not** read
`docs/reviews/coordinator/harness-progress-r9-codex.md` before or during measuring — I checked only
`…/verdicts/harness-progress-r9-codex.verdict.json` (`gate_ran: true`, gpt-5.5, 4536 chars) after
finishing — so wherever this half and the Codex half agree, that is independent corroboration rather
than an echo.

## Control, proved green FIRST

```
$ python3 scripts/check-fixture-variation.py --self-test
44/44 passed                                                                   rc=0

$ python3 scripts/check-fixture-variation.py
fixture variation OK — 402 parameter(s) examined across 48 file(s);
115 known-unvaried ratcheted, 2 exempt with a written reason                   rc=0

$ python3 scripts/check-plan-code.py --self-test
128/128 passed                                                                 rc=0
```

All three match the commit's claims exactly. **Round 8's own two falsifiers also still hold** — I
re-ran them rather than trusting the commit message:

| Round 8 falsifier | Result on `44446ba0` |
|---|---|
| privatise `audit` → `_audit` in `check-anchors.py` (19 substitutions) | rc 1, **three `NO LONGER EXAMINED` findings, zero gold stars** ✅ |
| `check-docs.py` unparseable **and** one new script added | rc 2, names *both* the departure and the arrival ✅ |
| pure departure (delete a script) / pure arrival (add one) | rc 2 each, correctly named ✅ |

So the fixes work against the exact inputs they were written for. Everything below is one edit
further out.

**And the guard passes its own rule cleanly** — brief question 5. Measured: `check-fixture-variation.py`
contributes 8 keys covering **all five** of its public module-level functions, including everything
round 8 added, with zero findings, zero ratchet entries and zero exemptions of its own:

```
analyse.exempt  analyse.path  analyse.source  dead_exemptions.sources
main.argv  population.root  population_drift.found  population_drift.pinned
```

The third `population_drift` case at `:798` (a differently-ordered pinned set) is genuinely
load-bearing, and I measured that rather than taking the comment's word for it — deleting that one
case and re-running the guard **on itself**:

```
FAILED — 2 parameter(s) never varied by any case:
  ✗ … `population_drift(found=…)`  … (2x `['a.py', 'c.py']`)
  ✗ … `population_drift(pinned=…)` … (2x `['a.py', 'b.py']`)
rc=1
```

That is the guard catching its own author, which is the thing it exists to do.

---

# ⛔ BLOCKING 1 — `known - keys` treats a NAME as identity, so reusing the vacated name restores the gold stars

**`scripts/check-fixture-variation.py:469-475`**

```python
for gone in sorted(known & keys - seen_known):
    paid.append(f"{t.name}: `{gone}` now varies — delete it from KNOWN_UNVARIED")
for lost in sorted(known - keys):
    all_findings.append(... "is ratcheted but NO LONGER EXAMINED" ...)
```

`keys` is `{f"{fn}.{param}" ...}` (`:389`) where `fn` is `node.name` (`:332`). The set records **a
name, not a function**. `known - keys` therefore asks *"is there still something called `audit` with
a parameter `shared_rel`?"* — not *"is the function we ratcheted still examined?"*

### Measured — the subject commit's headline defect, reproduced verbatim

Round 8's B1 was: *"renaming one public function to `_private` took three parameters out of the
guard's field of view and earned three gold stars."* Here is that, on `44446ba0`, plus one decoy
function reusing the vacated name:

```python
# scripts/check-explainer-delivery.py
re.sub(r'\baudit\b', '_audit', t)                     # the real audit() leaves the field of view
+ def audit(page_skills, shared_rel, skills_dir):     # decoy under the vacated name
+     return page_skills
  def self_test() -> int:
+     audit(1, 2, 3); audit(4, 5, 6)                   # varied, so nothing fires
```

```
$ python3 scripts/check-fixture-variation.py
  ⭐ check-explainer-delivery.py: `audit.shared_rel` now varies — delete it from KNOWN_UNVARIED
  ⭐ check-explainer-delivery.py: `audit.skills_dir` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — 402 parameter(s) examined across 48 file(s); 115 known-unvaried
ratcheted, 2 exempt with a written reason
rc=0
```

**The headline number is byte-identical to the control.** The real `audit` — the function both ratchet
entries were written about — is now private and unexamined. The guard misses it, and then
**instructs the reader to delete the two ratchet entries**, which retires the debt permanently. Three
lines of diff away, without the decoy:

```
FAILED — 3 parameter(s) never varied by any case:
  ✗ check-explainer-delivery.py: `audit.shared_rel` is ratcheted but NO LONGER EXAMINED …
  ✗ check-explainer-delivery.py: `audit.skills_dir` is ratcheted but NO LONGER EXAMINED …
  ✗ check-explainer-delivery.py: 0 parameter(s) examined, below the pinned floor of 3 …
rc=1
```

A weaker form needs no privatisation at all. Renaming `audit` → `inspect` and adding a *new, unvaried*
`audit(page_skills, shared_rel, skills_dir)` swallows **2 of the 3 new gaps** — only
`audit.page_skills` fires, because that key alone was not already ratcheted:

```
  ✗ … `audit(page_skills=…)` is passed the SAME value …    <-- the only one of the three NEW gaps
  ✗ … `inspect(shared_rel=…)` …                            <-- the renamed original
  ✗ … `inspect(skills_dir=…)` …
```

A brand-new function inherits a debt excuse written about a different function of that name. This is
**r8 H2's own defect** (`EXEMPT` had no file scope, so an excuse written about one script silenced all
48) one level down: `KNOWN_UNVARIED` has a *file* dimension but no *function-identity* dimension.

### Falsifier for the fix

`analyse` must return enough to tell one `audit` from another — a signature fingerprint (sorted
parameter names + arity), or the def's line number — carried beside the key, and `known - keys` must
compare that. The falsifier is the decoy above: it must produce `NO LONGER EXAMINED` and **no gold
star**. Note the case at `:826-828` already asserts *"and no gold star"* for the plain privatisation;
the decoy variant has no case at all.

---

# ⛔ BLOCKING 2 — `EXAMINED_FLOOR` is a per-file COUNT, and this repo has already written down why that fails

**`scripts/check-fixture-variation.py:223-272, 478-484`**

Codex B1 of round 8 was, in the commit's own words: *"THE POPULATION WAS PINNED BY COUNT, AND A COUNT
IS PRESERVED BY SUBSTITUTION."* The fix replaced the population count with a name **set**
(`population_drift`, `:77`). In the same commit the per-file coverage pin was widened from 2 files to
all 48 — and it is a **count**:

```python
floor = EXAMINED_FLOOR.get(t.name)
if floor is not None and n < floor:            # n = len(keys)
```

`n` is a cardinality, so *within* one file a departure and an arrival cancel out exactly as they did
at the population level. The exposure is the majority of the coverage: measured, **402 keys, of which
115 are ratcheted by name**, so **287 keys (71%) are pinned by nothing but this count**. That is the
healthy, varied coverage — precisely what r7 H1 built the floor to protect, since ratcheting only ever
names the *unhealthy* parameters.

### Measured

`check-handoff-path.py` examines 2 keys: `check_file.path` (healthy, **not** ratcheted) and
`check_text.text` (ratcheted). Privatising `check_file` removes a whole public function from the
guard's view. Step B is the floor working; step C adds a three-line decoy:

```python
re.sub(r'\bcheck_file\b', '_check_file', t)   # a public, exercised function leaves the population
+ def filler(z):                              # 1 key, fully varied, restores the count
+     return z
  def self_test() -> int:
+     filler(1); filler(2)
```

```
# STEP B — privatisation alone
FAILED — 1 parameter(s) never varied by any case:
  ✗ check-handoff-path.py: 1 parameter(s) examined, below the pinned floor of 2 …    rc=1

# STEP C — privatisation + decoy
fixture variation OK — 402 parameter(s) examined across 48 file(s); 115 known-unvaried
ratcheted, 2 exempt with a written reason                                            rc=0
```

Again byte-identical to the control, over a different key set. No `LOST` finding can fire, because
`check_file.path` was never ratcheted — the identity mechanism r8 B1 added covers 115 keys and
structurally **cannot** cover the other 287.

I checked the floors are not merely loose: measured, **every one of the 48 floors is exactly equal to
today's coverage** — zero slack anywhere. The defect is not a sloppy floor, it is the choice of
cardinality.

### ⭐ This argument is already written down in the sibling file, in this commit's own tree

`scripts/check-plan-code.py:868-873`, unchanged by this commit:

> ```
> # ⟲ IDENTITY, not just cardinality. EXPECTED_MUTATIONS pins HOW MANY entries a
> # script has; on its own that is satisfied by replacing one entry with a copy of
> # another — count unchanged, coverage silently narrowed. Found in branch review
> # by Codex, reproduced: entry 32 swapped for a duplicate of entry 1, still green.
> # This is the same error as asserting a threshold's presence instead of measuring
> # the ratio: a proxy for the property rather than the property.
> ```

The pattern was named, reproduced, and guarded against for mutation manifests — and `EXAMINED_FLOOR`
was shipped as a bare count 500 lines away in the same commit.

### Falsifier for the fix, and why it is a *reduction* in machinery

Pin the per-file **key set**, the way `population_drift` already pins the file-name set. Step C then
reports `check-handoff-path.py: check_file.path no longer examined; filler.z new and unpinned`. That
also subsumes Blocking 1 for every ratcheted key and **removes `EXAMINED_FLOOR` as a separate
mechanism** — one pinned set replaces a 48-entry count dict plus a 115-entry name dict's identity
half. Cost, stated honestly: the pinned set is ~402 lines instead of 48, and every legitimate
refactor edits it. That is the same bargain `KNOWN_UNVARIED`'s 115 entries already made, and it is the
only restructure this review proposes — offered because it deletes a mechanism rather than adding one.

---

# H1 — the case carrying the deadness mutation is falsifiable only while the whole repo is green

**`scripts/check-fixture-variation.py:679-698`**, and
`scripts/mutations/check-fixture-variation.json` entry *"dead exemptions are computed and dropped
instead of joining the findings"*.

The case `main() surfaces a dead exemption as a failure` drives `main([])` over the **live 48-file
population** and asserts `rc == 1`. `main` returns 1 whenever `all_findings` is non-empty — from *any*
file, for *any* reason. So the case distinguishes the deadness aggregation from its absence only while
every other script in the repo is clean.

Round 8 saw this hazard and fixed one instance of it, at `:691-693`:

> "⚠ THE REAL EXEMPTIONS STAY. Replacing them outright made their parameters fire as ordinary
> findings, so `main` returned 1 for a reason that had nothing to do with deadness and the case
> passed with the deadness aggregation deleted."

The class is diagnosed exactly, and only the reviewer's own fixture was fixed. Any *other* source of a
finding does the same thing — instance, not class.

### Measured — the mutation survives

The manifest's own edit (`all_findings += dead_exemptions(sources)` → `pass`), applied to an
otherwise-untouched tree, versus the same tree plus **one** unrelated unvaried parameter added to
`check-arch-findings.py`:

| mutation | pristine repo | repo with one unrelated finding |
|---|---|---|
| `dead exemptions are computed and dropped…` | **43/44** — named case RED | **44/44 — SURVIVES** |
| `the findings gate is short-circuited…` | 40/44 | 40/44 (killed by 3 other cases) |
| `the FAILED branch returns 0…` | 40/44 | 40/44 (killed by 3 other cases) |

Three of the 27 entries name this one case; it is the only case that *uniquely* attributes the first
of them, so exactly one mutation goes silent. The coupling runs the wrong way: the case weakens
precisely when the population is unhealthy, which is when the guard matters.

**Fix:** assert on the deadness *text* rather than on `rc` — `"is DEAD" in stderr` — which is what the
neighbouring case at `:777` already does correctly for the CANNOT-RUN path.

---

# M1 — an EXEMPT parameter that is also ratcheted earns a permanent FALSE gold star

**`scripts/check-fixture-variation.py:378-389, 456-470`**

`seen_known` is populated only from emitted findings (`:461`), and `:380` suppresses the finding for
an exempt parameter *before* it is ever emitted. So an exempt-and-ratcheted key lands in
`known & keys - seen_known` and is reported as debt paid.

This is r8 B1's defect a third time. "No finding for a ratcheted key" has **three** causes, and round 8
partitioned only two of them:

| cause | reported as | correct? |
|---|---|---|
| the parameter started varying | ⭐ paid | ✅ |
| the key left the field of view | `NO LONGER EXAMINED` (r8's fix) | ✅ — unless the name is reused (**Blocking 1**) |
| **the finding was suppressed by `EXEMPT`** | ⭐ paid | ❌ **false** |

### Measured

Adding one line to `KNOWN_UNVARIED` duplicating a live `EXEMPT` key:

```python
KNOWN_UNVARIED: dict[str, tuple[str, ...]] = {
+   'check-plan-code.py': ('diagnostic_tail.window',),
```

```
  ⭐ check-plan-code.py: `diagnostic_tail.window` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — 402 parameter(s) examined across 48 file(s); 116 known-unvaried …   rc=0
```

`diagnostic_tail.window` does **not** vary — the exemption at `:284` says so in writing ("callers
never pass it"). The guard asserts a cause it never measured, which is the exact sentence round 8
wrote about its own B1, and it tells the reader to delete a ratchet entry. Latent today (the two
`EXEMPT` keys do not appear in `KNOWN_UNVARIED`), and nothing refuses the overlap. **Fix:** either
refuse an overlap between the two dicts outright, or compute `paid` from *varied values* rather than
from the absence of a finding.

# M2 — adding one script makes the guard's own `--self-test` fail with two unactionable messages, one collateral

**`:885-886`, `:697-698`.** Brief question 4. Measured, adding one new `scripts/check-newthing.py`
that defines a suite:

```
$ python3 scripts/check-fixture-variation.py
  CANNOT RUN — the population is not the pinned set (newly discovered and unpinned:
  check-newthing.py). … Update EXAMINED_FLOOR deliberately. NOT CHECKED.          rc=2
```

That message is good: it names the file and the action. The self-test is not:

```
$ python3 scripts/check-fixture-variation.py --self-test
  [FAIL] main() surfaces a dead exemption as a failure: got 2 want 1
  [FAIL] every discovered file has a pinned examined floor, and vice versa: got False want True
42/44 passed
```

Neither line names the new file or the remedy, and the first is **collateral** — nothing to do with
dead exemptions; it fails because `main([])` now returns 2 (drift) instead of 1. Same world-coupling as
H1, surfacing as a misleading failure rather than a survived mutation. Round 8's comment at `:904-906`
made these cases unconditional so the case *count* would not vary with the state of the world; the
case *outcomes* still do.

# M3 — `analyse`'s docstring says "module level"; the code says "anywhere except the suite"

**`:301-302`** claims *"A parameter is EXAMINED when its function is defined at module level and called
from the suite."* The code walks the whole tree (`:329-332`) and excludes only defs inside the suite,
so class methods and functions nested inside other functions enter `defs` too.

Measured across the population: **22 such defs in 11 files** — e.g. `handle_data` in
`brief-compose.py`'s `_DocScan`, `do_GET`/`do_POST` in `explainer-serve.py`'s `Handler`, `sub` inside
`build-m4-schema.py:apply_edits`. **None produces a key today** and none is ratcheted — I checked both
— so this is latent. It matters because it is a second route into Blocking 1's mechanism: a class
method named `audit` would satisfy `known - keys` for a module-level `audit` that has gone away.
Either narrow the scan to `tree.body`, or correct the docstring and say why methods count.

# L1 — a key can name something that is not a parameter, via `**kwargs`

**`:363-365`** records `seen[(fn.name, kw.arg)]` for every keyword argument **without checking
`kw.arg` is in the signature**. For a function with `**kwargs` that is legal Python, so
`f(a=1, anything=2)` mints the key `f.anything` and inflates `n` — the quantity Blocking 2 shows is
fungible. Measured: **zero fabricated keys in the live population**, and the three public defs with
varargs (`explainer-serve.py:log_message`, `gen-backlog-page.py:git`, `verify-exclusion-reasons.py:sh`)
all take `*args`, which is dropped rather than recorded because `:359-361` bounds the index by
`len(names)`. Latent.

# L2 — a duplicate public `def` resolves to the first one, and there is one on disk

`defs.setdefault(node.name, node)` (`:332`) keeps the **first** definition `ast.walk` reaches; Python
keeps the last. Measured: `scripts/brief-compose.py` defines `markup_of` twice at module level, at
`:218` and `:362`. Harmless today — identical signatures, and `brief-compose.py` contributes 0 keys —
but two same-named defs differing in signature would map positional arguments by index against the
*wrong* parameter list, which is r8 L1's `posonlyargs` failure arriving by another door. (The
duplicate itself is pre-existing, not introduced by `44446ba0`.)

# L3 — the commit message's M1 number disagrees with the code comment and with its own arithmetic

The commit message says *"84 OF THE 484 'PARAMETERS EXAMINED' WERE THE SUITES' OWN FIXTURES"*. The
code comment at `:323-324` says **82**. Measured by re-running the r7 (`e314c235`) guard over the same
tree: **484 examined at r7, 402 at the subject — a drop of 82.** The code is right and the commit
message is the drifted copy. In a project that runs `check-selftest-counts.py` for exactly this class
of drift, a wrong number in the commit message is what the next reader quotes.

---

## What I confirmed is NOT a defect

Stated so round 10 does not re-attack them:

- **`population_drift` semantics** (`:87-97`) — re-measured: pure departure, pure arrival, and a swap
  each report correctly and name both directions; the same set in a different order is **not** drift.
- **rc 2 for an arrival** (brief question 2). Defensible: the guard genuinely has not checked a file
  nobody pinned a floor for, and the exit code is non-zero, so nothing turns green. The only cost is
  that real findings in the other 48 files are withheld until the floor is pinned — a reporting
  inconvenience, not a false pass.
- **Basename collision in `population_drift`** — unreachable: `population()` globs exactly one
  directory (`:104`), so two files cannot share a basename.
- **`EXAMINED_FLOOR` slack** — measured, all 48 floors sit exactly at today's coverage.
- **`posonlyargs`, keyword-only, omitted defaults** — re-measured, all three behave as the cases claim;
  r8 L1's `/` fix is correct.
- **Decorators** — a decorated `def` is still an `ast.FunctionDef` with its own name, so it neither
  hides a function nor mints a key. (`async def` *is* invisible to `isinstance(n, ast.FunctionDef)`,
  but it only ever *removes* keys, which the floor and `known - keys` both catch.)
- **`EXEMPT` file-scoping (r8 H2) and scoped deadness** — both re-driven; correct.
- **The guard against itself** — 8 keys, 5/5 public functions covered, no findings, no exemptions.
- **Neighbouring guard suites** — `check-selftest-counts` 9/9, `check-ratchet-contract` 22/22,
  `check-guard-coverage` 16/16, `check-docs` 13/13, all rc 0.

## Round 8's own open items, now closed

Round 8's *What I did not measure* listed four things. Two are now measured, so they need not be
carried forward:

- **`ast.AsyncFunctionDef`** — *"I did not check whether any of the 48 scripts defines one."*
  Measured: **zero** `AsyncFunctionDef` nodes anywhere under `scripts/`. Cleared, not presumed. And
  the failure mode would be benign anyway: an async def only ever *removes* keys, which both
  `EXAMINED_FLOOR` and `known - keys` catch.
- **Two functions with the same name in one file** — *"I constructed no case; I did not scan the
  corpus for it."* Scanned: exactly one instance, `brief-compose.py:markup_of` at `:218` and `:362`
  (**L2** above). Harmless today; the mechanism is real.

Still open from round 8, and not advanced by me: whether B1's fix is achievable without changing
`analyse`'s return type, and whether the 48-script CI gate changes PR friction on an unrelated change.

## What I did NOT measure

- **The other gates.** I ran four guard `--self-test`s above; the commit's claim that *all six* gates
  are green is **unverified by me**. Treat it as not checked.
- **Whether Blocking 1 or 2 has ever actually happened in this repo's history.** Both are demonstrated
  *capabilities* of the guard, not observed incidents.
- **Runtime cost** of the per-file key-set fix on a 48-file population.
- **The feature itself** (`7ae516fc`, the progress reporter). Nothing in this round touched it; eight
  rounds of findings have all been about the guards built around it.

## `--mutate .` — re-run, and the claim holds exactly

Brief question 6. Run from the staged subject tree with a complete `HARNESS_TREE` and a redirected
`$HOME`:

```
$ HOME=/tmp/r9home python3 scripts/check-plan-code.py --mutate .
[1/39] control scripts/begin-plan.py
…
[131/498] the variation rule accepts a single distinct value …      <-- the guard's 27 entries,
…                                                                        contiguous at 131–157
[157/498] deadness is judged over every file rather than the one its exemption names …
…
[13/39] re-control scripts/check-fixture-variation.py
OK — delivered scripts mutated: 39 file(s), 498 mutation(s), 498 killed,
498 attributed to the case each names, 0 survivor(s)
rc=0
```

**39 / 498 / 498 / 498 / 0, exit 0 — identical to the commit's claim.** A control was proved green
for every file before mutation and a re-control after, including for
`scripts/check-fixture-variation.py` itself (`[13/39]` in both passes). All 27 of the guard's
manifest entries ran and every one attributed under the exact-one rule, which
`check-plan-code.py:1203-1205` enforces directly — I did not re-implement that check.

⚠ **This is exactly why H1 matters.** The harness measures the manifest against a **pristine** tree,
which is the one condition under which the *"dead exemptions are computed and dropped"* mutation is
killable. A green `498 attributed` is therefore not evidence that entry is attributable in general —
it is evidence that it is attributable *today*. Nothing in the harness can see that distinction,
because the harness itself is the thing that establishes the pristine control.

---

## Summary for the coordinator

| # | Severity | One line |
|---|---|---|
| B1 | ⛔ Blocking | `known - keys` compares a NAME, so a decoy function under the vacated name restores the false gold stars — r8 B1 reproduced, rc 0 |
| B2 | ⛔ Blocking | `EXAMINED_FLOOR` is a per-file COUNT, defeated by substitution; 287 of 402 keys have no identity pin — r8 Codex B1 reproduced one level down, rc 0 |
| H1 | High | The deadness case asserts `rc==1` over the live population, so 1 of 27 mutations survives once any unrelated finding exists |
| M1 | Medium | An `EXEMPT` parameter that is also ratcheted earns a permanent FALSE gold star (the third cause of a missing finding, still unpartitioned) |
| M2 | Medium | Adding one script fails the guard's own `--self-test` with two unactionable messages, one collateral |
| M3 | Medium | `analyse`'s docstring says "module level"; the code accepts any def outside the suite — 22 live instances, all currently key-free |
| L1 | Low | `**kwargs` can mint a key for a parameter that does not exist; zero live instances |
| L2 | Low | A duplicate public `def` resolves to the first; one instance on disk (`brief-compose.py:markup_of`) |
| L3 | Low | The commit message says 84 suite-local parameters; the code comment and the arithmetic both say 82 |

B1, B2 and M1 are one root: **`paid` is computed from the absence of a finding, and identity is
approximated by a name or a count.** A single change — pinning the per-file **key set** instead of its
cardinality, with keys carrying a signature fingerprint — closes all three and deletes
`EXAMINED_FLOOR` as a separate mechanism.

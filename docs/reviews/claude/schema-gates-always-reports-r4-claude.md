# Round 4 — Claude adversarial half, `schema-gates-always-reports` (backlog #137)

## Subject, confirmed by execution

```
$ git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short
schema-gates-always-reports
72f3aefa59b8a9df065cc3681a4412e1f2540eef
(clean)

$ git log --oneline -3
72f3aefa A gate caught what round 4's reviewer did not: the parameter was never varied
1fe926a9 r3 claude: the asymmetry my retreat rested on was false, and I had invented its confirmation
2ec4d072 r3 codex: 2 Lows, both prose — the thrashing question answered with evidence
```

I read **`72f3aefa`**. ⚠ The r4 **codex** half read `1fe926a9` — one commit earlier, and specifically
the commit *before* the fix it failed to find. Its merge-safety sentence names `1fe926a9`, so it is
not a statement about the tree that merges.

---

## Verdict and shape — read this before the count

**NOT CONVERGED** — 0 Blocking, 0 High, 7 Low.

**Nothing I found changes an answer the shipped gate gives.** Every finding is a missing falsifier or
a wrong number in prose. I attacked the code paths hardest and they held: the two second-attempt
fixes (`prose_exceptions_cover`'s varied parameter, `_path_of`'s literal byte lengths) are both
correct and I re-derived them independently rather than reading the commit message. The eleven module
constants are pinned to the byte. The workflow is right about the thing it newly claims.

**The one structural result worth the round:** the shape `check-fixture-variation.py` caught in
`72f3aefa` **is still live twice more**, and both instances are invisible to that gate by
construction — one because it is declared in the gate's own ratchet (`KNOWN_UNVARIED`), one because
it is a *want* computed from the subject rather than a parameter. The commit message says the fix was
"cosmetic" because a parameter that receives one value is a constant wearing a signature; the same
sentence is true of `verdict.pr_body` at `:703`, in the same file, today. This is the project's own
recorded *after fixing, SEARCH for the class*.

**Severity discipline:** I considered Medium for Low 3 and Low 4 and declined both. Neither produces a
wrong gate answer, and both fail in the **noisy** direction. I am not inflating a final round.

---

## LOW 1 — `verdict.pr_body` is a constant wearing a signature: the exact shape `72f3aefa` exists to close, still live in the same file

**VERIFIED.** `scripts/check-review-recorded.py:677` (signature), `:703` (`reason = reason_of(pr_body)`).
**ORIGIN: (b) pre-existing** — `verdict`'s body is byte-identical to master `93c815c8` (checked by
`ast.unparse` comparison, not by eye). The branch did not introduce it and did not close it.

Every one of the eight case call sites passes the empty string:

```
$ grep -n "verdict(" scripts/check-review-recorded.py | grep -v "def \|antidrift\|tail_\|classify_"
1344:    case("a docs-only branch owes nothing", verdict(DOCS, [], "", none_reason)[0], 0)
1345:    case("a code branch with no review FAILS", verdict(CODE, [], "", none_reason)[0], 1)
1346:    case("...and the failure names the file", ... verdict(CODE, [], "", none_reason)[1], True)
1348:         verdict(CODE, ["docs/reviews/claude/x-r1-claude.md"], "", none_reason)[0], 0)
1350:         verdict(CODE, [], "", reason("typo in a comment")), (0, "NO-REVIEW: typo ...
1352:    case("an EMPTY NO-REVIEW: is refused", verdict(CODE, [], "", reason(""))[0], 1)
1356:         "no reason after it" in verdict(CODE, [], "", reason(""))[1], True)
1359:         verdict(["docs/reviews/claude/x-r1-claude.md"], [...], "", none_reason)[0], 0)
1631:         verdict(CODE, ["docs/notes.md"], "", none_reason)[0], 1)
```

The reason is injected through the `reason_of` lambda instead, so `pr_body` is inert in every case.
Executed, against a control proved green first:

```
CONTROL:                                              (0, '184/184 passed')
  verdict: reason_of(pr_body) -> reason_of('')     -> SURVIVED  [184/184 passed]
```

And `--mutate .` is blind to it too — no entry in the 64 mentions either symbol:

```
$ python3 -c "import json;d=json.load(open('scripts/mutations/check-review-recorded.json'));
             print([e['name'] for e in d if 'reason_of' in json.dumps(e) or 'pr_body' in json.dumps(e)])"
[]
```

**Concrete failure scenario.** The clause that carries the PR body into the declaration parser has no
observer. A refactor that drops or hardcodes the threading leaves the suite at 184/184 and the
manifest at 64/64 killed; the gate then stops reading `NO-REVIEW:` declarations and **fails every
code branch that declared one**. That direction is **noisy** — a wrongly-blocked PR, not a silent
pass — which is the only reason this is Low rather than Medium.

**It is declared, and that is the honest half of the picture.** `check-fixture-variation.py` names it
in `KNOWN_UNVARIED` under `check-review-recorded.py`, so the gap is ratcheted in writing rather than
hidden. What the branch did not do is *search the file it was fixing*: `72f3aefa` closed
`prose_exceptions_cover.declared` and left the only other entry for the same file untouched.

**Observation that proves it fixed:** one case passing a real body —
`verdict(CODE, [], "NO-REVIEW: docs only", lambda b: reason_of(b, NO_REVIEW))` — so `pr_body` varies
across call sites and the threading acquires a falsifier; plus a manifest entry on `:703`.

---

## LOW 2 — a case whose WANT is computed from the subject is silent on the exact policy its name claims

**VERIFIED.** `scripts/check-review-recorded.py:1832-1833`.
**ORIGIN: (b) pre-existing** — present verbatim on master `93c815c8` (r14's work).

This is the **only** one of the file's 165 static `case()` calls whose `want` expression references a
subject symbol. Derived mechanically rather than by reading:

```python
# AST over self_test: for each case(name, got, want), does `want` name a module-level symbol?
=== WANT references a SUBJECT symbol (1) ===
 1833 '...so the two questions cannot disagree about what a rename i
        want=diff_argv('abc123', added_only=True)[:4]
        subject symbols: ['diff_argv']
```

Both sides read the same list object — `args = ["diff", "--name-only", "-z", "--no-renames"]`, with
`added_only` appending only at index 4 — so the assertion is about the prefix's **length**, never its
**contents**. Executed, the case is silent on the policy it is named for:

```
### --no-renames -> --renames (WRONG rename policy, prefix length UNCHANGED)   rc=1 [181/184]
   FAIL: the diff asks git NOT to pair a deletion with an addition: got False want True
   FAIL: ...which is what stops a guarded file renamed into docs/ from disappearing entirely
   FAIL: the ADDED-only question asks the same way, plus the status filter
>>> did the "cannot disagree about what a rename is" case fire?  False
```

And it is **never a unique falsifier** — the only mutation class it catches also kills two
literal-pinned neighbours:

```
### drop `-z` from the shared prefix (length 4 -> 3)     target fired: True  | cases fired: 3
### append a 5th element to the shared prefix            target fired: False | cases fired: 2
```

**Concrete failure scenario.** None to the shipped gate — the two neighbouring cases pin both argv
lists against literals, so the rename policy *is* guarded. The defect is that this case contributes a
name and a count to the declared 184 while being incapable of independently failing, and its name
asserts a guarantee ("the two questions cannot disagree about what a rename is") that it does not
provide. A future edit that weakened the two literal cases would leave this one reading as cover.

**Why `check-fixture-variation.py` cannot see it:** that gate compares the **source text of arguments
at call sites**. Here both sides are calls in the `want` position, not parameters, so the file passes
the gate with this shape intact. Its own docstring names this class — *"r2 the WANT was derived from
the subject"* — as one it was built after, not one it detects.

**Observation that proves it fixed:** the case asserts a literal (`diff_argv("abc123")[:4] ==
["diff", "--name-only", "-z", "--no-renames"]`), or it is deleted as redundant with `:1829-1832`.

---

## LOW 3 — r3 Medium 5b's fix is unfalsified, carries no manifest entry, and is the one clause of four the branch did NOT document as such

**VERIFIED.** `scripts/check-review-recorded.py:1282-1286`.
**ORIGIN: (a) fix-induced** — this local **is** the r3 Medium 5b fix.

```python
def _is_file(rel: str) -> bool:
    try:
        return (ROOT / rel).is_file()
    except (OSError, ValueError):
        return False
```

Both mutations survive, against a control proved green first:

```
CONTROL:                                              (0, '184/184 passed')
  _is_file: swallow-clause removed (re-raise)      -> SURVIVED  [184/184 passed]
  _is_file: narrowed to OSError only               -> SURVIVED  [184/184 passed]
```

No manifest entry reaches it either:

```
_is_file    -> 0 entry(ies)      OSError -> 0 entry(ies)      ValueError -> 0 entry(ies)
```

It is a local inside `main`, so the pure suite cannot reach it at all — `gate_code_dirs` takes an
`is_file=` injection, but the *wrapper that supplies the swallow* is not injectable.

**Sibling, same class, same commit range, found by sweeping every `if` in the file's 39 non-`main`
functions and mutating each condition to `True` and to `False`:** `_gate_sources:639`
(`not runner_path.is_file()`) and `:646` (`p.is_file()`) both survive, because the cases call
`_gate_sources()` against the **real tree**, where the runner and every named script exist. That is
*a case can pass for an AMBIENT reason*, in code this branch introduced.

**Concrete failure scenario.** Removing the swallow restores the `ENAMETOOLONG` crash inside `main`'s
derivation on macOS with Python ≤3.12 — the unattributable-kill shape that was this branch's r2
headline — and nothing in 184 cases or 64 mutations would say so. Direction is a **loud crash**, not a
fail-open, which is why this is Low.

**Why it is filed at all: the branch is inconsistent with itself.** r3 Low 8's three inert clauses
were each given a written note saying they are prospective, unfalsifiable, and deliberately carry no
mutation entry (`:249-254`, `:580-583`, `:437-441`). That is exactly the right treatment. The fix
written in the *same round* got none of it. ⚠ And codex's r4 half reported *"I also checked the
`_is_file` exception behavior with a fixture"* — with **its own** fixture. That is a statement about
the code, not about the suite, and the suite is what ships.

**Observation that proves it fixed:** `_is_file` is lifted to module level and driven by a case whose
`stat` raises, or it carries the same written "cannot receive its input from a case" note the other
three clauses got.

---

## LOW 4 — r3 Low 6 is HALF fixed: the tuple half landed, the fallback half did not — the third round running in this lineage

**VERIFIED.** `scripts/check-review-recorded.py:221` (the root-`.md` fallback), case at `:1374-1375`.
**ORIGIN: (a) fix-induced** — the *code* is unchanged from master; the fix was a case, and the case
covers one of the two halves the finding named.

r3 Low 6's "observation that proves it fixed" named both halves explicitly:

> `guarded_changes([".gitignore"]) == []` (isolates the tuple) **and** `guarded_changes(["NOTICE.md"])
> == []` for a root `.md` outside the tuple (isolates the fallback).

Only the first was added. Executed:

```
CONTROL:                                              (0, '184/184 passed')
  PROSE_FILES loses `.gitignore` only              -> killed    [183/184]   <- FIXED
      [FAIL] .gitignore is prose — the only PROSE_FILES member the root-.md fallback cannot catch
  is_prose: PROSE_FILES branch deleted             -> killed    [183/184]   <- FIXED
  is_prose: root-.md FALLBACK -> return False      -> SURVIVED  [184/184]   <- NOT FIXED
```

No manifest entry covers the fallback in the `False` direction either (the one entry naming it
mutates it to `return True`).

**Concrete failure scenario.** The fallback is the clause that makes a *new* root-level Markdown file
prose. With it silently removed, adding `CHANGELOG.md` at the repository root makes that file
guarded, and a branch touching only it is told it owes a review round. Noisy direction, hence Low.

**The lineage is the point.** r2 Low 7 asked for the `.gitignore` case → reported fixed, was not →
r3 Low 6 found that and *also* found the fallback half → the `.gitignore` half is now genuinely fixed
and the fallback half is not. Three rounds, the same finding, each round closing the half the previous
round had named first.

**Observation that proves it fixed:** `case("a root .md outside PROSE_FILES is prose",
guarded_changes(["NOTICE.md"]), [])`, plus a manifest entry mutating the fallback to `return False`.

---

## LOW 5 — `docs/backlog.md` row 137's self-test count is stale for the FOURTH time, and the row carries two copies of the wrong number

**VERIFIED.** `docs/backlog.md:165`.
**ORIGIN: (a) fix-induced by `72f3aefa`**, which took the suite 182 → 184 and did not touch the row.

```
$ python3 scripts/check-review-recorded.py --self-test | tail -1
184/184 passed
$ grep -o "manifest 43→64, total 714→735, self-test 139→182" docs/backlog.md   # 1 hit
$ grep -o "Self-test 139→182\." docs/backlog.md                                # 1 hit
```

Manifest **64** ✓ and total **735** ✓ are correct; **self-test 182** is wrong, and appears twice in
the one row. The chain on this branch:

| Round | Row said (self-test) | Shipped | Status |
|---|---|---|---|
| r1 Medium 11 | 139→148 | 153 | filed, fixed |
| r2 (not filed) | 139→157 | 166 | stale again, unnoticed |
| r3 Medium 3 | 139→157 | 178 | filed, fixed to 182 |
| **r4 (here)** | 139→182 | **184** | stale by 2, in two places |

**This is disclosed, and the disclosure is why it stays Low.** The row says of itself: *"the durable
copies are the pins a gate checks (`EXPECTED_MUTATIONS`, the declared sum, the docstring count) and
this sentence is a summary that will go stale again."* It did, one commit later. The pins are all
correct and all machine-checked:

```
EXPECTED_MUTATIONS['scripts/check-review-recorded.py'] = 64   manifest on disk = 64   MATCH
sum(EXPECTED_MUTATIONS.values()) = 735                        declared pin     = 735  MATCH
check-selftest-counts.py  rc=0 — 40 script(s) declare a count, every one verified by running it
```

**Observation that proves it fixed:** the two self-test numbers are deleted from the row in favour of
the pins, which is what r3 Medium 3 asked for and what the row itself argues for — correcting them a
fourth time reproduces the defect a fifth.

---

## LOW 6 — the CORRECTED asymmetry still over-attributes findings to "the collateral derivation", and the document contradicts itself thirty lines apart

**VERIFIED.** `docs/reviews/coordinator/schema-gates-always-reports-r3-coordinator.md:93-96`, against
`:64-67` of the same file.
**ORIGIN: (a) fix-induced** — this is the *corrected* text written for r3 High 1.

The corrected sentence reads:

> 2 findings in the `#137` change (both now closed) against 11 of r1-claude's 14, **all of
> r2-claude's 9, all 8 of r3-claude's**, and codex's 1 + 1 + 2 — in the collateral derivation.

`11 of r1-claude's 14` is **right**, and I checked it rather than assuming: 14 = 2 in the workflow
(Medium 10, Low 14) + 1 in `docs/backlog.md` (Medium 11) + 11 in the derivation. The other two clauses
are wrong, by the documents' own titles:

| Finding | Its subject | In the collateral derivation? |
|---|---|---|
| r2 Low 9 | *"the count narrative in **`check-plan-code.py`**"* | No |
| r2 Medium 5 | *"**backlog #138's** measured … is refuted"* | No — a backlog row |
| r3 Medium 3 | *"**`docs/backlog.md`** row 137 ships stale counts"* | No |
| r3 Medium 4 | *"the severity-trajectory table"* — this coordinator document | No |
| r3 High 1 | the workflow file + the r2 coordinator document | No — and partly on the OTHER side |

**The self-contradiction is thirty lines up, in the same document.** `:64` says of r3 High 1: *"it is
a claim defect first written in the r2 coordinator document, not a defect introduced by a code fix"*.
`:94` then counts it among "all 8 of r3-claude's" findings in the collateral derivation. Both cannot
be true.

**This does NOT change the determination, and saying so is the point.** The honest split is roughly
**2 in the `#137` change against ~27 in the derivation** rather than 2 against 32. The direction is
unchanged and overwhelming; reverting the derivation remains the right retreat if it is ever needed.
The finding is that a passage written specifically to correct over-claimed arithmetic
(*"the word ZERO and the invented confirmation"*) still over-claims its arithmetic — the
*never write a cost table from memory: DERIVE, don't store* shape, third occurrence on this branch.

**Observation that proves it fixed:** the sentence names per-half counts that match the documents'
own subjects, or drops the per-half breakdown for the claim it actually needs ("the derivation
produced an order of magnitude more findings than the workflow change").

---

## LOW 7 — the branch made `review_added.paths` start varying and left the dead ratchet entry behind; the gate asks for its deletion and exits 0

**VERIFIED.** `scripts/check-fixture-variation.py:149` (`KNOWN_UNVARIED`), caused by the case added at
`scripts/check-review-recorded.py:1629`.
**ORIGIN: (a) fix-induced** — measured against master, which is silent:

```
$ cd /tmp/r4m/repo   # git archive 93c815c8
$ python3 scripts/check-fixture-variation.py | tail -2
fixture variation OK — 539 parameter(s) examined across 52 file(s); 126 known-unvaried ratcheted, 7 exempt
rc=0                                                          # no ⭐ line

$ cd /tmp/r4c/repo   # 72f3aefa
$ python3 scripts/check-fixture-variation.py | tail -3
  ⭐ check-review-recorded.py: `review_added.paths` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — 551 parameter(s) examined across 52 file(s); 126 known-unvaried ratcheted, 7 exempt
rc=0
```

The cause is a second literal call site the branch added:

```
MASTER:  review_added(["docs/reviews/verdicts/x.json"])                       # 1 literal call site
BRANCH:  review_added(["docs/notes.md"])  +  review_added([".../x.json"])     # 2, so `paths` varies
```

**Concrete failure scenario.** The ratchet is now looser than reality: `KNOWN_UNVARIED` excuses
`review_added.paths`, so if a future edit removes the `docs/notes.md` case and the parameter stops
varying again, the gate stays silent — the entry pre-authorises the regression. And the request to
delete it rides on **rc=0**, so nothing blocks and the line scrolls past in a green CI step. That is
this repository's own recorded *a gate's CHANNEL can be weaker than the gate*, one layer out.

**Observation that proves it fixed:** `review_added.paths` is deleted from `KNOWN_UNVARIED` and the
⭐ line stops appearing.

---

## Is the branch SAFE TO MERGE, and is `schema-gates` SAFE TO MAKE REQUIRED?

**Both YES, in that order, and the order is not optional.** Stated separately from the convergence
verdict, because they are different questions.

**Safe to merge — the code.** No finding above changes an answer the shipped gate gives; all seven are
missing falsifiers or wrong numbers in prose. Every repo gate is green at `72f3aefa`, run in the real
repository (the `/tmp` copy returns CANNOT RUN for the four that need `git` or a results file, which
is correct behaviour, not a pass):

```
check-docs                 rc=0     check-anchors            rc=0
check-plan-file-tags       rc=0     check-selftest-counts    rc=0
check-ratchet-contract     rc=0     check-guard-coverage     rc=0
check-backlog-closure      rc=0     check-test-counts        rc=0  (2,819 unit / 274 suites)
check-fixture-variation    rc=0     check-arch-findings      rc=0
check-dashboard-entry      rc=0
check-review-recorded --self-test   184/184  rc=0
check-review-rounds        rc=1  <-- for ONE reason: "round 4: only codex — claude neither ran nor
                                    recorded a REVIEW GAP:", which this document closes
```

**Safe to require `schema-gates`.** I re-derived the argument rather than inheriting it, because r3
found this section's previous version resting on a false premise.

| Red on a docs-only PR | Newly blocking once `schema-gates` is required? |
|---|---|
| gate 6 `check-docs.py` — the only tree-reading gate a docs-only diff can flip, and **both its budgets have ZERO slack** | **No.** `ci.yml:109` runs the same script inside `verify`, and `ci.yml` has **no `paths:` filter** — such a PR is already blocked today |
| gate 3 `check-guard-coverage.py`, gate 15 `check-paid-caller-arrival.py` | No — a docs-only diff cannot flip either |
| gates 1-2, 4-5, 7-14 | No — they rebuild the database from migrations and do not read the diff |
| **infrastructure**: the Postgres image pull, `npm ci`, docker | **Yes — this is the whole of the new exposure**, and the file states it honestly |

Re-measured, not inherited:

```
$ python3 scripts/check-docs.py | grep ^budget
budget docs/dev-process.md         :  220 / 220  ok
budget docs/plugins.md             :  260 / 260  ok        # zero slack, both

$ grep -n "check-docs" .github/workflows/ci.yml      ->  109:  run: python3 scripts/check-docs.py
$ grep -n "^  paths\|^    paths" .github/workflows/ci.yml   ->  (none)
```

**The ordering constraint holds, re-verified at `72f3aefa`:** `schema-gates` is gated
`if: github.event_name != 'schedule'` (`:183`), so the context reports on every PR and can therefore
be required; `prod-drift` is gated `schedule || workflow_dispatch` (`:229`), so no fork PR reaches
`CLAUDE_RO_DATABASE_URL`; `permissions: contents: read` (`:177`); the `concurrency` group still keys on
`github.event_name` **and** `github.ref` (`:172`), which is precisely why r1 Low 14's residual is real
and is now written down. **Adding the required context BEFORE this merges blocks every docs-only PR.**

**No red I found would wrongly block a docs-only PR.**

---

## What I tried that produced NO finding

These are reported because a final round's negative results are load-bearing.

1. **The eleven module constants, mutated by VALUE.** This is the class `check-fixture-variation.py`
   structurally cannot see (it reads parameters, not constants). All eleven are pinned, and the two
   numeric ones are pinned **to the byte in both directions** — which is r3 Medium 5a genuinely fixed,
   not reported fixed:

   ```
   CONTROL:  (0, '184/184 passed')
     PATH_LIMIT 1024 -> 4096      killed   [one byte over the TOTAL limit of 1024 is rejected]
     PATH_LIMIT 1024 -> 1025      killed   PATH_LIMIT 1024 -> 1023   killed
     COMPONENT_LIMIT 255 -> 256   killed   COMPONENT_LIMIT 255 -> 254 killed
     PROSE_SUFFIX ".md" -> ".markdown"     killed
     PROSE_DIRS ("docs/",) -> ()           killed   [177/184]
     REVIEW_DIR / VERDICT_DIR / NO_REVIEW  killed
   ```

2. **`_path_of`, re-derived rather than read.** The brief warns the first attempt built the input
   *from* the constant so it moved with the mutation. The shipped version does not:

   ```
   _path_of(1023): bytes=1023 exact=True maxcomp=100 ncomp=11 empty=False looks_like_path=True
   _path_of(1024): bytes=1024 exact=True maxcomp=100 ncomp=11 empty=False looks_like_path=True
   _path_of(1025): bytes=1025 exact=True maxcomp=100 ncomp=11 empty=False looks_like_path=False
   ```

   Byte-exact, every component legal, and the accept/reject boundary falls exactly at the constant.

3. **The two new fixture-variation cases, driven independently.** They are not cosmetic a second time:

   ```
   prose_exceptions_cover(['docs/x'], ('docs/x/',)) = []
   prose_exceptions_cover(['docs/x'], ())           = ['docs/x']
   ```

   Same input, two declarations, two different answers — and mutating the function to read the module
   global instead of its parameter is now **killed**.

4. **r3 Medium 2 — the empty-derivation guard.** Genuinely fixed; the case now distinguishes the
   guard from the completeness prong:

   ```
   delete `if not derived:`  -> killed  [FAIL] ...and it refuses even with NOTHING declared,
                                               so it is not standing on the other prong
   ```

5. **r3 Medium 4 — the trajectory table.** Re-derived from the six documents' own headings and verdict
   lines. **All six rows are now correct**: r1 claude 1/4/6/3, r2 claude 0/1/5/3, r3 claude 0/1/4/3,
   r1 codex 0/1/0/0 (one High), r2 codex 0/0/1/0 (one Medium), r3 codex 0/0/0/2 (two Lows).

6. **r3 Low 8 — the three inert clauses.** All three carry an accurate written note saying they are
   prospective and deliberately unfalsifiable (`:249-254`, `:437-441`, `:580-583`). Properly fixed,
   and the model Low 3 above asks to be applied to a fourth clause.

7. **The 64-entry manifest, and the whole 735 run to completion.** 64 unique names, 64 unique
   anchor-tuples — the four collisions of earlier rounds are gone.
   `EXPECTED_MUTATIONS['scripts/check-review-recorded.py'] = 64` equals the entries on disk, and
   `sum(EXPECTED_MUTATIONS.values()) = 735` equals the declared pin. Run against the delivered
   scripts, in the `/tmp` tree, to completion:

   ```
   $ python3 scripts/check-plan-code.py --mutate .
   OK — delivered scripts mutated: 47 file(s), 735 mutation(s), 735 killed,
        735 attributed to the case each names, 0 survivor(s)
   EXIT=0
   ```

   Note what this does **not** prove, and it is the whole of Low 1 through Low 4: every entry that
   exists is killed and correctly attributed, and the harness has nothing to say about the clauses
   for which **no entry exists**. `--mutate .` measures the manifest's accuracy, never its coverage.

8. **A full sweep of every `if` condition in the file's 39 non-`main` functions**, each mutated to
   `True` and to `False` (114 runs). 24 survivors, and I checked every one: 22 are in **impure,
   git-invoking functions** the pure suite cannot reach by design (`changed_paths`, `added_paths`,
   `_changed_since`, `_load_verdict`, the two `importlib` guards); of the rest, `_gate_sources:639`
   and `:646` are reported under Low 3, and `round_tail:872`, `_final_entries:957`, `round_tails:1048`
   are **pre-existing and untouched by this branch** (bodies byte-identical to master by
   `ast.unparse` comparison) — leads for the backlog, not findings against this PR.

9. **`check-fixture-variation.py` is genuinely wired into CI**, which the commit message asserts:
   `ci.yml:287` runs the rule and `:290` runs its `--self-test`, inside `verify`, which has no path
   filter and is the one required context. The gate that caught `72f3aefa` really does run on every PR.

10. **Dict and tuple fixtures.** I looked for the "same value at every call site" shape in `tails`,
    `CODE_UNDER_PROSE` and the `PROSE_*` tuples beyond the parameter level, and found nothing the
    constant-mutation sweep in (1) had not already pinned.

---

## ⟳ Thrashing — my own determination

**PROSE FLOOR, not thrashing. The architecture review is NOT armed, and round 4 does not change that.**

The r3 coordinator pre-committed the overturn condition: *"if the Claude half of r3 returns a Blocking
or High that is fix-induced, this determination is overturned and the retreat executes."* r3's Claude
half returned a High classified **(b) pre-existing** by its own author, so it did not fire. **Round 4
returns 0 Blocking and 0 High.** The trajectory, now correct in all six rows:

| | r1 | r2 | r3 | r4 |
|---|---|---|---|---|
| Blocking | 1 | 0 | 0 | **0** |
| High | 4 + 1 codex | 1 | 1 | **0** |
| Medium | 6 | 5 + 1 codex | 4 | **0** |
| Low | 3 | 3 | 3 + 2 codex | **7** |

The shape is the prose floor exactly as the method describes it: severity has drained monotonically to
zero while the finding *count* stays non-zero, because what remains are missing falsifiers and stale
numbers — classes that **any** implementation of this component produces, and that no redesign
removes. `review-method.md`'s test — *can a redesign remove it?* — answers **no** for all seven.

⚠ **Three of the seven are fix-induced, and I am not hiding that.** Low 3, Low 5 and Low 7 were each
created by a round-3 or round-4 fix, and Low 4 and Low 6 are fixes that only half-landed. On the
letter of a *count*-based arming rule that looks like thrashing. It is not, by the rule the method
actually prescribes: none is a **wrong gate answer**, all five fail in the noisy direction or in prose
only, and the component they are in converged on behaviour three rounds ago. The arming condition was
built for a Blocking-or-High recurring in one component across six rounds; High here ran 5 → 1 → 1 → 0.

**The stop signal is the one the method names for documents: *rounds can be right forever, which is a
signal to go build*.** Round 4 found nothing that changes what ships. Round 5 would find an eighth
missing falsifier.

---

## Verdict

**NOT CONVERGED** — 0 Blocking, 0 High, 0 Medium, 7 Low.

**MERGE-SAFETY: the branch at `72f3aefa` is SAFE TO MERGE as it stands.** All seven findings are Low,
none changes an answer the shipped gate gives, and none would wrongly block a docs-only PR. I would
merge it without fixing any of them — and if any one is worth a follow-up commit, it is **Low 1**,
because the branch's own headline lesson is the class Low 1 is a live instance of, in the same file.

**And `schema-gates` is SAFE to add to `required_status_checks.contexts` — AFTER this merges, never
before.** Before the merge, the workflow still carries its `paths:` filter on master, so a docs-only
PR would leave the required context pending forever.

⚠ **A correction to the dispatch brief, since it asked me to re-derive the numbers.** The brief states
*"1 Blocking, 7 High, 16 Medium, 8 Low across six halves"*. Blocking, High and Medium are right.
**Low is 11, not 8** (3 + 3 + 3 claude, + 2 from r3 codex). That is the third time a Low total has been
misstated in this branch's coordination — r3's brief said 3 when it was 6, the r3 coordinator document
corrected that, and the r4 brief is wrong again in the same direction. It changes nothing about the
verdict; it is the same *DERIVE, don't store* shape as Low 5 and Low 6, in a third artifact.

### Evidence hygiene

All mutation work was done in `/tmp/r4c/repo` (a `git ls-files` tar of the tracked tree, with
`node_modules` symlinked) and `/tmp/r4m/repo` (`git archive 93c815c8`); every probe restored the file
from an in-memory original in a `finally` block, and each result is quoted against a control proved
green first. **No tracked file was modified.** `git status --short` is clean at `72f3aefa` apart from
this document.

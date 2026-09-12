# Claude adversarial review — branch `goal-page-mutations`, round 1

PROOF OF SUBJECT
----------------

**(1) The `name` field of the 3rd entry in `scripts/mutations/gen-goals-page.json`** (as committed
at HEAD `2246ed6d`):

```
"DOC_PATH loses the basename end anchor, so README-generator.ts reads as documentation"
```

**(2) The exact current body of `eq()` in `scripts/gen-goals-page.py`** (`HEAD:scripts/gen-goals-page.py:753-772`,
verbatim including the comment this branch added):

```python
    def eq(label: str, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        # ⛔ THE FAILURE LINE IS A CONTRACT WITH THE MUTATION HARNESS, not a display choice.
        # `check-plan-code.attribute` reads a red case with `startswith("[FAIL] ")` then
        # `[7:]`, so a suite reporting failures any other way is one whose kills NOBODY
        # CAN SEE: every mutation reports "matched 0 red case(s)" while each one IS killed
        # by the case it names. This file printed `  ✗ <label>  got … want …` and paid all
        # 14 of its manifest entries for it on 2026-09-12 — the THIRD file to do so, after
        # `gen-backlog-page.py` (5 entries) and `brief-compose.py` (8), both of which paid
        # AFTER a convention was written to prevent exactly this.
        # ⚠ THE NAME STAYS ALONE ON THE `[FAIL]` LINE. Appending the got/want to it makes
        # the slice `[7:]` return a string that matches no case name.
        if ok:
            print(f"  ok     {label}")
        else:
            print(f"  [FAIL] {label}")
            print(f"    got {got!r} want {want!r}")
        failures += 0 if ok else 1
```

**(3) The two numbers `EXPECTED_MUTATIONS` holds** (`scripts/check-plan-code.py:568` and `:2907`):

```python
    "scripts/gen-goals-page.py": 14,
```
```python
    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 538)
```

Read back from the module rather than from the diff: `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"]`
is **14**, `sum(EXPECTED_MUTATIONS.values())` is **538**, the dict has **41** keys, and
`scripts/mutations/` holds **41** `.json` files. `len(json.load(gen-goals-page.json))` is **14**.

Subject: `git diff 58d82658..HEAD` — `scripts/mutations/gen-goals-page.json` (new, 14 entries),
`scripts/gen-goals-page.py` (+16/-2, the `eq()` printer), `scripts/check-plan-code.py` (+17/-2,
`EXPECTED_MUTATIONS` 524→538 and the pinned membership list), `docs/dashboard-entries.md` (+54).

STATUS: COMPLETE

⚠ **THE WORKING TREE STOPPED BEING THE SUBJECT PART-WAY THROUGH THIS REVIEW.** My first tool call
showed `scripts/gen-goals-page.py` clean at HEAD. Later in the session another agent began editing
it (adding `run=` injection seams to `git_pr_history` / `git_show_files`, +141/-22, docstring count
65→73) and extending `scripts/mutations/gen-goals-page.json` past 14 entries. **Every measurement
below was re-taken against a tree staged from `git archive HEAD scripts`,** so this review is of the
committed subject, not of whatever is on disk when you read it. Where a working-tree change bears on
a finding I say so explicitly.

---

## Findings

### High — the file's most emphatically documented rule has a case that cannot fail for it, and the manifest does not reach it

**Where:** `scripts/gen-goals-page.py:111` (the rule), `:790-792` (the case), `:69` (`AMENDMENT`)

**What:** `parse_adr`'s docstring calls the front-matter/in-body split *"the point"* and cites the
cost — *"ADR-0006 sat at `status: proposed` while its body recorded two corrections"*. The rule is
one line:

```python
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    return {"status": status, "amendments": AMENDMENT.findall(body)}
```

Deleting it (`body = text`) leaves the suite **65/65 green**. The case that exists to defend it —
`"front matter is NOT counted as an amendment"` — is blind, because its fixture cannot reach the
branch:

```python
    eq("front matter is NOT counted as an amendment",
       parse_adr("---\nstatus: accepted — supersedes ADR-0002\n---\n\nbody\n")["amendments"], [])
```

`AMENDMENT` is `⟳[^\n]*?\b(SUPERSEDED|CORRECTED|…)\b` — it requires a `⟳`. The fixture's front
matter has none, so both the real and the mutated `parse_adr` return `[]` and the assertion (an
**absence**) is satisfied either way. This is verbatim the class in this repo's own record: *the
fixture used an input a DIFFERENT rule filters first*, and *the assertion is an ABSENCE that
deleting the subject also satisfies*.

**Failing scenario:** an ADR whose front matter carries `⟳ SUPERSEDED 2026-08-06` (the shape
ADR-0006 actually had) → real code reports `amendments == []`; with the split removed it reports
`['SUPERSEDED']`. The goals page would show a decision as amended when its front matter merely
mentions it. No case and no manifest entry observes the difference.

**Evidence:** ran as a probe entry through the harness's own path (`load_manifests` anchor rules,
`run_suite`, `parse_fail_names`) over a `git archive HEAD` tree with a proved-green control:

```
CONTROL rc=0  tail=65/65 self-test cases passed
 1. SURVIVED   rc=0 nfails=0  PROBE: parse_adr counts front-matter amendments too (the ADR-0006 rule)
```

and directly:
```
suite fixture -> orig: []  mutated: []          (identical => the case is blind)
front-matter ⟳ -> orig: []  mutated: ['SUPERSEDED']
```

**Why this is High and not Low.** Two of three probes I aimed at *other* unmutated rules
(`parse_header`'s 10-line fold, the `ADR none` collapse) **killed and attributed cleanly** — so the
14 is a seed by choice, not by necessity, and the cheap remaining coverage is real. But the commit
subject says *"The goals page generator gets mutation coverage"* and `EXPECTED_MUTATIONS` is an
EXACT ratchet, so 14 now reads as the file's measured number. Compare `gen-backlog-page.py`'s entry,
which states its seed status in the constant itself (*"A SEED, not a full manifest, and the reason
is measured"*) and carries backlog row #113. This file's comment describes what the 14 cover but
never says what they do not, and the one rule a reader would most expect to be covered is both
uncovered *and* already unfalsifiable.

---

### Medium — the branch records the third payment of the report-format trap in two new places and leaves both canonical accounts saying "twice"

**Where:** `scripts/check-plan-code.py:1205` and `:2919` — neither touched by this diff

```python
            # in the whole file can ever be attributed. Measured twice on 2026-09-10 —
            # `gen-backlog-page.py` (5 entries) and `brief-compose.py` (8) — and BOTH times
```
```python
    # ⛔ THE PROBLEM IS REAL AND HAS NOW COST TWO BRANCHES. `attribute` reads a red case with
```

**What:** this branch is the third payment. It says so in `gen-goals-page.py:761` (*"the THIRD file
to do so"*) and in the dashboard entry (*"Third file to pay this … A convention did not hold, three
times."*). The two accounts inside **the file that owns the contract** — where a reader debugging
`matched 0 red case(s)` will actually land — still say *twice* and *TWO BRANCHES*. The diff moves
`EXPECTED_MUTATIONS` in that same file, so the file was open.

**Failing scenario:** the next author hits the empty-`fails` diagnostic, reads `attribute`'s comment
at `:1205`, and concludes the trap has cost two branches and that the abandoned pre-flight at `:2918`
was judged against a two-instance cost. It has cost three. The abandoned-pre-flight decision is
explicitly a cost/benefit one (*"worse than the 15 minutes it saves"*), and this repo has measured
that a cost/benefit finding expires when its denominator moves.

**Evidence:** `git diff 58d82658..HEAD -- scripts/check-plan-code.py` touches only
`EXPECTED_MUTATIONS` (+5 comment lines, +1 entry), the pinned membership list (+1), and the
`524 → 538` case (+9 comment lines). `grep -n "cost TWO BRANCHES\|Measured twice"` still matches at
`:2919` and `:1205` at HEAD.

---

### Medium — "the ONE sibling generator with no manifest" is false, and the class the branch pays for is measurable and unclosed

**Where:** `scripts/check-plan-code.py:563-567` (the new `EXPECTED_MUTATIONS` comment)

```python
    # ⟳ 2026-09-12. gen-goals-page.py was the ONE sibling generator with no manifest —
    # gen-dashboard, gen-backlog-page, brief-compose, page_chrome and page_markup all had
    # one. …
```

**What (a):** `scripts/gen-m4-manifest.py` is a `gen-*` script, has a `--self-test`
(`self_test()` at `:231`, prints `N/M self-test cases passed` at `:295`), and has **no manifest**.
The enumeration lists five siblings and omits it. The claim is true of *page* producers; it is
written as a claim about generators.

**What (b), and this is the part worth the finding.** I measured the whole population rather than
the five names. Of the scripts under `scripts/` that expose a self-test, **9 have no manifest**, and
**all 9 of them also lack a conforming `[FAIL] ` printer** — they print `✗`, `FAIL `, or nothing
parseable:

```
build-m4-schema, check-ratchet-contract, codex-review, explainer-serve,
gen-m4-manifest, m4_catalog, prior-art, subject_status, verify-exclusion-reasons
```

Every one of the **41** files that *is* in a manifest prints the conforming shape. So the invariant
"in `EXPECTED_MUTATIONS` ⇒ prints `[FAIL] <name>`" holds **41/41 today**, and the set of files
queued to pay the trap a fourth time is exactly the 9 above. That is not a guess about the future;
it is the current state of the filesystem.

**Failing scenario:** the next file to join the manifest is drawn from those 9 (`gen-m4-manifest.py`
is the nearest neighbour of this very change). Its entries all kill, none attribute, and the author
spends the same session at the bottom of a 538-mutation log that the last three spent.

**Evidence:** enumerated by script over `scripts/*.py` + `scripts/mutations/*.json`; spot-checked
`check-ratchet-contract.py:407` (`print(f"  FAIL {name}…")`) and `build-m4-schema.py:289`
(`print(("  ✓ " if ok else f"  ✗ [{got!r} != {want!r}] ") + label)`).

**Calibration, stated rather than hidden.** The dashboard entry already flags this
(*"⚠ Worth a rule, not a fourth comment"*) and names the right mechanism — run a suite with one case
forced red and check the output shape, which is behavioural and therefore decidable where
`check-plan-code.py:2918-2941`'s two abandoned *source-shape* rules were not. Nothing is filed. Per
this project's rule that filing is the user's step, I am not proposing the row — I am supplying the
measurement it would need: 41/41 conforming, 9 non-conforming and unmanifested, and a `--self-test`
harness (`check-selftest-counts.py`) that already spawns all 36 declaring suites under a redirected
`HOME` and could carry the forced-red probe at near-zero marginal cost.

---

### Low — `brief-compose.py (8)` is not supported by any committed artifact

**Where:** `scripts/gen-goals-page.py:762`, `docs/dashboard-entries.md:7708`

**What:** both new sites state *"`brief-compose.py` 8"* as an entry count. The only committed
observables disagree: `scripts/mutations/brief-compose.json` landed with **16** entries in
`f6c03fd8` (the commit that created it) and holds 16 today;
`EXPECTED_MUTATIONS["scripts/brief-compose.py"]` is **16** and
`git log -S'"scripts/brief-compose.py": 8' -- scripts/check-plan-code.py` returns **nothing** — it
was never committed as 8.

The number is inherited honestly: `brief-compose.py:1767` says *"all EIGHT entries"*, so 8 is
plausibly the manifest size at the moment the trap fired mid-development, before it grew to 16. That
state was squash-merged away and cannot be checked. The defect is that this branch propagates an
uncheckable figure to two new sites in a form (*"(8 entries)"*) that reads as the entry count, next
to *"(5 entries)"* which **is** verifiable (`gen-backlog-page.json` landed with 5 and has 5).

**Fix:** either say *"the 8 entries it had when the trap fired"*, or drop the parenthetical. This
project's recorded rule is to enumerate a cost from artifacts or drop the numbers.

---

### Low — "~540 lines of new rules" overstates the measured delta

**Where:** `scripts/check-plan-code.py:565`

`git show --numstat 58d82658 -- scripts/gen-goals-page.py` → `532  8`. So 532 added, 8 removed, net
**524**. "~540" rounds up past both readings. Immaterial to the code; noted because the same comment
is the justification for the entry existing, and every other number in this diff is exact.

---

### Low — entry 9's `expect` names a case whose title claims crash-safety, while the mutation is caught by the collapse, not by a crash

**Where:** `scripts/mutations/gen-goals-page.json` entry 9 at HEAD; case at
`scripts/gen-goals-page.py:981`

The mutation rewrites identity-matching to field-matching. With `named == [None]` and the extra
document's `.get("rel")` also `None`, the extra is *skipped* — the case fails by **reporting**
`"extra document" not in output`, which is the strong shape. But the case it names is
`"a document record with no rel does not crash the renderer"`, whose title asserts the weak shape
(no exception). Naming it makes the entry read as a crash test when what it measures is the silent
collapse — and the sibling case `"and the rel-less extra is still named once"` (which does describe
the defect) also goes red and is not named. `expect` accepts a list precisely for this.

⟳ Already addressed in the working tree: the `expect` there now reads *"a rel-less extra is
identified by identity, not collapsed into the spec"*. Recorded for the round, not for re-fixing.

---

### Low — three entries kill two cases each and name only one

Entries 8, 9 and 11 each produce two red cases (`pr_fanout` → also *"a PR touching both halves of
one thread counts as two documents"*; 9 → also *"and the rel-less extra is still named once"*; 11 →
also *"and it does NOT also claim there are no pull requests"*). The harness permits this — `expect`
must resolve to exactly one red case, not to all of them — but its own comment prefers the list
form: *"A mutation may legitimately break several behaviours, so `expect` accepts a LIST … That is
more honest than naming one of five arbitrarily and calling it the guard."* No defect; flagged so
round 2 does not re-derive it.

---

## Checked and found sound

**All 14 entries KILL and ATTRIBUTE, over a proved-green control, against a pinned HEAD tree.** Not
inferred from the commit message — re-run here through the subject's own functions
(`check-plan-code.child_env`, `run_suite`'s `[sys.executable, name, "--self-test"]` invocation,
`merged_output`, and `parse_fail_names` imported rather than re-implemented), staged with
`git archive HEAD scripts` so the concurrent working-tree edits could not leak in:

```
CONTROL rc=0  tail=65/65 self-test cases passed
 1..14   KILLED+ATTRIBUTED   rc=1   (nfails 1,1,1,1,1,1,1,2,2,1,2,1,1,1)
```

- **No entry kills by crashing or by failing to parse.** Every one produced `rc == 1` *and* at least
  one parseable `[FAIL] <case>` line, and every run reached the `65/65`-shaped summary — so no
  mutation aborted the suite before its named case ran. Checked explicitly because a crash-kill
  would have surfaced as `caught=True, fails=[]`, which `attribute` reports as a report-format
  defect rather than coverage.
- **No entry is syntax-only.** The two `if False:` entries (11, 12) leave the guarded statement
  present and the module importable; the rest are semantic rewrites of a live expression.
- **Every anchor matches exactly once** in the target at HEAD (`src.count(find) == 1` for all 14
  `before` strings), so `load_manifests`' duplicate-anchor refusal and `run_mutations`' "only the
  FIRST is replaced" hazard are both satisfied. No two entries share an anchor tuple; no two share
  a name.
- **The printer fix satisfies the contract for every path that reports a failure.** `eq()` is the
  **only** failure printer in `self_test` — grepped the whole `self_test` body: the sole other
  `print` is the `N/M self-test cases passed` summary. No `✗` survives anywhere in the file except
  inside the new comment's prose (which is inert). The got/want detail is on a **second** line
  beginning `    got `, so `l.strip().startswith("[FAIL] ")` never selects it.
- **Names round-trip exactly.** All **65** `eq` labels extracted from source: zero duplicates, and
  **zero contain `": got "`** — the one substring that would make `parse_fail_names`' `rsplit(": got ", 1)`
  truncate a name and render its entry unattributable. Every `expect` in the manifest matched its
  case by string equality, whitespace and unicode included (entries 5, 6, 7 carry apostrophes;
  entry 7 carries `NEWEST FIRST`).
- **Ratchet arithmetic balances.** `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"] == 14 ==
  len(manifest)`; `sum(...) == 538`; 41 dict keys ↔ 41 files in `scripts/mutations/`. The pinned
  membership list at `:2474` gains `scripts/gen-goals-page.py` in sorted position, which the
  dashboard entry correctly identifies as the second, independently-required ratchet.
- **`check-plan-code.py --self-test` passes 128/128** in the repo. (In my `scripts`-only scratch
  tree it is 125/128, because three `HARNESS_TREE` cases correctly report `supabase`, `docs`,
  `node_modules/typescript` and `.claude/hooks` missing — that is the guard working, not a defect.)
- **`gen-goals-page.py --self-test` is 65/65 at HEAD**, and the docstring's declared count is 65,
  so `check-selftest-counts.py` agrees. `gen-goals-page.py` is already pinned in that script's
  `POPULATION`, so the declaration has an outside observer. This branch adds no cases, so the count
  correctly does not move. (The 65→73 drift I saw once was the concurrent working-tree edit, not
  this branch.)
- **`check-ratchet-contract.py` is green with `MANIFEST_BASELINE = 0`** and is unaffected by this
  change: its R4 population is `discover_guards()`' 34 `check-*` guards, which never included
  `gen-goals-page.py`. So no third ratchet was silently left behind — I checked this specifically
  because the `check-gate-falsifiability.py` precedent required `MANIFEST_BASELINE` to move in the
  same commit, and that precedent does not apply here.
- **The provenance claims I could check against source hold**, except as filed above:
  `gen-backlog-page.json` landed with and holds **5** entries; `gen-dashboard`, `brief-compose`,
  `page_chrome` and `page_markup` all have manifests (64 / 16 / 11 / 14); both named files landed
  **after** `portable-practices` §22 existed (`050913f6` and `f6c03fd8`, both 2026-09-10, and
  `brief-compose.py:1771` says so in its own words); the `startswith("[FAIL] ")` + `[7:]` mechanism
  the comment describes is exactly `parse_fail_names` at `:1402-1403`.
- **Two rules I suspected were uncovered turned out to be coverable, and I say so because it bounds
  the High above**: probes on `parse_header`'s 10-line fold and on the `ADR none → []` collapse both
  killed and attributed on the first try. The gap in the manifest is breadth, not untestability —
  for those two.
- **The genuinely untestable surface at HEAD is real and correctly absent from the manifest.**
  `git_pr_history`'s CANNOT-RUN predicate, its `--follow` flag, and `git_show_files`' `.splitlines()`
  had no injection seam at HEAD (`annotate_code` took `show=`; these took nothing), so a mutation on
  them would have SURVIVED. Their absence from the 14 hides untestability rather than completeness —
  which is item 3 of the review brief, and it is a true positive. ⟳ It is being closed in the
  working tree as I write (`run=subprocess.run` added to both, plus manifest entries for the
  returncode branch, the `except` branch and `--follow`). Since that work is not in the subject, I
  record it as confirmed-and-in-flight rather than as a finding against this commit.

---

## Verdict

**NOT-CONVERGED.**

The 14 entries themselves are sound and I could not break one: every anchor is unique, every kill is
a report rather than a crash, every attribution resolves by exact name, and both ratchets balance.
Nothing here blocks on the mutations.

What does not converge is the **claim around them**. One measured defect (the `parse_adr`
front-matter rule: a live unfalsifiable case plus no entry, on the one invariant this file's
docstring says cost three weeks) and two provenance statements that the repo contradicts — *"the ONE
sibling generator"* (`gen-m4-manifest.py` is a second) and *"cost TWO BRANCHES"* left standing in the
contract's own file after this branch made it three. The minimum for round 2: an entry (or a written
seed declaration) for `parse_adr`, and the two stale counts in `check-plan-code.py` moved to three.

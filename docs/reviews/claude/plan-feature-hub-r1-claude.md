# Claude adversarial review — feature hub PLAN — round 1

Subject: `docs/superpowers/plans/2026-09-19-feature-hub.md` (714 lines), against
`docs/superpowers/specs/2026-09-19-feature-hub-design.md` (195 lines).
Branch `feature-hub-spec`, plan commit `c3b44ef5`. Reviewed 2026-09-19.

## Verdict: FINDINGS

**3 Blocking, 5 High, 4 Medium, 3 Low.**

The plan is unusually good in the places it chose to look — its one self-declared risk (Task 2's
`anchors.md` column) is real, was checked, and I measured it as harmless in both consumers. The
failures are all in the places it *asserted* rather than ran: its own self-test does not pass, its
mutation harness cannot attribute a single kill, and three of Task 6's five "Expected: exit 0"
gates will go red on arrival.

**Plain answer to "do the plan's self-test suites pass as written?" — NO.** Task 1 runs 11/12 and
exits 1; Task 3 runs 17/18 and exits 1. One added line fixes both, verified.

---

## Did the plan's code run? — yes, all of it

I extracted every Python block in Tasks 1, 3 and 4 into `/tmp/fhr1/` and executed them. Nothing in
this review is read-off-the-page.

| What | Built from | Result |
|---|---|---|
| Task 1 `check-features.py` (harness + parser + `check_nodes`) | plan `:60-151` + `:162-239` | **11/12, rc=1** |
| Task 1, with one `for:` line added | same + fix | 12/12, rc=0 |
| Task 3 (adds `backlog_areas`, `check_cross`, `main`) | plan `:376-400` + `:409-491` | **17/18, rc=1** |
| Task 3, with the same one-line fix | same + fix | 18/18, rc=0 |
| Task 4's `importlib` snippet | plan `:530-537` | **works** — imports `parse_features` and `Node` |
| `backlog_areas` vs the real `docs/backlog.md` | — | 21 areas, 140 rows accepted, **2 rows silently dropped** |
| 4 mutation anchors vs the delivered source | plan `:635-661` | all 4 match **exactly once** |
| Failure-line format vs `check_plan_code.parse_fail_names` | — | **`[]` — unparseable** |
| `check-ratchet-contract.evaluate` with the planned files injected | — | **1 violation** |
| `check-selftest-counts.population_errors` with both new scripts | — | **2 errors** |
| `check-anchors.parse_registry` + `gen-goals-page.parse_registry` with a 4th column | — | identical, **safe** |
| `STATUS_TOKENS` vs the 13 anchor Goal sentences | — | **1 of 13 rejected** |

Declared counts are correct: Task 1's `_self_test` contains exactly 12 `check(...)` calls, Task 3
adds exactly 6 → 18. The docstring form (`--self-test # N cases`, one space, trailing prose) *is*
recognised by `check_plan_code.count_drift` — I ran it.

---

## Findings

### [Blocking] 1 — The Task 1 self-test does not pass as written, and the defect propagates to Task 3

**Evidence.** Extracted verbatim and run:

```
$ python3 /tmp/fhr1/scripts/check-features.py --self-test
  ✗ clean tree passes the rules
      got  ['features.md:8: `rate-limiting-per-account` has no `for:` line — every node says what it is for']
      want []

11/12 self-test cases passed
rc=1
```

The fixture `TREE` (plan `:102-112`) gives `rate-limiting-per-account` a `state:` and an
`expected-because:` but **no `for:` line**, while `check_nodes` (plan `:216-217`) requires one on
every node regardless of state. Case 7, `"clean tree passes the rules"`, is the falsifier.

Task 1 Step 4 states `Expected: 12/12 self-test cases passed, exit 0`. It is 11/12, exit 1. Task 3
inherits the same fixture: **17/18, rc=1**, against Step 4's stated `18/18`.

The spec has the same hole at its own source — the illustrative node at `spec:91-96` also carries no
`for:` line, so the plan copied a fixture the spec had already written wrong.

**Why it matters.** Task 1 Step 4 is the green gate the whole plan stands on; a subagent executing
Task 1 hits a red suite on its first run with no instruction covering it, and the natural repair
(delete the failing case, or relax the `for:` rule for `absent` nodes) removes the rule the spec
calls its most important half.

**Fix.** Add a `for:` line to the fixture's absent node. Verified — with

```
state: absent
for: Keeps one account from exhausting the shared spend cap.
expected-because: standard for a hosted multi-tenant service.
```

Task 1 runs **12/12 rc=0** and Task 3 runs **18/18 rc=0**. No other change needed. Also fix
`spec:91-96` so the two do not disagree.

---

### [Blocking] 2 — The self-test's failure line cannot be parsed by the mutation harness, so all four of Task 6's mutations are unattributable

**Evidence.** The plan's `check()` (plan `:96-100`) prints:

```python
print(f"  ✗ {name}\n      got  {got!r}\n      want {want!r}")
```

`scripts/check-plan-code.py:1596-1597` — `parse_fail_names` — accepts **only** lines starting with
`[FAIL] `:

```python
return [l.strip()[7:].rsplit(": got ", 1)[0].strip()
        for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```

Run against the plan's actual output:

```
parse_fail_names on the PLAN's output    -> []
parse_fail_names on the CANONICAL form   -> ['a built node with no fragment fails']
```

`check-plan-code.py:1406-1409` then reports *"the suite went RED but printed no `[FAIL] <case>`
line"* and refuses the verdict. **39 of this repo's suites already print `[FAIL] `**; the plan's is
the outlier.

**Why it matters.** Task 6 Step 3 says `Expected: 4/4 killed`. The real result is 4 mutations that
kill the suite *unattributably* — the harness cannot tell them from "no coverage at all". This is
the **third** recorded instance of this exact defect in this repo, both prior ones documented inside
the file the plan is about to call: `check-plan-code.py:979` (`check-gate-falsifiability` printed
`  ✗ {label}: got …`, *"which this file's attribution parser cannot see, so every mutation here
would have killed the suite UNATTRIBUTABLY"*) and `:988` (`check-function-revokes` printed
`❌ {label}` — *"all six mutations first reported CRASH with zero parseable failure lines"*). That
second note also states the required order: **the print contract is fixed BEFORE the manifest is
registered.**

**Fix.** In Task 1 Step 1, change `check()` to the canonical line and keep the emoji out of it:

```python
print(f"  [FAIL] {name}: got {got!r} want {want!r}")
```

The `N/M … passed` summary line is fine as written — I ran `check_selftest_counts.printed_total`
against it and it parses.

---

### [Blocking] 3 — Task 6 Step 3 fails before any mutation runs: `check-features.py` is not in `EXPECTED_MUTATIONS`

**Evidence.** `scripts/check-plan-code.py:1152-1154`:

```python
for target in sorted(set(counts) - set(EXPECTED_MUTATIONS)):
    drift.append(f"{target}: {counts[target]} mutation(s) but no declared count — add it "
                 f"to EXPECTED_MUTATIONS so its coverage cannot shrink unnoticed")
```

`EXPECTED_MUTATIONS` is a dict at `check-plan-code.py:522` holding an **exact** count per manifested
file ("EXACT, not a floor"). Task 6 creates `scripts/mutations/check-features.json` with 4 entries
and **no task adds `"scripts/check-features.py": 4`** to it. Step 3's `Expected: 4/4 killed` is
therefore unreachable — the run stops at manifest validation.

**Why it matters.** The failure is loud, so nothing ships broken; but Task 6 is the last task, the
executor is out of plan at that point, and the constant lives in a 2,000-line file it was never told
to open.

**Fix.** Add a Task 6 step: register `"scripts/check-features.py": 4` in `EXPECTED_MUTATIONS`, in
the same commit as the manifest (the comment at `:1148-1151` requires exactly that).

---

### [High] 4 — `gen-features-page.py` DOES violate the ratchet contract, via R4's *widened* population

The brief asked whether the missing manifest for `gen-features-page.py` is a gap. It is — but not
where it was expected. The guard population (`GUARD_PATH_RE = scripts/check-[\w.-]+\.py`) never sees
a `gen-*` file. `discover_self_tested_nonguards` does.

**Evidence.** `check-ratchet-contract.py:402-411`:

```python
def discover_self_tested_nonguards(script_paths, texts):
    """Scripts that prove themselves with a `--self-test` but are not NAMED `check-*`. PURE."""
    guards = set(discover_guards(script_paths))
    return sorted(p for p in script_paths
                  if p not in guards and SELF_TEST_RE.search(texts.get(p, "")))
```

I drove the real `evaluate()` with the repo's live `scripts/*.py` plus the two planned files
(`gen-features-page.py` carrying the `--self-test  # 6 cases` Task 4 Step 1 specifies):

```
gen-features-page in R4W population: True
pinned as debt: False

violations: 1
  scripts/gen-features-page.py [R4W_no_mutation_manifest]
```

Corroboration from the shipped tree — every existing page producer with a `--self-test` already has
a manifest: `gen-backlog-page.py` Y, `gen-dashboard.py` Y, `gen-goals-page.py` Y. The one without
(`gen-m4-manifest.py`) is pinned in `WIDENED_MANIFEST_DEBT`.

`check-features.py` itself is clean: `check-*` name (R1 self-test ✓), CI caller from Task 6 Step 1
(R3 ✓), manifest from Step 2 (R4 ✓).

**Why it matters.** Task 6 Step 4 states `Expected: exit 0`. It exits non-zero and the executor has
no instruction for it.

**Fix.** One of: write `scripts/mutations/gen-features-page.json` (and its `EXPECTED_MUTATIONS`
entry — see finding 3); or put a real `NO-MUTATIONS: <reason>` in `gen-features-page.py`'s
**docstring** (a comment is explicitly not accepted, `:409-412`). Given three sibling page producers
carry manifests, the manifest is the consistent choice.

---

### [High] 5 — `check-selftest-counts.py` fails: both new scripts declare a count and neither is in `POPULATION`

**Evidence.** `check-selftest-counts.py:272-275`:

```python
for name in sorted(found - pinned):
    out.append(f"{name}: declares a case count but is not in POPULATION, so nothing checks "
               f"it. Add it.")
```

Driven with the real function:

```
POPULATION size: 40
errors: ['check-features.py: declares a case count but is not in POPULATION, so nothing checks it. Add it.',
         'gen-features-page.py: declares a case count but is not in POPULATION, so nothing checks it. Add it.']
```

Task 6 Step 5 states `Expected: the docstring's # 18 cases matches what the suite prints.` It never
gets that far — the population rule fires first, and **no task edits `POPULATION`**.

**Why it matters.** This is precisely the drift `POPULATION`'s own comments were written for
(`check-selection-card.py`, `check-group-claims.py` and `check-fixture-variation.py` each carry a
note saying they were pinned *in the same commit that created them*, because *"shipping a declared
count nothing verifies is the drift this script exists to stop"*). Shipping two such files is that
shape doubled.

**Fix.** Add `"check-features.py"` and `"gen-features-page.py"` to `POPULATION` in the commits that
create them.

---

### [High] 6 — Task 2 adds a `Feature` column that nothing ever reads, and it implements the *opposite* rule to the one the spec states

**Evidence.** `spec:165` — enforcement rule 1: *"every `Feature:` in `anchors.md` resolves to a
node"*, catching *"a renamed or deleted node"*. `spec:174` — falsifier 1: *"Delete a node that
`anchors.md` references → `check-features.py` fails naming it."*

The plan's `check_cross` (plan `:430-451`) reads `n.anchors` — the `anchors:` line **inside
features.md** — and checks those resolve into `anchors.md`. `main()` (plan `:474`) passes only
`_anchor_slugs(...)`, a set of slugs; **the `Feature` column is never parsed anywhere in the plan.**
The direction that is enforced is features→anchors. The direction the spec specifies and falsifies
is anchors→features. Deleting a node leaves a dangling `Feature` cell and every check stays green.

Worse, the two directions are already inconsistent **in the plan's own data**. Task 1 Step 5
(`:263-272`) gives `cloud-publishing` to *both* `job-queue-and-worker-lifecycle` and `wake-on-visit`
— and `check_cross` permits that, because the exactly-one rule is applied to `areas` only, never to
`anchors`. But `anchors.md`'s new `Feature` column is one cell per row: it can name only **one**
node for `cloud-publishing`. The plan therefore ships two representations of one relation with
different cardinalities and no reconciliation between them.

**Why it matters.** This is the duplicate-vocabulary shape `scripts/check-vocabulary-collisions.py`
exists to catch, arriving inside a spec whose central argument (`spec:30-32`) is *"a second copy of a
fact can disagree with the first, and this project has measured that repeatedly. A link cannot."*
It is also 13 rows of hand-editing that buy nothing.

**Fix (pick one, do not do both halves):** either (a) drop the `anchors:` line from the node grammar,
make `anchors.md`'s `Feature` column the single declaration, and have `check_cross` read it — which
is what the spec describes and gives a natural exactly-one cardinality; or (b) drop the `Feature`
column and keep the node's `anchors:` line, and correct `spec:165` and `spec:174` to state the rule
that is actually enforced. (a) matches the spec; (b) is cheaper. Either way, add a uniqueness rule
for anchors or state in writing that many-nodes-per-anchor is intended.

---

### [High] 7 — `backlog_areas` silently drops backlog rows whose **Status** cell contains an escaped pipe

**Evidence.** The `[-3]` positional read is otherwise **correct** — I verified the header is
`| # | Item | Touches | Size | Bundle | Status |` (`docs/backlog.md:30`), so `[-3]` is the Bundle
cell, and extra `\|` in *Item* or *Touches* is harmless because the index counts from the right.
The failure is an escaped pipe in the **last** cell:

```
rows accepted: 140
rows whose [-3] cell is NOT an (area): 3
   >>> ' Bundle '   (the header — correctly ignored)
   >>> ' Status \'  || pipes=11 || | 90 | 🟡 **The backlog is a parking space for STORIES...
   >>> ' 111 \'     || pipes=13 || | 110 | ✅ (was 🟠) **An open item can vanish...
```

Re-parsed with an escape-aware split, the true area cells are `(comprehensibility)` for #90 and
`(tooling)` for #110. Both are dropped. Today `areas_in_use` is unaffected (21 areas either way)
because other rows use the same two spellings.

**Why it matters, in two places.**
1. `spec:177` falsifier — *"Introduce a second spelling of an existing backlog area → fails as an
   unclaimed area."* That falsifier does not hold for any row with an escaped pipe in its Status
   cell. The drift-detection rule is the entire justification for the alias map (`spec:123-129`).
2. Task 4 Step 3 renders *"rows whose area cell is in `node.areas`"* using the same read. Backlog #90
   and #110 will silently never appear under their node — the page claims to be the map of known
   gaps and quietly omits two.

The repo already owns the fix: `check-docs.py` has a `CELL_SPLIT` with an **escaped-pipe
lookbehind**, and it is mutation-covered (`check-plan-code.py`: *"CELL_SPLIT's escaped-pipe
lookbehind"* is one of its 4 entries). Note the irony worth recording — row **#110 is itself about a
parser that silently skips rows**, and its own row defeats this new one.

**Fix.** Split on `re.split(r"(?<!\\)\|", line)`, or import `check-docs.py`'s existing `CELL_SPLIT`
rather than writing a second one. Add a self-test case using a row with `\|` in its Status cell —
the current case (plan `:398-399`) uses a clean 7-pipe row and therefore passes for a reason the real
corpus does not exercise.

---

### [High] 8 — The status-token rule, the design's whole anti-rot argument, is defeated by a line wrap

**Evidence.** `spec:131` says *"One paragraph per node"*. The grammar is a single-line
`for:` field (`FIELD`, plan `:163`); any continuation line simply fails `FIELD.match` and is
`continue`d (plan `:183-184`). Measured on the extracted parser:

```
input:
    for: Turns a transcript into a summary
      a person reads. Currently broken, see #322.

purpose  = 'Turns a transcript into a summary'
problems = []
```

The banned words `Currently` and the banned `#322` are both present in `docs/features.md`, and
`check_nodes` reports **nothing** — the text was never in `n.purpose` to be searched. The page
renders the truncated half, so the status prose is invisible there too.

**Why it matters.** `spec:136-138` calls the bound *"the whole anti-rot argument for the one
hand-written element"*, and `spec:178` falsifies it with *"Write `currently`, `#322` or `✅` into a
node's prose → fails, naming the token."* A wrap is not an exotic input: the plan's own example
`for:` line (plan `:265`) is 119 characters, longer than anything else in `docs/features.md`, so the
first author to wrap it silently disables the rule for that node.

**Fix.** Either fold continuation lines into `purpose` (indented lines after a `for:` append to it),
or refuse them: any non-blank, non-`###`, non-`FIELD` line under a node becomes a parse problem. The
second is a two-line change and is the "cannot run is a failure" posture; the first honours
"one paragraph". Do not leave them silently dropped.

---

### [Medium] 9 — `STATUS_TOKENS` rejects 1 in 13 of this repo's own purpose-shaped sentences; `now` is the offender

**Evidence.** The closest available corpus to "a sentence saying what a thing is for" is the 13
**Goal** sentences in `docs/anchors.md` — written by this project, for this purpose. Run through the
plan's compiled `STATUS_TOKENS`:

```
  REJECTED explanation-on-demand: token 'now'
     A person working now can have a subject they choose — a change, a concept, or a set of
     findings — explained in a page they can read and ask questions inside.
anchor goals: 13 tested, 1 rejected by STATUS_TOKENS
```

All five purpose sentences the plan itself proposes pass. So the rule is obeyable — but at roughly
an 8% false-positive rate on real prose, and `now` is doing all of it (`still`, `yet`, `done`,
`already` produced no hits; `\b` correctly protects `know`, `distill`).

**Why it matters.** `spec:143-144` argues the list *"is deliberately short and literal — a fuzzier
rule would be argued with rather than obeyed."* That argument is right, and this finding is not a
request to fuzz it. It is that a list which rejects one of the thirteen existing sentences will be
argued with on its first collision, and the plan's Global Constraints repeat the list **without any
note that it has a measured false-positive case.**

**Fix.** Keep the list. Add one line to the plan's Global Constraints recording the measurement and
the intended response — *rewrite the sentence, do not edit the list* — and, if a hand is wanted, make
the error message say so. (`explanation-on-demand`'s own goal rewrites cleanly as "A person mid-task
can have a subject they choose…".)

---

### [Medium] 10 — Task 4 Step 5 names two dicts that do not exist

**Evidence.** Plan `:561` — *"add to `PAGES` (near line 124) and `SOURCES` (near line 141)"*. The
real names are `REGENERABLE` (`scripts/explainer-serve.py:121`) and `PAGE_SOURCES` (`:139`). The
line numbers are near enough; the identifiers are wrong.

**Why it matters.** Minor for a human, a real stall for a subagent that greps for `PAGES` and finds
nothing at the cited line. The two dicts *are* keyed together and `_stale_sources_covered` in
`explainer-serve.py`'s own suite asserts it — the plan adds to both, which is correct.

**Fix.** Use the real names.

---

### [Medium] 11 — Task 4's self-test snippet has an undefined `nodes` and two cases coupled to live data

**Evidence.** Plan `:518-526` opens with `html = render(nodes, {...})`; `nodes` is never defined in
the snippet and no step says where it comes from. Three of the six cases —
`"an absent node is marked"`, `"the absent reason is shown"`, `"the absence count is shown"` with
the literal `"1 declared absence"` — can only pass against a tree containing **exactly one** absent
node. Task 2 Step 3 says *"Include at least one `absent` node"*. Two absences makes case 5 fail with
no explanation in the plan.

The parse target matters too: if `nodes` comes from the live `docs/features.md`, the suite is
non-hermetic. That is survivable here — I checked `check-plan-code.HARNESS_TREE` and it stages
`("scripts", "supabase", "docs", "node_modules/typescript", ".claude/hooks", ".github/workflows")`,
so `docs/` is present and the `FileNotFoundError` that killed `gen-backlog-page.py`'s manifest
(`check-plan-code.py:1005-1010`) does not recur. It is still a suite whose verdict changes when a
doc changes.

**Fix.** Parse a synthetic `TREE` inside the suite, as Task 1 does, and assert
`"1 declared absence"` against that fixture, not against the living tree.

---

### [Medium] 12 — Task 2 Step 1 checks one consumer of `anchors.md`; there are two. Both are safe — measured

This is the plan's one self-declared risk (plan `:714`), and the answer is that it **does not
materialise**. Stating it plainly because the plan told the executor to find out and the finding is
"no".

**Evidence.** Every reader of `anchors.md` in the repo:

```
$ grep -rln "anchors\.md" scripts/ .claude/ .github/
.claude/hooks/regen-goals-page.sh
scripts/check-anchors.py
scripts/gen-goals-page.py
```

- `check-anchors.py:71` — `REGISTRY_ROW = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|")`. Left-anchored,
  first cell only. I ran `parse_registry` against the live file and against a simulated 4-column
  version: `before: 13  after: 13  identical: True`.
- `gen-goals-page.py:64` — three capture groups, each `[^|]*?`, so none can cross into a 4th column.
  Same test: `rows: 13 13 identical: True`.

There is no `cells[-2]` anywhere in either. The live run is green today:
`anchors: 13 registered, all claimed; every spec/plan dated >= 2026-08-25 declares one; floor 22 held`.

**Why it is still a finding.** Task 2 Step 1's grep targets `scripts/check-anchors.py` **only**, and
the risk paragraph at `:714` names one consumer where there are two. The check was narrower than the
hazard it was written for; it happened to be enough.

**Fix.** Widen Step 1 to `grep -rln "anchors\.md" scripts/ .claude/` first, then inspect each hit.

---

### [Low] 13 — Task 1 Step 6 codifies a cannot-run as a pass

Plan `:276-277`: *"Run `python3 scripts/check-features.py` / Expected: exit 0 — but the `__main__`
block only handles `--self-test` so far, so it exits 0 silently. That is correct for this task."*
Verified: it does exit 0 and print nothing. The plan's own Global Constraints (`:22`) say
*"**'Cannot run' is a FAILURE, never a pass.**"* Calling a silent exit-0 "correct" — even
transiently — is the shape the constraint forbids, and Task 1 is where a reader learns the file's
conventions.

**Fix.** Make the Task 1 entry point `sys.exit(_self_test() if "--self-test" in sys.argv else 2)`
with a `CANNOT RUN — main() arrives in Task 3.` message, and let Task 3 replace it. Or drop Step 6.

### [Low] 14 — Task 2 Step 4's expected output is a prefix, not the output

Plan `:350` expects `anchors: 13 registered, all claimed`. Real output adds `; every spec/plan dated
>= 2026-08-25 declares one; floor 22 held`. Harmless for a human, an ambiguous match for a subagent
asked to confirm an exact expectation.

### [Low] 15 — `docs/backlog.md`'s second table can never reach the page

`docs/backlog.md:182` — `| # | Item | Status |`, under *"Found during testing (2026-06-19/20)"*,
rows #9/#10/#11. No Bundle column, so no area, so those rows are unreachable by the alias map. They
are excluded today only incidentally, by `line.count("|") < 7` — a row there that grew a nested table
or an escaped pipe would be read as if `[-3]` were an area cell. No task mentions the second table.
Worth one sentence in `features.md` or a deliberate skip in `backlog_areas`.

---

## Spec coverage — is any spec requirement missing a task?

The plan's own coverage table (`:692-708`) is accurate except for one row, and omits one requirement
entirely.

| Spec requirement | Plan claims | Actually |
|---|---|---|
| `spec:165` every `Feature:` in `anchors.md` resolves to a node | Task 3 | ✗ **not implemented** — finding 6. Task 3 implements the reverse direction |
| `spec:174` falsifier: delete a referenced node → fails naming it | — | ✗ **absent from the table entirely**, and unimplemented |
| `spec:177` falsifier: second spelling of an area → fails | Task 3 | ⚠ holds for 138/140 rows — finding 7 |
| `spec:178` falsifier: status token in prose → fails | Task 1 | ⚠ defeated by a line wrap — finding 8 |
| `spec:131` one **paragraph** per node | Task 1 | ⚠ grammar supports one **line** — finding 8 |
| Three trunks; `built`/`absent` both directions; `expected-because:`; `areas:` map with no per-row edits; exactly-one area claim; exit 2 on unparseable backlog; `/features` derived; rebuild hook; CI + mutations; absence count | Tasks 1–6 | ✓ all have a task |
| `spec:183` tests and code modules never appear as fragments | by omission | ✓ no task adds them |
| `spec:186` `/goals` not retired, re-evaluation sequenced | by omission | ✓ no task touches it. ⚠ the *sequenced re-examination* is deliberately future work and has no task, which matches the spec — but nothing records the trigger, so it will be forgotten |

One executability gap beyond the above: Task 2 Step 2 says *"Map each of the 13 anchors to a node
slug you create in Step 3"*, and Step 3 sources PRODUCT nodes from `find app/api -name route.ts`.
Nothing tells the executor what to do when an anchor is a **platform property or tooling** and no
route implies a node — which is 6 of the 13 by the spec's own table (`spec:46-51`). Step 2 says
"map to nodes under PLATFORM or DEV INFRASTRUCTURE"; Step 3 gives no source for those two trunks'
nodes at all. That is the largest unspecified step in the plan.

---

## Things I checked and found correct

- **Declared self-test counts are right.** 12 `check(...)` calls in Task 1, 6 added in Task 3 = 18.
  Both match the declared numbers.
- **The docstring form is recognised.** `count_drift(doc, 18) -> None`, `count_drift(doc, 99) ->
  '[DRIFT] the docstring declares 18 cases; the suite ran 99'`. One space before `#` and trailing
  prose after `cases` are both fine.
- **The summary line parses.** `check_selftest_counts.printed_total` reads `18/18 … passed`.
- **The `importlib` snippet works.** Run verbatim against a hyphenated `check-features.py`:
  `import OK: <function parse_features …> <class 'check_features.Node'>`. The module name
  `"check_features"` also keeps `__name__ != "__main__"`, so importing does not trigger `main()`.
- **All four mutation `edits` anchors match the delivered source exactly once** — indentation
  included (8 / 12 / 12 / 4 spaces). `check-plan-code.py:1297` refuses a multi-match anchor and
  `:1307` an absent one; neither fires. The manifest's JSON shape (`name`/`file`/`edits`/`expect`)
  matches `scripts/mutations/check-anchors.json`. The trailing `\n` in each anchor is harmless.
- **Task 2's `anchors.md` column risk does not materialise**, in either consumer — finding 12.
- **The spec's measured claim about area drift holds.** `backlog_areas` over the live file returns
  21 areas including **both** `(cloud/money)` and `(cloud / money)`, exactly as `spec:124-125` says.
- **`_anchor_slugs`** (plan `:454-455`) matches all 13 registry rows and nothing else.
- **`main()`'s three cannot-run arms are genuinely fail-closed** (missing file, zero nodes, zero
  areas → `return 2` with `Treat this as NOT RUN.`), which satisfies `spec:170` and `spec:179`.
- **`check-features.py` satisfies the guard half of the ratchet contract** — R1, R3 (CI step from
  Task 6 Step 1; `invocation_re` requires a real `python3 …` invocation and the step provides one),
  R4. Only `gen-features-page.py` violates, and by a different rule (finding 4).
- **Architecture: one parser, imported not duplicated.** The `check-features.py` owns / page imports
  split is the right call and matches `check-dashboard-entry.py`'s precedent as the plan claims.
- **Task 5's hook** copies `regen-goals-page.sh` and keeps `exit 0` on every path, which matches
  `.claude/hooks/regen-goals-page.sh`'s contract.

**One design observation that is not a code defect but is worth the author's eye.** `spec:74-76`
makes *job queue & worker lifecycle* the headline case — *"the busiest area of the last month … and
**no anchor, spec node or design document claims it**. An absence is only visible against a structure
that expected something there."* Task 1 Step 5 (`:263-266`) then gives exactly that node
`anchors: cloud-publishing`, solely because `built` requires ≥1 fragment. The plan's first concrete
data contradicts the spec's central finding, and does so by attributing the node to an anchor the
spec says does not claim it. If the honest state is "built, but nothing declares it", the tree has no
way to say so — which may be a third node state worth having, or an argument that the busiest area
should get its own anchor before the tree ships.

---

## What I could not run (treat every line as NOT VERIFIED)

- **`python3 scripts/check-plan-code.py --mutate .` end to end.** It stages `HARNESS_TREE` into a
  temp copy and spawns suites; running it with the planned files injected would mean writing them
  into this checkout, which the brief forbids. Findings 2 and 3 were established against the harness's
  own functions (`parse_fail_names`, and the `EXPECTED_MUTATIONS` rule at `:1145-1154`) rather than by
  a full run. **Whether the 4 mutations would each be killed by the case they name is UNMEASURED** —
  I only established that their kills could not be *attributed*.
- **Task 4's `render()`.** No implementation exists to run; Step 3 is prose describing four fragment
  resolvers. The six cases were read, not executed. Anything about the page's actual output is
  unverified.
- **Task 5's hook.** Not written; `regen-goals-page.sh` was read, not adapted and run.
- **`docs/features.md`'s full tree.** Only the 2-node minimal tree from Task 1 Step 5 exists in the
  plan, and I did not attempt Task 2's mapping of 13 anchors onto invented slugs — so whether the real
  tree can satisfy `check_cross` (all 21 areas claimed exactly once, every anchor resolving) is
  **unknown**. It is the largest unmeasured risk left in this plan.
- **`scripts/check-docs.py` against a new `docs/features.md`.** Not run — the file does not exist. Its
  `LINE_BUDGETS` covers only the `CLAUDE.md` @-includes, so `features.md` is unbudgeted, but its link
  and table rules were not exercised.
- **The live `/features` page and the explainer server.** Not started.

No file outside `docs/reviews/claude/` was modified; all scratch work was in `/tmp/fhr1/` and is
deleted.

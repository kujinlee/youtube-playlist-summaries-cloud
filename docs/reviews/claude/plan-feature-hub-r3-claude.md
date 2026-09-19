# Claude adversarial review — feature hub PLAN — round 3

Subject: `docs/superpowers/plans/2026-09-19-feature-hub.md` + `docs/superpowers/specs/2026-09-19-feature-hub-design.md` at HEAD `4fe8952b`.
Reviewer: Claude half, round 3, last half of the round. Codex's round-3 half ran first and its findings were folded; this half reviews the plan *and those fixes*.

## Verdict: FINDINGS — 2 Blocking, 0 High, 1 Medium, 4 Low

## Does this round add any new Blocking or High? — **YES. Two Blocking.**

**The Phase 2 gate is NOT met.** The plan's code is in good shape — it runs `24/24`, all five
mutations kill through the case each names, and the real run behaves exactly as the plan says. The
two Blockings are both about **registration with this repo's existing guards**, and they are the same
class as review r1's *"three of its gates were red on arrival"*:

- **Blocking 1 is new damage from round 3's own fix.** The r3 High put four *directory* paths into
  `PAGE_SOURCES["features"]`. `explainer-serve.py`'s self-test asserts every declared source
  `is_file()`, so it goes red — measured `202/202 → 201/202` over a control proved green first — and
  that redness cascades into two CI steps and makes `check-plan-code.py --mutate .` refuse to run at
  all. Worse, the `/_stale` handler **filters non-files out**, so the four directories buy nothing:
  the staleness blind spot r3 set out to close is still exactly as wide as it was.
- **Blocking 2 is pre-existing and newly found.** Task 6 Step 3 says "the **two** ratchets that pin
  them". There are **five** pinned literals across **three** ratchets. Measured: applying every
  registration the plan specifies leaves four CI steps red.

This is the fifth consecutive round whose findings include one created by the previous round's fix.

---

## Did the plan's code run? — yes, 24/24

Assembled in `/tmp/fhc3/` exactly as an executor reading the tasks in order would: Task 1 Step 1's
block (`:66`) written to `scripts/check-features.py`; Task 1 Step 3's block (`:174`) inserted above
`_self_test`; Task 2 Step 1's block (`:349`) appended into `_self_test` immediately before the summary
`print`; the docstring raised `# 16 cases` → `# 24 cases`; Task 2 Step 3's block (`:382`) inserted at
module level above `_self_test`; the entry point replaced with `:474`.

| Run | Expected by the plan | Printed |
|---|---|---|
| Task 1 Step 2 (harness only) | `NameError: name 'parse_features' is not defined` | **exactly that**, rc=1 |
| Task 1 Step 4 (parser added) | `16/16 self-test cases passed` | **`16/16`**, rc=0 |
| Task 2 Step 4 (cross-file rules) | `24/24 self-test cases passed` | **`24/24`**, rc=0 |

**Two places where I had to make a choice, both harmless, one of them load-bearing later** — see
Low 6. Task 1 Step 3's block re-declares five things Step 1's block already contains; Task 2 Step 3's
block opens with `import pathlib   # add to the existing 'import re, sys' line`, which is an
instruction to merge rather than a line to paste. Pasting both verbatim works.

### The mutation manifest — 5/5 killed, each through the case it names, over a green control

Control first: `24/24`, rc=0. Then each of the five manifest edits applied to the assembled source:

| Manifest entry | Anchor matches | Result | `[FAIL]` names printed | Exact match to `expect`? |
|---|---|---|---|---|
| a built node with no fragment stops failing | **1** | KILLED 23/24 | `a built node with no fragment fails` | ✅ |
| an absent node may carry fragments again | **1** | KILLED 23/24 | `an absent node WITH a fragment fails` | ✅ |
| status tokens stop being rejected in node prose | **1** | KILLED 23/24 | `a status token in prose fails` | ✅ |
| a built node may carry an absence argument again | **1** | KILLED 23/24 | `a built node carrying expected-because fails` | ✅ |
| an unclaimed backlog area stops being reported | **1** | KILLED 23/24 | `an in-use area claimed by nobody fails` | ✅ |

Every anchor resolves **exactly once** — not zero, not twice — and every `expect` list is an *exact*
set match against the red cases, so no mutation is credited to a sibling case.

### The real run, against today's repo

`docs/features.md` from Task 1 Step 5 plus the real `docs/anchors.md` and `docs/backlog.md`:

```
FAILED — 34 feature-map problem(s):
  ✗ anchor `cloud-publishing` is claimed by 2 nodes: job-queue-and-worker-lifecycle, wake-on-visit
  ✗ backlog area `(cloud / money)` is claimed by no node …
  ✗ backlog area `(cloud/money)` is claimed by no node …
```

21 backlog areas, 13 anchors (12 unclaimed + `cloud-publishing`), both duplicate spellings of
`cloud/money` visible side by side exactly as the spec predicts. The plan's `FAILED — N` (r3's fix
replaced the unowned `33`) is honest, and the duplicate-anchor line is its own starter tree firing.

---

## Codex round 3's three findings — closed or not

| # | Finding | Status |
|---|---|---|
| High 1 | stale sources omit fragments the page derives | **NOT CLOSED — the fix is defective. See Blocking 1.** The hook half is closed and correct; the `PAGE_SOURCES` half breaks a green guard and delivers none of the staleness detection it claims. |
| Medium 2 | post-swap numbering | **CLOSED.** `:56` now says Task 3; the self-review's placeholder scan says Task 3's; Task 3's steps are 1-2-3-4. `grep -n "Task [0-9]"` finds no surviving inversion. |
| Low 3 | unowned numeric claims | **CLOSED as filed.** `:308` is `16/16`; the `39 suites` figure is gone from the code comment; the spec's `140` is now "one edit per backlog row". Other unowned numbers remain — Low 7. |

---

## Findings

### [Blocking] 1 — The r3 fix puts four DIRECTORIES into `PAGE_SOURCES`, which turns a green guard red, cascades into four CI steps, and still does not detect the staleness it was written to detect

**Evidence — measured, over a control proved green first.** `scripts/explainer-serve.py` copied to a
temp tree with the repo's `docs/` symlinked in:

```
CONTROL   (pristine)                    self-test: 202/202 passed    rc=0
PATCHED   (Task 4 Step 5 applied)       self-test: 201/202 passed    rc=1
            [FAIL] ...and every declared source is a real file in the repo
```

The case is `scripts/explainer-serve.py:1482-1484`:

```python
case("...and every declared source is a real file in the repo",
     lambda: [s for ss in PAGE_SOURCES.values() for s in ss
              if not (REPO / s).is_file()] == [])
```

and the four new entries are directories, permanently:

```
docs/adr                  exists=True  is_file=False is_dir=True
docs/superpowers/specs    exists=True  is_file=False is_dir=True
docs/superpowers/plans    exists=True  is_file=False is_dir=True
docs/reviews              exists=True  is_file=False is_dir=True
```

**This is not one red case.** With *every* registration the plan specifies applied to a faithful temp
tree (both new scripts, the manifest, the `EXPECTED_MUTATIONS` entry, the `POPULATION` entries, the
two `explainer-serve.py` dicts, the two `ci.yml` steps):

| Guard | control | after the plan | CI step |
|---|---|---|---|
| `explainer-serve.py --self-test` | 202/202 rc=0 | **201/202 rc=1** | via the two below |
| `check-selftest-counts.py` | rc=0 | **rc=1** — `explainer-serve.py: --self-test exited 1 … Fix the suite first.` | `ci.yml:275` |
| `check-plan-code.py --mutate .` | — | **CANNOT RUN** | `ci.yml:390` |

The `--mutate .` consequence is the sharpest one and it is structural, not incidental.
`scripts/mutations/explainer-serve.json` exists and `"scripts/explainer-serve.py": 46` is in
`EXPECTED_MUTATIONS` (`check-plan-code.py:923`), so `explainer-serve.py` is a **control target**.
`control_is_green` (`:331`) is `rc == 0 and "passed" in out` → False, and `mutate_delivered`
(`:1208-1214`) then returns

> `CANNOT RUN — control run of … did not prove the suite works (exit 1) BEFORE any mutation was applied. Every verdict below would be an artefact.`

for the **whole run**. So Task 6 Step 4 cannot be performed, and no manifest in the repo gets measured
— including this plan's own five.

**And the change buys nothing it was written to buy.** The `/_stale` handler
(`explainer-serve.py:1176-1178`) is:

```python
newest, newest_src = max(
    ((REPO / s).stat().st_mtime_ns, s) for s in sources
    if (REPO / s).is_file())
```

Directories are **filtered out**. Even if the self-test case were relaxed, editing a spec, an ADR or a
review would move no timestamp the banner compares, and `/features` would still report itself fresh —
which is precisely Codex r3 High 1's complaint, unrepaired. (Listing the directories literally would
not work either: a directory's mtime moves when an entry is added or removed, never when a file inside
it is edited.)

**The root cause is a category error in the fix's own sentence.** `PAGE_SOURCES` is not "the watched
set". It is the file list the `/_stale` **banner** compares mtimes against, and its docstring says so
— *"Paths are REPO-RELATIVE … the source is a file in git"*. The hook is the regeneration mechanism and
takes glob patterns. The repo already ships the asymmetry deliberately: `gen-goals-page.py` derives
from **five** source families and `PAGE_SOURCES["goals"]` is `["docs/roadmap-to-launch.md"]` — one
file — while `regen-goals-page.sh` watches all five. ⛔ **THE WATCHED SET MUST EQUAL THE DERIVED SET**
(plan `:630`) asserts an equality the existing design does not hold and cannot express, and the
instruction one screen later that the hook's `case` list "must match `PAGE_SOURCES["features"]`
exactly" is literally unsatisfiable: `docs/adr` (every file) and `*/docs/adr/*.md` (only `.md`) are
different sets.

**Introduced by an earlier round's fix?** **Yes — entirely by round 3's.** Before `4fe8952b` the entry
was `["docs/features.md", "docs/anchors.md", "docs/backlog.md"]`, three real files, and every guard
above was green.

**Fix — one of these two, not a patch of the list.**

- **(a) Keep the two mechanisms separate and say so.** `PAGE_SOURCES["features"]` stays the three real
  files; the hook keeps the full seven-pattern `case` list it now has (that half is correct and is the
  half that actually rebuilds the page). Then state the residual honestly in Task 4 Step 5: *the
  `/_stale` banner can only see the three whole-file sources; a spec, ADR or review edit rebuilds the
  page through the hook but will not raise the banner if the hook did not run.* This matches `/goals`
  and needs no change to a guard.
- **(b) Teach `/_stale` about directories** — expand each entry with `rglob` and take the max over the
  files found. That is a real change to `explainer-serve.py`: it needs its own task, its own cases,
  an edit to `_stale_sources_covered`'s second case, and an entry in
  `scripts/mutations/explainer-serve.json`, and it walks four directory trees on every `/_stale` poll.

(a) is the cheaper and, given `/goals`' precedent, the more honest. Whichever is chosen, delete the
"must equal" and "must match exactly" sentences — they are what produced the defect.

---

### [Blocking] 2 — Task 6 Step 3 names "the two ratchets that pin them". There are five pinned literals across three ratchets, and the three it omits are all CI-enforced

**Evidence — measured in a temp tree with a green control (128/128, 67/67, rc=0), then with every
registration the plan specifies applied.**

**(i) `scripts/check-plan-code.py` pins `EXPECTED_MUTATIONS` in two more places than the plan knows
about.** Adding `"scripts/check-features.py": 5` exactly as Task 6 Step 3 item 1 instructs:

```
CONTROL   python3 scripts/check-plan-code.py --self-test   128/128 passed   rc=0
AFTER     python3 scripts/check-plan-code.py --self-test   126/128 passed   rc=1
  [FAIL] the declared counts name every manifest that ships: … 'scripts/check-features.py' …
  [FAIL] the declared counts are the real ones: got 742 want 737
```

- `check-plan-code.py:2623` — `sorted(EXPECTED_MUTATIONS)` is pinned against a **literal key list**.
- `check-plan-code.py:3262` — `case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 737)`.

`ci.yml:396` runs that suite, and `check-plan-code.py` is in `check-selftest-counts.py`'s
`POPULATION`, so the redness is reported twice.

**(ii) `scripts/check-fixture-variation.py` auto-discovers both new scripts and fails on arrival.**
Its `population()` (`:127-139`) globs every `scripts/*.py` defining `_self_test` or `self_test`, and
`population_drift` (`:120-122`) makes an ARRIVAL **a finding, exit 1**:

```
CONTROL   python3 scripts/check-fixture-variation.py
          fixture variation OK — 551 parameter(s) examined across 52 file(s)   rc=0
AFTER     FAILED — 2 parameter(s) never varied by any case:
  ✗ check-features.py: newly discovered and not pinned. Examine it and add its key set to EXAMINED_KEYS …
  ✗ gen-features-page.py: newly discovered and not pinned. …
                                                                                rc=1
          python3 scripts/check-fixture-variation.py --self-test   66/67 passed   rc=1
  [FAIL] every discovered file has a pinned key set, and vice versa
```

Both are CI steps (`ci.yml:287` and `:289`), and both are also reported by `check-selftest-counts.py`.

**The full end state of the plan, measured:**

| CI step | Result after every registration the plan specifies |
|---|---|
| `ci.yml:287` check-fixture-variation | **rc=1**, 2 findings |
| `ci.yml:289` check-fixture-variation self-test | **rc=1**, 66/67 |
| `ci.yml:275` check-selftest-counts | **rc=1**, 3 problems |
| `ci.yml:390` check-plan-code --mutate . | **CANNOT RUN** (Blocking 1) |
| `ci.yml:396` check-plan-code self-test | **rc=1**, 126/128 |
| `check-ratchet-contract.py` | rc=0 ✅ — r2's reading holds, `MANIFEST_BASELINE` stays 0 |

**Introduced by an earlier round's fix?** No — pre-existing since r1's fold, and missed by both halves
of rounds 1, 2 and 3. I am filing it Blocking rather than High because the plan makes an explicit,
measured-sounding completeness claim about exactly this — *"Neither is optional; review r1 measured
both as red-on-arrival"* — and the claim is wrong in the same direction r1's finding was: the
enumeration, not the instance.

**Fix.** Rewrite Task 6 Step 3 as five registrations, each with its file and the reason it exists:

1. `check-plan-code.py` `EXPECTED_MUTATIONS` — `"scripts/check-features.py": 5` (full path).
2. `check-plan-code.py:2623` — add `"scripts/check-features.py"` to the pinned key list, in sorted position.
3. `check-plan-code.py:3262` — `737` → `742`.
4. `check-fixture-variation.py` `EXAMINED_KEYS` — add key sets for **both** `check-features.py` and `gen-features-page.py`.
5. `check-selftest-counts.py` `POPULATION` — bare names for both (as the plan already says).

⚠ On (4): the guard's own error message says to run
`python3 scripts/check-fixture-variation.py check-features.py` to see what it examines. That resolves
`paths` relative to **cwd**, so from the repo root it answers
`CANNOT RUN — population is empty or unreadable` — the command only works from inside `scripts/`.
Pre-existing wrinkle in that guard, but the plan should carry the working invocation so the executor
does not lose twenty minutes to it.

And add a Step 0 to Task 6 that is the durable version of this finding: *before registering, run each
of the guards above against a control and name every literal that moves.* An enumeration nobody
re-derives is how this defect survived three rounds.

---

### [Medium] 3 — Review r2's High 1 is still only half closed: both worked examples were fixed, the documentation that made them wrong was not

**Evidence.** r2 High 1 found the spec's `absent` example and Task 3's `dig-job-recovery` example
rejected by the plan's own grammar, and named the root cause one line up: *"Both examples are faithful
to their own documentation; the documentation is what is wrong."* Its fix list had four items.

The two **example** items were done — Codex r3 claim 4 re-measured both as parsing clean, and so did I.
The two **documentation** items were not:

- Spec `:86-89`, the state table, still reads:

  | State | Must have | Must NOT have |
  |---|---|---|
  | `built` | ≥1 fragment | — |
  | `absent` | a one-line `expected-because:` | any fragment |

  `for:` is absent from **Must have** for both states, and `check_nodes` (plan `:248-249`) rejects any
  node without one.
- Plan `:25`, Global Constraints, still reads *"`built` (≥1 fragment, no `expected-because:`) or
  `absent` (an `expected-because:` line, zero fragments)"* — same omission.
- **The one-line-per-field rule is documented nowhere in either document.** `grep` finds it only
  inside the parser's own error string (plan `:222-224`). The spec's enforcement table gets closest
  with "prose present", which covers `for:` obliquely and says nothing about wrapping.

**Introduced by an earlier round's fix?** No — it is r2 High 1 fixed as two instances rather than as
its stated class, which is this repo's recorded *"after fixing, SEARCH for the class"* shape, and it
is the **second** time this same defect has been fixed instance-only (r1 fixed the fixture; r2 fixed
the two examples; nobody fixed the rule).

**Why it matters.** `expected-because:` reasons are inherently long — Task 3's own is 200 characters —
so it is the field most likely to wrap and the one with the least warning. The next author to write a
node wraps it, the check goes red on a rule neither document states, and the cheapest-looking repair
is to weaken `check_nodes`. Task 3 Step 2 is an open-ended authoring step; this is exactly where an
unstated grammar rule costs something.

**Fix.** Spec `:86-89`: `for:` into **Must have** for both rows, plus one sentence beside the table —
*"every field is one line; a wrapped continuation is refused, because it would hide its own status
tokens from the check."* Plan `:25`: the same sentence in Global Constraints.

---

### [Low] 4 — The page's build time is required by a note in the *registration* step, specified in no rendering step, and asserted by no case

Task 4 Step 5's new ⚠ (`:636-639`) makes the `git log` bound acceptable by requiring that *"the page
therefore prints its own build time"*. Step 5 is about `explainer-serve.py`'s two dicts. Task 4
**Step 3**, which is where an executor writes the renderer, lists four fragment kinds and does not
mention a build time; Step 1's six cases do not assert one; and the declared `# 6 cases` is pinned by
`check-selftest-counts.py`, so adding a case means editing the docstring too.

It is reachable rather than missing: `page_chrome.provenance()` exists and already emits
`generated <time> · <sha>`, `gen-goals-page.py:1216` calls it, and Step 3 does say to reuse that
file's theme/header approach. So this is an under-specification, not a hole. Move the requirement into
Step 3 beside the other things the page must render, and add a seventh case asserting the stamp
appears — raising the declared count to 7 in the same edit.

### [Low] 5 — Two of the four new watched families are watched on an assumption Task 4 Step 3 does not state

Task 4 Step 3 says ADRs are resolved *"via the anchors named on the node: read `docs/anchors.md` for
the ADR numbers"*. `docs/anchors.md` carries an `ADR(s)` column (`:28-32`), so the **numbers** come
from `anchors.md` — nothing in Step 3 says a file under `docs/adr/` is ever opened. If it is not, then
`docs/adr` is watched but not derived, which is the mirror of the defect r3 filed.

Similarly, reviews attach by *"filename stem"*, so the derived output changes when a review file is
**created or renamed** and not when its content is edited — yet the hook fires on every write under
`docs/reviews/` including the `verdicts/*.json` files the review wrapper writes. Harmless noise, but
say which it is: Step 3 should state whether ADR titles are read from the ADR files, and whether
reviews are stem-only.

### [Low] 6 — Task 1 Step 3's block re-declares five things Step 1's block already contains; pasted verbatim the delivered file ships two copies, and the duplication is a live hazard for the next mutation

Step 1's block (`:66-163`) contains `import re, sys`, `from dataclasses import dataclass, field`, the
`STATUS_TOKENS` comment and regex, `FIELD`, and the whole `Node` dataclass. Step 3's block (`:174-270`)
opens by repeating **all five** verbatim before `parse_features`. "Insert above `_self_test`" pasted
literally produces a file with two of each. It runs — I ran it, `16/16` — because the second binding
wins and both are identical.

The reason it is worth a line rather than nothing: `check-plan-code.py:1297` **refuses** any manifest
anchor matching more than once —

> `mutation 'X': anchor matches 2 times in <file> — only the FIRST is replaced, so a 'caught' verdict would not be about the line you named. Tighten it`

None of the five current anchors lands in the duplicated region, so this is latent, not live. But the
duplicated region contains `STATUS_TOKENS = re.compile(` — the rule most likely to acquire a mutation
next. Have Step 3 say "insert `parse_features` and `check_nodes` above `_self_test`" and drop the
repeated preamble from its block.

### [Low] 7 — Three unowned or stale items left in the two documents

- **Spec `:201`** — *"rendering 2,743 test names was the first design considered"*. The roadmap's
  current figure is **2,892 unit / 278 suites** (`docs/roadmap-to-launch.md:2045`). A number in prose
  with no owner, describing a rejected design. Say "every test name" or take the roadmap's figure.
- **Spec `:191`** — the first Falsifier still reads *"Delete a node that `anchors.md` references"*.
  `anchors.md` references no nodes; the edge points node → anchor. **This is r2's Low 8, unclosed.**
  It is true by accident while describing a mechanism the r1 amendment deleted.
- **Plan `:545`** — `git commit -F /tmp/t2.txt`, and `/tmp/t2.txt` is never written anywhere in the
  plan (`grep` finds `t1.txt` twice, with its body, and `t2.txt` once, without). **r2's Low 6, second
  half, unclosed.** Either write the body or drop the `-F` and let the executor compose it.

---

## Things I checked and found correct

Every item verified by running something or opening the cited file, never by reading the plan's claim.

- **The assembled suite: `NameError` → `16/16` → `24/24`**, all three exactly as the plan predicts, and
  the docstring count raised 16 → 24 in the step that adds the cases.
- **All five mutation anchors resolve exactly once, kill, and attribute exactly** — full table above,
  over a control proved green first. Codex r3's claim 3 independently reproduced.
- **The new `built` + `expected-because:` rule** (`:259-261`) is real, its case `a built node carrying
  expected-because fails` (`:146`) is real, and its mutation kills through that case and no other. r2's
  Medium 4 is closed properly — option (a), with count 23 → 24 and `EXPECTED_MUTATIONS` 4 → 5, as
  filed.
- **The real run** — 34 problems, 13 anchors, 21 backlog areas, both spellings of `cloud/money` shown
  side by side. The plan's `FAILED — N` no longer asserts a number it cannot own, which closes r2's
  Low 7.
- **`check-ratchet-contract.py` is satisfied at the end of Task 6.** With the manifest present the only
  violation delta against a control is `check-features.py [R3_no_caller]`, an artefact of my tree
  lacking the Task 6 Step 1 CI step; with the CI steps added it reports `rc=0`, `0 R4 manifest debt,
  baseline 0`. `gen-features-page.py`'s `NO-MUTATIONS:` escape is accepted and costs no baseline edit
  — r2's reading of `MANIFEST_BASELINE` holds.
- **`check-selftest-counts.py --self-test` stays 18/18** with both new names added to `POPULATION`; that
  registration has no pinned literal behind it. (Its *real* run goes red, but only as a consequence of
  Blockings 1 and 2, not of anything in item 2 of Task 6 Step 3.)
- **Task 5's hook, both halves.** The `case` list is correct bash: `docs/features.md` matches the bare
  alternative, absolute paths match the `*/…` alternative, and `*` matches `/` in a `case` pattern so
  `docs/reviews/*` does reach `docs/reviews/claude/foo.md`. Both Step 2 invocations behave as stated —
  `docs/features.md` takes the regeneration path, `README.md` falls to `*) exit 0` and is silent, both
  exit 0. `regen-goals-page.sh` is the right template: it already carries the `set -uo pipefail`, the
  python `file_path` extraction, the `|| exit 0`, and the never-blocks discipline.
- **Task 5 Step 3 is actionable.** `.claude/settings.json` registers `regen-goals-page.sh` under
  `PostToolUse` with matcher `Edit|Write`; "matching that entry's event and matcher exactly" resolves
  to something real.
- **Task 6's ordering.** Nothing it registers depends on a file a later step creates: the manifest
  (Step 2) precedes its `EXPECTED_MUTATIONS` entry (Step 3); `gen-features-page.py` exists from Task 4
  before Step 3 pins its count; Step 4's mutation run follows both; Steps 5 and 6 only confirm. The
  CI steps in Step 1 land before Step 5 asks `check-ratchet-contract.py` for a caller.
- **The two `ci.yml` steps match the `check-anchors` pair's shape** at `:183-186` exactly.
- **`docs/features.md` under `check-docs.py`** — `Documentation integrity OK` with the Task 1 Step 5
  tree present, confirming r2's reading that only `check_living_links` applies and the file is not
  red on arrival.
- **The Task 2/3 swap is fully swept.** `grep -n "Task [0-9]"` over the plan finds no surviving
  inversion; the self-review's fifteen-row coverage table reads 3 / 2 / 2 / 2 / 2 on the five rows r2
  found inverted; Task 3's steps are 1-2-3-4; `git add docs/anchors.md` is gone.
- **Both worked node examples parse clean** — the spec's `rate-limiting-per-account` and Task 3's
  `dig-job-recovery` each yield zero problems from `parse_features` + `check_nodes`. Task 4's inline
  fixture too.
- **`now` is gone from the banned list in the plan, the spec and the code**, and the spec records why.
- **PR #322 exists** (`e693f36a … (#322)`), so Task 6 Step 4's *"this happened four times in PR #322"*
  references a real merged PR rather than a forward reference.

## What I could not run

- **Nothing is implemented.** Everything above is the plan's extracted code run in `/tmp/fhc3/`, plus
  the repo's own guards run in faithful temp trees at `/tmp/fhc3b/`, `/tmp/fhc3e/` and `/tmp/fhfinal/`
  (all scripts copied, `docs/`, `supabase/`, `node_modules/typescript` symlinked, `.github` and
  `.claude/hooks` copied, `$HOME` redirected so no suite could reach `~/explainers/`). No file outside
  `docs/reviews/claude/` was written; `git status` is clean apart from this review.
- **`gen-features-page.py`'s 6 cases.** Task 4 specifies the cases but not `render`, so the suite still
  cannot be assembled. For the guard measurements above I substituted a one-case stub with the
  plan's declared docstring and `NO-MUTATIONS:` reason — enough to measure *discovery* by
  `check-fixture-variation.py` and `check-ratchet-contract.py`, not enough to measure its content. The
  `6/6` claim remains the one stated result in this plan that is still a prediction.
- **`check-plan-code.py --mutate .` end to end.** I measured its control gate by reading
  `control_is_green` (`:331`) and `mutate_delivered` (`:1208-1214`) and by measuring the red control
  they consume; I did not run the full ~740-mutation sweep.
- **CI itself**, the hook as a live `PostToolUse` registration, and `/features` in a browser.

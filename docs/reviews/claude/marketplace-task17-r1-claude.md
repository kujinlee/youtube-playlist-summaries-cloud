Reviewed head: 94e9fd084beebb153dd87293554b481426d0df14

# Round 1 — `marketplace-task17` — Claude half (adversarial)

Subject: plan Task 17 of `docs/superpowers/plans/2026-11-11-marketplace-inventory.md` (marketplace slice F), PR #616,
branch `marketplace-task17`. The diff against `origin/master` touches four files: `docs/marketplace/inventory.json`
(new: six effort (2) rows and `engine_comparison`), `docs/dashboard-entries.md`, `docs/goal-threads.md`, and the plan
tick. I checked the rows against `docs/marketplace/scan-2026-11-17.json` (`measured_at` 637950d2), `components.json`,
`shipping-sets.json`, `docs/portable-practices.md` and the code they describe. `check-plan-code.py`,
`sweep-red-alert.py`, `coverage_verdict.py` and `ci.yml` are byte-identical at HEAD and at the scan commit (checked
by `diff` against `git show 637950d2:<file>`). I re-fetched 13 of the 15 cited engine pages, plus the StrykerJS
configuration page, through web-fetch subagents told to refute each sentence.

## Mechanical checks (the Task 19 rules that apply to an effort (2) row)

| Rule | Result |
|---|---|
| every `cites` id was emitted by the scan | ✅ all 17 cite ids resolve (script over `scan.components[*].findings[*].id`) |
| `practice_entry` names an existing heading | ✅ both match exactly after stripping `## ` (`## 22. A kill that attributes…`, `## 10. A surviving mutation…`) |
| no row graded `measured` | ✅ all six are `argued`, and both cost grades are `argued` too |
| both estimates present and > 0 | ✅ |
| every non-ship row has a `route` | ✅ all six (none is SHIP) |
| `data` rows have C4 `struck` | ✅ mutation-manifests and velocity-docs |
| `phase` is `"1"` or `"later"` | ✅ all `later`, matching `components.json` |
| one row per effort (2) component in the map | ✅ the six `package: ci-layer` components. `fixture-git` is in the ci-layer shipping set but is an effort (3) component, so it gets no row here |
| roles match `components.json` | ✅ |

**Task 17's FAILS IF does not fire.** Every engine capability sentence either has a fetched source or is marked
`unverified`. C6 to C8 below are sentences whose wording goes beyond the page they cite. None of them names a capability
that no fetched page has.

## Findings

### C1 — MAJOR: the `coverage-verdict` row is argued from a coupling that does not exist. The module is not a parser of the engine's output, and nothing in the sweep step imports it

**The claim** (`inventory.json`, row `coverage-verdict`): *"its mentions are the guard name check-plan-code, because it
reads the verdict lines check-plan-code.run_mutations prints. C3 fail, argued from that coupling: the parser is bound
to our engine's output format."* Its scenario says it is *"imported by sweep-red-alert.py (line 442) in the
mutation-sweep-complete step"*. Its route says it should parse *"the documented record schema rather than our engine's
stdout"*. The dashboard entry repeats the claim as *"the parser it reads"*.

**What the code says:**

- `scripts/coverage_verdict.py` imports only `sys`, `dataclasses` and `__future__` (lines 68–71). It is the verdict
  *type* (`Measured`, `NotMeasured`, `not_measured_reason`). It parses nothing.
- The dependency runs the other way. `scripts/check-plan-code.py:104-109`: *"THE DEPENDENCY RUNS ONE WAY ONLY …
  this file imports it and never the reverse"*, followed by `from coverage_verdict import (Measured, NotMeasured, …)`.
- Its four mentions of `check-plan-code` are comments and docstrings. The one at line 217 is about **its own
  self-test's** failure-line format, which has to match the engine's kill parser so that mutations OF
  `coverage_verdict` are attributed. That is the engine reading this module's test output. It is not this module
  reading the engine's output.
- `sweep-red-alert.py:442` (`import coverage_verdict as _cv`) is inside `_self_test_body` (lines 339–592). The ci.yml
  step at line 1628 runs `python3 scripts/sweep-red-alert.py`, which is `main()` (line 593). Nothing at runtime
  imports `coverage_verdict` (grep: line 442 is the file's only import of it).

The scan emitted **zero** findings for this component, and the code agrees: by spec §4's C3 (*"does not depend on
parts of this repo that are not shipping"*) the module passes. The row's only cite, `sweep-red-alert:4:1`, is
`sweep-red-alert`'s self-test loading `check-plan-code.py` (`_writer`, line 332). It says nothing about
`coverage_verdict` either way. So the non-ship verdict has no supporting evidence, and its route and scenario describe
a path that does not exist.

**Fix:** re-argue the row from the code. C3 passes. The only runtime importer is `check-plan-code` (the entry-point
its C4 inherits from, spec §4), so the scenario should name that importer. The verdict then follows from what is
decided about that consumer (for example, ship as a library of whatever engine-agnostic layer replaces the engine,
or harvest the "a type you cannot read wrongly" lesson). Drop the "parse the record schema rather than our stdout"
route, and correct *"the parser it reads"* in the dashboard entry.

### C2 — MINOR: `sweep-red-alert`'s note describes self-test code as runtime coupling. All three of its cites are inside `_self_test`

The note says *"sweep-red-alert:4:1 is its importlib load of check-plan-code.py … it also imports coverage_verdict"*,
and the route says it should read a schema *"instead of loading our engine"*. The C2 argument cites
`sweep-red-alert:6:1` (git). Measured:

- `:4:1` (line 332) is inside `_writer()`, which only the self-test calls (line 441).
- `:2:1` (line 496) and `:6:1` (line 471) are inside `_self_test_body` (lines 339–592).
- `main()` and its helpers need only the standard library plus `gh` through `subprocess` (lines 41–49, 189).

**The C3 fail still holds, but for a different reason than the note gives.** The runtime reader is bound to the
engine's record format: `RECORD_SCHEMA = 1` (line 58) is *"`check-plan-code.shard_record` writes this"*, and
`record_problem` accepts exactly five keys. The shipped file's `--self-test` also cannot run without the engine. So
the verdict stands. But the note's description of the runtime is wrong, and the 6 h route estimate prices an engine
load that never happens at runtime.

**Fix:** argue C3 from `RECORD_SCHEMA` and the five-key record contract, plus the self-test's dependency on the
engine. Say that the cites are self-test lines, and re-estimate the route.

### C3 — MINOR: `check-plan-code`'s C3 cites are its own self-test internals, and the `unread` cite is mislabelled

The verdict is correct by definition: spec §2c, line 152, says *"depending on our engine is a C3 failure"*, and this
component IS the engine. But the evidence quoted for it does not show what the note says it shows:

- `:4:1` / `:4:2` (lines 8162/8165) are in `_copy_run`, a self-test helper that writes the file's own source into a
  temporary copy and runs it. A program that runs a copy of itself is portable.
- `:6:1` (line 3995) is the self-test saving and restoring `PC495_STATE`, a variable the same test sets for its own
  fake suite (lines 3947, 3969). A stranger never has to provide it, so it is not a variable this repo "defines" for
  a stranger.
- `:2:1` is called *"one of ten unread repo paths"*. Detector 2's `unread` kind is a load the reader could not
  resolve. In `check-publishability.py`'s own words (the `_invocations` docstring, around line 420), that is *"an
  unjudged coupling … shown, never counted as none"*. It is not evidence of a repo path.

The strongest C3 evidence is `HARNESS_TREE` (line 471: `"scripts"`, `"supabase"`, `"docs"`,
`"node_modules/typescript"`, …), and the scan emitted no finding for it.

**Fix:** describe each cite accurately. Rest C3 on spec §2c and `HARNESS_TREE`, and say that `HARNESS_TREE` has no
scan finding (a scan BOUND).

### C4 — MINOR: `mutation-sweep-job` cites two `verify`-job steps for the sweep, against its own bound, and the 104 / 4 split is wrong

Job boundaries in `ci.yml` at the scan commit: `verify` runs from line 58 to 1116, `mutation-sweep` from 1117 to 1532,
and `mutation-sweep-complete` from 1533 on. The note says *"104 of its 108 scan findings are outside-set paths of OTHER
jobs' steps and do not bear on the sweep"*. But:

- `:2:98` (line 1024, `check-plan-code --self-test`) and `:2:21` (line 471, `fixture_git --self-test`) are `verify`
  steps. They are cited as sweep C3 evidence, although by the note's own reasoning they do not bear on the sweep.
- `:2:106` (line 1432, `check-python-pin.py`, `outside-set`) is inside the `mutation-sweep` job. So at least one
  outside-set finding does bear on the sweep, and it is not cited.

The C3 fail rests safely on `:2:107` (line 1515) and `:2:108` (line 1628).

**Fix:** cite `:2:106`, `:2:107` and `:2:108`, drop `:2:98` and `:2:21`, and restate the split (findings at line 1117
or later: 3 of 108).

### C5 — MINOR: `mutation-manifests` cites `check-plan-code:4:1`, which has nothing to do with manifests

`check-plan-code:4:1` is the self-test writing a copy of the engine (C3 above). It does not read a manifest. The other
cite, `mutation-sweep-job:2:107` (the `--mutate` step that consumes every manifest), is relevant. **Fix:** drop
`check-plan-code:4:1`, or replace it with a finding that actually touches `scripts/mutations/`.

### C6 — MINOR: three comparison sentences say more than the page they cite

Re-fetched and checked against the page text:

- **cargo-mutants, `ci.html`:** *"diff-only runs on PRs"*. The page's workflow runs a full `cargo mutants -vV
  --in-place` on the (path-filtered) PR trigger. A diff-focused PR check is only named, as a link to `pr-diff.html`,
  which was not fetched. The capability itself is sourced (`in-diff.html` was fetched), so this is mis-attribution,
  not an unsourced capability.
- **Stryker, `stryker-in-pipeline`:** *"a dashboard report upload"*. The pipeline page documents **dashboard compare**
  as a PR baseline (`--dashboard-api-key`, `"provider": "Dashboard"`). It does not describe uploading a report. The
  second URL in the sentence (`docs/General/dashboard/`) was not re-fetched by me (NOT VERIFIED).
- **Stryker.NET configuration:** *"`with-baseline` is marked experimental"*. That is implied by a section banner
  above it, not stated on the entry. Also, `since` *"tests only code changes since the given target"*; the page does
  not say it *"mutates only source changed"*.

**Fix:** reword the three sentences to the page's own claims.

### C7 — MINOR: the PIT `unverified` row was answerable from a page this task already fetched

The row says *"PIT's git-diff (scmMutationCoverage-style) selection now lives in the separate Arcmutate product: NOT
fetched from Arcmutate's or PIT's own page"*. But `https://pitest.org/quickstart/maven/`, fetched for piece (a), shows
`-DextraFeatures="+GIT(from[HEAD~1]), +arcmutate_history(…)"`, says this activates *"arcmutate's git integration"*,
and says *"Arcmutate provides pull request integration"*. So the attribution IS on a fetched PIT page. Marking it
`unverified` is safe (it cannot trip the FAILS IF). But the sentence's *"not fetched from PIT's own page"* is false.
Also, *"now lives in"* claims a move that the page does not state. **Fix:** mark it `fetched` against the maven
quickstart, and word it the way the page does.

### C8 — MINOR: conclusion (b)'s absence claim "or by observed reads" is contradicted by a fetched page

*"none of the fetched pages documents selecting test suites by the import closure of a change, or by observed
reads"*. The import-closure half holds. The observed-reads half does not:

- mutmut's fetched docs say it *"Knows which tests to execute"*. A stats run records which tests reach each function,
  and a test counts as relevant only *"if the stack depth is below some limit"*.
- Stryker's incremental and `since` modes map a change to the tests that **cover** a mutant.

Those are test selection by runtime-observed reach (per mutant, not per suite). Our observed-reach piece is also not in
the components map (the row's own `ours.b`). So the sentence compares a piece that is not inventoried, and claims an
absence the fetched pages refute. **Fix:** narrow the sentence to "suites selected by the import closure of a change",
or record the per-mutant observed-coverage selection as the nearest equivalent.

## The builder's nine ambiguities — defect or plan gap

| # | Ambiguity | Classification |
|---|---|---|
| 1 | route `kind` values not listed | **Plan gap, file.** Task 19 cannot validate a `kind` that has no vocabulary. The plan's only example is `decouple-config`, and the rows use `practice` and `portable-core` |
| 2 | rows cite other components' findings | **Plan gap, file**, but it is also where C1 and C5 hide. A borrowed cite needs to bear on the citing component, and two of the three here do not. The rule should say what a borrowed cite has to show |
| 3 | extra fields (`notes`, `channel`, `uses`) | **Not a defect.** Task 19 should decide whether to refuse unknown keys. It is a note for Task 19, not a row error |
| 4 | `practice_entry` string form | **Plan gap, minor.** Both strings match the heading exactly after stripping `## `. Task 19 should fix the comparison (with or without the number) |
| 5 | velocity-docs C5 `unanswered` | **Not a defect.** Spec §4: C5 asks whether the content is redistributable, no review covers these documents, and a DON'T-SHIP verdict is consistent with a veto. Observation: `mutation-manifests`, also a `data` row with no content review, records C5 `pass`. The two data rows should apply one rule |
| 6 | mutation-sweep-job is the whole ci.yml | **Map gap (Task 5), file.** It is the source of the miscount in C4 |
| 7 | piece (b) has no component of its own | **Map gap, file.** `select_manifests` lives inside `check-plan-code`, and observed reach is not mapped at all (see C8) |
| 8 | some practices have no heading | **Not a defect.** Task 20 owns writing them, and the rows correctly say `harvest none` instead of claiming a practice that does not exist |
| 9 | `recall` omitted | **Not a defect.** Task 18 owns the `recall` key |

## Checked and NOT a finding

- Verdict shapes match the plan: the engine is DON'T-SHIP with a `practice` harvest, as Task 17 expects. Every grade
  is `argued`.
- Numbers re-derived: `check-plan-code.py` has 8,690 lines; `scripts/mutations/` has 106 files (at HEAD and at
  637950d2); the matrix has 38 shards (line 1394); `max-parallel` is 12 on a schedule (line 1208); the cron is
  `'30 8 * * *'` (line 43); `RECORD_SCHEMA` is at check-plan-code line 2988; the mention counts (4 and 180) match
  the scan.
- cargo-mutants `shards.html` matches the sentence exactly: `--shard k/n`, slice default, `--sharding round-robin`,
  no coordination, a GitHub Actions matrix, and partitioning by count, not by cost. So *"only cargo-mutants documents
  sharding across CI jobs"* holds over the fetched pages. The StrykerJS configuration page has no `shard`.
- Conclusion (c), *"no scheduled sweep that files an issue"*, holds across every fetched page (none contains
  schedule/cron/issue in that sense).
- PIT `incremental_analysis`, mutmut's function-level re-test, `in-diff.html` and `iterate.html` all match their
  sentences.

## NOT VERIFIED

- `https://stryker-mutator.io/docs/General/dashboard/` was not re-fetched.
- `mutants.rs/pr-diff.html` was not fetched (it is not cited).

## CHECK / RESULT

| Check | Result |
|---|---|
| Task 17 FAILS IF (unsourced capability, not marked `unverified`) | does not fire |
| Task 19 row rules for effort (2) rows | all pass |
| C3 fails rest on a real dependency on the engine | check-plan-code ✅ (by definition); mutation-sweep-job ✅ (`:2:107`); sweep-red-alert ✅ but for a different reason than stated (C2); **coverage-verdict ✗ (C1)** |
| Engine sentences match their pages | 3 overstatements (C6), 1 mis-marked `unverified` (C7), 1 refuted absence (C8) |

Findings: 1 Major (C1), 7 Minor (C2–C8).

VERDICT: NOT CONVERGED

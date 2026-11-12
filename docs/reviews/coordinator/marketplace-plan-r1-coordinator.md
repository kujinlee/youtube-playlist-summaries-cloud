# Round 1 — `marketplace-plan` (the marketplace-inventory implementation plan, PR #562) — coordinator — NOT CONVERGED (both halves), all folded

```yaml
round: 1
fixes_nontrivial: true
subject: marketplace-plan
halves:
  codex: ran
  claude: ran
findings:
  - {id: CB1, severity: Blocking, aim: deliverable, fix_induced: false, component: task-4-spike, disposition: fixed}
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: task-4-spike, disposition: fixed}
  - {id: CM2, severity: High, aim: deliverable, fix_induced: false, component: task-7-closure, disposition: fixed}
  - {id: CM3, severity: High, aim: deliverable, fix_induced: false, component: task-6-declaration, disposition: fixed}
  - {id: CM4, severity: High, aim: deliverable, fix_induced: false, component: task-11-detector-4, disposition: fixed}
  - {id: CM5, severity: High, aim: deliverable, fix_induced: false, component: task-11-detector-4, disposition: fixed}
  - {id: CM6, severity: High, aim: deliverable, fix_induced: false, component: task-9-detector-1, disposition: fixed}
  - {id: CM7, severity: High, aim: deliverable, fix_induced: false, component: task-19-inventory-guard, disposition: fixed}
  - {id: CM8, severity: High, aim: deliverable, fix_induced: false, component: slice-map, disposition: fixed}
  - {id: Cm1, severity: Low, aim: deliverable, fix_induced: false, component: task-3-staging, disposition: refuted}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: task-19-inventory-guard, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: task-19-inventory-guard, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: task-5-map, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: task-6-declaration, disposition: fixed}
  - {id: Cm6, severity: Low, aim: deliverable, fix_induced: false, component: slice-map, disposition: fixed}
  - {id: Cm7, severity: Low, aim: deliverable, fix_induced: false, component: task-14-tier-a, disposition: fixed}
  - {id: Cm8, severity: Low, aim: deliverable, fix_induced: false, component: task-18-recall, disposition: fixed}
  - {id: Cm9, severity: Low, aim: deliverable, fix_induced: false, component: task-14-tier-a, disposition: fixed}
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: task-4-spike, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: task-19-inventory-guard, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: task-14-tier-a, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: false, component: task-20-routes, disposition: fixed}
  - {id: X5, severity: High, aim: deliverable, fix_induced: false, component: task-11-detector-4, disposition: fixed}
  - {id: X6, severity: High, aim: deliverable, fix_induced: false, component: task-19-inventory-guard, disposition: fixed}
```

Plan at `266ba0b5`; both halves filed in `5945d39e`. Codex (`docs/reviews/codex/marketplace-plan-r1-codex.md`) 1
BLOCKER + 5 MAJOR; Claude (`docs/reviews/claude/marketplace-plan-r1-claude.md`) 1 BLOCKER + 8 MAJOR + 9 MINOR.
**Shared:** CB1 = X1 (one fix), CM5 = X5 (one fix), Cm3 ≈ X2 (one fix). Severity map: BLOCKER → Blocking, MAJOR →
High, MINOR → Low. Every gate this fold changed names the observation that makes it FAIL (in the plan, per task).

**No `OWNER DECISION NEEDED`.** CM3 and CM6 were followed as the spec states them and change no decision. CM8
RESTORES D8 (quoted below) rather than re-deciding it. The reviewer's broader point was that the plan turns the
spec's single "PR 1" into several PRs. That is not an owner decision the spec records. The spec names the deliverable
"PR 1" and decides only where the corrections go and when they may split off. That placement is now kept exactly.

## Findings

- **CB1 / X1 (Blocking, FIXED; Task 4):** the spike staged `explainer-serve.py` without `page_chrome.py` and
  `page_markup.py`, which it imports at module load (`explainer-serve.py:101-102`). Even `--help` died with
  `ModuleNotFoundError`. The fix stages the import closure. **Evidence (fold, measured):** I copied the three files
  to a scratch dir and ran them by absolute path from an unrelated directory, with a fresh `HOME` and `python3 -I`.
  Result: `--help` rc 0, `--status` rc 0. `fixture_git` is imported only in the self-tests (`:1636`). A NO-GO caused
  by the plan's own staging is now stated to be a plan defect, never the D3 falsifier. **FAILS IF:** `--help` by
  the installed path exits non-zero with `ModuleNotFoundError` naming a file that exists in `scripts/`.
- **CM1 (High, FIXED; Task 4, Task 2, H7):** there is no port option, because `PORT = 7391` is a module constant
  (`:104`) and `main()` takes only `--stop`, `--status` and `--self-test`. **Measured at fold:** the stranger-world
  `--status` printed `listening : yes on http://127.0.0.1:7391`. That is the owner's server, observed from the
  stranger's world. The fix: the serve operation runs on 7391 only once preflight confirms the port is free.
  Otherwise it waits on a new **Human step H7**, in which the owner stops their own server, and the spike is
  INCOMPLETE (neither GO nor NO-GO). The agent never stops the owner's process. The hard-coded port is recorded as
  a finding. The preflight self-test now binds port `0` and passes the assigned port in, so it no longer collides
  with the owner. **FAILS IF:** GO is recorded without `GET /` served from the world's `~/explainers`.
- **CM2 (High, FIXED; Task 7):** every CWD-relative edge is now also resolved against the package root, using a
  four-row rule table. An executable edge to a file that exists in the repository but not in the package is a
  **gap**. **Evidence:** the four CWD-relative skill→script edges re-measured
  (`dashboard/SKILL.md:76`, `explainer-delivery.md:165/223/300`). New case: `brief-compose.py dropped … → closure
  red`. **FAILS IF:** that mutation leaves `--closure` green.
- **CM3 (High, FIXED; Tasks 5, 6, 7, 17):** packages now carry a `channel`. `ci-layer` is `reusable-workflow` and is
  NEVER `claude plugin install`ed. This follows spec §2c, *Install channel for CI pieces* (line 149): "not through
  `/plugin marketplace add`", and "C4 stays `argued` (no experiment this milestone)". Its declaration is listed
  from the map, with no `installed_files`. `--closure` reports `SKIPPED`, never a silent pass. **FAILS IF:**
  `ci-layer`'s entry carries `installed_files`.
- **CM4 (High, FIXED; Task 11):** the calibration population is now stated as the ground-truth passage of
  `brief/SKILL.md`. The whole-file run gets its own case, which names all three extras. **Measured at fold:**
  `grep -o -E 'docs/…|check-[a-z-]+'` over the file gives 11 distinct items: 8 of the nine (`TaskList` matches
  neither pattern) plus `check-deploy-freshness`, `check-selftest-counts` and `docs/dev-process.md`. The file is
  unchanged since `2f5e3f3d`. The "exactly" case and the FAILS IF now agree. **FAILS IF:** the passage yields any
  count other than 9.
- **CM5 / X5 (High, FIXED; Task 11, file map):** the tool names are now a hand-written, dated
  `docs/marketplace/harness-tools.txt`, with `claude --version` (2.1.322) in its header. This is a STATED deviation
  from "derived". **Measured:** `available-skills.md` contains none of the four tool names. No repository file lists
  harness tools: the `.claude/settings.json` matchers name only `Agent`, `Skill`, `AskUserQuestion`, `Bash`,
  `Edit`, `Write`, `Read` and `SendMessage`. Adjacent negative: `JavaScript` and `SessionStart` are not tool
  names. **FAILS IF:** a list with no date/version header does not give CANNOT RUN.
- **CM6 (High, FIXED; Task 9):** the vocabulary is now derived through a table of sources, each read from disk.
  `gemini` comes from the module stems named in `docs/dev-process.md`'s *Mocking boundaries* paragraph (line 200),
  which follows spec §5 item 1's term list. The directory list is now a predicate: product-language files and no
  Task 5 candidate. **Measured:** it yields `app components lib supabase tests types worker`. The rule takes
  scoped-dependency scopes (`google`, `googleapis`, `supabase`). `fly.toml` is present and `.env.example` is
  absent. The owner handle from the remote URL is now included, with the intent stated. Cases: the live tree
  matches all four spec terms, plus an adjacent fixture with no source yielding no `gemini`. **FAILS IF:** the live
  vocabulary lacks any of the four terms, or the source holds one as a literal.
- **CM7 (High, FIXED; Tasks 14, 19):** the grade is now required on EVERY row, quoting §4b. Two new rules
  (adjacent negatives listed): SHIP versus experiment, read from a new tier-A sidecar
  `experiment-tier-a.json`; and a per-component shipping-set rule for D11. **FAILS IF:** a NEEDS-WORK row with
  no grade passes.
- **CM8 (High, FIXED; slice map, Task 1):** slice A is removed, and Task 1 is **slice B's first commit**. Spec §7
  item 8, quoted in the plan: *"⭐ **D8 — A CORRECTION LANDS WITH THE WORK THAT FOUND IT, NOT IN A SEPARATE PR.
  Decided 2026-10-16 by the owner** … 'yes, fix in here.'"* and *"they go in as its **first commit** and are
  mergeable alone. The observation that makes this bound FAIL: PR 1 open with ANY OF THE THREE corrections not yet
  committed."* D8's FAILS IF is restated against the slices. **FAILS IF:** slice B's PR is open without the three
  corrections, or the corrections commit is not first on `mkt-spike`, or it touches other files.
- **X2 / Cm3 (High, FIXED; Tasks 18, 19):** Task 18 now WRITES the recall rows' phase from
  `recall.a`/`recall.b`. `checkpoint_fires` counts only resolved phase `"1"`. An unresolved `"1-if-feasible"` row
  counts only when it cannot change the answer, and otherwise gives CANNOT RUN (it depends on H1). A row left at
  `1-if-feasible` after D11 failed is a row error. **Extracted and run at fold** (scratch, `python3 -I`): all 10
  asserts pass. The mutation restoring r0's population fails an assert. Codex's scenario (four excluded recall rows
  added to a firing set) now fires. **FAILS IF:** a recall row is `1-if-feasible` while `recall.a` is false.
- **X3 (High, FIXED; Task 14):** a hollow page now keeps `measured` and FAILS pass condition 2. The gate now rejects
  `pass`/`SHIP` instead of rejecting the grade. **FAILS IF:** condition 2 is `pass` on a page with a non-empty
  `missing-capability` item.
- **X4 (High, FIXED; Tasks 20, 22):** the practice entries move to Task 20, BEFORE the guard first reads the live
  inventory. **Measured:** no `portable-practices.md` heading contains `CLAUDE_PLUGIN_ROOT`. Task 22 keeps only the
  rubric entry. **FAILS IF:** a `practice_entry` names a heading absent from the same commit.
- **X6 (High, FIXED; Tasks 19, 20):** Task 19 wires `--self-test` only. The live CI caller lands in Task 20, in the
  commit that completes the rows. **FAILS IF:** Task 19's commit runs the live inventory in CI.
- **Cm1 (Low, REFUTED):** the reviewer's own verification that the probe works and that dot-directories survive
  install. Not a defect; recorded so it is not redone.
- **Cm2 (Low, FIXED):** `_fires` refuses `next_project_hours <= 0`, and an assert covers both of the reviewer's
  probes. Exit codes are ranked: 2 for unreadable input, then 1 for row errors (the checkpoint is not computed),
  then 2 for a checkpoint that cannot be computed, then 3, then 0. Case: `errors AND crossed threshold → 1, not 3`.
- **Cm4 (Low, FIXED by stating intent):** the `--map` CI tax is intended (spec §3). Glob exclusions with one reason
  keep it to a line. A glob that hides a file a package invokes is refused, with a case.
- **Cm5 (Low, FIXED):** the vacuous `check-publishability*` gate is replaced by "declare opens nothing outside the
  installed dir".
- **Cm6 (Low, FIXED):** moot once slice A is gone. The spend log is created in Task 2, and Task 1 writes no
  spend-log row (the row is per slice, at slice end). The DRAFT-at-slice-start rule no longer conflicts with any
  FAILS IF.
- **Cm7 (Low, FIXED):** `--permission-mode bypassPermissions` (measured present in `claude --help`) is named as a
  baseline deviation, and so is the namespaced `/comprehensibility:<skill>` invocation. A form that does not resolve
  is a baseline defect, not a suite defect.
- **Cm8 (Low, FIXED):** Task 18's allow-list now includes `bash` and `claude` (`surface-recall.sh` has a bash
  shebang, and `recall-llm.py:923-924` runs `claude -p`), and the task depends on H2. Without them the probe gives
  `a = "CANNOT RUN"`, never `false`.
- **Cm9 (Low, FIXED):** pass condition 2 is scored only for `brief`. The other four page skills are recorded `not
  scored — no seeded facts` and graded `argued` on that condition.

**Defaults-table notes folded too:** the sitecustomize shadowing is a stated baseline deviation. The cost unit now
says "review to convergence under the round cap", not "one round". The ADR 0015 vs spec `ADR: none` difference is
explained in the plan header.

**Backlog rows filed:** none. Every MINOR was cheap enough to fix.

Round 2 alternates: ONE half.
